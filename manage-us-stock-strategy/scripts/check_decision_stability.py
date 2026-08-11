#!/usr/bin/env python3
"""Compare repeated fixed-input decision outputs for material authority drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, write_json


BUY_ACTIONS = {"CONDITIONAL_BUY", "BUY_REVIEW"}
STOP_ACTIONS = {"STOP_REVIEW"}


def normalize(record: dict[str, Any]) -> dict[str, Any]:
    packet = record.get("research_packet") or {}
    manager = packet.get("research_manager") or {}
    portfolio = record.get("portfolio_decision") or {}
    risk = record.get("risk_review") or {}
    return {
        "action": record.get("final_action") or portfolio.get("action"),
        "risk_verdict": risk.get("verdict"),
        "dominant_thesis": manager.get("summary"),
        "invalidation": sorted(packet.get("invalidation_conditions") or []),
        "preferred_candidate": portfolio.get("preferred_candidate"),
    }


def compare(records: list[dict[str, Any]], minimum_runs: int = 3) -> dict[str, Any]:
    if len(records) < minimum_runs:
        return {"status": "INSUFFICIENT_RUNS", "critical_instability": True, "run_count": len(records), "differences": ["fewer than validation repeat count"]}
    normalized = [normalize(item) for item in records]
    differences: list[str] = []
    actions = {item["action"] for item in normalized}
    risks = {item["risk_verdict"] for item in normalized}
    opposite = bool(actions & BUY_ACTIONS and actions & STOP_ACTIONS) or ("ALLOW_REVIEW" in risks and "VETO" in risks)
    for field in normalized[0]:
        if len({json.dumps(item[field], sort_keys=True) for item in normalized}) > 1:
            differences.append(field)
    return {"status": "DECISION_STABILITY_RISK" if opposite else "PASS", "critical_instability": opposite, "run_count": len(records), "differences": differences, "normalized": normalized}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--minimum-runs", type=int, default=3, help="Validation setting only; not a trading rule.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare([load_json(path) for path in args.records], args.minimum_runs)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
