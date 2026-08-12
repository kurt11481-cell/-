#!/usr/bin/env python3
"""One-shot capability preflight used before a full post-market scan."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import load_json, write_json


def preflight(registry: dict[str, Any], health: dict[str, Any] | None = None, *, capability: str) -> dict[str, Any]:
    health = health or {}
    candidates: list[dict[str, Any]] = []
    for provider in registry.get("providers", []):
        scopes = set(provider.get("capability_scope") or []) | set(provider.get("authoritative_for") or [])
        if not (
            provider.get("enabled") is True
            and provider.get("independent_crosscheck_eligible") is True
            and capability in scopes
        ):
            continue
        observed = health.get(provider.get("provider")) or {}
        circuit = observed.get("circuit_state", "HEALTHY")
        candidates.append({
            "provider": provider.get("provider"),
            "circuit_state": circuit,
            "last_success": observed.get("last_success"),
            "last_failure": observed.get("last_failure"),
            "failure_type": observed.get("failure_type"),
            "retry_after": observed.get("retry_after"),
            "available": circuit != "OPEN",
        })
    available = [item for item in candidates if item["available"]]
    if available:
        status = "AVAILABLE" if len(available) == len(candidates) else "PARTIAL"
        failure = None
    else:
        status = "UNAVAILABLE"
        failure = "NO_APPROVED_HEALTHY_PROVIDER" if candidates else "NO_APPROVED_PROVIDER_CAPABILITY"
    return {
        "schema_version": "2.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capability": capability,
        "capability_status": status,
        "providers": candidates,
        "global_failure": failure,
        "retry_behavior": "NO_PER_TICKER_RETRY_WHEN_PROVIDER_WIDE_OUTAGE",
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--health", type=Path)
    parser.add_argument("--capability", default="INDEPENDENT_COMPLETED_CLOSE")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = preflight(load_json(args.registry), load_json(args.health) if args.health else None, capability=args.capability)
    write_json(args.output, result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
