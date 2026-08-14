#!/usr/bin/env python3
"""Normalize sanitized Kiwoom U.S. account reads into reconciliation-only evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from validation_common import canonical_hash


SNAPSHOT_ROLES = {"PRE_OPEN_BROKER_SNAPSHOT", "POST_CLOSE_BROKER_SNAPSHOT"}
READ_OPERATIONS = {
    "account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
    "account_open_items", "account_fills_read", "account_realized_pnl_read",
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _rows(results: list[dict[str, Any]], operation: str) -> list[dict[str, Any]]:
    for result in results:
        if result.get("operation") == operation and result.get("bridge_status") in {"PASS", "PARTIAL"}:
            return [item for item in (result.get("data") or []) if isinstance(item, dict)]
    return []


def normalize_snapshot(results: list[dict[str, Any]], *, snapshot_role: str,
                       generated_at: str, maximum_age_seconds: int) -> dict[str, Any]:
    if snapshot_role not in SNAPSHOT_ROLES:
        raise ValueError("BROKER_SNAPSHOT_ROLE_INVALID")
    if any(result.get("operation") not in READ_OPERATIONS for result in results):
        raise ValueError("BROKER_OPERATION_NOT_ALLOWLISTED")
    holdings = []
    for row in _rows(results, "account_holdings_read"):
        ticker = str(row.get("stk_cd") or "").strip().upper()
        if not ticker:
            continue
        holdings.append({
            "ticker": ticker, "security_name": row.get("frgn_stk_nm"), "currency": row.get("crnc_code"),
            "settled_quantity": _number(row.get("qty")), "held_quantity": _number(row.get("poss_qty")),
            "available_shares": _number(row.get("sell_alowq")), "average_cost": _number(row.get("frgn_stk_book_uv")),
        })
    deposits = _rows(results, "account_deposit_read")
    usd = next((row for row in deposits if str(row.get("crnc_code") or "").upper() == "USD"), None)
    withdrawable = _number((usd or {}).get("fc_pymn_alowa"))
    order_available = _number((usd or {}).get("fc_ord_alowa"))
    settled_cash = min(withdrawable, order_available) if withdrawable is not None and order_available is not None else None
    detail = (_rows(results, "account_deposit_detail_read") or [{}])[0]
    unsettled = {
        "d1_sell_settlement_usd": _number(detail.get("d1_usd_sell_excta")),
        "d1_buy_settlement_usd": _number(detail.get("d1_usd_buy_excta")),
        "d2_sell_settlement_usd": _number(detail.get("d2_usd_sell_excta")),
        "d2_buy_settlement_usd": _number(detail.get("d2_usd_buy_excta")),
    }
    timestamps = [result.get("retrieved_at") for result in results if result.get("retrieved_at")]
    as_of = max(timestamps) if timestamps else generated_at
    age = max(0, int((datetime.fromisoformat(generated_at.replace("Z", "+00:00")) -
                      datetime.fromisoformat(as_of.replace("Z", "+00:00"))).total_seconds()))
    complete = all(any(result.get("operation") == operation and result.get("bridge_status") == "PASS" for result in results)
                   for operation in READ_OPERATIONS)
    operation_statuses = {
        operation: next((str(result.get("bridge_status")) for result in results
                         if result.get("operation") == operation), "NOT_RETURNED")
        for operation in sorted(READ_OPERATIONS)
    }
    snapshot = {
        "schema_version": "1.0", "snapshot_role": snapshot_role,
        "status": "KIWOOM_BROKER_SNAPSHOT_SHADOW", "generated_at": generated_at,
        "broker_snapshot_as_of": as_of, "broker_snapshot_age_seconds": age,
        "broker_snapshot_freshness_status": "FRESH" if age <= maximum_age_seconds else "STALE",
        "account_identifier_stored": False, "scope_complete": complete,
        "operation_statuses": operation_statuses,
        "holdings": sorted(holdings, key=lambda item: item["ticker"]),
        "cash": {
            "currency": "USD", "foreign_currency_deposit": _number((usd or {}).get("fc_entra")),
            "withdrawable_cash": withdrawable, "order_available_cash": order_available,
            "settled_available_cash": settled_cash,
            "cash_status": ("VERIFIED_ZERO" if settled_cash == 0 else "VERIFIED_POSITIVE" if settled_cash is not None and settled_cash > 0 else "UNVERIFIED"),
            "unsettled_funds": unsettled,
            "projected_proceeds_included": False, "margin_or_credit_included": False,
        },
        "open_orders": _rows(results, "account_open_items"),
        "fills": _rows(results, "account_fills_read"),
        "realized_pnl": _rows(results, "account_realized_pnl_read"),
        "fill_inference_performed": False, "portfolio_mutation": False,
        "quantity_authority": "none", "order_authority": False,
        "snapshot_hash": "0" * 64,
    }
    snapshot["snapshot_hash"] = canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
    return snapshot


def reconciliation_proposal(snapshot: dict[str, Any], portfolio: dict[str, Any], *,
                            expected_before_hash: str) -> dict[str, Any]:
    proposed_holdings = {item["ticker"]: item["held_quantity"] for item in snapshot["holdings"]}
    proposed_costs = {item["ticker"]: item["average_cost"] for item in snapshot["holdings"]}
    proposed_cash = snapshot["cash"]["settled_available_cash"]
    changes = []
    for field, old, proposed in (
        ("holdings", portfolio.get("holdings"), proposed_holdings),
        ("average_cost_usd", portfolio.get("average_cost_usd"), proposed_costs),
        ("available_cash_usd", portfolio.get("available_cash_usd"), proposed_cash),
    ):
        if old != proposed:
            changes.append({"field": field, "old_value": old, "proposed_value": proposed})
    return {
        "proposal_id": canonical_hash({"snapshot_hash": snapshot["snapshot_hash"], "state_revision": portfolio.get("state_revision")})[:32],
        "status": "USER_CONFIRMATION_REQUIRED", "current_state_revision": portfolio.get("state_revision"),
        "expected_before_hash": expected_before_hash, "source_timestamp": snapshot["broker_snapshot_as_of"],
        "verified_scope": "FULL" if snapshot["scope_complete"] else "PARTIAL",
        "changes": changes, "unresolved_fields": [] if snapshot["scope_complete"] else ["INCOMPLETE_ACCOUNT_SCOPE"],
        "auto_apply": False, "fill_inference_performed": False,
        "quantity_authority": "none", "order_authority": False,
    }
