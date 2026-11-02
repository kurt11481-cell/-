#!/usr/bin/env python3
"""p-s44 / S4-4: pre-registered stock-core rebalance replay (2026-11-02).

Question (contract: docs/claude/s44-preregistration-2026-11-02.md + its .sha256):
  an equal-weight stock core that is put back to its target weights whenever one name drifts more
  than 10 percentage points from target (band rebalance, loss-limit-review-s5 C.8) -- does it beat
  leaving the weights alone (hold, the Champion: today the band is a card note only, R3 line 42), and
  does it beat the simpler same-exposure alternative (calendar rebalance once a year)?

Universe: the 32 names of loss-limit-review-s5 C.2 (fixed on 2026-10-01, before this test).  Eligible
= Kiwoom history (placeholder rows dropped) starting no later than 2005-01-31 and clean inside the
verdict window.  Every 4-name combination of the eligible names is one basket (no sampling, no seed).
Verdict window 2005-02-05 .. 2016-08-04 (the 2016-10 .. 2026-09 span was already explored in C.3 and
is report only).  Price returns only (Kiwoom split-adjusted daily bars), no cash target, costs come out
of a cash account that starts at zero after the first fill.

Contract: decide at the regular-session close, fill at the next open; a basket with any invalid open
that session keeps its fill pending.  Costs per traded notional.

Reused read-only (pinned): the S4 runner (calendar, folds, positions, slice_metrics) and through it
the 08-05 metrics.  The vectorised basket engine is new and is checked against the S4 metrics.

Historical research only: no broker, no Kiwoom tools, no policy, core or registry writes, no orders.
Run it in the cloud container, not on the user's PC.  Any STOP writes no result.

  --self-test   synthetic and hand-built checks (no contract and no market data needed)
  --run         verify hashes, run the contract once, write the results JSON (never overwrites)
  --shadow      forward shadow record (report only), once, after FORWARD_TO, from its own manifest
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import platform
import sys
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
PREREG = "docs/claude/s44-preregistration-2026-11-02.md"
PREREG_SIDECAR = "docs/claude/s44-preregistration-2026-11-02.sha256"
INPUTS_MANIFEST = "docs/claude/s44-inputs/inputs-manifest.json"
RESULTS_JSON = "docs/claude/s44-results.json"
SHADOW_MANIFEST = "docs/claude/s44-shadow-inputs/inputs-manifest.json"
SHADOW_JSON = "docs/claude/s44-shadow-results.json"
IDENTITY_DIR = "docs/claude/s44-inputs/nasdaq-identity"
KST = timezone(timedelta(hours=9))

# Parameters are fixed by the pre-registration; never edit after seeing a result.
UNIVERSE = ("NVDA", "AMD", "AVGO", "MRVL", "MU", "INTC", "QCOM", "TXN", "ADI", "NXPI", "ON", "MCHP",
            "AMAT", "LRCX", "KLAC", "TER", "MPWR", "SMCI", "ANET", "WDC", "STX", "DELL", "HPE", "VRT",
            "BE", "TSM", "ASML", "COHR", "CIEN", "LITE", "ORCL", "PLTR")      # C.2, 2026-10-01
ELIGIBLE_BY = "2005-01-31"            # first real row on or before this date
VERDICT = ("2005-02-05", "2016-08-04")
HALVES = (("2005-02-05", "2010-08-04"), ("2010-08-05", "2016-08-04"))
RECENT_FROM = "2016-08-05"            # already explored in C.3: report only
BASKET = 4                            # names per basket (C.3); 5 is report only (C.8 core size)
JUDGED_BAND, NEIGHBOR_BANDS = 0.10, (0.05, 0.15)
COSTS = (10.0, 50.0)                  # 50 = the user's real fee 25bp + 25bp slippage
MIN_UNIVERSE = 12
MAX_DATA_INELIGIBLE = 4               # names dropped for data gaps or unavailable responses before STOP
MAX_CAL_GAPS = 3
HISTORY_GAP = 20                      # a run of more missing sessions: history out for TICKER_REUSE names, data out otherwise
TICKER_REUSE = ("DELL", "COHR")       # symbols another company used before (pre-registered)
ROW_CAP = 5500                        # Kiwoom usa06012 full fetch returns at most this many rows
FETCH_DEADLINE = "2026-11-20T23:59:59+09:00"   # later fetches push the row-capped start past ELIGIBLE_BY
EXTRA_CLOSURES = ("2004-06-11", "2007-01-02")  # NYSE days of mourning (Reagan, Ford) not in the S4 rule set
YEAR_SESSIONS = {2005: 252, 2006: 251, 2007: 251, 2008: 253}   # NYSE sessions per year (calendar self-check)
BIG_MOVE = 0.25                       # recorded
SPLIT_LIKE_TOL = 0.005                # STOP: close/previous close within 0.5% (relative) of an unadjusted split ratio
SPLIT_RATIOS = (2, 3, 4, 5, 10)
SPLIT_CODE = "3231"
P1_MEDIAN, P1_WIN = 0.005, 0.60
P6_WIN = 0.55
FOLD_SHARE_MAX = 0.50
IDENTITY_SESSIONS, IDENTITY_MIN, IDENTITY_TOL = 60, 20, 0.01
CAUSALITY_BASKETS, CAUSALITY_CUTS = 30, 8
CHUNK = 4000
FORWARD_TO = "2027-04-30"
SHADOW_FETCH_FROM = "2027-05-04T00:00:00+09:00"
STOP_DIR = "docs/claude/s44-stops"
IDENTITY_PINNED: dict[str, str] = {   # sha256 of each Nasdaq public copy (fetched 2026-11-02 19:54-19:55 KST, 2026-06-01..10-30)
    "NVDA": "55e83106a82f7316dc72415556ee3282202de8619bc212cf1658148daca60ae0",
    "AMD": "daa84db0a0f2d4e7449f688747b285a6adf147cf07e29a1ab10b9662c87c42fe",
    "AVGO": "74140e4d7cd084be840bde58cd6e55139dff59012ef8b9fd586e28b2ae317b48",
    "MRVL": "30a5dc3f6f98772151519740e639474eba700a431237784e86333774f83fbf61",
    "MU": "9c77f2ed7252b8aa72b2096a35514b95c7d4d9576600b40704aceda9251df8ad",
    "INTC": "7bf67216fff78b01fe28b742178488c63105c70dcb4b0f113b3d7c00165f2dfc",
    "QCOM": "cbfdf751b1fea5014bde08c97cda5d02b61798fadcfb6e8efc6e4f69253e23e4",
    "TXN": "60d76760be711382ef12ae5005d99b6689b069152d760117afcaa1d6ccf27362",
    "ADI": "b84ee0a08a59338f154dcbc3e9b644d17553f08833c71792fb68b6ac12a16ac5",
    "NXPI": "54a1ac213bd759ea28d9e93d8c25bcfdb11d360eb7b7304cb73f8dbe42da9a6a",
    "ON": "25c89cdf4a25823528eb173d79658a88e79438262ea763a36b7ec115a4e48d72",
    "MCHP": "6bf9af9fcbb9288e25a11671ba7d750be6380b044a668542da9a5be80a0d9bd6",
    "AMAT": "67263148f464ea2f5a246f18c024c6aaf410a8c8895693c305542086caf35be9",
    "LRCX": "e7de6e30816ddb3fded3dcae23d4d675f9d7f2be9d8ff10a0501b60c16687506",
    "KLAC": "d020149404713f407612ddfc3243e54323c00e8e14ccd11ef620da7c1db43a3e",
    "TER": "b225f3744724124d18d65d48a053bdf6c34bd8786bc587d246e6fd3bfa61e1d3",
    "MPWR": "8155e2ea15610bebc28c181e8f34ab51cb023c8d84664be56f88c884b9f66b34",
    "SMCI": "2f6e05600a4e2b264c4c45eab761f95f4d140ed7b05ebe5cbd15a54a64786c39",
    "ANET": "bef3e5cae4fe18d82b17cf63b6bffab87fad6fc9223ed798872af439f14b003a",
    "WDC": "4ea1e2cd641c90a14e1298c4ef0a67c101b2847e7a1a637e487a08746d6b88e0",
    "STX": "6321660df11e220d21f8c4aa95587dacdcc09a1cc7b79356d505e08ff1fe2edf",
    "DELL": "f10e365d3e9626b541f47e2e343118a495246ee0d80766346aaae13a0a12b7b1",
    "HPE": "c6c9da1cb439abc9e61fc6b50f4523bce5ed2ef7d3b1e74bdadc747af10ffd51",
    "VRT": "8caed69861b6021cc73b6228a83cb815a5fd7a1a1ff7f34b7c4d76cf65f1a347",
    "BE": "6864a41880dc2c57b38aad0f2a422f0ebc5c96cce3c8551eb8fddc6ecc5a76cd",
    "TSM": "d4b8ca82e423f72418605bdc1e0c5ed26ae44cbd842a3dd94f23d4bb28392ef5",
    "ASML": "15a4733bb66dd6769096fcfe269ed848422c7cf9101ac0369f9b6e6a43a1d3e5",
    "COHR": "9b03785f14b41eae21aa1161c224330a4dd1af7ac4aae064db7263f2338247eb",
    "CIEN": "7b4106295ab6d0b00f800b39ef855d323253bdbe927ee0383aaf582f5c4010ed",
    "LITE": "9fb86cdcfafb76d24453e4a2fe7080f7f78538b00a351a4a7e04619208b1cfc6",
    "ORCL": "ec8422f0f2d9fcafbef0ad8f81cf985e14e03a2c34ac8e6f99b7fdd64db93862",
    "PLTR": "18e4365a3cba12eb332749b155e80b6b370bab023ad15fa0217384ecc63580cd",
}

_MODS: dict[str, Any] = {}


class ResultExists(Exception):
    """The results file is already there: refused without a STOP record."""


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
        _MODS["s4"] = load_module("s44_s4_runner", root / S4_RUNNER)
    return _MODS["s4"]


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


# ----------------------------------------------------------------------------
# contract, manifest, inputs
# ----------------------------------------------------------------------------
def check_contract(root: Path, prereg: str = PREREG, sidecar: str = PREREG_SIDECAR,
                   runner: Path | None = None) -> dict[str, Any]:
    """Sidecar lines: raw_sha256, lf_sha256, runner_sha256, fixed_at (exactly once, kept through
    amendments) and optional amended_at lines (section 10 amendments)."""
    side = (root / sidecar).read_text(encoding="utf-8")
    pairs = [(ln.split()[0], ln.split()[1]) for ln in side.splitlines() if len(ln.split()) >= 2]
    field = dict(pairs)
    doc = (root / prereg).read_bytes()
    got = hashlib.sha256(doc).hexdigest()
    if field.get("raw_sha256") != got:
        raise RuntimeError("STOP: pre-registration changed after fixation (sidecar mismatch)")
    rsha = sha256_file(Path(__file__).resolve() if runner is None else runner)
    if field.get("runner_sha256") != rsha:
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
            "runner_sha256": rsha, "fixed_at": fixed[0], "amended_at": amended}


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


def check_manifest(root: Path, rel: str, fixed_at: str, after: str | None = None,
                   deadline: str | None = FETCH_DEADLINE) -> dict[str, Any]:
    """Each ticker once: either a file entry (path, sha256, called_kst, rows, first, last, optional
    confirm) or {"unavailable": reason, "tried": [...]}.  Every call time must carry an offset, be after
    the lock (and after `after` for the shadow manifest) and, for the main run, not after the deadline."""
    man = json.loads((root / rel).read_text(encoding="utf-8"))
    t_fixed = datetime.fromisoformat(fixed_at)
    t_after = datetime.fromisoformat(after) if after else t_fixed
    t_dead = datetime.fromisoformat(deadline) if deadline else None
    files = man.get("files") or {}
    if sorted(files) != sorted(UNIVERSE):
        raise RuntimeError(f"STOP: manifest tickers differ from the universe: {sorted(set(files) ^ set(UNIVERSE))}")

    def when(tk: str, s: str) -> datetime:
        t = datetime.fromisoformat(s)
        if t.tzinfo is None:
            raise RuntimeError(f"STOP: {tk}: call time has no UTC offset")
        if t < t_fixed or t < t_after:
            raise RuntimeError(f"STOP: {tk} was fetched before the contract was fixed (or before the allowed start)")
        if t_dead is not None and t > t_dead:
            raise RuntimeError(f"STOP: {tk} was fetched after the deadline {deadline}")
        return t

    for tk, ent in files.items():
        if "unavailable" in ent:
            tried = ent.get("tried")
            if not isinstance(tried, list) or not tried or not all(
                    isinstance(tr, dict) and {"exchange", "called_kst", "return_code"} <= set(tr) for tr in tried):
                raise RuntimeError(f"STOP: {tk}: unavailable without the attempts listed as "
                                   "[{exchange, called_kst, return_code}]")
            for tr in tried:
                when(tk, str(tr["called_kst"]))
            continue
        got = sha256_file(root / ent["path"])
        if got != ent["sha256"]:
            raise RuntimeError(f"STOP: {tk}: sha256 {got} != manifest {ent['sha256']}")
        when(tk, ent["called_kst"])
        for key in ("rows", "first", "last"):
            if key not in ent:
                raise RuntimeError(f"STOP: {tk}: manifest entry has no {key}")
        conf = ent.get("confirm")
        if conf is not None:
            if sha256_file(root / conf["path"]) != conf["sha256"]:
                raise RuntimeError(f"STOP: {tk}: confirming fetch sha256 differs from the manifest")
            when(tk, conf["called_kst"])
    return man


def drop_placeholders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Leading zero-volume rows with open = high = low = close (Kiwoom placeholder before the first trade)."""
    flat = ((df["volume"].to_numpy(float) <= 0) & (df["open"] == df["close"]).to_numpy()
            & (df["high"] == df["close"]).to_numpy() & (df["low"] == df["close"]).to_numpy())
    k0 = int(np.argmin(flat)) if not flat.all() else len(df)
    info = {"count": k0, "range": [df.index[0].date().isoformat(), df.index[k0 - 1].date().isoformat()] if k0 else None}
    return df.iloc[k0:], info


def check_inputs(root: Path, man: dict[str, Any], frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Manifest rows/first/last must describe the file as loaded.  Truncation guard (the response has no
    continuation flag): a file with ROW_CAP rows or more is row-limited -- if it starts after ELIGIBLE_BY
    the fetch came too late (STOP; an implementation problem, fixable only by an amendment).  A shorter
    file starting after ELIGIBLE_BY (it would leave the universe) needs a confirming fetch with exactly
    the same dates up to this file's last date (newer rows of the confirming fetch are ignored)."""
    out = {}
    for tk, df in frames.items():
        ent = man["files"][tk]
        first, last = df.index[0].date().isoformat(), df.index[-1].date().isoformat()
        if int(ent["rows"]) != len(df) or ent["first"] != first or ent["last"] != last:
            raise RuntimeError(f"STOP: {tk}: manifest rows/first/last differ from the file")
        confirmed = None
        if first > ELIGIBLE_BY:
            if len(df) >= ROW_CAP:
                raise RuntimeError(f"STOP (implementation): {tk} has {len(df)} rows (row limit) and starts {first}, "
                                   f"after {ELIGIBLE_BY} -- the fetch was too late")
            conf = ent.get("confirm")
            if conf is None:
                raise RuntimeError(f"STOP: {tk} starts {first} (after {ELIGIBLE_BY}) without a confirming fetch")
            cdf = load_kiwoom(root / conf["path"])
            if not cdf.index[cdf.index <= df.index[-1]].equals(df.index):
                raise RuntimeError(f"STOP: {tk}: the confirming fetch has other dates up to {last} (truncated fetch?)")
            confirmed = {"first": cdf.index[0].date().isoformat(), "rows": int(len(cdf)),
                         "newer_rows_ignored": int((cdf.index > df.index[-1]).sum())}
        out[tk] = {"rows": len(df), "first": first, "last": last, "row_limited": len(df) >= ROW_CAP,
                   "late_start_confirmed": confirmed}
    return out


def load_nasdaq_close(path: Path, tk: str) -> pd.Series:
    j = json.loads(path.read_text(encoding="utf-8"))
    if str(j["data"]["symbol"]).upper() != tk:
        raise RuntimeError(f"STOP: identity copy {path.name} is for {j['data']['symbol']}, not {tk}")
    rows = j["data"]["tradesTable"]["rows"]
    vals = {pd.Timestamp(datetime.strptime(r["date"], "%m/%d/%Y")): float(str(r["close"]).replace("$", "").replace(",", ""))
            for r in rows}
    return pd.Series(vals).sort_index()


def identity_check(root: Path, frames: dict[str, pd.DataFrame], pinned: dict[str, str] | None = None,
                   ident_dir: str = IDENTITY_DIR) -> dict[str, Any]:
    """Labels come from the call order: over the last 60 overlapping sessions (Kiwoom provisional last
    row dropped; only sessions after a split row inside that span) the median of Kiwoom close / Nasdaq
    public close must be within 1 +- 1%, with at least 20 sessions."""
    pinned = IDENTITY_PINNED if pinned is None else pinned
    out = {}
    for tk, df in frames.items():
        p = root / ident_dir / f"{tk}.json"
        got = sha256_file(p)
        if got != pinned.get(tk):
            raise RuntimeError(f"STOP: identity copy {tk}: sha256 {got} != pinned {pinned.get(tk)}")
        nq = load_nasdaq_close(p, tk)
        k = df.iloc[:-1]
        common = k.index.intersection(nq.index)[-IDENTITY_SESSIONS:]
        sp = [d for d in common if bool(k.loc[d, "split"])]
        if sp:
            common = common[common > max(sp)]
        ratio = k.loc[common, "close"].to_numpy(float) / nq.loc[common].to_numpy(float)
        med = float(np.median(ratio)) if len(ratio) else float("nan")
        passed = bool(len(ratio) >= IDENTITY_MIN and abs(med - 1.0) <= IDENTITY_TOL)
        out[tk] = {"passed": passed, "sessions": int(len(ratio)), "median_ratio": med, "copy_sha256": got}
        if not passed:
            raise RuntimeError(f"STOP: identity check failed for {tk}: " + json.dumps(clean(out[tk])))
    return out


# ----------------------------------------------------------------------------
# eligibility and data audit
# ----------------------------------------------------------------------------
def audit_calendar(root: Path) -> set[str]:
    """NYSE full closures 2004-2027: the S4 rule set (its module calendar starts in 2009) extended back to
    2004, plus the two days of mourning.  Checked against the known session counts per year."""
    S4 = s4(root)
    return set(S4.nyse_full_closures(2004, 2027)) | set(EXTRA_CLOSURES)


def audit_sessions(closures: set[str], start: str, end: str) -> pd.DatetimeIndex:
    idx = pd.date_range(start, end, freq="B")
    return idx.difference(pd.to_datetime(sorted(closures))).sort_values()


def check_calendar(closures: set[str]) -> dict[str, int]:
    got = {y: len(audit_sessions(closures, f"{y}-01-01", f"{y}-12-31")) for y in YEAR_SESSIONS}
    if got != YEAR_SESSIONS:
        raise RuntimeError(f"STOP (implementation): audit calendar session counts {got} != {YEAR_SESSIONS}")
    return got


def split_like(r: np.ndarray) -> np.ndarray:
    """Close / previous close within SPLIT_LIKE_TOL (relative) of an unadjusted split (1/k) or reverse split (k)."""
    p = 1.0 + r
    hit = np.zeros(len(r), dtype=bool)
    for k in SPLIT_RATIOS:
        for ratio in (1.0 / k, float(k)):
            hit |= np.abs(p - ratio) <= SPLIT_LIKE_TOL * ratio
    return hit


def longest_run(missing: pd.DatetimeIndex, sessions: pd.DatetimeIndex) -> tuple[int, list[str] | None]:
    """Longest run of consecutive calendar sessions that are missing, and its first / last date."""
    if not len(missing):
        return 0, None
    pos = np.sort(sessions.get_indexer(missing))
    best, best_end, run = 1, 0, 1
    for i in range(1, len(pos)):
        run = run + 1 if pos[i] == pos[i - 1] + 1 else 1
        if run > best:
            best, best_end = run, i
    if best == 1:
        best_end = 0
    lo, hi = pos[best_end - best + 1], pos[best_end]
    return int(best), [sessions[lo].date().isoformat(), sessions[hi].date().isoformat()]


def audit_universe(root: Path, frames: dict[str, pd.DataFrame], unavailable: dict[str, Any],
                   window: tuple[str, str] = VERDICT) -> tuple[list[str], dict[str, Any]]:
    """Eligibility (decided by the data, never by results), over each name's whole history after the
    leading placeholder rows (first row .. last row; the last Kiwoom row is provisional and skipped):
      history out: first row after ELIGIBLE_BY, or one run of more than HISTORY_GAP missing sessions (a
        broken or reused ticker history);
      data out (counted): no response, a non-finite / non-positive close, more than MAX_CAL_GAPS missing
        or extra sessions vs the audit calendar from the first row to the verdict-window end;
      STOP: a split-like close move anywhere (an unadjusted split fakes a crash or a jump), more than
        MAX_DATA_INELIGIBLE names out for data, fewer than MIN_UNIVERSE eligible names.
    Missing / extra sessions after the verdict window are recorded only."""
    closures = audit_calendar(root)
    cal_counts = check_calendar(closures)
    w_end = pd.Timestamp(window[1])
    rep: dict[str, Any] = {"calendar_session_counts": cal_counts, "placeholders": {}, "per_ticker": {},
                           "unavailable": unavailable}
    eligible, data_lost = [], list(unavailable)
    stops = []
    for tk in UNIVERSE:
        if tk not in frames:
            continue
        df, info = drop_placeholders(frames[tk])
        frames[tk] = df
        rep["placeholders"][tk] = info
        row: dict[str, Any] = {"first": df.index[0].date().isoformat() if len(df) else None}
        if not len(df) or df.index[0] > pd.Timestamp(ELIGIBLE_BY):
            row["eligible"], row["reason"] = False, "history: starts after ELIGIBLE_BY"
            rep["per_ticker"][tk] = row
            continue
        body = df.iloc[:-1]
        sess = audit_sessions(closures, body.index[0].date().isoformat(), body.index[-1].date().isoformat())
        missing_all = sess.difference(body.index)
        run, run_span = longest_run(missing_all, sess)
        in_w = lambda ix: ix[ix <= w_end]
        missing, extra = in_w(missing_all), in_w(body.index.difference(sess))
        cl = body["close"].to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = cl[1:] / cl[:-1] - 1.0
        big = body.index[1:][np.abs(r) > BIG_MOVE]
        sl = body.index[1:][split_like(r)]
        row.update({"longest_missing_run": run, "longest_missing_span": run_span, "missing_in_window": [d.date().isoformat() for d in missing],
                    "extra_in_window": [d.date().isoformat() for d in extra],
                    "missing_after_window": int(len(missing_all) - len(missing)),
                    "big_moves": [d.date().isoformat() for d in big], "split_like": [d.date().isoformat() for d in sl],
                    "split_codes": [d.date().isoformat() for d in body.index[body["split"].to_numpy()]]})
        if run > HISTORY_GAP and tk in TICKER_REUSE:
            row["eligible"], row["reason"] = False, f"history: a run of {run} missing sessions (reused ticker)"
        elif run > HISTORY_GAP:
            row["eligible"], row["reason"] = False, f"data: a run of {run} missing sessions {run_span}"
            data_lost.append(tk)
        elif not (np.isfinite(cl).all() and (cl > 0).all()):
            row["eligible"], row["reason"] = False, "data: non-finite or non-positive close"
            data_lost.append(tk)
        elif len(missing) > MAX_CAL_GAPS or len(extra) > MAX_CAL_GAPS:
            row["eligible"], row["reason"] = False, "data: calendar gaps in the verdict span"
            data_lost.append(tk)
        else:
            row["eligible"] = True
            eligible.append(tk)
            if len(sl):
                stops.append(tk)
        rep["per_ticker"][tk] = row
    rep["eligible"] = eligible
    rep["data_lost"] = data_lost
    if stops:
        raise RuntimeError(f"STOP (fail closed): split-like close moves in {stops}: "
                           + json.dumps({t: rep["per_ticker"][t]["split_like"] for t in stops}))
    if len(data_lost) > MAX_DATA_INELIGIBLE:
        raise RuntimeError(f"STOP: {len(data_lost)} names lost to data ({data_lost}) > {MAX_DATA_INELIGIBLE}")
    if len(eligible) < MIN_UNIVERSE:
        raise RuntimeError(f"STOP: only {len(eligible)} eligible names (< {MIN_UNIVERSE})")
    return eligible, rep


def build_market(frames: dict[str, pd.DataFrame], names: list[str], start: pd.Timestamp | None = None):
    """Common sessions of `names` (the last row is provisional and dropped)."""
    common = None
    for tk in names:
        idx = frames[tk].index
        common = idx if common is None else common.intersection(idx)
    if start is not None:
        common = common[common >= start]
    provisional = common[-1]
    common = common[:-1]
    O = np.column_stack([frames[tk].loc[common, "open"].to_numpy(float) for tk in names])
    C = np.column_stack([frames[tk].loc[common, "close"].to_numpy(float) for tk in names])
    V = np.column_stack([frames[tk].loc[common, "volume"].to_numpy(float) for tk in names])
    ok = np.isfinite(O) & (O > 0) & np.isfinite(V) & (V > 0)
    return common, O, C, ok, provisional


# ----------------------------------------------------------------------------
# the new part: vectorised basket engine
# ----------------------------------------------------------------------------
def year_end_decisions(dates: pd.DatetimeIndex) -> np.ndarray:
    """True at the last session of each calendar year (fill at the first session of the next year)."""
    yr = dates.year.to_numpy()
    dec = np.zeros(len(dates), dtype=bool)
    dec[:-1] = yr[1:] != yr[:-1]
    return dec


def simulate_baskets(O: np.ndarray, C: np.ndarray, ok: np.ndarray, idx: np.ndarray, rule: str,
                     band: float = 0.0, cost_bps: float = 10.0, calendar: np.ndarray | None = None,
                     snap: int | None = None, peek: bool = False) -> dict[str, Any]:
    """O, C, ok: (n, K) universe arrays.  idx: (B, m) basket columns, equal target 1/m.
    rule 'hold': only the first allocation.  'band': after the close, if any name's weight differs from
    1/m by more than `band`, the whole basket goes back to 1/m at the next open.  'calendar': back to 1/m
    at the open after each True in `calendar`.  All start as cash 1.0; the close of session 0 decides
    the first allocation.  Each session: overnight move to the open, a pending fill at the open if every
    basket open is valid (else it stays pending), intraday move to the close, value at the close, then
    the close decides.  A name with an invalid open moves close to close.  Costs per traded notional come
    out of cash.  `snap` (checks only): also return the state right after the fill step of session snap.
    `peek` (self-test only): a deliberately leaking variant that decides on the next close."""
    n = C.shape[0]
    B, m = idx.shape
    tgt = 1.0 / m
    c = cost_bps / 10_000.0
    Ob, Cb, okb = O[:, idx], C[:, idx], ok[:, idx]           # (n, B, m)
    H = np.zeros((B, m))
    cash = np.ones(B)
    pending = np.zeros(B, dtype=bool)
    V = np.full((n, B), np.nan)
    fills = np.zeros(B, dtype=np.int64)
    stale = np.zeros(B, dtype=np.int64)
    turnover = np.zeros(B)
    state = None
    for t in range(n):
        okt = okb[t]
        if t > 0:
            H = np.where(okt, H * (Ob[t] / Cb[t - 1]), H)
        if pending.any():
            f = pending & okt.all(axis=1)
            if f.any():
                v = H[f].sum(axis=1) + cash[f]
                delta = tgt * v[:, None] - H[f]
                notional = np.abs(delta).sum(axis=1)
                H[f] = H[f] + delta
                cash[f] = cash[f] - delta.sum(axis=1) - c * notional
                fills[f] += 1
                turnover[f] += notional
                pending[f] = False
            stale += pending
        if snap is not None and t == snap:
            state = {"H": H.copy(), "cash": cash.copy(), "pending": pending.copy()}
        if t > 0:
            H = np.where(okt, H * (Cb[t] / Ob[t]), H * (Cb[t] / Cb[t - 1]))
        else:
            H = np.where(okt, H * (Cb[t] / Ob[t]), H)
        val = H.sum(axis=1) + cash
        V[t] = val
        if t == 0:
            dec = np.ones(B, dtype=bool)
        elif rule == "hold":
            dec = np.zeros(B, dtype=bool)
        elif rule == "band":
            if peek and t + 1 < n:
                Hn = H * (Cb[t + 1] / Cb[t])
                w = Hn / (Hn.sum(axis=1) + cash)[:, None]
            else:
                w = H / val[:, None]
            dec = (np.abs(w - tgt) > band + 1e-12).any(axis=1)
        elif rule == "calendar":
            dec = np.full(B, bool(calendar[t]))
        else:
            raise ValueError(rule)
        pending |= dec
    return {"V": V, "fills": fills, "stale": stale, "turnover": turnover, "state": state}


def window_stats(V: np.ndarray, dates: pd.DatetimeIndex, a: int, z: int) -> dict[str, np.ndarray]:
    """Per basket, the S4 / 08-05 definitions: slice value = 1 at the close before `a`; CAGR over
    (dates[z] - dates[a]).days / 365.25 years; MDD of the series with the starting 1 prepended."""
    base = V[a - 1]
    X = V[a - 1:z + 1] / base
    years = max((dates[z] - dates[a]).days / 365.25, 1 / 252)
    cagr = X[-1] ** (1.0 / years) - 1.0
    mdd = (X / np.maximum.accumulate(X, axis=0) - 1.0).min(axis=0)
    return {"cagr": cagr, "mdd": mdd, "total": X[-1] - 1.0}


def fold_returns(V: np.ndarray, dates: pd.DatetimeIndex, folds: list[tuple[int, int]]) -> np.ndarray:
    return np.stack([V[z] / V[a - 1] - 1.0 for a, z in folds])        # (F, B)


def run_rules(O, C, ok, idx, dates, cost: float, rules: dict[str, tuple[str, float]], cal: np.ndarray,
              windows: dict[str, tuple[int, int]], folds: list[tuple[int, int]] | None = None) -> dict[str, Any]:
    """Run each rule over the baskets in chunks and keep only the window statistics."""
    out: dict[str, Any] = {}
    for name, (rule, band) in rules.items():
        parts: dict[str, list] = {w: [] for w in windows}
        fparts, fl, tv, st = [], [], [], []
        for s in range(0, len(idx), CHUNK):
            run = simulate_baskets(O, C, ok, idx[s:s + CHUNK], rule, band, cost, cal)
            for w, (a, z) in windows.items():
                parts[w].append(window_stats(run["V"], dates, a, z))
            if folds is not None:
                fparts.append(fold_returns(run["V"], dates, folds))
            fl.append(run["fills"]); tv.append(run["turnover"]); st.append(run["stale"])
        out[name] = {w: {k: np.concatenate([p[k] for p in ps]) for k in ("cagr", "mdd", "total")}
                     for w, ps in parts.items()}
        out[name]["_fills"] = np.concatenate(fl)
        out[name]["_turnover"] = np.concatenate(tv)
        out[name]["_stale"] = np.concatenate(st)
        if folds is not None:
            out[name]["_folds"] = np.concatenate(fparts, axis=1)
    return out


def dist(x: np.ndarray) -> dict[str, float]:
    return {"median": float(np.median(x)), "mean": float(np.mean(x)), "win_share": float(np.mean(x > 0)),
            "p10": float(np.quantile(x, 0.10)), "p25": float(np.quantile(x, 0.25)),
            "p75": float(np.quantile(x, 0.75)), "p90": float(np.quantile(x, 0.90)), "n": int(len(x))}


# ----------------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------------
JUDGED, CHAMP, CTRL = "B10", "H", "C"
RULES = {"H": ("hold", 0.0), "B10": ("band", JUDGED_BAND), "B5": ("band", NEIGHBOR_BANDS[0]),
         "B15": ("band", NEIGHBOR_BANDS[1]), "C": ("calendar", 0.0)}


def judge(res: dict[float, dict[str, Any]], idx: np.ndarray | None = None, names: list[str] | None = None) -> dict[str, Any]:
    """P1..P7 on the per-basket differences (section 4-2).  P1 also holds with each eligible name left out
    (baskets holding that name dropped) when `idx` is given."""
    r10, r50 = res[10.0], res[50.0]
    d = lambda rr, a, b, w="verdict", k="cagr": rr[a][w][k] - rr[b][w][k]
    g: dict[str, Any] = {}
    x = d(r10, JUDGED, CHAMP)
    p1 = lambda v: bool(len(v) and np.median(v) >= P1_MEDIAN and np.mean(v > 0) >= P1_WIN)
    loo = {}
    if idx is not None:
        for j in range(int(idx.max()) + 1):
            keep = ~(idx == j).any(axis=1)
            nm = names[j] if names else str(j)
            loo[nm] = {"median": float(np.median(x[keep])), "win_share": float(np.mean(x[keep] > 0)), "pass": p1(x[keep])}
    g["P1"] = {"dcagr": dist(x), "leave_one_name_out": loo,
               "pass": bool(p1(x) and all(v["pass"] for v in loo.values())),
               "rule": f"median >= {P1_MEDIAN} and win share >= {P1_WIN}, also with each name left out"}
    y = d(r10, JUDGED, CHAMP, k="mdd")
    g["P2"] = {"dmdd": dist(y), "pass": bool(np.median(y) >= 0.0), "rule": "median MDD(B10) - MDD(H) >= 0"}
    x50 = d(r50, JUDGED, CHAMP)
    g["P3"] = {"dcagr_50bp": dist(x50), "pass": bool(np.median(x50) > 0.0), "rule": "50bp median > 0"}
    nb = {nm: dist(d(r10, nm, CHAMP)) for nm in ("B5", "B15")}
    g["P4"] = {"neighbors": nb, "pass": bool(all(v["median"] > 0.0 for v in nb.values())),
               "rule": "B5 and B15 median > 0 at 10bp"}
    hv = {w: dist(d(r10, JUDGED, CHAMP, w=w)) for w in ("half1", "half2")}
    g["P5"] = {"halves": hv, "pass": bool(all(v["median"] > 0.0 for v in hv.values())),
               "rule": "median > 0 in each half"}
    xc = d(r10, JUDGED, CTRL)
    xc50 = d(r50, JUDGED, CTRL)
    yc = d(r10, JUDGED, CTRL, k="mdd")
    g["P6"] = {"dcagr_vs_C": dist(xc), "dcagr_vs_C_50bp": dist(xc50), "dmdd_vs_C": dist(yc),
               "pass": bool(np.median(xc) > 0.0 and np.mean(xc > 0) >= P6_WIN
                            and np.median(xc50) > 0.0 and np.median(yc) >= 0.0),
               "rule": f"10bp median > 0 and win share >= {P6_WIN}; 50bp median > 0; median MDD(B10) - MDD(C) >= 0"}
    fm = np.median(r10[JUDGED]["_folds"] - r10[CHAMP]["_folds"], axis=1)
    pos = float(np.maximum(fm, 0.0).sum())
    share = float(fm.max() / pos) if pos > 0 else None
    g["P7"] = {"fold_medians": fm, "max_positive_share": share,
               "pass": bool(share is not None and share <= FOLD_SHARE_MAX),
               "rule": f"largest positive fold median <= {FOLD_SHARE_MAX} of the positive sum (no positive fold = fail)"}
    g["verdict"] = verdict_of(g)
    return g


def verdict_of(g: dict[str, Any]) -> str:
    core = all(g[p]["pass"] for p in ("P1", "P2", "P3", "P4", "P5", "P7"))
    if core and g["P6"]["pass"]:
        return "CANDIDATE"
    if core:
        return "REVIEW_ONLY_ALTERNATIVE"
    return "BELOW_STANDARD"


# ----------------------------------------------------------------------------
# causality check
# ----------------------------------------------------------------------------
def causality_check(O, C, ok, idx, cuts: list[int], cost: float, cal: np.ndarray) -> dict[str, Any]:
    """For each cut t: rerun on the closes up to t plus only the next open (close t+1 unknown = NaN);
    values up to t and the state after the fill at t+1's open must equal the full run."""
    fails = []
    for rule, band in (("hold", 0.0), ("band", JUDGED_BAND), ("band", NEIGHBOR_BANDS[0]), ("calendar", 0.0)):
        for t in cuts:
            full = simulate_baskets(O, C, ok, idx, rule, band, cost, cal, snap=t + 1)
            Ct = C[:t + 2].copy()
            Ct[t + 1] = np.nan
            cut = simulate_baskets(O[:t + 2], Ct, ok[:t + 2], idx, rule, band, cost, cal[:t + 2], snap=t + 1)
            same_v = np.allclose(full["V"][:t + 1], cut["V"][:t + 1], rtol=0, atol=1e-12)
            same_s = (np.allclose(full["state"]["H"], cut["state"]["H"], rtol=0, atol=1e-12)
                      and np.allclose(full["state"]["cash"], cut["state"]["cash"], rtol=0, atol=1e-12)
                      and np.array_equal(full["state"]["pending"], cut["state"]["pending"]))
            if not (same_v and same_s):
                fails.append({"rule": rule, "band": band, "cut": int(t)})
    return {"cuts": [int(c) for c in cuts], "passed": not fails, "fails": fails}


# ----------------------------------------------------------------------------
# run
# ----------------------------------------------------------------------------
def load_all(root: Path, man: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    frames, unavailable = {}, {}
    for tk in UNIVERSE:
        ent = man["files"][tk]
        if "unavailable" in ent:
            unavailable[tk] = ent
        else:
            frames[tk] = load_kiwoom(root / ent["path"])
    return frames, unavailable


def run_all(root: Path, out_path: Path) -> int:
    if out_path.exists():
        raise ResultExists(f"STOP: {out_path} exists; this contract runs once and never overwrites")
    contract = check_contract(root)
    check_code(root)
    S4 = s4(root)
    man = check_manifest(root, INPUTS_MANIFEST, contract["fixed_at"])
    frames, unavailable = load_all(root, man)
    inputs = check_inputs(root, man, frames)
    identity = identity_check(root, frames)
    eligible, audit = audit_universe(root, frames, unavailable)
    dates, O, C, ok, provisional = build_market(frames, eligible)
    va, vz = S4.positions(dates, pd.Timestamp(VERDICT[0]), pd.Timestamp(VERDICT[1]))
    if va < 2:
        raise RuntimeError("STOP: the first allocation is not filled before the verdict window")
    windows = {"verdict": (va, vz)}
    for i, (s0, s1) in enumerate(HALVES, 1):
        windows[f"half{i}"] = S4.positions(dates, pd.Timestamp(s0), pd.Timestamp(s1))
    windows["recent"] = S4.positions(dates, pd.Timestamp(RECENT_FROM), dates[-1])
    windows["all"] = (1, len(dates) - 1)
    folds = [S4.positions(dates, f["test_start"], f["test_end"]) for f in S4.make_folds(*VERDICT)]
    cal = year_end_decisions(dates)
    idx4 = np.array(list(itertools.combinations(range(len(eligible)), BASKET)), dtype=np.int64)
    res = {cost: run_rules(O, C, ok, idx4, dates, cost, RULES, cal, windows, folds) for cost in COSTS}
    gates = judge(res, idx4, eligible)

    # S4 metric cross-check on three baskets (first, middle, last) -------------------------
    xcheck = []
    for b in (0, len(idx4) // 2, len(idx4) - 1):
        for name in (JUDGED, CHAMP):
            rule, band = RULES[name]
            run = simulate_baskets(O, C, ok, idx4[b:b + 1], rule, band, 10.0, cal)
            m = S4.slice_metrics({"V": run["V"][:, 0], "trades": [], "W": np.ones(len(dates)), "stale": []},
                                 dates, va, vz, name)
            ws = window_stats(run["V"], dates, va, vz)
            ok_x = abs(m["cagr"] - ws["cagr"][0]) < 1e-12 and abs(m["maximum_drawdown"] - ws["mdd"][0]) < 1e-12
            xcheck.append({"basket": int(b), "rule": name, "s4_cagr": m["cagr"], "cagr": ws["cagr"][0],
                           "s4_mdd": m["maximum_drawdown"], "mdd": ws["mdd"][0], "same": ok_x})
            if not ok_x:
                raise RuntimeError("STOP: engine statistics differ from S4 slice_metrics " + json.dumps(clean(xcheck[-1])))

    # report only ---------------------------------------------------------------------------
    rep: dict[str, Any] = {}
    r10 = res[10.0]
    rep["by_window_10bp"] = {w: {nm: {"cagr": dist(r10[nm][w]["cagr"]), "mdd": dist(r10[nm][w]["mdd"])} for nm in RULES}
                             | {"B10_minus_H_cagr": dist(r10["B10"][w]["cagr"] - r10["H"][w]["cagr"]),
                                "B10_minus_H_mdd": dist(r10["B10"][w]["mdd"] - r10["H"][w]["mdd"]),
                                "B10_minus_C_cagr": dist(r10["B10"][w]["cagr"] - r10["C"][w]["cagr"]),
                                "C_minus_H_cagr": dist(r10["C"][w]["cagr"] - r10["H"][w]["cagr"])}
                             for w in windows}
    rep["fills_full_span_10bp"] = {nm: dist(r10[nm]["_fills"].astype(float)) for nm in RULES}
    rep["turnover_full_span_10bp"] = {nm: dist(r10[nm]["_turnover"]) for nm in RULES}
    rep["stale_sessions_10bp"] = {nm: int(r10[nm]["_stale"].sum()) for nm in RULES}
    per_name = {}
    for j, tk in enumerate(eligible):
        mask = (idx4 == j).any(axis=1)
        per_name[tk] = dist(r10["B10"]["verdict"]["cagr"][mask] - r10["H"]["verdict"]["cagr"][mask])
    rep["dcagr_B10_H_by_member_name"] = per_name
    idx5 = np.array(list(itertools.combinations(range(len(eligible)), 5)), dtype=np.int64)
    r5 = run_rules(O, C, ok, idx5, dates, 10.0, {"H": RULES["H"], "B10": RULES["B10"], "C": RULES["C"]}, cal,
                   {"verdict": (va, vz), "recent": windows["recent"]})
    rep["five_name_baskets_10bp"] = {w: {"B10_minus_H_cagr": dist(r5["B10"][w]["cagr"] - r5["H"][w]["cagr"]),
                                         "B10_minus_H_mdd": dist(r5["B10"][w]["mdd"] - r5["H"][w]["mdd"]),
                                         "B10_minus_C_cagr": dist(r5["B10"][w]["cagr"] - r5["C"][w]["cagr"])}
                                     for w in ("verdict", "recent")}

    # implementation checks on the real data ------------------------------------------------
    step = max(len(idx4) // CAUSALITY_BASKETS, 1)
    cidx = idx4[::step][:CAUSALITY_BASKETS]
    cuts = sorted(set(int(x) for x in np.linspace(va, vz, CAUSALITY_CUTS)) | {len(dates) - 2})   # evenly spaced + the last
    caus = causality_check(O, C, ok, cidx, cuts, 10.0, cal)
    if not caus["passed"]:
        raise RuntimeError("STOP: causality check failed " + json.dumps(caus["fails"][:5]))

    result = {
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "contract": {"path": PREREG, **contract},
        "pinned_code": CODE_PINNED,
        "inputs_manifest": {"path": INPUTS_MANIFEST, "sha256": sha256_file(root / INPUTS_MANIFEST)},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "inputs_check": inputs, "identity_check": identity, "universe_audit": audit,
        "market": {"first": dates[0].date().isoformat(), "last": dates[-1].date().isoformat(),
                   "sessions": len(dates), "provisional_row_dropped": provisional.date().isoformat(),
                   "untradable_opens": {tk: int((~ok[:, j]).sum()) for j, tk in enumerate(eligible)}},
        "design": {"eligible": eligible, "baskets": int(len(idx4)), "basket_size": BASKET, "rules": RULES,
                   "judged": JUDGED, "champion": CHAMP, "control": CTRL, "costs_bps": COSTS,
                   "windows": {w: [dates[a].date().isoformat(), dates[z].date().isoformat()] for w, (a, z) in windows.items()},
                   "folds": len(folds)},
        "gates": gates, "verdict": gates["verdict"],
        "s4_metric_crosscheck": xcheck, "report_only": rep, "causality": caus,
    }
    text = json.dumps(clean(result), ensure_ascii=False, indent=2)
    with open(out_path, "x", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"verdict: {gates['verdict']}  ->  {out_path}")
    return 0


def first_session_after(closures: set[str], when: datetime) -> pd.Timestamp:
    """First audit-calendar session whose 09:30 New York open is after `when`."""
    from zoneinfo import ZoneInfo

    ny = when.astimezone(ZoneInfo("America/New_York"))
    for d in audit_sessions(closures, ny.date().isoformat(), (ny.date() + timedelta(days=15)).isoformat()):
        open_ny = datetime(d.year, d.month, d.day, 9, 30, tzinfo=ZoneInfo("America/New_York"))
        if open_ny > when:
            return d
    raise RuntimeError("STOP (implementation): no session after the lock")


def run_shadow(root: Path, out_path: Path) -> int:
    """Report only: the same rules (H, B10, C, 10bp) on every 4-name combination of the universe names
    whose data are clean in the forward window (first session opening after the lock .. FORWARD_TO).
    Kiwoom fetched on or after SHADOW_FETCH_FROM; identity checked against fresh Nasdaq copies listed in
    the shadow manifest ("identity": {ticker: {"path", "sha256"}}, fetched after FORWARD_TO)."""
    if out_path.exists():
        raise ResultExists(f"STOP: {out_path} exists; the shadow record is written once")
    contract = check_contract(root)
    check_code(root)
    S4 = s4(root)
    man = check_manifest(root, SHADOW_MANIFEST, contract["fixed_at"], after=SHADOW_FETCH_FROM, deadline=None)
    frames, unavailable = load_all(root, man)
    for tk, df in frames.items():
        ent = man["files"][tk]
        if int(ent["rows"]) != len(df) or ent["first"] != df.index[0].date().isoformat() or ent["last"] != df.index[-1].date().isoformat():
            raise RuntimeError(f"STOP: {tk}: shadow manifest rows/first/last differ from the file")
    ident = man.get("identity") or {}
    if sorted(ident) != sorted(frames):
        raise RuntimeError("STOP: the shadow manifest must list one fresh Nasdaq identity copy per fetched name")
    t_from = datetime.fromisoformat(SHADOW_FETCH_FROM)
    for tk, e in ident.items():
        p = root / e["path"]
        if sha256_file(p) != e["sha256"]:
            raise RuntimeError(f"STOP: shadow identity copy {tk}: sha256 differs from the manifest")
        t = datetime.fromisoformat(e["called_kst"])
        if t.tzinfo is None or t < t_from:
            raise RuntimeError(f"STOP: shadow identity copy {tk}: fetched before {SHADOW_FETCH_FROM} or no offset")
        nq_last = load_nasdaq_close(p, tk).index[-1]
        if nq_last < frames[tk].index[-2] - pd.Timedelta(days=7):
            raise RuntimeError(f"STOP: shadow identity copy {tk} ends {nq_last.date()}, before the last Kiwoom sessions")
    identity = {}
    for tk, df in frames.items():
        identity.update(identity_check(root, {tk: df}, {tk: ident[tk]["sha256"]}, str(Path(ident[tk]["path"]).parent)))
    closures = audit_calendar(root)
    check_calendar(closures)
    w0 = first_session_after(closures, datetime.fromisoformat(contract["fixed_at"]))
    w1 = pd.Timestamp(FORWARD_TO)
    sess = audit_sessions(closures, (w0 - pd.Timedelta(days=10)).date().isoformat(), w1.date().isoformat())
    prev = sess[sess < w0][-1]
    sess = sess[sess >= prev]
    names, info = [], {}
    for tk in UNIVERSE:
        if tk not in frames:
            info[tk] = {"used": False, "reason": "unavailable"}
            continue
        df, _ = drop_placeholders(frames[tk])
        body = df.iloc[:-1]
        span = body.loc[(body.index >= prev) & (body.index <= w1)]
        miss, extra = sess.difference(span.index), span.index.difference(sess)
        cl = span["close"].to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = cl[1:] / cl[:-1] - 1.0
        sl = span.index[1:][split_like(r)]
        good = bool(len(span) and span.index[0] == prev and body.index[-1] >= sess[-1]
                    and len(miss) <= MAX_CAL_GAPS and len(extra) <= MAX_CAL_GAPS
                    and np.isfinite(cl).all() and (cl > 0).all() and not len(sl))
        info[tk] = {"used": good, "missing": len(miss), "extra": len(extra), "split_like": [d.date().isoformat() for d in sl]}
        if good:
            names.append(tk)
            frames[tk] = df
    if len(names) < BASKET:
        raise RuntimeError(f"STOP: only {len(names)} clean names in the shadow window")
    dates, O, C, ok, prov = build_market(frames, names, start=prev)
    dates_w = dates[dates <= w1]
    zz = len(dates_w) - 1
    if dates_w[0] != prev or dates_w[-1] != sess[-1]:
        raise RuntimeError("STOP: the shadow market does not span the window")
    a = 1
    cal = year_end_decisions(dates_w)
    idx4 = np.array(list(itertools.combinations(range(len(names)), BASKET)), dtype=np.int64)
    rr = run_rules(O[: zz + 1], C[: zz + 1], ok[: zz + 1], idx4, dates_w, 10.0,
                   {"H": RULES["H"], "B10": RULES["B10"], "C": RULES["C"]}, cal, {"fwd": (a, zz)})
    rep = {"B10_minus_H_total": dist(rr["B10"]["fwd"]["total"] - rr["H"]["fwd"]["total"]),
           "B10_minus_H_mdd": dist(rr["B10"]["fwd"]["mdd"] - rr["H"]["fwd"]["mdd"]),
           "B10_minus_C_total": dist(rr["B10"]["fwd"]["total"] - rr["C"]["fwd"]["total"]),
           "fills": {nm: dist(rr[nm]["_fills"].astype(float)) for nm in ("H", "B10", "C")}}
    result = {"generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"), "contract": contract,
              "window": [dates_w[a].date().isoformat(), dates_w[zz].date().isoformat()],
              "first_decision_close": prev.date().isoformat(), "names": names, "per_ticker": info,
              "identity_check": identity, "unavailable": list(unavailable), "baskets": int(len(idx4)),
              "report_only": rep, "note": "report only; not a verdict"}
    with open(out_path, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(clean(result), ensure_ascii=False, indent=2) + "\n")
    print(f"shadow written -> {out_path}")
    return 0


# ----------------------------------------------------------------------------
# self-test (synthetic and hand-built; no contract, no market data)
# ----------------------------------------------------------------------------
def self_test(root: Path) -> None:
    S4 = s4(root)
    # 1 hand-built 2-name basket, 4 sessions, band 0.10, cost 10bp
    O = np.array([[10.0, 10.0], [10.0, 10.0], [16.0, 10.0], [16.0, 10.0]])
    C = np.array([[10.0, 10.0], [10.0, 10.0], [16.0, 10.0], [16.0, 10.0]])
    ok = np.ones_like(O, dtype=bool)
    idx = np.array([[0, 1]])
    cal = np.zeros(4, dtype=bool)
    r = simulate_baskets(O, C, ok, idx, "band", 0.10, 10.0, cal)
    # t0 decide; t1 fill at open: notional 1.0, cost 0.001 -> V1 = 0.999
    assert abs(r["V"][1, 0] - 0.999) < 1e-12, r["V"][:, 0]
    # t2 open: 0.5*1.6 + 0.5 - 0.001 = 1.299; weight a = 0.8/1.299 = 0.616 -> band decision at t2 close
    assert abs(r["V"][2, 0] - 1.299) < 1e-12
    # t3 open fill: v = 1.299, target 0.6495 each; delta = -0.1505, +0.1495 -> notional 0.300, cost 0.0003
    assert abs(r["V"][3, 0] - (1.299 - 0.0003)) < 1e-12, r["V"][:, 0]
    assert r["fills"][0] == 2
    h = simulate_baskets(O, C, ok, idx, "hold", 0.0, 10.0, cal)
    assert abs(h["V"][3, 0] - 1.299) < 1e-12 and h["fills"][0] == 1
    # 2 invalid open freezes the fill; the name moves close to close
    ok2 = ok.copy(); ok2[1, 1] = False
    r2 = simulate_baskets(O, C, ok2, idx, "hold", 0.0, 0.0, cal)
    assert r2["fills"][0] == 1 and r2["stale"][0] == 1
    assert abs(r2["V"][1, 0] - 1.0) < 1e-12           # still cash at t1
    # 3 calendar rule fills after the last session of a year
    dates = pd.DatetimeIndex(["2019-12-30", "2019-12-31", "2020-01-02", "2020-01-03"])
    calr = year_end_decisions(dates)
    assert calr.tolist() == [False, True, False, False]
    r3 = simulate_baskets(O, C, ok, idx, "calendar", 0.0, 0.0, calr)
    assert r3["fills"][0] == 2                         # first allocation + after 2019-12-31
    # 4 window statistics equal S4 slice_metrics on a synthetic path
    rng = np.random.default_rng(11)
    n, K = 700, 6
    d = pd.bdate_range("2004-12-21", periods=n)
    R = rng.normal(0.0004, 0.02, size=(n, K))
    Cs = 50 * np.cumprod(1 + R, axis=0)
    Os = Cs * (1 + rng.normal(0, 0.004, size=(n, K)))
    oks = np.ones((n, K), dtype=bool)
    oks[200, 2] = False
    idxs = np.array(list(itertools.combinations(range(K), 4)))
    cals = year_end_decisions(d)
    for rule, band in (("hold", 0.0), ("band", 0.10), ("band", 0.05), ("calendar", 0.0)):
        run = simulate_baskets(Os, Cs, oks, idxs, rule, band, 10.0, cals)
        a, z = 30, n - 5
        ws = window_stats(run["V"], d, a, z)
        for b in (0, 7, len(idxs) - 1):
            m = S4.slice_metrics({"V": run["V"][:, b], "trades": [], "W": np.ones(n), "stale": []}, d, a, z, rule)
            assert abs(m["cagr"] - ws["cagr"][b]) < 1e-12 and abs(m["maximum_drawdown"] - ws["mdd"][b]) < 1e-12
        # chunking gives the same answer
        r_one = simulate_baskets(Os, Cs, oks, idxs[3:4], rule, band, 10.0, cals)
        assert np.allclose(r_one["V"][:, 0], run["V"][:, 3], rtol=0, atol=1e-13)
    # 5 causality: the honest engine passes, a peeking engine is caught
    cuts = [100, 250, 400, n - 2]
    assert causality_check(Os, Cs, oks, idxs, cuts, 10.0, cals)["passed"]
    caught = False
    for t in range(50, n - 2, 7):
        full = simulate_baskets(Os, Cs, oks, idxs, "band", 0.05, 10.0, cals, snap=t + 1, peek=True)
        Ct = Cs[:t + 2].copy(); Ct[t + 1] = np.nan
        cut = simulate_baskets(Os[:t + 2], Ct, oks[:t + 2], idxs, "band", 0.05, 10.0, cals[:t + 2], snap=t + 1, peek=True)
        same = (np.allclose(full["V"][:t + 1], cut["V"][:t + 1], rtol=0, atol=1e-12)
                and np.allclose(full["state"]["H"], cut["state"]["H"], rtol=0, atol=1e-12)
                and np.array_equal(full["state"]["pending"], cut["state"]["pending"]))
        if not same:
            caught = True
            break
    assert caught, "peeking engine not caught"
    # 6 split-like detector (price ratio within 0.5% relative of 1/k or k)
    rr = np.array([-0.5, -0.502, -0.48, 1.0, -0.6667, 0.3, -0.75, 9.0, -0.9, -0.504, 9.06])
    assert split_like(rr).tolist() == [True, True, False, True, True, False, True, True, True, False, False]
    # 7 gates and verdict names
    B = 200
    base = lambda: {w: {"cagr": np.zeros(B), "mdd": np.full(B, -0.5), "total": np.zeros(B)}
                    for w in ("verdict", "half1", "half2")} | {"_folds": np.zeros((23, B))}
    res = {c: {nm: base() for nm in RULES} for c in COSTS}
    for c in COSTS:
        for nm in ("B10", "B5", "B15"):
            for w in ("verdict", "half1", "half2"):
                res[c][nm][w]["cagr"] = np.full(B, 0.01)
            res[c][nm]["_folds"] = np.tile(np.linspace(0.001, 0.01, 23)[:, None], (1, B))
    assert judge(res)["verdict"] == "CANDIDATE"
    res[50.0]["C"]["verdict"]["cagr"] = np.full(B, 0.02)                 # P6 also needs 50bp vs C
    assert judge(res)["verdict"] == "REVIEW_ONLY_ALTERNATIVE"
    res[50.0]["C"]["verdict"]["cagr"] = np.zeros(B)
    res[10.0]["C"]["verdict"]["mdd"] = np.full(B, -0.4)                  # ... and MDD not deeper than C
    assert judge(res)["verdict"] == "REVIEW_ONLY_ALTERNATIVE"
    res[10.0]["C"]["verdict"]["mdd"] = np.full(B, -0.5)
    assert judge(res)["verdict"] == "CANDIDATE"
    # leave-one-name-out: all the gain sits in baskets holding name 0 -> P1 fails
    idxt = np.array(list(itertools.combinations(range(8), 4)))[:B] if B <= 70 else np.array(list(itertools.combinations(range(10), 4)))[:B]
    for c in COSTS:
        res[c]["B10"]["verdict"]["cagr"] = np.where((idxt == 0).any(axis=1), 0.03, 0.0)
    assert not judge(res, idxt)["P1"]["pass"]
    for c in COSTS:
        res[c]["B10"]["verdict"]["cagr"] = np.full(B, 0.01)
    assert judge(res, idxt)["P1"]["pass"]
    for c in COSTS:
        res[c]["B10"]["_folds"][:] = 0.0
        res[c]["B10"]["_folds"][5] = 0.05
    assert judge(res)["verdict"] == "BELOW_STANDARD"          # one fold carries everything (P7)
    # 8 audit calendar: independent session counts and known closures
    closures = audit_calendar(root)
    assert check_calendar(closures) == {2005: 252, 2006: 251, 2007: 251, 2008: 253}
    for d0 in ("2005-03-25", "2006-01-02", "2007-01-02", "2008-01-21", "2004-12-24", "2012-10-29"):
        assert d0 in closures, d0
    assert "2005-12-23" not in closures
    # 9 eligibility + audit on synthetic Kiwoom-shaped frames (audit calendar, not the S4 module calendar)
    frames = {}
    for j, tk in enumerate(UNIVERSE):
        start = "2004-12-21" if j < 20 else "2012-01-03"
        dd = audit_sessions(closures, start, "2017-01-03")
        cl = 20 + np.cumsum(rng.normal(0, 0.1, len(dd)))
        cl = np.abs(cl) + 5
        frames[tk] = pd.DataFrame({"open": cl, "high": cl * 1.01, "low": cl * 0.99, "close": cl,
                                   "volume": 1000.0, "adj_code": "", "split": False}, index=dd)
    lead = frames["NVDA"].iloc[:3].copy()
    lead.index = pd.DatetimeIndex(["2004-12-15", "2004-12-16", "2004-12-17"])
    lead[["open", "high", "low", "close"]] = 7.0
    lead["volume"] = 0.0
    frames["NVDA"] = pd.concat([lead, frames["NVDA"]])
    fr = {k: v.copy() for k, v in frames.items()}
    el, au = audit_universe(root, fr, {})
    assert len(el) == 20 and au["placeholders"]["NVDA"]["count"] == 3, (len(el), au["data_lost"])
    fr = {k: v.copy() for k, v in frames.items()}
    fr["AMD"] = fr["AMD"].drop(fr["AMD"].index[[300, 301, 302, 303]])     # 4 gaps -> out for data
    el, au = audit_universe(root, fr, {})
    assert "AMD" not in el and au["data_lost"] == ["AMD"]
    fr = {k: v.copy() for k, v in frames.items()}
    fr["AMD"] = fr["AMD"].drop(fr["AMD"].index[2400:2430])                  # 30-session hole -> data out (counted)
    fr["DELL"] = fr["DELL"].drop(fr["DELL"].index[2400:2430]) if fr["DELL"].index[0] <= pd.Timestamp(ELIGIBLE_BY) else fr["DELL"]
    el, au = audit_universe(root, fr, {})
    assert "AMD" not in el and au["data_lost"] == ["AMD"] and au["per_ticker"]["AMD"]["reason"].startswith("data: a run of 30")
    fr = {k: v.copy() for k, v in frames.items()}
    fr["DELL"] = frames["NVDA"].iloc[3:].copy().drop(frames["NVDA"].index[2403:2433])   # reused ticker -> history out
    el, au = audit_universe(root, fr, {})
    assert "DELL" not in el and au["data_lost"] == [] and au["per_ticker"]["DELL"]["reason"].startswith("history")
    fr = {k: v.copy() for k, v in frames.items()}
    fr["INTC"].iloc[3000, fr["INTC"].columns.get_loc("close")] = np.nan     # bad close after the window
    el, au = audit_universe(root, fr, {})
    assert "INTC" not in el and au["data_lost"] == ["INTC"]
    fr = {k: v.copy() for k, v in frames.items()}
    cmu = fr["MU"]["close"].to_numpy(float).copy()
    cmu[500:] *= 0.5 * cmu[499] / cmu[500]                                    # unadjusted 2:1 split (exact ratio)
    fr["MU"]["close"] = cmu
    try:
        audit_universe(root, fr, {})
        raise AssertionError("split-like move not stopped")
    except RuntimeError as e:
        assert "split-like" in str(e)
    fr = {k: v.copy() for k, v in frames.items()}
    for tk in ("AMD", "MU", "INTC", "TXN", "ADI"):
        fr[tk] = fr[tk].drop(fr[tk].index[[300, 301, 302, 303]])
    try:
        audit_universe(root, fr, {})
        raise AssertionError("too many data losses not stopped")
    except RuntimeError as e:
        assert "lost to data" in str(e)
    # 10 refusals: sidecar, manifest, inputs, identity, overwrite, STOP record
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    (tmp / "docs/claude/s44-inputs/nasdaq-identity").mkdir(parents=True)
    doc = tmp / PREREG
    doc.write_text("contract\n")
    rsha = sha256_file(Path(__file__).resolve())
    dsha = sha256_file(doc)

    def side(*extra: str, fixed: list[str] | None = None, raw: str | None = None) -> None:
        lines = [f"raw_sha256 {raw or dsha}", "lf_sha256 x", f"runner_sha256 {rsha}"]
        lines += [f"fixed_at {f}" for f in (fixed if fixed is not None else ["2026-11-02T22:00:00+09:00"])]
        (tmp / PREREG_SIDECAR).write_text("\n".join(lines + list(extra)) + "\n")

    def refuses(fn, word: str) -> None:
        try:
            fn()
        except (RuntimeError, ValueError, KeyError, ResultExists) as e:
            assert word in str(e), (word, str(e))
            return
        raise AssertionError(f"not refused: {word}")

    side()
    assert check_contract(tmp)["fixed_at"].startswith("2026-11-02T22")
    side(raw="0" * 64); refuses(lambda: check_contract(tmp), "changed after fixation")
    side(fixed=["2026-11-02T22:00:00"]); refuses(lambda: check_contract(tmp), "UTC offset")
    side(fixed=["2026-11-02T22:00:00+09:00", "2026-11-02T23:00:00+09:00"]); refuses(lambda: check_contract(tmp), "exactly one")
    side("amended_at 2026-11-02T21:00:00+09:00"); refuses(lambda: check_contract(tmp), "after the original lock")
    side()
    kdir = tmp / "docs/claude/s44-inputs"
    def kfile(name: str, dates: pd.DatetimeIndex) -> dict[str, Any]:
        rows = [{"dt": d.strftime("%Y%m%d"), "open_pric": "10", "high_pric": "10.5", "low_pric": "9.5", "cur_prc": "10",
                 "acc_trde_qty": "100", "upd_stkpc_tp": ""} for d in dates[::-1]]
        p = kdir / name
        p.write_text(json.dumps({"result": {"return_code": 0, "return_msg": "ok", "result_list": rows}}))
        return {"path": f"docs/claude/s44-inputs/{name}", "sha256": sha256_file(p), "called_kst": "2026-11-03T08:00:00+09:00",
                "rows": len(dates), "first": dates[0].date().isoformat(), "last": dates[-1].date().isoformat()}
    long_d = audit_sessions(closures, "2004-12-21", "2026-10-30")
    files = {tk: kfile(f"{tk}.json", long_d) for tk in UNIVERSE}
    mpath = tmp / INPUTS_MANIFEST
    def man_write(f): mpath.write_text(json.dumps({"files": f}))
    man_write(files)
    m = check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00")
    fr0 = {tk: load_kiwoom(tmp / files[tk]["path"]) for tk in UNIVERSE}
    check_inputs(tmp, m, fr0)
    f2 = json.loads(json.dumps(files)); f2["NVDA"]["called_kst"] = "2026-11-02T21:00:00+09:00"; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "before the contract")
    f2 = json.loads(json.dumps(files)); f2["NVDA"]["called_kst"] = "2026-11-25T08:00:00+09:00"; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "after the deadline")
    f2 = json.loads(json.dumps(files)); f2["NVDA"]["called_kst"] = "2026-11-03T08:00:00"; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "UTC offset")
    f2 = json.loads(json.dumps(files)); f2["NVDA"]["sha256"] = "0" * 64; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "sha256")
    f2 = json.loads(json.dumps(files)); del f2["NVDA"]["rows"]; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "no rows")
    f2 = json.loads(json.dumps(files)); del f2["PLTR"]; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "differ from the universe")
    f2 = json.loads(json.dumps(files)); f2["PLTR"] = {"unavailable": "rc 7"}; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "attempts")
    f2["PLTR"] = {"unavailable": "rc 7", "tried": ["NASDAQ", "NYSE"]}; man_write(f2)
    refuses(lambda: check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00"), "attempts")
    f2["PLTR"] = {"unavailable": "rc 7", "tried": [{"exchange": "NASDAQ", "called_kst": "2026-11-03T08:00:00+09:00", "return_code": 7}]}
    man_write(f2)
    assert "unavailable" in check_manifest(tmp, INPUTS_MANIFEST, "2026-11-02T22:00:00+09:00")["files"]["PLTR"]
    f2 = json.loads(json.dumps(files)); f2["NVDA"]["rows"] = 10; man_write(f2)
    refuses(lambda: check_inputs(tmp, f2 and {"files": f2}, fr0), "rows/first/last")
    # a short late file needs a confirming fetch with the same dates; a row-capped late file is a late fetch
    late = audit_sessions(closures, "2012-01-03", "2026-10-30")
    capped = audit_sessions(closures, "2005-03-01", "2026-10-30")
    capped = audit_sessions(closures, "2004-01-01", "2026-10-30")[-ROW_CAP:] if len(capped) < ROW_CAP else capped[-ROW_CAP:]
    f2 = json.loads(json.dumps(files)); f2["BE"] = kfile("BE.json", late)
    fr2 = dict(fr0); fr2["BE"] = load_kiwoom(tmp / f2["BE"]["path"])
    refuses(lambda: check_inputs(tmp, {"files": f2}, fr2), "without a confirming fetch")
    c_ok = kfile("BE_c.json", late.append(pd.DatetimeIndex(["2026-11-02"])))
    f2["BE"]["confirm"] = {k: c_ok[k] for k in ("path", "sha256", "called_kst")}
    assert check_inputs(tmp, {"files": f2}, fr2)["BE"]["late_start_confirmed"]["newer_rows_ignored"] == 1
    c_bad = kfile("BE_c2.json", late[5:])
    f2["BE"]["confirm"] = {k: c_bad[k] for k in ("path", "sha256", "called_kst")}
    refuses(lambda: check_inputs(tmp, {"files": f2}, fr2), "other dates")
    lc = audit_sessions(closures, "2005-03-01", "2027-03-31")[-ROW_CAP:]
    f3 = json.loads(json.dumps(files)); f3["NVDA"] = kfile("NVDA_cap.json", lc)
    fr3 = dict(fr0); fr3["NVDA"] = load_kiwoom(tmp / f3["NVDA"]["path"])
    assert len(fr3["NVDA"]) == ROW_CAP and fr3["NVDA"].index[0] > pd.Timestamp(ELIGIBLE_BY)
    refuses(lambda: check_inputs(tmp, {"files": f3}, fr3), "fetch was too late")
    # identity: pinned hash, symbol, level
    real = Path(__file__).resolve().parent / "s44-inputs/nasdaq-identity/MU.json"
    if real.exists():
        idp = tmp / IDENTITY_DIR / "MU.json"
        idp.write_bytes(real.read_bytes())
        nq = load_nasdaq_close(idp, "MU")
        kd = nq.index.append(pd.DatetimeIndex(["2026-11-02"]))
        good = pd.DataFrame({"close": list(nq.values) + [1.0], "split": False}, index=kd)
        identity_check(tmp, {"MU": good})
        refuses(lambda: identity_check(tmp, {"MU": good.assign(close=good["close"] * 1.03)}), "identity check failed")
        refuses(lambda: identity_check(tmp, {"MU": good}, {"MU": "0" * 64}), "sha256")
        (tmp / IDENTITY_DIR / "AMD.json").write_bytes(real.read_bytes())
        refuses(lambda: identity_check(tmp, {"AMD": good}, {"AMD": sha256_file(real)}), "not AMD")
    # overwrite refusal and STOP record
    out = tmp / RESULTS_JSON
    out.write_text("{}")
    refuses(lambda: run_all(tmp, out), "never overwrites")
    out.unlink()
    def boom(r, o):
        raise RuntimeError("STOP: synthetic")
    side(fixed=["2026-01-01T00:00:00+09:00"])                                # a lock in the past
    refuses(lambda: guarded(boom, tmp, out, "run"), "synthetic")
    assert len(list((tmp / STOP_DIR).glob("*.json"))) == 1
    refuses(lambda: guarded(boom, tmp, out, "run"), "amend first")
    side(f"amended_at {(datetime.now(KST) + timedelta(seconds=2)).isoformat(timespec='seconds')}",
         fixed=["2026-01-01T00:00:00+09:00"])
    refuses(lambda: guarded(boom, tmp, out, "run"), "synthetic")     # allowed again after an amendment
    def shadow_ok(r, o):
        return 0
    side(fixed=["2026-01-01T00:00:00+09:00"])
    assert guarded(shadow_ok, tmp, out, "shadow") == 0                # a main-run STOP does not block the shadow
    out.write_text("{}")
    n_rec = len(list((tmp / STOP_DIR).glob("*.json")))
    try:
        guarded(run_all, tmp, out, "run2")
        raise AssertionError("rerun not refused")
    except ResultExists:
        pass
    assert len(list((tmp / STOP_DIR).glob("*.json"))) == n_rec        # no STOP record for an existing result
    out.unlink()
    # first session after a lock
    assert first_session_after(closures, datetime.fromisoformat("2026-11-02T22:00:00+09:00")) == pd.Timestamp("2026-11-02")
    assert first_session_after(closures, datetime.fromisoformat("2026-11-03T00:00:00+09:00")) == pd.Timestamp("2026-11-03")
    assert first_session_after(closures, datetime.fromisoformat("2026-11-26T23:00:00+09:00")) == pd.Timestamp("2026-11-27")
    print("self-test passed")


def lock_times(root: Path) -> datetime | None:
    try:
        pairs = [ln.split() for ln in (root / PREREG_SIDECAR).read_text(encoding="utf-8").splitlines() if len(ln.split()) >= 2]
        ts = [datetime.fromisoformat(v) for k, v, *_ in pairs if k in ("fixed_at", "amended_at")]
        return max(ts) if ts else None
    except (OSError, ValueError):
        return None


def guarded(fn, root: Path, out: Path, kind: str) -> int:
    """A STOP (RuntimeError) leaves a record (never overwritten); a new run of the same kind after a STOP
    needs an amendment (a newer amended_at line in the sidecar).  The results-exist refusal leaves none."""
    sd = root / STOP_DIR
    last_lock = lock_times(root)
    for rec in sorted(sd.glob("*.json")) if sd.exists() else []:
        body = json.loads(rec.read_text(encoding="utf-8"))
        if body.get("kind") != kind:
            continue                                     # a main-run STOP never blocks the shadow, and back
        at = datetime.fromisoformat(body["at_kst"])
        if last_lock is None or at > last_lock:
            raise RuntimeError(f"STOP: an earlier STOP ({rec.name}) came after the last lock -- amend first (section 6)")
    try:
        return fn(root, out)
    except RuntimeError as e:
        sd.mkdir(parents=True, exist_ok=True)
        now = datetime.now(KST)
        rec = sd / f"s44-stop-{kind}-{now.strftime('%Y%m%dT%H%M%S%f')}.json"
        with open(rec, "x", encoding="utf-8") as fh:
            fh.write(json.dumps({"at_kst": now.isoformat(), "kind": kind, "message": str(e)}, ensure_ascii=False) + "\n")
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shadow", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    root = args.root.resolve()
    if args.self_test:
        self_test(root)
        return 0
    if args.out is not None:
        raise SystemExit("STOP: --out is not allowed (the contract writes only its own results files)")
    if args.run:
        return guarded(run_all, root, root / RESULTS_JSON, "run")
    if args.shadow:
        return guarded(run_shadow, root, root / SHADOW_JSON, "shadow")
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
