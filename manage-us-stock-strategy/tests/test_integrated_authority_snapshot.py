from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import integrated_authority_snapshot as integrated  # noqa: E402
import build_run_manifest as run_manifest_builder  # noqa: E402
from integrated_authority_snapshot import (  # noqa: E402
    IntegratedAuthorityLoadError,
    build_combined_activation_manifest,
    derive_us_market_session_authority_from_snapshot,
    load_integrated_authority_snapshot,
    load_production_integrated_authority_snapshot,
    resolve_instrument_identity_from_snapshot,
    write_production_combined_activation_manifest,
    write_shadow_combined_activation_manifest,
    write_staged_production_combined_activation_candidate,
)
from kiwoom_adapter_io import atomic_write_json  # noqa: E402
import run_manual_portfolio_analysis as manual_preflight  # noqa: E402
from run_manual_portfolio_analysis import _authority_context  # noqa: E402
from test_manual_portfolio_analysis import (  # noqa: E402
    PROVENANCE_POLICY,
    account_reader_for,
    market_reader_for,
    system_portfolio,
)
from validation_common import load_json, validate_instance  # noqa: E402


IDENTITY_HASH = "d8b03aa434c969e8fba338865eb3e6567bc78821d9b7b702e47d7403f2bc5e60"
SESSION_HASH = "a8a3aef243c2be0abaa10b82663db383143f1fdd6c98e243b0663467d3bc7ed7"
OLD_COHORT = "identity-calendar-coordinated-activation-20260829T1906KST"
COHORT_A = "TEST-K3-COMBINED-SNAPSHOT-A"
COHORT_B = "TEST-K3-COMBINED-SNAPSHOT-B"
ACTIVATED_A = "2026-09-02T14:00:00+09:00"
ACTIVATED_B = "2026-09-02T14:01:00+09:00"
CUTOFF = "2026-09-02T18:00:00-04:00"


def _copy_artifacts(root: Path) -> None:
    identity_source = (
        ROOT / "workspace/instrument-identity-authority/artifacts" / IDENTITY_HASH
        / "us-equity-instrument-identity-current-v1.registry.json"
    )
    identity_target = (
        root / "workspace/instrument-identity-authority/artifacts" / IDENTITY_HASH
        / identity_source.name
    )
    identity_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(identity_source, identity_target)
    identity_target.chmod(0o600)
    session_source = (
        ROOT / "workspace/calendar-authority/artifacts" / SESSION_HASH
        / "us-equities-core-session-v2.calendar.json"
    )
    session_target = (
        root / "workspace/calendar-authority/artifacts" / SESSION_HASH
        / session_source.name
    )
    session_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(session_source, session_target)
    session_target.chmod(0o600)


def _manifest(root: Path, cohort: str = COHORT_A, activated_at: str = ACTIVATED_A) -> dict:
    return build_combined_activation_manifest(
        trusted_root=root,
        identity_artifact_sha256=IDENTITY_HASH,
        session_calendar_artifact_sha256=SESSION_HASH,
        cohort_id=cohort,
        previous_cohort_id=OLD_COHORT if cohort == COHORT_A else COHORT_A,
        activated_at=activated_at,
        activation_status="SHADOW",
        activation_reason="TEST_ONLY non-authoritative K3 combined activation fixture.",
    )


def _active_manifest(root: Path) -> dict:
    return build_combined_activation_manifest(
        trusted_root=root,
        identity_artifact_sha256=IDENTITY_HASH,
        session_calendar_artifact_sha256=SESSION_HASH,
        cohort_id=COHORT_A,
        previous_cohort_id=OLD_COHORT,
        activated_at=ACTIVATED_A,
        activation_status="ACTIVE",
        activation_reason="TEST_ONLY active K3 Production fixture.",
    )


def _manifest_path(root: Path) -> Path:
    return (
        root / "workspace/outputs/k3-combined-identity-session-activation"
        / "test" / "combined.shadow.json"
    )


def _write_direct(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, value)


def _create_directory_alias(link: Path, target: Path) -> bool:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.returncode == 0
    link.symlink_to(target, target_is_directory=True)
    return True


def _remove_directory_alias(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()


class IntegratedAuthoritySnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        _copy_artifacts(self.root)
        self.path = _manifest_path(self.root)
        _write_direct(self.path, _manifest(self.root))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _load(self):
        return load_integrated_authority_snapshot(
            self.path,
            trusted_root=self.root,
            decision_as_of=CUTOFF,
            required_activation_status="SHADOW",
            resolved_at=CUTOFF,
            run_id="test-k3-run",
        )

    def test_01_normal_coherent_snapshot_and_snapshot_resolvers(self):
        snapshot = self._load()
        self.assertEqual(COHORT_A, snapshot.activation_cohort_id)
        self.assertEqual(IDENTITY_HASH, snapshot.identity.registry_hash)
        self.assertEqual(SESSION_HASH, snapshot.session.calendar_hash)
        identity = resolve_instrument_identity_from_snapshot(
            snapshot, "PGR", decision_as_of=CUTOFF,
        )
        self.assertEqual("VERIFIED", identity.authority_status)
        session = derive_us_market_session_authority_from_snapshot(
            snapshot,
            CUTOFF,
            primary_listing_operating_mic=identity.primary_listing_operating_mic,
            decision_as_of=CUTOFF,
        )
        self.assertEqual("VERIFIED", session.authority_status)
        self.assertEqual("2026-09-01", session.expected_completed_session.session_date)
        self.assertEqual(COHORT_A, identity.activation_cohort_id)
        self.assertEqual(COHORT_A, session.activation_cohort_id)

    def test_02_manifest_is_read_exactly_once_and_multi_ticker_context_reuses_snapshot(self):
        original = integrated.read_once_no_reparse
        reads: list[Path] = []

        def counted(path, trusted_root):
            reads.append(Path(path))
            return original(path, trusted_root)

        with patch.object(integrated, "read_once_no_reparse", side_effect=counted):
            snapshot = self._load()
            first = _authority_context(
                ["PGR", "V"],
                observed_at=CUTOFF,
                decision_as_of=CUTOFF,
                integrated_snapshot=snapshot,
            )
            second = _authority_context(
                ["PGR", "V"],
                observed_at=CUTOFF,
                decision_as_of=CUTOFF,
                integrated_snapshot=snapshot,
            )
        normalized_target = self.path.resolve()
        self.assertEqual(1, sum(path.resolve() == normalized_target for path in reads))
        self.assertEqual(3, len(reads))
        self.assertTrue(first["integrated_authority_matched"])
        self.assertTrue(second["integrated_authority_matched"])

    def test_03_mid_run_manifest_replacement_preserves_old_snapshot_for_existing_run(self):
        old_snapshot = self._load()
        replacement = _manifest(self.root, COHORT_B, ACTIVATED_B)
        write_shadow_combined_activation_manifest(
            replacement, self.path, trusted_root=self.root,
        )
        new_snapshot = self._load()
        self.assertEqual(COHORT_A, old_snapshot.activation_cohort_id)
        self.assertEqual(COHORT_B, new_snapshot.activation_cohort_id)
        old_view = resolve_instrument_identity_from_snapshot(
            old_snapshot, "V", decision_as_of=CUTOFF,
        )
        new_view = resolve_instrument_identity_from_snapshot(
            new_snapshot, "V", decision_as_of=CUTOFF,
        )
        self.assertEqual(COHORT_A, old_view.activation_cohort_id)
        self.assertEqual(COHORT_B, new_view.activation_cohort_id)

    def test_04_missing_corrupt_truncated_and_schema_invalid_manifest_fail_closed(self):
        cases = (
            b'{"activation_schema_version":',
            b'{"activation_schema_version":"1.0"}',
            b'{"activation_schema_version":"1.0","activation_schema_version":"1.0"}',
        )
        for payload in cases:
            with self.subTest(payload=payload):
                self.path.write_bytes(payload)
                with self.assertRaises(IntegratedAuthorityLoadError) as raised:
                    self._load()
                self.assertEqual("INTEGRITY_FAILURE", raised.exception.reason)
        self.path.unlink()
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            self._load()
        self.assertEqual("ARTIFACT_NOT_ACTIVATED", raised.exception.reason)

    def test_05_identity_artifact_substitution_fails_hash_binding(self):
        target = (
            self.root / "workspace/instrument-identity-authority/artifacts" / IDENTITY_HASH
            / "us-equity-instrument-identity-current-v1.registry.json"
        )
        target.write_bytes(b"{}\n")
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            self._load()
        self.assertEqual("INTEGRITY_FAILURE", raised.exception.reason)

    def test_06_session_artifact_substitution_fails_hash_binding(self):
        target = (
            self.root / "workspace/calendar-authority/artifacts" / SESSION_HASH
            / "us-equities-core-session-v2.calendar.json"
        )
        target.write_bytes(b"{}\n")
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            self._load()
        self.assertEqual("INTEGRITY_FAILURE", raised.exception.reason)

    def test_07_binding_specific_cohort_is_forbidden_so_internal_mismatch_is_unrepresentable(self):
        value = _manifest(self.root)
        value["instrument_identity"]["activation_cohort_id"] = "DIFFERENT"
        _write_direct(self.path, value)
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            self._load()
        self.assertEqual("INTEGRITY_FAILURE", raised.exception.reason)

    def test_08_combined_failure_never_calls_legacy_loaders(self):
        self.path.write_bytes(b"{broken")
        with patch(
            "instrument_identity_artifact._load_active_instrument_identity_from_root"
        ) as identity_legacy, patch(
            "session_calendar_artifact._load_active_session_calendar_from_root"
        ) as session_legacy:
            with self.assertRaises(IntegratedAuthorityLoadError):
                self._load()
        identity_legacy.assert_not_called()
        session_legacy.assert_not_called()

    def test_09_legacy_manifest_interleaving_does_not_influence_combined_mode(self):
        policies = self.root / "workspace/policies"
        policies.mkdir(parents=True, exist_ok=True)
        identity_legacy = {"activation_cohort_id": "LEGACY-C1"}
        session_legacy = {"activation_cohort_id": "LEGACY-C0"}
        atomic_write_json(policies / "instrument_identity_activation.json", identity_legacy)
        atomic_write_json(policies / "session_calendar_activation.json", session_legacy)
        snapshot = self._load()
        self.assertEqual(COHORT_A, snapshot.activation_cohort_id)
        identity_legacy["activation_cohort_id"] = "LEGACY-C2"
        session_legacy["activation_cohort_id"] = "LEGACY-C3"
        atomic_write_json(policies / "instrument_identity_activation.json", identity_legacy)
        atomic_write_json(policies / "session_calendar_activation.json", session_legacy)
        view = resolve_instrument_identity_from_snapshot(
            snapshot, "PGR", decision_as_of=CUTOFF,
        )
        self.assertEqual(COHORT_A, view.activation_cohort_id)

    def test_10_crash_before_authoritative_replace_preserves_exact_old_bytes(self):
        old_bytes = self.path.read_bytes()
        replacement = _manifest(self.root, COHORT_B, ACTIVATED_B)

        def crash(_staged: Path, _target: Path) -> None:
            raise RuntimeError("SIMULATED_CRASH_BEFORE_REPLACE")

        with self.assertRaisesRegex(RuntimeError, "SIMULATED_CRASH"):
            write_shadow_combined_activation_manifest(
                replacement,
                self.path,
                trusted_root=self.root,
                before_replace=crash,
            )
        self.assertEqual(old_bytes, self.path.read_bytes())
        self.assertEqual(COHORT_A, self._load().activation_cohort_id)

    def test_11_single_file_atomic_replace_changes_old_to_new_coherent_snapshot(self):
        old_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        old_snapshot = self._load()
        replacement = _manifest(self.root, COHORT_B, ACTIVATED_B)
        new_hash = write_shadow_combined_activation_manifest(
            replacement, self.path, trusted_root=self.root,
        )
        new_snapshot = self._load()
        self.assertNotEqual(old_hash, new_hash)
        self.assertEqual(COHORT_A, old_snapshot.activation_cohort_id)
        self.assertEqual(COHORT_B, new_snapshot.activation_cohort_id)
        self.assertEqual(IDENTITY_HASH, new_snapshot.identity.registry_hash)
        self.assertEqual(SESSION_HASH, new_snapshot.session.calendar_hash)

    def test_12_snapshot_and_nested_identity_session_values_are_frozen(self):
        snapshot = self._load()
        with self.assertRaises(FrozenInstanceError):
            snapshot.activation_cohort_id = "MUTATED"
        with self.assertRaises(TypeError):
            snapshot.identity.artifact["registry_version"] = "MUTATED"
        with self.assertRaises(TypeError):
            snapshot.session.artifact["sessions"][0]["session_date"] = "1900-01-01"
        identity_target = (
            self.root / "workspace/instrument-identity-authority/artifacts" / IDENTITY_HASH
            / "us-equity-instrument-identity-current-v1.registry.json"
        )
        session_target = (
            self.root / "workspace/calendar-authority/artifacts" / SESSION_HASH
            / "us-equities-core-session-v2.calendar.json"
        )
        identity_target.write_bytes(b"{}\n")
        session_target.write_bytes(b"{}\n")
        view = resolve_instrument_identity_from_snapshot(
            snapshot, "PGR", decision_as_of=CUTOFF,
        )
        self.assertEqual("VERIFIED", view.authority_status)

    def test_13_provenance_binds_manifest_pair_cohort_cutoff_and_run(self):
        snapshot = self._load()
        provenance = snapshot.provenance(
            authority_source="K3_COMBINED_SHADOW", report_decision_as_of=CUTOFF,
        )
        self.assertEqual(
            hashlib.sha256(self.path.read_bytes()).hexdigest(),
            provenance["combined_activation_manifest_sha256"],
        )
        self.assertEqual(COHORT_A, provenance["activation_cohort_id"])
        self.assertEqual(IDENTITY_HASH, provenance["instrument_identity_artifact_sha256"])
        self.assertEqual(SESSION_HASH, provenance["session_calendar_artifact_sha256"])
        self.assertEqual("test-k3-run", provenance["run_id"])

    def test_14_future_snapshot_cannot_be_used_for_historical_decision(self):
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            load_integrated_authority_snapshot(
                self.path,
                trusted_root=self.root,
                decision_as_of="2026-09-01T12:00:00+09:00",
                required_activation_status="SHADOW",
            )
        self.assertEqual("TEMPORAL_VIOLATION", raised.exception.reason)

    def test_15_builder_requires_explicit_distinct_caller_supplied_cohort(self):
        for cohort in ("", OLD_COHORT):
            with self.subTest(cohort=cohort), self.assertRaises(IntegratedAuthorityLoadError):
                build_combined_activation_manifest(
                    trusted_root=self.root,
                    identity_artifact_sha256=IDENTITY_HASH,
                    session_calendar_artifact_sha256=SESSION_HASH,
                    cohort_id=cohort,
                    previous_cohort_id=OLD_COHORT,
                    activated_at=ACTIVATED_A,
                    activation_status="SHADOW",
                    activation_reason="TEST_ONLY",
                )

    def test_16_shadow_writer_cannot_alias_production_policy_namespace(self):
        target = self.root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            write_shadow_combined_activation_manifest(
                _manifest(self.root), target, trusted_root=self.root,
            )
        self.assertEqual("OUTPUT_NOT_SHADOW", raised.exception.reason)
        self.assertFalse(target.exists())

    def test_17_manual_k3_path_loads_once_and_records_snapshot_provenance(self):
        original = integrated.read_once_no_reparse
        reads: list[Path] = []

        def counted(path, trusted_root):
            reads.append(Path(path))
            return original(path, trusted_root)

        portfolio = system_portfolio(
            {"PGR": 1.0, "V": 1.0},
            {"PGR": 80.0, "V": 90.0},
        )
        with patch.object(
            integrated, "read_once_no_reparse", side_effect=counted,
        ), patch.object(
            manual_preflight, "ROOT", self.root,
        ), patch.object(
            manual_preflight, "_acquisition_complete_cutoff", return_value=CUTOFF,
        ):
            report = manual_preflight.run_manual_preflight(
                manual_run_id="manual-k3-one-read-test",
                system_portfolio=portfolio,
                system_portfolio_source="TEST_ONLY/system-portfolio.json",
                system_portfolio_sha256="b" * 64,
                provenance_policy=load_json(PROVENANCE_POLICY),
                account_reader=account_reader_for(
                    {"PGR": 1.0, "V": 1.0}, {"PGR": 80.0, "V": 90.0},
                ),
                market_reader=market_reader_for(["PGR", "V"]),
                maximum_broker_age_seconds=900,
                decision_as_of=CUTOFF,
                observed_at=CUTOFF,
                k3_shadow_combined_activation=self.path,
            )
        self.assertEqual(1, sum(path.resolve() == self.path.resolve() for path in reads))
        self.assertEqual(3, len(reads))
        provenance = report["integrated_authority_snapshot_provenance"]
        self.assertEqual("K3_COMBINED_SHADOW", provenance["authority_source"])
        self.assertEqual(COHORT_A, provenance["activation_cohort_id"])
        self.assertEqual("manual-k3-one-read-test", provenance["run_id"])
        self.assertFalse(report["order_authority"])
        self.assertIsNone(report["execution_quantity"])

    def test_18_shadow_output_reparse_alias_cannot_reach_production_namespace(self):
        policies = self.root / "workspace/policies"
        policies.mkdir(parents=True, exist_ok=True)
        alias = (
            self.root / integrated.SHADOW_OUTPUT_RELATIVE_ROOT / "alias-to-policies"
        )
        alias.parent.mkdir(parents=True, exist_ok=True)
        if not _create_directory_alias(alias, policies):
            self.skipTest("directory alias creation unavailable")
        protected = policies / integrated.COMBINED_ACTIVATION_RELATIVE_PATH.name
        try:
            with self.assertRaises(IntegratedAuthorityLoadError) as raised:
                write_shadow_combined_activation_manifest(
                    _manifest(self.root),
                    alias / protected.name,
                    trusted_root=self.root,
                )
            self.assertEqual("OUTPUT_NOT_SHADOW", raised.exception.reason)
            self.assertFalse(protected.exists())
        finally:
            _remove_directory_alias(alias)

    def test_19_k3_report_schema_requires_snapshot_provenance(self):
        portfolio = system_portfolio(
            {"PGR": 1.0, "V": 1.0},
            {"PGR": 80.0, "V": 90.0},
        )
        with patch.object(
            manual_preflight, "ROOT", self.root,
        ), patch.object(
            manual_preflight, "_acquisition_complete_cutoff", return_value=CUTOFF,
        ):
            report = manual_preflight.run_manual_preflight(
                manual_run_id="manual-k3-required-provenance",
                system_portfolio=portfolio,
                system_portfolio_source="TEST_ONLY/system-portfolio.json",
                system_portfolio_sha256="b" * 64,
                provenance_policy=load_json(PROVENANCE_POLICY),
                account_reader=account_reader_for(
                    {"PGR": 1.0, "V": 1.0}, {"PGR": 80.0, "V": 90.0},
                ),
                market_reader=market_reader_for(["PGR", "V"]),
                maximum_broker_age_seconds=900,
                decision_as_of=CUTOFF,
                observed_at=CUTOFF,
                k3_shadow_combined_activation=self.path,
            )
        schema = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
        self.assertEqual("2.1", report["schema_version"])
        self.assertEqual([], validate_instance(report, schema))
        stripped = copy.deepcopy(report)
        del stripped["integrated_authority_snapshot_provenance"]
        errors = validate_instance(stripped, schema)
        self.assertTrue(
            any("missing required property integrated_authority_snapshot_provenance" in item for item in errors),
            errors,
        )

    def test_20_run_manifest_git_reader_preserves_porcelain_leading_status_space(self):
        with patch.object(
            run_manifest_builder.subprocess,
            "check_output",
            return_value=" M first-file.py\n?? second-file.py\n",
        ):
            status = run_manifest_builder._git(["status", "--porcelain"], ROOT)
        self.assertEqual(" M first-file.py\n?? second-file.py", status)

    def test_21_staged_candidate_and_fixed_production_activation_are_byte_identical(self):
        manifest = _active_manifest(self.root)
        staged = (
            self.root / "workspace/outputs/k3-combined-identity-session-activation"
            / "test-production-candidate.json"
        )
        staged_hash = write_staged_production_combined_activation_candidate(
            manifest,
            staged,
            trusted_root=self.root,
        )
        production_hash = write_production_combined_activation_manifest(
            manifest,
            trusted_root=self.root,
            expected_current_sha256=None,
        )
        self.assertEqual(staged_hash, production_hash)
        snapshot = load_production_integrated_authority_snapshot(
            trusted_root=self.root,
            decision_as_of=CUTOFF,
            resolved_at=CUTOFF,
            run_id="test-production-snapshot",
        )
        self.assertEqual(COHORT_A, snapshot.activation_cohort_id)
        self.assertEqual(IDENTITY_HASH, snapshot.identity.registry_hash)
        self.assertEqual(SESSION_HASH, snapshot.session.calendar_hash)
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            write_production_combined_activation_manifest(
                manifest,
                trusted_root=self.root,
                expected_current_sha256=None,
            )
        self.assertEqual("PRODUCTION_MANIFEST_ALREADY_ACTIVE", raised.exception.reason)

    def test_22_production_crash_before_replace_preserves_absence(self):
        manifest = _active_manifest(self.root)
        target = self.root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH

        def crash(_staged: Path, _target: Path) -> None:
            raise RuntimeError("TEST_ONLY_CRASH")

        with self.assertRaisesRegex(RuntimeError, "TEST_ONLY_CRASH"):
            write_production_combined_activation_manifest(
                manifest,
                trusted_root=self.root,
                expected_current_sha256=None,
                before_replace=crash,
            )
        self.assertFalse(target.exists())
        self.assertEqual([], list(target.parent.glob(".*.staged")))

    def test_23_manual_preflight_uses_active_production_snapshot(self):
        manifest = _active_manifest(self.root)
        write_production_combined_activation_manifest(
            manifest,
            trusted_root=self.root,
            expected_current_sha256=None,
        )
        production_path = self.root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
        portfolio = system_portfolio(
            {"PGR": 1.0, "V": 1.0},
            {"PGR": 80.0, "V": 90.0},
        )
        with patch.object(
            manual_preflight, "ROOT", self.root,
        ), patch.object(
            manual_preflight, "_acquisition_complete_cutoff", return_value=CUTOFF,
        ):
            report = manual_preflight.run_manual_preflight(
                manual_run_id="manual-k3-production-test",
                system_portfolio=portfolio,
                system_portfolio_source="TEST_ONLY/system-portfolio.json",
                system_portfolio_sha256="b" * 64,
                provenance_policy=load_json(PROVENANCE_POLICY),
                account_reader=account_reader_for(
                    {"PGR": 1.0, "V": 1.0}, {"PGR": 80.0, "V": 90.0},
                ),
                market_reader=market_reader_for(["PGR", "V"]),
                maximum_broker_age_seconds=900,
                decision_as_of=CUTOFF,
                observed_at=CUTOFF,
                k3_production_combined_activation=production_path,
            )
        provenance = report["integrated_authority_snapshot_provenance"]
        self.assertEqual("K3_COMBINED_PRODUCTION", provenance["authority_source"])
        self.assertEqual(COHORT_A, provenance["activation_cohort_id"])
        self.assertEqual([], validate_instance(
            report,
            ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json",
        ))
        self.assertFalse(report["order_authority"])
        self.assertIsNone(report["execution_quantity"])

    def test_24_corrupt_production_manifest_fails_before_legacy_or_broker_reads(self):
        production_path = self.root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
        production_path.parent.mkdir(parents=True, exist_ok=True)
        production_path.write_bytes(b'{"activation_schema_version":')
        account_reader = unittest.mock.Mock(side_effect=AssertionError("broker read"))
        market_reader = unittest.mock.Mock(side_effect=AssertionError("market read"))
        with patch.object(
            manual_preflight, "ROOT", self.root,
        ), patch.object(
            manual_preflight, "resolve_instrument_identity",
        ) as legacy_identity, patch.object(
            manual_preflight, "derive_us_market_session_authority",
        ) as legacy_session:
            with self.assertRaises(IntegratedAuthorityLoadError):
                manual_preflight.run_manual_preflight(
                    manual_run_id="manual-k3-production-corrupt",
                    system_portfolio=system_portfolio(),
                    system_portfolio_source="TEST_ONLY/system-portfolio.json",
                    system_portfolio_sha256="b" * 64,
                    provenance_policy=load_json(PROVENANCE_POLICY),
                    account_reader=account_reader,
                    market_reader=market_reader,
                    maximum_broker_age_seconds=900,
                    decision_as_of=CUTOFF,
                    observed_at=CUTOFF,
                    k3_production_combined_activation=production_path,
                )
        account_reader.assert_not_called()
        market_reader.assert_not_called()
        legacy_identity.assert_not_called()
        legacy_session.assert_not_called()

    def test_25_main_source_binds_fixed_production_manifest_by_default(self):
        source = Path(manual_preflight.__file__).read_text(encoding="utf-8")
        self.assertIn("production_activation = (", source)
        self.assertIn("else repo / COMBINED_ACTIVATION_RELATIVE_PATH", source)
        self.assertIn("k3_production_combined_activation=production_activation", source)


class ConfirmationIntegratedConsumerTest(unittest.TestCase):
    def setUp(self):
        from test_materialize_instrument_identity_artifact import valid_packet
        from materialize_instrument_identity_artifact import CANDIDATE_SCOPE, build_materialization
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        _copy_artifacts(self.root)
        _, _, self.identity_artifact, raw, self.identity_hash, _ = build_materialization(valid_packet(CANDIDATE_SCOPE))
        self.identity_path = self.root / "workspace/instrument-identity-authority/artifacts" / self.identity_hash / "us-equity-instrument-identity-current-v1.registry.json"
        self.identity_path.parent.mkdir(parents=True)
        self.identity_path.write_bytes(raw)
        self.path = _manifest_path(self.root)
        self.manifest = build_combined_activation_manifest(
            trusted_root=self.root, identity_artifact_sha256=self.identity_hash,
            session_calendar_artifact_sha256=SESSION_HASH,
            cohort_id="TEST-CONFIRMATION-ONLY", previous_cohort_id=OLD_COHORT,
            activated_at=ACTIVATED_A, activation_status="SHADOW",
            activation_reason="Synthetic confirmation consumer fixture; no production activation.",
        )
        _write_direct(self.path, self.manifest)

    def tearDown(self):
        self.temporary.cleanup()

    def load(self, cutoff=CUTOFF, status="SHADOW"):
        return load_integrated_authority_snapshot(
            self.path, trusted_root=self.root, decision_as_of=cutoff,
            required_activation_status=status, resolved_at=CUTOFF,
            run_id="TEST-CONFIRMATION-CONSUMER",
        )

    def test_shadow_snapshot_resolves_both_confirmations_and_session(self):
        snapshot = self.load()
        for ticker, segment in (("MRVL", "XNGS"), ("SOXX", "XNMS")):
            with self.subTest(ticker=ticker):
                view = resolve_instrument_identity_from_snapshot(snapshot, ticker, decision_as_of=CUTOFF)
                self.assertEqual("VERIFIED", view.authority_status)
                self.assertEqual(segment, view.primary_listing_segment_mic)
                self.assertEqual(self.identity_hash, view.registry_hash)
                self.assertFalse(view.order_authority)
                session = derive_us_market_session_authority_from_snapshot(snapshot, CUTOFF, primary_listing_operating_mic=view.primary_listing_operating_mic, decision_as_of=CUTOFF)
                self.assertEqual("VERIFIED", session.authority_status)
                self.assertEqual(snapshot.activation_cohort_id, session.activation_cohort_id)

    def test_shadow_never_satisfies_active_status_gate(self):
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            self.load(status="ACTIVE")
        self.assertEqual("ARTIFACT_NOT_ACTIVATED", raised.exception.reason)

    def test_identity_bytes_or_manifest_binding_mismatch_fails(self):
        raw = self.identity_path.read_bytes()
        self.identity_path.write_bytes(raw + b" ")
        with self.assertRaises(IntegratedAuthorityLoadError):
            self.load()
        self.identity_path.write_bytes(raw)
        changed = copy.deepcopy(self.manifest)
        changed["instrument_identity"]["source_packet_hash"] = "f" * 64
        _write_direct(self.path, changed)
        with self.assertRaises(IntegratedAuthorityLoadError):
            self.load()

    def test_partial_scope_and_future_cutoff_fail(self):
        changed = copy.deepcopy(self.manifest)
        changed["instrument_identity"]["scope"].remove("MRVL")
        _write_direct(self.path, changed)
        with self.assertRaises(IntegratedAuthorityLoadError):
            self.load()
        _write_direct(self.path, self.manifest)
        with self.assertRaises(IntegratedAuthorityLoadError) as raised:
            self.load(cutoff="2026-08-01T00:00:00+00:00")
        self.assertEqual("TEMPORAL_VIOLATION", raised.exception.reason)

    def test_manual_authority_context_consumes_single_bound_snapshot(self):
        portfolio = system_portfolio({"MRVL": 1.0, "SOXX": 1.0}, {"MRVL": 80.0, "SOXX": 90.0})
        original = integrated.read_once_no_reparse
        reads = []
        def counted(path, trusted_root):
            reads.append(Path(path))
            return original(path, trusted_root)
        with patch.object(integrated, "read_once_no_reparse", side_effect=counted), patch.object(manual_preflight, "ROOT", self.root), patch.object(manual_preflight, "_acquisition_complete_cutoff", return_value=CUTOFF):
            report = manual_preflight.run_manual_preflight(
                manual_run_id="TEST-CONFIRMATION-MANUAL", system_portfolio=portfolio,
                system_portfolio_source="SYNTHETIC_ONLY", system_portfolio_sha256="b" * 64,
                provenance_policy=load_json(PROVENANCE_POLICY),
                account_reader=account_reader_for({"MRVL": 1.0, "SOXX": 1.0}, {"MRVL": 80.0, "SOXX": 90.0}),
                market_reader=market_reader_for(["MRVL", "SOXX"]),
                maximum_broker_age_seconds=900, decision_as_of=CUTOFF,
                observed_at=CUTOFF, k3_shadow_combined_activation=self.path,
            )
        self.assertEqual(1, sum(path.resolve() == self.path.resolve() for path in reads))
        self.assertEqual(3, len(reads))
        provenance = report["integrated_authority_snapshot_provenance"]
        self.assertEqual("K3_COMBINED_SHADOW", provenance["authority_source"])
        self.assertEqual("TEST-CONFIRMATION-ONLY", provenance["activation_cohort_id"])
        self.assertFalse(report["order_authority"])
        self.assertIsNone(report["execution_quantity"])


class ManualDirectionCombinedReplayTest(unittest.TestCase):
    """Synthetic captures through real combined loaders and direction consumers."""

    observed = "2026-09-02T22:00:10+00:00"
    retrieved = "2026-09-02T22:00:02+00:00"
    initial_cutoff = "2026-09-02T22:00:03+00:00"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        _copy_artifacts(self.root)
        self.path = self.root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
        _write_direct(self.path, _active_manifest(self.root))
        self.root_patch = patch.object(manual_preflight, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        # Combined replay must never silently call the legacy authorities.
        for name in ("resolve_instrument_identity", "derive_us_market_session_authority",
                     "invoke_account_bridge_batch", "invoke_bridge_batch"):
            guard = patch.object(manual_preflight, name, side_effect=AssertionError(name))
            guard.start()
            self.addCleanup(guard.stop)
        self.state = system_portfolio({"PGR": 1.0}, {"PGR": 80.0}, cash=0.0)
        self.accounts = ["account_deposit_read", "account_holdings_read", "account_open_items"]
        self.requests = [{"operation": op} for op in self.accounts] + [
            {"operation": "oauth_health"},
            {"operation": "market_quote", "ticker": "PGR", "fx_applied": False},
            {"operation": "daily_chart", "ticker": "PGR", "completed_session": "2026-09-01",
             "price_basis": "RAW", "fx_applied": False},
        ]
        self.results = account_reader_for(
            self.state["holdings"], self.state["average_cost_usd"],
            orderable_cash=0.0, retrieved_at=self.retrieved,
        )(self.requests[:3]) + market_reader_for(
            ["PGR"], retrieved_at_by_operation={op: self.retrieved for op in manual_preflight.MARKET_READ_OPERATIONS},
        )(self.requests[3:])
        self.results[2].update(bridge_status="KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR",
                               data=[], pagination={"complete": False})
        self.results[-1]["data"] = [{"dt": "20260901", "cur_prc": 99.0}]

    def build(self, *, direction_only=True):
        doc = {"run_id": "manual-combined-direction-fixture", "started_at": CUTOFF,
               "observed_at": self.initial_cutoff, "requests": self.requests,
               "results": self.results, "request_sha256": manual_preflight.canonical_hash(self.requests)}
        raw = json.dumps(doc, sort_keys=True).encode()
        self.captures = [(raw, hashlib.sha256(raw).hexdigest())]
        def reader(requests):
            return [copy.deepcopy(self.results[self.requests.index(q)]) for q in requests]
        return manual_preflight.run_manual_preflight(
            manual_run_id=doc["run_id"], system_portfolio=self.state,
            system_portfolio_source="TEST_ONLY/system.json", system_portfolio_sha256="b" * 64,
            provenance_policy=load_json(PROVENANCE_POLICY), account_reader=reader, market_reader=reader,
            maximum_broker_age_seconds=900, observed_at=self.observed, decision_as_of=self.initial_cutoff,
            k3_production_combined_activation=self.path, account_operations=self.accounts,
            market_operations=list(manual_preflight.MARKET_READ_OPERATIONS),
            parent_capture_artifacts=self.captures, direction_only=direction_only,
        )

    def eligible(self, report, observed=None):
        return manual_preflight.validate_manual_direction_evidence(
            report, self.captures, analysis_observed_at=observed or self.observed)

    def test_partial_combined_direction_replays_and_preserves_two_cutoffs(self):
        report = self.build()
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "GRADE_B")
        self.assertTrue(self.eligible(report))
        self.assertEqual(report["decision_as_of"], self.retrieved)
        self.assertEqual(report["integrated_authority_snapshot_provenance"]["snapshot_decision_as_of"], self.initial_cutoff)
        self.assertEqual(report["verified_orderable_cash_usd"], 0.0)
        self.assertEqual(report["broker_observed_state"]["operation_statuses"]["account_open_items"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(report["broker_observed_state"]["operation_statuses"]["account_fills_read"], "NOT_REQUESTED")
        self.assertFalse(report["order_authority"])
        self.assertIsNone(report["execution_quantity"])
        self.assertEqual(report["quantity_authority"], "none")
        self.assertEqual([], validate_instance(report, ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"))

    def test_downstream_handoff_dashboard_and_sidecar_use_same_validator(self):
        from portfolio_decision_dashboard import _canonical_evidence_gate, MANUAL_EVIDENCE_SCHEMA
        from continuous_improvement_sidecar import manual_grade_b_eligible
        report = self.build()
        self.assertTrue(manual_preflight.validate_manual_acquisition_handoff(
            report, self.captures, analysis_observed_at=self.observed, maximum_age_seconds=900))
        plan = {"as_of": report["decision_as_of"],
                "evidence_binding": {"expected_run_id": report["manual_run_id"],
                                     "expected_decision_as_of": report["decision_as_of"]}}
        gate = _canonical_evidence_gate(report, plan, "INITIAL_COMPILE", MANUAL_EVIDENCE_SCHEMA.read_bytes(),
                                       parent_capture_artifacts=self.captures, analysis_observed_at=self.observed)
        self.assertEqual(gate[1], [])
        run = dict(report, execution_origin="MANUAL", decision_mode="MANUAL_READ_ONLY",
                   provenance_evidence={"manual_run_id": report["manual_run_id"]})
        self.assertTrue(manual_grade_b_eligible(run, direction_evidence=report,
                                              parent_capture_artifacts=self.captures, analysis_observed_at=self.observed))

    def test_provenance_hash_cohort_version_and_time_tampering_rejected(self):
        report = self.build()
        changes = {
            "combined_activation_manifest_sha256": "f" * 64,
            "instrument_identity_artifact_sha256": "f" * 64,
            "session_calendar_artifact_sha256": "f" * 64,
            "activation_cohort_id": "OTHER", "identity_registry_version": "OTHER",
            "session_calendar_version": "OTHER", "run_id": "manual-other-run",
            "authority_resolved_at": self.retrieved, "report_decision_as_of": self.observed,
            "snapshot_decision_as_of": "2026-09-02T22:00:11+00:00",
        }
        for key, value in changes.items():
            with self.subTest(field=key):
                changed = copy.deepcopy(report)
                changed["integrated_authority_snapshot_provenance"][key] = value
                self.assertFalse(self.eligible(changed))

    def test_changed_active_bundle_and_shadow_never_fall_back(self):
        report = self.build()
        for field, value in [("activation_cohort_id", COHORT_B), ("activation_status", "SHADOW")]:
            with self.subTest(field=field):
                manifest = _active_manifest(self.root)
                manifest[field] = value
                _write_direct(self.path, manifest)
                self.assertFalse(self.eligible(report))

    def test_missing_or_corrupt_manifest_blocks(self):
        report = self.build()
        self.path.write_text("{", encoding="utf-8")
        self.assertFalse(self.eligible(report))
        self.path.unlink()
        self.assertFalse(self.eligible(report))

    def test_stale_future_and_capture_tampering_block(self):
        report = self.build()
        for at in ("2026-09-02T22:15:03+00:00", "2026-09-02T22:00:01+00:00"):
            self.assertFalse(self.eligible(report, at))
        self.captures = [(self.captures[0][0] + b" ", self.captures[0][1])]
        self.assertFalse(self.eligible(report))

    def test_core_cash_missing_not_promoted(self):
        self.results[0]["data"] = []
        report = self.build()
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertFalse(self.eligible(report))

    def test_general_manual_not_automatically_opted_in(self):
        report = self.build(direction_only=False)
        self.assertNotEqual(report["evidence_grade"], "GRADE_B")
        self.assertFalse(self.eligible(report))


if __name__ == "__main__":
    unittest.main()
