"""s7-hold-gap: a reconciliation record that jumps past sessions in which held symbols were sold, and completed
peak reviews of closed positions. Synthetic inputs only."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_exposure as pe  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from test_portfolio_exposure import EVAL, Scenario, trigger  # noqa: E402
from test_portfolio_exposure_fail_closed import declaration, events  # noqa: E402


def jump_scenario(*, before: dict[str, int], after: dict[str, int], before_cash: str = "4000",
                  after_cash: str = "5000", decreased: bool = False, soxl_eval: str = "100") -> Scenario:
    """Record A (d0) holds `before`, record B (d8 = EVAL) holds `after`; no record for d1..d7 (the 10-29 shape).

    SOXL closes 100 and MVLL/TQQQ 50 on d0..d8; equity on d0 with SOXL 50, MVLL 20 and 4,000 cash is 10,000.
    """
    scenario = Scenario(after, after_cash)
    index = scenario.sessions.index(EVAL)
    days = scenario.sessions[index - 8:index + 1]
    scenario.days = days
    for day in days:
        scenario.closes["SOXL"][day] = "100"
        scenario.closes["MVLL"][day] = "50"
        scenario.closes["TQQQ"][day] = "50"
    scenario.closes["SOXL"][EVAL] = soxl_eval
    scenario.snapshots = [
        fx.snapshot(days[0], before, before_cash, revision=1, from_entry=True),
        fx.snapshot(days[8], after, after_cash, revision=2, decreased=decreased, from_entry=True,
                    block=declaration([], None, period=(days[0], "2026-09-30"))),
    ]
    scenario.journal = fx.journal(fx.activation_entry(days[0], "10000"))
    return scenario


def drop(scenario: Scenario, symbol: str, days: list[str]) -> None:
    for day in days:
        del scenario.closes[symbol][day]


def lines(review: dict[str, Any]) -> dict[str, Any]:
    return review["review_lines"]


class SoldSymbolGapTests(unittest.TestCase):
    def test_a_sold_symbol_without_closes_between_two_records_is_skipped_and_the_current_session_evaluated(self) -> None:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50})
        drop(scenario, "MVLL", scenario.days[1:])  # closes are collected for held symbols only
        review = scenario.review()
        result = lines(review)
        self.assertEqual((result["status"], result["reasons"]), ("EVALUATED", []))
        self.assertEqual(result["skipped_sessions"], scenario.days[1:8])
        self.assertEqual(result["evaluated_through"], EVAL)
        self.assertEqual((result["closing_equity_usd"], result["hwm_usd"]), ("10000", "10000"))
        self.assertFalse(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["active"])

    def test_the_10_29_shape_with_a_decreased_record_is_held_not_a_gap(self) -> None:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50}, decreased=True)
        drop(scenario, "MVLL", scenario.days[1:])
        review = scenario.review()
        result = lines(review)
        self.assertEqual((result["status"], result["reasons"]), ("HELD", ["LINE_EVALUATION_ON_HOLD"]))
        self.assertEqual(result["skipped_sessions"], scenario.days[1:])
        self.assertIn("SALE_PROCEEDS_PENDING_CASH_CONFIRMATION",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
        self.assertFalse(any(reason.startswith("EQUITY_GAP")
                             for reason in trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"]))

    def test_b_a_missing_close_of_a_symbol_still_held_stops_the_walk(self) -> None:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50})
        drop(scenario, "MVLL", scenario.days[1:])
        drop(scenario, "SOXL", [scenario.days[3]])
        result = lines(scenario.review())
        self.assertEqual((result["status"], result["reasons"]), ("UNVERIFIED", [f"EQUITY_GAP:{scenario.days[3]}:MVLL,SOXL"]))
        self.assertEqual(result["skipped_sessions"], scenario.days[1:3])
        self.assertEqual(result["evaluated_through"], scenario.days[0])

    def test_c_the_same_holdings_in_both_records_stop_the_walk(self) -> None:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50, "MVLL": 20}, after_cash="4000")
        drop(scenario, "MVLL", [scenario.days[1]])
        result = lines(scenario.review())
        self.assertEqual((result["status"], result["reasons"]), ("UNVERIFIED", [f"EQUITY_GAP:{scenario.days[1]}:MVLL"]))
        self.assertEqual(result["skipped_sessions"], [])
        # Only the quantity changed: the symbol is still held in B, so it is not a sold symbol either.
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50, "MVLL": 10}, after_cash="4500")
        drop(scenario, "MVLL", [scenario.days[1]])
        self.assertEqual(lines(scenario.review())["reasons"], [f"EQUITY_GAP:{scenario.days[1]}:MVLL"])

    def test_d_a_missing_item_that_is_not_a_sold_symbol_stops_the_walk(self) -> None:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20, "TQQQ": 10}, after={"SOXL": 50, "TQQQ": 10},
                                 before_cash="3500")
        drop(scenario, "MVLL", scenario.days[1:])
        drop(scenario, "TQQQ", [scenario.days[2]])
        result = lines(scenario.review())
        self.assertEqual(result["reasons"], [f"EQUITY_GAP:{scenario.days[2]}:MVLL,TQQQ"])
        self.assertEqual(result["skipped_sessions"], [scenario.days[1]])
        # A's cash is not readable: the gap is not only a sold symbol.
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50})
        scenario.snapshots[0]["cash_usd"] = None
        drop(scenario, "MVLL", scenario.days[1:])
        result = lines(scenario.review())
        self.assertEqual((result["status"], result["reasons"]), ("UNVERIFIED", [f"EQUITY_GAP:{scenario.days[0]}:CASH"]))

    def test_e_a_line_breach_on_the_current_session_is_still_caught_after_skipped_sessions(self) -> None:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50}, soxl_eval="80")
        drop(scenario, "MVLL", scenario.days[1:])
        review = scenario.review()
        self.assertEqual(lines(review)["skipped_sessions"], scenario.days[1:8])
        self.assertEqual(events(review), [("L1", EVAL, "open")])  # 9,000 = 10,000 x 0.90
        self.assertEqual(lines(review)["closing_equity_usd"], "9000")

    def test_a_record_that_is_not_confirmed_by_a_ledger_entry_does_not_open_the_skip(self) -> None:
        # Activation bound to B, so A is before activation and the ledger check of the walk does not cover it.
        for confirmed, expected in ((True, "EVALUATED"), (False, "UNVERIFIED")):
            scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50})
            scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000", revision=2))
            scenario.snapshots[0]["from_ledger_entry"] = confirmed
            drop(scenario, "MVLL", scenario.days[1:])
            result = lines(scenario.review())
            self.assertEqual(result["status"], expected)
            if not confirmed:
                self.assertEqual(result["reasons"], [f"EQUITY_GAP:{scenario.days[1]}:MVLL"])
                self.assertEqual(result["skipped_sessions"], [])

    def test_records_out_of_order_do_not_open_the_skip(self) -> None:
        # B is listed before A: the later record does not come after A in list order.
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50})
        scenario.snapshots.reverse()
        drop(scenario, "MVLL", scenario.days[1:])
        result = lines(scenario.review())
        self.assertEqual((result["status"], result["reasons"]), ("UNVERIFIED", [f"EQUITY_GAP:{scenario.days[1]}:MVLL"]))
        self.assertEqual(result["skipped_sessions"], [])

    def test_the_skip_check_itself_refuses_reversed_or_unconfirmed_records(self) -> None:
        days = jump_scenario(before={"SOXL": 50}, after={"SOXL": 50}).days
        a = fx.snapshot(days[0], {"SOXL": 50, "MVLL": 20}, "4000", revision=1)
        b = fx.snapshot(days[8], {"SOXL": 50}, "5000", revision=2)
        self.assertTrue(pe._sold_symbol_gap([a, b], a, days[1], EVAL, ["MVLL"]))
        self.assertFalse(pe._sold_symbol_gap([a, b], a, days[1], EVAL, []))
        self.assertFalse(pe._sold_symbol_gap([a, b], a, days[1], EVAL, ["MVLL", "SOXL"]))
        self.assertFalse(pe._sold_symbol_gap([a, b], a, days[1], EVAL, ["MVLL", "CASH"]))
        self.assertFalse(pe._sold_symbol_gap([a, b], a, days[1], days[7], ["MVLL"]))  # B after the evaluation
        self.assertFalse(pe._sold_symbol_gap([a, b], b, days[1], EVAL, ["MVLL"]))  # not the session's record
        self.assertFalse(pe._sold_symbol_gap([a, dict(b, state_revision=1)], a, days[1], EVAL, ["MVLL"]))
        self.assertFalse(pe._sold_symbol_gap([a, dict(b, state_revision=True)], a, days[1], EVAL, ["MVLL"]))
        self.assertFalse(pe._sold_symbol_gap([a, dict(b, from_ledger_entry=False)], a, days[1], EVAL, ["MVLL"]))
        unconfirmed = dict(a, from_ledger_entry=False)
        self.assertFalse(pe._sold_symbol_gap([unconfirmed, b], unconfirmed, days[1], EVAL, ["MVLL"]))
        # An as_of reversal: a record listed earlier is dated after A but still on or before the session.
        c = fx.snapshot(days[1], {"SOXL": 50, "MVLL": 20}, "4000", revision=0)
        self.assertFalse(pe._sold_symbol_gap([c, a, b], a, days[1], EVAL, ["MVLL"]))
        # The earliest later record still holds the symbol: it was not sold by the next record.
        middle = fx.snapshot(days[4], {"SOXL": 50, "MVLL": 20}, "4000", revision=2)
        self.assertFalse(pe._sold_symbol_gap([a, middle, dict(b, state_revision=3)], a, days[1], EVAL, ["MVLL"]))
        # A later record listed after A but with a lower revision than A.
        self.assertFalse(pe._sold_symbol_gap(
            [dict(a, state_revision=2), dict(middle, state_revision=1, holdings={"SOXL": 50}), dict(b, state_revision=3)],
            dict(a, state_revision=2), days[1], EVAL, ["MVLL"]))


class ClosedPositionPeakReviewTests(unittest.TestCase):
    def scenario(self, *entries: dict[str, Any]) -> Scenario:
        scenario = jump_scenario(before={"SOXL": 50, "MVLL": 20}, after={"SOXL": 50})
        drop(scenario, "MVLL", scenario.days[1:])
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000"), *entries)
        return scenario

    def unmatched(self, review: dict[str, Any]) -> list[str]:
        return [reason for reason in trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"]
                if reason.startswith("JOURNAL_REVIEW_UNMATCHED")]

    def test_f_a_completed_review_of_a_sold_symbol_is_not_unmatched(self) -> None:
        review = self.scenario(fx.peak_review_entry("MVLL", "60", "2026-09-01")).review()
        self.assertEqual(self.unmatched(review), [])
        self.assertFalse(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["active"])

    def test_f_a_review_of_a_symbol_never_held_is_unmatched(self) -> None:
        review = self.scenario(fx.peak_review_entry("NBIS", "250", "2026-09-01")).review()
        self.assertEqual(self.unmatched(review), ["JOURNAL_REVIEW_UNMATCHED:" + "c" * 64])

    def test_f_an_unmatched_review_of_a_symbol_held_now_is_unmatched(self) -> None:
        review = self.scenario(fx.peak_review_entry("SOXL", "120", "2026-09-01")).review()
        self.assertEqual(self.unmatched(review), ["JOURNAL_REVIEW_UNMATCHED:" + "c" * 64])

    def test_f_a_sold_symbol_review_that_is_not_completed_is_unmatched(self) -> None:
        entry = fx.peak_review_entry("MVLL", "60", "2026-09-01")
        entry["payload"]["review_status"] = "open"
        self.assertEqual(self.unmatched(self.scenario(entry).review()), ["JOURNAL_REVIEW_UNMATCHED:" + "c" * 64])


if __name__ == "__main__":
    unittest.main()
