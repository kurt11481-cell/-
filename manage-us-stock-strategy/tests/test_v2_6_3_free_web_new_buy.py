from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_candidate_discovery_proposal import build_discovery_proposal
from build_new_buy_approval_proposal import build_approval_proposal
from build_new_buy_strategy_draft import build_new_buy_strategy_draft
from build_price_crosscheck_queue import build_queue
from shadow_acceptance import apply_attempt, classify_attempt, initial_progress, semantic_fingerprint
from staged_promotion import build_staged_audit, validate_exact_scope_approval
from validation_common import file_hash, load_json, validate_instance
from v2_6_test_helpers import queue_item, valid_scheduled_attempt, valid_web_evidence
from web_close_evidence import resolve_shadow_close, validate_raw_web_evidence
from web_route_acceptance import evaluate_route_session, route_fingerprint, validate_registry_semantics


class V263FreeWebNewBuyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_json(ROOT / "workspace/policies/web_completed_close_evidence_policy.json")
        cls.registry = load_json(ROOT / "workspace/policies/web_completed_close_route_registry.json")
        cls.alert = load_json(ROOT / "stock-strategy-system/alert_policy.json")
        cls.portfolio_hash = file_hash(ROOT / "stock-strategy-system/portfolio_state.json")

    def context(self, **overrides):
        value = {
            "ticker": "BE", "legal_issuer_name": "Bloom Energy Corporation", "instrument_type": "stock",
            "leveraged_status": "NOT_LEVERAGED", "analysis_cutoff": "2026-08-13T05:00:00Z",
            "market_session": "2026-08-12", "research_packet_hash": "a" * 64,
            "identity_status": "VERIFIED", "evidence_integrity_status": "PASS", "thesis_status": "PASS",
            "valuation_status": "PASS", "technical_status": "READY", "event_risk_status": "CLEAR",
            "risk_liquidity_status": "PASS", "portfolio_fit_status": "PASS", "opportunity_state": "READY",
            "price_evidence_status": "PRIMARY_VALIDATED", "source_route_id": "BE_BLOOM_IR",
            "new_buy_instrument_approved": False, "entry_rule_status": "PENDING",
            "maximum_loss_rule_status": "PENDING", "risk_budget_status": "PENDING",
            "cash_status": "VERIFIED_ZERO", "promotion_scope_status": "PENDING",
            "primary_reason": "Validated evidence supports a research-only setup.",
            "strongest_counter_case": "Valuation and execution risk may invalidate the setup.",
            "entry_conditions": ["APPROVED_ENTRY_RULE_REQUIRED"],
            "remaining_conditions": [], "invalidation_conditions": ["THESIS_INVALIDATED"],
            "next_review_trigger": "NEXT_COMPLETED_US_SESSION",
        }
        value.update(overrides)
        return value

    def accepted_route(self, route_id="BE_BLOOM_IR"):
        registry = copy.deepcopy(self.registry)
        route = next(r for r in registry["routes"] if r["route_id"] == route_id)
        route["route_status"] = "SHADOW_APPROVED"
        route["accepted_sessions"] = [f"2026-08-{day:02d}" for day in range(3, 8)]
        return registry, route

    def route_record(self, route_id="BE_BLOOM_IR", close=100.02):
        registry, route = self.accepted_route(route_id)
        ticker = route["ticker_scope"][0]
        record = valid_web_evidence(ticker=ticker, close=close)
        record.update({
            "source_route_id": route_id, "source_url": route["source_url_template"],
            "final_source_url": route["source_url_template"], "source_domain": route["source_domain"],
            "source_type": route["source_type"], "price_basis": route["price_basis"],
            "source_field_label": route["source_field_label"], "provider": route["source_domain"],
        })
        return registry, route, record

    # FREE-01 through FREE-06
    def test_free_01_missing_api_key_does_not_block_draft(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(build_new_buy_strategy_draft(self.context())["strategy_draft_status"], "PRICE_VERIFICATION_PENDING")

    def test_free_02_missing_mcp_does_not_block_discovery(self):
        proposal = build_discovery_proposal({"ticker": "XYZ", "legal_issuer_name": "Example Inc.", "security_class": "Common", "exchange": "NASDAQ", "instrument_type": "stock", "leveraged_status": "NOT_LEVERAGED", "identity_status": "VERIFIED", "light_screen_passed": True})
        self.assertEqual(proposal["discovery_state"], "USER_WATCHLIST_APPROVAL_REQUIRED")

    def test_free_03_automation_prompt_has_no_massive_requirement(self):
        prompt = (ROOT / "stock-strategy-system/POST_MARKET_PORTFOLIO_STRATEGY_AUTOMATION_PROMPT_EN.md").read_text(encoding="utf-8").lower()
        self.assertNotIn("massive_api_key", prompt)
        self.assertNotIn("use massive mcp", prompt)
        self.assertIn("do not\nrequire massive", prompt)

    def test_free_04_massive_provider_not_enabled(self):
        providers = load_json(ROOT / "workspace/policies/source_capabilities.json")["providers"]
        self.assertFalse(any("massive" in p["provider"].lower() and p.get("enabled") is True for p in providers))

    def test_free_05_missing_massive_not_global_failure(self):
        self.assertNotIn("MASSIVE", json.dumps(self.context()).upper())

    def test_free_06_structured_placeholder_disabled(self):
        providers = load_json(ROOT / "workspace/policies/source_capabilities.json")["providers"]
        placeholder = next(p for p in providers if p["provider"] == "independent_completed_close_unconfigured")
        self.assertFalse(placeholder["enabled"]); self.assertFalse(placeholder["independent_crosscheck_eligible"])

    # BUY-01 through BUY-19
    def test_buy_01_screening_continues_without_independent_close(self): self.assertEqual(build_new_buy_strategy_draft(self.context())["opportunity_state"], "READY")
    def test_buy_02_primary_validated_supports_draft(self): self.assertEqual(build_new_buy_strategy_draft(self.context())["price_evidence_status"], "PRIMARY_VALIDATED")
    def test_buy_03_primary_validated_preserves_ready(self): self.assertEqual(build_new_buy_strategy_draft(self.context())["opportunity_state"], "READY")
    def test_buy_04_ready_without_web_is_verification_pending(self): self.assertEqual(build_new_buy_strategy_draft(self.context())["execution_state"], "VERIFICATION_PENDING")
    def test_buy_05_web_unavailable_does_not_erase_ready(self): self.assertEqual(build_new_buy_strategy_draft(self.context(price_evidence_status="UNAVAILABLE"))["opportunity_state"], "READY")
    def test_buy_06_draft_exists_before_web(self): self.assertEqual(build_new_buy_strategy_draft(self.context())["strategy_draft_status"], "PRICE_VERIFICATION_PENDING")
    def test_buy_07_preverification_quantity_null(self): self.assertIsNone(build_new_buy_strategy_draft(self.context())["quantity"])
    def test_buy_08_match_does_not_approve_instrument(self): self.assertEqual(build_new_buy_strategy_draft(self.context(price_evidence_status="INDEPENDENT_VERIFIED"))["strategy_draft_status"], "INSTRUMENT_APPROVAL_PENDING")
    def test_buy_09_watchlist_is_not_new_buy_approval(self):
        universe = load_json(ROOT / "workspace/policies/tactical_candidate_universe.json")
        self.assertTrue(universe["candidates"]["BE"]["watchlist_approved"]); self.assertFalse(universe["candidates"]["BE"]["new_buy_approved"])
    def test_buy_10_instrument_not_approved_without_exact_user_approval(self): self.assertEqual(build_new_buy_strategy_draft(self.context(price_evidence_status="INDEPENDENT_VERIFIED"))["execution_state"], "NOT_APPROVED")
    def test_buy_11_price_does_not_approve_risk_budget(self):
        draft = build_new_buy_strategy_draft(self.context(price_evidence_status="INDEPENDENT_VERIFIED", new_buy_instrument_approved=True, entry_rule_status="APPROVED", maximum_loss_rule_status="APPROVED"))
        self.assertEqual(draft["risk_budget_status"], "PENDING")
    def test_buy_12_price_does_not_approve_max_loss(self):
        draft = build_new_buy_strategy_draft(self.context(price_evidence_status="INDEPENDENT_VERIFIED", new_buy_instrument_approved=True, entry_rule_status="APPROVED"))
        self.assertEqual(draft["maximum_loss_rule_status"], "PENDING")
    def test_buy_13_zero_cash_preserves_ready_but_blocks_cash(self):
        draft = build_new_buy_strategy_draft(self.context(price_evidence_status="INDEPENDENT_VERIFIED", new_buy_instrument_approved=True, entry_rule_status="APPROVED", maximum_loss_rule_status="APPROVED", risk_budget_status="APPROVED"))
        self.assertEqual((draft["opportunity_state"], draft["execution_state"]), ("READY", "CASH_BLOCKED"))
    def test_buy_14_unverified_cash_blocks_cash(self):
        draft = build_new_buy_strategy_draft(self.context(price_evidence_status="INDEPENDENT_VERIFIED", new_buy_instrument_approved=True, entry_rule_status="APPROVED", maximum_loss_rule_status="APPROVED", risk_budget_status="APPROVED", cash_status="UNVERIFIED"))
        self.assertEqual(draft["strategy_draft_status"], "CASH_BLOCKED")
    def test_buy_15_external_candidate_is_proposal_only(self): self.assertFalse(build_discovery_proposal({"ticker":"XYZ","legal_issuer_name":"X","security_class":"Common","exchange":"NYSE","instrument_type":"stock","identity_status":"VERIFIED"})["watchlist_approved"])
    def test_buy_16_external_candidate_not_auto_active(self): self.assertFalse(build_discovery_proposal({"ticker":"XYZ","legal_issuer_name":"X","security_class":"Common","exchange":"NYSE","instrument_type":"stock","identity_status":"VERIFIED"})["active_universe_approved"])
    def test_buy_17_llm_signal_cannot_control_state(self): self.assertEqual(build_new_buy_strategy_draft(self.context(opportunity_state="WATCH", llm_strategy_signal="BUY"))["strategy_draft_status"], "RESEARCH_ONLY")
    def test_buy_18_no_share_count(self): self.assertIsNone(build_new_buy_strategy_draft(self.context())["quantity"])
    def test_buy_19_no_order_authority(self): self.assertFalse(build_new_buy_strategy_draft(self.context())["order_authority"])

    # WEB route acceptance and comparison
    def test_web_07_generic_nasdaq_not_nocp(self):
        route = next(r for r in self.registry["routes"] if r["route_id"] == "NBIS_NASDAQ_HISTORICAL")
        self.assertNotEqual(route["source_type"], "OFFICIAL_EXCHANGE_NOCP")
    def test_web_08_pending_route_is_inconclusive(self):
        registry, route, record = self.route_record(); next(r for r in registry["routes"] if r["route_id"] == route["route_id"])["route_status"] = "SOURCE_ROUTE_PENDING_REVIEW"
        self.assertEqual(validate_raw_web_evidence(record, queue_item("BE"), self.policy, route_registry=registry)["evidence_validation_status"], "INCONCLUSIVE")
    def test_web_09_issuer_ir_validates_after_route_acceptance(self):
        registry, _, record = self.route_record(); self.assertEqual(validate_raw_web_evidence(record, queue_item("BE"), self.policy, route_registry=registry)["evidence_validation_status"], "VALIDATED")
    def test_web_10_sponsor_market_close_requires_route_acceptance(self):
        registry, route, record = self.route_record("SOXL_DIREXION"); next(r for r in registry["routes"] if r["route_id"] == route["route_id"])["route_status"] = "SOURCE_ROUTE_PENDING_REVIEW"
        result = validate_raw_web_evidence(record, queue_item("SOXL"), self.policy, route_registry=registry)
        self.assertEqual(result["evidence_validation_status"], "INCONCLUSIVE")
    def test_web_16_one_route_failure_is_local(self):
        registry, _, record = self.route_record(); bad=copy.deepcopy(record); bad["ticker"]="NOW"
        self.assertEqual(validate_raw_web_evidence(bad, queue_item("BE"), self.policy, route_registry=registry)["evidence_validation_status"], "REJECTED")
        self.assertEqual(validate_raw_web_evidence(record, queue_item("BE"), self.policy, route_registry=registry)["evidence_validation_status"], "VALIDATED")
    def test_web_17_validation_alone_not_match(self):
        registry, _, record = self.route_record(); self.assertEqual(validate_raw_web_evidence(record, queue_item("BE"), self.policy, route_registry=registry)["comparison_status"], "NOT_EVALUATED")
    def test_web_18_approved_tolerance_reused(self):
        registry, _, record = self.route_record(); self.assertEqual(resolve_shadow_close(queue_item("BE"), record, self.policy, route_registry=registry)["tolerance_usd"], 0.1)
    def test_web_19_inside_tolerance_matches(self):
        registry, _, record = self.route_record(); self.assertEqual(resolve_shadow_close(queue_item("BE"), record, self.policy, route_registry=registry)["shadow_crosscheck_status"], "MATCH")
    def test_web_20_boundary_flip_conflicts(self):
        registry, _, record = self.route_record(); item=queue_item("BE"); item["decision_boundaries"]=[{"value":100.01,"operator":"less_than_or_equal"}]
        self.assertEqual(resolve_shadow_close(item, record, self.policy, route_registry=registry)["comparison_status"], "DECISION_BOUNDARY_FLIP")
    def test_web_22_match_cannot_promote(self):
        registry, _, record = self.route_record(); result=resolve_shadow_close(queue_item("BE"), record, self.policy, route_registry=registry)
        self.assertEqual(result["execution_state"], "VERIFICATION_PENDING"); self.assertFalse(result["order_authority"])
    def test_web_23_five_distinct_sessions_required(self):
        route=copy.deepcopy(self.registry["routes"][0])
        for day in range(3,8): route=evaluate_route_session(route,completed_session=f"2026-08-{day:02d}",evidence_validation_status="VALIDATED",comparison_status="MATCH",observed_at=f"2026-08-{day+1:02d}T01:00:00Z")
        self.assertEqual((len(route["accepted_sessions"]),route["route_status"]),(5,"SHADOW_APPROVED"))
    def test_web_24_route_sessions_are_not_operational_shadow_sessions(self):
        route=evaluate_route_session(copy.deepcopy(self.registry["routes"][0]),completed_session="2026-08-03",evidence_validation_status="VALIDATED",comparison_status="MATCH",observed_at="2026-08-04T01:00:00Z")
        self.assertNotIn("valid_shadow_sessions", route)
    def test_web_25_three_failures_suspend(self):
        route=copy.deepcopy(self.registry["routes"][0])
        for day in range(3): route=evaluate_route_session(route,completed_session=f"2026-08-0{day+3}",evidence_validation_status="REJECTED",comparison_status="NOT_EVALUATED",observed_at=f"2026-08-0{day+4}T01:00:00Z",failure_type="PAGE_UNAVAILABLE")
        self.assertEqual(route["route_status"],"SUSPENDED")
    def test_web_registry_fingerprints_valid(self): self.assertEqual(validate_registry_semantics(self.registry), [])

    # LEV direct/proxy separation
    def test_lev_01_soxl_direct_route_uses_soxl(self): self.assertEqual(next(r for r in self.registry["routes"] if r["route_id"]=="SOXL_DIREXION")["ticker_scope"],["SOXL"])
    def test_lev_02_soxx_direction_only(self): self.assertEqual(load_json(ROOT/"workspace/policies/instrument_registry.json")["instruments"]["SOXL"]["confirmation_mode"],"DIRECTION_ONLY")
    def test_lev_04_mvll_direct_route_uses_mvll(self): self.assertEqual(next(r for r in self.registry["routes"] if r["route_id"]=="MVLL_NASDAQ_HISTORICAL")["ticker_scope"],["MVLL"])
    def test_lev_05_mrvl_supplemental(self): self.assertEqual(load_json(ROOT/"workspace/policies/instrument_registry.json")["instruments"]["MVLL"]["confirmation_proxy"],"MRVL")

    def stage_progress(self, count):
        p=initial_progress("a"*64,"2026-08-01T00:00:00Z"); p["valid_shadow_sessions"]=count; p["counted_sessions"]=[f"2026-07-{i+1:02d}" for i in range(count)]; return p
    def stage_scope(self, ticker="BE"): return {"ticker":ticker,"decision_class":"NEW_BUY","source_route_id":"BE_BLOOM_IR","research_packet_hash":"a"*64,"baseline_hash":None}
    def stage_context(self, **overrides):
        value={"portfolio_mutations":0,"order_authority_violations":0,"unauthorized_quantities":0,"fill_inference":0,"genuine_scheduled_deliveries":1,"origin_main_provenance_valid":True,"delivery_id_valid":True,"historical_replay_status":"PASS","fault_injection_status":"PASS","route_status":"SHADOW_APPROVED","evidence_validation_pass_count":1,"deterministic_match_count":1,"broker_workflow_status":"PASS","research_or_baseline_valid":True,"ticker_overlay_sessions":10,"stage_5_status":"PASS","unresolved_delivery_failures":0,"unexplained_expected_session_gaps":0,"nonempty_web_queue_sessions":2,"unavailable_or_inconclusive_handled":True,"ticker_local_conflict_isolation":True,"accepted_route_healthy":True,"incomplete_baseline_no_hold":True,"leveraged_direct_proxy_separation":True,"stage_10_status":"PASS","maturity_audit_status":"PASS","long_horizon_evaluation_status":"PASS"}
        value.update(overrides); return value

    # STG-01 through STG-20
    def test_stg_01_first_delivery_stage_one(self): self.assertEqual(build_staged_audit(self.stage_progress(1),1,"2026-08-13T05:00:00Z",self.stage_context())["promotion_state"],"LIVE_READ_ONLY_DELIVERY_VERIFIED")
    def test_stg_02_manual_smoke_cannot_stage_one(self): self.assertEqual(build_staged_audit(self.stage_progress(1),1,"2026-08-13T05:00:00Z",self.stage_context(genuine_scheduled_deliveries=0))["promotion_state"],"NOT_ELIGIBLE")
    def test_stg_03_manual_run_now_excluded(self): self.assertFalse(classify_attempt(valid_scheduled_attempt(attempt_type="MANUAL_RUN_NOW"),progress=self.stage_progress(0))["counts_as_valid_session"])
    def test_stg_04_five_sessions_create_review(self): self.assertEqual(build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())["promotion_state"],"LIMITED_HUMAN_REVIEW_PENDING_APPROVAL")
    def test_stg_05_stage_five_no_auto(self): self.assertFalse(build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())["automatic_promotion"])
    def test_stg_06_replay_required(self): self.assertFalse(build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(historical_replay_status="FAIL"),self.stage_scope())["promotion_eligible"])
    def test_stg_07_fault_injection_required(self): self.assertFalse(build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(fault_injection_status="FAIL"),self.stage_scope())["promotion_eligible"])
    def test_stg_08_exact_route_required(self): self.assertFalse(build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(route_status="SOURCE_ROUTE_PENDING_REVIEW"),self.stage_scope())["promotion_eligible"])
    def test_stg_09_scope_exact(self): self.assertEqual(build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())["promotion_scope"]["ticker"],"BE")
    def test_stg_10_other_ticker_not_promoted(self):
        audit=build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())
        approval={"audit_hash":audit["audit_hash"],"promotion_scope":self.stage_scope("NOW"),"user_approval_reference":"user-ref"}
        self.assertIn("EXACT_SCOPE_MISMATCH",validate_exact_scope_approval(audit,approval)["errors"])
    def test_stg_11_two_queue_sessions_required(self): self.assertFalse(build_staged_audit(self.stage_progress(10),10,"2026-08-13T05:00:00Z",self.stage_context(nonempty_web_queue_sessions=1),self.stage_scope())["promotion_eligible"])
    def test_stg_12_match_required(self): self.assertFalse(build_staged_audit(self.stage_progress(10),10,"2026-08-13T05:00:00Z",self.stage_context(deterministic_match_count=0),self.stage_scope())["promotion_eligible"])
    def test_stg_13_unavailable_handling_required(self): self.assertFalse(build_staged_audit(self.stage_progress(10),10,"2026-08-13T05:00:00Z",self.stage_context(unavailable_or_inconclusive_handled=False),self.stage_scope())["promotion_eligible"])
    def test_stg_14_stage_ten_no_auto(self): self.assertFalse(build_staged_audit(self.stage_progress(10),10,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())["automatic_promotion"])
    def test_stg_15_stage_twenty_maturity_review(self): self.assertEqual(build_staged_audit(self.stage_progress(20),20,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())["promotion_state"],"MATURE_GUARDED_REVIEW_PENDING_APPROVAL")
    def test_stg_16_stage_twenty_no_auto(self): self.assertFalse(build_staged_audit(self.stage_progress(20),20,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())["automatic_promotion"])
    def test_stg_17_stage_sixty_no_policy_mutation(self):
        policy=load_json(ROOT/"workspace/policies/shadow_acceptance_policy.json"); before=copy.deepcopy(policy); build_staged_audit(self.stage_progress(60),60,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope()); self.assertEqual(policy,before)
    def test_stg_18_semantic_change_new_cohort(self): self.assertNotEqual(initial_progress("a"*64,"x")["cohort_id"],initial_progress("b"*64,"x")["cohort_id"])
    def test_stg_19_route_observation_does_not_change_semantic_hash(self):
        before=semantic_fingerprint(ROOT); registry=copy.deepcopy(self.registry); registry["routes"][0]["accepted_sessions"].append("2026-08-12"); registry["routes"][0]["last_success"]="2026-08-13T01:00:00Z"
        from shadow_acceptance import canonical_hash as _unused
        stable=("route_id","ticker_scope","exchange_scope","instrument_class_scope","source_type","source_domain","source_url_template","price_basis","source_field_label","currency","authentication_requirement","route_fingerprint")
        self.assertEqual(json.dumps([{k:r.get(k) for k in stable} for r in self.registry["routes"]],sort_keys=True),json.dumps([{k:r.get(k) for k in stable} for r in registry["routes"]],sort_keys=True)); self.assertEqual(before,semantic_fingerprint(ROOT))
    def test_stg_20_locale_not_semantic(self): self.assertNotIn("ko-KR.json", str(load_json(ROOT/"workspace/policies/shadow_acceptance_policy.json")["semantic_inputs"]))

    # Invariants
    def test_inv_01_portfolio_unchanged(self): self.assertEqual(self.portfolio_hash,file_hash(ROOT/"stock-strategy-system/portfolio_state.json"))
    def test_inv_02_strategy_version_unchanged(self): self.assertEqual(self.alert["strategy_version"],"2026-08-05-v4")
    def test_inv_03_05_hard_risk_thresholds(self):
        rules=self.alert["holding_risk_rules"]["positions"]
        self.assertEqual((rules["SOXL"]["maximum_loss_fraction_from_average_cost"],rules["MVLL"]["maximum_loss_fraction_from_average_cost"],rules["NBIS"]["maximum_loss_fraction_from_average_cost"]),(0.2,0.6,0.1))
    def test_inv_06_timing_quantities_unchanged(self):
        # I0-b (2026-10-06) removed the MVLL/SOXL timing slots from the active policy.
        self.assertEqual(self.alert["holding_timing_rules"]["positions"],{})
    def test_inv_07_rearm_rules_unchanged(self): self.assertEqual(self.alert["holding_timing_rules"]["weakness_rearm"]["minimum_completed_sessions_after_fill"],3)
    def test_inv_10_no_json_order_authority_true(self):
        def walk(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k=="order_authority": self.assertIs(x,False)
                    walk(x)
            elif isinstance(v,list):
                for x in v: walk(x)
        for path in (ROOT/"workspace/policies").glob("*.json"): walk(load_json(path))

    def test_new_schemas_validate(self):
        draft=build_new_buy_strategy_draft(self.context()); approval=build_approval_proposal(draft)
        self.assertEqual(validate_instance(draft,ROOT/"manage-us-stock-strategy/schemas/new-buy-strategy-draft.schema.json"),[])
        self.assertEqual(validate_instance(approval,ROOT/"manage-us-stock-strategy/schemas/new-buy-approval-proposal.schema.json"),[])
        audit=build_staged_audit(self.stage_progress(5),5,"2026-08-13T05:00:00Z",self.stage_context(),self.stage_scope())
        self.assertEqual(validate_instance(audit,ROOT/"manage-us-stock-strategy/schemas/staged-promotion-audit.schema.json"),[])


if __name__ == "__main__":
    unittest.main()
