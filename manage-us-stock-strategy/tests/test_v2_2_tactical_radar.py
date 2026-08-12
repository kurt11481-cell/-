from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "manage-us-stock-strategy"
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_tactical_opportunity_radar import ACTIVE_SYMBOLS, build_radar
from validate_registry_consistency import validate_registry_consistency
from validation_common import load_json, validate_instance


class V22TacticalRadarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.universe = load_json(ROOT / "workspace" / "policies" / "tactical_candidate_universe.json")
        cls.registry_path = ROOT / "workspace" / "policies" / "instrument_registry.json"
        cls.registry = load_json(cls.registry_path)
        cls.radar_policy = load_json(ROOT / "workspace" / "policies" / "tactical_radar_policy.json")
        cls.alert_policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        cls.registry_validation = validate_registry_consistency(cls.registry, cls.alert_policy, cls.registry_path)

    def _market(self, ready_count: int = 0) -> dict:
        rows = {}
        for index, symbol in enumerate(ACTIVE_SYMBOLS):
            rows[symbol] = {
                "bar_date": "2026-08-11", "open": 99.0, "high": 102.0, "low": 98.0,
                "close": 101.0, "close_prev": 100.0, "volume": 1000000,
                "corporate_action_unresolved": False,
                "breakout_acceptance_confirmed": False,
                "ema10_reclaim_confirmed": False,
                "ema20_reclaim_confirmed": index < ready_count,
                "indicator_validation": {"status": "passed", "errors": []},
                "quote_crosscheck": {"status": "verified", "independent_of_builder": True, "bar_date": "2026-08-11"},
            }
        return {
            "session": {"official_calendar_verified": True, "calendar_verification_status": "verified_trading_day", "regular_session_complete": True, "us_session_date": "2026-08-11", "expected_us_session_date": "2026-08-11"},
            "symbols": rows,
        }

    def _events(self) -> dict:
        return {"coverage_status": "COMPLETE", "events": []}

    def _runtime(self) -> dict:
        return {"schema_version": "1.0", "policy_version": self.radar_policy["policy_version"], "last_processed_us_session": None, "last_run_at": None, "candidates": {}, "deliveries": {}, "order_authority": False}

    def _context(self, ready_count: int = 0, cash: float = 10000.0) -> dict:
        values = {}
        for index, symbol in enumerate(ACTIVE_SYMBOLS):
            if index < ready_count:
                values[symbol] = {"validation": {"status": "VALIDATED", "evidence_packet_validated": True, "deterministic_gate_status": "PASS", "risk_controller_status": "ALLOW_REVIEW"}, "thesis_status": "STRONG", "valuation_status": "FAIR", "technical_status": "READY", "risk_liquidity_status": "ACCEPTABLE", "portfolio_fit_status": "FITS", "remaining_conditions": [], "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}
            else:
                values[symbol] = {"validation": {"status": "UNVALIDATED", "evidence_packet_validated": False, "deterministic_gate_status": "NOT_RUN", "risk_controller_status": "NOT_RUN"}, "thesis_status": "UNVERIFIED", "valuation_status": "UNVERIFIED", "technical_status": "WATCH", "risk_liquidity_status": "CONSTRAINED", "portfolio_fit_status": "UNVERIFIED", "remaining_conditions": ["THESIS_RESEARCH"], "next_review_trigger": "THESIS_RESEARCH"}
        return {"available_cash_usd": cash, "candidates": values, "deep_research_results": {}}

    def _run(self, context: dict, *, universe=None, registry=None, validation=None, runtime=None):
        return build_radar(
            universe or self.universe, registry or self.registry, validation or self.registry_validation,
            self._market(sum(1 for value in context["candidates"].values() if value.get("technical_status") == "READY")),
            self._events(), context, {"available_cash_usd": context.get("available_cash_usd")},
            runtime or self._runtime(), self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11",
        )

    def test_active_universe_is_exactly_seven_and_retired_records_are_preserved(self) -> None:
        active = [symbol for symbol, row in self.universe["candidates"].items() if row["candidate_status"] == "active"]
        self.assertEqual(active, list(ACTIVE_SYMBOLS))
        for symbol in ("RBRK", "NET", "MDB", "DDOG", "SNOW", "CRWD", "PANW", "PLTR"):
            self.assertIn(symbol, self.registry["instruments"])
            self.assertEqual(self.registry["instruments"][symbol]["candidate_status"], "inactive")
            self.assertFalse(self.registry["instruments"][symbol]["watchlist_approved"])

    def test_primary_identity_records_for_initial_exploration_symbols(self) -> None:
        for symbol in ("TOST", "NOW", "FSLY"):
            row = self.registry["instruments"][symbol]
            self.assertEqual(row["identity_verification_status"], "VERIFIED")
            self.assertTrue(row["official_identity_source_url"].startswith("https://www.sec.gov/"))
            self.assertTrue(row["legal_issuer_name"])
            self.assertEqual(row["trading_currency"], "USD")

    def test_watchlist_approval_is_not_new_buy_approval(self) -> None:
        report, _ = self._run(self._context(ready_count=1))
        row = report["candidate_dispositions"][0]
        self.assertEqual(row["opportunity_state"], "READY")
        self.assertEqual(row["execution_state"], "NOT_APPROVED")
        self.assertIsNone(row["quantity"])

    def test_ready_opportunity_survives_cash_block(self) -> None:
        universe = copy.deepcopy(self.universe)
        registry = copy.deepcopy(self.registry)
        universe["candidates"]["MVLL"]["new_buy_approved"] = True
        registry["instruments"]["MVLL"]["new_buy_instrument_approved"] = True
        report, _ = self._run(self._context(ready_count=1, cash=0.0), universe=universe, registry=registry)
        row = report["candidate_dispositions"][0]
        self.assertEqual(row["opportunity_state"], "READY")
        self.assertEqual(row["execution_state"], "CASH_BLOCKED")
        self.assertIsNone(row["quantity"])

    def test_identity_incomplete_fails_closed_but_verified_identity_passes(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["instruments"]["TOST"]["identity_status"] = "identity_incomplete"
        report, _ = self._run(self._context(ready_count=7), registry=registry)
        tost = next(item for item in report["candidate_dispositions"] if item["ticker"] == "TOST")
        now = next(item for item in report["candidate_dispositions"] if item["ticker"] == "NOW")
        self.assertEqual(tost["opportunity_state"], "DATA_BLOCKED")
        self.assertNotEqual(now["opportunity_state"], "DATA_BLOCKED")

    def test_registry_drift_fails_execution_closed_without_erasing_research(self) -> None:
        drift = copy.deepcopy(self.registry_validation)
        drift["status"] = "POLICY_REGISTRY_MISMATCH"
        report, _ = self._run(self._context(ready_count=1), validation=drift)
        row = report["candidate_dispositions"][0]
        self.assertEqual(row["opportunity_state"], "READY")
        self.assertEqual(row["execution_state"], "DATA_BLOCKED")
        self.assertEqual(report["registry_status"], "POLICY_REGISTRY_MISMATCH")

    def test_real_registry_reference_is_consistent(self) -> None:
        self.assertEqual(self.registry_validation["status"], "VALIDATED")
        broken = copy.deepcopy(self.alert_policy)
        broken["decision_harness"]["instrument_registry_authority"]["required_canonical_sha256"] = "0" * 64
        result = validate_registry_consistency(self.registry, broken, self.registry_path)
        self.assertEqual(result["status"], "POLICY_REGISTRY_MISMATCH")

    def test_registry_hash_is_line_ending_independent(self) -> None:
        temporary = ROOT / "workspace" / "outputs" / "registry-line-ending-test.json"
        try:
            temporary.write_text(json.dumps(self.registry, ensure_ascii=False, indent=2).replace("\n", "\r\n") + "\r\n", encoding="utf-8")
            result = validate_registry_consistency(self.registry, self.alert_policy, temporary)
            self.assertEqual(result["status"], "VALIDATED")
        finally:
            temporary.unlink(missing_ok=True)

    def test_shortlist_semantics_for_five_three_and_one_survivors(self) -> None:
        for ready_count, expected in ((7, 5), (3, 3), (1, 1)):
            report, _ = self._run(self._context(ready_count=ready_count))
            self.assertEqual(len(report["deep_research_shortlist"]), expected)
            self.assertEqual(report["shortlist_below_target_due_to_gates"], expected < 3)
            self.assertEqual(len(report["screen_survivors"]), 7)
            self.assertTrue(all("reason" in item for item in report["deep_research_skipped"]))

    def test_untrusted_context_cannot_upgrade_deterministic_technical_state(self) -> None:
        context = self._context(ready_count=1)
        market = self._market(ready_count=0)
        report, _ = build_radar(self.universe, self.registry, self.registry_validation, market, self._events(),
            context, {"available_cash_usd": 10000.0}, self._runtime(), self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11")
        self.assertEqual(report["candidate_dispositions"][0]["technical_status"], "WATCH")
        self.assertNotEqual(report["candidate_dispositions"][0]["opportunity_state"], "READY")

    def test_context_only_global_event_does_not_downgrade_ready(self) -> None:
        events = {"coverage_status": "COMPLETE", "events": [{"ticker": "GLOBAL", "event_type": "CPI", "validation_status": "VALIDATED", "policy_effect": "CONTEXT_ONLY"}]}
        context = self._context(ready_count=1)
        report, _ = build_radar(self.universe, self.registry, self.registry_validation, self._market(1), events,
            context, {"available_cash_usd": 10000.0}, self._runtime(), self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-11")
        self.assertEqual(report["candidate_dispositions"][0]["opportunity_state"], "READY")
        self.assertEqual(report["candidate_dispositions"][0]["event_policy_effect"], "CONTEXT_ONLY")

    def test_stale_session_is_rejected_and_cannot_notify(self) -> None:
        context = self._context(ready_count=1)
        report, _ = build_radar(self.universe, self.registry, self.registry_validation, self._market(1), self._events(),
            context, {"available_cash_usd": 10000.0}, self._runtime(), self.radar_policy,
            generated_at="2026-08-12T00:45:00+00:00", analysis_cutoff="2026-08-12T00:44:00+00:00",
            market_session="2026-08-11", latest_completed_session="2026-08-12")
        self.assertEqual(report["session_gate"], "DATA_INCOMPLETE")
        self.assertEqual(report["final_conclusion"], "DATA_INCOMPLETE")
        self.assertFalse(any(item["notify"] for item in report["transitions"]))

    def test_unapproved_condition_id_fails_closed(self) -> None:
        context = self._context(ready_count=1)
        context["candidates"]["MVLL"]["remaining_conditions"] = ["PRICE_ABOVE_123_45"]
        report, _ = self._run(context)
        row = report["candidate_dispositions"][0]
        self.assertEqual(row["opportunity_state"], "DATA_BLOCKED")
        self.assertIn("UNAPPROVED_CONDITION_ID", row["remaining_conditions"])

    def test_preferred_requires_validated_deep_research(self) -> None:
        context = self._context(ready_count=1)
        report, _ = self._run(context)
        self.assertEqual(report["deep_research_shortlist"], ["MVLL"])
        self.assertIsNone(report["preferred_candidate"])
        context["deep_research_results"] = {"MVLL": {"status": "VALIDATED", "research_packet_hash": "a" * 64}}
        report, _ = self._run(context)
        self.assertEqual(report["preferred_candidate"], "MVLL")

    def test_cash_and_approval_blockers_are_both_visible(self) -> None:
        report, _ = self._run(self._context(ready_count=1, cash=0.0))
        row = report["candidate_dispositions"][0]
        self.assertEqual(row["execution_state"], "NOT_APPROVED")
        self.assertIn("NEW_BUY_INSTRUMENT_APPROVAL", row["remaining_conditions"])
        self.assertIn("VERIFIED_AVAILABLE_CASH", row["remaining_conditions"])

    def test_transition_and_duplicate_session_dedup(self) -> None:
        report, updated = self._run(self._context(ready_count=1))
        mvll = report["transitions"][0]
        self.assertEqual(mvll["transition_type"], "NEW_READY")
        self.assertTrue(mvll["notify"])
        second, _ = self._run(self._context(ready_count=1), runtime=updated)
        self.assertEqual(second["session_gate"], "NO_NEW_SESSION")
        self.assertEqual(second["transitions"][0]["transition_type"], "NO_MATERIAL_CHANGE")
        self.assertFalse(second["transitions"][0]["notify"])

    def test_report_and_runtime_validate_and_inputs_are_not_mutated(self) -> None:
        context = self._context(ready_count=2)
        original = copy.deepcopy(context)
        report, runtime = self._run(context)
        self.assertEqual(context, original)
        self.assertEqual(validate_instance(report, SKILL / "schemas" / "tactical-radar-report.schema.json"), [])
        self.assertEqual(validate_instance(runtime, SKILL / "schemas" / "tactical-radar-state.schema.json"), [])
        self.assertFalse(report["order_authority"])


if __name__ == "__main__":
    unittest.main()
