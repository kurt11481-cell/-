"""decide-gap2: a Ctrl+C (KeyboardInterrupt) during the research-record wait only ends the wait, and one anywhere
else in the run still leaves a FAIL record (decision.json and LATEST_DECISION.json).

All inputs are synthetic (TEST_ONLY): the Env of test_auto_core_decide with an injected sleeper and bars_loader.
No real sleep, no network, no Kiwoom.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "manage-us-stock-strategy/tests"
sys.path.insert(0, str(TESTS))

import test_auto_core_decide as decide_tests  # noqa: E402
import test_auto_core_tickets as tickets_tests  # noqa: E402

decide_module = decide_tests.decide_module
helpers = decide_tests.helpers
load_json = decide_tests.load_json
validate_instance = decide_tests.validate_instance
journal_module = decide_tests.journal_module
DAYS = decide_tests.DAYS

# The judgment of a run (what a Ctrl+C during the wait must not change); the wait itself and the exception list
# may differ.
JUDGMENT_KEYS = ("status", "reasons", "tickets", "no_action", "blocked", "candidates", "buy_requirements", "symbols",
                 "evidence", "exposure", "shock", "account", "outcomes", "open_tickets", "keys", "f6_ran")


def sell_env(**kwargs):
    """SOXL held 120 with $300 cash, falling SOXL closes and a -2 sigma SOXX day: the decide path issues a SOXL
    sell ticket (the ResearchRecordGateTests sell case of test_auto_core_tickets, run through decide)."""
    env = decide_tests.Env(holdings={"SOXL": 120}, cash="300", soxl_closes=tickets_tests.falling_soxl(), **kwargs)
    env.bars["SOXX"] = helpers.bars("SOXX", DAYS, helpers.zigzag(len(DAYS) - 1, 500, 2.0, 0.3) + [470.0])
    return env


def interrupting_sleeper(after=0):
    """A sleeper whose call number after+1 raises KeyboardInterrupt (as Ctrl+C in the console would)."""
    calls = []

    def sleeper(seconds):
        calls.append(seconds)
        if len(calls) > after:
            raise KeyboardInterrupt

    return sleeper, calls


def never_sleeper(seconds):
    raise AssertionError("the wait must not sleep when the research record exists")


class WaitInterruptTests(unittest.TestCase):
    def run_pair(self, *, mode="compare"):
        """(interrupted at the first sleep, the full 07:45 -> 08:30 wait), both without a research record."""
        interrupted_env, full_env = sell_env(research=False, decision_mode=mode), sell_env(research=False, decision_mode=mode)
        try:
            sleeper, calls = interrupting_sleeper()
            interrupted = interrupted_env.run(sleeper=sleeper)
            full = full_env.run()
        finally:
            interrupted_env.close()
            full_env.close()
        return interrupted, full, calls

    def test_ctrl_c_in_the_wait_keeps_the_sell_and_no_action_judgment(self):
        interrupted, full, calls = self.run_pair()
        self.assertEqual(calls, [decide_module.RESEARCH_POLL_SECONDS])
        self.assertNotEqual(interrupted["status"], "FAIL", interrupted["reasons"])
        self.assertEqual(validate_instance(interrupted, decide_module.DECISION_SCHEMA), [])
        wait = interrupted["inputs"]["research_record"]["wait"]
        self.assertFalse(wait["found"])
        self.assertEqual(wait["waited_seconds"], 0)
        self.assertIs(wait["interrupted"], True)
        self.assertEqual(interrupted["inputs"]["research_record"]["status"], "MISSING")
        # The full wait ran its 5-minute steps to 08:30 and was not interrupted.
        self.assertEqual(full["inputs"]["research_record"]["wait"]["waited_seconds"], 45 * 60)
        self.assertIs(full["inputs"]["research_record"]["wait"]["interrupted"], False)
        # Sells and no-action come out as in the full wait: the interrupt changed nothing but the wait.
        sells = [ticket for ticket in interrupted["tickets"] if ticket["side"] == "sell"]
        self.assertTrue(sells, interrupted["blocked"])
        for key in JUDGMENT_KEYS:
            self.assertEqual(interrupted[key], full[key], key)
        # Buys stay blocked by the missing record (fail closed).
        self.assertEqual([ticket for ticket in interrupted["tickets"] if ticket["side"] == "buy"], [])
        mu = next(row for row in interrupted["buy_requirements"] if row["code"] == "MU")
        self.assertEqual(mu["c"][0]["s"], "no")
        self.assertFalse(interrupted["order_authority"])
        self.assertIsNone(interrupted["execution_quantity"])

    def test_ctrl_c_in_the_wait_in_recording_mode_journals_like_the_full_wait(self):
        interrupted, full, _calls = self.run_pair(mode="apply")
        self.assertNotEqual(interrupted["status"], "FAIL", interrupted["reasons"])
        self.assertEqual(interrupted["journal"]["appended"], full["journal"]["appended"])
        # The wait is outside the decision identity (r2 R2-5), so the interrupt mark does not change the review id.
        swapped = copy.deepcopy(interrupted)
        swapped["inputs"]["research_record"]["wait"] = full["inputs"]["research_record"]["wait"]
        self.assertEqual(decide_module.decision_identity_hash(swapped), decide_module.decision_identity_hash(interrupted))

    def test_ctrl_c_on_a_later_sleep_keeps_the_time_already_waited(self):
        env = sell_env(research=False)
        try:
            sleeper, calls = interrupting_sleeper(after=2)
            decision = env.run(sleeper=sleeper)
        finally:
            env.close()
        wait = decision["inputs"]["research_record"]["wait"]
        self.assertEqual(len(calls), 3)
        self.assertEqual(wait["waited_seconds"], 2 * decide_module.RESEARCH_POLL_SECONDS)
        self.assertIs(wait["interrupted"], True)
        self.assertNotEqual(decision["status"], "FAIL", decision["reasons"])

    def test_a_present_record_does_not_wait(self):
        first, second = sell_env(), sell_env()
        try:
            without_sleep = first.run(sleeper=never_sleeper)
            usual = second.run()
        finally:
            first.close()
            second.close()
        wait = without_sleep["inputs"]["research_record"]["wait"]
        self.assertTrue(wait["found"])
        self.assertEqual(wait["waited_seconds"], 0)
        self.assertIs(wait["interrupted"], False)
        self.assertEqual(without_sleep["inputs"]["research_record"]["status"], "OK")
        for key in JUDGMENT_KEYS:
            self.assertEqual(without_sleep[key], usual[key], key)


class RunInterruptTests(unittest.TestCase):
    def setUp(self):
        self.env = sell_env(decision_mode="apply")

    def tearDown(self):
        self.env.close()

    def interrupted_run(self):
        def bars_loader(symbol, evaluation_session):
            raise KeyboardInterrupt

        return self.env.run(bars_loader=bars_loader)

    def test_ctrl_c_outside_the_wait_leaves_a_fail_record(self):
        journal_before = self.env.journal.read_bytes()
        decision = self.interrupted_run()  # no KeyboardInterrupt leaves decide()
        self.assertEqual(decision["status"], "FAIL")
        self.assertIn("INTERRUPTED:KeyboardInterrupt", decision["reasons"])
        written = load_json(self.env.day_dir / decide_module.DECISION_FILE)
        self.assertEqual(written["status"], "FAIL")
        self.assertIn("INTERRUPTED:KeyboardInterrupt", written["reasons"])
        self.assertEqual(load_json(self.env.output / decide_module.LATEST_DECISION_FILE), written)
        self.assertEqual(validate_instance(written, decide_module.DECISION_SCHEMA), [])
        # A FAIL record offers no ticket, commits no ledger and writes no journal entry.
        self.assertEqual(written["tickets"], [])
        self.assertFalse(written["f6_ran"])
        self.assertEqual(written["journal"]["appended"], [])
        self.assertTrue(any(alert["code"] == "DECIDE_FAIL" and alert["push"] for alert in written["alerts"]))
        self.assertEqual(self.env.journal.read_bytes(), journal_before)
        self.assertFalse(written["order_authority"])
        self.assertIsNone(written["execution_quantity"])

    def test_a_same_day_rerun_after_the_fail_record_runs_normally(self):
        self.interrupted_run()
        rerun = self.env.run()
        self.assertNotEqual(rerun["status"], "FAIL", rerun["reasons"])
        self.assertTrue(rerun["tickets"])
        self.assertIn("core_decision", rerun["journal"]["appended"])
        self.assertEqual(load_json(self.env.day_dir / decide_module.DECISION_FILE)["status"], rerun["status"])
        self.assertEqual(list(self.env.day_dir.glob(decide_module.RERUN_PREFIX + "*")), [])
        entries = journal_module.load_journal(self.env.journal)["entries"]
        self.assertEqual(sum(entry["entry_type"] == "core_decision" for entry in entries), 1)


if __name__ == "__main__":
    unittest.main()
