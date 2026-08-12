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


def update_delivery(state: dict[str, Any], automation_id: str, *, attempted_at: str,
                    success: bool, completed_session: str | None, output_artifact: str | None,
                    notification_status: str | None, git_commit: str, policy_version: str,
                    portfolio_hash_before: str, portfolio_hash_after: str,
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
    if success and portfolio_hash_before == portfolio_hash_after and output_artifact:
        row["status"] = "DELIVERY_VERIFIED"
        row["last_successful_run"] = attempted_at
        row["last_completed_session"] = completed_session
        row["failure_reason"] = None
    else:
        row["status"] = "FAILED"
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
    parser.add_argument("--mode", choices=["mark-configured"], required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    canonical = (root / "workspace" / "state" / "automation_delivery_runtime.json").resolve()
    if args.runtime.resolve() != canonical or args.output.resolve() != canonical:
        raise SystemExit("automation delivery lifecycle updates are restricted to the canonical non-broker runtime")
    state = load_json(args.runtime)
    updated = mark_configured(state, args.automation_id)
    errors = validate_instance(updated, root / "manage-us-stock-strategy" / "schemas" / "automation-delivery-runtime.schema.json")
    if errors:
        raise SystemExit("automation delivery runtime validation failed: " + "; ".join(errors))
    _atomic_write(args.output, updated)
    print(json.dumps({"automation_id": args.automation_id, "status": updated["automations"][args.automation_id]["status"],
        "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
