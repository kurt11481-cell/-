import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from shadow_acceptance import apply_attempt, initial_progress, record_valid_preopen
from validation_common import validate_instance


class DualRunShadowProgressTests(unittest.TestCase):
    def test_new_cohort_starts_all_dual_run_counters_at_zero(self):
        progress = initial_progress("a" * 64, "2026-08-14T00:00:00Z")
        self.assertEqual(progress["valid_finalized_sessions"], 0)
        self.assertEqual(progress["valid_paired_operational_days"], 0)
        self.assertEqual(progress["preopen_success_count"], 0)
        self.assertEqual(progress["postclose_success_count"], 0)
        schema = ROOT / "manage-us-stock-strategy/schemas/shadow-progress-state.schema.json"
        self.assertEqual(validate_instance(progress, schema), [])

    def test_preopen_does_not_count_and_postclose_pairs_once(self):
        progress = initial_progress("b" * 64, "2026-08-14T00:00:00Z")
        progress = record_valid_preopen(progress, "2026-08-17")
        progress = record_valid_preopen(progress, "2026-08-17")
        self.assertEqual(progress["preopen_success_count"], 1)
        self.assertEqual(progress["valid_finalized_sessions"], 0)
        attempt = {
            "attempt_hash": "c" * 64,
            "counts_as_valid_session": True,
            "completed_session": "2026-08-17",
            "critical_violations": [],
            "baseline_coverage": {},
            "independent_price_coverage": {"status": "NOT_REQUIRED"},
        }
        progress = apply_attempt(progress, attempt)
        self.assertEqual(progress["valid_finalized_sessions"], 1)
        self.assertEqual(progress["valid_paired_operational_days"], 1)
        self.assertEqual(progress["postclose_success_count"], 1)
        self.assertEqual(progress["paired_operational_days"], ["2026-08-17"])


if __name__ == "__main__":
    unittest.main()
