#!/usr/bin/env python3
"""Deterministic gates for finalized post-market delivery and Shadow counting."""

from __future__ import annotations

from typing import Any, Iterable

from validation_common import canonical_hash


FINALIZED_RUN_PHASE = "POST_MARKET_FINALIZED"
PRELIMINARY_RUN_PHASE = "POST_MARKET_PRELIMINARY"
ANALYSIS_RUN_PHASE = "POST_MARKET"


def validate_finalization_evidence(evidence: dict[str, Any] | None,
                                   completed_session: str | None) -> list[str]:
    errors: list[str] = []
    value = evidence or {}
    if value.get("run_phase") != FINALIZED_RUN_PHASE:
        errors.append("FINALIZED_RUN_PHASE_REQUIRED")
    if value.get("analysis_run_phase") != ANALYSIS_RUN_PHASE:
        errors.append("POST_MARKET_ANALYSIS_PHASE_REQUIRED")
    if value.get("completed_session") != completed_session or not completed_session:
        errors.append("FINALIZED_SESSION_MISMATCH")
    if value.get("official_session_status") != "VALIDATED":
        errors.append("OFFICIAL_SESSION_NOT_VALIDATED")
    if value.get("finalization_status") != "VALIDATED":
        errors.append(str(value.get("finalization_status") or "FINALIZATION_STATUS_MISSING"))
    if value.get("all_critical_bars_finalized") is not True:
        errors.append("CRITICAL_BARS_NOT_FINALIZED")
    if value.get("extended_hours_records_separate") is not True:
        errors.append("EXTENDED_HOURS_NOT_SEPARATED")
    if value.get("provider_readiness_status") == "DATA_INCOMPLETE":
        errors.append("PROVIDER_READINESS_INCOMPLETE")
    if value.get("event_readiness_status") == "EVENT_DATA_INCOMPLETE":
        errors.append("EVENT_READINESS_NOT_NORMALIZED")
    if value.get("order_authority") is not False:
        errors.append("ORDER_AUTHORITY_NOT_FALSE")
    bars = value.get("critical_bars") or {}
    if not isinstance(bars, dict) or not bars:
        errors.append("CRITICAL_BARS_MISSING")
        return list(dict.fromkeys(errors))
    for ticker, bar in bars.items():
        if not isinstance(bar, dict):
            errors.append(f"CRITICAL_BAR_INVALID:{ticker}")
            continue
        if bar.get("market_session_type") != "REGULAR_COMPLETED":
            errors.append(f"NON_REGULAR_COMPLETED_BAR:{ticker}")
        if bar.get("reported_session") != completed_session:
            errors.append(f"BAR_SESSION_MISMATCH:{ticker}")
        if bar.get("price_basis") != "RAW_REGULAR_SESSION_CLOSE":
            errors.append(f"PRICE_BASIS_MISMATCH:{ticker}")
        if bar.get("quote_type") != "RAW_REGULAR_SESSION_CLOSE":
            errors.append(f"QUOTE_TYPE_MISMATCH:{ticker}")
        if bar.get("currency") != "USD":
            errors.append(f"CURRENCY_MISMATCH:{ticker}")
        if bar.get("bar_finalized") is not True:
            errors.append(f"BAR_NOT_FINALIZED:{ticker}")
        if bar.get("stable") is not True:
            errors.append(f"BAR_NOT_STABLE:{ticker}")
    return list(dict.fromkeys(errors))


def validate_scoped_provider_limits(provider_policy: dict[str, Any],
                                    evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if evidence.get("provider_scope_manifest_hash") != canonical_hash(provider_policy):
        errors.append("PROVIDER_SCOPE_MANIFEST_HASH_MISMATCH")
    scopes = provider_policy.get("ticker_scope_rules") or {}
    fsly = scopes.get("FSLY") or {}
    mvll = scopes.get("MVLL") or {}
    if fsly.get("technical_history_primary") != "YFINANCE_PRIMARY_VALIDATED_FALLBACK":
        errors.append("FSLY_FALLBACK_SCOPE_CHANGED")
    if fsly.get("history_merge_prohibited") is not True:
        errors.append("FSLY_HISTORY_MERGE_NOT_PROHIBITED")
    if fsly.get("minimum_history_reduction_prohibited") is not True:
        errors.append("FSLY_MINIMUM_HISTORY_REDUCTION_NOT_PROHIBITED")
    if "EMA10_RECLAIM_RVOL20" not in (mvll.get("blocked_decision_classes") or []):
        errors.append("MVLL_DECISION_CLASS_BLOCK_MISSING")
    bars = evidence.get("critical_bars") or {}
    if "FSLY" in bars and bars["FSLY"].get("technical_history_provider") != "YFINANCE_PRIMARY_VALIDATED_FALLBACK":
        errors.append("FSLY_FALLBACK_NOT_APPLIED")
    if "MVLL" in bars and "EMA10_RECLAIM_RVOL20" not in (bars["MVLL"].get("blocked_decision_classes") or []):
        errors.append("MVLL_DECISION_CLASS_NOT_ISOLATED")
    return list(dict.fromkeys(errors))


def event_and_provider_readiness(provider_status: str, event_status: str) -> dict[str, str]:
    return {
        "provider_readiness_status": provider_status,
        "event_readiness_status": (
            "EVENT_REVIEW_PENDING" if event_status in {"EVENT_DATA_INCOMPLETE", "INCOMPLETE"}
            else event_status
        ),
    }


def delivery_eligible(*, success: bool, run_phase: str,
                      finalization_status: str | None,
                      all_critical_bars_finalized: bool | None,
                      output_artifact: str | None,
                      delivery_id: str | None,
                      portfolio_hash_before: str,
                      portfolio_hash_after: str,
                      actual_scheduled_run: bool) -> bool:
    return bool(
        success
        and run_phase == FINALIZED_RUN_PHASE
        and finalization_status == "VALIDATED"
        and all_critical_bars_finalized is True
        and output_artifact
        and delivery_id
        and portfolio_hash_before == portfolio_hash_after
        and actual_scheduled_run
    )


def urgent_state_fingerprint(notification: dict[str, Any]) -> str:
    """Phase-neutral signal identity prevents preliminary/final duplicate urgency."""
    return canonical_hash({
        "ticker": notification.get("ticker"),
        "event_type": notification.get("event_type"),
        "strategy_state": notification.get("strategy_state"),
        "opportunity_state": notification.get("opportunity_state"),
        "signal_fingerprint": notification.get("signal_fingerprint"),
    })


def suppress_duplicate_urgent(existing: Iterable[dict[str, Any]],
                              candidate: dict[str, Any]) -> bool:
    fingerprint = urgent_state_fingerprint(candidate)
    return any(urgent_state_fingerprint(item) == fingerprint for item in existing)
