#!/usr/bin/env python3
"""Build a research-only external candidate proposal without activating policy."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance, write_json


def build_discovery_proposal(identity: dict[str, Any]) -> dict[str, Any]:
    identity_status = str(identity.get("identity_status") or "PENDING")
    if identity_status == "REJECTED":
        state = "REJECTED"
    elif identity_status != "VERIFIED":
        state = "IDENTITY_VERIFICATION_PENDING"
    elif identity.get("light_screen_passed") is True:
        state = "USER_WATCHLIST_APPROVAL_REQUIRED"
    else:
        state = "DISCOVERED_RESEARCH_ONLY"
    remaining = [] if state == "REJECTED" else [
        "EXPLICIT_WATCHLIST_APPROVAL", "EXPLICIT_ACTIVE_UNIVERSE_APPROVAL",
        "EXACT_NEW_BUY_INSTRUMENT_APPROVAL",
    ]
    return {
        "schema_version": "2.6.3", "ticker": str(identity.get("ticker") or ""),
        "legal_issuer_name": str(identity.get("legal_issuer_name") or ""),
        "security_class": str(identity.get("security_class") or ""),
        "exchange": str(identity.get("exchange") or ""), "currency": "USD",
        "instrument_type": str(identity.get("instrument_type") or "other"),
        "leveraged_status": str(identity.get("leveraged_status") or "UNVERIFIED"),
        "identity_status": identity_status, "discovery_state": state,
        "watchlist_approved": False, "active_universe_approved": False,
        "new_buy_instrument_approved": False, "remaining_conditions": remaining,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    value = build_discovery_proposal(load_json(args.input))
    errors = validate_instance(value, root / "manage-us-stock-strategy/schemas/candidate-discovery-proposal.schema.json")
    if errors:
        raise SystemExit("candidate discovery proposal invalid: " + "; ".join(errors))
    write_json(args.output, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
