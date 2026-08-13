#!/usr/bin/env python3
"""Build a schema-valid Kiwoom read-only shadow market snapshot."""

from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kiwoom_runtime_bridge import invoke_bridge, invoke_bridge_batch
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from kiwoom_provider_preflight import run_preflight
from provider_resilience import update_provider_health
from resolve_kiwoom_us_instrument import resolve_instrument
from validation_common import file_hash, load_json, validate_instance
from validate_kiwoom_market_snapshot import validate_snapshot_semantics


BridgeCall = Callable[[dict[str, Any]], dict[str, Any]]
BatchBridgeCall = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def normalize_series(
    rows: Any, *, ticker: str, completed_session: str, price_basis: str,
    minimum_history_bars: int = 1, pagination: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_session: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        session_raw = str(row.get("dt", ""))
        if len(session_raw) != 8 or not session_raw.isdigit():
            continue
        session = f"{session_raw[:4]}-{session_raw[4:6]}-{session_raw[6:]}"
        values = {
            "open": _number(row.get("open_pric")),
            "high": _number(row.get("high_pric")),
            "low": _number(row.get("low_pric")),
            "close": _number(row.get("cur_prc")),
            "volume": _number(row.get("acc_trde_qty")),
        }
        if any(value is None for value in values.values()):
            continue
        candidate = {"session": session, **values}
        if session > completed_session:
            errors.append(f"FUTURE_BAR_REJECTED:{session}")
            continue
        if (
            float(candidate["open"]) <= 0 or float(candidate["high"]) <= 0
            or float(candidate["low"]) <= 0 or float(candidate["close"]) <= 0
            or float(candidate["volume"]) < 0
            or float(candidate["high"]) < max(float(candidate["open"]), float(candidate["low"]), float(candidate["close"]))
            or float(candidate["low"]) > min(float(candidate["open"]), float(candidate["high"]), float(candidate["close"]))
        ):
            errors.append(f"INVALID_OHLCV:{session}")
            continue
        existing = by_session.get(session)
        if existing is not None and existing != candidate:
            errors.append(f"CONFLICTING_DUPLICATE_BAR:{session}")
            continue
        by_session[session] = candidate
    normalized = sorted(by_session.values(), key=lambda item: item["session"])
    matching = [item for item in normalized if item["session"] == completed_session]
    completed_close = matching[-1]["close"] if matching else None
    history_sufficient = len(normalized) >= int(minimum_history_bars)
    if not matching:
        errors.append("COMPLETED_SESSION_MISSING")
    if not history_sufficient:
        errors.append("INSUFFICIENT_HISTORY")
    status = "PASS" if not errors else "DATA_BLOCKED"
    return {
        "ticker": ticker,
        "price_basis": price_basis,
        "fx_applied": False,
        "completed_session": completed_session,
        "completed_close": completed_close,
        "bars": normalized,
        "history_bar_count": len(normalized),
        "minimum_history_bars": int(minimum_history_bars),
        "history_status": "SUFFICIENT" if history_sufficient else "INSUFFICIENT_HISTORY",
        "validation_errors": list(dict.fromkeys(errors)),
        "pagination": pagination,
        "status": status,
        "order_authority": False,
    }


def blocked_ticker_result(
    ticker: str, *, completed_session: str, generated_at: str,
    reason: str, runtime_commit: str = "", minimum_history_bars: int = 1,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "status": "DATA_BLOCKED",
        "identity": resolve_instrument(
            ticker, stock_rows=[], exchange_rows=[], etf_rows=[],
            runtime_commit=runtime_commit, verified_at=generated_at, api_available=False,
        ),
        "stock_info_status": "NOT_EVALUATED",
        "raw": normalize_series([], ticker=ticker, completed_session=completed_session, price_basis="RAW", minimum_history_bars=minimum_history_bars),
        "adjusted": normalize_series([], ticker=ticker, completed_session=completed_session, price_basis="ADJUSTED", minimum_history_bars=minimum_history_bars),
        "failure_reason": reason,
        "order_authority": False,
    }


def _failure_type(response: dict[str, Any]) -> str:
    value = response.get("failure_type")
    return value if value in {"HTTP_429", "TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH", "AUTHENTICATION_FAILURE"} else "EMPTY_RESPONSE"


def _bridge_data(call: BridgeCall, request: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    response = call(request)
    data = response.get("data", [])
    return (data if isinstance(data, list) else []), response


def build_snapshot(
    tickers: list[str], *, completed_session: str, bridge_call: BridgeCall,
    generated_at: str, portfolio_state_hash: str, preflight_status: str = "NOT_RUN",
    minimum_history_bars: int = 1,
) -> dict[str, Any]:
    symbols = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))
    results: list[dict[str, Any]] = []
    provider_health: dict[str, Any] | None = None
    runtime_commits: set[str] = set()
    for ticker in symbols:
        if provider_health and provider_health.get("circuit_state") == "OPEN":
            commit_hint = next(iter(runtime_commits)) if len(runtime_commits) == 1 else ""
            results.append(blocked_ticker_result(
                ticker, completed_session=completed_session, generated_at=generated_at,
                reason="GLOBAL_KIWOOM_CIRCUIT_OPEN", runtime_commit=commit_hint,
                minimum_history_bars=minimum_history_bars,
            ))
            continue
        try:
            stock_rows, stock_response = _bridge_data(bridge_call, {"operation": "stock_list", "ticker": ticker, "fx_applied": False})
            if stock_response.get("bridge_status") != "PASS":
                results.append(blocked_ticker_result(
                    ticker, completed_session=completed_session, generated_at=generated_at,
                    reason=str(stock_response.get("bridge_status") or "KIWOOM_API_UNAVAILABLE"),
                    runtime_commit=str(stock_response.get("runtime_commit") or ""),
                    minimum_history_bars=minimum_history_bars,
                ))
                provider_health = update_provider_health(provider_health, _failure_type(stock_response), generated_at)
                continue
            exchange_rows: list[dict[str, Any]] = []
            if not stock_rows:
                exchange_rows, exchange_response = _bridge_data(bridge_call, {"operation": "exchange_lookup", "ticker": ticker, "fx_applied": False})
                if exchange_response.get("bridge_status") != "PASS":
                    results.append(blocked_ticker_result(
                        ticker, completed_session=completed_session, generated_at=generated_at,
                        reason=str(exchange_response.get("bridge_status") or "KIWOOM_API_UNAVAILABLE"),
                        runtime_commit=str(exchange_response.get("runtime_commit") or ""),
                        minimum_history_bars=minimum_history_bars,
                    ))
                    provider_health = update_provider_health(provider_health, _failure_type(exchange_response), generated_at)
                    continue
            etf_rows, etf_response = _bridge_data(bridge_call, {"operation": "etf_etn_list", "ticker": ticker, "fx_applied": False})
            runtime_commit = str(stock_response.get("runtime_commit") or etf_response.get("runtime_commit") or "")
            if runtime_commit:
                runtime_commits.add(runtime_commit)
            identity = resolve_instrument(
                ticker, stock_rows=stock_rows, exchange_rows=exchange_rows, etf_rows=etf_rows,
                runtime_commit=runtime_commit, verified_at=str(stock_response.get("retrieved_at") or generated_at),
                api_available=stock_response.get("bridge_status") == "PASS",
            )
            if identity["mapping_status"] != "VERIFIED":
                results.append({
                    "ticker": ticker, "status": "DATA_BLOCKED", "identity": identity,
                    "stock_info_status": "NOT_EVALUATED",
                    "raw": normalize_series([], ticker=ticker, completed_session=completed_session, price_basis="RAW", minimum_history_bars=minimum_history_bars),
                    "adjusted": normalize_series([], ticker=ticker, completed_session=completed_session, price_basis="ADJUSTED", minimum_history_bars=minimum_history_bars),
                    "failure_reason": identity["mapping_status"], "order_authority": False,
                })
                provider_health = update_provider_health(provider_health, "EMPTY_RESPONSE", generated_at)
                continue
            info_rows, info_response = _bridge_data(bridge_call, {"operation": "stock_lookup", "ticker": ticker, "fx_applied": False})
            info_ok = bool(
                info_response.get("bridge_status") == "PASS" and len(info_rows) == 1
                and str(info_rows[0].get("stk_cd", "")).strip().upper() == ticker
                and str(info_rows[0].get("stex_tp", "")).strip().upper() == identity["stex_tp"]
            )
            raw_rows, raw_response = _bridge_data(bridge_call, {
                "operation": "daily_chart", "ticker": ticker, "completed_session": completed_session,
                "price_basis": "RAW", "fx_applied": False,
            })
            adjusted_rows, adjusted_response = _bridge_data(bridge_call, {
                "operation": "daily_chart", "ticker": ticker, "completed_session": completed_session,
                "price_basis": "ADJUSTED", "fx_applied": False,
            })
            runtime_commits.update(
                str(item.get("runtime_commit")) for item in (info_response, raw_response, adjusted_response) if item.get("runtime_commit")
            )
            raw = normalize_series(
                raw_rows, ticker=ticker, completed_session=completed_session, price_basis="RAW",
                minimum_history_bars=minimum_history_bars, pagination=raw_response.get("pagination"),
            )
            adjusted = normalize_series(
                adjusted_rows, ticker=ticker, completed_session=completed_session, price_basis="ADJUSTED",
                minimum_history_bars=minimum_history_bars, pagination=adjusted_response.get("pagination"),
            )
            passed = info_ok and raw["status"] == "PASS" and adjusted["status"] == "PASS"
            results.append({
                "ticker": ticker,
                "status": "PASS" if passed else "DATA_BLOCKED",
                "identity": identity,
                "stock_info_status": "PASS" if info_ok else "IDENTITY_MISMATCH",
                "raw": raw,
                "adjusted": adjusted,
                "failure_reason": None if passed else "TICKER_DATA_VALIDATION_FAILED",
                "order_authority": False,
            })
            if passed:
                provider_health = update_provider_health(provider_health, "SUCCESS", generated_at)
            else:
                failing = raw_response if raw_response.get("bridge_status") != "PASS" else adjusted_response
                provider_health = update_provider_health(provider_health, _failure_type(failing), generated_at)
        except Exception as exc:
            results.append(blocked_ticker_result(
                ticker, completed_session=completed_session, generated_at=generated_at,
                reason=type(exc).__name__, minimum_history_bars=minimum_history_bars,
            ))
            provider_health = update_provider_health(provider_health, "EMPTY_RESPONSE", generated_at)
    pass_count = sum(item["status"] == "PASS" for item in results)
    data_status = "PASS" if pass_count == len(results) and results else "PARTIAL" if pass_count else "DATA_INCOMPLETE"
    commit = next(iter(runtime_commits)) if len(runtime_commits) == 1 else None
    return {
        "schema_version": "1.0",
        "provider": "KIWOOM_REST",
        "provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
        "primary_provider": "yfinance",
        "generated_at": generated_at,
        "completed_session": completed_session,
        "official_runtime_commit": commit,
        "preflight_status": preflight_status,
        "session_lock": {"status": "LOCKED", "completed_session": completed_session},
        "provider_health": provider_health or {
            "last_success": None, "last_failure": generated_at, "consecutive_failures": 1,
            "failure_type": "EMPTY_RESPONSE", "circuit_state": "DEGRADED", "retry_after": None,
        },
        "data_status": data_status,
        "ticker_results": results,
        "portfolio_state_hash": portfolio_state_hash,
        "operational_shadow_session_increment": 0,
        "order_authority": False,
    }


def build_preflight_blocked_snapshot(
    tickers: list[str], *, completed_session: str, generated_at: str,
    portfolio_state_hash: str, preflight: dict[str, Any], minimum_history_bars: int = 1,
) -> dict[str, Any]:
    symbols = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))
    return {
        "schema_version": "1.0", "provider": "KIWOOM_REST",
        "provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED", "primary_provider": "yfinance",
        "generated_at": generated_at, "completed_session": completed_session,
        "official_runtime_commit": preflight.get("official_runtime_commit"),
        "preflight_status": "FAILED",
        "session_lock": {"status": "LOCKED", "completed_session": completed_session},
        "provider_health": preflight["provider_health"], "data_status": "DATA_INCOMPLETE",
        "ticker_results": [blocked_ticker_result(
            ticker, completed_session=completed_session, generated_at=generated_at,
            reason="GLOBAL_KIWOOM_PREFLIGHT_FAILED",
            runtime_commit=str(preflight.get("official_runtime_commit") or ""),
            minimum_history_bars=minimum_history_bars,
        ) for ticker in symbols],
        "portfolio_state_hash": portfolio_state_hash,
        "operational_shadow_session_increment": 0, "order_authority": False,
    }


def build_snapshot_with_batch(
    tickers: list[str], *, completed_session: str, batch_bridge_call: BatchBridgeCall,
    generated_at: str, portfolio_state_hash: str, preflight_status: str,
    minimum_history_bars: int = 1,
) -> dict[str, Any]:
    symbols = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))
    requests: list[dict[str, Any]] = []
    for ticker in symbols:
        requests.extend([
            {"operation": "stock_list", "ticker": ticker, "fx_applied": False},
            {"operation": "etf_etn_list", "ticker": ticker, "fx_applied": False},
            {"operation": "stock_lookup", "ticker": ticker, "fx_applied": False},
            {"operation": "daily_chart", "ticker": ticker, "completed_session": completed_session, "price_basis": "RAW", "fx_applied": False},
            {"operation": "daily_chart", "ticker": ticker, "completed_session": completed_session, "price_basis": "ADJUSTED", "fx_applied": False},
        ])
    responses = batch_bridge_call(requests)
    keyed: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for request, response in zip(requests, responses):
        keyed[(str(request["ticker"]), str(request["operation"]), request.get("price_basis"))] = response
    missing_identity = [
        ticker for ticker in symbols
        if (keyed.get((ticker, "stock_list", None)) or {}).get("bridge_status") == "PASS"
        and not (keyed.get((ticker, "stock_list", None)) or {}).get("data")
    ]
    if missing_identity:
        exchange_requests = [{"operation": "exchange_lookup", "ticker": ticker, "fx_applied": False} for ticker in missing_identity]
        for request, response in zip(exchange_requests, batch_bridge_call(exchange_requests)):
            keyed[(str(request["ticker"]), "exchange_lookup", None)] = response

    def replay(request: dict[str, Any]) -> dict[str, Any]:
        key = (str(request.get("ticker")), str(request["operation"]), request.get("price_basis"))
        return keyed.get(key, {
            "bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
            "operation": request["operation"], "ticker": request.get("ticker"),
            "data": [], "order_authority": False,
        })

    return build_snapshot(
        symbols, completed_session=completed_session, bridge_call=replay,
        generated_at=generated_at, portfolio_state_hash=portfolio_state_hash,
        preflight_status=preflight_status, minimum_history_bars=minimum_history_bars,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--readonly-policy", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    readonly_policy = load_json(args.readonly_policy)
    rate_policy = load_json(args.rate_policy)
    expected_runtime = str(readonly_policy["official_runtime_path"])
    if args.runtime.resolve() != Path(expected_runtime).resolve():
        raise SystemExit("KIWOOM_RUNTIME_PATH_MISMATCH")
    validate_shadow_output_path(args.output, args.repo_root, [args.portfolio_state, args.readonly_policy, args.rate_policy, args.schema])
    last_request = 0.0

    def call(request: dict[str, Any]) -> dict[str, Any]:
        nonlocal last_request
        minimum = float(rate_policy["minimum_request_interval_seconds"])
        wait = minimum - (time.monotonic() - last_request)
        if wait > 0:
            time.sleep(wait)
        response = invoke_bridge(request, runtime=args.runtime, policy=rate_policy)
        last_request = time.monotonic()
        return response

    def call_batch(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return invoke_bridge_batch(requests, runtime=args.runtime, policy=rate_policy)

    portfolio_hash = file_hash(args.portfolio_state)
    minimum_history_bars = int((rate_policy.get("history_policy") or {}).get("minimum_history_bars", 252))
    preflight = run_preflight(
        runtime=args.runtime, readonly_policy=readonly_policy, rate_policy=rate_policy,
        generated_at=args.generated_at, bridge_call=call,
    )
    if preflight["capability_status"] == "AVAILABLE":
        snapshot = build_snapshot_with_batch(
            args.ticker, completed_session=args.completed_session, batch_bridge_call=call_batch,
            generated_at=args.generated_at, portfolio_state_hash=portfolio_hash,
            preflight_status="PASS", minimum_history_bars=minimum_history_bars,
        )
    else:
        snapshot = build_preflight_blocked_snapshot(
            args.ticker, completed_session=args.completed_session, generated_at=args.generated_at,
            portfolio_state_hash=portfolio_hash, preflight=preflight,
            minimum_history_bars=minimum_history_bars,
        )
    errors = validate_instance(snapshot, args.schema) + validate_snapshot_semantics(snapshot)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, snapshot)
    return 0 if snapshot["data_status"] in {"PASS", "PARTIAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
