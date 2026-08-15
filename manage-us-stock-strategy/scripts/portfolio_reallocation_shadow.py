#!/usr/bin/env python3
"""Deterministic holding-decision and capital-reallocation Shadow engine.

This module evaluates portfolio decisions without creating execution authority.
Expected proceeds and hypothetical quantities remain Shadow-only and never
become broker cash, portfolio facts, order intents, or orders.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, load_json, parse_datetime, validate_instance


EVENT_STATES = {
    "EVENT_COMPLETE",
    "EVENT_PARTIAL_NONBLOCKING",
    "EVENT_PARTIAL_BUY_BLOCKING",
    "EVENT_STALE",
    "EVENT_REFRESH_FAILED",
    "EVENT_SOURCE_UNAVAILABLE",
}
EVENT_ACTIONS = {"NEW_BUY", "ADD", "HOLD", "TRIM", "EXIT"}
HOLDING_ACTIONS = {
    "HOLD_CORE", "HOLD_TIGHTEN_STOP", "HOLD_REVIEW_REQUIRED", "ADD_REVIEW",
    "TRIM_PROFIT", "TRIM_VALUATION", "TRIM_TECHNICAL",
    "TRIM_CONCENTRATION", "TRIM_RISK", "EXIT_THESIS",
    "EXIT_HARD_STOP", "ROTATE_REVIEW",
}
MATERIAL_CATEGORY_STATES = {
    "VERIFIED", "NOT_YET_ANNOUNCED", "NO_NEW_DISCLOSURE_FOUND",
    "NO_NEW_DISCLOSURE_FOUND_AS_OF_CUTOFF",
    "SOURCE_UNAVAILABLE", "REVIEW_REQUIRED",
}
VALID_EVENT_REFRESH_STATUSES = {
    "POST_CLOSE_EVENT_REFRESH_VALIDATED",
    "POST_CLOSE_EVENT_RESOLUTION_COMPLETED",
}
VALID_EVENT_RESOLUTION_STATUSES = {
    "RESOLVED", "RESOLVED_WITH_NONBLOCKING_GAPS",
    "UNRESOLVED_ACTION_BLOCKING", "UNRESOLVED_NONBLOCKING",
}
HOLDING_COMPILE_MODES = {"FULL", "DEGRADED_EVENT_SCOPED", "FAIL_CLOSED", "NOT_RUN"}
TEN_AXES = (
    "PRICE_AUTHORITY_STATUS", "VOLUME_AUTHORITY_STATUS",
    "TECHNICAL_CONDITION_STATUS", "EVENT_READINESS_STATUS",
    "BROKER_VISIBILITY_STATUS", "EXECUTION_AUTHORITY_STATUS",
    "RISK_AUTHORIZATION_STATUS", "ORDER_STATE",
    "CAPITAL_AVAILABILITY_STATUS", "PORTFOLIO_REALLOCATION_STATUS",
)
OPTIMIZER_INPUTS = (
    "expected_upside", "downside_risk", "risk_reward", "valuation",
    "technical_setup", "event_readiness", "liquidity", "volatility",
    "position_concentration", "sector_concentration", "correlation",
    "cash_buffer", "transaction_cost_estimates",
)


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_output_path(output: Path, *, repository_root: Path, protected: list[Path]) -> None:
    outputs_root = repository_root / "workspace" / "outputs"
    resolved = output.resolve()
    if not _within(resolved, outputs_root):
        raise ValueError("OUTPUT_MUST_BE_UNDER_WORKSPACE_OUTPUTS")
    if resolved in {path.resolve() for path in protected}:
        raise ValueError("OUTPUT_MUST_NOT_ALIAS_INPUT_OR_PROTECTED_STATE")


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    matrix = policy.get("event_actionability") or {}
    if set(matrix) != EVENT_STATES or any(set(matrix.get(state) or {}) != EVENT_ACTIONS for state in EVENT_STATES):
        errors.append("EVENT_ACTIONABILITY_MATRIX_INCOMPLETE")
    profit = policy.get("profit_protection") or {}
    if profit.get("fixed_profit_auto_sell_prohibited") is not True:
        errors.append("FIXED_PROFIT_AUTO_SELL_NOT_PROHIBITED")
    if profit.get("upstream_policy_result_required") is not True:
        errors.append("UPSTREAM_PROFIT_POLICY_RESULT_NOT_REQUIRED")
    if policy.get("expected_sale_proceeds_status") != "SHADOW_ONLY":
        errors.append("EXPECTED_PROCEEDS_POLICY_NOT_SHADOW_ONLY")
    if policy.get("portfolio_mutation_authority") is not False:
        errors.append("PORTFOLIO_MUTATION_AUTHORITY_VIOLATION")
    if policy.get("quantity_authority") != "none" or policy.get("execution_quantity") is not None:
        errors.append("QUANTITY_AUTHORITY_VIOLATION")
    if policy.get("order_authority") is not False:
        errors.append("ORDER_AUTHORITY_VIOLATION")
    return errors


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _iso(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("TIMESTAMP_TIMEZONE_REQUIRED")
    return parsed


def validate_post_close_ordering(*, decision_as_of: str, market_data_cutoff: str,
                                 event_cutoff: str, broker_cutoff: str,
                                 candidate_cutoff: str | None = None,
                                 evidence_timestamps: list[str] | None = None,
                                  completed_bar_finalization_status: str = "KIWOOM_COMPLETED_BAR_FINALIZED",
                                  event_refresh_status: str = "POST_CLOSE_EVENT_REFRESH_VALIDATED",
                                  event_resolution_status: str = "RESOLVED",
                                  holding_compile_mode: str = "FULL",
                                  event_bundle_hash: str | None = None) -> list[str]:
    """Enforce completed-bar -> event-refresh -> strategy decision ordering."""
    errors: list[str] = []
    if completed_bar_finalization_status != "KIWOOM_COMPLETED_BAR_FINALIZED":
        errors.append("COMPLETED_BAR_NOT_FINALIZED")
    if event_refresh_status not in VALID_EVENT_REFRESH_STATUSES:
        errors.append("POST_CLOSE_EVENT_REFRESH_NOT_VALIDATED")
    if event_resolution_status not in VALID_EVENT_RESOLUTION_STATUSES:
        errors.append("EVENT_RESOLUTION_NOT_ACTIONABLE")
    if holding_compile_mode not in {"FULL", "DEGRADED_EVENT_SCOPED"}:
        errors.append("HOLDING_COMPILE_MODE_NOT_ACTIONABLE")
    if event_resolution_status == "RESOLVED" and holding_compile_mode != "FULL":
        errors.append("RESOLVED_EVENT_REQUIRES_FULL_COMPILE")
    if event_resolution_status != "RESOLVED" and holding_compile_mode != "DEGRADED_EVENT_SCOPED":
        errors.append("UNRESOLVED_EVENT_REQUIRES_DEGRADED_COMPILE")
    if not isinstance(event_bundle_hash, str) or len(event_bundle_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in event_bundle_hash):
        errors.append("EVENT_BUNDLE_HASH_INVALID")
    try:
        decision = _iso(decision_as_of)
        market = _iso(market_data_cutoff)
        event = _iso(event_cutoff)
        broker = _iso(broker_cutoff)
        candidate = _iso(candidate_cutoff) if candidate_cutoff else None
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    if event < market:
        errors.append("EVENT_CUTOFF_BEFORE_STRATEGY_CUTOFF")
    for label, value in (("MARKET_DATA", market), ("EVENT", event), ("BROKER", broker),
                         ("CANDIDATE", candidate)):
        if value is not None and value > decision:
            errors.append(f"{label}_CUTOFF_AFTER_DECISION_AS_OF")
    for raw in evidence_timestamps or []:
        try:
            if _iso(raw) > decision:
                errors.append("LOOK_AHEAD_EVIDENCE_REJECTED")
        except (TypeError, ValueError):
            errors.append("EVIDENCE_TIMESTAMP_INVALID")
    return list(dict.fromkeys(errors))


def normalize_material_categories(categories: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    allowed_categories = set(policy.get("material_event_categories") or [])
    normalized: dict[str, str] = {}
    errors: list[str] = []
    for category, state in categories.items():
        if category not in allowed_categories:
            errors.append(f"UNAPPROVED_EVENT_CATEGORY:{category}")
            continue
        if state not in MATERIAL_CATEGORY_STATES:
            errors.append(f"INVALID_EVENT_CATEGORY_STATE:{category}")
            continue
        normalized[category] = state
    return {"categories": normalized, "errors": errors, "valid": not errors}


def evaluate_event_actionability(event_state: str, action: str, policy: dict[str, Any], *,
                                 hard_risk_exit: bool = False,
                                 thesis_invalidation_exit: bool = False) -> dict[str, Any]:
    if event_state not in EVENT_STATES:
        raise ValueError(f"INVALID_EVENT_STATE:{event_state}")
    if action not in EVENT_ACTIONS:
        raise ValueError(f"INVALID_EVENT_ACTION:{action}")
    configured = ((policy.get("event_actionability") or {}).get(event_state) or {}).get(action)
    if configured is None:
        raise ValueError(f"EVENT_MATRIX_POLICY_MISSING:{event_state}:{action}")
    override = action == "EXIT" and (hard_risk_exit or thesis_invalidation_exit)
    effective = "ALLOWED_RISK_REDUCTION_OVERRIDE" if override else configured
    allowed = effective in {
        "ALLOWED", "ALLOWED_WITH_CAUTION", "ALLOWED_RISK_REDUCTION",
        "ALLOWED_RISK_REDUCTION_OVERRIDE",
    }
    if effective == "ALLOWED_IF_HARD_RISK_OR_THESIS_INVALIDATING" and not override:
        allowed = False
    return {
        "event_state": event_state,
        "action": action,
        "decision": effective,
        "allowed": allowed,
        "hard_risk_override": bool(hard_risk_exit),
        "thesis_invalidation_override": bool(thesis_invalidation_exit),
        "order_authority": False,
    }


def _case(status: str, reasons: list[str], *, proposed_action: str) -> dict[str, Any]:
    return {
        "status": status,
        "proposed_action": proposed_action,
        "reason_codes": list(dict.fromkeys(reasons)),
    }


def _event_checks(event_state: str, policy: dict[str, Any], *, hard_exit: bool,
                  thesis_exit: bool) -> dict[str, dict[str, Any]]:
    return {
        action: evaluate_event_actionability(
            event_state, action, policy,
            hard_risk_exit=hard_exit,
            thesis_invalidation_exit=thesis_exit,
        )
        for action in EVENT_ACTIONS
    }


def evaluate_holding_decision(context: dict[str, Any], policy: dict[str, Any], *,
                              validation_mode: str = "LIVE_READ_ONLY",
                              holding_compile_mode: str = "FULL",
                              event_resolution_status: str = "RESOLVED") -> dict[str, Any]:
    ticker = str(context["ticker"])
    shares = context.get("current_broker_holding")
    average_cost = context.get("current_average_cost")
    price = context.get("current_canonical_price")
    if not isinstance(shares, int) or isinstance(shares, bool) or shares <= 0:
        raise ValueError(f"{ticker}:VERIFIED_POSITIVE_HOLDING_REQUIRED")
    if not _finite(average_cost) or float(average_cost) <= 0:
        raise ValueError(f"{ticker}:VERIFIED_AVERAGE_COST_REQUIRED")
    if not _finite(price) or float(price) <= 0:
        raise ValueError(f"{ticker}:VALID_CANONICAL_PRICE_REQUIRED")
    event_state = str(context.get("event_readiness_status"))
    hard_exit = context.get("hard_risk_status") == "BREACH" and context.get("hard_risk_exit_authorized") is True
    thesis_exit = (
        context.get("thesis_status") == "INVALIDATED"
        and context.get("thesis_invalidation_validated") is True
        and context.get("thesis_invalidation_event_verified") is True
    )
    event_checks = _event_checks(event_state, policy, hard_exit=hard_exit, thesis_exit=thesis_exit)

    exit_reasons: list[str] = []
    exit_action: str | None = None
    if hard_exit:
        exit_action, exit_reasons = "EXIT_HARD_STOP", ["HARD_STOP_EXIT", "POLICY_ACTION_AUTHORITY_VERIFIED"]
    elif thesis_exit:
        exit_action, exit_reasons = "EXIT_THESIS", ["THESIS_INVALIDATION_EXIT", "THESIS_INVALIDATION_VALIDATED"]
    elif context.get("hard_risk_status") == "BREACH":
        exit_reasons = ["HARD_RISK_BREACH_ACTION_AUTHORITY_UNVERIFIED"]
    exit_case = _case("PASS" if exit_action else ("REVIEW_REQUIRED" if exit_reasons else "NOT_MET"),
                      exit_reasons or ["NO_VALIDATED_EXIT_TRIGGER"], proposed_action=exit_action or "EXIT_THESIS")

    trim_action: str | None = None
    trim_reasons: list[str] = []
    trim_inputs = (
        ("TRIM_RISK", "risk_trim_status", "TRIGGERED", "RISK_REDUCTION_TRIGGER"),
        ("TRIM_CONCENTRATION", "concentration_trim_status", "TRIGGERED", "CONCENTRATION_LIMIT_TRIGGER"),
        ("TRIM_TECHNICAL", "technical_trim_status", "TRIGGERED", "TECHNICAL_DETERIORATION_TRIGGER"),
        ("TRIM_VALUATION", "valuation_trim_status", "TRIGGERED", "VALUATION_REVIEW_TRIGGER"),
        ("TRIM_PROFIT", "profit_protection_policy_result", "TRIGGERED", "MULTIFACTOR_PROFIT_PROTECTION_TRIGGER"),
    )
    for action, key, expected, reason in trim_inputs:
        if context.get(key) == expected:
            trim_action, trim_reasons = action, [reason]
            break
    if context.get("time_stop_status") == "TRIGGERED" and trim_action is None:
        trim_action, trim_reasons = "TRIM_RISK", ["TIME_STOP_TRIGGER"]
    trim_case = _case("PASS" if trim_action else "NOT_MET",
                      trim_reasons or ["NO_VALIDATED_TRIM_TRIGGER"], proposed_action=trim_action or "TRIM_RISK")

    add_reasons: list[str] = []
    add_required = {
        "THESIS_VALID": context.get("thesis_status") == "VALID",
        "VALUATION_SUPPORTS_ADD": context.get("valuation_add_status") == "SUPPORTED",
        "TECHNICAL_ADD_READY": context.get("technical_add_status") == "READY",
        "PORTFOLIO_FIT": context.get("portfolio_fit_status") == "FITS",
        "ADD_REVIEW_REQUESTED": context.get("add_review_requested") is True,
    }
    add_reasons.extend(key for key, passed in add_required.items() if not passed)
    technical_scope = context.get("technical_condition_decision_class")
    technical_status = context.get("technical_condition_status")
    if ticker == "MVLL" and technical_status == "RVOL20_NOT_MET":
        if technical_scope != "EMA10_RECLAIM_RVOL20":
            raise ValueError("MVLL_RVOL20_SCOPE_UNVERIFIED")
        add_reasons.append("EMA10_RECLAIM_RVOL20_CONDITION_NOT_MET")
    if not event_checks["ADD"]["allowed"]:
        add_reasons.append("EVENT_READINESS_ADD_BLOCKED")
    add_case = _case("PASS" if not add_reasons else "BLOCKED", add_reasons or ["ADD_GATES_PASSED"],
                     proposed_action="ADD_REVIEW")

    hold_reasons: list[str] = []
    hold_valid = context.get("thesis_status") in {"VALID", "CONTESTED"} and not hard_exit and not thesis_exit
    if not hold_valid:
        hold_reasons.append("VALID_HOLD_THESIS_REQUIRED")
    hold_event = event_checks["HOLD"]
    hold_review_required = hold_event["decision"] == "REVIEW_REQUIRED"
    if hold_review_required:
        hold_reasons.append("EVENT_REFRESH_REQUIRED_FOR_HOLD_CONFIDENCE")
    strong_profit_hold = bool(
        context.get("unrealized_return_status") == "LARGE_PROFIT"
        and context.get("trend_status") == "STRONG"
        and context.get("volume_health_status") == "HEALTHY"
        and context.get("profit_protection_policy_result") != "TRIGGERED"
    )
    if hold_review_required:
        hold_action = "HOLD_REVIEW_REQUIRED"
    else:
        hold_action = "HOLD_TIGHTEN_STOP" if strong_profit_hold or hold_reasons else "HOLD_CORE"
    hold_case = _case("PASS" if hold_valid and not hold_review_required else "REVIEW_REQUIRED",
                      hold_reasons or (["STRONG_PROFIT_TREND_INTACT"] if strong_profit_hold else ["HOLD_CASE_VALIDATED"]),
                      proposed_action=hold_action)

    rotate = context.get("opportunity_cost_status") == "ROTATION_REVIEW"
    selected: str
    if exit_action:
        selected = exit_action
    elif trim_action:
        selected = trim_action
    elif rotate:
        selected = "ROTATE_REVIEW"
    elif add_case["status"] == "PASS":
        selected = "ADD_REVIEW"
    else:
        selected = hold_action
    if selected not in HOLDING_ACTIONS:
        raise ValueError(f"{ticker}:INVALID_SELECTED_ACTION:{selected}")

    cases = {"ADD_CASE": add_case, "HOLD_CASE": hold_case, "TRIM_CASE": trim_case, "EXIT_CASE": exit_case}
    rejected = [
        {"case": name, "status": value["status"], "proposed_action": value["proposed_action"],
         "reason_codes": value["reason_codes"]}
        for name, value in cases.items() if value["proposed_action"] != selected
    ]
    unrealized = float(price) / float(average_cost) - 1.0
    ratio = context.get("hypothetical_trim_ratio")
    ratio_source = context.get("hypothetical_trim_ratio_source")
    if selected.startswith("EXIT_"):
        ratio = 1.0
        ratio_source = "ACTION_TAXONOMY_FULL_EXIT_SHADOW"
    policy_ratio = (policy.get("shadow_sale_ratios") or {}).get(selected)
    ratio_source_valid = (
        ratio_source == "ACTION_TAXONOMY_FULL_EXIT_SHADOW"
        or (ratio_source == "EXPLICIT_TEST_SCENARIO" and validation_mode == "TEST_ONLY")
        or (ratio_source == "APPROVED_POLICY" and _finite(policy_ratio) and _finite(ratio)
            and float(policy_ratio) == float(ratio))
    )
    ratio_valid = (
        selected.startswith(("TRIM_", "EXIT_")) and _finite(ratio)
        and 0 < float(ratio) <= 1
        and ratio_source_valid
    )
    hypothetical_quantity = min(shares, math.floor(shares * float(ratio))) if ratio_valid else None
    if ratio_valid and hypothetical_quantity == 0:
        hypothetical_quantity = 1
    expected = float(price) * hypothetical_quantity if hypothetical_quantity else 0.0

    capital_status = str(context.get("capital_availability_status") or "UNVERIFIED")
    axes = {
        "PRICE_AUTHORITY_STATUS": str(context.get("price_authority_status") or "UNVERIFIED"),
        "VOLUME_AUTHORITY_STATUS": str(context.get("volume_authority_status") or "UNVERIFIED"),
        "TECHNICAL_CONDITION_STATUS": str(context.get("technical_condition_status") or "UNVERIFIED"),
        "EVENT_READINESS_STATUS": event_state,
        "BROKER_VISIBILITY_STATUS": str(context.get("broker_visibility_status") or "UNKNOWN"),
        "EXECUTION_AUTHORITY_STATUS": "NONE",
        "RISK_AUTHORIZATION_STATUS": "SHADOW_REVIEW_ONLY",
        "ORDER_STATE": "NOT_CREATED",
        "CAPITAL_AVAILABILITY_STATUS": capital_status,
        "PORTFOLIO_REALLOCATION_STATUS": "SHADOW_REVIEW_PENDING",
    }
    return {
        "ticker": ticker,
        "current_broker_holding": shares,
        "current_average_cost": float(average_cost),
        "current_canonical_price": float(price),
        "unrealized_pl_fraction": unrealized,
        **cases,
        "selected_holding_action": selected,
        "selected_reason_codes": next(
            (value["reason_codes"] for value in cases.values() if value["proposed_action"] == selected),
            ["OPPORTUNITY_COST_REBALANCE"] if selected == "ROTATE_REVIEW" else [],
        ),
        "rejected_alternative_cases": rejected,
        "event_actionability": event_checks,
        "event_resolution_status": event_resolution_status,
        "holding_compile_mode": holding_compile_mode,
        "decision_mode": validation_mode,
        "technical_condition": axes["TECHNICAL_CONDITION_STATUS"],
        "valuation_condition": str(context.get("valuation_condition") or "UNCLASSIFIED"),
        "hypothetical_trim_ratio": float(ratio) if ratio_valid else None,
        "hypothetical_sell_quantity": hypothetical_quantity,
        "expected_sale_proceeds_usd": expected,
        "expected_sale_proceeds_status": "SHADOW_ONLY",
        "shadow_ratio_status": "VALIDATED_SHADOW_RATIO" if ratio_valid else "SHADOW_RATIO_NOT_CONFIGURED",
        "state_axes": axes,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def _portfolio_risk(positions: list[dict[str, Any]], cash_usd: float) -> dict[str, Any]:
    values = [float(row["market_value_usd"]) for row in positions if _finite(row.get("market_value_usd")) and float(row["market_value_usd"]) >= 0]
    total = sum(values) + max(0.0, float(cash_usd))
    weights = [value / total for value in values] if total > 0 else []
    effective = 0.0
    for row in positions:
        value = float(row.get("market_value_usd") or 0.0)
        multiplier = row.get("effective_exposure_multiplier", 1.0)
        multiplier = float(multiplier) if _finite(multiplier) and float(multiplier) >= 0 else 1.0
        effective += multiplier * (value / total if total > 0 else 0.0)
    return {
        "total_value_usd": total,
        "cash_weight": max(0.0, float(cash_usd)) / total if total > 0 else None,
        "maximum_position_weight": max(weights) if weights else None,
        "concentration_hhi": sum(weight * weight for weight in weights),
        "gross_effective_exposure": effective,
        "numeric_score_authority": false_value(),
    }


def false_value() -> bool:
    """Make the non-authority marker conspicuous in serialized risk records."""
    return False


def _candidate_decision(candidate: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    candidate_type = candidate.get("type")
    action = "ADD" if candidate_type == "EXISTING_HOLDING_ADD" else "NEW_BUY"
    event = evaluate_event_actionability(str(candidate.get("event_readiness_status")), action, policy)
    blockers: list[str] = []
    if candidate.get("hard_gate_status") != "PASS": blockers.append("HARD_GATE_FAILED")
    if candidate.get("risk_gate_status") != "PASS": blockers.append("RISK_GATE_FAILED")
    if candidate.get("portfolio_fit_status") != "PASS": blockers.append("PORTFOLIO_FIT_FAILED")
    if not event["allowed"]: blockers.append("EVENT_ACTIONABILITY_BLOCKED")
    return {
        **deepcopy(candidate),
        "event_actionability": event,
        "eligible_for_shadow_comparison": not blockers,
        "blockers": blockers,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def build_capital_reallocation_shadow(context: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    ordering_errors = validate_post_close_ordering(
        decision_as_of=context["decision_as_of"], market_data_cutoff=context["market_data_cutoff"],
        event_cutoff=context["event_cutoff"], broker_cutoff=context["broker_cutoff"],
        candidate_cutoff=context.get("candidate_cutoff"),
        evidence_timestamps=list(context.get("evidence_timestamps") or []),
        completed_bar_finalization_status=context["completed_bar_finalization_status"],
        event_refresh_status=context["event_refresh_status"],
        event_resolution_status=context["event_resolution_status"],
        holding_compile_mode=context["holding_compile_mode"],
        event_bundle_hash=context["event_bundle_hash"],
    )
    expected_tickers = [str(item) for item in context.get("canonical_positive_holding_tickers", [])]
    actual_tickers = [str(row.get("ticker")) for row in context.get("holdings", []) if isinstance(row, dict)]
    if len(expected_tickers) != len(set(expected_tickers)) or len(actual_tickers) != len(set(actual_tickers)):
        raise ValueError("DUPLICATE_HOLDING_DECISION_SCOPE")
    if set(expected_tickers) != set(actual_tickers):
        raise ValueError("CANONICAL_POSITIVE_HOLDING_SCOPE_MISMATCH")
    optimizer_inputs = context.get("optimizer_input_status") or {}
    if set(optimizer_inputs) != set(OPTIMIZER_INPUTS):
        raise ValueError("PORTFOLIO_OPTIMIZER_INPUT_STATUS_INCOMPLETE")
    holdings = [
        evaluate_holding_decision(
            row, policy, validation_mode=context["validation_mode"],
            holding_compile_mode=context["holding_compile_mode"],
            event_resolution_status=context["event_resolution_status"],
        )
        for row in context.get("holdings", [])
    ]
    decision_provenance = {
        "decision_as_of": context["decision_as_of"],
        "market_data_cutoff": context["market_data_cutoff"],
        "event_cutoff": context["event_cutoff"],
        "broker_cutoff": context["broker_cutoff"],
        "candidate_cutoff": context.get("candidate_cutoff"),
        "event_bundle_hash": context["event_bundle_hash"],
        "event_resolution_status": context["event_resolution_status"],
        "holding_compile_mode": context["holding_compile_mode"],
        "policy_version": policy["policy_version"],
    }
    for row in holdings:
        row["decision_provenance"] = deepcopy(decision_provenance)
    positions = deepcopy(context.get("portfolio_positions") or [])
    actual_cash = float(context.get("verified_actual_cash_usd") or 0.0)
    before = _portfolio_risk(positions, actual_cash)
    sale_candidates = [row for row in holdings if row["hypothetical_sell_quantity"]]
    expected_total = sum(row["expected_sale_proceeds_usd"] for row in sale_candidates)
    after_positions = deepcopy(positions)
    by_ticker = {row.get("ticker"): row for row in sale_candidates}
    for row in after_positions:
        sale = by_ticker.get(row.get("ticker"))
        if sale:
            row["market_value_usd"] = max(0.0, float(row["market_value_usd"]) - sale["expected_sale_proceeds_usd"])
    after_sale = _portfolio_risk(after_positions, actual_cash + expected_total)

    candidates = [_candidate_decision(row, policy) for row in context.get("opportunity_candidates", [])]
    for row in candidates:
        row["decision_provenance"] = deepcopy(decision_provenance)
    eligible = [row for row in candidates if row["eligible_for_shadow_comparison"]]
    eligible.sort(key=lambda row: (int(row.get("relative_opportunity_rank", 10**9)), str(row.get("ticker"))))
    best = eligible[0] if eligible else None
    optimizer_complete = all(value in {"AVAILABLE", "NOT_APPLICABLE"} for value in optimizer_inputs.values())
    event_or_evidence_blocked = any(
        "EVENT_ACTIONABILITY_BLOCKED" in row["blockers"] for row in candidates
    ) or not optimizer_complete
    keep_cash_state = "ELIGIBLE_NOT_SELECTED"
    if best is None:
        best_decision, rationale = "KEEP_CASH", "NO_CANDIDATE_PASSED_HARD_RISK_PORTFOLIO_AND_EVENT_GATES"
        keep_cash_state = (
            "SAFE_FALLBACK_NO_NEW_CAPITAL_DEPLOYMENT"
            if event_or_evidence_blocked else "OPTIMIZED_KEEP_CASH"
        )
    elif any(row["selected_holding_action"] == "ROTATE_REVIEW" for row in holdings):
        best_decision, rationale = "ROTATE_REVIEW", "ROTATION_REQUIRES_FULL_PORTFOLIO_RECOMPILE_AND_HUMAN_REVIEW"
    elif best.get("type") == "EXISTING_HOLDING_ADD":
        best_decision, rationale = "ADD_EXISTING_REVIEW", "BEST_ELIGIBLE_EXISTING_HOLDING_SHADOW_USE"
    else:
        best_decision, rationale = "NEW_BUY_REVIEW", "BEST_ELIGIBLE_NEW_BUY_SHADOW_USE"
        keep_cash_state = "ELIGIBLE_NOT_SELECTED"
    cycle_id = str(context["portfolio_reallocation_cycle_id"])
    duplicate = cycle_id in set(context.get("prior_cycle_ids") or [])
    if duplicate:
        best_decision, rationale = "KEEP_CASH", "SAME_CYCLE_DUPLICATE_SUPPRESSED"
        keep_cash_state = "SAFE_FALLBACK_NO_NEW_CAPITAL_DEPLOYMENT"
    degraded_path_status = (
        "EVALUATED" if sale_candidates
        else "NOT_APPLICABLE" if context["holding_compile_mode"] == "DEGRADED_EVENT_SCOPED"
        else "EVALUATED_NO_SALE_CANDIDATE"
    )
    status = "INVALID" if ordering_errors else "CAPITAL_REALLOCATION_SHADOW_VERIFIED"
    return {
        "schema_version": "1.1",
        "mode": "CAPITAL_REALLOCATION_SHADOW",
        "validation_mode": context["validation_mode"],
        "status": status,
        "policy_version": policy["policy_version"],
        "portfolio_decision_semantic_cohort": context["portfolio_decision_semantic_cohort"],
        "canonical_positive_holding_tickers": expected_tickers,
        "portfolio_reallocation_cycle_id": cycle_id,
        "same_cycle_duplicate_suppressed": duplicate,
        "decision_as_of": context["decision_as_of"],
        "completed_bar_finalization_status": context["completed_bar_finalization_status"],
        "event_refresh_status": context["event_refresh_status"],
        "event_resolution_status": context["event_resolution_status"],
        "holding_compile_mode": context["holding_compile_mode"],
        "capital_reallocation_degraded_path_status": degraded_path_status,
        "event_bundle_hash": context["event_bundle_hash"],
        "decision_provenance": decision_provenance,
        "market_data_cutoff": context["market_data_cutoff"],
        "event_cutoff": context["event_cutoff"],
        "broker_cutoff": context["broker_cutoff"],
        "candidate_cutoff": context.get("candidate_cutoff"),
        "post_close_ordering_status": "PASS" if not ordering_errors else "FAIL",
        "ordering_errors": ordering_errors,
        "holding_decisions": holdings,
        "expected_sale_proceeds_usd": expected_total,
        "expected_sale_proceeds_status": "SHADOW_ONLY",
        "verified_actual_cash_usd": actual_cash,
        "verified_orderable_cash_from_expected_proceeds_usd": 0.0,
        "hypothetical_cash_usd_after_sale": actual_cash + expected_total,
        "hypothetical_cash_status": "SHADOW_ONLY",
        "funding_authority": "VERIFIED_ACTUAL_CASH_ONLY",
        "expected_proceeds_may_fund_candidate": False,
        "capital_availability_status": context.get("capital_availability_status", "UNVERIFIED"),
        "portfolio_risk_before": before,
        "portfolio_risk_after": after_sale,
        "portfolio_risk_after_basis": "SHADOW_POST_SALE_ONLY",
        "optimizer_input_status": deepcopy(optimizer_inputs),
        "hypothetical_post_sale_portfolio": after_positions,
        "candidate_comparison": candidates,
        "keep_cash_alternative": {"status": "ELIGIBLE", "actual_cash_usd": actual_cash},
        "keep_cash_state": keep_cash_state,
        "best_shadow_decision": best_decision,
        "best_shadow_candidate": best.get("ticker") if best else None,
        "decision_rationale": rationale,
        "portfolio_turnover_status": "OBSERVATION_ONLY_NO_THRESHOLD",
        "reallocation_cooldown_status": "NOT_CONFIGURED",
        "rotation_justification": context.get("rotation_justification"),
        "sell_risk_decision": "RISK_REVIEW_REQUIRED" if sale_candidates else "NOT_APPLICABLE",
        "buy_risk_decision": "RISK_REVIEW_REQUIRED" if best else "NOT_APPLICABLE",
        "future_execution_state_compatibility": list(policy.get("future_execution_states") or []),
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
        "portfolio_mutation": False,
    }


def validate_report(report: dict[str, Any], schema_path: Path) -> list[str]:
    errors = validate_instance(report, schema_path)
    if report.get("expected_sale_proceeds_status") != "SHADOW_ONLY":
        errors.append("EXPECTED_PROCEEDS_NOT_SHADOW_ONLY")
    if report.get("verified_orderable_cash_from_expected_proceeds_usd") != 0:
        errors.append("EXPECTED_PROCEEDS_BECAME_ORDERABLE_CASH")
    if report.get("hypothetical_cash_status") != "SHADOW_ONLY":
        errors.append("HYPOTHETICAL_CASH_NOT_SHADOW_ONLY")
    if report.get("execution_quantity") is not None or report.get("quantity_authority") != "none":
        errors.append("EXECUTION_QUANTITY_AUTHORITY_VIOLATION")
    if report.get("order_authority") is not False or report.get("portfolio_mutation") is not False:
        errors.append("AUTHORITY_OR_PORTFOLIO_MUTATION_VIOLATION")
    for item in report.get("holding_decisions") or []:
        axes = item.get("state_axes") or {}
        if any(axis not in axes for axis in TEN_AXES):
            errors.append(f"TEN_AXIS_STATE_MISSING:{item.get('ticker')}")
    return list(dict.fromkeys(errors))


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--context-schema", required=True, type=Path)
    parser.add_argument("--report-schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    protected = [
        args.context, args.policy, args.context_schema, args.report_schema,
        root / "stock-strategy-system" / "portfolio_state.json",
        root / "stock-strategy-system" / "alert_policy.json",
    ]
    try:
        validate_output_path(args.output, repository_root=root, protected=protected)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    context, policy = load_json(args.context), load_json(args.policy)
    policy_errors = validate_policy(policy)
    if policy_errors:
        raise SystemExit("policy validation failed: " + "; ".join(policy_errors))
    context_errors = validate_instance(context, args.context_schema)
    if context_errors:
        raise SystemExit("context validation failed: " + "; ".join(context_errors))
    report = build_capital_reallocation_shadow(context, policy)
    errors = validate_report(report, args.report_schema)
    if errors:
        raise SystemExit("report validation failed: " + "; ".join(errors))
    _atomic_write(args.output, report)
    print(json.dumps({
        "output": str(args.output), "status": report["status"],
        "order_authority": False, "portfolio_mutation": False,
    }, separators=(",", ":")))
    return 0 if report["status"] == "CAPITAL_REALLOCATION_SHADOW_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
