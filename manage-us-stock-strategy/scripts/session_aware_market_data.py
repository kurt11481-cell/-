#!/usr/bin/env python3
"""Session-aware price normalization and deterministic comparability gates."""

from __future__ import annotations

import math
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
MARKET_SESSION_TYPES = {
    "PRE_MARKET", "REGULAR_INTRADAY", "REGULAR_COMPLETED", "AFTER_HOURS",
    "DAY_MARKET", "OVERNIGHT", "MARKET_CLOSED", "UNKNOWN",
}
PRICE_OR_QUOTE_TYPES = {
    "RAW_REGULAR_SESSION_CLOSE", "REGULAR_SESSION_LAST", "PREMARKET_LAST",
    "AFTER_HOURS_LAST", "DAY_MARKET_LAST", "OVERNIGHT_LAST", "BID", "ASK",
    "MID", "BROKER_MARK", "UNKNOWN",
}
EXTENDED_SESSION_TYPES = {"PRE_MARKET", "AFTER_HOURS", "DAY_MARKET", "OVERNIGHT"}


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("provider timestamp must be timezone-aware")
    return parsed


def _finite_positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(float(value)) and float(value) > 0
    )


def _timestamp_can_observe_completed_close(record: dict[str, Any]) -> bool:
    """Require a retrieval timestamp at or after the reported 16:00 ET close."""
    try:
        session = date.fromisoformat(str(record.get("reported_session")))
        observed = _timestamp(str(record.get("provider_timestamp"))).astimezone(ET)
    except (TypeError, ValueError):
        return False
    session_close = datetime.combine(session, time(16, 0), tzinfo=ET)
    return observed >= session_close


def market_session_at(
    provider_timestamp: str, *, explicit_session_type: str | None = None,
    is_official_trading_day: bool = True,
) -> str:
    """Classify the observation clock; never infer its price basis from time."""
    if explicit_session_type is not None:
        if explicit_session_type not in MARKET_SESSION_TYPES:
            raise ValueError("unknown explicit market session type")
        return explicit_session_type
    observed = _timestamp(provider_timestamp).astimezone(ET)
    if not is_official_trading_day or observed.weekday() >= 5:
        return "MARKET_CLOSED"
    wall = observed.timetz().replace(tzinfo=None)
    if time(4, 0) <= wall < time(9, 30):
        return "PRE_MARKET"
    if time(9, 30) <= wall < time(16, 0):
        return "REGULAR_INTRADAY"
    if time(16, 0) <= wall < time(20, 0):
        return "AFTER_HOURS"
    return "OVERNIGHT"


def _record(
    *, ticker: str, provider: str, market_session_type: str,
    reported_session: str | None, price_basis: str, quote_type: str,
    price: float | None, provider_timestamp: str, source_identifier: str,
    source_field: str, classification_basis: str, bar_finalized: bool,
    stable: bool, comparable_to_regular_close: bool, indicative_only: bool,
    daily_indicator_authority: bool, hard_risk_authority: bool,
    exchange_timestamp: str | None = None, currency: str = "USD",
    security_identity_status: str = "VERIFIED",
) -> dict[str, Any]:
    if market_session_type not in MARKET_SESSION_TYPES:
        raise ValueError("invalid market_session_type")
    if price_basis not in PRICE_OR_QUOTE_TYPES or quote_type not in PRICE_OR_QUOTE_TYPES:
        raise ValueError("invalid price or quote type")
    if price is not None and not _finite_positive(price):
        raise ValueError("price must be positive and finite")
    if market_session_type in EXTENDED_SESSION_TYPES and (
        daily_indicator_authority or hard_risk_authority or bar_finalized
    ):
        raise ValueError("extended-session data cannot own daily indicators or hard risk")
    return {
        "schema_version": "1.0", "ticker": ticker.upper(), "provider": provider,
        "security_identity_status": security_identity_status,
        "market_session_type": market_session_type,
        "reported_session": reported_session, "price_basis": price_basis,
        "quote_type": quote_type, "price": float(price) if price is not None else None,
        "currency": currency, "provider_timestamp": provider_timestamp,
        "exchange_timestamp": exchange_timestamp,
        "source_identifier": source_identifier, "source_field": source_field,
        "session_classification_basis": classification_basis,
        "bar_finalized": bool(bar_finalized), "stable": bool(stable),
        "comparable_to_regular_close": bool(comparable_to_regular_close),
        "indicative_only": bool(indicative_only),
        "daily_indicator_authority": bool(daily_indicator_authority),
        "hard_risk_authority": bool(hard_risk_authority),
        "order_authority": False,
    }


def kiwoom_daily_observation(
    *, ticker: str, reported_session: str, close: float | None,
    provider_timestamp: str, identity_verified: bool = True,
    official_session_verified: bool = True,
) -> dict[str, Any]:
    """Normalize usa06012 without calling a same-day row a finalized close."""
    observed_et = _timestamp(provider_timestamp).astimezone(ET)
    archived = bool(
        official_session_verified and reported_session < observed_et.date().isoformat()
    )
    if archived:
        return _record(
            ticker=ticker, provider="KIWOOM_REST", market_session_type="REGULAR_COMPLETED",
            reported_session=reported_session, price_basis="RAW_REGULAR_SESSION_CLOSE",
            quote_type="REGULAR_SESSION_LAST", price=close,
            provider_timestamp=provider_timestamp, source_identifier="usa06012:/api/us/chart",
            source_field="result_list.cur_prc", classification_basis="NEXT_ET_CALENDAR_DAY_PROVIDER_ARCHIVE",
            bar_finalized=True, stable=True, comparable_to_regular_close=True,
            indicative_only=False, daily_indicator_authority=True,
            hard_risk_authority=True,
            security_identity_status="VERIFIED" if identity_verified else "IDENTITY_MISMATCH",
        )
    phase = market_session_at(provider_timestamp, is_official_trading_day=official_session_verified)
    return _record(
        ticker=ticker, provider="KIWOOM_REST", market_session_type=phase,
        reported_session=reported_session, price_basis="UNKNOWN", quote_type="BROKER_MARK",
        price=close, provider_timestamp=provider_timestamp,
        source_identifier="usa06012:/api/us/chart", source_field="result_list.cur_prc",
        classification_basis="SAME_ET_DATE_DAILY_ROW_HAS_NO_FINALIZATION_FIELD",
        bar_finalized=False, stable=False, comparable_to_regular_close=False,
        indicative_only=True, daily_indicator_authority=False, hard_risk_authority=False,
        security_identity_status="VERIFIED" if identity_verified else "IDENTITY_MISMATCH",
    )


def yfinance_regular_close_observation(
    *, ticker: str, reported_session: str, close: float | None,
    provider_timestamp: str, identity_verified: bool = True,
) -> dict[str, Any]:
    return _record(
        ticker=ticker, provider="yfinance", market_session_type="REGULAR_COMPLETED",
        reported_session=reported_session, price_basis="RAW_REGULAR_SESSION_CLOSE",
        quote_type="REGULAR_SESSION_LAST", price=close,
        provider_timestamp=provider_timestamp, source_identifier="Yahoo chart via yfinance",
        source_field="chart.indicators.quote.close", classification_basis="PREPOST_FALSE_OFFICIAL_SESSION_VALIDATED",
        bar_finalized=True, stable=True, comparable_to_regular_close=True,
        indicative_only=False, daily_indicator_authority=False, hard_risk_authority=False,
        security_identity_status="VERIFIED" if identity_verified else "IDENTITY_MISMATCH",
    )


def kiwoom_broker_quote_observation(
    *, ticker: str, reported_session: str | None, price: float | None,
    provider_timestamp: str, source_field: str = "cur_prc",
    explicit_session_type: str | None = None,
) -> dict[str, Any]:
    phase = market_session_at(provider_timestamp, explicit_session_type=explicit_session_type)
    return _record(
        ticker=ticker, provider="KIWOOM_REST", market_session_type=phase,
        reported_session=reported_session, price_basis="BROKER_MARK", quote_type="BROKER_MARK",
        price=price, provider_timestamp=provider_timestamp,
        source_identifier="usa20100:/api/us/mrkcond", source_field=source_field,
        classification_basis="BROKER_CURRENT_PRICE_FIELD_PLUS_EXPLICIT_SESSION_CLOCK",
        bar_finalized=False, stable=False, comparable_to_regular_close=False,
        indicative_only=True, daily_indicator_authority=False, hard_risk_authority=False,
    )


def compare_price_observations(
    left: dict[str, Any], right: dict[str, Any], *,
    tolerance_policy: dict[str, Any], decision_boundary: float | None = None,
    timestamps_compatible: bool = True,
) -> dict[str, Any]:
    """Apply comparability gates before the existing approved close tolerance."""
    def result(status: str, reason: str, *, absolute: float | None = None,
               relative: float | None = None, tolerance: float | None = None,
               flip: bool = False) -> dict[str, Any]:
        return {
            "comparison_status": status, "reason_code": reason,
            "absolute_difference": absolute, "relative_difference": relative,
            "tolerance_usd": tolerance, "decision_boundary_flip": flip,
            "web_resolution_required": bool(status == "CONFLICT"),
        }

    if left.get("security_identity_status") != "VERIFIED" or right.get("security_identity_status") != "VERIFIED" or left.get("ticker") != right.get("ticker"):
        return result("NOT_COMPARABLE", "IDENTITY_MISMATCH")
    if left.get("reported_session") != right.get("reported_session"):
        return result("NOT_COMPARABLE", "NOT_COMPARABLE_SESSION")
    if not left.get("bar_finalized") or not right.get("bar_finalized"):
        return result("NOT_COMPARABLE", "FINALIZATION_PENDING")
    if not left.get("stable") or not right.get("stable"):
        return result("NOT_COMPARABLE", "BAR_UNSTABLE")
    if left.get("market_session_type") != right.get("market_session_type"):
        return result("NOT_COMPARABLE", "NOT_COMPARABLE_SESSION")
    if left.get("market_session_type") != "REGULAR_COMPLETED":
        return result("NOT_COMPARABLE", "NOT_COMPARABLE_SESSION")
    if left.get("quote_type") != right.get("quote_type"):
        return result("NOT_COMPARABLE", "QUOTE_TYPE_MISMATCH")
    if left.get("price_basis") != right.get("price_basis"):
        return result("NOT_COMPARABLE", "PRICE_BASIS_MISMATCH")
    if left.get("currency") != "USD" or right.get("currency") != "USD":
        return result("NOT_COMPARABLE", "PRICE_BASIS_MISMATCH")
    if (
        not timestamps_compatible
        or not _timestamp_can_observe_completed_close(left)
        or not _timestamp_can_observe_completed_close(right)
    ):
        return result("NOT_COMPARABLE", "TIMESTAMP_MISMATCH")
    if not left.get("comparable_to_regular_close") or not right.get("comparable_to_regular_close"):
        return result("NOT_COMPARABLE", "PRICE_BASIS_MISMATCH")
    if not _finite_positive(left.get("price")) or not _finite_positive(right.get("price")):
        return result("NOT_EVALUATED", "PRICE_UNAVAILABLE")
    left_price, right_price = float(left["price"]), float(right["price"])
    absolute = abs(left_price - right_price)
    relative = absolute / abs(right_price)
    tolerance = max(
        float(tolerance_policy["absolute_usd_floor"]),
        float(tolerance_policy["relative_fraction"]) * abs(right_price),
    )
    flip = bool(
        decision_boundary is not None
        and ((left_price < float(decision_boundary)) != (right_price < float(decision_boundary)))
    )
    if flip:
        return result("CONFLICT", "DECISION_BOUNDARY_FLIP", absolute=absolute, relative=relative, tolerance=tolerance, flip=True)
    if absolute > tolerance:
        return result("CONFLICT", "OUTSIDE_TOLERANCE", absolute=absolute, relative=relative, tolerance=tolerance)
    return result("MATCH", "WITHIN_TOLERANCE", absolute=absolute, relative=relative, tolerance=tolerance)


def reclassify_prior_result(comparison: dict[str, Any]) -> str:
    status = comparison.get("comparison_status")
    reason = comparison.get("reason_code")
    if status == "MATCH":
        return "MATCH"
    if status == "CONFLICT":
        return "TRUE_REGULAR_CLOSE_CONFLICT"
    if reason == "FINALIZATION_PENDING":
        return "FINALIZATION_PENDING"
    if reason == "BAR_UNSTABLE":
        return "BAR_UNSTABLE"
    if reason == "NOT_COMPARABLE_SESSION":
        return "FALSE_CONFLICT_SESSION_MISMATCH"
    if reason in {"PRICE_BASIS_MISMATCH", "QUOTE_TYPE_MISMATCH"}:
        return "FALSE_CONFLICT_PRICE_BASIS_MISMATCH"
    if reason == "TIMESTAMP_MISMATCH":
        return "SESSION_LAG"
    return "UNRESOLVED"


def apply_extended_hours_guard(
    *, prior_state: str, requested_state: str | None = None,
    hard_risk_requested: bool = False,
) -> dict[str, Any]:
    """Extended hours may preserve or downgrade, never upgrade or breach."""
    rank = {"DATA_BLOCKED": 0, "WATCH": 1, "NEAR_TRIGGER": 2, "READY": 3}
    requested = requested_state or prior_state
    state = requested if rank.get(requested, -1) <= rank.get(prior_state, -1) else prior_state
    return {
        "prior_state": prior_state, "resulting_state": state,
        "hard_risk_state": "PREMARKET_RISK_WATCH" if hard_risk_requested else "NONE",
        "daily_indicator_confirmation": False, "quantity": None,
        "order_authority": False,
    }
