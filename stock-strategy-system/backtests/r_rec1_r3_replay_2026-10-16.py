#!/usr/bin/env python3
"""R-REC1 r3 replay (preregistration docs/claude/r-rec1-r3-preregistration-2026-10-16.md).

Preregistration sha256 (raw = LF): 18cf5799692ded3eb4a671e42cfec7100714f0c76f225e902d5fc57a688c3ee1
(re-fixed 2026-10-16 14:13 KST, d = C). Historical computation only: no order tool, no policy/state/journal write.

Interpretations (numbers = preregistration sections):
I1 (3-1) V0 = auto_core_rules.rrec1 imported unchanged; portfolio_exposure._sample_std is extracted with ast (2-1).
I2 (3-1) series built once with build_series over the sample's own dates; per session t every list key is sliced to
   [t-129, t]; candidate / GRID series are built on the same common dates so indices align.
I3 (3-1) allowed_t = status == "ok".
I4 (4) W1 = C RG4 constants set to inf inside try/finally. W2 = textual patch of rrec1 source (asserted unique
   anchors); REBASE False runs the production lines.
I5 (5) t0: allowed[t0-1] True and allowed[t0] False (t0-1 must be an evaluated session). u: first allowed after t0.
   End kind at u: open (closed_at == u, all rg ok) / decay (closed_at == u) / window_exit (no closed_at).
I6 (5) left censor: every session in [t0-59, t0] has benchmark sigma60 (P2: candidate sigma60 too).
I7 (5) fill price P = close_f * 1.001; R_H, MAE_H need f+H inside the data.
I8 (6) pairs = G and X1' R60 and MAE60 complete. c = numpy.percentile(., 10) linear. d (C) = median R60 G (W)
   - median R60 G (V0), each on its own pairs, inside the same sub-sample.
I9 (8 S4) window_exit episodes: G = not bought; a, b, d on pairs without them; c, c' on pairs + window_exit with G = 0.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import inspect
import json
import math
import random
import statistics
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(sys.argv[sys.argv.index("--repo") + 1]) if "--repo" in sys.argv else Path(".")
SCRIPTS = REPO / "manage-us-stock-strategy" / "scripts"
BT = REPO / "stock-strategy-system" / "backtests"
KR = BT / "fx5b_inputs_2026-10-09" / "kiwoom_raw"
PREREG_SHA = "18cf5799692ded3eb4a671e42cfec7100714f0c76f225e902d5fc57a688c3ee1"
HASHES = {
    BT / "cpv_inputs_2026-10-01" / "SOX_yahoo_raw.csv": "a261cc8473368e29722a42fa120808d4f48ccdfc4d6ba91826ec0831e2f95167",
    BT / "soxl_signal_inputs_2026-10-01" / "SOXX_combined.csv": "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6",
    KR / "MU_kiwoom_usa06012_daily_adj1_20261009.json": "db9f9fa7a9e0492b5521ba8b7b10eb30a05005495417185622338f75f5359cc1",
    KR / "LITE_kiwoom_usa06012_daily_adj1_20261009.json": "d81ede0bb41ea3f692185352045ff721134085046dce256e52d0529ef3fbe193",
    KR / "DELL_kiwoom_usa06012_daily_adj1_20261009.json": "982a91b232255bf36f6affa75a0c134278df213aab35a18efa1e4cc087ae30cd",
    KR / "BE_kiwoom_usa06012_daily_adj1_20261009.json": "4f1f9aba713a05f63af24f9d81fbf1762e5953cab4f02856b5f03b3ab1de6426",
    KR / "PWR_kiwoom_usa06012_daily_adj1_20261009.json": "02d9c7d2b0b451581d5df10ea099134fd0a9dc5b82a112aaec32e273eecafc27",
    KR / "GRID_kiwoom_usa06012_daily_adj1_20261009.json": "538d94e6efba6e0114a98cffae7e65f9f8b0d7d7b7ca787a5fa79493bce8b50f",
    SCRIPTS / "auto_core_rules.py": "511c8a13ca3da46e5f4bb39a80e12ca3b72b6f23766e78948eed92a43aebe56a",
    SCRIPTS / "portfolio_exposure.py": "81130d05c8ab7a96d2368aa456a2224fb44ee998e9385257e4e28a683f17a75a",
}
SECTORS = {"MU": "B1 메모리", "LITE": "A3 광부품", "DELL": "AI 서버",
           "PWR": "A1 전력(그리드 시공)", "BE": "A1 전력(온사이트)"}
CANDIDATES = ["MU", "LITE", "DELL", "BE", "PWR"]
KEEP = 130
COST = 1.001
VARIANTS = ["V0", "W1", "W2", "W3"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ production code import (I1)
def load_rules():
    src = (SCRIPTS / "portfolio_exposure.py").read_text(encoding="utf-8")
    fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_sample_std"][0]
    seg = ast.get_source_segment(src, fn)
    lines = src.splitlines()
    assert "\n".join(lines[235:240]) == seg, "_sample_std is not lines 236-240"
    stub = types.ModuleType("portfolio_exposure")
    exec(compile("import math\n" + seg, "portfolio_exposure_sample_std", "exec"), stub.__dict__)
    sys.modules["portfolio_exposure"] = stub
    sys.path.insert(0, str(SCRIPTS))
    import auto_core_rules as rules  # noqa: E402
    return rules, seg


RULES, STD_SRC = None, None


def make_w2(rules):
    """W2 copy of rrec1 (4-1). REBASE False executes the production lines."""
    src = inspect.getsource(rules.rrec1)
    patches = [
        ('    def ds1(i: int) -> bool | None:\n'
         '        return _any(_cmp(s["close"][i], "lt", l0), _cmp(s["close"][i], "lt", s["ema50"][i]))\n',
         '    ref = {"l": l0, "c": c0, "since": e, "today": False}\n\n'
         '    def ds1(i: int) -> bool | None:\n'
         '        if REBASE:\n'
         '            if ref["today"]:\n'
         '                return True\n'
         '            return _any(_cmp(s["close"][i], "lt", ref["l"]), _cmp(s["close"][i], "lt", s["ema50"][i]))\n'
         '        return _any(_cmp(s["close"][i], "lt", l0), _cmp(s["close"][i], "lt", s["ema50"][i]))\n'),
        ('        lows = [s["low"][k] for k in range(e + 1, i + 1)]\n'
         '        no_new_low = None if any(low is None for low in lows) else all(low >= l0 for low in lows)\n',
         '        if REBASE:\n'
         '            lows = [s["low"][k] for k in range(ref["since"] + 1, i + 1)]\n'
         '            no_new_low = None if any(low is None for low in lows) else all(low >= ref["l"] for low in lows)\n'
         '        else:\n'
         '            lows = [s["low"][k] for k in range(e + 1, i + 1)]\n'
         '            no_new_low = None if any(low is None for low in lows) else all(low >= l0 for low in lows)\n'),
        ('_all(*[_cmp(s["close"][k], "gt", c0) for k in range(i - two + 1, i + 1)])',
         '_all(*[_cmp(s["close"][k], "gt", ref["c"] if REBASE else c0) for k in range(i - two + 1, i + 1)])'),
        ('    for i in range(e + 1, t + 1):\n        flag = ds1(i)\n',
         '    for i in range(e + 1, t + 1):\n'
         '        ref["today"] = False\n'
         '        if REBASE and _cmp(s["low"][i], "lt", ref["l"]):\n'
         '            ref.update(l=s["low"][i], c=s["close"][i], since=i, today=True)\n'
         '        flag = ds1(i)\n'),
        ('    out["ds1"] = ds1_seen\n',
         '    out["ds1"] = ds1_seen\n'
         '    if REBASE:\n'
         '        out["rebase"] = {"c": ref["c"], "l": ref["l"], "since": s["days"][ref["since"]]}\n'),
    ]
    for old, new in patches:
        assert src.count(old) == 1, old[:60]
        src = src.replace(old, new)
    src = src.replace("def rrec1(", "def rrec1_w2(", 1)
    namespace = dict(rules.__dict__)  # same C dict object -> W1 constants apply to the copy too
    namespace["REBASE"] = True
    exec(compile(src, "rrec1_w2", "exec"), namespace)
    return namespace


class RG4Off:
    def __init__(self, rules, on: bool):
        self.rules, self.on = rules, on

    def __enter__(self):
        self.saved = (self.rules.C["RREC_RG4_DAY_SIGMA"], self.rules.C["RREC_RG4_SHORT_RATIO"])
        if self.on:
            self.rules.C["RREC_RG4_DAY_SIGMA"] = float("inf")
            self.rules.C["RREC_RG4_SHORT_RATIO"] = float("inf")

    def __exit__(self, *exc):
        self.rules.C["RREC_RG4_DAY_SIGMA"], self.rules.C["RREC_RG4_SHORT_RATIO"] = self.saved
        return False


# ------------------------------------------------------------------ data (2-2)
def load_sox():
    rows = list(csv.DictReader(open(BT / "cpv_inputs_2026-10-01" / "SOX_yahoo_raw.csv", encoding="utf-8")))
    return {r["date"]: {"open": float(r["open"]), "close": float(r["close"]), "high": float(r["high"]),
                        "low": float(r["low"]), "volume": float(r["volume"])} for r in rows}


def load_soxx():
    out = {}
    for r in csv.DictReader(open(BT / "soxl_signal_inputs_2026-10-01" / "SOXX_combined.csv", encoding="utf-8")):
        f = float(r["adjclose"]) / float(r["close"])
        out[r["date"]] = {"open": float(r["open"]) * f, "close": float(r["close"]) * f, "high": float(r["high"]) * f,
                          "low": float(r["low"]) * f, "volume": float(r["volume"])}
    return out


def load_kiwoom(symbol: str):
    path = next(KR.glob(f"{symbol}_kiwoom_usa06012_daily_adj1_*.json"))
    out = {}
    for x in json.loads(path.read_text(encoding="utf-8"))["result"]["result_list"]:
        d = f"{x['dt'][:4]}-{x['dt'][4:6]}-{x['dt'][6:]}"
        out[d] = {"open": float(x["open_pric"]), "close": float(x["cur_prc"]), "high": float(x["high_pric"]),
                  "low": float(x["low_pric"]), "volume": float(x["acc_trde_qty"] or 0)}
    return out


def series_on(bars: dict, days: list[str]):
    rules = RULES
    sub = {"sessions": {d: bars[d] for d in days}}
    return rules.build_series(sub, days, days[-1])


def view(s: dict, t: int):
    lo = max(0, t - KEEP + 1)
    return {k: v[lo:t + 1] for k, v in s.items()}


# ------------------------------------------------------------------ runs
def run_status(bench, cand, rg2, variant: str, w2ns, start: int, symbol=None, rebase_override=None):
    """Per-session rrec1 output for sessions start..end (stateless per session)."""
    rules = RULES
    use_w2 = variant in ("W2", "W3") or rebase_override is not None
    fn = w2ns["rrec1_w2"] if use_w2 else rules.rrec1
    if use_w2:
        w2ns["REBASE"] = True if rebase_override is None else rebase_override
    out = {}
    with RG4Off(rules, variant in ("W1", "W3")):
        for t in range(start, len(bench["days"])):
            kwargs = dict(benchmark=view(bench, t), candidate=None if cand is None else view(cand, t),
                          evaluation_session=bench["days"][t], ev3_user_dates=[], thesis_damage=[], ev4_sessions=[],
                          candidate_symbol=symbol, research_sessions=None)
            if rg2 is not None:
                kwargs["rg2_series"] = view(rg2, t)
            out[t] = fn(**kwargs)
    return out


def episodes(bench, cand, status: dict, start: int, price: dict, t0_from: str, t0_to: str):
    days = bench["days"]
    n = len(days)
    allowed = {t: status[t]["status"] == "ok" for t in status}
    eps, left, right = [], 0, 0
    for t in range(start + 1, n):
        if not (allowed[t - 1] and not allowed[t]):
            continue
        if not (t0_from <= days[t] <= t0_to):
            continue
        win = range(t - 59, t + 1)
        ok = all(k >= 0 and bench["sigma60"][k] is not None and (cand is None or cand["sigma60"][k] is not None)
                 for k in win)
        if not ok:
            left += 1
            continue
        u = next((k for k in range(t + 1, n) if allowed[k]), None)
        if u is None:
            right += 1
            continue
        o = status[u]
        if o.get("closed_at") == days[u]:
            kind = "open" if all(v == "ok" for v in o["rg"].values()) else "decay"
        elif o.get("closed_at") is None and not o["open"]:
            kind = "window_exit"
        else:
            kind = "other:" + str(o.get("closed_at"))
        ep = {"t0": days[t], "u": days[u], "kind": kind, "delay": u + 1 - t,
              "x1p": metrics(price, t + 1), "g": metrics(price, u + 1), "x1": metrics(price, t),
              "low_break": low_break(bench, status, t, u)}
        ep["missed"] = (None if ep["g"]["P"] is None or ep["x1p"]["P"] is None else ep["g"]["P"] / ep["x1p"]["P"] - 1)
        eps.append(ep)
    return eps, left, right


def low_break(bench, status, t0, u):
    """D3: on some blocked session the regular low after the event went below the event L0."""
    days = bench["days"]
    for k in range(t0, u):
        ev = status[k].get("event")
        if not ev or ev.get("l0") is None:
            continue
        e = days.index(ev["date"], max(0, k - 70), k + 1)
        if any(bench["low"][j] < ev["l0"] for j in range(e + 1, k + 1)):
            return True
    return False


def metrics(price: dict, f: int):
    c, lo = price["close"], price["low"]
    n = len(c)
    if f >= n:
        return {"P": None, "R20": None, "R60": None, "MAE20": None, "MAE60": None}
    p = c[f] * COST
    out = {"P": p}
    for h in (20, 60):
        if f + h < n:
            out[f"R{h}"] = c[f + h] / p - 1
            out[f"MAE{h}"] = min(lo[f + 1:f + h + 1]) / p - 1
        else:
            out[f"R{h}"] = out[f"MAE{h}"] = None
    return out


# ------------------------------------------------------------------ criteria (6, 8 S4)
def med(x):
    return statistics.median(x) if x else None


def pct10(x):
    return float(np.percentile(x, 10)) if x else None


def evaluate(eps: list[dict], reading: str):
    pairs = [e for e in eps if all(e[a][k] is not None for a in ("g", "x1p") for k in ("R60", "MAE60"))]
    if reading == "S4":
        judge = [e for e in pairs if e["kind"] != "window_exit"]
        tail = [e for e in eps if e["x1p"]["R60"] is not None and e["x1p"]["MAE60"] is not None
                and (e["kind"] == "window_exit" or e in pairs)]
        g_tail = [0.0 if e["kind"] == "window_exit" else e["g"]["MAE60"] for e in tail]
    else:
        judge = pairs
        tail = pairs
        g_tail = [e["g"]["MAE60"] for e in tail]
    res = {"episodes": len(eps), "kinds": {k: sum(1 for e in eps if e["kind"] == k)
                                           for k in sorted({e["kind"] for e in eps})},
           "pairs": len(judge), "tail_n": len(tail)}
    if not judge:
        return res
    gm, xm = [e["g"]["MAE60"] for e in judge], [e["x1p"]["MAE60"] for e in judge]
    gr, xr = [e["g"]["R60"] for e in judge], [e["x1p"]["R60"] for e in judge]
    res.update(a=med(gm) - med(xm), b=med(gr) - med(xr), c=pct10(g_tail) - pct10([e["x1p"]["MAE60"] for e in tail]),
               g_R60=med(gr), x1p_R60=med(xr), g_MAE60=med(gm), x1p_MAE60=med(xm),
               delay_median=med([e["delay"] for e in judge]),
               delay_q=[float(np.percentile([e["delay"] for e in judge], q)) for q in (25, 50, 75)],
               missed_median=med([e["missed"] for e in judge]),
               x1_R60=med([e["x1"]["R60"] for e in judge if e["x1"]["R60"] is not None]),
               g_tail_p10=pct10(g_tail), x1p_tail_p10=pct10([e["x1p"]["MAE60"] for e in tail]),
               g_tail_worst=min(g_tail), x1p_tail_worst=min(e["x1p"]["MAE60"] for e in tail),
               window_exit_share=sum(1 for e in judge if e["kind"] == "window_exit") / len(judge),
               low_break=sum(1 for e in eps if e["low_break"]))
    return res


def verdict(table: dict, reading: str):
    """table[sample][variant] -> evaluate() output. Samples: P1, P1a, P1b, P2."""
    out = {}
    def ok15(r):
        return r.get("pairs", 0) >= 15 and "a" in r
    for v in VARIANTS:
        steps = {}
        r1 = table["P1"][v]
        if not ok15(r1):
            out[v] = {"pass": False, "reason": "P1 sample short"}
            continue
        d1 = r1["g_R60"] - table["P1"]["V0"]["g_R60"]
        passed = [k for k in ("a", "c") if r1[k] >= 0.02]
        cprime = r1["c"] >= table["P1"]["V0"]["c"]
        steps["P1"] = {"b": r1["b"] >= -0.03, "a_or_c": passed, "c_prime": cprime, "d": d1, "d_ok": d1 > 0}
        c2 = steps["P1"]["b"] and bool(passed) and (cprime or v == "V0") and (d1 > 0)
        sub_ok = {}
        for smp in ("P1a", "P1b", "P2"):
            r = table[smp][v]
            if not ok15(r):
                sub_ok[smp] = {"ok": False, "reason": "sample short"}
                continue
            dd = r["g_R60"] - table[smp]["V0"]["g_R60"]
            sign = [k for k in passed if r[k] > 0]
            sub_ok[smp] = {"b": r["b"] >= -0.03, "d": dd, "d_ok": dd > 0, "sign_ok": sign,
                           "ok": r["b"] >= -0.03 and dd > 0 and bool(sign)}
        steps["subs"] = sub_ok
        out[v] = {"pass": c2 and all(x["ok"] for x in sub_ok.values()), "steps": steps}
    v0_all = out["V0"]["pass"]
    chosen = None if v0_all else next((v for v in ("W1", "W2", "W3") if out[v]["pass"]), None)
    return {"by_variant": out, "v0_passes_all": v0_all, "chosen": chosen}


# ------------------------------------------------------------------ main
def build_samples():
    sox, soxx = load_sox(), load_soxx()
    grid = load_kiwoom("GRID")
    samples = {}
    d = sorted(sox)
    s = series_on(sox, d)
    samples["SOX"] = {"bench": s, "cand": None, "rg2": None, "price": s, "symbol": None}
    d = sorted(soxx)
    s = series_on(soxx, d)
    samples["SOXX"] = {"bench": s, "cand": None, "rg2": None, "price": s, "symbol": None}
    for sym in CANDIDATES:
        cb = load_kiwoom(sym)
        g = RULES.rg2_benchmark(SECTORS[sym])
        days = sorted(set(soxx) & set(cb) & (set(grid) if g == "GRID" else set(soxx)))
        bench, cand = series_on(soxx, days), series_on(cb, days)
        rg2 = series_on(grid, days) if g == "GRID" else None
        assert bench["days"] == cand["days"] == days
        samples[sym] = {"bench": bench, "cand": cand, "rg2": rg2, "price": cand, "symbol": sym, "rg2_name": g}
    return samples


def first_eval(smp):
    keys = [smp["bench"]] + ([smp["cand"]] if smp["cand"] else []) + ([smp["rg2"]] if smp["rg2"] else [])
    return next(t for t in range(len(smp["bench"]["days"]))
                if all(x["sigma60"][t] is not None and x["ema50"][t] is not None for x in keys))


def compute(samples, w2ns, variants=VARIANTS):
    runs = {}
    for name, smp in samples.items():
        st = first_eval(smp)
        for v in variants:
            runs[(name, v)] = (st, run_status(smp["bench"], smp["cand"], smp["rg2"], v, w2ns, st, smp["symbol"]))
    return runs


def main_run(out_dir: Path):
    for p, h in HASHES.items():
        assert sha(p) == h, f"hash mismatch {p}"
    prereg = REPO / "docs" / "claude" / "r-rec1-r3-preregistration-2026-10-16.md"
    assert hashlib.sha256(prereg.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == PREREG_SHA
    samples = build_samples()
    w2ns = make_w2(RULES)
    runs = compute(samples, w2ns)
    ranges = {"SOX": ("0000-00-00", "2010-12-31"), "SOXX": ("2011-01-03", "2026-09-29")}
    eps = {}
    for (name, v), (st, status) in runs.items():
        lo, hi = ranges.get(name, ("2011-01-03", "2026-09-29"))
        e, left, right = episodes(samples[name]["bench"], samples[name]["cand"], status, st, samples[name]["price"], lo, hi)
        eps[(name, v)] = (e, left, right)
    results = {"prereg_sha256": PREREG_SHA, "readings": {}, "censor": {}, "first_eval": {}}
    for name, smp in samples.items():
        results["first_eval"][name] = smp["bench"]["days"][first_eval(smp)]
    for (name, v), (e, left, right) in eps.items():
        results["censor"][f"{name}/{v}"] = {"left": left, "right": right}
    for reading in ("main", "S4"):
        table = {}
        for v in VARIANTS:
            p1 = eps[("SOX", v)][0]
            p2 = [x for sym in CANDIDATES for x in eps[(sym, v)][0]]
            parts = {"P1": p1, "P1a": [x for x in p1 if x["t0"] <= "2002-12-31"],
                     "P1b": [x for x in p1 if x["t0"] >= "2003-01-01"], "P2": p2, "S1": eps[("SOXX", v)][0]}
            parts.update({f"S2_{sym}": eps[(sym, v)][0] for sym in CANDIDATES})
            for k, val in parts.items():
                table.setdefault(k, {})[v] = evaluate(val, reading)
        results["readings"][reading] = {"table": table, "verdict": verdict(table, reading)}
    main_c = results["readings"]["main"]["verdict"]["chosen"]
    s4_c = results["readings"]["S4"]["verdict"]["chosen"]
    results["final"] = {"main_chosen": main_c, "s4_chosen": s4_c,
                        "adopt_candidate": main_c if (main_c is not None and main_c == s4_c) else None}
    # D4: blocked share when SOXX close <= 0.9 x 60-session close high (V0, per candidate)
    d4 = {}
    for sym in CANDIDATES:
        st, status = runs[(sym, "V0")]
        b = samples[sym]["bench"]
        sel = [t for t in status if b["days"][t] >= "2011-01-03" and t >= 59
               and b["close"][t] <= 0.9 * max(b["close"][t - 59:t + 1])]
        d4[sym] = {"sessions": len(sel), "blocked_share": (sum(1 for t in sel if status[t]["status"] != "ok") / len(sel)) if sel else None}
    results["D4"] = d4
    # F2 off-session low proxy
    f2 = {}
    for name, smp in samples.items():
        for lab, ser in (("bench", smp["bench"]), ("cand", smp["cand"]), ("rg2", smp["rg2"])):
            if ser is None or (lab == "bench" and name in CANDIDATES):
                continue
            bars = {"SOX": load_sox, "SOXX": load_soxx}.get(name if lab == "bench" else "", None)
            src = bars() if bars else load_kiwoom(name if lab == "cand" else "GRID")
            f2[f"{name}/{lab}"] = sum(1 for d in ser["days"] if d >= "1994-07-29" and
                                      src[d]["low"] < 0.97 * min(src[d]["open"], src[d]["close"]))
    results["F2"] = f2
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "r_rec1_r3_replay_2026-10-16"
    (out_dir / f"{stem}_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8", newline="\n")
    with open(out_dir / f"{stem}_episodes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sample", "variant", "t0", "u", "kind", "delay", "low_break", "x1p_R60", "x1p_MAE60",
                    "g_R60", "g_MAE60", "x1_R60", "missed"])
        for (name, v), (e, _, _) in sorted(eps.items()):
            for x in e:
                w.writerow([name, v, x["t0"], x["u"], x["kind"], x["delay"], int(x["low_break"]),
                            x["x1p"]["R60"], x["x1p"]["MAE60"], x["g"]["R60"], x["g"]["MAE60"], x["x1"]["R60"],
                            x["missed"]])
    return results


def self_test():
    samples = build_samples()
    w2ns = make_w2(RULES)
    n_ok = 0
    # T1 W2 switch off == production on every evaluated session of every sample
    for name, smp in samples.items():
        st = first_eval(smp)
        prod = run_status(smp["bench"], smp["cand"], smp["rg2"], "V0", w2ns, st, smp["symbol"])
        off = run_status(smp["bench"], smp["cand"], smp["rg2"], "V0", w2ns, st, smp["symbol"], rebase_override=False)
        assert all(json.dumps(prod[t], sort_keys=True, default=str) == json.dumps(off[t], sort_keys=True, default=str)
                   for t in prod), name
        n_ok += 1
    # T2 sliced view == series rebuilt through t (no future data), 50 random sessions per sample
    rnd = random.Random(20261016)
    for name, smp in samples.items():
        st = first_eval(smp)
        b = smp["bench"]
        for t in rnd.sample(range(st, len(b["days"])), 50):
            days = b["days"][:t + 1]
            raw = {"SOX": load_sox, "SOXX": load_soxx}
            bb = series_on(raw[name]() if name in raw else load_soxx(), days)
            cc = None if smp["cand"] is None else series_on(load_kiwoom(name), days)
            gg = None if smp["rg2"] is None else series_on(load_kiwoom("GRID"), days)
            kw = dict(evaluation_session=days[-1], ev3_user_dates=[], thesis_damage=[], ev4_sessions=[],
                      candidate_symbol=smp["symbol"], research_sessions=None)
            full = RULES.rrec1(benchmark=bb, candidate=cc, **kw, **({"rg2_series": gg} if gg else {}))
            cut = RULES.rrec1(benchmark=view(b, t), candidate=None if cc is None else view(smp["cand"], t), **kw,
                              **({"rg2_series": view(smp["rg2"], t)} if gg else {}))
            assert json.dumps(full, sort_keys=True, default=str) == json.dumps(cut, sort_keys=True, default=str), (name, t)
        n_ok += 1
    # T3 W1 constants restored
    before = (RULES.C["RREC_RG4_DAY_SIGMA"], RULES.C["RREC_RG4_SHORT_RATIO"])
    with RG4Off(RULES, True):
        assert math.isinf(RULES.C["RREC_RG4_DAY_SIGMA"])
    assert (RULES.C["RREC_RG4_DAY_SIGMA"], RULES.C["RREC_RG4_SHORT_RATIO"]) == before == (2.0, 1.5)
    n_ok += 1
    # T4 W2 rebases on a synthetic intraday break (close above L0) and can reopen; production cannot
    closes, lows = [], []
    p = 100.0
    for i in range(130):
        p *= 1.006 if i % 2 == 0 else 0.999
        closes.append(p)
        lows.append(p * 0.997)
    e = len(closes)
    c0 = closes[-1] * 0.991                     # event day: -0.9% (EV1, not EV2, with a tiny sigma60)
    closes.append(c0); lows.append(c0 * 0.995)
    closes.append(c0 * 1.002); lows.append(lows[e] * 0.99)   # e+1: intraday low below L0, close above C0
    closes.append(c0 * 1.006); lows.append(c0 * 1.001)       # e+2
    closes.append(c0 * 1.010); lows.append(c0 * 1.004)       # e+3
    syn_days = [f"2000-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(len(closes))]
    bars = {"sessions": {d: {"close": c, "high": c * 1.003, "low": l, "volume": 1.0}
                         for d, c, l in zip(syn_days, closes, lows)}}
    sy = RULES.build_series(bars, syn_days, syn_days[-1])
    t = len(syn_days) - 1
    kw = dict(benchmark=view(sy, t), candidate=None, evaluation_session=syn_days[t], ev3_user_dates=[],
              thesis_damage=[], ev4_sessions=[], research_sessions=None)
    with RG4Off(RULES, True):
        prod = RULES.rrec1(**kw)
        w2ns["REBASE"] = True
        w3 = w2ns["rrec1_w2"](**kw)
    assert prod["events"][-1]["date"] == syn_days[e] and prod["rg"]["RG3"] == "no" and prod["status"] != "ok", prod
    assert w3["status"] == "ok" and w3.get("closed_at") == syn_days[t] and w3["rebase"]["since"] == syn_days[e + 1], w3
    n_ok += 1
    # T5 metrics / percentile / median
    pr = {"close": [100.0] * 70 + [110.0], "low": [90.0] * 71}
    m = metrics(pr, 0)
    assert abs(m["R60"] - (100 / 100.1 - 1)) < 1e-12 and abs(m["MAE60"] - (90 / 100.1 - 1)) < 1e-12
    assert pct10([0, 10]) == 1.0 and med([1, 2, 3, 4]) == 2.5
    n_ok += 1
    print(json.dumps({"self_test": "ok", "groups": n_ok, "std_src_bytes_match": True}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    RULES, STD_SRC = load_rules()
    if args.self_test:
        self_test()
    if args.run:
        r = main_run(Path(args.out) if args.out else BT)
        print(json.dumps(r["final"]))
