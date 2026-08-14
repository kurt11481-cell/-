#!/usr/bin/env python3
"""Deterministic exchange-calendar-relative schedule and finalization retry gates."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from validation_common import canonical_hash


PRE_OPEN = "PRE_OPEN_T_MINUS_30"
POST_CLOSE = "REGULAR_CLOSE_T_PLUS_30"
FINALIZED = "POST_MARKET_FINALIZED"


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("TIMEZONE_AWARE_TIMESTAMP_REQUIRED")
    return parsed


def build_session_schedule(session: dict[str, Any]) -> dict[str, Any]:
    """Build the two logical run times from an already verified official session."""
    if session.get("official_calendar_verified") is not True:
        return {"status": "OFFICIAL_SESSION_UNVERIFIED", "run_count": 0, "order_authority": False}
    if session.get("is_trading_day") is not True:
        return {"status": "MARKET_HOLIDAY", "run_count": 0, "order_authority": False}
    opened = _aware(str(session.get("core_open_at")))
    closed = _aware(str(session.get("core_close_at")))
    if opened.tzinfo is None or closed.tzinfo is None or closed <= opened:
        raise ValueError("OFFICIAL_SESSION_WINDOW_INVALID")
    early_close = (closed.hour, closed.minute) < (16, 0)
    if early_close:
        post_close_scheduled = closed.replace(hour=16, minute=30, second=0, microsecond=0)
        if post_close_scheduled < closed + timedelta(minutes=30):
            raise ValueError("EARLY_CLOSE_POST_RUN_TOO_EARLY")
        retry_at = [post_close_scheduled]
    else:
        post_close_scheduled = closed + timedelta(minutes=30)
        retry_at = [closed + timedelta(minutes=value) for value in (30, 40, 50, 60)]
    scheduled_run_id = canonical_hash({
        "session": session.get("session"), "core_open_at": opened.isoformat(),
        "core_close_at": closed.isoformat(), "calendar_source": session.get("calendar_source"),
    })[:32]
    return {
        "status": "SCHEDULED",
        "session": session.get("session"),
        "timezone": "America/New_York",
        "scheduled_run_id": scheduled_run_id,
        "runs": [
            {"run_phase": PRE_OPEN, "scheduled_at": (opened - timedelta(minutes=30)).isoformat()},
            {"run_phase": POST_CLOSE, "scheduled_at": post_close_scheduled.isoformat()},
        ],
        "official_core_close_at": closed.isoformat(),
        "post_close_earliest_at": (closed + timedelta(minutes=30)).isoformat(),
        "early_close": early_close,
        "late_early_close_validation": early_close,
        "finalization_retry_at": [value.isoformat() for value in retry_at],
        "retry_deadline": (closed + timedelta(minutes=60)).isoformat(),
        "run_count": 2,
        "quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def run_finalization_retry(schedule: dict[str, Any], query: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Run bounded attempts under one scheduled_run_id and deliver at most once."""
    attempts: list[dict[str, Any]] = []
    delivered = False
    for attempted_at in schedule.get("finalization_retry_at") or []:
        result = query(attempted_at)
        finalized = bool(
            result.get("bar_finalized") is True and result.get("stable") is True
            and result.get("market_session_type") == "REGULAR_COMPLETED"
            and result.get("price_semantics") == "CLOSE"
            and result.get("reported_session") == schedule.get("session")
        )
        attempts.append({"attempted_at": attempted_at, "finalized": finalized,
                         "provider_status": result.get("status")})
        if finalized:
            delivered = True
            return {
                "scheduled_run_id": schedule.get("scheduled_run_id"), "run_phase": FINALIZED,
                "finalization_status": "VALIDATED", "attempts": attempts,
                "delivery_count": 1, "valid_finalized_session_increment": 1,
                "quantity": None, "quantity_authority": "none", "order_authority": False,
            }
    return {
        "scheduled_run_id": schedule.get("scheduled_run_id"), "run_phase": POST_CLOSE,
        "finalization_status": "FINALIZATION_PENDING", "attempts": attempts,
        "delivery_count": 0 if not delivered else 1, "valid_finalized_session_increment": 0,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }


def preopen_authority(prior_state: str, requested_state: str) -> dict[str, Any]:
    upgrades = {("WATCH", "READY"), ("NEAR_TRIGGER", "READY")}
    resulting = prior_state if (prior_state, requested_state) in upgrades else requested_state
    return {
        "run_phase": PRE_OPEN, "prior_state": prior_state, "requested_state": requested_state,
        "resulting_state": resulting, "finalized_session_increment": 0,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
