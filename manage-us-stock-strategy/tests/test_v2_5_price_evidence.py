from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_holding_strategy_review import build_holding_strategies
from build_independent_close_snapshot import build_snapshot
from build_price_crosscheck_queue import build_queue
from price_evidence import compare_close, evidence_status, validate_web_evidence
from run_tactical_opportunity_radar import ACTIVE_SYMBOLS, build_radar
from validate_independent_close_snapshot import validate_snapshot
from validate_registry_consistency import validate_registry_consistency
from validation_common import load_json


class V25PriceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        cls.registry_path = ROOT / "workspace/policies/instrument_registry.json"
        cls.registry = load_json(cls.registry_path)
        cls.universe = load_json(ROOT / "workspace/policies/tactical_candidate_universe.json")
        cls.radar_policy = load_json(ROOT / "workspace/policies/tactical_radar_policy.json")
        cls.registry_validation = validate_registry_consistency(cls.registry, cls.policy, cls.registry_path)

    def row(self, *, ready=False, cross=None, close=100.0):
        return {"bar_date": "2026-08-11", "open": close, "high": close + 1, "low": close - 1,
                "close": close, "close_prev": close - 1, "volume": 1000000,
                "corporate_action_unresolved": False, "breakout_acceptance_confirmed": False,
                "ema10_reclaim_confirmed": False, "ema20_reclaim_confirmed": ready,
                "indicator_validation": {"status": "passed", "errors": []}, "quote_crosscheck": cross}

    def market(self, ready="MVLL", cross=None):
        rows = {symbol: self.row(ready=symbol == ready, cross=copy.deepcopy(cross)) for symbol in ACTIVE_SYMBOLS}
        rows.update({"MRVL": self.row(cross=cross), "SOXX": self.row(cross=cross)})
        return {"session": {"official_calendar_verified": True, "calendar_verification_status": "verified_trading_day",
                            "regular_session_complete": True, "us_session_date": "2026-08-11", "expected_us_session_date": "2026-08-11"},
                "symbols": rows}

    def test_v25_pe_01_primary_hold_needs_no_crosscheck(self):
        portfolio = {"strategy_version": "2026-08-05-v4", "holdings": {"NBIS": 15}, "average_cost_usd": {"NBIS": 215.0},
                     "available_cash_usd": 0.0, "last_confirmed_broker_snapshot": {"verified": True, "holdings_complete": True,
                     "cash_verified": True, "cash_verified_scope": "available_cash_only", "as_of": "2026-08-11", "source": "TEST_ONLY"}}
        context = {"holdings": {"NBIS": {"validation": {"status": "VALIDATED", "evidence_packet_validated": True,
                   "deterministic_gate_status": "PASS", "risk_controller_status": "ALLOW_REVIEW"}, "thesis_status": "VALID",
                   "valuation_status": "FAIR", "technical_status": "WATCH", "risk_status": "ACCEPTABLE",
                   "portfolio_fit_status": "FITS", "strategy_signal": "NONE", "primary_reason": "TEST_HOLD",
                   "research_packet_hash": "a" * 64}}}
        result = build_holding_strategies(portfolio, self.policy, self.registry, self.market(ready="NONE"),
            {"coverage_status": "COMPLETE", "events": []}, {"state": "DAILY_REVIEW", "risk_freeze_active": False, "candidates": []},
            context, analysis_cutoff="2026-08-12T00:45:00+00:00", market_session="2026-08-11")[0]
        self.assertEqual(result["strategy_state"], "HOLD")
        self.assertEqual(result["crosscheck_status"], "NOT_REQUIRED")

    def radar(self, cross=None, ready=True, provider=None):
        candidates = {}
        for symbol in ACTIVE_SYMBOLS:
            validated = symbol == "MVLL"
            candidates[symbol] = {"validation": {"status": "VALIDATED" if validated else "UNVALIDATED",
                "evidence_packet_validated": validated, "deterministic_gate_status": "PASS" if validated else "NOT_RUN",
                "risk_controller_status": "ALLOW_REVIEW" if validated else "NOT_RUN"},
                "thesis_status": "STRONG" if validated else "UNVERIFIED", "valuation_status": "FAIR" if validated else "UNVERIFIED",
                "technical_status": "READY" if validated else "WATCH", "risk_liquidity_status": "ACCEPTABLE" if validated else "CONSTRAINED",
                "portfolio_fit_status": "FITS" if validated else "UNVERIFIED", "remaining_conditions": [],
                "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}
        runtime = {"schema_version": "1.0", "policy_version": self.radar_policy["policy_version"], "last_processed_us_session": None,
                   "last_run_at": None, "candidates": {}, "deliveries": {}, "order_authority": False}
        return build_radar(self.universe, self.registry, self.registry_validation, self.market(cross=cross),
            {"coverage_status": "COMPLETE", "events": []}, {"candidates": candidates, "deep_research_results": {}},
            {"available_cash_usd": 0}, runtime, self.radar_policy, generated_at="2026-08-12T00:45:00+00:00",
            analysis_cutoff="2026-08-12T00:44:00+00:00", market_session="2026-08-11", latest_completed_session="2026-08-11",
            provider_preflight=provider)[0]

    def test_v25_pe_02_watch_survives_provider_outage(self):
        report = self.radar(cross=None, provider={"capability_status": "UNAVAILABLE"})
        self.assertTrue(any(item["opportunity_state"] == "WATCH" for item in report["candidate_dispositions"][1:]))

    def test_v25_pe_03_ready_pending(self):
        item = self.radar(cross=None)["candidate_dispositions"][0]
        self.assertEqual((item["opportunity_state"], item["execution_state"]), ("READY", "VERIFICATION_PENDING"))

    def test_v25_pe_04_web_unavailable_does_not_delete_opportunity(self):
        self.assertEqual(self.radar(cross={"status": "unavailable"})["candidate_dispositions"][0]["opportunity_state"], "READY")

    def test_v25_pe_05_conflict_is_ticker_local(self):
        market = self.market(cross={"status": "verified", "independent_of_builder": True, "bar_date": "2026-08-11"})
        market["symbols"]["MVLL"]["quote_crosscheck"] = {"status": "conflict"}
        report = self.radar(cross={"status": "verified", "independent_of_builder": True, "bar_date": "2026-08-11"})
        report = self.radar(cross={"status": "conflict"})
        self.assertEqual(report["candidate_dispositions"][0]["opportunity_state"], "DATA_BLOCKED")
        self.assertTrue(all(item["opportunity_state"] != "DATA_BLOCKED" for item in report["candidate_dispositions"][1:]))

    def evidence(self, **overrides):
        value = {"ticker": "MVLL", "reported_session": "2026-08-11", "reported_close": 100.02, "currency": "USD",
                 "price_basis": "raw_completed_regular_session_close", "provider": "official_exchange", "source_url": "https://exchange.example/mvll",
                 "source_domain": "exchange.example", "source_type": "EXCHANGE_OFFICIAL_HISTORICAL_CLOSE", "source_timestamp": None,
                 "retrieved_at": "2026-08-12T00:45:00+00:00", "acquisition_method": "CODEX_WEB", "content_hash": "a" * 64,
                 "extractor_confidence": 1.0, "raw_evidence_note": "close", "security_identity_explicit": True,
                 "regular_session_close_explicit": True, "is_search_result_snippet": False, "order_authority": False}
        value.update(overrides)
        return value

    def primary(self, **overrides):
        value = {"ticker": "MVLL", "primary_session": "2026-08-11", "primary_close": 100.0,
                 "primary_price_basis": "raw_completed_regular_session_close", "currency": "USD", "primary_provider": "yfinance"}
        value.update(overrides)
        return value

    def test_v25_pe_06_basis_mismatch_is_inconclusive(self):
        result = compare_close(self.primary(), self.evidence(price_basis="adjusted_close"))
        self.assertEqual((result["comparison_status"], result["crosscheck_status"]), ("PRICE_BASIS_MISMATCH", "INCONCLUSIVE"))

    def test_v25_pe_07_boundary_flip_is_conflict(self):
        result = compare_close(self.primary(), self.evidence(reported_close=100.02), [{"value": 100.01, "operator": "less_than_or_equal"}])
        self.assertEqual((result["comparison_status"], result["crosscheck_status"]), ("DECISION_BOUNDARY_FLIP", "CONFLICT"))

    def test_v25_pe_08_search_snippet_rejected(self):
        self.assertIn("SEARCH_RESULT_SNIPPET_REJECTED", validate_web_evidence(self.evidence(is_search_result_snippet=True)))

    def test_v25_pe_09_yahoo_origin_rejected(self):
        self.assertIn("YAHOO_ORIGIN_NOT_INDEPENDENT", validate_web_evidence(self.evidence(source_url="https://finance.yahoo.com/quote/MVLL/history", source_domain="finance.yahoo.com")))

    def test_v25_pe_10_invalid_verified_combination_rejected(self):
        registry = {"providers": [{"provider": "test", "enabled": True, "independent_crosscheck_eligible": True,
                    "capability_scope": ["INDEPENDENT_COMPLETED_CLOSE"], "source_type": "market_data", "live_supported": True,
                    "historical_point_in_time_supported": True, "timestamp_quality": "SESSION_DATED", "authoritative_for": [],
                    "rate_limit_notes": "TEST", "failure_behavior": "FAIL_CLOSED", "fallback_priority": 1}]}
        record = {"ticker": "MVLL", "completed_session": "2026-08-11", "close": 100.0, "currency": "USD", "provider": "test",
                  "source_identifier": "TEST", "retrieved_at": "2026-08-12T00:45:00+00:00", "independent_of_primary_builder": True,
                  "crosscheck_status": "VERIFIED", "evidence_validation_status": "VALIDATED", "comparison_status": "CONFLICT", "tolerance_result": "FAIL"}
        snapshot = build_snapshot([record], registry, required_tickers=["MVLL"], completed_session="2026-08-11", primary_provider="yfinance",
                                  generated_at="2026-08-12T00:45:00+00:00", provider_health={"test": {"circuit_state": "HEALTHY"}})
        self.assertTrue(validate_snapshot(snapshot, ROOT / "manage-us-stock-strategy/schemas/independent-close-snapshot.schema.json"))

    def test_v25_pe_11_empty_queue_not_required(self):
        queue = build_queue(completed_session="2026-08-11", market_snapshot=self.market(ready="NONE"), candidate_dispositions=[],
                            holding_strategies=[], hard_risk_result={"candidates": []}, requested_at="2026-08-12T00:45:00+00:00")
        self.assertEqual((queue["crosscheck_requirement"], queue["capability_status"], queue["global_failure"]), ("NOT_REQUIRED", "NOT_REQUIRED", None))

    def test_v25_pe_12_outage_only_pends_queued(self):
        report = self.radar(cross=None, provider={"capability_status": "UNAVAILABLE", "global_failure": "TEST"})
        self.assertEqual(len(report["global_notifications"]), 1)
        self.assertEqual(report["candidate_dispositions"][0]["execution_state"], "VERIFICATION_PENDING")
        self.assertTrue(all(item["execution_state"] != "VERIFICATION_PENDING" for item in report["candidate_dispositions"][1:]))

    def test_v25_pe_13_provider_and_domain_provenance_required(self):
        missing_provider = self.evidence()
        del missing_provider["provider"]
        self.assertIn("MISSING_PROVIDER", validate_web_evidence(missing_provider))
        mismatch = self.evidence(source_domain="other.example")
        self.assertIn("SOURCE_DOMAIN_URL_MISMATCH", validate_web_evidence(mismatch))

    def test_stage0_kiwoom_conflict_is_diagnostic_not_blocking(self):
        row = self.row(cross={"status": "conflict"})
        row.update({"provider": "KIWOOM_REST", "provider_role": "KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED"})
        result = evidence_status(row, "2026-08-11", "READY")
        self.assertEqual(result["effective_price_status"], "KIWOOM_CANONICAL_COMPLETED_CLOSE")
        self.assertEqual(result["cross_provider_diagnostic_status"], "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE")
        self.assertFalse(result["divergence_blocking"])
        self.assertFalse(result["provider_price_averaged"])

    def test_stage0_radar_preserves_kiwoom_ready_on_diagnostic_divergence(self):
        market = self.market(cross={"status": "conflict"})
        for row in market["symbols"].values():
            row.update({"provider": "KIWOOM_REST", "provider_role": "KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED"})
        candidates = {}
        for symbol in ACTIVE_SYMBOLS:
            validated = symbol == "MVLL"
            candidates[symbol] = {
                "validation": {"status": "VALIDATED" if validated else "UNVALIDATED",
                               "evidence_packet_validated": validated,
                               "deterministic_gate_status": "PASS" if validated else "NOT_RUN",
                               "risk_controller_status": "ALLOW_REVIEW" if validated else "NOT_RUN"},
                "thesis_status": "STRONG" if validated else "UNVERIFIED",
                "valuation_status": "FAIR" if validated else "UNVERIFIED",
                "technical_status": "READY" if validated else "WATCH",
                "risk_liquidity_status": "ACCEPTABLE" if validated else "CONSTRAINED",
                "portfolio_fit_status": "FITS" if validated else "UNVERIFIED",
                "remaining_conditions": [], "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}
        runtime = {"schema_version": "1.0", "policy_version": self.radar_policy["policy_version"],
                   "last_processed_us_session": None, "last_run_at": None, "candidates": {},
                   "deliveries": {}, "order_authority": False}
        report, _ = build_radar(
            self.universe, self.registry, self.registry_validation, market,
            {"coverage_status": "COMPLETE", "events": []},
            {"candidates": candidates, "deep_research_results": {}},
            {"available_cash_usd": 0}, runtime, self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11")
        item = report["candidate_dispositions"][0]
        self.assertEqual(item["opportunity_state"], "READY")
        self.assertNotEqual(item["execution_state"], "DATA_BLOCKED")


if __name__ == "__main__":
    unittest.main()
