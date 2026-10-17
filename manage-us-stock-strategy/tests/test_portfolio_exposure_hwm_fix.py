"""hwm-fix (2026-10-17): sessions inside a lifted hold window are revalued, not skipped forever.

Rule 1: a session whose every covering hold window has ended is valued at the holdings of the first confirmed
reconciliation read after its close x its raw close + that read's broker order-available cash (POST_CLOSE, or
BRACKETED by an unchanged reconciliation read before its open). Anything that cannot be revalued fails closed.
Rule 3: a completed line review recorded against the event list of the old rule is shown as superseded.
Synthetic inputs except H11, which reproduces the shape of the 2026-10-01..10-16 record (docs/claude/hwm-fix-builder-prompt.md).
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_exposure as pe  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from test_portfolio_exposure import Scenario, trigger  # noqa: E402
from test_portfolio_exposure_fail_closed import (  # noqa: E402
    DEPOSIT, WITHDRAWAL, capture, declaration, et, line_scenario, released_review, session_bounds,
)

D = ["2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30"]  # line_scenario days (EVAL = D[4])


def clear(start: str, end: str = "2026-09-30") -> dict[str, Any]:
    return declaration([], None, period=(start, end))


def lines_of(review: dict[str, Any]) -> dict[str, Any]:
    return review["review_lines"]


def events(review: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(item["line_id"], item["breach_date"], item["review_status"]) for item in lines_of(review)["events"]]


def old_rule(scenario: Scenario, evaluation: str | None = None) -> dict[str, Any]:
    """The same input under the rule before hwm-fix (released holds skipped), via the internal switch."""
    config = pe.exposure_config(scenario.policy)
    session = evaluation or scenario.evaluation
    view = pe.journal_view(scenario.journal)
    snapshots = [item for item in scenario.snapshots if item["as_of"] <= session]
    return pe.evaluate_review_lines(
        config=config, activation=view["activation"], line_reviews=view["line_reviews"],
        sessions=[day for day in scenario.sessions if day <= session], evaluation_session=session,
        snapshots=snapshots, closes=scenario.closes, revalue_held_sessions=False)


def sale_case(prices: list[str], *, sold: int, proceeds: str, n_read: str, later_read: str) -> tuple[Scenario, dict]:
    """SOXL 50 + cash 5,000; `sold` shares sold on D[2] (sale hold D[2] -> D[3]); captures for revisions 2 and 3."""
    scenario = line_scenario(prices)
    left = 50 - sold
    cash = str(Decimal("5000") + Decimal(proceeds))
    scenario.snapshots = [
        fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
        fx.snapshot(D[2], {"SOXL": left}, "5000", revision=2, decreased=True, block=clear(D[0])),
        fx.snapshot(D[3], {"SOXL": left}, cash, revision=3, block=clear(D[2])),
    ]
    captures = {2: capture(n_read, cash, sell=proceeds), 3: capture(later_read, cash)}
    return scenario, captures


class RevaluationTests(unittest.TestCase):
    def test_h1_released_sale_hold_is_revalued_after_the_close_and_sets_the_hwm(self) -> None:
        scenario, captures = sale_case(["100", "100", "120", "100", "100"], sold=20, proceeds="2400",
                                       n_read=et(D[2], "19:00"), later_read=et(D[3], "19:00"))
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual((lines["status"], lines["hwm_usd"], lines["hwm_date"]), ("EVALUATED", "11000", D[2]))
        self.assertEqual(lines["skipped_sessions"], [D[2]])  # meaning kept: sessions inside a hold window
        self.assertEqual(lines["revalued_sessions"], [{
            "session": D[2], "method": "POST_CLOSE", "state_revision": 2, "earliest_read_at": et(D[2], "19:00"),
            "latest_read_at": et(D[2], "19:00"), "order_available_cash_usd": "7400", "flow_correction_usd": "0",
            "closing_equity_usd": "11000"}])
        self.assertEqual(old_rule(scenario)["hwm_usd"], "10400")  # the old rule never saw the 11,000 close
        self.assertFalse(review["fail_closed"]["active"])

    def test_h2_released_cash_flow_hold_brings_the_l1_date_forward(self) -> None:
        scenario = line_scenario(["100", "100", "80", "79", "79"])
        scenario.snapshots = [
            fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
            fx.snapshot(D[1], {"SOXL": 50}, "5000", revision=2),  # no cash-flow evidence: HOLD
            fx.snapshot(D[3], {"SOXL": 50}, "5000", revision=3, block=clear(D[0])),  # covers it: CLEAR
        ]
        captures = {2: capture(et(D[1], "19:00"), "5000"), 3: capture(et(D[3], "07:00"), "5000")}
        review = released_review(scenario, captures)
        self.assertEqual(lines_of(review)["skipped_sessions"], [D[1], D[2]])
        self.assertEqual([item["method"] for item in lines_of(review)["revalued_sessions"]], ["POST_CLOSE", "POST_CLOSE"])
        self.assertEqual(events(review), [("L1", D[2], "open")])  # 9,000 on D[2]
        self.assertEqual([(item["line_id"], item["breach_date"]) for item in old_rule(scenario)["events"]],
                         [("L1", D[3])])  # the old rule saw it one session later
        self.assertEqual(lines_of(review)["status"], "EVALUATED")

    def test_h3_hold_that_is_not_lifted_stays_held(self) -> None:
        scenario = line_scenario(["100", "100", "80", "79", "79"])
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
                              fx.snapshot(D[1], {"SOXL": 50}, "5000", revision=2)]
        captures = {2: capture(et(D[1], "19:00"), "5000")}
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual((lines["status"], lines["reasons"], lines["revalued_sessions"]),
                         ("HELD", ["LINE_EVALUATION_ON_HOLD"], []))
        self.assertEqual(lines["skipped_sessions"], D[1:])
        self.assertTrue(trigger(review, "undeclared_cash_flow")["active"])
        self.assertTrue(review["pauses"]["new_buy_recommendations"]["paused"])
        # Sale waiting for cash confirmation: no later reconciliation, nothing revalued.
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
                              fx.snapshot(D[2], {"SOXL": 30}, "5000", revision=2, decreased=True, block=clear(D[0]))]
        review = released_review(scenario, {2: capture(et(D[2], "19:00"), "7000", sell="2000")})
        self.assertEqual((lines_of(review)["status"], lines_of(review)["revalued_sessions"]), ("HELD", []))
        self.assertIn("SALE_PROCEEDS_PENDING_CASH_CONFIRMATION",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
        # Overlap: a lifted sale window and a cash-flow window that is still open cover the same sessions.
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
                              fx.snapshot(D[1], {"SOXL": 30}, "7000", revision=2, decreased=True),
                              fx.snapshot(D[2], {"SOXL": 30}, "7000", revision=3)]
        review = released_review(scenario, {2: capture(et(D[1], "19:00"), "7000"),
                                            3: capture(et(D[2], "19:00"), "7000")})
        self.assertEqual((lines_of(review)["status"], lines_of(review)["revalued_sessions"]), ("HELD", []))
        self.assertEqual(lines_of(review)["skipped_sessions"], D[1:])

    def above_band_case(self, later_deposit: str) -> tuple[Scenario, dict]:
        scenario = Scenario({"SOXL": 62}, "3800")  # N = 1.86: a reduce recommendation exists
        scenario.days = D
        for day in D:
            scenario.closes["SOXL"][day] = "100"
        scenario.journal = fx.journal(fx.activation_entry(D[0], "10000"))
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 62}, "3800", revision=1),
                              fx.snapshot(D[1], {"SOXL": 62}, "3800", revision=2),
                              fx.snapshot(D[3], {"SOXL": 62}, "3800", revision=3, block=clear(D[0]))]
        # Revision 2 read before D[1] opened; revision 3 read after D[3] opened (after the next open of D[1] and D[2]).
        captures = {2: capture(et(D[1], "08:00"), "3800"),
                    3: capture(et(D[3], "11:00"), later_deposit, deposit=later_deposit)}
        return scenario, captures

    def test_h4_bracket_mismatch_fails_closed_and_reduce_continues(self) -> None:
        scenario, captures = self.above_band_case("3801.47")  # a cash change between the two reads
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.05"}]
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual(lines["status"], "UNVERIFIED")
        self.assertEqual(lines["reasons"], [f"HELD_SESSION_NOT_REVALUABLE:{D[1]}:BRACKET_MISMATCH:2:3"])
        self.assertIn(f"HELD_SESSION_NOT_REVALUABLE:{D[1]}:BRACKET_MISMATCH:2:3",
                      trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"])
        self.assertTrue(review["pauses"]["add_recommendations"]["paused"])
        self.assertTrue(review["pauses"]["new_buy_recommendations"]["paused"])
        self.assertEqual(review["recommendations"]["proposals"][0]["status"], "OMITTED")
        self.assertFalse(lines["automatic_sell"])
        self.assertTrue(review["recommendations"]["reduce"])
        self.assertTrue(all(item["label"] == "UNVERIFIED" for item in review["recommendations"]["reduce"]))
        self.assertGreaterEqual(Decimal(lines["hwm_usd"]), Decimal(old_rule(scenario)["hwm_usd"]))

    def test_h5_bracketed_when_holdings_and_cash_total_did_not_change(self) -> None:
        scenario, captures = self.above_band_case("3800")
        review = released_review(scenario, captures)
        self.assertEqual([(item["session"], item["method"], item["state_revision"])
                          for item in lines_of(review)["revalued_sessions"]],
                         [(D[1], "BRACKETED", 3), (D[2], "BRACKETED", 3)])
        self.assertEqual(lines_of(review)["status"], "EVALUATED")

    def test_h5b_pre_open_order_available_drift_is_not_a_false_mismatch(self) -> None:
        scenario, captures = self.above_band_case("3800")
        captures[2] = capture(et(D[1], "08:00"), "3803.03", deposit="3800")  # +$3 before the open, deposit unchanged
        review = released_review(scenario, captures)
        self.assertEqual([item["method"] for item in lines_of(review)["revalued_sessions"]], ["BRACKETED", "BRACKETED"])
        self.assertEqual(lines_of(review)["status"], "EVALUATED")

    def test_h6_missing_capture_fails_closed_and_never_falls_back_to_skipping(self) -> None:
        scenario = line_scenario(["100", "100", "80", "79", "79"])
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
                              fx.snapshot(D[1], {"SOXL": 50}, "5000", revision=2),
                              fx.snapshot(D[3], {"SOXL": 50}, "5000", revision=3, block=clear(D[0]))]
        full = {2: capture(et(D[1], "19:00"), "5000"), 3: capture(et(D[3], "07:00"), "5000")}
        for captures, reason in (({2: full[2]}, f"{D[2]}:BROKER_CAPTURE_MISSING:3"),
                                 ({3: full[3]}, f"{D[1]}:BROKER_CAPTURE_MISSING:2"),
                                 (None, f"{D[1]}:BROKER_CAPTURE_MISSING:2"),
                                 ({2: dict(full[2], order_available_cash_usd="-1"), 3: full[3]},
                                  f"{D[1]}:BROKER_CAPTURE_MISSING:2")):
            review = released_review(scenario, captures)
            lines = lines_of(review)
            self.assertEqual((lines["status"], lines["reasons"]), ("UNVERIFIED", [f"HELD_SESSION_NOT_REVALUABLE:{reason}"]))
            self.assertTrue(review["fail_closed"]["active"])
        # Without session times nothing can be revalued either.
        review = released_review(scenario, full, bounds={})
        self.assertEqual(lines_of(review)["reasons"], [f"HELD_SESSION_NOT_REVALUABLE:{D[1]}:SESSION_BOUNDS_MISSING"])
        # The old fixture shape (no captures, no session times) fails closed instead of skipping.
        self.assertEqual(lines_of(scenario.review())["status"], "UNVERIFIED")

    def test_h7_a_reconciliation_after_the_evaluation_session_neither_lifts_nor_values(self) -> None:
        scenario = line_scenario(["100", "100", "80", "79", "79"])
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
                              fx.snapshot(D[1], {"SOXL": 50}, "5000", revision=2),
                              fx.snapshot(D[3], {"SOXL": 50}, "5000", revision=3, block=clear(D[0]))]
        captures = {2: capture(et(D[1], "08:00"), "5000"), 3: capture(et(D[3], "07:00"), "5000")}
        scenario.evaluation = D[2]  # revision 3 (as_of D[3]) is dated after this session
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual((lines["status"], lines["revalued_sessions"], lines["events"]), ("HELD", [], []))
        self.assertEqual(review["snapshot"]["later_reconciliations_not_used"], 1)
        scenario.evaluation = D[3]
        self.assertEqual([item["state_revision"] for item in lines_of(released_review(scenario, captures))["revalued_sessions"]],
                         [3, 3])


class FlowCountedOnceTests(unittest.TestCase):
    """B-6: the declared flow adjusts the HWM exactly once; revalued equity is on the pre-adjustment basis."""

    def assert_not_looser(self, scenario: Scenario, review: dict[str, Any]) -> None:
        old = old_rule(scenario)
        self.assertGreaterEqual(Decimal(lines_of(review)["hwm_usd"]), Decimal(old["hwm_usd"]))
        new = {(item["line_id"]): item["breach_date"] for item in lines_of(review)["events"]}
        for item in old["events"]:
            if lines_of(review)["status"] != "UNVERIFIED":
                self.assertLessEqual(new[item["line_id"]], item["breach_date"])

    def test_h8a_sale_and_deposit_declared_by_the_same_later_reconciliation(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        row = dict(DEPOSIT, deal_dt="20260928")  # deposited on D[2] (Korean date), declared by revision 3
        scenario.snapshots = [
            fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
            fx.snapshot(D[1], {"SOXL": 40}, "5000", revision=2, decreased=True, block=clear(D[0], D[1])),
            fx.snapshot(D[3], {"SOXL": 40}, "7000", revision=3,
                        block=declaration([row], "1000.00", period=(D[1], "2026-09-30"))),
        ]
        captures = {2: capture(et(D[1], "19:00"), "6000", sell="1000"), 3: capture(et(D[3], "07:00"), "7000")}
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual([(item["session"], item["state_revision"], item["flow_correction_usd"])
                          for item in lines["revalued_sessions"]], [(D[1], 2, "0"), (D[2], 3, "1000.00")])
        self.assertEqual((lines["status"], lines["hwm_usd"], lines["hwm_date"], lines["events"]),
                         ("EVALUATED", "11000.00", D[0], []))  # 10,000 + 1,000 once, never a new high
        self.assert_not_looser(scenario, review)

    def test_h8b_late_declared_withdrawal_is_not_a_false_line(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        row = dict(WITHDRAWAL, deal_dt="20260924")
        undeclared = declaration([row], None, period=(D[0], D[1]))
        late = declaration([row], "-1000.00", period=(D[0], "2026-09-30"), prior=[undeclared])
        scenario.snapshots = [
            fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
            fx.snapshot(D[1], {"SOXL": 50}, "4000", revision=2, block=undeclared),
            fx.snapshot(D[3], {"SOXL": 50}, "4000", revision=3, block=late),
        ]
        captures = {2: capture(et(D[1], "08:00"), "4000"), 3: capture(et(D[3], "11:00"), "4000")}
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual([(item["method"], item["flow_correction_usd"]) for item in lines["revalued_sessions"]],
                         [("BRACKETED", "-1000.00"), ("BRACKETED", "-1000.00")])
        self.assertEqual((lines["status"], lines["hwm_usd"], lines["events"]), ("EVALUATED", "9000.00", []))
        self.assert_not_looser(scenario, review)

    def test_h8c_a_flow_dated_on_the_capture_day_of_another_block_fails_closed(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        row = dict(DEPOSIT, deal_dt="20260926")  # the Korean date of revision 2's read (D[1] 19:00 New York)
        scenario.snapshots = [
            fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
            fx.snapshot(D[1], {"SOXL": 40}, "5000", revision=2, decreased=True, block=clear(D[0], D[1])),
            fx.snapshot(D[3], {"SOXL": 40}, "7000", revision=3,
                        block=declaration([row], "1000.00", period=(D[1], "2026-09-30"))),
        ]
        captures = {2: capture(et(D[1], "19:00"), "6000", sell="1000"), 3: capture(et(D[3], "07:00"), "7000")}
        review = released_review(scenario, captures)
        self.assertEqual(lines_of(review)["reasons"],
                         [f"HELD_SESSION_NOT_REVALUABLE:{D[1]}:CASH_FLOW_DATE_AMBIGUOUS:2026-09-26:000000001"])
        self.assertTrue(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["active"])
        self.assert_not_looser(scenario, review)

    def test_h8d_revaluation_failure_keeps_the_hwm_at_least_at_the_old_rule(self) -> None:
        # The old rule reaches a higher close after the failing session; the output HWM is never below it.
        scenario = line_scenario(["100", "100", "100", "130", "130"])
        scenario.snapshots = [
            fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
            fx.snapshot(D[1], {"SOXL": 50}, "5000", revision=2),
            fx.snapshot(D[2], {"SOXL": 50}, "5000", revision=3, block=clear(D[0])),
        ]
        review = released_review(scenario, {3: capture(et(D[2], "19:00"), "5000")})  # revision 2 unlinked
        lines = lines_of(review)
        self.assertEqual(lines["status"], "UNVERIFIED")
        self.assertEqual((lines["hwm_usd"], lines["hwm_date"]), (old_rule(scenario)["hwm_usd"], D[3]))
        self.assertEqual(lines["hwm_usd"], "11500")


class SplitTests(unittest.TestCase):
    def test_h12_split_between_the_session_and_the_capture_fails_revaluation(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        scenario.snapshots = [fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
                              fx.snapshot(D[1], {"SOXL": 50}, "5000", revision=2),
                              fx.snapshot(D[3], {"SOXL": 100}, "5000", revision=3, block=clear(D[0]))]
        for day in D[2:]:
            scenario.closes["SOXL"][day] = "50"
        action = {"symbol": "SOXL", "action_type": "FORWARD_SPLIT", "effective_session": D[2], "new_shares": 2,
                  "old_shares": 1}
        record = {"status": "OK", "actions": [action], "errors": [], "sha256": None}
        captures = {2: capture(et(D[1], "08:00"), "5000"), 3: capture(et(D[3], "07:00"), "5000")}
        review = released_review(scenario, captures, corporate_actions=record)
        self.assertEqual(lines_of(review)["reasons"],
                         [f"HELD_SESSION_NOT_REVALUABLE:{D[1]}:SPLIT_AFTER_SESSION:SOXL:{D[2]}"])
        self.assertEqual(lines_of(review)["status"], "UNVERIFIED")


class SupersededJournalTests(unittest.TestCase):
    def case(self) -> tuple[Scenario, dict]:
        # Sold 10 at 130 on D[1] (HWM 11,500 on the revalued close); the old rule's HWM is 10,100 on D[2].
        scenario = line_scenario(["100", "130", "95", "70", "65"])
        scenario.snapshots = [
            fx.snapshot(D[0], {"SOXL": 50}, "5000", revision=1),
            fx.snapshot(D[1], {"SOXL": 40}, "5000", revision=2, decreased=True, block=clear(D[0])),
            fx.snapshot(D[2], {"SOXL": 40}, "6300", revision=3, block=clear(D[1])),
        ]
        captures = {2: capture(et(D[1], "19:00"), "6300", sell="1300"), 3: capture(et(D[2], "07:00"), "6300")}
        return scenario, captures

    def test_h9_review_of_the_old_event_is_superseded_and_the_new_l2_stays_open(self) -> None:
        scenario, captures = self.case()
        old = old_rule(scenario)
        self.assertEqual([(item["line_id"], item["breach_date"], item["hwm"]) for item in old["events"]],
                         [("L1", D[4], "10100")])
        entry = fx.line_review_entry("L1", "10100", D[4])
        scenario.journal = fx.journal(fx.activation_entry(D[0], "10000"), entry)
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual(events(review), [("L1", D[2], "open"), ("L2", D[3], "open")])
        self.assertEqual(lines["superseded_journal_reviews"], [{
            "entry_id": entry["entry_id"], "line_id": "L1", "breach_date": D[4], "hwm": "10100",
            "reason": "HWM_RECOMPUTED_HELD_SESSIONS"}])
        self.assertEqual(lines["unmatched_journal_reviews"], [])
        self.assertFalse(any(reason.startswith("JOURNAL_REVIEW_UNMATCHED") for reason in
                             trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"]))
        self.assertIn("REVIEW_LINE_OPEN:L2", review["pauses"]["new_buy_recommendations"]["reasons"])
        # An entry that matches neither list stays unmatched and fails closed.
        scenario.journal = fx.journal(fx.activation_entry(D[0], "10000"), fx.line_review_entry("L1", "9999", D[4]))
        review = released_review(scenario, captures)
        self.assertEqual(lines_of(review)["superseded_journal_reviews"], [])
        self.assertIn("JOURNAL_REVIEW_UNMATCHED:" + "b" * 64,
                      trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"])
        # An entry for the recomputed event completes it as before.
        scenario.journal = fx.journal(fx.activation_entry(D[0], "10000"), fx.line_review_entry("L1", "11500", D[2]))
        review = released_review(scenario, captures)
        self.assertEqual(events(review), [("L1", D[2], "completed"), ("L2", D[3], "open")])
        self.assertEqual(lines_of(review)["superseded_journal_reviews"], [])


class NoHoldTests(unittest.TestCase):
    def test_h10_inputs_without_holds_give_the_same_review_lines(self) -> None:
        # The auto-core replay shape: one revision, holdings never decrease, no declaration block.
        scenario = Scenario({"SOXL": 50}, "5000")
        scenario.snapshots = [fx.snapshot(day, {"SOXL": 50}, "5000", revision=1) for day in D]
        scenario.journal = fx.journal(fx.activation_entry(D[0], "10000"))
        plain = scenario.review()["review_lines"]
        self.assertEqual((plain["revalued_sessions"], plain["superseded_journal_reviews"]), ([], []))
        with_inputs = released_review(scenario, {1: capture(et(D[0], "19:00"), "5000")})["review_lines"]
        self.assertEqual(with_inputs, plain)
        self.assertEqual(plain, old_rule(scenario))


# ------------------------------------------------------------------------------------------------
# H11: the 2026-10-01..10-16 record (closes from the saved close histories; holdings, cash and read times
# from the ledger revisions 16-28 and their broker snapshots; cpi-shock-review-2026-10-15.md D6)
# ------------------------------------------------------------------------------------------------

REAL_DAYS = ["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09",
             "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"]
REAL_CLOSES = {
    "MVLL": ["36.7900", "37.9300", "37.6500", "42.0300", "41.3800", "38.3600", "38.4955", "35.8060", "36.6500",
             "30.2000", "29.2100", "25.8500"],
    "SOXL": ["153.7500", "163.6600", "164.2200", "164.2100", "158.8700", "142.4700", "139.7050", "128.3599",
             "127.6201", "110.5393", "107.3400", "93.6838"],
    "NBIS": ["232.4600", "242.7900", "232.5800", "249.8900", "237.1500", "219.8100", "221.1100", "209.9800",
             "206.8950", "186.0500", "188.4600", "165.4500"],
    "SOXX": ["576.3200", "588.9000", "589.5000", "589.4500", "582.8700", "563.1850", "559.7900", "544.8500",
             "543.8400", "519.3800", "514.7300", "493.1400"],
}
H0 = {"MVLL": 396, "SOXL": 75, "NBIS": 13}
H1 = {"MVLL": 278, "SOXL": 75, "NBIS": 13}
H2 = {"MVLL": 159, "SOXL": 75, "NBIS": 13}
H3 = {"MVLL": 159, "SOXL": 53, "NBIS": 13}
# (revision, as_of, holdings, state cash, decreased, block period or None,
#  earliest read, latest read, order-available, deposit, d1 sell, d2 sell)
REAL_REVISIONS = [
    (16, "2026-09-29", H0, "5.92", False, None, None, None, None, None, "0", "0"),
    (17, "2026-10-02", H0, "5.92", False, None,
     "2026-10-02T04:07:10.105151Z", "2026-10-02T04:07:10.911650+00:00", "5.92", "5.92", "0", "0"),
    (18, "2026-10-05", H0, "5.92", False, ("2026-10-02", "2026-10-05"),
     "2026-10-05T23:59:34.972997Z", "2026-10-05T23:59:36.025391+00:00", "5.92", "5.92", "0", "0"),
    (19, "2026-10-06", H1, "5.92", True, ("2026-10-06", "2026-10-06"),
     "2026-10-06T13:18:51.610254Z", "2026-10-06T13:18:52.658832+00:00", "4466.15", "5.92", "0", "4457.19"),
    (20, "2026-10-07", H1, "5.92", False, ("2026-10-07", "2026-10-07"),
     "2026-10-07T04:36:49.890179Z", "2026-10-07T04:36:50.906832+00:00", "4463.1", "5.92", "4457.19", "0"),
    (21, "2026-10-07", H2, "4463.11", True, None,
     "2026-10-07T23:21:55.249631Z", "2026-10-07T23:21:56.272076+00:00", "9395.2", "4463.11", "4932.1", "0"),
    (22, "2026-10-08", H2, "4463.11", False, None,
     "2026-10-08T12:16:12.527220Z", "2026-10-08T12:16:13.556587+00:00", "9398.25", "4463.11", "4932.1", "0"),
    (23, "2026-10-09", H2, "9395.21", False, None,
     "2026-10-09T07:01:40.195812Z", "2026-10-09T07:01:41.207385+00:00", "9395.21", "9395.21", "0", "0"),
    (24, "2026-10-09", H3, "9395.21", True, ("2026-10-09", "2026-10-10"),
     "2026-10-09T23:52:04.178310Z", "2026-10-09T23:52:05.191007+00:00", "12467.71", "9395.21", "0", "3072.51"),
    (25, "2026-10-12", H3, "12469.18", False, None,
     "2026-10-13T03:51:24.119459Z", "2026-10-13T03:51:25.222275+00:00", "12469.18", "9396.68", "3072.51", "0"),
    (26, "2026-10-13", H3, "12469.18", False, ("2026-10-08", "2026-10-13"),
     "2026-10-13T09:40:45.339303Z", "2026-10-13T09:40:46.377371+00:00", "12469.18", "9396.68", "3072.51", "0"),
    (27, "2026-10-15", H3, "12469.19", False, ("2026-10-13", "2026-10-16"),
     "2026-10-15T21:15:06.017620Z", "2026-10-15T21:15:07.060885+00:00", "12469.19", "12469.19", "0", "0"),
    (28, "2026-10-16", H3, "12469.19", False, ("2026-10-16", "2026-10-17"),
     "2026-10-16T21:15:03.694475Z", "2026-10-16T21:15:04.733459+00:00", "12469.19", "12469.19", "0", "0"),
]


def real_case() -> tuple[Scenario, dict[int, Any]]:
    scenario = Scenario(dict(H3), "12469.19", session_count=320)
    scenario.sessions = fx.weekday_sessions(320, "2026-10-16", extra_after=5)  # 2026-10-12 is a U.S. session
    # Synthetic history before 10-01, scaled so the first real close continues it; real closes from 10-01.
    past = [day for day in scenario.sessions if day < REAL_DAYS[0]]
    bench = fx.benchmark_returns(len(past) + 1)
    multiples = {"SOXX": 1.0, "SOXL": 2.9, "MVLL": 1.9, "NBIS": 0.5}
    scenario.closes = {}
    for symbol, values in REAL_CLOSES.items():
        series = fx.series(past + [REAL_DAYS[0]], bench, last=values[0], multiple=multiples[symbol])
        series.update(dict(zip(REAL_DAYS, values)))
        scenario.closes[symbol] = series
    scenario.evaluation = "2026-10-16"
    scenario.earnings = fx.verified_earnings(["BE", "MU", "NBIS", "DELL", "AMD"], "2026-10-21")
    scenario.journal = fx.journal(fx.activation_entry("2026-10-01", "29127.9900", revision=16))
    scenario.snapshots, captures = [], {}
    for (revision, as_of, holdings, cash, decreased, period, earliest, latest, order_available, deposit,
         d1_sell, d2_sell) in REAL_REVISIONS:
        block = declaration([], None, period=period) if period else None
        scenario.snapshots.append(fx.snapshot(as_of, holdings, cash, revision=revision, decreased=decreased,
                                              block=block))
        if earliest:
            captures[revision] = capture(earliest, order_available, deposit=deposit, latest=latest,
                                         sell=d1_sell, sell_d2=d2_sell)
    return scenario, captures


class RealRecordShapeTests(unittest.TestCase):
    def test_h11_the_october_record_gives_hwm_10_06_l1_10_12_and_l2_10_15(self) -> None:
        scenario, captures = real_case()
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "MU", "target_weight": "0.05"}]
        review = released_review(scenario, captures)
        lines = lines_of(review)
        self.assertEqual([(item["session"], item["method"], item["state_revision"], item["order_available_cash_usd"],
                           Decimal(item["closing_equity_usd"]).quantize(Decimal("0.01")))
                          for item in lines["revalued_sessions"]], [
            ("2026-10-02", "BRACKETED", 18, "5.92", Decimal("30456.97")),
            ("2026-10-06", "POST_CLOSE", 20, "4463.1", Decimal("31711.76")),
            ("2026-10-07", "POST_CLOSE", 21, "9395.2", Decimal("30972.82")),
            ("2026-10-08", "POST_CLOSE", 23, "9395.21", Decimal("29037.23")),
            ("2026-10-09", "POST_CLOSE", 24, "12467.71", Decimal("28867.29")),
            ("2026-10-12", "POST_CLOSE", 25, "12469.18", Decimal("27695.15")),
        ])
        self.assertEqual((lines["status"], Decimal(lines["hwm_usd"]), lines["hwm_date"]),
                         ("EVALUATED", Decimal("31711.76"), "2026-10-06"))
        self.assertEqual([(item["line_id"], item["breach_date"], item["threshold_usd"]) for item in lines["events"]],
                         [("L1", "2026-10-12", "28540.58400"), ("L2", "2026-10-15", "25369.40800")])
        self.assertEqual(review["pauses"]["new_buy_recommendations"]["reasons"], ["REVIEW_LINE_OPEN:L2"])
        self.assertEqual(review["pauses"]["add_recommendations"]["reasons"], ["REVIEW_LINE_OPEN:L2"])
        by_line = {item["line_id"]: item for item in lines["lines"]}
        self.assertTrue(by_line["L2"]["triggered_in_current_drawdown"])
        self.assertFalse(by_line["L3"]["triggered_in_current_drawdown"])
        self.assertFalse(review["fail_closed"]["active"])
        self.assertEqual((lines["superseded_journal_reviews"], lines["unmatched_journal_reviews"]), ([], []))
        self.assertIn("REVIEW_LINE_OPEN:L2", review["recommendations"]["proposals"][0]["reasons"])
        old = old_rule(scenario)
        self.assertEqual((old["hwm_usd"], [(item["line_id"], item["breach_date"]) for item in old["events"]]),
                         ("30255.3600", [("L1", "2026-10-14"), ("L2", "2026-10-16")]))


if __name__ == "__main__":
    unittest.main()
