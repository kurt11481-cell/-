from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from orthogonal_state_axes import no_axis_implies_execution, state_axes


class OrthogonalStateAxesTests(unittest.TestCase):
    def test_provider_ready_does_not_imply_technical_ready_or_execution(self):
        value = state_axes(ticker="MVLL", decision_class="RVOL20", price="KIWOOM_VALID",
                           volume="KIWOOM_VALID_SCOPED", technical="RVOL20_NOT_MET",
                           event="PARTIAL_NONBLOCKING", broker="PARTIAL")
        self.assertEqual(value["technical_condition_status"], "RVOL20_NOT_MET")
        self.assertTrue(no_axis_implies_execution(value))

    def test_event_block_is_independent_from_price(self):
        value = state_axes(ticker="NBIS", decision_class="HOLDING_REVIEW", price="KIWOOM_VALID",
                           volume="NOT_EVALUATED", technical="WATCH",
                           event="PARTIAL_BLOCKING", broker="PARTIAL")
        self.assertEqual(value["price_authority_status"], "KIWOOM_VALID")
        self.assertEqual(value["event_readiness_status"], "PARTIAL_BLOCKING")
        self.assertTrue(no_axis_implies_execution(value))

    def test_invalid_axis_fails_closed(self):
        with self.assertRaises(ValueError):
            state_axes(ticker="SOXL", decision_class="HOLDING_REVIEW", price="READY",
                       volume="NOT_EVALUATED", technical="READY",
                       event="PARTIAL_NONBLOCKING", broker="PARTIAL")


if __name__ == "__main__":
    unittest.main()
