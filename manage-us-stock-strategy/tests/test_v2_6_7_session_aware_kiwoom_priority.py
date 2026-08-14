from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
sys.path.insert(0, str(SCRIPTS))

from build_kiwoom_session_observation import build_session_snapshot
from build_kiwoom_market_snapshot import build_snapshot
from kiwoom_runtime_bridge import blocked_api_target, validate_bridge_request
from run_kiwoom_session_aware_validation import build_validation, provider_scopes
from session_aware_market_data import (
    apply_extended_hours_guard,
    compare_price_observations,
    kiwoom_broker_quote_observation,
    kiwoom_daily_observation,
    market_session_at,
    yfinance_regular_close_observation,
)
from shadow_acceptance import semantic_fingerprint
from validation_common import load_json, validate_instance
from validate_kiwoom_session_aware_acceptance import validate_acceptance
from validate_kiwoom_market_snapshot import validate_snapshot_semantics
from validate_skill_deployment import normalized_text_sha256


SESSION = "2026-08-13"
AFTER = "2026-08-13T21:45:00+00:00"
NEXT_DAY = "2026-08-14T13:00:00+00:00"
TOLERANCE = {"absolute_usd_floor": 0.05, "relative_fraction": 0.001}


def regular(provider: str = "KIWOOM_REST", price: float = 100.0) -> dict:
    if provider == "KIWOOM_REST":
        return kiwoom_daily_observation(
            ticker="SOXL", reported_session=SESSION, close=price,
            provider_timestamp=NEXT_DAY,
        )
    return yfinance_regular_close_observation(
        ticker="SOXL", reported_session=SESSION, close=price,
        provider_timestamp=AFTER,
    )


def snapshot(tickers: list[str], generated_at: str, session: str, closes: dict[str, float]) -> dict:
    return {
        "generated_at": generated_at, "completed_session": session,
        "ticker_results": [{
            "ticker": ticker, "identity": {"mapping_status": "VERIFIED"},
            "raw": {"bars": [{"session": session, "close": closes[ticker]}]},
        } for ticker in tickers],
    }


def yf(tickers: list[str], generated_at: str, session: str, closes: dict[str, float]) -> dict:
    return {
        "generated_at": generated_at,
        "records": {ticker: {"bars": [{"session": session, "close": closes[ticker]}]} for ticker in tickers},
    }


class SessionComparabilityTests(unittest.TestCase):
    def test_session_01_premarket_and_regular_close_not_comparable(self):
        left = regular(); left["market_session_type"] = "PRE_MARKET"
        result = compare_price_observations(left, regular("yfinance"), tolerance_policy=TOLERANCE)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertEqual(result["reason_code"], "NOT_COMPARABLE_SESSION")

    def test_session_02_after_hours_and_regular_close_not_comparable(self):
        left = regular(); left["market_session_type"] = "AFTER_HOURS"
        result = compare_price_observations(left, regular("yfinance"), tolerance_policy=TOLERANCE)
        self.assertEqual(result["reason_code"], "NOT_COMPARABLE_SESSION")

    def test_session_03_day_market_and_regular_close_not_comparable(self):
        left = regular(); left["market_session_type"] = "DAY_MARKET"
        result = compare_price_observations(left, regular("yfinance"), tolerance_policy=TOLERANCE)
        self.assertEqual(result["reason_code"], "NOT_COMPARABLE_SESSION")

    def test_session_04_same_finalized_regular_closes_compare_after_hours(self):
        result = compare_price_observations(regular(price=100.0), regular("yfinance", 100.04), tolerance_policy=TOLERANCE)
        self.assertEqual(result["comparison_status"], "MATCH")

    def test_session_05_query_time_does_not_make_daily_row_a_close(self):
        value = kiwoom_daily_observation(ticker="SOXL", reported_session=SESSION, close=101.0, provider_timestamp=AFTER)
        self.assertEqual(value["market_session_type"], "AFTER_HOURS")
        self.assertEqual(value["price_basis"], "UNKNOWN")
        self.assertFalse(value["bar_finalized"])

    def test_session_06_quote_type_mismatch_explicit(self):
        left = regular(); left["quote_type"] = "BID"
        result = compare_price_observations(left, regular("yfinance"), tolerance_policy=TOLERANCE)
        self.assertEqual(result["reason_code"], "QUOTE_TYPE_MISMATCH")

    def test_session_07_timestamp_mismatch_explicit(self):
        result = compare_price_observations(regular(), regular("yfinance"), tolerance_policy=TOLERANCE, timestamps_compatible=False)
        self.assertEqual(result["reason_code"], "TIMESTAMP_MISMATCH")

    def test_session_07b_preclose_timestamp_cannot_validate_completed_close(self):
        left = regular()
        left["provider_timestamp"] = "2026-08-13T19:00:00+00:00"
        result = compare_price_observations(left, regular("yfinance"), tolerance_policy=TOLERANCE)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertEqual(result["reason_code"], "TIMESTAMP_MISMATCH")

    def test_session_08_extended_quote_cannot_overwrite_close(self):
        extended = kiwoom_broker_quote_observation(
            ticker="SOXL", reported_session=SESSION, price=110.0,
            provider_timestamp=AFTER, explicit_session_type="AFTER_HOURS",
        )
        result = compare_price_observations(extended, regular("yfinance"), tolerance_policy=TOLERANCE)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertFalse(extended["hard_risk_authority"])

    def test_session_09_extended_quote_cannot_enter_indicators(self):
        value = kiwoom_broker_quote_observation(
            ticker="SOXL", reported_session=SESSION, price=110.0,
            provider_timestamp=AFTER, explicit_session_type="AFTER_HOURS",
        )
        self.assertFalse(value["daily_indicator_authority"])

    def test_session_10_extended_state_cannot_upgrade_watch(self):
        result = apply_extended_hours_guard(prior_state="WATCH", requested_state="READY")
        self.assertEqual(result["resulting_state"], "WATCH")
        self.assertIsNone(result["quantity"])

    def test_session_11_extended_state_cannot_confirm_hard_risk(self):
        result = apply_extended_hours_guard(prior_state="READY", hard_risk_requested=True)
        self.assertEqual(result["hard_risk_state"], "PREMARKET_RISK_WATCH")
        self.assertFalse(result["order_authority"])


class PriorityAndScopeTests(unittest.TestCase):
    def test_priority_01_kiwoom_owns_broker_account_facts(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        self.assertEqual(policy["account_facts_authority"], "KIWOOM_AUTHORITATIVE")

    def test_priority_02_kiwoom_owns_operational_quote(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        self.assertEqual(policy["broker_quote_authority"], "KIWOOM_OPERATIONAL_PRIMARY")

    def test_priority_03_yfinance_remains_shadow(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        self.assertEqual(policy["shadow_provider"], "YFINANCE_DIAGNOSTIC_SHADOW")

    def test_priority_03b_transition_is_guarded_scoped(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        self.assertEqual(policy["transition_status"], "KIWOOM_PRIMARY_GUARDED_SCOPED")

    def test_priority_04_out_of_scope_difference_is_not_conflict(self):
        left = kiwoom_daily_observation(ticker="SOXL", reported_session=SESSION, close=120.0, provider_timestamp=AFTER)
        result = compare_price_observations(left, regular("yfinance", 100.0), tolerance_policy=TOLERANCE)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")

    def test_priority_05_true_regular_close_conflict_visible(self):
        result = compare_price_observations(regular(price=110.0), regular("yfinance", 100.0), tolerance_policy=TOLERANCE)
        self.assertEqual(result["comparison_status"], "CONFLICT")
        self.assertTrue(result["web_resolution_required"])

    def test_scope_01_fsly_fallback_is_ticker_local(self):
        rows = provider_scopes(["FSLY", "NOW"], effective_from=AFTER, acceptance_hash="a" * 64)
        fsly, now = rows
        self.assertEqual(fsly["technical_history_primary"], "YFINANCE_PRIMARY_VALIDATED_FALLBACK")
        self.assertEqual(now["technical_history_primary"], "KIWOOM_ADJUSTED_LOCAL_DETERMINISTIC")

    def test_scope_02_mvll_conflict_is_decision_class_local(self):
        row = provider_scopes(["MVLL"], effective_from=AFTER, acceptance_hash="a" * 64)[0]
        self.assertEqual(row["blocked_decision_classes"], ["EMA10_RECLAIM_RVOL20"])
        self.assertEqual(row["regular_close_primary"], "KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED")

    def test_scope_03_event_incomplete_does_not_block_provider(self):
        tickers = ["SOXL"]
        closes = {"SOXL": 100.0}
        value = build_validation(
            prior_kiwoom=snapshot(tickers, NEXT_DAY, SESSION, closes),
            prior_yfinance=yf(tickers, AFTER, SESSION, closes),
            latest_kiwoom=snapshot(tickers, NEXT_DAY, SESSION, closes),
            latest_yfinance=yf(tickers, AFTER, SESSION, closes),
            prior_session=SESSION, latest_session=SESSION, tolerance=TOLERANCE,
            decision_boundaries={}, generated_at=AFTER, acceptance_hash="a" * 64,
            tickers=tickers, event_data_complete=False,
        )
        self.assertEqual(value["event_gate_status"], "EVENT_REVIEW_PENDING")
        self.assertNotEqual(value["provider_transition_status"], "KIWOOM_PRIMARY_TRANSITION_BLOCKED")

    def test_scope_04_checked_in_provider_scopes_are_complete_and_locked(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        manifest_path = ROOT / "workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json"
        expected = {"SOXL", "MVLL", "NBIS", "BE", "TOST", "NOW", "FSLY", "SOXX", "MRVL", "AAPL", "IBM"}
        scopes = policy["provider_scopes"]
        self.assertEqual({row["ticker"] for row in scopes}, expected)
        self.assertEqual(len(scopes), len(expected))
        expected_hash = normalized_text_sha256(manifest_path).lower()
        self.assertTrue(all(row["acceptance_artifact_hash"] == expected_hash for row in scopes))
        self.assertTrue(all(row["order_authority"] is False for row in scopes))
        by_ticker = {row["ticker"]: row for row in scopes}
        self.assertEqual(by_ticker["FSLY"]["technical_history_primary"], "YFINANCE_PRIMARY_VALIDATED_FALLBACK")
        self.assertEqual(by_ticker["MVLL"]["blocked_decision_classes"], [])
        self.assertEqual(by_ticker["MVLL"]["volume_primary"], "KIWOOM_VALID_SCOPED")
        self.assertEqual(by_ticker["MVLL"]["volume_decision_class"], "RVOL20")
        self.assertRegex(by_ticker["MVLL"]["volume_acceptance_artifact_hash"], r"^[a-f0-9]{64}$")


class InvariantAndContractTests(unittest.TestCase):
    def test_inv_01_to_05_strategy_and_threshold_files_unchanged_by_helpers(self):
        portfolio = (ROOT / "stock-strategy-system/portfolio_state.json").read_bytes()
        alert = load_json(ROOT / "stock-strategy-system/alert_policy.json")
        before = (portfolio, alert["strategy_version"], json.dumps(alert.get("holding_risk_rules"), sort_keys=True), json.dumps(alert.get("holding_timing_rules"), sort_keys=True))
        apply_extended_hours_guard(prior_state="WATCH", requested_state="READY")
        after_alert = load_json(ROOT / "stock-strategy-system/alert_policy.json")
        after = ((ROOT / "stock-strategy-system/portfolio_state.json").read_bytes(), after_alert["strategy_version"], json.dumps(after_alert.get("holding_risk_rules"), sort_keys=True), json.dumps(after_alert.get("holding_timing_rules"), sort_keys=True))
        self.assertEqual(before, after)

    def test_inv_06_order_authority_recursively_false(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        found = []
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "order_authority": found.append(child)
                    walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(policy)
        self.assertTrue(found)
        self.assertTrue(all(value is False for value in found))

    def test_inv_07_order_endpoint_not_allowlisted(self):
        self.assertTrue(blocked_api_target("kt10000", "/api/dostk/ordr"))
        request = validate_bridge_request({"operation": "market_quote", "ticker": "SOXL", "fx_applied": False})
        self.assertEqual(request["operation"], "market_quote")

    def test_broker_quote_builder_keeps_ticker_failures_local(self):
        def batch(requests):
            return [
                {"bridge_status": "PASS", "data": [{"cur_prc": "100.0"}], "retrieved_at": AFTER, "order_authority": False},
                {"bridge_status": "KIWOOM_API_UNAVAILABLE", "data": [], "retrieved_at": AFTER, "order_authority": False},
            ]
        value = build_session_snapshot(["SOXL", "FSLY"], reported_session=SESSION, generated_at=AFTER, batch_call=batch)
        self.assertEqual(value["data_status"], "PARTIAL")
        self.assertEqual([row["ticker"] for row in value["records"]], ["SOXL"])
        self.assertEqual(value["errors"][0]["ticker"], "FSLY")

    def test_new_schemas_and_policy_validate(self):
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        self.assertEqual(validate_instance(policy, SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json"), [])
        record = regular()
        self.assertEqual(validate_instance(record, SCHEMAS / "market-price-observation.schema.json"), [])

    def test_active_snapshot_authority_pair_is_schema_and_semantically_valid(self):
        def bridge(request):
            ticker = request.get("ticker", "SOXL")
            operation = request["operation"]
            if operation == "stock_list":
                data = [{"stex_tp": "NY", "stk_cd": ticker, "stk_nm": ticker, "stk_enm": ticker,
                         "mkgb": "NYSE", "upgb": "", "isEtf": "Y"}]
            elif operation == "etf_etn_list":
                data = [{"stex_tp": "NY", "code": ticker, "cate1": "ETF", "cate2": "",
                         "etn": "N", "mkgb": "", "upnm": ""}]
            elif operation == "stock_lookup":
                data = [{"stex_tp": "NY", "stk_cd": ticker, "stk_nm": ticker, "stk_enm": ticker,
                         "mkgb": "NYSE", "upgb": "", "isEtf": "Y"}]
            else:
                basis = "0" if request.get("price_basis") == "RAW" else "1"
                data = [{"cur_prc": "100", "pred_pre": "0", "flu_rt": "0", "acc_trde_qty": "1000",
                         "acc_trde_prica": "100000", "open_pric": "99", "high_pric": "101",
                         "low_pric": "98", "dt": "20260813", "upd_stkpc_tp": basis, "upd_rt": "1"}]
            return {"bridge_status": "PASS", "operation": operation, "ticker": ticker, "data": data,
                    "runtime_commit": "6" * 40, "retrieved_at": AFTER, "order_authority": False}
        value = build_snapshot(
            ["SOXL"], completed_session=SESSION, bridge_call=bridge, generated_at=AFTER,
            portfolio_state_hash="a" * 64, provider_state="ENABLED_GUARDED_SCOPED",
            primary_provider="KIWOOM_REST_GUARDED_SCOPED",
        )
        self.assertEqual(validate_instance(value, SCHEMAS / "kiwoom-market-snapshot.schema.json"), [])
        self.assertEqual(validate_snapshot_semantics(value), [])

    def test_guarded_priority_requires_locked_acceptance_manifest(self):
        manifest_path = ROOT / "workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json"
        errors = validate_acceptance(
            manifest=load_json(manifest_path), manifest_path=manifest_path,
            manifest_schema=SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json",
            priority_policy=load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json"),
            priority_schema=SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json",
            source_registry=load_json(ROOT / "workspace/policies/source_capabilities.json"),
            source_schema=SCHEMAS / "source-capability.schema.json", repo_root=ROOT,
        )
        self.assertEqual(errors, [])

    def test_missing_acceptance_hash_blocks_guarded_transition(self):
        manifest_path = ROOT / "workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json"
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        policy["acceptance_evidence"]["session_aware_acceptance_manifest_sha256"] = None
        errors = validate_acceptance(
            manifest=load_json(manifest_path), manifest_path=manifest_path,
            manifest_schema=SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json",
            priority_policy=policy,
            priority_schema=SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json",
            source_registry=load_json(ROOT / "workspace/policies/source_capabilities.json"),
            source_schema=SCHEMAS / "source-capability.schema.json", repo_root=ROOT,
        )
        self.assertIn("priority policy acceptance hash mismatch", errors)

    def test_scope_acceptance_hash_mismatch_blocks_guarded_transition(self):
        manifest_path = ROOT / "workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json"
        policy = load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json")
        policy["provider_scopes"][0]["acceptance_artifact_hash"] = "0" * 64
        errors = validate_acceptance(
            manifest=load_json(manifest_path), manifest_path=manifest_path,
            manifest_schema=SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json",
            priority_policy=policy,
            priority_schema=SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json",
            source_registry=load_json(ROOT / "workspace/policies/source_capabilities.json"),
            source_schema=SCHEMAS / "source-capability.schema.json", repo_root=ROOT,
        )
        self.assertIn("provider scope acceptance hash mismatch: SOXL", errors)

    def test_provider_authority_change_starts_zero_count_cohort(self):
        progress = load_json(ROOT / "workspace/state/integrated_shadow/shadow_progress.json")
        self.assertEqual(progress["semantic_fingerprint"], semantic_fingerprint(ROOT))
        self.assertEqual(progress["valid_shadow_sessions"], 0)
        self.assertEqual(progress["observed_attempts"], 0)
        archives = [load_json(path) for path in
                    (ROOT / "workspace/state/integrated_shadow/cohorts").glob("*/superseded_progress.json")]
        predecessors = [item for item in archives if item.get("superseded_by") == progress["cohort_id"]]
        self.assertEqual(len(predecessors), 1)
        self.assertEqual(predecessors[0]["cohort_status"], "COHORT_SUPERSEDED")
        self.assertFalse(predecessors[0]["order_authority"])


if __name__ == "__main__":
    unittest.main()
