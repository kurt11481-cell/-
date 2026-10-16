#!/usr/bin/env python3
"""Independent reimplementation of r-rec1-r3-preregistration-2026-10-16 (sha256 3d3f5274...).

Written only from the preregistration and the listed inputs. Run: python3 -I indep_replay.py
"""
from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
import types
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path("/mnt/user-data/uploads/코덱스저장소")
OUT = Path("/tmp/claude-0/-home-claude/17519926-4835-5624-8e12-7efa59cbe4cb/scratchpad/indep")
PREREG = Path("/mnt/user-data/outputs/r-rec1-r3-preregistration-2026-10-16.md")
KW = "stock-strategy-system/backtests/fx5b_inputs_2026-10-09/kiwoom_raw/{}_kiwoom_usa06012_daily_adj1_20261009.json"
HASHES = {
    "stock-strategy-system/backtests/cpv_inputs_2026-10-01/SOX_yahoo_raw.csv": "a261cc8473368e29722a42fa120808d4f48ccdfc4d6ba91826ec0831e2f95167",
    "stock-strategy-system/backtests/soxl_signal_inputs_2026-10-01/SOXX_combined.csv": "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6",
    KW.format("MU"): "db9f9fa7a9e0492b5521ba8b7b10eb30a05005495417185622338f75f5359cc1",
    KW.format("LITE"): "d81ede0bb41ea3f692185352045ff721134085046dce256e52d0529ef3fbe193",
    KW.format("DELL"): "982a91b232255bf36f6affa75a0c134278df213aab35a18efa1e4cc087ae30cd",
    KW.format("BE"): "4f1f9aba713a05f63af24f9d81fbf1762e5953cab4f02856b5f03b3ab1de6426",
    KW.format("PWR"): "02d9c7d2b0b451581d5df10ea099134fd0a9dc5b82a112aaec32e273eecafc27",
    KW.format("GRID"): "538d94e6efba6e0114a98cffae7e65f9f8b0d7d7b7ca787a5fa79493bce8b50f",
    "manage-us-stock-strategy/scripts/auto_core_rules.py": "511c8a13ca3da46e5f4bb39a80e12ca3b72b6f23766e78948eed92a43aebe56a",
    "manage-us-stock-strategy/scripts/portfolio_exposure.py": "81130d05c8ab7a96d2368aa456a2224fb44ee998e9385257e4e28a683f17a75a",
}
PREREG_SHA = "3d3f52740f457005242a80288ffa3c657d79b9e4cae179b841db39197b6a3cc2"
SECTORS = {"MU": "B1 메모리", "LITE": "A3 광부품", "DELL": "AI 서버",
           "PWR": "A1 전력(그리드 시공)", "BE": "A1 전력(온사이트)"}
VARIANTS = ("V0", "W1", "W2", "W3")
SLICE = 130
COST = 1.001


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hashes() -> None:
    assert sha(PREREG) == PREREG_SHA, "prereg hash mismatch"
    for rel, want in HASHES.items():
        got = sha(REPO / rel)
        assert got == want, f"hash mismatch {rel}: {got}"


# --- module loading: portfolio_exposure stub with the _sample_std source extracted by ast -----------------

def load_rules():
    pe_path = REPO / "manage-us-stock-strategy/scripts/portfolio_exposure.py"
    raw = pe_path.read_bytes()
    text = raw.decode("utf-8")
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_sample_std")
    segment = ast.get_source_segment(text, node)
    # byte check: the segment equals lines 236..240 of the hashed file
    lines = raw.split(b"\n")
    want = b"\n".join(lines[235:240])
    seg_b = segment.encode("utf-8")
    assert node.lineno == 236 and node.end_lineno == 240, (node.lineno, node.end_lineno)
    # lines 236-240 joined by their own CRLF; the last line's CR is its line ending (not part of the segment)
    assert want.endswith(b"\r") and seg_b == want[:-1], "sample_std bytes differ"
    stub = types.ModuleType("portfolio_exposure")
    exec(compile("from __future__ import annotations\nimport math\n" + segment.replace("\r\n", "\n"),
                 "portfolio_exposure_stub", "exec"), stub.__dict__)
    sys.modules["portfolio_exposure"] = stub
    spec = importlib.util.spec_from_file_location(
        "auto_core_rules", REPO / "manage-us-stock-strategy/scripts/auto_core_rules.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_core_rules"] = mod
    spec.loader.exec_module(mod)
    return mod, segment


acr, SAMPLE_STD_SRC = load_rules()
C = acr.C
_all, _any, _cmp, _sample_std = acr._all, acr._any, acr._cmp, acr._sample_std


# --- W2 copy of rrec1 (rebase switch); with rebase=False it runs the production lines verbatim ----------

def rrec1_copy(*, benchmark, candidate, evaluation_session, ev3_user_dates, thesis_damage, ev4_sessions,
               candidate_symbol=None, research_sessions=None, rg2_series=acr.SAME_AS_BENCHMARK, rebase=False):
    out = {"status": "unk", "open": None, "events": [], "event": None, "rg": {}, "ds1": None,
           "benchmark": None, "reasons": [], "ev3b_coverage_start": None, "rg1_coverage": None}
    if benchmark is None or benchmark["days"][-1] != evaluation_session:
        out["reasons"].append("BENCHMARK_DATA_MISSING")
        return out
    s = benchmark
    t = len(s["close"]) - 1
    if s["sigma60"][t] is None:
        out["reasons"].append("BENCHMARK_SIGMA_UNAVAILABLE")
        return out
    window_start = max(0, t - C["RREC_WINDOW_SESSIONS"] + 1)
    coverage = None if research_sessions is None else set(research_sessions)
    gaps = []
    if coverage is not None:
        recorded = [s["days"][i] for i in range(window_start, t + 1) if s["days"][i] in coverage]
        out["ev3b_coverage_start"] = recorded[0] if recorded else None
        for i in range(window_start, t + 1):
            day, sigma, ret = s["days"][i], s["sigma60"][i], s["ret1"][i]
            if recorded and day >= recorded[0] and day not in coverage and (
                    sigma is None or ret is None or ret <= -C["RREC_EV3_SIGMA"] * sigma):
                gaps.append(day)

    def settle(result):
        if gaps:
            result.update(status="unk", open=None)
            result["reasons"].append("EV3B_RECORD_GAP:" + ",".join(gaps))
        return result

    damage_days = {fact["event_session"] for fact in thesis_damage or []}
    events = []
    for i in range(window_start, t + 1):
        sigma, ret = s["sigma60"][i], s["ret1"][i]
        day = s["days"][i]
        kinds = []
        if sigma is not None and ret is not None and ret <= -C["RREC_EV1_SIGMA"] * sigma:
            kinds.append("EV1")
        if sigma is not None and s["hi20"][i] is not None and s["close"][i] <= s["hi20"][i] * (1 - C["RREC_EV2_SIGMA"] * sigma):
            kinds.append("EV2")
        if day in ev3_user_dates:
            kinds.append("EV3a")
        if day in damage_days and sigma is not None and ret is not None and ret <= -C["RREC_EV3_SIGMA"] * sigma:
            kinds.append("EV3b")
        if day in ev4_sessions:
            kinds.append("EV4")
        if candidate is not None and day in candidate["days"]:
            j = candidate["days"].index(day)
            c_sigma, c_ret = candidate["sigma60"][j], candidate["ret1"][j]
            if c_sigma is not None and c_ret is not None and c_ret <= -C["RREC_EV5_SIGMA"] * c_sigma:
                kinds.append("EV5")
        if kinds:
            events.append({"index": i, "date": day, "kinds": kinds})
    out["events"] = [{"date": item["date"], "kinds": item["kinds"]} for item in events]
    if not events:
        out.update(status="ok", open=False)
        return settle(out)
    event = events[-1]
    e = event["index"]
    c0 = s["close"][e]
    l0 = s["low"][e]
    out["event"] = {"date": event["date"], "kinds": event["kinds"], "c0": c0, "l0": l0, "bench": None}
    first = out["ev3b_coverage_start"]

    def needs_record(day):
        return first is None or day >= first

    if coverage is not None:
        out["rg1_coverage"] = {"from": s["days"][e + 1] if e < t else None, "to": s["days"][t],
                               "missing_sessions": [s["days"][k] for k in range(e + 1, t + 1)
                                                    if s["days"][k] not in coverage and needs_record(s["days"][k])]}
        before = [s["days"][k] for k in range(e + 1, t + 1) if not needs_record(s["days"][k])]
        if before:
            out["rg1_coverage"]["before_first_record"] = before
    if l0 is None:
        out["reasons"].append("EVENT_LOW_UNAVAILABLE")
        out.update(status="unk", open=True)
        return settle(out)

    # W2 state: reference low/close, whether an unknown low was seen, whether day i rebased
    ref = {"l": l0, "c": c0, "low_unknown": False, "rebased_today": False}

    def ds1(i):
        if not rebase:  # production 858-859
            return _any(_cmp(s["close"][i], "lt", l0), _cmp(s["close"][i], "lt", s["ema50"][i]))
        return _any(True if ref["rebased_today"] else False,
                    _cmp(s["close"][i], "lt", ref["l"]), _cmp(s["close"][i], "lt", s["ema50"][i]))

    def gates(i, last_ds1):
        damage_after = None if thesis_damage is None else any(
            fact["event_session"] > s["days"][e] and fact["event_session"] <= s["days"][i] for fact in thesis_damage)
        recorded = coverage is None or all(s["days"][k] in coverage for k in range(e + 1, i + 1)
                                           if needs_record(s["days"][k]))
        rg1 = None if damage_after is None else False if damage_after else _all(
            i - e >= C["RREC_RG1_SESSIONS"], True if recorded else None)
        if rg2_series is acr.SAME_AS_BENCHMARK:
            bench_ok = _cmp(s["close"][i], "ge", s["ema50"][i])
        else:
            bench_ok = None
            if rg2_series is not None and s["days"][i] in rg2_series["days"]:
                g = rg2_series["days"].index(s["days"][i])
                bench_ok = _cmp(rg2_series["close"][g], "ge", rg2_series["ema50"][g])
        cand_ok = None
        if candidate is not None and s["days"][i] in candidate["days"]:
            j = candidate["days"].index(s["days"][i])
            cand_ok = _cmp(candidate["close"][j], "ge", candidate["ema50"][j])
        rg2 = _all(bench_ok, cand_ok) if candidate is not None else bench_ok
        start = max(e, last_ds1)
        two = C["RREC_RG3_SESSIONS"]
        if not rebase:  # production 883-887
            lows = [s["low"][k] for k in range(e + 1, i + 1)]
            no_new_low = None if any(low is None for low in lows) else all(low >= l0 for low in lows)
            rg3 = _all(i - start >= two, _all(*[_cmp(s["close"][k], "gt", c0) for k in range(i - two + 1, i + 1)])
                       if i - start >= two else False, no_new_low)
        else:
            no_new_low = None if ref["low_unknown"] else True
            cref = ref["c"]
            rg3 = _all(i - start >= two, _all(*[_cmp(s["close"][k], "gt", cref) for k in range(i - two + 1, i + 1)])
                       if i - start >= two else False, no_new_low)
        sigma, ret = s["sigma60"][i], s["ret1"][i]
        short = s["ret1"][i - C["RREC_RG4_SHORT_SESSIONS"] + 1:i + 1]
        short_sigma = None if any(value is None for value in short) else _sample_std(short)
        rg4 = None if sigma is None or ret is None or short_sigma is None else (
            abs(ret) <= C["RREC_RG4_DAY_SIGMA"] * sigma and short_sigma <= C["RREC_RG4_SHORT_RATIO"] * sigma)
        return {"RG1": rg1, "RG2": rg2, "RG3": rg3, "RG4": rg4}

    last_ds1 = e
    ds1_seen = None
    closed_at = None
    current = {}
    for i in range(e + 1, t + 1):
        if rebase:
            ref["rebased_today"] = False
            low = s["low"][i]
            if low is None:
                ref["low_unknown"] = True
            elif low < ref["l"]:
                ref["l"], ref["c"], ref["rebased_today"] = low, s["close"][i], True
        flag = ds1(i)
        if flag:
            last_ds1, ds1_seen = i, s["days"][i]
        current = gates(i, last_ds1)
        if all(value is True for value in current.values()):
            closed_at = s["days"][i]
            break
        if i - last_ds1 >= C["RREC_CLOSE_SESSIONS"] and current["RG2"] is True:
            closed_at = s["days"][i]
            break
    if e == t:
        current = gates(t, e)
    out["ds1"] = ds1_seen
    out["rg"] = {key: ("ok" if value is True else "no" if value is False else "unk") for key, value in current.items()}
    if rebase:
        out["rebase"] = {"c_ref": ref["c"], "l_ref": ref["l"]}
    if closed_at is not None:
        out.update(status="ok", open=False, closed_at=closed_at)
        return settle(out)
    out["open"] = True
    out["status"] = "ok" if all(value is True for value in current.values()) else (
        "unk" if any(value is None for value in current.values()) else "no")
    return settle(out)


# --- data ---------------------------------------------------------------------------------------------

def load_csv(rel, adjust):
    sessions = {}
    with open(REPO / rel, newline="") as fh:
        for row in csv.DictReader(fh):
            def num(k):
                v = row[k]
                return None if v in ("", "nan", "NaN", "None") else float(v)
            close = num("close")
            f = (num("adjclose") / close) if adjust else 1.0
            hi, lo = num("high"), num("low")
            sessions[row["date"]] = {"close": close * f, "high": None if hi is None else hi * f,
                                     "low": None if lo is None else lo * f, "volume": num("volume")}
    return sessions


def load_kw(sym):
    d = json.loads((REPO / KW.format(sym)).read_text())
    sessions = {}
    for r in d["result"]["result_list"]:
        day = f"{r['dt'][:4]}-{r['dt'][4:6]}-{r['dt'][6:]}"

        def num(k):
            v = r[k]
            return None if v in ("", None) else float(v)
        sessions[day] = {"close": num("cur_prc"), "high": num("high_pric"), "low": num("low_pric"),
                         "volume": num("acc_trde_qty")}
    return dict(sorted(sessions.items()))


def restrict(sessions, days):
    return {"sessions": {d: sessions[d] for d in days}}


def slice_series(series, t):
    lo = max(0, t - SLICE + 1)
    return {k: v[lo:t + 1] for k, v in series.items()}


# --- evaluation of one sample (worker) ----------------------------------------------------------------

def call(variant, bench, cand, day, rg2):
    kwargs = dict(benchmark=bench, candidate=cand, evaluation_session=day, ev3_user_dates=[], thesis_damage=[],
                  ev4_sessions=[], candidate_symbol=None, research_sessions=None)
    if rg2 is not None:
        kwargs["rg2_series"] = rg2
    w1 = variant in ("W1", "W3")
    if w1:
        saved = (C["RREC_RG4_DAY_SIGMA"], C["RREC_RG4_SHORT_RATIO"])
        C["RREC_RG4_DAY_SIGMA"] = float("inf")
        C["RREC_RG4_SHORT_RATIO"] = float("inf")
    try:
        if variant in ("V0", "W1"):
            return acr.rrec1(**kwargs)
        if variant == "COPY_OFF":
            return rrec1_copy(**kwargs, rebase=False)
        return rrec1_copy(**kwargs, rebase=True)
    finally:
        if w1:
            C["RREC_RG4_DAY_SIGMA"], C["RREC_RG4_SHORT_RATIO"] = saved


def build_sample(name):
    """Return dict with bench/cand/rg2 full series, days, eval start index and price arrays."""
    sox = None
    if name == "P1":
        sox = load_csv("stock-strategy-system/backtests/cpv_inputs_2026-10-01/SOX_yahoo_raw.csv", adjust=False)
        days = list(sox)
        bars = {"sessions": sox}
        bench = acr.build_series(bars, days, days[-1])
        return {"name": name, "days": days, "bench_bars": bars, "bench": bench, "cand": None, "cand_bars": None,
                "rg2": None, "rg2_bars": None, "price": bench}
    soxx = load_csv("stock-strategy-system/backtests/soxl_signal_inputs_2026-10-01/SOXX_combined.csv", adjust=True)
    if name == "S1":
        days = list(soxx)
        bars = {"sessions": soxx}
        bench = acr.build_series(bars, days, days[-1])
        return {"name": name, "days": days, "bench_bars": bars, "bench": bench, "cand": None, "cand_bars": None,
                "rg2": None, "rg2_bars": None, "price": bench}
    sym = name.split(":")[1]
    cand_raw = load_kw(sym)
    power = acr.rg2_benchmark(SECTORS[sym]) == "GRID"
    grid_raw = load_kw("GRID") if power else None
    common = set(soxx) & set(cand_raw)
    if power:
        common &= set(grid_raw)
    days = sorted(common)
    bb, cb = restrict(soxx, days), restrict(cand_raw, days)
    bench = acr.build_series(bb, days, days[-1])
    cand = acr.build_series(cb, days, days[-1])
    rg2 = rg2b = None
    if power:
        rg2b = restrict(grid_raw, days)
        rg2 = acr.build_series(rg2b, days, days[-1])
    else:
        rg2b, rg2 = bb, bench  # rg2_benchmark = SOXX: pass the SOXX series explicitly (as decide does)
    assert len(bench["days"]) == len(days) == len(cand["days"])
    return {"name": name, "days": days, "bench_bars": bb, "bench": bench, "cand": cand, "cand_bars": cb,
            "rg2": rg2, "rg2_bars": rg2b, "price": cand}


def eval_start(smp):
    n = len(smp["days"])
    series = [smp["bench"]] + ([smp["cand"]] if smp["cand"] else []) + (
        [smp["rg2"]] if smp["rg2"] is not None and smp["rg2"] is not smp["bench"] else [])
    for t in range(n):
        if all(s["sigma60"][t] is not None and s["ema50"][t] is not None for s in series):
            return t
    raise RuntimeError


def run_sample(args):
    name, variants = args
    smp = build_sample(name)
    n = len(smp["days"])
    t_start = eval_start(smp)
    results = {v: [None] * n for v in variants}
    for t in range(t_start, n):
        day = smp["days"][t]
        b = slice_series(smp["bench"], t)
        c = slice_series(smp["cand"], t) if smp["cand"] else None
        r = None
        if smp["rg2"] is not None:
            r = b if smp["rg2"] is smp["bench"] else slice_series(smp["rg2"], t)
        for v in variants:
            results[v][t] = call(v, b, c, day, r)
    return name, t_start, results


def self_test_slices(name, k=50, seed=7):
    """rrec1 on a fresh build_series through t == rrec1 on the sliced view (random sessions), all variants."""
    smp = build_sample(name)
    n = len(smp["days"])
    t0 = eval_start(smp)
    rnd = random.Random(seed)
    picks = rnd.sample(range(t0, n), k)
    bad = 0
    for t in picks:
        day = smp["days"][t]
        fb = acr.build_series(smp["bench_bars"], smp["days"], day)
        fc = acr.build_series(smp["cand_bars"], smp["days"], day) if smp["cand"] else None
        fr = None
        if smp["rg2"] is not None:
            fr = fb if smp["rg2"] is smp["bench"] else acr.build_series(smp["rg2_bars"], smp["days"], day)
        b = slice_series(smp["bench"], t)
        c = slice_series(smp["cand"], t) if smp["cand"] else None
        r = None if smp["rg2"] is None else (b if smp["rg2"] is smp["bench"] else slice_series(smp["rg2"], t))
        for v in VARIANTS:
            if call(v, fb, fc, day, fr) != call(v, b, c, day, r):
                bad += 1
    return bad


# --- episodes and metrics -----------------------------------------------------------------------------

def episodes_for(smp, t_start, res, t0_lo, t0_hi):
    days, n = smp["days"], len(smp["days"])
    bench, cand = smp["bench"], smp["cand"]
    allowed = [None if r is None else (r["status"] == "ok") for r in res]
    pc, pl = smp["price"]["close"], smp["price"]["low"]
    eps = []
    left = right = 0
    for t0 in range(t_start + 1, n):
        if not (allowed[t0 - 1] is True and allowed[t0] is False):
            continue
        if not (t0_lo <= days[t0] <= t0_hi):
            continue
        w = range(t0 - 59, t0 + 1)
        ok = t0 - 59 >= 0 and all(bench["sigma60"][k] is not None for k in w) and (
            cand is None or all(cand["sigma60"][k] is not None for k in w))
        if not ok:
            left += 1
            continue
        u = next((k for k in range(t0 + 1, n) if allowed[k]), None)
        if u is None:
            right += 1
            continue
        ru = res[u]
        if ru.get("closed_at") == days[u]:
            kind = "open" if all(ru["rg"].get(g) == "ok" for g in ("RG1", "RG2", "RG3", "RG4")) else "decay"
        elif ru.get("closed_at") is None and not ru["events"]:
            kind = "window"
        else:
            raise RuntimeError(("unexpected end", days[u], ru))

        def arm(f):
            outv = {}
            if f >= n:
                return {"P": None, "f": f, "R20": None, "R60": None, "MAE20": None, "MAE60": None}
            P = pc[f] * COST
            outv["P"], outv["f"] = P, f
            for H in (20, 60):
                if f + H < n and all(pl[k] is not None for k in range(f + 1, f + H + 1)):
                    outv[f"R{H}"] = pc[f + H] / P - 1
                    outv[f"MAE{H}"] = min(pl[k] for k in range(f + 1, f + H + 1)) / P - 1
                else:
                    outv[f"R{H}"] = outv[f"MAE{H}"] = None
            return outv
        g, x1p, x1 = arm(u + 1), arm(t0 + 1), arm(t0)
        eps.append({"t0": days[t0], "t0i": t0, "u": days[u], "kind": kind, "fG": days[u + 1] if u + 1 < n else None,
                    "delay": u + 1 - t0, "G": g, "X1p": x1p, "X1": x1, "event": res[t0]["event"]})
    return eps, left, right


def pct10(x):
    return float(np.percentile(np.array(x, dtype=float), 10))


def metrics(eps, reading):
    pairs = [e for e in eps if None not in (e["G"]["R60"], e["G"]["MAE60"], e["X1p"]["R60"], e["X1p"]["MAE60"])]
    if reading == "main":
        abd = cset = pairs
        c_g = [e["G"]["MAE60"] for e in cset]
    else:  # S4
        abd = [e for e in pairs if e["kind"] != "window"]
        win = [e for e in eps if e["kind"] == "window" and None not in (e["X1p"]["R60"], e["X1p"]["MAE60"])]
        cset = abd + win
        c_g = [e["G"]["MAE60"] for e in abd] + [0.0] * len(win)
    out = {"pairs_N": len(pairs), "abd_N": len(abd), "c_N": len(cset)}
    if not abd or not cset:
        out.update(a=None, b=None, c=None, d=None)
        return out
    med = statistics.median
    out["G_MAE60_med"] = med(e["G"]["MAE60"] for e in abd)
    out["X1p_MAE60_med"] = med(e["X1p"]["MAE60"] for e in abd)
    out["G_R60_med"] = med(e["G"]["R60"] for e in abd)
    out["X1p_R60_med"] = med(e["X1p"]["R60"] for e in abd)
    out["a"] = out["G_MAE60_med"] - out["X1p_MAE60_med"]
    out["b"] = out["G_R60_med"] - out["X1p_R60_med"]
    out["G_MAE60_p10"] = pct10(c_g)
    out["X1p_MAE60_p10"] = pct10([e["X1p"]["MAE60"] for e in cset])
    out["c"] = out["G_MAE60_p10"] - out["X1p_MAE60_p10"]
    out["d"] = med(e["delay"] for e in abd)
    x1 = [e for e in abd if e["X1"]["R60"] is not None]
    out["X1_R60_med"] = med(e["X1"]["R60"] for e in x1) if x1 else None
    out["X1_MAE60_med"] = med(e["X1"]["MAE60"] for e in x1) if x1 else None
    out["missed_rebound_med"] = med(e["G"]["P"] / e["X1p"]["P"] - 1 for e in abd)
    out["N_arm_R60"] = 0.0
    return out


def kinds(eps):
    out = {"open": 0, "decay": 0, "window": 0}
    for e in eps:
        out[e["kind"]] += 1
    return out


def d2(eps):
    pairs = [e for e in eps if None not in (e["G"]["R60"], e["G"]["MAE60"], e["X1p"]["R60"], e["X1p"]["MAE60"])]
    res = {}
    for k in ("open", "decay", "window"):
        sub = [e for e in pairs if e["kind"] == k]
        res[k] = {"n_pairs": len(sub), "share": (len(sub) / len(pairs)) if pairs else None,
                  "G_R60_med": statistics.median(e["G"]["R60"] for e in sub) if sub else None,
                  "G_MAE60_med": statistics.median(e["G"]["MAE60"] for e in sub) if sub else None,
                  "delay_med": statistics.median(e["delay"] for e in sub) if sub else None}
    return res


A_MIN, B_MIN, C_MIN, D_MAX, N_MIN = 0.02, -0.03, 0.02, 6, 15


def crit(m):
    if m.get("a") is None:
        return {"a": False, "b": False, "c": False, "d": False, "enough": False}
    enough = m["abd_N"] >= N_MIN and m["c_N"] >= N_MIN
    return {"a": m["a"] >= A_MIN, "b": m["b"] >= B_MIN, "c": m["c"] >= C_MIN, "d": m["d"] <= D_MAX,
            "enough": enough}


def choose(M, reading):
    """Apply conditions 1-4 for one reading; return (chosen variant or None, per-variant detail, V0 sufficient)."""
    def get(sample, v):
        return M[sample][v][reading]
    detail = {}
    # P1 sample-size hold
    p1_short = any(not crit(get("P1", v))["enough"] for v in VARIANTS)

    def pass_2_4(v, with_cprime):
        p1 = get("P1", v)
        k = crit(p1)
        met = [x for x in ("a", "c") if k[x]]
        c2 = k["enough"] and k["b"] and bool(met) and k["d"]
        cp = None
        if with_cprime:
            cp = p1["c"] is not None and get("P1", "V0")["c"] is not None and p1["c"] >= get("P1", "V0")["c"]
            c2 = c2 and cp
        h1, h2 = get("P1H1", v), get("P1H2", v)
        k1, k2 = crit(h1), crit(h2)
        c3 = (k1["enough"] and k2["enough"] and k1["b"] and k1["d"] and k2["b"] and k2["d"]
              and any(h1[x] > 0 and h2[x] > 0 for x in met))
        p2 = get("P2", v)
        kp = crit(p2)
        c4 = kp["enough"] and kp["b"] and kp["d"] and any(p2[x] > 0 for x in met)
        return {"c2": c2, "cprime": cp, "met_P1": met, "c3": c3, "c4": c4, "all": c2 and c3 and c4}
    v0 = pass_2_4("V0", False)
    detail["V0"] = v0
    for v in ("W1", "W2", "W3"):
        detail[v] = pass_2_4(v, True)
    cond1 = not v0["all"]
    passing = [v for v in ("W1", "W2", "W3") if cond1 and detail[v]["all"]] if not p1_short else []
    return (passing[0] if passing else None), detail, {"cond1_V0_not_sufficient": cond1, "P1_sample_short": p1_short}


def main():
    check_hashes()
    print("hashes ok; _sample_std bytes ok")
    # self-test: W1 restore
    before = (C["RREC_RG4_DAY_SIGMA"], C["RREC_RG4_SHORT_RATIO"])
    samples = ["P1", "S1"] + [f"P2:{s}" for s in ("MU", "LITE", "DELL", "BE", "PWR")]
    with ProcessPoolExecutor(max_workers=7) as ex:
        runs = dict((name, (ts, res)) for name, ts, res in
                    ex.map(run_sample, [(s, VARIANTS + ("COPY_OFF",)) for s in samples]))
        slice_bad = dict(zip(samples, ex.map(self_test_slices, samples)))
    assert (C["RREC_RG4_DAY_SIGMA"], C["RREC_RG4_SHORT_RATIO"]) == before == (2.0, 1.5)
    selftest = {"slice_mismatches": slice_bad, "copy_off_mismatches": {}}
    for name, (ts, res) in runs.items():
        selftest["copy_off_mismatches"][name] = sum(1 for a, b in zip(res["V0"], res["COPY_OFF"]) if a != b)
    print("self-test", selftest)
    assert all(v == 0 for v in slice_bad.values())
    assert all(v == 0 for v in selftest["copy_off_mismatches"].values())

    smps = {name: build_sample(name) for name in samples}
    # left-censor first-ok date in P1 (check vs prereg 1994-10-21)
    sb = smps["P1"]["bench"]
    first_ok = next(sb["days"][t] for t in range(59, len(sb["days"]))
                    if all(sb["sigma60"][k] is not None for k in range(t - 59, t + 1)))
    selftest["P1_first_left_ok"] = first_ok
    selftest["P1_eval_start"] = smps["P1"]["days"][runs["P1"][0]]
    selftest["eval_start"] = {n: smps[n]["days"][runs[n][0]] for n in samples}

    END = "9999-12-31"
    defs = {"P1": [("P1", "0000", "2010-12-31")], "P1H1": [("P1", "0000", "2002-12-31")],
            "P1H2": [("P1", "2003-01-01", "2010-12-31")],
            "P2": [(f"P2:{s}", "2011-01-03", "2026-09-29") for s in ("MU", "LITE", "DELL", "BE", "PWR")],
            "S1": [("S1", "2011-01-03", "2026-09-29")]}
    for s in ("MU", "LITE", "DELL", "BE", "PWR"):
        defs[f"S2:{s}"] = [(f"P2:{s}", "2011-01-03", "2026-09-29")]
    M, rows = {}, []
    for key, parts in defs.items():
        M[key] = {}
        for v in VARIANTS:
            eps_all, L, R = [], 0, 0
            for (name, lo, hi) in parts:
                ts, res = runs[name]
                eps, l_, r_ = episodes_for(smps[name], ts, res[v], lo, hi)
                for e in eps:
                    e["sample"] = name
                eps_all += eps
                L += l_
                R += r_
            entry = {"episodes": len(eps_all), "end_kinds": kinds(eps_all), "left_censored": L,
                     "right_censored": R, "D2": d2(eps_all)}
            for reading in ("main", "S4"):
                entry[reading] = metrics(eps_all, reading)
            M[key][v] = entry
            if key in ("P1", "P2", "S1"):
                for e in eps_all:
                    rows.append([key, e["sample"], v, e["t0"], e["u"], e["kind"], e["fG"], e["delay"],
                                 e["G"]["R60"], e["G"]["MAE60"], e["X1p"]["R60"], e["X1p"]["MAE60"],
                                 e["event"]["date"] if e["event"] else None])
    verdict = {}
    for reading in ("main", "S4"):
        ch, det, extra = choose(M, reading)
        verdict[reading] = {"chosen": ch, "detail": det, **extra}
    final = verdict["main"]["chosen"]
    cond5 = verdict["main"]["chosen"] == verdict["S4"]["chosen"]
    verdict["condition5_same_choice"] = cond5
    verdict["adoption_candidate"] = final if (final is not None and cond5) else None
    verdict["outcome"] = "NO_CHANGE" if verdict["adoption_candidate"] is None else (
        f"ADOPTION_CANDIDATE {final} (Judge + user approval required)")
    (OUT / "indep_results.json").write_text(json.dumps(
        {"prereg_sha256": PREREG_SHA, "self_test": selftest, "metrics": M, "verdict": verdict},
        indent=1, ensure_ascii=False, default=str))
    with open(OUT / "indep_episodes.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["subsample", "series", "variant", "t0", "u", "end_kind", "f_G", "delay", "G_R60", "G_MAE60",
                    "X1p_R60", "X1p_MAE60", "event_date_at_t0"])
        w.writerows(rows)
    print(json.dumps(verdict, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
