#!/usr/bin/env python3
"""Non-executing broker-event, reconciliation, intent, risk and gateway contracts."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from validation_common import canonical_hash

ORDER_API_IDS = {"ust20000", "ust20001", "ust20002", "ust20003", "ust31490"}
ORDER_PATHS = {"/api/us/ordr"}


def normalize_broker_event(raw: dict[str, Any], *, seen_ids: set[str]) -> dict[str, Any]:
    event_id = str(raw.get("event_id") or "")
    source = str(raw.get("source") or "KIWOOM_REALTIME")
    value = {
        "schema_version": "1.0", "event_id": event_id,
        "broker_order_id_masked": str(raw.get("broker_order_id_masked") or ""),
        "ticker": str(raw.get("ticker") or ""), "side": raw.get("side"),
        "status": raw.get("status"), "fill_quantity": raw.get("fill_quantity"),
        "remaining_quantity": raw.get("remaining_quantity"), "price": raw.get("price"),
        "timestamp": raw.get("timestamp"), "source": source,
        "duplicate_or_replay": event_id in seen_ids,
        "origin": "SYSTEM_INTENT" if raw.get("known_order_intent") is True else "EXTERNAL_MANUAL_ORDER_DETECTED",
        "automatic_cancel_authority": False, "portfolio_mutation": False,
        "order_authority": False,
    }
    value["record_hash"] = canonical_hash(value)
    return value


def reconcile_broker_state(snapshot: dict[str, Any], events: list[dict[str, Any]],
                           *, now: str, freshness_status: str) -> dict[str, Any]:
    visibility = snapshot.get("open_orders_visibility") or "UNKNOWN"
    status = "STALE" if freshness_status == "STALE" else (
        "FULL" if visibility == "AVAILABLE" else "PARTIAL")
    value = {
        "schema_version": "1.0", "status": status, "as_of": now,
        "rest_snapshot_hash": snapshot.get("record_hash"),
        "incremental_event_hashes": [event.get("record_hash") for event in events],
        "open_orders_visibility": visibility,
        "rest_snapshot_is_truth_anchor": True, "events_are_incremental_only": True,
        "portfolio_research_state_separate": True, "broker_execution_state_separate": True,
        "portfolio_mutation": False, "quantity": None, "quantity_authority": "none",
        "order_authority": False,
    }
    value["record_hash"] = canonical_hash(value)
    return value


def build_order_intent(*, ticker: str, side: str, strategy_id: str,
                       decision_class: str, reason: str, expires_at: str) -> dict[str, Any]:
    created = datetime.now(timezone.utc).isoformat()
    value = {
        "schema_version": "1.0", "order_intent_id": canonical_hash({"ticker": ticker, "side": side, "created": created}),
        "ticker": ticker, "side": side, "proposed_quantity": None,
        "proposed_order_type": None, "proposed_limit_price": None,
        "strategy_id": strategy_id, "decision_class": decision_class,
        "strategy_reason": reason, "price_evidence": None, "technical_state": None,
        "event_state": None, "broker_state_reference": None,
        "created_at": created, "expires_at": expires_at, "immutable": True,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    value["record_hash"] = canonical_hash(value)
    return value


def evaluate_risk(intent: dict[str, Any], broker_state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if broker_state.get("status") != "FULL": reasons.append("BROKER_STATE_NOT_FULL")
    if broker_state.get("open_orders_visibility") != "AVAILABLE": reasons.append("OPEN_ORDERS_VISIBILITY_INSUFFICIENT")
    if intent.get("proposed_quantity") is None: reasons.append("QUANTITY_AUTHORITY_NONE")
    for key in ("price_fresh", "event_gate_clear", "technical_condition_met", "market_phase_allowed"):
        if context.get(key) is not True: reasons.append(key.upper() + "_NOT_VERIFIED")
    status = "RISK_REJECTED" if "QUANTITY_AUTHORITY_NONE" in reasons else (
        "RISK_REVIEW_REQUIRED" if reasons else "RISK_APPROVED")
    value = {
        "schema_version": "1.0", "risk_decision_id": canonical_hash({"intent": intent.get("record_hash"), "reasons": reasons}),
        "order_intent_hash": intent.get("record_hash"), "status": status,
        "reason_codes": reasons, "strategy_override_allowed": False,
        "immutable": True, "quantity": None, "quantity_authority": "none",
        "order_authority": False,
    }
    value["record_hash"] = canonical_hash(value)
    return value


def build_gateway_dry_run(intent: dict[str, Any], risk: dict[str, Any], *, api_id: str) -> dict[str, Any]:
    blocked_target = api_id in ORDER_API_IDS
    state = "AWAITING_AUTHORIZATION" if risk.get("status") != "RISK_APPROVED" else "RISK_APPROVED"
    value = {
        "schema_version": "1.0", "status": "EXECUTION_GATEWAY_DRY_RUN_ONLY",
        "order_state": state, "target_api_id": api_id,
        "target_is_write_endpoint": blocked_target, "request_payload": None,
        "network_send": False, "blind_resubmit_allowed": False,
        "ack_unknown_requires_reconciliation": True,
        "idempotency_key": canonical_hash({"intent": intent.get("record_hash"), "api": api_id}),
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    value["record_hash"] = canonical_hash(value)
    return value


def transition_order_state(current: str, event: str) -> str:
    if current == "ACK_UNKNOWN":
        return "RECONCILIATION_REQUIRED"
    transitions = {("ACKNOWLEDGED", "PARTIAL_FILL"): "PARTIALLY_FILLED",
                   ("PARTIALLY_FILLED", "FULL_FILL"): "FILLED",
                   ("ACKNOWLEDGED", "CANCEL_REQUESTED"): "CANCEL_PENDING",
                   ("CANCEL_PENDING", "CANCEL_CONFIRMED"): "CANCELED"}
    return transitions.get((current, event), "RECONCILIATION_REQUIRED")
