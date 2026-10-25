"""cf-b2n (B2-N, user decisions 2026-10-23/25): an external outflow missing from the transaction history.

I3 passes for it only when it is an outflow, no other I3 reason is present, and the snapshot residual R equals the
ust21132 deposit-ledger residual L (by U.S. trading day) within 0.05; the result carries unverified_outflow_usd and
one warning, and the cash-flow declaration (HWM) is untouched. Anything else holds. The ust21132 reads are made
only for such a candidate and are never I1 reads. Account data and amounts are synthetic (TEST_ONLY); the
2026-10-23 replay uses the balances of the diagnosis (docs/claude/cashflow-proof-options-2026-10-23.md). No
network, no Kiwoom runtime.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_reconcile as core  # noqa: E402
import cash_flow_evidence as cfe  # noqa: E402
import kiwoom_account_readonly_bridge as bridge  # noqa: E402
import test_auto_core as base  # noqa: E402
import test_auto_core_reconcile_orddt as orddt  # noqa: E402
from kiwoom_runtime_bridge import BLOCKED_TERMS, BridgeError  # noqa: E402

KST = core.KST


def calendar(*sessions):
    """A synthetic operating calendar: regular close 16:00 ET on each session (EDT in October)."""
    return {"sessions": {day: {"session_date": day, "core_close_at": f"{day}T16:00:00-04:00"} for day in sessions},
            "identity": {"coverage_start": "2026-01-01", "coverage_end": "2026-12-31"}}


CALENDAR = calendar("2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16",
                    "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23")


def ledger_row(fx_entr, won_entr="0", currency="USD"):
    # A row after the bridge has attached the body's top-level won_entr (BridgeReadTests: the real ust21132 shape).
    return {"crnc_code": currency, "fx_entr": fx_entr, "won_entr": won_entr}


def ledger_read(base_dt, rows, status="PASS"):
    return {"operation": core.LEDGER_OPERATION, "bridge_status": status, "request_params": {"base_dt": base_dt},
            "pagination": {"complete": status == "PASS"}, "data": rows}


class LedgerBroker(base.FakeBroker):
    """test_auto_core's FakeBroker that also answers the ust21132 read (rows by base_dt)."""

    def __init__(self, *, ledger=None, **values):
        super().__init__(**values)
        self.ledger = ledger or {}

    def data(self, request):
        if request["operation"] == core.LEDGER_OPERATION:
            return self.ledger.get(request["params"]["base_dt"], [])
        return super().data(request)

    def ledger_requests(self):
        return [request for request in self.requests if request["operation"] == core.LEDGER_OPERATION]


# The U.S. 10/13 sale of test_auto_core.sale_broker (AAA 3, settles KST 10/15 for 329.17) plus a withdrawal of
# 82.93 that no transaction-history row shows: R = 1246.24 - 1000.00 - 329.17 = -82.93. ust21132: 10/12 1000.01,
# 10/13 1246.25 -> L = 1246.25 - 1000.01 - 329.17 = -82.93.
WITHDRAWN_CASH = "1246.24"
LEDGER = {"20261012": [ledger_row("1000.01")], "20261013": [ledger_row("1246.25")]}


def own_warnings(result):
    """The run's warnings other than the fixture state's proposal warnings (timing plan, policy positions)."""
    return [item for item in result["warnings"] if not item.startswith("PROPOSAL_WARNING:")]


def withdrawal_broker(ledger=None, **changes):
    values = dict(holdings=[base.holding("AAA", 7, settled=10), base.holding("BBB", 5)], ord_cash=WITHDRAWN_CASH,
                  pymn_cash="1000.00", fills={"20261013": [base.fill("AAA", base.SELL, 3, "110.0000")]},
                  day_trades={"20261013": [base.day_trade("AAA", sold=3, sell_amount="330.00", fees="0.83")]},
                  detail=dict(base.SALE_PENDING), ledger=dict(LEDGER if ledger is None else ledger))
    values.update(changes)
    return LedgerBroker(**values)


class Oct23ReplayTests(unittest.TestCase):
    """The 2026-10-23 06:15 run against the 10/21 06:15:04 record with the diagnosis balances: order-available
    82.93 at the record, the 10/21 session settles net +150.03 (fees included), the 10/22 withdrawal of 82.93;
    ust21132 USD 10/20 82.94 and 10/22 150.04, KRW 0."""

    RECORD = orddt.Oct23ReplayTests.RECORD
    NOW = orddt.Oct23ReplayTests.NOW

    def replay(self, ledger_rows=None):
        fills, errors = core.parse_fills([orddt.daily_read("20261020", []), orddt.daily_read("20261021", orddt.OCT21),
                                          orddt.daily_read("20261022", []), orddt.daily_read("20261023", [])])
        day_trades = [{"operation": "account_day_trades_read", "bridge_status": "PASS",
                       "request_params": {"base_dt": "20261021"}, "pagination": {"complete": True}, "data": [
                           base.day_trade("MVLL", sold=159, sell_amount="3180.00"),
                           base.day_trade("NBIS", sold=13, sell_amount="1300.00"),
                           base.day_trade("SOXL", bought=6, buy_amount="306.00", sold=82, sell_amount="10920.00"),
                           base.day_trade("BE", bought=28, buy_amount="2809.00"),
                           base.day_trade("LITE", bought=9, buy_amount="12120.00")]}]
        # Gross sell 15400.00 / buy 15235.00; settled with fees 15392.30 / 15242.27 (net +150.03).
        slots = [{"slot": "d1", "settlement_date": date(2026, 10, 23), "SELL": Decimal("15392.30"),
                  "BUY": Decimal("15242.27")}]
        calls = []

        def ledger(baseline_at):
            calls.append(baseline_at)
            days = core.ledger_days(CALENDAR, baseline_at=baseline_at, snapshot_at=self.NOW)
            rows = ledger_rows or {"20261020": [ledger_row("82.94")], "20261022": [ledger_row("150.04")]}
            return {"days": days, "results": [ledger_read(key, value) for key, value in rows.items()]}

        result = core.explain_change(
            baseline_holdings={"MVLL": 159, "NBIS": 13, "SOXL": 100}, baseline_time=self.RECORD,
            cash_baseline={"cash": Decimal("82.93"), "at": self.RECORD, "reason": None,
                           "reference": {"status": "OK", "source": "TEST_ONLY"}},
            broker_holdings={"SOXL": 24, "BE": 28, "LITE": 9}, broker_cash=Decimal("150.03"),
            fills=fills, fill_errors=errors, day_trade_results=day_trades, rows=[], slots=slots, slot_errors=[],
            open_order_count=0, now=self.NOW, table=cfe.load_classification(), outflow_ledger=ledger)
        return result, calls

    def test_the_ledger_days_are_the_last_closed_us_sessions(self):
        self.assertEqual(core.ledger_days(CALENDAR, baseline_at=self.RECORD, snapshot_at=self.NOW),
                         (date(2026, 10, 20), date(2026, 10, 22)))

    def test_withdrawal_matched_by_the_ledger_passes_as_unverified_outflow(self):
        result, calls = self.replay()
        self.assertEqual(calls, [self.RECORD])
        self.assertEqual(result["I2"]["status"], "PASS")
        i3 = result["I3"]
        self.assertEqual((i3["status"], i3["reasons"]), ("PASS", []))
        self.assertEqual((i3["fill_cash_usd"], i3["unexplained_usd"]), ("150.03", "-82.93"))
        self.assertEqual(i3["unverified_outflow_usd"], "82.93")
        self.assertEqual(i3["unverified_outflow_basis"], {
            "base_before": "2026-10-20", "base_after": "2026-10-22", "fx_entr_before_usd": "82.94",
            "fx_entr_after_usd": "150.04", "won_entr_before": "0", "won_entr_after": "0",
            "sessions": ["2026-10-21"], "fill_cash_usd": "150.03", "flow_cash_usd": "0.00",
            "ledger_residual_usd": "-82.93", "snapshot_residual_usd": "-82.93"})

    def test_without_the_ledger_callback_the_old_hold_stays(self):
        # recon-dt's replay (no outflow_ledger, as every existing caller): unchanged.
        held = orddt.Oct23ReplayTests("test_quantities_pass_and_only_the_withdrawal_holds").replay()
        self.assertEqual(held["I3"]["reasons"], ["CASH_CHANGE_NOT_EXPLAINED:-82.93"])
        self.assertNotIn("unverified_outflow_usd", held["I3"])


class OutflowRuleTests(unittest.TestCase):
    """unverified_outflow by itself: each condition alone holds."""

    DAYS = (date(2026, 10, 12), date(2026, 10, 13))

    def judge(self, *, residual="-82.93", baseline="1000.00", before="1000.01", after="1246.25",
              won_before="0", won_after="0", window=None, ledger=None):
        ledger = ledger or {"days": self.DAYS, "results": [
            ledger_read("20261012", [ledger_row(before, won_before)]),
            ledger_read("20261013", [ledger_row(after, won_after)])]}
        return core.unverified_outflow(
            residual=Decimal(residual), baseline_cash=Decimal(baseline), trades=Decimal("329.17"),
            flows=Decimal("0"), window=window if window is not None else [{"session_date": "2026-10-13"}],
            ledger=ledger)

    def test_match_within_five_cents_passes_and_six_cents_holds(self):
        self.assertEqual(self.judge()[0]["unverified_outflow_usd"], "82.93")
        self.assertEqual(self.judge(after="1246.20")[0]["unverified_outflow_basis"]["ledger_residual_usd"], "-82.98")
        self.assertEqual(self.judge(after="1246.19"), (None, ["UNVERIFIED_OUTFLOW_NOT_MATCHED:-82.93:-82.99"]))
        self.assertEqual(self.judge(after="1246.31"), (None, ["UNVERIFIED_OUTFLOW_NOT_MATCHED:-82.93:-82.87"]))

    def test_ledger_without_an_outflow_holds(self):
        # R and L agree but L is within the tolerance: the ledger shows no outflow.
        self.assertEqual(self.judge(residual="-1.02", after="1328.18"),
                         (None, ["UNVERIFIED_OUTFLOW_NOT_MATCHED:-1.02:-1.00"]))

    def test_fill_session_outside_the_ledger_days_holds(self):
        for session in ("2026-10-12", "2026-10-14"):
            with self.subTest(session=session):
                self.assertEqual(self.judge(window=[{"session_date": "2026-10-13"}, {"session_date": session}]),
                                 (None, [f"UNVERIFIED_OUTFLOW_SPAN_MISMATCH:{session}"]))

    def test_outflow_above_the_baseline_order_available_cash_holds(self):
        self.assertEqual(self.judge(residual="-1200.00", baseline="1000.00", after="129.18"),
                         (None, ["UNVERIFIED_OUTFLOW_ABOVE_BASELINE_CASH:1200.00:1000.00"]))

    def test_krw_deposit_rise_holds(self):
        self.assertEqual(self.judge(won_after="120000"), (None, ["UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:0:120000"]))
        # A KRW deposit that fell or stayed does not hold.
        self.assertIsNotNone(self.judge(won_before="5000", won_after="0")[0])

    def test_unreadable_ledger_holds(self):
        cases = {
            "failed read": ([ledger_read("20261012", [ledger_row("1000.01")]),
                             ledger_read("20261013", [], status="KIWOOM_API_RESPONSE_ERROR")],
                            "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261013"),
            "missing read": ([ledger_read("20261012", [ledger_row("1000.01")])],
                             "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261013"),
            "no USD row": ([ledger_read("20261012", [ledger_row("1000.01")]),
                            ledger_read("20261013", [ledger_row("1.00", currency="KRW")])],
                           "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261013:USD_ROW"),
            "unreadable value": ([ledger_read("20261012", [ledger_row("")]),
                                  ledger_read("20261013", [ledger_row("1246.25")])],
                                 "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261012:VALUE"),
            "no KRW value": ([ledger_read("20261012", [{"crnc_code": "USD", "fx_entr": "1000.01", "won_entr": None}]),
                              ledger_read("20261013", [ledger_row("1246.25")])],
                             "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261012:VALUE"),
        }
        for name, (results, reason) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.judge(ledger={"days": self.DAYS, "results": results}), (None, [reason]))
        self.assertEqual(self.judge(ledger={"reason": "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:CALENDAR"}),
                         (None, ["UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:CALENDAR"]))

    def test_ledger_days_fail_closed(self):
        record, now = base.NOW - timedelta(days=1), base.NOW
        self.assertEqual(core.ledger_days(CALENDAR, baseline_at=record, snapshot_at=now),
                         (date(2026, 10, 12), date(2026, 10, 13)))
        short = dict(CALENDAR, identity={"coverage_start": "2026-01-01", "coverage_end": "2026-10-12"})
        self.assertEqual(core.ledger_days(short, baseline_at=record, snapshot_at=now),
                         "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:CALENDAR_COVERAGE")
        # Two reads within one U.S. evening: no session closed in between.
        self.assertEqual(core.ledger_days(CALENDAR, baseline_at=now - timedelta(hours=1), snapshot_at=now),
                         "UNVERIFIED_OUTFLOW_SPAN_MISMATCH:NO_SESSION_BETWEEN:2026-10-13")


class OutflowRunTests(base.Workspace):
    """Through the auto run (reconcile_auto -> run_auto) with the operating calendar patched."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(core, "production_calendar", return_value=CALENDAR)
        self.calendar = patcher.start()
        self.addCleanup(patcher.stop)

    def test_withdrawal_is_recorded_with_a_warning_and_no_hwm_adjustment(self):
        broker = withdrawal_broker()
        result = self.auto(broker)
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(result["invariants"]["I1"], {"status": "PASS", "reasons": []})
        i3 = result["invariants"]["I3"]
        self.assertEqual((i3["status"], i3["unexplained_usd"], i3["unverified_outflow_usd"]), ("PASS", "-82.93", "82.93"))
        self.assertEqual((i3["unverified_outflow_basis"]["base_before"], i3["unverified_outflow_basis"]["base_after"]),
                         ("2026-10-12", "2026-10-13"))
        self.assertEqual(own_warnings(result),["UNVERIFIED_EXTERNAL_OUTFLOW:82.93"])
        self.assertEqual(broker.ledger_requests(), [
            {"operation": core.LEDGER_OPERATION, "params": {"base_dt": "20261012"}},
            {"operation": core.LEDGER_OPERATION, "params": {"base_dt": "20261013"}}])
        # The declaration is the ordinary one: no new status, no HWM adjustment.
        self.assertEqual(result["cash_flow_evidence"]["declaration_status"], "NO_EXTERNAL_FLOW")
        self.assertEqual(result["cash_flow_evidence"]["hwm_adjustment_usd"],
                         self.auto(base.sale_broker())["cash_flow_evidence"]["hwm_adjustment_usd"])
        self.assertEqual(result["would_apply"]["available_cash_usd"], 1246.24)

    def test_apply_records_the_cash_and_keeps_the_declaration(self):
        result = self.auto(withdrawal_broker(), mode="apply")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertIsNotNone(result["applied"])
        entry = self.ledger_entries()[-1]
        self.assertEqual(entry["confirmation_method"], "AUTO_CORE_INVARIANTS")
        self.assertEqual(entry["cash_flow_declaration"]["declaration_status"], "NO_EXTERNAL_FLOW")
        self.assertEqual(entry["cash_flow_declaration"]["new_external_net_usd"], "0.00")
        self.assertEqual(entry["auto_core"]["invariants"]["I3"]["unverified_outflow_usd"], "82.93")
        state = base.load_json(self.state_path)
        self.assertEqual(state["available_cash_usd"], 1246.24)

    def test_cash_within_tolerance_makes_no_ledger_read(self):
        for cash in ("1329.17", "1328.17", "1330.17"):
            with self.subTest(cash=cash):
                broker = withdrawal_broker(ord_cash=cash)
                result = self.auto(broker)
                self.assertEqual(result["status"], "OK", result["reasons"])
                self.assertEqual(broker.ledger_requests(), [])
                self.assertNotIn("unverified_outflow_usd", result["invariants"]["I3"])
                self.assertEqual(own_warnings(result),[])
        self.calendar.assert_not_called()

    def test_inflow_is_never_admitted(self):
        # R = +50 with a ledger that shows +50 too: still CASH_CHANGE_NOT_EXPLAINED, and nothing is read.
        broker = withdrawal_broker(ord_cash="1379.17", ledger={"20261012": [ledger_row("1000.01")],
                                                               "20261013": [ledger_row("1379.18")]})
        result = self.auto(broker)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["invariants"]["I3"]["reasons"], ["CASH_CHANGE_NOT_EXPLAINED:50.00"])
        self.assertEqual(broker.ledger_requests(), [])
        self.assertIsNone(result["would_apply"])

    def test_mismatch_holds_and_writes_nothing(self):
        before = self.snapshot_files()
        broker = withdrawal_broker(ledger={"20261012": [ledger_row("1000.01")], "20261013": [ledger_row("1246.19")]})
        result = self.auto(broker, mode="apply")
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["invariants"]["I3"]["reasons"],
                         ["CASH_CHANGE_NOT_EXPLAINED:-82.93", "UNVERIFIED_OUTFLOW_NOT_MATCHED:-82.93:-82.99"])
        self.assertIsNone(result["applied"])
        self.assertEqual(own_warnings(result),[])
        self.assertEqual(self.snapshot_files(), before)

    def test_failed_or_no_record_ledger_read_holds_outside_i1(self):
        key = (core.LEDGER_OPERATION, '{"base_dt": "20261013"}')
        cases = {"no records (20)": dict(failing={key: True}),
                 "no USD row": dict(ledger={"20261012": [ledger_row("1000.01")], "20261013": []})}
        reasons = {"no records (20)": "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261013",
                   "no USD row": "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261013:USD_ROW"}
        for name, changes in cases.items():
            with self.subTest(name):
                result = self.auto(withdrawal_broker(**changes))
                self.assertEqual(result["status"], "HOLD")
                self.assertEqual(result["invariants"]["I1"]["status"], "PASS")
                self.assertEqual(result["invariants"]["I3"]["reasons"],
                                 ["CASH_CHANGE_NOT_EXPLAINED:-82.93", reasons[name]])

    def test_reader_or_calendar_failure_holds(self):
        class Broken(LedgerBroker):
            def data(self, request):
                if request["operation"] == core.LEDGER_OPERATION:
                    raise BridgeError("KIWOOM_API_UNAVAILABLE")
                return super().data(request)

        values = dict(holdings=[base.holding("AAA", 7, settled=10), base.holding("BBB", 5)], ord_cash=WITHDRAWN_CASH,
                      pymn_cash="1000.00", fills={"20261013": [base.fill("AAA", base.SELL, 3, "110.0000")]},
                      day_trades={"20261013": [base.day_trade("AAA", sold=3, sell_amount="330.00", fees="0.83")]},
                      detail=dict(base.SALE_PENDING))
        result = self.auto(Broken(**values))
        self.assertEqual(result["invariants"]["I3"]["reasons"][-1], "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:READ_FAILED")
        self.calendar.side_effect = ValueError("SESSION_CALENDAR_UNAVAILABLE:TEST")
        broker = withdrawal_broker()
        result = self.auto(broker)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["invariants"]["I3"]["reasons"][-1], "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:CALENDAR")
        self.assertEqual(broker.ledger_requests(), [])

    def test_another_i3_reason_keeps_the_exception_off(self):
        # No day-trade row: FILL_AMOUNT_UNAVAILABLE, so the sale is not counted and R = 1246.24 - 1000.00 = +246.24,
        # an inflow: the outflow branch is not entered and nothing is read.
        broker = withdrawal_broker(day_trades={})
        result = self.auto(broker)
        self.assertEqual(result["status"], "HOLD")
        reasons = result["invariants"]["I3"]["reasons"]
        self.assertIn("FILL_AMOUNT_UNAVAILABLE:2026-10-13:AAA", reasons)
        self.assertFalse(any(reason.startswith("UNVERIFIED_OUTFLOW") for reason in reasons))
        self.assertEqual(broker.ledger_requests(), [])
        open_orders = withdrawal_broker(open_items=[{"crnc_code": "USD", "stk_cd": "BBB", "ord_qty": "1",
                                                     "ord_remnq": "1", "slby_tp": "2"}])
        held = self.auto(open_orders)
        self.assertEqual(held["status"], "HOLD")
        self.assertIn("OPEN_ORDERS_PRESENT:1", held["invariants"]["I3"]["reasons"])
        self.assertEqual(open_orders.ledger_requests(), [])

    def test_krw_rise_holds(self):
        broker = withdrawal_broker(ledger={"20261012": [ledger_row("1000.01", "0")],
                                           "20261013": [ledger_row("1246.25", "110000")]})
        result = self.auto(broker)
        self.assertEqual(result["invariants"]["I3"]["reasons"][-1], "UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:0:110000")

    def test_compare_check_uses_the_same_rule_and_one_read(self):
        baseline = {"holdings": {"AAA": 10, "BBB": 5}, "available_cash_usd": 1000.0, "as_of_timestamp": base.RECORD}
        broker = withdrawal_broker()
        result = self.auto(broker, baseline=baseline)
        self.assertEqual(result["compare_check"], {"explained": True, "reasons": []})
        self.assertEqual(len(broker.ledger_requests()), 2)


class BridgeReadTests(unittest.TestCase):
    def test_ust21132_is_a_dated_read_only_inquiry(self):
        self.assertEqual(bridge.ACCOUNT_APIS[core.LEDGER_OPERATION], ("ust21132", "/api/us/acnt"))
        self.assertFalse(any(term in f"{core.LEDGER_OPERATION} ust21132 /api/us/acnt" for term in BLOCKED_TERMS))
        self.assertEqual(bridge.validate_request({"operation": core.LEDGER_OPERATION,
                                                  "params": {"base_dt": "20261022"}}),
                         {"operation": core.LEDGER_OPERATION, "params": {"base_dt": "20261022"}})
        self.assertEqual(bridge.request_body({"operation": core.LEDGER_OPERATION, "params": {"base_dt": "20261022"}}),
                         {"base_dt": "20261022"})
        for bad in ({"operation": core.LEDGER_OPERATION},
                    {"operation": core.LEDGER_OPERATION, "params": {"base_dt": "2026-10-22"}},
                    {"operation": core.LEDGER_OPERATION, "params": {"base_dt": "20261022", "acnt_no": "1"}}):
            with self.subTest(bad=bad):
                with self.assertRaises(BridgeError):
                    bridge.validate_request(bad)
        self.assertEqual(bridge.SAFE_FIELDS[core.LEDGER_OPERATION], ("crnc_code", "fx_entr", "won_entr"))
        # "No records" is not promoted to an empty PASS for this read: it stays a failure (I3 holds).
        self.assertNotIn(core.LEDGER_OPERATION, bridge.NO_DATA_PASS_MESSAGE_CODES)

    @staticmethod
    def read(operation, body):
        session = {"client": SimpleNamespace(fetch_page=mock.Mock(return_value=SimpleNamespace(
                       body=body, continuation={"cont_yn": "N", "next_key": None}))),
                   "pacer": mock.Mock(), "maximum_attempts": 1, "maximum_history_pages": 1,
                   "immediate_open_failure_types": set(), "retryable_failure_types": set()}
        return bridge._read_pages(session, operation, {"base_dt": "20261022"})[0]

    def test_the_top_level_krw_deposit_is_attached_to_each_row(self):
        # The real ust21132 shape (2026-10-23): won_entr at depth 0, the currency rows carry no won_entr.
        body = {"won_entr": "000000000000", "tot_evlt_amt": "1", "return_code": 0, "return_msg": "OK",
                "result_list": [{"crnc_code": "USD", "fx_entr": "150.02", "evlt_amt": "1", "crnc_rt": "1",
                                 "chg_entr": "1", "chg_evlt_amt": "1", "evlt_amt_wght": "1"}]}
        rows = self.read(core.LEDGER_OPERATION, body)
        self.assertEqual(rows, [{"crnc_code": "USD", "fx_entr": "150.02", "won_entr": "000000000000"}])
        balance, reason = core.ledger_balance([ledger_read("20261022", rows)], date(2026, 10, 22))
        self.assertEqual((balance, reason), ({"fx_entr": Decimal("150.02"), "won_entr": Decimal("0")}, None))

    def test_without_a_top_level_krw_deposit_the_row_value_stays_none(self):
        # A won_entr inside a row is not used: only the body's top level counts, and its absence holds.
        body = {"return_code": 0, "result_list": [{"crnc_code": "USD", "fx_entr": "150.02", "won_entr": "5"}]}
        rows = self.read(core.LEDGER_OPERATION, body)
        self.assertEqual(rows, [{"crnc_code": "USD", "fx_entr": "150.02", "won_entr": None}])
        self.assertEqual(core.ledger_balance([ledger_read("20261022", rows)], date(2026, 10, 22)),
                         (None, "UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261022:VALUE"))
        # Other operations do not take top-level fields.
        other = self.read("account_deposit_read", {"won_entr": "7", "return_code": 0,
                                                   "result_list": [{"crnc_code": "USD", "fc_ord_alowa": "1.00"}]})
        self.assertEqual(other, [{"crnc_code": "USD", "crnc_nm": None, "fc_entra": None, "fc_pymn_alowa": None,
                                  "fc_ord_alowa": "1.00"}])

    def test_the_ledger_read_is_not_an_i1_read(self):
        plan = core.plan_reads(recorded_at=base.NOW - timedelta(days=1), evidence_from=date(2026, 10, 13),
                               now=base.NOW)
        self.assertNotIn(core.LEDGER_OPERATION, {request["operation"] for request in core.dated_requests(plan)})
        self.assertNotIn(core.LEDGER_OPERATION, core.I1_SNAPSHOT_OPERATIONS + core.SNAPSHOT_OPERATIONS)


if __name__ == "__main__":
    unittest.main()
