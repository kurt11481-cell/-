#!/usr/bin/env python3
"""Validate independent close snapshot authority and global/ticker scope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance


def validate_snapshot(snapshot: dict[str, Any], schema: Path) -> list[str]:
    errors = validate_instance(snapshot, schema)
    if errors:
        return errors
    seen: set[str] = set()
    for index, item in enumerate(snapshot.get("records", [])):
        if item.get("validation_status") != "VALIDATED":
            continue
        ticker = item["ticker"]
        if ticker in seen:
            errors.append(f"records[{index}]: duplicate validated ticker")
        seen.add(ticker)
        if item.get("provider") == snapshot.get("primary_provider") or item.get("independent_of_primary_builder") is not True:
            errors.append(f"records[{index}]: source is not independent from primary builder")
        if item.get("completed_session") != snapshot.get("completed_session"):
            errors.append(f"records[{index}]: completed-session mismatch")
    if snapshot.get("capability_status") == "UNAVAILABLE" and snapshot.get("global_failure") != "GLOBAL_INDEPENDENT_CLOSE_OUTAGE":
        errors.append("unavailable independent-close capability must expose one global outage")
    if snapshot.get("capability_status") == "PARTIAL" and not snapshot.get("missing_tickers"):
        errors.append("partial independent-close snapshot must identify missing tickers")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "independent-close-snapshot.schema.json")
    args = parser.parse_args()
    errors = validate_snapshot(load_json(args.snapshot), args.schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
