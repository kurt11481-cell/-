#!/usr/bin/env python3
"""Validate the canonical instrument registry against non-authoritative policy cache metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, load_json


CRITICAL_FIELDS = (
    "instrument_type",
    "watchlist_approved",
    "new_buy_instrument_approved",
)


def validate_registry_consistency(
    canonical: dict[str, Any],
    policy: dict[str, Any],
    canonical_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    reference = ((policy.get("decision_harness") or {}).get("instrument_registry_authority") or {})
    # Hash normalized JSON content so Git/OS line-ending conversion cannot
    # create a false registry-authority mismatch.
    canonical_digest = canonical_hash(canonical)
    if canonical.get("canonical_authority") is not True:
        errors.append("canonical registry does not declare canonical_authority=true")
    if reference.get("canonical_path") != "workspace/policies/instrument_registry.json":
        errors.append("policy does not reference the canonical registry path")
    if reference.get("embedded_registry_role") != "non_authoritative_operational_cache":
        errors.append("embedded registry is not marked non-authoritative")
    if reference.get("required_canonical_sha256") != canonical_digest:
        errors.append("canonical registry hash differs from policy reference")

    cache = ((policy.get("decision_harness") or {}).get("instrument_registry") or {})
    instruments = canonical.get("instruments") or {}
    for symbol, cached in cache.items():
        authoritative = instruments.get(symbol)
        if not isinstance(authoritative, dict):
            warnings.append(f"{symbol}: operational cache entry has no canonical research record")
            continue
        for field in CRITICAL_FIELDS:
            if field in cached and cached.get(field) != authoritative.get(field):
                errors.append(f"{symbol}: cached {field} conflicts with canonical registry")

    return {
        "status": "VALIDATED" if not errors else "POLICY_REGISTRY_MISMATCH",
        "canonical_path": str(canonical_path),
        "canonical_sha256": canonical_digest,
        "errors": errors,
        "warnings": warnings,
        "research_scan_authority": "canonical_registry",
        "execution_review_authority": "fail_closed" if errors else "eligible_for_other_gates",
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    args = parser.parse_args()
    result = validate_registry_consistency(load_json(args.registry), load_json(args.policy), args.registry.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "VALIDATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
