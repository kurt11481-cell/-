#!/usr/bin/env python3
"""Build a non-executing exact approval request from a validated strategy draft."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, load_json, validate_instance, write_json


def build_approval_proposal(draft: dict[str, Any], *, decision_class: str = "NEW_BUY") -> dict[str, Any]:
    requested: list[str] = []
    approval_stage = draft.get("strategy_draft_status") in {
        "INSTRUMENT_APPROVAL_PENDING", "RISK_POLICY_APPROVAL_PENDING",
        "HUMAN_REVIEW_ELIGIBLE_GUARDED",
    }
    if approval_stage:
        if draft.get("new_buy_instrument_approved") is not True:
            requested.append("NEW_BUY_INSTRUMENT")
        if draft.get("entry_rule_status") != "APPROVED":
            requested.append("ENTRY_RULE")
        if draft.get("maximum_loss_rule_status") != "APPROVED":
            requested.append("MAXIMUM_LOSS_RULE")
        if draft.get("risk_budget_status") != "APPROVED":
            requested.append("RISK_BUDGET")
        if draft.get("promotion_scope_status") != "APPROVED":
            requested.append("STAGED_PROMOTION_SCOPE")
        if draft.get("strategy_draft_status") == "HUMAN_REVIEW_ELIGIBLE_GUARDED":
            requested.append("FINAL_HUMAN_REVIEW")
    status = "HUMAN_REVIEW_ELIGIBLE_GUARDED" if requested == ["FINAL_HUMAN_REVIEW"] else (
        "USER_APPROVAL_REQUIRED" if requested else "NOT_READY"
    )
    return {
        "schema_version": "2.6.3", "ticker": draft.get("ticker"),
        "strategy_draft_hash": canonical_hash(draft), "requested_approvals": requested,
        "opportunity_state": draft.get("opportunity_state"),
        "price_evidence_status": draft.get("price_evidence_status"),
        "entry_rule_status": draft.get("entry_rule_status"),
        "maximum_loss_rule_status": draft.get("maximum_loss_rule_status"),
        "risk_budget_status": draft.get("risk_budget_status"),
        "cash_status": draft.get("cash_status"),
        "promotion_scope": {"ticker": draft.get("ticker"), "decision_class": decision_class,
                            "source_route_id": draft.get("source_route_id")},
        "proposal_status": status, "explicit_user_approval_required": True,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--decision-class", default="NEW_BUY")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    value = build_approval_proposal(load_json(args.draft), decision_class=args.decision_class)
    errors = validate_instance(value, root / "manage-us-stock-strategy/schemas/new-buy-approval-proposal.schema.json")
    if errors:
        raise SystemExit("new-buy approval proposal invalid: " + "; ".join(errors))
    write_json(args.output, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
