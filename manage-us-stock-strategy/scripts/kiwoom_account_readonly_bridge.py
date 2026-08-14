#!/usr/bin/env python3
"""Narrow Kiwoom U.S. account read-only bridge isolated from market-data acceptance."""

from __future__ import annotations

import argparse
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

ACCOUNT_APIS = {
    "account_deposit_read": ("ust21110", "/api/us/acnt"),
    "account_deposit_detail_read": ("ust21160", "/api/us/acnt"),
    "account_holdings_read": ("ust21070", "/api/us/acnt"),
    "account_open_items": ("ust21050", "/api/us/acnt"),
    "account_fills_read": ("ust21510", "/api/us/acnt"),
    "account_realized_pnl_read": ("ust21630", "/api/us/acnt"),
}
ACCOUNT_BODIES = {
    "account_deposit_read": {},
    "account_deposit_detail_read": {},
    "account_holdings_read": {"stex_tp": "", "stk_cd": ""},
    "account_open_items": {"ord_dt": "", "slby_tp": "0", "stex_tp": "", "stk_cd": ""},
    "account_fills_read": {"stex_tp": "", "stk_cd": ""},
    "account_realized_pnl_read": {"fc_krw_tp": "0", "stex_tp": "", "stk_cd": ""},
}
SAFE_FIELDS = {
    "account_deposit_read": ("crnc_code", "crnc_nm", "fc_entra", "fc_pymn_alowa", "fc_ord_alowa"),
    "account_deposit_detail_read": (
        "d0_setl_dt", "d0_usd_fx_entr", "d1_setl_dt", "d1_usd_fx_entr", "d1_usd_exct_amt",
        "d1_usd_buy_excta", "d1_usd_sell_excta", "d2_setl_dt", "d2_usd_fx_entr",
        "d2_usd_exct_amt", "d2_usd_buy_excta", "d2_usd_sell_excta",
    ),
    "account_holdings_read": (
        "stex_nm", "crnc_code", "stk_cd", "frgn_stk_nm", "qty", "poss_qty", "sell_alowq",
        "frgn_stk_book_uv", "now_pric", "evlt_amt", "pl_amt", "pl_rt",
    ),
    "account_open_items": (
        "crnc_code", "stk_cd", "frgn_stk_nm", "ord_qty", "ord_uv", "cntr_qty", "cntr_uv",
        "ord_remnq", "ord_time", "ord_stat", "slby_tp",
    ),
    "account_fills_read": (
        "crnc_code", "stk_cd", "frgn_stk_nm", "ord_qty", "cntr_qty", "cntr_uv", "cnfm_qty",
        "ord_time", "ord_resp_time", "cntr_time", "ord_remnq", "ord_stat_nm", "slby_tp",
    ),
    "account_realized_pnl_read": (
        "crnc_code", "stk_cd", "frgn_stk_nm", "cntr_sellq", "cntr_sella", "tdy_pl_amt", "pl_rt",
    ),
}


def validate_request(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or value.get("operation") not in ACCOUNT_APIS:
        raise BridgeError("OPERATION_NOT_ALLOWLISTED")
    return {"operation": str(value["operation"])}


def _fetch_account_page(session: dict[str, Any], operation: str, body: dict[str, Any],
                        *, cont_yn: str | None, next_key: str | None) -> Any:
    """Call only the exact read-only account route selected by an allowlisted operation."""
    api_id, path = ACCOUNT_APIS[operation]
    attempts = int(session["maximum_attempts"])
    last_error: Exception = BridgeError("KIWOOM_API_UNAVAILABLE", "EMPTY_RESPONSE")
    for attempt in range(attempts):
        try:
            session["pacer"]()
            response = session["client"].fetch_page(
                api_id=api_id, path=path, body=body, cont_yn=cont_yn, next_key=next_key,
            )
            payload = getattr(response, "body", None)
            if not isinstance(payload, dict):
                raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
            if not _return_code_ok(payload):
                raise BridgeError("KIWOOM_API_RESPONSE_ERROR", "API_RESPONSE_ERROR")
            return response
        except Exception as exc:
            last_error = exc
            failure = _exception_failure(exc)
            if failure in session["immediate_open_failure_types"]:
                raise
            if failure not in session["retryable_failure_types"] or attempt + 1 >= attempts:
                raise
            time.sleep(float(session["retry_backoff_seconds"]))
    raise last_error


def _read_pages(session: dict[str, Any], operation: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    api_id, path = ACCOUNT_APIS[operation]
    rows: list[dict[str, Any]] = []
    cont_yn: str | None = None
    next_key: str | None = None
    exhausted = False
    pages = 0
    for page_index in range(1, int(session["maximum_history_pages"]) + 1):
        response = _fetch_account_page(
            session, operation, ACCOUNT_BODIES[operation], cont_yn=cont_yn, next_key=next_key,
        )
        raw = response.body.get("result_list")
        if raw is None and operation == "account_deposit_detail_read":
            raw = [response.body]
        if not isinstance(raw, list):
            raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
        fields = SAFE_FIELDS[operation]
        rows.extend({field: item.get(field) for field in fields} for item in raw if isinstance(item, dict))
        pages = page_index
        next_cont, next_value = _continuation(response)
        if str(next_cont or "").upper() not in {"Y", "2", "MORE", "TRUE"} or not next_value:
            exhausted = True
            break
        if next_value == next_key:
            raise BridgeError("KIWOOM_PAGINATION_NO_PROGRESS")
        cont_yn, next_key = next_cont, next_value
    return rows, {"api_id": api_id, "pages": pages, "exhausted": exhausted,
                  "complete": exhausted, "secret_fields_retained": False}


def external_worker(stdin_text: str, runtime: Path, minimum_interval_seconds: float = 0.25,
                    maximum_attempts: int = 1, maximum_pages: int = 10) -> dict[str, Any]:
    try:
        raw = json.loads(stdin_text)
        requests = [validate_request(item) for item in raw]
        _load_env_without_echo(runtime / ".env")
        session = _runtime_session(
            runtime, minimum_interval_seconds, maximum_attempts, 1.0,
            {"TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH"},
            {"HTTP_429", "AUTHENTICATION_FAILURE"}, 1, 0, maximum_pages, 1,
        )
        results = []
        for request in requests:
            try:
                rows, pagination = _read_pages(session, request["operation"])
                results.append({
                    "bridge_status": "PASS" if pagination["complete"] else "PARTIAL",
                    "operation": request["operation"], "data": rows, "pagination": pagination,
                    "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                    "account_identifier_stored": False, "portfolio_mutation": False,
                    "quantity_authority": "none", "order_authority": False,
                })
            except Exception as exc:
                failure = exc.failure_type if isinstance(exc, BridgeError) else _exception_failure(exc)
                results.append({"bridge_status": getattr(exc, "status", "KIWOOM_API_UNAVAILABLE"),
                                "failure_type": failure, "operation": request["operation"],
                                "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                                "order_authority": False})
        return {"bridge_status": "PASS", "results": results, "order_authority": False}
    except Exception as exc:
        return {"bridge_status": "KIWOOM_API_UNAVAILABLE",
                "failure_type": getattr(exc, "failure_type", _exception_failure(exc)),
                "order_authority": False}


def _sanitize(value: dict[str, Any], operation: str) -> dict[str, Any]:
    safe = {"bridge_status": str(value.get("bridge_status", "BRIDGE_OUTPUT_INVALID")),
            "operation": operation, "runtime_commit": value.get("runtime_commit"),
            "retrieved_at": value.get("retrieved_at"), "account_identifier_stored": False,
            "portfolio_mutation": False, "quantity_authority": "none", "order_authority": False}
    if isinstance(value.get("failure_type"), str):
        safe["failure_type"] = value["failure_type"]
    data = value.get("data")
    safe["data"] = [{field: row.get(field) for field in SAFE_FIELDS[operation]}
                    for row in data if isinstance(row, dict)] if isinstance(data, list) else []
    if isinstance(value.get("pagination"), dict):
        safe["pagination"] = {key: value["pagination"].get(key)
                              for key in ("api_id", "pages", "exhausted", "complete", "secret_fields_retained")}
    return safe


def invoke_account_bridge_batch(requests: list[dict[str, Any]], *, runtime: Path, policy: dict[str, Any],
                                runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> list[dict[str, Any]]:
    sanitized = [validate_request(item) for item in requests]
    python_path = runtime / str(policy["external_python_relative_path"])
    if not python_path.is_file():
        return [{"bridge_status": "RUNTIME_PYTHON_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
                 "operation": item["operation"], "order_authority": False} for item in sanitized]
    try:
        completed = runner(
            [str(python_path), str(Path(__file__).resolve()), "--external-worker",
             "--minimum-request-interval", str(policy.get("minimum_request_interval_seconds", 0.25)),
             "--maximum-attempts", str(policy.get("maximum_attempts", 1)),
             "--maximum-pages", str((policy.get("history_policy") or {}).get("maximum_pages", 10))],
            input=json.dumps(sanitized, separators=(",", ":")), cwd=str(runtime),
            capture_output=True, text=True, encoding="utf-8",
            timeout=int(policy["request_timeout_seconds"]) * max(1, len(sanitized)), check=False,
        )
        payload = _parse_last_json(completed.stdout)
        raw_results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(raw_results, list) or len(raw_results) != len(sanitized):
            raise BridgeError("BRIDGE_BATCH_OUTPUT_INVALID")
        return [_sanitize(value if isinstance(value, dict) else {}, request["operation"])
                for value, request in zip(raw_results, sanitized)]
    except (OSError, subprocess.TimeoutExpired, BridgeError):
        return [{"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "TIMEOUT",
                 "operation": item["operation"], "order_authority": False} for item in sanitized]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-worker", action="store_true")
    parser.add_argument("--minimum-request-interval", type=float, default=0.25)
    parser.add_argument("--maximum-attempts", type=int, default=1)
    parser.add_argument("--maximum-pages", type=int, default=10)
    args = parser.parse_args()
    if not args.external_worker:
        raise SystemExit("external worker mode is required")
    result = external_worker(sys.stdin.read(), Path.cwd(), max(0.0, args.minimum_request_interval),
                             max(1, args.maximum_attempts), max(1, args.maximum_pages))
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("bridge_status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
