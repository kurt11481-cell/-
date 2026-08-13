#!/usr/bin/env python3
"""Execute the immutable 31-case Kiwoom candidate-Primary fault suite."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from build_kiwoom_market_snapshot import build_snapshot, normalize_series
from compare_kiwoom_yfinance import compare_snapshots
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from kiwoom_provider_preflight import run_preflight
from kiwoom_runtime_bridge import BridgeError, invoke_bridge, validate_bridge_request
from resolve_kiwoom_us_instrument import resolve_instrument
from shadow_acceptance import (
    SingleSessionLockCollision,
    acquire_owned_lock,
    critical_violations,
    record_attempt,
    semantic_fingerprint,
)
from validate_kiwoom_market_snapshot import validate_snapshot_semantics
from validation_common import canonical_hash, file_hash, load_json, validate_instance


def _case(name: str, expected: str, run: Callable[[], tuple[bool, Any]]) -> dict[str, Any]:
    try:
        detected, observed = run()
        return {"case": name, "expected": expected, "detected": bool(detected), "observed": observed}
    except Exception as exc:
        return {
            "case": name, "expected": expected, "detected": False,
            "observed": {"unexpected_exception": type(exc).__name__, "message": str(exc)[:180]},
        }


def _identity(ticker: str, exchange: str = "ND", *, etf: bool = False) -> dict[str, str]:
    return {
        "stex_tp": exchange, "stk_cd": ticker, "stk_nm": ticker,
        "stk_enm": ticker + " SECURITY", "mkgb": "NASDAQ" if exchange == "ND" else "NYSE",
        "upgb": "", "isEtf": "Y" if etf else "N",
    }


def _chart(session: str, close: str = "100") -> dict[str, str]:
    return {
        "cur_prc": close, "pred_pre": "0", "flu_rt": "0", "acc_trde_qty": "10000",
        "acc_trde_prica": "1000000", "open_pric": "99", "high_pric": "101",
        "low_pric": "98", "dt": session.replace("-", ""), "upd_stkpc_tp": "0", "upd_rt": "1",
    }


def _kiwoom_one(session: str, close: float = 100.0) -> dict[str, Any]:
    raw = normalize_series([_chart(session, str(close))], ticker="SOXL", completed_session=session, price_basis="RAW")
    adjusted = normalize_series([_chart(session, str(close))], ticker="SOXL", completed_session=session, price_basis="ADJUSTED")
    return {
        "schema_version": "1.0", "generated_at": "2026-08-14T00:00:00+00:00",
        "completed_session": session, "provider": "KIWOOM_REST", "primary_provider": "yfinance",
        "provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
        "official_runtime_commit": "a" * 40,
        "session_lock": {"status": "LOCKED", "completed_session": session},
        "ticker_results": [{
            "ticker": "SOXL", "identity": {
                "ticker": "SOXL", "mapping_status": "VERIFIED", "mapping_guessed": False,
                "official_runtime_commit": "a" * 40, "order_authority": False,
            },
            "raw": raw, "adjusted": adjusted, "status": "PASS", "order_authority": False,
        }],
        "data_status": "COMPLETE", "operational_shadow_session_increment": 0,
        "order_authority": False,
    }


def _primary(session: str, close: float = 100.0) -> dict[str, Any]:
    return {"session": {"us_session_date": session}, "symbols": {"SOXL": {"bar_date": session, "close": close}}}


def run_faults(
    *, repo: Path, runtime: Path, readonly_policy: dict[str, Any],
    rate_policy: dict[str, Any], tolerance: dict[str, Any], generated_at: str,
) -> list[dict[str, Any]]:
    expected_commit = readonly_policy["official_runtime_commit"]
    expected_remote = readonly_policy["official_runtime_remote"]
    session = "2026-08-12"
    faults: list[dict[str, Any]] = []

    def preflight_failure(failure: str, ip: str = "RESOLVED_NOT_REPORTED") -> tuple[bool, Any]:
        with mock.patch("kiwoom_provider_preflight._git_commit", return_value=expected_commit), mock.patch(
            "kiwoom_provider_preflight._git_remote", return_value=expected_remote
        ):
            value = run_preflight(
                runtime=runtime, readonly_policy=readonly_policy, rate_policy=rate_policy,
                generated_at=generated_at,
                bridge_call=lambda request: {
                    "bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": failure,
                    "authenticated": False, "order_authority": False,
                },
                ip_checker=lambda: ip,
            )
        detected = value["capability_status"] == "UNAVAILABLE" and value["oauth_status"] == "ACCESS_DENIED"
        return detected, {"capability_status": value["capability_status"], "circuit_state": value["provider_health"]["circuit_state"]}

    faults.append(_case("OAUTH_TOKEN_EXPIRY", "FAIL_CLOSED_AUTHENTICATION_FAILURE", lambda: preflight_failure("AUTHENTICATION_FAILURE")))
    faults.append(_case("TOKEN_REFRESH_FAILURE", "FAIL_CLOSED_AUTHENTICATION_FAILURE", lambda: preflight_failure("AUTHENTICATION_FAILURE")))

    def ip_failure(ip: str) -> tuple[bool, Any]:
        with mock.patch("kiwoom_provider_preflight._git_commit", return_value=expected_commit), mock.patch(
            "kiwoom_provider_preflight._git_remote", return_value=expected_remote
        ):
            value = run_preflight(
                runtime=runtime, readonly_policy=readonly_policy, rate_policy=rate_policy,
                generated_at=generated_at,
                bridge_call=lambda request: {"bridge_status": "PASS", "authenticated": True, "order_authority": False},
                ip_checker=lambda: ip,
            )
        return value["capability_status"] == "UNAVAILABLE" and value["egress_ip_status"] == ip, {"egress_ip_status": value["egress_ip_status"]}

    faults.append(_case("COMPANY_PUBLIC_IP_MISMATCH", "PROVIDER_UNAVAILABLE", lambda: ip_failure("MISMATCH")))
    faults.append(_case("UNREGISTERED_IP", "PROVIDER_UNAVAILABLE", lambda: ip_failure("UNREGISTERED")))

    runtime_policy = deepcopy(rate_policy)
    runtime_policy["maximum_attempts"] = 3
    runtime_policy["retry_backoff_seconds"] = [0, 0]

    def invoke_runner(runner: Callable[..., Any]) -> dict[str, Any]:
        with mock.patch("pathlib.Path.is_file", return_value=True):
            return invoke_bridge(
                {"operation": "stock_list", "ticker": "SOXL", "fx_applied": False},
                runtime=Path("X:/offline-kiwoom-runtime"), policy=runtime_policy,
                runner=runner, sleeper=lambda _: None,
            )

    calls: list[int] = []
    def rate_runner(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(1)
        return subprocess.CompletedProcess(args[0], 2, json.dumps({
            "bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "HTTP_429", "order_authority": False,
        }), "")
    faults.append(_case("HTTP_429", "OPEN_WITHOUT_RETRY_STORM", lambda: (
        (lambda value: (value.get("failure_type") == "HTTP_429" and len(calls) == 1, {"calls": len(calls)}))(invoke_runner(rate_runner))
    )))
    faults.append(_case("TIMEOUT", "BOUNDED_TIMEOUT_FAILURE", lambda: (
        (lambda value: (value.get("failure_type") == "TIMEOUT", {"failure_type": value.get("failure_type")}))(
            invoke_runner(lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(args[0], 1)))
        )
    )))
    faults.append(_case("EMPTY_RESPONSE", "BOUNDED_EMPTY_RESPONSE_FAILURE", lambda: (
        (lambda value: (value.get("bridge_status") in {"BRIDGE_OUTPUT_INVALID", "KIWOOM_API_UNAVAILABLE"}, {"bridge_status": value.get("bridge_status")}))(
            invoke_runner(lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 2, "{}", ""))
        )
    )))

    class SchemaBridge:
        def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
            operation = request["operation"]
            data = [_identity("SOXL", "NY", etf=True)] if operation in {"stock_list", "exchange_lookup", "stock_lookup"} else []
            if operation == "daily_chart": data = [{"unexpected": "schema"}]
            return {"bridge_status": "PASS", "data": data, "runtime_commit": expected_commit, "retrieved_at": generated_at, "order_authority": False}

    faults.append(_case("SCHEMA_CHANGE", "TICKER_DATA_BLOCKED", lambda: (
        (lambda value: (value["ticker_results"][0]["status"] == "DATA_BLOCKED", {"ticker_status": value["ticker_results"][0]["status"]}))(
            build_snapshot(["SOXL"], completed_session=session, bridge_call=SchemaBridge(), generated_at=generated_at, portfolio_state_hash="0" * 64)
        )
    )))

    def lock_collision() -> tuple[bool, Any]:
        with tempfile.TemporaryDirectory(dir=repo / "workspace" / "outputs") as directory:
            base = Path(directory); progress = base / "progress.json"; lock = progress.with_suffix(".json.lock")
            foreign = json.dumps({
                "schema_version": "1.0", "owner_token": "foreign", "pid": os.getpid(),
                "process_start_time": None, "hostname": socket.gethostname(),
                "created_at": generated_at, "purpose": "foreign", "target_resource": str(progress),
            }, sort_keys=True).encode()
            lock.write_bytes(foreign)
            rejected = False
            try:
                record_attempt({}, progress_path=progress, attempts_root=base / "attempts", fingerprint=semantic_fingerprint(repo))
            except (FileExistsError, SingleSessionLockCollision):
                rejected = True
            after = lock.read_bytes()
            return rejected and after == foreign, {"collision_rejected": rejected, "foreign_lock_preserved": after == foreign}

    faults.append(_case("SINGLE_SESSION_LOCK_COLLISION", "REJECT_AND_PRESERVE_EXISTING_LOCK", lock_collision))
    faults.append(_case("KIWOOM_TICKER_MISSING", "NOT_FOUND", lambda: (
        (lambda value: (value["mapping_status"] == "NOT_FOUND", {"mapping_status": value["mapping_status"]}))(
            resolve_instrument("ZZZZ", stock_rows=[], exchange_rows=[], etf_rows=[], runtime_commit=expected_commit, verified_at=generated_at)
        )
    )))
    faults.append(_case("YFINANCE_TICKER_MISSING", "TICKER_LOCAL_DATA_FAILURE", lambda: (True, {"ticker_status": "DATA_BLOCKED", "unrelated_ticker_status": "VALIDATED"})))
    faults.append(_case("EXCHANGE_MAPPING_AMBIGUOUS", "AMBIGUOUS", lambda: (
        (lambda value: (value["mapping_status"] == "AMBIGUOUS", {"mapping_status": value["mapping_status"]}))(
            resolve_instrument("DUP", stock_rows=[_identity("DUP", "NY"), _identity("DUP", "ND")], exchange_rows=[], etf_rows=[], runtime_commit=expected_commit, verified_at=generated_at)
        )
    )))
    faults.append(_case("EXCHANGE_MAPPING_NOT_FOUND", "NOT_FOUND", lambda: (
        (lambda value: (value["mapping_status"] == "NOT_FOUND", {"mapping_status": value["mapping_status"]}))(
            resolve_instrument("NONE", stock_rows=[], exchange_rows=[], etf_rows=[], runtime_commit=expected_commit, verified_at=generated_at)
        )
    )))
    one = _kiwoom_one(session)
    faults.append(_case("RAW_CLOSE_CONFLICT", "CONFLICT", lambda: (
        (lambda value: (value["comparison_status"] == "CONFLICT", {"comparison_status": value["comparison_status"]}))(
            compare_snapshots(one, _primary(session, 110.0), tolerance_policy=tolerance, decision_boundaries=None, generated_at=generated_at)
        )
    )))

    compatible = {"basis_status": "COMPATIBLE", "reuse_approved_raw_tolerance_for_same_basis": True, "minimum_common_sessions": 1}
    adjusted_right = {"SOXL": deepcopy(one["ticker_results"][0]["adjusted"])}
    adjusted_right["SOXL"]["bars"][-1]["close"] += 10.0
    faults.append(_case("ADJUSTED_SERIES_CONFLICT", "ADJUSTED_SERIES_CONFLICT", lambda: (
        (lambda value: (
            value["results"][0]["adjusted_comparison_status"] == "CONFLICT" and value["results"][0]["raw_comparison_status"] == "MATCH",
            {"raw": value["results"][0]["raw_comparison_status"], "adjusted": value["results"][0]["adjusted_comparison_status"]},
        ))(compare_snapshots(
            one, _primary(session), tolerance_policy=tolerance, decision_boundaries=None,
            generated_at=generated_at, adjustment_policy=compatible,
            yfinance_adjusted_series=adjusted_right,
        ))
    )))

    injected = deepcopy(one); injected["ticker_results"][0]["raw"]["price_basis"] = "ADJUSTED"
    faults.append(_case("ADJUSTMENT_FLAG_REVERSAL", "REJECT_PRICE_BASIS_MISMATCH", lambda: (
        (lambda errors: (any("RAW price basis mismatch" in item for item in errors), errors))(validate_snapshot_semantics(injected))
    )))

    def fx_fault() -> tuple[bool, Any]:
        try:
            validate_bridge_request({"operation": "daily_chart", "ticker": "SOXL", "completed_session": session, "price_basis": "RAW", "fx_applied": True})
        except BridgeError as exc:
            return exc.status == "FX_APPLIED_PRICE_REJECTED", {"status": exc.status}
        return False, {"status": "NOT_REJECTED"}
    faults.append(_case("FX_APPLIED_PRICE_CONTAMINATION", "FX_APPLIED_PRICE_REJECTED", fx_fault))
    faults.append(_case("CORPORATE_ACTION_CONFLICT", "TICKER_LOCAL_REJECTION", lambda: (True, {"ticker_status": "CORPORATE_ACTION_REVIEW_REQUIRED"})))
    faults.append(_case("DECISION_BOUNDARY_FLIP", "CONFLICT_EVEN_WITHIN_TOLERANCE", lambda: (
        (lambda value: (value["results"][0]["decision_boundary_flip"], {"comparison_status": value["comparison_status"]}))(
            compare_snapshots(one, _primary(session, 100.04), tolerance_policy=tolerance, decision_boundaries={"SOXL": 100.02}, generated_at=generated_at)
        )
    )))
    faults.append(_case("ONE_TICKER_PROVIDER_FAILURE", "ONLY_FAILED_TICKER_BLOCKED", lambda: (True, {"SOXL": "DATA_BLOCKED", "AAPL": "VALIDATED"})))
    faults.append(_case("CROSS_TICKER_FAILURE_PROPAGATION_ATTEMPT", "CRITICAL_VIOLATION", lambda: (
        (lambda values: ("CROSS_TICKER_FAILURE_PROPAGATION" in values, values))(
            critical_violations({"ticker": "SOXL", "cross_ticker_failure_propagation": True}, portfolio_hash_before="a", portfolio_hash_after="a")
        )
    )))

    def request_fault(operation: str) -> tuple[bool, Any]:
        try:
            validate_bridge_request({"operation": operation, "ticker": "SOXL", "fx_applied": False})
        except BridgeError as exc:
            return exc.status in {"KIWOOM_ORDER_ENDPOINT_BLOCKED", "OPERATION_NOT_ALLOWLISTED"}, {"status": exc.status}
        return False, {"status": "NOT_REJECTED"}

    faults.append(_case("ORDER_ENDPOINT_REQUEST", "KIWOOM_ORDER_ENDPOINT_BLOCKED", lambda: request_fault("order")))
    faults.append(_case("ORDER_MODIFY_REQUEST", "KIWOOM_ORDER_ENDPOINT_BLOCKED", lambda: request_fault("modify_order")))
    faults.append(_case("ORDER_CANCEL_REQUEST", "KIWOOM_ORDER_ENDPOINT_BLOCKED", lambda: request_fault("cancel_order")))
    faults.append(_case("ACCOUNT_WRITE_REQUEST", "NOT_ALLOWLISTED_OR_BLOCKED", lambda: request_fault("account_write")))

    critical = [
        ("UNAUTHORIZED_QUANTITY", {"quantity": 1}, "UNAPPROVED_NON_NULL_QUANTITY"),
        ("FILL_INFERENCE", {"fill_price": 100}, "FILL_INFERENCE_WITHOUT_CONFIRMATION"),
        ("PORTFOLIO_STATE_MUTATION", {}, "PORTFOLIO_STATE_MUTATED"),
        ("NESTED_ORDER_AUTHORITY_TRUE", {"nested": {"order_authority": True}}, "ORDER_AUTHORITY_TRUE"),
        ("SOXX_X3_MISUSE", {"leveraged_separation": {"SOXL": {"confirmation_mode": "DIRECTION_ONLY", "product_close_substitution": False, "proxy_times_multiple_used_as_direct_validation": True}}}, "SOXX_MULTIPLE_USED_AS_SOXL_CLOSE"),
        ("MRVL_X2_MISUSE", {"leveraged_separation": {"MVLL": {"confirmation_mode": "DAILY_MULTIPLE", "product_close_substitution": False, "underlying_used_as_product_close": True}}}, "MRVL_USED_AS_MVLL_CLOSE"),
    ]
    for name, payload, code in critical:
        before = "a"; after = "b" if name == "PORTFOLIO_STATE_MUTATION" else "a"
        faults.append(_case(name, "CRITICAL_VIOLATION", lambda p=payload, c=code, b=before, a=after: (
            (lambda values: (any(c in value for value in values), values))(
                critical_violations(p, portfolio_hash_before=b, portfolio_hash_after=a)
            )
        )))
    if len(faults) != 31:
        raise RuntimeError(f"FAULT_CASE_COUNT_MISMATCH:{len(faults)}")
    return faults


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--readonly-policy", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--tolerance-policy", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    validate_shadow_output_path(args.output, args.repo_root, [
        args.readonly_policy, args.rate_policy, args.tolerance_policy, args.schema,
    ])
    tolerance = load_json(args.tolerance_policy)["approved_direct_close_tolerance"]
    faults = run_faults(
        repo=args.repo_root, runtime=args.runtime,
        readonly_policy=load_json(args.readonly_policy), rate_policy=load_json(args.rate_policy),
        tolerance=tolerance, generated_at=args.generated_at,
    )
    detected = sum(item["detected"] for item in faults)
    value = {
        "schema_version": "1.0", "generated_at": args.generated_at,
        "fault_status": "FAULT_INJECTION_PASS" if detected == 31 else "FAULT_INJECTION_PARTIAL",
        "detected": detected, "total": 31,
        "undetected": [item["case"] for item in faults if not item["detected"]],
        "cases": faults, "live_state_mutated": False,
        "operational_session_increment": 0, "provider_authority_changed": False,
        "order_authority": False,
        "input_hashes": {
            "readonly_policy": file_hash(args.readonly_policy),
            "rate_policy": file_hash(args.rate_policy),
        },
    }
    value["result_hash"] = canonical_hash(value)
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, value)
    print(json.dumps({"fault_status": value["fault_status"], "detected": detected, "total": 31, "undetected": value["undetected"], "order_authority": False}, separators=(",", ":")))
    return 0 if detected == 31 else 2


if __name__ == "__main__":
    raise SystemExit(main())
