from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
sys.path.insert(0, str(SCRIPTS))

from complete_holding_event_coverage import (
    REQUIRED_CATEGORIES,
    build_successor_bundle,
    validate_completion_ledger,
)
from current_event_risk import scope_ticker_failure, validate_bundle_semantics
from holding_baseline_operationalization import validate_event_link
from validation_common import canonical_hash, file_hash, load_json, validate_instance


BASE_PATH = ROOT / "workspace/state/event_risk_archive/2026-08-13/event_risk_bundle.json"
LEDGER_PATH = ROOT / "workspace/research/event-evidence/v2.6.13-holding-event-completion-ledger.json"
BUNDLE_PATH = ROOT / "workspace/research/event-evidence/event-risk-2026-08-13-holding-completion-20260814T073717Z.json"
MANIFEST_PATH = ROOT / "workspace/research/event-evidence/v2.6.13-holding-event-completion-manifest.json"
LINK_ROOT = ROOT / "workspace/research/baseline-event-links/2026-08-13/v2.6.13"
PORTFOLIO_PATH = ROOT / "stock-strategy-system/portfolio_state.json"
ACTIVE_INDEX_PATH = ROOT / "workspace/research/holding-baselines/active-index.json"


def _contains_authority_violation(value):
    if isinstance(value, dict):
        return any(
            (key == "order_authority" and item is not False) or _contains_authority_violation(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_authority_violation(item) for item in value)
    return False


class HoldingEventCompletionTests(unittest.TestCase):
    def setUp(self):
        self.base = load_json(BASE_PATH)
        self.ledger = load_json(LEDGER_PATH)
        self.bundle = load_json(BUNDLE_PATH)
        self.manifest = load_json(MANIFEST_PATH)

    def test_event_completion_01_ledger_schema_exact_scope_and_base_hash(self):
        self.assertEqual(validate_instance(self.ledger, SCHEMAS / "event-risk-completion-ledger.schema.json"), [])
        self.assertEqual(validate_completion_ledger(self.ledger, self.base, BASE_PATH), [])
        self.assertEqual(self.ledger["base_bundle_file_hash"], file_hash(BASE_PATH))
        actual = {}
        for item in self.ledger["required_category_checks"]:
            actual.setdefault(item["ticker"], set()).add(item["required_category"])
        self.assertEqual(actual, REQUIRED_CATEGORIES)

    def test_event_completion_02_successor_schema_semantics_and_determinism(self):
        self.assertEqual(validate_instance(self.bundle, SCHEMAS / "current-event-risk-bundle.schema.json"), [])
        self.assertEqual(validate_bundle_semantics(self.bundle), [])
        self.assertEqual(build_successor_bundle(self.base, self.ledger), self.bundle)

    def test_event_completion_03_target_coverage_complete_effect_remains_separate(self):
        coverage = {item["ticker"]: item for item in self.bundle["ticker_coverage"]}
        for ticker in ("SOXL", "MVLL", "NBIS", "MRVL"):
            self.assertEqual(coverage[ticker]["coverage_status"], "COMPLETE_FOR_REQUIRED_CATEGORIES")
            self.assertFalse(coverage[ticker]["event_data_incomplete"])
            self.assertEqual(coverage[ticker]["missing_fields"], [])
        self.assertEqual(coverage["SOXL"]["event_effect"], "CONTEXT_ONLY")
        self.assertEqual(coverage["MVLL"]["event_effect"], "CONTEXT_ONLY")
        self.assertEqual(coverage["NBIS"]["event_effect"], "EVENT_REVIEW_REQUIRED")
        self.assertEqual(coverage["MRVL"]["event_effect"], "EVENT_REVIEW_REQUIRED")

    def test_event_completion_04_nb_is_next_earnings_is_unannounced_not_missing(self):
        exact = next(
            item for item in self.ledger["required_category_checks"]
            if item["category_id"] == "NBIS:NEXT_OFFICIALLY_ANNOUNCED_EARNINGS"
        )
        self.assertEqual(exact["announcement_status"], "NOT_YET_ANNOUNCED_AS_OF_CUTOFF")
        self.assertEqual(exact["required_source_route_ids"], exact["checked_source_route_ids"])
        self.assertIsNone(exact["published_at"])
        self.assertIsNone(exact["effective_at"])

    def test_event_completion_05_etf_and_underlying_records_are_separate(self):
        for event in self.bundle["events"]:
            if event["ticker"] == "SOXX":
                self.assertNotIn("SOXL", event["applies_to"])
            if event["ticker"] == "MRVL":
                self.assertEqual(event["applies_to"], ["MRVL"])
        target_ids = {item["category_id"] for item in self.ledger["required_category_checks"]}
        self.assertFalse(any(value.startswith("SOXX:") for value in target_ids))
        self.assertFalse(any(value.startswith("MVLL:MRVL") for value in target_ids))

    def test_event_completion_06_links_validate_and_bind_exact_hashes(self):
        targets = {item["ticker"]: item for item in self.ledger["link_targets"]}
        for path in sorted(LINK_ROOT.glob("*.json")):
            link = load_json(path)
            target = targets[link["ticker"]]
            baseline_path = ROOT / target["baseline_path"]
            baseline = load_json(baseline_path)
            validation = validate_event_link(
                link,
                schema_path=SCHEMAS / "baseline-event-link.schema.json",
                baseline=baseline,
                event_bundle_path=BUNDLE_PATH,
            )
            self.assertEqual(validation["validation_status"], "PASSED")
            self.assertEqual(link["baseline_hash"], baseline["baseline_hash"])
            self.assertEqual(link["event_bundle_hash"], file_hash(BUNDLE_PATH))
            self.assertEqual(link["link_hash"], canonical_hash({k: v for k, v in link.items() if k != "link_hash"}))

    def test_event_completion_07_link_status_preserves_event_review(self):
        links = {load_json(path)["ticker"]: load_json(path) for path in LINK_ROOT.glob("*.json")}
        self.assertEqual(links["SOXL"]["link_validation_status"], "VALID")
        self.assertEqual(links["MVLL"]["link_validation_status"], "VALID")
        self.assertEqual(links["NBIS"]["link_validation_status"], "EVENT_REVIEW_PENDING")
        self.assertEqual(links["MRVL"]["link_validation_status"], "EVENT_REVIEW_PENDING")
        self.assertTrue(all(item["event_coverage_status"] == "COMPLETE" for item in links.values()))

    def test_event_completion_08_manifest_hashes_and_data_only_classification(self):
        self.assertEqual(validate_instance(self.manifest, SCHEMAS / "holding-event-completion-manifest.schema.json"), [])
        self.assertEqual(self.manifest["change_classification"], "DATA_ONLY")
        self.assertEqual(self.manifest["successor_bundle_file_hash"], file_hash(BUNDLE_PATH))
        self.assertEqual(self.manifest["successor_bundle_canonical_hash"], canonical_hash(self.bundle))
        self.assertEqual(self.manifest["source_ledger_canonical_hash"], canonical_hash(self.ledger))

    def test_event_completion_09_active_bundle_and_active_baselines_remain_unchanged(self):
        self.assertEqual(file_hash(BASE_PATH), self.manifest["active_bundle_file_hash"])
        self.assertEqual(file_hash(ACTIVE_INDEX_PATH), self.manifest["active_baseline_index_hash"])
        index = load_json(ACTIVE_INDEX_PATH)
        active_ids = {item["baseline_id"] for item in index["active"].values()}
        self.assertEqual(active_ids, {"soxl-20260813-v1", "mvll-20260813-v1", "nbis-20260813-v1"})
        self.assertFalse(self.manifest["active_bundle_mutated"])
        self.assertFalse(self.manifest["active_baseline_index_mutated"])
        self.assertFalse(self.manifest["baseline_activation_mutated"])

    def test_event_completion_10_ticker_failure_is_local(self):
        failed = scope_ticker_failure(self.bundle, "NBIS", "TEST_ONLY_EVENT_ROUTE_FAILURE")
        original = {item["ticker"]: item["coverage_status"] for item in self.bundle["ticker_coverage"]}
        changed = {item["ticker"]: item["coverage_status"] for item in failed["ticker_coverage"]}
        self.assertEqual(changed["NBIS"], "SOURCE_UNAVAILABLE")
        for ticker, status in original.items():
            if ticker != "NBIS":
                self.assertEqual(changed[ticker], status)

    def test_event_completion_11_official_sources_https_and_cutoff_safe(self):
        cutoff = self.ledger["analysis_cutoff"]
        for route in self.ledger["evidence_routes"]:
            self.assertTrue(route["source_url"].startswith("https://"))
            self.assertIn(route["source_type"], {"SEC", "ISSUER_IR", "ETF_SPONSOR", "EXCHANGE", "REGULATOR"})
            self.assertLessEqual(route["checked_at"], cutoff)
        for item in self.ledger["required_category_checks"]:
            if item["published_at"]:
                self.assertLessEqual(item["published_at"], cutoff)

    def test_event_completion_12_portfolio_and_authority_immutable(self):
        self.assertEqual(file_hash(PORTFOLIO_PATH), self.manifest["portfolio_state_hash_before"])
        self.assertEqual(file_hash(PORTFOLIO_PATH), self.manifest["portfolio_state_hash_after"])
        self.assertFalse(self.manifest["portfolio_mutated"])
        for value in (self.ledger, self.bundle, self.manifest):
            self.assertFalse(_contains_authority_violation(value))
        for path in LINK_ROOT.glob("*.json"):
            self.assertFalse(_contains_authority_violation(load_json(path)))

    def test_event_completion_13_incomplete_required_route_fails_closed(self):
        bad = deepcopy(self.ledger)
        bad["required_category_checks"][0]["checked_source_route_ids"] = ["NBIS-IR-EVENTS-NEXT-EARNINGS"]
        errors = validate_completion_ledger(bad, self.base, BASE_PATH)
        self.assertTrue(any("REQUIRED_ROUTE_CHECK_INCOMPLETE" in item for item in errors))

    def test_event_completion_14_unannounced_with_dates_fails_closed(self):
        bad = deepcopy(self.ledger)
        target = next(
            item for item in bad["required_category_checks"]
            if item["announcement_status"] == "NOT_YET_ANNOUNCED_AS_OF_CUTOFF"
        )
        target["published_at"] = "2026-08-14T07:00:00Z"
        errors = validate_completion_ledger(bad, self.base, BASE_PATH)
        self.assertTrue(any("UNANNOUNCED_CATEGORY_HAS_EVENT_DATE" in item for item in errors))

    def test_event_completion_15_no_soxx_baseline_link_created(self):
        links = [load_json(path) for path in LINK_ROOT.glob("*.json")]
        self.assertEqual({item["ticker"] for item in links}, {"SOXL", "MVLL", "NBIS", "MRVL"})
        self.assertNotIn("SOXX", {item["ticker"] for item in links})


if __name__ == "__main__":
    unittest.main()
