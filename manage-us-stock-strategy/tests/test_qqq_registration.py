"""qqq-reg: QQQ registered as a 1x index ETF in the S5 exposure policy and the auto-core close list.

Real policy files are read for the value checks (a, b, f); exposure and eligibility (c, d, e, g) use
synthetic holdings and closes built with the S5 exposure fixtures. Nothing here writes a file.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_exposure as pe  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from validate_registry_consistency import validate_registry_consistency  # noqa: E402
from validation_common import validate_instance  # noqa: E402

SCHEMA = SKILL_ROOT / "schemas/portfolio-exposure-review.schema.json"
AUTO_CORE_POLICY = REPO_ROOT / "workspace/policies/auto_core.json"
REGISTRY = REPO_ROOT / "workspace/policies/instrument_registry.json"
EVAL = "2026-09-30"
PRICES = {"SOXX": "500", "SOXL": "100", "QQQ": "500", "XLE": "90"}
MULTIPLES = {"SOXX": 1.0, "SOXL": 2.9, "QQQ": 0.8, "XLE": 0.5}
CARD_STOCK_CORE_BEFORE = ["BE", "MU", "NBIS", "DELL", "AMD", "PWR", "LITE"]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _closes(sessions: list[str], symbols: list[str]) -> dict[str, dict[str, str]]:
    past = [session for session in sessions if session <= EVAL]
    bench = fx.benchmark_returns(len(past))
    return {symbol: fx.series(past, bench[-(len(past) - 1):], last=PRICES[symbol], multiple=MULTIPLES[symbol])
            for symbol in symbols}


def _review(holdings: dict[str, int], cash: str) -> tuple[dict[str, Any], dict[str, Any]]:
    policy = fx.real_policy()
    sessions = fx.weekday_sessions(260, EVAL, extra_after=10)
    closes = _closes(sessions, sorted(set(holdings) | {"SOXX"}))
    equity = sum((Decimal(quantity) * Decimal(PRICES[symbol]) for symbol, quantity in holdings.items()),
                 Decimal(cash))
    result = pe.build_exposure_review(
        policy=policy, evaluation_session=EVAL, calendar_sessions=sessions,
        snapshots=[fx.snapshot("2026-09-29", holdings, cash, revision=1)], snapshot_reasons=[], closes=closes,
        close_unverified={}, journal=fx.journal(fx.activation_entry(EVAL, fx.decimal_text(equity))), cards={},
        earnings=fx.verified_earnings(["BE", "MU", "NBIS", "DELL", "AMD"], sessions[-3]), proposals=[])
    errors = validate_instance(result, SCHEMA)
    assert not errors, errors
    return result, {"policy": policy, "sessions": sessions, "closes": closes, "equity": equity}


def _trigger(review: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in review["fail_closed"]["triggers"] if item["id"] == name)


class RealPolicyValueTests(unittest.TestCase):
    """(a) (b) the merged policy values; everything else in the touched sections stays as approved."""

    def test_a_alert_policy_registers_qqq_without_moving_other_values(self) -> None:
        section = _load(fx.POLICY_PATH)["portfolio_exposure_policy"]
        self.assertEqual(section["nominal_multipliers"]["QQQ"], 1)
        self.assertIn("QQQ", section["allowed_index_etfs"])
        self.assertEqual(section["allowed_index_etfs"], ["SOXL", "TQQQ", "DRAM", "QQQ"])
        self.assertEqual(section["add_default"], "card_add_stock_else_SOXL")
        self.assertEqual(section["card_stock_core"], CARD_STOCK_CORE_BEFORE)
        self.assertEqual(section["thresholds"]["hard_ceiling_when_exposure_gte"], 1.9)
        self.assertNotIn("QQQ", section["single_stock_cap_exempt"])
        self.assertEqual((section["order_authority"], section["quantity_authority"], section["execution_quantity"]),
                         (False, "none", None))

    def test_b_auto_core_collects_qqq_closes(self) -> None:
        self.assertEqual(_load(AUTO_CORE_POLICY)["symbols_extra"], ["SOXX", "GRID", "SPY", "QQQ"])


class QqqExposureTests(unittest.TestCase):
    """(c) (d) (e) (g) synthetic holdings through the real exposure code and the real policy."""

    def test_c_qqq_holding_keeps_exposure_computable(self) -> None:
        review, ctx = _review({"SOXL": 10, "QQQ": 2}, "2000")
        self.assertEqual(_trigger(review, "unregistered_instrument_held")["reasons"], [])
        self.assertFalse(_trigger(review, "unregistered_instrument_held")["active"])
        exposure = review["exposure"]
        self.assertIsInstance(exposure["effective"], float)
        self.assertEqual(exposure["unavailable_reasons"], [])
        # Expected values from the code's own definitions (portfolio_exposure.py nominal_exposure,
        # volatility_ratio, effective_exposure): N = sum(multiplier x weight), V = std(sum(weight x return))
        # / std(SOXX return) over the last window+1 sessions, E = max(N, V).
        equity = ctx["equity"]
        weights = {"SOXL": Decimal(10) * Decimal("100") / equity, "QQQ": Decimal(2) * Decimal("500") / equity}
        nominal = 3 * weights["SOXL"] + 1 * weights["QQQ"]
        window = [s for s in ctx["sessions"] if s <= EVAL][-(ctx["policy"]["portfolio_exposure_policy"]
                                                            ["sox_equivalent"]["window_sessions"] + 1):]

        def returns(symbol: str) -> list[float]:
            values = [float(ctx["closes"][symbol][session]) for session in window]
            return [values[i] / values[i - 1] - 1.0 for i in range(1, len(values))]

        portfolio = [math.fsum(float(weights[s]) * returns(s)[i] for s in weights) for i in range(len(window) - 1)]
        volatility = statistics.stdev(portfolio) / statistics.stdev(returns("SOXX"))
        self.assertAlmostEqual(exposure["nominal"], float(nominal), places=4)
        self.assertAlmostEqual(exposure["sox_equivalent"], volatility, places=4)
        self.assertAlmostEqual(exposure["effective"], max(float(nominal), volatility), places=4)
        position = next(item for item in review["positions"] if item["symbol"] == "QQQ")
        self.assertTrue(position["registered"])
        self.assertEqual(position["nominal_multiplier"], 1.0)
        self.assertAlmostEqual(position["nominal_contribution"], float(weights["QQQ"]), places=6)

    def test_d_qqq_is_an_s5_buy_instrument(self) -> None:
        config = pe.exposure_config(fx.real_policy())
        sessions = fx.weekday_sessions(260, EVAL, extra_after=10)
        for weights in ({}, {"SOXL": Decimal("0.25"), "QQQ": Decimal("0.25")}):
            reasons = pe.increase_blockers("QQQ", config=config, weights=weights, peaks={}, earnings=None,
                                           calendar_sessions=sessions, buy_session=sessions[-10])
            self.assertNotIn("UNREGISTERED_INSTRUMENT", reasons)
            self.assertNotIn("NOT_AN_S5_NEW_BUY_INSTRUMENT", reasons)
        self.assertEqual(pe.increase_blockers("QQQ", config=config, weights={}, peaks={}, earnings=None,
                                              calendar_sessions=sessions, buy_session=sessions[-10]), [])

    def test_e_unregistered_symbols_still_fail_closed(self) -> None:
        review, _ = _review({"SOXL": 10, "QQQ": 2, "XLE": 5}, "2000")
        self.assertEqual(_trigger(review, "unregistered_instrument_held")["reasons"], ["UNREGISTERED:XLE"])
        self.assertIsNone(review["exposure"]["effective"])
        config = pe.exposure_config(fx.real_policy())
        self.assertEqual(pe.increase_blockers("XLE", config=config, weights={}, peaks={}, earnings=None,
                                              calendar_sessions=[], buy_session=None), ["UNREGISTERED_INSTRUMENT"])

    def test_g_single_stock_cap_applies_to_qqq_as_today(self) -> None:
        # Current behaviour fixed, not changed: QQQ is not in single_stock_cap_exempt, so the 0.4 nominal
        # single-stock cap applies to it (cap_limit = cap / multiplier = 0.4).
        config = pe.exposure_config(fx.real_policy())
        self.assertEqual(pe.cap_limit("QQQ", config), Decimal("0.4"))
        breaches = pe.cap_breaches({"QQQ": Decimal("0.5")}, config)
        self.assertEqual([item["symbol"] for item in breaches], ["QQQ"])
        review, _ = _review({"SOXL": 10, "QQQ": 2}, "2000")
        position = next(item for item in review["positions"] if item["symbol"] == "QQQ")
        self.assertTrue(position["single_stock_cap_applies"])


class RegistryConsistencyTests(unittest.TestCase):
    """(f) the canonical registry and the policy hash agree, and QQQ's registry record is a verified 1x ETF."""

    def test_f_registry_and_policy_hash_validate(self) -> None:
        result = validate_registry_consistency(_load(REGISTRY), _load(fx.POLICY_PATH), REGISTRY)
        self.assertEqual(result["status"], "VALIDATED", result["errors"])
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["order_authority"])

    def test_f_qqq_registry_record(self) -> None:
        record = _load(REGISTRY)["instruments"]["QQQ"]
        self.assertEqual((record["instrument_type"], record["leverage_factor"], record["leverage_factor_status"]),
                         ("spot_etf", 1.0, "verified"))
        self.assertTrue(record["identity_status"].startswith("verified"))
        self.assertEqual(record["candidate_status"], "active")
        self.assertIs(record["new_buy_instrument_approved"], False)
        self.assertIs(record["short_sale_approved"], False)
        self.assertTrue(record["official_identity_source_url"].startswith("https://www.sec.gov/"))


if __name__ == "__main__":
    unittest.main()
