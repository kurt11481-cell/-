#!/usr/bin/env python3
"""Instrument Identity Authority security and contract tests."""

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
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

import authority_artifact_io  # noqa: E402
import instrument_identity_authority as identity_authority  # noqa: E402
from instrument_identity_artifact import (  # noqa: E402
    ARTIFACT_FILENAME,
    EXPECTED_SCOPE,
    LoadedInstrumentIdentityRegistry,
)
from instrument_identity_authority import (  # noqa: E402
    _resolve_instrument_identity_from_root,
    resolve_instrument_identity,
)


DECISION_AS_OF = "2026-08-24T14:00:00+00:00"
COHORT = "synthetic-shared-authority-cohort"


def canonical_bytes(value: object) -> bytes:
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


def build_artifact() -> dict:
    pairs = [
        ("XNYS", "XNYS"),
        ("XNGS", "XNAS"),
        ("BATS", "XCBO"),
        ("ARCX", "XNYS"),
        ("XNMS", "XNAS"),
        ("XNYS", "XNYS"),
        ("XNGS", "XNAS"),
        ("BATS", "XCBO"),
    ]
    records = []
    for index, ticker in enumerate(EXPECTED_SCOPE):
        segment, operating = pairs[index]
        records.append({
            "record_status": "VERIFIED",
            "ticker": ticker,
            "security_name": f"Synthetic Security {index + 1}",
            "instrument_type": "EQUITY",
            "security_class": "COMMON_STOCK",
            "primary_listing_venue_name": f"Synthetic Venue {index + 1}",
            "primary_listing_segment_mic": segment,
            "primary_listing_operating_mic": operating,
            "effective_from": None,
            "effective_from_basis": "CURRENT_AS_OF_ONLY",
            "effective_to": None,
            "source_ref_ids": [f"synthetic-ref-{index + 1}"],
        })
    return {
        "artifact_schema_version": "1.0",
        "authority_id": "US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1",
        "registry_version": "synthetic-registry-v1",
        "ticker_namespace": "US_EXCHANGE_LISTED",
        "scope": list(EXPECTED_SCOPE),
        "generated_at": "2026-02-02T00:00:00+00:00",
        "authority_as_of": "2026-02-01T00:00:00+00:00",
        "source_packet_id": "synthetic-source-packet-v1",
        "source_packet_hash": "a" * 64,
        "order_authority": False,
        "records": records,
    }


def activation_for(artifact: dict, registry_hash: str, *, status: str = "ACTIVE") -> dict:
    return {
        "activation_schema_version": "1.0",
        "activation_status": status,
        "activation_reason_code": (
            "INITIAL_BOOTSTRAP" if status == "ACTIVE" else "MANUAL_DEACTIVATION"
        ),
        "activation_reason": "Synthetic fixture only",
        "authority_id": artifact["authority_id"],
        "active_registry_hash": registry_hash,
        "active_registry_version": artifact["registry_version"],
        "ticker_namespace": artifact["ticker_namespace"],
        "scope": list(artifact["scope"]),
        "source_packet_id": artifact["source_packet_id"],
        "source_packet_hash": artifact["source_packet_hash"],
        "authority_as_of": artifact["authority_as_of"],
        "activated_at": "2026-02-03T00:00:00+00:00",
        "authority_modes_allowed": ["CURRENT"],
        "activation_cohort_id": COHORT,
    }


def write_fixture(
    trusted_root: Path,
    *,
    artifact: dict | None = None,
    status: str = "ACTIVE",
    activation_mutator=None,
) -> tuple[Path, Path, dict, dict]:
    value = artifact or build_artifact()
    artifact_raw = canonical_bytes(value)
    registry_hash = hashlib.sha256(artifact_raw).hexdigest()
    activation = activation_for(value, registry_hash, status=status)
    if activation_mutator is not None:
        activation_mutator(activation)
    activation_path = trusted_root / "workspace/policies/instrument_identity_activation.json"
    artifact_path = (
        trusted_root
        / "workspace/instrument-identity-authority/artifacts"
        / registry_hash
        / ARTIFACT_FILENAME
    )
    activation_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    activation_path.write_bytes(canonical_bytes(activation))
    artifact_path.write_bytes(artifact_raw)
    return activation_path, artifact_path, activation, value


def resolve(root: Path, ticker: str = "BE", **kwargs):
    return _resolve_instrument_identity_from_root(
        ticker,
        trusted_root=root,
        decision_as_of=kwargs.pop("decision_as_of", DECISION_AS_OF),
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
    os.rmdir(link) if os.name == "nt" else link.unlink()


class InstrumentIdentityAuthorityTest(unittest.TestCase):
    def test_01_activation_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual("ARTIFACT_NOT_ACTIVATED", resolve(Path(directory)).authority_reason)

    def test_02_activation_inactive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, status="INACTIVE")
            self.assertEqual("ARTIFACT_NOT_ACTIVATED", resolve(root).authority_reason)

    def test_03_known_symbol_is_verified_with_explicit_mics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            view = resolve(root)
            self.assertEqual("VERIFIED", view.authority_status)
            self.assertEqual("XNYS", view.primary_listing_segment_mic)
            self.assertEqual("XNYS", view.primary_listing_operating_mic)
            self.assertFalse(view.order_authority)
            self.assertEqual(COHORT, view.activation_cohort_id)

    def test_04_unknown_and_alias_tickers_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            self.assertEqual("UNKNOWN_SYMBOL", resolve(root, "ZZZ").authority_reason)
            for ticker in ("be", " BE", "BE ", ""):
                self.assertEqual("INVALID_INPUT", resolve(root, ticker).authority_reason)

    def test_05_one_byte_mutation_and_noncanonical_bytes_fail(self):
        for mode in ("mutation", "pretty"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _, artifact_path, _, artifact = write_fixture(root)
                if mode == "mutation":
                    raw = artifact_path.read_bytes()
                    artifact_path.write_bytes(raw[:-2] + (b" " if raw[-2:-1] != b" " else b"x") + raw[-1:])
                else:
                    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
                self.assertEqual("INTEGRITY_FAILURE", resolve(root).authority_reason)

    def test_06_activation_hash_authority_version_and_scope_binding(self):
        cases = [
            lambda a: a.__setitem__("active_registry_hash", "b" * 64),
            lambda a: a.__setitem__("authority_id", "WRONG"),
            lambda a: a.__setitem__("active_registry_version", "wrong-version"),
            lambda a: a.__setitem__("scope", list(reversed(a["scope"]))),
            lambda a: a.__setitem__("ticker_namespace", "UNTRUSTED"),
            lambda a: a.__setitem__("source_packet_id", "wrong-packet"),
            lambda a: a.__setitem__("source_packet_hash", "b" * 64),
            lambda a: a.__setitem__("authority_as_of", "2026-01-31T00:00:00+00:00"),
        ]
        for mutator in cases:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_fixture(root, activation_mutator=mutator)
                self.assertEqual("INTEGRITY_FAILURE", resolve(root).authority_reason)

    def test_07_future_activation_and_artifact_cutoffs_are_temporal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, activation_mutator=lambda a: a.__setitem__(
                "activated_at", "2027-02-03T00:00:00+00:00"
            ))
            self.assertEqual("TEMPORAL_VIOLATION", resolve(root).authority_reason)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = build_artifact()
            artifact["authority_as_of"] = "2027-02-01T00:00:00+00:00"
            artifact["generated_at"] = "2027-02-02T00:00:00+00:00"
            write_fixture(root, artifact=artifact, activation_mutator=lambda a: a.__setitem__(
                "activated_at", "2027-02-03T00:00:00+00:00"
            ))
            self.assertEqual("TEMPORAL_VIOLATION", resolve(root).authority_reason)

    def test_08_duplicate_unsorted_namespace_order_and_mic_fail_integrity(self):
        artifacts = []
        duplicate = build_artifact()
        duplicate["records"].append(dict(duplicate["records"][0]))
        artifacts.append(duplicate)
        unsorted = build_artifact()
        unsorted["records"][0], unsorted["records"][1] = unsorted["records"][1], unsorted["records"][0]
        artifacts.append(unsorted)
        namespace = build_artifact()
        namespace["ticker_namespace"] = "UNTRUSTED"
        artifacts.append(namespace)
        order_authority = build_artifact()
        order_authority["order_authority"] = True
        artifacts.append(order_authority)
        malformed_mic = build_artifact()
        malformed_mic["records"][0]["primary_listing_segment_mic"] = "NY"
        artifacts.append(malformed_mic)
        mismatch = build_artifact()
        mismatch["records"][0]["primary_listing_segment_mic"] = "BATS"
        artifacts.append(mismatch)
        for artifact in artifacts:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_fixture(root, artifact=artifact)
                self.assertEqual("INTEGRITY_FAILURE", resolve(root).authority_reason)

    def test_09_missing_fields_and_unsupported_type_fail_integrity(self):
        for field in ("primary_listing_operating_mic", "primary_listing_segment_mic"):
            artifact = build_artifact()
            del artifact["records"][0][field]
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_fixture(root, artifact=artifact)
                self.assertEqual("INTEGRITY_FAILURE", resolve(root).authority_reason)
        artifact = build_artifact()
        artifact["records"][0]["instrument_type"] = "SPOT_ETF"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, artifact=artifact)
            self.assertEqual("INTEGRITY_FAILURE", resolve(root).authority_reason)

    def test_10_ambiguous_pre_effective_expired_and_primary_mic_defenses(self):
        artifact = build_artifact()
        raw = canonical_bytes(artifact)
        loaded = LoadedInstrumentIdentityRegistry(
            activation=activation_for(artifact, hashlib.sha256(raw).hexdigest()),
            artifact=artifact,
            registry_hash=hashlib.sha256(raw).hexdigest(),
        )
        ambiguous = dict(artifact)
        ambiguous["records"] = list(artifact["records"]) + [dict(artifact["records"][0])]
        ambiguous_loaded = LoadedInstrumentIdentityRegistry(loaded.activation, ambiguous, loaded.registry_hash)
        view = identity_authority._resolve(
            "BE", decision_as_of=DECISION_AS_OF, authority_mode="CURRENT",
            loader=lambda: ambiguous_loaded,
        )
        self.assertEqual("AMBIGUOUS_SECURITY", view.authority_reason)

        pre_effective = json.loads(json.dumps(artifact))
        pre_effective["records"][0]["effective_from"] = "2026-09-01"
        pre_effective["records"][0]["effective_from_basis"] = "VERIFIED_DATE"
        pre_loaded = LoadedInstrumentIdentityRegistry(loaded.activation, pre_effective, loaded.registry_hash)
        self.assertEqual("OUT_OF_EFFECTIVE_RANGE", identity_authority._resolve(
            "BE", decision_as_of=DECISION_AS_OF, authority_mode="CURRENT", loader=lambda: pre_loaded,
        ).authority_reason)

        expired = json.loads(json.dumps(artifact))
        expired["records"][0]["effective_to"] = "2026-12-31"
        expired_loaded = LoadedInstrumentIdentityRegistry(loaded.activation, expired, loaded.registry_hash)
        self.assertEqual("OUT_OF_EFFECTIVE_RANGE", identity_authority._resolve(
            "BE", decision_as_of="2027-01-02T00:00:00+00:00", authority_mode="CURRENT",
            loader=lambda: expired_loaded,
        ).authority_reason)

        missing_primary = json.loads(json.dumps(artifact))
        missing_primary["records"][0]["primary_listing_operating_mic"] = None
        primary_loaded = LoadedInstrumentIdentityRegistry(loaded.activation, missing_primary, loaded.registry_hash)
        self.assertEqual("PRIMARY_MIC_NOT_VERIFIED", identity_authority._resolve(
            "BE", decision_as_of=DECISION_AS_OF, authority_mode="CURRENT", loader=lambda: primary_loaded,
        ).authority_reason)

    def test_11_current_as_of_only_never_backdates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            self.assertEqual("TEMPORAL_VIOLATION", resolve(
                root, decision_as_of="2026-02-02T12:00:00+00:00"
            ).authority_reason)

    def test_12_public_and_cli_authority_injection_surfaces_are_absent(self):
        forbidden = {
            "primary_mic", "exchange", "instrument_primary_mics", "artifact_path",
            "activation_path", "registry_hash", "kiwoom_market_category",
        }
        self.assertFalse(forbidden & set(inspect.signature(resolve_instrument_identity).parameters))
        source = inspect.getsource(resolve_instrument_identity)
        self.assertNotIn("instrument_registry", source)
        manual_source = (SCRIPTS / "run_manual_portfolio_analysis.py").read_text(encoding="utf-8")
        self.assertNotIn("--primary-mic", manual_source)
        self.assertNotIn("--exchange", manual_source)
        self.assertNotIn("--registry-path", manual_source)
        self.assertNotIn("instrument_primary_mics", manual_source)
        authority_source = (SCRIPTS / "instrument_identity_authority.py").read_text(encoding="utf-8")
        self.assertNotIn("kiwoom", authority_source.lower())
        self.assertNotIn("instrument_registry.json", authority_source)

    def test_13_activation_and_artifact_reparse_escape_fail_integrity(self):
        for target_kind in ("activation", "artifact"):
            with self.subTest(target_kind=target_kind), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                root = base / "root"
                activation_path, artifact_path, _, _ = write_fixture(root)
                target = activation_path.parent if target_kind == "activation" else artifact_path.parent
                outside = base / f"outside-{target_kind}"
                shutil.move(str(target), str(outside))
                create_directory_reparse(target, outside)
                try:
                    self.assertEqual("INTEGRITY_FAILURE", resolve(root).authority_reason)
                finally:
                    remove_directory_reparse(target)

    def test_14_open_handle_prevents_or_survives_substitution(self):
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
                    view = resolve(root)
                self.assertTrue(attack_rejected)
            else:
                view = resolve(root)
            self.assertEqual("VERIFIED", view.authority_status)

    def test_15_materialized_candidate_does_not_activate_authority(self):
        self.assertFalse((ROOT / "workspace/policies/instrument_identity_activation.json").exists())
        self.assertTrue((ROOT / "workspace/instrument-identity-authority/artifacts").is_dir())
        view = resolve_instrument_identity("BE", decision_as_of=DECISION_AS_OF)
        self.assertEqual("NOT_VERIFIED", view.authority_status)
        self.assertEqual("ARTIFACT_NOT_ACTIVATED", view.authority_reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
