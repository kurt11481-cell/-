#!/usr/bin/env python3
"""Isolated TEST_ONLY durable scheduler control-plane prototype.

This module deliberately has no imports from market, broker, event, holding,
portfolio, candidate, or execution code.  It may materialize deterministic
occurrences with the existing exchange-calendar-relative scheduler helper,
record append-only control-plane events, and launch only its own harmless
diagnostic child process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

from dual_run_scheduler import POST_CLOSE, PRE_OPEN, build_session_schedule
from validation_common import canonical_hash


SCHEMA_VERSION = "1.0"
CONTROL_PLANE_VERSION = "test-only-durable-control-plane-v1"
TEST_ORIGIN = "TEST_ONLY_DURABLE_LOCAL_SCHEDULER"
TEST_CONFIG_IDENTITY = "test-only-scheduler-config-v1"
NY_ZONE = ZoneInfo("America/New_York")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed


def iso_utc(value: str | datetime) -> str:
    return parse_time(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def artifact_hash(value: dict[str, Any], hash_field: str = "artifact_hash") -> str:
    payload = dict(value)
    payload.pop(hash_field, None)
    return canonical_hash(payload).upper()


def atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def protected_hashes(paths: Iterable[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"PROTECTED_FILE_NOT_FOUND:{resolved}")
        result[str(resolved)] = sha256_file(resolved)
    return result


def _command(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"command": command[0], "exit_code": None, "status": "UNAVAILABLE", "error": type(exc).__name__}
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    return {
        "command": command[0],
        "exit_code": result.returncode,
        "status": "PASS" if result.returncode == 0 and bool(stdout) else "FAIL",
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest().upper(),
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest().upper(),
        "stdout_preview": stdout[:500],
    }


def collect_host_clock_evidence(now: datetime | None = None) -> dict[str, Any]:
    observed = (now or utc_now()).astimezone(timezone.utc)
    derived = observed.astimezone(NY_ZONE)
    if os.name != "nt":
        return {
            "status": "CLOCK_INTEGRITY_NOT_VERIFIED",
            "system_utc": iso_utc(observed),
            "derived_america_new_york": derived.isoformat(),
            "configured_timezone": None,
            "clock_sync_source": None,
            "clock_sync_status": "UNAVAILABLE_ON_NON_WINDOWS",
        }

    timezone_result = _command([
        "powershell", "-NoProfile", "-Command", "(Get-TimeZone).Id",
    ])
    sync_result = _command(["w32tm", "/query", "/status"])
    configured_timezone = (timezone_result.get("stdout_preview") or "").strip() or None
    status = "VERIFIED" if timezone_result["status"] == "PASS" and sync_result["status"] == "PASS" else "CLOCK_INTEGRITY_NOT_VERIFIED"
    return {
        "status": status,
        "system_utc": iso_utc(observed),
        "derived_america_new_york": derived.isoformat(),
        "configured_timezone": configured_timezone,
        "clock_sync_source": "w32tm",
        "clock_sync_status": sync_result["status"],
        "clock_sync_evidence_sha256": sync_result.get("stdout_sha256"),
        "timezone_evidence_sha256": timezone_result.get("stdout_sha256"),
    }


@dataclass(frozen=True)
class AcceptanceContract:
    accepted_scheduler_origin: str
    accepted_config_identity: str
    activation_effective_at: str
    max_dispatch_lateness_seconds: float

    def __post_init__(self) -> None:
        parse_time(self.activation_effective_at)
        if self.max_dispatch_lateness_seconds < 0:
            raise ValueError("NEGATIVE_LATENESS_FORBIDDEN")


class TestOnlyLedger:
    """Insert-only SQLite ledger with an atomic unique dispatch claim."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS expected_occurrences (
                    occurrence_id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    scheduled_run_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    scheduled_fire_at TEXT NOT NULL,
                    scheduler_origin TEXT NOT NULL,
                    scheduler_config_hash TEXT NOT NULL,
                    trigger_created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    test_only INTEGER NOT NULL CHECK(test_only = 1),
                    maturity_eligible INTEGER NOT NULL CHECK(maturity_eligible = 0)
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurrence_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    test_only INTEGER NOT NULL CHECK(test_only = 1),
                    maturity_eligible INTEGER NOT NULL CHECK(maturity_eligible = 0),
                    FOREIGN KEY(occurrence_id) REFERENCES expected_occurrences(occurrence_id)
                );
                CREATE TABLE IF NOT EXISTS dispatch_claims (
                    occurrence_id TEXT PRIMARY KEY,
                    claimed_at TEXT NOT NULL,
                    claim_hash TEXT NOT NULL UNIQUE,
                    test_only INTEGER NOT NULL CHECK(test_only = 1),
                    maturity_eligible INTEGER NOT NULL CHECK(maturity_eligible = 0),
                    FOREIGN KEY(occurrence_id) REFERENCES expected_occurrences(occurrence_id)
                );
                """
            )

    def add_expected(self, value: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO expected_occurrences
                (occurrence_id,schedule_id,scheduled_run_id,phase,trading_date,scheduled_fire_at,
                 scheduler_origin,scheduler_config_hash,trigger_created_at,payload_json,test_only,maturity_eligible)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,0)""",
                (
                    value["occurrence_id"], value["schedule_id"], value["scheduled_run_id"], value["phase"],
                    value["trading_date"], value["scheduled_fire_at"], value["scheduler_origin"],
                    value["scheduler_config_hash"], value["trigger_created_at"],
                    json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )

    def event(self, occurrence_id: str, event_type: str, occurred_at: datetime, payload: dict[str, Any] | None = None) -> str:
        body = {
            "occurrence_id": occurrence_id,
            "event_type": event_type,
            "occurred_at": iso_utc(occurred_at),
            "payload": payload or {},
            "test_only": True,
            "maturity_eligible": False,
        }
        event_digest = canonical_hash(body).upper()
        with self.connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO events
                (occurrence_id,event_type,occurred_at,payload_json,event_hash,test_only,maturity_eligible)
                VALUES (?,?,?,?,?,1,0)""",
                (occurrence_id, event_type, body["occurred_at"], json.dumps(body, sort_keys=True), event_digest),
            )
        return event_digest

    def claim_dispatch(self, occurrence_id: str, claimed_at: datetime) -> bool:
        body = {"occurrence_id": occurrence_id, "claimed_at": iso_utc(claimed_at), "test_only": True}
        try:
            with self.connect() as connection:
                connection.execute(
                    """INSERT INTO dispatch_claims
                    (occurrence_id,claimed_at,claim_hash,test_only,maturity_eligible) VALUES (?,?,?,1,0)""",
                    (occurrence_id, body["claimed_at"], canonical_hash(body).upper()),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def event_types(self, occurrence_id: str) -> list[str]:
        with self.connect() as connection:
            return [row[0] for row in connection.execute(
                "SELECT event_type FROM events WHERE occurrence_id=? ORDER BY event_id", (occurrence_id,)
            )]

    def event_count(self, occurrence_id: str, event_type: str) -> int:
        with self.connect() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM events WHERE occurrence_id=? AND event_type=?", (occurrence_id, event_type)
            ).fetchone()[0])

    def missing_fire_occurrences(self, as_of: datetime) -> list[str]:
        cutoff = iso_utc(as_of)
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT e.occurrence_id FROM expected_occurrences e
                WHERE e.scheduled_fire_at <= ?
                  AND NOT EXISTS (SELECT 1 FROM events v WHERE v.occurrence_id=e.occurrence_id AND v.event_type='FIRE_RECEIPT')
                ORDER BY e.scheduled_fire_at""",
                (cutoff,),
            ).fetchall()
        return [row[0] for row in rows]

    def counts(self) -> dict[str, int]:
        with self.connect() as connection:
            expected = connection.execute("SELECT COUNT(*) FROM expected_occurrences").fetchone()[0]
            events = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            claims = connection.execute("SELECT COUNT(*) FROM dispatch_claims").fetchone()[0]
        return {"expected_occurrences": expected, "events": events, "dispatch_claims": claims}


def materialize_expected(
    ledger: TestOnlyLedger,
    *,
    session: dict[str, Any],
    phase: str,
    schedule_id: str,
    scheduler_origin: str,
    scheduler_config_hash: str,
    trigger_created_at: datetime,
) -> dict[str, Any]:
    schedule = build_session_schedule(session)
    if schedule.get("status") != "SCHEDULED":
        raise ValueError(f"SESSION_NOT_SCHEDULED:{schedule.get('status')}")
    run = next((row for row in schedule["runs"] if row["run_phase"] == phase), None)
    if run is None:
        raise ValueError("PHASE_NOT_FOUND")
    identity = {
        "schedule_id": schedule_id,
        "scheduled_run_id": schedule["scheduled_run_id"],
        "phase": phase,
        "scheduler_config_hash": scheduler_config_hash,
    }
    value = {
        "occurrence_id": canonical_hash(identity)[:40],
        **identity,
        "trading_date": str(schedule["session"]),
        "scheduled_fire_at": iso_utc(run["scheduled_at"]),
        "scheduled_fire_at_new_york": parse_time(run["scheduled_at"]).astimezone(NY_ZONE).isoformat(),
        "scheduler_origin": scheduler_origin,
        "trigger_created_at": iso_utc(trigger_created_at),
        "calendar_source": session.get("calendar_source"),
        "calendar_verified": session.get("official_calendar_verified") is True,
        "test_only": True,
        "maturity_eligible": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    ledger.add_expected(value)
    ledger.event(value["occurrence_id"], "EXPECTED_OCCURRENCE", trigger_created_at, {
        "scheduled_fire_at": value["scheduled_fire_at"], "phase": phase,
    })
    return value


Launcher = Callable[[dict[str, Any], datetime], dict[str, Any]]


def fire_and_dispatch(
    ledger: TestOnlyLedger,
    occurrence: dict[str, Any],
    *,
    fire_received_at: datetime,
    trigger_created_at: datetime,
    scheduler_origin: str,
    scheduler_config_hash: str,
    contract: AcceptanceContract,
    host_clock: dict[str, Any],
    launcher: Launcher | None = None,
    crash_after_fire: bool = False,
) -> dict[str, Any]:
    received = parse_time(fire_received_at).astimezone(timezone.utc)
    scheduled = parse_time(occurrence["scheduled_fire_at"]).astimezone(timezone.utc)
    created = parse_time(trigger_created_at).astimezone(timezone.utc)
    activation = parse_time(contract.activation_effective_at).astimezone(timezone.utc)
    ledger.event(occurrence["occurrence_id"], "FIRE_RECEIPT", received, {
        "scheduler_origin": scheduler_origin,
        "scheduler_config_hash": scheduler_config_hash,
        "fire_received_at": iso_utc(received),
    })
    base = {
        "occurrence_id": occurrence["occurrence_id"],
        "test_only": True,
        "maturity_eligible": False,
        "runtime_started": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }

    stale_reasons: list[str] = []
    if scheduler_origin != contract.accepted_scheduler_origin:
        stale_reasons.append("SCHEDULER_ORIGIN_MISMATCH")
    if scheduler_config_hash != contract.accepted_config_identity:
        stale_reasons.append("SCHEDULER_CONFIG_MISMATCH")
    if created < activation:
        stale_reasons.append("TRIGGER_PRECEDES_ACTIVATION")
    if stale_reasons:
        ledger.event(occurrence["occurrence_id"], "STALE_TRIGGER_REJECTED", received, {"reasons": stale_reasons})
        return {**base, "status": "STALE_TRIGGER_REJECTED", "failure_stage": "ACCEPTANCE", "failure_reason": stale_reasons}

    if host_clock.get("status") != "VERIFIED":
        ledger.event(occurrence["occurrence_id"], "CLOCK_INTEGRITY_FAILED", received, {"status": host_clock.get("status")})
        return {**base, "status": "CLOCK_INTEGRITY_FAILED", "failure_stage": "CLOCK_PREFLIGHT", "failure_reason": host_clock.get("status")}

    lateness = (received - scheduled).total_seconds()
    if lateness > contract.max_dispatch_lateness_seconds:
        ledger.event(occurrence["occurrence_id"], "MISSED", received, {"lateness_seconds": lateness})
        return {**base, "status": "MISSED", "failure_stage": "MISFIRE_GUARD", "failure_reason": "NO_BACKFILL"}

    if not ledger.claim_dispatch(occurrence["occurrence_id"], received):
        ledger.event(occurrence["occurrence_id"], "DUPLICATE_SUPPRESSED", received, {})
        return {**base, "status": "DUPLICATE_SUPPRESSED", "failure_stage": "IDEMPOTENCY", "failure_reason": "ALREADY_CLAIMED"}

    ledger.event(occurrence["occurrence_id"], "DISPATCH_ATTEMPT", received, {})
    if crash_after_fire:
        ledger.event(occurrence["occurrence_id"], "CRASH_AFTER_FIRE_BEFORE_LAUNCH", received, {})
        return {**base, "status": "CRASH_AFTER_FIRE_BEFORE_LAUNCH", "failure_stage": "DISPATCH", "failure_reason": "INJECTED_CRASH"}

    if launcher is None:
        ledger.event(occurrence["occurrence_id"], "DISPATCH_SUCCEEDED", received, {"launcher_required": False})
        return {**base, "status": "DISPATCH_SUCCEEDED", "dispatch_result": "PASS", "failure_stage": None, "failure_reason": None}

    started = utc_now()
    ledger.event(occurrence["occurrence_id"], "LAUNCH_STARTED", started, {})
    try:
        launch_result = launcher(occurrence, started)
    except Exception as exc:  # failure injection is intentionally classified
        finished = utc_now()
        ledger.event(occurrence["occurrence_id"], "LAUNCH_FAILED", finished, {"error_type": type(exc).__name__})
        return {
            **base,
            "status": "LAUNCH_FAILED",
            "failure_stage": "LAUNCH",
            "failure_reason": type(exc).__name__,
            "launcher_started_at": iso_utc(started),
            "launcher_finished_at": iso_utc(finished),
            "launcher_exit_code": None,
        }

    finished = utc_now()
    exit_code = int(launch_result.get("exit_code", 1))
    status = "LAUNCH_SUCCEEDED" if exit_code == 0 else "LAUNCH_FAILED"
    ledger.event(occurrence["occurrence_id"], status, finished, launch_result)
    return {
        **base,
        "status": status,
        "dispatch_result": "PASS" if exit_code == 0 else "FAIL",
        "failure_stage": None if exit_code == 0 else "LAUNCH",
        "failure_reason": None if exit_code == 0 else "NONZERO_EXIT",
        "launcher_started_at": iso_utc(started),
        "launcher_finished_at": iso_utc(finished),
        "launcher_exit_code": exit_code,
        "diagnostic_artifact_path": launch_result.get("diagnostic_artifact_path"),
        "diagnostic_artifact_sha256": launch_result.get("diagnostic_artifact_sha256"),
    }


def watchdog(ledger: TestOnlyLedger, *, as_of: datetime) -> dict[str, Any]:
    missing = ledger.missing_fire_occurrences(as_of)
    for occurrence_id in missing:
        ledger.event(occurrence_id, "WATCHDOG_FIRE_RECEIPT_MISSING", as_of, {"launcher_invoked": False})
    return {
        "status": "FIRE_RECEIPT_MISSING" if missing else "NO_MISSING_FIRE",
        "missing_occurrence_ids": missing,
        "launcher_invocations": 0,
        "runtime_started": False,
        "test_only": True,
        "maturity_eligible": False,
        "order_authority": False,
    }


def wait_for_scheduled_fire(
    scheduled_fire_at: str | datetime,
    *,
    now_provider: Callable[[], datetime] = utc_now,
    wait_fn: Callable[[float], None] = time.sleep,
    max_wait_seconds: float = 10.0,
) -> datetime:
    """Wait only for a bounded TEST_ONLY future occurrence; never catch up a past one."""
    scheduled = parse_time(scheduled_fire_at)
    observed = parse_time(now_provider())
    remaining = (scheduled - observed).total_seconds()
    if remaining < 0:
        raise RuntimeError("PAST_OCCURRENCE_NOT_BACKFILLABLE")
    if remaining > max_wait_seconds:
        raise RuntimeError("DIAGNOSTIC_WAIT_BOUND_EXCEEDED")
    if remaining:
        wait_fn(remaining)
    fired = parse_time(now_provider())
    if fired < scheduled:
        raise RuntimeError("CLOCK_MOVED_BACKWARD_OR_WAIT_RETURNED_EARLY")
    return fired


def diagnostic_session(now: datetime) -> dict[str, Any]:
    local = parse_time(now).astimezone(NY_ZONE).replace(microsecond=0)
    opened = local + timedelta(minutes=30)
    closed = opened + timedelta(hours=6, minutes=30)
    return {
        "session": local.date().isoformat(),
        "official_calendar_verified": True,
        "is_trading_day": True,
        "calendar_source": "TEST_ONLY_SYNTHETIC_EXCHANGE_CALENDAR",
        "core_open_at": opened.isoformat(),
        "core_close_at": closed.isoformat(),
        "early_close": False,
    }


def harmless_subprocess_launcher(output_dir: Path) -> Launcher:
    def launch(occurrence: dict[str, Any], _: datetime) -> dict[str, Any]:
        artifact = output_dir / f"{occurrence['occurrence_id']}-launcher-artifact.json"
        environment = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "WINDIR": os.environ.get("WINDIR", ""),
            "PYTHONUTF8": "1",
        }
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "_launcher",
            "--artifact",
            str(artifact),
            "--occurrence-id",
            occurrence["occurrence_id"],
        ]
        completed = subprocess.run(command, check=False, cwd=output_dir, env=environment)
        return {
            "exit_code": completed.returncode,
            "diagnostic_artifact_path": str(artifact.resolve()) if artifact.is_file() else None,
            "diagnostic_artifact_sha256": sha256_file(artifact) if artifact.is_file() else None,
        }

    return launch


def _diagnostic_report(
    mode: str,
    *,
    occurrence: dict[str, Any],
    result: dict[str, Any],
    ledger: TestOnlyLedger,
    host_clock: dict[str, Any],
    protected_before: dict[str, str],
    protected_after: dict[str, str],
) -> dict[str, Any]:
    passed = result["status"] in {"DISPATCH_SUCCEEDED", "LAUNCH_SUCCEEDED"}
    value = {
        "schema_version": SCHEMA_VERSION,
        "control_plane_version": CONTROL_PLANE_VERSION,
        "diagnostic_mode": mode,
        "status": "PASS" if passed else "FAIL",
        "generated_at": iso_utc(utc_now()),
        "occurrence": occurrence,
        "result": result,
        "event_types": ledger.event_types(occurrence["occurrence_id"]),
        "ledger_path": str(ledger.path),
        "ledger_sha256": sha256_file(ledger.path),
        "host_clock": host_clock,
        "protected_hashes_before": protected_before,
        "protected_hashes_after": protected_after,
        "protected_state_unchanged": protected_before == protected_after,
        "production_runtime_invoked": False,
        "portfolio_effect": "NONE",
        "core_counter_effect": "NONE",
        "test_only": True,
        "maturity_eligible": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    value["artifact_hash"] = artifact_hash(value)
    return value


def run_diagnostic(mode: str, *, output_dir: Path, protected_paths: list[Path]) -> tuple[dict[str, Any], Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before = protected_hashes(protected_paths)
    clock = collect_host_clock_evidence()
    now = parse_time(clock["system_utc"])
    scheduled = now.replace(microsecond=0) + timedelta(seconds=5)
    ledger = TestOnlyLedger(output_dir / "test-only-scheduler-ledger.sqlite3")
    config_hash = canonical_hash({"identity": TEST_CONFIG_IDENTITY, "mode": mode}).upper()
    schedule_id = f"TEST-ONLY-{mode}"
    occurrence = materialize_expected(
        ledger,
        session=diagnostic_session(scheduled),
        phase=PRE_OPEN,
        schedule_id=schedule_id,
        scheduler_origin=TEST_ORIGIN,
        scheduler_config_hash=config_hash,
        trigger_created_at=now,
    )
    contract = AcceptanceContract(
        accepted_scheduler_origin=TEST_ORIGIN,
        accepted_config_identity=config_hash,
        activation_effective_at=iso_utc(now - timedelta(seconds=1)),
        max_dispatch_lateness_seconds=5,
    )
    launcher = None if mode == "DIAGNOSTIC_A" else harmless_subprocess_launcher(output_dir)
    fire_received_at = wait_for_scheduled_fire(occurrence["scheduled_fire_at"])
    result = fire_and_dispatch(
        ledger,
        occurrence,
        fire_received_at=fire_received_at,
        trigger_created_at=now,
        scheduler_origin=TEST_ORIGIN,
        scheduler_config_hash=config_hash,
        contract=contract,
        host_clock=clock,
        launcher=launcher,
    )
    after = protected_hashes(protected_paths)
    report = _diagnostic_report(
        mode,
        occurrence=occurrence,
        result=result,
        ledger=ledger,
        host_clock=clock,
        protected_before=before,
        protected_after=after,
    )
    report_path = output_dir / f"{mode.lower()}-report.json"
    atomic_json_write(report_path, report)
    return report, report_path


def prepare_os_occurrence(
    *,
    config_path: Path,
    output_dir: Path,
    scheduled_fire_at: datetime,
    mode: str,
    protected_paths: list[Path],
    scheduler_origin: str = "TEST_ONLY_WINDOWS_TASK_SCHEDULER",
    scheduler_config_hash: str | None = None,
) -> dict[str, Any]:
    """Materialize one OS-fired TEST_ONLY occurrence without registering an OS task."""
    if mode not in {"DIAGNOSTIC_C", "DIAGNOSTIC_D", "CRASH_AFTER_FIRE", "WATCHDOG", "STALE_TRIGGER"}:
        raise ValueError("UNSUPPORTED_OS_DIAGNOSTIC_MODE")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "test-only-os-scheduler-ledger.sqlite3"
    ledger = TestOnlyLedger(ledger_path)
    config_identity = scheduler_config_hash or canonical_hash({
        "mode": mode,
        "origin": scheduler_origin,
        "scheduled_fire_at": iso_utc(scheduled_fire_at),
        "test_only": True,
    }).upper()
    created_at = utc_now()
    occurrence = materialize_expected(
        ledger,
        session=diagnostic_session(scheduled_fire_at),
        phase=PRE_OPEN,
        schedule_id=f"TEST-ONLY-OS-{mode}",
        scheduler_origin=scheduler_origin,
        scheduler_config_hash=config_identity,
        trigger_created_at=created_at,
    )
    value = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TEST_ONLY_OS_SCHEDULER_CONFIG",
        "mode": mode,
        "created_at": iso_utc(created_at),
        "activation_effective_at": iso_utc(created_at - timedelta(seconds=1)),
        "scheduler_origin": scheduler_origin,
        "scheduler_config_hash": config_identity,
        "max_dispatch_lateness_seconds": 5.0,
        "occurrence": occurrence,
        "ledger_path": str(ledger_path),
        "output_dir": str(output_dir),
        "protected_paths": [str(path.resolve()) for path in protected_paths],
        "test_only": True,
        "maturity_eligible": False,
        "production_scheduler": False,
        "production_runtime_invoked": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    value["config_hash"] = artifact_hash(value, "config_hash")
    atomic_json_write(config_path.resolve(), value)
    return value


def _load_test_only_os_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("artifact_type") != "TEST_ONLY_OS_SCHEDULER_CONFIG":
        raise ValueError("OS_CONFIG_ARTIFACT_TYPE_INVALID")
    if value.get("test_only") is not True or value.get("maturity_eligible") is not False:
        raise ValueError("OS_CONFIG_TEST_ONLY_FIREWALL_FAILED")
    if value.get("production_scheduler") is not False:
        raise ValueError("PRODUCTION_SCHEDULER_FORBIDDEN")
    if value.get("config_hash") != artifact_hash(value, "config_hash"):
        raise ValueError("OS_CONFIG_HASH_MISMATCH")
    return value


def execute_os_occurrence(config_path: Path) -> tuple[dict[str, Any], Path]:
    """Consume one actual OS launch and write fail-closed TEST_ONLY evidence."""
    config = _load_test_only_os_config(config_path.resolve())
    output_dir = Path(config["output_dir"]).resolve()
    ledger = TestOnlyLedger(Path(config["ledger_path"]))
    occurrence = dict(config["occurrence"])
    before = protected_hashes(Path(value) for value in config["protected_paths"])
    clock = collect_host_clock_evidence()
    received = parse_time(clock["system_utc"])
    mode = str(config["mode"])
    origin = str(config["scheduler_origin"])
    config_hash = str(config["scheduler_config_hash"])
    trigger_created_at = parse_time(config["created_at"])
    if mode == "STALE_TRIGGER":
        origin = "REJECTED_STALE_TEST_ORIGIN"
    contract = AcceptanceContract(
        accepted_scheduler_origin=str(config["scheduler_origin"]),
        accepted_config_identity=str(config["scheduler_config_hash"]),
        activation_effective_at=str(config["activation_effective_at"]),
        max_dispatch_lateness_seconds=float(config["max_dispatch_lateness_seconds"]),
    )
    launcher = harmless_subprocess_launcher(output_dir) if mode == "DIAGNOSTIC_D" else None
    result = fire_and_dispatch(
        ledger,
        occurrence,
        fire_received_at=received,
        trigger_created_at=trigger_created_at,
        scheduler_origin=origin,
        scheduler_config_hash=config_hash,
        contract=contract,
        host_clock=clock,
        launcher=launcher,
        crash_after_fire=mode == "CRASH_AFTER_FIRE",
    )
    after = protected_hashes(Path(value) for value in config["protected_paths"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TEST_ONLY_OS_SCHEDULER_RESULT",
        "mode": mode,
        "config_path": str(config_path.resolve()),
        "config_hash": config["config_hash"],
        "occurrence": occurrence,
        "host_clock": clock,
        "result": result,
        "protected_hashes_before": before,
        "protected_hashes_after": after,
        "protected_state_unchanged": before == after,
        "test_only": True,
        "maturity_eligible": False,
        "production_scheduler": False,
        "production_runtime_invoked": False,
        "portfolio_effect": "NONE",
        "core_counter_effect": "NONE",
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    report["artifact_hash"] = artifact_hash(report)
    report_path = output_dir / "os-fire-result.json"
    atomic_json_write(report_path, report)
    return report, report_path


def execute_os_watchdog(config_path: Path) -> tuple[dict[str, Any], Path]:
    config = _load_test_only_os_config(config_path.resolve())
    ledger = TestOnlyLedger(Path(config["ledger_path"]))
    result = watchdog(ledger, as_of=utc_now())
    report = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TEST_ONLY_OS_WATCHDOG_RESULT",
        "mode": "WATCHDOG",
        "config_hash": config["config_hash"],
        "result": result,
        "test_only": True,
        "maturity_eligible": False,
        "production_runtime_invoked": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    report["artifact_hash"] = artifact_hash(report)
    report_path = Path(config["output_dir"]) / "os-watchdog-result.json"
    atomic_json_write(report_path, report)
    return report, report_path


def _launcher_main(args: argparse.Namespace) -> int:
    value = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TEST_ONLY_HARMLESS_LAUNCHER_ARTIFACT",
        "occurrence_id": args.occurrence_id,
        "generated_at": iso_utc(utc_now()),
        "production_runtime_invoked": False,
        "portfolio_effect": "NONE",
        "core_counter_effect": "NONE",
        "test_only": True,
        "maturity_eligible": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    value["artifact_hash"] = artifact_hash(value)
    atomic_json_write(Path(args.artifact), value)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    launcher_parser = subparsers.add_parser("_launcher")
    launcher_parser.add_argument("--artifact", required=True)
    launcher_parser.add_argument("--occurrence-id", required=True)
    for name in ("diagnostic-a", "diagnostic-b"):
        diagnostic = subparsers.add_parser(name)
        diagnostic.add_argument("--output-dir", required=True)
        diagnostic.add_argument("--protected-path", action="append", default=[])
    prepare_parser = subparsers.add_parser("prepare-os-occurrence")
    prepare_parser.add_argument("--config", required=True)
    prepare_parser.add_argument("--output-dir", required=True)
    prepare_parser.add_argument("--scheduled-fire-at", required=True)
    prepare_parser.add_argument("--mode", required=True)
    prepare_parser.add_argument("--protected-path", action="append", default=[])
    os_fire_parser = subparsers.add_parser("os-fire")
    os_fire_parser.add_argument("--config", required=True)
    os_watchdog_parser = subparsers.add_parser("os-watchdog")
    os_watchdog_parser.add_argument("--config", required=True)
    args = parser.parse_args()
    if args.command == "_launcher":
        return _launcher_main(args)
    if args.command == "prepare-os-occurrence":
        value = prepare_os_occurrence(
            config_path=Path(args.config),
            output_dir=Path(args.output_dir),
            scheduled_fire_at=parse_time(args.scheduled_fire_at),
            mode=args.mode,
            protected_paths=[Path(value) for value in args.protected_path],
        )
        print(json.dumps({
            "config": str(Path(args.config).resolve()),
            "occurrence_id": value["occurrence"]["occurrence_id"],
            "scheduled_fire_at": value["occurrence"]["scheduled_fire_at"],
            "test_only": True,
            "maturity_eligible": False,
        }, indent=2))
        return 0
    if args.command == "os-fire":
        report, path = execute_os_occurrence(Path(args.config))
        print(json.dumps({
            "status": report["result"]["status"],
            "report": str(path),
            "test_only": True,
            "maturity_eligible": False,
        }, indent=2))
        return 0 if report["result"]["status"] in {
            "DISPATCH_SUCCEEDED", "LAUNCH_SUCCEEDED", "MISSED",
            "CRASH_AFTER_FIRE_BEFORE_LAUNCH", "STALE_TRIGGER_REJECTED",
        } else 1
    if args.command == "os-watchdog":
        report, path = execute_os_watchdog(Path(args.config))
        print(json.dumps({"status": report["result"]["status"], "report": str(path)}, indent=2))
        return 0
    mode = "DIAGNOSTIC_A" if args.command == "diagnostic-a" else "DIAGNOSTIC_B"
    report, path = run_diagnostic(
        mode,
        output_dir=Path(args.output_dir),
        protected_paths=[Path(value) for value in args.protected_path],
    )
    print(json.dumps({
        "diagnostic": mode,
        "status": report["status"],
        "report": str(path),
        "test_only": True,
        "maturity_eligible": False,
        "order_authority": False,
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
