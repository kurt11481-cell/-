"""rrec-rg1 bootstrap B: R-REC1 RG1 needs a research record only for the sessions after the event from the first
recorded session in the window (ev3b_coverage_start) on; earlier sessions could not have one (EV3 (a) covers them)
and are listed as rg1_coverage.before_first_record. No record in the window keeps RG1 unknown.

Synthetic series only (TEST_ONLY): a flat zigzag benchmark (close 494/506 around EMA50 500, sigma60 about 2.4%).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))

import auto_core_rules as rules  # noqa: E402
import helpers  # noqa: E402


def bench(closes):
    days = helpers.sessions("2026-03-02", len(closes))
    return rules.build_series(helpers.bars("SOXX", days, closes)["adjusted"], days, days[-1]), days


def run_rrec1(data, **kwargs):
    arguments = dict(benchmark=data, candidate=None, evaluation_session=data["days"][-1], ev3_user_dates=[],
                     thesis_damage=[], ev4_sessions=[])
    arguments.update(kwargs)
    return rules.rrec1(**arguments)


class BootstrapTests(unittest.TestCase):
    """EV3a five sessions back on a high day (C0 506, never closed above again: RG3 no, the event stays open)."""

    def setUp(self):
        self.data, self.days = bench(helpers.zigzag(81, 500, 6.0))
        self.event = len(self.days) - 1 - 5
        self.after = self.days[self.event + 1:]
        self.first = self.event + 2          # the first research record: one session after the event has none
        self.records = self.days[self.first:]

    def run_event(self, **kwargs):
        return run_rrec1(self.data, ev3_user_dates=[self.days[self.event]], **kwargs)

    def coverage(self, missing, before=None):
        value = {"from": self.days[self.event + 1], "to": self.days[-1], "missing_sessions": missing}
        if before is not None:
            value["before_first_record"] = before
        return value

    def test_fixture(self):
        result = self.run_event(research_sessions=self.days)
        self.assertEqual((result["event"]["date"], result["event"]["kinds"]), (self.days[self.event], ["EV3a"]))
        self.assertEqual([item["date"] for item in result["events"]], [self.days[self.event]])
        self.assertEqual((result["open"], result["rg"]["RG3"]), (True, "no"))

    def test_b1_session_before_the_first_record_is_left_out(self):
        result = self.run_event(research_sessions=self.records)
        self.assertEqual(result["ev3b_coverage_start"], self.days[self.first])
        self.assertEqual((result["open"], result["rg"]["RG1"]), (True, "ok"))
        self.assertEqual(result["rg1_coverage"], self.coverage([], [self.days[self.event + 1]]))
        self.assertEqual(result["reasons"], [])

    def test_b2_a_session_after_the_first_record_is_still_needed(self):
        missing = len(self.days) - 2  # an up day: not a 1-sigma fall, so no EV3 (b) record gap
        self.assertGreater(missing, self.first)
        self.assertGreater(self.data["ret1"][missing], 0)
        result = self.run_event(research_sessions=[day for day in self.records if day != self.days[missing]])
        self.assertEqual((result["status"], result["open"], result["rg"]["RG1"]), ("unk", True, "unk"))
        self.assertEqual(result["rg1_coverage"], self.coverage([self.days[missing]], [self.days[self.event + 1]]))
        self.assertFalse(any(reason.startswith("EV3B_RECORD_GAP") for reason in result["reasons"]))

    def test_b3_no_record_in_the_window_is_not_left_out(self):
        result = self.run_event(research_sessions=[])
        self.assertIsNone(result["ev3b_coverage_start"])
        self.assertEqual((result["status"], result["rg"]["RG1"]), ("unk", "unk"))
        self.assertEqual(result["rg1_coverage"], self.coverage(self.after))
        self.assertNotIn("before_first_record", result["rg1_coverage"])

    def test_b4_damage_fact_after_the_first_record_is_no(self):
        damaged = len(self.days) - 2  # an up day: the fact adds no EV3 (b) event
        self.assertGreater(self.data["ret1"][damaged], 0)
        damage = [{"fact_id": "D1", "event_session": self.days[damaged], "root_thesis_damage": True}]
        result = self.run_event(research_sessions=self.records, thesis_damage=damage)
        self.assertEqual(result["event"]["kinds"], ["EV3a"])
        self.assertEqual((result["status"], result["open"], result["rg"]["RG1"]), ("no", True, "no"))
        self.assertEqual(result["rg1_coverage"], self.coverage([], [self.days[self.event + 1]]))

    def test_b5_untracked_records_are_unchanged(self):
        result = self.run_event(research_sessions=None)
        self.assertIsNone(result["rg1_coverage"])
        self.assertIsNone(result["ev3b_coverage_start"])
        self.assertEqual(result["rg"]["RG1"], "ok")
        full = self.run_event(research_sessions=self.days)
        self.assertEqual((result["status"], result["open"], result["rg"]), (full["status"], full["open"], full["rg"]))
        unknown = self.run_event(research_sessions=None, thesis_damage=None)
        self.assertEqual(unknown["rg"]["RG1"], "unk")  # no research record at all: RG1 unknown as before

    def test_b7_records_from_before_the_event_are_unchanged(self):
        # Ordinary operation: the first record is before the event, so nothing is left out and the dict keeps its
        # three keys; every session after the event needs a record as before.
        full = self.run_event(research_sessions=self.days)
        self.assertEqual(full["rg1_coverage"], self.coverage([]))
        self.assertEqual(full["rg"]["RG1"], "ok")
        missing = self.days[self.event + 2]  # an up day: no EV3 (b) record gap
        self.assertGreater(self.data["ret1"][self.event + 2], 0)
        gap = self.run_event(research_sessions=[day for day in self.days if day != missing])
        self.assertEqual(gap["rg1_coverage"], self.coverage([missing]))
        self.assertEqual(gap["rg"]["RG1"], "unk")


class Case20261012Tests(unittest.TestCase):
    """B6: the 2026-10-12 evaluation (synthetic): EV3a two sessions back, no record on the session after it (the
    research record starts on the evaluation session), the benchmark closes below C0 and below EMA50."""

    def test_b6_rg1_ok_and_the_market_gates_decide(self):
        closes = helpers.zigzag(81, 500, 6.0)
        closes[-1] = 490.0  # below C0 (494) and EMA50 (about 500); not a -2 sigma60 day, not a 3 sigma60 drawdown
        data, days = bench(closes)
        self.assertLess(data["close"][-1], data["ema50"][-1])
        self.assertGreater(data["ret1"][-1], -2 * data["sigma60"][-1])
        result = run_rrec1(data, ev3_user_dates=[days[-3]], research_sessions=[days[-1]])
        self.assertEqual([item["date"] for item in result["events"]], [days[-3]])
        self.assertEqual((result["event"]["date"], result["event"]["kinds"]), (days[-3], ["EV3a"]))
        self.assertLess(data["close"][-1], result["event"]["c0"])
        self.assertEqual(result["ev3b_coverage_start"], days[-1])
        self.assertEqual(result["rg1_coverage"], {"from": days[-2], "to": days[-1], "missing_sessions": [],
                                                  "before_first_record": [days[-2]]})
        self.assertEqual((result["rg"]["RG1"], result["rg"]["RG2"], result["rg"]["RG3"]), ("ok", "no", "no"))
        self.assertNotEqual(result["rg"]["RG4"], "unk")
        self.assertEqual((result["status"], result["open"], result["ds1"]), ("no", True, days[-1]))
        self.assertEqual(result["reasons"], [])


if __name__ == "__main__":
    unittest.main()
