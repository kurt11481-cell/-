#!/usr/bin/env python3
"""Validate event snapshots and fail closed on look-ahead or authority leakage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, parse_datetime, validate_instance


def validate_snapshot(snapshot: dict[str, Any], schema_path: Path) -> list[str]:
    errors = validate_instance(snapshot, schema_path)
    if errors:
        return errors
    cutoff = parse_datetime(snapshot["analysis_cutoff"])
    generated = parse_datetime(snapshot["generated_at"])
    if generated < cutoff:
        errors.append("generated_at precedes analysis_cutoff")
    session = snapshot.get("market_session")
    if session and session > cutoff.date().isoformat():
        errors.append("event-calendar session is after analysis cutoff")
    for index, event in enumerate(snapshot.get("events", [])):
        prefix = f"events[{index}]"
        announced = event.get("announced_at")
        if event.get("validation_status") == "VALIDATED":
            if event.get("source_type") != "primary":
                errors.append(f"{prefix}: validated event requires a primary source")
            if snapshot.get("snapshot_mode") == "HISTORICAL":
                if not announced:
                    errors.append(f"{prefix}: historical validated event requires announced_at")
                elif parse_datetime(announced) > cutoff:
                    errors.append(f"{prefix}: future-known event information")
            else:
                knowledge_time = announced or event.get("retrieved_at")
                if not knowledge_time or parse_datetime(knowledge_time) > cutoff:
                    errors.append(f"{prefix}: live event was not known by the analysis cutoff")
            if event.get("point_in_time_eligible") is not True:
                errors.append(f"{prefix}: validated event is not point-in-time eligible")
        if event.get("policy_effect") == "WAIT_REQUIRED" and event.get("validation_status") != "VALIDATED":
            errors.append(f"{prefix}: unvalidated event cannot enforce WAIT_REQUIRED")
    if snapshot.get("coverage_status") == "COMPLETE" and not snapshot.get("coverage_notes") and not snapshot.get("events"):
        errors.append("empty event evidence cannot prove complete coverage")
    if snapshot.get("order_authority") is not False:
        errors.append("event snapshot cannot hold order authority")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "event-snapshot.schema.json")
    args = parser.parse_args()
    errors = validate_snapshot(load_json(args.snapshot), args.schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
