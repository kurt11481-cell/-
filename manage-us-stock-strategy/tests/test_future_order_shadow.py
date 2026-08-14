from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from future_order_shadow import (build_gateway_dry_run, build_order_intent,
    evaluate_risk, normalize_broker_event, reconcile_broker_state, transition_order_state)


class FutureOrderShadowTests(unittest.TestCase):
    def test_external_manual_event_is_observed_not_canceled(self):
        event = normalize_broker_event({"event_id": "e1", "ticker": "NBIS", "known_order_intent": False}, seen_ids=set())
        self.assertEqual(event["origin"], "EXTERNAL_MANUAL_ORDER_DETECTED")
        self.assertFalse(event["automatic_cancel_authority"])

    def test_duplicate_event_is_detected(self):
        event = normalize_broker_event({"event_id": "e1", "ticker": "NBIS"}, seen_ids={"e1"})
        self.assertTrue(event["duplicate_or_replay"])

    def test_reconciliation_rest_is_truth_anchor(self):
        state = reconcile_broker_state({"record_hash": "a" * 64, "open_orders_visibility": "UNKNOWN"}, [], now="2026-08-15T00:00:00Z", freshness_status="FRESH")
        self.assertEqual(state["status"], "PARTIAL")
        self.assertTrue(state["rest_snapshot_is_truth_anchor"])

    def test_intent_has_no_quantity_or_order_authority(self):
        intent = build_order_intent(ticker="NBIS", side="BUY", strategy_id="s", decision_class="ADD_REVIEW", reason="test-only", expires_at="2026-08-16T00:00:00Z")
        self.assertIsNone(intent["proposed_quantity"])
        self.assertFalse(intent["order_authority"])

    def test_independent_risk_kernel_rejects_missing_authority(self):
        intent = build_order_intent(ticker="NBIS", side="BUY", strategy_id="s", decision_class="ADD_REVIEW", reason="test-only", expires_at="2026-08-16T00:00:00Z")
        risk = evaluate_risk(intent, {"status": "PARTIAL", "open_orders_visibility": "UNKNOWN"}, {})
        self.assertEqual(risk["status"], "RISK_REJECTED")
        self.assertFalse(risk["strategy_override_allowed"])

    def test_gateway_never_sends_order_endpoint(self):
        intent = build_order_intent(ticker="NBIS", side="BUY", strategy_id="s", decision_class="ADD_REVIEW", reason="test-only", expires_at="2026-08-16T00:00:00Z")
        risk = evaluate_risk(intent, {"status": "PARTIAL", "open_orders_visibility": "UNKNOWN"}, {})
        gateway = build_gateway_dry_run(intent, risk, api_id="ust20000")
        self.assertTrue(gateway["target_is_write_endpoint"])
        self.assertFalse(gateway["network_send"])
        self.assertIsNone(gateway["request_payload"])

    def test_ack_unknown_never_blindly_resubmits(self):
        self.assertEqual(transition_order_state("ACK_UNKNOWN", "RETRY"), "RECONCILIATION_REQUIRED")

    def test_partial_fill_and_cancel_state_machine(self):
        self.assertEqual(transition_order_state("ACKNOWLEDGED", "PARTIAL_FILL"), "PARTIALLY_FILLED")
        self.assertEqual(transition_order_state("CANCEL_PENDING", "CANCEL_CONFIRMED"), "CANCELED")


if __name__ == "__main__":
    unittest.main()
