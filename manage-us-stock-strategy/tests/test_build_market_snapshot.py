from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_market_snapshot.py"
SPEC = importlib.util.spec_from_file_location("build_market_snapshot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MarketSnapshotBuilderTests(unittest.TestCase):
    def test_request_pacer_enforces_one_second_between_requests(self) -> None:
        now = [100.0]
        sleeps: list[float] = []

        def clock() -> float:
            return now[0]

        def sleeper(seconds: float) -> None:
            sleeps.append(seconds)
            now[0] += seconds

        pacer = MODULE.RequestPacer(1.0, clock=clock, sleeper=sleeper)
        pacer.wait()
        now[0] += 0.25
        pacer.wait()
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.75)

    def test_yfinance_frame_is_converted_without_auto_adjusting_raw_close(self) -> None:
        index = pd.date_range("2026-08-03", periods=3, freq="B")
        frame = pd.DataFrame(
            {
                "Open": [10.0, 11.0, 12.0],
                "High": [11.0, 12.0, 13.0],
                "Low": [9.0, 10.0, 11.0],
                "Close": [10.5, 11.5, 12.5],
                "Adj Close": [10.0, 11.0, 12.0],
                "Volume": [1000, 1100, 1200],
                "Dividends": [0.0, 0.5, 0.0],
                "Stock Splits": [0.0, 0.0, 2.0],
            },
            index=index,
        )
        result = MODULE.yfinance_frame_to_chart_result("TEST", frame)
        quote = result["indicators"]["quote"][0]
        self.assertEqual(quote["close"][-1], 12.5)
        self.assertEqual(result["indicators"]["adjclose"][0]["adjclose"][-1], 12.0)
        self.assertEqual(result["_provider"], "yfinance")
        self.assertEqual(len(result["events"]["splits"]), 1)

    def test_numpy_numeric_scalars_are_serializable(self) -> None:
        self.assertEqual(MODULE.safe_float(np.int64(1_234_567)), 1_234_567.0)
        self.assertAlmostEqual(MODULE.safe_float(np.float64(12.5)), 12.5)

    def test_unverified_cash_is_not_counted_as_account_value(self) -> None:
        state = {
            "brokerage_cash_usd": 0.0,
            "available_cash_usd": 0.0,
            "cash_pct_estimate": None,
            "last_confirmed_broker_snapshot": {"cash_verified": False},
        }
        summary = MODULE.build_account_summary(
            state,
            {"SOXL": 2},
            {"SOXL": {"close": 100.0}},
        )
        self.assertEqual(summary["holdings_market_value_usd"], 200.0)
        self.assertFalse(summary["cash_verified"])
        self.assertIsNone(summary["brokerage_cash_usd"])
        self.assertIsNone(summary["available_cash_usd"])
        self.assertIsNone(summary["account_value_usd"])
        self.assertEqual(summary["account_value_status"], "unavailable_unverified_cash")

    def test_verified_cash_is_counted_as_account_value(self) -> None:
        state = {
            "brokerage_cash_usd": 50.0,
            "available_cash_usd": 40.0,
            "last_confirmed_broker_snapshot": {"cash_verified": True},
        }
        summary = MODULE.build_account_summary(
            state,
            {"SOXL": 2},
            {"SOXL": {"close": 100.0}},
        )
        self.assertTrue(summary["cash_verified"])
        self.assertEqual(summary["account_value_usd"], 250.0)
        self.assertEqual(summary["available_cash_usd"], 40.0)


if __name__ == "__main__":
    unittest.main()
