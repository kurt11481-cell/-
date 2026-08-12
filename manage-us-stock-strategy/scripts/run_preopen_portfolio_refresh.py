#!/usr/bin/env python3
"""Revalidate an immutable post-market strategy against pre-open deltas.

Premarket prices are indicative.  This module cannot calculate daily technical
signals, declare a completed-close hard-risk breach, create quantity, or place
an order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from build_post_market_baseline import validate_baseline
from build_run_manifest import build_manifest
from portfolio_policy_gates import evaluate_cash_status
from validation_common import canonical_hash, load_json, parse_datetime, validate_instance, write_json


READINESS = {"CLEAR", "CAUTION", "RESEARCH_REFRESH_REQUIRED", "GAP_INVALIDATED", "EVENT_BLOCKED", "LIQUIDITY_BLOCKED", "DATA_INCOMPLETE"}


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _baseline_status(baseline: dict[str, Any] | None, report: dict[str, Any] | None,
                     post_market_manifest: dict[str, Any] | None, *,
                     latest_completed_session: str, upcoming_session: str, schema: Path,
                     strategy_version: str, policy_version: str) -> tuple[str, list[str]]:
    if not baseline or not report:
        return "POST_MARKET_BASELINE_MISSING", ["POST_MARKET_BASELINE_MISSING"]
    errors = validate_baseline(baseline, schema)
    if baseline.get("post_market_session") != latest_completed_session:
        errors.append("baseline is not for the latest completed regular session")
    if report.get("market_session") != latest_completed_session or report.get("run_phase") != "POST_MARKET":
        errors.append("post-market report session or phase is invalid")
    if baseline.get("portfolio_strategy_report_hash") != canonical_hash(report):
        errors.append("post-market report hash does not match baseline")
    if not post_market_manifest:
        errors.append("post-market run manifest is missing")
    else:
        if baseline.get("run_manifest_hash") != canonical_hash(post_market_manifest):
            errors.append("post-market run manifest hash does not match baseline")
        provenance = post_market_manifest.get("code_provenance") or {}
        if post_market_manifest.get("run_phase") != "POST_MARKET" or post_market_manifest.get("market_session") != latest_completed_session:
            errors.append("post-market run manifest phase or session is invalid")
        if baseline.get("git_commit") != provenance.get("git_commit"):
            errors.append("post-market baseline git commit does not match manifest")
        if baseline.get("strategy_version") != provenance.get("strategy_version") or baseline.get("policy_version") != provenance.get("policy_version"):
            errors.append("post-market baseline strategy/policy provenance does not match manifest")
    if baseline.get("strategy_version") != strategy_version or baseline.get("policy_version") != policy_version:
        errors.append("baseline strategy or policy version mismatch")
    try:
        regular_open = datetime.fromisoformat(upcoming_session).replace(
            hour=9, minute=30, second=0, microsecond=0, tzinfo=ZoneInfo("America/New_York"))
        if parse_datetime(baseline["generated_at"]) >= regular_open:
            errors.append("baseline was not generated before the upcoming regular-session open")
    except (KeyError, ValueError):
        errors.append("baseline generated_at is invalid")
    return ("POST_MARKET_BASELINE_INVALID", errors) if errors else ("VALID", [])


def _material_events(events: dict[str, Any], symbol: str, baseline_generated_at: str, cutoff: str) -> tuple[list[dict[str, Any]], bool]:
    baseline_time = parse_datetime(baseline_generated_at)
    cutoff_time = parse_datetime(cutoff)
    relevant: list[dict[str, Any]] = []
    blocked = False
    for event in events.get("events", []):
        if event.get("ticker") not in {symbol, "GLOBAL"} or event.get("validation_status") != "VALIDATED" or event.get("source_type") != "primary":
            continue
        published = event.get("announced_at") or event.get("effective_at") or event.get("retrieved_at")
        if not published:
            continue
        when = parse_datetime(published)
        if baseline_time < when <= cutoff_time:
            relevant.append(event)
            blocked = blocked or event.get("policy_effect") == "WAIT_REQUIRED"
    return relevant, blocked


def _approved_gap_invalidated(policy: dict[str, Any], symbol: str, quote: float | None) -> tuple[bool, str]:
    rule = (((policy.get("gap_policy") or {}).get("approved_gap_rules") or {}).get(symbol) or {})
    if not rule or rule.get("approval_status") != "VERIFIED_USER_APPROVAL" or quote is None:
        return False, "GAP_CONTEXT_ONLY"
    if rule.get("rule_type") == "outside_entry_band":
        band = rule.get("entry_band") or []
        if len(band) == 2 and all(_finite(value) for value in band):
            return not float(band[0]) <= quote <= float(band[1]), "APPROVED_ENTRY_BAND"
    level = rule.get("invalidation_price")
    if _finite(level):
        if rule.get("operator") == "below":
            return quote < float(level), "APPROVED_INVALIDATION_PRICE"
        if rule.get("operator") == "above":
            return quote > float(level), "APPROVED_INVALIDATION_PRICE"
    return False, "GAP_CONTEXT_ONLY"


def _baseline_items(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for holding in report.get("holding_strategies", []):
        result[holding["ticker"]] = {"holding": holding, "radar": None}
    for radar in (report.get("tactical_radar_result") or {}).get("candidate_dispositions", []):
        result.setdefault(radar["ticker"], {"holding": None, "radar": None})["radar"] = radar
    return result


def build_preopen_refresh(
    *, baseline: dict[str, Any] | None, post_market_report: dict[str, Any] | None,
    post_market_manifest: dict[str, Any] | None,
    premarket_snapshot: dict[str, Any], overnight_events: dict[str, Any], portfolio_state: dict[str, Any],
    preopen_policy: dict[str, Any], runtime: dict[str, Any] | None, generated_at: str,
    upcoming_session: str, latest_completed_session: str, strategy_version: str,
    post_market_policy_version: str, maximum_broker_age_calendar_days: int = 4,
    baseline_schema: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = baseline_schema or Path(__file__).resolve().parents[1] / "schemas" / "post-market-baseline.schema.json"
    baseline_status, baseline_errors = _baseline_status(baseline, post_market_report, post_market_manifest,
        latest_completed_session=latest_completed_session, upcoming_session=upcoming_session, schema=schema,
        strategy_version=strategy_version, policy_version=post_market_policy_version)
    cash_gate = evaluate_cash_status(portfolio_state, reference_session=upcoming_session,
        maximum_age_calendar_days=maximum_broker_age_calendar_days, required_strategy_version=strategy_version)
    provider_status = premarket_snapshot.get("provider_status", "UNAVAILABLE")
    global_failures: list[str] = []
    if baseline_status != "VALID":
        global_failures.append(baseline_status)
    if provider_status == "UNAVAILABLE":
        global_failures.append("GLOBAL_PREMARKET_DATA_OUTAGE")
    if not (
        premarket_snapshot.get("official_upcoming_session_verified") is True
        and premarket_snapshot.get("session_verification_status") == "verified_trading_day"
        and premarket_snapshot.get("upcoming_regular_session") == upcoming_session
        and premarket_snapshot.get("latest_completed_regular_session") == latest_completed_session
    ):
        global_failures.append("OFFICIAL_UPCOMING_SESSION_UNVERIFIED")
    records = {item.get("ticker"): item for item in premarket_snapshot.get("records", []) if item.get("ticker")}
    runtime = deepcopy(runtime or {"schema_version": "2.4", "last_run_at": None, "deliveries": {}, "items": {}, "order_authority": False})
    runtime.setdefault("deliveries", {})
    runtime.setdefault("items", {})
    items: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []

    if baseline_status == "VALID" and post_market_report:
        for symbol, pair in _baseline_items(post_market_report).items():
            holding = pair["holding"] or {}
            radar = pair["radar"] or {}
            record = records.get(symbol)
            quote = float(record["quote"]) if isinstance(record, dict) and _finite(record.get("quote")) else None
            strategy_state = holding.get("strategy_state")
            opportunity_state = radar.get("opportunity_state")
            if radar.get("opportunity_state") in {"READY", "NEAR_TRIGGER", "WATCH"}:
                baseline_execution = radar.get("execution_state") or holding.get("execution_state") or "WATCH_ONLY"
            else:
                baseline_execution = holding.get("execution_state") or radar.get("execution_state") or "WATCH_ONLY"
            readiness = "CLEAR"
            refreshed_execution = baseline_execution
            reasons: list[str] = []
            remaining = list(dict.fromkeys(list(holding.get("remaining_conditions") or []) + list(radar.get("remaining_conditions") or [])))
            event_type = "NO_MATERIAL_CHANGE"
            material_events, event_blocked = _material_events(overnight_events, symbol, baseline["generated_at"], generated_at)
            if provider_status == "UNAVAILABLE":
                readiness, refreshed_execution, event_type = "DATA_INCOMPLETE", "DATA_BLOCKED", "NO_MATERIAL_CHANGE"
                reasons.append("The premarket provider is globally unavailable; one global incident represents the outage.")
            elif record is None or record.get("data_quality") == "DATA_INCOMPLETE":
                readiness, refreshed_execution, event_type = "DATA_INCOMPLETE", "DATA_BLOCKED", "TICKER_PREMARKET_DATA_FAILURE"
                reasons.append("Ticker-specific premarket quote is unavailable; the post-market state remains visible but execution refresh is blocked.")
            if event_blocked:
                readiness, refreshed_execution, event_type = "EVENT_BLOCKED", "WATCH_ONLY", "EVENT_BLOCKED"
                reasons.append("A validated overnight event has an approved WAIT_REQUIRED policy effect.")
            elif material_events:
                readiness, refreshed_execution, event_type = "RESEARCH_REFRESH_REQUIRED", "WATCH_ONLY", "RESEARCH_REFRESH_REQUIRED"
                reasons.append("New authoritative overnight evidence requires bounded research refresh.")
            invalidated, gap_basis = _approved_gap_invalidated(preopen_policy, symbol, quote)
            if invalidated:
                readiness, refreshed_execution, event_type = "GAP_INVALIDATED", "WATCH_ONLY", "GAP_INVALIDATED"
                reasons.append("An explicitly approved pre-open gap invalidation rule was breached.")
            elif quote is not None:
                remaining.append("GAP_CONTEXT_ONLY")

            premarket_risk = "NONE"
            if holding and quote is not None and _finite(holding.get("average_cost_usd")):
                fraction = ((((post_market_report.get("holding_risk_result") or {}).get("candidates") or [])))
                hard = next((entry for entry in fraction if entry.get("symbol") == symbol and _finite(entry.get("hard_boundary_usd"))), None)
                if hard and quote <= float(hard["hard_boundary_usd"]):
                    premarket_risk = "PREMARKET_RISK_WATCH"
                    if readiness == "CLEAR":
                        readiness = "CAUTION"
                    reasons.append("Premarket indicative quote is below the configured boundary, but no completed regular-session breach is being declared.")
                    remaining.append("COMPLETED_REGULAR_SESSION_HARD_RISK_REVIEW")

            if readiness == "CLEAR" and baseline_execution == "CASH_BLOCKED" and cash_gate["cash_status"] == "VERIFIED_POSITIVE":
                if radar.get("new_buy_approval") is True and opportunity_state == "READY":
                    refreshed_execution = "ELIGIBLE_FOR_REVIEW"
                else:
                    refreshed_execution = "NOT_APPROVED" if radar else "WATCH_ONLY"
                event_type = "CASH_GATE_REEVALUATED"
                reasons.append("Fresh verified available cash changed the cash gate; no order or quantity authority was created.")
            elif readiness == "CLEAR" and cash_gate["cash_status"] != "VERIFIED_POSITIVE" and baseline_execution == "ELIGIBLE_FOR_REVIEW":
                refreshed_execution = "CASH_BLOCKED"
                readiness = "CAUTION"
                reasons.append("Execution review was downgraded because fresh verified positive cash is unavailable.")

            if readiness not in READINESS:
                raise ValueError(f"invalid pre-open readiness: {readiness}")
            item = {
                "ticker": symbol, "post_market_strategy_state": strategy_state,
                "post_market_opportunity_state": opportunity_state, "post_market_execution_state": baseline_execution,
                "preopen_readiness_state": readiness, "refreshed_execution_state": refreshed_execution,
                "premarket_quote": quote, "premarket_gap_context": (record or {}).get("gap_fraction"),
                "gap_policy_effect": gap_basis, "overnight_material_change": bool(material_events),
                "premarket_risk_state": premarket_risk,
                "primary_reason": reasons[0] if reasons else "No material overnight reason invalidated the completed-session strategy.",
                "remaining_conditions": list(dict.fromkeys(remaining)),
                "next_review_trigger": "REGULAR_SESSION_OPEN_HUMAN_REVIEW" if readiness != "CLEAR" else "NEXT_COMPLETED_US_SESSION",
                "quantity": None, "quantity_authority": False, "order_authority": False,
            }
            items.append(item)
            event_key = f"{preopen_policy.get('policy_version')}:{symbol}:PRE_OPEN:{event_type}:{strategy_state or opportunity_state}"
            delivery_id = hashlib.sha256(f"{event_key}:{upcoming_session}".encode("utf-8")).hexdigest()
            urgent = event_type in {"GAP_INVALIDATED", "EVENT_BLOCKED", "RESEARCH_REFRESH_REQUIRED", "CASH_GATE_REEVALUATED"}
            notify = bool(urgent and delivery_id not in runtime["deliveries"])
            transitions.append({"ticker": symbol, "run_phase": "PRE_OPEN", "event_type": event_type,
                "baseline_state": strategy_state or opportunity_state, "preopen_readiness_state": readiness,
                "event_key": event_key, "delivery_id": delivery_id, "notify": notify, "order_authority": False})
            runtime["items"][symbol] = {"session": upcoming_session, "readiness": readiness, "execution": refreshed_execution}
            if notify:
                runtime["deliveries"][delivery_id] = {"ticker": symbol, "run_phase": "PRE_OPEN", "session": upcoming_session, "delivered_at": generated_at}

    if global_failures:
        event_type = baseline_status if baseline_status != "VALID" else "GLOBAL_PREMARKET_DATA_OUTAGE"
        event_key = f"{preopen_policy.get('policy_version')}:GLOBAL:PRE_OPEN:{event_type}"
        delivery_id = hashlib.sha256(f"{event_key}:{upcoming_session}".encode("utf-8")).hexdigest()
        transitions.append({"ticker": "GLOBAL", "run_phase": "PRE_OPEN", "event_type": event_type,
            "baseline_state": None, "preopen_readiness_state": "DATA_INCOMPLETE", "event_key": event_key,
            "delivery_id": delivery_id, "notify": delivery_id not in runtime["deliveries"], "order_authority": False})
        if delivery_id not in runtime["deliveries"]:
            runtime["deliveries"][delivery_id] = {"ticker": "GLOBAL", "run_phase": "PRE_OPEN", "session": upcoming_session, "delivered_at": generated_at}

    material = any(item["event_type"] != "NO_MATERIAL_CHANGE" for item in transitions)
    final = "DATA_INCOMPLETE" if global_failures else ("PREOPEN_REVIEW_REQUIRED" if material else "NO_MATERIAL_PREOPEN_CHANGE")
    overnight_status = "EVENT_DATA_INCOMPLETE" if overnight_events.get("coverage_status") == "EVENT_DATA_INCOMPLETE" else ("MATERIAL_CHANGE" if any(item.get("overnight_material_change") for item in items) else "CLEAR")
    report = {
        "schema_version": "2.4", "run_phase": "PRE_OPEN", "generated_at": generated_at,
        "upcoming_regular_session": upcoming_session,
        "baseline_session": baseline.get("post_market_session") if baseline else None,
        "baseline_run_id": baseline.get("post_market_run_id") if baseline else None,
        "baseline_hash_status": baseline_status,
        "premarket_data_status": provider_status, "overnight_event_status": overnight_status,
        "broker_refresh_status": cash_gate["cash_status"], "provider_health": {"premarket": provider_status},
        "global_failures": list(dict.fromkeys(global_failures + baseline_errors)), "items": items,
        "transitions": transitions, "final_conclusion": final,
        "quantity_authority": False, "order_authority": False,
    }
    runtime["schema_version"] = "2.4"
    runtime["last_run_at"] = generated_at
    runtime["last_upcoming_session"] = upcoming_session
    runtime["order_authority"] = False
    return report, runtime


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--post-market-report", type=Path)
    parser.add_argument("--post-market-manifest", type=Path)
    parser.add_argument("--premarket", required=True, type=Path)
    parser.add_argument("--overnight-events", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--preopen-policy", required=True, type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--runtime-output", type=Path)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--upcoming-session", required=True)
    parser.add_argument("--latest-completed-session", required=True)
    parser.add_argument("--strategy-version", required=True)
    parser.add_argument("--post-market-policy-version", required=True)
    parser.add_argument("--maximum-broker-age-calendar-days", type=int, default=4)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    outputs = (root / "workspace" / "outputs").resolve()
    canonical_state = (root / "stock-strategy-system" / "portfolio_state.json").resolve()
    if args.portfolio_state.resolve() != canonical_state:
        raise SystemExit("--portfolio-state must be canonical and read-only")
    protected = {path.resolve() for path in (args.baseline, args.post_market_report, args.post_market_manifest, args.premarket,
        args.overnight_events, args.portfolio_state, args.preopen_policy, args.runtime) if path} | {canonical_state}
    manifest_output = args.manifest_output or args.output.with_name("preopen_run_manifest.json")
    requested_outputs = [path.resolve() for path in (args.output, args.runtime_output, manifest_output) if path]
    if len(requested_outputs) != len(set(requested_outputs)):
        raise SystemExit("pre-open outputs must not alias each other")
    for output in (args.output, args.runtime_output, manifest_output):
        if output and (output.resolve() in protected or not _within(output, outputs)):
            raise SystemExit("outputs must be unique artifacts under workspace/outputs")
    premarket = load_json(args.premarket)
    preopen_policy = load_json(args.preopen_policy)
    input_errors = validate_instance(premarket, root / "manage-us-stock-strategy" / "schemas" / "premarket-snapshot.schema.json")
    input_errors.extend(validate_instance(preopen_policy, root / "manage-us-stock-strategy" / "schemas" / "preopen-refresh-policy.schema.json"))
    if input_errors:
        raise SystemExit("pre-open input validation failed: " + "; ".join(input_errors))
    post_market_manifest = load_json(args.post_market_manifest) if args.post_market_manifest and args.post_market_manifest.is_file() else None
    if post_market_manifest is not None:
        manifest_input_errors = validate_instance(post_market_manifest, root / "manage-us-stock-strategy" / "schemas" / "run-manifest.schema.json")
        if manifest_input_errors:
            raise SystemExit("post-market manifest validation failed: " + "; ".join(manifest_input_errors))
    report, runtime = build_preopen_refresh(baseline=load_json(args.baseline) if args.baseline and args.baseline.is_file() else None,
        post_market_report=load_json(args.post_market_report) if args.post_market_report and args.post_market_report.is_file() else None,
        post_market_manifest=post_market_manifest,
        premarket_snapshot=premarket, overnight_events=load_json(args.overnight_events),
        portfolio_state=load_json(args.portfolio_state), preopen_policy=preopen_policy,
        runtime=load_json(args.runtime) if args.runtime and args.runtime.is_file() else None,
        generated_at=args.generated_at, upcoming_session=args.upcoming_session,
        latest_completed_session=args.latest_completed_session, strategy_version=args.strategy_version,
        post_market_policy_version=args.post_market_policy_version,
        maximum_broker_age_calendar_days=args.maximum_broker_age_calendar_days)
    errors = validate_instance(report, root / "manage-us-stock-strategy" / "schemas" / "preopen-refresh-report.schema.json")
    errors.extend(validate_instance(runtime, root / "manage-us-stock-strategy" / "schemas" / "preopen-refresh-runtime.schema.json"))
    if errors:
        raise SystemExit("pre-open report validation failed: " + "; ".join(errors))
    write_json(args.output, report)
    if args.runtime_output:
        _atomic_write(args.runtime_output, runtime)
    manifest_hashes = []
    if args.baseline and args.baseline.is_file():
        manifest_hashes.append(["evidence_packet_hash", str(args.baseline)])
    elif args.post_market_report and args.post_market_report.is_file():
        manifest_hashes.append(["evidence_packet_hash", str(args.post_market_report)])
    manifest_hashes.extend([["market_snapshot_hash", str(args.premarket)],
                            ["event_snapshot_hash", str(args.overnight_events)],
                            ["portfolio_state_hash", str(args.portfolio_state)],
                            ["strategy_policy_hash", str(args.preopen_policy)]])
    manifest_args = argparse.Namespace(
        repo=root,
        run_id=f"PREOPEN-REFRESH-{args.upcoming_session}",
        run_phase="PRE_OPEN",
        analysis_id=f"PREOPEN-REFRESH-{args.upcoming_session}",
        run_type="LIVE_SHADOW_REVIEW",
        generated_at=args.generated_at,
        analysis_cutoff=args.generated_at,
        market_session=args.upcoming_session,
        skill_version="2.4",
        strategy_version=args.strategy_version,
        policy_version=str(preopen_policy.get("policy_version") or "UNVERSIONED"),
        llm_provider=None,
        llm_model=None,
        llm_identifier=None,
        temperature=None,
        max_debate_rounds=0,
        max_risk_rounds=0,
        hash=manifest_hashes,
        result_hash=[["deterministic_gate_hash", str(args.output)]],
        gate_result=report["final_conclusion"],
    )
    manifest = build_manifest(manifest_args)
    manifest_errors = validate_instance(manifest, root / "manage-us-stock-strategy" / "schemas" / "run-manifest.schema.json")
    if manifest_errors:
        raise SystemExit("pre-open run manifest validation failed: " + "; ".join(manifest_errors))
    write_json(manifest_output, manifest)
    print(json.dumps({"status": report["final_conclusion"], "baseline": report["baseline_hash_status"], "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
