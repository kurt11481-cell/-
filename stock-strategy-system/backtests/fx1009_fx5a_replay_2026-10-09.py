#!/usr/bin/env python
"""FX-1009 fx-5a replay (research only; no broker access, no orders, no policy/state/journal/scheduled-task change).

Pre-result contract: docs/claude/fx1009-fx5a-preregistration-2026-10-09.md
  (sha256 12c39fe7dab6f234e2cfe6f15cc654b8203c00aea006fb22105d0217b6f27890, fixed 2026-10-09 15:47:07 KST).
Engine: leverage_up_study_2026-10-01.py (S4-3) is imported unchanged; features(), Feat, fixed(), simulate() and seg_metrics()
are reused as-is (fixed targets only, no new target kind).

Part A  fixed risk budgets 1.00 / 1.32 / 1.55, ETF core ('core'), daily rebalance (band 0) -> 6 ordered pairs, criteria a-d.
Part B  fill target at the same budget: S = SOXL fill ('cash3': T/3 in 3x + cash) vs K = 1x core first ('core'),
        S5 adjustment band +-0.3 in exposure -> engine band 0.10 for cash3 and 0.15 for core; both directions, verdict at T=1.55.
Readings fixed in this file before any replay computation (all follow the preregistration text):
 J1  Criteria = R-REC1-X s4 a-d unchanged (>= at the boundary, unrounded). e (boost count) is not applicable (preregistration 3-4).
 J2  Anchor: Part A F1.55 must equal R-REC1-X results 'primary' B (cagr/mdd/w1_min, SOX full+post, NDX full, SPX full) within 1e-9,
     otherwise the run stops before writing results.
 J3  Segments: full = whole run, post = first session >= 2010-03-11 (rebased), recent (report) >= 2016-01-01, >= 2021-10-01.
     Shift k drops the first k raw closes before features() (S4-3 / R-REC1-X convention).
 J4  Extras (report): worst day, drawdown episodes reaching -10%/-20% (new-high groups, as S4-3 dd20_count), share of sessions
     <= -10% below the running high, adjustments per year = (trades - first fill) / (n/252) on the full run.
 J5  Path loss (report): PL = (P3[j+L]/P3[j]-1)/3 - (P1[j+L]/P1[j]-1), P = cumulative product of the run's daily legs from i=1,
     every start j with j >= a and j+L <= b-1. Real = SOXL/SOXX adjclose daily change aligned to SOX sessions from 2010-03-11
     (first row NaN -> 0, any other NaN = error). Spot window 2026-06-22 -> 2026-09-29.
"""
from __future__ import annotations

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
PREREG = REPO / "docs" / "claude" / "fx1009-fx5a-preregistration-2026-10-09.md"
PREREG_SHA = "12c39fe7dab6f234e2cfe6f15cc654b8203c00aea006fb22105d0217b6f27890"
ENGINE = HERE / "leverage_up_study_2026-10-01.py"
ENGINE_SHA = "25f5dce84b84975440985b51d15749964283a09f6a114899042bed6d09bffb2b"
ANCHOR = HERE / "r_rec1_x_replay_2026-10-09_results.json"
ANCHOR_SHA = "77581918981ffd15a6b81d493e276f664f05db0a776e741480be42775b38b78f"
CPV = HERE / "cpv_inputs_2026-10-01"
LUI = HERE / "leverage_up_inputs_2026-10-01"
S4 = HERE / "soxl_signal_inputs_2026-10-01"
INPUTS = {
    "SOX": (CPV / "SOX_yahoo_raw.csv", "a261cc8473368e29722a42fa120808d4f48ccdfc4d6ba91826ec0831e2f95167"),
    "NDX": (CPV / "NDX_yahoo_raw.csv", "cb17eb80b0bbcef1b9bcd7453c06d46ff727143ea865a9349216d0b921b12748"),
    "SPX": (LUI / "SPX_yahoo_raw.csv", "4460849fbc94a7b8aed4aea5c8c89a622ce04522cdf7259a1553712d689f7c03"),
    "DGS3MO": (CPV / "DGS3MO_full.csv", "cee08fd9882231c94777e70a62b6de4d8bd005298bb94195b5135e954c7097b5"),
    "DTB3": (LUI / "DTB3_full.csv", "4a20f83a1ab50c53b06c62018cb4828a375e0177e09d26ad689fdb923d1e54fc"),
    "SOXL": (S4 / "SOXL_combined.csv", "56e612b764a7c5df48b1f009efb300badba34dfc1d2cc262946a0d33a7502c24"),
    "SOXX": (S4 / "SOXX_combined.csv", "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6"),
}
STEM = "fx1009_fx5a_replay_2026-10-09"
RESULTS_JSON = HERE / f"{STEM}_results.json"

# fixed by the preregistration
LEVELS = (1.00, 1.32, 1.55)
CURRENT = 1.55
FEE1 = 0.0035
COST = 0.0010
POST_START = pd.Timestamp("2010-03-11")
RECENT = {"2016~": pd.Timestamp("2016-01-01"), "2021-10~": pd.Timestamp("2021-10-01")}
SHIFTS = tuple(range(10))
CRIT = {"a_cagr": 0.005, "b_mdd": -0.05, "c_cagr": 0.0, "d_w1": -0.05}
PAIRS_A = ((1.32, 1.00), (1.55, 1.00), (1.55, 1.32), (1.00, 1.32), (1.00, 1.55), (1.32, 1.55))
PL_L = (20, 60, 120, 252)
SPOT = (pd.Timestamp("2026-06-22"), pd.Timestamp("2026-09-29"))
ENGINE_FEE1 = {"NDX": 0.0020, "SPX": 0.0009}
MARKETS = ("SOX", "NDX", "SPX")
# configuration name -> (impl, band, cash)
CFG = {
    "A_main": ("core", 0.0, "usd0"),       # Part A primary; also Part B K daily
    "core_pm03": ("core", 0.15, "usd0"),   # Part B K primary; Part A report (S5 band +-0.3)
    "core_10p": ("core", 0.10, "usd0"),    # Part A report (C.6 exploratory convention)
    "cash3_daily": ("cash3", 0.0, "usd0"),  # Part A report; Part B S daily
    "cash3_pm03": ("cash3", 0.10, "usd0"),  # Part B S primary
    "cash3_pm03_tbill": ("cash3", 0.10, "tbill"),
    "core_pm03_tbill": ("core", 0.15, "tbill"),
}
B_MAIN = {"K": "core_pm03", "S": "cash3_pm03"}
B_SENS = {"daily": {"K": "A_main", "S": "cash3_daily"}, "tbill": {"K": "core_pm03_tbill", "S": "cash3_pm03_tbill"}}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_inputs() -> dict[str, str]:
    for p, sha, label in ((PREREG, PREREG_SHA, "preregistration"), (ENGINE, ENGINE_SHA, "engine"), (ANCHOR, ANCHOR_SHA, "anchor")):
        got = sha256_file(p)
        if got != sha:
            raise RuntimeError(f"{label} hash differs: {got}")
    out = {}
    for k, (p, sha) in INPUTS.items():
        h = sha256_file(p)
        if h != sha:
            raise RuntimeError(f"{k}: input hash differs: {h}")
        out[k] = h
    return out


def load_engine():
    got = sha256_file(ENGINE)
    if got != ENGINE_SHA:
        raise RuntimeError(f"engine hash differs: {got}")
    spec = importlib.util.spec_from_file_location("s43_engine", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_close(key: str) -> pd.Series:
    return pd.read_csv(INPUTS[key][0], index_col="date", parse_dates=["date"])["close"].astype(float)


def load_adj(key: str) -> pd.Series:
    return pd.read_csv(INPUTS[key][0], index_col="date", parse_dates=["date"])["adjclose"].astype(float)


def load_rate() -> pd.Series:
    dg = pd.read_csv(INPUTS["DGS3MO"][0], index_col="date", parse_dates=["date"])["DGS3MO"].astype(float)
    dt3 = pd.read_csv(INPUTS["DTB3"][0], index_col="date", parse_dates=["date"])["DTB3"].astype(float)
    splice = pd.Timestamp("1981-09-01")
    return pd.concat([dt3[dt3.index < splice], dg[dg.index >= splice]]).sort_index()


# ----------------------------------------------------------------------------
# runs and metrics
# ----------------------------------------------------------------------------
class Mkt:
    def __init__(self, mod, close: pd.Series, rate: pd.Series, fee1: float = FEE1, shift: int = 0, d: pd.DataFrame | None = None):
        if d is None:
            d = mod.features(close.iloc[shift:], rate, fee1, None)
        self.d = d
        self.F = mod.Feat(d)
        self.idx = d.index
        self.n = len(d)
        self.bounds = {"full": (0, self.n), "post": (int(self.idx.searchsorted(POST_START, side="left")), self.n)}
        for name, ts in RECENT.items():
            self.bounds[name] = (int(self.idx.searchsorted(ts, side="left")), self.n)


def seg_S(E: np.ndarray, a: int, b: int) -> np.ndarray:
    return E[0:b] if a == 0 else np.concatenate(([1.0], E[a:b] / E[a - 1]))


def dd_counts(S: np.ndarray, th: float) -> int:
    M = np.maximum.accumulate(S)
    newhigh = np.zeros(len(S), dtype=bool)
    newhigh[1:] = M[1:] > M[:-1]
    grp = np.cumsum(newhigh)
    below = (S / M - 1.0) <= th
    return int(np.unique(grp[below]).size)


def seg_block(mod, E: np.ndarray, X: np.ndarray, a: int, b: int, idx: pd.DatetimeIndex) -> dict[str, Any]:
    m = dict(zip(mod.METRIC_COLS, (float(v) for v in mod.seg_metrics(E, X, a, b))))
    S = seg_S(E, a, b)
    dd = S / np.maximum.accumulate(S) - 1.0
    out = {k: m[k] for k in ("cagr", "mdd", "w1_min", "w1_med", "w3_min", "meanx", "n")}
    out.update({
        "worst_day": float((S[1:] / S[:-1]).min() - 1.0),
        "dd10_episodes": dd_counts(S, -0.10), "dd20_episodes": dd_counts(S, -0.20),
        "below10_share": float((dd <= -0.10).mean()),
        "start": str(idx[a].date()), "end": str(idx[b - 1].date()),
    })
    if out["dd20_episodes"] != int(m["dd20n"]):
        raise RuntimeError("dd20 count differs from engine dd20n")
    return out


def run_cfg(mod, M: Mkt, T: float, cfg: str, lev=None, one=None, segs: tuple[str, ...] | None = None) -> dict[str, Any]:
    impl, band, cash = CFG[cfg]
    E, X, st = mod.simulate(M.F, mod.fixed(T), band, COST, impl, cash, lev, one)
    res = {s: seg_block(mod, E, X, a, b, M.idx) for s, (a, b) in M.bounds.items() if b - a > 1 and (segs is None or s in segs)}
    res["adj_per_year"] = max(st["ntr"] - 1, 0) / (M.n / 252.0)
    res["_E"] = E
    return res


def verdict(x: dict[str, dict], b: dict[str, dict]) -> dict[str, Any]:
    """x, b: {'SOX': run, 'NDX': run, 'SPX': run} for the challenger X and the base B."""
    d = lambda mk, s, k: x[mk][s][k] - b[mk][s][k]
    v = {
        "a": {"sox_full": d("SOX", "full", "cagr"), "sox_post": d("SOX", "post", "cagr")},
        "b": {"sox_full": d("SOX", "full", "mdd"), "sox_post": d("SOX", "post", "mdd")},
        "c": {"ndx_full": d("NDX", "full", "cagr"), "spx_full": d("SPX", "full", "cagr")},
        "d": {"sox_full": d("SOX", "full", "w1_min")},
    }
    v["a"]["pass"] = bool(v["a"]["sox_full"] >= CRIT["a_cagr"] and v["a"]["sox_post"] >= CRIT["a_cagr"])
    v["b"]["pass"] = bool(v["b"]["sox_full"] >= CRIT["b_mdd"] and v["b"]["sox_post"] >= CRIT["b_mdd"])
    v["c"]["pass"] = bool(v["c"]["ndx_full"] >= CRIT["c_cagr"] and v["c"]["spx_full"] >= CRIT["c_cagr"])
    v["d"]["pass"] = bool(v["d"]["sox_full"] >= CRIT["d_w1"])
    v["e"] = "해당 없음"
    v["fails"] = [k for k in "abcd" if not v[k]["pass"]]
    v["all_pass"] = not v["fails"]
    return v


def path_loss(P3: np.ndarray, P1: np.ndarray, a: int, b: int, L: int) -> dict[str, Any]:
    j = np.arange(a, b - L)
    if j.size == 0:
        return {"n": 0}
    pl = (P3[j + L] / P3[j] - 1.0) / 3.0 - (P1[j + L] / P1[j] - 1.0)
    return {"n": int(pl.size), "min": float(pl.min()), "p05": float(np.percentile(pl, 5)), "median": float(np.median(pl)),
            "mean": float(pl.mean()), "neg_share": float((pl < 0).mean())}


def legs(r3: list[float], r1: list[float]) -> tuple[np.ndarray, np.ndarray]:
    a3, a1 = np.asarray(r3, dtype=float).copy(), np.asarray(r1, dtype=float).copy()
    a3[0] = 0.0
    a1[0] = 0.0
    return np.cumprod(1.0 + a3), np.cumprod(1.0 + a1)


def strip(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): strip(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [strip(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def lv(T: float) -> str:
    return f"{T:.2f}"


def run_all() -> int:
    t0 = datetime.now(timezone(timedelta(hours=9)))
    shas = check_inputs()
    mod = load_engine()
    rate = load_rate()
    close = {k: load_close(k) for k in MARKETS}
    res: dict[str, Any] = {"meta": {
        "started_kst": t0.isoformat(timespec="seconds"), "preregistration_sha256": PREREG_SHA, "engine_sha256": ENGINE_SHA,
        "anchor_sha256": ANCHOR_SHA, "script_sha256": sha256_file(Path(__file__)), "inputs_sha256": shas,
        "grade_cap": "C (과거 재현, 외부 가격 참고용)",
        "fixed": {"levels": LEVELS, "fee1": FEE1, "cost": COST, "crit": CRIT, "cfg": CFG, "b_main": B_MAIN},
    }}
    # ---- shift-0 runs for every configuration
    mk0 = {m: Mkt(mod, close[m], rate) for m in MARKETS}
    R: dict[str, dict[str, dict[str, Any]]] = {cfg: {lv(T): {} for T in LEVELS} for cfg in CFG}
    for cfg in CFG:
        for T in LEVELS:
            for m in MARKETS:
                R[cfg][lv(T)][m] = run_cfg(mod, mk0[m], T, cfg)
    # ---- anchor (stop before writing anything if it fails)
    anc = json.loads(ANCHOR.read_text(encoding="utf-8"))["primary"]
    anchor_rows = []
    for m, segs in (("SOX", ("full", "post")), ("NDX", ("full",)), ("SPX", ("full",))):
        for s in segs:
            for k in ("cagr", "mdd", "w1_min"):
                got, ref = R["A_main"]["1.55"][m][s][k], anc[m][s]["B"][k]
                anchor_rows.append({"market": m, "seg": s, "metric": k, "got": got, "ref": ref, "diff": got - ref})
                if abs(got - ref) > 1e-9:
                    raise RuntimeError(f"anchor mismatch {m} {s} {k}: {got} vs {ref}")
    res["anchor"] = {"pass": True, "tol": 1e-9, "rows": anchor_rows}
    # ---- metrics tables
    res["runs"] = {cfg: {T: {m: R[cfg][T][m] for m in MARKETS} for T in R[cfg]} for cfg in R}
    # ---- Part A verdicts
    A = {"main": {}, "sens": {}}
    for X, B in PAIRS_A:
        A["main"][f"{lv(X)}_vs_{lv(B)}"] = verdict(R["A_main"][lv(X)], R["A_main"][lv(B)])
    for cfg in ("core_pm03", "core_10p", "cash3_daily"):
        A["sens"][cfg] = {f"{lv(X)}_vs_{lv(B)}": verdict(R[cfg][lv(X)], R[cfg][lv(B)]) for X, B in PAIRS_A}
    # fee sensitivity: NDX/SPX with S4-3 per-market 1x fee (criterion c only)
    fee = {}
    for m in ("NDX", "SPX"):
        Mf = Mkt(mod, close[m], rate, fee1=ENGINE_FEE1[m])
        fee[m] = {lv(T): run_cfg(mod, Mf, T, "A_main")["full"]["cagr"] for T in LEVELS}
    A["sens"]["engine_fee_c"] = {f"{lv(X)}_vs_{lv(B)}": {m: fee[m][lv(X)] - fee[m][lv(B)] for m in fee} for X, B in PAIRS_A}
    chg = [lv(X) for X in (1.00, 1.32) if A["main"][f"{lv(X)}_vs_{lv(CURRENT)}"]["all_pass"]]
    cur = all(A["main"][f"{lv(CURRENT)}_vs_{lv(B)}"]["all_pass"] for B in (1.00, 1.32))
    A["decision"] = {"change_candidates": chg, "current_passes": cur,
                     "status": "변경 후보" if chg else ("현행 통과" if cur else "우열 미확인(현행 미검증 유지)")}
    res["A"] = A
    # ---- Part B verdicts
    Bv = {"main": {}, "sens": {}}
    for T in LEVELS:
        Bv["main"][lv(T)] = {"K_vs_S": verdict(R[B_MAIN["K"]][lv(T)], R[B_MAIN["S"]][lv(T)]),
                             "S_vs_K": verdict(R[B_MAIN["S"]][lv(T)], R[B_MAIN["K"]][lv(T)])}
    for name, pair in B_SENS.items():
        Bv["sens"][name] = {lv(T): {"K_vs_S": verdict(R[pair["K"]][lv(T)], R[pair["S"]][lv(T)]),
                                    "S_vs_K": verdict(R[pair["S"]][lv(T)], R[pair["K"]][lv(T)])} for T in LEVELS}
    judged_T = [lv(CURRENT)] + [c for c in chg if c != lv(CURRENT)]
    Bv["decision"] = {}
    for t in judged_T:
        kp, sp = Bv["main"][t]["K_vs_S"]["all_pass"], Bv["main"][t]["S_vs_K"]["all_pass"]
        Bv["decision"][t] = {"K_passes_vs_S": kp, "S_passes_vs_K": sp,
                             "status": "변경 후보(1배 코어)" if kp else ("현행 통과(SOXL)" if sp else "우열 미확인(SOXL 미검증 유지)")}
    # drift effect: +-0.3 band minus daily, per structure
    Bv["drift_effect_cagr"] = {lv(T): {m: {"S": R["cash3_pm03"][lv(T)][m]["full"]["cagr"] - R["cash3_daily"][lv(T)][m]["full"]["cagr"],
                                           "K": R["core_pm03"][lv(T)][m]["full"]["cagr"] - R["A_main"][lv(T)][m]["full"]["cagr"]}
                                       for m in MARKETS} for T in LEVELS}
    res["B"] = Bv
    # ---- shift sensitivity 0-9 (report only)
    shifts = []
    for k in SHIFTS:
        mk = {m: Mkt(mod, close[m], rate, shift=k) for m in MARKETS}
        rr = {cfg: {lv(T): {m: run_cfg(mod, mk[m], T, cfg, segs=("full", "post")) for m in MARKETS} for T in LEVELS}
              for cfg in ("A_main", "core_pm03", "cash3_pm03")}
        row = {"shift": k, "A": {}, "B": {}}
        for X, B in PAIRS_A:
            v = verdict(rr["A_main"][lv(X)], rr["A_main"][lv(B)])
            row["A"][f"{lv(X)}_vs_{lv(B)}"] = {"fails": v["fails"], "a_full": v["a"]["sox_full"], "a_post": v["a"]["sox_post"],
                                               "b_full": v["b"]["sox_full"], "b_post": v["b"]["sox_post"], "c_ndx": v["c"]["ndx_full"],
                                               "c_spx": v["c"]["spx_full"], "d": v["d"]["sox_full"]}
        for T in LEVELS:
            for dirn, (x, b) in (("K_vs_S", ("core_pm03", "cash3_pm03")), ("S_vs_K", ("cash3_pm03", "core_pm03"))):
                v = verdict(rr[x][lv(T)], rr[b][lv(T)])
                row["B"][f"{lv(T)}_{dirn}"] = {"fails": v["fails"], "a_full": v["a"]["sox_full"], "a_post": v["a"]["sox_post"],
                                               "b_full": v["b"]["sox_full"], "b_post": v["b"]["sox_post"], "c_ndx": v["c"]["ndx_full"],
                                               "c_spx": v["c"]["spx_full"], "d": v["d"]["sox_full"]}
        shifts.append(row)
    res["shift_sensitivity"] = shifts
    # ---- path loss (report only)
    PL: dict[str, Any] = {"synthetic": {}, "real": {}}
    for m in MARKETS:
        M = mk0[m]
        P3, P1 = legs(M.F.L["r3"], M.F.L["r1"])
        segs = ("full", "post") if m == "SOX" else ("full",)
        PL["synthetic"][m] = {s: {str(L): path_loss(P3, P1, *M.bounds[s], L) for L in PL_L} for s in segs}
        if m == "SOX":
            P3s, P1s, idxs = P3, P1, M.idx
    # real products run (SOX sessions from 2010-03-11)
    dsox = mk0["SOX"].d
    ds = dsox.loc[POST_START:]
    lr = load_adj("SOXL").pct_change().reindex(ds.index)
    ro = load_adj("SOXX").pct_change().reindex(ds.index)
    miss = int(lr.iloc[1:].isna().sum() + ro.iloc[1:].isna().sum())
    if miss:
        raise RuntimeError(f"{miss} NaN real returns after alignment with SOX sessions")
    lrl, rol = lr.fillna(0.0).tolist(), ro.fillna(0.0).tolist()
    Mr = Mkt(mod, None, rate, d=ds)
    P3r, P1r = legs(lrl, rol)
    PL["real"]["SOXL_SOXX"] = {str(L): path_loss(P3r, P1r, 0, Mr.n, L) for L in PL_L}
    PL["real"]["period"] = {"start": str(Mr.idx[0].date()), "end": str(Mr.idx[-1].date()), "n": Mr.n}
    a_s, b_s = int(idxs.get_loc(SPOT[0])), int(idxs.get_loc(SPOT[1]))
    a_r, b_r = int(Mr.idx.get_loc(SPOT[0])), int(Mr.idx.get_loc(SPOT[1]))
    syn3, syn1 = P3s[b_s] / P3s[a_s] - 1.0, P1s[b_s] / P1s[a_s] - 1.0
    re3, re1 = P3r[b_r] / P3r[a_r] - 1.0, P1r[b_r] / P1r[a_r] - 1.0
    PL["spot"] = {"start": str(SPOT[0].date()), "end": str(SPOT[1].date()), "sox_index": float(close["SOX"][SPOT[1]] / close["SOX"][SPOT[0]] - 1.0),
                  "synthetic_3x": syn3, "synthetic_1x": syn1, "synthetic_PL": syn3 / 3.0 - syn1,
                  "SOXL": re3, "SOXX": re1, "real_PL": re3 / 3.0 - re1}
    res["path_loss"] = PL
    # real-product portfolios vs synthetic fresh from 2010-03-11 (report only)
    real = {}
    for T in LEVELS:
        real[lv(T)] = {}
        for cfg in ("core_pm03", "cash3_pm03", "A_main", "cash3_daily"):
            rr_ = run_cfg(mod, Mr, T, cfg, lev=lrl, one=rol)
            sy_ = run_cfg(mod, Mr, T, cfg)
            keys = ("cagr", "mdd", "w1_min", "worst_day", "meanx")
            real[lv(T)][cfg] = {"real": {**{k: rr_["full"][k] for k in keys}, "adj_per_year": rr_["adj_per_year"]},
                                "synthetic_fresh": {**{k: sy_["full"][k] for k in keys}, "adj_per_year": sy_["adj_per_year"]}}
        real[lv(T)]["K_minus_S_pm03"] = {"real": real[lv(T)]["core_pm03"]["real"]["cagr"] - real[lv(T)]["cash3_pm03"]["real"]["cagr"],
                                         "synthetic_fresh": real[lv(T)]["core_pm03"]["synthetic_fresh"]["cagr"] - real[lv(T)]["cash3_pm03"]["synthetic_fresh"]["cagr"]}
    res["real_products"] = real
    res["meta"]["finished_kst"] = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    RESULTS_JSON.write_text(json.dumps(strip(res), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(strip({"anchor": res["anchor"]["pass"], "A": A["decision"], "B": Bv["decision"]}), ensure_ascii=False, indent=1))
    return 0


# ----------------------------------------------------------------------------
# self-test
# ----------------------------------------------------------------------------
def toy_feat(mod, r3: list[float], r1: list[float], rate: float = 0.0):
    n = len(r3)
    d = pd.DataFrame({"px": [100.0] * n, "rate": [rate] * n, "r3": r3, "r1": r1, "sig_med": [0.3] * n, "dd252": [0.0] * n,
                      "sma150": [90.0] * n, "sma200": [90.0] * n, "sma250": [90.0] * n, "ext": [0.1] * n},
                     index=pd.bdate_range("2000-01-03", periods=n))
    return mod.Feat(d)


def self_test() -> int:
    mod = load_engine()
    checks = []

    def ok(cond, msg):
        checks.append((bool(cond), msg))

    # S1 target -> exposure for both structures, all budgets (zero returns: weights never drift)
    F0 = toy_feat(mod, [0.0] * 10, [0.0] * 10)
    for T in LEVELS:
        for impl in ("core", "cash3"):
            E, X, st = mod.simulate(F0, mod.fixed(T), 0.0, COST, impl, "usd0")
            ok(abs(X[1] - T) < 1e-12 and abs(X[0]) < 1e-15, f"S1 {impl} {T} exposure {X[:3]}")
    # S2 first-fill cost: core trades full weight 1, cash3 trades T/3
    E, X, _ = mod.simulate(F0, mod.fixed(1.55), 0.0, COST, "core", "usd0")
    ok(abs(E[1] - 0.999) < 1e-15, f"S2 core first fill {E[1]}")
    E, X, _ = mod.simulate(F0, mod.fixed(1.55), 0.0, COST, "cash3", "usd0")
    ok(abs(E[1] - (1 - 0.001 * 1.55 / 3)) < 1e-15, f"S2 cash3 first fill {E[1]}")

    # S3/S4 band mapping: rebalance exactly when |E - T| >= 0.30 (reference loop in exposure terms)
    def ref_trades(impl: str, T: float, r3: list[float], r1: list[float]) -> list[int]:
        days = []
        if impl == "cash3":
            w = None
            for i in range(len(r3)):
                if i == 1:
                    w = T / 3
                elif i > 1:
                    g = w * (1 + r3[i]); w = g / (g + 1 - w)
                    if abs(3 * w - T) >= 0.30 - 1e-9:
                        days.append(i); w = T / 3
        else:
            wl = wx = None
            for i in range(len(r3)):
                if i == 1:
                    wl, wx = (T - 1) / 2, 1 - (T - 1) / 2
                elif i > 1:
                    gl, gx = wl * (1 + r3[i]), wx * (1 + r1[i]); tot = gl + gx; wl, wx = gl / tot, gx / tot
                    if abs(3 * wl + wx - T) >= 0.30 - 1e-9:
                        days.append(i); wl, wx = (T - 1) / 2, 1 - (T - 1) / 2
        return days

    rng = np.random.default_rng(20261009)
    n = 2000
    r1 = list(rng.normal(0.002, 0.04, n))  # n=400, sd 0.02 gave too few band crossings for the >=3 check (fixed before --run)
    r3 = [3 * x for x in r1]
    for impl, band in (("cash3", 0.10), ("core", 0.15)):
        for T in (1.32, 1.55):
            F = toy_feat(mod, r3, r1)
            E, X, st = mod.simulate(F, mod.fixed(T), band, COST, impl, "usd0")
            exp = ref_trades(impl, T, r3, r1)
            got = [i for i in range(2, n) if abs(X[i] - T) < 1e-12]
            ok(got == exp and len(exp) >= 3, f"S3 {impl} {T} band->E+-0.3 trades {got[:6]} vs {exp[:6]} (n={len(exp)})")
            ok(float(np.max(np.abs(X[1:] - T))) < 0.30, f"S4 {impl} {T} recorded exposure stays inside +-0.3")
    F = toy_feat(mod, r3, r1)
    E, X, st = mod.simulate(F, mod.fixed(1.00), 0.15, COST, "core", "usd0")
    ok(st["ntr"] == 1 and np.allclose(X[1:], 1.0), f"S4b core 1.00 never rebalances after first fill (ntr={st['ntr']})")

    # S5 independent equity recomputation, core 1.32 daily, toy returns
    n5 = 30
    r3c, r1c = [0.03] * n5, [0.01] * n5
    F = toy_feat(mod, r3c, r1c)
    E, X, _ = mod.simulate(F, mod.fixed(1.32), 0.0, COST, "core", "usd0")
    e, wl, wx, ref = 1.0, 0.0, 0.0, []
    tl, tx = 0.16, 0.84
    for i in range(n5):
        if i > 0:
            gl, gx, gc = wl * 1.03, wx * 1.01, (1 - wl - wx)
            tot = gl + gx + gc; e *= tot; wl, wx = gl / tot, gx / tot
            e -= e * 0.001 * (abs(tl - wl) + abs(tx - wx)); wl, wx = tl, tx
        ref.append(e)
    ok(np.allclose(E, ref, rtol=0, atol=1e-13), "S5 core 1.32 equity recomputation")
    # S6 cash3 1.55 daily recomputation with t-bill cash
    F = toy_feat(mod, r3c, r1c, rate=0.05)
    E, X, _ = mod.simulate(F, mod.fixed(1.55), 0.0, COST, "cash3", "tbill")
    e, w, ref = 1.0, 0.0, []
    p = 1.55 / 3
    for i in range(n5):
        if i > 0:
            g, c = w * 1.03, (1 - w) * (1 + 0.05 / 252)
            e *= (g + c); w = g / (g + c)
            e -= e * 0.001 * abs(p - w); w = p
        ref.append(e)
    ok(np.allclose(E, ref, rtol=0, atol=1e-13), "S6 cash3 1.55 t-bill equity recomputation")

    # S7 verdict boundaries
    def fake(cf, cp, mf, mp, nd, sp, w1):
        return {"SOX": {"full": {"cagr": cf, "mdd": mf, "w1_min": w1}, "post": {"cagr": cp, "mdd": mp, "w1_min": 0.0}},
                "NDX": {"full": {"cagr": nd, "mdd": 0.0, "w1_min": 0.0}}, "SPX": {"full": {"cagr": sp, "mdd": 0.0, "w1_min": 0.0}}}
    base = fake(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)  # zero base: differences equal the thresholds exactly
    edge = fake(0.005, 0.005, -0.05, -0.05, 0.0, 0.0, -0.05)
    v = verdict(edge, base)
    ok(v["all_pass"] and v["fails"] == [], f"S7 boundary passes {v['fails']}")
    for k, bad in (("a", fake(0.0049, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0)), ("b", fake(0.01, 0.01, 0.0, -0.0501, 0.0, 0.0, 0.0)),
                   ("c", fake(0.01, 0.01, 0.0, 0.0, 0.0, -1e-6, 0.0)), ("d", fake(0.01, 0.01, 0.0, 0.0, 0.0, 0.0, -0.0501))):
        v = verdict(bad, base)
        ok(v["fails"] == [k], f"S7 {k} fails alone {v['fails']}")

    # S8 path loss on constant legs: L=2, r3=0.03, r1=0.01
    P3, P1 = legs([0.03] * 6, [0.01] * 6)
    pl = path_loss(P3, P1, 0, 6, 2)
    expv = (1.03 ** 2 - 1) / 3 - (1.01 ** 2 - 1)
    ok(pl["n"] == 4 and abs(pl["median"] - expv) < 1e-15 and abs(pl["min"] - expv) < 1e-15, f"S8 path loss {pl}")
    # S9 extras on a toy equity path
    Et = np.array([1.0, 0.95, 0.85, 1.05, 0.93, 0.80, 1.10])
    Xt = np.ones_like(Et)
    blk = seg_block(mod, Et, Xt, 0, len(Et), pd.bdate_range("2000-01-03", periods=len(Et)))
    ok(blk["dd10_episodes"] == 2 and blk["dd20_episodes"] == 1 and abs(blk["worst_day"] - (0.80 / 0.93 - 1)) < 1e-15,
       f"S9 extras {blk['dd10_episodes']} {blk['dd20_episodes']} {blk['worst_day']}")
    ok(abs(blk["below10_share"] - 3 / 7) < 1e-15, f"S9 below10 share {blk['below10_share']}")

    fails = [m for c, m in checks if not c]
    if fails:
        print(f"SELF-TEST FAIL ({len(fails)} of {len(checks)})")
        for m in fails:
            print(" -", m)
        return 1
    print(f"SELF-TEST PASS ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--run" in sys.argv:
        if self_test() != 0:
            sys.exit(1)
        sys.exit(run_all())
    print(__doc__)
