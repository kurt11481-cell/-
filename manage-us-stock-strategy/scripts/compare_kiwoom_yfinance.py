#!/usr/bin/env python3
"""Compare Kiwoom raw closes with the yfinance Primary snapshot."""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from validation_common import load_json, validate_instance


def compare_snapshots(
    kiwoom: dict[str, Any], primary: dict[str, Any], *,
    tolerance_policy: dict[str, Any], decision_boundaries: dict[str, float] | None,
    generated_at: str,
) -> dict[str, Any]:
    session = kiwoom.get("completed_session")
    primary_session = (primary.get("session") or {}).get("us_session_date")
    boundaries = decision_boundaries or {}
    results: list[dict[str, Any]] = []
    symbols = primary.get("symbols") or {}
    for item in kiwoom.get("ticker_results", []):
        ticker = item.get("ticker")
        raw = item.get("raw") or {}
        p_row = symbols.get(ticker) if isinstance(symbols, dict) else None
        k_close = raw.get("completed_close")
        p_close = p_row.get("close") if primary_session == session and isinstance(p_row, dict) and p_row.get("bar_date") == session else None
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) for value in (k_close, p_close)):
            results.append({
                "ticker": ticker, "completed_session": session,
                "kiwoom_raw_close": k_close, "yfinance_raw_close": p_close,
                "absolute_difference": None, "relative_difference": None,
                "tolerance_usd": None, "decision_boundary_flip": False,
                "comparison_status": "NOT_EVALUATED", "reason": "RAW_CLOSE_UNAVAILABLE",
            })
            continue
        absolute = abs(float(k_close) - float(p_close))
        relative = absolute / float(p_close)
        tolerance = max(float(tolerance_policy["absolute_usd_floor"]), float(tolerance_policy["relative_fraction"]) * float(p_close))
        boundary = boundaries.get(str(ticker))
        flip = boundary is not None and ((float(k_close) < float(boundary)) != (float(p_close) < float(boundary)))
        status = "CONFLICT" if flip or absolute > tolerance else "MATCH"
        reason = "DECISION_BOUNDARY_FLIP" if flip else "OUTSIDE_TOLERANCE" if absolute > tolerance else "WITHIN_TOLERANCE"
        results.append({
            "ticker": ticker, "completed_session": session,
            "kiwoom_raw_close": float(k_close), "yfinance_raw_close": float(p_close),
            "absolute_difference": absolute, "relative_difference": relative,
            "tolerance_usd": tolerance, "decision_boundary_flip": flip,
            "comparison_status": status, "reason": reason,
        })
    evaluated = [item for item in results if item["comparison_status"] != "NOT_EVALUATED"]
    overall = "MATCH" if evaluated and all(item["comparison_status"] == "MATCH" for item in evaluated) else "CONFLICT" if any(item["comparison_status"] == "CONFLICT" for item in results) else "NOT_EVALUATED"
    return {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "completed_session": session,
        "primary_session_status": "MATCH" if primary_session == session else "MISMATCH",
        "primary_provider": "yfinance",
        "shadow_provider": "KIWOOM_REST",
        "shadow_provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
        "comparison_status": overall,
        "results": results,
        "provider_promotion": False,
        "operational_shadow_session_increment": 0,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kiwoom-snapshot", required=True, type=Path)
    parser.add_argument("--yfinance-snapshot", required=True, type=Path)
    parser.add_argument("--tolerance-policy", required=True, type=Path)
    parser.add_argument("--decision-boundaries", type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    protected = [args.kiwoom_snapshot, args.yfinance_snapshot, args.tolerance_policy, args.schema]
    if args.decision_boundaries:
        protected.append(args.decision_boundaries)
    validate_shadow_output_path(args.output, args.repo_root, protected)
    policy = load_json(args.tolerance_policy)
    tolerance = policy.get("approved_direct_close_tolerance") or policy
    result = compare_snapshots(
        load_json(args.kiwoom_snapshot), load_json(args.yfinance_snapshot),
        tolerance_policy=tolerance,
        decision_boundaries=load_json(args.decision_boundaries) if args.decision_boundaries else None,
        generated_at=args.generated_at,
    )
    errors = validate_instance(result, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, result)
    return 0 if result["comparison_status"] in {"MATCH", "NOT_EVALUATED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
