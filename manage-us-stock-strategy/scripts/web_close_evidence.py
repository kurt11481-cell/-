#!/usr/bin/env python3
"""Validate untrusted Codex Web close evidence, then compare in Shadow only."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from math import isfinite
from typing import Any
from urllib.parse import parse_qsl, urlparse

from price_evidence import compare_close


YAHOO_DOMAINS = {"finance.yahoo.com", "query1.finance.yahoo.com", "query2.finance.yahoo.com"}
SECRET_QUERY_KEYS = {"token", "access_token", "api_key", "apikey", "key", "cookie", "session", "password", "otp"}


def normalize_extracted_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", normalized).strip()


def extracted_text_sha256(value: str) -> str:
    return hashlib.sha256(normalize_extracted_text(value).encode("utf-8")).hexdigest()


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().split(":", 1)[0].removeprefix("www.")


def _credential_leak(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        return True
    return any(key.lower() in SECRET_QUERY_KEYS for key, _ in parse_qsl(parsed.query, keep_blank_values=True))


def _approved_route(record: dict[str, Any], policy: dict[str, Any]) -> bool:
    final_url = str(record.get("final_source_url") or "")
    domain = _domain(final_url)
    for route in policy.get("approved_routes") or []:
        if route.get("status") != "SHADOW_APPROVED":
            continue
        if route.get("source_domain") != domain or route.get("source_type") != record.get("source_type"):
            continue
        prefix = str(route.get("url_prefix") or "")
        if not prefix or final_url.startswith(prefix):
            return True
    return False


def validate_raw_web_evidence(record: dict[str, Any], queue_item: dict[str, Any],
                              policy: dict[str, Any], *, analysis_cutoff: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    inconclusive: list[str] = []
    required = (
        "queue_item_id", "ticker", "security_name", "reported_session", "reported_close", "currency",
        "price_basis", "provider", "source_url", "final_source_url", "source_domain", "source_type",
        "source_title", "source_field_label", "retrieved_at", "source_timestamp", "acquisition_method",
        "is_search_snippet", "is_yahoo_origin", "security_identity_match_claim",
        "regular_session_close_claim", "extracted_text", "evidence_authority",
    )
    for field in required:
        if record.get(field) in {None, ""}:
            inconclusive.append(f"MISSING_{field.upper()}")
    if record.get("queue_item_id") != (queue_item.get("queue_item_id") or queue_item.get("request_id")):
        errors.append("QUEUE_ITEM_MISMATCH")
    if record.get("ticker") != queue_item.get("ticker"):
        errors.append("IDENTITY_MISMATCH")
    if record.get("reported_session") not in {None, ""} and record.get("reported_session") != queue_item.get("completed_session"):
        errors.append("SESSION_MISMATCH")
    if record.get("currency") != "USD" or queue_item.get("currency", "USD") != "USD":
        errors.append("CURRENCY_MISMATCH")
    if record.get("acquisition_method") != "CODEX_WEB":
        errors.append("ACQUISITION_METHOD_INVALID")
    if record.get("evidence_authority") != "UNTRUSTED_WEB_EVIDENCE":
        errors.append("EVIDENCE_AUTHORITY_INVALID")
    if record.get("is_search_snippet") is not False:
        errors.append("SEARCH_RESULT_SNIPPET_REJECTED")
    if record.get("security_identity_match_claim") is not True:
        errors.append("SECURITY_IDENTITY_NOT_EXPLICIT")
    if record.get("regular_session_close_claim") is not True:
        errors.append("REGULAR_SESSION_CLOSE_NOT_EXPLICIT")
    urls = [str(record.get("source_url") or ""), str(record.get("final_source_url") or "")]
    if any(urlparse(url).scheme != "https" for url in urls):
        errors.append("SOURCE_URL_NOT_HTTPS")
    if any(_credential_leak(url) for url in urls):
        errors.append("CREDENTIAL_LEAK_IN_URL")
    final_domain = _domain(urls[1])
    claimed_domain = str(record.get("source_domain") or "").lower().removeprefix("www.")
    if final_domain != claimed_domain:
        errors.append("SOURCE_DOMAIN_URL_MISMATCH")
    if final_domain in YAHOO_DOMAINS or record.get("is_yahoo_origin") is not False:
        errors.append("YAHOO_ORIGIN_NOT_INDEPENDENT")
    if record.get("source_type") in (policy.get("rejected_source_types") or []):
        errors.append("SOURCE_TYPE_REJECTED")
    if not _approved_route(record, policy):
        inconclusive.append("SOURCE_ROUTE_PENDING_REVIEW")
    basis = record.get("price_basis")
    if basis in (policy.get("rejected_price_bases") or []):
        errors.append("PRICE_BASIS_REJECTED")
    elif basis in (policy.get("inconclusive_price_bases") or []) or basis in (policy.get("conditional_price_bases") or []):
        inconclusive.append("PRICE_BASIS_INCONCLUSIVE")
    elif basis not in (policy.get("eligible_price_bases") or []):
        inconclusive.append("PRICE_BASIS_UNKNOWN")
    close = record.get("reported_close")
    if not isinstance(close, (int, float)) or isinstance(close, bool) or not isfinite(float(close)) or float(close) <= 0:
        errors.append("REPORTED_CLOSE_INVALID")
    expected_hash = extracted_text_sha256(str(record.get("extracted_text") or ""))
    if record.get("extracted_text_sha256") != expected_hash:
        errors.append("EXTRACTED_TEXT_HASH_MISMATCH")
    try:
        source_time = datetime.fromisoformat(str(record.get("source_timestamp")).replace("Z", "+00:00"))
        retrieved = datetime.fromisoformat(str(record.get("retrieved_at")).replace("Z", "+00:00"))
        if source_time > retrieved:
            errors.append("SOURCE_TIMESTAMP_AFTER_RETRIEVAL")
        if analysis_cutoff:
            cutoff = datetime.fromisoformat(analysis_cutoff.replace("Z", "+00:00"))
            if source_time > cutoff:
                errors.append("FUTURE_KNOWN_EVIDENCE")
    except (TypeError, ValueError):
        inconclusive.append("SOURCE_OR_RETRIEVAL_TIMESTAMP_INVALID")
    status = "REJECTED" if errors else ("INCONCLUSIVE" if inconclusive else "VALIDATED")
    return {
        "evidence_validation_status": status,
        "computed_extracted_text_sha256": expected_hash,
        "source_route_status": "SHADOW_APPROVED" if _approved_route(record, policy) else "SOURCE_ROUTE_PENDING_REVIEW",
        "errors": list(dict.fromkeys(errors)), "inconclusive_reasons": list(dict.fromkeys(inconclusive)),
        "comparison_status": "NOT_EVALUATED", "order_authority": False,
    }


def _primary_basis_to_v26(value: str) -> str:
    return "RAW_REGULAR_SESSION_CLOSE" if value in {"raw_completed_regular_session_close", "RAW_REGULAR_SESSION_CLOSE"} else value


def resolve_shadow_close(queue_item: dict[str, Any], record: dict[str, Any], policy: dict[str, Any],
                         *, current_live_crosscheck_status: str = "PENDING",
                         current_execution_state: str = "VERIFICATION_PENDING",
                         analysis_cutoff: str | None = None) -> dict[str, Any]:
    validation = validate_raw_web_evidence(record, queue_item, policy, analysis_cutoff=analysis_cutoff)
    result = {
        **validation, "queue_item_id": queue_item.get("queue_item_id") or queue_item.get("request_id"),
        "ticker": queue_item.get("ticker"), "live_crosscheck_status": current_live_crosscheck_status,
        "shadow_crosscheck_status": "INCONCLUSIVE", "shadow_only": True,
        "execution_state": current_execution_state, "quantity": None, "order_authority": False,
    }
    if validation["evidence_validation_status"] != "VALIDATED":
        return result
    primary = {
        "ticker": queue_item["ticker"], "primary_session": queue_item["completed_session"],
        "primary_close": queue_item["primary_close"],
        "primary_price_basis": _primary_basis_to_v26(queue_item.get("primary_price_basis") or queue_item.get("price_basis")),
        "currency": queue_item.get("currency", "USD"), "primary_provider": "yfinance",
    }
    independent = {
        "ticker": record["ticker"], "reported_session": record["reported_session"],
        "reported_close": record["reported_close"], "currency": record["currency"],
        "price_basis": record["price_basis"], "provider": record["provider"],
        "source_url": record["final_source_url"], "source_domain": record["source_domain"],
        "source_type": record["source_type"], "source_timestamp": record["source_timestamp"],
        "retrieved_at": record["retrieved_at"], "acquisition_method": "CODEX_WEB",
        "content_hash": validation["computed_extracted_text_sha256"], "security_identity_explicit": True,
        "regular_session_close_explicit": True, "is_search_result_snippet": False, "order_authority": False,
    }
    comparison = compare_close(primary, independent, queue_item.get("decision_boundaries") or [],
                               policy.get("approved_direct_close_tolerance"))
    shadow_status = comparison["comparison_status"]
    result.update(comparison)
    result["live_crosscheck_status"] = current_live_crosscheck_status
    result["shadow_crosscheck_status"] = shadow_status
    result["shadow_only"] = True
    result["execution_state"] = current_execution_state
    result["quantity"] = None
    result["order_authority"] = False
    return result
