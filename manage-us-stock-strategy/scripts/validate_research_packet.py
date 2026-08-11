#!/usr/bin/env python3
"""Validate an LLM research packet before deterministic alert evaluation.

This validator never authorizes or places a trade. It checks structure,
point-in-time evidence, portfolio state, cash, holdings, leverage approval, and
policy references. A successful result is only eligible for the separate alert
engine and human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import uuid
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class PacketError(RuntimeError):
    pass


ALLOWED_ACTIONS = {"buy", "sell", "reduce", "hold", "watch"}
ALLOWED_STANCES = {"bullish", "neutral", "bearish", "veto", "not_applicable"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_SOURCE_TYPES = {
    "primary",
    "market_data",
    "secondary",
    "social",
    "user_provided_unverified",
}
ALLOWED_INSTRUMENT_TYPES = {"stock", "spot_etf", "leveraged_etf", "inverse_etf"}
ALLOWED_QUANTITY_AUTHORITIES = {"none", "fixed"}
VALIDATOR_SCHEMA_VERSION = "1.1"
DEFAULT_REQUIRED_ROLES = {
    "live_new_buy": [
        "identity_data_auditor",
        "fundamental_valuation_analyst",
        "market_technical_analyst",
        "news_macro_analyst",
        "bull_researcher",
        "bear_researcher",
        "risk_controller",
        "synthesizer",
    ],
    "holding_risk": [
        "identity_data_auditor",
        "market_technical_analyst",
        "bear_researcher",
        "risk_controller",
        "synthesizer",
    ],
    "report_validation": [
        "identity_data_auditor",
        "fundamental_valuation_analyst",
        "news_macro_analyst",
        "bull_researcher",
        "bear_researcher",
        "risk_controller",
        "synthesizer",
    ],
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PacketError(f"top-level JSON must be an object: {path}")
    return value


def parse_dt(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PacketError(f"missing {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PacketError(f"invalid {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise PacketError(f"{field} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise PacketError(f"missing {field}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PacketError(f"invalid {field}: {value}") from exc


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def valid_symbol(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Z0-9.^=\-]{1,24}", value) is not None


def valid_source_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    if parsed.scheme == "https":
        return bool(parsed.netloc)
    if parsed.scheme == "artifact":
        return bool(parsed.netloc or parsed.path)
    return False


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fingerprint(
    packet: dict[str, Any],
    policy: dict[str, Any],
    state: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, str]:
    hashes = {
        "packet_hash": canonical_sha256(packet),
        "policy_hash": canonical_sha256(policy),
        "state_hash": canonical_sha256(state),
        "snapshot_hash": canonical_sha256(snapshot),
    }
    hashes["fingerprint"] = canonical_sha256(hashes)
    return hashes


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_cli_paths(args: argparse.Namespace) -> None:
    inputs = {
        "packet": args.packet.resolve(),
        "state": args.state.resolve(),
        "policy": args.policy.resolve(),
        "snapshot": args.snapshot.resolve(),
    }
    if len(set(inputs.values())) != len(inputs):
        raise PacketError("packet, state, policy, and snapshot must be different files")
    if args.output is None:
        return
    if args.output.suffix.lower() != ".md":
        raise PacketError("--output must use a .md suffix")
    output = args.output.resolve()
    output_json = args.output.with_suffix(".json").resolve()
    protected = set(inputs.values())
    if output in protected or output_json in protected:
        raise PacketError("output files must not alias packet, state, policy, or snapshot")
    if output == output_json:
        raise PacketError("markdown and JSON output paths must be different")


def get_required_roles(packet: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    mode = str(packet.get("mode", ""))
    configured = ((policy.get("decision_harness") or {}).get("required_roles_by_mode") or {}).get(mode)
    if isinstance(configured, list) and configured:
        return [str(item) for item in configured]
    return DEFAULT_REQUIRED_ROLES.get(mode, [])


def validate_packet(
    packet: dict[str, Any],
    state: dict[str, Any],
    policy: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    hard_gates: list[str] = []
    now_utc = datetime.now(timezone.utc)
    future_timestamp_tolerance = now_utc + timedelta(minutes=5)
    harness = policy.get("decision_harness") or {}

    schema_contract = harness.get("schema_contract")
    if not isinstance(schema_contract, dict):
        errors.append("decision harness schema contract is missing")
        schema_contract = {}
    schema_values = {
        "research_packet": packet.get("schema_version"),
        "portfolio_state": state.get("schema_version"),
        "alert_policy": policy.get("schema_version"),
        "market_snapshot": snapshot.get("schema_version"),
    }
    for name, actual in schema_values.items():
        expected = schema_contract.get(name)
        if not isinstance(expected, str) or not expected:
            errors.append(f"schema contract has no version for {name}")
        elif actual != expected:
            errors.append(f"{name} schema version {actual!r} does not match {expected!r}")

    if harness.get("llm_output_is_untrusted_input") is not True:
        errors.append("decision harness must treat LLM output as untrusted input")
    if harness.get("validator_can_place_or_approve_orders") is not False:
        errors.append("decision harness must explicitly forbid validator order authority")
    if harness.get("packet_to_candidate_adapter_enabled") is not False:
        errors.append("research-packet-to-candidate adapters must remain disabled")
    if harness.get("maximum_validator_grade") != "B":
        errors.append("decision harness maximum validator grade must be B")
    if not isinstance(packet.get("analysis_id"), str) or not packet.get(
        "analysis_id", ""
    ).strip():
        errors.append("analysis_id is missing")
    if packet.get("analysis_kind") not in {"live", "historical"}:
        errors.append("analysis_kind must be live or historical")

    if packet.get("strategy_version") != state.get("strategy_version"):
        errors.append("packet and state strategy versions do not match")
    if policy.get("strategy_version") != state.get("strategy_version"):
        errors.append("policy and state strategy versions do not match")
    if packet.get("state_revision") != state.get("state_revision"):
        errors.append("packet state revision is stale or mismatched")

    try:
        cutoff = parse_dt(packet.get("analysis_cutoff_utc"), "analysis_cutoff_utc")
    except PacketError as exc:
        errors.append(str(exc))
        cutoff = None

    try:
        packet_generated_at = parse_dt(
            packet.get("generated_at_utc"), "packet generated_at_utc"
        )
        if packet_generated_at > future_timestamp_tolerance:
            errors.append("research packet generation timestamp is in the future")
        if cutoff is not None and packet_generated_at < cutoff:
            errors.append("research packet was generated before its analysis cutoff")
    except PacketError as exc:
        errors.append(str(exc))
        packet_generated_at = None

    if cutoff is not None and packet.get("analysis_kind") == "live":
        maximum_packet_age_hours = harness.get(
            "maximum_live_packet_age_hours",
            policy.get("maximum_snapshot_age_hours", 18),
        )
        if not finite(maximum_packet_age_hours) or float(maximum_packet_age_hours) <= 0:
            errors.append("maximum live packet age must be a positive finite number")
        else:
            packet_age_hours = (now_utc - cutoff).total_seconds() / 3600
            if packet_age_hours < -(5 / 60):
                errors.append("live packet analysis cutoff is in the future")
            elif packet_age_hours > float(maximum_packet_age_hours):
                errors.append("live research packet is stale")
            if packet_generated_at is not None:
                generated_age_hours = (
                    now_utc - packet_generated_at
                ).total_seconds() / 3600
                if generated_age_hours > float(maximum_packet_age_hours):
                    errors.append("live research packet generation is stale")

    session = snapshot.get("session") or {}
    session_date = session.get("us_session_date")
    try:
        parse_date(session_date, "snapshot U.S. session date")
        parse_date(packet.get("analysis_session_date"), "packet analysis session date")
    except PacketError as exc:
        errors.append(str(exc))
    if packet.get("analysis_session_date") != session_date:
        errors.append("packet and market snapshot session dates do not match")
    if session.get("exchange_timezone") != policy.get("exchange_timezone"):
        errors.append("snapshot exchange timezone does not match policy")
    if session.get("is_trading_day") is not True:
        errors.append("snapshot is not a verified trading day")
    if not session.get("regular_session_complete"):
        errors.append("market snapshot is not a completed regular session")
    if not session.get("official_calendar_verified"):
        errors.append("official exchange calendar is not verified")
    if session.get("calendar_verification_status") != "verified_trading_day":
        errors.append("calendar verification status is not verified_trading_day")
    if session.get("calendar_source_type") != "official_exchange_or_regulator":
        errors.append("calendar source type is not authoritative")
    if not isinstance(session.get("calendar_source"), str) or not session.get(
        "calendar_source", ""
    ).strip():
        errors.append("authoritative calendar source is missing")
    if session.get("expected_us_session_date") != session_date:
        errors.append("snapshot session does not match the authoritative expected session")

    generated_at = None
    verified_at = None
    try:
        generated_at = parse_dt(snapshot.get("generated_at_utc"), "snapshot generated_at_utc")
        verified_at = parse_dt(
            session.get("calendar_verified_at_utc"), "calendar_verified_at_utc"
        )
        maximum_snapshot_age_hours = policy.get("maximum_snapshot_age_hours", 18)
        if not finite(maximum_snapshot_age_hours) or float(maximum_snapshot_age_hours) <= 0:
            errors.append("maximum snapshot age must be a positive finite number")
        else:
            for label, timestamp in (
                ("market snapshot", generated_at),
                ("calendar verification", verified_at),
            ):
                age_hours = (now_utc - timestamp).total_seconds() / 3600
                if age_hours < -(5 / 60) or age_hours > float(maximum_snapshot_age_hours):
                    errors.append(f"{label} is stale or implausibly future-dated")
        if verified_at < generated_at:
            errors.append("calendar verification predates snapshot generation")
        if (verified_at - generated_at).total_seconds() > 86400:
            errors.append("calendar verification is too far removed from snapshot generation")
    except PacketError as exc:
        errors.append(str(exc))

    if (
        cutoff is not None
        and generated_at is not None
        and packet.get("analysis_kind") == "live"
        and cutoff < generated_at
    ):
        errors.append("live packet cutoff predates its market snapshot")

    broker_snapshot = state.get("last_confirmed_broker_snapshot") or {}
    if broker_snapshot.get("verified") is not True:
        errors.append("portfolio state is not tied to a verified broker or user snapshot")
    if broker_snapshot.get("holdings_complete") is not True:
        errors.append("verified holdings snapshot is not complete")
    if not isinstance(broker_snapshot.get("source"), str) or not broker_snapshot.get(
        "source", ""
    ).strip():
        errors.append("verified holdings snapshot source is missing")
    try:
        broker_as_of = parse_date(broker_snapshot.get("as_of"), "broker snapshot as_of")
        expected_session = parse_date(session_date, "snapshot U.S. session date")
        maximum_broker_age = int(policy.get("broker_snapshot_max_age_calendar_days", 4))
        broker_age = (expected_session - broker_as_of).days
        if broker_age > maximum_broker_age:
            errors.append("verified holdings snapshot is stale")
        if broker_age < -1:
            errors.append("verified holdings snapshot is implausibly later than session")
    except (PacketError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    proposal = packet.get("proposal")
    if not isinstance(proposal, dict):
        errors.append("proposal object is missing")
        proposal = {}
    symbol = proposal.get("symbol")
    action = str(proposal.get("action", "")).lower()
    if not valid_symbol(symbol):
        errors.append("proposal symbol is not a normalized exact ticker")
    if action not in ALLOWED_ACTIONS:
        errors.append("proposal action is invalid")

    symbols = snapshot.get("symbols") or {}
    row = symbols.get(symbol) if valid_symbol(symbol) else None
    if not isinstance(row, dict):
        errors.append(f"market snapshot is missing proposed symbol {symbol}")
    else:
        if row.get("bar_date") != session_date:
            errors.append(f"{symbol} bar date does not match the completed session")
        if not finite(row.get("close")):
            errors.append(f"{symbol} completed close is missing")
        if row.get("corporate_action_unresolved"):
            errors.append(f"{symbol} has an unresolved corporate action")

    evidence = packet.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence ledger is missing or empty")
        evidence = []
    evidence_ids: set[str] = set()
    evidence_by_id: dict[str, dict[str, Any]] = {}
    historical = packet.get("analysis_kind") == "historical"
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"evidence[{index}] is not an object")
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append(f"evidence[{index}] has no id")
            continue
        if evidence_id in evidence_ids:
            errors.append(f"duplicate evidence id {evidence_id}")
        evidence_ids.add(evidence_id)
        evidence_by_id[evidence_id] = item
        if not isinstance(item.get("claim"), str) or not item.get("claim", "").strip():
            errors.append(f"{evidence_id} has no claim")
        if item.get("source_type") not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{evidence_id} has an invalid source_type")
        if item.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{evidence_id} has invalid confidence")
        if not valid_source_url(item.get("source_url")):
            errors.append(f"{evidence_id} has no valid https or artifact source")
        published_value = item.get("published_at_utc")
        if not published_value:
            message = f"{evidence_id} has no publication timestamp"
            (errors if historical else warnings).append(message)
        elif cutoff is not None:
            try:
                published = parse_dt(published_value, f"{evidence_id}.published_at_utc")
                if published > cutoff:
                    errors.append(f"{evidence_id} is look-ahead evidence published after cutoff")
            except PacketError as exc:
                errors.append(str(exc))
        effective_value = item.get("effective_at_utc")
        if effective_value and cutoff is not None:
            try:
                effective = parse_dt(effective_value, f"{evidence_id}.effective_at_utc")
                if effective > cutoff:
                    errors.append(f"{evidence_id} became effective after cutoff")
            except PacketError as exc:
                errors.append(str(exc))
        try:
            retrieved = parse_dt(item.get("retrieved_at_utc"), f"{evidence_id}.retrieved_at_utc")
            if retrieved > future_timestamp_tolerance:
                warnings.append(f"{evidence_id} retrieval timestamp is in the future")
        except PacketError as exc:
            errors.append(str(exc))

    roles = packet.get("roles")
    if not isinstance(roles, dict):
        errors.append("roles object is missing")
        roles = {}
    required_roles = get_required_roles(packet, policy)
    if not required_roles:
        errors.append(f"unsupported packet mode {packet.get('mode')}")
    for role_name in required_roles:
        role = roles.get(role_name)
        if not isinstance(role, dict):
            errors.append(f"required role {role_name} is missing")
            continue
        if role.get("stance") not in ALLOWED_STANCES:
            errors.append(f"{role_name} has an invalid stance")
        if role.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{role_name} has invalid confidence")
        if not isinstance(role.get("summary"), str) or not role.get("summary", "").strip():
            errors.append(f"{role_name} has no summary")
        claim_ids = role.get("claim_ids")
        if not isinstance(claim_ids, list):
            errors.append(f"{role_name} claim_ids must be a list")
            continue
        missing = sorted(set(map(str, claim_ids)) - evidence_ids)
        if missing:
            errors.append(f"{role_name} references unknown claims: {', '.join(missing)}")
        unknowns = role.get("unknowns")
        if not isinstance(unknowns, list) or any(
            not isinstance(item, str) for item in unknowns
        ):
            errors.append(f"{role_name} unknowns must be a list of strings")

    configured_source_types = (
        harness.get("required_source_types_by_mode") or {}
    ).get(str(packet.get("mode", "")))
    if not isinstance(configured_source_types, list) or not configured_source_types:
        errors.append(f"required source tiers are not configured for mode {packet.get('mode')}")
        configured_source_types = []
    else:
        invalid_required_types = sorted(
            set(map(str, configured_source_types)) - ALLOWED_SOURCE_TYPES
        )
        if invalid_required_types:
            errors.append(
                "decision harness contains invalid required source types: "
                + ", ".join(invalid_required_types)
            )

    proposal_claims = proposal.get("claim_ids")
    if not isinstance(proposal_claims, list) or not proposal_claims:
        warnings.append("proposal has no evidence claim_ids")
        if configured_source_types:
            hard_gates.append(
                "proposal lacks required evidence source tiers: "
                + ", ".join(sorted(set(map(str, configured_source_types))))
            )
    else:
        missing = sorted(set(map(str, proposal_claims)) - evidence_ids)
        if missing:
            errors.append(f"proposal references unknown claims: {', '.join(missing)}")
        proposal_source_types = {
            evidence_by_id[claim_id].get("source_type")
            for claim_id in map(str, proposal_claims)
            if claim_id in evidence_by_id
        }
        if configured_source_types:
            missing_source_types = sorted(
                set(map(str, configured_source_types)) - proposal_source_types
            )
            if missing_source_types:
                hard_gates.append(
                    "proposal lacks required evidence source tiers: "
                    + ", ".join(missing_source_types)
                )

    holdings = state.get("holdings") or {}
    current_shares = holdings.get(symbol, 0) if valid_symbol(symbol) else 0
    if not isinstance(current_shares, int) or isinstance(current_shares, bool) or current_shares < 0:
        errors.append(f"verified holding for {symbol} is invalid")
        current_shares = 0

    quantity = proposal.get("quantity")
    quantity_valid = isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0
    if action in {"buy", "sell", "reduce"} and not quantity_valid:
        hard_gates.append("positive integer quantity is not supplied")
    if action in {"sell", "reduce"} and quantity_valid and quantity > current_shares:
        errors.append("proposed sale exceeds verified holdings")
    if action in {"hold", "watch"} and quantity not in (None, 0):
        warnings.append("hold/watch proposal quantity is ignored")

    instrument_registry = harness.get("instrument_registry") or {}
    instrument = instrument_registry.get(symbol) if valid_symbol(symbol) else None
    effective_instrument_type = None
    if not isinstance(instrument, dict):
        hard_gates.append("instrument is not present in the deterministic policy registry")
    else:
        effective_instrument_type = instrument.get("instrument_type")
        if effective_instrument_type not in ALLOWED_INSTRUMENT_TYPES:
            errors.append("policy instrument registry contains an invalid instrument type")
        if instrument.get("identity_status") != "verified":
            hard_gates.append("instrument identity is not verified in policy")
        proposed_instrument_type = proposal.get("instrument_type")
        if (
            proposed_instrument_type is not None
            and proposed_instrument_type != effective_instrument_type
        ):
            errors.append("LLM-proposed instrument type conflicts with deterministic policy")

    registry = harness.get("approved_rule_registry") or {}
    rule_id = proposal.get("policy_rule_id")
    rule = registry.get(rule_id) if isinstance(rule_id, str) else None
    if action not in {"hold", "watch"}:
        if not isinstance(rule, dict):
            hard_gates.append("proposal does not reference an approved deterministic rule")
        else:
            if rule.get("status") != "approved":
                hard_gates.append("referenced deterministic rule is not approved")
            if rule.get("symbol") != symbol:
                errors.append("referenced rule symbol does not match proposal")
            allowed_sides = rule.get("allowed_actions") or [rule.get("side")]
            if action not in allowed_sides:
                errors.append("referenced rule does not allow the proposed action")
            quantity_authority = rule.get("quantity_authority")
            if quantity_authority not in ALLOWED_QUANTITY_AUTHORITIES:
                errors.append("referenced rule has invalid or missing quantity authority")
            elif quantity_authority == "none":
                hard_gates.append("referenced rule authorizes review but no trade quantity")
            elif quantity_authority == "fixed":
                approved_quantity = rule.get("approved_quantity")
                if not (
                    isinstance(approved_quantity, int)
                    and not isinstance(approved_quantity, bool)
                    and approved_quantity > 0
                ):
                    errors.append("fixed-quantity rule has no valid approved quantity")
                elif not quantity_valid or quantity != approved_quantity:
                    hard_gates.append(
                        f"proposal quantity does not match approved fixed quantity {approved_quantity}"
                    )

    if action == "buy":
        state_cash = state.get("available_cash_usd")
        snapshot_cash = (snapshot.get("account") or {}).get("available_cash_usd")
        if broker_snapshot.get("cash_verified") is not True:
            hard_gates.append("available cash is not verified by the broker or user snapshot")
        if not finite(state_cash) or not finite(snapshot_cash):
            hard_gates.append("verified available cash is missing")
        elif abs(float(state_cash) - float(snapshot_cash)) > 0.01:
            errors.append("state and snapshot available cash do not match")
        elif float(state_cash) <= 0:
            hard_gates.append("verified available cash is zero")
        if quantity_valid and isinstance(row, dict) and finite(row.get("close")) and finite(state_cash):
            if quantity * float(row["close"]) > float(state_cash) + 0.01:
                hard_gates.append("proposed buy exceeds verified available cash")

    if action == "buy" and (
        not isinstance(instrument, dict)
        or instrument.get("new_buy_instrument_approved") is not True
    ):
        hard_gates.append("exact instrument is not approved for new purchase")

    risk_positions = ((policy.get("holding_risk_rules") or {}).get("positions") or {})
    average_costs = state.get("average_cost_usd") or {}
    risk_breaches: list[str] = []
    risk_boundaries: dict[str, float] = {}
    for held_symbol, held_shares in holdings.items():
        if (
            isinstance(held_shares, int)
            and not isinstance(held_shares, bool)
            and held_shares > 0
        ):
            held_instrument = instrument_registry.get(held_symbol)
            held_type = (
                held_instrument.get("instrument_type")
                if isinstance(held_instrument, dict)
                else None
            )
            if held_type in {"leveraged_etf", "inverse_etf"} and held_symbol not in risk_positions:
                errors.append(
                    f"held leveraged or inverse symbol {held_symbol} has no approved risk inputs"
                )
    for held_symbol, risk_rule in risk_positions.items():
        held_shares = holdings.get(held_symbol, 0)
        if not isinstance(held_shares, int) or isinstance(held_shares, bool) or held_shares < 0:
            errors.append(f"verified holding for risk-managed symbol {held_symbol} is invalid")
            continue
        if held_shares == 0:
            continue
        held_row = symbols.get(held_symbol)
        if not isinstance(held_row, dict):
            errors.append(f"held risk-managed symbol {held_symbol} is missing from snapshot")
            continue
        if held_row.get("bar_date") != session_date:
            errors.append(f"held risk-managed symbol {held_symbol} has a mismatched bar date")
        if held_row.get("corporate_action_unresolved"):
            errors.append(f"held risk-managed symbol {held_symbol} has an unresolved corporate action")
        average_cost = average_costs.get(held_symbol)
        max_loss = (
            risk_rule.get("maximum_loss_fraction_from_average_cost")
            if isinstance(risk_rule, dict)
            else None
        )
        if not finite(held_row.get("close")) or float(held_row.get("close", 0)) <= 0:
            errors.append(f"held risk-managed symbol {held_symbol} has no valid completed close")
            continue
        if not finite(average_cost) or float(average_cost) <= 0:
            errors.append(f"held risk-managed symbol {held_symbol} has no valid average cost")
            continue
        if not finite(max_loss) or not 0 < float(max_loss) < 1:
            errors.append(f"held risk-managed symbol {held_symbol} has no valid loss rule")
            continue
        boundary = float(average_cost) * (1 - float(max_loss))
        risk_boundaries[held_symbol] = boundary
        if float(held_row["close"]) <= boundary:
            risk_breaches.append(held_symbol)
    risk_policy = policy.get("holding_risk_rules") or {}
    freeze_new_buys = risk_policy.get(
        "freeze_new_buy_candidates_on_any_breach",
        risk_policy.get("freeze_new_buys_on_any_breach", True),
    )
    if action == "buy" and risk_breaches and freeze_new_buys:
        hard_gates.append(f"held-position risk breach freezes new buys: {', '.join(risk_breaches)}")

    status = "eligible_for_alert_engine"
    max_grade = "B"
    if errors:
        status = "rejected"
        max_grade = "F"
    elif action in {"hold", "watch"} or hard_gates or warnings:
        status = "watch_only"
        max_grade = "B" if action != "hold" else "E"

    hashes = fingerprint(packet, policy, state, snapshot)
    return {
        "schema_version": VALIDATOR_SCHEMA_VERSION,
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_id": packet.get("analysis_id"),
        "symbol": symbol,
        "action": action,
        "status": status,
        "maximum_alert_grade": max_grade,
        "errors": errors,
        "warnings": warnings,
        "hard_gates": hard_gates,
        "risk_breaches": risk_breaches,
        "risk_boundaries": risk_boundaries,
        "current_verified_shares": current_shares,
        "proposed_quantity": quantity if quantity_valid else None,
        "effective_instrument_type": effective_instrument_type,
        "strategy_version": state.get("strategy_version"),
        "state_revision": state.get("state_revision"),
        **hashes,
        "packet_can_create_candidate": False,
        "candidate_adapter_status": "disabled; alert candidates are rebuilt only from approved policy",
        "next_step": (
            "stop and correct the packet"
            if status == "rejected"
            else "research/watch only; resolve every hard gate"
            if status == "watch_only"
            else (
                "run the deterministic alert evaluator independently from state, policy, and snapshot; "
                "do not copy packet fields into a candidate"
            )
        ),
        "order_status": "no order was placed or scheduled",
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# Research packet: {result['status']}",
        "",
        f"- Symbol / action: {result.get('symbol')} / {result.get('action')}",
        f"- Maximum alert grade: {result.get('maximum_alert_grade')}",
        f"- Strategy / state revision: {result.get('strategy_version')} / {result.get('state_revision')}",
        f"- Verified shares / proposed quantity: {result.get('current_verified_shares')} / {result.get('proposed_quantity')}",
        f"- Fingerprint: {result.get('fingerprint')}",
        f"- Policy hash: {result.get('policy_hash')}",
        f"- Snapshot hash: {result.get('snapshot_hash')}",
        f"- Candidate adapter: {result.get('candidate_adapter_status')}",
    ]
    for title, key in (("Errors", "errors"), ("Hard gates", "hard_gates"), ("Warnings", "warnings")):
        values = result.get(key) or []
        if values:
            lines.extend(["", f"## {title}", ""])
            lines.extend(f"- {value}" for value in values)
    lines.extend([
        "",
        f"Next step: {result.get('next_step')}",
        "",
        "No order was placed or scheduled. This validator cannot approve a trade or create an alert candidate.",
    ])
    return "\n".join(lines)


def self_test() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    state = {
        "schema_version": "1.2",
        "strategy_version": "test-v1",
        "state_revision": 7,
        "holdings": {"AAA": 10, "LEV": 0},
        "average_cost_usd": {"AAA": 100.0},
        "available_cash_usd": 0.0,
        "last_confirmed_broker_snapshot": {
            "verified": True,
            "holdings_complete": True,
            "cash_verified": True,
            "source": "self-test",
            "as_of": "2026-07-30",
        },
    }
    policy = {
        "schema_version": "1.2",
        "strategy_version": "test-v1",
        "exchange_timezone": "America/New_York",
        "maximum_snapshot_age_hours": 18,
        "broker_snapshot_max_age_calendar_days": 4,
        "decision_harness": {
            "schema_contract": {
                "research_packet": "1.1",
                "portfolio_state": "1.2",
                "alert_policy": "1.2",
                "market_snapshot": "1.0",
            },
            "llm_output_is_untrusted_input": True,
            "validator_can_place_or_approve_orders": False,
            "packet_to_candidate_adapter_enabled": False,
            "maximum_validator_grade": "B",
            "maximum_live_packet_age_hours": 18,
            "required_roles_by_mode": {
                "holding_risk": DEFAULT_REQUIRED_ROLES["holding_risk"],
            },
            "required_source_types_by_mode": {"holding_risk": ["market_data"]},
            "instrument_registry": {
                "AAA": {
                    "instrument_type": "stock",
                    "identity_status": "verified",
                    "watchlist_approved": True,
                    "new_buy_instrument_approved": False,
                },
                "LEV": {
                    "instrument_type": "leveraged_etf",
                    "identity_status": "verified",
                    "watchlist_approved": True,
                    "new_buy_instrument_approved": False,
                },
            },
            "approved_rule_registry": {
                "aaa_reduce": {
                    "status": "approved",
                    "symbol": "AAA",
                    "allowed_actions": ["reduce", "sell"],
                    "quantity_authority": "fixed",
                    "approved_quantity": 5,
                },
                "aaa_review_only": {
                    "status": "approved",
                    "symbol": "AAA",
                    "allowed_actions": ["reduce", "sell"],
                    "quantity_authority": "none",
                },
            },
        },
        "holding_risk_rules": {
            "freeze_new_buy_candidates_on_any_breach": True,
            "positions": {
                "AAA": {"maximum_loss_fraction_from_average_cost": 0.20},
            },
        },
    }
    snapshot = {
        "schema_version": "1.0",
        "generated_at_utc": now.isoformat(),
        "session": {
            "exchange_timezone": "America/New_York",
            "us_session_date": "2026-07-30",
            "expected_us_session_date": "2026-07-30",
            "is_trading_day": True,
            "regular_session_complete": True,
            "official_calendar_verified": True,
            "calendar_verification_status": "verified_trading_day",
            "calendar_source_type": "official_exchange_or_regulator",
            "calendar_source": "https://example.test/official-calendar",
            "calendar_verified_at_utc": now.isoformat(),
        },
        "account": {"available_cash_usd": 0.0},
        "symbols": {
            "AAA": {
                "bar_date": "2026-07-30",
                "close": 90.0,
                "corporate_action_unresolved": False,
            },
            "LEV": {
                "bar_date": "2026-07-30",
                "close": 20.0,
                "corporate_action_unresolved": False,
            },
        },
    }
    role = {
        "stance": "neutral",
        "confidence": "medium",
        "summary": "Grounded test role.",
        "claim_ids": ["E1"],
        "unknowns": [],
    }
    packet = {
        "schema_version": "1.1",
        "mode": "holding_risk",
        "analysis_kind": "live",
        "analysis_id": "test-1",
        "strategy_version": "test-v1",
        "state_revision": 7,
        "analysis_cutoff_utc": now.isoformat(),
        "generated_at_utc": now.isoformat(),
        "analysis_session_date": "2026-07-30",
        "evidence": [{
            "id": "E1",
            "claim": "Verified test claim",
            "source_url": "https://example.test/source",
            "source_type": "market_data",
            "published_at_utc": now.isoformat(),
            "retrieved_at_utc": now.isoformat(),
            "effective_at_utc": now.isoformat(),
            "confidence": "high",
        }],
        "roles": {name: deepcopy(role) for name in DEFAULT_REQUIRED_ROLES["holding_risk"]},
        "proposal": {
            "symbol": "AAA",
            "action": "reduce",
            "quantity": 5,
            "policy_rule_id": "aaa_reduce",
            "claim_ids": ["E1"],
            "instrument_type": "stock",
        },
    }
    valid = validate_packet(packet, state, policy, snapshot)
    assert valid["status"] == "eligible_for_alert_engine", valid
    assert valid["packet_can_create_candidate"] is False
    assert len(valid["policy_hash"]) == 64
    assert len(valid["snapshot_hash"]) == 64
    assert len(valid["fingerprint"]) == 64

    future = deepcopy(packet)
    future["evidence"][0]["published_at_utc"] = "2099-01-01T00:00:00+00:00"
    assert validate_packet(future, state, policy, snapshot)["status"] == "rejected"

    too_many = deepcopy(packet)
    too_many["proposal"]["quantity"] = 11
    assert validate_packet(too_many, state, policy, snapshot)["status"] == "rejected"

    buy = deepcopy(packet)
    buy["proposal"] = {
        "symbol": "LEV",
        "action": "buy",
        "quantity": 1,
        "policy_rule_id": "missing",
        "claim_ids": ["E1"],
        "instrument_type": "leveraged_etf",
    }
    buy_result = validate_packet(buy, state, policy, snapshot)
    assert buy_result["status"] == "watch_only", buy_result
    assert "verified available cash is zero" in buy_result["hard_gates"]
    assert "exact instrument is not approved for new purchase" in buy_result["hard_gates"]

    watchlist_only_stock_buy = deepcopy(packet)
    watchlist_only_stock_buy["proposal"] = {
        "symbol": "AAA",
        "action": "buy",
        "quantity": 5,
        "policy_rule_id": "missing",
        "claim_ids": ["E1"],
        "instrument_type": "stock",
    }
    watchlist_result = validate_packet(
        watchlist_only_stock_buy, state, policy, snapshot
    )
    assert "exact instrument is not approved for new purchase" in watchlist_result[
        "hard_gates"
    ]

    disguised = deepcopy(buy)
    disguised["proposal"]["instrument_type"] = "stock"
    disguised_result = validate_packet(disguised, state, policy, snapshot)
    assert disguised_result["status"] == "rejected"
    assert disguised_result["effective_instrument_type"] == "leveraged_etf"

    review_only = deepcopy(packet)
    review_only["proposal"]["policy_rule_id"] = "aaa_review_only"
    review_only_result = validate_packet(review_only, state, policy, snapshot)
    assert review_only_result["status"] == "watch_only"
    assert "referenced rule authorizes review but no trade quantity" in review_only_result["hard_gates"]

    missing_risk_input = deepcopy(snapshot)
    missing_risk_input["symbols"]["AAA"]["close"] = None
    assert validate_packet(packet, state, policy, missing_risk_input)["status"] == "rejected"

    weak_sources = deepcopy(packet)
    weak_sources["evidence"][0]["source_type"] = "social"
    weak_result = validate_packet(weak_sources, state, policy, snapshot)
    assert weak_result["status"] == "watch_only"
    assert "proposal lacks required evidence source tiers: market_data" in weak_result["hard_gates"]

    bad_schema = deepcopy(packet)
    bad_schema["schema_version"] = "0.9"
    assert validate_packet(bad_schema, state, policy, snapshot)["status"] == "rejected"

    stale_packet_generation = deepcopy(packet)
    stale_packet_generation["generated_at_utc"] = "2026-07-01T00:00:00+00:00"
    assert validate_packet(
        stale_packet_generation, state, policy, snapshot
    )["status"] == "rejected"

    missing_leveraged_risk_rule = deepcopy(state)
    missing_leveraged_risk_rule["holdings"]["LEV"] = 1
    missing_leveraged_risk_result = validate_packet(
        packet, missing_leveraged_risk_rule, policy, snapshot
    )
    assert missing_leveraged_risk_result["status"] == "rejected"

    stale_snapshot = deepcopy(snapshot)
    stale_time = datetime(2026, 7, 1, tzinfo=timezone.utc).isoformat()
    stale_snapshot["generated_at_utc"] = stale_time
    stale_snapshot["session"]["calendar_verified_at_utc"] = stale_time
    assert validate_packet(packet, state, policy, stale_snapshot)["status"] == "rejected"

    policy_changed = deepcopy(policy)
    policy_changed["decision_harness"]["policy_note"] = "changed"
    assert validate_packet(packet, state, policy_changed, snapshot)["fingerprint"] != valid["fingerprint"]
    snapshot_changed = deepcopy(snapshot)
    snapshot_changed["symbols"]["AAA"]["close"] = 91.0
    assert validate_packet(packet, state, policy, snapshot_changed)["fingerprint"] != valid["fingerprint"]

    stale = deepcopy(packet)
    stale["state_revision"] = 6
    assert validate_packet(stale, state, policy, snapshot)["status"] == "rejected"

    assert valid_source_url("artifact:") is False
    self_test_root = Path(
        os.environ.get("RESEARCH_VALIDATOR_TEST_TMPDIR", str(Path.cwd()))
    ).resolve()
    self_test_root.mkdir(parents=True, exist_ok=True)
    root = self_test_root / (
        f".research-validator-selftest-{os.getpid()}-{uuid.uuid4().hex}"
    )
    root.mkdir(exist_ok=False)
    cleanup_names = (
        "packet.json",
        "state.json",
        "policy.json",
        "snapshot.json",
        "state.md",
        "report.txt",
        "report.md",
        "report.json",
    )
    try:
        packet_path = root / "packet.json"
        state_path = root / "state.json"
        policy_path = root / "policy.json"
        snapshot_path = root / "snapshot.json"
        for path in (packet_path, state_path, policy_path, snapshot_path):
            path.write_text("{}", encoding="utf-8")
        alias_args = argparse.Namespace(
            packet=packet_path,
            state=state_path,
            policy=policy_path,
            snapshot=snapshot_path,
            output=root / "state.md",
        )
        try:
            validate_cli_paths(alias_args)
            raise AssertionError("JSON output alias should fail")
        except PacketError:
            pass
        invalid_suffix_args = deepcopy(alias_args)
        invalid_suffix_args.output = root / "report.txt"
        try:
            validate_cli_paths(invalid_suffix_args)
            raise AssertionError("non-markdown output should fail")
        except PacketError:
            pass
        safe_args = deepcopy(alias_args)
        safe_args.output = root / "report.md"
        validate_cli_paths(safe_args)
        atomic_write_text(safe_args.output, "safe")
        assert safe_args.output.read_text(encoding="utf-8") == "safe"
    finally:
        for name in cleanup_names:
            (root / name).unlink(missing_ok=True)
        root.rmdir()
    print("Self-test passed")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.packet, args.state, args.policy, args.snapshot)):
        parser.error("--packet, --state, --policy, and --snapshot are required")
    try:
        validate_cli_paths(args)
        result = validate_packet(
            read_json(args.packet),
            read_json(args.state),
            read_json(args.policy),
            read_json(args.snapshot),
        )
        rendered = render_markdown(result)
        if args.output:
            atomic_write_text(args.output, rendered)
            atomic_write_text(
                args.output.with_suffix(".json"),
                json.dumps(result, ensure_ascii=False, indent=2),
            )
        print(rendered)
        return 2 if result["status"] == "rejected" else 0
    except PacketError as exc:
        print(f"PACKET_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
