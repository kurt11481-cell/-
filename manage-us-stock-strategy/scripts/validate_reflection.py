#!/usr/bin/env python3
"""Reject reflection payloads that attempt to mutate operational authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json


PROHIBITED_KEYS = {
    "policy", "policy_version", "portfolio_state", "holdings", "cash",
    "available_cash_usd", "fills", "quantity", "leverage_approval",
    "loss_limit", "alert_candidate", "order", "broker_order",
}


def validate_reflection(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PROHIBITED_KEYS:
                errors.append(f"{path}.{key}: reflection cannot mutate operational state or policy")
            errors.extend(validate_reflection(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(validate_reflection(child, f"{path}[{index}]"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reflection", type=Path)
    args = parser.parse_args()
    errors = validate_reflection(load_json(args.reflection))
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
