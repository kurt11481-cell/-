#!/usr/bin/env python3
"""Combine an immutable research baseline with current overlays without changing live strategy."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from holding_research import compile_context
from validation_common import canonical_hash, load_json, validate_instance, write_json


def _load_baseline(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    raw = Path(str(item["baseline_path"]))
    path = raw if raw.is_absolute() else root / raw
    return load_json(path)


def build_integrated_report(*, root: Path, live_report: dict[str, Any], registry: dict[str, Any],
                            baseline_index: dict[str, Any], overlays: dict[str, Any],
                            baseline_schema: Path, generated_at: str,
                            shadow_progress: dict[str, Any] | None = None) -> dict[str, Any]:
    compiled: list[dict[str, Any]] = []
    coverage: dict[str, str] = {}
    for ticker in ("NBIS", "MVLL", "SOXL"):
        active = (baseline_index.get("active") or {}).get(ticker)
        overlay = overlays.get(ticker)
        if not active or not isinstance(overlay, dict):
            coverage[ticker] = "REFRESH_REQUIRED"
            compiled.append({"ticker": ticker, "strategy_state": "STRATEGY_REFRESH_REQUIRED",
                             "strategy_signal": "NONE", "remaining_conditions": ["ACTIVE_BASELINE_OR_OVERLAY_MISSING"],
                             "quantity": None, "quantity_authority": "none", "order_authority": False})
            continue
        try:
            baseline = _load_baseline(root, active)
            profile = deepcopy((registry.get("instruments") or {}).get(ticker) or {})
            profile["ticker"] = ticker
            context = compile_context(profile, baseline, overlay, baseline_schema=baseline_schema)
            compiled.append(context)
            coverage[ticker] = "VALIDATED_SHADOW"
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            coverage[ticker] = "REJECTED"
            compiled.append({"ticker": ticker, "strategy_state": "STRATEGY_REFRESH_REQUIRED",
                             "strategy_signal": "NONE", "remaining_conditions": [f"BASELINE_COMPILE_FAILED:{type(exc).__name__}"],
                             "quantity": None, "quantity_authority": "none", "order_authority": False})
    progress = shadow_progress or {"valid_shadow_sessions": 0, "checkpoint_status": "FIRST_VALID_SESSION_PENDING"}
    beginner = deepcopy(live_report.get("beginner_summary") or {})
    beginner["shadow_only_notice_code"] = "SHADOW_ONLY_LIVE_STRATEGY_UNCHANGED"
    beginner["shadow_valid_sessions"] = int(progress.get("valid_shadow_sessions", 0))
    return {
        "schema_version": "2.6", "mode": "SHADOW_ONLY", "generated_at": generated_at,
        "market_session": live_report.get("market_session"),
        "current_live_holding_strategy": deepcopy(live_report.get("holding_strategies") or []),
        "shadow_compiled_holding_strategy": compiled,
        "price_evidence": {"live": deepcopy(live_report.get("price_evidence") or {}),
                           "shadow": {"status": "PENDING_OR_NOT_REQUIRED", "live_execution_upgrade_allowed": False,
                                      "order_authority": False}},
        "broker_snapshot": {"status": (live_report.get("snapshot_request") or {}).get("snapshot_request_status", "NOT_REQUIRED"),
                            "portfolio_mutation": False, "confirmation_required_before_apply": True,
                            "order_authority": False},
        "shadow_acceptance": {"baseline_coverage": coverage,
                              "valid_shadow_sessions": int(progress.get("valid_shadow_sessions", 0)),
                              "checkpoint_status": progress.get("checkpoint_status", "FIRST_VALID_SESSION_PENDING"),
                              "automatic_promotion": False, "explicit_user_approval_required": True,
                              "order_authority": False},
        "beginner_summary": beginner, "quantity": None, "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--live-report", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--baseline-index", type=Path, required=True)
    parser.add_argument("--overlays", type=Path, required=True)
    parser.add_argument("--baseline-schema", type=Path, required=True)
    parser.add_argument("--report-schema", type=Path, required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--shadow-progress", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before = canonical_hash(load_json(args.root / "stock-strategy-system/portfolio_state.json"))
    report = build_integrated_report(root=args.root, live_report=load_json(args.live_report),
        registry=load_json(args.registry), baseline_index=load_json(args.baseline_index),
        overlays=load_json(args.overlays), baseline_schema=args.baseline_schema,
        generated_at=args.generated_at,
        shadow_progress=load_json(args.shadow_progress) if args.shadow_progress and args.shadow_progress.is_file() else None)
    errors = validate_instance(report, args.report_schema)
    after = canonical_hash(load_json(args.root / "stock-strategy-system/portfolio_state.json"))
    if before != after:
        raise SystemExit("portfolio state mutation detected")
    if errors:
        raise SystemExit("integrated report validation failed: " + "; ".join(errors))
    write_json(args.output, report)
    print(json.dumps({"output": str(args.output), "portfolio_state_unchanged": True,
                      "shadow_counted_session": False, "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
