"""t2-equity-cash (user decisions 2026-10-13): the total equity behind decide's rule-file N, V6 account line and
EV4 uses the approved cash - Kiwoom order-available behind T1's one cash check - and no longer the settled
deposit fc_entra (a sale before settlement lowered the total, a buy before settlement counted the shares and the
unpaid cash).

T1 the 2026-10-13 values  T2 a sale before settlement without a settled > held row  T3 a buy before settlement
T4 the three values equal (the result as before)  T5 missing values  T6 decide records of the existing fixtures.
Synthetic inputs (TEST_ONLY) except the 2026-10-13 broker snapshot values and closes of T1. No Kiwoom, no network.
"""

from __future__ import annotations

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
TESTS = ROOT / "manage-us-stock-strategy/tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(TESTS))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import auto_core_tickets as tickets_module  # noqa: E402
import helpers  # noqa: E402
import kiwoom_broker_shadow  # noqa: E402
import test_auto_core_decide as decide_fixture  # noqa: E402
from validation_common import validate_instance, write_json  # noqa: E402

CENT = Decimal("0.01")
MULTIPLIERS = dict(helpers.policy()["portfolio_exposure_policy"]["nominal_multipliers"])
# The 2026-10-13 07:45 KST decide run (evaluation session 2026-10-12): T1's broker snapshot and the closes.
HOLDINGS_1013 = {"MVLL": 159, "NBIS": 13, "SOXL": 53}
CLOSES_1013 = {"MVLL": Decimal("35.806"), "NBIS": Decimal("209.98"), "SOXL": Decimal("128.3599")}
ROWS_1013 = [{"ticker": "MVLL", "settled_quantity": 159.0, "held_quantity": 159.0},
             {"ticker": "NBIS", "settled_quantity": 13.0, "held_quantity": 13.0},
             {"ticker": "SOXL", "settled_quantity": 75.0, "held_quantity": 53.0}]
CASH_1013 = {"foreign_currency_deposit": 9396.68, "withdrawable_cash": 9396.68, "order_available_cash": 12469.18}
S7_HWM_1013 = "30255.3600"
FIELDS = ("order_available_cash", "withdrawable_cash", "foreign_currency_deposit")


def old_deposit(cash, _holdings):
    """The cash of the total before t2-equity-cash (fc_entra, settled money only), kept as the reference."""
    return decide_module._decimal((cash or {}).get("foreign_currency_deposit")), "PRE_CHANGE_FC_ENTRA"


def total_view(cash_value, holdings=None, closes=None, hwm=S7_HWM_1013):
    """The rule-file N, the V6 state and EV4 of one total, through the functions decide calls."""
    nominal = tickets_module.rule_file_nominal(holdings or HOLDINGS_1013, closes or CLOSES_1013, cash_value,
                                               MULTIPLIERS)
    total = nominal["total"]
    return {"total": None if total is None else total.quantize(CENT),
            "n": None if nominal["n"] is None else round(nominal["n"], 4), "status": nominal["status"],
            "v6": rules.v6_account(total)["state"], "ev4": rules.ev4_open(total, hwm)}


def settled_as_held(rows):
    return [dict(row, settled_quantity=row["held_quantity"]) for row in rows]


class EquityCashChoiceTests(unittest.TestCase):
    """The one choice function (auto_core_decide.equity_cash) and the totals it gives."""

    def test_t1_2026_10_13_order_available_passes_the_check(self):
        cash, basis = decide_module.equity_cash(CASH_1013, ROWS_1013)
        self.assertEqual((cash, basis), (Decimal("12469.18"), "ORDER_AVAILABLE"))
        self.assertEqual(total_view(cash), {"total": Decimal("27695.15"), "n": 1.2466, "status": "OK",
                                            "v6": "none", "ev4": False})
        self.assertFalse(rules.ev4_open(tickets_module.rule_file_nominal(
            HOLDINGS_1013, CLOSES_1013, cash, MULTIPLIERS)["total"], "30255.3600"))
        # That day's record (fc_entra): the account line in review and EV4 open.
        self.assertEqual(total_view(old_deposit(CASH_1013, ROWS_1013)[0]),
                         {"total": Decimal("24622.65"), "n": 1.4022, "status": "OK", "v6": "review", "ev4": True})

    def test_the_check_is_t1s_imported_function(self):
        self.assertIs(decide_module.order_available_cash_errors, kiwoom_broker_shadow.order_available_cash_errors)
        calls = []

        def failing(order_available, withdrawable, quantities):
            calls.append((order_available, withdrawable, quantities))
            return ["TEST_ONLY_CHECK_FAILED"]

        with mock.patch.object(decide_module, "order_available_cash_errors", failing):
            cash, basis = decide_module.equity_cash(CASH_1013, ROWS_1013)
        self.assertEqual((cash, basis), (Decimal("9396.68"), "MIN_FALLBACK:TEST_ONLY_CHECK_FAILED"))
        self.assertEqual(calls, [(Decimal("12469.18"), Decimal("9396.68"),
                                  [(Decimal("159.0"), Decimal("159.0")), (Decimal("13.0"), Decimal("13.0")),
                                   (Decimal("75.0"), Decimal("53.0"))])])

    def test_t2_sale_unsettled_without_a_settled_above_held_row_falls_to_the_deposit(self):
        for rows in (settled_as_held(ROWS_1013), [dict(row, settled_quantity=None) for row in ROWS_1013], [], None):
            with self.subTest(rows=rows):
                cash, basis = decide_module.equity_cash(CASH_1013, rows)
                self.assertEqual(basis, "MIN_FALLBACK:CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS")
                self.assertEqual(cash, Decimal("9396.68"))  # never order-available after a failed check
                self.assertEqual(total_view(cash), total_view(old_deposit(CASH_1013, rows)[0]))

    def test_t3_buy_unsettled_uses_order_available_without_double_count(self):
        # $10 000 and no shares; a buy of 30 x $100 filled, not settled: held 30 (settled 0), the deposit still
        # holds the $3 000. Order-available below withdrawable fails the check; withdrawable down too passes it.
        rows = [{"ticker": "MU", "settled_quantity": 0.0, "held_quantity": 30.0}]
        cases = (({"foreign_currency_deposit": 10000.0, "withdrawable_cash": 10000.0, "order_available_cash": 7000.0},
                  "MIN_FALLBACK:CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE"),
                 ({"foreign_currency_deposit": 10000.0, "withdrawable_cash": 7000.0, "order_available_cash": 7000.0},
                  "ORDER_AVAILABLE"))
        for cash_block, expected_basis in cases:
            with self.subTest(basis=expected_basis):
                cash, basis = decide_module.equity_cash(cash_block, rows)
                self.assertEqual((cash, basis), (Decimal("7000"), expected_basis))
                nominal = tickets_module.rule_file_nominal({"MU": 30}, {"MU": Decimal("100")}, cash, MULTIPLIERS)
                self.assertEqual(nominal["total"], Decimal("10000"))  # the account before the buy
                before = tickets_module.rule_file_nominal({"MU": 30}, {"MU": Decimal("100")},
                                                          old_deposit(cash_block, rows)[0], MULTIPLIERS)
                self.assertEqual(before["total"], Decimal("13000"))  # before: the shares and the unpaid cash

    def test_t4_three_values_equal_keep_the_previous_result(self):
        rows = settled_as_held(ROWS_1013)
        cash_block = {field: 9396.68 for field in FIELDS}
        cash, basis = decide_module.equity_cash(cash_block, rows)
        self.assertEqual((cash, basis), (Decimal("9396.68"), "ORDER_AVAILABLE"))
        golden = {"total": Decimal("24622.65"), "n": 1.4022, "status": "OK", "v6": "review", "ev4": True}
        self.assertEqual(total_view(cash), golden)
        self.assertEqual(total_view(old_deposit(cash_block, rows)[0]), golden)
        self.assertEqual(tickets_module.rule_file_nominal(HOLDINGS_1013, CLOSES_1013, cash, MULTIPLIERS),
                         tickets_module.rule_file_nominal(HOLDINGS_1013, CLOSES_1013,
                                                          old_deposit(cash_block, rows)[0], MULTIPLIERS))

    def test_t4_check_tolerance_is_t1s(self):
        rows = settled_as_held(ROWS_1013)
        within = {"foreign_currency_deposit": 9396.68, "withdrawable_cash": 9396.68, "order_available_cash": 9397.68}
        self.assertEqual(decide_module.equity_cash(within, rows), (Decimal("9397.68"), "ORDER_AVAILABLE"))
        above = dict(within, order_available_cash=9397.69)
        self.assertEqual(decide_module.equity_cash(above, rows),
                         (Decimal("9396.68"), "MIN_FALLBACK:CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS"))

    def test_t5_missing_values_take_the_smallest_known(self):
        cases = (
            ({"foreign_currency_deposit": 9396.68, "order_available_cash": 12469.18},
             (Decimal("9396.68"), "MIN_FALLBACK:CASH_VALUE_MISSING:withdrawable_cash")),
            ({"foreign_currency_deposit": 9396.68, "withdrawable_cash": 9396.68},
             (Decimal("9396.68"), "MIN_FALLBACK:CASH_VALUE_MISSING:order_available_cash")),
            ({"foreign_currency_deposit": 10000.0, "order_available_cash": 7000.0},
             (Decimal("7000"), "MIN_FALLBACK:CASH_VALUE_MISSING:withdrawable_cash")),
            ({"foreign_currency_deposit": 9396.68},
             (Decimal("9396.68"), "MIN_FALLBACK:CASH_VALUE_MISSING:order_available_cash,withdrawable_cash")),
            ({"foreign_currency_deposit": 9396.68, "withdrawable_cash": "n/a", "order_available_cash": None},
             (Decimal("9396.68"), "MIN_FALLBACK:CASH_VALUE_MISSING:order_available_cash,withdrawable_cash")),
            # The deposit is not needed when the check passes.
            ({"withdrawable_cash": 9396.68, "order_available_cash": 12469.18},
             (Decimal("12469.18"), "ORDER_AVAILABLE")),
        )
        for cash_block, expected in cases:
            with self.subTest(cash=cash_block):
                self.assertEqual(decide_module.equity_cash(cash_block, ROWS_1013), expected)

    def test_t5_no_value_leaves_n_unknown_as_before(self):
        for cash_block in ({}, None, {field: None for field in FIELDS}, {"foreign_currency_deposit": float("nan")}):
            with self.subTest(cash=cash_block):
                cash, basis = decide_module.equity_cash(cash_block, ROWS_1013)
                self.assertEqual((cash, basis), (None, "CASH_UNAVAILABLE"))
                view = total_view(cash)
                self.assertEqual((view["total"], view["n"], view["v6"], view["ev4"]), (None, None, "unk", False))
                self.assertEqual(view["status"], "CASH_UNAVAILABLE")
                self.assertEqual(total_view(old_deposit(cash_block, ROWS_1013)[0])["n"], None)


# ---------------------------------------------------------------------------------------------
# T6 and the 2026-10-13 values through decide
# ---------------------------------------------------------------------------------------------

def write_snapshot(env, rows, cash):
    write_json(env.day_dir / "kiwoom_broker_snapshot.shadow.json", {"holdings": rows, "cash": cash})


def reset_journal(env):
    write_json(env.journal, decide_fixture.EMPTY_JOURNAL)


ACCOUNT_TOTAL_FIELDS = ("total", "state", "first_cushion_pct", "ev4_open", "max_reached", "hwm_candidate")


def comparable(decision, *, total_changes=False):
    """The record without what t2-equity-cash may change: exposure.cash_basis (new) and the journal's
    decision_sha256 (the hash of the whole record) always; with total_changes also N and the account total."""
    view = copy.deepcopy(decision)
    view["exposure"].pop("cash_basis", None)
    view["journal"].pop("decision_sha256", None)
    if total_changes:
        view["exposure"].pop("N", None)
        for key in ACCOUNT_TOTAL_FIELDS:
            view["account"].pop(key, None)
        run_core = view["dashboard"]["runCore"]
        run_core["exposure"].pop("N", None)
        run_core.pop("account", None)
    return view


class DecideRecordTests(unittest.TestCase):
    """T6: decide's records of the existing fixtures (test_auto_core_decide.Env) against the same run with the
    cash of the total as before (old_deposit). Without unsettled money everything but exposure.cash_basis is
    equal; runCore never gets cash_basis."""

    def env(self, **kwargs):
        env = decide_fixture.Env(**kwargs)
        self.addCleanup(env.close)
        return env

    def pair(self, env):
        new = env.run()
        if env.journal.is_file() and new["decision_mode"] == "apply":
            reset_journal(env)
        with mock.patch.object(decide_module, "equity_cash", old_deposit):
            old = env.run()
        self.assertEqual(validate_instance(new, decide_module.DECISION_SCHEMA), [])
        return new, old

    def fixtures(self):
        default = self.env()
        mu_ticket = self.env(holdings={"SOXL": 10})
        mu_ticket.write_good_news()
        soxl_cues = self.env()
        soxl_cues.bars["SOXL"] = helpers.bars("SOXL", decide_fixture.DAYS, decide_fixture._soxl_two_new_cues())
        applied = self.env(holdings={"SOXL": 10}, decision_mode="apply")
        applied.write_good_news()
        return {"default": default, "mu_buy_ticket": mu_ticket, "soxl_buy_ticket": soxl_cues,
                "mu_buy_ticket_apply": applied}

    def test_t6_existing_fixtures_give_the_same_record(self):
        for name, env in self.fixtures().items():
            with self.subTest(fixture=name):
                new, old = self.pair(env)
                # The fixtures' snapshot has no withdrawable_cash: the smallest known value, equal to before.
                self.assertEqual(new["exposure"]["cash_basis"], "MIN_FALLBACK:CASH_VALUE_MISSING:withdrawable_cash")
                self.assertEqual(comparable(new), comparable(old))
                self.assertEqual((new["exposure"]["N"], new["account"]), (old["exposure"]["N"], old["account"]))
                self.assertNotIn("cash_basis", new["dashboard"]["runCore"]["exposure"])
                self.assertEqual(new["dashboard"], old["dashboard"])
        self.assertTrue(new["tickets"])  # the apply fixture issues its ticket (compared above)

    def test_t6_three_values_equal_give_the_same_record(self):
        env = self.env()
        write_snapshot(env, [{"ticker": "SOXL", "settled_quantity": 40, "held_quantity": 40}],
                       {field: 30000.0 for field in FIELDS})
        new, old = self.pair(env)
        self.assertEqual(new["exposure"]["cash_basis"], "ORDER_AVAILABLE")
        self.assertEqual(comparable(new), comparable(old))
        self.assertEqual((new["exposure"]["N"], new["account"]), (old["exposure"]["N"], old["account"]))

    def test_t6_unsettled_money_changes_only_n_and_the_account_total(self):
        cases = (
            # A sale before settlement: order-available holds the proceeds (+3 000), SOXL settled 50 > held 40.
            ("sale", "30000.00", [{"ticker": "SOXL", "settled_quantity": 50, "held_quantity": 40}],
             {"order_available_cash": 30000.0, "withdrawable_cash": 27000.0, "foreign_currency_deposit": 27000.0},
             "ORDER_AVAILABLE", Decimal("3000")),
            # A buy before settlement: the deposit still holds the unpaid 3 000 (-3 000, no double count).
            ("buy", "27000.00", [{"ticker": "SOXL", "settled_quantity": 30, "held_quantity": 40}],
             {"order_available_cash": 27000.0, "withdrawable_cash": 30000.0, "foreign_currency_deposit": 30000.0},
             "MIN_FALLBACK:CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE", Decimal("-3000")),
        )
        for name, cash, rows, cash_block, basis, change in cases:
            with self.subTest(case=name):
                env = self.env(cash=cash)
                write_snapshot(env, rows, cash_block)
                new, old = self.pair(env)
                self.assertEqual(new["status"], "OK", new["reasons"])
                self.assertEqual(new["exposure"]["cash_basis"], basis)
                self.assertEqual(Decimal(str(new["account"]["total"])) - Decimal(str(old["account"]["total"])), change)
                self.assertNotEqual(new["exposure"]["N"], old["exposure"]["N"])
                self.assertEqual(comparable(new, total_changes=True), comparable(old, total_changes=True))


class DecideOctober13Tests(unittest.TestCase):
    """T1 through decide: the 2026-10-13 holdings, closes and broker cash reach the rule-file N, V6 and EV4."""

    def env(self):
        env = decide_fixture.Env(holdings=dict(HOLDINGS_1013), cash="12469.18")
        self.addCleanup(env.close)
        count = len(decide_fixture.DAYS)
        for symbol, start in (("MVLL", 35.0), ("NBIS", 205.0), ("SOXL", 125.0)):
            closes = helpers.zigzag(count, start, 0.5, 0.0)
            closes[-1] = float(CLOSES_1013[symbol])
            env.bars[symbol] = helpers.bars(symbol, decide_fixture.DAYS, closes)
        write_snapshot(env, copy.deepcopy(ROWS_1013), dict(CASH_1013))
        return env

    def test_t1_through_decide(self):
        env = self.env()
        decision = env.run()
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        self.assertNotIn("G1_STATE_NOT_EQUAL_BROKER", decision["reasons"])
        account, exposure = decision["account"], decision["exposure"]
        self.assertEqual(exposure["cash_basis"], "ORDER_AVAILABLE")
        self.assertEqual(Decimal(str(account["total"])).quantize(CENT), Decimal("27695.15"))
        self.assertEqual(round(exposure["N"], 4), 1.2466)
        self.assertEqual(account["state"], "none")
        self.assertEqual(account["ev4_open"], rules.ev4_open(Decimal(str(account["total"])), account["s7_hwm_usd"]))
        self.assertFalse(rules.ev4_open(Decimal(str(account["total"])), S7_HWM_1013))
        with mock.patch.object(decide_module, "equity_cash", old_deposit):
            before = env.run()
        self.assertEqual(Decimal(str(before["account"]["total"])).quantize(CENT), Decimal("24622.65"))
        self.assertEqual(round(before["exposure"]["N"], 4), 1.4022)
        self.assertEqual(before["account"]["state"], "review")


if __name__ == "__main__":
    unittest.main()
