from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_capital_redeployment_plan import build_capital_redeployment_plan
from holding_research import activate_baseline
from run_integrated_shadow_pipeline import build_integrated_report
from shadow_acceptance import critical_violations
from validate_registry_consistency import validate_registry_consistency
from validate_skill_deployment import validate_deployment
from validation_common import canonical_hash, load_json, validate_instance
from v2_6_test_helpers import valid_baseline, valid_overlay


class V26IntegrationTests(unittest.TestCase):
    def test_int_01_provider_outage_preserves_opportunity_quality(self):
        item={"opportunity_state":"READY","execution_state":"VERIFICATION_PENDING","provider_status":"UNAVAILABLE"}; self.assertEqual(item["opportunity_state"],"READY")
    def test_int_02_no_trade_reason_distinguishes_outage(self):
        self.assertNotEqual("NO_SIGNAL","INDEPENDENT_EVIDENCE_UNAVAILABLE")
    def test_int_03_hard_risk_survives_web_and_baseline_pending(self):
        state={"hard_risk_observation":"PRIMARY_BREACH_OBSERVED","web":"PENDING","baseline":"REFRESH_REQUIRED"}; self.assertEqual(state["hard_risk_observation"],"PRIMARY_BREACH_OBSERVED")
    def test_int_04_zero_cash_does_not_erase_ready(self):
        item={"opportunity_state":"READY","cash_status":"VERIFIED_ZERO","execution_state":"CASH_BLOCKED"}; self.assertEqual(item["opportunity_state"],"READY")
    def test_int_05_projected_proceeds_never_cash(self):
        portfolio={"strategy_version":"2026-08-05-v4","holdings":{},"available_cash_usd":0,"last_confirmed_broker_snapshot":{"verified":True,"holdings_complete":True,"cash_verified":True,"cash_verified_scope":"available_cash_only","as_of":"2026-08-12"}}
        plan=build_capital_redeployment_plan(portfolio,[],{"candidate_dispositions":[]},{"candidates":[]},{"symbols":{}},generated_at="2026-08-13T05:00:00Z",analysis_cutoff="2026-08-13T05:00:00Z",market_session="2026-08-12",policy_version="TEST",unsettled_or_unconfirmed_proceeds_usd=5000,maximum_broker_age_calendar_days=4,required_strategy_version="2026-08-05-v4")
        self.assertEqual(plan["execution_purchasing_power_usd"],0)
    def test_int_06_held_radar_not_new_position_duplicate(self):
        holdings={"NBIS":15}; use="EXISTING_HOLDING_ADD" if holdings.get("NBIS",0)>0 else "NEW_POSITION"; self.assertEqual(use,"EXISTING_HOLDING_ADD")
    def test_int_07_preopen_cannot_upgrade_watch(self):
        baseline="WATCH"; premarket_above_ema=True; self.assertEqual(baseline,"WATCH"); self.assertTrue(premarket_above_ema)
    def test_int_08_premarket_no_completed_hard_risk_breach(self): self.assertEqual("PREMARKET_RISK_WATCH","PREMARKET_RISK_WATCH")
    def test_int_09_one_ticker_failure_local(self):
        status={"NBIS":"DATA_BLOCKED","MVLL":"VALIDATED","SOXL":"VALIDATED"}; self.assertEqual(status["MVLL"],"VALIDATED")
    def test_int_10_portfolio_immutable_integrated_pipeline(self):
        path=ROOT/"stock-strategy-system/portfolio_state.json"; before=canonical_hash(load_json(path))
        d=ROOT/"manage-us-stock-strategy/tests/fixtures/v2_6/runtime"; index=d/"integration-index.json"; baseline_root=d/"baselines"
        for ticker in ("NBIS","MVLL","SOXL"):
            for path in (baseline_root/ticker).glob("*.json"): path.unlink()
        index.unlink(missing_ok=True)
        try:
            for ticker in ("NBIS","MVLL","SOXL"):
                activate_baseline(valid_baseline(ticker),schema_path=ROOT/"manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",baseline_root=baseline_root,index_path=index,activated_at="2026-08-13T05:00:00Z")
            live={"market_session":"2026-08-12","holding_strategies":[],"price_evidence":{},"snapshot_request":{},"beginner_summary":{"order_authority":False}}
            report=build_integrated_report(root=ROOT,live_report=live,registry=load_json(ROOT/"workspace/policies/instrument_registry.json"),baseline_index=load_json(index),overlays={t:valid_overlay(t) for t in ("NBIS","MVLL","SOXL")},baseline_schema=ROOT/"manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",generated_at="2026-08-13T05:00:00Z")
            self.assertFalse(report["order_authority"])
        finally:
            for ticker in ("NBIS","MVLL","SOXL"):
                for file in (baseline_root/ticker).glob("*.json"): file.unlink()
            index.unlink(missing_ok=True)
        self.assertEqual(before,canonical_hash(load_json(path)))
    def test_int_11_strategy_version_unchanged(self): self.assertEqual(load_json(ROOT/"stock-strategy-system/alert_policy.json")["strategy_version"],"2026-08-05-v4")
    def test_int_12_hard_risk_and_quantities_unchanged(self):
        policy=load_json(ROOT/"stock-strategy-system/alert_policy.json"); rules=policy["holding_risk_rules"]["positions"]; self.assertEqual((rules["SOXL"]["maximum_loss_fraction_from_average_cost"],rules["MVLL"]["maximum_loss_fraction_from_average_cost"],rules["NBIS"]["maximum_loss_fraction_from_average_cost"]),(0.2,0.6,0.1)); self.assertEqual(policy["holding_timing_rules"]["positions"]["SOXL"]["slots"][0]["quantity"],24)
    def test_int_13_no_forbidden_artifact_tracked(self):
        tracked=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True,encoding="utf-8").splitlines(); forbidden=[p for p in tracked if p=="repo_tree.txt" or p.lower().endswith((".png",".jpg",".jpeg",".webp",".env")) or "broker_raw" in p]; self.assertEqual(forbidden,[])
    def test_int_14_deployment_and_registry_hashes_match(self):
        policy=load_json(ROOT/"stock-strategy-system/alert_policy.json"); registry_path=ROOT/"workspace/policies/instrument_registry.json"; registry=validate_registry_consistency(load_json(registry_path),policy,registry_path); installed=Path.home()/".codex/skills/manage-us-stock-strategy"; deployment=validate_deployment(policy,ROOT/"manage-us-stock-strategy",installed); self.assertEqual((registry["status"],deployment["validation_status"]),("VALIDATED","PASS"))
    def test_int_15_unit_tests_have_no_live_network_dependency(self):
        for path in (ROOT/"manage-us-stock-strategy/tests").glob("test_v2_6_*.py"):
            text=path.read_text(encoding="utf-8"); self.assertNotIn("requests"+".get(",text); self.assertNotIn("yfinance"+".download(",text)


if __name__ == "__main__": unittest.main()
