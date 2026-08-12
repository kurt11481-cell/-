#!/usr/bin/env python3
"""Shared deterministic portfolio-policy gates for v2.4.

The helpers in this module never mutate portfolio or policy state.  They expose
cash and hard-risk authority as explicit, auditable statuses so research code
cannot turn an incomplete broker fact or policy record into execution authority.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any


CASH_STATUSES = {"VERIFIED_POSITIVE", "VERIFIED_ZERO", "UNVERIFIED", "STALE", "STATE_MISMATCH"}
POLICY_AUTHORITY_STATUSES = {"VERIFIED", "THRESHOLD_VERIFIED_ACTION_UNVERIFIED", "UNVERIFIED"}


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def evaluate_cash_status(
    portfolio_state: dict[str, Any],
    *,
    reference_session: str | None,
    maximum_age_calendar_days: int,
    required_strategy_version: str | None = None,
) -> dict[str, Any]:
    """Return a strict cash status; only VERIFIED_POSITIVE is purchasing power."""
    reasons: list[str] = []
    cash = portfolio_state.get("available_cash_usd")
    broker = portfolio_state.get("last_confirmed_broker_snapshot") or {}
    state_version = portfolio_state.get("strategy_version")
    if required_strategy_version and state_version != required_strategy_version:
        reasons.append("PORTFOLIO_STRATEGY_VERSION_MISMATCH")
    if not _finite(cash) or float(cash) < 0:
        reasons.append("AVAILABLE_CASH_NOT_NON_NEGATIVE_NUMERIC")
    if broker.get("verified") is not True:
        reasons.append("BROKER_SNAPSHOT_NOT_VERIFIED")
    if broker.get("cash_verified") is not True:
        reasons.append("AVAILABLE_CASH_NOT_VERIFIED")
    if broker.get("holdings_complete") is not True:
        reasons.append("BROKER_HOLDINGS_INCOMPLETE")
    scope = broker.get("cash_verified_scope")
    # Older deterministic test fixtures may omit scope.  They remain accepted
    # only when their explicit source is TEST_ONLY; live state must identify the
    # value as available cash rather than total or projected proceeds.
    if scope not in {"available_cash_only", "settled_available_cash"} and broker.get("source") != "TEST_ONLY":
        reasons.append("CASH_AVAILABILITY_SCOPE_UNVERIFIED")

    reference = _date(reference_session)
    broker_as_of = _date(broker.get("as_of"))
    stale = False
    if reference is None or broker_as_of is None:
        reasons.append("BROKER_SNAPSHOT_DATE_UNAVAILABLE")
    else:
        age = (reference - broker_as_of).days
        if age > int(maximum_age_calendar_days) or age < -1:
            stale = True
            reasons.append("BROKER_SNAPSHOT_STALE")

    if "PORTFOLIO_STRATEGY_VERSION_MISMATCH" in reasons:
        status = "STATE_MISMATCH"
    elif stale:
        status = "STALE"
    elif reasons:
        status = "UNVERIFIED"
    elif float(cash) > 0:
        status = "VERIFIED_POSITIVE"
    else:
        status = "VERIFIED_ZERO"
    if status not in CASH_STATUSES:
        raise AssertionError(f"unexpected cash status: {status}")
    verified_cash = float(cash) if status in {"VERIFIED_POSITIVE", "VERIFIED_ZERO"} else None
    return {
        "cash_status": status,
        "verified_available_cash_usd": verified_cash,
        "execution_purchasing_power_usd": verified_cash if status == "VERIFIED_POSITIVE" else 0.0,
        "broker_snapshot_as_of": broker.get("as_of"),
        "reference_session": reference_session,
        "holdings_complete": broker.get("holdings_complete") is True,
        "cash_verified": broker.get("cash_verified") is True,
        "reasons": reasons,
    }

def hard_risk_rule_audit(alert_policy: dict[str, Any], symbol: str) -> dict[str, Any]:
    """Audit rule provenance without treating prose or a threshold as action authority."""
    risk_policy = alert_policy.get("holding_risk_rules") or {}
    rule = (risk_policy.get("positions") or {}).get(symbol) or {}
    rule_id = rule.get("rule_id")
    threshold_status = rule.get("approval_status") == "VERIFIED_USER_APPROVAL"
    provenance_complete = bool(
        isinstance(rule_id, str) and rule_id
        and rule.get("ticker") == symbol
        and _finite(rule.get("maximum_loss_fraction_from_average_cost"))
        and isinstance(rule.get("calculation_basis"), str) and rule.get("calculation_basis")
        and isinstance(rule.get("approved_by"), str) and rule.get("approved_by")
        and isinstance(rule.get("user_approval_reference"), str) and rule.get("user_approval_reference")
        and isinstance(rule.get("average_cost_source_requirement"), str) and rule.get("average_cost_source_requirement")
    )
    action = rule.get("action_on_breach")
    action_verified = action in {"exit_review", "reduction_review"} and rule.get("action_approval_status") == "VERIFIED_USER_APPROVAL"
    if threshold_status and provenance_complete and action_verified:
        authority = "VERIFIED"
    elif threshold_status and provenance_complete:
        authority = "THRESHOLD_VERIFIED_ACTION_UNVERIFIED"
    else:
        authority = "UNVERIFIED"
    if authority not in POLICY_AUTHORITY_STATUSES:
        raise AssertionError(f"unexpected policy authority: {authority}")
    return {
        "rule_id": rule_id,
        "rule_version": rule.get("rule_version") or risk_policy.get("rule_version"),
        "ticker": symbol,
        "maximum_loss_fraction": rule.get("maximum_loss_fraction_from_average_cost"),
        "calculation_basis": rule.get("calculation_basis") or risk_policy.get("threshold_formula"),
        "action_on_breach": action,
        "approval_status": rule.get("approval_status", "UNVERIFIED"),
        "approved_by": rule.get("approved_by"),
        "approved_at": rule.get("approved_at"),
        "user_approval_reference": rule.get("user_approval_reference"),
        "average_cost_source_requirement": rule.get("average_cost_source_requirement"),
        "action_approval_status": rule.get("action_approval_status", "UNVERIFIED"),
        "policy_authority_status": authority,
        "quantity_authority": "none",
    }
