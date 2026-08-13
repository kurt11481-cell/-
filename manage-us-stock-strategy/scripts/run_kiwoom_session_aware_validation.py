#!/usr/bin/env python3
"""Reclassify Kiwoom/yfinance evidence through session-aware provider gates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from session_aware_market_data import (
    compare_price_observations,
    kiwoom_daily_observation,
    reclassify_prior_result,
    yfinance_regular_close_observation,
)
from validation_common import load_json, validate_instance


DEFAULT_TICKERS = ("SOXL", "MVLL", "NBIS", "BE", "TOST", "NOW", "FSLY", "SOXX", "MRVL", "AAPL", "IBM")


def _kiwoom_item(snapshot: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    return next((item for item in snapshot.get("ticker_results", []) if item.get("ticker") == ticker), None)


def _kiwoom_close(snapshot: dict[str, Any], ticker: str, session: str) -> tuple[float | None, bool]:
    item = _kiwoom_item(snapshot, ticker)
    if not isinstance(item, dict):
        return None, False
    row = next((row for row in (item.get("raw") or {}).get("bars", []) if row.get("session") == session), None)
    identity = (item.get("identity") or {}).get("mapping_status") == "VERIFIED"
    return (float(row["close"]) if isinstance(row, dict) and isinstance(row.get("close"), (int, float)) else None), identity


def _yfinance_close(evidence: dict[str, Any], ticker: str, session: str) -> float | None:
    record = (evidence.get("records") or {}).get(ticker) or {}
    row = next((row for row in record.get("bars", []) if row.get("session") == session), None)
    return float(row["close"]) if isinstance(row, dict) and isinstance(row.get("close"), (int, float)) else None


def _validation_rows(
    *, kiwoom: dict[str, Any], yfinance: dict[str, Any], session: str,
    tolerance: dict[str, Any], decision_boundaries: dict[str, float],
    tickers: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    k_timestamp = str(kiwoom.get("generated_at"))
    y_timestamp = str(yfinance.get("generated_at"))
    for ticker in tickers:
        k_close, identity = _kiwoom_close(kiwoom, ticker, session)
        y_close = _yfinance_close(yfinance, ticker, session)
        k_record = kiwoom_daily_observation(
            ticker=ticker, reported_session=session, close=k_close,
            provider_timestamp=k_timestamp, identity_verified=identity,
            official_session_verified=True,
        )
        y_record = yfinance_regular_close_observation(
            ticker=ticker, reported_session=session, close=y_close,
            provider_timestamp=y_timestamp, identity_verified=y_close is not None,
        )
        comparison = compare_price_observations(
            k_record, y_record, tolerance_policy=tolerance,
            decision_boundary=decision_boundaries.get(ticker),
        )
        rows.append({
            "ticker": ticker, "kiwoom_record": k_record,
            "yfinance_record": y_record, "comparison": comparison,
            "reclassification": reclassify_prior_result(comparison),
            "order_authority": False,
        })
    return rows


def provider_scopes(
    tickers: list[str], *, effective_from: str, acceptance_hash: str,
) -> list[dict[str, Any]]:
    scopes: list[dict[str, Any]] = []
    for ticker in tickers:
        technical = "YFINANCE_PRIMARY_VALIDATED_FALLBACK" if ticker == "FSLY" else "KIWOOM_ADJUSTED_LOCAL_DETERMINISTIC"
        blocked = ["EMA10_RECLAIM_RVOL20"] if ticker == "MVLL" else []
        fallback = (
            "KIWOOM_HISTORY_BELOW_POLICY_MINIMUM" if ticker == "FSLY"
            else "TICKER_AND_DECISION_CLASS_LOCAL_TECHNICAL_BOUNDARY_CONFLICT" if ticker == "MVLL"
            else None
        )
        scopes.append({
            "ticker": ticker, "identity_provider": "KIWOOM_REST",
            "regular_close_primary": "KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED",
            "extended_hours_primary": "KIWOOM_OPERATIONAL_PRIMARY",
            "technical_history_primary": technical,
            "shadow_provider": "YFINANCE_DIAGNOSTIC_SHADOW",
            "blocked_decision_classes": blocked, "fallback_reason": fallback,
            "effective_from": effective_from,
            "acceptance_artifact_hash": acceptance_hash.lower(),
            "order_authority": False,
        })
    return scopes


def build_validation(
    *, prior_kiwoom: dict[str, Any], prior_yfinance: dict[str, Any],
    latest_kiwoom: dict[str, Any], latest_yfinance: dict[str, Any],
    prior_session: str, latest_session: str, tolerance: dict[str, Any],
    decision_boundaries: dict[str, float], generated_at: str,
    acceptance_hash: str, tickers: list[str] | None = None,
    extended_snapshot: dict[str, Any] | None = None,
    event_data_complete: bool = False,
) -> dict[str, Any]:
    symbols = tickers or list(DEFAULT_TICKERS)
    prior_rows = _validation_rows(
        kiwoom=prior_kiwoom, yfinance=prior_yfinance, session=prior_session,
        tolerance=tolerance, decision_boundaries=decision_boundaries, tickers=symbols,
    )
    latest_rows = _validation_rows(
        kiwoom=latest_kiwoom, yfinance=latest_yfinance, session=latest_session,
        tolerance=tolerance, decision_boundaries=decision_boundaries, tickers=symbols,
    )
    identity_failed = any(row["kiwoom_record"]["security_identity_status"] != "VERIFIED" for row in latest_rows)
    true_conflict = any(row["comparison"]["comparison_status"] == "CONFLICT" for row in latest_rows)
    common_blocked = identity_failed and all(row["kiwoom_record"]["security_identity_status"] != "VERIFIED" for row in latest_rows)
    if common_blocked:
        transition = "KIWOOM_PRIMARY_TRANSITION_BLOCKED"
    elif true_conflict or any(row["reclassification"] != "MATCH" for row in latest_rows) or any(t in symbols for t in ("FSLY", "MVLL")):
        transition = "KIWOOM_PRIMARY_GUARDED_SCOPED"
    else:
        transition = "KIWOOM_PRIMARY_GUARDED_FULL"
    return {
        "schema_version": "1.0", "generated_at": generated_at,
        "prior_session": prior_session, "latest_completed_session": latest_session,
        "provider_transition_status": transition,
        "prior_reclassification": prior_rows, "latest_validation": latest_rows,
        "extended_hours_observations": list((extended_snapshot or {}).get("records") or []),
        "provider_scopes": provider_scopes(symbols, effective_from=generated_at, acceptance_hash=acceptance_hash),
        "event_gate_status": "EVENT_DATA_COMPLETE" if event_data_complete else "EVENT_REVIEW_PENDING",
        "new_cohort_required": transition != "KIWOOM_PRIMARY_TRANSITION_BLOCKED",
        "operational_session_increment": 0, "quantity_authority": False,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-kiwoom", required=True, type=Path)
    parser.add_argument("--prior-yfinance", required=True, type=Path)
    parser.add_argument("--latest-kiwoom", required=True, type=Path)
    parser.add_argument("--latest-yfinance", required=True, type=Path)
    parser.add_argument("--prior-session", required=True)
    parser.add_argument("--latest-session", required=True)
    parser.add_argument("--tolerance-policy", required=True, type=Path)
    parser.add_argument("--decision-boundaries", type=Path)
    parser.add_argument("--extended-snapshot", type=Path)
    parser.add_argument("--ticker", action="append")
    parser.add_argument("--acceptance-hash", required=True)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    protected = [args.prior_kiwoom, args.prior_yfinance, args.latest_kiwoom, args.latest_yfinance, args.tolerance_policy, args.schema]
    protected.extend(path for path in (args.decision_boundaries, args.extended_snapshot) if path)
    validate_shadow_output_path(args.output, args.repo_root, protected)
    tolerance_value = load_json(args.tolerance_policy)
    tolerance = tolerance_value.get("approved_direct_close_tolerance") or tolerance_value
    boundaries = load_json(args.decision_boundaries) if args.decision_boundaries else {}
    value = build_validation(
        prior_kiwoom=load_json(args.prior_kiwoom), prior_yfinance=load_json(args.prior_yfinance),
        latest_kiwoom=load_json(args.latest_kiwoom), latest_yfinance=load_json(args.latest_yfinance),
        prior_session=args.prior_session, latest_session=args.latest_session,
        tolerance=tolerance, decision_boundaries=boundaries,
        generated_at=args.generated_at, acceptance_hash=args.acceptance_hash,
        tickers=args.ticker, extended_snapshot=load_json(args.extended_snapshot) if args.extended_snapshot else None,
    )
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, value)
    print(json.dumps({
        "provider_transition_status": value["provider_transition_status"],
        "prior_non_matches": sum(row["reclassification"] != "MATCH" for row in value["prior_reclassification"]),
        "latest_non_matches": sum(row["reclassification"] != "MATCH" for row in value["latest_validation"]),
        "order_authority": False,
    }, separators=(",", ":")))
    return 0 if value["provider_transition_status"] != "KIWOOM_PRIMARY_TRANSITION_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
