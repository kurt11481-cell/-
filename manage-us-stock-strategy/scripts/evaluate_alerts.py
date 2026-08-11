#!/usr/bin/env python3
"""Evaluate deterministic, read-only portfolio alert candidates from JSON inputs.

This script does not fetch market data and never places orders. A separate agent
must create a validated completed-session snapshot that follows the documented
schema in references/alert-automation.md.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import sys
import tempfile
import time as time_module
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from timing_engine import (
    evaluate_holding_timing,
    timing_anchor_errors,
    watch_setup,
)
from validate_technical_snapshot import validate_snapshot as validate_technical_snapshot


class AlertError(RuntimeError):
    pass


ACTIVE_EVENT_GRADES = {"A", "B", "D"}
DEFAULT_OUTPUT_LOCALE = "ko-KR"
SUPPORTED_OUTPUT_LOCALES = ("en-US", "ko-KR")
LOCALE_ROOT = Path(__file__).resolve().parents[1] / "assets" / "locales"
HEADLINE_PRESENT_KEY = "alert_present"
HEADLINE_NONE_KEY = "alert_none"
CANONICAL_ENGLISH_MESSAGES = {
    HEADLINE_PRESENT_KEY: "Trade review alert available",
    HEADLINE_NONE_KEY: "No trade review alert",
    "staged_reduction_review": "staged-reduction review",
    "no_order_notice": (
        "No order was placed or scheduled. Human approval and a current "
        "broker state are required."
    ),
}


def load_output_messages(output_locale: str) -> dict[str, str]:
    """Load presentation-only labels without exposing core logic to localization."""

    if output_locale not in SUPPORTED_OUTPUT_LOCALES:
        raise AlertError(f"unsupported output locale: {output_locale}")
    if output_locale == "en-US":
        return dict(CANONICAL_ENGLISH_MESSAGES)
    path = LOCALE_ROOT / f"{output_locale}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AlertError(f"failed to load output locale {output_locale}: {exc}") from exc
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, dict):
        raise AlertError(f"output locale {output_locale} has no messages object")
    resolved = dict(CANONICAL_ENGLISH_MESSAGES)
    for key in CANONICAL_ENGLISH_MESSAGES:
        value = messages.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AlertError(f"output locale {output_locale} is missing {key}")
        resolved[key] = value
    return resolved


def set_result_headline(result: dict[str, Any], key: str) -> None:
    """Store an English canonical headline plus its stable localization key."""

    if key not in {HEADLINE_PRESENT_KEY, HEADLINE_NONE_KEY}:
        raise AlertError(f"unsupported headline key: {key}")
    result["headline_key"] = key
    result["headline"] = CANONICAL_ENGLISH_MESSAGES[key]


def parse_iso_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AlertError(f"missing {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AlertError(f"invalid {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise AlertError(f"{field} must include a timezone offset")
    return parsed


def parse_iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise AlertError(f"missing {field}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise AlertError(f"invalid {field}: {value}") from exc


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


@contextlib.contextmanager
def exclusive_run_lock(path: Path, stale_after_seconds: int = 3600):
    """Prevent concurrent evaluations from delivering the same event twice."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(
                descriptor,
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).encode("utf-8"),
            )
            os.close(descriptor)
            break
        except FileExistsError as exc:
            age = time_module.time() - path.stat().st_mtime
            if attempt == 0 and age > stale_after_seconds:
                path.unlink(missing_ok=True)
                continue
            raise AlertError(f"another alert evaluation is active: {path}") from exc
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AlertError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AlertError(f"Top-level JSON must be an object: {path}")
    return value


def read_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "schema_version": "1.0",
            "last_processed_us_session": None,
            "event_states": {},
            "delivery_ids": [],
            "audit_log": [],
        }
    return read_json(path)


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def inside_band(price: float, band: list[float]) -> bool:
    low, high = sorted(map(float, band))
    return low <= price <= high


def distance_to_band(price: float, band: list[float]) -> float:
    low, high = sorted(map(float, band))
    if low <= price <= high:
        return 0.0
    boundary = low if price < low else high
    return abs(price - boundary) / boundary


def trend_ok(side: str, row: dict[str, Any], rules: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    required = ["close", "ma20", "ma50", "ma50_5d_ago", "ma200", "rsi14"]
    missing = [key for key in required if not finite_number(row.get(key))]
    if missing:
        return False, [f"missing trend inputs: {', '.join(missing)}"]
    close = float(row["close"])
    ma20 = float(row["ma20"])
    ma50 = float(row["ma50"])
    ma50_old = float(row["ma50_5d_ago"])
    ma200 = float(row["ma200"])
    rsi = float(row["rsi14"])
    if side == "buy":
        checks = {
            "close_at_or_above_ma20": close >= ma20,
            "ma20_at_or_above_ma50": ma20 >= ma50,
            "ma50_nonfalling": ma50 >= ma50_old,
            "close_at_or_above_ma200": close >= ma200,
        }
        minimum = int(rules.get("buy_minimum_pass_count", 3))
        passed = sum(checks.values())
        reasons.extend(f"{name}={value}" for name, value in checks.items())
        return passed >= minimum, reasons
    checks = {
        "close_at_or_above_ma20": close >= ma20,
        "rsi_at_or_above_threshold": rsi >= float(rules.get("sell_rsi_minimum", 55)),
    }
    reasons.extend(f"{name}={value}" for name, value in checks.items())
    return any(checks.values()), reasons


def allowed_post_trade_shares(symbol: str, shares: int, policy: dict[str, Any]) -> bool:
    if symbol in set(policy.get("zero_target_exceptions", [])) and shares == 0:
        return True
    if symbol == "SGOV":
        return shares >= 0 and shares % 5 == 0
    if symbol in set(policy.get("tracking_symbols", [])):
        return shares == 1 or (shares >= 5 and shares % 5 == 0)
    return shares >= 0


def rules_hash(policy: dict[str, Any]) -> str:
    operational_policy = deepcopy(policy)
    operational_policy.pop("archived_prior_strategy", None)
    encoded = json.dumps(
        operational_policy, ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def alert_event_key(
    strategy_version: str,
    current_rules_hash: str,
    event_type: str,
    symbol: str,
    side: str,
    quantity: int,
    band_version: str,
    stage: str,
) -> str:
    raw = "|".join(
        [
            strategy_version,
            current_rules_hash,
            event_type,
            symbol,
            side,
            str(quantity),
            band_version,
            stage,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def alert_delivery_id(
    event_key: str, session_date: str, grade: str, signal_fingerprint: str = ""
) -> str:
    raw = "|".join([event_key, session_date, grade, signal_fingerprint])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def policy_event_key(
    strategy_version: str,
    current_rules_hash: str,
    state_revision: Any,
    event_type: str,
    symbol: str,
    side: str,
    rule_version: str,
) -> str:
    """Build a stable event key for non-order policy events.

    State revision is included because average cost and verified holdings are
    state-dependent inputs to holding-risk rules.
    """
    raw = "|".join(
        [
            strategy_version,
            current_rules_hash,
            str(state_revision),
            event_type,
            symbol,
            side,
            rule_version,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def apply_event_dedup(
    candidates: list[dict[str, Any]],
    runtime: dict[str, Any],
    session_date: str,
) -> None:
    """Suppress an unchanged active event while retaining its evaluated state."""
    previous_event_states = runtime.get("event_states") or {}
    seen_delivery_ids = set(runtime.get("delivery_ids") or [])
    for candidate in candidates:
        evaluated_grade = candidate["grade"]
        delivery_id = alert_delivery_id(
            candidate["event_key"],
            session_date,
            evaluated_grade,
            str(candidate.get("signal_fingerprint") or ""),
        )
        previous = previous_event_states.get(candidate["event_key"]) or {}
        persistent_duplicate = (
            evaluated_grade in ACTIVE_EVENT_GRADES
            and previous.get("active")
            and previous.get("grade") == evaluated_grade
            and previous.get("signal_fingerprint")
            == candidate.get("signal_fingerprint")
        )
        same_delivery = delivery_id in seen_delivery_ids
        candidate["evaluated_grade"] = evaluated_grade
        candidate["delivery_id"] = delivery_id
        candidate["fingerprint"] = delivery_id
        if evaluated_grade in ACTIVE_EVENT_GRADES and (
            persistent_duplicate or same_delivery
        ):
            candidate["duplicate"] = True
            candidate["suppressed_reason"] = (
                "condition remains active with unchanged grade"
                if persistent_duplicate
                else "delivery already recorded"
            )
            candidate["grade"] = "E"


def validate_session(
    runtime: dict[str, Any], snapshot: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    session = snapshot.get("session") or {}
    if not session.get("official_calendar_verified"):
        errors.append("official exchange calendar has not verified the latest completed session")
    if session.get("calendar_verification_status") != "verified_trading_day":
        errors.append("calendar verification status is not verified_trading_day")
    if session.get("calendar_source_type") != "official_exchange_or_regulator":
        errors.append("calendar source type is not authoritative")
    if not isinstance(session.get("calendar_source"), str) or not session.get(
        "calendar_source", ""
    ).strip():
        errors.append("missing authoritative calendar source")
    try:
        verified_at = parse_iso_datetime(
            session.get("calendar_verified_at_utc"), "calendar_verified_at_utc"
        ).astimezone(timezone.utc)
        generated_at = parse_iso_datetime(
            snapshot.get("generated_at_utc"), "generated_at_utc"
        ).astimezone(timezone.utc)
        if verified_at < generated_at or (verified_at - generated_at).total_seconds() > 86400:
            errors.append("calendar verification timestamp is inconsistent with snapshot generation")
        now_utc = datetime.now(timezone.utc)
        maximum_age_hours = float(policy.get("maximum_snapshot_age_hours", 18))
        generated_age_hours = (now_utc - generated_at).total_seconds() / 3600
        verified_age_hours = (now_utc - verified_at).total_seconds() / 3600
        if not -1 <= generated_age_hours <= maximum_age_hours:
            errors.append(
                f"market snapshot is not fresh relative to this run; maximum age is {maximum_age_hours:g} hours"
            )
        if not -1 <= verified_age_hours <= maximum_age_hours:
            errors.append(
                f"calendar verification is not fresh relative to this run; maximum age is {maximum_age_hours:g} hours"
            )
    except AlertError as exc:
        errors.append(str(exc))
    if not session.get("is_trading_day"):
        errors.append("latest expected date is not a verified U.S. trading session")
    if not session.get("regular_session_complete"):
        errors.append("regular session is not complete")
    session_date = session.get("us_session_date")
    if not session_date:
        errors.append("missing U.S. session date")
    if session_date and session_date == runtime.get("last_processed_us_session"):
        errors.append("session already processed")
    expected = session.get("expected_us_session_date")
    if not expected:
        errors.append("missing authoritative expected U.S. session date")
    if expected and session_date and expected != session_date:
        errors.append(f"expected session {expected} but snapshot contains {session_date}")
    return errors


def state_integrity_errors(
    state: dict[str, Any],
    policy: dict[str, Any],
    stage_id: str,
    stage: dict[str, Any],
    session_date: str | None,
) -> list[str]:
    errors: list[str] = []
    if state.get("strategy_version") != policy.get("strategy_version"):
        errors.append("state and policy strategy versions do not match")
    broker_snapshot = state.get("last_confirmed_broker_snapshot") or {}
    if not broker_snapshot.get("verified"):
        errors.append("holdings are not reconciled to a verified user or broker snapshot")
    if not isinstance(broker_snapshot.get("source"), str) or not broker_snapshot.get(
        "source", ""
    ).strip():
        errors.append("verified holdings snapshot source is missing")
    try:
        broker_as_of = parse_iso_date(broker_snapshot.get("as_of"), "broker snapshot as_of")
        expected_date = parse_iso_date(session_date, "U.S. session date")
        maximum_age = int(policy.get("broker_snapshot_max_age_calendar_days", 4))
        snapshot_age = (expected_date - broker_as_of).days
        if snapshot_age > maximum_age:
            errors.append(
                f"verified holdings snapshot is stale by {snapshot_age} calendar days; maximum is {maximum_age}"
            )
        if snapshot_age < -1:
            errors.append("verified holdings snapshot is implausibly later than the U.S. session")
    except (AlertError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    if stage.get("status") != "active":
        errors.append(f"current stage {stage_id} is not active")
    holdings = state.get("holdings")
    if not isinstance(holdings, dict):
        errors.append("holdings object is missing")
        return errors
    for leg in stage.get("legs", []):
        symbol = leg.get("symbol")
        if symbol not in holdings:
            errors.append(f"missing verified holding quantity for {symbol}")
            continue
        current = int(holdings[symbol])
        quantity = int(leg.get("quantity", 0))
        if leg.get("side") == "sell" and quantity > current:
            errors.append(f"planned {symbol} sale exceeds verified holdings")
    return errors


def leveraged_state_integrity_errors(
    state: dict[str, Any],
    policy: dict[str, Any],
    session_date: str | None,
) -> list[str]:
    """Validate broker facts and mandates without requiring a staged plan."""
    errors: list[str] = []
    if state.get("strategy_version") != policy.get("strategy_version"):
        errors.append("state and policy strategy versions do not match")
    if state.get("strategy_mode") != "leveraged_holding_risk_and_watchlist":
        errors.append("state strategy mode does not match leveraged monitoring policy")

    broker_snapshot = state.get("last_confirmed_broker_snapshot") or {}
    if not broker_snapshot.get("verified"):
        errors.append("holdings are not reconciled to a verified user or broker snapshot")
    if not broker_snapshot.get("holdings_complete"):
        errors.append("verified broker snapshot is not marked as a complete holdings list")
    if not isinstance(broker_snapshot.get("source"), str) or not broker_snapshot.get(
        "source", ""
    ).strip():
        errors.append("verified holdings snapshot source is missing")
    try:
        broker_as_of = parse_iso_date(
            broker_snapshot.get("as_of"), "broker snapshot as_of"
        )
        expected_date = parse_iso_date(session_date, "U.S. session date")
        maximum_age = int(policy.get("broker_snapshot_max_age_calendar_days", 4))
        snapshot_age = (expected_date - broker_as_of).days
        if snapshot_age > maximum_age:
            errors.append(
                f"verified holdings snapshot is stale by {snapshot_age} calendar days; maximum is {maximum_age}"
            )
        if snapshot_age < -1:
            errors.append("verified holdings snapshot is implausibly later than the U.S. session")
    except (AlertError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    holdings = state.get("holdings")
    average_cost = state.get("average_cost_usd")
    position_cost_basis = state.get("position_cost_basis_usd")
    if not isinstance(holdings, dict):
        errors.append("holdings object is missing")
        holdings = {}
    if not isinstance(average_cost, dict):
        errors.append("average_cost_usd object is missing")
        average_cost = {}
    if not isinstance(position_cost_basis, dict):
        errors.append("position_cost_basis_usd object is missing")
        position_cost_basis = {}

    risk_policy = policy.get("holding_risk_rules") or {}
    positions = risk_policy.get("positions") or {}
    if not isinstance(positions, dict) or not positions:
        errors.append("holding risk position rules are missing")
        positions = {}
    de_minimis = risk_policy.get("de_minimis_manual_exit_positions") or {}
    if not isinstance(de_minimis, dict):
        errors.append("de-minimis manual-exit position rules are invalid")
        de_minimis = {}

    positive_holdings = {
        symbol
        for symbol, quantity in holdings.items()
        if finite_number(quantity) and int(quantity) > 0
    }
    unknown_positive = positive_holdings - set(positions) - set(de_minimis)
    if unknown_positive:
        errors.append(
            "positive holdings contain symbols with neither a holding-risk rule nor a de-minimis exception: "
            + ", ".join(sorted(unknown_positive))
        )

    missing_required = set(positions) - positive_holdings
    if missing_required:
        errors.append(
            "holding-risk policy symbols are not positive verified holdings: "
            + ", ".join(sorted(missing_required))
        )

    registry = ((policy.get("decision_harness") or {}).get("instrument_registry") or {})
    for symbol in sorted(positive_holdings):
        identity = registry.get(symbol)
        if not isinstance(identity, dict):
            errors.append(f"{symbol}: official instrument identity record is missing")
            continue
        if identity.get("identity_status") != "verified" or identity.get(
            "holding_identity_verified"
        ) is not True:
            errors.append(f"{symbol}: held-instrument identity is not verified")
        locator = identity.get("official_identity_source_url")
        if not isinstance(locator, str) or not locator.startswith("https://"):
            errors.append(f"{symbol}: official issuer identity source is missing")

    for symbol, rule in positions.items():
        quantity = holdings.get(symbol)
        if not finite_number(quantity) or int(quantity) <= 0:
            errors.append(f"missing positive verified holding quantity for {symbol}")
        cost = average_cost.get(symbol)
        if not finite_number(cost) or float(cost) <= 0:
            errors.append(f"missing positive verified average cost for {symbol}")
        loss_fraction = rule.get("maximum_loss_fraction_from_average_cost")
        if not finite_number(loss_fraction) or not 0 < float(loss_fraction) < 1:
            errors.append(f"invalid maximum-loss fraction for {symbol}")
        if rule.get("default_direction") not in {"hold", "reduce"}:
            errors.append(f"invalid default direction for {symbol}")
    for symbol, rule in de_minimis.items():
        quantity = holdings.get(symbol, 0)
        maximum_shares = rule.get("maximum_ignored_shares")
        maximum_cost_basis = rule.get("maximum_ignored_position_cost_basis_usd")
        if (
            not finite_number(quantity)
            or float(quantity) < 0
            or float(quantity) != int(float(quantity))
        ):
            errors.append(f"{symbol}: de-minimis holding quantity is invalid")
            continue
        if not isinstance(maximum_shares, int) or maximum_shares <= 0:
            errors.append(f"{symbol}: de-minimis share cap is invalid")
            continue
        if int(quantity) > maximum_shares:
            errors.append(
                f"{symbol}: de-minimis exception exceeded the exact {maximum_shares}-share cap"
            )
        if not finite_number(maximum_cost_basis) or float(maximum_cost_basis) <= 0:
            errors.append(f"{symbol}: de-minimis cost-basis cap is invalid")
        if int(quantity) > 0:
            cost = average_cost.get(symbol)
            position_cost = position_cost_basis.get(symbol)
            if not finite_number(cost) or float(cost) <= 0:
                errors.append(f"{symbol}: de-minimis average cost is missing or invalid")
            if not finite_number(position_cost) or float(position_cost) <= 0:
                errors.append(f"{symbol}: de-minimis position cost basis is missing or invalid")
            elif finite_number(maximum_cost_basis) and Decimal(
                str(position_cost)
            ) > Decimal(str(maximum_cost_basis)):
                errors.append(
                    f"{symbol}: de-minimis exception exceeded the exact USD {maximum_cost_basis} cost-basis cap"
                )
        if rule.get("status") != "approved_de_minimis_manual_exit":
            errors.append(f"{symbol}: de-minimis exception status is not approved")
        if rule.get("default_direction") != "reduce":
            errors.append(f"{symbol}: de-minimis exception direction must be reduce")
        if rule.get("quantity_authority") != "none":
            errors.append(f"{symbol}: de-minimis exception must not authorize a quantity")
    errors.extend(timing_anchor_errors(state, policy))
    return errors


def evidence_verification_record(
    row: dict[str, Any], session_date: str, technical_status: str
) -> dict[str, Any]:
    crosscheck = row.get("quote_crosscheck") or {}
    indicator = row.get("indicator_validation") or {}
    source = row.get("source")
    source_ok = isinstance(source, str) and bool(source.strip())
    crosscheck_ok = bool(
        crosscheck.get("status") == "verified"
        and crosscheck.get("independent_of_builder") is True
        and crosscheck.get("bar_date") == session_date
        and isinstance(crosscheck.get("source"), str)
        and bool(crosscheck.get("source", "").strip())
    )
    technical_ok = bool(
        technical_status == "not_required_for_raw_close_hard_risk"
        or (
            technical_status == "verified"
            and indicator.get("status") == "passed"
            and isinstance(indicator.get("formula_version"), str)
            and bool(indicator.get("formula_version", "").strip())
        )
    )
    return {
        "observation_session": session_date,
        "completed_close_price_basis": "raw_completed_regular_session_close",
        "technical_price_basis": row.get("technical_price_basis"),
        "market_data_source": source,
        "market_data_source_present": source_ok,
        "independent_close_crosscheck_status": crosscheck.get("status"),
        "independent_close_crosscheck_source": crosscheck.get("source"),
        "independent_close_crosscheck_session": crosscheck.get("bar_date"),
        "independent_close_crosscheck_verified": crosscheck_ok,
        "technical_snapshot_status": technical_status,
        "indicator_validation_status": indicator.get("status"),
        "indicator_formula_version": indicator.get("formula_version"),
        "all_required_evidence_verified": bool(source_ok and crosscheck_ok and technical_ok),
    }


def leveraged_held_symbol_errors(
    state: dict[str, Any],
    policy: dict[str, Any],
    snapshot: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    symbols = snapshot.get("symbols") or {}
    session_date = (snapshot.get("session") or {}).get("us_session_date")
    positions = ((policy.get("holding_risk_rules") or {}).get("positions") or {})
    for symbol in positions:
        row = symbols.get(symbol)
        if not isinstance(row, dict):
            errors.append(f"missing held-symbol snapshot for {symbol}")
            continue
        if row.get("bar_date") != session_date:
            errors.append(f"{symbol} held-symbol bar date does not match session")
        for field in ("open", "high", "low", "close"):
            if not finite_number(row.get(field)) or float(row.get(field, 0)) <= 0:
                errors.append(f"{symbol} held-symbol {field} is missing or invalid")
        if not finite_number(row.get("volume")) or float(row.get("volume", 0)) < 0:
            errors.append(f"{symbol} held-symbol volume is missing or invalid")
        if all(finite_number(row.get(field)) for field in ("open", "high", "low", "close")):
            if float(row["high"]) < max(float(row["open"]), float(row["close"])):
                errors.append(f"{symbol} held-symbol high violates OHLC integrity")
            if float(row["low"]) > min(float(row["open"]), float(row["close"])):
                errors.append(f"{symbol} held-symbol low violates OHLC integrity")
        if not isinstance(row.get("source"), str) or not row.get("source", "").strip():
            errors.append(f"{symbol} held-symbol market-data source is missing")
        if row.get("corporate_action_unresolved"):
            errors.append(f"{symbol} has an unresolved corporate action")
    return errors


def exact_loss_boundary(average_cost: Any, loss_fraction: Any) -> float:
    """Calculate a decimal-exact boundary and convert once for JSON output."""
    try:
        cost = Decimal(str(average_cost))
        loss = Decimal(str(loss_fraction))
        boundary = cost * (Decimal("1") - loss)
    except (InvalidOperation, ValueError) as exc:
        raise AlertError("cannot calculate maximum-loss boundary") from exc
    if cost <= 0 or not Decimal("0") < loss < Decimal("1") or boundary <= 0:
        raise AlertError("invalid inputs for maximum-loss boundary")
    return float(boundary)


def critical_symbol_errors(
    policy: dict[str, Any], snapshot: dict[str, Any], stage: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    symbols = snapshot.get("symbols") or {}
    session_date = (snapshot.get("session") or {}).get("us_session_date")
    required = {leg["symbol"] for leg in stage.get("legs", [])}
    funding_leg = stage.get("funding_leg") or {}
    funding_symbol = funding_leg.get("symbol")
    if funding_symbol:
        required.add(funding_symbol)
    required.update(policy.get("market_context_symbols", []))
    for symbol in sorted(required):
        row = symbols.get(symbol)
        if not isinstance(row, dict):
            errors.append(f"missing snapshot for {symbol}")
            continue
        if row.get("bar_date") != session_date:
            errors.append(f"{symbol} bar date does not match session")
        required_fields = ("close",) if symbol == funding_symbol else (
            "close",
            "ma20",
            "ma50",
            "ma50_5d_ago",
            "ma200",
            "rsi14",
        )
        for field in required_fields:
            if not finite_number(row.get(field)):
                errors.append(f"{symbol} missing {field}")
        if row.get("corporate_action_unresolved"):
            errors.append(f"{symbol} has an unresolved corporate action")
    return errors


def projected_cap_check(
    symbol: str,
    side: str,
    post_shares: int,
    price: float,
    snapshot: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[bool, str]:
    cap = (policy.get("exposure_caps") or {}).get(symbol)
    if cap is None:
        return True, "no symbol-specific cap"
    if side == "sell":
        return True, "sale cannot increase the symbol-specific exposure"
    account_value = (snapshot.get("account") or {}).get("account_value_usd")
    account_is_exact = (
        (snapshot.get("account") or {}).get("account_value_is_estimate") is False
    )
    if not finite_number(account_value) or account_value <= 0 or not account_is_exact:
        return False, "exact account value missing"
    weight = post_shares * price / float(account_value)
    return weight <= float(cap), f"projected_weight={weight:.4%}, cap={float(cap):.4%}"


def evaluate_leveraged_mode(
    state: dict[str, Any],
    policy: dict[str, Any],
    snapshot: dict[str, Any],
    runtime: dict[str, Any],
    result: dict[str, Any],
    current_rules_hash: str,
) -> dict[str, Any]:
    """Evaluate held-position loss boundaries before non-actionable watches."""
    session_date = str((snapshot.get("session") or {}).get("us_session_date"))
    integrity_errors = leveraged_state_integrity_errors(
        state, policy, session_date
    )
    if integrity_errors:
        result.update(state="STATE_MISMATCH", grade="F")
        result["warnings"] = integrity_errors
        return result

    data_errors = leveraged_held_symbol_errors(state, policy, snapshot)
    if data_errors:
        result.update(state="DATA_INCOMPLETE", grade="F")
        result["warnings"] = data_errors
        return result

    holdings = state["holdings"]
    average_costs = state["average_cost_usd"]
    symbol_rows = snapshot.get("symbols") or {}
    risk_policy = policy.get("holding_risk_rules") or {}
    rule_version = str(risk_policy.get("rule_version", "unversioned-risk-rule"))
    positions = risk_policy.get("positions") or {}
    hard_breached_symbols: set[str] = set()

    for symbol, rule in positions.items():
        row = symbol_rows[symbol]
        close = float(row["close"])
        average_cost = float(average_costs[symbol])
        maximum_loss = float(rule["maximum_loss_fraction_from_average_cost"])
        hard_boundary = exact_loss_boundary(average_cost, maximum_loss)
        return_from_cost = close / average_cost - 1
        breached = close <= hard_boundary
        if breached:
            hard_breached_symbols.add(symbol)
        event_key = policy_event_key(
            str(state.get("strategy_version")),
            current_rules_hash,
            state.get("state_revision"),
            "holding_max_loss_breach",
            symbol,
            "risk_review",
            rule_version,
        )
        result["candidates"].append(
            {
                "event_type": "holding_max_loss_breach",
                "symbol": symbol,
                "side": "risk_review",
                "quantity": None,
                "actionable": False,
                "current_shares": int(holdings[symbol]),
                "post_trade_shares": None,
                "average_cost_usd": average_cost,
                "close": close,
                "return_from_cost_fraction": return_from_cost,
                "maximum_loss_fraction": maximum_loss,
                "hard_boundary_usd": hard_boundary,
                "comparison_operator": "less_than_or_equal",
                "default_direction": rule.get("default_direction"),
                "horizons": list(rule.get("horizons") or []),
                "breached": breached,
                "grade": "D" if breached else "E",
                "event_key": event_key,
                "delivery_id": None,
                "duplicate": False,
                "suppressed_reason": None,
                "missing_conditions": (
                    []
                    if breached
                    else ["completed close remains above the exact maximum-loss boundary"]
                ),
                "evidence_verification": evidence_verification_record(
                    row, session_date, "not_required_for_raw_close_hard_risk"
                ),
            }
        )

        reduction_status = str(rule.get("reduction_plan_status", "not_applicable"))
        if (
            rule.get("default_direction") == "reduce"
            and reduction_status not in {"approved", "complete", "not_applicable"}
        ):
            review_key = policy_event_key(
                str(state.get("strategy_version")),
                current_rules_hash,
                state.get("state_revision"),
                "reduction_plan_required",
                symbol,
                "reduce",
                rule_version,
            )
            result["candidates"].append(
                {
                    "event_type": "reduction_plan_required",
                    "symbol": symbol,
                    "side": "reduce",
                    "quantity": None,
                    "actionable": False,
                    "current_shares": int(holdings[symbol]),
                    "post_trade_shares": None,
                    "average_cost_usd": average_cost,
                    "close": close,
                    "default_direction": "reduce",
                    "reduction_plan_status": reduction_status,
                    "grade": "B",
                    "event_key": review_key,
                    "delivery_id": None,
                    "duplicate": False,
                    "suppressed_reason": None,
                    "missing_conditions": [
                        "user-approved reduction quantity or percentage",
                        "user-approved reduction trigger or price band",
                        "user-approved deadline or completion rule",
                    ],
                }
            )

    timing_policy = policy.get("holding_timing_rules") or {}
    if timing_policy.get("status") == "approved_review_only":
        for symbol, timing_rule in (timing_policy.get("positions") or {}).items():
            proxy_symbol = timing_rule.get("confirmation_symbol")
            required = [symbol]
            if isinstance(proxy_symbol, str) and proxy_symbol and proxy_symbol != symbol:
                required.append(proxy_symbol)
            validation = validate_technical_snapshot(
                snapshot,
                required_symbols=required,
                expected_session_date=session_date,
                require_official_calendar=True,
            )
            if validation.get("status") != "verified":
                errors = validation.get("errors") or ["unknown technical validation error"]
                result["warnings"].append(
                    f"{symbol} EMA timing disabled: " + "; ".join(errors[:3])
                )
                continue
            candidate, warnings = evaluate_holding_timing(
                state=state,
                policy=policy,
                symbol=symbol,
                row=symbol_rows[symbol],
                proxy_row=symbol_rows[proxy_symbol],
                hard_boundary=exact_loss_boundary(
                    average_costs[symbol],
                    positions[symbol]["maximum_loss_fraction_from_average_cost"],
                ),
                rules_hash=current_rules_hash,
                suppress_for_hard_risk=symbol in hard_breached_symbols,
            )
            result["warnings"].extend(warnings)
            if candidate is not None:
                candidate["technical_validation_status"] = "verified"
                candidate["technical_validation_fingerprint"] = validation.get(
                    "snapshot_sha256"
                )
                candidate["evidence_verification"] = evidence_verification_record(
                    symbol_rows[symbol], session_date, "verified"
                )
                result["candidates"].append(candidate)

    broker_snapshot = state.get("last_confirmed_broker_snapshot") or {}
    available_cash = state.get("available_cash_usd")
    cash_verified = bool(broker_snapshot.get("cash_verified")) and finite_number(
        available_cash
    )
    watch_policy = policy.get("watchlist") or {}
    entry_rules_status = str(watch_policy.get("entry_rules_status", "not_approved"))
    for item in watch_policy.get("candidates") or []:
        symbol = item.get("base_symbol")
        if not isinstance(symbol, str) or not symbol:
            result["warnings"].append("watchlist contains an invalid base symbol")
            continue
        row = symbol_rows.get(symbol)
        data_available = (
            isinstance(row, dict)
            and row.get("bar_date") == session_date
            and finite_number(row.get("close"))
            and float(row.get("close", 0)) > 0
            and not row.get("corporate_action_unresolved")
        )
        if not data_available:
            result["warnings"].append(
                f"{symbol} watch-only data is unavailable; holding-risk monitoring continues"
            )
        technical_setup = None
        technical_validation_status = "not_evaluated"
        timing_rule = (timing_policy.get("watch_confirmations") or {}).get(symbol) or {}
        proxy_symbol = timing_rule.get("confirmation_symbol")
        technical_required = [symbol]
        if isinstance(proxy_symbol, str) and proxy_symbol and proxy_symbol != symbol:
            technical_required.append(proxy_symbol)
        if data_available and timing_policy.get("status") == "approved_review_only":
            validation = validate_technical_snapshot(
                snapshot,
                required_symbols=technical_required,
                expected_session_date=session_date,
                require_official_calendar=True,
            )
            technical_validation_status = str(validation.get("status"))
            if technical_validation_status == "verified":
                technical_setup = watch_setup(
                    row,
                    leveraged=bool(timing_rule.get("leveraged")),
                    proxy_row=(symbol_rows.get(proxy_symbol) if proxy_symbol else None),
                )
        if not cash_verified:
            watch_status = "watch_only_cash_unverified"
        elif float(available_cash) <= 0:
            watch_status = "watch_only_zero_cash"
        else:
            watch_status = "watch_only_entry_rules_not_approved"
        if not data_available:
            watch_status = "watch_data_unavailable"
        elif (
            timing_policy.get("status") == "approved_review_only"
            and technical_validation_status != "verified"
        ):
            watch_status = "watch_only_technical_validation_failed"
        result["watchlist"].append(
            {
                "symbol": symbol,
                "purpose": item.get("purpose"),
                "close": float(row["close"]) if data_available else None,
                "data_status": "available" if data_available else "unavailable",
                "leverage_permitted": bool(item.get("leverage_permitted")),
                "approved_leveraged_symbol": item.get("approved_leveraged_symbol"),
                "entry_rules_status": entry_rules_status,
                "verified_available_cash_usd": (
                    float(available_cash) if cash_verified else None
                ),
                "status": watch_status,
                "technical_validation_status": technical_validation_status,
                "technical_setup": technical_setup,
                "actionable": False,
                "quantity": None,
                "maximum_grade": "B",
                "evidence_verification": (
                    evidence_verification_record(
                        row, session_date, technical_validation_status
                    )
                    if data_available
                    else None
                ),
            }
        )

    apply_event_dedup(result["candidates"], runtime, session_date)
    result["risk_freeze_active"] = any(
        item.get("evaluated_grade") == "D" for item in result["candidates"]
    )
    active = [
        item
        for item in result["candidates"]
        if item.get("grade") in ACTIVE_EVENT_GRADES
    ]
    if any(item["grade"] == "D" for item in active):
        result.update(state="HARD_RISK_REVIEW", grade="D")
        set_result_headline(result, HEADLINE_PRESENT_KEY)
    elif any(item["grade"] == "B" for item in active):
        result.update(state="STRATEGY_REVIEW", grade="B")
        set_result_headline(result, HEADLINE_PRESENT_KEY)
    else:
        result.update(state="DAILY_REVIEW", grade="E")
        set_result_headline(result, HEADLINE_NONE_KEY)
    return result


def evaluate(
    state: dict[str, Any],
    policy: dict[str, Any],
    snapshot: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or {}
    current_rules_hash = rules_hash(policy)
    session = snapshot.get("session") or {}
    result: dict[str, Any] = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "strategy_version": state.get("strategy_version"),
        "rules_hash": current_rules_hash,
        "band_version": policy.get("band_version"),
        "state_updated_at": state.get("last_updated_at"),
        "us_session_date": session.get("us_session_date"),
        "expected_us_session_date": session.get("expected_us_session_date"),
        "official_calendar_verified": bool(session.get("official_calendar_verified")),
        "state": "",
        "grade": "E",
        "headline_key": HEADLINE_NONE_KEY,
        "headline": CANONICAL_ENGLISH_MESSAGES[HEADLINE_NONE_KEY],
        "candidates": [],
        "watchlist": [],
        "risk_freeze_active": False,
        "warnings": [],
        "funding_context": None,
        "evidence_validation_policy_version": (
            (policy.get("evidence_validation_policy") or {}).get("version")
        ),
    }
    session_errors = validate_session(runtime, snapshot, policy)
    if session_errors:
        if session_errors == ["session already processed"]:
            result.update(state="NO_NEW_SESSION", grade="E")
            result["warnings"] = session_errors
            return result
        result.update(state="DATA_INCOMPLETE", grade="F")
        result["warnings"] = session_errors
        return result

    if policy.get("daily_engine_scope") == "leveraged_holding_risk_and_watchlist":
        return evaluate_leveraged_mode(
            state,
            policy,
            snapshot,
            runtime,
            result,
            current_rules_hash,
        )

    stage_id = str(state.get("current_stage", "1"))
    stage = (policy.get("stages") or {}).get(stage_id)
    if not isinstance(stage, dict):
        result.update(state="STATE_MISMATCH", grade="F")
        result["warnings"] = [f"missing policy for current stage {stage_id}"]
        return result

    integrity_errors = state_integrity_errors(
        state, policy, stage_id, stage, session.get("us_session_date")
    )
    if integrity_errors:
        result.update(state="STATE_MISMATCH", grade="F")
        result["warnings"] = integrity_errors
        return result

    data_errors = critical_symbol_errors(policy, snapshot, stage)
    account = snapshot.get("account") or {}
    if "account_value_is_estimate" not in account or not isinstance(
        account.get("account_value_is_estimate"), bool
    ):
        data_errors.append("account_value_is_estimate must be explicitly true or false")
    if data_errors:
        result.update(state="DATA_INCOMPLETE", grade="F")
        result["warnings"] = data_errors
        return result

    holdings = deepcopy(state.get("holdings") or {})
    symbols = snapshot["symbols"]
    account = snapshot.get("account") or {}
    account_value = account.get("account_value_usd")
    exact_account_value = (
        finite_number(account_value)
        and float(account_value) > 0
        and account.get("account_value_is_estimate") is False
    )
    exact_available_cash = account.get("available_cash_usd")
    cash_verified = bool(
        (state.get("last_confirmed_broker_snapshot") or {}).get("cash_verified")
    ) and finite_number(exact_available_cash)

    for leg in stage.get("legs", []):
        symbol = leg["symbol"]
        side = leg["side"]
        quantity = int(leg["quantity"])
        row = symbols[symbol]
        close = float(row["close"])
        band_key = leg.get("band_key")
        band = (policy.get("approved_bands") or {}).get(band_key)
        if not isinstance(band, list) or len(band) != 2:
            result["warnings"].append(f"{symbol} has no valid approved band for {band_key}")
            continue
        in_band = inside_band(close, band)
        distance = distance_to_band(close, band)
        trend_pass, trend_reasons = trend_ok(side, row, policy.get("trend_confirmation") or {})
        current_shares = int(holdings.get(symbol, 0))
        post_shares = current_shares + quantity if side == "buy" else current_shares - quantity
        quantity_ok = post_shares >= 0 and allowed_post_trade_shares(symbol, post_shares, policy)
        cap_ok, cap_reason = projected_cap_check(
            symbol, side, post_shares, close, snapshot, policy
        )
        trade_value = close * quantity
        materiality_ok = (
            exact_account_value
            and trade_value / float(account_value) >= float(policy.get("minimum_trade_fraction", 0.02))
        )
        cap_unknown = (not cap_ok) and "exact account value missing" in cap_reason
        materiality_unknown = not exact_account_value

        grade = "E"
        if in_band and trend_pass and quantity_ok and cap_ok and materiality_ok:
            grade = "A"
        elif (
            distance <= float(policy.get("watch_distance_fraction", 0.01))
            and quantity_ok
            and (cap_ok or cap_unknown)
            and (materiality_ok or materiality_unknown)
        ):
            grade = "B"

        missing_conditions: list[str] = []
        if not in_band:
            missing_conditions.append("completed close is outside the approved band")
        if not trend_pass:
            missing_conditions.append("trend confirmation is incomplete")
        if not quantity_ok:
            missing_conditions.append("post-trade quantity rule fails")
        if not cap_ok:
            missing_conditions.append(cap_reason)
        if not materiality_ok:
            missing_conditions.append(
                "exact account value is missing"
                if materiality_unknown
                else "trade is below the configured materiality threshold"
            )

        event_key = alert_event_key(
            str(state.get("strategy_version")),
            current_rules_hash,
            "staged_trade_review",
            symbol,
            side,
            quantity,
            str(policy.get("band_version")),
            stage_id,
        )
        candidate = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "current_shares": current_shares,
            "post_trade_shares": post_shares,
            "close": close,
            "approved_band": band,
            "distance_to_band_fraction": distance,
            "trend_ok": trend_pass,
            "trend_details": trend_reasons,
            "quantity_rule_ok": quantity_ok,
            "cap_ok": cap_ok,
            "cap_detail": cap_reason,
            "materiality_ok": materiality_ok,
            "materiality_unknown": materiality_unknown,
            "grade": grade,
            "event_key": event_key,
            "delivery_id": None,
            "duplicate": False,
            "suppressed_reason": None,
            "missing_conditions": missing_conditions,
        }
        result["candidates"].append(candidate)

    prospective_buys = [
        item
        for item in result["candidates"]
        if item["side"] == "buy" and item["grade"] in {"A", "B"}
    ]
    candidate_cost = sum(item["close"] * item["quantity"] for item in prospective_buys)
    basket_linked = bool(stage.get("funding_leg"))
    cash_ok = not prospective_buys
    if basket_linked and not cash_verified:
        cash_ok = False
    elif prospective_buys and cash_verified and exact_account_value:
        required_buffer = float(policy.get("minimum_cash_buffer_fraction", 0.02))
        cash_ok = candidate_cost + float(account_value) * required_buffer <= float(exact_available_cash)
    if not cash_ok:
        for candidate in result["candidates"]:
            if candidate["grade"] in {"A", "B"} and (
                basket_linked or candidate["side"] == "buy"
            ):
                if candidate["grade"] == "A":
                    candidate["grade"] = "B"
                if "verified available cash and cash buffer are not confirmed" not in candidate["missing_conditions"]:
                    candidate["missing_conditions"].append(
                        "verified available cash and cash buffer are not confirmed"
                    )
        result["warnings"].append(
            "exact verified available cash and the post-trade cash buffer are not confirmed; linked basket candidates cannot receive grade A"
        )

    funding_leg = stage.get("funding_leg") or None
    if funding_leg:
        funding_symbol = funding_leg.get("symbol")
        funding_row = symbols.get(funding_symbol) or {}
        funding_close = funding_row.get("close")
        result["funding_context"] = {
            "symbol": funding_symbol,
            "side": funding_leg.get("side"),
            "quantity": funding_leg.get("quantity"),
            "trigger": funding_leg.get("trigger"),
            "indicative_value": (
                float(funding_close) * int(funding_leg.get("quantity", 0))
                if finite_number(funding_close)
                else None
            ),
            "actionable": False,
        }

    apply_event_dedup(
        result["candidates"], runtime, str(session.get("us_session_date"))
    )

    active = [
        item
        for item in result["candidates"]
        if item["grade"] in ACTIVE_EVENT_GRADES
    ]
    if any(item["grade"] == "D" for item in active):
        result.update(state="HARD_RISK_REVIEW", grade="D")
        set_result_headline(result, HEADLINE_PRESENT_KEY)
    elif any(item["grade"] == "A" for item in active):
        result.update(state="CANDIDATE_OPEN", grade="A")
        set_result_headline(result, HEADLINE_PRESENT_KEY)
    elif active:
        result.update(state="DAILY_REVIEW", grade="B")
        set_result_headline(result, HEADLINE_PRESENT_KEY)
    else:
        result.update(state="DAILY_REVIEW", grade="E")
        set_result_headline(result, HEADLINE_NONE_KEY)
    return result


def commit_runtime_state(
    path: Path,
    runtime: dict[str, Any],
    result: dict[str, Any],
) -> None:
    updated = deepcopy(runtime)
    updated.setdefault("schema_version", "1.0")
    updated["last_run_at"] = result.get("generated_at")
    updated["last_run_status"] = result.get("state")
    updated["last_run_grade"] = result.get("grade")
    updated["strategy_version"] = result.get("strategy_version")
    updated["rules_hash"] = result.get("rules_hash")

    if result.get("grade") != "F" and result.get("state") != "NO_NEW_SESSION":
        updated["last_processed_us_session"] = result.get("us_session_date")
        event_states = updated.setdefault("event_states", {})
        delivery_ids = list(updated.get("delivery_ids") or [])
        for candidate in result.get("candidates") or []:
            evaluated_grade = candidate.get("evaluated_grade", candidate.get("grade"))
            event_states[candidate["event_key"]] = {
                "active": evaluated_grade in ACTIVE_EVENT_GRADES,
                "grade": evaluated_grade,
                "last_seen_session": result.get("us_session_date"),
                "symbol": candidate.get("symbol"),
                "side": candidate.get("side"),
                "signal_fingerprint": candidate.get("signal_fingerprint"),
                "quantity": candidate.get("quantity"),
                "trigger_path": candidate.get("trigger_path"),
                "tranche_id": candidate.get("tranche_id"),
                "candidate_for_session": (
                    "next_regular_session"
                    if evaluated_grade in ACTIVE_EVENT_GRADES
                    else None
                ),
            }
            if (
                candidate.get("grade") in ACTIVE_EVENT_GRADES
                and not candidate.get("duplicate")
            ):
                delivery_ids.append(candidate["delivery_id"])
        updated["delivery_ids"] = list(dict.fromkeys(delivery_ids))[-1000:]

    audit_log = list(updated.get("audit_log") or [])
    audit_log.append(
        {
            "run_at": result.get("generated_at"),
            "us_session_date": result.get("us_session_date"),
            "state": result.get("state"),
            "grade": result.get("grade"),
            "headline_key": result.get("headline_key"),
            "headline": result.get("headline"),
        }
    )
    updated["audit_log"] = audit_log[-100:]

    atomic_write_text(path, json.dumps(updated, ensure_ascii=False, indent=2))


def validate_cli_paths(args: argparse.Namespace) -> None:
    read_paths = {
        "state": args.state.resolve(),
        "policy": args.policy.resolve(),
        "snapshot": args.snapshot.resolve(),
    }
    if len(set(read_paths.values())) != len(read_paths):
        raise AlertError("state, policy, and snapshot must be different files")

    protected = set(read_paths.values())
    runtime = args.runtime_state.resolve() if args.runtime_state else None
    output = args.output.resolve() if args.output else None
    output_json = output.with_suffix(".json") if output else None
    if runtime in protected:
        raise AlertError("runtime-state must not alias state, policy, or snapshot")
    if output:
        if output.suffix.lower() != ".md":
            raise AlertError("--output must use a .md suffix")
        if output in protected or output_json in protected:
            raise AlertError("output files must not alias state, policy, or snapshot")
        if runtime is not None and runtime in {output, output_json}:
            raise AlertError("runtime-state must not alias either output file")


def rendered_headline(result: dict[str, Any], messages: dict[str, str]) -> str:
    key = result.get("headline_key")
    if key not in {HEADLINE_PRESENT_KEY, HEADLINE_NONE_KEY}:
        key = (
            HEADLINE_PRESENT_KEY
            if result.get("grade") in ACTIVE_EVENT_GRADES
            else HEADLINE_NONE_KEY
        )
    return messages[key]


def render_markdown_legacy(
    result: dict[str, Any], output_locale: str = DEFAULT_OUTPUT_LOCALE
) -> str:
    messages = load_output_messages(output_locale)
    lines = [
        f"# {rendered_headline(result, messages)}",
        "",
        f"- State: {result['state']}",
        f"- Grade: {result['grade']}",
        f"- Strategy version: {result.get('strategy_version')}",
        f"- Rules hash: {result.get('rules_hash')}",
        f"- U.S. session / expected: {result.get('us_session_date')} / {result.get('expected_us_session_date')}",
        f"- Official calendar verified: {result.get('official_calendar_verified')}",
        f"- State updated at: {result.get('state_updated_at')}",
    ]
    if result["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"][:10])
    candidates = [item for item in result["candidates"] if item["grade"] != "E"]
    if candidates:
        lines.extend(["", "## Next-session review candidates", ""])
        for item in candidates:
            lines.extend(
                [
                    f"### {item['symbol']} - {item['grade']}",
                    f"- Side / quantity: {item['side']} / {item['quantity']}",
                    f"- Current close / band: {item['close']} / {item['approved_band']}",
                    f"- Current -> post-trade shares: {item['current_shares']} -> {item['post_trade_shares']}",
                    f"- Trend / quantity / cap / materiality: {item['trend_ok']} / {item['quantity_rule_ok']} / {item['cap_ok']} / {item['materiality_ok']}",
                    f"- Missing conditions: {item.get('missing_conditions') or ['none']}",
                    f"- Fingerprint: {item['fingerprint']}",
                    "- Validity: next regular session only; cancel after a gap outside the band or any state/rule change.",
                    "",
                ]
            )
    elif result["grade"] == "E":
        lines.extend(["", "No actionable candidate. Review only the most important unmet conditions above.", ""])
    lines.append(messages["no_order_notice"])
    return "\n".join(lines)


def render_markdown(
    result: dict[str, Any], output_locale: str = DEFAULT_OUTPUT_LOCALE
) -> str:
    messages = load_output_messages(output_locale)
    lines = [
        f"# {rendered_headline(result, messages)}",
        "",
        f"- State: {result['state']}",
        f"- Grade: {result['grade']}",
        f"- Strategy version: {result.get('strategy_version')}",
        f"- Rules hash: {result.get('rules_hash')}",
        f"- U.S. session / expected: {result.get('us_session_date')} / {result.get('expected_us_session_date')}",
        f"- Official calendar verified: {result.get('official_calendar_verified')}",
        f"- State updated at: {result.get('state_updated_at')}",
        f"- Holding-risk freeze active: {result.get('risk_freeze_active', False)}",
    ]
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"][:10])

    candidates = [
        item for item in result.get("candidates", []) if item.get("grade") != "E"
    ]
    if candidates:
        lines.extend(["", "## Next-session review candidates", ""])
        for item in candidates:
            event_type = item.get("event_type", "staged_trade_review")
            if event_type == "holding_max_loss_breach":
                lines.extend(
                    [
                        f"### {item['symbol']} - {item['grade']} hard-risk review",
                        f"- Shares / direction: {item['current_shares']} / {item['default_direction']}",
                        f"- Average cost / completed close: {item['average_cost_usd']} / {item['close']}",
                        f"- Return from cost: {item['return_from_cost_fraction']:.4%}",
                        f"- Exact unrounded boundary: {item['hard_boundary_usd']}",
                        "- Quantity / actionable: null / false",
                        f"- Fingerprint: {item['fingerprint']}",
                        "- Validity: next regular session review only; no automatic stop or order.",
                        "",
                    ]
                )
            elif event_type == "reduction_plan_required":
                lines.extend(
                    [
                        f"### {item['symbol']} - {item['grade']} reduction-plan review",
                        f"- Shares / direction: {item['current_shares']} / reduce",
                        "- Quantity / actionable: null / false",
                        f"- Missing conditions: {item.get('missing_conditions') or ['none']}",
                        f"- Fingerprint: {item['fingerprint']}",
                        "- Validity: policy review only; do not infer a sell quantity.",
                        "",
                    ]
                )
            elif event_type in {"holding_timing_review", "holding_timing_watch"}:
                lines.extend(
                    [
                        f"### {item['symbol']} - {item['grade']} {messages['staged_reduction_review']}",
                        f"- Trigger / tranche: {item.get('trigger_path')} / {item.get('tranche_id')}",
                        f"- Review quantity: {item.get('quantity')} shares",
                        f"- Current / post-review shares: {item.get('current_shares')} / {item.get('post_trade_shares')}",
                        f"- Completed close / technical stop: {item.get('close')} / {item.get('technical_stop_level_usd')}",
                        f"- Confirmation proxy: {item.get('proxy_symbol')}",
                        f"- Technical validation: {item.get('technical_validation_status')}",
                        f"- Watch-only / rearm gate: {item.get('watch_only')} / {item.get('rearm_gate')}",
                        f"- Fingerprint: {item['fingerprint']}",
                        "- Validity: next regular-session review only; a confirmed fill is required before the next tranche unlocks.",
                        "- Actionable: false; no order was placed or scheduled.",
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"### {item['symbol']} - {item['grade']}",
                        f"- Side / quantity: {item['side']} / {item['quantity']}",
                        f"- Current close / band: {item['close']} / {item['approved_band']}",
                        f"- Current / post-trade shares: {item['current_shares']} / {item['post_trade_shares']}",
                        f"- Trend / quantity / cap / materiality: {item['trend_ok']} / {item['quantity_rule_ok']} / {item['cap_ok']} / {item['materiality_ok']}",
                        f"- Missing conditions: {item.get('missing_conditions') or ['none']}",
                        f"- Fingerprint: {item['fingerprint']}",
                        "- Validity: next regular session only; cancel after a gap outside the band or any state/rule change.",
                        "",
                    ]
                )
    elif result.get("grade") == "E":
        lines.extend(
            [
                "",
                "No new actionable candidate. Risk monitoring and watchlist review only.",
                "",
            ]
        )

    if result.get("watchlist"):
        lines.extend(["", "## Non-actionable watchlist", ""])
        for item in result["watchlist"]:
            lines.append(
                f"- {item['symbol']}: status={item['status']}, close={item['close']}, actionable=false, quantity=null, approved_leveraged_symbol={item['approved_leveraged_symbol']}"
            )
    lines.append(messages["no_order_notice"])
    return "\n".join(lines)


def self_test() -> None:
    policy = {
        "strategy_version": "test",
        "band_version": "v1",
        "tracking_symbols": ["AAA"],
        "zero_target_exceptions": [],
        "market_context_symbols": [],
        "exposure_caps": {"AAA": 0.5},
        "minimum_trade_fraction": 0.01,
        "minimum_cash_buffer_fraction": 0.02,
        "watch_distance_fraction": 0.01,
        "trend_confirmation": {"buy_minimum_pass_count": 3, "sell_rsi_minimum": 55},
        "approved_bands": {"aaa_buy_1": [99, 101]},
        "stages": {
            "1": {
                "status": "active",
                "legs": [
                    {"symbol": "AAA", "side": "buy", "quantity": 4, "band_key": "aaa_buy_1"}
                ],
            }
        },
    }
    now = datetime.now(timezone.utc)
    state = {
        "strategy_version": "test",
        "current_stage": 1,
        "holdings": {"AAA": 1},
        "last_confirmed_broker_snapshot": {
            "verified": True,
            "cash_verified": True,
            "source": "self-test",
            "as_of": "2026-07-30",
        },
    }
    snapshot = {
        "generated_at_utc": now.isoformat(),
        "session": {
            "is_trading_day": True,
            "regular_session_complete": True,
            "us_session_date": "2026-07-30",
            "expected_us_session_date": "2026-07-30",
            "official_calendar_verified": True,
            "calendar_verification_status": "verified_trading_day",
            "calendar_source_type": "official_exchange_or_regulator",
            "calendar_source": "https://example.test/official-calendar",
            "calendar_verified_at_utc": now.isoformat(),
        },
        "account": {
            "account_value_usd": 10000,
            "account_value_is_estimate": False,
            "available_cash_usd": 1000,
        },
        "symbols": {
            "AAA": {
                "bar_date": "2026-07-30",
                "close": 100,
                "ma20": 98,
                "ma50": 97,
                "ma50_5d_ago": 96,
                "ma200": 90,
                "rsi14": 60,
            }
        },
    }
    result = evaluate(state, policy, snapshot, {})
    assert result["grade"] == "A"
    assert result["candidates"][0]["post_trade_shares"] == 5
    candidate = result["candidates"][0]
    runtime = {
        "last_processed_us_session": None,
        "event_states": {
            candidate["event_key"]: {"active": True, "grade": "A"}
        },
        "delivery_ids": [],
    }
    duplicate = evaluate(state, policy, snapshot, runtime)
    assert duplicate["grade"] == "E"
    assert duplicate["candidates"][0]["duplicate"] is True
    unverified = deepcopy(snapshot)
    unverified["session"]["official_calendar_verified"] = False
    failed = evaluate(state, policy, unverified, {})
    assert failed["grade"] == "F"
    missing_expected = deepcopy(snapshot)
    missing_expected["session"]["expected_us_session_date"] = None
    assert evaluate(state, policy, missing_expected, {})["grade"] == "F"

    stale_calendar = deepcopy(snapshot)
    stale_time = datetime(2026, 6, 1, tzinfo=timezone.utc).isoformat()
    stale_calendar["generated_at_utc"] = stale_time
    stale_calendar["session"]["calendar_verified_at_utc"] = stale_time
    assert evaluate(state, policy, stale_calendar, {})["grade"] == "F"

    estimated_nav = deepcopy(snapshot)
    estimated_nav["account"]["account_value_is_estimate"] = True
    estimated_result = evaluate(state, policy, estimated_nav, {})
    assert estimated_result["grade"] != "A"
    missing_estimate_flag = deepcopy(snapshot)
    del missing_estimate_flag["account"]["account_value_is_estimate"]
    assert evaluate(state, policy, missing_estimate_flag, {})["grade"] == "F"

    stale_state = deepcopy(state)
    stale_state["last_confirmed_broker_snapshot"]["as_of"] = "2026-07-01"
    assert evaluate(stale_state, policy, snapshot, {})["grade"] == "F"

    linked_policy = deepcopy(policy)
    linked_policy["stages"]["1"]["funding_leg"] = {
        "symbol": "AAA",
        "side": "sell",
        "quantity": 0,
        "trigger": "linked self-test",
    }
    linked_policy["approved_bands"]["aaa_sell_1"] = [99, 101]
    linked_policy["stages"]["1"]["legs"] = [
        {"symbol": "AAA", "side": "sell", "quantity": 4, "band_key": "aaa_sell_1"}
    ]
    linked_state = deepcopy(state)
    linked_state["holdings"]["AAA"] = 5
    linked_state["last_confirmed_broker_snapshot"]["cash_verified"] = False
    linked_result = evaluate(linked_state, linked_policy, snapshot, {})
    assert linked_result["candidates"][0]["grade"] == "B"

    risk_policy = {
        "strategy_version": "risk-test-v2",
        "daily_engine_scope": "leveraged_holding_risk_and_watchlist",
        "broker_snapshot_max_age_calendar_days": 4,
        "decision_harness": {
            "instrument_registry": {
                "SOXL": {
                    "identity_status": "verified",
                    "holding_identity_verified": True,
                    "official_identity_source_url": "https://www.direxion.com/product/daily-semiconductor-bull-bear-3x-etfs",
                },
                "MVLL": {
                    "identity_status": "verified",
                    "holding_identity_verified": True,
                    "official_identity_source_url": "https://graniteshares.com/etfs/mvll/",
                },
            }
        },
        "holding_risk_rules": {
            "rule_version": "risk-boundary-v1",
            "positions": {
                "SOXL": {
                    "horizons": ["short", "medium"],
                    "default_direction": "hold",
                    "maximum_loss_fraction_from_average_cost": 0.20,
                    "reduction_plan_status": "not_applicable",
                },
                "MVLL": {
                    "horizons": ["short", "medium"],
                    "default_direction": "reduce",
                    "maximum_loss_fraction_from_average_cost": 0.60,
                    "reduction_plan_status": "pending_user_quantity_and_trigger",
                },
            },
        },
        "watchlist": {
            "entry_rules_status": "not_approved",
            "candidates": [
                {
                    "base_symbol": "DRAM",
                    "purpose": "new_position_watch",
                    "leverage_permitted": True,
                    "approved_leveraged_symbol": None,
                },
                {
                    "base_symbol": "NBIS",
                    "purpose": "new_position_watch",
                    "leverage_permitted": True,
                    "approved_leveraged_symbol": None,
                },
                {
                    "base_symbol": "BE",
                    "purpose": "new_position_watch",
                    "leverage_permitted": True,
                    "approved_leveraged_symbol": None,
                },
                {
                    "base_symbol": "SOXL",
                    "purpose": "possible_add_on_watch",
                    "leverage_permitted": True,
                    "approved_leveraged_symbol": "SOXL",
                },
            ],
        },
    }
    risk_state = {
        "strategy_version": "risk-test-v2",
        "state_revision": 3,
        "strategy_mode": "leveraged_holding_risk_and_watchlist",
        "current_stage": None,
        "holdings": {"SOXL": 99, "MVLL": 396},
        "average_cost_usd": {"SOXL": 123.32, "MVLL": 41.78},
        "position_cost_basis_usd": {"SOXL": 12208.68, "MVLL": 16544.88},
        "available_cash_usd": 0.0,
        "last_confirmed_broker_snapshot": {
            "verified": True,
            "holdings_complete": True,
            "cash_verified": True,
            "source": "self-test complete snapshot",
            "as_of": "2026-07-30",
        },
    }
    risk_snapshot = deepcopy(snapshot)
    risk_snapshot["account"] = {}
    risk_snapshot["symbols"] = {
        "SOXL": {
            "bar_date": "2026-07-30",
            "open": 99.0,
            "high": 100.0,
            "low": 98.0,
            "close": 98.656,
            "volume": 1000000,
            "source": "self-test market data",
            "corporate_action_unresolved": False,
        },
        "MVLL": {
            "bar_date": "2026-07-30",
            "open": 16.8,
            "high": 17.0,
            "low": 16.6,
            "close": 16.713,
            "volume": 1000000,
            "source": "self-test market data",
            "corporate_action_unresolved": False,
        },
        "NBIS": {
            "bar_date": "2026-07-30",
            "close": 50.0,
            "corporate_action_unresolved": False,
        },
    }
    boundary_result = evaluate(risk_state, risk_policy, risk_snapshot, {})
    assert boundary_result["grade"] == "D"
    soxl_risk = next(
        item
        for item in boundary_result["candidates"]
        if item["symbol"] == "SOXL"
        and item["event_type"] == "holding_max_loss_breach"
    )
    mvll_risk = next(
        item
        for item in boundary_result["candidates"]
        if item["symbol"] == "MVLL"
        and item["event_type"] == "holding_max_loss_breach"
    )
    mvll_review = next(
        item
        for item in boundary_result["candidates"]
        if item["event_type"] == "reduction_plan_required"
    )
    assert soxl_risk["hard_boundary_usd"] == 98.656
    assert soxl_risk["breached"] is True
    assert mvll_risk["hard_boundary_usd"] == 16.712
    assert mvll_risk["breached"] is False
    assert mvll_review["grade"] == "B"
    assert mvll_review["quantity"] is None
    assert len(boundary_result["watchlist"]) == 4
    assert all(item["actionable"] is False for item in boundary_result["watchlist"])
    assert all(item["quantity"] is None for item in boundary_result["watchlist"])
    assert next(
        item for item in boundary_result["watchlist"] if item["symbol"] == "DRAM"
    )["approved_leveraged_symbol"] is None
    assert boundary_result["state"] != "STATE_MISMATCH"

    above_policy = deepcopy(risk_policy)
    above_policy["holding_risk_rules"]["positions"]["MVLL"][
        "reduction_plan_status"
    ] = "approved"
    above_snapshot = deepcopy(risk_snapshot)
    above_snapshot["symbols"]["SOXL"]["close"] = 98.657
    above_snapshot["symbols"]["MVLL"]["close"] = 16.713
    above_result = evaluate(risk_state, above_policy, above_snapshot, {})
    assert above_result["grade"] == "E"

    mvll_boundary_snapshot = deepcopy(above_snapshot)
    mvll_boundary_snapshot["symbols"]["MVLL"]["close"] = 16.712
    mvll_boundary_result = evaluate(
        risk_state, above_policy, mvll_boundary_snapshot, {}
    )
    assert mvll_boundary_result["grade"] == "D"

    duplicate_runtime = {
        "last_processed_us_session": None,
        "event_states": {
            item["event_key"]: {
                "active": True,
                "grade": item["evaluated_grade"],
            }
            for item in boundary_result["candidates"]
            if item["evaluated_grade"] in ACTIVE_EVENT_GRADES
        },
        "delivery_ids": [],
    }
    duplicate_risk = evaluate(
        risk_state, risk_policy, risk_snapshot, duplicate_runtime
    )
    assert duplicate_risk["grade"] == "E"
    assert all(
        item["duplicate"]
        for item in duplicate_risk["candidates"]
        if item["evaluated_grade"] in ACTIVE_EVENT_GRADES
    )
    recovered = evaluate(risk_state, risk_policy, above_snapshot, duplicate_runtime)
    recovered_soxl = next(
        item
        for item in recovered["candidates"]
        if item["symbol"] == "SOXL"
        and item["event_type"] == "holding_max_loss_breach"
    )
    assert recovered_soxl["evaluated_grade"] == "E"
    reentry_runtime = {
        "event_states": {
            soxl_risk["event_key"]: {"active": False, "grade": "E"}
        },
        "delivery_ids": [],
    }
    assert evaluate(risk_state, risk_policy, risk_snapshot, reentry_runtime)[
        "grade"
    ] == "D"

    positive_cash_state = deepcopy(risk_state)
    positive_cash_state["available_cash_usd"] = 1000.0
    positive_cash_watch = evaluate(
        positive_cash_state, above_policy, above_snapshot, {}
    )["watchlist"]
    assert all(item["actionable"] is False for item in positive_cash_watch)
    assert all(
        item["status"] in {"watch_only_entry_rules_not_approved", "watch_data_unavailable"}
        for item in positive_cash_watch
    )

    missing_held_snapshot = deepcopy(risk_snapshot)
    del missing_held_snapshot["symbols"]["MVLL"]
    assert evaluate(risk_state, risk_policy, missing_held_snapshot, {})[
        "grade"
    ] == "F"
    assert load_output_messages("ko-KR")["no_order_notice"] in render_markdown(
        boundary_result, "ko-KR"
    )
    assert CANONICAL_ENGLISH_MESSAGES["no_order_notice"] in render_markdown(
        boundary_result, "en-US"
    )

    temporary_root = Path.cwd()
    prefix = f".alert_self_test_{os.getpid()}"
    runtime_path = temporary_root / f"{prefix}_runtime.json"
    state_path = temporary_root / f"{prefix}_state.json"
    policy_path = temporary_root / f"{prefix}_policy.json"
    snapshot_path = temporary_root / f"{prefix}_snapshot.json"
    report_path = temporary_root / f"{prefix}_report.md"
    lock_path = temporary_root / f"{prefix}.lock"
    cleanup_paths = [
        runtime_path,
        state_path,
        policy_path,
        snapshot_path,
        report_path,
        report_path.with_suffix(".json"),
        lock_path,
    ]
    try:
        commit_runtime_state(runtime_path, {}, result)
        persisted = read_json(runtime_path)
        assert persisted["last_processed_us_session"] == "2026-07-30"
        assert candidate["event_key"] in persisted["event_states"]
        assert candidate["delivery_id"] in persisted["delivery_ids"]
        for path in (state_path, policy_path, snapshot_path):
            path.write_text("{}", encoding="utf-8")
        alias_args = argparse.Namespace(
            state=state_path,
            policy=policy_path,
            snapshot=snapshot_path,
            runtime_state=state_path,
            output=report_path,
        )
        try:
            validate_cli_paths(alias_args)
            raise AssertionError("path alias should fail")
        except AlertError:
            pass
        with exclusive_run_lock(lock_path):
            try:
                with exclusive_run_lock(lock_path):
                    raise AssertionError("concurrent lock acquisition should fail")
            except AlertError:
                pass
    finally:
        for path in cleanup_paths:
            path.unlink(missing_ok=True)
    print("Self-test passed")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--runtime-state", type=Path)
    parser.add_argument("--commit-runtime", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--output-locale",
        choices=SUPPORTED_OUTPUT_LOCALES,
        default=DEFAULT_OUTPUT_LOCALE,
        help="Presentation locale only; core evaluation and JSON remain English.",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.state, args.policy, args.snapshot)):
        parser.error("--state, --policy, and --snapshot are required")
    if args.commit_runtime and not args.runtime_state:
        parser.error("--runtime-state is required with --commit-runtime")
    try:
        validate_cli_paths(args)
        lock_path = (
            args.runtime_state.resolve().with_name(args.runtime_state.name + ".lock")
            if args.runtime_state
            else args.output.resolve().with_name(args.output.name + ".lock")
            if args.output
            else Path(tempfile.gettempdir()) / "evaluate-alerts.lock"
        )
        with exclusive_run_lock(lock_path):
            runtime = read_optional_json(args.runtime_state)
            result = evaluate(
                read_json(args.state),
                read_json(args.policy),
                read_json(args.snapshot),
                runtime,
            )
            markdown = render_markdown(result, args.output_locale)
            if args.output:
                atomic_write_text(args.output, markdown)
                atomic_write_text(
                    args.output.with_suffix(".json"),
                    json.dumps(result, ensure_ascii=False, indent=2),
                )
            if args.commit_runtime and args.runtime_state:
                commit_runtime_state(args.runtime_state, runtime, result)
            print(markdown)
            return 0 if result["grade"] != "F" else 2
    except AlertError as exc:
        print(f"ALERT_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
