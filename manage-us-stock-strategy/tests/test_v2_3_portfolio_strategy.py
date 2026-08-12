from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "manage-us-stock-strategy"
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_capital_redeployment_plan import build_capital_redeployment_plan
from build_holding_strategy_review import build_holding_strategies
from run_portfolio_strategy_orchestrator import (
    _component_output_paths,
    build_portfolio_strategy_report,
    update_holding_runtime,
)
from run_tactical_opportunity_radar import ACTIVE_SYMBOLS
from validate_registry_consistency import validate_registry_consistency
from validation_common import load_json, validate_instance


class V23PortfolioStrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.alert_policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        cls.registry_path = ROOT / "workspace" / "policies" / "instrument_registry.json"
        cls.registry = load_json(cls.registry_path)
        cls.universe = load_json(ROOT / "workspace" / "policies" / "tactical_candidate_universe.json")
        cls.radar_policy = load_json(ROOT / "workspace" / "policies" / "tactical_radar_policy.json")
        cls.registry_validation = validate_registry_consistency(cls.registry, cls.alert_policy, cls.registry_path)
        cls.state_path = ROOT / "stock-strategy-system" / "portfolio_state.json"

    def _portfolio(self, cash: float = 0.0, holdings: dict[str, int] | None = None) -> dict:
        holdings = holdings or {"SOXL": 75}
        costs = {"SOXL": 123.3251, "MVLL": 41.7791, "NBIS": 215.0}
        return {
            "strategy_version": "2026-08-05-v4", "state_revision": 99,
            "holdings": holdings, "average_cost_usd": {key: costs[key] for key in holdings},
            "position_cost_basis_usd": {key: costs[key] * value for key, value in holdings.items()},
            "available_cash_usd": cash,
            "last_confirmed_broker_snapshot": {"verified": True, "holdings_complete": True,
                "cash_verified": True, "as_of": "2026-08-11", "source": "TEST_ONLY"},
        }

    def _row(self, close: float = 100.0, ready: bool = False) -> dict:
        return {"bar_date": "2026-08-11", "open": close - 1, "high": close + 1, "low": close - 2,
            "close": close, "close_prev": close - 1, "volume": 1_000_000,
            "corporate_action_unresolved": False, "breakout_acceptance_confirmed": False,
            "ema10_reclaim_confirmed": False, "ema20_reclaim_confirmed": ready,
            "indicator_validation": {"status": "passed", "errors": []},
            "quote_crosscheck": {"status": "verified", "independent_of_builder": True,
                "bar_date": "2026-08-11", "source": "TEST_ONLY_INDEPENDENT"}}

    def _market(self, ready_symbols: set[str] | None = None) -> dict:
        ready_symbols = ready_symbols or set()
        symbols = {symbol: self._row(100.0, symbol in ready_symbols) for symbol in ACTIVE_SYMBOLS}
        symbols["MRVL"] = self._row(100.0)
        symbols["SOXX"] = self._row(100.0)
        return {"session": {"official_calendar_verified": True,
            "calendar_verification_status": "verified_trading_day", "regular_session_complete": True,
            "us_session_date": "2026-08-11", "expected_us_session_date": "2026-08-11"}, "symbols": symbols}

    def _events(self) -> dict:
        return {"coverage_status": "COMPLETE", "events": [], "order_authority": False}

    def _risk(self, candidates: list[dict] | None = None, hard: bool = False) -> dict:
        return {"state": "HARD_RISK_REVIEW" if hard else "DAILY_REVIEW", "grade": "D" if hard else "E",
            "candidates": candidates or [], "watchlist": [], "risk_freeze_active": hard,
            "warnings": [], "order_authority": False}

    def _research(self, *, signal: str = "NONE", thesis: str = "VALID", valuation: str = "FAIR",
                  technical: str = "WATCH", risk: str = "ACCEPTABLE", fit: str = "FITS") -> dict:
        return {"holdings": {"SOXL": {"validation": {"status": "VALIDATED",
            "evidence_packet_validated": True, "deterministic_gate_status": "PASS",
            "risk_controller_status": "ALLOW_REVIEW"}, "research_packet_hash": "a" * 64,
            "thesis_status": thesis, "valuation_status": valuation, "technical_status": technical,
            "risk_status": risk, "portfolio_fit_status": fit, "strategy_signal": signal,
            "claim_ids": ["CLAIM-1"], "primary_reason": "Validated test-only evidence remains stable.",
            "strongest_counter_case": "Test-only counter case.", "remaining_conditions": [],
            "add_conditions": ["VALIDATED_ADD_GATE"], "reduce_conditions": ["VALIDATED_REDUCE_GATE"],
            "invalidation": "TEST_ONLY_INVALIDATION", "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}}}

    def _holding(self, context: dict, *, state=None, market=None, risk=None):
        return build_holding_strategies(state or self._portfolio(), self.alert_policy, self.registry,
            market or self._market(), self._events(), risk or self._risk(), context,
            analysis_cutoff="2026-08-12T00:45:00+00:00", market_session="2026-08-11")

    def test_verified_healthy_holding_is_hold(self) -> None:
        result = self._holding(self._research())[0]
        self.assertEqual(result["strategy_state"], "HOLD")
        self.assertEqual(result["execution_state"], "NOT_APPLICABLE")

    def test_validated_add_is_visible_but_cash_blocked(self) -> None:
        result = self._holding(self._research(signal="ADD_CANDIDATE", technical="READY"))[0]
        self.assertEqual(result["strategy_state"], "ADD_REVIEW")
        self.assertEqual(result["execution_state"], "CASH_BLOCKED")

    def test_validated_add_with_pending_entry_is_add_on_watch(self) -> None:
        result = self._holding(self._research(signal="ADD_CANDIDATE", technical="WATCH"))[0]
        self.assertEqual(result["strategy_state"], "ADD_ON_WATCH")
        self.assertEqual(result["execution_state"], "WATCH_ONLY")
        self.assertEqual(result["strongest_counter_case"], "Test-only counter case.")
        self.assertEqual(result["next_review_trigger"], "NEXT_COMPLETED_US_SESSION")
        self.assertEqual(len(result["snapshot_hash"]), 64)
        self.assertEqual(len(result["event_snapshot_hash"]), 64)

    def test_validated_deterioration_is_reduction_review_without_quantity(self) -> None:
        result = self._holding(self._research(signal="REDUCE_CANDIDATE", thesis="CONTESTED", technical="DETERIORATING", risk="CONSTRAINED"))[0]
        self.assertEqual(result["strategy_state"], "REDUCTION_REVIEW")
        self.assertIsNone(result["quantity"])
        self.assertEqual(result["quantity_authority"], "none")

    def test_validated_severe_thesis_failure_is_exit_review(self) -> None:
        result = self._holding(self._research(signal="EXIT_CANDIDATE", thesis="INVALIDATED", risk="VETO"))[0]
        self.assertEqual(result["strategy_state"], "EXIT_REVIEW")
        self.assertIsNone(result["quantity"])

    def test_stale_strategy_requires_refresh(self) -> None:
        result = self._holding({"holdings": {}})[0]
        self.assertEqual(result["strategy_state"], "STRATEGY_REFRESH_REQUIRED")

    def test_missing_critical_market_data_is_data_blocked(self) -> None:
        market = self._market()
        del market["symbols"]["SOXL"]
        result = self._holding(self._research(), market=market)[0]
        self.assertEqual(result["strategy_state"], "DATA_BLOCKED")

    def test_no_sell_side_holding_action_for_non_held_ticker(self) -> None:
        context = self._research(signal="EXIT_CANDIDATE", thesis="INVALIDATED", risk="VETO")
        context["holdings"]["NOW"] = copy.deepcopy(context["holdings"]["SOXL"])
        records = self._holding(context)
        self.assertEqual({item["ticker"] for item in records}, {"SOXL"})

    def test_existing_deterministic_tranche_quantity_carries_provenance(self) -> None:
        timing = {"event_type": "holding_timing_review", "symbol": "SOXL", "side": "reduce",
            "grade": "B", "quantity": 24, "tranche_id": "SOXL-R50", "trigger_path": "weakness_20ema",
            "event_key": "TIMING-TEST", "missing_conditions": []}
        result = self._holding(self._research(), risk=self._risk([timing]))[0]
        self.assertEqual(result["strategy_state"], "REDUCTION_REVIEW")
        self.assertEqual(result["quantity"], 24)
        self.assertEqual(result["quantity_authority"], "deterministic_existing_policy")
        self.assertEqual(result["tranche_id"], "SOXL-R50")

    def test_projected_proceeds_require_deterministic_quantity(self) -> None:
        strategy = self._holding(self._research(signal="REDUCE_CANDIDATE", thesis="CONTESTED", technical="DETERIORATING", risk="CONSTRAINED"))[0]
        plan = build_capital_redeployment_plan(self._portfolio(), [strategy], {"candidate_dispositions": []},
            self._risk(), self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertIsNone(plan["projected_sale_proceeds_usd"])
        timing = {"event_type": "holding_timing_review", "symbol": "SOXL", "side": "reduce",
            "grade": "B", "quantity": 24, "tranche_id": "SOXL-R50", "trigger_path": "weakness_20ema",
            "event_key": "TIMING-TEST", "missing_conditions": []}
        strategy = self._holding(self._research(), risk=self._risk([timing]))[0]
        plan = build_capital_redeployment_plan(self._portfolio(), [strategy], {"candidate_dispositions": []},
            self._risk(), self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(plan["projected_sale_proceeds_usd"], 2400.0)
        self.assertEqual(plan["verified_available_cash_usd"], 0.0)
        self.assertEqual(plan["execution_purchasing_power_usd"], 0.0)
        self.assertEqual(plan["funding_status"], "UNFUNDED_PROJECTED_PLAN")

    def test_confirmed_cash_changes_only_with_verified_state(self) -> None:
        strategy = self._holding(self._research())[0]
        plan = build_capital_redeployment_plan(self._portfolio(3264.31), [strategy], {"candidate_dispositions": []},
            self._risk(), self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(plan["verified_available_cash_usd"], 3264.31)
        self.assertEqual(plan["execution_purchasing_power_usd"], 3264.31)
        self.assertEqual(plan["funding_status"], "FUNDED_VERIFIED")

    def test_projected_and_unconfirmed_proceeds_never_double_count(self) -> None:
        timing = {"event_type": "holding_timing_review", "symbol": "SOXL", "side": "reduce",
            "grade": "B", "quantity": 24, "tranche_id": "SOXL-R50", "trigger_path": "weakness_20ema",
            "event_key": "TIMING-TEST", "missing_conditions": []}
        strategy = self._holding(self._research(), state=self._portfolio(100.0), risk=self._risk([timing]))[0]
        plan = build_capital_redeployment_plan(self._portfolio(100.0), [strategy], {"candidate_dispositions": []},
            self._risk(), self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST",
            unsettled_or_unconfirmed_proceeds_usd=500.0)
        self.assertEqual(plan["execution_purchasing_power_usd"], 100.0)
        self.assertEqual(plan["projected_sale_proceeds_usd"], 2400.0)
        self.assertEqual(plan["unsettled_or_unconfirmed_proceeds_usd"], 500.0)

    def test_redeployment_uses_validated_radar_ranking_not_universe_order(self) -> None:
        strategies = self._holding(self._research(), state=self._portfolio(100.0))
        radar = {"preferred_candidate": "NOW", "alternative_candidate": "MVLL",
            "candidate_dispositions": [
                {"ticker": "MVLL", "opportunity_state": "READY", "execution_state": "ELIGIBLE_FOR_REVIEW",
                    "portfolio_fit_status": "FITS", "primary_blocker": None, "remaining_conditions": []},
                {"ticker": "NOW", "opportunity_state": "READY", "execution_state": "ELIGIBLE_FOR_REVIEW",
                    "portfolio_fit_status": "FITS", "primary_blocker": None, "remaining_conditions": []},
            ]}
        plan = build_capital_redeployment_plan(self._portfolio(100.0), strategies, radar, self._risk(),
            self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(plan["preferred_use"], "NEW_POSITION:NOW")
        self.assertEqual(plan["alternative_use"], "NEW_POSITION:MVLL")

    def test_redeployment_does_not_invent_preference_without_validated_ranking(self) -> None:
        strategies = self._holding(self._research(), state=self._portfolio(100.0))
        radar = {"preferred_candidate": None, "alternative_candidate": None,
            "candidate_dispositions": [{"ticker": "NOW", "opportunity_state": "READY",
                "execution_state": "ELIGIBLE_FOR_REVIEW", "portfolio_fit_status": "FITS",
                "primary_blocker": None, "remaining_conditions": []}]}
        plan = build_capital_redeployment_plan(self._portfolio(100.0), strategies, radar, self._risk(),
            self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(plan["preferred_use"], "KEEP_CASH")
        self.assertIsNone(plan["alternative_use"])

    def test_hard_risk_precedes_bullish_research_and_does_not_hide_opportunity(self) -> None:
        hard = {"event_type": "holding_max_loss_breach", "symbol": "SOXL", "breached": True,
            "grade": "D", "event_key": "HARD-RISK-TEST"}
        strategy = self._holding(self._research(signal="ADD_CANDIDATE", technical="READY"), risk=self._risk([hard], hard=True))[0]
        self.assertEqual(strategy["holding_risk_state"], "POLICY_AUTHORITY_UNVERIFIED")
        self.assertEqual(strategy["strategy_state"], "STRATEGY_REFRESH_REQUIRED")
        radar = {"candidate_dispositions": [{"ticker": "NOW", "opportunity_state": "READY",
            "execution_state": "CASH_BLOCKED", "portfolio_fit_status": "FITS", "primary_blocker": "VERIFIED_AVAILABLE_CASH",
            "remaining_conditions": ["VERIFIED_AVAILABLE_CASH"]}]}
        plan = build_capital_redeployment_plan(self._portfolio(), [strategy], radar, self._risk([hard], hard=True),
            self._market(), generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", policy_version="TEST")
        now = next(item for item in plan["candidate_uses"] if item.get("ticker") == "NOW")
        self.assertEqual(now["opportunity_or_strategy_state"], "READY")
        self.assertEqual(now["execution_state"], "PORTFOLIO_BLOCKED")
        self.assertIn("HARD_RISK_NEW_BUY_FREEZE", now["remaining_conditions"])

    def test_hard_risk_survives_unrelated_global_data_block(self) -> None:
        hard = {"event_type": "holding_max_loss_breach", "symbol": "SOXL", "breached": True,
            "grade": "D", "event_key": "HARD-RISK-DATA-INCOMPLETE"}
        risk = self._risk([hard], hard=False)
        risk["state"] = "DATA_INCOMPLETE"
        strategy = self._holding(self._research(signal="ADD_CANDIDATE", technical="READY"), risk=risk)[0]
        self.assertEqual(strategy["holding_risk_state"], "POLICY_AUTHORITY_UNVERIFIED")
        self.assertEqual(strategy["strategy_state"], "STRATEGY_REFRESH_REQUIRED")
        self.assertTrue(strategy["hard_risk_active"])
        radar = {"candidate_dispositions": [{"ticker": "NOW", "opportunity_state": "READY",
            "execution_state": "CASH_BLOCKED", "portfolio_fit_status": "FITS",
            "primary_blocker": "VERIFIED_AVAILABLE_CASH", "remaining_conditions": ["VERIFIED_AVAILABLE_CASH"]}]}
        plan = build_capital_redeployment_plan(self._portfolio(), [strategy], radar, risk, self._market(),
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", policy_version="TEST")
        now = next(item for item in plan["candidate_uses"] if item.get("ticker") == "NOW")
        self.assertEqual(now["execution_state"], "PORTFOLIO_BLOCKED")

    def test_invalid_session_cannot_advance_holding_runtime_or_notify(self) -> None:
        strategy = self._holding(self._research())[0]
        runtime = {"schema_version": "1.0", "last_processed_session": "2026-08-08",
            "last_run_at": None, "holdings": {"SOXL": {"strategy_state": "DATA_BLOCKED"}},
            "deliveries": {}, "order_authority": False}
        updated, notifications = update_holding_runtime(runtime, [strategy], market_session="2026-08-11",
            generated_at="2026-08-12T00:45:00+00:00", session_valid=False)
        self.assertEqual(updated["last_processed_session"], "2026-08-08")
        self.assertEqual(updated["holdings"]["SOXL"]["strategy_state"], "DATA_BLOCKED")
        self.assertFalse(notifications[0]["notify"])

    def test_component_output_cannot_alias_an_input(self) -> None:
        output = ROOT / "workspace" / "outputs" / "test-v2.3-output-alias"
        protected = {(output / "portfolio_strategy_report.json").resolve()}
        with self.assertRaises(ValueError):
            _component_output_paths(output, protected)

    def test_schemas_and_portfolio_state_immutability(self) -> None:
        before = hashlib.sha256(self.state_path.read_bytes()).hexdigest()
        strategies = self._holding(self._research())
        plan = build_capital_redeployment_plan(self._portfolio(), strategies, {"candidate_dispositions": []},
            self._risk(), self._market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(validate_instance(strategies[0], SKILL / "schemas" / "holding-strategy.schema.json"), [])
        self.assertEqual(validate_instance(plan, SKILL / "schemas" / "capital-redeployment-plan.schema.json"), [])
        self.assertEqual(before, hashlib.sha256(self.state_path.read_bytes()).hexdigest())

    def test_combined_report_validates_and_active_universe_regresses_exactly(self) -> None:
        portfolio = self._portfolio(0.0, {"SOXL": 75, "MVLL": 396, "NBIS": 15})
        research = {"holdings": {}}
        radar_context = {"available_cash_usd": 0.0, "candidates": {}, "deep_research_results": {}}
        for symbol in ACTIVE_SYMBOLS:
            radar_context["candidates"][symbol] = {"validation": {"status": "UNVALIDATED",
                "evidence_packet_validated": False, "deterministic_gate_status": "NOT_RUN", "risk_controller_status": "NOT_RUN"},
                "thesis_status": "UNVERIFIED", "valuation_status": "UNVERIFIED", "technical_status": "WATCH",
                "risk_liquidity_status": "CONSTRAINED", "portfolio_fit_status": "UNVERIFIED",
                "remaining_conditions": ["THESIS_RESEARCH"], "next_review_trigger": "THESIS_RESEARCH"}
        runtime = {"schema_version": "1.0", "policy_version": self.radar_policy["policy_version"],
            "last_processed_us_session": None, "last_run_at": None, "candidates": {}, "deliveries": {}, "order_authority": False}
        holding_runtime = {"schema_version": "1.0", "last_processed_session": None, "last_run_at": None,
            "holdings": {}, "deliveries": {}, "order_authority": False}
        report, _, strategies, plan, _ = build_portfolio_strategy_report(portfolio_state=portfolio,
            alert_policy=self.alert_policy, registry=self.registry, registry_validation=self.registry_validation,
            universe=self.universe, radar_policy=self.radar_policy, market_snapshot=self._market(),
            event_snapshot=self._events(), radar_context=radar_context, holding_research_context=research,
            alert_runtime={}, radar_runtime=runtime, holding_runtime=holding_runtime,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11", holding_risk_result=self._risk())
        self.assertEqual({item["ticker"] for item in strategies}, {"SOXL", "MVLL", "NBIS"})
        self.assertEqual(report["tactical_radar_result"]["active_universe"], list(ACTIVE_SYMBOLS))
        self.assertEqual(validate_instance(report, SKILL / "schemas" / "portfolio-strategy-report.schema.json"), [])
        self.assertEqual(validate_instance(plan, SKILL / "schemas" / "capital-redeployment-plan.schema.json"), [])
        self.assertFalse(report["order_authority"])


if __name__ == "__main__":
    unittest.main()
