#!/usr/bin/env python3
"""cue-count-gate pre-registered replay: does the reduce ticket need to wait for two weak price cues?

Contract: docs/claude/cue-count-gate-preregistration-2026-11-18.md (+ .sha256 sidecar). This file is part of
the contract: the sidecar pins its sha256 and the run refuses when either changed after the lock.

Question (user decision card 2026-11-18 09:05:54 KST, option 'run as drafted'): on a session whose close puts
the exposure in the reduce zone (E >= 1.85), the core issues the reduce ticket only when the sell side has at
least two kinds of weak price cue (auto_core_tickets.evidence_summary, basis_met). Is that line
  G  (Champion: the present evidence ladder, called from the pinned core as it is)
better than
  U  (challenger: the reduce ticket does not look at price cues, step ceiling 1/2), and than
  F  a fixed mix with the same time-average SOXL weight (rebalanced once a year)?

Model: one account holding SOXL and cash, E = 3 x SOXL weight. Decision at the close of session t, LOC order
filled at the close of session t + 1 when the close is on the right side of the LOC price. Everything that is
not the evidence ladder is the same for G and U: target weight, regret table and step choice (pinned core
functions), deadband, LOC price, refill rule, cost, cash interest.

Reads: the pinned Kiwoom SOXL daily file fetched 2026-10-09 (no new query), its pinned source record, pinned
DGS3MO (cash interest), the pinned core modules (auto_core_rules.py, auto_core_tickets.py; one function text
of portfolio_exposure.py) and the pinned card evidence registry (SOXL entry). Writes one results JSON, once.

No order, quantity or price authority. Research only (order_authority=false). Model amounts are not account
amounts; the results file carries ratios only.

  --self-test   synthetic data only (run before the lock; needs the pinned core files under --root)
  --run         the one real run (fixed output path; refuses when the results file exists)
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import inspect
import json
import math
import platform
import random
import shutil
import signal
import sys
import tempfile
import time
import types
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_FLOOR, Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
KST = timezone(timedelta(hours=9))

PREREG = "docs/claude/cue-count-gate-preregistration-2026-11-18.md"
PREREG_SIDECAR = "docs/claude/cue-count-gate-preregistration-2026-11-18.sha256"
RESULTS_JSON = "docs/claude/cue-count-gate-results.json"
STOP_DIR = "docs/claude/cue-count-gate-stops"
STOP_PREFIX = "cue-count-gate-stop-"

SYMBOL = "SOXL"
PINS = {
    "soxl": ("stock-strategy-system/backtests/fx5b_inputs_2026-10-09/kiwoom_raw/"
             "SOXL_kiwoom_usa06012_daily_adj1_20261009.json",
             "e8faa3ac68bf2c283b2c4ae84c232cbb60a3a2b61dddc7869dee03c37aba980f"),
    "sources": ("stock-strategy-system/backtests/fx5b_inputs_2026-10-09/kiwoom_raw_sources.json",
                "62eeb50f4ff19012cb59de5c215092028d6cb33ab2a3d835a07d8924b1e819e6"),
    "dgs3mo": ("stock-strategy-system/backtests/rule1028_a3_inputs_2026-10-28/fred/DGS3MO.csv",
               "739d4ce160fb4f294837e2573d29b5f9a0f4e4642f15e100d841870849c8230a"),
    "core_rules": ("manage-us-stock-strategy/scripts/auto_core_rules.py",
                   "ba979d234ea95644c6bb78456e8f500974060ab96c23f8dafe97281acaa4ea6a"),
    "core_tickets": ("manage-us-stock-strategy/scripts/auto_core_tickets.py",
                     "4e9deac04772cfda5e4776da3a1dee8426cebe4edaee12b1f661713175786b64"),
    "exposure": ("manage-us-stock-strategy/scripts/portfolio_exposure.py",
                 "9a5360c58f55b18a36c906c011132588152e85cd20cce6bc768288a7a1b1fb09"),
    "registry": ("docs/claude/card-evidence-registry.json",
                 "9a46c3464f545be8976b72a050e8da15a316649ce70e1cdbd6a29e6110c5b3c9"),
}
# Identity of the price file (its JSON does not echo the ticker): the approximate regular-session closes of
# two sessions from another collection (workspace/outputs/regular-session-closes/history/SOXL.close-history.json,
# Kiwoom 30-minute bars usa06011, read 2026-11-18). The file's close must be within IDENTITY_TOL of each.
IDENTITY_REFS = (("2026-09-15", 102.33), ("2026-10-01", 153.75))
IDENTITY_TOL = 0.02

# Exposure band (stock-strategy-system/alert_policy.json lines 684-690; the first three are also checked
# against auto_core_tickets.POLICY_EXPECTED of the pinned core).
MULTIPLIER = 3
TARGET_E = Decimal("1.55")
REDUCE_GTE = 1.85
HARD_GTE = 1.90
ADD_LTE = 1.25
WEIGHT_STEP = Decimal("0.001")         # portfolio_exposure.WEIGHT_STEP (text-checked against the pinned file)
U_R_MAX = Fraction(1, 2)               # challenger step ceiling = the ladder's "two weak kinds" ceiling

WARMUP = 65                            # sessions before the account opens (sigma60 needs 61 closes, the
                                       # regret scenarios 65, EMA50 50)
HALF_SPLIT = "2019-01-01"              # c-rule replay halves: 2011-2018 / 2019-
MIN_HALF_SESSIONS = 504
COSTS = (10.0, 50.0)                   # bp per traded value; 50 = the stress used in exit-1117
YEAR = 252.0
EQUITY0 = 10_000_000.0                 # model scale only (share rounding becomes negligible); never reported
SPLIT_RATIOS = (2, 3, 4, 5, 10, 15, 20)
SPLIT_LIKE_TOL = 0.005
SPLIT_GUARD_LOW, SPLIT_GUARD_HIGH = 0.5, 2.0   # portfolio_exposure.py data-integrity guard (text-checked): a
                                       # close ratio at or beyond these is a STOP
FLAG_MIN_RATE = 20.0                   # a Kiwoom price-adjustment flag (upd_rt, percent) of at least this size
FLAG_TOL = 0.20                        # ... whose row moves like the unadjusted event (within 20%) is a STOP
EXTREME_LOW, EXTREME_HIGH = 0.6, 1.6   # report only: sessions whose close ratio is beyond these
MAX_GAP_DAYS = 7                       # a calendar gap longer than this between two rows is a data STOP
EPS = 1e-12

# Gates (section 4 of the contract)
Q3_CAGR_KEEP = 0.90
Q7_EPISODES = 10
Q7_BLOCKED_DAYS = 20
SUPPORT_CALMAR_RATIO = 1.10


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
    if isinstance(obj, Fraction):
        return f"{obj.numerator}/{obj.denominator}" if obj.denominator != 1 else str(obj.numerator)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    return obj


def check_contract(root: Path, runner: Path | None = None, prereg: str = PREREG,
                   sidecar: str = PREREG_SIDECAR) -> dict[str, Any]:
    """Sidecar lines: raw_sha256, runner_sha256, fixed_at (exactly once) and optional amended_at lines.
    Every amended_at value must also stand in the pre-registration text (section 10), so an amendment cannot
    be made without changing the document; no lock time may lie in the future."""
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
    now = datetime.now(KST)
    if any(datetime.fromisoformat(t) > now for t in [fixed[0], *amended]):
        raise Stop("STOP: a lock or amendment time lies in the future")
    text = (root / prereg).read_text(encoding="utf-8")
    if any(t not in text for t in amended):
        raise Stop("STOP: an amended_at time is not written in the pre-registration (section 10)")
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
def load_kiwoom(path: Path) -> list[dict[str, Any]]:
    """usa06012 daily, adjusted=1: rows sorted by date (the file is newest first)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["result"]["return_code"] != 0:
        raise Stop(f"STOP: {path.name}: return_code != 0")
    rows = []
    for r in payload["result"]["result_list"]:
        d = str(r["dt"])
        try:
            rows.append({"day": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "open": float(r["open_pric"]),
                         "high": float(r["high_pric"]), "low": float(r["low_pric"]), "close": float(r["cur_prc"]),
                         "volume": float(r["acc_trde_qty"]), "upd_tp": str(r.get("upd_stkpc_tp") or ""),
                         "upd_rt": str(r.get("upd_rt") or "")})
        except (KeyError, TypeError, ValueError):
            raise Stop(f"STOP: {path.name}: unreadable row {d}") from None
    rows.sort(key=lambda row: row["day"])
    days = [row["day"] for row in rows]
    if len(set(days)) != len(days):
        raise Stop(f"STOP: {path.name}: duplicate dates")
    for day in days:
        try:
            date.fromisoformat(day)
        except ValueError:
            raise Stop(f"STOP: {path.name}: bad date {day}") from None
    return rows


def prepare(rows: list[dict[str, Any]], name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Leading placeholder rows out, last (provisional) row out, then the data checks."""
    k0 = 0
    while k0 < len(rows) and rows[k0]["volume"] <= 0 and (
            rows[k0]["open"] == rows[k0]["close"] == rows[k0]["high"] == rows[k0]["low"]):
        k0 += 1
    body = rows[k0:]
    if len(body) < WARMUP + 2 * MIN_HALF_SESSIONS:
        raise Stop(f"STOP: {name}: too few rows")
    provisional = body[-1]["day"]
    body = body[:-1]
    days = [row["day"] for row in body]
    close = [row["close"] for row in body]
    for key in ("close", "high", "low"):
        if not all(math.isfinite(row[key]) and row[key] > 0 for row in body):
            raise Stop(f"STOP: {name}: {key} not finite and positive")
    if not all(math.isfinite(row["volume"]) and row["volume"] >= 0 for row in body):
        raise Stop(f"STOP: {name}: volume not finite")
    gaps = [(days[i - 1], days[i], (date.fromisoformat(days[i]) - date.fromisoformat(days[i - 1])).days)
            for i in range(1, len(days))]
    long_gaps = [g for g in gaps if g[2] > MAX_GAP_DAYS]
    if long_gaps:
        raise Stop(f"STOP: {name}: calendar gap longer than {MAX_GAP_DAYS} days {long_gaps[:3]}")
    if any(date.fromisoformat(day).weekday() >= 5 for day in days):
        raise Stop(f"STOP: {name}: a weekend date")
    ratio = [close[i] / close[i - 1] for i in range(1, len(close))]
    split_like = [days[i + 1] for i, r in enumerate(ratio)
                  if any(abs(r / k - 1) <= SPLIT_LIKE_TOL or abs(r * k - 1) <= SPLIT_LIKE_TOL for k in SPLIT_RATIOS)]
    if split_like:
        raise Stop(f"STOP: {name}: split-like move {split_like[:3]}")
    beyond = [days[i + 1] for i, r in enumerate(ratio) if r <= SPLIT_GUARD_LOW or r >= SPLIT_GUARD_HIGH]
    if beyond:
        raise Stop(f"STOP: {name}: close ratio at or beyond the split guard {beyond[:3]}")
    flagged = []
    for i in range(len(body)):
        if not body[i]["upd_rt"]:
            continue
        try:
            rt = float(body[i]["upd_rt"])
        except ValueError:
            raise Stop(f"STOP: {name}: unreadable adjustment rate on {days[i]}") from None
        raw_ratio = 1.0 + rt / 100.0           # what the close ratio would be had the event not been adjusted
        flagged.append({"day": days[i], "upd_stkpc_tp": body[i]["upd_tp"], "upd_rt": rt,
                        "close_ratio": ratio[i - 1] if i else None})      # the first kept row has no ratio
        if i and abs(rt) >= FLAG_MIN_RATE and raw_ratio > 0 and abs(ratio[i - 1] / raw_ratio - 1.0) <= FLAG_TOL:
            raise Stop(f"STOP: {name}: flagged price adjustment on {days[i]} ({rt}%) looks unadjusted")
    dropped_flags = [{"day": row["day"], "upd_stkpc_tp": row["upd_tp"], "upd_rt": row["upd_rt"]}
                     for row in rows[:k0] + rows[-1:] if row["upd_rt"]]       # report only: rows not used
    low_i = min(range(len(ratio)), key=lambda i: ratio[i])
    high_i = max(range(len(ratio)), key=lambda i: ratio[i])
    per_year: dict[str, int] = {}
    for day in days:
        per_year[day[:4]] = per_year.get(day[:4], 0) + 1
    series = {"name": name, "days": days, "close": close, "high": [row["high"] for row in body],
              "low": [row["low"] for row in body], "volume": [row["volume"] for row in body]}
    info = {"placeholders_dropped": k0, "provisional_row_dropped": provisional, "first": days[0], "last": days[-1],
            "rows": len(body), "sessions_per_year": per_year,
            "gaps_of_5_days_or_more": [list(g) for g in gaps if g[2] >= 5],
            "close_outside_high_low": sum(1 for row in body if not row["low"] - 1e-9 <= row["close"] <= row["high"] + 1e-9),
            "zero_volume_rows": sum(1 for row in body if row["volume"] <= 0),
            "zero_volume_days": [row["day"] for row in body if row["volume"] <= 0],
            "adjustment_flag_rows": flagged, "adjustment_flags_on_dropped_rows": dropped_flags,
            "min_close_ratio": [days[low_i + 1], ratio[low_i]], "max_close_ratio": [days[high_i + 1], ratio[high_i]],
            "extreme_close_ratios": [[days[i + 1], r] for i, r in enumerate(ratio)
                                     if r <= EXTREME_LOW or r >= EXTREME_HIGH]}
    return series, info


def identity_check(series: dict[str, Any], refs: tuple[tuple[str, float], ...], tol: float) -> list[dict[str, Any]]:
    out = []
    index = {day: i for i, day in enumerate(series["days"])}
    for day, ref in refs:
        if day not in index:
            raise Stop(f"STOP: identity check: no row for {day}")
        got = series["close"][index[day]]
        if abs(got / ref - 1.0) > tol:
            raise Stop(f"STOP: identity check: close on {day} is {got}, reference {ref} (not the expected instrument)")
        out.append({"day": day, "reference": ref, "ratio": got / ref})
    return out


def source_record_check(root: Path, pins: dict[str, tuple[str, str]], raw_rows: int, first: str, last: str
                        ) -> dict[str, Any]:
    """The pinned collection record names this file (ticker, sha256, rows, first and last date)."""
    doc = json.loads((root / pins["sources"][0]).read_text(encoding="utf-8"))
    rel = Path(pins["soxl"][0]).name
    hits = [f for f in doc["files"] if Path(f["file"]).name == rel]
    if len(hits) != 1:
        raise Stop("STOP: the source record does not name the price file exactly once")
    rec = hits[0]
    if rec["ticker"] != SYMBOL or rec["sha256"] != pins["soxl"][1]:
        raise Stop("STOP: the source record's ticker or sha256 differs from the pin")
    if rec["rows"] != raw_rows or rec["first"] != first or rec["last"] != last:
        raise Stop(f"STOP: the source record rows/first/last {rec['rows']}/{rec['first']}/{rec['last']} differ "
                   f"from the file {raw_rows}/{first}/{last}")
    return {"ticker": rec["ticker"], "exchange": rec["exchange"], "called_kst": rec["called_kst"],
            "rows": rec["rows"], "first": rec["first"], "last": rec["last"]}


def load_rates(path: Path) -> tuple[list[str], list[float]]:
    days, vals = [], []
    for ln in path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = ln.strip().split(",")
        if len(parts) != 2 or parts[1] in ("", "."):
            continue
        days.append(parts[0])
        vals.append(float(parts[1]))
    if not days or days != sorted(days):
        raise Stop("STOP: DGS3MO series empty or unsorted")
    return days, vals


def session_rates(days: list[str], rates: tuple[list[str], list[float]], zero: bool = False) -> list[float]:
    """Cash interest of one session: the last DGS3MO observation dated before the session, / 100 / 252."""
    if zero:
        return [0.0] * len(days)
    rdays, vals = rates
    out = []
    for d in days:
        k = bisect.bisect_left(rdays, d) - 1
        if k < 0:
            raise Stop("STOP: no DGS3MO observation before the first session")
        out.append(vals[k] / 100.0 / YEAR)
    return out


# ----------------------------------------------------------------------------------------------
# the pinned core
# ----------------------------------------------------------------------------------------------
def _sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = math.fsum(values) / len(values)
    return math.sqrt(math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _not_used(*_args: Any, **_kwargs: Any) -> Any:
    raise Stop("STOP: a stubbed core dependency was called (the replay must not reach it)")


def load_core(root: Path, pins: dict[str, tuple[str, str]]) -> types.SimpleNamespace:
    """auto_core_rules.py and auto_core_tickets.py of the pinned tree, imported as they are. Their imports from
    portfolio_exposure / auto_core_reconcile are replaced by stubs: _sample_std is the same text as the pinned
    portfolio_exposure.py (checked), WEIGHT_STEP the same value (checked), the rest must never be called."""
    text = (root / pins["exposure"][0]).read_text(encoding="utf-8").replace("\r\n", "\n")
    if inspect.getsource(_sample_std) not in text:
        raise Stop("STOP: _sample_std here is not the text of the pinned portfolio_exposure.py")
    if f'\nWEIGHT_STEP = Decimal("{WEIGHT_STEP}")\n' not in text:
        raise Stop("STOP: WEIGHT_STEP differs from the pinned portfolio_exposure.py")
    if f"\nSPLIT_GUARD_LOW = {SPLIT_GUARD_LOW}\nSPLIT_GUARD_HIGH = {SPLIT_GUARD_HIGH}\n" not in text:
        raise Stop("STOP: split guard values differ from the pinned portfolio_exposure.py")
    exposure = types.ModuleType("portfolio_exposure")
    exposure._sample_std = _sample_std
    exposure.WEIGHT_STEP = WEIGHT_STEP
    exposure.earnings_blackout = exposure.effective_exposure = exposure.floor_to_step = _not_used
    reconcile = types.ModuleType("auto_core_reconcile")
    reconcile._clock = _not_used
    names = ("portfolio_exposure", "auto_core_reconcile", "auto_core_rules", "auto_core_tickets")
    saved = {name: sys.modules.get(name) for name in names}
    sys.modules["portfolio_exposure"], sys.modules["auto_core_reconcile"] = exposure, reconcile
    try:
        loaded = {}
        for name, key in (("auto_core_rules", "core_rules"), ("auto_core_tickets", "core_tickets")):
            spec = importlib.util.spec_from_file_location(name, root / pins[key][0])
            if spec is None or spec.loader is None:
                raise Stop(f"STOP: cannot load {pins[key][0]}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            loaded[name] = module
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    rules, tickets = loaded["auto_core_rules"], loaded["auto_core_tickets"]
    expected = tickets.POLICY_EXPECTED
    if (Decimal(str(expected["target_exposure"])) != TARGET_E or expected["reduce_when_exposure_gte"] != REDUCE_GTE
            or expected["hard_ceiling_when_exposure_gte"] != HARD_GTE):
        raise Stop("STOP: exposure band constants differ from the pinned core's POLICY_EXPECTED")
    if tickets.S["STEPS"] != (Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(1)) or U_R_MAX not in tickets.S["STEPS"]:
        raise Stop("STOP: step ladder of the pinned core is not 0, 1/3, 1/2, 1")
    return types.SimpleNamespace(rules=rules, tickets=tickets)


def registry_entry(root: Path, pins: dict[str, tuple[str, str]]) -> dict[str, Any]:
    doc = json.loads((root / pins["registry"][0]).read_text(encoding="utf-8"))
    entry = doc["symbols"][SYMBOL]
    if not entry.get("card_triggers"):
        raise Stop("STOP: registry entry without card triggers")
    return entry


def core_bars(series: dict[str, Any]) -> dict[str, Any]:
    sessions = {day: {"close": series["close"][i], "high": series["high"][i], "low": series["low"][i],
                      "volume": series["volume"][i]} for i, day in enumerate(series["days"])}
    return {"status": "OK", "split_suspects": [], "adjusted": {"sessions": sessions}}


def evidence_track(core: types.SimpleNamespace, series: dict[str, Any], entry: dict[str, Any], start: int,
                   upto: int | None = None) -> list[dict[str, Any] | None]:
    """Sell-side evidence of every session from `start`: the pinned evaluate_symbol with that session as the
    evaluation session (it reads rows up to that session only), then the pinned evidence_summary. No official
    facts (none are on file for the past), the card as it is registered today, the symbol held."""
    days = series["days"]
    bars = core_bars(series)
    calendar = {"sessions": {day: {} for day in days}}
    check = {"eligible": True, "hash_ok": True, "entry": entry, "symbol": SYMBOL}
    card_groups = {core.rules.CARD_KINDS[trig["kind"]][0] for trig in entry["card_triggers"]
                   if trig.get("side") == "-" and trig.get("active_when") == "held"}
    out: list[dict[str, Any] | None] = [None] * len(days)
    for t in range(start, len(days) if upto is None else upto + 1):
        result = core.rules.evaluate_symbol(symbol=SYMBOL, role="holding", bars=bars, calendar=calendar,
                                            evaluation_session=days[t], registry_entry=entry, held=True,
                                            member=False, multiplier=MULTIPLIER, facts=[], buy_approved=True)
        if result["status"] != "OK" or result["indicators"]["session"] != days[t]:
            raise Stop(f"STOP: core evaluation not OK on {days[t]}")
        ev = core.tickets.evidence_summary(side="sell", result=result, check=check, official={}, config={})
        if ev["strong"]:
            raise Stop(f"STOP: strong evidence without official facts on {days[t]}")
        out[t] = {"kinds": list(ev["weak_kinds"]), "ids": list(ev["price_ids"]), "r_max": Fraction(ev["r_max"]),
                  "basis_met": bool(ev["basis_met"]), "common_only": bool(ev["common_only"]),
                  "sigma60": result["indicators"]["sigma60"]}
        if out[t]["sigma60"] is None or not out[t]["sigma60"] > 0:
            raise Stop(f"STOP: sigma60 missing on {days[t]}")
        kinds = out[t]["kinds"]
        common_only = bool(kinds) and not (set(kinds) & card_groups)
        ladder = Fraction(0) if len(kinds) < 2 else Fraction(1, 3) if common_only else Fraction(1, 2)
        if (out[t]["r_max"] != ladder or out[t]["common_only"] != common_only
                or out[t]["basis_met"] != (len(kinds) >= 2)):
            raise Stop(f"STOP: evidence ladder not as documented on {days[t]}")
    return out


def target_weight() -> Decimal:
    """Largest weight on the core's weight step whose exposure stays at or under the target (reduce_recommendations)."""
    return (TARGET_E / MULTIPLIER / WEIGHT_STEP).to_integral_value(rounding=ROUND_FLOOR) * WEIGHT_STEP


# ----------------------------------------------------------------------------------------------
# engines
# ----------------------------------------------------------------------------------------------
def ceiling_for(mode: str, ev: dict[str, Any], exposure: float) -> Fraction:
    """Step ceiling of a reduce ticket on a reduce-zone session.
    G: the pinned ladder (0 below two weak kinds, 1/3 common rule only, 1/2).  U: 1/2 whatever the cues.
    Report only - H: U at or above the hard ceiling, G below it.  GH: 1/2 when the basis is met, else 0."""
    if mode == "G":
        return ev["r_max"]
    if mode == "U":
        return U_R_MAX
    if mode == "H":
        return U_R_MAX if exposure >= HARD_GTE else ev["r_max"]
    if mode == "GH":
        return U_R_MAX if ev["basis_met"] else Fraction(0)
    raise ValueError(mode)


def simulate(core: types.SimpleNamespace, series: dict[str, Any], evidence: list[dict[str, Any] | None],
             rate: list[float], mode: str, cost_bp: float, loc: bool = True, start: int = WARMUP,
             decide_last: bool = False, peek: int = 0) -> dict[str, Any]:
    """One line, continuous from `start` (opened at the target weight at close[start], no entry cost).
    Session order from start + 1: cash interest -> the pending LOC order at the close -> value and exposure at
    the close -> decision at the close. The last session's decision places no order; with decide_last it is
    still computed and returned (truncation check). `peek` is a deliberate look-ahead bug for the self-test's
    negative control and is 0 everywhere else."""
    close, days = series["close"], series["days"]
    n = len(close)
    c = cost_bp / 10000.0
    tickets = core.tickets
    w_target = float(target_weight())
    shares = math.floor(w_target * EQUITY0 / close[start])
    cash = EQUITY0 - shares * close[start]
    value: list[float | None] = [None] * n
    weight: list[float | None] = [None] * n
    zone: list[str | None] = [None] * n
    decisions: list[tuple[Any, ...] | None] = [None] * n
    events: list[dict[str, Any]] = []
    blocked: list[int] = []
    no_ticket: dict[str, int] = {}
    pending: dict[str, Any] | None = None
    unfilled = {"sell": 0, "buy": 0}

    def decide(t: int, shares: int, equity: float, exposure: float) -> tuple[Any, ...]:
        """("sell" | "buy", step, quantity, LOC price, why, kinds) or ("none", reason)."""
        ev = evidence[t]
        if ev is None:
            raise Stop(f"STOP: no evidence on {days[t]}")
        ref = close[min(t + peek, n - 1)]
        target_shares = math.floor(w_target * equity / ref)
        if zone[t] == "reduce":
            r_max = ceiling_for(mode, ev, exposure)
            delta = shares - target_shares
            if r_max <= 0:
                return ("none", "BASIS_NOT_MET")
            if delta < 1:
                return ("none", "LOT_ZERO")
            scenario = tickets.scenarios(close[:t + 1])
            if scenario["status"] != "ok":
                raise Stop(f"STOP: scenario unavailable on {days[t]}")
            reference, equity_d = Decimal(repr(ref)), Decimal(repr(equity))
            table = tickets.regret_table(side="sell", delta=delta, reference=reference, up=scenario["up"],
                                         down=scenario["down"], equity=equity_d, candidate=None,
                                         worst_day=scenario["worst_day"], sigma=ev["sigma60"])
            step, why = tickets.choose_step(table, r_max)
            qty = tickets.step_quantity(delta, step)
            if step == 0:
                return ("none", "REGRET_ZERO")
            if qty < 1:
                return ("none", "LOT_ZERO")
            if Decimal(qty) * reference < equity_d * tickets.S["DEADBAND"]:
                return ("none", "DEADBAND")
            return ("sell", step, qty, ref * (1.0 - float(tickets.S["SELL_FLOOR_SIGMA"]) * ev["sigma60"]), why,
                    tuple(ev["kinds"]))
        if zone[t] == "add":
            qty = target_shares - shares
            if qty >= 1:
                return ("buy", Fraction(1), qty, ref * (1.0 + float(tickets.S["BUY_CAP_SIGMA"]) * ev["sigma60"]),
                        "REFILL_TO_TARGET", ())
            return ("none", "LOT_ZERO")
        return ("none", "IN_BAND")

    last_decision = None
    for t in range(start, n):
        if t > start:
            cash *= 1.0 + rate[t]
            if pending is not None:
                side, qty, limit = pending["side"], pending["qty"], pending["limit"]
                if side == "sell":
                    fills = (not loc) or close[t] >= limit * (1.0 - EPS)
                    if fills:
                        cash += qty * close[t] * (1.0 - c)
                        shares -= qty
                else:
                    fills = (not loc) or close[t] <= limit * (1.0 + EPS)
                    if fills:
                        qty = min(qty, math.floor(cash / (close[t] * (1.0 + c))))
                        cash -= qty * close[t] * (1.0 + c)
                        shares += qty
                pending["event"]["filled"] = bool(fills)
                if not fills:
                    unfilled[side] += 1
                pending = None
        equity = shares * close[t] + cash
        w = shares * close[t] / equity
        exposure = MULTIPLIER * w
        value[t], weight[t] = equity, w
        zone[t] = "reduce" if exposure >= REDUCE_GTE else "add" if exposure <= ADD_LTE else "band"
        if t == n - 1:
            if decide_last:
                last_decision = decide(t, shares, equity, exposure)
            break
        decision = decide(t, shares, equity, exposure)
        decisions[t] = decision
        if decision[0] == "none":
            if decision[1] == "BASIS_NOT_MET":
                blocked.append(t)
            if zone[t] == "reduce":
                no_ticket[decision[1]] = no_ticket.get(decision[1], 0) + 1
            continue
        side, step, qty, limit, why, kinds = decision
        event = {"day": days[t], "side": side, "step": step, "why": why, "exposure": exposure,
                 "kinds": list(kinds), "filled": None}
        events.append(event)
        pending = {"side": side, "qty": qty, "limit": limit, "event": event}
    return {"mode": mode, "cost_bp": cost_bp, "loc": loc, "start": start, "value": value, "weight": weight,
            "zone": zone, "events": events, "blocked": blocked, "no_ticket": no_ticket, "unfilled": unfilled,
            "decisions": decisions, "last_decision": last_decision}


def simulate_f(close: list[float], rate: list[float], days: list[str], a: int, z: int, w: float, cost_bp: float
               ) -> list[float | None]:
    """Fixed mix inside [a, z]: value 1 at close[a-1] with SOXL at weight w (no entry cost, as for the other
    lines). Back to w at the close of the first session of each calendar year, cost on the traded value."""
    c = cost_bp / 10000.0
    stock, cash = w, 1.0 - w
    value: list[float | None] = [None] * len(close)
    value[a - 1] = 1.0
    for t in range(a, z + 1):
        cash *= 1.0 + rate[t]
        stock *= close[t] / close[t - 1]
        if days[t][:4] != days[t - 1][:4]:
            total = stock + cash
            delta = w * total - stock
            cash = total - w * total - c * abs(delta)
            stock = w * total
        value[t] = stock + cash
    return value


def window(days: list[str], start: str, end: str, floor: int) -> tuple[int, int]:
    a = max(bisect.bisect_left(days, start), floor)
    z = bisect.bisect_right(days, end) - 1
    if z < a:
        raise Stop(f"STOP: empty window {start}..{end}")
    return a, z


def metrics(value: list[float | None], a: int, z: int) -> dict[str, float | None]:
    base = value[a - 1]
    n = z - a + 1
    cagr = (value[z] / base) ** (YEAR / n) - 1.0
    peak, mdd = base, 0.0
    for t in range(a, z + 1):
        peak = max(peak, value[t])
        mdd = min(mdd, value[t] / peak - 1.0)
    return {"cagr": cagr, "mdd": mdd, "calmar": (cagr / abs(mdd)) if mdd < 0 else None, "sessions": n,
            "total": value[z] / base - 1.0}


def episodes(zone: list[str | None], a: int, z: int) -> list[tuple[int, int]]:
    """Maximal runs of reduce-zone sessions inside [a, z]."""
    out, begin = [], None
    for t in range(a, z + 1):
        if zone[t] == "reduce" and begin is None:
            begin = t
        if zone[t] != "reduce" and begin is not None:
            out.append((begin, t - 1))
            begin = None
    if begin is not None:
        out.append((begin, z))
    return out


def line_stats(run: dict[str, Any], days: list[str], a: int, z: int) -> dict[str, Any]:
    weight, zone = run["weight"], run["zone"]
    span = range(a, z + 1)
    index = {day: i for i, day in enumerate(days)}
    inside = [e for e in run["events"] if a <= index[e["day"]] <= z]
    sells = [e for e in inside if e["side"] == "sell"]
    buys = [e for e in inside if e["side"] == "buy"]
    eps = episodes(zone, a, z)
    return {**metrics(run["value"], a, z),
            "avg_weight": math.fsum(weight[t] for t in span) / len(span),
            "avg_exposure": MULTIPLIER * math.fsum(weight[t] for t in span) / len(span),
            "max_exposure": MULTIPLIER * max(weight[t] for t in span),
            "sessions_hard": sum(1 for t in span if MULTIPLIER * weight[t] >= HARD_GTE),
            "sessions_reduce_zone": sum(1 for t in span if zone[t] == "reduce"),
            "sessions_add_zone": sum(1 for t in span if zone[t] == "add"),
            "reduce_episodes": len(eps),
            "longest_episode_sessions": max((e - b + 1 for b, e in eps), default=0),
            "blocked_days": sum(1 for t in run["blocked"] if a <= t <= z),
            "sell_tickets": len(sells), "sell_fills": sum(1 for e in sells if e["filled"]),
            "buy_tickets": len(buys), "buy_fills": sum(1 for e in buys if e["filled"]),
            "sell_steps": {str(k): sum(1 for e in sells if e["step"] == k) for k in (Fraction(1, 3), Fraction(1, 2))}}


def compare(run_a: dict[str, Any], run_b: dict[str, Any], series: dict[str, Any], rate: list[float],
            a: int, z: int, cost_bp: float, names: tuple[str, str] = ("G", "U")) -> dict[str, Any]:
    """Two lines side by side in one window, each with the fixed mix of its own average weight."""
    days, close = series["days"], series["close"]
    out: dict[str, Any] = {"window": [days[a], days[z]]}
    for name, run in zip(names, (run_a, run_b)):
        out[name] = line_stats(run, days, a, z)
    for name in names:
        out[f"F_{name}"] = metrics(simulate_f(close, rate, days, a, z, out[name]["avg_weight"], cost_bp), a, z)
    out["hold"] = metrics(simulate_f(close, rate, days, a, z, 1.0, 0.0), a, z)
    out["sessions_weight_differs"] = sum(1 for t in range(a, z + 1)
                                         if abs(run_a["weight"][t] - run_b["weight"][t]) > 1e-9)
    return out


# ----------------------------------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------------------------------
def q2(r: dict[str, Any]) -> bool:
    """Drawdown: U not deeper than G."""
    return r["U"]["mdd"] >= r["G"]["mdd"] - EPS


def q3(r: dict[str, Any]) -> bool:
    """Return kept and Calmar not lower. When G's CAGR is not positive the two become CAGR(U) >= CAGR(G)
    (a Calmar comparison runs backwards below zero)."""
    g, u = r["G"], r["U"]
    if g["cagr"] > 0:
        keep = u["cagr"] >= Q3_CAGR_KEEP * g["cagr"] - EPS
        calmar = (u["calmar"] is not None and g["calmar"] is not None and u["calmar"] >= g["calmar"] - EPS)
        return bool(keep and calmar)
    return bool(u["cagr"] >= g["cagr"] - EPS)


def q4(r: dict[str, Any]) -> bool:
    """The Champion's timing value: G beats the fixed mix with G's own average weight, drawdown not deeper."""
    return bool(r["G"]["cagr"] - r["F_G"]["cagr"] > EPS and r["G"]["mdd"] >= r["F_G"]["mdd"] - EPS)


def champion_ahead(r: dict[str, Any]) -> bool:
    """Calmar(G) at least 10% above Calmar(U); when either CAGR is not positive: CAGR(G) > CAGR(U) and
    G's drawdown not deeper."""
    g, u = r["G"], r["U"]
    if g["cagr"] > 0 and u["cagr"] > 0 and g["calmar"] is not None and u["calmar"] is not None:
        return bool(g["calmar"] >= SUPPORT_CALMAR_RATIO * u["calmar"] - EPS)
    return bool(g["cagr"] - u["cagr"] > EPS and g["mdd"] >= u["mdd"] - EPS)


def judge(full10: dict[str, Any], full50: dict[str, Any], halves10: list[dict[str, Any]]) -> dict[str, Any]:
    g = full10["G"]
    gates = {
        "Q1": {"pass": bool(full10["U"]["sessions_hard"] <= g["sessions_hard"]),
               "U": full10["U"]["sessions_hard"], "G": g["sessions_hard"]},
        "Q2": {"pass": q2(full10), "U_mdd": full10["U"]["mdd"], "G_mdd": g["mdd"]},
        "Q3": {"pass": q3(full10), "U_cagr": full10["U"]["cagr"], "G_cagr": g["cagr"],
               "U_calmar": full10["U"]["calmar"], "G_calmar": g["calmar"]},
        "Q4": {"pass": all(q4(h) for h in halves10), "halves": [q4(h) for h in halves10], "full": q4(full10)},
        "Q5": {"pass": bool(q2(full50) and q3(full50)), "q2": q2(full50), "q3": q3(full50)},
        "Q6": {"pass": all(q2(h) and q3(h) for h in halves10), "halves": [[q2(h), q3(h)] for h in halves10]},
        "Q7": {"pass": bool(g["reduce_episodes"] >= Q7_EPISODES and g["blocked_days"] >= Q7_BLOCKED_DAYS),
               "episodes": g["reduce_episodes"], "blocked_days": g["blocked_days"]},
        "champion_ahead": {"pass": champion_ahead(full10)},
    }
    return gates


def verdict_of(g: dict[str, Any]) -> str:
    if not g["Q7"]["pass"]:
        return "INCONCLUSIVE"
    if all(g[k]["pass"] for k in ("Q1", "Q2", "Q3", "Q5", "Q6")):
        return "SIMPLE_CANDIDATE"
    if g["champion_ahead"]["pass"] and g["Q4"]["pass"]:
        return "CURRENT_SUPPORTED"
    return "INCONCLUSIVE"


# ----------------------------------------------------------------------------------------------
# checks on the implementation
# ----------------------------------------------------------------------------------------------
def truncation_check(core: types.SimpleNamespace, series: dict[str, Any], entry: dict[str, Any],
                     evidence: list[dict[str, Any] | None], rate: list[float], cuts: list[int], peek: int = 0) -> int:
    """No look-ahead: with the rows after a cut removed, (1) the evidence of the last sessions up to the cut,
    (2) both lines' value and weight at the cut and (3) the decision taken at the cut's close (order side,
    step, quantity, LOC price or the reason for none) are the same as in the full run."""
    n = len(series["close"])
    full = {mode: simulate(core, series, evidence, rate, mode, 10.0, peek=peek) for mode in ("G", "U")}
    for cut in cuts:
        if not WARMUP < cut < n - 1:
            raise Stop("STOP: truncation cut outside the run")
        part = {key: (vals[:cut + 1] if isinstance(vals, list) else vals) for key, vals in series.items()}
        back = max(WARMUP, cut - 4)
        ev2 = evidence_track(core, part, entry, back)
        if ev2[back:cut + 1] != evidence[back:cut + 1]:
            raise Stop(f"STOP: evidence changes when later rows are removed (cut {series['days'][cut]})")
        for mode in ("G", "U"):
            run = simulate(core, part, evidence[:cut + 1], rate[:cut + 1], mode, 10.0, decide_last=True, peek=peek)
            if (abs(run["value"][cut] / full[mode]["value"][cut] - 1.0) > 1e-12
                    or abs(run["weight"][cut] - full[mode]["weight"][cut]) > 1e-12):
                raise Stop(f"STOP: truncated {mode} run differs at cut {series['days'][cut]}")
            if run["last_decision"] != full[mode]["decisions"][cut]:
                raise Stop(f"STOP: {mode} decision at {series['days'][cut]} changes when later rows are removed")
    return len(cuts)


def truncation_cuts(g: dict[str, Any], u: dict[str, Any], days: list[str], a: int, z: int) -> list[int]:
    """Where the truncation check cuts, by a rule fixed before the run: five sessions into the judged window,
    the seven inner eighths of it, and for each line (10bp) its first, middle and last sell-order day, its
    first buy-order day and its first blocked day. Order days matter: away from them the decision at the cut
    is 'nothing to do' in both runs and a look-ahead in the sizing would not show."""
    index = {day: i for i, day in enumerate(days)}
    cuts = {a + 5} | {a + (z - a) * k // 8 for k in range(1, 8)}
    for run in (g, u):
        sells = [index[e["day"]] for e in run["events"] if e["side"] == "sell"]
        buys = [index[e["day"]] for e in run["events"] if e["side"] == "buy"]
        if sells:
            cuts |= {sells[0], sells[len(sells) // 2], sells[-1]}
        cuts |= set(buys[:1]) | set(run["blocked"][:1])
    return sorted(t for t in cuts if a <= t < z)


def evidence_summary_table(evidence: list[dict[str, Any] | None], a: int, z: int) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    count: dict[str, int] = {}
    combos: dict[str, int] = {}
    for t in range(a, z + 1):
        ev = evidence[t]
        for kind in ev["kinds"]:
            kinds[kind] = kinds.get(kind, 0) + 1
        key = str(min(len(ev["kinds"]), 3)) if len(ev["kinds"]) < 3 else "3+"
        count[key] = count.get(key, 0) + 1
        if ev["basis_met"]:
            combo = "+".join(ev["kinds"])
            combos[combo] = combos.get(combo, 0) + 1
    return {"sessions": z - a + 1, "sessions_by_kind": kinds, "sessions_by_number_of_kinds": count,
            "basis_met_sessions": sum(1 for t in range(a, z + 1) if evidence[t]["basis_met"]),
            "common_only_sessions": sum(1 for t in range(a, z + 1) if evidence[t]["common_only"]),
            "basis_met_combinations": combos}


# ----------------------------------------------------------------------------------------------
# the run
# ----------------------------------------------------------------------------------------------
def compute(root: Path, pins: dict[str, tuple[str, str]], contract: dict[str, Any],
            refs: tuple[tuple[str, float], ...] = IDENTITY_REFS) -> dict[str, Any]:
    pinned = check_pins(root, pins)
    core = load_core(root, pins)
    entry = registry_entry(root, pins)
    rates = load_rates(root / pins["dgs3mo"][0])
    raw = load_kiwoom(root / pins["soxl"][0])
    source = source_record_check(root, pins, len(raw), raw[0]["day"], raw[-1]["day"])
    series, info = prepare(raw, SYMBOL)
    info["identity"] = identity_check(series, refs, IDENTITY_TOL)
    info["source_record"] = source
    days, close, n = series["days"], series["close"], len(series["days"])
    rate = session_rates(days, rates)
    zero = session_rates(days, rates, zero=True)

    evidence = evidence_track(core, series, entry, WARMUP)
    a, z = WARMUP + 1, n - 1
    h1 = window(days, days[a], (date.fromisoformat(HALF_SPLIT) - timedelta(days=1)).isoformat(), a)
    h2 = window(days, HALF_SPLIT, days[z], a)
    for lo, hi in (h1, h2):
        if hi - lo + 1 < MIN_HALF_SESSIONS:
            raise Stop("STOP: a half of the judged window is shorter than 504 sessions")
    if h1[1] + 1 != h2[0]:
        raise Stop("STOP: the halves do not tile the judged window")

    runs: dict[tuple[str, float], dict[str, Any]] = {}
    for mode in ("G", "U"):
        for cost in COSTS:
            runs[(mode, cost)] = simulate(core, series, evidence, rate, mode, cost)
    cuts = truncation_cuts(runs[("G", 10.0)], runs[("U", 10.0)], days, a, z)
    checks = {"truncation_cuts": truncation_check(core, series, entry, evidence, rate, cuts),
              "truncation_cut_days": [days[t] for t in cuts],
              "evidence_sessions": sum(1 for e in evidence if e is not None)}
    full10 = compare(runs[("G", 10.0)], runs[("U", 10.0)], series, rate, a, z, 10.0)
    full50 = compare(runs[("G", 50.0)], runs[("U", 50.0)], series, rate, a, z, 50.0)
    halves10 = [compare(runs[("G", 10.0)], runs[("U", 10.0)], series, rate, lo, hi, 10.0) for lo, hi in (h1, h2)]
    gates = judge(full10, full50, halves10)
    verdict = verdict_of(gates)

    def variant(mode_a: str, mode_b: str, rt: list[float], loc: bool = True, cost: float = 10.0) -> dict[str, Any]:
        ra = simulate(core, series, evidence, rt, mode_a, cost, loc)
        rb = simulate(core, series, evidence, rt, mode_b, cost, loc)
        return compare(ra, rb, series, rt, a, z, cost, names=(mode_a, mode_b))

    g10, u10 = runs[("G", 10.0)], runs[("U", 10.0)]
    by_year = {}
    for year in sorted({day[:4] for day in days[a:z + 1]}):
        lo = max(bisect.bisect_left(days, f"{year}-01-01"), a)
        hi = min(bisect.bisect_left(days, f"{int(year) + 1}-01-01") - 1, z)
        by_year[year] = {"sessions": hi - lo + 1, "SOXL": close[hi] / close[lo - 1] - 1.0,
                         **{f"{name}_return": run["value"][hi] / run["value"][lo - 1] - 1.0
                            for name, run in (("G", g10), ("U", u10))},
                         **{f"{name}_avg_exposure": MULTIPLIER * math.fsum(run["weight"][lo:hi + 1]) / (hi - lo + 1)
                            for name, run in (("G", g10), ("U", u10))}}
    eps = episodes(g10["zone"], a, z)
    blocked = set(g10["blocked"])
    sold = {e["day"] for e in g10["events"] if e["side"] == "sell"}
    u_sold = {e["day"]: e["filled"] for e in u10["events"] if e["side"] == "sell"}
    blocked_in = [t for t in g10["blocked"] if a <= t <= z]
    report = {
        "by_year_10bp": by_year,
        "G_blocked_days_with_U_sell_ticket": sum(1 for t in blocked_in if days[t] in u_sold),
        "G_blocked_days_with_U_sell_filled": sum(1 for t in blocked_in if u_sold.get(days[t]) is True),
        "evidence": evidence_summary_table(evidence, a, z),
        "blocked_days_by_kinds": _count(["+".join(evidence[t]["kinds"]) or "none" for t in g10["blocked"]
                                         if a <= t <= z]),
        "blocked_days_by_year": _count([days[t][:4] for t in g10["blocked"] if a <= t <= z]),
        "no_ticket_reasons": {f"{mode}_{int(cost)}": runs[(mode, cost)]["no_ticket"]
                              for mode in ("G", "U") for cost in COSTS},
        "unfilled": {f"{mode}_{int(cost)}": runs[(mode, cost)]["unfilled"] for mode in ("G", "U") for cost in COSTS},
        "G_episodes": [{"first": days[b], "last": days[e], "sessions": e - b + 1,
                        "max_exposure": MULTIPLIER * max(g10["weight"][t] for t in range(b, e + 1)),
                        "blocked_days": sum(1 for t in range(b, e + 1) if t in blocked),
                        "sell_tickets": sum(1 for t in range(b, e + 1) if days[t] in sold)} for b, e in eps],
        "events": {mode: [{**e, "exposure": round(e["exposure"], 4)} for e in runs[(mode, 10.0)]["events"]]
                   for mode in ("G", "U")},
        "variant_G_vs_H_hard_ceiling_only": variant("G", "H", rate),
        "variant_GH_gate_with_flat_half_vs_U": variant("GH", "U", rate),
        "variant_no_loc_price": variant("G", "U", rate, loc=False),
        "variant_zero_cash_interest": variant("G", "U", zero),
    }
    return {"contract": contract, "pinned": pinned, "inputs": info, "checks": checks,
            "design": {"symbol": SYMBOL, "multiplier": MULTIPLIER, "target_weight": float(target_weight()),
                       "reduce_gte": REDUCE_GTE, "hard_gte": HARD_GTE, "add_lte": ADD_LTE, "warmup": WARMUP,
                       "account_opens": days[WARMUP], "judged_window": [days[a], days[z]],
                       "halves": [[days[lo], days[hi]] for lo, hi in (h1, h2)], "costs_bp": list(COSTS),
                       "card_triggers": [{k: trig.get(k) for k in ("id", "kind", "side", "strength", "params")}
                                         for trig in entry["card_triggers"]]},
            "gates": gates, "verdict": verdict,
            "judged": {"full_10bp": full10, "full_50bp": full50, "halves_10bp": halves10},
            "report_only": report}


def _count(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items()))


def run_all(root: Path, out_path: Path, pins: dict[str, tuple[str, str]] = PINS, runner: Path | None = None,
            prereg: str = PREREG, sidecar: str = PREREG_SIDECAR,
            refs: tuple[tuple[str, float], ...] = IDENTITY_REFS, prior_stops: list[dict[str, Any]] | None = None,
            label: str = "VERDICT") -> int:
    if out_path.exists():
        raise ResultExists(f"refused: {out_path} exists (one run only)")
    contract = check_contract(root, runner, prereg, sidecar)
    body = compute(root, pins, contract, refs)
    doc = {"generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
           "environment": {"python": platform.python_version(), "platform": platform.platform()},
           "prior_stop_records": list(prior_stops or []), **body}
    text = json.dumps(clean(doc), ensure_ascii=False, indent=1, allow_nan=False)
    if out_path.exists():
        raise ResultExists(f"refused: {out_path} exists (one run only)")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    g = doc["gates"]
    print(label, doc["verdict"], {k: g[k]["pass"] for k in sorted(g)})
    return 0


def guarded(root: Path, pins: dict[str, tuple[str, str]] = PINS, runner: Path | None = None,
            prereg: str = PREREG, sidecar: str = PREREG_SIDECAR, results: str = RESULTS_JSON,
            stops: str = STOP_DIR, refs: tuple[tuple[str, float], ...] = IDENTITY_REFS,
            label: str = "VERDICT") -> int:
    """The one real run. 0 = results written, 1 = STOP (a record is left), 2 = results already there,
    3 = a STOP record later than the last lock / amendment (amend section 10 of the contract first).
    Any other failure (an unexpected error, an interrupt, SIGTERM) also leaves a STOP record and is raised
    again. Only a kill that Python cannot see (SIGKILL, power loss) ends a run with neither a results file nor
    a record; the pre-registration treats that as a STOP by procedure (section 2-3)."""
    stop_dir = root / stops
    try:
        side = (root / sidecar).read_text(encoding="utf-8")
        times = [datetime.fromisoformat(ln.split()[1]) for ln in side.splitlines()
                 if len(ln.split()) >= 2 and ln.split()[0] in ("fixed_at", "amended_at")]
        last_lock = max(times) if times and all(t.tzinfo is not None for t in times) else None
    except (OSError, ValueError):
        last_lock = None                     # run_all stops on the broken sidecar and leaves a record
    prior = []
    if stop_dir.exists():
        for p in sorted(stop_dir.glob(f"{STOP_PREFIX}*.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            when = datetime.fromisoformat(rec["stopped_at_kst"])
            if last_lock is None or when > last_lock:
                print(f"refused: STOP record {p.name} is later than the last lock/amendment (amend section 10 first)")
                return 3
            prior.append({"record": p.name, "stopped_at_kst": rec["stopped_at_kst"], "reason": rec["reason"]})

    def record(reason: str) -> None:
        stop_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(KST)
        rec = stop_dir / f"{STOP_PREFIX}{now.strftime('%Y%m%dT%H%M%S%f')}.json"
        with open(rec, "x", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"stopped_at_kst": now.isoformat(timespec="seconds"), "reason": reason},
                                ensure_ascii=False, indent=1) + "\n")

    def on_term(signum: int, frame: Any) -> None:
        raise SystemExit(f"signal {signum}")

    try:
        signal.signal(signal.SIGTERM, on_term)           # a tool timeout sends SIGTERM: leave a record too
    except ValueError:                                   # not the main thread
        pass
    try:
        return run_all(root, root / results, pins, runner, prereg, sidecar, refs, prior, label)
    except ResultExists as exc:
        print(str(exc))
        return 2
    except Stop as exc:
        record(str(exc))
        print(str(exc))
        return 1
    except BaseException as exc:             # noqa: BLE001 - nothing may end the run without a trace
        record(f"UNEXPECTED {type(exc).__name__}: {exc}")
        raise


# ----------------------------------------------------------------------------------------------
# self-test (synthetic data only)
# ----------------------------------------------------------------------------------------------
def _synthetic_rows(seed: int, n: int, start: float = 40.0, drift: float = 0.0012, vol: float = 0.045
                    ) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    day = date(2014, 1, 2)
    rows, price = [], start
    while len(rows) < n:
        if day.weekday() < 5:
            prev = price
            price = prev * math.exp(rng.gauss(drift, vol))
            op = prev * math.exp(rng.gauss(0.0, vol / 3))
            high = max(op, price) * (1 + abs(rng.gauss(0, vol / 4)))
            low = min(op, price) * (1 - abs(rng.gauss(0, vol / 4)))
            rows.append({"day": day.isoformat(), "open": op, "high": high, "low": low, "close": price,
                         "volume": float(rng.randint(1_000_000, 9_000_000)), "upd_tp": "", "upd_rt": ""})
        day += timedelta(days=1)
    return rows


def _payload(rows: list[dict[str, Any]], placeholders: int = 0) -> dict[str, Any]:
    out = []
    first = date.fromisoformat(rows[0]["day"])
    k, day = 0, first
    while k < placeholders:
        day -= timedelta(days=1)
        if day.weekday() < 5:
            p = f"{rows[0]['open']:.4f}"
            out.append({"dt": day.strftime("%Y%m%d"), "open_pric": p, "high_pric": p, "low_pric": p, "cur_prc": p,
                        "acc_trde_qty": "0"})
            k += 1
    for r in rows:
        out.append({"dt": r["day"].replace("-", ""), "open_pric": f"{r['open']:.4f}", "high_pric": f"{r['high']:.4f}",
                    "low_pric": f"{r['low']:.4f}", "cur_prc": f"{r['close']:.4f}", "acc_trde_qty": str(int(r["volume"])),
                    "upd_stkpc_tp": r.get("upd_tp", ""), "upd_rt": r.get("upd_rt", "")})
    out.sort(key=lambda r: r["dt"], reverse=True)
    return {"result": {"return_code": 0, "return_msg": "", "result_list": out}}


def self_test(root: Path) -> None:
    pins = {k: PINS[k] for k in ("core_rules", "core_tickets", "exposure", "registry")}
    check_pins(root, pins)
    core = load_core(root, pins)
    entry = registry_entry(root, pins)
    tickets = core.tickets
    assert target_weight() == Decimal("0.516") and MULTIPLIER * float(target_weight()) <= float(TARGET_E)

    # --- data preparation
    rows = _synthetic_rows(3, 1500)
    series, info = prepare(rows, "SYN")
    assert info["rows"] == 1499 and info["provisional_row_dropped"] == rows[-1]["day"]
    def scaled(factor: float, flag: str = "") -> list[dict[str, Any]]:
        """Rows 700.. multiplied by `factor` (an event the vendor did not adjust), row 700 optionally flagged."""
        out = [dict(r) for r in rows]
        for r in out[700:]:
            for key in ("open", "high", "low", "close"):
                r[key] *= factor
        out[700]["upd_tp"], out[700]["upd_rt"] = ("3231", flag) if flag else ("", "")
        return out
    day_move = rows[700]["close"] / rows[699]["close"]
    exact3 = [dict(r) for r in rows]
    exact3[700]["close"] = exact3[699]["close"] / 3.0
    weekend = [dict(r) for r in rows]
    weekend[5]["day"] = "2014-01-11"
    negative = [dict(r) for r in rows]
    negative[300]["low"] = 0.0
    garbled = scaled(1.0, "n/a")
    for broken in (exact3, rows[:400] + rows[420:], rows[:WARMUP + 2 * MIN_HALF_SESSIONS - 1],
                   scaled(0.45 / day_move), scaled(2.2 / day_move),          # beyond the core's split guard
                   scaled(0.5 * 1.03 / day_move, "-50.00000"),               # flagged 2:1, not adjusted, +3% day
                   scaled(1.0 / 15 * 0.96 / day_move, "-93.33333"),          # (also beyond the guard)
                   weekend, negative, garbled):
        try:
            prepare(broken, "SYN")
            raise AssertionError("bad data did not stop")
        except Stop:
            pass
    ok_flag, info_flag = prepare(scaled(1.0, "-50.00000"), "SYN")           # flagged and adjusted: kept, reported
    assert info_flag["adjustment_flag_rows"] == [{"day": rows[700]["day"], "upd_stkpc_tp": "3231", "upd_rt": -50.0,
                                                  "close_ratio": day_move}]
    hole, info_hole = prepare(scaled(0.5 * 1.03 / day_move), "SYN")         # the known hole: unflagged, 0.515
    assert info_hole["extreme_close_ratios"] and info_hole["extreme_close_ratios"][0][0] == rows[700]["day"]
    assert info_hole["min_close_ratio"][0] == rows[700]["day"] and not info["extreme_close_ratios"]
    assert info["zero_volume_days"] == [] and info["adjustment_flag_rows"] == []
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "k.json"
        f.write_text(json.dumps(_payload(rows[:50])), encoding="utf-8")
        assert [r["day"] for r in load_kiwoom(f)] == [r["day"] for r in rows[:50]]
        dup = _payload(rows[:50])
        dup["result"]["result_list"].append(dict(dup["result"]["result_list"][3]))
        empty = _payload(rows[:50])
        empty["result"]["result_list"][7]["cur_prc"] = ""
        code = _payload(rows[:50])
        code["result"]["return_code"] = 7
        for payload in (dup, empty, code):
            f.write_text(json.dumps(payload), encoding="utf-8")
            try:
                load_kiwoom(f)
                raise AssertionError("bad file did not stop")
            except Stop:
                pass
    try:
        identity_check(series, ((series["days"][10], series["close"][10] * 1.05),), IDENTITY_TOL)
        raise AssertionError("identity check did not stop")
    except Stop:
        pass
    assert identity_check(series, ((series["days"][10], series["close"][10] * 1.01),), IDENTITY_TOL)

    # --- evidence: the pinned ladder, and an independent recount of the hit groups
    n = len(series["close"])
    evidence = evidence_track(core, series, entry, WARMUP)
    full = core.rules.build_series(core_bars(series)["adjusted"], series["days"], series["days"][-1])
    assert full["days"] == series["days"]
    for t in range(WARMUP, n):
        ev = evidence[t]
        assert ev["sigma60"] == full["sigma60"][t]
        assert ev["r_max"] in (Fraction(0), Fraction(1, 3), Fraction(1, 2))
        assert set(ev["kinds"]) <= {"overheat", "overheat_fade", "trend_break", "false_breakout", "new_low",
                                    "rebound_fail"}
        assert ev["r_max"] == (Fraction(0) if len(ev["kinds"]) < 2 else
                               Fraction(1, 2) if "trend_break" in ev["kinds"] else Fraction(1, 3))
        assert ("C3-" not in ev["ids"]) and (("trend_break" in ev["kinds"]) == bool({"S4", "S5"} & set(ev["ids"])))
    seen = {k for e in evidence[WARMUP:] for k in e["kinds"]}
    assert {"overheat", "trend_break", "new_low"} <= seen, seen
    assert any(e["basis_met"] for e in evidence[WARMUP:]) and any(e["common_only"] for e in evidence[WARMUP:])
    # trend_break state from first principles (S4: two closes in a row under EMA20; S5: three under EMA50)
    def run_below(line: list[float | None], t: int) -> int | None:
        """Closes in a row under the line ending at t; None when the run reaches back to where the line starts
        (the core calls that unknown, not hit)."""
        k = t
        while k >= 0 and line[k] is not None and full["close"][k] < line[k] - 1e-9:
            k -= 1
        return None if k < 0 or line[k] is None else t - k
    known = 0
    for t in range(WARMUP, n):
        r20, r50 = run_below(full["ema20"], t), run_below(full["ema50"], t)
        if r20 is None or r50 is None:
            assert "trend_break" not in evidence[t]["kinds"] or (r20 is not None and r20 >= 2), series["days"][t]
            continue
        known += 1
        assert ("trend_break" in evidence[t]["kinds"]) == (r20 >= 2 or r50 >= 3), series["days"][t]
    assert known > 0.9 * (n - WARMUP)
    for t in range(WARMUP, n):
        over = full["rsi14"][t] >= 70 - 1e-9 or full["close"][t] >= full["ema20"][t - 1] + 2.0 * full["atr14"][t - 1] - 1e-9
        assert ("overheat" in evidence[t]["kinds"]) == over, series["days"][t]

    # --- engine
    rate = [0.0001] * n
    g = simulate(core, series, evidence, rate, "G", 10.0)
    u = simulate(core, series, evidence, rate, "U", 10.0)
    a, z = WARMUP + 1, n - 1
    assert abs(MULTIPLIER * g["weight"][WARMUP] - 1.548) < 1e-3 and g["value"][WARMUP] == EQUITY0
    assert not u["blocked"] and "BASIS_NOT_MET" not in u["no_ticket"]
    assert g["blocked"] and g["no_ticket"]["BASIS_NOT_MET"] == len(g["blocked"])
    assert all(evidence[t]["r_max"] == 0 and g["zone"][t] == "reduce" for t in g["blocked"])
    index = {day: i for i, day in enumerate(series["days"])}
    for run in (g, u):
        assert any(e["side"] == "sell" for e in run["events"]) and any(e["side"] == "buy" for e in run["events"])
        for e in run["events"]:
            t = index[e["day"]]
            assert run["zone"][t] == ("reduce" if e["side"] == "sell" else "add")
            assert e["filled"] in (True, False)
            w0, w1 = run["weight"][t], run["weight"][t + 1]
            drift_only = w0 * (series["close"][t + 1] / series["close"][t]) / (
                w0 * (series["close"][t + 1] / series["close"][t]) + (1 - w0) * (1 + rate[t + 1]))
            if e["side"] == "sell":
                floor = series["close"][t] * (1 - evidence[t]["sigma60"])
                assert e["filled"] == (series["close"][t + 1] >= floor * (1 - EPS))
                assert (w1 < drift_only - 1e-6) == e["filled"]
                assert e["step"] <= (U_R_MAX if run is u else evidence[t]["r_max"])
            else:
                cap = series["close"][t] * (1 + 0.5 * evidence[t]["sigma60"])
                assert e["filled"] == (series["close"][t + 1] <= cap * (1 + EPS))
                assert (w1 > drift_only + 1e-6) == e["filled"]
            if not e["filled"]:
                assert abs(w1 - drift_only) < 1e-9
    assert sum(1 for e in g["events"] if e["filled"] is False) == sum(g["unfilled"].values()) > 0
    # a filled 1/2 sell from just above the band lands about halfway to the target
    halves = [(run["weight"][index[e["day"]]], run["weight"][index[e["day"]] + 1], index[e["day"]])
              for run in (u,) for e in run["events"] if e["side"] == "sell" and e["filled"] and e["step"] == U_R_MAX]
    assert halves
    for w0, w1, t in halves:
        r = series["close"][t + 1] / series["close"][t]
        shares0 = w0                                  # per unit of equity at t (price normalised to 1)
        sold = 0.5 * (w0 - float(target_weight()))
        expect = (shares0 - sold) * r / ((shares0 - sold) * r + (1 - w0) * (1 + rate[t + 1]) + sold * r * (1 - 0.001))
        assert abs(w1 - expect) < 2e-5, (w0, w1, expect)
        no_cost = (shares0 - sold) * r / ((shares0 - sold) * r + (1 - w0) * (1 + rate[t + 1]) + sold * r)
        assert abs(w1 - no_cost) > abs(w1 - expect)          # the cost is in the cash
    # the same ceiling on every session makes G and U the same line
    forced = [None if e is None else {**e, "r_max": U_R_MAX, "basis_met": True} for e in evidence]
    gf = simulate(core, series, forced, rate, "G", 10.0)
    assert gf["value"] == u["value"] and gf["events"] == u["events"] and not gf["blocked"]
    never = [None if e is None else {**e, "r_max": Fraction(0), "basis_met": False} for e in evidence]
    gn = simulate(core, series, never, rate, "G", 10.0)
    assert not any(e["side"] == "sell" for e in gn["events"])
    assert simulate(core, series, never, rate, "U", 10.0)["value"] == u["value"]
    hh = simulate(core, series, evidence, rate, "H", 10.0)
    assert hh["blocked"] and all(MULTIPLIER * hh["weight"][t] < HARD_GTE for t in hh["blocked"])
    assert any(e["side"] == "sell" and e["exposure"] >= HARD_GTE and not evidence[index[e["day"]]]["basis_met"]
               for e in hh["events"])
    assert all(e["exposure"] >= HARD_GTE or evidence[index[e["day"]]]["basis_met"]
               for e in hh["events"] if e["side"] == "sell")
    gh = simulate(core, series, evidence, rate, "GH", 10.0)
    assert gh["blocked"] and all(not evidence[t]["basis_met"] for t in gh["blocked"])
    assert any(e["side"] == "sell" and e["step"] == U_R_MAX and evidence[index[e["day"]]]["common_only"]
               for e in gh["events"])
    assert all(e["step"] <= Fraction(1, 3) for e in g["events"]
               if e["side"] == "sell" and evidence[index[e["day"]]]["common_only"])
    # every recorded decision is an order event or a reason, and the last session places nothing
    for run in (g, u):
        placed = [t for t in range(WARMUP, n - 1) if run["decisions"][t][0] != "none"]
        assert [series["days"][t] for t in placed] == [e["day"] for e in run["events"]]
        assert run["decisions"][n - 1] is None and run["last_decision"] is None
    # a zero step from the regret table places no ticket and is counted
    keep_choose = core.tickets.choose_step
    core.tickets.choose_step = lambda table, r_max: (Fraction(0), "FORCED_ZERO")
    try:
        rz = simulate(core, series, evidence, rate, "U", 10.0)
    finally:
        core.tickets.choose_step = keep_choose
    assert not [e for e in rz["events"] if e["side"] == "sell"] and rz["no_ticket"].get("REGRET_ZERO", 0) > 0
    # cost and LOC switches
    assert simulate(core, series, evidence, rate, "U", 50.0)["value"][z] < u["value"][z]
    nl = simulate(core, series, evidence, rate, "U", 10.0, loc=False)
    assert all(e["filled"] for e in nl["events"]) and sum(nl["unfilled"].values()) == 0
    # value identity with no trades: zero cost, zero rate, evidence that never opens, band never left
    flat = {**series, "close": [50.0] * n}
    ident = simulate(core, flat, never, [0.0] * n, "G", 0.0)
    assert not ident["events"] and all(abs(v - EQUITY0) < 1e-6 for v in ident["value"][WARMUP:])

    # --- fixed mix and metrics
    close, days = series["close"], series["days"]
    f1 = simulate_f(close, rate, days, a, z, 1.0, 0.0)
    assert abs(f1[z] - close[z] / close[a - 1]) < 1e-9
    f0 = simulate_f(close, rate, days, a, z, 0.0, 10.0)
    assert abs(f0[z] - (1.0001) ** (z - a + 1)) < 1e-9
    stock, cash_, v = 0.55, 0.45, None                              # w = 0.55 by hand, 10bp at each new year
    for t in range(a, z + 1):
        cash_ *= 1.0001
        stock *= close[t] / close[t - 1]
        if days[t][:4] != days[t - 1][:4]:
            total = stock + cash_
            cash_, stock = total * 0.45 - 0.001 * abs(0.55 * total - stock), 0.55 * total
        v = stock + cash_
    assert abs(simulate_f(close, rate, days, a, z, 0.55, 10.0)[z] - v) < 1e-12
    # interest lag: the observation dated before the session, never the same day
    assert session_rates(["2020-01-02", "2020-01-03", "2020-01-06"],
                         (["2019-12-31", "2020-01-02", "2020-01-03"], [1.0, 2.0, 3.0])) == [
        1.0 / 100 / YEAR, 2.0 / 100 / YEAR, 3.0 / 100 / YEAR]
    m = metrics([None, 1.0, 2.0, 1.0, 1.5], 2, 4)
    assert abs(m["mdd"] + 0.5) < 1e-12 and abs(m["total"] - 0.5) < 1e-12 and m["sessions"] == 3
    assert episodes([None, "band", "reduce", "reduce", "band", "reduce"], 1, 5) == [(2, 3), (5, 5)]
    st = line_stats(g, days, a, z)
    assert st["blocked_days"] == len([t for t in g["blocked"] if a <= t <= z]) and st["sessions"] == z - a + 1
    assert st["sell_tickets"] >= st["sell_fills"] and st["reduce_episodes"] >= 1

    # --- gates
    def row(g_cagr, g_mdd, u_cagr, u_mdd, fg_cagr=0.0, fg_mdd=-0.9, hard_g=10, hard_u=0, ep=12, blk=30):
        def m_(c, d):
            return {"cagr": c, "mdd": d, "calmar": c / abs(d)}
        return {"G": {**m_(g_cagr, g_mdd), "sessions_hard": hard_g, "reduce_episodes": ep, "blocked_days": blk},
                "U": {**m_(u_cagr, u_mdd), "sessions_hard": hard_u}, "F_G": m_(fg_cagr, fg_mdd)}
    cand = row(0.30, -0.60, 0.29, -0.50)
    assert verdict_of(judge(cand, cand, [cand, cand])) == "SIMPLE_CANDIDATE"
    assert verdict_of(judge(row(0.30, -0.60, 0.29, -0.50, ep=9), cand, [cand, cand])) == "INCONCLUSIVE"
    assert verdict_of(judge(row(0.30, -0.60, 0.29, -0.50, blk=19), cand, [cand, cand])) == "INCONCLUSIVE"
    worse_half = row(0.30, -0.60, 0.20, -0.50)
    assert verdict_of(judge(cand, cand, [cand, worse_half])) == "INCONCLUSIVE"
    assert verdict_of(judge(cand, worse_half, [cand, cand])) == "INCONCLUSIVE"
    sup = row(0.40, -0.50, 0.20, -0.50, fg_cagr=0.30, fg_mdd=-0.55)
    assert verdict_of(judge(sup, sup, [sup, sup])) == "CURRENT_SUPPORTED"
    no_timing = row(0.40, -0.50, 0.20, -0.50, fg_cagr=0.45, fg_mdd=-0.55)
    assert verdict_of(judge(sup, sup, [sup, no_timing])) == "INCONCLUSIVE"
    assert not q3(row(0.30, -0.60, 0.26, -0.50)) and q3(row(0.30, -0.60, 0.27, -0.50))
    assert q3(row(-0.10, -0.60, -0.05, -0.50)) and not q3(row(-0.10, -0.60, -0.12, -0.50))
    assert not q2(row(0.3, -0.5, 0.3, -0.51)) and q2(row(0.3, -0.5, 0.3, -0.5))
    assert champion_ahead(row(0.33, -0.5, 0.30, -0.5)) and not champion_ahead(row(0.32, -0.5, 0.30, -0.5))
    assert champion_ahead(row(0.05, -0.5, -0.01, -0.5)) and not champion_ahead(row(0.05, -0.6, -0.01, -0.5))
    assert not q3(row(0.30, -0.50, 0.28, -0.50)) and q3(row(0.30, -0.50, 0.30, -0.50))     # the Calmar leg alone
    assert q4(row(0.3, -0.5, 0.3, -0.5, fg_cagr=0.2, fg_mdd=-0.5))
    assert not q4(row(0.3, -0.5, 0.3, -0.5, fg_cagr=0.2, fg_mdd=-0.45))                    # G deeper than its fixed mix
    assert not q4(row(0.3, -0.5, 0.3, -0.5, fg_cagr=0.3, fg_mdd=-0.6))                     # no return edge
    more_hard = row(0.30, -0.60, 0.29, -0.50, hard_g=3, hard_u=4)
    assert verdict_of(judge(more_hard, cand, [cand, cand])) == "INCONCLUSIVE"              # Q1 fails
    sup_small = row(0.40, -0.50, 0.20, -0.50, fg_cagr=0.30, fg_mdd=-0.55, ep=9)
    assert verdict_of(judge(sup_small, sup_small, [sup, sup])) == "INCONCLUSIVE"           # Q7 before 'supported'
    zero_dd = {"G": {"cagr": 0.3, "mdd": -0.5, "calmar": 0.6, "sessions_hard": 1, "reduce_episodes": 12,
                     "blocked_days": 30},
               "U": {"cagr": 0.4, "mdd": 0.0, "calmar": None, "sessions_hard": 0}, "F_G": {"cagr": 0.0, "mdd": -0.9}}
    assert not q3(zero_dd) and not champion_ahead(zero_dd)           # a missing Calmar never passes Q3
    assert verdict_of(judge(zero_dd, zero_dd, [zero_dd, zero_dd])) == "INCONCLUSIVE"
    m2 = metrics([None, 1.0] + [1.0 * 1.001 ** k for k in range(1, 253)], 2, 253)
    assert abs(m2["cagr"] - (1.001 ** 252 - 1)) < 1e-12 and m2["mdd"] == 0.0 and m2["calmar"] is None
    m3 = metrics([None, 2.0, 1.0, 4.0], 2, 3)
    assert abs(m3["cagr"] - (2.0 ** 126 - 1)) / (2.0 ** 126) < 1e-12 and abs(m3["calmar"] - m3["cagr"] / 0.5) < 1e-3

    # --- truncation and the whole pipeline on a synthetic tree
    assert truncation_check(core, series, entry, evidence, rate, [WARMUP + 6, 400, 900, n - 2]) == 4
    rule = truncation_cuts(g, u, series["days"], a, z)
    assert {index[u["events"][0]["day"]], index[g["events"][0]["day"]], g["blocked"][0], a + 5} <= set(rule)
    assert rule == sorted(set(rule)) and all(a <= t < z for t in rule)
    assert truncation_check(core, series, entry, evidence, rate, rule) == len(rule)
    bug_runs = [simulate(core, series, evidence, rate, mode, 10.0, peek=1) for mode in ("G", "U")]
    try:                                     # the run's own cut rule sees the look-ahead bug (order-day cuts)
        truncation_check(core, series, entry, evidence, rate, truncation_cuts(*bug_runs, series["days"], a, z),
                         peek=1)
        raise AssertionError("the run's cut rule did not see a look-ahead decision")
    except Stop as exc:
        assert "decision" in str(exc)
    bug = bug_runs[1]
    orders_at = [t for t in range(WARMUP + 1, n - 1) if bug["decisions"][t] and bug["decisions"][t][0] != "none"]
    assert len(orders_at) >= 3
    try:                                     # negative control: a one-session look-ahead in the decision
        truncation_check(core, series, entry, evidence, rate, orders_at[:3], peek=1)
        raise AssertionError("the truncation check did not see a look-ahead decision")
    except Stop as exc:
        assert "decision" in str(exc)
    shifted = evidence[:WARMUP] + evidence[WARMUP + 1:] + [evidence[-1]]      # tomorrow's evidence used today
    try:
        truncation_check(core, series, entry, shifted, rate, [400])
        raise AssertionError("the truncation check did not see shifted evidence")
    except Stop as exc:
        assert "evidence" in str(exc)
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        for key in ("core_rules", "core_tickets", "exposure", "registry"):
            dst = troot / PINS[key][0]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / PINS[key][0], dst)
        long_rows = _synthetic_rows(11, 2400, drift=0.0015)
        price = troot / PINS["soxl"][0]
        price.parent.mkdir(parents=True, exist_ok=True)
        price.write_text(json.dumps(_payload(long_rows, placeholders=3)), encoding="utf-8")
        srec = troot / PINS["sources"][0]
        first_placeholder = min(r["dt"] for r in _payload(long_rows, 3)["result"]["result_list"])
        srec.write_text(json.dumps({"files": [{
            "ticker": SYMBOL, "exchange": "NYSE", "called_kst": "test", "file": "kiwoom_raw/" + price.name,
            "sha256": sha256_file(price), "rows": len(long_rows) + 3,
            "first": f"{first_placeholder[:4]}-{first_placeholder[4:6]}-{first_placeholder[6:]}",
            "last": long_rows[-1]["day"]}]}), encoding="utf-8")
        rpath = troot / PINS["dgs3mo"][0]
        rpath.parent.mkdir(parents=True, exist_ok=True)
        rpath.write_text("observation_date,DGS3MO\n2013-12-02,1.50\n2013-12-03,.\n2016-06-01,3.00\n", encoding="utf-8")
        tpins = {**PINS, "soxl": (PINS["soxl"][0], sha256_file(price)), "sources": (PINS["sources"][0], sha256_file(srec)),
                 "dgs3mo": (PINS["dgs3mo"][0], sha256_file(rpath))}
        refs = ((long_rows[100]["day"], float(f"{long_rows[100]['close']:.4f}")),)
        (troot / "docs/claude").mkdir(parents=True, exist_ok=True)
        (troot / "docs/claude/p.md").write_text("contract", encoding="utf-8")
        me = Path(__file__).resolve()

        def lock(raw: str, runner_sha: str, extra: str = "", fixed: str = "2026-11-01T12:00:00+09:00") -> None:
            (troot / "docs/claude/p.sha256").write_text(
                f"raw_sha256 {raw}\nrunner_sha256 {runner_sha}\nfixed_at {fixed}\n{extra}", encoding="utf-8")
        good_raw = hashlib.sha256(b"contract").hexdigest()
        out = troot / "docs/claude/out.json"
        for raw_sha, rsha, extra, fixed in (
                (good_raw[::-1], sha256_file(me), "", None), (good_raw, "0" * 64, "", None),
                (good_raw, sha256_file(me), "fixed_at 2026-11-01T13:00:00+09:00\n", None),
                (good_raw, sha256_file(me), "amended_at 2026-11-01T11:00:00+09:00\n", None),
                (good_raw, sha256_file(me), "", "2026-11-01T12:00:00"),
                (good_raw, sha256_file(me), "", "2099-01-01T00:00:00+09:00"),            # a lock in the future
                (good_raw, sha256_file(me), "amended_at 2026-11-02T12:00:00+09:00\n", None),  # not in the document
                (good_raw, sha256_file(me), "", "yesterday")):
            lock(raw_sha, rsha, extra, *(() if fixed is None else (fixed,)))
            try:
                run_all(troot, out, tpins, me, "docs/claude/p.md", "docs/claude/p.sha256", refs, label="SELF-TEST")
                raise AssertionError("contract guard did not stop")
            except Stop:
                pass
        lock(good_raw, sha256_file(me))
        wrong_record = json.loads(srec.read_text(encoding="utf-8"))
        wrong_record["files"][0]["rows"] += 1
        srec.write_text(json.dumps(wrong_record), encoding="utf-8")
        try:                                 # the source record disagrees with the file
            run_all(troot, out, {**tpins, "sources": (tpins["sources"][0], sha256_file(srec))}, me,
                    "docs/claude/p.md", "docs/claude/p.sha256", refs)
            raise AssertionError("source record guard did not stop")
        except Stop as exc:
            assert "source record" in str(exc)
        wrong_record["files"][0]["rows"] -= 1
        srec.write_text(json.dumps(wrong_record), encoding="utf-8")
        tpins["sources"] = (tpins["sources"][0], sha256_file(srec))
        for key in ("dgs3mo", "core_rules", "core_tickets", "exposure", "registry", "sources", "soxl"):
            try:
                run_all(troot, out, {**tpins, key: (tpins[key][0], "0" * 64)}, me, "docs/claude/p.md",
                        "docs/claude/p.sha256", refs)
                raise AssertionError("pin guard did not stop")
            except Stop:
                pass
        try:
            run_all(troot, out, tpins, me, "docs/claude/p.md", "docs/claude/p.sha256",
                    ((refs[0][0], refs[0][1] * 1.2),))
            raise AssertionError("identity guard did not stop")
        except Stop:
            pass
        assert not out.exists()
        assert run_all(troot, out, tpins, me, "docs/claude/p.md", "docs/claude/p.sha256", refs,
                       label="SELF-TEST synthetic (not a result)") == 0
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["prior_stop_records"] == [] and 8 <= doc["checks"]["truncation_cuts"] == len(doc["checks"]["truncation_cut_days"]) <= 17
        ro = doc["report_only"]
        assert set(ro["variant_G_vs_H_hard_ceiling_only"]) >= {"G", "H", "F_G", "F_H", "hold"}
        assert set(ro["variant_GH_gate_with_flat_half_vs_U"]) >= {"GH", "U", "F_GH", "F_U"}
        assert ro["variant_G_vs_H_hard_ceiling_only"]["G"] == doc["judged"]["full_10bp"]["G"]
        assert ro["variant_GH_gate_with_flat_half_vs_U"]["U"] == doc["judged"]["full_10bp"]["U"]
        assert 0 < doc["judged"]["full_10bp"]["sessions_weight_differs"] <= doc["judged"]["full_10bp"]["G"]["sessions"]
        assert 0 <= ro["G_blocked_days_with_U_sell_filled"] <= ro["G_blocked_days_with_U_sell_ticket"] <= doc[
            "judged"]["full_10bp"]["G"]["blocked_days"]
        for key in ("EQUITY", "qty", "shares", "limit"):
            assert key not in out.read_text(encoding="utf-8")
        assert doc["verdict"] in ("SIMPLE_CANDIDATE", "CURRENT_SUPPORTED", "INCONCLUSIVE")
        assert doc["inputs"]["placeholders_dropped"] == 3 and doc["inputs"]["rows"] == 2399
        assert doc["design"]["account_opens"] == long_rows[WARMUP]["day"]
        assert doc["design"]["judged_window"] == [long_rows[WARMUP + 1]["day"], long_rows[-2]["day"]]
        assert doc["design"]["halves"][0][1] < HALF_SPLIT <= doc["design"]["halves"][1][0]
        j = doc["judged"]["full_10bp"]
        assert j["G"]["sessions"] == j["U"]["sessions"] == 2399 - WARMUP - 1
        assert j["U"]["blocked_days"] == 0 and j["G"]["blocked_days"] == sum(doc["report_only"]["blocked_days_by_year"].values())
        assert sum(h["G"]["sessions"] for h in doc["judged"]["halves_10bp"]) == j["G"]["sessions"]
        assert doc["report_only"]["variant_no_loc_price"]["G"]["sell_tickets"] == doc["report_only"]["variant_no_loc_price"]["G"]["sell_fills"]
        assert "10000000" not in out.read_text(encoding="utf-8")
        years = doc["report_only"]["by_year_10bp"]
        assert sum(y["sessions"] for y in years.values()) == j["G"]["sessions"]
        total = 1.0
        for y in years.values():
            total *= 1.0 + y["G_return"]
        assert abs(total - 1.0 - j["G"]["total"]) < 1e-9
        try:
            run_all(troot, out, tpins, me, "docs/claude/p.md", "docs/claude/p.sha256", refs)
            raise AssertionError("second run was not refused")
        except ResultExists:
            pass
        kw = dict(runner=me, prereg="docs/claude/p.md", sidecar="docs/claude/p.sha256",
                  results="docs/claude/guarded.json", stops="docs/claude/stops", refs=refs,
                  label="SELF-TEST synthetic (not a result)")
        stop_glob = lambda d="stops": sorted((troot / "docs/claude" / d).glob(f"{STOP_PREFIX}*.json"))   # noqa: E731
        # an unexpected error (here: a pin missing from the table) leaves a record too, and is raised again
        try:
            guarded(troot, {k: v for k, v in tpins.items() if k != "registry"}, **kw)
            raise AssertionError("unexpected error was swallowed")
        except KeyError:
            pass
        assert len(stop_glob()) == 1 and "UNEXPECTED KeyError" in json.loads(
            stop_glob()[0].read_text(encoding="utf-8"))["reason"]
        assert guarded(troot, tpins, **kw) == 3                       # blocked until an amendment
        assert not (troot / "docs/claude/guarded.json").exists() and len(stop_glob()) == 1
        time.sleep(1.2)
        amended = datetime.now(KST).isoformat(timespec="seconds")
        lock(good_raw, sha256_file(me), f"amended_at {amended}\n")
        assert guarded(troot, tpins, **kw) == 1                       # sidecar amended, document not: a new STOP
        assert len(stop_glob()) == 2
        time.sleep(1.2)
        amended = datetime.now(KST).isoformat(timespec="seconds")
        (troot / "docs/claude/p.md").write_text(f"contract\n- amended {amended}: reason\n", encoding="utf-8")
        lock(sha256_file(troot / "docs/claude/p.md"), sha256_file(me), f"amended_at {amended}\n")
        assert guarded(troot, tpins, **kw) == 0                       # amended in both: the run goes through
        done = json.loads((troot / "docs/claude/guarded.json").read_text(encoding="utf-8"))
        assert done["gates"] == doc["gates"] and len(done["prior_stop_records"]) == 2
        assert guarded(troot, tpins, **kw) == 2                       # results already there
        assert len(stop_glob()) == 2
        kw2 = {**kw, "results": "docs/claude/guarded2.json", "stops": "docs/claude/stops2"}
        assert guarded(troot, {**tpins, "dgs3mo": (tpins["dgs3mo"][0], "0" * 64)}, **kw2) == 1   # a plain STOP
        assert len(stop_glob("stops2")) == 1 and guarded(troot, tpins, **kw2) == 3
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
