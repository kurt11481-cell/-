#!/usr/bin/env python3
"""Validate the exact Codex Web completed-close route registry."""

from __future__ import annotations

import argparse
from pathlib import Path

from validation_common import load_json, validate_instance
from web_route_acceptance import validate_registry_semantics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    value = load_json(args.registry)
    errors = validate_instance(
        value, root / "manage-us-stock-strategy/schemas/web-completed-close-route-registry.schema.json"
    )
    errors.extend(validate_registry_semantics(value))
    if errors:
        print("FAILED: " + "; ".join(dict.fromkeys(errors)))
        return 2
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
