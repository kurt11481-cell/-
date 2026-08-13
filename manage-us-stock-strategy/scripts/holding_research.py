#!/usr/bin/env python3
"""Deterministic v2.6 Shadow holding-research baseline, overlay, and compiler."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, parse_datetime, validate_instance


BASELINE_FORBIDDEN_FIELDS = {
    "holdings", "current_shares", "average_cost", "average_cost_usd",
    "available_cash_usd", "current_market_price", "hard_risk_observation",
    "execution_state", "strategy_signal", "quantity", "fills", "orders",
    "broker_snapshot", "broker_extraction",
}
VALID_BASELINE_CONTENT = {"COMPLETE", "PARTIAL"}
ELIGIBLE_RISK_RESULTS = {"ALLOW_REVIEW", "DOWNGRADE"}
SHA256_PATTERN_LENGTH = 64


def research_packet_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable evidence/thesis payload owned by the research layer."""
    return {
        "ticker": record.get("ticker"),
        "analysis_cutoff": record.get("analysis_cutoff"),
        "evidence_cutoff": record.get("evidence_cutoff"),
        "claims": record.get("claims", []),
        "evidence": record.get("evidence", []),
        "primary_reason": record.get("primary_reason"),
        "strongest_counter_case": record.get("strongest_counter_case"),
        "invalidation_conditions": record.get("invalidation_conditions", []),
        "next_research_triggers": record.get("next_research_triggers", []),
    }


def baseline_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Exclude lifecycle fields so activation does not change the immutable hash."""
    excluded = {"baseline_hash", "validation_status", "activated_at"}
    return {key: value for key, value in record.items() if key not in excluded}


def recompute_hashes(record: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(record)
    value["research_packet_hash"] = canonical_hash(research_packet_payload(value))
    value["baseline_hash"] = canonical_hash(baseline_payload(value))
    return value


def _evidence_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = record.get("evidence") if isinstance(record.get("evidence"), list) else []
    claims = record.get("claims") if isinstance(record.get("claims"), list) else []
    evidence_by_id: dict[str, dict[str, Any]] = {}
    try:
        cutoff = parse_datetime(str(record.get("evidence_cutoff")))
    except (ValueError, TypeError):
        return ["EVIDENCE_CUTOFF_INVALID"]
    for item in evidence:
        if not isinstance(item, dict) or not item.get("evidence_id"):
            errors.append("EVIDENCE_ID_MISSING")
            continue
        evidence_by_id[str(item["evidence_id"])] = item
        if item.get("point_in_time_eligible") is not True:
            errors.append(f"EVIDENCE_NOT_POINT_IN_TIME_ELIGIBLE:{item['evidence_id']}")
        if item.get("verification_status") != "VERIFIED":
            errors.append(f"EVIDENCE_NOT_VERIFIED:{item['evidence_id']}")
        url = str(item.get("source_url") or "")
        if not url.startswith("https://"):
            errors.append(f"EVIDENCE_URL_NOT_HTTPS:{item['evidence_id']}")
        published = item.get("published_at")
        if not published:
            errors.append(f"EVIDENCE_PUBLISHED_AT_MISSING:{item['evidence_id']}")
        else:
            try:
                if parse_datetime(str(published)) > cutoff:
                    errors.append(f"FUTURE_KNOWN_EVIDENCE:{item['evidence_id']}")
            except ValueError:
                errors.append(f"EVIDENCE_PUBLISHED_AT_INVALID:{item['evidence_id']}")
    for claim in claims:
        if not isinstance(claim, dict) or not claim.get("claim_id"):
            errors.append("CLAIM_ID_MISSING")
            continue
        references = claim.get("evidence_ids")
        if not isinstance(references, list) or not references:
            errors.append(f"CLAIM_WITHOUT_EVIDENCE:{claim['claim_id']}")
        else:
            for evidence_id in references:
                if str(evidence_id) not in evidence_by_id:
                    errors.append(f"CLAIM_EVIDENCE_NOT_FOUND:{claim['claim_id']}:{evidence_id}")
    return errors


def validate_baseline(record: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    errors = validate_instance(record, schema_path)
    for forbidden in sorted(BASELINE_FORBIDDEN_FIELDS.intersection(record)):
        errors.append(f"FORBIDDEN_BASELINE_FIELD:{forbidden}")
    if record.get("content_status") not in VALID_BASELINE_CONTENT:
        errors.append("BASELINE_CONTENT_NOT_ACTIVATABLE")
    if record.get("thesis_status") in {"UNVERIFIED", "STALE", None}:
        errors.append("BASELINE_THESIS_NOT_ACTIVATABLE")
    if record.get("risk_controller_result") not in ELIGIBLE_RISK_RESULTS:
        errors.append("RISK_CONTROLLER_NOT_ELIGIBLE")
    if record.get("point_in_time_status") != "PASSED":
        errors.append("POINT_IN_TIME_GATE_FAILED")
    errors.extend(_evidence_errors(record))
    expected_packet_hash = canonical_hash(research_packet_payload(record))
    expected_baseline_hash = canonical_hash(baseline_payload(record))
    if record.get("research_packet_hash") != expected_packet_hash:
        errors.append("RESEARCH_PACKET_HASH_MISMATCH")
    if record.get("baseline_hash") != expected_baseline_hash:
        errors.append("BASELINE_HASH_MISMATCH")
    return {
        "validation_status": "PASSED" if not errors else "FAILED",
        "activation_status": "VALIDATED_SHADOW" if not errors else "REJECTED",
        "errors": list(dict.fromkeys(errors)),
        "locally_computed_research_packet_hash": expected_packet_hash,
        "locally_computed_baseline_hash": expected_baseline_hash,
        "quantity_authority": "none",
        "order_authority": False,
    }


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def activate_baseline(record: dict[str, Any], *, schema_path: Path, baseline_root: Path,
                      index_path: Path, activated_at: str, mode: str = "SHADOW") -> dict[str, Any]:
    validation = validate_baseline(record, schema_path)
    if validation["validation_status"] != "PASSED":
        return {**validation, "ticker": record.get("ticker"), "index_updated": False}
    if mode not in {"SHADOW", "MIGRATION"}:
        raise ValueError("baseline activation is restricted to SHADOW or MIGRATION")
    activated = deepcopy(record)
    activated["validation_status"] = "VALIDATED_SHADOW"
    activated["activated_at"] = activated_at
    ticker = str(activated["ticker"])
    baseline_id = str(activated["baseline_id"])
    target = baseline_root / ticker / f"{baseline_id}.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if canonical_hash(existing) != canonical_hash(activated):
            return {**validation, "activation_status": "REJECTED", "errors": ["IMMUTABLE_BASELINE_EXISTS"], "ticker": ticker, "index_updated": False}
    else:
        _atomic_write_json(target, activated)
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"schema_version": "2.6", "mode": mode, "updated_at": activated_at, "active": {},
                 "historical_alert_replay_allowed": False, "portfolio_state_mutation": False,
                 "order_authority": False}
    previous = (index.get("active") or {}).get(ticker)
    if previous and previous.get("baseline_id") == baseline_id:
        return {**validation, "ticker": ticker, "activation_status": "VALIDATED_SHADOW", "index_updated": False,
                "baseline_path": str(target), "active_index_path": str(index_path)}
    index.setdefault("active", {})[ticker] = {
        "baseline_id": baseline_id,
        "baseline_version": activated["baseline_version"],
        "baseline_hash": activated["baseline_hash"],
        "research_packet_hash": activated["research_packet_hash"],
        "activated_at": activated_at,
        "baseline_path": target.as_posix(),
    }
    index["updated_at"] = activated_at
    _atomic_write_json(index_path, index)
    return {**validation, "ticker": ticker, "activation_status": "VALIDATED_SHADOW", "index_updated": True,
            "baseline_path": str(target), "active_index_path": str(index_path)}


def evaluate_freshness(record: dict[str, Any], *, as_of: str, max_age_days: int) -> dict[str, Any]:
    try:
        age = (parse_datetime(as_of) - parse_datetime(str(record.get("evidence_cutoff")))).total_seconds() / 86400
    except ValueError:
        return {"freshness_status": "INVALID", "age_days": None, "errors": ["FRESHNESS_TIMESTAMP_INVALID"]}
    if age < 0:
        return {"freshness_status": "INVALID", "age_days": age, "errors": ["FUTURE_EVIDENCE_CUTOFF"]}
    return {"freshness_status": "FRESH" if age <= max_age_days else "STALE", "age_days": age, "errors": []}


def build_overlay(*, ticker: str, market_session: str, primary_price_status: str,
                  independent_price_status: str, technical_status: str, event_risk_status: str,
                  hard_risk_observation: str, risk_status: str, portfolio_fit_status: str,
                  cash_status: str, broker_snapshot_status: str,
                  leveraged_confirmation_status: str = "NOT_APPLICABLE",
                  active_timing_tranche: str | None = None, rearm_status: str = "NOT_APPLICABLE",
                  portfolio_state_revision: int = 0, quantity: int | None = None,
                  quantity_authority: str = "none",
                  deterministic_existing_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    if quantity is not None and quantity_authority != "deterministic_existing_policy":
        raise ValueError("quantity requires deterministic_existing_policy authority")
    value = {
        "schema_version": "2.6", "ticker": ticker, "market_session": market_session,
        "primary_price_status": primary_price_status, "independent_price_status": independent_price_status,
        "technical_status": technical_status, "event_risk_status": event_risk_status,
        "hard_risk_observation": hard_risk_observation, "risk_status": risk_status,
        "portfolio_fit_status": portfolio_fit_status, "cash_status": cash_status,
        "broker_snapshot_status": broker_snapshot_status,
        "leveraged_confirmation_status": leveraged_confirmation_status,
        "active_timing_tranche": active_timing_tranche, "rearm_status": rearm_status,
        "portfolio_state_revision": portfolio_state_revision,
        "deterministic_existing_policy": deterministic_existing_policy,
        "quantity": quantity, "quantity_authority": quantity_authority, "order_authority": False,
    }
    value["overlay_hash"] = canonical_hash(value)
    return value


def validate_overlay_hash(overlay: dict[str, Any]) -> bool:
    payload = {key: value for key, value in overlay.items() if key != "overlay_hash"}
    return overlay.get("overlay_hash") == canonical_hash(payload)


def compile_context(profile: dict[str, Any], baseline: dict[str, Any], overlay: dict[str, Any],
                    *, baseline_schema: Path) -> dict[str, Any]:
    if "strategy_signal" in baseline:
        raise ValueError("raw research strategy_signal is prohibited")
    baseline_validation = validate_baseline(baseline, baseline_schema)
    remaining: list[str] = []
    if not validate_overlay_hash(overlay):
        remaining.append("OVERLAY_HASH_INVALID")
    profile_ticker = profile.get("ticker") or baseline.get("ticker")
    if baseline.get("ticker") != overlay.get("ticker") or baseline.get("ticker") != profile_ticker:
        remaining.append("TICKER_IDENTITY_MISMATCH")

    content_usable = baseline_validation["validation_status"] == "PASSED"
    signal = "NONE"
    strategy_state = "HOLD"
    risk_status = overlay.get("risk_status", "UNVERIFIED")
    hard_risk = overlay.get("hard_risk_observation") == "PRIMARY_BREACH_OBSERVED"
    approved_action = ((overlay.get("deterministic_existing_policy") or {}).get("action_on_breach"))

    valuation_required_but_unverified = (
        baseline.get("valuation_applicability") != "NOT_APPLICABLE_TO_PRODUCT"
        and baseline.get("valuation_status") in {"UNVERIFIED", "STALE", None}
    )
    fundamental_risk_unverified = baseline.get("fundamental_risk_status") == "UNVERIFIED"

    if not content_usable:
        strategy_state = "STRATEGY_REFRESH_REQUIRED"
        remaining.extend(baseline_validation["errors"])
    elif valuation_required_but_unverified or fundamental_risk_unverified:
        strategy_state = "STRATEGY_REFRESH_REQUIRED"
        if valuation_required_but_unverified:
            remaining.append("DIRECT_OR_UNDERLYING_VALUATION_REFRESH_REQUIRED")
        if fundamental_risk_unverified:
            remaining.append("FUNDAMENTAL_RISK_REFRESH_REQUIRED")
    elif remaining:
        strategy_state = "DATA_BLOCKED"
    elif baseline.get("thesis_status") == "INVALIDATED" or risk_status == "VETO":
        signal = "EXIT_CANDIDATE"
        strategy_state = "EXIT_REVIEW"
    elif hard_risk:
        if approved_action == "exit_review":
            signal, strategy_state = "EXIT_CANDIDATE", "EXIT_REVIEW"
        elif approved_action == "reduction_review":
            signal, strategy_state = "REDUCE_CANDIDATE", "REDUCTION_REVIEW"
        else:
            strategy_state = "STRATEGY_REFRESH_REQUIRED"
            remaining.append("HARD_RISK_ACTION_AUTHORITY_REQUIRED")
    else:
        valuation = baseline.get("valuation_status")
        valuation_applicable = baseline.get("valuation_applicability") != "NOT_APPLICABLE_TO_PRODUCT"
        reduction_evidence = (
            baseline.get("thesis_status") == "CONTESTED"
            and (valuation == "STRETCHED" if valuation_applicable else True)
            and overlay.get("technical_status") == "DETERIORATING"
        ) or risk_status == "CONSTRAINED" or overlay.get("portfolio_fit_status") == "CONSTRAINED"
        add_evidence = (
            baseline.get("thesis_status") == "VALID"
            and (valuation in {"ATTRACTIVE", "FAIR"} if valuation_applicable else True)
            and overlay.get("technical_status") == "READY"
            and overlay.get("event_risk_status") == "CLEAR"
            and risk_status == "ACCEPTABLE"
            and overlay.get("portfolio_fit_status") == "FITS"
        )
        if reduction_evidence:
            signal, strategy_state = "REDUCE_CANDIDATE", "REDUCTION_REVIEW"
        elif add_evidence:
            signal, strategy_state = "ADD_CANDIDATE", "ADD_REVIEW"
        elif overlay.get("technical_status") in {"WATCH", "DETERIORATING"}:
            strategy_state = "ADD_ON_WATCH" if baseline.get("research_recommendation") == "POTENTIAL_ADD_CASE" else "HOLD"

    quantity = None
    quantity_authority = "none"
    if overlay.get("quantity_authority") == "deterministic_existing_policy" and isinstance(overlay.get("quantity"), int):
        quantity = overlay["quantity"]
        quantity_authority = "deterministic_existing_policy"
    return {
        "schema_version": "2.6", "mode": "SHADOW_ONLY", "ticker": baseline.get("ticker"),
        "research_packet_hash": baseline.get("research_packet_hash", "0" * 64),
        "baseline_hash": baseline.get("baseline_hash", "0" * 64),
        "overlay_hash": overlay.get("overlay_hash", "0" * 64),
        "baseline_content_status": baseline.get("content_status", "INVALID"),
        "thesis_status": baseline.get("thesis_status", "UNVERIFIED"),
        "valuation_status": baseline.get("valuation_status", "UNVERIFIED"),
        "valuation_applicability": baseline.get("valuation_applicability", "DIRECT"),
        "valuation_basis": baseline.get("valuation_basis", "NBIS_ISSUER"),
        "technical_status": overlay.get("technical_status", "UNAVAILABLE"),
        "risk_status": risk_status, "portfolio_fit_status": overlay.get("portfolio_fit_status", "UNVERIFIED"),
        "strategy_signal": signal, "strategy_state": strategy_state,
        "primary_reason": baseline.get("primary_reason") or "BASELINE_REFRESH_REQUIRED",
        "strongest_counter_case": baseline.get("strongest_counter_case") or "BASELINE_REFRESH_REQUIRED",
        "invalidation": baseline.get("invalidation_conditions") or ["BASELINE_REFRESH_REQUIRED"],
        "next_review_trigger": baseline.get("next_research_triggers") or ["BASELINE_REFRESH_REQUIRED"],
        "claim_ids": baseline.get("claim_ids") or ["BASELINE_REFRESH_REQUIRED"],
        "remaining_conditions": list(dict.fromkeys(remaining)),
        "quantity": quantity, "quantity_authority": quantity_authority, "order_authority": False,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
