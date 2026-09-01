#!/usr/bin/env python3
"""Offline safety and negative tests for Portfolio Decision Dashboard v1.0."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from portfolio_decision_dashboard import (  # noqa: E402
    ContractError,
    CURRENT_SESSION_CONTEXT_SCHEMA,
    DEFAULT_RISK_POLICY,
    MANUAL_EVIDENCE_SCHEMA,
    REQUEST_ACCOUNTING_SCHEMA,
    compile_dashboard,
    discover_historical_replay,
    implementation_provenance_paths,
    render_html,
    render_markdown,
    validate_plan,
    write_run,
)
from validation_common import load_json, validate_instance  # noqa: E402


MANUAL_TEST_PATH = ROOT / "manage-us-stock-strategy/tests/test_manual_portfolio_analysis.py"
_manual_spec = importlib.util.spec_from_file_location("dashboard_canonical_manual_fixture", MANUAL_TEST_PATH)
assert _manual_spec and _manual_spec.loader
_manual_module = importlib.util.module_from_spec(_manual_spec)
_manual_spec.loader.exec_module(_manual_module)


def evidence(
    *, market_phase: str = "REGULAR_COMPLETED", cash: float = 10_000.0,
    run_id: str = "manual-synthetic-grade-b", decision_as_of: str = "2026-08-21T22:00:00+00:00",
    holdings: dict[str, float] | None = None,
) -> dict:
    broker_holdings = holdings or {"MVLL": 100, "NBIS": 20, "SOXL": 20, "PGR": 0, "JPM": 0}
    costs = {"MVLL": 30.0, "NBIS": 90.0, "SOXL": 50.0, "PGR": 0.0, "JPM": 0.0}
    system = _manual_module.system_portfolio(
        {"MVLL": 99, "NBIS": 20, "SOXL": 20, "PGR": 0, "JPM": 0}, costs, cash,
    )
    case = _manual_module.ManualPortfolioAnalysisTest(methodName="runTest")
    case.setUpClass()
    case.setUp()
    try:
        value = case.build_report(
            portfolio=system, broker_holdings=broker_holdings, broker_costs=costs,
            orderable_cash=cash, manual_run_id=run_id, observed_at=decision_as_of,
            decision_as_of=decision_as_of, account_retrieved_at=decision_as_of,
            market_retrieved_at_by_operation={"oauth_health": decision_as_of, "market_quote": decision_as_of,
                                               "daily_chart": decision_as_of},
        )
    finally:
        case.tearDown()
    prices = {"MVLL": 20.0, "NBIS": 100.0, "SOXL": 40.0, "PGR": 200.0, "JPM": 100.0}
    for item in value["last_verified_finalized_bars"]:
        item["bar"]["price"] = prices[item["ticker"]]
    value["market_phase"] = market_phase
    value["current_session_finalization_status"] = "VERIFIED" if market_phase == "REGULAR_COMPLETED" else "NOT_VERIFIED"
    assert validate_instance(value, MANUAL_EVIDENCE_SCHEMA) == []
    return value


def plan(*, status: str = "CURRENT_APPROVED", include_priority: bool = True) -> dict:
    value = {
        "plan_id": "synthetic-plan-v1",
        "as_of": "2026-08-21T22:00:00+00:00",
        "plan_status": status,
        "evidence_binding": {
            "expected_run_id": "manual-synthetic-grade-b",
            "expected_decision_as_of": "2026-08-21T22:00:00+00:00",
        },
        "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET",
        "cash_target_pct": 61.5,
        "positions": [
            {"ticker": "MVLL", "action": "TRIM", "target_weight_pct": 5.0, "rationale": "leveraged concentration", "investment_horizon": "transition", "target_status": "APPROVED", "material_risk": "daily reset", "decision_change_triggers": ["risk cap changes"]},
            {"ticker": "NBIS", "action": "HOLD", "target_weight_pct": 13.5, "rationale": "hold reference", "investment_horizon": "long", "target_status": "APPROVED"},
            {"ticker": "SOXL", "action": "EXIT", "target_weight_pct": 0.0, "rationale": "reduce 3x exposure", "investment_horizon": "transition", "target_status": "APPROVED"},
            {"ticker": "PGR", "action": "ADD", "target_weight_pct": 10.0, "rationale": "diversifier", "investment_horizon": "long", "target_status": "APPROVED"},
            {"ticker": "JPM", "action": "ADD", "target_weight_pct": 10.0, "rationale": "diversifier", "investment_horizon": "long", "target_status": "APPROVED"},
        ],
        "material_unknowns": [],
        "decision_change_triggers": ["fresh broker snapshot"],
    }
    if include_priority:
        value["buy_priority"] = ["PGR", "JPM"]
    return value


def post_sell_evidence(*, cash: float = 13_000.0) -> dict:
    value = evidence(
        cash=cash, run_id="manual-post-sell-grade-b",
        decision_as_of="2026-08-21T22:05:00+00:00",
        holdings={"MVLL": 37, "NBIS": 20, "SOXL": 0, "PGR": 0, "JPM": 0},
    )
    value["broker_diff_status"] = "MATCH"
    return value


def post_sell_plan(*, cash_priority: bool = True) -> dict:
    value = plan(include_priority=cash_priority)
    value["post_sell_refresh"] = {
        "prior_run_id": value["evidence_binding"]["expected_run_id"],
        "prior_decision_as_of": value["evidence_binding"]["expected_decision_as_of"],
    }
    return value


def evidence_raw_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def current_context(value: dict, source_sha256: str | None = None) -> dict:
    return {
        "context_type": "PORTFOLIO_DECISION_CURRENT_SESSION_CONTEXT",
        "context_version": "1.0",
        "context_generated_at": value["decision_as_of"],
        "expected_evidence_run_id": value["manual_run_id"],
        "expected_evidence_sha256": source_sha256 or hashlib.sha256(evidence_raw_bytes(value)).hexdigest(),
        "expected_evidence_decision_as_of": value["decision_as_of"],
        "expected_completed_us_session": value["expected_completed_us_session"],
        "market_phase": value["market_phase"],
        "session_authority_market_phase": value["session_authority_market_phase"],
        "primary_listing_operating_mic": "XNAS",
        "calendar_policy_identity": value["calendar_policy_identity"],
        "calendar_hash": value["calendar_hash"],
        "session_activation_cohort_id": value["session_activation_cohort_id"],
        "context_status": "VERIFIED_CURRENT_SESSION",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }


def verified_request_accounting(value: dict, source_sha256: str | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "source_type": "KIWOOM_MANUAL_PORTFOLIO_ANALYSIS",
        "source_run_id": value["manual_run_id"],
        "source_artifact_sha256": source_sha256 or hashlib.sha256(evidence_raw_bytes(value)).hexdigest(),
        "generated_at": value["decision_as_of"],
        "verification_status": "VERIFIED_EXACT",
        "http_request_count": 5,
        "successful_request_count": 5,
        "failed_request_count": 0,
        "retry_count": 0,
        "operation_counts": {
            "account_holdings_read": 1, "account_deposit_read": 1,
            "oauth_health": 1, "market_quote": 1, "daily_chart": 1,
        },
        "endpoint_counts": {"account": 2, "oauth": 1, "quote": 1, "chart": 1},
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }


def canonical_runtime_resolver(value: dict):
    def resolve(*_args, **_kwargs):
        return SimpleNamespace(
            authority_status="VERIFIED",
            expected_completed_session=SimpleNamespace(session_date=value["expected_completed_us_session"]),
            market_phase=value["session_authority_market_phase"],
            calendar_policy_identity=value["calendar_policy_identity"],
            calendar_hash=value["calendar_hash"],
            activation_cohort_id=value["session_activation_cohort_id"],
        )
    return resolve


class PortfolioDecisionDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_json(DEFAULT_RISK_POLICY)

    def compile(self, evidence_value=None, plan_value=None, **kwargs):
        source = evidence_value if evidence_value is not None else evidence()
        source_sha256 = hashlib.sha256(evidence_raw_bytes(source)).hexdigest()
        kwargs.setdefault("evidence_sha256", source_sha256)
        kwargs.setdefault("current_session_context", current_context(source, source_sha256))
        kwargs.setdefault("current_session_authority_resolver", canonical_runtime_resolver(source))
        return compile_dashboard(
            source, plan_value if plan_value is not None else plan(), self.policy,
            run_id="synthetic-run", generated_at=source["decision_as_of"], **kwargs,
        )

    def test_stage1_integer_floor_and_stage2_firewall(self):
        report, validation = self.compile()
        rows = {row["ticker"]: row for row in report["stage1"]["sell_advisories"]}
        self.assertEqual(rows["MVLL"]["target_shares_reference"], 37)
        self.assertEqual(rows["MVLL"]["calculated_sell_shares"], 63)
        self.assertEqual(rows["SOXL"]["calculated_sell_shares"], 20)
        self.assertEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED")
        self.assertTrue(validation["invariants"]["stage2_firewall"])

    def test_missing_holdings_fails_closed(self):
        source = evidence()
        source["broker_observed_state"]["holdings"] = []
        report, _ = self.compile(source)
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("MISSING_HOLDINGS", report["evidence"]["issues"])

    def test_missing_current_cash_blocks_nav(self):
        source = evidence()
        del source["broker_observed_state"]["cash"]["foreign_currency_deposit"]
        report, _ = self.compile(source)
        self.assertIsNone(report["portfolio"]["nav_usd"]["value"])
        self.assertIn("MISSING_CURRENT_CASH", report["evidence"]["issues"])

    def test_missing_orderable_cash_blocks_post_sell_stage2(self):
        source = post_sell_evidence()
        source["orderable_cash_status"] = "NOT_VERIFIED"
        source["verified_orderable_cash_usd"] = None
        report, _ = self.compile(source, post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("VERIFIED_ORDERABLE_CASH_REQUIRED", report["stage2"]["blockers"])

    def test_missing_price_blocks_only_affected_candidate(self):
        source = evidence()
        source["last_verified_finalized_bars"] = [item for item in source["last_verified_finalized_bars"] if item["ticker"] != "PGR"]
        report, _ = self.compile(source)
        pgr = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "PGR")
        self.assertIn("BLOCKED_CANONICAL_PRICE_REQUIRED", pgr["blockers"])
        self.assertIsNotNone(report["portfolio"]["nav_usd"]["value"])

    def test_duplicate_ticker_in_plan_rejected(self):
        value = plan()
        value["positions"].append(copy.deepcopy(value["positions"][0]))
        self.assertTrue(any("DUPLICATE_TICKER" in item for item in validate_plan(value)))
        with self.assertRaises(ContractError):
            self.compile(plan_value=value)

    def test_duplicate_broker_ticker_visible_and_blocked(self):
        source = evidence()
        source["broker_observed_state"]["holdings"].append(copy.deepcopy(source["broker_observed_state"]["holdings"][0]))
        report, _ = self.compile(source)
        self.assertTrue(any("DUPLICATE_BROKER_TICKER" in item for item in report["evidence"]["issues"]))

    def test_broker_system_mismatch_keeps_broker_canonical(self):
        report, _ = self.compile()
        mvll = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "MVLL")
        self.assertEqual(mvll["current_quantity"]["value"], 100)
        self.assertIn("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL", report["evidence"]["warnings"])

    def test_non_regular_market_is_provisional(self):
        report, _ = self.compile(evidence(market_phase="MARKET_CLOSED"))
        self.assertEqual(report["stage1"]["status"], "PROVISIONAL")
        self.assertEqual(report["evidence"]["current_freshness"], "CURRENT_SESSION_CONTEXT_VERIFIED")

    def test_historical_plan_is_replay_only(self):
        report, _ = self.compile(plan_value=plan(status="HISTORICAL"), compile_mode="HISTORICAL_REPLAY")
        self.assertEqual(report["stage1"]["status"], "REPLAY_ONLY")
        self.assertEqual(report["stage2"]["status"], "REPLAY_ONLY")
        self.assertEqual(report["evidence"]["current_freshness"], "HISTORICAL_REPLAY")
        self.assertEqual(report["evidence"]["portfolio_evidence_grade_display"], "GRADE_B_AT_ARTIFACT_TIME")

    def test_input_order_authority_fails_closed(self):
        source = evidence()
        source["order_authority"] = True
        report, _ = self.compile(source)
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("INPUT_ORDER_AUTHORITY_NOT_FALSE", report["evidence"]["issues"])

    def test_missing_target_weight_blocks_ticker_without_invention(self):
        value = plan()
        del value["positions"][3]["target_weight_pct"]
        report, _ = self.compile(plan_value=value)
        pgr = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "PGR")
        self.assertIn("BLOCKED_TARGET_WEIGHT_REQUIRED", pgr["blockers"])
        self.assertIsNone(pgr["target_shares_reference"]["value"])

    def test_target_weight_outside_range_rejected(self):
        value = plan()
        del value["cash_target_pct"]
        value["positions"][0]["target_weight_pct"] = 101.0
        with self.assertRaises(ContractError):
            self.compile(plan_value=value)

    def test_deadband_prefers_no_trade(self):
        source = evidence(cash=900.0)
        source["broker_observed_state"]["holdings"] = [{"ticker": "PGR", "held_quantity": 1, "average_cost": 90.0}]
        source["last_verified_finalized_bars"] = [
            item for item in source["last_verified_finalized_bars"] if item["ticker"] == "PGR"
        ]
        source["last_verified_finalized_bars"][0]["bar"]["price"] = 100.0
        value = {
            "plan_id": "deadband", "as_of": "2026-08-21T22:00:00+00:00", "plan_status": "CURRENT_APPROVED",
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 89.0,
            "evidence_binding": {"expected_run_id": "manual-synthetic-grade-b", "expected_decision_as_of": "2026-08-21T22:00:00+00:00"},
            "positions": [{"ticker": "PGR", "action": "HOLD", "target_weight_pct": 11.0, "rationale": "inside deadband", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = report["portfolio"]["positions"][0]
        self.assertEqual(row["deadband_status"], "NO_TRADE_PREFERRED")
        self.assertEqual(row["share_delta"]["value"], 0)

    def test_hard_cap_violation_is_visible(self):
        report, _ = self.compile()
        violations = report["portfolio"]["current_risk"]["hard_cap_violations"]
        self.assertIn("POSITION_PCT:MVLL", violations)

    def test_expected_sale_proceeds_never_become_orderable_cash(self):
        report, _ = self.compile()
        self.assertGreater(report["stage1"]["expected_sale_proceeds_usd"]["value"], 0)
        self.assertEqual(report["cash_semantics"]["verified_orderable_cash_usd"]["value"], 10_000.0)
        self.assertFalse(report["cash_semantics"]["expected_proceeds_treated_as_orderable_cash"])
        self.assertIsNotNone(report["cash_semantics"]["full_target_reference_cash_usd"]["value"])

    def test_post_sell_verified_cash_permits_stage2(self):
        report, _ = self.compile(post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertTrue(report["stage2"]["buy_advisories"])
        self.assertTrue(all(row["calculated_buy_shares"] >= 0 for row in report["stage2"]["buy_advisories"]))

    def test_insufficient_buy_cash_requires_priority(self):
        report, _ = self.compile(post_sell_evidence(cash=50.0), post_sell_plan(cash_priority=False), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("BUY_ALLOCATION_PRIORITY_REQUIRED", report["stage2"]["blockers"])

    def test_open_items_and_request_accounting_remain_visible(self):
        source = evidence()
        source["broker_observed_state"]["operation_statuses"]["account_open_items"] = "KIWOOM_API_RESPONSE_ERROR"
        report, _ = self.compile(source)
        self.assertIn("OPEN_ITEMS_VISIBILITY_UNAVAILABLE", report["evidence"]["warnings"])
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assertEqual(report["evidence"]["request_accounting"]["account_holdings_read"], "PASS")
        self.assertEqual(report["authority"]["artifact_time_quantity_authority"], "none")

    def test_no_event_context_and_high_event_context(self):
        without, _ = self.compile()
        with_high, _ = self.compile(event_context={"current_high_count": 2, "new_high_count": 1, "affected_tickers": ["MVLL"]})
        self.assertEqual(without["event_context"]["status"], "NOT_PROVIDED")
        self.assertEqual(with_high["event_context"]["current_high_count"], 2)
        self.assertFalse(with_high["event_context"]["automatic_target_change"])

    def test_no_order_path_and_renderer_parity(self):
        report, validation = self.compile()
        markdown = render_markdown(report)
        dashboard_html = render_html(report)
        for token in ("MVLL", "63", "Broker Order Authority", "FALSE"):
            self.assertIn(token, markdown)
            self.assertIn(token, dashboard_html)
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertIsNone(report["authority"]["execution_quantity"])
        self.assertFalse(report["authority"]["automatic_order"])
        self.assertFalse(validation["network_used"])
        self.assertFalse(validation["broker_used"])
        self.assertFalse(validation["order_path_used"])

    def test_canonical_synthetic_fixture_is_schema_valid(self):
        source = evidence()
        self.assertEqual(validate_instance(source, MANUAL_EVIDENCE_SCHEMA), [])
        report, validation = self.compile(source)
        self.assertEqual(report["evidence"]["canonical_schema_errors"], [])
        self.assertEqual(report["evidence"]["canonical_schema_sha256"], hashlib.sha256(MANUAL_EVIDENCE_SCHEMA.read_bytes()).hexdigest())
        self.assertTrue(validation["invariants"]["canonical_evidence_schema"])

    def test_noncanonical_regular_literal_never_finalizes_stage1(self):
        source = evidence()
        source["market_phase"] = "REGULAR"
        report, validation = self.compile(source)
        self.assertNotEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertEqual(validation["status"], "FAIL")

    def test_decimal_floor_boundary_avoids_binary_float_underallocation(self):
        source = evidence(cash=1290.50, holdings={"PGR": 0})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 0.89
        value = {
            "plan_id": "decimal-boundary", "as_of": source["decision_as_of"],
            "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 98.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 2.0,
                           "rationale": "decimal boundary", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertEqual(row["target_shares_reference"]["value"], 29)

    def test_total_targets_over_100_rejected_without_cash_target(self):
        value = plan()
        del value["cash_target_pct"]
        value["positions"][0]["target_weight_pct"] = 70.0
        value["positions"][1]["target_weight_pct"] = 40.0
        self.assertTrue(any("TARGET_ALLOCATION_EXCEEDS_100_PERCENT" in item for item in validate_plan(value)))
        with self.assertRaises(ContractError):
            self.compile(plan_value=value)

    def test_target_hard_cap_blocks_deadband(self):
        source = evidence(cash=852.0, holdings={"PGR": 148})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 1.0
        value = {
            "plan_id": "target-hard-cap", "as_of": source["decision_as_of"], "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 84.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 16.0,
                           "rationale": "counterexample", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertIn("TARGET_HARD_CAP_VIOLATION", row["blockers"])
        self.assertEqual(row["deadband_status"], "NOT_APPLIED")

    def test_partial_priority_is_blocked_when_cash_is_insufficient(self):
        value = post_sell_plan()
        value["buy_priority"] = ["PGR"]
        report, _ = self.compile(post_sell_evidence(cash=50.0), value, compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("BUY_ALLOCATION_PRIORITY_INCOMPLETE", report["stage2"]["blockers"])
        self.assertEqual(report["stage2"]["buy_advisories"], [])

    def test_post_sell_requires_newer_bound_run_and_eligible_session(self):
        stale = evidence()
        value = post_sell_plan()
        stale_report, _ = self.compile(stale, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(stale_report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertIn("POST_SELL_FRESH_RUN_REQUIRED", stale_report["evidence"]["canonical_gate_blockers"])
        pre_market = post_sell_evidence()
        pre_market["market_phase"] = "PRE_MARKET"
        pre_market["current_session_finalization_status"] = "NOT_VERIFIED"
        pre_report, _ = self.compile(pre_market, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(pre_report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertIn("POST_SELL_SESSION_NOT_ELIGIBLE", pre_report["stage2"]["blockers"])

    def test_cli_authority_input_cannot_elevate_blocked_report(self):
        source = evidence(market_phase="PRE_MARKET")
        report, _ = self.compile(source, runtime_advisory_authority="CURRENT_MANUAL_ADVISORY_ELIGIBLE")
        self.assertEqual(report["authority"]["current_runtime_advisory_authority"], "NOT_VERIFIED_BY_RUNTIME")
        self.assertEqual(report["authority"]["runtime_authority_cli_input_effect"], "DISPLAY_ONLY_NO_AUTHORITY_EFFECT")

    def test_json_markdown_html_parity_for_buys_events_and_requests(self):
        report, _ = self.compile(
            post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE",
            event_context={"current_high_count": 2, "new_high_count": 1, "affected_tickers": ["MVLL"]},
        )
        markdown = render_markdown(report)
        dashboard_html = render_html(report)
        self.assertTrue(report["stage2"]["buy_advisories"])
        for row in report["stage2"]["buy_advisories"]:
            for token in (row["ticker"], str(row["calculated_buy_shares"])):
                self.assertIn(token, markdown)
                self.assertIn(token, dashboard_html)
        for token in ("Event context", "MVLL", "Request accounting", "account_holdings_read", "현재성 확인"):
            self.assertIn(token, markdown)
            self.assertIn(token, dashboard_html)

    def test_verified_request_accounting_plain_language_has_html_markdown_parity(self):
        source = evidence()
        report, _ = self.compile(source, request_accounting=verified_request_accounting(source))
        for rendered in (render_markdown(report), render_html(report)):
            self.assertIn("Request accounting: VERIFIED", rendered)
            self.assertIn("원본 해시에 정확히 결속", rendered)
            self.assertIn("현재 세션 확인 자료", rendered)

    def test_schema_valid_but_unverified_and_preflight_fail_block_stage1(self):
        unverified = evidence()
        unverified["evidence_grade"] = "UNVERIFIED"
        unverified["manual_data_verification_status"] = "NOT_VERIFIED"
        unverified["provenance"]["evidence_grade"] = "UNVERIFIED"
        unverified["provenance"]["decision_quality_eligible"] = False
        self.assertEqual(validate_instance(unverified, MANUAL_EVIDENCE_SCHEMA), [])
        unverified_report, _ = self.compile(unverified)
        self.assertNotEqual(unverified_report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        failed = evidence()
        failed["preflight_status"] = "FAIL"
        failed_report, _ = self.compile(failed)
        self.assertNotEqual(failed_report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_plan_later_than_evidence_blocks_current_final(self):
        value = plan()
        value["as_of"] = "2026-08-21T22:00:01+00:00"
        report, _ = self.compile(plan_value=value)
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("PLAN_AS_OF_AFTER_BOUND_EVIDENCE", report["evidence"]["canonical_gate_blockers"])

    def test_stage2_unverified_and_preflight_fail_are_blocked(self):
        value = post_sell_plan()
        unverified = post_sell_evidence()
        unverified["evidence_grade"] = "UNVERIFIED"
        unverified["manual_data_verification_status"] = "NOT_VERIFIED"
        unverified["provenance"]["evidence_grade"] = "UNVERIFIED"
        unverified["provenance"]["decision_quality_eligible"] = False
        report, _ = self.compile(unverified, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        failed = post_sell_evidence()
        failed["preflight_status"] = "FAIL"
        report, _ = self.compile(failed, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_decimal_floor_just_below_integer_boundary(self):
        source = evidence(cash=1290.49, holdings={"PGR": 0})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 0.89
        value = {
            "plan_id": "decimal-below", "as_of": source["decision_as_of"], "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 98.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 2.0,
                           "rationale": "below boundary", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertEqual(row["target_shares_reference"]["value"], 28)

    def test_position_targets_plus_cash_over_100_rejected(self):
        value = plan()
        value["cash_target_pct"] = 70.0
        self.assertTrue(any("TARGET_ALLOCATION_EXCEEDS_100_PERCENT" in item for item in validate_plan(value)))

    def test_current_hard_cap_prevents_deadband(self):
        source = evidence(cash=840.0, holdings={"PGR": 160})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 1.0
        value = {
            "plan_id": "current-hard-cap", "as_of": source["decision_as_of"], "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 85.5,
            "positions": [{"ticker": "PGR", "action": "TRIM", "target_weight_pct": 14.5,
                           "rationale": "current cap", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertEqual(row["deadband_status"], "NOT_APPLIED")
        self.assertNotEqual(row["share_delta"]["value"], 0)

    def test_complete_priority_is_deterministic_without_ticker_fallback(self):
        first_source = post_sell_evidence(cash=250.0)
        second_source = post_sell_evidence(cash=250.0)
        for source in (first_source, second_source):
            next(item for item in source["broker_observed_state"]["holdings"] if item["ticker"] == "NBIS")["held_quantity"] = 100
        first_plan = post_sell_plan()
        first_plan["buy_priority"] = ["PGR", "JPM"]
        first, _ = self.compile(first_source, first_plan, compile_mode="POST_SELL_RECOMPILE")
        second_plan = post_sell_plan()
        second_plan["buy_priority"] = ["JPM", "PGR"]
        second, _ = self.compile(second_source, second_plan, compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual([row["ticker"] for row in first["stage2"]["buy_advisories"]], ["PGR", "JPM"])
        self.assertEqual([row["ticker"] for row in second["stage2"]["buy_advisories"]], ["JPM", "PGR"])

    def test_request_accounting_absent_and_arbitrary_shape_are_not_verified(self):
        absent = evidence()
        del absent["broker_observed_state"]["operation_statuses"]
        absent_report, _ = self.compile(absent)
        self.assertEqual(absent_report["evidence"]["request_accounting_status"], "ABSENT")
        invalid = evidence()
        invalid["broker_observed_state"]["operation_statuses"] = ["arbitrary"]
        invalid_report, _ = self.compile(invalid)
        self.assertEqual(invalid_report["evidence"]["request_accounting_status"], "PRESENT_INVALID")
        self.assertNotIn("VERIFIED", invalid_report["evidence"]["request_accounting_status"])

    def test_old_evidence_cannot_use_later_current_context(self):
        old = evidence()
        later = post_sell_evidence()
        later_hash = hashlib.sha256(evidence_raw_bytes(later)).hexdigest()
        report, _ = self.compile(old, current_session_context=current_context(later, later_hash))
        self.assertEqual(report["stage1"]["status"], "READY_FOR_DECISION_PLAN_PREPARATION")
        self.assertIn("CURRENT_CONTEXT_RUN_ID_MISMATCH", report["current_context"]["blockers"])

    def test_bound_old_context_cannot_pass_a_later_canonical_session(self):
        source = evidence()

        def later_session(*_args, **_kwargs):
            return SimpleNamespace(
                authority_status="VERIFIED",
                expected_completed_session=SimpleNamespace(session_date="2026-08-24"),
                market_phase=source["session_authority_market_phase"],
                calendar_policy_identity=source["calendar_policy_identity"],
                calendar_hash=source["calendar_hash"],
                activation_cohort_id=source["session_activation_cohort_id"],
            )

        report, _ = self.compile(source, current_session_authority_resolver=later_session)
        self.assertEqual(report["stage1"]["status"], "READY_FOR_DECISION_PLAN_PREPARATION")
        self.assertIn("CURRENT_CONTEXT_NOT_CURRENT_CANONICAL_SESSION", report["current_context"]["blockers"])

    def test_missing_current_context_allows_only_plan_preparation(self):
        report, _ = self.compile(current_session_context=None)
        self.assertEqual(report["stage1"]["status"], "READY_FOR_DECISION_PLAN_PREPARATION")
        self.assertEqual(report["current_context"]["status"], "ABSENT")
        self.assertTrue(report["authority"]["ready_for_decision_plan_preparation"])
        self.assertEqual(report["authority"]["current_runtime_advisory_authority"], "NOT_VERIFIED_BY_RUNTIME")

    def test_current_context_run_mismatch_blocks_final(self):
        source = evidence()
        context = current_context(source)
        context["expected_evidence_run_id"] = "manual-other-grade-b"
        report, _ = self.compile(source, current_session_context=context)
        self.assertIn("CURRENT_CONTEXT_RUN_ID_MISMATCH", report["current_context"]["blockers"])
        self.assertNotEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_current_context_sha_mismatch_blocks_final(self):
        source = evidence()
        context = current_context(source)
        context["expected_evidence_sha256"] = "0" * 64
        report, _ = self.compile(source, current_session_context=context)
        self.assertIn("CURRENT_CONTEXT_EVIDENCE_SHA256_MISMATCH", report["current_context"]["blockers"])

    def test_current_context_decision_as_of_mismatch_blocks_final(self):
        source = evidence()
        context = current_context(source)
        context["expected_evidence_decision_as_of"] = "2026-08-21T22:00:01+00:00"
        report, _ = self.compile(source, current_session_context=context)
        self.assertIn("CURRENT_CONTEXT_DECISION_AS_OF_MISMATCH", report["current_context"]["blockers"])

    def test_matching_current_context_allows_other_stage1_gates(self):
        report, validation = self.compile()
        self.assertEqual(report["current_context"]["status"], "VERIFIED")
        self.assertEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertTrue(validation["invariants"]["current_session_context_gate_enforced"])

    def test_stage2_context_bound_to_prior_run_is_blocked(self):
        source = post_sell_evidence()
        prior = evidence()
        prior_hash = hashlib.sha256(evidence_raw_bytes(prior)).hexdigest()
        report, _ = self.compile(
            source, post_sell_plan(), compile_mode="POST_SELL_RECOMPILE",
            current_session_context=current_context(prior, prior_hash),
        )
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("CURRENT_CONTEXT_RUN_ID_MISMATCH", report["stage2"]["blockers"])

    def test_stage2_matching_post_sell_context_passes_currentness(self):
        report, _ = self.compile(post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["current_context"]["status"], "VERIFIED")
        self.assertEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def _decimal_portfolio_case(self, pgr_price: float) -> tuple[dict, dict]:
        source = evidence(cash=0.01, holdings={"PGR": 1, "JPM": 1, "SOXL": 0})
        exact_prices = {"PGR": pgr_price, "JPM": 1289.37, "SOXL": 0.89}
        source["last_verified_finalized_bars"] = [
            item for item in source["last_verified_finalized_bars"] if item["ticker"] in exact_prices
        ]
        for item in source["last_verified_finalized_bars"]:
            item["bar"]["price"] = exact_prices[item["ticker"]]
        value = {
            "plan_id": "exact-decimal", "as_of": source["decision_as_of"],
            "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"],
                                 "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 98.0,
            "positions": [
                {"ticker": "PGR", "action": "HOLD", "target_weight_pct": 0.0,
                 "rationale": "NAV component A", "investment_horizon": "test", "target_status": "APPROVED"},
                {"ticker": "JPM", "action": "HOLD", "target_weight_pct": 0.0,
                 "rationale": "NAV component B", "investment_horizon": "test", "target_status": "APPROVED"},
                {"ticker": "SOXL", "action": "ADD", "target_weight_pct": 2.0,
                 "rationale": "exact target", "investment_horizon": "test", "target_status": "APPROVED"},
            ],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        return source, value

    def test_decimal_nav_is_exact_before_serialization(self):
        source, value = self._decimal_portfolio_case(1.12)
        report, _ = self.compile(source, value)
        self.assertEqual(report["portfolio"]["nav_usd"]["value"], 1290.5)

    def test_decimal_multi_position_values_recompute_to_exact_nav(self):
        source, value = self._decimal_portfolio_case(1.12)
        report, _ = self.compile(source, value)
        values = {row["ticker"]: row["current_market_value_usd"]["value"] for row in report["portfolio"]["positions"]}
        self.assertEqual(values["PGR"], 1.12)
        self.assertEqual(values["JPM"], 1289.37)
        recomputed = Decimal("0.01") + Decimal(str(values["PGR"])) + Decimal(str(values["JPM"]))
        self.assertEqual(recomputed, Decimal(str(report["portfolio"]["nav_usd"]["value"])))

    def test_decimal_exact_target_yields_29_shares(self):
        source, value = self._decimal_portfolio_case(1.12)
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "SOXL")
        self.assertEqual(row["target_shares_reference"]["value"], 29)

    def test_decimal_just_below_target_yields_28_shares(self):
        source, value = self._decimal_portfolio_case(1.11)
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "SOXL")
        self.assertEqual(report["portfolio"]["nav_usd"]["value"], 1290.49)
        self.assertEqual(row["target_shares_reference"]["value"], 28)

    def test_decimal_exact_whole_share_boundary_is_not_underallocated(self):
        source, value = self._decimal_portfolio_case(1.12)
        value["positions"][2]["target_weight_pct"] = 2
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "SOXL")
        self.assertEqual(row["target_shares_reference"]["value"], 29)

    def test_decimal_cash_bound_has_no_epsilon_overspend(self):
        source = post_sell_evidence(cash=100.89)
        source["broker_observed_state"]["holdings"] = [
            {"ticker": "PGR", "held_quantity": 0, "average_cost": 0.0}
        ]
        source["verified_orderable_cash_usd"] = 0.89
        source["last_verified_finalized_bars"] = [
            item for item in source["last_verified_finalized_bars"] if item["ticker"] == "PGR"
        ]
        source["last_verified_finalized_bars"][0]["bar"]["price"] = 0.89
        value = {
            "plan_id": "cash-bound", "as_of": "2026-08-21T22:00:00+00:00",
            "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": "manual-synthetic-grade-b",
                                 "expected_decision_as_of": "2026-08-21T22:00:00+00:00"},
            "post_sell_refresh": {"prior_run_id": "manual-synthetic-grade-b",
                                  "prior_decision_as_of": "2026-08-21T22:00:00+00:00"},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 90.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 10.0,
                           "rationale": "cash boundary", "investment_horizon": "test", "target_status": "APPROVED"}],
            "buy_priority": ["PGR"], "material_unknowns": [], "decision_change_triggers": [],
        }
        original_policy = self.policy
        self.policy = copy.deepcopy(self.policy)
        self.policy["cash"]["hard_floor_pct"] = 0
        try:
            exact, _ = self.compile(source, value, compile_mode="POST_SELL_RECOMPILE")
            self.assertEqual(exact["stage2"]["buy_advisories"][0]["calculated_buy_shares"], 1)
            self.assertEqual(exact["cash_semantics"]["post_initial_buy_estimated_cash_usd"]["value"], 0)
            source["verified_orderable_cash_usd"] = 0.8899999999999999
            below, _ = self.compile(source, value, compile_mode="POST_SELL_RECOMPILE")
            self.assertEqual(below["stage2"]["buy_advisories"][0]["calculated_buy_shares"], 0)
            self.assertGreaterEqual(below["cash_semantics"]["post_initial_buy_estimated_cash_usd"]["value"], 0)
        finally:
            self.policy = original_policy

    def test_request_accounting_verified_state_is_reachable(self):
        source = evidence()
        verified = verified_request_accounting(source)
        report, _ = self.compile(source, request_accounting=verified)
        self.assertEqual(report["evidence"]["request_accounting_status"], "VERIFIED")

    def test_request_accounting_present_unverified_state_is_reachable(self):
        source = evidence()
        unverified = verified_request_accounting(source)
        unverified["verification_status"] = "UNVERIFIED"
        report, _ = self.compile(source, request_accounting=unverified)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")

    def test_request_accounting_present_invalid_state_is_reachable(self):
        report, _ = self.compile(request_accounting={"arbitrary": True})
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_INVALID")

    def test_request_accounting_absent_state_is_reachable(self):
        source = evidence()
        del source["broker_observed_state"]["operation_statuses"]
        report, _ = self.compile(source, request_accounting=None)
        self.assertEqual(report["evidence"]["request_accounting_status"], "ABSENT")

    def test_request_accounting_run_mismatch_is_unverified(self):
        source = evidence()
        wrong_run = verified_request_accounting(source)
        wrong_run["source_run_id"] = "manual-other-grade-b"
        report, _ = self.compile(source, request_accounting=wrong_run)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assertIn("REQUEST_ACCOUNTING_RUN_ID_MISMATCH", report["evidence"]["request_accounting_issues"])

    def test_request_accounting_hash_mismatch_is_unverified(self):
        source = evidence()
        wrong_hash = verified_request_accounting(source)
        wrong_hash["source_artifact_sha256"] = "0" * 64
        report, _ = self.compile(source, request_accounting=wrong_hash)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assertIn("REQUEST_ACCOUNTING_SOURCE_SHA256_MISMATCH", report["evidence"]["request_accounting_issues"])

    def test_request_accounting_negative_counter_is_invalid(self):
        source = evidence()
        negative = verified_request_accounting(source)
        negative["retry_count"] = -1
        report, _ = self.compile(source, request_accounting=negative)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_INVALID")

    def test_request_accounting_consistency_violation_is_invalid(self):
        source = evidence()
        inconsistent = verified_request_accounting(source)
        inconsistent["successful_request_count"] = 4
        report, _ = self.compile(source, request_accounting=inconsistent)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_INVALID")
        self.assertIn("REQUEST_ACCOUNTING_RESULT_TOTAL_MISMATCH", report["evidence"]["request_accounting_issues"])

    def test_verified_request_accounting_never_changes_authority(self):
        source = evidence()
        report, _ = self.compile(source, request_accounting=verified_request_accounting(source))
        self.assertEqual(report["evidence"]["request_accounting_status"], "VERIFIED")
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertIsNone(report["authority"]["execution_quantity"])
        self.assertFalse(report["authority"]["automatic_order"])

    def test_event_asset_review_required_is_visible_without_target_change(self):
        report, _ = self.compile(event_context={
            "status": "ASSET_REVIEW_REQUIRED", "current_high_count": 2,
            "new_high_count": 0, "affected_tickers": ["MVLL", "NBIS"],
        })
        self.assertFalse(report["event_context"]["automatic_target_change"])
        for rendered in (render_markdown(report), render_html(report)):
            self.assertIn("ASSET_REVIEW_REQUIRED", rendered)
            self.assertIn("MVLL", rendered)
            self.assertIn("NBIS", rendered)

    def test_historical_replay_cannot_be_forced_current_by_cli(self):
        report, _ = self.compile(
            plan_value=plan(status="HISTORICAL"), compile_mode="HISTORICAL_REPLAY",
            runtime_advisory_authority="CURRENT_MANUAL_ADVISORY_ELIGIBLE",
        )
        self.assertEqual(report["stage1"]["status"], "REPLAY_ONLY")
        self.assertEqual(report["authority"]["current_runtime_advisory_authority"], "NOT_VERIFIED_BY_RUNTIME")

    def test_validation_common_is_in_implementation_provenance(self):
        paths = implementation_provenance_paths(DEFAULT_RISK_POLICY)
        self.assertIn(SCRIPTS / "validation_common.py", paths)
        self.assertIn(SCRIPTS / "session_authority.py", paths)
        self.assertIn(SCRIPTS / "session_calendar_artifact.py", paths)
        self.assertIn(CURRENT_SESSION_CONTEXT_SCHEMA, paths)
        self.assertIn(REQUEST_ACCOUNTING_SCHEMA, paths)
        report, validation = self.compile()
        with tempfile.TemporaryDirectory(dir=ROOT / "manage-us-stock-strategy/tests") as temp:
            consumed = {"risk_policy": hashlib.sha256(DEFAULT_RISK_POLICY.read_bytes()).hexdigest()}
            run_dir = write_run(
                report, validation, output_root=Path(temp), root=ROOT,
                source_paths={"portfolio_evidence": None, "decision_plan": None},
                implementation_paths=paths, consumed_hashes=consumed,
            )
            manifest = load_json(run_dir / "run-manifest.json")
            self.assertIn("manage-us-stock-strategy/scripts/validation_common.py", manifest["implementation_hashes"])
            self.assertEqual(manifest["consumed_hashes"], consumed)

    def test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan(self):
        fixture = ROOT / "workspace/outputs/manual-portfolio-analysis/manual-20260829T153208101909Z-c32341e4e7f3/manual-portfolio-analysis.json"
        self.assertTrue(fixture.is_file())
        self.assertEqual(validate_instance(load_json(fixture), MANUAL_EVIDENCE_SCHEMA), [])
        discovery = discover_historical_replay(ROOT)
        self.assertEqual(discovery["status"], "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND")
        self.assertFalse(discovery["current_advisory_created"])

    def test_create_only_collision(self):
        report, validation = self.compile()
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            implementation = temp_root / "implementation.py"
            implementation.write_text("# synthetic\n", encoding="utf-8")
            output = temp_root / "outputs"
            run_dir = write_run(report, validation, output_root=output, root=temp_root,
                                source_paths={"portfolio_evidence": None, "decision_plan": None},
                                implementation_paths=[implementation])
            manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
            for name, expected in manifest["artifact_hashes"].items():
                self.assertEqual(hashlib.sha256((run_dir / name).read_bytes()).hexdigest(), expected)
            self.assertTrue(manifest["create_only"])
            with self.assertRaises(FileExistsError):
                write_run(report, validation, output_root=output, root=temp_root,
                          source_paths={"portfolio_evidence": None, "decision_plan": None},
                          implementation_paths=[implementation])

    def test_replay_discovery_requires_real_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema_target = root / MANUAL_EVIDENCE_SCHEMA.relative_to(ROOT)
            schema_target.parent.mkdir(parents=True)
            schema_target.write_bytes(MANUAL_EVIDENCE_SCHEMA.read_bytes())
            fixture_dir = root / "workspace/outputs/manual-portfolio-analysis/run-1"
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "manual-portfolio-analysis.json").write_text(
                json.dumps(evidence()), encoding="utf-8",
            )
            result = discover_historical_replay(root)
            self.assertEqual(result["status"], "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND")
            self.assertFalse(result["current_advisory_created"])


if __name__ == "__main__":
    unittest.main()
