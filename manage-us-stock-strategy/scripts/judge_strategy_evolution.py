#!/usr/bin/env python3
"""Independent read-only Judge for Strategy Evolution artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from strategy_evolution import SCORECARD_AXES, validate_evolution_ledger
from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


GATES = (
    "CORE_OPERATIONAL_ISOLATION", "EVENT_RESOLUTION_LIVE_STATUS_MODEL",
    "PORTFOLIO_DECISION_EVIDENCE", "CAPITAL_REALLOCATION", "OPTIMIZATION_SCORECARD",
    "EVIDENCE_ELIGIBILITY", "CHAMPION_FINGERPRINT", "CANDIDATE_UNIVERSE_INTEGRITY",
    "FORWARD_OUTCOMES", "PAIRED_EVALUATION", "UNCERTAINTY_HANDLING",
    "DECISION_ATTRIBUTION", "FINDINGS", "MULTI_HYPOTHESIS_GENERATION",
    "REPLAY_TEMPORAL_ISOLATION", "OOS_ISOLATION", "SIX_AXIS_DOMINANCE",
    "EVOLUTION_LEDGER", "REJECTED_CHALLENGER_MEMORY", "EVOLUTION_BUDGET",
    "POLICY_STABILITY", "POLICY_PROPOSAL_GOVERNANCE", "EVOLUTION_AUTHORITY",
    "EXECUTION_AUTHORITY", "PORTFOLIO_IMMUTABILITY", "TESTS",
)


def judge(*, repo: Path, artifact_dir: Path, validation_summary: dict[str, Any],
          portfolio_hash_before: str) -> dict[str, Any]:
    report = load_json(artifact_dir / "strategy_evolution_report.json")
    champion = load_json(artifact_dir / "champion_policy.json")
    universe = load_json(artifact_dir / "candidate_universe_snapshot.json")
    ledger = load_json(artifact_dir / "strategy_evolution_ledger.json")
    registry = load_json(artifact_dir / "rejected_challenger_registry.json")
    checks: dict[str, bool] = {
        "CORE_OPERATIONAL_ISOLATION": all(int(value) == 0 for value in report["core_counters"].values()),
        "EVENT_RESOLUTION_LIVE_STATUS_MODEL": report["live_event_resolution_status"] in {"NOT_EXERCISED", "SUCCESS", "PARTIAL", "FAILED"},
        "PORTFOLIO_DECISION_EVIDENCE": all(int(value) == 0 for value in report["portfolio_decision_counters"].values()),
        "CAPITAL_REALLOCATION": "SAFE_FALLBACK_EVENT_UNRESOLVED" in report["safe_fallback_reasons"],
        "OPTIMIZATION_SCORECARD": set(report["portfolio_optimization_scorecard"]["axes"]) == set(SCORECARD_AXES) and not report["portfolio_optimization_scorecard"]["single_composite_score_authority"],
        "EVIDENCE_ELIGIBILITY": report["evidence_sufficiency_status"] == "INSUFFICIENT_EVIDENCE",
        "CHAMPION_FINGERPRINT": report["champion_fingerprint"] == champion["champion_fingerprint"] and not champion["auto_apply"],
        "CANDIDATE_UNIVERSE_INTEGRITY": report["candidate_universe_hash"] == universe["candidate_universe_hash"] and universe["survivorship_reconstruction_forbidden"],
        "FORWARD_OUTCOMES": all(item["status"] == "OUTCOME_PENDING" for item in report["forward_outcomes"].values()),
        "PAIRED_EVALUATION": report["paired_evaluation_status"] == "INSUFFICIENT_EVIDENCE",
        "UNCERTAINTY_HANDLING": report["uncertainty"]["evidence_uncertainty_status"] == "INSUFFICIENT_EVIDENCE",
        "DECISION_ATTRIBUTION": report["decision_attribution"]["status"] == "INSUFFICIENT_EVIDENCE",
        "FINDINGS": report["improvement_findings"] == [],
        "MULTI_HYPOTHESIS_GENERATION": report["challenger_hypotheses"] == [],
        "REPLAY_TEMPORAL_ISOLATION": report["analytics_counters"].get("replay_ingested", 0) == 0,
        "OOS_ISOLATION": report["uncertainty"]["out_of_sample_status"] == "INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE",
        "SIX_AXIS_DOMINANCE": report["six_axis_dominance"] == "INSUFFICIENT_EVIDENCE",
        "EVOLUTION_LEDGER": validate_evolution_ledger(ledger),
        "REJECTED_CHALLENGER_MEMORY": registry.get("mode") == "APPEND_ONLY" and isinstance(registry.get("entries"), list),
        "EVOLUTION_BUDGET": report["evolution_budget_status"] == "OBSERVATIONAL_NO_NUMERIC_LIMIT",
        "POLICY_STABILITY": report["policy_stability_status"]["slow_loop"] == "NO_CHANGE_PROPOSED",
        "POLICY_PROPOSAL_GOVERNANCE": report["auto_apply"] is False and report["policy_change_proposals"] == [],
        "EVOLUTION_AUTHORITY": report["evolution_authority"] == "EVOLUTION_4" and report["evolution_5_enabled"] is False,
        "EXECUTION_AUTHORITY": report["execution_authority_status"] == "NONE" and report["order_authority"] is False and report["execution_quantity"] is None and report["quantity_authority"] == "none",
        "PORTFOLIO_IMMUTABILITY": file_hash(repo / "stock-strategy-system/portfolio_state.json") == portfolio_hash_before and report["portfolio_mutation"] is False,
        "TESTS": validation_summary.get("full_suite_failures") == 0 and validation_summary.get("targeted_failures") == 0 and validation_summary.get("schemas") == "PASS" and validation_summary.get("compile") == "PASS" and validation_summary.get("git_diff_check") == "PASS",
    }
    schema_checks = {
        "report": validate_instance(report, repo / "manage-us-stock-strategy/schemas/strategy-evolution-report.schema.json"),
        "champion": validate_instance(champion, repo / "manage-us-stock-strategy/schemas/champion-policy.schema.json"),
        "universe": validate_instance(universe, repo / "manage-us-stock-strategy/schemas/candidate-universe-snapshot.schema.json"),
        "ledger": validate_instance(ledger, repo / "manage-us-stock-strategy/schemas/strategy-evolution-ledger.schema.json"),
    }
    if any(schema_checks.values()):
        checks["TESTS"] = False
    result = {
        "schema_version": "1.0", "artifact_type": "INDEPENDENT_STRATEGY_EVOLUTION_JUDGE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "gates": [{"gate": gate, "status": "PASS" if checks[gate] else "FAIL"} for gate in GATES],
        "schema_errors": schema_checks,
        "validation_summary": validation_summary,
        "portfolio_hash_before": portfolio_hash_before,
        "portfolio_hash_after": file_hash(repo / "stock-strategy-system/portfolio_state.json"),
        "order_authority": False,
    }
    result["record_hash"] = canonical_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--validation-summary", type=Path, required=True)
    parser.add_argument("--portfolio-hash-before", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = judge(repo=args.repo.resolve(), artifact_dir=args.artifact_dir.resolve(),
                   validation_summary=load_json(args.validation_summary),
                   portfolio_hash_before=args.portfolio_hash_before)
    write_json(args.output, result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
