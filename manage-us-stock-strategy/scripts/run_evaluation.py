#!/usr/bin/env python3
"""Produce a repeatable three-layer evaluation result without score collapse."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import load_json, write_json


def _aggregate(checks: dict[str, str], *, partial_allowed: bool = False) -> str:
    if not checks:
        return "NOT_TESTED"
    values = set(checks.values())
    if "FAIL" in values:
        return "FAIL"
    if "NOT_TESTED" in values:
        return "PARTIAL" if partial_allowed and values != {"NOT_TESTED"} else "NOT_TESTED"
    if "PARTIAL" in values:
        return "PARTIAL"
    return "PASS"


def build_result(config: dict[str, Any]) -> dict[str, Any]:
    safety_checks = config.get("safety_checks", {})
    quality_checks = config.get("decision_quality_checks", {})
    safety_status = _aggregate(safety_checks)
    quality_status = _aggregate(quality_checks, partial_allowed=True)
    cost_status = config.get("transaction_cost_status", "ASSUMPTION_REQUIRED")
    benchmark_status = config.get("benchmark_status", "ASSUMPTION_REQUIRED")
    economic_status = config.get("economic_status")
    if not economic_status:
        economic_status = "ASSUMPTION_REQUIRED" if "ASSUMPTION_REQUIRED" in {cost_status, benchmark_status} else "NOT_TESTED"
    if safety_status == "FAIL":
        merge_gate = "FAIL"
    elif safety_status != "PASS" or quality_status != "PASS":
        merge_gate = "BLOCKED"
    else:
        merge_gate = "PASS"
    return {
        "schema_version": "1.0",
        "evaluation_id": config["evaluation_id"],
        "generated_at": config.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "analysis_cutoff": config["analysis_cutoff"],
        "safety": {"status": safety_status, "checks": safety_checks},
        "decision_quality": {"status": quality_status, "checks": quality_checks},
        "economic_performance": {"status": economic_status, "transaction_cost_status": cost_status, "benchmark_status": benchmark_status, "metrics": config.get("metrics", {})},
        "overall_merge_gate": merge_gate,
        "notes": config.get("notes", []),
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_json(args.output, build_result(load_json(args.config)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
