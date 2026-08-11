#!/usr/bin/env python3
"""Fail-closed point-in-time eligibility checks for historical evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, parse_datetime


def _provider_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["provider"]: item for item in registry.get("providers", []) if isinstance(item, dict) and item.get("provider")}


def validate_historical_evidence(evidence: list[dict[str, Any]], cutoff: str, registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cutoff_dt = parse_datetime(cutoff)
    providers = _provider_map(registry)
    for index, record in enumerate(evidence):
        prefix = f"evidence[{index}]"
        provider_name = record.get("provider")
        provider = providers.get(provider_name)
        if not provider:
            errors.append(f"{prefix}: provider is missing from capability registry")
            continue
        if provider.get("historical_point_in_time_supported") is not True:
            errors.append(f"{prefix}: provider is not approved for historical point-in-time use")
        published = record.get("published_at_utc")
        if not published:
            errors.append(f"{prefix}: published_at_utc is required for historical evidence")
        else:
            try:
                if parse_datetime(published) > cutoff_dt:
                    errors.append(f"{prefix}: future-published evidence")
            except ValueError as exc:
                errors.append(f"{prefix}: invalid publication timestamp: {exc}")
        effective = record.get("effective_at_utc")
        if effective:
            try:
                if parse_datetime(effective) > cutoff_dt and record.get("record_type") != "SCENARIO":
                    errors.append(f"{prefix}: future-effective fact")
            except ValueError as exc:
                errors.append(f"{prefix}: invalid effective timestamp: {exc}")
        if provider.get("source_type") == "social":
            errors.append(f"{prefix}: live social content is prohibited in historical analysis")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--registry", required=True, type=Path)
    args = parser.parse_args()
    errors = validate_historical_evidence(load_json(args.evidence), args.analysis_cutoff, load_json(args.registry))
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
