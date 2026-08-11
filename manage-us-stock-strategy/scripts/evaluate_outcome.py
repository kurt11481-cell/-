#!/usr/bin/env python3
"""Evaluate a locked v2 decision outcome without mutating the decision record."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OutcomeError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OutcomeError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OutcomeError(f"top-level JSON must be an object: {path}")
    return value


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_datetime(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is missing")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} is invalid")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone offset")
        return None
    return parsed.astimezone(timezone.utc)


def finite_fraction(value: Any, field: str, errors: list[str], default: float | None = None) -> float | None:
    if value is None and default is not None:
        return default
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        errors.append(f"{field} must be a finite number")
        return None
    return float(value)


def string_set(value: Any, field: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{field} must be a list of non-empty strings")
        return set()
    if len(value) != len(set(value)):
        errors.append(f"{field} must not contain duplicates")
    return set(value)


def evaluate(decision: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    decision_hash = canonical_sha256(decision)
    if decision.get("schema_version") != "2.0" or decision.get("record_locked") is not True:
        errors.append("decision must be a locked v2 record")
    if decision.get("order_authority") is not False:
        errors.append("decision record unexpectedly has order authority")
    if outcome.get("decision_id") != decision.get("decision_id"):
        errors.append("outcome decision_id does not match the locked decision")
    if outcome.get("original_decision_sha256") != decision_hash:
        errors.append("outcome is not anchored to the exact locked decision hash")
    observed_at = parse_datetime(outcome.get("observed_at_utc"), "observed_at_utc", errors)
    created_at = parse_datetime(decision.get("created_at_utc"), "decision.created_at_utc", errors)
    if observed_at and created_at and observed_at < created_at:
        errors.append("outcome observation predates the decision")

    plan = decision.get("evaluation_plan")
    conditions = plan.get("conditions") if isinstance(plan, dict) else None
    if not isinstance(conditions, list) or not conditions:
        errors.append("decision has no evaluation conditions")
        conditions = []
    condition_map: dict[str, str] = {}
    for item in conditions:
        if not isinstance(item, dict):
            errors.append("decision contains an invalid evaluation condition")
            continue
        condition_id = item.get("id")
        kind = item.get("kind")
        if not isinstance(condition_id, str) or kind not in {"CONFIRMATION", "INVALIDATION"}:
            errors.append("decision contains an invalid evaluation condition")
            continue
        condition_map[condition_id] = kind

    confirmations = string_set(
        outcome.get("triggered_confirmation_condition_ids", []),
        "triggered_confirmation_condition_ids",
        errors,
    )
    invalidations = string_set(
        outcome.get("triggered_invalidation_condition_ids", []),
        "triggered_invalidation_condition_ids",
        errors,
    )
    outcome_evidence_ids = string_set(outcome.get("evidence_ids"), "evidence_ids", errors)
    if not outcome_evidence_ids:
        errors.append("at least one outcome evidence id is required")
    unknown = sorted((confirmations | invalidations) - set(condition_map))
    if unknown:
        errors.append("outcome references unknown condition ids: " + ", ".join(unknown))
    wrong_confirmations = sorted(item for item in confirmations if condition_map.get(item) != "CONFIRMATION")
    wrong_invalidations = sorted(item for item in invalidations if condition_map.get(item) != "INVALIDATION")
    if wrong_confirmations:
        errors.append("condition ids are not confirmations: " + ", ".join(wrong_confirmations))
    if wrong_invalidations:
        errors.append("condition ids are not invalidations: " + ", ".join(wrong_invalidations))

    security_return = finite_fraction(outcome.get("security_return_fraction"), "security_return_fraction", errors)
    benchmark_return = finite_fraction(outcome.get("benchmark_return_fraction"), "benchmark_return_fraction", errors)
    costs = finite_fraction(outcome.get("transaction_cost_fraction"), "transaction_cost_fraction", errors, 0.0)
    slippage = finite_fraction(outcome.get("slippage_fraction"), "slippage_fraction", errors, 0.0)
    if costs is not None and costs < 0:
        errors.append("transaction_cost_fraction cannot be negative")
    if slippage is not None and slippage < 0:
        errors.append("slippage_fraction cannot be negative")

    if confirmations and invalidations:
        classification = "REVISED"
    elif invalidations:
        classification = "FAILED"
    elif confirmations:
        classification = "CONFIRMED"
    else:
        classification = "PENDING"
    if decision.get("final_action") == "WAIT":
        warnings.append("WAIT is evaluated as a thesis/no-trade decision, not as a missed fill")
    if errors:
        classification = "REJECTED"

    net_return = None
    excess_return = None
    if None not in (security_return, costs, slippage):
        net_return = security_return - costs - slippage
        if benchmark_return is not None:
            excess_return = net_return - benchmark_return

    return {
        "schema_version": "1.0",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_id": decision.get("decision_id"),
        "symbol": decision.get("symbol"),
        "original_decision_sha256": decision_hash,
        "classification": classification,
        "triggered_confirmation_condition_ids": sorted(confirmations),
        "triggered_invalidation_condition_ids": sorted(invalidations),
        "outcome_evidence_ids": sorted(outcome_evidence_ids),
        "security_return_fraction": security_return,
        "benchmark_return_fraction": benchmark_return,
        "transaction_cost_fraction": costs,
        "slippage_fraction": slippage,
        "net_security_return_fraction": net_return,
        "excess_return_fraction": excess_return,
        "calibration_eligible": classification in {"CONFIRMED", "FAILED", "REVISED"} and not errors,
        "errors": errors,
        "warnings": warnings,
        "decision_record_unchanged": canonical_sha256(decision) == decision_hash,
        "order_authority": False,
        "order_status": "no order was placed or scheduled",
    }


def self_test() -> int:
    decision = {
        "schema_version": "2.0",
        "decision_id": "D-TEST",
        "created_at_utc": "2026-08-11T12:00:00+00:00",
        "symbol": "TEST",
        "record_locked": True,
        "order_authority": False,
        "final_action": "WAIT",
        "evaluation_plan": {
            "conditions": [
                {"id": "C1", "kind": "CONFIRMATION", "description": "confirmation"},
                {"id": "I1", "kind": "INVALIDATION", "description": "invalidation"},
            ]
        },
    }
    outcome = {
        "decision_id": "D-TEST",
        "original_decision_sha256": canonical_sha256(decision),
        "observed_at_utc": "2026-08-12T12:00:00+00:00",
        "triggered_confirmation_condition_ids": ["C1"],
        "triggered_invalidation_condition_ids": [],
        "security_return_fraction": 0.02,
        "benchmark_return_fraction": 0.01,
        "transaction_cost_fraction": 0.001,
        "slippage_fraction": 0.001,
        "evidence_ids": ["OUTCOME-E1"],
    }
    result = evaluate(decision, outcome)
    if result["classification"] != "CONFIRMED" or result["errors"]:
        print(json.dumps(result, indent=2))
        return 2
    outcome["original_decision_sha256"] = "0" * 64
    if evaluate(decision, outcome)["classification"] != "REJECTED":
        return 2
    print("evaluate_outcome self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--outcome", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.decision or not args.outcome:
        parser.error("--decision and --outcome are required")
    try:
        result = evaluate(read_json(args.decision), read_json(args.outcome))
    except OutcomeError as exc:
        print(f"OUTCOME_EVALUATION_ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["classification"] != "REJECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
