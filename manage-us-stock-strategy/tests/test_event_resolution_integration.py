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

from event_resolution_engine import (  # noqa: E402
    MISSING_REASONS,
    resolve_event_bundle,
    resolution_to_event_readiness,
    validate_requirement_matrix,
    validate_source_registry,
)
from portfolio_reallocation_shadow import (  # noqa: E402
    OPTIMIZER_INPUTS,
    build_capital_reallocation_shadow,
    evaluate_holding_decision,
)
from validation_common import load_json, validate_instance  # noqa: E402


MATRIX_PATH = ROOT / "workspace" / "policies" / "event_required_category_matrix.json"
REGISTRY_PATH = ROOT / "workspace" / "policies" / "event_source_authority_registry.json"
POLICY_PATH = ROOT / "workspace" / "policies" / "portfolio_reallocation_shadow_policy.json"
PORTFOLIO_PATH = ROOT / "stock-strategy-system" / "portfolio_state.json"


def verified(source_type: str = "ETF_SPONSOR_NOTICE") -> dict:
    return {
        "coverage_status": "VERIFIED",
        "source": "https://example.invalid/official",
        "source_type": source_type,
        "observed_at": "2026-08-14T20:10:00Z",
        "effective_at": "2026-08-14T20:10:00Z",
        "freshness_status": "CURRENT",
        "conflict_status": "NO_CONFLICT_OBSERVED",
        "identity_status": "VERIFIED",
        "event_effect": "CONTEXT_ONLY",
        "source_hash": "a" * 64,
    }


def holding(ticker: str, event: str = "EVENT_STALE") -> dict:
    value = {
        "ticker": ticker,
        "current_broker_holding": {"SOXL": 75, "MVLL": 396, "NBIS": 15}[ticker],
        "current_average_cost": {"SOXL": 123.3251, "MVLL": 41.7791, "NBIS": 215.0}[ticker],
        "current_canonical_price": {"SOXL": 144.95, "MVLL": 27.69, "NBIS": 277.68}[ticker],
        "hard_risk_status": "NO_BREACH", "hard_risk_exit_authorized": False,
        "thesis_status": "VALID", "thesis_invalidation_validated": False,
        "thesis_invalidation_event_verified": False,
        "event_readiness_status": event,
        "risk_trim_status": "NOT_TRIGGERED", "concentration_trim_status": "NOT_TRIGGERED",
        "technical_trim_status": "NOT_TRIGGERED", "valuation_trim_status": "NOT_TRIGGERED",
        "profit_protection_policy_result": "NOT_TRIGGERED", "time_stop_status": "NOT_TRIGGERED",
        "opportunity_cost_status": "NO_ROTATION", "valuation_add_status": "UNSUPPORTED",
        "technical_add_status": "WATCH", "portfolio_fit_status": "FITS", "add_review_requested": False,
        "unrealized_return_status": "LOSS", "trend_status": "WEAKENING", "volume_health_status": "UNKNOWN",
        "price_authority_status": "KIWOOM_VALID", "volume_authority_status": "KIWOOM_VALID_SCOPED",
        "technical_condition_status": "WATCH", "broker_visibility_status": "BROKER_READ_ONLY_OPEN_ORDERS_UNKNOWN",
        "capital_availability_status": "VERIFIED_USD_63_69", "valuation_condition": "UNCLASSIFIED",
    }
    if ticker == "MVLL":
        value["technical_condition_status"] = "RVOL20_NOT_MET"
        value["technical_condition_decision_class"] = "EMA10_RECLAIM_RVOL20"
    return value


def degraded_context(rows: list[dict], candidates: list[dict] | None = None) -> dict:
    return {
        "validation_mode": "MANUAL_READ_ONLY",
        "completed_bar_finalization_status": "KIWOOM_COMPLETED_BAR_FINALIZED",
        "event_refresh_status": "POST_CLOSE_EVENT_RESOLUTION_COMPLETED",
        "event_resolution_status": "UNRESOLVED_ACTION_BLOCKING",
        "holding_compile_mode": "DEGRADED_EVENT_SCOPED",
        "event_bundle_hash": "e" * 64,
        "decision_as_of": "2026-08-15T02:14:17Z",
        "market_data_cutoff": "2026-08-14T20:00:00Z",
        "event_cutoff": "2026-08-14T20:00:00Z",
        "broker_cutoff": "2026-08-14T19:59:00Z",
        "candidate_cutoff": "2026-08-14T20:00:00Z",
        "evidence_timestamps": ["2026-08-14T20:00:00Z"],
        "portfolio_decision_semantic_cohort": "portfolio-decision-32fb4351fc727f7e",
        "portfolio_reallocation_cycle_id": "manual-replay-2026-08-14",
        "canonical_positive_holding_tickers": [row["ticker"] for row in rows],
        "prior_cycle_ids": [], "holdings": rows,
        "portfolio_positions": [{"ticker": row["ticker"], "market_value_usd": row["current_broker_holding"] * row["current_canonical_price"]} for row in rows],
        "opportunity_candidates": candidates or [],
        "verified_actual_cash_usd": 63.69, "capital_availability_status": "VERIFIED_USD_63_69",
        "optimizer_input_status": {key: ("AVAILABLE" if key in {"technical_setup", "event_readiness", "position_concentration", "cash_buffer"} else "UNAVAILABLE") for key in OPTIMIZER_INPUTS},
        "rotation_justification": None, "order_authority": False,
    }


class EventResolutionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix, cls.registry, cls.policy = load_json(MATRIX_PATH), load_json(REGISTRY_PATH), load_json(POLICY_PATH)

    def test_event_policies_and_schemas_validate(self):
        self.assertEqual(validate_requirement_matrix(self.matrix), [])
        self.assertEqual(validate_source_registry(self.registry), [])
        self.assertEqual(validate_instance(self.matrix, SCHEMAS / "event-required-category-matrix.schema.json"), [])
        self.assertEqual(validate_instance(self.registry, SCHEMAS / "event-source-authority-registry.schema.json"), [])

    def test_missing_reason_vocabulary_is_explicit(self):
        for value in ("NOT_YET_PUBLISHED", "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF", "SOURCE_UNAVAILABLE", "PARSER_FAILED", "CATEGORY_NOT_CHECKED", "UNRESOLVED"):
            self.assertIn(value, MISSING_REASONS)

    def test_source_failure_cannot_become_no_new_disclosure(self):
        bad = verified(); bad.update({"coverage_status": "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF", "missing_reason": "SOURCE_UNAVAILABLE"})
        result = resolve_event_bundle(ticker="SOXL", instrument_identity={"ticker": "SOXL"}, decision_as_of="2026-08-15T00:00:00Z", evidence_by_category={"sponsor_notice": bad}, requirement_matrix=self.matrix, source_registry=self.registry)
        row = next(x for x in result["categories"] if x["event_category"] == "sponsor_notice")
        self.assertIn("MISSING_REASON_CANNOT_PROVE_NO_NEW_DISCLOSURE", row["errors"])
        self.assertEqual(row["coverage_status"], "INVALID")

    def test_targeted_resolution_calls_only_missing_category(self):
        evidence = {category: verified() for category in self.matrix["ticker_requirements"]["NBIS"]["categories"]}
        evidence["dilution"] = {"coverage_status": "SOURCE_UNAVAILABLE", "missing_reason": "SOURCE_UNAVAILABLE"}
        calls = []
        def refresh(ticker, category, cutoff):
            calls.append((ticker, category, cutoff)); return verified("SEC_FILING")
        result = resolve_event_bundle(ticker="NBIS", instrument_identity={"ticker": "NBIS"}, decision_as_of="2026-08-15T00:00:00Z", evidence_by_category=evidence, requirement_matrix=self.matrix, source_registry=self.registry, refresh_callback=refresh, maximum_attempts=2)
        self.assertEqual(calls, [("NBIS", "dilution", "2026-08-15T00:00:00Z")])
        self.assertEqual(result["resolution_status"], "RESOLVED")
        self.assertEqual(result["holding_compile_mode"], "FULL")

    def test_secondary_detection_requires_primary_confirmation(self):
        item = verified("MAJOR_FINANCIAL_PRESS"); item["material_event_detected"] = True
        result = resolve_event_bundle(ticker="NBIS", instrument_identity={"ticker": "NBIS"}, decision_as_of="2026-08-15T00:00:00Z", evidence_by_category={"earnings": item}, requirement_matrix=self.matrix, source_registry=self.registry)
        row = next(x for x in result["categories"] if x["event_category"] == "earnings")
        self.assertIn("PRIMARY_CONFIRMATION_REQUIRED", row["errors"])
        self.assertNotEqual(row["coverage_status"], "VERIFIED")

    def test_product_and_underlying_event_scopes_are_separate(self):
        scope = self.matrix["ticker_requirements"]["MVLL"]
        self.assertEqual(scope["supplemental_underlying"], "MRVL")
        self.assertFalse(self.matrix["product_events_may_be_replaced_by_underlying_events"])
        self.assertEqual(scope["categories"]["underlying_issuer_context"]["requirement"], "OPTIONAL")

    def test_degraded_event_compile_evaluates_all_four_cases(self):
        report = build_capital_reallocation_shadow(degraded_context([holding("SOXL"), holding("MVLL"), holding("NBIS")]), self.policy)
        self.assertEqual(report["holding_compile_mode"], "DEGRADED_EVENT_SCOPED")
        self.assertEqual(report["post_close_ordering_status"], "PASS")
        for row in report["holding_decisions"]:
            for name in ("ADD_CASE", "HOLD_CASE", "TRIM_CASE", "EXIT_CASE"):
                self.assertIn(name, row)
            self.assertEqual(row["selected_holding_action"], "HOLD_REVIEW_REQUIRED")

    def test_stale_and_source_unavailable_do_not_globally_skip(self):
        for state in ("EVENT_STALE", "EVENT_SOURCE_UNAVAILABLE", "EVENT_REFRESH_FAILED"):
            result = evaluate_holding_decision(holding("SOXL", state), self.policy, holding_compile_mode="DEGRADED_EVENT_SCOPED", event_resolution_status="UNRESOLVED_ACTION_BLOCKING")
            self.assertEqual(result["HOLD_CASE"]["status"], "REVIEW_REQUIRED")
            self.assertIn(result["TRIM_CASE"]["status"], {"PASS", "NOT_MET"})
            self.assertIn(result["EXIT_CASE"]["status"], {"PASS", "NOT_MET", "REVIEW_REQUIRED"})

    def test_event_incomplete_profit_trim_remains_evaluable(self):
        row = holding("SOXL", "EVENT_SOURCE_UNAVAILABLE"); row["profit_protection_policy_result"] = "TRIGGERED"
        self.assertEqual(evaluate_holding_decision(row, self.policy)["selected_holding_action"], "TRIM_PROFIT")

    def test_hard_risk_exit_wins_with_event_unavailable(self):
        row = holding("SOXL", "EVENT_SOURCE_UNAVAILABLE"); row.update({"hard_risk_status": "BREACH", "hard_risk_exit_authorized": True})
        self.assertEqual(evaluate_holding_decision(row, self.policy)["selected_holding_action"], "EXIT_HARD_STOP")

    def test_thesis_exit_is_not_fabricated_without_event_evidence(self):
        row = holding("NBIS"); row.update({"thesis_status": "INVALIDATED", "thesis_invalidation_validated": True, "thesis_invalidation_event_verified": False})
        result = evaluate_holding_decision(row, self.policy)
        self.assertNotEqual(result["selected_holding_action"], "EXIT_THESIS")

    def test_degraded_valid_trim_runs_reallocation_shadow(self):
        row = holding("SOXL"); row.update({"profit_protection_policy_result": "TRIGGERED", "hypothetical_trim_ratio": 0.25, "hypothetical_trim_ratio_source": "EXPLICIT_TEST_SCENARIO"})
        value = degraded_context([row]); value["validation_mode"] = "TEST_ONLY"
        report = build_capital_reallocation_shadow(value, self.policy)
        self.assertEqual(report["capital_reallocation_degraded_path_status"], "EVALUATED")
        self.assertGreater(report["expected_sale_proceeds_usd"], 0)

    def test_degraded_without_sale_is_not_applicable_not_not_run(self):
        report = build_capital_reallocation_shadow(degraded_context([holding("NBIS")]), self.policy)
        self.assertEqual(report["capital_reallocation_degraded_path_status"], "NOT_APPLICABLE")

    def test_keep_cash_fallback_is_not_optimizer_selected_cash(self):
        candidate = {"ticker": "BE", "type": "NEW_POSITION", "event_readiness_status": "EVENT_PARTIAL_BUY_BLOCKING", "hard_gate_status": "PASS", "risk_gate_status": "PASS", "portfolio_fit_status": "PASS", "relative_opportunity_rank": 1}
        report = build_capital_reallocation_shadow(degraded_context([holding("SOXL")], [candidate]), self.policy)
        self.assertEqual(report["best_shadow_decision"], "KEEP_CASH")
        self.assertEqual(report["keep_cash_state"], "SAFE_FALLBACK_NO_NEW_CAPITAL_DEPLOYMENT")
        self.assertNotEqual(report["keep_cash_state"], "OPTIMIZED_KEEP_CASH")

    def test_mvll_rvol_not_met_is_add_setup_local(self):
        result = evaluate_holding_decision(holding("MVLL"), self.policy)
        self.assertIn("EMA10_RECLAIM_RVOL20_CONDITION_NOT_MET", result["ADD_CASE"]["reason_codes"])
        self.assertNotIn("EMA10_RECLAIM_RVOL20_CONDITION_NOT_MET", result["HOLD_CASE"]["reason_codes"])
        self.assertNotIn("EMA10_RECLAIM_RVOL20_CONDITION_NOT_MET", result["TRIM_CASE"]["reason_codes"])
        self.assertNotIn("EMA10_RECLAIM_RVOL20_CONDITION_NOT_MET", result["EXIT_CASE"]["reason_codes"])

    def test_mvll_rvol_scope_must_be_exact(self):
        row = holding("MVLL"); row["technical_condition_decision_class"] = "GLOBAL"
        with self.assertRaisesRegex(ValueError, "MVLL_RVOL20_SCOPE_UNVERIFIED"):
            evaluate_holding_decision(row, self.policy)

    def test_expected_proceeds_never_become_broker_cash(self):
        row = holding("SOXL"); row.update({"profit_protection_policy_result": "TRIGGERED", "hypothetical_trim_ratio": 0.5, "hypothetical_trim_ratio_source": "EXPLICIT_TEST_SCENARIO"})
        value = degraded_context([row]); value["validation_mode"] = "TEST_ONLY"
        report = build_capital_reallocation_shadow(value, self.policy)
        self.assertEqual(report["verified_orderable_cash_from_expected_proceeds_usd"], 0)
        self.assertEqual(report["funding_authority"], "VERIFIED_ACTUAL_CASH_ONLY")

    def test_quantity_authority_and_portfolio_are_immutable(self):
        before = hashlib.sha256(PORTFOLIO_PATH.read_bytes()).hexdigest()
        report = build_capital_reallocation_shadow(degraded_context([holding("SOXL")]), self.policy)
        self.assertEqual(hashlib.sha256(PORTFOLIO_PATH.read_bytes()).hexdigest(), before)
        self.assertIsNone(report["execution_quantity"])
        self.assertEqual(report["quantity_authority"], "none")
        self.assertFalse(report["order_authority"])

    def test_resolution_result_schema_and_readiness_mapping(self):
        evidence = {category: verified() for category in self.matrix["ticker_requirements"]["SOXL"]["categories"]}
        result = resolve_event_bundle(ticker="SOXL", instrument_identity={"ticker": "SOXL"}, decision_as_of="2026-08-15T00:00:00Z", evidence_by_category=evidence, requirement_matrix=self.matrix, source_registry=self.registry)
        self.assertEqual(validate_instance(result, SCHEMAS / "event-resolution-result.schema.json"), [])
        self.assertEqual(resolution_to_event_readiness(result), "EVENT_COMPLETE")
        self.assertEqual(result["network_order_calls"], 0)


if __name__ == "__main__":
    unittest.main()
