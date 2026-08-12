#!/usr/bin/env python3
"""Coordinate v2.3 holding strategy, tactical radar, and capital review.

All inputs are read-only.  Lower-level deterministic modules retain calculation
authority; this module only coordinates, validates, and reports their outputs.
"""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_capital_redeployment_plan import build_capital_redeployment_plan
from build_holding_strategy_review import build_holding_strategies
from build_run_manifest import build_manifest
from evaluate_alerts import evaluate
from run_tactical_opportunity_radar import build_radar
from validate_registry_consistency import validate_registry_consistency
from validation_common import canonical_hash, load_json, validate_instance, write_json


def _within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _component_output_paths(output_directory: Path, protected: set[Path]) -> dict[str, Path]:
    paths = {
        "holding": output_directory / "holding_strategy_report.json",
        "capital": output_directory / "capital_redeployment_plan.json",
        "combined": output_directory / "portfolio_strategy_report.json",
        "radar": output_directory / "tactical_radar_report.json",
        "risk": output_directory / "holding_risk_result.json",
        "markdown": output_directory / "morning_portfolio_strategy.md",
        "manifest": output_directory / "run_manifest.json",
    }
    collisions = sorted(str(path) for path in paths.values() if path.resolve() in protected)
    if collisions:
        raise ValueError("component outputs may not alias any input: " + ", ".join(collisions))
    return paths


def _holding_data_status(strategies: list[dict[str, Any]]) -> str:
    blocked = sum(1 for item in strategies if item.get("strategy_state") == "DATA_BLOCKED")
    if not strategies or blocked == len(strategies):
        return "DATA_INCOMPLETE"
    return "PARTIAL" if blocked else "VALIDATED"


def _overall_data_status(holding_status: str, tactical_status: str) -> str:
    if holding_status == "DATA_INCOMPLETE" and tactical_status == "DATA_INCOMPLETE":
        return "DATA_INCOMPLETE"
    if holding_status == "VALIDATED" and tactical_status == "VALIDATED":
        return "VALIDATED"
    return "PARTIAL"


def _runtime_transition(previous: str | None, current: str) -> str:
    if previous == current:
        return "NO_MATERIAL_CHANGE"
    if previous is None:
        return "INITIAL_STATE"
    return f"{previous}_TO_{current}"


def update_holding_runtime(
    runtime: dict[str, Any],
    strategies: list[dict[str, Any]],
    *,
    market_session: str | None,
    generated_at: str,
    session_valid: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = deepcopy(runtime)
    updated.setdefault("schema_version", "1.0")
    updated.setdefault("last_processed_session", None)
    updated.setdefault("last_run_at", None)
    updated.setdefault("holdings", {})
    updated.setdefault("deliveries", {})
    notifications: list[dict[str, Any]] = []
    duplicate = bool(market_session and updated.get("last_processed_session") == market_session)
    for strategy in strategies:
        symbol = strategy["ticker"]
        previous = (updated["holdings"].get(symbol) or {}).get("strategy_state")
        transition = "NO_MATERIAL_CHANGE" if duplicate else _runtime_transition(previous, strategy["strategy_state"])
        fingerprint = canonical_hash({key: strategy.get(key) for key in ("ticker", "strategy_state", "execution_state", "primary_reason", "quantity", "tranche_id", "trigger_path")})
        material = transition not in {"NO_MATERIAL_CHANGE", "INITIAL_STATE"}
        delivery_id = canonical_hash({"session": market_session, "ticker": symbol, "transition": transition, "fingerprint": fingerprint})
        delivered = delivery_id in updated["deliveries"]
        notify = bool(session_valid and material and market_session and not duplicate and not delivered)
        notifications.append({"ticker": symbol, "transition": transition, "notify": notify,
            "delivery_id": delivery_id, "strategy_state": strategy["strategy_state"], "order_authority": False})
        if session_valid and market_session and not duplicate:
            updated["holdings"][symbol] = {"strategy_state": strategy["strategy_state"],
                "execution_state": strategy["execution_state"], "fingerprint": fingerprint,
                "last_deep_research_session": market_session if strategy.get("research_packet_hash") else (updated["holdings"].get(symbol) or {}).get("last_deep_research_session")}
            if notify:
                updated["deliveries"][delivery_id] = {"ticker": symbol, "session": market_session,
                    "transition": transition, "delivered_at": generated_at}
    if session_valid and market_session and not duplicate:
        updated["last_processed_session"] = market_session
    updated["last_run_at"] = generated_at
    updated["order_authority"] = False
    return updated, notifications


def build_portfolio_strategy_report(
    *,
    portfolio_state: dict[str, Any],
    alert_policy: dict[str, Any],
    registry: dict[str, Any],
    registry_validation: dict[str, Any],
    universe: dict[str, Any],
    radar_policy: dict[str, Any],
    market_snapshot: dict[str, Any],
    event_snapshot: dict[str, Any],
    radar_context: dict[str, Any],
    holding_research_context: dict[str, Any],
    alert_runtime: dict[str, Any],
    radar_runtime: dict[str, Any],
    holding_runtime: dict[str, Any],
    generated_at: str,
    analysis_cutoff: str,
    market_session: str | None,
    latest_completed_session: str | None,
    holding_risk_result: dict[str, Any] | None = None,
    unsettled_or_unconfirmed_proceeds_usd: float | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    risk_result = holding_risk_result or evaluate(portfolio_state, alert_policy, market_snapshot, alert_runtime)
    strategies = build_holding_strategies(portfolio_state, alert_policy, registry, market_snapshot, event_snapshot,
        risk_result, holding_research_context, analysis_cutoff=analysis_cutoff, market_session=market_session)
    radar, updated_radar = build_radar(universe, registry, registry_validation, market_snapshot, event_snapshot,
        radar_context, portfolio_state, radar_runtime, radar_policy, generated_at=generated_at,
        analysis_cutoff=analysis_cutoff, market_session=market_session, latest_completed_session=latest_completed_session)
    capital = build_capital_redeployment_plan(portfolio_state, strategies, radar, risk_result, market_snapshot,
        generated_at=generated_at, analysis_cutoff=analysis_cutoff, market_session=market_session,
        policy_version=str(radar_policy.get("policy_version") or "UNVERSIONED"),
        unsettled_or_unconfirmed_proceeds_usd=unsettled_or_unconfirmed_proceeds_usd)
    session = market_snapshot.get("session") or {}
    session_valid = bool(
        market_session
        and market_session == latest_completed_session
        and session.get("expected_us_session_date") == latest_completed_session
        and session.get("official_calendar_verified") is True
        and session.get("calendar_verification_status") == "verified_trading_day"
        and session.get("regular_session_complete") is True
        and session.get("us_session_date") == market_session
    )
    updated_holding, notifications = update_holding_runtime(
        holding_runtime,
        strategies,
        market_session=market_session,
        generated_at=generated_at,
        session_valid=session_valid,
    )
    holding_status = _holding_data_status(strategies)
    tactical_status = radar.get("data_status", "DATA_INCOMPLETE")
    overall = _overall_data_status(holding_status, tactical_status)
    hard_risk = any(item.get("hard_risk_active") for item in strategies)
    review_items = [
        {"ticker": item["ticker"], "strategy_state": item["strategy_state"],
         "execution_state": item["execution_state"], "quantity": item["quantity"],
         "quantity_authority": item["quantity_authority"]}
        for item in strategies if item["strategy_state"] in {"ADD_REVIEW", "REDUCTION_REVIEW", "EXIT_REVIEW"}
    ]
    deterministic_gate = "HARD_RISK_REVIEW" if hard_risk else ("DATA_BLOCKED" if overall == "DATA_INCOMPLETE" else ("PASS" if review_items else "WAIT"))
    report = {
        "schema_version": "2.3", "generated_at": generated_at, "analysis_cutoff": analysis_cutoff,
        "market_session": market_session, "data_status": overall, "holding_data_status": holding_status,
        "tactical_data_status": tactical_status, "event_data_status": event_snapshot.get("coverage_status", "EVENT_DATA_INCOMPLETE"),
        "holding_risk_result": risk_result, "holding_strategies": strategies, "tactical_radar_result": radar,
        "cash_funding_state": {"verified_available_cash_usd": capital["verified_available_cash_usd"],
            "projected_sale_proceeds_usd": capital["projected_sale_proceeds_usd"],
            "unsettled_or_unconfirmed_proceeds_usd": capital["unsettled_or_unconfirmed_proceeds_usd"],
            "execution_purchasing_power_usd": capital["execution_purchasing_power_usd"],
            "funding_status": capital["funding_status"]},
        "capital_redeployment": capital,
        "final_portfolio_strategy": {"hard_risk_active": hard_risk, "human_review_items": review_items,
            "preferred_capital_use": capital["preferred_use"], "alternative_capital_use": capital["alternative_use"],
            "keep_cash_option": True, "human_approval_required": True},
        "notifications": notifications,
        "component_artifacts": {"portfolio_state_hash": canonical_hash(portfolio_state),
            "market_snapshot_hash": canonical_hash(market_snapshot), "event_snapshot_hash": canonical_hash(event_snapshot),
            "holding_risk_result_hash": canonical_hash(risk_result), "tactical_radar_hash": canonical_hash(radar),
            "capital_redeployment_hash": canonical_hash(capital)},
        "deterministic_gate_result": deterministic_gate, "order_authority": False,
    }
    return report, updated_holding, strategies, capital, updated_radar


def render_morning_markdown(report: dict[str, Any]) -> str:
    locale_path = Path(__file__).resolve().parents[1] / "assets" / "locales" / "ko-KR.json"
    locale = load_json(locale_path) if locale_path.is_file() else {}
    messages = locale.get("messages") or {}
    reasons = locale.get("reason_translations") or {}
    msg = lambda key, fallback: messages.get(key, fallback)
    reason = lambda value: reasons.get(value, value)
    lines = [f"# {msg('portfolio_title', 'Morning Portfolio Strategy')}", "",
        f"## {msg('critical_risk_heading', 'A. Critical Risk')}", ""]
    hard = [item for item in report["holding_strategies"] if item["hard_risk_active"]]
    lines.extend([f"- {item['ticker']}: {item['strategy_state']} - {reason(item['primary_reason'])}" for item in hard]
        or ["- " + messages.get("portfolio_no_hard_risk", "No active hard-risk review")])
    lines.extend(["", f"## {msg('holdings_heading', 'B. Existing Holdings')}", ""])
    for item in report["holding_strategies"]:
        lines.extend([f"### {item['ticker']}",
            f"- {msg('strategy_execution_label', 'Strategy / Execution')}: {item['strategy_state']} / {item['execution_state']}",
            f"- {msg('primary_reason_label', 'Primary reason')}: {reason(item['primary_reason'])}",
            f"- {msg('quantity_authority_label', 'Quantity / authority')}: {item['quantity']} / {item['quantity_authority']}",
            f"- {msg('next_review_label', 'Next review')}: {item['next_review_trigger']}",
            f"- {msg('add_conditions_label', 'Add conditions')}: {item['add_conditions'] or ['none']}",
            f"- {msg('reduce_conditions_label', 'Reduce conditions')}: {item['reduce_conditions'] or ['none']}", ""])
    lines.extend([f"## {msg('opportunities_heading', 'C. New Opportunities')}", ""])
    for item in report["tactical_radar_result"].get("candidate_dispositions", []):
        lines.append(f"- {item['ticker']}: Opportunity={item['opportunity_state']}, Execution={item['execution_state']}, Blocker={item.get('primary_blocker')}")
    cash = report["cash_funding_state"]
    lines.extend(["", f"## {msg('cash_heading', 'D. Cash / Funding')}", "",
        f"- {msg('verified_cash_label', 'Verified Available Cash')}: {cash['verified_available_cash_usd']}",
        f"- {msg('projected_proceeds_label', 'Projected Sale Proceeds')}: {cash['projected_sale_proceeds_usd']}",
        f"- {msg('unsettled_proceeds_label', 'Unsettled/Unconfirmed Proceeds')}: {cash['unsettled_or_unconfirmed_proceeds_usd']}",
        f"- {msg('purchasing_power_label', 'Execution Purchasing Power')}: {cash['execution_purchasing_power_usd']}", ""])
    capital = report["capital_redeployment"]
    lines.extend([f"## {msg('redeployment_heading', 'E. Capital Redeployment')}", "",
        f"- {msg('funding_status_label', 'Funding status')}: {capital['funding_status']}",
        f"- {msg('preferred_use_label', 'Preferred use')}: {capital['preferred_use']}",
        f"- {msg('alternative_use_label', 'Alternative use')}: {capital['alternative_use']}",
        f"- {msg('keep_cash_label', 'Keep cash option')}: KEEP_CASH", "",
        f"## {msg('review_heading', 'F. Final Human-Review Items')}", ""])
    review_items = report["final_portfolio_strategy"]["human_review_items"]
    lines.extend([f"- {item['ticker']}: {item['strategy_state']} ({item['execution_state']}), quantity={item['quantity']}" for item in review_items]
        or ["- " + messages.get("portfolio_no_human_review", "No current human-review item")])
    lines.extend(["", messages.get("no_order_notice", "No brokerage order was placed or scheduled.")])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--alert-policy", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--radar-policy", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--radar-context", required=True, type=Path)
    parser.add_argument("--holding-context", required=True, type=Path)
    parser.add_argument("--alert-runtime", required=True, type=Path)
    parser.add_argument("--radar-runtime", required=True, type=Path)
    parser.add_argument("--holding-runtime", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session", required=True)
    parser.add_argument("--latest-completed-session", required=True)
    parser.add_argument("--unsettled-proceeds-usd", type=float)
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--holding-runtime-output", type=Path)
    parser.add_argument("--radar-runtime-output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    canonical_state = (root / "stock-strategy-system" / "portfolio_state.json").resolve()
    outputs_root = (root / "workspace" / "outputs").resolve()
    if args.portfolio_state.resolve() != canonical_state:
        raise SystemExit("--portfolio-state must be the canonical read-only operational state")
    if not _within(args.output_directory, outputs_root):
        raise SystemExit("--output-directory must be under workspace/outputs")
    protected = {path.resolve() for path in (args.portfolio_state, args.alert_policy, args.registry, args.universe,
        args.radar_policy, args.market, args.events, args.radar_context, args.holding_context,
        args.alert_runtime, args.radar_runtime, args.holding_runtime)} | {canonical_state}
    for path in (args.holding_runtime_output, args.radar_runtime_output):
        if path and (path.resolve() in protected or not _within(path, outputs_root)):
            raise SystemExit("runtime outputs must be non-aliasing shadow artifacts under workspace/outputs")

    portfolio = load_json(args.portfolio_state)
    alert_policy = load_json(args.alert_policy)
    registry = load_json(args.registry)
    registry_validation = validate_registry_consistency(registry, alert_policy, args.registry.resolve())
    radar_context = load_json(args.radar_context)
    context_errors = validate_instance(radar_context, root / "manage-us-stock-strategy" / "schemas" / "tactical-radar-context.schema.json")
    if context_errors:
        raise SystemExit("invalid radar context: " + "; ".join(context_errors))
    report, holding_runtime, strategies, capital, radar_runtime = build_portfolio_strategy_report(
        portfolio_state=portfolio, alert_policy=alert_policy, registry=registry, registry_validation=registry_validation,
        universe=load_json(args.universe), radar_policy=load_json(args.radar_policy), market_snapshot=load_json(args.market),
        event_snapshot=load_json(args.events), radar_context=radar_context, holding_research_context=load_json(args.holding_context),
        alert_runtime=load_json(args.alert_runtime), radar_runtime=load_json(args.radar_runtime),
        holding_runtime=load_json(args.holding_runtime), generated_at=args.generated_at, analysis_cutoff=args.analysis_cutoff,
        market_session=args.market_session, latest_completed_session=args.latest_completed_session,
        unsettled_or_unconfirmed_proceeds_usd=args.unsettled_proceeds_usd)
    schemas = root / "manage-us-stock-strategy" / "schemas"
    errors = [error for strategy in strategies for error in validate_instance(strategy, schemas / "holding-strategy.schema.json")]
    errors.extend(validate_instance(capital, schemas / "capital-redeployment-plan.schema.json"))
    errors.extend(validate_instance(report, schemas / "portfolio-strategy-report.schema.json"))
    if errors:
        raise SystemExit("portfolio strategy schema validation failed: " + "; ".join(errors))

    output = args.output_directory
    try:
        artifacts = _component_output_paths(output, protected)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    output.mkdir(parents=True, exist_ok=True)
    holding_artifact = artifacts["holding"]
    capital_artifact = artifacts["capital"]
    combined_artifact = artifacts["combined"]
    radar_artifact = artifacts["radar"]
    risk_artifact = artifacts["risk"]
    write_json(holding_artifact, {"schema_version": "2.3", "analysis_cutoff": args.analysis_cutoff,
        "market_session": args.market_session, "holding_strategies": strategies, "order_authority": False})
    write_json(capital_artifact, capital)
    write_json(radar_artifact, report["tactical_radar_result"])
    write_json(risk_artifact, report["holding_risk_result"])
    write_json(combined_artifact, report)
    artifacts["markdown"].write_text(render_morning_markdown(report), encoding="utf-8")
    if args.holding_runtime_output:
        _atomic_write(args.holding_runtime_output, holding_runtime)
    if args.radar_runtime_output:
        _atomic_write(args.radar_runtime_output, radar_runtime)

    manifest_args = argparse.Namespace(repo=root, run_id=f"PORTFOLIO-STRATEGY-{args.market_session}",
        analysis_id=f"PORTFOLIO-STRATEGY-{args.market_session}", run_type="LIVE_SHADOW_REVIEW",
        generated_at=args.generated_at, analysis_cutoff=args.analysis_cutoff, market_session=args.market_session,
        skill_version="2.3", strategy_version=str(portfolio.get("strategy_version")),
        policy_version=str(alert_policy.get("strategy_version") or alert_policy.get("band_version") or "UNVERSIONED"),
        llm_provider=None, llm_model=None, llm_identifier=None, temperature=None, max_debate_rounds=0, max_risk_rounds=0,
        hash=[["market_snapshot_hash", str(args.market)], ["event_snapshot_hash", str(args.events)],
              ["portfolio_state_hash", str(args.portfolio_state)], ["alert_policy_hash", str(args.alert_policy)],
              ["instrument_registry_hash", str(args.registry)], ["candidate_universe_hash", str(args.universe)]],
        result_hash=[["tactical_screen_hash", str(radar_artifact)], ["deterministic_gate_hash", str(combined_artifact)]],
        gate_result=report["deterministic_gate_result"])
    manifest = build_manifest(manifest_args)
    manifest_errors = validate_instance(manifest, schemas / "run-manifest.schema.json")
    if manifest_errors:
        raise SystemExit("run manifest validation failed: " + "; ".join(manifest_errors))
    write_json(artifacts["manifest"], manifest)
    print(json.dumps({"status": report["deterministic_gate_result"], "data_status": report["data_status"],
        "holding_states": {item["ticker"]: item["strategy_state"] for item in strategies},
        "preferred_use": capital["preferred_use"], "order_authority": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
