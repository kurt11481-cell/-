#!/usr/bin/env python3
"""Deterministic holding fact pack builder (I1, K2).

Turns one manual analysis JSON, the portfolio state, the active holding
baselines, the alert policy and an optional alert result into the fact pack
that a holding card is checked against. It is read-only: it never writes state,
policy or ledger files, never places or infers orders, and never reads the
clock. Missing or stale inputs stay visible as NOT_EVALUATED / null plus a
missing code. Values copied from the broker observation are display-only.

Rule results reuse existing functions only: evaluate_alerts.exact_loss_boundary
and portfolio_policy_gates.hard_risk_rule_audit. The only new arithmetic is the
remaining distance (boundary / close - 1) and display ratios.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validation_common import canonical_hash  # noqa: E402

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "HOLDING_FACT_PACK"
OUTPUT_ROOT = "workspace/outputs/holding-cards"
FACT_PACK_NAME = "fact-pack.json"
# Allowlist: only these evidence grades lift the "LOW" conviction cap. UNVERIFIED,
# unknown and missing values keep the cap. Enum seen in manual-portfolio-analysis
# schema: GRADE_A, GRADE_B, UNVERIFIED.
CAP_RELEASE_GRADES = ("GRADE_A", "GRADE_B")
CASH_OK_STATUSES = ("VERIFIED_POSITIVE", "VERIFIED_ZERO")
TICKER = re.compile(r"^[A-Z0-9.^=-]{1,24}$")
LEVERAGE_TERM = re.compile(r"(\d+(?:\.\d+)?)\*abs\(([A-Z0-9.^=-]{1,24}) market-value weight\)")


class FactPackError(Exception):
    """Raised when inputs cannot produce a trustworthy fact pack."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise FactPackError(f"INPUT_UNREADABLE:{Path(path).name}") from exc


def _dec(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _round(value: Decimal | None, places: int) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def _plain_number(value: Any) -> int | float | None:
    parsed = _dec(value)
    if parsed is None:
        return None
    return int(parsed) if parsed == parsed.to_integral_value() else float(parsed)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def leverage_factors(policy: dict[str, Any]) -> dict[str, Decimal]:
    """Read leverage multiples from the approved gross-leverage formula text."""
    overlay = _dict(_dict(policy.get("holding_timing_rules")).get("risk_overlay_rules"))
    formula = _dict(overlay.get("dynamic_gross_leverage_cap")).get("gross_effective_leverage_formula")
    if not isinstance(formula, str):
        return {}
    return {symbol: Decimal(factor) for factor, symbol in LEVERAGE_TERM.findall(formula)}


def _holdings(analysis: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    broker = _dict(analysis.get("broker_observed_state"))
    status = broker.get("status")
    if status != "AVAILABLE":
        state_holdings = _dict(_dict(analysis.get("system_portfolio_state")).get("holdings"))
        tickers = sorted(key for key in state_holdings if isinstance(key, str) and TICKER.match(key))
        if not tickers:
            raise FactPackError("NO_HOLDINGS_KNOWN")
        return str(status), [{"ticker": ticker} for ticker in tickers]
    raw = broker.get("holdings")
    if not isinstance(raw, list) or not raw:
        raise FactPackError("EMPTY_HOLDINGS_WITH_AVAILABLE_BROKER")
    rows: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        ticker = item.get("ticker") if isinstance(item, dict) else None
        quantity = _dec(item.get("held_quantity")) if isinstance(item, dict) else None
        if not isinstance(ticker, str) or not TICKER.match(ticker) or quantity is None or quantity <= 0:
            raise FactPackError(f"INVALID_HOLDING_RECORD:{index}")
        if ticker in rows:
            raise FactPackError(f"DUPLICATE_BROKER_TICKER:{ticker}")
        rows[ticker] = item
    return "AVAILABLE", [rows[key] for key in sorted(rows)]


def _mark(analysis: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    for item in analysis.get("current_price_evidence") or []:
        if not isinstance(item, dict) or item.get("ticker") != ticker or item.get("status") != "AVAILABLE":
            continue
        record = _dict(item.get("record"))
        price = _dec(record.get("price"))
        if price is None or price <= 0:
            return None
        return {
            "price_usd": _plain_number(record.get("price")),
            "session_type": record.get("market_session_type"),
            "price_basis": record.get("price_basis"),
            "provider_timestamp": record.get("provider_timestamp"),
            "indicative_only": record.get("indicative_only") is True,
            "reference_only": True,
        }
    return None


def _confirmed_close(analysis: dict[str, Any], ticker: str) -> tuple[dict[str, Any] | None, str | None]:
    expected = analysis.get("expected_completed_us_session")
    for item in analysis.get("historical_daily_evidence") or []:
        if not isinstance(item, dict) or item.get("ticker") != ticker:
            continue
        if item.get("status") != "AVAILABLE":
            return None, "DAILY_EVIDENCE_NOT_AVAILABLE"
        for record in reversed(item.get("records") or []):
            if not isinstance(record, dict):
                continue
            price = _dec(record.get("price"))
            if (
                record.get("reported_session") == expected
                and record.get("market_session_type") == "REGULAR_COMPLETED"
                and record.get("price_basis") == "RAW_REGULAR_SESSION_CLOSE"
                and record.get("bar_finalized") is True
                and record.get("hard_risk_authority") is True
                and price is not None and price > 0
            ):
                return {
                    "price_usd": _plain_number(record.get("price")),
                    "session": record.get("reported_session"),
                    "price_basis": record.get("price_basis"),
                    "provider_finalized": True,
                }, None
        return None, "EXPECTED_SESSION_CLOSE_NOT_FOUND"
    return None, "DAILY_EVIDENCE_MISSING"


def _engine_bar_status(analysis: dict[str, Any], ticker: str) -> str | None:
    for item in analysis.get("last_verified_finalized_bars") or []:
        if isinstance(item, dict) and item.get("ticker") == ticker:
            return item.get("status")
    return None


def _identity_unverified(analysis: dict[str, Any], ticker: str) -> bool:
    if analysis.get("identity_authority_status") != "VERIFIED":
        return True
    for item in analysis.get("last_verified_finalized_bars") or []:
        if isinstance(item, dict) and item.get("ticker") == ticker:
            return item.get("identity_authority_status") != "VERIFIED"
    return True


def _hard_risk(
    ticker: str, policy: dict[str, Any], state_average: Any, broker_average: Any,
    close: dict[str, Any] | None, mark: dict[str, Any] | None, state_revision: Any,
) -> dict[str, Any]:
    from evaluate_alerts import AlertError, exact_loss_boundary
    from portfolio_policy_gates import hard_risk_rule_audit

    rule = _dict(_dict(_dict(policy.get("holding_risk_rules")).get("positions")).get(ticker))
    result: dict[str, Any] = {"status": "NOT_EVALUATED", "reason": None, "rule_id": rule.get("rule_id")}
    if not rule:
        result["reason"] = "NO_POLICY_RULE"
        return result
    audit = hard_risk_rule_audit(policy, ticker)
    result.update(
        rule_version=audit.get("rule_version"),
        maximum_loss_fraction=audit.get("maximum_loss_fraction"),
        default_direction=rule.get("default_direction"),
        reduction_plan_status=rule.get("reduction_plan_status"),
        policy_authority_status=audit.get("policy_authority_status"),
        approval_status=audit.get("approval_status"),
        action_approval_status=audit.get("action_approval_status"),
        action_on_breach=audit.get("action_on_breach"),
        comparison="completed_regular_session_close <= boundary",
        price_basis="RAW_REGULAR_SESSION_CLOSE",
        average_cost_source=f"SYSTEM_STATE_REVISION_{state_revision}",
    )
    average = _dec(state_average)
    if average is None:
        result["reason"] = "STATE_AVERAGE_COST_MISSING"
        return result
    if close is None:
        result["reason"] = "CONFIRMED_CLOSE_MISSING"
        return result
    try:
        boundary = exact_loss_boundary(state_average, rule["maximum_loss_fraction_from_average_cost"])
    except (AlertError, KeyError):
        result["reason"] = "BOUNDARY_INPUT_INVALID"
        return result
    close_price = float(close["price_usd"])
    breached = close_price <= boundary
    remaining = Decimal(str(boundary)) / Decimal(str(close_price)) - 1
    result.update(
        status="EVALUATED",
        boundary_usd=_round(Decimal(str(boundary)), 4),
        close_usd=close["price_usd"],
        close_session=close["session"],
        breached=breached,
        remaining_pct=_round(remaining * 100, 1),
        holding_risk_state=(
            "POLICY_AUTHORITY_UNVERIFIED" if breached and audit.get("policy_authority_status") != "VERIFIED"
            else ("HARD_RISK_BREACH" if breached else "NO_HARD_RISK")
        ),
        average_cost_matches_broker=(
            _round(average, 4) == _round(_dec(broker_average), 4) if _dec(broker_average) is not None else None
        ),
    )
    mark_price = _dec((mark or {}).get("price_usd"))
    if mark_price is not None:
        result["premarket_reference_remaining_pct"] = _round(Decimal(str(boundary)) / mark_price * 100 - 100, 1)
        result["premarket_reference_note"] = "REFERENCE_ONLY_NOT_HARD_RISK_AUTHORITY"
    return result


def _timing(ticker: str, policy: dict[str, Any], alert_result: dict[str, Any] | None, expected_session: Any) -> dict[str, Any]:
    positions = _dict(_dict(policy.get("holding_timing_rules")).get("positions"))
    if ticker not in positions:
        return {"status": "NOT_APPLICABLE", "reason": "NO_TIMING_RULE_FOR_TICKER"}
    if alert_result is None:
        return {"status": "NOT_EVALUATED", "reason": "ALERT_RESULT_NOT_PROVIDED"}
    if alert_result.get("us_session_date") != expected_session:
        return {"status": "NOT_EVALUATED", "reason": "ALERT_RESULT_STALE"}
    for candidate in alert_result.get("candidates") or []:
        if (
            isinstance(candidate, dict) and candidate.get("symbol") == ticker
            and candidate.get("event_type") == "holding_timing_review"
        ):
            return {"status": "EVALUATED", "reason": None, "side": candidate.get("side"), "grade": candidate.get("grade")}
    return {"status": "NOT_EVALUATED", "reason": "NO_TIMING_CANDIDATE_IN_ALERT_RESULT"}


def _rule_direction(hard_risk: dict[str, Any], timing: dict[str, Any]) -> tuple[str, list[str]]:
    reduce_basis: list[str] = []
    if hard_risk.get("status") == "EVALUATED" and hard_risk.get("breached") is True:
        reduce_basis.append("HARD_RISK_BREACH")
    if timing.get("status") == "EVALUATED" and timing.get("side") == "reduce":
        reduce_basis.append("TIMING_REDUCE_REVIEW")
    if hard_risk.get("default_direction") == "reduce":
        reduce_basis.append("POLICY_DEFAULT_REDUCE")
    if reduce_basis:
        return "REDUCE", reduce_basis
    if hard_risk.get("default_direction") == "hold":
        return "HOLD", ["POLICY_DEFAULT_HOLD"]
    return "NONE", []


def _baseline(baseline: dict[str, Any] | None, decision_as_of: datetime | None) -> dict[str, Any] | None:
    if not isinstance(baseline, dict):
        return None
    cutoff = _parse_time(baseline.get("analysis_cutoff"))
    age = (decision_as_of - cutoff).days if cutoff is not None and decision_as_of is not None else None
    return {
        "baseline_id": baseline.get("baseline_id"),
        "baseline_version": baseline.get("baseline_version"),
        "analysis_cutoff": baseline.get("analysis_cutoff"),
        "age_days": age,
        "thesis_status": baseline.get("thesis_status"),
        "valuation_status": baseline.get("valuation_status"),
        "validation_status": baseline.get("validation_status"),
        "primary_reason": baseline.get("primary_reason"),
        "strongest_counter_case": baseline.get("strongest_counter_case"),
        "invalidation_conditions": list(baseline.get("invalidation_conditions") or []),
    }


def _confidence_cap(analysis: dict[str, Any], broker_status: str, state_changed: bool) -> dict[str, Any]:
    reasons: list[str] = []
    if analysis.get("evidence_grade") not in CAP_RELEASE_GRADES:
        reasons.append("EVIDENCE_GRADE_NOT_ALLOWLISTED")
    if analysis.get("preflight_status") != "PASS":
        reasons.append("PREFLIGHT_NOT_PASS")
    if analysis.get("broker_diff_status") != "MATCH":
        reasons.append("STATE_UNRECONCILED_BROKER_DIFF_NOT_MATCH")
    if broker_status != "AVAILABLE":
        reasons.append("BROKER_NOT_AVAILABLE")
    if state_changed:
        reasons.append("STATE_CHANGED_SINCE_ANALYSIS")
    return {
        "max_conviction": "LOW" if reasons else "HIGH",
        "reasons": reasons,
        "release_grades": list(CAP_RELEASE_GRADES),
    }


def _s5_exposure_block(review: Any, expected_session: Any) -> dict[str, Any]:
    """Copy the S5 display block (E, distance to the next line, pause state) from one exposure review.

    Nothing is recomputed here and no target weights are copied. A review that fails its schema or
    its own hash is rejected rather than shown.
    """
    from portfolio_exposure import exposure_display_block, review_content_hash
    from validation_common import validate_instance

    schema = SKILL_ROOT / "schemas/portfolio-exposure-review.schema.json"
    if not isinstance(review, dict) or validate_instance(review, schema) or (
            review_content_hash(review) != review.get("review_id")):
        raise FactPackError("EXPOSURE_REVIEW_INVALID")
    block = exposure_display_block(review)
    block["matches_expected_completed_session"] = review["evaluation_session"] == expected_session
    return block


def build_fact_pack(
    analysis: dict[str, Any], state: dict[str, Any] | None, baselines: dict[str, Any],
    policy: dict[str, Any], alert_result: dict[str, Any] | None = None,
    exposure_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = analysis.get("manual_run_id")
    decision_as_of = _parse_time(analysis.get("decision_as_of"))
    if not isinstance(run_id, str) or not run_id or decision_as_of is None:
        raise FactPackError("ANALYSIS_BINDING_FIELDS_INVALID")
    broker = _dict(analysis.get("broker_observed_state"))
    broker_status, holdings = _holdings(analysis)
    system_state = _dict(analysis.get("system_portfolio_state"))
    state_revision = system_state.get("state_revision")
    state_changed = state is not None and state.get("state_revision") != state_revision
    cap = _confidence_cap(analysis, broker_status, state_changed)

    cash = _dict(broker.get("cash"))
    deposit = _dec(cash.get("foreign_currency_deposit")) if cash.get("cash_status") in CASH_OK_STATUSES else None
    orderable_verified = analysis.get("orderable_cash_status") == "VERIFIED"
    operations = _dict(broker.get("operation_statuses"))
    leverage = leverage_factors(policy)
    expected_session = analysis.get("expected_completed_us_session")

    marks = {row["ticker"]: _mark(analysis, row["ticker"]) for row in holdings}
    values: dict[str, Decimal | None] = {}
    for row in holdings:
        quantity, price = _dec(row.get("held_quantity")), _dec((marks[row["ticker"]] or {}).get("price_usd"))
        values[row["ticker"]] = quantity * price if quantity is not None and price is not None else None
    total = None if deposit is None or any(v is None for v in values.values()) else sum(values.values(), deposit)

    tickers: dict[str, Any] = {}
    for row in holdings:
        ticker = row["ticker"]
        mark, (close, close_reason) = marks[ticker], _confirmed_close(analysis, ticker)
        quantity, average = _dec(row.get("held_quantity")), _dec(row.get("average_cost"))
        value = values[ticker]
        cost = quantity * average if quantity is not None and average is not None else None
        mark_price = _dec((mark or {}).get("price_usd"))
        state_average = _dict(system_state.get("average_cost_usd")).get(ticker)
        hard_risk = _hard_risk(ticker, policy, state_average, row.get("average_cost"), close, mark, state_revision)
        timing = _timing(ticker, policy, alert_result, expected_session)
        direction, basis = _rule_direction(hard_risk, timing)
        factor = leverage.get(ticker)
        missing = sorted(
            code for code, present in {
                "HOLDING_NOT_OBSERVED_BY_BROKER": broker_status != "AVAILABLE",
                "MARK_PRICE_MISSING": mark is None,
                "CONFIRMED_CLOSE_MISSING": close is None,
                "LOSS_LIMIT_NOT_EVALUATED": hard_risk["status"] != "EVALUATED",
                "TIMING_NOT_EVALUATED": timing["status"] == "NOT_EVALUATED",
                "LEVERAGE_FACTOR_NOT_IN_POLICY": factor is None,
                "BASELINE_MISSING": not isinstance(baselines.get(ticker), dict),
                "WEIGHT_NOT_COMPUTABLE": total is None,
            }.items() if present
        )
        tickers[ticker] = {
            "holding_observed": {
                "display_only": True,
                "source": "BROKER_OBSERVED_STATE",
                "held_quantity": _plain_number(row.get("held_quantity")),
                "average_cost_usd": _plain_number(row.get("average_cost")),
            },
            "mark": mark,
            "confirmed_close": close,
            "confirmed_close_missing_reason": close_reason,
            "engine_finalized_bar_status": _engine_bar_status(analysis, ticker),
            "display": {
                "held_quantity": _plain_number(row.get("held_quantity")),
                "average_cost_usd": _plain_number(row.get("average_cost")),
                "mark_price_usd": (mark or {}).get("price_usd"),
                "market_value_usd": _round(value, 2),
                "unrealized_pnl_usd": _round(value - cost, 2) if value is not None and cost is not None else None,
                "unrealized_pnl_pct": (
                    _round((mark_price / average - 1) * 100, 1)
                    if mark_price is not None and average is not None and average > 0 else None
                ),
                "weight_pct": _round(value / total * 100, 1) if value is not None and total else None,
                "leverage_factor": _plain_number(factor) if factor is not None else None,
                "confirmed_close_usd": (close or {}).get("price_usd"),
                "loss_limit_boundary_usd": hard_risk.get("boundary_usd"),
                "loss_limit_remaining_pct": hard_risk.get("remaining_pct"),
            },
            "rule_results": {
                "hard_risk": hard_risk,
                "timing": timing,
                "rule_direction": direction,
                "rule_direction_basis": basis,
            },
            "baseline": _baseline(baselines.get(ticker), decision_as_of),
            "withhold_allowed": {
                "BROKER_UNAVAILABLE": broker_status == "UNAVAILABLE",
                "IDENTITY_UNVERIFIED": _identity_unverified(analysis, ticker),
            },
            "missing": missing,
        }

    # Optional S5 display block; without the input the fact pack is byte-identical to before.
    s5_exposure = ({"s5_exposure": _s5_exposure_block(exposure_review, expected_session)}
                   if exposure_review is not None else {})

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "display_only": True,
        "order_authority": False,
        "quantity_authority": "none",
        "source": {
            "manual_run_id": run_id,
            "decision_as_of": analysis.get("decision_as_of"),
            "observed_at": analysis.get("observed_at"),
            "trading_date": analysis.get("trading_date"),
            "market_phase": analysis.get("market_phase"),
            "expected_completed_us_session": expected_session,
        },
        "status": {
            "evidence_grade": analysis.get("evidence_grade"),
            "preflight_status": analysis.get("preflight_status"),
            "hard_fail_reasons": list(analysis.get("hard_fail_reasons") or []),
            "broker_diff_status": analysis.get("broker_diff_status"),
            "broker_status": broker_status,
            "identity_authority_status": analysis.get("identity_authority_status"),
            "state_revision": state_revision,
            "state_file_revision_matches_analysis": None if state is None else not state_changed,
            "event_evidence_status": analysis.get("event_evidence_status"),
            "technical_evidence_status": analysis.get("technical_evidence_status"),
            "confidence_cap": cap,
        },
        "portfolio": {
            "display_only": True,
            "total_value_usd": _round(total, 2),
            "cash_deposit_usd": _round(deposit, 2),
            "cash_weight_pct": _round(deposit / total * 100, 2) if deposit is not None and total else None,
            "orderable_cash": {
                "usd": _plain_number(analysis.get("verified_orderable_cash_usd")) if orderable_verified else None,
                "status": analysis.get("orderable_cash_status"),
                "label": "VERIFIED_ORDERABLE_CASH" if orderable_verified else "NOT_VERIFIED",
                "expected_sale_proceeds_counted_as_orderable_cash": False,
            },
            "open_orders_status": operations.get("account_open_items"),
            "realized_pnl_status": operations.get("account_realized_pnl_read"),
            **s5_exposure,
        },
        "tickers": tickers,
    }


def load_baselines(index_path: Path, root: Path = REPO_ROOT) -> dict[str, Any]:
    index = read_json(index_path)
    loaded: dict[str, Any] = {}
    for ticker, entry in _dict(_dict(index).get("active")).items():
        relative = _dict(entry).get("baseline_path")
        if not isinstance(relative, str):
            continue
        target = (root / relative).resolve()
        if root.resolve() not in target.parents:
            continue
        try:
            loaded[ticker] = read_json(target)
        except FactPackError:
            continue
    return loaded


def fact_pack_hash(fact_pack: dict[str, Any]) -> str:
    return canonical_hash(fact_pack)


def write_fact_pack(fact_pack: dict[str, Any], output_dir: Path, root: Path = REPO_ROOT) -> Path:
    allowed = (root / OUTPUT_ROOT).resolve()
    target_dir = Path(output_dir).resolve()
    if target_dir != allowed and allowed not in target_dir.parents:
        raise FactPackError("OUTPUT_OUTSIDE_HOLDING_CARDS")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / FACT_PACK_NAME
    payload = (json.dumps(fact_pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with target.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise FactPackError("FACT_PACK_ALREADY_EXISTS") from exc
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--state", type=Path, default=REPO_ROOT / "stock-strategy-system/portfolio_state.json")
    parser.add_argument("--policy", type=Path, default=REPO_ROOT / "stock-strategy-system/alert_policy.json")
    parser.add_argument(
        "--baseline-index", type=Path, default=REPO_ROOT / "workspace/research/holding-baselines/active-index.json"
    )
    parser.add_argument("--alert-result", type=Path, default=None)
    parser.add_argument("--exposure-review", type=Path, default=None,
                        help="optional S5 portfolio exposure review; adds a display-only block")
    args = parser.parse_args(argv)
    try:
        pack = build_fact_pack(
            read_json(args.analysis),
            read_json(args.state) if args.state.is_file() else None,
            load_baselines(args.baseline_index) if args.baseline_index.is_file() else {},
            read_json(args.policy),
            read_json(args.alert_result) if args.alert_result else None,
            read_json(args.exposure_review) if args.exposure_review else None,
        )
        path = write_fact_pack(pack, args.output_dir)
    except FactPackError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 2
    print(json.dumps({
        "status": "OK",
        "fact_pack_path": str(path),
        "fact_pack_sha256": fact_pack_hash(pack),
        "manual_run_id": pack["source"]["manual_run_id"],
        "tickers": sorted(pack["tickers"]),
        "max_conviction": pack["status"]["confidence_cap"]["max_conviction"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
