#!/usr/bin/env python3
"""Build immutable current Strategy Evolution artifacts without live-data calls."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from strategy_evolution import (
    append_evolution_entry,
    build_candidate_universe_snapshot,
    build_holding_universe_snapshot,
    build_champion_policy,
    build_no_change_decision,
    build_sentinel_challenger,
    build_strategy_evolution_report,
    empty_evolution_ledger,
)
from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _counter_subset(payload: dict[str, Any], names: tuple[str, ...]) -> dict[str, int]:
    return {name: int(payload.get(name) or 0) for name in names}


def build(repo: Path, output_dir: Path, generated_at: str) -> dict[str, Any]:
    portfolio_path = repo / "stock-strategy-system/portfolio_state.json"
    progress_path = repo / "workspace/state/integrated_shadow/shadow_progress.json"
    decision_cohort_path = repo / "workspace/state/portfolio_decision_cohort.json"
    analytics_cohort_path = repo / "workspace/state/continuous_improvement/improvement_analytics_cohort.json"
    current_evolution_cohort_path = repo / "workspace/state/strategy_evolution/strategy_evolution_cohort.json"
    provider_scope_path = repo / "workspace/policies/source_capabilities.json"
    event_policy_path = repo / "workspace/policies/event_risk_policy.json"
    decision_policy_path = repo / "workspace/policies/portfolio_reallocation_shadow_policy.json"
    reallocation_policy_path = decision_policy_path
    portfolio = load_json(portfolio_path)
    core = load_json(progress_path)
    decision = load_json(decision_cohort_path)
    analytics = load_json(analytics_cohort_path)
    tree_hash = _git(repo, "rev-parse", "HEAD^{tree}")
    semantic_material = {
        "tree_hash": tree_hash,
        "provider_scope_hash": file_hash(provider_scope_path),
        "event_policy_hash": file_hash(event_policy_path),
        "portfolio_decision_policy_hash": file_hash(decision_policy_path),
        "reallocation_policy_hash": file_hash(reallocation_policy_path),
    }
    current_evolution = load_json(current_evolution_cohort_path)
    current_champion_path = repo / current_evolution["current_artifact_directory"] / "champion_policy.json"
    if current_champion_path.is_file():
        champion = load_json(current_champion_path)
    else:
        champion = build_champion_policy(
            champion_policy_id="champion-read-only-v1",
            semantic_fingerprint=canonical_hash(semantic_material),
            git_tree_hash=tree_hash,
            provider_scope_hash=semantic_material["provider_scope_hash"],
            event_policy_hash=semantic_material["event_policy_hash"],
            portfolio_decision_policy_hash=semantic_material["portfolio_decision_policy_hash"],
            reallocation_policy_hash=semantic_material["reallocation_policy_hash"],
            activated_at=generated_at,
        )
    holding_universe = build_holding_universe_snapshot(
        decision_as_of=generated_at,
        instruments=[{
            "ticker": ticker,
            "security_identity": f"{ticker}-US",
            "observed_at": generated_at,
            "source_sha256": file_hash(portfolio_path),
        } for ticker in sorted((portfolio.get("holdings") or {}).keys())],
    )
    opportunity_universe = build_candidate_universe_snapshot(
        decision_as_of=generated_at, instruments=[],
        availability_status="UNAVAILABLE_AT_DECISION_TIME",
    )
    evolution_cohort_id = "strategy-evolution-" + canonical_hash({
        "policy": file_hash(repo / "workspace/policies/strategy_evolution_policy.json"),
        "engine": file_hash(repo / "manage-us-stock-strategy/scripts/strategy_evolution.py"),
    })[:16]
    report = build_strategy_evolution_report(
        generated_at=generated_at, champion=champion,
        holding_universe=holding_universe, candidate_universe=opportunity_universe,
        live_event_resolution_status="NO_GENUINE_RUN_YET",
        core_counters=_counter_subset(core, (
            "valid_finalized_sessions", "valid_paired_operational_days",
            "preopen_success_count", "postclose_success_count",
        )),
        portfolio_decision_counters=_counter_subset(decision, (
            "genuine_decision_observations", "genuine_full_compile_observations",
            "genuine_degraded_compile_observations", "genuine_actionable_decisions",
            "genuine_review_required_decisions",
        )),
        analytics_counters={
            "scheduled_genuine_ingested": 0,
            "manual_ingested": int(analytics.get("ingested_runs") or 0),
            "replay_ingested": 0, "shadow_ingested": 0, "outcome_records": 0,
        },
        event_resolution_counters={
            "live_resolution_exercised": 0, "live_resolution_success": 0,
            "live_resolution_partial": 0, "live_resolution_failed": 0,
        },
        evolution_cohort_id=evolution_cohort_id,
    )
    ledger = append_evolution_entry(empty_evolution_ledger(evolution_cohort_id), {
        "entry_type": "CHAMPION_FREEZE", "recorded_at": generated_at,
        "policy_fingerprint": champion["champion_fingerprint"],
        "hypothesis": None, "scope": "CURRENT_APPROVED_READ_ONLY_POLICY",
        "evidence_windows": [], "validation_result": "CHAMPION_FROZEN",
        "promotion_reason": "EXISTING_APPROVED_POLICY",
        "rollback_history": [], "auto_apply": False,
    })
    ledger = append_evolution_entry(ledger, build_no_change_decision(
        recorded_at=generated_at,
        reason="NO_BASE_GENUINE_DECISION_AND_INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE",
        champion_fingerprint=champion["champion_fingerprint"],
        evidence_grade="GRADE_D", evidence_sufficiency="INSUFFICIENT_EVIDENCE",
        uncertainty="INSUFFICIENT_EVIDENCE",
        out_of_sample_status="INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE",
    ))
    sentinel = build_sentinel_challenger(
        champion_fingerprint=champion["champion_fingerprint"], created_at=generated_at,
    )
    registry = {
        "schema_version": "1.0", "artifact_type": "REJECTED_CHALLENGER_REGISTRY",
        "mode": "APPEND_ONLY", "entries": [], "last_record_hash": None,
        "order_authority": False,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    artifacts = {
        "champion_policy.json": champion,
        "holding_universe_snapshot.json": holding_universe,
        "candidate_universe_snapshot.json": opportunity_universe,
        "sentinel_challenger.json": sentinel,
        "strategy_evolution_report.json": report,
        "strategy_evolution_ledger.json": ledger,
        "rejected_challenger_registry.json": registry,
    }
    for name, payload in artifacts.items():
        write_json(output_dir / name, payload)
    schemas = {
        "champion_policy.json": "champion-policy.schema.json",
        "holding_universe_snapshot.json": "holding-universe-snapshot.schema.json",
        "candidate_universe_snapshot.json": "candidate-universe-snapshot.schema.json",
        "sentinel_challenger.json": "sentinel-challenger.schema.json",
        "strategy_evolution_report.json": "strategy-evolution-report.schema.json",
        "strategy_evolution_ledger.json": "strategy-evolution-ledger.schema.json",
    }
    errors = {
        name: validate_instance(artifacts[name], repo / "manage-us-stock-strategy/schemas" / schema)
        for name, schema in schemas.items()
    }
    if any(errors.values()):
        raise ValueError(f"STRATEGY_EVOLUTION_SCHEMA_INVALID:{errors}")
    manifest = {
        "schema_version": "1.0", "generated_at": generated_at,
        "status": "STRATEGY_EVOLUTION_ENGINE_VERIFIED",
        "artifact_hashes": {name: file_hash(output_dir / name) for name in artifacts},
        "portfolio_hash": file_hash(portfolio_path),
        "portfolio_mutation": False, "execution_quantity": None,
        "quantity_authority": "none", "order_authority": False,
    }
    manifest["record_hash"] = canonical_hash(manifest)
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    build(args.repo.resolve(), args.output.resolve(), args.generated_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
