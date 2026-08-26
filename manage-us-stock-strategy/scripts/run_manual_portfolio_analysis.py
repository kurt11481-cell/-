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
import json
import math
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from continuous_improvement_sidecar import derive_run_provenance
from instrument_identity_authority import resolve_instrument_identity
from kiwoom_account_readonly_bridge import invoke_account_bridge_batch
from kiwoom_broker_shadow import normalize_snapshot
from kiwoom_runtime_bridge import invoke_bridge_batch
from session_aware_market_data import (
    ET,
    kiwoom_broker_quote_observation,
    kiwoom_daily_observation,
    market_session_at,
)
from session_authority import derive_us_market_session_authority
from validation_common import file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_READ_OPERATIONS = (
    "account_deposit_read",
    "account_deposit_detail_read",
    "account_holdings_read",
    "account_open_items",
    "account_fills_read",
    "account_realized_pnl_read",
)
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
    state = {
        "state_type": "BROKER_OBSERVED_STATE",
        "status": broker_status,
        "as_of": snapshot.get("broker_snapshot_as_of"),
        "scope_complete": snapshot.get("scope_complete") is True,
        "operation_statuses": snapshot.get("operation_statuses") or {},
        "holdings": snapshot.get("holdings") or [],
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
            ticker: broker_costs.get(ticker, (system_state.get("average_cost_usd") or {}).get(ticker))
            for ticker in holdings
        }
        source = "BROKER_OBSERVED_STATE"
    else:
        holdings = dict(system_state.get("holdings") or {})
        costs = dict(system_state.get("average_cost_usd") or {})
        source = "SYSTEM_PORTFOLIO_STATE_FALLBACK"
    verified_cash = _number((broker_state.get("cash") or {}).get("settled_available_cash"))
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


def _authority_context(
    tickers: list[str], *, observed_at: str, decision_as_of: str,
) -> dict[str, Any]:
    """Resolve the existing Identity/Calendar authority contract at one boundary."""
    identity_views = {}
    authority_views = {}
    for ticker in tickers:
        identity_view = resolve_instrument_identity(ticker, decision_as_of=decision_as_of)
        identity_views[ticker] = identity_view
        if identity_view.authority_status != "VERIFIED":
            continue
        authority_views[ticker] = derive_us_market_session_authority(
            observed_at,
            primary_listing_operating_mic=identity_view.primary_listing_operating_mic,
            decision_as_of=decision_as_of,
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
) -> dict[str, Any]:
    """Collect and validate M1 evidence without writing or invoking strategy logic."""
    run_id = validate_manual_run_id(manual_run_id)
    initial_observation = observed_at or _utc_now()
    observed_dt = _timestamp(initial_observation)
    initial_trading_date = observed_dt.astimezone(ET).date().isoformat()
    initial_market_phase = market_session_at(initial_observation)
    initial_authority_cutoff = decision_as_of or initial_observation
    _timestamp(initial_authority_cutoff)

    account_requests = [{"operation": operation} for operation in ACCOUNT_READ_OPERATIONS]
    account_results = _safe_reader_call(
        account_reader, account_requests, unavailable_status="KIWOOM_ACCOUNT_UNAVAILABLE",
    )
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
    market_results = _safe_reader_call(
        market_reader, market_requests, unavailable_status="KIWOOM_API_UNAVAILABLE",
    )
    acquisition_complete_cutoff = _acquisition_complete_cutoff(
        account_results, market_results,
    )
    cutoff = acquisition_complete_cutoff or initial_authority_cutoff
    cutoff_dt = _timestamp(cutoff)
    if acquisition_complete_cutoff is not None:
        authority_context = _authority_context(
            tickers, observed_at=cutoff, decision_as_of=cutoff,
        )
        broker_state, broker_status = _normalize_broker_state(
            account_results,
            observed_at=cutoff,
            maximum_age_seconds=maximum_broker_age_seconds,
        )
    else:
        authority_context = initial_authority_context
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
    for ticker in tickers:
        identity_view = identity_views[ticker]
        authority_view = authority_views.get(ticker)
        daily_response = _operation_result(market_results, "daily_chart", ticker)
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
    verified_orderable_cash = _number(cash.get("settled_available_cash"))
    orderable_cash_status = "VERIFIED" if verified_orderable_cash is not None else "NOT_VERIFIED"
    broker_diff_status, broker_diff_details = compare_broker_and_system(broker_state, system_state)
    manual_view = _manual_analysis_view(broker_state, system_state)

    hard_fail_reasons: list[str] = []
    partial_reasons: list[str] = []
    unknowns: list[str] = ["EVENT_EVIDENCE_NOT_EVALUATED_M1"]
    if acquisition_complete_cutoff is None:
        hard_fail_reasons.append("ACQUISITION_TIMESTAMP_INVALID")
    if not authority_revalidation_valid:
        hard_fail_reasons.append("AUTHORITY_REVALIDATION_AT_ACQUISITION_CUTOFF_FAILED")
    if session_rollover_detected:
        hard_fail_reasons.append("ACQUISITION_SESSION_ROLLOVER")
    elif acquisition_complete_cutoff is not None and not session_identity_revalidated:
        hard_fail_reasons.append("ACQUISITION_SESSION_IDENTITY_NOT_REVALIDATED")
    if kiwoom_health_status != "HEALTHY":
        hard_fail_reasons.append("KIWOOM_UNAVAILABLE")
    if broker_status == "UNAVAILABLE":
        hard_fail_reasons.append("BROKER_HOLDINGS_UNAVAILABLE")
    elif broker_status == "INCOMPLETE":
        hard_fail_reasons.append("BROKER_HOLDINGS_INCOMPLETE")
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
            acquisition_complete_cutoff, account_results, market_results,
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
    provenance = derive_run_provenance({
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
    }, provenance_policy)
    expected_provenance = {
        "run_provenance_status": "VERIFIED_MANUAL",
        "evidence_grade": requested_evidence_grade,
        "maturity_eligible": False,
        "operational_maturity_eligible": False,
        "policy_evolution_eligible": False,
    }
    if any(provenance.get(key) != value for key, value in expected_provenance.items()):
        raise RuntimeError("CANONICAL_MANUAL_PROVENANCE_MISMATCH")

    return {
        "schema_version": "2.0",
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
    args = parser.parse_args()

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
