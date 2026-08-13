from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from apply_user_confirmed_broker_snapshot import apply_confirmed
from build_broker_reconciliation_proposal import build_proposal
from evaluate_broker_snapshot_request import evaluate_broker_snapshot_request
from ingest_broker_snapshot import ingest
from render_beginner_portfolio_report import render_beginner_summary
from validate_broker_snapshot_extraction import validate_extraction
from validation_common import canonical_hash, load_json


class V26BrokerBeginnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = load_json(ROOT / "manage-us-stock-strategy/tests/fixtures/v2_5/broker-snapshot-extraction.sample-korean.test-only.json")
        cls.locale = load_json(ROOT / "manage-us-stock-strategy/assets/locales/ko-KR.json")
        cls.broker_policy = load_json(ROOT / "workspace/policies/broker_snapshot_policy.json")
        cls.proposal_schema = ROOT / "manage-us-stock-strategy/schemas/broker-reconciliation-proposal.schema.json"

    def state(self):
        return {"schema_version": "1.3", "strategy_version": "2026-08-05-v4", "state_revision": 1,
                "holdings": {"OLD": 1}, "average_cost_usd": {"OLD": 10.0}, "position_cost_basis_usd": {"OLD": 10.0},
                "available_cash_usd": 0.0, "last_confirmed_broker_snapshot": {"verified": True, "holdings_complete": True,
                "cash_verified": True, "as_of": "2026-08-12"}}

    def test_bs_01_upload_alone_no_mutation(self):
        state = self.state(); before = canonical_hash(state)
        image = ROOT / "workspace/outputs/v2_5_shadow/test-v26-upload.png"
        try:
            image.write_bytes(b"TEST_IMAGE"); ingest([image], bundle_id="T")
            self.assertEqual(before, canonical_hash(state))
        finally: image.unlink(missing_ok=True)

    def test_bs_02_extraction_alone_no_mutation(self):
        state = self.state(); before = canonical_hash(state); build_proposal(self.fixture, state); self.assertEqual(before, canonical_hash(state))

    def test_bs_03_explicit_confirmation_atomic_apply_only(self):
        state = self.state(); proposal = build_proposal(self.fixture, state)
        directory = ROOT / "workspace/outputs/v2_5_shadow"; state_path = directory / "test-v26-state.json"; audit = directory / "test-v26-audit.json"
        try:
            state_path.write_text(json.dumps(state), encoding="utf-8")
            apply_confirmed(state_path=state_path, proposal=proposal, confirmation={"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"], "account_id_masked": "****5546", "evidence_sha256": "a"*64, "as_of": "2026-08-13", "holdings_complete": True, "cash_verified": False, "confirmed_at": "2026-08-13T05:00:00Z"}, proposal_schema=self.proposal_schema, audit_path=audit)
            self.assertEqual(load_json(state_path)["state_revision"], 2)
        finally: state_path.unlink(missing_ok=True); audit.unlink(missing_ok=True)

    def test_bs_04_wrong_revision_rejected(self):
        state = self.state(); proposal = build_proposal(self.fixture, state); proposal["expected_state_revision"] = 99
        directory = ROOT / "workspace/outputs/v2_5_shadow"; path = directory / "test-v26-revision.json"; audit = directory / "test-v26-revision-audit.json"
        try:
            path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaises(ValueError): apply_confirmed(state_path=path, proposal=proposal, confirmation={"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"]}, proposal_schema=self.proposal_schema, audit_path=Path(directory)/"a.json")
        finally: path.unlink(missing_ok=True); audit.unlink(missing_ok=True); (directory/"a.json").unlink(missing_ok=True)

    def test_bs_05_holdings_only_cannot_verify_cash(self):
        value=copy.deepcopy(self.fixture); value["cash_status"]="VERIFIED_AVAILABLE"; value["cash_classification"]="AVAILABLE_SETTLED"; self.assertIn("HOLDINGS_ONLY_CANNOT_VERIFY_CASH", validate_extraction(value))

    def test_bs_06_cash_only_cannot_verify_holdings(self):
        value=copy.deepcopy(self.fixture); value["scope"]="CASH_ONLY"; value["holdings_complete_status"]="VERIFIED"; self.assertIn("CASH_ONLY_CANNOT_VERIFY_HOLDINGS", validate_extraction(value))

    def test_bs_07_position_only_cannot_complete_holdings(self):
        value=copy.deepcopy(self.fixture); value["scope"]="POSITION_ONLY"; value["holdings_complete_status"]="VERIFIED"; self.assertIn("POSITION_ONLY_CANNOT_VERIFY_HOLDINGS_COMPLETE", validate_extraction(value))

    def test_bs_08_broker_price_not_market_evidence(self):
        encoded=json.dumps(build_proposal(self.fixture,self.state())); self.assertNotIn("market_evidence_close", encoded)

    def test_bs_09_quantity_change_no_fill_or_tranche(self):
        proposal=build_proposal(self.fixture,self.state()); self.assertFalse(proposal["inferred_fills"]); self.assertNotIn("tranche", json.dumps(proposal))

    def test_bs_10_margin_unsettled_not_cash(self):
        for kind in ("MARGIN_BUYING_POWER","UNSETTLED_D_PLUS_1","UNSETTLED_D_PLUS_2"):
            value=copy.deepcopy(self.fixture); value.update({"scope":"CASH_ONLY","cash_status":"VERIFIED_AVAILABLE","cash_classification":kind}); self.assertIn("NON_SETTLED_OR_MARGIN_CASH_CANNOT_BECOME_AVAILABLE_CASH",validate_extraction(value))

    def test_bs_11_korean_two_line_one_record_per_ticker(self): self.assertEqual([x["ticker"] for x in self.fixture["positions"]],["SOXL","MVLL","NBIS"])
    def test_bs_12_ranking_date_not_capture_date(self): self.assertIsNone(self.fixture["captured_date"])
    def test_bs_13_pii_not_retained(self): self.assertNotIn("account_number",self.fixture); self.assertNotIn("account_holder_name",self.fixture)

    def request(self, *, state=None, cash="VERIFIED_ZERO", radar=None, runtime=None):
        state=state or {"holdings":{"NBIS":15},"average_cost_usd":{"NBIS":215},"unreconciled_holding_changes":[],"last_confirmed_broker_snapshot":{"verified":True,"holdings_complete":True,"cash_verified":True,"as_of":"2026-08-12","account_id_masked":"****5546"}}
        return evaluate_broker_snapshot_request(portfolio_state=state,cash_gate_result={"cash_status":cash},holding_strategies=[{"ticker":"NBIS","strategy_state":"HOLD","policy_rule_id":"HR"}],holding_risk_result={"state":"DAILY_REVIEW"},tactical_radar_result=radar or {"candidate_dispositions":[]},latest_completed_session="2026-08-12",broker_snapshot_policy=self.broker_policy,unreconciled_user_change_state=[],runtime=runtime)

    def test_sr_01_stale_requests_full_portfolio(self): self.assertEqual(self.request(cash="STALE")[0]["required_scope"],"FULL_PORTFOLIO")
    def test_sr_02_cash_missing_plus_ready_requests_cash_only(self): self.assertEqual(self.request(cash="UNVERIFIED",radar={"candidate_dispositions":[{"ticker":"NOW","opportunity_state":"READY"}]})[0]["required_scope"],"CASH_ONLY")
    def test_sr_03_market_failure_not_broker_request(self): self.assertEqual(self.request()[0]["snapshot_request_status"],"NOT_REQUIRED")
    def test_sr_04_same_request_deduplicated(self):
        first,runtime=self.request(cash="STALE"); second,_=self.request(cash="STALE",runtime=runtime); self.assertTrue(first["notify"]); self.assertFalse(second["notify"])
    def test_sr_05_scope_expansion_renotifies(self):
        first,runtime=self.request(cash="UNVERIFIED",radar={"candidate_dispositions":[{"ticker":"NOW","opportunity_state":"READY"}]}); state={"holdings":{"NBIS":15},"last_confirmed_broker_snapshot":{"verified":True,"holdings_complete":False,"cash_verified":False,"as_of":"2026-08-12"},"unreconciled_holding_changes":[]}; second,_=self.request(state=state,cash="UNVERIFIED",runtime=runtime); self.assertEqual((first["required_scope"],second["required_scope"]),("CASH_ONLY","FULL_PORTFOLIO")); self.assertTrue(second["notify"])

    def render(self, state="HOLD", execution="NOT_APPLICABLE", hard=False, data="VALIDATED"):
        report={"data_status":data,"holding_strategies":[{"ticker":"NBIS","strategy_state":state,"execution_state":execution,"display_action_code":{"HOLD":"HOLD_NO_ACTION","ADD_ON_WATCH":"ADD_WAIT","ADD_REVIEW":"ADD_REVIEW"}.get(state,"HOLD_NO_ACTION"),"primary_reason_code":"TEST","effective_price_status":"PRIMARY_VALIDATED","hard_risk_active":hard}],"tactical_radar_result":{"candidate_dispositions":[]},"snapshot_request":{}}
        return render_beginner_summary(report,self.locale)

    def test_ui_01_hold_korean(self): self.assertEqual(self.render()["display_action"],"그대로 보유")
    def test_ui_02_add_watch_korean(self): self.assertEqual(self.render("ADD_ON_WATCH")["display_action"],"추가매수는 아직 기다리기")
    def test_ui_03_add_pending_uses_price_check(self): self.assertEqual(self.render("ADD_REVIEW","VERIFICATION_PENDING")["display_action_code"],"ADD_PRICE_CHECK")
    def test_ui_04_hard_risk_priority(self): self.assertEqual(self.render("ADD_REVIEW","VERIFICATION_PENDING",True)["display_action_code"],"RISK_REVIEW")
    def test_ui_05_data_incomplete_not_alert_none(self): self.assertNotEqual(render_beginner_summary({"data_status":"DATA_INCOMPLETE","holding_strategies":[],"tactical_radar_result":{"candidate_dispositions":[]},"snapshot_request":{}},self.locale)["display_action"],self.locale["messages"]["alert_none"])
    def test_ui_06_core_codes_not_korean_sentences(self): self.assertEqual(self.render()["display_action_code"],"HOLD_NO_ACTION")
    def test_ui_07_no_order_notice(self): self.assertIn("주문",self.render()["no_order_notice"])


if __name__ == "__main__": unittest.main()
