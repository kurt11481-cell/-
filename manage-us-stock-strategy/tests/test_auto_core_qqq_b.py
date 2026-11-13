"""qqq-b-core3 (docs/claude/qqq-b-core3-builder-prompt.md; decision t3-proceeds-qqq-1108): QQQ is a proceeds-parking
index ETF. It is an index ETF (no earnings date, not in single_nominal), it gets no no-card alert lines (alert 2
NOCARD and alert 10), and it is not a card-buy product (APPROVED_BUY unchanged).

Unit tests only (TEST_ONLY inputs): no Kiwoom, kiwoomcli or PowerShell call.
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_tickets as tickets  # noqa: E402

OLD_APPROVED_BUY = ("BE", "MU", "NBIS", "DELL", "AMD", "SOXL", "TQQQ", "DRAM", "PWR", "LITE")
# The NOCARD trigger exactly as auto_core_rules.py appends it for a symbol without a card.
NOCARD = {"id": "NOCARD", "group": None, "name": "카드 없음", "side": "alert", "state": "review",
          "previous_state": None, "new": False, "source": "registry", "card_defined": False, "strength": "review"}
OTHER_REVIEW = {"id": "C8-", "group": None, "name": "TEST_ONLY C8", "side": "alert", "state": "review",
                "previous_state": None, "new": False, "source": "rule", "card_defined": False, "strength": "weak"}


class ConstantTests(unittest.TestCase):
    def test_1_lists(self):
        self.assertEqual(tickets.INDEX_ETFS, ("SOXL", "TQQQ", "DRAM", "QQQ"))
        self.assertEqual(tickets.PARKING_ETFS, ("QQQ",))
        self.assertEqual(tickets.APPROVED_BUY, OLD_APPROVED_BUY)
        self.assertNotIn("QQQ", tickets.APPROVED_BUY)


class NominalTests(unittest.TestCase):
    def test_2_qqq_not_in_single_nominal(self):
        result = tickets.rule_file_nominal({"BE": 10, "QQQ": 5}, {"BE": Decimal("100"), "QQQ": Decimal("500")},
                                           Decimal("1000"), {"BE": 1, "QQQ": 1})
        self.assertEqual(result["status"], "OK")
        self.assertIn("BE", result["single_nominal"])
        self.assertNotIn("QQQ", result["single_nominal"])


class BuyRequirementTests(unittest.TestCase):
    def row(self, research_block):
        return tickets.buy_requirements(
            symbol="QQQ", held=True, s7={"fresh": True, "e": 1.0}, nominal={"n": 1.0, "status": "OK", "single_nominal": {}},
            peaks={}, earnings=None, calendar_sessions=[], buy_session=None, evaluation_session="2026-11-12",
            generated_at=None, cash=Decimal("100000"), close=Decimal("500"), check={"entry": {}},
            evidence={"basis_met": True, "composition": "TEST_ONLY"}, watch_status=None, m6={"s": "ok", "t": "x"},
            shock={"status": "ok", "open": False, "reasons": []}, research_block=research_block)

    def test_3_index_etf_cell_and_no_product_approval(self):
        cells = self.row(None)["c"]
        self.assertEqual(cells[0], {"s": "ok", "t": "통과 (지수 ETF — 해당 없음)"})
        self.assertEqual(cells[1]["s"], "no")
        self.assertIn("상품 승인 없음", cells[1]["t"])

    def test_4_research_block_still_blocks(self):
        self.assertEqual(self.row("X")["c"][0]["s"], "no")


class AlertTests(unittest.TestCase):
    def test_5_no_nocard_lines_for_qqq(self):
        decision = {
            "symbols": {
                "QQQ": {"role": "held", "nocard": True, "triggers": [dict(NOCARD), dict(OTHER_REVIEW)]},
                "BE": {"role": "held", "nocard": True, "triggers": [dict(NOCARD)]},
            },
            "evidence": {}, "account": {}, "exposure": {}, "buy_requirements": [], "tickets": [], "shock": {}}
        alerts, states = decide_module.alert_candidates(decision=decision, previous=None, mode="compare", exceptions=[],
                                                        previous_run_missing=False)
        self.assertIn("10:BE", states)
        self.assertIn("2:BE:NOCARD", states)
        self.assertNotIn("10:QQQ", states)
        self.assertNotIn("2:QQQ:NOCARD", states)
        self.assertEqual(states.get("2:QQQ:C8-"), "review")
        codes = [alert["code"] for alert in alerts]
        self.assertIn("2:QQQ:C8-", codes)
        self.assertIn("10:BE", codes)
        self.assertIn("2:BE:NOCARD", codes)
        self.assertFalse([alert["line"] for alert in alerts if "QQQ" in alert["line"] and "카드 없음" in alert["line"]])


if __name__ == "__main__":
    unittest.main()
