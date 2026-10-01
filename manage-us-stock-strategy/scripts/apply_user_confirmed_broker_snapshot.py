#!/usr/bin/env python3
"""Atomically apply one explicitly confirmed broker proposal to a caller-selected state file."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cash_flow_evidence import declaration_block_errors
from kiwoom_broker_shadow import PATCH_FIELDS, PROPOSAL_SCHEMA_VERSION, proposal_content_hash
from validation_common import canonical_hash, load_json, validate_instance


PROTECTED_NON_PORTFOLIO_NAMES = {
    "alert_policy.json", "alert_runtime_state.json", "tactical_radar_runtime.json",
    "holding_strategy_runtime.json", "automation_delivery_runtime.json",
}
SCREENSHOT_SCHEMA_VERSION = "2.5"
SCHEMA_DIRECTORY = Path(__file__).resolve().parents[1] / "schemas"
PINNED_PROPOSAL_SCHEMAS = {
    SCREENSHOT_SCHEMA_VERSION: SCHEMA_DIRECTORY / "broker-reconciliation-proposal.schema.json",
    PROPOSAL_SCHEMA_VERSION: SCHEMA_DIRECTORY / "kiwoom-reconciliation-proposal.schema.json",
}
CONFIRMATION_METHODS = ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL")
LEDGER_FILE_NAME = "reconciliation_ledger.jsonl"
BACKUP_DIRECTORY_NAME = "backups"
GENESIS_LEDGER_HASH = "0" * 64
# Every other top-level state field must be byte-identical (canonical JSON) after apply.
WRITTEN_STATE_FIELDS = frozenset(PATCH_FIELDS) | {
    "state_revision", "last_updated_at", "last_confirmed_broker_snapshot", "holding_change_reconciliations",
}
KST = timezone(timedelta(hours=9))


def default_ledger_path(state_path: Path) -> Path:
    return Path(state_path).parent / LEDGER_FILE_NAME


def default_backup_directory(state_path: Path) -> Path:
    return Path(state_path).parent / BACKUP_DIRECTORY_NAME


def ledger_status(ledger_path: Path) -> dict[str, Any]:
    """Read the append-only ledger and verify its hash chain; never raises for a bad ledger."""
    path = Path(ledger_path)
    status: dict[str, Any] = {"exists": path.is_file(), "entries": 0, "chain_ok": True,
                              "last_entry_sha256": GENESIS_LEDGER_HASH, "last_portfolio_hash_after": None,
                              "last_portfolio_hash_before": None}
    if not status["exists"]:
        return status
    previous = GENESIS_LEDGER_HASH
    try:
        for raw in path.read_bytes().splitlines():
            if not raw.strip():
                continue
            entry = json.loads(raw.decode("utf-8"))
            if not isinstance(entry, dict) or entry.get("previous_entry_sha256") != previous:
                status["chain_ok"] = False
            previous = hashlib.sha256(raw).hexdigest()
            status["entries"] += 1
            status["last_portfolio_hash_after"] = entry.get("portfolio_hash_after") if isinstance(entry, dict) else None
            status["last_portfolio_hash_before"] = entry.get("portfolio_hash_before") if isinstance(entry, dict) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        status["chain_ok"] = False
    status["last_entry_sha256"] = previous
    return status


def _append_ledger(ledger_path: Path, entry: dict[str, Any]) -> str:
    line = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("ab") as output:
        output.write(line + b"\n")
        output.flush()
        os.fsync(output.fileno())
    return hashlib.sha256(line).hexdigest()


def _write_backup(backup_directory: Path, state_path: Path, revision: int, stamp: str, content: bytes) -> Path:
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"{state_path.stem}.r{revision}.{stamp}.json"
    with backup_path.open("xb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    return backup_path


def _atomic_write_json(path: Path, value: dict[str, Any], *, newline: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline=newline) as output:
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _kiwoom_snapshot_record(proposal: dict[str, Any], confirmation: dict[str, Any],
                            confirmed_at: str) -> dict[str, Any]:
    # as_of, holdings_complete and cash scope come from the proposal, never from the caller.
    record = proposal["confirmed_snapshot_record"]
    cash_verified = record.get("cash_verified") is True
    return {
        "verified": True, "authority_state": "VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT",
        "source": record["source"], "scope": proposal["scope"],
        "account_id_masked": None, "account_identifier_stored": False,
        "evidence_bundle_id": proposal["bundle_id"], "evidence_sha256": record["evidence_sha256"],
        "confirmed_at": confirmed_at, "as_of": record["as_of"], "as_of_timestamp": record["as_of_timestamp"],
        "holdings_complete": record.get("holdings_complete") is True, "cash_verified": cash_verified,
        "cash_verified_scope": record.get("cash_verified_scope") if cash_verified else None,
        "open_orders_verified": record.get("open_orders_verified") is True,
        "confirmation_method": confirmation.get("confirmation_method"),
        "proposal_id": proposal["proposal_id"],
    }


def _updated_state(state: dict[str, Any], proposal: dict[str, Any], confirmation: dict[str, Any],
                   confirmed_at: str) -> dict[str, Any]:
    updated = deepcopy(state)
    patch = proposal.get("proposed_patch") or {}
    for key in PATCH_FIELDS:
        if key in patch:
            updated[key] = deepcopy(patch[key])
    for ticker, values in (patch.get("position_updates") or {}).items():
        updated.setdefault("holdings", {})[ticker] = values["quantity"]
        updated.setdefault("average_cost_usd", {})[ticker] = values.get("average_cost")
        updated.setdefault("position_cost_basis_usd", {})[ticker] = values.get("purchase_amount")
    updated["state_revision"] = int(state["state_revision"]) + 1
    updated["last_updated_at"] = confirmed_at
    if proposal.get("schema_version") == PROPOSAL_SCHEMA_VERSION:
        updated["last_confirmed_broker_snapshot"] = _kiwoom_snapshot_record(proposal, confirmation, confirmed_at)
        old_holdings = state.get("holdings") if isinstance(state.get("holdings"), dict) else {}
        new_holdings = updated.get("holdings") if isinstance(updated.get("holdings"), dict) else {}
        share_changes = [
            {"symbol": symbol, "prior_verified_shares": old_holdings.get(symbol),
             "current_verified_shares": new_holdings.get(symbol),
             "share_change": (new_holdings.get(symbol) or 0) - (old_holdings.get(symbol) or 0)}
            for symbol in sorted(set(old_holdings) | set(new_holdings))
            if old_holdings.get(symbol) != new_holdings.get(symbol)
        ]
        confirmed = _parse_utc(confirmed_at)
        reconciliations = updated.get("holding_change_reconciliations")
        updated["holding_change_reconciliations"] = (list(reconciliations) if isinstance(reconciliations, list)
                                                     else []) + [{
            "reconciliation_id": proposal["proposal_id"],
            "status": "BROKER_SNAPSHOT_RECONCILED_NO_FILL_RECORDED",
            "method": "KIWOOM_READONLY_SNAPSHOT_USER_CONFIRMED", "change_kind": proposal.get("change_kind"),
            "reconciled_at": confirmed_at,
            "reconciled_at_kst": confirmed.astimezone(KST).isoformat() if confirmed else None,
            "share_changes": share_changes, "trade_id": None,
            "fill_recorded": False, "inferred_fills": False,
        }]
    else:
        source = confirmation.get("source")
        updated["last_confirmed_broker_snapshot"] = {
            "verified": True, "authority_state": "VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT",
            "source": source.strip() if isinstance(source, str) else source,
            "scope": proposal["scope"], "account_id_masked": confirmation.get("account_id_masked"),
            "evidence_bundle_id": proposal["bundle_id"], "evidence_sha256": confirmation.get("evidence_sha256"),
            "confirmed_at": confirmed_at, "as_of": confirmation.get("as_of"),
            "holdings_complete": confirmation.get("holdings_complete") is True,
            "cash_verified": confirmation.get("cash_verified") is True,
            "cash_verified_scope": confirmation.get("cash_verified_scope")
            if confirmation.get("cash_verified") is True else None,
        }
    return updated


def preview_updated_state(state: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Pure preview used by propose for the post-apply alert-engine check; writes nothing."""
    confirmation = {"confirmation_method": "PREVIEW_NOT_CONFIRMED"}
    return _updated_state(state, proposal, confirmation, datetime.now(timezone.utc).isoformat())


def _assert_untouched(state: dict[str, Any], updated: dict[str, Any]) -> None:
    for key in (set(state) | set(updated)) - WRITTEN_STATE_FIELDS:
        if key not in state or key not in updated or canonical_hash(state[key]) != canonical_hash(updated[key]):
            raise ValueError("NEVER_TOUCHED_FIELD_CHANGED: " + key)


def apply_confirmed(*, state_path: Path, proposal: dict[str, Any], confirmation: dict[str, Any],
                    proposal_schema: Path | None = None, audit_path: Path,
                    now: datetime | None = None) -> dict[str, Any]:
    state_path = Path(state_path)
    audit_path = Path(audit_path)
    # The ledger and backups always sit next to the state file; callers cannot point them elsewhere.
    backup_directory = default_backup_directory(state_path)
    ledger_path = default_ledger_path(state_path)
    resolved_state = state_path.resolve()
    if state_path.name in PROTECTED_NON_PORTFOLIO_NAMES:
        raise ValueError("PORTFOLIO_STATE_PATH_REQUIRED")
    aliases = {audit_path.resolve(), ledger_path.resolve()}
    if proposal_schema is not None:
        aliases.add(Path(proposal_schema).resolve())
    if resolved_state in aliases or resolved_state.parent == backup_directory.resolve():
        raise ValueError("BROKER_APPLY_PATH_ALIAS_REJECTED")
    pinned_schema = PINNED_PROPOSAL_SCHEMAS.get(proposal.get("schema_version"))
    if pinned_schema is None:
        raise ValueError("BROKER_PROPOSAL_TYPE_UNSUPPORTED")
    # The library validates against its own schema; a caller-supplied schema can only add constraints.
    schema_errors = validate_instance(proposal, pinned_schema)
    if proposal_schema is not None and Path(proposal_schema).resolve() != pinned_schema.resolve():
        schema_errors += validate_instance(proposal, proposal_schema)
    if schema_errors:
        raise ValueError("BROKER_PROPOSAL_SCHEMA_INVALID: " + "; ".join(schema_errors))
    kiwoom = proposal["schema_version"] == PROPOSAL_SCHEMA_VERSION
    original_bytes = state_path.read_bytes()
    try:
        state = json.loads(original_bytes.decode("utf-8"))
    except ValueError as exc:
        raise ValueError("STATE_CHANGED_OUTSIDE_LEDGER: STATE_FILE_NOT_JSON") from exc
    if not isinstance(state, dict):
        raise ValueError("STATE_CHANGED_OUTSIDE_LEDGER: STATE_FILE_NOT_JSON_OBJECT")
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
    if not kiwoom:
        source = confirmation.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("BROKER_SOURCE_PROVENANCE_REQUIRED")
    # Every path, including direct library calls: nothing unresolved may be applied.
    if proposal.get("unresolved_fields"):
        raise ValueError("BROKER_PROPOSAL_UNRESOLVED_FIELDS: " + ", ".join(map(str, proposal["unresolved_fields"])))
    # v1 applies Kiwoom proposals only. Screenshot (2.5) proposals carry no expiry or confirm code.
    if not kiwoom:
        raise ValueError("SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED")
    # Expiry and confirmed_at use the real clock; a caller's now can only move time forward.
    real_now = datetime.now(timezone.utc)
    current_time = real_now if now is None else max(now, real_now)
    if kiwoom:
        if proposal_content_hash(proposal) != proposal["proposal_id"] or (
                proposal["confirm_code"] != proposal["proposal_id"][:8].upper()):
            raise ValueError("BROKER_PROPOSAL_INTEGRITY_MISMATCH")
        code = confirmation.get("confirm_code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("CONFIRM_CODE_REQUIRED")
        if code.strip().upper() != proposal["confirm_code"]:
            raise ValueError("CONFIRM_CODE_MISMATCH")
        if confirmation.get("confirmation_method") not in CONFIRMATION_METHODS:
            raise ValueError("CONFIRMATION_METHOD_INVALID")
        message = confirmation.get("user_message")
        if not isinstance(message, str) or proposal["confirm_code"] not in message.upper():
            raise ValueError("USER_CONFIRMATION_MESSAGE_REQUIRED")
        expires_at = _parse_utc(proposal.get("expires_at"))
        if expires_at is None or current_time > expires_at:
            raise ValueError("BROKER_PROPOSAL_EXPIRED")
        missing = [key for key in PATCH_FIELDS if key not in (proposal.get("proposed_patch") or {})]
        if missing:
            raise ValueError("BROKER_PROPOSAL_PATCH_INCOMPLETE: " + ", ".join(missing))
        # S5 R6: a declaration block must be self-consistent (e.g. never beyond its own limit).
        declaration_errors = (declaration_block_errors(proposal["cash_flow_declaration"])
                              if "cash_flow_declaration" in proposal else [])
        if declaration_errors:
            raise ValueError("CASH_FLOW_DECLARATION_INVALID: " + ", ".join(declaration_errors))
    ledger = ledger_status(ledger_path)
    if not ledger["chain_ok"]:
        raise ValueError("LEDGER_INTEGRITY_FAILED")
    outside_ledger = (ledger["last_portfolio_hash_after"] is not None
                      and ledger["last_portfolio_hash_after"] != before_hash)
    if outside_ledger and ledger["last_portfolio_hash_before"] == before_hash:
        # The last ledger entry was written but its state replacement never happened (P4 1-12).
        raise ValueError("STATE_CHANGED_OUTSIDE_LEDGER: STATE_EQUALS_LAST_LEDGER_BEFORE_HASH")
    # Any other outside change is applied only when the confirmed proposal showed it; the entry records it.
    if outside_ledger and "STATE_CHANGED_OUTSIDE_LEDGER" not in (proposal.get("warnings") or []):
        raise ValueError("OUTSIDE_LEDGER_WARNING_NOT_IN_PROPOSAL")
    confirmed_at = current_time.astimezone(timezone.utc).isoformat()
    updated = _updated_state(state, proposal, confirmation, confirmed_at)
    _assert_untouched(state, updated)
    after_hash = canonical_hash(updated)
    newline = "\r\n" if b"\r\n" in original_bytes else "\n"
    stamp = current_time.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    # Order: backup, then ledger, then the atomic state replacement.
    backup_path = _write_backup(backup_directory, state_path, int(state["state_revision"]), stamp, original_bytes)
    if state_path.read_bytes() != original_bytes:
        raise ValueError("CONCURRENT_STATE_BYTES_CHANGED")
    entry = {
        "schema_version": "1.0", "event": "APPLY", "proposal_schema_version": proposal["schema_version"],
        "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
        "confirm_code": proposal.get("confirm_code"),
        "confirmation_method": confirmation.get("confirmation_method") if kiwoom else "LIBRARY_CONFIRMATION_RECORD",
        "user_message": confirmation.get("user_message"), "confirmed_at": confirmed_at,
        "state_file": state_path.name, "backup_file": backup_path.name,
        "state_revision_before": state["state_revision"], "state_revision_after": updated["state_revision"],
        "portfolio_hash_before": before_hash, "portfolio_hash_after": after_hash,
        "changes": proposal.get("changes") if kiwoom else sorted((proposal.get("proposed_patch") or {}).keys()),
        "open_orders_verified": (proposal.get("confirmed_snapshot_record") or {}).get("open_orders_verified")
        if kiwoom else None,
        "inferred_fills": False, "order_authority": False,
        "state_changed_outside_ledger": outside_ledger,
        "ledger_expected_portfolio_hash": ledger["last_portfolio_hash_after"] if outside_ledger else None,
        "previous_entry_sha256": ledger["last_entry_sha256"],
    }
    if kiwoom and "cash_flow_declaration" in proposal:
        # Recorded in the ledger only; no state field is written for it (NEVER_TOUCHED is unchanged).
        entry["cash_flow_declaration"] = proposal["cash_flow_declaration"]
    _append_ledger(ledger_path, entry)
    _atomic_write_json(state_path, updated, newline=newline)
    if canonical_hash(load_json(state_path)) != after_hash:
        raise ValueError("STATE_WRITE_VERIFICATION_FAILED")
    audit = {"schema_version": "2.5", "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
             "confirmed_at": confirmed_at, "state_revision_before": state["state_revision"],
             "state_revision_after": updated["state_revision"], "portfolio_hash_before": before_hash,
             "portfolio_hash_after": after_hash, "backup_file": backup_path.name, "ledger_file": ledger_path.name,
             "inferred_fills": False, "order_authority": False}
    _atomic_write_json(audit_path, audit)
    return audit
