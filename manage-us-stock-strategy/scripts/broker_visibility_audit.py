#!/usr/bin/env python3
"""Classify Kiwoom broker visibility without inferring absence from missing APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from validation_common import canonical_hash


OFFICIAL_CAPABILITIES = {
    "open_orders": {"api_id": "ust21050", "adapter_operation": "account_open_items"},
    "current_day_fills": {"api_id": "ust21510", "adapter_operation": "account_fills_read"},
    "daily_order_fills": {"api_id": "ust21150", "adapter_operation": None},
    "orders_by_period": {"api_id": "ust21180", "adapter_operation": None},
    "current_day_realized_pnl": {"api_id": "ust21630", "adapter_operation": "account_realized_pnl_read"},
    "daily_realized_pnl": {"api_id": "ust21660", "adapter_operation": None},
    "realized_pnl": {"api_id": "ust21530", "adapter_operation": None},
}


def _result_map(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("operation")): item for item in results}


def _visibility(item: dict[str, Any] | None, *, empty_means_none: bool = False) -> dict[str, Any]:
    value = item or {}
    status = value.get("bridge_status")
    rows = value.get("data") if isinstance(value.get("data"), list) else []
    if status == "PASS":
        return {"status": "AVAILABLE", "record_count": len(rows),
                "empty_result_interpreted_as_none": bool(empty_means_none)}
    classification = {
        "KIWOOM_API_RESPONSE_ERROR": "API_RESPONSE_ERROR",
        "AUTHENTICATION_FAILURE": "AUTH_SCOPE_ERROR",
        "RUNTIME_PYTHON_UNAVAILABLE": "REQUEST_CONFIGURATION_ERROR",
    }.get(str(status), "API_RESPONSE_ERROR" if value.get("failure_type") == "API_RESPONSE_ERROR"
          else "PARTIAL_PROVIDER_SUPPORT")
    return {"status": "UNKNOWN", "record_count": None,
            "empty_result_interpreted_as_none": False, "gap_classification": classification,
            "bridge_status": status}


def build_audit(*, results: list[dict[str, Any]], snapshot: dict[str, Any]) -> dict[str, Any]:
    by_operation = _result_map(results)
    open_orders = _visibility(by_operation.get("account_open_items"))
    fills = _visibility(by_operation.get("account_fills_read"))
    realized = _visibility(by_operation.get("account_realized_pnl_read"))
    holdings = _visibility(by_operation.get("account_holdings_read"))
    deposit = _visibility(by_operation.get("account_deposit_read"))
    gaps = []
    for capability, metadata in OFFICIAL_CAPABILITIES.items():
        operation = metadata["adapter_operation"]
        if operation is None:
            gaps.append({"capability": capability, "api_id": metadata["api_id"],
                         "classification": "OFFICIAL_API_SUPPORTED_ADAPTER_MISSING"})
        else:
            observed = _visibility(by_operation.get(operation))
            if observed["status"] != "AVAILABLE":
                gaps.append({"capability": capability, "api_id": metadata["api_id"],
                             "classification": observed.get("gap_classification", "PARTIAL_PROVIDER_SUPPORT")})
    fresh = snapshot.get("broker_snapshot_freshness_status")
    readonly = ("BROKER_READ_ONLY_SHADOW_VERIFIED"
                if holdings["status"] == deposit["status"] == "AVAILABLE"
                else "BROKER_READ_ONLY_SHADOW_PARTIAL" if any(
                    item["status"] == "AVAILABLE" for item in (holdings, deposit, fills, realized, open_orders)
                ) else "BROKER_READ_ONLY_SHADOW_FAILED")
    runtime_commit = next((item.get("runtime_commit") for item in results if item.get("runtime_commit")), None)
    value = {
        "schema_version": "1.0", "status": "FUTURE_EXECUTION_BROKER_VISIBILITY_AUDIT",
        "provider": "KIWOOM_REST", "runtime_commit": runtime_commit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_freshness_status": fresh if fresh in {"FRESH", "STALE"} else "UNAVAILABLE",
        "cash_visibility": {**deposit, "verified_held_cash_usd": (snapshot.get("cash") or {}).get("settled_available_cash")},
        "holdings_visibility": holdings, "open_orders_visibility": open_orders,
        "fills_visibility": fills, "realized_pnl_visibility": realized,
        "capability_gaps": gaps, "current_readonly_readiness": readonly,
        "broker_visibility_for_live_execution": "READY" if (
            fresh == "FRESH" and open_orders["status"] == fills["status"] == "AVAILABLE"
        ) else "NOT_READY",
        "fill_inference_performed": False, "portfolio_mutation": False,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
        "record_hash": "0" * 64,
    }
    value["record_hash"] = canonical_hash({key: item for key, item in value.items() if key != "record_hash"})
    return value
