#!/usr/bin/env python3
"""Deterministically request only broker evidence that can resolve an active state issue."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any


NON_REMEDIABLE = {
    "GLOBAL_INDEPENDENT_CLOSE_OUTAGE", "OFFICIAL_SESSION_UNVERIFIED", "MARKET_SNAPSHOT_FAILURE",
    "PRICE_CONFLICT", "EVENT_DATA_INCOMPLETE", "POLICY_REGISTRY_MISMATCH",
    "PORTFOLIO_STRATEGY_VERSION_MISMATCH", "DEPLOYMENT_HASH_MISMATCH",
}


def _decision_changing(holding_strategies: list[dict[str, Any]], radar: dict[str, Any]) -> bool:
    if any(item.get("strategy_state") == "ADD_REVIEW" for item in holding_strategies):
        return True
    return any(item.get("opportunity_state") == "READY" for item in radar.get("candidate_dispositions", []))


def evaluate_broker_snapshot_request(*, portfolio_state: dict[str, Any], cash_gate_result: dict[str, Any],
                                     holding_strategies: list[dict[str, Any]], holding_risk_result: dict[str, Any],
                                     tactical_radar_result: dict[str, Any], latest_completed_session: str | None,
                                     broker_snapshot_policy: dict[str, Any],
                                     unreconciled_user_change_state: list[Any] | None = None,
                                     runtime: dict[str, Any] | None = None, run_phase: str = "POST_MARKET") -> tuple[dict[str, Any], dict[str, Any]]:
    broker = portfolio_state.get("last_confirmed_broker_snapshot") or {}
    reasons: list[str] = []
    if broker.get("verified") is not True:
        reasons.append("BROKER_SNAPSHOT_NOT_VERIFIED")
    if broker.get("holdings_complete") is not True:
        reasons.append("BROKER_HOLDINGS_INCOMPLETE")
    if not broker.get("as_of") and not broker.get("confirmed_at"):
        reasons.append("BROKER_SNAPSHOT_DATE_UNAVAILABLE")
    if cash_gate_result.get("cash_status") == "STALE":
        reasons.append("BROKER_SNAPSHOT_STALE")
    if unreconciled_user_change_state:
        reasons.append("USER_REPORTED_PORTFOLIO_CHANGE_UNRECONCILED")
    average_costs = portfolio_state.get("average_cost_usd") or {}
    for item in holding_strategies:
        if item.get("policy_rule_id") and not isinstance(average_costs.get(item["ticker"]), (int, float)):
            reasons.append("AVERAGE_COST_MISSING_FOR_ACTIVE_RISK_RULE")
            break
    decision_changing = _decision_changing(holding_strategies, tactical_radar_result)
    cash_missing = cash_gate_result.get("cash_status") not in {"VERIFIED_POSITIVE", "VERIFIED_ZERO"}
    if decision_changing and cash_missing:
        reasons.append("AVAILABLE_CASH_NOT_VERIFIED")
    reasons = list(dict.fromkeys(reasons))
    full_reasons = {"BROKER_SNAPSHOT_NOT_VERIFIED", "BROKER_HOLDINGS_INCOMPLETE", "BROKER_SNAPSHOT_DATE_UNAVAILABLE",
                    "BROKER_SNAPSHOT_STALE", "USER_REPORTED_PORTFOLIO_CHANGE_UNRECONCILED", "BROKER_STATE_MISMATCH"}
    required_scope = "FULL_PORTFOLIO" if any(item in full_reasons for item in reasons) else ("CASH_ONLY" if reasons else None)
    status = "REQUIRED" if reasons else "NOT_REQUIRED"
    reason_objects = [{"reason_code": item, "snapshot_remediable": item not in NON_REMEDIABLE} for item in reasons]
    policy_version = broker_snapshot_policy.get("policy_version", "UNVERSIONED")
    event_key = None
    delivery_id = None
    runtime = dict(runtime or {"schema_version": "2.5", "policy_version": policy_version,
                               "requests": {}, "deliveries": {}, "order_authority": False})
    runtime.setdefault("requests", {})
    runtime.setdefault("deliveries", {})
    notify = False
    if status == "REQUIRED":
        account_scope_hash = hashlib.sha256(str(broker.get("account_id_masked", "UNKNOWN")).encode()).hexdigest()[:16]
        event_key = f"{policy_version}:PORTFOLIO_SNAPSHOT_REQUEST:{account_scope_hash}:{','.join(sorted(reasons))}:{required_scope}"
        delivery_id = hashlib.sha256(f"{event_key}:{latest_completed_session}:{run_phase}:BLOCKING".encode()).hexdigest()
        previous = runtime["requests"].get(event_key)
        previous_scope = previous.get("required_scope") if isinstance(previous, dict) else None
        notify = delivery_id not in runtime["deliveries"] and (previous is None or previous_scope == "CASH_ONLY" and required_scope == "FULL_PORTFOLIO")
        runtime["requests"][event_key] = {"status": status, "required_scope": required_scope,
                                           "reason_codes": sorted(reasons), "session": latest_completed_session}
        if notify:
            runtime["deliveries"][delivery_id] = {"event_key": event_key, "session": latest_completed_session,
                                                    "run_phase": run_phase}
    else:
        for prior in runtime["requests"].values():
            if isinstance(prior, dict) and prior.get("status") not in {"DECLINED", "EXPIRED"}:
                prior["status"] = "VERIFIED"
    required_fields = [] if not reasons else (["holdings", "average_cost", "as_of", "available_cash", "account_scope"] if required_scope == "FULL_PORTFOLIO" else ["available_cash", "as_of"])
    execution_effect = "NONE" if not reasons else ("PORTFOLIO_BLOCKED" if required_scope == "FULL_PORTFOLIO" else "CASH_BLOCKED")
    result = {"schema_version": "2.5", "snapshot_request_status": status,
              "severity": "BLOCKING" if reasons else "NONE", "reason_codes": reason_objects,
              "required_scope": required_scope, "required_fields": required_fields,
              "execution_effect": execution_effect, "event_key": event_key, "delivery_id": delivery_id,
              "notify": notify, "order_authority": False}
    runtime["policy_version"] = policy_version
    runtime["order_authority"] = False
    return result, runtime
