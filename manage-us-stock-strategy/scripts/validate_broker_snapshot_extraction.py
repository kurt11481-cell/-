#!/usr/bin/env python3
"""Validate structured broker extraction; no OCR or portfolio mutation occurs here."""

from __future__ import annotations

from typing import Any


def validate_extraction(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("authority_state") != "EXTRACTED_PENDING_USER_CONFIRMATION":
        errors.append("AUTHORITY_STATE_INVALID")
    if value.get("sensitive_login_or_otp_visible") is True:
        errors.append("SENSITIVE_LOGIN_OR_OTP_REUPLOAD_REQUIRED")
    account = str(value.get("account_id_masked") or "")
    if len(account) != 8 or not account.startswith("****") or not account[4:].isdigit():
        errors.append("ACCOUNT_ID_NOT_MASKED")
    scope = value.get("scope")
    if value.get("cash_status") == "VERIFIED_AVAILABLE" and value.get("cash_classification") != "AVAILABLE_SETTLED":
        errors.append("NON_SETTLED_OR_MARGIN_CASH_CANNOT_BECOME_AVAILABLE_CASH")
    positions = value.get("positions") or []
    symbols: set[str] = set()
    for item in positions:
        symbol = item.get("ticker")
        if not isinstance(symbol, str) or not symbol or symbol in symbols:
            errors.append("POSITION_TICKER_INVALID_OR_DUPLICATE")
        symbols.add(symbol)
        if not isinstance(item.get("quantity"), int) or item.get("quantity") < 0:
            errors.append(f"{symbol or 'UNKNOWN'}_QUANTITY_INVALID")
        if "market_evidence_close" in item or "hard_risk_close" in item:
            errors.append(f"{symbol or 'UNKNOWN'}_BROKER_PRICE_ENTERED_MARKET_EVIDENCE")
    if scope == "POSITION_ONLY" and value.get("holdings_complete_status") == "VERIFIED":
        errors.append("POSITION_ONLY_CANNOT_VERIFY_HOLDINGS_COMPLETE")
    if scope == "CASH_ONLY" and value.get("holdings_complete_status") == "VERIFIED":
        errors.append("CASH_ONLY_CANNOT_VERIFY_HOLDINGS")
    if scope == "HOLDINGS_ONLY" and value.get("cash_status") == "VERIFIED_AVAILABLE":
        errors.append("HOLDINGS_ONLY_CANNOT_VERIFY_CASH")
    if scope == "FULL_PORTFOLIO":
        if value.get("account_scope_complete") is not True:
            errors.append("FULL_PORTFOLIO_ACCOUNT_SCOPE_INCOMPLETE")
        if value.get("holdings_complete_status") != "VERIFIED":
            errors.append("FULL_PORTFOLIO_HOLDINGS_INCOMPLETE")
        if value.get("cash_status") != "VERIFIED_AVAILABLE":
            errors.append("FULL_PORTFOLIO_CASH_UNVERIFIED")
        if value.get("capture_date_status") != "VERIFIED":
            errors.append("FULL_PORTFOLIO_CAPTURE_DATE_UNVERIFIED")
    return list(dict.fromkeys(errors))
