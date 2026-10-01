"""S5 (r2) review lines (R4), peak review (R5), cash-flow hold (R6) and the seven R0 fail-closed triggers."""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import s5_exposure_fixtures as fx  # noqa: E402
from cash_flow_evidence import build_declaration, normalize_transaction_history  # noqa: E402
from test_portfolio_exposure import EVAL, Scenario, make_closes, trigger  # noqa: E402


def line_scenario(soxl_path: list[str], *, hwm: str = "10000") -> Scenario:
    """SOXL 50 shares + cash 5,000; the last len(path) SOXL closes are set, activation on the first of them."""
    scenario = Scenario({"SOXL": 50}, "5000")
    index = scenario.sessions.index(EVAL)
    days = scenario.sessions[index - len(soxl_path) + 1:index + 1]
    for day, price in zip(days, soxl_path):
        scenario.closes["SOXL"][day] = price
    scenario.days = days
    scenario.snapshots = [fx.snapshot(days[0], {"SOXL": 50}, "5000"), fx.snapshot("2026-09-29", {"SOXL": 50}, "5000")]
    scenario.journal = fx.journal(fx.activation_entry(days[0], hwm))
    return scenario


def events(review: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(item["line_id"], item["breach_date"], item["review_status"]) for item in review["review_lines"]["events"]]


class ReviewLineBoundaryTests(unittest.TestCase):
    def test_equity_exactly_on_the_line_triggers_and_one_cent_above_does_not(self) -> None:
        scenario = line_scenario(["100", "90", "85", "82", "80"])  # equity 9,000.00 = 10,000 x 0.90
        review = scenario.review()
        self.assertEqual(events(review), [("L1", EVAL, "open")])
        self.assertEqual(review["review_lines"]["events"][0]["threshold_usd"], "9000.0")
        self.assertEqual(review["review_lines"]["closing_equity_usd"], "9000")
        scenario = line_scenario(["100", "90", "85", "82", "80.0002"])  # equity 9,000.01
        self.assertEqual(events(scenario.review()), [])

    def test_l1_is_grade_c_and_does_not_pause_recommendations(self) -> None:
        review = line_scenario(["100", "90", "85", "82", "80"]).review()
        self.assertEqual(review["review_lines"]["events"][0]["alert_grade"], "C")
        self.assertIn({"code": "S5_REVIEW_LINE_L1", "grade": "C", "breach_date": EVAL}, review["alerts"])
        self.assertFalse(review["pauses"]["add_recommendations"]["paused"])
        self.assertFalse(review["pauses"]["new_buy_recommendations"]["paused"])
        self.assertFalse(review["fail_closed"]["active"])

    def test_a_line_triggers_once_in_the_same_drawdown(self) -> None:
        scenario = line_scenario(["100", "80", "78", "79", "80"])
        review = scenario.review()
        self.assertEqual(events(review), [("L1", scenario.days[1], "open")])
        self.assertEqual(review["review_lines"]["hwm_usd"], "10000")

    def test_a_new_hwm_rearms_the_line(self) -> None:
        scenario = line_scenario(["100", "80", "110", "84", "84"])  # new HWM 10,500; 9,200 <= 9,450
        review = scenario.review()
        self.assertEqual(events(review), [("L1", scenario.days[1], "open"), ("L1", scenario.days[3], "open")])
        self.assertEqual([item["hwm"] for item in review["review_lines"]["events"]], ["10000", "10500"])
        self.assertEqual((review["review_lines"]["hwm_usd"], review["review_lines"]["hwm_date"]),
                         ("10500", scenario.days[2]))

    def test_review_continue_keeps_the_hwm_and_the_next_line_still_triggers(self) -> None:
        scenario = line_scenario(["100", "80", "80", "60", "60"])  # L1 at 9,000 then L2 at exactly 8,000
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000"),
                                      fx.line_review_entry("L1", "10000", scenario.days[1], conclusion="continue"))
        review = scenario.review()
        self.assertEqual(events(review), [("L1", scenario.days[1], "completed"), ("L2", scenario.days[3], "open")])
        self.assertEqual(review["review_lines"]["hwm_usd"], "10000")
        self.assertEqual(review["review_lines"]["events"][1]["alert_grade"], "D")
        self.assertEqual(review["pauses"]["add_recommendations"]["reasons"], ["REVIEW_LINE_OPEN:L2"])
        self.assertEqual(review["pauses"]["new_buy_recommendations"]["reasons"], ["REVIEW_LINE_OPEN:L2"])
        self.assertIn({"code": "S5_REVIEW_LINE_L2", "grade": "D", "breach_date": scenario.days[3]}, review["alerts"])
        self.assertFalse(review["review_lines"]["automatic_sell"])
        self.assertEqual(review["review_lines"]["next_line"]["line_id"], "L3")

    def test_l2_pause_is_released_only_by_a_matching_journal_review(self) -> None:
        scenario = line_scenario(["100", "80", "80", "60", "70"])  # equity recovers to 8,500: pause stays
        l1 = fx.line_review_entry("L1", "10000", scenario.days[1])
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000"), l1)
        self.assertTrue(scenario.review()["pauses"]["add_recommendations"]["paused"])
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000"), l1,
                                      fx.line_review_entry("L2", "10000", scenario.days[3]))
        review = scenario.review()
        self.assertFalse(review["pauses"]["add_recommendations"]["paused"])
        self.assertEqual(review["review_lines"]["open_events"], [])

    def test_a_gap_down_can_trigger_two_lines_on_one_day(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "58"])  # equity 7,900
        self.assertEqual(events(scenario.review()), [("L1", EVAL, "open"), ("L2", EVAL, "open")])

    def test_a_journal_review_that_matches_no_recomputed_event_fails_closed(self) -> None:
        scenario = line_scenario(["100", "80", "80", "80", "80"])
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000"),
                                      fx.line_review_entry("L1", "9999", scenario.days[1]))  # wrong HWM
        review = scenario.review()
        self.assertEqual(events(review), [("L1", scenario.days[1], "open")])
        self.assertEqual(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"],
                         ["JOURNAL_REVIEW_UNMATCHED:" + "b" * 64])
        self.assertTrue(review["pauses"]["add_recommendations"]["paused"])

    def test_a_missing_close_after_activation_is_not_skipped(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        del scenario.closes["SOXL"][scenario.days[2]]
        review = scenario.review()
        self.assertEqual(review["review_lines"]["status"], "UNVERIFIED")
        self.assertEqual(review["review_lines"]["reasons"], [f"EQUITY_GAP:{scenario.days[2]}:SOXL"])
        self.assertEqual(review["review_lines"]["evaluated_through"], scenario.days[1])
        self.assertTrue(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["active"])

    def test_without_an_activation_record_lines_are_not_judged_and_a_candidate_is_offered(self) -> None:
        scenario = line_scenario(["100", "104", "98", "96", "97"])
        scenario.snapshots = [fx.snapshot("2026-09-23", {"SOXL": 50}, "5000", revision=16),
                              fx.snapshot("2026-09-29", {"SOXL": 50}, "5000", revision=16)]
        scenario.journal = fx.journal()
        scenario.policy["portfolio_review_lines"]["hwm_initial_as_of"] = scenario.days[0]
        review = scenario.review()
        self.assertEqual((review["review_lines"]["status"], review["review_lines"]["reasons"]),
                         ("NOT_ACTIVATED", ["S5_NOT_ACTIVATED"]))
        self.assertEqual(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"], ["S5_NOT_ACTIVATED"])
        candidate = review["activation_candidate"]
        self.assertEqual((candidate["status"], candidate["hwm_usd"], candidate["hwm_as_of"]),
                         ("READY", "10200", scenario.days[1]))
        self.assertEqual((candidate["activation_date"], candidate["state_revision"]), (EVAL, 16))
        self.assertEqual(Decimal(candidate["hwm_difference_usd"]), Decimal("10200") - Decimal("28473.94"))
        del scenario.closes["SOXL"][scenario.days[2]]
        self.assertEqual(scenario.review()["activation_candidate"]["status"], "NOT_READY")

    def test_activation_session_itself_is_judged_against_the_rechecked_hwm(self) -> None:
        scenario = Scenario({"SOXL": 50}, "5000")  # equity 10,000 on the activation session, HWM 11,200
        scenario.journal = fx.journal(fx.activation_entry(EVAL, "11200", hwm_as_of="2026-09-25"))
        self.assertEqual(events(scenario.review()), [("L1", EVAL, "open")])


RAW_ROW = {"deal_kind_nm": "", "rmrk_nm": "", "fc_exct_amt": "0.00", "fc_cmsn": "0.00", "fc_deal_tax": "0.00",
           "frgn_pay_txam": "0.00", "crnc_code": "USD", "acnt_print": "FICTIONAL"}


def declaration(rows: list[dict[str, str]], declared: str | None, *, period: tuple[str, str], prior: list[Any] | None = None):
    """Fictional transaction rows -> a declaration block (no real account data)."""
    raw = {"result": {"return_code": 0, "acnt_print": "0000-0000-00 [***]", "result_list": [
        dict(RAW_ROW, deal_no=f"{index + 1:09d}", **row) for index, row in enumerate(rows)]}}
    evidence = normalize_transaction_history(raw, period_from=period[0], period_to=period[1], raw_sha256="f" * 64)
    return build_declaration(evidence, declared_usd=declared, prior_blocks=prior or [])


DEPOSIT = {"deal_dt": "20260928", "deal_kind_nm": "입출금", "rmrk_nm": "이체입금",
           "fc_exct_amt": "1000.00"}
WITHDRAWAL = {"deal_dt": "20260928", "deal_kind_nm": "입출금", "rmrk_nm": "이체출금",
              "fc_exct_amt": "1000.00"}
DIVIDEND = {"deal_dt": "20260928", "deal_kind_nm": "입출금",
            "rmrk_nm": "배당금(외화)입금", "fc_exct_amt": "50.00", "frgn_pay_txam": "7.50"}


class CashFlowHoldTests(unittest.TestCase):
    def scenario(self, cash_after: str, block: Any) -> Scenario:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        day = scenario.days[2]
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 50}, "5000", revision=1, from_entry=True),
            fx.snapshot(day, {"SOXL": 50}, cash_after, revision=2, block=block, from_entry=True),
            fx.snapshot("2026-09-29", {"SOXL": 50}, cash_after, revision=3, from_entry=True,
                        block=declaration([], None, period=(day, "2026-09-30")) if block is not None else None),
        ]
        self.period = (scenario.days[0], day)
        return scenario

    def test_declared_deposit_raises_the_hwm_by_the_same_amount_and_is_not_a_gain(self) -> None:
        scenario = self.scenario("6000", None)
        block = declaration([dict(DEPOSIT, deal_dt=scenario.days[1].replace("-", ""))], "1000.00", period=self.period)
        scenario = self.scenario("6000", block)
        review = scenario.review()
        lines = review["review_lines"]
        self.assertEqual((lines["status"], lines["hwm_usd"], lines["closing_equity_usd"]), ("EVALUATED", "11000.00", "11000"))
        self.assertEqual(lines["hwm_date"], scenario.days[0])  # the deposit did not create a new high
        self.assertEqual(lines["cash_flow"]["adjustments"][0]["amount_usd"], "1000.00")
        self.assertFalse(trigger(review, "undeclared_cash_flow")["active"])

    def test_undeclared_deposit_holds_hwm_and_lines_and_pauses_recommendations(self) -> None:
        scenario = self.scenario("6000", None)
        block = declaration([dict(DEPOSIT, deal_dt=scenario.days[1].replace("-", ""))], None, period=self.period)
        scenario = self.scenario("6000", block)
        review = scenario.review()
        lines = review["review_lines"]
        self.assertEqual((lines["status"], lines["hwm_usd"]), ("HELD", "10000"))  # not lifted to 11,000
        self.assertEqual(lines["skipped_sessions"], scenario.days[2:])
        # The later reconciliation starts after the undeclared period, so it cannot end the hold.
        self.assertEqual(trigger(review, "undeclared_cash_flow")["reasons"],
                         ["CASH_FLOW_COVERAGE_GAP", "CASH_FLOW_UNDECLARED"])
        self.assertTrue(review["pauses"]["add_recommendations"]["paused"])
        self.assertTrue(review["pauses"]["new_buy_recommendations"]["paused"])

    def test_undeclared_withdrawal_does_not_fire_a_false_line(self) -> None:
        scenario = self.scenario("4000", None)
        block = declaration([dict(WITHDRAWAL, deal_dt=scenario.days[1].replace("-", ""))], None, period=self.period)
        scenario = self.scenario("4000", block)  # equity 9,000 would look like an L1 breach
        review = scenario.review()
        self.assertEqual(review["review_lines"]["events"], [])
        self.assertTrue(trigger(review, "undeclared_cash_flow")["active"])
        declared = declaration([dict(WITHDRAWAL, deal_dt=scenario.days[1].replace("-", ""))], "-1000.00",
                               period=self.period)
        review = self.scenario("4000", declared).review()
        self.assertEqual((review["review_lines"]["hwm_usd"], review["review_lines"]["events"]), ("9000.00", []))

    def test_reconciliation_without_cash_flow_evidence_is_on_hold(self) -> None:
        review = self.scenario("5000", None).review()
        self.assertEqual(trigger(review, "undeclared_cash_flow")["reasons"], ["CASH_FLOW_EVIDENCE_MISSING"])
        self.assertEqual(review["review_lines"]["status"], "HELD")

    def test_dividends_fees_and_taxes_are_not_cash_flows(self) -> None:
        scenario = self.scenario("5042.50", None)
        block = declaration([dict(DIVIDEND, deal_dt=scenario.days[1].replace("-", ""))], None, period=self.period)
        self.assertEqual((block["declaration_status"], block["new_external_net_usd"], block["hwm_adjustment_usd"]),
                         ("NO_EXTERNAL_FLOW", "0.00", "0.00"))
        review = self.scenario("5042.50", block).review()
        lines = review["review_lines"]
        self.assertEqual((lines["status"], lines["hwm_usd"], lines["hwm_date"]),
                         ("EVALUATED", "10042.50", scenario.days[2]))  # counted as a gain, not as a deposit
        self.assertFalse(trigger(review, "undeclared_cash_flow")["active"])

    def test_a_later_full_declaration_ends_the_hold(self) -> None:
        scenario = self.scenario("6000", None)
        row = dict(DEPOSIT, deal_dt=scenario.days[1].replace("-", ""))
        undeclared = declaration([row], None, period=self.period)
        late = declaration([row], "1000.00", period=(scenario.days[0], "2026-09-30"), prior=[undeclared])
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 50}, "5000", revision=1, from_entry=True),
            fx.snapshot(scenario.days[2], {"SOXL": 50}, "6000", revision=2, block=undeclared, from_entry=True),
            fx.snapshot("2026-09-29", {"SOXL": 50}, "6000", revision=3, block=late, from_entry=True),
        ]
        review = scenario.review()
        lines = review["review_lines"]
        self.assertEqual((lines["status"], lines["hwm_usd"]), ("EVALUATED", "11000.00"))
        self.assertEqual(lines["skipped_sessions"], [scenario.days[2]])
        self.assertFalse(trigger(review, "undeclared_cash_flow")["active"])

    def test_sale_waiting_for_cash_confirmation_does_not_fire_a_false_line(self) -> None:
        scenario = line_scenario(["100", "100", "100", "100", "100"])
        day = scenario.days[2]
        clear = declaration([], None, period=(scenario.days[0], "2026-09-30"))
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 50}, "5000", revision=1, from_entry=True),
            # 20 shares sold, proceeds not yet in available cash: equity looks like 8,000
            fx.snapshot(day, {"SOXL": 30}, "5000", revision=2, decreased=True, block=clear, from_entry=True),
        ]
        review = scenario.review()
        self.assertEqual((review["review_lines"]["events"], review["review_lines"]["status"]), ([], "HELD"))
        self.assertEqual(review["review_lines"]["skipped_sessions"], scenario.days[2:])
        scenario.snapshots.append(fx.snapshot("2026-09-29", {"SOXL": 30}, "7000", revision=3, from_entry=True,
                                              block=declaration([], None, period=(day, "2026-09-30"))))
        review = scenario.review()
        self.assertEqual((review["review_lines"]["status"], review["review_lines"]["events"]), ("EVALUATED", []))
        self.assertEqual(review["review_lines"]["skipped_sessions"], [day])


class PeakReviewTests(unittest.TestCase):
    def scenario(self, nbis_path: list[str]) -> Scenario:
        scenario = Scenario({"NBIS": 5, "SOXL": 3}, "8700")
        index = scenario.sessions.index(EVAL)
        days = scenario.sessions[index - len(nbis_path) + 1:index + 1]
        scenario.closes["NBIS"][scenario.sessions[index - len(nbis_path)]] = "400"  # high before activation
        for day, price in zip(days, nbis_path):
            scenario.closes["NBIS"][day] = price
        scenario.days = days
        scenario.snapshots = [fx.snapshot(days[0], {"NBIS": 5, "SOXL": 3}, "8700"),
                              fx.snapshot("2026-09-29", {"NBIS": 5, "SOXL": 3}, "8700")]
        scenario.journal = fx.journal(fx.activation_entry(days[0], "20000"))
        return scenario

    def nbis(self, review: dict[str, Any]) -> dict[str, Any]:
        return next(item for item in review["peak_reviews"] if item["symbol"] == "NBIS")

    def test_close_exactly_at_70_percent_of_the_forward_peak_triggers(self) -> None:
        item = self.nbis(self.scenario(["200", "180", "160", "150", "140"]).review())
        self.assertEqual((item["status"], item["peak"], item["threshold"]), ("REVIEW_OPEN", "200", "140.0"))
        self.assertEqual(item["open_events"][0]["breach_date"], EVAL)
        self.assertEqual(item["open_events"][0]["alert_grade"], "B")
        self.assertFalse(item["automatic_sell"])
        item = self.nbis(self.scenario(["200", "180", "160", "150", "140.01"]).review())
        self.assertEqual((item["status"], item["pause_add_recommendations"]), ("OK", False))

    def test_peak_is_forward_only_from_activation(self) -> None:
        item = self.nbis(self.scenario(["200", "180", "160", "150", "141"]).review())  # 400 before activation ignored
        self.assertEqual((item["peak"], item["basis_date"], item["status"]), ("200", item["basis_date"], "OK"))

    def test_one_trigger_per_drawdown_and_rearm_on_a_new_high(self) -> None:
        scenario = self.scenario(["200", "140", "130", "210", "147"])
        item = self.nbis(scenario.review())
        self.assertEqual([(event["breach_date"], event["peak"]) for event in item["events"]],
                         [(scenario.days[1], "200"), (scenario.days[4], "210")])

    def test_journal_card_completion_releases_the_pause(self) -> None:
        scenario = self.scenario(["200", "140", "150", "150", "150"])
        self.assertTrue(self.nbis(scenario.review())["pause_add_recommendations"])
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "20000"),
                                      fx.peak_review_entry("NBIS", "200", scenario.days[1]))
        item = self.nbis(scenario.review())
        self.assertEqual((item["status"], item["pause_add_recommendations"]), ("OK", False))
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "20000"),
                                      fx.peak_review_entry("NBIS", "201", scenario.days[1]))
        review = scenario.review()
        self.assertTrue(self.nbis(review)["pause_add_recommendations"])
        self.assertTrue(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["active"])

    def test_new_entry_uses_its_first_reconciled_date(self) -> None:
        scenario = self.scenario(["200", "140", "150", "150", "150"])
        scenario.snapshots = [fx.snapshot(scenario.days[0], {"SOXL": 3}, "9700"),
                              fx.snapshot(scenario.days[2], {"NBIS": 5, "SOXL": 3}, "8700")]
        item = self.nbis(scenario.review())
        self.assertEqual((item["basis_date"], item["peak"], item["status"]), (scenario.days[2], "150", "OK"))

    def test_close_gap_since_the_basis_date_is_unverified(self) -> None:
        scenario = self.scenario(["200", "180", "160", "150", "150"])
        del scenario.closes["NBIS"][scenario.days[2]]
        review = scenario.review()
        item = self.nbis(review)
        self.assertEqual((item["status"], item["pause_add_recommendations"]), ("UNVERIFIED", True))
        self.assertIn(f"PEAK_CLOSE_GAP:{scenario.days[2]}:NBIS", trigger(review, "required_price_missing")["reasons"])


class FailClosedTriggerTests(unittest.TestCase):
    """Each R0 trigger pauses add and new-buy recommendations; reduce recommendations continue, labelled."""

    def above_band(self) -> Scenario:
        return Scenario({"SOXL": 62}, "3800")  # N = 1.86

    def add_zone(self) -> Scenario:
        return Scenario({"SOXL": 30}, "7000")

    def assert_fail_closed(self, review: dict[str, Any], name: str, *, reduce_expected: bool = True) -> None:
        self.assertTrue(trigger(review, name)["active"], name)
        self.assertTrue(review["fail_closed"]["active"])
        self.assertEqual(review["fail_closed"]["pause"], ["add_recommendations", "new_buy_recommendations"])
        self.assertEqual(review["fail_closed"]["continue_with_unverified_label"], ["reduce_recommendations", "warnings"])
        for kind in ("add_recommendations", "new_buy_recommendations"):
            self.assertIn(f"FAIL_CLOSED:{name}", review["pauses"][kind]["reasons"])
        self.assertIn("S5_FAIL_CLOSED_UNVERIFIED", [alert["code"] for alert in review["alerts"]])
        self.assertTrue(all(alert["label"] == "UNVERIFIED" for alert in review["alerts"]))
        self.assertEqual(review["recommendations"]["add"], [])
        if reduce_expected:
            self.assertTrue(review["recommendations"]["reduce"])
            self.assertTrue(all(item["label"] == "UNVERIFIED" for item in review["recommendations"]["reduce"]))

    def assert_add_omitted(self, scenario: Scenario, name: str) -> None:
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.05"}]
        review = scenario.review()
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertIn(f"FAIL_CLOSED:{name}", review["recommendations"]["omitted"][0]["reasons"])
        self.assertEqual(review["recommendations"]["proposals"][0]["status"], "OMITTED")
        self.assertIn(f"FAIL_CLOSED:{name}", review["recommendations"]["proposals"][0]["reasons"])

    def test_baseline_has_no_trigger_and_gives_an_add(self) -> None:
        review = self.add_zone().review()
        self.assertFalse(review["fail_closed"]["active"])
        self.assertEqual([item["id"] for item in review["fail_closed"]["triggers"]], list(
            fx.real_policy()["portfolio_exposure_policy"]["fail_closed"]["triggers"]))
        self.assertTrue(review["recommendations"]["add"])
        self.assertNotIn("label", self.above_band().review()["recommendations"]["reduce"][0])

    def test_1_exposure_or_equity_or_v_unavailable(self) -> None:
        name = "exposure_or_equity_or_v_unavailable"
        scenario = self.above_band()
        scenario.closes = make_closes(scenario.sessions, lengths={"SOXL": 50})
        review = scenario.review()
        self.assert_fail_closed(review, name)
        self.assertEqual(review["exposure"]["status"], "UNAVAILABLE")
        scenario = self.add_zone()
        scenario.closes = make_closes(scenario.sessions, lengths={"SOXL": 50})
        self.assert_add_omitted_or_unavailable(scenario, name)  # E <= 1.25 cannot be established without V
        scenario = self.above_band()
        scenario.snapshot_reasons = ["STATE_CHANGED_OUTSIDE_LEDGER"]
        self.assert_fail_closed(scenario.review(), name)

    def test_2_unregistered_instrument_held(self) -> None:
        name = "unregistered_instrument_held"
        scenario = Scenario({"SOXL": 62, "ZZZZ": 1}, "3790")
        review = scenario.review()
        self.assert_fail_closed(review, name, reduce_expected=False)  # N cannot be computed at all
        self.assertEqual(review["band"]["state"], "UNAVAILABLE")
        scenario = Scenario({"SOXL": 30, "ZZZZ": 1}, "6990")
        self.assert_add_omitted_or_unavailable(scenario, name)

    def assert_add_omitted_or_unavailable(self, scenario: Scenario, name: str) -> None:
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.05"}]
        review = scenario.review()
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertIn(f"FAIL_CLOSED:{name}", review["recommendations"]["proposals"][0]["reasons"])

    def test_3_hwm_line_or_pause_state_missing_or_corrupt(self) -> None:
        name = "hwm_line_or_pause_state_missing_or_corrupt"
        scenario = self.above_band()
        scenario.journal = fx.journal()  # readable journal without an activation record
        self.assert_fail_closed(scenario.review(), name)
        scenario = self.add_zone()
        scenario.journal = fx.journal()
        self.assert_add_omitted(scenario, name)

    def test_4_decision_journal_missing_or_corrupt(self) -> None:
        name = "decision_journal_missing_or_corrupt"
        for status in ("MISSING", "CORRUPT"):
            scenario = self.above_band()
            scenario.journal = {"status": status, "entries": [], "errors": ["JOURNAL_CHAIN_BROKEN:1"] if status == "CORRUPT" else []}
            review = scenario.review()
            self.assert_fail_closed(review, name)
            self.assertIn(f"JOURNAL_{status}", trigger(review, name)["reasons"])
            scenario = self.add_zone()
            scenario.journal = {"status": status, "entries": [], "errors": []}
            self.assert_add_omitted(scenario, name)
        scenario = self.add_zone()
        scenario.journal = fx.journal(fx.activation_entry(EVAL, "10000"), fx.activation_entry(EVAL, "10000"))
        self.assertIn("MULTIPLE_S5_ACTIVATION_ENTRIES", trigger(scenario.review(), name)["reasons"])

    def test_5_broker_snapshot_older_than_four_calendar_days(self) -> None:
        name = "broker_snapshot_older_than_broker_snapshot_max_age_calendar_days"
        scenario = self.above_band()
        scenario.snapshots = [fx.snapshot("2026-09-25", scenario.holdings, scenario.cash)]  # 5 days
        review = scenario.review()
        self.assert_fail_closed(review, name)
        self.assertEqual(trigger(review, name)["reasons"], ["BROKER_SNAPSHOT_AGE_DAYS:5"])
        scenario = self.above_band()
        scenario.snapshots = [fx.snapshot("2026-09-26", scenario.holdings, scenario.cash)]  # exactly 4 days
        self.assertFalse(trigger(scenario.review(), name)["active"])
        scenario = self.add_zone()
        scenario.snapshots = [fx.snapshot("2026-09-25", scenario.holdings, scenario.cash)]
        self.assert_add_omitted(scenario, name)

    def test_6_required_price_missing(self) -> None:
        name = "required_price_missing"
        scenario = self.above_band()
        del scenario.closes["SOXX"][EVAL]  # benchmark close missing: N still known
        review = scenario.review()
        self.assert_fail_closed(review, name)
        self.assertEqual(trigger(review, name)["reasons"], [f"CLOSE_MISSING:SOXX:{EVAL}"])
        scenario = self.above_band()
        del scenario.closes["SOXL"][EVAL]  # held instrument close missing: no weights, no reduce targets
        review = scenario.review()
        self.assert_fail_closed(review, name, reduce_expected=False)
        self.assertEqual(review["equity"]["status"], "UNAVAILABLE")
        scenario = self.above_band()
        scenario.close_unverified = {"SOXL": {EVAL: ["SESSION_CALENDAR_NOT_ACTIVE"]}}
        review = scenario.review()
        self.assert_fail_closed(review, name)
        self.assertEqual(review["exposure"]["status"], "UNVERIFIED")  # value kept on display
        self.assertIsNotNone(review["exposure"]["effective"])
        scenario = self.add_zone()
        scenario.close_unverified = {"SOXX": {EVAL: ["BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET"]}}
        self.assert_add_omitted(scenario, name)

    def test_7_undeclared_cash_flow(self) -> None:
        name = "undeclared_cash_flow"
        for scenario, check in ((self.above_band(), self.assert_fail_closed), (self.add_zone(), None)):
            scenario.snapshots = [
                fx.snapshot("2026-09-25", scenario.holdings, scenario.cash, revision=1, from_entry=True),
                fx.snapshot("2026-09-29", scenario.holdings, scenario.cash, revision=2, from_entry=True)]
            scenario.journal = fx.journal(fx.activation_entry("2026-09-25", fx.decimal_text(scenario.equity), revision=1))
            if check is not None:
                check(scenario.review(), name)
            else:
                self.assert_add_omitted(scenario, name)


if __name__ == "__main__":
    unittest.main()
