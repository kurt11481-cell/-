"""S7 calendar binding: the exposure runner and the close-history builder read the session calendar from
the Production integrated authority only. Every authority root here is a temp folder built from the
repository artifacts (line endings normalized to LF, like a committed blob), never the real policy files."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import integrated_authority_snapshot as integrated  # noqa: E402
import regular_session_close_history as rsch  # noqa: E402
import run_portfolio_exposure_review as runner  # noqa: E402

IDENTITY_HASH = "d8b03aa434c969e8fba338865eb3e6567bc78821d9b7b702e47d7403f2bc5e60"
SESSION_2026 = "2421eeb7e115ad640b6b0ec76d0d88cfe2a49499c12c39dc35ea5f71c1fed22b"
SESSION_0829 = "d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe"
COHORT = "TEST-S7-CALENDAR-BINDING"
PREVIOUS_COHORT = "TEST-S7-CALENDAR-BINDING-PREVIOUS"
ACTIVATED_AT = "2026-09-23T00:00:00+00:00"
IDENTITY_FILE = "us-equity-instrument-identity-current-v1.registry.json"
CALENDAR_FILE = "us-equities-core-session-v2.calendar.json"
POLICY = ROOT / "stock-strategy-system/alert_policy.json"
EVAL = "2026-09-30"
NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
LOADER_REASONS = ("ARTIFACT_NOT_ACTIVATED", "INTEGRITY_FAILURE", "TEMPORAL_VIOLATION")


def lf_bytes(path: Path, expected_sha256: str) -> bytes:
    """Repository artifact bytes with CRLF folded to LF (a CRLF checkout), checked against its content address."""
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise AssertionError(f"artifact does not match its address: {path}")
    return raw


def install_calendar(root: Path, session_hash: str) -> Path:
    source = ROOT / "workspace/calendar-authority/artifacts" / session_hash / CALENDAR_FILE
    target = root / "workspace/calendar-authority/artifacts" / session_hash / CALENDAR_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(lf_bytes(source, session_hash))
    return target


def build_authority_root(root: Path, *, session_hash: str = SESSION_2026, status: str = "ACTIVE",
                         activated_at: str = ACTIVATED_AT, extra_calendars: tuple[str, ...] = ()) -> Path:
    """Temp trusted root with an integrated authority manifest; returns the calendar copy it activates."""
    source = ROOT / "workspace/instrument-identity-authority/artifacts" / IDENTITY_HASH / IDENTITY_FILE
    target = root / "workspace/instrument-identity-authority/artifacts" / IDENTITY_HASH / IDENTITY_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(lf_bytes(source, IDENTITY_HASH))
    calendar = install_calendar(root, session_hash)
    for extra in extra_calendars:
        install_calendar(root, extra)
    manifest = integrated.build_combined_activation_manifest(
        trusted_root=root, identity_artifact_sha256=IDENTITY_HASH, session_calendar_artifact_sha256=session_hash,
        cohort_id=COHORT, previous_cohort_id=PREVIOUS_COHORT, activated_at=activated_at,
        activation_status="ACTIVE", activation_reason="TEST_ONLY active integrated authority fixture.")
    manifest["activation_status"] = status
    write_manifest(root, manifest)
    return calendar


def write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    path = root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))


def calendar_sessions(calendar: Path, end: str = EVAL, count: int = 3) -> list[str]:
    sessions = sorted(row["session_date"] for row in json.loads(calendar.read_text(encoding="utf-8"))["sessions"])
    return sessions[:sessions.index(end) + 1][-count:]


def write_pages(folder: Path, sessions: list[str], close: str = "100.0000") -> None:
    """Saved 30-minute pages (16:00 bar and 15:30 bar per session, newest first) for one symbol."""
    rows = []
    for session in sorted(sessions, reverse=True):
        day = session.replace("-", "")
        for label, price in (("160000", "1.0000"), ("153000", close)):
            rows.append({"cur_prc": price, "trde_qty": "1", "open_pric": price, "high_pric": price,
                         "low_pric": price, "cntr_tm": day + label, "bus_dt": day, "upd_stkpc_tp": "", "upd_rt": ""})
    for index, row in enumerate(rows):
        if index % 100 == 99 or index == len(rows) - 1:
            row["upd_stkpc_tp"] = "1f"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "p1.json").write_text(json.dumps({"result": {"result_list": rows, "return_code": 0}}), encoding="utf-8")


class AuthorityCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="s7_calendar_binding_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.trusted = self.tmp / "trusted"
        self.output_root = self.tmp / "out"
        self.state_path = self.tmp / "state/portfolio_state.json"
        self.journal_path = self.tmp / "state/decision_journal.json"
        self.closes_root = self.tmp / "closes"
        self.runs = 0
        # The trusted root and the clock are module seams (no command-line or environment override).
        # The runner loads the authority through regular_session_close_history, so that module owns the root.
        patcher = mock.patch.object(rsch, "TRUSTED_ROOT", self.trusted, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name, value in (("DEFAULT_STATE", self.state_path), ("DEFAULT_JOURNAL", self.journal_path),
                            ("DEFAULT_CLOSES_ROOT", self.closes_root)):
            patcher = mock.patch.object(runner, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        clock = mock.patch.object(runner, "current_time", side_effect=self.next_now)
        clock.start()
        self.addCleanup(clock.stop)
        clock = mock.patch.object(rsch, "current_time", side_effect=self.next_now)
        clock.start()
        self.addCleanup(clock.stop)
        self.calendar = build_authority_root(self.trusted, extra_calendars=(SESSION_0829,))
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(json.dumps({
            "schema_version": "1.3", "state_revision": 16, "holdings": {"SOXL": 30}, "available_cash_usd": 7000.0,
            "last_confirmed_broker_snapshot": {"verified": True, "holdings_complete": True, "cash_verified": True,
                                               "source": "TEST_ONLY", "as_of": "2026-09-29"},
            "timing_plan": {"policy_version": "TEST_ONLY"}}), encoding="utf-8")

    def next_now(self) -> datetime:
        """Each run gets its own clock second (result files are create-only)."""
        self.runs += 1
        return NOW.replace(second=self.runs)

    def rebuild(self, **options: Any) -> Path:
        shutil.rmtree(self.trusted)
        options.setdefault("extra_calendars", (SESSION_0829,))
        return build_authority_root(self.trusted, **options)

    def manifest_sha256(self) -> str:
        return hashlib.sha256((self.trusted / integrated.COMBINED_ACTIVATION_RELATIVE_PATH).read_bytes()).hexdigest()

    def run_review(self, *extra: str) -> tuple[int, str, dict | None]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = runner.main(["--policy", str(POLICY), "--state", str(self.state_path), "--journal",
                                str(self.journal_path), "--closes-root", str(self.closes_root), "--output-root",
                                str(self.output_root), *extra])
        files = sorted(self.output_root.glob("*/portfolio-exposure-review.*.json"))
        return code, buffer.getvalue(), json.loads(files[-1].read_text(encoding="utf-8")) if files else None

    def build_history(self, *extra: str) -> tuple[int, dict]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = rsch.main(["build", "--symbol", "SOXX", "--exchange", "NASDAQ", "--pages-dir",
                              str(self.closes_root / "pages/SOXX"), "--calendar", str(self.calendar),
                              "--output", str(self.closes_root / "history/SOXX.close-history.json"), *extra])
        return code, json.loads(buffer.getvalue())


class RunnerBindingTests(AuthorityCase):
    def test_t1_default_run_reads_the_integrated_authority_calendar(self) -> None:
        code, output, review = self.run_review()
        self.assertEqual(code, 0, output)
        calendar = review["inputs"]["calendar"]
        self.assertEqual((calendar["authority_status"], calendar["calendar_sha256"]), ("ACTIVE", SESSION_2026))
        self.assertEqual((review["evaluation_session"], review["inputs"]["evaluation_session_status"]),
                         (EVAL, "LATEST_COMPLETED_SESSION"))
        self.assertEqual(review["inputs"]["latest_completed_session"], EVAL)
        version = json.loads(self.calendar.read_text(encoding="utf-8"))["calendar_version"]
        self.assertEqual(review["inputs"]["calendar_authority"], {
            "status": "LOADED", "combined_activation_manifest_sha256": self.manifest_sha256(),
            "activation_cohort_id": COHORT, "session_calendar_artifact_sha256": SESSION_2026,
            "session_calendar_version": version})
        self.assertEqual(review["inputs"]["non_default_inputs"], [])
        self.assertEqual((review["order_authority"], review["quantity_authority"], review["execution_quantity"]),
                         (False, "none", None))
        # The same artifact passed explicitly is the active one too.
        code, _, review = self.run_review("--calendar", str(self.calendar), "--session", EVAL)
        self.assertEqual(code, 0)
        self.assertEqual(review["inputs"]["calendar"]["authority_status"], "ACTIVE")
        self.assertEqual(review["inputs"]["non_default_inputs"], [])

    def test_t2_the_old_activation_file_is_ignored(self) -> None:
        legacy = self.trusted / "workspace/policies/session_calendar_activation.json"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"activation_status": "ACTIVE", "active_calendar_hash": SESSION_0829}),
                          encoding="utf-8")
        code, output, review = self.run_review()
        self.assertEqual(code, 0, output)
        self.assertEqual(review["inputs"]["calendar"]["calendar_sha256"], SESSION_2026)
        self.assertEqual(review["evaluation_session"], EVAL)
        legacy.unlink()
        code, _, review = self.run_review()
        self.assertEqual((code, review["inputs"]["calendar"]["calendar_sha256"]), (0, SESSION_2026))
        for script in (runner, rsch):
            source = Path(script.__file__).read_text(encoding="utf-8-sig")
            self.assertNotIn("session_calendar_activation", source)
            self.assertFalse(hasattr(script, "DEFAULT_ACTIVATION"))

    def test_t3_loader_failures_stop_the_default_run_without_a_result_file(self) -> None:
        def delete_manifest() -> None:
            (self.trusted / integrated.COMBINED_ACTIVATION_RELATIVE_PATH).unlink()

        def shadow() -> None:
            self.rebuild(status="SHADOW")

        def hash_mismatch() -> None:
            path = self.trusted / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["session_calendar"]["active_calendar_hash"] = SESSION_0829
            write_manifest(self.trusted, manifest)

        def tampered_artifact() -> None:
            self.calendar.write_bytes(self.calendar.read_bytes() + b" ")

        def activated_after_the_clock() -> None:
            self.rebuild(activated_at="2026-10-05T00:00:00+00:00")

        for name, break_authority, reason in (
                ("no authority file", delete_manifest, "ARTIFACT_NOT_ACTIVATED"),
                ("shadow manifest", shadow, "ARTIFACT_NOT_ACTIVATED"),
                ("calendar hash does not match the manifest binding", hash_mismatch, "INTEGRITY_FAILURE"),
                ("artifact tampered", tampered_artifact, "INTEGRITY_FAILURE"),
                ("activated after the clock", activated_after_the_clock, "TEMPORAL_VIOLATION")):
            with self.subTest(name):
                self.rebuild()
                break_authority()
                code, output, review = self.run_review()
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(output), {"status": "FAIL", "error": f"SESSION_CALENDAR_UNAVAILABLE:{reason}"})
                self.assertIn(reason, LOADER_REASONS)
                self.assertIsNone(review)
                self.assertEqual(list(self.output_root.glob("**/*.json")) if self.output_root.exists() else [], [])

    def test_t3b_explicit_calendar_without_a_loaded_authority_is_not_active(self) -> None:
        self.rebuild(status="SHADOW")
        code, output, review = self.run_review("--calendar", str(self.calendar), "--session", EVAL)
        self.assertEqual(code, 0, output)
        self.assertEqual(review["inputs"]["calendar"]["authority_status"], "EXPLICIT_ARTIFACT_NOT_ACTIVE")
        self.assertEqual(review["inputs"]["calendar_authority"],
                         {"status": "UNAVAILABLE", "reason": "ARTIFACT_NOT_ACTIVATED"})
        self.assertEqual(review["inputs"]["non_default_inputs"], ["calendar"])

    def test_t4_explicit_other_artifact_is_not_active_and_is_labelled(self) -> None:
        other = self.trusted / "workspace/calendar-authority/artifacts" / SESSION_0829 / CALENDAR_FILE
        code, output, review = self.run_review("--calendar", str(other), "--session", "2026-08-28")
        self.assertEqual(code, 0, output)
        calendar = review["inputs"]["calendar"]
        self.assertEqual((calendar["authority_status"], calendar["calendar_sha256"]),
                         ("EXPLICIT_ARTIFACT_NOT_ACTIVE", SESSION_0829))
        # The production authority is still reported, so the difference is visible.
        self.assertEqual(review["inputs"]["calendar_authority"]["session_calendar_artifact_sha256"], SESSION_2026)
        # Added condition (a): a non-active explicit calendar is a non-default input.
        self.assertEqual(review["inputs"]["non_default_inputs"], ["calendar"])
        self.assertTrue(output.splitlines()[0].endswith(" [비표준 입력]"))
        self.assertEqual(review["activation_candidate"]["status"], "NOT_READY")

    def test_t5_history_file_cannot_claim_an_active_calendar(self) -> None:
        write_pages(self.closes_root / "pages/SOXX", calendar_sessions(self.calendar))
        code, built = self.build_history()
        self.assertEqual((code, built["calendar_authority"]), (0, "ACTIVE"))
        path = self.closes_root / "history/SOXX.close-history.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["calendar"]["authority_status"], "ACTIVE")
        # The integrated authority now activates another calendar: the file's own claim is not used.
        self.rebuild(session_hash=SESSION_0829, extra_calendars=(SESSION_2026,))
        code, output, review = self.run_review("--calendar", str(self.calendar), "--session", EVAL)
        self.assertEqual(code, 0, output)
        self.assertEqual(review["inputs"]["calendar"]["authority_status"], "EXPLICIT_ARTIFACT_NOT_ACTIVE")
        self.assertEqual(review["inputs"]["close_histories"]["SOXX"]["status"], "OK")
        reasons = next(item for item in review["fail_closed"]["triggers"] if item["id"] == "required_price_missing")
        self.assertIn("CLOSE_UNVERIFIED:SOXX:SESSION_CALENDAR_NOT_ACTIVE", reasons["reasons"])


class HistoryBuilderBindingTests(AuthorityCase):
    def setUp(self) -> None:
        super().setUp()
        write_pages(self.closes_root / "pages/SOXX", calendar_sessions(self.calendar))

    def written(self) -> dict:
        return json.loads((self.closes_root / "history/SOXX.close-history.json").read_text(encoding="utf-8"))

    def test_t6_calendar_matching_the_integrated_authority_is_active(self) -> None:
        code, built = self.build_history()
        self.assertEqual((code, built["status"], built["calendar_authority"]), (0, "OK", "ACTIVE"))
        self.assertNotIn("calendar_authority_reason", built)
        history = self.written()
        self.assertEqual(history["calendar"]["authority_status"], "ACTIVE")
        self.assertTrue(all(item["verified"] for item in history["sessions"]))
        self.assertEqual(rsch.history_errors(history), [])

    def test_t6_other_calendar_or_loader_failure_is_not_active_with_a_reason(self) -> None:
        for name, prepare, reason in (
                ("another calendar is active", lambda: self.rebuild(session_hash=SESSION_0829,
                                                                    extra_calendars=(SESSION_2026,)),
                 "CALENDAR_HASH_NOT_ACTIVE_AUTHORITY"),
                ("no authority file", lambda: (self.trusted / integrated.COMBINED_ACTIVATION_RELATIVE_PATH).unlink(),
                 "ARTIFACT_NOT_ACTIVATED"),
                ("shadow manifest", lambda: self.rebuild(status="SHADOW"), "ARTIFACT_NOT_ACTIVATED"),
                ("activated after the clock", lambda: self.rebuild(activated_at="2026-10-05T00:00:00+00:00"),
                 "TEMPORAL_VIOLATION")):
            with self.subTest(name):
                self.rebuild()
                prepare()
                target = self.closes_root / "history/SOXX.close-history.json"
                if target.exists():
                    target.unlink()
                code, built = self.build_history()
                self.assertEqual((code, built["calendar_authority"]), (0, "EXPLICIT_ARTIFACT_NOT_ACTIVE"))
                self.assertEqual(built["calendar_authority_reason"], reason)
                history = self.written()
                self.assertEqual(history["calendar"]["authority_status"], "EXPLICIT_ARTIFACT_NOT_ACTIVE")
                self.assertEqual(set(history["calendar"]),
                                 {"calendar_version", "calendar_sha256", "coverage_start", "coverage_end",
                                  "authority_status"})  # schema keys unchanged
                self.assertTrue(all(item["unverified_reasons"] == ["SESSION_CALENDAR_NOT_ACTIVE"]
                                    for item in history["sessions"]))
                self.assertEqual(rsch.history_errors(history), [])

    def test_load_calendar_decides_active_from_the_snapshot_hash_only(self) -> None:
        snapshot, failure = rsch.load_production_snapshot(NOW)
        self.assertIsNone(failure)
        self.assertEqual(snapshot.session.calendar_hash, SESSION_2026)
        self.assertEqual(rsch.load_calendar(self.calendar, snapshot)["identity"]["authority_status"], "ACTIVE")
        other = self.trusted / "workspace/calendar-authority/artifacts" / SESSION_0829 / CALENDAR_FILE
        self.assertEqual(rsch.load_calendar(other, snapshot)["identity"]["authority_status"],
                         "EXPLICIT_ARTIFACT_NOT_ACTIVE")
        self.assertEqual(rsch.load_calendar(self.calendar, None)["identity"]["authority_status"],
                         "EXPLICIT_ARTIFACT_NOT_ACTIVE")


class NoOverrideTests(unittest.TestCase):
    def test_t7_no_argument_or_environment_variable_selects_the_authority(self) -> None:
        forbidden = ("activation", "manifest", "trusted", "authority")
        runner_help = runner.build_parser().format_help().lower()
        for word in forbidden:
            self.assertNotIn(word, runner_help.replace("--calendar", ""))
        for option in ("--closes-root", "--output-root"):
            self.assertIn(option, runner_help)
        buffer = io.StringIO()
        for arguments in (["build", "--help"], ["verify", "--help"], ["--help"]):
            with contextlib.redirect_stdout(buffer), self.assertRaises(SystemExit):
                rsch.main(arguments)
        history_help = buffer.getvalue().lower()
        for word in forbidden:
            self.assertNotIn(word, history_help)
        for script in (runner, rsch):
            source = Path(script.__file__).read_text(encoding="utf-8-sig")
            self.assertNotIn("os.environ", source)
            self.assertNotIn("getenv", source)


if __name__ == "__main__":
    unittest.main()
