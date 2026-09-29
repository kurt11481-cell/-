#!/usr/bin/env python3
"""User-initiated, read-only M1 manual portfolio preflight.

This adapter may read Kiwoom account and market evidence and may create one
immutable report. It has no holding-strategy, delivery, cohort, counter,
canonical-portfolio, policy, quantity, or order capability.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import math
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from continuous_improvement_sidecar import derive_run_provenance
from integrated_authority_snapshot import (
    COMBINED_ACTIVATION_RELATIVE_PATH,
    IntegratedAuthoritySnapshot,
    derive_us_market_session_authority_from_snapshot,
    load_integrated_authority_snapshot,
    resolve_instrument_identity_from_snapshot,
)
from instrument_identity_authority import resolve_instrument_identity
from kiwoom_account_readonly_bridge import SAFE_FAILURE_STATUSES, _sanitize, invoke_account_bridge_batch
from kiwoom_broker_shadow import normalize_snapshot
from kiwoom_runtime_bridge import invoke_bridge_batch
from session_aware_market_data import (
    ET,
    kiwoom_broker_quote_observation,
    kiwoom_daily_observation,
    market_session_at,
)
from session_authority import derive_us_market_session_authority
from validation_common import canonical_hash, file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_READ_OPERATIONS = (
    "account_deposit_read",
    "account_deposit_detail_read",
    "account_holdings_read",
    "account_open_items",
    "account_fills_read",
    "account_realized_pnl_read",
)
MARKET_READ_OPERATIONS = ("oauth_health", "market_quote", "daily_chart")
MANUAL_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}")
APPROVED_FINALIZATION_BASIS = "NEXT_ET_CALENDAR_DAY_PROVIDER_ARCHIVE"
AccountReader = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
MarketReader = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return parsed


def _number(value: Any, *, positive: bool = False) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        return None
    return result


def _cur_prc_price(value: Any) -> float | None:
    """Normalize the Kiwoom cur_prc sign prefix to a positive price."""
    if value is None or isinstance(value, bool):
        return None
    match = re.fullmatch(r"[+-]?(\d+(?:\.\d+)?)", str(value))
    if match is None:
        return None
    return _number(match.group(1), positive=True)


def _ticker(value: Any) -> str | None:
    result = str(value or "").strip().upper()
    return result if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", result) else None


def generate_manual_run_id(now: datetime | None = None) -> str:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return f"manual-{current.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:12]}"


def validate_manual_run_id(manual_run_id: str) -> str:
    value = str(manual_run_id)
    if MANUAL_RUN_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("INVALID_MANUAL_RUN_ID")
    return value


def _candidate_session_fields_match(
    raw: dict[str, Any], *, reported_session: str,
    provider_observed: datetime,
) -> bool:
    for field in ("bar_date", "completed_session", "expected_us_session_date", "us_session_date"):
        value = raw.get(field)
        if value is not None and value != reported_session:
            return False
    exchange_timestamp = raw.get("exchange_timestamp")
    if exchange_timestamp is not None:
        try:
            exchange_observed = _timestamp(str(exchange_timestamp))
        except ValueError:
            return False
        if exchange_observed.astimezone(ET).date().isoformat() != reported_session:
            return False
        if exchange_observed > provider_observed:
            return False
    return provider_observed.astimezone(ET).date().isoformat() > reported_session


def _select_last_verified_finalized_bar(
    rows: list[dict[str, Any]], *, observed_at: str,
    expected_ticker: str,
    expected_completed_session: str | None,
) -> dict[str, Any]:
    """Validate candidates against an expected session resolved upstream."""
    observed = _timestamp(observed_at)
    observed_et_date = observed.astimezone(ET).date().isoformat()
    ticker = _ticker(expected_ticker)
    expected_session = expected_completed_session
    if ticker is None or expected_session is None:
        return {
            "status": "NOT_VERIFIED",
            "bar_date": None,
            "bar": None,
            "technical_authority": False,
            "reason": "EXPECTED_IDENTITY_OR_SESSION_NOT_VERIFIED",
        }
    accepted: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        reported_session = str(raw.get("reported_session") or "")
        provider_timestamp = str(raw.get("provider_timestamp") or "")
        try:
            provider_observed = _timestamp(provider_timestamp)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", reported_session) is None:
                continue
            date.fromisoformat(reported_session)
        except ValueError:
            continue
        checks = (
            _ticker(raw.get("ticker")) == ticker,
            reported_session == expected_session,
            raw.get("provider") == "KIWOOM_REST",
            raw.get("source_identifier") == "usa06012:/api/us/chart",
            raw.get("source_field") == "result_list.cur_prc",
            raw.get("session_classification_basis") == APPROVED_FINALIZATION_BASIS,
            raw.get("security_identity_status") == "VERIFIED",
            raw.get("market_session_type") == "REGULAR_COMPLETED",
            raw.get("price_basis") == "RAW_REGULAR_SESSION_CLOSE",
            raw.get("quote_type") == "REGULAR_SESSION_LAST",
            raw.get("currency") == "USD",
            raw.get("bar_finalized") is True,
            raw.get("stable") is True,
            raw.get("comparable_to_regular_close") is True,
            raw.get("daily_indicator_authority") is True,
            raw.get("hard_risk_authority") is True,
            raw.get("indicative_only") is False,
            raw.get("order_authority") is False,
            _number(raw.get("price"), positive=True) is not None,
            reported_session < observed_et_date,
            provider_observed <= observed,
            _candidate_session_fields_match(
                raw,
                reported_session=reported_session,
                provider_observed=provider_observed,
            ),
        )
        if all(checks):
            accepted.append(dict(raw))
    if not accepted:
        return {
            "status": "NOT_VERIFIED",
            "bar_date": None,
            "bar": None,
            "technical_authority": False,
            "reason": "NO_INDEPENDENTLY_VERIFIED_FINALIZED_BAR",
        }
    selected = max(accepted, key=lambda item: str(item["reported_session"]))
    return {
        "status": "VERIFIED",
        "bar_date": selected["reported_session"],
        "bar": selected,
        "technical_authority": True,
        "reason": None,
    }


def select_last_verified_finalized_bar(
    rows: list[dict[str, Any]], *, observed_at: str,
    expected_ticker: str,
    official_session_evidence: dict[str, Any] | None = None,
    completed_session: str | None = None,
) -> dict[str, Any]:
    """Fail-closed compatibility entrypoint without caller authority.

    Legacy caller session metadata is never accepted as authority. The optional
    arguments remain only to fail closed for compatibility with older callers.
    """
    del rows, observed_at, expected_ticker, official_session_evidence, completed_session
    return {
        "status": "NOT_VERIFIED",
        "bar_date": None,
        "bar": None,
        "technical_authority": False,
        "reason": "LEGACY_SESSION_AUTHORITY_DISABLED",
    }


def _manual_provider_finalization_projection(selected: dict[str, Any]) -> dict[str, Any]:
    """Keep the legacy archive decision out of provider-finalization authority."""
    if selected.get("status") != "VERIFIED":
        return selected
    return {
        "status": "NOT_VERIFIED", "bar_date": None, "bar": None,
        "technical_authority": False,
        "reason": "PROVIDER_FINALIZATION_NOT_VERIFIED",
    }


def _safe_reader_call(
    reader: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    requests: list[dict[str, Any]],
    *, unavailable_status: str,
) -> list[dict[str, Any]]:
    try:
        results = reader(requests)
    except Exception as exc:  # adapters return evidence failures; no fallback is invented
        return [
            {
                "bridge_status": unavailable_status,
                "failure_type": type(exc).__name__,
                "operation": request["operation"],
                "ticker": request.get("ticker"),
                "order_authority": False,
            }
            for request in requests
        ]
    if not isinstance(results, list) or len(results) != len(requests):
        return [
            {
                "bridge_status": unavailable_status,
                "failure_type": "BRIDGE_BATCH_OUTPUT_INVALID",
                "operation": request["operation"],
                "ticker": request.get("ticker"),
                "order_authority": False,
            }
            for request in requests
        ]
    normalized = []
    for request, result in zip(requests, results):
        value = dict(result) if isinstance(result, dict) else {}
        value.setdefault("operation", request["operation"])
        value.setdefault("ticker", request.get("ticker"))
        value["order_authority"] = False
        normalized.append(value)
    return normalized


def _operation_result(
    results: list[dict[str, Any]], operation: str, ticker: str | None = None,
) -> dict[str, Any] | None:
    for result in results:
        if result.get("operation") != operation:
            continue
        if ticker is not None and _ticker(result.get("ticker")) != ticker:
            continue
        return result
    return None


def _normalize_broker_state(
    account_results: list[dict[str, Any]], *, observed_at: str,
    maximum_age_seconds: int,
) -> tuple[dict[str, Any], str]:
    try:
        snapshot = normalize_snapshot(
            account_results,
            snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
            generated_at=observed_at,
            maximum_age_seconds=maximum_age_seconds,
        )
    except Exception:
        snapshot = {
            "broker_snapshot_as_of": None,
            "scope_complete": False,
            "operation_statuses": {},
            "holdings": [],
            "cash": {
                "currency": "USD",
                "withdrawable_cash": None,
                "order_available_cash": None,
                "settled_available_cash": None,
                "cash_status": "UNVERIFIED",
                "projected_proceeds_included": False,
                "margin_or_credit_included": False,
            },
        }
    holdings_result = _operation_result(account_results, "account_holdings_read")
    if holdings_result is None or holdings_result.get("bridge_status") not in {"PASS", "PARTIAL"}:
        broker_status = "UNAVAILABLE"
    elif (
        holdings_result.get("bridge_status") != "PASS"
        or (holdings_result.get("pagination") or {}).get("complete") is not True
    ):
        broker_status = "INCOMPLETE"
    else:
        broker_status = "AVAILABLE"
    open_results = [item for item in account_results if item.get("operation") == "account_open_items"]
    open_evidence = None
    if len(open_results) == 1:
        open_result = open_results[0]
        open_evidence = _sanitize(open_result, "account_open_items")
        # Sanitizing malformed rows must never manufacture verified empty evidence.
        data = open_result.get("data")
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            open_evidence["data"] = None
    # A generated_at fallback is a parent observation, not a Broker data timestamp.
    broker_data_as_of = _acquisition_complete_cutoff([
        result for result in account_results if result.get("bridge_status") in {"PASS", "PARTIAL"}
    ])
    state = {
        "state_type": "BROKER_OBSERVED_STATE",
        "status": broker_status,
        "as_of": broker_data_as_of,
        "scope_complete": snapshot.get("scope_complete") is True,
        "operation_statuses": snapshot.get("operation_statuses") or {},
        "holdings": snapshot.get("holdings") or [],
        "open_order_evidence": open_evidence,
        "cash": snapshot.get("cash") or {},
        "source": "KIWOOM_ACCOUNT_READ_ONLY",
        "canonical_apply": False,
        "portfolio_mutation": False,
        "quantity_authority": "none",
        "order_authority": False,
    }
    return state, broker_status


def _system_portfolio_projection(
    system_portfolio: dict[str, Any], *, source_path: str,
    source_sha256: str,
) -> dict[str, Any]:
    return {
        "state_type": "SYSTEM_PORTFOLIO_STATE",
        "source_path": source_path,
        "source_sha256": source_sha256,
        "state_revision": system_portfolio.get("state_revision"),
        "last_updated_at": system_portfolio.get("last_updated_at"),
        "holdings": dict(system_portfolio.get("holdings") or {}),
        "average_cost_usd": dict(system_portfolio.get("average_cost_usd") or {}),
        "available_cash_usd": _number(system_portfolio.get("available_cash_usd")),
        "portfolio_mutation": False,
        "order_authority": False,
    }


def _maps_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if set(left) != set(right):
        return False
    for key in left:
        left_value = _number(left[key])
        right_value = _number(right[key])
        if left_value is None or right_value is None:
            if left[key] != right[key]:
                return False
        elif not math.isclose(left_value, right_value, rel_tol=1e-9, abs_tol=1e-8):
            return False
    return True


def compare_broker_and_system(
    broker_state: dict[str, Any], system_state: dict[str, Any],
) -> tuple[str, list[str]]:
    if broker_state.get("status") != "AVAILABLE":
        return "UNKNOWN", ["BROKER_HOLDINGS_NOT_COMPLETE"]
    system_holdings = system_state.get("holdings")
    if not isinstance(system_holdings, dict):
        return "UNKNOWN", ["SYSTEM_HOLDINGS_UNAVAILABLE"]
    broker_holdings = {
        item["ticker"]: item.get("held_quantity")
        for item in broker_state.get("holdings", [])
        if isinstance(item, dict) and _ticker(item.get("ticker"))
    }
    differences: list[str] = []
    if not _maps_match(broker_holdings, system_holdings):
        differences.append("HOLDINGS_DIFFER")
    broker_costs = {
        item["ticker"]: item.get("average_cost")
        for item in broker_state.get("holdings", [])
        if isinstance(item, dict) and _ticker(item.get("ticker"))
        and item.get("average_cost") is not None
    }
    system_costs = system_state.get("average_cost_usd") or {}
    if broker_costs and not _maps_match(broker_costs, system_costs):
        differences.append("AVERAGE_COST_DIFFERS")
    broker_cash = _number((broker_state.get("cash") or {}).get("settled_available_cash"))
    system_cash = _number(system_state.get("available_cash_usd"))
    cash_unknown = broker_cash is None or system_cash is None
    if not cash_unknown and not math.isclose(broker_cash, system_cash, rel_tol=1e-9, abs_tol=1e-8):
        differences.append("AVAILABLE_CASH_DIFFERS")
    if differences:
        return "DIFFERENT", differences
    if cash_unknown or (system_costs and set(broker_costs) != set(system_costs)):
        return "UNKNOWN", ["COMPARISON_FIELD_UNAVAILABLE"]
    return "MATCH", []


def _manual_analysis_view(
    broker_state: dict[str, Any], system_state: dict[str, Any],
) -> dict[str, Any]:
    broker_available = broker_state.get("status") == "AVAILABLE"
    if broker_available:
        holdings = {
            item["ticker"]: item.get("held_quantity")
            for item in broker_state.get("holdings", []) if isinstance(item, dict)
        }
        broker_costs = {
            item["ticker"]: item.get("average_cost")
            for item in broker_state.get("holdings", [])
            if isinstance(item, dict) and item.get("average_cost") is not None
        }
        costs = {
            # A missing current Broker cost is unknown, not the historical cost.
            ticker: broker_costs.get(ticker)
            for ticker in holdings
        }
        source = "BROKER_OBSERVED_STATE"
    else:
        holdings = dict(system_state.get("holdings") or {})
        costs = dict(system_state.get("average_cost_usd") or {})
        source = "SYSTEM_PORTFOLIO_STATE_FALLBACK"
    verified_cash = _number((broker_state.get("cash") or {}).get("order_available_cash"))
    return {
        "state_type": "MANUAL_ANALYSIS_VIEW",
        "ephemeral": True,
        "memory_only": True,
        "compatibility_projection": True,
        "holding_source": source,
        "holdings": holdings,
        "average_cost_usd": costs,
        "verified_orderable_cash_usd": verified_cash,
        "expected_sale_proceeds_usd": None,
        "full_holding_analysis_performed": False,
        "portfolio_mutation": False,
        "quantity_authority": "none",
        "execution_quantity": None,
        "order_authority": False,
    }


def _normalize_daily_records(
    response: dict[str, Any] | None, *, ticker: str, observed_at: str,
) -> list[dict[str, Any]]:
    if not response or response.get("bridge_status") != "PASS":
        return []
    if _ticker(response.get("ticker")) != ticker:
        return []
    if (response.get("pagination") or {}).get("api_id") != "usa06012":
        return []
    provider_timestamp = str(response.get("retrieved_at") or observed_at)
    records: list[dict[str, Any]] = []
    for row in response.get("data") or []:
        if not isinstance(row, dict) or re.fullmatch(r"\d{8}", str(row.get("dt") or "")) is None:
            continue
        session = datetime.strptime(str(row["dt"]), "%Y%m%d").date().isoformat()
        price = _number(row.get("cur_prc"), positive=True)
        if price is None:
            continue
        records.append(kiwoom_daily_observation(
            ticker=ticker,
            reported_session=session,
            close=price,
            provider_timestamp=provider_timestamp,
            identity_verified=True,
            official_session_verified=True,
        ))
    return sorted(records, key=lambda item: str(item["reported_session"]))


def _same_scope_raw_bar_coherence(
    captures: list[dict[str, Any]], *, ticker: str, completed_session: str,
) -> str:
    """Compare every consumed, comparable RAW bar by normalized OHLCV."""
    from build_kiwoom_market_snapshot import normalize_series

    bars: list[tuple[float, float, float, float, float]] = []
    session_key = completed_session.replace("-", "")
    for capture in captures:
        requests, responses = capture.get("requests"), capture.get("results")
        if (not isinstance(requests, list) or not isinstance(responses, list)
                or len(requests) != len(responses)
                or capture.get("request_sha256") != canonical_hash(requests)):
            return "NOT_VERIFIED"
        for saved_request, saved_response in zip(requests, responses):
            if not isinstance(saved_request, dict) or not isinstance(saved_response, dict):
                return "NOT_VERIFIED"
            if (saved_request.get("operation") != "daily_chart"
                    or _ticker(saved_request.get("ticker")) != ticker
                    or saved_request.get("completed_session") != completed_session
                    or saved_request.get("price_basis") != "RAW"
                    or saved_request.get("fx_applied") is not False):
                continue
            if saved_response.get("bridge_status") != "PASS":
                continue
            pagination = saved_response.get("pagination")
            if (saved_response.get("operation") != "daily_chart"
                    or _ticker(saved_response.get("ticker")) != ticker
                    or saved_response.get("requested_price_basis") not in (None, "RAW")
                    or saved_response.get("source_provider") not in (None, "KIWOOM_REST")
                    or not isinstance(pagination, dict)
                    or pagination.get("api_id") != "usa06012"
                    or pagination.get("status") != "SUFFICIENT"):
                return "NOT_VERIFIED"
            pages = pagination.get("pages")
            if (not isinstance(pages, list) or not pages
                    or pagination.get("pages_fetched") != len(pages)
                    or any(not isinstance(page, dict) or page.get("api_id") != "usa06012"
                           for page in pages)
                    or [page.get("page_index") for page in pages] != list(range(1, len(pages) + 1))):
                return "NOT_VERIFIED"
            rows = [row for row in saved_response.get("data") or []
                    if isinstance(row, dict) and str(row.get("dt")) == session_key]
            if not rows:
                return "NOT_VERIFIED"
            for row in rows:
                if row.get("upd_stkpc_tp") not in (None, "0", 0):
                    return "NOT_VERIFIED"
                normalized = normalize_series(
                    [row], ticker=ticker, completed_session=completed_session,
                    price_basis="RAW", minimum_history_bars=1,
                )
                if normalized["status"] != "PASS":
                    return "NOT_VERIFIED"
                bar = normalized["bars"][0]
                bars.append(tuple(bar[field] for field in (
                    "open", "high", "low", "close", "volume",
                )))
    return "PASS" if bars and all(bar == bars[0] for bar in bars[1:]) else "NOT_VERIFIED"


def local_regular_bar_coherence(
    response: dict[str, Any] | None, *, request: dict[str, Any],
    captures: list[dict[str, Any]], expected_completed_session: str,
    core_close_at: str, observed_at: str, maximum_age_seconds: int = 900,
) -> dict[str, Any]:
    """Check a consumed RAW bar without asserting provider finalization.

    This calculation has no market access. Its capture argument must come from
    hashed parent bytes; callers must also validate their complete handoff.
    """
    result: dict[str, Any] = {
        "status": "NOT_VERIFIED", "reason": "LOCAL_BAR_EVIDENCE_INCOMPLETE",
        "provider_finalization_verified": "NOT_VERIFIED", "bar": None,
        "input_sha256": None,
    }
    try:
        ticker = _ticker(request.get("ticker"))
        if (ticker is None or request.get("operation") != "daily_chart"
                or request.get("completed_session") != expected_completed_session
                or request.get("price_basis") != "RAW"
                or request.get("fx_applied") is not False):
            return dict(result, status="FAIL", reason="LOCAL_BAR_REQUEST_SCOPE_MISMATCH")
        close_time = _timestamp(core_close_at)
        observed = _timestamp(observed_at)
        if close_time > observed or close_time.astimezone(ET).date().isoformat() != expected_completed_session:
            return dict(result, status="FAIL", reason="LOCAL_BAR_SESSION_TIME_MISMATCH")
        if not isinstance(response, dict) or response.get("bridge_status") != "PASS":
            return result
        if (response.get("operation") != "daily_chart" or _ticker(response.get("ticker")) != ticker
                or response.get("order_authority") is not False
                or response.get("requested_price_basis") not in (None, "RAW")):
            return dict(result, status="FAIL", reason="LOCAL_BAR_RESPONSE_SCOPE_MISMATCH")
        pagination = response.get("pagination")
        if not isinstance(pagination, dict):
            return result
        if pagination.get("api_id") != "usa06012":
            return dict(result, status="FAIL", reason="LOCAL_BAR_API_MISMATCH")
        pages = pagination.get("pages")
        if (pagination.get("status") != "SUFFICIENT" or not isinstance(pages, list)
                or not pages or pagination.get("pages_fetched") != len(pages)
                or any(not isinstance(page, dict) for page in pages)
                or [page.get("page_index") for page in pages] != list(range(1, len(pages) + 1))):
            return result
        retrieved = _timestamp(response.get("retrieved_at"))
        if (retrieved < close_time or retrieved > observed
                or not 0 <= (observed - retrieved).total_seconds() <= maximum_age_seconds):
            return dict(result, status="FAIL", reason="LOCAL_BAR_RETRIEVAL_TIME_INVALID")
        if any(page.get("api_id") != "usa06012"
               or not close_time <= _timestamp(page.get("retrieved_at")) <= retrieved
               for page in pages):
            return dict(result, status="FAIL", reason="LOCAL_BAR_PAGE_BINDING_INVALID")

        matches: list[dict[str, Any]] = []
        for capture in captures:
            requests, responses = capture.get("requests"), capture.get("results")
            if (not isinstance(requests, list) or not isinstance(responses, list)
                    or len(requests) != len(responses)
                    or capture.get("request_sha256") != canonical_hash(requests)):
                return result
            started, ended = _timestamp(capture["started_at"]), _timestamp(capture["observed_at"])
            if not started <= ended <= observed:
                return dict(result, status="FAIL", reason="LOCAL_BAR_CAPTURE_TIME_INVALID")
            for saved_request, saved_response in zip(requests, responses):
                if not isinstance(saved_request, dict) or not isinstance(saved_response, dict):
                    return result
                if (saved_request.get("operation") != "daily_chart"
                        or _ticker(saved_request.get("ticker")) != ticker
                        or saved_request.get("completed_session") != expected_completed_session
                        or saved_request.get("price_basis") != "RAW"
                        or saved_request.get("fx_applied") is not False):
                    continue
                saved = dict(saved_response)
                saved.setdefault("ticker", None)
                saved["order_authority"] = False
                if saved_request == request and saved == response:
                    if not started <= retrieved <= ended:
                        return dict(result, status="FAIL", reason="LOCAL_BAR_CAPTURE_TIME_INVALID")
                    matches.append(capture)
        if len(matches) != 1:
            return dict(result, reason="LOCAL_BAR_CAPTURE_NOT_UNIQUE")
        if any(isinstance(row, dict) and re.fullmatch(r"\d{8}", str(row.get("dt") or ""))
               and str(row["dt"]) > expected_completed_session.replace("-", "")
               for row in response.get("data") or []):
            return dict(result, status="FAIL", reason="LOCAL_BAR_FUTURE_ROW")
        rows = [row for row in response.get("data") or [] if isinstance(row, dict)
                and str(row.get("dt")) == expected_completed_session.replace("-", "")]
        if not rows:
            return result
        from build_kiwoom_market_snapshot import normalize_series
        normalized = normalize_series(
            rows, ticker=ticker, completed_session=expected_completed_session,
            price_basis="RAW", minimum_history_bars=1, pagination=pagination,
        )
        if "INVALID_OHLCV:" + expected_completed_session in normalized["validation_errors"]:
            return dict(result, status="FAIL", reason="LOCAL_BAR_OHLCV_INVALID")
        if normalized["status"] != "PASS":
            return dict(result, reason="LOCAL_BAR_OHLCV_NOT_VERIFIED")
        selected = normalized["bars"][0]
        if any(row.get("upd_stkpc_tp") not in (None, "0", 0) for row in rows):
            return dict(result, status="FAIL", reason="LOCAL_BAR_BASIS_MISMATCH")
        if _same_scope_raw_bar_coherence(
                captures, ticker=ticker, completed_session=expected_completed_session) != "PASS":
            return dict(result, reason="LOCAL_BAR_SAME_SCOPE_CONFLICT")
        return dict(
            result, status="PASS", reason=None, bar=selected,
            input_sha256=canonical_hash({
                "request": request, "response": response,
                "capture_sha256": matches[0]["source_sha256"],
            }),
        )
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return result


def _current_price_record(
    *, ticker: str, quote_response: dict[str, Any] | None,
    daily_records: list[dict[str, Any]], trading_date: str, observed_at: str,
    market_phase: str,
) -> dict[str, Any] | None:
    if quote_response and quote_response.get("bridge_status") == "PASS":
        rows = quote_response.get("data") or []
        row = rows[0] if len(rows) == 1 and isinstance(rows[0], dict) else None
        price = _cur_prc_price((row or {}).get("cur_prc"))
        if price is not None:
            return kiwoom_broker_quote_observation(
                ticker=ticker,
                reported_session=trading_date,
                price=price,
                provider_timestamp=str(quote_response.get("retrieved_at") or observed_at),
                source_field="cur_prc",
                explicit_session_type=market_phase,
            )
    same_day = [item for item in daily_records if item.get("reported_session") == trading_date]
    return dict(same_day[-1]) if same_day else None


def _aggregate_status(available: int, total: int) -> str:
    if total == 0:
        return "NOT_REQUIRED"
    if available == total:
        return "AVAILABLE"
    if available:
        return "PARTIAL"
    return "UNAVAILABLE"


def _evidence_timestamps(*result_sets: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for results in result_sets:
        for result in results:
            value = result.get("retrieved_at")
            if isinstance(value, str):
                values.append(value)
    return values


def _acquisition_complete_cutoff(
    *result_sets: list[dict[str, Any]],
) -> str | None:
    """Freeze Tc at the latest required result-level evidence timestamp."""
    values = _evidence_timestamps(*result_sets)
    required_count = sum(len(results) for results in result_sets)
    if required_count == 0 or len(values) != required_count:
        return None
    parsed: list[tuple[datetime, str]] = []
    try:
        for value in values:
            parsed.append((_timestamp(value), value))
    except (TypeError, ValueError):
        return None
    return max(parsed, key=lambda item: item[0])[1]


def _temporal_evidence_valid(
    cutoff: str, *result_sets: list[dict[str, Any]],
) -> bool:
    """Validate a frozen cutoff without advancing it for later evidence."""
    values = _evidence_timestamps(*result_sets)
    if len(values) != sum(len(results) for results in result_sets):
        return False
    try:
        cutoff_dt = _timestamp(cutoff)
        return bool(values) and all(_timestamp(value) <= cutoff_dt for value in values)
    except (TypeError, ValueError):
        return False


def _requested_operations(value: list[str] | tuple[str, ...] | None,
                          allowed: tuple[str, ...]) -> tuple[str, ...]:
    """An explicit caller scope narrows dispatch; it is not an approval receipt."""
    if value is None:
        return allowed
    if (not isinstance(value, (list, tuple))
            or any(not isinstance(item, str) or item not in allowed for item in value)
            or len(set(value)) != len(value)):
        raise ValueError("INVALID_ACQUISITION_SCOPE")
    return tuple(value)


def _parent_capture_evidence(
    artifacts: list[tuple[bytes, str]] | None, *, run_id: str, observed_at: str,
) -> list[dict[str, Any]]:
    """Bind consumed wrapper bytes, not self-asserted fields inside a response.

    This checks consistency, not independent authenticity or acquisition approval.
    Existing wrapper formats are accepted; raw contents never enter the report.
    """
    captures: list[dict[str, Any]] = []
    try:
        for raw, expected_hash in artifacts or []:
            if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected_hash:
                raise ValueError
            document = json.loads(raw)
            if not isinstance(document, dict):
                raise ValueError
            fields = {}
            for name in ("run_id", "started_at", "observed_at"):
                values = [document[key] for key in (name, name.upper()) if key in document]
                if not values or any(value != values[0] for value in values):
                    raise ValueError
                fields[name] = values[0]
            if fields["run_id"] != run_id:
                raise ValueError
            if not (_timestamp(fields["started_at"]) <= _timestamp(fields["observed_at"])
                    <= _timestamp(observed_at)):
                raise ValueError
            keys = [key for key in ("safe_bridge_results", "results") if key in document]
            if len(keys) != 1:
                raise ValueError
            results = document[keys[0]]
            if not isinstance(results, list) or not results or any(not isinstance(r, dict) for r in results):
                raise ValueError
            if any(c["source_sha256"] == expected_hash for c in captures):
                raise ValueError
            request_fields = {}
            for name in ("requests", "request_sha256"):
                values = [document[key] for key in (name, name.upper()) if key in document]
                if values:
                    if any(value != values[0] for value in values):
                        raise ValueError
                    request_fields[name] = values[0]
            captures.append({**fields, **request_fields, "source_sha256": expected_hash, "results": results})
    except (TypeError, ValueError, KeyError, UnicodeError):
        raise ValueError("PARENT_CAPTURE_BINDING_INVALID") from None
    return captures


def _failure_timing_evidence(
    requests: list[dict[str, Any]], results: list[dict[str, Any]],
    captures: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Use parent time only in a separate failure-timing view, never broker data."""
    timing = [dict(result) for result in results]
    bindings: list[dict[str, Any]] = []
    for request, result, view in zip(requests, results, timing):
        if (result.get("bridge_status") not in SAFE_FAILURE_STATUSES
                or result.get("retrieved_at") is not None):
            continue
        matches = []
        for capture in captures:
            for saved in capture["results"]:
                candidate = dict(saved)
                # Never infer a missing saved ticker from the current request.
                candidate.setdefault("ticker", None)
                candidate["order_authority"] = False
                if (candidate.get("operation") == request["operation"]
                        and candidate.get("ticker") == request.get("ticker")
                        and canonical_hash(candidate) == canonical_hash(result)):
                    matches.append(capture)
        if len(matches) > 1:
            raise ValueError("PARENT_CAPTURE_BINDING_AMBIGUOUS")
        if matches:
            capture = matches[0]
            view["retrieved_at"] = capture["observed_at"]
            bindings.append({
                "operation": request["operation"], "ticker": request.get("ticker"),
                "run_id": capture["run_id"], "source_sha256": capture["source_sha256"],
                "request_sha256": canonical_hash(request), "result_sha256": canonical_hash(result),
                "parent_observed_at": capture["observed_at"],
                "timestamp_role": "FAILURE_OBSERVATION_ONLY",
            })
    return timing, bindings



def _captured_acquisition_handoff(
    requests: list[dict[str, Any]], results: list[dict[str, Any]],
    captures: list[dict[str, Any]], *, observed_at: str, cutoff: str,
    maximum_age_seconds: int,
) -> dict[str, Any] | None:
    """Bind a complete, bounded saved acquisition; never grant execution authority."""
    try:
        observed = _timestamp(observed_at)
        if not captures or not requests or len(requests) != len(results):
            return None
        bindings, times, seen = [], [], set()
        for request, result in zip(requests, results):
            key = (request["operation"], request.get("ticker"))
            if key in seen or result.get("operation") != key[0] or result.get("ticker") != key[1]:
                return None
            seen.add(key)
            matches = []
            for capture in captures:
                recorded_requests = capture.get("requests")
                if (not isinstance(recorded_requests, list)
                        or len(recorded_requests) != len(capture["results"])
                        or any(not isinstance(r, dict) for r in recorded_requests)):
                    return None
                if ("request_sha256" in capture
                        and capture["request_sha256"] != canonical_hash(recorded_requests)):
                    return None
                recorded_keys = [(r.get("operation"), r.get("ticker")) for r in recorded_requests]
                if len(set(recorded_keys)) != len(recorded_keys):
                    return None
                for recorded_request, saved in zip(recorded_requests, capture["results"]):
                    item = dict(saved)
                    item.setdefault("ticker", None)
                    item["order_authority"] = False
                    if canonical_hash(item) == canonical_hash(result):
                        if recorded_request != request:
                            return None
                        matches.append(capture)
            if len(matches) != 1:
                return None
            capture = matches[0]
            value = result.get("retrieved_at")
            if value is None and result.get("bridge_status") in SAFE_FAILURE_STATUSES:
                value = capture["observed_at"]
            when = _timestamp(value)
            if not (_timestamp(capture["started_at"]) <= when
                    <= _timestamp(capture["observed_at"]) <= observed):
                return None
            if not 0 <= (observed - when).total_seconds() <= maximum_age_seconds:
                return None
            times.append(when)
            bindings.append({
                "request": dict(request), "source_sha256": capture["source_sha256"],
                "result_sha256": canonical_hash(result),
            })
        if max(times) != _timestamp(cutoff):
            return None
        return {
            "assurance": "CONSUMED_INPUT_CONSISTENCY_ONLY",
            "request_sha256": canonical_hash(requests),
            "bindings": bindings,
        }
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def validate_manual_acquisition_handoff(
    evidence: dict[str, Any], artifacts: list[tuple[bytes, str]] | None,
    *, analysis_observed_at: str, maximum_age_seconds: int,
) -> bool:
    """Recheck consumed bytes at the analysis boundary, not a report's claimed status."""
    try:
        view = evidence.get("manual_analysis_view") or {}
        proof = view.get("acquisition_handoff")
        if not isinstance(proof, dict) or not artifacts:
            return False
        observed_at = evidence["observed_at"]
        cutoff = evidence["decision_as_of"]
        analysis = _timestamp(analysis_observed_at)
        if analysis < _timestamp(observed_at):
            return False
        captures = _parent_capture_evidence(
            artifacts, run_id=evidence["manual_run_id"], observed_at=observed_at,
        )
        requests, results = [], []
        for binding in proof["bindings"]:
            request = binding["request"]
            if not isinstance(request, dict):
                return False
            matches = []
            for capture in captures:
                if capture["source_sha256"] != binding["source_sha256"]:
                    continue
                for saved in capture["results"]:
                    item = dict(saved)
                    item.setdefault("ticker", None)
                    item["order_authority"] = False
                    if canonical_hash(item) == binding["result_sha256"]:
                        matches.append(item)
            if len(matches) != 1:
                return False
            requests.append(request)
            results.append(matches[0])
        rebuilt = _captured_acquisition_handoff(
            requests, results, captures, observed_at=analysis_observed_at,
            cutoff=cutoff, maximum_age_seconds=maximum_age_seconds,
        )
        if rebuilt != proof:
            return False
        scope = evidence["broker_observed_state"]["acquisition_scope"]
        if proof["request_sha256"] != scope["request_sha256"]:
            return False
        accounts = _requested_operations(scope["account_operations"], ACCOUNT_READ_OPERATIONS)
        markets = _requested_operations(scope["market_operations"], MARKET_READ_OPERATIONS)
        expected = [{"operation": op} for op in accounts]
        tickers = [item["ticker"] for item in evidence["current_price_evidence"]]
        if tickers != sorted(set(tickers)):
            return False
        if "oauth_health" in markets:
            expected.append({"operation": "oauth_health"})
        if "market_quote" in markets:
            expected.extend({"operation": "market_quote", "ticker": t, "fx_applied": False}
                            for t in tickers)
        if "daily_chart" in markets:
            expected.extend({
                "operation": "daily_chart", "ticker": t,
                "completed_session": evidence["expected_completed_us_session"],
                "price_basis": "RAW", "fx_applied": False,
            } for t in tickers)
        if requests != expected:
            return False
        incomplete = (set(accounts) != set(ACCOUNT_READ_OPERATIONS)
                      or set(markets) != set(MARKET_READ_OPERATIONS)
                      or any(item.get("bridge_status") != "PASS" for item in results))
        if incomplete and evidence.get("preflight_status") == "PASS":
            return False
        scoped_promotion = incomplete and (
            evidence.get("manual_data_verification_status") == "VERIFIED_REAL_DATA"
            or evidence.get("evidence_grade") in {"GRADE_A", "GRADE_B"}
        )
        account_results = results[:len(accounts)]
        market_results = results[len(accounts):]
        broker, _ = _normalize_broker_state(
            account_results, observed_at=cutoff, maximum_age_seconds=maximum_age_seconds,
        )
        for op in set(ACCOUNT_READ_OPERATIONS) - set(accounts):
            broker["operation_statuses"][op] = "NOT_REQUESTED"
        actual = evidence["broker_observed_state"]
        if any(actual.get(k) != v for k, v in broker.items()):
            return False
        if evidence["broker_snapshot_as_of"] != broker["as_of"]:
            return False
        if evidence["verified_orderable_cash_usd"] != _number(broker["cash"].get("order_available_cash")):
            return False
        if (view.get("analysis_observed_at") != observed_at
                or view.get("acquisition_completed_at") != cutoff):
            return False
        current, history = [], []
        for ticker in tickers:
            daily = _operation_result(market_results, "daily_chart", ticker)
            records = _normalize_daily_records(daily, ticker=ticker, observed_at=cutoff)
            history.append({
                "ticker": ticker, "status": "AVAILABLE" if records else "UNAVAILABLE",
                "provider": "KIWOOM_REST", "source_api_id": "usa06012",
                "retrieved_at": (daily or {}).get("retrieved_at"),
                "pagination_status": ((daily or {}).get("pagination") or {}).get("status"),
                "records": records,
            })
            record = _current_price_record(
                ticker=ticker, quote_response=_operation_result(market_results, "market_quote", ticker),
                daily_records=records, trading_date=evidence["trading_date"],
                observed_at=cutoff, market_phase=evidence["market_phase"],
            )
            current.append({"ticker": ticker, "status": "AVAILABLE" if record else "UNAVAILABLE",
                            "record": record})
            for selected in evidence.get("last_verified_finalized_bars", []):
                if selected.get("ticker") == ticker and selected.get("status") == "VERIFIED":
                    if selected.get("bar") not in records:
                        return False
        matched = current == evidence["current_price_evidence"] and history == evidence["historical_daily_evidence"]
        return matched and (not scoped_promotion or validate_manual_direction_evidence(
            evidence, artifacts, analysis_observed_at=analysis_observed_at,
        ))
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return False


def validate_manual_direction_evidence(
    evidence: dict[str, Any], artifacts: list[tuple[bytes, str]] | None,
    *, analysis_observed_at: str,
) -> bool:
    """Recompute the opted-in holdings/Cash direction scope from consumed captures.

    This is input consistency, not source authenticity or execution readiness.
    The original preflight status is retained; PARTIAL is never rewritten to PASS.
    """
    try:
        view = evidence["manual_analysis_view"]
        if (view.get("decision_evidence_scope") != "EXISTING_HOLDINGS_AND_CASH_DIRECTION_ONLY"
                or evidence.get("run_mode") != "MANUAL_READ_ONLY"
                or evidence.get("preflight_status") not in {"PASS", "PARTIAL"}
                or evidence.get("hard_fail_reasons") != []
                or evidence.get("order_authority") is not False
                or evidence.get("quantity_authority") != "none"
                or evidence.get("execution_quantity") is not None
                or evidence.get("backfill") is not False
                or evidence.get("scheduled_occurrence_id") is not None
                or evidence.get("evidence_grade") not in {"UNVERIFIED", "GRADE_B"}
                or (evidence.get("integrated_authority_snapshot_provenance") or {}).get("authority_source")
                    not in {"LEGACY_INDEPENDENT", "K3_COMBINED_PRODUCTION"}):
            return False
        # Validate bytes without trusting this report's proposed grade. This also
        # avoids recursion through the handoff validator's promotion check.
        ungraded = dict(evidence, evidence_grade="UNVERIFIED", manual_data_verification_status="PARTIAL")
        if not validate_manual_acquisition_handoff(
            ungraded, artifacts, analysis_observed_at=analysis_observed_at, maximum_age_seconds=900,
        ):
            return False
        scope = evidence["broker_observed_state"]["acquisition_scope"]
        captures = _parent_capture_evidence(
            artifacts, run_id=evidence["manual_run_id"], observed_at=evidence["observed_at"],
        )

        def saved_reader(requests):
            found = []
            for request in requests:
                matches = [result for capture in captures
                           for recorded, result in zip(capture["requests"], capture["results"])
                           if recorded == request]
                if len(matches) != 1:
                    raise ValueError("DIRECTION_CAPTURE_REQUEST_NOT_UNIQUE")
                found.append(dict(matches[0]))
            return found

        source = evidence["system_portfolio_state"]
        authority_provenance = evidence["integrated_authority_snapshot_provenance"]
        combined_replay = authority_provenance["authority_source"] == "K3_COMBINED_PRODUCTION"
        replay_cutoff = evidence["decision_as_of"]
        if combined_replay:
            # Preserve the initial authority cutoff separately from the final
            # acquisition cutoff. Never accept an artifact path from the report.
            replay_cutoff = authority_provenance["snapshot_decision_as_of"]
            if (authority_provenance.get("run_id") != evidence["manual_run_id"]
                    or authority_provenance.get("authority_resolved_at") != evidence["observed_at"]
                    or authority_provenance.get("report_decision_as_of") != evidence["decision_as_of"]
                    or _timestamp(replay_cutoff) > _timestamp(evidence["observed_at"])):
                return False
        replay = run_manual_preflight(
            manual_run_id=evidence["manual_run_id"], system_portfolio=source,
            system_portfolio_source=source["source_path"], system_portfolio_sha256=source["source_sha256"],
            provenance_policy={}, account_reader=saved_reader, market_reader=saved_reader,
            maximum_broker_age_seconds=900, observed_at=evidence["observed_at"],
            decision_as_of=replay_cutoff,
            k3_production_combined_activation=(
                ROOT / COMBINED_ACTIVATION_RELATIVE_PATH if combined_replay else None
            ),
            account_operations=scope["account_operations"], market_operations=scope["market_operations"],
            parent_capture_artifacts=artifacts,
        )
        # The trusted loader validates ACTIVE artifacts; exact provenance binds
        # their hashes, cohort, versions and times to this consumed report.
        # A replaced/missing production bundle must fail closed, not fall back.
        if (combined_replay
                and replay["integrated_authority_snapshot_provenance"] != authority_provenance):
            return False
        auxiliary = set(ACCOUNT_READ_OPERATIONS) - {"account_holdings_read", "account_deposit_read"}
        allowed = {prefix + operation for operation in auxiliary
                   for prefix in ("NOT_REQUESTED:", "ACCOUNT_EVIDENCE_NOT_VERIFIED:")}
        if (not set(replay["partial_reasons"]) <= allowed
                or replay["hard_fail_reasons"]):
            return False
        required = {
            "kiwoom_health_status": "HEALTHY", "broker_snapshot_status": "AVAILABLE",
            "orderable_cash_status": "VERIFIED", "current_price_status": "AVAILABLE",
            "historical_daily_evidence_status": "AVAILABLE",
            "identity_authority_status": "VERIFIED", "session_authority_status": "VERIFIED",
            "integrated_authority_cohort_status": "MATCHED",
        }
        if any(replay.get(k) != v or evidence.get(k) != v for k, v in required.items()):
            return False
        local = (view.get("local_regular_bar_coherence") or {})
        if (view.get("provider_finalization_verified") != "NOT_VERIFIED"
                or view.get("technical_analysis_eligibility") != "NOT_VERIFIED"
                or not isinstance(local, dict)
                or set(local) != {item["ticker"] for item in replay["current_price_evidence"]}
                or any(not isinstance(item, dict) or item.get("status") != "PASS"
                       for item in local.values())):
            return False
        keys = ["broker_observed_state", "verified_orderable_cash_usd", "current_price_evidence",
                "historical_daily_evidence", "partial_reasons", "preflight_status",
                "expected_completed_us_session", "market_phase", "trading_date", "decision_as_of",
                "identity_authority_id", "identity_registry_hash", "identity_activation_cohort_id",
                "identity_registry_version", "identity_authority_reasons", "session_authority_reasons",
                "calendar_hash", "calendar_policy_identity", "session_activation_cohort_id",
                "session_authority_market_phase"]
        if any(evidence.get(k) != replay.get(k) for k in keys):
            return False
        projected_bars = [
            dict(item, **_manual_provider_finalization_projection(item))
            for item in replay["last_verified_finalized_bars"]
        ]
        if (evidence.get("last_verified_finalized_bars") != projected_bars
                or evidence.get("last_verified_finalized_bar_status") != "NOT_VERIFIED"
                or evidence.get("last_verified_finalized_bar_date") is not None
                or evidence.get("finalized_bar_preflight_status") != "FAIL"
                or evidence.get("current_session_finalization_status") != "NOT_VERIFIED"):
            return False
        expected_view = dict(view)
        for derived in ("decision_evidence_scope", "provider_finalization_verified",
                        "local_regular_bar_coherence", "technical_analysis_eligibility"):
            expected_view.pop(derived, None)
        if expected_view != replay["manual_analysis_view"]:
            return False
        holdings = replay["broker_observed_state"]["holdings"]
        tickers = {row["ticker"] for row in holdings}
        if not tickers or tickers != {row["ticker"] for row in replay["current_price_evidence"]}:
            return False
        bound_snapshot = (
            load_integrated_authority_snapshot(
                ROOT / COMBINED_ACTIVATION_RELATIVE_PATH, trusted_root=ROOT,
                decision_as_of=replay_cutoff, required_activation_status="ACTIVE",
                resolved_at=evidence["observed_at"], run_id=evidence["manual_run_id"],
            ) if combined_replay else None
        )
        authority = _authority_context(
            sorted(tickers), observed_at=evidence["decision_as_of"],
            decision_as_of=evidence["decision_as_of"], integrated_snapshot=bound_snapshot,
        )
        if authority["expected_completed_session"] != evidence["expected_completed_us_session"]:
            return False
        recomputed = {}
        for ticker in sorted(tickers):
            completed = authority["authority_views"][ticker].expected_completed_session
            if completed is None:
                return False
            request = {
                "operation": "daily_chart", "ticker": ticker,
                "completed_session": evidence["expected_completed_us_session"],
                "price_basis": "RAW", "fx_applied": False,
            }
            response = saved_reader([request])[0]
            response.setdefault("ticker", None)
            response["order_authority"] = False
            recomputed[ticker] = local_regular_bar_coherence(
                response, request=request, captures=captures,
                expected_completed_session=evidence["expected_completed_us_session"],
                core_close_at=completed.core_close_at,
                observed_at=analysis_observed_at,
            )
        if local != recomputed:
            return False
        cash = replay["broker_observed_state"]["cash"]
        return all(_number(cash.get(k)) is not None for k in (
            "foreign_currency_deposit", "withdrawable_cash", "order_available_cash", "settled_available_cash",
        ))
    except (OSError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return False


def _authority_context(
    tickers: list[str], *, observed_at: str, decision_as_of: str,
    integrated_snapshot: IntegratedAuthoritySnapshot | None = None,
) -> dict[str, Any]:
    """Resolve one authority boundary, optionally from one frozen K3 snapshot."""
    identity_views = {}
    authority_views = {}
    for ticker in tickers:
        identity_view = (
            resolve_instrument_identity_from_snapshot(
                integrated_snapshot, ticker, decision_as_of=decision_as_of,
            )
            if integrated_snapshot is not None
            else resolve_instrument_identity(ticker, decision_as_of=decision_as_of)
        )
        identity_views[ticker] = identity_view
        if identity_view.authority_status != "VERIFIED":
            continue
        authority_views[ticker] = (
            derive_us_market_session_authority_from_snapshot(
                integrated_snapshot,
                observed_at,
                primary_listing_operating_mic=identity_view.primary_listing_operating_mic,
                decision_as_of=decision_as_of,
            )
            if integrated_snapshot is not None
            else derive_us_market_session_authority(
                observed_at,
                primary_listing_operating_mic=identity_view.primary_listing_operating_mic,
                decision_as_of=decision_as_of,
            )
        )
    verified_identity_views = [
        view for view in identity_views.values() if view.authority_status == "VERIFIED"
    ]
    all_identities_verified = bool(
        tickers and len(verified_identity_views) == len(tickers)
    )
    identity_authority_status = "VERIFIED" if all_identities_verified else "NOT_VERIFIED"
    identity_authority_reasons = sorted({
        view.authority_reason for view in identity_views.values()
        if view.authority_reason != "OK"
    })
    if not tickers:
        identity_authority_reasons = ["INVALID_INPUT"]
    identity_authority_ids = {
        view.authority_id for view in verified_identity_views if view.authority_id is not None
    }
    identity_registry_versions = {
        view.registry_version for view in verified_identity_views if view.registry_version is not None
    }
    identity_registry_hashes = {
        view.registry_hash for view in verified_identity_views if view.registry_hash is not None
    }
    identity_activation_cohorts = {
        view.activation_cohort_id
        for view in verified_identity_views
        if view.activation_cohort_id is not None
    }
    identity_authority_id = (
        next(iter(identity_authority_ids)) if len(identity_authority_ids) == 1 else None
    )
    identity_registry_version = (
        next(iter(identity_registry_versions)) if len(identity_registry_versions) == 1 else None
    )
    identity_registry_hash = (
        next(iter(identity_registry_hashes)) if len(identity_registry_hashes) == 1 else None
    )
    identity_activation_cohort_id = (
        next(iter(identity_activation_cohorts)) if len(identity_activation_cohorts) == 1 else None
    )
    verified_authority_views = [
        view for view in authority_views.values()
        if view.authority_status == "VERIFIED" and view.expected_completed_session is not None
    ]
    expected_sessions = {
        view.expected_completed_session.session_date for view in verified_authority_views
    }
    all_authorities_verified = bool(
        all_identities_verified
        and len(authority_views) == len(tickers)
        and len(verified_authority_views) == len(tickers)
    )
    session_authority_status = "VERIFIED" if all_authorities_verified else "NOT_VERIFIED"
    session_authority_reasons = sorted({
        view.authority_reason for view in authority_views.values()
        if view.authority_reason != "OK"
    })
    if not tickers:
        session_authority_reasons = ["INVALID_INPUT"]
    authority_market_phases = {
        view.market_phase for view in authority_views.values() if view.market_phase is not None
    }
    session_authority_market_phase = (
        next(iter(authority_market_phases)) if len(authority_market_phases) == 1 else None
    )
    calendar_hashes = {
        view.calendar_hash for view in authority_views.values() if view.calendar_hash is not None
    }
    calendar_hash = next(iter(calendar_hashes)) if len(calendar_hashes) == 1 else None
    session_activation_cohorts = {
        view.activation_cohort_id
        for view in authority_views.values()
        if view.activation_cohort_id is not None
    }
    session_activation_cohort_id = (
        next(iter(session_activation_cohorts)) if len(session_activation_cohorts) == 1 else None
    )
    integrated_authority_matched = bool(
        all_authorities_verified
        and len(expected_sessions) == 1
        and len(identity_authority_ids) == 1
        and len(identity_registry_versions) == 1
        and len(identity_registry_hashes) == 1
        and all(view.registry_hash is not None for view in verified_identity_views)
        and all(view.activation_cohort_id is not None for view in verified_identity_views)
        and identity_registry_hash is not None
        and calendar_hash is not None
        and all(view.calendar_hash is not None for view in verified_authority_views)
        and all(view.activation_cohort_id is not None for view in verified_authority_views)
        and identity_activation_cohort_id is not None
        and identity_activation_cohort_id != ""
        and session_activation_cohort_id != ""
        and identity_activation_cohort_id == session_activation_cohort_id
    )
    integrated_authority_cohort_status = (
        "MATCHED" if integrated_authority_matched else "NOT_VERIFIED"
    )
    expected_completed_session = (
        next(iter(expected_sessions)) if integrated_authority_matched else None
    )
    return {
        "identity_views": identity_views,
        "authority_views": authority_views,
        "identity_authority_status": identity_authority_status,
        "identity_authority_reasons": identity_authority_reasons,
        "identity_authority_id": identity_authority_id,
        "identity_registry_version": identity_registry_version,
        "identity_registry_hash": identity_registry_hash,
        "identity_activation_cohort_id": identity_activation_cohort_id,
        "session_authority_status": session_authority_status,
        "session_authority_reasons": session_authority_reasons,
        "session_authority_market_phase": session_authority_market_phase,
        "calendar_hash": calendar_hash,
        "session_activation_cohort_id": session_activation_cohort_id,
        "integrated_authority_matched": integrated_authority_matched,
        "integrated_authority_cohort_status": integrated_authority_cohort_status,
        "expected_completed_session": expected_completed_session,
    }


def run_manual_preflight(
    *,
    manual_run_id: str,
    system_portfolio: dict[str, Any],
    system_portfolio_source: str,
    system_portfolio_sha256: str,
    provenance_policy: dict[str, Any],
    account_reader: AccountReader,
    market_reader: MarketReader,
    maximum_broker_age_seconds: int,
    decision_as_of: str | None = None,
    observed_at: str | None = None,
    extra_tickers: list[str] | None = None,
    k3_shadow_combined_activation: Path | None = None,
    k3_production_combined_activation: Path | None = None,
    account_operations: list[str] | tuple[str, ...] | None = None,
    market_operations: list[str] | tuple[str, ...] | None = None,
    parent_capture_artifacts: list[tuple[bytes, str]] | None = None,
    direction_only: bool = False,
) -> dict[str, Any]:
    """Collect and validate M1 evidence without writing or invoking strategy logic."""
    run_id = validate_manual_run_id(manual_run_id)
    initial_observation = observed_at or _utc_now()
    observed_dt = _timestamp(initial_observation)
    initial_trading_date = observed_dt.astimezone(ET).date().isoformat()
    initial_market_phase = market_session_at(initial_observation)
    initial_authority_cutoff = decision_as_of or initial_observation
    _timestamp(initial_authority_cutoff)
    requested_accounts = _requested_operations(account_operations, ACCOUNT_READ_OPERATIONS)
    requested_market = _requested_operations(market_operations, MARKET_READ_OPERATIONS)
    captures = _parent_capture_evidence(
        parent_capture_artifacts, run_id=run_id, observed_at=initial_observation,
    )
    omitted_operations = sorted(
        (set(ACCOUNT_READ_OPERATIONS) - set(requested_accounts))
        | (set(MARKET_READ_OPERATIONS) - set(requested_market))
    )
    if (
        k3_shadow_combined_activation is not None
        and k3_production_combined_activation is not None
    ):
        raise ValueError("MULTIPLE_COMBINED_AUTHORITY_SOURCES")
    combined_activation = (
        k3_shadow_combined_activation
        if k3_shadow_combined_activation is not None
        else k3_production_combined_activation
    )
    combined_activation_status = (
        "SHADOW" if k3_shadow_combined_activation is not None else "ACTIVE"
    )
    integrated_snapshot = (
        load_integrated_authority_snapshot(
            combined_activation,
            trusted_root=ROOT,
            decision_as_of=initial_authority_cutoff,
            required_activation_status=combined_activation_status,
            resolved_at=initial_observation,
            run_id=run_id,
        )
        if combined_activation is not None
        else None
    )

    account_requests = [{"operation": operation} for operation in requested_accounts]
    account_results = _safe_reader_call(
        account_reader, account_requests, unavailable_status="KIWOOM_ACCOUNT_UNAVAILABLE",
    ) if account_requests else []
    broker_state, broker_status = _normalize_broker_state(
        account_results,
        observed_at=initial_observation,
        maximum_age_seconds=maximum_broker_age_seconds,
    )
    system_state = _system_portfolio_projection(
        system_portfolio,
        source_path=system_portfolio_source,
        source_sha256=system_portfolio_sha256,
    )
    tickers = sorted({
        item
        for item in (
            [_ticker(value) for value in (extra_tickers or [])]
            + [_ticker(value) for value in (system_state.get("holdings") or {})]
            + [_ticker(item.get("ticker")) for item in broker_state.get("holdings", []) if isinstance(item, dict)]
        )
        if item is not None
    })
    initial_authority_context = _authority_context(
        tickers,
        observed_at=initial_observation,
        decision_as_of=initial_authority_cutoff,
        integrated_snapshot=integrated_snapshot,
    )
    initial_authority_views = initial_authority_context["authority_views"]
    initial_integrated_authority_matched = initial_authority_context[
        "integrated_authority_matched"
    ]
    expected_completed_session_before_acquisition = initial_authority_context[
        "expected_completed_session"
    ]
    initial_session_context = (
        initial_trading_date,
        initial_market_phase,
        expected_completed_session_before_acquisition,
    )

    market_requests: list[dict[str, Any]] = [{"operation": "oauth_health"}]
    market_requests.extend(
        {"operation": "market_quote", "ticker": ticker, "fx_applied": False}
        for ticker in tickers
    )
    market_requests.extend(
        {
            "operation": "daily_chart", "ticker": ticker,
            "completed_session": expected_completed_session_before_acquisition,
            "price_basis": "RAW", "fx_applied": False,
        }
        for ticker in tickers
        if initial_integrated_authority_matched
        and initial_authority_views[ticker].authority_status == "VERIFIED"
        and initial_authority_views[ticker].expected_completed_session is not None
    )
    market_requests = [r for r in market_requests if r["operation"] in requested_market]
    market_results = _safe_reader_call(
        market_reader, market_requests, unavailable_status="KIWOOM_API_UNAVAILABLE",
    ) if market_requests else []
    account_timing, account_bindings = _failure_timing_evidence(account_requests, account_results, captures)
    market_timing, market_bindings = _failure_timing_evidence(market_requests, market_results, captures)
    timing_bindings = account_bindings + market_bindings
    acquisition_complete_cutoff = _acquisition_complete_cutoff(account_timing, market_timing)
    cutoff = acquisition_complete_cutoff or initial_authority_cutoff
    cutoff_dt = _timestamp(cutoff)
    if acquisition_complete_cutoff is not None:
        authority_context = _authority_context(
            tickers,
            observed_at=cutoff,
            decision_as_of=cutoff,
            integrated_snapshot=integrated_snapshot,
        )
        broker_state, broker_status = _normalize_broker_state(
            account_results,
            observed_at=cutoff,
            maximum_age_seconds=maximum_broker_age_seconds,
        )
    else:
        authority_context = initial_authority_context
    if account_operations is not None or market_operations is not None or parent_capture_artifacts is not None:
        for operation in set(ACCOUNT_READ_OPERATIONS) - set(requested_accounts):
            broker_state["operation_statuses"][operation] = "NOT_REQUESTED"
        broker_state["acquisition_scope"] = {
            "account_operations": list(requested_accounts), "market_operations": list(requested_market),
            "not_requested": omitted_operations,
            "request_sha256": canonical_hash(account_requests + market_requests),
            "parent_failure_timing": timing_bindings,
            "binding_assurance": "CONSUMED_INPUT_CONSISTENCY_ONLY",
            "capabilities_checked_meaning": "CAPABILITY_INVENTORY_NOT_DISPATCH_EVIDENCE",
        }
    identity_views = authority_context["identity_views"]
    authority_views = authority_context["authority_views"]
    identity_authority_status = authority_context["identity_authority_status"]
    identity_authority_reasons = authority_context["identity_authority_reasons"]
    identity_authority_id = authority_context["identity_authority_id"]
    identity_registry_version = authority_context["identity_registry_version"]
    identity_registry_hash = authority_context["identity_registry_hash"]
    identity_activation_cohort_id = authority_context["identity_activation_cohort_id"]
    session_authority_status = authority_context["session_authority_status"]
    session_authority_reasons = authority_context["session_authority_reasons"]
    session_authority_market_phase = authority_context["session_authority_market_phase"]
    calendar_hash = authority_context["calendar_hash"]
    session_activation_cohort_id = authority_context["session_activation_cohort_id"]
    integrated_authority_matched = authority_context["integrated_authority_matched"]
    integrated_authority_cohort_status = authority_context[
        "integrated_authority_cohort_status"
    ]
    expected_completed_session = authority_context["expected_completed_session"]
    trading_date = cutoff_dt.astimezone(ET).date().isoformat()
    market_phase = market_session_at(cutoff)
    cutoff_session_context = (
        trading_date,
        market_phase,
        expected_completed_session,
    )
    authority_revalidation_valid = bool(
        acquisition_complete_cutoff is not None
        and identity_authority_status == "VERIFIED"
        and session_authority_status == "VERIFIED"
        and integrated_authority_cohort_status == "MATCHED"
    )
    session_rollover_detected = bool(
        acquisition_complete_cutoff is not None
        and initial_session_context[2] is not None
        and cutoff_session_context[2] is not None
        and initial_session_context[2] != cutoff_session_context[2]
    )
    session_identity_revalidated = bool(
        authority_revalidation_valid
        and expected_completed_session_before_acquisition is not None
        and expected_completed_session_before_acquisition == expected_completed_session
    )
    health = _operation_result(market_results, "oauth_health")
    if health and health.get("bridge_status") == "PASS" and health.get("authenticated") is True:
        kiwoom_health_status = "HEALTHY"
    elif health and health.get("failure_type") == "AUTHENTICATION_FAILURE":
        kiwoom_health_status = "AUTHENTICATION_FAILED"
    else:
        kiwoom_health_status = "UNAVAILABLE"

    current_price_evidence: list[dict[str, Any]] = []
    historical_daily_evidence: list[dict[str, Any]] = []
    finalized_results: list[dict[str, Any]] = []
    local_regular_bars: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        identity_view = identity_views[ticker]
        authority_view = authority_views.get(ticker)
        daily_response = _operation_result(market_results, "daily_chart", ticker)
        if direction_only:
            completed = getattr(authority_view, "expected_completed_session", None)
            if completed is not None and expected_completed_session is not None:
                local_regular_bars[ticker] = local_regular_bar_coherence(
                    daily_response,
                    request={
                        "operation": "daily_chart", "ticker": ticker,
                        "completed_session": expected_completed_session,
                        "price_basis": "RAW", "fx_applied": False,
                    },
                    captures=captures, expected_completed_session=expected_completed_session,
                    core_close_at=completed.core_close_at, observed_at=initial_observation,
                    maximum_age_seconds=maximum_broker_age_seconds,
                )
            else:
                local_regular_bars[ticker] = {
                    "status": "NOT_VERIFIED", "reason": "LOCAL_BAR_SESSION_NOT_VERIFIED",
                    "provider_finalization_verified": "NOT_VERIFIED", "bar": None,
                    "input_sha256": None,
                }
        daily_records = _normalize_daily_records(
            daily_response, ticker=ticker, observed_at=cutoff,
        )
        pagination = (daily_response or {}).get("pagination") or {}
        history_status = "AVAILABLE" if daily_records else "UNAVAILABLE"
        historical_daily_evidence.append({
            "ticker": ticker,
            "status": history_status,
            "provider": "KIWOOM_REST",
            "source_api_id": "usa06012",
            "retrieved_at": (daily_response or {}).get("retrieved_at"),
            "pagination_status": pagination.get("status"),
            "records": daily_records,
        })
        current = _current_price_record(
            ticker=ticker,
            quote_response=_operation_result(market_results, "market_quote", ticker),
            daily_records=daily_records,
            trading_date=trading_date,
            observed_at=cutoff,
            market_phase=market_phase,
        )
        current_price_evidence.append({
            "ticker": ticker,
            "status": "AVAILABLE" if current is not None else "UNAVAILABLE",
            "record": current,
        })
        if identity_view.authority_status != "VERIFIED":
            session_authority_item_status = "NOT_VERIFIED"
            session_authority_item_reason = "UPSTREAM_IDENTITY_NOT_VERIFIED"
            selected = {
                "status": "NOT_VERIFIED",
                "bar_date": None,
                "bar": None,
                "technical_authority": False,
                "reason": "IDENTITY_NOT_VERIFIED:" + identity_view.authority_reason,
            }
        elif authority_view is None:
            session_authority_item_status = "NOT_VERIFIED"
            session_authority_item_reason = "INTEGRITY_FAILURE"
            selected = {
                "status": "NOT_VERIFIED",
                "bar_date": None,
                "bar": None,
                "technical_authority": False,
                "reason": "INTEGRITY_FAILURE",
            }
        elif (
            authority_view.authority_status == "VERIFIED"
            and authority_view.expected_completed_session is not None
            and integrated_authority_matched
            and session_identity_revalidated
        ):
            session_authority_item_status = authority_view.authority_status
            session_authority_item_reason = authority_view.authority_reason
            selected = _select_last_verified_finalized_bar(
                daily_records,
                observed_at=cutoff,
                expected_ticker=ticker,
                expected_completed_session=(
                    authority_view.expected_completed_session.session_date
                ),
            )
        else:
            session_authority_item_status = authority_view.authority_status
            session_authority_item_reason = authority_view.authority_reason
            failure_reason = (
                "ACQUISITION_SESSION_ROLLOVER"
                if session_rollover_detected
                else "INTEGRITY_FAILURE"
                if authority_view.authority_status == "VERIFIED"
                and not integrated_authority_matched
                else authority_view.authority_reason
            )
            selected = {
                "status": "NOT_VERIFIED",
                "bar_date": None,
                "bar": None,
                "technical_authority": False,
                "reason": failure_reason,
            }
        if direction_only:
            selected = _manual_provider_finalization_projection(selected)
        finalized_results.append({
            "ticker": ticker,
            "identity_authority_status": identity_view.authority_status,
            "identity_authority_reason": identity_view.authority_reason,
            "primary_listing_segment_mic": identity_view.primary_listing_segment_mic,
            "primary_listing_operating_mic": identity_view.primary_listing_operating_mic,
            "session_authority_status": session_authority_item_status,
            "session_authority_reason": session_authority_item_reason,
            **selected,
        })

    available_current = sum(item["status"] == "AVAILABLE" for item in current_price_evidence)
    current_price_status = _aggregate_status(available_current, len(tickers))
    available_history = sum(item["status"] == "AVAILABLE" for item in historical_daily_evidence)
    historical_status = _aggregate_status(available_history, len(tickers))
    verified_bars = [item for item in finalized_results if item["status"] == "VERIFIED"]
    if tickers and len(verified_bars) == len(tickers):
        finalized_status = "VERIFIED"
    elif verified_bars:
        finalized_status = "PARTIAL"
    else:
        finalized_status = "NOT_VERIFIED"
    finalized_dates = [str(item["bar_date"]) for item in verified_bars if item.get("bar_date")]
    last_finalized_date = max(finalized_dates) if finalized_dates else None
    finalized_bar_preflight_pass = bool(
        tickers
        and integrated_authority_matched
        and session_identity_revalidated
        and expected_completed_session is not None
        and len(verified_bars) == len(tickers)
        and all(
            item.get("bar_date") == expected_completed_session
            for item in verified_bars
        )
    )
    finalized_bar_preflight_status = "PASS" if finalized_bar_preflight_pass else "FAIL"
    current_session_finalized = bool(
        tickers and len(verified_bars) == len(tickers)
        and expected_completed_session == trading_date
        and all(item.get("bar_date") == trading_date for item in verified_bars)
    )
    current_session_finalization_status = "VERIFIED" if current_session_finalized else "NOT_VERIFIED"

    cash = broker_state.get("cash") or {}
    verified_orderable_cash = _number(cash.get("order_available_cash"))
    orderable_cash_status = "VERIFIED" if verified_orderable_cash is not None else "NOT_VERIFIED"
    broker_diff_status, broker_diff_details = compare_broker_and_system(broker_state, system_state)
    manual_view = _manual_analysis_view(broker_state, system_state)
    if direction_only:
        manual_view["provider_finalization_verified"] = "NOT_VERIFIED"
        manual_view["local_regular_bar_coherence"] = local_regular_bars
        manual_view["technical_analysis_eligibility"] = "NOT_VERIFIED"
    # Preserve acquisition cutoff and later analysis observation without backdating.
    manual_view["analysis_observed_at"] = initial_observation
    manual_view["acquisition_completed_at"] = acquisition_complete_cutoff
    handoff = _captured_acquisition_handoff(
        account_requests + market_requests, account_results + market_results, captures,
        observed_at=initial_observation, cutoff=cutoff,
        maximum_age_seconds=maximum_broker_age_seconds,
    )
    if handoff is not None:
        manual_view["acquisition_handoff"] = handoff

    hard_fail_reasons: list[str] = []
    partial_reasons: list[str] = []
    unknowns: list[str] = ["EVENT_EVIDENCE_NOT_EVALUATED_M1"]
    if acquisition_complete_cutoff is not None and observed_dt > cutoff_dt and handoff is None:
        partial_reasons.append("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE")
    if acquisition_complete_cutoff is None:
        hard_fail_reasons.append("ACQUISITION_TIMESTAMP_INVALID")
    if not authority_revalidation_valid:
        hard_fail_reasons.append("AUTHORITY_REVALIDATION_AT_ACQUISITION_CUTOFF_FAILED")
    if session_rollover_detected:
        hard_fail_reasons.append("ACQUISITION_SESSION_ROLLOVER")
    elif acquisition_complete_cutoff is not None and not session_identity_revalidated:
        hard_fail_reasons.append("ACQUISITION_SESSION_IDENTITY_NOT_REVALIDATED")
    for operation in omitted_operations:
        partial_reasons.append("NOT_REQUESTED:" + operation)
    # Missing scope is not an endpoint failure; genuine failures remain visible.
    if kiwoom_health_status != "HEALTHY" and "oauth_health" in requested_market:
        hard_fail_reasons.append("KIWOOM_UNAVAILABLE")
    if broker_status == "UNAVAILABLE" and "account_holdings_read" in requested_accounts:
        hard_fail_reasons.append("BROKER_HOLDINGS_UNAVAILABLE")
    elif broker_status == "UNAVAILABLE":
        partial_reasons.append("BROKER_HOLDINGS_NOT_REQUESTED")
    elif broker_status == "INCOMPLETE":
        hard_fail_reasons.append("BROKER_HOLDINGS_INCOMPLETE")
    for request, result in zip(account_requests, account_results):
        if result.get("bridge_status") != "PASS":
            partial_reasons.append("ACCOUNT_EVIDENCE_NOT_VERIFIED:" + request["operation"])
    for request, result in zip(market_requests, market_results):
        if result.get("bridge_status") != "PASS":
            ticker_suffix = ":" + request["ticker"] if request.get("ticker") else ""
            partial_reasons.append("MARKET_EVIDENCE_NOT_VERIFIED:" + request["operation"] + ticker_suffix)
    if captures:
        # Re-reading a saved failure cannot freshen its timestamp or old successes.
        try:
            timestamps = _evidence_timestamps(account_timing, market_timing)
            stale = any((observed_dt - _timestamp(value)).total_seconds() > maximum_broker_age_seconds
                        for value in timestamps)
            future = any(_timestamp(value) > observed_dt for value in timestamps)
        except (TypeError, ValueError):
            stale, future = False, True
        if stale:
            hard_fail_reasons.append("PARENT_CAPTURE_REPLAY_STALE")
        if future:
            hard_fail_reasons.append("PARENT_CAPTURE_REPLAY_FUTURE")
    if orderable_cash_status != "VERIFIED":
        partial_reasons.append("ORDERABLE_CASH_NOT_VERIFIED")
    missing_current = [item["ticker"] for item in current_price_evidence if item["status"] != "AVAILABLE"]
    if missing_current:
        partial_reasons.append("CURRENT_PRICE_UNAVAILABLE:" + ",".join(missing_current))
    if current_session_finalization_status != "VERIFIED":
        unknowns.append("CURRENT_SESSION_FINALIZATION_NOT_VERIFIED")
    if identity_authority_status != "VERIFIED":
        partial_reasons.append(
            "IDENTITY_AUTHORITY_NOT_VERIFIED:" + ",".join(identity_authority_reasons)
        )
    if session_authority_status != "VERIFIED" and authority_views:
        partial_reasons.append(
            "SESSION_AUTHORITY_NOT_VERIFIED:" + ",".join(session_authority_reasons)
        )
    if integrated_authority_cohort_status != "MATCHED":
        partial_reasons.append("INTEGRATED_AUTHORITY_COHORT_NOT_VERIFIED")
    missing_technical = [item["ticker"] for item in finalized_results if item["status"] != "VERIFIED"]
    if missing_technical or historical_status in {"PARTIAL", "UNAVAILABLE"}:
        unknowns.append("TECHNICAL_EVIDENCE_INCOMPLETE:" + ",".join(sorted(set(missing_technical))))

    temporal_valid = bool(
        acquisition_complete_cutoff is not None
        and _temporal_evidence_valid(
            acquisition_complete_cutoff, account_timing, market_timing,
        )
    )
    if not temporal_valid:
        hard_fail_reasons.append("TEMPORAL_EVIDENCE_VIOLATION")

    hard_fail_reasons = sorted(set(hard_fail_reasons))
    partial_reasons = sorted(set(partial_reasons))
    unknowns = sorted(set(unknowns))
    preflight_status = "FAIL" if hard_fail_reasons else "PARTIAL" if partial_reasons else "PASS"
    real_data_verified = bool(
        tickers
        and kiwoom_health_status == "HEALTHY"
        and broker_status == "AVAILABLE"
        and orderable_cash_status == "VERIFIED"
        and current_price_status == "AVAILABLE"
        and historical_status == "AVAILABLE"
        and finalized_bar_preflight_pass
        and identity_authority_status == "VERIFIED"
        and session_authority_status == "VERIFIED"
        and integrated_authority_cohort_status == "MATCHED"
        and preflight_status == "PASS"
        and temporal_valid
    )
    if preflight_status == "FAIL":
        manual_data_status = "FAILED"
    elif real_data_verified:
        manual_data_status = "VERIFIED_REAL_DATA"
    elif preflight_status == "PARTIAL":
        manual_data_status = "PARTIAL"
    else:
        manual_data_status = "NOT_VERIFIED"

    requested_evidence_grade = "GRADE_B" if real_data_verified else "UNVERIFIED"
    authority_snapshot_provenance = (
        integrated_snapshot.provenance(
            authority_source=(
                "K3_COMBINED_SHADOW"
                if k3_shadow_combined_activation is not None
                else "K3_COMBINED_PRODUCTION"
            ),
            report_decision_as_of=cutoff,
        )
        if integrated_snapshot is not None
        else {
            "authority_source": "LEGACY_INDEPENDENT",
            "combined_activation_manifest_sha256": None,
            "activation_cohort_id": (
                identity_activation_cohort_id
                if identity_activation_cohort_id == session_activation_cohort_id
                else None
            ),
            "instrument_identity_artifact_sha256": identity_registry_hash,
            "session_calendar_artifact_sha256": calendar_hash,
            "identity_registry_version": identity_registry_version,
            "session_calendar_version": None,
            "authority_resolved_at": None,
            "snapshot_decision_as_of": initial_authority_cutoff,
            "report_decision_as_of": cutoff,
            "run_id": run_id,
        }
    )
    provenance_input = {
        "execution_origin": "MANUAL",
        "decision_mode": "MANUAL_READ_ONLY",
        "evidence_grade": requested_evidence_grade,
        "manual_data_verification_status": manual_data_status,
        "kiwoom_health_status": kiwoom_health_status,
        "broker_snapshot_status": broker_status,
        "orderable_cash_status": orderable_cash_status,
        "current_price_status": current_price_status,
        "historical_daily_evidence_status": historical_status,
        "finalized_bar_preflight_status": finalized_bar_preflight_status,
        "identity_authority_status": identity_authority_status,
        "session_authority_status": session_authority_status,
        "integrated_authority_cohort_status": integrated_authority_cohort_status,
        "integrated_authority_snapshot_provenance": authority_snapshot_provenance,
        "preflight_status": preflight_status,
        "manual_analysis_view": manual_view,
        "provenance_evidence": {
            "manual_run_id": run_id,
            "operator_initiated": True,
            "trigger_type": "USER_INITIATED",
        },
        "temporal_evidence_status": (
            "TEMPORAL_EVIDENCE_VALID" if temporal_valid else "TEMPORAL_EVIDENCE_VIOLATION"
        ),
    }
    provenance = derive_run_provenance(provenance_input, provenance_policy)
    expected_provenance = {
        "run_provenance_status": "VERIFIED_MANUAL",
        "evidence_grade": requested_evidence_grade,
        "maturity_eligible": False,
        "operational_maturity_eligible": False,
        "policy_evolution_eligible": False,
    }
    if any(provenance.get(key) != value for key, value in expected_provenance.items()):
        raise RuntimeError("CANONICAL_MANUAL_PROVENANCE_MISMATCH")

    report = {
        "schema_version": "2.1",
        "report_type": "MANUAL_PORTFOLIO_ANALYSIS_PREFLIGHT",
        "manual_run_id": run_id,
        "run_mode": "MANUAL_READ_ONLY",
        "trigger_type": "USER_INITIATED",
        "operator_initiated": True,
        "decision_as_of": cutoff,
        "observed_at": initial_observation,
        "market_phase": market_phase,
        "trading_date": trading_date,
        "run_provenance_status": provenance["run_provenance_status"],
        "evidence_grade": provenance["evidence_grade"],
        "maturity_eligible": provenance["maturity_eligible"],
        "operational_maturity_eligible": provenance["operational_maturity_eligible"],
        "policy_evolution_eligible": provenance["policy_evolution_eligible"],
        "provenance": provenance,
        "manual_data_verification_status": manual_data_status,
        "kiwoom_capability_status": "VERIFIED_READ_ONLY",
        "kiwoom_capabilities_checked": [
            "OAUTH_HEALTH",
            "ACCOUNT_DEPOSIT_READ",
            "ACCOUNT_HOLDINGS_READ",
            "MARKET_QUOTE_READ",
            "DAILY_CHART_READ",
        ],
        "kiwoom_health_status": kiwoom_health_status,
        "broker_snapshot_status": broker_status,
        "broker_snapshot_as_of": broker_state.get("as_of"),
        "broker_diff_status": broker_diff_status,
        "broker_diff_details": broker_diff_details,
        "orderable_cash_status": orderable_cash_status,
        "verified_orderable_cash_usd": verified_orderable_cash,
        "current_price_status": current_price_status,
        "historical_daily_evidence_status": historical_status,
        "identity_authority_status": identity_authority_status,
        "identity_authority_reasons": identity_authority_reasons,
        "identity_authority_id": identity_authority_id,
        "identity_registry_version": identity_registry_version,
        "identity_registry_hash": identity_registry_hash,
        "identity_activation_cohort_id": identity_activation_cohort_id,
        "session_authority_status": session_authority_status,
        "session_authority_reasons": session_authority_reasons,
        "session_authority_market_phase": session_authority_market_phase,
        "calendar_policy_identity": "US_EQUITIES_CORE_SESSION_V2",
        "calendar_hash": calendar_hash,
        "session_activation_cohort_id": session_activation_cohort_id,
        "integrated_authority_cohort_status": integrated_authority_cohort_status,
        "integrated_authority_snapshot_provenance": authority_snapshot_provenance,
        "expected_completed_us_session": expected_completed_session,
        "finalized_bar_preflight_status": finalized_bar_preflight_status,
        "current_session_finalization_status": current_session_finalization_status,
        "last_verified_finalized_bar_status": finalized_status,
        "last_verified_finalized_bar_date": last_finalized_date,
        "preflight_status": preflight_status,
        "hard_fail_reasons": hard_fail_reasons,
        "partial_reasons": partial_reasons,
        "unknowns": unknowns,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
        "backfill": False,
        "scheduled_occurrence_id": None,
        "scheduled_pair_eligible": False,
        "mutation_status": "REPORT_ONLY_CREATE_ONLY",
        "broker_observed_state": broker_state,
        "system_portfolio_state": system_state,
        "manual_analysis_view": manual_view,
        "current_price_evidence": current_price_evidence,
        "historical_daily_evidence": historical_daily_evidence,
        "last_verified_finalized_bars": finalized_results,
        "event_evidence_status": "NOT_EVALUATED_M1",
        "technical_evidence_status": "REPORT_ONLY_M1",
    }
    if direction_only is True:
        manual_view["decision_evidence_scope"] = "EXISTING_HOLDINGS_AND_CASH_DIRECTION_ONLY"
        eligible = validate_manual_direction_evidence(
            report, parent_capture_artifacts, analysis_observed_at=initial_observation,
        )
        if eligible:
            report["manual_data_verification_status"] = "VERIFIED_REAL_DATA"
            report["evidence_grade"] = "GRADE_B"
        else:
            report["evidence_grade"] = "UNVERIFIED"
            if report["manual_data_verification_status"] == "VERIFIED_REAL_DATA":
                report["manual_data_verification_status"] = "NOT_VERIFIED"
        provenance_input.update(evidence_grade=report["evidence_grade"],
                                manual_data_verification_status=report["manual_data_verification_status"])
        provenance = derive_run_provenance(
            provenance_input, provenance_policy, direction_evidence=report,
            parent_capture_artifacts=parent_capture_artifacts, analysis_observed_at=initial_observation,
        )
        if provenance["evidence_grade"] != report["evidence_grade"]:
            raise RuntimeError("CANONICAL_MANUAL_PROVENANCE_MISMATCH")
        report["provenance"] = provenance
    return report


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _require_lexical_descendant(path: Path, trusted_root: Path) -> None:
    root_text = os.path.normcase(os.fspath(trusted_root))
    path_text = os.path.normcase(os.fspath(path))
    try:
        common = os.path.commonpath((root_text, path_text))
    except ValueError as exc:
        raise ValueError("MANUAL_OUTPUT_OUTSIDE_TRUSTED_ROOT") from exc
    if common != root_text:
        raise ValueError("MANUAL_OUTPUT_OUTSIDE_TRUSTED_ROOT")


def _windows_final_path(handle: int) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    get_final_path.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_final_path(handle, buffer, len(buffer), 0)
    if length == 0 or length >= len(buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    return value[4:] if value.startswith("\\\\?\\") else value


def _windows_open_locked_directory(path: Path) -> int:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    handle = create_file(
        os.fspath(path),
        0x80000000,  # GENERIC_READ: blocks delete/rename when FILE_SHARE_DELETE is absent
        0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
        None,
        3,  # OPEN_EXISTING
        0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())

    class FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [("file_attributes", wintypes.DWORD), ("reparse_tag", wintypes.DWORD)]

    info = FileAttributeTagInfo()
    get_info = kernel32.GetFileInformationByHandleEx
    get_info.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    if not get_info(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
        error = ctypes.WinError(ctypes.get_last_error())
        close_handle(handle)
        raise error
    if info.file_attributes & 0x00000400:  # FILE_ATTRIBUTE_REPARSE_POINT
        close_handle(handle)
        raise ValueError("MANUAL_OUTPUT_REPARSE_POINT_REJECTED")
    final_path = _windows_final_path(handle)
    if os.path.normcase(os.path.abspath(final_path)) != os.path.normcase(os.path.abspath(path)):
        close_handle(handle)
        raise ValueError("MANUAL_OUTPUT_PATH_IDENTITY_MISMATCH")
    return int(handle)


@contextlib.contextmanager
def _windows_locked_output_target(
    *, trusted_root: Path, output_root: Path, run_id: str,
) -> Iterator[Path]:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    handles: list[int] = []
    try:
        handles.append(_windows_open_locked_directory(trusted_root))
        relative = Path(os.path.relpath(output_root, trusted_root))
        current = trusted_root
        if relative != Path("."):
            for component in relative.parts:
                current = current / component
                try:
                    current.mkdir()
                except FileExistsError:
                    pass
                handles.append(_windows_open_locked_directory(current))
        run_directory = output_root / run_id
        run_directory.mkdir(exist_ok=False)
        handles.append(_windows_open_locked_directory(run_directory))
        yield run_directory / "manual-portfolio-analysis.json"
    finally:
        for handle in reversed(handles):
            close_handle(handle)


def _write_posix_create_only(
    payload: bytes, *, trusted_root: Path, output_root: Path, run_id: str,
) -> Path:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    handles: list[int] = []
    try:
        current_handle = os.open(trusted_root, directory_flags)
        handles.append(current_handle)
        relative = Path(os.path.relpath(output_root, trusted_root))
        if relative != Path("."):
            for component in relative.parts:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=current_handle)
                except FileExistsError:
                    pass
                current_handle = os.open(component, directory_flags, dir_fd=current_handle)
                handles.append(current_handle)
        os.mkdir(run_id, mode=0o700, dir_fd=current_handle)
        run_handle = os.open(run_id, directory_flags, dir_fd=current_handle)
        handles.append(run_handle)
        file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        file_handle = os.open(
            "manual-portfolio-analysis.json", file_flags, 0o600, dir_fd=run_handle,
        )
        with os.fdopen(file_handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return output_root / run_id / "manual-portfolio-analysis.json"
    finally:
        for handle in reversed(handles):
            os.close(handle)


def _write_immutable_report(
    report: dict[str, Any], *, output_root: Path, schema_path: Path,
    trusted_root: Path,
) -> Path:
    """Internal/test injection point; production uses the fixed repository namespace."""
    if (report.get("run_mode") != "MANUAL_READ_ONLY" or report.get("trigger_type") != "USER_INITIATED"
            or report.get("operator_initiated") is not True or report.get("scheduled_occurrence_id") is not None
            or report.get("evidence_grade") not in {"GRADE_B", "UNVERIFIED"}
            or report.get("run_provenance_status") != "VERIFIED_MANUAL"
            or (report.get("provenance") or {}).get("execution_origin") != "MANUAL"
            or (report.get("provenance") or {}).get("decision_mode") != "MANUAL_READ_ONLY"
            or (report.get("provenance") or {}).get("run_provenance_status") != "VERIFIED_MANUAL"
            or (report.get("provenance") or {}).get("evidence_grade") != report.get("evidence_grade")):
        raise ValueError("MANUAL_REPORT_MODE_MISMATCH")
    errors = validate_instance(report, schema_path)
    if errors:
        raise ValueError("MANUAL_REPORT_SCHEMA_INVALID:" + "; ".join(errors))
    run_id = validate_manual_run_id(str(report["manual_run_id"]))
    trusted = _lexical_absolute(trusted_root)
    output = _lexical_absolute(output_root)
    _require_lexical_descendant(output, trusted)
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if os.name != "nt":
        return _write_posix_create_only(
            payload, trusted_root=trusted, output_root=output, run_id=run_id,
        )
    with _windows_locked_output_target(
        trusted_root=trusted, output_root=output, run_id=run_id,
    ) as target:
        try:
            with target.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            if target.exists() and target.stat().st_size == 0:
                target.unlink()
            raise
        return target


def write_immutable_report(report: dict[str, Any], *, schema_path: Path) -> Path:
    """Create a report only in the fixed repository-owned manual namespace."""
    return _write_immutable_report(
        report,
        output_root=ROOT / "workspace/outputs/manual-portfolio-analysis",
        schema_path=schema_path,
        trusted_root=ROOT,
    )


def validate_scheduled_input(
    evidence: dict[str, Any], supplied: dict[str, Any], *, evidence_sha256: str,
    expected_head: str, runtime_repo: Path = ROOT,
    session_authority_resolver: Callable[..., Any] = derive_us_market_session_authority,
) -> dict[str, Any]:
    """Validate an externally supplied scheduled run; never collect or promote it.

    scheduled_run_id identifies the logical run, while run_id identifies this
    analysis and scheduled_occurrence_id identifies the task/phase occurrence.
    The caller supplies an existing run and deployment manifest on every call.
    This is a compilation gate, not operational maturity or delivery evidence.
    """
    from continuous_improvement_sidecar import validate_temporal_evidence
    from deployment_provenance import verify_current_provenance
    from validation_common import canonical_hash

    if not isinstance(supplied, dict) or not isinstance(supplied.get("run"), dict):
        raise ValueError("SCHEDULED_PROVENANCE_REQUIRED")
    run = supplied["run"]
    pe = run.get("provenance_evidence")
    manifest = supplied.get("deployment_provenance")
    if not isinstance(pe, dict) or not isinstance(manifest, dict):
        raise ValueError("SCHEDULED_PROVENANCE_REQUIRED")
    policy_path = runtime_repo / "workspace/policies/continuous_improvement_policy.json"
    failures = verify_current_provenance(
        manifest, expected_head=expected_head, runtime_repo=runtime_repo,
        provider_scope_path=runtime_repo / "workspace/policies/kiwoom-session-aware-priority-policy.json",
        progress_path=runtime_repo / "workspace/state/integrated_shadow/shadow_progress.json",
        required_code_paths=(
            "manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py",
            "manage-us-stock-strategy/scripts/portfolio_decision_dashboard.py",
            "manage-us-stock-strategy/scripts/portfolio_decision_order_intent.py",
            "manage-us-stock-strategy/scripts/deployment_provenance.py",
            "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json",
        ),
        required_policy_paths=("workspace/policies/continuous_improvement_policy.json",),
    )
    if failures:
        raise ValueError("SCHEDULED_DEPLOYMENT_NOT_VERIFIED:" + ";".join(sorted(set(failures))))
    policy_bytes = policy_path.read_bytes()
    policy = json.loads(policy_bytes)
    if hashlib.sha256(policy_bytes).hexdigest() != (manifest.get("policy_hashes") or {}).get("workspace/policies/continuous_improvement_policy.json"):
        failures.append("SCHEDULED_CONSUMED_POLICY_HASH_MISMATCH")
    expected_mode = {
        "report_type": "SCHEDULED_PORTFOLIO_ANALYSIS_PREFLIGHT",
        "run_mode": "LIVE_READ_ONLY", "trigger_type": "SCHEDULED_GENUINE",
        "operator_initiated": False, "run_provenance_status": "VERIFIED_SCHEDULED",
        "evidence_grade": "GRADE_A", "backfill": False,
        "maturity_eligible": False, "operational_maturity_eligible": False,
        "policy_evolution_eligible": False, "scheduled_pair_eligible": False,
    }
    if any(evidence.get(k) != v for k, v in expected_mode.items()):
        failures.append("SCHEDULED_EVIDENCE_MODE_MISMATCH")
    if run.get("execution_origin") != "SCHEDULED_GENUINE" or run.get("decision_mode") != "LIVE_READ_ONLY":
        failures.append("SCHEDULED_SOURCE_MODE_MISMATCH")
    if pe.get("operator_initiated") is not False or pe.get("trigger_type") != "SCHEDULED_GENUINE":
        failures.append("SCHEDULED_SOURCE_TRIGGER_MISMATCH")
    if pe.get("manual_run_id") is not None:
        failures.append("MANUAL_PROVENANCE_MASQUERADING")
    if run.get("run_id") != evidence.get("manual_run_id") or run.get("decision_as_of") != evidence.get("decision_as_of"):
        failures.append("SCHEDULED_EVIDENCE_BINDING_MISMATCH")
    phase = pe.get("expected_operational_phase")
    task_phase = "REGULAR_CLOSE_T_PLUS_30" if phase == "POST_MARKET_FINALIZED" else phase
    task_mapping = {"PRE_OPEN_T_MINUS_30": "automation",
                    "REGULAR_CLOSE_T_PLUS_30": "post-close-portfolio-strategy"}
    actual_task_id = supplied.get("task_id")
    # The analytics policy uses logical phase IDs; deployment uses App task IDs.
    if (actual_task_id != task_mapping.get(task_phase) or task_phase is None
            or pe.get("task_id") != task_phase
            or not any(t.get("task_id") == actual_task_id and t.get("run_phase") == task_phase
                       for t in manifest.get("tasks", []) if isinstance(t, dict))):
        failures.append("SCHEDULED_TASK_PHASE_MAPPING_MISMATCH")
    occurrence = canonical_hash({"task_id": actual_task_id, "run_phase": phase,
                                 "scheduled_run_id": pe.get("scheduled_run_id"),
                                 "scheduled_at": supplied.get("scheduled_at")})
    if evidence.get("scheduled_occurrence_id") != occurrence or supplied.get("scheduled_occurrence_id") != occurrence:
        failures.append("SCHEDULED_OCCURRENCE_BINDING_MISMATCH")
    try:
        scheduled_at = _timestamp(supplied.get("scheduled_at"))
        observed = _timestamp(evidence.get("observed_at"))
        cutoff = _timestamp(evidence.get("decision_as_of"))
        from dual_run_scheduler import build_session_schedule
        authority = session_authority_resolver(
            evidence["decision_as_of"], primary_listing_operating_mic="XNYS",
            decision_as_of=evidence["decision_as_of"],
        )
        window = authority.current_date_session
        if (authority.authority_status != "VERIFIED" or window is None
                or authority.calendar_hash != evidence.get("calendar_hash")
                or authority.activation_cohort_id != evidence.get("session_activation_cohort_id")):
            raise ValueError("SCHEDULED_OFFICIAL_SESSION_NOT_VERIFIED")
        schedule = build_session_schedule({
            "official_calendar_verified": True, "is_trading_day": True,
            "session": window.session_date, "core_open_at": window.core_open_at,
            "core_close_at": window.core_close_at, "calendar_source": authority.calendar_hash,
        })
        times = (schedule["finalization_retry_at"] if phase == "POST_MARKET_FINALIZED" else
                 [r["scheduled_at"] for r in schedule["runs"] if r["run_phase"] == phase])
        if scheduled_at not in [_timestamp(t) for t in times] or pe.get("scheduled_run_id") != schedule["scheduled_run_id"]:
            failures.append("SCHEDULED_OFFICIAL_OCCURRENCE_MISMATCH")
        if not scheduled_at <= observed <= cutoff or (cutoff - scheduled_at).total_seconds() > 900:
            failures.append("SCHEDULED_TEMPORAL_BINDING_MISMATCH")
        if pe.get("expected_trading_day") != evidence.get("trading_date") or scheduled_at.astimezone(ET).date().isoformat() != evidence.get("trading_date"):
            failures.append("SCHEDULED_TRADING_DAY_MISMATCH")
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        failures.append("SCHEDULED_TIMESTAMP_OR_OFFICIAL_SESSION_INVALID")
    if (run.get("git_sha") != expected_head or pe.get("runtime_manifest_hash") != manifest.get("record_hash")
            or run.get("runtime_manifest_hash") != manifest.get("record_hash")
            or run.get("semantic_cohort") != manifest.get("semantic_cohort_id")):
        failures.append("SCHEDULED_DEPLOYMENT_BINDING_MISMATCH")
    portfolio_hash = (evidence.get("system_portfolio_state") or {}).get("source_sha256")
    if not portfolio_hash or run.get("portfolio_hash_before") != portfolio_hash or run.get("portfolio_hash_after") != portfolio_hash:
        failures.append("SCHEDULED_PORTFOLIO_HASH_MISMATCH")
    sources = run.get("source_artifacts")
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(s, dict) for s in sources)
            or not any(s.get("sha256") == evidence_sha256 and s.get("observed_at") == evidence.get("decision_as_of") for s in sources)):
        failures.append("SCHEDULED_SOURCE_EVIDENCE_HASH_MISSING")
    else:
        try:
            if not validate_temporal_evidence(run["decision_as_of"], sources)["evaluation_valid"]:
                failures.append("SCHEDULED_TEMPORAL_EVIDENCE_INVALID")
        except (KeyError, TypeError, ValueError):
            failures.append("SCHEDULED_TEMPORAL_EVIDENCE_INVALID")
    if run.get("temporal_evidence_status") != "TEMPORAL_EVIDENCE_VALID":
        failures.append("SCHEDULED_TEMPORAL_STATUS_REQUIRED")
    derived = derive_run_provenance(run, policy)
    if derived["run_provenance_status"] != "VERIFIED_SCHEDULED" or not derived["decision_quality_eligible"]:
        failures.append("SCHEDULED_CANONICAL_PROVENANCE_NOT_VERIFIED")
    p = evidence.get("provenance") or {}
    if any(p.get(k) != v for k, v in {
        "execution_origin": "SCHEDULED_GENUINE", "decision_mode": "LIVE_READ_ONLY",
        "run_provenance_status": "VERIFIED_SCHEDULED", "evidence_grade": "GRADE_A",
        "decision_quality_eligible": True, "maturity_eligible": False,
        "operational_maturity_eligible": False, "policy_evolution_eligible": False,
    }.items()):
        failures.append("SCHEDULED_REPORT_PROVENANCE_MISMATCH")
    if failures:
        raise ValueError("SCHEDULED_INPUT_NOT_VERIFIED:" + ";".join(sorted(set(failures))))
    return {"trigger_type": "SCHEDULED_GENUINE",
            "run_provenance_status": "VERIFIED_SCHEDULED_GENUINE",
            "actual_scheduled_run": True, "scheduled_occurrence_id": occurrence,
            "operational_grade": "GRADE_A_CANDIDATE", "scheduled_maturity_promoted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the M1 manual read-only portfolio preflight")
    parser.add_argument("--manual-run-id", default=None)
    parser.add_argument("--decision-as-of")
    parser.add_argument("--observed-at")
    parser.add_argument("--ticker", action="append", default=[])
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--readonly-policy", type=Path)
    parser.add_argument("--rate-policy", type=Path)
    parser.add_argument("--broker-policy", type=Path)
    parser.add_argument("--provenance-policy", type=Path)
    parser.add_argument("--portfolio-state", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument(
        "--k3-shadow-combined-activation",
        type=Path,
        help="Explicit non-authoritative combined manifest override for validation only",
    )
    parser.add_argument("--input-mode", choices=("MANUAL_READ_ONLY", "LIVE_READ_ONLY"), default="MANUAL_READ_ONLY")
    parser.add_argument("--portfolio-evidence", type=Path)
    parser.add_argument("--scheduled-provenance", type=Path)
    parser.add_argument("--decision-plan", type=Path)
    parser.add_argument("--current-session-context", type=Path)
    parser.add_argument("--expected-runtime-head")
    args = parser.parse_args()
    if args.input_mode == "LIVE_READ_ONLY":
        if not all((args.portfolio_evidence, args.scheduled_provenance, args.decision_plan, args.expected_runtime_head)):
            parser.error("Scheduled input requires evidence, provenance, supplied Plan and expected runtime HEAD")
        from portfolio_decision_dashboard import main as compile_supplied_dashboard
        forwarded = ["--input-mode", "LIVE_READ_ONLY", "--portfolio-evidence", str(args.portfolio_evidence),
                     "--scheduled-provenance", str(args.scheduled_provenance), "--decision-plan", str(args.decision_plan),
                     "--expected-runtime-head", args.expected_runtime_head]
        if args.current_session_context:
            forwarded += ["--current-session-context", str(args.current_session_context)]
        return compile_supplied_dashboard(forwarded)
    if any((args.portfolio_evidence, args.scheduled_provenance, args.decision_plan, args.expected_runtime_head)):
        parser.error("Scheduled inputs require explicit LIVE_READ_ONLY input mode")

    repo = ROOT.resolve()
    readonly_path = args.readonly_policy or repo / "workspace/policies/kiwoom-readonly-policy.json"
    rate_path = args.rate_policy or repo / "workspace/policies/kiwoom-rate-limit-policy.json"
    broker_path = args.broker_policy or repo / "workspace/policies/kiwoom-broker-readonly-policy.json"
    provenance_path = args.provenance_policy or repo / "workspace/policies/continuous_improvement_policy.json"
    portfolio_path = args.portfolio_state or repo / "stock-strategy-system/portfolio_state.json"
    schema_path = args.schema or repo / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
    readonly_policy = load_json(readonly_path)
    runtime = (args.runtime or Path(str(readonly_policy["official_runtime_path"]))).resolve()
    if runtime != Path(str(readonly_policy["official_runtime_path"])).resolve():
        raise SystemExit("KIWOOM_RUNTIME_PATH_MISMATCH")
    rate_policy = load_json(rate_path)
    broker_policy = load_json(broker_path)
    provenance_policy = load_json(provenance_path)
    system_portfolio = load_json(portfolio_path)
    shadow_activation = args.k3_shadow_combined_activation
    production_activation = (
        None
        if shadow_activation is not None
        else repo / COMBINED_ACTIVATION_RELATIVE_PATH
    )

    report = run_manual_preflight(
        manual_run_id=args.manual_run_id or generate_manual_run_id(),
        system_portfolio=system_portfolio,
        system_portfolio_source=str(portfolio_path.resolve()),
        system_portfolio_sha256=file_hash(portfolio_path),
        provenance_policy=provenance_policy,
        account_reader=lambda requests: invoke_account_bridge_batch(
            requests, runtime=runtime, policy=rate_policy,
        ),
        market_reader=lambda requests: invoke_bridge_batch(
            requests, runtime=runtime, policy=rate_policy,
        ),
        maximum_broker_age_seconds=int(broker_policy["maximum_age_seconds"]),
        decision_as_of=args.decision_as_of,
        observed_at=args.observed_at,
        extra_tickers=args.ticker,
        k3_shadow_combined_activation=shadow_activation,
        k3_production_combined_activation=production_activation,
    )
    target = write_immutable_report(
        report,
        schema_path=schema_path,
    )
    print(json.dumps({
        "manual_run_id": report["manual_run_id"],
        "preflight_status": report["preflight_status"],
        "manual_data_verification_status": report["manual_data_verification_status"],
        "report_path": str(target),
        "order_authority": False,
    }, ensure_ascii=True, separators=(",", ":")))
    return 0 if report["preflight_status"] != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
