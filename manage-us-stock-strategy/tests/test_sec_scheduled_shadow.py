from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

from sec_official_event_intake import IntakeError, build_dashboard_view
from sec_scheduled_shadow import (
    ATTEMPT_SCHEMA,
    attempt_artifact_path,
    build_summary,
    build_scheduled_attempt,
    derive_accession_diff,
    discover_latest_compatible_successful_run,
    discover_previous_run,
    latest_known_summary,
    load_run_artifact,
    runs_are_compatible,
    write_scheduled_attempt,
    write_scheduled_artifacts,
)
from validation_common import file_hash, load_json, validate_instance


CONTRACT_PATH = ROOT / "manage-us-stock-strategy/assets/sec-scheduled-shadow-contract-v0.1.json"
SUMMARY_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-scheduled-shadow-summary.schema.json"
WRAPPER_PATH = SCRIPT_ROOT / "run_sec_scheduled_shadow.ps1"
REGISTER_PATH = SCRIPT_ROOT / "register_sec_scheduled_shadow_task.ps1"
PREFLIGHT_PATH = SCRIPT_ROOT / "sec_scheduled_shadow_preflight.ps1"
WATCHLIST = ["MRVL", "NBIS", "PGR", "JPM", "CME", "V"]


def powershell_executable() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")


def write_fake_preflight(
    scripts: Path,
    *,
    timezone_id: str = "Korea Standard Time",
    process_configured: bool = True,
    persistent_configured: bool = True,
) -> None:
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / PREFLIGHT_PATH.name).write_text(
        "function Get-SecScheduledShadowSystemPreflight {\n"
        "    [pscustomobject]@{\n"
        f"        TimezoneId = '{timezone_id}'\n"
        f"        TimezonePreflight = '{'PASS' if timezone_id == 'Korea Standard Time' else 'FAIL'}'\n"
        f"        ProcessUserAgent = '{'CONFIGURED' if process_configured else 'NOT_CONFIGURED'}'\n"
        f"        PersistentUserAgent = '{'CONFIGURED' if persistent_configured else 'NOT_CONFIGURED'}'\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )


def event(ticker: str, accession: str, *, materiality: str = "MEDIUM", form: str = "8-K") -> dict:
    return {
        "ticker": ticker,
        "accession_number": accession,
        "materiality": materiality,
        "form": form,
        "event_type": "CURRENT_REPORT" if form == "8-K" else "OFFERING_PROSPECTUS",
        "portfolio_relevance": "HOLDING" if ticker in {"MRVL", "NBIS"} else "CHALLENGER",
        "decision_impact": "ASSET_REVIEW_REQUIRED" if materiality == "HIGH" else "WATCH",
        "filing_date": "2026-08-30",
        "accepted_at": "2026-08-30T20:00:00+00:00",
        "items_if_available": [],
        "underlying_company_relevance": False,
        "verification_status": "OFFICIAL_SOURCE_VERIFIED",
        "source_authority": "OFFICIAL_SEC",
    }


def write_run(
    output_root: Path,
    run_id: str,
    decision_as_of: str,
    events: list[dict],
    *,
    watchlist: list[str] | None = None,
    pipeline_version: str = "0.1",
    schema_version: str = "0.1",
    pipeline_status: str = "PASS",
) -> Path:
    date_directory = decision_as_of[:10]
    run_directory = output_root / date_directory / run_id
    run_directory.mkdir(parents=True)
    normalized = {
        "schema_version": schema_version,
        "pipeline_version": pipeline_version,
        "decision_as_of": decision_as_of,
        "lookback_days": 7,
        "events": events,
    }
    manifest = {
        "run_id": run_id,
        "pipeline_version": pipeline_version,
        "pipeline_status": pipeline_status,
        "network_access": "SEC_OFFICIAL_ONLY",
        "watchlist": list(watchlist or WATCHLIST),
        "started_at": decision_as_of,
        "finished_at": decision_as_of,
    }
    (run_directory / "normalized-events.json").write_text(
        json.dumps(normalized, indent=2) + "\n", encoding="utf-8"
    )
    (run_directory / "run-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return run_directory


class SecScheduledShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(CONTRACT_PATH)

    def run_plan(self, *, user_agent: str | None = None) -> subprocess.CompletedProcess[str]:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        environment = os.environ.copy()
        if user_agent is None:
            environment.pop("SEC_USER_AGENT", None)
        else:
            environment["SEC_USER_AGENT"] = user_agent
        return subprocess.run(
            [executable, "-NoProfile", "-File", str(REGISTER_PATH), "-SkipTaskQuery"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def test_01_plan_only_is_default_and_never_mutates(self) -> None:
        result = self.run_plan()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("MODE = PLAN_ONLY", result.stdout)
        self.assertIn("TASK_MUTATION = NO", result.stdout)
        self.assertIn("TASK_CREATED = NO", result.stdout)
        self.assertIn("TASK_UPDATED = NO", result.stdout)
        self.assertIn("TASK_DELETED = NO", result.stdout)

    def test_02_apply_is_explicit_and_registration_is_below_plan_exit(self) -> None:
        source = REGISTER_PATH.read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", source)
        self.assertLess(source.index("if (-not $Apply)"), source.index("Register-ScheduledTask"))
        self.assertNotIn("HighestAvailable", source)
        self.assertNotIn("-RunLevel Highest", source)

    def test_03_contract_has_exact_two_trigger_groups_weekdays_and_times(self) -> None:
        triggers = self.contract["triggers"]
        self.assertEqual(2, len(triggers))
        self.assertEqual(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            triggers[0]["days_of_week"],
        )
        self.assertEqual("22:00", triggers[0]["local_time"])
        self.assertEqual(
            ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            triggers[1]["days_of_week"],
        )
        self.assertEqual("12:30", triggers[1]["local_time"])

    def test_04_contract_is_normal_user_non_waking_bounded_and_nonoverlapping(self) -> None:
        settings = self.contract["settings"]
        self.assertEqual("INTERACTIVE", settings["logon_type"])
        self.assertEqual("LIMITED", settings["run_level"])
        self.assertTrue(settings["start_when_available"])
        self.assertFalse(settings["wake_to_run"])
        self.assertEqual(10, settings["execution_time_limit_minutes"])
        self.assertEqual("IGNORE_NEW", settings["multiple_instances"])

    def test_05_plan_output_is_sanitized(self) -> None:
        secret = "ScheduledTest/0.1 private-contact@example.invalid"
        result = self.run_plan(user_agent=secret)
        combined = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, combined)
        self.assertIn("USER_AGENT = CONFIGURED", result.stdout)
        self.assertIn("USER_AGENT_VALUE = REDACTED", result.stdout)
        self.assertNotIn(secret, combined)

    def test_06_missing_user_agent_exits_before_python_runner(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "runner-called.txt"
            environment = os.environ.copy()
            environment.pop("SEC_USER_AGENT", None)
            result = subprocess.run(
                [
                    executable, "-NoProfile", "-File", str(WRAPPER_PATH),
                    "-RepositoryRoot", directory,
                    "-PythonPath", sys.executable,
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("SEC_USER_AGENT_REQUIRED", result.stdout)
            self.assertFalse(marker.exists())
            output = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertTrue(output["ATTEMPT_ID"].startswith("sec-scheduled-attempt-"))
            attempt_path = next(Path(directory).rglob("scheduled-attempt.json"))
            attempt = load_json(attempt_path)
            self.assertEqual("BLOCKED", attempt["attempt_result"])
            self.assertEqual("BASELINE_ONLY", attempt["freshness_status"])
            self.assertFalse(attempt["network_started"])
            self.assertEqual([], validate_instance(attempt, ATTEMPT_SCHEMA))

    def test_07_wrapper_passes_lookback_seven_and_never_emits_user_agent(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        secret = "ScheduledTest/0.1 do-not-print@example.invalid"
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            assets = temporary_root / "manage-us-stock-strategy/assets"
            scripts = temporary_root / "manage-us-stock-strategy/scripts"
            assets.mkdir(parents=True)
            scripts.mkdir(parents=True)
            shutil.copyfile(CONTRACT_PATH, assets / CONTRACT_PATH.name)
            write_fake_preflight(scripts)
            fake_intake = scripts / "sec_official_event_intake.py"
            fake_intake.write_text(
                "import json, pathlib, sys\n"
                "out = pathlib.Path(sys.argv[sys.argv.index('--output-root') + 1])\n"
                "out.mkdir(parents=True, exist_ok=True)\n"
                "(out / 'arguments.json').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
                "print(json.dumps({'status':'PASS'}))\n",
                encoding="utf-8",
            )
            (scripts / "sec_scheduled_shadow.py").write_text(
                "import datetime, json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "root = pathlib.Path(args[args.index('--attempt-output-root') + 1])\n"
                "attempt_id = args[args.index('--attempt-id') + 1]\n"
                "started = args[args.index('--attempt-started-at') + 1]\n"
                "date = datetime.datetime.fromisoformat(started).date().isoformat()\n"
                "path = root / date / attempt_id / 'scheduled-attempt.json'\n"
                "path.parent.mkdir(parents=True)\n"
                "path.write_text(json.dumps({'attempt_id': attempt_id}), encoding='utf-8')\n"
                "print(json.dumps({'schedule_status':'PASS'}))\n",
                encoding="utf-8",
            )
            output_root = temporary_root / "outputs"
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = secret
            result = subprocess.run(
                [
                    executable, "-NoProfile", "-File", str(WRAPPER_PATH),
                    "-RepositoryRoot", str(temporary_root),
                    "-PythonPath", sys.executable,
                    "-OutputRoot", str(output_root),
                    "-RunId", "sec-scheduled-test",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            combined = result.stdout + result.stderr
            self.assertEqual(0, result.returncode, combined)
            arguments = json.loads((output_root / "arguments.json").read_text(encoding="utf-8"))
            self.assertEqual("7", arguments[arguments.index("--lookback-days") + 1])
            self.assertNotIn(secret, combined)

    def test_08_previous_compatible_run_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_directory = write_run(root, "previous", "2026-08-30T01:00:00+00:00", [event("MRVL", "a")])
            current_directory = write_run(root, "current", "2026-08-31T01:00:00+00:00", [event("MRVL", "a")])
            status, previous = discover_previous_run(root, load_run_artifact(current_directory))
            self.assertEqual("PASS", status)
            self.assertEqual(previous_directory, previous.run_directory)

    def test_09_previous_run_missing_is_baseline_only_not_zero_new(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current_directory = write_run(root, "current", "2026-08-31T01:00:00+00:00", [event("MRVL", "a")])
            current = load_run_artifact(current_directory)
            status, previous = discover_previous_run(root, current)
            summary = build_summary(current, status, previous)
            self.assertEqual("BASELINE_ONLY", summary["diff_status"])
            self.assertIsNone(summary["new_since_previous_count"])
            self.assertIsNone(summary["new_high_since_previous_count"])

    def test_10_incompatible_previous_run_is_visible_and_not_diffed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_directory = write_run(
                root, "previous", "2026-08-30T01:00:00+00:00", [event("MRVL", "a")],
                watchlist=["MRVL"],
            )
            current_directory = write_run(root, "current", "2026-08-31T01:00:00+00:00", [event("MRVL", "b")])
            current = load_run_artifact(current_directory)
            previous = load_run_artifact(previous_directory)
            self.assertFalse(runs_are_compatible(current, previous))
            status, selected = discover_previous_run(root, current)
            summary = build_summary(current, status, selected)
            self.assertEqual("PREVIOUS_RUN_INCOMPATIBLE", summary["diff_status"])
            self.assertIsNone(summary["new_since_previous_count"])

    def test_11_accession_diff_is_ticker_scoped_and_repeated_accession_is_not_new(self) -> None:
        previous_events = [event("MRVL", "same"), event("NBIS", "shared")]
        current_events = [
            event("MRVL", "same"),
            event("NBIS", "shared"),
            event("MRVL", "shared"),
            event("NBIS", "new"),
        ]
        new_events = derive_accession_diff(current_events, previous_events)
        self.assertEqual([("MRVL", "shared"), ("NBIS", "new")], [
            (item["ticker"], item["accession_number"]) for item in new_events
        ])

    def test_12_new_high_count_and_window_count_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, "previous", "2026-08-30T01:00:00+00:00", [event("MRVL", "old", materiality="HIGH")])
            current_directory = write_run(root, "current", "2026-08-31T01:00:00+00:00", [
                event("MRVL", "old", materiality="HIGH"),
                event("NBIS", "new-high", materiality="HIGH"),
                event("JPM", "new-medium"),
            ])
            current = load_run_artifact(current_directory)
            status, previous = discover_previous_run(root, current)
            summary = build_summary(current, status, previous)
            self.assertEqual(3, summary["filings_in_lookback_window"])
            self.assertEqual(2, summary["new_since_previous_count"])
            self.assertEqual(1, summary["new_high_since_previous_count"])
            self.assertEqual([], validate_instance(summary, SUMMARY_SCHEMA))

    def test_13_zero_accession_diff_is_no_new_filings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = [event("MRVL", "same")]
            write_run(root, "previous", "2026-08-30T01:00:00+00:00", events)
            current_directory = write_run(root, "current", "2026-08-31T01:00:00+00:00", events)
            current = load_run_artifact(current_directory)
            status, previous = discover_previous_run(root, current)
            summary = build_summary(current, status, previous)
            self.assertEqual("NO_NEW_FILINGS", summary["schedule_status"])
            self.assertEqual(0, summary["new_since_previous_count"])

    def test_14_previous_and_current_evidence_are_not_mutated_and_derived_view_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_directory = write_run(root, "previous", "2026-08-30T01:00:00+00:00", [event("MRVL", "old")])
            current_directory = write_run(root, "current", "2026-08-31T01:00:00+00:00", [event("MRVL", "new")])
            protected = [
                previous_directory / "normalized-events.json",
                previous_directory / "run-manifest.json",
                current_directory / "normalized-events.json",
                current_directory / "run-manifest.json",
            ]
            before = {path: file_hash(path) for path in protected}
            summary = write_scheduled_artifacts(root, "current")
            self.assertEqual("PASS", summary["diff_status"])
            self.assertEqual(before, {path: file_hash(path) for path in protected})
            self.assertTrue((current_directory / "scheduled-dashboard.json").is_file())
            self.assertTrue((current_directory / "scheduled-dashboard.md").is_file())
            self.assertTrue((current_directory / "scheduled-dashboard.html").is_file())
            markdown_bytes = (current_directory / "scheduled-dashboard.md").read_bytes()
            html_bytes = (current_directory / "scheduled-dashboard.html").read_bytes()
            self.assertTrue(markdown_bytes.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(html_bytes.startswith(b"\xef\xbb\xbf"))
            for token in ("SEC 공시 자동 분석", "최근 7일 공시 수", "새 HIGH 공시 수", "현재 HIGH 검토 공시 수"):
                self.assertIn(token, markdown_bytes.decode("utf-8-sig"))
                self.assertIn(token, html_bytes.decode("utf-8-sig"))
            with self.assertRaises(IntakeError) as context:
                write_scheduled_artifacts(root, "current")
            self.assertEqual("RUN_COLLISION", context.exception.code)

    def test_15_failure_summary_never_labels_prior_run_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, "previous", "2026-08-30T01:00:00+00:00", [event("MRVL", "old")])
            summary = latest_known_summary(root, "SEC_ACCESS_BLOCKED")
            self.assertEqual("SEC_ACCESS_BLOCKED", summary["schedule_status"])
            self.assertEqual("LAST_KNOWN", summary["freshness_status"])
            self.assertIsNone(summary["decision_as_of"])
            self.assertEqual("previous", summary["previous_run_id"])

    def test_16_failure_without_prior_run_is_baseline_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = latest_known_summary(Path(directory), "SEC_RATE_LIMITED")
            self.assertEqual("BASELINE_ONLY", summary["freshness_status"])
            self.assertIsNone(summary["previous_run_id"])

    def test_17_routine_prospectus_aggregation_regression_is_preserved(self) -> None:
        routine = [event("JPM", f"424b2-{index}", form="424B2") for index in range(25)]
        high = event("MRVL", "high", materiality="HIGH")
        view = build_dashboard_view([high, *routine])
        self.assertEqual(1, view["high_event_count"])
        self.assertEqual(1, len(view["routine_aggregates"]))
        self.assertEqual(25, view["routine_aggregates"][0]["count"])
        self.assertEqual(0, view["individual_routine_top_events"])
        self.assertEqual("NOT_VERIFIED", view["confirmed_convertible_dilution"])

    def test_18_scheduled_components_have_no_network_or_secret_persistence_path(self) -> None:
        python_source = (SCRIPT_ROOT / "sec_scheduled_shadow.py").read_text(encoding="utf-8")
        wrapper_source = WRAPPER_PATH.read_text(encoding="utf-8")
        registration_source = REGISTER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("urllib", python_source)
        self.assertNotIn("requests", python_source)
        self.assertNotIn("Invoke-WebRequest", wrapper_source + registration_source)
        self.assertNotIn("SetEnvironmentVariable", wrapper_source + registration_source)
        self.assertNotIn("SEC_USER_AGENT=", wrapper_source + registration_source)
        self.assertNotIn("Unregister-ScheduledTask", registration_source)

    def test_19_existing_live_artifact_offline_radar_regression(self) -> None:
        default_path = (
            ROOT / "workspace/outputs/official-event-intake/sec/2026-08-30"
            / "sec-official-20260830T141948864095Z/normalized-events.json"
        )
        artifact_path = Path(os.environ.get("SEC_LIVE_NORMALIZED_ARTIFACT", default_path))
        if not artifact_path.is_file():
            self.skipTest("Existing immutable live SEC artifact is not present")
        before = file_hash(artifact_path)
        events = load_json(artifact_path)["events"]
        view = build_dashboard_view(events)
        jpm_events = [item for item in events if item["ticker"] == "JPM"]
        aggregate_counts = {
            (item["ticker"], item["form"]): item["count"] for item in view["routine_aggregates"]
        }
        self.assertEqual(924, len(events))
        self.assertEqual(902, len(jpm_events))
        self.assertEqual(881, sum(item["form"] == "424B2" for item in jpm_events))
        self.assertEqual(21, sum(item["form"] == "424B3" for item in jpm_events))
        self.assertEqual(7, view["high_event_count"])
        self.assertEqual(881, aggregate_counts[("JPM", "424B2")])
        self.assertEqual(21, aggregate_counts[("JPM", "424B3")])
        self.assertEqual(0, view["individual_routine_top_events"])
        self.assertEqual("NOT_VERIFIED", view["confirmed_convertible_dilution"])
        self.assertEqual(before, file_hash(artifact_path))

    def test_20_timezone_preflight_is_pure_and_fail_closed(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        command = (
            f". '{PREFLIGHT_PATH}'; "
            "$pass = Get-SecScheduledShadowPreflight -TimezoneId 'Korea Standard Time' "
            "-ProcessUserAgent 'process-secret@example.invalid' -PersistentUserAgent 'persistent-secret@example.invalid'; "
            "$fail = Get-SecScheduledShadowPreflight -TimezoneId 'UTC' "
            "-ProcessUserAgent 'process-secret@example.invalid' -PersistentUserAgent 'persistent-secret@example.invalid'; "
            "@{pass=$pass;fail=$fail} | ConvertTo-Json -Depth 4 -Compress"
        )
        result = subprocess.run(
            [executable, "-NoProfile", "-Command", command],
            cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["pass"]["ActivationReady"])
        self.assertEqual("PASS", output["pass"]["TimezonePreflight"])
        self.assertFalse(output["fail"]["ActivationReady"])
        self.assertEqual("WINDOWS_TIMEZONE_MISMATCH", output["fail"]["FailureCode"])
        self.assertNotIn("process-secret", result.stdout + result.stderr)
        self.assertNotIn("persistent-secret", result.stdout + result.stderr)

    def test_21_process_user_agent_does_not_replace_persistent_user_environment(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        command = (
            f". '{PREFLIGHT_PATH}'; "
            "Get-SecScheduledShadowPreflight -TimezoneId 'Korea Standard Time' "
            "-ProcessUserAgent 'temporary-only@example.invalid' -PersistentUserAgent '' | "
            "ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            [executable, "-NoProfile", "-Command", command],
            cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("CONFIGURED", output["ProcessUserAgent"])
        self.assertEqual("NOT_CONFIGURED", output["PersistentUserAgent"])
        self.assertEqual("SEC_USER_AGENT_USER_ENV_REQUIRED", output["FailureCode"])
        self.assertFalse(output["ActivationReady"])
        self.assertNotIn("temporary-only", result.stdout + result.stderr)

    def test_22_registration_preflights_precede_exact_task_mutation(self) -> None:
        source = REGISTER_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("Assert-ScheduleContract"), source.index("$preflight = Get-SecScheduledShadowSystemPreflight"))
        self.assertLess(source.index("if (-not $preflight.ActivationReady)"), source.index("Register-ScheduledTask"))
        self.assertLess(source.index("if (-not (Test-Path -LiteralPath $wrapperPath"), source.index("Register-ScheduledTask"))
        self.assertNotIn("Set-TimeZone", source)
        self.assertNotIn("SetEnvironmentVariable", source)
        self.assertNotIn("Unregister-ScheduledTask", source)

    def test_23_plan_reports_preflights_without_operational_attempt_or_mutation(self) -> None:
        result = self.run_plan()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("TIMEZONE_PREFLIGHT = PASS", result.stdout)
        self.assertIn("PROCESS_USER_AGENT = NOT_CONFIGURED", result.stdout)
        self.assertIn("PERSISTENT_USER_AGENT =", result.stdout)
        self.assertIn("ACTIVATION_READY = FALSE", result.stdout)
        self.assertIn("NEW_LOGON_SESSION_REQUIRED_AFTER_CHANGE = TRUE", result.stdout)
        self.assertIn("TASK_MUTATION = NO", result.stdout)
        self.assertNotIn("scheduled-attempt.json", result.stdout)

    def test_24_failure_attempt_without_prior_is_create_only_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            started = "2026-08-31T01:00:00+00:00"
            summary = latest_known_summary(root / "sec", "SEC_USER_AGENT_REQUIRED")
            path = write_scheduled_attempt(
                attempt_output_root=root / "attempts", summary=summary, attempt_id="attempt-baseline",
                started_at=started, attempt_result="BLOCKED", failure_code="SEC_USER_AGENT_REQUIRED",
                network_started=False, sec_live_request_count_if_known=None, runner_exit_code=2,
                user_agent_configured=False, persistent_user_agent_configured=True,
                timezone_id="Korea Standard Time", timezone_preflight_status="PASS",
            )
            attempt = load_json(path)
            self.assertEqual("BASELINE_ONLY", attempt["freshness_status"])
            self.assertIsNone(attempt["last_known_run_id"])
            self.assertFalse(attempt["network_started"])
            self.assertEqual([], validate_instance(attempt, ATTEMPT_SCHEMA))

    def test_25_failure_attempt_with_compatible_prior_is_last_known(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sec_root = root / "sec"
            previous = write_run(sec_root, "previous", "2026-08-30T01:00:00+00:00", [event("MRVL", "old")])
            protected = [previous / "normalized-events.json", previous / "run-manifest.json"]
            before = {path: file_hash(path) for path in protected}
            summary = latest_known_summary(sec_root, "SEC_ACCESS_BLOCKED")
            path = write_scheduled_attempt(
                attempt_output_root=root / "attempts", summary=summary, attempt_id="attempt-last-known",
                started_at="2026-08-31T01:00:00+00:00", attempt_result="FAIL",
                failure_code="SEC_ACCESS_BLOCKED", network_started=True,
                sec_live_request_count_if_known=None, runner_exit_code=2,
                user_agent_configured=True, persistent_user_agent_configured=True,
                timezone_id="Korea Standard Time", timezone_preflight_status="PASS",
            )
            attempt = load_json(path)
            self.assertEqual("LAST_KNOWN", attempt["freshness_status"])
            self.assertEqual("previous", attempt["last_known_run_id"])
            self.assertEqual(before, {item: file_hash(item) for item in protected})

    def test_26_incompatible_prior_is_never_last_known(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(
                root, "incompatible", "2026-08-30T01:00:00+00:00", [event("MRVL", "old")],
                watchlist=["MRVL"],
            )
            status, previous = discover_latest_compatible_successful_run(root)
            summary = latest_known_summary(root, "PROCESS_ERROR")
            self.assertEqual("PREVIOUS_RUN_INCOMPATIBLE", status)
            self.assertIsNone(previous)
            self.assertEqual("BASELINE_ONLY", summary["freshness_status"])
            self.assertIsNone(summary["previous_run_id"])

    def test_27_success_attempt_is_current_and_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sec_root = root / "sec"
            current_directory = write_run(sec_root, "current", "2026-08-31T01:00:00+00:00", [event("MRVL", "new")])
            protected = [current_directory / "normalized-events.json", current_directory / "run-manifest.json"]
            before = {path: file_hash(path) for path in protected}
            summary = write_scheduled_artifacts(sec_root, "current")
            path = write_scheduled_attempt(
                attempt_output_root=root / "attempts", summary=summary, attempt_id="attempt-success",
                started_at="2026-08-31T01:00:00+00:00", attempt_result="PASS", failure_code=None,
                network_started=True, sec_live_request_count_if_known=7, runner_exit_code=0,
                user_agent_configured=True, persistent_user_agent_configured=True,
                timezone_id="Korea Standard Time", timezone_preflight_status="PASS",
            )
            attempt = load_json(path)
            self.assertEqual("CURRENT_RUN", attempt["freshness_status"])
            self.assertEqual("current", attempt["current_run_id"])
            self.assertEqual(7, attempt["sec_live_request_count_if_known"])
            self.assertEqual(before, {item: file_hash(item) for item in protected})

    def test_28_attempt_collision_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            started = "2026-08-31T01:00:00+00:00"
            summary = latest_known_summary(root / "sec", "PROCESS_ERROR")
            kwargs = dict(
                attempt_output_root=root / "attempts", summary=summary, attempt_id="same-attempt",
                started_at=started, attempt_result="FAIL", failure_code="PROCESS_ERROR",
                network_started=True, sec_live_request_count_if_known=None, runner_exit_code=3,
                user_agent_configured=True, persistent_user_agent_configured=True,
                timezone_id="Korea Standard Time", timezone_preflight_status="PASS",
            )
            path = write_scheduled_attempt(**kwargs)
            before = file_hash(path)
            with self.assertRaises(IntakeError) as context:
                write_scheduled_attempt(**kwargs)
            self.assertEqual("RUN_COLLISION", context.exception.code)
            self.assertEqual(before, file_hash(path))

    def test_29_early_failure_rejects_network_started_true(self) -> None:
        summary = {
            "freshness_status": "BASELINE_ONLY", "previous_run_id": None,
            "previous_run_as_of": None, "diff_status": "BASELINE_ONLY",
        }
        with self.assertRaises(IntakeError):
            build_scheduled_attempt(
                summary=summary, attempt_id="invalid-network", started_at="2026-08-31T01:00:00+00:00",
                attempt_result="BLOCKED", failure_code="SEC_USER_AGENT_REQUIRED", network_started=True,
                sec_live_request_count_if_known=None, runner_exit_code=2, user_agent_configured=False,
                persistent_user_agent_configured=True, timezone_id="Korea Standard Time",
                timezone_preflight_status="PASS",
            )

    def test_30_attempt_schema_and_sources_have_no_plaintext_secret_field(self) -> None:
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (WRAPPER_PATH, REGISTER_PATH, PREFLIGHT_PATH, SCRIPT_ROOT / "sec_scheduled_shadow.py")
        )
        schema = load_json(ATTEMPT_SCHEMA)
        self.assertNotIn("SEC_USER_AGENT=", sources)
        self.assertNotIn("SetEnvironmentVariable", sources)
        self.assertNotIn("email", json.dumps(schema).casefold())
        self.assertNotIn("credential", json.dumps(schema).casefold())
        self.assertNotIn("cookie", json.dumps(schema).casefold())

    def test_31_timezone_mismatch_wrapper_creates_blocked_attempt_without_runner(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "manage-us-stock-strategy/scripts"
            write_fake_preflight(scripts, timezone_id="UTC")
            marker = root / "runner-called.txt"
            (scripts / "sec_official_event_intake.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).write_text('called')\n", encoding="utf-8"
            )
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = "do-not-print@example.invalid"
            attempt_root = root / "attempts"
            result = subprocess.run(
                [executable, "-NoProfile", "-File", str(WRAPPER_PATH), "-RepositoryRoot", str(root),
                 "-PythonPath", sys.executable, "-AttemptOutputRoot", str(attempt_root), "-AttemptId", "timezone-block"],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertIn("WINDOWS_TIMEZONE_MISMATCH", result.stdout)
            self.assertFalse(marker.exists())
            attempt = load_json(next(attempt_root.rglob("scheduled-attempt.json")))
            self.assertFalse(attempt["network_started"])
            self.assertEqual("FAIL", attempt["timezone_preflight_status"])
            self.assertNotIn("do-not-print", result.stdout + result.stderr + json.dumps(attempt))

    def test_32_process_only_user_agent_wrapper_blocks_and_persists_evidence(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "manage-us-stock-strategy/scripts"
            write_fake_preflight(scripts, process_configured=True, persistent_configured=False)
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = "temporary-only@example.invalid"
            attempt_root = root / "attempts"
            result = subprocess.run(
                [executable, "-NoProfile", "-File", str(WRAPPER_PATH), "-RepositoryRoot", str(root),
                 "-PythonPath", sys.executable, "-AttemptOutputRoot", str(attempt_root), "-AttemptId", "persistent-block"],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertIn("SEC_USER_AGENT_USER_ENV_REQUIRED", result.stdout)
            attempt = load_json(next(attempt_root.rglob("scheduled-attempt.json")))
            self.assertTrue(attempt["user_agent_configured"])
            self.assertFalse(attempt["persistent_user_agent_configured"])
            self.assertFalse(attempt["network_started"])
            self.assertNotIn("temporary-only", result.stdout + result.stderr + json.dumps(attempt))

    def test_33_runner_not_found_creates_blocked_attempt_without_network(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fake_preflight(root / "manage-us-stock-strategy/scripts")
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = "configured-but-redacted@example.invalid"
            attempt_root = root / "attempts"
            result = subprocess.run(
                [executable, "-NoProfile", "-File", str(WRAPPER_PATH), "-RepositoryRoot", str(root),
                 "-PythonPath", sys.executable, "-AttemptOutputRoot", str(attempt_root), "-AttemptId", "runner-missing"],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(3, result.returncode, result.stderr)
            self.assertIn("RUNNER_NOT_FOUND", result.stdout)
            attempt = load_json(next(attempt_root.rglob("scheduled-attempt.json")))
            self.assertEqual("RUNNER_NOT_FOUND", attempt["failure_code"])
            self.assertFalse(attempt["network_started"])
            self.assertNotIn("configured-but-redacted", result.stdout + result.stderr + json.dumps(attempt))

    def test_34_python_runtime_not_found_creates_blocked_attempt(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "manage-us-stock-strategy/assets"
            scripts = root / "manage-us-stock-strategy/scripts"
            assets.mkdir(parents=True)
            scripts.mkdir(parents=True)
            shutil.copyfile(CONTRACT_PATH, assets / CONTRACT_PATH.name)
            write_fake_preflight(scripts)
            (scripts / "sec_official_event_intake.py").write_text("raise SystemExit(99)\n", encoding="utf-8")
            (scripts / "sec_scheduled_shadow.py").write_text("raise SystemExit(99)\n", encoding="utf-8")
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = "configured-but-redacted@example.invalid"
            attempt_root = root / "attempts"
            result = subprocess.run(
                [executable, "-NoProfile", "-File", str(WRAPPER_PATH), "-RepositoryRoot", str(root),
                 "-PythonPath", str(root / "missing-python.exe"), "-AttemptOutputRoot", str(attempt_root),
                 "-AttemptId", "python-missing"],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(3, result.returncode, result.stderr)
            self.assertIn("PYTHON_RUNTIME_NOT_FOUND", result.stdout)
            attempt = load_json(next(attempt_root.rglob("scheduled-attempt.json")))
            self.assertEqual("PYTHON_RUNTIME_NOT_FOUND", attempt["failure_code"])
            self.assertFalse(attempt["network_started"])
            self.assertEqual([], validate_instance(attempt, ATTEMPT_SCHEMA))

    def test_35_late_runner_failure_finalizes_attempt_and_preserves_exit_code(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "manage-us-stock-strategy/assets"
            schemas = root / "manage-us-stock-strategy/schemas"
            scripts = root / "manage-us-stock-strategy/scripts"
            assets.mkdir(parents=True)
            schemas.mkdir(parents=True)
            scripts.mkdir(parents=True)
            shutil.copyfile(CONTRACT_PATH, assets / CONTRACT_PATH.name)
            shutil.copyfile(ATTEMPT_SCHEMA, schemas / ATTEMPT_SCHEMA.name)
            shutil.copyfile(SCRIPT_ROOT / "sec_scheduled_shadow.py", scripts / "sec_scheduled_shadow.py")
            shutil.copyfile(SCRIPT_ROOT / "validation_common.py", scripts / "validation_common.py")
            write_fake_preflight(scripts)
            (scripts / "sec_official_event_intake.py").write_text(
                "import json, sys\n"
                "from pathlib import Path\n"
                "DEFAULT_OUTPUT_ROOT = Path('.')\n"
                "DEFAULT_RULES_PATH = Path('unused-rules.json')\n"
                "PIPELINE_VERSION = '0.1'\n"
                "class IntakeError(RuntimeError):\n"
                "    def __init__(self, code, detail=''):\n"
                "        super().__init__(code)\n"
                "        self.code = code\n"
                "def create_only_json(path, value):\n"
                "    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)\n"
                "    with path.open('x', encoding='utf-8') as handle: json.dump(value, handle)\n"
                "def create_only_write(path, value):\n"
                "    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)\n"
                "    with path.open('x', encoding='utf-8') as handle: handle.write(value)\n"
                "if __name__ == '__main__':\n"
                "    print(json.dumps({'status':'BLOCKED','code':'SEC_ACCESS_BLOCKED'}), file=sys.stderr)\n"
                "    raise SystemExit(7)\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = "configured-but-redacted@example.invalid"
            attempt_root = root / "attempts"
            result = subprocess.run(
                [executable, "-NoProfile", "-File", str(WRAPPER_PATH), "-RepositoryRoot", str(root),
                 "-PythonPath", sys.executable, "-OutputRoot", str(root / "sec"),
                 "-AttemptOutputRoot", str(attempt_root), "-AttemptId", "late-failure"],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(7, result.returncode, result.stderr)
            self.assertIn("SEC_ACCESS_BLOCKED", result.stdout + result.stderr)
            attempt = load_json(next(attempt_root.rglob("scheduled-attempt.json")))
            self.assertEqual("FAIL", attempt["attempt_result"])
            self.assertEqual("SEC_ACCESS_BLOCKED", attempt["failure_code"])
            self.assertTrue(attempt["network_started"])
            self.assertEqual(7, attempt["runner_exit_code"])
            self.assertEqual([], validate_instance(attempt, ATTEMPT_SCHEMA))
            self.assertNotIn("configured-but-redacted", result.stdout + result.stderr + json.dumps(attempt))

    def test_36_failure_discovery_excludes_current_attempt_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root, "prior", "2026-08-30T01:00:00+00:00", [event("MRVL", "old")])
            write_run(root, "current-attempt", "2026-08-31T01:00:00+00:00", [event("MRVL", "new")])
            summary = latest_known_summary(root, "PROCESS_ERROR", exclude_run_id="current-attempt")
            self.assertEqual("LAST_KNOWN", summary["freshness_status"])
            self.assertEqual("prior", summary["previous_run_id"])

    def test_37_wrapper_duplicate_attempt_id_fails_closed_before_runner(self) -> None:
        executable = powershell_executable()
        if executable is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "manage-us-stock-strategy/assets"
            schemas = root / "manage-us-stock-strategy/schemas"
            scripts = root / "manage-us-stock-strategy/scripts"
            assets.mkdir(parents=True)
            schemas.mkdir(parents=True)
            scripts.mkdir(parents=True)
            shutil.copyfile(CONTRACT_PATH, assets / CONTRACT_PATH.name)
            shutil.copyfile(ATTEMPT_SCHEMA, schemas / ATTEMPT_SCHEMA.name)
            shutil.copyfile(SCRIPT_ROOT / "sec_scheduled_shadow.py", scripts / "sec_scheduled_shadow.py")
            shutil.copyfile(SCRIPT_ROOT / "validation_common.py", scripts / "validation_common.py")
            write_fake_preflight(scripts)
            runner_count = root / "runner-count.txt"
            (scripts / "sec_official_event_intake.py").write_text(
                "import json, sys\n"
                "from pathlib import Path\n"
                "DEFAULT_OUTPUT_ROOT = Path('.')\n"
                "DEFAULT_RULES_PATH = Path('unused-rules.json')\n"
                "PIPELINE_VERSION = '0.1'\n"
                "class IntakeError(RuntimeError):\n"
                "    def __init__(self, code, detail=''):\n"
                "        super().__init__(code)\n"
                "        self.code = code\n"
                "def create_only_json(path, value):\n"
                "    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)\n"
                "    with path.open('x', encoding='utf-8') as handle: json.dump(value, handle)\n"
                "def create_only_write(path, value):\n"
                "    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)\n"
                "    with path.open('x', encoding='utf-8') as handle: handle.write(value)\n"
                "if __name__ == '__main__':\n"
                f"    marker = Path({str(runner_count)!r})\n"
                "    count = int(marker.read_text(encoding='utf-8')) if marker.exists() else 0\n"
                "    marker.write_text(str(count + 1), encoding='utf-8')\n"
                "    print(json.dumps({'status':'BLOCKED','code':'SEC_ACCESS_BLOCKED'}), file=sys.stderr)\n"
                "    raise SystemExit(7)\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["SEC_USER_AGENT"] = "configured-but-redacted@example.invalid"
            attempt_root = root / "attempts"
            arguments = [
                executable, "-NoProfile", "-File", str(WRAPPER_PATH),
                "-RepositoryRoot", str(root), "-PythonPath", sys.executable,
                "-OutputRoot", str(root / "sec"), "-AttemptOutputRoot", str(attempt_root),
                "-AttemptId", "fixed-test-attempt-id",
            ]
            first = subprocess.run(
                arguments, cwd=ROOT, env=environment, text=True, capture_output=True,
                timeout=30, check=False,
            )
            self.assertEqual(7, first.returncode, first.stderr)
            artifact_path = next(attempt_root.rglob("scheduled-attempt.json"))
            artifact_before = artifact_path.read_bytes()
            hash_before = file_hash(artifact_path)
            first_artifact = json.loads(artifact_before)
            self.assertEqual(1, int(runner_count.read_text(encoding="utf-8")))

            second = subprocess.run(
                arguments, cwd=ROOT, env=environment, text=True, capture_output=True,
                timeout=30, check=False,
            )
            self.assertEqual(3, second.returncode, second.stderr)
            second_result = json.loads(second.stdout.strip().splitlines()[-1])
            self.assertEqual("RUN_COLLISION", second_result["SCHEDULE_STATUS"])
            self.assertEqual("RUN_COLLISION", second_result["FAILURE_CODE"])
            self.assertEqual("BLOCKED", second_result["ATTEMPT_RESULT"])
            self.assertEqual("NOT_AVAILABLE", second_result["FRESHNESS_STATUS"])
            self.assertFalse(second_result["NETWORK_STARTED"])
            self.assertFalse(second_result["SEC_RUNNER_INVOKED"])
            self.assertFalse(second_result["TASK_MUTATION"])
            self.assertEqual(1, int(runner_count.read_text(encoding="utf-8")))
            self.assertEqual(hash_before, file_hash(artifact_path))
            self.assertEqual(artifact_before, artifact_path.read_bytes())
            self.assertEqual(1, len(list(attempt_root.rglob("scheduled-attempt.json"))))
            self.assertNotEqual(first_artifact["freshness_status"], second_result["FRESHNESS_STATUS"])
            self.assertNotEqual(first_artifact["failure_code"], second_result["FAILURE_CODE"])


if __name__ == "__main__":
    unittest.main()
