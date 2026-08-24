#!/usr/bin/env python3
"""Synthetic-only Session Authority V2 contract, algorithm, and filesystem tests."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

import authority_artifact_io  # noqa: E402
import session_calendar_artifact as calendar_loader  # noqa: E402
from session_authority import (  # noqa: E402
    _derive_us_market_session_authority_from_root,
    derive_us_market_session_authority,
)


ET = ZoneInfo("America/New_York")
COVERAGE_START = date(2026, 3, 2)
COVERAGE_END = date(2026, 11, 4)
CLOSURES = {date(2026, 5, 25), date(2026, 7, 3)}
EARLY_CLOSES = {date(2026, 7, 2), date(2026, 11, 27)}


def independent_canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def rfc3339_local(day: date, clock: time) -> str:
    return datetime.combine(day, clock, tzinfo=ET).isoformat()


def build_artifact(
    *, coverage_start: date = COVERAGE_START, coverage_end: date = COVERAGE_END,
) -> dict:
    sessions = []
    closures = []
    current = coverage_start
    while current <= coverage_end:
        if current in CLOSURES:
            closures.append({"closure_date": current.isoformat()})
        elif current.weekday() < 5:
            early = current in EARLY_CLOSES
            sessions.append({
                "session_date": current.isoformat(),
                "core_open_at": rfc3339_local(current, time(9, 30)),
                "core_close_at": rfc3339_local(current, time(13 if early else 16, 0)),
                "close_type": "EARLY" if early else "REGULAR",
            })
        current += timedelta(days=1)
    return {
        "artifact_schema_version": "2.0",
        "calendar_policy_identity": "US_EQUITIES_CORE_SESSION_V2",
        "timezone_identity": "America/New_York",
        "operating_mic_scope": ["XNYS", "XNAS", "XCBO"],
        "source_families": ["NYSE_GROUP", "NASDAQ", "CBOE"],
        "coverage_start": coverage_start.isoformat(),
        "coverage_end": coverage_end.isoformat(),
        "source_bundle_id": "synthetic-independent-bundle-v1",
        "source_bundle_hash": "a" * 64,
        "calendar_version": "synthetic-2026-v1",
        "generated_at": "2026-02-02T00:00:00+00:00",
        "authority_as_of": "2026-02-01T00:00:00+00:00",
        "operating_mic_agreement_status": "VERIFIED",
        "sessions": sessions,
        "closures": closures,
    }


def activation_for(artifact: dict, artifact_hash: str, *, status: str = "ACTIVE") -> dict:
    return {
        "activation_schema_version": "2.0",
        "activation_status": status,
        "activation_reason_code": (
            "INITIAL_BOOTSTRAP" if status == "ACTIVE" else "MANUAL_DEACTIVATION"
        ),
        "activation_reason": "Synthetic fixture only",
        "calendar_policy_identity": artifact["calendar_policy_identity"],
        "active_calendar_hash": artifact_hash,
        "active_calendar_version": artifact["calendar_version"],
        "timezone_identity": artifact["timezone_identity"],
        "operating_mic_scope": list(artifact["operating_mic_scope"]),
        "source_families": list(artifact["source_families"]),
        "coverage_start": artifact["coverage_start"],
        "coverage_end": artifact["coverage_end"],
        "source_bundle_id": artifact["source_bundle_id"],
        "source_bundle_hash": artifact["source_bundle_hash"],
        "authority_as_of": artifact["authority_as_of"],
        "activated_at": "2026-02-03T00:00:00+00:00",
        "authority_modes_allowed": ["CURRENT"],
        "activation_cohort_id": "synthetic-shared-authority-cohort",
    }


def write_fixture(
    trusted_root: Path,
    *,
    artifact: dict | None = None,
    status: str = "ACTIVE",
    activation_mutator=None,
) -> tuple[Path, Path, dict, dict]:
    value = artifact or build_artifact()
    artifact_raw = independent_canonical_bytes(value)
    artifact_hash = hashlib.sha256(artifact_raw).hexdigest()
    activation = activation_for(value, artifact_hash, status=status)
    if activation_mutator is not None:
        activation_mutator(activation)
    activation_path = trusted_root / "workspace/policies/session_calendar_activation.json"
    artifact_path = (
        trusted_root
        / "workspace/calendar-authority/artifacts"
        / artifact_hash
        / "us-equities-core-session-v2.calendar.json"
    )
    activation_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    activation_path.write_bytes(independent_canonical_bytes(activation))
    artifact_path.write_bytes(artifact_raw)
    return activation_path, artifact_path, activation, value


def derive(trusted_root: Path, observed_at: str, *, mic: str | None = "XNAS", **kwargs):
    return _derive_us_market_session_authority_from_root(
        observed_at,
        primary_listing_operating_mic=mic,
        trusted_root=trusted_root,
        **kwargs,
    )


def create_directory_reparse(link: Path, target: Path) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr or completed.stdout)
    else:
        link.symlink_to(target, target_is_directory=True)


def remove_directory_reparse(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()


class SessionAuthorityTest(unittest.TestCase):
    def test_01_activation_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            view = derive(Path(directory), "2026-08-24T14:00:00+00:00")
        self.assertEqual(("NOT_VERIFIED", "ARTIFACT_NOT_ACTIVATED"), (
            view.authority_status, view.authority_reason,
        ))

    def test_02_activation_inactive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, status="INACTIVE")
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("ARTIFACT_NOT_ACTIVATED", view.authority_reason)

    def test_03_public_api_has_no_arbitrary_artifact_path(self):
        parameters = inspect.signature(derive_us_market_session_authority).parameters
        self.assertTrue({"root", "trusted_root", "artifact_path", "activation_path"}.isdisjoint(parameters))
        self.assertEqual({}, inspect.signature(calendar_loader.load_active_session_calendar).parameters)

    def test_04_public_api_has_no_arbitrary_hash(self):
        parameters = inspect.signature(derive_us_market_session_authority).parameters
        self.assertTrue({"calendar_hash", "active_calendar_hash", "expected_session"}.isdisjoint(parameters))

    def test_05_correct_activation_and_artifact_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual(("VERIFIED", "OK", "2026-08-21"), (
            view.authority_status,
            view.authority_reason,
            view.expected_completed_session.session_date,
        ))

    def test_06_one_byte_artifact_mutation_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, artifact_path, _, _ = write_fixture(root)
            raw = artifact_path.read_bytes()
            artifact_path.write_bytes(raw[:-1] + b" \n")
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_07_wrong_active_hash_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, activation_mutator=lambda value: value.update(active_calendar_hash="0" * 64))
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_08_wrong_policy_identity_fails_integrity(self):
        artifact = build_artifact()
        artifact["calendar_policy_identity"] = "ATTACKER_POLICY"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_09_activation_artifact_operating_scope_mismatch_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(
                root,
                activation_mutator=lambda value: value.update(
                    operating_mic_scope=["XNYS", "XNAS", "XNYS"]
                ),
            )
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_10_coverage_binding_mismatch_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, activation_mutator=lambda value: value.update(coverage_start="2026-03-03"))
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_11_source_bundle_binding_mismatch_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, activation_mutator=lambda value: value.update(source_bundle_id="other"))
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_12_future_authority_as_of_is_temporal_violation(self):
        artifact = build_artifact()
        artifact["authority_as_of"] = "2026-09-01T00:00:00+00:00"
        artifact["generated_at"] = "2026-09-02T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(
                root,
                artifact=artifact,
                activation_mutator=lambda value: value.update(
                    activated_at="2026-09-03T00:00:00+00:00"
                ),
            )
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("TEMPORAL_VIOLATION", view.authority_reason)

    def test_13_future_generated_at_is_temporal_violation(self):
        artifact = build_artifact()
        artifact["generated_at"] = "2026-09-02T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(
                root,
                artifact=artifact,
                activation_mutator=lambda value: value.update(
                    activated_at="2026-09-03T00:00:00+00:00"
                ),
            )
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("TEMPORAL_VIOLATION", view.authority_reason)

    def test_14_future_activated_at_is_temporal_violation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(
                root,
                activation_mutator=lambda value: value.update(activated_at="2026-09-02T00:00:00+00:00"),
            )
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("TEMPORAL_VIOLATION", view.authority_reason)

    def test_15_missing_primary_mic_fails_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = derive(root, "2026-08-24T14:00:00+00:00", mic=None)
        self.assertEqual("WRONG_EXCHANGE_SCOPE", view.authority_reason)

    def test_16_outside_primary_mic_fails_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = derive(root, "2026-08-24T14:00:00+00:00", mic="BATS")
        self.assertEqual("WRONG_EXCHANGE_SCOPE", view.authority_reason)

    def test_17_approved_mics_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            for mic in ("XNYS", "XNAS", "XCBO"):
                with self.subTest(mic=mic):
                    self.assertEqual("VERIFIED", derive(root, "2026-08-24T14:00:00+00:00", mic=mic).authority_status)

    def test_17a_segment_mics_are_rejected_as_operating_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            for mic in ("ARCX", "BATS", "XNGS", "XNMS"):
                with self.subTest(mic=mic):
                    self.assertEqual(
                        "WRONG_EXCHANGE_SCOPE",
                        derive(root, "2026-08-24T14:00:00+00:00", mic=mic).authority_reason,
                    )

    def test_17b_source_families_and_old_v1_fields_fail_closed(self):
        missing_family = build_artifact()
        missing_family["source_families"] = ["NYSE_GROUP", "NASDAQ"]
        old_v1 = build_artifact()
        old_v1["artifact_schema_version"] = "1.0"
        old_v1["calendar_policy_identity"] = "US_EQUITIES_CORE_SESSION_V1"
        old_v1["venue_scope"] = ["ARCX", "XNAS", "XNYS"]
        for artifact in (missing_family, old_v1):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_fixture(root, artifact=artifact)
                self.assertEqual(
                    "INTEGRITY_FAILURE",
                    derive(root, "2026-08-24T14:00:00+00:00").authority_reason,
                )

    def assert_expected(self, timestamp: str, expected: str, *, phase: str | None = None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = derive(root, timestamp)
        self.assertEqual("VERIFIED", view.authority_status)
        self.assertEqual(expected, view.expected_completed_session.session_date)
        if phase is not None:
            self.assertEqual(phase, view.market_phase)
        return view

    def test_18_monday_intraday_uses_previous_session(self):
        self.assert_expected("2026-08-24T14:00:00+00:00", "2026-08-21", phase="CORE_OPEN")

    def test_19_monday_after_close_still_uses_previous_session(self):
        self.assert_expected("2026-08-24T21:00:00+00:00", "2026-08-21", phase="POST_CORE")

    def test_20_tuesday_et_rollover_uses_monday(self):
        self.assert_expected("2026-08-25T04:01:00+00:00", "2026-08-24", phase="PRE_CORE")

    def test_21_saturday_uses_friday(self):
        self.assert_expected("2026-08-22T16:00:00+00:00", "2026-08-21", phase="NON_TRADING_DATE")

    def test_22_regular_holiday_uses_prior_session(self):
        self.assert_expected("2026-05-25T16:00:00+00:00", "2026-05-22", phase="NON_TRADING_DATE")

    def test_23_observed_holiday_uses_prior_session(self):
        view = self.assert_expected("2026-07-03T16:00:00+00:00", "2026-07-02", phase="NON_TRADING_DATE")
        self.assertEqual("EARLY", view.expected_completed_session.close_type)

    def test_24_early_close_after_actual_close_still_uses_prior_session(self):
        self.assert_expected("2026-07-02T17:30:00+00:00", "2026-07-01", phase="POST_CORE")

    def test_25_day_after_early_close_uses_early_session(self):
        view = self.assert_expected("2026-07-03T13:00:00+00:00", "2026-07-02")
        self.assertEqual("2026-07-02T13:00:00-04:00", view.expected_completed_session.core_close_at)

    def test_26_dst_spring_boundary(self):
        view = self.assert_expected("2026-03-09T14:00:00+00:00", "2026-03-06", phase="CORE_OPEN")
        self.assertTrue(view.current_date_session.core_open_at.endswith("-04:00"))
        self.assertTrue(view.expected_completed_session.core_open_at.endswith("-05:00"))

    def test_27_dst_fall_boundary(self):
        view = self.assert_expected("2026-11-02T15:00:00+00:00", "2026-10-30", phase="CORE_OPEN")
        self.assertTrue(view.current_date_session.core_open_at.endswith("-05:00"))
        self.assertTrue(view.expected_completed_session.core_open_at.endswith("-04:00"))

    def test_28_missing_previous_boundary_is_out_of_coverage(self):
        artifact = build_artifact(coverage_start=date(2026, 8, 24), coverage_end=date(2026, 8, 24))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("OUT_OF_COVERAGE", view.authority_reason)

    def test_29_decision_after_observation_is_temporal_violation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = derive(
                root,
                "2026-08-24T14:00:00+00:00",
                decision_as_of="2026-08-24T14:00:01+00:00",
            )
        self.assertEqual("TEMPORAL_VIOLATION", view.authority_reason)

    def test_30_unsupported_authority_mode_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = derive(root, "2026-08-24T14:00:00+00:00", authority_mode="REPLAY")
        self.assertEqual("INVALID_INPUT", view.authority_reason)

    def test_31_duplicate_session_fails_integrity(self):
        artifact = build_artifact()
        artifact["sessions"].insert(1, dict(artifact["sessions"][0]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_32_session_closure_overlap_fails_integrity(self):
        artifact = build_artifact()
        artifact["closures"].append({"closure_date": "2026-08-21", "closure_type": "SPECIAL_CLOSURE"})
        artifact["closures"].sort(key=lambda row: row["closure_date"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_33_wrong_et_timestamp_offset_fails_integrity(self):
        artifact = build_artifact()
        row = next(item for item in artifact["sessions"] if item["session_date"] == "2026-08-21")
        row["core_open_at"] = "2026-08-21T10:30:00-03:00"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_34_open_not_before_close_fails_integrity(self):
        artifact = build_artifact()
        row = next(item for item in artifact["sessions"] if item["session_date"] == "2026-08-21")
        row["core_open_at"] = row["core_close_at"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_35_row_outside_coverage_fails_integrity(self):
        artifact = build_artifact()
        artifact["sessions"].insert(0, {
            "session_date": "2026-02-27",
            "core_open_at": "2026-02-27T09:30:00-05:00",
            "core_close_at": "2026-02-27T16:00:00-05:00",
            "close_type": "REGULAR",
        })
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_36_missing_weekday_classification_fails_integrity(self):
        artifact = build_artifact()
        artifact["sessions"] = [row for row in artifact["sessions"] if row["session_date"] != "2026-08-20"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            view = derive(root, "2026-08-24T14:00:00+00:00")
        self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)

    def test_37_activation_symlink_or_reparse_escape_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            activation_path, _, _, _ = write_fixture(root)
            policies = activation_path.parent
            outside = base / "outside-policies"
            shutil.move(str(policies), str(outside))
            create_directory_reparse(policies, outside)
            try:
                view = derive(root, "2026-08-24T14:00:00+00:00")
                self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)
            finally:
                remove_directory_reparse(policies)

    def test_38_artifact_junction_or_reparse_escape_fails_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            _, artifact_path, _, _ = write_fixture(root)
            hash_directory = artifact_path.parent
            outside = base / "outside-artifact"
            shutil.move(str(hash_directory), str(outside))
            create_directory_reparse(hash_directory, outside)
            try:
                view = derive(root, "2026-08-24T14:00:00+00:00")
                self.assertEqual("INTEGRITY_FAILURE", view.authority_reason)
            finally:
                remove_directory_reparse(hash_directory)

    def test_39_open_handle_prevents_or_survives_substitution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, artifact_path, _, _ = write_fixture(root)
            replacement = artifact_path.with_name("replacement.json")
            replacement.write_bytes(b"{}\n")
            if os.name == "nt":
                original = authority_artifact_io._windows_read_handle
                reads = 0
                attack_rejected = False

                def racing_read(handle):
                    nonlocal reads, attack_rejected
                    reads += 1
                    if reads == 2:
                        try:
                            os.replace(replacement, artifact_path)
                        except OSError:
                            attack_rejected = True
                    return original(handle)

                with patch.object(authority_artifact_io, "_windows_read_handle", new=racing_read):
                    view = derive(root, "2026-08-24T14:00:00+00:00")
                self.assertTrue(attack_rejected)
            else:
                view = derive(root, "2026-08-24T14:00:00+00:00")
            self.assertEqual("VERIFIED", view.authority_status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
