#!/usr/bin/env python3
"""Offline safety and negative tests for Portfolio Decision Dashboard v1.0."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from portfolio_decision_dashboard import (  # noqa: E402
    ContractError,
    DEFAULT_RISK_POLICY,
    compile_dashboard,
    discover_historical_replay,
    render_html,
    render_markdown,
    validate_plan,
    write_run,
)
from validation_common import load_json  # noqa: E402


def finalized_bar(ticker: str, price: float) -> dict:
    return {
        "ticker": ticker,
        "identity_authority_status": "VERIFIED",
        "session_authority_status": "VERIFIED",
        "status": "VERIFIED",
        "bar_date": "2026-08-28",
        "bar": {
            "ticker": ticker,
            "provider": "KIWOOM_REST",
            "market_session_type": "REGULAR_COMPLETED",
            "reported_session": "2026-08-28",
            "price_basis": "RAW_REGULAR_SESSION_CLOSE",
            "price": price,
            "currency": "USD",
            "provider_timestamp": "2026-08-29T20:00:00+09:00",
            "bar_finalized": True,
            "stable": True,
            "comparable_to_regular_close": True,
        },
    }


def evidence(*, market_phase: str = "REGULAR", cash: float = 10_000.0) -> dict:
    prices = {"MVLL": 20.0, "NBIS": 100.0, "SOXL": 40.0, "PGR": 200.0, "JPM": 100.0}
    return {
        "schema_version": "2.0",
        "manual_run_id": "manual-synthetic-grade-b",
        "decision_as_of": "2026-08-29T20:00:00+09:00",
        "market_phase": market_phase,
        "evidence_grade": "GRADE_B",
        "preflight_status": "PASS",
        "provenance": {"decision_quality_eligible": True},
        "broker_snapshot_status": "AVAILABLE",
        "broker_diff_status": "DIFFERENT",
        "orderable_cash_status": "VERIFIED",
        "verified_orderable_cash_usd": cash,
        "quantity_authority": "none",
        "order_authority": False,
        "execution_quantity": None,
        "mutation_status": "REPORT_ONLY_CREATE_ONLY",
        "broker_observed_state": {
            "status": "AVAILABLE",
            "scope_complete": False,
            "operation_statuses": {
                "account_holdings_read": "PASS",
                "account_deposit_read": "PASS",
                "account_open_items": "KIWOOM_API_RESPONSE_ERROR",
            },
            "holdings": [
                {"ticker": "MVLL", "held_quantity": 100, "average_cost": 30.0},
                {"ticker": "NBIS", "held_quantity": 20, "average_cost": 90.0},
                {"ticker": "SOXL", "held_quantity": 20, "average_cost": 50.0},
            ],
            "cash": {
                "foreign_currency_deposit": cash,
                "settled_available_cash": cash,
                "order_available_cash": cash,
                "cash_status": "VERIFIED_POSITIVE",
                "projected_proceeds_included": False,
            },
        },
        "system_portfolio_state": {"holdings": {"MVLL": 99, "NBIS": 20, "SOXL": 20}},
        "last_verified_finalized_bars": [finalized_bar(ticker, price) for ticker, price in prices.items()],
    }


def plan(*, status: str = "CURRENT_APPROVED", include_priority: bool = True) -> dict:
    value = {
        "plan_id": "synthetic-plan-v1",
        "as_of": "2026-08-29T20:00:00+09:00",
        "plan_status": status,
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
    value = evidence(cash=cash)
    value["broker_diff_status"] = "MATCH"
    value["broker_observed_state"]["holdings"] = [
        {"ticker": "MVLL", "held_quantity": 37, "average_cost": 30.0},
        {"ticker": "NBIS", "held_quantity": 20, "average_cost": 90.0},
        {"ticker": "SOXL", "held_quantity": 0, "average_cost": 50.0},
    ]
    return value


class PortfolioDecisionDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_json(DEFAULT_RISK_POLICY)

    def compile(self, evidence_value=None, plan_value=None, **kwargs):
        return compile_dashboard(
            evidence_value or evidence(), plan_value or plan(), self.policy,
            run_id="synthetic-run", generated_at="2026-08-30T00:00:00+00:00", **kwargs,
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
        report, _ = self.compile(source, compile_mode="POST_SELL_RECOMPILE")
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
        self.assertEqual(report["evidence"]["current_freshness"], "LAST_KNOWN")

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
        source["last_verified_finalized_bars"] = [finalized_bar("PGR", 100.0)]
        value = {
            "plan_id": "deadband", "as_of": "2026-08-29T20:00:00+09:00", "plan_status": "CURRENT_APPROVED",
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 89.0,
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
        report, _ = self.compile(post_sell_evidence(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertTrue(report["stage2"]["buy_advisories"])
        self.assertTrue(all(row["calculated_buy_shares"] >= 0 for row in report["stage2"]["buy_advisories"]))

    def test_insufficient_buy_cash_requires_priority(self):
        report, _ = self.compile(post_sell_evidence(cash=50.0), plan(include_priority=False), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("BUY_ALLOCATION_PRIORITY_REQUIRED", report["stage2"]["blockers"])

    def test_open_items_and_request_accounting_absence_remain_visible(self):
        report, _ = self.compile()
        self.assertIn("OPEN_ITEMS_VISIBILITY_UNAVAILABLE", report["evidence"]["warnings"])
        self.assertEqual(report["evidence"]["exact_request_accounting_status"], "ABSENT")
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
            fixture_dir = root / "workspace/outputs/manual-portfolio-analysis/run-1"
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "manual-portfolio-analysis.json").write_text(
                json.dumps({"evidence_grade": "GRADE_B"}), encoding="utf-8",
            )
            result = discover_historical_replay(root)
            self.assertEqual(result["status"], "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND")
            self.assertFalse(result["current_advisory_created"])


if __name__ == "__main__":
    unittest.main()
