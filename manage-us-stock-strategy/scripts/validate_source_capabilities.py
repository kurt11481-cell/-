#!/usr/bin/env python3
"""Validate source capability registry and non-negotiable provider boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance


def validate_registry(registry: dict[str, Any], schema: Path) -> list[str]:
    errors = validate_instance(registry, schema)
    providers = registry.get("providers", [])
    names = [item.get("provider") for item in providers if isinstance(item, dict)]
    if len(names) != len(set(names)):
        errors.append("provider names must be unique")
    by_name = {item.get("provider"): item for item in providers if isinstance(item, dict)}
    yfinance = by_name.get("yfinance") or {}
    if yfinance.get("independent_crosscheck_eligible") is not False:
        errors.append("yfinance cannot be an independent Yahoo-free cross-check")
    if "TRADING_CALENDAR" in yfinance.get("authoritative_for", []):
        errors.append("yfinance cannot be authoritative for the exchange calendar")
    kiwoom = by_name.get("kiwoom_rest") or {}
    if kiwoom:
        if kiwoom.get("enabled") is not False:
            errors.append("Kiwoom must remain disabled until operational Shadow acceptance")
        if kiwoom.get("independent_crosscheck_eligible") is not False:
            errors.append("Kiwoom is not yet an approved independent close cross-check")
        if kiwoom.get("authoritative_for"):
            errors.append("Kiwoom cannot become authoritative from adapter implementation")
    for social in ("reddit", "stocktwits"):
        item = by_name.get(social)
        if item and item.get("historical_point_in_time_supported") is not False:
            errors.append(f"{social} historical point-in-time capability must be false")
        if item and item.get("authoritative_for"):
            errors.append(f"{social} cannot be authoritative evidence")
    circuit = registry.get("circuit_breaker") or {}
    for key in ("retry_storm_prohibited", "ip_rotation_prohibited", "silent_stale_fallback_prohibited"):
        if circuit.get(key) is not True:
            errors.append(f"circuit_breaker.{key} must be true")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "source-capability.schema.json")
    args = parser.parse_args()
    errors = validate_registry(load_json(args.registry), args.schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
