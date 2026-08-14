from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
sys.path.insert(0, str(SCRIPTS))

from current_event_risk import (
    append_checkpoint,
    build_checkpoint,
    classify_announcement_status,
    event_gate_for_coverage,
    scope_ticker_failure,
    validate_bundle_semantics,
    validate_checkpoint_chain,
    validate_checkpoint_hash,
)
from correct_event_risk_bundle import apply_source_corrections
from finalized_postmarket_automation import current_event_bundle_readiness
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
        root = ROOT / "workspace/outputs" / f"event-risk-test-{uuid.uuid4().hex}"
        try:
            append_checkpoint(root, checkpoint)
            before = (root / "2026-08-13/event_checkpoint.json").read_bytes()
            with self.assertRaisesRegex(FileExistsError, "APPEND_ONLY"):
                append_checkpoint(root, checkpoint)
            self.assertEqual((root / "2026-08-13/event_checkpoint.json").read_bytes(), before)
        finally:
            shutil.rmtree(root, ignore_errors=True)

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
        statuses = {item["ticker"]: item["coverage_status"] for item in value["ticker_coverage"]}
        self.assertEqual(statuses["TOST"], "SOURCE_UNAVAILABLE")
        for ticker in ("SOXL", "MVLL", "NBIS", "BE", "NOW", "FSLY", "SOXX", "MRVL"):
            original = next(item["coverage_status"] for item in self.bundle["ticker_coverage"] if item["ticker"] == ticker)
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
                source_evidence_ledger_hash="d" * 64,
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
        current_before = file_hash(PORTFOLIO_PATH)
        checkpoint = load_json(CHECKPOINT_PATH)
        self.assertRegex(checkpoint["portfolio_state_hash_before"], r"^[A-Fa-f0-9]{64}$")
        self.assertEqual(
            checkpoint["portfolio_state_hash_before"],
            checkpoint["portfolio_state_hash_after"],
        )
        self.assertFalse(checkpoint["portfolio_mutated"])
        self.assertEqual(file_hash(PORTFOLIO_PATH), current_before)

    def test_event_11_policy_and_active_baseline_provenance(self):
        self.assertEqual(
            self.bundle["event_policy_hash"].lower(),
            file_hash(ROOT / "workspace/policies/event_risk_policy.json"),
        )
        self.assertRegex(self.bundle["active_research_baseline_index_hash"], r"^[A-Fa-f0-9]{64}$")
        for item in self.bundle["active_research_baselines"]:
            baseline_path = (
                ROOT / "workspace/research/holding-baselines"
                / item["ticker"] / f"{item['baseline_id']}.json"
            )
            self.assertEqual(load_json(baseline_path)["baseline_hash"], item["baseline_hash"])
        self.assertEqual({item["ticker"] for item in self.bundle["active_research_baselines"]}, {"SOXL", "MVLL", "NBIS"})

    def test_event_12_tost_q2_results_use_official_form_8k_and_exhibit(self):
        event = next(item for item in self.bundle["events"] if item["event_id"] == "TOST-20260804-Q2-EARNINGS")
        self.assertEqual(event["source_type"], "SEC")
        self.assertEqual(event["verification_status"], "VERIFIED")
        self.assertEqual(event["event_type"], "EARNINGS_RELEASE")
        self.assertEqual(set(event["evidence_ids"]), {"TOST-SEC-8K-20260804", "TOST-SEC-EX991-Q2-2026"})
        coverage = next(item for item in self.bundle["ticker_coverage"] if item["ticker"] == "TOST")
        self.assertNotIn("official_q2_2026_results_release_or_sec_8k", coverage["missing_fields"])

    def test_event_13_fastly_exact_release_supplement_and_investor_day_are_separate(self):
        earnings = next(item for item in self.bundle["events"] if item["event_id"] == "FSLY-20260805-Q2-EARNINGS")
        investor_day = next(item for item in self.bundle["events"] if item["event_id"] == "FSLY-20260922-INVESTOR-DAY")
        self.assertIn("fastly-announces-second-quarter-2026-financial-results", earnings["source_url"])
        self.assertIn("FSLY-IR-Q2-2026-SUPPLEMENT", earnings["evidence_ids"])
        self.assertEqual(investor_day["event_type"], "INVESTOR_DAY")
        self.assertNotEqual(earnings["event_id"], investor_day["event_id"])

    def test_event_14_mvll_split_dates_and_exact_ticker(self):
        event = next(item for item in self.bundle["events"] if item["event_id"] == "MVLL-20260626-3FOR1-FORWARD-SPLIT")
        self.assertEqual(event["event_type"], "ETF_SPLIT_OR_REVERSE_SPLIT")
        self.assertEqual(event["record_at"], "2026-06-24T23:59:59Z")
        self.assertEqual(event["payable_at"], "2026-06-25T23:59:59Z")
        self.assertEqual(event["effective_at"], "2026-06-26T23:59:59Z")
        self.assertEqual(event["applies_to"], ["MVLL"])

    def test_event_15_exact_ticker_matching_and_underlying_separation(self):
        for event in self.bundle["events"]:
            if event["ticker"] != "GLOBAL":
                self.assertEqual(event["applies_to"], [event["ticker"]])
        mrvl = [item for item in self.bundle["events"] if item["ticker"] == "MRVL"]
        self.assertTrue(all("MVLL" not in item["applies_to"] for item in mrvl))

    def test_event_16_unannounced_is_not_a_collection_failure(self):
        self.assertEqual(
            classify_announcement_status(announced=False, official_route_checked=True),
            "NOT_YET_ANNOUNCED_AS_OF_CUTOFF",
        )
        self.assertEqual(
            classify_announcement_status(announced=False, official_route_checked=False),
            "SEARCH_INCOMPLETE",
        )

    def test_event_17_coverage_and_event_effect_are_separate(self):
        self.assertEqual(event_gate_for_coverage("PARTIAL_NONBLOCKING", "CONTEXT_ONLY"), "CONTEXT_ONLY")
        self.assertEqual(event_gate_for_coverage("PARTIAL_BLOCKING", "CONTEXT_ONLY"), "EVENT_REVIEW_PENDING")
        self.assertEqual(event_gate_for_coverage("COMPLETE_FOR_REQUIRED_CATEGORIES", "WAIT_REQUIRED"), "WAIT_REQUIRED")

    def test_event_18_partial_nonblocking_does_not_change_provider_readiness(self):
        soxl = next(item for item in self.bundle["ticker_coverage"] if item["ticker"] == "SOXL")
        self.assertEqual(soxl["coverage_status"], "PARTIAL_NONBLOCKING")
        self.assertEqual(soxl["event_effect"], "CONTEXT_ONLY")
        self.assertFalse(self.bundle["provider_readiness_mutated"])

    def test_event_19_category_records_are_hashed_and_ticker_local(self):
        category_ids = {item["category_id"] for item in self.bundle["category_coverage"]}
        for coverage in self.bundle["ticker_coverage"]:
            self.assertTrue(set(coverage["category_ids"]).issubset(category_ids))
        tost = [item for item in self.bundle["category_coverage"] if item["ticker"] == "TOST"]
        self.assertTrue(any(item["event_category"] == "RECENT_EARNINGS" for item in tost))

    def test_event_20_checkpoint_includes_source_ledger_and_coverage_hashes(self):
        checkpoint = load_json(CHECKPOINT_PATH)
        self.assertEqual(
            checkpoint["source_evidence_ledger_hash"],
            canonical_hash(load_json(ROOT / "workspace/research/event-evidence/v2.6.9-official-source-ledger.json")),
        )
        self.assertEqual(checkpoint["bundle_hash"], canonical_hash(self.bundle))
        self.assertEqual(checkpoint["coverage_status"], self.bundle["coverage_status"])
        self.assertEqual(checkpoint["event_count"], len(self.bundle["events"]))

    def test_event_21_scheduled_gate_consumes_ticker_local_coverage(self):
        readiness = current_event_bundle_readiness(self.bundle)
        self.assertFalse(readiness["provider_readiness_mutated"])
        self.assertEqual(readiness["ticker_event_gates"]["SOXL"], "CONTEXT_ONLY")
        self.assertEqual(readiness["ticker_event_gates"]["MVLL"], "CONTEXT_ONLY")
        self.assertEqual(readiness["ticker_event_gates"]["TOST"], "EVENT_REVIEW_PENDING")
        self.assertEqual(readiness["event_readiness_status"], "EVENT_REVIEW_PENDING")

    def test_event_22_missing_or_invalid_bundle_fails_closed(self):
        self.assertEqual(
            current_event_bundle_readiness(None)["event_readiness_status"],
            "EVENT_DATA_INCOMPLETE",
        )
        value = deepcopy(self.bundle)
        value["ticker_coverage"] = []
        self.assertEqual(
            current_event_bundle_readiness(value)["event_readiness_status"],
            "EVENT_DATA_INCOMPLETE",
        )

    def test_event_23_correction_evidence_must_be_registered_and_ticker_exact(self):
        ledger = load_json(ROOT / "workspace/research/event-evidence/v2.6.9-official-source-ledger.json")
        bad = deepcopy(ledger)
        bad["corrections"][0]["evidence_ids"] = ["UNREGISTERED-EVIDENCE"]
        with self.assertRaisesRegex(ValueError, "CORRECTION_EVIDENCE_NOT_REGISTERED"):
            apply_source_corrections(self.bundle, bad)

        bad = deepcopy(ledger)
        bad["evidence_routes"][0]["ticker"] = "FSLY"
        with self.assertRaisesRegex(ValueError, "CORRECTION_EVIDENCE_TICKER_MISMATCH"):
            apply_source_corrections(self.bundle, bad)

    def test_event_24_archive_manifest_hashes_and_scheduled_consumption(self):
        manifest = load_json(ROOT / "workspace/research/event-evidence/v2.6.9-event-risk-archive-manifest.json")
        self.assertEqual(
            validate_instance(manifest, SCHEMAS / "event-risk-archive-manifest.schema.json"),
            [],
        )
        checkpoint = load_json(CHECKPOINT_PATH)
        self.assertEqual(manifest["hash_basis"], "CANONICAL_JSON_SHA256")
        self.assertEqual(manifest["bundle_sha256"], canonical_hash(self.bundle))
        self.assertEqual(manifest["checkpoint_sha256"], canonical_hash(checkpoint))
        self.assertEqual(manifest["checkpoint_record_hash"], checkpoint["record_hash"])
        self.assertEqual(
            manifest["source_evidence_ledger_sha256"],
            canonical_hash(load_json(ROOT / manifest["source_evidence_ledger_path"])),
        )
        self.assertEqual(
            manifest["portfolio_state_sha256"],
            checkpoint["portfolio_state_hash_before"],
        )
        self.assertTrue(manifest["scheduled_task_consumes_bundle"])
        automation_prompt = (ROOT / "stock-strategy-system/AUTOMATION_PROMPT_EN.md").read_text(encoding="utf-8")
        self.assertIn("workspace/state/event_risk_archive/<SESSION>/", automation_prompt)
        self.assertIn("PARTIAL_NONBLOCKING", automation_prompt)


if __name__ == "__main__":
    unittest.main()
