#!/usr/bin/env python3
"""Compile a file-first, read-only portfolio manual-advisory dashboard.

This module performs deterministic arithmetic only.  It never calls a broker,
market-data provider, SEC endpoint, scheduler, or order path, and it never
mutates portfolio or policy state.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import subprocess
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
PLAN_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-plan.schema.json"
DASHBOARD_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-dashboard.schema.json"
MANUAL_EVIDENCE_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
DEFAULT_RISK_POLICY = ROOT / "manage-us-stock-strategy/assets/portfolio-decision-risk-envelope-v0.2.json"
DEFAULT_OUTPUT_ROOT = ROOT / "workspace/outputs/portfolio-decision-dashboard"
ALLOWED_MODES = {"INITIAL_COMPILE", "POST_SELL_RECOMPILE", "HISTORICAL_REPLAY"}
CURRENT_PLAN_STATUS = "CURRENT_APPROVED"


class ContractError(ValueError):
    """Raised when an input contract is structurally or semantically invalid."""


def _finite(value: Any, *, minimum: float | None = None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        return None
    return result


def _integer_quantity(value: Any) -> int | None:
    number = _finite(value, minimum=0)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _ticker(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    if not normalized or len(normalized) > 24:
        return None
    return normalized


def _value(value: float | int | None, label: str, unit: str) -> dict[str, Any]:
    return {"value": value, "value_status": label, "unit": unit}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if len(value) == 40 else None


def implementation_provenance_paths(risk_path: Path) -> list[Path]:
    return [
        Path(__file__).resolve(), Path(__file__).with_name("validation_common.py"),
        MANUAL_EVIDENCE_SCHEMA, PLAN_SCHEMA, DASHBOARD_SCHEMA, risk_path.resolve(),
    ]


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _floor_shares(nav: Any, target_weight_pct: Any, price: Any) -> int | None:
    nav_value = _decimal(nav)
    target_value = _decimal(target_weight_pct)
    price_value = _decimal(price)
    if nav_value is None or target_value is None or price_value is None or price_value <= 0:
        return None
    return int((nav_value * target_value / Decimal("100") / price_value).to_integral_value(rounding=ROUND_FLOOR))


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def validate_plan(
    plan: dict[str, Any], schema_path: Path = PLAN_SCHEMA, *, schema_bytes: bytes | None = None,
) -> list[str]:
    errors = validate_instance(plan, schema_path, schema_bytes=schema_bytes)
    seen: set[str] = set()
    for index, position in enumerate(plan.get("positions") or []):
        ticker = _ticker(position.get("ticker")) if isinstance(position, dict) else None
        if ticker is None:
            continue
        if ticker in seen:
            errors.append(f"$.positions[{index}]: DUPLICATE_TICKER:{ticker}")
        seen.add(ticker)
        weight = position.get("target_weight_pct")
        if weight is not None and (_finite(weight, minimum=0) is None or float(weight) > 100):
            errors.append(f"$.positions[{index}].target_weight_pct: TARGET_WEIGHT_OUTSIDE_0_100")
    cash_target = plan.get("cash_target_pct")
    if cash_target is not None and (_finite(cash_target, minimum=0) is None or float(cash_target) > 100):
        errors.append("$.cash_target_pct: CASH_TARGET_OUTSIDE_0_100")
    supplied = [p.get("target_weight_pct") for p in plan.get("positions", []) if p.get("target_weight_pct") is not None]
    supplied_total = sum((_decimal(value) or Decimal("0")) for value in supplied)
    if supplied_total > Decimal("100"):
        errors.append("$: TARGET_ALLOCATION_EXCEEDS_100_PERCENT")
    if cash_target is not None:
        cash_decimal = _decimal(cash_target)
        if cash_decimal is not None and supplied_total + cash_decimal > Decimal("100"):
            errors.append("$: TARGET_ALLOCATION_EXCEEDS_100_PERCENT")
    priority = plan.get("buy_priority") or []
    unknown_priority = [item for item in priority if item not in seen]
    if unknown_priority:
        errors.append("$.buy_priority: UNKNOWN_TICKER:" + ",".join(unknown_priority))
    return sorted(set(errors))


def _extract_holdings(evidence: dict[str, Any]) -> tuple[dict[str, int], dict[str, float], list[str], str]:
    broker = evidence.get("broker_observed_state") or {}
    issues: list[str] = []
    holdings: dict[str, int] = {}
    costs: dict[str, float] = {}
    if broker.get("status") != "AVAILABLE":
        return {}, {}, ["BROKER_HOLDINGS_NOT_AVAILABLE"], "BROKER_OBSERVED_STATE"
    raw = broker.get("holdings")
    if not isinstance(raw, list) or not raw:
        return {}, {}, ["MISSING_HOLDINGS"], "BROKER_OBSERVED_STATE"
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            issues.append(f"INVALID_HOLDING_RECORD:{index}")
            continue
        ticker = _ticker(item.get("ticker"))
        quantity = _integer_quantity(item.get("held_quantity"))
        if ticker is None or quantity is None:
            issues.append(f"INVALID_HOLDING_CORE_FIELDS:{index}")
            continue
        if ticker in holdings:
            issues.append(f"DUPLICATE_BROKER_TICKER:{ticker}")
            continue
        holdings[ticker] = quantity
        average_cost = _finite(item.get("average_cost"), minimum=0)
        if average_cost is not None:
            costs[ticker] = average_cost
    if not holdings:
        issues.append("MISSING_HOLDINGS")
    return holdings, costs, issues, "BROKER_OBSERVED_STATE"


def _extract_cash(evidence: dict[str, Any]) -> tuple[float | None, float | None, list[str]]:
    broker = evidence.get("broker_observed_state") or {}
    cash = broker.get("cash") or {}
    issues: list[str] = []
    current_cash = _finite(cash.get("foreign_currency_deposit"), minimum=0)
    if cash.get("cash_status") not in {"VERIFIED_POSITIVE", "VERIFIED_ZERO"}:
        current_cash = None
    if current_cash is None:
        issues.append("MISSING_CURRENT_CASH")
    verified_orderable = _finite(evidence.get("verified_orderable_cash_usd"), minimum=0)
    if evidence.get("orderable_cash_status") != "VERIFIED" or verified_orderable is None:
        verified_orderable = None
        issues.append("MISSING_VERIFIED_ORDERABLE_CASH")
    return current_cash, verified_orderable, issues


def _extract_prices(evidence: dict[str, Any], required: set[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    prices: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    for item in evidence.get("last_verified_finalized_bars") or []:
        if not isinstance(item, dict):
            continue
        ticker = _ticker(item.get("ticker"))
        bar = item.get("bar") or {}
        price = _finite(bar.get("price"), minimum=0)
        valid = bool(
            ticker and price and item.get("status") == "VERIFIED"
            and item.get("session_authority_status") == "VERIFIED"
            and bar.get("bar_finalized") is True
            and bar.get("stable") is True
            and bar.get("comparable_to_regular_close") is True
            and bar.get("market_session_type") == "REGULAR_COMPLETED"
            and bar.get("price_basis") == "RAW_REGULAR_SESSION_CLOSE"
            and bar.get("currency") == "USD"
        )
        if valid:
            prices[ticker] = {
                "price": price,
                "value_status": "VERIFIED",
                "basis": "RAW_REGULAR_SESSION_CLOSE",
                "session": item.get("bar_date") or bar.get("reported_session"),
                "provider": bar.get("provider"),
                "provider_timestamp": bar.get("provider_timestamp"),
            }
    for ticker in sorted(required - set(prices)):
        issues.append(f"MISSING_VERIFIED_CANONICAL_PRICE:{ticker}")
    return prices, issues


def _instrument_mapping(
    ticker: str, risk_policy: dict[str, Any], registry: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    fallback = (risk_policy.get("fallback_instrument_mapping") or {}).get(ticker)
    registered = ((registry or {}).get("instruments") or {}).get(ticker)
    if fallback is None and registered is None:
        return None, "RISK_MAPPING_REQUIRED"
    if fallback is None:
        factor = _finite(registered.get("leverage_factor"), minimum=0)
        if factor is None or registered.get("leverage_factor_status") not in {
            "verified", "verified_by_existing_active_policy"
        }:
            return None, "RISK_MAPPING_UNVERIFIED"
        instrument_class = "NORMAL_STOCK" if factor == 1 else "LEVERAGED_PRODUCT"
        return {
            "instrument_class": instrument_class,
            "leverage_factor": factor,
            "growth_ai_semiconductor_cluster": registered.get("theme") in {
                "ai_infrastructure", "leveraged_semiconductor", "semiconductor"
            },
            "mapping_source": "INSTRUMENT_REGISTRY",
        }, None
    mapping = dict(fallback)
    mapping["mapping_source"] = "USER_APPROVED_FALLBACK"
    if registered is not None:
        registered_factor = _finite(registered.get("leverage_factor"), minimum=0)
        if registered_factor is not None and not math.isclose(
            registered_factor, float(fallback["leverage_factor"]), rel_tol=0, abs_tol=1e-12,
        ):
            return None, "RISK_MAPPING_CONFLICT"
        if registered_factor is not None:
            mapping["mapping_source"] = "INSTRUMENT_REGISTRY_CONFIRMED"
    return mapping, None


def _risk_status(value: float | None, *, low: float | None = None, high: float | None = None,
                 hard_low: float | None = None, hard_high: float | None = None) -> str:
    if value is None:
        return "BLOCKED"
    if hard_low is not None and value < hard_low - 1e-9:
        return "VIOLATION"
    if hard_high is not None and value > hard_high + 1e-9:
        return "VIOLATION"
    if low is not None and value < low - 1e-9:
        return "WARNING"
    if high is not None and value > high + 1e-9:
        return "WARNING"
    return "PASS"


def calculate_risk_metrics(
    weights: dict[str, float], cash_pct: float | None,
    mappings: dict[str, dict[str, Any]], policy: dict[str, Any],
) -> dict[str, Any]:
    leveraged = sum(weight for ticker, weight in weights.items() if mappings[ticker]["leverage_factor"] > 1)
    cluster_book = sum(weight for ticker, weight in weights.items() if mappings[ticker]["growth_ai_semiconductor_cluster"])
    cluster_adjusted = sum(
        weight * mappings[ticker]["leverage_factor"] for ticker, weight in weights.items()
        if mappings[ticker]["growth_ai_semiconductor_cluster"]
    )
    overall_adjusted = sum(weight * mappings[ticker]["leverage_factor"] for ticker, weight in weights.items())
    checks: list[dict[str, Any]] = []
    cash_rule = policy["cash"]
    checks.append({"metric": "CASH_PCT", "value": cash_pct,
                   "status": _risk_status(cash_pct, low=cash_rule["target_min_pct"], high=cash_rule["target_max_pct"], hard_low=cash_rule["hard_floor_pct"])})
    lev_rule = policy["all_daily_reset_leveraged_products"]
    checks.append({"metric": "LEVERAGED_PRODUCTS_PCT", "value": leveraged,
                   "status": _risk_status(leveraged, low=lev_rule["target_min_pct"], high=lev_rule["target_max_pct"], hard_high=lev_rule["hard_cap_pct"])})
    for ticker, weight in sorted(weights.items()):
        klass = mappings[ticker]["instrument_class"]
        rule = None
        if klass == "SINGLE_3X_ETF":
            rule = policy["single_3x_etf"]
        elif klass == "SINGLE_2X_SINGLE_STOCK_ETF":
            rule = policy["single_2x_single_stock_etf"]
        elif klass == "NORMAL_STOCK":
            rule = policy["single_normal_stock"]
        if rule:
            checks.append({"metric": f"POSITION_PCT:{ticker}", "value": weight,
                           "status": _risk_status(weight, low=rule["target_min_pct"], high=rule["target_max_pct"], hard_high=rule["hard_cap_pct"])})
    cluster_rule = policy["growth_ai_semiconductor_cluster"]
    checks.extend([
        {"metric": "GROWTH_AI_SEMI_BOOK_PCT", "value": cluster_book,
         "status": _risk_status(cluster_book, hard_high=cluster_rule["book_hard_cap_pct"])},
        {"metric": "GROWTH_AI_SEMI_LEVERAGE_ADJUSTED_PCT", "value": cluster_adjusted,
         "status": _risk_status(cluster_adjusted, hard_high=cluster_rule["leverage_adjusted_hard_cap_pct"])},
    ])
    overall_rule = policy["overall_leverage_adjusted_exposure_proxy"]
    checks.append({"metric": "OVERALL_LEVERAGE_ADJUSTED_PROXY_PCT", "value": overall_adjusted,
                   "status": _risk_status(overall_adjusted, low=overall_rule["target_min_pct"], high=overall_rule["target_max_pct"], hard_high=overall_rule["hard_cap_pct"])})
    violations = [item["metric"] for item in checks if item["status"] == "VIOLATION"]
    aggregate_status = (
        "VIOLATION" if violations else
        "BLOCKED" if any(i["status"] == "BLOCKED" for i in checks) else
        "WARNING" if any(i["status"] == "WARNING" for i in checks) else "PASS"
    )
    return {
        "cash_pct": _value(cash_pct, "DERIVED" if cash_pct is not None else "PROVISIONAL", "PCT"),
        "leveraged_products_pct": _value(leveraged, "DERIVED", "PCT"),
        "growth_ai_semiconductor_book_pct": _value(cluster_book, "DERIVED", "PCT"),
        "growth_ai_semiconductor_leverage_adjusted_pct": _value(cluster_adjusted, "DERIVED", "PCT"),
        "overall_leverage_adjusted_proxy_pct": _value(overall_adjusted, "DERIVED", "PCT"),
        "checks": checks,
        "hard_cap_violations": violations,
        "status": aggregate_status,
    }


def _event_context(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"status": "NOT_PROVIDED", "current_high_count": None, "new_high_count": None,
                "affected_tickers": [], "automatic_target_change": False}
    summary = value.get("summary") or {}
    high = value.get("current_high_count", summary.get("current_high_count", 0))
    new = value.get("new_high_count", summary.get("new_high_count", 0))
    affected = value.get("affected_tickers", summary.get("affected_tickers", []))
    status = value.get("status") or ("ASSET_REVIEW_REQUIRED" if high or new or affected else "AVAILABLE")
    return {"status": status, "current_high_count": int(high or 0), "new_high_count": int(new or 0),
            "affected_tickers": sorted({_ticker(item) for item in affected if _ticker(item)}),
             "automatic_target_change": False}


def _canonical_evidence_gate(
    evidence: dict[str, Any], plan: dict[str, Any], compile_mode: str, schema_bytes: bytes,
) -> tuple[list[str], list[str], set[str]]:
    schema_errors = validate_instance(evidence, MANUAL_EVIDENCE_SCHEMA, schema_bytes=schema_bytes)
    schema = json.loads(schema_bytes.decode("utf-8"))
    phases = set(schema["properties"]["market_phase"]["enum"])
    blockers = [f"CANONICAL_EVIDENCE_SCHEMA_INVALID:{item}" for item in schema_errors]
    required_values = {
        "EVIDENCE_GRADE_NOT_GRADE_B": evidence.get("evidence_grade") == "GRADE_B",
        "MANUAL_DATA_NOT_VERIFIED_REAL": evidence.get("manual_data_verification_status") == "VERIFIED_REAL_DATA",
        "RUN_PROVENANCE_NOT_VERIFIED_MANUAL": evidence.get("run_provenance_status") == "VERIFIED_MANUAL",
        "PREFLIGHT_NOT_PASS": evidence.get("preflight_status") == "PASS",
        "BROKER_SNAPSHOT_NOT_AVAILABLE": evidence.get("broker_snapshot_status") == "AVAILABLE",
        "BROKER_OBSERVED_STATE_NOT_AVAILABLE": (evidence.get("broker_observed_state") or {}).get("status") == "AVAILABLE",
        "ORDERABLE_CASH_NOT_VERIFIED": evidence.get("orderable_cash_status") == "VERIFIED",
        "FINALIZED_BAR_PREFLIGHT_NOT_PASS": evidence.get("finalized_bar_preflight_status") == "PASS",
        "FINALIZED_BAR_NOT_VERIFIED": evidence.get("last_verified_finalized_bar_status") == "VERIFIED",
        "IDENTITY_AUTHORITY_NOT_VERIFIED": evidence.get("identity_authority_status") == "VERIFIED",
        "SESSION_AUTHORITY_NOT_VERIFIED": evidence.get("session_authority_status") == "VERIFIED",
        "AUTHORITY_COHORT_NOT_MATCHED": evidence.get("integrated_authority_cohort_status") == "MATCHED",
        "DECISION_QUALITY_NOT_ELIGIBLE": (evidence.get("provenance") or {}).get("decision_quality_eligible") is True,
    }
    blockers.extend(reason for reason, satisfied in required_values.items() if not satisfied)
    operations = (evidence.get("broker_observed_state") or {}).get("operation_statuses") or {}
    for operation in ("account_holdings_read", "account_deposit_read"):
        if not isinstance(operations, dict) or operations.get(operation) != "PASS":
            blockers.append(f"CORE_BROKER_OPERATION_NOT_PASS:{operation}")

    decision_time = _parse_timestamp(evidence.get("decision_as_of"))
    observed_time = _parse_timestamp(evidence.get("observed_at"))
    broker_time = _parse_timestamp(evidence.get("broker_snapshot_as_of"))
    if decision_time is None or observed_time is None or broker_time is None:
        blockers.append("EVIDENCE_FRESHNESS_TIMESTAMP_INVALID")
    else:
        if observed_time > decision_time or broker_time > decision_time:
            blockers.append("EVIDENCE_FROM_FUTURE")
        if (decision_time - broker_time).total_seconds() > 900:
            blockers.append("BROKER_SNAPSHOT_STALE")

    evidence_run_id = evidence.get("manual_run_id")
    evidence_as_of = evidence.get("decision_as_of")
    binding = plan.get("evidence_binding") or {}
    if compile_mode == "POST_SELL_RECOMPILE":
        refresh = plan.get("post_sell_refresh") or {}
        if not refresh:
            blockers.append("POST_SELL_REFRESH_BINDING_REQUIRED")
        if (refresh.get("prior_run_id"), refresh.get("prior_decision_as_of")) != (
            binding.get("expected_run_id"), binding.get("expected_decision_as_of"),
        ):
            blockers.append("POST_SELL_PRIOR_BINDING_MISMATCH")
        if evidence_run_id == refresh.get("prior_run_id"):
            blockers.append("POST_SELL_FRESH_RUN_REQUIRED")
        current_time = _parse_timestamp(evidence_as_of)
        prior_time = _parse_timestamp(refresh.get("prior_decision_as_of"))
        if current_time is None or prior_time is None or current_time <= prior_time:
            blockers.append("POST_SELL_DECISION_AS_OF_NOT_LATER")
        plan_time = _parse_timestamp(plan.get("as_of"))
        if plan_time is None or prior_time is None or plan_time > prior_time:
            blockers.append("PLAN_AS_OF_AFTER_BOUND_EVIDENCE")
    else:
        if evidence_run_id != binding.get("expected_run_id"):
            blockers.append("EVIDENCE_RUN_ID_BINDING_MISMATCH")
        if evidence_as_of != binding.get("expected_decision_as_of"):
            blockers.append("EVIDENCE_DECISION_AS_OF_BINDING_MISMATCH")
        plan_time = _parse_timestamp(plan.get("as_of"))
        evidence_time = _parse_timestamp(evidence_as_of)
        if plan_time is None or evidence_time is None or plan_time > evidence_time:
            blockers.append("PLAN_AS_OF_AFTER_BOUND_EVIDENCE")
    return schema_errors, sorted(set(blockers)), phases


def compile_dashboard(
    evidence: dict[str, Any], plan: dict[str, Any], risk_policy: dict[str, Any],
    *, compile_mode: str = "INITIAL_COMPILE", registry: dict[str, Any] | None = None,
    event_context: dict[str, Any] | None = None, run_id: str = "portfolio-decision-test",
    generated_at: str | None = None, runtime_advisory_authority: str | None = None,
    evidence_schema_bytes: bytes | None = None, plan_schema_bytes: bytes | None = None,
    dashboard_schema_bytes: bytes | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if compile_mode not in ALLOWED_MODES:
        raise ContractError("INVALID_COMPILE_MODE")
    evidence_schema_bytes = evidence_schema_bytes or MANUAL_EVIDENCE_SCHEMA.read_bytes()
    plan_schema_bytes = plan_schema_bytes or PLAN_SCHEMA.read_bytes()
    dashboard_schema_bytes = dashboard_schema_bytes or DASHBOARD_SCHEMA.read_bytes()
    plan_errors = validate_plan(plan, schema_bytes=plan_schema_bytes)
    if plan_errors:
        raise ContractError("DECISION_PLAN_INVALID:" + "; ".join(plan_errors))
    evidence_schema_errors, evidence_gate_blockers, canonical_phases = _canonical_evidence_gate(
        evidence, plan, compile_mode, evidence_schema_bytes,
    )
    positions = {item["ticker"]: item for item in plan["positions"]}
    holdings, costs, holding_issues, holding_source = _extract_holdings(evidence)
    current_cash, orderable_cash, cash_issues = _extract_cash(evidence)
    required_tickers = set(holdings) | set(positions)
    prices, price_issues = _extract_prices(evidence, required_tickers)
    issues = holding_issues + cash_issues + price_issues + evidence_gate_blockers
    warnings: list[str] = []
    input_authority_blockers: list[str] = []
    if evidence.get("order_authority") is not False:
        input_authority_blockers.append("INPUT_ORDER_AUTHORITY_NOT_FALSE")
    if evidence.get("execution_quantity") is not None:
        input_authority_blockers.append("INPUT_EXECUTION_QUANTITY_NOT_NULL")
    broker_input = evidence.get("broker_observed_state") or {}
    if broker_input.get("portfolio_mutation") is True or broker_input.get("canonical_apply") is True:
        input_authority_blockers.append("INPUT_PORTFOLIO_MUTATION_DETECTED")
    issues.extend(input_authority_blockers)
    if evidence.get("broker_diff_status") == "DIFFERENT":
        warnings.append("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL")
    operations = (evidence.get("broker_observed_state") or {}).get("operation_statuses") or {}
    open_items_status = operations.get("account_open_items") if isinstance(operations, dict) else None
    if open_items_status != "PASS":
        warnings.append("OPEN_ITEMS_VISIBILITY_UNAVAILABLE")
    if (evidence.get("broker_observed_state") or {}).get("scope_complete") is not True:
        warnings.append("AUXILIARY_SCOPE_INCOMPLETE_CORE_MAY_REMAIN_VERIFIED")
    if not operations:
        request_accounting_status = "ABSENT"
    elif not isinstance(operations, dict) or any(
        not isinstance(name, str) or not name or not isinstance(status, str) or not status
        for name, status in operations.items()
    ):
        request_accounting_status = "PRESENT_INVALID"
        warnings.append("REQUEST_ACCOUNTING_INVALID")
    else:
        request_accounting_status = "PRESENT_UNVERIFIED"
        warnings.append("REQUEST_ACCOUNTING_NOT_CANONICALLY_VERIFIABLE")

    mappings: dict[str, dict[str, Any]] = {}
    for ticker in sorted(required_tickers):
        mapping, mapping_issue = _instrument_mapping(ticker, risk_policy, registry)
        if mapping_issue:
            issues.append(f"{mapping_issue}:{ticker}")
        elif mapping:
            mappings[ticker] = mapping

    nav: float | None = None
    values: dict[str, float] = {}
    weights: dict[str, float] = {}
    positive_holdings = {ticker for ticker, quantity in holdings.items() if quantity > 0}
    if current_cash is not None and holdings and all(ticker in prices for ticker in positive_holdings):
        values = {
            ticker: quantity * prices[ticker]["price"] if quantity > 0 else 0.0
            for ticker, quantity in holdings.items()
        }
        nav = current_cash + sum(values.values())
        if nav <= 0:
            nav = None
            issues.append("NAV_NOT_POSITIVE")
        else:
            weights = {ticker: value / nav * 100.0 for ticker, value in values.items()}
    else:
        issues.append("NAV_BLOCKED_REQUIRED_CORE_EVIDENCE")
    core_blockers = bool(
        holding_issues or current_cash is None
        or input_authority_blockers
        or evidence_gate_blockers
        or any(issue.endswith(tuple(f":{ticker}" for ticker in positive_holdings)) for issue in price_issues)
    )
    evidence_contract_verified = not evidence_gate_blockers
    core_status = (
        "BLOCKED" if nav is None or core_blockers else
        "VERIFIED" if evidence_contract_verified else "PARTIAL"
    )
    current_risk = None
    if nav is not None and set(weights) <= set(mappings):
        current_risk = calculate_risk_metrics(weights, current_cash / nav * 100.0, mappings, risk_policy)
    current_violations = set((current_risk or {}).get("hard_cap_violations") or [])
    target_weights = {
        ticker: float(item["target_weight_pct"]) for ticker, item in positions.items()
        if item.get("target_weight_pct") is not None and ticker in mappings
    }
    target_risk = calculate_risk_metrics(
        target_weights, float(plan["cash_target_pct"]) if plan.get("cash_target_pct") is not None else None,
        mappings, risk_policy,
    ) if set(target_weights) <= set(mappings) else None
    target_violations = set((target_risk or {}).get("hard_cap_violations") or [])

    position_rows: list[dict[str, Any]] = []
    all_tickers = sorted(set(holdings) | set(positions))
    for ticker in all_tickers:
        source = positions.get(ticker)
        current_quantity = holdings.get(ticker, 0)
        price = prices.get(ticker, {}).get("price")
        current_weight = weights.get(ticker) if nav is not None else None
        blockers: list[str] = []
        if source is None:
            blockers.append("BLOCKED_DECISION_PLAN_POSITION_REQUIRED")
            source = {"ticker": ticker, "action": "HOLD", "target_status": "BLOCKED",
                      "rationale": "Decision Plan entry required", "investment_horizon": "Not specified"}
        target_weight = source.get("target_weight_pct")
        if target_weight is None:
            blockers.append("BLOCKED_TARGET_WEIGHT_REQUIRED")
        if price is None:
            blockers.append("BLOCKED_CANONICAL_PRICE_REQUIRED")
        if ticker not in mappings:
            blockers.append("BLOCKED_RISK_MAPPING_REQUIRED")
        if nav is None:
            blockers.append("BLOCKED_NAV_REQUIRED")
        target_shares = None
        delta = None
        if not blockers and target_weight is not None and price and nav is not None:
            target_shares = _floor_shares(nav, target_weight, price)
            delta = target_shares - current_quantity
        if target_violations:
            blockers.append("TARGET_HARD_CAP_VIOLATION")
            delta = None
        deadband = False
        if (delta is not None and current_weight is not None and target_weight is not None
                and abs(float(target_weight) - current_weight) < risk_policy["deadband"]["absolute_percentage_points"]
                and not current_violations and not target_violations
                and not blockers and source.get("thesis_kill") is not True):
            deadband = True
            delta = 0
        direction_conflict = bool(
            delta is not None and ((source["action"] in {"TRIM", "EXIT"} and delta > 0)
                                   or (source["action"] == "ADD" and delta < 0))
        )
        if direction_conflict:
            blockers.append("ACTION_TARGET_DIRECTION_CONFLICT")
            delta = None
        position_rows.append({
            "ticker": ticker,
            "action": source["action"],
            "target_status": source["target_status"],
            "current_quantity": _value(current_quantity, "VERIFIED" if ticker in holdings else "DERIVED", "SHARES"),
            "average_cost_usd": _value(costs.get(ticker), "VERIFIED" if ticker in costs else "NOT_VERIFIED", "USD"),
            "canonical_price_usd": _value(price, "VERIFIED" if price is not None else "NOT_VERIFIED", "USD"),
            "price_session": prices.get(ticker, {}).get("session"),
            "current_market_value_usd": _value(values.get(ticker, 0.0 if nav is not None else None), "DERIVED" if nav is not None else "PROVISIONAL", "USD"),
            "current_weight_pct": _value(current_weight, "DERIVED" if current_weight is not None else "PROVISIONAL", "PCT"),
            "target_weight_pct": _value(float(target_weight) if target_weight is not None else None, "VERIFIED" if target_weight is not None else "NOT_VERIFIED", "PCT"),
            "target_shares_reference": _value(target_shares, "DERIVED" if target_shares is not None else "PROVISIONAL", "SHARES"),
            "share_delta": _value(delta, "DERIVED" if delta is not None else "PROVISIONAL", "SHARES"),
            "deadband_status": "NO_TRADE_PREFERRED" if deadband else "NOT_APPLIED",
            "calculation_status": "BLOCKED" if blockers else ("NO_TRADE_PREFERRED" if deadband else "CALCULATED_MANUAL_ADVISORY"),
            "blockers": sorted(set(blockers)),
            "rationale": source["rationale"],
            "investment_horizon": source["investment_horizon"],
            "material_risk": source.get("material_risk"),
            "decision_change_triggers": source.get("decision_change_triggers") or [],
        })

    replay = compile_mode == "HISTORICAL_REPLAY" or plan["plan_status"] in {"HISTORICAL", "REPLAY_ONLY"}
    stage1_rows: list[dict[str, Any]] = []
    for row in position_rows:
        delta = row["share_delta"]["value"]
        if row["action"] not in {"TRIM", "EXIT"}:
            continue
        sell = abs(delta) if isinstance(delta, int) and delta < 0 else 0 if delta == 0 else None
        stage1_rows.append({
            "ticker": row["ticker"], "action": row["action"],
            "current_shares": row["current_quantity"]["value"],
            "target_shares_reference": row["target_shares_reference"]["value"],
            "calculated_sell_shares": sell,
            "current_weight_pct": row["current_weight_pct"]["value"],
            "target_weight_pct": row["target_weight_pct"]["value"],
            "reason": row["rationale"], "risk_violation_addressed": sorted(current_violations),
            "status": row["calculation_status"], "blockers": row["blockers"],
        })
    sell_rows = [row for row in stage1_rows if isinstance(row["calculated_sell_shares"], int) and row["calculated_sell_shares"] > 0]
    expected_proceeds = None
    if sell_rows and all(row["ticker"] in prices for row in sell_rows):
        expected_proceeds = sum(row["calculated_sell_shares"] * prices[row["ticker"]]["price"] for row in sell_rows)
    post_sell_estimated_cash = (
        current_cash + expected_proceeds if current_cash is not None and expected_proceeds is not None else None
    )
    if any(row["calculated_sell_shares"] is None for row in stage1_rows) or nav is None:
        stage1_status = "BLOCKED"
    elif replay:
        stage1_status = "REPLAY_ONLY"
    elif evidence.get("market_phase") not in canonical_phases or evidence.get("market_phase") != "REGULAR_COMPLETED":
        stage1_status = "PROVISIONAL"
    elif evidence.get("current_session_finalization_status") != "VERIFIED":
        stage1_status = "PROVISIONAL"
    elif plan["plan_status"] != CURRENT_PLAN_STATUS or any(row.get("target_status") != "APPROVED" for row in position_rows):
        stage1_status = "PROVISIONAL"
    elif core_status == "VERIFIED":
        stage1_status = "FINAL_MANUAL_ADVISORY_ELIGIBLE"
    else:
        stage1_status = "BLOCKED"

    add_rows = [row for row in position_rows if row["action"] == "ADD"]
    buy_rows = [row for row in add_rows if isinstance(row["share_delta"]["value"], int) and row["share_delta"]["value"] > 0]
    buy_advisories: list[dict[str, Any]] = []
    stage2_blockers: list[str] = []
    post_initial_buy_cash = None
    if replay:
        stage2_status = "REPLAY_ONLY"
        stage2_blockers.append("HISTORICAL_PLAN_CANNOT_CREATE_CURRENT_BUY_ADVISORY")
    elif compile_mode != "POST_SELL_RECOMPILE":
        stage2_status = "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED"
        stage2_blockers.append("BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED")
    elif orderable_cash is None:
        stage2_status = "BLOCKED"
        stage2_blockers.append("VERIFIED_ORDERABLE_CASH_REQUIRED")
    elif core_status != "VERIFIED":
        stage2_status = "BLOCKED"
        stage2_blockers.append("POST_SELL_CANONICAL_EVIDENCE_NOT_VERIFIED")
    elif evidence.get("market_phase") not in {"REGULAR_INTRADAY", "REGULAR_COMPLETED"}:
        stage2_status = "BLOCKED"
        stage2_blockers.append("POST_SELL_SESSION_NOT_ELIGIBLE")
    elif plan["plan_status"] != CURRENT_PLAN_STATUS or any(row.get("target_status") != "APPROVED" for row in position_rows):
        stage2_status = "PROVISIONAL"
        stage2_blockers.append("CURRENT_APPROVED_PLAN_REQUIRED")
    elif any(row["blockers"] for row in add_rows):
        stage2_status = "BLOCKED"
        stage2_blockers.append("BUY_INPUT_BLOCKED")
    else:
        requested_cost = 0.0
        capped_gaps: dict[str, int] = {}
        for row in buy_rows:
            gap = int(row["share_delta"]["value"])
            if int(row["current_quantity"]["value"]) == 0:
                full_target = int(row["target_shares_reference"]["value"])
                entry_fraction = _decimal(risk_policy["new_position_initial_entry"]["maximum_fraction_of_full_target"])
                capped_target = int((Decimal(full_target) * entry_fraction).to_integral_value(rounding=ROUND_FLOOR))
                gap = min(gap, capped_target)
            capped_gaps[row["ticker"]] = max(0, gap)
            requested_cost += capped_gaps[row["ticker"]] * prices[row["ticker"]]["price"]
        eligible_gaps = {ticker: gap for ticker, gap in capped_gaps.items() if gap > 0}
        priority = plan.get("buy_priority") or []
        insufficient_cash = requested_cost > orderable_cash + 1e-9
        eligible = set(eligible_gaps)
        if insufficient_cash and not priority:
            stage2_status = "BLOCKED"
            stage2_blockers.append("BUY_ALLOCATION_PRIORITY_REQUIRED")
        elif insufficient_cash and (len(priority) != len(eligible) or set(priority) != eligible):
            stage2_status = "BLOCKED"
            stage2_blockers.append("BUY_ALLOCATION_PRIORITY_INCOMPLETE")
        else:
            order = list(priority) if insufficient_cash else [
                item["ticker"] for item in plan["positions"] if item["ticker"] in eligible_gaps
            ]
            cash_left = orderable_cash
            simulated_holdings = dict(holdings)
            allocations = {ticker: 0 for ticker in eligible_gaps}
            for ticker in order:
                price = prices[ticker]["price"]
                maximum = min(eligible_gaps[ticker], _floor_shares(cash_left, 100, price) or 0)
                for _ in range(maximum):
                    candidate_holdings = dict(simulated_holdings)
                    candidate_holdings[ticker] = candidate_holdings.get(ticker, 0) + 1
                    candidate_values = {name: qty * prices[name]["price"] for name, qty in candidate_holdings.items()}
                    candidate_weights = {name: value / nav * 100.0 for name, value in candidate_values.items()} if nav else {}
                    candidate_cash_pct = (cash_left - price) / nav * 100.0 if nav else None
                    candidate_risk = calculate_risk_metrics(candidate_weights, candidate_cash_pct, mappings, risk_policy)
                    if candidate_risk["hard_cap_violations"]:
                        break
                    simulated_holdings = candidate_holdings
                    cash_left -= price
                    allocations[ticker] += 1
            for ticker in order:
                buy_advisories.append({
                    "ticker": ticker,
                    "target_gap_shares": eligible_gaps[ticker],
                    "calculated_buy_shares": allocations[ticker],
                    "price_usd": prices[ticker]["price"],
                    "estimated_cost_usd": allocations[ticker] * prices[ticker]["price"],
                    "quantity_status": "CALCULATED_MANUAL_ADVISORY",
                })
            post_initial_buy_cash = cash_left
            stage2_status = "FINAL_MANUAL_ADVISORY_ELIGIBLE"

    event = _event_context(event_context)
    generated = generated_at or _now()
    current_authority_eligible = (
        stage1_status == "FINAL_MANUAL_ADVISORY_ELIGIBLE"
        or stage2_status == "FINAL_MANUAL_ADVISORY_ELIGIBLE"
    )
    derived_runtime_authority = (
        "CURRENT_MANUAL_ADVISORY_ELIGIBLE" if current_authority_eligible else "NOT_VERIFIED_BY_RUNTIME"
    )
    report = {
        "schema_version": "1.0",
        "report_type": "PORTFOLIO_DECISION_DASHBOARD_MANUAL_ADVISORY",
        "run_id": run_id,
        "generated_at": generated,
        "compile_mode": compile_mode,
        "evidence": {
            "portfolio_evidence_status": core_status,
            "evidence_grade": evidence.get("evidence_grade", "NOT_VERIFIED"),
            "portfolio_evidence_grade_display": "GRADE_B_AT_ARTIFACT_TIME" if replay and evidence.get("evidence_grade") == "GRADE_B" else evidence.get("evidence_grade", "NOT_VERIFIED"),
            "run_id": evidence.get("manual_run_id") or evidence.get("run_id"),
            "decision_as_of": evidence.get("decision_as_of"),
            "market_phase": evidence.get("market_phase"),
            "decision_quality_eligible": (evidence.get("provenance") or {}).get("decision_quality_eligible") is True,
            "holding_source": holding_source,
            "broker_system_mismatch": evidence.get("broker_diff_status"),
            "scope_complete": (evidence.get("broker_observed_state") or {}).get("scope_complete") is True,
            "open_items_status": open_items_status or "NOT_AVAILABLE",
            "request_accounting_status": request_accounting_status,
            "request_accounting": dict(sorted(operations.items())) if isinstance(operations, dict) else {},
            "canonical_schema_sha256": _sha256_bytes(evidence_schema_bytes),
            "canonical_schema_errors": evidence_schema_errors,
            "failure_code": "GRADE_B_SCHEMA_INVALID" if evidence_schema_errors else None,
            "canonical_gate_blockers": evidence_gate_blockers,
            "issues": sorted(set(issues)),
            "warnings": sorted(set(warnings)),
            "current_freshness": "HISTORICAL_REPLAY" if replay else (
                "CURRENT_AT_ARTIFACT_TIME" if stage1_status == "FINAL_MANUAL_ADVISORY_ELIGIBLE" else "LAST_KNOWN"
            ),
        },
        "plan": {
            "plan_id": plan["plan_id"], "as_of": plan["as_of"], "plan_status": plan["plan_status"],
            "target_type": plan["target_type"], "cash_target_pct": plan.get("cash_target_pct"),
            "evidence_binding": plan["evidence_binding"],
            "post_sell_refresh": plan.get("post_sell_refresh"),
            "material_unknowns": plan.get("material_unknowns") or [],
            "decision_change_triggers": plan.get("decision_change_triggers") or [],
            "temporal_status": "HISTORICAL_REPLAY" if replay else "CURRENT_OR_PROVISIONAL",
        },
        "portfolio": {
            "nav_usd": _value(nav, "DERIVED" if nav is not None else "PROVISIONAL", "USD"),
            "positions": position_rows,
            "current_risk": current_risk,
            "target_reference_risk": target_risk,
            "risk_mapping_status": "CONFLICT" if any("RISK_MAPPING_CONFLICT" in issue for issue in issues) else (
                "BLOCKED" if any("RISK_MAPPING_" in issue for issue in issues) else "VERIFIED_OR_CONFIRMED_FALLBACK"
            ),
        },
        "stage1": {
            "status": stage1_status,
            "sell_advisories": stage1_rows,
            "expected_sale_proceeds_usd": _value(expected_proceeds, "ESTIMATED" if expected_proceeds is not None else "PROVISIONAL", "USD"),
            "post_sell_estimated_cash_usd": _value(post_sell_estimated_cash, "ESTIMATED" if post_sell_estimated_cash is not None else "PROVISIONAL", "USD"),
            "order_created": False,
        },
        "stage2": {
            "status": stage2_status,
            "verified_orderable_cash_usd": _value(orderable_cash, "VERIFIED" if orderable_cash is not None else "NOT_VERIFIED", "USD"),
            "buy_candidates": [row["ticker"] for row in buy_rows],
            "buy_candidate_references": [
                {"ticker": row["ticker"], "target_shares_reference": row["target_shares_reference"]["value"]}
                for row in add_rows
            ],
            "buy_advisories": buy_advisories,
            "blockers": sorted(set(stage2_blockers)),
            "order_created": False,
        },
        "cash_semantics": {
            "current_cash_usd": _value(current_cash, "VERIFIED" if current_cash is not None else "NOT_VERIFIED", "USD"),
            "verified_orderable_cash_usd": _value(orderable_cash, "VERIFIED" if orderable_cash is not None else "NOT_VERIFIED", "USD"),
            "post_sell_estimated_cash_usd": _value(post_sell_estimated_cash, "ESTIMATED" if post_sell_estimated_cash is not None else "PROVISIONAL", "USD"),
            "post_initial_buy_estimated_cash_usd": _value(post_initial_buy_cash, "ESTIMATED" if post_initial_buy_cash is not None else "PROVISIONAL", "USD"),
            "full_target_reference_cash_pct": _value(float(plan["cash_target_pct"]) if plan.get("cash_target_pct") is not None else None,
                                                        "VERIFIED" if plan.get("cash_target_pct") is not None else "NOT_VERIFIED", "PCT"),
            "full_target_reference_cash_usd": _value(
                nav * float(plan["cash_target_pct"]) / 100.0 if nav is not None and plan.get("cash_target_pct") is not None else None,
                "DERIVED" if nav is not None and plan.get("cash_target_pct") is not None else "PROVISIONAL", "USD",
            ),
            "expected_proceeds_treated_as_orderable_cash": False,
        },
        "event_context": event,
        "authority": {
            "artifact_time_quantity_authority": evidence.get("quantity_authority", "none"),
            "current_runtime_advisory_authority": derived_runtime_authority,
            "runtime_authority_cli_input": runtime_advisory_authority,
            "runtime_authority_cli_input_effect": "DISPLAY_ONLY_NO_AUTHORITY_EFFECT" if runtime_advisory_authority else "NOT_PROVIDED",
            "manual_advisory_label": "CALCULATED_MANUAL_ADVISORY",
            "broker_order_authority": False,
            "execution_quantity": None,
            "automatic_order": False,
        },
        "safety": {
            "network_access": False, "kiwoom_call": False, "broker_call": False,
            "sec_live_request": False, "save_access": False, "task_scheduler_mutation": False,
            "portfolio_mutation": False, "policy_mutation": False, "orders": "NONE",
        },
    }
    schema_errors = validate_instance(report, DASHBOARD_SCHEMA, schema_bytes=dashboard_schema_bytes)
    stage2_gate_verified = bool(
        compile_mode == "POST_SELL_RECOMPILE"
        and core_status == "VERIFIED"
        and evidence.get("market_phase") in {"REGULAR_INTRADAY", "REGULAR_COMPLETED"}
        and orderable_cash is not None
        and plan["plan_status"] == CURRENT_PLAN_STATUS
        and not evidence_gate_blockers
    )
    invariants = {
        "dashboard_schema": not schema_errors,
        "order_authority_false": report["authority"]["broker_order_authority"] is False,
        "execution_quantity_null": report["authority"]["execution_quantity"] is None,
        "automatic_order_false": report["authority"]["automatic_order"] is False,
        "expected_proceeds_not_orderable": report["cash_semantics"]["expected_proceeds_treated_as_orderable_cash"] is False,
        "canonical_evidence_schema": not evidence_schema_errors,
        "canonical_evidence_gate_enforced": not current_authority_eligible or not evidence_gate_blockers,
        "stage2_firewall": stage2_status != "FINAL_MANUAL_ADVISORY_ELIGIBLE" or stage2_gate_verified,
        "portfolio_mutation_false": report["safety"]["portfolio_mutation"] is False,
        "policy_mutation_false": report["safety"]["policy_mutation"] is False,
        "network_false": report["safety"]["network_access"] is False,
    }
    validation_status = "FAIL" if schema_errors or evidence_schema_errors or not all(invariants.values()) else (
        "BLOCKED" if core_status == "BLOCKED" else "PASS"
    )
    validation = {
        "schema_version": "1.0", "run_id": run_id, "generated_at": generated,
        "status": validation_status, "schema_errors": schema_errors,
        "invariants": invariants, "input_issues": sorted(set(issues)),
        "network_used": False, "broker_used": False, "order_path_used": False,
    }
    return report, validation


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "확인 필요"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _render_markdown_legacy(report: dict[str, Any]) -> str:
    stage1 = report["stage1"]
    stage2 = report["stage2"]
    conclusion = "위험 축소 우선" if any((row.get("calculated_sell_shares") or 0) > 0 for row in stage1["sell_advisories"]) else (
        "매수 검토" if stage2["buy_advisories"] else "현금 유지 / 보유 검토"
    )
    lines = [
        "# 포트폴리오 조정안", "",
        f"- 기준 시각: {report['evidence'].get('decision_as_of') or '확인 필요'}",
        f"- Evidence Grade: {report['evidence']['portfolio_evidence_grade_display']}",
        f"- 시장 상태: {report['evidence'].get('market_phase') or '확인 필요'}",
        f"- 오늘의 결론: **{conclusion}**", "",
        "> 이 문서는 계산된 수동 검토 자료입니다. 매수·매도 주문을 만들거나 전송하지 않습니다.", "",
        "## 지금 할 일 — 1단계", "",
        f"상태: {stage1['status']}", "",
        "| 종목 | 현재 주수 | 목표 참고 주수 | 수동 매도 참고 | 현재 비중 | 목표 비중 | 이유 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    if stage1["sell_advisories"]:
        for row in stage1["sell_advisories"]:
            lines.append(
                f"| {row['ticker']} | {_fmt(row['current_shares'])} | {_fmt(row['target_shares_reference'])} | "
                f"{_fmt(row['calculated_sell_shares'])} | {_fmt(row['current_weight_pct'])}% | "
                f"{_fmt(row['target_weight_pct'])}% | {row['reason']} |"
            )
    else:
        lines.append("| 해당 없음 | - | - | - | - | - | 현재 계획에 축소·정리 항목 없음 |")
    lines += ["", "## 2단계 매수", "", f"상태: {stage2['status']}", ""]
    if stage2["status"] == "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED":
        lines.append("매도 체결 후 Kiwoom 계좌를 다시 확인해야 매수 수량을 계산할 수 있습니다.")
    if stage2["buy_advisories"]:
        lines += ["", "| 종목 | 계산된 수동 매수 참고 | 예상 소요액 |", "|---|---:|---:|"]
        for row in stage2["buy_advisories"]:
            lines.append(f"| {row['ticker']} | {_fmt(row['calculated_buy_shares'])}주 | ${_fmt(row['estimated_cost_usd'])} |")
    else:
        candidates = ", ".join(stage2["buy_candidates"]) or "없음"
        lines += [f"매수 후보: {candidates}", "", "현재 최종 매수 수량: 계산 금지 / BLOCKED"]
    lines += ["", "## 종목별 판단 카드", ""]
    action_ko = {"ADD": "늘림", "HOLD": "유지", "TRIM": "축소", "EXIT": "정리 검토"}
    for row in report["portfolio"]["positions"]:
        lines += [
            f"### {row['ticker']}", "",
            f"- 판단: {action_ko[row['action']]}",
            f"- 현재 비중 / 목표 비중: {_fmt(row['current_weight_pct']['value'])}% / {_fmt(row['target_weight_pct']['value'])}%",
            f"- 현재 주수 / 목표 참고 주수: {_fmt(row['current_quantity']['value'])}주 / {_fmt(row['target_shares_reference']['value'])}주",
            f"- 조정 참고: {_fmt(row['share_delta']['value'])}주",
            f"- 핵심 이유: {row['rationale']}",
            f"- 가장 큰 위험: {row.get('material_risk') or '계획에 명시되지 않음'}",
            f"- 판단이 바뀌는 조건: {', '.join(row['decision_change_triggers']) or '계획에 명시되지 않음'}", "",
        ]
    risk = report["portfolio"].get("current_risk") or {}
    lines += ["## 포트폴리오 건강", "", "| 항목 | 현재 | 상태 |", "|---|---:|---|"]
    labels = {
        "CASH_PCT": "현금", "LEVERAGED_PRODUCTS_PCT": "레버리지 상품",
        "GROWTH_AI_SEMI_BOOK_PCT": "Growth/AI/Semi 장부",
        "GROWTH_AI_SEMI_LEVERAGE_ADJUSTED_PCT": "Growth/AI/Semi 레버리지 조정",
        "OVERALL_LEVERAGE_ADJUSTED_PROXY_PCT": "전체 레버리지 조정 proxy",
    }
    for check in risk.get("checks", []):
        if check["metric"].startswith("POSITION_PCT:"):
            continue
        lines.append(f"| {labels.get(check['metric'], check['metric'])} | {_fmt(check['value'])}% | {check['status']} |")
    if "OPEN_ITEMS_VISIBILITY_UNAVAILABLE" in report["evidence"]["warnings"]:
        lines += ["", "> 실제 주문 전 Kiwoom에서 미체결 주문이 없는지 확인이 필요합니다."]
    lines += [
        "", "## 권한과 현금 구분", "",
        f"- 현재 현금: ${_fmt(report['cash_semantics']['current_cash_usd']['value'])}",
        f"- 검증된 주문가능 현금: ${_fmt(report['cash_semantics']['verified_orderable_cash_usd']['value'])}",
        f"- 매도 후 추정 현금: ${_fmt(report['cash_semantics']['post_sell_estimated_cash_usd']['value'])}",
        f"- 전체 목표 참고 현금: ${_fmt(report['cash_semantics']['full_target_reference_cash_usd']['value'])}",
        f"- 현재 수동 검토 권한: {report['authority']['current_runtime_advisory_authority']}",
        "- Broker Order Authority: FALSE",
        "- execution_quantity: NULL",
        "- automatic_order: FALSE", "",
    ]
    return "\n".join(lines) + "\n"


def _render_html_legacy(report: dict[str, Any]) -> str:
    markdown = _render_markdown_legacy(report)
    first = report["stage1"]["sell_advisories"]
    stage1_rows = "".join(
        f"<tr><td>{html.escape(row['ticker'])}</td><td>{_fmt(row['current_shares'])}</td>"
        f"<td>{_fmt(row['target_shares_reference'])}</td><td>{_fmt(row['calculated_sell_shares'])}</td>"
        f"<td>{html.escape(row['reason'])}</td></tr>" for row in first
    ) or "<tr><td colspan='5'>현재 계획에 축소·정리 항목이 없습니다.</td></tr>"
    cards = "".join(
        f"<article><h3>{html.escape(row['ticker'])}</h3><p><strong>{html.escape(row['action'])}</strong></p>"
        f"<p>현재 {_fmt(row['current_quantity']['value'])}주 · 목표 참고 {_fmt(row['target_shares_reference']['value'])}주</p>"
        f"<p>{html.escape(row['rationale'])}</p></article>" for row in report["portfolio"]["positions"]
    )
    blocked = report["stage2"]["status"] == "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED"
    buy_text = "매도 체결 후 Kiwoom 계좌를 다시 확인해야 매수 수량을 계산할 수 있습니다." if blocked else report["stage2"]["status"]
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>포트폴리오 조정안</title><style>
body{{font-family:"Malgun Gothic","맑은 고딕","Segoe UI",Arial,sans-serif;margin:0;background:#f4f7fb;color:#172033}}
main{{max-width:1120px;margin:auto;padding:28px}}.hero{{background:#173b66;color:white;padding:26px;border-radius:18px}}
.notice{{background:#fff4d6;border-left:5px solid #d39500;padding:14px;margin:18px 0}}section{{background:white;padding:20px;margin:18px 0;border-radius:14px;box-shadow:0 5px 20px #16324f14}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #dce3ec;padding:10px;text-align:left}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}article{{border:1px solid #dce3ec;border-radius:12px;padding:14px}}
.status{{font-size:1.1rem;font-weight:700;color:#8a4200}}small{{color:#526173}}pre{{white-space:pre-wrap;background:#f7f8fa;padding:12px;border-radius:8px}}
</style></head><body><main>
<header class="hero"><h1>포트폴리오 조정안</h1><p>기준 시각: {html.escape(str(report['evidence'].get('decision_as_of') or '확인 필요'))}</p><p>Evidence Grade: {html.escape(report['evidence']['portfolio_evidence_grade_display'])} · 시장 상태: {html.escape(str(report['evidence'].get('market_phase') or '확인 필요'))}</p></header>
<div class="notice">계산된 수동 검토 자료이며, 매수·매도 주문을 만들거나 전송하지 않습니다.</div>
<section><h2>지금 할 일 — 1단계</h2><p class="status">{html.escape(report['stage1']['status'])}</p><table><thead><tr><th>종목</th><th>현재 주수</th><th>목표 참고</th><th>수동 매도 참고</th><th>이유</th></tr></thead><tbody>{stage1_rows}</tbody></table></section>
<section><h2>2단계 매수</h2><p class="status">{html.escape(report['stage2']['status'])}</p><p>{html.escape(buy_text)}</p><p>매수 후보: {html.escape(', '.join(report['stage2']['buy_candidates']) or '없음')}</p></section>
<section><h2>종목별 판단</h2><div class="cards">{cards}</div></section>
<section><h2>권한</h2><p>Broker Order Authority = FALSE · execution_quantity = NULL · automatic_order = FALSE</p><small>현재 수동 검토 권한: {html.escape(report['authority']['current_runtime_advisory_authority'])}</small></section>
<details><summary>동일 의미의 Markdown 원문</summary><pre>{html.escape(markdown)}</pre></details>
</main></body></html>"""


def _display(value: Any, digits: int = 2) -> str:
    if value is None:
        return "확인 필요"
    if isinstance(value, bool):
        return str(value).upper()
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    evidence = report["evidence"]
    stage1 = report["stage1"]
    stage2 = report["stage2"]
    event = report["event_context"]
    lines = [
        "# 포트폴리오 의사결정 대시보드", "",
        f"- 판단 시각: {evidence.get('decision_as_of') or '확인 필요'}",
        f"- Evidence Run: {evidence.get('run_id') or '확인 필요'}",
        f"- Evidence Grade: {evidence['portfolio_evidence_grade_display']}",
        f"- 시장 단계: {evidence.get('market_phase') or '확인 필요'}", "",
        "> 수동 검토용 계산 자료이며, 매수·매도 주문을 만들거나 전송하지 않습니다.", "",
        "## 위험 축소 1단계", "", f"상태: {stage1['status']}", "",
        "| 종목 | 현재 주식 | 목표 참고 주식 | 계산 매도 주식 | 현재 비중 | 목표 비중 | 근거 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    if stage1["sell_advisories"]:
        for row in stage1["sell_advisories"]:
            lines.append(
                f"| {row['ticker']} | {_display(row['current_shares'])} | {_display(row['target_shares_reference'])} | "
                f"{_display(row['calculated_sell_shares'])} | {_display(row['current_weight_pct'])}% | "
                f"{_display(row['target_weight_pct'])}% | {row['reason']} |"
            )
    else:
        lines.append("| 해당 없음 | - | - | - | - | - | 계획상 축소·청산 항목 없음 |")

    lines += ["", "## 2단계 매수", "", f"상태: {stage2['status']}", ""]
    if stage2["status"] == "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED":
        lines.append("매도 체결 후 새 broker-observed Grade B run으로 다시 계산해야 합니다.")
    if stage2["buy_advisories"]:
        lines += [
            "| 종목 | 목표 참고 주식 | 목표 격차 | 계산 매수 주식 | 기준 가격 | 예상 소요액 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        references = {item["ticker"]: item["target_shares_reference"] for item in stage2["buy_candidate_references"]}
        for row in stage2["buy_advisories"]:
            lines.append(
                f"| {row['ticker']} | {_display(references.get(row['ticker']))}주 | {_display(row['target_gap_shares'])}주 | "
                f"{_display(row['calculated_buy_shares'])}주 | ${_display(row['price_usd'])} | "
                f"${_display(row['estimated_cost_usd'])} |"
            )
    else:
        lines += ["| 종목 | 목표 참고 주식 | 최종 매수 주식 |", "|---|---:|---|"]
        if stage2["buy_candidate_references"]:
            for row in stage2["buy_candidate_references"]:
                lines.append(f"| {row['ticker']} | {_display(row['target_shares_reference'])}주 | 산출 보류 / BLOCKED |")
        else:
            lines.append("| 없음 | - | 산출 보류 / BLOCKED |")
    if stage2["blockers"]:
        lines.append(f"차단 사유: {', '.join(stage2['blockers'])}")

    lines += ["", "## 종목 판단", ""]
    actions = {"ADD": "늘림", "HOLD": "유지", "TRIM": "축소", "EXIT": "전량 정리"}
    for row in report["portfolio"]["positions"]:
        lines += [
            f"### {row['ticker']}", "",
            f"- 판단: {actions[row['action']]}",
            f"- 현재/목표 비중: {_display(row['current_weight_pct']['value'])}% / {_display(row['target_weight_pct']['value'])}%",
            f"- 현재/목표 참고 주식: {_display(row['current_quantity']['value'])}주 / {_display(row['target_shares_reference']['value'])}주",
            f"- 계산 변화: {_display(row['share_delta']['value'])}주",
            f"- 근거: {row['rationale']}",
            f"- 주요 위험: {row.get('material_risk') or '계획에 기재되지 않음'}",
            f"- 판단 변경 조건: {', '.join(row['decision_change_triggers']) or '계획에 기재되지 않음'}", "",
        ]

    lines += [
        "## 근거·요청·이벤트", "",
        f"- Canonical schema SHA-256: {evidence['canonical_schema_sha256']}",
        f"- Request accounting: {evidence['request_accounting_status']}",
    ]
    for name, status in evidence.get("request_accounting", {}).items():
        lines.append(f"  - {name}: {status}")
    lines += [
        f"- Event context: {event['status']}",
        f"- HIGH events (current/new): {_display(event['current_high_count'])}/{_display(event['new_high_count'])}",
        f"- Affected tickers: {', '.join(event['affected_tickers']) or '없음'}",
        f"- Automatic target change: {_display(event['automatic_target_change'])}", "",
        "## 권한과 현금 의미", "",
        f"- 현재 현금: ${_display(report['cash_semantics']['current_cash_usd']['value'])}",
        f"- 검증된 주문 가능 현금: ${_display(report['cash_semantics']['verified_orderable_cash_usd']['value'])}",
        f"- 매도 후 추정 현금: ${_display(report['cash_semantics']['post_sell_estimated_cash_usd']['value'])}",
        f"- 현재 런타임 수동자문 권한: {report['authority']['current_runtime_advisory_authority']}",
        f"- CLI authority input effect: {report['authority']['runtime_authority_cli_input_effect']}",
        "- Broker Order Authority: FALSE", "- execution_quantity: NULL", "- automatic_order: FALSE", "",
    ]
    return "\n".join(lines) + "\n"


def render_html(report: dict[str, Any]) -> str:
    evidence = report["evidence"]
    stage1_rows = "".join(
        f"<tr><td>{html.escape(row['ticker'])}</td><td>{_display(row['current_shares'])}</td>"
        f"<td>{_display(row['target_shares_reference'])}</td><td>{_display(row['calculated_sell_shares'])}</td>"
        f"<td>{html.escape(row['reason'])}</td></tr>" for row in report["stage1"]["sell_advisories"]
    ) or "<tr><td colspan='5'>계획상 축소·청산 항목이 없습니다.</td></tr>"
    references = {
        item["ticker"]: item["target_shares_reference"]
        for item in report["stage2"]["buy_candidate_references"]
    }
    buy_rows = "".join(
        f"<tr><td>{html.escape(row['ticker'])}</td><td>{_display(references.get(row['ticker']))}</td>"
        f"<td>{_display(row['target_gap_shares'])}</td><td>{_display(row['calculated_buy_shares'])}</td>"
        f"<td>${_display(row['price_usd'])}</td><td>${_display(row['estimated_cost_usd'])}</td></tr>"
        for row in report["stage2"]["buy_advisories"]
    )
    if not buy_rows:
        buy_rows = "".join(
            f"<tr><td>{html.escape(row['ticker'])}</td><td>{_display(row['target_shares_reference'])}</td>"
            "<td>-</td><td>산출 보류 / BLOCKED</td><td>-</td><td>-</td></tr>"
            for row in report["stage2"]["buy_candidate_references"]
        ) or "<tr><td colspan='6'>후보 없음 · 산출 보류 / BLOCKED</td></tr>"
    request_rows = "".join(
        f"<li>{html.escape(name)}: {html.escape(str(status))}</li>"
        for name, status in evidence.get("request_accounting", {}).items()
    )
    event = report["event_context"]
    markdown = render_markdown(report)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>포트폴리오 의사결정 대시보드</title><style>
body{{font-family:"Malgun Gothic","Segoe UI",sans-serif;margin:0;background:#f4f7fb;color:#172033}}main{{max-width:1120px;margin:auto;padding:28px}}
.hero{{background:#173b66;color:white;padding:26px;border-radius:18px}}.notice{{background:#fff4d6;border-left:5px solid #d39500;padding:14px;margin:18px 0}}
section{{background:white;padding:20px;margin:18px 0;border-radius:14px;box-shadow:0 5px 20px #16324f14}}table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #dce3ec;padding:10px;text-align:left}}.status{{font-weight:700;color:#8a4200}}pre{{white-space:pre-wrap;background:#f7f8fa;padding:12px}}
</style></head><body><main>
<header class="hero"><h1>포트폴리오 의사결정 대시보드</h1><p>판단 시각: {html.escape(str(evidence.get('decision_as_of') or '확인 필요'))}</p><p>Evidence Run: {html.escape(str(evidence.get('run_id') or '확인 필요'))} · Grade: {html.escape(evidence['portfolio_evidence_grade_display'])} · 시장 단계: {html.escape(str(evidence.get('market_phase') or '확인 필요'))}</p></header>
<div class="notice">수동 검토용 계산 자료이며, 매수·매도 주문을 만들거나 전송하지 않습니다.</div>
<section><h2>위험 축소 1단계</h2><p class="status">{html.escape(report['stage1']['status'])}</p><table><thead><tr><th>종목</th><th>현재 주식</th><th>목표 참고</th><th>계산 매도</th><th>근거</th></tr></thead><tbody>{stage1_rows}</tbody></table></section>
<section><h2>2단계 매수</h2><p class="status">{html.escape(report['stage2']['status'])}</p><table><thead><tr><th>종목</th><th>목표 참고</th><th>목표 격차</th><th>계산 매수</th><th>기준 가격</th><th>예상 소요액</th></tr></thead><tbody>{buy_rows}</tbody></table><p>차단 사유: {html.escape(', '.join(report['stage2']['blockers']) or '없음')}</p></section>
<section><h2>근거·요청·이벤트</h2><p>Canonical schema SHA-256: {html.escape(evidence['canonical_schema_sha256'])}</p><p>Request accounting: {html.escape(evidence['request_accounting_status'])}</p><ul>{request_rows}</ul><p>Event context: {html.escape(event['status'])} · HIGH current/new: {_display(event['current_high_count'])}/{_display(event['new_high_count'])} · affected: {html.escape(', '.join(event['affected_tickers']) or '없음')} · automatic target change: {_display(event['automatic_target_change'])}</p></section>
<section><h2>권한</h2><p>Broker Order Authority = FALSE · execution_quantity = NULL · automatic_order = FALSE</p><p>현재 런타임 수동자문 권한: {html.escape(report['authority']['current_runtime_advisory_authority'])}</p><small>CLI authority input effect: {html.escape(report['authority']['runtime_authority_cli_input_effect'])}</small></section>
<details><summary>동일 의미의 Markdown 원문</summary><pre>{html.escape(markdown)}</pre></details>
</main></body></html>"""


def _trusted_output(root: Path, output_root: Path) -> Path:
    trusted = Path(os.path.abspath(root))
    output = Path(os.path.abspath(output_root))
    try:
        if os.path.commonpath((os.path.normcase(str(trusted)), os.path.normcase(str(output)))) != os.path.normcase(str(trusted)):
            raise ContractError("OUTPUT_OUTSIDE_REPOSITORY")
    except ValueError as exc:
        raise ContractError("OUTPUT_OUTSIDE_REPOSITORY") from exc
    return output


def write_run(
    report: dict[str, Any], validation: dict[str, Any], *, output_root: Path,
    source_paths: dict[str, Path | None], implementation_paths: list[Path], root: Path = ROOT,
    consumed_hashes: dict[str, str] | None = None,
) -> Path:
    output = _trusted_output(root, output_root)
    run_dir = output / report["run_id"]
    run_dir.mkdir(parents=True, exist_ok=False)
    decision_bytes = _json_bytes(report)
    validation_bytes = _json_bytes(validation)
    md_bytes = render_markdown(report).encode("utf-8")
    html_bytes = render_html(report).encode("utf-8")
    artifacts = {
        "portfolio-decision.json": decision_bytes,
        "validation-report.json": validation_bytes,
        "portfolio-decision-dashboard.md": md_bytes,
        "portfolio-decision-dashboard.html": html_bytes,
    }
    manifest = {
        "schema_version": "1.0", "run_id": report["run_id"], "generated_at": report["generated_at"],
        "git_commit": _git_commit(root),
        "source_artifacts": {
            name: ({"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)} if path else None)
            for name, path in source_paths.items()
        },
        "implementation_hashes": {
            path.relative_to(root).as_posix(): file_hash(path) for path in implementation_paths
        },
        "consumed_hashes": dict(sorted((consumed_hashes or {}).items())),
        "artifact_hashes": {name: _sha256_bytes(payload) for name, payload in artifacts.items()},
        "create_only": True, "immutable_derived_output": True,
        "order_authority": False, "execution_quantity": None, "automatic_order": False,
    }
    for name, payload in {**artifacts, "run-manifest.json": _json_bytes(manifest)}.items():
        with (run_dir / name).open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    return run_dir


def discover_historical_replay(root: Path = ROOT) -> dict[str, Any]:
    evidence_candidates: list[Path] = []
    rejected_schema_errors: dict[str, list[str]] = {}
    schema_bytes = (root / MANUAL_EVIDENCE_SCHEMA.relative_to(ROOT)).read_bytes()
    base = root / "workspace/outputs/manual-portfolio-analysis"
    if base.exists():
        for path in base.glob("*/manual-portfolio-analysis.json"):
            try:
                source_bytes = path.read_bytes()
                candidate = json.loads(source_bytes.decode("utf-8"))
                errors = validate_instance(
                    candidate, root / MANUAL_EVIDENCE_SCHEMA.relative_to(ROOT), schema_bytes=schema_bytes,
                )
                if candidate.get("evidence_grade") == "GRADE_B" and not errors:
                    evidence_candidates.append(path)
                elif candidate.get("evidence_grade") == "GRADE_B":
                    rejected_schema_errors[path.relative_to(root).as_posix()] = errors
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
    plan_candidates = [
        path for path in (root / "workspace").rglob("*.json")
        if "portfolio-decision-plan" in path.name.lower()
    ] if (root / "workspace").exists() else []
    evidence_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    plan_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if not evidence_candidates:
        status = "BLOCKED_REAL_FIXTURE_NOT_FOUND"
    elif not plan_candidates:
        status = "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND"
    else:
        status = "READY_FOR_HISTORICAL_REPLAY"
    return {
        "status": status,
        "real_grade_b_fixture": evidence_candidates[0].relative_to(root).as_posix() if evidence_candidates else None,
        "historical_decision_plan": plan_candidates[0].relative_to(root).as_posix() if plan_candidates else None,
        "rejected_grade_b_schema_errors": rejected_schema_errors,
        "current_advisory_created": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a read-only portfolio decision dashboard")
    parser.add_argument("--portfolio-evidence", type=Path)
    parser.add_argument("--decision-plan", type=Path)
    parser.add_argument("--risk-policy", type=Path, default=DEFAULT_RISK_POLICY)
    parser.add_argument("--event-context", type=Path)
    parser.add_argument("--instrument-registry", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="INITIAL_COMPILE")
    parser.add_argument("--runtime-advisory-authority")
    parser.add_argument("--discover-historical-replay", action="store_true")
    args = parser.parse_args()
    if args.discover_historical_replay:
        print(json.dumps(discover_historical_replay(), ensure_ascii=False, indent=2))
        return 0
    if args.portfolio_evidence is None or args.decision_plan is None:
        parser.error("--portfolio-evidence and --decision-plan are required")
    evidence_path = args.portfolio_evidence.resolve()
    plan_path = args.decision_plan.resolve()
    risk_path = args.risk_policy.resolve()
    event_path = args.event_context.resolve() if args.event_context else None
    evidence_bytes = evidence_path.read_bytes()
    plan_bytes = plan_path.read_bytes()
    evidence_schema_bytes = MANUAL_EVIDENCE_SCHEMA.read_bytes()
    plan_schema_bytes = PLAN_SCHEMA.read_bytes()
    dashboard_schema_bytes = DASHBOARD_SCHEMA.read_bytes()
    evidence_value = json.loads(evidence_bytes.decode("utf-8"))
    plan_value = json.loads(plan_bytes.decode("utf-8"))
    risk_bytes = risk_path.read_bytes()
    risk = json.loads(risk_bytes.decode("utf-8"))
    registry_path = args.instrument_registry.resolve() if args.instrument_registry else ROOT / risk["instrument_registry_path"]
    registry_bytes = registry_path.read_bytes() if registry_path.exists() else None
    registry = json.loads(registry_bytes.decode("utf-8")) if registry_bytes is not None else None
    event_bytes = event_path.read_bytes() if event_path else None
    generated = _now()
    seed = _sha256_bytes((file_hash(evidence_path) + file_hash(plan_path) + generated).encode("utf-8"))[:12]
    run_id = args.run_id or f"portfolio-decision-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{seed}"
    report, validation = compile_dashboard(
        evidence_value, plan_value, risk, compile_mode=args.mode,
        registry=registry, event_context=json.loads(event_bytes.decode("utf-8")) if event_bytes else None,
        run_id=run_id, generated_at=generated,
        runtime_advisory_authority=args.runtime_advisory_authority,
        evidence_schema_bytes=evidence_schema_bytes, plan_schema_bytes=plan_schema_bytes,
        dashboard_schema_bytes=dashboard_schema_bytes,
    )
    implementation_paths = implementation_provenance_paths(risk_path)
    run_dir = write_run(
        report, validation, output_root=args.output_root.resolve(), root=ROOT,
        source_paths={"portfolio_evidence": evidence_path, "decision_plan": plan_path,
                       "risk_policy": risk_path, "instrument_registry": registry_path if registry_path.exists() else None,
                      "event_context": event_path, "portfolio_evidence_schema": MANUAL_EVIDENCE_SCHEMA},
        implementation_paths=implementation_paths,
        consumed_hashes={
            "portfolio_evidence": _sha256_bytes(evidence_bytes),
            "decision_plan": _sha256_bytes(plan_bytes),
            "portfolio_evidence_schema": _sha256_bytes(evidence_schema_bytes),
            "decision_plan_schema": _sha256_bytes(plan_schema_bytes),
            "dashboard_schema": _sha256_bytes(dashboard_schema_bytes),
            "risk_policy": _sha256_bytes(risk_bytes),
            **({"instrument_registry": _sha256_bytes(registry_bytes)} if registry_bytes is not None else {}),
            **({"event_context": _sha256_bytes(event_bytes)} if event_bytes is not None else {}),
        },
    )
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
