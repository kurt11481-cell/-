#!/usr/bin/env python3
"""Build a non-mutating broker reconciliation proposal from confirmed-pending extraction."""

from __future__ import annotations

import hashlib
from typing import Any

from validate_broker_snapshot_extraction import validate_extraction
from validation_common import canonical_hash


def build_proposal(extraction: dict[str, Any], portfolio_state: dict[str, Any]) -> dict[str, Any]:
    errors = validate_extraction(extraction)
    unresolved = list(errors)
    if extraction.get("capture_date_status") != "VERIFIED":
        unresolved.append("CAPTURE_DATE_USER_CONFIRMATION")
    if extraction.get("holdings_complete_status") == "USER_CONFIRMATION_REQUIRED":
        unresolved.append("HOLDINGS_COMPLETENESS_USER_CONFIRMATION")
    if extraction.get("position_currency_status") == "USER_CONFIRMATION_REQUIRED":
        unresolved.append("POSITION_CURRENCY_USER_CONFIRMATION")
    positions = extraction.get("positions") or []
    holdings = {item["ticker"]: item["quantity"] for item in positions if isinstance(item.get("ticker"), str)}
    average_costs = {item["ticker"]: item.get("average_cost") for item in positions if isinstance(item.get("ticker"), str)}
    cost_basis = {item["ticker"]: item.get("purchase_amount") for item in positions if isinstance(item.get("ticker"), str)}
    scope = extraction["scope"]
    patch: dict[str, Any] = {}
    if scope in {"FULL_PORTFOLIO", "HOLDINGS_ONLY"}:
        patch.update({"holdings": holdings, "average_cost_usd": average_costs,
                      "position_cost_basis_usd": cost_basis})
    elif scope == "POSITION_ONLY":
        patch["position_updates"] = {
            ticker: {"quantity": holdings[ticker], "average_cost": average_costs[ticker],
                     "purchase_amount": cost_basis[ticker]}
            for ticker in holdings
        }
    if scope in {"FULL_PORTFOLIO", "CASH_ONLY"} and extraction.get("cash_status") == "VERIFIED_AVAILABLE":
        patch["available_cash_usd"] = extraction.get("available_cash")
    proposal_id = "BRP-" + hashlib.sha256((extraction["bundle_id"] + canonical_hash(extraction)).encode("utf-8")).hexdigest()[:20]
    return {"schema_version": "2.5", "proposal_id": proposal_id, "bundle_id": extraction["bundle_id"],
            "authority_state": "EXTRACTED_PENDING_USER_CONFIRMATION", "scope": scope,
            "expected_state_revision": int(portfolio_state.get("state_revision", 0)),
            "expected_portfolio_hash_before": canonical_hash(portfolio_state),
            "status": "REUPLOAD_REQUIRED" if errors else "USER_CONFIRMATION_REQUIRED",
            "proposed_patch": patch, "unresolved_fields": list(dict.fromkeys(unresolved)),
            "inferred_fills": False, "quantity_authority": "none", "order_authority": False}
