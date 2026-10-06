from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from resolve_leveraged_quote import evaluate_leveraged_confirmation, leveraged_proxy_check, resolve_independent_product_close
from validation_common import load_json


class V25LeveragedConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_json(ROOT / "workspace/policies/instrument_registry.json")["instruments"]
        cls.policy = load_json(ROOT / "stock-strategy-system/alert_policy.json")

    def row(self, close, prev=100):
        return {"bar_date": "2026-08-11", "close": close, "close_prev": prev}

    def test_v25_lv_01_soxl_direction_only(self):
        self.assertEqual(self.registry["SOXL"]["confirmation_mode"], "DIRECTION_ONLY")
        result = evaluate_leveraged_confirmation(self.row(103), self.row(101), profile=self.registry["SOXL"])
        self.assertEqual(result["status"], "ALIGNED")

    def test_v25_lv_02_soxx_times_three_not_exact(self):
        result = evaluate_leveraged_confirmation(self.row(102), self.row(101), profile=self.registry["SOXL"])
        self.assertFalse(result["exact_multiple_comparison_performed"])
        self.assertNotIn("expected_product_return_fraction", result)

    def test_v25_lv_03_mvll_daily_multiple(self):
        self.assertEqual(self.registry["MVLL"]["confirmation_mode"], "DAILY_MULTIPLE")

    def test_v25_lv_04_proxy_cannot_substitute_direct_close(self):
        with self.assertRaises(Exception):
            resolve_independent_product_close(self.row(100), independent_close=101, bar_date="2026-08-11")

    def test_v25_lv_05_divergence_does_not_invalidate_direct_close(self):
        direct = resolve_independent_product_close(self.row(100), independent_close=100.02, bar_date="2026-08-11")
        proxy = evaluate_leveraged_confirmation(self.row(99), self.row(102), profile=self.registry["SOXL"])
        self.assertEqual(direct["status"], "verified")
        self.assertEqual(proxy["status"], "DIVERGED")

    def test_v25_lv_06_unapproved_tracking_tolerance_is_shadow_only(self):
        result = evaluate_leveraged_confirmation(self.row(102), self.row(101), profile=self.registry["MVLL"])
        self.assertEqual((result["status"], result["tolerance_authority"]), ("SHADOW_ONLY", "SHADOW_ONLY_UNAPPROVED"))

    def test_v25_lv_07_existing_rules_unchanged(self):
        rules = self.policy["holding_risk_rules"]["positions"]
        self.assertEqual(rules["SOXL"]["maximum_loss_fraction_from_average_cost"], 0.2)
        self.assertEqual(rules["MVLL"]["maximum_loss_fraction_from_average_cost"], 0.6)
        # I0-b (2026-10-06) removed the MVLL/SOXL timing slots from the active policy.
        self.assertEqual(self.policy["holding_timing_rules"]["positions"], {})

    def test_v25_lv_08_legacy_proxy_helper_remains_callable(self):
        value = leveraged_proxy_check(
            self.row(102), self.row(101), proxy_symbol="MRVL",
            leverage_multiple=2.0, maximum_tracking_error_fraction=0.001,
        )
        self.assertEqual(value["status"], "corroborated")


if __name__ == "__main__":
    unittest.main()
