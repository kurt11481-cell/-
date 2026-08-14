#!/usr/bin/env python3
"""Build and validate independent readiness axes without implicit upgrades."""

from __future__ import annotations

from typing import Any


PRICE = {
    "KIWOOM_VALID", "KIWOOM_API_ERROR", "KIWOOM_DATA_MISSING", "KIWOOM_STALE",
    "KIWOOM_WRONG_TICKER", "KIWOOM_SECURITY_IDENTITY_MISMATCH",
    "KIWOOM_UNKNOWN_PRICE_SEMANTICS", "KIWOOM_UNKNOWN_MARKET_PHASE",
    "KIWOOM_SCALE_OR_CURRENCY_ERROR", "KIWOOM_CORPORATE_ACTION_AMBIGUITY",
    "NOT_APPLICABLE", "NOT_EVALUATED",
}
VOLUME = {"KIWOOM_VALID_SCOPED", "YFINANCE_SCOPED_FALLBACK", "UNRESOLVED", "UNAVAILABLE", "NOT_APPLICABLE", "NOT_EVALUATED"}
TECHNICAL = {"READY", "WATCH", "RVOL20_NOT_MET", "HISTORY_FALLBACK_REQUIRED", "CONDITION_NOT_MET", "INVALID", "UNAVAILABLE", "NOT_EVALUATED"}
EVENT = {"COMPLETE", "PARTIAL_NONBLOCKING", "PARTIAL_BLOCKING", "UNAVAILABLE", "INVALID", "NOT_EVALUATED"}
BROKER = {"VERIFIED", "PARTIAL", "UNKNOWN", "STALE", "NOT_REQUIRED", "NOT_EVALUATED"}


def state_axes(*, ticker: str, decision_class: str, price: str, volume: str,
               technical: str, event: str, broker: str) -> dict[str, Any]:
    if price not in PRICE or volume not in VOLUME or technical not in TECHNICAL or event not in EVENT or broker not in BROKER:
        raise ValueError("ORTHOGONAL_STATE_VALUE_INVALID")
    return {
        "ticker": ticker, "decision_class": decision_class,
        "price_authority_status": price, "volume_authority_status": volume,
        "technical_condition_status": technical, "event_readiness_status": event,
        "broker_visibility_status": broker, "execution_authority_status": "NONE",
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }


def no_axis_implies_execution(value: dict[str, Any]) -> bool:
    return (
        value.get("execution_authority_status") == "NONE"
        and value.get("quantity") is None
        and value.get("quantity_authority") == "none"
        and value.get("order_authority") is False
    )
