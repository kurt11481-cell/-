#!/usr/bin/env python3
"""Validate a new-buy draft and its immutable authority boundaries."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance


def validate_draft(value: dict[str, Any], schema_path: Path) -> list[str]:
    errors = validate_instance(value, schema_path)
    if value.get("quantity") is not None:
        errors.append("QUANTITY_MUST_BE_NULL")
    if value.get("quantity_authority") != "none":
        errors.append("QUANTITY_AUTHORITY_PROHIBITED")
    if value.get("order_authority") is not False:
        errors.append("ORDER_AUTHORITY_PROHIBITED")
    earlier_block = value.get("strategy_draft_status") in {"DATA_BLOCKED", "PORTFOLIO_BLOCKED"}
    if (not earlier_block and value.get("opportunity_state") in {"READY", "NEAR_TRIGGER"}
            and value.get("price_evidence_status") == "INDEPENDENT_VERIFIED"
            and value.get("new_buy_instrument_approved") is not True):
        if value.get("strategy_draft_status") != "INSTRUMENT_APPROVAL_PENDING":
            errors.append("PRICE_EVIDENCE_CANNOT_APPROVE_INSTRUMENT")
    return list(dict.fromkeys(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    errors = validate_draft(load_json(args.input), root / "manage-us-stock-strategy/schemas/new-buy-strategy-draft.schema.json")
    if errors:
        print("FAILED: " + "; ".join(errors))
        return 2
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
