from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from kiwoom_account_readonly_bridge import ACCOUNT_BODIES, request_body, validate_request

# ust21100 template after the 2026-10-13 fix (krw_repl_skip_yn empty returned 1511).
TRANSACTION_HISTORY_TEMPLATE = {
    "strt_dt": "", "end_dt": "", "tp": "0", "stex_tp": "", "stk_cd": "", "krw_repl_skip_yn": "N",
}
# Every other read body, pinned to its value before the fix.
GOLDEN_OTHER_BODIES = {
    "account_deposit_read": {},
    "account_deposit_detail_read": {},
    "account_holdings_read": {"stex_tp": "", "stk_cd": ""},
    "account_open_items": {"ord_dt": "", "slby_tp": "0", "stex_tp": "", "stk_cd": ""},
    "account_fills_read": {"stex_tp": "", "stk_cd": ""},
    "account_realized_pnl_read": {"fc_krw_tp": "0", "stex_tp": "", "stk_cd": ""},
    "account_daily_fills_read": {"ord_dt": "", "query_tp": "1", "slby_tp": "0", "stex_tp": "", "stk_cd": "",
                                 "oppo_trde_tp": "%", "fr_ord_no": ""},
    "account_day_trades_read": {"base_dt": "", "qry_tp": "1", "fc_krw_tp": "0"},
}


class KiwoomAccountBodiesTests(unittest.TestCase):
    def test_transaction_history_required_fields_are_filled(self):
        body = ACCOUNT_BODIES["account_transaction_history_read"]
        self.assertEqual(body["tp"], "0")
        self.assertEqual(body["krw_repl_skip_yn"], "N")
        self.assertNotEqual(body["krw_repl_skip_yn"], "")
        self.assertEqual(body, TRANSACTION_HISTORY_TEMPLATE)

    def test_transaction_history_request_body_fills_dates_only(self):
        request = validate_request({"operation": "account_transaction_history_read",
                                    "params": {"strt_dt": "20261010", "end_dt": "20261013"}})
        expected = dict(TRANSACTION_HISTORY_TEMPLATE, strt_dt="20261010", end_dt="20261013")
        self.assertEqual(request_body(request), expected)
        # The template itself is not mutated by filling a request.
        self.assertEqual(ACCOUNT_BODIES["account_transaction_history_read"], TRANSACTION_HISTORY_TEMPLATE)

    def test_other_bodies_unchanged(self):
        self.assertEqual(set(ACCOUNT_BODIES), set(GOLDEN_OTHER_BODIES) | {"account_transaction_history_read"})
        for operation, golden in GOLDEN_OTHER_BODIES.items():
            with self.subTest(operation=operation):
                self.assertEqual(ACCOUNT_BODIES[operation], golden)


if __name__ == "__main__":
    unittest.main()
