#!/usr/bin/env python3
"""strategy-1101 (4): pre-registered defensive-root replay (2026-11-01).

Question (contract: docs/claude/strategy1101-root-preregistration-2026-11-01.md + its .sha256):
  with the 3x product held at 10% of the account (adopted structure target), does holding the
  freed sleeve (27.6% of the account) in energy + healthcare (XLE 50 / XLV 50) beat holding it in
  cash (the Champion), and beat the same-nominal-exposure simple alternative (SPY)?

Stylized account (ratios only, strategy-revision-2026-11-01.md 4-3 S0): AI-infrastructure root 1x =
SOXX 62.4%, 3x = SOXL 10.0%, sleeve 27.6%.  Constant mix, rebalanced to the targets on the first
session of each calendar quarter (decided at the previous regular-session close, filled at that
open; a session with any invalid open freezes the fill until the next session with all opens valid).
Price returns only (Kiwoom split-adjusted daily bars, dividends not included); judged cash earns DGS3MO
(as S4, a-3 and crash1031), 0% cash is report-only.

Reused read-only (pinned): S4 runner (calendar, folds, slices, metrics, G1/G2, G3/G5) and through
it the 08-05 runner (metrics, regime labels).  New: the multi-asset constant-mix engine, the data
audit for five tickers, the truncation guard, the identity check against pinned Nasdaq public copies,
the policy-style exposure E (report only), SOXX drawdown episodes split by the 10-year yield change
(report only).

Historical research only: no broker, no Kiwoom tools, no policy, core or registry writes, no orders.
Run it in the cloud container, not on the user's PC.  Any STOP writes no result.

  --self-test   synthetic and hand-built checks (no contract and no market data needed)
  --run         verify hashes, run the contract once, write the results JSON (never overwrites)
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
S4_RUNNER = "stock-strategy-system/backtests/walk_forward_soxl_signals_2026-10-01.py"
WF0805 = "stock-strategy-system/backtests/walk_forward_soxl_policy_2026-08-05.py"
BASE0805 = "stock-strategy-system/backtests/backtest_soxl_ema_policy_2026-08-05.py"
CODE_PINNED = {
    S4_RUNNER: "5294d17cb84a1c0b8c13f5ae11dabbe2171d98cb6f63ce81e9da9c51c95df169",
    WF0805: "896c3b0f563416e9a0d62c179bb6ae8ce171b171a1fa4da549b68232224e023f",
    BASE0805: "519c41b730455652ddde503ddcce82c6a55c0d41d4ae55e5ec8369b6d21b3029",
}
FRED_DIR = "stock-strategy-system/backtests/rule1028_a3_inputs_2026-10-28/fred"
FRED_PINNED = {
    "DGS10": "a9b77d9da4ea71961bcfbf55085ecb20a948bb16bdb48d32058a7aa9e4902994",
    "DGS3MO": "739d4ce160fb4f294837e2573d29b5f9a0f4e4642f15e100d841870849c8230a",
}
PREREG = "docs/claude/strategy1101-root-preregistration-2026-11-01.md"
PREREG_SIDECAR = "docs/claude/strategy1101-root-preregistration-2026-11-01.sha256"
INPUTS_MANIFEST = "docs/claude/strategy1101-root-inputs/inputs-manifest.json"
RESULTS_JSON = "docs/claude/strategy1101-root-results.json"
KST = timezone(timedelta(hours=9))

# Parameters are fixed by the pre-registration; never edit after seeing a result.
TICKERS = ("SOXX", "SOXL", "XLE", "XLV", "SPY")
MULT = {"SOXX": 1.0, "SOXL": 3.0, "XLE": 1.0, "XLV": 1.0, "SPY": 1.0}
CORE = {"SOXX": 0.624, "SOXL": 0.100}
SLEEVE = 0.276
FIRST_ALLOWED = "2010-10-18"          # Kiwoom SOXX history start (kiwoom_raw_sources 2026-10-28)
VERDICT_END = "2026-08-04"            # last fold boundary on the S4 schedule (02-05 / 08-05)
PRIMARY_SUB = ("2021-08-05", "2026-08-04")   # S4 primary window, report only here
TRAIN_MONTHS = 24                     # 08-05 regime_label training window
MIN_FOLDS = 20                        # G6
COSTS = (10.0, 20.0, 50.0)
JUDGE_COST = 50.0                     # G4 (b), G7, G8: the user's real fee 25bp + 25bp slippage per traded weight
DATA_ERROR_LEV = 0.25                 # |r(SOXL) - 3 r(SOXX)|
DATA_ERROR_ONE = 0.25                 # |r| of a 1x ETF in one session
EPISODE_DD = 0.20                     # report: SOXX close drawdown from its running peak
RATE_RISE_PP = 0.75                   # report: DGS10 change peak -> trough that labels an episode "rate"
MIN_CAUSALITY_CUTS = 8                # decision-day cuts (plus 4 other days and the second-to-last session)
MAX_CAL_GAPS = 3                      # calendar mismatches inside the critical window that are only recorded
KNOWN_FIRST = {"SOXX": "2010-10-18", "SOXL": "2010-04-05"}   # earlier full Kiwoom fetches (truncation guard)
LATE_START = "2011-02-05"             # a later first row moves the verdict start: needs a confirming fetch
SPLIT_CODE = "3231"
IDENTITY_DIR = "docs/claude/strategy1101-root-inputs/nasdaq-identity"   # already-seen Nasdaq public daily copies
IDENTITY_PINNED = {
    "SOXX": "ccc5156f913cb3bb3487ec560b4e0d4edf0f4132bebadd82ff335ff47ba9f22b",
    "SOXL": "83d7283f7cda0923216bb616d2d1b1efa3b805baaa655ef1a18ccfab2f83bf0a",
    "XLE": "bc267acf6a7d8f8b045b063496dfdada65f7fc50ba5645908a27df9e723f5d42",
    "XLV": "a0df405dc8e00df359b4415a47820d025ab86a4b90574144a0412be2f322a8b9",
    "SPY": "f6a2e9b218fef6fe1b12101acd7466ccb35cbd831e72f3225b90216b0dd0034f",
}
IDENTITY_SESSIONS, IDENTITY_MIN, IDENTITY_TOL = 60, 20, 0.01

ARMS: dict[str, dict[str, float]] = {
    "B_cash": {},                                  # Champion: the sleeve stays cash (NO_CHANGE)
    "R_eh50": {"XLE": 0.50, "XLV": 0.50},          # judged row
    "R_eh40": {"XLE": 0.40, "XLV": 0.60},          # neighbour (G4)
    "R_eh60": {"XLE": 0.60, "XLV": 0.40},          # neighbour (G4)
    "C_spy": {"SPY": 1.00},                        # same nominal exposure simple alternative (G8)
}
JUDGED, BASE, CTRL, NEIGHBORS = "R_eh50", "B_cash", "C_spy", ("R_eh40", "R_eh60")
REPORT_ARMS: dict[str, dict[str, float]] = {
    "R_eh50_half": {"XLE": 0.25, "XLV": 0.25},     # half the sleeve in E/H, half in cash
}

_MODS: dict[str, Any] = {}


# ----------------------------------------------------------------------------
# helpers and pinned modules
# ----------------------------------------------------------------------------
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


def check_code(root: Path) -> None:
    for rel, want in CODE_PINNED.items():
        got = sha256_file(root / rel)
        if got != want:
            raise RuntimeError(f"STOP: {rel}: sha256 {got} != pinned {want}")


def s4(root: Path):
    if "s4" not in _MODS:
        check_code(root)
        _MODS["s4"] = load_module("s1101_s4_runner", root / S4_RUNNER)
    return _MODS["s4"]


def wf(root: Path):
    return s4(root).wf_mod()          # the same 08-05 module instance that S4 slice_metrics() uses


def clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        x = float(obj)
        return None if not math.isfinite(x) else x
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return clean(obj.tolist())
    return obj


def arm_weights(sleeve: dict[str, float]) -> dict[str, float]:
    w = dict(CORE)
    for t, share in sleeve.items():
        w[t] = w.get(t, 0.0) + SLEEVE * share
    return w


# ----------------------------------------------------------------------------
# inputs (Kiwoom usa06012 daily, adjusted=1; FRED DGS10 / DGS3MO from the a-3 inputs)
# ----------------------------------------------------------------------------
def load_kiwoom(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["result"]["return_code"] != 0:
        raise RuntimeError(f"STOP: {path.name}: return_code != 0")
    recs = [{"date": pd.Timestamp(r["dt"]), "open": float(r["open_pric"]), "high": float(r["high_pric"]),
             "low": float(r["low_pric"]), "close": float(r["cur_prc"]), "volume": float(r["acc_trde_qty"]),
             "adj_code": str(r.get("upd_stkpc_tp", "")).strip()}
            for r in payload["result"]["result_list"]]
    df = pd.DataFrame(recs).set_index("date").sort_index()
    df["split"] = df["adj_code"] == SPLIT_CODE
    if df.index.has_duplicates:
        raise RuntimeError(f"STOP: {path.name}: duplicate dates")
    return df


def load_fred(path: Path, sid: str) -> pd.Series:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(raw.columns) != ["observation_date", sid]:
        raise RuntimeError(f"STOP: {sid}: unexpected header {list(raw.columns)}")
    idx = pd.to_datetime(raw["observation_date"], format="%Y-%m-%d")
    vals = pd.to_numeric(raw[sid].str.strip(), errors="coerce")
    s = pd.Series(vals.to_numpy(float), index=idx, name=sid).sort_index()
    if s.index.has_duplicates:
        raise RuntimeError(f"STOP: {sid}: duplicate dates")
    return s


def check_contract(root: Path) -> dict[str, Any]:
    """Sidecar lines: raw_sha256, lf_sha256, runner_sha256 (current files), fixed_at (the original lock,
    exactly once, kept through amendments) and optional amended_at lines (section 10 amendments)."""
    side = (root / PREREG_SIDECAR).read_text(encoding="utf-8")
    pairs = [(ln.split()[0], ln.split()[1]) for ln in side.splitlines() if len(ln.split()) >= 2]
    field = dict(pairs)
    doc = (root / PREREG).read_bytes()
    got = hashlib.sha256(doc).hexdigest()
    if field.get("raw_sha256") != got:
        raise RuntimeError("STOP: pre-registration changed after fixation (sidecar mismatch)")
    runner = sha256_file(Path(__file__).resolve())
    if field.get("runner_sha256") != runner:
        raise RuntimeError("STOP: runner changed after fixation (sidecar runner_sha256 mismatch)")
    fixed = [v for k, v in pairs if k == "fixed_at"]
    if len(fixed) != 1:
        raise RuntimeError("STOP: sidecar must hold exactly one fixed_at (the original lock)")
    amended = [v for k, v in pairs if k == "amended_at"]
    for t in [fixed[0], *amended]:
        if datetime.fromisoformat(t).tzinfo is None:
            raise RuntimeError("STOP: sidecar times need a UTC offset")
    if any(datetime.fromisoformat(t) <= datetime.fromisoformat(fixed[0]) for t in amended):
        raise RuntimeError("STOP: an amendment must come after the original lock")
    return {"raw_sha256": got, "lf_sha256": hashlib.sha256(doc.replace(b"\r\n", b"\n")).hexdigest(),
            "runner_sha256": runner, "fixed_at": fixed[0], "amended_at": amended}


def check_manifest(root: Path, fixed_at: str) -> dict[str, Any]:
    """Market data are fetched only after fixation; the manifest records each file once."""
    man = json.loads((root / INPUTS_MANIFEST).read_text(encoding="utf-8"))
    t_fixed = datetime.fromisoformat(fixed_at)
    if t_fixed.tzinfo is None:
        raise RuntimeError("STOP: sidecar fixed_at has no UTC offset")
    files = man.get("files") or {}
    if sorted(files) != sorted(TICKERS):
        raise RuntimeError(f"STOP: manifest tickers {sorted(files)} != {sorted(TICKERS)}")
    for tk, ent in files.items():
        got = sha256_file(root / ent["path"])
        if got != ent["sha256"]:
            raise RuntimeError(f"STOP: {tk}: sha256 {got} != manifest {ent['sha256']}")
        t_call = datetime.fromisoformat(ent["called_kst"])
        if t_call.tzinfo is None:
            raise RuntimeError(f"STOP: {tk}: called_kst has no UTC offset")
        if t_call < t_fixed:
            raise RuntimeError(f"STOP: {tk} was fetched before the contract was fixed")
        for key in ("rows", "first", "last"):
            if key not in ent:
                raise RuntimeError(f"STOP: {tk}: manifest entry has no {key}")
        conf = ent.get("confirm")
        if conf is not None:
            if sha256_file(root / conf["path"]) != conf["sha256"]:
                raise RuntimeError(f"STOP: {tk}: confirming fetch sha256 differs from the manifest")
            t_conf = datetime.fromisoformat(conf["called_kst"])
            if t_conf.tzinfo is None or t_conf < t_fixed:
                raise RuntimeError(f"STOP: {tk}: confirming fetch time missing an offset or before the lock")
    return man


def check_inputs(root: Path, man: dict[str, Any], frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """The manifest must describe the files as loaded (rows, first, last).  Truncation guard (the response
    carries no continuation flag): SOXX / SOXL must start no later than the earlier full Kiwoom fetches;
    any ticker starting after LATE_START (which would move the verdict start) needs a confirming fetch,
    saved and listed in the manifest, holding exactly the same dates up to this file's last date (newer
    rows of the confirming fetch are ignored)."""
    out = {}
    for tk in TICKERS:
        ent, df = man["files"][tk], frames[tk]
        first, last = df.index[0].date().isoformat(), df.index[-1].date().isoformat()
        if int(ent["rows"]) != len(df) or ent["first"] != first or ent["last"] != last:
            raise RuntimeError(f"STOP: {tk}: manifest rows/first/last differ from the file "
                               f"({ent['rows']}, {ent['first']}, {ent['last']} vs {len(df)}, {first}, {last})")
        if tk in KNOWN_FIRST and first > KNOWN_FIRST[tk]:
            raise RuntimeError(f"STOP: {tk} starts {first}, later than the earlier full fetch {KNOWN_FIRST[tk]} (truncated?)")
        confirmed = None
        if first > LATE_START:
            conf = ent.get("confirm")
            if conf is None:
                raise RuntimeError(f"STOP: {tk} starts {first} (after {LATE_START}) without a confirming fetch")
            cdf = load_kiwoom(root / conf["path"])
            if not cdf.index[cdf.index <= df.index[-1]].equals(df.index):
                raise RuntimeError(f"STOP: {tk}: the confirming fetch has other dates up to {last} (truncated fetch?)")
            confirmed = {"first": cdf.index[0].date().isoformat(), "rows": int(len(cdf)),
                         "newer_rows_ignored": int((cdf.index > df.index[-1]).sum())}
        out[tk] = {"rows": len(df), "first": first, "last": last, "late_start_confirmed": confirmed}
    return out


def load_nasdaq_close(path: Path, tk: str) -> pd.Series:
    j = json.loads(path.read_text(encoding="utf-8"))
    if str(j["data"]["symbol"]).upper() != tk:
        raise RuntimeError(f"STOP: identity copy {path.name} is for {j['data']['symbol']}, not {tk}")
    rows = j["data"]["tradesTable"]["rows"]
    vals = {pd.Timestamp(datetime.strptime(r["date"], "%m/%d/%Y")): float(str(r["close"]).replace("$", "").replace(",", ""))
            for r in rows}
    return pd.Series(vals).sort_index()


def identity_check(root: Path, frames: dict[str, pd.DataFrame], pinned: dict[str, str] | None = None) -> dict[str, Any]:
    """Labels come from the call order (the response carries no ticker): over the last 60 overlapping
    sessions (Kiwoom provisional last row dropped; only sessions after a split row inside that span) the
    median of Kiwoom close / Nasdaq public close must be within 1 +- 1%, with at least 20 sessions."""
    pinned = IDENTITY_PINNED if pinned is None else pinned
    out = {}
    for tk in TICKERS:
        p = root / IDENTITY_DIR / f"{tk}.json"
        got = sha256_file(p)
        if got != pinned[tk]:
            raise RuntimeError(f"STOP: identity copy {tk}: sha256 {got} != pinned {pinned[tk]}")
        nq = load_nasdaq_close(p, tk)
        k = frames[tk].iloc[:-1]
        common = k.index.intersection(nq.index)[-IDENTITY_SESSIONS:]
        sp = [d for d in common if bool(k.loc[d, "split"])]
        if sp:
            common = common[common > max(sp)]
        ratio = k.loc[common, "close"].to_numpy(float) / nq.loc[common].to_numpy(float)
        med = float(np.median(ratio)) if len(ratio) else float("nan")
        passed = bool(len(ratio) >= IDENTITY_MIN and abs(med - 1.0) <= IDENTITY_TOL)
        out[tk] = {"passed": passed, "sessions": int(len(ratio)), "median_ratio": med, "copy_sha256": got,
                   "after_split": max(sp).date().isoformat() if sp else None,
                   "span": [common[0].date().isoformat(), common[-1].date().isoformat()] if len(common) else None}
        if not passed:
            raise RuntimeError(f"STOP: identity check failed for {tk}: " + json.dumps(clean(out[tk])))
    return out


def pit_level(series: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    """Value at each session = the last valid observation dated strictly before it (NaN if none)."""
    s = series.dropna()
    idx = s.index.values.astype("datetime64[ns]")
    pos = np.searchsorted(idx, dates.values.astype("datetime64[ns]"), side="left") - 1
    vals = s.to_numpy(float)
    return np.where(pos >= 0, vals[np.clip(pos, 0, None)], np.nan)


# ----------------------------------------------------------------------------
# windows and data audit
# ----------------------------------------------------------------------------
def verdict_start(common_first: pd.Timestamp) -> pd.Timestamp:
    """First 02-05 / 08-05 boundary b with b - 24 months >= the first common session."""
    y = common_first.year
    while True:
        for m in (2, 8):
            b = pd.Timestamp(year=y, month=m, day=5)
            if b - pd.DateOffset(months=TRAIN_MONTHS) >= common_first:
                return b
        y += 1


def audit_and_align(root: Path, frames: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    S4 = s4(root)
    lead = {}
    trimmed = {}
    for tk in TICKERS:                         # leading flat zero-volume placeholder rows (Kiwoom NBIS) are dropped
        df = frames[tk]
        flat = ((df["volume"].to_numpy(float) <= 0) & (df["open"] == df["close"]).to_numpy()
                & (df["high"] == df["close"]).to_numpy() & (df["low"] == df["close"]).to_numpy())
        k0 = int(np.argmin(flat)) if not flat.all() else len(df)
        lead[tk] = {"count": k0, "range": [df.index[0].date().isoformat(), df.index[k0 - 1].date().isoformat()] if k0 else None}
        trimmed[tk] = df.iloc[k0:]
    frames = trimmed
    common = None
    for tk in TICKERS:
        idx = frames[tk].index
        common = idx if common is None else common.intersection(idx)
    common = common[common >= pd.Timestamp(FIRST_ALLOWED)]
    if len(common) < 3:
        raise RuntimeError("STOP: no common history")
    provisional = common[-1]
    common = common[:-1]                       # the last Kiwoom row is provisional until a newer row exists
    first, last = common[0], common[-1]
    vs = verdict_start(first)
    crit_lo = vs - pd.DateOffset(months=TRAIN_MONTHS)
    crit_hi = min(pd.Timestamp(VERDICT_END), last)
    exp = S4.expected_sessions(first.date().isoformat(), last.date().isoformat())
    missing, extra = exp.difference(common), common.difference(exp)

    def crit(days) -> list[str]:
        return [d.date().isoformat() for d in days if crit_lo <= d <= crit_hi]

    aligned = {tk: frames[tk].loc[common] for tk in TICKERS}
    closes_ok, opens_bad, ohlc_odd = {}, {}, {}
    for tk, df in aligned.items():
        cl = df["close"].to_numpy(float)
        closes_ok[tk] = bool(np.isfinite(cl).all() and (cl > 0).all())        # STOP: the engine values at closes
        op, vol = df["open"].to_numpy(float), df["volume"].to_numpy(float)
        bad = ~(np.isfinite(op) & (op > 0) & np.isfinite(vol) & (vol > 0))     # recorded: the engine freezes fills
        opens_bad[tk] = {"count": int(bad.sum()), "in_critical": crit(df.index[bad])}
        odd = ~((df["low"] <= df[["open", "close"]].min(axis=1) + 1e-9) & (df["high"] >= df[["open", "close"]].max(axis=1) - 1e-9))
        ohlc_odd[tk] = {"count": int(odd.sum()), "dates_first_20": [d.date().isoformat() for d in df.index[odd.to_numpy()]][:20]}
    r = {tk: aligned[tk]["close"].pct_change() for tk in TICKERS}
    lev_gap = (r["SOXL"] - 3 * r["SOXX"]).abs()
    flags = {"SOXL_vs_3xSOXX": [d.date().isoformat() for d in lev_gap.index[lev_gap > DATA_ERROR_LEV]]}
    for tk in ("SOXX", "XLE", "XLV", "SPY"):
        big = r[tk].abs()
        flags[tk] = [d.date().isoformat() for d in big.index[big > DATA_ERROR_ONE]]
    flags_crit = {k: [d for d in v if crit_lo.date().isoformat() <= d <= crit_hi.date().isoformat()]
                  for k, v in flags.items()}
    audit = {
        "common_sessions": len(common), "first": first.date().isoformat(), "last": last.date().isoformat(),
        "provisional_row_dropped": provisional.date().isoformat(),
        "leading_zero_volume_rows_dropped": lead,
        "per_ticker_range": {tk: [frames[tk].index[0].date().isoformat(), frames[tk].index[-1].date().isoformat(),
                                  int(len(frames[tk]))] for tk in TICKERS},
        "verdict_start": vs.date().isoformat(), "critical": [crit_lo.date().isoformat(), crit_hi.date().isoformat()],
        "missing_vs_calendar": [d.date().isoformat() for d in missing],
        "extra_vs_calendar": [d.date().isoformat() for d in extra],
        "missing_in_critical": crit(missing), "extra_in_critical": crit(extra),
        "closes_finite_positive": closes_ok, "untradable_opens": opens_bad, "ohlc_order_odd_rows": ohlc_odd,
        "data_error_days": flags, "data_error_days_in_critical": flags_crit,
        "split_sessions": {tk: [d.date().isoformat() for d in frames[tk].index[frames[tk]["split"]]] for tk in TICKERS},
        "adjustment_codes": {tk: {code: {"count": int(n), "dates": [d.date().isoformat() for d in frames[tk].index[frames[tk]["adj_code"] == code]]}
                                  for code, n in frames[tk]["adj_code"].value_counts().items() if code}
                             for tk in TICKERS},
        "calendar_mismatch_allowed_in_critical": MAX_CAL_GAPS,
    }
    bad_crit = any(flags_crit.values())
    too_many = len(audit["missing_in_critical"]) > MAX_CAL_GAPS or len(audit["extra_in_critical"]) > MAX_CAL_GAPS
    if too_many or not all(closes_ok.values()) or bad_crit:
        raise RuntimeError("STOP (fail closed): data audit failed: " + json.dumps(clean(
            {k: audit[k] for k in ("missing_in_critical", "extra_in_critical", "closes_finite_positive",
                                   "data_error_days_in_critical")})))
    return aligned, audit


# ----------------------------------------------------------------------------
# the new part: multi-asset constant-mix engine
# ----------------------------------------------------------------------------
def decide_schedule(dates: pd.DatetimeIndex, start: int, freq: str = "Q") -> np.ndarray:
    """True at the close of `start` (initial allocation) and at the last session before each new
    calendar quarter (freq 'Q') or month (freq 'M'); the fill is the next session's open."""
    n = len(dates)
    dec = np.zeros(n, dtype=bool)
    if start < n:
        dec[start] = True
    per = dates.to_period(freq)
    for t in range(start, n - 1):
        if per[t + 1] != per[t]:
            dec[t] = True
    return dec


def simulate_mix(O: np.ndarray, C: np.ndarray, ok: np.ndarray, days: np.ndarray, rate: np.ndarray,
                 target: np.ndarray, decide: np.ndarray, cost_bps: float, mode: str = "full",
                 sleeve_ratio: np.ndarray | None = None, core_mask: np.ndarray | None = None,
                 start: int = 0, end: int | None = None, target_at=None) -> dict[str, Any]:
    """O, C, ok: (n, k).  target: (k,) weights, the rest is cash.  Starts all cash at `start`.
    mode 'full': every asset to its target weight.  mode 'trim' (report only): after the initial
    allocation, a core asset (`core_mask`) above its target is sold down to it, nothing is bought for
    a core asset below its target, the sleeve is not rebalanced, and the proceeds go to the sleeve
    assets in `sleeve_ratio` (cash if the ratio is all zero).
    Each session: overnight move to the open, fill a pending rebalance at the open if every open is
    valid (else it stays pending), intraday move to the close, then the close decides.  An asset
    with an invalid open moves close to close.  Costs come out of cash.  `target_at(t)` (self-test only)
    replaces the constant target for a decision taken at close t."""
    n, k = C.shape
    end = n - 1 if end is None else end
    c = cost_bps / 10_000.0
    H = np.zeros(k)
    cash = 1.0
    pending = False
    tgt = target
    first_fill_done = False
    V = np.full(n, np.nan)
    W = np.full(n, np.nan)
    WI = np.full((n, k), np.nan)
    trades: list[dict[str, Any]] = []
    stale: list[int] = []
    for t in range(start, end + 1):
        all_ok = bool(ok[t].all())
        if t > start:
            for i in range(k):
                if ok[t, i]:
                    H[i] *= O[t, i] / C[t - 1, i]
            cash *= 1.0 + rate[t] * days[t] / 365.0
        if pending:
            if all_ok:
                v_open = float(H.sum() + cash)
                if mode == "full" or not first_fill_done:
                    delta = tgt * v_open - H
                else:
                    mask = np.ones(k, dtype=bool) if core_mask is None else core_mask
                    sell = np.where(mask, np.maximum(H - tgt * v_open, 0.0), 0.0)
                    proceeds = float(sell.sum())
                    delta = -sell
                    if sleeve_ratio is not None and sleeve_ratio.sum() > 0:
                        delta = delta + proceeds * sleeve_ratio / sleeve_ratio.sum()
                notional = float(np.abs(delta).sum())
                if notional > 1e-15:
                    cost = c * notional
                    H = H + delta
                    cash -= float(delta.sum()) + cost
                    trades.append({"idx": t, "notional": notional, "cost": cost,
                                   "deltas": [float(x) for x in delta]})
                pending = False
                first_fill_done = True
            else:
                stale.append(t)
        for i in range(k):
            if ok[t, i]:
                H[i] *= C[t, i] / O[t, i]
            elif t > start:
                H[i] *= C[t, i] / C[t - 1, i]
        v = float(H.sum() + cash)
        V[t] = v
        W[t] = float(H.sum()) / v
        WI[t] = H / v
        if decide[t]:
            pending = True
            tgt = target if target_at is None else target_at(t)
    return {"V": V, "W": W, "WI": WI, "trades": trades, "stale": stale}


def policy_exposure(WI: np.ndarray, C: np.ndarray, mult: np.ndarray, soxx_col: int, lo: int, hi: int,
                    window: int = 252) -> dict[str, Any]:
    """Report only: E = max(N, V) as in alert_policy.json 697~712 (N = sum w x multiplier, V = 252-session
    daily volatility of the current-weight portfolio / SOXX volatility), at each close in [lo, hi]."""
    R = C[1:] / C[:-1] - 1.0
    N, Vr, E = [], [], []
    for t in range(lo, hi + 1):
        if t < window or not np.isfinite(WI[t]).all():
            continue
        w = WI[t]
        rr = R[t - window:t]                      # returns ending at close t
        port = rr @ w
        sx = rr[:, soxx_col]
        v = float(np.std(port, ddof=1) / np.std(sx, ddof=1))
        nn = float(w @ mult)
        N.append(nn); Vr.append(v); E.append(max(nn, v))
    if not E:
        return {"sessions": 0}
    return {"sessions": len(E), "mean_E": float(np.mean(E)), "min_E": float(np.min(E)), "max_E": float(np.max(E)),
            "mean_N": float(np.mean(N)), "min_N": float(np.min(N)), "max_N": float(np.max(N)),
            "mean_V": float(np.mean(Vr)), "min_V": float(np.min(Vr)), "max_V": float(np.max(Vr)),
            "share_V_dominant": float(np.mean(np.array(Vr) > np.array(N)))}


# ----------------------------------------------------------------------------
# report-only views
# ----------------------------------------------------------------------------
def soxx_episodes(close: np.ndarray, lo: int, hi: int, dd: float = EPISODE_DD) -> list[dict[str, Any]]:
    """Drawdown episodes of a close series from its running peak (from index 0): an episode runs from a
    peak close to the lowest close before the series first closes at or above that peak again (or the
    data end, 'open').  Kept when trough / peak - 1 <= -dd and the trough index is in [lo, hi]."""
    out: list[dict[str, Any]] = []
    peak_i, trough_i = 0, 0
    for t in range(1, len(close)):
        if close[t] >= close[peak_i]:
            if close[trough_i] / close[peak_i] - 1 <= -dd and lo <= trough_i <= hi:
                out.append({"peak": peak_i, "trough": trough_i, "recovered": t, "open": False})
            peak_i, trough_i = t, t
        elif close[t] < close[trough_i]:
            trough_i = t
    if close[trough_i] / close[peak_i] - 1 <= -dd and lo <= trough_i <= hi:
        out.append({"peak": peak_i, "trough": trough_i, "recovered": None, "open": True})
    return out


def drawdown_report(V: np.ndarray, dates: pd.DatetimeIndex, lo: int, hi: int) -> dict[str, Any]:
    """Deepest drawdown inside [lo, hi] measured from the value at lo - 1 (as slice_metrics)."""
    peak_v, peak_i = float(V[lo - 1]), lo - 1
    best = (0.0, lo - 1, lo - 1)
    for t in range(lo, hi + 1):
        if V[t] >= peak_v:
            peak_v, peak_i = float(V[t]), t
        dd = float(V[t] / peak_v - 1)
        if dd < best[0]:
            best = (dd, peak_i, t)
    dd, p, q = best
    rec = next((t for t in range(q, hi + 1) if V[t] >= V[p]), None) if dd < 0 else None
    return {"max_drawdown": dd, "peak": dates[p].date().isoformat(), "trough": dates[q].date().isoformat(),
            "recovered_by": dates[rec].date().isoformat() if rec is not None else None}


# ----------------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------------
def window_metrics(root: Path, run: dict[str, Any], dates: pd.DatetimeIndex, a: int, z: int, name: str) -> dict[str, Any]:
    m = s4(root).slice_metrics(run, dates, a, z, name)
    m.pop("average_factor_exposure", None)      # 08-05 field = 3 x invested weight (SOXL only); see policy E
    return m


def fold_table(root: Path, runs: dict[str, dict], dates: pd.DatetimeIndex, soxx: pd.DataFrame,
               start: pd.Timestamp, end: pd.Timestamp) -> tuple[list[dict], dict[str, list[dict]]]:
    S4 = s4(root)
    folds = S4.make_folds(start.date().isoformat(), end.date().isoformat())
    regimes, per = [], {name: [] for name in runs}
    for f in folds:
        a, z = S4.positions(dates, f["test_start"], f["test_end"])
        regimes.append(wf(root).regime_label(soxx, f) | {"test_start": f["test_start"].date().isoformat(),
                                                          "test_end": f["test_end"].date().isoformat()})
        for name, run in runs.items():
            per[name].append(window_metrics(root, run, dates, a, z, name))
    return regimes, per


def judge(root: Path, m: dict[float, dict[str, dict]], folds: dict[str, list[dict]], regimes: list[dict],
          n_folds: int) -> dict[str, Any]:
    S4 = s4(root)
    g = {}
    base10 = S4.g1_g2(m[10.0][JUDGED], m[10.0][BASE])
    g["G1"] = base10["G1"]
    g["G2"] = base10["G2"]
    g["G1_G2_detail_10bp"] = base10
    gf = S4.gate_folds(folds[JUDGED], folds[BASE], regimes)
    g["G3"] = gf["G3"]
    g["G5"] = gf["G5"]
    g["G3_G5_detail"] = gf
    g20 = S4.g1_g2(m[20.0][JUDGED], m[20.0][BASE])
    c50, b50 = m[JUDGE_COST][JUDGED], m[JUDGE_COST][BASE]
    g4b = bool(c50["maximum_drawdown"] > b50["maximum_drawdown"] + 1e-12 and c50["calmar"] is not None
               and b50["calmar"] is not None and c50["calmar"] > b50["calmar"] + 1e-12)
    nb = {name: S4.g1_g2(m[10.0][name], m[10.0][BASE]) for name in NEIGHBORS}
    passing = sum(1 for v in nb.values() if v["G1"] and v["G2"])
    g4c = bool(passing > len(nb) / 2)
    g["G4"] = bool(g20["G1"] and g20["G2"] and g4b and g4c)
    g["G4_detail"] = {"a_20bp": g20, "b_50bp_mdd_and_calmar_better": g4b, "c_neighbors": nb,
                      "c_neighbors_passing": passing}
    g["G6"] = bool(n_folds >= MIN_FOLDS)
    g["G6_detail"] = {"folds": n_folds, "required": MIN_FOLDS}
    b50g = S4.g1_g2(m[JUDGE_COST][JUDGED], m[JUDGE_COST][BASE])
    g["G7"] = bool(b50g["G1"] and b50g["G2"])
    g["G7_detail"] = {"vs_B_50bp": b50g}
    c10 = S4.g1_g2(m[10.0][JUDGED], m[10.0][CTRL])
    c50g = S4.g1_g2(m[JUDGE_COST][JUDGED], m[JUDGE_COST][CTRL])
    cf = S4.gate_folds(folds[JUDGED], folds[CTRL], regimes)
    g["G8"] = bool(c10["G1"] and c10["G2"] and c50g["G1"] and c50g["G2"] and cf["G5"])
    g["G8_detail"] = {"vs_C_10bp": c10, "vs_C_50bp": c50g, "vs_C_fold_concentration_G5": cf["G5"],
                      "vs_C_folds_report_only": cf}
    g["verdict"] = verdict_of(g)
    g["failed"] = [k for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8") if not g[k]]
    return g


def verdict_of(g: dict[str, Any]) -> str:
    core = all(g[k] for k in ("G1", "G2", "G3", "G4", "G5", "G7"))
    if core and g["G6"] and g["G8"]:
        return "후보"
    if core and not g["G8"]:
        return "검토 전용(대안)"          # whatever G6 says (crash1031 '검토 전용(노출)')
    if core and g["G8"] and not g["G6"]:
        return "검토 전용(표본)"
    return "기준 미달"


# ----------------------------------------------------------------------------
# run
# ----------------------------------------------------------------------------
def build_market(aligned: dict[str, pd.DataFrame]):
    dates = aligned["SOXX"].index
    O = np.column_stack([aligned[tk]["open"].to_numpy(float) for tk in TICKERS])
    C = np.column_stack([aligned[tk]["close"].to_numpy(float) for tk in TICKERS])
    vol = np.column_stack([aligned[tk]["volume"].to_numpy(float) for tk in TICKERS])
    ok = np.isfinite(O) & (O > 0) & np.isfinite(vol) & (vol > 0)
    days = np.zeros(len(dates))
    days[1:] = np.diff(dates.values).astype("timedelta64[D]").astype(float)
    return dates, O, C, ok, days


def target_vec(weights: dict[str, float]) -> np.ndarray:
    return np.array([weights.get(tk, 0.0) for tk in TICKERS], dtype=float)


def sleeve_vec(sleeve: dict[str, float]) -> np.ndarray:
    return np.array([sleeve.get(tk, 0.0) for tk in TICKERS], dtype=float)


def run_arms(arms: dict[str, dict[str, float]], O, C, ok, days, rate, decide, cost: float, mode: str = "full"):
    core_mask = np.array([tk in CORE for tk in TICKERS])
    return {name: simulate_mix(O, C, ok, days, rate, target_vec(arm_weights(sl)), decide, cost, mode,
                               sleeve_vec(sl), core_mask) for name, sl in arms.items()}


def _trades_upto(run: dict[str, Any], last: int) -> list[tuple]:
    return [(tr["idx"], round(tr["notional"], 12), tuple(round(x, 12) for x in tr["deltas"]))
            for tr in run["trades"] if tr["idx"] <= last]


def causality_check(O, C, ok, days, rate, dates, cuts: list[int], arms: dict[str, dict[str, float]] | None = None,
                    engine=None) -> dict[str, Any]:
    """For each cut, re-run every arm on the data up to that close plus the next session's open only
    (its close unknown, the schedule rebuilt from the truncated calendar).  Values and weights up to the
    cut and every fill up to and including the next open must equal the full run."""
    arms = ARMS if arms is None else arms
    engine = simulate_mix if engine is None else engine
    n = len(dates)
    full_dec = decide_schedule(dates, 0)
    fails = []
    for name, sl in arms.items():
        tv = target_vec(arm_weights(sl))
        full = engine(O, C, ok, days, rate, tv, full_dec, 10.0)
        for cut in cuts:
            m = min(cut + 2, n)
            Ct = C[:m].copy()
            if m > cut + 1:
                Ct[cut + 1] = np.nan                     # the next close is not known at the cut
            dec = decide_schedule(dates[:m], 0)
            if m > cut + 1:
                dec[cut + 1] = False                     # nothing after the next open is compared
            part = engine(O[:m], Ct, ok[:m], days[:m], rate[:m], tv, dec, 10.0)
            same = (np.allclose(part["V"][:cut + 1], full["V"][:cut + 1], rtol=0, atol=1e-12, equal_nan=True)
                    and np.allclose(part["WI"][:cut + 1], full["WI"][:cut + 1], rtol=0, atol=1e-12, equal_nan=True)
                    and _trades_upto(part, m - 1) == _trades_upto(full, m - 1))
            if not same:
                fails.append({"arm": name, "cut": dates[cut].date().isoformat()})
    return {"cuts": [dates[c].date().isoformat() for c in cuts],
            "decision_day_cuts": int(sum(bool(full_dec[c]) for c in cuts)), "fails": fails, "passed": not fails}


def run_all(root: Path, out_path: Path) -> int:
    if out_path.exists():
        raise RuntimeError(f"STOP: {out_path} exists; this contract runs once and never overwrites")
    contract = check_contract(root)
    check_code(root)
    manifest = check_manifest(root, contract["fixed_at"])
    for sid, want in FRED_PINNED.items():
        if sha256_file(root / FRED_DIR / f"{sid}.csv") != want:
            raise RuntimeError(f"STOP: {sid} differs from the a-3 pin")
    frames = {tk: load_kiwoom(root / manifest["files"][tk]["path"]) for tk in TICKERS}
    inputs = check_inputs(root, manifest, frames)
    identity = identity_check(root, frames)
    aligned, audit = audit_and_align(root, frames)
    dates, O, C, ok, days = build_market(aligned)
    S4 = s4(root)
    dgs3 = load_fred(root / FRED_DIR / "DGS3MO.csv", "DGS3MO")
    dgs10 = load_fred(root / FRED_DIR / "DGS10.csv", "DGS10")
    rate0 = np.zeros(len(dates))                          # report only
    rate3 = S4.rate_array(dates, dgs3.dropna())           # judged cash yield (S4, a-3, crash1031)
    vs = pd.Timestamp(audit["verdict_start"])
    ve = pd.Timestamp(VERDICT_END)
    if dates[-1] < ve:
        raise RuntimeError(f"STOP: common history ends {dates[-1].date()} before {VERDICT_END}")
    a, z = S4.positions(dates, vs, ve)
    soxx_df = pd.DataFrame({"close": aligned["SOXX"]["close"]})
    decQ = decide_schedule(dates, 0, "Q")
    decM = decide_schedule(dates, 0, "M")

    runs = {cost: run_arms(ARMS, O, C, ok, days, rate3, decQ, cost) for cost in COSTS}
    metrics = {cost: {name: window_metrics(root, run, dates, a, z, name) for name, run in rs.items()}
               for cost, rs in runs.items()}
    regimes, folds = fold_table(root, runs[10.0], dates, soxx_df, vs, ve)
    n_folds = len(regimes)
    gates = judge(root, metrics, folds, regimes, n_folds)

    # report only ---------------------------------------------------------------
    rep: dict[str, Any] = {}
    rep_runs = {
        "cash_0pct_10bp": run_arms({**ARMS}, O, C, ok, days, rate0, decQ, 10.0),
        "monthly_10bp": run_arms({**ARMS}, O, C, ok, days, rate3, decM, 10.0),
        "trim_only_10bp": run_arms({**ARMS}, O, C, ok, days, rate3, decQ, 10.0, mode="trim"),
        "half_sleeve_10bp": run_arms({**REPORT_ARMS, BASE: ARMS[BASE]}, O, C, ok, days, rate3, decQ, 10.0),
    }
    for key, rs in rep_runs.items():
        mm = {name: window_metrics(root, run, dates, a, z, name) for name, run in rs.items()}
        ref = BASE
        rep[key] = {"metrics": mm,
                    "g1_g2_vs_B": {name: S4.g1_g2(mm[name], mm[ref]) for name in mm if name != ref}}
    sub = {}
    for label, (s0, s1) in {"primary_2021_2026": PRIMARY_SUB,
                            "before_primary": (audit["verdict_start"], "2021-08-04")}.items():
        aa, zz = S4.positions(dates, pd.Timestamp(s0), pd.Timestamp(s1))
        mm = {name: window_metrics(root, run, dates, aa, zz, name) for name, run in runs[10.0].items()}
        sub[label] = {"window": [s0, s1], "metrics": mm,
                      "g1_g2_R_vs_B": S4.g1_g2(mm[JUDGED], mm[BASE]), "g1_g2_R_vs_C": S4.g1_g2(mm[JUDGED], mm[CTRL])}
    rep["sub_windows_10bp"] = sub
    t_lo = int(dates.searchsorted(ve, side="right"))
    if t_lo <= len(dates) - 1:
        rep["tail_10bp"] = {"window": [dates[t_lo].date().isoformat(), dates[-1].date().isoformat()],
                            "total_return": {name: float(run["V"][-1] / run["V"][t_lo - 1] - 1)
                                             for name, run in runs[10.0].items()}}
    rep["drawdowns_10bp"] = {name: drawdown_report(run["V"], dates, a, z) for name, run in runs[10.0].items()}
    mult = np.array([MULT[tk] for tk in TICKERS])
    rep["policy_exposure_E"] = {name: policy_exposure(run["WI"], C, mult, TICKERS.index("SOXX"), a, z)
                                for name, run in runs[10.0].items()}
    lvl10 = pit_level(dgs10, dates)
    eps = []
    closeX = aligned["SOXX"]["close"].to_numpy(float)
    for e in soxx_episodes(closeX, a, len(dates) - 1):
        p, q = e["peak"], e["trough"]
        d10 = float(lvl10[q] - lvl10[p]) if np.isfinite(lvl10[p]) and np.isfinite(lvl10[q]) else None
        row = {"peak": dates[p].date().isoformat(), "trough": dates[q].date().isoformat(),
               "recovered": dates[e["recovered"]].date().isoformat() if e["recovered"] is not None else None,
               "soxx": float(closeX[q] / closeX[p] - 1), "dgs10_change_pp": d10,
               "type": None if d10 is None else ("rate" if d10 >= RATE_RISE_PP - 1e-12 else "other"),
               "assets": {tk: float(aligned[tk]["close"].iloc[q] / aligned[tk]["close"].iloc[p] - 1) for tk in TICKERS},
               "arms_10bp": {name: float(run["V"][q] / run["V"][p] - 1) for name, run in runs[10.0].items()}}
        row["R_minus_B"] = row["arms_10bp"][JUDGED] - row["arms_10bp"][BASE]
        row["C_minus_B"] = row["arms_10bp"][CTRL] - row["arms_10bp"][BASE]
        eps.append(row)
    rep["soxx_episodes"] = {"threshold": EPISODE_DD, "rate_rise_pp": RATE_RISE_PP, "rows": eps}
    rep["fills_and_freezes_10bp"] = {name: {"fills": len(run["trades"]), "frozen_sessions": len(run["stale"])}
                                     for name, run in runs[10.0].items()}

    # implementation checks on the real data ---------------------------------------
    dec_days = [int(i) for i in np.flatnonzero(decQ) if a <= i <= z]
    other = [i for i in range(a, z + 1) if not decQ[i]]
    pick = lambda xs, k: [xs[int(j)] for j in np.linspace(0, len(xs) - 1, k)] if len(xs) >= k else list(xs)
    cuts = sorted(set(pick(dec_days, MIN_CAUSALITY_CUTS) + pick(other, 4) + [len(dates) - 2]))
    caus = causality_check(O, C, ok, days, rate3, dates, cuts)
    if not caus["passed"]:
        raise RuntimeError("STOP: causality check failed " + json.dumps(caus["fails"][:5]))

    result = {
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "contract": {"path": PREREG, **contract},
        "pinned_code": CODE_PINNED, "pinned_fred": FRED_PINNED,
        "inputs_manifest": {"path": INPUTS_MANIFEST, "sha256": sha256_file(root / INPUTS_MANIFEST),
                            "files": manifest["files"]},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "inputs_check": inputs, "identity_check": identity,
        "identity_copies": {"dir": IDENTITY_DIR, "sha256": IDENTITY_PINNED},
        "data_audit": audit | {"all_opens_tradable": bool(ok.all())},
        "design": {"tickers": TICKERS, "core": CORE, "sleeve": SLEEVE, "arms": ARMS, "judged": JUDGED,
                   "champion": BASE, "control": CTRL, "neighbors": NEIGHBORS, "rebalance": "quarterly first session",
                   "income": "price returns, cash DGS3MO (judged); cash 0% report only", "costs_bps": COSTS},
        "verdict_window": [dates[a].date().isoformat(), dates[z].date().isoformat()], "folds": n_folds,
        "regimes": regimes,
        "metrics": metrics, "fold_metrics_10bp": folds,
        "gates": gates, "verdict": gates["verdict"],
        "report_only": rep, "causality": caus,
    }
    text = json.dumps(clean(result), ensure_ascii=False, indent=2)
    with open(out_path, "x", encoding="utf-8") as fh:            # "x": never overwrite
        fh.write(text + "\n")
    print(f"verdict: {gates['verdict']}  ->  {out_path}")
    return 0


# ----------------------------------------------------------------------------
# self-test (synthetic and hand-built; no contract, no market data)
# ----------------------------------------------------------------------------
def synthetic_market(n: int = 900, seed: int = 5):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-02", periods=n)
    k = len(TICKERS)
    r = rng.normal(0.0004, 0.015, size=(n, k))
    r[:, 1] = 3 * r[:, 0] + rng.normal(0, 0.002, n)          # SOXL ~ 3x SOXX
    C = 100 * np.cumprod(1 + r, axis=0)
    O = C * (1 + rng.normal(0, 0.003, size=(n, k)))
    O[0] = C[0]
    ok = np.ones((n, k), dtype=bool)
    days = np.zeros(n)
    days[1:] = np.diff(dates.values).astype("timedelta64[D]").astype(float)
    return dates, O, C, ok, days


def self_test(root: Path) -> None:
    S4 = s4(root)
    # 1 hand-built: two assets, three sessions, 10bp
    O = np.array([[10.0, 20.0], [11.0, 20.0], [12.0, 18.0]])
    C = np.array([[10.0, 20.0], [11.5, 19.0], [12.6, 18.9]])
    ok = np.ones((3, 2), dtype=bool)
    days = np.array([0.0, 1.0, 1.0])
    tv = np.array([0.5, 0.3])
    dec = np.array([True, False, False])
    run = simulate_mix(O, C, ok, days, np.zeros(3), tv, dec, 10.0)
    # session 1 open: v = 1, buy 0.5 / 0.3, cost 0.0008 -> cash 0.2 - 0.0008
    h0 = 0.5 * 11.5 / 11.0
    h1 = 0.3 * 19.0 / 20.0
    v1 = h0 + h1 + 0.2 - 0.0008
    assert abs(run["V"][1] - v1) < 1e-12, (run["V"][1], v1)
    v2 = h0 * 12.6 / 11.5 + h1 * 18.9 / 19.0 + 0.2 - 0.0008
    assert abs(run["V"][2] - v2) < 1e-12
    assert len(run["trades"]) == 1 and abs(run["trades"][0]["cost"] - 0.0008) < 1e-15
    assert abs(run["V"][0] - 1.0) < 1e-15
    # 2 quarter schedule: decide on the last session of March, fill on the first session of April
    d = pd.bdate_range("2020-03-25", "2020-04-10")
    dq = decide_schedule(d, 0, "Q")
    assert dq[0] and dq[list(d).index(pd.Timestamp("2020-03-31"))] and dq.sum() == 2
    dm = decide_schedule(pd.bdate_range("2020-01-27", "2020-03-06"), 0, "M")
    assert dm.sum() == 3                        # start, last Jan session, last Feb session
    # 3 frozen fill: an invalid open on the fill session postpones the fill by one session
    dates, O, C, ok, days = synthetic_market(80)
    dec = decide_schedule(dates, 0, "Q")
    ok2 = ok.copy()
    ok2[1, 2] = False
    r_ok = simulate_mix(O, C, ok, days, np.zeros(len(dates)), target_vec(arm_weights(ARMS["R_eh50"])), dec, 10.0)
    r_fz = simulate_mix(O, C, ok2, days, np.zeros(len(dates)), target_vec(arm_weights(ARMS["R_eh50"])), dec, 10.0)
    assert r_ok["trades"][0]["idx"] == 1 and r_fz["trades"][0]["idx"] == 2 and r_fz["stale"] == [1]
    # 4 causality: data to each close + the next open only reproduce the full run up to that open's fill
    dates, O, C, ok, days = synthetic_market(700)
    rate = np.full(len(dates), 0.02)
    full_dec = decide_schedule(dates, 0)
    dd_ = [int(i) for i in np.flatnonzero(full_dec) if 5 <= i <= 698]
    rnd = np.random.default_rng(3)
    cuts = sorted(set(dd_[::2] + [int(x) for x in rnd.integers(5, 690, size=6)] + [698]))
    caus = causality_check(O, C, ok, days, rate, dates, cuts)
    assert caus["passed"] and caus["decision_day_cuts"] >= 4, caus
    # 4b a per-step look-ahead (the decision at close t reads close t+1) is caught; the honest twin is not
    def leaky_engine(peek: bool):
        def eng(O_, C_, ok_, days_, rate_, target, decide, cost_bps):
            def tgt_at(t):
                nxt = C_[t + 1, 0] if t + 1 < len(C_) else np.nan
                return target * 0.5 if (peek and np.isfinite(nxt) and nxt < C_[t, 0]) else target
            return simulate_mix(O_, C_, ok_, days_, rate_, target, decide, cost_bps, target_at=tgt_at)
        return eng
    one = {"R_eh50": ARMS["R_eh50"]}
    assert causality_check(O, C, ok, days, rate, dates, cuts, one, leaky_engine(False))["passed"]
    assert not causality_check(O, C, ok, days, rate, dates, cuts, one, leaky_engine(True))["passed"]
    honest = simulate_mix(O, C, ok, days, rate, target_vec(arm_weights(ARMS["R_eh50"])), full_dec, 10.0)
    twin = leaky_engine(False)(O, C, ok, days, rate, target_vec(arm_weights(ARMS["R_eh50"])), full_dec, 10.0)
    assert np.allclose(honest["V"], twin["V"], rtol=0, atol=1e-13)      # the hook itself changes nothing
    # 5 trim mode: above target is sold into the sleeve, below target is not bought
    O = np.array([[10.0, 10.0, 10.0], [10.0, 10.0, 10.0], [20.0, 10.0, 10.0], [20.0, 10.0, 10.0], [5.0, 5.0, 10.0], [5.0, 5.0, 10.0]])
    C = O.copy()
    ok = np.ones_like(O, dtype=bool)
    days = np.ones(6)
    dec = np.array([True, False, True, False, True, False])
    tv = np.array([0.5, 0.2, 0.3])
    sr = np.array([0.0, 0.0, 1.0])
    tr = simulate_mix(O, C, ok, days, np.zeros(6), tv, dec, 0.0, mode="trim", sleeve_ratio=sr,
                      core_mask=np.array([True, True, False]))
    # after asset 0 doubles: values 1.0/0.2/0.3 (v 1.5) -> sell 1.0 - 0.75 = 0.25 into asset 2
    assert abs(tr["WI"][3, 0] - 0.5) < 1e-12 and abs(tr["WI"][3, 2] - (0.55 / 1.5)) < 1e-12
    # after assets 0 and 1 fall: no buy-back of either, and the over-target sleeve is not sold
    assert len(tr["trades"]) == 2 and abs(tr["WI"][5, 2] - 0.55 / (0.1875 + 0.1 + 0.55)) < 1e-12
    # 6 exposure E equals a direct computation
    dates, O, C, ok, days = synthetic_market(400)
    run = simulate_mix(O, C, ok, days, np.zeros(400), target_vec(arm_weights(ARMS["R_eh50"])),
                       decide_schedule(dates, 0), 10.0)
    mult = np.array([MULT[tk] for tk in TICKERS])
    pe = policy_exposure(run["WI"], C, mult, 0, 399, 399)
    w = run["WI"][399]
    rr = C[1:] / C[:-1] - 1
    vdir = np.std(rr[399 - 252:399] @ w, ddof=1) / np.std(rr[399 - 252:399, 0], ddof=1)
    assert pe["sessions"] == 1 and abs(pe["mean_E"] - max(float(w @ mult), vdir)) < 1e-12
    # 7 episodes: a -30% episode (recovered), a -15% dip (ignored) and an open -22% episode
    x = np.concatenate([np.linspace(100, 70, 11), np.linspace(70, 101, 11), np.linspace(101, 86, 6),
                        np.linspace(86, 110, 9), np.linspace(110, 85.8, 8)])
    eps = soxx_episodes(x, 0, len(x) - 1)
    assert len(eps) == 2 and abs(x[eps[0]["trough"]] - 70) < 1e-9 and not eps[0]["open"] and eps[1]["open"]
    assert soxx_episodes(x, 30, len(x) - 1)[0]["open"]          # first trough is outside [30, end]
    # 7b rate label uses only observations dated before the session
    dd = pd.bdate_range("2022-01-03", periods=5)
    ser = pd.Series([1.0, 1.5, 2.0, 2.5, 3.0], index=dd)
    lv = pit_level(ser, dd)
    assert np.isnan(lv[0]) and lv[1] == 1.0 and lv[4] == 2.5
    # 8 verdict start rule, the pinned gate functions on hand-made metrics, and the verdict mapping
    assert verdict_start(pd.Timestamp("2010-10-18")) == pd.Timestamp("2013-02-05")
    assert verdict_start(pd.Timestamp("2011-02-05")) == pd.Timestamp("2013-02-05")
    assert verdict_start(pd.Timestamp("2011-02-07")) == pd.Timestamp("2013-08-05")
    good = {"maximum_drawdown": -0.20, "maximum_recovery_sessions": 80, "cagr": 0.10, "calmar": 0.5}
    base = {"maximum_drawdown": -0.30, "maximum_recovery_sessions": 100, "cagr": 0.10, "calmar": 0.333}
    gg = S4.g1_g2(good, base)
    assert gg["G1"] and gg["G2"]
    assert not S4.g1_g2(base, good)["G1"]
    allg = {k: True for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")}
    assert verdict_of(allg) == "후보"
    assert verdict_of(allg | {"G8": False}) == "검토 전용(대안)"
    assert verdict_of(allg | {"G8": False, "G6": False}) == "검토 전용(대안)"
    assert verdict_of(allg | {"G6": False}) == "검토 전용(표본)"
    assert verdict_of(allg | {"G7": False}) == "기준 미달"
    assert verdict_of(allg | {"G3": False, "G8": False}) == "기준 미달"
    # 9 contract, sidecar amendments and manifest refuse changed or early files; results are never overwritten
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        (troot / "docs/claude/strategy1101-root-inputs").mkdir(parents=True)
        doc = troot / PREREG
        doc.write_bytes(b"contract\n")
        me = sha256_file(Path(__file__).resolve())
        good_doc = hashlib.sha256(b"contract\n").hexdigest()

        def side_refused(text: str) -> bool:
            (troot / PREREG_SIDECAR).write_text(text, encoding="utf-8")
            try:
                check_contract(troot)
                return False
            except RuntimeError:
                return True
        head = f"raw_sha256 {good_doc}\nrunner_sha256 {me}\n"
        assert side_refused(f"raw_sha256 {hashlib.sha256(b'other').hexdigest()}\nrunner_sha256 {me}\n"
                            "fixed_at 2026-11-01T23:00:00+09:00\n"), "changed contract not refused"
        assert side_refused(head + "fixed_at 2026-11-01T23:00:00\n"), "fixed_at without offset not refused"
        assert side_refused(head + "fixed_at 2026-11-01T23:00:00+09:00\nfixed_at 2026-11-02T23:00:00+09:00\n")
        assert side_refused(head + "fixed_at 2026-11-01T23:00:00+09:00\namended_at 2026-11-01T22:00:00+09:00\n")
        assert not side_refused(head + "fixed_at 2026-11-01T23:00:00+09:00 (note)\namended_at 2026-11-02T09:00:00+09:00 (stop fix)\n")
        cc = check_contract(troot)
        assert cc["fixed_at"] == "2026-11-01T23:00:00+09:00" and cc["amended_at"] == ["2026-11-02T09:00:00+09:00"]
        files = {}
        for tk in TICKERS:
            p_ = troot / "docs/claude/strategy1101-root-inputs" / f"{tk}.json"
            p_.write_text(tk, encoding="utf-8")
            files[tk] = {"path": str(p_.relative_to(troot)), "sha256": sha256_file(p_), "called_kst": "2026-11-02T07:00:00+09:00",
                         "rows": 1, "first": "2010-10-18", "last": "2010-10-18"}
        def refused(files_, fixed="2026-11-01T23:00:00+09:00") -> bool:
            (troot / INPUTS_MANIFEST).write_text(json.dumps({"files": files_}), encoding="utf-8")
            try:
                check_manifest(troot, fixed)
                return False
            except RuntimeError:
                return True
        cp = lambda x: json.loads(json.dumps(x))
        assert not refused(files)
        early = cp(files); early["SPY"]["called_kst"] = "2026-11-01T22:00:00+09:00"
        assert refused(early), "data fetched before fixation not refused"
        naive = cp(files); naive["XLE"]["called_kst"] = "2026-11-02T07:00:00"
        assert refused(naive), "a fetch time without offset not refused"
        assert refused(files, "2026-11-01T23:00:00"), "a fixed_at without offset not refused"
        norow = cp(files); del norow["SOXL"]["rows"]
        assert refused(norow), "an entry without rows not refused"
        (troot / files["XLV"]["path"]).write_text("XLV changed", encoding="utf-8")
        assert refused(files), "a data file changed after the manifest not refused"
        (troot / files["XLV"]["path"]).write_text("XLV", encoding="utf-8")
        conf = cp(files)
        cpath = troot / "docs/claude/strategy1101-root-inputs" / "XLE_confirm.json"
        cpath.write_text("XLE again", encoding="utf-8")
        conf["XLE"]["confirm"] = {"path": str(cpath.relative_to(troot)), "sha256": sha256_file(cpath),
                                  "called_kst": "2026-11-01T22:30:00+09:00"}
        assert refused(conf), "a confirming fetch before the lock not refused"
        conf["XLE"]["confirm"]["called_kst"] = "2026-11-02T07:05:00+09:00"
        assert not refused(conf)
        out = troot / "exists.json"
        out.write_text("{}", encoding="utf-8")
        try:
            run_all(troot, out)
            raise AssertionError("existing results not refused")
        except RuntimeError as exc:
            assert "exists" in str(exc)
    # 10 data audit: pre-committed stop / record rules
    idx = S4.expected_sessions("2010-10-18", "2014-03-31")
    rng = np.random.default_rng(1)
    base_px = 50 * np.cumprod(1 + rng.normal(0, 0.01, len(idx)))
    def frame(px, mult=1.0):
        c = px if mult == 1.0 else 50 * np.cumprod(1 + mult * np.r_[0, np.diff(px) / px[:-1]])
        return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6,
                             "adj_code": "", "split": False}, index=idx)
    fr = {"SOXX": frame(base_px), "SOXL": frame(base_px, 3.0), "XLE": frame(base_px * 0.9 + 5),
          "XLV": frame(base_px * 1.1), "SPY": frame(base_px + 100)}
    _, au = audit_and_align(root, fr)
    assert au["verdict_start"] == "2013-02-05" and au["provisional_row_dropped"] == "2014-03-31"
    assert au["leading_zero_volume_rows_dropped"]["XLE"]["count"] == 0

    def stops(name: str, df: pd.DataFrame) -> bool:
        try:
            audit_and_align(root, fr | {name: df})
            return False
        except RuntimeError:
            return True
    zl = fr["XLE"].copy()
    zl.iloc[:80, zl.columns.get_loc("volume")] = 0.0           # 80 leading flat placeholder rows (into 2011-02)
    for col in ("open", "high", "low"):
        zl.iloc[:80, zl.columns.get_loc(col)] = zl["close"].iloc[:80].to_numpy()
    nf = fr["XLE"].copy()
    nf.iloc[:80, nf.columns.get_loc("volume")] = 0.0           # zero volume but moving prices: kept (missing volume)
    _, au_nf = audit_and_align(root, fr | {"XLE": nf})
    assert au_nf["leading_zero_volume_rows_dropped"]["XLE"]["count"] == 0 and au_nf["untradable_opens"]["XLE"]["count"] == 80
    assert au_nf["verdict_start"] == "2013-02-05"
    _, au2 = audit_and_align(root, fr | {"XLE": zl})
    assert au2["leading_zero_volume_rows_dropped"]["XLE"]["count"] == 80 and au2["first"] == zl.index[80].date().isoformat()
    assert au2["verdict_start"] == "2013-08-05"                # the first common session moved past 2011-02-05
    zm = fr["XLE"].copy()
    zm.iloc[300, zm.columns.get_loc("volume")] = 0.0             # zero volume after trading started: untradable open, recorded
    _, au3 = audit_and_align(root, fr | {"XLE": zm})
    assert au3["untradable_opens"]["XLE"]["count"] == 1
    od = fr["SPY"].copy()
    od.iloc[20, od.columns.get_loc("open")] = od["high"].iloc[20] + 0.01   # open above the high: recorded only
    _, au4 = audit_and_align(root, fr | {"SPY": od})
    assert au4["ohlc_order_odd_rows"]["SPY"]["count"] == 1
    three = fr["XLV"].drop([pd.Timestamp("2011-03-15"), pd.Timestamp("2012-06-01"), pd.Timestamp("2013-06-03")])
    _, au5 = audit_and_align(root, fr | {"XLV": three})
    assert len(au5["missing_in_critical"]) == 3
    four = three.drop(pd.Timestamp("2013-09-03"))
    assert stops("XLV", four), "four missing sessions inside the critical window not refused"
    zc = fr["SOXX"].copy()
    zc.iloc[10, zc.columns.get_loc("close")] = 0.0               # a non-positive close anywhere stops
    assert stops("SOXX", zc)
    j = fr["XLV"].copy()
    j.loc[pd.Timestamp("2013-06-03"):, ["open", "high", "low", "close"]] *= 0.5
    assert stops("XLV", j), "unadjusted split-like jump not refused"
    # 11 inputs vs manifest and the truncation guard (Kiwoom-format files)
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        def kiwoom_file(name: str, df: pd.DataFrame) -> str:
            rows = [{"dt": d.strftime("%Y%m%d"), "open_pric": f"{r.open:.4f}", "high_pric": f"{r.high:.4f}",
                     "low_pric": f"{r.low:.4f}", "cur_prc": f"{r.close:.4f}", "acc_trde_qty": f"{r.volume:.0f}",
                     "upd_stkpc_tp": ("3231" if i == 5 else "")} for i, (d, r) in enumerate(df.iterrows())]
            pth = troot / f"{name}.json"
            pth.write_text(json.dumps({"result": {"return_code": 0, "return_msg": "ok", "result_list": rows[::-1]}}), encoding="utf-8")
            return pth.name
        idx_l = S4.expected_sessions("2010-04-05", "2014-03-31")      # SOXL's earlier Kiwoom start
        px_l = 50 * np.cumprod(1 + np.random.default_rng(2).normal(0, 0.03, len(idx_l)))
        soxl_long = pd.DataFrame({"open": px_l, "high": px_l * 1.01, "low": px_l * 0.99, "close": px_l, "volume": 1e6,
                                  "adj_code": "", "split": False}, index=idx_l)
        fx = {tk: load_kiwoom(troot / kiwoom_file(tk, soxl_long if tk == "SOXL" else fr[tk])) for tk in TICKERS}
        assert fx["SOXX"]["split"].sum() == 1 and (fx["SOXX"]["adj_code"] == "3231").sum() == 1
        man = {"files": {tk: {"rows": len(fx[tk]), "first": fx[tk].index[0].date().isoformat(),
                              "last": fx[tk].index[-1].date().isoformat()} for tk in TICKERS}}
        assert check_inputs(troot, man, fx)["XLE"]["late_start_confirmed"] is None

        def in_refused(man_, fx_) -> bool:
            try:
                check_inputs(troot, man_, fx_)
                return False
            except RuntimeError:
                return True
        bad = json.loads(json.dumps(man)); bad["files"]["SPY"]["rows"] += 1
        assert in_refused(bad, fx), "rows differing from the manifest not refused"
        late_soxx = fx | {"SOXX": fx["SOXX"].iloc[30:]}
        lm = json.loads(json.dumps(man)); lm["files"]["SOXX"] |= {"rows": len(late_soxx["SOXX"]),
                                                                 "first": late_soxx["SOXX"].index[0].date().isoformat()}
        assert in_refused(lm, late_soxx), "SOXX starting after the earlier full fetch not refused"
        late = fr["XLE"].iloc[100:]
        lx = fx | {"XLE": load_kiwoom(troot / kiwoom_file("XLE_late", late))}
        lmx = json.loads(json.dumps(man)); lmx["files"]["XLE"] |= {"rows": len(late), "first": late.index[0].date().isoformat()}
        assert in_refused(lmx, lx), "a late start without a confirming fetch not refused"
        lmx["files"]["XLE"]["confirm"] = {"path": kiwoom_file("XLE_late_confirm", late)}
        assert check_inputs(troot, lmx, lx)["XLE"]["late_start_confirmed"]["rows"] == len(late)
        newer = pd.concat([late, late.iloc[[-1]].set_axis([late.index[-1] + pd.Timedelta(days=3)])])
        lmx["files"]["XLE"]["confirm"] = {"path": kiwoom_file("XLE_late_newer", newer)}
        assert check_inputs(troot, lmx, lx)["XLE"]["late_start_confirmed"]["newer_rows_ignored"] == 1
        lmx["files"]["XLE"]["confirm"] = {"path": kiwoom_file("XLE_late_short", late.iloc[50:])}
        assert in_refused(lmx, lx), "a confirming fetch with a different start not refused"
    # 12 identity: Kiwoom close / pinned Nasdaq copy over the last 60 sessions
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        (troot / IDENTITY_DIR).mkdir(parents=True)
        idf = {tk: fr[tk] for tk in TICKERS}

        def nasdaq_file(tk: str, df: pd.DataFrame, scale: float = 1.0, sym: str | None = None) -> str:
            rows = [{"date": d.strftime("%m/%d/%Y"), "close": f"${c * scale:,.4f}"} for d, c in df["close"].items()]
            pth = troot / IDENTITY_DIR / f"{tk}.json"
            pth.write_text(json.dumps({"data": {"symbol": sym or tk, "tradesTable": {"rows": rows[::-1]}}}), encoding="utf-8")
            return sha256_file(pth)
        pins = {tk: nasdaq_file(tk, idf[tk].iloc[-300:]) for tk in TICKERS}
        res = identity_check(troot, idf, pins)
        assert all(v["passed"] and v["sessions"] == 60 for v in res.values())

        def id_stops(pins_, frames_) -> bool:
            try:
                identity_check(troot, frames_, pins_)
                return False
            except RuntimeError:
                return True
        assert id_stops(pins | {"SPY": "0" * 64}, idf), "a changed identity copy not refused"
        pins2 = pins | {"XLE": nasdaq_file("XLE", idf["XLE"].iloc[-300:], 1.03)}
        assert id_stops(pins2, idf), "a 3% level gap (another ticker) not refused"
        pins3 = pins | {"XLE": nasdaq_file("XLE", idf["XLE"].iloc[-300:], 1.0, "XLV")}
        assert id_stops(pins3, idf), "an identity copy for another symbol not refused"
        pins4 = pins | {"XLE": nasdaq_file("XLE", idf["XLE"].iloc[-300:])}
        sx = idf["SPY"].copy()
        sx.iloc[-30, sx.columns.get_loc("split")] = True              # split row inside the span: only later sessions count
        r4 = identity_check(troot, idf | {"SPY": sx}, pins4)
        assert r4["SPY"]["sessions"] == 28 and r4["SPY"]["after_split"] == sx.index[-30].date().isoformat()
    print("self-test passed (hand-built engine, schedule, freeze, causality + per-step leak, trim, exposure E, "
          "episodes, verdict start, gates + verdict map, contract/amendment/manifest/write-once, "
          "data audit rules, inputs vs manifest + truncation guard, identity vs pinned copies)")

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
        if args.out is not None:
            raise SystemExit("STOP: --out is not allowed with --run (the contract writes only its own results file)")
        return run_all(root, root / RESULTS_JSON)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
