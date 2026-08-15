#!/usr/bin/env python3
"""Deterministic, ticker/category-local Event resolution for read-only strategy use.

The engine never treats missing evidence as proof that no event exists.  It
classifies each required category, optionally calls a supplied read-only
resolver for that exact ticker/category, and emits action-specific readiness.
It contains no network or broker write implementation.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Callable

from validation_common import canonical_hash, parse_datetime


MISSING_REASONS = {
    "NOT_YET_PUBLISHED",
    "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF",
    "SOURCE_UNAVAILABLE",
    "SOURCE_STALE",
    "CATEGORY_NOT_CHECKED",
    "PARSER_FAILED",
    "IDENTITY_UNCERTAIN",
    "CONFLICTING_EVIDENCE",
    "CUTOFF_GAP",
    "UNRESOLVED",
}
REQUIREMENT_STATES = {"REQUIRED", "OPTIONAL", "NOT_APPLICABLE"}
SOURCE_AUTHORITY_TIERS = {
    "PRIMARY_AUTHORITY",
    "SECONDARY_AUTHORITATIVE",
    "DIAGNOSTIC_SECONDARY",
}
CATEGORY_COVERAGE_STATES = {
    "VERIFIED",
    "NOT_YET_ANNOUNCED",
    "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF",
    "SOURCE_UNAVAILABLE",
    "SOURCE_STALE",
    "REVIEW_REQUIRED",
    "NOT_APPLICABLE",
    "INVALID",
}
RESOLUTION_STATES = {
    "RESOLVED",
    "RESOLVED_WITH_NONBLOCKING_GAPS",
    "UNRESOLVED_ACTION_BLOCKING",
    "UNRESOLVED_NONBLOCKING",
    "INVALID",
}
COMPILE_MODES = {"FULL", "DEGRADED_EVENT_SCOPED", "FAIL_CLOSED", "NOT_RUN"}

PRIMARY_SOURCE_TYPES = {
    "ISSUER_IR", "ISSUER_OFFICIAL_PRESS_RELEASE", "SEC_FILING",
    "EXCHANGE_NOTICE", "ETF_SPONSOR_NOTICE", "REGULATOR_NOTICE",
    "GOVERNMENT_SOURCE",
}


def _at_or_before(value: str | None, cutoff: str) -> bool:
    if not value:
        return False
    try:
        return parse_datetime(value) <= parse_datetime(cutoff)
    except (TypeError, ValueError):
        return False


def validate_source_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = registry.get("source_types") or {}
    if not sources:
        errors.append("EVENT_SOURCE_REGISTRY_EMPTY")
    for source_type, value in sources.items():
        tier = (value or {}).get("authority_tier")
        if tier not in SOURCE_AUTHORITY_TIERS:
            errors.append(f"INVALID_SOURCE_AUTHORITY_TIER:{source_type}")
        if source_type in PRIMARY_SOURCE_TYPES and tier != "PRIMARY_AUTHORITY":
            errors.append(f"PRIMARY_SOURCE_MISCLASSIFIED:{source_type}")
    if registry.get("single_confidence_score_is_sole_gate") is not False:
        errors.append("SINGLE_CONFIDENCE_GATE_NOT_PROHIBITED")
    if registry.get("order_authority") is not False:
        errors.append("ORDER_AUTHORITY_VIOLATION")
    return errors


def validate_requirement_matrix(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scopes = matrix.get("ticker_requirements") or {}
    for ticker in ("SOXL", "MVLL", "NBIS"):
        if ticker not in scopes:
            errors.append(f"REQUIRED_TICKER_MATRIX_MISSING:{ticker}")
    for ticker, scope in scopes.items():
        categories = (scope or {}).get("categories") or {}
        if not categories:
            errors.append(f"EVENT_CATEGORY_MATRIX_EMPTY:{ticker}")
        for category, value in categories.items():
            requirement = (value or {}).get("requirement")
            if requirement not in REQUIREMENT_STATES:
                errors.append(f"INVALID_EVENT_REQUIREMENT:{ticker}:{category}")
            actions = (value or {}).get("blocking_actions") or []
            if any(action not in {"NEW_BUY", "ADD", "HOLD", "TRIM", "EXIT"} for action in actions):
                errors.append(f"INVALID_EVENT_BLOCKING_ACTION:{ticker}:{category}")
        if ticker == "MVLL" and (scope or {}).get("supplemental_underlying") != "MRVL":
            errors.append("MVLL_MRVL_SUPPLEMENTAL_SEPARATION_MISSING")
    if matrix.get("product_events_may_be_replaced_by_underlying_events") is not False:
        errors.append("PRODUCT_UNDERLYING_EVENT_SEPARATION_VIOLATION")
    if matrix.get("order_authority") is not False:
        errors.append("ORDER_AUTHORITY_VIOLATION")
    return errors


def _normalize_category(
    ticker: str,
    category: str,
    requirement: dict[str, Any],
    evidence: dict[str, Any] | None,
    registry: dict[str, Any],
    decision_as_of: str,
) -> dict[str, Any]:
    evidence = copy.deepcopy(evidence or {})
    requirement_status = requirement["requirement"]
    coverage = evidence.get("coverage_status")
    missing_reason = evidence.get("missing_reason")
    source_type = evidence.get("source_type")
    source_policy = (registry.get("source_types") or {}).get(source_type) or {}
    tier = evidence.get("source_authority_tier") or source_policy.get("authority_tier")
    errors: list[str] = []
    if requirement_status == "NOT_APPLICABLE":
        coverage, missing_reason = "NOT_APPLICABLE", None
    elif coverage not in CATEGORY_COVERAGE_STATES:
        coverage = "REVIEW_REQUIRED"
        missing_reason = missing_reason if missing_reason in MISSING_REASONS else "CATEGORY_NOT_CHECKED"
    if missing_reason is not None and missing_reason not in MISSING_REASONS:
        errors.append("INVALID_MISSING_REASON")
    if missing_reason in {"SOURCE_UNAVAILABLE", "PARSER_FAILED", "SOURCE_STALE"} and coverage == "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF":
        errors.append("MISSING_REASON_CANNOT_PROVE_NO_NEW_DISCLOSURE")
    if missing_reason == "NOT_YET_PUBLISHED" and coverage not in {"NOT_YET_ANNOUNCED", "REVIEW_REQUIRED"}:
        errors.append("NOT_YET_PUBLISHED_MISCLASSIFIED")
    if coverage == "VERIFIED":
        if tier not in SOURCE_AUTHORITY_TIERS:
            errors.append("SOURCE_AUTHORITY_UNKNOWN")
        if not _at_or_before(evidence.get("observed_at"), decision_as_of):
            errors.append("TEMPORAL_CUTOFF_INVALID")
        if evidence.get("identity_status") != "VERIFIED":
            errors.append("EVENT_IDENTITY_NOT_VERIFIED")
    secondary_detected = bool(evidence.get("material_event_detected")) and tier != "PRIMARY_AUTHORITY"
    primary_confirmation = evidence.get("primary_confirmation_status") == "VERIFIED"
    if secondary_detected and not primary_confirmation:
        coverage = "REVIEW_REQUIRED"
        missing_reason = "UNRESOLVED"
        errors.append("PRIMARY_CONFIRMATION_REQUIRED")
    return {
        "ticker": ticker,
        "event_category": category,
        "requirement_status": requirement_status,
        "blocking_actions": list(requirement.get("blocking_actions") or []),
        "source": evidence.get("source"),
        "source_type": source_type,
        "source_authority_tier": tier,
        "observed_at": evidence.get("observed_at"),
        "effective_at": evidence.get("effective_at"),
        "decision_as_of": decision_as_of,
        "coverage_status": "INVALID" if errors and "PRIMARY_CONFIRMATION_REQUIRED" not in errors else coverage,
        "freshness_status": evidence.get("freshness_status", "UNKNOWN"),
        "conflict_status": evidence.get("conflict_status", "NO_CONFLICT_OBSERVED"),
        "identity_status": evidence.get("identity_status", "UNKNOWN"),
        "temporal_cutoff_status": "VALID" if _at_or_before(evidence.get("observed_at"), decision_as_of) else "UNKNOWN_OR_INVALID",
        "missing_reason": missing_reason,
        "resolution_attempts": [],
        "event_effect": evidence.get("event_effect", "UNKNOWN"),
        "action_impact": copy.deepcopy(evidence.get("action_impact") or {}),
        "source_hash": evidence.get("source_hash"),
        "errors": errors,
        "order_authority": False,
    }


def _needs_resolution(row: dict[str, Any]) -> bool:
    return row["requirement_status"] == "REQUIRED" and row["coverage_status"] not in {
        "VERIFIED", "NOT_YET_ANNOUNCED", "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF",
    }


def resolve_event_bundle(
    *,
    ticker: str,
    instrument_identity: dict[str, Any],
    decision_as_of: str,
    evidence_by_category: dict[str, dict[str, Any]],
    requirement_matrix: dict[str, Any],
    source_registry: dict[str, Any],
    refresh_callback: Callable[[str, str, str], dict[str, Any] | None] | None = None,
    maximum_attempts: int = 1,
) -> dict[str, Any]:
    """Resolve only missing categories; callback must itself be read-only."""
    if validate_requirement_matrix(requirement_matrix) or validate_source_registry(source_registry):
        raise ValueError("EVENT_POLICY_VALIDATION_FAILED")
    if maximum_attempts < 0:
        raise ValueError("NEGATIVE_EVENT_RESOLUTION_ATTEMPTS")
    scope = (requirement_matrix.get("ticker_requirements") or {}).get(ticker)
    if not scope:
        raise ValueError(f"EVENT_REQUIREMENT_SCOPE_MISSING:{ticker}")
    rows: list[dict[str, Any]] = []
    for category, requirement in (scope.get("categories") or {}).items():
        row = _normalize_category(
            ticker, category, requirement, evidence_by_category.get(category),
            source_registry, decision_as_of,
        )
        if _needs_resolution(row) and refresh_callback is not None:
            for attempt in range(1, maximum_attempts + 1):
                refreshed = refresh_callback(ticker, category, decision_as_of)
                row["resolution_attempts"].append({
                    "attempt": attempt,
                    "target_ticker": ticker,
                    "target_category": category,
                    "status": "EVIDENCE_RETURNED" if refreshed else "NO_ELIGIBLE_EVIDENCE",
                })
                if refreshed:
                    candidate = _normalize_category(
                        ticker, category, requirement, refreshed, source_registry, decision_as_of,
                    )
                    candidate["resolution_attempts"] = row["resolution_attempts"]
                    row = candidate
                    if not _needs_resolution(row):
                        break
        rows.append(row)

    invalid = any(row["coverage_status"] == "INVALID" for row in rows)
    unresolved_required = [row for row in rows if _needs_resolution(row)]
    blocking = [row for row in unresolved_required if row["blocking_actions"]]
    optional_gaps = [row for row in rows if row["requirement_status"] == "OPTIONAL" and row["coverage_status"] not in {"VERIFIED", "NOT_APPLICABLE"}]
    if invalid:
        resolution_status = "INVALID"
    elif blocking:
        resolution_status = "UNRESOLVED_ACTION_BLOCKING"
    elif unresolved_required:
        resolution_status = "UNRESOLVED_NONBLOCKING"
    elif optional_gaps:
        resolution_status = "RESOLVED_WITH_NONBLOCKING_GAPS"
    else:
        resolution_status = "RESOLVED"
    compile_mode = "FAIL_CLOSED" if invalid else ("FULL" if resolution_status == "RESOLVED" else "DEGRADED_EVENT_SCOPED")

    action_impacts: dict[str, dict[str, Any]] = {}
    for action in ("NEW_BUY", "ADD", "HOLD", "TRIM", "EXIT"):
        affected = [row["event_category"] for row in blocking if action in row["blocking_actions"]]
        if action in {"NEW_BUY", "ADD"} and affected:
            decision = "BLOCKED"
        elif action == "HOLD" and affected:
            decision = "REVIEW_REQUIRED"
        elif action in {"TRIM", "EXIT"} and affected:
            decision = "EVENT_DEPENDENT_BRANCH_BLOCKED_INDEPENDENT_BRANCHES_EVALUABLE"
        else:
            decision = "EVALUABLE"
        action_impacts[action] = {"decision": decision, "affected_categories": affected}

    result = {
        "schema_version": "1.0",
        "engine_version": "EVENT_RESOLUTION_V1",
        "ticker": ticker,
        "instrument_identity": copy.deepcopy(instrument_identity),
        "decision_as_of": decision_as_of,
        "resolution_status": resolution_status,
        "holding_compile_mode": compile_mode,
        "categories": rows,
        "action_impacts": action_impacts,
        "resolution_attempt_count": sum(len(row["resolution_attempts"]) for row in rows),
        "network_order_calls": 0,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    result["bundle_hash"] = canonical_hash(result)
    return result


def resolution_to_event_readiness(result: dict[str, Any]) -> str:
    status = result.get("resolution_status")
    if status == "RESOLVED":
        return "EVENT_COMPLETE"
    if status in {"RESOLVED_WITH_NONBLOCKING_GAPS", "UNRESOLVED_NONBLOCKING"}:
        return "EVENT_PARTIAL_NONBLOCKING"
    if status == "UNRESOLVED_ACTION_BLOCKING":
        return "EVENT_PARTIAL_BUY_BLOCKING"
    return "EVENT_REFRESH_FAILED"
