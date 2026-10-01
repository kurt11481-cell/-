#!/usr/bin/env python3
"""Normalize sanitized Kiwoom U.S. account reads into reconciliation-only evidence."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Callable
from zoneinfo import ZoneInfo

from validation_common import canonical_hash


SNAPSHOT_ROLES = {"PRE_OPEN_BROKER_SNAPSHOT", "POST_CLOSE_BROKER_SNAPSHOT"}
READ_OPERATIONS = {
    "account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
    "account_open_items", "account_fills_read", "account_realized_pnl_read",
}

# I0 reconciliation proposal contract (kiwoom-reconciliation-proposal.schema.json).
PROPOSAL_SCHEMA_VERSION = "kiwoom-reconciliation-1.0"
PROPOSAL_TYPE = "KIWOOM_BROKER_RECONCILIATION"
PROPOSAL_SOURCE = "KIWOOM_READONLY_API"
RECONCILIATION_SCOPE = "HOLDINGS_AND_AVAILABLE_CASH"
DEFAULT_PORTFOLIO_STATE_PATH = "stock-strategy-system/portfolio_state.json"
REQUIRED_RECONCILIATION_OPERATIONS = ("account_holdings_read", "account_deposit_read", "account_fills_read")
DISPLAY_ONLY_OPERATIONS = ("account_deposit_detail_read", "account_open_items", "account_realized_pnl_read")
PATCH_FIELDS = ("holdings", "average_cost_usd", "position_cost_basis_usd", "aggregate_cost_basis_usd",
                "available_cash_usd")
NEVER_TOUCHED_FIELDS = ("current_stage", "timing_plan", "confirmed_trades", "pending_candidates",
                        "broker_display_snapshot", "unreconciled_holding_changes", "strategy_version",
                        "strategy_mode", "state_status", "archived_prior_strategy", "state_notes")
SNAPSHOT_RECORD_COMPARED_FIELDS = ("source", "scope", "as_of", "holdings_complete", "cash_verified",
                                   "cash_verified_scope", "open_orders_verified")
COST_BASIS_DERIVATION = "QUANTITY_X_AVERAGE_COST_DECIMAL_ROUND_HALF_UP_CENTS"
FUTURE_TIMESTAMP_TOLERANCE_SECONDS = 60
US_EASTERN = "America/New_York"


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _rows(results: list[dict[str, Any]], operation: str) -> list[dict[str, Any]]:
    for result in results:
        if result.get("operation") == operation and result.get("bridge_status") in {"PASS", "PARTIAL"}:
            return [item for item in (result.get("data") or []) if isinstance(item, dict)]
    return []


def normalize_snapshot(results: list[dict[str, Any]], *, snapshot_role: str,
                       generated_at: str, maximum_age_seconds: int) -> dict[str, Any]:
    if snapshot_role not in SNAPSHOT_ROLES:
        raise ValueError("BROKER_SNAPSHOT_ROLE_INVALID")
    if any(result.get("operation") not in READ_OPERATIONS for result in results):
        raise ValueError("BROKER_OPERATION_NOT_ALLOWLISTED")
    holdings = []
    for row in _rows(results, "account_holdings_read"):
        ticker = str(row.get("stk_cd") or "").strip().upper()
        if not ticker:
            continue
        holdings.append({
            "ticker": ticker, "security_name": row.get("frgn_stk_nm"), "currency": row.get("crnc_code"),
            "settled_quantity": _number(row.get("qty")), "held_quantity": _number(row.get("poss_qty")),
            "available_shares": _number(row.get("sell_alowq")), "average_cost": _number(row.get("frgn_stk_book_uv")),
        })
    deposits = _rows(results, "account_deposit_read")
    usd = next((row for row in deposits if str(row.get("crnc_code") or "").upper() == "USD"), None)
    withdrawable = _number((usd or {}).get("fc_pymn_alowa"))
    order_available = _number((usd or {}).get("fc_ord_alowa"))
    settled_cash = min(withdrawable, order_available) if withdrawable is not None and order_available is not None else None
    detail = (_rows(results, "account_deposit_detail_read") or [{}])[0]
    unsettled = {
        "d1_sell_settlement_usd": _number(detail.get("d1_usd_sell_excta")),
        "d1_buy_settlement_usd": _number(detail.get("d1_usd_buy_excta")),
        "d2_sell_settlement_usd": _number(detail.get("d2_usd_sell_excta")),
        "d2_buy_settlement_usd": _number(detail.get("d2_usd_buy_excta")),
    }
    timestamps = [result.get("retrieved_at") for result in results if result.get("retrieved_at")]
    as_of = max(timestamps) if timestamps else generated_at
    age = max(0, int((datetime.fromisoformat(generated_at.replace("Z", "+00:00")) -
                      datetime.fromisoformat(as_of.replace("Z", "+00:00"))).total_seconds()))
    complete = all(any(result.get("operation") == operation and result.get("bridge_status") == "PASS" for result in results)
                   for operation in READ_OPERATIONS)
    operation_statuses = {
        operation: next((str(result.get("bridge_status")) for result in results
                         if result.get("operation") == operation), "NOT_RETURNED")
        for operation in sorted(READ_OPERATIONS)
    }
    snapshot = {
        "schema_version": "1.0", "snapshot_role": snapshot_role,
        "status": "KIWOOM_BROKER_SNAPSHOT_SHADOW", "generated_at": generated_at,
        "broker_snapshot_as_of": as_of, "broker_snapshot_age_seconds": age,
        "broker_snapshot_freshness_status": "FRESH" if age <= maximum_age_seconds else "STALE",
        "account_identifier_stored": False, "scope_complete": complete,
        "operation_statuses": operation_statuses,
        "holdings": sorted(holdings, key=lambda item: item["ticker"]),
        "cash": {
            "currency": "USD", "foreign_currency_deposit": _number((usd or {}).get("fc_entra")),
            "withdrawable_cash": withdrawable, "order_available_cash": order_available,
            "settled_available_cash": settled_cash,
            "cash_status": ("VERIFIED_ZERO" if settled_cash == 0 else "VERIFIED_POSITIVE" if settled_cash is not None and settled_cash > 0 else "UNVERIFIED"),
            "unsettled_funds": unsettled,
            "projected_proceeds_included": False, "margin_or_credit_included": False,
        },
        "open_orders": _rows(results, "account_open_items"),
        "fills": _rows(results, "account_fills_read"),
        "realized_pnl": _rows(results, "account_realized_pnl_read"),
        "fill_inference_performed": False, "portfolio_mutation": False,
        "quantity_authority": "none", "order_authority": False,
        "snapshot_hash": "0" * 64,
    }
    snapshot["snapshot_hash"] = canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
    return snapshot


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _operation_results(results: list[dict[str, Any]], operation: str) -> list[dict[str, Any]]:
    return [result for result in results if isinstance(result, dict) and result.get("operation") == operation]


def _passed_rows(results: list[dict[str, Any]], operation: str) -> list[dict[str, Any]]:
    matches = _operation_results(results, operation)
    if len(matches) != 1 or matches[0].get("bridge_status") != "PASS":
        return []
    return [row for row in (matches[0].get("data") or []) if isinstance(row, dict)]


def _required_retrieval_times(results: list[dict[str, Any]]) -> dict[str, datetime]:
    times: dict[str, datetime] = {}
    for operation in REQUIRED_RECONCILIATION_OPERATIONS:
        matches = _operation_results(results, operation)
        if len(matches) == 1 and matches[0].get("bridge_status") == "PASS":
            parsed = _parse_timestamp(matches[0].get("retrieved_at"))
            if parsed is not None:
                times[operation] = parsed
    return times


def validate_reconciliation_inputs(results: list[dict[str, Any]], snapshot: dict[str, Any], *,
                                   maximum_age_seconds: int) -> list[str]:
    """I0-only fail-closed input checks run after normalize_snapshot, whose contract is unchanged."""
    errors: list[str] = []
    generated_at = _parse_timestamp(snapshot.get("generated_at"))
    if generated_at is None:
        errors.append("SNAPSHOT_GENERATED_AT_INVALID")
    for operation in REQUIRED_RECONCILIATION_OPERATIONS:
        matches = _operation_results(results, operation)
        if len(matches) != 1:
            errors.append(f"REQUIRED_READ_MISSING:{operation}")
            continue
        if matches[0].get("bridge_status") != "PASS":
            errors.append(f"REQUIRED_READ_NOT_PASS:{operation}")
            continue
        pagination = matches[0].get("pagination")
        if isinstance(pagination, dict) and pagination.get("complete") is not True:
            errors.append(f"REQUIRED_READ_INCOMPLETE:{operation}")
        retrieved = _parse_timestamp(matches[0].get("retrieved_at"))
        if retrieved is None:
            errors.append(f"REQUIRED_READ_TIMESTAMP_INVALID:{operation}")
        elif generated_at is not None and (
                retrieved - generated_at).total_seconds() > FUTURE_TIMESTAMP_TOLERANCE_SECONDS:
            errors.append(f"REQUIRED_READ_TIMESTAMP_IN_FUTURE:{operation}")
    times = _required_retrieval_times(results)
    # The oldest required read bounds freshness; broker_snapshot_as_of uses the latest one.
    if generated_at is not None and times and (
            generated_at - min(times.values())).total_seconds() > maximum_age_seconds:
        errors.append("BROKER_SNAPSHOT_TOO_OLD")
    seen: set[str] = set()
    for row in _passed_rows(results, "account_holdings_read"):
        ticker = str(row.get("stk_cd") or "").strip().upper()
        if not ticker:
            errors.append("HOLDING_TICKER_MISSING")
            continue
        if ticker in seen:
            errors.append(f"HOLDING_TICKER_DUPLICATE:{ticker}")
        seen.add(ticker)
        if str(row.get("crnc_code") or "").strip().upper() != "USD":
            errors.append(f"HOLDING_CURRENCY_NOT_USD:{ticker}")
        quantity = _decimal(row.get("poss_qty"))
        if quantity is None:
            errors.append(f"HOLDING_QUANTITY_INVALID:{ticker}")
        elif quantity < 0:
            errors.append(f"HOLDING_QUANTITY_NEGATIVE:{ticker}")
        elif quantity != quantity.to_integral_value():
            errors.append(f"HOLDING_QUANTITY_FRACTIONAL:{ticker}")
        cost = _decimal(row.get("frgn_stk_book_uv"))
        if cost is None:
            errors.append(f"AVERAGE_COST_INVALID:{ticker}")
        elif cost < 0:
            errors.append(f"AVERAGE_COST_NEGATIVE:{ticker}")
    deposit = _operation_results(results, "account_deposit_read")
    if len(deposit) == 1 and deposit[0].get("bridge_status") == "PASS":
        usd_rows = [row for row in _passed_rows(results, "account_deposit_read")
                    if str(row.get("crnc_code") or "").strip().upper() == "USD"]
        if not usd_rows:
            errors.append("CASH_USD_ROW_MISSING")
        elif len(usd_rows) > 1:
            errors.append("CASH_USD_ROW_DUPLICATE")
        else:
            for field in ("fc_pymn_alowa", "fc_ord_alowa"):
                value = _decimal(usd_rows[0].get(field))
                if value is None:
                    errors.append(f"CASH_VALUE_INVALID:{field}")
                elif value < 0:
                    errors.append(f"CASH_VALUE_NEGATIVE:{field}")
    return list(dict.fromkeys(errors))


def derived_cost_basis(quantity: int, average_cost: float) -> Decimal:
    """Position cost basis derived as quantity x average cost, rounded half-up to cents."""
    return (Decimal(quantity) * Decimal(str(average_cost))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def proposal_content_hash(proposal: dict[str, Any]) -> str:
    """proposal_id covers every field except the identifiers derived from it."""
    return canonical_hash({key: value for key, value in proposal.items() if key not in {"proposal_id", "confirm_code"}})


def _numbers_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-8)
    return left == right


def _map_changes(field: str, old_map: Any, new_map: dict[str, Any]) -> list[dict[str, Any]]:
    old = old_map if isinstance(old_map, dict) else {}
    changes = []
    for key in sorted(set(old) | set(new_map)):
        if key not in old or key not in new_map or not _numbers_equal(old[key], new_map[key]):
            changes.append({"field": field, "key": key, "old_value": old.get(key), "new_value": new_map.get(key)})
    return changes


def _scalar_change(field: str, old: Any, new: Any) -> list[dict[str, Any]]:
    return [] if _numbers_equal(old, new) else [{"field": field, "key": None, "old_value": old, "new_value": new}]


def _record_changes(old_record: Any, new_record: dict[str, Any]) -> list[dict[str, Any]]:
    old = old_record if isinstance(old_record, dict) else {}
    return [{"field": "last_confirmed_broker_snapshot", "key": key,
             "old_value": old.get(key), "new_value": new_record.get(key)}
            for key in SNAPSHOT_RECORD_COMPARED_FIELDS if old.get(key) != new_record.get(key)]


def _cost_basis_crosscheck(results: list[dict[str, Any]], patch: dict[str, Any]) -> list[dict[str, Any]]:
    """Display-only comparison with evlt_amt - pl_amt; never gates application."""
    rows = []
    for row in _passed_rows(results, "account_holdings_read"):
        ticker = str(row.get("stk_cd") or "").strip().upper()
        if ticker not in (patch.get("position_cost_basis_usd") or {}):
            continue
        evaluation, pnl = _decimal(row.get("evlt_amt")), _decimal(row.get("pl_amt"))
        derived = Decimal(str(patch["position_cost_basis_usd"][ticker]))
        implied = evaluation - pnl if evaluation is not None and pnl is not None else None
        status = ("UNAVAILABLE" if implied is None
                  else "WITHIN_ONE_DOLLAR" if abs(implied - derived) <= 1 else "DIFFERS")
        rows.append({"ticker": ticker, "derived_cost_basis_usd": float(derived),
                     "evaluation_minus_pnl": float(implied) if implied is not None else None, "status": status})
    return rows


def _recent_fills(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"ticker": str(row.get("stk_cd") or "").strip().upper() or None, "side": row.get("slby_tp"),
             "filled_quantity": row.get("cntr_qty"), "time": row.get("cntr_time") or row.get("ord_time")}
            for row in _passed_rows(results, "account_fills_read")]


def reconciliation_proposal(snapshot: dict[str, Any], portfolio: dict[str, Any], *,
                            results: list[dict[str, Any]], maximum_age_seconds: int,
                            portfolio_state_path: str = DEFAULT_PORTFOLIO_STATE_PATH,
                            snapshot_path: str | None = None,
                            ledger_last_hash_after: str | None = None,
                            ledger_last_hash_before: str | None = None,
                            ledger_integrity_ok: bool = True,
                            post_apply_check: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
                            cash_flow_declaration: dict[str, Any] | None = None,
                            ) -> dict[str, Any]:
    """Build one non-mutating Kiwoom reconciliation proposal in the unified apply format.

    cash_flow_declaration (S5 R6) is an optional block built by cash_flow_evidence.build_declaration.
    It is part of the hashed content, so a declaration always gets a new proposal_id and confirm code.
    It changes no state field; apply only records it in the ledger entry.
    """
    input_errors = validate_reconciliation_inputs(results, snapshot, maximum_age_seconds=maximum_age_seconds)
    times = _required_retrieval_times(results)
    generated_at = _parse_timestamp(snapshot.get("generated_at")) or datetime(1970, 1, 1, tzinfo=timezone.utc)
    earliest = min(times.values()) if times else generated_at
    open_orders_verified = (snapshot.get("operation_statuses") or {}).get("account_open_items") == "PASS"
    record = {
        "source": PROPOSAL_SOURCE, "evidence_sha256": snapshot["snapshot_hash"],
        "as_of": earliest.astimezone(ZoneInfo(US_EASTERN)).date().isoformat(),
        "as_of_timestamp": _utc_iso(earliest), "scope": RECONCILIATION_SCOPE,
        "holdings_complete": True, "cash_verified": True, "cash_verified_scope": "available_cash_only",
        "open_orders_verified": open_orders_verified,
    }
    patch: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    value_changed = False
    if not input_errors:
        holdings = {item["ticker"]: int(item["held_quantity"]) for item in snapshot["holdings"]}
        costs = {item["ticker"]: float(item["average_cost"]) for item in snapshot["holdings"]}
        basis = {ticker: derived_cost_basis(holdings[ticker], costs[ticker]) for ticker in holdings}
        patch = {
            "holdings": holdings, "average_cost_usd": costs,
            "position_cost_basis_usd": {ticker: float(value) for ticker, value in basis.items()},
            "aggregate_cost_basis_usd": float(sum(basis.values(), Decimal("0"))),
            "available_cash_usd": float(snapshot["cash"]["settled_available_cash"]),
        }
        changes = (_map_changes("holdings", portfolio.get("holdings"), patch["holdings"])
                   + _map_changes("average_cost_usd", portfolio.get("average_cost_usd"), patch["average_cost_usd"])
                   + _map_changes("position_cost_basis_usd", portfolio.get("position_cost_basis_usd"),
                                  patch["position_cost_basis_usd"])
                   + _scalar_change("aggregate_cost_basis_usd", portfolio.get("aggregate_cost_basis_usd"),
                                    patch["aggregate_cost_basis_usd"])
                   + _scalar_change("available_cash_usd", portfolio.get("available_cash_usd"),
                                    patch["available_cash_usd"]))
        value_changed = bool(changes)
        changes += _record_changes(portfolio.get("last_confirmed_broker_snapshot"), record)
    warnings: list[str] = [] if open_orders_verified else ["OPEN_ORDERS_UNVERIFIED"]
    timing_tickers = set(((portfolio.get("timing_plan") or {}).get("positions") or {}).keys())
    if any(item["field"] == "holdings" and item["key"] in timing_tickers for item in changes):
        warnings.append("TIMING_PLAN_TICKER_CHANGED")
    unresolved = list(input_errors)
    before_hash = canonical_hash(portfolio)
    if ledger_last_hash_after is not None and ledger_last_hash_after != before_hash:
        # An outside change is a warning shown in the table. Only a state equal to the last entry's
        # before-hash (entry written, state write failed) blocks applying (P4 1-12).
        warnings.append("STATE_CHANGED_OUTSIDE_LEDGER")
        if ledger_last_hash_before == before_hash:
            unresolved.append("STATE_CHANGED_OUTSIDE_LEDGER")
    if not ledger_integrity_ok:
        warnings.append("LEDGER_INTEGRITY_FAILED")
        unresolved.append("LEDGER_INTEGRITY_FAILED")
    status = ("BLOCKED" if unresolved else "NO_CHANGE_REQUIRED" if not changes
              else "USER_CONFIRMATION_REQUIRED")
    proposal: dict[str, Any] = {
        "schema_version": PROPOSAL_SCHEMA_VERSION, "proposal_type": PROPOSAL_TYPE,
        "proposal_id": "", "confirm_code": "",
        "bundle_id": "KIWOOM-" + snapshot["snapshot_hash"][:20],
        "status": status, "change_kind": "NONE" if status != "USER_CONFIRMATION_REQUIRED"
        else "VALUES" if value_changed else "METADATA_ONLY",
        "authority_state": "BROKER_READ_PENDING_USER_CONFIRMATION", "scope": RECONCILIATION_SCOPE,
        "generated_at": snapshot.get("generated_at"),
        "expires_at": _utc_iso(earliest + timedelta(seconds=int(maximum_age_seconds))),
        "maximum_age_seconds": int(maximum_age_seconds),
        "source": {
            "kind": PROPOSAL_SOURCE, "snapshot_hash": snapshot["snapshot_hash"], "snapshot_path": snapshot_path,
            "runtime_commit": next((result.get("runtime_commit") for result in results
                                    if isinstance(result, dict) and result.get("runtime_commit")), None),
            "broker_snapshot_as_of": snapshot.get("broker_snapshot_as_of"),
            "earliest_required_retrieved_at": _utc_iso(earliest) if times else None,
            "retrieved_at": {operation: _utc_iso(value) for operation, value in sorted(times.items())},
            "operation_statuses": dict(snapshot.get("operation_statuses") or {}),
            "required_operations": list(REQUIRED_RECONCILIATION_OPERATIONS),
            "display_only_operations": list(DISPLAY_ONLY_OPERATIONS),
        },
        "portfolio_state_path": portfolio_state_path,
        "expected_state_revision": portfolio.get("state_revision"),
        "expected_portfolio_hash_before": before_hash,
        "state_last_updated_at": portfolio.get("last_updated_at"),
        "changes": changes, "proposed_patch": patch if status == "USER_CONFIRMATION_REQUIRED" else {},
        "cost_basis_derivation": COST_BASIS_DERIVATION,
        "cost_basis_crosscheck": _cost_basis_crosscheck(results, patch) if patch else [],
        "cash_semantics": {
            "available_cash_usd_basis": "MIN_WITHDRAWABLE_AND_ORDER_AVAILABLE_USD",
            "cash_verified_scope": "available_cash_only", "settled_cash": False,
            "unsettled_funds_included": False, "margin_or_credit_included": False,
        },
        "confirmed_snapshot_record": record,
        "never_touched": list(NEVER_TOUCHED_FIELDS),
        "post_apply_checks": {"check": None, "session_date": None, "status": "NOT_APPLICABLE",
                              "errors": [], "policy_positions_mismatch": False},
        "recent_fills": _recent_fills(results),
        "warnings": warnings, "unresolved_fields": unresolved,
        "open_orders_verified": open_orders_verified,
        "auto_apply": False, "fill_inference_performed": False, "inferred_fills": False,
        "quantity_authority": "none", "order_authority": False,
    }
    if cash_flow_declaration is not None:
        proposal["cash_flow_declaration"] = cash_flow_declaration
    if status == "USER_CONFIRMATION_REQUIRED":
        if post_apply_check is None:
            proposal["post_apply_checks"]["status"] = "NOT_RUN"
            unresolved.append("POST_APPLY_CHECK_NOT_RUN")
            proposal.update(status="BLOCKED", change_kind="NONE", proposed_patch={})
        else:
            result = post_apply_check(portfolio, proposal)
            proposal["post_apply_checks"] = {
                "check": result.get("check"), "session_date": result.get("session_date"),
                "status": result.get("status") if result.get("status") in {"PASS", "FAIL", "NOT_APPLICABLE"}
                else "FAIL",
                "errors": [str(item) for item in result.get("errors") or []],
                "policy_positions_mismatch": result.get("policy_positions_mismatch") is True,
            }
            if proposal["post_apply_checks"]["status"] == "FAIL":
                warnings.append("POST_APPLY_ALERT_ENGINE_CHECK_FAILED")
            if proposal["post_apply_checks"]["policy_positions_mismatch"]:
                warnings.append("POLICY_POSITIONS_MISMATCH")
    proposal["proposal_id"] = proposal_content_hash(proposal)
    proposal["confirm_code"] = proposal["proposal_id"][:8].upper()
    return proposal
