#!/usr/bin/env python
"""R-REC1-X replay (research only; no broker access, no orders, no policy/state/scheduled-task change).

Pre-result contract: docs/claude/r-rec1-x-preregistration-2026-10-09.md
  (sha256 97514de28f816d2126ef0de02b62cdbc1585e19ddc8f06153a5bdb3b78d3d4fc, fixed 2026-10-09 03:02:51 KST).
Engine: leverage_up_study_2026-10-01.py (S4-3) is imported unchanged; its features(), simulate() (fill/cost/band arithmetic)
and metric functions are reused. Only a new target kind "RREC1X" is dispatched in front of its make_target().

Implementation readings of points the preregistration leaves open (fixed in this file before any replay computation):
 I1  "Index" = the market's own index (SOX / NDX / SPX). EV, RG, DS1 and SMA200 all use that index's close and low.
 I2  sigma60_t = pandas rolling(60).std() (ddof=1) of daily close returns ending at t (t included; S4-3 sig20 convention).
     5-session sigma = rolling(5).std() of the same returns ending at t. EMA50 = close.ewm(span=50, adjust=False)
     (repo EMA convention), valid from the 50th close. SMA200 = rolling(200).mean(). 20-session close high = rolling(20).max()
     including t. A missing indicator means no event and no boost on that close.
 I3  An event close t opens or refreshes the event: C0 = close_t, L0 = low_t. "No intraday new low below L0 after the event"
     = every low in (event close, t] >= L0. RG3 = close_{t-1} > C0 and close_t > C0 with t-1 after the event close.
     An event stays open until a boost starts or a new event refreshes it (the preregistration lists no timeout).
 I4  A boost is decided at close s (target 1.85) and filled at close s+1 (S4-3). End check at each close i while boosted:
     i - s >= 20 (20 sessions), DS1 (close_i < L0 of the boost's event, or close_i < EMA50_i), or E_i <= 0.90 x HWM_i.
     An end decided at close i is filled (back to 1.55) at close i+1. No new boost on the same close as an end.
     A new event during a boost opens a pending event; it does not end the boost, and DS1 keeps the boost's own L0.
 I5  HWM = running maximum of the X strategy's own equity from the run's first session (S5 decision-4 "full-period high").
     If E_s <= 0.90 x HWM_s on the start close, the boost ends on that same close (zero length, never filled); the event is
     still closed and the start is logged as "blocked", not counted as a boost.
     Report-only sensitivities: HWM = 252-session rolling max (S4-3 G-gate convention); sequential end check (start close
     not checked); a fresh run from 2010-03-11 (indicators from full history).
 I6  "Daily adjustment" = S4-3 simulate() with band 0 (rebalanced to target every close), 10 bp of traded weight per
     product, cash return 0 (usd0). ETF core: X >= 1 -> 3x (X-1)/2 + 1x rest. Aux: 'cash3' = X/3 in 3x + cash.
 I7  1x fee 0.0035/yr in every market (preregistration text). Rate = 3-month Treasury: DGS3MO from 1981-09-01, DTB3 before
     (S4-3 load_inputs splice; only SPX uses the DTB3 part). Price indices, no dividends.
 I8  SOX 32y = the full SOX file (1994-05-04 ~ 2026-09-29; first close is the return base). "2010~2026" = S4-3 "post" segment
     (2010-03-11 ~) of the continuous run, rebased (seg_metrics). NDX = cpv_inputs NDX (1994-05-04 ~, preregistration s3).
     SPX = leverage_up_inputs SPX (1954-01-04 ~). Criterion c uses each file's full segment. NDX 1985~ file: report only.
 I9  1-year-window worst diff = worst 252-session window return of X minus that of B, same segment (S4-3 A3).
 I10 Verdict uses start shift 0. Shifts 0-9 (drop the first k sessions, S4-3 convention) are reported, not judged.
"""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PREREG = REPO / "docs" / "claude" / "r-rec1-x-preregistration-2026-10-09.md"
PREREG_SHA = "97514de28f816d2126ef0de02b62cdbc1585e19ddc8f06153a5bdb3b78d3d4fc"
ENGINE = HERE / "leverage_up_study_2026-10-01.py"
ENGINE_SHA = "25f5dce84b84975440985b51d15749964283a09f6a114899042bed6d09bffb2b"
CPV = HERE / "cpv_inputs_2026-10-01"
LUI = HERE / "leverage_up_inputs_2026-10-01"
INPUTS = {
    "SOX": (CPV / "SOX_yahoo_raw.csv", "a261cc8473368e29722a42fa120808d4f48ccdfc4d6ba91826ec0831e2f95167"),
    "NDX": (CPV / "NDX_yahoo_raw.csv", "cb17eb80b0bbcef1b9bcd7453c06d46ff727143ea865a9349216d0b921b12748"),
    "SPX": (LUI / "SPX_yahoo_raw.csv", "4460849fbc94a7b8aed4aea5c8c89a622ce04522cdf7259a1553712d689f7c03"),
    "NDX85": (LUI / "NDX_yahoo_raw.csv", "d6ea7409215429bbd220fb80218bc72ec5632ee260eaf583b3af0b4fb0367f39"),
    "DGS3MO": (CPV / "DGS3MO_full.csv", "cee08fd9882231c94777e70a62b6de4d8bd005298bb94195b5135e954c7097b5"),
    "DTB3": (LUI / "DTB3_full.csv", "4a20f83a1ab50c53b06c62018cb4828a375e0177e09d26ad689fdb923d1e54fc"),
}
STEM = "r_rec1_x_replay_2026-10-09"
RESULTS_JSON = HERE / f"{STEM}_results.json"
BOOSTS_CSV = HERE / f"{STEM}_boosts.csv"

# fixed by the preregistration
B_LEVEL, X_LEVEL = 1.55, 1.85
FEE1 = 0.0035
COST = 0.0010
BAND = 0.0
EV1_K, EV2_K = 2.0, 3.0
RG4_DAY_K, RG4_SD5_K = 2.0, 1.5
BOOST_MAX = 20
HWM_STOP = 0.90
POST_START = pd.Timestamp("2010-03-11")
SHIFTS = tuple(range(10))
CRIT = {"a_cagr": 0.005, "b_mdd": -0.05, "c_cagr": 0.0, "d_w1": -0.05, "e_n": 10}
ENGINE_FEE1 = {"NDX": 0.0020, "SPX": 0.0009}  # S4-3 per-market fees, report-only sensitivity


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_engine():
    got = sha256_file(ENGINE)
    if got != ENGINE_SHA:
        raise RuntimeError(f"engine hash differs: {got}")
    spec = importlib.util.spec_from_file_location("s43_engine", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    orig = mod.make_target

    def make_target(spec_: dict[str, Any], L, stats):
        if spec_.get("kind") == "RREC1X":
            return rrec1x_target(spec_)
        return orig(spec_, L, stats)

    mod.make_target = make_target
    return mod


def check_inputs() -> dict[str, str]:
    got = sha256_file(PREREG)
    if got != PREREG_SHA:
        raise RuntimeError(f"preregistration hash differs: {got}")
    out = {}
    for k, (p, sha) in INPUTS.items():
        h = sha256_file(p)
        if h != sha:
            raise RuntimeError(f"{k}: input hash differs: {h}")
        out[k] = h
    return out


def load_ohlc(key: str) -> pd.DataFrame:
    return pd.read_csv(INPUTS[key][0], index_col="date", parse_dates=["date"])[["open", "high", "low", "close"]].astype(float)


def load_rate() -> pd.Series:
    dg = pd.read_csv(INPUTS["DGS3MO"][0], index_col="date", parse_dates=["date"])["DGS3MO"].astype(float)
    dt3 = pd.read_csv(INPUTS["DTB3"][0], index_col="date", parse_dates=["date"])["DTB3"].astype(float)
    splice = pd.Timestamp("1981-09-01")
    return pd.concat([dt3[dt3.index < splice], dg[dg.index >= splice]]).sort_index()


# ----------------------------------------------------------------------------
# indicators and target
# ----------------------------------------------------------------------------
def indicators(ohlc: pd.DataFrame) -> pd.DataFrame:
    close, low = ohlc["close"], ohlc["low"]
    r = close.pct_change()
    ind = pd.DataFrame(index=close.index)
    ind["px"] = close
    ind["low"] = low
    ind["r"] = r
    ind["sig60"] = r.rolling(60).std()
    ind["sd5"] = r.rolling(5).std()
    ema = close.ewm(span=50, adjust=False).mean()
    ema.iloc[:49] = np.nan
    ind["ema50"] = ema
    ind["sma200"] = close.rolling(200).mean()
    ind["hi20"] = close.rolling(20).max()
    return ind


def rrec1x_target(spec: dict[str, Any]):
    a = spec["arrays"]
    log = spec["log"]
    hmode = spec.get("hwm", "full")
    start_check = spec.get("start_hwm", True)
    px, low, r, sig, sd5, ema, sma, hi20 = (a[k] for k in ("px", "low", "r", "sig60", "sd5", "ema50", "sma200", "hi20"))
    st = {"ev": False, "C0": math.nan, "L0": math.nan, "ei": -1, "nl": False, "boost": False, "bs": -1, "bL0": math.nan, "hwm": -math.inf}
    dq: collections.deque = collections.deque()

    def f(i: int, e: float) -> float:
        if hmode == "full":
            if e > st["hwm"]:
                st["hwm"] = e
            H = st["hwm"]
        else:
            while dq and dq[-1][1] <= e:
                dq.pop()
            dq.append((i, e))
            while dq[0][0] <= i - 252:
                dq.popleft()
            H = dq[0][1]
        s = sig[i]
        kind = None
        if s == s:
            if r[i] == r[i] and r[i] <= -EV1_K * s:
                kind = "EV1"
            h = hi20[i]
            if h == h and px[i] <= h * (1.0 - EV2_K * s):
                kind = "EV1+EV2" if kind else "EV2"
        if kind:
            log["events"].append({"i": i, "kind": kind, "refresh": st["ev"], "during_boost": st["boost"]})
            st.update(ev=True, C0=px[i], L0=low[i], ei=i, nl=False)
        elif st["ev"] and low[i] < st["L0"]:
            st["nl"] = True
        ended = False
        if st["boost"]:
            reasons = []
            if i - st["bs"] >= BOOST_MAX:
                reasons.append("20세션")
            if px[i] < st["bL0"] or px[i] < ema[i]:
                reasons.append("DS1")
            if e <= HWM_STOP * H:
                reasons.append("HWM")
            if reasons:
                st["boost"] = False
                ended = True
                log["boosts"][-1].update(end=i, reasons=reasons)
        if (not st["boost"]) and (not ended) and st["ev"] and not kind:
            i0 = st["ei"]
            if i - 1 > i0 and ema[i] == ema[i] and sma[i] == sma[i] and s == s and sd5[i] == sd5[i]:
                rg2 = px[i] >= ema[i]
                rg3 = px[i] > st["C0"] and px[i - 1] > st["C0"] and not st["nl"]
                rg4 = abs(r[i]) <= RG4_DAY_K * s and sd5[i] <= RG4_SD5_K * s
                tr = px[i] > sma[i]
                if rg2 and rg3 and rg4 and tr:
                    st["ev"] = False
                    rec = {"start": i, "event": i0, "C0": st["C0"], "L0": st["L0"], "dd_hwm": e / H - 1.0}
                    if start_check and e <= HWM_STOP * H:
                        log["blocked"].append(rec)
                    else:
                        st.update(boost=True, bs=i, bL0=st["L0"])
                        rec.update(end=None, reasons=None)
                        log["boosts"].append(rec)
        return X_LEVEL if st["boost"] else B_LEVEL

    return f


# ----------------------------------------------------------------------------
# runs and metrics
# ----------------------------------------------------------------------------
class Market:
    def __init__(self, mod, ohlc: pd.DataFrame, rate: pd.Series, fee1: float = FEE1, shift: int = 0, start: pd.Timestamp | None = None):
        o = ohlc.iloc[shift:]
        d = mod.features(o["close"], rate, fee1, None)
        ind = indicators(o).reindex(d.index)
        if start is not None:
            keep = d.index >= start
            d, ind = d[keep].copy(), ind[keep].copy()
        self.F = mod.Feat(d)
        self.idx = d.index
        self.n = len(d)
        self.arrays = {k: ind[k].to_numpy(dtype=float) for k in ind.columns}
        self.post = int(self.idx.searchsorted(POST_START, side="left"))


def run_pair(mod, M: Market, impl: str = "core", **kw) -> dict[str, Any]:
    log = {"events": [], "boosts": [], "blocked": []}
    specX = {"kind": "RREC1X", "arrays": M.arrays, "log": log}
    specX.update(kw)
    EB, XB, _ = mod.simulate(M.F, mod.fixed(B_LEVEL), BAND, COST, impl, "usd0")
    EX, XX, _ = mod.simulate(M.F, specX, BAND, COST, impl, "usd0")
    return {"EB": EB, "XB": XB, "EX": EX, "XX": XX, "log": log}


def seg(mod, E, X, a, b) -> dict[str, float]:
    return dict(zip(mod.METRIC_COLS, (float(v) for v in mod.seg_metrics(E, X, a, b))))


def compare(mod, M: Market, R: dict[str, Any], a: int, b: int) -> dict[str, Any]:
    sb, sx = seg(mod, R["EB"], R["XB"], a, b), seg(mod, R["EX"], R["XX"], a, b)
    return {"B": sb, "X": sx, "d_cagr": sx["cagr"] - sb["cagr"], "d_mdd": sx["mdd"] - sb["mdd"], "d_w1": sx["w1_min"] - sb["w1_min"],
            "start": str(M.idx[a].date()), "end": str(M.idx[b - 1].date()), "years": (b - a) / 252.0}


def boost_table(M: Market, R: dict[str, Any], a: int = 0) -> list[dict[str, Any]]:
    px, EX, EB, n = M.arrays["px"], R["EX"], R["EB"], M.n
    rows = []
    for k, bt in enumerate(R["log"]["boosts"]):
        s = bt["start"]
        if s < a:
            continue
        end = bt["end"]
        dur = (end - s) if end is not None else (n - 1 - s)
        s1, e1 = min(s + 1, n - 1), min((end if end is not None else n - 1) + 1, n - 1)
        rows.append({
            "k": k, "event_date": str(M.idx[bt["event"]].date()), "start_date": str(M.idx[s].date()),
            "end_date": str(M.idx[end].date()) if end is not None else None, "sessions": dur,
            "reasons": "+".join(bt["reasons"]) if bt["reasons"] else "진행 중(자료 끝)",
            "idx_fwd20": float(px[s + 20] / px[s] - 1.0) if s + 20 < n else None,
            "excess_log": float(math.log(EX[e1] / EX[s1]) - math.log(EB[e1] / EB[s1])),
            "dd_hwm_at_start": bt["dd_hwm"],
        })
    return rows


def dist(vals: list[float]) -> dict[str, Any]:
    v = np.array([x for x in vals if x is not None], dtype=float)
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size), "min": float(v.min()), "p25": float(np.percentile(v, 25)), "median": float(np.median(v)),
            "p75": float(np.percentile(v, 75)), "max": float(v.max()), "mean": float(v.mean()), "pos_share": float((v > 0).mean())}


def boost_summary(rows: list[dict[str, Any]], blocked: list[dict[str, Any]], n_events: int) -> dict[str, Any]:
    reasons = collections.Counter()
    for r_ in rows:
        for x in r_["reasons"].split("+"):
            reasons[x] += 1
    return {"n_boosts": len(rows), "n_blocked_hwm_at_start": len(blocked), "n_event_closes": n_events,
            "mean_sessions": float(np.mean([r_["sessions"] for r_ in rows])) if rows else None,
            "end_reasons": dict(reasons), "idx_fwd20": dist([r_["idx_fwd20"] for r_ in rows]),
            "excess_log": dist([r_["excess_log"] for r_ in rows])}


def market_block(mod, M: Market, R: dict[str, Any], with_post: bool) -> dict[str, Any]:
    out = {"full": compare(mod, M, R, 0, M.n)}
    rows = boost_table(M, R)
    out["boosts"] = boost_summary(rows, R["log"]["blocked"], len(R["log"]["events"]))
    out["blocked_dates"] = [str(M.idx[b["start"]].date()) for b in R["log"]["blocked"]]
    if with_post:
        out["post"] = compare(mod, M, R, M.post, M.n)
        prow = [r_ for r_ in rows if r_["start_date"] >= str(POST_START.date())]
        pblk = [b for b in R["log"]["blocked"] if b["start"] >= M.post]
        out["post_boosts"] = boost_summary(prow, pblk, sum(1 for e in R["log"]["events"] if e["i"] >= M.post))
    out["_rows"] = rows
    return out


def verdict(sox: dict[str, Any], ndx: dict[str, Any], spx: dict[str, Any]) -> dict[str, Any]:
    v = {}
    v["a"] = {"sox_full": sox["full"]["d_cagr"], "sox_post": sox["post"]["d_cagr"],
              "pass": bool(sox["full"]["d_cagr"] >= CRIT["a_cagr"] and sox["post"]["d_cagr"] >= CRIT["a_cagr"])}
    v["b"] = {"sox_full": sox["full"]["d_mdd"], "sox_post": sox["post"]["d_mdd"],
              "pass": bool(sox["full"]["d_mdd"] >= CRIT["b_mdd"] and sox["post"]["d_mdd"] >= CRIT["b_mdd"])}
    v["c"] = {"ndx_full": ndx["full"]["d_cagr"], "spx_full": spx["full"]["d_cagr"],
              "pass": bool(ndx["full"]["d_cagr"] >= CRIT["c_cagr"] and spx["full"]["d_cagr"] >= CRIT["c_cagr"])}
    v["d"] = {"sox_full": sox["full"]["d_w1"], "pass": bool(sox["full"]["d_w1"] >= CRIT["d_w1"])}
    v["e"] = {"sox_full": sox["boosts"]["n_boosts"], "pass": bool(sox["boosts"]["n_boosts"] >= CRIT["e_n"])}
    v["all_pass"] = all(v[k]["pass"] for k in "abcde")
    v["verdict"] = "채택 후보(K3 Independent Judge로)" if v["all_pass"] else "미달(기각 또는 재설계 — 새 사전 등록 필요)"
    return v


def clean(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run_all() -> int:
    t0 = datetime.now(timezone(timedelta(hours=9)))
    shas = check_inputs()
    mod = load_engine()
    rate = load_rate()
    ohlc = {k: load_ohlc(k) for k in ("SOX", "NDX", "SPX", "NDX85")}
    res: dict[str, Any] = {"meta": {
        "started_kst": t0.isoformat(timespec="seconds"), "preregistration_sha256": PREREG_SHA, "engine_sha256": ENGINE_SHA,
        "script_sha256": sha256_file(Path(__file__)), "inputs_sha256": shas, "grade_cap": "C (과거 재현, 외부 가격 참고용)",
        "fixed": {"B": B_LEVEL, "X": X_LEVEL, "fee1": FEE1, "cost": COST, "band": BAND, "cash": "usd0", "crit": CRIT},
    }}
    # primary (shift 0, ETF core)
    prim = {}
    for mk in ("SOX", "NDX", "SPX"):
        M = Market(mod, ohlc[mk], rate)
        R = run_pair(mod, M)
        prim[mk] = market_block(mod, M, R, with_post=True)
        if mk == "SOX":
            pd.DataFrame(prim[mk]["_rows"]).to_csv(BOOSTS_CSV, index=False, encoding="utf-8")
    res["primary"] = prim
    res["verdict"] = verdict(prim["SOX"], prim["NDX"], prim["SPX"])
    # shift sensitivity 0-9 (report only)
    sh = []
    for k in SHIFTS:
        row = {"shift": k}
        for mk in ("SOX", "NDX", "SPX"):
            M = Market(mod, ohlc[mk], rate, shift=k)
            R = run_pair(mod, M)
            b = market_block(mod, M, R, with_post=(mk == "SOX"))
            row[mk] = {"full": {x: b["full"][x] for x in ("d_cagr", "d_mdd", "d_w1")}, "n_boosts": b["boosts"]["n_boosts"]}
            if mk == "SOX":
                row[mk]["post"] = {x: b["post"][x] for x in ("d_cagr", "d_mdd", "d_w1")}
        row["verdict"] = verdict(
            {"full": row["SOX"]["full"], "post": row["SOX"]["post"], "boosts": {"n_boosts": row["SOX"]["n_boosts"]}},
            {"full": row["NDX"]["full"]}, {"full": row["SPX"]["full"]})
        sh.append(row)
    res["shift_sensitivity"] = sh
    # aux: 3x + cash structure (report only)
    aux = {}
    for mk in ("SOX", "NDX", "SPX"):
        M = Market(mod, ohlc[mk], rate)
        R = run_pair(mod, M, impl="cash3")
        b = market_block(mod, M, R, with_post=(mk == "SOX"))
        aux[mk] = {s: {x: b[s][x] for x in ("d_cagr", "d_mdd", "d_w1")} for s in (("full", "post") if mk == "SOX" else ("full",))}
        aux[mk]["n_boosts"] = b["boosts"]["n_boosts"]
    res["aux_cash3"] = aux
    # interpretation sensitivities (report only)
    sens = {}
    for name, kw in (("hwm_252", {"hwm": "h252"}), ("sequential_start", {"start_hwm": False})):
        sens[name] = {}
        for mk in ("SOX", "NDX", "SPX"):
            M = Market(mod, ohlc[mk], rate)
            R = run_pair(mod, M, **kw)
            b = market_block(mod, M, R, with_post=(mk == "SOX"))
            sens[name][mk] = {s: {x: b[s][x] for x in ("d_cagr", "d_mdd", "d_w1")} for s in (("full", "post") if mk == "SOX" else ("full",))}
            sens[name][mk]["n_boosts"] = b["boosts"]["n_boosts"]
            sens[name][mk]["n_blocked"] = b["boosts"]["n_blocked_hwm_at_start"]
    M = Market(mod, ohlc["SOX"], rate, start=POST_START)
    R = run_pair(mod, M)
    b = market_block(mod, M, R, with_post=False)
    sens["fresh_2010_SOX"] = {"full": {x: b["full"][x] for x in ("d_cagr", "d_mdd", "d_w1", "start", "end")},
                              "n_boosts": b["boosts"]["n_boosts"], "n_blocked": b["boosts"]["n_blocked_hwm_at_start"]}
    res["interpretation_sensitivity"] = sens
    # report-only extras
    extra = {}
    M = Market(mod, ohlc["NDX85"], rate)
    R = run_pair(mod, M)
    b = market_block(mod, M, R, with_post=False)
    extra["NDX_1985"] = {"full": {x: b["full"][x] for x in ("d_cagr", "d_mdd", "d_w1", "start", "end")}, "n_boosts": b["boosts"]["n_boosts"]}
    for mk in ("NDX", "SPX"):
        M = Market(mod, ohlc[mk], rate, fee1=ENGINE_FEE1[mk])
        R = run_pair(mod, M)
        b = market_block(mod, M, R, with_post=False)
        extra[f"{mk}_engine_fee"] = {"fee1": ENGINE_FEE1[mk], "d_cagr": b["full"]["d_cagr"]}
    res["report_only"] = extra
    res["meta"]["finished_kst"] = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    RESULTS_JSON.write_text(json.dumps(clean(res), ensure_ascii=False, indent=1), encoding="utf-8")
    v = res["verdict"]
    print(json.dumps(clean(v), ensure_ascii=False, indent=1))
    return 0


# ----------------------------------------------------------------------------
# self-test (state machine + engine plumbing)
# ----------------------------------------------------------------------------
def _arrays(n: int, **over) -> dict[str, np.ndarray]:
    a = {"px": np.full(n, 100.0), "low": np.full(n, 99.5), "r": np.zeros(n), "sig60": np.full(n, 0.01), "sd5": np.full(n, 0.005),
         "ema50": np.full(n, 95.0), "sma200": np.full(n, 90.0), "hi20": np.full(n, 100.0)}
    for k, v in over.items():
        a[k] = np.asarray(v, dtype=float)
    return a


def _path(a, e=None, **kw):
    log = {"events": [], "boosts": [], "blocked": []}
    spec = {"kind": "RREC1X", "arrays": a, "log": log}
    spec.update(kw)
    f = rrec1x_target(spec)
    n = len(a["px"])
    e = e if e is not None else [1.0] * n
    return [f(i, e[i]) for i in range(n)], log


def self_test() -> int:
    fails = []

    def ok(cond, msg):
        if not cond:
            fails.append(msg)

    n = 40
    # T1 EV1 at 2, start at 4 (needs closes 3,4 > C0), 20 sessions -> end at 24
    px = np.full(n, 101.0); px[2] = 96.0
    r = np.zeros(n); r[2] = -0.05
    low = np.full(n, 100.5); low[2] = 95.0
    a = _arrays(n, px=px, r=r, low=low)
    t, lg = _path(a)
    ok(t[:4] == [1.55] * 4 and t[4:24] == [1.85] * 20 and t[24:] == [1.55] * (n - 24), f"T1 path {t}")
    ok(lg["boosts"] and lg["boosts"][0]["reasons"] == ["20세션"] and lg["boosts"][0]["end"] == 24, f"T1 log {lg['boosts']}")
    # T2 new low below L0 after event -> no start
    low2 = low.copy(); low2[3] = 94.0
    t, lg = _path(_arrays(n, px=px, r=r, low=low2))
    ok(all(x == 1.55 for x in t) and not lg["boosts"], "T2 new low must block")
    # T2b a later event refreshes C0/L0 and can start
    px3 = px.copy(); r3 = r.copy(); low3 = low2.copy(); px3[10] = 99.0; r3[10] = -0.03; low3[10] = 93.0
    t, lg = _path(_arrays(n, px=px3, r=r3, low=low3))
    ok(lg["boosts"] and lg["boosts"][0]["start"] == 12, f"T2b start {lg['boosts']}")
    # T3 DS1 close < EMA50 ends at 7
    ema = np.full(n, 95.0); ema[7] = 102.0
    t, lg = _path(_arrays(n, px=px, r=r, low=low, ema50=ema))
    ok(lg["boosts"][0]["end"] == 7 and lg["boosts"][0]["reasons"] == ["DS1"] and t[7] == 1.55 and t[6] == 1.85, f"T3 {lg['boosts']}")
    # T3b DS1 close < L0 (95) ends
    px4 = px.copy(); px4[9] = 94.9; ema4 = np.full(n, 90.0)
    t, lg = _path(_arrays(n, px=px4, r=r, low=low, ema50=ema4))
    ok(lg["boosts"][0]["end"] == 9 and "DS1" in lg["boosts"][0]["reasons"], f"T3b {lg['boosts']}")
    # T4 HWM -10% ends at 6
    e = [1.0] * n; e[4] = 1.2; e[5] = 1.2
    for i in range(6, n):
        e[i] = 1.07
    t, lg = _path(_arrays(n, px=px, r=r, low=low), e=e)
    ok(lg["boosts"][0]["end"] == 6 and lg["boosts"][0]["reasons"] == ["HWM"], f"T4 {lg['boosts']}")
    # T5 start-close HWM block: zero length, event closed, no later start
    e = [1.0] * n; e[1] = 1.2
    t, lg = _path(_arrays(n, px=px, r=r, low=low), e=e)
    ok(all(x == 1.55 for x in t) and len(lg["blocked"]) == 1 and lg["blocked"][0]["start"] == 4 and not lg["boosts"], f"T5 {lg}")
    # T6 sequential variant: starts at 4, ends at 5 by HWM
    t, lg = _path(_arrays(n, px=px, r=r, low=low), e=e, start_hwm=False)
    ok(t[4] == 1.85 and t[5] == 1.55 and lg["boosts"][0]["end"] == 5, f"T6 {t[:8]} {lg['boosts']}")
    # T7 new event during boost keeps the boost; pending event starts after end (24) at >= 25
    n7 = 60
    px7 = np.full(n7, 101.0); px7[2] = 96.0; px7[10] = 99.0
    r7 = np.zeros(n7); r7[2] = -0.05; r7[10] = -0.03
    low7 = np.full(n7, 100.5); low7[2] = 95.0; low7[10] = 98.0
    t, lg = _path(_arrays(n7, px=px7, r=r7, low=low7))
    ok(len(lg["boosts"]) == 2 and lg["boosts"][0]["end"] == 24 and lg["boosts"][1]["start"] == 25, f"T7 {lg['boosts']}")
    # T8 EV2 only: px <= hi20*(1-3sig) with r not below -2sig
    px8 = np.full(n, 101.0); px8[2] = 96.9; px8[1] = 98.0
    r8 = np.zeros(n); r8[1] = -0.015; r8[2] = -0.011
    hi = np.full(n, 100.0)
    t, lg = _path(_arrays(n, px=px8, r=r8, low=np.full(n, 96.5), hi20=hi))
    ok(lg["events"] and lg["events"][0]["kind"] == "EV2" and lg["events"][0]["i"] == 2, f"T8 {lg['events']}")
    # T9 RG4 sd5 too high -> no start; T10 SMA200 fail -> no start; T11 RG4 day move too big
    t, lg = _path(_arrays(n, px=px, r=r, low=low, sd5=np.full(n, 0.016)))
    ok(not lg["boosts"], "T9 sd5")
    t, lg = _path(_arrays(n, px=px, r=r, low=low, sma200=np.full(n, 101.0)))
    ok(not lg["boosts"], "T10 sma200 (close must be strictly above)")
    r11 = r.copy(); r11[4:6] = 0.021
    t, lg = _path(_arrays(n, px=px, r=r11, low=low))
    ok(lg["boosts"] and lg["boosts"][0]["start"] == 6, f"T11 {lg['boosts']}")
    # T12 missing indicator -> no event
    t, lg = _path(_arrays(n, px=px, r=r, low=low, sig60=np.full(n, np.nan)))
    ok(not lg["events"] and not lg["boosts"], "T12 nan sigma")
    # T13 H252 mode: drawdown older than 252 sessions forgotten
    n13 = 300
    px13 = np.full(n13, 101.0); px13[280] = 96.0
    r13 = np.zeros(n13); r13[280] = -0.05
    low13 = np.full(n13, 100.5); low13[280] = 95.0
    e13 = [0.5] * n13; e13[0] = 1.0
    t, lg = _path(_arrays(n13, px=px13, r=r13, low=low13), e=e13, hwm="h252")
    ok(lg["boosts"] and lg["boosts"][0]["start"] == 282, f"T13 h252 {lg['boosts'][:1]} {lg['blocked'][:1]}")
    t, lg = _path(_arrays(n13, px=px13, r=r13, low=low13), e=e13)
    ok(not lg["boosts"] and len(lg["blocked"]) == 1, "T13 full HWM blocks")
    # engine plumbing: fill timing, split, cost, daily rebalance
    mod = load_engine()
    F = mod._toy_feat(30, r=0.01)
    a = _arrays(30, px=np.full(30, 101.0), r=np.r_[0, 0, -0.05, np.zeros(27)], low=np.r_[np.full(2, 100.5), 95.0, np.full(27, 100.5)])
    a["px"][2] = 96.0
    log = {"events": [], "boosts": [], "blocked": []}
    E, X, _ = mod.simulate(F, {"kind": "RREC1X", "arrays": a, "log": log}, 0.0, 0.0010, "core", "usd0")
    ok(abs(X[1] - 1.55) < 1e-12 and abs(X[4] - 1.55) < 1e-12 and abs(X[5] - 1.85) < 1e-12 and abs(X[24] - 1.85) < 1e-12 and abs(X[25] - 1.55) < 1e-12,
       f"E1 fill timing {X[:8]} {X[23:27]}")
    # independent equity recomputation for fixed 1.55 with r3=r1=0.01, rc=0
    EB, XB, _ = mod.simulate(F, mod.fixed(1.55), 0.0, 0.0010, "core", "usd0")
    e_, wl, wx = 1.0, None, None
    ref = []
    for i in range(30):
        if i > 0:
            gl, gx, gc = wl * 1.01, wx * 1.01, (1 - wl - wx)
            tot = gl + gx + gc; e_ *= tot; wl, wx = gl / tot, gx / tot
        if i >= 1:
            tl, tx = 0.275, 0.725
            if wl is None:
                wl, wx = tl, tx; e_ -= e_ * 0.001 * 1.0
            else:
                e_ -= e_ * 0.001 * (abs(tl - wl) + abs(tx - wx)); wl, wx = tl, tx
        if wl is None:
            wl, wx = 0.0, 0.0
        ref.append(e_)
    ok(np.allclose(EB, ref, rtol=0, atol=1e-13), "E2 equity recomputation")
    ok(abs(EB[1] - 0.999) < 1e-15, f"E3 first fill cost {EB[1]}")
    # cash3: 1.55/3 in 3x
    Ec, Xc, _ = mod.simulate(F, mod.fixed(1.55), 0.0, 0.0010, "cash3", "usd0")
    ok(abs(Xc[2] - 1.55) < 1e-12, f"E4 cash3 exposure {Xc[2]}")
    if fails:
        print("SELF-TEST FAIL")
        for m in fails:
            print(" -", m)
        return 1
    print("SELF-TEST PASS (17 checks)")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--run" in sys.argv:
        if self_test() != 0:
            sys.exit(1)
        sys.exit(run_all())
    print(__doc__)
