#!/usr/bin/env python3
"""rule-1028 a-3 pre-registered tests (2026-10-28).

  (1) credit-regime band   (2) SCN-27H1 trigger history   (3) leverage peak-line sell slip

The pre-result contract is docs/claude/rule1028-a3-preregistration-2026-10-28.md
(+ its .sha256 sidecar).  The runner refuses to run if the contract, the inputs,
or the reused runners/modules changed.  Engine, folds, metrics and gates are the
S4 / 08-05 functions themselves; the re-entry setup and timing features are the
08-05 base runner + build_market_snapshot + timing_engine functions, all loaded
read-only (no bytecode written).

Historical research only.  It never reads or changes broker state, never uses
Kiwoom tools, never writes policy, core or registry files, and never places or
schedules an order.  Run it in the cloud container, not on the user's PC.

  --self-test   synthetic-data checks (needs only the reused modules)
  --run         verify hashes, run the protocol, write the results JSON
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
S4_RUNNER = "stock-strategy-system/backtests/walk_forward_soxl_signals_2026-10-01.py"
WF0805 = "stock-strategy-system/backtests/walk_forward_soxl_policy_2026-08-05.py"
BASE0805 = "stock-strategy-system/backtests/backtest_soxl_ema_policy_2026-08-05.py"
BUILDER = "stock-strategy-system/skill-staging/manage-us-stock-strategy/scripts/build_market_snapshot.py"
TIMING = "stock-strategy-system/skill-staging/manage-us-stock-strategy/scripts/timing_engine.py"
PREREG = "docs/claude/rule1028-a3-preregistration-2026-10-28.md"
PREREG_SIDECAR = "docs/claude/rule1028-a3-preregistration-2026-10-28.sha256"
SOXL_JSON = ("stock-strategy-system/backtests/fx5b_inputs_2026-10-09/kiwoom_raw/"
             "SOXL_kiwoom_usa06012_daily_adj1_20261009.json")
SOXX_JSON = ("stock-strategy-system/backtests/kiwoom_raw_2026-10-28/"
             "SOXX_kiwoom_usa06012_daily_adj1_20261028.json")
FRED_DIR = "stock-strategy-system/backtests/rule1028_a3_inputs_2026-10-28/fred"
RESULTS_JSON = "stock-strategy-system/backtests/rule1028_a3_results_2026-10-28.json"

CODE_PINNED = {
    S4_RUNNER: "5294d17cb84a1c0b8c13f5ae11dabbe2171d98cb6f63ce81e9da9c51c95df169",
    WF0805: "896c3b0f563416e9a0d62c179bb6ae8ce171b171a1fa4da549b68232224e023f",
    BASE0805: "519c41b730455652ddde503ddcce82c6a55c0d41d4ae55e5ec8369b6d21b3029",
    BUILDER: "70ce879d982c6e178bb6b1ca88b03d95d64d04e8fe54dc35ee538b7ab67469a3",
    TIMING: "dac71ea7eb5eb2b1e7a2b07734aa360f287fef3ff2487996b1fa9dfc0a5bb332",
}
DATA_PINNED = {
    SOXL_JSON: "e8faa3ac68bf2c283b2c4ae84c232cbb60a3a2b61dddc7869dee03c37aba980f",
    SOXX_JSON: "a5d7ef7f8864ccd22d3a80fdb81059a4148f2d85bfedc9e04cf0def024ecc8db",
}
FRED_SHA = {
    "BAA10Y": "eccf4dc67a5ced4c2a3da5cd1ea5996c6d39fd02e81525a74d453929cf06bc4a",
    "BAMLC0A4CBBB": "b69355c703aaba9cde8b2af381f792f06aeadc3d411dd7dc3c45ae9b80ced424",
    "BAMLH0A0HYM2": "e2a339fed5441282b84462d410e28ec1d6afe87fabe25547208a6f254d0137a4",
    "SP500": "269b80fef05c69061cb7f9c42ac6f12c03b3a1074e21da3c64b501036c7a8193",
    "DGS10": "a9b77d9da4ea71961bcfbf55085ecb20a948bb16bdb48d32058a7aa9e4902994",
    "DFEDTARU": "00fb5af84da59d8fa701ec54105de3c148eb80a5a752154e4a78239349fb3ebb",
    "DCOILWTICO": "7254e3dda1076488f76df8287913095e8ef5c5f6ea104d8384376bc135bc6a06",
    "CPIAUCSL": "d90ebb1d51621d5f948e163327bd95bedf4e2e3dbe69c850173d792ede8752dc",
    "DGS3MO": "739d4ce160fb4f294837e2573d29b5f9a0f4e4642f15e100d841870849c8230a",
}

# Parameters are fixed by the pre-registration; never edit after seeing a result.
CAP = 0.517            # current band target (1.55 / 3), literal as in S4 appendix A2
DEFENSIVE = 0.417      # one notch down, 0.517 - 0.10, literal
BAND = 0.10
PRIMARY = ("2021-08-05", "2026-08-04")
AUX1 = ("2013-08-05", "2021-08-04")
AUX2_START = "2026-08-05"
CRITICAL = ("2019-08-05", "2026-08-04")
COMMON = ("2010-10-18", "2026-10-08")
COSTS = (10.0, 20.0, 50.0)
CREDIT_WINDOW, SP_WINDOW = 126, 252
X_BASE, X_NEIGHBORS = 30, (20, 40)           # credit alarm, integer basis points
P_BASE, P_NEIGHBORS, P_REPORT = 0.30, (0.25, 0.35), (0.20,)
STALE_DAYS, STALE_DAYS_WTI = 7, 10
WTI_PUBLICATION_LAG_DAYS = 7                 # weekly EIA release proxy: obs dated d usable only after d + 7
T1_DAYS, T1_RISE = 1096, 2.0
T2_HIKES = 6
MIN_OFF_SESSIONS = 20                        # episode start = on after >= 20 sessions off (1 G6 and 2)
FWD = (20, 60)
MIN_UNION_EPISODES, MAE_GAP = 5, -0.05
DATA_ERROR_GAP = 0.25
ELIGIBILITY_SESSIONS = 10                    # 08-05 re-entry eligibility expiry
MIN_CAUSALITY_CUTS = 8

_MODS: dict[str, Any] = {}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def s4(root: Path):
    if "s4" not in _MODS:
        _MODS["s4"] = load_module("a3_s4_runner", root / S4_RUNNER)
    return _MODS["s4"]


def wf(root: Path):
    # The same 08-05 module instance that S4's slice_metrics() uses.
    return s4(root).wf_mod()


def base(root: Path):
    # S4's own loader for the 08-05 base runner (technical_components, point_in_time_row).
    return s4(root).base_mod()


def builder(root: Path):
    if "builder" not in _MODS:
        _MODS["builder"] = load_module("a3_snapshot_builder", root / BUILDER)
    return _MODS["builder"]


def timing(root: Path):
    if "timing" not in _MODS:
        _MODS["timing"] = load_module("a3_timing_engine", root / TIMING)
    return _MODS["timing"]


def check_code(root: Path) -> None:
    for rel, want in CODE_PINNED.items():
        got = sha256_file(root / rel)
        if got != want:
            raise RuntimeError(f"{rel}: sha256 {got} != pinned {want}")


def clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        x = float(obj)
        return None if not math.isfinite(x) else x
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return clean(obj.tolist())
    return obj


# ----------------------------------------------------------------------------
# inputs
# ----------------------------------------------------------------------------
def load_kiwoom(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["result"]["return_code"] != 0:
        raise RuntimeError(f"{path.name}: return_code != 0")
    recs = [{"date": pd.Timestamp(r["dt"]), "open": float(r["open_pric"]), "high": float(r["high_pric"]),
             "low": float(r["low_pric"]), "close": float(r["cur_prc"]), "volume": float(r["acc_trde_qty"]),
             "split": str(r.get("upd_stkpc_tp", "")).strip() == "3231"}
            for r in payload["result"]["result_list"]]
    df = pd.DataFrame(recs).set_index("date").sort_index()
    if df.index.has_duplicates:
        raise RuntimeError(f"{path.name}: duplicate dates")
    return df


def load_fred(path: Path, sid: str) -> pd.Series:
    """Full series with NaN for '.'/blank rows (kept so missing months stay visible)."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(raw.columns) != ["observation_date", sid]:
        raise RuntimeError(f"{sid}: unexpected header {list(raw.columns)}")
    idx = pd.to_datetime(raw["observation_date"], format="%Y-%m-%d")
    vals = pd.to_numeric(raw[sid].str.strip(), errors="coerce")
    s = pd.Series(vals.to_numpy(float), index=idx, name=sid).sort_index()
    if s.index.has_duplicates:
        raise RuntimeError(f"{sid}: duplicate dates")
    return s


def check_contract(root: Path) -> dict[str, str]:
    side = (root / PREREG_SIDECAR).read_text(encoding="utf-8")
    field = {ln.split()[0]: ln.split()[1] for ln in side.splitlines() if len(ln.split()) >= 2}
    doc = (root / PREREG).read_bytes()
    got = hashlib.sha256(doc).hexdigest()
    if field.get("raw_sha256") != got:
        raise RuntimeError("pre-registration changed after fixation (sidecar mismatch)")
    runner = sha256_file(Path(__file__).resolve())
    if field.get("runner_sha256") != runner:
        raise RuntimeError("runner changed after fixation (sidecar runner_sha256 mismatch)")
    lf = hashlib.sha256(doc.replace(b"\r\n", b"\n")).hexdigest()
    return {"raw_sha256": got, "lf_sha256": lf, "runner_sha256": runner}


def load_inputs(root: Path) -> dict[str, Any]:
    check_code(root)
    for rel, want in DATA_PINNED.items():
        got = sha256_file(root / rel)
        if got != want:
            raise RuntimeError(f"{rel}: sha256 {got} != pinned {want}")
    fred: dict[str, pd.Series] = {}
    for sid, want in FRED_SHA.items():
        p = root / FRED_DIR / f"{sid}.csv"
        if sha256_file(p) != want:
            raise RuntimeError(f"{sid}: sha256 differs from pre-registration")
        fred[sid] = load_fred(p, sid)
    return {"soxl": load_kiwoom(root / SOXL_JSON), "soxx": load_kiwoom(root / SOXX_JSON), "fred": fred}


# ----------------------------------------------------------------------------
# point-in-time helpers (only observations dated strictly before the session)
# ----------------------------------------------------------------------------
class PIT:
    def __init__(self, valid: pd.Series, dates: pd.DatetimeIndex, stale_days: int):
        self.v = valid.to_numpy(float)
        self.d = valid.index.values.astype("datetime64[D]")
        sd = dates.values.astype("datetime64[D]")
        self.pos = np.searchsorted(self.d, sd, side="left") - 1
        last = self.d[np.clip(self.pos, 0, None)] if len(self.d) else sd
        age = (sd - last).astype(np.int64)
        self.ok = (self.pos >= 0) & (age <= stale_days)


def credit_bp(valid: pd.Series, dates: pd.DatetimeIndex, window: int = CREDIT_WINDOW) -> np.ndarray:
    """round((last - min(last `window` valid obs)) * 100) as scn27h1-triggers.py 39/43; NaN when not computable."""
    pit = PIT(valid, dates, STALE_DAYS)
    rmin = pd.Series(pit.v).rolling(window).min().to_numpy()
    out = np.full(len(dates), np.nan)
    for i, j in enumerate(pit.pos):
        if pit.ok[i] and math.isfinite(rmin[j]):
            out[i] = round((pit.v[j] - rmin[j]) * 100)
    return out


def sp_near_high(valid: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    """1.0 if 100*(SP/H - 1) >= -5 with H = max of last 252 valid obs (scn27h1-triggers.py 40/45), 0.0 if not, NaN if n/a."""
    pit = PIT(valid, dates, STALE_DAYS)
    rmax = pd.Series(pit.v).rolling(SP_WINDOW).max().to_numpy()
    out = np.full(len(dates), np.nan)
    for i, j in enumerate(pit.pos):
        if pit.ok[i] and math.isfinite(rmax[j]):
            dd = 100 * (pit.v[j] / rmax[j] - 1)
            out[i] = 1.0 if dd >= -5 else 0.0
    return out


def defense_a(bp: np.ndarray, x_bp: int) -> np.ndarray:
    return np.where(np.isfinite(bp), bp >= x_bp, False).astype(bool)


def defense_b(bp: np.ndarray, near: np.ndarray, x_bp: int) -> np.ndarray:
    """Entry needs the S&P near its high; then held while the alarm stays on.  State carried
    over the whole common history (no reset at the overlay start)."""
    alarm = defense_a(bp, x_bp)
    d = np.zeros(len(bp), bool)
    for i in range(len(bp)):
        d[i] = bool(alarm[i] and ((i > 0 and d[i - 1]) or near[i] == 1.0))
    return d


def episode_starts(on: np.ndarray, min_off: int = MIN_OFF_SESSIONS) -> list[int]:
    """Sessions where `on` turns true after at least `min_off` consecutive false sessions."""
    out, off = [], 0
    for i in range(len(on)):
        if on[i]:
            if off >= min_off:
                out.append(i)
            off = 0
        else:
            off += 1
    return out


# ----------------------------------------------------------------------------
# SCN triggers (scn27h1-triggers.py definitions applied to every past session)
# ----------------------------------------------------------------------------
def trig_t1(dgs10: pd.Series, dates: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    pit = PIT(dgs10, dates, STALE_DAYS)
    on, comp = np.zeros(len(dates), bool), np.zeros(len(dates), bool)
    sd = dates.values.astype("datetime64[D]")
    for i, j in enumerate(pit.pos):
        if not pit.ok[i]:
            continue
        lo = int(np.searchsorted(pit.d, sd[i] - np.timedelta64(T1_DAYS, "D"), side="left"))
        window = pit.v[lo:j + 1]
        comp[i] = True
        on[i] = bool(pit.v[j] >= window.min() + T1_RISE)
    return on, comp


def hikes_since_cut(values: np.ndarray) -> np.ndarray:
    out = np.zeros(len(values), int)
    count = 0
    for j in range(1, len(values)):
        if values[j] < values[j - 1]:
            count = 0
        elif values[j] > values[j - 1]:
            count += 1
        out[j] = count
    return out


def trig_t2(fed: pd.Series, dates: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    pit = PIT(fed, dates, STALE_DAYS)
    hikes = hikes_since_cut(pit.v)
    on = np.array([bool(pit.ok[i] and hikes[j] >= T2_HIKES) for i, j in enumerate(pit.pos)], bool)
    return on, pit.ok.copy()


def trig_t3(bp: np.ndarray, near: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    comp = np.isfinite(bp) & np.isfinite(near)
    on = comp & np.where(comp, (np.nan_to_num(bp) >= X_BASE) & (near == 1.0), False)
    return on.astype(bool), comp


def cpi_yoy_table(cpi_full: pd.Series) -> dict[pd.Period, float | None]:
    months = {pd.Timestamp(d).to_period("M"): v for d, v in cpi_full.items()}
    out: dict[pd.Period, float | None] = {}
    for m, v in months.items():
        prev = months.get(m - 12)
        out[m] = (100 * (v / prev - 1)) if (prev is not None and math.isfinite(v) and math.isfinite(prev)) else None
    return out


def wti_available(wti: pd.Series) -> pd.Series:
    """Re-date each WTI observation to its assumed availability (date + 7 days, weekly EIA release proxy)."""
    return pd.Series(wti.to_numpy(float), index=wti.index + pd.Timedelta(days=WTI_PUBLICATION_LAG_DAYS))


def trig_t4(wti: pd.Series, cpi_full: pd.Series, dates: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray, list[str]]:
    pit = PIT(wti_available(wti), dates, STALE_DAYS_WTI)
    yoy = cpi_yoy_table(cpi_full)
    on, comp = np.zeros(len(dates), bool), np.zeros(len(dates), bool)
    for i, j in enumerate(pit.pos):
        if not pit.ok[i] or j < 4:
            continue
        comp[i] = True
        five = bool(np.all(pit.v[j - 4:j + 1] >= 100))
        m = dates[i].to_period("M") - 2          # month M is usable from the first session of M+2
        seq = [yoy.get(m - 2), yoy.get(m - 1), yoy.get(m)]
        up2 = all(x is not None for x in seq) and seq[2] > seq[1] > seq[0]
        on[i] = five and up2
    missing = [str(pd.Timestamp(d).to_period("M")) for d, v in cpi_full.items() if not math.isfinite(v)]
    return on, comp, missing


def onsets(on: np.ndarray, comp: np.ndarray, last_idx: int) -> list[int]:
    """On after >= 20 consecutive computable-off sessions; a non-computable session breaks the run."""
    out, off_run = [], 0
    for i in range(len(on)):
        if comp[i] and not on[i]:
            off_run += 1
        elif comp[i] and on[i]:
            if off_run >= MIN_OFF_SESSIONS and i <= last_idx:
                out.append(i)
            off_run = 0
        else:
            off_run = 0
    return out


def union_onsets(union_on: np.ndarray, individual: list[list[int]], last_idx: int) -> list[int]:
    """An individual-trigger onset on a session after >= 20 sessions with the union off
    (a non-computable trigger counts as off for the union)."""
    off_before = np.zeros(len(union_on), int)
    run = 0
    for i in range(len(union_on)):
        off_before[i] = run
        run = 0 if union_on[i] else run + 1
    cand = sorted(set(i for lst in individual for i in lst))
    return [i for i in cand if i <= last_idx and off_before[i] >= MIN_OFF_SESSIONS]


def forward_measures(close: np.ndarray, i: int) -> dict[str, float]:
    c0 = close[i]
    path = close[i:i + 61]
    window_mdd = float(np.min(path / np.maximum.accumulate(path))) - 1
    return {"r20": close[i + 20] / c0 - 1, "r60": close[i + 60] / c0 - 1,
            "mae60": float(np.min(close[i + 1:i + 61])) / c0 - 1, "mdd60_report_only": window_mdd}


def summarize(rows: list[dict[str, float]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    out: dict[str, Any] = {"n": len(rows)}
    for k in ("r20", "r60", "mae60", "mdd60_report_only"):
        x = np.array([r[k] for r in rows], float)
        out[k] = {"median": float(np.median(x)), "p10": float(np.quantile(x, 0.10)), "mean": float(np.mean(x))}
    return out


# ----------------------------------------------------------------------------
# (3) 08-05 timing rows, re-entry setup and the peak-line slot state machine
# ----------------------------------------------------------------------------
def feature_rows(root: Path, df: pd.DataFrame, start: int) -> list[dict[str, Any] | None]:
    """08-05 point-in-time rows from the original modules.  Kiwoom adjusted=1 prices are already
    split-adjusted, so adjclose = close (normalisation factor 1, scale 1)."""
    b, bld = base(root), builder(root)
    f = df[["open", "high", "low", "close", "volume"]].copy()
    f["adjclose"] = f["close"]
    tech, e10, e20, atr = b.technical_components(f, bld)
    rows: list[dict[str, Any] | None] = [None] * len(f)
    for pos in range(max(start, 252), len(f)):
        rows[pos] = b.point_in_time_row(f, tech, e10, e20, atr, pos, bld)
    return rows


def volume_fail_closed(dates: pd.DatetimeIndex, split_l: np.ndarray, early: set[str]) -> np.ndarray:
    """S4 protocol line 91: volume conditions fail closed on an early-close session, the session
    after it, and a split session (here SOXL, whose volume the setup reads)."""
    is_early = np.array([d.date().isoformat() in early for d in dates], bool)
    out = is_early | np.asarray(split_l, bool)
    out[1:] |= is_early[:-1]
    return out


def slot_inputs(root: Path, rows_l: list, rows_x: list, vol_bad: np.ndarray, start: int) -> dict[str, np.ndarray]:
    n = len(rows_l)
    keys = ("below_l", "below_x", "above_l", "above_x", "aligned", "setup")
    out = {k: np.zeros(n, bool) for k in keys}
    tm = timing(root)
    for t in range(start, n):
        r, x = rows_l[t], rows_x[t]
        if r is None or x is None:
            raise RuntimeError(f"timing row missing at position {t}")
        out["below_l"][t], out["above_l"][t] = r["close"] < r["ema20"], r["close"] > r["ema20"]
        out["below_x"][t], out["above_x"][t] = x["close"] < x["ema20"], x["close"] > x["ema20"]
        out["aligned"][t] = bool(out["above_l"][t] and out["above_x"][t]
                                 and r["ema10_above_ema20"] and x["ema10_above_ema20"]
                                 and r["ema20_direction_3d"] == "rising" and x["ema20_direction_3d"] == "rising")
        out["setup"][t] = bool(not vol_bad[t] and
                               tm.watch_setup(r, leveraged=True, proxy_row=x).get("technical_setup_detected", False))
    return out


def slot_path(a: int, close_l: np.ndarray, si: dict[str, np.ndarray], p: float,
              literal: bool = False) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """k[t] = slots held after the close-t decision (3 before a).  Order per close as 08-05 run_staged:
    rearm -> re-entry eligibility -> peak sell -> re-entry.  literal=True is the report-only
    'R5 as written' variant: no EMA20 condition, rearm only on a new closing high."""
    n = len(close_l)
    k = np.full(n, 3, int)
    if a >= n:                                   # history ends before the overlay starts
        return k, []
    hwm = -math.inf
    armed, prev_p = True, False
    held = 3
    fill: int | None = None
    recov = align = 0
    expiry: int | None = None
    events: list[dict[str, Any]] = []
    for t in range(a, n):
        hwm = max(hwm, float(close_l[t]))         # highest completed close since a (never reset)
        hit = bool(close_l[t] <= (1 - p) * hwm)
        cond = hit if literal else bool(hit and si["below_l"][t] and si["below_x"][t])
        both_above = bool(si["above_l"][t] and si["above_x"][t])
        if not armed and fill is not None and t >= fill:
            if literal:
                if close_l[t] >= hwm:
                    armed = True
                    events.append({"idx": t, "kind": "rearm"})
            else:
                recov = recov + 1 if both_above else 0
                if t - fill >= 3 and recov >= 2 and close_l[t] > (1 - p) * hwm:
                    armed = True
                    events.append({"idx": t, "kind": "rearm"})
        align = align + 1 if si["aligned"][t] else 0
        if not both_above:
            expiry = None
        elif align >= 2 and expiry is None:
            expiry = t + ELIGIBILITY_SESSIONS
        if expiry is not None and t > expiry:
            expiry = None
        if armed and cond and not prev_p and held >= 1:
            held -= 1
            armed, fill, recov = False, t + 1, 0
            events.append({"idx": t, "kind": "sell", "close": float(close_l[t]), "hwm": hwm,
                           "close_to_hwm": float(close_l[t]) / hwm, "held_after": held})
        elif held < 3 and expiry is not None and si["setup"][t]:
            held += 1
            align, expiry = 0, None
            events.append({"idx": t, "kind": "reentry", "close": float(close_l[t]), "held_after": held})
        k[t] = held
        prev_p = cond
    return k, events


def slot_mult(root: Path) -> dict[int, float]:
    w = wf(root)
    return {k: float(w.RESIDUAL_FRACTION + sum(w.SLOT_FRACTIONS[:k])) for k in range(4)}


# ----------------------------------------------------------------------------
# engine wrappers (S4 simulate / slice_metrics / gates)
# ----------------------------------------------------------------------------
class Market:
    def __init__(self, root: Path, soxl: pd.DataFrame, soxx: pd.DataFrame, dgs3mo: pd.Series | None, row_start: int):
        self.root = root
        self.dates = soxl.index
        self.O = soxl["open"].to_numpy(float)
        self.C = soxl["close"].to_numpy(float)
        self.open_ok = np.isfinite(self.O) & (self.O > 0) & (soxl["volume"].to_numpy(float) > 0)
        self.days = np.r_[1.0, np.diff(self.dates.values.astype("datetime64[D]").astype(np.int64)).astype(float)]
        self.rate = s4(root).rate_array(self.dates, dgs3mo)
        self.row_start = row_start
        self.vol_bad = volume_fail_closed(self.dates, soxl["split"].to_numpy(bool), s4(root).early_closes())
        self.rows_l = feature_rows(root, soxl, row_start)
        self.rows_x = feature_rows(root, soxx, row_start)
        self.si = slot_inputs(root, self.rows_l, self.rows_x, self.vol_bad, row_start)

    def run(self, target: np.ndarray, cost: float, cash_yield: bool = True, force: np.ndarray | None = None):
        return s4(self.root).simulate(self.O, self.C, self.open_ok, self.days, self.rate, target, BAND,
                                      "band", cost, cash_yield, force=force)


def credit_target(n: int, a: int, d: np.ndarray) -> np.ndarray:
    tgt = np.full(n, CAP)
    tgt[a:] = np.where(d[a:], DEFENSIVE, CAP)
    return tgt


def slot_target(n: int, a: int, k: np.ndarray, mult: dict[int, float], open_ok: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tgt = np.full(n, CAP)
    tgt[a:] = CAP * np.vectorize(mult.get)(k[a:])
    prev = np.r_[3, k[:-1]]
    force = np.zeros(n, bool)
    for t in range(a, n):
        # forced to the new slot target at the next open; kept forced until a tradable open fills it
        force[t] = bool(k[t] != prev[t] or (t > a and force[t - 1] and not open_ok[t]))
    return tgt, force


def evaluate_window(mk: Market, wf_m, soxx_close: pd.DataFrame, window: tuple[str, str],
                    specs: dict[str, dict[str, Any]], gate_rows: dict[str, list[str]], full: bool) -> dict[str, Any]:
    S4 = s4(mk.root)
    dates = mk.dates
    folds = S4.make_folds(*window)
    fold_pos = [S4.positions(dates, f["test_start"], f["test_end"]) for f in folds]
    regimes = [wf_m.regime_label(soxx_close, f) for f in folds]
    a_all, z_all = fold_pos[0][0], fold_pos[-1][1]
    costs = COSTS if full else (10.0,)
    runs = {c: {name: mk.run(s["target"], c, True, s.get("force")) for name, s in specs.items()} for c in costs}
    tot = {c: {name: S4.slice_metrics(r, dates, a_all, z_all, name) for name, r in rc.items()} for c, rc in runs.items()}
    fm = {name: [S4.slice_metrics(r, dates, a, z, name) for (a, z) in fold_pos] for name, r in runs[10.0].items()}
    out: dict[str, Any] = {
        "range": [dates[a_all].date().isoformat(), dates[z_all].date().isoformat()],
        "folds": [{k: v.date().isoformat() for k, v in f.items()} | {"regime": regimes[i]} for i, f in enumerate(folds)],
        "totals_10bp": tot[10.0],
        "fold_metrics": {k: [{kk: m[kk] for kk in ("total_return", "maximum_drawdown", "cagr")} for m in v]
                         for k, v in fm.items()},
    }
    base_tot, base_folds = tot[10.0]["B"], fm["B"]
    wB = runs[10.0]["B"]["W"]
    gates: dict[str, Any] = {}
    for name, nbs in gate_rows.items():
        g = S4.g1_g2(tot[10.0][name], base_tot)
        g.update(S4.gate_folds(fm[name], base_folds, regimes))
        wC = runs[10.0][name]["W"]
        g["report_active_folds"] = sum(1 for (a, z) in fold_pos if np.nanmax(np.abs(wC[a:z + 1] - wB[a:z + 1])) > 1e-9)
        g["report_not_worse_folds"] = sum(
            1 for i in range(len(fold_pos))
            if fm[name][i]["maximum_drawdown"] >= base_folds[i]["maximum_drawdown"] - 1e-12
            and fm[name][i]["total_return"] >= base_folds[i]["total_return"] - 1e-12)
        ev = specs[name]["events"]
        g["G6_independent_observations"] = sum(1 for i in ev["count"] if a_all <= i <= z_all)
        g["G6_secondary_report_only"] = {key: sum(1 for i in idx if a_all <= i <= z_all)
                                         for key, idx in ev.get("secondary", {}).items()}
        g["G6"] = bool(g["G6_independent_observations"] >= 20)
        if full:
            g20 = S4.g1_g2(tot[20.0][name], tot[20.0]["B"])
            c50, b50 = tot[50.0][name], tot[50.0]["B"]
            g["G4_20bp_G1_G2"] = bool(g20["G1"] and g20["G2"])
            g["G4_50bp_direction"] = bool(c50["maximum_drawdown"] > b50["maximum_drawdown"]
                                          and c50["calmar"] is not None and b50["calmar"] is not None
                                          and c50["calmar"] > b50["calmar"])
            passing = 0
            for nb in nbs:
                gn = S4.g1_g2(tot[10.0][nb], base_tot)
                passing += int(gn["G1"] and gn["G2"])
            g["G4_neighbors_passing"], g["G4_neighbors_total"] = passing, len(nbs)
            g["G4_neighbors"] = bool(passing > len(nbs) / 2)
            g["G4"] = bool(g["G4_20bp_G1_G2"] and g["G4_50bp_direction"] and g["G4_neighbors"])
            core_ok = bool(g["G1"] and g["G2"] and g["G3"] and g["G4"] and g["G5"])
            g["G1_to_G5_all_pass"] = core_ok
            g["verdict"] = ("candidate" if core_ok and g["G6"] else
                            "review_only_insufficient_observations" if core_ok else "gate_failed")
            if name not in GATE_ROWS:
                g["verdict"] = "report_only_not_judged"
        gates[name] = g
    out["gates" if full else "gate_reference_report_only"] = gates
    if full:
        out["totals_stress"] = {str(c): tot[c] for c in (20.0, 50.0)}
        zero = {name: mk.run(s["target"], 10.0, False, s.get("force")) for name, s in specs.items()}
        out["totals_zero_cash_yield"] = {name: S4.slice_metrics(r, dates, a_all, z_all, name)
                                         for name, r in zero.items()}
        last = len(dates) - 1
        if dates[last] >= pd.Timestamp(AUX2_START):
            a2, z2 = S4.positions(dates, pd.Timestamp(AUX2_START), dates[last])
            out["aux_after_2026_08_05_report_only"] = {
                "range": [dates[a2].date().isoformat(), dates[z2].date().isoformat()],
                "totals_10bp": {name: S4.slice_metrics(r, dates, a2, z2, name) for name, r in runs[10.0].items()}}
    out["_runs10"] = runs[10.0]
    return out


def build_specs(mk: Market, a: int, d_a: dict[int, np.ndarray], d_b: dict[int, np.ndarray],
                mult: dict[int, float]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    n = len(mk.dates)
    specs: dict[str, dict[str, Any]] = {"B": {"target": np.full(n, CAP), "events": {"count": []}}}
    for x in (X_BASE, *X_NEIGHBORS):
        for tag, d in (("A", d_a[x]), ("B", d_b[x])):
            flips = [i for i in range(1, n) if d[i] and not d[i - 1]]
            specs[f"credit_{tag}_x{x}"] = {"target": credit_target(n, a, d),
                                           "events": {"count": episode_starts(d),
                                                      "secondary": {"false_to_true_transitions": flips}}}
    slot_events: dict[str, list[dict[str, Any]]] = {}
    variants = [(f"peak_p{int(round(p * 100))}", p, False) for p in (P_BASE, *P_NEIGHBORS, *P_REPORT)]
    variants.append(("peak_r5_literal_p30", P_BASE, True))
    for name, p, literal in variants:
        k, ev = slot_path(a, mk.C, mk.si, p, literal=literal)
        tgt, force = slot_target(n, a, k, mult, mk.open_ok)
        specs[name] = {"target": tgt, "force": force, "k": k,
                       "events": {"count": [e["idx"] for e in ev if e["kind"] == "reentry"],
                                  "secondary": {"sells": [e["idx"] for e in ev if e["kind"] == "sell"]}}}
        slot_events[name] = ev
    return specs, slot_events


GATE_ROWS = {
    "credit_A_x30": ["credit_A_x20", "credit_A_x40"],
    "credit_B_x30": ["credit_B_x20", "credit_B_x40"],
    "peak_p30": ["peak_p25", "peak_p35"],
}
REPORT_ROWS = {"peak_p20": [], "peak_r5_literal_p30": []}


# ----------------------------------------------------------------------------
# data audit
# ----------------------------------------------------------------------------
def audit_and_align(root: Path, soxl: pd.DataFrame, soxx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    S4 = s4(root)
    lo, hi = pd.Timestamp(COMMON[0]), pd.Timestamp(COMMON[1])
    common = soxl.index.intersection(soxx.index)
    common = common[(common >= lo) & (common <= hi)]
    exp = S4.expected_sessions(*COMMON)
    missing, extra = exp.difference(common), common.difference(exp)
    c0, c1 = pd.Timestamp(CRITICAL[0]), pd.Timestamp(CRITICAL[1])

    def crit(idx: pd.DatetimeIndex) -> list[str]:
        return [d.date().isoformat() for d in idx if c0 <= d <= c1]

    L, X = soxl.loc[common], soxx.loc[common]
    vals_ok = bool(np.isfinite(L[["open", "high", "low", "close"]].to_numpy()).all()
                   and (L[["open", "high", "low", "close", "volume"]] > 0).all().all()
                   and np.isfinite(X[["open", "high", "low", "close"]].to_numpy()).all()
                   and (X[["open", "high", "low", "close", "volume"]] > 0).all().all())
    rl, rx = L["close"].pct_change(), X["close"].pct_change()
    gap = (rl - 3 * rx).abs()
    flagged = [d.date().isoformat() for d in gap.index[gap > DATA_ERROR_GAP]]
    soxx_exp = S4.expected_sessions(soxx.index[0].date().isoformat(), soxx.index[-1].date().isoformat())
    audit = {
        "common_sessions": len(common), "first": common[0].date().isoformat(), "last": common[-1].date().isoformat(),
        "missing_vs_calendar": [d.date().isoformat() for d in missing], "extra_vs_calendar": [d.date().isoformat() for d in extra],
        "missing_in_critical": crit(missing), "extra_in_critical": crit(extra),
        "values_positive_finite": vals_ok, "data_error_days_gap_gt_0.25": flagged,
        "data_error_days_in_critical": [d for d in flagged if CRITICAL[0] <= d <= CRITICAL[1]],
        "soxx_only_missing_vs_calendar": [d.date().isoformat() for d in soxx_exp.difference(soxx.index)],
        "soxx_only_extra_vs_calendar": [d.date().isoformat() for d in soxx.index.difference(soxx_exp)],
        "split_sessions": {"SOXL": [d.date().isoformat() for d in soxl.index[soxl["split"]]],
                           "SOXX": [d.date().isoformat() for d in soxx.index[soxx["split"]]]},
    }
    if audit["missing_in_critical"] or audit["extra_in_critical"] or not vals_ok or audit["data_error_days_in_critical"]:
        raise RuntimeError("STOP (fail closed): data audit failed inside the critical window or values invalid: "
                           + json.dumps({k: audit[k] for k in ("missing_in_critical", "extra_in_critical",
                                                               "values_positive_finite", "data_error_days_in_critical")}))
    return L, X, audit


# ----------------------------------------------------------------------------
# (1) signals over the full common history and report-only views
# ----------------------------------------------------------------------------
def credit_signals(fred: dict[str, pd.Series], dates: pd.DatetimeIndex, series: str = "BAA10Y"):
    bp = credit_bp(fred[series].dropna(), dates)
    near = sp_near_high(fred["SP500"].dropna(), dates)
    d_a = {x: defense_a(bp, x) for x in (X_BASE, *X_NEIGHBORS)}
    d_b = {x: defense_b(bp, near, x) for x in (X_BASE, *X_NEIGHBORS)}
    return bp, near, d_a, d_b


def episodes(d: np.ndarray, dates: pd.DatetimeIndex, close_x: np.ndarray, lo: int, hi: int) -> list[dict[str, Any]]:
    out, i, n = [], 0, len(d)
    starts = set(episode_starts(d))
    while i < n:
        if d[i] and (i == 0 or not d[i - 1]):
            j = i
            while j + 1 < n and d[j + 1]:
                j += 1
            if j >= lo and i <= hi:
                out.append({"start": dates[i].date().isoformat(), "end": dates[j].date().isoformat(),
                            "sessions": j - i + 1, "soxx_return_start_to_end": close_x[j] / close_x[i] - 1,
                            "counts_for_G6": i in starts, "ongoing_at_data_end": bool(j == n - 1)})
            i = j + 1
        else:
            i += 1
    return out


def release_report(d: np.ndarray, dates: pd.DatetimeIndex, close_x: np.ndarray) -> dict[str, Any]:
    """Report only: SOXX after the defense switches off (first false session after a true run)."""
    last = len(d) - 1 - max(FWD)
    rel = [i for i in range(1, last + 1) if d[i - 1] and not d[i]]
    ev = [forward_measures(close_x, i) | {"date": dates[i].date().isoformat()} for i in rel]
    return {"releases": ev, "summary": summarize(ev),
            "all_sessions": summarize([forward_measures(close_x, i) for i in range(0, last + 1)])}


def concordance(bp: np.ndarray, other_bp: np.ndarray, dates: pd.DatetimeIndex) -> dict[str, Any]:
    both = np.isfinite(other_bp) & np.isfinite(bp)
    return {"comparable_sessions": int(both.sum()),
            "first_comparable": dates[np.argmax(both)].date().isoformat() if both.any() else None,
            "agreement_ratio_x30": float(np.mean((bp[both] >= X_BASE) == (other_bp[both] >= X_BASE))) if both.any() else None,
            "baa_on_x30": int((bp[both] >= X_BASE).sum()), "other_on_x30": int((other_bp[both] >= X_BASE).sum())}


# ----------------------------------------------------------------------------
# (2) SCN history on SOXX sessions (SOXX file to its last session)
# ----------------------------------------------------------------------------
def scn_history(fred: dict[str, pd.Series], soxx: pd.DataFrame) -> dict[str, Any]:
    dates = soxx.index
    close = soxx["close"].to_numpy(float)
    n = len(dates)
    last_idx = n - 1 - max(FWD)
    t1, c1 = trig_t1(fred["DGS10"].dropna(), dates)
    t2, c2 = trig_t2(fred["DFEDTARU"].dropna(), dates)
    bp = credit_bp(fred["BAA10Y"].dropna(), dates)
    near = sp_near_high(fred["SP500"].dropna(), dates)
    t3, c3 = trig_t3(bp, near)
    t4, c4, cpi_missing = trig_t4(fred["DCOILWTICO"].dropna(), fred["CPIAUCSL"], dates)
    bbb_bp = credit_bp(fred["BAMLC0A4CBBB"].dropna(), dates)
    t3_bbb, _ = trig_t3(bbb_bp, near)
    trig = {"T1": (t1, c1), "T2": (t2, c2), "T3": (t3, c3), "T4": (t4, c4)}
    out: dict[str, Any] = {"sessions": [dates[0].date().isoformat(), dates[n - 1].date().isoformat()],
                           "last_start": dates[last_idx].date().isoformat(),
                           "cpi_missing_months": cpi_missing, "triggers": {}}
    individual = []
    for name, (on, comp) in trig.items():
        idx = [i for i in range(last_idx + 1) if comp[i]]
        ons = onsets(on, comp, last_idx)
        individual.append(ons)
        ev = [forward_measures(close, i) | {"date": dates[i].date().isoformat()} for i in ons]
        out["triggers"][name] = {
            "computable_from": dates[idx[0]].date().isoformat() if idx else None,
            "computable_sessions": len(idx), "on_sessions": int(np.sum(on[:last_idx + 1] & comp[:last_idx + 1])),
            "episodes": ev, "episode_summary": summarize(ev),
            "all_sessions_summary": summarize([forward_measures(close, i) for i in idx])}
    union_on = (t1 & c1) | (t2 & c2) | (t3 & c3) | (t4 & c4)
    uons = union_onsets(union_on, individual, last_idx)
    uev = [forward_measures(close, i) | {"date": dates[i].date().isoformat()} for i in uons]
    out["triggers"]["UNION"] = {
        "computable_sessions": last_idx + 1, "on_sessions": int(np.sum(union_on[:last_idx + 1])),
        "episodes": uev, "episode_summary": summarize(uev),
        "all_sessions_summary": summarize([forward_measures(close, i) for i in range(last_idx + 1)])}
    u = out["triggers"]["UNION"]
    k = u["episode_summary"]["n"]
    if k < MIN_UNION_EPISODES:
        reading = "insufficient_sample_keep_a2_option3"
    else:
        gap = u["episode_summary"]["mae60"]["median"] - u["all_sessions_summary"]["mae60"]["median"]
        u["mae60_median_gap"] = gap
        reading = ("worse_than_usual_keep_a2_option3" if gap <= MAE_GAP + 1e-12
                   else "not_different_from_usual_ask_user_about_withdrawing_a2_option3")
    out["reading"] = reading
    both = np.isfinite(bp) & np.isfinite(bbb_bp)
    out["t3_bbb_report_only"] = {
        "comparable_sessions": int(both.sum()),
        "first_comparable": dates[np.argmax(both)].date().isoformat() if both.any() else None,
        "agreement_ratio": float(np.mean(t3[both] == t3_bbb[both])) if both.any() else None,
        "t3_baa_on": int(t3[both].sum()) if both.any() else 0, "t3_bbb_on": int(t3_bbb[both].sum()) if both.any() else 0}
    return out


# ----------------------------------------------------------------------------
# causality (truncation) checks
# ----------------------------------------------------------------------------
def truncate_fred(fred: dict[str, pd.Series], cut: pd.Timestamp) -> dict[str, pd.Series]:
    # Strictly before the cut session: a same-day leak at the cut would then show as a mismatch.
    return {k: v.loc[v.index < cut] for k, v in fred.items()}


def signal_bundle(root: Path, fred: dict[str, pd.Series], L: pd.DataFrame, X: pd.DataFrame, a: int,
                  early: set[str]) -> dict[str, np.ndarray]:
    dates = L.index
    bp, near, d_a, d_b = credit_signals(fred, dates)
    n = len(dates)
    out = {"bp": np.nan_to_num(bp, nan=-9e9), "near": np.nan_to_num(near, nan=-1), "dA": d_a[X_BASE], "dB": d_b[X_BASE]}
    if a < n:
        vol_bad = volume_fail_closed(dates, L["split"].to_numpy(bool), early)
        si = slot_inputs(root, feature_rows(root, L, a), feature_rows(root, X, a), vol_bad, a)
        close = L["close"].to_numpy(float)
        out["k"], _ = slot_path(a, close, si, P_BASE)
        out["k_literal"], _ = slot_path(a, close, si, P_BASE, literal=True)
        for key in ("aligned", "setup", "below_l", "below_x"):
            out[key] = si[key]
    else:
        out["k"] = out["k_literal"] = np.full(n, 3, int)
    t1, _ = trig_t1(fred["DGS10"].dropna(), dates)
    t2, _ = trig_t2(fred["DFEDTARU"].dropna(), dates)
    t3, _ = trig_t3(bp, near)
    t4, _, _ = trig_t4(fred["DCOILWTICO"].dropna(), fred["CPIAUCSL"], dates)
    out.update({"t1": t1, "t2": t2, "t3": t3, "t4": t4})
    return out


def causality_check(root: Path, fred: dict[str, pd.Series], L: pd.DataFrame, X: pd.DataFrame, a: int,
                    cuts: list[int]) -> dict[str, Any]:
    early = s4(root).early_closes()
    full = signal_bundle(root, fred, L, X, a, early)
    bad: list[str] = []
    for cut in cuts:
        cd = L.index[cut]
        part = signal_bundle(root, truncate_fred(fred, cd), L.iloc[:cut + 1], X.iloc[:cut + 1], a, early)
        for key, arr in part.items():
            ref = full[key][:cut + 1] if key in full else None
            if ref is None or len(ref) != len(arr):
                if a < cut + 1:
                    bad.append(f"{key}@{cd.date()}:missing")
                continue
            if not np.allclose(arr, ref, rtol=0, atol=1e-12, equal_nan=True):
                bad.append(f"{key}@{cd.date()}")
    return {"cuts": [L.index[c].date().isoformat() for c in cuts], "mismatches": bad, "passed": not bad}


# ----------------------------------------------------------------------------
# run
# ----------------------------------------------------------------------------
def run_all(root: Path, out_path: Path) -> int:
    contract = check_contract(root)
    data = load_inputs(root)
    fred = data["fred"]
    L, X, audit = audit_and_align(root, data["soxl"], data["soxx"])
    dates = L.index
    a_p = int(dates.searchsorted(pd.Timestamp(PRIMARY[0]), side="left"))
    a_x = int(dates.searchsorted(pd.Timestamp(AUX1[0]), side="left"))
    mk = Market(root, L, X, fred["DGS3MO"].dropna(), row_start=min(a_p, a_x))
    wf_m = wf(root)
    mult = slot_mult(root)
    soxx_close = pd.DataFrame({"close": data["soxx"]["close"]})
    bp, near, d_a, d_b = credit_signals(fred, dates)
    result: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": {"path": PREREG, **contract},
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "pinned_code": CODE_PINNED,
        "pinned_inputs": DATA_PINNED | {f"{FRED_DIR}/{k}.csv": v for k, v in FRED_SHA.items()},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "data_audit": audit | {"tradable_open_all_sessions": bool(mk.open_ok.all()),
                               "volume_fail_closed_sessions_from_row_start": int(mk.vol_bad[mk.row_start:].sum())},
        "slot_multipliers": mult,
        "authority": {"order_authority": False, "quantity_authority": "none", "execution_quantity": None},
    }
    windows: dict[str, Any] = {}
    for label, window, full, a in (("primary", PRIMARY, True, a_p), ("aux_2013_2021_report_only", AUX1, False, a_x)):
        specs, slot_ev = build_specs(mk, a, d_a, d_b, mult)
        rows = GATE_ROWS | REPORT_ROWS
        w = evaluate_window(mk, wf_m, soxx_close, window, specs, rows, full)
        runs10 = w.pop("_runs10")
        same = {name: bool(np.allclose(r["V"][:a + 1], runs10["B"]["V"][:a + 1], rtol=0, atol=1e-12))
                for name, r in runs10.items()}
        if not all(same.values()):
            raise RuntimeError(f"candidate path differs from B before the overlay start: {same}")
        w["overlay_start"] = dates[a].date().isoformat()
        w["identity_before_overlay"] = same
        w["slot_events"] = {name: [e | {"date": dates[e["idx"]].date().isoformat()} for e in ev]
                            for name, ev in slot_ev.items()}
        w["reentry_inputs_report_only"] = {
            "aligned_sessions": int(mk.si["aligned"][a:].sum()),
            "setup_sessions": int(mk.si["setup"][a:].sum()),
            "volume_fail_closed_sessions": int((mk.vol_bad[a:]).sum())}
        windows[label] = w
    result["windows"] = windows
    xclose = X["close"].to_numpy(float)
    result["credit_episodes"] = {f"{tag}_x{x}": episodes(d, dates, xclose, a_x, len(dates) - 1)
                                 for tag, dd in (("A", d_a), ("B", d_b)) for x, d in dd.items()}
    days_in = {}
    for label, (s, e) in (("primary", PRIMARY), ("aux1", AUX1)):
        i0, i1 = s4(root).positions(dates, pd.Timestamp(s), pd.Timestamp(e))
        days_in[label] = {f"{tag}_x{x}": float(np.mean(d[i0:i1 + 1])) for tag, dd in (("A", d_a), ("B", d_b))
                          for x, d in dd.items()}
    result["credit_defense_day_share"] = days_in
    result["credit_release_report_only"] = {f"{tag}_x{X_BASE}": release_report(dd[X_BASE], dates, xclose)
                                            for tag, dd in (("A", d_a), ("B", d_b))}
    result["credit_concordance_report_only"] = {
        "BBB_OAS": concordance(bp, credit_bp(fred["BAMLC0A4CBBB"].dropna(), dates), dates),
        "HY_OAS": concordance(bp, credit_bp(fred["BAMLH0A0HYM2"].dropna(), dates), dates)}
    result["scn_history"] = scn_history(fred, data["soxx"])
    cuts = [int(x) for x in np.linspace(a_p + 30, len(dates) - 2, 6)] + \
           [int(dates.searchsorted(pd.Timestamp(d))) for d in ("2013-03-01", "2018-10-01", "2020-03-16")]
    cuts = sorted(set(cuts))
    if len(cuts) < MIN_CAUSALITY_CUTS:
        raise RuntimeError(f"STOP: fewer than {MIN_CAUSALITY_CUTS} causality cuts ({len(cuts)})")
    result["causality_real"] = causality_check(root, fred, L, X, a_p, cuts)
    if not result["causality_real"]["passed"]:
        raise RuntimeError(f"STOP: causality check failed {result['causality_real']['mismatches'][:10]}")
    out_path.write_text(json.dumps(clean(result), ensure_ascii=False, indent=1), encoding="utf-8")
    g = windows["primary"]["gates"]
    print(json.dumps({"status": "written", "path": str(out_path),
                      "verdicts": {k: v["verdict"] for k, v in g.items()},
                      "scn_reading": result["scn_history"]["reading"]}, ensure_ascii=False))
    return 0


# ----------------------------------------------------------------------------
# self-test (synthetic data)
# ----------------------------------------------------------------------------
def synthetic(root: Path, seed: int = 11):
    S4 = s4(root)
    rng = np.random.default_rng(seed)
    dates = S4.expected_sessions("2015-01-02", "2019-12-31")
    n = len(dates)
    rx = rng.normal(0.0006, 0.018, n)
    rx[500:540] = rng.normal(-0.02, 0.03, 40)            # a crash
    rx[700:720] = rng.normal(0.012, 0.02, 20)            # a rebound
    cx = 100 * np.cumprod(1 + rx)
    cl = 20 * np.cumprod(1 + 3 * rx)
    gap = rng.normal(0, 0.004, n)

    def frame(c, vol_scale):
        o = np.r_[c[0], c[:-1]] * (1 + gap)
        hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.006, n)))
        lo_ = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.006, n)))
        vol = vol_scale * np.exp(rng.normal(0, 0.35, n))
        return pd.DataFrame({"open": o, "high": hi, "low": lo_, "close": c, "volume": vol,
                             "split": np.zeros(n, bool)}, index=dates)

    L, X = frame(cl, 2e6), frame(cx, 1e6)
    L.iloc[600, L.columns.get_loc("split")] = True
    bd = pd.bdate_range("2012-01-02", "2019-12-31")
    baa = pd.Series(2.0 + np.cumsum(rng.normal(0, 0.02, len(bd))), index=bd).round(2)
    baa.iloc[1100:1180] += 0.6
    sp = pd.Series(2000 * np.cumprod(1 + rng.normal(0.0004, 0.01, len(bd))), index=bd).round(2)
    dgs10 = pd.Series(2.0 + np.cumsum(rng.normal(0, 0.03, len(bd))), index=bd).round(2)
    fed_days = pd.date_range("2012-01-01", "2019-12-31", freq="D")
    fed = pd.Series(0.25, index=fed_days)
    for i, d in enumerate(pd.date_range("2016-01-15", periods=8, freq="90D")):
        fed.loc[d:] = 0.25 + 0.25 * (i + 1)
    fed.loc["2019-08-01":] = fed.loc["2019-07-31"] - 0.25
    wti = pd.Series(np.r_[np.full(len(bd) // 2, 90.0), np.full(len(bd) - len(bd) // 2, 105.0)], index=bd)
    months = pd.date_range("2011-01-01", "2019-11-01", freq="MS")
    cpi = pd.Series(np.linspace(220, 260, len(months)) * (1 + 0.002 * np.sin(np.arange(len(months)))), index=months)
    cpi.iloc[60] = np.nan
    fred = {"BAA10Y": baa, "BAMLC0A4CBBB": baa - 0.8, "BAMLH0A0HYM2": baa + 1.5, "SP500": sp, "DGS10": dgs10,
            "DFEDTARU": fed, "DCOILWTICO": wti, "CPIAUCSL": cpi, "DGS3MO": dgs10 * 0 + 1.0}
    return L, X, fred


def hand_inputs(n: int, below: list[int], above: list[int], aligned: list[int], setup: list[int]) -> dict[str, np.ndarray]:
    si = {k: np.zeros(n, bool) for k in ("below_l", "below_x", "above_l", "above_x", "aligned", "setup")}
    for key, idx in (("below_l", below), ("below_x", below), ("above_l", above), ("above_x", above),
                     ("aligned", aligned), ("setup", setup)):
        si[key][idx] = True
    return si


def self_test(root: Path) -> None:
    check_code(root)
    S4 = s4(root)
    mult = slot_mult(root)
    assert math.isclose(mult[3], 1.0) and math.isclose(mult[0], 27 / 99) and math.isclose(mult[2], 75 / 99)
    # 1. integer basis points as scn27h1 (round((b - low) * 100)); 2.53 - 2.23 is 29.999.. -> 30
    s = pd.Series([2.23, 2.40, 2.53], index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]))
    bp = credit_bp(s, pd.DatetimeIndex(["2020-01-06"]), window=3)
    assert bp[0] == 30 and (2.53 - 2.23) < 0.30, bp
    # 2. strictly-before rule: a same-day observation is never used
    bp2 = credit_bp(s, pd.DatetimeIndex(["2020-01-03"]), window=2)
    assert bp2[0] == 17, bp2                        # uses 01-01..01-02 only
    # 3. staleness
    assert np.isnan(credit_bp(s, pd.DatetimeIndex(["2020-01-20"]), window=3)[0])
    # 4. T2 generalisation
    assert list(hikes_since_cut(np.array([1, 1, 1.25, 1.5, 1.25, 1.5, 1.75, 1.75]))) == [0, 0, 1, 2, 0, 1, 2, 2]
    # 5. CPI timing: month M usable from the first session of M+2; WTI dated d usable after d + 7
    months = pd.date_range("2018-01-01", "2020-06-01", freq="MS")
    cpi = pd.Series(100 * np.exp(0.001 * np.arange(len(months), dtype=float) ** 2), index=months)  # YoY rising
    wti = pd.Series(120.0, index=pd.bdate_range("2020-01-01", "2020-07-31"))
    on, comp, _ = trig_t4(wti, cpi, pd.DatetimeIndex(["2020-04-30", "2020-05-01"]))
    assert comp.all() and on.all()
    m_apr, m_may = pd.Timestamp("2020-04-30").to_period("M") - 2, pd.Timestamp("2020-05-01").to_period("M") - 2
    assert str(m_apr) == "2020-02" and str(m_may) == "2020-03"
    w2 = pd.Series([90.0, 90, 90, 90, 90, 120, 120, 120, 120, 120],
                   index=pd.bdate_range("2020-03-02", periods=10))      # 120 from 03-09 to 03-13
    on2, _, _ = trig_t4(w2, cpi, pd.DatetimeIndex(["2020-03-16", "2020-03-20", "2020-03-23"]))
    assert list(on2) == [False, False, True], on2   # 03-13 (5th 120) usable only from 03-21
    # 6. onset rules
    on = np.array([0] * 25 + [1, 1, 0, 1] + [0] * 19 + [1], bool)
    assert onsets(on, np.ones(len(on), bool), len(on)) == [25], onsets(on, np.ones(len(on), bool), len(on))
    assert episode_starts(on) == [25]
    u_on = np.array([0] * 30 + [1] * 3 + [0] * 30, bool)
    assert union_onsets(u_on, [[30], [31]], 100) == [30]          # a second trigger inside a union episode
    assert union_onsets(u_on, [[], [31]], 100) == []              # union already on at 31
    # 7. slot machine hand cases (timing inputs injected)
    n = 30
    cl = np.array([100, 110, 120, 110, 100, 90, 84, 83, 82, 85, 90, 95, 100, 101, 102, 103, 104, 105, 106, 107,
                   80, 79, 78, 90, 100, 110, 120, 125, 126, 127], float)
    above = [11, 12, 13, 14, 15, 16, 17, 18, 19, 24, 25, 26, 27, 28, 29]
    si = hand_inputs(n, [5, 6, 7, 8, 20, 21, 22], above, [13, 14, 26, 27], [16, 27])
    k, ev = slot_path(0, cl, si, 0.30)
    kinds = [(e["idx"], e["kind"]) for e in ev]
    # HWM 120 (closes only) -> line 84: day 6 close 84 <= 84, both below, P false on 5 -> sell (fill 7).
    # Rearm: t - 7 >= 3 and two both-above closes (11, 12) and close > 84 -> day 12.
    # Eligibility: aligned 13, 14 -> expiry 24; setup first on 16 -> re-entry 16.
    # Day 20 close 80 <= 84, below, P false on 19 -> sell.  Rearm 25 (fill 21; above 24, 25).
    # Eligibility: aligned 26, 27 -> re-entry 27 (setup on 27).
    assert kinds == [(6, "sell"), (12, "rearm"), (16, "reentry"), (20, "sell"), (25, "rearm"), (27, "reentry")], kinds
    assert k[6] == 2 and k[15] == 2 and k[16] == 3 and k[20] == 2 and k[27] == 3, k
    # 7a. eligibility expires after ten sessions and is cleared by a close below EMA20
    si_x = hand_inputs(n, [5, 6, 7, 8], list(range(11, 30)), [13, 14], [26])
    k_x, ev_x = slot_path(0, cl, si_x, 0.30)
    assert not any(e["kind"] == "reentry" for e in ev_x), ev_x      # expiry 24 < 26
    si_c = hand_inputs(n, [5, 6, 7, 8], [11, 12, 13, 14, 15, 17, 18, 19], [13, 14], [17])
    k_c, ev_c = slot_path(0, cl, si_c, 0.30)
    assert not any(e["kind"] == "reentry" for e in ev_c), ev_c      # day 16 not above -> eligibility gone
    # 7b. exhaustion: repeated fresh breaches consume at most three slots
    cl2 = np.array([100, 60, 99, 99, 99, 99, 60, 99, 99, 99, 99, 60, 99, 99, 99, 99, 60], float)
    m2 = len(cl2)
    b2 = list(np.where(cl2 < 70)[0]); a2 = list(np.where(cl2 >= 70)[0])
    k2, ev2 = slot_path(0, cl2, hand_inputs(m2, b2, a2, [], []), 0.30)
    assert [e["kind"] for e in ev2].count("sell") == 3 and k2[-1] == 0, (k2, ev2)
    # 7c. literal R5: once per episode, rearm only at a new closing high
    cl3 = np.array([100, 69, 75, 68, 80, 101, 70, 72], float)
    k3, ev3 = slot_path(0, cl3, hand_inputs(len(cl3), [], [], [], []), 0.30, literal=True)
    assert [(e["idx"], e["kind"]) for e in ev3] == [(1, "sell"), (5, "rearm"), (6, "sell")], ev3
    # 7d. force persists until a tradable open
    kk = np.array([3, 3, 2, 2, 2, 2])
    _, fz = slot_target(6, 1, kk, mult, np.array([True, True, True, False, True, True]))
    assert list(fz) == [False, False, True, True, False, False], fz
    # 8. synthetic market: 08-05 rows, engine identity before the overlay and truncation causality
    L, X, fred = synthetic(root)
    a = 400
    mk = Market(root, L, X, fred["DGS3MO"], row_start=a)
    early = S4.early_closes()
    vb = volume_fail_closed(L.index, L["split"].to_numpy(bool), early)
    e0 = next(i for i, d in enumerate(L.index) if d.date().isoformat() in early)
    assert vb[600] and not vb[601] and vb[e0] and vb[e0 + 1] and not vb[e0 + 2], (e0, vb[e0:e0 + 3])
    bp, near, d_a, d_b = credit_signals(fred, L.index)
    specs, _ = build_specs(mk, a, d_a, d_b, mult)
    base_run = mk.run(specs["B"]["target"], 10.0)
    for name, sp_ in specs.items():
        r = mk.run(sp_["target"], 10.0, True, sp_.get("force"))
        assert np.allclose(r["V"][:a + 1], base_run["V"][:a + 1], rtol=0, atol=1e-12), name
    assert any(d_a[X_BASE][a:]) and any(specs["peak_p30"]["k"][a:] < 3), "synthetic data should exercise both rules"
    assert mk.si["setup"][a:].any() and mk.si["aligned"][a:].any(), "synthetic data should exercise the setup"
    cuts = [a - 50] + [int(x) for x in np.linspace(a + 5, len(L) - 2, 9)]
    cc = causality_check(root, fred, L, X, a, cuts)
    assert cc["passed"], cc["mismatches"][:10]
    # 8b. the same check catches deliberate leaks: a same-day FRED observation, tomorrow's close
    g = globals()
    pit_init, rows_fn = PIT.__init__, g["feature_rows"]

    def same_day(self, valid, dates, stale_days):
        pit_init(self, valid, dates, stale_days)
        self.pos = np.searchsorted(self.d, dates.values.astype("datetime64[D]"), side="right") - 1

    def next_close(root_, df, start):
        df2 = df.copy()
        df2["close"] = df2["close"].shift(-1).fillna(df2["close"])
        return rows_fn(root_, df2, start)

    try:
        PIT.__init__ = same_day
        leak_fred = causality_check(root, fred, L, X, a, cuts)
        PIT.__init__ = pit_init
        g["feature_rows"] = next_close
        leak_price = causality_check(root, fred, L, X, a, cuts)
    finally:
        PIT.__init__, g["feature_rows"] = pit_init, rows_fn
    assert not leak_fred["passed"] and not leak_price["passed"], (leak_fred["mismatches"][:3],
                                                                  leak_price["mismatches"][:3])
    # 9. SCN history pipeline runs end to end on synthetic data
    sx = scn_history(fred, X)
    assert "reading" in sx and sx["triggers"]["UNION"]["computable_sessions"] > 0
    print(json.dumps({"status": "passed", "slot_multipliers": mult, "causality_cuts": len(cuts),
                      "leaks_caught": {"same_day_fred": len(leak_fred["mismatches"]),
                                       "next_day_close": len(leak_price["mismatches"])},
                      "synthetic_setup_sessions": int(mk.si["setup"][a:].sum()),
                      "synthetic_reentries_p30": len(specs["peak_p30"]["events"]["count"]),
                      "synthetic_union_episodes": sx["triggers"]["UNION"]["episode_summary"]["n"]}))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    root = args.root.resolve()
    if args.self_test:
        self_test(root)
        return 0
    if args.run:
        return run_all(root, args.out or (root / RESULTS_JSON))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
