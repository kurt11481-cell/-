#!/usr/bin/env python3
"""Deterministic non-broker lifecycle updates for Codex automation delivery."""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance
from finalized_postmarket_automation import FINALIZED_RUN_PHASE, delivery_eligible


def update_delivery(state: dict[str, Any], automation_id: str, *, attempted_at: str,
                    success: bool, completed_session: str | None, output_artifact: str | None,
                    notification_status: str | None, git_commit: str, policy_version: str,
                    portfolio_hash_before: str, portfolio_hash_after: str,
                    run_phase: str, finalization_status: str | None = None,
                    all_critical_bars_finalized: bool | None = None,
                    actual_scheduled_run: bool = False,
                    delivery_id: str | None = None,
                    failure_reason: str | None = None) -> dict[str, Any]:
    updated = deepcopy(state)
    row = (updated.get("automations") or {}).get(automation_id)
    if not isinstance(row, dict):
        raise ValueError("unknown automation id")
    row["last_attempted_run"] = attempted_at
    row["git_commit"] = git_commit
    row["policy_version"] = policy_version
    row["portfolio_state_hash_before"] = portfolio_hash_before
    row["portfolio_state_hash_after"] = portfolio_hash_after
    row["output_artifact"] = output_artifact
    row["notification_status"] = notification_status
    row["last_attempt_run_phase"] = run_phase
    row["last_finalization_status"] = finalization_status
    row["last_attempt_was_scheduled"] = bool(actual_scheduled_run)
    row["last_delivery_id"] = delivery_id
    if row.get("run_phase") == "PRE_OPEN":
        eligible = bool(success and run_phase == "PRE_OPEN" and output_artifact and delivery_id
                        and portfolio_hash_before == portfolio_hash_after and actual_scheduled_run)
    else:
        eligible = delivery_eligible(
            success=success, run_phase=run_phase,
            finalization_status=finalization_status,
            all_critical_bars_finalized=all_critical_bars_finalized,
            output_artifact=output_artifact, delivery_id=delivery_id,
            portfolio_hash_before=portfolio_hash_before,
            portfolio_hash_after=portfolio_hash_after,
            actual_scheduled_run=actual_scheduled_run,
        )
    if eligible:
        row["status"] = "DELIVERY_VERIFIED"
        row["last_successful_run"] = attempted_at
        row["last_completed_session"] = completed_session
        row["failure_reason"] = None
    else:
        preliminary = run_phase == "POST_MARKET_PRELIMINARY"
        row["status"] = "FIRST_RUN_PENDING" if preliminary else "FAILED"
        if preliminary:
            row["failure_reason"] = "PRELIMINARY_RUN_NOT_DELIVERY_ELIGIBLE"
        elif run_phase != row.get("run_phase"):
            row["failure_reason"] = failure_reason or "RUN_PHASE_MISMATCH"
        elif row.get("run_phase") == FINALIZED_RUN_PHASE and finalization_status != "VALIDATED":
            row["failure_reason"] = failure_reason or "FINALIZATION_NOT_VALIDATED"
        else:
            row["failure_reason"] = failure_reason or ("PORTFOLIO_STATE_HASH_CHANGED" if portfolio_hash_before != portfolio_hash_after else "OUTPUT_NOT_VERIFIED")
    updated["order_authority"] = False
    return updated


def mark_configured(state: dict[str, Any], automation_id: str) -> dict[str, Any]:
    updated = deepcopy(state)
    row = (updated.get("automations") or {}).get(automation_id)
    if not isinstance(row, dict):
        raise ValueError("unknown automation id")
    # Configuration is deliberately weaker than successful delivery.
    row["status"] = "FIRST_RUN_PENDING"
    updated["order_authority"] = False
    return updated


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--automation-id", required=True)
    parser.add_argument("--mode", choices=["mark-configured", "record-delivery"], required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--attempted-at")
    parser.add_argument("--success", action="store_true")
    parser.add_argument("--completed-session")
    parser.add_argument("--output-artifact")
    parser.add_argument("--notification-status")
    parser.add_argument("--git-commit")
    parser.add_argument("--policy-version")
    parser.add_argument("--portfolio-hash-before")
    parser.add_argument("--portfolio-hash-after")
    parser.add_argument("--run-phase")
    parser.add_argument("--finalization-status")
    parser.add_argument("--all-critical-bars-finalized", action="store_true")
    parser.add_argument("--actual-scheduled-run", action="store_true")
    parser.add_argument("--delivery-id")
    parser.add_argument("--failure-reason")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    canonical = (root / "workspace" / "state" / "automation_delivery_runtime.json").resolve()
    if args.runtime.resolve() != canonical or args.output.resolve() != canonical:
        raise SystemExit("automation delivery lifecycle updates are restricted to the canonical non-broker runtime")
    state = load_json(args.runtime)
    if args.mode == "mark-configured":
        updated = mark_configured(state, args.automation_id)
    else:
        required = {
            "attempted_at": args.attempted_at, "git_commit": args.git_commit,
            "policy_version": args.policy_version,
            "portfolio_hash_before": args.portfolio_hash_before,
            "portfolio_hash_after": args.portfolio_hash_after,
            "run_phase": args.run_phase,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise SystemExit("record-delivery missing required arguments: " + ",".join(missing))
        updated = update_delivery(
            state, args.automation_id, attempted_at=args.attempted_at,
            success=args.success, completed_session=args.completed_session,
            output_artifact=args.output_artifact,
            notification_status=args.notification_status,
            git_commit=args.git_commit, policy_version=args.policy_version,
            portfolio_hash_before=args.portfolio_hash_before,
            portfolio_hash_after=args.portfolio_hash_after,
            run_phase=args.run_phase, finalization_status=args.finalization_status,
            all_critical_bars_finalized=args.all_critical_bars_finalized,
            actual_scheduled_run=args.actual_scheduled_run,
            delivery_id=args.delivery_id, failure_reason=args.failure_reason,
        )
    errors = validate_instance(updated, root / "manage-us-stock-strategy" / "schemas" / "automation-delivery-runtime.schema.json")
    if errors:
        raise SystemExit("automation delivery runtime validation failed: " + "; ".join(errors))
    _atomic_write(args.output, updated)
    print(json.dumps({"automation_id": args.automation_id, "status": updated["automations"][args.automation_id]["status"],
        "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
