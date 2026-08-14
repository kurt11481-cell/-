from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from provider_limitation_audit import build_audit
from validation_common import load_json


class ProviderLimitationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / "workspace/outputs/portfolio-strategy/2026-08-13"
        cls.kiwoom = load_json(base / "kiwoom_market_snapshot.json")
        cls.yfinance = load_json(base / "yfinance_shadow_snapshot.json")
        cls.extended = load_json(ROOT / "workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/kiwoom_extended_hours_snapshot_v2.json")
        cls.policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        cls.volume_acceptance = load_json(ROOT / "workspace/research/provider-evidence/kiwoom/2026-08-14/mvll-volume-authority-acceptance.json")

    def audit(self):
        return build_audit(kiwoom_snapshot=self.kiwoom, yfinance_snapshot=self.yfinance,
                           extended_snapshot=self.extended, provider_policy=self.policy,
                           volume_acceptance=self.volume_acceptance)

    def test_fsly_exhaustion_keeps_exact_fallback(self):
        value = self.audit()["FSLY"]
        self.assertTrue(value["continuation_exhausted"])
        self.assertLess(value["kiwoom_history_bars"], value["policy_minimum_bars"])
        self.assertEqual(value["technical_history_status"], "YFINANCE_PRIMARY_VALIDATED_FALLBACK_REQUIRED")

    def test_mvll_price_and_volume_authority_separate(self):
        value = self.audit()["MVLL"]
        self.assertEqual(value["price_authority"], "KIWOOM_REST")
        self.assertEqual(value["volume_authority"], "KIWOOM_VALID_SCOPED")
        self.assertEqual(value["technical_condition_status"], "RVOL20_NOT_MET")
        self.assertEqual(value["blocked_decision_classes"], [])
        self.assertFalse(value["volume_averaged"])
        self.assertFalse(value["threshold_changed"])

    def test_missing_extended_quote_is_ticker_local(self):
        value = self.audit()["extended_sessions"]
        self.assertEqual(value["NBIS"]["capability"], "UNAVAILABLE_TICKER_LOCAL")
        self.assertEqual(value["SOXL"]["capability"], "AVAILABLE")
        self.assertFalse(value["NBIS"]["daily_data_invalidated"])

    def test_no_scope_or_authority_mutation(self):
        value = self.audit()
        self.assertFalse(value["provider_scope_mutated"])
        self.assertFalse(value["portfolio_mutation"])
        self.assertIsNone(value["quantity"])
        self.assertEqual(value["quantity_authority"], "none")
        self.assertFalse(value["order_authority"])


if __name__ == "__main__":
    unittest.main()
