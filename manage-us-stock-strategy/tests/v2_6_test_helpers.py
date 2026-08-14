from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def valid_baseline(ticker: str = "NBIS") -> dict[str, Any]:
    from holding_research import recompute_hashes

    types = {"NBIS": "ISSUER_EQUITY", "MVLL": "SINGLE_STOCK_LEVERAGED_ETF", "SOXL": "SECTOR_LEVERAGED_ETF"}
    applicability = {"NBIS": "DIRECT", "MVLL": "UNDERLYING_BASED", "SOXL": "NOT_APPLICABLE_TO_PRODUCT"}
    basis = {"NBIS": "NBIS_ISSUER", "MVLL": "MRVL_ISSUER", "SOXL": "SEMICONDUCTOR_SECTOR_REGIME"}
    valuation = "NOT_APPLICABLE" if ticker == "SOXL" else "FAIR"
    evidence_id = f"{ticker.lower()}-e1"
    claim_id = f"{ticker.lower()}-c1"
    value = {
        "schema_version": "2.6", "baseline_id": f"{ticker.lower()}-20260813-v1", "baseline_version": 1,
        "ticker": ticker, "baseline_type": types[ticker], "analysis_cutoff": "2026-08-13T05:00:00Z",
        "evidence_cutoff": "2026-08-13T04:59:00Z", "content_status": "PARTIAL",
        "thesis_status": "VALID", "valuation_applicability": applicability[ticker],
        "valuation_status": valuation, "valuation_basis": basis[ticker],
        "fundamental_risk_status": "ACCEPTABLE", "primary_reason": f"{ticker} verified primary-source thesis.",
        "strongest_counter_case": "Growth expectations may weaken while financing or cycle risk rises.",
        "invalidation_conditions": ["Official evidence invalidates the principal demand or product thesis."],
        "next_research_triggers": ["Next official earnings or sponsor disclosure."],
        "claims": [{"claim_id": claim_id, "claim_type": "BUSINESS_MODEL", "evidence_ids": [evidence_id],
                    "normalized_claim": "Primary source confirms the relevant issuer or product structure."}],
        "evidence": [{"evidence_id": evidence_id, "source_url": "https://example.com/official",
                      "source_type": "OFFICIAL_PRIMARY", "published_at": "2026-08-12T20:00:00Z",
                      "retrieved_at": "2026-08-13T04:58:00Z", "effective_at": "2026-08-12T20:00:00Z",
                      "evidence_cutoff": "2026-08-13T04:59:00Z", "point_in_time_eligible": True,
                      "normalized_field": "official product or issuer disclosure", "verification_status": "VERIFIED"}],
        "claim_ids": [claim_id], "evidence_ids": [evidence_id],
        "linked_components": [], "technical_view_at_baseline": "HISTORICAL_CONTEXT_ONLY",
        "portfolio_fit_view_at_baseline": "HISTORICAL_CONTEXT_ONLY",
        "research_packet_hash": "0" * 64, "baseline_hash": "0" * 64,
        "supersedes_baseline_id": None, "validation_status": "DRAFT",
        "evidence_packet_validation": "PASSED", "deterministic_research_gate": "PASSED",
        "risk_controller_result": "ALLOW_REVIEW", "point_in_time_status": "PASSED",
        "research_recommendation": "MAINTAIN", "quantity_authority": "none", "order_authority": False,
    }
    if ticker == "MVLL":
        value["linked_components"] = [{"ticker": "MRVL", "role": "UNDERLYING_THESIS", "confirmation_mode": "DAILY_MULTIPLE"}]
    if ticker == "SOXL":
        value["linked_components"] = [{"ticker": "SOXX", "role": "SECTOR_DIRECTION_PROXY", "confirmation_mode": "DIRECTION_ONLY"}]
    return recompute_hashes(value)


def valid_overlay(ticker: str = "NBIS", **overrides: Any) -> dict[str, Any]:
    from holding_research import build_overlay

    values = {
        "ticker": ticker, "market_session": "2026-08-12", "primary_price_status": "VALIDATED",
        "independent_price_status": "PENDING", "technical_status": "WATCH", "event_risk_status": "CLEAR",
        "hard_risk_observation": "NO_PRIMARY_BREACH", "risk_status": "ACCEPTABLE",
        "portfolio_fit_status": "FITS", "cash_status": "VERIFIED_ZERO", "broker_snapshot_status": "VERIFIED",
        "leveraged_confirmation_status": "NOT_APPLICABLE" if ticker == "NBIS" else "ALIGNED",
        "active_timing_tranche": None, "rearm_status": "NOT_APPLICABLE", "portfolio_state_revision": 13,
    }
    values.update(overrides)
    return build_overlay(**values)


def queue_item(ticker: str = "MVLL", close: float = 100.0) -> dict[str, Any]:
    from price_evidence import request_id

    item_id = request_id(ticker, "2026-08-12", "READY")
    return {"queue_item_id": item_id, "request_id": item_id, "ticker": ticker,
            "canonical_identity": ticker, "primary_exchange": "NASDAQ", "completed_session": "2026-08-12",
            "primary_close": close, "primary_price_basis": "RAW_REGULAR_SESSION_CLOSE",
            "price_basis": "RAW_REGULAR_SESSION_CLOSE", "currency": "USD", "queue_reason": "READY",
            "reason": "READY", "decision_boundaries": [], "current_execution_state": "VERIFICATION_PENDING",
            "quantity": None, "order_authority": False}


def approved_web_policy() -> dict[str, Any]:
    from validation_common import load_json

    policy = deepcopy(load_json(ROOT / "workspace/policies/web_completed_close_evidence_policy.json"))
    policy["approved_routes"] = [{"status": "SHADOW_APPROVED", "source_domain": "exchange.example",
                                  "source_type": "OFFICIAL_EXCHANGE", "url_prefix": "https://exchange.example/"}]
    return policy


def valid_web_evidence(ticker: str = "MVLL", close: float = 100.02) -> dict[str, Any]:
    from web_close_evidence import extracted_text_sha256

    text = f"{ticker} regular session close on 2026-08-12 was {close} USD"
    return {"schema_version": "2.6.3", "queue_item_id": queue_item(ticker)["queue_item_id"],
            "source_route_id": "LEGACY_EXAMPLE_ROUTE", "ticker": ticker,
            "security_name": ticker, "reported_session": "2026-08-12", "reported_close": close,
            "currency": "USD", "price_basis": "RAW_REGULAR_SESSION_CLOSE", "provider": "Example Exchange",
            "source_url": f"https://exchange.example/{ticker.lower()}/history",
            "final_source_url": f"https://exchange.example/{ticker.lower()}/history",
            "source_domain": "exchange.example", "source_type": "OFFICIAL_EXCHANGE",
            "source_title": f"{ticker} Historical Data", "source_field_label": "Close",
            "retrieved_at": "2026-08-13T04:50:00Z", "source_timestamp": "2026-08-13T00:10:00Z",
            "acquisition_method": "CODEX_WEB", "is_search_snippet": False, "is_yahoo_origin": False,
            "security_identity_match_claim": True, "regular_session_close_claim": True,
            "extracted_text": text, "extracted_text_sha256": extracted_text_sha256(text),
            "evidence_authority": "UNTRUSTED_WEB_EVIDENCE", "order_authority": False}


def valid_scheduled_attempt(**overrides: Any) -> dict[str, Any]:
    from validation_common import canonical_hash, load_json

    completed_session = str(overrides.get("completed_session") or "2026-08-12")
    provider_scope_hash = canonical_hash(load_json(
        ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json"
    ))
    critical_bars = {
        ticker: {
            "market_session_type": "REGULAR_COMPLETED", "reported_session": completed_session,
            "price_basis": "RAW_REGULAR_SESSION_CLOSE", "quote_type": "RAW_REGULAR_SESSION_CLOSE",
            "currency": "USD", "bar_finalized": True, "stable": True,
            "regular_close_provider": "KIWOOM_REST",
            "technical_history_provider": (
                "YFINANCE_PRIMARY_VALIDATED_FALLBACK" if ticker == "FSLY"
                else "KIWOOM_ADJUSTED_LOCAL_DETERMINISTIC"
            ),
            "blocked_decision_classes": ["EMA10_RECLAIM_RVOL20"] if ticker == "MVLL" else [],
        }
        for ticker in ("SOXL", "MVLL", "NBIS", "BE", "TOST", "NOW", "FSLY")
    }
    value = {
        "attempt_id": "scheduled-2026-08-12-a", "attempt_type": "SCHEDULED_POST_MARKET",
        "run_phase": "POST_MARKET_FINALIZED", "automation_name": "Morning Portfolio Strategy",
        "attempted_at": "2026-08-13T00:00:00Z", "completed_session": completed_session,
        "official_session_status": "VALIDATED", "expected_scheduled_session": True,
        "historical_backfill": False, "delivery_status": "DELIVERED", "delivery_id": "delivery-1",
        "git_commit": "a" * 40, "branch": "main", "working_tree_clean": True,
        "deployment_status": "PASS", "registry_status": "VALIDATED",
        "finalization_evidence": {"schema_version": "1.0", "run_phase": "POST_MARKET_FINALIZED",
            "analysis_run_phase": "POST_MARKET", "completed_session": completed_session,
            "official_session_status": "VALIDATED", "finalization_status": "VALIDATED",
            "all_critical_bars_finalized": True, "critical_bars": critical_bars,
            "extended_hours_records_separate": True,
            "provider_readiness_status": "KIWOOM_PRIMARY_GUARDED_SCOPED_READY",
            "event_readiness_status": "CLEAR", "provider_scope_manifest_hash": provider_scope_hash,
            "order_authority": False},
        "run_manifest_hash": "b" * 64, "report_hash": "c" * 64,
        "portfolio_hash_before": "d" * 64, "portfolio_hash_after": "d" * 64,
        "baseline_coverage": {ticker: "VALIDATED_SHADOW" for ticker in ("NBIS", "MVLL", "SOXL")},
        "independent_price_coverage": {"status": "NOT_REQUIRED"}, "price_evidence_queue_status": "NOT_REQUIRED",
        "live_strategy_hash": "e" * 64, "shadow_strategy_hash": "f" * 64,
        "report": {"final_conclusion": "NO_TRADE", "order_authority": False,
                   "leveraged_separation": {"SOXL": {"confirmation_mode": "DIRECTION_ONLY", "product_close_substitution": False,
                                                        "proxy_times_multiple_used_as_direct_validation": False},
                                              "MVLL": {"confirmation_mode": "DAILY_MULTIPLE", "product_close_substitution": False,
                                                       "underlying_used_as_product_close": False}},
                   "price_evidence": {"shadow_crosscheck_status": "NOT_REQUIRED", "live_execution_upgraded": False}},
    }
    value.update(overrides)
    return value
