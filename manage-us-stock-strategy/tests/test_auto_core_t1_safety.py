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


class Ev4BackfillTests(unittest.TestCase):
    def setUp(self):
        self.env = decide_fixture.Env()
        self.addCleanup(self.env.close)
        self.base = self.env.run()  # a real F1 record to copy (today's file is written again by each run)

    # -- helpers -------------------------------------------------------------------------------
    def record(self, session, *, account=None, before_f1=False):
        """A previous decision.json of the run day that evaluates `session`."""
        item = decide_fixture._as_of(copy.deepcopy(self.base), run_day_of(session))
        self.assertEqual(item["evaluation_session"], session)
        if account is not None:
            item["account"] = account
        if before_f1:  # a FAIL after the calendar, before F1: no account
            item.update(status="FAIL", reasons=["UNEXPECTED_ERROR:TEST_ONLY"], account={}, f6_ran=False, tickets=[])
        folder = self.env.output / run_day_of(session)
        folder.mkdir(exist_ok=True)
        write_json(folder / decide_module.DECISION_FILE, item)
        return item

    def snapshot(self, session, cash, quantity=40):
        folder = self.env.output / run_day_of(session)
        folder.mkdir(exist_ok=True)
        write_json(folder / decide_module.SNAPSHOT_FILE, {
            "holdings": [{"ticker": "SOXL", "held_quantity": quantity}],
            "cash": {"order_available_cash": float(cash), "foreign_currency_deposit": float(cash)}})

    def total_of(self, session, cash, quantity=40):
        return Decimal(quantity) * self.env.bars["SOXL"]["raw"]["sessions"][session]["close"] + Decimal(cash)

    def line(self):
        """The EV4 line of today's S7 hwm (the hwm a session without a record is judged with)."""
        hwm = self.base["account"]["s7_hwm_usd"]
        return max(rules.C["V6_FIRST_LINE_USD"], Decimal(str(hwm)) * rules.C["RREC_EV4_HWM_FRACTION"])

    def pair(self):
        new = self.env.run()
        with mock.patch.object(decide_module, "ev4_backfill_plan", without_backfill):
            old = self.env.run()
        self.assertEqual(validate_instance(new, decide_module.DECISION_SCHEMA), [])
        self.assertEqual(old["ev4_backfill"], [])
        return new, old

    @staticmethod
    def ev4_dates(decision):
        return [event["date"] for event in decision["shock"]["events"] if "EV4" in event["kinds"]]

    @staticmethod
    def undetermined(decision):
        return [alert for alert in decision["alerts"] if alert["code"] == "EV4_UNDETERMINED"]

    # -- S1-S6 ---------------------------------------------------------------------------------
    def test_s1_record_before_f1_with_snapshot_below_the_line_is_rebuilt_and_opens_rrec1(self):
        self.record(S3, before_f1=True)
        self.snapshot(S3, "20000.00")
        total = self.total_of(S3, "20000.00")
        self.assertTrue(rules.ev4_open(total, self.base["account"]["s7_hwm_usd"]))  # below the line
        new, old = self.pair()
        self.assertEqual(new["ev4_backfill"], [{"session": S3, "method": "REBUILT", "ev4_open": True,
                                                "total": float(total), "neighbors": [], "reason": None}])
        self.assertIn(S3, self.ev4_dates(new))
        self.assertNotIn(S3, self.ev4_dates(old))  # the session lost before t1-safety
        self.assertTrue(new["shock"]["open"])
        self.assertEqual(self.undetermined(new), [])

    def test_s1_record_without_evaluation_session_counts_from_its_run_day(self):
        """A HOLD before the calendar (T1 result missing) has no evaluation session: the session it would have
        evaluated (the last one before its run day) is the first decide session."""
        hold = decide_fixture._as_of(copy.deepcopy(self.base), run_day_of(S3))
        hold.update(evaluation_session=None, buy_session=None, status="HOLD", reasons=["T1_RESULT_MISSING"],
                    account={}, f6_ran=False)
        (self.env.output / run_day_of(S3)).mkdir()
        write_json(self.env.output / run_day_of(S3) / decide_module.DECISION_FILE, hold)
        self.snapshot(S3, "20000.00")
        new, _old = self.pair()
        self.assertEqual([(entry["session"], entry["method"], entry["ev4_open"]) for entry in new["ev4_backfill"]],
                         [(S3, "REBUILT", True)])
        self.assertIn(S3, self.ev4_dates(new))

    def test_s2_rebuilt_above_the_line_changes_nothing_else(self):
        self.record(S3, before_f1=True)
        self.snapshot(S3, "30000.00")
        total = self.total_of(S3, "30000.00")
        self.assertFalse(rules.ev4_open(total, self.base["account"]["s7_hwm_usd"]))
        new, old = self.pair()
        self.assertEqual(new["ev4_backfill"], [{"session": S3, "method": "REBUILT", "ev4_open": False,
                                                "total": float(total), "neighbors": [], "reason": None}])
        self.assertEqual(self.ev4_dates(new), [])
        self.assertEqual(self.undetermined(new), [])
        self.assertEqual(comparable(new), comparable(old))  # golden: everything else as before

    def neighbor_case(self, factor):
        """A full F1 record of S1 whose total is `factor` x the EV4 line; no record and no snapshot for S2, S3."""
        total = (self.line() * factor).quantize(Decimal("0.01"))
        account = dict(self.base["account"], total=float(total), s7_hwm_usd=self.base["account"]["s7_hwm_usd"])
        account["ev4_open"] = rules.ev4_open(total, account["s7_hwm_usd"])
        self.assertFalse(account["ev4_open"])  # the neighbour itself is not an EV4 day
        self.record(S1, account=account)
        # Today's total is far above the line (the after-neighbour of S3).
        today = Decimal(str(self.base["account"]["total"]))
        self.assertFalse(rules.ev4_open(today / rules.C["RREC_EV4_NEIGHBOR_MARGIN"], self.base["account"]["s7_hwm_usd"]))
        return self.pair()

    def test_s3_no_record_no_snapshot_neighbor_within_three_percent_opens(self):
        new, old = self.neighbor_case(Decimal("1.02"))
        self.assertEqual([(entry["session"], entry["method"], entry["ev4_open"], entry["reason"])
                          for entry in new["ev4_backfill"]],
                         [(S2, "NEIGHBOR_NEAR", True, "SNAPSHOT_MISSING"), (S3, "NEIGHBOR_NEAR", True, "SNAPSHOT_MISSING")])
        self.assertEqual([entry["neighbors"] for entry in new["ev4_backfill"]], [[S1, LAST], [S1, LAST]])
        self.assertEqual(self.ev4_dates(new), [S2, S3])
        self.assertEqual(self.ev4_dates(old), [])
        alerts = self.undetermined(new)
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0]["push"])
        self.assertTrue(alerts[0]["line"].startswith(f"EV4_UNDETERMINED:{S2},{S3}"))
        self.assertTrue(new["shock"]["open"])

    def test_s4_no_record_no_snapshot_neighbors_far_stays_closed_with_a_push(self):
        new, old = self.neighbor_case(Decimal("1.05"))
        self.assertEqual([(entry["session"], entry["method"], entry["ev4_open"]) for entry in new["ev4_backfill"]],
                         [(S2, "NEIGHBOR_CLEAR", False), (S3, "NEIGHBOR_CLEAR", False)])
        self.assertEqual(self.ev4_dates(new), [])
        alerts = self.undetermined(new)
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0]["push"])
        self.assertTrue(alerts[0]["line"].startswith(f"EV4_UNDETERMINED:{S2},{S3}"))
        # Only the backfill entries and the push differ from before.
        new_view = comparable(new)
        new_view["alerts"] = [alert for alert in new_view["alerts"] if alert["code"] != "EV4_UNDETERMINED"]
        self.assertEqual(new_view, comparable(old))

    def test_s4_snapshot_without_the_holding_bars_is_not_rebuilt(self):
        self.record(S2)
        self.record(S3, before_f1=True)
        folder = self.env.output / run_day_of(S3)
        write_json(folder / decide_module.SNAPSHOT_FILE, {
            "holdings": [{"ticker": "ZZZZ", "held_quantity": 3}],
            "cash": {"order_available_cash": 30000.0, "foreign_currency_deposit": 30000.0}})
        new, _old = self.pair()
        self.assertEqual([(entry["session"], entry["method"], entry["reason"]) for entry in new["ev4_backfill"]],
                         [(S3, "NEIGHBOR_CLEAR", "CLOSE_MISSING:ZZZZ")])
        self.assertEqual(len(self.undetermined(new)), 1)

    def test_s5_sessions_before_the_first_record_are_not_targets(self):
        self.record(S3)  # the first (and only) record evaluated S3 through F1; nothing before it is looked at
        new, old = self.pair()
        self.assertEqual(new["ev4_backfill"], [])
        self.assertEqual(self.undetermined(new), [])
        self.assertEqual(comparable(new), comparable(old))

    def test_s5_existing_fixture_without_records_is_unchanged(self):
        new, old = self.pair()
        self.assertEqual(new["ev4_backfill"], [])
        self.assertEqual(comparable(new), comparable(old))

    def test_s6_every_record_reached_f1_gives_the_same_decision(self):
        env = decide_fixture.Env(holdings={"SOXL": 10})
        self.addCleanup(env.close)
        env.write_good_news()
        base = env.run()
        for session in (S1, S2, S3):
            item = decide_fixture._as_of(copy.deepcopy(base), run_day_of(session))
            (env.output / run_day_of(session)).mkdir()
            write_json(env.output / run_day_of(session) / decide_module.DECISION_FILE, item)
        new = env.run()
        with mock.patch.object(decide_module, "ev4_backfill_plan", without_backfill):
            old = env.run()
        self.assertEqual(validate_instance(new, decide_module.DECISION_SCHEMA), [])
        self.assertEqual(new["ev4_backfill"], [])
        for key in ("tickets", "buy_requirements", "reasons", "shock", "account", "exposure", "alerts", "status"):
            self.assertEqual(new[key], old[key], key)
        self.assertEqual(comparable(new), comparable(old))

    def test_record_before_f1_is_absent_key_and_schema_valid(self):
        write_json(self.env.day_dir / "result.json", {"status": "FAIL"})
        decision = self.env.run()
        self.assertEqual(decision["status"], "HOLD")
        self.assertNotIn("ev4_backfill", decision)
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])


class Ev4ResolveTests(unittest.TestCase):
    """ev4_backfill_resolve on a plan alone: the record's own hwm comes first; no known total is open."""

    def test_record_hwm_is_used_before_todays(self):
        plan = {"targets": ["2026-10-07"], "rebuilt": {"2026-10-07": (Decimal("27000"), None)}, "known": {},
                "hwm": {"2026-10-07": "30000"}}
        entries = decide_module.ev4_backfill_resolve(plan, hwm="40000", total=None, evaluation_session="2026-10-09")
        self.assertEqual((entries[0]["method"], entries[0]["ev4_open"]), ("REBUILT", True))  # 27000 <= 30000 x 0.9
        plan["hwm"] = {}
        entries = decide_module.ev4_backfill_resolve(plan, hwm="29000", total=None, evaluation_session="2026-10-09")
        self.assertFalse(entries[0]["ev4_open"])  # 27000 > 29000 x 0.9 and > the V6 first line

    def test_no_known_total_is_open(self):
        plan = {"targets": ["2026-10-07"], "rebuilt": {"2026-10-07": (None, "SNAPSHOT_MISSING")}, "known": {},
                "hwm": {}}
        entries = decide_module.ev4_backfill_resolve(plan, hwm=None, total=None, evaluation_session="2026-10-09")
        self.assertEqual((entries[0]["method"], entries[0]["ev4_open"], entries[0]["neighbors"]),
                         ("NEIGHBOR_NONE", True, []))

    def test_no_plan_is_nothing(self):
        self.assertEqual(decide_module.ev4_backfill_resolve(None, hwm=None, total=None, evaluation_session="x"), [])

    def test_margin_constant_names_its_source(self):
        value, source = rules.CONSTANTS["RREC_EV4_NEIGHBOR_MARGIN"]
        self.assertEqual(value, Decimal("1.03"))
        self.assertEqual((rules.C["V6_FIRST_LINE_USD"] * value).quantize(Decimal("0.01")), Decimal("26395.35"))
        self.assertIn("V6 approach", source)


# ---------------------------------------------------------------------------------------------
# Fix 2: duplicate (ord_dt, ord_no) rows in F6
# ---------------------------------------------------------------------------------------------

def _ticket():
    return decide_fixture._fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")


def _row(**overrides):
    row = helpers.fill_row("SOXL", SELL, ordered=5, filled=5, price="95.00", fill_price="96.10")
    row.update(overrides)
    return row


class DuplicateOrderNumberTests(unittest.TestCase):
    def test_f1_the_same_row_twice_counts_once(self):
        ticket = _ticket()
        chosen = tickets_module.ticket_rows(ticket, [("2026-10-01", _row()), ("2026-10-01", _row())], set())
        self.assertIsNone(chosen["note"])
        self.assertEqual(chosen["orders"], [{"ord_dt": "2026-10-01", "ord_no": "0000001"}])
        outcome = tickets_module.classify_outcome(ticket, chosen["rows"])
        self.assertEqual((outcome["state"], outcome["filled_qty"], outcome["rows"]), ("filled", 5, 1))

    def test_f2_a_different_row_with_the_same_order_number_is_unknown(self):
        ticket = _ticket()
        for name, other in (("fill", _row(cntr_qty="000000000003")), ("other_ticker", _row(stk_cd="SOXS"))):
            with self.subTest(case=name):
                chosen = tickets_module.ticket_rows(ticket, [("2026-10-01", _row()), ("2026-10-01", other)], set())
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
                     ("2026-10-02", _row(ord_qty="000000000002", cntr_qty="000000000002"))], set())
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
            {("2026-10-01", "0000009")})
        self.assertIsNone(chosen["note"])
        self.assertEqual(chosen["rows"], [one, two])
        self.assertEqual(chosen["orders"], [{"ord_dt": "2026-10-01", "ord_no": "0000001"},
                                            {"ord_dt": "2026-10-01", "ord_no": "0000002"}])
        outcome = tickets_module.classify_outcome(ticket, chosen["rows"])
        self.assertEqual((outcome["state"], outcome["filled_qty"]), ("partial", 3))
        # The other existing notes are unchanged.
        self.assertEqual(tickets_module.ticket_rows(ticket, [("2026-10-01", _row(ord_no=""))], set())["note"],
                         "ORD_NO_UNREADABLE")
        self.assertEqual(tickets_module.ticket_rows(ticket, [("2026-10-01", _row(ord_time="x"))], set())["note"],
                         "ORD_TIME_UNREADABLE")
        attributed = tickets_module.ticket_rows(ticket, [("2026-10-01", _row())], {("2026-10-01", "0000001")})
        self.assertEqual((attributed["rows"], attributed["note"]), ([], None))


if __name__ == "__main__":
    unittest.main()
