#!/usr/bin/env python3
"""crash-1031 B: pre-registered pre-open gap sell replay for SOXL (2026-10-31).

Rule under test (contract: docs/claude/crash1031-gap-preregistration-2026-10-31.md + its .sha256):
  when the SOXX opening gap  open[t+1] / close[t] - 1  is <= -G, sell one 24/99 slot of the SOXL
  band target at that open (the 27/99 residual is never sold); buy a sold slot back only with the
  08-05 re-entry rule as rule-1028 a-3 (3).  A sell resets re-entry eligibility; no re-entry on a
  close whose next open triggers (even with no slot left).  Judged also against an exposure-matched
  constant band (G8) so that a lower average weight alone cannot pass.

Everything except the trigger, its slot path, the G8 control and the trigger-input audit is reused,
read-only, from the pinned rule-1028 a-3 runner: data load and audit, timing rows, re-entry inputs,
slot multipliers and targets, S4 engine, folds, metrics and gates.  Two module constants of that
runner are set for this contract only (COMMON: drop the provisional 2026-10-08 row; GATE_ROWS:
this contract's judged row).

Historical research only: no broker, no Kiwoom tools, no policy, core or registry writes, no
orders.  Run it in the cloud container, not on the user's PC.  Any STOP writes no result.

  --self-test   synthetic and hand-built checks (no contract needed)
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
A3 = "stock-strategy-system/backtests/rule1028_a3_2026-10-28.py"
A3_SHA = "35207bf554173f894982e31b9f263c91579ba2fb330e2dc299a377ec7a0b9695"
DGS3MO = "stock-strategy-system/backtests/rule1028_a3_inputs_2026-10-28/fred/DGS3MO.csv"
PREREG = "docs/claude/crash1031-gap-preregistration-2026-10-31.md"
PREREG_SIDECAR = "docs/claude/crash1031-gap-preregistration-2026-10-31.sha256"
RESULTS_JSON = "docs/claude/crash1031-gap-results-2026-10-31.json"
KST = timezone(timedelta(hours=9))

# Parameters are fixed by the pre-registration; never edit after seeing a result.
G_BASE = 0.030                      # SOXX opening gap threshold (= the alert line chosen before any result)
G_NEIGHBORS = (0.025, 0.035)
G_REPORT = (0.020, 0.050)           # report only, never judged
COMMON = ("2010-10-18", "2026-10-07")
JUDGE_COST = 50.0                   # G7 and G8: fee 25bp + opening slippage 25bp per traded weight
MIN_CAUSALITY_CUTS = 8
SELL_CUTS_MAX = 10                  # extra causality cuts at the first 10 judged-row sell closes (primary) and the close before
FWD_REPORT = (5, 20)                # h-th session counting the fill session as 1 (index t+h)
AUX_CUT_DATES = ("2014-10-01", "2017-03-01", "2020-03-16")
AUDIT_GAP = 0.020                   # trigger-input audit on every SOXX gap <= -2.0% (the lowest G)
AUDIT_RATIO_TOL = 0.10              # |SOXL gap - 3 x SOXX gap| allowed on those sessions
SI_KEYS = ("below_l", "below_x", "above_l", "above_x", "aligned", "setup")
ROW_KEYS = ("ema10", "ema20", "atr14")


def name_for(g: float) -> str:
    return f"gap_g{int(round(g * 1000)):03d}"


BASE = name_for(G_BASE)
CTRL = f"ctrl_{BASE}"
GATE_ROWS = {BASE: [name_for(g) for g in G_NEIGHBORS]}
REPORT_ROWS = {name_for(g): [] for g in G_REPORT}
ALL_G = (G_BASE, *G_NEIGHBORS, *G_REPORT)

_A3: dict[str, Any] = {}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def a3(root: Path):
    """The pinned a-3 runner, loaded read-only (no bytecode)."""
    if "m" not in _A3:
        got = sha256_file(root / A3)
        if got != A3_SHA:
            raise RuntimeError(f"{A3}: sha256 {got} != pinned {A3_SHA}")
        spec = importlib.util.spec_from_file_location("c1031_a3_runner", root / A3)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {A3}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["c1031_a3_runner"] = mod
        spec.loader.exec_module(mod)
        mod.COMMON = COMMON          # contract 2-1: the provisional last SOXL row (2026-10-08) is left out
        mod.GATE_ROWS = GATE_ROWS    # contract 4-4: a row outside GATE_ROWS is labelled report-only
        _A3["m"] = mod
    return _A3["m"]


# ----------------------------------------------------------------------------
# the new part: gap trigger, slot path, exposure-matched control, trigger-input audit
# ----------------------------------------------------------------------------
def gap_next(x_open: np.ndarray, x_close: np.ndarray, next_open: float | None = None) -> np.ndarray:
    """g[t] = SOXX open[t+1] / close[t] - 1, decided before the t+1 open (pre-market proxy).
    The last session has no next open unless one is supplied (causality check)."""
    n = len(x_close)
    g = np.full(n, np.nan)
    if n > 1:
        g[:-1] = x_open[1:] / x_close[:-1] - 1.0
    if next_open is not None and n:
        g[-1] = next_open / x_close[-1] - 1.0
    return g


def triggered(gap: float, g: float) -> bool:
    # compared in basis points rounded to 1e-6 bp so an exact -G gap from 2-decimal prices is not lost
    return bool(math.isfinite(gap) and round(gap * 1e4, 6) <= -round(g * 1e4, 6))


def slot_path_gap(a: int, gnext: np.ndarray, si: dict[str, np.ndarray], g: float,
                  eligibility_sessions: int) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """k[t] = slots held after the close-t decision (3 before a).  Per close, as a-3 (3) without the
    rearm step: re-entry eligibility -> gap trigger (sell, or 'no slot') -> otherwise re-entry.
    A sell resets eligibility.  Decisions at close t fill at the t+1 open (the gap open)."""
    n = len(gnext)
    k = np.full(n, 3, int)
    if a >= n:
        return k, []
    held, align = 3, 0
    expiry: int | None = None
    events: list[dict[str, Any]] = []
    for t in range(a, n):
        both_above = bool(si["above_l"][t] and si["above_x"][t])
        align = align + 1 if si["aligned"][t] else 0
        if not both_above:
            expiry = None
        elif align >= 2 and expiry is None:
            expiry = t + eligibility_sessions
        if expiry is not None and t > expiry:
            expiry = None
        if triggered(float(gnext[t]), g):
            if held >= 1:
                held -= 1
                align, expiry = 0, None          # a sold slot needs a fresh 2-session alignment (contract 3)
                events.append({"idx": t, "kind": "sell", "soxx_gap_next": float(gnext[t]), "held_after": held})
            else:
                events.append({"idx": t, "kind": "trigger_no_slot", "soxx_gap_next": float(gnext[t])})
        elif held < 3 and expiry is not None and si["setup"][t]:
            held += 1
            align, expiry = 0, None
            events.append({"idx": t, "kind": "reentry", "held_after": held})
        k[t] = held
    return k, events


def build_specs(m, mk, a: int, gnext: np.ndarray, mult: dict[int, float]):
    n = len(mk.dates)
    specs: dict[str, dict[str, Any]] = {"B": {"target": np.full(n, m.CAP), "events": {"count": []}}}
    events: dict[str, list[dict[str, Any]]] = {}
    for g in ALL_G:
        k, ev = slot_path_gap(a, gnext, mk.si, g, m.ELIGIBILITY_SESSIONS)
        tgt, force = m.slot_target(n, a, k, mult, mk.open_ok)
        specs[name_for(g)] = {
            "target": tgt, "force": force, "k": k,
            "events": {"count": [e["idx"] for e in ev if e["kind"] == "reentry"],
                       "secondary": {"sells": [e["idx"] for e in ev if e["kind"] == "sell"],
                                     "triggers_without_slot": [e["idx"] for e in ev if e["kind"] == "trigger_no_slot"]}}}
        events[name_for(g)] = ev
    return specs, events


def exposure_control(cap: float, tgt_c: np.ndarray, a: int, lo: int, hi: int,
                     open_ok: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """G8 control: a constant target at the judged row's time-average target over the window [lo, hi],
    moved there at the first open after the overlay start (forced, kept forced until a tradable open
    fills it) and from then on the same 0.10 band as B.  Before a it is B."""
    n = len(tgt_c)
    level = float(np.mean(tgt_c[lo:hi + 1]))
    tgt = np.full(n, cap)
    tgt[a:] = level
    force = np.zeros(n, bool)
    if a < n:
        force[a] = True
        for t in range(a + 1, n):
            force[t] = bool(force[t - 1] and not open_ok[t])
    return tgt, force, level


def trigger_audit(L: pd.DataFrame, X: pd.DataFrame, start: int, stop_from: int) -> dict[str, Any]:
    """Every decision close t >= start whose next SOXX open gaps <= -AUDIT_GAP, or whose next SOXL open gaps
    <= -3 x AUDIT_GAP: on the gap session s = t+1, low <= open <= high for SOXX and SOXL and
    |SOXL gap - 3 x SOXX gap| <= AUDIT_RATIO_TOL.  A failure with t >= stop_from is a STOP; earlier ones
    (report-only window) are listed.  Split sessions among them are listed only.  No gap session is ever
    excluded from the replay."""
    dates = L.index
    xo, xh, xl, xc = (X[c].to_numpy(float) for c in ("open", "high", "low", "close"))
    lo_, lh, ll, lc = (L[c].to_numpy(float) for c in ("open", "high", "low", "close"))
    xs, ls = X["split"].to_numpy(bool), L["split"].to_numpy(bool)
    gx = gap_next(xo, xc)
    rows: list[dict[str, Any]] = []
    for t in range(start, len(dates) - 1):
        s = t + 1
        soxl_gap = float(lo_[s] / lc[t] - 1.0)
        if not (triggered(float(gx[t]), AUDIT_GAP) or triggered(soxl_gap / 3.0, AUDIT_GAP)):
            continue
        checks = {"soxx_open_in_range": bool(xl[s] <= xo[s] <= xh[s]),
                  "soxl_open_in_range": bool(ll[s] <= lo_[s] <= lh[s]),
                  "soxl_gap_about_3x": bool(abs(soxl_gap - 3.0 * float(gx[t])) <= AUDIT_RATIO_TOL)}
        rows.append({"decision_close": dates[t].date().isoformat(), "gap_session": dates[s].date().isoformat(),
                     "idx": t, "soxx_gap": float(gx[t]), "soxl_gap": soxl_gap, **checks,
                     "split_session_list_only": bool(xs[s] or ls[s]), "ok": all(checks.values())})
    stop = [r for r in rows if not r["ok"] and r["idx"] >= stop_from]
    flagged = [r for r in rows if not r["ok"] and r["idx"] < stop_from]
    return {"threshold": -AUDIT_GAP, "ratio_tolerance": AUDIT_RATIO_TOL,
            "from_decision_close": dates[start].date().isoformat() if start < len(dates) else None,
            "stop_from_decision_close": dates[stop_from].date().isoformat() if stop_from < len(dates) else None,
            "sessions_checked": len(rows), "failed_stop": stop, "flagged_report_only": flagged,
            "split_sessions_list_only": [r for r in rows if r["split_session_list_only"]],
            "passed": not stop}


def trigger_cross_check(L: pd.DataFrame, X: pd.DataFrame, lo: int, hi: int) -> dict[str, Any]:
    """Report only: decision closes in [lo, hi] where the SOXX gap and one third of the SOXL gap disagree on
    whether the judged threshold or a neighbour triggers (how much the result leans on the SOXX open)."""
    dates = L.index
    gx = gap_next(X["open"].to_numpy(float), X["close"].to_numpy(float))
    gl = gap_next(L["open"].to_numpy(float), L["close"].to_numpy(float)) / 3.0
    out: dict[str, Any] = {}
    for g in (G_BASE, *G_NEIGHBORS):
        days = [dates[t].date().isoformat() for t in range(lo, hi + 1)
                if triggered(float(gx[t]), g) != triggered(float(gl[t]), g)]
        out[name_for(g)] = {"disagreements": len(days), "decision_closes": days}
    return out


def drawdown_report(V: np.ndarray, dates: pd.DatetimeIndex, lo: int, hi: int) -> dict[str, Any]:
    """Report only: the deepest drawdown in [lo, hi] (NAV at lo-1 as start), its peak and trough dates and
    whether NAV got back to that peak by hi (a tie in recovery sessions fails G1 - contract 4-4)."""
    x = np.asarray(V[lo - 1:hi + 1], float)
    peak = np.maximum.accumulate(x)
    dd = x / peak - 1.0
    i = int(np.argmin(dd))
    p = int(np.argmax(x[:i + 1]))
    return {"max_drawdown": float(dd[i]), "peak_date": dates[lo - 1 + p].date().isoformat(),
            "trough_date": dates[lo - 1 + i].date().isoformat(),
            "recovered_by_window_end": bool((x[i:] >= x[p] - 1e-12).any())}


# ----------------------------------------------------------------------------
# report-only views (never judged)
# ----------------------------------------------------------------------------
def event_report(ev: list[dict[str, Any]], k: np.ndarray, dates: pd.DatetimeIndex, L: pd.DataFrame,
                 X: pd.DataFrame, lo: int, hi: int) -> dict[str, Any]:
    O_l, C_l = L["open"].to_numpy(float), L["close"].to_numpy(float)
    C_x = X["close"].to_numpy(float)
    n = len(dates)
    rows: list[dict[str, Any]] = []
    stack: list[float | None] = []
    pairs: list[dict[str, Any]] = []
    for e in ev:
        t = e["idx"]
        f = t + 1
        row = {"kind": e["kind"], "decision_close": dates[t].date().isoformat(),
               "fill_open": dates[f].date().isoformat() if f < n else None, "in_window": bool(lo <= t <= hi)}
        if e["kind"] in ("sell", "trigger_no_slot"):
            row["soxx_gap"] = e["soxx_gap_next"]
            if f < n:
                row["soxl_gap"] = O_l[f] / C_l[t] - 1
                row["soxl_open_to_close_fill_day"] = C_l[f] / O_l[f] - 1
                for h in FWD_REPORT:
                    j = t + h                            # h-th session counting the fill session (t+1) as 1
                    row[f"soxl_close_h{h}_vs_fill_open"] = (C_l[j] / O_l[f] - 1) if j < n else None
                    row[f"soxx_close_h{h}_vs_decision_close"] = (C_x[j] / C_x[t] - 1) if j < n else None
            if e["kind"] == "sell":
                stack.append(float(O_l[f]) if f < n else None)
        elif e["kind"] == "reentry":
            sold = stack.pop() if stack else None      # the most recently sold slot is bought back
            if f < n:
                px = float(O_l[f])
                row["reentry_fill_open"] = px
                if sold is not None:
                    row["matched_sell_fill_open"] = sold
                    row["rebuy_vs_sell"] = px / sold - 1
                    pairs.append({"in_window": row["in_window"], "rebuy_vs_sell": px / sold - 1})
        rows.append(row)
    inw = [p["rebuy_vs_sell"] for p in pairs if p["in_window"]]
    return {"forward_definition": "h-th session counting the fill session as 1 (close index t+h)",
            "events": rows,
            "rebuy_pairs_in_window": len(inw),
            "rebuy_higher_than_sell_in_window": sum(1 for x in inw if x > 0),
            "rebuy_vs_sell_median_in_window": float(np.median(inw)) if inw else None,
            "open_slots_at_window_end": int(3 - k[hi]),
            "open_slots_after_last_decision": int(3 - k[-1])}   # includes a decision at the last close not yet filled


def gap_day_census(X: pd.DataFrame, lo: int, hi: int) -> dict[str, Any]:
    """How many decision closes in the window had a next SOXX opening gap at or below each threshold."""
    gx = gap_next(X["open"].to_numpy(float), X["close"].to_numpy(float))
    sel = gx[lo:hi + 1]
    return {name_for(g): int(sum(triggered(float(v), g) for v in sel)) for g in ALL_G}


# ----------------------------------------------------------------------------
# contract, causality, run
# ----------------------------------------------------------------------------
def check_contract(root: Path) -> dict[str, str]:
    side = (root / PREREG_SIDECAR).read_text(encoding="utf-8")
    field = {ln.split()[0]: ln.split()[1] for ln in side.splitlines() if len(ln.split()) >= 2}
    doc = (root / PREREG).read_bytes()
    got = hashlib.sha256(doc).hexdigest()
    if field.get("raw_sha256") != got:
        raise RuntimeError("STOP: pre-registration changed after fixation (sidecar mismatch)")
    runner = sha256_file(Path(__file__).resolve())
    if field.get("runner_sha256") != runner:
        raise RuntimeError("STOP: runner changed after fixation (sidecar runner_sha256 mismatch)")
    return {"raw_sha256": got, "lf_sha256": hashlib.sha256(doc.replace(b"\r\n", b"\n")).hexdigest(),
            "runner_sha256": runner, "fixed_at": field.get("fixed_at")}


def row_arrays(rows: list[dict[str, Any] | None]) -> dict[str, np.ndarray]:
    n = len(rows)
    out = {key: np.full(n, np.nan) for key in ROW_KEYS}
    for t, r in enumerate(rows):
        if r is not None:
            for key in ROW_KEYS:
                out[key][t] = float(r[key])
    return out


def same(x: np.ndarray, y: np.ndarray) -> bool:
    x, y = np.asarray(x, float), np.asarray(y, float)
    return bool(x.shape == y.shape and np.allclose(x, y, rtol=1e-12, atol=1e-12, equal_nan=True))


def path_bundle(root: Path, m, L: pd.DataFrame, X: pd.DataFrame, a: int, early: set[str],
                next_open: float | None, leak: bool = False) -> dict[str, np.ndarray]:
    """Everything a decision at close t may use: rows up to t and, for the gap, the t+1 open only.
    leak=True swaps the next open for the next close (self-test: the check must catch it)."""
    dates = L.index
    n = len(dates)
    out: dict[str, np.ndarray] = {}
    if leak:
        cx = X["close"].to_numpy(float)
        gx = np.full(n, np.nan)
        gx[:-1] = cx[1:] / cx[:-1] - 1.0
    else:
        gx = gap_next(X["open"].to_numpy(float), X["close"].to_numpy(float), next_open)
    out["gap"] = np.nan_to_num(gx, nan=-9e9)
    if a < n:
        rows_l, rows_x = m.feature_rows(root, L, a), m.feature_rows(root, X, a)
        out |= {f"l_{key}": v for key, v in row_arrays(rows_l).items()}
        out |= {f"x_{key}": v for key, v in row_arrays(rows_x).items()}
        vol_bad = m.volume_fail_closed(dates, L["split"].to_numpy(bool), early)
        si = m.slot_inputs(root, rows_l, rows_x, vol_bad, a)
        for key in SI_KEYS:
            out[key] = si[key]
        for g in ALL_G:
            out[f"k_{name_for(g)}"], _ = slot_path_gap(a, gx, si, g, m.ELIGIBILITY_SESSIONS)
    return out


def causality_check(root: Path, m, L: pd.DataFrame, X: pd.DataFrame, a: int, cuts: list[int],
                    leak: bool = False, expect: dict[str, np.ndarray] | None = None) -> dict[str, Any]:
    """Recompute everything from the data cut after each close (plus the next open only) and compare with
    the full-history computation; with `expect`, the full computation must also equal the arrays the run
    actually used (from the overlay start a on)."""
    early = m.s4(root).early_closes()
    full = path_bundle(root, m, L, X, a, early, None, leak)
    bad: list[str] = []
    if expect is not None:
        for key, ref in expect.items():
            arr = full.get(key)
            if arr is None or not same(arr[a:], ref[a:]):
                bad.append(f"{key}:differs_from_run_arrays")
    xo = X["open"].to_numpy(float)
    for cut in cuts:
        nxt = float(xo[cut + 1]) if cut + 1 < len(xo) else None
        part = path_bundle(root, m, L.iloc[:cut + 1], X.iloc[:cut + 1], a, early, nxt, leak)
        for key, ref in full.items():
            arr = part.get(key)
            if arr is None:
                bad.append(f"{key}@{L.index[cut].date()}:missing")
            elif not same(arr, ref[:cut + 1]):
                bad.append(f"{key}@{L.index[cut].date()}")
    return {"cuts": [L.index[c].date().isoformat() for c in cuts], "keys": sorted(full),
            "tied_to_run_arrays": expect is not None, "mismatches": bad, "passed": not bad}


def prefix_replay(path_fn: Callable, a: int, gx: np.ndarray, si: dict[str, np.ndarray], g: float,
                  eligibility_sessions: int) -> list[int]:
    """Re-run the slot path on every prefix ending at close c (its gap entry is the c+1 open, known before
    that open) and return the closes where the prefix path differs from the full path on [a, c]."""
    k_full, _ = path_fn(a, gx, si, g, eligibility_sessions)
    bad: list[int] = []
    for c in range(a, len(gx)):
        k_c, _ = path_fn(a, gx[:c + 1], {key: v[:c + 1] for key, v in si.items()}, g, eligibility_sessions)
        if not np.array_equal(k_c[a:], k_full[a:c + 1]):
            bad.append(c)
    return bad


def run_all(root: Path, out_path: Path) -> int:
    if out_path.exists():
        raise RuntimeError(f"STOP: {out_path} exists; this contract runs once and never overwrites")
    m = a3(root)
    contract = check_contract(root)
    m.check_code(root)
    for rel, want in m.DATA_PINNED.items():
        got = sha256_file(root / rel)
        if got != want:
            raise RuntimeError(f"STOP: {rel}: sha256 {got} != pinned {want}")
    if sha256_file(root / DGS3MO) != m.FRED_SHA["DGS3MO"]:
        raise RuntimeError("STOP: DGS3MO differs from the a-3 pin")
    S4 = m.s4(root)
    E = m.ELIGIBILITY_SESSIONS
    soxl, soxx = m.load_kiwoom(root / m.SOXL_JSON), m.load_kiwoom(root / m.SOXX_JSON)
    dgs = m.load_fred(root / DGS3MO, "DGS3MO")
    L, X, audit = m.audit_and_align(root, soxl, soxx)
    dates = L.index
    n = len(dates)
    if dates[-1] != pd.Timestamp(COMMON[1]):
        raise RuntimeError(f"STOP: common range ends {dates[-1].date()} not {COMMON[1]}")
    a_p = int(dates.searchsorted(pd.Timestamp(m.PRIMARY[0]), side="left"))
    a_x = int(dates.searchsorted(pd.Timestamp(m.AUX1[0]), side="left"))
    t_audit = trigger_audit(L, X, min(a_p, a_x), a_p)
    if not t_audit["passed"]:
        raise RuntimeError("STOP: trigger-input audit failed " + json.dumps(m.clean(t_audit["failed_stop"][:5])))
    mk = m.Market(root, L, X, dgs.dropna(), row_start=min(a_p, a_x))
    wf_m, mult = m.wf(root), m.slot_mult(root)
    soxx_close = pd.DataFrame({"close": soxx["close"]})
    gx = gap_next(X["open"].to_numpy(float), X["close"].to_numpy(float))
    run_rows = {f"l_{key}": v for key, v in row_arrays(mk.rows_l).items()} | \
               {f"x_{key}": v for key, v in row_arrays(mk.rows_x).items()}
    result: dict[str, Any] = {
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "contract": {"path": PREREG, **contract},
        "reused_runner": {"path": A3, "sha256": A3_SHA, "constants_set": {"COMMON": list(COMMON),
                                                                          "GATE_ROWS": GATE_ROWS}},
        "pinned_code": m.CODE_PINNED,
        "pinned_inputs": m.DATA_PINNED | {DGS3MO: m.FRED_SHA["DGS3MO"]},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "data_audit": audit | {"tradable_open_all_sessions": bool(mk.open_ok.all()),
                               "volume_fail_closed_sessions_from_row_start": int(mk.vol_bad[mk.row_start:].sum())},
        "trigger_input_audit": t_audit,
        "slot_multipliers": mult,
        "parameters": {"G_BASE": G_BASE, "G_NEIGHBORS": G_NEIGHBORS, "G_REPORT": G_REPORT,
                       "JUDGE_COST_bps": JUDGE_COST, "costs_bps": m.COSTS, "band": m.BAND, "cap": m.CAP,
                       "control": CTRL},
        "authority": {"order_authority": False, "quantity_authority": "none", "execution_quantity": None},
    }
    windows: dict[str, Any] = {}
    replay: dict[str, Any] = {}
    sell_cuts: list[int] = []
    expect: dict[str, dict[str, np.ndarray]] = {}
    for label, window, full, a in (("primary", m.PRIMARY, True, a_p), ("aux_2013_2021_report_only", m.AUX1, False, a_x)):
        lo, hi = S4.positions(dates, pd.Timestamp(window[0]), pd.Timestamp(window[1]))
        if lo != a:
            raise RuntimeError(f"STOP: overlay start {a} != window start {lo}")
        specs, ev = build_specs(m, mk, a, gx, mult)
        ctgt, cforce, level = exposure_control(m.CAP, specs[BASE]["target"], a, lo, hi, mk.open_ok)
        specs[CTRL] = {"target": ctgt, "force": cforce, "events": {"count": []}}
        w = m.evaluate_window(mk, wf_m, soxx_close, window, specs, GATE_ROWS | REPORT_ROWS, full)
        runs10 = w.pop("_runs10")
        same0 = {name: bool(np.allclose(r["V"][:a + 1], runs10["B"]["V"][:a + 1], rtol=0, atol=1e-12))
                 for name, r in runs10.items()}
        if not all(same0.values()):
            raise RuntimeError(f"STOP: a path differs from B before the overlay start: {same0}")
        w["overlay_start"] = dates[a].date().isoformat()
        w["identity_before_overlay"] = same0
        w["exposure_control"] = {
            "name": CTRL, "level": level,
            "mean_target_in_window": {nm: float(np.mean(specs[nm]["target"][lo:hi + 1])) for nm in ("B", BASE, CTRL)},
            "mean_realized_weight_in_window": {nm: float(np.mean(runs10[nm]["W"][lo:hi + 1])) for nm in ("B", BASE, CTRL)}}
        t10 = w["totals_10bp"]
        if full:
            t50 = w["totals_stress"][str(JUDGE_COST)]
            for name, gate in w["gates"].items():
                g7 = S4.g1_g2(t50[name], t50["B"])
                gate["G7_50bp_G1"], gate["G7_50bp_G2"] = g7["G1"], g7["G2"]
                gate["G7"] = bool(g7["G1"] and g7["G2"])
                gate["verdict_a3_engine"] = gate["verdict"]
                if name in GATE_ROWS:
                    c10, c50 = S4.g1_g2(t10[name], t10[CTRL]), S4.g1_g2(t50[name], t50[CTRL])
                    gate["G8_vs_control_10bp"], gate["G8_vs_control_50bp"] = c10, c50
                    gate["G8"] = bool(c10["G1"] and c10["G2"] and c50["G1"] and c50["G2"])
                    sells = sum(1 for i in specs[name]["events"]["secondary"]["sells"] if lo <= i and i + 1 <= hi)
                    gate["sells_filled_in_window"] = sells
                    core = bool(gate["G1_to_G5_all_pass"] and gate["G7"])
                    gate["verdict"] = ("no_sells_no_evidence" if sells == 0 else
                                       "candidate" if core and gate["G8"] and gate["G6"] else
                                       "review_only_exposure_explained" if core and not gate["G8"] else
                                       "review_only_insufficient_observations" if core else
                                       "gate_failed")
            first = [i for i in specs[BASE]["events"]["secondary"]["sells"] if lo <= i <= hi][:SELL_CUTS_MAX]
            sell_cuts = sorted({c for i in first for c in (i - 1, i) if a <= c <= n - 2})
        else:
            w["G8_reference_vs_control_10bp_report_only"] = S4.g1_g2(t10[BASE], t10[CTRL])
        w["drawdown_report_only"] = {nm: drawdown_report(runs10[nm]["V"], dates, lo, hi)
                                     for nm in ("B", BASE, CTRL, *(name_for(g) for g in G_NEIGHBORS))}
        w["trigger_cross_check_report_only"] = trigger_cross_check(L, X, lo, hi)
        w["gap_day_census_report_only"] = gap_day_census(X, lo, hi)
        w["slot_events_report_only"] = {name: event_report(e, specs[name]["k"], dates, L, X, lo, hi)
                                        for name, e in ev.items()}
        w["reentry_inputs_report_only"] = {"aligned_sessions": int(mk.si["aligned"][a:].sum()),
                                           "setup_sessions": int(mk.si["setup"][a:].sum()),
                                           "volume_fail_closed_sessions": int(mk.vol_bad[a:].sum())}
        rp = {name_for(g): prefix_replay(slot_path_gap, a, gx, mk.si, g, E) for g in ALL_G}
        replay[label] = {name: {"closes": n - a, "mismatches": [dates[c].date().isoformat() for c in bad[:20]],
                                "passed": not bad} for name, bad in rp.items()}
        if any(rp.values()):
            raise RuntimeError(f"STOP: slot path prefix replay failed in {label}")
        expect[label] = {"gap": np.nan_to_num(gx, nan=-9e9), **{key: mk.si[key] for key in SI_KEYS}, **run_rows,
                         **{f"k_{name}": specs[name]["k"] for name in ev}}
        windows[label] = w
    result["windows"] = windows
    fixed_p = sorted(set(int(x) for x in np.linspace(a_p + 30, n - 2, 6)))
    cuts_x = sorted(set(int(dates.searchsorted(pd.Timestamp(d))) for d in AUX_CUT_DATES))
    if len(fixed_p) + len(cuts_x) < MIN_CAUSALITY_CUTS:
        raise RuntimeError("STOP: too few causality cuts")
    cuts_p = sorted(set(fixed_p) | set(sell_cuts))
    cp = causality_check(root, m, L, X, a_p, cuts_p, expect=expect["primary"])
    cx = causality_check(root, m, L, X, a_x, cuts_x, expect=expect["aux_2013_2021_report_only"])
    result["causality_real"] = {"primary": cp | {"sell_cuts": len(sell_cuts)}, "aux": cx,
                                "prefix_replay": replay, "passed": bool(cp["passed"] and cx["passed"])}
    if not result["causality_real"]["passed"]:
        raise RuntimeError(f"STOP: causality check failed {cp['mismatches'][:5]} {cx['mismatches'][:5]}")
    payload = json.dumps(m.clean(result), ensure_ascii=False, indent=1)     # serialise before touching the file
    with open(out_path, "x", encoding="utf-8") as fh:          # "x": never overwrite
        fh.write(payload)
    g = windows["primary"]["gates"]
    print(json.dumps({"status": "written", "path": str(out_path),
                      "verdicts": {k: v["verdict"] for k, v in g.items()}}, ensure_ascii=False))
    return 0


# ----------------------------------------------------------------------------
# self-test
# ----------------------------------------------------------------------------
def self_test(root: Path) -> None:
    m = a3(root)
    m.check_code(root)
    E = m.ELIGIBILITY_SESSIONS
    assert E == 10
    mult = m.slot_mult(root)
    assert math.isclose(mult[3], 1.0) and math.isclose(mult[0], 27 / 99)
    assert name_for(0.03) == "gap_g030" and name_for(0.025) == "gap_g025" and CTRL == "ctrl_gap_g030"
    assert list(GATE_ROWS) == [BASE] and str(JUDGE_COST) == "50.0"

    # 1. trigger boundary: exactly -3.00% triggers, -2.99% does not (prices with 2 decimals)
    assert triggered(97.00 / 100.00 - 1, 0.03) and not triggered(97.01 / 100.00 - 1, 0.03)
    assert not triggered(float("nan"), 0.03)

    def hand(n, above=(), aligned=(), setup=()):
        si = {k: np.zeros(n, bool) for k in SI_KEYS}
        for key, idx in (("above_l", above), ("above_x", above), ("aligned", aligned), ("setup", setup)):
            si[key][list(idx)] = True
        return si

    n = 30
    gn = np.zeros(n)
    gn[-1] = np.nan
    # 2. one gap -> sell at that close (fills next open); re-entry after 2 aligned closes + setup
    g1 = gn.copy(); g1[5] = -0.04
    k, ev = slot_path_gap(2, g1, hand(n, above=range(8, 20), aligned=(8, 9), setup=(11,)), 0.03, E)
    assert list(k[:5]) == [3] * 5 and k[5] == 2 and k[10] == 2 and k[11] == 3, k
    assert [e["kind"] for e in ev] == ["sell", "reentry"]
    tgt, force = m.slot_target(n, 2, k, mult, np.ones(n, bool))
    assert force[5] and force[11] and not force[6] and math.isclose(tgt[5], m.CAP * mult[2])
    # 3. consecutive gaps sell slot by slot; the residual is never sold
    g2 = gn.copy(); g2[[4, 5, 6, 7]] = -0.05
    k, ev = slot_path_gap(0, g2, hand(n), 0.03, E)
    assert list(k[3:9]) == [3, 2, 1, 0, 0, 0], k
    assert [e["kind"] for e in ev] == ["sell", "sell", "sell", "trigger_no_slot"]
    # 4. gap and setup on the same close -> the sell wins; the sell wipes the older eligibility
    g3 = gn.copy(); g3[3] = -0.04; g3[10] = -0.04
    k, ev = slot_path_gap(0, g3, hand(n, above=range(6, 20), aligned=(6, 7), setup=(10, 11)), 0.03, E)
    assert k[3] == 2 and k[10] == 1 and k[11] == 1, k
    #    a fresh 2-session alignment after the sell is needed before a re-entry
    k, ev = slot_path_gap(0, g3, hand(n, above=range(6, 20), aligned=(6, 7, 11, 12), setup=(10, 11, 12)), 0.03, E)
    assert k[10] == 1 and k[11] == 1 and k[12] == 2, k
    # 4b. a trigger with no slot left blocks re-entry on that close only (eligibility is kept)
    g6 = gn.copy(); g6[[2, 3, 4, 12]] = -0.05
    k, ev = slot_path_gap(0, g6, hand(n, above=range(5, 25), aligned=(8, 9), setup=(12, 13)), 0.03, E)
    assert list(k[2:5]) == [2, 1, 0] and k[12] == 0 and k[13] == 1, k
    assert [e["kind"] for e in ev] == ["sell", "sell", "sell", "trigger_no_slot", "reentry"]
    # 5. eligibility expires after 10 sessions and vanishes on a close not above EMA20
    g4 = gn.copy(); g4[2] = -0.04
    k, _ = slot_path_gap(0, g4, hand(n, above=range(3, 28), aligned=(3, 4), setup=(15,)), 0.03, E)
    assert k[15] == 2, k                       # eligible from 4 to 14 only
    k, _ = slot_path_gap(0, g4, hand(n, above=[3, 4, 5, 7, 8], aligned=(3, 4), setup=(7,)), 0.03, E)
    assert k[7] == 2, k                        # close 6 not above EMA20 -> eligibility gone
    # 6. no trigger without a next open; nothing before the overlay start
    g5 = gn.copy(); g5[1] = -0.09
    k, ev = slot_path_gap(2, g5, hand(n), 0.03, E)
    assert (k == 3).all() and not ev

    # 7. synthetic market: engine timing, identity before overlay, control, audit, causality and leaks
    L, X, fred = m.synthetic(root)
    xo = X["open"].to_numpy(float).copy()
    xc = X["close"].to_numpy(float)
    gaps = (520, 530, 560, 900, 1100)
    for i in gaps:
        xo[i] = xc[i - 1] * 0.95                    # -5% SOXX opening gaps
    X = X.assign(open=xo, high=np.maximum(X["high"].to_numpy(float), xo), low=np.minimum(X["low"].to_numpy(float), xo))
    dates = L.index
    N = len(dates)
    a = 400
    # 7a. trigger-input audit: SOXX-only gaps (SOXL did not gap) are caught; consistent 3x gaps pass;
    #     a SOXL-only gap (stale SOXX open) is audited and caught; a split session on a gap day is listed
    #     only; failures before stop_from are only listed; the cross-check lists SOXX vs SOXL/3 disagreements
    bad = trigger_audit(L, X, a, a)
    assert not bad["passed"] and len(bad["failed_stop"]) == len(gaps), bad["failed_stop"]
    assert all(not r["soxl_gap_about_3x"] for r in bad["failed_stop"])
    part = trigger_audit(L, X, a, 600)
    assert len(part["flagged_report_only"]) == 3 and len(part["failed_stop"]) == 2
    assert trigger_cross_check(L, X, a, N - 2)[BASE]["disagreements"] == len(gaps)
    lo_ = L["open"].to_numpy(float).copy()
    lc_ = L["close"].to_numpy(float)
    for i in gaps:
        lo_[i] = lc_[i - 1] * 0.85
    L = L.assign(open=lo_, high=np.maximum(L["high"].to_numpy(float), lo_), low=np.minimum(L["low"].to_numpy(float), lo_))
    good = trigger_audit(L, X, a, a)
    assert good["passed"] and good["sessions_checked"] == len(gaps), good
    assert trigger_cross_check(L, X, a, N - 2)[BASE]["disagreements"] == 0
    Ls = L.copy()
    Ls.iloc[560, Ls.columns.get_loc("split")] = True
    sp = trigger_audit(Ls, X, a, a)
    assert sp["passed"] and [r["gap_session"] for r in sp["split_sessions_list_only"]] == [dates[560].date().isoformat()]
    lo2 = L["open"].to_numpy(float).copy()
    lo2[700] = lc_[699] * 0.85                       # SOXL gaps -15%, the SOXX open stays normal
    Lx = L.assign(open=lo2, low=np.minimum(L["low"].to_numpy(float), lo2))
    stale = trigger_audit(Lx, X, a, a)
    assert not stale["passed"] and [r["idx"] for r in stale["failed_stop"]] == [699], stale["failed_stop"]
    # 7a'. drawdown report: peak, trough and recovery flag on a hand path
    dv = np.array([1.0, 1.1, 1.2, 0.9, 1.0, 1.25, 1.1])
    dr = drawdown_report(dv, pd.date_range("2020-01-01", periods=7), 1, 6)
    assert math.isclose(dr["max_drawdown"], 0.9 / 1.2 - 1) and dr["peak_date"] == "2020-01-03"
    assert dr["trough_date"] == "2020-01-04" and dr["recovered_by_window_end"]
    assert not drawdown_report(dv[:5], pd.date_range("2020-01-01", periods=5), 1, 4)["recovered_by_window_end"]
    # 7b. engine timing and identity before the overlay
    mk = m.Market(root, L, X, fred["DGS3MO"], row_start=a)
    gx = gap_next(X["open"].to_numpy(float), X["close"].to_numpy(float))
    specs, ev = build_specs(m, mk, a, gx, mult)
    sells = specs[BASE]["events"]["secondary"]["sells"]
    assert 519 in sells and 529 in sells, sells       # decided at the close before each gap open
    rb = mk.run(specs["B"]["target"], 10.0)
    rc = mk.run(specs[BASE]["target"], 10.0, True, specs[BASE]["force"])
    assert np.allclose(rb["V"][:520], rc["V"][:520], rtol=0, atol=1e-12)   # same until the first gap close
    assert rc["W"][520] < rb["W"][520] - 0.05, (rc["W"][520], rb["W"][520])  # reduced at the 520 open
    tr = [t for t in rc["trades"] if t["idx"] == 520]
    assert tr and tr[0]["delta"] < 0
    # 7c. exposure-matched control: constant at the window mean of the judged target, moved at the a+1 open
    ctgt, cforce, level = exposure_control(m.CAP, specs[BASE]["target"], a, a, N - 1, mk.open_ok)
    assert math.isclose(level, float(np.mean(specs[BASE]["target"][a:]))) and level < m.CAP - 0.01
    assert (ctgt[:a] == m.CAP).all() and np.allclose(ctgt[a:], level) and cforce[a] and not cforce[a + 1:].any()
    rk = mk.run(ctgt, 10.0, True, cforce)
    assert np.allclose(rb["V"][:a + 1], rk["V"][:a + 1], rtol=0, atol=1e-12)
    trk = [t for t in rk["trades"] if t["idx"] == a + 1]
    assert trk and math.isclose(trk[0]["target"], level)
    # 7d. event report bookkeeping: open slots = 3 - k at the window end and at the data end
    er = event_report(ev[BASE], specs[BASE]["k"], dates, L, X, a, 1000)
    assert er["open_slots_at_window_end"] == 3 - specs[BASE]["k"][1000]
    assert er["open_slots_after_last_decision"] == 3 - specs[BASE]["k"][-1]
    # 7e. path-level causality: every prefix replays the same path; a one-session peek is caught
    E_ = m.ELIGIBILITY_SESSIONS
    assert prefix_replay(slot_path_gap, a, gx, mk.si, G_BASE, E_) == []

    def peek_path(a_, gnext, si, g, e_):              # decides at close t with the gap of the t+2 open
        return slot_path_gap(a_, np.r_[gnext[1:], np.nan], si, g, e_)

    caught = prefix_replay(peek_path, a, gx, mk.si, G_BASE, E_)
    assert caught, "a one-session-ahead peek in the slot path was not caught"
    # 7f. data-level causality at fixed cuts and around sells, tied to the arrays the run used
    run_rows = {f"l_{key}": v for key, v in row_arrays(mk.rows_l).items()} | \
               {f"x_{key}": v for key, v in row_arrays(mk.rows_x).items()}
    exp = {"gap": np.nan_to_num(gx, nan=-9e9), **{key: mk.si[key] for key in SI_KEYS}, **run_rows,
           **{f"k_{name}": specs[name]["k"] for name in ev}}
    cuts = sorted({450, 700, 1000, N - 2} | {c for i in sells[:SELL_CUTS_MAX] for c in (i - 1, i)})
    assert len(cuts) >= MIN_CAUSALITY_CUTS
    ok = causality_check(root, m, L, X, a, cuts, expect=exp)
    assert ok["passed"], ok["mismatches"][:10]
    assert {"l_ema20", "x_atr14", "setup", f"k_{BASE}"} <= set(ok["keys"])
    wrong = dict(exp)
    wrong[f"k_{BASE}"] = specs[BASE]["k"].copy()
    wrong[f"k_{BASE}"][N - 5] = (wrong[f"k_{BASE}"][N - 5] + 1) % 4     # one changed slot count
    tied = causality_check(root, m, L, X, a, [], expect=wrong)
    assert not tied["passed"] and tied["mismatches"] == [f"k_{BASE}:differs_from_run_arrays"], tied
    leak = causality_check(root, m, L, X, a, [519, 529, 899], leak=True)
    assert not leak["passed"], "a next-close leak was not caught"
    print(json.dumps({"status": "passed", "slot_multipliers": mult, "synthetic_sells_g030": len(sells),
                      "synthetic_reentries_g030": len(specs[BASE]["events"]["count"]),
                      "control_level": level, "causality_cuts": len(cuts), "peek_caught_at": len(caught),
                      "leak_mismatches": len(leak["mismatches"])}))


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
