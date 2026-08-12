#!/usr/bin/env python3
"""Build a cash-safe capital redeployment review without execution authority."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance, write_json


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validated_reference_price(market: dict[str, Any], symbol: str, market_session: str | None) -> float | None:
    row = (market.get("symbols") or {}).get(symbol)
    if not isinstance(row, dict) or not market_session:
        return None
    indicator = row.get("indicator_validation") or {}
    crosscheck = row.get("quote_crosscheck") or {}
    if not (
        row.get("bar_date") == market_session
        and _finite(row.get("close")) and float(row["close"]) > 0
        and row.get("corporate_action_unresolved") is False
        and indicator.get("status") == "passed" and indicator.get("errors") == []
        and crosscheck.get("status") == "verified"
        and crosscheck.get("independent_of_builder") is True
        and crosscheck.get("bar_date") == market_session
    ):
        return None
    return float(row["close"])


def build_capital_redeployment_plan(
    portfolio_state: dict[str, Any],
    holding_strategies: list[dict[str, Any]],
    tactical_radar: dict[str, Any],
    holding_risk_result: dict[str, Any],
    market_snapshot: dict[str, Any],
    *,
    generated_at: str,
    analysis_cutoff: str,
    market_session: str | None,
    policy_version: str,
    unsettled_or_unconfirmed_proceeds_usd: float | None = None,
) -> dict[str, Any]:
    broker = portfolio_state.get("last_confirmed_broker_snapshot") or {}
    cash = portfolio_state.get("available_cash_usd")
    cash_verified = broker.get("cash_verified") is True and _finite(cash) and float(cash) >= 0
    verified_cash = float(cash) if cash_verified else None
    execution_power = verified_cash
    if unsettled_or_unconfirmed_proceeds_usd is not None and (not _finite(unsettled_or_unconfirmed_proceeds_usd) or unsettled_or_unconfirmed_proceeds_usd < 0):
        raise ValueError("unsettled proceeds must be a non-negative explicit value or null")

    projected_details: list[dict[str, Any]] = []
    for strategy in holding_strategies:
        if strategy.get("strategy_state") not in {"REDUCTION_REVIEW", "EXIT_REVIEW"}:
            continue
        if strategy.get("quantity_authority") != "deterministic_existing_policy":
            continue
        quantity = strategy.get("quantity")
        if not isinstance(quantity, int) or quantity <= 0:
            continue
        if not all(isinstance(strategy.get(field), str) and strategy.get(field) for field in ("policy_rule_id", "tranche_id", "trigger_path")):
            continue
        price = _validated_reference_price(market_snapshot, str(strategy["ticker"]), market_session)
        if price is None:
            continue
        projected_details.append({
            "ticker": strategy["ticker"], "quantity": quantity, "reference_price_usd": price,
            "gross_projected_proceeds_usd": round(quantity * price, 8),
            "status": "PROJECTED_ONLY_NOT_AVAILABLE_CASH", "fill_confirmed": False,
            "quantity_authority": "deterministic_existing_policy",
            "policy_rule_id": strategy["policy_rule_id"], "tranche_id": strategy["tranche_id"],
            "trigger_path": strategy["trigger_path"],
        })
    projected = round(sum(item["gross_projected_proceeds_usd"] for item in projected_details), 8) if projected_details else None

    hard_risk_freeze = bool(
        holding_risk_result.get("risk_freeze_active")
        or any(strategy.get("hard_risk_active") is True for strategy in holding_strategies)
    )
    candidate_uses: list[dict[str, Any]] = []
    for item in tactical_radar.get("candidate_dispositions", []):
        if item.get("opportunity_state") not in {"READY", "NEAR_TRIGGER"}:
            continue
        execution = item.get("execution_state", "DATA_BLOCKED")
        remaining = list(item.get("remaining_conditions") or [])
        if hard_risk_freeze:
            if "HARD_RISK_NEW_BUY_FREEZE" not in remaining:
                remaining.append("HARD_RISK_NEW_BUY_FREEZE")
            if execution not in {"DATA_BLOCKED", "NOT_APPROVED"}:
                execution = "PORTFOLIO_BLOCKED"
        candidate_uses.append({
            "use_id": f"NEW_POSITION:{item['ticker']}", "type": "NEW_POSITION", "ticker": item["ticker"],
            "opportunity_or_strategy_state": item["opportunity_state"], "execution_state": execution,
            "portfolio_fit": item.get("portfolio_fit_status", "UNVERIFIED"),
            "primary_reason": item.get("primary_blocker") or "Validated tactical opportunity remains subject to all execution gates.",
            "remaining_conditions": remaining, "quantity": None, "quantity_authority": "none",
        })
    for strategy in holding_strategies:
        if strategy.get("strategy_state") not in {"ADD_REVIEW", "ADD_ON_WATCH"}:
            continue
        candidate_uses.append({
            "use_id": f"EXISTING_HOLDING_ADD:{strategy['ticker']}", "type": "EXISTING_HOLDING_ADD",
            "ticker": strategy["ticker"], "opportunity_or_strategy_state": strategy["strategy_state"],
            "execution_state": strategy["execution_state"], "portfolio_fit": strategy["portfolio_fit_status"],
            "primary_reason": strategy["primary_reason"], "remaining_conditions": list(strategy["remaining_conditions"]),
            "quantity": None, "quantity_authority": "none",
        })
    candidate_uses.append({
        "use_id": "KEEP_CASH", "type": "KEEP_CASH", "ticker": None,
        "opportunity_or_strategy_state": "ALWAYS_AVAILABLE", "execution_state": "ELIGIBLE_FOR_REVIEW" if cash_verified else "DATA_BLOCKED",
        "portfolio_fit": "FITS", "primary_reason": "Capital deployment is not forced; verified cash may remain unallocated.",
        "remaining_conditions": [] if cash_verified else ["VERIFIED_AVAILABLE_CASH"], "quantity": None,
        "quantity_authority": "none",
    })

    executable = [item for item in candidate_uses if item["type"] != "KEEP_CASH" and item["execution_state"] == "ELIGIBLE_FOR_REVIEW"]
    researched = [item for item in candidate_uses if item["type"] != "KEEP_CASH" and item["opportunity_or_strategy_state"] in {"READY", "ADD_REVIEW"}]
    preferred_ticker = tactical_radar.get("preferred_candidate")
    alternative_ticker = tactical_radar.get("alternative_candidate")
    ranked_use_ids = [f"NEW_POSITION:{symbol}" for symbol in (preferred_ticker, alternative_ticker) if isinstance(symbol, str)]
    executable_ids = {item["use_id"] for item in executable}
    researched_ids = {item["use_id"] for item in researched}
    preferred = "KEEP_CASH"
    if verified_cash and verified_cash > 0:
        preferred = next((use_id for use_id in ranked_use_ids if use_id in executable_ids), "KEEP_CASH")
    elif projected:
        preferred = next((use_id for use_id in ranked_use_ids if use_id in researched_ids), "KEEP_CASH")
    eligible_for_alternative = executable_ids | (researched_ids if projected else set())
    alternative = next((use_id for use_id in ranked_use_ids if use_id != preferred and use_id in eligible_for_alternative), None)
    if alternative is None and preferred != "KEEP_CASH":
        alternative = "KEEP_CASH"
    if not cash_verified:
        funding_status = "DATA_BLOCKED"
    elif verified_cash > 0:
        funding_status = "FUNDED_VERIFIED"
    elif projected:
        funding_status = "UNFUNDED_PROJECTED_PLAN"
    else:
        funding_status = "NO_VERIFIED_FUNDING"
    blockers: list[str] = []
    if not cash_verified:
        blockers.append("VERIFIED_AVAILABLE_CASH_NOT_CONFIRMED")
    elif verified_cash <= 0:
        blockers.append("VERIFIED_AVAILABLE_CASH_IS_ZERO")
    if hard_risk_freeze:
        blockers.append("HARD_RISK_NEW_BUY_FREEZE")
    if projected:
        blockers.append("PROJECTED_PROCEEDS_ARE_NOT_EXECUTION_PURCHASING_POWER")
    return {
        "schema_version": "2.3", "generated_at": generated_at, "analysis_cutoff": analysis_cutoff,
        "market_session": market_session, "funding_status": funding_status,
        "verified_available_cash_usd": verified_cash, "projected_sale_proceeds_usd": projected,
        "projected_sale_details": projected_details,
        "unsettled_or_unconfirmed_proceeds_usd": float(unsettled_or_unconfirmed_proceeds_usd) if unsettled_or_unconfirmed_proceeds_usd is not None else None,
        "execution_purchasing_power_usd": execution_power,
        "projected_proceeds_status": "PROJECTED_ONLY_NOT_AVAILABLE_CASH_NO_FILL_CONFIRMED" if projected else "NONE",
        "cost_impact_status": "ASSUMPTION_REQUIRED" if projected else "NOT_APPLICABLE",
        "candidate_uses": candidate_uses, "preferred_use": preferred, "alternative_use": alternative,
        "cash_reserve_option": "KEEP_CASH", "execution_blockers": list(dict.fromkeys(blockers)),
        "policy_version": policy_version, "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--holding-strategies", required=True, type=Path)
    parser.add_argument("--tactical-radar", required=True, type=Path)
    parser.add_argument("--holding-risk", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session")
    parser.add_argument("--policy-version", required=True)
    parser.add_argument("--unsettled-proceeds-usd", type=float)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    canonical = (root / "stock-strategy-system" / "portfolio_state.json").resolve()
    outputs = (root / "workspace" / "outputs").resolve()
    if args.portfolio_state.resolve() != canonical:
        raise SystemExit("--portfolio-state must be canonical and read-only")
    try:
        args.output.resolve().relative_to(outputs)
    except ValueError as exc:
        raise SystemExit("--output must be under workspace/outputs") from exc
    protected = {path.resolve() for path in (args.portfolio_state, args.holding_strategies,
        args.tactical_radar, args.holding_risk, args.market)}
    if args.output.resolve() in protected:
        raise SystemExit("output may not alias an input or canonical portfolio state")
    holding_payload = load_json(args.holding_strategies)
    strategies = holding_payload.get("holding_strategies") if isinstance(holding_payload, dict) else holding_payload
    plan = build_capital_redeployment_plan(load_json(args.portfolio_state), strategies, load_json(args.tactical_radar),
        load_json(args.holding_risk), load_json(args.market), generated_at=args.generated_at,
        analysis_cutoff=args.analysis_cutoff, market_session=args.market_session, policy_version=args.policy_version,
        unsettled_or_unconfirmed_proceeds_usd=args.unsettled_proceeds_usd)
    errors = validate_instance(plan, root / "manage-us-stock-strategy" / "schemas" / "capital-redeployment-plan.schema.json")
    if errors:
        raise SystemExit("capital plan schema validation failed: " + "; ".join(errors))
    write_json(args.output, plan)
    print(json.dumps({"status": plan["funding_status"], "preferred_use": plan["preferred_use"],
        "execution_purchasing_power_usd": plan["execution_purchasing_power_usd"], "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
