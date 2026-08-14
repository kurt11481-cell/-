from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from dual_run_scheduler import build_session_schedule, preopen_authority, run_finalization_retry
from validation_common import load_json, validate_instance


class DualRunSchedulerTests(unittest.TestCase):
    def session(self, opened="2026-08-14T09:30:00-04:00", closed="2026-08-14T16:00:00-04:00"):
        return {"session": "2026-08-14", "official_calendar_verified": True,
                "is_trading_day": True, "core_open_at": opened, "core_close_at": closed,
                "calendar_source": "OFFICIAL_TEST_FIXTURE"}

    def result(self, finalized=True):
        return {"bar_finalized": finalized, "stable": finalized, "status": "PASS" if finalized else "PENDING",
                "market_session_type": "REGULAR_COMPLETED", "price_semantics": "CLOSE",
                "reported_session": "2026-08-14"}

    def test_holiday_has_no_runs(self):
        value = self.session(); value["is_trading_day"] = False
        self.assertEqual(build_session_schedule(value)["run_count"], 0)

    def test_dst_is_preserved_from_official_times(self):
        winter = build_session_schedule(self.session("2026-01-12T09:30:00-05:00", "2026-01-12T16:00:00-05:00"))
        summer = build_session_schedule(self.session())
        self.assertTrue(winter["runs"][0]["scheduled_at"].endswith("-05:00"))
        self.assertTrue(summer["runs"][0]["scheduled_at"].endswith("-04:00"))

    def test_early_close_uses_actual_official_close(self):
        value = build_session_schedule(self.session(closed="2026-11-27T13:00:00-05:00"))
        self.assertIn("16:30:00-05:00", value["runs"][1]["scheduled_at"])
        self.assertTrue(value["early_close"])
        self.assertGreaterEqual(value["runs"][1]["scheduled_at"], value["post_close_earliest_at"])

    def test_t_plus_30_success(self):
        value = run_finalization_retry(build_session_schedule(self.session()), lambda _: self.result())
        self.assertEqual((len(value["attempts"]), value["delivery_count"]), (1, 1))

    def test_t_plus_40_success(self):
        seen = 0
        def query(_):
            nonlocal seen; seen += 1
            return self.result(seen == 2)
        value = run_finalization_retry(build_session_schedule(self.session()), query)
        self.assertEqual((len(value["attempts"]), value["delivery_count"]), (2, 1))

    def test_t_plus_50_success(self):
        seen = 0
        def query(_):
            nonlocal seen; seen += 1
            return self.result(seen == 3)
        value = run_finalization_retry(build_session_schedule(self.session()), query)
        self.assertEqual((len(value["attempts"]), value["delivery_count"]), (3, 1))

    def test_t_plus_60_success(self):
        seen = 0
        def query(_):
            nonlocal seen; seen += 1
            return self.result(seen == 4)
        value = run_finalization_retry(build_session_schedule(self.session()), query)
        self.assertEqual((len(value["attempts"]), value["delivery_count"]), (4, 1))

    def test_t_plus_60_failure_does_not_count(self):
        value = run_finalization_retry(build_session_schedule(self.session()), lambda _: self.result(False))
        self.assertEqual((len(value["attempts"]), value["delivery_count"], value["valid_finalized_session_increment"]), (4, 0, 0))
        self.assertEqual(value["finalization_status"], "FINALIZATION_PENDING")

    def test_retry_dedup_and_no_duplicate_delivery(self):
        schedule = build_session_schedule(self.session())
        value = run_finalization_retry(schedule, lambda _: self.result())
        self.assertEqual(value["scheduled_run_id"], schedule["scheduled_run_id"])
        self.assertEqual(value["delivery_count"], 1)

    def test_preopen_cannot_upgrade_or_count(self):
        value = preopen_authority("WATCH", "READY")
        self.assertEqual(value["resulting_state"], "WATCH")
        self.assertEqual(value["finalized_session_increment"], 0)

    def test_current_price_cannot_overwrite_completed_close(self):
        result = self.result()
        result.update({"market_session_type": "AFTER_HOURS", "price_semantics": "CURRENT"})
        value = run_finalization_retry(build_session_schedule(self.session()), lambda _: result)
        self.assertEqual(value["finalization_status"], "FINALIZATION_PENDING")
        self.assertEqual(value["valid_finalized_session_increment"], 0)

    def test_authority_boundary(self):
        value = build_session_schedule(self.session())
        self.assertIsNone(value["quantity"])
        self.assertEqual(value["quantity_authority"], "none")
        self.assertFalse(value["order_authority"])

    def test_policy_schema(self):
        policy = load_json(ROOT / "workspace/policies/dual_run_scheduler_policy.json")
        errors = validate_instance(policy, ROOT / "manage-us-stock-strategy/schemas/dual-run-scheduler-policy.schema.json")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
