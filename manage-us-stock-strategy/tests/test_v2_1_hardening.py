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

from check_decision_stability import compare
from point_in_time_guard import validate_historical_evidence
from provider_resilience import fallback_eligible, update_provider_health
from run_evaluation import build_result
from screen_tactical_candidates import screen
from validate_canonical_market_record import validate_market_record
from validate_decision_record import validate_record
from validate_event_snapshot import validate_snapshot
from validate_reflection import validate_reflection
from validate_run_manifest import validate_manifest
from validate_schema_contracts import audit_directory
from validate_source_capabilities import validate_registry
from validation_common import load_json, validate_instance


class V21HardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schemas = SKILL / "schemas"
        cls.registry = load_json(ROOT / "workspace" / "policies" / "instrument_registry.json")
        cls.universe = load_json(ROOT / "workspace" / "policies" / "tactical_candidate_universe.json")
        cls.sources = load_json(ROOT / "workspace" / "policies" / "source_capabilities.json")
        cls.policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        cls.valid_decision = load_json(SKILL / "tests" / "fixtures" / "decision-record.valid.test-only.json")
        cls.negative_cases = load_json(SKILL / "tests" / "fixtures" / "v2_1" / "negative-cases.test-only.json")

    def _event_snapshot(self) -> dict:
        return {
            "schema_version": "1.0",
            "snapshot_id": "EVENT-TEST-1",
            "snapshot_mode": "LIVE",
            "generated_at": "2026-08-11T13:00:00+00:00",
            "analysis_cutoff": "2026-08-11T12:00:00+00:00",
            "market_session": "2026-08-10",
            "coverage_status": "PARTIAL",
            "coverage_notes": ["Test-only fixture."],
            "events": [{
                "event_id": "FOMC-TEST",
                "ticker": "GLOBAL",
                "event_type": "FOMC_DECISION",
                "scheduled_at": "2026-09-16T18:00:00+00:00",
                "timezone": "America/New_York",
                "announced_at": "2025-06-20T12:00:00+00:00",
                "effective_at": "2026-09-16T18:00:00+00:00",
                "retrieved_at": "2026-08-11T12:30:00+00:00",
                "source_identifier": "official_macro_provider",
                "source_type": "primary",
                "point_in_time_eligible": True,
                "confidence": "HIGH",
                "validation_status": "VALIDATED",
                "policy_effect": "CONTEXT_ONLY"
            }],
            "order_authority": False
        }

    def _manifest(self) -> dict:
        return {
            "schema_version": "1.0", "run_id": "RUN-TEST", "analysis_id": "ANALYSIS-TEST",
            "run_type": "VALIDATION_TEST", "generated_at": "2026-08-11T13:00:00+00:00",
            "analysis_cutoff": "2026-08-11T12:00:00+00:00", "market_session": "2026-08-10",
            "code_provenance": {"git_commit": "abc", "git_branch": "feature/test", "git_dirty": False, "working_tree_diff_hash": None, "skill_version": "2.1", "schema_versions": {"decision": "2.0"}, "strategy_version": "test", "policy_version": "test"},
            "llm_provenance": {"provider": None, "model": None, "model_identifier": None, "temperature": None, "max_debate_rounds": 0, "max_risk_rounds": 0},
            "input_hashes": {"market_snapshot_hash": None},
            "tool_provenance": {"python_version": "test"},
            "result_provenance": {"research_packet_hash": None, "decision_record_hash": None, "tactical_screen_hash": None, "deterministic_gate_hash": None, "deterministic_gate_result": "WAIT"},
            "secrets_recorded": False
        }

    def test_all_checked_in_schemas_use_supported_dialect(self) -> None:
        self.assertEqual(audit_directory(self.schemas), [])

    def test_schema_audit_rejects_unsupported_format_and_broken_reference(self) -> None:
        schema_dir = SKILL / "tests" / "fixtures" / "v2_1" / "broken_schemas"
        errors = audit_directory(schema_dir)
        self.assertTrue(any("unsupported format" in item for item in errors))
        self.assertTrue(any("unresolved" in item for item in errors))

    def test_valid_decision_passes_independent_schema(self) -> None:
        errors = validate_instance(self.valid_decision, self.schemas / "decision-record.schema.json")
        self.assertEqual(errors, [])

    def test_invalid_decision_fails_independent_schema(self) -> None:
        invalid = copy.deepcopy(self.valid_decision)
        invalid["research_packet"]["research_manager"]["status"] = "READY_FOR_TRADER"
        errors = validate_instance(invalid, self.schemas / "decision-record.schema.json")
        self.assertTrue(any("enum" in item for item in errors))

    def test_operational_validator_paths_cash_narrative_and_template_enum(self) -> None:
        lifecycle = self.policy["research_lifecycle_policy"]
        self.assertEqual(lifecycle["validator_path_base"], "workspace_root")
        for key in (
            "legacy_packet_validator",
            "canonical_v2_decision_validator",
            "canonical_v2_schema_contract_validator",
        ):
            self.assertTrue((ROOT / lifecycle[key]).is_file(), f"missing operational validator: {lifecycle[key]}")

        automation_prompt = (ROOT / "stock-strategy-system" / "AUTOMATION_PROMPT_EN.md").read_text(encoding="utf-8")
        self.assertNotIn("available cash is USD 0", automation_prompt)
        self.assertIn("portfolio_state.json", automation_prompt)
        self.assertIn("Missing or unverified cash", automation_prompt)

        template = (SKILL / "templates" / "research-report.md").read_text(encoding="utf-8")
        self.assertIn("RESEARCH_COMPLETE | RESEARCH_CONDITIONAL | RESEARCH_REJECTED", template)
        self.assertNotIn("READY_FOR_TRADER", template)

        readme = (ROOT / "stock-strategy-system" / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("validate_research_cycle.py", readme)
        self.assertIn("manage-us-stock-strategy/scripts/validate_decision_record.py", readme)

    def test_source_capability_registry(self) -> None:
        errors = validate_registry(self.sources, self.schemas / "source-capability.schema.json")
        self.assertEqual(errors, [])

    def test_tactical_screen_fails_closed_without_market_data(self) -> None:
        events = self._event_snapshot()
        events["coverage_status"] = "EVENT_DATA_INCOMPLETE"
        result = screen(self.universe, self.registry, {"symbols": {}}, events, generated_at="2026-08-11T13:00:00+00:00", analysis_cutoff="2026-08-11T12:59:00+00:00", market_session="2026-08-10")
        self.assertEqual(result["final_status"], "DATA_INCOMPLETE")
        self.assertEqual(result["shortlist"], [])
        self.assertFalse(result["order_authority"])
        self.assertIn("event_risk", self.universe["screening"]["ordered_gates"])

    def test_tactical_screen_rejects_present_but_unvalidated_market_row(self) -> None:
        market = {
            "session": {
                "official_calendar_verified": False,
                "calendar_verification_status": "unverified",
                "regular_session_complete": True,
                "us_session_date": "2026-08-10",
            },
            "symbols": {"NBIS": {"bar_date": "2026-08-10", "close": 100.0}},
        }
        result = screen(self.universe, self.registry, market, self._event_snapshot(), generated_at="2026-08-11T13:00:00+00:00", analysis_cutoff="2026-08-11T12:59:00+00:00", market_session="2026-08-10")
        row = next(item for item in result["stage_one"] if item["symbol"] == "NBIS")
        self.assertEqual(row["screen_status"], "REJECTED")
        self.assertEqual(row["evidence"], "FAIL")
        self.assertTrue(any("calendar" in item for item in row["reasons"]))

    def test_tactical_screen_accepts_only_fully_validated_market_row(self) -> None:
        market = {
            "session": {
                "official_calendar_verified": True,
                "calendar_verification_status": "verified",
                "regular_session_complete": True,
                "us_session_date": "2026-08-10",
            },
            "symbols": {"NBIS": {
                "bar_date": "2026-08-10",
                "open": 99.0,
                "high": 102.0,
                "low": 98.0,
                "close": 101.0,
                "close_prev": 100.0,
                "volume": 1000000,
                "corporate_action_unresolved": False,
                "indicator_validation": {"status": "passed", "errors": []},
                "quote_crosscheck": {"status": "verified", "independent_of_builder": True, "bar_date": "2026-08-10"},
            }},
        }
        result = screen(self.universe, self.registry, market, self._event_snapshot(), generated_at="2026-08-11T13:00:00+00:00", analysis_cutoff="2026-08-11T12:59:00+00:00", market_session="2026-08-10")
        row = next(item for item in result["stage_one"] if item["symbol"] == "NBIS")
        self.assertEqual(row["screen_status"], "SURVIVES")
        self.assertEqual(row["technical"], "VALIDATED")
        self.assertIn("NBIS", result["shortlist"])

    def test_provider_failures_open_or_degrade_without_retry_bypass(self) -> None:
        rate_limit = update_provider_health({}, "HTTP_429", "2026-08-11T12:00:00+00:00")
        mismatch = update_provider_health({}, "SCHEMA_MISMATCH", "2026-08-11T12:00:00+00:00")
        self.assertEqual(rate_limit["circuit_state"], "OPEN")
        self.assertEqual(mismatch["circuit_state"], "DEGRADED")
        allowed, reasons = fallback_eligible(None, historical=True, session_compatible=False, timestamp_compatible=False, provenance_retained=False)
        self.assertFalse(allowed)
        self.assertGreaterEqual(len(reasons), 4)

    def test_fallback_requires_explicit_evidence_type_capability(self) -> None:
        yfinance = next(item for item in self.sources["providers"] if item["provider"] == "yfinance")
        allowed, reasons = fallback_eligible(yfinance, historical=True, session_compatible=True, timestamp_compatible=True, provenance_retained=True)
        self.assertFalse(allowed)
        self.assertTrue(any("evidence type" in item for item in reasons))
        allowed, reasons = fallback_eligible(yfinance, evidence_type="COMPLETED_DAILY_OHLCV", historical=True, session_compatible=True, timestamp_compatible=True, provenance_retained=True)
        self.assertTrue(allowed)
        self.assertEqual(reasons, [])

    def test_current_reddit_is_rejected_in_historical_run(self) -> None:
        evidence = [{"provider": "reddit", "published_at_utc": "2026-08-01T12:00:00+00:00", "effective_at_utc": "2026-08-01T12:00:00+00:00", "record_type": "VERIFIED_FACT"}]
        errors = validate_historical_evidence(evidence, "2026-08-02T12:00:00+00:00", self.sources)
        self.assertTrue(any("social" in item or "point-in-time" in item for item in errors))

    def test_future_published_article_is_rejected(self) -> None:
        evidence = [{"provider": "official_macro_provider", "published_at_utc": "2026-08-03T12:00:00+00:00", "effective_at_utc": "2026-08-03T12:00:00+00:00", "record_type": "VERIFIED_FACT"}]
        errors = validate_historical_evidence(evidence, "2026-08-02T12:00:00+00:00", self.sources)
        self.assertTrue(any("future-published" in item for item in errors))

    def test_valid_event_snapshot(self) -> None:
        self.assertEqual(validate_snapshot(self._event_snapshot(), self.schemas / "event-snapshot.schema.json"), [])

    def test_missing_event_date_is_rejected(self) -> None:
        snapshot = self._event_snapshot()
        del snapshot["events"][0]["scheduled_at"]
        errors = validate_snapshot(snapshot, self.schemas / "event-snapshot.schema.json")
        self.assertTrue(any("scheduled_at" in item for item in errors))

    def test_event_calendar_session_mismatch_is_rejected(self) -> None:
        snapshot = self._event_snapshot()
        snapshot["market_session"] = "2026-08-12"
        errors = validate_snapshot(snapshot, self.schemas / "event-snapshot.schema.json")
        self.assertTrue(any("session" in item for item in errors))

    def test_historical_event_rejects_future_known_information(self) -> None:
        snapshot = self._event_snapshot()
        snapshot["snapshot_mode"] = "HISTORICAL"
        snapshot["events"][0]["announced_at"] = "2026-08-12T12:00:00+00:00"
        errors = validate_snapshot(snapshot, self.schemas / "event-snapshot.schema.json")
        self.assertTrue(any("future-known" in item for item in errors))

    def test_event_shadow_fixture_surfaces_multiple_tickers_without_order_authority(self) -> None:
        snapshot = self._event_snapshot()
        snapshot["coverage_status"] = "PARTIAL"
        snapshot["coverage_notes"] = ["Test-only multi-ticker corporate-event coverage."]
        snapshot["events"] = []
        for index, symbol in enumerate(("NBIS", "FSLY", "RBRK"), start=1):
            snapshot["events"].append({
                "event_id": f"{symbol}-EARNINGS-TEST",
                "ticker": symbol,
                "event_type": "EARNINGS_RELEASE",
                "scheduled_at": f"2026-08-{20 + index:02d}T16:05:00-04:00",
                "timezone": "America/New_York",
                "announced_at": "2026-08-01T12:00:00+00:00",
                "effective_at": f"2026-08-{20 + index:02d}T16:05:00-04:00",
                "retrieved_at": "2026-08-11T11:30:00+00:00",
                "source_identifier": f"https://example.test/{symbol.lower()}/ir",
                "source_type": "primary",
                "point_in_time_eligible": True,
                "confidence": "HIGH",
                "validation_status": "VALIDATED",
                "policy_effect": "CONTEXT_ONLY",
            })
        self.assertEqual(validate_snapshot(snapshot, self.schemas / "event-snapshot.schema.json"), [])
        self.assertEqual({item["ticker"] for item in snapshot["events"]}, {"NBIS", "FSLY", "RBRK"})
        self.assertFalse(snapshot["order_authority"])

    def test_stale_completed_close_is_rejected(self) -> None:
        record = {"symbol": "SOXL", "field": "close", "value": 100.0, "units": "USD", "exchange_session": "2026-08-08", "timestamp": "2026-08-08T20:00:00+00:00", "provider": "yfinance", "retrieved_at": "2026-08-11T12:00:00+00:00", "raw_or_adjusted": "RAW", "quality_status": "VALIDATED", "source_identifier": "yfinance"}
        errors = validate_market_record(record, "2026-08-10", self.schemas / "canonical-market-record.schema.json")
        self.assertTrue(any("stale" in item for item in errors))

    def test_unauthorized_leveraged_new_buy_cannot_be_eligible(self) -> None:
        record = copy.deepcopy(self.valid_decision)
        record["symbol"] = "SOXL"
        record["research_packet"]["symbol"] = "SOXL"
        record["trader_proposal"]["symbol"] = "SOXL"
        record["trader_proposal"]["action"] = "BUY_REVIEW"
        record["risk_review"]["input_action"] = "BUY_REVIEW"
        record["risk_review"]["output_action"] = "BUY_REVIEW"
        record["portfolio_decision"]["action"] = "BUY_REVIEW"
        record["final_action"] = "BUY_REVIEW"
        result = validate_record(record, self.registry, self.universe)
        self.assertNotEqual(result["status"], "ELIGIBLE_FOR_REVIEW")
        self.assertTrue(any("new buy" in item for item in result["warnings"]))

    def test_unauthorized_quantity_is_rejected(self) -> None:
        record = copy.deepcopy(self.valid_decision)
        record["trader_proposal"]["quantity"] = 1
        result = validate_record(record, self.registry, self.universe)
        self.assertEqual(result["status"], "REJECTED")
        self.assertTrue(any("quantity" in item for item in result["errors"]))

    def test_sell_without_verified_holding_is_rejected(self) -> None:
        record = copy.deepcopy(self.valid_decision)
        record["trader_proposal"]["action"] = "REDUCTION_REVIEW"
        record["risk_review"]["input_action"] = "REDUCTION_REVIEW"
        record["risk_review"]["output_action"] = "REDUCTION_REVIEW"
        record["portfolio_decision"]["action"] = "REDUCTION_REVIEW"
        record["final_action"] = "REDUCTION_REVIEW"
        result = validate_record(record, self.registry, self.universe, {"holdings": {}})
        self.assertEqual(result["status"], "REJECTED")
        self.assertTrue(any("not allowed for position status NOT_HELD" in item for item in result["errors"]))

    def test_reflection_policy_mutation_is_rejected(self) -> None:
        errors = validate_reflection({"lessons": ["test"], "policy_version": "mutated"})
        self.assertTrue(errors)

    def test_research_packet_cannot_escalate_alert_grade(self) -> None:
        harness = self.policy["decision_harness"]
        self.assertFalse(harness["packet_to_candidate_adapter_enabled"])
        self.assertEqual(harness["maximum_validator_grade"], "B")

    def test_run_manifest_and_secret_guard(self) -> None:
        manifest = self._manifest()
        self.assertEqual(validate_manifest(manifest, self.schemas / "run-manifest.schema.json"), [])
        manifest["tool_provenance"]["api_key"] = "secret-value"
        self.assertTrue(any("secret" in item for item in validate_manifest(manifest, self.schemas / "run-manifest.schema.json")))

    def test_repeated_decision_stability(self) -> None:
        records = [copy.deepcopy(self.valid_decision) for _ in range(3)]
        self.assertEqual(compare(records)["status"], "PASS")
        records[2]["risk_review"]["verdict"] = "VETO"
        self.assertEqual(compare(records)["status"], "DECISION_STABILITY_RISK")

    def test_evaluation_layer_one_dominates(self) -> None:
        config = {"evaluation_id": "EVAL-TEST", "analysis_cutoff": "2026-08-11T12:00:00+00:00", "safety_checks": {"look_ahead": "FAIL"}, "decision_quality_checks": {"evidence_accuracy": "PASS"}, "transaction_cost_status": "ASSUMPTION_REQUIRED", "benchmark_status": "ASSUMPTION_REQUIRED"}
        result = build_result(config)
        self.assertEqual(result["overall_merge_gate"], "FAIL")
        self.assertEqual(result["economic_performance"]["status"], "ASSUMPTION_REQUIRED")

    def test_evaluation_empty_checks_fail_closed_as_not_tested(self) -> None:
        config = {"evaluation_id": "EVAL-EMPTY", "analysis_cutoff": "2026-08-11T12:00:00+00:00"}
        result = build_result(config)
        self.assertEqual(result["safety"]["status"], "NOT_TESTED")
        self.assertEqual(result["decision_quality"]["status"], "NOT_TESTED")
        self.assertEqual(result["overall_merge_gate"], "BLOCKED")

    def test_negative_fixture_lists_all_required_cases(self) -> None:
        ids = {item["id"] for item in self.negative_cases["cases"]}
        expected = {"yfinance_rate_limit_failure", "provider_schema_mismatch", "current_reddit_in_historical_run", "future_published_article", "missing_earnings_event_date", "event_calendar_session_mismatch", "stale_completed_close", "unauthorized_leveraged_new_buy", "unauthorized_quantity", "sell_without_verified_holding", "reflection_policy_mutation", "research_packet_alert_grade_escalation"}
        self.assertEqual(ids, expected)


if __name__ == "__main__":
    unittest.main()
