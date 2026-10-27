#!/usr/bin/env python3
"""flow-attn: does the dollar-volume attention ratio V1 rank later returns? (pre-registered 2026-10-27)

Pre-registration: docs/claude/flow-attention-review-2026-10-27.md section 5 (criteria are fixed there,
this script only computes them; user decision card 2026-10-27 20:11 KST "고정 + 1/16 함께 채점").
Rows and forward returns are the wl-fwd-score rows (docs/claude/watchlist_forward_score.py, imported).
Read-only: reads the registry (git history + working copy) and a folder of saved Kiwoom daily-bar responses.
Writes nothing (save the --json output yourself to keep the 2026-12-19 values). No authority, no orders.

Bars: one file per symbol, <bars-dir>/<CODE>.json = the kiwoom_query "overseas candles stock-daily" response
(adjusted, format json) with result.result_list rows {dt, cur_prc, acc_trde_prica, ...}. Fetch every symbol that
appears in any snapshot plus SOXX and GRID. A failed fetch is simply missing (rows become null, never filled).

Usage (repo root): python docs/claude/flow_attention_score.py --bars-dir <dir> [--horizon-weeks 4] [--json]
                   [--cache <earlier --json output>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watchlist_forward_score as wf  # noqa: E402  (same folder; rows, Spearman, terciles, thresholds)

# Pre-registered values (section 5). Do not edit after the commit that fixes section 5.
RECENT, PRIOR = 5, 15                     # V1 = mean dollar value of the last 5 sessions / the 15 before
MIN_RECENT, MIN_PRIOR = 4, 12             # sessions left after exclusions, else null
EARLY_CLOSE = {"20261127", "20261224"}    # calendar-authority reviewed.json:121-122 (13:00 ET)
RET_TOLERANCE = 0.003                     # snapshot return vs re-fetched bar return, else null
CACHE_TOLERANCE = 1e-9                    # 12/19 value vs 1/16 recomputation, else null
R60 = 60                                  # V3 (display only): 60-session return vs the row's benchmark
V3_MIN_SIDE = 3


def load_bars(folder: Path) -> dict[str, dict]:
    """{code: {"days": [YYYYMMDD...], "close": [...], "value": [...]}} ascending; value None when 0/missing."""
    out = {}
    for path in sorted(folder.glob("*.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8-sig"))["result"]["result_list"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        series = {}
        for row in rows:
            try:
                day, close = str(row["dt"]), float(row["cur_prc"])
            except (KeyError, TypeError, ValueError):
                continue
            try:
                value = float(row.get("acc_trde_prica") or 0)
            except (TypeError, ValueError):
                value = 0.0
            series[day] = (close, value if value > 0 else None)
        days = sorted(series)
        out[path.stem.upper()] = {"days": days, "close": [series[d][0] for d in days],
                                  "value": [series[d][1] for d in days]}
    return out


def v1(bar: dict, day: str) -> float | None:
    if day not in bar["days"]:
        return None
    i = bar["days"].index(day)
    if i < RECENT + PRIOR - 1:
        return None
    def usable(lo: int, hi: int) -> list[float]:
        return [bar["value"][k] for k in range(lo, hi)
                if bar["value"][k] is not None and bar["days"][k] not in EARLY_CLOSE]
    recent = usable(i - RECENT + 1, i + 1)
    prior = usable(i - RECENT - PRIOR + 1, i - RECENT + 1)
    if len(recent) < MIN_RECENT or len(prior) < MIN_PRIOR:
        return None
    return statistics.fmean(recent) / statistics.fmean(prior)


def ret(bar: dict | None, start: str, end: str, back: int = 0) -> float | None:
    if not bar or start not in bar["days"] or end not in bar["days"]:
        return None
    i = bar["days"].index(start) - back
    if i < 0:
        return None
    return bar["close"][bar["days"].index(end)] / bar["close"][i] - 1


def r60(bar: dict | None, day: str) -> float | None:
    return ret(bar, day, day, back=R60)


def evaluate(snaps: dict, bars: dict, horizon_weeks: int, cache: dict | None) -> dict:
    bases = sorted(snaps)
    weeks, dropped = [], {"no_v1": 0, "return_mismatch": 0, "cache_mismatch": 0}
    for base in bases:
        target = wf._day(base) + dt.timedelta(days=7 * horizon_weeks)
        fwd = [b for b in bases if abs((wf._day(b) - target).days) <= 3]
        if not fwd:
            continue
        later = snaps[fwd[0]]
        rows = []
        for code in sorted(set(snaps[base]) & set(later)):
            snap_ret = later[code]["close"] / snaps[base][code]["close"] - 1
            value = v1(bars[code], base) if code in bars else None
            if value is None:
                dropped["no_v1"] += 1
                continue
            bar_ret = ret(bars.get(code), base, fwd[0])
            if bar_ret is None or abs(bar_ret - snap_ret) > RET_TOLERANCE:
                dropped["return_mismatch"] += 1
                continue
            old = ((cache or {}).get(base) or {}).get(code)
            if old is not None and abs(old - value) > CACHE_TOLERANCE:
                dropped["cache_mismatch"] += 1
                continue
            bm = (snaps[base][code].get("bm") or "SOXX")
            own, ref = r60(bars.get(code), base), r60(bars.get(bm), base)
            rows.append({"code": code, "v1": value, "price": wf.part_value(snaps[base][code], "price"),
                         "ret": snap_ret, "v3": None if own is None or ref is None else bool(value > 1.0 and own > ref)})
        xs, ps, ys = [r["v1"] for r in rows], [r["price"] for r in rows], [r["ret"] for r in rows]
        on = [r["ret"] for r in rows if r["v3"] is True]
        off = [r["ret"] for r in rows if r["v3"] is False]
        weeks.append({"base": base, "forward": fwd[0], "pairs": len(rows),
                      "v1_rho": wf.spearman(xs, ys), "v1_spread": wf.tercile_spread(xs, ys),
                      "price_rho": wf.spearman(ps, ys), "v1_price_rho": wf.spearman(xs, ps),
                      "v3_on_minus_off": (statistics.fmean(on) - statistics.fmean(off))
                      if len(on) >= V3_MIN_SIDE and len(off) >= V3_MIN_SIDE else None,
                      "v1": {r["code"]: r["v1"] for r in rows}})
    usable = [w for w in weeks if w["pairs"] >= wf.MIN_PAIRS and w["v1_rho"] is not None]
    rhos = [w["v1_rho"] for w in usable]
    spreads = [w["v1_spread"] for w in usable if w["v1_spread"] is not None]
    prices = [w["price_rho"] for w in usable if w["price_rho"] is not None]
    s = {"weeks": len(rhos),
         "mean_rho": statistics.fmean(rhos) if rhos else None,
         "share_rho_pos": (sum(r > 0 for r in rhos) / len(rhos)) if rhos else None,
         "mean_spread": statistics.fmean(spreads) if spreads else None,
         "mean_price_rho_same_rows": statistics.fmean(prices) if prices else None,
         "mean_v1_price_rho": statistics.fmean([w["v1_price_rho"] for w in usable if w["v1_price_rho"] is not None])
         if any(w["v1_price_rho"] is not None for w in usable) else None}
    if s["weeks"] < wf.MIN_WEEKS:
        s["verdict"] = "INSUFFICIENT_SAMPLE"
    else:
        ok = (s["mean_rho"] >= wf.P1_RHO and s["share_rho_pos"] >= wf.P2_SHARE
              and s["mean_spread"] is not None and s["mean_spread"] >= wf.P3_SPREAD
              and s["mean_price_rho_same_rows"] is not None and s["mean_rho"] > s["mean_price_rho_same_rows"])
        s["verdict"] = "PASS" if ok else "FAIL"
    return {"horizon_weeks": horizon_weeks, "snapshots": bases, "weeks": weeks, "dropped": dropped, "summary": s,
            "criteria": {"min_weeks": wf.MIN_WEEKS, "min_pairs": wf.MIN_PAIRS, "P1_mean_rho": wf.P1_RHO,
                         "P2_share_rho_pos": wf.P2_SHARE, "P3_mean_tercile_spread": wf.P3_SPREAD,
                         "P4": "mean V1 rho > mean price rho on the same rows"},
            "order_authority": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars-dir", type=Path, required=True)
    parser.add_argument("--horizon-weeks", type=int, default=4)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo", type=Path, default=wf.REPO)
    args = parser.parse_args()
    cache = None
    if args.cache:
        cache = {w["base"]: w["v1"] for w in json.loads(args.cache.read_text(encoding="utf-8"))["weeks"]}
    docs = wf.load_documents(args.repo)
    snaps = wf.snapshots(docs)
    for doc in docs:  # benchmark per row (detail.bm, default SOXX), oldest first like wf.snapshots
        run = doc.get("weeklyRun") or {}
        base = run.get("basis")
        items = [(c.get("code"), c) for c in doc.get("candidates") or []] + list((run.get("memberData") or {}).items())
        for code, item in items:
            if base in snaps and code in snaps[base]:
                snaps[base][code]["bm"] = (item.get("detail") or {}).get("bm") or "SOXX"
    result = evaluate(snaps, load_bars(args.bars_dir), args.horizon_weeks, cache)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    fmt = lambda v, p=2: "-" if v is None else f"{v:.{p}f}"
    print(f"flow-attn horizon {result['horizon_weeks']}w · snapshots {', '.join(result['snapshots'])} · dropped {result['dropped']}")
    for w in result["weeks"]:
        print(f"  {w['base']}->{w['forward']} n={w['pairs']} V1 rho {fmt(w['v1_rho'])} spr {fmt(w['v1_spread'], 3)} "
              f"| price rho {fmt(w['price_rho'])} | V1~price {fmt(w['v1_price_rho'])} | V3 on-off {fmt(w['v3_on_minus_off'], 3)}")
    s = result["summary"]
    print(f"  [V1] weeks {s['weeks']} mean_rho {fmt(s['mean_rho'])} pos {fmt(s['share_rho_pos'])} spread "
          f"{fmt(s['mean_spread'], 3)} price_rho {fmt(s['mean_price_rho_same_rows'])} -> {s['verdict']}")


if __name__ == "__main__":
    main()
