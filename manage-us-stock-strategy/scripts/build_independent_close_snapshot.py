#!/usr/bin/env python3
"""Normalize independent completed-close records using registry capabilities."""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from provider_preflight import preflight
from validation_common import load_json, write_json


def _finite_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0


def build_snapshot(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    *,
    required_tickers: list[str],
    completed_session: str,
    primary_provider: str,
    generated_at: str,
    provider_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check = preflight(registry, provider_health, capability="INDEPENDENT_COMPLETED_CLOSE")
    providers = {item.get("provider"): item for item in registry.get("providers", [])}
    normalized: list[dict[str, Any]] = []
    validated: set[str] = set()
    for raw in records:
        item = dict(raw)
        provider = providers.get(item.get("provider")) or {}
        scopes = set(provider.get("capability_scope") or []) | set(provider.get("authoritative_for") or [])
        valid = bool(
            item.get("ticker") in required_tickers
            and item.get("completed_session") == completed_session
            and _finite_positive(item.get("close"))
            and item.get("currency") == "USD"
            and item.get("provider") != primary_provider
            and item.get("independent_of_primary_builder") is True
            and provider.get("enabled") is True
            and provider.get("independent_crosscheck_eligible") is True
            and "INDEPENDENT_COMPLETED_CLOSE" in scopes
            and isinstance(item.get("source_identifier"), str) and item.get("source_identifier")
            and isinstance(item.get("retrieved_at"), str) and item.get("retrieved_at")
        )
        item["validation_status"] = "VALIDATED" if valid else "REJECTED"
        item.setdefault("source_timestamp", None)
        item.setdefault("tolerance_result", "NOT_EVALUATED")
        normalized.append(item)
        if valid:
            validated.add(str(item["ticker"]))
    missing = [ticker for ticker in required_tickers if ticker not in validated]
    if check["capability_status"] == "UNAVAILABLE":
        capability_status = "UNAVAILABLE"
        global_failure = "GLOBAL_INDEPENDENT_CLOSE_OUTAGE"
    elif not validated:
        capability_status = "UNAVAILABLE"
        global_failure = "GLOBAL_INDEPENDENT_CLOSE_OUTAGE"
    elif missing:
        capability_status = "PARTIAL"
        global_failure = None
    else:
        capability_status = "AVAILABLE"
        global_failure = None
    return {
        "schema_version": "2.4",
        "generated_at": generated_at,
        "completed_session": completed_session,
        "primary_provider": primary_provider,
        "capability_status": capability_status,
        "global_failure": global_failure,
        "provider_health": check,
        "records": normalized,
        "missing_tickers": missing,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--provider-health", type=Path)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--primary-provider", required=True)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    records = load_json(args.records)
    if not isinstance(records, list):
        raise SystemExit("--records must contain a JSON array")
    snapshot = build_snapshot(records, load_json(args.registry), required_tickers=args.ticker,
        completed_session=args.completed_session, primary_provider=args.primary_provider,
        generated_at=args.generated_at, provider_health=load_json(args.provider_health) if args.provider_health else None)
    write_json(args.output, snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
