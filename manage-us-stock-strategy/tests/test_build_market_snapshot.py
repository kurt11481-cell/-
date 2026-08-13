from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_market_snapshot.py"
SPEC = importlib.util.spec_from_file_location("build_market_snapshot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MarketSnapshotBuilderTests(unittest.TestCase):
    def test_unicode_certifi_path_is_mirrored_without_disabling_tls(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRIPT.parents[2]) as temporary_directory:
            root = Path(temporary_directory)
            source = root / "사용자" / "cacert.pem"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"test-ca-bundle")
            public_root = root / "public"
            environment: dict[str, str] = {}
            with patch.object(MODULE, "_path_is_ascii", side_effect=[False, True]):
                result = MODULE.configure_yfinance_ca_bundle(
                    certifi_path=source,
                    public_root=public_root,
                    environment=environment,
                    platform_name="win32",
                )

            copied = public_root / "Codex" / "certifi" / "cacert.pem"
            self.assertEqual(copied.read_bytes(), source.read_bytes())
            self.assertEqual(environment["REQUESTS_CA_BUNDLE"], str(copied))
            self.assertEqual(environment["CURL_CA_BUNDLE"], str(copied))
            self.assertTrue(result["tls_verification"])
            self.assertEqual(
                result["strategy"],
                "unicode_certifi_mirrored_to_ascii_public_path",
            )

    def test_existing_ascii_ca_bundle_is_respected(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRIPT.parents[2]) as temporary_directory:
            bundle = Path(temporary_directory) / "cacert.pem"
            bundle.write_bytes(b"existing-ca-bundle")
            environment = {"CURL_CA_BUNDLE": str(bundle)}
            with patch.object(MODULE, "_path_is_ascii", return_value=True):
                result = MODULE.configure_yfinance_ca_bundle(
                    environment=environment,
                    platform_name="win32",
                )
            self.assertEqual(result["strategy"], "existing_ascii_ca_bundle")
            self.assertTrue(result["tls_verification"])

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
