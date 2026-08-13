#!/usr/bin/env python3
"""Compare Kiwoom Raw and Adjusted evidence with the yfinance Primary snapshot."""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from kiwoom_replay_validation import compare_technical_decisions
from validation_common import load_json, validate_instance


def _series_rows(value: Any) -> dict[str, dict[str, Any]]:
    rows = value.get("bars") if isinstance(value, dict) else value
    result: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and isinstance(row.get("session"), str):
            result[row["session"]] = row
    return result


def _compare_adjusted(
    kiwoom_series: dict[str, Any], yfinance_series: Any, *,
    basis_status: str, tolerance_policy: dict[str, Any],
    adjustment_policy: dict[str, Any],
) -> tuple[str, int, list[str]]:
    if basis_status == "UNKNOWN":
        return "INCONCLUSIVE", 0, ["ADJUSTED_BASIS_INCONCLUSIVE"]
    if basis_status == "INCOMPATIBLE":
        return "INCONCLUSIVE", 0, ["ADJUSTED_BASIS_INCOMPATIBLE"]
    if adjustment_policy.get("reuse_approved_raw_tolerance_for_same_basis") is not True:
        return "INCONCLUSIVE", 0, ["ADJUSTED_TOLERANCE_NOT_APPROVED"]
    left = _series_rows(kiwoom_series)
    right = _series_rows(yfinance_series)
    common = sorted(set(left) & set(right))
    minimum = int(adjustment_policy.get("minimum_common_sessions", 1))
    if len(common) < minimum:
        return "INSUFFICIENT_HISTORY", len(common), ["ADJUSTED_COMMON_HISTORY_INSUFFICIENT"]
    for session in common:
        for field in ("open", "high", "low", "close"):
            l_value = left[session].get(field)
            r_value = right[session].get(field)
            if not all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(float(value)) for value in (l_value, r_value)
            ):
                return "INCONCLUSIVE", len(common), [f"ADJUSTED_{field.upper()}_INVALID"]
            difference = abs(float(l_value) - float(r_value))
            tolerance = max(
                float(tolerance_policy["absolute_usd_floor"]),
                float(tolerance_policy["relative_fraction"]) * abs(float(r_value)),
            )
            if difference > tolerance:
                return "CONFLICT", len(common), [
                    "ADJUSTED_SERIES_CONFLICT", f"FIELD:{field}", f"SESSION:{session}",
                ]
    return "MATCH", len(common), ["SAME_BASIS_WITHIN_APPROVED_TOLERANCE"]


def compare_snapshots(
    kiwoom: dict[str, Any], primary: dict[str, Any], *,
    tolerance_policy: dict[str, Any], decision_boundaries: dict[str, float] | None,
    generated_at: str, adjustment_policy: dict[str, Any] | None = None,
    yfinance_adjusted_series: dict[str, Any] | None = None,
    kiwoom_technical: dict[str, Any] | None = None,
    yfinance_technical: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = kiwoom.get("completed_session")
    primary_session = (primary.get("session") or {}).get("us_session_date")
    boundaries = decision_boundaries or {}
    symbols = primary.get("symbols") or {}
    adjusted_inputs = yfinance_adjusted_series or {}
    technical_left = kiwoom_technical or {}
    technical_right = yfinance_technical or {}
    adjusted_policy = adjustment_policy or {}
    basis_status = str(
        adjusted_policy.get("basis_status")
        or adjusted_policy.get("default_basis_status") or "UNKNOWN"
    )
    if basis_status not in {"COMPATIBLE", "INCOMPATIBLE", "UNKNOWN"}:
        basis_status = "UNKNOWN"
    results: list[dict[str, Any]] = []
    for item in kiwoom.get("ticker_results", []):
        ticker = str(item.get("ticker"))
        raw = item.get("raw") or {}
        p_row = symbols.get(ticker) if isinstance(symbols, dict) else None
        k_close = raw.get("completed_close")
        p_close = (
            p_row.get("close")
            if primary_session == session and isinstance(p_row, dict)
            and p_row.get("bar_date") == session else None
        )
        adjusted_status, common_count, adjusted_reasons = _compare_adjusted(
            item.get("adjusted") or {}, adjusted_inputs.get(ticker),
            basis_status=basis_status, tolerance_policy=tolerance_policy,
            adjustment_policy=adjusted_policy,
        )
        technical_status, technical_flip, technical_reasons = compare_technical_decisions(
            technical_left.get(ticker), technical_right.get(ticker),
        )
        if not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)) for value in (k_close, p_close)
        ):
            raw_status = "NOT_EVALUATED"
            combined_status = "CONFLICT" if adjusted_status == "CONFLICT" or technical_flip else "NOT_EVALUATED"
            results.append({
                "ticker": ticker, "completed_session": session,
                "kiwoom_raw_close": k_close, "yfinance_raw_close": p_close,
                "absolute_difference": None, "relative_difference": None,
                "tolerance_usd": None, "decision_boundary_flip": False,
                "comparison_status": combined_status,
                "raw_comparison_status": raw_status,
                "reason": "RAW_CLOSE_UNAVAILABLE",
                "adjustment_basis_status": basis_status,
                "adjusted_comparison_status": adjusted_status,
                "technical_indicator_shadow_status": technical_status,
                "technical_decision_flip": technical_flip,
                "adjusted_common_session_count": common_count,
                "adjusted_comparison_reason_codes": adjusted_reasons + technical_reasons,
            })
            continue
        absolute = abs(float(k_close) - float(p_close))
        relative = absolute / float(p_close)
        tolerance = max(
            float(tolerance_policy["absolute_usd_floor"]),
            float(tolerance_policy["relative_fraction"]) * float(p_close),
        )
        boundary = boundaries.get(ticker)
        flip = boundary is not None and (
            (float(k_close) < float(boundary)) != (float(p_close) < float(boundary))
        )
        raw_status = "CONFLICT" if flip or absolute > tolerance else "MATCH"
        reason = (
            "DECISION_BOUNDARY_FLIP" if flip else
            "OUTSIDE_TOLERANCE" if absolute > tolerance else "WITHIN_TOLERANCE"
        )
        combined_status = (
            "CONFLICT" if raw_status == "CONFLICT" or adjusted_status == "CONFLICT" or technical_flip
            else raw_status
        )
        results.append({
            "ticker": ticker, "completed_session": session,
            "kiwoom_raw_close": float(k_close), "yfinance_raw_close": float(p_close),
            "absolute_difference": absolute, "relative_difference": relative,
            "tolerance_usd": tolerance, "decision_boundary_flip": flip,
            "comparison_status": combined_status,
            "raw_comparison_status": raw_status, "reason": reason,
            "adjustment_basis_status": basis_status,
            "adjusted_comparison_status": adjusted_status,
            "technical_indicator_shadow_status": technical_status,
            "technical_decision_flip": technical_flip,
            "adjusted_common_session_count": common_count,
            "adjusted_comparison_reason_codes": adjusted_reasons + technical_reasons,
        })
    evaluated = [item for item in results if item["comparison_status"] != "NOT_EVALUATED"]
    overall = (
        "MATCH" if evaluated and all(item["comparison_status"] == "MATCH" for item in evaluated)
        else "CONFLICT" if any(item["comparison_status"] == "CONFLICT" for item in results)
        else "NOT_EVALUATED"
    )
    return {
        "schema_version": "1.0", "generated_at": generated_at,
        "completed_session": session,
        "primary_session_status": "MATCH" if primary_session == session else "MISMATCH",
        "primary_provider": "yfinance", "shadow_provider": "KIWOOM_REST",
        "shadow_provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
        "comparison_status": overall,
        "market_data_provider_replay_status": (
            "PASS" if overall == "MATCH" else "FAIL" if overall == "CONFLICT" else "PARTIAL"
        ),
        "full_strategy_context_replay_status": "PARTIAL_EXPECTED_NO_ARCHIVE",
        "results": results, "provider_promotion": False,
        "operational_shadow_session_increment": 0, "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kiwoom-snapshot", required=True, type=Path)
    parser.add_argument("--yfinance-snapshot", required=True, type=Path)
    parser.add_argument("--tolerance-policy", required=True, type=Path)
    parser.add_argument("--decision-boundaries", type=Path)
    parser.add_argument("--adjustment-policy", type=Path)
    parser.add_argument("--yfinance-adjusted-series", type=Path)
    parser.add_argument("--kiwoom-technical", type=Path)
    parser.add_argument("--yfinance-technical", type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    protected = [args.kiwoom_snapshot, args.yfinance_snapshot, args.tolerance_policy, args.schema]
    protected.extend(path for path in (
        args.decision_boundaries, args.adjustment_policy, args.yfinance_adjusted_series,
        args.kiwoom_technical, args.yfinance_technical,
    ) if path)
    validate_shadow_output_path(args.output, args.repo_root, protected)
    policy = load_json(args.tolerance_policy)
    tolerance = policy.get("approved_direct_close_tolerance") or policy
    result = compare_snapshots(
        load_json(args.kiwoom_snapshot), load_json(args.yfinance_snapshot),
        tolerance_policy=tolerance,
        decision_boundaries=load_json(args.decision_boundaries) if args.decision_boundaries else None,
        generated_at=args.generated_at,
        adjustment_policy=(load_json(args.adjustment_policy).get("adjustment_basis_policy") if args.adjustment_policy else None),
        yfinance_adjusted_series=load_json(args.yfinance_adjusted_series) if args.yfinance_adjusted_series else None,
        kiwoom_technical=load_json(args.kiwoom_technical) if args.kiwoom_technical else None,
        yfinance_technical=load_json(args.yfinance_technical) if args.yfinance_technical else None,
    )
    errors = validate_instance(result, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, result)
    return 0 if result["comparison_status"] in {"MATCH", "NOT_EVALUATED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
