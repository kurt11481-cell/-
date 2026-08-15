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
    build_holding_universe_snapshot,
    build_benchmark_portfolios,
    build_capital_efficiency,
    build_champion_policy,
    build_decision_attribution,
    build_forward_horizon_status,
    build_no_change_decision,
    build_paired_value_attribution,
    build_policy_stability,
    build_policy_change_proposal,
    build_portfolio_optimization_scorecard,
    build_strategy_evolution_report,
    build_sentinel_challenger,
    build_uncertainty,
    classify_evidence_eligibility,
    classify_live_event_resolution,
    classify_six_axis_dominance,
    empty_evolution_ledger,
    extract_prompt_expected_head,
    generate_challenger_hypotheses,
    rejected_challenger_match,
    validate_evolution_ledger,
    validate_paired_evidence,
    validate_safety,
)
from runtime_contract_suite import evaluate_runtime_contracts  # noqa: E402
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
        self.assertEqual(snapshot["universe_role"], "CANDIDATE_OPPORTUNITY_UNIVERSE")
        validate_instance(snapshot, ROOT / "manage-us-stock-strategy/schemas/candidate-universe-snapshot.schema.json")
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"):
            build_candidate_universe_snapshot(
                decision_as_of="2026-08-14T20:30:00Z",
                instruments=[{"ticker": "NBIS", "security_identity": "NBIS-US", "observed_at": "2026-08-14T20:31:00Z"}],
            )

    def test_holding_and_opportunity_universes_are_distinct(self):
        holding = build_holding_universe_snapshot(
            decision_as_of="2026-08-14T20:30:00Z",
            instruments=[{"ticker": "NBIS", "security_identity": "NBIS-US"}],
        )
        opportunity = build_candidate_universe_snapshot(
            decision_as_of="2026-08-14T20:30:00Z", instruments=[],
            availability_status="UNAVAILABLE_AT_DECISION_TIME",
        )
        self.assertNotEqual(holding["universe_role"], opportunity["universe_role"])
        self.assertEqual(opportunity["instrument_identities"], [])
        with self.assertRaisesRegex(ValueError, "RECONSTRUCTION_FORBIDDEN"):
            build_candidate_universe_snapshot(
                decision_as_of="2026-08-14T20:30:00Z",
                instruments=[{"ticker": "NBIS", "security_identity": "NBIS-US"}],
                availability_status="UNAVAILABLE_AT_DECISION_TIME",
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
            "holding_universe_hash", "candidate_opportunity_universe_hash", "policy_independent_source_hash",
        )}
        self.assertTrue(validate_paired_evidence(base, copy.deepcopy(base))["causal_comparison_eligible"])
        changed = copy.deepcopy(base)
        changed["candidate_opportunity_universe_hash"] = "today-survivors"
        self.assertFalse(validate_paired_evidence(base, changed)["causal_comparison_eligible"])

    def test_outcome_lifecycle_no_base_pending_available(self):
        no_base = build_forward_horizon_status(completed_sessions_available=0, base_decision_exists=False)
        self.assertTrue(all(row["status"] == "NO_BASE_DECISION" for row in no_base.values()))
        status = build_forward_horizon_status(completed_sessions_available=1, base_decision_exists=True)
        self.assertEqual(status["1"]["status"], "OUTCOME_AVAILABLE")
        for horizon in ("5", "10", "20"):
            self.assertEqual(status[horizon]["status"], "OUTCOME_PENDING")

    def test_live_event_resolution_status_is_genuine_only(self):
        self.assertEqual(classify_live_event_resolution(
            genuine_run_exists=False, resolution_needed=True, resolution_attempted=True,
            unresolved_relevant_gaps=False,
        ), "NO_GENUINE_RUN_YET")
        self.assertEqual(classify_live_event_resolution(
            genuine_run_exists=True, resolution_needed=False, resolution_attempted=False,
            unresolved_relevant_gaps=False,
        ), "NOT_NEEDED")
        self.assertEqual(classify_live_event_resolution(
            genuine_run_exists=True, resolution_needed=True, resolution_attempted=True,
            unresolved_relevant_gaps=False,
        ), "SUCCESS")

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

    def test_benchmark_and_paired_value_contracts(self):
        benchmarks = build_benchmark_portfolios(
            decision_as_of="2026-08-15T00:00:00Z", champion_fingerprint="a" * 64,
            market_hash="m", event_hash="e", broker_state_reference="b",
            holding_universe_hash="h", candidate_opportunity_universe_hash="c",
            opportunity_universe_available=False, base_decision_exists=False,
        )
        self.assertEqual([b["benchmark_id"] for b in benchmarks], [
            "BENCHMARK_CHAMPION", "BENCHMARK_HOLD_ALL", "BENCHMARK_TRIM_NO_REDEPLOY",
        ])
        self.assertTrue(all(b["outcome_state"] == "NO_BASE_DECISION" for b in benchmarks))
        values = build_paired_value_attribution(
            evidence_identity_status="PAIRED_EVIDENCE_VALID", base_decision_exists=True,
            hold_all_outcome=0.10, trim_no_redeploy_outcome=0.12, full_reallocation_outcome=0.15,
        )
        self.assertAlmostEqual(values["TRIM_VALUE"]["value"], 0.02)
        self.assertAlmostEqual(values["REDEPLOYMENT_VALUE"]["value"], 0.03)
        self.assertAlmostEqual(values["REALLOCATION_VALUE"]["value"], 0.05)
        self.assertEqual(values["CANDIDATE_SELECTION_VALUE"]["status"], "INSUFFICIENT_EVIDENCE")
        invalid = build_paired_value_attribution(
            evidence_identity_status="PAIRED_EVIDENCE_INVALID", base_decision_exists=True,
        )
        self.assertTrue(all(row["status"] == "PAIRED_EVIDENCE_INVALID" for row in invalid.values()))

    def test_sentinel_is_fully_excluded_from_production(self):
        sentinel = build_sentinel_challenger(champion_fingerprint="a" * 64, created_at="2026-08-15T00:00:00Z")
        for field in ("promotion_eligible", "operational_maturity_eligible", "decision_quality_eligible", "policy_evolution_eligible", "production_challenger"):
            self.assertFalse(sentinel[field])
        self.assertEqual(sentinel["namespace"], "SENTINEL_TEST_NAMESPACE")
        validate_instance(sentinel, ROOT / "manage-us-stock-strategy/schemas/sentinel-challenger.schema.json")

    def test_no_change_decision_is_append_only_and_policy_stability_distinguishes_semantics(self):
        ledger = empty_evolution_ledger("cohort")
        decision = build_no_change_decision(
            recorded_at="2026-08-15T00:00:00Z", reason="INSUFFICIENT_EVIDENCE",
            champion_fingerprint="a" * 64, evidence_grade="GRADE_D",
            evidence_sufficiency="INSUFFICIENT_EVIDENCE", uncertainty="INSUFFICIENT_EVIDENCE",
            out_of_sample_status="INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE",
        )
        ledger = append_evolution_entry(ledger, decision)
        self.assertTrue(validate_evolution_ledger(ledger))
        self.assertEqual(ledger["entries"][0]["entry_type"], "NO_CHANGE_DECISION")
        correction = build_policy_stability(
            champion_activated_at="2026-08-15T00:00:00Z", as_of="2026-08-15T01:00:00Z",
            semantic_policy_change_count=0, active_production_challenger_count=0,
            unresolved_production_challenger_count=0, pending_oos_count=0,
            pending_outcome_horizon_count=0, recent_regression_count=0, no_change_decision_count=1,
        )
        semantic = correction | {"semantic_policy_change_count": 1, "policy_stability_status": "UNDER_OBSERVATION"}
        self.assertEqual(correction["policy_stability_status"], "BASELINE_BUILDING")
        self.assertEqual(semantic["semantic_policy_change_count"], 1)

    def test_capital_efficiency_does_not_invent_cost_model(self):
        metrics = build_capital_efficiency(base_decision_exists=False)
        self.assertEqual(metrics["CASH_IDLE_RATIO"]["status"], "NO_BASE_DECISION")
        self.assertEqual(metrics["EXECUTION_COST_EFFICIENCY"]["status"], "NOT_MODELLED")
        self.assertEqual(metrics["NET_TRADING_EFFICIENCY"]["status"], "NOT_VERIFIED")

    def test_runtime_contract_suite_does_not_require_source_fixtures(self):
        manifest = {"runtime_head": "a" * 40, "runtime_tree_hash": "b" * 40, "scheduler_expected_head": "a" * 40}
        result = evaluate_runtime_contracts(
            runtime_head="a" * 40, runtime_tree="b" * 40, runtime_clean=True,
            manifest=manifest, policy_paths_exist=True, schema_paths_exist=True,
            provider_scope_exists=True, champion_valid=True, engines_importable=True,
            ledger_accessible=True, portfolio_read_only_accessible=True,
            kiwoom_preflight_safe=True, authority_firewall_pass=True,
            order_endpoint_usage_detected=False,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["protected_source_only_fixtures_required"])

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
        holding = build_holding_universe_snapshot(decision_as_of="2026-08-15T00:00:00Z", instruments=[])
        universe = build_candidate_universe_snapshot(
            decision_as_of="2026-08-15T00:00:00Z", instruments=[],
            availability_status="UNAVAILABLE_AT_DECISION_TIME",
        )
        report = build_strategy_evolution_report(
            generated_at="2026-08-15T00:00:00Z", champion=champion,
            holding_universe=holding, candidate_universe=universe,
            live_event_resolution_status="NO_GENUINE_RUN_YET", core_counters={},
            portfolio_decision_counters={}, analytics_counters={}, event_resolution_counters={},
            evolution_cohort_id="strategy-evolution-1",
        )
        self.assertEqual(report["lifecycle_status"], "FIRST_GENUINE_DUAL_RUN_PENDING")
        self.assertEqual(report["six_axis_dominance"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(report["evolution_authority"], "EVOLUTION_4")
        self.assertTrue(all(row["status"] == "NO_BASE_DECISION" for row in report["forward_outcomes"].values()))
        self.assertEqual(report["strategy_evolution_counters"]["production_challengers"], 0)
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
