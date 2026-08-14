#!/usr/bin/env python3
"""Audit ticker-local provider limitations without expanding provider scope."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validation_common import load_json, write_json


def _rvol20(bars: list[dict[str, Any]]) -> float | None:
    ordered = sorted((row for row in bars if isinstance(row.get("volume"), (int, float))),
                     key=lambda row: row["session"])
    if len(ordered) < 21:
        return None
    prior = [float(row["volume"]) for row in ordered[-21:-1]]
    return float(ordered[-1]["volume"]) / (sum(prior) / len(prior)) if sum(prior) > 0 else None


def build_audit(*, kiwoom_snapshot: dict[str, Any], yfinance_snapshot: dict[str, Any],
                extended_snapshot: dict[str, Any], provider_policy: dict[str, Any],
                volume_acceptance: dict[str, Any] | None = None,
                volume_lineage: dict[str, Any] | None = None) -> dict[str, Any]:
    kiwoom = {item["ticker"]: item for item in kiwoom_snapshot.get("ticker_results") or []}
    yfinance = yfinance_snapshot.get("symbols") or {}
    fsly = kiwoom.get("FSLY") or {}
    mvll = kiwoom.get("MVLL") or {}
    mvll_bars = ((mvll.get("adjusted") or {}).get("bars") or [])
    kiwoom_rvol = _rvol20(mvll_bars)
    yfinance_rvol = (yfinance.get("MVLL") or {}).get("volume_ratio_to_20d")
    same_session = ((mvll.get("adjusted") or {}).get("completed_session") ==
                    (yfinance.get("MVLL") or {}).get("bar_date"))
    extended = {item["ticker"]: item for item in extended_snapshot.get("records") or []}
    scope = provider_policy.get("ticker_scope_rules") or {}
    authority = volume_lineage if volume_lineage else volume_acceptance
    scoped_volume_valid = bool(authority and authority.get("ticker") == "MVLL"
        and authority.get("volume_authority_status") == "KIWOOM_VALID_SCOPED"
        and authority.get("order_authority") is False
        and (authority.get("divergence_blocking") is False
             if volume_lineage else authority.get("blocking") is False))
    canonical_rvol = (authority.get("canonical_rvol20") if volume_lineage
                      else authority.get("kiwoom_rvol20") if authority else None)
    result = {
        "schema_version": "1.0", "market_session": kiwoom_snapshot.get("completed_session"),
        "FSLY": {
            "kiwoom_history_bars": (fsly.get("adjusted") or {}).get("history_bar_count"),
            "policy_minimum_bars": (fsly.get("adjusted") or {}).get("minimum_history_bars"),
            "continuation_exhausted": ((fsly.get("adjusted") or {}).get("pagination") or {}).get("provider_exhausted"),
            "history_merge_prohibited": (scope.get("FSLY") or {}).get("history_merge_prohibited") is True,
            "minimum_reduction_prohibited": (scope.get("FSLY") or {}).get("minimum_history_reduction_prohibited") is True,
            "technical_history_status": "YFINANCE_PRIMARY_VALIDATED_FALLBACK_REQUIRED",
        },
        "MVLL": {
            "price_authority": "KIWOOM_REST",
            "volume_authority": "KIWOOM_VALID_SCOPED" if scoped_volume_valid else "UNRESOLVED",
            "same_session_window": same_session, "kiwoom_rvol20": canonical_rvol,
            "snapshot_observed_rvol20": kiwoom_rvol,
            "canonical_volume_lineage_hash": (volume_lineage or {}).get("record_hash"),
            "lineage_consistent": bool(canonical_rvol is not None and kiwoom_rvol is not None
                                       and abs(float(canonical_rvol) - float(kiwoom_rvol)) < 1e-12),
            "yfinance_rvol20": yfinance_rvol, "volume_averaged": False,
            "preferred_result_selected": False, "threshold_changed": False,
            "technical_condition_status": (
                authority.get("technical_condition_status") if scoped_volume_valid
                else "TECHNICAL_BOUNDARY_CONFLICT"
            ),
            "blocked_decision_classes": list((scope.get("MVLL") or {}).get("blocked_decision_classes") or []),
        },
        "extended_sessions": {
            ticker: {"capability": "AVAILABLE" if ticker in extended else "UNAVAILABLE_TICKER_LOCAL",
                     "market_session_type": (extended.get(ticker) or {}).get("market_session_type"),
                     "daily_data_invalidated": False}
            for ticker in ("SOXL", "MVLL", "NBIS", "BE", "TOST", "NOW", "FSLY")
        },
        "cross_provider_diagnostics": {
            "role": "DIAGNOSTIC_ONLY", "kiwoom_override_allowed": False,
            "price_averaging_allowed": False, "noncomparable_session_is_conflict": False,
        },
        "scope_expansion": "EXPLICIT_LATER_APPROVAL_REQUIRED",
        "provider_scope_mutated": False, "portfolio_mutation": False,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kiwoom", required=True, type=Path)
    parser.add_argument("--yfinance", required=True, type=Path)
    parser.add_argument("--extended", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--volume-acceptance", type=Path)
    parser.add_argument("--volume-lineage", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build_audit(kiwoom_snapshot=load_json(args.kiwoom), yfinance_snapshot=load_json(args.yfinance),
                         extended_snapshot=load_json(args.extended), provider_policy=load_json(args.policy),
                         volume_acceptance=load_json(args.volume_acceptance) if args.volume_acceptance else None,
                         volume_lineage=load_json(args.volume_lineage) if args.volume_lineage else None)
    write_json(args.output, result)
    print("PROVIDER_LIMITATION_AUDIT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
