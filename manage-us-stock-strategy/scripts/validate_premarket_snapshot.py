#!/usr/bin/env python3
"""Validate premarket snapshots and prohibit completed-session authority."""

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
    for index, item in enumerate(snapshot.get("records", [])):
        if item.get("premarket_session") != snapshot.get("upcoming_regular_session"):
            errors.append(f"records[{index}]: premarket session mismatch")
        if item.get("latest_completed_regular_session") != snapshot.get("latest_completed_regular_session"):
            errors.append(f"records[{index}]: completed-session reference mismatch")
        if any(item.get(field) is not False for field in ("completed_regular_session", "daily_indicator_authority", "hard_risk_authority", "order_authority")):
            errors.append(f"records[{index}]: indicative quote leaked completed-session or order authority")
    if snapshot.get("provider_status") == "UNAVAILABLE" and snapshot.get("global_failure") != "GLOBAL_PREMARKET_DATA_OUTAGE":
        errors.append("provider-wide unavailability must expose GLOBAL_PREMARKET_DATA_OUTAGE")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "premarket-snapshot.schema.json")
    args = parser.parse_args()
    errors = validate_snapshot(load_json(args.snapshot), args.schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
