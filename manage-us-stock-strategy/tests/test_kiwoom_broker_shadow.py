from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from kiwoom_broker_shadow import normalize_snapshot, reconciliation_proposal
from kiwoom_account_readonly_bridge import validate_request
from kiwoom_runtime_bridge import blocked_api_target
from validation_common import file_hash, load_json, validate_instance


class KiwoomBrokerShadowTests(unittest.TestCase):
    def results(self):
        at = "2026-08-14T13:00:00Z"
        def value(operation, data):
            return {"bridge_status": "PASS", "operation": operation, "data": data,
                    "retrieved_at": at, "account_identifier_stored": False, "order_authority": False}
        return [
            value("account_holdings_read", [{"stk_cd": "NBIS", "frgn_stk_nm": "Nebius", "crnc_code": "USD", "qty": "15", "poss_qty": "15", "sell_alowq": "15", "frgn_stk_book_uv": "215"}]),
            value("account_deposit_read", [{"crnc_code": "USD", "crnc_nm": "US Dollar", "fc_entra": "0", "fc_pymn_alowa": "0", "fc_ord_alowa": "0"}]),
            value("account_deposit_detail_read", [{"d1_usd_sell_excta": "5000", "d1_usd_buy_excta": "0", "d2_usd_sell_excta": "0", "d2_usd_buy_excta": "0"}]),
            value("account_open_items", []), value("account_fills_read", []), value("account_realized_pnl_read", []),
        ]

    def test_masking_and_no_account_identifier(self):
        value = normalize_snapshot(self.results(), snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                   generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        self.assertFalse(value["account_identifier_stored"])
        self.assertNotIn("account_number", str(value).lower())

    def test_cash_semantics_excludes_unsettled(self):
        value = normalize_snapshot(self.results(), snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                   generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        self.assertEqual(value["cash"]["settled_available_cash"], 0)
        self.assertEqual(value["cash"]["cash_status"], "VERIFIED_ZERO")
        self.assertEqual(value["cash"]["unsettled_funds"]["d1_sell_settlement_usd"], 5000)

    def test_stale_snapshot(self):
        value = normalize_snapshot(self.results(), snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                   generated_at="2026-08-14T14:00:01Z", maximum_age_seconds=900)
        self.assertEqual(value["broker_snapshot_freshness_status"], "STALE")

    def test_no_fill_inference_or_auto_apply(self):
        before = file_hash(ROOT / "stock-strategy-system/portfolio_state.json")
        portfolio = load_json(ROOT / "stock-strategy-system/portfolio_state.json")
        snap = normalize_snapshot(self.results(), snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        proposal = reconciliation_proposal(snap, portfolio, expected_before_hash=before)
        self.assertFalse(proposal["auto_apply"])
        self.assertFalse(proposal["fill_inference_performed"])
        self.assertEqual(before, file_hash(ROOT / "stock-strategy-system/portfolio_state.json"))

    def test_state_revision_is_bound(self):
        portfolio = load_json(ROOT / "stock-strategy-system/portfolio_state.json")
        snap = normalize_snapshot(self.results(), snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        proposal = reconciliation_proposal(snap, portfolio, expected_before_hash="a" * 64)
        self.assertEqual(proposal["current_state_revision"], portfolio["state_revision"])
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")

    def test_read_operations_allowlisted_and_writes_denied(self):
        self.assertEqual(validate_request({"operation": "account_holdings_read"})["operation"], "account_holdings_read")
        self.assertTrue(blocked_api_target("usa10075", "/api/us/ordr"))
        with self.assertRaises(Exception):
            validate_request({"operation": "order_modify"})

    def test_authority_boundary(self):
        snap = normalize_snapshot(self.results(), snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        self.assertEqual(snap["quantity_authority"], "none")
        self.assertFalse(snap["order_authority"])
        self.assertEqual(validate_instance(snap, ROOT / "manage-us-stock-strategy/schemas/kiwoom-broker-shadow.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
