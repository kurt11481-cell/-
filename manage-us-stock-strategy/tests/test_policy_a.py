"""policy-a (K3 policy-a-1126): leveraged (3x) weight-sum cap 0.10 on exposure-increasing buys of a leveraged
instrument only, and the add (fill) default 'card ADD stock only'. Synthetic inputs only."""

from __future__ import annotations

import contextlib
import copy
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent / "scripts"))
sys.path.insert(0, str(TESTS))

import portfolio_exposure as pe  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
import test_auto_core_tickets as tickets_tests  # noqa: E402
import test_portfolio_exposure as tpe  # noqa: E402

tk = tickets_tests.tk
rules = tickets_tests.rules
helpers = tickets_tests.helpers
OLD_ADD_DEFAULT = "card_add_stock_else_SOXL"
NEW_ADD_DEFAULT = "card_add_stock_only"
CAP_REASON = "LEVERAGED_3X_WEIGHT_CAP"


def section(policy):
    return policy["portfolio_exposure_policy"]


def with_add_default(policy, value):
    changed = copy.deepcopy(policy)
    section(changed)["add_default"] = value
    return changed


def with_cap(policy, value):
    changed = copy.deepcopy(policy)
    section(changed)["leveraged_3x_weight_cap"]["max_weight_sum"] = value
    return changed


@contextlib.contextmanager
def policy_file_copy(*, cap=True, old_add_default=False):
    """(supplement 1 (ㄱ)/(가)) A temporary copy of the real alert_policy.json whose leveraged cap is 1.0 (and, when
    asked, whose add_default is the old value), read by the test helpers instead of the real file: helpers.POLICY_PATH
    and s5_exposure_fixtures.POLICY_PATH are patched for the duration. Only test inputs change; scripts are not."""
    data = fx.POLICY_PATH.read_bytes()
    edits = []
    if cap:
        edits.append((b'"max_weight_sum": 0.10', b'"max_weight_sum": 1.0'))
    if old_add_default:
        edits.append((('"add_default": "%s"' % NEW_ADD_DEFAULT).encode(), ('"add_default": "%s"' % OLD_ADD_DEFAULT).encode()))
    for old, new in edits:
        if data.count(old) != 1:
            raise AssertionError(f"policy copy: {old!r} not found exactly once")
        data = data.replace(old, new)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "alert_policy.json"
        path.write_bytes(data)
        with mock.patch.object(helpers, "POLICY_PATH", path), mock.patch.object(fx, "POLICY_PATH", path):
            yield path


def grid_proposals(symbol, kind="new_buy_within_band", **extra):
    """The decide grid for `symbol` (auto_core_tickets.proposal_targets with the real policy values)."""
    policy = section(fx.real_policy())
    targets = tk.proposal_targets(symbol, policy["nominal_multipliers"], float(policy["single_stock_nominal_cap"]),
                                  float(policy["thresholds"]["exposure_increasing_projected_exposure_lte"]),
                                  list(policy["single_stock_cap_exempt"]))
    return [dict({"kind": kind, "symbol": symbol, "target_weight": str(target)}, **extra) for target in targets]


def best(review, symbol):
    evaluations = [{"symbol": symbol, "target_weight": float(Decimal(str(item["target_weight"]))),
                    "status": result["status"], "reasons": result.get("reasons") or []}
                   for item, result in zip(review["_proposals"], review["recommendations"]["proposals"])]
    return tk.best_target(symbol, evaluations)


def review_with(scenario):
    review = scenario.review()
    review["_proposals"] = list(scenario.proposals)
    return review


# ---------------------------------------------------------------------------------------------
# a. the real policy
# ---------------------------------------------------------------------------------------------

class RealPolicyTests(unittest.TestCase):
    def test_a_new_values_and_everything_else_unchanged(self):
        policy = section(fx.real_policy())
        self.assertEqual(policy["leveraged_3x_weight_cap"]["max_weight_sum"], 0.10)
        self.assertEqual(policy["leveraged_3x_weight_cap"]["applies_to_nominal_multiplier_gte"], 3)
        self.assertEqual(policy["leveraged_3x_weight_cap"]["applies_to"], "exposure_increasing_buy_of_member_only")
        self.assertEqual(policy["add_default"], NEW_ADD_DEFAULT)
        self.assertEqual(policy["thresholds"], {"reduce_when_exposure_gte": 1.85, "add_when_exposure_lte": 1.25,
                                                "exposure_increasing_projected_exposure_lte": 1.55,
                                                "hard_ceiling_when_exposure_gte": 1.9})
        self.assertEqual(policy["target_exposure"], 1.55)
        self.assertEqual(policy["reduce_order"][-1], "SOXL")
        self.assertEqual(policy["single_stock_nominal_cap"], 0.4)
        self.assertEqual(policy["single_stock_cap_exempt"], ["SOXL", "TQQQ"])
        self.assertEqual((policy["nominal_multipliers"]["SOXL"], policy["nominal_multipliers"]["TQQQ"]), (3, 3))
        self.assertEqual(policy["add_when_default_paused"], "omit_recommendation_no_substitute")
        self.assertEqual((policy["order_authority"], policy["quantity_authority"], policy["execution_quantity"]),
                         (False, "none", None))
        config = pe.exposure_config(fx.real_policy())
        self.assertEqual((config["supplement"], config["add_supplement"]), ("SOXL", None))
        self.assertEqual((config["leveraged_cap"], config["leveraged_bound"]), (Decimal("0.1"), Decimal("3")))


# ---------------------------------------------------------------------------------------------
# b. exposure_config
# ---------------------------------------------------------------------------------------------

class ConfigTests(unittest.TestCase):
    def assert_invalid(self, policy):
        with self.assertRaises(pe.ExposureError):
            pe.exposure_config(policy)

    def test_b_cap_key_missing_or_malformed_raises(self):
        missing = copy.deepcopy(fx.real_policy())
        del section(missing)["leveraged_3x_weight_cap"]
        self.assert_invalid(missing)
        for value in ("0.1", True, None, -0.01, 1.5, float("nan"), float("inf")):
            self.assert_invalid(with_cap(fx.real_policy(), value))
        for key, value in (("applies_to_nominal_multiplier_gte", "3"), ("applies_to_nominal_multiplier_gte", 1),
                           ("applies_to", "every_buy")):
            broken = copy.deepcopy(fx.real_policy())
            section(broken)["leveraged_3x_weight_cap"][key] = value
            self.assert_invalid(broken)
        broken = copy.deepcopy(fx.real_policy())
        section(broken)["leveraged_3x_weight_cap"] = 0.1
        self.assert_invalid(broken)

    def test_b_add_default_values(self):
        old = pe.exposure_config(with_add_default(fx.real_policy(), OLD_ADD_DEFAULT))
        self.assertEqual((old["supplement"], old["add_supplement"]), ("SOXL", "SOXL"))
        new = pe.exposure_config(fx.real_policy())
        self.assertEqual((new["supplement"], new["add_supplement"]), ("SOXL", None))
        for value in ("card_add_stock_else_TQQQ", "card_add_stock_else_QQQ", "SOXL", "", None):
            self.assert_invalid(with_add_default(fx.real_policy(), value))
        self.assertEqual(pe.add_supplement_instrument(section(fx.real_policy())), None)
        self.assertEqual(pe.add_supplement_instrument(section(with_add_default(fx.real_policy(), OLD_ADD_DEFAULT))),
                         "SOXL")


# ---------------------------------------------------------------------------------------------
# c. the add (fill) default
# ---------------------------------------------------------------------------------------------

class FillDefaultTests(unittest.TestCase):
    def scenario(self):
        return tpe.Scenario({"SOXL": 5, "NBIS": 5}, "8500")  # SOXL 0.05, NBIS 0.10, E well below 1.25

    def test_c_no_card_add_gives_no_fill_and_no_soxl(self):
        review = self.scenario().review()
        self.assertEqual(review["band"]["state"], "ADD_ZONE")
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertNotIn("SOXL", [item["symbol"] for item in review["recommendations"]["omitted"]])
        self.assertEqual(review["recommendations"]["omitted"],
                         [{"kind": "add", "symbol": None, "reasons": [pe.NO_DEFAULT_ADD_REASON]}])
        self.assertNotIn("S5_ADD_RECOMMENDATION", [alert["code"] for alert in review["alerts"]])

    def test_c_card_add_is_used_as_before(self):
        scenario = self.scenario()
        scenario.cards = {"NBIS": {"action": "ADD", "valid": True, "session_date": tpe.EVAL}}
        new = scenario.review()["recommendations"]
        scenario.policy = with_add_default(scenario.policy, OLD_ADD_DEFAULT)
        old = scenario.review()["recommendations"]
        self.assertEqual([item["symbol"] for item in new["add"]], ["NBIS"])
        self.assertEqual(new["add"][0]["target_weight"], 0.4)
        self.assertEqual((new["add"], new["omitted"]), (old["add"], old["omitted"]))

    def test_c_old_add_default_still_fills_soxl_now_up_to_the_cap(self):
        scenario = self.scenario()
        scenario.policy = with_add_default(scenario.policy, OLD_ADD_DEFAULT)
        review = scenario.review()
        self.assertEqual([item["symbol"] for item in review["recommendations"]["add"]], ["SOXL"])
        self.assertEqual(review["recommendations"]["add"][0]["target_weight"], 0.1)
        self.assertEqual(review["recommendations"]["omitted"], [])
        # Without the cap (1.0) the old default fills to the projected-E bound as before.
        scenario.policy = with_cap(scenario.policy, 1.0)
        self.assertGreater(scenario.review()["recommendations"]["add"][0]["target_weight"], 0.1)


# ---------------------------------------------------------------------------------------------
# d, e, h. the cap on exposure-increasing buys
# ---------------------------------------------------------------------------------------------

class CapTests(unittest.TestCase):
    def test_d_soxl_new_evidence_grid_stops_at_the_cap(self):
        scenario = tpe.Scenario({"SOXL": 7}, "9300")  # SOXL 0.07
        scenario.proposals = grid_proposals("SOXL")
        target, reasons = best(review_with(scenario), "SOXL")
        self.assertEqual((target, reasons), (Decimal("0.1"), []))
        results = scenario.review()["recommendations"]["proposals"]
        above = [result for item, result in zip(scenario.proposals, results)
                 if Decimal(item["target_weight"]) == Decimal("0.101")]
        self.assertEqual(above[0]["reasons"], [CAP_REASON])

    def test_d_tqqq_is_capped_on_the_sum_with_soxl(self):
        scenario = tpe.Scenario({"SOXL": 7}, "9300")  # SOXL 0.07 -> TQQQ room 0.03
        scenario.proposals = grid_proposals("TQQQ")
        self.assertEqual(best(review_with(scenario), "TQQQ"), (Decimal("0.03"), []))
        scenario = tpe.Scenario({"SOXL": 6}, "9400")  # SOXL 0.06 -> TQQQ room 0.04
        scenario.proposals = grid_proposals("TQQQ")
        self.assertEqual(best(review_with(scenario), "TQQQ"), (Decimal("0.04"), []))
        scenario = tpe.Scenario({"TQQQ": 10}, "9200")  # TQQQ 0.08 -> SOXL room 0.02
        scenario.proposals = grid_proposals("SOXL")
        self.assertEqual(best(review_with(scenario), "SOXL"), (Decimal("0.02"), []))

    def test_d_already_at_or_above_the_cap_blocks_every_leveraged_target(self):
        scenario = tpe.Scenario({"SOXL": 12}, "8800")  # SOXL 0.12
        scenario.proposals = grid_proposals("SOXL")
        target, reasons = best(review_with(scenario), "SOXL")
        self.assertEqual((target, reasons), (None, [CAP_REASON]))

    def test_e_one_x_buys_are_not_blocked_by_the_cap(self):
        scenario = tpe.Scenario({"SOXL": 12}, "8800")  # leveraged 0.12, above the 0.10 cap
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "DELL", "target_weight": "0.05"},
                              {"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.05"},
                              {"kind": "new_buy_within_band", "symbol": "TQQQ", "target_weight": "0.01"}]
        scenario.cards = {"DELL": {"action": "ADD", "valid": True, "session_date": tpe.EVAL}}
        review = scenario.review()
        results = review["recommendations"]["proposals"]
        self.assertEqual([item["status"] for item in results], ["DISPLAY", "DISPLAY", "OMITTED"])
        self.assertEqual(results[2]["reasons"], [CAP_REASON])
        self.assertEqual([item["symbol"] for item in review["recommendations"]["add"]], ["DELL"])
        self.assertTrue(all(CAP_REASON not in item["reasons"] for item in review["recommendations"]["omitted"]))
        for symbol in ("DELL", "NBIS", "MU", "QQQ", "MVLL"):
            weights = {"SOXL": Decimal("0.5"), symbol: Decimal("0.05")}
            self.assertFalse(pe.leveraged(symbol, pe.exposure_config(fx.real_policy())))
            self.assertNotIn(CAP_REASON, pe.projected_increase_reasons(
                _AlwaysWithin(), weights, symbol, pe.exposure_config(fx.real_policy())))

    def test_h_swap_buy_leg_is_capped_too(self):
        scenario = tpe.Scenario({"SOXL": 7, "NBIS": 5}, "8300")  # SOXL 0.07, NBIS 0.10
        swap = {"sell_symbol": "NBIS", "sell_target_weight": "0"}
        scenario.proposals = [dict({"kind": "swap_buy_leg", "symbol": "SOXL", "target_weight": "0.1"}, **swap),
                              dict({"kind": "swap_buy_leg", "symbol": "SOXL", "target_weight": "0.101"}, **swap),
                              dict({"kind": "swap_buy_leg", "symbol": "TQQQ", "target_weight": "0.04"}, **swap)]
        results = scenario.review()["recommendations"]["proposals"]
        self.assertEqual(results[0]["status"], "DISPLAY")
        self.assertEqual((results[1]["buy_leg"], results[1]["reasons"]), ("WITHHELD", [CAP_REASON]))
        self.assertEqual((results[2]["buy_leg"], results[2]["reasons"]), ("WITHHELD", [CAP_REASON]))
        self.assertEqual(results[1]["legs"][0]["action"], "reduce")  # the sell leg is still shown


class _AlwaysWithin:
    """A model stub whose projected parts are always within the target (isolates the cap reasons)."""

    def parts(self, weights):
        return Decimal("0"), 0.0


# ---------------------------------------------------------------------------------------------
# f. reduce, warnings and fail-closed do not change
# ---------------------------------------------------------------------------------------------

class ReduceUnchangedTests(unittest.TestCase):
    def assert_same_sell_side(self, scenario):
        capped = scenario.review()
        scenario.policy = with_cap(scenario.policy, 1.0)
        free = scenario.review()
        for key in ("band", "single_stock_cap", "fail_closed", "pauses", "exposure"):
            self.assertEqual(capped[key], free[key], key)
        for key in ("reduce", "warnings"):
            self.assertEqual(capped["recommendations"][key], free["recommendations"][key], key)
        return capped

    def test_f_at_012_reduce_and_order_are_the_same_as_without_the_cap(self):
        self.assert_same_sell_side(tpe.Scenario({"SOXL": 12, "NBIS": 5}, "7800"))
        above = tpe.Scenario({"SOXL": 62, "NBIS": 5}, "2800")  # N = 1.86 + 0.10: above the band
        above.cards = {"NBIS": {"action": "TRIM", "valid": True, "session_date": tpe.EVAL}}
        review = self.assert_same_sell_side(above)
        self.assertIn(review["band"]["state"], ("ABOVE_BAND", "HARD_CEILING"))
        self.assertEqual([(item["order"], item["symbol"]) for item in review["recommendations"]["reduce"]],
                         [(2, "NBIS"), (3, "SOXL")])
        breached = tpe.Scenario({"SOXL": 50, "NBIS": 45}, "500")
        self.assert_same_sell_side(breached)

    def test_f_cap_is_not_a_single_stock_cap_breach(self):
        config = pe.exposure_config(fx.real_policy())
        self.assertEqual(pe.cap_breaches({"SOXL": Decimal("0.5"), "TQQQ": Decimal("0.3")}, config), [])
        self.assertIsNone(pe.cap_limit("SOXL", config))


# ---------------------------------------------------------------------------------------------
# g. auto_core_decide proposals to S7
# ---------------------------------------------------------------------------------------------

class DecideProposalTests(unittest.TestCase):
    def run_scenario(self, *, new_cues, policy=None):
        seen = []
        original_runner = helpers.s7_runner

        def recording_runner(**kwargs):
            runner = original_runner(**kwargs)

            def call(proposals):
                seen.extend(proposals)
                return runner(proposals)
            return call

        scenario = tickets_tests.Scenario(facts=True, earnings=True)
        if policy is not None:
            scenario.policy = policy
        scenario.bars["SOXL"] = helpers.bars("SOXL", tickets_tests.DAYS, tickets_tests.soxl_two_new_cues())
        original_evaluate = rules.evaluate_symbol

        def unknown_yesterday(**kwargs):
            result = original_evaluate(**kwargs)
            if kwargs["symbol"] == "SOXL" and not new_cues:
                for item in result["groups"].values():
                    if item["side"] == "+":
                        item["previous_state"] = "unk"
            return result

        with mock.patch.object(helpers, "s7_runner", side_effect=recording_runner), \
                mock.patch.object(rules, "evaluate_symbol", side_effect=unknown_yesterday):
            result = scenario.run()
        return result, sorted({item["symbol"] for item in seen})

    def test_g_basis_met_only_soxl_is_not_proposed_without_a_default_add(self):
        result, proposed = self.run_scenario(new_cues=False)
        evidence = result["evidence"]["SOXL"]["buy"]
        self.assertEqual((evidence["new_basis_met"], evidence["basis_met"]), (False, True))
        self.assertNotIn("SOXL", proposed)
        self.assertNotIn("SOXL", [item["symbol"] for item in result["planned"]["candidates"] if item["side"] == "buy"])

    def test_g_new_evidence_soxl_is_still_proposed(self):
        result, proposed = self.run_scenario(new_cues=True)
        self.assertTrue(result["evidence"]["SOXL"]["buy"]["new_basis_met"])
        self.assertIn("SOXL", proposed)

    def test_g_old_add_default_keeps_the_basis_met_branch(self):
        old = with_add_default(helpers.policy(), OLD_ADD_DEFAULT)
        _result, proposed = self.run_scenario(new_cues=False, policy=old)
        self.assertIn("SOXL", proposed)


# ---------------------------------------------------------------------------------------------
# i. (supplement 1, 2) the ticket path: auto_core_tickets is only called
# ---------------------------------------------------------------------------------------------

class TicketPathTests(unittest.TestCase):
    """New-evidence SOXL buy through decide -> S7 -> tickets. The ticket amount checked against the minimum is the
    one auto_core_tickets._buy_ticket uses: delta = floor((best target - current) x equity / reference) shares,
    qty = step_quantity(delta, chosen step), DEADBAND when qty x reference < equity x 0.02."""

    @staticmethod
    def run_soxl(holdings=None):
        scenario = tickets_tests.Scenario(facts=True, earnings=True, holdings=holdings)
        scenario.bars["SOXL"] = helpers.bars("SOXL", tickets_tests.DAYS, tickets_tests.soxl_two_new_cues())
        got = {"steps": []}
        original_plan, original_choose = tk.plan, tk.choose_step

        def plan(ctx):
            got["ctx"] = ctx
            return original_plan(ctx)

        def choose(table, r_max):
            step, why = original_choose(table, r_max)
            got["steps"].append(step)
            return step, why
        with mock.patch.object(tk, "plan", plan), mock.patch.object(tk, "choose_step", choose):
            result = scenario.run()
        return result, got

    @staticmethod
    def soxl_buys(result):
        return [ticket for ticket in result["planned"]["tickets"] if ticket["ticker"] == "SOXL" and ticket["side"] == "buy"]

    @staticmethod
    def code_amount(got):
        """(qty x reference, minimum, current SOXL weight, best target, equity) as _buy_ticket computes them."""
        ctx = got["ctx"]
        equity, reference = ctx["equity"], ctx["closes"]["SOXL"]
        current = Decimal(str(ctx["weights"]["SOXL"]))
        target, reasons = tk.best_target("SOXL", ctx["proposal_results"])
        assert target is not None, reasons
        delta = int((target - current) * equity / reference)  # floor for a positive value
        qty = tk.step_quantity(delta, got["steps"][-1])
        return Decimal(qty) * reference, equity * Decimal("0.02"), current, target, equity

    def test_i1_amount_below_the_minimum_is_deadband_and_above_cap_targets_carry_the_cap_reason(self):
        result, got = self.run_soxl()
        self.assertTrue(result["evidence"]["SOXL"]["buy"]["new_basis_met"])
        self.assertEqual(self.soxl_buys(result), [])
        self.assertEqual([item["reasons"] for item in result["planned"]["blocked"]
                          if item["symbol"] == "SOXL" and item["side"] == "buy"], [["DEADBAND"]])
        amount, minimum, current, target, _equity = self.code_amount(got)
        self.assertEqual(target, Decimal("0.1"))
        self.assertGreaterEqual((Decimal("0.10") - current) * _equity, minimum)  # the room alone would be enough
        self.assertLess(amount, minimum)  # but the stepped ticket amount is not: DEADBAND (existing rule)
        above = [item for item in got["ctx"]["proposal_results"]
                 if item["symbol"] == "SOXL" and Decimal(str(item["target_weight"])) > Decimal("0.1")]
        self.assertTrue(above)
        self.assertTrue(all(item["reasons"] == [CAP_REASON] for item in above))

    def test_i2_amount_at_or_above_the_minimum_gives_a_ticket_within_the_cap(self):
        result, got = self.run_soxl(holdings={"SOXL": 1})
        amount, minimum, current, target, equity = self.code_amount(got)
        self.assertEqual(target, Decimal("0.1"))
        self.assertGreaterEqual(amount, minimum)
        tickets = self.soxl_buys(result)
        self.assertEqual(len(tickets), 1, result["planned"]["blocked"])
        after = current + Decimal(tickets[0]["qty"]) * Decimal(str(tickets[0]["price"])) / equity
        self.assertLessEqual(after, Decimal("0.10"))

    def test_i3_same_input_with_the_cap_at_one_gives_the_ticket(self):
        with policy_file_copy(cap=True):
            result, got = self.run_soxl()
        self.assertEqual(len(self.soxl_buys(result)), 1, result["planned"]["blocked"])
        amount, minimum, _current, target, _equity = self.code_amount(got)
        self.assertGreater(target, Decimal("0.1"))
        self.assertGreaterEqual(amount, minimum)


if __name__ == "__main__":
    unittest.main()
