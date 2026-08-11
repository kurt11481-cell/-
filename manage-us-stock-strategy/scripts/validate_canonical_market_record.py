#!/usr/bin/env python3
"""Validate normalized market evidence and reject stale-session reuse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, parse_datetime, validate_instance


def validate_market_record(record: dict[str, Any], expected_session: str, schema: Path) -> list[str]:
    errors = validate_instance(record, schema)
    if record.get("exchange_session") != expected_session:
        errors.append("stale or mismatched completed session")
    if record.get("quality_status") != "VALIDATED":
        errors.append("market record is not validated")
    try:
        if parse_datetime(record["retrieved_at"]) < parse_datetime(record["timestamp"]):
            errors.append("retrieval precedes observation timestamp")
    except (KeyError, ValueError) as exc:
        errors.append(f"invalid market timestamps: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--expected-session", required=True)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "canonical-market-record.schema.json")
    args = parser.parse_args()
    errors = validate_market_record(load_json(args.record), args.expected_session, args.schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
