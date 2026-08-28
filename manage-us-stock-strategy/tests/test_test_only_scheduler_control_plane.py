from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "manage-us-stock-strategy"
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from test_only_scheduler_control_plane import (
    AcceptanceContract,
    TEST_CONFIG_IDENTITY,
    TEST_ORIGIN,
    TestOnlyLedger,
    artifact_hash,
    diagnostic_session,
    fire_and_dispatch,
    materialize_expected,
    parse_time,
    wait_for_scheduled_fire,
    watchdog,
)
from dual_run_scheduler import PRE_OPEN, build_session_schedule
from validation_common import canonical_hash, validate_instance
import test_only_scheduler_control_plane as control_plane


UTC = timezone.utc
NY = ZoneInfo("America/New_York")


def verified_clock(at: datetime) -> dict:
    return {
        "status": "VERIFIED",
        "system_utc": at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "derived_america_new_york": at.astimezone(NY).isoformat(),
        "configured_timezone": "Test/Verified",
        "clock_sync_source": "TEST_FIXTURE",
        "clock_sync_status": "PASS",
    }


class TestOnlySchedulerControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent
        self.db_path = self.root / f".test-only-scheduler-{uuid.uuid4().hex}.sqlite3"
        self.os_root = self.root / f".test-only-os-stage-{uuid.uuid4().hex}"
        self.os_root.mkdir()
        self.ledger = TestOnlyLedger(self.db_path)
        self.fire_at = datetime(2026, 8, 18, 13, 0, tzinfo=UTC)
        self.config_hash = canonical_hash({"identity": TEST_CONFIG_IDENTITY, "test": self.id()}).upper()
        self.contract = AcceptanceContract(
            accepted_scheduler_origin=TEST_ORIGIN,
            accepted_config_identity=self.config_hash,
            activation_effective_at=(self.fire_at - timedelta(minutes=5)).isoformat(),
            max_dispatch_lateness_seconds=5,
        )
        self.occurrence = self._occurrence()

    def tearDown(self) -> None:
        for suffix in ("", "-shm", "-wal"):
            path = Path(f"{self.db_path}{suffix}")
            if path.exists():
                path.unlink()
        shutil.rmtree(self.os_root)

    def _session(self, *, local_open: datetime | None = None, early_close: bool = False) -> dict:
        opened = local_open or datetime(2026, 8, 18, 9, 30, tzinfo=NY)
        closed = datetime(2026, 8, 18, 13 if early_close else 16, 0, tzinfo=NY)
        return {
            "session": opened.date().isoformat(),
            "official_calendar_verified": True,
            "is_trading_day": True,
            "calendar_source": "TEST_ONLY_SYNTHETIC_EXCHANGE_CALENDAR",
            "core_open_at": opened.isoformat(),
            "core_close_at": closed.isoformat(),
            "early_close": early_close,
        }

    def _occurrence(self, **overrides) -> dict:
        values = {
            "ledger": self.ledger,
            "session": self._session(),
            "phase": PRE_OPEN,
            "schedule_id": f"TEST-{self.id()}",
            "scheduler_origin": TEST_ORIGIN,
            "scheduler_config_hash": self.config_hash,
            "trigger_created_at": self.fire_at - timedelta(minutes=1),
        }
        values.update(overrides)
        return materialize_expected(**values)

    def _fire(self, **overrides) -> dict:
        values = {
            "ledger": self.ledger,
            "occurrence": self.occurrence,
            "fire_received_at": self.fire_at,
            "trigger_created_at": self.fire_at - timedelta(minutes=1),
            "scheduler_origin": TEST_ORIGIN,
            "scheduler_config_hash": self.config_hash,
            "contract": self.contract,
            "host_clock": verified_clock(self.fire_at),
        }
        values.update(overrides)
        return fire_and_dispatch(**values)

    def test_occurrence_and_fire_are_separate(self) -> None:
        self.assertEqual(self.ledger.event_types(self.occurrence["occurrence_id"]), ["EXPECTED_OCCURRENCE"])
        self.assertEqual(self.ledger.event_count(self.occurrence["occurrence_id"], "FIRE_RECEIPT"), 0)

    def test_bounded_scheduler_waits_for_future_occurrence(self) -> None:
        times = iter((self.fire_at - timedelta(seconds=1), self.fire_at))
        waits: list[float] = []
        fired = wait_for_scheduled_fire(
            self.fire_at,
            now_provider=lambda: next(times),
            wait_fn=waits.append,
            max_wait_seconds=2,
        )
        self.assertEqual(fired, self.fire_at)
        self.assertEqual(waits, [1.0])

    def test_bounded_scheduler_refuses_past_occurrence(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "PAST_OCCURRENCE_NOT_BACKFILLABLE"):
            wait_for_scheduled_fire(
                self.fire_at,
                now_provider=lambda: self.fire_at + timedelta(seconds=1),
                wait_fn=lambda _: None,
            )

    def test_diagnostic_a_dispatch_without_launcher(self) -> None:
        result = self._fire()
        self.assertEqual(result["status"], "DISPATCH_SUCCEEDED")
        self.assertFalse(result["runtime_started"])
        self.assertIn("FIRE_RECEIPT", self.ledger.event_types(self.occurrence["occurrence_id"]))
        self.assertIn("DISPATCH_ATTEMPT", self.ledger.event_types(self.occurrence["occurrence_id"]))
        self.assertNotIn("LAUNCH_STARTED", self.ledger.event_types(self.occurrence["occurrence_id"]))

    def test_no_backfill_late_start_is_missed(self) -> None:
        result = self._fire(fire_received_at=self.fire_at + timedelta(minutes=20))
        self.assertEqual(result["status"], "MISSED")
        self.assertEqual(result["failure_reason"], "NO_BACKFILL")
        self.assertEqual(self.ledger.counts()["dispatch_claims"], 0)

    def test_restart_or_manual_reentry_cannot_claim_duplicate(self) -> None:
        self.assertEqual(self._fire()["status"], "DISPATCH_SUCCEEDED")
        duplicate = self._fire()
        self.assertEqual(duplicate["status"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(self.ledger.counts()["dispatch_claims"], 1)

    def test_stale_origin_rejected(self) -> None:
        result = self._fire(scheduler_origin="OLD_CODEX_HEARTBEAT")
        self.assertEqual(result["status"], "STALE_TRIGGER_REJECTED")
        self.assertFalse(result["runtime_started"])

    def test_stale_config_rejected(self) -> None:
        result = self._fire(scheduler_config_hash="OLD_CONFIG")
        self.assertEqual(result["status"], "STALE_TRIGGER_REJECTED")

    def test_pre_activation_trigger_rejected(self) -> None:
        result = self._fire(trigger_created_at=self.fire_at - timedelta(hours=1))
        self.assertEqual(result["status"], "STALE_TRIGGER_REJECTED")
        self.assertIn("TRIGGER_PRECEDES_ACTIVATION", result["failure_reason"])

    def test_clock_integrity_fail_closed(self) -> None:
        result = self._fire(host_clock={"status": "CLOCK_INTEGRITY_NOT_VERIFIED"})
        self.assertEqual(result["status"], "CLOCK_INTEGRITY_FAILED")
        self.assertEqual(self.ledger.counts()["dispatch_claims"], 0)

    def test_watchdog_detects_missing_fire_without_launching(self) -> None:
        result = watchdog(self.ledger, as_of=self.fire_at + timedelta(seconds=1))
        self.assertEqual(result["status"], "FIRE_RECEIPT_MISSING")
        self.assertEqual(result["launcher_invocations"], 0)
        self.assertFalse(result["runtime_started"])
        self.assertEqual(self.ledger.counts()["dispatch_claims"], 0)

    def test_dispatch_failure_is_classified(self) -> None:
        def failing_launcher(_, __):
            raise PermissionError("TEST_ONLY")

        result = self._fire(launcher=failing_launcher)
        self.assertEqual(result["status"], "LAUNCH_FAILED")
        self.assertEqual(result["failure_stage"], "LAUNCH")

    def test_nonzero_launcher_exit_is_failure(self) -> None:
        result = self._fire(launcher=lambda *_: {"exit_code": 7})
        self.assertEqual(result["status"], "LAUNCH_FAILED")
        self.assertEqual(result["launcher_exit_code"], 7)

    def test_crash_after_fire_before_launch_is_not_retried_blindly(self) -> None:
        crashed = self._fire(crash_after_fire=True)
        self.assertEqual(crashed["status"], "CRASH_AFTER_FIRE_BEFORE_LAUNCH")
        retried = self._fire()
        self.assertEqual(retried["status"], "DUPLICATE_SUPPRESSED")

    def test_artifact_write_failure_is_classified(self) -> None:
        def artifact_failure(_, __):
            raise OSError("INJECTED_ARTIFACT_WRITE_FAILURE")

        result = self._fire(launcher=artifact_failure)
        self.assertEqual(result["status"], "LAUNCH_FAILED")

    def test_normal_edt_and_est_conversion(self) -> None:
        edt = build_session_schedule(self._session(local_open=datetime(2026, 8, 18, 9, 30, tzinfo=NY)))
        est = build_session_schedule({
            **self._session(local_open=datetime(2026, 12, 1, 9, 30, tzinfo=NY)),
            "session": "2026-12-01",
            "core_close_at": datetime(2026, 12, 1, 16, 0, tzinfo=NY).isoformat(),
        })
        self.assertTrue(edt["runs"][0]["scheduled_at"].endswith("-04:00"))
        self.assertTrue(est["runs"][0]["scheduled_at"].endswith("-05:00"))

    def test_dst_transition_vicinity_keeps_new_york_wall_time(self) -> None:
        before = build_session_schedule({
            **self._session(local_open=datetime(2026, 3, 6, 9, 30, tzinfo=NY)),
            "session": "2026-03-06",
            "core_close_at": datetime(2026, 3, 6, 16, 0, tzinfo=NY).isoformat(),
        })
        after = build_session_schedule({
            **self._session(local_open=datetime(2026, 3, 9, 9, 30, tzinfo=NY)),
            "session": "2026-03-09",
            "core_close_at": datetime(2026, 3, 9, 16, 0, tzinfo=NY).isoformat(),
        })
        self.assertEqual(parse_time(before["runs"][0]["scheduled_at"]).hour, 9)
        self.assertEqual(parse_time(after["runs"][0]["scheduled_at"]).hour, 9)
        self.assertNotEqual(before["runs"][0]["scheduled_at"][-6:], after["runs"][0]["scheduled_at"][-6:])

    def test_market_holiday_has_no_occurrence(self) -> None:
        session = {**self._session(), "is_trading_day": False}
        self.assertEqual(build_session_schedule(session)["status"], "MARKET_HOLIDAY")

    def test_early_close_uses_existing_calendar_logic(self) -> None:
        value = build_session_schedule(self._session(early_close=True))
        self.assertTrue(value["early_close"])
        self.assertEqual(parse_time(value["post_close_earliest_at"]).astimezone(NY).hour, 13)
        self.assertEqual(parse_time(value["post_close_earliest_at"]).astimezone(NY).minute, 30)

    def test_test_only_database_constraints_reject_maturity(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError), self.ledger.connect() as connection:
            connection.execute(
                "INSERT INTO dispatch_claims VALUES (?,?,?,?,?)",
                (self.occurrence["occurrence_id"], self.fire_at.isoformat(), "bad", 1, 1),
            )

    def test_authority_is_always_disabled(self) -> None:
        result = self._fire()
        self.assertFalse(result["order_authority"])
        self.assertEqual(result["quantity_authority"], "none")
        self.assertIsNone(result["execution_quantity"])

    def test_schema_accepts_realistic_diagnostic_report(self) -> None:
        result = self._fire()
        report = {
            "schema_version": "1.0",
            "control_plane_version": "test-only-durable-control-plane-v1",
            "diagnostic_mode": "DIAGNOSTIC_A",
            "status": "PASS",
            "generated_at": self.fire_at.isoformat(),
            "occurrence": self.occurrence,
            "result": result,
            "event_types": self.ledger.event_types(self.occurrence["occurrence_id"]),
            "ledger_path": str(self.ledger.path),
            "ledger_sha256": "A" * 64,
            "host_clock": verified_clock(self.fire_at),
            "protected_hashes_before": {},
            "protected_hashes_after": {},
            "protected_state_unchanged": True,
            "production_runtime_invoked": False,
            "portfolio_effect": "NONE",
            "core_counter_effect": "NONE",
            "test_only": True,
            "maturity_eligible": False,
            "order_authority": False,
            "quantity_authority": "none",
            "execution_quantity": None,
        }
        report["artifact_hash"] = artifact_hash(report)
        errors = validate_instance(report, SKILL / "schemas" / "test-only-scheduler-diagnostic.schema.json")
        self.assertEqual(errors, [])

    def _prepare_os(self, mode: str, fire_at: datetime | None = None) -> Path:
        config_path = self.os_root / f"{mode.lower()}-config.json"
        control_plane.prepare_os_occurrence(
            config_path=config_path,
            output_dir=self.os_root / mode.lower(),
            scheduled_fire_at=fire_at or self.fire_at,
            mode=mode,
            protected_paths=[],
        )
        return config_path

    def _execute_os_with_clock(self, mode: str, observed_at: datetime) -> dict:
        config = self._prepare_os(mode)
        original = control_plane.collect_host_clock_evidence
        control_plane.collect_host_clock_evidence = lambda: verified_clock(observed_at)
        try:
            report, _ = control_plane.execute_os_occurrence(config)
        finally:
            control_plane.collect_host_clock_evidence = original
        return report

    def test_os_diagnostic_c_dispatches_without_runtime(self) -> None:
        report = self._execute_os_with_clock("DIAGNOSTIC_C", self.fire_at)
        self.assertEqual(report["result"]["status"], "DISPATCH_SUCCEEDED")
        self.assertFalse(report["production_runtime_invoked"])
        self.assertFalse(report["maturity_eligible"])

    def test_os_diagnostic_d_uses_harmless_launcher(self) -> None:
        report = self._execute_os_with_clock("DIAGNOSTIC_D", self.fire_at)
        self.assertEqual(report["result"]["status"], "LAUNCH_SUCCEEDED")
        self.assertEqual(report["result"]["launcher_exit_code"], 0)
        self.assertFalse(report["production_runtime_invoked"])

    def test_os_missed_occurrence_never_backfills(self) -> None:
        report = self._execute_os_with_clock("DIAGNOSTIC_C", self.fire_at + timedelta(seconds=30))
        self.assertEqual(report["result"]["status"], "MISSED")
        self.assertEqual(report["result"]["failure_reason"], "NO_BACKFILL")
        self.assertFalse(report["result"]["runtime_started"])

    def test_os_crash_after_fire_is_preserved(self) -> None:
        report = self._execute_os_with_clock("CRASH_AFTER_FIRE", self.fire_at)
        self.assertEqual(report["result"]["status"], "CRASH_AFTER_FIRE_BEFORE_LAUNCH")
        config = Path(report["config_path"])
        original = control_plane.collect_host_clock_evidence
        control_plane.collect_host_clock_evidence = lambda: verified_clock(self.fire_at)
        try:
            replay, _ = control_plane.execute_os_occurrence(config)
        finally:
            control_plane.collect_host_clock_evidence = original
        self.assertEqual(replay["result"]["status"], "DUPLICATE_SUPPRESSED")

    def test_os_stale_trigger_is_rejected(self) -> None:
        report = self._execute_os_with_clock("STALE_TRIGGER", self.fire_at)
        self.assertEqual(report["result"]["status"], "STALE_TRIGGER_REJECTED")
        self.assertFalse(report["result"]["runtime_started"])

    def test_windows_task_staging_is_namespaced_and_no_backfill(self) -> None:
        script = (SCRIPTS / "test_only_windows_task_stage.ps1").read_text(encoding="utf-8")
        self.assertIn('"\\CodexTestOnly\\"', script)
        self.assertIn("StockStrategy-TESTONLY-", script)
        self.assertIn("-StartWhenAvailable:$false", script)
        self.assertIn("-MultipleInstances IgnoreNew", script)
        self.assertNotIn("portfolio_state.json", script)
        self.assertNotIn("PREOPEN_T_MINUS_30_AUTOMATION_PROMPT_EN", script)


if __name__ == "__main__":
    unittest.main()
