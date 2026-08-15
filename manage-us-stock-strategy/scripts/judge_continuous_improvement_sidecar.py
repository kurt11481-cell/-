#!/usr/bin/env python3
"""Independent read-only judge for the continuous-improvement sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from continuous_improvement_sidecar import (
    ANALYTICS_ENGINE_VERSION, ANALYTICS_SCHEMA_VERSION, JUDGE_GATES,
    METRIC_DEFINITION_VERSION, OUTCOME_HORIZONS, _atomic_write, validate_ledger_chain,
    validate_outcome_ledger_chain, validate_output_path,
)
from validation_common import file_hash, load_json, validate_instance


def _authority_safe(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "order_authority" and item is not False:
                return False
            if key in {"execution_quantity", "quantity"} and item is not None:
                return False
            if key == "quantity_authority" and item != "none":
                return False
            if key in {"portfolio_mutation", "production_policy_mutation", "operational_counter_mutation", "auto_apply"} and item is not False:
                return False
            if not _authority_safe(item):
                return False
    elif isinstance(value, list):
        return all(_authority_safe(item) for item in value)
    return True


def judge(*, report: dict[str, Any], ledger: dict[str, Any], policy: dict[str, Any],
          report_schema: Path, ledger_schema: Path, portfolio_path: Path,
          expected_portfolio_hash: str, operational_progress_path: Path,
          expected_operational_progress_hash: str, scheduler_hash_before: str,
          scheduler_hash_after: str, tests_passed: bool, test_output_hash: str | None) -> dict[str, Any]:
    gates = {name: "FAIL" for name in JUDGE_GATES}
    schema_errors = validate_instance(report, report_schema) + validate_instance(ledger, ledger_schema)
    entries = ledger.get("entries") or []
    if not schema_errors and validate_ledger_chain(ledger):
        gates["UNIFIED_RUN_LEDGER"] = "PASS"
    expected_status = {
        "SCHEDULED_GENUINE": "VERIFIED_SCHEDULED", "MANUAL": "VERIFIED_MANUAL",
        "REPLAY": "VERIFIED_REPLAY", "TEST_ONLY": "VERIFIED_TEST",
        "SHADOW_COUNTERFACTUAL": "VERIFIED_SHADOW",
    }
    if entries and all(item["run_provenance_status"] == expected_status.get(item["execution_origin"], "UNVERIFIED") for item in entries):
        gates["RUN_PROVENANCE"] = "PASS"
    if all(not item["maturity_eligible"] for item in entries if item["run_provenance_status"] != "VERIFIED_SCHEDULED"):
        gates["MATURITY_ISOLATION"] = "PASS"
    if report.get("temporal_evidence", {}).get("violations") == 0 and all(item.get("evaluation_valid") for item in entries):
        gates["TEMPORAL_EVIDENCE_ISOLATION"] = "PASS"
    outcomes = report.get("forward_outcomes") or []
    if (outcomes and all(item.get("original_decision_immutable") is True for item in outcomes)
            and report.get("outcome_ledger_chain_valid") is True
            and validate_outcome_ledger_chain(report.get("outcome_ledger") or {})):
        gates["DECISION_IMMUTABILITY"] = "PASS"
    if outcomes and all({row["horizon_completed_sessions"] for row in item.get("results") or []} == set(OUTCOME_HORIZONS) for item in outcomes):
        gates["FORWARD_OUTCOME_ENGINE"] = "PASS"
    quality = report.get("decision_quality") or {}
    if quality.get("status") == "OBSERVATIONAL_ONLY" and quality.get("hard_gate_override") is False:
        gates["DECISION_QUALITY_ANALYTICS"] = "PASS"
    blocked = report.get("blocked_opportunity_review") or {}
    if blocked.get("status") == "BLOCKED_OPPORTUNITY_REVIEW" and all(item.get("later_price_alone_proves_error") is False for item in blocked.get("items") or []):
        gates["BLOCKED_OPPORTUNITY_REVIEW"] = "PASS"
    counterfactual = report.get("counterfactual_evaluation") or {}
    if (counterfactual.get("counterfactual_validity") == "MODELLED_ONLY"
            and counterfactual.get("expected_sale_proceeds_status") == "SHADOW_ONLY"
            and counterfactual.get("verified_orderable_cash_from_expected_proceeds_usd") == 0
            and counterfactual.get("broker_cash_before") == counterfactual.get("broker_cash_after")):
        gates["COUNTERFACTUAL_EVALUATION"] = "PASS"
    stability = report.get("decision_stability") or {}
    if stability.get("status") == "OBSERVATIONAL_ONLY" and stability.get("hysteresis_thresholds_active") is False:
        gates["DECISION_STABILITY"] = "PASS"
    drift = report.get("drift_monitoring") or {}
    if drift.get("status") == "DRIFT_MONITORING_READY" and drift.get("production_thresholds_configured") is False:
        gates["DRIFT_MONITORING"] = "PASS"
    operational = report.get("operational_analytics") or {}
    if operational.get("manual_replay_test_shadow_in_denominator") is False and operational.get("sla_thresholds_configured") is False:
        gates["OPERATIONAL_ANALYTICS"] = "PASS"
    if all(item.get("policy_change") is False for item in report.get("improvement_findings") or []):
        gates["IMPROVEMENT_FINDINGS"] = "PASS"
    proposals = report.get("policy_change_proposals") or []
    if proposals and all(item.get("auto_apply") is False and item.get("approval_status") == "EXPLICIT_USER_APPROVAL_REQUIRED" for item in proposals):
        gates["POLICY_PROPOSAL_GOVERNANCE"] = "PASS"
    experiments = report.get("shadow_policy_experiments") or []
    if experiments and all(item.get("production_policy_mutation") is False and item.get("portfolio_mutation") is False and item.get("operational_counter_mutation") is False for item in experiments):
        gates["SHADOW_POLICY_EXPERIMENT"] = "PASS"
    expected_modes = {
        "SCHEDULED_GENUINE": "LIVE_READ_ONLY", "MANUAL": "MANUAL_READ_ONLY",
        "REPLAY": "REPLAY", "TEST_ONLY": "TEST_ONLY",
        "SHADOW_COUNTERFACTUAL": "SHADOW_COUNTERFACTUAL",
    }
    if entries and all(item.get("decision_mode") == expected_modes.get(item.get("execution_origin"))
                       and item.get("decision_mode_status") == "DECISION_MODE_VALID"
                       for item in entries):
        gates["TEST_LIVE_SEMANTIC_FIREWALL"] = "PASS"
    if (report.get("core_operational_counter_mutation") is False
            and report.get("portfolio_decision_counter_mutation") is False
            and report.get("operational_counter_mutation") is False
            and counterfactual.get("verified_orderable_cash_from_expected_proceeds_usd") == 0
            and counterfactual.get("shadow_quantity_consumed_as_execution_quantity") is False
            and counterfactual.get("shadow_fill_consumed_as_actual_fill") is False):
        gates["COUNTER_AUTHORITY_FIREWALL"] = "PASS"
    if (scheduler_hash_before == scheduler_hash_after and len(scheduler_hash_before) == 64
            and report.get("analytics_failure_affects_core_scheduled_run") is False):
        gates["CORE_SCHEDULER_ISOLATION"] = "PASS"
    actual_portfolio_hash = file_hash(portfolio_path)
    actual_progress_hash = file_hash(operational_progress_path)
    if (actual_portfolio_hash == expected_portfolio_hash
            and actual_progress_hash == expected_operational_progress_hash
            and report.get("portfolio_mutation") is False
            and report.get("operational_counter_mutation") is False):
        gates["PORTFOLIO_IMMUTABILITY"] = "PASS"
    if (_authority_safe(report) and _authority_safe(ledger)
            and policy.get("order_authority") is False
            and policy.get("quantity_authority") == "none"
            and policy.get("execution_quantity") is None):
        gates["ORDER_AUTHORITY"] = "PASS"
    if tests_passed:
        gates["TESTS"] = "PASS"
    overall = "CONTINUOUS_IMPROVEMENT_PIPELINE_VERIFIED" if all(value == "PASS" for value in gates.values()) else "CONTINUOUS_IMPROVEMENT_PIPELINE_NOT_READY"
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "judge_mode": "INDEPENDENT_READ_ONLY",
        "overall_status": overall,
        "gates": gates,
        "schema_errors": schema_errors,
        "portfolio_hash_expected": expected_portfolio_hash,
        "portfolio_hash_actual": actual_portfolio_hash,
        "operational_progress_hash_expected": expected_operational_progress_hash,
        "operational_progress_hash_actual": actual_progress_hash,
        "scheduler_hash_before": scheduler_hash_before,
        "scheduler_hash_after": scheduler_hash_after,
        "test_output_hash": test_output_hash,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def _run_targeted_tests(test_root: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(test_root),
         "-p", "test_continuous_improvement_sidecar.py"],
        capture_output=True, text=True, check=False,
    )
    payload = (completed.stdout + completed.stderr).encode("utf-8")
    return completed.returncode == 0, hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report-schema", required=True, type=Path)
    parser.add_argument("--ledger-schema", required=True, type=Path)
    parser.add_argument("--judge-schema", required=True, type=Path)
    parser.add_argument("--portfolio", required=True, type=Path)
    parser.add_argument("--expected-portfolio-hash", required=True)
    parser.add_argument("--operational-progress", required=True, type=Path)
    parser.add_argument("--expected-operational-progress-hash", required=True)
    parser.add_argument("--scheduler-hash-before", required=True)
    parser.add_argument("--scheduler-hash-after", required=True)
    parser.add_argument("--test-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    validate_output_path(args.output, repository_root=root, protected=[args.report, args.ledger, args.policy, args.portfolio, args.operational_progress])
    tests_passed, test_hash = _run_targeted_tests(args.test_root)
    result = judge(
        report=load_json(args.report), ledger=load_json(args.ledger), policy=load_json(args.policy),
        report_schema=args.report_schema, ledger_schema=args.ledger_schema,
        portfolio_path=args.portfolio, expected_portfolio_hash=args.expected_portfolio_hash,
        operational_progress_path=args.operational_progress,
        expected_operational_progress_hash=args.expected_operational_progress_hash,
        scheduler_hash_before=args.scheduler_hash_before, scheduler_hash_after=args.scheduler_hash_after,
        tests_passed=tests_passed, test_output_hash=test_hash,
    )
    errors = validate_instance(result, args.judge_schema)
    if errors:
        raise SystemExit("judge schema validation failed: " + "; ".join(errors))
    _atomic_write(args.output, result)
    print(json.dumps({"overall_status": result["overall_status"], "output": str(args.output), "order_authority": False}, separators=(",", ":")))
    return 0 if result["overall_status"] == "CONTINUOUS_IMPROVEMENT_PIPELINE_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
