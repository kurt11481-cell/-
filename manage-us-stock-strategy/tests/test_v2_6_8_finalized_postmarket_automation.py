from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(TESTS))

from automation_delivery import update_delivery
from finalized_postmarket_automation import (
    event_and_provider_readiness,
    suppress_duplicate_urgent,
    validate_finalization_evidence,
    validate_scoped_provider_limits,
)
from session_aware_market_data import apply_extended_hours_guard, kiwoom_broker_quote_observation
from shadow_acceptance import apply_attempt, classify_attempt, critical_violations, initial_progress
from v2_6_test_helpers import valid_scheduled_attempt
from validation_common import file_hash, load_json, validate_instance


class V268FinalizedPostMarketAutomationTests(unittest.TestCase):
    def setUp(self):
        self.progress = initial_progress("a" * 64, "2026-08-14T00:00:00Z")
        self.runtime = load_json(ROOT / "workspace/state/automation_delivery_runtime.json")
        self.scope = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")

    def test_auto_01_preliminary_run_cannot_count(self):
        raw = valid_scheduled_attempt(run_phase="POST_MARKET_PRELIMINARY")
        result = classify_attempt(raw, progress=self.progress)
        self.assertFalse(result["counts_as_valid_session"])
        self.assertIn("PRELIMINARY_RUN_NOT_COUNTABLE", result["exclusion_reasons"])

    def test_auto_02_preliminary_run_cannot_verify_delivery(self):
        result = update_delivery(self.runtime, "morning_portfolio_strategy",
            attempted_at="2026-08-14T01:15:00Z", success=True,
            completed_session="2026-08-13", output_artifact="workspace/outputs/test/report.json",
            notification_status="DELIVERED", git_commit="a" * 40,
            policy_version="2026-08-14-finalized-postmarket-v1",
            portfolio_hash_before="b" * 64, portfolio_hash_after="b" * 64,
            run_phase="POST_MARKET_PRELIMINARY", finalization_status="VALIDATED",
            all_critical_bars_finalized=True, actual_scheduled_run=True,
            delivery_id="delivery-preliminary")
        row = result["automations"]["morning_portfolio_strategy"]
        self.assertEqual(row["status"], "FIRST_RUN_PENDING")
        self.assertNotEqual(row["status"], "DELIVERY_VERIFIED")

    def test_auto_03_finalized_run_requires_finalized_bars(self):
        valid = valid_scheduled_attempt()
        self.assertTrue(classify_attempt(valid, progress=self.progress)["counts_as_valid_session"])
        pending = copy.deepcopy(valid)
        pending["finalization_evidence"]["critical_bars"]["SOXL"]["bar_finalized"] = False
        pending["finalization_evidence"]["all_critical_bars_finalized"] = False
        result = classify_attempt(pending, progress=self.progress)
        self.assertFalse(result["counts_as_valid_session"])
        self.assertIn("BAR_NOT_FINALIZED:SOXL", result["exclusion_reasons"])

    def test_auto_04_extended_quote_cannot_overwrite_completed_bar(self):
        quote = kiwoom_broker_quote_observation(ticker="SOXL", reported_session="2026-08-13",
            price=140.0, provider_timestamp="2026-08-13T18:30:00-04:00",
            explicit_session_type="AFTER_HOURS")
        guarded = apply_extended_hours_guard(prior_state="WATCH", requested_state="READY")
        self.assertFalse(quote["bar_finalized"])
        self.assertFalse(quote["daily_indicator_authority"])
        self.assertEqual(guarded["resulting_state"], "WATCH")

    def test_auto_05_phase_neutral_urgent_dedup(self):
        preliminary = {"ticker": "SOXL", "run_phase": "POST_MARKET_PRELIMINARY",
            "event_type": "READY", "strategy_state": "HOLD", "opportunity_state": "READY",
            "signal_fingerprint": "same"}
        finalized = dict(preliminary, run_phase="POST_MARKET_FINALIZED")
        self.assertTrue(suppress_duplicate_urgent([preliminary], finalized))

    def test_auto_06_fsly_fallback_follows_scope_manifest(self):
        evidence = valid_scheduled_attempt()["finalization_evidence"]
        self.assertEqual(validate_scoped_provider_limits(self.scope, evidence), [])
        broken = copy.deepcopy(evidence)
        broken["critical_bars"]["FSLY"]["technical_history_provider"] = "KIWOOM_REST"
        self.assertIn("FSLY_FALLBACK_NOT_APPLIED", validate_scoped_provider_limits(self.scope, broken))
        raw = valid_scheduled_attempt()
        raw["finalization_evidence"] = broken
        self.assertFalse(classify_attempt(raw, progress=self.progress,
                                          provider_scope_policy=self.scope)["counts_as_valid_session"])
        bad_hash = copy.deepcopy(evidence)
        bad_hash["provider_scope_manifest_hash"] = "0" * 64
        self.assertIn("PROVIDER_SCOPE_MANIFEST_HASH_MISMATCH",
                      validate_scoped_provider_limits(self.scope, bad_hash))

    def test_auto_07_mvll_decision_class_remains_blocked(self):
        evidence = valid_scheduled_attempt()["finalization_evidence"]
        self.assertEqual(validate_scoped_provider_limits(self.scope, evidence), [])
        broken = copy.deepcopy(evidence)
        broken["critical_bars"]["MVLL"]["blocked_decision_classes"] = []
        self.assertIn("MVLL_DECISION_CLASS_NOT_ISOLATED", validate_scoped_provider_limits(self.scope, broken))

    def test_auto_08_event_incomplete_does_not_change_provider_readiness(self):
        value = event_and_provider_readiness("KIWOOM_PRIMARY_GUARDED_SCOPED_READY", "EVENT_DATA_INCOMPLETE")
        self.assertEqual(value["provider_readiness_status"], "KIWOOM_PRIMARY_GUARDED_SCOPED_READY")
        self.assertEqual(value["event_readiness_status"], "EVENT_REVIEW_PENDING")
        raw = valid_scheduled_attempt()
        raw["finalization_evidence"]["event_readiness_status"] = "EVENT_REVIEW_PENDING"
        self.assertTrue(classify_attempt(raw, progress=self.progress)["counts_as_valid_session"])
        raw["finalization_evidence"]["provider_readiness_status"] = "DATA_INCOMPLETE"
        self.assertFalse(classify_attempt(raw, progress=self.progress)["counts_as_valid_session"])

    def test_auto_09_finalization_pending_is_observed_not_counted(self):
        raw = valid_scheduled_attempt()
        raw["finalization_evidence"]["finalization_status"] = "FINALIZATION_PENDING"
        attempt = classify_attempt(raw, progress=self.progress)
        updated = apply_attempt(self.progress, attempt)
        self.assertFalse(attempt["counts_as_valid_session"])
        self.assertEqual(updated["observed_attempts"], 1)
        self.assertEqual(updated["valid_shadow_sessions"], 0)

    def test_auto_10_portfolio_hash_remains_unchanged(self):
        path = ROOT / "stock-strategy-system/portfolio_state.json"
        before = file_hash(path)
        classify_attempt(valid_scheduled_attempt(), progress=self.progress)
        self.assertEqual(before, file_hash(path))

    def test_auto_11_order_authority_remains_false(self):
        raw = valid_scheduled_attempt()
        self.assertEqual(critical_violations(raw["report"],
            portfolio_hash_before=raw["portfolio_hash_before"],
            portfolio_hash_after=raw["portfolio_hash_after"]), [])
        self.assertFalse(raw["finalization_evidence"]["order_authority"])

    def test_policy_and_evidence_schemas(self):
        policy = load_json(ROOT / "workspace/policies/finalized_postmarket_automation_policy.json")
        self.assertEqual(validate_instance(policy,
            ROOT / "manage-us-stock-strategy/schemas/finalized-postmarket-automation-policy.schema.json"), [])
        evidence = valid_scheduled_attempt()["finalization_evidence"]
        self.assertEqual(validate_finalization_evidence(evidence, "2026-08-12"), [])
        self.assertEqual(validate_instance(evidence,
            ROOT / "manage-us-stock-strategy/schemas/finalized-postmarket-evidence.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
