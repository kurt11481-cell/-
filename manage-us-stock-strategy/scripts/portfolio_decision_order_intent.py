#!/usr/bin/env python3
"""Compile canonical ORDER_INTENT_ONLY artifacts without broker mutation authority.

This is a thin adapter over the validated Portfolio Decision Dashboard.  It
does not import a broker transport, construct an order request, infer a fill,
or mutate portfolio, policy, delivery-runtime, or scheduler state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from functools import partial
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from portfolio_decision_dashboard import (
    ContractError, _snapshot_authority_hashes, _load_risk_registry_inputs,
    CURRENT_SESSION_CONTEXT_SCHEMA, _canonical_evidence_gate, _evaluate_current_session_context,
    _instrument_mapping, calculate_risk_metrics, manual_evidence_schema_bytes,
    _sell_readiness_evidence,
)
from session_authority import derive_us_market_session_authority
from integrated_authority_snapshot import (
    IntegratedAuthoritySnapshot, IntegratedAuthorityLoadError,
    derive_us_market_session_authority_from_snapshot,
    load_production_integrated_authority_snapshot, resolve_instrument_identity_from_snapshot,
)
from validation_common import canonical_hash, file_hash, load_json, validate_instance
from validate_registry_consistency import validate_registry_consistency


ROOT = Path(__file__).resolve().parents[2]
ORDER_INTENT_SCHEMA = (
    ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-order-intent.schema.json"
)
DEFAULT_RISK_POLICY = (
    ROOT / "manage-us-stock-strategy/assets/portfolio-decision-risk-envelope-v0.2.json"
)
DEFAULT_REGISTRY = ROOT / "workspace/policies/instrument_registry.json"
NEW_YORK = ZoneInfo("America/New_York")
MANUAL_SELL_PRICE_RULE = "KIWOOM_US_REGULAR_BEST_BID_MANUAL_SELL_LIMIT_DAY_V1"


class OrderIntentContractError(ValueError):
    """Raised when an ORDER_INTENT_ONLY artifact cannot satisfy its contract."""


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _number(value: Decimal | int | float | None) -> int | float | None:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _decision_semantic_value(report: dict[str, Any]) -> dict[str, Any]:
    """Exclude run-instance metadata from the stable decision identity."""
    semantic = deepcopy(report)
    semantic.pop("run_id", None)
    semantic.pop("generated_at", None)
    return semantic


def _manual_trigger_provenance() -> dict[str, Any]:
    return {
        "trigger_type": "MANUAL_GENUINE",
        "run_provenance_status": "VERIFIED_MANUAL",
        "actual_scheduled_run": False,
        "scheduled_occurrence_id": None,
        "operational_grade": "GRADE_B",
        "scheduled_maturity_promoted": False,
    }


def _trigger_blockers(value: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    trigger = value.get("trigger_type")
    if trigger == "MANUAL_GENUINE":
        if value.get("run_provenance_status") != "VERIFIED_MANUAL":
            blockers.append("MANUAL_TRIGGER_PROVENANCE_NOT_VERIFIED")
        if value.get("actual_scheduled_run") is not False:
            blockers.append("MANUAL_TRIGGER_MARKED_SCHEDULED")
        if value.get("operational_grade") != "GRADE_B":
            blockers.append("MANUAL_TRIGGER_GRADE_NOT_B")
    elif trigger == "SCHEDULED_GENUINE":
        if value.get("run_provenance_status") != "VERIFIED_SCHEDULED_GENUINE":
            blockers.append("SCHEDULED_TRIGGER_PROVENANCE_NOT_VERIFIED")
        if value.get("actual_scheduled_run") is not True:
            blockers.append("SCHEDULED_TRIGGER_NOT_ACTUAL_SCHEDULED_RUN")
        if not value.get("scheduled_occurrence_id"):
            blockers.append("SCHEDULED_OCCURRENCE_ID_REQUIRED")
        if value.get("operational_grade") != "GRADE_A_CANDIDATE":
            blockers.append("SCHEDULED_TRIGGER_NOT_GRADE_A_CANDIDATE")
    else:
        blockers.append("TRIGGER_TYPE_NOT_VERIFIED")
    if value.get("scheduled_maturity_promoted") is not False:
        blockers.append("SCHEDULED_MATURITY_AUTOMATIC_PROMOTION_FORBIDDEN")
    return blockers


def _request_accounting_status(report: dict[str, Any]) -> str:
    status = (report.get("evidence") or {}).get("request_accounting_status")
    if status == "VERIFIED":
        return "VERIFIED_DATA_ACQUISITION_ONLY"
    if status in {"PRESENT_INVALID", "PRESENT_UNVERIFIED"}:
        return "PARTIAL"
    return "NOT_VERIFIED"


def _canonical_price_evidence(
    evidence: dict[str, Any], ticker: str, expected_session: str | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    selected = None
    for item in evidence.get("last_verified_finalized_bars") or []:
        if isinstance(item, dict) and str(item.get("ticker") or "").upper() == ticker:
            selected = item
            break
    if not isinstance(selected, dict):
        return None, ["CANONICAL_REFERENCE_PRICE_NOT_VERIFIED"]
    bar = selected.get("bar") or {}
    price = _decimal(bar.get("price"))
    timestamp = _parse_timestamp(bar.get("provider_timestamp"))
    reported_session = bar.get("reported_session")
    if (
        selected.get("status") != "VERIFIED"
        or selected.get("identity_authority_status") != "VERIFIED"
        or selected.get("session_authority_status") != "VERIFIED"
        or selected.get("bar_date") != expected_session
        or bar.get("bar_finalized") is not True
        or bar.get("stable") is not True
        or bar.get("comparable_to_regular_close") is not True
        or bar.get("market_session_type") != "REGULAR_COMPLETED"
        or bar.get("price_basis") != "RAW_REGULAR_SESSION_CLOSE"
        or bar.get("currency") != "USD"
        or price is None
        or price <= 0
    ):
        blockers.append("CANONICAL_REFERENCE_PRICE_NOT_VERIFIED")
    if reported_session != expected_session:
        blockers.append("REPORTED_SESSION_MISMATCH")
    if timestamp is None:
        blockers.append("PRICE_TIMESTAMP_NOT_VERIFIED")
    provider = str(bar.get("provider") or "")
    if "KIWOOM" not in provider.upper():
        blockers.append("CANONICAL_PRICE_PROVIDER_NOT_KIWOOM")
    decision_time = _parse_timestamp(evidence.get("decision_as_of"))
    if decision_time is None:
        blockers.append("DECISION_TIMESTAMP_NOT_VERIFIED")
    elif timestamp is not None and timestamp > decision_time:
        blockers.append("PRICE_TIMESTAMP_AFTER_DECISION")
    try:
        expected_reported_date = date.fromisoformat(str(expected_session))
    except (TypeError, ValueError):
        expected_reported_date = None
        blockers.append("REPORTED_SESSION_NOT_VERIFIED")
    if (
        timestamp is not None
        and expected_reported_date is not None
        and timestamp.astimezone(NEW_YORK).date() <= expected_reported_date
    ):
        blockers.append("PROVIDER_OBSERVED_DATE_NOT_AFTER_REPORTED_SESSION")
    if blockers:
        return None, sorted(set(blockers))
    return {
        "price": price,
        "timestamp": bar.get("provider_timestamp"),
        "provider": provider,
        "session": selected.get("bar_date"),
    }, []


def _identity(
    ticker: str, evidence: dict[str, Any], risk_policy: dict[str, Any],
    registry: dict[str, Any] | None, snapshot: IntegratedAuthoritySnapshot | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    mapping, issue = _instrument_mapping(ticker, risk_policy, registry)
    blockers = ["INSTRUMENT_CLASSIFICATION_NOT_VERIFIED"] if issue or mapping is None else []
    status = evidence.get("identity_authority_status")
    if status != "VERIFIED":
        return mapping, None, blockers + ["INSTRUMENT_IDENTITY_NOT_VERIFIED"]
    if not isinstance(snapshot, IntegratedAuthoritySnapshot):
        return mapping, None, blockers + ["INSTRUMENT_IDENTITY_NOT_VERIFIED"]
    try:
        _snapshot_authority_hashes(snapshot, evidence)
    except (ContractError, KeyError, TypeError, ValueError, AttributeError):
        return mapping, None, blockers + ["INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH"]
    resolved = resolve_instrument_identity_from_snapshot(
        snapshot, ticker, decision_as_of=snapshot.snapshot_decision_as_of,
    )
    if resolved.authority_status != "VERIFIED" or resolved.ticker != ticker:
        return mapping, None, blockers + ["INSTRUMENT_IDENTITY_NOT_VERIFIED"]
    if blockers:
        return mapping, None, blockers
    identity = {
        "canonical_ticker": ticker,
        "instrument_class": str(mapping["instrument_class"]),
        "leverage_factor": _number(mapping["leverage_factor"]),
        "growth_ai_semiconductor_cluster": bool(mapping["growth_ai_semiconductor_cluster"]),
        "mapping_source": str(mapping["mapping_source"]),
        "identity_authority_status": "VERIFIED",
        "identity_authority_id": resolved.authority_id,
        "identity_registry_version": resolved.registry_version,
        "identity_registry_hash": resolved.registry_hash,
    }
    return mapping, identity, []


def _risk_registry_blockers(
    registry: dict[str, Any] | None, alert_policy: dict[str, Any] | None,
    input_hashes: dict[str, str],
) -> list[str]:
    """Validate Risk/Approval authority independently from Identity provenance."""
    if (
        not isinstance(registry, dict) or not isinstance(alert_policy, dict)
        or not isinstance(registry.get("registry_version"), str) or not registry["registry_version"]
        or not isinstance(registry.get("instruments"), dict)
        or not _is_sha256(input_hashes.get("instrument_registry"))
        or not _is_sha256(input_hashes.get("alert_policy"))
    ):
        return ["POLICY_REGISTRY_MISMATCH"]
    try:
        result = validate_registry_consistency(registry, alert_policy, DEFAULT_REGISTRY)
    except (KeyError, TypeError, ValueError, AttributeError):
        return ["POLICY_REGISTRY_MISMATCH"]
    return [] if result["status"] == "VALIDATED" else ["POLICY_REGISTRY_MISMATCH"]


def _projected_risk(
    report: dict[str, Any], ticker: str, side: str, quantity: int,
    estimated_value: Decimal, risk_policy: dict[str, Any], registry: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    nav = _decimal(((report.get("portfolio") or {}).get("nav_usd") or {}).get("value"))
    current_cash = _decimal(((report.get("cash_semantics") or {}).get("current_cash_usd") or {}).get("value"))
    if nav is None or nav <= 0:
        blockers.append("PROJECTED_RISK_NAV_NOT_VERIFIED")
    if current_cash is None:
        blockers.append("PROJECTED_RISK_CURRENT_CASH_NOT_VERIFIED")
    quantities: dict[str, int] = {}
    prices: dict[str, Decimal] = {}
    mappings: dict[str, dict[str, Any]] = {}
    for row in (report.get("portfolio") or {}).get("positions") or []:
        name = str(row.get("ticker") or "")
        held = ((row.get("current_quantity") or {}).get("value"))
        price = _decimal(((row.get("canonical_price_usd") or {}).get("value")))
        if not isinstance(held, int) or held < 0:
            if name == ticker:
                blockers.append("CURRENT_POSITION_QUANTITY_NOT_VERIFIED")
            continue
        if held == 0 and name != ticker:
            continue
        mapping, issue = _instrument_mapping(name, risk_policy, registry)
        if issue or mapping is None:
            blockers.append(
                "INSTRUMENT_CLASSIFICATION_NOT_VERIFIED"
                if name == ticker else f"PORTFOLIO_RISK_MAPPING_INCOMPLETE:{name}"
            )
            continue
        if price is None or price <= 0:
            blockers.append(
                "CANONICAL_REFERENCE_PRICE_NOT_VERIFIED"
                if name == ticker else f"PORTFOLIO_RISK_PRICE_INCOMPLETE:{name}"
            )
            continue
        quantities[name] = held
        prices[name] = price
        mappings[name] = mapping
    if blockers or nav is None or current_cash is None:
        return None, sorted(set(blockers))
    quantities[ticker] = quantities.get(ticker, 0) + (quantity if side == "BUY" else -quantity)
    if quantities[ticker] < 0:
        return None, ["PROPOSED_SELL_EXCEEDS_CURRENT_POSITION"]
    projected_cash = current_cash - estimated_value if side == "BUY" else current_cash + estimated_value
    if projected_cash < 0:
        return None, ["PROJECTED_CASH_BELOW_ZERO"]
    weights = {
        name: Decimal(held) * prices[name] / nav * Decimal("100")
        for name, held in quantities.items()
    }
    risk = calculate_risk_metrics(
        weights, projected_cash / nav * Decimal("100"), mappings, risk_policy,
    )
    violations = risk.get("hard_cap_violations") or []
    if violations:
        blockers.extend(f"PROJECTED_HARD_CAP_VIOLATION:{item}" for item in violations)
    return risk, sorted(set(blockers))


def _manual_risk_projection(
    report: dict[str, Any], ticker: str, quantity: Any, reference_price: Decimal | None,
    risk_policy: dict[str, Any], registry: dict[str, Any] | None,
) -> list[str]:
    """Validate completeness around the existing independent SELL projection."""
    required_metrics = {
        "CASH_PCT", "LEVERAGED_PRODUCTS_PCT", "GROWTH_AI_SEMI_BOOK_PCT",
        "GROWTH_AI_SEMI_LEVERAGE_ADJUSTED_PCT", "OVERALL_LEVERAGE_ADJUSTED_PROXY_PCT",
    }
    aggregate_fields = (
        "cash_pct", "leveraged_products_pct", "growth_ai_semiconductor_book_pct",
        "growth_ai_semiconductor_leverage_adjusted_pct", "overall_leverage_adjusted_proxy_pct",
    )

    def complete(risk: Any, metrics: set[str]) -> bool:
        if not isinstance(risk, dict) or risk.get("status") not in {"PASS", "WARNING"}:
            return False
        if risk.get("hard_cap_violations") != []:
            return False
        if any(_decimal((risk.get(field) or {}).get("value")) is None for field in aggregate_fields):
            return False
        checks = risk.get("checks")
        if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
            return False
        return metrics <= {item.get("metric") for item in checks} and all(
            _decimal(item.get("value")) is not None and item.get("status") in {"PASS", "WARNING"}
            for item in checks
        )

    try:
        if (not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0
                or reference_price is None or reference_price <= 0):
            return ["MANUAL_RULE_PROJECTED_RISK_INPUT_INCOMPLETE"]
        for section, fields in (
            ("cash", ("target_min_pct", "target_max_pct", "hard_floor_pct")),
            ("all_daily_reset_leveraged_products", ("target_min_pct", "target_max_pct", "hard_cap_pct")),
            ("single_3x_etf", ("target_min_pct", "target_max_pct", "hard_cap_pct")),
            ("single_2x_single_stock_etf", ("target_min_pct", "target_max_pct", "hard_cap_pct")),
            ("single_normal_stock", ("target_min_pct", "target_max_pct", "hard_cap_pct")),
            ("growth_ai_semiconductor_cluster", ("book_hard_cap_pct", "leverage_adjusted_hard_cap_pct")),
            ("overall_leverage_adjusted_exposure_proxy", ("target_min_pct", "target_max_pct", "hard_cap_pct")),
        ):
            if any(_decimal(risk_policy[section][field]) is None for field in fields):
                return ["MANUAL_RULE_RISK_THRESHOLD_INCOMPLETE"]
        rows = report["portfolio"]["positions"]
        target_metrics = set(required_metrics)
        names: set[str] = set()
        for row in rows:
            name = row["ticker"]
            held = row["current_quantity"]["value"]
            if (name in names or not isinstance(held, int) or isinstance(held, bool) or held < 0):
                return ["MANUAL_RULE_PORTFOLIO_RISK_INPUT_INCOMPLETE"]
            names.add(name)
            target_metrics.add(f"POSITION_PCT:{name}")
            if held == 0 and name != ticker:
                continue
            mapping, issue = _instrument_mapping(name, risk_policy, registry)
            if (issue or not isinstance(mapping, dict)
                    or mapping.get("instrument_class") not in {
                        "NORMAL_STOCK", "SINGLE_3X_ETF", "SINGLE_2X_SINGLE_STOCK_ETF"}
                    or _decimal(mapping.get("leverage_factor")) is None
                    or mapping["leverage_factor"] <= 0
                    or not isinstance(mapping.get("growth_ai_semiconductor_cluster"), bool)):
                return ["MANUAL_RULE_RISK_MAPPING_INCOMPLETE"]
            price = _decimal(row["canonical_price_usd"]["value"])
            if price is None or price <= 0 or (name == ticker and price != reference_price):
                return ["MANUAL_RULE_PORTFOLIO_RISK_PRICE_INCOMPLETE"]
            required_metrics.add(f"POSITION_PCT:{name}")
        if ticker not in names:
            return ["MANUAL_RULE_PORTFOLIO_RISK_INPUT_INCOMPLETE"]
        # Reference proceeds exist only inside this independent risk simulation.
        risk, blockers = _projected_risk(
            report, ticker, "SELL", quantity, Decimal(quantity) * reference_price, risk_policy, registry,
        )
        if not complete(risk, required_metrics):
            blockers.append("MANUAL_RULE_PROJECTED_RISK_NOT_COMPLETE_OR_PASS")
        if not complete(report["portfolio"].get("target_reference_risk"), target_metrics):
            blockers.append("MANUAL_RULE_TARGET_RISK_NOT_COMPLETE_OR_PASS")
        return sorted(set(blockers))
    except (KeyError, TypeError, ValueError, AttributeError, ArithmeticError):
        return ["MANUAL_RULE_PROJECTED_RISK_INPUT_INCOMPLETE"]


def _manual_session_window(
    context: dict[str, Any] | None, evidence: dict[str, Any], input_hashes: dict[str, str],
    evaluation_time: datetime, valid_from: Any, valid_until: Any,
    authority_resolver: Callable[..., Any],
) -> tuple[Any, bool, list[str]]:
    """Bind the current authority and existing freshness boundary without rollover."""
    blockers: list[str] = []
    start, end = _parse_timestamp(valid_from), _parse_timestamp(valid_until)
    boundaries = [(end, valid_until)] if end is not None else []
    if start is None or end is None or start >= end:
        blockers.append("INSTRUCTION_VALIDITY_WINDOW_INVALID")
    elif evaluation_time < start:
        blockers.append("MANUAL_RULE_VALIDITY_NOT_STARTED")
    runtime = None

    def resolve(*args: Any, **kwargs: Any) -> Any:
        nonlocal runtime
        runtime = authority_resolver(*args, **kwargs)
        return runtime

    result = _evaluate_current_session_context(
        context, evidence, input_hashes.get("portfolio_evidence"),
        CURRENT_SESSION_CONTEXT_SCHEMA.read_bytes(), evaluation_time.isoformat(), resolve,
    )
    blockers.extend(result["blockers"])
    if runtime is None or runtime.authority_status != "VERIFIED":
        blockers.append("MANUAL_RULE_CURRENT_SESSION_AUTHORITY_NOT_VERIFIED")
    else:
        if runtime.market_phase != "CORE_OPEN":
            blockers.append("MANUAL_RULE_CORE_OPEN_REQUIRED")
        window = getattr(runtime, "current_date_session", None)
        opened = _parse_timestamp(getattr(window, "core_open_at", None))
        closed = _parse_timestamp(getattr(window, "core_close_at", None))
        if opened is None or closed is None or opened >= closed:
            blockers.append("MANUAL_RULE_CORE_WINDOW_NOT_VERIFIED")
        else:
            boundaries.append((closed, window.core_close_at))
            if evaluation_time < opened:
                blockers.append("MANUAL_RULE_CORE_OPEN_REQUIRED")
            if start is None or start.astimezone(NEW_YORK).date().isoformat() != window.session_date:
                blockers.append("MANUAL_RULE_SESSION_ROLLOVER_FORBIDDEN")
    for field in ("decision_as_of", "observed_at", "broker_snapshot_as_of"):
        timestamp = _parse_timestamp(evidence.get(field))
        if timestamp is None:
            blockers.append("MANUAL_RULE_CURRENT_FRESHNESS_NOT_VERIFIED")
        elif timestamp > evaluation_time:
            blockers.append("MANUAL_RULE_EVIDENCE_FROM_FUTURE")
        elif field == "broker_snapshot_as_of":
            # Reuse _canonical_evidence_gate's approved 900-second broker contract.
            freshness_end = timestamp + timedelta(seconds=900)
            boundaries.append((freshness_end, freshness_end.isoformat()))
            if evaluation_time >= freshness_end:
                blockers.append("BROKER_SNAPSHOT_STALE")
    context_time = _parse_timestamp(context.get("context_generated_at")) if isinstance(context, dict) else None
    if context_time is None or context_time > evaluation_time:
        blockers.append("MANUAL_RULE_CURRENT_CONTEXT_TIME_NOT_VERIFIED")
    effective_end, output_end = min(boundaries, key=lambda item: item[0]) if boundaries else (None, valid_until)
    if start is not None and effective_end is not None and start >= effective_end:
        blockers.append("INSTRUCTION_VALIDITY_WINDOW_INVALID")
    return output_end, effective_end is not None and evaluation_time >= effective_end, sorted(set(blockers))


def _global_blockers(
    report: dict[str, Any], validation: dict[str, Any], plan: dict[str, Any],
    evidence: dict[str, Any], risk_policy: dict[str, Any], risk_envelope_sha256: str,
    input_hashes: dict[str, str], trigger_provenance: dict[str, Any],
) -> list[str]:
    blockers = _trigger_blockers(trigger_provenance)
    if validation.get("status") != "PASS":
        blockers.append("PORTFOLIO_DECISION_VALIDATION_NOT_PASS")
    if report.get("schema_version") != "1.0":
        blockers.append("PORTFOLIO_DECISION_SCHEMA_VERSION_NOT_SUPPORTED")
    authority = report.get("authority") or {}
    if authority.get("broker_order_authority") is not False:
        blockers.append("UPSTREAM_ORDER_AUTHORITY_NOT_FALSE")
    if authority.get("execution_quantity") is not None:
        blockers.append("UPSTREAM_EXECUTION_QUANTITY_NOT_NULL")
    if authority.get("automatic_order") is not False:
        blockers.append("UPSTREAM_AUTOMATIC_ORDER_NOT_FALSE")
    if (report.get("evidence") or {}).get("current_freshness") != "CURRENT_SESSION_CONTEXT_VERIFIED":
        blockers.append("CURRENT_SESSION_EVIDENCE_NOT_VERIFIED")
    if (report.get("current_context") or {}).get("verified") is not True:
        blockers.append("CURRENT_SESSION_CONTEXT_NOT_VERIFIED")
    if plan.get("plan_status") != "CURRENT_APPROVED":
        blockers.append("CURRENT_APPROVED_DECISION_PLAN_REQUIRED")
    if evidence.get("expected_completed_us_session") != (
        report.get("current_context") or {}
    ).get("expected_completed_us_session"):
        blockers.append("MARKET_SESSION_BINDING_MISMATCH")
    if risk_policy.get("status") != "APPROVED_READ_ONLY_REFERENCE":
        blockers.append("RISK_ENVELOPE_NOT_APPROVED_READ_ONLY_REFERENCE")
    if risk_policy.get("policy_version") != "portfolio-decision-risk-envelope-v0.2":
        blockers.append("RISK_ENVELOPE_VERSION_NOT_VERIFIED")
    if risk_policy.get("order_authority") is not False:
        blockers.append("RISK_ENVELOPE_ORDER_AUTHORITY_NOT_FALSE")
    if risk_policy.get("execution_quantity") is not None:
        blockers.append("RISK_ENVELOPE_EXECUTION_QUANTITY_NOT_NULL")
    if risk_policy.get("automatic_order") is not False:
        blockers.append("RISK_ENVELOPE_AUTOMATIC_ORDER_NOT_FALSE")
    if len(risk_envelope_sha256) != 64 or input_hashes.get("risk_policy") != risk_envelope_sha256:
        blockers.append("RISK_ENVELOPE_HASH_NOT_VERIFIED")
    return sorted(set(blockers))


def _instruction_state(states: list[str], global_blockers: list[str]) -> str:
    if "ORDER_INSTRUCTION_READY" in states:
        return "ORDER_INSTRUCTION_READY"
    if "ORDER_BLOCKED" in states or global_blockers:
        return "ORDER_BLOCKED"
    if "ORDER_EXPIRED" in states:
        return "ORDER_EXPIRED"
    return "NO_ORDER"


def compile_order_intent_artifact(
    report: dict[str, Any], validation: dict[str, Any], plan: dict[str, Any],
    evidence: dict[str, Any], risk_policy: dict[str, Any], registry: dict[str, Any] | None,
    *, risk_envelope_sha256: str, input_hashes: dict[str, str],
    trigger_provenance: dict[str, Any] | None = None,
    now: str | None = None, schema_path: Path = ORDER_INTENT_SCHEMA,
    current_session_context: dict[str, Any] | None = None,
    current_session_authority_resolver: Callable[..., Any] = derive_us_market_session_authority,
    integrated_snapshot: IntegratedAuthoritySnapshot | None = None,
    alert_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile a non-submitting artifact from a validated Portfolio Decision."""
    generated_at = str(report.get("generated_at") or now or datetime.now(timezone.utc).isoformat())
    evaluation_time = _parse_timestamp(now or generated_at)
    if evaluation_time is None:
        raise OrderIntentContractError("ORDER_INTENT_EVALUATION_TIME_INVALID")
    manual_evaluation_time = evaluation_time if now is not None else None
    trigger = deepcopy(trigger_provenance or _manual_trigger_provenance())
    decision_digest = canonical_hash(_decision_semantic_value(report))
    market_session_date = evidence.get("expected_completed_us_session")
    broker_state = evidence.get("broker_observed_state")
    broker_snapshot_id = canonical_hash(broker_state) if isinstance(broker_state, dict) else None
    input_digest = canonical_hash(dict(sorted(input_hashes.items())))
    global_blockers = _global_blockers(
        report, validation, plan, evidence, risk_policy, risk_envelope_sha256,
        input_hashes, trigger,
    )
    registry_blockers = _risk_registry_blockers(registry, alert_policy, input_hashes)
    plan_positions = {
        str(item.get("ticker") or "").upper(): item
        for item in plan.get("positions") or [] if isinstance(item, dict)
    }
    decision_rows = {
        str(item.get("ticker") or "").upper(): item
        for item in (report.get("portfolio") or {}).get("positions") or []
        if isinstance(item, dict)
    }
    instructions: list[dict[str, Any]] = []
    for ticker, source in plan_positions.items():
        action = source.get("action")
        side = "BUY" if action == "ADD" else "SELL" if action in {"TRIM", "EXIT"} else None
        row = decision_rows.get(ticker)
        terms = source.get("order_intent_terms") if isinstance(source.get("order_intent_terms"), dict) else None
        manual_rule = bool(
            terms and side == "SELL" and terms.get("order_type") == "LIMIT"
            and terms.get("time_in_force") == "DAY" and terms.get("limit_price") is None
            and terms.get("approved_price_rule") == MANUAL_SELL_PRICE_RULE
        )
        blockers = list(global_blockers) if side else []
        if row is None:
            blockers.append("PORTFOLIO_DECISION_ROW_MISSING")
            row = {}
        for item in row.get("blockers") or []:
            blockers.append({
                "BLOCKED_RISK_MAPPING_REQUIRED": "INSTRUMENT_CLASSIFICATION_NOT_VERIFIED",
                "BLOCKED_CANONICAL_PRICE_REQUIRED": "CANONICAL_REFERENCE_PRICE_NOT_VERIFIED",
                "BLOCKED_TARGET_WEIGHT_REQUIRED": "APPROVED_PRODUCTION_TARGET_REQUIRED",
            }.get(item, str(item)))
        try:
            mapping, identity, identity_blockers = _identity(
                ticker, evidence, risk_policy, registry, integrated_snapshot,
            )
        except (KeyError, TypeError, ValueError, AttributeError, ArithmeticError):
            if not manual_rule:
                raise
            mapping, identity = None, None
            identity_blockers = ["INSTRUMENT_CLASSIFICATION_NOT_VERIFIED"]
        if side:
            blockers.extend(identity_blockers)
            blockers.extend(registry_blockers)
        price, price_blockers = _canonical_price_evidence(evidence, ticker, market_session_date)
        blockers.extend(price_blockers)
        current_quantity = ((row.get("current_quantity") or {}).get("value"))
        current_weight = ((row.get("current_weight_pct") or {}).get("value"))
        target_quantity = ((row.get("target_shares_reference") or {}).get("value"))
        target_weight = ((row.get("target_weight_pct") or {}).get("value"))
        proposed_quantity = terms.get("proposed_quantity") if terms else None
        order_type = terms.get("order_type") if terms else None
        limit_price = terms.get("limit_price") if terms else None
        approved_price_rule = terms.get("approved_price_rule") if terms else None
        valid_from = terms.get("valid_from") if terms else None
        valid_until = terms.get("valid_until") if terms else None
        why_now = terms.get("why_now") if terms else None
        decision_change_trigger = terms.get("decision_change_trigger") if terms else None
        thesis_status = terms.get("thesis_status") if terms else None
        kill_condition = terms.get("kill_condition") if terms else None
        tif = terms.get("time_in_force") if terms else None
        estimated_value: Decimal | None = None
        expired = False
        if side:
            if side == "BUY" and source.get("thesis_kill") is True:
                blockers.append("BUY_SOURCE_THESIS_KILL_ACTIVE")
            if side == "BUY" and thesis_status == "KILLED":
                blockers.append("BUY_APPROVED_TERMS_THESIS_STATUS_KILLED")
            if terms is None:
                blockers.append("APPROVED_ORDER_INTENT_TERMS_REQUIRED")
            else:
                if terms.get("terms_status") != "APPROVED_ORDER_INTENT_ONLY":
                    blockers.append("ORDER_INTENT_TERMS_NOT_APPROVED")
                if terms.get("production_target_approval_status") != "APPROVED_PRODUCTION_TARGET":
                    blockers.append("PRODUCTION_TARGET_NOT_APPROVED")
                if source.get("target_status") != "APPROVED" or plan.get("target_type") == "PROVISIONAL_FULL_TARGET_REFERENCE":
                    blockers.append("PRODUCTION_TARGET_NOT_APPROVED")
                start = _parse_timestamp(valid_from)
                end = _parse_timestamp(valid_until)
                if start is None or end is None or start >= end:
                    blockers.append("INSTRUCTION_VALIDITY_WINDOW_INVALID")
                elif evaluation_time > end:
                    expired = True
                if not isinstance(proposed_quantity, int) or isinstance(proposed_quantity, bool) or proposed_quantity <= 0:
                    blockers.append("PROPOSED_QUANTITY_NOT_APPROVED")
                if manual_rule:
                    manual_evaluation_time = manual_evaluation_time or datetime.now(timezone.utc)
                    valid_until, expired, session_blockers = _manual_session_window(
                        current_session_context, evidence, input_hashes, manual_evaluation_time,
                        valid_from, valid_until, current_session_authority_resolver,
                    )
                    blockers.extend(session_blockers)
                elif order_type == "LIMIT":
                    limit_value = _decimal(limit_price)
                    if limit_value is None or limit_value <= 0 or approved_price_rule is not None:
                        blockers.append("APPROVED_LIMIT_PRICE_REQUIRED")
                    elif isinstance(proposed_quantity, int):
                        estimated_value = Decimal(proposed_quantity) * limit_value
                elif order_type == "PRICE_RULE":
                    blockers.append("APPROVED_PRICE_RULE_RUNTIME_NOT_IMPLEMENTED")
                else:
                    blockers.append("ORDER_TYPE_NOT_APPROVED")
                if not why_now:
                    blockers.append("WHY_NOW_REQUIRED")
                if not decision_change_trigger:
                    blockers.append("DECISION_CHANGE_TRIGGER_REQUIRED")
                if action == "ADD" and not kill_condition:
                    blockers.append("KILL_CONDITION_REQUIRED_FOR_BUY")
                delta = ((row.get("share_delta") or {}).get("value"))
                if not isinstance(current_quantity, int) or current_quantity < 0:
                    blockers.append("CURRENT_POSITION_QUANTITY_NOT_VERIFIED")
                if not isinstance(target_quantity, int) or target_quantity < 0:
                    blockers.append("TARGET_POSITION_QUANTITY_NOT_VERIFIED")
                if not isinstance(delta, int):
                    blockers.append("PORTFOLIO_DECISION_QUANTITY_DELTA_NOT_VERIFIED")
                elif side == "BUY":
                    if delta <= 0 or not isinstance(proposed_quantity, int) or proposed_quantity > delta:
                        blockers.append("PROPOSED_BUY_EXCEEDS_APPROVED_TARGET_GAP")
                elif action == "TRIM":
                    if delta >= 0 or not isinstance(proposed_quantity, int) or proposed_quantity > abs(delta):
                        blockers.append("PROPOSED_SELL_EXCEEDS_APPROVED_TARGET_GAP")
                elif action == "EXIT" and proposed_quantity != current_quantity:
                    blockers.append("EXIT_QUANTITY_MUST_EQUAL_CURRENT_POSITION")
                if side == "BUY":
                    funding_source = terms.get("funding_source")
                    if funding_source == "PENDING_SELL_PROCEEDS":
                        blockers.append("PENDING_SELL_FILL_RECONCILIATION")
                    elif funding_source != "VERIFIED_ORDERABLE_CASH":
                        blockers.append("VERIFIED_ORDERABLE_CASH_REQUIRED")
                    orderable = _decimal(((report.get("cash_semantics") or {}).get("verified_orderable_cash_usd") or {}).get("value"))
                    if orderable is None:
                        blockers.append("VERIFIED_ORDERABLE_CASH_REQUIRED")
                    elif estimated_value is not None and estimated_value > orderable:
                        blockers.append("VERIFIED_ORDERABLE_CASH_INSUFFICIENT")
                    if current_quantity == 0 and isinstance(target_quantity, int) and isinstance(proposed_quantity, int):
                        fraction = _decimal(
                            (risk_policy.get("new_position_initial_entry") or {}).get(
                                "maximum_fraction_of_full_target"
                            )
                        )
                        if fraction is None:
                            blockers.append("INITIAL_ENTRY_POLICY_NOT_VERIFIED")
                        else:
                            maximum = int((Decimal(target_quantity) * fraction).to_integral_value(rounding=ROUND_FLOOR))
                            if proposed_quantity > maximum:
                                blockers.append("NEW_POSITION_INITIAL_ENTRY_EXCEEDS_50_PERCENT")
                elif terms.get("funding_source") != "NOT_APPLICABLE":
                    blockers.append("SELL_FUNDING_SOURCE_MUST_BE_NOT_APPLICABLE")
        if side == "SELL":
            sell_evidence = _sell_readiness_evidence(
                evidence, ticker, current_quantity, proposed_quantity,
                manual_evaluation_time if manual_rule else evaluation_time,
            )
            blockers.extend(sell_evidence["blockers"])
            open_end = _parse_timestamp(sell_evidence["open_order_valid_until"])
            instruction_end = _parse_timestamp(valid_until)
            if open_end is not None and instruction_end is not None and open_end < instruction_end:
                valid_until = sell_evidence["open_order_valid_until"]
        current_risk = ((report.get("portfolio") or {}).get("current_risk") or {})
        target_risk = ((report.get("portfolio") or {}).get("target_reference_risk") or {})
        if side == "BUY" and current_risk.get("hard_cap_violations"):
            blockers.append("CURRENT_HARD_CAP_VIOLATION")
        if side and target_risk.get("hard_cap_violations"):
            blockers.append("TARGET_HARD_CAP_VIOLATION")
        if manual_rule:
            _, evidence_blockers, _ = _canonical_evidence_gate(
                evidence, plan, report.get("compile_mode", "INITIAL_COMPILE"),
                manual_evidence_schema_bytes(evidence),
            )
            blockers.extend(evidence_blockers)
            blockers.extend(_manual_risk_projection(
                report, ticker, proposed_quantity, price["price"] if price else None, risk_policy, registry,
            ))
        elif side and isinstance(proposed_quantity, int) and estimated_value is not None and mapping is not None:
            _, projected_blockers = _projected_risk(
                report, ticker, side, proposed_quantity, estimated_value, risk_policy, registry,
            )
            blockers.extend(projected_blockers)
        deadband_no_order = bool(
            row.get("deadband_status") == "NO_TRADE_PREFERRED"
            and not current_risk.get("hard_cap_violations")
            and not target_risk.get("hard_cap_violations")
            and source.get("thesis_kill") is not True
        )
        blockers = sorted(set(blockers))
        if side is None:
            state = "NO_ORDER"
            risk_gate = "NOT_APPLICABLE"
        elif expired:
            state = "ORDER_EXPIRED"
            risk_gate = "BLOCKED"
        elif side == "SELL" and sell_evidence["blockers"]:
            state = "ORDER_BLOCKED"
            risk_gate = "BLOCKED"
        elif deadband_no_order:
            state = "NO_ORDER"
            risk_gate = "NOT_APPLICABLE"
            blockers = sorted(set(blockers + ["DEADBAND_NO_TRADE_PREFERRED"]))
        elif blockers:
            state = "ORDER_BLOCKED"
            risk_gate = "BLOCKED"
        else:
            state = "ORDER_INSTRUCTION_READY"
            risk_gate = "PASS"
        semantic = {
            "decision_digest": decision_digest,
            "market_session_date": market_session_date,
            "ticker": ticker,
            "side": side,
            "proposed_quantity": proposed_quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "approved_price_rule": approved_price_rule,
            "time_in_force": tif,
            "valid_from": valid_from,
            "valid_until": valid_until,
        }
        instruction = {
            "instruction_id": canonical_hash(semantic),
            "state": state,
            "generated_at": generated_at,
            "market_session_date": market_session_date,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "ticker": ticker,
            "instrument_identity": identity,
            "side": side,
            "proposed_quantity": proposed_quantity,
            "order_type": order_type,
            "limit_price": _number(_decimal(limit_price)),
            "approved_price_rule": approved_price_rule,
            "time_in_force": tif,
            "canonical_reference_price": _number(price["price"]) if price else None,
            "price_timestamp": price["timestamp"] if price else None,
            "market_phase": (report.get("evidence") or {}).get("market_phase"),
            "current_position_quantity": current_quantity if isinstance(current_quantity, int) else None,
            "current_position_weight": _number(_decimal(current_weight)),
            "target_position_quantity": target_quantity if isinstance(target_quantity, int) else None,
            "target_position_weight": _number(_decimal(target_weight)),
            "estimated_order_value": _number(estimated_value),
            "verified_orderable_cash": (
                ((report.get("cash_semantics") or {}).get("verified_orderable_cash_usd") or {}).get("value")
                if side == "BUY" else None
            ),
            "decision_reason": str(source.get("rationale") or "Decision Plan rationale unavailable"),
            "why_now": why_now,
            "decision_change_trigger": decision_change_trigger,
            "thesis_status": thesis_status,
            "kill_condition": kill_condition,
            "risk_envelope_version": risk_policy.get("policy_version"),
            "decision_plan_version": plan.get("plan_id"),
            "broker_snapshot_id": broker_snapshot_id,
            "input_provenance_digest": input_digest,
            "decision_digest": decision_digest,
            "risk_gate_status": risk_gate,
            "authority_status": "ORDER_INTENT_ONLY_NO_EXECUTION_AUTHORITY",
            "submission_status": "NOT_SUBMITTED",
            "order_authority": False,
            "execution_quantity": None,
            "automatic_order": False,
            "broker_submission": "DISABLED",
            "portfolio_mutation": False,
            "blockers": blockers,
        }
        instruction["record_hash"] = canonical_hash(instruction)
        instructions.append(instruction)
    instruction_states = [item["state"] for item in instructions]
    run_state = _instruction_state(instruction_states, global_blockers)
    semantic_digest = canonical_hash({
        "decision_digest": decision_digest,
        "market_session_date": market_session_date,
        "instructions": [item["instruction_id"] for item in instructions],
        "risk_envelope_sha256": risk_envelope_sha256,
    })
    delivery_id = canonical_hash({
        "semantic_digest": semantic_digest,
        "market_session_date": market_session_date,
        "channel": "EXISTING_AUTOMATION_DELIVERY",
    })
    artifact = {
        "schema_version": "1.0",
        "artifact_type": "PORTFOLIO_DECISION_ORDER_INTENT_ONLY",
        "generated_at": generated_at,
        "run_state": run_state,
        "market_session_date": market_session_date,
        "risk_envelope_version": risk_policy.get("policy_version"),
        "risk_envelope_sha256": risk_envelope_sha256,
        "decision_plan_version": plan.get("plan_id"),
        "broker_snapshot_id": broker_snapshot_id,
        "input_hashes": dict(sorted(input_hashes.items())),
        "input_provenance_digest": input_digest,
        "decision_digest": decision_digest,
        "semantic_digest": semantic_digest,
        "trigger_provenance": trigger,
        "request_accounting_status": _request_accounting_status(report),
        "order_endpoint_evidence": "STATICALLY_BLOCKED",
        "instructions": instructions,
        "run_blockers": global_blockers,
        "delivery": {
            "channel": "EXISTING_AUTOMATION_DELIVERY",
            "delivery_id": delivery_id,
            "status": "ELIGIBLE" if run_state == "ORDER_INSTRUCTION_READY" else "NOT_ELIGIBLE",
            "delivery_attempted": False,
            "delivery_successful": False,
            "failure_isolated": True,
        },
        "submission_status": "NOT_SUBMITTED",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
        "broker_submission": "DISABLED",
        "portfolio_mutation": False,
    }
    artifact["record_hash"] = canonical_hash(artifact)
    schema_errors = validate_instance(artifact, schema_path)
    if schema_errors:
        raise OrderIntentContractError("ORDER_INTENT_SCHEMA_INVALID:" + "; ".join(schema_errors))
    return artifact


def plan_delivery(
    artifact: dict[str, Any], *, successful_delivery_ids: set[str],
    delivery_error: str | None = None,
) -> dict[str, Any]:
    """Return isolated delivery metadata without mutating the canonical artifact."""
    delivery = deepcopy(artifact["delivery"])
    if delivery["delivery_id"] in successful_delivery_ids:
        delivery["status"] = "DUPLICATE_SUPPRESSED"
        delivery["delivery_attempted"] = False
        delivery["delivery_successful"] = False
    elif delivery_error is not None:
        delivery["status"] = "DELIVERY_FAILED"
        delivery["delivery_attempted"] = True
        delivery["delivery_successful"] = False
        delivery["failure_reason"] = delivery_error
    return delivery


def write_order_intent_artifact(path: Path, artifact: dict[str, Any]) -> Path:
    """Create one immutable JSON artifact; never overwrite an existing path."""
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with target.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile an ORDER_INTENT_ONLY artifact")
    parser.add_argument("--portfolio-decision", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    parser.add_argument("--decision-plan", type=Path, required=True)
    parser.add_argument("--portfolio-evidence", type=Path, required=True)
    parser.add_argument("--risk-policy", type=Path, default=DEFAULT_RISK_POLICY)
    parser.add_argument("--instrument-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now")
    parser.add_argument("--current-session-context", type=Path)
    args = parser.parse_args()
    paths = {
        "portfolio_decision": args.portfolio_decision.resolve(),
        "validation_report": args.validation_report.resolve(),
        "decision_plan": args.decision_plan.resolve(),
        "portfolio_evidence": args.portfolio_evidence.resolve(),
        "risk_policy": args.risk_policy.resolve(),
    }
    if args.current_session_context is not None:
        paths["current_session_context"] = args.current_session_context.resolve()
    raw = {name: path.read_bytes() for name, path in paths.items()}
    values = {name: json.loads(payload.decode("utf-8")) for name, payload in raw.items()}
    hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in raw.items()}
    try:
        registry, alert_policy, registry_hashes = _load_risk_registry_inputs(args.instrument_registry)
    except ContractError as exc:
        parser.error(str(exc))
    hashes.update(registry_hashes)
    evaluation_time = args.now or datetime.now(timezone.utc).isoformat()
    try:
        snapshot = load_production_integrated_authority_snapshot(
            trusted_root=ROOT, decision_as_of=evaluation_time, resolved_at=evaluation_time,
            run_id=values["portfolio_decision"].get("run_id"),
        )
        hashes.update(_snapshot_authority_hashes(snapshot, values["portfolio_evidence"]))
    except (IntegratedAuthorityLoadError, ContractError, OSError) as exc:
        parser.error(str(exc))
    resolver = partial(derive_us_market_session_authority_from_snapshot, snapshot)
    context = values.get("current_session_context")
    context_result = _evaluate_current_session_context(
        context, values["portfolio_evidence"], hashes["portfolio_evidence"],
        CURRENT_SESSION_CONTEXT_SCHEMA.read_bytes(), evaluation_time, resolver,
    )
    if not context_result["verified"]:
        parser.error(";".join(context_result["blockers"]))
    artifact = compile_order_intent_artifact(
        values["portfolio_decision"], values["validation_report"], values["decision_plan"],
        values["portfolio_evidence"], values["risk_policy"], registry,
        risk_envelope_sha256=hashes["risk_policy"], input_hashes=hashes, now=evaluation_time,
        current_session_context=context, current_session_authority_resolver=resolver,
        integrated_snapshot=snapshot, alert_policy=alert_policy,
    )
    print(write_order_intent_artifact(args.output, artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
