from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from current_event_risk import append_checkpoint, scope_ticker_failure
from dual_phase_event_pipeline import build_refresh_windows, ingest_window


class DualPhaseEventPipelineTests(unittest.TestCase):
    def windows(self):
        return build_refresh_windows(previous_post_close_cutoff="2026-08-13T21:00:00Z",
                                     preopen_cutoff="2026-08-14T13:00:00Z",
                                     postclose_cutoff="2026-08-14T20:30:00Z")

    def event(self, event_id="NBIS-1", published="2026-08-14T12:00:00Z"):
        return {"event_id": event_id, "ticker": "NBIS", "event_type": "SEC_FILING",
                "source": "https://www.sec.gov/test", "source_type": "SEC",
                "published_at": published, "effective_at": None,
                "retrieved_at": "2026-08-14T12:30:00Z", "analysis_cutoff": "2026-08-14T13:00:00Z",
                "verification_status": "VERIFIED", "strategy_relevance": "CONTEXT_ONLY"}

    def test_cutoff_integrity(self):
        result = ingest_window([self.event()], window=self.windows()["PRE_OPEN_EVENT_REFRESH"],
                               run_id="preopen-1", previously_seen_event_ids=set())
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["first_seen_run_id"], "preopen-1")

    def test_future_evidence_rejected(self):
        event = self.event(published="2026-08-14T14:00:00Z")
        result = ingest_window([event], window=self.windows()["PRE_OPEN_EVENT_REFRESH"],
                               run_id="preopen-1", previously_seen_event_ids=set())
        self.assertEqual(result["rejected"][0]["reason"], "FUTURE_OR_CUTOFF_VIOLATION")

    def test_event_dedup(self):
        result = ingest_window([self.event()], window=self.windows()["PRE_OPEN_EVENT_REFRESH"],
                               run_id="preopen-2", previously_seen_event_ids={"NBIS-1"})
        self.assertEqual(result["events"], [])
        self.assertEqual(result["rejected"][0]["reason"], "DUPLICATE_EVENT_ID")

    def test_primary_source_required(self):
        event = self.event(); event["source_type"] = "NEWS_AGGREGATOR"
        result = ingest_window([event], window=self.windows()["PRE_OPEN_EVENT_REFRESH"],
                               run_id="preopen-1", previously_seen_event_ids=set())
        self.assertEqual(result["rejected"][0]["reason"], "PRIMARY_SOURCE_REQUIRED")

    def test_append_only_checkpoint(self):
        checkpoint = {"market_session": "2026-08-14", "analysis_cutoff": "2026-08-14T20:30:00Z"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            append_checkpoint(root, checkpoint)
            with self.assertRaises(FileExistsError):
                append_checkpoint(root, checkpoint)

    def test_ticker_failure_is_local(self):
        bundle = {"ticker_coverage": [
            {"ticker": "NBIS", "coverage_status": "COMPLETE_FOR_REQUIRED_CATEGORIES", "event_effect": "CONTEXT_ONLY", "event_data_incomplete": False, "missing_fields": []},
            {"ticker": "SOXL", "coverage_status": "COMPLETE_FOR_REQUIRED_CATEGORIES", "event_effect": "CONTEXT_ONLY", "event_data_incomplete": False, "missing_fields": []}],
            "event_data_status": "COMPLETE", "bundle_status": "COMPLETE", "coverage_status": "COMPLETE_FOR_REQUIRED_CATEGORIES"}
        scoped = scope_ticker_failure(copy.deepcopy(bundle), "NBIS", "earnings_date")
        self.assertEqual(scoped["ticker_coverage"][0]["coverage_status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(scoped["ticker_coverage"][1]["coverage_status"], "COMPLETE_FOR_REQUIRED_CATEGORIES")


if __name__ == "__main__":
    unittest.main()
