from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from validate_mvll_volume_authority import build_acceptance


def bars(key: str = "session"):
    return [{key: f"2026-07-{index:02d}", "volume": 100 + index} for index in range(1, 22)]


class MVLLVolumeAuthorityTests(unittest.TestCase):
    def inputs(self):
        kbars = bars()
        kiwoom = {"completed_session": "2026-07-21", "ticker_results": [{
            "ticker": "MVLL", "status": "PASS",
            "identity": {"ticker": "MVLL", "mapping_status": "VERIFIED", "mapping_guessed": False, "source_api_id": "usa10099"},
            "raw": {"status": "PASS", "bars": copy.deepcopy(kbars)},
            "adjusted": {"status": "PASS", "price_basis": "ADJUSTED", "fx_applied": False,
                         "completed_session": "2026-07-21", "bars": copy.deepcopy(kbars)},
        }]}
        yfinance = {"symbols": {"MVLL": {"bar_date": "2026-07-21", "corporate_action_unresolved": False,
            "timing_window": [{"bar_date": row["session"], "volume": row["volume"] - 1} for row in kbars]}}}
        policy = {"window_sessions": 20, "volume_semantics": "SESSION_AGGREGATED_DAILY_VOLUME_AS_REPORTED_BY_KIWOOM_USA06012"}
        alert = {"holding_timing_rules": {"definitions": {"pullback_reclaim_relative_volume_minimum": 1.0}}}
        return kiwoom, yfinance, policy, alert

    def test_valid_kiwoom_is_scoped_primary_and_divergence_nonblocking(self):
        value = build_acceptance(kiwoom=self.inputs()[0], yfinance=self.inputs()[1],
                                 policy=self.inputs()[2], alert_policy=self.inputs()[3],
                                 source_hashes={"kiwoom": "a" * 64})
        self.assertEqual(value["volume_authority_status"], "KIWOOM_VALID_SCOPED")
        self.assertFalse(value["blocking"])
        self.assertFalse(value["volume_averaged"])

    def test_wrong_identity_fails_closed(self):
        kiwoom, yfinance, policy, alert = self.inputs()
        kiwoom["ticker_results"][0]["identity"]["ticker"] = "MRVL"
        value = build_acceptance(kiwoom=kiwoom, yfinance=yfinance, policy=policy,
                                 alert_policy=alert, source_hashes={"kiwoom": "a" * 64})
        self.assertEqual(value["acceptance_status"], "INVALID")
        self.assertEqual(value["volume_authority_status"], "UNRESOLVED")

    def test_different_window_fails_closed(self):
        kiwoom, yfinance, policy, alert = self.inputs()
        yfinance["symbols"]["MVLL"]["timing_window"][-1]["bar_date"] = "2026-07-22"
        value = build_acceptance(kiwoom=kiwoom, yfinance=yfinance, policy=policy,
                                 alert_policy=alert, source_hashes={"kiwoom": "a" * 64})
        self.assertFalse(value["same_session_window"])
        self.assertEqual(value["acceptance_status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
