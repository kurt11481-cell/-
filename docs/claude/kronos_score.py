#!/usr/bin/env python3
"""evolve-1029 Kronos forecast scoring (research only, no trading use).

Pre-registered in docs/claude/trading-tools-review-2026-10-29.md section 11-3 (CEO confirmation
2026-10-29 19:58 KST). Scores 20-session probabilistic close forecasts of Kronos-small against three
random-walk / historical baselines with Kiwoom daily closes. Never calls a broker; grants no order,
quantity, card or core authority.

Inference is Kronos's own autoregressive sampler re-run with a key/value cache (same model math;
eval mode as in the authors' finetune/qlib_test.py 211-212). `--selftest` checks it against
model/kronos.py auto_regressive_inference on synthetic input before any scoring run.

python -I kronos_score.py --manifest M --code KRONOS_DIR --model DIR --tokenizer DIR --phase first
       --rows rows.jsonl --out result.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

TICKERS = ["SOXX", "QQQ", "SOXL", "MU", "DELL", "PWR", "LITE", "BE", "GRID", "NBIS"]
SECONDARY = ["SOXX", "QQQ"]
ANCHOR = "2025-07-01"
STEP = 5
H = 20
MAX_CTX_ROWS = 400
MIN_ROWS = 120
BASE_WINDOW = 252
PATHS = 30
T_SAMPLE, TOP_P, TOP_K = 1.0, 0.9, 0
CLIP = 5
BLOCK = 4
BOOT = 10_000
SEED = 1029
PHASES = {  # origin on/after, target on/before
    "first": (None, "2026-10-28"),
    "mid": ("2026-10-30", "2027-01-15"),
    "second": ("2026-10-30", "2027-04-09"),
}


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------ cached Kronos sampler
class CachedSampler:
    def __init__(self, code_dir: str, model_dir: str, tok_dir: str, threads: int = 4):
        sys.path.insert(0, code_dir)
        import torch
        from model import Kronos, KronosTokenizer
        from model.kronos import sample_from_logits, calc_time_stamps
        torch.set_num_threads(threads)
        self.torch, self.sample, self.stamps = torch, sample_from_logits, calc_time_stamps
        self.model = Kronos.from_pretrained(model_dir).eval()
        self.tok = KronosTokenizer.from_pretrained(tok_dir).eval()

    def _rope(self, rotary, start: int, length: int):
        t = self.torch.arange(start, start + length).type_as(rotary.inv_freq)
        emb = self.torch.einsum("i,j->ij", t, rotary.inv_freq)
        emb = self.torch.cat((emb, emb), dim=-1)
        return emb.cos()[None, None], emb.sin()[None, None]

    def _blocks(self, x, caches, pos):
        F = self.torch.nn.functional
        for li, layer in enumerate(self.model.transformer):
            att = layer.self_attn
            h = layer.norm1(x)
            b, n, _ = h.shape
            q, k, v = (proj(h).view(b, n, att.n_heads, att.head_dim).transpose(1, 2)
                       for proj in (att.q_proj, att.k_proj, att.v_proj))
            cos, sin = self._rope(att.rotary, pos, n)
            q = q * cos + att.rotary._rotate_half(q) * sin
            k = k * cos + att.rotary._rotate_half(k) * sin
            if caches[li] is not None:
                k = self.torch.cat([caches[li][0], k], dim=2)
                v = self.torch.cat([caches[li][1], v], dim=2)
            caches[li] = (k, v)
            o = F.scaled_dot_product_attention(q, k, v, is_causal=(pos == 0))
            x = x + att.out_proj(o.transpose(1, 2).contiguous().view(b, n, att.d_model))
            x = x + layer.ffn(layer.norm2(x))
        return self.model.norm(x)

    def _s2_logits(self, ctx_all, s1):
        dep = self.model.dep_layer
        sib = self.model.embedding.emb_s1(s1)
        att = dep.cross_attn(query=sib, key=ctx_all, value=ctx_all)
        return self.model.head.cond_forward(dep.norm(ctx_all[:, -1:] + att))[:, -1]

    def paths(self, df: pd.DataFrame, x_ts: pd.Series, y_ts: pd.Series, n_paths: int, seed: int) -> np.ndarray:
        """n_paths sampled future frames (n_paths, H, 6) in price units."""
        torch = self.torch
        cols = ["open", "high", "low", "close", "volume", "amount"]
        x = df[cols].values.astype(np.float32)
        mean, std = x.mean(axis=0), x.std(axis=0)
        xn = np.clip((x - mean) / (std + 1e-5), -CLIP, CLIP)
        stamp = np.concatenate([self.stamps(x_ts).values, self.stamps(y_ts).values]).astype(np.float32)
        torch.manual_seed(seed)
        with torch.no_grad():
            xt = torch.from_numpy(xn)[None]
            st = torch.from_numpy(stamp)[None]
            pre, post = self.tok.encode(torch.clip(xt, -CLIP, CLIP), half=True)
            L0 = pre.shape[1]
            caches = [None] * len(self.model.transformer)
            emb = self.model.embedding([pre, post]) + self.model.time_emb(st[:, :L0])
            ctx = self._blocks(emb, caches, 0)
            caches = [(k.expand(n_paths, -1, -1, -1).contiguous(), v.expand(n_paths, -1, -1, -1).contiguous())
                      for k, v in caches]
            ctx = ctx.expand(n_paths, -1, -1).contiguous()
            gen_pre, gen_post = [], []
            for i in range(H):
                if i > 0:
                    pos = L0 + i - 1
                    e = self.model.embedding([gen_pre[-1], gen_post[-1]]) + self.model.time_emb(
                        st[:, pos:pos + 1].expand(n_paths, -1, -1))
                    ctx = torch.cat([ctx, self._blocks(e, caches, pos)], dim=1)
                s1_logits = self.model.head(ctx[:, -1])
                s1 = self.sample(s1_logits, temperature=T_SAMPLE, top_k=TOP_K, top_p=TOP_P, sample_logits=True)
                s2 = self.sample(self._s2_logits(ctx, s1), temperature=T_SAMPLE, top_k=TOP_K, top_p=TOP_P,
                                 sample_logits=True)
                gen_pre.append(s1)
                gen_post.append(s2)
            full_pre = torch.cat([pre.expand(n_paths, -1)] + gen_pre, dim=1)
            full_post = torch.cat([post.expand(n_paths, -1)] + gen_post, dim=1)
            z = self.tok.decode([full_pre, full_post], half=True)[:, -H:].numpy()
        return z * (std + 1e-5) + mean


def selftest(s: CachedSampler) -> dict:
    """Compare against the reference sampler (eval mode, sample_count=1, same seed)."""
    from model.kronos import auto_regressive_inference
    torch = s.torch
    out = []
    for case in range(2):
        rng = np.random.default_rng(100 + case)
        n = 400 if case == 0 else 175
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
        df = pd.DataFrame({"open": c * (1 + rng.normal(0, 0.003, n)), "high": c * 1.01, "low": c * 0.99,
                           "close": c, "volume": rng.uniform(1e6, 2e6, n)})
        df["amount"] = df["volume"] * c
        x_ts = pd.Series(pd.bdate_range("2024-01-01", periods=n))
        y_ts = pd.Series(pd.bdate_range(x_ts.iloc[-1] + pd.Timedelta(days=1), periods=H))
        mine = s.paths(df, x_ts, y_ts, 8, seed=7)
        x = df.values.astype(np.float32)
        mean, std = x.mean(axis=0), x.std(axis=0)
        xn = np.clip((x - mean) / (std + 1e-5), -CLIP, CLIP)
        xs = s.stamps(x_ts).values.astype(np.float32)
        ys = s.stamps(y_ts).values.astype(np.float32)
        torch.manual_seed(7)
        ref = auto_regressive_inference(s.tok, s.model, torch.from_numpy(np.repeat(xn[None], 8, 0)),
                                        torch.from_numpy(np.repeat(xs[None], 8, 0)),
                                        torch.from_numpy(np.repeat(ys[None], 8, 0)), 512, H, CLIP,
                                        T_SAMPLE, TOP_K, TOP_P, 1, False)[:, -H:] * (std + 1e-5) + mean
        diff = np.abs(mine[:, :, 3] - ref[:, :, 3]) / np.abs(ref[:, :, 3])
        out.append({"rows": n, "paths_identical": int((diff.max(axis=1) < 1e-4).sum()), "paths": 8,
                    "max_rel_diff_close": float(diff.max())})
    return {"cases": out}


# ------------------------------------------------------------------ scoring
def crps_normal(m: float, sd: float, y: float) -> float:
    from scipy.stats import norm
    z = (y - m) / sd
    return float(sd * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / math.sqrt(math.pi)))


def crps_fair(xs: np.ndarray, y: float) -> float:
    xs = np.asarray(xs, dtype=float)
    m = len(xs)
    return float(np.abs(xs - y).mean() - np.abs(xs[:, None] - xs[None, :]).sum() / (2 * m * (m - 1)))


def bootstrap(rows: list[dict], stat, rng) -> tuple[float, float]:
    origins = sorted({r["origin"] for r in rows})
    by = {o: [r for r in rows if r["origin"] == o] for o in origins}
    k = len(origins)
    nb = math.ceil(k / BLOCK)
    vals = np.empty(BOOT)
    for b in range(BOOT):
        starts = rng.integers(0, max(1, k - BLOCK + 1), nb)
        pick = [origins[i] for s0 in starts for i in range(s0, min(s0 + BLOCK, k))][:k]
        vals[b] = stat([r for o in pick for r in by[o]])
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def summarize(rows: list[dict], rng) -> dict:
    if not rows:
        return {"forecasts": 0}
    sums = {b: sum(r[b] for r in rows) for b in ("crps_b1", "crps_b2", "crps_b3")}
    best = min(sums, key=sums.get)

    def p1(rs):
        return 1 - sum(r["crps_k"] for r in rs) / sum(r[best] for r in rs)

    def cover(rs):
        return float(np.mean([r["covered80"] for r in rs]))

    p1_lo, p1_hi = bootstrap(rows, p1, rng)
    cv_lo, cv_hi = bootstrap(rows, cover, rng)
    dirs = [r for r in rows if r["y"] != 0]
    res = {"forecasts": len(rows), "origins": len({r["origin"] for r in rows}),
           "n_eff_blocks": len({r["origin"] for r in rows}) / BLOCK,
           "crps_sums": {k: v for k, v in {"kronos": sum(r["crps_k"] for r in rows), **sums}.items()},
           "best_baseline": best, "P1": p1(rows), "P1_ci95": [p1_lo, p1_hi],
           "P1_vs_each": {b: 1 - sum(r["crps_k"] for r in rows) / sums[b] for b in sums},
           "P2_coverage80": cover(rows), "P2_ci95": [cv_lo, cv_hi],
           "P3_direction_hit": float(np.mean([np.sign(r["median"]) == np.sign(r["y"]) for r in dirs]))}
    res["P1_pass"] = res["P1"] > 0 and p1_lo > 0
    res["P2_pass"] = cv_lo <= 0.80 <= cv_hi
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest")
    ap.add_argument("--code", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--phase", choices=sorted(PHASES))
    ap.add_argument("--rows")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--qqq-refetch-same", action="store_true")
    ap.add_argument("--max-new", type=int, default=10**9, help="stop after this many new forecasts (resume later)")
    a = ap.parse_args()

    sampler = CachedSampler(a.code, a.model, a.tokenizer)
    if a.selftest:
        print(json.dumps(selftest(sampler)))
        return 0

    sys.path.insert(0, str(Path(__file__).parent))
    from risk_map import clean_hl, load_kiwoom
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    bars, notes = {}, []
    for t in TICKERS:
        bars[t], n = clean_hl(t, load_kiwoom(manifest[t]), a.qqq_refetch_same)
        notes += n
    cal = bars["SOXX"].index
    lo, hi = PHASES[a.phase]
    grid = list(range(cal.searchsorted(pd.Timestamp(ANCHOR)), len(cal), STEP))
    origins = [i for i in grid if i + H < len(cal) and cal[i + H] <= pd.Timestamp(hi)
               and (lo is None or cal[i] >= pd.Timestamp(lo))]

    rows_path = Path(a.rows)
    done = {}
    if rows_path.exists():
        for line in rows_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done[(r["origin"], r["ticker"])] = r
    skipped, new = [], 0
    with rows_path.open("a", encoding="utf-8") as fh:
        for oi in origins:
            o, target_day = cal[oi], cal[oi + H]
            for ti, t in enumerate(TICKERS):
                key = (str(o.date()), t)
                if key in done:
                    continue
                b = bars[t].loc[:o]
                if len(b) == 0 or b.index[-1] != o or len(b) < MIN_ROWS + 1:
                    skipped.append({"origin": key[0], "ticker": t, "reason": "history_or_origin_bar"})
                    continue
                if target_day not in bars[t].index:
                    skipped.append({"origin": key[0], "ticker": t, "reason": "target_close_missing"})
                    continue
                if new >= a.max_new:
                    continue
                c0 = float(b["close"].iloc[-1])
                y = math.log(float(bars[t].at[target_day, "close"]) / c0)
                ctx = b.iloc[-MAX_CTX_ROWS:]
                y_ts = pd.Series(cal[oi + 1:oi + H + 1])
                t0 = time.time()
                fut = sampler.paths(ctx, pd.Series(ctx.index), y_ts, PATHS, SEED * 100000 + oi * 100 + ti)
                xs = np.log(fut[:, -1, 3] / c0)
                lr = np.diff(np.log(b["close"].values))[-BASE_WINDOW:]
                mu, sd = float(lr.mean()), float(lr.std(ddof=1))
                b3 = np.convolve(lr, np.ones(H), "valid")
                q10, q90 = np.quantile(xs, [0.1, 0.9])
                r = {"origin": key[0], "ticker": t, "target": str(target_day.date()), "y": y,
                     "ctx_rows": len(ctx), "base_rows": len(lr), "median": float(np.median(xs)),
                     "q10": float(q10), "q90": float(q90), "covered80": bool(q10 <= y <= q90),
                     "crps_k": crps_fair(xs, y), "crps_b1": crps_normal(0.0, sd * math.sqrt(H), y),
                     "crps_b2": crps_normal(mu * H, sd * math.sqrt(H), y), "crps_b3": crps_fair(b3, y),
                     "samples": [float(v) for v in xs], "sec": round(time.time() - t0, 1)}
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                done[key] = r
                new += 1
    expected = len(origins) * len(TICKERS)
    wanted = {str(cal[i].date()) for i in origins}
    rows = [done[k] for k in sorted(done) if k[0] in wanted]
    complete = len(rows) + len(skipped) >= expected
    rng = np.random.default_rng(SEED)
    result = {"artifact": "EVOLVE_1029_KRONOS_SCORE", "research_only": True, "order_authority": False,
              "phase": a.phase, "complete": complete, "notes": notes, "expected": expected, "scored": len(rows),
              "skipped": skipped, "origins": [str(cal[i].date()) for i in origins],
              "script_sha256": sha256(__file__),
              "model_sha256": sha256(Path(a.model) / "model.safetensors"),
              "tokenizer_sha256": sha256(Path(a.tokenizer) / "model.safetensors"),
              "code_sha256": {f: sha256(Path(a.code) / "model" / f) for f in ("__init__.py", "kronos.py", "module.py")},
              "versions": {"torch": sampler.torch.__version__, "numpy": np.__version__, "pandas": pd.__version__,
                           "python": sys.version.split()[0]},
              "inputs": {t: [{"file": Path(p).name, "sha256": sha256(p)} for p in manifest[t]] for t in TICKERS}}
    if complete:
        result["all"] = summarize(rows, rng)
        result["secondary_soxx_qqq"] = summarize([r for r in rows if r["ticker"] in SECONDARY], rng)
        result["per_ticker"] = {t: {"n": len(rs), "P1_vs_b1": 1 - sum(r["crps_k"] for r in rs) / sum(r["crps_b1"] for r in rs)}
                                for t in TICKERS if (rs := [r for r in rows if r["ticker"] == t])}
        result["pass_first"] = bool(result["all"]["P1_pass"] and result["all"]["P2_pass"])
    Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in ("phase", "complete", "expected", "scored")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
