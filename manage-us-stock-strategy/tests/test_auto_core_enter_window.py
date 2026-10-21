"""enter-window: the ticket entry window starts at the pre-market open of the session's own KST day.

Kiwoom takes a U.S. LOC order from the pre-market open to the regular close (user 2026-10-20); the pre-market
opens 5h30m before core_open_at (17:00 KST in summer, 18:00 in winter). A Saturday ticket for Monday or a ticket
across a holiday starts on the open's KST day; the end stays the open. The user line of a new-session day and of a
carried day names the entry start (M/D(<weekday>) HH:MM); when it cannot be read it keeps "in the evening".

GoldenCauseTests: with the enter_window before this change put back, the risk1r GOLDEN hashes are the base
values again (all 8 keys), so enterWindow is the only cause of the 5 changed keys. Display only: no gate, constant,
quantity, price or outcome classification changes. All inputs are synthetic (TEST_ONLY); no network, no Kiwoom.
"""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

import test_auto_core_decide as decide_fixture  # noqa: E402
import test_auto_core_risk1r as risk1r  # noqa: E402
import test_auto_core_tickets as tickets_tests  # noqa: E402
from test_auto_core_hold_range import revert_hold_view  # noqa: E402  (close-confirm e: priceCalc band/hold off)

tk = tickets_tests.tk
decide_module = tickets_tests.decide_module
helpers = tickets_tests.helpers
KST = tk.KST

CALENDAR = helpers.calendar(helpers.sessions("2026-06-01", 130))  # summer and winter time, no holiday
# risk1r GOLDEN before enter-window (base dfa1b07): every key, measured with the old enter_window.
BASE_GOLDEN = {
    "default": "0ddc8af344e761de9af9eb90a75a226fafde6b1acd2d238d861f987fa4e20423",
    "g2b": "0857c795b26629af20982b09bb815f995ccb1d7340b9ea580031b3c6ac28bca9",
    "cash5": "c6f6158903b7727497439df2f6f6fba8c9ad15d9395f7f0eeda0a81f799db7c5",
    "research_block": "8254e97e2e1ea50b89e966120d83e942bc32d1bd34a0c19eaac3e83252273091",
    "sell": "04d0c947817377eb8f51815b0c47173988236afee41519c1eacb9a66ecbbbadc",
    "pwr": "cb46340d4e5c08df3a793fff727dc1c3537fb084f57a0b413d50dd82f7fda807",
    "decide_compare": "612f246deed9729f1d61fa7bdc913c54ddc18945a1f4f943903837bdad993955",
    "decide_apply": "91c252b86a22b15808196cc38f36c5e954bbed5734657c35990ad8b2c4f200a5",
}
UNCHANGED_KEYS = ("g2b", "cash5", "research_block")
CARRIED = ("주문표 {count}건 — {days} 발행분과 같은 주문표: "
           "이미 입력했으면 다시 넣지 않음"
           "(안 넣었으면 {when} 키움 입력)")


def _old_enter_window(issue_day, session_row):
    """enter_window as it was before enter-window (base dfa1b07): from 17:00 KST of the issue day."""
    issued = date.fromisoformat(issue_day)
    opens = datetime.fromisoformat(session_row["core_open_at"]).astimezone(KST)
    start = f"한국 {issued.month}/{issued.day} 17:00 이후 ~ "
    if opens.date() == issued:
        return start + f"정규장 개장 전({opens:%H:%M})"
    return start + f"{opens.month}/{opens.day} {opens:%H:%M} 개장 전"


def _window(issued, session, calendar=CALENDAR):
    return tk.enter_window(issued, calendar["sessions"][session])


def _kst(text):
    return datetime.fromisoformat(text).astimezone(KST)


class EnterWindowTests(unittest.TestCase):
    def test_summer_weekday_is_as_before(self):
        self.assertEqual(_window("2026-10-14", "2026-10-14"), "한국 10/14 17:00 이후 ~ 정규장 개장 전(22:30)")
        self.assertEqual(_window("2026-10-14", "2026-10-14"), _old_enter_window("2026-10-14", CALENDAR["sessions"]["2026-10-14"]))

    def test_summer_saturday_starts_on_monday(self):
        self.assertEqual(_window("2026-10-17", "2026-10-19"), "한국 10/19(월) 17:00 이후 ~ 22:30 개장 전")
        self.assertEqual(tk.entry_start("2026-10-17", CALENDAR["sessions"]["2026-10-19"]),
                         _kst("2026-10-19T17:00:00+09:00"))

    def test_after_a_holiday_starts_on_the_open_day(self):
        calendar = copy.deepcopy(CALENDAR)
        del calendar["sessions"]["2026-10-19"]  # U.S. holiday on Monday 10/19: the Saturday ticket is for Tuesday
        self.assertEqual(_window("2026-10-17", "2026-10-20", calendar), "한국 10/20(화) 17:00 이후 ~ 22:30 개장 전")

    def test_winter_starts_at_18_00(self):
        # 09:30 EST = 23:30 KST (from 11/2): the pre-market opens at 18:00 KST.
        self.assertEqual(_window("2026-11-04", "2026-11-04"), "한국 11/4 18:00 이후 ~ 정규장 개장 전(23:30)")
        self.assertEqual(_window("2026-11-07", "2026-11-09"), "한국 11/9(월) 18:00 이후 ~ 23:30 개장 전")
        self.assertEqual(tk.entry_start("2026-11-07", CALENDAR["sessions"]["2026-11-09"]),
                         _kst("2026-11-09T18:00:00+09:00"))

    def test_an_early_close_keeps_the_open(self):
        calendar = copy.deepcopy(CALENDAR)
        calendar["sessions"]["2026-07-03"].update(core_close_at="2026-07-03T13:00:00-04:00", close_type="EARLY")
        self.assertEqual(_window("2026-07-03", "2026-07-03", calendar), "한국 7/3 17:00 이후 ~ 정규장 개장 전(22:30)")
        calendar["sessions"]["2026-11-27"].update(core_close_at="2026-11-27T13:00:00-05:00", close_type="EARLY")
        self.assertEqual(_window("2026-11-27", "2026-11-27", calendar), "한국 11/27 18:00 이후 ~ 정규장 개장 전(23:30)")

    def test_the_start_is_never_before_the_issue_days_run(self):
        # Not a calendar case (the open is always on or after the issue day): the max() keeps 07:45 of the issue day.
        row = {"core_open_at": "2026-10-14T00:30:00+09:00"}
        self.assertEqual(tk.entry_start("2026-10-14", row), _kst("2026-10-14T07:45:00+09:00"))

    def test_an_unreadable_start_is_none(self):
        row = CALENDAR["sessions"]["2026-10-14"]
        for issued, session_row in ((None, row), ("x", row), ("2026-10-14", None), ("2026-10-14", {}),
                                    ("2026-10-14", {"core_open_at": None}), ("2026-10-14", {"core_open_at": "x"}),
                                    ("2026-10-14", {"core_open_at": "2026-10-14T09:30:00"})):  # no offset
            with self.subTest(issued=issued, session_row=session_row):
                self.assertIsNone(tk.entry_start(issued, session_row))

    def test_the_lead_is_display_only(self):
        self.assertEqual(tk.PREMARKET_LEAD, timedelta(hours=5, minutes=30))
        self.assertEqual(len(tk.WEEKDAYS), 7)
        self.assertEqual("".join(tk.WEEKDAYS), "월화수목금토일")
        for table in (tk.SIZING, tk.POLICY_EXPECTED, tk.S):
            self.assertFalse(any("PREMARKET" in key or "LEAD" in key for key in table))

    def test_the_ticket_carries_it(self):
        ticket = tickets_tests.tickets_of(tickets_tests.Scenario().run(), "MU", "buy")[0]
        self.assertEqual(ticket["session"], "2026-10-12")  # issued Saturday 10/10
        self.assertEqual(ticket["enterWindow"], "한국 10/12(월) 17:00 이후 ~ 22:30 개장 전")
        self.assertEqual(ticket["fillAt"], "10/13 05:00 (한국) 정규장 종가")


class NewSessionLineTests(unittest.TestCase):
    """The decide run issues on Saturday 10/10 for Monday 10/12 (test_auto_core_decide.Env)."""

    def decide(self, mode):
        env = decide_fixture.Env(holdings={"SOXL": 10}, decision_mode=mode)
        self.addCleanup(env.close)
        env.write_good_news()
        return env.run()

    def test_apply_names_the_monday_start(self):
        decision = self.decide("apply")
        self.assertEqual((decision["status"], decision["no_new_session"]), ("OK", False))
        self.assertEqual([ticket["session"] for ticket in decision["tickets"]], ["2026-10-12"])
        self.assertEqual(decision["next_action_for_user"], "주문표 1건 — 10/12(월) 17:00 이후 키움 입력")
        self.assertEqual(decision["tickets"][0]["enterWindow"], "한국 10/12(월) 17:00 이후 ~ 22:30 개장 전")

    def test_compare_has_no_user_line(self):
        decision = self.decide("compare")
        self.assertTrue(decision["tickets"])
        self.assertIsNone(decision["next_action_for_user"])

    def test_an_unreadable_start_keeps_the_evening_line(self):
        with mock.patch.object(tk, "entry_start", return_value=None):
            decision = self.decide("apply")
        self.assertEqual(len(decision["tickets"]), 1)
        self.assertEqual(decision["next_action_for_user"], "주문표 1건 — 저녁 키움 입력")

    def test_earliest_start(self):
        line = decide_module._earliest_entry_start
        self.assertEqual(line([("2026-10-14", "2026-10-14")], CALENDAR), "10/14(수) 17:00")
        self.assertEqual(line([("2026-10-17", "2026-10-19")], CALENDAR), "10/19(월) 17:00")
        # Different sessions (not normal): the earliest start is named.
        self.assertEqual(line([("2026-10-17", "2026-10-20"), ("2026-10-17", "2026-10-19")], CALENDAR), "10/19(월) 17:00")
        for pairs, calendar in (([], CALENDAR), ([("2026-10-17", "2026-10-17")], CALENDAR),  # Saturday: no session
                                ([("2026-10-17", None)], CALENDAR), ([("2026-10-17", "2026-10-19")], None),
                                ([("2026-10-17", "2026-10-19"), ("2026-10-17", "2026-10-17")], CALENDAR)):
            with self.subTest(pairs=pairs):
                self.assertIsNone(line(pairs, calendar))


class CarriedLineTests(unittest.TestCase):
    def test_a_readable_start_is_named(self):
        tickets = [{"ticket_id": "A", "issued_day": "2026-10-17", "session": "2026-10-20"}]
        self.assertEqual(decide_module._carried_entry_line([{"id": "A"}], tickets, CALENDAR),
                         CARRIED.format(count=1, days="10/17", when="10/20(화) 17:00 이후"))

    def test_the_earliest_of_two_sessions(self):
        tickets = [{"ticket_id": "A", "issued_day": "2026-10-16", "session": "2026-11-09"},
                   {"ticket_id": "B", "issued_day": "2026-10-17", "session": "2026-10-20"}]
        self.assertEqual(decide_module._carried_entry_line([{"id": "A"}, {"id": "B"}], tickets, CALENDAR),
                         CARRIED.format(count=2, days="10/16·10/17", when="10/20(화) 17:00 이후"))

    def test_an_unreadable_start_keeps_the_evening_line(self):
        cases = (
            ([{"ticket_id": "A", "issued_day": "2026-10-17", "session": "2026-10-20"}], None, "10/17"),
            ([{"ticket_id": "A", "issued_day": None, "session": "2026-10-20"}], CALENDAR, "?"),
            ([{"ticket_id": "A", "issued_day": "2026-10-17"}], CALENDAR, "10/17"),
            ([{"ticket_id": "A", "issued_day": "2026-10-17", "session": "2026-10-18"}], CALENDAR, "10/17"),  # Sunday
            ([{"ticket_id": "B", "issued_day": "2026-10-17", "session": "2026-10-20"}], CALENDAR, "?"),  # no such ticket
        )
        for tickets, calendar, days in cases:
            with self.subTest(tickets=tickets, calendar=calendar is not None):
                self.assertEqual(decide_module._carried_entry_line([{"id": "A"}], tickets, calendar),
                                 CARRIED.format(count=1, days=days, when="저녁"))
        self.assertEqual(decide_module._carried_entry_line([{"id": "A"}], [{"ticket_id": "A", "issued_day": None}]),
                         CARRIED.format(count=1, days="?", when="저녁"))


class GoldenCauseTests(unittest.TestCase):
    """The 5 changed risk1r GOLDEN keys change only because of enterWindow."""

    def measure(self):
        results = {name: item.run() for name, item in risk1r._scenarios().items()}
        views = {name: risk1r._plan_view(result["planned"]) for name, result in results.items()}
        for mode in ("compare", "apply"):
            decision = risk1r._decide(mode)[0]
            views[f"decide_{mode}"] = {"tickets": [risk1r._strip(ticket) for ticket in decision["tickets"]],
                                       "blocked": decision["blocked"], "no_action": decision["no_action"],
                                       "keys": decision["keys"]}
        return views

    @staticmethod
    def without_window(views):
        return {name: {**view, "tickets": [{key: value for key, value in ticket.items() if key != "enterWindow"}
                                           for ticket in view["tickets"]]} for name, view in views.items()}

    def test_the_old_enter_window_gives_the_base_golden(self):
        with mock.patch.object(tk, "enter_window", _old_enter_window):
            old = self.measure()
        self.assertEqual({name: risk1r._digest(revert_hold_view(view)) for name, view in old.items()}, BASE_GOLDEN)
        new = self.measure()
        measured = {name: risk1r._digest(view) for name, view in new.items()}
        self.assertEqual(measured, risk1r.GOLDEN)
        self.assertEqual({key: measured[key] for key in UNCHANGED_KEYS}, {key: BASE_GOLDEN[key] for key in UNCHANGED_KEYS})
        self.assertEqual(sorted(key for key in BASE_GOLDEN if measured[key] != BASE_GOLDEN[key]),
                         ["decide_apply", "decide_compare", "default", "pwr", "sell"])
        # Without the enterWindow field the views are the same: nothing else in a ticket changed.
        self.assertEqual(self.without_window(new), self.without_window(old))
        self.assertTrue(any(view["tickets"] for view in new.values()))


if __name__ == "__main__":
    unittest.main()
