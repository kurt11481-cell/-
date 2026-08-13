#!/usr/bin/env python3
"""Migrate delivery metadata into the isolated v2.5 shadow runtime namespace."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


FORBIDDEN_BROKER_KEYS = {
    "holdings", "positions", "cash", "available_cash_usd", "average_cost_usd",
    "position_cost_basis_usd", "fills", "orders",
}


def migrate_runtime(*, tactical_runtime: dict[str, Any], holding_runtime: dict[str, Any],
                    policy_version: str, migrated_at: str | None = None) -> dict[str, Any]:
    """Copy dedup history without copying brokerage facts or creating deliveries."""
    migrated_at = migrated_at or datetime.now(timezone.utc).isoformat()
    trade_review_deliveries = deepcopy(tactical_runtime.get("deliveries") or {})
    holding_deliveries = deepcopy(holding_runtime.get("deliveries") or {})
    migrated = {
        "schema_version": "2.5",
        "policy_version": policy_version,
        "migrated_at": migrated_at,
        "migration_mode": "SHADOW_ONLY",
        "source_metadata": {
            "tactical_last_processed_session": tactical_runtime.get("last_processed_us_session"),
            "holding_last_processed_session": holding_runtime.get("last_processed_session"),
        },
        "namespaces": {
            "trade_review": {"deliveries": trade_review_deliveries},
            "holding_review": {"deliveries": holding_deliveries},
            "price_verification": {"requests": {}, "deliveries": {}},
            "broker_snapshot_request": {"requests": {}, "deliveries": {}},
            "confirmation_required": {"proposals": {}, "deliveries": {}},
        },
        "delivery_replay_allowed": False,
        "portfolio_state_mutation": False,
        "order_authority": False,
    }
    encoded = str(migrated).lower()
    for key in FORBIDDEN_BROKER_KEYS:
        if f"'{key}':" in encoded or f'"{key}":' in encoded:
            raise ValueError(f"FORBIDDEN_BROKER_FACT_IN_SHADOW_RUNTIME:{key}")
    return migrated
