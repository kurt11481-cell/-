#!/usr/bin/env python3
"""Reviewed adapter for one immutable MANUAL_READ_ONLY learning record."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from continuous_improvement_sidecar import (
    METRIC_DEFINITION_VERSION,
    _atomic_write,
    append_run_record,
    build_event_resolution_analytics,
    build_run_record,
    validate_ledger_chain,
)
from validation_common import canonical_hash, file_hash, load_json, validate_instance


EXPECTED_MANUAL_SHA256 = "75fc2eb83aa4624bec2c049ffadf81ec72cc367e6c356b43d9f9038aab8e9e7e"


def build_manual_run(
    manual: dict[str, Any], replay: dict[str, Any], *, manual_path: Path,
    runtime_manifest_hash: str, provider_scope_hash: str,
    semantic_cohort: str, analytics_cohort: str,
) -> dict[str, Any]:
    manual_sha = file_hash(manual_path)
    if manual_sha != EXPECTED_MANUAL_SHA256:
        raise ValueError("MANUAL_ARTIFACT_HASH_MISMATCH")
    unresolved = []
    for resolution in replay.get("event_resolutions") or []:
        for row in resolution.get("categories") or []:
            if row.get("missing_reason"):
                unresolved.append({
                    "category": row["event_category"],
                    "missing_reason": row["missing_reason"],
                    "source_type": row.get("source_type"),
                })
    observation = {
        "artifact_type": "EVENT_ACTIONABILITY_ORCHESTRATION_GAP",
        "decision_mode": "MANUAL_READ_ONLY",
        "ticker": "PORTFOLIO",
        "resolution_status": "UNRESOLVED_ACTION_BLOCKING",
        "holding_compile_mode": "DEGRADED_EVENT_SCOPED",
        "resolution_attempt_count": sum(item.get("resolution_attempt_count", 0) for item in replay.get("event_resolutions") or []),
        "buy_blocked_by_event": True,
        "hold_review_required": True,
        "keep_cash_state": replay["capital_reallocation_shadow"]["keep_cash_state"],
        "unresolved_categories": unresolved,
        "original_runtime_gap": "HOLDING_AND_REALLOCATION_COMPILE_SKIPPED_BY_GENERIC_EVENT_GATE",
        "repaired_replay_status": replay["capital_reallocation_shadow"]["status"],
        "policy_change": False,
        "auto_apply": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    return {
        "run_id": manual["run_id"],
        "execution_origin": "MANUAL",
        "decision_mode": "MANUAL_READ_ONLY",
        "operational_day_id": manual["completed_session"],
        "provenance_evidence": {
            "manual_run_id": manual["run_id"],
            "operator_initiated": True,
        },
        "git_sha": manual["deployment_provenance"]["runtime_head"],
        "runtime_manifest_hash": runtime_manifest_hash,
        "provider_scope_hash": provider_scope_hash,
        "semantic_cohort": semantic_cohort,
        "improvement_analytics_cohort": analytics_cohort,
        "decision_as_of": manual["generated_at"],
        "market_data_cutoff": f"{manual['completed_session']}T20:00:00Z",
        "event_cutoff": f"{manual['completed_session']}T20:00:00Z",
        "broker_cutoff": f"{manual['completed_session']}T19:59:00Z",
        "candidate_cutoff": None,
        "portfolio_hash_before": manual["portfolio_state_hash_before"].lower(),
        "portfolio_hash_after": manual["portfolio_state_hash_after"].lower(),
        "source_artifacts": [{
            "provider": "LOCAL_IMMUTABLE_ARCHIVE",
            "source_type": "MANUAL_POST_CLOSE_RESULT",
            "artifact_path": str(manual_path),
            "sha256": manual_sha,
            "observed_at": manual["generated_at"],
            "effective_at": f"{manual['completed_session']}T20:00:00Z",
            "market_session_semantics": "REGULAR_COMPLETED",
        }],
        "decision_artifacts": [observation],
        "delivery_status": "NOT_APPLICABLE",
    }


def ingest(
    *, manual_path: Path, replay_path: Path, ledger_path: Path,
    cohort_path: Path, policy_path: Path, ledger_schema_path: Path,
    provider_scope_path: Path, core_progress_path: Path,
) -> dict[str, Any]:
    manual, replay, ledger = load_json(manual_path), load_json(replay_path), load_json(ledger_path)
    cohort, policy = load_json(cohort_path), load_json(policy_path)
    provider_scope_hash = file_hash(provider_scope_path)
    core = load_json(core_progress_path)
    runtime_manifest_hash = manual["deployment_provenance"]["manifest_sha256"].lower()
    run = build_manual_run(
        manual, replay, manual_path=manual_path,
        runtime_manifest_hash=runtime_manifest_hash,
        provider_scope_hash=provider_scope_hash,
        semantic_cohort=core["cohort_id"], analytics_cohort=cohort["cohort_id"],
    )
    record = build_run_record(run, policy)
    updated, duplicate = append_run_record(ledger, record)
    if not validate_ledger_chain(updated):
        raise ValueError("UNIFIED_RUN_LEDGER_CHAIN_INVALID")
    errors = validate_instance(updated, ledger_schema_path)
    if errors:
        raise ValueError("UNIFIED_RUN_LEDGER_SCHEMA_INVALID:" + ";".join(errors))
    if not duplicate:
        cohort["ingested_runs"] += 1
        cohort["maturity_eligible_runs"] += int(record["maturity_eligible"])
        _atomic_write(ledger_path, updated)
        _atomic_write(cohort_path, cohort)
    analytics = build_event_resolution_analytics(updated["entries"])
    finding = {
        "schema_version": "2.0",
        "analytics_engine_version": "continuous-improvement-engine-2.0",
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "finding_type": "EVENT_ACTIONABILITY_ORCHESTRATION_GAP",
        "finding_status": "IMPLEMENTATION_REPAIR_REQUIRED",
        "manual_run_id": manual["run_id"],
        "manual_artifact_sha256": EXPECTED_MANUAL_SHA256,
        "run_provenance_status": record["run_provenance_status"],
        "maturity_eligible": record["maturity_eligible"],
        "duplicate_ingestion": duplicate,
        "event_resolution_analytics": analytics,
        "production_policy_auto_apply": False,
        "core_operational_counter_mutation": False,
        "portfolio_decision_counter_mutation": False,
        "portfolio_mutation": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    finding["finding_hash"] = canonical_hash(finding)
    return finding


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True, type=Path)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--ledger-schema", required=True, type=Path)
    parser.add_argument("--provider-scope", required=True, type=Path)
    parser.add_argument("--core-progress", required=True, type=Path)
    parser.add_argument("--finding-output", required=True, type=Path)
    args = parser.parse_args()
    finding = ingest(
        manual_path=args.manual, replay_path=args.replay, ledger_path=args.ledger,
        cohort_path=args.cohort, policy_path=args.policy,
        ledger_schema_path=args.ledger_schema, provider_scope_path=args.provider_scope,
        core_progress_path=args.core_progress,
    )
    _atomic_write(args.finding_output, finding)
    print(json.dumps({"status": "MANUAL_RUN_INGESTED", "maturity_eligible": False, "duplicate": finding["duplicate_ingestion"], "order_authority": False}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
