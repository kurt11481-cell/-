"""first-collect: the first 30m collection for a symbol with no history starts at
max(FIRST_COLLECTION_DAY, today - FIRST_COLLECTION_LOOKBACK_DAYS).

Kiwoom 30m data starts at a month boundary that moves forward (PLTR first collection failed 2026-11-11 because data
began 2026-05-01). Uses test_auto_core's daily fixture (NOW, RECORD) unchanged; no network, no Kiwoom runtime.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core  # noqa: E402
import test_auto_core as base  # noqa: E402


class FirstCollectionStartTests(base.DailyTests):
    """Only the tests below run (load_tests); the inherited DailyTests tests run in test_auto_core."""

    def collected_for(self, symbol):
        return next(item for item in self.collected if item[0] == symbol)

    def test_new_symbol_starts_150_days_back(self):
        result = self.daily(base.sale_broker())
        self.assertEqual(result["status"], "OK", result["reasons"])
        # fixture NOW is KST 2026-10-14; 2026-10-14 - 150 days = 2026-05-17
        self.assertEqual(self.collected_for("NEWW"), ("NEWW", "NASDAQ", "2026-10-14", "2026-05-17"))

    def test_symbol_with_history_starts_at_its_last_session(self):
        result = self.daily(base.sale_broker())
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(self.collected_for("AAA"), ("AAA", "NASDAQ", "2026-10-14", "2026-10-12"))

    def test_later_fixed_first_day_wins(self):
        with mock.patch.object(auto_core, "FIRST_COLLECTION_DAY", date(2026, 6, 1)):
            result = self.daily(base.sale_broker())
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(self.collected_for("NEWW"), ("NEWW", "NASDAQ", "2026-10-14", "2026-06-01"))

    def test_constants(self):
        self.assertEqual(auto_core.FIRST_COLLECTION_LOOKBACK_DAYS, 150)
        self.assertEqual(auto_core.FIRST_COLLECTION_DAY, date(2026, 4, 1))


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    for name in ("test_new_symbol_starts_150_days_back",
                 "test_symbol_with_history_starts_at_its_last_session",
                 "test_later_fixed_first_day_wins",
                 "test_constants"):
        suite.addTest(FirstCollectionStartTests(name))
    return suite


if __name__ == "__main__":
    unittest.main()
