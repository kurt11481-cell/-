#!/usr/bin/env python3
"""Build a fail-closed, read-only seven-candidate tactical opportunity radar."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from screen_tactical_candidates import _lane_for, _market_integrity
from portfolio_policy_gates import evaluate_cash_status
from price_evidence import crosscheck_required, evidence_status
from validate_registry_consistency import validate_registry_consistency
from validation_common import canonical_hash, load_json, validate_instance, write_json


ACTIVE_SYMBOLS = ("MVLL", "SOXL", "NBIS", "BE", "TOST", "NOW", "FSLY")
OPPORTUNITY_ORDER = {"DATA_BLOCKED": 0, "NOT_READY": 1, "WATCH": 2, "NEAR_TRIGGER": 3, "READY": 4}
IDENTITY_INCOMPLETE_VALUES = {"UNVERIFIED", "user_supplied_pending_primary_verification", "identity_incomplete"}
INTERNAL_CONDITION_IDS = {
    "IDENTITY_VERIFICATION", "OFFICIAL_SESSION_VERIFICATION", "SESSION_ALIGNMENT",
    "COMPLETED_OHLCV", "CORPORATE_ACTION_RESOLUTION", "TECHNICAL_VALIDATION",
    "INDEPENDENT_COMPLETED_CLOSE", "POLICY_REGISTRY_CONSISTENCY",
    "NEW_BUY_INSTRUMENT_APPROVAL", "VERIFIED_AVAILABLE_CASH", "PORTFOLIO_REVIEW",
    "THESIS_RESEARCH", "UNAPPROVED_CONDITION_ID", "NEXT_COMPLETED_US_SESSION",
}


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _active_candidates(universe: dict[str, Any]) -> list[str]:
    return [symbol for symbol, row in (universe.get("candidates") or {}).items()
            if row.get("candidate_status") == "active" and row.get("watchlist_approved") is True]


def _validated_context(context: dict[str, Any]) -> bool:
    validation = context.get("validation") or {}
    return (
        validation.get("status") == "VALIDATED"
        and validation.get("evidence_packet_validated") is True
        and validation.get("deterministic_gate_status") == "PASS"
        and validation.get("risk_controller_status") in {"ALLOW_REVIEW", "DOWNGRADE"}
    )


def _technical_from_market(row: dict[str, Any] | None, context: dict[str, Any]) -> tuple[str, list[str]]:
    """Derive technical authority from the validated market row; context may only downgrade."""
    if not isinstance(row, dict):
        return "UNAVAILABLE", ["COMPLETED_OHLCV"]
    if row.get("breakout_acceptance_confirmed") is True or row.get("ema20_reclaim_confirmed") is True:
        derived, remaining = "READY", []
    elif row.get("ema10_reclaim_confirmed") is True:
        # The approved SOXL policy treats EMA10 alone as observation, not an actionable reduction/entry trigger.
        derived, remaining = "WATCH", ["EMA20_RECLAIM_CONFIRMED", "BREAKOUT_ACCEPTANCE_CONFIRMED"]
    else:
        derived = "WATCH"
        remaining = ["EMA10_RECLAIM_CONFIRMED", "EMA20_RECLAIM_CONFIRMED", "BREAKOUT_ACCEPTANCE_CONFIRMED"]
    explicit = context.get("technical_status")
    if explicit in {"INVALID", "UNAVAILABLE"}:
        return explicit, list(context.get("technical_remaining_conditions") or remaining)
    if explicit == "WATCH" and derived == "READY":
        return "WATCH", list(context.get("technical_remaining_conditions") or ["PULLBACK_CONFIRMATION"])
    return derived, remaining


def _event_status(events: dict[str, Any], symbol: str) -> tuple[str, str]:
    """Expose known events, but downgrade only for an approved WAIT_REQUIRED policy effect."""
    coverage = events.get("coverage_status", "EVENT_DATA_INCOMPLETE")
    if coverage == "EVENT_DATA_INCOMPLETE":
        return "EVENT_DATA_INCOMPLETE", "EVENT_DATA_INCOMPLETE"
    known = [event for event in events.get("events", []) if event.get("ticker") in {symbol, "GLOBAL"}]
    applicable = [event for event in known if event.get("validation_status") == "VALIDATED" and event.get("policy_effect") == "WAIT_REQUIRED"]
    if applicable:
        return "KNOWN_EVENT", "WAIT_REQUIRED"
    if known:
        return "KNOWN_EVENT", "CONTEXT_ONLY"
    if coverage == "COMPLETE":
        return "CLEAR", "NONE"
    return "EVENT_DATA_INCOMPLETE", "EVENT_DATA_INCOMPLETE"


def _condition_code(message: str) -> str:
    lower = message.lower()
    if "calendar" in lower or "regular session" in lower:
        return "OFFICIAL_SESSION_VERIFICATION"
    if "session mismatch" in lower or "bar date" in lower:
        return "SESSION_ALIGNMENT"
    if "ohlcv" in lower or "market data unavailable" in lower:
        return "COMPLETED_OHLCV"
    if "corporate-action" in lower:
        return "CORPORATE_ACTION_RESOLUTION"
    if "indicator" in lower:
        return "TECHNICAL_VALIDATION"
    if "cross-check" in lower:
        return "INDEPENDENT_COMPLETED_CLOSE"
    return "EVIDENCE_REFRESH"


def _sanitize_conditions(values: list[Any], approved: set[str]) -> tuple[list[str], bool]:
    conditions: list[str] = []
    rejected = False
    for value in values:
        if isinstance(value, str) and value in approved:
            if value not in conditions:
                conditions.append(value)
        else:
            rejected = True
    return conditions, rejected


def _opportunity_state(*, identity_status: str, evidence: str, thesis: str, valuation: str,
                       technical: str, event_policy_effect: str, risk_liquidity: str,
                       portfolio_fit: str, context_valid: bool, condition_rejected: bool) -> str:
    if condition_rejected or identity_status in IDENTITY_INCOMPLETE_VALUES or evidence == "FAIL" or technical == "UNAVAILABLE":
        return "DATA_BLOCKED"
    if thesis == "WEAK" or valuation == "STRETCHED" or technical == "INVALID" or risk_liquidity == "VETO" or portfolio_fit == "BLOCKED":
        return "NOT_READY"
    research_ok = context_valid and thesis in {"STRONG", "CONTESTED"} and valuation in {"ATTRACTIVE", "FAIR"}
    if evidence == "PASS" and research_ok and technical == "READY" and risk_liquidity == "ACCEPTABLE" and portfolio_fit in {"FITS", "CONSTRAINED"}:
        return "NEAR_TRIGGER" if event_policy_effect in {"WAIT_REQUIRED", "EVENT_DATA_INCOMPLETE"} else "READY"
    if evidence in {"PASS", "CONDITIONAL"} and research_ok and technical in {"READY", "WATCH"} and risk_liquidity != "VETO" and portfolio_fit != "BLOCKED":
        return "NEAR_TRIGGER"
    return "WATCH"


def _execution_state(opportunity_state: str, *, registry_valid: bool, new_buy_approved: bool,
                     cash_status: str, portfolio_fit: str) -> str:
    if opportunity_state == "DATA_BLOCKED" or not registry_valid:
        return "DATA_BLOCKED"
    if not new_buy_approved:
        return "NOT_APPROVED"
    if portfolio_fit == "BLOCKED":
        return "PORTFOLIO_BLOCKED"
    if cash_status != "VERIFIED_POSITIVE":
        return "CASH_BLOCKED"
    return "ELIGIBLE_FOR_REVIEW" if opportunity_state == "READY" else "WATCH_ONLY"


def _primary_blocker(opportunity: str, execution: str, remaining: list[str]) -> str | None:
    if opportunity == "DATA_BLOCKED":
        return remaining[0] if remaining else "DATA_INCOMPLETE"
    mapping = {"DATA_BLOCKED": "POLICY_REGISTRY_CONSISTENCY", "NOT_APPROVED": "NEW_BUY_INSTRUMENT_APPROVAL",
               "CASH_BLOCKED": "VERIFIED_AVAILABLE_CASH", "PORTFOLIO_BLOCKED": "PORTFOLIO_REVIEW"}
    return mapping.get(execution) or (remaining[0] if remaining else None)


def _transition(previous: str | None, current: str) -> str:
    if current == "DATA_BLOCKED" and previous != "DATA_BLOCKED":
        return "DATA_BLOCKED"
    if previous is None:
        return "NEW_READY" if current == "READY" else ("NEW_NEAR_TRIGGER" if current == "NEAR_TRIGGER" else "NO_MATERIAL_CHANGE")
    if OPPORTUNITY_ORDER[current] > OPPORTUNITY_ORDER.get(previous, -1):
        return "OPPORTUNITY_UPGRADE"
    if OPPORTUNITY_ORDER[current] < OPPORTUNITY_ORDER.get(previous, -1):
        return "OPPORTUNITY_DOWNGRADE"
    return "NO_MATERIAL_CHANGE"


def _ranking_key(item: dict[str, Any], registry: dict[str, Any], active: list[str]) -> tuple[Any, ...]:
    instrument = (registry.get("instruments") or {}).get(item["ticker"]) or {}
    leverage = instrument.get("leverage_factor")
    leverage_value = float(leverage) if isinstance(leverage, (int, float)) and not isinstance(leverage, bool) else 1.0
    # Ordered, non-additive tie-break: opportunity, thesis, valuation, risk, portfolio fit, lower leverage, stable universe order.
    return (
        -OPPORTUNITY_ORDER[item["opportunity_state"]],
        -{"STRONG": 2, "CONTESTED": 1}.get(item["thesis_status"], 0),
        -{"ATTRACTIVE": 2, "FAIR": 1}.get(item["valuation_status"], 0),
        -{"ACCEPTABLE": 2, "CONSTRAINED": 1}.get(item["risk_liquidity_status"], 0),
        -{"FITS": 2, "CONSTRAINED": 1}.get(item["portfolio_fit_status"], 0),
        leverage_value,
        active.index(item["ticker"]),
    )


def build_radar(universe: dict[str, Any], registry: dict[str, Any], registry_validation: dict[str, Any],
                market: dict[str, Any], events: dict[str, Any], context: dict[str, Any],
                portfolio_state: dict[str, Any], runtime: dict[str, Any], policy: dict[str, Any], *,
                generated_at: str, analysis_cutoff: str, market_session: str | None,
                latest_completed_session: str | None, provider_preflight: dict[str, Any] | None = None,
                cash_gate: dict[str, Any] | None = None, run_phase: str = "POST_MARKET") -> tuple[dict[str, Any], dict[str, Any]]:
    if run_phase != "POST_MARKET":
        raise ValueError("Tactical Radar completed-session authority requires run_phase=POST_MARKET")
    active = _active_candidates(universe)
    if active != list(ACTIVE_SYMBOLS):
        raise ValueError(f"active tactical universe must be exactly {list(ACTIVE_SYMBOLS)}, got {active}")
    session = market.get("session") or {}
    duplicate_session = bool(market_session and runtime.get("last_processed_us_session") == market_session)
    session_valid = (
        bool(market_session) and market_session == latest_completed_session
        and session.get("expected_us_session_date") == latest_completed_session
        and session.get("official_calendar_verified") is True
        and session.get("calendar_verification_status") == "verified_trading_day"
        and session.get("regular_session_complete") is True
        and session.get("us_session_date") == market_session
    )
    session_gate = "NO_NEW_SESSION" if duplicate_session else ("VALID_SESSION" if session_valid else "DATA_INCOMPLETE")

    instruments = registry.get("instruments") or {}
    candidates = universe.get("candidates") or {}
    market_rows = market.get("symbols") or {}
    candidate_context = context.get("candidates") or {}
    cash_gate = cash_gate or evaluate_cash_status(portfolio_state, reference_session=market_session,
        maximum_age_calendar_days=4, required_strategy_version=portfolio_state.get("strategy_version"))
    cash_status = str(cash_gate.get("cash_status", "UNVERIFIED"))
    provider_preflight = provider_preflight or {}
    global_failures: list[str] = []
    if session_gate == "DATA_INCOMPLETE":
        global_failures.append("OFFICIAL_COMPLETED_SESSION_FAILURE")
    approved = set(((policy.get("technical_authority") or {}).get("approved_condition_ids") or [])) | INTERNAL_CONDITION_IDS
    dispositions: list[dict[str, Any]] = []
    survivors: list[str] = []
    transitions: list[dict[str, Any]] = []
    previous_candidates = runtime.get("candidates") or {}
    registry_valid = registry_validation.get("status") == "VALIDATED"

    for symbol in active:
        instrument = instruments.get(symbol) or {}
        candidate = candidates.get(symbol) or {}
        row = market_rows.get(symbol)
        market_errors = _market_integrity(market, row, market_session)
        if session_gate == "DATA_INCOMPLETE" and "OFFICIAL_SESSION_VERIFICATION" not in [_condition_code(x) for x in market_errors]:
            market_errors.append("official latest-completed-session verification did not pass")
        market_conditions = [_condition_code(error) for error in market_errors]
        evidence = "PASS" if not market_errors and session_gate in {"VALID_SESSION", "NO_NEW_SESSION"} else "FAIL"
        identity = str(instrument.get("identity_status", "UNVERIFIED"))
        raw_context = candidate_context.get(symbol) or {}
        context_valid = _validated_context(raw_context)
        local_context = raw_context if context_valid else {}
        thesis = local_context.get("thesis_status", "UNVERIFIED")
        valuation = local_context.get("valuation_status", "UNVERIFIED")
        technical, technical_remaining = _technical_from_market(row, local_context)
        event_risk, event_effect = _event_status(events, symbol)
        risk_liquidity = local_context.get("risk_liquidity_status", "CONSTRAINED" if evidence == "PASS" else "VETO")
        portfolio_fit = local_context.get("portfolio_fit_status", "UNVERIFIED")
        supplied_conditions, condition_rejected = _sanitize_conditions(list(local_context.get("remaining_conditions") or []), approved)
        remaining: list[str] = []
        for item in market_conditions + supplied_conditions + technical_remaining:
            if item in approved and item not in remaining:
                remaining.append(item)
        if condition_rejected:
            remaining.insert(0, "UNAPPROVED_CONDITION_ID")
        if identity in IDENTITY_INCOMPLETE_VALUES and "IDENTITY_VERIFICATION" not in remaining:
            remaining.append("IDENTITY_VERIFICATION")
        if thesis == "UNVERIFIED" and "THESIS_RESEARCH" not in remaining:
            remaining.append("THESIS_RESEARCH")
        if valuation == "UNVERIFIED" and "VALUATION_REFRESH" not in remaining:
            remaining.append("VALUATION_REFRESH")
        if event_effect == "EVENT_DATA_INCOMPLETE" and "EVENT_CLEARANCE" not in remaining:
            remaining.append("EVENT_CLEARANCE")
        opportunity = _opportunity_state(identity_status=identity, evidence=evidence, thesis=thesis, valuation=valuation,
            technical=technical, event_policy_effect=event_effect, risk_liquidity=risk_liquidity,
            portfolio_fit=portfolio_fit, context_valid=context_valid, condition_rejected=condition_rejected)
        new_buy_approved = candidate.get("new_buy_approved") is True and instrument.get("new_buy_instrument_approved") is True
        material_near_trigger = bool(opportunity == "NEAR_TRIGGER" and context_valid and technical == "READY")
        crosscheck_reason = crosscheck_required(opportunity_state=opportunity,
                                                material_near_trigger=material_near_trigger)
        price_evidence = evidence_status(row, market_session, crosscheck_reason)
        if price_evidence["crosscheck_status"] == "CONFLICT":
            opportunity, execution = "DATA_BLOCKED", "DATA_BLOCKED"
            if "PRICE_CONFLICT" not in remaining:
                remaining.insert(0, "PRICE_CONFLICT")
        elif price_evidence["crosscheck_requirement"] == "REQUIRED" and price_evidence["crosscheck_status"] != "VERIFIED":
            execution = "VERIFICATION_PENDING"
            if "INDEPENDENT_COMPLETED_CLOSE" not in remaining:
                remaining.append("INDEPENDENT_COMPLETED_CLOSE")
        else:
            execution = _execution_state(opportunity, registry_valid=registry_valid, new_buy_approved=new_buy_approved,
                cash_status=cash_status, portfolio_fit=portfolio_fit)
        if not registry_valid and "POLICY_REGISTRY_CONSISTENCY" not in remaining:
            remaining.append("POLICY_REGISTRY_CONSISTENCY")
        if not new_buy_approved and "NEW_BUY_INSTRUMENT_APPROVAL" not in remaining:
            remaining.append("NEW_BUY_INSTRUMENT_APPROVAL")
        if cash_status != "VERIFIED_POSITIVE":
            if "VERIFIED_AVAILABLE_CASH" not in remaining:
                remaining.append("VERIFIED_AVAILABLE_CASH")
        if portfolio_fit in {"BLOCKED", "UNVERIFIED"} and "PORTFOLIO_REVIEW" not in remaining:
            remaining.append("PORTFOLIO_REVIEW")
        requested_trigger = local_context.get("next_review_trigger")
        next_trigger = requested_trigger if requested_trigger in approved else (remaining[0] if remaining else "NEXT_COMPLETED_US_SESSION")
        if requested_trigger is not None and requested_trigger not in approved:
            condition_rejected = True
            if "UNAPPROVED_CONDITION_ID" not in remaining:
                remaining.insert(0, "UNAPPROVED_CONDITION_ID")
            opportunity, execution, next_trigger = "DATA_BLOCKED", "DATA_BLOCKED", "UNAPPROVED_CONDITION_ID"
        disposition = {
            "ticker": symbol, "lane": _lane_for(symbol, universe), "opportunity_state": opportunity,
            "execution_state": execution, "evidence_status": evidence, "thesis_status": thesis,
            "valuation_status": valuation, "technical_status": technical, "event_risk_status": event_risk,
            "event_policy_effect": event_effect, "risk_liquidity_status": risk_liquidity,
            "portfolio_fit_status": portfolio_fit, "identity_status": identity,
            "new_buy_approval": new_buy_approved, "primary_blocker": _primary_blocker(opportunity, execution, remaining),
            "remaining_conditions": remaining, "next_review_trigger": next_trigger,
            "evidence_cutoff": analysis_cutoff, "quantity": None, "order_authority": False,
            "material_near_trigger": material_near_trigger,
            "price_evidence": price_evidence,
        }
        dispositions.append(disposition)
        if (evidence == "PASS" and identity not in IDENTITY_INCOMPLETE_VALUES and candidate.get("watchlist_approved") is True
                and thesis != "WEAK" and valuation != "STRETCHED" and technical not in {"INVALID", "UNAVAILABLE"}
                and risk_liquidity != "VETO" and portfolio_fit != "BLOCKED"):
            survivors.append(symbol)
        previous = (previous_candidates.get(symbol) or {}).get("opportunity_state")
        transition_type = "NO_MATERIAL_CHANGE" if duplicate_session else _transition(previous, opportunity)
        fingerprint = canonical_hash({key: disposition[key] for key in ("ticker", "opportunity_state", "execution_state", "primary_blocker", "remaining_conditions")})
        event_key = f"{policy.get('policy_version')}:{run_phase}:{symbol}:{opportunity}"
        delivery_id = hashlib.sha256(f"{event_key}:{market_session}:{transition_type}".encode("utf-8")).hexdigest()
        urgent = transition_type in set((policy.get("notification") or {}).get("urgent_transition_events") or [])
        delivered = delivery_id in (runtime.get("deliveries") or {})
        transitions.append({"ticker": symbol, "session": market_session or "1970-01-01", "run_phase": run_phase, "transition_type": transition_type,
            "previous_opportunity_state": previous, "opportunity_state": opportunity, "execution_state": execution,
            "event_key": event_key, "delivery_id": delivery_id, "signal_fingerprint": fingerprint,
            "notify": bool(session_gate == "VALID_SESSION" and urgent and not delivered and not duplicate_session
                           and not (execution == "VERIFICATION_PENDING" and provider_preflight.get("capability_status") == "UNAVAILABLE")),
            "order_authority": False})

    requested = set(context.get("deep_research_requested") or [])
    material = set(context.get("material_change_symbols") or []) | set(context.get("opportunity_upgrade_symbols") or [])
    eligible = [item for item in dispositions if item["ticker"] in survivors and
                (item["opportunity_state"] in {"READY", "NEAR_TRIGGER"} or item["ticker"] in requested | material)]
    eligible.sort(key=lambda item: _ranking_key(item, registry, active))
    maximum = int((policy.get("deep_research") or {}).get("maximum_candidates", 5))
    target_minimum = int((policy.get("deep_research") or {}).get("target_minimum", 3))
    shortlist = [item["ticker"] for item in eligible[:maximum]]
    deep_results = context.get("deep_research_results") or {}
    completed = [symbol for symbol in shortlist if (deep_results.get(symbol) or {}).get("status") == "VALIDATED"
                 and isinstance((deep_results.get(symbol) or {}).get("research_packet_hash"), str)]
    skipped: list[dict[str, str]] = []
    for symbol in active:
        if symbol in completed:
            continue
        if symbol in shortlist:
            skipped.append({"ticker": symbol, "reason": "DEEP_RESEARCH_PENDING_OR_UNVALIDATED"})
        else:
            state = next(item["opportunity_state"] for item in dispositions if item["ticker"] == symbol)
            skipped.append({"ticker": symbol, "reason": f"OPPORTUNITY_STATE_{state}_NOT_ELIGIBLE"})

    ranked_completed = [item for item in eligible if item["ticker"] in completed]
    ranked_completed.sort(key=lambda item: _ranking_key(item, registry, active))
    preferred = ranked_completed[0]["ticker"] if ranked_completed else None
    alternative = ranked_completed[1]["ticker"] if len(ranked_completed) > 1 else None
    preferred_execution = next((item["execution_state"] for item in dispositions if item["ticker"] == preferred), None)
    valid_rows = sum(1 for item in dispositions if item["evidence_status"] == "PASS")
    data_status = "VALIDATED" if valid_rows == len(active) else ("PARTIAL" if valid_rows else "DATA_INCOMPLETE")
    global_notifications: list[dict[str, Any]] = []
    queued = [
        item["ticker"] for item in dispositions
        if item["price_evidence"]["crosscheck_requirement"] == "REQUIRED"
        and item["price_evidence"]["crosscheck_status"] != "VERIFIED"
    ]
    if queued and provider_preflight.get("capability_status") == "UNAVAILABLE":
        affected = queued
        incident_key = f"{policy.get('policy_version')}:{run_phase}:GLOBAL:GLOBAL_INDEPENDENT_CLOSE_OUTAGE"
        incident_delivery = hashlib.sha256(f"{incident_key}:{market_session}".encode("utf-8")).hexdigest()
        delivered = incident_delivery in (runtime.get("deliveries") or {})
        global_notifications.append({
            "ticker": "GLOBAL", "run_phase": run_phase, "event_type": "GLOBAL_INDEPENDENT_CLOSE_OUTAGE",
            "affected_tickers": affected, "provider": provider_preflight.get("selected_provider"),
            "failure_type": provider_preflight.get("global_failure") or "NO_APPROVED_HEALTHY_PROVIDER",
            "last_success": provider_preflight.get("last_success"), "retry_after": provider_preflight.get("retry_after"),
            "next_review_trigger": "INDEPENDENT_COMPLETED_CLOSE_PROVIDER_RECOVERY",
            "event_key": incident_key, "delivery_id": incident_delivery,
            "notify": bool(session_gate == "VALID_SESSION" and not delivered and not duplicate_session),
            "order_authority": False,
        })
    if session_gate == "NO_NEW_SESSION":
        conclusion = "NO_NEW_SESSION"
    elif session_gate != "VALID_SESSION" or any(item != "GLOBAL_INDEPENDENT_CLOSE_OUTAGE" for item in global_failures):
        conclusion = "DATA_INCOMPLETE"
    elif preferred and preferred_execution == "ELIGIBLE_FOR_REVIEW":
        conclusion = "BUY_REVIEW"
    elif shortlist:
        conclusion = "WAIT"
    else:
        conclusion = "NO_TRADE"
    report = {"schema_version": "2.5", "run_phase": run_phase, "generated_at": generated_at, "analysis_cutoff": analysis_cutoff,
        "market_session": market_session, "session_gate": session_gate, "registry_status": registry_validation.get("status"),
        "data_status": data_status, "event_status": events.get("coverage_status", "EVENT_DATA_INCOMPLETE"),
        "active_universe": active, "candidate_dispositions": dispositions, "screen_survivors": survivors,
        "deep_research_shortlist": shortlist, "deep_research_completed": completed, "deep_research_skipped": skipped,
        "shortlist_below_target_due_to_gates": len(shortlist) < target_minimum, "transitions": transitions,
        "global_failures": list(dict.fromkeys(global_failures)), "global_notifications": global_notifications,
        "provider_health": provider_preflight, "cash_status": cash_status,
        "price_crosscheck_queue": {"crosscheck_requirement": "REQUIRED" if queued else "NOT_REQUIRED",
                                     "capability_status": (provider_preflight.get("capability_status", "PENDING") if queued else "NOT_REQUIRED"),
                                     "queued_tickers": queued, "global_failure": "GLOBAL_INDEPENDENT_CLOSE_OUTAGE" if queued and provider_preflight.get("capability_status") == "UNAVAILABLE" else None},
        "preferred_candidate": preferred, "alternative_candidate": alternative, "final_conclusion": conclusion,
        "quantity": None, "order_authority": False}

    updated = deepcopy(runtime)
    updated.setdefault("schema_version", "1.0")
    updated["policy_version"] = policy.get("policy_version")
    updated["last_run_at"] = generated_at
    updated.setdefault("candidates", {})
    updated.setdefault("deliveries", {})
    if session_gate == "VALID_SESSION":
        updated["last_processed_us_session"] = market_session
        for disposition, transition in zip(dispositions, transitions):
            previous_record = updated["candidates"].get(disposition["ticker"]) or {}
            updated["candidates"][disposition["ticker"]] = {"session": market_session,
                "opportunity_state": disposition["opportunity_state"], "execution_state": disposition["execution_state"],
                "primary_blocker": disposition["primary_blocker"], "remaining_conditions": disposition["remaining_conditions"],
                "last_deep_research_session": market_session if disposition["ticker"] in completed else previous_record.get("last_deep_research_session"),
                "signal_fingerprint": transition["signal_fingerprint"]}
            if transition["notify"]:
                updated["deliveries"][transition["delivery_id"]] = {"ticker": disposition["ticker"], "session": market_session,
                    "transition_type": transition["transition_type"], "delivered_at": generated_at}
        for notification in global_notifications:
            if notification["notify"]:
                updated["deliveries"][notification["delivery_id"]] = {"ticker": "GLOBAL", "session": market_session,
                    "run_phase": run_phase, "transition_type": notification["event_type"], "delivered_at": generated_at}
    updated.setdefault("last_processed_us_session", None)
    updated["order_authority"] = False
    return report, updated


def _within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--alert-policy", required=True, type=Path)
    parser.add_argument("--radar-policy", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session", required=True)
    parser.add_argument("--latest-completed-session", required=True)
    parser.add_argument("--provider-preflight", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--runtime-output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    outputs = root / "workspace" / "outputs"
    canonical_runtime = (root / "workspace" / "state" / "tactical_radar_runtime.json").resolve()
    canonical_portfolio = (root / "stock-strategy-system" / "portfolio_state.json").resolve()
    protected = {path.resolve() for path in (args.universe, args.registry, args.alert_policy, args.radar_policy,
                 args.market, args.events, args.context, args.portfolio_state, args.runtime)} | {canonical_portfolio}
    if args.portfolio_state.resolve() != canonical_portfolio:
        raise SystemExit("--portfolio-state must be the canonical read-only operational portfolio state")
    if args.runtime.resolve() != canonical_runtime and not _within(args.runtime, outputs):
        raise SystemExit("--runtime must be the canonical radar runtime or a workspace/outputs shadow artifact")
    for output in [args.output, args.runtime_output]:
        if output and (output.resolve() in protected or not _within(output, outputs)):
            raise SystemExit("outputs must be unique artifacts under workspace/outputs and may not alias protected inputs")
    registry = load_json(args.registry)
    alert_policy = load_json(args.alert_policy)
    registry_validation = validate_registry_consistency(registry, alert_policy, args.registry.resolve())
    runtime = load_json(args.runtime) if args.runtime.is_file() else {"schema_version": "1.0", "policy_version": "uninitialized",
        "last_processed_us_session": None, "last_run_at": None, "candidates": {}, "deliveries": {}, "order_authority": False}
    context = load_json(args.context)
    context_errors = validate_instance(context, root / "manage-us-stock-strategy" / "schemas" / "tactical-radar-context.schema.json")
    if context_errors:
        raise SystemExit("invalid tactical radar context: " + "; ".join(context_errors))
    portfolio_state = load_json(args.portfolio_state)
    if not isinstance(portfolio_state.get("available_cash_usd"), (int, float)) or isinstance(portfolio_state.get("available_cash_usd"), bool):
        raise SystemExit("canonical portfolio state has no numeric available_cash_usd")
    cash_gate = evaluate_cash_status(portfolio_state, reference_session=args.market_session,
        maximum_age_calendar_days=int(alert_policy.get("broker_snapshot_max_age_calendar_days", 4)),
        required_strategy_version=alert_policy.get("strategy_version"))
    report, updated = build_radar(load_json(args.universe), registry, registry_validation, load_json(args.market),
        load_json(args.events), context, portfolio_state, runtime, load_json(args.radar_policy),
        generated_at=args.generated_at, analysis_cutoff=args.analysis_cutoff, market_session=args.market_session,
        latest_completed_session=args.latest_completed_session,
        provider_preflight=load_json(args.provider_preflight) if args.provider_preflight else None,
        cash_gate=cash_gate, run_phase="POST_MARKET")
    report_errors = validate_instance(report, root / "manage-us-stock-strategy" / "schemas" / "tactical-radar-report.schema.json")
    runtime_errors = validate_instance(updated, root / "manage-us-stock-strategy" / "schemas" / "tactical-radar-state.schema.json")
    if report_errors or runtime_errors:
        raise SystemExit("radar output schema validation failed: " + "; ".join(report_errors + runtime_errors))
    write_json(args.output, report)
    if args.runtime_output:
        _atomic_write(args.runtime_output, updated)
    print(json.dumps({"status": report["final_conclusion"], "registry_status": report["registry_status"],
        "session_gate": report["session_gate"], "shortlist": report["deep_research_shortlist"], "order_authority": False}, indent=2))
    return 0 if report["registry_status"] == "VALIDATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
