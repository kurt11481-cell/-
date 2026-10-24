"""recon-dt commit 1: ust21150 ord_dt is the U.S. (ET) order day.

The KST day of a fill is the one of {ord_dt, ord_dt + 1} that puts cntr_time within ord_dt 04:00-20:00 ET; the
order clock lies after ord_dt - 1 20:00 ET and not after the fill. Anything else holds (fail closed). The rows
replay the 2026-10-21 ET order day behind the 2026-10-22/23 HOLDs (docs/claude/recon-hold-2026-10-23.md); account
data and amounts are synthetic (TEST_ONLY). No network, no Kiwoom runtime.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_reconcile as core  # noqa: E402
import cash_flow_evidence as cfe  # noqa: E402
import test_auto_core as base  # noqa: E402

SELL, BUY = "매도", "매수"  # Korean side names: sell, buy
KST = core.KST


def row(number, ticker, side, quantity, price, ord_time, cntr_time):
    return {"ord_no": number, "crnc_code": "USD", "stk_cd": ticker, "slby_tp_nm": side, "frgn_trde_tp": "LOC",
            "ord_qty": f"{quantity:012d}", "cntr_qty": f"{quantity:012d}", "cncl_qty": "000000000000",
            "ord_remnq": "000000000000", "ord_uv": price, "cntr_uv": price, "ord_time": ord_time,
            "cntr_time": cntr_time, "ord_stat_nm": "TEST", "rsrv_tp": "0"}


def daily_read(ord_dt, rows):
    return {"operation": "account_daily_fills_read", "bridge_status": "PASS", "request_params": {"ord_dt": ord_dt},
            "pagination": {"complete": True}, "data": rows}


def kst(text):
    return datetime.fromisoformat(text + "+09:00")


# The 2026-10-21 ET order day. NBIS and the second BE order have no order time in the diagnosis; theirs here are
# synthetic, shortly before the fill.
OCT21 = [
    row("0000001", "MVLL", SELL, 159, "20.0000", "06:13:17", "06:13:18"),
    row("0000002", "BE", BUY, 19, "100.0000", "06:13:46", "06:15:28"),
    row("0000003", "NBIS", SELL, 13, "100.0000", "06:20:00", "06:20:18"),
    row("0000004", "BE", BUY, 9, "101.0000", "06:40:00", "06:40:50"),
    row("0000005", "SOXL", SELL, 82, "50.0000", "22:22:07", "22:22:23"),
    row("0000006", "LITE", BUY, 9, "200.0000", "22:24:57", "22:24:57"),
    row("0000007", "SOXL", BUY, 6, "51.0000", "22:26:17", "22:26:43"),
]


class OrderDayIsUsDayTests(unittest.TestCase):
    def parse(self, ord_dt, rows):
        return core.parse_fills([daily_read(ord_dt, rows)])

    def test_oct21_after_hours_fills_fall_on_the_next_kst_day(self):
        fills, errors = self.parse("20261021", OCT21)
        self.assertEqual(errors, [])
        by_number = {item["ticker"] + str(item["quantity"]): item for item in fills}
        self.assertEqual({key: item["filled_at_kst"] for key, item in by_number.items()}, {
            "MVLL159": "2026-10-22T06:13:18+09:00", "BE19": "2026-10-22T06:15:28+09:00",
            "NBIS13": "2026-10-22T06:20:18+09:00", "BE9": "2026-10-22T06:40:50+09:00",
            "SOXL82": "2026-10-21T22:22:23+09:00", "LITE9": "2026-10-21T22:24:57+09:00",
            "SOXL6": "2026-10-21T22:26:43+09:00"})
        self.assertEqual({item["session_date"] for item in fills}, {"2026-10-21"})
        self.assertEqual({item["order_date"] for item in fills}, {"20261021"})
        # BE 19 was still open in the 10/22 06:15:07 snapshot: its fill is after it.
        self.assertGreater(kst(by_number["BE19"]["filled_at_kst"][:19]), kst("2026-10-22T06:15:07"))
        self.assertEqual(core.day_trade_requests(fills),
                         [{"operation": "account_day_trades_read", "params": {"base_dt": "20261021"}}])

    def test_after_the_oct21_record_every_fill_counts_including_mvll(self):
        fills, _ = self.parse("20261021", OCT21)
        after = core.fills_after(fills, kst("2026-10-21T06:15:04"))
        self.assertEqual({item["ticker"] for item in after}, {"MVLL", "BE", "NBIS", "SOXL", "LITE"})
        self.assertEqual(len(after), 7)
        # The 10/22 06:15:07 snapshot already held MVLL's sale (06:13:18) but not BE's buy.
        later = core.fills_after(fills, kst("2026-10-22T06:15:07"))
        self.assertEqual([(item["ticker"], item["quantity"]) for item in later], [("BE", 19), ("NBIS", 13), ("BE", 9)])

    def test_fill_after_kst_midnight_is_the_same_us_day(self):
        fills, errors = self.parse("20261021", [row("0000001", "AAA", BUY, 1, "10.0000", "23:59:58", "00:00:03")])
        self.assertEqual(errors, [])
        self.assertEqual((fills[0]["filled_at_kst"], fills[0]["session_date"]),
                         ("2026-10-22T00:00:03+09:00", "2026-10-21"))

    def test_winter_time_moves_the_kst_bounds_one_hour(self):
        # 2026-11-02 (EST, UTC-5): 20:00 ET = 10:00 KST on 11/03, 04:00 ET = 18:00 KST on 11/02.
        rows = [row("0000001", "AAA", SELL, 1, "10.0000", "08:29:00", "08:30:00"),
                row("0000002", "AAA", SELL, 1, "10.0000", "09:59:00", "10:00:00"),
                row("0000003", "AAA", SELL, 1, "10.0000", "18:00:00", "18:00:00")]
        fills, errors = self.parse("20261102", rows)
        self.assertEqual(errors, [])
        self.assertEqual(sorted(item["filled_at_kst"] for item in fills),
                         ["2026-11-02T18:00:00+09:00", "2026-11-03T08:30:00+09:00", "2026-11-03T10:00:00+09:00"])
        self.assertEqual({item["session_date"] for item in fills}, {"2026-11-02"})
        late = [row("0000004", "AAA", SELL, 1, "10.0000", "10:29:00", "10:30:00")]
        self.assertEqual(self.parse("20261102", late), ([], ["FILL_TIME_OUTSIDE_US_SESSION:20261102:0"]))
        early = [row("0000005", "AAA", SELL, 1, "10.0000", "17:59:00", "17:59:59")]
        self.assertEqual(self.parse("20261102", early), ([], ["FILL_TIME_OUTSIDE_US_SESSION:20261102:0"]))
        # Summer time (EDT, UTC-4): 09:30 KST on 10/22 is 20:30 ET on 10/21 (outside), 09:00 KST is 20:00 (inside).
        self.assertEqual(self.parse("20261021", [row("1", "AAA", SELL, 1, "10.0000", "08:00:00", "09:30:00")]),
                         ([], ["FILL_TIME_OUTSIDE_US_SESSION:20261021:0"]))
        self.assertEqual(self.parse("20261021", [row("1", "AAA", SELL, 1, "10.0000", "08:00:00", "09:00:00")])[1], [])

    def test_kiwoom_day_session_fill_holds(self):
        # 12:00 KST is 23:00 ET on either candidate day: outside every U.S. hour of the order day.
        rows = [row("0000001", "AAA", BUY, 1, "10.0000", "11:50:00", "12:00:00")]
        self.assertEqual(self.parse("20261021", rows), ([], ["FILL_TIME_OUTSIDE_US_SESSION:20261021:0"]))

    def test_order_after_fill_or_outside_its_window_holds(self):
        later = [row("0000001", "AAA", SELL, 1, "10.0000", "06:20:00", "06:13:18")]
        self.assertEqual(self.parse("20261021", later), ([], ["FILL_TIME_INVALID:20261021:0"]))
        # 08:00 KST on 10/21 is 19:00 ET on 10/20 (before 10/20 20:00 ET); 08:00 on 10/22 is after the fill.
        early = [row("0000001", "AAA", SELL, 1, "10.0000", "08:00:00", "22:30:00")]
        self.assertEqual(self.parse("20261021", early), ([], ["FILL_TIME_INVALID:20261021:0"]))
        missing = [row("0000001", "AAA", SELL, 1, "10.0000", "", "22:30:00")]
        self.assertEqual(self.parse("20261021", missing), ([], ["FILL_TIME_INVALID:20261021:0"]))

    def test_reserved_order_before_the_session_is_accepted(self):
        # 10:00 KST on 10/21 = 21:00 ET on 10/20: after 10/20 20:00 ET, so a reserved order for 10/21 stands.
        fills, errors = self.parse("20261021", [row("0000001", "AAA", BUY, 1, "10.0000", "10:00:00", "22:30:00")])
        self.assertEqual(errors, [])
        self.assertEqual(fills[0]["filled_at_kst"], "2026-10-21T22:30:00+09:00")

    def test_fill_later_than_the_snapshot_holds(self):
        fills, _ = self.parse("20261021", OCT21)
        self.assertEqual(core.fills_after_snapshot(fills, kst("2026-10-23T06:15:00")), [])
        self.assertEqual(core.fills_after_snapshot(fills, kst("2026-10-22T06:20:00")),
                         ["FILL_AFTER_SNAPSHOT:20261021:NBIS:SELL", "FILL_AFTER_SNAPSHOT:20261021:BE:BUY"])


class Oct23ReplayTests(unittest.TestCase):
    """The 2026-10-23 06:15 run against the 10/21 06:15:04 record: the fills now explain every quantity and
    their amounts bind to the 10/21 day-trade read; only the withdrawal (no evidence row, cashflow-api-gap) is
    left, so the run still holds and nothing is recorded."""

    RECORD = kst("2026-10-21T06:15:04")
    NOW = kst("2026-10-23T06:15:00")

    def replay(self):
        fills, errors = core.parse_fills([daily_read("20261020", []), daily_read("20261021", OCT21),
                                          daily_read("20261022", []), daily_read("20261023", [])])
        errors += core.fills_after_snapshot(fills, self.NOW)
        day_trades = [{"operation": "account_day_trades_read", "bridge_status": "PASS",
                       "request_params": {"base_dt": "20261021"}, "pagination": {"complete": True}, "data": [
                           base.day_trade("MVLL", sold=159, sell_amount="3180.00"),
                           base.day_trade("NBIS", sold=13, sell_amount="1300.00"),
                           base.day_trade("SOXL", bought=6, buy_amount="306.00", sold=82, sell_amount="4100.00"),
                           base.day_trade("BE", bought=28, buy_amount="2809.00"),
                           base.day_trade("LITE", bought=9, buy_amount="1800.00")]}]
        self.assertEqual(core.day_trade_requests(core.fills_after(fills, self.RECORD)),
                         [{"operation": "account_day_trades_read", "params": {"base_dt": "20261021"}}])
        # The 10/21 session settles on KST 10/23: gross sell 8580.00, buy 4915.00; settled with fees.
        slots = [{"slot": "d1", "settlement_date": date(2026, 10, 23), "SELL": Decimal("8571.42"),
                  "BUY": Decimal("4917.46")}]
        withdrawal = Decimal("82.93")
        return core.explain_change(
            baseline_holdings={"MVLL": 159, "NBIS": 13, "SOXL": 100}, baseline_time=self.RECORD,
            cash_baseline={"cash": Decimal("1000.00"), "at": self.RECORD, "reason": None,
                           "reference": {"status": "OK", "source": "TEST_ONLY"}},
            broker_holdings={"SOXL": 24, "BE": 28, "LITE": 9},
            broker_cash=Decimal("1000.00") + Decimal("8571.42") - Decimal("4917.46") - withdrawal,
            fills=fills, fill_errors=errors, day_trade_results=day_trades, rows=[], slots=slots, slot_errors=[],
            open_order_count=0, now=self.NOW, table=cfe.load_classification())

    def test_quantities_pass_and_only_the_withdrawal_holds(self):
        result = self.replay()
        self.assertEqual(result["I2"], {"status": "PASS", "reasons": [], "fills_counted": 7})
        self.assertEqual(result["I3"]["status"], "FAIL")
        self.assertEqual(result["I3"]["reasons"], ["CASH_CHANGE_NOT_EXPLAINED:-82.93"])
        self.assertFalse(any("FILL_AMOUNT_UNAVAILABLE" in reason for reason in result["I3"]["reasons"]))
        self.assertEqual([(item["settlement_date"], item["sessions"]) for item in result["I3"]["settlements"]],
                         [("2026-10-23", ["2026-10-21"])])
        self.assertEqual(result["I3"]["fill_cash_usd"], "3653.96")


class CorrectedDailyFixture(base.DailyTests):
    """test_auto_core's unseen-settlement streak scenario with the after-hours fill dated by its U.S. order day:
    AAA 3 sold in the after-hours of the U.S. 10/14 session (KST 10/15 07:07) carries ord_dt 20261014. Only the
    test below runs (load_tests); the inherited DailyTests tests run in test_auto_core."""

    @staticmethod
    def late(ord_dt="20261014"):
        return dict(holdings=[base.holding("AAA", 7, settled=10), base.holding("BBB", 5)], ord_cash="1329.17",
                    pymn_cash="1000.00",
                    fills={ord_dt: [base.fill("AAA", base.SELL, 3, "110.0000", order_no="0007",
                                              ord_time="06:50:00", cntr_time="07:07:00")]},
                    day_trades={"20261014": [base.day_trade("AAA", sold=3, sell_amount="330.00", fees="0.83")]},
                    detail={"d1_setl_dt": "20261019", "d1_usd_sell_excta": "0.00", "d1_usd_buy_excta": "0.00"})

    def test_after_hours_fill_dated_by_its_us_order_day_keeps_the_streak(self):
        late = self.late()
        days = [base.NOW + timedelta(days=offset) for offset in range(4)]
        brokers = [self.quiet(days[0]), self.quiet(days[1]),
                   base.FakeBroker(**late, retrieved=days[2] - timedelta(seconds=5)),
                   base.FakeBroker(**dict(late, holdings=[base.holding("AAA", 7), base.holding("BBB", 5)],
                                          pymn_cash="1329.17", detail={},
                                          history=[base.trade_row("20261016", "000000001", "AAA", base.SELL, 3,
                                                                  "330.00", "0.83", "329.17")]),
                                   retrieved=days[3] - timedelta(seconds=5))]
        results = [self.daily(broker, now=moment) for broker, moment in zip(brokers, days)]
        self.assertEqual([item["status"] for item in results], ["OK", "OK", "HOLD", "OK"],
                         [item["reasons"] for item in results])
        self.assertEqual([item["compare"]["streak"] for item in results], [0, 1, 1, 2])
        self.assertEqual(results[2]["reasons"], ["I3:SETTLEMENT_D0_NOT_SHOWN:2026-10-16"])
        self.assertEqual(results[3]["compare"]["basis"], "EXPLAINED_BY_FILLS")

    def test_the_kst_day_as_ord_dt_puts_the_fill_after_the_read_and_holds(self):
        # The old fixture's ord_dt (KST 10/15) now means U.S. 10/15: the fill would be KST 10/16 07:07, after
        # the KST 10/16 06:15 read.
        moment = base.NOW + timedelta(days=2)
        held = self.daily(base.FakeBroker(**self.late("20261015"), retrieved=moment - timedelta(seconds=5)), now=moment)
        self.assertEqual(held["status"], "HOLD")
        self.assertIn("I2:FILL_AFTER_SNAPSHOT:20261015:AAA:SELL", held["reasons"])
        self.assertIsNone(held["applied"])


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    for case in (OrderDayIsUsDayTests, Oct23ReplayTests):
        suite.addTests(loader.loadTestsFromTestCase(case))
    for name in ("test_after_hours_fill_dated_by_its_us_order_day_keeps_the_streak",
                 "test_the_kst_day_as_ord_dt_puts_the_fill_after_the_read_and_holds"):
        suite.addTest(CorrectedDailyFixture(name))
    return suite


if __name__ == "__main__":
    unittest.main()
