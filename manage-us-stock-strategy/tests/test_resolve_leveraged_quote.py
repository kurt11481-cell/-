"""Regression tests for direct quote resolution and leveraged proxy corroboration."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
RESOLVER_PATH = SKILL_ROOT / "scripts" / "resolve_leveraged_quote.py"
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_technical_snapshot.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESOLVER = load_module("resolve_leveraged_quote", RESOLVER_PATH)
VALIDATOR = load_module("validate_technical_snapshot_for_proxy", VALIDATOR_PATH)


def fixture():
    value = json.loads(json.dumps(VALIDATOR.valid_fixture()))
    row = value["symbols"]["TEST"]
    row["close_prev"] = 110.0
    row["quote_crosscheck"] = None
    proxy_close = 200.0 * (1.0 + ((row["close"] / row["close_prev"]) - 1.0) / 2.0)
    value["symbols"]["BASE"] = {
        "bar_date": value["session"]["us_session_date"],
        "close_prev": 200.0,
        "close": proxy_close,
    }
    return value


class LeveragedQuoteResolverTests(unittest.TestCase):
    def test_direct_close_plus_proxy_corroboration_passes(self) -> None:
        value = fixture()
        resolved = RESOLVER.resolve(
            value,
            symbol="TEST",
            independent_close=102.0,
            source="Independent completed-close header",
            source_url="https://example.test/test/history",
            source_field="raw_completed_regular_session_close",
            bar_date=value["session"]["us_session_date"],
            proxy_symbol="BASE",
            leverage_multiple=2.0,
            maximum_tracking_error_fraction=0.01,
            conflict_note="A separate adjusted table was inconsistent.",
        )
        self.assertEqual(resolved["symbols"]["TEST"]["quote_crosscheck"]["status"], "verified")
        result = VALIDATOR.validate_snapshot(resolved, required_symbols=["TEST"])
        self.assertEqual(result["status"], "verified", result["errors"])

    def test_proxy_cannot_replace_direct_close(self) -> None:
        value = fixture()
        with self.assertRaises(RESOLVER.QuoteResolutionError):
            RESOLVER.resolve(
                value,
                symbol="TEST",
                independent_close=107.0,
                source="Independent completed-close header",
                source_url="https://example.test/test/history",
                source_field="raw_completed_regular_session_close",
                bar_date=value["session"]["us_session_date"],
                proxy_symbol="BASE",
                leverage_multiple=2.0,
            )

    def test_proxy_tracking_error_outside_tolerance_fails(self) -> None:
        value = fixture()
        value["symbols"]["BASE"]["close"] = 205.0
        with self.assertRaises(RESOLVER.QuoteResolutionError):
            RESOLVER.resolve(
                value,
                symbol="TEST",
                independent_close=102.0,
                source="Independent completed-close header",
                source_url="https://example.test/test/history",
                source_field="raw_completed_regular_session_close",
                bar_date=value["session"]["us_session_date"],
                proxy_symbol="BASE",
                leverage_multiple=2.0,
                maximum_tracking_error_fraction=0.01,
            )


if __name__ == "__main__":
    unittest.main()
