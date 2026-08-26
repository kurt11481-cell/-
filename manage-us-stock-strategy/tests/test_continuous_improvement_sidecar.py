from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from continuous_improvement_sidecar import (  # noqa: E402
    OUTCOME_HORIZONS,
    ANALYTICS_ENGINE_VERSION,
    METRIC_DEFINITION_VERSION,
    append_outcome_artifact,
    append_run_record,
    build_blocked_opportunity_review,
    build_counterfactual_evaluation,
    build_decision_stability,
    build_drift_observation,
    build_execution_analytics_link,
    build_event_resolution_analytics,
    build_operational_analytics,
    build_policy_change_proposal,
    build_report,
    build_run_record,
    build_shadow_policy_experiment,
    compute_analytics_semantic_fingerprint,
    derive_run_provenance,
    empty_ledger,
    empty_outcome_ledger,
    evaluate_forward_outcomes,
    run_sidecar_isolated,
    assert_counter_authority_firewall,
    assert_production_decision_consumable,
    validate_ledger_chain,
    validate_outcome_ledger_chain,
    validate_temporal_evidence,
)
from validation_common import file_hash, load_json, validate_instance  # noqa: E402


FIXTURE = ROOT / "manage-us-stock-strategy/tests/fixtures/continuous-improvement-sidecar.fixture.json"
POLICY = ROOT / "workspace/policies/continuous_improvement_policy.json"
PORTFOLIO = ROOT / "stock-strategy-system/portfolio_state.json"
PROGRESS = ROOT / "workspace/state/integrated_shadow/shadow_progress.json"
REPORT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/continuous-improvement-report.schema.json"
LEDGER_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/unified-run-ledger.schema.json"
RUN_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/continuous-improvement-run-record.schema.json"
OUTCOME_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/forward-outcome-artifact.schema.json"
PROPOSAL_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/policy-change-proposal.schema.json"
EXPERIMENT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/shadow-policy-experiment.schema.json"
OUTCOME_LEDGER_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/forward-outcome-ledger.schema.json"
COHORT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/continuous-improvement-cohort.schema.json"
POLICY_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/continuous-improvement-policy.schema.json"
FINDING_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/improvement-finding.schema.json"
EXECUTION_LINK_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/execution-analytics-link.schema.json"


def scheduled_run() -> dict:
    return {
        "run_id": "scheduled-001",
        "execution_origin": "SCHEDULED_GENUINE",
        "decision_mode": "LIVE_READ_ONLY",
        "operational_day_id": "2026-08-14",
        "provenance_evidence": {
            "task_id": "REGULAR_CLOSE_T_PLUS_30",
            "scheduled_run_id": "scheduled-run-001",
            "expected_operational_phase": "REGULAR_CLOSE_T_PLUS_30",
            "expected_trading_day": "2026-08-14",
            "deployment_provenance_valid": True,
            "runtime_head_matches": True,
            "semantic_cohort_matches": True,
            "schedule_provenance_valid": True,
            "runtime_manifest_hash": "1" * 64,
            "clean_committed_main": True,
        },
        "git_sha": "1cb35755ae56492599605af87403b801940f2559",
        "runtime_manifest_hash": "1" * 64,
        "provider_scope_hash": "2" * 64,
        "semantic_cohort": "integrated-shadow-246c0aa2eb76b27f",
        "improvement_analytics_cohort": "continuous-improvement-sidecar-v2",
        "decision_as_of": "2026-08-14T22:00:00+00:00",
        "market_data_cutoff": "2026-08-14T20:00:00+00:00",
        "event_cutoff": "2026-08-14T21:00:00+00:00",
        "broker_cutoff": "2026-08-14T21:30:00+00:00",
        "candidate_cutoff": None,
        "portfolio_hash_before": file_hash(PORTFOLIO),
        "portfolio_hash_after": file_hash(PORTFOLIO),
        "source_artifacts": [],
        "decision_artifacts": [],
        "delivery_status": "DELIVERED",
    }


def verified_manual_contract() -> dict:
    return {
        "evidence_grade": "GRADE_B",
        "manual_data_verification_status": "VERIFIED_REAL_DATA",
        "kiwoom_health_status": "HEALTHY",
        "broker_snapshot_status": "AVAILABLE",
        "orderable_cash_status": "VERIFIED",
        "current_price_status": "AVAILABLE",
        "historical_daily_evidence_status": "AVAILABLE",
        "finalized_bar_preflight_status": "PASS",
        "identity_authority_status": "VERIFIED",
        "session_authority_status": "VERIFIED",
        "integrated_authority_cohort_status": "MATCHED",
        "preflight_status": "PASS",
        "manual_analysis_view": {
            "holding_source": "BROKER_OBSERVED_STATE",
            "ephemeral": True,
            "memory_only": True,
            "portfolio_mutation": False,
            "order_authority": False,
            "quantity_authority": "none",
            "execution_quantity": None,
        },
    }


class ContinuousImprovementSidecarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load_json(FIXTURE)
        cls.policy = load_json(POLICY)

    def test_manual_cannot_spoof_scheduled_eligibility(self):
        raw = scheduled_run()
        raw["execution_origin"] = "MANUAL"
        raw["decision_mode"] = "MANUAL_READ_ONLY"
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual(result["run_provenance_status"], "UNVERIFIED")
        self.assertFalse(result["maturity_eligible"])

    def test_verified_manual_unverified_or_missing_grade_stays_unverified(self):
        for provided_grade in ("UNVERIFIED", None):
            raw = copy.deepcopy(self.fixture["runs"][0])
            raw.update(verified_manual_contract())
            if provided_grade is None:
                raw.pop("evidence_grade")
            else:
                raw["evidence_grade"] = provided_grade
            result = derive_run_provenance(raw, self.policy)
            self.assertEqual("VERIFIED_MANUAL", result["run_provenance_status"])
            self.assertEqual("UNVERIFIED", result["evidence_grade"])
            self.assertFalse(result["decision_quality_eligible"])
            self.assertFalse(result["counterfactual_eligible"])

    def test_verified_manual_grade_b_requires_verified_real_data(self):
        raw = copy.deepcopy(self.fixture["runs"][0])
        raw.update(verified_manual_contract())
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual("GRADE_B", result["evidence_grade"])
        self.assertTrue(result["decision_quality_eligible"])

        failed = copy.deepcopy(raw)
        failed["manual_data_verification_status"] = "FAILED"
        failed_result = derive_run_provenance(failed, self.policy)
        self.assertEqual("UNVERIFIED", failed_result["evidence_grade"])
        self.assertFalse(failed_result["decision_quality_eligible"])

    def test_verified_manual_grade_b_requires_every_authority_and_preflight_gate(self):
        base = copy.deepcopy(self.fixture["runs"][0])
        base.update(verified_manual_contract())
        failures = {
            "identity_authority_status": "NOT_VERIFIED",
            "session_authority_status": "NOT_VERIFIED",
            "integrated_authority_cohort_status": "NOT_VERIFIED",
            "preflight_status": "PARTIAL",
        }
        for field, failed_value in failures.items():
            with self.subTest(field=field, value=failed_value):
                raw = copy.deepcopy(base)
                raw[field] = failed_value
                result = derive_run_provenance(raw, self.policy)
                self.assertEqual("UNVERIFIED", result["evidence_grade"])
                self.assertFalse(result["decision_quality_eligible"])
        failed_preflight = copy.deepcopy(base)
        failed_preflight["preflight_status"] = "FAIL"
        result = derive_run_provenance(failed_preflight, self.policy)
        self.assertEqual("UNVERIFIED", result["evidence_grade"])
        self.assertFalse(result["decision_quality_eligible"])

    def test_manual_system_portfolio_fallback_is_not_grade_b_or_actionable(self):
        raw = copy.deepcopy(self.fixture["runs"][0])
        raw.update(verified_manual_contract())
        raw["manual_analysis_view"]["holding_source"] = "SYSTEM_PORTFOLIO_STATE_FALLBACK"
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual("UNVERIFIED", result["evidence_grade"])
        self.assertFalse(result["decision_quality_eligible"])
        self.assertFalse(result["counterfactual_eligible"])

    def test_non_manual_grade_contracts_are_unchanged(self):
        scheduled = derive_run_provenance(scheduled_run(), self.policy)
        replay = derive_run_provenance(self.fixture["runs"][1], self.policy)
        test_only = derive_run_provenance(self.fixture["runs"][2], self.policy)
        shadow = derive_run_provenance(self.fixture["runs"][3], self.policy)
        self.assertEqual("GRADE_A", scheduled["evidence_grade"])
        self.assertEqual("GRADE_C", replay["evidence_grade"])
        self.assertEqual("GRADE_D", test_only["evidence_grade"])
        self.assertEqual("GRADE_D", shadow["evidence_grade"])

    def test_replay_cannot_be_maturity_eligible(self):
        result = derive_run_provenance(self.fixture["runs"][1], self.policy)
        self.assertEqual(result["run_provenance_status"], "VERIFIED_REPLAY")
        self.assertFalse(result["maturity_eligible"])

    def test_shadow_cannot_be_maturity_eligible(self):
        result = derive_run_provenance(self.fixture["runs"][3], self.policy)
        self.assertEqual(result["run_provenance_status"], "VERIFIED_SHADOW")
        self.assertFalse(result["maturity_eligible"])

    def test_test_cannot_be_maturity_eligible(self):
        result = derive_run_provenance(self.fixture["runs"][2], self.policy)
        self.assertEqual(result["run_provenance_status"], "VERIFIED_TEST")
        self.assertFalse(result["maturity_eligible"])

    def test_legacy_test_and_shadow_aliases_are_canonicalized(self):
        raw = copy.deepcopy(self.fixture["runs"][2])
        raw["execution_origin"] = "TEST"
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual(result["execution_origin"], "TEST_ONLY")
        raw = copy.deepcopy(self.fixture["runs"][3])
        raw["execution_origin"] = "SHADOW"
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual(result["execution_origin"], "SHADOW_COUNTERFACTUAL")

    def test_test_only_decision_is_rejected_by_live_consumer(self):
        with self.assertRaisesRegex(ValueError, "NON_LIVE_DECISION_REJECTED"):
            assert_production_decision_consumable({
                "decision_mode": "TEST_ONLY", "order_authority": False,
                "quantity_authority": "none", "execution_quantity": None,
            })

    def test_replay_result_cannot_spoof_scheduled_decision_mode(self):
        raw = copy.deepcopy(self.fixture["runs"][1])
        raw["decision_mode"] = "LIVE_READ_ONLY"
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual(result["run_provenance_status"], "UNVERIFIED")
        self.assertIn("DECISION_MODE_MISMATCH", result["reason_codes"])

    def test_live_read_only_decision_passes_consumer_firewall(self):
        assert_production_decision_consumable({
            "decision_mode": "LIVE_READ_ONLY", "order_authority": False,
            "quantity_authority": "none", "execution_quantity": None,
        })

    def test_valid_postclose_scheduled_provenance_is_eligible(self):
        result = derive_run_provenance(scheduled_run(), self.policy)
        self.assertEqual(result["run_provenance_status"], "VERIFIED_SCHEDULED")
        self.assertTrue(result["maturity_eligible"])

    def test_preopen_scheduled_provenance_never_counts(self):
        raw = scheduled_run()
        raw["provenance_evidence"]["task_id"] = "PRE_OPEN_T_MINUS_30"
        raw["provenance_evidence"]["expected_operational_phase"] = "PRE_OPEN_T_MINUS_30"
        raw["delivery_status"] = "NOT_APPLICABLE"
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual(result["run_provenance_status"], "VERIFIED_SCHEDULED")
        self.assertFalse(result["maturity_eligible"])

    def test_missing_deployment_provenance_is_unverified(self):
        raw = scheduled_run()
        raw["provenance_evidence"]["deployment_provenance_valid"] = False
        result = derive_run_provenance(raw, self.policy)
        self.assertEqual(result["run_provenance_status"], "UNVERIFIED")
        self.assertIn("DEPLOYMENT_PROVENANCE_INVALID", result["reason_codes"])

    def test_ledger_append_is_idempotent(self):
        record = build_run_record(self.fixture["runs"][0], self.policy)
        ledger, duplicate = append_run_record(empty_ledger("test"), record)
        self.assertFalse(duplicate)
        ledger_again, duplicate = append_run_record(ledger, record)
        self.assertTrue(duplicate)
        self.assertEqual(len(ledger_again["entries"]), 1)
        self.assertTrue(validate_ledger_chain(ledger_again))

    def test_duplicate_scheduled_run_does_not_double_count(self):
        record = build_run_record(scheduled_run(), self.policy)
        ledger, _ = append_run_record(empty_ledger("test"), record)
        ledger, duplicate = append_run_record(ledger, copy.deepcopy(record))
        self.assertTrue(duplicate)
        self.assertEqual(sum(item["maturity_eligible"] for item in ledger["entries"]), 1)

    def test_temporal_evidence_rejects_lookahead(self):
        result = validate_temporal_evidence(
            "2026-07-01T20:00:00+00:00",
            [{"observed_at": "2026-07-01T20:00:01+00:00"}],
        )
        self.assertEqual(result["status"], "TEMPORAL_EVIDENCE_VIOLATION")
        self.assertFalse(result["evaluation_valid"])

    def test_temporal_violation_invalidates_whole_run(self):
        raw = copy.deepcopy(self.fixture["runs"][0])
        raw["source_artifacts"][0]["observed_at"] = "2026-07-01T22:00:00+00:00"
        record = build_run_record(raw, self.policy)
        self.assertFalse(record["evaluation_valid"])
        self.assertFalse(record["maturity_eligible"])

    def test_original_decision_remains_immutable(self):
        decision = copy.deepcopy(self.fixture["decisions"][0])
        original = copy.deepcopy(decision)
        outcome = evaluate_forward_outcomes(decision, self.fixture["bars_by_ticker"]["NBIS"])
        self.assertEqual(decision, original)
        self.assertTrue(outcome["original_decision_immutable"])
        self.assertEqual(outcome["decision_fingerprint"], __import__("validation_common").canonical_hash(original))

    def test_completed_session_horizon_indexing(self):
        outcome = evaluate_forward_outcomes(self.fixture["decisions"][0], self.fixture["bars_by_ticker"]["NBIS"])
        statuses = {item["horizon_completed_sessions"]: item["status"] for item in outcome["results"]}
        self.assertEqual(tuple(statuses), OUTCOME_HORIZONS)
        self.assertEqual(statuses[1], "AVAILABLE")
        self.assertEqual(statuses[5], "AVAILABLE")
        self.assertEqual(statuses[10], "OUTCOME_PENDING")
        self.assertEqual(statuses[20], "OUTCOME_PENDING")

    def test_outcome_metrics_mfe_mae_and_drawdown(self):
        outcome = evaluate_forward_outcomes(self.fixture["decisions"][0], self.fixture["bars_by_ticker"]["NBIS"])
        five = next(item for item in outcome["results"] if item["horizon_completed_sessions"] == 5)
        self.assertAlmostEqual(five["forward_return"], 0.10)
        self.assertAlmostEqual(five["mfe"], 0.11)
        self.assertAlmostEqual(five["mae"], -0.01)
        self.assertLess(five["maximum_drawdown"], 0)

    def test_provider_lineage_is_preserved_without_averaging(self):
        outcome = evaluate_forward_outcomes(self.fixture["decisions"][0], self.fixture["bars_by_ticker"]["NBIS"])
        one = outcome["results"][0]
        self.assertEqual(one["provider"], "KIWOOM")
        self.assertEqual(one["price_semantics"], "RAW_REGULAR_SESSION_CLOSE")
        self.assertNotIn("averaged_price", one)

    def test_outcome_artifact_schema(self):
        outcome = evaluate_forward_outcomes(self.fixture["decisions"][0], self.fixture["bars_by_ticker"]["NBIS"])
        self.assertEqual(validate_instance(outcome, OUTCOME_SCHEMA), [])

    def test_outcome_append_is_separate_idempotent_and_hash_chained(self):
        outcome = evaluate_forward_outcomes(self.fixture["decisions"][0], self.fixture["bars_by_ticker"]["NBIS"])
        ledger, duplicate = append_outcome_artifact(empty_outcome_ledger("test"), outcome)
        self.assertFalse(duplicate)
        ledger, duplicate = append_outcome_artifact(ledger, copy.deepcopy(outcome))
        self.assertTrue(duplicate)
        self.assertEqual(len(ledger["entries"]), 1)
        self.assertTrue(validate_outcome_ledger_chain(ledger))

    def test_forward_outcome_rejects_evidence_newer_than_analytics_cutoff(self):
        bars = copy.deepcopy(self.fixture["bars_by_ticker"]["NBIS"])
        bars[0]["observed_at"] = "2026-08-16T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "TEMPORAL_EVIDENCE_VIOLATION"):
            evaluate_forward_outcomes(
                self.fixture["decisions"][0], bars,
                evaluation_as_of=self.fixture["analytics_as_of"],
            )

    def test_blocked_opportunity_review_does_not_call_rising_price_an_error(self):
        review = build_blocked_opportunity_review(self.fixture["decisions"])
        self.assertEqual(len(review["items"]), 1)
        self.assertFalse(review["items"][0]["later_price_alone_proves_error"])
        self.assertFalse(review["items"][0]["production_blocker_change_authorized"])

    def test_counterfactual_is_modelled_only_and_proceeds_are_not_cash(self):
        result = build_counterfactual_evaluation(self.fixture["counterfactual"])
        self.assertEqual(result["counterfactual_validity"], "MODELLED_ONLY")
        self.assertEqual(result["expected_sale_proceeds_status"], "SHADOW_ONLY")
        self.assertEqual(result["verified_orderable_cash_from_expected_proceeds_usd"], 0)
        self.assertEqual(result["broker_cash_before"], result["broker_cash_after"])

    def test_shadow_proceeds_cannot_be_consumed_as_broker_cash(self):
        with self.assertRaisesRegex(ValueError, "ANALYTICS_AUTHORITY_FIREWALL_VIOLATION"):
            assert_counter_authority_firewall({
                "verified_orderable_cash_from_expected_proceeds_usd": 1.0,
            })

    def test_shadow_quantity_cannot_be_consumed_as_execution_quantity(self):
        with self.assertRaisesRegex(ValueError, "ANALYTICS_AUTHORITY_FIREWALL_VIOLATION"):
            assert_counter_authority_firewall({
                "execution_quantity": 1, "quantity_authority": "shadow",
            })

    def test_analytics_cannot_mutate_core_or_portfolio_decision_counters(self):
        with self.assertRaisesRegex(ValueError, "ANALYTICS_AUTHORITY_FIREWALL_VIOLATION"):
            assert_counter_authority_firewall({"operational_counter_mutation": True})
        with self.assertRaisesRegex(ValueError, "ANALYTICS_AUTHORITY_FIREWALL_VIOLATION"):
            assert_counter_authority_firewall({"portfolio_decision_counter_mutation": True})

    def test_keep_cash_is_evaluated(self):
        result = build_counterfactual_evaluation(self.fixture["counterfactual"])
        self.assertIn("KEEP_CASH", {item["action"] for item in result["alternatives"]})

    def test_decision_flip_analytics_is_observational(self):
        result = build_decision_stability(self.fixture["decisions"])
        self.assertEqual(result["flip_count"], 1)
        self.assertFalse(result["hysteresis_thresholds_active"])

    def test_drift_monitor_builds_baseline_without_thresholds(self):
        records = [build_run_record(item, self.policy) for item in self.fixture["runs"]]
        drift = build_drift_observation(records)
        self.assertEqual(drift["status"], "DRIFT_MONITORING_READY")
        self.assertFalse(drift["production_thresholds_configured"])
        self.assertTrue(all(value == "BASELINE_BUILDING" for value in drift["states"].values()))

    def test_operational_analytics_excludes_non_scheduled(self):
        records = [build_run_record(item, self.policy) for item in self.fixture["runs"]]
        result = build_operational_analytics(records)
        self.assertEqual(result["scheduled_denominator"], 0)
        self.assertFalse(result["manual_replay_test_shadow_in_denominator"])

    def test_event_resolution_analytics_records_implementation_gap_without_policy_apply(self):
        record = build_run_record(self.fixture["runs"][0], self.policy)
        record["decision_artifacts"] = [{
            "artifact_type": "EVENT_ACTIONABILITY_ORCHESTRATION_GAP",
            "ticker": "MVLL",
            "resolution_status": "UNRESOLVED_ACTION_BLOCKING",
            "holding_compile_mode": "DEGRADED_EVENT_SCOPED",
            "resolution_attempt_count": 0,
            "buy_blocked_by_event": True,
            "hold_review_required": True,
            "keep_cash_state": "SAFE_FALLBACK_NO_NEW_CAPITAL_DEPLOYMENT",
            "unresolved_categories": [{"category": "sponsor_notice", "missing_reason": "SOURCE_STALE", "source_type": "ETF_SPONSOR_NOTICE"}],
        }]
        result = build_event_resolution_analytics([record])
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(result["degraded_compile_rate"], 1.0)
        self.assertEqual(result["safe_fallback_rate"], 1.0)
        self.assertFalse(result["production_policy_mutation"])
        self.assertFalse(result["order_authority"])

    def test_policy_proposal_can_never_auto_apply(self):
        proposal = build_policy_change_proposal(
            exact_scope={"ticker": "NBIS"}, current_policy={"x": 1}, proposed_policy={"x": 2},
            evidence_window={"start": "a", "end": "b"}, sample_size=3,
            supporting_evidence=["a"], counter_evidence=["b"],
        )
        self.assertFalse(proposal["auto_apply"])
        self.assertEqual(proposal["approval_status"], "EXPLICIT_USER_APPROVAL_REQUIRED")
        self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])

    def test_shadow_policy_experiment_cannot_mutate_production(self):
        experiment = build_shadow_policy_experiment(
            current_policy={"x": 1}, candidate_policy={"x": 2},
            eligible_evidence_hashes=["a" * 64], out_of_sample_hashes=[],
        )
        self.assertFalse(experiment["production_policy_mutation"])
        self.assertFalse(experiment["portfolio_mutation"])
        self.assertFalse(experiment["operational_counter_mutation"])
        self.assertEqual(validate_instance(experiment, EXPERIMENT_SCHEMA), [])

    def test_analytics_failure_isolated_from_core_scheduled_result(self):
        core = {"status": "DELIVERED", "valid": True}
        broken = copy.deepcopy(self.fixture)
        broken.pop("counterfactual")
        result = run_sidecar_isolated(core_scheduled_result=core, fixture=broken, policy=self.policy)
        self.assertEqual(result["sidecar_status"], "FAILED_ISOLATED")
        self.assertEqual(core, {"status": "DELIVERED", "valid": True})
        self.assertFalse(result["core_result_mutated"])

    def test_build_report_does_not_change_portfolio_or_operational_progress(self):
        before_portfolio = file_hash(PORTFOLIO)
        before_progress = file_hash(PROGRESS)
        report, _ = build_report(copy.deepcopy(self.fixture), self.policy)
        self.assertEqual(file_hash(PORTFOLIO), before_portfolio)
        self.assertEqual(file_hash(PROGRESS), before_progress)
        self.assertFalse(report["portfolio_mutation"])
        self.assertFalse(report["operational_counter_mutation"])

    def test_fixture_report_has_separate_origin_counts_and_zero_maturity(self):
        report, ledger = build_report(copy.deepcopy(self.fixture), self.policy)
        self.assertEqual(report["run_counts"]["SCHEDULED_GENUINE"], 0)
        self.assertEqual(report["run_counts"]["MANUAL"], 1)
        self.assertEqual(report["run_counts"]["REPLAY"], 1)
        self.assertEqual(report["run_counts"]["TEST_ONLY"], 1)
        self.assertEqual(report["run_counts"]["SHADOW_COUNTERFACTUAL"], 1)
        self.assertEqual(report["maturity_eligible_count"], 0)
        self.assertTrue(validate_ledger_chain(ledger))

    def test_report_ledger_and_run_schemas(self):
        report, ledger = build_report(copy.deepcopy(self.fixture), self.policy)
        self.assertEqual(validate_instance(report, REPORT_SCHEMA), [])
        self.assertEqual(validate_instance(ledger, LEDGER_SCHEMA), [])
        for record in ledger["entries"]:
            self.assertEqual(validate_instance(record, RUN_SCHEMA), [])
        self.assertEqual(validate_instance(report["outcome_ledger"], OUTCOME_LEDGER_SCHEMA), [])

    def test_live_empty_ledgers_cohort_policy_and_findings_validate(self):
        self.assertEqual(validate_instance(load_json(ROOT / "workspace/state/continuous_improvement/unified_run_ledger.json"), LEDGER_SCHEMA), [])
        self.assertEqual(validate_instance(load_json(ROOT / "workspace/state/continuous_improvement/forward_outcome_ledger.json"), OUTCOME_LEDGER_SCHEMA), [])
        self.assertEqual(validate_instance(load_json(ROOT / "workspace/state/continuous_improvement/improvement_analytics_cohort.json"), COHORT_SCHEMA), [])
        self.assertEqual(validate_instance(self.policy, POLICY_SCHEMA), [])
        report, _ = build_report(copy.deepcopy(self.fixture), self.policy)
        self.assertTrue(report["improvement_findings"])
        for finding in report["improvement_findings"]:
            self.assertEqual(validate_instance(finding, FINDING_SCHEMA), [])

    def test_analytics_cohort_fingerprint_detects_sidecar_semantic_change(self):
        cohort = load_json(ROOT / "workspace/state/continuous_improvement/improvement_analytics_cohort.json")
        result = compute_analytics_semantic_fingerprint({
            "sidecar": ROOT / "manage-us-stock-strategy/scripts/continuous_improvement_sidecar.py",
            "policy": ROOT / "workspace/policies/continuous_improvement_policy.json",
            "run_record_schema": ROOT / "manage-us-stock-strategy/schemas/continuous-improvement-run-record.schema.json",
            "run_ledger_schema": ROOT / "manage-us-stock-strategy/schemas/unified-run-ledger.schema.json",
            "outcome_schema": ROOT / "manage-us-stock-strategy/schemas/forward-outcome-artifact.schema.json",
            "outcome_ledger_schema": ROOT / "manage-us-stock-strategy/schemas/forward-outcome-ledger.schema.json",
            "report_schema": ROOT / "manage-us-stock-strategy/schemas/continuous-improvement-report.schema.json",
        })
        self.assertNotEqual(cohort["semantic_fingerprint"], result["semantic_fingerprint"])
        self.assertEqual(cohort["semantic_fingerprint_algorithm"], result["algorithm"])
        self.assertNotEqual(
            cohort["semantic_input_hashes"]["sidecar"],
            result["normalized_input_hashes"]["sidecar"],
        )
        unchanged_inputs = {
            key: value for key, value in cohort["semantic_input_hashes"].items()
            if key != "sidecar"
        }
        self.assertEqual(
            unchanged_inputs,
            {
                key: value for key, value in result["normalized_input_hashes"].items()
                if key != "sidecar"
            },
        )

    def test_order_and_quantity_authority_remain_disabled(self):
        report, ledger = build_report(copy.deepcopy(self.fixture), self.policy)
        self.assertFalse(report["order_authority"])
        self.assertEqual(report["quantity_authority"], "none")
        self.assertIsNone(report["execution_quantity"])
        self.assertTrue(all(item["order_authority"] is False for item in ledger["entries"]))
        self.assertEqual(report["live_api_calls"], 0)
        self.assertEqual(report["analytics_engine_version"], ANALYTICS_ENGINE_VERSION)
        self.assertEqual(report["metric_definition_version"], METRIC_DEFINITION_VERSION)

    def test_shadow_fill_namespace_cannot_update_broker_truth(self):
        link = build_execution_analytics_link(
            artifact_id="shadow-fill-test-only", artifact_type="SHADOW_FILL",
            event_namespace="SHADOW_SIMULATION_EVENT", source_hash="a" * 64,
        )
        self.assertFalse(link["broker_truth_mutation"])
        self.assertFalse(link["maturity_eligible"])
        self.assertEqual(validate_instance(link, EXECUTION_LINK_SCHEMA), [])
        with self.assertRaisesRegex(ValueError, "SHADOW_EVENT_NAMESPACE_VIOLATION"):
            build_execution_analytics_link(
                artifact_id="bad", artifact_type="SHADOW_FILL",
                event_namespace="ACTUAL_BROKER_EVENT", source_hash="b" * 64,
            )

    def test_shadow_fill_cannot_be_consumed_as_actual_fill(self):
        link = build_execution_analytics_link(
            artifact_id="shadow-fill", artifact_type="SHADOW_FILL",
            event_namespace="SHADOW_SIMULATION_EVENT", source_hash="c" * 64,
        )
        with self.assertRaisesRegex(ValueError, "ANALYTICS_AUTHORITY_FIREWALL_VIOLATION"):
            assert_counter_authority_firewall({**link, "broker_truth_mutation": True})


if __name__ == "__main__":
    unittest.main()
