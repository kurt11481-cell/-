#!/usr/bin/env python3
"""Pinned validation gate for externally supplied scheduled analysis input.

Moved out of run_manual_portfolio_analysis.py (which re-exports it) so that
the manual adapter can change without re-pinning the Kiwoom acceptance.
The gate only reads; it never collects evidence, writes, or promotes a run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from continuous_improvement_sidecar import derive_run_provenance
from manual_data_guards import _timestamp
from session_aware_market_data import ET
from session_authority import derive_us_market_session_authority


ROOT = Path(__file__).resolve().parents[2]


def validate_scheduled_input(
    evidence: dict[str, Any], supplied: dict[str, Any], *, evidence_sha256: str,
    expected_head: str, runtime_repo: Path = ROOT,
    session_authority_resolver: Callable[..., Any] = derive_us_market_session_authority,
    provenance_deriver: Callable[..., dict[str, Any]] = derive_run_provenance,
) -> dict[str, Any]:
    """Validate an externally supplied scheduled run; never collect or promote it.

    scheduled_run_id identifies the logical run, while run_id identifies this
    analysis and scheduled_occurrence_id identifies the task/phase occurrence.
    The caller supplies an existing run and deployment manifest on every call.
    This is a compilation gate, not operational maturity or delivery evidence.
    """
    from continuous_improvement_sidecar import validate_temporal_evidence
    from deployment_provenance import verify_current_provenance
    from validation_common import canonical_hash

    if not isinstance(supplied, dict) or not isinstance(supplied.get("run"), dict):
        raise ValueError("SCHEDULED_PROVENANCE_REQUIRED")
    run = supplied["run"]
    pe = run.get("provenance_evidence")
    manifest = supplied.get("deployment_provenance")
    if not isinstance(pe, dict) or not isinstance(manifest, dict):
        raise ValueError("SCHEDULED_PROVENANCE_REQUIRED")
    policy_path = runtime_repo / "workspace/policies/continuous_improvement_policy.json"
    failures = verify_current_provenance(
        manifest, expected_head=expected_head, runtime_repo=runtime_repo,
        provider_scope_path=runtime_repo / "workspace/policies/kiwoom-session-aware-priority-policy.json",
        progress_path=runtime_repo / "workspace/state/integrated_shadow/shadow_progress.json",
        required_code_paths=(
            "manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py",
            "manage-us-stock-strategy/scripts/portfolio_decision_dashboard.py",
            "manage-us-stock-strategy/scripts/portfolio_decision_order_intent.py",
            "manage-us-stock-strategy/scripts/deployment_provenance.py",
            "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json",
        ),
        required_policy_paths=("workspace/policies/continuous_improvement_policy.json",),
    )
    if failures:
        raise ValueError("SCHEDULED_DEPLOYMENT_NOT_VERIFIED:" + ";".join(sorted(set(failures))))
    policy_bytes = policy_path.read_bytes()
    policy = json.loads(policy_bytes)
    if hashlib.sha256(policy_bytes).hexdigest() != (manifest.get("policy_hashes") or {}).get("workspace/policies/continuous_improvement_policy.json"):
        failures.append("SCHEDULED_CONSUMED_POLICY_HASH_MISMATCH")
    expected_mode = {
        "report_type": "SCHEDULED_PORTFOLIO_ANALYSIS_PREFLIGHT",
        "run_mode": "LIVE_READ_ONLY", "trigger_type": "SCHEDULED_GENUINE",
        "operator_initiated": False, "run_provenance_status": "VERIFIED_SCHEDULED",
        "evidence_grade": "GRADE_A", "backfill": False,
        "maturity_eligible": False, "operational_maturity_eligible": False,
        "policy_evolution_eligible": False, "scheduled_pair_eligible": False,
    }
    if any(evidence.get(k) != v for k, v in expected_mode.items()):
        failures.append("SCHEDULED_EVIDENCE_MODE_MISMATCH")
    if run.get("execution_origin") != "SCHEDULED_GENUINE" or run.get("decision_mode") != "LIVE_READ_ONLY":
        failures.append("SCHEDULED_SOURCE_MODE_MISMATCH")
    if pe.get("operator_initiated") is not False or pe.get("trigger_type") != "SCHEDULED_GENUINE":
        failures.append("SCHEDULED_SOURCE_TRIGGER_MISMATCH")
    if pe.get("manual_run_id") is not None:
        failures.append("MANUAL_PROVENANCE_MASQUERADING")
    if run.get("run_id") != evidence.get("manual_run_id") or run.get("decision_as_of") != evidence.get("decision_as_of"):
        failures.append("SCHEDULED_EVIDENCE_BINDING_MISMATCH")
    phase = pe.get("expected_operational_phase")
    task_phase = "REGULAR_CLOSE_T_PLUS_30" if phase == "POST_MARKET_FINALIZED" else phase
    task_mapping = {"PRE_OPEN_T_MINUS_30": "automation",
                    "REGULAR_CLOSE_T_PLUS_30": "post-close-portfolio-strategy"}
    actual_task_id = supplied.get("task_id")
    # The analytics policy uses logical phase IDs; deployment uses App task IDs.
    if (actual_task_id != task_mapping.get(task_phase) or task_phase is None
            or pe.get("task_id") != task_phase
            or not any(t.get("task_id") == actual_task_id and t.get("run_phase") == task_phase
                       for t in manifest.get("tasks", []) if isinstance(t, dict))):
        failures.append("SCHEDULED_TASK_PHASE_MAPPING_MISMATCH")
    occurrence = canonical_hash({"task_id": actual_task_id, "run_phase": phase,
                                 "scheduled_run_id": pe.get("scheduled_run_id"),
                                 "scheduled_at": supplied.get("scheduled_at")})
    if evidence.get("scheduled_occurrence_id") != occurrence or supplied.get("scheduled_occurrence_id") != occurrence:
        failures.append("SCHEDULED_OCCURRENCE_BINDING_MISMATCH")
    try:
        scheduled_at = _timestamp(supplied.get("scheduled_at"))
        observed = _timestamp(evidence.get("observed_at"))
        cutoff = _timestamp(evidence.get("decision_as_of"))
        from dual_run_scheduler import build_session_schedule
        authority = session_authority_resolver(
            evidence["decision_as_of"], primary_listing_operating_mic="XNYS",
            decision_as_of=evidence["decision_as_of"],
        )
        window = authority.current_date_session
        if (authority.authority_status != "VERIFIED" or window is None
                or authority.calendar_hash != evidence.get("calendar_hash")
                or authority.activation_cohort_id != evidence.get("session_activation_cohort_id")):
            raise ValueError("SCHEDULED_OFFICIAL_SESSION_NOT_VERIFIED")
        schedule = build_session_schedule({
            "official_calendar_verified": True, "is_trading_day": True,
            "session": window.session_date, "core_open_at": window.core_open_at,
            "core_close_at": window.core_close_at, "calendar_source": authority.calendar_hash,
        })
        times = (schedule["finalization_retry_at"] if phase == "POST_MARKET_FINALIZED" else
                 [r["scheduled_at"] for r in schedule["runs"] if r["run_phase"] == phase])
        if scheduled_at not in [_timestamp(t) for t in times] or pe.get("scheduled_run_id") != schedule["scheduled_run_id"]:
            failures.append("SCHEDULED_OFFICIAL_OCCURRENCE_MISMATCH")
        if not scheduled_at <= observed <= cutoff or (cutoff - scheduled_at).total_seconds() > 900:
            failures.append("SCHEDULED_TEMPORAL_BINDING_MISMATCH")
        if pe.get("expected_trading_day") != evidence.get("trading_date") or scheduled_at.astimezone(ET).date().isoformat() != evidence.get("trading_date"):
            failures.append("SCHEDULED_TRADING_DAY_MISMATCH")
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        failures.append("SCHEDULED_TIMESTAMP_OR_OFFICIAL_SESSION_INVALID")
    if (run.get("git_sha") != expected_head or pe.get("runtime_manifest_hash") != manifest.get("record_hash")
            or run.get("runtime_manifest_hash") != manifest.get("record_hash")
            or run.get("semantic_cohort") != manifest.get("semantic_cohort_id")):
        failures.append("SCHEDULED_DEPLOYMENT_BINDING_MISMATCH")
    portfolio_hash = (evidence.get("system_portfolio_state") or {}).get("source_sha256")
    if not portfolio_hash or run.get("portfolio_hash_before") != portfolio_hash or run.get("portfolio_hash_after") != portfolio_hash:
        failures.append("SCHEDULED_PORTFOLIO_HASH_MISMATCH")
    sources = run.get("source_artifacts")
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(s, dict) for s in sources)
            or not any(s.get("sha256") == evidence_sha256 and s.get("observed_at") == evidence.get("decision_as_of") for s in sources)):
        failures.append("SCHEDULED_SOURCE_EVIDENCE_HASH_MISSING")
    else:
        try:
            if not validate_temporal_evidence(run["decision_as_of"], sources)["evaluation_valid"]:
                failures.append("SCHEDULED_TEMPORAL_EVIDENCE_INVALID")
        except (KeyError, TypeError, ValueError):
            failures.append("SCHEDULED_TEMPORAL_EVIDENCE_INVALID")
    if run.get("temporal_evidence_status") != "TEMPORAL_EVIDENCE_VALID":
        failures.append("SCHEDULED_TEMPORAL_STATUS_REQUIRED")
    derived = provenance_deriver(run, policy)
    if derived["run_provenance_status"] != "VERIFIED_SCHEDULED" or not derived["decision_quality_eligible"]:
        failures.append("SCHEDULED_CANONICAL_PROVENANCE_NOT_VERIFIED")
    p = evidence.get("provenance") or {}
    if any(p.get(k) != v for k, v in {
        "execution_origin": "SCHEDULED_GENUINE", "decision_mode": "LIVE_READ_ONLY",
        "run_provenance_status": "VERIFIED_SCHEDULED", "evidence_grade": "GRADE_A",
        "decision_quality_eligible": True, "maturity_eligible": False,
        "operational_maturity_eligible": False, "policy_evolution_eligible": False,
    }.items()):
        failures.append("SCHEDULED_REPORT_PROVENANCE_MISMATCH")
    if failures:
        raise ValueError("SCHEDULED_INPUT_NOT_VERIFIED:" + ";".join(sorted(set(failures))))
    return {"trigger_type": "SCHEDULED_GENUINE",
            "run_provenance_status": "VERIFIED_SCHEDULED_GENUINE",
            "actual_scheduled_run": True, "scheduled_occurrence_id": occurrence,
            "operational_grade": "GRADE_A_CANDIDATE", "scheduled_maturity_promoted": False}
