from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
sys.path.insert(0, str(SCRIPTS))

from portfolio_reallocation_shadow import (  # noqa: E402
    EVENT_ACTIONS,
    EVENT_STATES,
    OPTIMIZER_INPUTS,
    TEN_AXES,
    build_capital_reallocation_shadow,
    evaluate_event_actionability,
    evaluate_holding_decision,
    normalize_material_categories,
    validate_post_close_ordering,
    validate_output_path,
    validate_policy,
    validate_report,
)
from judge_portfolio_reallocation_shadow import GATE_NAMES, judge  # noqa: E402
from validation_common import canonical_hash, load_json, validate_instance  # noqa: E402


POLICY_PATH = ROOT / "workspace" / "policies" / "portfolio_reallocation_shadow_policy.json"
CONTEXT_SCHEMA = SCHEMAS / "portfolio-reallocation-context.schema.json"
REPORT_SCHEMA = SCHEMAS / "portfolio-reallocation-shadow.schema.json"
COHORT_SCHEMA = SCHEMAS / "portfolio-decision-cohort.schema.json"
COHORT_PATH = ROOT / "workspace" / "state" / "portfolio_decision_cohort.json"
JUDGE_SCHEMA = SCHEMAS / "portfolio-reallocation-judge.schema.json"
PORTFOLIO_PATH = ROOT / "stock-strategy-system" / "portfolio_state.json"


def holding(ticker: str = "SOXL") -> dict:
    return {
        "ticker": ticker,
        "current_broker_holding": 10,
        "current_average_cost": 100.0,
        "current_canonical_price": 120.0,
        "hard_risk_status": "NO_BREACH",
        "hard_risk_exit_authorized": False,
        "thesis_status": "VALID",
        "thesis_invalidation_validated": False,
        "event_readiness_status": "EVENT_COMPLETE",
        "risk_trim_status": "NOT_TRIGGERED",
        "concentration_trim_status": "NOT_TRIGGERED",
        "technical_trim_status": "NOT_TRIGGERED",
        "valuation_trim_status": "NOT_TRIGGERED",
        "profit_protection_policy_result": "NOT_TRIGGERED",
        "time_stop_status": "NOT_TRIGGERED",
        "opportunity_cost_status": "NO_ROTATION",
        "valuation_add_status": "UNSUPPORTED",
        "technical_add_status": "WATCH",
        "portfolio_fit_status": "FITS",
        "add_review_requested": False,
        "unrealized_return_status": "PROFIT",
        "trend_status": "STRONG",
        "volume_health_status": "HEALTHY",
        "price_authority_status": "KIWOOM_VALID",
        "volume_authority_status": "KIWOOM_VALID_SCOPED",
        "technical_condition_status": "WATCH",
        "broker_visibility_status": "BROKER_READ_ONLY_OPEN_ORDERS_UNKNOWN",
        "capital_availability_status": "VERIFIED_USD_63_69",
        "valuation_condition": "UNCLASSIFIED",
    }


def context(*, holdings: list[dict] | None = None, candidates: list[dict] | None = None) -> dict:
    rows = holdings or [holding("SOXL"), holding("MVLL"), holding("NBIS")]
    return {
        "validation_mode": "TEST_ONLY",
        "completed_bar_finalization_status": "KIWOOM_COMPLETED_BAR_FINALIZED",
        "event_refresh_status": "POST_CLOSE_EVENT_REFRESH_VALIDATED",
        "event_resolution_status": "RESOLVED",
        "holding_compile_mode": "FULL",
        "event_bundle_hash": "e" * 64,
        "decision_as_of": "2026-08-15T00:30:00Z",
        "market_data_cutoff": "2026-08-14T20:00:00Z",
        "event_cutoff": "2026-08-14T20:25:00Z",
        "broker_cutoff": "2026-08-14T20:20:00Z",
        "candidate_cutoff": "2026-08-14T20:25:00Z",
        "evidence_timestamps": ["2026-08-14T20:25:00Z"],
        "portfolio_decision_semantic_cohort": "portfolio-decision-32fb4351fc727f7e",
        "portfolio_reallocation_cycle_id": "cycle-2026-08-14",
        "canonical_positive_holding_tickers": [row["ticker"] for row in rows],
        "prior_cycle_ids": [],
        "holdings": rows,
        "portfolio_positions": [
            {"ticker": row["ticker"], "market_value_usd": row["current_broker_holding"] * row["current_canonical_price"],
             "effective_exposure_multiplier": {"SOXL": 3.0, "MVLL": 2.0}.get(row["ticker"], 1.0)}
            for row in rows
        ],
        "opportunity_candidates": candidates or [],
        "verified_actual_cash_usd": 63.69,
        "capital_availability_status": "VERIFIED_USD_63_69",
        "optimizer_input_status": {
            key: ("AVAILABLE" if key in {"technical_setup", "event_readiness", "position_concentration", "cash_buffer"} else "UNAVAILABLE")
            for key in OPTIMIZER_INPUTS
        },
        "rotation_justification": None,
        "order_authority": False,
    }


class PortfolioReallocationShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_json(POLICY_PATH)

    def test_event_state_action_matrix_is_complete_and_deterministic(self):
        self.assertEqual(validate_policy(self.policy), [])
        expected = self.policy["event_actionability"]
        self.assertEqual(set(expected), EVENT_STATES)
        for state in EVENT_STATES:
            self.assertEqual(set(expected[state]), EVENT_ACTIONS)
            for action in EVENT_ACTIONS:
                result = evaluate_event_actionability(state, action, self.policy)
                self.assertEqual(result["decision"], expected[state][action])

    def test_buy_and_add_fail_closed_when_event_readiness_is_insufficient(self):
        for state in ("EVENT_PARTIAL_BUY_BLOCKING", "EVENT_STALE", "EVENT_REFRESH_FAILED", "EVENT_SOURCE_UNAVAILABLE"):
            for action in ("NEW_BUY", "ADD"):
                self.assertFalse(evaluate_event_actionability(state, action, self.policy)["allowed"])

    def test_trim_is_not_blocked_by_event_incompleteness(self):
        for state in EVENT_STATES:
            self.assertTrue(evaluate_event_actionability(state, "TRIM", self.policy)["allowed"])

    def test_hard_risk_exit_overrides_incomplete_events(self):
        row = holding()
        row.update({"hard_risk_status": "BREACH", "hard_risk_exit_authorized": True,
                    "event_readiness_status": "EVENT_SOURCE_UNAVAILABLE"})
        result = evaluate_holding_decision(row, self.policy)
        self.assertEqual(result["selected_holding_action"], "EXIT_HARD_STOP")
        self.assertTrue(result["event_actionability"]["EXIT"]["allowed"])

    def test_thesis_invalidation_exit(self):
        row = holding()
        row.update({"thesis_status": "INVALIDATED", "thesis_invalidation_validated": True,
                    "thesis_invalidation_event_verified": True,
                    "event_readiness_status": "EVENT_REFRESH_FAILED"})
        self.assertEqual(evaluate_holding_decision(row, self.policy)["selected_holding_action"], "EXIT_THESIS")

    def test_profit_valuation_concentration_technical_and_time_trim_paths(self):
        paths = (
            ("profit_protection_policy_result", "TRIM_PROFIT"),
            ("valuation_trim_status", "TRIM_VALUATION"),
            ("technical_trim_status", "TRIM_TECHNICAL"),
            ("concentration_trim_status", "TRIM_CONCENTRATION"),
            ("time_stop_status", "TRIM_RISK"),
        )
        for key, action in paths:
            row = holding()
            row[key] = "TRIGGERED"
            self.assertEqual(evaluate_holding_decision(row, self.policy)["selected_holding_action"], action)

    def test_max_loss_not_breached_does_not_imply_hold_core(self):
        row = holding()
        row["thesis_status"] = "UNVERIFIED"
        result = evaluate_holding_decision(row, self.policy)
        self.assertEqual(result["HOLD_CASE"]["status"], "REVIEW_REQUIRED")
        self.assertIn("VALID_HOLD_THESIS_REQUIRED", result["HOLD_CASE"]["reason_codes"])

    def test_strong_profit_with_intact_trend_tightens_stop_instead_of_auto_sell(self):
        row = holding()
        row["unrealized_return_status"] = "LARGE_PROFIT"
        result = evaluate_holding_decision(row, self.policy)
        self.assertEqual(result["selected_holding_action"], "HOLD_TIGHTEN_STOP")
        self.assertIsNone(result["hypothetical_sell_quantity"])

    def test_all_four_cases_and_ten_axes_are_emitted_for_each_holding(self):
        report = build_capital_reallocation_shadow(context(), self.policy)
        for row in report["holding_decisions"]:
            for case in ("ADD_CASE", "HOLD_CASE", "TRIM_CASE", "EXIT_CASE"):
                self.assertIn(case, row)
            self.assertEqual(set(row["state_axes"]), set(TEN_AXES))
            self.assertEqual(row["decision_provenance"]["event_bundle_hash"], "e" * 64)
            self.assertGreaterEqual(row["decision_provenance"]["event_cutoff"], row["decision_provenance"]["market_data_cutoff"])

    def test_every_canonical_positive_holding_is_mandatory(self):
        value = context()
        value["holdings"] = value["holdings"][:-1]
        with self.assertRaisesRegex(ValueError, "CANONICAL_POSITIVE_HOLDING_SCOPE_MISMATCH"):
            build_capital_reallocation_shadow(value, self.policy)

    def test_hypothetical_proceeds_never_become_actual_or_orderable_cash(self):
        row = holding()
        row.update({"profit_protection_policy_result": "TRIGGERED", "hypothetical_trim_ratio": 0.5,
                    "hypothetical_trim_ratio_source": "EXPLICIT_TEST_SCENARIO"})
        report = build_capital_reallocation_shadow(context(holdings=[row]), self.policy)
        self.assertEqual(report["expected_sale_proceeds_usd"], 600.0)
        self.assertEqual(report["expected_sale_proceeds_status"], "SHADOW_ONLY")
        self.assertEqual(report["verified_actual_cash_usd"], 63.69)
        self.assertEqual(report["verified_orderable_cash_from_expected_proceeds_usd"], 0.0)
        self.assertEqual(report["hypothetical_cash_usd_after_sale"], 663.69)
        self.assertEqual(report["hypothetical_cash_status"], "SHADOW_ONLY")
        self.assertEqual(report["funding_authority"], "VERIFIED_ACTUAL_CASH_ONLY")
        self.assertFalse(report["expected_proceeds_may_fund_candidate"])

    def test_trim_without_approved_ratio_keeps_shadow_quantity_null(self):
        row = holding(); row["profit_protection_policy_result"] = "TRIGGERED"
        result = evaluate_holding_decision(row, self.policy)
        self.assertIsNone(result["hypothetical_sell_quantity"])
        self.assertEqual(result["shadow_ratio_status"], "SHADOW_RATIO_NOT_CONFIGURED")

    def test_test_only_ratio_cannot_enter_live_read_only_mode(self):
        row = holding()
        row.update({"profit_protection_policy_result": "TRIGGERED", "hypothetical_trim_ratio": 0.5,
                    "hypothetical_trim_ratio_source": "EXPLICIT_TEST_SCENARIO"})
        result = evaluate_holding_decision(row, self.policy, validation_mode="LIVE_READ_ONLY")
        self.assertIsNone(result["hypothetical_sell_quantity"])
        self.assertEqual(result["shadow_ratio_status"], "SHADOW_RATIO_NOT_CONFIGURED")

    def test_keep_cash_wins_when_candidates_fail_hard_or_event_gates(self):
        candidates = [
            {"ticker": "BE", "type": "NEW_POSITION", "event_readiness_status": "EVENT_PARTIAL_BUY_BLOCKING",
             "hard_gate_status": "PASS", "risk_gate_status": "PASS", "portfolio_fit_status": "PASS", "relative_opportunity_rank": 1},
            {"ticker": "NOW", "type": "NEW_POSITION", "event_readiness_status": "EVENT_COMPLETE",
             "hard_gate_status": "FAIL", "risk_gate_status": "PASS", "portfolio_fit_status": "PASS", "relative_opportunity_rank": 2},
        ]
        report = build_capital_reallocation_shadow(context(candidates=candidates), self.policy)
        self.assertEqual(report["best_shadow_decision"], "KEEP_CASH")
        self.assertFalse(report["candidate_comparison"][0]["eligible_for_shadow_comparison"])

    def test_existing_add_and_new_buy_comparison_remains_full_portfolio_review(self):
        candidates = [
            {"ticker": "NBIS", "type": "EXISTING_HOLDING_ADD", "event_readiness_status": "EVENT_COMPLETE",
             "hard_gate_status": "PASS", "risk_gate_status": "PASS", "portfolio_fit_status": "PASS", "relative_opportunity_rank": 1},
            {"ticker": "NOW", "type": "NEW_POSITION", "event_readiness_status": "EVENT_COMPLETE",
             "hard_gate_status": "PASS", "risk_gate_status": "PASS", "portfolio_fit_status": "PASS", "relative_opportunity_rank": 2},
        ]
        report = build_capital_reallocation_shadow(context(candidates=candidates), self.policy)
        self.assertEqual(report["best_shadow_decision"], "ADD_EXISTING_REVIEW")
        self.assertEqual(len(report["candidate_comparison"]), 2)
        self.assertTrue(all(row["execution_quantity"] is None for row in report["candidate_comparison"]))

    def test_portfolio_risk_before_after_and_risk_kernel_separation(self):
        row = holding()
        row.update({"hard_risk_status": "BREACH", "hard_risk_exit_authorized": True})
        report = build_capital_reallocation_shadow(context(holdings=[row]), self.policy)
        self.assertNotEqual(report["portfolio_risk_before"], report["portfolio_risk_after"])
        self.assertEqual(report["sell_risk_decision"], "RISK_REVIEW_REQUIRED")
        self.assertFalse(report["portfolio_risk_after"]["numeric_score_authority"])
        self.assertEqual(set(report["optimizer_input_status"]), set(OPTIMIZER_INPUTS))

    def test_same_cycle_duplicate_is_suppressed(self):
        value = context()
        value["prior_cycle_ids"] = [value["portfolio_reallocation_cycle_id"]]
        report = build_capital_reallocation_shadow(value, self.policy)
        self.assertTrue(report["same_cycle_duplicate_suppressed"])
        self.assertEqual(report["best_shadow_decision"], "KEEP_CASH")

    def test_lookahead_evidence_is_rejected(self):
        errors = validate_post_close_ordering(
            decision_as_of="2026-08-15T00:30:00Z", market_data_cutoff="2026-08-14T20:00:00Z",
            event_cutoff="2026-08-14T20:25:00Z", broker_cutoff="2026-08-14T20:20:00Z",
            evidence_timestamps=["2026-08-15T00:31:00Z"],
            event_bundle_hash="e" * 64,
        )
        self.assertIn("LOOK_AHEAD_EVIDENCE_REJECTED", errors)

    def test_post_close_ordering_requires_finalized_bar_event_refresh_and_bundle_hash(self):
        errors = validate_post_close_ordering(
            decision_as_of="2026-08-15T00:30:00Z", market_data_cutoff="2026-08-14T20:00:00Z",
            event_cutoff="2026-08-14T20:25:00Z", broker_cutoff="2026-08-14T20:20:00Z",
            completed_bar_finalization_status="FINALIZATION_PENDING",
            event_refresh_status="FAILED", event_bundle_hash=None,
        )
        self.assertIn("COMPLETED_BAR_NOT_FINALIZED", errors)
        self.assertIn("POST_CLOSE_EVENT_REFRESH_NOT_VALIDATED", errors)
        self.assertIn("EVENT_BUNDLE_HASH_INVALID", errors)

    def test_material_categories_do_not_invent_no_event(self):
        normalized = normalize_material_categories({"earnings": "VERIFIED"}, self.policy)
        self.assertEqual(normalized["categories"], {"earnings": "VERIFIED"})
        self.assertTrue(normalized["valid"])
        self.assertNotIn("guidance", normalized["categories"])

    def test_future_partial_fill_schema_support_is_inert(self):
        self.assertIn("SELL_PARTIALLY_FILLED", self.policy["future_execution_states"])
        self.assertIn("BUY_PARTIALLY_FILLED", self.policy["future_execution_states"])
        self.assertFalse(self.policy["order_authority"])
        future = {
            "schema_version": "1.0", "future_state": "SELL_PARTIALLY_FILLED",
            "expected_sale_proceeds_status": "SHADOW_ONLY",
            "verified_orderable_cash_from_expected_proceeds_usd": 0,
            "quantity": None, "quantity_authority": "none", "order_authority": False,
            "network_send": False, "portfolio_mutation": False, "record_hash": "a" * 64,
        }
        self.assertEqual(validate_instance(future, SCHEMAS / "future-order-shadow.schema.json"), [])

    def test_context_report_and_cohort_schemas(self):
        value = context()
        self.assertEqual(validate_instance(value, CONTEXT_SCHEMA), [])
        report = build_capital_reallocation_shadow(value, self.policy)
        self.assertEqual(validate_report(report, REPORT_SCHEMA), [])
        self.assertEqual(validate_instance(load_json(COHORT_PATH), COHORT_SCHEMA), [])
        self.assertEqual(load_json(COHORT_PATH)["semantic_fingerprint"], canonical_hash(self.policy))

    def test_quantity_order_and_portfolio_immutability(self):
        before = hashlib.sha256(PORTFOLIO_PATH.read_bytes()).hexdigest()
        report = build_capital_reallocation_shadow(context(), self.policy)
        after = hashlib.sha256(PORTFOLIO_PATH.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertIsNone(report["execution_quantity"])
        self.assertEqual(report["quantity_authority"], "none")
        self.assertFalse(report["order_authority"])
        self.assertFalse(report["portfolio_mutation"])

    def test_output_path_cannot_alias_portfolio_or_escape_managed_outputs(self):
        with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_BE_UNDER_WORKSPACE_OUTPUTS"):
            validate_output_path(PORTFOLIO_PATH, repository_root=ROOT, protected=[PORTFOLIO_PATH])
        with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_BE_UNDER_WORKSPACE_OUTPUTS"):
            validate_output_path(ROOT / "outside.json", repository_root=ROOT, protected=[])
        managed = ROOT / "workspace" / "outputs" / "protected.json"
        with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_NOT_ALIAS_INPUT_OR_PROTECTED_STATE"):
            validate_output_path(managed, repository_root=ROOT, protected=[managed])

    def test_independent_judge_recomputes_all_required_gates(self):
        expected_hash = hashlib.sha256(PORTFOLIO_PATH.read_bytes()).hexdigest()
        scheduler_hash = "a" * 64
        result = judge(
            report=build_capital_reallocation_shadow(context(), self.policy),
            policy=self.policy,
            cohort=load_json(COHORT_PATH),
            report_schema=REPORT_SCHEMA,
            cohort_schema=COHORT_SCHEMA,
            portfolio_path=PORTFOLIO_PATH,
            expected_portfolio_hash=expected_hash,
            scheduler_hash_before=scheduler_hash,
            scheduler_hash_after=scheduler_hash,
            tests_passed=True,
            test_output_hash="b" * 64,
        )
        self.assertEqual(result["overall_status"], "CAPITAL_REALLOCATION_SHADOW_VERIFIED")
        self.assertEqual(set(result["gates"]), set(GATE_NAMES))
        self.assertTrue(all(value == "PASS" for value in result["gates"].values()))
        self.assertEqual(validate_instance(result, JUDGE_SCHEMA), [])


if __name__ == "__main__":
    unittest.main()
