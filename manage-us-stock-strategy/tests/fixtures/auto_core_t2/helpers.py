"""Synthetic inputs for the redesign T2 tests (TEST_ONLY).

Calendars, regular-session bars, registry entries and S7 reviews built from made-up values: no account data,
no network, no Kiwoom runtime. The S7 review is built with portfolio_exposure.build_exposure_review on a fixed
portfolio activated at the first session (the replay assumption), so the gates read the real S7 code.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
ET = ZoneInfo("America/New_York")
POLICY_PATH = ROOT / "stock-strategy-system/alert_policy.json"


def sessions(start: str, count: int) -> list[str]:
    """`count` weekday sessions from `start` (no holidays)."""
    day, out = date.fromisoformat(start), []
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day.isoformat())
        day += timedelta(days=1)
    return out


def calendar(days: list[str]) -> dict[str, Any]:
    rows = {}
    for day in days:
        opened = datetime.combine(date.fromisoformat(day), time(9, 30), tzinfo=ET)
        closed = datetime.combine(date.fromisoformat(day), time(16, 0), tzinfo=ET)
        rows[day] = {"session_date": day, "core_open_at": opened.isoformat(), "core_close_at": closed.isoformat(),
                     "close_type": "REGULAR"}
    return {"sessions": rows, "identity": {"calendar_version": "TEST_ONLY", "calendar_sha256": "0" * 64,
                                           "coverage_start": days[0], "coverage_end": days[-1],
                                           "authority_status": "ACTIVE"}}


def bars(symbol: str, days: list[str], closes: list[float], *, highs: list[float] | None = None,
         lows: list[float] | None = None, volumes: list[float] | None = None,
         incomplete: set[str] | None = None) -> dict[str, Any]:
    """A load_symbol-shaped result (raw = adjusted, no split record)."""
    incomplete = incomplete or set()
    data = {}
    for index, day in enumerate(days):
        close = Decimal(str(closes[index]))
        full = day not in incomplete
        data[day] = {
            "open": close, "close": close,
            "high": (Decimal(str(highs[index])) if highs else close * Decimal("1.01")) if full else None,
            "low": (Decimal(str(lows[index])) if lows else close * Decimal("0.99")) if full else None,
            "volume": (Decimal(str(volumes[index])) if volumes else Decimal(1000)) if full else None,
            "complete": full, "reasons": [] if full else ["INCOMPLETE"]}
    raw = {"symbol": symbol, "status": "OK", "errors": [], "sessions": data, "continuity_gaps": []}
    return {"symbol": symbol, "status": "OK", "errors": [], "raw": raw, "adjusted": raw, "applied_actions": [],
            "split_suspects": [], "continuity_gaps": []}


def missing_bars(symbol: str) -> dict[str, Any]:
    raw = {"symbol": symbol, "status": "MISSING", "errors": ["PAGES_MISSING"], "sessions": {}, "continuity_gaps": []}
    return {"symbol": symbol, "status": "MISSING", "errors": ["PAGES_MISSING"], "raw": raw, "adjusted": raw,
            "applied_actions": [], "split_suspects": [], "continuity_gaps": []}


def ramp(count: int, start: float, step: float) -> list[float]:
    return [round(start + step * index, 4) for index in range(count)]


def zigzag(count: int, start: float, amplitude: float, drift: float = 0.0) -> list[float]:
    """Alternating closes (keeps sigma60 and ATR positive)."""
    return [round(start + drift * index + (amplitude if index % 2 else -amplitude), 4) for index in range(count)]


def entry(symbol: str, *, role: str = "watch", triggers: list[dict[str, Any]] | None = None,
          static: list[dict[str, Any]] | None = None, action: str = "WATCH", trim: float | None = None,
          sector: str | None = None) -> dict[str, Any]:
    return {"role": role, "card_doc": "docs/claude/TEST_ONLY.md", "card_section": f"## {symbol}",
            "section_sha256": "0" * 64, "accepted": {"text": "TEST_ONLY", "date": "2026-10-01",
                                                     "source": "docs/claude/TEST_ONLY.md:1"},
            "card_action": action, "trim_target_weight": trim, "trigger_set": symbol[:2], "sector": sector,
            "rg2_benchmark": "SOXX", "official_domains": ["example.com"], "c8": None,
            "card_triggers": triggers or [], "static_evidence": static or [], "kill_refs": [], "known_events": []}


def check(symbol: str, entry_value: dict[str, Any] | None, *, eligible: bool = True, hash_ok: bool = True,
          reasons: list[str] | None = None) -> dict[str, Any]:
    return {"symbol": symbol, "entry": entry_value, "eligible": eligible and entry_value is not None,
            "reasons": list(reasons or ([] if eligible and entry_value is not None else ["NOCARD"])),
            "hash_ok": hash_ok and entry_value is not None, "accepted": True}


def policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def activation_journal(hwm: Decimal, day: str) -> dict[str, Any]:
    return {"status": "OK", "errors": [], "entries": [
        {"entry_type": "s5_activation", "entry_id": "test-activation",
         "payload": {"hwm_usd": format(hwm, "f"), "activation_date": day, "hwm_as_of": day, "state_revision": 1}}]}


def s7_runner(*, policy_value: dict[str, Any], days: list[str], evaluation_session: str, holdings: dict[str, int],
              cash: Decimal, closes: dict[str, dict[str, str]], earnings: dict[str, Any] | None = None,
              activation_day: str | None = None):
    """A callable(proposals) -> S7 review on a fixed portfolio, activated at `activation_day` (default: the
    evaluation session minus nothing - the first of the last 3 sessions)."""
    from portfolio_exposure import build_exposure_review, closing_equity

    span = [day for day in days if day <= evaluation_session]
    activation_day = activation_day or span[-3]
    snapshots = [{"as_of": day, "state_revision": 1, "holdings": dict(holdings), "cash_usd": str(cash),
                  "holdings_decreased": False, "cash_flow_declaration": None, "from_ledger_entry": True}
                 for day in span if day >= activation_day]
    equity, _values, _missing = closing_equity(snapshots[0], closes, activation_day)
    journal = activation_journal(equity if equity is not None else Decimal(1), activation_day)
    generated = datetime.combine(date.fromisoformat(evaluation_session), time(17, 0), tzinfo=ET)
    generated_at = generated.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def run(proposals: list[dict[str, Any]]) -> dict[str, Any]:
        return build_exposure_review(
            policy=policy_value, evaluation_session=evaluation_session, calendar_sessions=days, snapshots=snapshots,
            snapshot_reasons=[], closes=closes, close_unverified={}, journal=journal, earnings=earnings,
            proposals=proposals, inputs={"generated_at": generated_at}, generated_at=generated_at)

    return run


def closes_of(bars_by_symbol: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    return {symbol: {day: format(bar["close"], "f") for day, bar in item["raw"]["sessions"].items()}
            for symbol, item in bars_by_symbol.items() if item["status"] == "OK"}


def fill_row(ticker: str, side: str, *, ordered: int, filled: int, price: str, fill_price: str | None = None,
             kind: str = "Limit On Close", cancelled: int = 0, status: str = "TEST_ONLY") -> dict[str, Any]:
    """A sanitized ust21150 row (SAFE_FIELDS only, synthetic)."""
    return {"ord_no": "0000001", "crnc_code": "USD", "stk_cd": ticker, "slby_tp_nm": side, "frgn_trde_tp": kind,
            "ord_qty": f"{ordered:012d}", "cntr_qty": f"{filled:012d}", "cncl_qty": f"{cancelled:012d}",
            "ord_remnq": "000000000000", "ord_uv": price, "cntr_uv": fill_price or (price if filled else "0"),
            "ord_time": "17:30:00", "cntr_time": "05:00:02" if filled else "", "ord_stat_nm": status, "rsrv_tp": "0"}
