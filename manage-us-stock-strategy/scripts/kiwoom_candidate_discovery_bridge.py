#!/usr/bin/env python3
"""Strict Kiwoom U.S. candidate-discovery bridge; query/search routes only."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from kiwoom_runtime_bridge import (
    BridgeError, _continuation, _exception_failure, _load_env_without_echo,
    _parse_last_json, _return_code_ok, _runtime_session, utc_now,
)


REQUEST_KEYS = {"operation", "condition_sequence", "ticker", "exchange"}
TICKER_FIELDS = ("stk_cd", "9001")


def _targets(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    value = policy.get("allowed_api_targets")
    if not isinstance(value, dict) or not value:
        raise BridgeError("DISCOVERY_ALLOWLIST_MISSING")
    return value


def validate_request(value: Any, policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - REQUEST_KEYS:
        raise BridgeError("INVALID_DISCOVERY_REQUEST")
    operation = str(value.get("operation") or "")
    if operation not in _targets(policy):
        raise BridgeError("OPERATION_NOT_ALLOWLISTED")
    if operation == "condition_search" and not str(value.get("condition_sequence") or "").isdigit():
        raise BridgeError("CONDITION_SEQUENCE_REQUIRED")
    ticker = str(value.get("ticker") or "").strip().upper() or None
    exchange = str(value.get("exchange") or "").strip().upper() or None
    if operation == "security_info" and (not ticker or not exchange):
        raise BridgeError("SECURITY_IDENTITY_PARAMETERS_REQUIRED")
    return {"operation": operation, "condition_sequence": value.get("condition_sequence"),
            "ticker": ticker, "exchange": exchange}


def blocked_api_target(policy: dict[str, Any], api_id: str, path: str) -> bool:
    if api_id in set(policy.get("blocked_api_ids") or []):
        return True
    if path in set(policy.get("blocked_paths") or []):
        return True
    allowed = {(str(meta.get("api_id")), str(meta.get("path")))
               for meta in _targets(policy).values() if isinstance(meta, dict)}
    return (str(api_id), str(path)) not in allowed


def _safe_rows(raw: Any, policy: dict[str, Any], operation: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(raw, list):
        raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
    fields = tuple(policy.get("safe_response_fields") or [])
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if isinstance(item, (list, tuple)) and operation in {"condition_list", "condition_search"}:
            keys = ("seq", "name") if operation == "condition_list" else (
                "9001", "302", "10", "25", "11", "12", "13", "16", "17", "18", "318", "stex_tp")
            item = dict(zip(keys, item))
        if not isinstance(item, dict):
            failures.append({"operation": operation, "row_index": index, "reason": "MALFORMED_RECORD"})
            continue
        safe = {field: item.get(field) for field in fields if field in item}
        ticker = next((str(item.get(field) or "").strip().upper() for field in TICKER_FIELDS
                       if item.get(field)), None)
        if operation != "condition_list" and (not ticker or not ticker.replace(".", "").replace("-", "").isalnum()):
            failures.append({"operation": operation, "row_index": index, "reason": "INVALID_TICKER"})
            continue
        if ticker:
            safe["canonical_ticker"] = ticker
        safe["source_operation"] = operation
        rows.append(safe)
    return rows, failures


def classify_instrument(row: dict[str, Any]) -> str:
    name = " ".join(str(row.get(key) or "").upper() for key in ("stk_nm", "stk_enm", "302"))
    source = str(row.get("source_operation") or "")
    if any(term in name for term in (" WARRANT", " WTS", " C/WTS", " UNIT", " RIGHTS", " RIGHT ", " PREFERRED")):
        return "unsupported_product"
    is_etf = (source.endswith("_etf") or " ETF" in " " + name
              or str(row.get("isEtf") or "").upper() in {"Y", "1", "TRUE"})
    if is_etf and any(term in name for term in ("INVERSE", "SHORT", "BEAR", "-1X", "-2X", "-3X")):
        return "inverse_product"
    if is_etf and any(term in name for term in ("2X", "3X", "ULTRA", "LEVERAGED", "BULL")):
        return "leveraged_etf"
    if is_etf:
        return "spot_etf"
    if " ADR" in " " + name or " ADS" in " " + name or "DEPOSITARY" in name:
        return "adr"
    return "ordinary_common_stock"


def classify_liquidity(row: dict[str, Any]) -> str:
    raw = row.get("acc_trde_qty")
    if raw in (None, ""):
        return "UNVERIFIED_NO_APPROVED_THRESHOLD"
    try:
        volume = int(str(raw).replace(",", "").lstrip("+-"))
    except ValueError:
        return "UNVERIFIED_MALFORMED_VOLUME"
    return "LOW_LIQUIDITY_CANDIDATE" if volume == 0 else "UNVERIFIED_NO_APPROVED_THRESHOLD"


def deduplicate_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("canonical_ticker") or "")
        exchange = str(row.get("stex_tp") or "UNKNOWN")
        if not ticker:
            continue
        key = (ticker, exchange)
        if key not in values:
            item = dict(row)
            item["instrument_class"] = classify_instrument(row)
            item["liquidity_classification"] = classify_liquidity(row)
            item["discovery_sources"] = [row.get("source_operation")]
            item["lifecycle_state"] = "DISCOVERED_RESEARCH_ONLY"
            item["price_authority_status"] = "KIWOOM_UNKNOWN_MARKET_PHASE"
            item["technical_condition_status"] = "NOT_EVALUATED"
            item["watchlist_approval_required"] = True
            item["quantity"] = None
            item["quantity_authority"] = "none"
            item["order_authority"] = False
            values[key] = item
        else:
            source = row.get("source_operation")
            if source not in values[key]["discovery_sources"]:
                values[key]["discovery_sources"].append(source)
    return sorted(values.values(), key=lambda item: (item["canonical_ticker"], str(item.get("stex_tp"))))


def _fetch_rest(session: dict[str, Any], meta: dict[str, Any], body: dict[str, Any],
                maximum_pages: int) -> tuple[list[Any], dict[str, Any]]:
    api_id, path = str(meta["api_id"]), str(meta["path"])
    rows: list[Any] = []
    cont_yn = next_key = None
    exhausted = False
    prior_key = None
    for page in range(1, maximum_pages + 1):
        session["pacer"]()
        response = session["client"].fetch_page(api_id=api_id, path=path, body=body,
                                                cont_yn=cont_yn, next_key=next_key)
        payload = getattr(response, "body", None)
        if not isinstance(payload, dict) or not _return_code_ok(payload):
            raise BridgeError("KIWOOM_API_UNAVAILABLE", "EMPTY_RESPONSE")
        current = payload if meta.get("response_key") is None else payload.get(meta.get("response_key"))
        if meta.get("response_key") is None:
            current = [current]
        if not isinstance(current, list):
            raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
        rows.extend(current)
        cont_yn, next_key = _continuation(response)
        if str(cont_yn or "").upper() not in {"Y", "2", "MORE", "TRUE"} or not next_key:
            exhausted = True
            break
        if next_key == prior_key:
            raise BridgeError("KIWOOM_PAGINATION_NO_PROGRESS")
        prior_key = next_key
    return rows, {"api_id": api_id, "pages": page, "exhausted": exhausted}


def _fetch_websocket(meta: dict[str, Any], body: dict[str, Any]) -> list[Any]:
    from kiwoom import get_ws_client
    payload = asyncio.run(get_ws_client().request_once(api_url=str(meta["path"]), body=body))
    if not isinstance(payload, dict):
        raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
    rows = payload.get(meta.get("response_key"))
    if not isinstance(rows, list):
        raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
    return rows


def external_worker(stdin_text: str, runtime: Path) -> dict[str, Any]:
    try:
        envelope = json.loads(stdin_text)
        policy = envelope["policy"]
        requests = [validate_request(item, policy) for item in envelope["requests"]]
        _load_env_without_echo(runtime / ".env")
        session = _runtime_session(
            runtime, float(policy["minimum_request_interval_seconds"]),
            int(policy["maximum_attempts"]), 1.0,
            {"TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH"},
            {"HTTP_429", "AUTHENTICATION_FAILURE"}, 1, 0,
            int(policy["maximum_pages"]), 1,
        )
        results = []
        for request in requests:
            operation = request["operation"]
            meta = _targets(policy)[operation]
            try:
                if blocked_api_target(policy, str(meta["api_id"]), str(meta["path"])):
                    raise BridgeError("KIWOOM_ORDER_ENDPOINT_BLOCKED")
                body = dict(meta.get("default_body") or {})
                if operation == "condition_search":
                    body["seq"] = request["condition_sequence"]
                if operation == "security_info":
                    body.update({"stex_tp": request["exchange"], "stk_cd": request["ticker"]})
                if meta.get("transport") == "WEBSOCKET":
                    raw, pagination = _fetch_websocket(meta, body), {"api_id": meta["api_id"], "pages": 1, "exhausted": True}
                else:
                    raw, pagination = _fetch_rest(session, meta, body, int(policy["maximum_pages"]))
                rows, failures = _safe_rows(raw[:int(policy["maximum_rows_per_operation"])], policy, operation)
                results.append({"bridge_status": "PASS", "operation": operation, "data": rows,
                                "ticker_failures": failures, "pagination": pagination,
                                "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                                "portfolio_mutation": False, "quantity": None,
                                "quantity_authority": "none", "order_authority": False})
            except Exception as exc:
                results.append({"bridge_status": getattr(exc, "status", "KIWOOM_API_UNAVAILABLE"),
                                "failure_type": getattr(exc, "failure_type", _exception_failure(exc)),
                                "operation": operation, "data": [], "ticker_failures": [],
                                "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                                "portfolio_mutation": False, "quantity": None,
                                "quantity_authority": "none", "order_authority": False})
        return {"bridge_status": "PASS", "results": results, "order_authority": False}
    except Exception as exc:
        return {"bridge_status": "KIWOOM_API_UNAVAILABLE",
                "failure_type": getattr(exc, "failure_type", _exception_failure(exc)),
                "order_authority": False}


def invoke_discovery_bridge_batch(requests: list[dict[str, Any]], *, runtime: Path,
                                  policy: dict[str, Any], rate_policy: dict[str, Any],
                                  runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> list[dict[str, Any]]:
    safe_requests = [validate_request(item, policy) for item in requests]
    python_path = runtime / str(rate_policy["external_python_relative_path"])
    if not python_path.is_file():
        return [{"bridge_status": "RUNTIME_PYTHON_UNAVAILABLE", "operation": item["operation"],
                 "data": [], "ticker_failures": [], "order_authority": False} for item in safe_requests]
    try:
        completed = runner(
            [str(python_path), str(Path(__file__).resolve()), "--external-worker"],
            input=json.dumps({"policy": policy, "requests": safe_requests}, separators=(",", ":")),
            cwd=str(runtime), capture_output=True, text=True, encoding="utf-8",
            timeout=int(policy["request_timeout_seconds"]) * max(1, len(safe_requests)), check=False,
        )
        payload = _parse_last_json(completed.stdout)
        values = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(values, list) or len(values) != len(safe_requests):
            raise BridgeError("BRIDGE_BATCH_OUTPUT_INVALID")
        return values
    except (OSError, subprocess.TimeoutExpired, BridgeError):
        return [{"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "TIMEOUT",
                 "operation": item["operation"], "data": [], "ticker_failures": [],
                 "order_authority": False} for item in safe_requests]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-worker", action="store_true")
    args = parser.parse_args()
    if not args.external_worker:
        raise SystemExit("external worker mode is required")
    result = external_worker(sys.stdin.read(), Path.cwd())
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("bridge_status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
