from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from broker_visibility_audit import build_audit
from kiwoom_account_readonly_bridge import ACCOUNT_BODIES
from validation_common import validate_instance


class BrokerVisibilityAuditTests(unittest.TestCase):
    def result(self, operation, status="PASS", rows=None, failure=None):
        value = {"operation": operation, "bridge_status": status, "data": rows or [],
                 "runtime_commit": "a" * 40, "order_authority": False}
        if failure:
            value["failure_type"] = failure
        return value

    def test_realized_pnl_request_preserves_required_currency_basis(self):
        self.assertEqual(ACCOUNT_BODIES["account_realized_pnl_read"]["fc_krw_tp"], "0")

    def test_unknown_open_orders_is_not_none_and_blocks_future_execution(self):
        results = [self.result("account_deposit_read"), self.result("account_holdings_read"),
                   self.result("account_fills_read"),
                   self.result("account_open_items", "KIWOOM_API_RESPONSE_ERROR", failure="API_RESPONSE_ERROR"),
                   self.result("account_realized_pnl_read")]
        value = build_audit(results=results, snapshot={"broker_snapshot_freshness_status": "FRESH", "cash": {"settled_available_cash": 63.69}})
        self.assertEqual(value["open_orders_visibility"]["status"], "UNKNOWN")
        self.assertFalse(value["open_orders_visibility"]["empty_result_interpreted_as_none"])
        self.assertEqual(value["broker_visibility_for_live_execution"], "NOT_READY")
        self.assertFalse(value["fill_inference_performed"])
        self.assertEqual(validate_instance(value, ROOT / "manage-us-stock-strategy/schemas/kiwoom-broker-visibility-audit.schema.json"), [])

    def test_official_history_api_without_adapter_is_classified(self):
        results = [self.result("account_deposit_read"), self.result("account_holdings_read"),
                   self.result("account_fills_read"), self.result("account_open_items"),
                   self.result("account_realized_pnl_read")]
        value = build_audit(results=results, snapshot={"broker_snapshot_freshness_status": "FRESH", "cash": {"settled_available_cash": 63.69}})
        gaps = {item["capability"]: item["classification"] for item in value["capability_gaps"]}
        self.assertEqual(gaps["daily_order_fills"], "OFFICIAL_API_SUPPORTED_ADAPTER_MISSING")
        self.assertEqual(gaps["orders_by_period"], "OFFICIAL_API_SUPPORTED_ADAPTER_MISSING")
        self.assertIsNone(value["quantity"])
        self.assertFalse(value["order_authority"])


if __name__ == "__main__":
    unittest.main()
