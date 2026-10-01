"""Synthetic inputs for the S5 exposure tests. No real holdings, prices or account data are used."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "stock-strategy-system/alert_policy.json"
GENESIS = "0" * 64


def real_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def weekday_sessions(count: int, end: str = "2026-09-30", extra_after: int = 5) -> list[str]:
    """`count` weekday dates ending at `end`, plus a few later weekdays (the next sessions)."""
    days: list[str] = []
    cursor = date.fromisoformat(end)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    days.reverse()
    cursor = date.fromisoformat(end) + timedelta(days=1)
    later: list[str] = []
    while len(later) < extra_after:
        if cursor.weekday() < 5:
            later.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days + later


def benchmark_returns(count: int, seed: int = 7) -> list[float]:
    generator = random.Random(seed)
    return [generator.uniform(-0.02, 0.02) for _ in range(count)]


def series(sessions: list[str], returns: list[float], *, last: str = "100", multiple: float = 1.0) -> dict[str, str]:
    """Closes whose daily returns are `multiple` x `returns`, scaled so the last close is exactly `last`."""
    values = [1.0]
    for value in returns[:len(sessions) - 1]:
        values.append(values[-1] * (1.0 + multiple * value))
    scale = float(last) / values[-1]
    closes = {session: f"{value * scale:.6f}" for session, value in zip(sessions, values)}
    closes[sessions[-1]] = last
    return closes


def flat_series(sessions: list[str], price: str) -> dict[str, str]:
    return {session: price for session in sessions}


def snapshot(as_of: str, holdings: dict[str, int], cash: str, *, revision: int = 1, decreased: bool = False,
             block: Any = None, from_entry: bool = True) -> dict[str, Any]:
    """One confirmed reconciliation. By default it is confirmed by a ledger entry, as real ones are."""
    return {"as_of": as_of, "state_revision": revision, "holdings": dict(holdings), "cash_usd": cash,
            "holdings_decreased": decreased, "cash_flow_declaration": block, "from_ledger_entry": from_entry}


def journal(*entries: dict[str, Any], status: str = "OK") -> dict[str, Any]:
    return {"status": status, "entries": list(entries), "errors": []}


def activation_entry(activation_date: str, hwm: str, *, revision: int = 1, hwm_as_of: str | None = None) -> dict[str, Any]:
    return {"entry_type": "s5_activation", "entry_id": "a" * 64,
            "payload": {"activation_date": activation_date, "hwm_usd": hwm, "hwm_as_of": hwm_as_of or activation_date,
                        "state_revision": revision}}


def line_review_entry(line_id: str, hwm: str, breach_date: str, *, conclusion: str = "continue") -> dict[str, Any]:
    return {"entry_type": "line_review_completed", "entry_id": "b" * 64,
            "payload": {"line_id": line_id, "hwm": hwm, "breach_date": breach_date, "review_status": "completed",
                        "conclusion": conclusion, "conclusion_note": ""}}


def peak_review_entry(symbol: str, peak: str, breach_date: str) -> dict[str, Any]:
    return {"entry_type": "peak_review_card_completed", "entry_id": "c" * 64,
            "payload": {"symbol": symbol, "peak": peak, "peak_date": breach_date, "breach_date": breach_date,
                        "review_status": "completed"}}


def verified_earnings(symbols: list[str], announcement_session: str) -> dict[str, Any]:
    return {symbol: {"status": "VERIFIED", "announcement_session": announcement_session, "timing": "AFTER_CLOSE"}
            for symbol in symbols}


def decimal_text(value: Decimal) -> str:
    return format(value, "f")
