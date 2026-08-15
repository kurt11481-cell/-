#!/usr/bin/env python3
"""Deterministic, read-only Champion/Challenger strategy-evolution contracts."""

from __future__ import annotations

import copy
import re
from datetime import datetime
from typing import Any

from validation_common import canonical_hash, parse_datetime


SCHEMA_VERSION = "1.0"
ANALYTICS_ENGINE_VERSION = "strategy-evolution-engine-1.0"
METRIC_DEFINITION_VERSION = "strategy-evolution-metrics-1.0"
SCORECARD_VERSION = "portfolio-optimization-scorecard-1.0"
REGIME_DEFINITION_VERSION = "NOT_CONFIGURED"
TRANSACTION_COST_MODEL_VERSION = "NOT_CONFIGURED"
POLICY_EVALUATION_VERSION = "champion-challenger-evaluation-1.0"
OUTCOME_HORIZONS = (1, 5, 10, 20)
SCORECARD_AXES = ("RETURN", "STABILITY", "OPTIMIZATION", "EFFICIENCY", "ROBUSTNESS", "EXECUTABILITY")
EVALUATION_ORDER = ("DATA_INTEGRITY", "HARD_SAFETY", "EXECUTABILITY", "STABILITY", "OPTIMIZATION", "RETURN", "EFFICIENCY")
DOMINANCE_STATUSES = {
    "DOMINATES_CHAMPION", "NON_DOMINATED_DIFFERENT_PROFILE", "UNDERPERFORMS_CHAMPION",
    "INSUFFICIENT_EVIDENCE", "SAFETY_REJECTED", "EXECUTION_REJECTED",
}
SAFE_FALLBACK_REASONS = {
    "SAFE_FALLBACK_EVENT_UNRESOLVED", "SAFE_FALLBACK_NO_ELIGIBLE_CANDIDATE",
    "SAFE_FALLBACK_INSUFFICIENT_VERIFIED_CASH", "SAFE_FALLBACK_BROKER_VISIBILITY",
    "SAFE_FALLBACK_PORTFOLIO_RISK", "SAFE_FALLBACK_EXECUTION_FEASIBILITY",
}
EXPECTED_HEAD_PATTERN = re.compile(
    r"(?:expected|EXPECTED)\s+(?:runtime\s+)?HEAD(?:\s+SHA)?\s*(?:is|=|:)?\s*[`'\"]?([0-9a-fA-F]{40})"
)


def _versions() -> dict[str, str]:
    return {
        "analytics_engine_version": ANALYTICS_ENGINE_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "scorecard_version": SCORECARD_VERSION,
        "regime_definition_version": REGIME_DEFINITION_VERSION,
        "transaction_cost_model_version": TRANSACTION_COST_MODEL_VERSION,
        "policy_evaluation_version": POLICY_EVALUATION_VERSION,
        "schema_version": SCHEMA_VERSION,
    }


def extract_prompt_expected_head(prompt: str) -> str | None:
    match = EXPECTED_HEAD_PATTERN.search(prompt)
    return match.group(1).lower() if match else None


def build_champion_policy(*, champion_policy_id: str, semantic_fingerprint: str,
                          git_tree_hash: str, provider_scope_hash: str,
                          event_policy_hash: str, portfolio_decision_policy_hash: str,
                          reallocation_policy_hash: str, activated_at: str) -> dict[str, Any]:
    payload = {
        **_versions(),
        "artifact_type": "CHAMPION_POLICY",
        "champion_policy_id": champion_policy_id,
        "semantic_fingerprint": semantic_fingerprint,
        "git_tree_hash": git_tree_hash,
        "provider_scope_hash": provider_scope_hash,
        "event_policy_hash": event_policy_hash,
        "portfolio_decision_policy_hash": portfolio_decision_policy_hash,
        "reallocation_policy_hash": reallocation_policy_hash,
        "activated_at": activated_at,
        "status": "APPROVED_READ_ONLY_PRODUCTION_CHAMPION",
        "auto_apply": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    payload["champion_fingerprint"] = canonical_hash(payload)
    return payload


def build_candidate_universe_snapshot(*, decision_as_of: str,
                                      instruments: list[dict[str, Any]]) -> dict[str, Any]:
    cutoff = parse_datetime(decision_as_of)
    identities: set[tuple[str, str]] = set()
    normalized = []
    for item in instruments:
        ticker = str(item.get("ticker") or "").upper()
        identity = str(item.get("security_identity") or "")
        observed_at = parse_datetime(str(item.get("observed_at") or decision_as_of))
        if not ticker or not identity:
            raise ValueError("CANDIDATE_IDENTITY_INCOMPLETE")
        if observed_at > cutoff:
            raise ValueError("CANDIDATE_UNIVERSE_LOOKAHEAD")
        key = (ticker, identity)
        if key in identities:
            raise ValueError("DUPLICATE_CANDIDATE_IDENTITY")
        identities.add(key)
        normalized.append({
            "ticker": ticker,
            "security_identity": identity,
            "eligibility_state": item.get("eligibility_state", "UNVERIFIED"),
            "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
            "source_sha256": item.get("source_sha256"),
        })
    normalized.sort(key=lambda row: (row["ticker"], row["security_identity"]))
    payload = {
        **_versions(),
        "artifact_type": "CANDIDATE_UNIVERSE_SNAPSHOT",
        "candidate_universe_as_of": decision_as_of,
        "instrument_identities": normalized,
        "survivorship_reconstruction_forbidden": True,
        "order_authority": False,
    }
    payload["candidate_universe_hash"] = canonical_hash(payload)
    return payload


def classify_evidence_eligibility(*, run_provenance_status: str,
                                  temporal_evidence_valid: bool,
                                  decision_artifact_valid: bool,
                                  actionable_decision: bool) -> dict[str, Any]:
    grade = {
        "VERIFIED_SCHEDULED": "GRADE_A",
        "VERIFIED_MANUAL": "GRADE_B",
        "VERIFIED_REPLAY": "GRADE_C",
        "VERIFIED_TEST": "GRADE_D",
        "VERIFIED_SHADOW": "GRADE_D",
    }.get(run_provenance_status, "UNVERIFIED")
    valid = temporal_evidence_valid and decision_artifact_valid and grade != "UNVERIFIED"
    genuine = run_provenance_status == "VERIFIED_SCHEDULED" and valid
    return {
        "evidence_grade": grade,
        "operational_maturity_eligible": genuine,
        "decision_quality_eligible": valid and grade in {"GRADE_A", "GRADE_B", "GRADE_C"},
        "counterfactual_eligible": valid and grade in {"GRADE_A", "GRADE_B", "GRADE_C", "GRADE_D"},
        "policy_evolution_eligible": genuine,
        "genuine_decision_observation": genuine,
        "actionable_decision": bool(actionable_decision and valid),
    }


def validate_paired_evidence(champion: dict[str, Any], challenger: dict[str, Any]) -> dict[str, Any]:
    required = (
        "decision_as_of", "market_evidence_hash", "event_evidence_hash", "broker_state_hash",
        "candidate_universe_hash", "policy_independent_source_hash",
    )
    mismatches = [key for key in required if champion.get(key) != challenger.get(key)]
    return {
        "status": "PAIRED_EVIDENCE_VALID" if not mismatches else "PAIRED_EVIDENCE_INVALID",
        "mismatched_fields": mismatches,
        "causal_comparison_eligible": not mismatches,
    }


def build_forward_horizon_status(*, completed_sessions_available: int) -> dict[str, Any]:
    return {
        str(horizon): {
            "status": "AVAILABLE" if completed_sessions_available >= horizon else "OUTCOME_PENDING",
            "completed_trading_sessions_required": horizon,
        }
        for horizon in OUTCOME_HORIZONS
    }


def _axis(status: str, metrics: dict[str, Any] | None = None,
          reason_codes: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "metrics": copy.deepcopy(metrics or {}), "reason_codes": list(reason_codes or [])}


def build_portfolio_optimization_scorecard(*, data_integrity: str, hard_safety: str,
                                           executability: str,
                                           champion_metrics: dict[str, dict[str, Any]] | None = None,
                                           challenger_metrics: dict[str, dict[str, Any]] | None = None,
                                           evidence_sample_size: int = 0) -> dict[str, Any]:
    champion_metrics = champion_metrics or {}
    challenger_metrics = challenger_metrics or {}
    hard_gate = data_integrity == "PASS" and hard_safety == "PASS"
    executable = executability == "PASS"
    sufficient = evidence_sample_size > 0
    axes = {
        axis: _axis(
            "EVALUATED" if sufficient else "INSUFFICIENT_EVIDENCE",
            {"champion": champion_metrics.get(axis, {}), "challenger": challenger_metrics.get(axis, {})},
        )
        for axis in SCORECARD_AXES
    }
    payload = {
        **_versions(),
        "artifact_type": "PORTFOLIO_OPTIMIZATION_SCORECARD",
        "evaluation_order": list(EVALUATION_ORDER),
        "single_composite_score_authority": False,
        "data_integrity_status": data_integrity,
        "hard_safety_status": hard_safety,
        "executability_status": executability,
        "axes": axes,
        "evidence_sample_size": evidence_sample_size,
        "policy_thresholds_invented": False,
        "order_authority": False,
    }
    if not hard_gate:
        payload["dominance_status"] = "SAFETY_REJECTED"
    elif not executable:
        payload["dominance_status"] = "EXECUTION_REJECTED"
    elif not sufficient:
        payload["dominance_status"] = "INSUFFICIENT_EVIDENCE"
    else:
        payload["dominance_status"] = "NON_DOMINATED_DIFFERENT_PROFILE"
    payload["scorecard_hash"] = canonical_hash(payload)
    return payload


def classify_six_axis_dominance(*, scorecard: dict[str, Any],
                                challenger_deltas: dict[str, float] | None) -> str:
    gate_status = scorecard.get("dominance_status")
    if gate_status in {"SAFETY_REJECTED", "EXECUTION_REJECTED", "INSUFFICIENT_EVIDENCE"}:
        return str(gate_status)
    deltas = challenger_deltas or {}
    if set(deltas) != set(SCORECARD_AXES):
        return "INSUFFICIENT_EVIDENCE"
    values = list(deltas.values())
    if all(value >= 0 for value in values) and any(value > 0 for value in values):
        return "DOMINATES_CHAMPION"
    if all(value <= 0 for value in values) and any(value < 0 for value in values):
        return "UNDERPERFORMS_CHAMPION"
    return "NON_DOMINATED_DIFFERENT_PROFILE"


def build_uncertainty(*, paired_sample_size: int, out_of_sample_available: bool) -> dict[str, Any]:
    return {
        "evidence_uncertainty_status": "INSUFFICIENT_EVIDENCE" if paired_sample_size == 0 else "OBSERVATIONAL_ONLY",
        "paired_sample_size": paired_sample_size,
        "confidence_interval": None,
        "bootstrap_uncertainty": None,
        "out_of_sample_status": "AVAILABLE" if out_of_sample_available else "INSUFFICIENT_OUT_OF_SAMPLE_EVIDENCE",
        "significance_threshold_configured": False,
    }


def build_decision_attribution(attributions: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = {
        "ENTRY_TIMING", "EXIT_TIMING", "PROFIT_PROTECTION", "VALUATION_TRIM", "TECHNICAL_TRIM",
        "EVENT_BLOCKING", "EVENT_RESOLUTION", "CANDIDATE_SELECTION", "CAPITAL_ALLOCATION",
        "CASH_ALLOCATION", "CONCENTRATION", "ROTATION", "TURNOVER",
    }
    invalid = [row.get("scope") for row in attributions if row.get("scope") not in allowed]
    if invalid:
        raise ValueError("UNKNOWN_ATTRIBUTION_SCOPE:" + ",".join(map(str, invalid)))
    return {"status": "ATTRIBUTED" if attributions else "INSUFFICIENT_EVIDENCE", "attributions": copy.deepcopy(attributions)}


def generate_challenger_hypotheses(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hypotheses = []
    for index, finding in enumerate(findings, start=1):
        exact_scope = copy.deepcopy(finding.get("exact_scope") or {})
        hypotheses.append({
            "hypothesis_id": f"challenger-hypothesis-{index:03d}",
            "source_finding_id": finding.get("finding_id"),
            "exact_scope": exact_scope,
            "experiment_scope": sorted(exact_scope),
            "mechanism": finding.get("candidate_mechanism", "UNCLASSIFIED"),
            "expected_benefit": finding.get("expected_benefit", "NOT_QUANTIFIED"),
            "expected_risk": finding.get("expected_risk", "NOT_QUANTIFIED"),
            "required_evidence": list(finding.get("required_evidence") or []),
            "status": "HYPOTHESIS_ONLY",
        })
    return hypotheses


def build_policy_change_proposal(*, proposal_id: str, champion_policy_id: str,
                                 challenger_policy_id: str, hypothesis: dict[str, Any],
                                 evidence_window: dict[str, Any], sample_size: int,
                                 impacts: dict[str, Any], counter_evidence: list[str],
                                 out_of_sample_status: str, uncertainty: dict[str, Any],
                                 number_of_challengers_tested: int,
                                 number_rejected: int, selected_rank: int | None,
                                 rollback_plan: str) -> dict[str, Any]:
    return {
        **_versions(),
        "artifact_type": "POLICY_CHANGE_PROPOSAL",
        "proposal_id": proposal_id,
        "exact_scope": copy.deepcopy(hypothesis.get("exact_scope") or {}),
        "champion_policy_id": champion_policy_id,
        "challenger_policy_id": challenger_policy_id,
        "hypothesis": copy.deepcopy(hypothesis),
        "evidence_window": copy.deepcopy(evidence_window),
        "sample_size": sample_size,
        "impacts": copy.deepcopy(impacts),
        "counter_evidence": list(counter_evidence),
        "out_of_sample_status": out_of_sample_status,
        "uncertainty": copy.deepcopy(uncertainty),
        "number_of_challengers_tested": number_of_challengers_tested,
        "number_rejected": number_rejected,
        "selected_rank": selected_rank,
        "multiple_hypothesis_risk": "PRESENT" if number_of_challengers_tested > 1 else "LIMITED",
        "overfitting_risk": "UNRESOLVED" if out_of_sample_status != "AVAILABLE" else "REVIEW_REQUIRED",
        "semantic_cohort_impact": "REQUIRES_PRE_APPLY_CLASSIFICATION",
        "rollback_plan": rollback_plan,
        "auto_apply": False,
        "production_applied": False,
        "order_authority": False,
    }


def empty_evolution_ledger(cohort_id: str) -> dict[str, Any]:
    return {
        **_versions(),
        "artifact_type": "STRATEGY_EVOLUTION_LEDGER",
        "cohort_id": cohort_id,
        "mode": "APPEND_ONLY",
        "entries": [],
        "last_record_hash": None,
        "order_authority": False,
    }


def append_evolution_entry(ledger: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(ledger)
    payload = copy.deepcopy(entry)
    payload["previous_record_hash"] = updated.get("last_record_hash")
    payload["record_hash"] = canonical_hash(payload)
    updated["entries"].append(payload)
    updated["last_record_hash"] = payload["record_hash"]
    return updated


def validate_evolution_ledger(ledger: dict[str, Any]) -> bool:
    previous = None
    for row in ledger.get("entries") or []:
        candidate = copy.deepcopy(row)
        record_hash = candidate.pop("record_hash", None)
        if candidate.get("previous_record_hash") != previous or canonical_hash(candidate) != record_hash:
            return False
        previous = record_hash
    return ledger.get("last_record_hash") == previous


def rejected_challenger_match(registry: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    fingerprint = canonical_hash({"exact_scope": candidate.get("exact_scope"), "mechanism": candidate.get("mechanism")})
    matches = [row for row in registry.get("entries") or [] if row.get("similarity_fingerprint") == fingerprint]
    return {
        "status": "SIMILAR_REJECTED_POLICY_FOUND" if matches else "NO_SIMILAR_REJECTED_POLICY",
        "similarity_fingerprint": fingerprint,
        "matched_rejection_ids": [row.get("rejection_id") for row in matches],
        "new_evidence_required": bool(matches),
    }


def build_strategy_evolution_report(*, generated_at: str, champion: dict[str, Any],
                                    candidate_universe: dict[str, Any],
                                    live_event_resolution_status: str,
                                    core_counters: dict[str, int],
                                    portfolio_decision_counters: dict[str, int],
                                    analytics_counters: dict[str, int],
                                    event_resolution_counters: dict[str, int],
                                    evolution_cohort_id: str) -> dict[str, Any]:
    scorecard = build_portfolio_optimization_scorecard(
        data_integrity="PASS", hard_safety="PASS", executability="NOT_READY",
        evidence_sample_size=0,
    )
    report = {
        **_versions(),
        "artifact_type": "STRATEGY_EVOLUTION_CURRENT_STATE",
        "generated_at": generated_at,
        "status": "STRATEGY_EVOLUTION_ENGINE_VERIFIED",
        "lifecycle_status": "FIRST_GENUINE_DUAL_RUN_PENDING",
        "champion_policy_id": champion["champion_policy_id"],
        "champion_fingerprint": champion["champion_fingerprint"],
        "candidate_universe_hash": candidate_universe["candidate_universe_hash"],
        "live_event_resolution_status": live_event_resolution_status,
        "safe_fallback_reasons": sorted(SAFE_FALLBACK_REASONS),
        "forward_outcomes": build_forward_horizon_status(completed_sessions_available=0),
        "portfolio_optimization_scorecard": scorecard,
        "paired_evaluation_status": "INSUFFICIENT_EVIDENCE",
        "uncertainty": build_uncertainty(paired_sample_size=0, out_of_sample_available=False),
        "decision_attribution": build_decision_attribution([]),
        "improvement_findings": [],
        "challenger_hypotheses": [],
        "six_axis_dominance": "INSUFFICIENT_EVIDENCE",
        "evidence_sufficiency_status": "INSUFFICIENT_EVIDENCE",
        "evolution_budget_status": "OBSERVATIONAL_NO_NUMERIC_LIMIT",
        "policy_stability_status": {"fast_loop": "READY", "medium_loop": "OUTCOME_PENDING", "slow_loop": "NO_CHANGE_PROPOSED"},
        "policy_change_proposals": [],
        "auto_apply": False,
        "evolution_authority": "EVOLUTION_4",
        "evolution_5_enabled": False,
        "execution_authority_status": "NONE",
        "core_counters": copy.deepcopy(core_counters),
        "portfolio_decision_counters": copy.deepcopy(portfolio_decision_counters),
        "analytics_counters": copy.deepcopy(analytics_counters),
        "event_resolution_counters": copy.deepcopy(event_resolution_counters),
        "strategy_evolution_counters": {"champions": 1, "challengers": 0, "outcomes": 0, "proposals": 0},
        "strategy_evolution_cohort": evolution_cohort_id,
        "portfolio_mutation": False,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }
    report["report_hash"] = canonical_hash(report)
    return report


def validate_safety(payload: dict[str, Any]) -> None:
    if payload.get("order_authority") is not False:
        raise ValueError("ORDER_AUTHORITY_VIOLATION")
    if payload.get("quantity_authority") not in {None, "none"}:
        raise ValueError("QUANTITY_AUTHORITY_VIOLATION")
    if payload.get("execution_quantity") is not None:
        raise ValueError("EXECUTION_QUANTITY_VIOLATION")
    if payload.get("auto_apply") is True:
        raise ValueError("POLICY_AUTO_APPLY_VIOLATION")
