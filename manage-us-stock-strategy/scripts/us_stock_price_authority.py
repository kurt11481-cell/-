#!/usr/bin/env python3
"""Deterministic U.S. stock price authority with Kiwoom execution priority.

Cross-provider divergence is diagnostic only.  Kiwoom remains fail-closed
against its own identity, session, semantics, freshness, API, currency, scale,
and corporate-action integrity gates.  This module never grants quantity or
order authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from typing import Any

from validation_common import canonical_hash


KNOWN_MARKET_PHASES = {
    "DAY_MARKET", "PRE_MARKET", "REGULAR", "AFTER_MARKET",
    "COMPLETED_DAILY", "MARKET_CLOSED", "OVERNIGHT",
}
KNOWN_PRICE_SEMANTICS = {
    "CURRENT_PRICE", "DAY_MARKET_CURRENT", "PREMARKET_CURRENT",
    "REGULAR_CURRENT", "AFTERMARKET_CURRENT", "COMPLETED_DAILY_CLOSE",
}


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def validate_kiwoom_self_integrity(record: dict[str, Any]) -> dict[str, Any]:
    """Validate Kiwoom independently of yfinance or Web reference prices."""
    errors: list[str] = []
    ticker = record.get("ticker")
    if not isinstance(ticker, str) or ticker != record.get("requested_ticker"):
        errors.append("KIWOOM_WRONG_TICKER")
    if record.get("security_identity_status") != "VERIFIED":
        errors.append("KIWOOM_SECURITY_IDENTITY_MISMATCH")
    if record.get("currency") != "USD" or record.get("fx_applied") is not False:
        errors.append("KIWOOM_SCALE_OR_CURRENCY_ERROR")
    if not _positive_number(record.get("canonical_price")):
        errors.append("KIWOOM_DATA_MISSING")
    if record.get("api_status") != "SUCCESS":
        errors.append("KIWOOM_API_ERROR")
    if not _valid_timestamp(record.get("retrieval_timestamp")):
        errors.append("KIWOOM_TIMESTAMP_INVALID")
    if record.get("market_phase") not in KNOWN_MARKET_PHASES:
        errors.append("KIWOOM_UNKNOWN_MARKET_PHASE")
    if record.get("price_semantics") not in KNOWN_PRICE_SEMANTICS:
        errors.append("KIWOOM_UNKNOWN_PRICE_SEMANTICS")
    if record.get("stale_record") is not False:
        errors.append("KIWOOM_STALE")
    if record.get("corporate_action_ambiguity") is not False:
        errors.append("KIWOOM_CORPORATE_ACTION_AMBIGUITY")
    if record.get("scale_error") is not False:
        errors.append("KIWOOM_SCALE_OR_CURRENCY_ERROR")

    if record.get("price_semantics") == "COMPLETED_DAILY_CLOSE":
        if record.get("market_phase") != "COMPLETED_DAILY":
            errors.append("KIWOOM_COMPLETED_CLOSE_PHASE_MISMATCH")
        if record.get("source_api_id") != "usa06012":
            errors.append("KIWOOM_COMPLETED_CLOSE_API_MISMATCH")
        if record.get("source_field") != "result_list.cur_prc":
            errors.append("KIWOOM_COMPLETED_CLOSE_FIELD_MISMATCH")
        if record.get("bar_finalized") is not True:
            errors.append("KIWOOM_COMPLETED_CLOSE_NOT_FINALIZED")
        if record.get("returned_row_date") != record.get("target_session"):
            errors.append("KIWOOM_COMPLETED_CLOSE_SESSION_MISMATCH")
        request = record.get("request_parameters") or {}
        expected = {
            "stk_cd": ticker,
            "strt_dt": str(record.get("target_session", "")).replace("-", ""),
            "upd_stkpc_tp": "0",
            "exrt_appl_tp": "0",
        }
        for field, expected_value in expected.items():
            if request.get(field) != expected_value:
                errors.append(f"KIWOOM_REQUEST_PARAMETER_MISMATCH:{field}")

    return {
        "status": "KIWOOM_PRICE_VALIDATED" if not errors else "KIWOOM_PRIMARY_INVALID",
        "blocking": bool(errors),
        "errors": list(dict.fromkeys(errors)),
        "order_authority": False,
    }


def build_us_stock_price_authority(
    kiwoom_record: dict[str, Any], *,
    yfinance_reference: float | None,
    external_reference: float | None,
    authority_policy_version: str,
    generated_at: str,
) -> dict[str, Any]:
    """Build an immutable authority decision without averaging providers."""
    integrity = validate_kiwoom_self_integrity(kiwoom_record)
    canonical = kiwoom_record.get("canonical_price")
    diagnostics: dict[str, Any] = {
        "yfinance_role": "DIAGNOSTIC_SHADOW",
        "yfinance_reference_price": yfinance_reference,
        "external_reference_role": "EXTERNAL_DIAGNOSTIC_REFERENCE",
        "external_reference_price": external_reference,
        "cross_provider_divergence": False,
        "cross_provider_difference_abs": None,
        "cross_provider_difference_fraction": None,
        "cross_provider_difference_pct": None,
        "divergence_blocking": False,
        "provider_price_averaged": False,
    }
    if _positive_number(canonical) and _positive_number(yfinance_reference):
        difference = Decimal(str(canonical)) - Decimal(str(yfinance_reference))
        fraction = difference / Decimal(str(yfinance_reference))
        diagnostics.update({
            "cross_provider_divergence": difference != 0,
            "cross_provider_difference_abs": float(abs(difference)),
            "cross_provider_difference_fraction": float(abs(fraction)),
            "cross_provider_difference_pct": float(abs(fraction) * Decimal("100")),
        })
    result = {
        "schema_version": "1.0",
        "authority_policy_version": authority_policy_version,
        "ticker": kiwoom_record.get("ticker"),
        "security_identity": kiwoom_record.get("security_identity"),
        "canonical_provider": "KIWOOM_REST",
        "canonical_provider_role": "OPERATIONAL_EXECUTION_PRIMARY",
        "canonical_price": canonical,
        "currency": kiwoom_record.get("currency"),
        "target_session": kiwoom_record.get("target_session"),
        "market_phase": kiwoom_record.get("market_phase"),
        "price_semantics": kiwoom_record.get("price_semantics"),
        "price_basis": kiwoom_record.get("price_basis"),
        "source_api_id": kiwoom_record.get("source_api_id"),
        "source_endpoint": kiwoom_record.get("source_endpoint"),
        "source_field": kiwoom_record.get("source_field"),
        "retrieval_timestamp": kiwoom_record.get("retrieval_timestamp"),
        "retrieval_market_phase": kiwoom_record.get("retrieval_market_phase"),
        "request_parameters": deepcopy(kiwoom_record.get("request_parameters") or {}),
        "returned_row_date": kiwoom_record.get("returned_row_date"),
        "self_integrity": integrity,
        "price_evidence_status": "VALID" if not integrity["blocking"] else "INVALID",
        "comparison_status": (
            "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE"
            if diagnostics["cross_provider_divergence"]
            else "DIAGNOSTIC_MATCH"
        ),
        "diagnostics": diagnostics,
        "blocking": bool(integrity["blocking"]),
        "generated_at": generated_at,
        "quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
        "evidence_hash": "0" * 64,
    }
    result["evidence_hash"] = canonical_hash({k: v for k, v in result.items() if k != "evidence_hash"})
    return result


def validate_price_authority_artifact(record: dict[str, Any]) -> list[str]:
    """Revalidate a persisted authority artifact without trusting its status."""
    errors: list[str] = []
    if record.get("canonical_provider") != "KIWOOM_REST":
        errors.append("CANONICAL_PROVIDER_NOT_KIWOOM")
    if record.get("diagnostics", {}).get("divergence_blocking") is not False:
        errors.append("DIAGNOSTIC_DIVERGENCE_BLOCKING_PROHIBITED")
    if record.get("diagnostics", {}).get("provider_price_averaged") is not False:
        errors.append("PROVIDER_PRICE_AVERAGING_PROHIBITED")
    if record.get("quantity") is not None or record.get("quantity_authority") != "none":
        errors.append("QUANTITY_AUTHORITY_PROHIBITED")
    if record.get("order_authority") is not False:
        errors.append("ORDER_AUTHORITY_PROHIBITED")
    local_hash = canonical_hash({k: v for k, v in record.items() if k != "evidence_hash"})
    if record.get("evidence_hash") != local_hash:
        errors.append("PRICE_AUTHORITY_HASH_MISMATCH")
    if record.get("self_integrity", {}).get("status") != "KIWOOM_PRICE_VALIDATED":
        errors.append("KIWOOM_SELF_INTEGRITY_NOT_VALIDATED")
    if record.get("blocking") is not False:
        errors.append("PRICE_AUTHORITY_BLOCKED")
    return errors
