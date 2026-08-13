#!/usr/bin/env python3
"""Strict read-only JSON bridge for the external official Kiwoom runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ALLOWED_REQUEST_KEYS = {"operation", "ticker", "completed_session", "price_basis", "fx_applied"}
ALLOWED_OPERATIONS = {
    "oauth_health",
    "exchange_lookup",
    "stock_list",
    "stock_lookup",
    "etf_etn_list",
    "daily_chart",
    "market_quote",
}
BLOCKED_TERMS = {"order", "modify", "cancel", "credit", "forex", "fx_order", "account_mutation"}
RUNTIME_APIS = {
    "exchange_lookup": ("usa10098", "/api/us/stkinfo"),
    "stock_list": ("usa10099", "/api/us/stkinfo"),
    "stock_lookup": ("usa10100", "/api/us/stkinfo"),
    "etf_etn_list": ("usa10104", "/api/us/stkinfo"),
    "daily_chart": ("usa06012", "/api/us/chart"),
    "market_quote": ("usa20100", "/api/us/mrkcond"),
}
SAFE_IDENTITY_FIELDS = ("stex_tp", "stk_cd", "stk_nm", "stk_enm", "mkgb", "upgb", "isEtf")
SAFE_ETF_FIELDS = ("stex_tp", "code", "cate1", "cate2", "etn", "mkgb", "upnm")
SAFE_CHART_FIELDS = (
    "cur_prc", "pred_pre", "flu_rt", "acc_trde_qty", "acc_trde_prica",
    "open_pric", "high_pric", "low_pric", "dt", "upd_stkpc_tp", "upd_rt",
)
SAFE_QUOTE_FIELDS = (
    "stex_tp", "stk_cd", "stk_nm", "stk_enm", "cur_prc", "pred_pre",
    "flu_rt", "acc_trde_qty", "base_close_pric", "pre_open_pric",
    "pre_high_pric", "pre_low_pric", "open_pric", "high_pric", "low_pric",
    "curr_unit", "trd_susp_tp",
)


class BridgeError(RuntimeError):
    """A sanitized bridge failure with a deterministic status."""

    def __init__(self, status: str, failure_type: str = "SCHEMA_MISMATCH") -> None:
        super().__init__(status)
        self.status = status
        self.failure_type = failure_type


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_ticker(value: Any) -> str | None:
    if value is None:
        return None
    ticker = str(value).strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", ticker):
        raise BridgeError("INVALID_TICKER")
    return ticker


def validate_bridge_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - ALLOWED_REQUEST_KEYS:
        raise BridgeError("INVALID_BRIDGE_REQUEST")
    operation = str(value.get("operation", "")).strip().lower()
    if any(term in operation for term in BLOCKED_TERMS):
        raise BridgeError("KIWOOM_ORDER_ENDPOINT_BLOCKED", "AUTHENTICATION_FAILURE")
    if operation not in ALLOWED_OPERATIONS:
        raise BridgeError("OPERATION_NOT_ALLOWLISTED")
    ticker = _normalized_ticker(value.get("ticker"))
    if operation != "oauth_health" and ticker is None:
        raise BridgeError("TICKER_REQUIRED")
    completed_session = value.get("completed_session")
    if completed_session is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(completed_session)):
        raise BridgeError("INVALID_COMPLETED_SESSION")
    price_basis = value.get("price_basis")
    if price_basis is not None and price_basis not in {"RAW", "ADJUSTED"}:
        raise BridgeError("INVALID_PRICE_BASIS")
    fx_applied = value.get("fx_applied", False)
    if not isinstance(fx_applied, bool):
        raise BridgeError("INVALID_FX_FLAG")
    if fx_applied:
        raise BridgeError("FX_APPLIED_PRICE_REJECTED")
    if operation == "daily_chart" and (completed_session is None or price_basis is None):
        raise BridgeError("DAILY_CHART_PARAMETERS_REQUIRED")
    return {
        "operation": operation,
        "ticker": ticker,
        "completed_session": completed_session,
        "price_basis": price_basis,
        "fx_applied": False,
    }


def blocked_api_target(api_id: str, path: str) -> bool:
    allowed = {value for value in RUNTIME_APIS.values()}
    normalized = (str(api_id).strip(), str(path).strip())
    if any(term in (normalized[0] + " " + normalized[1]).lower() for term in BLOCKED_TERMS):
        return True
    return normalized not in allowed


def _load_env_without_echo(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


def _runtime_commit(runtime: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(runtime), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    commit = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise BridgeError("RUNTIME_COMMIT_UNAVAILABLE")
    return commit


def _return_code_ok(body: dict[str, Any]) -> bool:
    return body.get("return_code") in (None, 0, "0", "0000")


def _safe_universe(body: dict[str, Any], key: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    rows = body.get(key, [])
    if not isinstance(rows, list):
        raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
    return [{field: row.get(field) for field in fields} for row in rows if isinstance(row, dict)]


def _exact_rows(rows: list[dict[str, Any]], ticker: str, ticker_key: str) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get(ticker_key, "")).strip().upper() == ticker]


def _exception_failure(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return "HTTP_429"
    if status_code in {401, 403}:
        return "AUTHENTICATION_FAILURE"
    if isinstance(exc, BridgeError):
        return exc.failure_type
    return "EMPTY_RESPONSE"


def _request(session: dict[str, Any], api_id: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    if blocked_api_target(api_id, path):
        raise BridgeError("KIWOOM_ORDER_ENDPOINT_BLOCKED", "AUTHENTICATION_FAILURE")
    attempts = int(session["maximum_attempts"])
    last_error: Exception = BridgeError("KIWOOM_API_UNAVAILABLE", "EMPTY_RESPONSE")
    for attempt in range(attempts):
        try:
            session["pacer"]()
            response = session["client"].request(
                api_id=api_id, path=path, body=body, retry_on_auth_failure=False,
            )
            payload = response.body
            if not isinstance(payload, dict):
                raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
            if not _return_code_ok(payload):
                raise BridgeError("KIWOOM_API_UNAVAILABLE", "EMPTY_RESPONSE")
            return payload
        except Exception as exc:
            last_error = exc
            failure = _exception_failure(exc)
            if failure in session["immediate_open_failure_types"]:
                raise
            if failure not in session["retryable_failure_types"] or attempt + 1 >= attempts:
                raise
            time.sleep(float(session["retry_backoff_seconds"]))
    raise last_error


def _fetch_page(
    session: dict[str, Any], api_id: str, path: str, body: dict[str, Any],
    *, cont_yn: str | None, next_key: str | None,
) -> Any:
    """Fetch one official continuation page with the existing bounded retry policy."""
    if blocked_api_target(api_id, path):
        raise BridgeError("KIWOOM_ORDER_ENDPOINT_BLOCKED", "AUTHENTICATION_FAILURE")
    attempts = int(session["maximum_attempts"])
    last_error: Exception = BridgeError("KIWOOM_API_UNAVAILABLE", "EMPTY_RESPONSE")
    for attempt in range(attempts):
        try:
            session["pacer"]()
            response = session["client"].fetch_page(
                api_id=api_id,
                path=path,
                body=body,
                cont_yn=cont_yn,
                next_key=next_key,
            )
            payload = getattr(response, "body", None)
            if not isinstance(payload, dict):
                raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
            if not _return_code_ok(payload):
                raise BridgeError("KIWOOM_API_UNAVAILABLE", "EMPTY_RESPONSE")
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


def _continuation(response: Any) -> tuple[str | None, str | None]:
    value = getattr(response, "continuation", None)
    if isinstance(value, dict):
        return value.get("cont_yn"), value.get("next_key")
    return getattr(value, "cont_yn", None), getattr(value, "next_key", None)


def _daily_chart_pages(
    session: dict[str, Any], *, ticker: str, stex_tp: str,
    completed_session: str, price_basis: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read bounded official usa06012 continuation pages without guessing fields."""
    api_id, path = RUNTIME_APIS["daily_chart"]
    body = {
        "stex_tp": stex_tp,
        "stk_cd": ticker,
        "strt_dt": completed_session.replace("-", ""),
        "upd_stkpc_tp": "0" if price_basis == "RAW" else "1",
        "exrt_appl_tp": "0",
    }
    minimum = int(session["minimum_history_bars"])
    target = minimum + int(session["history_buffer_bars"])
    maximum_pages = int(session["maximum_history_pages"])
    no_progress_limit = int(session["no_progress_page_limit"])
    rows: list[dict[str, Any]] = []
    distinct_dates: set[str] = set()
    provenance: list[dict[str, Any]] = []
    cont_yn: str | None = None
    next_key: str | None = None
    no_progress = 0
    exhausted = False
    for page_index in range(1, maximum_pages + 1):
        response = _fetch_page(
            session, api_id, path, body, cont_yn=cont_yn, next_key=next_key,
        )
        payload = response.body
        page_rows = payload.get("result_list")
        if not isinstance(page_rows, list):
            raise BridgeError("KIWOOM_SCHEMA_MISMATCH")
        safe_rows = [
            {field: row.get(field) for field in SAFE_CHART_FIELDS}
            for row in page_rows if isinstance(row, dict)
        ]
        page_dates = {
            str(row.get("dt")) for row in safe_rows
            if re.fullmatch(r"\d{8}", str(row.get("dt", "")))
        }
        new_dates = page_dates - distinct_dates
        no_progress = no_progress + 1 if not new_dates else 0
        if no_progress >= no_progress_limit:
            raise BridgeError("KIWOOM_PAGINATION_NO_PROGRESS")
        rows.extend(safe_rows)
        distinct_dates.update(page_dates)
        next_cont_yn, next_next_key = _continuation(response)
        state_payload = json.dumps(
            {"cont_yn": next_cont_yn, "next_key": next_next_key},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        provenance.append({
            "page_index": page_index,
            "api_id": api_id,
            "row_count": len(safe_rows),
            "first_session": min(page_dates) if page_dates else None,
            "last_session": max(page_dates) if page_dates else None,
            "continuation_state_hash": hashlib.sha256(state_payload).hexdigest(),
            "retrieved_at": utc_now(),
        })
        if len(distinct_dates) >= target:
            break
        if next_cont_yn != "Y":
            exhausted = True
            break
        cont_yn, next_key = next_cont_yn, next_next_key
    pagination = {
        "api_id": api_id,
        "minimum_history_bars": minimum,
        "target_history_bars": target,
        "maximum_pages": maximum_pages,
        "pages_fetched": len(provenance),
        "distinct_session_count": len(distinct_dates),
        "provider_exhausted": exhausted,
        "status": "SUFFICIENT" if len(distinct_dates) >= minimum else "INSUFFICIENT_HISTORY",
        "pages": provenance,
    }
    return rows, pagination


def _stock_universe(session: dict[str, Any]) -> list[dict[str, Any]]:
    if session.get("stock_universe") is None:
        body = _request(session, "usa10099", "/api/us/stkinfo", {"stex_tp": "%"})
        session["stock_universe"] = _safe_universe(body, "list", SAFE_IDENTITY_FIELDS)
    return session["stock_universe"]


def _etf_universe(session: dict[str, Any]) -> list[dict[str, Any]]:
    if session.get("etf_universe") is None:
        body = _request(session, "usa10104", "/api/us/stkinfo", {"stex_tp": "%"})
        session["etf_universe"] = _safe_universe(body, "list", SAFE_ETF_FIELDS)
    return session["etf_universe"]


def _resolve_identity(session: dict[str, Any], ticker: str) -> dict[str, Any]:
    candidates = _exact_rows(_stock_universe(session), ticker, "stk_cd")
    if not candidates:
        body = _request(session, "usa10098", "/api/us/stkinfo", {"stk_cd": ticker})
        candidates = _exact_rows(_safe_universe(body, "list", SAFE_IDENTITY_FIELDS), ticker, "stk_cd")
    unique = {(row.get("stk_cd"), row.get("stex_tp")): row for row in candidates if row.get("stex_tp")}
    if len(unique) != 1:
        status = "NOT_FOUND" if not unique else "AMBIGUOUS"
        return {"status": status, "candidates": list(unique.values())}
    return {"status": "VERIFIED", "identity": next(iter(unique.values()))}


def _runtime_session(
    runtime: Path, minimum_interval_seconds: float, maximum_attempts: int,
    retry_backoff_seconds: float, retryable_failure_types: set[str],
    immediate_open_failure_types: set[str], minimum_history_bars: int,
    history_buffer_bars: int, maximum_history_pages: int,
    no_progress_page_limit: int,
) -> dict[str, Any]:
    from kiwoom import get_auth, get_client

    commit = _runtime_commit(runtime)
    auth = get_auth(mode="real", token_store_kind="memory")
    token_received = bool(auth.refresh_access_token())
    client = get_client(auth=auth)
    last_request = 0.0

    def pacer() -> None:
        nonlocal last_request
        wait = minimum_interval_seconds - (time.monotonic() - last_request)
        if wait > 0:
            time.sleep(wait)
        last_request = time.monotonic()

    return {
        "commit": commit, "auth": auth, "client": client, "token_received": token_received,
        "pacer": pacer, "stock_universe": None, "etf_universe": None,
        "maximum_attempts": max(1, maximum_attempts),
        "retry_backoff_seconds": max(0.0, retry_backoff_seconds),
        "retryable_failure_types": retryable_failure_types,
        "immediate_open_failure_types": immediate_open_failure_types,
        "minimum_history_bars": max(1, minimum_history_bars),
        "history_buffer_bars": max(0, history_buffer_bars),
        "maximum_history_pages": max(1, maximum_history_pages),
        "no_progress_page_limit": max(1, no_progress_page_limit),
    }


def _worker_result(request: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    commit = session["commit"]
    operation = request["operation"]
    if operation == "oauth_health":
        return {
            "bridge_status": "PASS" if session["token_received"] else "API_UNAVAILABLE",
            "operation": operation,
            "authenticated": bool(session["token_received"]),
            "runtime_commit": commit,
            "retrieved_at": utc_now(),
            "order_authority": False,
        }
    ticker = str(request["ticker"])
    pagination: dict[str, Any] | None = None
    if operation == "exchange_lookup":
        body = _request(session, *RUNTIME_APIS[operation], {"stk_cd": ticker})
        data = _exact_rows(_safe_universe(body, "list", SAFE_IDENTITY_FIELDS), ticker, "stk_cd")
    elif operation == "stock_list":
        data = _exact_rows(_stock_universe(session), ticker, "stk_cd")
    elif operation == "etf_etn_list":
        data = _exact_rows(_etf_universe(session), ticker, "code")
    else:
        resolution = _resolve_identity(session, ticker)
        if resolution["status"] != "VERIFIED":
            return {
                "bridge_status": resolution["status"], "operation": operation,
                "ticker": ticker, "data": resolution.get("candidates", []),
                "runtime_commit": commit, "retrieved_at": utc_now(),
                "order_authority": False,
            }
        identity = resolution["identity"]
        stex_tp = str(identity["stex_tp"])
        if operation == "stock_lookup":
            body = _request(session, *RUNTIME_APIS[operation], {"stex_tp": stex_tp, "stk_cd": ticker})
            data = [{field: body.get(field) for field in SAFE_IDENTITY_FIELDS}]
        elif operation == "daily_chart":
            basis = request["price_basis"]
            data, pagination = _daily_chart_pages(
                session, ticker=ticker, stex_tp=stex_tp,
                completed_session=str(request["completed_session"]), price_basis=str(basis),
            )
        elif operation == "market_quote":
            body = _request(
                session, *RUNTIME_APIS[operation],
                {"stex_tp": stex_tp, "stk_cd": ticker},
            )
            data = [{field: body.get(field) for field in SAFE_QUOTE_FIELDS}]
        else:
            raise BridgeError("OPERATION_NOT_ALLOWLISTED")
    result = {
        "bridge_status": "PASS",
        "operation": operation,
        "ticker": ticker,
        "data": data,
        "runtime_commit": commit,
        "retrieved_at": utc_now(),
        "order_authority": False,
    }
    if pagination is not None:
        result["pagination"] = pagination
    return result


def external_worker(
    stdin_text: str, runtime: Path, minimum_interval_seconds: float = 0.25,
    maximum_attempts: int = 1, retry_backoff_seconds: float = 1.0,
    retryable_failure_types: set[str] | None = None,
    immediate_open_failure_types: set[str] | None = None,
    minimum_history_bars: int = 252,
    history_buffer_bars: int = 32,
    maximum_history_pages: int = 10,
    no_progress_page_limit: int = 1,
) -> dict[str, Any]:
    try:
        raw = json.loads(stdin_text)
        is_batch = isinstance(raw, list)
        requests = [validate_bridge_request(item) for item in raw] if is_batch else [validate_bridge_request(raw)]
        _load_env_without_echo(runtime / ".env")
        session = _runtime_session(
            runtime, minimum_interval_seconds, maximum_attempts, retry_backoff_seconds,
            retryable_failure_types or {"TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH"},
            immediate_open_failure_types or {"HTTP_429", "AUTHENTICATION_FAILURE"},
            minimum_history_bars, history_buffer_bars, maximum_history_pages,
            no_progress_page_limit,
        )
        results: list[dict[str, Any]] = []
        for request in requests:
            try:
                results.append(_worker_result(request, session))
            except BridgeError as exc:
                results.append({
                    "bridge_status": exc.status, "failure_type": exc.failure_type,
                    "operation": request["operation"], "ticker": request.get("ticker"),
                    "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                    "order_authority": False,
                })
            except Exception as exc:
                failure = _exception_failure(exc)
                results.append({
                    "bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": failure,
                    "exception_type": type(exc).__name__, "operation": request["operation"],
                    "ticker": request.get("ticker"), "runtime_commit": session["commit"],
                    "retrieved_at": utc_now(), "order_authority": False,
                })
                if failure in {"HTTP_429", "AUTHENTICATION_FAILURE"}:
                    remaining = len(requests) - len(results)
                    results.extend({
                        "bridge_status": "KIWOOM_CIRCUIT_OPEN", "failure_type": failure,
                        "operation": pending["operation"], "ticker": pending.get("ticker"),
                        "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                        "order_authority": False,
                    } for pending in requests[-remaining:] if remaining)
                    break
        if is_batch:
            return {
                "bridge_status": "PASS", "bridge_batch": True, "results": results,
                "runtime_commit": session["commit"], "retrieved_at": utc_now(),
                "order_authority": False,
            }
        return results[0]
    except BridgeError as exc:
        return {
            "bridge_status": exc.status,
            "failure_type": exc.failure_type,
            "retrieved_at": utc_now(),
            "order_authority": False,
        }
    except Exception as exc:
        failure = _exception_failure(exc)
        return {
            "bridge_status": "KIWOOM_API_UNAVAILABLE",
            "failure_type": failure,
            "exception_type": type(exc).__name__,
            "retrieved_at": utc_now(),
            "order_authority": False,
        }


def _parse_last_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise BridgeError("BRIDGE_OUTPUT_INVALID")


def sanitize_bridge_response(value: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    operation = request["operation"]
    safe: dict[str, Any] = {
        "bridge_status": str(value.get("bridge_status", "BRIDGE_OUTPUT_INVALID")),
        "operation": operation,
        "ticker": request.get("ticker"),
        "runtime_commit": value.get("runtime_commit") if isinstance(value.get("runtime_commit"), str) else None,
        "retrieved_at": value.get("retrieved_at") if isinstance(value.get("retrieved_at"), str) else None,
        "order_authority": False,
    }
    if isinstance(value.get("failure_type"), str):
        safe["failure_type"] = value["failure_type"]
    if isinstance(value.get("exception_type"), str):
        safe["exception_type"] = value["exception_type"]
    if operation == "oauth_health":
        safe["authenticated"] = value.get("authenticated") is True
        return safe
    fields = (
        SAFE_CHART_FIELDS if operation == "daily_chart"
        else SAFE_QUOTE_FIELDS if operation == "market_quote"
        else SAFE_ETF_FIELDS if operation == "etf_etn_list"
        else SAFE_IDENTITY_FIELDS
    )
    data = value.get("data")
    safe["data"] = [
        {field: row.get(field) for field in fields}
        for row in data if isinstance(row, dict)
    ] if isinstance(data, list) else []
    if operation == "daily_chart" and isinstance(value.get("pagination"), dict):
        pagination = value["pagination"]
        pages = pagination.get("pages") if isinstance(pagination.get("pages"), list) else []
        safe["pagination"] = {
            key: pagination.get(key)
            for key in (
                "api_id", "minimum_history_bars", "target_history_bars", "maximum_pages",
                "pages_fetched", "distinct_session_count", "provider_exhausted", "status",
            )
        }
        safe["pagination"]["pages"] = [
            {key: page.get(key) for key in (
                "page_index", "api_id", "row_count", "first_session", "last_session",
                "continuation_state_hash", "retrieved_at",
            )}
            for page in pages if isinstance(page, dict)
        ]
    return safe


def _history_cli_args(policy: dict[str, Any]) -> list[str]:
    history = policy.get("history_policy") or {}
    return [
        "--minimum-history-bars", str(history.get("minimum_history_bars", 252)),
        "--history-buffer-bars", str(history.get("replay_history_buffer_bars", 32)),
        "--maximum-history-pages", str(history.get("maximum_pages", 10)),
        "--no-progress-page-limit", str(history.get("no_progress_page_limit", 1)),
    ]


def invoke_bridge(
    request: dict[str, Any], *, runtime: Path, policy: dict[str, Any],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    sanitized = validate_bridge_request(request)
    python_path = runtime / str(policy["external_python_relative_path"])
    if not python_path.is_file():
        return {"bridge_status": "RUNTIME_PYTHON_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE", "order_authority": False}
    attempts = int(policy["maximum_attempts"])
    timeout = int(policy["request_timeout_seconds"])
    delays = list(policy.get("retry_backoff_seconds", []))
    last: dict[str, Any] = {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE", "order_authority": False}
    for attempt in range(attempts):
        try:
            completed = runner(
                [str(python_path), str(Path(__file__).resolve()), "--external-worker",
                 "--minimum-request-interval", str(policy.get("minimum_request_interval_seconds", 0.25)),
                 "--maximum-attempts", "1",
                 "--retry-backoff-seconds", str((policy.get("retry_backoff_seconds") or [1.0])[0]),
                 "--retryable-failure-types", ",".join(policy.get("retryable_failure_types", [])),
                 "--immediate-open-failure-types", ",".join(policy.get("immediate_open_failure_types", [])),
                 *_history_cli_args(policy)],
                input=json.dumps(sanitized, separators=(",", ":")),
                cwd=str(runtime), capture_output=True, text=True, encoding="utf-8",
                timeout=timeout, check=False,
            )
            last = sanitize_bridge_response(_parse_last_json(completed.stdout), sanitized)
        except subprocess.TimeoutExpired:
            last = {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "TIMEOUT", "order_authority": False}
        except (OSError, BridgeError):
            last = {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE", "order_authority": False}
        if last.get("bridge_status") == "PASS" or last.get("bridge_status") in {"NOT_FOUND", "AMBIGUOUS", "IDENTITY_MISMATCH", "KIWOOM_ORDER_ENDPOINT_BLOCKED"}:
            return last
        if last.get("failure_type") in {"HTTP_429", "AUTHENTICATION_FAILURE"}:
            return last
        if attempt + 1 < attempts:
            sleeper(float(delays[min(attempt, len(delays) - 1)]) if delays else 1.0)
    return last


def invoke_bridge_batch(
    requests: list[dict[str, Any]], *, runtime: Path, policy: dict[str, Any],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[dict[str, Any]]:
    sanitized = [validate_bridge_request(item) for item in requests]
    python_path = runtime / str(policy["external_python_relative_path"])
    if not python_path.is_file():
        return [
            {"bridge_status": "RUNTIME_PYTHON_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE", "operation": item["operation"], "ticker": item.get("ticker"), "order_authority": False}
            for item in sanitized
        ]
    try:
        completed = runner(
            [str(python_path), str(Path(__file__).resolve()), "--external-worker",
             "--minimum-request-interval", str(policy.get("minimum_request_interval_seconds", 0.25)),
             "--maximum-attempts", str(policy.get("maximum_attempts", 1)),
             "--retry-backoff-seconds", str((policy.get("retry_backoff_seconds") or [1.0])[0]),
             "--retryable-failure-types", ",".join(policy.get("retryable_failure_types", [])),
             "--immediate-open-failure-types", ",".join(policy.get("immediate_open_failure_types", [])),
             *_history_cli_args(policy)],
            input=json.dumps(sanitized, separators=(",", ":")), cwd=str(runtime),
            capture_output=True, text=True, encoding="utf-8",
            timeout=int(policy["request_timeout_seconds"]) * max(1, len(sanitized)), check=False,
        )
        payload = _parse_last_json(completed.stdout)
        raw_results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(raw_results, list) or len(raw_results) != len(sanitized):
            raise BridgeError("BRIDGE_BATCH_OUTPUT_INVALID")
        return [sanitize_bridge_response(value if isinstance(value, dict) else {}, request) for value, request in zip(raw_results, sanitized)]
    except (OSError, subprocess.TimeoutExpired, BridgeError):
        return [
            {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "TIMEOUT", "operation": item["operation"], "ticker": item.get("ticker"), "order_authority": False}
            for item in sanitized
        ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-worker", action="store_true")
    parser.add_argument("--minimum-request-interval", type=float, default=0.25)
    parser.add_argument("--maximum-attempts", type=int, default=1)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.0)
    parser.add_argument("--retryable-failure-types", default="TIMEOUT,EMPTY_RESPONSE,SCHEMA_MISMATCH")
    parser.add_argument("--immediate-open-failure-types", default="HTTP_429,AUTHENTICATION_FAILURE")
    parser.add_argument("--minimum-history-bars", type=int, default=252)
    parser.add_argument("--history-buffer-bars", type=int, default=32)
    parser.add_argument("--maximum-history-pages", type=int, default=10)
    parser.add_argument("--no-progress-page-limit", type=int, default=1)
    args = parser.parse_args()
    if not args.external_worker:
        raise SystemExit("external worker mode is required")
    result = external_worker(
        sys.stdin.read(), Path.cwd(), max(0.0, args.minimum_request_interval),
        max(1, args.maximum_attempts), max(0.0, args.retry_backoff_seconds),
        {item for item in args.retryable_failure_types.split(",") if item},
        {item for item in args.immediate_open_failure_types.split(",") if item},
        max(1, args.minimum_history_bars), max(0, args.history_buffer_bars),
        max(1, args.maximum_history_pages), max(1, args.no_progress_page_limit),
    )
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("bridge_status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
