#!/usr/bin/env python3
"""Deterministic provider health and fallback eligibility logic."""

from __future__ import annotations

from typing import Any


FAILURES = {"HTTP_429", "TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH", "AUTHENTICATION_FAILURE"}


def update_provider_health(state: dict[str, Any] | None, outcome: str, now: str, retry_after: str | None = None, open_after: int = 3) -> dict[str, Any]:
    current = dict(state or {})
    failures = int(current.get("consecutive_failures", 0))
    if outcome == "SUCCESS":
        return {"last_success": now, "last_failure": current.get("last_failure"), "consecutive_failures": 0, "failure_type": None, "circuit_state": "HEALTHY", "retry_after": None}
    if outcome not in FAILURES:
        raise ValueError(f"unsupported provider outcome: {outcome}")
    failures += 1
    circuit = "OPEN" if failures >= open_after or outcome in {"HTTP_429", "AUTHENTICATION_FAILURE"} else "DEGRADED"
    return {"last_success": current.get("last_success"), "last_failure": now, "consecutive_failures": failures, "failure_type": outcome, "circuit_state": circuit, "retry_after": retry_after}


def fallback_eligible(capability: dict[str, Any] | None, *, evidence_type: str | None = None, historical: bool, session_compatible: bool, timestamp_compatible: bool, provenance_retained: bool) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not capability or capability.get("enabled") is not True:
        reasons.append("fallback provider is not enabled")
    approved_types = set((capability or {}).get("capability_scope", [])) | set((capability or {}).get("authoritative_for", []))
    if not evidence_type:
        reasons.append("fallback evidence type is not declared")
    elif evidence_type not in approved_types:
        reasons.append("fallback is not approved for the requested evidence type")
    if historical and (not capability or capability.get("historical_point_in_time_supported") is not True):
        reasons.append("fallback is not point-in-time eligible")
    if not session_compatible:
        reasons.append("session mismatch")
    if not timestamp_compatible:
        reasons.append("timestamp mismatch")
    if not provenance_retained:
        reasons.append("provenance is missing")
    return not reasons, reasons
