#!/usr/bin/env python3
"""Build a deterministic, unsized new-buy strategy draft from validated gates."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance, write_json


def _append(values: list[str], item: str) -> None:
    if item not in values:
        values.append(item)


def build_new_buy_strategy_draft(context: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(context)
    opportunity = str(value.get("opportunity_state") or "DATA_BLOCKED")
    price = str(value.get("price_evidence_status") or "DATA_BLOCKED")
    remaining = list(value.get("remaining_conditions") or [])
    status = "RESEARCH_ONLY"
    execution = "WATCH_ONLY"

    early_fail = (
        value.get("identity_status") != "VERIFIED"
        or value.get("evidence_integrity_status") not in {"PASS", "PASSED", "VALIDATED"}
        or opportunity == "DATA_BLOCKED"
        or (opportunity == "READY" and value.get("technical_status") != "READY")
        or (opportunity == "NEAR_TRIGGER" and value.get("technical_status") not in {"READY", "NEAR_TRIGGER", "WATCH"})
        or value.get("thesis_status") == "FAIL"
        or value.get("valuation_status") == "REJECTED"
        or value.get("risk_liquidity_status") == "FAIL"
        or price in {"PRICE_CONFLICT", "DATA_BLOCKED"}
    )
    if early_fail:
        status, execution = "DATA_BLOCKED", "DATA_BLOCKED"
    elif opportunity not in {"READY", "NEAR_TRIGGER"}:
        status, execution = "RESEARCH_ONLY", "WATCH_ONLY"
    elif value.get("event_risk_status") in {"EVENT_DATA_INCOMPLETE", "DATA_INCOMPLETE"}:
        status, execution = "DATA_BLOCKED", "DATA_BLOCKED"
        _append(remaining, "VERIFIED_EVENT_RISK")
    elif value.get("event_risk_status") in {"WAIT_REQUIRED", "EVENT_BLOCKED"}:
        status, execution = "PORTFOLIO_BLOCKED", "PORTFOLIO_BLOCKED"
        _append(remaining, "EVENT_RISK_CLEARANCE")
    elif value.get("portfolio_fit_status") == "BLOCKED":
        status, execution = "PORTFOLIO_BLOCKED", "PORTFOLIO_BLOCKED"
        _append(remaining, "PORTFOLIO_FIT_CLEARANCE")
    elif price != "INDEPENDENT_VERIFIED":
        status, execution = "PRICE_VERIFICATION_PENDING", "VERIFICATION_PENDING"
        _append(remaining, "INDEPENDENT_COMPLETED_CLOSE")
    elif value.get("new_buy_instrument_approved") is not True:
        status, execution = "INSTRUMENT_APPROVAL_PENDING", "NOT_APPROVED"
        _append(remaining, "EXACT_NEW_BUY_INSTRUMENT_APPROVAL")
    elif value.get("entry_rule_status") != "APPROVED":
        status, execution = "RISK_POLICY_APPROVAL_PENDING", "NOT_APPROVED"
        _append(remaining, "APPROVED_ENTRY_RULE")
    elif value.get("maximum_loss_rule_status") != "APPROVED":
        status, execution = "RISK_POLICY_APPROVAL_PENDING", "NOT_APPROVED"
        _append(remaining, "APPROVED_MAXIMUM_LOSS_RULE")
    elif value.get("risk_budget_status") != "APPROVED":
        status, execution = "RISK_POLICY_APPROVAL_PENDING", "NOT_APPROVED"
        _append(remaining, "APPROVED_RISK_BUDGET")
    elif value.get("cash_status") != "VERIFIED_POSITIVE":
        status, execution = "CASH_BLOCKED", "CASH_BLOCKED"
        _append(remaining, "VERIFIED_POSITIVE_AVAILABLE_CASH")
    elif value.get("promotion_scope_status") != "APPROVED":
        status, execution = "RISK_POLICY_APPROVAL_PENDING", "NOT_APPROVED"
        _append(remaining, "EXACT_STAGED_PROMOTION_SCOPE_APPROVAL")
    else:
        status, execution = "HUMAN_REVIEW_ELIGIBLE_GUARDED", "ELIGIBLE_FOR_HUMAN_REVIEW"
        _append(remaining, "FINAL_HUMAN_APPROVAL")

    return {
        "schema_version": "2.6.3", "ticker": str(value.get("ticker") or ""),
        "legal_issuer_name": str(value.get("legal_issuer_name") or ""),
        "instrument_type": str(value.get("instrument_type") or ""),
        "leveraged_status": str(value.get("leveraged_status") or "UNVERIFIED"),
        "analysis_cutoff": str(value.get("analysis_cutoff") or ""),
        "market_session": str(value.get("market_session") or ""),
        "research_packet_hash": str(value.get("research_packet_hash") or ""),
        "thesis_status": str(value.get("thesis_status") or "UNVERIFIED"),
        "valuation_status": str(value.get("valuation_status") or "UNVERIFIED"),
        "technical_status": str(value.get("technical_status") or "DATA_BLOCKED"),
        "event_risk_status": str(value.get("event_risk_status") or "EVENT_DATA_INCOMPLETE"),
        "risk_liquidity_status": str(value.get("risk_liquidity_status") or "UNVERIFIED"),
        "portfolio_fit_status": str(value.get("portfolio_fit_status") or "UNVERIFIED"),
        "opportunity_state": opportunity, "price_evidence_status": price,
        "source_route_id": value.get("source_route_id"),
        "new_buy_instrument_approved": value.get("new_buy_instrument_approved") is True,
        "entry_rule_status": str(value.get("entry_rule_status") or "PENDING"),
        "maximum_loss_rule_status": str(value.get("maximum_loss_rule_status") or "PENDING"),
        "risk_budget_status": str(value.get("risk_budget_status") or "PENDING"),
        "cash_status": str(value.get("cash_status") or "UNVERIFIED"),
        "promotion_scope_status": str(value.get("promotion_scope_status") or "PENDING"),
        "strategy_draft_status": status, "execution_state": execution,
        "primary_reason": str(value.get("primary_reason") or "Deterministic research gates evaluated."),
        "strongest_counter_case": str(value.get("strongest_counter_case") or "Decision-relevant counter-case remains required."),
        "entry_conditions": list(value.get("entry_conditions") or []),
        "remaining_conditions": remaining,
        "invalidation_conditions": list(value.get("invalidation_conditions") or []),
        "next_review_trigger": str(value.get("next_review_trigger") or "NEXT_COMPLETED_US_SESSION"),
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    value = build_new_buy_strategy_draft(load_json(args.input))
    errors = validate_instance(value, root / "manage-us-stock-strategy/schemas/new-buy-strategy-draft.schema.json")
    if errors:
        raise SystemExit("new-buy strategy draft invalid: " + "; ".join(errors))
    write_json(args.output, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
