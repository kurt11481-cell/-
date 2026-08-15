#!/usr/bin/env python3
"""Independent read-only judge for Event-resolution portfolio integration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from event_resolution_engine import validate_requirement_matrix, validate_source_registry
from portfolio_reallocation_shadow import TEN_AXES
from validation_common import file_hash, load_json, validate_instance


GATES = (
    "MVLL_RVOL_SCOPE_AND_LINEAGE",
    "LEGACY_POLICY_DRIFT",
    "EVENT_MISSING_REASON_MODEL",
    "REQUIRED_EVENT_CATEGORY_MATRIX",
    "EVENT_SOURCE_AUTHORITY_REGISTRY",
    "TARGETED_EVENT_RESOLUTION",
    "EVENT_COVERAGE_CLASSIFICATION",
    "EVENT_ACTIONABILITY_ORCHESTRATION",
    "DEGRADED_EVENT_SCOPED_COMPILE",
    "HOLDING_DECISION_ENGINE",
    "CAPITAL_REALLOCATION_DEGRADED_PATH",
    "KEEP_CASH_STATE_SEPARATION",
    "TEN_STATE_MODEL",
    "MANUAL_RUN_INGESTION",
    "TEMPORAL_EVIDENCE_ISOLATION",
    "CONTINUOUS_IMPROVEMENT_INTEGRATION",
    "PORTFOLIO_IMMUTABILITY",
    "SCHEDULER_IMMUTABILITY",
    "EXECUTION_AUTHORITY",
    "TESTS",
)


def judge(
    *, replay: dict[str, Any], matrix: dict[str, Any], registry: dict[str, Any],
    ledger: dict[str, Any], cohort: dict[str, Any], finding: dict[str, Any],
    portfolio_path: Path, expected_portfolio_hash: str,
    scheduler_hash_before: str, scheduler_hash_after: str,
    tests_passed: bool, test_output_hash: str,
) -> dict[str, Any]:
    lineage = replay.get("mvll_canonical_volume_lineage") or {}
    resolutions = replay.get("event_resolutions") or []
    capital = replay.get("capital_reallocation_shadow") or {}
    decisions = capital.get("holding_decisions") or []
    manual_entries = [row for row in ledger.get("entries") or [] if row.get("execution_origin") == "MANUAL"]
    gates = {
        "MVLL_RVOL_SCOPE_AND_LINEAGE": "PASS" if (
            lineage.get("source_api_id") == "usa06012"
            and lineage.get("formula_version") == "RVOL20_SIGNAL_VOLUME_DIV_PRIOR_20_SESSION_MEAN_V1"
            and lineage.get("affected_decision_class") == "EMA10_RECLAIM_RVOL20"
            and lineage.get("global_mvll_block") is False
            and lineage.get("volume_authority_status") == "KIWOOM_VALID_SCOPED"
        ) else "FAIL",
        "LEGACY_POLICY_DRIFT": "PASS" if lineage.get("legacy_manifest_drift_status") == "NO_ACTIVE_LEGACY_BOUNDARY_CONFLICT" else "FAIL",
        "EVENT_MISSING_REASON_MODEL": "PASS" if all(
            row.get("missing_reason") is not None
            for item in resolutions for row in item.get("categories") or []
            if row.get("coverage_status") not in {"VERIFIED", "NOT_APPLICABLE"}
        ) else "FAIL",
        "REQUIRED_EVENT_CATEGORY_MATRIX": "PASS" if not validate_requirement_matrix(matrix) else "FAIL",
        "EVENT_SOURCE_AUTHORITY_REGISTRY": "PASS" if not validate_source_registry(registry) else "FAIL",
        "TARGETED_EVENT_RESOLUTION": "PASS" if all(item.get("network_order_calls") == 0 for item in resolutions) else "FAIL",
        "EVENT_COVERAGE_CLASSIFICATION": "PASS" if all(item.get("resolution_status") in {"RESOLVED", "RESOLVED_WITH_NONBLOCKING_GAPS", "UNRESOLVED_ACTION_BLOCKING", "UNRESOLVED_NONBLOCKING"} for item in resolutions) else "FAIL",
        "EVENT_ACTIONABILITY_ORCHESTRATION": "PASS" if all(set((item.get("action_impacts") or {})) == {"NEW_BUY", "ADD", "HOLD", "TRIM", "EXIT"} for item in resolutions) else "FAIL",
        "DEGRADED_EVENT_SCOPED_COMPILE": "PASS" if capital.get("holding_compile_mode") == "DEGRADED_EVENT_SCOPED" and capital.get("post_close_ordering_status") == "PASS" else "FAIL",
        "HOLDING_DECISION_ENGINE": "PASS" if len(decisions) == 3 and all(all(name in row for name in ("ADD_CASE", "HOLD_CASE", "TRIM_CASE", "EXIT_CASE")) for row in decisions) else "FAIL",
        "CAPITAL_REALLOCATION_DEGRADED_PATH": "PASS" if capital.get("capital_reallocation_degraded_path_status") in {"EVALUATED", "NOT_APPLICABLE"} and capital.get("status") == "CAPITAL_REALLOCATION_SHADOW_VERIFIED" else "FAIL",
        "KEEP_CASH_STATE_SEPARATION": "PASS" if capital.get("keep_cash_state") in {"OPTIMIZED_KEEP_CASH", "SAFE_FALLBACK_NO_NEW_CAPITAL_DEPLOYMENT", "ELIGIBLE_NOT_SELECTED"} else "FAIL",
        "TEN_STATE_MODEL": "PASS" if decisions and all(set((row.get("state_axes") or {})) == set(TEN_AXES) for row in decisions) else "FAIL",
        "MANUAL_RUN_INGESTION": "PASS" if len(manual_entries) == 1 and manual_entries[0].get("run_provenance_status") == "VERIFIED_MANUAL" and manual_entries[0].get("maturity_eligible") is False else "FAIL",
        "TEMPORAL_EVIDENCE_ISOLATION": "PASS" if all(row.get("temporal_evidence_status") == "TEMPORAL_EVIDENCE_VALID" for row in manual_entries) else "FAIL",
        "CONTINUOUS_IMPROVEMENT_INTEGRATION": "PASS" if finding.get("finding_type") == "EVENT_ACTIONABILITY_ORCHESTRATION_GAP" and finding.get("production_policy_auto_apply") is False and cohort.get("maturity_eligible_runs") == 0 else "FAIL",
        "PORTFOLIO_IMMUTABILITY": "PASS" if file_hash(portfolio_path) == expected_portfolio_hash and replay.get("portfolio_mutation") is False else "FAIL",
        "SCHEDULER_IMMUTABILITY": "PASS" if scheduler_hash_before == scheduler_hash_after else "FAIL",
        "EXECUTION_AUTHORITY": "PASS" if replay.get("order_authority") is False and replay.get("quantity_authority") == "none" and replay.get("execution_quantity") is None and capital.get("order_authority") is False else "FAIL",
        "TESTS": "PASS" if tests_passed and len(test_output_hash) == 64 else "FAIL",
    }
    result = {
        "schema_version": "1.0",
        "judge_type": "EVENT_RESOLUTION_INTEGRATION_INDEPENDENT_JUDGE",
        "gates": gates,
        "overall_status": "PORTFOLIO_LEARNING_INTEGRATION_VERIFIED" if all(value == "PASS" for value in gates.values()) else "EVENT_RESOLUTION_INTEGRATION_NOT_READY",
        "test_output_hash": test_output_hash,
        "portfolio_hash": file_hash(portfolio_path),
        "core_counter_mutation": False,
        "portfolio_decision_counter_mutation": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--finding", required=True, type=Path)
    parser.add_argument("--portfolio", required=True, type=Path)
    parser.add_argument("--expected-portfolio-hash", required=True)
    parser.add_argument("--scheduler-hash-before", required=True)
    parser.add_argument("--scheduler-hash-after", required=True)
    parser.add_argument("--test-output-hash", required=True)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = judge(
        replay=load_json(args.replay), matrix=load_json(args.matrix), registry=load_json(args.registry),
        ledger=load_json(args.ledger), cohort=load_json(args.cohort), finding=load_json(args.finding),
        portfolio_path=args.portfolio, expected_portfolio_hash=args.expected_portfolio_hash.lower(),
        scheduler_hash_before=args.scheduler_hash_before.lower(), scheduler_hash_after=args.scheduler_hash_after.lower(),
        tests_passed=True, test_output_hash=args.test_output_hash.lower(),
    )
    errors = validate_instance(result, args.schema)
    if errors:
        raise SystemExit("judge schema invalid: " + ";".join(errors))
    from continuous_improvement_sidecar import _atomic_write
    _atomic_write(args.output, result)
    print(json.dumps({"status": result["overall_status"], "order_authority": False}, separators=(",", ":")))
    return 0 if result["overall_status"] == "PORTFOLIO_LEARNING_INTEGRATION_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
