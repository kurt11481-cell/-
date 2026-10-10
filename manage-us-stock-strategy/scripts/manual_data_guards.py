#!/usr/bin/env python3
"""Pinned data-accuracy guards for the manual read-only preflight.

These rules were moved out of run_manual_portfolio_analysis.py so that the
analysis adapter can change without re-pinning the Kiwoom acceptance. Every
function here is pure: no file, clock, network, or state writes.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable

from kiwoom_account_readonly_bridge import _sanitize
from kiwoom_broker_shadow import normalize_snapshot, order_available_cash_errors


BROKER_NORMALIZATION_FAILED = "BROKER_SNAPSHOT_NORMALIZATION_FAILED"


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


def normalize_broker_state(
    account_results: list[dict[str, Any]], *, observed_at: str,
    maximum_age_seconds: int,
    acquisition_cutoff: Callable[..., str | None] = _acquisition_complete_cutoff,
) -> tuple[dict[str, Any], str]:
    """Project account reads into the observed broker state; never trusted on failure."""
    normalization_failed = False
    try:
        snapshot = normalize_snapshot(
            account_results,
            snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
            generated_at=observed_at,
            maximum_age_seconds=maximum_age_seconds,
        )
    except Exception:
        normalization_failed = True
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
    if normalization_failed:
        # Empty fallback holdings are not broker evidence; they must never read as AVAILABLE.
        broker_status = "UNAVAILABLE"
    elif holdings_result is None or holdings_result.get("bridge_status") not in {"PASS", "PARTIAL"}:
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
    broker_data_as_of = acquisition_cutoff([
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
    if normalization_failed:
        state["normalization_status"] = BROKER_NORMALIZATION_FAILED
    return state, broker_status


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


def _order_available_cash(broker_state: dict[str, Any]) -> float | None:
    """Order-available cash of the observed read, or None when the F1 cash check does not pass."""
    cash = broker_state.get("cash") or {}
    order_available = _number(cash.get("order_available_cash"))
    withdrawable = _number(cash.get("withdrawable_cash"))
    if order_available is None or withdrawable is None:
        return None
    quantities = []
    for item in broker_state.get("holdings") or []:
        if isinstance(item, dict):
            settled, held = _number(item.get("settled_quantity")), _number(item.get("held_quantity"))
            quantities.append((None if settled is None else Decimal(str(settled)),
                               None if held is None else Decimal(str(held))))
    if order_available_cash_errors(Decimal(str(order_available)), Decimal(str(withdrawable)), quantities):
        return None
    return order_available


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
    # Redesign T1 F1: system cash is the Kiwoom order-available amount, trusted only when the one cash
    # check passes on the same read (unsettled proceeds must show as a sold, unsettled quantity).
    broker_cash = _order_available_cash(broker_state)
    system_cash = _number(system_state.get("available_cash_usd"))
    cash_unknown = broker_cash is None or system_cash is None
    if not cash_unknown and not math.isclose(broker_cash, system_cash, rel_tol=1e-9, abs_tol=1e-8):
        differences.append("AVAILABLE_CASH_DIFFERS")
    if differences:
        return "DIFFERENT", differences
    if cash_unknown or (system_costs and set(broker_costs) != set(system_costs)):
        return "UNKNOWN", ["COMPARISON_FIELD_UNAVAILABLE"]
    return "MATCH", []
