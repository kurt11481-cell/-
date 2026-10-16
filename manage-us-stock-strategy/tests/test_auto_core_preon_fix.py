"""pre-on-fix: three core fixes before decision_mode apply (redesign-t2 judge2 G 1, 4, 6).

Fix 4: on a no-new-session day the user line of the carried order rows names their issue day and says not to
enter them again if already entered. Fix 1 (r4 E): on the last order day (the KST day of the session's close)
only rows placed at or before the close count for the ticket. Fix 6: G0_TICKET_SESSION_NOT_YET on a new-session
day is pushed as an exception (gate0 and the HOLD are unchanged).

All inputs are synthetic (TEST_ONLY), built on test_auto_core_decide.Env. No network, no Kiwoom.
"""

from __future__ import annotations

import copy
import shutil
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_tickets as tickets_module  # noqa: E402
import helpers  # noqa: E402
import test_auto_core_decide as decide_fixture  # noqa: E402
from validation_common import load_json, validate_instance, write_json  # noqa: E402

SELL = tickets_module.SIDE_NAMES["sell"]
SATURDAY, MONDAY, TUESDAY = decide_fixture.SATURDAY, decide_fixture.MONDAY, decide_fixture.TUESDAY
HOLIDAY_DAYS = [day for day in decide_fixture.R3_DAYS if day != MONDAY]  # U.S. holiday on Monday 10/19
CALENDAR = helpers.calendar(helpers.sessions("2026-09-01", 80))
# "<n> tickets - <days> issue: if already entered do not enter again (if not, enter in Kiwoom in the evening)"
CARRIED = ("주문표 {count}건 — {days} 발행분과 같은 주문표: "
           "이미 입력했으면 다시 넣지 않음"
           "(안 넣었으면 저녁 키움 입력)")
NEW_SESSION_LINE = "주문표 {count}건 — 저녁 키움 입력"
NOT_YET_LINE = "주문표 세션 이전 상태 — 새 주문표 없음, Cowork 확인"


# ---------------------------------------------------------------------------------------------
# Fix 4: the no-new-session day's entry line
# ---------------------------------------------------------------------------------------------

class NoNewSessionEntryLineTests(unittest.TestCase):
    """Saturday 10/17 issues a ticket for Tuesday 10/20; Monday 10/19 is a U.S. holiday, so the Tuesday 07:45 KST
    run has no new session and carries the order row."""

    def make_env(self, mode):
        self.env = decide_fixture.Env(decision_mode=mode)
        self.addCleanup(self.env.close)
        self.base = self.env.run()  # a real record to copy (its journal entry is dropped again below)
        write_json(self.env.journal, decide_fixture.EMPTY_JOURNAL)

    def source(self, extra=()):
        """Saturday's ledger source with one ticket for Tuesday, plus extra open tickets (each with its row)."""
        ticket = decide_fixture._fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
        ticket.update(ticket_id="AT-20261017-SOXL-1", session=TUESDAY, issuedAt=f"{SATURDAY} 07:45 KST")
        del ticket["issued_day"]
        ids = [ticket["ticket_id"]] + [item["ticket_id"] for item in extra]
        record = copy.deepcopy(self.base)
        record.update(run_day_kst=SATURDAY, evaluation_session="2026-10-16", buy_session=MONDAY, tickets=[ticket],
                      open_tickets=list(extra), keys={}, f6_ran=True, carried_from=None,
                      dashboard={"runCore": {**self.base["dashboard"]["runCore"],
                                             "tickets": [{"id": item} for item in ids]},
                                 "orders": [{"id": item, "session": TUESDAY, "outcome": {"state": "pending"}}
                                            for item in ids]})
        (self.env.output / SATURDAY).mkdir()
        write_json(self.env.output / SATURDAY / "decision.json", record)
        return ticket

    def run_on(self, day, reader=None):
        folder = self.env.output / day
        folder.mkdir(exist_ok=True)
        for name in ("result.json", "reconcile.json", "kiwoom_broker_snapshot.shadow.json"):
            shutil.copyfile(self.env.day_dir / name, folder / name)
        return self.env.run(now=decide_fixture._morning(day), reader=reader or decide_fixture.FakeReader(),
                            calendar_loader=lambda now: helpers.calendar(HOLIDAY_DAYS))

    def test_one_carried_ticket_names_its_issue_day(self):
        self.make_env("apply")
        ticket = self.source()
        reader = decide_fixture.FakeReader()
        quiet = self.run_on(TUESDAY, reader)
        self.assertEqual((quiet["status"], quiet["no_new_session"]), ("OK", True))
        self.assertEqual(quiet["next_action_for_user"], CARRIED.format(count=1, days="10/17"))
        # Display only: the carried rows, the files and the reads of that day are as before.
        self.assertEqual(quiet["dashboard"]["orders"],
                         [{"id": ticket["ticket_id"], "session": TUESDAY, "outcome": {"state": "pending"}}])
        self.assertEqual(reader.requests, [])
        self.assertEqual(sorted(path.name for path in (self.env.output / TUESDAY).iterdir()),
                         ["decision.json", "kiwoom_broker_snapshot.shadow.json", "reconcile.json", "result.json"])
        self.assertEqual(validate_instance(load_json(self.env.output / TUESDAY / "decision.json"),
                                           decide_module.DECISION_SCHEMA), [])
        # Fix 6 leaves this path alone: a ticket before its session stays open without a reason or a push.
        self.assertEqual(quiet["reasons"], [])
        self.assertEqual([(alert["code"], alert["push"]) for alert in quiet["alerts"]], [("NO_NEW_SESSION", False)])

    def test_two_issue_days_are_both_named(self):
        self.make_env("apply")
        friday = decide_fixture._fake_ticket("SOXL", "buy", 3, 95.0, mode="apply")
        friday.update(ticket_id="AT-20261016-SOXL-1", session=TUESDAY, issued_day="2026-10-16", decision_key="d" * 64)
        self.source(extra=[friday])
        quiet = self.run_on(TUESDAY)
        self.assertEqual(quiet["inputs"]["no_new_session"]["not_yet"], ["AT-20261016-SOXL-1", "AT-20261017-SOXL-1"])
        self.assertEqual(quiet["next_action_for_user"], CARRIED.format(count=2, days="10/16·10/17"))

    def test_compare_mode_has_no_user_line(self):
        self.make_env("compare")
        ticket = self.source()
        quiet = self.run_on(TUESDAY)
        self.assertEqual((quiet["no_new_session"], [order["id"] for order in quiet["dashboard"]["orders"]]),
                         (True, [ticket["ticket_id"]]))
        self.assertIsNone(quiet["next_action_for_user"])

    def test_the_new_session_day_line_is_unchanged(self):
        env = decide_fixture.Env(holdings={"SOXL": 10}, decision_mode="apply")
        self.addCleanup(env.close)
        env.write_good_news()
        decision = env.run()
        self.assertEqual((decision["status"], decision["no_new_session"]), ("OK", False))
        self.assertEqual(len(decision["tickets"]), 1, decision["blocked"])
        self.assertEqual(decision["next_action_for_user"], NEW_SESSION_LINE.format(count=1))

    def test_an_unreadable_issue_day_shows_as_unknown(self):
        line = decide_module._carried_entry_line([{"id": "A"}], [{"ticket_id": "A", "issued_day": None}])
        self.assertEqual(line, CARRIED.format(count=1, days="?"))


# ---------------------------------------------------------------------------------------------
# Fix 1: rows after the session close on the last order day
# ---------------------------------------------------------------------------------------------

def _ticket(session="2026-10-14", issued_at="2026-10-14 07:45 KST", issued_day="2026-10-14"):
    ticket = decide_fixture._fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
    ticket.update(ticket_id=f"AT-{issued_day.replace('-', '')}-SOXL-1", session=session, issuedAt=issued_at,
                  issued_day=issued_day)
    return ticket


def _row(number, placed):
    row = helpers.fill_row("SOXL", SELL, ordered=5, filled=5, price="95.00", fill_price="96.10")
    row.update(ord_no=number, ord_time=placed)
    return row


def _chosen(ticket, dated_rows, calendar=CALENDAR):
    return tickets_module.ticket_rows(ticket, dated_rows, set(),
                                      close_at=tickets_module.session_close(ticket, calendar))


class SessionCloseBoundTests(unittest.TestCase):
    def test_close_is_the_calendar_close_in_kst(self):
        self.assertEqual(tickets_module.session_close(_ticket(), CALENDAR).isoformat(), "2026-10-15T05:00:00+09:00")
        winter = _ticket(session="2026-11-04", issued_at="2026-11-04 07:45 KST", issued_day="2026-11-04")
        self.assertEqual(tickets_module.session_close(winter, CALENDAR).isoformat(), "2026-11-05T06:00:00+09:00")
        self.assertIsNone(tickets_module.session_close(_ticket(session="2026-10-17"), CALENDAR))  # Saturday

    def test_a_row_after_the_summer_close_is_left_out(self):
        ticket = _ticket()
        late = _chosen(ticket, [("2026-10-15", _row("0000001", "05:30:00"))])
        self.assertEqual((late["note"], late["rows"], late["orders"]), (None, [], []))
        self.assertEqual(tickets_module.classify_outcome(ticket, late["rows"])["state"], "not_entered")
        # The close itself and the minute before count.
        kept = _chosen(ticket, [("2026-10-15", _row("0000002", "04:59:00")), ("2026-10-15", _row("0000003", "050000"))])
        self.assertEqual(kept["orders"], [{"ord_dt": "2026-10-15", "ord_no": "0000002"},
                                          {"ord_dt": "2026-10-15", "ord_no": "0000003"}])
        self.assertEqual(tickets_module.classify_outcome(ticket, kept["rows"][:1])["state"], "filled")

    def test_the_winter_close_is_06_00(self):
        ticket = _ticket(session="2026-11-04", issued_at="2026-11-04 07:45 KST", issued_day="2026-11-04")
        chosen = _chosen(ticket, [("2026-11-05", _row("0000001", "05:30:00")), ("2026-11-05", _row("0000002", "06:01:00"))])
        self.assertEqual(chosen["orders"], [{"ord_dt": "2026-11-05", "ord_no": "0000001"}])

    def test_an_early_close_uses_its_own_time(self):
        calendar = copy.deepcopy(CALENDAR)
        calendar["sessions"]["2026-11-27"].update(core_close_at="2026-11-27T13:00:00-05:00", close_type="EARLY")
        ticket = _ticket(session="2026-11-27", issued_at="2026-11-27 07:45 KST", issued_day="2026-11-27")
        late = _chosen(ticket, [("2026-11-28", _row("0000001", "03:30:00"))], calendar)
        self.assertEqual((late["note"], late["orders"]), (None, []))
        kept = _chosen(ticket, [("2026-11-28", _row("0000002", "02:59:00"))], calendar)
        self.assertEqual(kept["orders"], [{"ord_dt": "2026-11-28", "ord_no": "0000002"}])

    def test_an_unreadable_order_time_on_the_last_day_is_unknown(self):
        for placed in ("", "x", "25:00:00"):
            with self.subTest(placed=placed):
                chosen = _chosen(_ticket(), [("2026-10-15", _row("0000001", placed))])
                self.assertEqual(chosen, {"rows": [], "orders": [], "note": "ORD_TIME_UNREADABLE"})

    def test_an_unknown_close_is_order_window_unknown(self):
        self.assertEqual(tickets_module.ticket_rows(_ticket(), [("2026-10-14", _row("0000001", "17:30:00"))], set(),
                                                    close_at=None),
                         {"rows": [], "orders": [], "note": "ORDER_WINDOW_UNKNOWN"})

    def test_the_issue_day_bound_is_unchanged(self):
        ticket = _ticket()
        chosen = _chosen(ticket, [("2026-10-14", _row("0000001", "07:44:59")), ("2026-10-14", _row("0000002", "07:45:00")),
                                  ("2026-10-14", _row("0000003", "23:30:00"))])
        self.assertEqual([order["ord_no"] for order in chosen["orders"]], ["0000002", "0000003"])
        self.assertEqual(_chosen(ticket, [("2026-10-14", _row("0000001", ""))])["note"], "ORD_TIME_UNREADABLE")

    def test_issue_day_and_last_day_the_same_applies_both_bounds(self):
        # Issued at 00:10 KST on 10/15 for the 10/14 session (close 05:00 KST on 10/15).
        ticket = _ticket(session="2026-10-14", issued_at="2026-10-15 00:10 KST", issued_day="2026-10-15")
        self.assertEqual(tickets_module.order_days(ticket, CALENDAR), ["2026-10-15"])
        chosen = _chosen(ticket, [("2026-10-15", _row("0000001", "00:05:00")), ("2026-10-15", _row("0000002", "01:00:00")),
                                  ("2026-10-15", _row("0000003", "05:30:00"))])
        self.assertEqual([order["ord_no"] for order in chosen["orders"]], ["0000002"])


class ReadOutcomesCloseTests(unittest.TestCase):
    """Fix 1 through read_outcomes (the ticket of session 2026-10-01 closes at 05:00 KST on 10/02)."""

    def read(self, rows, calendar=None):
        ticket = decide_fixture._fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
        reader = decide_fixture.FakeReader(fills=rows)
        block = decide_module.read_outcomes(
            [ticket], reader=reader, runtime=Path("."), rate_policy={}, run_day="2026-10-02", reconcile_fills=None,
            evaluation_session="2026-10-01", calendar=calendar or helpers.calendar(decide_fixture.CALENDAR_DAYS),
            attributed_orders=[])
        return ticket, block

    def test_a_row_after_the_close_is_not_the_tickets(self):
        ticket, block = self.read({"20261002": [_row("0000001", "05:30:00")]})
        self.assertEqual([(item["ticket_id"], item["state"]) for item in block["outcomes"]],
                         [(ticket["ticket_id"], "not_entered")])
        self.assertEqual(block["attributed"], [])
        ticket, block = self.read({"20261002": [_row("0000001", "04:59:00")]})
        self.assertEqual([item["state"] for item in block["outcomes"]], ["filled"])
        self.assertEqual(block["attributed"], [{"ord_dt": "2026-10-02", "ord_no": "0000001",
                                                "ticket_id": ticket["ticket_id"]}])

    def test_an_unreadable_last_day_time_leaves_the_ticket_open(self):
        ticket, block = self.read({"20261002": [_row("0000001", "")]})
        self.assertEqual((block["outcomes"], [item["ticket_id"] for item in block["open_tickets"]]),
                         ([], [ticket["ticket_id"]]))
        self.assertIn(f"OUTCOME_UNKNOWN:{ticket['ticket_id']}", block["reasons"])

    def test_an_unreadable_close_is_order_window_unknown(self):
        calendar = helpers.calendar(decide_fixture.CALENDAR_DAYS)
        calendar["sessions"]["2026-10-01"]["core_close_at"] = "2026-10-01T16:00:00"  # no offset: not a known time
        ticket, block = self.read({"20261001": [_row("0000001", "17:30:00")]}, calendar)
        self.assertEqual(block["outcomes"], [])
        self.assertEqual([item["ticket_id"] for item in block["open_tickets"]], [ticket["ticket_id"]])
        self.assertIn(f"ORDER_WINDOW_UNKNOWN:{ticket['ticket_id']}", block["reasons"])
        self.assertIn(f"OUTCOME_UNKNOWN:{ticket['ticket_id']}", block["reasons"])


# ---------------------------------------------------------------------------------------------
# Fix 6: G0_TICKET_SESSION_NOT_YET is pushed
# ---------------------------------------------------------------------------------------------

class TicketSessionNotYetAlertTests(unittest.TestCase):
    def run_with_early_ticket(self, mode):
        env = decide_fixture.Env(holdings={"SOXL": 10}, decision_mode=mode)
        self.addCleanup(env.close)
        first = env.run()
        write_json(env.journal, decide_fixture.EMPTY_JOURNAL)
        early = decide_fixture._fake_ticket("SOXL", "sell", 5, 95.0, mode=mode)
        early["session"] = "2026-10-12"  # after this run's evaluation session 2026-10-09
        later = decide_fixture._fake_ticket("MU", "buy", 1, 95.0, mode=mode)
        later.update(session="2026-10-13", decision_key="e" * 64)
        previous = decide_fixture._as_of(copy.deepcopy(first), "2026-10-01")
        previous.update(tickets=[early, later], open_tickets=[])
        (env.output / "2026-10-01").mkdir()
        write_json(env.output / "2026-10-01" / "decision.json", previous)
        reader = decide_fixture.FakeReader()
        return early, later, reader, env.run(reader=reader)

    def test_the_anomaly_is_pushed_and_the_hold_is_unchanged(self):
        for mode in ("compare", "apply"):
            with self.subTest(mode=mode):
                early, later, reader, decision = self.run_with_early_ticket(mode)
                self.assertEqual((decision["status"], decision["no_new_session"], decision["tickets"]), ("HOLD", False, []))
                for ticket in (early, later):
                    self.assertIn(f"G0_TICKET_SESSION_NOT_YET:{ticket['ticket_id']}", decision["reasons"])
                self.assertEqual(sorted(item["ticket_id"] for item in decision["open_tickets"]),
                                 sorted([early["ticket_id"], later["ticket_id"]]))
                self.assertEqual([request["operation"] for request in reader.requests], ["account_open_items"])
                found = [alert for alert in decision["alerts"] if alert["code"] == "G0_TICKET_SESSION_NOT_YET"]
                self.assertEqual(found, [{"code": "G0_TICKET_SESSION_NOT_YET", "line": NOT_YET_LINE, "push": True}])
                self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])

    def test_no_alert_without_the_reason(self):
        env = decide_fixture.Env()
        self.addCleanup(env.close)
        decision = env.run()
        self.assertFalse(any(reason.startswith("G0_TICKET_SESSION_NOT_YET") for reason in decision["reasons"]))
        self.assertNotIn("G0_TICKET_SESSION_NOT_YET", [alert["code"] for alert in decision["alerts"]])


if __name__ == "__main__":
    unittest.main()
