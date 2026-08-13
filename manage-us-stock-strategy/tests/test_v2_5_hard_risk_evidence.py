from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
from build_holding_strategy_review import build_holding_strategies
from validation_common import load_json


class V25HardRiskEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_json(ROOT / "stock-strategy-system/alert_policy.json")
        cls.registry = load_json(ROOT / "workspace/policies/instrument_registry.json")

    def build(self, cross):
        portfolio = {"strategy_version": "2026-08-05-v4", "holdings": {"NBIS": 15}, "average_cost_usd": {"NBIS": 215.0},
            "available_cash_usd": 0.0, "last_confirmed_broker_snapshot": {"verified": True, "holdings_complete": True,
            "cash_verified": True, "cash_verified_scope": "available_cash_only", "as_of": "2026-08-11", "source": "TEST_ONLY"}}
        row = {"bar_date": "2026-08-11", "open": 195.0, "high": 196.0, "low": 189.0, "close": 190.0,
            "close_prev": 195.0, "volume": 1000000, "corporate_action_unresolved": False,
            "indicator_validation": {"status": "passed", "errors": []}, "quote_crosscheck": cross}
        market = {"symbols": {"NBIS": row}, "session": {"us_session_date": "2026-08-11"}}
        hard = {"state": "HARD_RISK_REVIEW", "risk_freeze_active": True, "candidates": [{"event_type": "holding_max_loss_breach",
            "symbol": "NBIS", "breached": True, "grade": "D", "event_key": "HR", "boundary_usd": 193.5}]}
        return build_holding_strategies(portfolio, self.policy, self.registry, market,
            {"coverage_status": "COMPLETE", "events": []}, hard, {"holdings": {}},
            analysis_cutoff="2026-08-12T00:45:00+00:00", market_session="2026-08-11")[0]

    def test_v25_hr_01_primary_breach_survives_pending(self):
        item = self.build(None)
        self.assertEqual(item["breach_observation_status"], "PRIMARY_BREACH_OBSERVED")
        self.assertEqual(item["holding_risk_state"], "HARD_RISK_WATCH")
        self.assertEqual(item["execution_state"], "HUMAN_REVIEW_REQUIRED")

    def test_v25_hr_02_confirmed_unapproved_action_no_auto_exit(self):
        item = self.build({"status": "verified", "independent_of_builder": True, "bar_date": "2026-08-11",
                           "evidence_validation_status": "VALIDATED", "comparison_status": "MATCH", "acquisition_method": "STRUCTURED_API"})
        self.assertEqual(item["breach_action_authority_status"], "UNVERIFIED")
        self.assertEqual(item["strategy_state"], "STRATEGY_REFRESH_REQUIRED")

    def test_v25_hr_03_conflict_retains_warning(self):
        item = self.build({"status": "conflict"})
        self.assertEqual(item["independent_confirmation_status"], "CONFLICT")
        self.assertEqual(item["holding_risk_state"], "HARD_RISK_WATCH")
        self.assertEqual(item["effective_price_status"], "PRICE_CONFLICT")

    def test_v25_hr_04_quantity_null(self):
        self.assertIsNone(self.build(None)["quantity"])


if __name__ == "__main__":
    unittest.main()
