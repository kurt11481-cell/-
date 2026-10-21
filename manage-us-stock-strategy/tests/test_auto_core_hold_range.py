"""close-confirm e (user decision 2026-10-20): the hold range of a ticket (priceCalc band and hold).

decide (hold_range=True) gives every ticket priceCalc.band (the +/-1% lo-hi of loc_price) and priceCalc.hold, the cent
range in which the same judgment comes out when only the ticket symbol's own evaluation-session close is replaced
(S7 fixed). A buy's lo-hi becomes the hold range and an unverified buy gets no ticket (HOLD_RANGE_UNVERIFIED); a
sell keeps lo-hi = band. Outcome classification keeps the band. The replay (hold_range False) is unchanged.

H1 self-check and basics, H2 (E4) every band cent against the full evaluate_session path, H3 a buy boundary inside
the band (own -2 sigma60 day, R-REC1 EV5), H4 cash (and G2b), H5 a sell is only warned, H6 unverified and errors,
H7 (E1) hold off is the base, H8 (E3) outcome classification, H9 (E6, E7) determinism and unchanged inputs, H10
schema, H11 HoldCauseTests (decide off/on in one process; revert_hold_view is imported by the enter-window test).
All inputs are synthetic (TEST_ONLY); no network, no Kiwoom.
"""

from __future__ import annotations

import contextlib
import copy
import math
import sys
import unittest
from decimal import ROUND_FLOOR, Decimal
from fractions import Fraction
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

import test_auto_core_risk1r as risk1r  # noqa: E402
import test_auto_core_tickets as tickets_tests  # noqa: E402

tk = tickets_tests.tk
decide_module = tickets_tests.decide_module
helpers = tickets_tests.helpers
rules = tickets_tests.rules
validate_instance = tickets_tests.validate_instance
TICKET_SCHEMA = tickets_tests.TICKET_SCHEMA
DAYS, LAST = tickets_tests.DAYS, tickets_tests.LAST
CENT = Decimal("0.01")
ORIGINAL_EVALUATE = decide_module.evaluate_session
ORIGINAL_PLAN = tk.plan
# risk1r GOLDEN decide_compare / decide_apply before close-confirm e (base 3e753f3), measured on Windows; the decide
# hashes differ on Linux, so the check against them runs on Windows only (the off/on comparison runs everywhere).
OLD_DECIDE_GOLDEN = {"decide_compare": "2e565c3b7f2d10eb10089c81cce6899b62168bb36a6ede08f78159fcf925bf95",
                     "decide_apply": "d78459cbeb51b2d7ebe70284de3d73ffbae404093fb680c4f7fa1acbe870c43b"}
# Decision keys compared between the off and on decide runs (everything a reader of the record sees, except the
# journal's decision_sha256, which hashes the tickets).
DECISION_VIEW_KEYS = ("status", "reasons", "tickets", "candidates", "blocked", "no_action", "keys", "alerts", "dashboard",
                      "compare", "next_action_for_user", "outcomes", "open_tickets", "symbols", "evidence",
                      "buy_requirements", "exposure", "shock", "account", "facts_seen")


def revert_hold_view(value):
    """A deep copy of `value` in which every priceCalc loses band and hold, with lo-hi = band when band is there
    (the priceCalc before close-confirm e). The input is not changed."""
    out = copy.deepcopy(value)

    def walk(node):
        if isinstance(node, dict):
            calc = node.get("priceCalc")
            if isinstance(calc, dict) and ("band" in calc or "hold" in calc):
                band = calc.pop("band", None)
                calc.pop("hold", None)
                if band is not None:
                    calc["lo"], calc["hi"] = band["lo"], band["hi"]
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(out)
    return out


def run_scenario(scenario, *, hold, cash=None, plan=None):
    """Scenario.run with hold_range forced (and the buy cash, when given); plan replaces tk.plan when given."""
    extra = {"hold_range": hold, **({} if cash is None else {"cash": Decimal(cash)})}
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(decide_module, "evaluate_session",
                                              lambda **kw: ORIGINAL_EVALUATE(**{**kw, **extra})))
        if plan is not None:
            stack.enter_context(mock.patch.object(tk, "plan", plan))
        return scenario.run()


def only(result, symbol, side):
    found = tickets_tests.tickets_of(result, symbol, side)
    assert len(found) == 1, (symbol, side, result["planned"]["blocked"])
    return found[0]


def ev5_scenario(last):
    """MU whose evaluation-session return is near its own -2 sigma60 (R-REC1 EV5): a lower close is an event day."""
    scenario = tickets_tests.Scenario()
    scenario.bars["MU"] = helpers.bars("MU", DAYS, helpers.zigzag(len(DAYS), 200, 3.0, 0.2)[:-1] + [last])
    return scenario


def sell_prefix():
    return helpers.zigzag(len(DAYS) - 6, 100, 1.0, 0.05) + [100.0, 99.0, 98.0, 97.0, 96.0]


def narrow_sell_scenario():
    """SOXL sell (S7 reduce; trend_break and new_low) with its last close 0.20 under the previous session's EMA10:
    C5- (new_low) needs the close below EMA10, so from the cent at or above that EMA10 the sell evidence has one
    kind only and the sell circuit closes inside the band."""
    prefix = sell_prefix()
    last = round(rules.ema_series(prefix, rules.C["EMA_SHORT"])[-1] - 0.2, 2)
    scenario = tickets_tests.Scenario(holdings={"SOXL": 120}, cash="300",
                                      soxx=helpers.zigzag(len(DAYS) - 1, 500, 2.0, 0.3) + [470.0])
    scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, prefix + [last])
    return scenario


def recording_plan(calls, faulty=None):
    """tk.plan that records every hold_eval price (and replaces hold_eval by faulty(real) when given)."""
    def plan(ctx):
        real = ctx.get("hold_eval")
        if real is not None:
            inner = faulty(real) if faulty is not None else real

            def hold_eval(symbol, price):
                calls.append(price)
                return inner(symbol, price)
            ctx["hold_eval"] = hold_eval
        return ORIGINAL_PLAN(ctx)
    return plan


class Probe:
    """One hold-on run of a scenario that keeps what E4 needs: the evaluate_session keywords, plan()'s ctx (with
    hold_eval) and the S7 proposals and review of the reference. full(symbol, b) runs evaluate_session itself with
    that symbol's evaluation-session bar moved to b and an S7 runner that answers each proposal with the
    reference review's evaluation of the same (symbol, target_weight) (not evaluated there = not passing)."""

    def __init__(self, scenario, *, cash=None):
        self.extra = {} if cash is None else {"cash": Decimal(cash)}
        got = {}

        def evaluate(**kw):
            runner = kw["s7_runner"]

            def recording(proposals):
                got["proposals"] = [dict(item) for item in proposals]
                got["review"] = runner(proposals)
                return got["review"]
            got["kw"] = kw
            return ORIGINAL_EVALUATE(**{**kw, **self.extra, "hold_range": True, "s7_runner": recording})

        def plan(ctx):
            got["ctx"] = ctx
            return ORIGINAL_PLAN(ctx)

        with mock.patch.object(decide_module, "evaluate_session", evaluate), mock.patch.object(tk, "plan", plan):
            self.result = scenario.run()
        self.kw, self.ctx, self.review, self.proposals = got["kw"], got["ctx"], got["review"], got["proposals"]
        self.by_key = {(item["symbol"], item["target_weight"]): evaluation for item, evaluation in
                       zip(self.proposals, self.review["recommendations"]["proposals"])}

    @staticmethod
    def moved(item, price):
        def one(daily):
            bar = daily["sessions"][LAST]
            new = dict(bar, close=price, high=None if bar["high"] is None else max(bar["high"], price),
                       low=None if bar["low"] is None else min(bar["low"], price))
            return dict(daily, sessions=dict(daily["sessions"], **{LAST: new}))
        raw = one(item["raw"])
        return dict(item, raw=raw, adjusted=raw if item["adjusted"] is item["raw"] else one(item["adjusted"]))

    def full(self, symbol, price):
        seen = []

        def s7_runner(proposals):
            seen.append([dict(item) for item in proposals])
            out = []
            for index, item in enumerate(proposals):
                found = self.by_key.get((item["symbol"], item["target_weight"]))
                out.append({**found, "index": index} if found is not None else
                           {"index": index, "status": "NOT_EVALUATED_AT_REF", "reasons": ["NOT_EVALUATED_AT_REF"]})
            return {**self.review, "recommendations": {**self.review["recommendations"], "proposals": out}}
        bars = dict(self.kw["bars"])
        bars[symbol] = self.moved(bars[symbol], price)
        result = ORIGINAL_EVALUATE(**{**self.kw, **self.extra, "bars": bars, "s7_runner": s7_runner})
        return result, seen[0]


def full_code(probe, result, ticket, price):
    """The judgment of the full path at b, by the definition (None = holds): a ticket of that symbol and side at a
    step not below the ticket's, and for a buy the ticket's quantity within G2b (when set) and G4 at b x mult."""
    symbol, side = ticket["ticker"], ticket["side"]
    mine = [item for item in result["planned"]["tickets"] if item["ticker"] == symbol and item["side"] == side]
    if not mine:
        reasons = [reason for item in result["planned"]["blocked"] if item["symbol"] == symbol and item["side"] == side
                   for reason in item["reasons"] if reason != "CARD_TRIM_SIZE_MISSING"]
        return "NO_TICKET:" + (reasons[0] if reasons else "CIRCUIT_CLOSED")
    if Fraction(mine[0]["evidence"]["r"]) < Fraction(ticket["evidence"]["r"]):
        return "STEP_DOWN"
    if side == "buy":
        shown = (price * Decimal(str(ticket["priceCalc"]["mult"]))).quantize(CENT, rounding=ROUND_FLOOR)
        pct = probe.ctx["config"].get("max_buy_ticket_pct_of_equity")
        if pct is not None and math.floor(probe.ctx["equity"] * Decimal(str(pct)) / shown) < ticket["qty"]:
            return "G2B"
        if math.floor(probe.ctx["cash"] / (shown * Decimal("1.0025"))) < ticket["qty"]:
            return "CASH"
    return None


def cents(start, end):
    price = start
    while price <= end:
        yield price
        price += CENT


class E4Mixin:
    def assert_full_path(self, probe, symbol, side):
        """H2 (E4): at every cent of the band the scan's judgment is the full path's, and hold is the largest run
        from the reference on which it holds."""
        ticket = only(probe.result, symbol, side)
        hold, band = ticket["priceCalc"]["hold"], ticket["priceCalc"]["band"]
        band_lo, band_hi = Decimal(str(band["lo"])), Decimal(str(band["hi"]))
        reference = probe.ctx["closes"][symbol]
        codes, self.proposal_changes = {}, 0
        for price in cents(band_lo, band_hi):
            result, proposals = probe.full(symbol, price)
            codes[price] = full_code(probe, result, ticket, price)
            self.assertEqual(tk._hold_break(probe.ctx, ticket, price), codes[price], (symbol, side, str(price)))
            if proposals != probe.proposals:
                self.proposal_changes += 1
                # The proposal list follows that symbol's new_basis_met (basis_met for the supplement ETF): only
                # its own proposals may differ, and then neither path has its ticket.
                changed = [item for item in proposals if item not in probe.proposals] + [
                    item for item in probe.proposals if item not in proposals]
                self.assertEqual({item["symbol"] for item in changed}, {symbol}, str(price))
                self.assertTrue(codes[price].startswith("NO_TICKET:"), (str(price), codes[price]))
                self.assertIsNone(tk._hold_ticket(probe.ctx, ticket, price)[0], str(price))
        # The full path at the reference gives the ticket itself (all but band and hold).
        at_reference, _ = probe.full(symbol, reference)
        mine = [item for item in at_reference["planned"]["tickets"] if item["ticker"] == symbol and item["side"] == side]
        self.assertEqual(mine, [revert_hold_view(ticket)])
        # hold = the largest unbroken run from the reference (scan starts: the cent above / below it).
        start_up = (reference * 100).to_integral_value(rounding="ROUND_FLOOR") + 1
        start_down = (reference * 100).to_integral_value(rounding="ROUND_CEILING") - 1

        def run(first, step, inside):
            last, price = reference, first / 100
            while inside(price):
                if codes[price] is not None:
                    return last, codes[price]
                last, price = price, price + step
            return last, "BAND"
        high, high_limit = run(start_up, CENT, lambda price: price <= band_hi)
        low, low_limit = run(start_down, -CENT, lambda price: price >= band_lo)
        self.assertEqual((hold["status"], hold["lo"], hold["hi"], hold["lo_limit"], hold["hi_limit"]),
                         ("ok", float(low), float(high), low_limit, high_limit))
        return codes


class BasicTests(unittest.TestCase):  # H1
    def assert_basic(self, scenario, symbol, side, cash=None):
        on = run_scenario(scenario, hold=True, cash=cash)
        off = run_scenario(scenario, hold=False, cash=cash)
        ticket, before = only(on, symbol, side), only(off, symbol, side)
        calc, hold = ticket["priceCalc"], ticket["priceCalc"]["hold"]
        self.assertNotIn("band", before["priceCalc"])
        self.assertNotIn("hold", before["priceCalc"])
        self.assertEqual(calc["band"], {"lo": before["priceCalc"]["lo"], "hi": before["priceCalc"]["hi"]})
        self.assertEqual((hold["status"], hold["reason"], hold["basis"]), ("ok", None, "SYMBOL_CLOSE_ONLY:S7_FIXED"))
        self.assertTrue(calc["band"]["lo"] <= hold["lo"] <= ticket["ref"]["price"] <= hold["hi"] <= calc["band"]["hi"])
        expected = (hold["lo"], hold["hi"]) if side == "buy" else (calc["band"]["lo"], calc["band"]["hi"])
        self.assertEqual((calc["lo"], calc["hi"]), expected)
        # E2: nothing else in the ticket, the plan or the record changes.
        self.assertEqual(revert_hold_view(ticket), before)
        self.assertEqual(revert_hold_view(on["planned"]), off["planned"])
        for key in ("symbols", "evidence", "rows", "s7", "nominal", "account", "exposure", "shock", "shocks",
                    "facts_seen", "gate1", "proposal_results", "buy_session"):
            self.assertEqual(on[key], off[key], key)
        return ticket, on

    def test_buy_and_sell(self):
        buy, _ = self.assert_basic(tickets_tests.Scenario(), "MU", "buy")
        self.assertEqual((buy["priceCalc"]["hold"]["lo_limit"], buy["priceCalc"]["hold"]["hi_limit"]), ("BAND", "BAND"))
        sell, _ = self.assert_basic(risk1r._scenarios()["sell"], "SOXL", "sell")
        self.assertEqual(sell["priceCalc"]["hold"]["checked"], 173)  # the reference and 172 band cents

    def test_reference_between_cents(self):
        # 208.615: the lower cent 208.61 is MU's own -2 sigma60 day (EV5), the reference and 208.62 are not.
        calls = []
        scenario = ev5_scenario(208.615)
        on = run_scenario(scenario, hold=True, plan=recording_plan(calls))
        ticket = only(on, "MU", "buy")
        hold, band = ticket["priceCalc"]["hold"], ticket["priceCalc"]["band"]
        self.assertEqual(ticket["ref"]["price"], 208.615)
        self.assertEqual(hold["status"], "ok")
        self.assertEqual(calls[:2], [Decimal("208.615"), Decimal("208.62")])  # self-check, then the cent above
        self.assertEqual(calls[-1], Decimal("208.61"))  # the cent below breaks at once
        self.assertEqual((hold["lo"], hold["lo_limit"]), (208.615, "NO_TICKET:REQ5_RREC1:no"))
        self.assertEqual((hold["hi"], hold["hi_limit"]), (band["hi"], "BAND"))
        self.assertEqual(hold["checked"], len(calls))
        self.assertEqual((ticket["priceCalc"]["lo"], ticket["priceCalc"]["hi"]), (208.615, band["hi"]))
        self.assertEqual(revert_hold_view(ticket), only(run_scenario(scenario, hold=False), "MU", "buy"))


class FullPathTests(E4Mixin, unittest.TestCase):  # H2
    def test_h1_buy(self):
        self.assert_full_path(Probe(tickets_tests.Scenario()), "MU", "buy")

    def test_h1_sell(self):
        self.assert_full_path(Probe(risk1r._scenarios()["sell"]), "SOXL", "sell")

    def test_h1_reference_between_cents(self):
        self.assert_full_path(Probe(ev5_scenario(208.615)), "MU", "buy")

    def test_h3_buy_boundary(self):
        self.assert_full_path(Probe(ev5_scenario(209.0)), "MU", "buy")

    def test_h4_cash(self):
        self.assert_full_path(Probe(tickets_tests.Scenario(), cash="6146.00"), "MU", "buy")

    def test_h4_g2b(self):
        self.assert_full_path(Probe(G2bTests.scenario()), "MU", "buy")

    def test_h5_sell(self):
        self.assert_full_path(Probe(narrow_sell_scenario()), "SOXL", "sell")

    def test_supplement_proposals_change_with_the_close(self):
        # SOXL (the S7 supplement, reduce_order[-1]) bought on two new + cues: below 100.10 its evidence no longer
        # meets the basis, so the full path makes no SOXL proposal and neither path has a SOXL ticket.
        scenario = tickets_tests.Scenario()
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.soxl_two_new_cues())
        probe = Probe(scenario)
        self.assert_full_path(probe, "SOXL", "buy")
        self.assertGreater(self.proposal_changes, 0)  # the branch above was exercised
        hold = only(probe.result, "SOXL", "buy")["priceCalc"]["hold"]
        self.assertEqual((hold["lo"], hold["lo_limit"]), (100.1, "NO_TICKET:CIRCUIT_CLOSED"))


class BuyBoundaryTests(unittest.TestCase):  # H3
    def test_own_minus_two_sigma_day_stops_the_range_inside_the_band(self):
        ticket = only(run_scenario(ev5_scenario(209.0), hold=True), "MU", "buy")
        hold, band, calc = ticket["priceCalc"]["hold"], ticket["priceCalc"]["band"], ticket["priceCalc"]
        self.assertEqual((band["lo"], band["hi"]), (206.91, 211.09))
        # 208.61 and below: MU's 1-day return <= -2 sigma60 (EV5) -> R-REC1 open, RG1 not met -> requirement (5) no.
        self.assertEqual((hold["lo"], hold["lo_limit"]), (208.62, "NO_TICKET:REQ5_RREC1:no"))
        self.assertEqual((hold["hi"], hold["hi_limit"]), (211.09, "BAND"))
        self.assertGreater(calc["lo"], band["lo"])  # the screen blocks a Kiwoom reference close below 208.62
        self.assertEqual((calc["lo"], calc["hi"]), (208.62, 211.09))
        closes = helpers.zigzag(len(DAYS), 200, 3.0, 0.2)[:-1]
        for price, event in ((208.61, True), (208.62, False)):
            series = rules.build_series(helpers.bars("MU", DAYS, closes + [price])["adjusted"],
                                        tickets_tests.CALENDAR_DAYS, LAST)
            self.assertEqual(series["ret1"][-1] <= -rules.C["RREC_EV5_SIGMA"] * series["sigma60"][-1], event, price)


class CashTests(unittest.TestCase):  # H4
    def test_cash_just_above_the_ticket_stops_hi_at_the_hand_computed_cent(self):
        # qty 28 at 218.86 (215.80 x 1.0142, cent down) needs 28 x 218.86 x 1.0025 = 6143.40; cash 6146.00.
        # 215.89 x 1.0142 = 218.955638 -> 218.95: floor(6146 / (218.95 x 1.0025)) = floor(28.0003) = 28 (holds);
        # 215.90 x 1.0142 = 218.96578 -> 218.96: floor(6146 / (218.96 x 1.0025)) = floor(27.9990) = 27 (CASH).
        ticket = only(run_scenario(tickets_tests.Scenario(), hold=True, cash="6146.00"), "MU", "buy")
        hold = ticket["priceCalc"]["hold"]
        self.assertEqual((ticket["qty"], ticket["price"], ticket["priceCalc"]["mult"], ticket["gates"]["G4"]),
                         (28, 218.86, 1.0142, "ok"))
        self.assertEqual((hold["hi"], hold["hi_limit"]), (215.89, "CASH"))
        self.assertEqual((hold["lo"], hold["lo_limit"]), (ticket["priceCalc"]["band"]["lo"], "BAND"))
        self.assertLess(hold["hi"], ticket["priceCalc"]["band"]["hi"])
        self.assertEqual((ticket["priceCalc"]["lo"], ticket["priceCalc"]["hi"]), (hold["lo"], 215.89))
        for price, shares in (("215.89", 28), ("215.90", 27)):
            shown = (Decimal(price) * Decimal("1.0142")).quantize(CENT, rounding=ROUND_FLOOR)
            self.assertEqual(math.floor(Decimal("6146.00") / (shown * Decimal("1.0025"))), shares)


class G2bTests(unittest.TestCase):  # H4 (G2b, when max_buy_ticket_pct_of_equity is set)
    @staticmethod
    def scenario():
        review = run_scenario(tickets_tests.Scenario(), hold=False)["review"]
        equity = Decimal(str(review["equity"]["closing_equity_usd"]))
        # The cap allows 28 shares up to a screen price of 218.95 (the same cent as the cash test): pct = 6130.65 / E.
        return tickets_tests.Scenario(config={"max_buy_ticket_pct_of_equity": float(round(Decimal("6130.65") / equity, 10))})

    def test_g2b_cap_stops_hi(self):
        ticket = only(run_scenario(self.scenario(), hold=True), "MU", "buy")
        hold = ticket["priceCalc"]["hold"]
        self.assertEqual(ticket["qty"], 28)
        self.assertEqual((hold["hi"], hold["hi_limit"]), (215.89, "G2B"))


class SellWarningTests(unittest.TestCase):  # H5
    def test_narrower_sell_range_keeps_the_band_and_the_ticket(self):
        scenario = narrow_sell_scenario()
        ticket = only(run_scenario(scenario, hold=True), "SOXL", "sell")
        before = only(run_scenario(scenario, hold=False), "SOXL", "sell")
        hold, band = ticket["priceCalc"]["hold"], ticket["priceCalc"]["band"]
        prefix_ema10 = rules.ema_series(sell_prefix(), rules.C["EMA_SHORT"])[-1]
        self.assertEqual(ticket["ref"]["price"], round(prefix_ema10 - 0.2, 2))
        self.assertEqual((hold["status"], hold["hi_limit"]), ("ok", "NO_TICKET:CIRCUIT_CLOSED"))
        self.assertEqual(hold["hi"], math.floor(prefix_ema10 * 100) / 100)  # the last cent under that EMA10
        self.assertLess(hold["hi"], band["hi"])
        self.assertEqual((ticket["priceCalc"]["lo"], ticket["priceCalc"]["hi"]), (band["lo"], band["hi"]))
        self.assertEqual(revert_hold_view(ticket), before)


class UnverifiedTests(unittest.TestCase):  # H6
    @staticmethod
    def shifted(real):
        """A wrong hold_eval: the symbol's reference one cent off (the recomputed ticket differs at the reference)."""
        def wrong(symbol, price):
            view = real(symbol, price)
            return {**view, "closes": {**view["closes"], symbol: view["closes"][symbol] + CENT}}
        return wrong

    @staticmethod
    def failing(when):
        def make(real):
            def hold_eval(symbol, price):
                if when(price):
                    raise ValueError("TEST_ONLY")
                return real(symbol, price)
            return hold_eval
        return make

    @staticmethod
    def missing(when):
        def make(real):
            return lambda symbol, price: None if when(price) else real(symbol, price)
        return make

    def test_wrong_hold_eval_drops_the_buy_and_keeps_the_rest(self):
        scenario = tickets_tests.Scenario()
        on = run_scenario(scenario, hold=True, plan=recording_plan([], self.shifted))
        off = run_scenario(scenario, hold=False)
        self.assertEqual(tickets_tests.tickets_of(on, "MU", "buy"), [])
        self.assertEqual(on["planned"]["blocked"], off["planned"]["blocked"] + [
            {"symbol": "MU", "side": "buy", "reasons": ["HOLD_RANGE_UNVERIFIED"]}])
        self.assertEqual(on["planned"]["candidates"], off["planned"]["candidates"])
        self.assertEqual(on["planned"]["no_action"], {"value": True, "reasons": ["HOLD_RANGE_UNVERIFIED"]})
        self.assertNotIn("HOLD_RANGE_UNVERIFIED", tk.ALLOWED_NO_TICKET)  # an anomaly, not an allowed reason

    def test_wrong_hold_eval_keeps_the_sell(self):
        scenario = risk1r._scenarios()["sell"]
        ticket = only(run_scenario(scenario, hold=True, plan=recording_plan([], self.shifted)), "SOXL", "sell")
        hold, band = ticket["priceCalc"]["hold"], ticket["priceCalc"]["band"]
        self.assertEqual(hold, {"status": "unverified", "lo": None, "hi": None, "lo_limit": None, "hi_limit": None,
                                "checked": 1, "reason": "SELF_CHECK_MISMATCH", "basis": "SYMBOL_CLOSE_ONLY:S7_FIXED"})
        self.assertEqual((ticket["priceCalc"]["lo"], ticket["priceCalc"]["hi"]), (band["lo"], band["hi"]))
        self.assertEqual(revert_hold_view(ticket), only(run_scenario(scenario, hold=False), "SOXL", "sell"))
        self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])

    def test_errors_and_missing_bars_during_the_scan_are_data(self):
        reference = Decimal("215.8")
        raised = only(run_scenario(tickets_tests.Scenario(), hold=True,
                                   plan=recording_plan([], self.failing(lambda price: price > reference + 5 * CENT))),
                      "MU", "buy")["priceCalc"]["hold"]
        self.assertEqual((raised["status"], raised["hi"], raised["hi_limit"], raised["lo_limit"]),
                         ("ok", 215.85, "DATA", "BAND"))
        gone = only(run_scenario(tickets_tests.Scenario(), hold=True,
                                 plan=recording_plan([], self.missing(lambda price: price < reference - 3 * CENT))),
                    "MU", "buy")["priceCalc"]["hold"]
        self.assertEqual((gone["status"], gone["lo"], gone["lo_limit"], gone["hi_limit"]), ("ok", 215.77, "DATA", "BAND"))

    def test_errors_at_the_reference_are_unverified(self):
        for make, reason in ((self.failing(lambda price: True), "EVAL_ERROR:ValueError"),
                             (self.missing(lambda price: True), "DATA")):
            with self.subTest(reason=reason):
                sell = only(run_scenario(risk1r._scenarios()["sell"], hold=True, plan=recording_plan([], make)),
                            "SOXL", "sell")["priceCalc"]["hold"]
                self.assertEqual((sell["status"], sell["reason"], sell["checked"]), ("unverified", reason, 1))
                buy = run_scenario(tickets_tests.Scenario(), hold=True, plan=recording_plan([], make))
                self.assertEqual(tickets_tests.tickets_of(buy, "MU", "buy"), [])
                self.assertIn("HOLD_RANGE_UNVERIFIED", tickets_tests.blocked_reasons(buy, "MU", "buy"))

    def test_decide_goes_on_when_the_reference_raises(self):
        with mock.patch.object(tk, "plan", recording_plan([], self.failing(lambda price: True))):
            decision, _entries = risk1r._decide("compare")
        self.assertIn(decision["status"], ("OK", "HOLD"), decision["reasons"])
        self.assertEqual(decision["tickets"], [])
        self.assertIn({"symbol": "MU", "side": "buy", "reasons": ["HOLD_RANGE_UNVERIFIED"]}, decision["blocked"])
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])


def base_plan(ctx):
    """tk.plan as it was before close-confirm e (base 3e753f3, auto_core_tickets.py 718-791), verbatim but for
    the tk. prefixes: the reference for the helper split (E1)."""
    symbols, checks = ctx["symbols"], ctx["checks"]
    review, s7 = ctx["review"], ctx["s7"]
    holdings, equity = ctx["holdings"], ctx["equity"]
    weights, closes, sigmas = ctx["weights"], ctx["closes"], ctx["sigmas"]
    config = ctx["config"]
    blocked = []
    candidates = []
    tickets = []
    global_reasons = list(ctx["gate0"]["reasons"]) + list(ctx["gate1"]["reasons"])
    reduce_items = {item["symbol"]: item for item in (review or {}).get("recommendations", {}).get("reduce") or []}
    add_symbols = {item["symbol"] for item in (review or {}).get("recommendations", {}).get("add") or []}
    if ctx.get("redeploy_ranked") is not None:
        selling = {symbol for symbol in holdings if tk._sell_gap_sources(checks, symbol, reduce_items)[0]
                   and ctx["evidence"][symbol]["sell"]["basis_met"]}
        ctx["redeploy_candidate"] = next((dict(item) for item in ctx["redeploy_ranked"]
                                          if item["symbol"] not in selling), None)
    for symbol in sorted(holdings):
        check = checks.get(symbol) or {}
        evidence = ctx["evidence"][symbol]["sell"]
        gap_sources, trim_missing = tk._sell_gap_sources(checks, symbol, reduce_items)
        if trim_missing:
            blocked.append({"symbol": symbol, "side": "sell", "reasons": ["CARD_TRIM_SIZE_MISSING"]})
        if not gap_sources or not evidence["basis_met"]:
            continue
        source, target = min(gap_sources, key=lambda item: item[1])
        candidates.append({"symbol": symbol, "side": "sell", "gap_source": source, "target_weight": float(target)})
        reasons = list(global_reasons) + list(check.get("reasons") or []) + ctx["data_reasons"].get(symbol, [])
        ticket = tk._sell_ticket(ctx, symbol, source, target, evidence, check, reasons, blocked)
        if ticket:
            tickets.append(ticket)
    for row in ctx["buy_rows"]:
        symbol = row["code"]
        evidence = ctx["evidence"][symbol]["buy"]
        opened = evidence["new_basis_met"] or (symbol in add_symbols and evidence["basis_met"])
        if not opened:
            continue
        candidates.append({"symbol": symbol, "side": "buy", "trigger": "NEW_EVIDENCE" if evidence["new_basis_met"]
                           else "S7_ADD_RECOMMENDATION"})
        research = [f"RESEARCH_RECORD_NOT_OK:{ctx['research_block']}"] if ctx["research_block"] is not None else []
        reasons = list(global_reasons) + research + list((checks.get(symbol) or {}).get("reasons") or []) + \
            ctx["data_reasons"].get(symbol, [])
        ticket = tk._buy_ticket(ctx, symbol, row, evidence, reasons, blocked)
        if ticket:
            tickets.append(ticket)
    tickets = tk._limit_daily(tickets, config, blocked)
    reduce_plan = list((review or {}).get("recommendations", {}).get("reduce") or [])
    sells = [ticket for ticket in tickets if ticket["side"] == "sell"]
    for ticket in sells:
        line = tk.plan_premise(ticket, reduce_plan, sells, blocked, candidates)
        ticket["gap"]["plan_premise"] = line
        ticket["after_sale"]["plan_premise"] = line
    for index, ticket in enumerate(sorted(tickets, key=lambda item: (item["side"] != "sell", item["ticker"]))):
        ticket["ticket_id"] = f"AT-{ctx['run_day'].replace('-', '')}-{ticket['ticker']}-{index + 1}"
    no_action = not tickets
    top = []
    for item in blocked:
        for reason in item["reasons"]:
            if reason not in top:
                top.append(reason)
    if not candidates:
        top = ["NO_CIRCUIT_OPEN"]
    return {"candidates": candidates, "tickets": tickets, "blocked": blocked,
            "no_action": {"value": no_action, "reasons": top[:5] if no_action else []}}


class HoldOffTests(unittest.TestCase):  # H7 (E1)
    KEYS = ("default", "g2b", "cash5", "research_block", "sell", "pwr")

    def test_default_off_keeps_the_six_golden_keys(self):
        results = {name: item.run() for name, item in risk1r._scenarios().items()}
        measured = {name: risk1r._digest(risk1r._plan_view(result["planned"])) for name, result in results.items()}
        self.assertEqual(sorted(measured), sorted(self.KEYS))
        self.assertEqual(measured, {key: risk1r.GOLDEN[key] for key in self.KEYS})
        for result in results.values():
            for ticket in result["planned"]["tickets"]:
                self.assertNotIn("band", ticket["priceCalc"])
                self.assertNotIn("hold", ticket["priceCalc"])

    def test_the_helper_split_gives_the_base_plan(self):
        scenarios = {**risk1r._scenarios(), "narrow_sell": narrow_sell_scenario(), "ev5": ev5_scenario(209.0),
                     "trim_missing": tickets_tests.Scenario(holdings={"SOXL": 120}, cash="300",
                                                            soxl_entry=helpers.entry("SOXL", role="holding",
                                                                                     action="TRIM"))}
        for name, scenario in scenarios.items():
            with self.subTest(name=name):
                with mock.patch.object(tk, "plan", base_plan):
                    old = scenario.run()
                new = scenario.run()
                self.assertEqual(new["planned"], old["planned"])
                self.assertEqual(new["rows"], old["rows"])

    def test_the_replay_passes_no_hold_range(self):
        import inspect

        import auto_core_replay
        self.assertNotIn("hold_range", inspect.getsource(auto_core_replay))
        self.assertIs(inspect.signature(decide_module.evaluate_session).parameters["hold_range"].default, False)


class OutcomeTests(unittest.TestCase):  # H8 (E3)
    BUY, SELL = tickets_tests.BUY, tickets_tests.SELL  # ust21150 slby_tp_nm (Korean side names)

    @staticmethod
    def pair(side):
        calc = {"mult": 1.0142, "round": "down", "lo": 215.0, "hi": 215.89, "label": "TEST_ONLY",
                "band": {"lo": 213.64, "hi": 217.96},
                "hold": {"status": "ok", "lo": 215.0, "hi": 215.89, "lo_limit": "STEP_DOWN", "hi_limit": "CASH",
                         "checked": 90, "reason": None, "basis": "SYMBOL_CLOSE_ONLY:S7_FIXED"}}
        if side == "sell":
            calc.update(mult=0.98, round="up", lo=213.64, hi=217.96)
        new = {"ticket_id": "AT-20261010-MU-1", "ticker": "MU", "side": side, "qty": 28, "price": 218.86,
               "decision_key": "a" * 64, "mode": "apply", "priceCalc": calc}
        old = {**new, "priceCalc": {key: value for key, value in calc.items() if key not in ("band", "hold")}}
        old["priceCalc"].update(lo=213.64, hi=217.96)
        return new, old

    def test_classification_keeps_the_band(self):
        for side in ("buy", "sell"):
            new, old = self.pair(side)
            name = self.BUY if side == "buy" else self.SELL
            cases = {
                "inside_hold": [helpers.fill_row("MU", name, ordered=28, filled=28, price="218.86")],
                "inside_band_outside_hold": [helpers.fill_row("MU", name, ordered=28, filled=28, price="220.50")],
                "outside_band": [helpers.fill_row("MU", name, ordered=28, filled=28, price="222.00")],
                "below_band": [helpers.fill_row("MU", name, ordered=28, filled=28, price="200.00")],
                "partial": [helpers.fill_row("MU", name, ordered=28, filled=10, price="219.00")],
                "unfilled": [helpers.fill_row("MU", name, ordered=28, filled=0, price="219.00")],
                "cancelled": [helpers.fill_row("MU", name, ordered=28, filled=0, price="219.00", cancelled=28)],
                "not_loc": [helpers.fill_row("MU", name, ordered=28, filled=28, price="219.00", kind="Limit")],
                "not_entered": [],
            }
            for case, rows in cases.items():
                with self.subTest(side=side, case=case):
                    self.assertEqual(tk.classify_outcome(new, rows), tk.classify_outcome(old, rows))
            if side == "buy":
                # 220.50 is inside the band (216.67-221.06 at mult 1.0142) though outside the hold range: as the ticket.
                self.assertEqual(tk.classify_outcome(new, cases["inside_band_outside_hold"])["state"], "filled")
                self.assertEqual(tk.classify_outcome(new, cases["outside_band"])["state"], "changed")


class DeterminismTests(unittest.TestCase):  # H9 (E6, E7)
    def test_same_inputs_same_hold_and_nothing_changed(self):
        for scenario, symbol, side in ((tickets_tests.Scenario(), "MU", "buy"), (narrow_sell_scenario(), "SOXL", "sell"),
                                       (ev5_scenario(208.615), "MU", "buy")):
            with self.subTest(symbol=symbol, side=side):
                bars_before = copy.deepcopy(scenario.bars)
                same_object = {name: item["raw"] is item["adjusted"] for name, item in scenario.bars.items()}
                snapshots = {}

                def plan(ctx):
                    snapshots["before"] = copy.deepcopy(ctx)
                    out = ORIGINAL_PLAN(ctx)
                    snapshots["after"] = copy.deepcopy(ctx)
                    snapshots["ctx"] = ctx
                    return out
                first = run_scenario(scenario, hold=True, plan=plan)
                self.assertEqual(scenario.bars, bars_before)
                self.assertEqual({name: item["raw"] is item["adjusted"] for name, item in scenario.bars.items()},
                                 same_object)
                ctx = snapshots["ctx"]
                # plan() sets the redeployment candidate as before; the range computation changes nothing else.
                before = {key: value for key, value in snapshots["before"].items() if key != "redeploy_candidate"}
                after = {key: value for key, value in snapshots["after"].items() if key != "redeploy_candidate"}
                self.assertEqual(after, before)
                ticket = only(first, symbol, side)
                review_before = copy.deepcopy(ctx["review"])
                # The ticket as plan() had it when the range was computed: lo-hi = band, no compare-mode note.
                pre = {key: value for key, value in revert_hold_view(ticket).items() if key != "note"}
                again = tk.hold_range(ctx, pre)
                self.assertEqual(again, ticket["priceCalc"]["hold"])
                self.assertEqual(ctx["review"], review_before)
                self.assertEqual(snapshots["after"], copy.deepcopy(ctx))
                self.assertEqual(scenario.bars, bars_before)
                second = run_scenario(scenario, hold=True)
                self.assertEqual(second["planned"], first["planned"])

    def test_bars_copy_leaves_the_input(self):
        item = helpers.bars("MU", DAYS, helpers.zigzag(len(DAYS), 20, 0.3, 0.02))
        before = copy.deepcopy(item)
        moved = decide_module._bars_with_close(item, LAST, Decimal("20.05"))
        self.assertEqual(item, before)
        self.assertIs(moved["raw"], moved["adjusted"])  # one copy when raw and adjusted are the same object
        bar = moved["raw"]["sessions"][LAST]
        self.assertEqual(bar["close"], Decimal("20.05"))
        self.assertEqual(bar["high"], max(item["raw"]["sessions"][LAST]["high"], Decimal("20.05")))
        self.assertEqual(bar["low"], min(item["raw"]["sessions"][LAST]["low"], Decimal("20.05")))
        self.assertEqual({day: value for day, value in moved["raw"]["sessions"].items() if day != LAST},
                         {day: value for day, value in item["raw"]["sessions"].items() if day != LAST})
        # Separate adjusted bars (a load_symbol result with status OK): both get the close.
        split = {**item, "adjusted": copy.deepcopy(item["raw"])}
        moved = decide_module._bars_with_close(split, LAST, Decimal("20.05"))
        self.assertEqual(moved["adjusted"]["sessions"][LAST]["close"], Decimal("20.05"))
        self.assertIsNot(moved["adjusted"], moved["raw"])
        # Cannot be built: not OK, no such session, raw and adjusted closes differ (a split reaching the session).
        self.assertIsNone(decide_module._bars_with_close(helpers.missing_bars("MU"), LAST, Decimal("20.05")))
        self.assertIsNone(decide_module._bars_with_close(item, "2030-01-01", Decimal("20.05")))
        split["adjusted"]["sessions"][LAST] = {**split["adjusted"]["sessions"][LAST], "close": Decimal("10")}
        self.assertIsNone(decide_module._bars_with_close(split, LAST, Decimal("20.05")))
        incomplete = helpers.bars("MU", DAYS, helpers.zigzag(len(DAYS), 20, 0.3, 0.02), incomplete={LAST})
        bar = decide_module._bars_with_close(incomplete, LAST, Decimal("20.05"))["raw"]["sessions"][LAST]
        self.assertEqual((bar["high"], bar["low"], bar["close"]), (None, None, Decimal("20.05")))


class SchemaTests(unittest.TestCase):  # H10
    def test_tickets_and_decisions_are_valid(self):
        buy = only(run_scenario(tickets_tests.Scenario(), hold=True), "MU", "buy")
        sell = only(run_scenario(narrow_sell_scenario(), hold=True), "SOXL", "sell")
        unverified = only(run_scenario(risk1r._scenarios()["sell"], hold=True,
                                       plan=recording_plan([], UnverifiedTests.shifted)), "SOXL", "sell")
        old = only(run_scenario(tickets_tests.Scenario(), hold=False), "MU", "buy")
        for ticket in (buy, sell, unverified, old):
            self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [], ticket["priceCalc"])
        self.assertEqual(unverified["priceCalc"]["hold"]["status"], "unverified")
        broken = copy.deepcopy(buy)
        broken["priceCalc"]["hold"]["extra"] = 1
        self.assertTrue(validate_instance(broken, TICKET_SCHEMA))
        for mode in ("compare", "apply"):
            decision = risk1r._decide(mode)[0]
            self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
            self.assertTrue(decision["tickets"])
            for ticket in decision["tickets"]:
                self.assertEqual(ticket["priceCalc"]["hold"]["status"], "ok")


class HoldCauseTests(unittest.TestCase):  # H11
    """decide twice in one process: hold_range forced False, then as decide passes it (True)."""

    @staticmethod
    def decide(mode, hold):
        if hold:
            return risk1r._decide(mode)[0]
        with mock.patch.object(decide_module, "evaluate_session",
                               lambda **kw: ORIGINAL_EVALUATE(**{**kw, "hold_range": False})):
            return risk1r._decide(mode)[0]

    @staticmethod
    def golden_view(decision):
        return {"tickets": [risk1r._strip(ticket) for ticket in decision["tickets"]], "blocked": decision["blocked"],
                "no_action": decision["no_action"], "keys": decision["keys"]}

    def test_only_price_calc_changes(self):
        for mode in ("compare", "apply"):
            with self.subTest(mode=mode):
                off, on = self.decide(mode, False), self.decide(mode, True)
                self.assertTrue(off["tickets"])
                for ticket in off["tickets"] + [order for order in off["dashboard"]["orders"]]:
                    self.assertNotIn("band", ticket["priceCalc"])
                    self.assertNotIn("hold", ticket["priceCalc"])
                for ticket in on["tickets"]:
                    self.assertEqual(ticket["priceCalc"]["hold"]["status"], "ok")
                self.assertNotEqual(on["tickets"], off["tickets"])
                view_off = {key: off.get(key) for key in DECISION_VIEW_KEYS}
                view_on = {key: on.get(key) for key in DECISION_VIEW_KEYS}
                self.assertEqual(revert_hold_view(view_on), view_off)
                self.assertEqual(revert_hold_view(self.golden_view(on)), self.golden_view(off))
                journal_off = {key: value for key, value in off["journal"].items() if key != "decision_sha256"}
                journal_on = {key: value for key, value in on["journal"].items() if key != "decision_sha256"}
                self.assertEqual(journal_on, journal_off)
                if mode == "apply":
                    self.assertTrue(on["dashboard"]["orders"])
                    self.assertEqual([order["priceCalc"] for order in on["dashboard"]["orders"]],
                                     [ticket["priceCalc"] for ticket in on["tickets"]])

    @unittest.skipUnless(sys.platform == "win32", "the decide_* hashes were measured on Windows (Linux differs)")
    def test_reverted_view_hashes_as_the_old_golden(self):
        measured = {f"decide_{mode}": risk1r._digest(revert_hold_view(self.golden_view(self.decide(mode, True))))
                    for mode in ("compare", "apply")}
        self.assertEqual(measured, OLD_DECIDE_GOLDEN)


if __name__ == "__main__":
    unittest.main()
