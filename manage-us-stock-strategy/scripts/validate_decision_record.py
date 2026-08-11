#!/usr/bin/env python3
"""Validate a v2 stock decision record without granting order authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIONS = {
    "WAIT",
    "CONDITIONAL_BUY",
    "BUY_REVIEW",
    "HOLD",
    "TAKE_PROFIT_REVIEW",
    "REDUCTION_REVIEW",
    "STOP_REVIEW",
}
NON_HELD_ACTIONS = {"WAIT", "CONDITIONAL_BUY", "BUY_REVIEW"}
HELD_ACTIONS = {"WAIT", "HOLD", "TAKE_PROFIT_REVIEW", "REDUCTION_REVIEW", "STOP_REVIEW"}
REQUIRED_ROLES = {"identity_data_auditor", "bull_researcher", "bear_researcher"}
DOWNGRADES = {
    "WAIT": {"WAIT"},
    "CONDITIONAL_BUY": {"CONDITIONAL_BUY", "WAIT"},
    "BUY_REVIEW": {"BUY_REVIEW", "CONDITIONAL_BUY", "WAIT"},
    "HOLD": {"HOLD", "WAIT"},
    "TAKE_PROFIT_REVIEW": {"TAKE_PROFIT_REVIEW", "HOLD", "WAIT"},
    "REDUCTION_REVIEW": {"REDUCTION_REVIEW", "HOLD", "WAIT"},
    "STOP_REVIEW": {"STOP_REVIEW", "REDUCTION_REVIEW", "HOLD", "WAIT"},
}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.^=\-]{1,24}$")


class ValidationFailure(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"top-level JSON must be an object: {path}")
    return value


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_datetime(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is missing")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} is not a valid ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone offset")
        return None
    return parsed.astimezone(timezone.utc)


def require_object(value: Any, field: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return {}
    return value


def add_unique(target: list[str], message: str) -> None:
    if message not in target:
        target.append(message)


def action_is_not_more_aggressive(input_action: str, output_action: str) -> bool:
    return output_action in DOWNGRADES.get(input_action, set())


def validate_evidence(packet: dict[str, Any], errors: list[str], warnings: list[str]) -> set[str]:
    cutoff = parse_datetime(packet.get("analysis_cutoff_utc"), "research_packet.analysis_cutoff_utc", errors)
    generated = parse_datetime(packet.get("generated_at_utc"), "research_packet.generated_at_utc", errors)
    if cutoff and generated and generated < cutoff:
        errors.append("research packet was generated before its analysis cutoff")
    evidence = packet.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("research_packet.evidence must be a non-empty list")
        return set()
    ids: set[str] = set()
    for index, item in enumerate(evidence):
        field = f"research_packet.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{field} must be an object")
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or re.fullmatch(r"E[0-9]+", evidence_id) is None:
            errors.append(f"{field}.id is invalid")
            continue
        if evidence_id in ids:
            errors.append(f"duplicate evidence id: {evidence_id}")
        ids.add(evidence_id)
        retrieved = parse_datetime(item.get("retrieved_at_utc"), f"{field}.retrieved_at_utc", errors)
        for time_name in ("published_at_utc", "effective_at_utc"):
            raw_time = item.get(time_name)
            if raw_time is None:
                if item.get("actionable") is True:
                    add_unique(warnings, f"{evidence_id} is actionable but {time_name} is undated")
                continue
            event_time = parse_datetime(raw_time, f"{field}.{time_name}", errors)
            if cutoff and event_time and event_time > cutoff:
                errors.append(f"look-ahead evidence detected: {evidence_id} {time_name}")
        if cutoff and retrieved and retrieved > cutoff and packet.get("analysis_kind") != "REPORT_VALIDATION":
            errors.append(f"look-ahead retrieval detected: {evidence_id}")
        if item.get("actionable") is True and item.get("source_type") in {
            "social",
            "user_provided_unverified",
        }:
            add_unique(warnings, f"{evidence_id} uses a weak source and cannot independently authorize review")
        if item.get("contradiction_status") == "OPEN":
            add_unique(warnings, f"{evidence_id} has an unresolved contradiction")
    return ids


def validate_claim_references(
    value: Any,
    field: str,
    known_ids: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return
    unknown = sorted({item for item in value if isinstance(item, str)} - known_ids)
    if unknown:
        errors.append(f"{field} references unknown evidence ids: {', '.join(unknown)}")


def validate_record(
    record: dict[str, Any],
    registry: dict[str, Any],
    universe: dict[str, Any],
    portfolio_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if record.get("schema_version") != "2.0":
        errors.append("decision record schema_version must be 2.0")
    if record.get("order_authority") is not False:
        errors.append("decision record must explicitly deny order authority")
    if record.get("record_locked") is not True:
        errors.append("decision record must be locked")
    parse_datetime(record.get("created_at_utc"), "created_at_utc", errors)

    symbol = record.get("symbol")
    if not isinstance(symbol, str) or SYMBOL_PATTERN.fullmatch(symbol) is None:
        errors.append("symbol is invalid")
        symbol = ""
    instruments = registry.get("instruments") if isinstance(registry.get("instruments"), dict) else {}
    candidates = universe.get("candidates") if isinstance(universe.get("candidates"), dict) else {}
    instrument = instruments.get(symbol)
    candidate = candidates.get(symbol)
    if not isinstance(instrument, dict):
        errors.append(f"symbol {symbol} is absent from the instrument registry")
        instrument = {}
    if not isinstance(candidate, dict):
        errors.append(f"symbol {symbol} is absent from the tactical candidate universe")
        candidate = {}
    elif candidate.get("watchlist_approved") is not True:
        errors.append(f"symbol {symbol} is not approved for watchlist research")
    if instrument:
        policy_pairs = (
            ("watchlist_approved", "watchlist_approved"),
            ("new_buy_instrument_approved", "new_buy_approved"),
            ("short_sale_approved", "short_approved"),
        )
        for registry_field, candidate_field in policy_pairs:
            if instrument.get(registry_field) != candidate.get(candidate_field):
                errors.append(
                    f"registry and tactical universe disagree on {symbol} {candidate_field}"
                )
    lanes = universe.get("lanes") if isinstance(universe.get("lanes"), dict) else {}
    for lane_name, lane in lanes.items():
        if not isinstance(lane, dict) or symbol not in (lane.get("symbols") or []):
            continue
        for field in ("watchlist_approved", "new_buy_approved"):
            if field in lane and lane.get(field) != candidate.get(field):
                errors.append(f"lane {lane_name} disagrees on {symbol} {field}")
    if record.get("instrument_registry_version") != registry.get("registry_version"):
        errors.append("instrument registry version mismatch")
    if record.get("tactical_universe_version") != universe.get("universe_version"):
        errors.append("tactical universe version mismatch")

    packet = require_object(record.get("research_packet"), "research_packet", errors)
    if packet.get("schema_version") != "2.0":
        errors.append("research packet schema_version must be 2.0")
    if packet.get("symbol") != symbol:
        errors.append("research packet symbol mismatch")
    known_ids = validate_evidence(packet, errors, warnings)
    outputs = packet.get("analyst_outputs")
    if not isinstance(outputs, list):
        errors.append("research_packet.analyst_outputs must be a list")
        outputs = []
    roles: set[str] = set()
    for index, output in enumerate(outputs):
        if not isinstance(output, dict):
            errors.append(f"analyst output {index} must be an object")
            continue
        role = output.get("role")
        if isinstance(role, str):
            roles.add(role)
        validate_claim_references(output.get("claim_ids"), f"analyst output {index}.claim_ids", known_ids, errors)
    missing_roles = sorted(REQUIRED_ROLES - roles)
    if missing_roles:
        errors.append("missing required analyst roles: " + ", ".join(missing_roles))
    manager = require_object(packet.get("research_manager"), "research_packet.research_manager", errors)
    if manager.get("role") != "research_manager":
        errors.append("research manager role is missing")
    validate_claim_references(manager.get("claim_ids"), "research_manager.claim_ids", known_ids, errors)
    if manager.get("status") not in {
        "RESEARCH_COMPLETE",
        "RESEARCH_CONDITIONAL",
        "RESEARCH_REJECTED",
    }:
        errors.append("research manager status is invalid")

    trader = require_object(record.get("trader_proposal"), "trader_proposal", errors)
    if trader.get("symbol") != symbol:
        errors.append("trader proposal symbol mismatch")
    if trader.get("quantity") is not None:
        errors.append("untrusted trader proposal quantity must be null")
    if trader.get("order_authority") is not False:
        errors.append("trader proposal must deny order authority")
    trader_action = trader.get("action")
    if trader_action not in ACTIONS:
        errors.append("trader action is invalid")
        trader_action = "WAIT"
    validate_claim_references(trader.get("claim_ids"), "trader_proposal.claim_ids", known_ids, errors)

    live_record = record.get("test_only") is False
    held = False
    if portfolio_state is not None:
        holdings = portfolio_state.get("holdings") if isinstance(portfolio_state.get("holdings"), dict) else {}
        quantity = holdings.get(symbol, 0)
        held = isinstance(quantity, (int, float)) and not isinstance(quantity, bool) and quantity > 0
        expected_position = "HELD" if held else "NOT_HELD"
        if trader.get("position_status") != expected_position:
            errors.append("trader position status contradicts verified portfolio state")
        if live_record and record.get("portfolio_state_revision") != portfolio_state.get("state_revision"):
            errors.append("portfolio state revision mismatch")
    elif live_record:
        errors.append("live decision validation requires portfolio_state.json")
        expected_position = trader.get("position_status")
        held = expected_position == "HELD"
    else:
        expected_position = trader.get("position_status")
        held = expected_position == "HELD"
    allowed_actions = HELD_ACTIONS if held else NON_HELD_ACTIONS
    if trader_action not in allowed_actions:
        errors.append(f"{trader_action} is not allowed for position status {expected_position}")
    if manager.get("status") == "RESEARCH_REJECTED" and trader_action != "WAIT":
        errors.append("rejected research must map to WAIT")

    buy_review_requested = not held and trader_action in {"CONDITIONAL_BUY", "BUY_REVIEW"}
    if buy_review_requested and instrument.get("identity_status") == "user_supplied_pending_primary_verification":
        add_unique(warnings, "instrument identity is provisional and cannot pass a live new-buy gate")
    if buy_review_requested and (
        candidate.get("new_buy_approved") is not True
        or instrument.get("new_buy_instrument_approved") is not True
    ):
        add_unique(warnings, "watchlist approval is not new-buy approval")
    if not held and candidate.get("new_buy_approved") is not True:
        add_unique(warnings, "new buy is not approved for this candidate")

    risk = require_object(record.get("risk_review"), "risk_review", errors)
    if risk.get("order_authority") is not False or risk.get("may_upgrade") is not False:
        errors.append("risk controller authority is invalid")
    if risk.get("input_action") != trader_action:
        errors.append("risk review input action does not match trader action")
    risk_output = risk.get("output_action")
    verdict = risk.get("verdict")
    if risk_output not in ACTIONS:
        errors.append("risk output action is invalid")
        risk_output = "WAIT"
    if verdict == "ALLOW_REVIEW" and risk_output != trader_action:
        errors.append("ALLOW_REVIEW must preserve the trader action")
    elif verdict == "DOWNGRADE" and (
        risk_output == trader_action or not action_is_not_more_aggressive(trader_action, risk_output)
    ):
        errors.append("DOWNGRADE must produce a strictly less aggressive action")
    elif verdict == "VETO" and risk_output != "WAIT":
        errors.append("VETO must output WAIT")
    elif verdict not in {"ALLOW_REVIEW", "DOWNGRADE", "VETO"}:
        errors.append("risk verdict is invalid")

    portfolio = require_object(record.get("portfolio_decision"), "portfolio_decision", errors)
    portfolio_action = portfolio.get("action")
    if portfolio.get("quantity") is not None:
        errors.append("portfolio decision quantity must be null")
    if portfolio.get("order_authority") is not False:
        errors.append("portfolio decision must deny order authority")
    if portfolio.get("strategic_allocation_change") is not False:
        errors.append("tactical decision cannot change strategic allocation")
    if portfolio_action not in ACTIONS:
        errors.append("portfolio action is invalid")
        portfolio_action = "WAIT"
    if not action_is_not_more_aggressive(risk_output, portfolio_action):
        errors.append("portfolio manager upgraded the risk-reviewed action")
    if portfolio_action not in allowed_actions:
        errors.append(f"portfolio action {portfolio_action} is invalid for {expected_position}")
    for field in ("preferred_candidate", "alternative_candidate"):
        selected = portfolio.get(field)
        if selected is not None and selected not in candidates:
            errors.append(f"{field} is outside the tactical candidate universe")
    if (
        portfolio.get("preferred_candidate") is not None
        and portfolio.get("preferred_candidate") == portfolio.get("alternative_candidate")
    ):
        errors.append("preferred and alternative candidates must be distinct")

    final_action = record.get("final_action")
    if final_action != portfolio_action:
        errors.append("final_action must equal the portfolio decision action")
    if record.get("human_decision") == "ACCEPTED_FOR_MANUAL_REVIEW" and errors:
        errors.append("a rejected record cannot be accepted for manual review")
    conditions = (record.get("evaluation_plan") or {}).get("conditions")
    if not isinstance(conditions, list) or not conditions:
        errors.append("evaluation plan requires confirmation or invalidation conditions")
    else:
        condition_ids = [item.get("id") for item in conditions if isinstance(item, dict)]
        if len(condition_ids) != len(set(condition_ids)):
            errors.append("evaluation condition ids must be unique")
        invalidation_ids = set(trader.get("invalidation_condition_ids") or [])
        missing = sorted(invalidation_ids - set(condition_ids))
        if missing:
            errors.append("trader invalidation ids are absent from the evaluation plan: " + ", ".join(missing))

    if errors:
        computed_status = "REJECTED"
    elif warnings:
        computed_status = "WATCH_ONLY"
    else:
        computed_status = "ELIGIBLE_FOR_REVIEW"
    expected_gate_errors = list(errors)
    expected_gate_warnings = list(warnings)
    embedded_gate = require_object(record.get("deterministic_gate"), "deterministic_gate", errors)
    if embedded_gate.get("order_authority") is not False:
        errors.append("embedded deterministic gate must deny order authority")
    parse_datetime(embedded_gate.get("validated_at_utc"), "deterministic_gate.validated_at_utc", errors)
    if embedded_gate.get("status") != computed_status:
        errors.append(
            f"embedded deterministic gate status {embedded_gate.get('status')} does not match computed {computed_status}"
        )
        computed_status = "REJECTED"
    if embedded_gate.get("errors") != expected_gate_errors:
        errors.append("embedded deterministic gate errors do not match recomputation")
        computed_status = "REJECTED"
    if embedded_gate.get("warnings") != expected_gate_warnings:
        errors.append("embedded deterministic gate warnings do not match recomputation")
        computed_status = "REJECTED"
    if embedded_gate.get("status") == "REJECTED" and final_action != "WAIT":
        errors.append("a rejected deterministic gate must finalize as WAIT")
        computed_status = "REJECTED"
    if computed_status != "ELIGIBLE_FOR_REVIEW" and record.get("human_decision") == "ACCEPTED_FOR_MANUAL_REVIEW":
        errors.append("human acceptance is inconsistent with a non-eligible gate")
        computed_status = "REJECTED"
    if errors:
        computed_status = "REJECTED"

    return {
        "schema_version": "2.0",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_id": record.get("decision_id"),
        "symbol": symbol,
        "status": computed_status,
        "errors": errors,
        "warnings": warnings,
        "decision_record_sha256": canonical_sha256(record),
        "instrument_registry_sha256": canonical_sha256(registry),
        "tactical_universe_sha256": canonical_sha256(universe),
        "portfolio_state_sha256": canonical_sha256(portfolio_state) if portfolio_state else None,
        "order_authority": False,
        "order_status": "no order was placed or scheduled",
    }


def self_test() -> int:
    now = "2026-08-11T12:00:00+00:00"
    registry = {
        "registry_version": "test-registry",
        "instruments": {"TEST": {"identity_status": "verified", "watchlist_approved": True, "new_buy_instrument_approved": False, "short_sale_approved": False}},
    }
    universe = {
        "universe_version": "test-universe",
        "candidates": {"TEST": {"watchlist_approved": True, "new_buy_approved": False, "short_approved": False}},
    }
    evidence = [{
        "id": "E1", "retrieved_at_utc": now, "published_at_utc": now,
        "effective_at_utc": now, "actionable": True, "source_type": "primary",
        "contradiction_status": "NONE",
    }]
    analyst = lambda role: {"role": role, "claim_ids": ["E1"]}
    record = {
        "schema_version": "2.0", "decision_id": "D-TEST", "created_at_utc": now,
        "test_only": True, "symbol": "TEST", "instrument_registry_version": "test-registry",
        "tactical_universe_version": "test-universe", "portfolio_state_revision": None,
        "policy_version": "test", "order_authority": False, "record_locked": True,
        "research_packet": {
            "schema_version": "2.0", "symbol": "TEST", "analysis_cutoff_utc": now,
            "generated_at_utc": now, "analysis_kind": "TACTICAL_SELECTION", "evidence": evidence,
            "analyst_outputs": [analyst("identity_data_auditor"), analyst("bull_researcher"), analyst("bear_researcher")],
            "research_manager": {"role": "research_manager", "status": "RESEARCH_COMPLETE", "claim_ids": ["E1"]},
        },
        "trader_proposal": {"symbol": "TEST", "position_status": "NOT_HELD", "action": "WAIT", "quantity": None, "claim_ids": ["E1"], "invalidation_condition_ids": ["I1"], "order_authority": False},
        "risk_review": {"verdict": "ALLOW_REVIEW", "input_action": "WAIT", "output_action": "WAIT", "may_upgrade": False, "order_authority": False},
        "portfolio_decision": {"action": "WAIT", "quantity": None, "preferred_candidate": None, "alternative_candidate": None, "strategic_allocation_change": False, "order_authority": False},
        "deterministic_gate": {"status": "WATCH_ONLY", "validated_at_utc": now, "errors": [], "warnings": ["new buy is not approved for this candidate"], "order_authority": False},
        "final_action": "WAIT", "human_decision": "PENDING",
        "evaluation_plan": {"conditions": [{"id": "I1", "kind": "INVALIDATION", "description": "test"}]},
    }
    result = validate_record(record, registry, universe)
    if result["status"] != "WATCH_ONLY" or result["errors"]:
        print(json.dumps(result, indent=2))
        return 2
    record["trader_proposal"]["action"] = "STOP_REVIEW"
    rejected = validate_record(record, registry, universe)
    if rejected["status"] != "REJECTED":
        print(json.dumps(rejected, indent=2))
        return 2
    print("validate_decision_record self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--universe", type=Path)
    parser.add_argument("--portfolio-state", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.record or not args.registry or not args.universe:
        parser.error("--record, --registry, and --universe are required")
    try:
        result = validate_record(
            read_json(args.record),
            read_json(args.registry),
            read_json(args.universe),
            read_json(args.portfolio_state) if args.portfolio_state else None,
        )
    except ValidationFailure as exc:
        print(f"DECISION_VALIDATION_ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] != "REJECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
