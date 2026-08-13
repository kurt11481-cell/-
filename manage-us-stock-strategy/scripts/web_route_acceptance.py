#!/usr/bin/env python3
"""Deterministically evaluate five-session Codex Web route acceptance."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, load_json, validate_instance, write_json


FAILURE_TYPES = {
    "HTTP_429", "TIMEOUT", "PAGE_UNAVAILABLE", "LOGIN_REQUIRED", "ANTI_BOT_CHALLENGE",
    "DOM_OR_FIELD_CHANGED", "DATE_MISSING", "PRICE_BASIS_UNKNOWN", "IDENTITY_MISMATCH",
    "SCHEMA_MISMATCH",
}


def evaluate_route_session(route: dict[str, Any], *, completed_session: str,
                           evidence_validation_status: str, comparison_status: str,
                           observed_at: str, failure_type: str | None = None,
                           required_sessions: int = 5, suspend_after: int = 3) -> dict[str, Any]:
    updated = deepcopy(route)
    if updated.get("route_status") == "GUARDED_APPROVED":
        raise ValueError("guarded route approval cannot be mutated by Shadow acceptance")
    accepted = list(updated.get("accepted_sessions") or [])
    locked_status = updated.get("route_status") in {"SUSPENDED", "BROKEN"}
    success = evidence_validation_status == "VALIDATED" and comparison_status == "MATCH"
    if success:
        if completed_session not in accepted:
            accepted.append(completed_session)
        updated["accepted_sessions"] = sorted(accepted)
        updated["last_success"] = observed_at
        updated["consecutive_failures"] = 0
        if not locked_status:
            updated["route_status"] = "SHADOW_APPROVED" if len(accepted) >= required_sessions else "SOURCE_ROUTE_PENDING_REVIEW"
    else:
        failure = failure_type or "SCHEMA_MISMATCH"
        if failure not in FAILURE_TYPES:
            failure = "SCHEMA_MISMATCH"
        updated["last_failure"] = observed_at
        updated["consecutive_failures"] = int(updated.get("consecutive_failures", 0)) + 1
        if updated["consecutive_failures"] >= suspend_after:
            updated["route_status"] = "SUSPENDED"
    updated["order_authority"] = False
    return updated


def update_registry(registry: dict[str, Any], route_id: str, **observation: Any) -> dict[str, Any]:
    value = deepcopy(registry)
    matches = [route for route in value.get("routes", []) if route.get("route_id") == route_id]
    if len(matches) != 1:
        raise ValueError("route_id must resolve to exactly one registered route")
    index = value["routes"].index(matches[0])
    value["routes"][index] = evaluate_route_session(
        matches[0], required_sessions=int(value.get("route_acceptance_sessions_required", 5)),
        suspend_after=int(value.get("suspend_after_consecutive_failures", 3)), **observation,
    )
    value["order_authority"] = False
    return value


def route_fingerprint(route: dict[str, Any]) -> str:
    return canonical_hash({key: route.get(key) for key in (
        "route_id", "ticker_scope", "exchange_scope", "instrument_class_scope", "source_type",
        "source_domain", "source_url_template", "price_basis", "source_field_label", "currency",
        "authentication_requirement",
    )})


def validate_registry_semantics(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    route_ids: set[str] = set()
    for route in registry.get("routes", []):
        route_id = str(route.get("route_id") or "")
        if route_id in route_ids:
            errors.append(f"DUPLICATE_ROUTE_ID:{route_id}")
        route_ids.add(route_id)
        if route.get("route_fingerprint") != route_fingerprint(route):
            errors.append(f"ROUTE_FINGERPRINT_MISMATCH:{route_id}")
        if route.get("order_authority") is not False:
            errors.append(f"ROUTE_ORDER_AUTHORITY_PROHIBITED:{route_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--route-id", required=True)
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--evidence-status", required=True)
    parser.add_argument("--comparison-status", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--failure-type")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    value = update_registry(load_json(args.registry), args.route_id,
        completed_session=args.completed_session, evidence_validation_status=args.evidence_status,
        comparison_status=args.comparison_status, observed_at=args.observed_at,
        failure_type=args.failure_type)
    errors = validate_instance(value, root / "manage-us-stock-strategy/schemas/web-completed-close-route-registry.schema.json")
    errors.extend(validate_registry_semantics(value))
    if errors:
        raise SystemExit("route registry invalid: " + "; ".join(errors))
    write_json(args.output, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
