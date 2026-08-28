from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import materialize_session_calendar_artifact as materializer  # noqa: E402
from authority_artifact_io import canonical_json_bytes  # noqa: E402
from session_calendar_artifact import _semantic_validate_artifact  # noqa: E402
from validation_common import validate_instance  # noqa: E402


PACKET_PATH = (
    REPO_ROOT
    / "workspace/calendar-authority/reviewed-inputs"
    / "us-equities-core-session-2026-through-20260821.reviewed.json"
)


def reviewed_packet() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def early_close_packet() -> dict:
    packet = reviewed_packet()
    packet["packet_identity"] = "SYNTHETIC_EARLY_CLOSE_TEST_ONLY"
    packet["authority_as_of"] = "2026-11-28T00:00:00-05:00"
    packet["generated_at"] = "2026-11-28T00:00:00-05:00"
    packet["coverage_start"] = "2026-11-26"
    packet["coverage_end"] = "2026-11-27"
    packet["calendar_version"] = "synthetic-test-only"
    labels = {
        "NYSE_GROUP": "Thanksgiving Day",
        "NASDAQ": "Thanksgiving Day - U.S.",
        "CBOE": "Thanksgiving Day",
    }
    for calendar in packet["calendars"]:
        calendar["closures"] = [
            {"session_date": "2026-11-26", "label": labels[calendar["source_family"]]}
        ]
        calendar["early_closes"] = [
            {
                "session_date": "2026-11-27",
                "label": "Thanksgiving Early Close",
                "core_close": "13:00:00",
            }
        ]
    return packet


class SessionCalendarMaterializationTest(unittest.TestCase):
    def test_01_reviewed_packet_builds_exact_candidate_scope(self):
        bundle_bytes, bundle_hash, artifact, artifact_bytes, artifact_hash, counts = (
            materializer.build_materialization(reviewed_packet())
        )
        self.assertEqual(["XNYS", "XNAS", "XCBO"], artifact["operating_mic_scope"])
        self.assertEqual(["NYSE_GROUP", "NASDAQ", "CBOE"], artifact["source_families"])
        self.assertEqual(bundle_hash, artifact["source_bundle_hash"])
        self.assertEqual(bundle_hash, hashlib.sha256(bundle_bytes).hexdigest())
        self.assertEqual(artifact_hash, hashlib.sha256(artifact_bytes).hexdigest())
        self.assertEqual(4, counts["source_count"])

    def test_02_source_identity_and_claim_traceability_are_retained(self):
        bundle_bytes, _, _, _, _, counts = materializer.build_materialization(reviewed_packet())
        bundle = json.loads(bundle_bytes)
        source_ids = {source["source_id"] for source in bundle["official_sources"]}
        self.assertEqual(counts["claim_count"], len(bundle["calendar_claims"]))
        self.assertEqual(counts["claim_source_edge_count"], len(bundle["claim_source_edges"]))
        self.assertTrue(all(edge["source_id"] in source_ids for edge in bundle["claim_source_edges"]))
        self.assertTrue(all(claim["source_ids"] for claim in bundle["calendar_claims"]))

    def test_03_not_captured_content_hash_status_is_honest(self):
        bundle_bytes, _, _, _, _, _ = materializer.build_materialization(reviewed_packet())
        bundle = json.loads(bundle_bytes)
        self.assertEqual("NO", bundle["source_content_bytes_captured"])
        self.assertEqual("NOT_CAPTURED", bundle["source_content_hash_status"])
        self.assertTrue(all(source["content_sha256"] is None for source in bundle["official_sources"]))

    def test_04_not_captured_source_cannot_claim_content_hash(self):
        packet = reviewed_packet()
        packet["sources"][0]["content_sha256"] = "0" * 64
        with self.assertRaisesRegex(materializer.CalendarMaterializationError, "dishonest content hash"):
            materializer.build_materialization(packet)

    def test_05_non_official_source_host_fails_closed(self):
        packet = reviewed_packet()
        packet["sources"][0]["official_url"] = "https://example.com/calendar"
        with self.assertRaisesRegex(materializer.CalendarMaterializationError, "SOURCE_UNAVAILABLE"):
            materializer.build_materialization(packet)

    def test_06_missing_source_family_fails_closed(self):
        packet = reviewed_packet()
        packet["sources"] = [source for source in packet["sources"] if source["source_family"] != "CBOE"]
        with self.assertRaisesRegex(materializer.CalendarMaterializationError, "SOURCE_UNAVAILABLE"):
            materializer.build_materialization(packet)

    def test_07_future_coverage_relative_to_authority_fails(self):
        packet = reviewed_packet()
        packet["coverage_end"] = "2026-08-24"
        with self.assertRaisesRegex(materializer.CalendarMaterializationError, "TEMPORAL_VIOLATION"):
            materializer.build_materialization(packet)

    def test_08_full_closures_are_common_and_labels_may_differ(self):
        _, _, artifact, _, _, counts = materializer.build_materialization(reviewed_packet())
        closure_dates = [row["closure_date"] for row in artifact["closures"]]
        self.assertIn("2026-02-16", closure_dates)
        self.assertEqual(7, counts["closure_count"])

    def test_09_regular_session_has_exact_et_hours(self):
        _, _, artifact, _, _, _ = materializer.build_materialization(reviewed_packet())
        row = next(row for row in artifact["sessions"] if row["session_date"] == "2026-08-21")
        self.assertEqual("2026-08-21T09:30:00-04:00", row["core_open_at"])
        self.assertEqual("2026-08-21T16:00:00-04:00", row["core_close_at"])
        self.assertEqual("REGULAR", row["close_type"])

    def test_10_early_close_is_materialized_without_new_runtime_semantics(self):
        _, _, artifact, _, _, counts = materializer.build_materialization(early_close_packet())
        self.assertEqual(1, counts["session_count"])
        self.assertEqual(1, counts["closure_count"])
        self.assertEqual("EARLY", artifact["sessions"][0]["close_type"])
        self.assertEqual("2026-11-27T13:00:00-05:00", artifact["sessions"][0]["core_close_at"])

    def test_11_decision_relevant_cross_source_conflict_fails_closed(self):
        packet = reviewed_packet()
        packet["calendars"][2]["regular_close"] = "15:59:00"
        with self.assertRaisesRegex(materializer.CalendarMaterializationError, "CALENDAR_CONFLICT"):
            materializer.build_materialization(packet)

    def test_12_missing_calendar_family_fails_closed(self):
        packet = reviewed_packet()
        packet["calendars"].pop()
        with self.assertRaisesRegex(materializer.CalendarMaterializationError, "SOURCE_UNAVAILABLE"):
            materializer.build_materialization(packet)

    def test_13_source_bundle_and_candidate_validate_against_schemas(self):
        bundle_bytes, _, artifact, _, _, _ = materializer.build_materialization(reviewed_packet())
        bundle = json.loads(bundle_bytes)
        self.assertEqual(
            [],
            validate_instance(
                bundle,
                REPO_ROOT / "manage-us-stock-strategy/schemas/session-calendar-source-bundle.schema.json",
            ),
        )
        self.assertEqual(
            [],
            validate_instance(
                artifact,
                REPO_ROOT / "manage-us-stock-strategy/schemas/session-calendar-artifact.schema.json",
            ),
        )
        _semantic_validate_artifact(artifact)

    def test_14_exact_content_and_hash_are_reproducible(self):
        first = materializer.build_materialization(reviewed_packet())
        second = materializer.build_materialization(reviewed_packet())
        self.assertEqual(first[:5], second[:5])
        self.assertEqual(canonical_json_bytes(json.loads(first[0])), first[0])
        self.assertEqual(canonical_json_bytes(first[2]), first[3])

    def test_15_create_only_and_idempotent_rebuild(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = materializer.materialize_evidence_and_candidate(reviewed_packet(), trusted_root=root)
            second = materializer.materialize_evidence_and_candidate(reviewed_packet(), trusted_root=root)
            self.assertEqual("CREATED", first.evidence_packet_write_status)
            self.assertEqual("CREATED", first.candidate_artifact_write_status)
            self.assertEqual("ALREADY_PRESENT_VERIFIED", second.evidence_packet_write_status)
            self.assertEqual("ALREADY_PRESENT_VERIFIED", second.candidate_artifact_write_status)

    def test_16_mismatched_existing_candidate_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = materializer.materialize_evidence_and_candidate(reviewed_packet(), trusted_root=root)
            os.chmod(first.candidate_artifact_path, stat.S_IWRITE | stat.S_IREAD)
            first.candidate_artifact_path.write_bytes(b"mismatch")
            with self.assertRaises(materializer.CalendarMaterializationError):
                materializer.materialize_evidence_and_candidate(reviewed_packet(), trusted_root=root)
            self.assertEqual(b"mismatch", first.candidate_artifact_path.read_bytes())

    def test_17_candidate_does_not_create_activation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materializer.materialize_evidence_and_candidate(reviewed_packet(), trusted_root=root)
            self.assertFalse((root / materializer.ACTIVATION_RELATIVE_PATH).exists())

    def test_18_existing_activation_bytes_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            activation = root / materializer.ACTIVATION_RELATIVE_PATH
            activation.parent.mkdir(parents=True)
            activation.write_bytes(b"existing-read-only-activation")
            before = activation.read_bytes()
            result = materializer.materialize_evidence_and_candidate(reviewed_packet(), trusted_root=root)
            self.assertTrue(result.activation_unchanged)
            self.assertEqual(before, activation.read_bytes())

    def test_19_input_mutation_changes_bundle_and_candidate_hashes(self):
        packet = reviewed_packet()
        baseline = materializer.build_materialization(packet)
        changed = copy.deepcopy(packet)
        changed["packet_identity"] = "DIFFERENT_BOUNDED_PACKET"
        mutated = materializer.build_materialization(changed)
        self.assertNotEqual(baseline[1], mutated[1])
        self.assertNotEqual(baseline[4], mutated[4])


if __name__ == "__main__":
    unittest.main()
