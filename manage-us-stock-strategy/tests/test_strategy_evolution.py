from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from continuous_improvement_sidecar import build_event_resolution_analytics, build_run_record  # noqa: E402
from portfolio_reallocation_shadow import build_capital_reallocation_shadow  # noqa: E402
from strategy_evolution import (  # noqa: E402
    SCORECARD_AXES,
    append_evolution_entry,
    build_candidate_universe_snapshot,
    build_champion_policy,
    build_decision_attribution,
    build_forward_horizon_status,
    build_policy_change_proposal,
    build_portfolio_optimization_scorecard,
    build_strategy_evolution_report,
    build_uncertainty,
    classify_evidence_eligibility,
    classify_six_axis_dominance,
    empty_evolution_ledger,
    extract_prompt_expected_head,
    generate_challenger_hypotheses,
    rejected_challenger_match,
    validate_evolution_ledger,
    validate_paired_evidence,
    validate_safety,
)
from validation_common import load_json, validate_instance  # noqa: E402


POLICY = ROOT / "workspace/policies/continuous_improvement_policy.json"
CONTINUOUS_FIXTURE = ROOT / "manage-us-stock-strategy/tests/fixtures/continuous-improvement-sidecar.fixture.json"
REALLOCATION_POLICY = ROOT / "workspace/policies/portfolio_reallocation_shadow_policy.json"
REALLOCATION_CONTEXT = ROOT / "manage-us-stock-strategy/tests/fixtures/portfolio-reallocation-shadow.context.json"


class StrategyEvolutionTests(unittest.TestCase):
    def test_deployment_prompt_expected_head_is_explicit(self):
        self.assertEqual(extract_prompt_expected_head("expected HEAD: `" + "a" * 40 + "`"), "a" * 40)
        self.assertIsNone(extract_prompt_expected_head("No runtime commit pin."))

    def test_evidence_grade_and_four_eligibility_axes_are_separate(self):
        scheduled = classify_evidence_eligibility(
            run_provenance_status="VERIFIED_SCHEDULED", temporal_evidence_valid=True,
            decision_artifact_valid=True, actionable_decision=False,
        )
        self.assertEqual(scheduled["evidence_grade"], "GRADE_A")
        self.assertTrue(scheduled["genuine_decision_observation"])
        self.assertFalse(scheduled["actionable_decision"])
        manual = classify_evidence_eligibility(
            run_provenance_status="VERIFIED_MANUAL", temporal_evidence_valid=True,
            decision_artifact_valid=True, actionable_decision=True,
        )
        self.assertEqual(manual["evidence_grade"], "GRADE_B")
        self.assertFalse(manual["operational_maturity_eligible"])
        self.assertTrue(manual["decision_quality_eligible"])
        replay = classify_evidence_eligibility(
            run_provenance_status="VERIFIED_REPLAY", temporal_evidence_valid=True,
            decision_artifact_valid=True, actionable_decision=True,
        )
        self.assertEqual(replay["evidence_grade"], "GRADE_C")
        self.assertFalse(replay["policy_evolution_eligible"])

    def test_continuous_run_record_cannot_promote_manual(self):
        fixture = load_json(CONTINUOUS_FIXTURE)
        policy = load_json(POLICY)
        manual = build_run_record(fixture["runs"][0] | {
            "execution_origin": "MANUAL", "decision_mode": "MANUAL_READ_ONLY",
            "provenance_evidence": {"manual_run_id": "manual-1", "operator_initiated": True},
        }, policy)
        self.assertEqual(manual["evidence_grade"], "GRADE_B")
        self.assertFalse(manual["operational_maturity_eligible"])
        self.assertFalse(manual["policy_evolution_eligible"])

    def test_candidate_universe_is_point_in_time_and_rejects_survivorship_lookahead(self):
        snapshot = build_candidate_universe_snapshot(
            decision_as_of="2026-08-14T20:30:00Z",
            instruments=[{"ticker": "NBIS", "security_identity": "NBIS-US", "observed_at": "2026-08-14T20:29:00Z"}],
        )
        self.assertTrue(snapshot["survivorship_reconstruction_forbidden"])
        validate_instance(snapshot, ROOT / "manage-us-stock-strategy/schemas/candidate-universe-snapshot.schema.json")
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"):
            build_candidate_universe_snapshot(
                decision_as_of="2026-08-14T20:30:00Z",
                instruments=[{"ticker": "NBIS", "security_identity": "NBIS-US", "observed_at": "2026-08-14T20:31:00Z"}],
            )

    def test_champion_fingerprint_is_deterministic_and_read_only(self):
        kwargs = dict(
            champion_policy_id="champion-v1", semantic_fingerprint="s" * 64,
            git_tree_hash="a" * 40, provider_scope_hash="b" * 64,
            event_policy_hash="c" * 64, portfolio_decision_policy_hash="d" * 64,
            reallocation_policy_hash="e" * 64, activated_at="2026-08-15T00:00:00Z",
        )
        first = build_champion_policy(**kwargs)
        second = build_champion_policy(**kwargs)
        self.assertEqual(first["champion_fingerprint"], second["champion_fingerprint"])
        self.assertFalse(first["auto_apply"])
        validate_instance(first, ROOT / "manage-us-stock-strategy/schemas/champion-policy.schema.json")

    def test_paired_champion_challenger_require_identical_evidence(self):
        base = {key: key + "-hash" for key in (
            "decision_as_of", "market_evidence_hash", "event_evidence_hash", "broker_state_hash",
            "candidate_universe_hash", "policy_independent_source_hash",
        )}
        self.assertTrue(validate_paired_evidence(base, copy.deepcopy(base))["causal_comparison_eligible"])
        changed = copy.deepcopy(base)
        changed["candidate_universe_hash"] = "today-survivors"
        self.assertFalse(validate_paired_evidence(base, changed)["causal_comparison_eligible"])

    def test_outcomes_use_completed_session_horizons_and_pending(self):
        status = build_forward_horizon_status(completed_sessions_available=1)
        self.assertEqual(status["1"]["status"], "AVAILABLE")
        for horizon in ("5", "10", "20"):
            self.assertEqual(status[horizon]["status"], "OUTCOME_PENDING")

    def test_scorecard_has_six_axes_and_hard_gate_wins(self):
        scorecard = build_portfolio_optimization_scorecard(
            data_integrity="FAIL", hard_safety="PASS", executability="PASS",
            evidence_sample_size=99,
        )
        self.assertEqual(set(scorecard["axes"]), set(SCORECARD_AXES))
        self.assertFalse(scorecard["single_composite_score_authority"])
        self.assertEqual(scorecard["dominance_status"], "SAFETY_REJECTED")
        self.assertEqual(classify_six_axis_dominance(scorecard=scorecard, challenger_deltas={axis: 10 for axis in SCORECARD_AXES}), "SAFETY_REJECTED")
        validate_instance(scorecard, ROOT / "manage-us-stock-strategy/schemas/portfolio-optimization-scorecard.schema.json")

    def test_pareto_dominance_does_not_reduce_to_return(self):
        scorecard = build_portfolio_optimization_scorecard(
            data_integrity="PASS", hard_safety="PASS", executability="PASS", evidence_sample_size=5,
        )
        mixed = {axis: 1.0 for axis in SCORECARD_AXES}
        mixed["STABILITY"] = -1.0
        self.assertEqual(classify_six_axis_dominance(scorecard=scorecard, challenger_deltas=mixed), "NON_DOMINATED_DIFFERENT_PROFILE")
        self.assertEqual(classify_six_axis_dominance(scorecard=scorecard, challenger_deltas={axis: 1.0 for axis in SCORECARD_AXES}), "DOMINATES_CHAMPION")

    def test_uncertainty_and_oos_are_not_fabricated(self):
        uncertainty = build_uncertainty(paired_sample_size=0, out_of_sample_available=False)
        self.assertEqual(uncertainty["evidence_uncertainty_status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(uncertainty["out_of_sample_status"], "INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE")
        self.assertIsNone(uncertainty["confidence_interval"])

    def test_attribution_rejects_unknown_scope(self):
        self.assertEqual(build_decision_attribution([])["status"], "INSUFFICIENT_EVIDENCE")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_ATTRIBUTION_SCOPE"):
            build_decision_attribution([{"scope": "TOTAL_RETURN_GUESS"}])

    def test_multi_hypothesis_retains_all_and_scope_isolated(self):
        findings = [
            {"finding_id": "f1", "exact_scope": {"ticker": "NBIS", "decision_class": "PROFIT_TRIM"}},
            {"finding_id": "f2", "exact_scope": {"ticker": "SOXL", "decision_class": "EVENT_BLOCKING"}},
        ]
        hypotheses = generate_challenger_hypotheses(findings)
        self.assertEqual(len(hypotheses), 2)
        self.assertNotEqual(hypotheses[0]["exact_scope"], hypotheses[1]["exact_scope"])

    def test_policy_proposal_never_auto_applies_and_accounts_multiple_hypotheses(self):
        proposal = build_policy_change_proposal(
            proposal_id="p1", champion_policy_id="c1", challenger_policy_id="x1",
            hypothesis={"exact_scope": {"ticker": "NBIS"}},
            evidence_window={"discovery": [], "validation": [], "out_of_sample": []},
            sample_size=0, impacts={}, counter_evidence=["INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE"],
            out_of_sample_status="INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE",
            uncertainty=build_uncertainty(paired_sample_size=0, out_of_sample_available=False),
            number_of_challengers_tested=3, number_rejected=2, selected_rank=None,
            rollback_plan="Restore champion fingerprint after independent approval.",
        )
        self.assertFalse(proposal["auto_apply"])
        self.assertEqual(proposal["multiple_hypothesis_risk"], "PRESENT")

    def test_evolution_ledger_is_append_only_and_rejected_memory_requires_new_evidence(self):
        ledger = empty_evolution_ledger("evolution-cohort-1")
        ledger = append_evolution_entry(ledger, {"policy_id": "challenger-a", "result": "REJECTED"})
        self.assertTrue(validate_evolution_ledger(ledger))
        tampered = copy.deepcopy(ledger)
        tampered["entries"][0]["result"] = "PROMOTED"
        self.assertFalse(validate_evolution_ledger(tampered))
        candidate = {"exact_scope": {"ticker": "NBIS"}, "mechanism": "WIDER_TRIM_BAND"}
        first = rejected_challenger_match({"entries": []}, candidate)
        registry = {"entries": [{"rejection_id": "r1", "similarity_fingerprint": first["similarity_fingerprint"]}]}
        self.assertEqual(rejected_challenger_match(registry, candidate)["status"], "SIMILAR_REJECTED_POLICY_FOUND")

    def test_event_analytics_are_origin_and_ticker_category_action_scoped(self):
        records = [{
            "execution_origin": "REPLAY",
            "decision_artifacts": [{
                "artifact_type": "EVENT_RESOLUTION_OBSERVATION", "ticker": "NBIS",
                "resolution_status": "UNRESOLVED_ACTION_BLOCKING", "resolution_attempt_count": 1,
                "holding_compile_mode": "DEGRADED_EVENT_SCOPED", "required_categories_checked": 2,
                "resolved_categories": 1, "unresolved_categories": [{
                    "category": "dilution", "action": "ADD", "requirement_level": "REQUIRED",
                    "missing_reason": "SOURCE_UNAVAILABLE", "source_authority": "PRIMARY_AUTHORITY",
                }],
            }],
        }]
        analytics = build_event_resolution_analytics(records)
        self.assertIn("REPLAY", analytics["run_level"])
        self.assertEqual(analytics["ticker_category_action_level"][0]["ticker"], "NBIS")
        self.assertTrue(analytics["live_scheduled_quality_excludes_replay"])

    def test_safe_fallback_reason_is_not_optimized_keep_cash(self):
        context = load_json(REALLOCATION_CONTEXT)
        policy = load_json(REALLOCATION_POLICY)
        for row in context["opportunity_candidates"]:
            row["event_readiness_status"] = "EVENT_PARTIAL_BUY_BLOCKING"
        result = build_capital_reallocation_shadow(context, policy)
        self.assertEqual(result["keep_cash_state"], "SAFE_FALLBACK_NO_NEW_CAPITAL_DEPLOYMENT")
        self.assertEqual(result["safe_fallback_reason"], "SAFE_FALLBACK_EVENT_UNRESOLVED")
        self.assertEqual(result["verified_orderable_cash_from_expected_proceeds_usd"], 0.0)

    def test_current_report_preserves_execution_and_empty_evidence(self):
        champion = build_champion_policy(
            champion_policy_id="champion-v1", semantic_fingerprint="s" * 64,
            git_tree_hash="a" * 40, provider_scope_hash="b" * 64,
            event_policy_hash="c" * 64, portfolio_decision_policy_hash="d" * 64,
            reallocation_policy_hash="e" * 64, activated_at="2026-08-15T00:00:00Z",
        )
        universe = build_candidate_universe_snapshot(decision_as_of="2026-08-15T00:00:00Z", instruments=[])
        report = build_strategy_evolution_report(
            generated_at="2026-08-15T00:00:00Z", champion=champion, candidate_universe=universe,
            live_event_resolution_status="NOT_EXERCISED", core_counters={},
            portfolio_decision_counters={}, analytics_counters={}, event_resolution_counters={},
            evolution_cohort_id="strategy-evolution-1",
        )
        self.assertEqual(report["lifecycle_status"], "FIRST_GENUINE_DUAL_RUN_PENDING")
        self.assertEqual(report["six_axis_dominance"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(report["evolution_authority"], "EVOLUTION_4")
        validate_safety(report)
        validate_instance(report, ROOT / "manage-us-stock-strategy/schemas/strategy-evolution-report.schema.json")

    def test_strategy_evolution_policy_and_cohort_validate(self):
        self.assertEqual(validate_instance(
            load_json(ROOT / "workspace/policies/strategy_evolution_policy.json"),
            ROOT / "manage-us-stock-strategy/schemas/strategy-evolution-policy.schema.json",
        ), [])
        self.assertEqual(validate_instance(
            load_json(ROOT / "workspace/state/strategy_evolution/strategy_evolution_cohort.json"),
            ROOT / "manage-us-stock-strategy/schemas/strategy-evolution-cohort.schema.json",
        ), [])


if __name__ == "__main__":
    unittest.main()
