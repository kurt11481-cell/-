#!/usr/bin/env python3
"""Validate current event risk and append forward-only immutable checkpoints."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, file_hash, load_json, parse_datetime, validate_instance


PRIMARY_SOURCE_TYPES = {"SEC", "ISSUER_IR", "ETF_SPONSOR", "EXCHANGE", "REGULATOR", "GOVERNMENT"}
EVENT_BUNDLE_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "current-event-risk-bundle.schema.json"
EVENT_CHECKPOINT_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "event-risk-checkpoint.schema.json"


def validate_bundle_semantics(bundle: dict[str, Any]) -> list[str]:
    errors = validate_instance(bundle, EVENT_BUNDLE_SCHEMA)
    if errors:
        return errors
    cutoff = parse_datetime(bundle["analysis_cutoff"])
    universe = bundle["universe"]["direct"] + bundle["universe"]["supplemental"]
    coverage = bundle["ticker_coverage"]
    covered = [item["ticker"] for item in coverage]
    if sorted(covered) != sorted(universe) or len(covered) != len(set(covered)):
        errors.append("TICKER_COVERAGE_MUST_MATCH_EXACT_UNIVERSE")
    event_ids = [event["event_id"] for event in bundle["events"]]
    if len(event_ids) != len(set(event_ids)):
        errors.append("DUPLICATE_EVENT_ID")
    known_ids = set(event_ids)
    for item in coverage:
        if any(event_id not in known_ids for event_id in item["event_ids"]):
            errors.append(f"UNKNOWN_COVERAGE_EVENT_ID:{item['ticker']}")
        if item["missing_fields"] and not item["event_data_incomplete"]:
            errors.append(f"MISSING_FIELDS_MUST_REMAIN_INCOMPLETE:{item['ticker']}")
        if item["missing_fields"] and item["status"] == "COMPLETE":
            errors.append(f"COMPLETE_WITH_MISSING_FIELDS:{item['ticker']}")
    for event in bundle["events"]:
        if event["analysis_cutoff"] != bundle["analysis_cutoff"]:
            errors.append(f"EVENT_CUTOFF_MISMATCH:{event['event_id']}")
        if parse_datetime(event["retrieved_at"]) > cutoff:
            errors.append(f"RETRIEVED_AFTER_CUTOFF:{event['event_id']}")
        if parse_datetime(event["first_seen_at"]) > cutoff:
            errors.append(f"FIRST_SEEN_AFTER_CUTOFF:{event['event_id']}")
        published = event.get("published_at")
        if published is not None and parse_datetime(published) > cutoff and event["point_in_time_eligible"]:
            errors.append(f"FUTURE_PUBLISHED_EVENT_ELIGIBLE:{event['event_id']}")
        if event["point_in_time_eligible"]:
            if event["source_type"] not in PRIMARY_SOURCE_TYPES:
                errors.append(f"NON_PRIMARY_SOURCE_ELIGIBLE:{event['event_id']}")
            knowledge_time = published or event["first_seen_at"]
            if parse_datetime(knowledge_time) > cutoff:
                errors.append(f"KNOWLEDGE_AFTER_CUTOFF:{event['event_id']}")
        if event["ticker"] != "GLOBAL" and event["ticker"] not in universe:
            errors.append(f"EVENT_TICKER_OUTSIDE_UNIVERSE:{event['event_id']}")
        if event["ticker"] == "SOXX" and "SOXL" in event["applies_to"]:
            errors.append(f"SOXX_EVENT_MISAPPLIED_TO_SOXL:{event['event_id']}")
        if event["ticker"] == "MRVL" and "MVLL" in event["applies_to"]:
            errors.append(f"MRVL_EVENT_MISAPPLIED_TO_MVLL_PRODUCT:{event['event_id']}")
    incomplete = any(item["event_data_incomplete"] for item in coverage)
    if incomplete and bundle["event_data_status"] != "EVENT_DATA_INCOMPLETE":
        errors.append("INCOMPLETE_TICKER_MUST_KEEP_EVENT_DATA_INCOMPLETE")
    return errors


def scope_ticker_failure(bundle: dict[str, Any], ticker: str, missing_field: str) -> dict[str, Any]:
    """Return a diagnostic copy where only the failed ticker is unavailable."""
    scoped = deepcopy(bundle)
    matched = False
    for item in scoped["ticker_coverage"]:
        if item["ticker"] != ticker:
            continue
        matched = True
        item["status"] = "UNAVAILABLE"
        item["strategy_effect"] = "DATA_BLOCKED"
        item["event_data_incomplete"] = True
        if missing_field not in item["missing_fields"]:
            item["missing_fields"].append(missing_field)
    if not matched:
        raise KeyError(f"UNKNOWN_TICKER:{ticker}")
    scoped["event_data_status"] = "EVENT_DATA_INCOMPLETE"
    if scoped["bundle_status"] == "COMPLETE":
        scoped["bundle_status"] = "PARTIAL"
    return scoped


def _checkpoint_payload(checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in checkpoint.items() if key != "record_hash"}


def validate_checkpoint_hash(checkpoint: dict[str, Any]) -> bool:
    return checkpoint.get("record_hash") == canonical_hash(_checkpoint_payload(checkpoint))


def validate_checkpoint_chain(checkpoints: list[dict[str, Any]]) -> bool:
    previous = None
    for checkpoint in sorted(checkpoints, key=lambda item: (item["market_session"], item["analysis_cutoff"])):
        if checkpoint.get("previous_record_hash") != previous or not validate_checkpoint_hash(checkpoint):
            return False
        previous = checkpoint["record_hash"]
    return True


def previous_checkpoint_hash(archive_root: Path) -> str | None:
    paths = sorted(archive_root.glob("*/event_checkpoint.json"))
    if not paths:
        return None
    value = load_json(paths[-1])
    if not validate_checkpoint_hash(value):
        raise ValueError("EVENT_CHECKPOINT_HASH_CHAIN_INVALID")
    return str(value["record_hash"])


def build_checkpoint(
    *, bundle: dict[str, Any], bundle_path: Path, market_session: str,
    current_completed_session: str, created_at: str, portfolio_hash_before: str,
    portfolio_hash_after: str, event_policy_hash: str,
    active_research_baseline_index_hash: str, previous_record_hash: str | None,
) -> dict[str, Any]:
    if market_session != current_completed_session:
        raise ValueError("EVENT_CHECKPOINT_HISTORICAL_BACKFILL_PROHIBITED")
    if bundle["market_session"] != market_session:
        raise ValueError("EVENT_BUNDLE_SESSION_MISMATCH")
    if validate_bundle_semantics(bundle):
        raise ValueError("EVENT_BUNDLE_INVALID")
    if portfolio_hash_before.lower() != portfolio_hash_after.lower():
        raise ValueError("PORTFOLIO_STATE_MUTATION_DETECTED")
    source_urls = sorted({event["source_url"] for event in bundle["events"]})
    checkpoint = {
        "schema_version": "1.0",
        "checkpoint_id": f"event-risk-{market_session}-{bundle['analysis_cutoff']}",
        "market_session": market_session,
        "analysis_cutoff": bundle["analysis_cutoff"],
        "created_at": created_at,
        "bundle_path": bundle_path.as_posix(),
        "bundle_hash": file_hash(bundle_path),
        "bundle_status": bundle["bundle_status"],
        "event_data_status": bundle["event_data_status"],
        "source_urls_hash": canonical_hash(source_urls),
        "event_policy_hash": event_policy_hash,
        "active_research_baseline_index_hash": active_research_baseline_index_hash,
        "portfolio_state_hash_before": portfolio_hash_before,
        "portfolio_state_hash_after": portfolio_hash_after,
        "portfolio_mutated": False,
        "provider_readiness_mutated": False,
        "strategy_state_mutated": False,
        "quantity_authority": False,
        "order_authority": False,
        "historical_backfill": False,
        "previous_record_hash": previous_record_hash,
        "record_hash": None,
    }
    checkpoint["record_hash"] = canonical_hash(_checkpoint_payload(checkpoint))
    return checkpoint


def append_checkpoint(archive_root: Path, checkpoint: dict[str, Any]) -> Path:
    target = archive_root / checkpoint["market_session"] / "event_checkpoint.json"
    if target.exists():
        raise FileExistsError("EVENT_CHECKPOINT_APPEND_ONLY")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".event-checkpoint.", suffix=".tmp", dir=str(target.parent))
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--current-completed-session", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--event-policy", required=True, type=Path)
    parser.add_argument("--baseline-index", required=True, type=Path)
    args = parser.parse_args()
    bundle = load_json(args.bundle)
    errors = validate_bundle_semantics(bundle)
    if errors:
        raise SystemExit("; ".join(errors))
    portfolio_hash = file_hash(args.portfolio_state)
    event_policy_hash = file_hash(args.event_policy)
    baseline_index_hash = file_hash(args.baseline_index)
    if bundle["event_policy_hash"].lower() != event_policy_hash.lower():
        raise SystemExit("EVENT_POLICY_HASH_MISMATCH")
    if bundle["active_research_baseline_index_hash"].lower() != baseline_index_hash.lower():
        raise SystemExit("ACTIVE_BASELINE_INDEX_HASH_MISMATCH")
    checkpoint = build_checkpoint(
        bundle=bundle, bundle_path=args.bundle, market_session=bundle["market_session"],
        current_completed_session=args.current_completed_session, created_at=args.created_at,
        portfolio_hash_before=portfolio_hash, portfolio_hash_after=portfolio_hash,
        event_policy_hash=event_policy_hash,
        active_research_baseline_index_hash=baseline_index_hash,
        previous_record_hash=previous_checkpoint_hash(args.archive_root),
    )
    schema_errors = validate_instance(checkpoint, EVENT_CHECKPOINT_SCHEMA)
    if schema_errors or not validate_checkpoint_hash(checkpoint):
        raise SystemExit("; ".join(schema_errors or ["EVENT_CHECKPOINT_HASH_INVALID"]))
    output = append_checkpoint(args.archive_root, checkpoint)
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
