"""Redesign T2 F4-F6: requirements, gates, the ticket calculator (golden G-1..G-3) and outcome classification.

Synthetic inputs (TEST_ONLY) except G-3, which uses the copied approximate closes in
tests/fixtures/auto_core_t2/g3-closes-2026-10-08.json (no account data).
"""

from __future__ import annotations

import copy
import inspect
import json
import math
import sys
import unittest
from datetime import date, datetime, time, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import auto_core_tickets as tk  # noqa: E402
import helpers  # noqa: E402
from corporate_actions import adjust_closes, applicable_actions, validate_corporate_actions  # noqa: E402
from portfolio_exposure import (  # noqa: E402
    ExposureModel, build_exposure_review, closing_equity, effective_exposure, exposure_config,
)
from validation_common import validate_instance  # noqa: E402

SELL, BUY = "매도", "매수"
DAYS = helpers.sessions("2026-06-01", 95)
CALENDAR_DAYS = helpers.sessions("2026-06-01", 100)
LAST = DAYS[-1]
TICKET_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/auto-core-ticket.schema.json"


class GoldenTests(unittest.TestCase):
    def test_g1_mvll_regret_table_gives_118_shares(self):
        # Design section 5: gap 236, reference 37.65, equity 30,255.36, up +29.6%, down -26.1%, r_max 1/2.
        table = tk.regret_table(side="sell", delta=236, reference=Decimal("37.65"), up=0.296, down=-0.261,
                                equity=Decimal("30255.36"), worst_day=-0.208, sigma=0.0994)
        design = {"0": (0, 0, 2319), "1/3": (78, 869, 1553), "1/2": (118, 1315, 1160), "1": (236, 2630, 0)}
        self.assertEqual([row["r"] for row in table["rows"]], ["0", "1/3", "1/2", "1"])
        for row in table["rows"]:
            quantity, up, down = design[row["r"]]
            self.assertEqual(row["qty"], quantity)
            self.assertLessEqual(abs(row["regret"]["up:cash"] - up), 1.0)
            self.assertLessEqual(abs(row["regret"]["down:cash"] - down), 1.0)
        step, why = tk.choose_step(table, Fraction(1, 2))
        self.assertEqual((step, why), (Fraction(1, 2), "MINIMAX_REGRET"))
        self.assertEqual(tk.step_quantity(236, step), 118)
        # Tail: -20.8% is below the LOC floor (1 - sigma), so nothing fills: regret $1,848 (design 5).
        self.assertTrue(all(not row["loc_fills"] and abs(row["regret"] - 1848.15) < 1 for row in table["tail_rows"]))

    def test_g2_soxl_floor_and_cap_rounding(self):
        sell = tk.loc_price("sell", Decimal("142.45"), 0.0835)
        self.assertEqual(sell["price"], Decimal("130.56"))  # OI-20261009-SOXL-2 section 1
        self.assertEqual((sell["calc"]["mult"], sell["calc"]["round"]), (0.9165, "up"))
        self.assertEqual((sell["calc"]["lo"], sell["calc"]["hi"]), (141.03, 143.87))
        buy = tk.loc_price("buy", Decimal("142.45"), 0.0835)
        self.assertEqual((buy["calc"]["mult"], buy["calc"]["round"]), (1.0417, "down"))
        self.assertEqual(buy["price"], Decimal("148.39"))  # 142.45 x 1.0417 = 148.390165 -> cent down

    def test_g3_soxl_gap_from_the_s7_reduce_plan(self):
        fixture = json.loads((FIXTURES / "g3-closes-2026-10-08.json").read_text(encoding="utf-8"))
        sessions = fixture["calendar_sessions"]
        actions, errors = validate_corporate_actions(fixture["corporate_actions"], sessions)
        self.assertEqual(errors, [])
        corporate = {"status": "OK", "actions": actions, "errors": [], "sha256": None}
        holdings, cash, session = {"MVLL": 159, "SOXL": 75, "NBIS": 13}, Decimal("9395.20"), "2026-10-08"
        snapshots = [{"as_of": day, "state_revision": 1, "holdings": holdings, "cash_usd": str(cash),
                      "holdings_decreased": False, "cash_flow_declaration": None, "from_ledger_entry": True}
                     for day in sessions if "2026-10-01" <= day <= session]
        equity0, _values, _missing = closing_equity(snapshots[0], fixture["closes"], snapshots[0]["as_of"])
        review = build_exposure_review(
            policy=helpers.policy(), evaluation_session=session, calendar_sessions=sessions, snapshots=snapshots,
            snapshot_reasons=[], closes=fixture["closes"], close_unverified={},
            journal=helpers.activation_journal(equity0, snapshots[0]["as_of"]), corporate_actions=corporate,
            generated_at="2026-10-08T21:00:00Z", inputs={"generated_at": "2026-10-08T21:00:00Z"})
        self.assertAlmostEqual(review["exposure"]["effective"], 1.857, places=3)  # OI section 5: 1.857
        soxl = next(item for item in review["recommendations"]["reduce"] if item["symbol"] == "SOXL")
        equity = Decimal(review["equity"]["closing_equity_usd"])
        reference = Decimal(fixture["closes"]["SOXL"][session])
        delta = 75 - math.floor(Decimal(str(soxl["target_weight"])) * equity / reference)
        # S7 reduces MVLL's cap excess (0.210 -> 0.2) first, so SOXL's gap is 20 (projected E 1.5495), not the
        # OI's SOXL-only 22 (reported). Selling SOXL alone reproduces the OI's E: 22 -> 1.552, 23 -> 1.538.
        self.assertEqual((soxl["target_weight"], delta), (0.271, 20))
        self.assertLessEqual(soxl["projected_after_all_steps"]["projected_effective"], 1.55)
        config = exposure_config(helpers.policy())
        adjusted = adjust_closes(fixture["closes"], applicable_actions(actions, session))
        model = ExposureModel(config, adjusted, [day for day in sessions if day <= session], session, list(holdings))
        weights = {item["symbol"]: Decimal(str(item["weight"])) for item in review["positions"]}
        for quantity, expected in ((22, 1.552), (23, 1.538)):
            trial = dict(weights)
            trial["SOXL"] -= Decimal(quantity) * reference / equity
            self.assertAlmostEqual(effective_exposure(*model.parts(trial)), expected, places=3)


class StepAndRegretTests(unittest.TestCase):
    def test_within_budget_keeps_r_max(self):
        table = tk.regret_table(side="buy", delta=10, reference=Decimal("100"), up=0.02, down=-0.02,
                                equity=Decimal("100000"))
        self.assertEqual(tk.choose_step(table, Fraction(1)), (Fraction(1), "WITHIN_REGRET_BUDGET"))

    def test_never_above_r_max(self):
        table = tk.regret_table(side="buy", delta=1000, reference=Decimal("100"), up=0.3, down=-0.01,
                                equity=Decimal("10000"))
        step, _why = tk.choose_step(table, Fraction(1, 3))
        self.assertLessEqual(step, Fraction(1, 3))
        self.assertEqual(tk.choose_step(table, Fraction(0)), (Fraction(0), "R_MAX_ZERO"))

    def test_sell_regret_uses_the_redeployment_bridge(self):
        table = tk.regret_table(side="sell", delta=30, reference=Decimal("100"), up=0.1, down=-0.1,
                                equity=Decimal("20000"), candidate={"symbol": "MU", "up": 0.2, "down": -0.05})
        self.assertEqual(table["columns"], ["up:cash", "down:cash", "up:MU", "down:MU"])
        cash_only = tk.regret_table(side="sell", delta=30, reference=Decimal("100"), up=0.1, down=-0.1,
                                    equity=Decimal("20000"))
        self.assertEqual(cash_only["columns"], ["up:cash", "down:cash"])
        # Selling into a candidate that rises more than the holding: the "hold" step has regret on the up path.
        hold = next(row for row in table["rows"] if row["r"] == "0")
        self.assertGreater(hold["regret"]["up:MU"], 0)

    def test_scenarios_use_60_five_session_returns_and_need_65_closes(self):
        self.assertEqual(tk.scenarios([100.0] * 64)["status"], "unk")
        closes = helpers.zigzag(70, 100, 1.0, 0.1)
        scenario = tk.scenarios(closes)
        self.assertEqual((scenario["status"], scenario["returns_used"]), ("ok", 60))
        self.assertAlmostEqual(tk.quantile([1.0, 2.0, 3.0, 4.0], 0.9), 3.7)


class ReissueTests(unittest.TestCase):
    def outcome(self, state, filled=0, key="k" * 64, mode="apply"):
        return {"decision_key": key, "state": state, "filled_qty": filled, "mode": mode, "ticket_id": "AT-1",
                "price": 100.0}

    def test_unfilled_twice_closes_and_one_reissue_is_allowed(self):
        ledger = tk.update_keys({}, [self.outcome("unfilled")])
        self.assertFalse(ledger["k" * 64]["closed"])
        ledger = tk.update_keys(ledger, [self.outcome("unfilled")])
        self.assertEqual((ledger["k" * 64]["closed"], ledger["k" * 64]["closed_reason"]), (True, "UNFILLED_TWICE"))

    def test_not_entered_does_not_count_but_two_in_a_row_close(self):
        ledger = tk.update_keys({}, [self.outcome("not_entered")])
        self.assertEqual((ledger["k" * 64]["market_tests"], ledger["k" * 64]["closed"]), (0, False))
        ledger = tk.update_keys(ledger, [self.outcome("unfilled")])
        self.assertEqual(ledger["k" * 64]["consecutive_not_entered"], 0)
        ledger = tk.update_keys(ledger, [self.outcome("not_entered")])
        ledger = tk.update_keys(ledger, [self.outcome("not_entered")])
        self.assertEqual(ledger["k" * 64]["closed_reason"], "NOT_ENTERED_TWICE")

    def test_filled_ends_the_key_and_compare_outcomes_are_ignored(self):
        self.assertEqual(tk.update_keys({}, [self.outcome("partial", 3)])["k" * 64]["closed_reason"], "FILLED")
        self.assertEqual(tk.update_keys({}, [self.outcome("filled", 5, mode="compare")]), {})

    def test_decision_key_changes_with_new_evidence(self):
        first = tk.decision_key("MU", "buy", ["a", "b"], "0" * 64, "S7_TARGET")
        self.assertEqual(first, tk.decision_key("MU", "buy", ["b", "a"], "0" * 64, "S7_TARGET"))
        self.assertNotEqual(first, tk.decision_key("MU", "buy", ["a", "c"], "0" * 64, "S7_TARGET"))


class OutcomeTests(unittest.TestCase):
    TICKET = {"ticket_id": "AT-20261009-SOXL-1", "ticker": "SOXL", "side": "sell", "qty": 22, "price": 130.56,
              "decision_key": "k" * 64, "mode": "apply",
              "priceCalc": {"mult": 0.9165, "round": "up", "lo": 141.03, "hi": 143.87, "label": "TEST_ONLY"}}

    def classify(self, rows):
        return tk.classify_outcome(self.TICKET, rows)

    def test_five_states(self):
        self.assertEqual(self.classify([])["state"], "not_entered")
        filled = self.classify([helpers.fill_row("SOXL", SELL, ordered=22, filled=22, price="130.62",
                                                 fill_price="139.76")])
        self.assertEqual((filled["state"], filled["filled_qty"], filled["average_fill_price"]), ("filled", 22, 139.76))
        self.assertEqual(self.classify([helpers.fill_row("SOXL", SELL, ordered=22, filled=10, price="130.62",
                                                         fill_price="139.76")])["state"], "partial")
        self.assertEqual(self.classify([helpers.fill_row("SOXL", SELL, ordered=22, filled=0, price="130.62",
                                                         status="무효주문")])["state"], "unfilled")
        changed = self.classify([helpers.fill_row("SOXL", SELL, ordered=30, filled=30, price="130.62",
                                                  fill_price="139.00")])
        self.assertEqual((changed["state"], changed["filled_qty"]), ("changed", 30))
        self.assertEqual(self.classify([helpers.fill_row("SOXL", SELL, ordered=22, filled=22, price="130.62",
                                                         kind="Limit")])["state"], "changed")
        self.assertEqual(self.classify([helpers.fill_row("SOXL", SELL, ordered=22, filled=22, price="120.00")])["state"],
                         "changed")

    def test_other_symbol_or_side_is_not_entered(self):
        self.assertEqual(self.classify([helpers.fill_row("SOXL", BUY, ordered=22, filled=22, price="130.62")])["state"],
                         "not_entered")
        self.assertEqual(self.classify([helpers.fill_row("NBIS", SELL, ordered=22, filled=22, price="130.62")])["state"],
                         "not_entered")

    def test_unreadable_row_is_unknown(self):
        row = helpers.fill_row("SOXL", SELL, ordered=22, filled=22, price="130.62")
        row["cntr_qty"] = "x"
        self.assertEqual(self.classify([row])["state"], "unknown")

    def test_no_price_inference_path(self):
        # The classifier sees only the broker rows: no close, quote or reference price goes in.
        self.assertEqual(list(inspect.signature(tk.classify_outcome).parameters), ["ticket", "rows"])
        source = inspect.getsource(tk.classify_outcome)
        for word in ("close", "quote", "now_pric", "cur_prc"):
            self.assertNotIn(word, source)

    def test_reconcile_mismatch(self):
        outcome = self.classify([helpers.fill_row("SOXL", SELL, ordered=22, filled=22, price="130.62")])
        fills = [{"ticker": "SOXL", "side": "SELL", "quantity": 22, "session_date": "2026-10-09"}]
        self.assertFalse(tk.reconcile_mismatch(outcome, "2026-10-09", fills))
        self.assertTrue(tk.reconcile_mismatch(outcome, "2026-10-09", []))
        self.assertFalse(tk.reconcile_mismatch(outcome, "2026-10-09", None))


class OrderWindowTests(unittest.TestCase):
    """r3 R3-1/R3-2: when a ticket is classified, and which KST order days (ust21150 ord_dt) are read for it."""

    CALENDAR = helpers.calendar(helpers.sessions("2026-10-01", 70))  # summer and winter time, no holiday

    @staticmethod
    def ticket(issued, session):
        return {"ticket_id": "AT-TEST", "issued_day": issued, "session": session}

    def days(self, issued, session, calendar=None):
        return tk.order_days(self.ticket(issued, session), calendar or self.CALENDAR)

    def test_weekday_ticket_reads_its_issue_day_and_the_next(self):
        # 16:00 EDT = 05:00 KST the next day.
        self.assertEqual(self.days("2026-10-14", "2026-10-14"), ["2026-10-14", "2026-10-15"])

    def test_saturday_ticket_for_monday_reads_saturday_to_tuesday(self):
        self.assertEqual(self.days("2026-10-17", "2026-10-19"), ["2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20"])

    def test_winter_close_is_six_kst_the_next_day(self):
        # 16:00 EST = 06:00 KST the next day (from 11/2).
        self.assertEqual(self.days("2026-11-07", "2026-11-09"), ["2026-11-07", "2026-11-08", "2026-11-09", "2026-11-10"])

    def test_early_close_uses_the_calendar_close(self):
        calendar = copy.deepcopy(self.CALENDAR)
        row = calendar["sessions"]["2026-11-27"]
        row.update(core_close_at="2026-11-27T13:00:00-05:00", close_type="EARLY")  # 03:00 KST 11/28
        self.assertEqual(self.days("2026-11-27", "2026-11-27", calendar), ["2026-11-27", "2026-11-28"])
        self.assertEqual(self.days("2026-11-25", "2026-11-27", calendar),
                         ["2026-11-25", "2026-11-26", "2026-11-27", "2026-11-28"])
        # The calendar's close decides the last day (synthetic close before midnight KST).
        row["core_close_at"] = "2026-11-27T09:59:00-05:00"  # 23:59 KST 11/27
        self.assertEqual(self.days("2026-11-27", "2026-11-27", calendar), ["2026-11-27"])

    def test_unknown_window_fails_closed(self):
        self.assertIsNone(self.days("2026-10-17", "2026-10-18"))  # Sunday: not a calendar session
        self.assertIsNone(self.days("2026-10-21", "2026-10-19"))  # the session closed before the issue day

    def test_classified_only_after_the_session(self):
        ticket = self.ticket("2026-10-17", "2026-10-19")
        self.assertFalse(tk.ticket_session_ended(ticket, "2026-10-16"))
        self.assertTrue(tk.ticket_session_ended(ticket, "2026-10-19"))
        self.assertTrue(tk.ticket_session_ended(ticket, "2026-10-20"))


class OrderAttributionTests(unittest.TestCase):
    """r4 R4-1: an order row counts for one ticket only. Rows already attributed to a ticket are left out, and on
    the issue KST day only rows placed at or after the issue time count; the ledger keeps 30 calendar days."""

    TICKET = {"ticket_id": "AT-20261014-SOXL-1", "ticker": "SOXL", "side": "sell", "qty": 5,
              "issuedAt": "2026-10-14 07:45 KST", "issued_day": "2026-10-14", "session": "2026-10-14"}

    @staticmethod
    def row(number, placed, symbol="SOXL", side=SELL):
        row = helpers.fill_row(symbol, side, ordered=5, filled=5, price="95.00")
        row.update(ord_no=number, ord_time=placed)
        return row

    def chosen(self, dated_rows, attributed=(), ticket=None):
        return tk.ticket_rows(ticket or self.TICKET, dated_rows, set(attributed))

    def test_issue_day_rows_before_the_issue_time_are_left_out(self):
        self.assertEqual(tk.issue_time(self.TICKET), time(7, 45))
        result = self.chosen([("2026-10-14", self.row("0000001", "07:00:00")),     # before the ticket existed
                              ("2026-10-14", self.row("0000002", "07:44:59")),
                              ("2026-10-14", self.row("0000003", "074500")),       # at the issue time (compact form)
                              ("2026-10-14", self.row("0000004", "17:30:00")),
                              ("2026-10-15", self.row("0000005", "00:30:00"))])    # after midnight: not the issue day
        self.assertIsNone(result["note"])
        self.assertEqual(result["orders"], [{"ord_dt": "2026-10-14", "ord_no": "0000003"},
                                            {"ord_dt": "2026-10-14", "ord_no": "0000004"},
                                            {"ord_dt": "2026-10-15", "ord_no": "0000005"}])
        self.assertEqual([row["ord_no"] for row in result["rows"]], ["0000003", "0000004", "0000005"])

    def test_attributed_rows_are_left_out(self):
        rows = [("2026-10-15", self.row("0000005", "00:30:00")), ("2026-10-16", self.row("0000005", "00:30:00"))]
        result = self.chosen(rows, attributed={("2026-10-15", "0000005")})
        # The same order number on another day is another order (the pair is the key).
        self.assertEqual(result["orders"], [{"ord_dt": "2026-10-16", "ord_no": "0000005"}])
        left = self.chosen(rows[:1], {("2026-10-15", "0000005")})
        self.assertEqual(tk.classify_outcome(self.TICKET, left["rows"])["state"], "not_entered")

    def test_other_symbols_and_sides_are_not_candidates(self):
        unreadable = self.row("", "x")
        result = self.chosen([("2026-10-14", unreadable | {"stk_cd": "NBIS"}),
                              ("2026-10-14", unreadable | {"slby_tp_nm": BUY})])
        self.assertEqual((result["note"], result["rows"], result["orders"]), (None, [], []))

    def test_unreadable_cells_fail_closed(self):
        self.assertEqual(self.chosen([("2026-10-15", self.row(" ", "00:30:00"))])["note"], "ORD_NO_UNREADABLE")
        self.assertEqual(self.chosen([("2026-10-14", self.row("0000001", "25:00:00"))])["note"], "ORD_TIME_UNREADABLE")
        self.assertEqual(self.chosen([("2026-10-14", self.row("0000001", ""))])["note"], "ORD_TIME_UNREADABLE")
        broken = self.TICKET | {"issuedAt": "2026-10-14"}
        self.assertIsNone(tk.issue_time(broken))
        self.assertEqual(self.chosen([("2026-10-14", self.row("0000001", "17:30:00"))], ticket=broken)["note"],
                         "ISSUED_AT_UNREADABLE")
        # Order time and issue time matter only on the issue day.
        later = self.chosen([("2026-10-15", self.row("0000001", ""))], ticket=broken)
        self.assertEqual((later["note"], later["orders"]), (None, [{"ord_dt": "2026-10-15", "ord_no": "0000001"}]))

    def test_ledger_keeps_thirty_calendar_days_and_each_pair_once(self):
        self.assertEqual(tk.ATTRIBUTION_DAYS, 30)
        ledger = [{"ord_dt": "2026-09-15", "ord_no": "0000001", "ticket_id": "AT-20260914-SOXL-1"},
                  {"ord_dt": "2026-09-16", "ord_no": "0000002", "ticket_id": "AT-20260915-SOXL-1"}]
        new = [{"ord_dt": "2026-10-15", "ord_no": "0000003", "ticket_id": "AT-20261014-SOXL-1"},
               {"ord_dt": "2026-09-16", "ord_no": "0000002", "ticket_id": "AT-20261014-SOXL-1"}]
        kept = tk.attribute_orders(ledger, new, "2026-10-15")
        # 2026-10-15 - 29 days = 2026-09-16 (kept); 2026-09-15 is 30 days back (dropped).
        self.assertEqual(kept, [ledger[1], new[0]])
        self.assertEqual(ledger[0]["ord_dt"], "2026-09-15")  # the input is not changed
        self.assertEqual(tk.attribute_orders([], [], "2026-10-15"), [])


class Scenario:
    """evaluate_session on synthetic bars: SOXL held, MU a watch member with an official good-news fact.

    The default cash keeps the account total above the V6 first line (25,626.55): r2 R2-3 counts this
    session's EV4, so a smaller account opens R-REC1 and blocks every buy. research_block / research_sessions
    are the decide inputs for today's research record (None = OK) and the recorded sessions (default: all)."""

    def __init__(self, *, holdings=None, cash="30000", members=("MU",), mu_entry=True, mu_eligible=True,
                 mu_hash_ok=True, facts=True, config=None, gate0=(), soxx=None, keys=None, earnings=True,
                 extra_members=(), soxl_entry=None, research_block=None, research_sessions=None):
        self.holdings = holdings if holdings is not None else {"SOXL": 10}
        self.cash = Decimal(cash)
        count = len(DAYS)
        self.bars = {
            "SOXL": helpers.bars("SOXL", DAYS, helpers.zigzag(count, 100, 2.0, 0.05)),
            "SOXX": helpers.bars("SOXX", DAYS, soxx or helpers.zigzag(count, 500, 4.0, 0.3)),
            "MU": helpers.bars("MU", DAYS, helpers.zigzag(count, 200, 3.0, 0.2)),
            "PWR": helpers.bars("PWR", DAYS, helpers.zigzag(count, 300, 3.0, 0.2)),
            "GRID": helpers.bars("GRID", DAYS, helpers.zigzag(count, 150, 1.0, 0.1)),
        }
        self.members = list(members) + list(extra_members)
        static = [{"id": "MU-SE1", "e1_kind": "thesis", "strength": "strong", "direction": "+", "as_of": "2026-10-02",
                   "source": "docs/claude/TEST_ONLY.md:1", "quote": "TEST_ONLY"}]
        entries = {"MU": helpers.entry("MU", static=static) if mu_entry else None,
                   "PWR": helpers.entry("PWR", static=static),
                   "SOXL": soxl_entry or helpers.entry("SOXL", role="holding", action="HOLD")}
        self.checks = {}
        for symbol in sorted(set(self.holdings) | set(self.members)):
            entry = entries.get(symbol)
            eligible = mu_eligible if symbol == "MU" else True
            hash_ok = mu_hash_ok if symbol == "MU" else True
            reasons = [] if eligible and hash_ok else ["CARD_SECTION_CHANGED" if not hash_ok else "REGISTRY_UNCOMMITTED"]
            self.checks[symbol] = helpers.check(symbol, entry, eligible=eligible and hash_ok, hash_ok=hash_ok,
                                                reasons=reasons if entry else None)
        self.facts = [{"fact_id": "MU-FACT-1", "symbol": "MU", "direction": "+", "kind": "contract",
                       "card_trigger_ids": ["U2"], "event_session": LAST, "announced_at": f"{LAST}T16:30:00-04:00",
                       "source_kind": "SEC_FILING", "source_url": "https://www.sec.gov/test", "criterion_a": True,
                       "root_thesis_damage": False, "summary_ko": "TEST_ONLY"}] if facts else []
        checked = datetime.combine(date.fromisoformat(LAST), time(16, 30), tzinfo=helpers.ET).isoformat()
        self.earnings = {symbol: {"status": "NOT_ANNOUNCED", "source_kind": "SEC_FILING",
                                  "source_url": "https://www.sec.gov/test", "checked_at": checked}
                         for symbol in ("MU", "PWR")} if earnings else None
        self.config = config or {"decision_mode": "compare"}
        self.gate0 = list(gate0)
        self.keys = keys or {}
        self.policy = helpers.policy()
        self.research_block = research_block
        self.research_sessions = research_sessions

    def run(self):
        closes = helpers.closes_of(self.bars)
        runner = helpers.s7_runner(policy_value=self.policy, days=CALENDAR_DAYS, evaluation_session=LAST,
                                   holdings=self.holdings, cash=self.cash, closes=closes, earnings=self.earnings)
        watchlist = {"status": "OK", "members": {code: {"cardStatus": "수락(2026-10-02)",
                                                        "sector": "A1 전력" if code == "PWR" else "B1"}
                                                 for code in self.members}}
        sectors = {symbol: (watchlist["members"].get(symbol) or {}).get("sector") for symbol in self.checks}
        bars = {symbol: item for symbol, item in self.bars.items()
                if symbol in self.checks or symbol in ("SOXX", "GRID")}
        return decide_module.evaluate_session(
            day="2026-10-10", mode="compare", issued_at="2026-10-10 07:45 KST", calendar=helpers.calendar(CALENDAR_DAYS),
            evaluation_session=LAST, bars=bars, holdings=self.holdings, cash=self.cash, deposit=self.cash,
            sectors=sectors, members=self.members, checks=self.checks, watchlist=watchlist,
            m6_docs=[("m6-relative-comparison-7stock-TEST.md", "MU PWR SOXL")], facts=self.facts,
            earnings=self.earnings, ev3=[], ev4_sessions=[], seen_fact_ids=set(), policy=self.policy,
            config=self.config, keys=self.keys, gate0=self.gate0, gate1=[], s7_runner=runner,
            research={"block": self.research_block,
                      "sessions": CALENDAR_DAYS if self.research_sessions is None else self.research_sessions,
                      "damage": [fact for fact in self.facts or [] if fact.get("root_thesis_damage")]},
            input_hashes={})


def tickets_of(result, symbol=None, side=None):
    return [ticket for ticket in result["planned"]["tickets"]
            if (symbol is None or ticket["ticker"] == symbol) and (side is None or ticket["side"] == side)]


def blocked_reasons(result, symbol, side):
    return [reason for item in result["planned"]["blocked"] if item["symbol"] == symbol and item["side"] == side
            for reason in item["reasons"]]


class BuyTicketTests(unittest.TestCase):
    def test_new_official_fact_opens_the_circuit_and_makes_a_valid_ticket(self):
        result = Scenario().run()
        tickets = tickets_of(result, "MU", "buy")
        self.assertEqual(len(tickets), 1, result["planned"]["blocked"])
        ticket = tickets[0]
        self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])
        self.assertEqual(ticket["authority"], {"order_authority": False, "quantity_authority": "ORDER_TICKET_HUMAN_ENTRY",
                                               "execution_quantity": None})
        self.assertEqual((ticket["type"], ticket["priceCalc"]["round"]), ("LOC", "down"))
        self.assertTrue(ticket["gap"]["first_entry"])
        self.assertLessEqual(Fraction(ticket["evidence"]["r"]), Fraction(ticket["evidence"]["r_max"]))
        self.assertLessEqual(ticket["qty"] * ticket["price"] * 1.0025, 20000)
        self.assertLessEqual(ticket["gap"]["target_weight"], ticket["gap"]["whole_target"] / 2 + 0.0005)
        # The whole target is exactly what the S7 proposal evaluation passed (largest passing grid weight).
        passing = [item["target_weight"] for item in result["proposal_results"]
                   if item["symbol"] == "MU" and item["status"] == "DISPLAY"]
        self.assertEqual(ticket["gap"]["whole_target"], max(passing))
        # risk1r: a display-only 1R from the evaluation session's EMA20 and ATR14 (grade D).
        self.assertEqual((ticket["risk_1r"]["grade"], ticket["risk_1r"]["display_only"]), ("D", True))
        self.assertIn(ticket["risk_1r"]["status"], ("ok", "below_band"))

    def test_no_research_fact_means_no_new_basis(self):
        result = Scenario(facts=False).run()
        self.assertEqual(tickets_of(result, "MU", "buy"), [])

    def test_e_at_or_above_hard_ceiling_blocks_buys(self):
        result = Scenario(holdings={"SOXL": 190}, cash="200").run()
        self.assertGreaterEqual(result["s7"]["e"], 1.9)
        self.assertEqual(tickets_of(result, side="buy"), [])
        self.assertTrue(any(reason.startswith("REQ2") for reason in blocked_reasons(result, "MU", "buy")))

    def test_policy_unregistered_instrument_has_no_ticket(self):
        scenario = Scenario(extra_members=("PWR",))
        scenario.facts.append({**scenario.facts[0], "fact_id": "PWR-FACT-1", "symbol": "PWR"})
        section = scenario.policy["portfolio_exposure_policy"]  # this test's own copy of the policy
        section["card_stock_core"] = [code for code in section["card_stock_core"] if code != "PWR"]
        section["nominal_multipliers"].pop("PWR", None)
        result = scenario.run()
        self.assertEqual(tickets_of(result, "PWR"), [])
        self.assertIn("POLICY_UNREGISTERED_INSTRUMENT", blocked_reasons(result, "PWR", "buy"))

    def test_registered_instrument_is_not_blocked_by_policy_registration(self):
        scenario = Scenario(extra_members=("PWR",))
        scenario.facts.append({**scenario.facts[0], "fact_id": "PWR-FACT-1", "symbol": "PWR"})
        section = scenario.policy["portfolio_exposure_policy"]
        if "PWR" not in section["card_stock_core"]:
            section["card_stock_core"].append("PWR")
        section["nominal_multipliers"].setdefault("PWR", 1)
        result = scenario.run()
        self.assertNotIn("POLICY_UNREGISTERED_INSTRUMENT", blocked_reasons(result, "PWR", "buy"))
        self.assertEqual(len(tickets_of(result, "PWR", "buy")), 1, result["planned"]["blocked"])

    def test_card_eligibility_failures_mean_no_ticket(self):
        for kwargs, reason in (({"mu_entry": False}, "REQ3_EVIDENCE:unk"),
                               ({"mu_hash_ok": False}, "CARD_SECTION_CHANGED"),
                               ({"mu_eligible": False}, "REGISTRY_UNCOMMITTED")):
            with self.subTest(case=reason):
                result = Scenario(**kwargs).run()
                self.assertEqual(tickets_of(result, "MU"), [])
                self.assertIn(reason, blocked_reasons(result, "MU", "buy"))

    def test_g0_failure_blocks_every_ticket(self):
        result = Scenario(gate0=["G0_OPEN_ORDERS:1"]).run()
        self.assertEqual(result["planned"]["tickets"], [])
        self.assertIn("G0_OPEN_ORDERS:1", blocked_reasons(result, "MU", "buy"))

    def test_missing_earnings_record_is_a_blackout(self):
        result = Scenario(earnings=False).run()
        self.assertEqual(tickets_of(result, "MU"), [])
        self.assertIn("REQ1_EARNINGS:no", blocked_reasons(result, "MU", "buy"))

    def test_g2b_size_and_count_keys(self):
        base = tickets_of(Scenario().run(), "MU", "buy")[0]
        capped = tickets_of(Scenario(config={"max_buy_ticket_pct_of_equity": 0.02}).run(), "MU", "buy")
        if capped:
            self.assertLess(capped[0]["qty"], base["qty"])
            self.assertTrue(str(capped[0]["gates"]["G2b"]).startswith("size_capped"))
        else:
            # Capped below the 2% deadband: no ticket with the allowed reason.
            self.assertTrue({"G2B_CAP", "DEADBAND"} & set(blocked_reasons(Scenario(
                config={"max_buy_ticket_pct_of_equity": 0.02}).run(), "MU", "buy")))
        none_left = Scenario(config={"max_buy_ticket_pct_of_equity": 0.0}).run()
        self.assertIn("G2B_CAP", blocked_reasons(none_left, "MU", "buy"))
        self.assertEqual(tk._limit_daily([{"side": "buy", "amount": 1, "ticker": "A"}, {"side": "sell", "amount": 1,
                                           "ticker": "B"}], {"max_tickets_per_day": 1}, [])[0]["side"], "sell")

    def test_research_only_strong_cap(self):
        result = Scenario(config={"research_only_strong_r_cap": "1/2"}).run()
        evidence = result["evidence"]["MU"]["buy"]
        self.assertFalse(evidence["research_only_strong"])  # MU also has a static strong card row
        check = helpers.check("MU", helpers.entry("MU"))
        only = tk.evidence_summary(side="buy", result={"groups": {}}, check=check,
                                   official={"+": ["F1"], "-": []}, config={"research_only_strong_r_cap": "1/2"})
        self.assertEqual((only["research_only_strong"], only["r_max"]), (True, "1/2"))
        self.assertEqual(tk.evidence_summary(side="buy", result={"groups": {}}, check=check,
                                             official={"+": ["F1"], "-": []}, config={})["r_max"], "1")

    def test_closed_key_is_not_reissued_and_first_cap_key(self):
        ticket = tickets_of(Scenario().run(), "MU", "buy")[0]
        closed = Scenario(keys={ticket["decision_key"]: {"closed": True, "closed_reason": "UNFILLED_TWICE"}}).run()
        self.assertIn("DECISION_KEY_CLOSED:UNFILLED_TWICE", blocked_reasons(closed, "MU", "buy"))
        low = ticket["price"] - 5
        capped = Scenario(config={"reissue_buy_cap_not_above_first": True},
                          keys={ticket["decision_key"]: {"closed": False, "consecutive_not_entered": 1,
                                                         "first_cap": low}}).run()
        self.assertEqual(tickets_of(capped, "MU", "buy")[0]["price"], low)
        uncapped = Scenario(config={"reissue_buy_cap_not_above_first": False},
                            keys={ticket["decision_key"]: {"closed": False, "consecutive_not_entered": 1,
                                                           "first_cap": low}}).run()
        self.assertEqual(tickets_of(uncapped, "MU", "buy")[0]["price"], ticket["price"])  # Q2 b: formula cap
        lapsed = Scenario(keys={ticket["decision_key"]: {"closed": False, "consecutive_not_entered": 1,
                                                         "first_cap": low}}).run()
        self.assertEqual(tickets_of(lapsed, "MU", "buy"), [])  # Q2 c or no answer: not issued again
        self.assertIn("NOT_ENTERED_NO_REISSUE", blocked_reasons(lapsed, "MU", "buy"))
        self.assertEqual(tk.reissue_block({"consecutive_not_entered": 0, "market_tests": 1}, {}), None)

    def test_cash_zero(self):
        result = Scenario(cash="5").run()
        self.assertEqual(tickets_of(result, "MU"), [])
        self.assertTrue({"CASH_ZERO", "REQ2_EXPOSURE_CASH_PRODUCT:no"} & set(blocked_reasons(result, "MU", "buy")))


class EvidenceLadderTests(unittest.TestCase):
    def group(self, name, side, state="hit", previous="none", card=False):
        return {"group": name, "side": side, "state": state, "previous_state": previous, "ids": [name],
                "card_defined": card}

    def test_common_only_caps_at_one_third(self):
        result = {"groups": {"trend_break": self.group("trend_break", "-"), "new_low": self.group("new_low", "-")}}
        check = helpers.check("SOXL", helpers.entry("SOXL", role="holding"))
        summary = tk.evidence_summary(side="sell", result=result, check=check, official={"+": [], "-": []}, config={})
        self.assertEqual((summary["r_max"], summary["common_only"], summary["composition"]), ("1/3", True, "C 단독"))
        result["groups"]["trend_break"]["card_defined"] = True
        self.assertEqual(tk.evidence_summary(side="sell", result=result, check=check,
                                             official={"+": [], "-": []}, config={})["r_max"], "1/2")

    def test_one_weak_kind_is_zero_and_strong_official_is_one(self):
        result = {"groups": {"trend_break": self.group("trend_break", "-", card=True)}}
        check = helpers.check("SOXL", helpers.entry("SOXL", role="holding"))
        self.assertEqual(tk.evidence_summary(side="sell", result=result, check=check,
                                             official={"+": [], "-": []}, config={})["r_max"], "0")
        self.assertEqual(tk.evidence_summary(side="sell", result=result, check=check,
                                             official={"+": [], "-": ["F"]}, config={})["r_max"], "1")

    def test_ineligible_card_is_zero(self):
        result = {"groups": {"trend_break": self.group("trend_break", "-", card=True),
                             "new_low": self.group("new_low", "-")}}
        check = helpers.check("NBIS", None)
        self.assertEqual(tk.evidence_summary(side="sell", result=result, check=check,
                                             official={"+": [], "-": ["F"]}, config={})["r_max"], "0")

    def test_official_counts_only_when_new(self):
        fact = {"fact_id": "F", "symbol": "MU", "direction": "+", "kind": "contract", "criterion_a": True,
                "event_session": "2026-10-08"}
        self.assertEqual(tk.official_evidence("MU", [fact], evaluation_session="2026-10-09",
                                              previous_session="2026-10-08", seen_fact_ids=set())["+"], ["F"])
        self.assertEqual(tk.official_evidence("MU", [fact], evaluation_session="2026-10-09",
                                              previous_session="2026-10-08", seen_fact_ids={"F"})["+"], [])
        self.assertEqual(tk.official_evidence("MU", [{**fact, "criterion_a": False}], evaluation_session="2026-10-08",
                                              previous_session=None, seen_fact_ids=set())["+"], [])
        self.assertEqual(tk.official_evidence("MU", [{**fact, "direction": "-", "kind": "dilution"}],
                                              evaluation_session="2026-10-08", previous_session=None,
                                              seen_fact_ids=set())["-"], ["F"])


class SellTicketTests(unittest.TestCase):
    def falling(self):
        count = len(DAYS)
        closes = helpers.zigzag(count - 6, 100, 1.0, 0.05) + [96.0, 94.0, 92.0, 90.0, 88.0, 86.0]
        return closes

    def test_reduce_gap_with_two_minus_kinds_makes_a_sell_ticket_even_with_an_open_shock(self):
        count = len(DAYS)
        soxx = helpers.zigzag(count - 1, 500, 2.0, 0.3) + [470.0]  # a -2 sigma day on the last session: EV1
        scenario = Scenario(holdings={"SOXL": 120}, cash="300", soxx=soxx)
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, self.falling())
        result = scenario.run()
        self.assertTrue(result["shock"]["open"])
        sells = tickets_of(result, "SOXL", "sell")
        reasons = blocked_reasons(result, "SOXL", "sell")
        self.assertTrue(sells or set(reasons) <= set(tk.ALLOWED_NO_TICKET), reasons)
        for ticket in sells:
            self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])
            self.assertEqual(ticket["priceCalc"]["round"], "up")
            self.assertEqual(ticket["gates"]["G5"], "not_applicable_sell")
            self.assertTrue(ticket["after_sale"]["display_only"])
            self.assertIn("e", ticket["after_sale"])
            self.assertNotIn("risk_1r", ticket)  # risk1r: buy tickets only

    def test_nocard_holding_gets_no_sell_ticket(self):
        scenario = Scenario(holdings={"SOXL": 120}, cash="300")
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, self.falling())
        scenario.checks["SOXL"] = helpers.check("SOXL", None)
        result = scenario.run()
        self.assertEqual(tickets_of(result, "SOXL"), [])


def soxl_two_new_cues():
    """SOXL closes whose last session newly hits two + kinds (new high held C5+, pullback rebound C6+)."""
    closes = [round(100 + (0.1 if index % 2 else -0.1), 4) for index in range(len(DAYS) - 3)]
    closes[-1] = 99.9
    return closes + [100.05, 100.3, 100.5]


def falling_soxl():
    return helpers.zigzag(len(DAYS) - 6, 100, 1.0, 0.05) + [96.0, 94.0, 92.0, 90.0, 88.0, 86.0]


class ResearchRecordGateTests(unittest.TestCase):
    """r2 R2-1 (Judge F-1, J6): without an OK research record every buy is blocked, index ETFs included."""

    def soxl_case(self, ok):
        scenario = Scenario(facts=ok, earnings=ok, research_block=None if ok else "RESEARCH_RECORD_MISSING")
        if not ok:
            scenario.facts = None  # what decide passes when today's record is not OK
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, soxl_two_new_cues())
        return scenario.run()

    def test_no_research_record_blocks_the_index_etf_buy(self):
        result = self.soxl_case(ok=False)
        self.assertEqual(result["evidence"]["SOXL"]["buy"]["new_kinds"], ["new_high", "pullback_rebound"])
        self.assertIn({"symbol": "SOXL", "side": "buy", "trigger": "NEW_EVIDENCE"}, result["planned"]["candidates"])
        self.assertEqual(tickets_of(result, "SOXL", "buy"), [])
        self.assertIn("RESEARCH_RECORD_NOT_OK:RESEARCH_RECORD_MISSING", blocked_reasons(result, "SOXL", "buy"))
        row = next(row for row in result["rows"] if row["code"] == "SOXL")
        self.assertEqual(row["c"][0], {"s": "no", "t": "막힘 RESEARCH_RECORD_NOT_OK:RESEARCH_RECORD_MISSING"})
        # The same day with an OK record issues the SOXL buy: the record alone made the difference.
        with_record = self.soxl_case(ok=True)
        self.assertEqual(len(tickets_of(with_record, "SOXL", "buy")), 1, with_record["planned"]["blocked"])
        self.assertEqual(next(row for row in with_record["rows"] if row["code"] == "SOXL")["c"][0]["s"], "ok")

    def sell_case(self, ok):
        soxx = helpers.zigzag(len(DAYS) - 1, 500, 2.0, 0.3) + [470.0]
        scenario = Scenario(holdings={"SOXL": 120}, cash="300", soxx=soxx, facts=ok, earnings=ok,
                            research_block=None if ok else "RESEARCH_RECORD_MISSING")
        if not ok:
            scenario.facts = None
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, falling_soxl())
        return scenario.run()

    def test_the_sell_circuit_is_the_same_without_a_research_record(self):
        missing, present = self.sell_case(ok=False), self.sell_case(ok=True)
        sells = [(ticket["qty"], ticket["price"]) for ticket in tickets_of(missing, "SOXL", "sell")]
        self.assertEqual(len(sells), 1)
        self.assertEqual(sells, [(ticket["qty"], ticket["price"]) for ticket in tickets_of(present, "SOXL", "sell")])
        self.assertEqual(blocked_reasons(missing, "SOXL", "sell"), blocked_reasons(present, "SOXL", "sell"))
        self.assertFalse(any(reason.startswith("RESEARCH_RECORD_NOT_OK")
                             for item in missing["planned"]["blocked"] if item["side"] == "sell"
                             for reason in item["reasons"]))


class SessionEv4Tests(unittest.TestCase):
    """r2 R2-3 (Judge F-3): the evaluation session's own EV4 opens R-REC1 before the gates."""

    def test_no_previous_record_and_total_below_the_first_line_blocks_buys(self):
        scenario = Scenario(cash="5000")
        result = scenario.run()
        self.assertTrue(result["account"]["ev4_open"])
        self.assertLessEqual(Decimal(str(result["account"]["total"])), Decimal("25626.55"))
        self.assertTrue(result["shock"]["open"])
        self.assertEqual(result["shock"]["event"]["date"], LAST)
        self.assertIn("EV4", result["shock"]["event"]["kinds"])
        mu = next(row for row in result["rows"] if row["code"] == "MU")
        self.assertNotEqual(mu["c"][4]["s"], "ok")
        self.assertIn({"symbol": "MU", "side": "buy", "trigger": "NEW_EVIDENCE"}, result["planned"]["candidates"])
        self.assertEqual(tickets_of(result, side="buy"), [])
        self.assertTrue(any(reason.startswith("REQ5_RREC1") for reason in blocked_reasons(result, "MU", "buy")))


class ResearchCoverageTests(unittest.TestCase):
    """r2 R2-4 (Judge F-4): one session after the R-REC1 event without a research record leaves RG1 unknown."""

    def test_unrecorded_session_after_the_event_blocks_the_buy(self):
        soxx = helpers.zigzag(len(DAYS), 500, 2.0, 0.3)
        event = len(DAYS) - 1 - 8
        soxx[event] = round(soxx[event - 1] * 0.95, 4)  # EV1, recovered since
        recorded = Scenario(soxx=soxx).run()
        self.assertEqual((recorded["shock"]["status"], recorded["shock"]["open"]), ("ok", False))
        self.assertEqual(len(tickets_of(recorded, "MU", "buy")), 1, recorded["planned"]["blocked"])
        missing = DAYS[event + 1]  # the rebound day: not a 1-sigma fall, so only RG1 is affected
        gap = Scenario(soxx=soxx, research_sessions=[day for day in CALENDAR_DAYS if day != missing]).run()
        self.assertEqual((gap["shock"]["open"], gap["shock"]["rg"]["RG1"]), (True, "unk"))
        self.assertEqual(gap["shock"]["rg1_coverage"]["missing_sessions"], [missing])
        self.assertEqual(next(row for row in gap["rows"] if row["code"] == "MU")["c"][4]["s"], "unk")
        self.assertEqual(tickets_of(gap, side="buy"), [])


class PlanPremiseTests(unittest.TestCase):
    """r2 R2-6 (Judge K1 23b): a sell ticket names the S7 plan steps it assumes and its E when it fills alone."""

    PLAN = [{"order": 1, "basis": "single_stock_cap_excess_including_sell_only", "symbol": "MVLL", "target_weight": 0.2},
            {"order": 3, "basis": "SOXL", "symbol": "SOXL", "target_weight": 0.271}]

    def ticket(self, symbol="SOXL", source="S7_REDUCE_3", qty=20):
        return {"ticker": symbol, "qty": qty, "gap": {"source": source}, "after_sale": {"e": 1.5495}}

    def test_earlier_step_without_a_ticket(self):
        soxl = self.ticket()
        self.assertEqual(tk.plan_premise(soxl, self.PLAN, [soxl], [], []),
                         "S7 계획 전제: 앞 순서 MVLL 상한 초과분 — 오늘 주문표 없음(매도 근거 없음) · 이 주문표만 체결 시 예상 E 1.5495")
        blocked = [{"symbol": "MVLL", "side": "sell", "reasons": ["DEADBAND"]}]
        self.assertIn("MVLL 상한 초과분 — 오늘 주문표 없음(DEADBAND)", tk.plan_premise(soxl, self.PLAN, [soxl], blocked, []))
        mvll = self.ticket("MVLL", "S7_REDUCE_1", 5)
        self.assertIn("오늘 주문표 있음(5주)", tk.plan_premise(soxl, self.PLAN, [mvll, soxl], [], []))
        self.assertEqual(tk.plan_premise(mvll, self.PLAN, [mvll, soxl], [], []),
                         "S7 계획 전제: 앞 순서 없음 · 이 주문표만 체결 시 예상 E 1.5495")
        self.assertTrue(tk.plan_premise(self.ticket(source="CARD_EXIT"), self.PLAN, [], [], []).startswith(
            "카드 목표(CARD_EXIT) — S7 계획 순서 아님"))

    def test_sell_ticket_carries_the_line_in_gap_and_after_sale(self):
        soxx = helpers.zigzag(len(DAYS) - 1, 500, 2.0, 0.3) + [470.0]
        scenario = Scenario(holdings={"SOXL": 120}, cash="300", soxx=soxx)
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, falling_soxl())
        ticket = tickets_of(scenario.run(), "SOXL", "sell")[0]
        self.assertEqual(ticket["gap"]["plan_premise"], ticket["after_sale"]["plan_premise"])
        self.assertTrue(ticket["gap"]["plan_premise"].startswith("S7 계획 전제: "))
        self.assertIn(f"예상 E {ticket['after_sale']['e']}", ticket["gap"]["plan_premise"])
        self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])
        self.assertIn(ticket["gap"]["plan_premise"], decide_module._after_sale_line(ticket["after_sale"]))


class LotZeroAfterStepTests(unittest.TestCase):
    def test_zero_shares_after_the_step_is_lot_zero(self):
        # Gap 2 shares (first entry 0.02 of 10,000 at 100), step 1/3 -> floor(2/3) = 0 shares with ample cash.
        ctx = {"policy_instruments": {"MU"}, "equity": Decimal("10000"), "holdings": {}, "weights": {},
               "proposal_results": [{"symbol": "MU", "target_weight": 0.04, "status": "DISPLAY", "reasons": []}],
               "closes": {"MU": Decimal("100")}, "sigmas": {"MU": 0.02}, "cash": Decimal("100000"),
               "scenarios": {"MU": {"status": "ok", "up": 0.02, "down": -0.02, "worst_day": -0.03}},
               "checks": {"MU": {"entry": {}}}, "keys": {}, "config": {}}
        row = {"code": "MU", "add": False, "c": [{"s": "ok", "t": ""}] * 5 + [{"s": "wait", "t": ""}]}
        blocked = []
        self.assertIsNone(tk._buy_ticket(ctx, "MU", row, {"r_max": "1/3", "ids": ["MU:x"]}, [], blocked))
        self.assertEqual(blocked, [{"symbol": "MU", "side": "buy", "reasons": ["LOT_ZERO"]}])


class RequirementRowTests(unittest.TestCase):
    def test_six_cells_and_index_etf_has_no_earnings_date(self):
        result = Scenario().run()
        rows = {row["code"]: row for row in result["rows"]}
        self.assertEqual(len(rows["MU"]["c"]), 6)
        self.assertEqual(rows["MU"]["c"][5]["s"], "wait")
        self.assertEqual(rows["SOXL"]["c"][0]["s"], "ok")
        self.assertTrue(rows["SOXL"]["add"])

    def test_rule_file_nominal(self):
        nominal = tk.rule_file_nominal({"SOXL": 10, "PWR": 5}, {"SOXL": Decimal("100"), "PWR": Decimal("200")},
                                       Decimal("1000"), {"SOXL": 3})
        self.assertAlmostEqual(nominal["n"], (3 * 1000 + 1 * 1000) / 3000)
        self.assertEqual(nominal["assumed_one_x"], ["PWR"])
        self.assertIsNone(tk.rule_file_nominal({"ZZZ": 1}, {"ZZZ": Decimal("1")}, Decimal("1"), {})["n"])

    def test_policy_mismatch_is_reported(self):
        self.assertEqual(tk.policy_mismatches({"policy": {"target_exposure": 1.55, "reduce_when_exposure_gte": 1.85,
                                                          "hard_ceiling_when_exposure_gte": 1.9,
                                                          "single_stock_nominal_cap": 0.4}}), [])
        self.assertEqual(tk.policy_mismatches({"policy": {"target_exposure": 1.6, "reduce_when_exposure_gte": 1.85,
                                                          "hard_ceiling_when_exposure_gte": 1.9,
                                                          "single_stock_nominal_cap": 0.4}}),
                         ["POLICY_THRESHOLD_CHANGED:target_exposure"])


class EnterWindowTests(unittest.TestCase):
    """r4 R4-2: the entry window ends at the session's open (calendar core_open_at in KST) and names the open's
    KST date when it is not the issue day; fillAt is unchanged."""

    CALENDAR = helpers.calendar(helpers.sessions("2026-10-01", 70))  # summer and winter time, no holiday

    def window(self, issued, session, calendar=None):
        return tk.enter_window(issued, (calendar or self.CALENDAR)["sessions"][session])

    def test_weekday(self):
        self.assertEqual(self.window("2026-10-14", "2026-10-14"), "한국 10/14 17:00 이후 ~ 정규장 개장 전(22:30)")

    def test_saturday_for_monday(self):
        self.assertEqual(self.window("2026-10-17", "2026-10-19"), "한국 10/17 17:00 이후 ~ 10/19 22:30 개장 전")

    def test_tuesday_after_a_holiday(self):
        calendar = copy.deepcopy(self.CALENDAR)
        del calendar["sessions"]["2026-10-19"]  # U.S. holiday on Monday 10/19: the Saturday ticket is for Tuesday
        self.assertEqual(self.window("2026-10-17", "2026-10-20", calendar), "한국 10/17 17:00 이후 ~ 10/20 22:30 개장 전")

    def test_winter_time(self):
        # 09:30 EST = 23:30 KST (from 11/2).
        self.assertEqual(self.window("2026-11-04", "2026-11-04"), "한국 11/4 17:00 이후 ~ 정규장 개장 전(23:30)")
        self.assertEqual(self.window("2026-11-07", "2026-11-09"), "한국 11/7 17:00 이후 ~ 11/9 23:30 개장 전")

    def test_the_ticket_carries_it_and_fill_at_is_unchanged(self):
        # Scenario issues on Saturday 2026-10-10 for Monday 2026-10-12.
        ticket = tickets_of(Scenario().run(), "MU", "buy")[0]
        self.assertEqual(ticket["session"], "2026-10-12")
        self.assertEqual(ticket["enterWindow"], "한국 10/10 17:00 이후 ~ 10/12 22:30 개장 전")
        self.assertEqual(ticket["fillAt"], "10/13 05:00 (한국) 정규장 종가")


if __name__ == "__main__":
    unittest.main()
