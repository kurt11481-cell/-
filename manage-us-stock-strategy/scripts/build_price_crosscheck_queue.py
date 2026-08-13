#!/usr/bin/env python3
"""Build the deterministic v2.5 selective completed-close verification queue."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from price_evidence import crosscheck_required, primary_validation, request_id


def build_queue(*, completed_session: str, market_snapshot: dict[str, Any],
                candidate_dispositions: list[dict[str, Any]], holding_strategies: list[dict[str, Any]],
                hard_risk_result: dict[str, Any], requested_at: str | None = None) -> dict[str, Any]:
    requested_at = requested_at or datetime.now(timezone.utc).isoformat()
    rows = market_snapshot.get("symbols") or {}
    reasons: dict[str, str] = {}
    boundaries: dict[str, list[dict[str, Any]]] = {}
    for item in candidate_dispositions:
        reason = crosscheck_required(opportunity_state=item.get("opportunity_state"),
                                     material_near_trigger=item.get("material_near_trigger") is True)
        if reason:
            reasons[item["ticker"]] = reason
    for item in holding_strategies:
        reason = crosscheck_required(strategy_state=item.get("strategy_state"),
                                     hard_risk_boundary=item.get("breach_observation_status") == "PRIMARY_BREACH_OBSERVED")
        if reason:
            reasons[item["ticker"]] = reason
        boundary = item.get("hard_risk_boundary_usd")
        if isinstance(boundary, (int, float)):
            boundaries.setdefault(item["ticker"], []).append({"boundary_id": item.get("policy_rule_id") or "HARD_RISK",
                                                                "operator": "less_than_or_equal", "value": boundary})
    for item in hard_risk_result.get("candidates", []):
        if item.get("event_type") == "holding_max_loss_breach" and item.get("breached") is True:
            reasons[item["symbol"]] = "HARD_RISK_BOUNDARY"
            boundary = item.get("boundary_usd")
            if isinstance(boundary, (int, float)):
                boundaries.setdefault(item["symbol"], []).append({"boundary_id": item.get("event_key", "HARD_RISK"),
                                                                    "operator": "less_than_or_equal", "value": boundary})
    queue: list[dict[str, Any]] = []
    for ticker in sorted(reasons):
        row = rows.get(ticker)
        primary = primary_validation(row, completed_session)
        if primary["primary_status"] != "VALIDATED":
            continue
        existing = row.get("quote_crosscheck") if isinstance(row, dict) else None
        if (
            isinstance(existing, dict)
            and str(existing.get("status", "")).lower() == "verified"
            and existing.get("independent_of_builder") is True
            and existing.get("bar_date") == completed_session
        ):
            continue
        queue.append({"ticker": ticker, "completed_session": completed_session,
                      "primary_close": float(row["close"]), "price_basis": primary["primary_price_basis"],
                      "currency": row.get("currency", "USD"), "primary_exchange": row.get("exchange"),
                      "reason": reasons[ticker], "decision_boundaries": boundaries.get(ticker, []),
                      "request_id": request_id(ticker, completed_session, reasons[ticker]),
                      "requested_at": requested_at, "order_authority": False})
    return {"schema_version": "2.5", "completed_session": completed_session,
            "crosscheck_requirement": "REQUIRED" if queue else "NOT_REQUIRED",
            "capability_status": "PENDING" if queue else "NOT_REQUIRED",
            "global_failure": None, "queue": queue, "order_authority": False}
