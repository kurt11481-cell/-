#!/usr/bin/env python3
"""Rebuild the preserved manual Post-Close case through degraded Event scope.

This consumes only artifacts already captured for the original decision cutoff.
It does not fetch current evidence, mutate portfolio/broker state, or count an
operational session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from event_resolution_engine import resolve_event_bundle
from portfolio_reallocation_shadow import OPTIMIZER_INPUTS, build_capital_reallocation_shadow
from validation_common import canonical_hash, load_json


EXPECTED_MANUAL_SHA256 = "75fc2eb83aa4624bec2c049ffadf81ec72cc367e6c356b43d9f9038aab8e9e7e"
MVLL_RVOL_FORMULA_VERSION = "RVOL20_SIGNAL_VOLUME_DIV_PRIOR_20_SESSION_MEAN_V1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def calculate_rvol20(snapshot: dict[str, Any], ticker: str, cutoff: str) -> dict[str, Any]:
    ticker_result = next(row for row in snapshot["ticker_results"] if row["ticker"] == ticker)
    raw = ticker_result["raw"]
    bars = sorted((row for row in raw["bars"] if row["session"] <= cutoff), key=lambda row: row["session"])
    if len(bars) < 21:
        raise ValueError("MVLL_RVOL20_INSUFFICIENT_HISTORY")
    window = bars[-21:]
    signal, prior = window[-1], window[:-1]
    mean = sum(float(row["volume"]) for row in prior) / len(prior)
    result = float(signal["volume"]) / mean
    if raw.get("completed_session") != cutoff or raw.get("status") != "PASS":
        raise ValueError("MVLL_COMPLETED_RAW_NOT_VALID")
    pagination = raw.get("pagination") or {}
    return {
        "schema_version": "1.0",
        "artifact_type": "MVLL_CANONICAL_VOLUME_LINEAGE",
        "ticker": ticker,
        "provider": "KIWOOM_REST",
        "source_api_id": pagination.get("api_id"),
        "session_cutoff": cutoff,
        "market_phase": "REGULAR_COMPLETED",
        "bar_finalized": True,
        "price_basis": "RAW",
        "volume_basis": "RAW_COMPLETED_DAILY_VOLUME",
        "corporate_action_treatment": "RAW_VOLUME_NO_ADJUSTED_VOLUME_SUBSTITUTION",
        "window_start": window[0]["session"],
        "window_end": window[-1]["session"],
        "signal_session": signal["session"],
        "signal_volume": signal["volume"],
        "denominator_sessions": [row["session"] for row in prior],
        "denominator_volumes": [row["volume"] for row in prior],
        "prior_20_session_mean_volume": mean,
        "formula_version": MVLL_RVOL_FORMULA_VERSION,
        "canonical_rvol20": result,
        "threshold": 1.0,
        "volume_authority_status": "KIWOOM_VALID_SCOPED",
        "technical_condition_status": "RVOL20_NOT_MET" if result < 1.0 else "RVOL20_MET",
        "affected_decision_class": "EMA10_RECLAIM_RVOL20",
        "global_mvll_block": False,
        "order_authority": False,
    }


def yfinance_diagnostic_rvol(snapshot: dict[str, Any], cutoff: str) -> float | None:
    symbol_row = (snapshot.get("symbols") or {}).get("MVLL")
    if symbol_row and symbol_row.get("bar_date") == cutoff:
        value = symbol_row.get("volume_ratio_to_20d")
        return float(value) if isinstance(value, (int, float)) else None
    candidates = snapshot.get("ticker_results") or snapshot.get("tickers") or []
    row = next((item for item in candidates if item.get("ticker") == "MVLL"), None)
    if not row:
        return None
    series = row.get("raw", {}).get("bars") or row.get("bars") or row.get("history") or []
    bars = sorted((item for item in series if item.get("session") <= cutoff), key=lambda item: item["session"])
    if len(bars) < 21:
        return None
    window = bars[-21:]
    mean = sum(float(item["volume"]) for item in window[:-1]) / 20
    return float(window[-1]["volume"]) / mean if mean else None


def _stale_event_evidence(matrix: dict[str, Any], ticker: str) -> dict[str, dict[str, Any]]:
    return {
        category: {
            "coverage_status": "SOURCE_STALE",
            "missing_reason": "SOURCE_STALE",
            "freshness_status": "STALE",
            "conflict_status": "NO_CONFLICT_OBSERVED",
            "identity_status": "VERIFIED",
            "event_effect": "UNKNOWN",
            "action_impact": {},
        }
        for category in matrix["ticker_requirements"][ticker]["categories"]
        if category != "underlying_issuer_context"
    }


def _holding_context(ticker: str, manual: dict[str, Any]) -> dict[str, Any]:
    source = manual["holding_review"][ticker]
    current = source["canonical_raw_close_usd"]
    average = source["current_average_cost_usd"]
    value = {
        "ticker": ticker,
        "current_broker_holding": source["current_broker_holding"],
        "current_average_cost": average,
        "current_canonical_price": current,
        "hard_risk_status": "NO_BREACH" if source["risk_state"] == "NO_HARD_RISK" else "BREACH",
        "hard_risk_exit_authorized": False,
        "thesis_status": "VALID",
        "thesis_invalidation_validated": False,
        "thesis_invalidation_event_verified": False,
        "event_readiness_status": "EVENT_STALE",
        "risk_trim_status": "NOT_TRIGGERED",
        "concentration_trim_status": "NOT_TRIGGERED",
        "technical_trim_status": "NOT_TRIGGERED",
        "valuation_trim_status": "NOT_TRIGGERED",
        "profit_protection_policy_result": "NOT_TRIGGERED",
        "time_stop_status": "NOT_TRIGGERED",
        "opportunity_cost_status": "NO_ROTATION",
        "valuation_add_status": "UNSUPPORTED",
        "technical_add_status": "WATCH",
        "portfolio_fit_status": "FITS",
        "add_review_requested": False,
        "unrealized_return_status": "LOSS" if current < average else "PROFIT",
        "trend_status": "UNKNOWN",
        "volume_health_status": "UNKNOWN",
        "price_authority_status": "KIWOOM_VALID",
        "volume_authority_status": source.get("volume_authority_status", "KIWOOM_VALID"),
        "technical_condition_status": source.get("technical_condition_status", "REVIEW_PENDING"),
        "broker_visibility_status": "BROKER_READ_ONLY_OPEN_ORDERS_UNKNOWN",
        "capital_availability_status": "VERIFIED_USD_63_69",
        "valuation_condition": "UNCLASSIFIED",
    }
    if ticker == "MVLL":
        value["technical_condition_decision_class"] = "EMA10_RECLAIM_RVOL20"
    return value


def build_evidence(
    *, manual_path: Path, kiwoom_snapshot_path: Path, yfinance_snapshot_path: Path,
    matrix_path: Path, registry_path: Path, reallocation_policy_path: Path,
    provider_scope_path: Path,
) -> dict[str, Any]:
    manual_hash = sha256_file(manual_path)
    if manual_hash != EXPECTED_MANUAL_SHA256:
        raise ValueError("MANUAL_ARTIFACT_HASH_MISMATCH")
    manual, snapshot = load_json(manual_path), load_json(kiwoom_snapshot_path)
    yfinance = load_json(yfinance_snapshot_path)
    matrix, registry, policy = load_json(matrix_path), load_json(registry_path), load_json(reallocation_policy_path)
    cutoff = manual["completed_session"]
    decision_as_of = manual["generated_at"]
    lineage = calculate_rvol20(snapshot, "MVLL", cutoff)
    diagnostic = yfinance_diagnostic_rvol(yfinance, cutoff)
    lineage["source_artifact_path"] = str(kiwoom_snapshot_path)
    lineage["source_artifact_sha256"] = sha256_file(kiwoom_snapshot_path)
    lineage["yfinance_diagnostic_rvol20"] = diagnostic
    lineage["cross_provider_divergence"] = None if diagnostic is None else lineage["canonical_rvol20"] - diagnostic
    lineage["divergence_blocking"] = False
    active_scope = load_json(provider_scope_path)
    mvll_scope = next(row for row in active_scope["provider_scopes"] if row["ticker"] == "MVLL")
    lineage["legacy_manifest_drift_status"] = (
        "POLICY_MANIFEST_DRIFT" if mvll_scope.get("blocked_decision_classes") else "NO_ACTIVE_LEGACY_BOUNDARY_CONFLICT"
    )
    lineage["lineage_hash"] = canonical_hash(lineage)

    resolutions = []
    for ticker in ("SOXL", "MVLL", "NBIS"):
        resolutions.append(resolve_event_bundle(
            ticker=ticker,
            instrument_identity={"ticker": ticker, "identity_status": "VERIFIED"},
            decision_as_of=decision_as_of,
            evidence_by_category=_stale_event_evidence(matrix, ticker),
            requirement_matrix=matrix,
            source_registry=registry,
            refresh_callback=None,
            maximum_attempts=0,
        ))
    combined_bundle_hash = canonical_hash({"manual_hash": manual_hash, "resolutions": resolutions})
    holdings = [_holding_context(ticker, manual) for ticker in ("SOXL", "MVLL", "NBIS")]
    reallocation_context = {
        "validation_mode": "REPLAY",
        "completed_bar_finalization_status": "KIWOOM_COMPLETED_BAR_FINALIZED",
        "event_refresh_status": "POST_CLOSE_EVENT_RESOLUTION_COMPLETED",
        "event_resolution_status": "UNRESOLVED_ACTION_BLOCKING",
        "holding_compile_mode": "DEGRADED_EVENT_SCOPED",
        "event_bundle_hash": combined_bundle_hash,
        "decision_as_of": decision_as_of,
        "market_data_cutoff": f"{cutoff}T20:00:00Z",
        "event_cutoff": f"{cutoff}T20:00:00Z",
        "broker_cutoff": f"{cutoff}T19:59:00Z",
        "candidate_cutoff": f"{cutoff}T20:00:00Z",
        "evidence_timestamps": [f"{cutoff}T20:00:00Z"],
        "portfolio_decision_semantic_cohort": "portfolio-decision-32fb4351fc727f7e",
        "portfolio_reallocation_cycle_id": f"manual-replay-{cutoff}",
        "canonical_positive_holding_tickers": [row["ticker"] for row in holdings],
        "prior_cycle_ids": [],
        "holdings": holdings,
        "portfolio_positions": [
            {"ticker": row["ticker"], "market_value_usd": row["current_broker_holding"] * row["current_canonical_price"], "effective_exposure_multiplier": {"SOXL": 3.0, "MVLL": 2.0}.get(row["ticker"], 1.0)}
            for row in holdings
        ],
        "opportunity_candidates": [],
        "verified_actual_cash_usd": float(manual["capital_reallocation_shadow"]["verified_actual_cash_usd"]),
        "capital_availability_status": "VERIFIED_USD_63_69",
        "optimizer_input_status": {key: ("AVAILABLE" if key in {"technical_setup", "event_readiness", "position_concentration", "cash_buffer"} else "UNAVAILABLE") for key in OPTIMIZER_INPUTS},
        "rotation_justification": None,
        "order_authority": False,
    }
    reallocation = build_capital_reallocation_shadow(reallocation_context, policy)
    provenance = {
        "schema_version": "1.0",
        "artifact_type": "EXECUTION_PATH_PROVENANCE",
        "entrypoint_id": "MANUAL_READ_ONLY_POST_CLOSE_2026_08_14",
        "orchestrator_version": manual.get("schema_version"),
        "event_gate_version": "LEGACY_GENERIC_EVENT_ORDERING_GATE",
        "holding_engine_version": "NOT_INVOKED_BY_ORIGINAL_RUN",
        "reallocation_engine_version": "NOT_INVOKED_BY_ORIGINAL_RUN",
        "sidecar_version": "NOT_INGESTED_BY_ORIGINAL_RUN",
        "called_components": ["KIWOOM_PROVIDER_PREFLIGHT", "KIWOOM_MARKET_SNAPSHOT", "YFINANCE_DIAGNOSTIC_SHADOW"],
        "skipped_components": ["HOLDING_STRATEGY_COMPILE", "CAPITAL_REALLOCATION_SHADOW", "CONTINUOUS_IMPROVEMENT_SIDECAR"],
        "skip_reason": "PRE_COMPILER_EARLY_RETURN_ENFORCED_BY_GENERIC_EVENT_ORDERING_GATE",
        "root_cause_classification": "IMPLEMENTATION_CORRECTION",
        "core_cohort_reset_required": False,
        "portfolio_decision_cohort_reset_required": False,
        "order_authority": False,
    }
    result = {
        "schema_version": "1.0",
        "artifact_type": "MANUAL_DEGRADED_EVENT_PATH_REPLAY",
        "source_manual_artifact": str(manual_path),
        "source_manual_sha256": manual_hash,
        "execution_origin": "REPLAY",
        "run_provenance_status": "VERIFIED_REPLAY",
        "decision_mode": "REPLAY",
        "maturity_eligible": False,
        "completed_session": cutoff,
        "mvll_canonical_volume_lineage": lineage,
        "event_resolutions": resolutions,
        "execution_path_provenance": provenance,
        "capital_reallocation_shadow": reallocation,
        "valid_finalized_session_increment": 0,
        "valid_paired_operational_day_increment": 0,
        "portfolio_decision_observation_increment": 0,
        "portfolio_mutation": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    result["artifact_hash"] = canonical_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True, type=Path)
    parser.add_argument("--kiwoom-snapshot", required=True, type=Path)
    parser.add_argument("--yfinance-snapshot", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--reallocation-policy", required=True, type=Path)
    parser.add_argument("--provider-scope", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build_evidence(
        manual_path=args.manual, kiwoom_snapshot_path=args.kiwoom_snapshot,
        yfinance_snapshot_path=args.yfinance_snapshot, matrix_path=args.matrix,
        registry_path=args.registry, reallocation_policy_path=args.reallocation_policy,
        provider_scope_path=args.provider_scope,
    )
    atomic_write(args.output, result)
    print(json.dumps({"status": "MANUAL_DEGRADED_EVENT_PATH_VERIFIED", "output": str(args.output), "order_authority": False}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
