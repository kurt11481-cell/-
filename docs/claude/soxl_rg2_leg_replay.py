#!/usr/bin/env python3
"""SOXL RG2 candidate-leg replay (preregistration docs/claude/soxl-rg2-leg-preregistration-2026-11-24.md).

Historical computation only: no order tool, no policy/state/journal write, no network.
Usage: python soxl_rg2_leg_replay.py --repo <repo copy> --self-test | --run
V0 = production auto_core_rules.rrec1; VA / VB = source copies with only the RG2 line changed (prereg 3).
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import inspect
import json
import statistics
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(sys.argv[sys.argv.index("--repo") + 1]) if "--repo" in sys.argv else Path(".")
SCRIPTS = REPO / "manage-us-stock-strategy" / "scripts"
INP = REPO / "stock-strategy-system" / "backtests" / "soxl_signal_inputs_2026-10-01"
DOCS = REPO / "docs" / "claude"
PREREG = DOCS / "soxl-rg2-leg-preregistration-2026-11-24.md"
SIDECAR = DOCS / "soxl-rg2-leg-preregistration-2026-11-24.sha256"
OUT_JSON = DOCS / "soxl-rg2-leg-results.json"
HASHES = {
    INP / "SOXX_combined.csv": "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6",
    INP / "SOXL_combined.csv": "56e612b764a7c5df48b1f009efb300badba34dfc1d2cc262946a0d33a7502c24",
    SCRIPTS / "auto_core_rules.py": "ba979d234ea95644c6bb78456e8f500974060ab96c23f8dafe97281acaa4ea6a",
    SCRIPTS / "portfolio_exposure.py": "9a5360c58f55b18a36c906c011132588152e85cd20cce6bc768288a7a1b1fb09",
}
KEEP, COST, H = 130, 1.001, 60
T0_FROM, HALF, END = "2010-09-01", "2018-07-01", "2026-09-29"
RG2_LINE = "        rg2 = _all(bench_ok, cand_ok) if candidate is not None else bench_ok\n"
VA_LINE = "        rg2 = bench_ok\n"
VB_LINE = ("        cand_ok20 = None\n"
           "        if candidate is not None and s[\"days\"][i] in candidate[\"days\"]:\n"
           "            j20 = candidate[\"days\"].index(s[\"days\"][i])\n"
           "            cand_ok20 = _cmp(candidate[\"close\"][j20], \"ge\", candidate[\"ema20\"][j20])\n"
           "        rg2 = _all(bench_ok, cand_ok20) if candidate is not None else bench_ok\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rules():
    src = (SCRIPTS / "portfolio_exposure.py").read_text(encoding="utf-8")
    fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_sample_std"][0]
    stub = types.ModuleType("portfolio_exposure")
    exec(compile("import math\nfrom decimal import Decimal\n" + ast.get_source_segment(src, fn), "pe_std", "exec"),
         stub.__dict__)
    sys.modules["portfolio_exposure"] = stub
    sys.path.insert(0, str(SCRIPTS))
    import auto_core_rules as rules  # noqa: E402
    return rules


RULES = load_rules()


def variant_fn(line: str, name: str):
    src = inspect.getsource(RULES.rrec1)
    assert src.count(RG2_LINE) == 1, "RG2 anchor line not unique"
    src = src.replace(RG2_LINE, line).replace("def rrec1(", f"def {name}(", 1)
    ns = dict(RULES.__dict__)
    exec(compile(src, name, "exec"), ns)
    return ns[name]


FN = {"V0": RULES.rrec1, "V0copy": variant_fn(RG2_LINE, "rrec1_v0copy"),
      "VA": variant_fn(VA_LINE, "rrec1_va"), "VB": variant_fn(VB_LINE, "rrec1_vb")}


def load(path: Path):
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        f = float(r["adjclose"]) / float(r["close"])
        out[r["date"]] = {"open": float(r["open"]) * f, "close": float(r["close"]) * f, "high": float(r["high"]) * f,
                          "low": float(r["low"]) * f, "volume": float(r["volume"])}
    return out


def build(bench_bars, cand_bars):
    days = sorted(d for d in set(bench_bars) & set(cand_bars) if d <= END)
    b = RULES.build_series({"sessions": {d: bench_bars[d] for d in days}}, days, days[-1])
    c = RULES.build_series({"sessions": {d: cand_bars[d] for d in days}}, days, days[-1])
    assert b["days"] == days and c["days"] == days, "series not contiguous over common days"
    return days, b, c


def view(s, t):
    lo = max(0, t - KEEP + 1)
    return {k: v[lo:t + 1] for k, v in s.items()}


def statuses(name, b, c, start=130):
    fn, out = FN[name], {}
    for t in range(start, len(b["days"])):
        out[t] = fn(benchmark=view(b, t), candidate=view(c, t), evaluation_session=b["days"][t], ev3_user_dates=[],
                    thesis_damage=[], candidate_symbol="SOXL", research_sessions=None)
    return out


def kind(o, day):
    if o.get("closed_at") == day:
        return "open" if all(v == "ok" for v in o["rg"].values()) else "decay"
    if not o.get("events"):
        return "no_event_in_window"
    return "other"


def first_allowed(st, t0, n):
    return next((k for k in range(t0, n) if st[k]["status"] == "ok"), None)


def leg(price, f, end):
    """Return and MAE over (f, end] for a buy at close[f]*COST; cash (0, 0) when no buy inside the window."""
    if f is None or f >= end:
        return 0.0, 0.0
    p = price["close"][f] * COST
    return price["close"][end] / p - 1, min(price["low"][f + 1:end + 1]) / p - 1


def episodes(days, b, c, st):
    n = len(days)
    eps, censored = [], 0
    for t in range(131, n):
        if not (st["V0"][t - 1]["status"] == "ok" and st["V0"][t]["status"] != "ok"):
            continue
        if days[t] < T0_FROM:
            continue
        if not all(k >= 0 and b["sigma60"][k] is not None and c["sigma60"][k] is not None for k in range(t - 59, t + 1)):
            continue
        u = {v: first_allowed(st[v], t, n) for v in ("V0", "VA", "VB")}
        if u["VA"] is None or u["VA"] + 1 + H >= n:
            censored += 1
            continue
        fa = u["VA"] + 1
        end = fa + H
        ep = {"t0": days[t], "u": {v: (days[u[v]] if u[v] is not None else None) for v in u},
              "kind": {v: (kind(st[v][u[v]], days[u[v]]) if u[v] is not None else None) for v in u}}
        for v in ("V0", "VA", "VB"):
            f = None if u[v] is None else u[v] + 1
            r, m = leg(c, f if f is not None and f <= end else None, end)
            ep[v] = {"f": None if f is None else days[f] if f < n else None, "in_window": f is not None and f < end,
                     "R": r, "MAE": m}
        f0 = None if u["V0"] is None else u["V0"] + 1
        ep["d"] = None if f0 is None or f0 >= end else f0 - fa
        ep["binding"] = ep["d"] is None or ep["d"] >= 1
        fb = None if u["VB"] is None else u["VB"] + 1
        ep["d_vb"] = None if fb is None or fb >= end else f0 - fb if f0 is not None and f0 < end else None
        ep["dR_VA"] = ep["VA"]["R"] - ep["V0"]["R"]
        ep["dR_VB"] = ep["VB"]["R"] - ep["V0"]["R"]
        eps.append(ep)
    return eps, censored


def p10(x):
    return float(np.percentile(x, 10)) if x else None


def judge(eps, alt="VA"):
    B = [e for e in eps if e["binding"]] if alt == "VA" else [
        e for e in eps if e["VB"]["R"] != e["V0"]["R"] or e["VB"]["MAE"] != e["V0"]["MAE"]]
    res = {"episodes": len(eps), "binding": len(B)}
    if not B:
        return res
    dr = [e[f"dR_{alt}"] for e in B]
    ma, m0 = [e[alt]["MAE"] for e in B], [e["V0"]["MAE"] for e in B]
    res.update(dR_median=statistics.median(dr), dR_mean=statistics.fmean(dr),
               tail_alt=p10(ma), tail_v0=p10(m0), tail_diff=p10(ma) - p10(m0),
               worst_alt=min(ma), worst_v0=min(m0), worst_diff=min(ma) - min(m0))
    halves = {}
    for name, sel in (("first", lambda e: e["t0"] < HALF), ("second", lambda e: e["t0"] >= HALF)):
        hb = [e[f"dR_{alt}"] for e in B if sel(e)]
        halves[name] = {"n": len(hb), "dR_median": statistics.median(hb) if hb else None}
    res["halves"] = halves
    res["all_dR_mean"] = statistics.fmean([e[f"dR_{alt}"] for e in eps])
    res["all_dR_median"] = statistics.median([e[f"dR_{alt}"] for e in eps])
    return res


def verdict(r):
    if r["episodes"] < 30 or r["binding"] < 15:
        return "INCONCLUSIVE", {"reason": "sample short"}
    c = {"1_dR_median_ge_3pp": r["dR_median"] >= 0.03,
         "2_tail_diff_ge_-3pp": r["tail_diff"] >= -0.03,
         "3_halves_positive": all(h["n"] >= 5 and h["dR_median"] is not None and h["dR_median"] > 0
                                  for h in r["halves"].values()),
         "4_worst_diff_ge_-5pp": r["worst_diff"] >= -0.05}
    return ("CANDIDATE" if all(c.values()) else "BELOW_STANDARD"), c


def check_hashes():
    side = SIDECAR.read_text(encoding="utf-8").split()
    assert side[0] == sha(PREREG), "preregistration hash mismatch"
    assert side[side.index("runner") + 1] == sha(Path(__file__)), "runner hash mismatch"
    for p, h in HASHES.items():
        assert sha(p) == h, f"input hash mismatch {p.name}"


def synthetic():
    """Prereg 7-4: SOXX above its EMA50, SOXL below its EMA50 -> V0 blocked, VA open."""
    import datetime as dt
    d0 = dt.date(2001, 1, 1)
    days = [(d0 + dt.timedelta(i)).isoformat() for i in range(200)]
    bb, cb = {}, {}
    for i, d in enumerate(days):
        x = 100 + 0.01 * i + (0.3 if i % 2 else -0.3)
        if i == 150:
            x = 90.0
        if i > 150:
            x = 110 + 0.01 * i + (0.3 if i % 2 else -0.3)
        bb[d] = {"open": x, "close": x, "high": x * 1.002, "low": x * 0.998 if i != 150 else 89.5, "volume": 1}
        y = 100 + (0.5 if i % 2 else -0.5) if i < 150 else 60.0 + (0.5 if i % 2 else -0.5)
        cb[d] = {"open": y, "close": y, "high": y * 1.002, "low": y * 0.998, "volume": 1}
    b = RULES.build_series({"sessions": bb}, days, days[-1])
    c = RULES.build_series({"sessions": cb}, days, days[-1])
    hit = False
    for t in range(160, 199):
        kw = dict(benchmark=view(b, t), candidate=view(c, t), evaluation_session=days[t], ev3_user_dates=[],
                  thesis_damage=[], candidate_symbol="SOXL", research_sessions=None)
        v0, va = FN["V0"](**kw), FN["VA"](**kw)
        if b["close"][t] >= b["ema50"][t] and c["close"][t] < c["ema50"][t] and va["status"] == "ok":
            assert v0["status"] != "ok", "synthetic: V0 should be blocked"
            hit = True
    assert hit, "synthetic: VA never opened while SOXL below EMA50"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    for p, h in HASHES.items():
        assert sha(p) == h, f"input hash mismatch {p.name}"
    synthetic()
    days, b, c = build(load(INP / "SOXX_combined.csv"), load(INP / "SOXL_combined.csv"))
    st = {v: statuses(v, b, c) for v in ("V0", "V0copy", "VA", "VB")}
    for t in st["V0"]:
        x, y = st["V0"][t], st["V0copy"][t]
        assert (x["status"], x["open"], x["rg"], x.get("closed_at")) == (y["status"], y["open"], y["rg"], y.get("closed_at")), days[t]
        if x["status"] == "ok":
            assert st["VA"][t]["status"] == "ok", "V0 allowed but VA blocked " + days[t]
    print("self-test ok:", len(days), "days", days[0], days[-1], "evaluated", len(st["V0"]))
    if a.self_test:
        return
    check_hashes()
    assert not OUT_JSON.exists(), "results already exist (one run only)"
    eps, censored = episodes(days, b, c, st)
    ra, rb = judge(eps, "VA"), judge(eps, "VB")
    va, crit = verdict(ra) if ra.get("binding") else ("INCONCLUSIVE", {"reason": "no binding"})
    out = {"preregistration_sha256": sha(PREREG), "runner_sha256": sha(Path(__file__)),
           "inputs": {p.name: h for p, h in HASHES.items()}, "days": [days[0], days[-1], len(days)],
           "verdict_VA": va, "criteria": crit, "VA": ra, "VB_record_only": rb, "right_censored": censored,
           "episodes": eps}
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("verdict_VA", "criteria", "VA", "VB_record_only", "right_censored")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
