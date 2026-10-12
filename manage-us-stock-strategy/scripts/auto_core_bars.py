#!/usr/bin/env python3
"""Redesign T2 F1: regular-session daily bars (open, high, low, close, volume) from the saved 30-minute pages.

Read only: the pages under workspace/outputs/regular-session-closes/pages/<SYMBOL>/ are the same evidence files
regular_session_close_history.py verifies. A session's bars are the 30-minute bars labelled from core_open_at
(09:30 Eastern on every session) through the final regular bar (30 minutes before core_close_at, so an early
close follows the operating calendar). The close is the close history's value (build_history on the same pages
and calendar), so it always equals the stored close definition. When any regular bar of a session is missing,
that session's high, low and volume are INCOMPLETE (None) and only the rules that use them become unknown.

Split adjustment uses the official record (corporate-actions.json): prices before an effective session are
multiplied by old/new (corporate_actions.adjust_closes, reused field by field) and volumes by new/old. A
close-to-close jump the record does not explain is SPLIT_SUSPECTED: every indicator of that symbol is unknown.
Nothing here calls Kiwoom, writes a file or reads a clock.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from corporate_actions import adjust_closes, applicable_actions, applied_summary
from regular_session_close_history import (
    INTERVAL_MINUTES, CloseHistoryError, build_history, closes_by_session, parse_page,
)


# Data check, not a strategy threshold (prompt F1): a close-to-close move at least this large whose ratio is
# within SPLIT_RATIO_TOLERANCE of k or 1/k for one of SPLIT_FACTORS is treated as an unrecorded split.
SPLIT_MOVE_MINIMUM = Decimal("0.45")
SPLIT_RATIO_TOLERANCE = Decimal("0.03")
SPLIT_FACTORS = (2, 3, 4, 5, 8, 10, 15, 20)
INCOMPLETE = "INCOMPLETE"


def _decimal(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return number if number.is_finite() else None


def regular_labels(session_row: dict[str, Any]) -> list[str]:
    """cntr_tm labels (bar start, Eastern wall clock) of every regular-session bar of one calendar session."""
    opened = datetime.fromisoformat(session_row["core_open_at"])
    final = datetime.fromisoformat(session_row["core_close_at"]) - timedelta(minutes=INTERVAL_MINUTES)
    labels = []
    moment = opened
    while moment <= final:
        labels.append(moment.strftime("%Y%m%d%H%M%S"))
        moment += timedelta(minutes=INTERVAL_MINUTES)
    return labels


def _page_body_rows(path: Path) -> list[dict[str, Any]]:
    """The raw rows of a page parse_page has accepted (same wrapper rule as parse_page)."""
    document = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    body = document["result"] if "result" in document and "result_list" not in document else document
    return list(body["result_list"])


def confirmed_bars(page_paths: list[Path]) -> tuple[dict[str, dict[str, Decimal | None]], list[str]]:
    """{cntr_tm: {open, high, low, close, volume}} of every confirmed bar (a later bar exists in the same page).

    parse_page validates each page first (row keys, times, prices, adjustment fields). A bar seen in two pages
    with a different close is an error (as in build_history); a different open, high, low or volume keeps the
    first value and marks the bar conflicting (its session becomes incomplete).
    """
    bars: dict[str, dict[str, Any]] = {}
    conflicts: list[str] = []
    for path in sorted(page_paths, key=lambda item: Path(item).name):
        parse_page(Path(path))
        for row in _page_body_rows(Path(path))[1:]:
            values = {"open": _decimal(row["open_pric"]), "high": _decimal(row["high_pric"]),
                      "low": _decimal(row["low_pric"]), "close": _decimal(row["cur_prc"]),
                      "volume": _decimal(row["trde_qty"])}
            known = bars.get(row["cntr_tm"])
            if known is None:
                bars[row["cntr_tm"]] = values
            elif known["close"] != values["close"]:
                raise CloseHistoryError(f"PAGE_ROWS_CONFLICT:{row['cntr_tm']}")
            elif known != values:
                conflicts.append(row["cntr_tm"])
    return bars, sorted(set(conflicts))


def daily_bars(symbol: str, pages_dir: Path, calendar: dict[str, Any], *, exchange: str = "NASDAQ"
               ) -> dict[str, Any]:
    """{status OK|MISSING|INVALID, errors, sessions {date: bar}} for one symbol (raw, unadjusted prices)."""
    page_paths = sorted(Path(pages_dir).glob("*.json")) if Path(pages_dir).is_dir() else []
    if not page_paths:
        return {"symbol": symbol, "status": "MISSING", "errors": ["PAGES_MISSING"], "sessions": {},
                "continuity_gaps": []}
    try:
        history = build_history(symbol=symbol, exchange=exchange, page_paths=page_paths, calendar=calendar)
        bars, conflicts = confirmed_bars(page_paths)
    except (CloseHistoryError, OSError, ValueError, KeyError, TypeError) as exc:
        return {"symbol": symbol, "status": "INVALID", "errors": [f"BARS_INVALID:{exc}"], "sessions": {},
                "continuity_gaps": []}
    closes = closes_by_session(history)
    sessions: dict[str, dict[str, Any]] = {}
    for session_date, close in closes.items():
        labels = regular_labels(calendar["sessions"][session_date])
        present = [bars.get(label) for label in labels]
        reasons = []
        if any(item is None for item in present):
            reasons.append("REGULAR_BAR_MISSING")
        if any(label in conflicts for label in labels):
            reasons.append("BAR_FIELD_CONFLICT")
        complete = not reasons and all(item[key] is not None for item in present
                                       for key in ("high", "low", "volume"))
        first = present[0] if present else None
        sessions[session_date] = {
            "open": first["open"] if first else None,
            "high": max(item["high"] for item in present) if complete else None,
            "low": min(item["low"] for item in present) if complete else None,
            "close": Decimal(close),
            "volume": sum((item["volume"] for item in present), Decimal(0)) if complete else None,
            "complete": complete, "reasons": reasons or ([] if complete else [INCOMPLETE]),
        }
    return {"symbol": symbol, "status": "OK", "errors": [], "sessions": sessions,
            "continuity_gaps": list(history["continuity"]["missing_sessions"])}


def adjust_bars(bars: dict[str, Any], actions: list[dict[str, Any]], evaluation_session: str
                ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Split-adjusted copy (prices x old/new, volume x new/old before each effective session in effect)."""
    symbol = bars["symbol"]
    in_effect = [action for action in applicable_actions(actions, evaluation_session) if action["symbol"] == symbol]
    adjusted = {**bars, "sessions": {day: dict(bar) for day, bar in bars["sessions"].items()}}
    if not in_effect:
        return adjusted, []
    for field in ("open", "high", "low", "close"):
        series = {day: format(bar[field], "f") for day, bar in bars["sessions"].items() if bar[field] is not None}
        for day, value in adjust_closes({symbol: series}, in_effect)[symbol].items():
            adjusted["sessions"][day][field] = Decimal(value)
    for day, bar in adjusted["sessions"].items():
        if bar["volume"] is None:
            continue
        numerator, denominator = 1, 1
        for action in in_effect:
            if day < action["effective_session"]:
                numerator *= action["new_shares"]
                denominator *= action["old_shares"]
        bar["volume"] = bar["volume"] * numerator / denominator
    return adjusted, applied_summary(in_effect)


def split_suspects(bars: dict[str, Any], through: str) -> list[str]:
    """SPLIT_SUSPECTED:<symbol>:<session> for an unexplained split-sized close jump on or before `through`."""
    days = sorted(day for day in bars["sessions"] if day <= through)
    found = []
    for previous, current in zip(days, days[1:]):
        before, after = bars["sessions"][previous]["close"], bars["sessions"][current]["close"]
        if not before or before <= 0:
            continue
        ratio = after / before
        if abs(ratio - 1) < SPLIT_MOVE_MINIMUM:
            continue
        for factor in SPLIT_FACTORS:
            if abs(ratio / factor - 1) <= SPLIT_RATIO_TOLERANCE or abs(ratio * factor - 1) <= SPLIT_RATIO_TOLERANCE:
                found.append(f"SPLIT_SUSPECTED:{bars['symbol']}:{current}")
                break
    return found


def load_symbol(symbol: str, *, pages_root: Path, calendar: dict[str, Any], corporate_actions: dict[str, Any],
                evaluation_session: str, exchange: str = "NASDAQ") -> dict[str, Any]:
    """Raw and adjusted bars of one symbol with the adjustment evidence and the split check.

    An INVALID corporate-action record adjusts nothing and makes the symbol unusable (status INVALID), the same
    fail-closed reading the exposure review uses.
    """
    raw = daily_bars(symbol, Path(pages_root) / symbol, calendar, exchange=exchange)
    result = {"symbol": symbol, "status": raw["status"], "errors": list(raw["errors"]), "raw": raw,
              "adjusted": raw, "applied_actions": [], "split_suspects": [],
              "continuity_gaps": raw["continuity_gaps"]}
    if raw["status"] != "OK":
        return result
    if corporate_actions.get("status") == "INVALID":
        result.update(status="INVALID", errors=["CORPORATE_ACTIONS_INVALID"])
        return result
    actions = list(corporate_actions.get("actions") or []) if corporate_actions.get("status") == "OK" else []
    adjusted, applied = adjust_bars(raw, actions, evaluation_session)
    for item in applied:
        action = next(action for action in actions if action["symbol"] == symbol
                      and action["effective_session"] == item["effective_session"])
        item["source_url"] = action["official_source"]["url"]
        item["record_id"] = f"{symbol}:{item['effective_session']}"
    result.update(adjusted=adjusted, applied_actions=applied,
                  split_suspects=split_suspects(adjusted, evaluation_session))
    return result
