from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
sys.path.insert(0, str(SCRIPTS))

from current_event_risk import (
    append_checkpoint,
    build_checkpoint,
    scope_ticker_failure,
    validate_bundle_semantics,
    validate_checkpoint_chain,
    validate_checkpoint_hash,
)
from validation_common import canonical_hash, file_hash, load_json, validate_instance


BUNDLE_PATH = ROOT / "workspace/state/event_risk_archive/2026-08-13/event_risk_bundle.json"
CHECKPOINT_PATH = ROOT / "workspace/state/event_risk_archive/2026-08-13/event_checkpoint.json"
PORTFOLIO_PATH = ROOT / "stock-strategy-system/portfolio_state.json"


class CurrentEventRiskTests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_json(BUNDLE_PATH)

    def test_event_01_current_bundle_schema_and_semantics(self):
        self.assertEqual(validate_instance(self.bundle, SCHEMAS / "current-event-risk-bundle.schema.json"), [])
        self.assertEqual(validate_bundle_semantics(self.bundle), [])

    def test_event_02_future_published_evidence_is_rejected(self):
        value = deepcopy(self.bundle)
        event = value["events"][0]
        event["published_at"] = "2026-08-15T00:00:00Z"
        event["published_at_precision"] = "EXACT"
        errors = validate_bundle_semantics(value)
        self.assertIn(f"FUTURE_PUBLISHED_EVENT_ELIGIBLE:{event['event_id']}", errors)

    def test_event_03_append_only_refuses_same_session_overwrite(self):
        checkpoint = load_json(CHECKPOINT_PATH)
        with tempfile.TemporaryDirectory(dir=ROOT / "workspace/outputs") as directory:
            root = Path(directory)
            append_checkpoint(root, checkpoint)
            before = (root / "2026-08-13/event_checkpoint.json").read_bytes()
            with self.assertRaisesRegex(FileExistsError, "APPEND_ONLY"):
                append_checkpoint(root, checkpoint)
            self.assertEqual((root / "2026-08-13/event_checkpoint.json").read_bytes(), before)

    def test_event_04_checkpoint_hash_chain(self):
        first = load_json(CHECKPOINT_PATH)
        second = deepcopy(first)
        second["checkpoint_id"] = "event-risk-2026-08-14-test"
        second["market_session"] = "2026-08-14"
        second["analysis_cutoff"] = "2026-08-15T01:00:00Z"
        second["created_at"] = "2026-08-15T01:00:00Z"
        second["previous_record_hash"] = first["record_hash"]
        second["record_hash"] = None
        second["record_hash"] = canonical_hash({key: value for key, value in second.items() if key != "record_hash"})
        self.assertTrue(validate_checkpoint_chain([first, second]))

    def test_event_05_ticker_failure_is_local(self):
        value = scope_ticker_failure(self.bundle, "TOST", "test_only_missing_source")
        statuses = {item["ticker"]: item["status"] for item in value["ticker_coverage"]}
        self.assertEqual(statuses["TOST"], "UNAVAILABLE")
        for ticker in ("SOXL", "MVLL", "NBIS", "BE", "NOW", "FSLY", "SOXX", "MRVL"):
            original = next(item["status"] for item in self.bundle["ticker_coverage"] if item["ticker"] == ticker)
            self.assertEqual(statuses[ticker], original)

    def test_event_06_etf_and_underlying_events_remain_separate(self):
        for event in self.bundle["events"]:
            if event["ticker"] == "SOXX":
                self.assertNotIn("SOXL", event["applies_to"])
            if event["ticker"] == "MRVL":
                self.assertNotIn("MVLL", event["applies_to"])

    def test_event_07_checkpoint_schema_and_hash(self):
        checkpoint = load_json(CHECKPOINT_PATH)
        self.assertEqual(validate_instance(checkpoint, SCHEMAS / "event-risk-checkpoint.schema.json"), [])
        self.assertTrue(validate_checkpoint_hash(checkpoint))

    def test_event_08_no_backfill(self):
        with self.assertRaisesRegex(ValueError, "HISTORICAL_BACKFILL"):
            build_checkpoint(
                bundle=self.bundle,
                bundle_path=BUNDLE_PATH,
                market_session="2026-08-13",
                current_completed_session="2026-08-14",
                created_at="2026-08-15T01:00:00Z",
                portfolio_hash_before="a" * 64,
                portfolio_hash_after="a" * 64,
                event_policy_hash="b" * 64,
                active_research_baseline_index_hash="c" * 64,
                previous_record_hash=None,
            )

    def test_event_09_provider_strategy_quantity_and_order_authority_unchanged(self):
        self.assertFalse(self.bundle["provider_readiness_mutated"])
        self.assertFalse(self.bundle["strategy_state_mutated"])
        self.assertFalse(self.bundle["quantity_authority"])
        self.assertFalse(self.bundle["order_authority"])
        checkpoint = load_json(CHECKPOINT_PATH)
        self.assertFalse(checkpoint["provider_readiness_mutated"])
        self.assertFalse(checkpoint["strategy_state_mutated"])
        self.assertFalse(checkpoint["quantity_authority"])
        self.assertFalse(checkpoint["order_authority"])

    def test_event_10_portfolio_immutable_and_hash_recorded(self):
        before = file_hash(PORTFOLIO_PATH)
        checkpoint = load_json(CHECKPOINT_PATH)
        self.assertEqual(checkpoint["portfolio_state_hash_before"], before)
        self.assertEqual(checkpoint["portfolio_state_hash_after"], before)
        self.assertFalse(checkpoint["portfolio_mutated"])

    def test_event_11_policy_and_active_baseline_provenance(self):
        self.assertEqual(
            self.bundle["event_policy_hash"].lower(),
            file_hash(ROOT / "workspace/policies/event_risk_policy.json"),
        )
        self.assertEqual(
            self.bundle["active_research_baseline_index_hash"].lower(),
            file_hash(ROOT / "workspace/research/holding-baselines/active-index.json"),
        )
        self.assertEqual({item["ticker"] for item in self.bundle["active_research_baselines"]}, {"SOXL", "MVLL", "NBIS"})


if __name__ == "__main__":
    unittest.main()
