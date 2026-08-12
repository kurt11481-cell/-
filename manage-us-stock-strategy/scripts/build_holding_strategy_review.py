#!/usr/bin/env python3
"""Build evidence-gated strategy reviews for verified positive holdings.

This module consumes deterministic alert/technical results.  It never calculates
technical indicators, infers fills, creates holdings, or writes portfolio state.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from portfolio_policy_gates import evaluate_cash_status, hard_risk_rule_audit
from validation_common import canonical_hash, load_json, validate_instance, write_json


STRATEGY_STATES = {
    "HOLD", "ADD_ON_WATCH", "ADD_REVIEW", "REDUCTION_REVIEW",
    "EXIT_REVIEW", "STRATEGY_REFRESH_REQUIRED", "DATA_BLOCKED",
}
RISK_STATES = {"NO_HARD_RISK", "HARD_RISK_WATCH", "HARD_RISK_BREACH", "POLICY_AUTHORITY_UNVERIFIED", "DATA_BLOCKED"}


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _verified_research(context: dict[str, Any]) -> bool:
    validation = context.get("validation") or {}
    packet_hash = context.get("research_packet_hash")
    return bool(
        validation.get("status") == "VALIDATED"
        and validation.get("evidence_packet_validated") is True
        and validation.get("deterministic_gate_status") == "PASS"
        and validation.get("risk_controller_status") in {"ALLOW_REVIEW", "DOWNGRADE"}
        and isinstance(packet_hash, str)
        and len(packet_hash) == 64
        and all(character in "0123456789abcdef" for character in packet_hash.lower())
    )


def _event_status(events: dict[str, Any], symbol: str) -> tuple[str, str]:
    coverage = events.get("coverage_status", "EVENT_DATA_INCOMPLETE")
    known = [item for item in events.get("events", []) if item.get("ticker") in {symbol, "GLOBAL"}]
    blocking = [item for item in known if item.get("validation_status") == "VALIDATED" and item.get("policy_effect") == "WAIT_REQUIRED"]
    if blocking:
        return "KNOWN_EVENT", "WAIT_REQUIRED"
    if known:
        return "KNOWN_EVENT", "CONTEXT_ONLY"
    if coverage == "COMPLETE":
        return "CLEAR", "NONE"
    return "EVENT_DATA_INCOMPLETE", "EVENT_DATA_INCOMPLETE"


def _valid_market_row(row: Any, market_session: str | None) -> bool:
    if not isinstance(row, dict) or not market_session:
        return False
    crosscheck = row.get("quote_crosscheck") or {}
    indicator = row.get("indicator_validation") or {}
    return bool(
        row.get("bar_date") == market_session
        and _finite(row.get("close"))
        and float(row["close"]) > 0
        and row.get("corporate_action_unresolved") is False
        and indicator.get("status") == "passed"
        and indicator.get("errors") == []
        and crosscheck.get("status") == "verified"
        and crosscheck.get("independent_of_builder") is True
        and crosscheck.get("bar_date") == market_session
    )


def _risk_candidates(result: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    return [item for item in result.get("candidates", []) if item.get("symbol") == symbol]


def _hard_risk(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in items if item.get("event_type") == "holding_max_loss_breach" and item.get("breached") is True and item.get("grade") == "D"), None)


def _timing_reduction(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in items if item.get("event_type") == "holding_timing_review" and item.get("side") == "reduce" and item.get("grade") == "B"), None)


def _plan_required(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in items if item.get("event_type") == "reduction_plan_required" and item.get("grade") == "B"), None)


def _execution_state(
    strategy_state: str,
    *,
    cash_verified: bool,
    available_cash: float | None,
    event_effect: str,
    risk_freeze: bool,
    add_policy_approved: bool,
) -> str:
    if strategy_state == "DATA_BLOCKED":
        return "DATA_BLOCKED"
    if strategy_state in {"REDUCTION_REVIEW", "EXIT_REVIEW"}:
        return "HUMAN_REVIEW_REQUIRED"
    if strategy_state == "ADD_REVIEW":
        if risk_freeze:
            return "PORTFOLIO_BLOCKED"
        if not cash_verified or available_cash is None or available_cash <= 0:
            return "CASH_BLOCKED"
        if event_effect == "WAIT_REQUIRED":
            return "POLICY_BLOCKED"
        if not add_policy_approved:
            return "POLICY_BLOCKED"
        return "ELIGIBLE_FOR_REVIEW"
    if strategy_state in {"ADD_ON_WATCH", "STRATEGY_REFRESH_REQUIRED"}:
        return "WATCH_ONLY"
    return "NOT_APPLICABLE"


def build_holding_strategies(
    portfolio_state: dict[str, Any],
    alert_policy: dict[str, Any],
    registry: dict[str, Any],
    market_snapshot: dict[str, Any],
    event_snapshot: dict[str, Any],
    holding_risk_result: dict[str, Any],
    research_context: dict[str, Any] | None,
    *,
    analysis_cutoff: str,
    market_session: str | None,
) -> list[dict[str, Any]]:
    """Return one review record for every verified positive holding."""
    holdings = portfolio_state.get("holdings") or {}
    costs = portfolio_state.get("average_cost_usd") or {}
    broker = portfolio_state.get("last_confirmed_broker_snapshot") or {}
    if not isinstance(holdings, dict):
        raise ValueError("canonical portfolio holdings must be an object")
    positive = {symbol: int(quantity) for symbol, quantity in holdings.items() if _finite(quantity) and int(quantity) > 0}
    contexts = (research_context or {}).get("holdings") or {}
    instruments = registry.get("instruments") or {}
    market_rows = market_snapshot.get("symbols") or {}
    snapshot_hash = canonical_hash(market_snapshot)
    event_hash = canonical_hash(event_snapshot)
    policy_version = str((alert_policy.get("holding_timing_rules") or {}).get("policy_version") or alert_policy.get("strategy_version") or "UNVERSIONED")
    strategy_version = str(portfolio_state.get("strategy_version") or "UNVERSIONED")
    risk_freeze = bool(holding_risk_result.get("risk_freeze_active"))
    globally_blocked = holding_risk_result.get("state") in {"STATE_MISMATCH", "DATA_INCOMPLETE"}
    cash_gate = evaluate_cash_status(portfolio_state, reference_session=market_session,
        maximum_age_calendar_days=int(alert_policy.get("broker_snapshot_max_age_calendar_days", 4)),
        required_strategy_version=alert_policy.get("strategy_version"))
    cash_verified = cash_gate["cash_status"] == "VERIFIED_POSITIVE"
    available_cash = cash_gate["verified_available_cash_usd"] if cash_verified else None
    records: list[dict[str, Any]] = []

    for symbol, shares in sorted(positive.items()):
        instrument = instruments.get(symbol) or {}
        identity_verified = instrument.get("identity_status") not in {None, "UNVERIFIED", "user_supplied_pending_primary_verification", "identity_incomplete"}
        held_identity = ((alert_policy.get("decision_harness") or {}).get("instrument_registry") or {}).get(symbol) or {}
        holding_verified = bool(broker.get("verified") and broker.get("holdings_complete") and identity_verified and held_identity.get("holding_identity_verified") is True)
        if not holding_verified:
            raise ValueError(f"{symbol}: positive holding is not verified by canonical state and registry")

        row = market_rows.get(symbol)
        row_valid = _valid_market_row(row, market_session)
        items = _risk_candidates(holding_risk_result, symbol)
        hard = _hard_risk(items)
        timing = _timing_reduction(items)
        plan_required = _plan_required(items)
        context = contexts.get(symbol) or {}
        research_valid = _verified_research(context)
        event_status, event_effect = _event_status(event_snapshot, symbol)
        thesis = context.get("thesis_status", "UNVERIFIED") if research_valid else "STALE"
        valuation = context.get("valuation_status", "UNVERIFIED") if research_valid else "STALE"
        technical = context.get("technical_status", "UNAVAILABLE") if research_valid else ("WATCH" if row_valid else "UNAVAILABLE")
        risk = context.get("risk_status", "UNVERIFIED") if research_valid else "UNVERIFIED"
        portfolio_fit = context.get("portfolio_fit_status", "UNVERIFIED") if research_valid else "UNVERIFIED"
        strategy_signal = context.get("strategy_signal", "NONE") if research_valid else "NONE"
        claim_ids = list(context.get("claim_ids") or []) if research_valid else []
        primary_reason = "A fresh validated holding thesis and valuation review is required."
        remaining = list(context.get("remaining_conditions") or []) if research_valid else ["VALIDATED_HOLDING_RESEARCH_REFRESH"]
        add_conditions = list(context.get("add_conditions") or []) if research_valid else []
        reduce_conditions = list(context.get("reduce_conditions") or []) if research_valid else []
        strongest_counter = context.get("strongest_counter_case") if research_valid else None
        invalidation = context.get("invalidation") if research_valid else None
        next_trigger = context.get("next_review_trigger") if research_valid else "VALIDATED_HOLDING_RESEARCH_REFRESH"
        strategy_state = "STRATEGY_REFRESH_REQUIRED"
        risk_state = "NO_HARD_RISK"
        quantity: int | None = None
        quantity_authority = "none"
        policy_rule_id = tranche_id = trigger_path = None

        rule_audit = hard_risk_rule_audit(alert_policy, symbol)
        primary_close_status = "VERIFIED" if isinstance(row, dict) and row.get("bar_date") == market_session and _finite(row.get("close")) and row.get("corporate_action_unresolved") is False else "UNAVAILABLE"
        crosscheck = (row or {}).get("quote_crosscheck") if isinstance(row, dict) else {}
        crosscheck = crosscheck or {}
        independent_close_status = "VERIFIED" if crosscheck.get("status") == "verified" and crosscheck.get("independent_of_builder") is True and crosscheck.get("bar_date") == market_session else "PENDING"
        price_verification_status = "VERIFIED" if primary_close_status == "VERIFIED" and independent_close_status == "VERIFIED" else ("PRIMARY_VERIFIED_INDEPENDENT_PENDING" if primary_close_status == "VERIFIED" else "DATA_BLOCKED")

        if hard is not None:
            risk = "HARD_RISK"
            action = rule_audit.get("action_on_breach")
            authority = rule_audit.get("policy_authority_status")
            if authority == "VERIFIED" and action == "exit_review":
                risk_state, strategy_state = "HARD_RISK_BREACH", "EXIT_REVIEW"
                primary_reason = "A provenance-verified maximum-loss boundary was breached and its approved action maps to exit review."
            elif authority == "VERIFIED" and action == "reduction_review":
                risk_state, strategy_state = "HARD_RISK_BREACH", "REDUCTION_REVIEW"
                primary_reason = "A provenance-verified maximum-loss boundary was breached and its approved action maps to reduction review."
            else:
                risk_state, strategy_state = "POLICY_AUTHORITY_UNVERIFIED", "STRATEGY_REFRESH_REQUIRED"
                primary_reason = "The completed close reached the configured maximum-loss boundary, but action authority is incomplete; strategy refresh and human reconciliation are required."
            remaining = []
            if authority != "VERIFIED":
                remaining.append("HARD_RISK_POLICY_ACTION_AUTHORITY_RECONCILIATION")
            if independent_close_status != "VERIFIED":
                remaining.append("INDEPENDENT_COMPLETED_CLOSE")
            reduce_conditions = ["HUMAN_REVIEW_OF_HARD_RISK_EVIDENCE"]
            next_trigger = "IMMEDIATE_HUMAN_REVIEW_BEFORE_NEXT_SESSION"
            claim_ids = list(dict.fromkeys(claim_ids + [str(hard.get("event_key"))]))
        elif globally_blocked:
            strategy_state = "DATA_BLOCKED"
            risk_state = "DATA_BLOCKED"
            primary_reason = "The deterministic holding-risk engine rejected the canonical state or held-position data."
            remaining = ["RESTORE_VALIDATED_HOLDING_RISK_INPUTS"]
            next_trigger = "NEXT_VALIDATED_COMPLETED_SESSION"
        elif timing is not None:
            strategy_state = "REDUCTION_REVIEW"
            risk = "CONSTRAINED"
            primary_reason = "An approved deterministic holding-timing reduction tranche is active."
            quantity_value = timing.get("quantity")
            if isinstance(quantity_value, int) and quantity_value > 0 and timing.get("tranche_id") and timing.get("trigger_path"):
                quantity = quantity_value
                quantity_authority = "deterministic_existing_policy"
                policy_rule_id = f"holding_timing_rules:{policy_version}"
                tranche_id = str(timing["tranche_id"])
                trigger_path = str(timing["trigger_path"])
            remaining = list(timing.get("missing_conditions") or [])
            next_trigger = "HUMAN_REVIEW_OF_DETERMINISTIC_TRANCHE"
            claim_ids = list(dict.fromkeys(claim_ids + [str(timing.get("event_key"))]))
        elif plan_required is not None:
            strategy_state = "REDUCTION_REVIEW"
            risk = "CONSTRAINED"
            primary_reason = "The approved default reduction direction lacks an exact approved reduction plan."
            remaining = list(plan_required.get("missing_conditions") or [])
            next_trigger = "USER_APPROVES_OR_REJECTS_REDUCTION_PLAN"
        elif not row_valid:
            strategy_state = "DATA_BLOCKED"
            technical = "UNAVAILABLE"
            primary_reason = "Validated completed-session price, indicators, and independent close cross-check are unavailable."
            remaining = ["VALIDATED_COMPLETED_SESSION_MARKET_DATA"]
            next_trigger = "NEXT_VALIDATED_COMPLETED_SESSION"
        elif not research_valid:
            strategy_state = "STRATEGY_REFRESH_REQUIRED"
        elif thesis == "INVALIDATED" or risk == "VETO" or strategy_signal == "EXIT_CANDIDATE":
            strategy_state = "EXIT_REVIEW"
            primary_reason = "Validated research identifies thesis invalidation or severe risk requiring full-exit review."
            next_trigger = "IMMEDIATE_HUMAN_REVIEW"
        elif strategy_signal == "REDUCE_CANDIDATE" and (thesis == "CONTESTED" or valuation == "STRETCHED" or technical in {"DETERIORATING", "INVALID"} or risk == "CONSTRAINED" or portfolio_fit in {"CONSTRAINED", "BLOCKED"}):
            strategy_state = "REDUCTION_REVIEW"
            primary_reason = "Validated multi-factor evidence supports a partial-reduction review; no quantity is inferred."
        elif strategy_signal == "ADD_CANDIDATE" and thesis == "VALID" and valuation in {"ATTRACTIVE", "FAIR"} and risk == "ACCEPTABLE" and portfolio_fit == "FITS":
            if technical == "READY" and event_effect != "WAIT_REQUIRED":
                strategy_state = "ADD_REVIEW"
                primary_reason = "Validated thesis, valuation, technical entry, event, risk, and portfolio-fit gates support an add review."
            else:
                strategy_state = "ADD_ON_WATCH"
                primary_reason = "The holding thesis remains valid, but an observable entry or event condition is still pending."
        else:
            strategy_state = "HOLD"
            primary_reason = context.get("primary_reason") or "Validated evidence does not currently justify a portfolio-changing review."

        if strategy_state not in STRATEGY_STATES:
            raise ValueError(f"{symbol}: invalid strategy state {strategy_state}")
        if risk_state not in RISK_STATES:
            raise ValueError(f"{symbol}: invalid holding risk state {risk_state}")
        # Current operational policy detects add setups only as watch/review context;
        # it does not authorize an exact add risk budget or quantity.  Research
        # context is intentionally unable to upgrade this deterministic gate.
        add_policy_approved = False
        execution = _execution_state(strategy_state, cash_verified=cash_verified, available_cash=available_cash,
            event_effect=event_effect, risk_freeze=risk_freeze, add_policy_approved=add_policy_approved)
        if hard is not None and strategy_state == "STRATEGY_REFRESH_REQUIRED":
            execution = "HUMAN_REVIEW_REQUIRED"
        if strategy_state == "ADD_REVIEW" and execution == "CASH_BLOCKED" and "VERIFIED_AVAILABLE_CASH" not in remaining:
            remaining.append("VERIFIED_AVAILABLE_CASH")
        if strategy_state == "ADD_REVIEW" and not add_policy_approved and "EXISTING_ADD_POLICY_APPROVAL" not in remaining:
            remaining.append("EXISTING_ADD_POLICY_APPROVAL")
        if event_effect == "EVENT_DATA_INCOMPLETE" and "EVENT_DATA_INCOMPLETE" not in remaining:
            remaining.append("EVENT_DATA_INCOMPLETE")

        average_cost = float(costs[symbol]) if _finite(costs.get(symbol)) else None
        market_value = round(shares * float(row["close"]), 8) if row_valid else None
        record = {
            "schema_version": "2.4", "run_phase": "POST_MARKET", "ticker": symbol, "holding_verified": True,
            "current_shares": shares, "average_cost_usd": average_cost, "market_value_usd": market_value,
            "analysis_cutoff": analysis_cutoff, "market_session": market_session,
            "strategy_state": strategy_state, "execution_state": execution,
            "thesis_status": thesis, "valuation_status": valuation, "technical_status": technical,
            "event_risk_status": event_status, "risk_status": risk, "holding_risk_state": risk_state,
            "portfolio_fit_status": portfolio_fit,
            "primary_reason": primary_reason, "claim_ids": [item for item in claim_ids if item and item != "None"],
            "strongest_counter_case": strongest_counter, "remaining_conditions": list(dict.fromkeys(remaining)),
            "add_conditions": list(dict.fromkeys(add_conditions)), "reduce_conditions": list(dict.fromkeys(reduce_conditions)),
            "invalidation": invalidation, "next_review_trigger": str(next_trigger or "NEXT_COMPLETED_US_SESSION"),
            "quantity": quantity, "quantity_authority": quantity_authority,
            "policy_rule_id": policy_rule_id or rule_audit.get("rule_id"),
            "policy_approval_status": rule_audit.get("approval_status", "UNVERIFIED"),
            "policy_authority_status": rule_audit.get("policy_authority_status", "UNVERIFIED"),
            "action_on_breach": rule_audit.get("action_on_breach"),
            "primary_close_status": primary_close_status,
            "independent_close_status": independent_close_status,
            "price_verification_status": price_verification_status,
            "tranche_id": tranche_id, "trigger_path": trigger_path,
            "research_packet_hash": context.get("research_packet_hash") if research_valid else None,
            "snapshot_hash": snapshot_hash, "event_snapshot_hash": event_hash,
            "policy_version": policy_version, "strategy_version": strategy_version,
            "hard_risk_active": hard is not None, "order_authority": False,
        }
        records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--alert-policy", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--holding-risk", required=True, type=Path)
    parser.add_argument("--research-context", type=Path)
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    canonical_state = (root / "stock-strategy-system" / "portfolio_state.json").resolve()
    outputs = (root / "workspace" / "outputs").resolve()
    if args.portfolio_state.resolve() != canonical_state:
        raise SystemExit("--portfolio-state must be the canonical read-only operational state")
    try:
        args.output.resolve().relative_to(outputs)
    except ValueError as exc:
        raise SystemExit("--output must be under workspace/outputs") from exc
    protected = {path.resolve() for path in (args.portfolio_state, args.alert_policy, args.registry,
        args.market, args.events, args.holding_risk) if path}
    if args.research_context:
        protected.add(args.research_context.resolve())
    if args.output.resolve() in protected:
        raise SystemExit("output may not alias any input or canonical portfolio state")
    context = load_json(args.research_context) if args.research_context else {"holdings": {}}
    records = build_holding_strategies(load_json(args.portfolio_state), load_json(args.alert_policy), load_json(args.registry),
        load_json(args.market), load_json(args.events), load_json(args.holding_risk), context,
        analysis_cutoff=args.analysis_cutoff, market_session=args.market_session)
    schema = root / "manage-us-stock-strategy" / "schemas" / "holding-strategy.schema.json"
    errors = [error for record in records for error in validate_instance(record, schema)]
    if errors:
        raise SystemExit("holding strategy schema validation failed: " + "; ".join(errors))
    write_json(args.output, {"schema_version": "2.4", "run_phase": "POST_MARKET", "analysis_cutoff": args.analysis_cutoff,
        "market_session": args.market_session, "holding_strategies": records, "order_authority": False})
    print(json.dumps({"status": "PASS", "holdings": len(records), "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
