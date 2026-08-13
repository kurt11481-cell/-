#!/usr/bin/env python3
"""Evaluate exact-scope 1/5/10/20/60 promotion without mutating authority."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from validation_common import canonical_hash


CHECKPOINTS = (1, 5, 10, 20, 60)
STATES = {
    1: "LIVE_READ_ONLY_DELIVERY_VERIFIED",
    5: "LIMITED_HUMAN_REVIEW_PENDING_APPROVAL",
    10: "GUARDED_HUMAN_REVIEW_PENDING_APPROVAL",
    20: "MATURE_GUARDED_REVIEW_PENDING_APPROVAL",
    60: "LONG_HORIZON_EVALUATION_REQUIRED",
}


def _scope_valid(scope: dict[str, Any] | None) -> bool:
    if not scope:
        return False
    return bool(
        scope.get("ticker") and scope.get("decision_class") and scope.get("source_route_id")
        and isinstance(scope.get("research_packet_hash"), str)
        and len(scope["research_packet_hash"]) == 64
    )


def build_staged_audit(progress: dict[str, Any], checkpoint: int, generated_at: str,
                       context: dict[str, Any], scope: dict[str, Any] | None = None) -> dict[str, Any]:
    if checkpoint not in CHECKPOINTS:
        raise ValueError("unsupported checkpoint")
    valid_sessions = int(progress.get("valid_shadow_sessions", 0))
    no_critical = not progress.get("critical_violations")
    requirements: dict[str, bool] = {
        "VALID_SESSION_COUNT": valid_sessions >= checkpoint,
        "ZERO_CRITICAL_VIOLATIONS": no_critical,
        "PORTFOLIO_IMMUTABILITY": context.get("portfolio_mutations", 0) == 0,
        "ORDER_AUTHORITY_FALSE": context.get("order_authority_violations", 0) == 0,
        "UNAUTHORIZED_QUANTITY_ZERO": context.get("unauthorized_quantities", 0) == 0,
        "FILL_INFERENCE_ZERO": context.get("fill_inference", 0) == 0,
    }
    if checkpoint == 1:
        requirements.update({
            "GENUINE_SCHEDULED_DELIVERY": context.get("genuine_scheduled_deliveries", 0) >= 1,
            "VALID_ORIGIN_MAIN_PROVENANCE": context.get("origin_main_provenance_valid") is True,
            "VALID_DELIVERY_ID": context.get("delivery_id_valid") is True,
        })
    if checkpoint >= 5:
        requirements.update({
            "EXACT_SCOPE_PRESENT": _scope_valid(scope),
            "HISTORICAL_REPLAY_PASS": context.get("historical_replay_status") == "PASS",
            "FAULT_INJECTION_PASS": context.get("fault_injection_status") == "PASS",
            "EXACT_ROUTE_SHADOW_APPROVED": context.get("route_status") in {"SHADOW_APPROVED", "GUARDED_APPROVED"},
            "EVIDENCE_VALIDATION_PASS": context.get("evidence_validation_pass_count", 0) >= 1,
            "DETERMINISTIC_MATCH_PRESENT": context.get("deterministic_match_count", 0) >= 1,
            "BROKER_WORKFLOW_PASS": context.get("broker_workflow_status") == "PASS",
            "RESEARCH_OR_BASELINE_VALID": context.get("research_or_baseline_valid") is True,
            "TICKER_OVERLAY_COVERAGE": context.get("ticker_overlay_sessions", 0) >= 5,
        })
    if checkpoint >= 10:
        requirements.update({
            "STAGE_5_PASS": context.get("stage_5_status") == "PASS",
            "NO_UNRESOLVED_DELIVERY_FAILURE": context.get("unresolved_delivery_failures", 0) == 0,
            "NO_UNEXPLAINED_SESSION_GAPS": context.get("unexplained_expected_session_gaps", 0) == 0,
            "TWO_NONEMPTY_WEB_QUEUE_SESSIONS": context.get("nonempty_web_queue_sessions", 0) >= 2,
            "UNAVAILABLE_OR_INCONCLUSIVE_HANDLED": context.get("unavailable_or_inconclusive_handled") is True,
            "TICKER_LOCAL_CONFLICT_ISOLATION": context.get("ticker_local_conflict_isolation") is True,
            "ACCEPTED_ROUTE_HEALTHY": context.get("accepted_route_healthy") is True,
            "INCOMPLETE_BASELINE_NO_HOLD": context.get("incomplete_baseline_no_hold") is True,
            "LEVERAGED_DIRECT_PROXY_SEPARATION": context.get("leveraged_direct_proxy_separation") is True,
        })
    if checkpoint >= 20:
        requirements["STAGE_10_PASS"] = context.get("stage_10_status") == "PASS"
        requirements["MATURITY_AUDIT_PASS"] = context.get("maturity_audit_status") == "PASS"
    if checkpoint >= 60:
        requirements["LONG_HORIZON_EVALUATION_READY"] = context.get("long_horizon_evaluation_status") == "PASS"
    eligible = all(requirements.values())
    value = {
        "schema_version": "2.6.3", "cohort_id": str(progress.get("cohort_id") or ""),
        "checkpoint": checkpoint, "generated_at": generated_at, "valid_sessions": valid_sessions,
        "promotion_model": "COVERAGE_WEIGHTED_STAGED",
        "promotion_scope_model": "TICKER_DECISION_CLASS_SOURCE_ROUTE",
        "promotion_scope": deepcopy(scope) if scope else None, "requirements": requirements,
        "promotion_state": STATES[checkpoint] if eligible else "NOT_ELIGIBLE",
        "promotion_eligible": eligible, "automatic_promotion": False,
        "explicit_user_approval_required": True, "order_authority": False,
    }
    value["audit_hash"] = canonical_hash(value)
    return value


def validate_exact_scope_approval(audit: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if audit.get("promotion_eligible") is not True:
        errors.append("PROMOTION_NOT_ELIGIBLE")
    if approval.get("audit_hash") != audit.get("audit_hash"):
        errors.append("AUDIT_HASH_MISMATCH")
    if approval.get("promotion_scope") != audit.get("promotion_scope"):
        errors.append("EXACT_SCOPE_MISMATCH")
    if not approval.get("user_approval_reference"):
        errors.append("EXPLICIT_USER_APPROVAL_REFERENCE_MISSING")
    return {
        "validation_status": "PASS" if not errors else "FAIL", "errors": errors,
        "automatic_promotion": False, "quantity": None, "order_authority": False,
    }
