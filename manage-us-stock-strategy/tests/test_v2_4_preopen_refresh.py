from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_post_market_baseline import build_baseline
from build_premarket_snapshot import build_snapshot as build_premarket
from run_preopen_portfolio_refresh import build_preopen_refresh, main as preopen_main
from validation_common import load_json, validate_instance


class V24PreopenRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_json(ROOT / "workspace" / "policies" / "preopen_refresh_policy.json")
        self.report = self._report()
        self.manifest = self._manifest("POST-TEST", "abc123")
        self.baseline = build_baseline(self.report, self.manifest, git_commit="abc123",
            strategy_version="2026-08-05-v4", policy_version="TEST-POLICY")

    def _manifest(self, run_id="POST-TEST", git_commit="abc123"):
        return {"schema_version": "1.0", "run_phase": "POST_MARKET", "run_id": run_id,
            "analysis_id": run_id, "run_type": "VALIDATION_TEST", "generated_at": "2026-08-12T01:00:00+00:00",
            "analysis_cutoff": "2026-08-12T01:00:00+00:00", "market_session": "2026-08-11",
            "code_provenance": {"git_commit": git_commit, "git_branch": "TEST", "git_dirty": False,
                "working_tree_diff_hash": None, "skill_version": "2.4", "schema_versions": {},
                "strategy_version": "2026-08-05-v4", "policy_version": "TEST-POLICY"},
            "llm_provenance": {"provider": None, "model": None, "model_identifier": None, "temperature": None,
                "max_debate_rounds": 0, "max_risk_rounds": 0}, "input_hashes": {}, "tool_provenance": {},
            "result_provenance": {"research_packet_hash": None, "decision_record_hash": None,
                "tactical_screen_hash": None, "deterministic_gate_hash": None,
                "deterministic_gate_result": "WAIT"}, "secrets_recorded": False}

    def _portfolio(self, cash=0.0):
        return {"strategy_version": "2026-08-05-v4", "available_cash_usd": cash,
            "holdings": {"NBIS": 15}, "average_cost_usd": {"NBIS": 215.0},
            "last_confirmed_broker_snapshot": {"verified": True, "cash_verified": True,
                "holdings_complete": True, "cash_verified_scope": "available_cash_only",
                "as_of": "2026-08-12", "source": "TEST_ONLY"}}

    def _report(self, opportunity="READY", execution="CASH_BLOCKED", strategy="HOLD", new_buy=True):
        return {"schema_version": "2.4", "run_phase": "POST_MARKET", "generated_at": "2026-08-12T01:00:00+00:00",
            "market_session": "2026-08-11", "holding_strategies": [{"ticker": "NBIS", "strategy_state": strategy,
                "execution_state": "NOT_APPLICABLE", "average_cost_usd": 215.0, "remaining_conditions": [],
                "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}],
            "tactical_radar_result": {"candidate_dispositions": [{"ticker": "NBIS",
                "opportunity_state": opportunity, "execution_state": execution, "new_buy_approval": new_buy,
                "remaining_conditions": [], "next_review_trigger": "NEXT_COMPLETED_US_SESSION"}]},
            "holding_risk_result": {"candidates": [{"symbol": "NBIS", "hard_boundary_usd": 193.5}]},
            "capital_redeployment": {}, "component_artifacts": {"market_snapshot_hash": "a" * 64,
                "event_snapshot_hash": "b" * 64, "tactical_radar_hash": "c" * 64,
                "capital_redeployment_hash": "d" * 64}}

    def _premarket(self, quote=210.0, *, provider="AVAILABLE", include=True):
        records = [] if not include else [{"ticker": "NBIS", "quote": quote, "bid": quote - .1, "ask": quote + .1,
            "quote_timestamp": "2026-08-12T12:40:00+00:00", "timezone": "America/New_York",
            "provider": "TEST_ONLY", "source_identifier": "TEST", "reference_completed_close": 205.0, "volume": 1000}]
        return build_premarket(records, generated_at="2026-08-12T12:40:00+00:00",
            upcoming_session="2026-08-12", latest_completed_session="2026-08-11", provider_status=provider,
            official_upcoming_session_verified=True, session_verification_status="verified_trading_day")

    def _events(self, material=False, blocked=False):
        events = []
        if material:
            events.append({"ticker": "NBIS", "validation_status": "VALIDATED", "source_type": "primary",
                "announced_at": "2026-08-12T10:00:00+00:00", "retrieved_at": "2026-08-12T10:05:00+00:00",
                "policy_effect": "WAIT_REQUIRED" if blocked else "CONTEXT_ONLY"})
        return {"coverage_status": "COMPLETE", "events": events}

    def _run(self, **kwargs):
        report = kwargs.pop("report", self.report)
        baseline = kwargs.pop("baseline", self.baseline)
        return build_preopen_refresh(baseline=baseline, post_market_report=report,
            post_market_manifest=kwargs.pop("manifest", self.manifest),
            premarket_snapshot=kwargs.pop("premarket", self._premarket()),
            overnight_events=kwargs.pop("events", self._events()), portfolio_state=kwargs.pop("portfolio", self._portfolio()),
            preopen_policy=kwargs.pop("policy", self.policy), runtime=kwargs.pop("runtime", None),
            generated_at="2026-08-12T12:45:00+00:00", upcoming_session="2026-08-12",
            latest_completed_session="2026-08-11", strategy_version="2026-08-05-v4",
            post_market_policy_version="TEST-POLICY")

    def test_approved_gap_rule_can_only_downgrade_execution(self):
        policy = copy.deepcopy(self.policy)
        policy["gap_policy"]["approved_gap_rules"]["NBIS"] = {"approval_status": "VERIFIED_USER_APPROVAL",
            "rule_type": "outside_entry_band", "entry_band": [200.0, 220.0]}
        report, _ = self._run(policy=policy, premarket=self._premarket(230.0))
        item = report["items"][0]
        self.assertEqual(item["post_market_opportunity_state"], "READY")
        self.assertEqual(item["preopen_readiness_state"], "GAP_INVALIDATED")
        self.assertEqual(item["refreshed_execution_state"], "WATCH_ONLY")
        self.assertIsNone(item["quantity"])

    def test_premarket_price_above_ema_cannot_upgrade_watch(self):
        report = self._report(opportunity="WATCH", execution="WATCH_ONLY")
        manifest = self._manifest("WATCH", "abc")
        baseline = build_baseline(report, manifest, git_commit="abc", strategy_version="2026-08-05-v4", policy_version="TEST-POLICY")
        output, _ = self._run(report=report, baseline=baseline, manifest=manifest, premarket=self._premarket(300.0))
        self.assertEqual(output["items"][0]["post_market_opportunity_state"], "WATCH")
        self.assertEqual(output["items"][0]["refreshed_execution_state"], "WATCH_ONLY")

    def test_premarket_below_loss_boundary_is_watch_not_breach(self):
        output, _ = self._run(premarket=self._premarket(190.0))
        item = output["items"][0]
        self.assertEqual(item["premarket_risk_state"], "PREMARKET_RISK_WATCH")
        self.assertNotEqual(item["preopen_readiness_state"], "HARD_RISK_BREACH")

    def test_official_overnight_release_requires_research_refresh(self):
        output, _ = self._run(events=self._events(material=True))
        self.assertEqual(output["items"][0]["preopen_readiness_state"], "RESEARCH_REFRESH_REQUIRED")
        self.assertEqual(output["items"][0]["refreshed_execution_state"], "WATCH_ONLY")

    def test_wait_required_event_blocks_execution(self):
        output, _ = self._run(events=self._events(material=True, blocked=True))
        self.assertEqual(output["items"][0]["preopen_readiness_state"], "EVENT_BLOCKED")

    def test_fresh_verified_cash_rechecks_but_never_orders(self):
        output, _ = self._run(portfolio=self._portfolio(10000))
        self.assertEqual(output["items"][0]["refreshed_execution_state"], "ELIGIBLE_FOR_REVIEW")
        self.assertFalse(output["order_authority"])

    def test_projected_proceeds_are_not_a_preopen_cash_input(self):
        output, _ = self._run(portfolio=self._portfolio(0))
        self.assertEqual(output["items"][0]["refreshed_execution_state"], "CASH_BLOCKED")

    def test_global_premarket_outage_is_one_global_event(self):
        output, _ = self._run(premarket=self._premarket(provider="UNAVAILABLE", include=False))
        global_events = [event for event in output["transitions"] if event["ticker"] == "GLOBAL"]
        ticker_notifications = [event for event in output["transitions"] if event["ticker"] != "GLOBAL" and event["notify"]]
        self.assertEqual(len(global_events), 1)
        self.assertEqual(ticker_notifications, [])

    def test_one_ticker_premarket_failure_is_isolated(self):
        report = self._report()
        report["tactical_radar_result"]["candidate_dispositions"].append({"ticker": "NOW", "opportunity_state": "READY",
            "execution_state": "NOT_APPROVED", "new_buy_approval": False, "remaining_conditions": []})
        manifest = self._manifest("PARTIAL", "abc")
        baseline = build_baseline(report, manifest, git_commit="abc", strategy_version="2026-08-05-v4", policy_version="TEST-POLICY")
        output, _ = self._run(report=report, baseline=baseline, manifest=manifest, premarket=self._premarket())
        states = {item["ticker"]: item["preopen_readiness_state"] for item in output["items"]}
        self.assertEqual(states["NOW"], "DATA_INCOMPLETE")
        self.assertNotEqual(states["NBIS"], "DATA_INCOMPLETE")

    def test_missing_and_invalid_baseline_fail_closed(self):
        missing, _ = self._run(baseline=None, report=None)
        self.assertEqual(missing["baseline_hash_status"], "POST_MARKET_BASELINE_MISSING")
        invalid = copy.deepcopy(self.baseline)
        invalid["baseline_hash"] = "0" * 64
        failed, _ = self._run(baseline=invalid)
        self.assertEqual(failed["baseline_hash_status"], "POST_MARKET_BASELINE_INVALID")

    def test_duplicate_run_suppresses_urgent_delivery(self):
        first, runtime = self._run(events=self._events(material=True))
        second, _ = self._run(events=self._events(material=True), runtime=runtime)
        self.assertTrue(any(event["notify"] for event in first["transitions"]))
        self.assertFalse(any(event["notify"] for event in second["transitions"]))

    def test_unchanged_strategy_returns_compact_no_change(self):
        output, _ = self._run()
        self.assertEqual(output["final_conclusion"], "NO_MATERIAL_PREOPEN_CHANGE")
        self.assertEqual(validate_instance(output, ROOT / "manage-us-stock-strategy" / "schemas" / "preopen-refresh-report.schema.json"), [])

    def test_unverified_upcoming_session_fails_closed(self):
        snapshot = self._premarket()
        snapshot["official_upcoming_session_verified"] = False
        snapshot["session_verification_status"] = "unverified"
        output, _ = self._run(premarket=snapshot)
        self.assertEqual(output["final_conclusion"], "DATA_INCOMPLETE")
        self.assertIn("OFFICIAL_UPCOMING_SESSION_UNVERIFIED", output["global_failures"])

    def test_cli_writes_valid_report_runtime_and_manifest(self):
        outputs_root = ROOT / "workspace" / "outputs"
        base = outputs_root / "test-v2.4-preopen-cli"
        base.mkdir(parents=True, exist_ok=True)
        try:
            paths = {
                "baseline": base / "baseline.json", "report": base / "postmarket.json",
                "postmarket_manifest": base / "postmarket_manifest.json",
                "premarket": base / "premarket.json", "events": base / "events.json",
                "output": base / "preopen_report.json", "runtime": base / "preopen_runtime.json",
                "manifest": base / "run_manifest.json",
            }
            values = {"baseline": self.baseline, "report": self.report, "postmarket_manifest": self.manifest,
                "premarket": self._premarket(), "events": self._events()}
            for key, value in values.items():
                paths[key].write_text(json.dumps(value), encoding="utf-8")
            arguments = ["run_preopen_portfolio_refresh.py", "--baseline", str(paths["baseline"]),
                "--post-market-report", str(paths["report"]), "--premarket", str(paths["premarket"]),
                "--post-market-manifest", str(paths["postmarket_manifest"]),
                "--overnight-events", str(paths["events"]), "--portfolio-state",
                str(ROOT / "stock-strategy-system" / "portfolio_state.json"), "--preopen-policy",
                str(ROOT / "workspace" / "policies" / "preopen_refresh_policy.json"),
                "--runtime-output", str(paths["runtime"]), "--manifest-output", str(paths["manifest"]),
                "--generated-at", "2026-08-12T12:45:00+00:00", "--upcoming-session", "2026-08-12",
                "--latest-completed-session", "2026-08-11", "--strategy-version", "2026-08-05-v4",
                "--post-market-policy-version", "TEST-POLICY", "--output", str(paths["output"])]
            with mock.patch.object(sys, "argv", arguments):
                self.assertEqual(preopen_main(), 0)
            self.assertTrue(all(path.is_file() for path in (paths["output"], paths["runtime"], paths["manifest"])))
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_phase"], "PRE_OPEN")
        finally:
            for path in base.glob("*"):
                if path.is_file():
                    path.unlink(missing_ok=True)
            base.rmdir()


if __name__ == "__main__":
    unittest.main()
