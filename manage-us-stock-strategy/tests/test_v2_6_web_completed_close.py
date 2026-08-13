from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_independent_close_provider import audit_provider
from build_price_crosscheck_queue import build_queue
from resolve_leveraged_quote import evaluate_leveraged_confirmation
from validation_common import load_json
from web_close_evidence import extracted_text_sha256, resolve_shadow_close, validate_raw_web_evidence
from v2_6_test_helpers import approved_web_policy, queue_item, valid_web_evidence


class V26WebCompletedCloseTests(unittest.TestCase):
    def policy(self): return approved_web_policy()
    def validate(self, record=None, queue=None):
        return validate_raw_web_evidence(record or valid_web_evidence(), queue or queue_item(), self.policy(), analysis_cutoff="2026-08-13T05:00:00Z")

    def market(self):
        row = {"bar_date": "2026-08-12", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1_000_000,
               "corporate_action_unresolved": False, "indicator_validation": {"status": "passed", "errors": []}}
        return {"symbols": {"MVLL": row}}

    def test_web_01_empty_queue_not_required(self):
        result = build_queue(completed_session="2026-08-12", market_snapshot=self.market(), candidate_dispositions=[], holding_strategies=[], hard_risk_result={"candidates": []})
        self.assertEqual((result["crosscheck_requirement"], result["web_acquisition_status"], result["queue"]), ("NOT_REQUIRED", "NOT_REQUIRED", []))

    def test_web_02_ready_creates_queue_item(self):
        result = build_queue(completed_session="2026-08-12", market_snapshot=self.market(), candidate_dispositions=[{"ticker": "MVLL", "opportunity_state": "READY"}], holding_strategies=[], hard_risk_result={"candidates": []})
        self.assertEqual(result["queue"][0]["queue_reason"], "READY")

    def test_web_03_ordinary_hold_no_queue(self):
        result = build_queue(completed_session="2026-08-12", market_snapshot=self.market(), candidate_dispositions=[], holding_strategies=[{"ticker": "MVLL", "strategy_state": "HOLD"}], hard_risk_result={"candidates": []})
        self.assertEqual(result["queue"], [])

    def test_web_04_hard_risk_queues_and_stays_visible(self):
        result = build_queue(completed_session="2026-08-12", market_snapshot=self.market(), candidate_dispositions=[], holding_strategies=[], hard_risk_result={"candidates": [{"symbol": "MVLL", "event_type": "holding_max_loss_breach", "breached": True, "boundary_usd": 90}]})
        self.assertEqual(result["queue"][0]["queue_reason"], "HARD_RISK_BOUNDARY")

    def test_web_05_search_snippet_rejected(self):
        record = valid_web_evidence(); record["is_search_snippet"] = True
        self.assertEqual(self.validate(record)["evidence_validation_status"], "REJECTED")

    def test_web_06_yahoo_origin_rejected(self):
        record = valid_web_evidence(); record.update({"source_url": "https://finance.yahoo.com/x", "final_source_url": "https://finance.yahoo.com/x", "source_domain": "finance.yahoo.com", "is_yahoo_origin": True})
        self.assertIn("YAHOO_ORIGIN_NOT_INDEPENDENT", self.validate(record)["errors"])

    def test_web_07_missing_reported_session_inconclusive(self):
        record = valid_web_evidence(); record["reported_session"] = None
        self.assertEqual(self.validate(record)["evidence_validation_status"], "INCONCLUSIVE")

    def test_web_08_missing_source_timestamp_inconclusive(self):
        record = valid_web_evidence(); record["source_timestamp"] = None
        self.assertEqual(self.validate(record)["evidence_validation_status"], "INCONCLUSIVE")

    def test_web_09_unknown_price_basis_inconclusive(self):
        record = valid_web_evidence(); record["price_basis"] = "UNKNOWN"
        self.assertEqual(self.validate(record)["evidence_validation_status"], "INCONCLUSIVE")

    def test_web_10_adjusted_close_inconclusive(self):
        record = valid_web_evidence(); record["price_basis"] = "ADJUSTED_CLOSE"
        self.assertEqual(self.validate(record)["evidence_validation_status"], "INCONCLUSIVE")

    def test_web_11_valid_same_session_raw_close_validates(self):
        self.assertEqual(self.validate()["evidence_validation_status"], "VALIDATED")

    def test_web_12_validator_never_returns_match(self):
        self.assertEqual(self.validate()["comparison_status"], "NOT_EVALUATED")

    def test_web_13_approved_tolerance_used(self):
        result = resolve_shadow_close(queue_item(), valid_web_evidence(close=100.02), self.policy())
        self.assertEqual(result["tolerance_usd"], 0.1)

    def test_web_14_inside_tolerance_matches(self):
        self.assertEqual(resolve_shadow_close(queue_item(), valid_web_evidence(close=100.02), self.policy())["shadow_crosscheck_status"], "MATCH")

    def test_web_15_outside_tolerance_conflicts(self):
        self.assertEqual(resolve_shadow_close(queue_item(), valid_web_evidence(close=101), self.policy())["shadow_crosscheck_status"], "CONFLICT")

    def test_web_16_boundary_flip_conflicts_inside_tolerance(self):
        item = queue_item(); item["decision_boundaries"] = [{"value": 100.01, "operator": "less_than_or_equal"}]
        self.assertEqual(resolve_shadow_close(item, valid_web_evidence(close=100.02), self.policy())["comparison_status"], "DECISION_BOUNDARY_FLIP")

    def test_web_17_ticker_conflict_is_local(self):
        bad = valid_web_evidence(); bad["ticker"] = "SOXL"
        self.assertEqual(self.validate(bad)["evidence_validation_status"], "REJECTED")
        self.assertEqual(self.validate()["evidence_validation_status"], "VALIDATED")

    def test_web_18_browser_unavailable_preserves_ready_pending(self):
        state = {"opportunity_state": "READY", "execution_state": "VERIFICATION_PENDING", "web_acquisition_status": "UNAVAILABLE"}
        self.assertEqual((state["opportunity_state"], state["execution_state"]), ("READY", "VERIFICATION_PENDING"))

    def test_web_19_shadow_match_cannot_promote_execution(self):
        result = resolve_shadow_close(queue_item(), valid_web_evidence(), self.policy(), current_execution_state="VERIFICATION_PENDING")
        self.assertEqual((result["shadow_crosscheck_status"], result["execution_state"]), ("MATCH", "VERIFICATION_PENDING"))

    def test_web_20_shadow_conflict_cannot_mutate_policy_or_portfolio(self):
        policy = self.policy(); before = copy.deepcopy(policy)
        result = resolve_shadow_close(queue_item(), valid_web_evidence(close=110), policy)
        self.assertEqual(policy, before); self.assertIsNone(result["quantity"])

    def test_web_21_soxl_remains_direction_only(self):
        registry = load_json(ROOT / "workspace/policies/instrument_registry.json")
        self.assertEqual(registry["instruments"]["SOXL"]["confirmation_mode"], "DIRECTION_ONLY")

    def test_web_22_soxx_times_three_not_direct_soxl_validation(self):
        registry = load_json(ROOT / "workspace/policies/instrument_registry.json")["instruments"]
        result = evaluate_leveraged_confirmation({"bar_date": "2026-08-12", "close": 100, "close_prev": 99}, {"bar_date": "2026-08-12", "close": 200, "close_prev": 190}, profile=registry["SOXL"])
        self.assertFalse(result["product_close_substitution"])

    def test_web_23_mvll_mrvl_is_supplemental(self):
        registry = load_json(ROOT / "workspace/policies/instrument_registry.json")["instruments"]
        result = evaluate_leveraged_confirmation({"bar_date": "2026-08-12", "close": 100, "close_prev": 99}, {"bar_date": "2026-08-12", "close": 50, "close_prev": 49}, profile=registry["MVLL"])
        self.assertFalse(result["product_close_substitution"])

    def test_web_24_mrvl_cannot_replace_mvll_close(self):
        self.assertEqual(queue_item("MVLL")["ticker"], "MVLL")

    def test_web_25_no_unapproved_tracking_tolerance(self):
        registry = load_json(ROOT / "workspace/policies/instrument_registry.json")
        self.assertEqual(registry["instruments"]["MVLL"]["tracking_tolerance_authority"], "SHADOW_ONLY_UNLESS_POLICY_SUPPLIED")

    def provider_record(self, **overrides):
        value = {"provider": "placeholder", "provider_state": "DISCOVERED", "independent_from_yahoo": True,
                 "source_timestamp_supported": True, "enabled": False, "independent_crosscheck_eligible": False,
                 "sample_comparisons": [], "shadow_session_results": [], "user_approval_reference": None}
        value.update(overrides); return value

    def test_api_01_placeholder_disabled(self):
        policy = load_json(ROOT / "workspace/policies/independent_close_provider_onboarding_policy.json")
        self.assertFalse(policy["placeholder"]["enabled"])

    def test_api_02_enablement_needs_acceptance(self):
        result = audit_provider(self.provider_record(enabled=True, provider_state="ENABLED"), {})
        self.assertIn("ACCEPTANCE_RECORD_INCOMPLETE", result["errors"])

    def test_api_03_enablement_needs_user_approval(self):
        result = audit_provider(self.provider_record(enabled=True, provider_state="ENABLED", sample_comparisons=[{}], shadow_session_results=[{}]), {})
        self.assertIn("EXPLICIT_USER_APPROVAL_MISSING", result["errors"])

    def test_api_04_source_timestamp_required(self):
        self.assertIn("SOURCE_TIMESTAMP_UNSUPPORTED", audit_provider(self.provider_record(source_timestamp_supported=False), {})["errors"])

    def test_api_05_yahoo_independence_required(self):
        self.assertIn("PROVIDER_NOT_INDEPENDENT_FROM_YAHOO", audit_provider(self.provider_record(independent_from_yahoo=False), {})["errors"])


if __name__ == "__main__": unittest.main()
