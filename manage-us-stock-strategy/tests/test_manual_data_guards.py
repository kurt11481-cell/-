#!/usr/bin/env python3
"""Pinned tests for the manual preflight data-accuracy guards (I4 R6).

These assertions mirror the guard-level tests that previously lived only in
the released test_manual_portfolio_analysis.py, and add the R6 broker
normalization fail-closed rule. They need no repository state.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import manual_data_guards as guards  # noqa: E402
import run_manual_portfolio_analysis as manual  # noqa: E402


OBSERVED_AT = "2026-08-21T22:00:00+00:00"
ACCOUNT_RETRIEVED_AT = "2026-08-21T22:00:02+00:00"
HEALTH_RETRIEVED_AT = "2026-08-21T22:00:03+00:00"
QUOTE_RETRIEVED_AT = "2026-08-21T22:00:04+00:00"
HISTORY_RETRIEVED_AT = "2026-08-21T22:00:06+00:00"
POST_CUTOFF_RETRIEVED_AT = "2026-08-21T22:00:07+00:00"


def account_results(*, holdings=None, cash="25.0", retrieved_at=ACCOUNT_RETRIEVED_AT,
                    holdings_status="PASS", complete=True):
    holdings = {"AAA": ("1", "80.0")} if holdings is None else holdings
    rows = [
        {"stk_cd": ticker, "crnc_code": "USD", "frgn_stk_nm": ticker, "qty": qty,
         "poss_qty": qty, "sell_alowq": qty, "frgn_stk_book_uv": cost}
        for ticker, (qty, cost) in holdings.items()
    ]
    return [
        {"operation": "account_holdings_read", "bridge_status": holdings_status,
         "data": rows if holdings_status in {"PASS", "PARTIAL"} else [],
         "pagination": {"api_id": "ust21070", "pages": 1, "complete": complete, "exhausted": complete},
         "retrieved_at": retrieved_at, "order_authority": False},
        {"operation": "account_deposit_read", "bridge_status": "PASS",
         "data": [{"crnc_code": "USD", "fc_entra": cash, "fc_pymn_alowa": cash, "fc_ord_alowa": cash}],
         "pagination": {"api_id": "READ_ONLY", "pages": 1, "complete": True, "exhausted": True},
         "retrieved_at": retrieved_at, "order_authority": False},
    ]


def system_state(holdings=None, costs=None, cash=25.0):
    return {
        "holdings": {"AAA": 1.0} if holdings is None else holdings,
        "average_cost_usd": {"AAA": 80.0} if costs is None else costs,
        "available_cash_usd": cash,
    }


class PriceSignGuardTest(unittest.TestCase):
    """Moved from test_manual_portfolio_analysis test_07i1, test_07i2, test_07i3."""

    def test_signed_cur_prc_normalizes_to_positive_price(self):
        for raw, expected in (("-30.6390", 30.639), ("-218.6500", 218.65), ("+115.8200", 115.82),
                              ("100", 100.0), ("100.5", 100.5)):
            with self.subTest(raw=raw):
                self.assertEqual(expected, guards._cur_prc_price(raw))

    def test_invalid_cur_prc_values_fail_closed(self):
        cases = ("", " ", "0", "+0.0000", "-0.0000", "-+1.0000", "+-1.0000", "++1.0000",
                 "--1.0000", "+ 1.0000", "- 1.0000", "+\t1.0000", "-\t1.0000", "1e2", "1E2",
                 "+1e2", "-1e2", "+", "-", ".", "+.", "-.", "not-a-price", float("nan"),
                 float("inf"), float("-inf"), "NaN", "Infinity", "+Infinity", "-Infinity",
                 None, True, False)
        for raw in cases:
            with self.subTest(raw=raw):
                self.assertIsNone(guards._cur_prc_price(raw))

    def test_generic_positive_number_behavior_is_unchanged(self):
        self.assertIsNone(guards._number("-30.6390", positive=True))
        self.assertIsNone(guards._number("0", positive=True))
        self.assertEqual(115.82, guards._number("+115.8200", positive=True))
        self.assertEqual(0.0, guards._number("0"))
        self.assertEqual(1234.5, guards._number("1,234.5"))
        for raw in (None, True, "nan", "inf", "-1", "abc"):
            with self.subTest(raw=raw):
                self.assertIsNone(guards._number(raw))


class TimestampGuardTest(unittest.TestCase):
    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
            guards._timestamp("2026-08-21T22:00:00")

    def test_zulu_and_offset_timestamps_are_equal_instants(self):
        self.assertEqual(guards._timestamp("2026-08-21T22:00:00Z"),
                         guards._timestamp("2026-08-21T18:00:00-04:00"))

    def test_malformed_timestamp_raises(self):
        for raw in ("not-a-timestamp", "", "2026-13-01T00:00:00+00:00"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                guards._timestamp(raw)


class TemporalGuardTest(unittest.TestCase):
    """Moved from test_manual_portfolio_analysis test_02p, test_02q, test_02v."""

    def test_cutoff_is_latest_required_result_timestamp(self):
        account = [{"retrieved_at": ACCOUNT_RETRIEVED_AT}]
        market = [{"retrieved_at": HEALTH_RETRIEVED_AT}, {"retrieved_at": QUOTE_RETRIEVED_AT},
                  {"retrieved_at": HISTORY_RETRIEVED_AT}]
        cutoff = guards._acquisition_complete_cutoff(account, market)
        self.assertEqual(HISTORY_RETRIEVED_AT, cutoff)
        self.assertFalse(guards._temporal_evidence_valid(OBSERVED_AT, account, market))
        self.assertTrue(guards._temporal_evidence_valid(cutoff, account, market))

    def test_frozen_cutoff_rejects_later_evidence(self):
        account = [{"retrieved_at": ACCOUNT_RETRIEVED_AT}]
        market = [{"retrieved_at": HISTORY_RETRIEVED_AT}]
        cutoff = guards._acquisition_complete_cutoff(account, market)
        market.append({"retrieved_at": POST_CUTOFF_RETRIEVED_AT})
        self.assertFalse(guards._temporal_evidence_valid(cutoff, account, market))

    def test_missing_or_invalid_timestamps_never_produce_a_cutoff(self):
        self.assertIsNone(guards._acquisition_complete_cutoff([]))
        self.assertIsNone(guards._acquisition_complete_cutoff([{"retrieved_at": None}]))
        self.assertIsNone(guards._acquisition_complete_cutoff([{}]))
        self.assertIsNone(guards._acquisition_complete_cutoff([{"retrieved_at": "not-a-timestamp"}]))
        self.assertIsNone(guards._acquisition_complete_cutoff([{"retrieved_at": "2026-08-21T22:00:00"}]))

    def test_temporal_validity_requires_every_timestamp(self):
        self.assertFalse(guards._temporal_evidence_valid(OBSERVED_AT, []))
        self.assertFalse(guards._temporal_evidence_valid(OBSERVED_AT, [{"retrieved_at": None}]))
        self.assertFalse(guards._temporal_evidence_valid("garbage", [{"retrieved_at": OBSERVED_AT}]))
        self.assertTrue(guards._temporal_evidence_valid(OBSERVED_AT, [{"retrieved_at": OBSERVED_AT}]))
        self.assertFalse(guards._temporal_evidence_valid(OBSERVED_AT, [{"retrieved_at": POST_CUTOFF_RETRIEVED_AT}]))


class BrokerComparisonGuardTest(unittest.TestCase):
    def broker(self, holdings=None, cash="25.0", **kwargs):
        state, status = guards.normalize_broker_state(
            account_results(holdings=holdings, cash=cash, **kwargs),
            observed_at=ACCOUNT_RETRIEVED_AT, maximum_age_seconds=900,
        )
        return state, status

    def test_matching_holdings_cost_and_cash(self):
        broker, status = self.broker()
        self.assertEqual("AVAILABLE", status)
        self.assertEqual(("MATCH", []), guards.compare_broker_and_system(broker, system_state()))

    def test_each_difference_is_reported(self):
        broker, _ = self.broker(holdings={"AAA": ("2", "70.0")}, cash="10.0")
        status, details = guards.compare_broker_and_system(broker, system_state())
        self.assertEqual("DIFFERENT", status)
        self.assertEqual(["HOLDINGS_DIFFER", "AVERAGE_COST_DIFFERS", "AVAILABLE_CASH_DIFFERS"], details)

    def test_unavailable_or_incomplete_broker_is_unknown_not_match(self):
        for kwargs in ({"holdings_status": "KIWOOM_ACCOUNT_UNAVAILABLE"}, {"complete": False}):
            with self.subTest(kwargs=kwargs):
                broker, status = self.broker(**kwargs)
                self.assertNotEqual("AVAILABLE", status)
                self.assertEqual(("UNKNOWN", ["BROKER_HOLDINGS_NOT_COMPLETE"]),
                                 guards.compare_broker_and_system(broker, system_state()))

    def test_missing_system_holdings_or_cash_is_unknown(self):
        broker, _ = self.broker()
        self.assertEqual(("UNKNOWN", ["SYSTEM_HOLDINGS_UNAVAILABLE"]),
                         guards.compare_broker_and_system(broker, {"holdings": None}))
        self.assertEqual(("UNKNOWN", ["COMPARISON_FIELD_UNAVAILABLE"]),
                         guards.compare_broker_and_system(broker, system_state(cash=None)))


class BrokerNormalizationFailClosedTest(unittest.TestCase):
    """R6 item 8: a normalization exception must never read as AVAILABLE with empty holdings."""

    def test_normalization_exception_is_unavailable_and_marked(self):
        results = account_results()
        results[1]["retrieved_at"] = "not-a-timestamp"  # normalize_snapshot cannot parse it
        state, status = guards.normalize_broker_state(
            results, observed_at=ACCOUNT_RETRIEVED_AT, maximum_age_seconds=900,
        )
        self.assertEqual("UNAVAILABLE", status)
        self.assertEqual("UNAVAILABLE", state["status"])
        self.assertEqual(guards.BROKER_NORMALIZATION_FAILED, state["normalization_status"])
        self.assertEqual([], state["holdings"])
        self.assertEqual(("UNKNOWN", ["BROKER_HOLDINGS_NOT_COMPLETE"]),
                         guards.compare_broker_and_system(state, system_state()))
        self.assertFalse(state["order_authority"])
        self.assertEqual("none", state["quantity_authority"])

    def test_any_normalizer_exception_fails_closed(self):
        with patch.object(guards, "normalize_snapshot", side_effect=RuntimeError("boom")):
            state, status = guards.normalize_broker_state(
                account_results(), observed_at=ACCOUNT_RETRIEVED_AT, maximum_age_seconds=900,
            )
        self.assertEqual("UNAVAILABLE", status)
        self.assertEqual(guards.BROKER_NORMALIZATION_FAILED, state["normalization_status"])

    def test_successful_normalization_carries_no_failure_marker(self):
        state, status = guards.normalize_broker_state(
            account_results(), observed_at=ACCOUNT_RETRIEVED_AT, maximum_age_seconds=900,
        )
        self.assertEqual("AVAILABLE", status)
        self.assertNotIn("normalization_status", state)
        self.assertEqual("AAA", state["holdings"][0]["ticker"])


class ManualAdapterUsesPinnedGuardsTest(unittest.TestCase):
    """The released adapter must keep consuming these exact pinned objects."""

    def test_adapter_reexports_the_pinned_guard_objects(self):
        for name in ("_timestamp", "_number", "_cur_prc_price", "_ticker", "_operation_result",
                     "_evidence_timestamps", "_acquisition_complete_cutoff",
                     "_temporal_evidence_valid", "compare_broker_and_system"):
            with self.subTest(name=name):
                self.assertIs(getattr(guards, name), getattr(manual, name))

    def test_adapter_broker_state_delegates_to_pinned_guard(self):
        with patch.object(manual, "normalize_broker_state", wraps=guards.normalize_broker_state) as delegate:
            manual._normalize_broker_state(
                account_results(), observed_at=ACCOUNT_RETRIEVED_AT, maximum_age_seconds=900,
            )
        delegate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
