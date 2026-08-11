#!/usr/bin/env python3
"""Normalize supplied authoritative event records into a point-in-time snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import load_json, parse_datetime, write_json


def build_snapshot(events: list[dict[str, Any]], *, snapshot_id: str, snapshot_mode: str, generated_at: str, analysis_cutoff: str, market_session: str | None, coverage_status: str, coverage_notes: list[str] | None = None) -> dict[str, Any]:
    cutoff = parse_datetime(analysis_cutoff)
    normalized: list[dict[str, Any]] = []
    for raw in events:
        item = dict(raw)
        announced = item.get("announced_at")
        retrieved = item.get("retrieved_at")
        source_type = item.get("source_type")
        point_in_time = False
        if source_type == "primary":
            knowledge_time = announced if snapshot_mode == "HISTORICAL" else (announced or retrieved)
            if knowledge_time:
                try:
                    point_in_time = parse_datetime(knowledge_time) <= cutoff
                except ValueError:
                    point_in_time = False
        item["point_in_time_eligible"] = bool(point_in_time)
        item["validation_status"] = "VALIDATED" if point_in_time else "REJECTED"
        item.setdefault("confidence", "HIGH" if point_in_time else "LOW")
        item.setdefault("policy_effect", "CONTEXT_ONLY" if point_in_time else "EVENT_DATA_INCOMPLETE")
        normalized.append(item)
    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "snapshot_mode": snapshot_mode,
        "generated_at": generated_at,
        "analysis_cutoff": analysis_cutoff,
        "market_session": market_session,
        "coverage_status": coverage_status,
        "coverage_notes": coverage_notes or [],
        "events": normalized,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--snapshot-mode", choices=["LIVE", "HISTORICAL"], required=True)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session")
    parser.add_argument("--coverage-status", choices=["COMPLETE", "PARTIAL", "EVENT_DATA_INCOMPLETE"], required=True)
    parser.add_argument("--coverage-note", action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = load_json(args.events)
    if not isinstance(source, list):
        raise SystemExit("events input must be a JSON array")
    snapshot = build_snapshot(source, snapshot_id=args.snapshot_id, snapshot_mode=args.snapshot_mode, generated_at=args.generated_at, analysis_cutoff=args.analysis_cutoff, market_session=args.market_session, coverage_status=args.coverage_status, coverage_notes=args.coverage_note)
    write_json(args.output, snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
