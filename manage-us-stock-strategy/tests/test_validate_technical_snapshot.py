from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_technical_snapshot.py"
SPEC = importlib.util.spec_from_file_location("validate_technical_snapshot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def clone(value):
    return json.loads(json.dumps(value))


class TechnicalSnapshotValidationTests(unittest.TestCase):
    def test_valid_fixture_passes(self) -> None:
        result = MODULE.validate_snapshot(
            MODULE.valid_fixture(), required_symbols=["TEST"]
        )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["errors"], [])

    def test_unverified_calendar_fails_closed(self) -> None:
        fixture = clone(MODULE.valid_fixture())
        fixture["session"]["official_calendar_verified"] = False
        fixture["session"]["calendar_verification_status"] = "unverified"
        result = MODULE.validate_snapshot(fixture, required_symbols=["TEST"])
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any("calendar" in item for item in result["errors"]))

    def test_indicator_inconsistency_fails_closed(self) -> None:
        fixture = clone(MODULE.valid_fixture())
        fixture["symbols"]["TEST"]["atr14_pct"] = 0.5
        result = MODULE.validate_snapshot(fixture, required_symbols=["TEST"])
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(
            any("atr14_pct calculation mismatch" in item for item in result["errors"])
        )

    def test_required_symbol_must_exist(self) -> None:
        result = MODULE.validate_snapshot(
            MODULE.valid_fixture(), required_symbols=["MISSING"]
        )
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(
            any("required symbol record is missing" in item for item in result["errors"])
        )

    def test_independent_close_outside_tolerance_fails_closed(self) -> None:
        fixture = clone(MODULE.valid_fixture())
        fixture["symbols"]["TEST"]["quote_crosscheck"]["completed_close"] = 103.0
        result = MODULE.validate_snapshot(fixture, required_symbols=["TEST"])
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(
            any("exceeds approved tolerance" in item for item in result["errors"])
        )

    def test_crosscheck_difference_must_be_explicit(self) -> None:
        fixture = clone(MODULE.valid_fixture())
        del fixture["symbols"]["TEST"]["quote_crosscheck"]["difference_usd"]
        result = MODULE.validate_snapshot(fixture, required_symbols=["TEST"])
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any("difference is missing" in item for item in result["errors"]))

    def test_crosscheck_tolerance_must_be_explicit(self) -> None:
        fixture = clone(MODULE.valid_fixture())
        del fixture["symbols"]["TEST"]["quote_crosscheck"]["tolerance_usd"]
        result = MODULE.validate_snapshot(fixture, required_symbols=["TEST"])
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any("tolerance is missing" in item for item in result["errors"]))

    def test_unadjusted_early_close_volume_fails_closed(self) -> None:
        fixture = clone(MODULE.valid_fixture())
        fixture["session"]["is_early_close"] = True
        result = MODULE.validate_snapshot(fixture, required_symbols=["TEST"])
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any("early-close" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
