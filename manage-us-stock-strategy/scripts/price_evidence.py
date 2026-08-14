#!/usr/bin/env python3
"""Deterministic v2.5 completed-close evidence classification and comparison."""

from __future__ import annotations

import hashlib
from datetime import datetime
from math import isfinite
from typing import Any, Iterable
from urllib.parse import urlparse


YAHOO_ORIGINS = {"finance.yahoo.com", "query1.finance.yahoo.com", "query2.finance.yahoo.com"}
DECISION_CHANGING_REASONS = {
    "READY", "MATERIAL_NEAR_TRIGGER", "ADD_REVIEW", "REDUCTION_REVIEW",
    "EXIT_REVIEW", "HARD_RISK_BOUNDARY", "DECISION_BOUNDARY_PROXIMITY",
    "CANARY_AUDIT",
}


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value)) and float(value) > 0


def primary_validation(row: Any, completed_session: str | None) -> dict[str, Any]:
    """Validate the primary completed-session record without conferring official status."""
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append("PRIMARY_RECORD_UNAVAILABLE")
        row = {}
    if not completed_session or row.get("bar_date") != completed_session:
        errors.append("PRIMARY_SESSION_MISMATCH")
    for field in ("open", "high", "low", "close", "volume"):
        if field not in row or not isinstance(row.get(field), (int, float)) or not isfinite(float(row[field])):
            errors.append(f"PRIMARY_{field.upper()}_INVALID")
    if _positive(row.get("close")):
        high, low, opened, closed = row.get("high"), row.get("low"), row.get("open"), row.get("close")
        if all(isinstance(value, (int, float)) for value in (high, low, opened, closed)):
            if float(high) < max(float(opened), float(closed)) or float(low) > min(float(opened), float(closed)) or float(high) < float(low):
                errors.append("PRIMARY_OHLC_INTEGRITY")
    else:
        errors.append("PRIMARY_CLOSE_NOT_POSITIVE")
    if row.get("corporate_action_unresolved") is not False:
        errors.append("PRIMARY_CORPORATE_ACTION_UNRESOLVED")
    status = "VALIDATED" if not errors else ("UNAVAILABLE" if "PRIMARY_RECORD_UNAVAILABLE" in errors else "INVALID")
    provider = str(row.get("provider") or row.get("source_provider") or "yfinance")
    provider_role = str(row.get("provider_role") or "")
    kiwoom_primary = provider.upper() in {"KIWOOM", "KIWOOM_REST"} or provider_role in {
        "KIWOOM_OPERATIONAL_PRIMARY",
        "KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED",
        "OPERATIONAL_EXECUTION_PRIMARY",
    }
    return {
        "primary_status": status,
        "primary_session": completed_session,
        "primary_price_basis": row.get("raw_close_price_basis", "raw_completed_regular_session_close"),
        "primary_provider": provider,
        "primary_provider_role": provider_role or ("KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED" if kiwoom_primary else "DIAGNOSTIC_SHADOW"),
        "kiwoom_canonical_primary": kiwoom_primary,
        "errors": errors,
    }


def technical_validation(row: Any) -> dict[str, Any]:
    indicator = row.get("indicator_validation") if isinstance(row, dict) else None
    valid = isinstance(indicator, dict) and indicator.get("status") == "passed" and indicator.get("errors") == []
    return {"technical_validation_status": "VALIDATED" if valid else "INVALID",
            "errors": [] if valid else ["TECHNICAL_VALIDATION_FAILED"]}


def crosscheck_required(*, opportunity_state: str | None = None, strategy_state: str | None = None,
                        hard_risk_boundary: bool = False, material_near_trigger: bool = False,
                        decision_boundary_proximity: bool = False, canary_audit: bool = False) -> str | None:
    if hard_risk_boundary:
        return "HARD_RISK_BOUNDARY"
    if strategy_state in {"ADD_REVIEW", "REDUCTION_REVIEW", "EXIT_REVIEW"}:
        return strategy_state
    if opportunity_state == "READY":
        return "READY"
    if opportunity_state == "NEAR_TRIGGER" and material_near_trigger:
        return "MATERIAL_NEAR_TRIGGER"
    if decision_boundary_proximity:
        return "DECISION_BOUNDARY_PROXIMITY"
    if canary_audit:
        return "CANARY_AUDIT"
    return None


def evidence_status(row: Any, completed_session: str | None, reason: str | None = None) -> dict[str, Any]:
    primary = primary_validation(row, completed_session)
    technical = technical_validation(row)
    cross = row.get("quote_crosscheck") if isinstance(row, dict) else {}
    cross = cross if isinstance(cross, dict) else {}
    required = reason in DECISION_CHANGING_REASONS
    status_map = {
        "verified": "VERIFIED", "pending": "PENDING", "unavailable": "UNAVAILABLE",
        "inconclusive": "INCONCLUSIVE", "conflict": "CONFLICT", "not_required": "NOT_REQUIRED",
    }
    cross_status = status_map.get(str(cross.get("status", "")).lower(), "PENDING" if required else "NOT_REQUIRED")
    if cross_status == "VERIFIED" and (
        cross.get("independent_of_builder") is not True
        or cross.get("bar_date") != completed_session
    ):
        cross_status = "INCONCLUSIVE"
    if not required:
        cross_status = "NOT_REQUIRED"
    effective = "DATA_BLOCKED"
    divergence_blocking = False
    if primary["primary_status"] == "VALIDATED":
        if primary["kiwoom_canonical_primary"]:
            effective = "KIWOOM_CANONICAL_COMPLETED_CLOSE"
        else:
            effective = "INDEPENDENT_VERIFIED" if cross_status == "VERIFIED" else "PRIMARY_VALIDATED"
    if cross_status == "CONFLICT" and not primary["kiwoom_canonical_primary"]:
        effective = "PRICE_CONFLICT"
        divergence_blocking = True
    if primary["primary_status"] != "VALIDATED":
        effective = "DATA_BLOCKED"
    return {
        **primary,
        **technical,
        "crosscheck_requirement": "REQUIRED" if required else "NOT_REQUIRED",
        "crosscheck_reason": reason,
        "crosscheck_status": cross_status,
        "crosscheck_method": cross.get("acquisition_method", "NONE" if not required else "CODEX_WEB"),
        "evidence_validation_status": cross.get("evidence_validation_status", "NOT_REQUIRED" if not required else ("VALIDATED" if cross_status == "VERIFIED" else "PENDING")),
        "comparison_status": cross.get("comparison_status", "MATCH" if cross_status == "VERIFIED" else "NOT_EVALUATED"),
        "cross_provider_diagnostic_status": (
            "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE"
            if primary["kiwoom_canonical_primary"] and cross_status == "CONFLICT"
            else ("DIAGNOSTIC_MATCH" if primary["kiwoom_canonical_primary"] and cross_status == "VERIFIED" else "NOT_EVALUATED")
        ),
        "divergence_blocking": divergence_blocking,
        "provider_price_averaged": False,
        "effective_price_status": effective,
    }


def validate_web_evidence(record: dict[str, Any], *, primary_provider: str = "yfinance") -> list[str]:
    errors: list[str] = []
    required = ("ticker", "reported_session", "reported_close", "currency", "price_basis", "provider",
                "source_url", "source_domain", "source_type", "retrieved_at", "acquisition_method", "content_hash",
                "security_identity_explicit", "regular_session_close_explicit", "is_search_result_snippet")
    for field in required:
        if record.get(field) in {None, ""}:
            errors.append(f"MISSING_{field.upper()}")
    if record.get("acquisition_method") != "CODEX_WEB":
        errors.append("ACQUISITION_METHOD_NOT_CODEX_WEB")
    if record.get("is_search_result_snippet") is True:
        errors.append("SEARCH_RESULT_SNIPPET_REJECTED")
    domain = str(record.get("source_domain") or "").lower().removeprefix("www.")
    parsed_domain = urlparse(str(record.get("source_url") or "")).netloc.lower().removeprefix("www.")
    if urlparse(str(record.get("source_url") or "")).scheme != "https":
        errors.append("SOURCE_URL_NOT_HTTPS")
    if domain and parsed_domain and domain != parsed_domain:
        errors.append("SOURCE_DOMAIN_URL_MISMATCH")
    if domain in YAHOO_ORIGINS or parsed_domain in YAHOO_ORIGINS or record.get("source_origin") == "YAHOO":
        errors.append("YAHOO_ORIGIN_NOT_INDEPENDENT")
    if record.get("security_identity_explicit") is not True:
        errors.append("SECURITY_IDENTITY_NOT_EXPLICIT")
    if record.get("regular_session_close_explicit") is not True:
        errors.append("REGULAR_SESSION_CLOSE_NOT_EXPLICIT")
    if not _positive(record.get("reported_close")):
        errors.append("REPORTED_CLOSE_INVALID")
    if record.get("provider") == primary_provider:
        errors.append("SOURCE_NOT_INDEPENDENT")
    digest = str(record.get("content_hash") or "")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest.lower()):
        errors.append("CONTENT_HASH_INVALID")
    try:
        datetime.fromisoformat(str(record.get("retrieved_at")).replace("Z", "+00:00"))
    except ValueError:
        errors.append("RETRIEVED_AT_INVALID")
    return list(dict.fromkeys(errors))


def compare_close(primary: dict[str, Any], independent: dict[str, Any],
                  decision_boundaries: Iterable[dict[str, Any]] = (),
                  tolerance_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    errors = validate_web_evidence(independent, primary_provider=str(primary.get("primary_provider", "yfinance")))
    if errors:
        return _comparison("REJECTED", "INCONCLUSIVE", "NOT_EVALUATED", errors)
    if independent.get("ticker") != primary.get("ticker"):
        return _comparison("REJECTED", "CONFLICT", "IDENTITY_MISMATCH", ["IDENTITY_MISMATCH"])
    if independent.get("reported_session") != primary.get("primary_session"):
        return _comparison("REJECTED", "CONFLICT", "SESSION_MISMATCH", ["SESSION_MISMATCH"])
    if independent.get("currency") != primary.get("currency", "USD"):
        return _comparison("REJECTED", "CONFLICT", "CURRENCY_MISMATCH", ["CURRENCY_MISMATCH"])
    if independent.get("price_basis") != primary.get("primary_price_basis"):
        return _comparison("VALIDATED", "INCONCLUSIVE", "PRICE_BASIS_MISMATCH", [])
    p = float(primary["primary_close"])
    q = float(independent["reported_close"])
    absolute = abs(p - q)
    relative = absolute / p
    tolerance_policy = tolerance_policy or {"absolute_usd_floor": 0.05, "relative_fraction": 0.001}
    tolerance = max(float(tolerance_policy["absolute_usd_floor"]),
                    float(tolerance_policy["relative_fraction"]) * p)
    boundary_flip = any(_boundary_result(p, item) != _boundary_result(q, item) for item in decision_boundaries)
    if boundary_flip:
        return _comparison("VALIDATED", "CONFLICT", "DECISION_BOUNDARY_FLIP", [], absolute, relative, True, tolerance)
    if absolute <= tolerance:
        return _comparison("VALIDATED", "VERIFIED", "MATCH", [], absolute, relative, False, tolerance)
    return _comparison("VALIDATED", "CONFLICT", "CONFLICT", [], absolute, relative, False, tolerance)


def _boundary_result(price: float, boundary: dict[str, Any]) -> bool:
    level = float(boundary["value"])
    operator = boundary.get("operator", "less_than_or_equal")
    return price <= level if operator == "less_than_or_equal" else price >= level


def _comparison(evidence: str, crosscheck: str, comparison: str, errors: list[str],
                absolute: float | None = None, relative: float | None = None,
                flip: bool = False, tolerance: float | None = None) -> dict[str, Any]:
    return {"evidence_validation_status": evidence, "crosscheck_status": crosscheck,
            "comparison_status": comparison, "decision_boundary_flip": flip,
            "absolute_difference": absolute, "relative_difference": relative,
            "tolerance_usd": tolerance,
            "errors": errors}


def request_id(ticker: str, completed_session: str, reason: str) -> str:
    return hashlib.sha256(f"v2.6:{ticker}:{completed_session}:{reason}".encode("utf-8")).hexdigest()
