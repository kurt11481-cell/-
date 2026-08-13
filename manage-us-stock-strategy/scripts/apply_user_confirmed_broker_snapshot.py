#!/usr/bin/env python3
"""Atomically apply one explicitly confirmed broker proposal to a caller-selected state file."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, load_json, validate_instance


PROTECTED_NON_PORTFOLIO_NAMES = {
    "alert_policy.json", "alert_runtime_state.json", "tactical_radar_runtime.json",
    "holding_strategy_runtime.json", "automation_delivery_runtime.json",
}


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def apply_confirmed(*, state_path: Path, proposal: dict[str, Any], confirmation: dict[str, Any],
                    proposal_schema: Path, audit_path: Path) -> dict[str, Any]:
    resolved_state = state_path.resolve()
    if state_path.name in PROTECTED_NON_PORTFOLIO_NAMES:
        raise ValueError("PORTFOLIO_STATE_PATH_REQUIRED")
    if resolved_state in {audit_path.resolve(), proposal_schema.resolve()}:
        raise ValueError("BROKER_APPLY_PATH_ALIAS_REJECTED")
    schema_errors = validate_instance(proposal, proposal_schema)
    if schema_errors:
        raise ValueError("BROKER_PROPOSAL_SCHEMA_INVALID: " + "; ".join(schema_errors))
    state = load_json(state_path)
    before_hash = canonical_hash(state)
    if confirmation.get("confirmed") is not True or confirmation.get("proposal_id") != proposal.get("proposal_id"):
        raise ValueError("EXPLICIT_USER_CONFIRMATION_REQUIRED")
    if confirmation.get("bundle_id") != proposal.get("bundle_id"):
        raise ValueError("BROKER_BUNDLE_ID_MISMATCH")
    if int(state.get("state_revision", -1)) != int(proposal.get("expected_state_revision", -2)):
        raise ValueError("CONCURRENT_STATE_REVISION_MISMATCH")
    if before_hash != proposal.get("expected_portfolio_hash_before"):
        raise ValueError("CONCURRENT_STATE_HASH_MISMATCH")
    if proposal.get("status") != "USER_CONFIRMATION_REQUIRED":
        raise ValueError("PROPOSAL_NOT_APPLYABLE")
    updated = deepcopy(state)
    patch = proposal.get("proposed_patch") or {}
    for key in ("holdings", "average_cost_usd", "position_cost_basis_usd", "available_cash_usd"):
        if key in patch:
            updated[key] = deepcopy(patch[key])
    for ticker, values in (patch.get("position_updates") or {}).items():
        updated.setdefault("holdings", {})[ticker] = values["quantity"]
        updated.setdefault("average_cost_usd", {})[ticker] = values.get("average_cost")
        updated.setdefault("position_cost_basis_usd", {})[ticker] = values.get("purchase_amount")
    updated["state_revision"] = int(state["state_revision"]) + 1
    confirmed_at = confirmation.get("confirmed_at") or datetime.now(timezone.utc).isoformat()
    updated["last_confirmed_broker_snapshot"] = {
        "verified": True, "authority_state": "VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT",
        "scope": proposal["scope"], "account_id_masked": confirmation.get("account_id_masked"),
        "evidence_bundle_id": proposal["bundle_id"], "evidence_sha256": confirmation.get("evidence_sha256"),
        "confirmed_at": confirmed_at, "as_of": confirmation.get("as_of"),
        "holdings_complete": confirmation.get("holdings_complete") is True,
        "cash_verified": confirmation.get("cash_verified") is True,
        "cash_verified_scope": confirmation.get("cash_verified_scope")
        if confirmation.get("cash_verified") is True else None,
    }
    after_hash = canonical_hash(updated)
    _atomic_write_json(state_path, updated)
    audit = {"schema_version": "2.5", "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
             "confirmed_at": confirmed_at, "state_revision_before": state["state_revision"],
             "state_revision_after": updated["state_revision"], "portfolio_hash_before": before_hash,
             "portfolio_hash_after": after_hash, "inferred_fills": False, "order_authority": False}
    _atomic_write_json(audit_path, audit)
    return audit
