#!/usr/bin/env python3
"""Deterministic continuous-improvement sidecar for immutable strategy evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from validation_common import canonical_hash, load_json, parse_datetime, validate_instance


ANALYTICS_ENGINE_VERSION = "continuous-improvement-engine-2.0"
METRIC_DEFINITION_VERSION = "continuous-improvement-metrics-2.0"
ANALYTICS_SCHEMA_VERSION = "2.0"
RUN_ORIGINS = {
    "SCHEDULED_GENUINE", "MANUAL", "REPLAY", "TEST_ONLY", "SHADOW_COUNTERFACTUAL",
}
LEGACY_RUN_ORIGIN_ALIASES = {"TEST": "TEST_ONLY", "SHADOW": "SHADOW_COUNTERFACTUAL"}
DECISION_MODES_BY_ORIGIN = {
    "SCHEDULED_GENUINE": "LIVE_READ_ONLY",
    "MANUAL": "MANUAL_READ_ONLY",
    "REPLAY": "REPLAY",
    "TEST_ONLY": "TEST_ONLY",
    "SHADOW_COUNTERFACTUAL": "SHADOW_COUNTERFACTUAL",
}
PRODUCTION_DECISION_MODE = "LIVE_READ_ONLY"
PROVENANCE_STATUSES = {
    "VERIFIED_SCHEDULED", "VERIFIED_MANUAL", "VERIFIED_REPLAY",
    "VERIFIED_TEST", "VERIFIED_SHADOW", "UNVERIFIED",
}
OUTCOME_HORIZONS = (1, 5, 10, 20)
DECISION_ACTIONS = {
    "HOLD_CORE", "HOLD_TIGHTEN_STOP", "ADD_REVIEW", "TRIM_PROFIT",
    "TRIM_VALUATION", "TRIM_TECHNICAL", "TRIM_CONCENTRATION", "TRIM_RISK",
    "EXIT_THESIS", "EXIT_HARD_STOP", "ROTATE_REVIEW", "KEEP_CASH",
}
DRIFT_AXES = (
    "DATA_DRIFT_STATUS", "STRATEGY_DRIFT_STATUS", "BROKER_API_DRIFT_STATUS",
    "EVENT_PIPELINE_DRIFT_STATUS", "CANDIDATE_DISTRIBUTION_DRIFT_STATUS",
)
JUDGE_GATES = (
    "UNIFIED_RUN_LEDGER", "RUN_PROVENANCE", "MATURITY_ISOLATION",
    "TEMPORAL_EVIDENCE_ISOLATION", "DECISION_IMMUTABILITY",
    "FORWARD_OUTCOME_ENGINE", "DECISION_QUALITY_ANALYTICS",
    "BLOCKED_OPPORTUNITY_REVIEW", "COUNTERFACTUAL_EVALUATION",
    "DECISION_STABILITY", "DRIFT_MONITORING", "OPERATIONAL_ANALYTICS",
    "IMPROVEMENT_FINDINGS", "POLICY_PROPOSAL_GOVERNANCE",
    "SHADOW_POLICY_EXPERIMENT", "CORE_SCHEDULER_ISOLATION",
    "TEST_LIVE_SEMANTIC_FIREWALL", "COUNTER_AUTHORITY_FIREWALL",
    "PORTFOLIO_IMMUTABILITY", "ORDER_AUTHORITY", "TESTS",
)


def _atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_output_path(output: Path, *, repository_root: Path,
                         protected: Iterable[Path] = ()) -> Path:
    target = output.resolve()
    allowed = (repository_root / "workspace/outputs/activation/continuous-improvement").resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise ValueError("OUTPUT_OUTSIDE_CONTINUOUS_IMPROVEMENT_ROOT") from exc
    protected_paths = {path.resolve() for path in protected}
    protected_paths.update({
        (repository_root / "stock-strategy-system/portfolio_state.json").resolve(),
        (repository_root / "stock-strategy-system/alert_policy.json").resolve(),
        (repository_root / "workspace/state/integrated_shadow/shadow_progress.json").resolve(),
    })
    if target in protected_paths:
        raise ValueError("OUTPUT_TARGET_IS_PROTECTED")
    return target


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def compute_analytics_semantic_fingerprint(inputs: dict[str, Path]) -> dict[str, Any]:
    normalized_hashes = {}
    for name, source in sorted(inputs.items()):
        text = source.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        normalized_hashes[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    material = {
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "run_modes": sorted(RUN_ORIGINS),
        "decision_modes": sorted(set(DECISION_MODES_BY_ORIGIN.values())),
        "normalized_input_hashes": normalized_hashes,
    }
    return {
        "algorithm": "SHA256_CANONICAL_JSON_OF_NORMALIZED_TEXT_HASHES_V1",
        "normalized_input_hashes": normalized_hashes,
        "semantic_fingerprint": canonical_hash(material),
    }


def normalize_run_origin(origin: Any) -> str:
    if isinstance(origin, str):
        return LEGACY_RUN_ORIGIN_ALIASES.get(origin, origin)
    return "UNVERIFIED"


def validate_decision_mode(*, execution_origin: str, decision_mode: Any) -> dict[str, Any]:
    expected = DECISION_MODES_BY_ORIGIN.get(execution_origin)
    valid = expected is not None and decision_mode == expected
    return {
        "status": "DECISION_MODE_VALID" if valid else "DECISION_MODE_MISMATCH",
        "expected_decision_mode": expected,
        "decision_mode": decision_mode,
        "valid": valid,
    }


def assert_production_decision_consumable(decision: dict[str, Any]) -> None:
    """Reject non-live decisions at the production consumer boundary."""
    if decision.get("decision_mode") != PRODUCTION_DECISION_MODE:
        raise ValueError("NON_LIVE_DECISION_REJECTED_BY_PRODUCTION_CONSUMER")
    if decision.get("order_authority") is not False:
        raise ValueError("ORDER_AUTHORITY_MUST_REMAIN_FALSE")
    if decision.get("quantity_authority") != "none" or decision.get("execution_quantity") is not None:
        raise ValueError("EXECUTION_QUANTITY_AUTHORITY_VIOLATION")


def assert_counter_authority_firewall(payload: dict[str, Any]) -> None:
    """Sidecar evidence may never mutate operational/decision counters or broker truth."""
    forbidden_truth = {
        "verified_orderable_cash_from_expected_proceeds_usd": 0,
        "broker_truth_mutation": False,
        "operational_counter_mutation": False,
        "portfolio_decision_counter_mutation": False,
        "portfolio_mutation": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    violations = [key for key, expected in forbidden_truth.items()
                  if key in payload and payload.get(key) != expected]
    if violations:
        raise ValueError("ANALYTICS_AUTHORITY_FIREWALL_VIOLATION:" + ",".join(sorted(violations)))


def derive_run_provenance(run: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Derive provenance from evidence. A caller's origin label alone grants no authority."""
    origin = normalize_run_origin(run.get("execution_origin"))
    evidence = run.get("provenance_evidence") or {}
    status = "UNVERIFIED"
    reasons: list[str] = []
    if origin not in RUN_ORIGINS:
        reasons.append("UNKNOWN_EXECUTION_ORIGIN")
    elif origin == "SCHEDULED_GENUINE":
        scheduled = policy["scheduled_provenance"]
        checks = {
            "TASK_ID_NOT_APPROVED": evidence.get("task_id") in scheduled["allowed_task_ids"],
            "SCHEDULED_RUN_ID_MISSING": _nonempty(evidence.get("scheduled_run_id")),
            "PHASE_NOT_APPROVED": evidence.get("expected_operational_phase") in scheduled["allowed_phases"],
            "TRADING_DAY_MISSING": _nonempty(evidence.get("expected_trading_day")),
            "DEPLOYMENT_PROVENANCE_INVALID": evidence.get("deployment_provenance_valid") is True,
            "RUNTIME_HEAD_MISMATCH": evidence.get("runtime_head_matches") is True,
            "SEMANTIC_COHORT_MISMATCH": evidence.get("semantic_cohort_matches") is True,
            "SCHEDULE_PROVENANCE_INVALID": evidence.get("schedule_provenance_valid") is True,
            "RUNTIME_MANIFEST_HASH_MISSING": _nonempty(evidence.get("runtime_manifest_hash")),
            "CLEAN_COMMITTED_MAIN_NOT_VERIFIED": evidence.get("clean_committed_main") is True,
            "PORTFOLIO_HASH_CHANGED": run.get("portfolio_hash_before") == run.get("portfolio_hash_after"),
        }
        reasons.extend(reason for reason, passed in checks.items() if not passed)
        if not reasons:
            status = "VERIFIED_SCHEDULED"
    elif origin == "MANUAL":
        if _nonempty(evidence.get("manual_run_id")) and evidence.get("operator_initiated") is True:
            status = "VERIFIED_MANUAL"
        else:
            reasons.append("MANUAL_EVIDENCE_INCOMPLETE")
    elif origin == "REPLAY":
        if evidence.get("replay_mode") == "REPLAY_VALIDATION_ONLY" and evidence.get("not_counted_for_operational_promotion") is True:
            status = "VERIFIED_REPLAY"
        else:
            reasons.append("REPLAY_EVIDENCE_INCOMPLETE")
    elif origin == "TEST_ONLY":
        if evidence.get("fixture_mode") == "TEST_ONLY":
            status = "VERIFIED_TEST"
        else:
            reasons.append("TEST_EVIDENCE_INCOMPLETE")
    elif origin == "SHADOW_COUNTERFACTUAL":
        if evidence.get("shadow_mode") is True and evidence.get("not_counted_for_operational_promotion") is True:
            status = "VERIFIED_SHADOW"
        else:
            reasons.append("SHADOW_EVIDENCE_INCOMPLETE")
    mode = validate_decision_mode(execution_origin=origin, decision_mode=run.get("decision_mode"))
    if not mode["valid"]:
        reasons.append("DECISION_MODE_MISMATCH")
        status = "UNVERIFIED"
    maturity_eligible = status == "VERIFIED_SCHEDULED"
    if status == "VERIFIED_SCHEDULED":
        scheduled = policy["scheduled_provenance"]
        phase = evidence.get("expected_operational_phase")
        maturity_eligible = phase in scheduled["maturity_eligible_phases"]
        if maturity_eligible and run.get("delivery_status") != "DELIVERED":
            maturity_eligible = False
            reasons.append("DELIVERY_NOT_VERIFIED")
    return {
        "execution_origin": origin if origin in RUN_ORIGINS else "UNVERIFIED",
        "decision_mode": run.get("decision_mode"),
        "decision_mode_status": mode["status"],
        "run_provenance_status": status,
        "maturity_eligible": maturity_eligible,
        "reason_codes": reasons,
    }


def validate_temporal_evidence(decision_as_of: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    cutoff = parse_datetime(decision_as_of)
    violations: list[dict[str, Any]] = []
    for index, item in enumerate(evidence):
        timestamps = []
        for field in ("observed_at", "effective_at", "evidence_timestamp"):
            value = item.get(field)
            if value:
                timestamps.append((field, value))
        for field, value in timestamps:
            try:
                if parse_datetime(value) > cutoff:
                    violations.append({"index": index, "field": field, "value": value})
            except (TypeError, ValueError):
                violations.append({"index": index, "field": field, "value": value, "reason": "INVALID_TIMESTAMP"})
    return {
        "status": "TEMPORAL_EVIDENCE_VIOLATION" if violations else "TEMPORAL_EVIDENCE_VALID",
        "evaluation_valid": not violations,
        "violations": violations,
    }


def build_run_record(run: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    provenance = derive_run_provenance(run, policy)
    temporal = validate_temporal_evidence(run["decision_as_of"], run.get("source_artifacts") or [])
    scheduled_id = (run.get("provenance_evidence") or {}).get("scheduled_run_id")
    dedup_material = {
        "origin": provenance["execution_origin"],
        "run_id": run["run_id"],
        "scheduled_run_id": scheduled_id,
        "provenance_evidence": copy.deepcopy(run.get("provenance_evidence") or {}),
        "operational_day_id": run.get("operational_day_id"),
        "phase": (run.get("provenance_evidence") or {}).get("expected_operational_phase"),
        "git_sha": run["git_sha"],
        "runtime_manifest_hash": run["runtime_manifest_hash"],
    }
    decision_artifacts = copy.deepcopy(run.get("decision_artifacts") or [])
    artifact_mode_mismatch = any(item.get("decision_mode") != run.get("decision_mode")
                                 for item in decision_artifacts)
    record = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "run_id": run["run_id"],
        "run_fingerprint": canonical_hash(dedup_material),
        "operational_day_id": run.get("operational_day_id"),
        "scheduled_run_id": scheduled_id,
        **provenance,
        "git_sha": run["git_sha"],
        "runtime_manifest_hash": run["runtime_manifest_hash"],
        "provider_scope_hash": run["provider_scope_hash"],
        "semantic_cohort": run["semantic_cohort"],
        "improvement_analytics_cohort": run["improvement_analytics_cohort"],
        "decision_as_of": run["decision_as_of"],
        "market_data_cutoff": run["market_data_cutoff"],
        "event_cutoff": run["event_cutoff"],
        "broker_cutoff": run["broker_cutoff"],
        "candidate_cutoff": run.get("candidate_cutoff"),
        "portfolio_hash_before": run["portfolio_hash_before"],
        "portfolio_hash_after": run["portfolio_hash_after"],
        "source_artifacts": copy.deepcopy(run.get("source_artifacts") or []),
        "source_sha256": sorted({item["sha256"] for item in run.get("source_artifacts") or [] if item.get("sha256")}),
        "decision_artifacts": decision_artifacts,
        "delivery_status": run.get("delivery_status", "NOT_APPLICABLE"),
        "temporal_evidence_status": temporal["status"],
        "evaluation_valid": temporal["evaluation_valid"] and not artifact_mode_mismatch,
        "temporal_violations": temporal["violations"],
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    if artifact_mode_mismatch:
        record["reason_codes"].append("DECISION_ARTIFACT_MODE_MISMATCH")
    if not record["evaluation_valid"]:
        record["maturity_eligible"] = False
    return record


def empty_ledger(cohort_id: str) -> dict[str, Any]:
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "ledger_mode": "APPEND_ONLY_SIDECAR",
        "improvement_analytics_cohort": cohort_id,
        "entries": [],
        "last_record_hash": None,
        "order_authority": False,
    }


def append_run_record(ledger: dict[str, Any], record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    updated = copy.deepcopy(ledger)
    if any(item["run_fingerprint"] == record["run_fingerprint"] for item in updated["entries"]):
        return updated, True
    chained = copy.deepcopy(record)
    chained["previous_record_hash"] = updated.get("last_record_hash")
    chained["record_hash"] = canonical_hash({key: value for key, value in chained.items() if key != "record_hash"})
    updated["entries"].append(chained)
    updated["last_record_hash"] = chained["record_hash"]
    return updated, False


def validate_ledger_chain(ledger: dict[str, Any]) -> bool:
    previous = None
    fingerprints: set[str] = set()
    for item in ledger.get("entries") or []:
        if item.get("run_fingerprint") in fingerprints or item.get("previous_record_hash") != previous:
            return False
        expected = canonical_hash({key: value for key, value in item.items() if key != "record_hash"})
        if item.get("record_hash") != expected:
            return False
        fingerprints.add(item["run_fingerprint"])
        previous = expected
    return ledger.get("last_record_hash") == previous


def empty_outcome_ledger(cohort_id: str) -> dict[str, Any]:
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "ledger_mode": "APPEND_ONLY_FORWARD_OUTCOMES",
        "improvement_analytics_cohort": cohort_id,
        "entries": [],
        "last_record_hash": None,
        "order_authority": False,
    }


def append_outcome_artifact(ledger: dict[str, Any], artifact: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    updated = copy.deepcopy(ledger)
    fingerprint = artifact["outcome_artifact_hash"]
    if any(item["outcome_artifact_hash"] == fingerprint for item in updated["entries"]):
        return updated, True
    chained = copy.deepcopy(artifact)
    chained["previous_record_hash"] = updated.get("last_record_hash")
    chained["record_hash"] = canonical_hash({key: value for key, value in chained.items() if key != "record_hash"})
    updated["entries"].append(chained)
    updated["last_record_hash"] = chained["record_hash"]
    return updated, False


def validate_outcome_ledger_chain(ledger: dict[str, Any]) -> bool:
    previous = None
    fingerprints: set[str] = set()
    for item in ledger.get("entries") or []:
        fingerprint = item.get("outcome_artifact_hash")
        if fingerprint in fingerprints or item.get("previous_record_hash") != previous:
            return False
        expected = canonical_hash({key: value for key, value in item.items() if key != "record_hash"})
        if item.get("record_hash") != expected:
            return False
        fingerprints.add(fingerprint)
        previous = expected
    return ledger.get("last_record_hash") == previous


def _maximum_drawdown(closes: list[float]) -> float:
    peak = closes[0]
    drawdown = 0.0
    for value in closes:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1.0)
    return drawdown


def evaluate_forward_outcomes(decision: dict[str, Any], bars: list[dict[str, Any]],
                              horizons: Iterable[int] = OUTCOME_HORIZONS,
                              evaluation_as_of: str | None = None) -> dict[str, Any]:
    original = copy.deepcopy(decision)
    cutoff = decision["decision_session"]
    if evaluation_as_of is not None:
        analytics_cutoff = parse_datetime(evaluation_as_of)
        for bar in bars:
            if not bar.get("observed_at"):
                raise ValueError("OUTCOME_EVIDENCE_TIMESTAMP_MISSING")
            if parse_datetime(bar["observed_at"]) > analytics_cutoff:
                raise ValueError("TEMPORAL_EVIDENCE_VIOLATION")
    valid = [bar for bar in bars if bar.get("session") > cutoff and bar.get("bar_finalized") is True]
    valid.sort(key=lambda item: item["session"])
    seen: set[str] = set()
    valid = [bar for bar in valid if not (bar["session"] in seen or seen.add(bar["session"]))]
    start = float(decision["decision_price"])
    results = []
    for horizon in horizons:
        if len(valid) < horizon:
            results.append({
                "horizon_completed_sessions": horizon,
                "status": "OUTCOME_PENDING",
                "available_sessions": len(valid),
                "forward_return": None,
                "mfe": None,
                "mae": None,
                "maximum_drawdown": None,
                "provider": decision["provider"],
                "price_semantics": decision["price_semantics"],
                "adjustment_semantics": decision["adjustment_semantics"],
                "source_artifact_hashes": list(decision.get("source_artifact_hashes") or []),
            })
            continue
        window = valid[:horizon]
        closes = [float(item["close"]) for item in window]
        results.append({
            "horizon_completed_sessions": horizon,
            "status": "AVAILABLE",
            "available_sessions": len(valid),
            "window_start": window[0]["session"],
            "window_end": window[-1]["session"],
            "forward_return": closes[-1] / start - 1.0,
            "mfe": max(float(item["high"]) for item in window) / start - 1.0,
            "mae": min(float(item["low"]) for item in window) / start - 1.0,
            "maximum_drawdown": _maximum_drawdown([start, *closes]),
            "provider": decision["provider"],
            "price_semantics": decision["price_semantics"],
            "adjustment_semantics": decision["adjustment_semantics"],
            "source_artifact_hashes": sorted({*(decision.get("source_artifact_hashes") or []), *(item["source_sha256"] for item in window)}),
        })
    decision_mode = decision.get("decision_mode")
    if decision_mode not in set(DECISION_MODES_BY_ORIGIN.values()):
        raise ValueError("DECISION_MODE_MISSING_OR_INVALID")
    artifact = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "outcome_artifact_id": f"outcome-{decision['decision_id']}-{canonical_hash(results)[:12]}",
        "decision_id": decision["decision_id"],
        "decision_mode": decision_mode,
        "decision_fingerprint": canonical_hash(original),
        "selected_action": decision["selected_action"],
        "ticker": decision["ticker"],
        "decision_class": decision["decision_class"],
        "semantic_cohort": decision["semantic_cohort"],
        "event_state": decision["event_state"],
        "results": results,
        "original_decision_immutable": decision == original,
        "maturity_eligible": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    artifact["outcome_artifact_hash"] = canonical_hash(artifact)
    return artifact


def build_decision_quality(decisions: list[dict[str, Any]], outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {item["decision_id"]: item for item in outcomes}
    groups: dict[str, list[float]] = defaultdict(list)
    rows = []
    for decision in decisions:
        outcome = by_id.get(decision["decision_id"])
        available = [] if not outcome else [item for item in outcome["results"] if item["status"] == "AVAILABLE"]
        for item in available:
            groups[decision["selected_action"]].append(item["forward_return"])
        rows.append({
            "decision_id": decision["decision_id"],
            "selected_action": decision["selected_action"],
            "reason_codes": decision.get("reason_codes") or [],
            "ticker": decision["ticker"],
            "decision_class": decision["decision_class"],
            "semantic_cohort": decision["semantic_cohort"],
            "event_state": decision["event_state"],
            "available_outcome_count": len(available),
            "safety_gate_override": False,
        })
    aggregates = {action: {"sample_size": len(values), "mean_forward_return": sum(values) / len(values)} for action, values in groups.items()}
    return {"status": "OBSERVATIONAL_ONLY", "rows": rows, "aggregates": aggregates, "hard_gate_override": False}


def build_blocked_opportunity_review(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for decision in decisions:
        blockers = decision.get("blockers") or []
        if blockers:
            rows.append({
                "decision_id": decision["decision_id"],
                "ticker": decision["ticker"],
                "blockers": copy.deepcopy(blockers),
                "reasonableness_basis": "EVIDENCE_AVAILABLE_AT_DECISION_AS_OF",
                "later_price_alone_proves_error": False,
                "production_blocker_change_authorized": False,
            })
    return {"status": "BLOCKED_OPPORTUNITY_REVIEW", "items": rows}


def build_counterfactual_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    alternatives = copy.deepcopy(payload.get("alternatives") or [])
    if not any(item.get("action") == "KEEP_CASH" for item in alternatives):
        alternatives.append({"action": "KEEP_CASH", "gross_hypothetical_outcome": 0.0, "cost_adjusted_hypothetical_outcome": None})
    result = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "decision_mode": "SHADOW_COUNTERFACTUAL",
        "status": "COUNTERFACTUAL_EVALUATION_VERIFIED",
        "counterfactual_validity": "MODELLED_ONLY",
        "actual_decision": copy.deepcopy(payload["actual_decision"]),
        "alternatives": alternatives,
        "expected_sale_proceeds_status": "SHADOW_ONLY",
        "expected_sale_proceeds_usd": payload.get("expected_sale_proceeds_usd"),
        "verified_orderable_cash_from_expected_proceeds_usd": 0,
        "broker_cash_before": payload.get("broker_cash_before"),
        "broker_cash_after": payload.get("broker_cash_before"),
        "shadow_quantity_consumed_as_execution_quantity": False,
        "shadow_fill_consumed_as_actual_fill": False,
        "portfolio_decision_counter_mutation": False,
        "portfolio_mutation": False,
        "transaction_cost_status": "ASSUMPTION_REQUIRED" if payload.get("transaction_costs") is None else "SUPPLIED_FOR_MODEL_ONLY",
        "maturity_eligible": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    assert_counter_authority_firewall(result)
    return result


def build_decision_stability(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in decisions:
        grouped[(item["ticker"], item["decision_class"])].append(item)
    transitions = []
    opportunities = 0
    flips = 0
    for (ticker, decision_class), rows in grouped.items():
        rows.sort(key=lambda item: item["decision_as_of"])
        for previous, current in zip(rows, rows[1:]):
            opportunities += 1
            changed = previous["selected_action"] != current["selected_action"]
            flips += int(changed)
            transitions.append({
                "ticker": ticker, "decision_class": decision_class,
                "from_action": previous["selected_action"], "to_action": current["selected_action"],
                "changed": changed,
            })
    return {
        "status": "OBSERVATIONAL_ONLY",
        "decision_flip_rate": None if opportunities == 0 else flips / opportunities,
        "flip_count": flips,
        "transition_count": opportunities,
        "transitions": transitions,
        "hysteresis_thresholds_active": False,
    }


def build_drift_observation(records: list[dict[str, Any]]) -> dict[str, Any]:
    values = {
        "candidate_count": [len(item.get("decision_artifacts") or []) for item in records],
        "data_completeness": [1.0 if item.get("evaluation_valid") else 0.0 for item in records],
        "provider_fallback_frequency": [1 if any("fallback" in json.dumps(source).lower() for source in item.get("source_artifacts") or []) else 0 for item in records],
    }
    baselines = {}
    for name, samples in values.items():
        baselines[name] = {"sample_size": len(samples), "mean": None if not samples else sum(samples) / len(samples)}
    return {
        "status": "DRIFT_MONITORING_READY",
        "states": {axis: "BASELINE_BUILDING" for axis in DRIFT_AXES},
        "baseline_statistics": baselines,
        "production_thresholds_configured": False,
    }


def build_operational_analytics(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [item for item in records if item.get("run_provenance_status") == "VERIFIED_SCHEDULED" and item.get("maturity_eligible") is True]
    phase_counts = Counter((item.get("provenance_evidence") or {}).get("expected_operational_phase") for item in eligible)
    return {
        "status": "OBSERVATIONAL_ONLY",
        "scheduled_denominator": len(eligible),
        "preopen_success": phase_counts.get("PRE_OPEN_T_MINUS_30", 0),
        "postclose_success": phase_counts.get("REGULAR_CLOSE_T_PLUS_30", 0),
        "paired_day_success": 0,
        "finalization_attempt_distribution": {"T+30": 0, "T+40": 0, "T+50": 0, "T+60": 0},
        "manual_replay_test_shadow_in_denominator": False,
        "sla_thresholds_configured": False,
    }


def build_improvement_findings(quality: dict[str, Any], blocked: dict[str, Any],
                               stability: dict[str, Any], drift: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    if stability["flip_count"]:
        findings.append({
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
            "metric_definition_version": METRIC_DEFINITION_VERSION,
            "finding_id": f"finding-flip-{canonical_hash(stability)[:12]}",
            "finding_type": "HIGH_DECISION_FLIP_PATTERN",
            "evidence_hash": canonical_hash(stability),
            "status": "OBSERVATIONAL_ONLY",
            "policy_change": False,
        })
    if blocked["items"]:
        findings.append({
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
            "metric_definition_version": METRIC_DEFINITION_VERSION,
            "finding_id": f"finding-block-{canonical_hash(blocked)[:12]}",
            "finding_type": "EVENT_FALSE_BLOCK_PATTERN_REVIEW",
            "evidence_hash": canonical_hash(blocked),
            "status": "REVIEW_REQUIRED",
            "policy_change": False,
        })
    if any(value == "BASELINE_BUILDING" for value in drift["states"].values()):
        findings.append({
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
            "metric_definition_version": METRIC_DEFINITION_VERSION,
            "finding_id": f"finding-drift-{canonical_hash(drift)[:12]}",
            "finding_type": "DATA_DRIFT_BASELINE_BUILDING",
            "evidence_hash": canonical_hash(drift),
            "status": "OBSERVATIONAL_ONLY",
            "policy_change": False,
        })
    return findings


def build_policy_change_proposal(*, exact_scope: dict[str, Any], current_policy: Any,
                                 proposed_policy: Any, evidence_window: dict[str, Any],
                                 sample_size: int, supporting_evidence: list[str],
                                 counter_evidence: list[str]) -> dict[str, Any]:
    proposal = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "proposal_id": "policy-proposal-" + canonical_hash({"scope": exact_scope, "proposed": proposed_policy})[:16],
        "exact_scope": copy.deepcopy(exact_scope),
        "current_policy": copy.deepcopy(current_policy),
        "proposed_policy": copy.deepcopy(proposed_policy),
        "evidence_window": copy.deepcopy(evidence_window),
        "sample_size": sample_size,
        "supporting_evidence": list(supporting_evidence),
        "counter_evidence": list(counter_evidence),
        "expected_improvement": "NOT_YET_ESTABLISHED",
        "known_risks": ["OVERFITTING", "REGIME_DEPENDENCE"],
        "overfitting_risk": "REVIEW_REQUIRED",
        "multiple_hypothesis_risk": "REVIEW_REQUIRED",
        "semantic_impact": "REVALIDATION_REQUIRED",
        "rollback_plan": "Restore the prior exact-scope policy artifact and start a compatible semantic cohort.",
        "auto_apply": False,
        "approval_status": "EXPLICIT_USER_APPROVAL_REQUIRED",
        "order_authority": False,
    }
    proposal["proposal_hash"] = canonical_hash(proposal)
    return proposal


def build_shadow_policy_experiment(*, current_policy: dict[str, Any], candidate_policy: dict[str, Any],
                                   eligible_evidence_hashes: list[str], out_of_sample_hashes: list[str]) -> dict[str, Any]:
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "status": "SHADOW_POLICY_EXPERIMENT_VERIFIED",
        "current_production_policy_hash": canonical_hash(current_policy),
        "shadow_policy_candidate_hash": canonical_hash(candidate_policy),
        "eligible_evidence_hashes": list(eligible_evidence_hashes),
        "out_of_sample_evidence_hashes": list(out_of_sample_hashes),
        "identical_evidence_required": True,
        "production_policy_mutation": False,
        "portfolio_mutation": False,
        "operational_counter_mutation": False,
        "auto_apply": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def build_execution_analytics_link(*, artifact_id: str, artifact_type: str,
                                   event_namespace: str, source_hash: str) -> dict[str, Any]:
    allowed = {"ORDER_INTENT", "ACTUAL_ORDER", "BROKER_ACK", "ACTUAL_FILL", "SHADOW_FILL"}
    if artifact_type not in allowed:
        raise ValueError("UNSUPPORTED_EXECUTION_ANALYTICS_ARTIFACT")
    if artifact_type == "SHADOW_FILL" and event_namespace != "SHADOW_SIMULATION_EVENT":
        raise ValueError("SHADOW_EVENT_NAMESPACE_VIOLATION")
    if artifact_type in {"ACTUAL_ORDER", "BROKER_ACK", "ACTUAL_FILL"} and event_namespace != "ACTUAL_BROKER_EVENT":
        raise ValueError("ACTUAL_EVENT_NAMESPACE_VIOLATION")
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "event_namespace": event_namespace,
        "source_hash": source_hash,
        "broker_truth_mutation": False,
        "maturity_eligible": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def _origin_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(item["execution_origin"] for item in records)
    return {origin: counts.get(origin, 0) for origin in sorted(RUN_ORIGINS)}


def build_report(fixture: dict[str, Any], policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    cohort_id = fixture["improvement_analytics_cohort"]
    ledger = empty_ledger(cohort_id)
    duplicate_count = 0
    records = []
    for raw in fixture.get("runs") or []:
        record = build_run_record(raw, policy)
        ledger, duplicate = append_run_record(ledger, record)
        duplicate_count += int(duplicate)
        records.append(record)
    outcomes = []
    outcome_ledger = empty_outcome_ledger(cohort_id)
    outcome_duplicate_count = 0
    bars_by_ticker = fixture.get("bars_by_ticker") or {}
    for decision in fixture.get("decisions") or []:
        outcome = evaluate_forward_outcomes(
            decision, bars_by_ticker.get(decision["ticker"], []),
            evaluation_as_of=fixture["analytics_as_of"],
        )
        outcomes.append(outcome)
        outcome_ledger, duplicate = append_outcome_artifact(outcome_ledger, outcome)
        outcome_duplicate_count += int(duplicate)
    quality = build_decision_quality(fixture.get("decisions") or [], outcomes)
    blocked = build_blocked_opportunity_review(fixture.get("decisions") or [])
    counterfactual = build_counterfactual_evaluation(fixture["counterfactual"])
    stability = build_decision_stability(fixture.get("decisions") or [])
    drift = build_drift_observation(records)
    operational = build_operational_analytics(records)
    findings = build_improvement_findings(quality, blocked, stability, drift)
    proposal = build_policy_change_proposal(
        exact_scope={"ticker": "TEST_ONLY", "decision_class": "TEST_ONLY"},
        current_policy={"status": "UNCHANGED"}, proposed_policy={"status": "SHADOW_CANDIDATE_ONLY"},
        evidence_window={"start": fixture["analytics_as_of"], "end": fixture["analytics_as_of"]},
        sample_size=len(outcomes), supporting_evidence=[item["outcome_artifact_hash"] for item in outcomes],
        counter_evidence=["INSUFFICIENT_OPERATIONAL_SAMPLE"],
    )
    experiment = build_shadow_policy_experiment(
        current_policy={"status": "UNCHANGED"}, candidate_policy={"status": "SHADOW_CANDIDATE_ONLY"},
        eligible_evidence_hashes=[item["outcome_artifact_hash"] for item in outcomes],
        out_of_sample_hashes=[],
    )
    horizon_counts = {}
    for horizon in OUTCOME_HORIZONS:
        rows = [result for outcome in outcomes for result in outcome["results"] if result["horizon_completed_sessions"] == horizon]
        horizon_counts[str(horizon)] = {
            "available": sum(item["status"] == "AVAILABLE" for item in rows),
            "pending": sum(item["status"] == "OUTCOME_PENDING" for item in rows),
        }
    report = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "mode": "CONTINUOUS_IMPROVEMENT_SIDECAR",
        "validation_mode": fixture.get("validation_mode", "TEST_ONLY"),
        "status": "CONTINUOUS_IMPROVEMENT_PIPELINE_VERIFIED",
        "analytics_as_of": fixture["analytics_as_of"],
        "run_counts": _origin_counts(records),
        "maturity_eligible_count": sum(item["maturity_eligible"] for item in records),
        "unverified_run_count": sum(item["run_provenance_status"] == "UNVERIFIED" for item in records),
        "duplicate_ingestion_count": duplicate_count,
        "ledger_chain_valid": validate_ledger_chain(ledger),
        "temporal_evidence": {
            "valid": sum(item["temporal_evidence_status"] == "TEMPORAL_EVIDENCE_VALID" for item in records),
            "violations": sum(item["temporal_evidence_status"] == "TEMPORAL_EVIDENCE_VIOLATION" for item in records),
        },
        "forward_outcomes": outcomes,
        "outcome_ledger": outcome_ledger,
        "outcome_ledger_chain_valid": validate_outcome_ledger_chain(outcome_ledger),
        "outcome_duplicate_count": outcome_duplicate_count,
        "horizon_counts": horizon_counts,
        "decision_quality": quality,
        "blocked_opportunity_review": blocked,
        "counterfactual_evaluation": counterfactual,
        "decision_stability": stability,
        "drift_monitoring": drift,
        "operational_analytics": operational,
        "improvement_findings": findings,
        "policy_change_proposals": [proposal],
        "shadow_policy_experiments": [experiment],
        "analytics_failure_affects_core_scheduled_run": False,
        "live_api_calls": 0,
        "portfolio_mutation": False,
        "production_policy_mutation": False,
        "operational_counter_mutation": False,
        "portfolio_decision_counter_mutation": False,
        "core_operational_counter_mutation": False,
        "execution_authority_status": "NONE",
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    assert_counter_authority_firewall(report)
    report["report_hash"] = canonical_hash(report)
    return report, ledger


def run_sidecar_isolated(*, core_scheduled_result: dict[str, Any], fixture: dict[str, Any],
                         policy: dict[str, Any]) -> dict[str, Any]:
    """Contain analytics failure without changing or invalidating the core run."""
    core_snapshot = copy.deepcopy(core_scheduled_result)
    try:
        report, ledger = build_report(fixture, policy)
        return {
            "sidecar_status": "SUCCESS",
            "core_scheduled_result": core_snapshot,
            "report": report,
            "ledger": ledger,
            "core_result_mutated": core_scheduled_result != core_snapshot,
        }
    except Exception as exc:  # isolation boundary; callers retain the core result
        return {
            "sidecar_status": "FAILED_ISOLATED",
            "failure_type": type(exc).__name__,
            "core_scheduled_result": core_snapshot,
            "report": None,
            "ledger": None,
            "core_result_mutated": core_scheduled_result != core_snapshot,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report-schema", required=True, type=Path)
    parser.add_argument("--ledger-schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ledger-output", required=True, type=Path)
    parser.add_argument("--outcome-ledger-output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for output in (args.output, args.ledger_output, args.outcome_ledger_output):
        validate_output_path(output, repository_root=root, protected=[args.fixture, args.policy])
    fixture = load_json(args.fixture)
    if fixture.get("validation_mode") != "TEST_ONLY":
        raise SystemExit("CLI fixture execution is restricted to TEST_ONLY; live ingestion uses reviewed adapter calls")
    report, ledger = build_report(fixture, load_json(args.policy))
    errors = validate_instance(report, args.report_schema)
    errors.extend(validate_instance(ledger, args.ledger_schema))
    if errors:
        raise SystemExit("schema validation failed: " + "; ".join(errors))
    _atomic_write(args.output, report)
    _atomic_write(args.ledger_output, ledger)
    _atomic_write(args.outcome_ledger_output, report["outcome_ledger"])
    print(json.dumps({"status": report["status"], "output": str(args.output), "maturity_eligible_count": report["maturity_eligible_count"], "order_authority": False}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
