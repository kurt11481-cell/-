"""S5 (r2) exposure, review-line and recommendation rules. Synthetic inputs only."""

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

import portfolio_exposure as pe  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from validation_common import validate_instance  # noqa: E402

SCHEMA = SKILL_ROOT / "schemas/portfolio-exposure-review.schema.json"
EVAL = "2026-09-30"
PRICES = {"SOXX": "500", "SOXL": "100", "TQQQ": "80", "MVLL": "50", "NBIS": "200", "MU": "120", "DRAM": "40",
          "BE": "150", "DELL": "130", "AMD": "160", "ZZZZ": "10", "NBIL": "20"}
STOCKS = ["BE", "MU", "NBIS", "DELL", "AMD"]
FORBIDDEN_OUTPUT_KEYS = {"quantity", "order_quantity", "proposed_quantity", "shares", "limit_price", "order_type",
                         "notional_usd", "amount_to_trade_usd", "candidates", "candidate"}


def make_closes(sessions: list[str], *, symbols: list[str] | None = None, lengths: dict[str, int] | None = None,
                soxl_multiple: float = 2.9) -> dict[str, dict[str, str]]:
    """Leveraged ETFs follow the benchmark; every stock is half as volatile as the benchmark."""
    past = [session for session in sessions if session <= EVAL]
    bench = fx.benchmark_returns(len(past))
    multiples = {"SOXX": 1.0, "SOXL": soxl_multiple, "TQQQ": 2.9, "MVLL": 1.9}
    closes = {}
    for symbol in symbols or list(PRICES):
        length = (lengths or {}).get(symbol, len(past))
        closes[symbol] = fx.series(past[-length:], bench[-(length - 1):] if length > 1 else [],
                                   last=PRICES[symbol], multiple=multiples.get(symbol, 0.5))
    return closes


class Scenario:
    """One reviewable setup; tests change a field and call review()."""

    def __init__(self, holdings: dict[str, int], cash: str, *, session_count: int = 260) -> None:
        self.policy = fx.real_policy()
        self.sessions = fx.weekday_sessions(session_count, EVAL, extra_after=10)
        self.closes = make_closes(self.sessions)
        self.holdings, self.cash = holdings, cash
        self.snapshots = [fx.snapshot("2026-09-29", holdings, cash, revision=1)]
        self.equity = sum((Decimal(quantity) * Decimal(PRICES[symbol]) for symbol, quantity in holdings.items()),
                          Decimal(cash))
        self.journal = fx.journal(fx.activation_entry(EVAL, fx.decimal_text(self.equity)))
        self.snapshot_reasons: list[str] = []
        self.close_unverified: dict[str, dict[str, list[str]]] = {}
        self.cards: dict[str, Any] = {}
        self.earnings: dict[str, Any] = fx.verified_earnings(STOCKS, self.sessions[-3])
        self.proposals: list[dict[str, Any]] = []
        self.evaluation = EVAL

    def review(self) -> dict[str, Any]:
        result = pe.build_exposure_review(
            policy=self.policy, evaluation_session=self.evaluation, calendar_sessions=self.sessions,
            snapshots=self.snapshots, snapshot_reasons=self.snapshot_reasons, closes=self.closes,
            close_unverified=self.close_unverified, journal=self.journal, cards=self.cards,
            earnings=self.earnings, proposals=self.proposals)
        errors = validate_instance(result, SCHEMA)
        assert not errors, errors
        return result


def trigger(review: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in review["fail_closed"]["triggers"] if item["id"] == name)


def keys_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(key)
            found |= keys_in(child)
    elif isinstance(value, list):
        for child in value:
            found |= keys_in(child)
    return found


class PolicyValueTests(unittest.TestCase):
    """The approved r2 numbers and operators are read from policy and must not drift."""

    def test_real_policy_carries_the_fixed_r2_values(self) -> None:
        policy = fx.real_policy()
        config = pe.exposure_config(policy)
        self.assertEqual((config["target"], config["reduce_gte"], config["add_lte"], config["hard_gte"]),
                         (Decimal("1.55"), Decimal("1.85"), Decimal("1.25"), Decimal("1.9")))
        self.assertEqual(config["projected_lte"], Decimal("1.55"))
        self.assertEqual((config["cap"], config["peak_drawdown"]), (Decimal("0.4"), Decimal("0.3")))
        self.assertEqual((config["window"], config["minimum"], config["broker_max_age_days"]), (252, 60, 4))
        self.assertEqual([(line["id"], line["fraction"]) for line in config["lines"][:4]],
                         [("L1", Decimal("0.9")), ("L2", Decimal("0.8")), ("L3", Decimal("0.7")), ("L4", Decimal("0.6"))])
        self.assertEqual((config["hwm_initial"], config["hwm_initial_as_of"]), (Decimal("28473.94"), "2026-09-30"))
        self.assertEqual(config["multipliers"], {
            "SOXL": 3, "TQQQ": 3, "MVLL": 2, "BE": 1, "MU": 1, "NBIS": 1, "DELL": 1, "AMD": 1, "DRAM": 1})
        self.assertEqual(config["grades"], {
            "REVIEW_LINE_WITHOUT_PAUSE": "C", "REVIEW_LINE_WITH_PAUSE": "D", "EXPOSURE_HARD_CEILING": "D",
            "EXPOSURE_ABOVE_BAND": "B", "PEAK_REVIEW": "B", "FAIL_CLOSED_UNVERIFIED": "B", "ADD_RECOMMENDATION": "B"})
        section = policy["portfolio_exposure_policy"]
        self.assertIs(section["order_authority"], False)
        self.assertEqual(section["quantity_authority"], "none")
        self.assertIsNone(section["execution_quantity"])
        self.assertEqual(section["status"], "approved_display_only_old_controls_retained")
        self.assertEqual(policy["portfolio_review_lines"]["status"], "approved_display_only_old_controls_retained")
        self.assertEqual(section["sox_equivalent"]["latest_close_bar"], "final_regular_session_30m_bar")

    def test_first_stage_keeps_the_old_controls(self) -> None:
        policy = fx.real_policy()
        positions = policy["holding_risk_rules"]["positions"]
        self.assertEqual({symbol: rule["maximum_loss_fraction_from_average_cost"]
                          for symbol, rule in positions.items()}, {"SOXL": 0.2, "MVLL": 0.6, "NBIS": 0.1})
        self.assertIs(policy["holding_risk_rules"]["freeze_new_buy_candidates_on_any_breach"], True)
        self.assertIn("NBIL", policy["holding_risk_rules"]["de_minimis_manual_exit_positions"])
        timing = policy["holding_timing_rules"]["positions"]
        self.assertTrue(timing["SOXL"]["slots"] and timing["MVLL"]["slots"])
        self.assertIn("weakness_10ema", timing["SOXL"]["watch_only_triggers"])
        registry = policy["decision_harness"]["approved_rule_registry"]
        self.assertEqual(len(registry), 7)
        self.assertTrue(all(not item["new_buy_instrument_approved"]
                            for item in policy["decision_harness"]["instrument_registry"].values()))

    def test_missing_or_inconsistent_policy_is_rejected_not_defaulted(self) -> None:
        policy = fx.real_policy()
        broken = copy.deepcopy(policy)
        del broken["portfolio_exposure_policy"]["thresholds"]["hard_ceiling_when_exposure_gte"]
        with self.assertRaises(pe.ExposureError):
            pe.exposure_config(broken)
        broken = copy.deepcopy(policy)
        broken["portfolio_exposure_policy"]["quantity_authority"] = "fixed"
        with self.assertRaises(pe.ExposureError):
            pe.exposure_config(broken)
        broken = copy.deepcopy(policy)
        broken["portfolio_exposure_policy"]["alert_grade_mapping"]["add_recommendation"] = "A"
        with self.assertRaises(pe.ExposureError):
            pe.exposure_config(broken)
        with self.assertRaises(pe.ExposureError):
            pe.exposure_config({})


class ExposureMeasureTests(unittest.TestCase):
    def test_nominal_volatility_and_effective_exposure(self) -> None:
        scenario = Scenario({"SOXL": 30, "NBIS": 10}, "5000")  # equity 10,000: SOXL 30%, NBIS 20%
        review = scenario.review()
        exposure = review["exposure"]
        self.assertAlmostEqual(exposure["nominal"], 3 * 0.3 + 0.2, places=6)
        self.assertEqual(exposure["effective"], max(exposure["nominal"], exposure["sox_equivalent"]))
        self.assertEqual((exposure["return_sessions_used"], exposure["short_history"]), (252, False))
        self.assertEqual(exposure["status"], "VERIFIED")
        self.assertFalse(review["fail_closed"]["active"])
        self.assertEqual(review["band"]["state"], "ADD_ZONE")  # 1.1 <= 1.25

    def test_volatility_ratio_can_exceed_nominal(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        scenario.closes = make_closes(scenario.sessions, soxl_multiple=4.0)
        exposure = scenario.review()["exposure"]
        self.assertAlmostEqual(exposure["nominal"], 0.9, places=6)
        self.assertGreater(exposure["sox_equivalent"], 1.1)
        self.assertEqual(exposure["effective"], exposure["sox_equivalent"])

    def test_cash_only_portfolio_has_zero_exposure(self) -> None:
        review = Scenario({}, "1000").review()
        self.assertEqual((review["exposure"]["nominal"], review["exposure"]["effective"]), (0.0, 0.0))

    def test_history_of_60_to_251_sessions_is_used_and_labelled_short(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        scenario.closes = make_closes(scenario.sessions, lengths={"SOXL": 125})  # 124 returns
        exposure = scenario.review()["exposure"]
        self.assertEqual((exposure["return_sessions_used"], exposure["short_history"], exposure["status"]),
                         (124, True, "VERIFIED"))
        scenario.closes = make_closes(scenario.sessions, lengths={"SOXL": 61})  # exactly 60 returns
        self.assertEqual(scenario.review()["exposure"]["return_sessions_used"], 60)

    def test_held_instrument_below_60_sessions_makes_v_unavailable(self) -> None:
        scenario = Scenario({"SOXL": 70}, "3000")  # N = 2.1
        scenario.closes = make_closes(scenario.sessions, lengths={"SOXL": 60})  # 59 returns
        review = scenario.review()
        self.assertIsNone(review["exposure"]["sox_equivalent"])
        self.assertIsNone(review["exposure"]["effective"])
        self.assertAlmostEqual(review["exposure"]["effective_lower_bound"], 2.1, places=6)
        self.assertTrue(trigger(review, "exposure_or_equity_or_v_unavailable")["active"])
        self.assertEqual(review["band"]["state"], "HARD_CEILING")  # N alone already reaches 1.9

    def test_split_guard_makes_v_unavailable(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        day = scenario.sessions[scenario.sessions.index(EVAL) - 10]
        scenario.closes["SOXL"][day] = "1.0"
        review = scenario.review()
        self.assertIsNone(review["exposure"]["sox_equivalent"])
        self.assertTrue(any("SPLIT_GUARD:SOXL" in reason for reason in review["exposure"]["unavailable_reasons"]))

    def test_unregistered_holding_makes_exposure_unavailable(self) -> None:
        scenario = Scenario({"SOXL": 30, "ZZZZ": 100}, "6000")
        review = scenario.review()
        self.assertIsNone(review["exposure"]["nominal"])
        self.assertIsNone(review["exposure"]["effective"])
        self.assertEqual(trigger(review, "unregistered_instrument_held")["reasons"], ["UNREGISTERED:ZZZZ"])
        self.assertTrue(review["pauses"]["add_recommendations"]["paused"])
        self.assertTrue(review["pauses"]["new_buy_recommendations"]["paused"])


class BandTests(unittest.TestCase):
    def test_exactly_at_reduce_threshold_is_above_band(self) -> None:
        scenario = Scenario({"SOXL": 37}, "2300")  # N = 3 * 3700 / 6000 = 1.85 exactly
        review = scenario.review()
        self.assertEqual(review["band"]["state"], "ABOVE_BAND")
        self.assertTrue(review["pauses"]["new_buy_recommendations"]["paused"])
        self.assertIn("EXPOSURE_ABOVE_BAND", review["pauses"]["new_buy_recommendations"]["reasons"])
        self.assertFalse(review["band"]["urgent_reduce"])
        self.assertTrue(review["recommendations"]["reduce"])
        self.assertEqual({item["alert_grade"] for item in review["recommendations"]["reduce"]}, {"B"})
        self.assertIn({"code": "S5_EXPOSURE_ABOVE_BAND", "grade": "B"}, review["alerts"])

    def test_just_below_reduce_threshold_stays_in_band(self) -> None:
        review = Scenario({"SOXL": 3699}, "230100").review()  # N = 1.8495
        self.assertEqual(review["band"]["state"], "WITHIN_BAND")
        self.assertEqual(review["recommendations"]["reduce"], [])
        self.assertFalse(review["pauses"]["new_buy_recommendations"]["paused"])

    def test_exactly_at_hard_ceiling_blocks_all_new_buys_and_flags_urgent(self) -> None:
        scenario = Scenario({"SOXL": 19}, "1100")  # N = 3 * 1900 / 3000 = 1.9 exactly
        review = scenario.review()
        self.assertEqual(review["band"], {"state": "HARD_CEILING", "urgent_reduce": True, "block_all_new_buys": True})
        self.assertIn("EXPOSURE_HARD_CEILING", review["pauses"]["new_buy_recommendations"]["reasons"])
        self.assertTrue(all(item["urgent"] and item["alert_grade"] == "D"
                            for item in review["recommendations"]["reduce"]))
        self.assertIn({"code": "S5_EXPOSURE_HARD_CEILING", "grade": "D"}, review["alerts"])

    def test_exactly_at_add_threshold_is_add_zone(self) -> None:
        scenario = Scenario({"SOXL": 5}, "700")  # N = 1500 / 1200 = 1.25 exactly, V below N
        self.assertEqual(scenario.review()["band"]["state"], "ADD_ZONE")
        self.assertEqual(Scenario({"SOXL": 5001}, "699900").review()["band"]["state"], "WITHIN_BAND")


class ReduceOrderTests(unittest.TestCase):
    def test_cap_excess_first_then_card_trim_then_soxl(self) -> None:
        # equity 10,000: MVLL 30% (nominal 0.6 > 0.4), NBIS 10%, SOXL 40% -> N = 0.6 + 0.1 + 1.2 = 1.9
        scenario = Scenario({"MVLL": 60, "NBIS": 5, "SOXL": 40}, "2000")
        scenario.cards = {"NBIS": {"action": "TRIM", "valid": True, "session_date": EVAL}}
        review = scenario.review()
        reduce = review["recommendations"]["reduce"]
        self.assertEqual([(item["order"], item["symbol"]) for item in reduce], [(1, "MVLL"), (2, "NBIS"), (3, "SOXL")])
        self.assertEqual(reduce[0]["target_weight"], 0.2)  # 0.4 / 2
        self.assertIsNone(reduce[1]["target_weight"])  # TRIM size is the card's judgment
        self.assertLess(reduce[2]["target_weight"], reduce[2]["current_weight"])
        projected = reduce[2]["projected_after_all_steps"]
        self.assertLessEqual(projected["projected_effective"], 1.55)
        self.assertGreater(projected["projected_effective"], 1.55 - 0.01)  # reduced only as far as the target
        self.assertIn("SINGLE_STOCK_CAP_EXCEEDED", review["recommendations"]["warnings"])
        self.assertEqual(review["single_stock_cap"]["breaches"][0]["symbol"], "MVLL")

    def test_exit_card_targets_zero_and_stale_or_invalid_cards_are_ignored(self) -> None:
        scenario = Scenario({"NBIS": 5, "SOXL": 60}, "3000")
        scenario.cards = {"NBIS": {"action": "EXIT", "valid": True, "session_date": EVAL}}
        reduce = scenario.review()["recommendations"]["reduce"]
        self.assertEqual([(item["order"], item["symbol"], item["target_weight"]) for item in reduce][0],
                         (2, "NBIS", 0.0))
        scenario.cards = {"NBIS": {"action": "EXIT", "valid": True, "session_date": "2026-09-29"}}
        self.assertEqual([item["order"] for item in scenario.review()["recommendations"]["reduce"]], [3])
        scenario.cards = {"NBIS": {"action": "EXIT", "valid": False, "session_date": EVAL}}
        self.assertEqual([item["order"] for item in scenario.review()["recommendations"]["reduce"]], [3])

    def test_exactly_at_cap_is_not_a_breach(self) -> None:
        review = Scenario({"MVLL": 20, "SOXL": 30}, "6000").review()  # MVLL 10% -> nominal 0.2
        self.assertEqual(review["single_stock_cap"]["breaches"], [])
        review = Scenario({"MVLL": 40}, "8000").review()  # MVLL 20% -> nominal exactly 0.4
        self.assertEqual(review["single_stock_cap"]["breaches"], [])
        review = Scenario({"MVLL": 2001}, "399950").review()  # nominal 0.4002
        self.assertEqual([item["symbol"] for item in review["single_stock_cap"]["breaches"]], ["MVLL"])

    def test_index_leveraged_etfs_are_exempt_and_dram_is_capped(self) -> None:
        review = Scenario({"TQQQ": 50, "DRAM": 125}, "1000").review()  # TQQQ 40%, DRAM 50%
        self.assertEqual([item["symbol"] for item in review["single_stock_cap"]["breaches"]], ["DRAM"])

    def test_without_soxl_only_an_unresolved_warning_is_given(self) -> None:
        # equity 10,000: TQQQ 60% (N 1.8) + MVLL 10% (0.2) -> N = 2.0, no SOXL held
        review = Scenario({"TQQQ": 75, "MVLL": 20}, "3000").review()
        self.assertEqual(review["band"]["state"], "HARD_CEILING")
        self.assertEqual(review["recommendations"]["reduce"], [])
        self.assertIn("EXCESS_UNRESOLVED_NO_SUBSTITUTE", review["recommendations"]["warnings"])

    def test_soxl_at_zero_still_above_target_warns(self) -> None:
        # TQQQ 60% (1.8) + SOXL 5% (0.15) = 1.95: SOXL to zero still leaves 1.8 > 1.55
        review = Scenario({"TQQQ": 75, "SOXL": 5}, "3500").review()
        soxl = [item for item in review["recommendations"]["reduce"] if item["symbol"] == "SOXL"]
        self.assertEqual(soxl[0]["target_weight"], 0.0)
        self.assertIn("EXCESS_UNRESOLVED_NO_SUBSTITUTE", review["recommendations"]["warnings"])


class AddRecommendationTests(unittest.TestCase):
    def test_default_add_is_soxl_up_to_the_target(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")  # E = 0.9
        review = scenario.review()
        add = review["recommendations"]["add"]
        self.assertEqual([item["symbol"] for item in add], ["SOXL"])
        self.assertLessEqual(add[0]["projected_effective"], 1.55)
        self.assertAlmostEqual(add[0]["target_weight"], 0.516, places=3)  # 3w <= 1.55 on the 0.1%p grid
        self.assertEqual((add[0]["nature"], add[0]["return_gate"], add[0]["oos_and_shadow"], add[0]["output"]),
                         ("return_seeking", "not_passed", "skipped", "display_only"))
        self.assertEqual(add[0]["alert_grade"], "B")
        self.assertIn({"code": "S5_ADD_RECOMMENDATION", "grade": "B"}, review["alerts"])

    def test_card_add_stock_is_used_instead_of_soxl_and_is_capped(self) -> None:
        scenario = Scenario({"SOXL": 30, "NBIS": 5}, "6000")  # NBIS 10%
        scenario.cards = {"NBIS": {"action": "ADD", "valid": True, "session_date": EVAL}}
        add = scenario.review()["recommendations"]["add"]
        self.assertEqual([item["symbol"] for item in add], ["NBIS"])
        self.assertEqual(add[0]["target_weight"], 0.4)  # single-stock nominal cap
        self.assertLessEqual(add[0]["projected_effective"], 1.55)

    def test_two_card_adds_share_the_room_and_stay_jointly_within_target(self) -> None:
        scenario = Scenario({"SOXL": 30, "NBIS": 5, "MU": 5}, "5400")
        scenario.cards = {symbol: {"action": "ADD", "valid": True, "session_date": EVAL} for symbol in ("NBIS", "MU")}
        add = scenario.review()["recommendations"]["add"]
        self.assertEqual(sorted(item["symbol"] for item in add), ["MU", "NBIS"])
        self.assertTrue(all(item["projected_effective"] <= 1.55 for item in add))
        self.assertTrue(all(item["target_weight"] <= 0.4 for item in add))

    def test_add_is_limited_by_verified_cash(self) -> None:
        scenario = Scenario({"NBIS": 5}, "100")  # NBIS 90.9%... cap already exceeded -> no add target
        scenario.cards = {"NBIS": {"action": "ADD", "valid": True, "session_date": EVAL}}
        review = scenario.review()
        self.assertEqual(review["recommendations"]["add"], [])
        scenario = Scenario({"SOXL": 30}, "500")  # E = 3 * 3000/3500 = 2.57 -> not an add zone at all
        self.assertEqual(scenario.review()["recommendations"]["add"], [])
        scenario = Scenario({"DRAM": 10}, "600")  # DRAM 40%: cap reached, cash 60%
        scenario.cards = {"DRAM": {"action": "ADD", "valid": True, "session_date": EVAL}}
        omitted = scenario.review()["recommendations"]["omitted"]
        self.assertEqual(omitted[0]["reasons"], ["SINGLE_STOCK_CAP"])

    def test_projected_exposure_above_target_omits_the_add(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        config = pe.exposure_config(scenario.policy)
        model = pe.ExposureModel(config, scenario.closes, scenario.sessions, EVAL, ["SOXL"])
        # Already at the largest grid weight whose projected E is within 1.55: one more step is 1.551.
        items, omitted = pe.add_recommendations(candidates=["SOXL"], model=model,
                                                weights={"SOXL": Decimal("0.516")}, config=config)
        self.assertEqual(items, [])
        self.assertEqual(omitted, [{"kind": "add", "symbol": "SOXL", "reasons": ["PROJECTED_EXPOSURE_ABOVE_TARGET"]}])
        # When V is the larger part it limits the target before N does.
        scenario.closes = make_closes(scenario.sessions, soxl_multiple=4.0)
        add = scenario.review()["recommendations"]["add"][0]
        self.assertLess(add["target_weight"], 0.45)
        self.assertLessEqual(add["projected_effective"], 1.55)
        self.assertEqual(add["projected_effective"], add["projected_sox_equivalent"])

    def test_soxl_paused_by_peak_review_omits_the_add_without_substitute(self) -> None:
        scenario = Scenario({"SOXL": 3}, "9700")
        index = scenario.sessions.index(EVAL)
        scenario.journal = fx.journal(fx.activation_entry(scenario.sessions[index - 3], "10150"))
        for offset, price in ((3, "150"), (2, "150"), (1, "104"), (0, "100")):  # 104 <= 150 * 0.70
            scenario.closes["SOXL"][scenario.sessions[index - offset]] = price
        scenario.snapshots = [fx.snapshot(scenario.sessions[index - 3], {"SOXL": 3}, "9700"),
                              fx.snapshot(scenario.sessions[index - 1], {"SOXL": 3}, "9700")]
        review = scenario.review()
        peak = review["peak_reviews"][0]
        self.assertEqual((peak["status"], peak["open_events"][0]["breach_date"]),
                         ("REVIEW_OPEN", scenario.sessions[index - 1]))
        self.assertEqual(review["recommendations"]["add"], [])
        omitted = [item for item in review["recommendations"]["omitted"] if item["symbol"] == "SOXL"]
        self.assertEqual(omitted[0]["reasons"], ["PEAK_REVIEW_PAUSE:REVIEW_OPEN"])
        self.assertEqual(len(review["recommendations"]["omitted"]), 1)  # nothing replaces SOXL

    def test_no_baseline_peak_pauses_the_add_for_that_instrument(self) -> None:
        scenario = Scenario({"SOXL": 30, "NBIS": 5}, "6000")
        scenario.cards = {"NBIS": {"action": "ADD", "valid": True, "session_date": EVAL}}
        scenario.journal = fx.journal(status="MISSING")
        review = scenario.review()
        nbis = next(item for item in review["peak_reviews"] if item["symbol"] == "NBIS")
        self.assertEqual((nbis["status"], nbis["pause_add_recommendations"]), ("NO_BASELINE_PEAK", True))
        blockers = pe.increase_blockers(
            "NBIS", config=pe.exposure_config(scenario.policy),
            weights={"NBIS": Decimal("0.1")}, peaks={"NBIS": nbis}, earnings=scenario.earnings,
            calendar_sessions=scenario.sessions, buy_session=scenario.sessions[scenario.sessions.index(EVAL) + 1])
        self.assertEqual(blockers, ["PEAK_REVIEW_PAUSE:NO_BASELINE_PEAK"])

    def test_new_entry_with_fewer_than_60_sessions_is_blocked(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        scenario.cards = {"MU": {"action": "ADD", "valid": True, "session_date": EVAL}}
        scenario.closes = make_closes(scenario.sessions, lengths={"MU": 60})  # 59 returns
        review = scenario.review()
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertEqual(review["recommendations"]["omitted"][0],
                         {"kind": "add", "symbol": "MU", "reasons": ["V_HISTORY_BELOW_MINIMUM_BLOCKS_NEW_ENTRY"]})
        scenario.closes = make_closes(scenario.sessions, lengths={"MU": 61})
        self.assertEqual([item["symbol"] for item in scenario.review()["recommendations"]["add"]], ["MU"])
        # The new instrument's own closes must be verified as well.
        scenario.close_unverified = {"MU": {EVAL: ["CLOSE_HISTORY_PAGES_NOT_VERIFIED"]}}
        review = scenario.review()
        self.assertFalse(review["fail_closed"]["active"])
        self.assertEqual(review["recommendations"]["omitted"][0]["reasons"],
                         ["CANDIDATE_CLOSE_UNVERIFIED:CLOSE_HISTORY_PAGES_NOT_VERIFIED"])


class EarningsBlackoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = Scenario({"SOXL": 30}, "7000")
        self.next_session = self.scenario.sessions[self.scenario.sessions.index(EVAL) + 1]
        self.config = pe.exposure_config(self.scenario.policy)

    def blockers(self, symbol: str, earnings: Any) -> list[str]:
        return pe.increase_blockers(symbol, config=self.config, weights={}, peaks={}, earnings=earnings,
                                    calendar_sessions=self.scenario.sessions, buy_session=self.next_session)

    def test_window_is_two_sessions_before_through_first_session_after(self) -> None:
        sessions, index = self.scenario.sessions, self.scenario.sessions.index(self.next_session)
        for offset, expected in ((3, False), (2, True), (1, True), (0, True), (-1, True)):
            announced = sessions[index + offset]  # buy session is `offset` sessions before the announcement
            blackout, code = pe.earnings_blackout(
                "MU", {"MU": {"status": "VERIFIED", "announcement_session": announced, "timing": "AFTER_CLOSE"}},
                sessions, self.next_session)
            self.assertEqual(blackout, expected, (offset, code))
        announced = sessions[index - 1]
        self.assertEqual(pe.earnings_blackout(
            "MU", {"MU": {"status": "VERIFIED", "announcement_session": announced, "timing": "BEFORE_OPEN"}},
            sessions, self.next_session), (True, "EARNINGS_DATE_STALE"))
        self.assertEqual(pe.earnings_blackout(
            "MU", {"MU": {"status": "VERIFIED", "announcement_session": self.next_session, "timing": "BEFORE_OPEN"}},
            sessions, self.next_session), (True, "EARNINGS_BLACKOUT"))

    def test_unverified_or_uncheckable_earnings_date_is_a_blackout(self) -> None:
        self.assertEqual(self.blockers("MU", None), ["EARNINGS_DATE_UNVERIFIED"])
        self.assertEqual(self.blockers("MU", {"MU": {"status": "UNVERIFIED"}}), ["EARNINGS_DATE_UNVERIFIED"])
        self.assertEqual(self.blockers("MU", {"MU": {"status": "VERIFIED", "announcement_session": "2027-03-01"}}),
                         ["EARNINGS_WINDOW_NOT_CHECKABLE"])

    def test_mu_blackout_blocks_dram_as_a_substitute(self) -> None:
        clear = fx.verified_earnings(STOCKS, self.scenario.sessions[-3])
        self.assertEqual(self.blockers("DRAM", clear), [])
        in_blackout = dict(clear, MU={"status": "VERIFIED", "announcement_session": self.next_session,
                                      "timing": "AFTER_CLOSE"})
        self.assertEqual(self.blockers("DRAM", in_blackout), ["BLACKOUT_SUBSTITUTION_PROHIBITED:MU"])
        self.assertEqual(self.blockers("DRAM", None), ["BLACKOUT_SUBSTITUTION_PROHIBITED:MU"])  # unverified MU date
        self.assertEqual(self.blockers("SOXL", None), [])  # index ETFs have no earnings blackout

    def test_stock_in_blackout_gets_no_add_recommendation(self) -> None:
        scenario = self.scenario
        scenario.cards = {"MU": {"action": "ADD", "valid": True, "session_date": EVAL}}
        scenario.earnings = None
        review = scenario.review()
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertEqual(review["recommendations"]["omitted"][0]["reasons"], ["EARNINGS_DATE_UNVERIFIED"])

    def test_sell_only_and_unregistered_instruments_cannot_be_bought(self) -> None:
        self.assertEqual(self.blockers("MVLL", None), ["SELL_ONLY_HOLDING"])
        self.assertEqual(self.blockers("NBIL", None), ["UNREGISTERED_INSTRUMENT"])
        self.assertEqual(self.blockers("ZZZZ", None), ["UNREGISTERED_INSTRUMENT"])
        self.assertEqual(self.blockers("SOXX", None), ["UNREGISTERED_INSTRUMENT"])  # measurement only, not held


class ProposalTests(unittest.TestCase):
    def test_new_buy_within_band_is_shown_only_when_projected_exposure_and_cap_hold(self) -> None:
        scenario = Scenario({"SOXL": 45, "NBIS": 5}, "4500")  # N = 1.35 + 0.1 = 1.45 (within band)
        scenario.proposals = [
            {"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.2"},   # N 1.55 -> shown
            {"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.201"},  # N 1.551 -> omitted
            {"kind": "new_buy_within_band", "symbol": "TQQQ", "target_weight": "0.05"},   # N 1.60 -> omitted
            {"kind": "new_buy_within_band", "symbol": "MVLL", "target_weight": "0.01"},
            {"kind": "new_buy_within_band", "symbol": "ZZZZ", "target_weight": "0.01"},
            {"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.05"},   # not an increase
        ]
        review = scenario.review()
        self.assertEqual(review["band"]["state"], "WITHIN_BAND")
        results = review["recommendations"]["proposals"]
        self.assertEqual([item["status"] for item in results], ["DISPLAY"] + ["OMITTED"] * 5)
        self.assertEqual(results[0]["legs"][0]["alert_grade"], "B")
        self.assertEqual(results[1]["reasons"], ["PROJECTED_EXPOSURE_ABOVE_TARGET"])
        self.assertEqual(results[2]["reasons"], ["PROJECTED_EXPOSURE_ABOVE_TARGET"])
        self.assertEqual(results[3]["reasons"], ["SELL_ONLY_HOLDING"])
        self.assertEqual(results[4]["reasons"], ["UNREGISTERED_INSTRUMENT"])
        self.assertEqual(results[5]["reasons"], ["PROPOSAL_NOT_AN_INCREASE"])

    def test_swap_buy_leg_is_omitted_when_projected_exposure_or_the_cap_would_be_exceeded(self) -> None:
        scenario = Scenario({"SOXL": 45, "NBIS": 5}, "4500")  # N = 1.45, cash 45%
        scenario.proposals = [
            {"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.2", "sell_symbol": "MVLL",
             "sell_target_weight": "0"},   # N 1.55 -> shown
            {"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.201", "sell_symbol": "MVLL",
             "sell_target_weight": "0"},   # N 1.551 -> omitted
        ]
        results = scenario.review()["recommendations"]["proposals"]
        self.assertEqual([item["status"] for item in results], ["DISPLAY", "OMITTED"])
        self.assertEqual((results[1]["reasons"], results[1]["buy_leg"]), (["PROJECTED_EXPOSURE_ABOVE_TARGET"], "WITHHELD"))
        capped = Scenario({"SOXL": 10, "NBIS": 15}, "6000")  # NBIS 30%, N = 0.6
        capped.proposals = [{"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.401",
                             "sell_symbol": "MVLL", "sell_target_weight": "0"}]
        self.assertEqual(capped.review()["recommendations"]["proposals"][0]["reasons"], ["SINGLE_STOCK_CAP"])

    def test_new_buy_above_the_single_stock_cap_is_omitted(self) -> None:
        scenario = Scenario({"SOXL": 30, "NBIS": 15}, "4000")  # NBIS 30%, N = 0.9 + 0.3 = 1.2... add zone
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.401"}]
        self.assertEqual(scenario.review()["recommendations"]["proposals"][0]["reasons"], ["SINGLE_STOCK_CAP"])

    def test_swap_shows_the_sell_leg_first_and_withholds_the_buy_leg(self) -> None:
        scenario = Scenario({"MVLL": 40, "SOXL": 30}, "0")  # equity 5,000, no cash
        scenario.proposals = [{"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.2",
                               "sell_symbol": "MVLL", "sell_target_weight": "0.2"}]
        result = scenario.review()["recommendations"]["proposals"][0]
        self.assertEqual((result["status"], result["buy_leg"]), ("SELL_LEG_ONLY", "WITHHELD"))
        self.assertEqual([(leg["action"], leg["symbol"], leg["step"]) for leg in result["legs"]],
                         [("reduce", "MVLL", 1)])

    def test_swap_buy_leg_needs_verified_cash_not_expected_sale_proceeds(self) -> None:
        scenario = Scenario({"MVLL": 20, "SOXL": 10}, "0")  # equity 2,000: MVLL 50%, SOXL 50% -> N 2.5
        scenario.proposals = [{"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.1",
                               "sell_symbol": "MVLL", "sell_target_weight": "0"}]
        result = scenario.review()["recommendations"]["proposals"][0]
        self.assertEqual(result["status"], "SELL_LEG_ONLY")
        # After the sale is reconciled and the cash is confirmed, the buy leg can be shown.
        after = Scenario({"SOXL": 10}, "1000")  # same equity, MVLL sold, cash verified; N = 1.5
        after.proposals = [{"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.05",
                            "sell_symbol": "MVLL", "sell_target_weight": "0"}]
        result = after.review()["recommendations"]["proposals"][0]
        self.assertEqual(result["status"], "DISPLAY")
        self.assertEqual([(leg["action"], leg["symbol"], leg["step"]) for leg in result["legs"]], [("buy", "NBIS", 2)])
        # Cash that is not there is not counted: 2% verified cash cannot fund a 5% position.
        short = Scenario({"BE": 26, "AMD": 24, "SOXL": 5, "DELL": 12}, "200")
        short.proposals = [{"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.05",
                            "sell_symbol": "MVLL", "sell_target_weight": "0"}]
        result = short.review()["recommendations"]["proposals"][0]
        self.assertEqual((result["status"], result["reasons"]), ("OMITTED", ["VERIFIED_CASH_INSUFFICIENT"]))

    def test_buy_leg_is_withheld_while_a_sale_is_waiting_for_cash_confirmation(self) -> None:
        scenario = Scenario({"SOXL": 10}, "1000")
        scenario.snapshots = [fx.snapshot("2026-09-28", {"SOXL": 10, "MVLL": 20}, "0", revision=1, from_entry=True),
                              fx.snapshot("2026-09-30", {"SOXL": 10}, "1000", revision=2, decreased=True,
                                          from_entry=True)]
        scenario.journal = fx.journal(fx.activation_entry("2026-09-25", "2000", revision=1))
        scenario.proposals = [{"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.05",
                               "sell_symbol": "MVLL", "sell_target_weight": "0"}]
        review = scenario.review()
        self.assertTrue(review["review_lines"]["sale_pending_hold"])
        self.assertIn("SALE_PROCEEDS_PENDING_CASH_CONFIRMATION",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
        self.assertEqual(review["recommendations"]["proposals"][0]["status"], "OMITTED")

    def test_invalid_proposals_are_omitted(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        scenario.proposals = [{"kind": "buy"}, {"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.0005"},
                              {"kind": "swap_buy_leg", "symbol": "NBIS", "target_weight": "0.1"}]
        results = scenario.review()["recommendations"]["proposals"]
        self.assertEqual([item["reasons"] for item in results],
                         [["PROPOSAL_KIND_INVALID"], ["PROPOSAL_TARGET_INVALID"], ["SWAP_SELL_LEG_INVALID"]])


class OutputAuthorityTests(unittest.TestCase):
    def test_output_is_target_weights_only_with_no_authority(self) -> None:
        for scenario in (Scenario({"MVLL": 60, "NBIS": 5, "SOXL": 40}, "2000"), Scenario({"SOXL": 30}, "7000")):
            scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.1"}]
            review = scenario.review()
            self.assertIs(review["order_authority"], False)
            self.assertEqual(review["quantity_authority"], "none")
            self.assertIsNone(review["execution_quantity"])
            self.assertIs(review["display_only"], True)
            self.assertEqual(review["recommendation_output"], "target_weights_only")
            self.assertEqual(keys_in(review) & FORBIDDEN_OUTPUT_KEYS, set())
            self.assertTrue({item["grade"] for item in review["alerts"]} <= {"B", "C", "D"})

    def test_same_input_gives_the_same_review_id(self) -> None:
        first, second = Scenario({"SOXL": 30}, "7000").review(), Scenario({"SOXL": 30}, "7000").review()
        self.assertEqual(first, second)
        self.assertEqual(first["review_id"], pe.review_content_hash(first))

    def test_display_block_has_no_weights_or_quantities(self) -> None:
        block = pe.exposure_display_block(Scenario({"SOXL": 30}, "7000").review())
        self.assertEqual(pe.display_block_errors(block), [])
        self.assertFalse(any("weight" in key or "quantity" in key for key in block))
        self.assertEqual(pe.display_block_errors({"display_only": False}), [
            "EXPOSURE_DISPLAY_BLOCK_FIELD:source", "EXPOSURE_DISPLAY_BLOCK_FIELD:review_id",
            "EXPOSURE_DISPLAY_BLOCK_FIELD:evaluation_session", "EXPOSURE_DISPLAY_BLOCK_FIELD:exposure_status",
            "EXPOSURE_DISPLAY_BLOCK_FIELD:band_state", "EXPOSURE_DISPLAY_BLOCK_FIELD:review_lines_status",
            "EXPOSURE_DISPLAY_BLOCK_FIELD:add_paused", "EXPOSURE_DISPLAY_BLOCK_FIELD:new_buy_paused",
            "EXPOSURE_DISPLAY_BLOCK_FIELD:fail_closed_active", "EXPOSURE_DISPLAY_BLOCK_FIELD:short_history",
            "EXPOSURE_DISPLAY_BLOCK_NOT_DISPLAY_ONLY"])


if __name__ == "__main__":
    unittest.main()
