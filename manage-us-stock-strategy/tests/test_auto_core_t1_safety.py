"""t1-safety: two fail-open edges of decide closed before T1 recording is switched on.

Fix 1 (judge2 G 5): the EV4 of a past session whose decide record ended before F1 (or that has no record) is
rebuilt from that run day's T1 broker snapshot through F1's own functions, or else judged cautiously from the
nearest known totals (3% of the EV4 line), and enters R-REC1. Fix 2 (judge2 G 2, r4 F): in F6 an (ord_dt, ord_no)
that comes twice as the very same row counts once; as a different row the outcome is unknown.

All inputs are synthetic (TEST_ONLY), built on test_auto_core_decide.Env. No network, no Kiwoom.
"""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import auto_core_tickets as tickets_module  # noqa: E402
import helpers  # noqa: E402
import test_auto_core_decide as decide_fixture  # noqa: E402
from validation_common import validate_instance, write_json  # noqa: E402

DAYS = decide_fixture.DAYS
LAST = decide_fixture.LAST
S1, S2, S3 = DAYS[-4], DAYS[-3], DAYS[-2]  # the three sessions before today's evaluation session (LAST)
SELL = tickets_module.SIDE_NAMES["sell"]


def run_day_of(session):
    """The KST run day whose decide evaluates `session` (the day after it)."""
    return (date.fromisoformat(session) + timedelta(days=1)).isoformat()


def without_backfill(**_kwargs):
    """ev4_backfill_plan as before t1-safety: no past session is looked at."""
    return None


def comparable(decision):
    view = copy.deepcopy(decision)
    view.pop("ev4_backfill", None)
    return view


# ---------------------------------------------------------------------------------------------
# Fix 2: duplicate (ord_dt, ord_no) rows in F6
# ---------------------------------------------------------------------------------------------

def _ticket():
    return decide_fixture._fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")


def _row(**overrides):
    row = helpers.fill_row("SOXL", SELL, ordered=5, filled=5, price="95.00", fill_price="96.10")
    row.update(overrides)
    return row


def _close():
    """pre-on-fix 1: the ticket session's close (05:00 KST on 2026-10-02), passed to ticket_rows."""
    return tickets_module.session_close(_ticket(), helpers.calendar(decide_fixture.CALENDAR_DAYS))


class DuplicateOrderNumberTests(unittest.TestCase):
    def test_f1_the_same_row_twice_counts_once(self):
        ticket = _ticket()
        chosen = tickets_module.ticket_rows(ticket, [("2026-10-01", _row()), ("2026-10-01", _row())], set(),
                                            close_at=_close())
        self.assertIsNone(chosen["note"])
        self.assertEqual(chosen["orders"], [{"ord_dt": "2026-10-01", "ord_no": "0000001"}])
        outcome = tickets_module.classify_outcome(ticket, chosen["rows"])
        self.assertEqual((outcome["state"], outcome["filled_qty"], outcome["rows"]), ("filled", 5, 1))

    def test_f2_a_different_row_with_the_same_order_number_is_unknown(self):
        ticket = _ticket()
        for name, other in (("fill", _row(cntr_qty="000000000003")), ("other_ticker", _row(stk_cd="SOXS"))):
            with self.subTest(case=name):
                chosen = tickets_module.ticket_rows(ticket, [("2026-10-01", _row()), ("2026-10-01", other)], set(),
                                                    close_at=_close())
                self.assertEqual(chosen, {"rows": [], "orders": [], "note": "ORD_NO_DUPLICATE_CONFLICT"})

    def test_f2_through_read_outcomes_the_ticket_stays_open(self):
        ticket = _ticket()
        reader = decide_fixture.FakeReader(fills={"20261001": [_row(), _row(cntr_qty="000000000003")]})
        block = decide_module.read_outcomes(
            [ticket], reader=reader, runtime=Path("."), rate_policy={}, run_day="2026-10-02", reconcile_fills=[],
            evaluation_session="2026-10-01", calendar=helpers.calendar(decide_fixture.CALENDAR_DAYS),
            attributed_orders=[])
        self.assertEqual(block["outcomes"], [])
        self.assertEqual([item["ticket_id"] for item in block["open_tickets"]], [ticket["ticket_id"]])
        self.assertIn(f"OUTCOME_UNKNOWN:{ticket['ticket_id']}", block["reasons"])
        self.assertEqual(block["attributed"], [])

    def test_f2_same_number_on_another_day_is_not_a_duplicate(self):
        ticket = _ticket()
        chosen = tickets_module.ticket_rows(
            ticket, [("2026-10-01", _row(ord_qty="000000000003", cntr_qty="000000000003")),
                     ("2026-10-02", _row(ord_qty="000000000002", cntr_qty="000000000002", ord_time="00:30:00"))],
            set(), close_at=_close())
        self.assertIsNone(chosen["note"])
        self.assertEqual(len(chosen["orders"]), 2)

    def test_f3_no_duplicate_classifies_as_before(self):
        ticket = _ticket()
        one = _row(ord_no="0000001", ord_qty="000000000003", cntr_qty="000000000003")
        two = _row(ord_no="0000002", ord_qty="000000000002", cntr_qty="000000000000", cntr_uv="0")
        foreign = _row(ord_no="0000003", stk_cd="MU")
        early = _row(ord_no="0000004", ord_time="07:00:00")  # before the ticket was issued
        chosen = tickets_module.ticket_rows(
            ticket, [("2026-10-01", one), ("2026-10-01", foreign), ("2026-10-01", two), ("2026-10-01", early)],
            {("2026-10-01", "0000009")}, close_at=_close())
        self.assertIsNone(chosen["note"])
        self.assertEqual(chosen["rows"], [one, two])
        self.assertEqual(chosen["orders"], [{"ord_dt": "2026-10-01", "ord_no": "0000001"},
                                            {"ord_dt": "2026-10-01", "ord_no": "0000002"}])
        outcome = tickets_module.classify_outcome(ticket, chosen["rows"])
        self.assertEqual((outcome["state"], outcome["filled_qty"]), ("partial", 3))
        # The other existing notes are unchanged.
        self.assertEqual(tickets_module.ticket_rows(ticket, [("2026-10-01", _row(ord_no=""))], set(),
                                                    close_at=_close())["note"], "ORD_NO_UNREADABLE")
        self.assertEqual(tickets_module.ticket_rows(ticket, [("2026-10-01", _row(ord_time="x"))], set(),
                                                    close_at=_close())["note"], "ORD_TIME_UNREADABLE")
        attributed = tickets_module.ticket_rows(ticket, [("2026-10-01", _row())], {("2026-10-01", "0000001")},
                                                close_at=_close())
        self.assertEqual((attributed["rows"], attributed["note"]), ([], None))


if __name__ == "__main__":
    unittest.main()
