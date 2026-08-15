#!/usr/bin/env python3
"""Independent read-only judge for Capital Reallocation Shadow artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from portfolio_reallocation_shadow import (
    EVENT_ACTIONS, EVENT_STATES, OPTIMIZER_INPUTS, TEN_AXES, _atomic_write, validate_output_path,
)
from validation_common import file_hash, load_json, validate_instance


GATE_NAMES = (
    "EVENT_ACTIONABILITY_MATRIX",
    "POST_CLOSE_EVENT_ORDERING",
    "HOLDING_DECISION_ENGINE",
    "PROFIT_PROTECTION_ENGINE",
    "CAPITAL_REALLOCATION_SHADOW",
    "PORTFOLIO_OPTIMIZER_SHADOW",
    "TEN_STATE_MODEL",
    "BROKER_CASH_SEPARATION",
    "PORTFOLIO_IMMUTABILITY",
    "ORDER_AUTHORITY",
    "SCHEDULER_IMMUTABILITY",
    "TESTS",
)


def _recursive_authority_safe(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "order_authority" and item is not False:
                return False
            if key in {"execution_quantity", "quantity"} and item is not None:
                return False
            if key == "quantity_authority" and item != "none":
                return False
            if not _recursive_authority_safe(item):
                return False
    elif isinstance(value, list):
        return all(_recursive_authority_safe(item) for item in value)
    return True


def judge(*, report: dict[str, Any], policy: dict[str, Any], cohort: dict[str, Any],
          report_schema: Path, cohort_schema: Path, portfolio_path: Path,
          expected_portfolio_hash: str, scheduler_hash_before: str,
          scheduler_hash_after: str, tests_passed: bool, test_output_hash: str | None) -> dict[str, Any]:
    gates = {name: "FAIL" for name in GATE_NAMES}
    matrix = policy.get("event_actionability") or {}
    if set(matrix) == EVENT_STATES and all(set(matrix[state]) == EVENT_ACTIONS for state in EVENT_STATES):
        gates["EVENT_ACTIONABILITY_MATRIX"] = "PASS"
    if report.get("post_close_ordering_status") == "PASS" and not report.get("ordering_errors"):
        gates["POST_CLOSE_EVENT_ORDERING"] = "PASS"
    holdings = report.get("holding_decisions") or []
    if holdings and all(all(case in row for case in ("ADD_CASE", "HOLD_CASE", "TRIM_CASE", "EXIT_CASE")) for row in holdings):
        gates["HOLDING_DECISION_ENGINE"] = "PASS"
    profit = policy.get("profit_protection") or {}
    if profit.get("fixed_profit_auto_sell_prohibited") is True and profit.get("upstream_policy_result_required") is True:
        gates["PROFIT_PROTECTION_ENGINE"] = "PASS"
    if (report.get("mode") == "CAPITAL_REALLOCATION_SHADOW"
            and report.get("status") == "CAPITAL_REALLOCATION_SHADOW_VERIFIED"
            and report.get("portfolio_mutation") is False):
        gates["CAPITAL_REALLOCATION_SHADOW"] = "PASS"
    if (report.get("portfolio_risk_before") and report.get("portfolio_risk_after")
            and report.get("best_shadow_decision") in {"ADD_EXISTING_REVIEW", "NEW_BUY_REVIEW", "KEEP_CASH", "ROTATE_REVIEW"}
            and set(report.get("optimizer_input_status") or {}) == set(OPTIMIZER_INPUTS)
            and report.get("sell_risk_decision") in {"RISK_REVIEW_REQUIRED", "NOT_APPLICABLE"}
            and report.get("buy_risk_decision") in {"RISK_REVIEW_REQUIRED", "NOT_APPLICABLE"}):
        gates["PORTFOLIO_OPTIMIZER_SHADOW"] = "PASS"
    if holdings and all(set(row.get("state_axes") or {}) == set(TEN_AXES) for row in holdings):
        gates["TEN_STATE_MODEL"] = "PASS"
    if (report.get("expected_sale_proceeds_status") == "SHADOW_ONLY"
            and report.get("hypothetical_cash_status") == "SHADOW_ONLY"
            and report.get("funding_authority") == "VERIFIED_ACTUAL_CASH_ONLY"
            and report.get("expected_proceeds_may_fund_candidate") is False
            and report.get("verified_orderable_cash_from_expected_proceeds_usd") == 0):
        gates["BROKER_CASH_SEPARATION"] = "PASS"
    actual_portfolio_hash = file_hash(portfolio_path)
    if actual_portfolio_hash == expected_portfolio_hash:
        gates["PORTFOLIO_IMMUTABILITY"] = "PASS"
    if _recursive_authority_safe(report) and report.get("order_authority") is False:
        gates["ORDER_AUTHORITY"] = "PASS"
    if scheduler_hash_before == scheduler_hash_after and len(scheduler_hash_before) == 64:
        gates["SCHEDULER_IMMUTABILITY"] = "PASS"
    if tests_passed:
        gates["TESTS"] = "PASS"

    schema_errors = validate_instance(report, report_schema)
    schema_errors.extend(validate_instance(cohort, cohort_schema))
    if schema_errors:
        gates["CAPITAL_REALLOCATION_SHADOW"] = "FAIL"
    overall = "CAPITAL_REALLOCATION_SHADOW_VERIFIED" if all(value == "PASS" for value in gates.values()) else "CAPITAL_REALLOCATION_SHADOW_NOT_READY"
    return {
        "schema_version": "1.0",
        "judge_mode": "INDEPENDENT_READ_ONLY",
        "overall_status": overall,
        "gates": gates,
        "schema_errors": schema_errors,
        "portfolio_hash_expected": expected_portfolio_hash,
        "portfolio_hash_actual": actual_portfolio_hash,
        "scheduler_hash_before": scheduler_hash_before,
        "scheduler_hash_after": scheduler_hash_after,
        "test_output_hash": test_output_hash,
        "validation_mode": report.get("validation_mode"),
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def _run_targeted_tests(test_root: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(test_root),
         "-p", "test_portfolio_reallocation_shadow.py"],
        capture_output=True, text=True, check=False,
    )
    payload = (completed.stdout + completed.stderr).encode("utf-8")
    return completed.returncode == 0, hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--report-schema", required=True, type=Path)
    parser.add_argument("--cohort-schema", required=True, type=Path)
    parser.add_argument("--judge-schema", required=True, type=Path)
    parser.add_argument("--portfolio", required=True, type=Path)
    parser.add_argument("--expected-portfolio-hash", required=True)
    parser.add_argument("--scheduler-hash-before", required=True)
    parser.add_argument("--scheduler-hash-after", required=True)
    parser.add_argument("--test-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        validate_output_path(
            args.output, repository_root=root,
            protected=[args.report, args.policy, args.cohort, args.portfolio,
                       args.report_schema, args.cohort_schema, args.judge_schema],
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    tests_passed, test_hash = _run_targeted_tests(args.test_root)
    result = judge(
        report=load_json(args.report), policy=load_json(args.policy), cohort=load_json(args.cohort),
        report_schema=args.report_schema, cohort_schema=args.cohort_schema,
        portfolio_path=args.portfolio, expected_portfolio_hash=args.expected_portfolio_hash,
        scheduler_hash_before=args.scheduler_hash_before, scheduler_hash_after=args.scheduler_hash_after,
        tests_passed=tests_passed, test_output_hash=test_hash,
    )
    judge_errors = validate_instance(result, args.judge_schema)
    if judge_errors:
        raise SystemExit("judge schema validation failed: " + "; ".join(judge_errors))
    _atomic_write(args.output, result)
    print(json.dumps({"output": str(args.output), "overall_status": result["overall_status"],
                      "order_authority": False}, separators=(",", ":")))
    return 0 if result["overall_status"] == "CAPITAL_REALLOCATION_SHADOW_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
