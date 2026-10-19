"""t2rc-corefix2: the five core fixes of the t2-rc independent Judge (2026-10-15, section 11 "core").

1 R-REC1 events, C0, L0, RG3, RG4, DS1 and the record-gap check on SOXX for every candidate; GRID only in RG2.
2 RG3 lows from the session after the event (a DS1 restarts only the two-close count).
3 a group whose previous session is unknown is not new evidence.
4 redeployment candidates: requirements (1) (3) (4) (5) ok, approved policy product, not in today's sell circuit.
5 buy evidence: card_defined only when a card trigger of the group is hit today; sell keeps the definition.

Synthetic inputs only (TEST_ONLY).
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/tests"))

import test_auto_core_tickets as tickets_tests  # noqa: E402

decide_module = tickets_tests.decide_module
rules = tickets_tests.rules
tk = tickets_tests.tk
helpers = tickets_tests.helpers
Scenario = tickets_tests.Scenario
DAYS = tickets_tests.DAYS
LAST = tickets_tests.LAST
tickets_of = tickets_tests.tickets_of


def flat(n=30, **overrides):
    """A build_series-shaped benchmark: close 100, low 99.5, EMA50 100, sigma60 2%, no 1-day move."""
    base = {"days": helpers.sessions("2026-06-01", n), "close": [100.0] * n, "low": [99.5] * n,
            "sigma60": [0.02] * n, "ret1": [0.0] * n, "hi20": [100.0] * n, "ema50": [100.0] * n}
    base.update({key: list(value) for key, value in overrides.items()})
    return base


def run_rrec1(benchmark, **kwargs):
    arguments = dict(benchmark=benchmark, candidate=None, evaluation_session=benchmark["days"][-1],
                     ev3_user_dates=[], thesis_damage=[])
    arguments.update(kwargs)
    return rules.rrec1(**arguments)


def pwr_scenario(**kwargs):
    scenario = Scenario(extra_members=("PWR",), **kwargs)
    return scenario


# ---------------------------------------------------------------------------------------------
# 1 R-REC1 on SOXX, GRID only in RG2
# ---------------------------------------------------------------------------------------------

class SoxxEventTests(unittest.TestCase):
    def test_grid_only_minus_two_sigma_day_is_no_event_for_a_power_candidate(self):
        scenario = pwr_scenario()
        scenario.bars["GRID"] = helpers.bars("GRID", DAYS, helpers.zigzag(len(DAYS) - 1, 150, 1.0, 0.1) + [140.0])
        result = scenario.run()
        grid = result["series"]["GRID"]
        self.assertLessEqual(grid["ret1"][-1], -2 * grid["sigma60"][-1])  # GRID alone fell 2 sigma60 or more
        shock = result["shocks"]["PWR"]
        self.assertEqual((shock["status"], shock["open"], shock["events"]), ("ok", False, []))
        row = next(row for row in result["rows"] if row["code"] == "PWR")
        self.assertEqual(row["c"][4]["s"], "ok")

    def test_soxx_minus_two_sigma_day_opens_the_event_with_soxx_c0_and_l0(self):
        soxx = helpers.zigzag(len(DAYS) - 1, 500, 2.0, 0.3) + [470.0]
        result = pwr_scenario(soxx=soxx, cash="30000").run()
        for symbol in ("PWR", "MU"):
            shock = result["shocks"][symbol]
            self.assertTrue(shock["open"], symbol)
            self.assertEqual(shock["event"]["date"], LAST)
            self.assertIn("EV1", shock["event"]["kinds"])
            self.assertEqual((shock["event"]["c0"], shock["event"]["l0"]), (470.0, 465.3))  # SOXX close, low
        self.assertNotEqual(next(row for row in result["rows"] if row["code"] == "PWR")["c"][4]["s"], "ok")

    def test_power_candidate_record_gap_is_checked_on_soxx(self):
        days = helpers.sessions("2026-06-01", 30)
        soxx = flat(ret1=[0.0] * 25 + [-0.03] + [0.0] * 4)  # a 1.5 sigma60 SOXX fall, not an event
        grid = flat()
        unrecorded = [day for day in days if day != days[25]]
        result = run_rrec1(soxx, rg2_series=grid, research_sessions=unrecorded)
        self.assertEqual(result["status"], "unk")
        self.assertIn(f"EV3B_RECORD_GAP:{days[25]}", result["reasons"])
        quiet = run_rrec1(flat(), rg2_series=flat(ret1=[0.0] * 25 + [-0.03] + [0.0] * 4),
                          research_sessions=unrecorded)
        self.assertEqual((quiet["status"], quiet["open"]), ("ok", False))  # a GRID fall leaves no gap


class Rg2BenchmarkLegTests(unittest.TestCase):
    """Event on the 11th session (EV3 a); afterwards every SOXX gate holds, so only the RG2 leg decides."""

    def case(self, **kwargs):
        soxx = flat(close=[100.0] * 11 + [101.0] * 19, low=[99.5] * 11 + [100.5] * 19)
        return run_rrec1(soxx, ev3_user_dates=[soxx["days"][10]], **kwargs)

    def test_grid_below_its_ema50_keeps_rg2_no(self):
        result = self.case(rg2_series=flat(ema50=[105.0] * 30))
        self.assertEqual((result["open"], result["status"]), (True, "no"))
        self.assertEqual(result["rg"], {"RG1": "ok", "RG2": "no", "RG3": "ok", "RG4": "ok"})

    def test_grid_and_candidate_at_or_above_ema50_close_the_event(self):
        result = self.case(rg2_series=flat(ema50=[95.0] * 30), candidate=flat())
        self.assertEqual((result["open"], result["status"]), (False, "ok"))
        self.assertEqual(result["closed_at"], flat()["days"][12])

    def test_candidate_below_its_ema50_keeps_rg2_no(self):
        result = self.case(rg2_series=flat(ema50=[95.0] * 30), candidate=flat(ema50=[105.0] * 30))
        self.assertEqual(result["rg"]["RG2"], "no")

    def test_missing_grid_makes_rg2_unknown(self):
        result = self.case(rg2_series=None)
        self.assertEqual((result["open"], result["status"], result["rg"]["RG2"]), (True, "unk", "unk"))

    def test_default_leg_is_the_benchmark(self):
        self.assertEqual(self.case()["open"], False)


# ---------------------------------------------------------------------------------------------
# 2 RG3 lows from the session after the event
# ---------------------------------------------------------------------------------------------

class Rg3LowWindowTests(unittest.TestCase):
    """Event (EV3 a) on session 10 (C0 100, L0 99); sessions 11-14 close at C0; DS1 on 15 (close below EMA50);
    sessions 16-29 close 101 with lows 100.5. Session 12's low decides."""

    def case(self, low_12):
        n = 30
        close = [100.0] * 16 + [101.0] * 14
        low = [99.5] * 10 + [99.0] + [99.5] * 5 + [100.5] * 14
        low[12] = low_12
        ema50 = [100.0] * n
        ema50[15] = 102.0  # DS1: close 100 < EMA50 102 (close stays above L0)
        soxx = flat(close=close, low=low, ema50=ema50)
        return run_rrec1(soxx, ev3_user_dates=[soxx["days"][10]]), soxx["days"]

    def test_low_below_l0_before_the_ds1_keeps_rg3_no(self):
        result, days = self.case(98.0)
        self.assertEqual(result["ds1"], days[15])
        self.assertEqual((result["open"], result["status"]), (True, "no"))
        self.assertEqual(result["rg"], {"RG1": "ok", "RG2": "ok", "RG3": "no", "RG4": "ok"})

    def test_lows_at_or_above_l0_and_two_closes_after_the_ds1_close_the_event(self):
        result, days = self.case(99.0)  # equal to L0 is not below it
        self.assertEqual((result["open"], result["status"]), (False, "ok"))
        self.assertEqual(result["closed_at"], days[17])  # the DS1 restarted the count: 16 and 17 above C0


# ---------------------------------------------------------------------------------------------
# 3 previous unknown is not new
# ---------------------------------------------------------------------------------------------

def group(name, side, previous, state="hit", card=False):
    return {"group": name, "side": side, "state": state, "previous_state": previous, "ids": [name],
            "card_defined": card}


class NewEvidenceTests(unittest.TestCase):
    def summary(self, previous_states, side="buy"):
        direction = "+" if side == "buy" else "-"
        names = ("trend_recover", "new_high") if side == "buy" else ("trend_break", "new_low")
        result = {"groups": {name: group(name, direction, previous) for name, previous in zip(names, previous_states)}}
        check = helpers.check("X", helpers.entry("X"))
        return tk.evidence_summary(side=side, result=result, check=check, official={"+": [], "-": []}, config={})

    def test_previous_unknown_is_not_new_and_the_buy_circuit_stays_shut(self):
        both = self.summary(("unk", "unk"))
        self.assertEqual((both["new_kinds"], both["new_basis_met"]), ([], False))
        self.assertTrue(both["basis_met"])  # card table N + new M: unchanged
        one = self.summary(("unk", "none"))
        self.assertEqual((one["new_kinds"], one["new_basis_met"]), (["new_high"], False))

    def test_previous_none_or_pending_is_new(self):
        result = self.summary(("none", "pending"))
        self.assertEqual((result["new_kinds"], result["new_basis_met"]), (["new_high", "trend_recover"], True))
        self.assertEqual(self.summary(("hit", "none"))["new_kinds"], ["new_high"])

    def test_sell_basis_is_unchanged(self):
        self.assertTrue(self.summary(("unk", "unk"), side="sell")["basis_met"])

    def test_scenario_buy_circuit_closes_when_the_previous_session_is_unknown(self):
        def scenario():
            item = Scenario(facts=True, earnings=True)
            item.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.soxl_two_new_cues())
            return item

        opened = scenario().run()
        self.assertEqual(opened["evidence"]["SOXL"]["buy"]["new_kinds"], ["new_high", "trend_recover"])
        self.assertIn({"symbol": "SOXL", "side": "buy", "trigger": "NEW_EVIDENCE"}, opened["planned"]["candidates"])
        self.assertEqual(len(tickets_of(opened, "SOXL", "buy")), 1, opened["planned"]["blocked"])
        original = rules.evaluate_symbol

        def unknown_yesterday(**kwargs):
            result = original(**kwargs)
            if kwargs["symbol"] == "SOXL":
                for item in result["groups"].values():
                    if item["side"] == "+":
                        item["previous_state"] = "unk"
            return result

        with mock.patch.object(rules, "evaluate_symbol", side_effect=unknown_yesterday):
            shut = scenario().run()
        evidence = shut["evidence"]["SOXL"]["buy"]
        self.assertEqual((evidence["new_kinds"], evidence["new_basis_met"], evidence["basis_met"]), ([], False, True))
        # The new-evidence circuit is shut; only the unchanged S7 add route (requirement (3) + S7 add) remains.
        soxl = [item for item in shut["planned"]["candidates"] if item["symbol"] == "SOXL" and item["side"] == "buy"]
        self.assertEqual(soxl, [{"symbol": "SOXL", "side": "buy", "trigger": "S7_ADD_RECOMMENDATION"}])


# ---------------------------------------------------------------------------------------------
# 4 redeployment candidates
# ---------------------------------------------------------------------------------------------

def row(code, *states):
    cells = [{"s": state, "t": "TEST_ONLY"} for state in states] + [{"s": "wait", "t": "TEST_ONLY"}]
    return {"code": code, "add": False, "c": cells}


class RedeployRankingTests(unittest.TestCase):
    def test_filter_and_rank(self):
        rows = [row("MU", "ok", "ok", "ok", "ok", "ok"), row("MVLL", "ok", "ok", "ok", "ok", "ok"),
                row("BE", "ok", "ok", "ok", "ok", "no"), row("AMD", "no", "ok", "ok", "ok", "ok"),
                row("DELL", "ok", "ok", "unk", "ok", "ok"), row("NBIS", "ok", "ok", "ok", "no", "ok"),
                row("LITE", "ok", "no", "ok", "ok", "ok"), row("SOXL", "ok", "ok", "ok", "ok", "ok"),
                row("TQQQ", "ok", "ok", "ok", "ok", "ok")]
        codes = [item["code"] for item in rows]
        checks = {code: {"eligible": code != "TQQQ"} for code in codes}
        evidence = {code: {"buy": {"strong": ["S"] if code == "LITE" else [],
                                   "weak_kinds": ["a", "b"] if code == "SOXL" else ["a"]}} for code in codes}
        scenarios = {code: {"status": "ok", "up": 0.1, "down": -0.1} for code in codes}
        scenarios["TQQQ"] = {"status": "unk"}
        policy = set(helpers.policy()["portfolio_exposure_policy"]["card_stock_core"]) | set(
            helpers.policy()["portfolio_exposure_policy"]["allowed_index_etfs"])
        self.assertNotIn("MVLL", policy)
        ranked = decide_module.redeploy_ranking(rows=rows, checks=checks, evidence=evidence, scenarios=scenarios,
                                                policy_instruments=policy)
        # MVLL (sell-only), BE (5), AMD (1), DELL (3 unk), NBIS (4), TQQQ (card, scenario) are out; (2) is not a filter.
        self.assertEqual([item["symbol"] for item in ranked], ["LITE", "SOXL", "MU"])
        self.assertEqual(ranked[0], {"symbol": "LITE", "up": 0.1, "down": -0.1})


class RedeployPlanTests(unittest.TestCase):
    def ctx(self, ranked):
        return {"symbols": {}, "checks": {"A": {"entry": {"card_action": "EXIT"}}, "B": {"entry": {"card_action": "HOLD"}}},
                "review": {}, "s7": {}, "holdings": {"A": 10, "B": 5}, "equity": Decimal("10000"), "weights": {},
                "closes": {}, "sigmas": {}, "config": {}, "gate0": {"ok": False, "reasons": ["G0_TEST"]},
                "gate1": {"ok": True, "reasons": []}, "buy_rows": [], "data_reasons": {}, "run_day": "2026-10-10",
                "evidence": {symbol: {"sell": {"basis_met": True, "r_max": "1/3"}} for symbol in ("A", "B")},
                "redeploy_ranked": ranked}

    def test_open_sell_circuit_without_a_ticket_is_left_out(self):
        ranked = [{"symbol": "A", "up": 0.1, "down": -0.1}, {"symbol": "B", "up": 0.2, "down": -0.2}]
        ctx = self.ctx(ranked)
        planned = tk.plan(ctx)
        self.assertEqual(planned["tickets"], [])
        self.assertIn({"symbol": "A", "side": "sell", "reasons": ["G0_TEST"]}, planned["blocked"])
        self.assertEqual(ctx["redeploy_candidate"], {"symbol": "B", "up": 0.2, "down": -0.2})
        only = self.ctx(ranked[:1])
        tk.plan(only)
        self.assertIsNone(only["redeploy_candidate"])

    def sell_scenario(self, **kwargs):
        scenario = Scenario(holdings={"SOXL": 400}, cash="3000", **kwargs)
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.falling_soxl())
        return scenario

    def sell_ticket(self, result):
        sells = tickets_of(result, "SOXL", "sell")
        self.assertEqual(len(sells), 1, result["planned"]["blocked"])
        return sells[0]

    def test_first_ranked_symbol_sold_today_gives_way_to_the_next(self):
        result = self.sell_scenario().run()
        self.assertEqual(next(item for item in result["rows"] if item["code"] == "MU")["c"][4]["s"], "ok")
        ticket = self.sell_ticket(result)
        self.assertEqual(ticket["regret"]["columns"], ["up:cash", "down:cash", "up:MU", "down:MU"])
        original = decide_module.redeploy_ranking

        def soxl_first(**kwargs):
            return [{"symbol": "SOXL", "up": 0.5, "down": 0.4}] + original(**kwargs)

        with mock.patch.object(decide_module, "redeploy_ranking", side_effect=soxl_first):
            moved = self.sell_ticket(self.sell_scenario().run())
        self.assertEqual(moved["regret"]["columns"], ["up:cash", "down:cash", "up:MU", "down:MU"])
        self.assertEqual(moved["after_sale"]["swap_pair"]["buy_next_day"].split()[0], "MU")
        self.assertEqual(moved["regret"]["rows"], ticket["regret"]["rows"])  # the table shape is unchanged

    def test_requirement_1_or_5_not_ok_leaves_only_cash(self):
        for name, kwargs in (("earnings blackout", {"earnings": False}),
                             ("R-REC1 open", {"soxx": helpers.zigzag(len(DAYS) - 1, 500, 2.0, 0.3) + [470.0]})):
            with self.subTest(case=name):
                result = self.sell_scenario(**kwargs).run()
                self.assertNotEqual(next(item for item in result["rows"] if item["code"] == "MU")["c"][
                    0 if name == "earnings blackout" else 4]["s"], "ok")
                ticket = self.sell_ticket(result)
                self.assertEqual(ticket["regret"]["columns"], ["up:cash", "down:cash"])
                self.assertIsNone(ticket["after_sale"]["swap_pair"])


# ---------------------------------------------------------------------------------------------
# 5 G3 one-third cap: card_defined for buy evidence only when the card trigger is hit
# ---------------------------------------------------------------------------------------------

class CardDefinedTests(unittest.TestCase):
    def summary(self, side, card_state):
        direction = "+" if side == "buy" else "-"
        carded, other = ("trend_recover", "new_high") if side == "buy" else ("trend_break", "new_low")
        result = {"groups": {carded: group(carded, direction, "none", card=True), other: group(other, direction, "none")},
                  "triggers": [{"id": "K1", "group": carded, "side": direction, "source": "card", "state": card_state},
                               {"id": "C3", "group": carded, "side": direction, "source": "common", "state": "hit"},
                               {"id": "C5", "group": other, "side": direction, "source": "common", "state": "hit"}]}
        check = helpers.check("X", helpers.entry("X"))
        return tk.evidence_summary(side=side, result=result, check=check, official={"+": [], "-": []}, config={})

    def test_buy_card_trigger_defined_but_not_hit_caps_at_one_third(self):
        result = self.summary("buy", "none")
        self.assertEqual((result["r_max"], result["common_only"]), ("1/3", True))

    def test_buy_card_trigger_hit_is_one_half(self):
        result = self.summary("buy", "hit")
        self.assertEqual((result["r_max"], result["common_only"]), ("1/2", False))

    def test_sell_card_definition_alone_keeps_one_half(self):
        for state in ("none", "hit"):
            result = self.summary("sell", state)
            self.assertEqual((result["r_max"], result["common_only"]), ("1/2", False), state)

    def test_price_evidence_directly(self):
        result = {"groups": {"trend_recover": group("trend_recover", "+", "none", card=True)},
                  "triggers": [{"id": "K1", "group": "trend_recover", "side": "+", "source": "card", "state": "pending"}]}
        self.assertFalse(rules.price_evidence(result, "+")["card_defined"])
        result["triggers"][0]["state"] = "hit"
        self.assertTrue(rules.price_evidence(result, "+")["card_defined"])


if __name__ == "__main__":
    unittest.main()
