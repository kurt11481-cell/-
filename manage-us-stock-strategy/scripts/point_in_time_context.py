#!/usr/bin/env python3
"""Forward-only, append-only point-in-time context checkpoint support."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from holding_research import baseline_payload
from validation_common import canonical_hash, file_hash, load_json, parse_datetime, validate_instance


FORBIDDEN_KEYS = {
    "account_number", "account_no", "app_key", "app_secret", "oauth_token",
    "access_token", "refresh_token", "credential", "credentials", "broker_screenshot",
}


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            found.extend(_forbidden_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return found


def build_checkpoint(
    *, market_session: str, current_completed_session: str, analysis_cutoff: str,
    created_at: str, portfolio_state_revision: int, portfolio_hash: str,
    event_evidence_cutoff: str, event_bundle_hash: str | None,
    active_baselines: list[dict[str, str]], policy_hashes: dict[str, str],
    registry_hash: str, source_artifact_hashes: dict[str, str | None],
    previous_record_hash: str | None,
) -> dict[str, Any]:
    if market_session != current_completed_session:
        raise ValueError("POINT_IN_TIME_HISTORICAL_BACKFILL_PROHIBITED")
    if parse_datetime(event_evidence_cutoff) > parse_datetime(analysis_cutoff):
        raise ValueError("EVENT_EVIDENCE_AFTER_ANALYSIS_CUTOFF")
    value = {
        "schema_version": "1.0", "market_session": market_session,
        "analysis_cutoff": analysis_cutoff, "created_at": created_at,
        "portfolio_context_checkpoint": {
            "portfolio_state_revision": portfolio_state_revision,
            "portfolio_hash": portfolio_hash,
        },
        "event_risk_bundle": {
            "evidence_cutoff": event_evidence_cutoff,
            "bundle_hash": event_bundle_hash,
        },
        "active_research_baseline_index": deepcopy(active_baselines),
        "policy_and_registry_snapshot": {
            "policy_hashes": deepcopy(policy_hashes), "registry_hash": registry_hash,
        },
        "source_artifact_hashes": deepcopy(source_artifact_hashes),
        "previous_record_hash": previous_record_hash,
        "record_hash": None, "historical_backfill": False,
        "order_authority": False,
    }
    forbidden = _forbidden_paths(value)
    if forbidden:
        raise ValueError("FORBIDDEN_POINT_IN_TIME_CONTENT:" + ",".join(forbidden))
    payload = {key: child for key, child in value.items() if key != "record_hash"}
    value["record_hash"] = canonical_hash(payload)
    return value


def validate_checkpoint_hash(value: dict[str, Any]) -> bool:
    payload = {key: child for key, child in value.items() if key != "record_hash"}
    return value.get("record_hash") == canonical_hash(payload) and not _forbidden_paths(value)


def validate_hash_chain(records: list[dict[str, Any]]) -> bool:
    previous = None
    for record in sorted(records, key=lambda item: str(item.get("market_session"))):
        if record.get("previous_record_hash") != previous or not validate_checkpoint_hash(record):
            return False
        previous = record.get("record_hash")
    return True


def append_checkpoint(archive_root: Path, checkpoint: dict[str, Any]) -> Path:
    target = archive_root / checkpoint["market_session"] / "context_checkpoint.json"
    if target.exists():
        raise FileExistsError("POINT_IN_TIME_CHECKPOINT_APPEND_ONLY")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".context-checkpoint.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(checkpoint, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def previous_hash(archive_root: Path) -> str | None:
    paths = sorted(archive_root.glob("*/context_checkpoint.json"))
    if not paths:
        return None
    last = load_json(paths[-1])
    if not validate_checkpoint_hash(last):
        raise ValueError("POINT_IN_TIME_HASH_CHAIN_INVALID")
    return str(last["record_hash"])


def baseline_reference(path: Path) -> tuple[dict[str, str], str]:
    """Return the baseline's validated semantic identity and its file hash."""
    value = load_json(path)
    expected_hash = canonical_hash(baseline_payload(value))
    if value.get("baseline_hash") != expected_hash:
        raise ValueError(f"BASELINE_HASH_MISMATCH:{path}")
    baseline_id = value.get("baseline_id")
    if not isinstance(baseline_id, str) or not baseline_id:
        raise ValueError(f"BASELINE_ID_MISSING:{path}")
    return {"baseline_id": baseline_id, "baseline_hash": expected_hash}, file_hash(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-session", required=True)
    parser.add_argument("--current-completed-session", required=True)
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--event-evidence-cutoff", required=True)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--event-bundle", type=Path)
    parser.add_argument("--baseline", action="append", default=[], type=Path)
    parser.add_argument("--policy", action="append", default=[], type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    args = parser.parse_args()
    portfolio = load_json(args.portfolio_state)
    baseline_inputs = [baseline_reference(path) for path in args.baseline]
    baselines = [reference for reference, _ in baseline_inputs]
    policies = {path.name: file_hash(path) for path in args.policy}
    sources: dict[str, str | None] = {
        "portfolio_state": file_hash(args.portfolio_state),
        "event_bundle": file_hash(args.event_bundle) if args.event_bundle else None,
        "instrument_registry": file_hash(args.registry),
    }
    sources.update({
        f"research_baseline:{reference['baseline_id']}": artifact_hash
        for (reference, artifact_hash) in baseline_inputs
    })
    checkpoint = build_checkpoint(
        market_session=args.market_session,
        current_completed_session=args.current_completed_session,
        analysis_cutoff=args.analysis_cutoff, created_at=args.created_at,
        portfolio_state_revision=int(portfolio["state_revision"]),
        portfolio_hash=file_hash(args.portfolio_state),
        event_evidence_cutoff=args.event_evidence_cutoff,
        event_bundle_hash=file_hash(args.event_bundle) if args.event_bundle else None,
        active_baselines=baselines, policy_hashes=policies,
        registry_hash=file_hash(args.registry), source_artifact_hashes=sources,
        previous_record_hash=previous_hash(args.archive_root),
    )
    errors = validate_instance(checkpoint, args.schema)
    if errors or not validate_checkpoint_hash(checkpoint):
        raise SystemExit("; ".join(errors or ["POINT_IN_TIME_HASH_INVALID"]))
    output = append_checkpoint(args.archive_root, checkpoint)
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
