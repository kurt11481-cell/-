#!/usr/bin/env python3
"""Protocol-locked SOXL/SOXX five-year walk-forward research.

This program is historical research only.  It never reads or changes broker
state, never infers a fill, and never places or schedules an order.  Completed
close signals are simulated at the next valid regular-session raw open.  A
missing/invalid open freezes the pending review instead of inventing a fill.

The pre-result contract is SOXL_WALK_FORWARD_PROTOCOL_2026-08-05.md.  The
fixed revised-simple defaults are two-close rearm, 100% restoration of one
previously sold slot, active policy RVOL rules, no peak/time overlay, and
10-bp one-way friction.  All requested sensitivities are one-at-a-time.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


RAW_START = "2018-08-01"
OOS_START = "2021-08-05"
OOS_END = "2026-08-04"
PROTOCOL_NAME = "SOXL_WALK_FORWARD_PROTOCOL_2026-08-05.md"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = "DGS3MO"
SLOT_FRACTIONS = (24 / 99, 24 / 99, 24 / 99)
RESIDUAL_FRACTION = 27 / 99
RISK_REASONS = {
    "technical_stop",
    "weakness_20ema",
    "weakness_failed_reclaim",
    "peak_drawdown",
}
INDICATORS = (
    "none",
    "sma20",
    "sma50",
    "sma60",
    "sma200",
    "macd",
    "no_rvol",
    "stoch",
    "chaikin",
)

# Official NYSE full closures transcribed from current/archive calendars.  The
# 2018-12-05 and 2025-01-09 national days of mourning are included explicitly.
FULL_CLOSURES = {
    "2018-09-03", "2018-11-22", "2018-12-05", "2018-12-25",
    "2019-01-01", "2019-01-21", "2019-02-18", "2019-04-19", "2019-05-27",
    "2019-07-04", "2019-09-02", "2019-11-28", "2019-12-25",
    "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25",
    "2020-07-03", "2020-09-07", "2020-11-26", "2020-12-25",
    "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31",
    "2021-07-05", "2021-09-06", "2021-11-25", "2021-12-24",
    "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20",
    "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26",
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
    "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18",
    "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27",
    "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03",
}
EARLY_CLOSES = {
    "2018-11-23", "2018-12-24", "2019-07-03", "2019-11-29", "2019-12-24",
    "2020-11-27", "2020-12-24", "2021-11-26", "2022-11-25", "2023-07-03",
    "2023-11-24", "2024-07-03", "2024-11-29", "2024-12-24", "2025-07-03",
    "2025-11-28", "2025-12-24", "2026-07-02",
}
CALENDAR_SOURCES = [
    "https://www.nyse.com/trade/hours-calendars",
    "https://www.nyse.com/publicdocs/ICE_NYSE_2021_Yearly_Trading_Calendar.pdf",
    "https://www.nyse.com/publicdocs/ICE_NYSE_2022_Yearly_Trading_Calendar.pdf",
    "https://www.nyse.com/publicdocs/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf",
    "https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf",
    "https://www.nyse.com/publicdocs/ICE_NYSE_2025_Yearly_Trading_Calendar.pdf",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def expected_sessions(start: str, end: str) -> pd.DatetimeIndex:
    idx = pd.date_range(start, end, freq="B")
    return idx.difference(pd.to_datetime(sorted(FULL_CLOSURES))).sort_values()


def split_map(events: dict[str, Any]) -> dict[pd.Timestamp, float]:
    out: dict[pd.Timestamp, float] = {}
    for item in (events.get("splits") or {}).values():
        day = pd.Timestamp(datetime.fromtimestamp(int(item["date"]), tz=timezone.utc).date())
        if item.get("numerator") and item.get("denominator"):
            ratio = float(item["numerator"]) / float(item["denominator"])
        else:
            text = str(item.get("splitRatio", "")).replace(":", "/")
            left, right = text.split("/")
            ratio = float(left) / float(right)
        if not math.isfinite(ratio) or ratio <= 0:
            raise RuntimeError(f"invalid split ratio {item}")
        out[day] = out.get(day, 1.0) * ratio
    return out


def split_adjusted_volume(frame: pd.DataFrame, splits: dict[pd.Timestamp, float]) -> pd.Series:
    result = frame["volume"].astype(float).copy()
    for day, ratio in sorted(splits.items()):
        result.loc[result.index < day] *= ratio
    return result


def fetch_treasury(start: str, end: str) -> tuple[pd.Series | None, dict[str, Any]]:
    params = {"id": FRED_SERIES, "cosd": start, "coed": end}
    url = FRED_URL + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
        lines = text.splitlines()
        rows = []
        for line in lines[1:]:
            day, value = line.split(",", 1)
            if value not in ("", "."):
                rows.append((pd.Timestamp(day), float(value)))
        series = pd.Series(dict(rows), dtype=float).sort_index()
        if series.empty:
            raise RuntimeError("empty DGS3MO")
        return series, {"status": "passed", "url": url, "rows": len(series)}
    except Exception as exc:
        return None, {"status": "unavailable_zero_yield_used", "url": url, "error": repr(exc)}


def build_features(
    raw: pd.DataFrame,
    events: dict[str, Any],
    builder: Any,
    base: Any,
) -> tuple[pd.DataFrame, list[dict[str, Any] | None]]:
    splits = split_map(events)
    adjusted_raw = raw.copy()
    adjusted_raw["volume"] = split_adjusted_volume(raw, splits)
    technical, ema10, ema20, atr14 = base.technical_components(adjusted_raw, builder)
    f = technical.copy()
    f["raw_open"] = raw["open"]
    f["raw_high"] = raw["high"]
    f["raw_low"] = raw["low"]
    f["raw_close"] = raw["close"]
    f["raw_volume"] = raw["volume"]
    f["ema10"] = ema10
    f["ema20"] = ema20
    f["atr14"] = atr14
    for n in (20, 50, 60, 200):
        f[f"sma{n}"] = f["close"].rolling(n).mean()
        f[f"sma{n}_5"] = f[f"sma{n}"].shift(5)
    ema12 = f["close"].ewm(span=12, adjust=False).mean()
    ema26 = f["close"].ewm(span=26, adjust=False).mean()
    f["macd"] = ema12 - ema26
    f["macd_signal"] = f["macd"].ewm(span=9, adjust=False).mean()
    f["macd_hist"] = f["macd"] - f["macd_signal"]
    f["rvol20"] = f["volume"] / f["volume"].shift(1).rolling(20).mean()
    low20 = f["low"].rolling(20).min()
    high20 = f["high"].rolling(20).max()
    span = high20 - low20
    raw_k = np.where(span != 0, 100.0 * (f["close"] - low20) / span, np.nan)
    f["stoch_k"] = pd.Series(raw_k, index=f.index).rolling(3).mean()
    f["stoch_d"] = f["stoch_k"].rolling(3).mean()
    day_range = f["high"] - f["low"]
    mfm = np.where(
        day_range != 0,
        ((f["close"] - f["low"]) - (f["high"] - f["close"])) / day_range,
        0.0,
    )
    adl = pd.Series(mfm, index=f.index).fillna(0.0).mul(f["volume"]).cumsum()
    f["chaikin"] = adl.ewm(span=3, adjust=False).mean() - adl.ewm(span=10, adjust=False).mean()

    rows: list[dict[str, Any] | None] = [None] * len(f)
    for pos in range(252, len(f)):
        rows[pos] = base.point_in_time_row(
            adjusted_raw, technical, ema10, ema20, atr14, pos, builder
        )
    return f, rows


def setup_without_rvol(
    f: pd.DataFrame,
    rows: list[dict[str, Any] | None],
    proxy_rows: list[dict[str, Any] | None],
    pos: int,
) -> bool:
    row, proxy = rows[pos], proxy_rows[pos]
    if row is None or proxy is None or pos < 22:
        return False
    aligned = bool(
        row["close"] > row["ema20"]
        and row["ema10_above_ema20"]
        and row["ema10_direction_3d"] == "rising"
        and row["ema20_direction_3d"] == "rising"
    )
    proxy_ok = bool(
        proxy["close"] > proxy["ema20"]
        and proxy["ema10_above_ema20"]
        and proxy["ema20_direction_3d"] == "rising"
        and (row["close"] >= row["ma50"] or row["ma50"] >= row["ma50_5d_ago"])
    )
    if not aligned or not proxy_ok or abs(row["opening_gap_fraction"]) > max(0.05, row["atr14"] / row["close_prev"]):
        return False
    # Exact price/ATR reclaim semantics with only the volume clauses removed.
    reclaim = False
    for ema_name in ("ema10", "ema20"):
        for age in (1, 2, 3):
            p = pos - age
            if (
                f["low"].iloc[p] <= f[ema_name].iloc[p] + 0.25 * f["atr14"].iloc[p]
                and f["high"].iloc[p] >= f[ema_name].iloc[p] - 0.25 * f["atr14"].iloc[p]
            ):
                reclaim = bool(
                    f["close"].iloc[pos] >= f[ema_name].iloc[pos] + 0.10 * f["atr14"].iloc[pos]
                    and f["close"].iloc[pos] > f["close"].iloc[pos - 1]
                )
                if reclaim:
                    break
        if reclaim:
            break
    prior_level = f["high"].iloc[pos - 21 : pos - 1].max()
    previous_breakout = bool(
        f["close"].iloc[pos - 1] >= prior_level + 0.10 * f["atr14"].iloc[pos - 1]
    )
    breakout = bool(
        previous_breakout
        and f["close"].iloc[pos] >= prior_level
        and f["low"].iloc[pos] >= prior_level - 0.25 * f["atr14"].iloc[pos]
    )
    extension = row["extension_above_ema20_atr"]
    return bool((reclaim and extension <= 1.5) or (breakout and extension <= 2.0))


def indicator_pass(name: str, soxl: pd.DataFrame, soxx: pd.DataFrame, pos: int) -> bool:
    if name in ("none", "no_rvol"):
        return True
    p = soxx.iloc[pos]
    s = soxl.iloc[pos]
    if name == "sma20":
        return bool(p["close"] > p["sma20"])
    if name in ("sma50", "sma60"):
        return bool(p["close"] > p[name] and p[name] > p[f"{name}_5"])
    if name == "sma200":
        return bool(p["close"] > p["sma200"])
    if name == "macd":
        return bool(p["macd_hist"] > 0)
    if name == "stoch":
        return bool(s["stoch_k"] > s["stoch_d"] and s["stoch_k"] < 80)
    if name == "chaikin":
        return bool(p["chaikin"] > 0)
    raise ValueError(name)


@dataclass
class ReentryLot:
    shares: float
    entry_pos: int
    entry_price: float
    planned_r: float | None
    hwm: float
    mfe: float = 0.0


@dataclass
class Slot:
    target: float
    shares: float
    cost: float
    hwm: float
    lots: list[ReentryLot] = field(default_factory=list)


@dataclass
class State:
    cash: float
    residual_shares: float
    residual_cost: float
    residual_hwm: float
    slots: list[Slot]
    pending: dict[str, Any] | None = None
    armed_queue: list[int] = field(default_factory=lambda: [0, 1, 2])
    sold_order: list[int] = field(default_factory=list)
    risk_armed: bool = True
    risk_false_seen: bool = True
    risk_recovery_count: int = 0
    risk_rearm_reason: str | None = None
    last_reduction_pos: int | None = None
    align_count: int = 0
    eligibility_expiry: int | None = None
    previous_triggers: dict[str, bool] = field(default_factory=dict)
    trades: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    costs: float = 0.0
    stale_freezes: int = 0
    gap_through_stop: int = 0
    hard_reviews: int = 0

    def total_shares(self) -> float:
        return self.residual_shares + sum(slot.shares for slot in self.slots)

    def avg_cost(self) -> float:
        shares = self.total_shares()
        if shares <= 0:
            return 0.0
        cost = self.residual_shares * self.residual_cost + sum(s.shares * s.cost for s in self.slots)
        return cost / shares


@dataclass(frozen=True)
class Config:
    name: str
    mode: str = "revised"
    indicator: str = "none"
    rearm_closes: int = 2
    restore_fraction: float = 1.0
    peak_dd: float | None = None
    time_stop: int | None = None
    cost_bps: float = 10.0
    cash_yield: bool = True


def initial_state(open_price: float, cost_rate: float) -> tuple[State, float]:
    execution = open_price * (1 + cost_rate)
    initial = 99.0 * execution
    slots = [Slot(24.0, 24.0, execution, open_price) for _ in range(3)]
    state = State(0.0, 27.0, execution, open_price, slots)
    state.costs = 99.0 * open_price * cost_rate
    state.trades.append({
        "date": None, "side": "buy", "shares": 99.0, "raw_open": open_price,
        "execution_price": execution, "notional_usd": 99.0 * open_price,
        "reason": "fold_initial_normalization",
    })
    return state, initial


def apply_split(state: State, ratio: float) -> None:
    state.residual_shares *= ratio
    state.residual_cost /= ratio
    state.residual_hwm /= ratio
    for slot in state.slots:
        slot.target *= ratio
        slot.shares *= ratio
        slot.cost /= ratio
        slot.hwm /= ratio
        for lot in slot.lots:
            lot.shares *= ratio
            lot.entry_price /= ratio
            if lot.planned_r is not None:
                lot.planned_r /= ratio
            lot.hwm /= ratio
            lot.mfe /= ratio
    if state.pending:
        state.pending["quantity"] *= ratio
        if state.pending.get("stop_level") is not None:
            state.pending["stop_level"] /= ratio


def remove_from_slot(slot: Slot, quantity: float) -> float:
    sold = min(quantity, slot.shares)
    remaining = sold
    # Remove newest re-entry lots first; the untouched original lot keeps its HWM.
    for lot in reversed(slot.lots):
        take = min(remaining, lot.shares)
        lot.shares -= take
        remaining -= take
        if remaining <= 1e-12:
            break
    slot.lots = [lot for lot in slot.lots if lot.shares > 1e-12]
    slot.shares -= sold
    return sold


def execute_pending(
    state: State,
    day: pd.Timestamp,
    pos: int,
    bar: pd.Series,
    config: Config,
    soxl_row: dict[str, Any] | None,
) -> None:
    if not state.pending:
        return
    raw_open = float(bar["raw_open"])
    raw_volume = float(bar["raw_volume"])
    if not math.isfinite(raw_open) or raw_open <= 0 or not math.isfinite(raw_volume) or raw_volume <= 0:
        state.stale_freezes += 1
        state.events.append({"date": day.date().isoformat(), "event": "pending_frozen_invalid_or_halted_open"})
        return
    pending = dict(state.pending)
    state.pending = None
    cost = config.cost_bps / 10_000.0
    idx = int(pending["slot"])
    slot = state.slots[idx]
    if pending["side"] == "sell":
        qty = remove_from_slot(slot, float(pending["quantity"]))
        execution = raw_open * (1 - cost)
        state.cash += qty * execution
        state.costs += qty * raw_open * cost
        if idx in state.armed_queue:
            state.armed_queue.remove(idx)
        if idx in state.sold_order:
            state.sold_order.remove(idx)
        state.sold_order.append(idx)
        if pending.get("stop_level") is not None and raw_open < float(pending["stop_level"]):
            state.gap_through_stop += 1
        reason = str(pending["reason"])
        state.last_reduction_pos = pos
        if reason in RISK_REASONS:
            state.risk_armed = False
            state.risk_false_seen = False
            state.risk_recovery_count = 0
            state.risk_rearm_reason = reason
        state.trades.append({
            "date": day.date().isoformat(), "side": "sell", "shares": qty,
            "raw_open": raw_open, "execution_price": execution,
            "notional_usd": qty * raw_open, "reason": reason, "slot": idx,
        })
    else:
        requested = float(pending["quantity"])
        execution = raw_open * (1 + cost)
        qty = min(requested, state.cash / execution)
        qty = math.floor(qty + 1e-12)
        if qty <= 0:
            state.events.append({"date": day.date().isoformat(), "event": "reentry_blocked_by_cash"})
            return
        state.cash -= qty * execution
        state.costs += qty * raw_open * cost
        prior_shares = slot.shares
        slot.cost = (slot.cost * prior_shares + execution * qty) / (prior_shares + qty) if prior_shares else execution
        slot.shares += qty
        slot.hwm = raw_open
        stop_level = pending.get("planned_stop")
        planned_r = execution - float(stop_level) if stop_level is not None and float(stop_level) < execution else None
        slot.lots.append(ReentryLot(qty, pos, execution, planned_r, raw_open))
        if idx not in state.armed_queue:
            state.armed_queue.append(idx)
        state.align_count = 0
        state.eligibility_expiry = None
        state.trades.append({
            "date": day.date().isoformat(), "side": "buy", "shares": qty,
            "raw_open": raw_open, "execution_price": execution,
            "notional_usd": qty * raw_open, "reason": pending["reason"], "slot": idx,
            "planned_r": planned_r,
        })


def update_high_water(state: State, high: float, close: float) -> None:
    if state.residual_shares > 0:
        state.residual_hwm = max(state.residual_hwm, close)
    for slot in state.slots:
        if slot.shares > 0:
            slot.hwm = max(slot.hwm, close)
        for lot in slot.lots:
            lot.hwm = max(lot.hwm, close)
            lot.mfe = max(lot.mfe, high - lot.entry_price)


def fresh_trigger(states: dict[str, bool], previous: dict[str, bool], ordered: list[str]) -> str | None:
    for name in ordered:
        if states.get(name) and not previous.get(name, False):
            return name
    return None


def run_staged(
    config: Config,
    soxl: pd.DataFrame,
    soxx: pd.DataFrame,
    soxl_rows: list[dict[str, Any] | None],
    soxx_rows: list[dict[str, Any] | None],
    timing: Any,
    dividends: dict[pd.Timestamp, float],
    splits: dict[pd.Timestamp, float],
    treasury: pd.Series | None,
    start: pd.Timestamp,
    end: pd.Timestamp,
    indicator_schedule: dict[pd.Timestamp, str] | None = None,
    carry_state: State | None = None,
    initial_capital: float | None = None,
) -> dict[str, Any]:
    positions = np.where((soxl.index >= start) & (soxl.index <= end))[0]
    if not len(positions):
        raise RuntimeError("empty simulation interval")
    first = int(positions[0])
    cost_rate = config.cost_bps / 10_000.0
    if carry_state is None:
        state, initial = initial_state(float(soxl["raw_open"].iloc[first]), cost_rate)
        state.trades[0]["date"] = soxl.index[first].date().isoformat()
    else:
        state = carry_state
        initial = float(initial_capital)
    values: list[tuple[pd.Timestamp, float]] = []
    exposures: list[float] = []
    prior_day: pd.Timestamp | None = None

    for pos in positions:
        pos = int(pos)
        day = soxl.index[pos]
        bar = soxl.iloc[pos]
        if day in splits:
            apply_split(state, splits[day])
        if prior_day is not None and config.cash_yield and treasury is not None and state.cash > 0:
            known = treasury.loc[treasury.index < day]
            if not known.empty:
                calendar_days = max(1, (day - prior_day).days)
                state.cash *= 1.0 + float(known.iloc[-1]) / 100.0 * calendar_days / 365.0
        if day in dividends:
            state.cash += state.total_shares() * float(dividends[day])
        execute_pending(state, day, pos, bar, config, soxl_rows[pos])
        close = float(bar["raw_close"])
        update_high_water(state, float(bar["raw_high"]), close)
        equity = state.cash + state.total_shares() * close
        values.append((day, equity))
        exposures.append(state.total_shares() * close / equity if equity else 0.0)
        prior_day = day
        if bool(bar["is_early_close"]):
            state.events.append({"date": day.date().isoformat(), "event": "signal_frozen_early_close"})
            continue
        row, proxy = soxl_rows[pos], soxx_rows[pos]
        if row is None or proxy is None:
            continue

        avg = state.avg_cost()
        hard_boundary = avg * 0.8 if avg > 0 else 0.0
        trigger_states, diagnostics, _ = timing._trigger_states("SOXL", row, proxy, avg, hard_boundary)
        if close <= hard_boundary and hard_boundary > 0:
            if not state.previous_triggers.get("hard", False):
                state.hard_reviews += 1
                state.events.append({"date": day.date().isoformat(), "event": "unsized_hard_risk_review"})
            state.previous_triggers["hard"] = True
        else:
            state.previous_triggers["hard"] = False

        # Existing policy replay: action on every observed priority signal and
        # never rearm/re-enter.  It intentionally demonstrates the old path.
        if config.mode == "existing":
            old = dict(trigger_states)
            if row.get("close_below_ema10_consecutive", 0) >= 2 and row.get("ema10_direction_3d") == "falling":
                old["weakness_10ema"] = bool(proxy["close"] < proxy["ema10"])
            # The historical slots never authorized strength-reclaim or
            # extension sells.  Take-profit was allowed only for the first two
            # common slots; all three accepted the four weakness/stop paths.
            idx = state.armed_queue[0] if state.armed_queue else None
            allowed = ["technical_stop", "weakness_20ema", "weakness_failed_reclaim", "weakness_10ema"]
            if idx is not None and idx < 2:
                allowed.append("take_profit_rejection")
            reason = next((x for x in allowed if old.get(x)), None)
            if reason and state.pending is None and state.armed_queue:
                idx = state.armed_queue[0]
                state.pending = {"side": "sell", "slot": idx, "quantity": state.slots[idx].shares,
                                 "reason": reason, "stop_level": diagnostics.get("technical_stop_level_usd")}
            state.previous_triggers.update(old)
            continue

        both_above20 = bool(row["close"] > row["ema20"] and proxy["close"] > proxy["ema20"])
        if not state.risk_armed:
            enough_wait = state.last_reduction_pos is not None and pos - state.last_reduction_pos >= 3
            state.risk_recovery_count = state.risk_recovery_count + 1 if both_above20 else 0
            peak_recovered = True
            if state.risk_rearm_reason == "peak_drawdown" and config.peak_dd is not None:
                hwms = [state.residual_hwm] + [s.hwm for s in state.slots if s.shares > 0]
                peak_recovered = not hwms or close > max(hwms) * (1 - config.peak_dd)
            if enough_wait and state.risk_recovery_count >= config.rearm_closes and peak_recovered:
                state.risk_armed = True
                state.risk_false_seen = True
                state.risk_rearm_reason = None
                state.events.append({"date": day.date().isoformat(), "event": "ema20_risk_rearmed"})

        # Two-close recovery eligibility, expiring in ten completed sessions.
        aligned = bool(
            both_above20 and row["ema10_above_ema20"] and proxy["ema10_above_ema20"]
            and row["ema20_direction_3d"] == "rising" and proxy["ema20_direction_3d"] == "rising"
        )
        state.align_count = state.align_count + 1 if aligned else 0
        if not both_above20:
            state.eligibility_expiry = None
        elif state.align_count >= 2 and state.eligibility_expiry is None:
            state.eligibility_expiry = pos + 10
        if state.eligibility_expiry is not None and pos > state.eligibility_expiry:
            state.eligibility_expiry = None

        # A time stop applies only to the newest surviving re-entry lot.
        if config.time_stop is not None and state.pending is None:
            newest: tuple[int, ReentryLot] | None = None
            for idx, slot in enumerate(state.slots):
                for lot in slot.lots:
                    if newest is None or lot.entry_pos > newest[1].entry_pos:
                        newest = (idx, lot)
            if newest is not None:
                idx, lot = newest
                if (
                    pos - lot.entry_pos >= config.time_stop
                    and lot.planned_r is not None
                    and lot.mfe < 0.5 * lot.planned_r
                    and not both_above20
                ):
                    state.pending = {"side": "sell", "slot": idx, "quantity": lot.shares,
                                     "reason": "time_stop", "stop_level": None}

        # Peak-to-close review is a fresh threshold crossing and consumes one
        # common armed slot only after both symbols are below EMA20.
        peak_hit = False
        if config.peak_dd is not None:
            hwms = [state.residual_hwm] + [s.hwm for s in state.slots if s.shares > 0]
            peak_hit = bool(hwms and close <= max(hwms) * (1 - config.peak_dd) and not both_above20)
        risk_map = {
            "technical_stop": bool(trigger_states.get("technical_stop")),
            "weakness_20ema": bool(trigger_states.get("weakness_20ema")),
            "weakness_failed_reclaim": bool(trigger_states.get("weakness_failed_reclaim")),
            "peak_drawdown": peak_hit,
        }
        if state.risk_armed and state.risk_false_seen and state.pending is None and state.armed_queue:
            reason = fresh_trigger(
                risk_map, state.previous_triggers,
                ["technical_stop", "peak_drawdown", "weakness_20ema", "weakness_failed_reclaim"],
            )
            if reason:
                idx = state.armed_queue[0]
                state.pending = {"side": "sell", "slot": idx, "quantity": state.slots[idx].shares,
                                 "reason": reason, "stop_level": diagnostics.get("technical_stop_level_usd")}
        # Take-profit rejection stays distinct and has a common 3-session spacing.
        if (
            state.pending is None and state.armed_queue and state.armed_queue[0] < 2
            and trigger_states.get("take_profit_rejection")
            and not state.previous_triggers.get("take_profit_rejection", False)
            and (state.last_reduction_pos is None or pos - state.last_reduction_pos >= 3)
        ):
            idx = state.armed_queue[0]
            state.pending = {"side": "sell", "slot": idx, "quantity": state.slots[idx].shares,
                             "reason": "take_profit_rejection", "stop_level": None}

        # Re-entry restores only a previously sold slot and is capped by cash.
        if state.pending is None and state.sold_order and state.eligibility_expiry is not None:
            indicator = indicator_schedule.get(day, config.indicator) if indicator_schedule else config.indicator
            setup = (
                setup_without_rvol(soxl, soxl_rows, soxx_rows, pos)
                if indicator == "no_rvol"
                else timing.watch_setup(row, leveraged=True, proxy_row=proxy).get("technical_setup_detected", False)
            )
            if setup and indicator_pass(indicator, soxl, soxx, pos):
                idx = next((i for i in reversed(state.sold_order) if state.slots[i].shares < state.slots[i].target - 1e-12), None)
                if idx is not None:
                    missing = state.slots[idx].target - state.slots[idx].shares
                    quantity = min(missing, math.floor(state.slots[idx].target * config.restore_fraction))
                    if quantity >= 1:
                        stop_level = max(row["prior_10d_low"] - 0.25 * row["atr14"], row["ema20"] - 0.75 * row["atr14"])
                        state.pending = {"side": "buy", "slot": idx, "quantity": quantity,
                                         "reason": f"reentry_{indicator}", "planned_stop": stop_level}

        state.previous_triggers.update(risk_map)
        state.previous_triggers["take_profit_rejection"] = bool(trigger_states.get("take_profit_rejection"))

    metric = metrics(config.name, initial, values, state.trades, state.costs, exposures)
    return {"metric": metric, "state": state, "values": values, "exposures": exposures}


def metrics(
    name: str,
    initial: float,
    values: list[tuple[pd.Timestamp, float]],
    trades: list[dict[str, Any]],
    costs: float,
    exposure: list[float],
) -> dict[str, Any]:
    s = pd.Series(dict(values), dtype=float).sort_index()
    start_marker = s.index[0] - pd.Timedelta(days=1)
    aug = pd.concat([pd.Series([initial], index=[start_marker]), s])
    r = aug.pct_change().dropna()
    dd = aug / aug.cummax() - 1
    years = max((s.index[-1] - s.index[0]).days / 365.25, 1 / 252)
    total = float(s.iloc[-1] / initial - 1)
    cagr = float((s.iloc[-1] / initial) ** (1 / years) - 1)
    vol = float(r.std(ddof=1) * math.sqrt(252)) if len(r) > 1 else None
    sharpe = float(r.mean() / r.std(ddof=1) * math.sqrt(252)) if len(r) > 1 and r.std(ddof=1) > 0 else None
    down = np.minimum(r.to_numpy(float), 0)
    ddev = float(np.sqrt(np.mean(down * down)) * math.sqrt(252)) if len(down) else None
    sortino = float(r.mean() * 252 / ddev) if ddev and ddev > 0 else None
    mdd = float(dd.min())
    monthly = aug.resample("ME").last().pct_change().dropna()
    # Maximum sessions from a peak until full recovery; unrecovered spans count.
    peak = -math.inf
    peak_pos = 0
    max_recovery = 0
    for i, value in enumerate(aug.to_numpy(float)):
        if value >= peak:
            peak, peak_pos = value, i
        else:
            max_recovery = max(max_recovery, i - peak_pos)
    turnover = sum(abs(float(t.get("notional_usd") or 0)) for t in trades) / initial
    return {
        "name": name, "start_value_usd": initial, "end_value_usd": float(s.iloc[-1]),
        "total_return": total, "cagr": cagr, "annualized_volatility": vol,
        "maximum_drawdown": mdd, "calmar": cagr / abs(mdd) if mdd < 0 else None,
        "sharpe_rf0": sharpe, "sortino_target0": sortino,
        "worst_day": float(r.min()), "worst_month": float(monthly.min()) if len(monthly) else None,
        "maximum_recovery_sessions": int(max_recovery), "trade_count": len(trades),
        "turnover_multiple": float(turnover), "estimated_cost_usd": float(costs),
        "average_capital_weight": float(np.mean(exposure)),
        "average_factor_exposure": float(3 * np.mean(exposure)),
    }


def run_buy_hold(
    name: str, soxl: pd.DataFrame, dividends: dict[pd.Timestamp, float], splits: dict[pd.Timestamp, float],
    start: pd.Timestamp, end: pd.Timestamp, cost_bps: float,
) -> dict[str, Any]:
    positions = np.where((soxl.index >= start) & (soxl.index <= end))[0]
    first = int(positions[0]); cost = cost_bps / 10_000
    open_price = float(soxl["raw_open"].iloc[first]); shares = 99.0
    initial = shares * open_price * (1 + cost); cash = 0.0
    trades = [{"date": soxl.index[first].date().isoformat(), "side": "buy", "shares": shares,
               "raw_open": open_price, "notional_usd": shares * open_price, "reason": "initial"}]
    values = []; exposures = []
    for pos in positions:
        day = soxl.index[int(pos)]
        if day in splits: shares *= splits[day]
        if day in dividends: cash += shares * dividends[day]
        value = cash + shares * float(soxl["raw_close"].iloc[int(pos)])
        values.append((day, value)); exposures.append(shares * float(soxl["raw_close"].iloc[int(pos)]) / value)
    return {"metric": metrics(name, initial, values, trades, initial - 99 * open_price, exposures), "values": values, "trades": trades}


def factor_tier(soxx: pd.DataFrame, pos: int) -> float:
    p = soxx.iloc[pos]
    ema_falling = pos >= 3 and (p["ema20"] - soxx["ema20"].iloc[pos - 3]) / p["atr14"] < -0.10
    ema_rising = pos >= 3 and (p["ema20"] - soxx["ema20"].iloc[pos - 3]) / p["atr14"] > 0.10
    sma200_rising = p["sma200"] > p["sma200_5"]
    sma50_rising = p["sma50"] > p["sma50_5"]
    if p["close"] < p["sma200"] or (p["close"] < p["ema20"] and p["ema10"] < p["ema20"] and ema_falling):
        return 0.75
    if p["close"] > p["sma200"] and sma200_rising and p["close"] > p["ema20"] and p["ema10"] > p["ema20"] and ema_rising:
        return 3.0 if p["sma50"] > p["sma200"] and sma50_rising else 2.25
    return 1.5


def run_dynamic(
    soxl: pd.DataFrame, soxx: pd.DataFrame, dividends: dict[pd.Timestamp, float], splits: dict[pd.Timestamp, float],
    treasury: pd.Series | None, start: pd.Timestamp, end: pd.Timestamp, cost_bps: float,
    cash_yield: bool = True,
) -> dict[str, Any]:
    positions = np.where((soxl.index >= start) & (soxl.index <= end))[0]
    first = int(positions[0]); cost = cost_bps / 10_000
    initial = 99 * float(soxl["raw_open"].iloc[first]) * (1 + cost)
    cash = initial; shares = 0.0
    pending_weight: float | None = factor_tier(soxx, first - 1) / 3.0
    trades = []; values = []; exposures = []; costs = 0.0; last_tier = None
    prior_day: pd.Timestamp | None = None
    for pos in positions:
        pos = int(pos); day = soxl.index[pos]
        if day in splits: shares *= splits[day]
        if prior_day is not None and cash_yield and treasury is not None and cash > 0:
            known = treasury.loc[treasury.index < day]
            if not known.empty:
                cash *= 1.0 + float(known.iloc[-1]) / 100.0 * max(1, (day - prior_day).days) / 365.0
        if day in dividends: cash += shares * dividends[day]
        raw_open = float(soxl["raw_open"].iloc[pos])
        if pending_weight is not None and raw_open > 0:
            equity_open = cash + shares * raw_open
            target = pending_weight * equity_open
            current = shares * raw_open
            delta = target - current
            if abs(delta) / equity_open >= 0.10 or not trades:
                if delta > 0:
                    qty = min(delta / (raw_open * (1 + cost)), cash / (raw_open * (1 + cost)))
                    cash -= qty * raw_open * (1 + cost); shares += qty
                    side = "buy"
                else:
                    qty = min(-delta / raw_open, shares)
                    cash += qty * raw_open * (1 - cost); shares -= qty
                    side = "sell"
                costs += qty * raw_open * cost
                trades.append({"date": day.date().isoformat(), "side": side, "shares": qty,
                               "raw_open": raw_open, "notional_usd": qty * raw_open, "reason": "factor_tier"})
            pending_weight = None
        close = float(soxl["raw_close"].iloc[pos]); equity = cash + shares * close
        values.append((day, equity)); exposures.append(shares * close / equity if equity else 0.0)
        tier = factor_tier(soxx, pos)
        if tier != last_tier:
            pending_weight = tier / 3.0
            last_tier = tier
        prior_day = day
    return {"metric": metrics("dynamic_factor_cap_research", initial, values, trades, costs, exposures),
            "values": values, "trades": trades}


def fold_ranges() -> list[dict[str, pd.Timestamp]]:
    folds = []
    test_start = pd.Timestamp(OOS_START)
    for _ in range(10):
        test_end = min(test_start + pd.DateOffset(months=6) - pd.Timedelta(days=1), pd.Timestamp(OOS_END))
        folds.append({"train_start": test_start - pd.DateOffset(months=24),
                      "train_end": test_start - pd.Timedelta(days=1),
                      "test_start": test_start, "test_end": test_end})
        test_start = test_start + pd.DateOffset(months=6)
    return folds


def metric_for_slice(values: list[tuple[pd.Timestamp, float]], start: pd.Timestamp, end: pd.Timestamp, name: str) -> dict[str, Any]:
    s = pd.Series(dict(values), dtype=float).sort_index().loc[start:end]
    if s.empty: raise RuntimeError("empty fold slice")
    prior = pd.Series(dict(values), dtype=float).sort_index().loc[:start]
    initial = float(prior.iloc[0] if len(prior) == len(s) else prior.iloc[-len(s)-1]) if len(prior) > len(s) else float(s.iloc[0])
    # Fold return uses first available close as a neutral boundary; independent
    # reset metrics below retain open-to-close precision.
    pairs = list(s.items())
    return metrics(name, initial, pairs, [], 0.0, [np.nan] * len(pairs))


def regime_label(soxx: pd.DataFrame, fold: dict[str, pd.Timestamp]) -> dict[str, Any]:
    test = soxx.loc[fold["test_start"]:fold["test_end"], "close"].pct_change().dropna()
    train = soxx.loc[fold["train_start"]:fold["train_end"], "close"].pct_change().dropna()
    total = float((1 + test).prod() - 1)
    label = "bull" if total > 0.10 else "bear" if total < -0.10 else "range"
    test_vol = float(test.std(ddof=1) * math.sqrt(252))
    rolling = train.rolling(126).std(ddof=1) * math.sqrt(252)
    median_train_vol = float(rolling.dropna().median())
    return {"return": total, "regime": label, "annualized_volatility": test_vol,
            "high_volatility": bool(test_vol > median_train_vol), "training_median_126d_vol": median_train_vol}


def acceptance(candidate: dict[str, Any], core: dict[str, Any], folds: list[dict[str, Any]], event_count: int) -> dict[str, Any]:
    cagr_gain = candidate["cagr"] - core["cagr"]
    mdd_gain = candidate["maximum_drawdown"] - core["maximum_drawdown"]
    c1 = (cagr_gain >= 0.05 and candidate["maximum_drawdown"] >= core["maximum_drawdown"] - 0.03) or (
        mdd_gain >= 0.05 and candidate["cagr"] >= 0.95 * core["cagr"]
    )
    c2 = candidate["calmar"] is not None and core["calmar"] is not None and candidate["calmar"] >= 1.10 * core["calmar"]
    improved = [f for f in folds if f.get("candidate_return", -math.inf) > f.get("core_return", math.inf)]
    c3 = len(improved) >= 7 and any(f.get("regime") == "bull" for f in improved) and any(f.get("regime") == "bear" or f.get("high_volatility") for f in improved)
    excesses = [max(0.0, f.get("candidate_return", 0) - f.get("core_return", 0)) for f in folds]
    c5 = sum(excesses) <= 0 or max(excesses, default=0) <= 0.5 * sum(excesses)
    return {"criterion_1_return_or_drawdown": c1, "criterion_2_calmar": c2,
            "criterion_3_fold_and_regime": c3, "criterion_5_no_single_fold_dominance": c5,
            "criterion_6_minimum_events": event_count >= 20,
            "criterion_4_cost_and_adjacent_stability": "evaluated_separately",
            "eligible_before_cost_stability": bool(c1 and c2 and c3 and c5 and event_count >= 20),
            "improved_fold_count": len(improved), "event_count": event_count}


def self_test() -> None:
    folds = fold_ranges()
    assert len(folds) == 10
    assert folds[0]["train_start"] == pd.Timestamp("2019-08-05")
    assert folds[0]["test_start"] == pd.Timestamp(OOS_START)
    assert folds[-1]["test_end"] == pd.Timestamp(OOS_END)
    state, initial = initial_state(10.0, 0.001)
    assert math.isclose(initial, 990.99)
    assert math.isclose(state.total_shares(), 99.0)
    apply_split(state, 2.0)
    assert math.isclose(state.total_shares(), 198.0)
    assert math.isclose(state.avg_cost(), 5.005)
    state.pending = {"side": "sell", "slot": 0, "quantity": 48.0,
                     "reason": "technical_stop", "stop_level": 4.0}
    execute_pending(
        state, pd.Timestamp("2026-01-02"), 1,
        pd.Series({"raw_open": float("nan"), "raw_volume": 100.0}),
        Config("test"), None,
    )
    assert state.pending is not None and state.stale_freezes == 1
    print(json.dumps({"status": "passed", "folds": len(folds),
                      "split_and_halt_fail_closed": True}))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    out = args.output_dir; out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    backtest_source = out / "backtest_soxl_ema_policy_2026-08-05.py"
    base = load_module("soxl_one_year_base", backtest_source)
    base.NYSE_FULL_CLOSURES = set(FULL_CLOSURES)
    base.NYSE_EARLY_CLOSES = set(EARLY_CLOSES)
    scripts = root / "stock-strategy-system" / "skill-staging" / "manage-us-stock-strategy" / "scripts"
    builder = load_module("wf_snapshot_builder", scripts / "build_market_snapshot.py")
    timing = load_module("wf_timing_engine", scripts / "timing_engine.py")

    soxl_raw, q_soxl = base.combined_history("SOXL", RAW_START, OOS_END)
    soxx_raw, q_soxx = base.combined_history("SOXX", RAW_START, OOS_END)
    expected = expected_sessions(RAW_START, OOS_END)
    if not soxl_raw.index.equals(expected) or not soxx_raw.index.equals(expected):
        raise RuntimeError("official calendar/vendor completeness audit failed")
    if not soxl_raw.index.equals(soxx_raw.index):
        raise RuntimeError("SOXL/SOXX session indexes disagree")
    soxl, soxl_rows = build_features(soxl_raw, q_soxl["events"], builder, base)
    soxx, soxx_rows = build_features(soxx_raw, q_soxx["events"], builder, base)
    dividends = base.yahoo_dividends(q_soxl["events"])
    splits = split_map(q_soxl["events"])
    treasury, treasury_quality = fetch_treasury(RAW_START, OOS_END)
    folds = fold_ranges()

    # Select at most one indicator in each training fold, causally.
    selections = []
    schedule: dict[pd.Timestamp, str] = {}
    train_table = []
    for number, fold in enumerate(folds, 1):
        core_cfg = Config("train_core", indicator="none")
        core_train = run_staged(core_cfg, soxl, soxx, soxl_rows, soxx_rows, timing,
                                dividends, splits, treasury, fold["train_start"], fold["train_end"])["metric"]
        candidates = []
        for indicator in INDICATORS:
            cfg = Config(f"train_{indicator}", indicator=indicator)
            result = run_staged(cfg, soxl, soxx, soxl_rows, soxx_rows, timing,
                                dividends, splits, treasury, fold["train_start"], fold["train_end"])["metric"]
            candidates.append((indicator, result))
            train_table.append({"fold": number, "indicator": indicator, **result})
        eligible = [x for x in candidates if x[1]["maximum_drawdown"] >= core_train["maximum_drawdown"] - 1e-12]
        chosen = sorted(eligible, key=lambda x: (-x[1]["cagr"], -(x[1]["calmar"] or -999), x[1]["turnover_multiple"], INDICATORS.index(x[0])))[0][0]
        selections.append({"fold": number, "chosen": chosen, **{k: v.date().isoformat() for k, v in fold.items()}})
        for day in soxl.loc[fold["test_start"]:fold["test_end"]].index:
            schedule[day] = chosen

    configs = [
        Config("existing_staged_replay", mode="existing"),
        Config("revised_simple", indicator="none"),
        *[Config(f"indicator_{x}", indicator=x) for x in INDICATORS if x != "none"],
        Config("rearm_1", rearm_closes=1), Config("rearm_2", rearm_closes=2),
        *[Config(f"restore_{int(x*100)}", restore_fraction=x) for x in (0.25, 0.50, 0.75, 1.00)],
        *[Config(f"peak_dd_{int(x*100)}", peak_dd=x) for x in (0.20, 0.25, 0.30, 0.35)],
        *[Config(f"time_stop_{x}", time_stop=x) for x in (10, 20, 30)],
        Config("selected_indicator_walk_forward", indicator="none"),
    ]
    results: dict[str, Any] = {}
    all_trades = []
    daily = pd.DataFrame(index=soxl.loc[OOS_START:OOS_END].index)
    for cfg in configs:
        result = run_staged(cfg, soxl, soxx, soxl_rows, soxx_rows, timing, dividends, splits, treasury,
                            pd.Timestamp(OOS_START), pd.Timestamp(OOS_END), schedule if cfg.name == "selected_indicator_walk_forward" else None)
        results[cfg.name] = result
        daily[cfg.name] = pd.Series(dict(result["values"]))
        all_trades.extend({"strategy": cfg.name, **t} for t in result["state"].trades)
    bh = run_buy_hold("buy_hold", soxl, dividends, splits, pd.Timestamp(OOS_START), pd.Timestamp(OOS_END), 10)
    dyn = run_dynamic(soxl, soxx, dividends, splits, treasury, pd.Timestamp(OOS_START), pd.Timestamp(OOS_END), 10)
    results["buy_hold"] = bh; results["dynamic_factor_cap_research"] = dyn
    daily["buy_hold"] = pd.Series(dict(bh["values"])); daily["dynamic_factor_cap_research"] = pd.Series(dict(dyn["values"]))
    all_trades.extend({"strategy": "buy_hold", **t} for t in bh["trades"])
    all_trades.extend({"strategy": "dynamic_factor_cap_research", **t} for t in dyn["trades"])

    # Fold-independent reset checks and regime labels for every requested
    # candidate family, not only the selected indicator.
    fold_rows = []
    for number, fold in enumerate(folds, 1):
        regime = regime_label(soxx, fold)
        chosen = selections[number - 1]["chosen"]
        fold_candidates = [(cfg.name, cfg) for cfg in configs if cfg.name != "selected_indicator_walk_forward"]
        fold_candidates.append(("selected_indicator_walk_forward", Config("selected", indicator=chosen)))
        for name, cfg in fold_candidates:
            r = run_staged(cfg, soxl, soxx, soxl_rows, soxx_rows, timing, dividends, splits, treasury,
                           fold["test_start"], fold["test_end"])
            fold_rows.append({"fold": number, "strategy": name, "chosen_indicator": chosen,
                              **{k: v.date().isoformat() for k, v in fold.items()}, **regime, **r["metric"]})
        for name in ("buy_hold", "dynamic_factor_cap_research"):
            if name == "buy_hold":
                r = run_buy_hold(name, soxl, dividends, splits, fold["test_start"], fold["test_end"], 10)
            else:
                r = run_dynamic(soxl, soxx, dividends, splits, treasury, fold["test_start"], fold["test_end"], 10)
            fold_rows.append({"fold": number, "strategy": name, "chosen_indicator": chosen,
                              **{k: v.date().isoformat() for k, v in fold.items()}, **regime, **r["metric"]})

    # Friction and zero-yield directional sensitivities for every candidate.
    stress = []
    for bps in (20.0, 50.0):
        for base_cfg in configs:
            cfg = replace(base_cfg, cost_bps=bps)
            metric = run_staged(cfg, soxl, soxx, soxl_rows, soxx_rows, timing, dividends, splits, treasury,
                                pd.Timestamp(OOS_START), pd.Timestamp(OOS_END),
                                schedule if cfg.name == "selected_indicator_walk_forward" else None)["metric"]
            stress.append({"cost_bps": bps, **metric})
        metric = run_dynamic(soxl, soxx, dividends, splits, treasury, pd.Timestamp(OOS_START), pd.Timestamp(OOS_END), bps)["metric"]
        stress.append({"cost_bps": bps, **metric})
    zero_yield = run_staged(Config("revised_simple_zero_cash_yield", cash_yield=False), soxl, soxx, soxl_rows,
                            soxx_rows, timing, dividends, splits, None, pd.Timestamp(OOS_START), pd.Timestamp(OOS_END))["metric"]
    dynamic_zero_yield = run_dynamic(soxl, soxx, dividends, splits, None, pd.Timestamp(OOS_START), pd.Timestamp(OOS_END), 10, cash_yield=False)["metric"]

    metric_table = {name: value["metric"] for name, value in results.items()}
    core = metric_table["revised_simple"]
    fold_df = pd.DataFrame(fold_rows)
    gates = {}
    for name in [x for x in metric_table if x not in ("revised_simple", "buy_hold", "existing_staged_replay")]:
        pairs = []
        for number in range(1, 11):
            c = fold_df[(fold_df.fold == number) & (fold_df.strategy == "revised_simple")].iloc[0]
            x = fold_df[(fold_df.fold == number) & (fold_df.strategy == name)].iloc[0]
            pairs.append({"core_return": c.total_return, "candidate_return": x.total_return,
                          "regime": x.regime, "high_volatility": bool(x.high_volatility)})
        state = results[name].get("state")
        event_count = len([t for t in state.trades if t.get("reason") != "fold_initial_normalization"]) if state else max(0, len(results[name].get("trades", [])) - 1)
        gates[name] = acceptance(metric_table[name], core, pairs, event_count)

    # Criterion 4 is a real boolean: both cost stresses must retain a Calmar
    # advantage, and numerical grids need a directionally consistent neighbor.
    stress_lookup = {(float(x["cost_bps"]), x["name"]): x for x in stress}
    adjacent = {
        "rearm_1": ["rearm_2"], "rearm_2": ["rearm_1"],
        "restore_25": ["restore_50"], "restore_50": ["restore_25", "restore_75"],
        "restore_75": ["restore_50", "restore_100"], "restore_100": ["restore_75"],
        "peak_dd_20": ["peak_dd_25"], "peak_dd_25": ["peak_dd_20", "peak_dd_30"],
        "peak_dd_30": ["peak_dd_25", "peak_dd_35"], "peak_dd_35": ["peak_dd_30"],
        "time_stop_10": ["time_stop_20"], "time_stop_20": ["time_stop_10", "time_stop_30"],
        "time_stop_30": ["time_stop_20"],
    }
    for name, gate in gates.items():
        cost_ok = True
        for bps in (20.0, 50.0):
            candidate_stress = stress_lookup.get((bps, name))
            core_stress = stress_lookup.get((bps, "revised_simple"))
            cost_ok = bool(cost_ok and candidate_stress and core_stress and
                           candidate_stress["calmar"] is not None and core_stress["calmar"] is not None and
                           candidate_stress["calmar"] > core_stress["calmar"])
        neighbors = adjacent.get(name)
        adjacent_ok = True if neighbors is None else any(
            metric_table[n]["calmar"] is not None and core["calmar"] is not None and metric_table[n]["calmar"] > core["calmar"]
            for n in neighbors
        )
        gate["criterion_4_cost_and_adjacent_stability"] = bool(cost_ok and adjacent_ok)
        gate["eligible_all_criteria"] = bool(gate["eligible_before_cost_stability"] and gate["criterion_4_cost_and_adjacent_stability"])

    protocol = out / PROTOCOL_NAME
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": "historical_walk_forward_research_not_untouched_future_test",
        "protocol_sha256": sha256(protocol),
        "data_period": {"raw_start": RAW_START, "oos_start": OOS_START, "oos_end": OOS_END},
        "calendar_audit": {"status": "passed", "expected_rows": len(expected), "sources": CALENDAR_SOURCES},
        "data_quality": {"SOXL": q_soxl, "SOXX": q_soxx, "treasury": treasury_quality},
        "corporate_actions": {"SOXL_splits": {k.date().isoformat(): v for k, v in splits.items()},
                              "SOXL_dividends": {k.date().isoformat(): v for k, v in dividends.items()}},
        "execution": {"signal": "completed regular close", "fill": "next valid raw regular open",
                      "base_cost_bps": 10, "stress_bps": [20, 50], "tax_fx": "excluded",
                      "gap": "next open paid in full; never stop price", "halt": "pending frozen"},
        "indicator_selections": selections,
        "metrics": metric_table,
        "fold_independent_metrics": fold_rows,
        "training_selection_metrics": train_table,
        "cost_stress": stress,
        "zero_cash_yield_sensitivity": {"revised_simple": zero_yield, "dynamic_factor_cap_research": dynamic_zero_yield},
        "acceptance_gates": gates,
        "operational_counts": {
            name: {"stale_or_halt_freezes": value["state"].stale_freezes,
                   "gap_through_stop": value["state"].gap_through_stop,
                   "hard_review_count": value["state"].hard_reviews}
            for name, value in results.items() if value.get("state") is not None
        },
        "limitations": [
            "Every fold is historical; walk-forward selection reduces but does not eliminate data-mining risk.",
            "All review alerts are assumed human-approved only for the simulation; live fills/quantities remain unconfirmed.",
            "The dynamic factor-cap study is SOXL-only and cannot validate a portfolio cap including MVLL or NBIL.",
            "Time stops apply only to simulated re-entry lots, never retrospectively to the existing broker holding.",
            "Cash yield uses point-in-time DGS3MO when available; zero-yield sensitivity is reported.",
        ],
    }
    stem = "soxl_walk_forward_2021-08-05_2026-08-04"
    daily.to_csv(out / f"{stem}_daily.csv", index_label="date")
    pd.DataFrame(all_trades).to_csv(out / f"{stem}_trades.csv", index=False)
    pd.DataFrame(fold_rows).to_csv(out / f"{stem}_folds.csv", index=False)
    pd.DataFrame(train_table).to_csv(out / f"{stem}_training_selection.csv", index=False)
    (out / f"{stem}_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"status": "passed", "results": str(out / f"{stem}_results.json"),
                      "metrics": metric_table}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
