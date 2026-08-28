#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from authority_artifact_io import canonical_json_bytes
import materialize_instrument_identity_artifact as materializer
from materialize_instrument_identity_artifact import (
    ARTIFACT_DIRECTORY,
    ARTIFACT_FILENAME,
    EVIDENCE_PACKET_FILENAME,
    EXPECTED_SCOPE,
    MaterializationError,
    REQUIRED_CLAIMS,
    build_materialization,
    materialize_evidence_and_candidate,
    validate_evidence_packet,
)


AUTHORITY_DATE = "2026-08-22"
AUTHORITY_TIMESTAMP = "2026-08-22T00:00:00+09:00"
GENERATED_AT = "2026-08-22T12:00:00+09:00"
RECORDS = {
    "BE": ("Bloom Energy Corporation Common Stock", "EQUITY", "COMMON_STOCK", "New York Stock Exchange", "XNYS", "XNYS", None, "CURRENT_AS_OF_ONLY"),
    "DRAM": ("Roundhill Memory ETF", "ETF", "ACTIVELY_MANAGED_ETF", "Cboe BZX Exchange", "BATS", "XCBO", "2026-04-02", "VERIFIED_DATE"),
    "FSLY": ("Fastly, Inc. Class A Common Stock", "EQUITY", "CLASS_A_COMMON_STOCK", "Nasdaq Global Select Market", "XNGS", "XNAS", "2025-12-09", "VERIFIED_DATE"),
    "MVLL": ("GraniteShares 2x Long MRVL Daily ETF", "ETF", "LEVERAGED_ETF", "Nasdaq Global Market", "XNMS", "XNAS", "2025-03-07", "VERIFIED_DATE"),
    "NBIS": ("Nebius Group N.V. Class A Ordinary Shares", "EQUITY", "CLASS_A_ORDINARY_SHARES", "Nasdaq Global Select Market", "XNGS", "XNAS", "2024-10-21", "VERIFIED_DATE"),
    "NOW": ("ServiceNow, Inc. Common Stock", "EQUITY", "COMMON_STOCK", "New York Stock Exchange", "XNYS", "XNYS", None, "CURRENT_AS_OF_ONLY"),
    "SOXL": ("Direxion Daily Semiconductor Bull 3X ETF", "ETF", "LEVERAGED_ETF", "NYSE Arca", "ARCX", "XNYS", None, "CURRENT_AS_OF_ONLY"),
    "TOST": ("Toast, Inc. Class A Common Stock", "EQUITY", "CLASS_A_COMMON_STOCK", "New York Stock Exchange", "XNYS", "XNYS", "2021-09-22", "VERIFIED_DATE"),
}
EXCHANGE_FAMILY = {
    "BE": "NYSE", "DRAM": "CBOE", "FSLY": "NASDAQ", "MVLL": "NASDAQ",
    "NBIS": "NASDAQ", "NOW": "NYSE", "SOXL": "NYSE", "TOST": "NYSE",
}


def source(
    source_id: str,
    *,
    ticker: str | None,
    family: str,
    scopes: list[str],
) -> dict:
    return {
        "source_id": source_id,
        "source_id_semantics": "INTERNAL_EVIDENCE_PACKET_REFERENCE",
        "ticker": ticker,
        "source_family": family,
        "publisher": f"Synthetic {family} fixture",
        "source_reference": f"https://example.invalid/{source_id}",
        "claim_scope": scopes,
        "publication_or_effective_date": None,
        "publication_or_effective_date_note": None,
        "retrieved_date": AUTHORITY_DATE,
        "retrieval_time_precision": "DATE_ONLY_KST",
        "content_sha256": None,
        "content_hash_status": "NOT_CAPTURED",
        "source_observation": None,
        "evidence_note": "Synthetic materialization-only fixture.",
    }


def valid_packet() -> dict:
    claims = [
        source(
            "ISO_REGISTER",
            ticker=None,
            family="ISO_10383",
            scopes=["MIC_IDENTITY", "OPERATING_MIC_RELATIONSHIP", "MIC_STATUS"],
        ),
        source(
            "ISO_CSV",
            ticker=None,
            family="ISO_10383",
            scopes=["SEGMENT_MIC", "OPERATING_MIC", "OPRT_SGMT_RELATIONSHIP", "STATUS"],
        ),
    ]
    records = []
    for ticker in EXPECTED_SCOPE:
        exchange_id = f"{ticker}_EXCHANGE"
        class_id = f"{ticker}_CLASS"
        claims.extend(
            [
                source(
                    exchange_id,
                    ticker=ticker,
                    family=EXCHANGE_FAMILY[ticker],
                    scopes=[
                        "SECURITY_IDENTITY",
                        "CURRENT_PRIMARY_LISTING_VENUE",
                        "CURRENT_LISTING",
                        "FIRST_TRADING_DATE",
                        "TICKER",
                    ],
                ),
                source(
                    class_id,
                    ticker=ticker,
                    family="SPONSOR" if ticker in {"DRAM", "MVLL", "SOXL"} else "SEC",
                    scopes=["SECURITY_IDENTITY", "INSTRUMENT_TYPE", "SECURITY_CLASS", "FUND_IDENTITY"],
                ),
            ]
        )
        name, instrument_type, security_class, venue, segment, operating, start, basis = RECORDS[ticker]
        link_map = {
            "SECURITY_IDENTITY": [exchange_id, class_id],
            "INSTRUMENT_TYPE_OR_CLASS": [class_id],
            "PRIMARY_LISTING_VENUE": [exchange_id],
            "PRIMARY_LISTING_SEGMENT_MIC": ["ISO_CSV", "ISO_REGISTER"],
            "PRIMARY_LISTING_OPERATING_MIC": ["ISO_CSV", "ISO_REGISTER"],
            "EFFECTIVE_DATE_BASIS": [exchange_id],
        }
        records.append(
            {
                "ticker": ticker,
                "research_verdict": "VERIFIED",
                "normalized_record": {
                    "record_status": "VERIFIED",
                    "ticker": ticker,
                    "security_name": name,
                    "instrument_type": instrument_type,
                    "security_class": security_class,
                    "primary_listing_venue_name": venue,
                    "primary_listing_segment_mic": segment,
                    "primary_listing_operating_mic": operating,
                    "effective_from": start,
                    "effective_from_basis": basis,
                    "effective_to": None,
                },
                "claim_links": [
                    {"claim_type": claim_type, "source_ids": link_map[claim_type]}
                    for claim_type in REQUIRED_CLAIMS
                ],
                "temporal_notes": ["Current authority evidence fixture."],
                "unresolved_non_blocking_historical_gaps": [],
            }
        )
    return {
        "packet_schema_version": "1.0",
        "source_packet_id": "SYNTHETIC_II_B2_PACKET",
        "registry_version": "synthetic-2026-08-22",
        "ticker_namespace": "US_EXCHANGE_LISTED",
        "scope": list(EXPECTED_SCOPE),
        "generated_at": GENERATED_AT,
        "authority_as_of": AUTHORITY_DATE,
        "artifact_authority_as_of": AUTHORITY_TIMESTAMP,
        "authority_as_of_time_basis": "DATE_START_KST_CONSERVATIVE",
        "research_verdict": "VERIFIED",
        "claims": claims,
        "records": records,
    }


def record(packet: dict, ticker: str) -> dict:
    return next(item for item in packet["records"] if item["ticker"] == ticker)


def link(packet: dict, ticker: str, claim_type: str) -> dict:
    return next(item for item in record(packet, ticker)["claim_links"] if item["claim_type"] == claim_type)


class InstrumentIdentityMaterializationTest(unittest.TestCase):
    def assert_invalid(self, packet: dict, code: str = "INTEGRITY_FAILURE") -> None:
        with self.assertRaises(MaterializationError) as caught:
            validate_evidence_packet(packet)
        self.assertEqual(code, caught.exception.code)

    def make_junction(self, link_path: Path, target_path: Path) -> None:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr.decode(errors="replace"))

    def outside_snapshot(self, outside: Path) -> dict[str, tuple[str, bytes]]:
        return {
            str(path.relative_to(outside)): (
                "directory" if path.is_dir() else "file",
                b"" if path.is_dir() else path.read_bytes(),
            )
            for path in outside.rglob("*")
        }

    def test_01_exact_eight_symbol_packet_is_accepted(self):
        result = validate_evidence_packet(valid_packet())
        self.assertEqual(8, result["record_count"])
        self.assertEqual(48, result["required_claim_count"])

    def test_02_candidate_has_exact_eight_records(self):
        _, _, artifact, _, _, _ = build_materialization(valid_packet())
        self.assertEqual(list(EXPECTED_SCOPE), artifact["scope"])
        self.assertEqual(list(EXPECTED_SCOPE), [item["ticker"] for item in artifact["records"]])

    def test_03_missing_symbol_fails(self):
        packet = valid_packet()
        packet["records"].pop()
        self.assert_invalid(packet)

    def test_04_extra_symbol_fails(self):
        packet = valid_packet()
        extra = deepcopy(packet["records"][-1])
        extra["ticker"] = "MRVL"
        extra["normalized_record"]["ticker"] = "MRVL"
        packet["records"].append(extra)
        self.assert_invalid(packet)

    def test_05_duplicate_symbol_fails(self):
        packet = valid_packet()
        packet["records"][-1] = deepcopy(packet["records"][0])
        self.assert_invalid(packet)

    def test_06_dram_spot_etf_contamination_fails(self):
        packet = valid_packet()
        record(packet, "DRAM")["normalized_record"]["security_class"] = "SPOT_ETF"
        self.assert_invalid(packet)

    def test_07_soxl_operating_arcx_fails(self):
        packet = valid_packet()
        record(packet, "SOXL")["normalized_record"]["primary_listing_operating_mic"] = "ARCX"
        self.assert_invalid(packet)

    def test_08_dram_operating_bats_fails(self):
        packet = valid_packet()
        record(packet, "DRAM")["normalized_record"]["primary_listing_operating_mic"] = "BATS"
        self.assert_invalid(packet)

    def test_09_fsly_operating_xngs_fails(self):
        packet = valid_packet()
        record(packet, "FSLY")["normalized_record"]["primary_listing_operating_mic"] = "XNGS"
        self.assert_invalid(packet)

    def test_10_mvll_operating_xnms_fails(self):
        packet = valid_packet()
        record(packet, "MVLL")["normalized_record"]["primary_listing_operating_mic"] = "XNMS"
        self.assert_invalid(packet)

    def test_11_wrong_segment_operating_pair_fails(self):
        packet = valid_packet()
        record(packet, "BE")["normalized_record"]["primary_listing_segment_mic"] = "ARCX"
        self.assert_invalid(packet)

    def test_12_current_as_of_only_backdate_fails(self):
        packet = valid_packet()
        record(packet, "SOXL")["normalized_record"]["effective_from"] = "2010-03-11"
        self.assert_invalid(packet)

    def test_13_verified_effective_dates_are_preserved(self):
        _, _, artifact, _, _, _ = build_materialization(valid_packet())
        starts = {item["ticker"]: item["effective_from"] for item in artifact["records"]}
        self.assertEqual("2026-04-02", starts["DRAM"])
        self.assertEqual("2025-12-09", starts["FSLY"])
        self.assertEqual("2025-03-07", starts["MVLL"])
        self.assertEqual("2024-10-21", starts["NBIS"])
        self.assertEqual("2021-09-22", starts["TOST"])

    def test_14_missing_identity_provenance_fails(self):
        packet = valid_packet()
        link(packet, "BE", "SECURITY_IDENTITY")["source_ids"] = []
        self.assert_invalid(packet)

    def test_15_missing_operating_mic_provenance_fails(self):
        packet = valid_packet()
        for item in packet["claims"]:
            if item["source_id"] == "ISO_CSV":
                item["claim_scope"] = ["SEGMENT_MIC", "STATUS"]
            if item["source_id"] == "ISO_REGISTER":
                item["claim_scope"] = ["MIC_IDENTITY", "MIC_STATUS"]
        self.assert_invalid(packet)

    def test_16_artifact_canonical_hash_is_reproducible(self):
        built = build_materialization(valid_packet())
        self.assertEqual(hashlib.sha256(built[3]).hexdigest(), built[4])
        self.assertEqual(built[3], canonical_json_bytes(built[2]))

    def test_17_same_input_same_hashes(self):
        first = build_materialization(valid_packet())
        second = build_materialization(valid_packet())
        self.assertEqual((first[1], first[4]), (second[1], second[4]))

    def test_18_one_field_change_changes_both_hashes(self):
        first = build_materialization(valid_packet())
        changed = valid_packet()
        changed["claims"][2]["evidence_note"] = "Changed reviewed note."
        second = build_materialization(changed)
        self.assertNotEqual(first[1], second[1])
        self.assertNotEqual(first[4], second[4])

    def test_19_create_only_success(self):
        with tempfile.TemporaryDirectory() as directory:
            result = materialize_evidence_and_candidate(valid_packet(), trusted_root=Path(directory))
            self.assertEqual("CREATED", result.evidence_packet_write_status)
            self.assertEqual("CREATED", result.candidate_registry_write_status)
            self.assertTrue(result.evidence_packet_path.is_file())
            self.assertTrue(result.candidate_registry_path.is_file())

    def test_20_duplicate_same_bytes_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = materialize_evidence_and_candidate(valid_packet(), trusted_root=root)
            packet_before = first.evidence_packet_path.read_bytes()
            candidate_before = first.candidate_registry_path.read_bytes()
            packet_mtime_before = first.evidence_packet_path.stat().st_mtime_ns
            candidate_mtime_before = first.candidate_registry_path.stat().st_mtime_ns
            second = materialize_evidence_and_candidate(valid_packet(), trusted_root=root)
            self.assertEqual(first.candidate_registry_sha256, second.candidate_registry_sha256)
            self.assertEqual("ALREADY_PRESENT_VERIFIED", second.evidence_packet_write_status)
            self.assertEqual("ALREADY_PRESENT_VERIFIED", second.candidate_registry_write_status)
            self.assertEqual(packet_before, second.evidence_packet_path.read_bytes())
            self.assertEqual(candidate_before, second.candidate_registry_path.read_bytes())
            self.assertEqual(packet_mtime_before, second.evidence_packet_path.stat().st_mtime_ns)
            self.assertEqual(candidate_mtime_before, second.candidate_registry_path.stat().st_mtime_ns)

    def test_21_same_hash_path_mismatched_bytes_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = materialize_evidence_and_candidate(valid_packet(), trusted_root=root)
            os.chmod(first.candidate_registry_path, stat.S_IREAD | stat.S_IWRITE)
            first.candidate_registry_path.write_bytes(b"{}\n")
            with self.assertRaises(MaterializationError) as caught:
                materialize_evidence_and_candidate(valid_packet(), trusted_root=root)
            self.assertEqual("INTEGRITY_FAILURE", caught.exception.code)
            self.assertEqual(b"{}\n", first.candidate_registry_path.read_bytes())

    def test_22_reparse_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            link_path = root / "workspace"
            try:
                if os.name == "nt":
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(link_path), str(outside)],
                        capture_output=True,
                    )
                    if result.returncode != 0:
                        self.skipTest("directory junction creation unavailable")
                else:
                    os.symlink(outside, link_path, target_is_directory=True)
                with self.assertRaises(MaterializationError):
                    materialize_evidence_and_candidate(valid_packet(), trusted_root=root)
            finally:
                if link_path.exists() or link_path.is_symlink():
                    os.rmdir(link_path) if os.name == "nt" else link_path.unlink()

    def test_23_production_activation_path_is_unchanged(self):
        activation = ROOT / "workspace" / "policies" / "instrument_identity_activation.json"
        self.assertFalse(activation.exists())

    def test_24_runtime_python_has_no_official_ticker_mapping(self):
        runtime_files = [
            SCRIPTS / "instrument_identity_authority.py",
            SCRIPTS / "run_manual_portfolio_analysis.py",
            SCRIPTS / "session_authority.py",
        ]
        for path in runtime_files:
            content = path.read_text(encoding="utf-8")
            for ticker in EXPECTED_SCOPE:
                self.assertNotIn(f'"{ticker}":', content, path.name)
            self.assertNotIn("Bloom Energy Corporation Common Stock", content)
            self.assertNotIn("Roundhill Memory ETF", content)

    def test_25_wrong_mic_source_family_fails(self):
        packet = valid_packet()
        packet["claims"][0]["source_family"] = "SEC"
        self.assert_invalid(packet)

    def test_26_missing_source_reference_fails(self):
        packet = valid_packet()
        packet["claims"][2]["source_reference"] = ""
        self.assert_invalid(packet)

    def test_27_unsupported_claim_scope_fails(self):
        packet = valid_packet()
        packet["claims"][2]["claim_scope"] = ["UNSUPPORTED_SCOPE"]
        self.assert_invalid(packet)

    def test_28_missing_retrieved_date_fails(self):
        packet = valid_packet()
        del packet["claims"][2]["retrieved_date"]
        self.assert_invalid(packet)

    def test_29_future_retrieved_date_fails(self):
        packet = valid_packet()
        packet["claims"][2]["retrieved_date"] = "2026-08-23"
        self.assert_invalid(packet, "TEMPORAL_VIOLATION")

    def test_30_source_attached_to_wrong_ticker_fails(self):
        packet = valid_packet()
        packet["claims"][2]["ticker"] = "NOW"
        self.assert_invalid(packet)

    def test_31_iso_source_without_segment_relation_fails(self):
        packet = valid_packet()
        packet["claims"][0]["claim_scope"] = ["MIC_IDENTITY", "MIC_STATUS"]
        packet["claims"][1]["claim_scope"] = ["OPERATING_MIC", "STATUS"]
        self.assert_invalid(packet)

    def test_32_not_captured_source_cannot_have_hash(self):
        packet = valid_packet()
        packet["claims"][2]["content_sha256"] = "0" * 64
        self.assert_invalid(packet)

    def test_33_candidate_source_refs_resolve_to_packet_sources(self):
        packet = valid_packet()
        _, _, artifact, _, _, _ = build_materialization(packet)
        source_ids = {item["source_id"] for item in packet["claims"]}
        for item in artifact["records"]:
            self.assertTrue(set(item["source_ref_ids"]).issubset(source_ids))

    def test_34_packet_and_artifact_filenames_are_fixed(self):
        with tempfile.TemporaryDirectory() as directory:
            result = materialize_evidence_and_candidate(valid_packet(), trusted_root=Path(directory))
            self.assertEqual(EVIDENCE_PACKET_FILENAME, result.evidence_packet_path.name)
            self.assertEqual(ARTIFACT_FILENAME, result.candidate_registry_path.name)
            self.assertEqual(
                ARTIFACT_DIRECTORY / result.candidate_registry_sha256 / ARTIFACT_FILENAME,
                result.candidate_registry_path.relative_to(directory),
            )

    @unittest.skipUnless(os.name == "nt", "actual Windows junction attack")
    def test_35_static_parent_junction_zero_outside_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            trusted = base / "trusted"
            outside = base / "outside"
            trusted.mkdir()
            outside.mkdir()
            (outside / "sentinel.bin").write_bytes(b"sentinel")
            junction = trusted / "workspace"
            before = self.outside_snapshot(outside)
            self.make_junction(junction, outside)
            try:
                with self.assertRaises(MaterializationError):
                    materializer._create_only_write(
                        trusted,
                        ARTIFACT_DIRECTORY / ("a" * 64) / "static-parent-probe.bin",
                        b"STATIC_PARENT_JUNCTION_PROBE\n",
                    )
                self.assertEqual(before, self.outside_snapshot(outside))
            finally:
                if junction.exists():
                    os.rmdir(junction)

    @unittest.skipUnless(os.name == "nt", "actual Windows junction attack")
    def test_36_hash_directory_junction_zero_outside_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            trusted = base / "trusted"
            outside = base / "outside"
            hash_parent = trusted / ARTIFACT_DIRECTORY
            hash_parent.mkdir(parents=True)
            outside.mkdir()
            (outside / "sentinel.bin").write_bytes(b"sentinel")
            hash_junction = hash_parent / ("b" * 64)
            relative = ARTIFACT_DIRECTORY / ("b" * 64) / "hash-junction-probe.bin"
            before = self.outside_snapshot(outside)
            self.make_junction(hash_junction, outside)
            try:
                with self.assertRaises(MaterializationError):
                    materializer._create_only_write(trusted, relative, b"HASH_DIRECTORY_JUNCTION_PROBE\n")
                self.assertEqual(before, self.outside_snapshot(outside))
            finally:
                if hash_junction.exists():
                    os.rmdir(hash_junction)

    @unittest.skipUnless(os.name == "nt", "actual Windows file-symlink attack")
    def test_37_final_file_symlink_zero_outside_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            trusted = base / "trusted"
            outside = base / "outside"
            relative = ARTIFACT_DIRECTORY / ("c" * 64) / "final-symlink-probe.bin"
            final_path = trusted / relative
            final_path.parent.mkdir(parents=True)
            outside.mkdir()
            outside_target = outside / "outside-target.bin"
            outside_target.write_bytes(b"outside-sentinel")
            os.symlink(outside_target, final_path, target_is_directory=False)
            before = self.outside_snapshot(outside)
            with self.assertRaises(MaterializationError):
                materializer._create_only_write(trusted, relative, b"FINAL_FILE_SYMLINK_PROBE\n")
            self.assertEqual(before, self.outside_snapshot(outside))

    @unittest.skipUnless(os.name == "nt", "actual Windows parent-substitution attack")
    def test_38_writer_parent_substitution_outside_write_attack(self):
        classification = "WRITER_PARENT_SUBSTITUTION_OUTSIDE_WRITE_ATTACK"
        attack_type = "ACTUAL_ATTACK"
        self.assertEqual("WRITER_PARENT_SUBSTITUTION_OUTSIDE_WRITE_ATTACK", classification)
        self.assertEqual("ACTUAL_ATTACK", attack_type)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            trusted = base / "trusted"
            outside = base / "outside"
            trusted.mkdir()
            outside.mkdir()
            (outside / "sentinel.bin").write_bytes(b"sentinel")
            relative = ARTIFACT_DIRECTORY / ("d" * 64) / "parent-substitution-probe.bin"
            parent = trusted / relative.parent
            parked = parent.with_name(parent.name + ".parked")
            attack = {"rename_blocked": False, "junction_created": False}
            before = self.outside_snapshot(outside)

            def substitute_parent() -> None:
                try:
                    os.replace(parent, parked)
                except OSError:
                    attack["rename_blocked"] = True
                else:
                    self.make_junction(parent, outside)
                    attack["junction_created"] = True
                raise OSError("ACTUAL_ATTACK_ABORT")

            try:
                with mock.patch.object(
                    materializer,
                    "_writer_pre_create_test_seam",
                    side_effect=substitute_parent,
                ):
                    with self.assertRaises(MaterializationError):
                        materializer._create_only_write(
                            trusted,
                            relative,
                            b"PARENT_SUBSTITUTION_PROBE\n",
                        )
                self.assertTrue(attack["rename_blocked"])
                self.assertFalse(attack["junction_created"])
                self.assertEqual(before, self.outside_snapshot(outside))
                self.assertFalse((outside / relative.name).exists())
            finally:
                if parent.exists() and attack["junction_created"]:
                    os.rmdir(parent)
                if parked.exists():
                    os.replace(parked, parent)

    @unittest.skipUnless(os.name == "nt", "actual Windows parent-rename attack")
    def test_39_parent_rename_substitution_zero_outside_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            trusted = base / "trusted"
            outside = base / "outside"
            trusted.mkdir()
            outside.mkdir()
            (outside / "sentinel.bin").write_bytes(b"sentinel")
            relative = ARTIFACT_DIRECTORY / ("e" * 64) / "parent-rename-probe.bin"
            rename_target = trusted / ARTIFACT_DIRECTORY
            parked = rename_target.with_name(rename_target.name + ".parked")
            attack = {"rename_blocked": False, "replacement_created": False}
            before = self.outside_snapshot(outside)

            def rename_parent() -> None:
                try:
                    os.replace(rename_target, parked)
                except OSError:
                    attack["rename_blocked"] = True
                else:
                    rename_target.mkdir()
                    attack["replacement_created"] = True
                raise OSError("ACTUAL_ATTACK_ABORT")

            try:
                with mock.patch.object(
                    materializer,
                    "_writer_pre_create_test_seam",
                    side_effect=rename_parent,
                ):
                    with self.assertRaises(MaterializationError):
                        materializer._create_only_write(
                            trusted,
                            relative,
                            b"PARENT_RENAME_SUBSTITUTION_PROBE\n",
                        )
                self.assertTrue(attack["rename_blocked"])
                self.assertFalse(attack["replacement_created"])
                self.assertEqual(before, self.outside_snapshot(outside))
            finally:
                if attack["replacement_created"] and rename_target.exists():
                    os.rmdir(rename_target)
                if parked.exists():
                    os.replace(parked, rename_target)


if __name__ == "__main__":
    unittest.main(verbosity=2)
