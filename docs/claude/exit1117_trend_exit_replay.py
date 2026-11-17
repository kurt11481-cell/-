#!/usr/bin/env python3
"""exit-1117 pre-registered replay: per-stock trend exit and recovery re-entry against hold.

Contract: docs/claude/exit1117-preregistration-2026-11-17.md (+ .sha256 sidecar). This file is part of the
contract: the sidecar pins its sha256 and the run refuses when either changed after the lock.

Question (user decision 2026-11-17 08:37:57 KST, card option 'test first'): for a single stock held in the
core, does "sell all when the system's two downtrend price cues are both on at the close (C3- trend break
and C5- new low, auto_core_rules.py definitions) and buy back when C3+ trend recover is on", decided at the
regular-session close and executed at the next open, do better than
  H  hold (Champion: price alone never sells), and
  F  a fixed mix with the same time-average exposure as the rule (rebalanced once a year)?

Lines per stock: H, T (lookback L = 20, the system constant), neighbours T16 and T24, and F for each T.
Judged on the distribution over the 18 names the s44v2 audit kept (pinned), window 2005-02-05..2016-08-04.
Everything after 2016-08-04, the names BE and LITE, the structural variants and 0% cash interest are
report only.

Reads: pinned Kiwoom daily files fetched 2026-11-02 for s44v2 (no new query), the pinned s44v2 results
(eligible list, identity check already done on the same files), pinned DGS3MO (cash interest) and the pinned
auto_core_rules.py (cross-check of the copied cue definitions). Writes one results JSON, once.

No order, quantity or price authority. Display and research only (order_authority=false).

  --self-test   synthetic data only (run before the lock)
  --run         the one real run (fixed output path; refuses when the results file exists)
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import math
import platform
import statistics
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
KST = timezone(timedelta(hours=9))

PREREG = "docs/claude/exit1117-preregistration-2026-11-17.md"
PREREG_SIDECAR = "docs/claude/exit1117-preregistration-2026-11-17.sha256"
RESULTS_JSON = "docs/claude/exit1117-results.json"
STOP_DIR = "docs/claude/exit1117-stops"

PINS = {
    "manifest": ("docs/claude/s44v2-inputs/inputs-manifest.json",
                 "e104ba245d9ff9a8828e827cba4708e5cb244d66581a2fac6132a76c3657e9da"),
    "s44v2_results": ("docs/claude/s44v2-results.json",
                      "26455e253e4abaf011db91de0371d2a263b35a49ee3c6dda04ce99a34092854d"),
    "dgs3mo": ("stock-strategy-system/backtests/rule1028_a3_inputs_2026-10-28/fred/DGS3MO.csv",
               "739d4ce160fb4f294837e2573d29b5f9a0f4e4642f15e100d841870849c8230a"),
    "core_rules": ("manage-us-stock-strategy/scripts/auto_core_rules.py",
                   "ba979d234ea95644c6bb78456e8f500974060ab96c23f8dafe97281acaa4ea6a"),
}

# The 18 names the s44v2 audit kept (history from 2005-01-31 or earlier, clean calendar, no split-like move).
ELIGIBLE = ("AMD", "MRVL", "MU", "INTC", "QCOM", "TXN", "ADI", "MCHP", "AMAT", "LRCX", "KLAC", "TER",
            "MPWR", "WDC", "STX", "TSM", "ASML", "ORCL")
REPORT_EXTRA = ("BE", "LITE")          # the two names the question is about: too short for the judged window
AUDIT_FROM = "2004-12-01"              # rows before this date are dropped (s44v2 rule, kept)
VERDICT = ("2005-02-05", "2016-08-04")
HALVES = (("2005-02-05", "2010-08-04"), ("2010-08-05", "2016-08-04"))
RECENT = ("2016-08-05", "2099-12-31")  # already explored (S5 C.2, Yahoo 2016-10..2026-09): report only
RECENT5 = ("2021-08-05", "2099-12-31")
L_MAIN = 20                            # auto_core_rules CONSTANTS: EMA_MID 20, LOOKBACK_SESSIONS 20, EMA_SHORT 10
NEIGHBOURS = (16, 24)                  # every 20-session constant scaled together; short EMA = L // 2
HOLD = 2                               # two-session hold of C3 and C5 (rule file, not varied)
COSTS = (10.0, 50.0)                   # bp per traded value; 50 = the user's real fee 25bp + 25bp slippage
YEAR = 252.0
SPLIT_RATIOS = (2, 3, 4, 5, 10)
SPLIT_LIKE_TOL = 0.005
FLOAT_EQUAL = 1e-9                     # the core's representation tolerance (auto_core_rules.FLOAT_EQUAL)

# Gates (section 4-2 of the contract). Per stock against hold, the S4 precedent formulas
# (walk_forward_soxl_signals_2026-10-01.py g1_g2) without the recovery-session condition, with a 1e-12
# allowance on (b) that the precedent does not have, and without Calmar when hold's CAGR is not positive:
MDD_IMPROVE = 0.05        # (a) maximum drawdown at least 5 points shallower than H
CAGR_KEEP = 0.10          # (b) CAGR(T) >= 0.9 x CAGR(H) when CAGR(H) > 0, else CAGR(T) >= CAGR(H)
CALMAR_GAIN = 0.10        # (c) Calmar(T) >= Calmar(H) + 10% x |Calmar(H)| when CAGR(H) > 0, else (b) again
P1_SHARE = 0.60
P2_WIN_SHARE = 0.60
P3_SHARE = 0.50
P4_SHARE = 0.50
P6_ROUND_TRIPS = 10
FOLD_SHARE_MAX = 0.50


class Stop(RuntimeError):
    """Data, contract or implementation check failed: no results file is written."""


class ResultExists(Exception):
    """The results file is already there: refused without a STOP record."""


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return obj


def check_contract(root: Path, runner: Path | None = None, prereg: str = PREREG,
                   sidecar: str = PREREG_SIDECAR) -> dict[str, Any]:
    """Sidecar lines: raw_sha256, runner_sha256, fixed_at (exactly once) and optional amended_at lines."""
    for rel in (prereg, sidecar):
        if not (root / rel).is_file():
            raise Stop(f"STOP: contract file missing: {rel}")
    side = (root / sidecar).read_text(encoding="utf-8")
    pairs = [(ln.split()[0], ln.split()[1]) for ln in side.splitlines() if len(ln.split()) >= 2]
    field = dict(pairs)
    got = hashlib.sha256((root / prereg).read_bytes()).hexdigest()
    if field.get("raw_sha256") != got:
        raise Stop("STOP: pre-registration changed after the lock (sidecar raw_sha256 mismatch)")
    rsha = sha256_file(Path(__file__).resolve() if runner is None else runner)
    if field.get("runner_sha256") != rsha:
        raise Stop("STOP: runner changed after the lock (sidecar runner_sha256 mismatch)")
    fixed = [v for k, v in pairs if k == "fixed_at"]
    if len(fixed) != 1:
        raise Stop("STOP: sidecar must hold exactly one fixed_at")
    amended = [v for k, v in pairs if k == "amended_at"]
    for t in [fixed[0], *amended]:
        try:
            aware = datetime.fromisoformat(t).tzinfo is not None
        except ValueError:
            raise Stop(f"STOP: sidecar time not ISO 8601: {t}") from None
        if not aware:
            raise Stop("STOP: sidecar times need a UTC offset")
    if any(datetime.fromisoformat(t) <= datetime.fromisoformat(fixed[0]) for t in amended):
        raise Stop("STOP: an amendment must come after the original lock")
    return {"raw_sha256": got, "runner_sha256": rsha, "fixed_at": fixed[0], "amended_at": amended}


def check_pins(root: Path, pins: dict[str, tuple[str, str]]) -> dict[str, Any]:
    out = {}
    for key, (rel, want) in pins.items():
        path = root / rel
        if not path.exists():
            raise Stop(f"STOP: pinned file missing: {rel}")
        got = sha256_file(path)
        if got != want:
            raise Stop(f"STOP: {rel}: sha256 {got} != pinned {want}")
        out[key] = {"path": rel, "sha256": got}
    return out


# ----------------------------------------------------------------------------------------------
# inputs
# ----------------------------------------------------------------------------------------------
def load_kiwoom(path: Path) -> pd.DataFrame:
    """Same reading as s44v2_rebalance_replay.load_kiwoom (usa06012 daily, adjusted=1)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["result"]["return_code"] != 0:
        raise Stop(f"STOP: {path.name}: return_code != 0")
    recs = [{"date": pd.Timestamp(r["dt"]), "open": float(r["open_pric"]), "high": float(r["high_pric"]),
             "low": float(r["low_pric"]), "close": float(r["cur_prc"]), "volume": float(r["acc_trde_qty"])}
            for r in payload["result"]["result_list"]]
    df = pd.DataFrame(recs).set_index("date").sort_index()
    if df.index.has_duplicates:
        raise Stop(f"STOP: {path.name}: duplicate dates")
    return df


def prepare(df: pd.DataFrame, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Leading placeholder rows out, rows before AUDIT_FROM out, last (provisional) row out."""
    flat = ((df["volume"].to_numpy(float) <= 0) & (df["open"] == df["close"]).to_numpy()
            & (df["high"] == df["close"]).to_numpy() & (df["low"] == df["close"]).to_numpy())
    k0 = int(np.argmin(flat)) if not flat.all() else len(df)
    body = df.iloc[k0:]
    before = int((body.index < pd.Timestamp(AUDIT_FROM)).sum())
    body = body[body.index >= pd.Timestamp(AUDIT_FROM)]
    if len(body) < 3 * L_MAIN:
        raise Stop(f"STOP: {name}: too few rows after the audit start")
    provisional = body.index[-1].date().isoformat()
    body = body.iloc[:-1]
    close = [float(x) for x in body["close"]]
    if not all(math.isfinite(x) and x > 0 for x in close):
        raise Stop(f"STOP: {name}: close not finite and positive")
    op = [float(x) for x in body["open"]]
    vol = [float(x) for x in body["volume"]]
    ok = [math.isfinite(o) and o > 0 and v > 0 for o, v in zip(op, vol)]
    ratio = [close[i] / close[i - 1] for i in range(1, len(close))]
    split_like = [body.index[i + 1].date().isoformat() for i, r in enumerate(ratio)
                  if any(abs(r / k - 1) <= SPLIT_LIKE_TOL or abs(r * k - 1) <= SPLIT_LIKE_TOL for k in SPLIT_RATIOS)]
    series = {"name": name, "dates": list(body.index), "open": op, "close": close, "ok": ok,
              "high": [float(x) for x in body["high"]], "low": [float(x) for x in body["low"]], "volume": vol}
    info = {"placeholders_dropped": k0, "rows_before_audit_from": before, "provisional_row_dropped": provisional,
            "first": body.index[0].date().isoformat(), "last": body.index[-1].date().isoformat(),
            "rows": len(body), "untradable_opens": int(sum(1 for x in ok if not x)), "split_like": split_like}
    return series, info


def load_rates(path: Path) -> tuple[list[pd.Timestamp], list[float]]:
    days, vals = [], []
    for ln in path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = ln.strip().split(",")
        if len(parts) != 2 or parts[1] in ("", "."):
            continue
        days.append(pd.Timestamp(parts[0]))
        vals.append(float(parts[1]))
    if not days or days != sorted(days):
        raise Stop("STOP: DGS3MO series empty or unsorted")
    return days, vals


def session_rates(dates: list[pd.Timestamp], rates: tuple[list[pd.Timestamp], list[float]], zero: bool = False
                  ) -> list[float]:
    """Cash interest of one session: the last DGS3MO observation dated before the session, / 100 / 252."""
    if zero:
        return [0.0] * len(dates)
    days, vals = rates
    out = []
    for d in dates:
        k = bisect.bisect_left(days, d) - 1
        if k < 0:
            raise Stop("STOP: no DGS3MO observation before the first session")
        out.append(vals[k] / 100.0 / YEAR)
    return out


# ----------------------------------------------------------------------------------------------
# cue definitions, copied from auto_core_rules.py (cross-checked against the pinned file)
# ----------------------------------------------------------------------------------------------
def _all(*values: bool | None) -> bool | None:
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def _cmp(left: float | None, op: str, right: float | None) -> bool | None:
    if left is None or right is None:
        return None
    return {"ge": left >= right - FLOAT_EQUAL, "le": left <= right + FLOAT_EQUAL,
            "gt": left > right + FLOAT_EQUAL, "lt": left < right - FLOAT_EQUAL}[op]


def _at(values: list[Any], index: int) -> Any:
    return values[index] if 0 <= index < len(values) else None


def ema_series(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1)
    current = math.fsum(values[:period]) / period
    out[period - 1] = current
    for index in range(period, len(values)):
        current = alpha * values[index] + (1 - alpha) * current
        out[index] = current
    return out


def _runs(flags: list[bool | None]) -> list[int | None]:
    out: list[int | None] = []
    run: int | None = 0
    for flag in flags:
        if flag is None:
            run = None
        elif flag:
            run = None if run is None else run + 1
        else:
            run = 0
        out.append(run)
    return out


def _hold_state(close: list[float], ema_short: list[float | None], line_series: list[float | None],
                side: str) -> list[str | None]:
    op = "lt" if side == "-" else "gt"
    out: list[str | None] = []
    state, line = "none", None
    for i in range(len(close)):
        if state in ("pending", "hit") and line is not None:
            holds = _all(_cmp(close[i], op, line), _cmp(close[i], op, ema_short[i]))
            if holds is None:
                out.append(None)
                state, line = "none", None
                continue
            if holds:
                state = "hit"
                out.append("hit")
                continue
            crossed = _cmp(close[i], "gt" if side == "-" else "lt", line)
            state, line = "none", None
            if crossed:
                out.append("fail")
                continue
        start = _all(_cmp(close[i], op, line_series[i]), _cmp(close[i], op, ema_short[i]))
        if start is None:
            out.append(None)
        elif start:
            state, line = "pending", line_series[i]
            out.append("pending")
        else:
            out.append("none")
    return out


def signals(close: list[float], lookback: int) -> dict[str, list[Any]]:
    """C3-, C3+ (two closes beyond the mid EMA, the close before the run on the other side) and C5-, C5+
    (close beyond the prior `lookback`-session close line and the short EMA, held two sessions)."""
    n, short = len(close), lookback // 2
    e_mid, e_short = ema_series(close, lookback), ema_series(close, short)
    hi = [None if i < lookback else max(close[i - lookback:i]) for i in range(n)]
    lo = [None if i < lookback else min(close[i - lookback:i]) for i in range(n)]
    below = [_cmp(close[i], "lt", e_mid[i]) for i in range(n)]
    above = [_cmp(close[i], "gt", e_mid[i]) for i in range(n)]
    below_run, above_run = _runs(below), _runs(above)
    c3m: list[bool | None] = []
    c3p: list[bool | None] = []
    for i in range(n):
        for runs, other, out in ((below_run, above, c3m), (above_run, below, c3p)):
            run = runs[i]
            if run is None:
                out.append(None)
            elif run < HOLD:
                out.append(False)
            else:
                out.append(_at(other, i - run))
    return {"C3-": c3m, "C3+": c3p, "C5-": _hold_state(close, e_short, lo, "-"),
            "C5+": _hold_state(close, e_short, hi, "+")}


def rule_flags(sig: dict[str, list[Any]], variant: str = "T") -> tuple[list[bool], list[bool]]:
    """Exit / re-entry flags at each close. T: exit C3- and C5- hit, re-entry C3+.
    Report-only variants: E1 exit C3- alone; E2 re-entry C3+ and C5+ hit."""
    n = len(sig["C3-"])
    if variant == "E1":
        exit_ = [sig["C3-"][i] is True for i in range(n)]
    else:
        exit_ = [sig["C3-"][i] is True and sig["C5-"][i] == "hit" for i in range(n)]
    if variant == "E2":
        entry = [sig["C3+"][i] is True and sig["C5+"][i] == "hit" for i in range(n)]
    else:
        entry = [sig["C3+"][i] is True for i in range(n)]
    return exit_, entry


# ----------------------------------------------------------------------------------------------
# engines
# ----------------------------------------------------------------------------------------------
def simulate_t(op: list[float], close: list[float], ok: list[bool], rate: list[float], exit_: list[bool],
               entry: list[bool], cost_bp: float) -> dict[str, Any]:
    """Continuous run from the first row: fully in the stock at close[0] (value 1, no entry cost).
    Session order: pending order at the open (kept while the open is not tradable) -> cash interest ->
    value at the close -> decision at the close."""
    c = cost_bp / 10000.0
    n = len(close)
    shares, cash = 1.0 / close[0], 0.0
    pending: str | None = None
    value, held = [1.0] + [0.0] * (n - 1), [True] + [False] * (n - 1)
    trades: list[tuple[str, int, float]] = []
    if exit_[0]:
        pending = "sell"
    for t in range(1, n):
        if pending is not None and ok[t]:
            if pending == "sell":
                cash += shares * op[t] * (1.0 - c)
                shares = 0.0
            else:
                shares = cash * (1.0 - c) / op[t]
                cash = 0.0
            trades.append((pending, t, op[t]))
            pending = None
        cash *= 1.0 + rate[t]
        value[t] = shares * close[t] + cash
        held[t] = shares > 0.0
        if pending is None:
            if shares > 0.0 and exit_[t]:
                pending = "sell"
            elif shares == 0.0 and entry[t]:
                pending = "buy"
    return {"value": value, "held": held, "trades": trades, "pending_end": pending}


def simulate_f(op: list[float], close: list[float], ok: list[bool], rate: list[float],
               dates: list[pd.Timestamp], a: int, z: int, w: float, cost_bp: float) -> list[float]:
    """Fixed mix inside [a, z]: value 1 at close[a-1] with the stock at weight w (no entry cost, as for the
    other lines). Back to w at the first tradable open of each calendar year, cost on the traded value."""
    c = cost_bp / 10000.0
    stock, cash = w, 1.0 - w
    value = [float("nan")] * len(close)
    value[a - 1] = 1.0
    due = False
    for t in range(a, z + 1):
        stock_open = stock * op[t] / close[t - 1] if ok[t] else stock
        if dates[t].year != dates[t - 1].year:
            due = True
        if due and ok[t]:
            total = stock_open + cash
            delta = w * total - stock_open
            cash = total - w * total - c * abs(delta)
            stock_open = w * total
            due = False
        cash *= 1.0 + rate[t]
        stock = stock_open * close[t] / op[t] if ok[t] else stock * close[t] / close[t - 1]
        value[t] = stock + cash
    return value


def window(dates: list[pd.Timestamp], start: str, end: str) -> tuple[int, int] | None:
    a = bisect.bisect_left(dates, pd.Timestamp(start))
    z = bisect.bisect_right(dates, pd.Timestamp(end)) - 1
    if a < 1 or z < a:
        return None
    return a, z


def metrics(value: list[float], a: int, z: int) -> dict[str, float | None]:
    base = value[a - 1]
    n = z - a + 1
    cagr = (value[z] / base) ** (YEAR / n) - 1.0
    peak, mdd = base, 0.0
    for t in range(a, z + 1):
        peak = max(peak, value[t])
        mdd = min(mdd, value[t] / peak - 1.0)
    return {"cagr": cagr, "mdd": mdd, "calmar": (cagr / abs(mdd)) if mdd < 0 else None, "sessions": n,
            "total": value[z] / base - 1.0}


def make_folds(start: str, end: str) -> list[tuple[str, str]]:
    """Six-month folds from the window start (02-05 / 08-05 boundaries), the last one ending at `end`."""
    out, cur, last = [], pd.Timestamp(start), pd.Timestamp(end)
    while cur <= last:
        nxt = cur + pd.DateOffset(months=6)
        out.append((cur.date().isoformat(), min(nxt - pd.Timedelta(days=1), last).date().isoformat()))
        cur = nxt
    return out


def run_stock(series: dict[str, Any], rate: list[float], cost_bp: float, lookback: int, variant: str,
              win: tuple[str, str], with_folds: bool = False) -> dict[str, Any] | None:
    """H, T and F of one stock in one window (T sliced from its continuous run)."""
    dates, op, close, ok = series["dates"], series["open"], series["close"], series["ok"]
    idx = window(dates, *win)
    if idx is None:
        return None
    a, z = idx
    exit_, entry = rule_flags(signals(close, lookback), variant)
    t = simulate_t(op, close, ok, rate, exit_, entry, cost_bp)
    held = t["held"][a:z + 1]
    w = sum(1 for x in held if x) / len(held)
    f_value = simulate_f(op, close, ok, rate, dates, a, z, w, cost_bp)
    h_value = [x / close[a - 1] for x in close]
    sells = [(i, p) for kind, i, p in t["trades"] if kind == "sell" and a <= i <= z]
    buys = [(i, p) for kind, i, p in t["trades"] if kind == "buy" and a <= i <= z]
    pairs = []
    for i, p in buys:                       # a buy paired with the latest sell before it inside the window
        prev = [q for j, q in sells if j < i]
        if prev:
            pairs.append(p / prev[-1])
    out = {"window": [dates[a].date().isoformat(), dates[z].date().isoformat()], "avg_exposure": w,
           "H": metrics(h_value, a, z), "T": metrics(t["value"], a, z), "F": metrics(f_value, a, z),
           "sells": len(sells), "buys": len(buys), "round_trips": len(pairs),
           "rebuy_higher_share": (sum(1 for r in pairs if r > 1.0) / len(pairs)) if pairs else None,
           "rebuy_ratio_median": statistics.median(pairs) if pairs else None,
           "held_at_end": bool(t["held"][z])}
    if with_folds:
        rows = []
        for fs, fe in make_folds(*win):
            fi = window(dates, fs, fe)
            if fi is None:
                raise Stop(f"STOP: {series['name']}: fold {fs} has no sessions")
            fa, fz = fi
            rows.append({"fold": fs, "T": t["value"][fz] / t["value"][fa - 1] - 1.0,
                         "F": f_value[fz] / f_value[fa - 1] - 1.0, "H": close[fz] / close[fa - 1] - 1.0})
        out["folds"] = rows
    return out


# ----------------------------------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------------------------------
def pass_h(r: dict[str, Any]) -> bool:
    """One stock against hold: (a) drawdown, (b) return kept, (c) Calmar.
    When hold's CAGR is not positive a Calmar comparison runs backwards (a shallower drawdown makes a
    negative Calmar look worse), so (b) and (c) both become CAGR(T) >= CAGR(H).
    Every comparison has a 1e-12 allowance for representation error."""
    t, h = r["T"], r["H"]
    a = t["mdd"] - h["mdd"] >= MDD_IMPROVE - 1e-12
    if h["cagr"] > 0:
        b = t["cagr"] >= (1.0 - CAGR_KEEP) * h["cagr"] - 1e-12
        c = (t["calmar"] is not None and h["calmar"] is not None
             and t["calmar"] >= h["calmar"] + CALMAR_GAIN * abs(h["calmar"]) - 1e-12)
    else:
        b = t["cagr"] >= h["cagr"] - 1e-12
        c = b
    return bool(a and b and c)


def spread(rows: dict[str, dict[str, Any]], key: str, other: str) -> dict[str, Any]:
    d = [rows[n]["T"][key] - rows[n][other][key] for n in rows]
    return {"median": statistics.median(d), "mean": statistics.fmean(d), "min": min(d), "max": max(d),
            "positive_share": sum(1 for x in d if x > 0) / len(d), "count": len(d)}


def judge(res: dict[str, Any]) -> dict[str, Any]:
    """res[(L, cost)] = {name: run_stock(...)} on the judged window; res['halves'][k] at 10bp, main L."""
    main10, main50 = res[(L_MAIN, 10.0)], res[(L_MAIN, 50.0)]
    n = len(main10)
    g: dict[str, Any] = {}
    share10 = sum(1 for r in main10.values() if pass_h(r)) / n
    g["P1"] = {"pass": share10 >= P1_SHARE, "share_pass_vs_hold": share10, "need": P1_SHARE,
               "names_pass": [k for k, r in main10.items() if pass_h(r)]}
    c10, m10 = spread(main10, "cagr", "F"), spread(main10, "mdd", "F")
    g["P2"] = {"pass": c10["median"] > 0 and c10["positive_share"] >= P2_WIN_SHARE and m10["median"] >= 0,
               "cagr_T_minus_F": c10, "mdd_T_minus_F": m10, "need_win_share": P2_WIN_SHARE}
    share50 = sum(1 for r in main50.values() if pass_h(r)) / n
    c50 = spread(main50, "cagr", "F")
    g["P3"] = {"pass": share50 >= P3_SHARE and c50["median"] > 0, "pass_vs_hold": share50 >= P3_SHARE,
               "pass_vs_mix": c50["median"] > 0, "share_pass_vs_hold": share50, "cagr_T_minus_F": c50,
               "need": P3_SHARE}
    neigh = {}
    for lb in NEIGHBOURS:
        rows = res[(lb, 10.0)]
        sh = sum(1 for r in rows.values() if pass_h(r)) / n
        cf = spread(rows, "cagr", "F")
        neigh[str(lb)] = {"pass": sh >= P4_SHARE and cf["median"] > 0, "pass_vs_hold": sh >= P4_SHARE,
                          "pass_vs_mix": cf["median"] > 0, "share_pass_vs_hold": sh, "cagr_T_minus_F": cf}
    g["P4"] = {"pass": all(v["pass"] for v in neigh.values()),
               "pass_vs_hold": all(v["pass_vs_hold"] for v in neigh.values()),
               "pass_vs_mix": all(v["pass_vs_mix"] for v in neigh.values()), "neighbours": neigh, "need": P4_SHARE}
    halves = {k: spread(rows, "cagr", "F") for k, rows in res["halves"].items()}
    g["P5"] = {"pass": all(v["median"] > 0 for v in halves.values()), "halves_cagr_T_minus_F": halves}
    trips = statistics.median([r["round_trips"] for r in main10.values()])
    g["P6"] = {"pass": trips >= P6_ROUND_TRIPS, "round_trips_median": trips, "need": P6_ROUND_TRIPS}
    names = list(main10)
    k_folds = len(main10[names[0]]["folds"])
    fold_med = [statistics.median([main10[nm]["folds"][k]["T"] - main10[nm]["folds"][k]["F"] for nm in names])
                for k in range(k_folds)]
    pos = [x for x in fold_med if x > 0]
    top = (max(pos) / sum(pos)) if pos else None
    g["P7"] = {"pass": top is not None and top <= FOLD_SHARE_MAX, "top_fold_share": top,
               "fold_median_T_minus_F": fold_med, "need": FOLD_SHARE_MAX}
    return g


def verdict_of(g: dict[str, Any]) -> str:
    """CANDIDATE: every gate. REVIEW_ONLY_EXPOSURE: every hold-side condition (P1, the hold part of P3 and P4)
    and the sample gate P6 pass, so whatever failed is a fixed-mix condition (P2, the mix part of P3 / P4,
    P5, P7). BELOW_STANDARD: the rest."""
    if all(g[k]["pass"] for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7")):
        return "CANDIDATE"
    if g["P1"]["pass"] and g["P3"]["pass_vs_hold"] and g["P4"]["pass_vs_hold"] and g["P6"]["pass"]:
        return "REVIEW_ONLY_EXPOSURE"
    return "BELOW_STANDARD"


# ----------------------------------------------------------------------------------------------
# checks on the implementation
# ----------------------------------------------------------------------------------------------
def load_core(path: Path):
    """The pinned auto_core_rules.py with a stub for its portfolio_exposure import (sigma is not used here)."""
    stub = types.ModuleType("portfolio_exposure")
    stub._sample_std = lambda values: None
    saved = sys.modules.get("portfolio_exposure")
    sys.modules["portfolio_exposure"] = stub
    try:
        spec = importlib.util.spec_from_file_location("exit1117_core_rules", path)
        if spec is None or spec.loader is None:
            raise Stop(f"STOP: cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["exit1117_core_rules"] = module
        spec.loader.exec_module(module)
    finally:
        if saved is None:
            sys.modules.pop("portfolio_exposure", None)
        else:
            sys.modules["portfolio_exposure"] = saved
    return module


def core_cross_check(core, close: list[float], high: list[float], low: list[float], volume: list[float]) -> int:
    """This file's C3 / C5 at L = 20 against raw_common of the pinned core, every index. Returns the count."""
    n, lb = len(close), 20
    ret1 = [None] + [close[i] / close[i - 1] - 1 for i in range(1, n)]
    ret5 = [None if i < 5 else close[i] / close[i - 5] - 1 for i in range(n)]
    series = {
        "close": close, "high": high, "low": low, "volume": volume, "ret1": ret1, "ret5": ret5,
        "hi20": [None if i < lb else max(close[i - lb:i]) for i in range(n)],
        "lo20": [None if i < lb else min(close[i - lb:i]) for i in range(n)],
        "avgv20": [None if i < lb else math.fsum(volume[i - lb:i]) / lb for i in range(n)],
        "position": [0.5 if high[i] == low[i] else (close[i] - low[i]) / (high[i] - low[i]) for i in range(n)],
        "ema10": core.ema_series(close, 10), "ema20": core.ema_series(close, 20),
        "ema50": core.ema_series(close, 50), "rsi14": core.rsi_series(close, 14),
        "atr14": core.atr_series(high, low, close, 14),
    }
    raw = core.raw_common(series, {"one_day": None, "five_day": None})
    mine = signals(close, 20)
    for key in ("C3-", "C3+", "C5-", "C5+"):
        if list(raw[key]) != list(mine[key]):
            bad = next(i for i in range(n) if raw[key][i] != mine[key][i])
            raise Stop(f"STOP: {key} differs from the pinned core at index {bad}")
    return n


def truncation_check(series: dict[str, Any], rate: list[float], cuts: list[int], lookback: int,
                     flags=None) -> int:
    """No look-ahead: the flags and the T run on the first cut + 1 rows equal the full run up to the cut
    (flags at every index, value and held at the cut). `flags(close)` is replaced only by the self-test."""
    if flags is None:
        flags = lambda c: rule_flags(signals(c, lookback))      # noqa: E731
    op, close, ok = series["open"], series["close"], series["ok"]
    exit_, entry = flags(close)
    full = simulate_t(op, close, ok, rate, exit_, entry, 10.0)
    for cut in cuts:
        e2, n2 = flags(close[:cut + 1])
        if e2 != exit_[:cut + 1] or n2 != entry[:cut + 1]:
            raise Stop(f"STOP: {series['name']}: signals change when later rows are removed (cut {cut})")
        part = simulate_t(op[:cut + 1], close[:cut + 1], ok[:cut + 1], rate[:cut + 1], e2, n2, 10.0)
        if abs(part["value"][cut] - full["value"][cut]) > 1e-12 or part["held"][cut] != full["held"][cut]:
            raise Stop(f"STOP: {series['name']}: truncated run differs at cut {cut}")
    return len(cuts)


# ----------------------------------------------------------------------------------------------
# the run
# ----------------------------------------------------------------------------------------------
def compute(root: Path, pins: dict[str, tuple[str, str]], contract: dict[str, Any]) -> dict[str, Any]:
    pinned = check_pins(root, pins)
    man = json.loads((root / pins["manifest"][0]).read_text(encoding="utf-8"))
    prior = json.loads((root / pins["s44v2_results"][0]).read_text(encoding="utf-8"))
    if prior["inputs_manifest"]["sha256"] != pins["manifest"][1]:
        raise Stop("STOP: the s44v2 results were not computed on the pinned manifest")
    if sorted(prior["universe_audit"]["eligible"]) != sorted(ELIGIBLE):
        raise Stop("STOP: eligible names differ from the pinned s44v2 audit")
    rates = load_rates(root / pins["dgs3mo"][0])
    core = load_core(root / pins["core_rules"][0])

    series: dict[str, dict[str, Any]] = {}
    inputs: dict[str, Any] = {}
    skipped: dict[str, str] = {}
    for name in (*ELIGIBLE, *REPORT_EXTRA):
        ent = man["files"][name]
        path = root / ent["path"]
        got = sha256_file(path)
        if got != ent["sha256"]:
            raise Stop(f"STOP: {name}: sha256 {got} != manifest {ent['sha256']}")
        if name in ELIGIBLE and prior["identity_check"][name]["passed"] is not True:
            raise Stop(f"STOP: {name}: no passed identity check in the pinned s44v2 results")
        try:
            ser, info = prepare(load_kiwoom(path), name)
        except Stop as exc:
            if name in ELIGIBLE:
                raise
            skipped[name] = f"data check failed, report only name left out: {exc}"
            inputs[name] = {"sha256": got, "left_out": str(exc)}
            continue
        info["sha256"] = got
        inputs[name] = info
        if info["split_like"]:
            if name in ELIGIBLE:
                raise Stop(f"STOP: {name}: split-like move {info['split_like'][:3]} in an audited name")
            skipped[name] = f"split-like move {info['split_like'][:3]} (report only name left out)"
            continue
        series[name] = ser
    for name in ELIGIBLE:
        if series[name]["dates"][0] > pd.Timestamp("2005-01-31"):
            raise Stop(f"STOP: {name}: first row after 2005-01-31")
        if window(series[name]["dates"], *VERDICT) is None:
            raise Stop(f"STOP: {name}: no judged window")

    rate = {name: session_rates(s["dates"], rates) for name, s in series.items()}
    zero = {name: session_rates(s["dates"], rates, zero=True) for name, s in series.items()}

    checks: dict[str, Any] = {"core_cross_check": {}, "truncation": {}}
    for name, s in series.items():           # every judged name and every report-only name that was kept
        checks["core_cross_check"][name] = core_cross_check(core, s["close"], s["high"], s["low"], s["volume"])
        a, z = window(s["dates"], *VERDICT) or (min(3 * L_MAIN, len(s["close"]) - 1), len(s["close"]) - 1)
        cuts = [a + (z - a) * k // 8 for k in range(1, 9)] + [len(s["close"]) - 1]
        checks["truncation"][name] = truncation_check(s, rate[name], cuts, L_MAIN)

    res: dict[Any, Any] = {}
    for lb in (L_MAIN, *NEIGHBOURS):
        for cost in COSTS:
            if lb != L_MAIN and cost != 10.0:
                continue
            res[(lb, cost)] = {name: run_stock(series[name], rate[name], cost, lb, "T", VERDICT,
                                               with_folds=(lb == L_MAIN and cost == 10.0))
                               for name in ELIGIBLE}
    res["halves"] = {f"{hs}..{he}": {name: run_stock(series[name], rate[name], 10.0, L_MAIN, "T", (hs, he))
                                     for name in ELIGIBLE} for hs, he in HALVES}
    gates = judge(res)
    verdict = verdict_of(gates)

    def table(rows: dict[str, Any]) -> dict[str, Any]:
        return {"per_stock": rows,
                "T_minus_H": {"cagr": spread(rows, "cagr", "H"), "mdd": spread(rows, "mdd", "H")},
                "T_minus_F": {"cagr": spread(rows, "cagr", "F"), "mdd": spread(rows, "mdd", "F")},
                "share_pass_vs_hold": sum(1 for r in rows.values() if pass_h(r)) / len(rows)}

    report: dict[str, Any] = {
        "judged_window": {f"L{lb}_cost{int(cost)}": table(rows) for (lb, cost), rows in
                          ((k, v) for k, v in res.items() if k != "halves")},
        "halves": {k: table(v) for k, v in res["halves"].items()},
        "recent_2016_08_05_on": table({name: run_stock(series[name], rate[name], 10.0, L_MAIN, "T", RECENT)
                                       for name in ELIGIBLE}),
        "recent_2021_08_05_on": table({name: run_stock(series[name], rate[name], 10.0, L_MAIN, "T", RECENT5)
                                       for name in ELIGIBLE}),
        "zero_cash_interest_judged": table({name: run_stock(series[name], zero[name], 10.0, L_MAIN, "T", VERDICT)
                                            for name in ELIGIBLE}),
        "variant_E1_exit_on_C3_only_judged": table({name: run_stock(series[name], rate[name], 10.0, L_MAIN, "E1",
                                                                    VERDICT) for name in ELIGIBLE}),
        "variant_E2_reentry_C3_and_C5_judged": table({name: run_stock(series[name], rate[name], 10.0, L_MAIN, "E2",
                                                                      VERDICT) for name in ELIGIBLE}),
        "extra_names": {}, "extra_names_skipped": skipped,
    }
    for name in REPORT_EXTRA:
        if name not in series:
            continue
        s = series[name]
        full = (s["dates"][1].date().isoformat(), "2099-12-31")
        report["extra_names"][name] = {
            "full_history_10bp": run_stock(s, rate[name], 10.0, L_MAIN, "T", full),
            "full_history_50bp": run_stock(s, rate[name], 50.0, L_MAIN, "T", full),
            "from_2021_08_05_10bp": run_stock(s, rate[name], 10.0, L_MAIN, "T", RECENT5),
            "trade_dates": [[kind, s["dates"][i].date().isoformat()] for kind, i, _ in simulate_t(
                s["open"], s["close"], s["ok"], rate[name], *rule_flags(signals(s["close"], L_MAIN)), 10.0)["trades"]],
        }
    return {"contract": contract, "pinned": pinned, "inputs": inputs, "checks": checks,
            "design": {"eligible": list(ELIGIBLE), "verdict_window": list(VERDICT), "halves": [list(h) for h in HALVES],
                       "lookback": L_MAIN, "neighbours": list(NEIGHBOURS), "costs_bp": list(COSTS),
                       "folds": make_folds(*VERDICT)},
            "gates": gates, "verdict": verdict, "report_only": report}


def run_all(root: Path, out_path: Path, pins: dict[str, tuple[str, str]] = PINS, runner: Path | None = None,
            prereg: str = PREREG, sidecar: str = PREREG_SIDECAR) -> int:
    if out_path.exists():
        raise ResultExists(f"refused: {out_path} exists (one run only)")
    contract = check_contract(root, runner, prereg, sidecar)
    body = compute(root, pins, contract)
    doc = {"generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
           "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                           "platform": platform.platform()}, **body}
    text = json.dumps(clean(doc), ensure_ascii=False, indent=1, allow_nan=False)
    if out_path.exists():
        raise ResultExists(f"refused: {out_path} exists (one run only)")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    g = doc["gates"]
    print("VERDICT", doc["verdict"], {k: g[k]["pass"] for k in sorted(g)})
    return 0


def guarded(root: Path, pins: dict[str, tuple[str, str]] = PINS, runner: Path | None = None,
            prereg: str = PREREG, sidecar: str = PREREG_SIDECAR, results: str = RESULTS_JSON,
            stops: str = STOP_DIR) -> int:
    """The one real run. 0 = results written, 1 = STOP (a record is left), 2 = results already there,
    3 = a STOP record later than the last lock / amendment (amend section 10 of the contract first)."""
    stop_dir = root / stops
    try:
        side = (root / sidecar).read_text(encoding="utf-8")
        times = [datetime.fromisoformat(ln.split()[1]) for ln in side.splitlines()
                 if len(ln.split()) >= 2 and ln.split()[0] in ("fixed_at", "amended_at")]
        last_lock = max(times) if times and all(t.tzinfo is not None for t in times) else None
    except (OSError, ValueError):
        last_lock = None                     # run_all stops on the broken sidecar and leaves a record
    if stop_dir.exists():
        for p in sorted(stop_dir.glob("exit1117-stop-*.json")):
            when = datetime.fromisoformat(json.loads(p.read_text(encoding="utf-8"))["stopped_at_kst"])
            if last_lock is None or when > last_lock:
                print(f"refused: STOP record {p.name} is later than the last lock/amendment (amend section 10 first)")
                return 3
    try:
        return run_all(root, root / results, pins, runner, prereg, sidecar)
    except ResultExists as exc:
        print(str(exc))
        return 2
    except Stop as exc:
        stop_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(KST)
        rec = stop_dir / f"exit1117-stop-{now.strftime('%Y%m%dT%H%M%S%f')}.json"
        with open(rec, "x", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"stopped_at_kst": now.isoformat(timespec="seconds"), "reason": str(exc)},
                                ensure_ascii=False, indent=1) + "\n")
        print(str(exc))
        return 1


# ----------------------------------------------------------------------------------------------
# self-test (synthetic and hand-computed data only)
# ----------------------------------------------------------------------------------------------
def _synthetic_walk(rng: np.random.RandomState, n: int, start: float = 50.0) -> tuple[list[float], ...]:
    regime = np.where(rng.rand(n) < 0.02, -0.03, 0.0005)
    drift = pd.Series(regime).rolling(15, min_periods=1).mean().to_numpy()
    close = start * np.exp(np.cumsum(drift + 0.022 * rng.randn(n)))
    op = close * np.exp(0.006 * rng.randn(n))
    op[0] = close[0]
    op[1:] = np.roll(close, 1)[1:] * np.exp(0.008 * rng.randn(n - 1))
    high = np.maximum(op, close) * (1 + 0.004 * rng.rand(n))
    low = np.minimum(op, close) * (1 - 0.004 * rng.rand(n))
    vol = 1e6 * (1 + rng.rand(n))
    return [float(x) for x in op], [float(x) for x in high], [float(x) for x in low], [float(x) for x in close], \
        [float(x) for x in vol]


def _kiwoom_payload(dates: pd.DatetimeIndex, op, high, low, close, vol, placeholders: int = 0) -> dict[str, Any]:
    rows = []
    if placeholders:
        first = dates[0]
        for k in range(placeholders, 0, -1):
            d = first - pd.offsets.BDay(k)
            rows.append({"dt": d.strftime("%Y%m%d"), "open_pric": str(close[0]), "high_pric": str(close[0]),
                         "low_pric": str(close[0]), "cur_prc": str(close[0]), "acc_trde_qty": "0"})
    for i, d in enumerate(dates):
        rows.append({"dt": d.strftime("%Y%m%d"), "open_pric": repr(op[i]), "high_pric": repr(high[i]),
                     "low_pric": repr(low[i]), "cur_prc": repr(close[i]), "acc_trde_qty": repr(vol[i])})
    return {"result": {"return_code": 0, "result_list": rows[::-1]}}


def self_test(root: Path) -> None:
    core_path = root / PINS["core_rules"][0]
    if sha256_file(core_path) != PINS["core_rules"][1]:
        raise Stop("STOP: self-test needs the pinned auto_core_rules.py")
    core = load_core(core_path)
    rng = np.random.RandomState(1117)

    # 1. cue definitions = pinned core, 40 synthetic walks (incl. short ones and ties)
    total = 0
    for k in range(40):
        n = 60 + 40 * (k % 9)
        op, high, low, close, vol = _synthetic_walk(rng, n)
        if k % 5 == 0:                       # exact ties and flat stretches
            for i in range(25, min(n, 45)):
                close[i] = round(close[24], 2)
                high[i] = max(high[i], close[i])
                low[i] = min(low[i], close[i])
        total += core_cross_check(core, close, high, low, vol)
    assert total == 8400

    # 2. T engine by hand: exit decided at close 2, sold at open 3; entry decided at close 5, bought at open 6
    op = [100.0, 100.0, 98.0, 90.0, 85.0, 88.0, 95.0, 96.0]
    close = [100.0, 99.0, 92.0, 86.0, 87.0, 94.0, 97.0, 99.0]
    ok = [True] * 8
    rate = [0.0, 0.0, 0.0, 0.001, 0.001, 0.001, 0.001, 0.001]
    exit_ = [False, False, True, True, False, False, False, False]
    entry = [False, False, False, False, False, True, True, False]
    t = simulate_t(op, close, ok, rate, exit_, entry, 50.0)
    cash3 = (1.0 / 100.0) * 90.0 * (1 - 0.005) * 1.001
    assert abs(t["value"][2] - 0.92) < 1e-12 and abs(t["value"][3] - cash3) < 1e-12
    cash5 = cash3 * 1.001 * 1.001
    assert abs(t["value"][5] - cash5) < 1e-12 and t["held"][5] is False
    shares6 = cash5 * (1 - 0.005) / 95.0
    assert abs(t["value"][6] - shares6 * 97.0) < 1e-12 and t["held"][6] is True
    assert [(k, i) for k, i, _ in t["trades"]] == [("sell", 3), ("buy", 6)]
    assert abs(t["value"][7] - shares6 * 99.0) < 1e-12
    # an untradable open defers the order
    ok2 = [True, True, True, False, True, True, True, True]
    t2 = simulate_t(op, close, ok2, rate, exit_, entry, 0.0)
    assert [(k, i) for k, i, _ in t2["trades"]][0] == ("sell", 4)
    assert abs(t2["value"][3] - 0.86) < 1e-12
    # exit flag while out and entry flag while in do nothing
    t3 = simulate_t(op, close, ok, [0.0] * 8, [False] * 8, [True] * 8, 10.0)
    assert t3["trades"] == [] and abs(t3["value"][7] - 0.99) < 1e-12

    # 3. F by hand: w = 0.5, year change at index 3
    dates = [pd.Timestamp(x) for x in ("2010-12-28", "2010-12-29", "2010-12-30", "2011-01-03", "2011-01-04")]
    fo = [100.0, 100.0, 110.0, 120.0, 120.0]
    fc = [100.0, 110.0, 120.0, 120.0, 132.0]
    f = simulate_f(fo, fc, [True] * 5, [0.0] * 5, dates, 1, 4, 0.5, 100.0)
    assert abs(f[1] - 1.05) < 1e-12 and abs(f[2] - 1.10) < 1e-12
    fee = 0.01 * abs(0.5 * 1.10 - 0.60)
    assert abs(f[3] - (1.10 - fee)) < 1e-12
    assert abs(f[4] - (0.55 * 1.1 + 0.55 - fee)) < 1e-12
    f1 = simulate_f(fo, fc, [True] * 5, [0.0] * 5, dates, 1, 4, 1.0, 100.0)
    assert all(abs(f1[i] - fc[i] / 100.0) < 1e-12 for i in range(1, 5))

    # 4. metrics by hand
    m = metrics([1.0, 1.2, 0.9, 1.5], 1, 3)
    assert abs(m["mdd"] - (0.9 / 1.2 - 1)) < 1e-12 and abs(m["cagr"] - (1.5 ** (252 / 3) - 1)) < 1e-6
    assert metrics([1.0, 1.1, 1.2], 1, 2)["calmar"] is None
    assert make_folds(*VERDICT)[0] == ("2005-02-05", "2005-08-04") and len(make_folds(*VERDICT)) == 23
    assert make_folds(*VERDICT)[-1] == ("2016-02-05", "2016-08-04")

    # 5. no look-ahead on synthetic data, and the check catches a peeking rule
    op, high, low, close, vol = _synthetic_walk(rng, 900)
    ser = {"name": "SYN", "open": op, "close": close, "ok": [True] * 900}
    assert truncation_check(ser, [0.0001] * 900, [100, 333, 500, 899], 20) == 4

    def peek(c):                                                # tomorrow's cue used today
        return rule_flags({k: v[1:] + [None] for k, v in signals(c, 20).items()})
    cut = peek(close)[0].index(True)
    try:
        truncation_check(ser, [0.0001] * 900, [cut], 20, flags=peek)
        raise AssertionError("the truncation check did not catch a peeking rule")
    except Stop:
        pass

    # 6. gates and verdicts
    def row(tc, tm, hc, hm, fcg, fm, trips=20, folds=None):
        mk = lambda c, d: {"cagr": c, "mdd": d, "calmar": c / abs(d)}
        return {"T": mk(tc, tm), "H": mk(hc, hm), "F": mk(fcg, fm), "round_trips": trips,
                "folds": folds or [{"T": 0.02, "F": 0.01}, {"T": 0.03, "F": 0.01}, {"T": 0.02, "F": 0.00}]}

    def book(r):
        rows = {f"S{i}": r for i in range(10)}
        return {(20, 10.0): rows, (20, 50.0): rows, (16, 10.0): rows, (24, 10.0): rows,
                "halves": {"a": rows, "b": rows}}
    good = row(0.10, -0.30, 0.10, -0.60, 0.07, -0.35)
    assert verdict_of(judge(book(good))) == "CANDIDATE"
    exposure_only = row(0.10, -0.30, 0.10, -0.60, 0.11, -0.28)       # hold beaten, the fixed mix is not
    assert verdict_of(judge(book(exposure_only))) == "REVIEW_ONLY_EXPOSURE"
    weak = row(0.05, -0.58, 0.10, -0.60, 0.04, -0.60)                # drawdown not 5 points shallower
    assert verdict_of(judge(book(weak))) == "BELOW_STANDARD"
    few = row(0.10, -0.30, 0.10, -0.60, 0.07, -0.35, trips=3)        # sample gate P6 alone fails
    assert verdict_of(judge(book(few))) == "BELOW_STANDARD"
    few_and_mix = row(0.10, -0.30, 0.10, -0.60, 0.11, -0.28, trips=3)  # P1 passes, P2 and P6 fail
    assert verdict_of(judge(book(few_and_mix))) == "BELOW_STANDARD"
    one_fold = row(0.10, -0.30, 0.10, -0.60, 0.07, -0.35,            # only the mix-side P7 fails
                   folds=[{"T": 0.30, "F": 0.01}, {"T": 0.011, "F": 0.01}, {"T": 0.00, "F": 0.01}])
    g7 = judge(book(one_fold))
    assert not g7["P7"]["pass"] and all(g7[k]["pass"] for k in ("P1", "P2", "P3", "P4", "P5", "P6"))
    assert verdict_of(g7) == "REVIEW_ONLY_EXPOSURE"
    b = book(good)                                                   # only the mix-side P5 fails
    b["halves"]["b"] = {k: row(0.02, -0.2, 0.05, -0.3, 0.03, -0.2) for k in b["halves"]["b"]}
    g5 = judge(b)
    assert not g5["P5"]["pass"] and all(g5[k]["pass"] for k in ("P1", "P2", "P3", "P4", "P6", "P7"))
    assert verdict_of(g5) == "REVIEW_ONLY_EXPOSURE"
    for key in ((20, 10.0), (20, 50.0), (24, 10.0)):                 # one mix-side condition alone fails
        bx = book(good)
        bx[key] = {k: exposure_only for k in bx[key]}
        gx = judge(bx)
        failed = [k for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7") if not gx[k]["pass"]]
        assert failed == [{(20, 10.0): "P2", (20, 50.0): "P3", (24, 10.0): "P4"}[key]]
        assert gx["P3"]["pass_vs_hold"] and gx["P4"]["pass_vs_hold"] and verdict_of(gx) == "REVIEW_ONLY_EXPOSURE"
    bh = book(good)                                                  # the hold part of a neighbour fails
    bh[(16, 10.0)] = {k: weak for k in bh[(16, 10.0)]}
    g4 = judge(bh)
    assert g4["P1"]["pass"] and not g4["P4"]["pass_vs_hold"] and verdict_of(g4) == "BELOW_STANDARD"
    bc = book(good)                                                  # the hold part of the 50bp gate fails
    bc[(20, 50.0)] = {k: weak for k in bc[(20, 50.0)]}
    g3 = judge(bc)
    assert g3["P1"]["pass"] and not g3["P3"]["pass_vs_hold"] and verdict_of(g3) == "BELOW_STANDARD"
    # per-stock gate against hold: positive hold CAGR (S4 precedent formulas)
    assert pass_h(row(0.09, -0.30, 0.10, -0.60, 0, -1)) and not pass_h(row(0.0899, -0.30, 0.10, -0.60, 0, -1))
    assert not pass_h(row(0.09, -0.56, 0.10, -0.60, 0, -1))          # (a) only 4 points shallower
    assert not pass_h(row(0.09, -0.55, 0.10, -0.60, 0, -1))          # (a), (b) pass, Calmar gain under 10%
    assert not pass_h(row(-0.01, -0.20, 0.10, -0.60, 0, -1))         # T loses money, hold does not
    # hold CAGR not positive: Calmar would run backwards, so CAGR(T) >= CAGR(H) replaces it
    assert pass_h(row(-0.02, -0.40, -0.05, -0.80, 0, -1))
    assert pass_h(row(-0.04, -0.40, -0.05, -0.80, 0, -1))            # Calmar -0.100 < -0.0625, still better
    assert not pass_h(row(-0.06, -0.40, -0.05, -0.80, 0, -1))        # shallower drawdown, lower return
    assert not pass_h(row(-0.04, -0.78, -0.05, -0.80, 0, -1))        # higher return, drawdown not 5 points
    assert pass_h(row(0.00, -0.40, 0.00, -0.80, 0, -1))              # hold CAGR exactly zero
    mixed = {f"S{i}": (good if i < 6 else weak) for i in range(10)}
    bm = book(good)
    bm[(20, 10.0)] = mixed
    assert judge(bm)["P1"]["pass"] and abs(judge(bm)["P1"]["share_pass_vs_hold"] - 0.6) < 1e-12

    # 7 + 8. guards and an end-to-end run on synthetic Kiwoom-format files (history wider than the real fetch)
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        (troot / "docs/claude/s44v2-inputs").mkdir(parents=True)
        files = {}
        for k, name in enumerate((*ELIGIBLE, *REPORT_EXTRA)):
            first = {"BE": "2018-07-25", "LITE": "2015-08-05"}.get(name, "1990-01-02" if k % 2 == 0 else "2004-12-21")
            dates = pd.bdate_range(first, "2026-11-02")
            op, high, low, close, vol = _synthetic_walk(np.random.RandomState(100 + k), len(dates))
            rel = f"docs/claude/s44v2-inputs/{name}_kiwoom_usa06012_daily_adj1_20261102.json"
            (troot / rel).write_text(json.dumps(_kiwoom_payload(dates, op, high, low, close, vol,
                                                                placeholders=3 if k == 1 else 0)), encoding="utf-8")
            files[name] = {"path": rel, "sha256": sha256_file(troot / rel)}
        man_rel = "docs/claude/s44v2-inputs/inputs-manifest.json"
        (troot / man_rel).write_text(json.dumps({"files": files}), encoding="utf-8")
        prior_rel = "docs/claude/s44v2-results.json"
        (troot / prior_rel).write_text(json.dumps({
            "inputs_manifest": {"sha256": sha256_file(troot / man_rel)},
            "universe_audit": {"eligible": list(ELIGIBLE)},
            "identity_check": {n: {"passed": True} for n in ELIGIBLE}}), encoding="utf-8")
        rate_rel = "rates/DGS3MO.csv"
        (troot / "rates").mkdir()
        (troot / rate_rel).write_text("observation_date,DGS3MO\n1989-12-29,5.0\n2008-12-16,0.1\n2009-01-02,\n"
                                      "2017-01-03,1.0\n", encoding="utf-8")
        pins = {"manifest": (man_rel, sha256_file(troot / man_rel)),
                "s44v2_results": (prior_rel, sha256_file(troot / prior_rel)),
                "dgs3mo": (rate_rel, sha256_file(troot / rate_rel)),
                "core_rules": (str(core_path.resolve()), PINS["core_rules"][1])}
        (troot / "docs/claude/p.md").write_text("contract", encoding="utf-8")
        me = Path(__file__).resolve()

        def lock(raw: str, runner_sha: str, extra: str = "", fixed: str = "2026-11-01T12:00:00+09:00") -> None:
            (troot / "docs/claude/p.sha256").write_text(
                f"raw_sha256 {raw}\nrunner_sha256 {runner_sha}\nfixed_at {fixed}\n{extra}", encoding="utf-8")
        good_raw = hashlib.sha256(b"contract").hexdigest()
        out = troot / "docs/claude/out.json"
        for raw, rsha, extra, fixed in (
                (good_raw[::-1], sha256_file(me), "", None), (good_raw, "0" * 64, "", None),
                (good_raw, sha256_file(me), "fixed_at 2026-11-01T13:00:00+09:00\n", None),
                (good_raw, sha256_file(me), "amended_at 2026-11-01T11:00:00+09:00\n", None),
                (good_raw, sha256_file(me), "", "2026-11-01T12:00:00"),          # no UTC offset
                (good_raw, sha256_file(me), "amended_at 2026-11-01T13:00:00\n", None),
                (good_raw, sha256_file(me), "", "yesterday")):
            lock(raw, rsha, extra, *(() if fixed is None else (fixed,)))
            try:
                run_all(troot, out, pins, me, "docs/claude/p.md", "docs/claude/p.sha256")
                raise AssertionError("contract guard did not stop")
            except Stop:
                pass
        for missing in ("docs/claude/none.md", "docs/claude/p.md"):          # a missing contract file is a STOP
            try:
                run_all(troot, out, pins, me, missing,
                        "docs/claude/none.sha256" if missing.endswith("p.md") else "docs/claude/p.sha256")
                raise AssertionError("missing contract file did not stop")
            except Stop:
                pass
        lock(good_raw, sha256_file(me))
        bad = dict(pins)
        bad["dgs3mo"] = (rate_rel, "0" * 64)
        try:
            run_all(troot, out, bad, me, "docs/claude/p.md", "docs/claude/p.sha256")
            raise AssertionError("pin guard did not stop")
        except Stop:
            pass
        assert not out.exists()
        assert run_all(troot, out, pins, me, "docs/claude/p.md", "docs/claude/p.sha256") == 0
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["verdict"] in ("CANDIDATE", "REVIEW_ONLY_EXPOSURE", "BELOW_STANDARD")
        assert doc["inputs"]["MRVL"]["placeholders_dropped"] == 3
        assert doc["inputs"]["AMD"]["rows_before_audit_from"] > 3000 and doc["inputs"]["AMD"]["first"] == "2004-12-01"
        assert doc["inputs"]["MRVL"]["first"] == "2004-12-21" and doc["inputs"]["MRVL"]["last"] == "2026-10-30"
        assert set(doc["report_only"]["extra_names"]) == {"BE", "LITE"}
        j = doc["report_only"]["judged_window"]["L20_cost10"]["per_stock"]["TXN"]
        assert j["window"] == ["2005-02-07", "2016-08-04"] and len(j["folds"]) == 23
        assert 0.0 < j["avg_exposure"] < 1.0 and j["H"]["sessions"] == j["T"]["sessions"]
        try:
            run_all(troot, out, pins, me, "docs/claude/p.md", "docs/claude/p.sha256")
            raise AssertionError("second run was not refused")
        except ResultExists:
            pass
        # a report-only name with bad data is left out, the judged names still run
        lite = troot / files["LITE"]["path"]
        payload = json.loads(lite.read_text(encoding="utf-8"))
        payload["result"]["result_list"][5]["cur_prc"] = "0"
        lite.write_text(json.dumps(payload), encoding="utf-8")
        files2 = {**files, "LITE": {"path": files["LITE"]["path"], "sha256": sha256_file(lite)}}
        (troot / man_rel).write_text(json.dumps({"files": files2}), encoding="utf-8")
        prior = json.loads((troot / prior_rel).read_text(encoding="utf-8"))
        prior["inputs_manifest"]["sha256"] = sha256_file(troot / man_rel)
        (troot / prior_rel).write_text(json.dumps(prior), encoding="utf-8")
        pins2 = {**pins, "manifest": (man_rel, sha256_file(troot / man_rel)),
                 "s44v2_results": (prior_rel, sha256_file(troot / prior_rel))}
        out2 = troot / "docs/claude/out2.json"
        assert run_all(troot, out2, pins2, me, "docs/claude/p.md", "docs/claude/p.sha256") == 0
        doc2 = json.loads(out2.read_text(encoding="utf-8"))
        assert set(doc2["report_only"]["extra_names"]) == {"BE"} and "LITE" in doc2["report_only"]["extra_names_skipped"]
        assert doc2["gates"] == doc["gates"] and doc2["verdict"] == doc["verdict"]
        assert set(doc2["checks"]["core_cross_check"]) == {*ELIGIBLE, "BE"}
        assert set(doc["checks"]["core_cross_check"]) == {*ELIGIBLE, *REPORT_EXTRA}
        # the guarded entry: STOP record -> refused until amended -> one run -> refused again
        kw = dict(runner=me, prereg="docs/claude/p.md", sidecar="docs/claude/p.sha256",
                  results="docs/claude/guarded.json", stops="docs/claude/stops")
        stop_glob = lambda: sorted((troot / "docs/claude/stops").glob("exit1117-stop-*.json"))   # noqa: E731
        assert guarded(troot, {**pins2, "dgs3mo": (rate_rel, "0" * 64)}, **kw) == 1   # pin mismatch: STOP + record
        assert len(stop_glob()) == 1 and "DGS3MO" in json.loads(stop_glob()[0].read_text(encoding="utf-8"))["reason"]
        assert guarded(troot, pins2, **kw) == 3                            # record later than the lock
        assert not (troot / "docs/claude/guarded.json").exists() and len(stop_glob()) == 1
        later = (datetime.now(KST) + timedelta(hours=1)).isoformat(timespec="seconds")
        lock(good_raw, sha256_file(me), f"amended_at {later}\n")
        assert guarded(troot, pins2, **kw) == 0                            # amended: the run goes through
        assert json.loads((troot / "docs/claude/guarded.json").read_text(encoding="utf-8"))["gates"] == doc["gates"]
        assert guarded(troot, pins2, **kw) == 2                            # results already there
        assert len(stop_glob()) == 1

        # the same bad row in a judged name is a STOP
        amd = troot / files["AMD"]["path"]
        payload = json.loads(amd.read_text(encoding="utf-8"))
        payload["result"]["result_list"][5]["cur_prc"] = "0"
        amd.write_text(json.dumps(payload), encoding="utf-8")
        files3 = {**files2, "AMD": {"path": files["AMD"]["path"], "sha256": sha256_file(amd)}}
        (troot / man_rel).write_text(json.dumps({"files": files3}), encoding="utf-8")
        prior["inputs_manifest"]["sha256"] = sha256_file(troot / man_rel)
        (troot / prior_rel).write_text(json.dumps(prior), encoding="utf-8")
        pins3 = {**pins, "manifest": (man_rel, sha256_file(troot / man_rel)),
                 "s44v2_results": (prior_rel, sha256_file(troot / prior_rel))}
        try:
            run_all(troot, troot / "docs/claude/out3.json", pins3, me, "docs/claude/p.md", "docs/claude/p.sha256")
            raise AssertionError("bad data in a judged name did not stop")
        except Stop as exc:
            assert "AMD" in str(exc)
    print("SELF_TEST_OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()                   # no output option: the results path is part of the contract
    if args.self_test:
        self_test(args.root)
        return 0
    if args.run:
        return guarded(args.root)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
