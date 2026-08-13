from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from holding_research import activate_baseline, compile_context, recompute_hashes, validate_baseline
from validation_common import canonical_hash, load_json, validate_instance
from v2_6_test_helpers import valid_baseline, valid_overlay


BASELINE_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json"
COMPILED_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/compiled-holding-research-context.schema.json"


class V26HoldingResearchBaselineTests(unittest.TestCase):
    def validate(self, ticker="NBIS"):
        return validate_baseline(valid_baseline(ticker), BASELINE_SCHEMA)

    def compile(self, ticker="NBIS", baseline=None, overlay=None):
        baseline = baseline or valid_baseline(ticker)
        overlay = overlay or valid_overlay(ticker)
        registry = load_json(ROOT / "workspace/policies/instrument_registry.json")
        profile = copy.deepcopy(registry["instruments"][ticker])
        profile["ticker"] = ticker
        return compile_context(profile, baseline, overlay, baseline_schema=BASELINE_SCHEMA)

    def test_hrb_01_valid_nbis_direct_issuer_baseline_passes(self):
        self.assertEqual(self.validate("NBIS")["validation_status"], "PASSED")

    def test_hrb_02_valid_mvll_product_plus_underlying_passes(self):
        baseline = valid_baseline("MVLL")
        self.assertEqual(baseline["linked_components"][0]["ticker"], "MRVL")
        self.assertEqual(validate_baseline(baseline, BASELINE_SCHEMA)["validation_status"], "PASSED")

    def test_hrb_03_valid_soxl_sector_baseline_passes(self):
        baseline = valid_baseline("SOXL")
        self.assertEqual(baseline["linked_components"][0]["confirmation_mode"], "DIRECTION_ONLY")
        self.assertEqual(validate_baseline(baseline, BASELINE_SCHEMA)["validation_status"], "PASSED")

    def test_hrb_04_invalid_research_packet_hash_rejected(self):
        value = valid_baseline(); value["research_packet_hash"] = "f" * 64
        self.assertIn("RESEARCH_PACKET_HASH_MISMATCH", validate_baseline(value, BASELINE_SCHEMA)["errors"])

    def test_hrb_05_invalid_baseline_hash_rejected(self):
        value = valid_baseline(); value["baseline_hash"] = "f" * 64
        self.assertIn("BASELINE_HASH_MISMATCH", validate_baseline(value, BASELINE_SCHEMA)["errors"])

    def test_hrb_06_baseline_without_claim_rejected(self):
        value = valid_baseline(); value["claims"] = []; value["claim_ids"] = []; value = recompute_hashes(value)
        self.assertEqual(validate_baseline(value, BASELINE_SCHEMA)["validation_status"], "FAILED")

    def test_hrb_07_no_counter_case_rejected(self):
        value = valid_baseline(); value["strongest_counter_case"] = ""; value = recompute_hashes(value)
        self.assertEqual(validate_baseline(value, BASELINE_SCHEMA)["validation_status"], "FAILED")

    def test_hrb_08_no_invalidation_rejected(self):
        value = valid_baseline(); value["invalidation_conditions"] = []; value = recompute_hashes(value)
        self.assertEqual(validate_baseline(value, BASELINE_SCHEMA)["validation_status"], "FAILED")

    def test_hrb_09_no_evidence_cutoff_rejected(self):
        value = valid_baseline(); value["evidence_cutoff"] = ""; value = recompute_hashes(value)
        self.assertEqual(validate_baseline(value, BASELINE_SCHEMA)["validation_status"], "FAILED")

    def test_hrb_10_validated_insufficient_cannot_hold(self):
        value = valid_baseline(); value["content_status"] = "INSUFFICIENT"; value = recompute_hashes(value)
        result = self.compile(baseline=value)
        self.assertEqual(result["strategy_state"], "STRATEGY_REFRESH_REQUIRED")

    def test_hrb_11_unverified_thesis_cannot_hold(self):
        value = valid_baseline(); value["thesis_status"] = "UNVERIFIED"; value = recompute_hashes(value)
        self.assertEqual(self.compile(baseline=value)["strategy_state"], "STRATEGY_REFRESH_REQUIRED")
        value = valid_baseline(); value["valuation_status"] = "UNVERIFIED"; value = recompute_hashes(value)
        self.assertEqual(self.compile(baseline=value)["strategy_state"], "STRATEGY_REFRESH_REQUIRED")

    def test_hrb_12_baseline_technical_view_cannot_override_overlay(self):
        value = valid_baseline(); value["technical_view_at_baseline"] = "READY"; value = recompute_hashes(value)
        self.assertEqual(self.compile(baseline=value, overlay=valid_overlay(technical_status="DETERIORATING"))["technical_status"], "DETERIORATING")

    def test_hrb_13_baseline_portfolio_fit_cannot_override_overlay(self):
        value = valid_baseline(); value["portfolio_fit_view_at_baseline"] = "FITS"; value = recompute_hashes(value)
        self.assertEqual(self.compile(baseline=value, overlay=valid_overlay(portfolio_fit_status="BLOCKED"))["portfolio_fit_status"], "BLOCKED")

    def test_hrb_14_raw_llm_strategy_signal_rejected(self):
        value = valid_baseline(); value["strategy_signal"] = "ADD_CANDIDATE"
        with self.assertRaises(ValueError): self.compile(baseline=value)

    def test_hrb_15_soxl_is_direction_only(self):
        registry = load_json(ROOT / "workspace/policies/instrument_registry.json")
        self.assertEqual(registry["instruments"]["SOXL"]["confirmation_mode"], "DIRECTION_ONLY")

    def test_hrb_16_soxx_multiple_never_strategy_gate(self):
        result = self.compile("SOXL", overlay=valid_overlay("SOXL", technical_status="WATCH", leveraged_confirmation_status="ALIGNED"))
        self.assertEqual(result["strategy_signal"], "NONE")

    def test_hrb_17_mvll_daily_multiple_is_supplemental(self):
        result = self.compile("MVLL", overlay=valid_overlay("MVLL", technical_status="WATCH", leveraged_confirmation_status="DIVERGED"))
        self.assertEqual(result["strategy_signal"], "NONE")

    def test_hrb_18_mrvl_value_cannot_replace_mvll_close(self):
        overlay = valid_overlay("MVLL")
        self.assertEqual(overlay["primary_price_status"], "VALIDATED")
        self.assertNotIn("MRVL", json.dumps(overlay))

    def test_hrb_19_hard_risk_outranks_bullish_baseline(self):
        overlay = valid_overlay(technical_status="READY", hard_risk_observation="PRIMARY_BREACH_OBSERVED",
                                risk_status="HARD_RISK", deterministic_existing_policy={"action_on_breach": "exit_review"})
        self.assertEqual(self.compile(overlay=overlay)["strategy_signal"], "EXIT_CANDIDATE")

    def test_hrb_20_existing_timing_quantity_can_carry_authority(self):
        overlay = valid_overlay(quantity=3, quantity_authority="deterministic_existing_policy",
                                deterministic_existing_policy={"rule_id": "TEST", "action_on_breach": None})
        result = self.compile(overlay=overlay)
        self.assertEqual((result["quantity"], result["quantity_authority"]), (3, "deterministic_existing_policy"))

    def test_hrb_21_research_cannot_generate_quantity(self):
        self.assertIsNone(self.compile()["quantity"])

    def test_hrb_22_portfolio_hash_unchanged(self):
        path = ROOT / "stock-strategy-system/portfolio_state.json"; before = canonical_hash(load_json(path)); self.compile()
        self.assertEqual(before, canonical_hash(load_json(path)))

    def test_hrb_23_alert_policy_thresholds_unchanged(self):
        policy = load_json(ROOT / "stock-strategy-system/alert_policy.json")
        self.assertEqual(policy["strategy_version"], "2026-08-05-v4")

    def test_hrb_24_order_authority_false(self):
        self.assertFalse(self.compile()["order_authority"])
        self.assertEqual(validate_instance(self.compile(), COMPILED_SCHEMA), [])

    def test_hrb_25_one_ticker_failure_does_not_propagate(self):
        bad = valid_baseline("MVLL"); bad["baseline_hash"] = "f" * 64
        self.assertEqual(self.compile("MVLL", baseline=bad, overlay=valid_overlay("MVLL"))["strategy_state"], "STRATEGY_REFRESH_REQUIRED")
        self.assertNotEqual(self.compile("NBIS")["strategy_state"], "STRATEGY_REFRESH_REQUIRED")

    def test_hrb_26_migration_does_not_replay_alerts(self):
        policy = load_json(ROOT / "workspace/policies/holding_research_baseline_policy.json")
        self.assertFalse(policy["historical_alert_replay_allowed"])

    def test_hrb_27_refresh_is_new_immutable_version(self):
        root = ROOT / "manage-us-stock-strategy/tests/fixtures/v2_6/runtime"; index = root / "index.json"
        for path in (root/"baselines/NBIS").glob("*.json"): path.unlink()
        index.unlink(missing_ok=True)
        try:
            first = valid_baseline(); second = valid_baseline(); second["baseline_id"] = "nbis-v2"; second["baseline_version"] = 2; second["supersedes_baseline_id"] = first["baseline_id"]; second = recompute_hashes(second)
            self.assertTrue(activate_baseline(first, schema_path=BASELINE_SCHEMA, baseline_root=root / "baselines", index_path=index, activated_at="2026-08-13T05:10:00Z")["index_updated"])
            self.assertTrue(activate_baseline(second, schema_path=BASELINE_SCHEMA, baseline_root=root / "baselines", index_path=index, activated_at="2026-08-13T05:20:00Z")["index_updated"])
            self.assertTrue((root / "baselines/NBIS/nbis-20260813-v1.json").exists())
        finally:
            for path in (root/"baselines/NBIS").glob("*.json"): path.unlink()
            index.unlink(missing_ok=True)

    def test_hrb_28_unconfirmed_broker_extraction_cannot_enter_baseline_or_overlay(self):
        baseline = valid_baseline(); overlay = valid_overlay()
        self.assertFalse({"broker_extraction", "available_cash_usd", "average_cost_usd"}.intersection(baseline))
        self.assertNotIn("broker_extraction", overlay)


if __name__ == "__main__":
    unittest.main()
