from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_capital_redeployment_plan import build_capital_redeployment_plan
from build_holding_strategy_review import build_holding_strategies
from build_independent_close_snapshot import build_snapshot as build_independent_snapshot
from portfolio_policy_gates import evaluate_cash_status
from provider_preflight import preflight
from run_tactical_opportunity_radar import ACTIVE_SYMBOLS, build_radar
from validate_independent_close_snapshot import validate_snapshot as validate_independent_snapshot
from validate_registry_consistency import validate_registry_consistency
from validation_common import load_json, validate_instance


class V24DualPhaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        cls.registry_path = ROOT / "workspace" / "policies" / "instrument_registry.json"
        cls.registry = load_json(cls.registry_path)
        cls.universe = load_json(ROOT / "workspace" / "policies" / "tactical_candidate_universe.json")
        cls.radar_policy = load_json(ROOT / "workspace" / "policies" / "tactical_radar_policy.json")
        cls.registry_validation = validate_registry_consistency(cls.registry, cls.policy, cls.registry_path)

    def portfolio(self, cash=0.0, *, verified=True, cash_verified=True, complete=True, as_of="2026-08-11", holdings=None):
        holdings = holdings if holdings is not None else {"NBIS": 15}
        costs = {"SOXL": 123.3251, "MVLL": 41.7791, "NBIS": 215.0}
        return {"strategy_version": "2026-08-05-v4", "holdings": holdings,
            "average_cost_usd": {key: costs[key] for key in holdings}, "available_cash_usd": cash,
            "last_confirmed_broker_snapshot": {"verified": verified, "cash_verified": cash_verified,
                "holdings_complete": complete, "as_of": as_of, "source": "TEST_ONLY",
                "cash_verified_scope": "available_cash_only"}}

    def row(self, close=100.0, ready=False, cross=True):
        return {"bar_date": "2026-08-11", "open": close, "high": close + 1, "low": close - 1,
            "close": close, "close_prev": close - 1, "volume": 1_000_000,
            "corporate_action_unresolved": False, "breakout_acceptance_confirmed": False,
            "ema10_reclaim_confirmed": False, "ema20_reclaim_confirmed": ready,
            "indicator_validation": {"status": "passed", "errors": []},
            "quote_crosscheck": {"status": "verified" if cross else "pending",
                "independent_of_builder": cross, "bar_date": "2026-08-11", "source": "TEST_INDEPENDENT"}}

    def market(self, ready=None):
        ready = ready or set()
        symbols = {symbol: self.row(100, symbol in ready) for symbol in ACTIVE_SYMBOLS}
        symbols.update({"MRVL": self.row(), "SOXX": self.row()})
        return {"session": {"official_calendar_verified": True, "calendar_verification_status": "verified_trading_day",
            "regular_session_complete": True, "us_session_date": "2026-08-11", "expected_us_session_date": "2026-08-11"},
            "symbols": symbols}

    def events(self):
        return {"coverage_status": "COMPLETE", "events": [], "order_authority": False}

    def risk(self, symbol="NBIS", hard=True, independent=True):
        return {"state": "HARD_RISK_REVIEW" if hard else "DAILY_REVIEW", "grade": "D" if hard else "E",
            "risk_freeze_active": hard, "warnings": [], "watchlist": [], "candidates": [{
                "event_type": "holding_max_loss_breach", "symbol": symbol, "breached": hard,
                "grade": "D" if hard else "E", "event_key": "TEST-HARD",
                "evidence_verification": {"independent_close_crosscheck_verified": independent}}]}

    def test_verified_action_maps_risk_to_exit_or_reduction(self):
        for action, expected in (("exit_review", "EXIT_REVIEW"), ("reduction_review", "REDUCTION_REVIEW")):
            policy = copy.deepcopy(self.policy)
            rule = policy["holding_risk_rules"]["positions"]["NBIS"]
            rule["action_on_breach"] = action
            rule["action_approval_status"] = "VERIFIED_USER_APPROVAL"
            records = build_holding_strategies(self.portfolio(), policy, self.registry, self.market(), self.events(),
                self.risk(), {"holdings": {}}, analysis_cutoff="2026-08-12T00:45:00+00:00", market_session="2026-08-11")
            self.assertEqual(records[0]["holding_risk_state"], "HARD_RISK_BREACH")
            self.assertEqual(records[0]["strategy_state"], expected)
            self.assertIsNone(records[0]["quantity"])

    def test_missing_action_authority_never_auto_exits(self):
        record = build_holding_strategies(self.portfolio(), self.policy, self.registry, self.market(), self.events(),
            self.risk(), {"holdings": {}}, analysis_cutoff="2026-08-12T00:45:00+00:00", market_session="2026-08-11")[0]
        self.assertEqual(record["holding_risk_state"], "POLICY_AUTHORITY_UNVERIFIED")
        self.assertEqual(record["strategy_state"], "STRATEGY_REFRESH_REQUIRED")
        self.assertEqual(record["execution_state"], "HUMAN_REVIEW_REQUIRED")

    def test_primary_close_warning_survives_independent_pending(self):
        market = self.market()
        market["symbols"]["NBIS"]["quote_crosscheck"] = {"status": "pending", "independent_of_builder": False, "bar_date": "2026-08-11"}
        record = build_holding_strategies(self.portfolio(), self.policy, self.registry, market, self.events(),
            self.risk(independent=False), {"holdings": {}}, analysis_cutoff="2026-08-12T00:45:00+00:00", market_session="2026-08-11")[0]
        self.assertTrue(record["hard_risk_active"])
        self.assertEqual(record["primary_close_status"], "VERIFIED")
        self.assertEqual(record["independent_close_status"], "PENDING")

    def test_strict_cash_statuses(self):
        self.assertEqual(evaluate_cash_status(self.portfolio(100, cash_verified=False), reference_session="2026-08-11", maximum_age_calendar_days=4, required_strategy_version="2026-08-05-v4")["cash_status"], "UNVERIFIED")
        self.assertEqual(evaluate_cash_status(self.portfolio(100, as_of="2026-07-01"), reference_session="2026-08-11", maximum_age_calendar_days=4, required_strategy_version="2026-08-05-v4")["cash_status"], "STALE")
        self.assertEqual(evaluate_cash_status(self.portfolio(100, complete=False), reference_session="2026-08-11", maximum_age_calendar_days=4, required_strategy_version="2026-08-05-v4")["cash_status"], "UNVERIFIED")
        self.assertEqual(evaluate_cash_status(self.portfolio(100), reference_session="2026-08-11", maximum_age_calendar_days=4, required_strategy_version="2026-08-05-v4")["cash_status"], "VERIFIED_POSITIVE")

    def test_zero_cash_is_no_funded_action_not_keep_cash(self):
        plan = build_capital_redeployment_plan(self.portfolio(0), [], {"candidate_dispositions": []},
            {"risk_freeze_active": False}, self.market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(plan["cash_status"], "VERIFIED_ZERO")
        self.assertEqual(plan["deployment_decision"], "NO_FUNDED_ACTION")
        self.assertIsNone(plan["preferred_use"])
        self.assertIsNone(plan["alternative_use"])
        self.assertEqual(plan["keep_cash_option"], "NOT_APPLICABLE")

    def test_projected_proceeds_do_not_become_cash(self):
        strategy = {"ticker": "NBIS", "strategy_state": "REDUCTION_REVIEW", "quantity_authority": "deterministic_existing_policy",
            "quantity": 2, "policy_rule_id": "TEST", "tranche_id": "TEST-T1", "trigger_path": "TEST_PATH"}
        plan = build_capital_redeployment_plan(self.portfolio(0), [strategy], {"candidate_dispositions": []},
            {"risk_freeze_active": False}, self.market(), generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST",
            unsettled_or_unconfirmed_proceeds_usd=500)
        self.assertEqual(plan["funding_status"], "UNFUNDED_PROJECTED_PLAN")
        self.assertEqual(plan["execution_purchasing_power_usd"], 0.0)
        self.assertEqual(plan["deployment_decision"], "NO_FUNDED_ACTION")

    def test_held_radar_ticker_is_not_duplicated_as_new_position(self):
        for symbol in ("NBIS", "MVLL", "SOXL"):
            with self.subTest(symbol=symbol):
                radar = {"preferred_candidate": symbol, "alternative_candidate": None, "candidate_dispositions": [{
                    "ticker": symbol, "opportunity_state": "READY", "execution_state": "CASH_BLOCKED",
                    "portfolio_fit_status": "FITS", "primary_blocker": "VERIFIED_AVAILABLE_CASH", "remaining_conditions": []}]}
                holding = {"ticker": symbol, "strategy_state": "ADD_ON_WATCH", "execution_state": "WATCH_ONLY",
                    "portfolio_fit_status": "FITS", "primary_reason": "TEST", "remaining_conditions": []}
                plan = build_capital_redeployment_plan(self.portfolio(0, holdings={symbol: 1}), [holding], radar,
                    {"risk_freeze_active": False}, self.market(), generated_at="2026-08-12T00:45:00+00:00",
                    analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", policy_version="TEST")
                entries = [item for item in plan["candidate_uses"] if item.get("ticker") == symbol]
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["type"], "EXISTING_HOLDING_ADD")

    def test_funded_redeployment_pool_has_one_preferred_and_one_alternative(self):
        portfolio = self.portfolio(10000, holdings={"NBIS": 15})
        radar = {"preferred_candidate": "NOW", "alternative_candidate": None, "candidate_dispositions": [{
            "ticker": "NOW", "opportunity_state": "READY", "execution_state": "ELIGIBLE_FOR_REVIEW",
            "portfolio_fit_status": "FITS", "primary_blocker": None, "remaining_conditions": []}]}
        holding = {"ticker": "NBIS", "strategy_state": "ADD_REVIEW", "execution_state": "ELIGIBLE_FOR_REVIEW",
            "portfolio_fit_status": "FITS", "primary_reason": "TEST_ONLY_VALIDATED_ADD", "remaining_conditions": [],
            "quantity": None, "quantity_authority": "none"}
        plan = build_capital_redeployment_plan(portfolio, [holding], radar, {"risk_freeze_active": False}, self.market(),
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", policy_version="TEST")
        self.assertEqual(plan["execution_purchasing_power_usd"], 10000.0)
        self.assertEqual(plan["preferred_use"], "NEW_POSITION:NOW")
        self.assertEqual(plan["alternative_use"], "KEEP_CASH")
        self.assertLessEqual(len([plan["preferred_use"]]), 1)
        self.assertLessEqual(len([plan["alternative_use"]]), 1)
        self.assertEqual(len({item["use_id"] for item in plan["candidate_uses"]}), len(plan["candidate_uses"]))
        self.assertTrue(all(item["quantity"] is None for item in plan["candidate_uses"]))

    def radar_context(self, ready_symbol="NOW"):
        candidates = {}
        for symbol in ACTIVE_SYMBOLS:
            candidates[symbol] = {"validation": {"status": "VALIDATED", "evidence_packet_validated": True,
                "deterministic_gate_status": "PASS", "risk_controller_status": "ALLOW_REVIEW"},
                "thesis_status": "STRONG" if symbol == ready_symbol else "UNVERIFIED",
                "valuation_status": "FAIR" if symbol == ready_symbol else "UNVERIFIED",
                "technical_status": "READY" if symbol == ready_symbol else "WATCH",
                "risk_liquidity_status": "ACCEPTABLE" if symbol == ready_symbol else "CONSTRAINED",
                "portfolio_fit_status": "FITS" if symbol == ready_symbol else "UNVERIFIED",
                "remaining_conditions": [], "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}
        return {"available_cash_usd": 0, "candidates": candidates, "deep_research_requested": [ready_symbol],
            "deep_research_results": {ready_symbol: {"status": "VALIDATED", "research_packet_hash": "a" * 64}}}

    def runtime(self):
        return {"schema_version": "1.0", "policy_version": self.radar_policy["policy_version"],
            "last_processed_us_session": None, "last_run_at": None, "candidates": {}, "deliveries": {}, "order_authority": False}

    def test_ticker_failure_isolated_and_partial_ready_remains_visible(self):
        market = self.market({"NOW"})
        market["symbols"]["TOST"]["quote_crosscheck"]["status"] = "pending"
        report, _ = build_radar(self.universe, self.registry, self.registry_validation, market, self.events(),
            self.radar_context(), self.portfolio(0, holdings={"NBIS": 15}), self.runtime(), self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11")
        self.assertEqual(report["data_status"], "PARTIAL")
        self.assertEqual(report["preferred_candidate"], "NOW")
        self.assertEqual(report["final_conclusion"], "WAIT")
        self.assertEqual(next(item for item in report["candidate_dispositions"] if item["ticker"] == "TOST")["opportunity_state"], "DATA_BLOCKED")

    def test_provider_wide_outage_is_one_global_incident(self):
        outage = {"capability_status": "UNAVAILABLE", "global_failure": "NO_APPROVED_HEALTHY_PROVIDER"}
        report, _ = build_radar(self.universe, self.registry, self.registry_validation, self.market({"NOW"}), self.events(),
            self.radar_context(), self.portfolio(0), self.runtime(), self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11", provider_preflight=outage)
        self.assertEqual(report["final_conclusion"], "DATA_INCOMPLETE")
        self.assertEqual(report["global_failures"], ["GLOBAL_INDEPENDENT_CLOSE_OUTAGE"])
        self.assertEqual(len(report["global_notifications"]), 1)
        self.assertTrue(report["global_notifications"][0]["notify"])
        self.assertFalse(any(event["notify"] for event in report["transitions"]))

    def test_independent_adapter_rejects_unapproved_provider_and_validates_fixture_provider(self):
        base = load_json(ROOT / "workspace" / "policies" / "source_capabilities.json")
        self.assertEqual(validate_instance(base, ROOT / "manage-us-stock-strategy" / "schemas" / "source-capability.schema.json"), [])
        self.assertEqual(preflight(base, capability="INDEPENDENT_COMPLETED_CLOSE")["capability_status"], "UNAVAILABLE")
        registry = copy.deepcopy(base)
        registry["providers"].append({"provider": "test_independent", "source_type": "market_data",
            "live_supported": True, "historical_point_in_time_supported": True, "timestamp_quality": "SESSION_DATED",
            "authoritative_for": [], "independent_crosscheck_eligible": True, "rate_limit_notes": "TEST_ONLY",
            "failure_behavior": "FAIL_CLOSED", "fallback_priority": 1, "enabled": True,
            "capability_scope": ["INDEPENDENT_COMPLETED_CLOSE"], "limitations": []})
        records = [{"ticker": "NOW", "completed_session": "2026-08-11", "close": 100.0, "currency": "USD",
            "provider": "test_independent", "source_identifier": "TEST", "retrieved_at": "2026-08-12T00:30:00+00:00",
            "source_timestamp": "2026-08-11T20:00:00+00:00", "independent_of_primary_builder": True,
            "tolerance_result": "PASS"}]
        snapshot = build_independent_snapshot(records, registry, required_tickers=["NOW"], completed_session="2026-08-11",
            primary_provider="yfinance", generated_at="2026-08-12T00:45:00+00:00")
        self.assertEqual(snapshot["capability_status"], "AVAILABLE")
        self.assertEqual(validate_independent_snapshot(snapshot, ROOT / "manage-us-stock-strategy" / "schemas" / "independent-close-snapshot.schema.json"), [])

    def test_portfolio_state_remains_immutable(self):
        path = ROOT / "stock-strategy-system" / "portfolio_state.json"
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        evaluate_cash_status(load_json(path), reference_session="2026-08-12", maximum_age_calendar_days=4,
            required_strategy_version="2026-08-05-v4")
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
