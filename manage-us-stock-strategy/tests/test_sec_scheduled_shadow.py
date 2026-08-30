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
    build_summary,
    derive_accession_diff,
    discover_previous_run,
    latest_known_summary,
    load_run_artifact,
    runs_are_compatible,
    write_scheduled_artifacts,
)
from validation_common import file_hash, load_json, validate_instance


CONTRACT_PATH = ROOT / "manage-us-stock-strategy/assets/sec-scheduled-shadow-contract-v0.1.json"
SUMMARY_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-scheduled-shadow-summary.schema.json"
WRAPPER_PATH = SCRIPT_ROOT / "run_sec_scheduled_shadow.ps1"
REGISTER_PATH = SCRIPT_ROOT / "register_sec_scheduled_shadow_task.ps1"
WATCHLIST = ["MRVL", "NBIS", "PGR", "JPM", "CME", "V"]


def powershell_executable() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")


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
                "import json\nprint(json.dumps({'schedule_status':'PASS'}))\n", encoding="utf-8"
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


if __name__ == "__main__":
    unittest.main()
