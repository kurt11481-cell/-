"""Official split record: validation, backward adjustment, and its use for V and the peak review.

Synthetic inputs only. No real holdings, prices or account data are used.
"""

from __future__ import annotations

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import corporate_actions as ca  # noqa: E402
import portfolio_exposure as pe  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from test_portfolio_exposure import EVAL, SCHEMA, Scenario, trigger  # noqa: E402
from validation_common import validate_instance  # noqa: E402

CORPORATE_ACTIONS_SCHEMA = SKILL_ROOT / "schemas/corporate-actions.schema.json"


def rate_text(new: int, old: int) -> str:
    return f"{(Decimal(old) / Decimal(new) - 1) * 100:.5f}"


def action(effective: str, *, symbol: str = "MVLL", new: int = 3, old: int = 1, **over: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "symbol": symbol, "action_type": "SPLIT", "effective_session": effective, "new_shares": new,
        "old_shares": old,
        "official_source": {"issuer": "TestIssuer", "url": "https://issuer.example/split",
                            "published_date": "2020-01-01"},
        "kiwoom_crosscheck": {"api_id": "usa06012", "adjusted": "1", "dt": effective.replace("-", ""),
                              "upd_stkpc_tp": "3231", "upd_rt": rate_text(new, old)},
        "recorded_by": "cowork", "recorded_at": "2026-10-02"}
    value.update(over)
    return value


def document(*actions: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "corporate-actions-1.0", "artifact_type": "CORPORATE_ACTIONS",
            "actions": list(actions)}


def evaluated(doc: Any, sessions: list[str]) -> dict[str, Any]:
    actions, errors = ca.validate_corporate_actions(doc, sessions)
    return {"status": "INVALID" if errors else "OK", "errors": errors, "actions": actions, "sha256": None}


def raw_closes(clean: dict[str, str], steps: list[tuple[str, int, int]]) -> dict[str, str]:
    """Raw (unadjusted) closes: a close before a split is the clean close x new/old."""
    raw = {}
    for session, value in clean.items():
        numerator = denominator = 1
        for effective, new, old in steps:
            if session < effective:
                numerator, denominator = numerator * new, denominator * old
        raw[session] = format(Decimal(value) * numerator / denominator, "f")
    return raw


class SplitScenario(Scenario):
    """MVLL held; its raw closes carry the given splits. `steps` are (offset into past sessions, new, old)."""

    def __init__(self, steps: tuple[tuple[int, int, int], ...] = (), holdings: dict[str, int] | None = None,
                 cash: str = "1000") -> None:
        super().__init__(holdings or {"MVLL": 100}, cash)
        self.past = [session for session in self.sessions if session <= EVAL]
        self.clean = dict(self.closes["MVLL"])
        self.steps = [(self.past[offset], new, old) for offset, new, old in steps]
        self.closes["MVLL"] = raw_closes(self.clean, self.steps)
        self.record: dict[str, Any] | None = None

    def set_record(self, *actions: dict[str, Any]) -> None:
        self.record = evaluated(document(*actions), self.sessions)

    def review(self) -> dict[str, Any]:
        result = pe.build_exposure_review(
            policy=self.policy, evaluation_session=self.evaluation, calendar_sessions=self.sessions,
            snapshots=self.snapshots, snapshot_reasons=self.snapshot_reasons, closes=self.closes,
            close_unverified=self.close_unverified, journal=self.journal, cards=self.cards,
            earnings=self.earnings, proposals=self.proposals, corporate_actions=self.record)
        errors = validate_instance(result, SCHEMA)
        assert not errors, errors
        return result


def v_reasons(review: dict[str, Any]) -> list[str]:
    return review["exposure"]["unavailable_reasons"]


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sessions = fx.weekday_sessions(30, EVAL, extra_after=3)
        self.effective = self.sessions[10]

    def check(self, doc: Any) -> tuple[list[dict[str, Any]], list[str]]:
        return ca.validate_corporate_actions(doc, self.sessions)

    def test_valid_record_and_empty_list(self) -> None:
        actions, errors = self.check(document(action(self.effective)))
        self.assertEqual((errors, len(actions)), ([], 1))
        self.assertEqual(self.check(document()), ([], []))
        self.assertEqual(validate_instance(document(action(self.effective)), CORPORATE_ACTIONS_SCHEMA), [])

    def test_invalid_documents_make_the_whole_file_invalid(self) -> None:
        good, other = action(self.effective), action(self.sessions[12], symbol="SOXL")
        cases = {
            "extra top-level key": {**document(good), "note": "x"},
            "wrong schema version": {**document(good), "schema_version": "corporate-actions-9.9"},
            "wrong artifact type": {**document(good), "artifact_type": "OTHER"},
            "actions not a list": {**document(good), "actions": {}},
            "not an object": [good],
            "extra action key": document({**good, "note": "x"}),
            "missing action key": document({key: value for key, value in good.items() if key != "recorded_at"}),
            "duplicate symbol and session": document(good, copy.deepcopy(good)),
            "session not in this calendar": document(action("2099-01-01")),
            "new equals old": document(action(self.effective, new=2, old=2, kiwoom_crosscheck=dict(
                good["kiwoom_crosscheck"], upd_rt="0.00000"))),
            "bool shares": document({**good, "new_shares": True}),
            "zero shares": document({**good, "old_shares": 0}),
            "published after effective": document({**good, "official_source": dict(
                good["official_source"], published_date=self.sessions[11])}),
            "http url": document({**good, "official_source": dict(good["official_source"], url="http://x.example")}),
            "action type": document({**good, "action_type": "REVERSE_SPLIT"}),
            "lower-case symbol": document({**good, "symbol": "mvll"}),
            "one bad record among good ones": document(other, {**good, "recorded_by": ""}),
            "date not zero padded": document({**good, "recorded_at": "2026-6-2"}),
        }
        for name, doc in cases.items():
            with self.subTest(name):
                actions, errors = self.check(doc)
                self.assertTrue(errors)
                self.assertEqual(actions, [])

    def test_kiwoom_crosscheck_rules(self) -> None:
        good = action(self.effective)
        base = good["kiwoom_crosscheck"]
        cases = {
            "ratio and upd_rt disagree": dict(base, upd_rt="-50.00000"),
            "dt is another day": dict(base, dt=self.sessions[9].replace("-", "")),
            "dt not compact": dict(base, dt=self.effective),
            "page-end marker only": dict(base, upd_stkpc_tp="1f"),
            "empty flag": dict(base, upd_stkpc_tp=""),
            "blank flag": dict(base, upd_stkpc_tp="  "),
            "upd_rt not a number": dict(base, upd_rt="n/a"),
            "upd_rt not finite": dict(base, upd_rt="NaN"),
            "extra key": dict(base, note="x"),
        }
        for name, crosscheck in cases.items():
            with self.subTest(name):
                self.assertTrue(self.check(document({**good, "kiwoom_crosscheck": crosscheck}))[1])
        # The flag value is not interpreted, and upd_rt may differ by up to 0.005.
        for flag, rate in (("anything", "-66.66700"), ("3231", "-66.66200"), ("3231", "-66.67100")):
            with self.subTest(flag=flag, rate=rate):
                self.assertEqual(self.check(document({**good, "kiwoom_crosscheck": dict(
                    base, upd_stkpc_tp=flag, upd_rt=rate)}))[1], [])
        self.assertTrue(self.check(document({**good, "kiwoom_crosscheck": dict(base, upd_rt="-66.67300")}))[1])

    def test_reverse_split_rate_is_plus_900_for_one_to_ten(self) -> None:
        merge = action(self.effective, new=1, old=10)
        self.assertEqual(merge["kiwoom_crosscheck"]["upd_rt"], "900.00000")
        self.assertEqual(self.check(document(merge))[1], [])
        wrong = action(self.effective, new=1, old=10, kiwoom_crosscheck=dict(
            merge["kiwoom_crosscheck"], upd_rt="-90.00000"))
        self.assertTrue(self.check(document(wrong))[1])


class AdjustmentTests(unittest.TestCase):
    def test_backward_adjustment_leaves_the_input_untouched(self) -> None:
        closes = {"MVLL": {"2026-06-24": "150", "2026-06-25": "156", "2026-06-26": "46.5"},
                  "SOXX": {"2026-06-24": "500", "2026-06-25": "501", "2026-06-26": "499"}}
        before = copy.deepcopy(closes)
        adjusted = ca.adjust_closes(closes, [action("2026-06-26")])
        self.assertEqual(closes, before)
        self.assertEqual(adjusted["MVLL"], {"2026-06-24": "50", "2026-06-25": "52", "2026-06-26": "46.5"})
        self.assertEqual(adjusted["SOXX"], closes["SOXX"])
        self.assertIsNot(adjusted["SOXX"], closes["SOXX"])

    def test_reverse_split_and_accumulated_records(self) -> None:
        closes = {"MVLL": {"2026-06-01": "6", "2026-06-10": "20", "2026-06-20": "100"}}
        merge = ca.adjust_closes(closes, [action("2026-06-20", new=1, old=10)])
        self.assertEqual(merge["MVLL"], {"2026-06-01": "60", "2026-06-10": "200", "2026-06-20": "100"})
        both = ca.adjust_closes(closes, [action("2026-06-10", new=3, old=1), action("2026-06-20", new=2, old=1)])
        self.assertEqual(both["MVLL"], {"2026-06-01": "1", "2026-06-10": "10", "2026-06-20": "100"})

    def test_unusable_close_text_stays_as_it_is(self) -> None:
        closes = {"MVLL": {"2026-06-01": "n/a", "2026-06-02": "300"}}
        adjusted = ca.adjust_closes(closes, [action("2026-06-20")])
        self.assertEqual(adjusted["MVLL"], {"2026-06-01": "n/a", "2026-06-02": "100"})

    def test_applied_summary_and_in_effect_filter(self) -> None:
        records = [action("2026-06-26"), action("2026-07-10", new=1, old=10)]
        self.assertEqual(ca.applicable_actions(records, "2026-06-30"), records[:1])
        self.assertEqual(ca.applied_summary(records[:1]), [{
            "symbol": "MVLL", "effective_session": "2026-06-26", "new_shares": 3, "old_shares": 1,
            "price_factor": "0.3333333333333333333333333333"}])


class SplitVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clean = Scenario({"MVLL": 100}, "1000").review()["exposure"]

    def test_clean_series_has_a_v(self) -> None:
        self.assertEqual(v_reasons(Scenario({"MVLL": 100}, "1000").review()), [])
        self.assertIsNotNone(self.clean["sox_equivalent"])

    def test_t1_three_for_one_split_matches_pre_divided_closes(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1),))
        scenario.set_record(action(scenario.past[-30]))
        exposure = scenario.review()["exposure"]
        self.assertEqual(v_reasons(scenario.review()), [])
        self.assertEqual(exposure["sox_equivalent"], self.clean["sox_equivalent"])
        self.assertEqual(exposure["return_sessions_used"], self.clean["return_sessions_used"])
        self.assertEqual(exposure["status"], "UNVERIFIED" if scenario.review()["fail_closed"]["active"] else "VERIFIED")
        # The record is echoed in the review inputs.
        recorded = scenario.review()["inputs"]["corporate_actions"]
        self.assertEqual((recorded["status"], recorded["errors"]), ("OK", []))
        self.assertEqual([(item["symbol"], item["effective_session"], item["new_shares"], item["old_shares"])
                          for item in recorded["applied"]], [("MVLL", scenario.past[-30], 3, 1)])

    def test_t2_without_a_record_split_guard_stays(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1),))
        review = scenario.review()
        self.assertEqual(v_reasons(review), [f"SPLIT_GUARD:MVLL:{scenario.past[-30]}"])
        self.assertIsNone(review["exposure"]["sox_equivalent"])
        self.assertEqual(review["inputs"]["corporate_actions"], {
            "status": "MISSING", "sha256": None, "errors": [], "applied": []})
        self.assertIn(f"V_UNAVAILABLE:SPLIT_GUARD:MVLL:{scenario.past[-30]}",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])

    def test_t3_record_one_session_late_leaves_the_guard(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1),))
        scenario.set_record(action(scenario.past[-29]))
        review = scenario.review()
        self.assertEqual(review["inputs"]["corporate_actions"]["status"], "OK")
        self.assertIn(f"SPLIT_GUARD:MVLL:{scenario.past[-30]}", v_reasons(review))
        self.assertIsNone(review["exposure"]["sox_equivalent"])

    def test_t4_invalid_record_makes_v_unavailable(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1),))
        good = action(scenario.past[-30])
        cases = {
            "upd_rt disagrees": dict(good, kiwoom_crosscheck=dict(good["kiwoom_crosscheck"], upd_rt="-50.00000")),
            "dt differs": dict(good, kiwoom_crosscheck=dict(good["kiwoom_crosscheck"], dt="20200101")),
            "page-end marker": dict(good, kiwoom_crosscheck=dict(good["kiwoom_crosscheck"], upd_stkpc_tp="1f")),
            "empty flag": dict(good, kiwoom_crosscheck=dict(good["kiwoom_crosscheck"], upd_stkpc_tp="")),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                scenario.set_record(bad)
                review = scenario.review()
                self.assertEqual(review["inputs"]["corporate_actions"]["status"], "INVALID")
                self.assertTrue(review["inputs"]["corporate_actions"]["errors"])
                self.assertEqual(review["inputs"]["corporate_actions"]["applied"], [])
                self.assertEqual(v_reasons(review), ["CORPORATE_ACTIONS_INVALID"])
                self.assertIsNone(review["exposure"]["sox_equivalent"])
                self.assertIn("V_UNAVAILABLE:CORPORATE_ACTIONS_INVALID",
                              trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
                # Equity and the nominal exposure use raw closes and are not affected.
                self.assertEqual(review["equity"]["status"], "AVAILABLE")
                self.assertIsNotNone(review["exposure"]["nominal"])

    def test_t4_invalid_record_leaves_peak_reviews_unverified(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1),))
        scenario.set_record(action(scenario.past[-30], kiwoom_crosscheck={
            "api_id": "usa06012", "adjusted": "1", "dt": "20200101", "upd_stkpc_tp": "3231", "upd_rt": "-66.66700"}))
        review = scenario.review()
        item = next(entry for entry in review["peak_reviews"] if entry["symbol"] == "MVLL")
        self.assertEqual((item["status"], item["reasons"]), ("UNVERIFIED", ["CORPORATE_ACTIONS_INVALID"]))
        self.assertIn("PEAK_CORPORATE_ACTIONS_INVALID:MVLL", trigger(review, "required_price_missing")["reasons"])

    def test_t6_reverse_split_one_for_ten(self) -> None:
        scenario = SplitScenario(steps=((-30, 1, 10),))
        scenario.set_record(action(scenario.past[-30], new=1, old=10))
        review = scenario.review()
        self.assertEqual(v_reasons(review), [])
        self.assertEqual(review["exposure"]["sox_equivalent"], self.clean["sox_equivalent"])

    def test_t7_two_records_for_one_symbol_accumulate(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1), (-10, 2, 1)))
        scenario.set_record(action(scenario.past[-30]), action(scenario.past[-10], new=2, old=1))
        review = scenario.review()
        self.assertEqual(v_reasons(review), [])
        self.assertEqual(review["exposure"]["sox_equivalent"], self.clean["sox_equivalent"])
        self.assertEqual([item["price_factor"] for item in review["inputs"]["corporate_actions"]["applied"]],
                         ["0.3333333333333333333333333333", "0.5"])

    def test_record_after_the_evaluation_session_is_not_applied(self) -> None:
        scenario = SplitScenario()
        later = scenario.sessions[len(scenario.past)]
        scenario.set_record(action(later))
        review = scenario.review()
        self.assertEqual(review["inputs"]["corporate_actions"]["status"], "OK")
        self.assertEqual(review["inputs"]["corporate_actions"]["applied"], [])
        self.assertEqual(review["exposure"]["sox_equivalent"], self.clean["sox_equivalent"])

    def test_benchmark_split_is_adjusted_too(self) -> None:
        scenario = SplitScenario()
        scenario.closes["SOXX"] = raw_closes(scenario.closes["SOXX"], [(scenario.past[-40], 2, 1)])
        self.assertIn(f"SPLIT_GUARD:SOXX:{scenario.past[-40]}", v_reasons(scenario.review()))
        scenario.set_record(action(scenario.past[-40], symbol="SOXX", new=2, old=1))
        review = scenario.review()
        self.assertEqual(v_reasons(review), [])
        self.assertEqual(review["exposure"]["sox_equivalent"], self.clean["sox_equivalent"])


class RawPriceKeptTests(unittest.TestCase):
    def test_t8_equity_lines_and_position_close_use_raw_closes(self) -> None:
        scenario = SplitScenario(steps=((-30, 3, 1),))
        without = scenario.review()
        scenario.set_record(action(scenario.past[-30]))
        with_record = scenario.review()
        for key in ("equity", "review_lines", "positions", "activation_candidate", "snapshot"):
            self.assertEqual(without[key], with_record[key], key)
        self.assertEqual(with_record["positions"][0]["close"], "50")

    def test_t8_a_split_inside_the_line_window_is_withheld_not_guessed(self) -> None:
        # The activation snapshot predates the split, so the split session cannot be valued from it (R5).
        # Equity is never rebuilt from the split ratio; the sessions before the split are valued as before.
        scenario = SplitScenario(steps=((-30, 3, 1),))
        scenario.journal = fx.journal(fx.activation_entry(scenario.past[-40], "6000", revision=1))
        scenario.snapshots = [fx.snapshot(scenario.past[-40], {"MVLL": 100}, "1000", revision=1)]
        scenario.set_record(action(scenario.past[-30]))
        lines = scenario.review()["review_lines"]
        self.assertEqual(lines["status"], "UNVERIFIED")
        self.assertEqual(lines["reasons"], [f"EQUITY_GAP:{scenario.past[-30]}:"
                                            f"SPLIT_RECONCILIATION_REQUIRED:MVLL:{scenario.past[-30]}"])
        self.assertEqual(lines["evaluated_through"], scenario.past[-31])


class PeakReviewTests(unittest.TestCase):
    def scenario(self) -> SplitScenario:
        scenario = SplitScenario(steps=((-20, 3, 1),))
        past = scenario.past
        # Adjusted basis: 100 until the 10th session from the end, 90 after (-10%, no -30% event).
        clean = {session: ("100" if session < past[-10] else "90") for session in past}
        scenario.clean = clean
        scenario.closes["MVLL"] = raw_closes(clean, scenario.steps)
        scenario.journal = fx.journal(fx.activation_entry(past[-40], "6000", revision=1))
        scenario.snapshots = [fx.snapshot(past[-40], {"MVLL": 100}, "1000", revision=1)]
        return scenario

    @staticmethod
    def item(review: dict[str, Any]) -> dict[str, Any]:
        return next(entry for entry in review["peak_reviews"] if entry["symbol"] == "MVLL")

    def test_t9_split_after_the_basis_date_makes_no_false_event(self) -> None:
        scenario = self.scenario()
        before = self.item(scenario.review())
        self.assertEqual(before["status"], "REVIEW_OPEN")  # raw 300 -> 90 looks like -70%
        self.assertEqual(before["events"][0]["peak"], "300")
        scenario.set_record(action(scenario.past[-20]))
        item = self.item(scenario.review())
        self.assertEqual((item["status"], item["events"], item["open_events"]), ("OK", [], []))
        self.assertEqual((item["peak"], item["close"], item["threshold"]), ("100", "90", "70.0"))
        self.assertFalse(item["pause_add_recommendations"])

    def test_t9_a_real_drawdown_after_adjustment_is_still_found(self) -> None:
        scenario = self.scenario()
        past = scenario.past
        clean = {session: ("100" if session < past[-10] else "65") for session in past}
        scenario.closes["MVLL"] = raw_closes(clean, scenario.steps)
        scenario.set_record(action(past[-20]))
        item = self.item(scenario.review())
        self.assertEqual(item["status"], "REVIEW_OPEN")
        self.assertEqual((item["events"][0]["peak"], item["events"][0]["close"], item["events"][0]["threshold"]),
                         ("100", "65", "70.0"))
        self.assertEqual(item["events"][0]["breach_date"], past[-10])


class SplitReconciliationTests(unittest.TestCase):
    def scenario(self) -> SplitScenario:
        scenario = SplitScenario(steps=((-20, 3, 1),))
        scenario.set_record(action(scenario.past[-20]))
        return scenario

    def test_t10_snapshot_before_the_split_does_not_value_a_later_session(self) -> None:
        scenario = self.scenario()
        scenario.snapshots = [fx.snapshot(scenario.past[-40], {"MVLL": 100}, "1000", revision=1)]
        review = scenario.review()
        self.assertEqual(review["equity"]["status"], "UNAVAILABLE")
        self.assertIsNone(review["equity"]["closing_equity_usd"])
        reason = f"SPLIT_RECONCILIATION_REQUIRED:MVLL:{scenario.past[-20]}"
        self.assertIn(reason, trigger(review, "required_price_missing")["reasons"])
        self.assertNotIn(f"CLOSE_MISSING:MVLL:{EVAL}", trigger(review, "required_price_missing")["reasons"])
        self.assertTrue(review["fail_closed"]["active"])
        self.assertIsNone(review["exposure"]["effective"])  # no quantity guess from the split ratio

    def test_t10_snapshot_after_the_split_is_normal(self) -> None:
        scenario = self.scenario()
        scenario.snapshots = [fx.snapshot(scenario.past[-40], {"MVLL": 100}, "1000", revision=1),
                              fx.snapshot(scenario.past[-19], {"MVLL": 300}, "1000", revision=2)]
        review = scenario.review()
        self.assertEqual(review["equity"]["status"], "AVAILABLE")
        self.assertEqual(review["equity"]["closing_equity_usd"], "16000.00")  # 300 x 50 + 1000, raw close
        self.assertNotIn(f"SPLIT_RECONCILIATION_REQUIRED:MVLL:{scenario.past[-20]}",
                         trigger(review, "required_price_missing")["reasons"])

    def test_snapshot_on_the_effective_session_counts_as_after(self) -> None:
        scenario = self.scenario()
        scenario.snapshots = [fx.snapshot(scenario.past[-20], {"MVLL": 300}, "1000", revision=1)]
        self.assertEqual(scenario.review()["equity"]["status"], "AVAILABLE")

    def test_a_symbol_not_held_in_the_old_snapshot_is_not_withheld(self) -> None:
        scenario = self.scenario()
        scenario.snapshots = [fx.snapshot(scenario.past[-40], {"SOXL": 10}, "1000", revision=1)]
        self.assertEqual(scenario.review()["equity"]["status"], "AVAILABLE")

    def test_an_earlier_session_before_the_split_is_still_valued_by_the_old_snapshot(self) -> None:
        snapshot = fx.snapshot("2026-06-01", {"MVLL": 100}, "1000", revision=1)
        records = [action("2026-06-26")]
        closes = {"MVLL": {"2026-06-24": "150", "2026-06-26": "46"}}
        equity, _, missing = pe.closing_equity(snapshot, closes, "2026-06-24", records)
        self.assertEqual((equity, missing), (Decimal("16000"), []))
        equity, _, missing = pe.closing_equity(snapshot, closes, "2026-06-26", records)
        self.assertEqual((equity, missing), (None, ["SPLIT_RECONCILIATION_REQUIRED:MVLL:2026-06-26"]))
        # No records: the call behaves as before.
        self.assertEqual(pe.closing_equity(snapshot, closes, "2026-06-26")[0], Decimal("5600"))


if __name__ == "__main__":
    unittest.main()
