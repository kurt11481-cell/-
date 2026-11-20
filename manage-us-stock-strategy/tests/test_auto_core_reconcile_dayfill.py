"""recon-dayfill (K3, user card 2026-11-20): a Kiwoom day-session fill counts on its order day.

ust21150 ord_dt is the U.S. (ET) order day D. A fill lies after D-1 20:00 ET and not after D 20:00 ET; one before
D 04:00 ET is a Kiwoom day-session fill (segment DAY_SESSION) whose ord_dt is its KST fill day. Its amounts still
bind to the ust21610 read of D (else FILL_AMOUNT_UNAVAILABLE, fail closed). Settlement slots and rows dated on or
before max(last KST fill day, D + 1 day) belong to sessions before the baseline.

Pre-registered tests T1-T12 of docs/claude/recon-dayfill-k3-proposal-2026-11-20.md section 4, 3rd edition
(T3 order time 10:00:01). The 2026-11-19 SOXL row replays the observation behind the 2026-11-20 HOLD; account data, record
times and cash amounts other than the observed ones are synthetic (TEST_ONLY). No network, no Kiwoom runtime.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_reconcile as core  # noqa: E402
import cash_flow_evidence as cfe  # noqa: E402
import test_auto_core as base  # noqa: E402
from test_auto_core_reconcile_orddt import BUY, SELL, daily_read, kst, row  # noqa: E402

# The observed 2026-11-19 row: SOXL 74 sold in the Kiwoom day session, ord_dt 20261119 (= 22:44 ET on 11/18).
SOXL_DAY = row("0000001", "SOXL", SELL, 74, "51.0000", "11:34:06", "12:44:27")
REGULAR_KEYS = {"order_date", "ticker", "side", "quantity", "price", "filled_at_kst", "session_date"}


def day_trades(base_dt, rows):
    return {"operation": "account_day_trades_read", "bridge_status": "PASS", "request_params": {"base_dt": base_dt},
            "pagination": {"complete": True}, "data": rows}


def slot(name, day, sell="0.00", buy="0.00"):
    return {"slot": name, "settlement_date": day, "SELL": Decimal(sell), "BUY": Decimal(buy)}


def explain(*, record, now, baseline_holdings, broker_holdings, reads, trades, slots, baseline_cash, broker_cash):
    fills, errors = core.parse_fills(reads)
    errors += core.fills_after_snapshot(fills, now)
    return core.explain_change(
        baseline_holdings=baseline_holdings, baseline_time=record,
        cash_baseline={"cash": Decimal(baseline_cash), "at": record, "reason": None,
                       "reference": {"status": "OK", "source": "TEST_ONLY"}},
        broker_holdings=broker_holdings, broker_cash=Decimal(broker_cash), fills=fills, fill_errors=errors,
        day_trade_results=trades, rows=[], slots=slots, slot_errors=[], open_order_count=0, now=now,
        table=cfe.load_classification())


class DayFillWindowTests(unittest.TestCase):
    def parse(self, ord_dt, rows):
        return core.parse_fills([daily_read(ord_dt, rows)])

    def test_t1_observed_nov19_soxl_day_session_fill(self):
        fills, errors = self.parse("20261119", [SOXL_DAY])
        self.assertEqual(errors, [])
        self.assertEqual(len(fills), 1)
        self.assertEqual((fills[0]["filled_at_kst"], fills[0]["session_date"], fills[0]["segment"]),
                         ("2026-11-19T12:44:27+09:00", "2026-11-19", "DAY_SESSION"))
        self.assertEqual(datetime.fromisoformat(fills[0]["filled_at_kst"]).astimezone(core.ET).isoformat(),
                         "2026-11-18T22:44:27-05:00")
        self.assertEqual(core.day_trade_requests(fills),
                         [{"operation": "account_day_trades_read", "params": {"base_dt": "20261119"}}])

    def test_t2_est_upper_end_is_the_after_hours_close(self):
        # 10:00 KST on 11/03 = 20:00 ET on 11/02: the closed upper end (after-hours close), not a day-session fill.
        fills, errors = self.parse("20261102", [row("1", "AAA", SELL, 1, "10.0000", "09:59:00", "10:00:00")])
        self.assertEqual(errors, [])
        self.assertEqual(fills[0]["filled_at_kst"], "2026-11-03T10:00:00+09:00")
        self.assertNotIn("segment", fills[0])

    def test_t3_est_one_second_after_the_lower_end(self):
        # 10:00:01 KST on 11/02 = 20:00:01 ET on 11/01 (EST): just inside the window, a day-session fill.
        fills, errors = self.parse("20261102", [row("1", "AAA", SELL, 1, "10.0000", "10:00:01", "10:00:01")])
        self.assertEqual(errors, [])
        self.assertEqual(len(fills), 1)
        self.assertEqual((fills[0]["filled_at_kst"], fills[0]["segment"]),
                         ("2026-11-02T10:00:01+09:00", "DAY_SESSION"))

    def test_t3b_est_day_session_fill_after_et_midnight(self):
        # 15:00 KST on 11/02 = 01:00 ET on 11/02: a day-session fill whose ET date is D itself.
        fills, errors = self.parse("20261102", [row("1", "AAA", BUY, 1, "10.0000", "14:00:00", "15:00:00")])
        self.assertEqual(errors, [])
        self.assertEqual((fills[0]["filled_at_kst"], fills[0]["session_date"], fills[0]["segment"]),
                         ("2026-11-02T15:00:00+09:00", "2026-11-02", "DAY_SESSION"))

    def test_t4_edt_one_second_after_the_lower_end(self):
        # 09:00:01 KST on 10/21 = 20:00:01 ET on 10/20 (EDT): inside, a day-session fill.
        fills, errors = self.parse("20261021", [row("1", "AAA", BUY, 1, "10.0000", "09:00:01", "09:00:01")])
        self.assertEqual(errors, [])
        self.assertEqual((fills[0]["filled_at_kst"], fills[0]["segment"]),
                         ("2026-10-21T09:00:01+09:00", "DAY_SESSION"))

    def test_t5_day_session_order_after_fill_holds(self):
        later = [row("0000001", "SOXL", SELL, 74, "51.0000", "12:50:00", "12:44:27")]
        self.assertEqual(self.parse("20261119", later), ([], ["FILL_TIME_INVALID:20261119:0"]))

    def test_t6_day_session_fill_later_than_the_snapshot_holds(self):
        fills, _ = self.parse("20261119", [SOXL_DAY])
        self.assertEqual(core.fills_after_snapshot(fills, kst("2026-11-19T12:00:00")),
                         ["FILL_AFTER_SNAPSHOT:20261119:SOXL:SELL"])
        self.assertEqual(core.fills_after_snapshot(fills, kst("2026-11-20T06:15:00")), [])

    def test_t10_regular_and_after_hours_fills_keep_their_exact_item(self):
        # Regular and after-hours items carry no segment key: byte-for-byte the item before recon-dayfill.
        rows = [row("1", "AAA", SELL, 1, "10.0000", "22:22:07", "22:22:23"),
                row("2", "BBB", BUY, 1, "10.0000", "06:13:17", "06:13:18"),
                row("3", "CCC", BUY, 1, "10.0000", "16:59:00", "17:00:00")]  # 17:00 KST 10/21 = 04:00 ET (EDT)
        fills, errors = self.parse("20261021", rows)
        self.assertEqual(errors, [])
        self.assertEqual([set(item) for item in fills], [REGULAR_KEYS] * 3)
        self.assertEqual(sorted(item["filled_at_kst"] for item in fills),
                         ["2026-10-21T17:00:00+09:00", "2026-10-21T22:22:23+09:00", "2026-10-22T06:13:18+09:00"])


class Nov20ReplayTests(unittest.TestCase):
    """The 2026-11-20 06:15 run: rev 43 recorded SOXL 103 before the 11/19 day-session sale of 74; the snapshot
    holds 29 and the d2 slot (KST 11/23) the sale proceeds 3771.28 (= 3774.00 - 2.72)."""

    RECORD = kst("2026-11-19T06:15:04")  # rev 43 (synthetic time, before the fill)
    NOW = kst("2026-11-20T06:15:00")
    READS = [daily_read("20261119", [SOXL_DAY]), daily_read("20261120", [])]
    SLOTS = [slot("d1", date(2026, 11, 20)), slot("d2", date(2026, 11, 23), sell="3771.28")]

    def run_replay(self, trades):
        return explain(record=self.RECORD, now=self.NOW, baseline_holdings={"SOXL": 103},
                       broker_holdings={"SOXL": 29}, reads=self.READS, trades=trades, slots=self.SLOTS,
                       baseline_cash="1000.00", broker_cash="4771.28")

    def test_t7_quantity_and_cash_pass(self):
        result = self.run_replay([day_trades("20261119", [base.day_trade("SOXL", sold=74, sell_amount="3774.00")])])
        self.assertEqual(result["I2"], {"status": "PASS", "reasons": [], "fills_counted": 1})
        self.assertEqual(result["holdings_change"], [{"ticker": "SOXL", "recorded": 103, "broker": 29,
                                                      "fills_net": -74}])
        self.assertEqual(result["I3"]["status"], "PASS", result["I3"]["reasons"])
        self.assertLessEqual(abs(Decimal(result["I3"]["unexplained_usd"])), Decimal("1.00"))
        self.assertEqual([(item["settlement_date"], item["sessions"]) for item in result["I3"]["settlements"]],
                         [("2026-11-23", ["2026-11-19"])])
        self.assertEqual(result["I3"]["fill_cash_usd"], "3771.28")

    def test_t8_day_session_fill_without_its_day_trade_row_holds(self):
        result = self.run_replay([day_trades("20261119", [])])
        self.assertEqual(result["I2"]["status"], "PASS")
        self.assertEqual(result["I3"]["status"], "FAIL")
        self.assertIn("FILL_AMOUNT_UNAVAILABLE:2026-11-19:SOXL", result["I3"]["reasons"])

    def test_t9_after_the_rev44_record_the_reread_row_is_not_counted(self):
        # rev 44 (manual reconciliation) recorded 29 at 2026-11-19T23:38:07Z; the 11/21 run reads ord_dt 20261119
        # again. The sale is before the record: nothing counts, and the pending 3771.28 is already in its cash.
        record = datetime.fromisoformat("2026-11-19T23:38:07+00:00")
        result = explain(record=record, now=kst("2026-11-21T06:15:00"), baseline_holdings={"SOXL": 29},
                         broker_holdings={"SOXL": 29},
                         reads=[daily_read("20261119", [SOXL_DAY]), daily_read("20261120", []),
                                daily_read("20261121", [])],
                         trades=[], slots=[slot("d1", date(2026, 11, 23), sell="3771.28")],
                         baseline_cash="4771.28", broker_cash="4771.28")
        self.assertEqual(result["I2"], {"status": "PASS", "reasons": [], "fills_counted": 0})
        self.assertEqual(result["I3"]["status"], "PASS", result["I3"]["reasons"])
        self.assertEqual((result["I3"]["fill_cash_usd"], result["I3"]["settlements"]), ("0.00", []))
        self.assertLessEqual(abs(Decimal(result["I3"]["unexplained_usd"])), Decimal("1.00"))


class SettlementBaseDayTests(unittest.TestCase):
    """The settlement base day max(last KST fill day, session + 1 day): a slot of the session before the baseline
    on KST D+1 is never counted (T11 day session, T12 regular session filled before KST midnight)."""

    RECORD = kst("2026-11-17T06:15:04")
    NOW = kst("2026-11-18T06:15:00")

    def replay(self, fill_row):
        # Session 11/16 (before the record) settles on KST 11/18; session 11/17 on KST 11/19.
        return explain(record=self.RECORD, now=self.NOW, baseline_holdings={"AAA": 10}, broker_holdings={"AAA": 6},
                       reads=[daily_read("20261117", [fill_row])],
                       trades=[day_trades("20261117", [base.day_trade("AAA", sold=4, sell_amount="400.00")])],
                       slots=[slot("d0", date(2026, 11, 18), sell="250.00", buy="120.00"),
                              slot("d1", date(2026, 11, 19), sell="399.00")],
                       baseline_cash="1000.00", broker_cash="1399.00")

    def check(self, result, segment):
        self.assertEqual(result["I2"]["status"], "PASS", result["I2"]["reasons"])
        self.assertEqual(result["I3"]["status"], "PASS", result["I3"]["reasons"])
        self.assertEqual([(item["settlement_date"], item["sessions"]) for item in result["I3"]["settlements"]],
                         [("2026-11-19", ["2026-11-17"])])
        self.assertEqual(result["I3"]["fill_cash_usd"], "399.00")
        self.assertEqual([item.get("segment") for item in result["fills"]], [segment])

    def test_t11_day_session_only_skips_the_earlier_sessions_d_plus_1_slot(self):
        # 12:00 KST on 11/17 = 22:00 ET on 11/16: a day-session fill of the 11/17 session, last KST fill day 11/17.
        self.check(self.replay(row("1", "AAA", SELL, 4, "100.0000", "11:50:00", "12:00:00")), "DAY_SESSION")

    def test_t12_regular_fill_before_kst_midnight_skips_the_s_plus_1_slot(self):
        # 23:40 KST on 11/17 = 09:40 ET on 11/17 (regular session), last KST fill day 11/17.
        self.check(self.replay(row("1", "AAA", SELL, 4, "100.0000", "23:35:00", "23:40:00")), None)


if __name__ == "__main__":
    unittest.main()
