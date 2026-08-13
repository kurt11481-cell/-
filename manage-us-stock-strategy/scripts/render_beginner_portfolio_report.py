#!/usr/bin/env python3
"""Render canonical portfolio codes into a deterministic beginner Korean first screen."""

from __future__ import annotations

from typing import Any


PRIORITY = {"RISK_REVIEW": 1, "BROKER_SNAPSHOT_REQUIRED": 2, "BROKER_CONFIRMATION_REQUIRED": 3,
            "DATA_ISSUE": 4, "EXIT_REVIEW": 5, "REDUCE_REVIEW": 6, "ADD_REVIEW": 7,
            "ADD_PRICE_CHECK": 7, "ADD_WAIT": 8, "STRATEGY_REVIEW": 8, "HOLD_NO_ACTION": 9}


def render_beginner_summary(report: dict[str, Any], locale: dict[str, Any]) -> dict[str, Any]:
    messages = locale.get("messages") or {}
    action_keys = locale.get("action_code_keys") or {}
    items: list[dict[str, Any]] = []
    for holding in report.get("holding_strategies", []):
        code = holding.get("display_action_code", "DATA_ISSUE")
        if holding.get("hard_risk_active"):
            code = "RISK_REVIEW"
        elif holding.get("execution_state") == "VERIFICATION_PENDING" and holding.get("strategy_state") == "ADD_REVIEW":
            code = "ADD_PRICE_CHECK"
        items.append({"ticker": holding.get("ticker"), "display_action_code": code,
                      "display_action": messages.get(action_keys.get(code), code),
                      "primary_reason_code": holding.get("primary_reason_code"),
                      "price_evidence_display_code": holding.get("effective_price_status", "DATA_BLOCKED"),
                      "execution_display_code": holding.get("execution_state")})
    for candidate in (report.get("tactical_radar_result") or {}).get("candidate_dispositions", []):
        if candidate.get("opportunity_state") not in {"READY", "NEAR_TRIGGER"}:
            continue
        code = "ADD_PRICE_CHECK" if candidate.get("execution_state") == "VERIFICATION_PENDING" else ("ADD_REVIEW" if candidate.get("opportunity_state") == "READY" else "ADD_WAIT")
        items.append({"ticker": candidate.get("ticker"), "display_action_code": code,
                      "display_action": messages.get(action_keys.get(code), code),
                      "primary_reason_code": candidate.get("primary_blocker"),
                      "price_evidence_display_code": (candidate.get("price_evidence") or {}).get("effective_price_status", "DATA_BLOCKED"),
                      "execution_display_code": candidate.get("execution_state")})
    request = report.get("snapshot_request") or {}
    if request.get("snapshot_request_status") == "REQUIRED":
        items.append({"ticker": "PORTFOLIO", "display_action_code": "BROKER_SNAPSHOT_REQUIRED",
                      "display_action": messages.get("action_broker_snapshot_required"),
                      "primary_reason_code": "BROKER_SNAPSHOT_REQUIRED",
                      "price_evidence_display_code": "NOT_APPLICABLE", "execution_display_code": request.get("execution_effect")})
    if report.get("data_status") == "DATA_INCOMPLETE" and not any(item["display_action_code"] == "RISK_REVIEW" for item in items):
        items.append({"ticker": "GLOBAL", "display_action_code": "DATA_ISSUE",
                      "display_action": messages.get("action_data_issue"), "primary_reason_code": "DATA_INCOMPLETE",
                      "price_evidence_display_code": "DATA_BLOCKED", "execution_display_code": "DATA_BLOCKED"})
    if not items:
        items.append({"ticker": "PORTFOLIO", "display_action_code": "HOLD_NO_ACTION",
                      "display_action": messages.get("action_hold_no_action"), "primary_reason_code": "NO_CHANGE",
                      "price_evidence_display_code": "PRIMARY_VALIDATED", "execution_display_code": "NOT_APPLICABLE"})
    items.sort(key=lambda item: (PRIORITY.get(item["display_action_code"], 99), str(item["ticker"])))
    top = items[0]
    price_code = top["price_evidence_display_code"]
    price_text = {"PRIMARY_VALIDATED": messages.get("price_primary_validated"),
                  "INDEPENDENT_VERIFIED": messages.get("price_independent_verified"),
                  "PRICE_CONFLICT": messages.get("price_conflict"),
                  "DATA_BLOCKED": messages.get("summary_data_issue")}.get(price_code, messages.get("price_verification_pending"))
    urgency = "URGENT" if top["display_action_code"] == "RISK_REVIEW" else ("REVIEW" if PRIORITY.get(top["display_action_code"], 99) <= 7 else ("WAIT" if PRIORITY.get(top["display_action_code"], 99) == 8 else "NONE"))
    return {"schema_version": "2.5", "locale": "ko-KR", "display_action_code": top["display_action_code"],
            "display_action": top["display_action"], "display_urgency": urgency,
            "why": str(top.get("primary_reason_code") or messages.get("generic_review_reason", "REVIEW_REQUIRED")),
            "price_verification": str(price_text or messages.get("generic_price_review", "PRICE_REVIEW_REQUIRED")),
            "what_changes_decision": messages.get("what_changes_decision", "NEXT_VALIDATED_EVIDENCE"),
            "no_order_notice": messages.get("no_order_notice", "NO_ORDER_PLACED_OR_SCHEDULED"),
            "items": items, "order_authority": False}
