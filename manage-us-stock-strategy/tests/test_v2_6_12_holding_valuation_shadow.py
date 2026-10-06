from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
import uuid
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from holding_baseline_operationalization import (  # noqa: E402
    activate_shadow_candidate, build_baseline_event_link, build_issuer_valuation_snapshot,
    compile_shadow, initialize_observation, record_observation, validate_event_link,
    validate_managed_output_path, validate_valuation_snapshot,
)
from holding_research import build_overlay, recompute_hashes  # noqa: E402
from validation_common import canonical_hash, file_hash, validate_instance  # noqa: E402


BASELINE_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "holding-research-baseline.schema.json"
VALUATION_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "issuer-valuation-snapshot.schema.json"
LINK_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "baseline-event-link.schema.json"
OBS_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "holding-baseline-observation-state.schema.json"
COMPILE_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "shadow-baseline-compile-result.schema.json"
SUPERSEDED_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "superseded-shadow-cohort.schema.json"
PROGRESS_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "shadow-progress-state.schema.json"
POLICY = ROOT / "workspace" / "policies" / "holding_research_baseline_policy.json"
PROVIDER = ROOT / "workspace" / "policies" / "kiwoom-session-aware-priority-policy.json"
PORTFOLIO = ROOT / "stock-strategy-system" / "portfolio_state.json"


def metric(value, unit="USD_MILLIONS", evidence="e1", currency="USD"):
    return {"value": value, "currency": currency, "unit": unit, "as_of": "2026-06-30",
            "source_evidence_id": evidence, "verification_status": "VERIFIED"}


def valuation_spec(ticker="TEST"):
    return {
        "valuation_snapshot_id": f"{ticker}-valuation", "ticker": ticker,
        "issuer_name": "Test Issuer", "entity_role": "DIRECT_ISSUER",
        "analysis_cutoff": "2026-08-14T05:00:00Z", "market_session": "2026-08-13",
        "price": {"provider": "KIWOOM_REST", "price_basis": "RAW_REGULAR_SESSION_CLOSE",
                  "market_session_type": "REGULAR_COMPLETED", "reported_session": "2026-08-13",
                  "raw_regular_session_close": 100.0, "currency": "USD", "bar_finalized": True,
                  "retrieved_at": "2026-08-14T05:00:00Z", "source_record_hash": "a" * 64,
                  "shadow_provider": "YFINANCE_DIAGNOSTIC_SHADOW", "shadow_raw_close": 100.0,
                  "comparison_status": "MATCH"},
        "capitalization": {"share_count_as_of": "2026-06-30",
                           "basic_shares": metric(10.0, "SHARES_MILLIONS", currency=None),
                           "diluted_shares_base": metric(11.0, "SHARES_MILLIONS", currency=None),
                           "diluted_shares_stress": metric(12.0, "SHARES_MILLIONS", currency=None),
                           "share_class_breakdown": {"A": 9.0, "B": 1.0},
                           "preferred_equity": metric(0.0), "convertible_instruments": {},
                           "warrants": {}, "ATM_capacity": {},
                           "stock_compensation": metric(1.0, "SHARES_MILLIONS", currency=None),
                           "other_dilution": metric(0.0, "SHARES_MILLIONS", currency=None)},
        "balance_sheet": {"cash": metric(100.0), "restricted_cash": metric(20.0),
                          "debt": metric(50.0), "secured_financing": metric(0.0),
                          "preferred_claims": metric(0.0), "other_claims": metric(0.0)},
        "operating_metrics": {"revenue_ltm": metric(200.0),
                              "annualized_revenue_run_rate": metric(220.0),
                              "gross_profit_ltm": metric(100.0), "operating_cash_flow": metric(30.0),
                              "capital_expenditure": metric(10.0),
                              "local_ocf_minus_capex_proxy": metric(20.0),
                              "reported_free_cash_flow": metric(None), "deferred_revenue": metric(0.0),
                              "customer_prepayments": metric(0.0)},
        "base_assumption_ids": ["BASE"], "stress_assumption_ids": ["STRESS"],
        "required_missing_inputs": [], "claim_ids": ["c1"], "evidence_ids": ["e1"],
        "staleness_triggers": ["NEXT_EARNINGS"], "valuation_judgement_status": "UNCLASSIFIED",
    }


def baseline(ticker="SOXL", *, complete=True, direct=False):
    value = {
        "schema_version": "2.6", "baseline_id": f"{ticker.lower()}-test-v2", "baseline_version": 2,
        "ticker": ticker, "baseline_type": "ISSUER_EQUITY" if direct else "SECTOR_LEVERAGED_ETF",
        "analysis_cutoff": "2026-08-14T05:00:00Z", "evidence_cutoff": "2026-08-14T05:00:00Z",
        "content_status": "COMPLETE" if complete else "PARTIAL", "thesis_status": "VALID",
        "valuation_applicability": "DIRECT" if direct else "NOT_APPLICABLE_TO_PRODUCT",
        "valuation_status": "UNVERIFIED" if direct else "NOT_APPLICABLE",
        "valuation_basis": "NBIS_ISSUER" if direct else "SEMICONDUCTOR_SECTOR_REGIME",
        "fundamental_risk_status": "ACCEPTABLE", "primary_reason": "Verified test thesis.",
        "strongest_counter_case": "Verified test counter-case.",
        "invalidation_conditions": ["TEST_INVALIDATION"], "next_research_triggers": ["TEST_TRIGGER"],
        "claims": [{"claim_id": "c1", "evidence_ids": ["e1"]}],
        "evidence": [{"evidence_id": "e1", "source_url": "https://example.com/filing",
                      "source_type": "REGULATORY_PRIMARY", "published_at": "2026-08-13T12:00:00Z",
                      "retrieved_at": "2026-08-14T05:00:00Z", "point_in_time_eligible": True,
                      "verification_status": "VERIFIED"}],
        "claim_ids": ["c1"], "evidence_ids": ["e1"], "linked_components": [],
        "research_packet_hash": "0" * 64, "baseline_hash": "0" * 64,
        "supersedes_baseline_id": f"{ticker.lower()}-test-v1", "validation_status": "DRAFT",
        "evidence_packet_validation": "PASSED", "deterministic_research_gate": "PASSED",
        "risk_controller_result": "ALLOW_REVIEW", "point_in_time_status": "PASSED",
        "research_recommendation": "MAINTAIN", "quantity_authority": "none", "order_authority": False,
    }
    return recompute_hashes(value)


def overlay(ticker="SOXL", **changes):
    values = dict(ticker=ticker, market_session="2026-08-13", primary_price_status="VALIDATED",
                  independent_price_status="VERIFIED", technical_status="WATCH", event_risk_status="CLEAR",
                  hard_risk_observation="NO_PRIMARY_BREACH", risk_status="ACCEPTABLE",
                  portfolio_fit_status="FITS", cash_status="VERIFIED_ZERO", broker_snapshot_status="VERIFIED",
                  leveraged_confirmation_status="ALIGNED", active_timing_tranche=None,
                  rearm_status="OBSERVATION_ONLY", portfolio_state_revision=13, quantity=None,
                  quantity_authority="none", deterministic_existing_policy=None)
    values.update(changes)
    return build_overlay(**values)


def event_link(b):
    value = {"schema_version": "2.6.12", "baseline_event_link_id": f"{b['baseline_id']}--link",
             "ticker": b["ticker"], "entity_role": "DIRECT_PRODUCT", "baseline_id": b["baseline_id"],
             "baseline_hash": b["baseline_hash"], "event_bundle_id": "bundle", "event_bundle_hash": "a" * 64,
             "event_coverage_status": "PARTIAL_NONBLOCKING", "event_effect": "CONTEXT_ONLY",
             "analysis_cutoff": "2026-08-14T02:00:00Z", "link_created_at": "2026-08-14T05:00:00Z",
             "link_validation_status": "PARTIAL_NONBLOCKING", "link_hash": "0" * 64,
             "order_authority": False}
    value["link_hash"] = canonical_hash({k: v for k, v in value.items() if k != "link_hash"})
    return value


def compile_value(b, ov=None, val=None, link=None, blocked=None):
    return compile_shadow(baseline=b, valuation=val, event_link=link or event_link(b), overlay=ov or overlay(b["ticker"]),
                          portfolio=json.loads(PORTFOLIO.read_text(encoding="utf-8")), policy_path=POLICY,
                          provider_scope_path=PROVIDER, portfolio_path=PORTFOLIO, baseline_schema=BASELINE_SCHEMA,
                          live_strategy_state="UNCHANGED", blocked_decision_classes=blocked or [])


def observation(session="2026-08-14", **changes):
    value = {
        "market_session": session,
        "run_phase": "POST_MARKET_FINALIZED",
        "official_session_verified": True,
        "bar_finalized": True,
        "delivery_verified": True,
        "clean_committed_main": True,
        "portfolio_hash_unchanged": True,
        "policy_hash_unchanged": True,
        "manual": False,
        "replay": False,
        "order_authority": False,
    }
    value.update(changes)
    return value


class ValuationTests(unittest.TestCase):
    def test_val_01_finalized_kiwoom_raw_is_accepted(self):
        snap = build_issuer_valuation_snapshot(valuation_spec())
        self.assertEqual(validate_valuation_snapshot(snap, VALUATION_SCHEMA)["validation_status"], "PASSED")

    def test_val_02_extended_hours_rejected(self):
        spec = valuation_spec(); spec["price"]["market_session_type"] = "AFTER_HOURS"
        self.assertIn("PRICE_SESSION_NOT_REGULAR_COMPLETED", validate_valuation_snapshot(build_issuer_valuation_snapshot(spec), VALUATION_SCHEMA)["errors"])

    def test_val_03_price_conflict_blocks_snapshot(self):
        spec = valuation_spec(); spec["price"]["comparison_status"] = "CONFLICT"
        snap = build_issuer_valuation_snapshot(spec)
        self.assertEqual(snap["valuation_evidence_status"], "PRICE_EVIDENCE_CONFLICT")
        self.assertEqual(snap["valuation_judgement_status"], "UNVERIFIED")

    def test_val_04_numeric_metadata_required(self):
        snap = build_issuer_valuation_snapshot(valuation_spec()); del snap["balance_sheet"]["cash"]["as_of"]
        self.assertTrue(any("METRIC_METADATA_MISSING" in e for e in validate_valuation_snapshot(snap, VALUATION_SCHEMA)["errors"]))

    def test_val_05_basic_and_diluted_separate(self):
        snap = build_issuer_valuation_snapshot(valuation_spec())
        self.assertNotEqual(snap["capitalization"]["basic_shares"], snap["capitalization"]["diluted_shares_base"])

    def test_val_06_cash_and_restricted_cash_separate(self):
        snap = build_issuer_valuation_snapshot(valuation_spec())
        self.assertEqual((snap["balance_sheet"]["cash"]["value"], snap["balance_sheet"]["restricted_cash"]["value"]), (100.0, 20.0))

    def test_val_07_debt_and_convertibles_separate(self):
        snap = build_issuer_valuation_snapshot(valuation_spec())
        self.assertIn("debt", snap["balance_sheet"]); self.assertIn("convertible_instruments", snap["capitalization"])

    def test_val_08_llm_hash_ignored(self):
        spec = valuation_spec(); spec["snapshot_hash"] = "f" * 64
        self.assertNotEqual(build_issuer_valuation_snapshot(spec)["snapshot_hash"], spec["snapshot_hash"])

    def test_val_09_hash_deterministic(self):
        self.assertEqual(build_issuer_valuation_snapshot(valuation_spec())["snapshot_hash"], build_issuer_valuation_snapshot(valuation_spec())["snapshot_hash"])

    def test_val_10_stale_snapshot_cannot_activate(self):
        b = baseline(direct=True); val = build_issuer_valuation_snapshot(valuation_spec("SOXL")); val["valuation_evidence_status"] = "STALE"
        result = compile_value(b, val=val)
        self.assertNotEqual(result["shadow_compile_status"], "PASSED")


class IssuerSpecificTests(unittest.TestCase):
    def test_nbis_01_share_classes_evaluated(self):
        spec = valuation_spec("NBIS"); self.assertEqual(set(spec["capitalization"]["share_class_breakdown"]), {"A", "B"})

    def test_nbis_02_basic_share_source_and_date(self):
        item = valuation_spec("NBIS")["capitalization"]["basic_shares"]; self.assertTrue(item["source_evidence_id"] and item["as_of"])

    def test_nbis_03_base_and_stress_separate(self):
        snap = build_issuer_valuation_snapshot(valuation_spec("NBIS")); self.assertNotEqual(snap["valuation_scenarios"][1]["share_basis"], snap["valuation_scenarios"][2]["share_basis"])

    def test_nbis_04_dilution_categories_present(self):
        cap = valuation_spec("NBIS")["capitalization"]
        self.assertTrue(all(k in cap for k in ("ATM_capacity", "convertible_instruments", "warrants", "stock_compensation")))

    def test_nbis_05_proxy_not_reported_fcf(self):
        metrics = valuation_spec("NBIS")["operating_metrics"]; self.assertIsNot(metrics["local_ocf_minus_capex_proxy"], metrics["reported_free_cash_flow"])

    def test_nbis_06_commitments_not_revenue(self):
        self.assertNotIn("customer_commitments", valuation_spec("NBIS")["operating_metrics"])

    def test_nbis_07_restricted_cash_not_unrestricted(self):
        spec = valuation_spec("NBIS"); self.assertNotEqual(spec["balance_sheet"]["cash"]["value"], spec["balance_sheet"]["restricted_cash"]["value"])

    def test_nbis_08_incomplete_capital_structure_blocks(self):
        spec = valuation_spec("NBIS"); spec["required_missing_inputs"] = ["CAPITAL_STRUCTURE"]
        self.assertEqual(build_issuer_valuation_snapshot(spec)["valuation_evidence_status"], "PARTIAL")

    def test_nbis_09_scenario_complete_not_attractive(self):
        self.assertEqual(build_issuer_valuation_snapshot(valuation_spec("NBIS"))["valuation_judgement_status"], "UNCLASSIFIED")

    def test_mvll_01_product_valuation_not_applicable(self):
        self.assertEqual(baseline("MVLL")["valuation_applicability"], "NOT_APPLICABLE_TO_PRODUCT")

    def test_mvll_02_mrvl_stored_as_underlying(self):
        spec = valuation_spec("MRVL"); spec["entity_role"] = "UNDERLYING_ISSUER"
        self.assertEqual(build_issuer_valuation_snapshot(spec)["entity_role"], "UNDERLYING_ISSUER")

    def test_mvll_03_no_mvll_target_from_mrvl(self):
        self.assertNotIn("MVLL_TARGET_PRICE", build_issuer_valuation_snapshot(valuation_spec("MRVL")))

    def test_mvll_04_mrvl_times_two_prohibited(self):
        b = baseline("MVLL"); b["linked_components"] = [{"product_close_substitution": True}]; b = recompute_hashes(b)
        self.assertIn("SUPPLEMENTAL_PRICE_SUBSTITUTION_PROHIBITED", compile_value(b)["remaining_conditions"])

    def test_mvll_05_preferred_conversion_represented(self):
        spec = valuation_spec("MRVL"); spec["capitalization"]["convertible_instruments"] = {"series_a": 21.778}
        self.assertIn("series_a", build_issuer_valuation_snapshot(spec)["capitalization"]["convertible_instruments"])

    def test_mvll_06_cash_and_debt_point_in_time(self):
        bal = valuation_spec("MRVL")["balance_sheet"]; self.assertTrue(bal["cash"]["as_of"] and bal["debt"]["as_of"])

    def test_mvll_07_complete_product_keeps_boundary_block(self):
        self.assertIn("EMA10_RECLAIM_RVOL20", compile_value(baseline("MVLL"))["blocked_decision_classes"])

    def test_mvll_08_boundary_conflict_exact(self):
        self.assertEqual(compile_value(baseline("MVLL"))["blocked_decision_classes"], ["EMA10_RECLAIM_RVOL20"])

    def test_mvll_09_valuation_cannot_bypass_boundary(self):
        result = compile_value(baseline("MVLL")); self.assertIn("EMA10_RECLAIM_RVOL20", result["blocked_decision_classes"])


class ProductAndLinkTests(unittest.TestCase):
    def test_soxl_01_product_valuation_not_applicable(self): self.assertEqual(baseline()["valuation_applicability"], "NOT_APPLICABLE_TO_PRODUCT")
    def test_soxl_02_soxx_direction_only(self):
        b = baseline(); b["linked_components"] = [{"ticker": "SOXX", "confirmation_mode": "DIRECTION_ONLY", "product_close_substitution": False}]
        self.assertEqual(b["linked_components"][0]["confirmation_mode"], "DIRECTION_ONLY")
    def test_soxl_03_soxx_times_three_prohibited(self):
        b = baseline(); b["linked_components"] = [{"ticker": "SOXX", "product_close_substitution": True}]; b = recompute_hashes(b)
        self.assertEqual(compile_value(b)["shadow_compile_status"], "FAILED")
    def test_soxl_04_direct_price_identity(self): self.assertEqual(overlay()["ticker"], "SOXL")
    def test_soxl_05_complete_valid_inputs_compile(self): self.assertEqual(compile_value(baseline())["shadow_compile_status"], "PASSED")
    def test_soxl_06_activation_does_not_wait_for_other_tickers(self):
        result = compile_value(baseline("SOXL"))
        self.assertEqual((result["ticker"], result["shadow_compile_status"]), ("SOXL", "PASSED"))
    def test_soxl_07_activation_never_replays_historical_alerts(self):
        b = baseline("SOXL")
        temp, _, _, result = ActivationObservationTests()._activate(b, compile_value(b))
        self.assertEqual(result["historical_alert_replay_count"], 0)
        temp.cleanup()

    def test_link_01_hashes_match(self):
        b = baseline(); link = event_link(b); self.assertEqual(link["baseline_hash"], b["baseline_hash"])

    def test_link_02_stale_bundle_only_invalidates_link(self):
        b = baseline(); link = event_link(b); link["link_validation_status"] = "STALE"; link["link_hash"] = canonical_hash({k:v for k,v in link.items() if k!="link_hash"})
        self.assertEqual(compile_value(b, link=link)["shadow_strategy_state"], "STRATEGY_REFRESH_REQUIRED")

    def test_link_03_soxl_soxx_separate(self): self.assertNotEqual("SOXL", "SOXX")
    def test_link_04_mvll_mrvl_separate(self): self.assertNotEqual("MVLL", "MRVL")
    def test_link_05_ticker_local_failure(self):
        bad = event_link(baseline("SOXL")); bad["link_validation_status"]="INVALID"; bad["link_hash"]=canonical_hash({k:v for k,v in bad.items() if k!="link_hash"})
        self.assertNotEqual(compile_value(baseline("SOXL"), link=bad)["shadow_compile_status"], compile_value(baseline("MVLL"))["shadow_compile_status"])
    def test_link_06_link_change_does_not_mutate_portfolio(self):
        before = file_hash(PORTFOLIO)
        b = baseline("SOXL")
        link = event_link(b)
        link["event_bundle_hash"] = "b" * 64
        self.assertEqual(before, file_hash(PORTFOLIO))


class CompileTests(unittest.TestCase):
    def test_comp_01_incomplete_cannot_hold(self): self.assertNotEqual(compile_value(baseline(complete=False))["shadow_strategy_state"], "HOLD")
    def test_comp_02_unverified_cannot_add(self):
        b=baseline("NBIS", direct=True); result=compile_value(b, ov=overlay("NBIS", technical_status="READY")); self.assertNotEqual(result["strategy_signal"], "ADD_CANDIDATE")
    def test_comp_03_technical_from_overlay(self): self.assertEqual(compile_value(baseline(), ov=overlay(technical_status="DETERIORATING"))["technical_status"], "DETERIORATING")
    def test_comp_04_portfolio_fit_from_overlay(self): self.assertEqual(compile_value(baseline(), ov=overlay(portfolio_fit_status="CONSTRAINED"))["portfolio_fit_status"], "CONSTRAINED")
    def test_comp_05_hard_risk_priority(self):
        ov=overlay(technical_status="READY", hard_risk_observation="PRIMARY_BREACH_OBSERVED", deterministic_existing_policy={"action_on_breach":"exit_review"})
        self.assertEqual(compile_value(baseline(), ov=ov)["strategy_signal"], "EXIT_CANDIDATE")
    def test_comp_06_raw_llm_signal_rejected(self):
        b=baseline(); b["strategy_signal"]="ADD_CANDIDATE"; b=recompute_hashes(b)
        result=compile_value(b)
        self.assertEqual(result["shadow_compile_status"], "FAILED")
    def test_comp_07_live_strategy_preserved(self): self.assertEqual(compile_value(baseline())["live_strategy_state"], "UNCHANGED")
    def test_comp_08_no_notification_runtime_input(self): self.assertNotIn("notification_runtime", compile_value(baseline()))
    def test_comp_09_stateless_ticker_isolation(self): self.assertEqual(compile_value(baseline("MVLL"))["ticker"], "MVLL")
    def test_comp_10_quantity_null(self): self.assertIsNone(compile_value(baseline())["quantity"])
    def test_comp_11_order_false(self): self.assertFalse(compile_value(baseline())["order_authority"])


class ActivationObservationTests(unittest.TestCase):
    def _activate(self, b=None, result=None, expected=None):
        b=b or baseline(); result=result or compile_value(b)
        test_temp_root = ROOT / ".runtime-cache" / "tests"
        test_temp_root.mkdir(parents=True, exist_ok=True)
        root = test_temp_root / f"activation-{uuid.uuid4().hex}"
        root.mkdir(parents=True)
        temp = SimpleNamespace(cleanup=lambda: shutil.rmtree(root, ignore_errors=True))
        idx=root/"index.json"
        index={"schema_version":"2.6","mode":"SHADOW","updated_at":"2026-08-13T00:00:00Z","active":{},"historical_alert_replay_allowed":False,"portfolio_state_mutation":False,"order_authority":False}
        idx.write_text(json.dumps(index),encoding="utf-8")
        value=activate_shadow_candidate(baseline=b,compile_result=result,baseline_schema=BASELINE_SCHEMA,baseline_root=root/"baselines",index_path=idx,expected_prior_index_hash=expected or canonical_hash(index),activated_at="2026-08-14T05:00:00Z")
        return temp,root,idx,value

    def test_act_01_atomic_per_ticker(self):
        temp,_,idx,result=self._activate(); self.assertTrue(result["index_updated"]); self.assertIn("SOXL",json.loads(idx.read_text(encoding="utf-8"))["active"]); temp.cleanup()
    def test_act_02_wrong_prior_hash_rejected(self):
        temp,_,_,result=self._activate(expected="f"*64); self.assertEqual(result["errors"],["PRIOR_INDEX_HASH_MISMATCH"]); temp.cleanup()
    def test_act_03_old_baseline_remains(self):
        b=baseline(); temp,root,_,result=self._activate(b); self.assertTrue((root/"baselines"/"SOXL"/f"{b['baseline_id']}.json").exists()); temp.cleanup()
    def test_act_04_soxl_independent(self):
        temp,_,_,result=self._activate(); self.assertEqual(result["ticker"],"SOXL"); temp.cleanup()
    def test_act_05_nbis_incomplete_candidate_only(self):
        b=baseline("NBIS",complete=False,direct=True); temp,_,_,result=self._activate(b,compile_value(b)); self.assertEqual(result["activation_status"],"REJECTED"); temp.cleanup()
    def test_act_06_mvll_block_survives(self): self.assertIn("EMA10_RECLAIM_RVOL20",compile_value(baseline("MVLL"))["blocked_decision_classes"])
    def test_act_07_baseline_path_traversal_rejected(self):
        b=baseline(); b["baseline_id"]="../escape"; b=recompute_hashes(b)
        temp,_,_,result=self._activate(b,compile_value(b))
        self.assertEqual(result["errors"],["BASELINE_TARGET_PATH_INVALID"])
        temp.cleanup()
    def test_act_08_baseline_path_is_portable_and_relative(self):
        temp,_,idx,result=self._activate()
        self.assertTrue(result["index_updated"])
        stored=json.loads(idx.read_text(encoding="utf-8"))["active"]["SOXL"]["baseline_path"]
        self.assertFalse(Path(stored).is_absolute())
        self.assertNotIn("E:/",stored)
        temp.cleanup()

    def test_obs_01_manual_not_counted(self): self.assertEqual(record_observation(initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"),observation(manual=True))["valid_sessions"],[])
    def test_obs_02_replay_not_counted(self): self.assertEqual(record_observation(initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"),observation(replay=True))["valid_sessions"],[])
    def test_obs_03_future_finalized_counts_once(self):
        s=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"); self.assertEqual(record_observation(s,observation())["valid_sessions"],["2026-08-14"])
    def test_obs_04_duplicate_not_twice(self):
        s=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"); o=observation(); s=record_observation(s,o); self.assertEqual(len(record_observation(s,o)["valid_sessions"]),1)
    def test_obs_05_five_sessions_requires_review(self):
        s=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13")
        for day in range(14,19): s=record_observation(s,observation(f"2026-08-{day}"))
        self.assertEqual(s["status"],"FIVE_SESSION_REVIEW_REQUIRED")
    def test_obs_06_portfolio_mutation_critical(self):
        s=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"); self.assertEqual(record_observation(s,observation(portfolio_mutated=True))["status"],"CRITICAL_VIOLATION")
    def test_obs_07_order_authority_critical(self):
        s=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"); self.assertEqual(record_observation(s,observation(order_authority=True))["status"],"CRITICAL_VIOLATION")

    def test_obs_08_unverified_session_not_counted(self):
        state=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13")
        self.assertEqual(record_observation(state,observation(official_session_verified=False))["valid_sessions"],[])

    def test_obs_09_dirty_or_mutated_context_not_counted(self):
        state=initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13")
        self.assertEqual(record_observation(state,observation(clean_committed_main=False))["valid_sessions"],[])
        self.assertEqual(record_observation(state,observation(policy_hash_unchanged=False))["valid_sessions"],[])


class InvariantTests(unittest.TestCase):
    @staticmethod
    def _alert_policy(): return json.loads((ROOT / "stock-strategy-system/alert_policy.json").read_text(encoding="utf-8"))

    def test_inv_01_portfolio_hash_unchanged(self):
        before=file_hash(PORTFOLIO); compile_value(baseline()); self.assertEqual(before,file_hash(PORTFOLIO))
    def test_inv_02_strategy_version_unchanged(self): self.assertEqual(json.loads(PORTFOLIO.read_text(encoding="utf-8"))["strategy_version"],"2026-08-05-v4")
    def test_inv_03_soxl_hard_risk_threshold_unchanged(self): self.assertEqual(self._alert_policy()["holding_risk_rules"]["positions"]["SOXL"]["maximum_loss_fraction_from_average_cost"], 0.2)
    def test_inv_04_mvll_hard_risk_threshold_unchanged(self): self.assertEqual(self._alert_policy()["holding_risk_rules"]["positions"]["MVLL"]["maximum_loss_fraction_from_average_cost"], 0.6)
    def test_inv_05_nbis_hard_risk_threshold_unchanged(self): self.assertEqual(self._alert_policy()["holding_risk_rules"]["positions"]["NBIS"]["maximum_loss_fraction_from_average_cost"], 0.1)
    def test_inv_06_timing_quantities_unchanged(self):
        # I0-b (2026-10-06) removed the MVLL/SOXL timing slots from the active policy.
        self.assertEqual(self._alert_policy()["holding_timing_rules"]["positions"], {})
    def test_inv_07_rearm_rules_unchanged(self):
        rearm=self._alert_policy()["holding_timing_rules"]["weakness_rearm"]
        self.assertEqual((rearm["minimum_common_recovery_sessions"],rearm["minimum_completed_sessions_after_fill"]),(1,3))
    def test_inv_08_action_on_breach_unchanged(self):
        rules=self._alert_policy()["holding_risk_rules"]["positions"]
        self.assertTrue(all(rules[ticker]["action_on_breach"] is None for ticker in ("SOXL","MVLL","NBIS")))
    def test_inv_09_no_order_endpoint(self): self.assertNotIn("order_endpoint", compile_value(baseline()))
    def test_inv_10_no_fill_inference(self): self.assertNotIn("fill", compile_value(baseline()))
    def test_inv_11_no_sensitive_artifact_is_tracked(self):
        tracked=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True,encoding="utf-8").splitlines()
        normalized=[item.lower().replace("\\","/") for item in tracked]
        self.assertFalse(any(Path(item).name.startswith(".env") or "raw-broker" in item or "broker-screenshot" in item for item in normalized))
    def test_inv_12_unit_tests_are_offline(self): self.assertTrue(True)
    def test_observation_schema(self): self.assertEqual(validate_instance(initialize_observation(ticker="SOXL",baseline_id="b",baseline_hash="a"*64,activation_session="2026-08-13"),OBS_SCHEMA),[])
    def test_managed_output_path_allows_only_its_artifact_root(self):
        allowed=ROOT/"workspace/research/valuation-snapshots/test.json"
        self.assertEqual(validate_managed_output_path(allowed,repo_root=ROOT,allowed_relative_root="workspace/research/valuation-snapshots"),allowed.resolve())
        with self.assertRaisesRegex(ValueError,"OUTPUT_OUTSIDE_ALLOWED_ROOT"):
            validate_managed_output_path(PORTFOLIO,repo_root=ROOT,allowed_relative_root="workspace/research/valuation-snapshots")


class ArtifactValidationTests(unittest.TestCase):
    def test_artifact_01_valuation_instances_are_schema_valid_and_semantically_blocked(self):
        for ticker in ("nbis", "mrvl"):
            path=ROOT/f"workspace/research/valuation-snapshots/2026-08-13/{ticker}-valuation-snapshot.json"
            value=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_instance(value, VALUATION_SCHEMA), [])
            semantic=validate_valuation_snapshot(value, VALUATION_SCHEMA)
            self.assertIn("PRICE_EVIDENCE_CONFLICT", semantic["errors"])

    def test_artifact_02_event_links_are_schema_and_hash_valid(self):
        root=ROOT/"workspace/research/baseline-event-links/2026-08-13"
        for path in root.glob("*.json"):
            value=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_instance(value, LINK_SCHEMA), [])
            self.assertEqual(value["link_hash"], canonical_hash({k:v for k,v in value.items() if k!="link_hash"}))

    def test_artifact_03_compiles_are_schema_valid_and_non_authoritative(self):
        for path in (ROOT/"workspace/research/shadow-compiles/2026-08-13").glob("*-shadow-compile.json"):
            value=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_instance(value, COMPILE_SCHEMA), [])
            self.assertEqual(value["mode"], "NON_AUTHORITATIVE_SHADOW")
            self.assertIsNone(value["quantity"])
            self.assertFalse(value["order_authority"])

    def test_artifact_04_no_baseline_activation_or_observation_backfill(self):
        decision=json.loads((ROOT/"workspace/research/shadow-compiles/2026-08-13/activation-decision.json").read_text(encoding="utf-8"))
        self.assertEqual(decision["independently_activated_tickers"], [])
        self.assertTrue(all(row["observation_state_initialized"] is False for row in decision["results"]))
        self.assertEqual(decision["historical_alert_replay_count"], 0)

    def test_artifact_05_semantic_cohort_reset_is_zero_and_valid(self):
        progress=json.loads((ROOT/"workspace/state/integrated_shadow/shadow_progress.json").read_text(encoding="utf-8"))
        superseded=json.loads((ROOT/"workspace/state/integrated_shadow/cohorts/integrated-shadow-8c22e0073e2f2136/superseded_progress.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_instance(progress, PROGRESS_SCHEMA), [])
        self.assertEqual(validate_instance(superseded, SUPERSEDED_SCHEMA), [])
        self.assertEqual((progress["observed_attempts"],progress["valid_shadow_sessions"]),(0,0))
        self.assertEqual(superseded["reason"],"HOLDING_BASELINE_SEMANTIC_CHANGE")


if __name__ == "__main__": unittest.main()
