#!/usr/bin/env python3
"""Independent read-only Judge for Strategy Evolution Hardening v2."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from strategy_evolution import validate_evolution_ledger
from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


GATES = (
    "OUTCOME_STATE_SEMANTICS", "UNIVERSE_SEPARATION", "EVIDENCE_GRADES",
    "LIVE_EVENT_RESOLUTION_STATUS", "BENCHMARK_CONTRACTS", "PAIRED_ATTRIBUTION",
    "RUNTIME_CONTRACT_SUITE", "SENTINEL_ISOLATION", "NO_CHANGE_EVOLUTION_LEDGER",
    "POLICY_STABILITY", "CAPITAL_EFFICIENCY", "EVIDENCE_UNCERTAINTY",
    "GENUINE_ACTIONABLE_SEPARATION", "REAL_CHALLENGER_CREATION_RULE",
    "PAIRED_EVIDENCE_IDENTITY", "EVOLUTION_AUTHORITY", "EXECUTION_AUTHORITY",
    "PORTFOLIO_IMMUTABILITY", "COUNTER_ISOLATION", "TESTS",
)


def judge(*, repo: Path, artifact_dir: Path, validation_summary: dict[str, Any],
          runtime_contract: dict[str, Any], portfolio_hash_before: str) -> dict[str, Any]:
    report = load_json(artifact_dir / "strategy_evolution_report.json")
    holding = load_json(artifact_dir / "holding_universe_snapshot.json")
    opportunity = load_json(artifact_dir / "candidate_universe_snapshot.json")
    sentinel = load_json(artifact_dir / "sentinel_challenger.json")
    ledger = load_json(artifact_dir / "strategy_evolution_ledger.json")
    outcome_states = {row.get("status") for row in report.get("forward_outcomes", {}).values()}
    benchmark_ids = {row.get("benchmark_id") for row in report.get("benchmark_portfolios", [])}
    attribution = report.get("paired_value_attribution", {})
    stability = report.get("policy_stability_status", {})
    efficiency = report.get("capital_efficiency", {})
    checks = {
        "OUTCOME_STATE_SEMANTICS": outcome_states == {"NO_BASE_DECISION"},
        "UNIVERSE_SEPARATION": holding.get("universe_role") == "PORTFOLIO_HOLDING_UNIVERSE" and opportunity.get("universe_role") == "CANDIDATE_OPPORTUNITY_UNIVERSE" and opportunity.get("availability_status") == "UNAVAILABLE_AT_DECISION_TIME" and not opportunity.get("instrument_identities"),
        "EVIDENCE_GRADES": report.get("evidence_grade_policy", {}).get("grade_a_required_for_production_promotion") is True and report.get("evidence_grade_policy", {}).get("lower_grades_can_replace_grade_a") is False,
        "LIVE_EVENT_RESOLUTION_STATUS": report.get("live_event_resolution_status") == "NO_GENUINE_RUN_YET",
        "BENCHMARK_CONTRACTS": benchmark_ids == {"BENCHMARK_CHAMPION", "BENCHMARK_HOLD_ALL", "BENCHMARK_TRIM_NO_REDEPLOY"},
        "PAIRED_ATTRIBUTION": set(attribution) == {"TRIM_VALUE", "REDEPLOYMENT_VALUE", "REALLOCATION_VALUE", "CANDIDATE_SELECTION_VALUE"} and all(row.get("status") == "NOT_APPLICABLE" for row in attribution.values()),
        "RUNTIME_CONTRACT_SUITE": runtime_contract.get("status") == "PASS" and runtime_contract.get("protected_source_only_fixtures_required") is False,
        "SENTINEL_ISOLATION": sentinel.get("namespace") == "SENTINEL_TEST_NAMESPACE" and sentinel.get("production_challenger") is False and sentinel.get("promotion_eligible") is False and report.get("strategy_evolution_counters", {}).get("production_challengers") == 0,
        "NO_CHANGE_EVOLUTION_LEDGER": validate_evolution_ledger(ledger) and any(row.get("entry_type") == "NO_CHANGE_DECISION" for row in ledger.get("entries", [])),
        "POLICY_STABILITY": stability.get("semantic_policy_change_count") == 0 and stability.get("no_change_decision_count") == 1,
        "CAPITAL_EFFICIENCY": efficiency.get("EXECUTION_COST_EFFICIENCY", {}).get("status") == "NOT_MODELLED" and efficiency.get("NET_TRADING_EFFICIENCY", {}).get("status") == "NOT_VERIFIED",
        "EVIDENCE_UNCERTAINTY": report.get("uncertainty", {}).get("evidence_uncertainty_status") == "INSUFFICIENT_EVIDENCE",
        "GENUINE_ACTIONABLE_SEPARATION": "genuine_decision_observations" in report.get("portfolio_decision_counters", {}) or not report.get("portfolio_decision_counters"),
        "REAL_CHALLENGER_CREATION_RULE": report.get("real_challenger_creation_rule", {}).get("eligible_trigger_present") is False and report.get("real_challenger_creation_rule", {}).get("production_challenger_count") == 0,
        "PAIRED_EVIDENCE_IDENTITY": report.get("paired_evidence_identity", {}).get("holding_universe_hash") == holding.get("holding_universe_hash") and report.get("paired_evidence_identity", {}).get("candidate_opportunity_universe_hash") == opportunity.get("candidate_universe_hash"),
        "EVOLUTION_AUTHORITY": report.get("evolution_authority") == "EVOLUTION_4" and report.get("evolution_5_enabled") is False and report.get("auto_apply") is False,
        "EXECUTION_AUTHORITY": report.get("execution_authority_status") == "NONE" and report.get("order_authority") is False and report.get("quantity_authority") == "none" and report.get("execution_quantity") is None,
        "PORTFOLIO_IMMUTABILITY": file_hash(repo / "stock-strategy-system/portfolio_state.json") == portfolio_hash_before and report.get("portfolio_mutation") is False,
        "COUNTER_ISOLATION": report.get("core_counters", {}).get("valid_finalized_sessions", 0) == 0 and report.get("core_counters", {}).get("valid_paired_operational_days", 0) == 0 and report.get("strategy_evolution_counters", {}).get("sentinel_challengers") == 0,
        "TESTS": validation_summary.get("targeted_failures") == 0 and validation_summary.get("full_suite_failures") == 0 and validation_summary.get("schemas") == "PASS" and validation_summary.get("compile") == "PASS" and validation_summary.get("git_diff_check") == "PASS" and validation_summary.get("security") == "PASS",
    }
    schema_checks = {
        "report": validate_instance(report, repo / "manage-us-stock-strategy/schemas/strategy-evolution-report.schema.json"),
        "holding": validate_instance(holding, repo / "manage-us-stock-strategy/schemas/holding-universe-snapshot.schema.json"),
        "opportunity": validate_instance(opportunity, repo / "manage-us-stock-strategy/schemas/candidate-universe-snapshot.schema.json"),
        "sentinel": validate_instance(sentinel, repo / "manage-us-stock-strategy/schemas/sentinel-challenger.schema.json"),
    }
    if any(schema_checks.values()):
        checks["TESTS"] = False
    result = {
        "schema_version": "1.0", "artifact_type": "INDEPENDENT_STRATEGY_EVOLUTION_HARDENING_JUDGE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "gates": [{"gate": gate, "status": "PASS" if checks[gate] else "FAIL"} for gate in GATES],
        "schema_errors": schema_checks, "validation_summary": validation_summary,
        "runtime_contract_status": runtime_contract.get("status"),
        "portfolio_hash_before": portfolio_hash_before,
        "portfolio_hash_after": file_hash(repo / "stock-strategy-system/portfolio_state.json"),
        "execution_quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    result["record_hash"] = canonical_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--validation-summary", type=Path, required=True)
    parser.add_argument("--runtime-contract", type=Path, required=True)
    parser.add_argument("--portfolio-hash-before", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = judge(
        repo=args.repo.resolve(), artifact_dir=args.artifact_dir.resolve(),
        validation_summary=load_json(args.validation_summary),
        runtime_contract=load_json(args.runtime_contract),
        portfolio_hash_before=args.portfolio_hash_before,
    )
    write_json(args.output, result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
