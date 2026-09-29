#!/usr/bin/env python3
"""Offline regression tests for the Kiwoom read-only shadow adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = SKILL_ROOT / "scripts"
SCHEMAS = SKILL_ROOT / "schemas"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_kiwoom_market_snapshot import build_preflight_blocked_snapshot, build_snapshot, build_snapshot_with_batch, normalize_series
from compare_kiwoom_yfinance import compare_snapshots
from kiwoom_account_readonly_bridge import invoke_account_bridge_batch
from kiwoom_provider_preflight import run_preflight
from kiwoom_adapter_io import validate_shadow_output_path
from kiwoom_runtime_bridge import _request, blocked_api_target, invoke_bridge, invoke_bridge_batch, validate_bridge_request
from resolve_kiwoom_us_instrument import resolve_instrument
from validation_common import validate_instance
from validate_kiwoom_market_snapshot import validate_snapshot_semantics
from validate_source_capabilities import validate_registry


COMMIT = "6" * 40
NOW = "2026-08-13T12:00:00+00:00"
SESSION = "2026-08-12"


def identity(ticker: str, exchange: str = "ND", etf: str = "N") -> dict[str, str]:
    return {
        "stex_tp": exchange, "stk_cd": ticker, "stk_nm": ticker,
        "stk_enm": ticker + " SECURITY", "mkgb": "NASDAQ" if exchange == "ND" else "NYSE",
        "upgb": "", "isEtf": etf,
    }


def chart_row(close: str = "100.0000") -> dict[str, str]:
    return {
        "cur_prc": close, "pred_pre": "0", "flu_rt": "0", "acc_trde_qty": "10000",
        "acc_trde_prica": "1000000", "open_pric": "99.0000", "high_pric": "101.0000",
        "low_pric": "98.0000", "dt": "20260812", "upd_stkpc_tp": "0", "upd_rt": "1",
    }


class FakeBridge:
    def __init__(self, failed: set[str] | None = None) -> None:
        self.failed = failed or set()

    def __call__(self, request: dict[str, object]) -> dict[str, object]:
        ticker = str(request.get("ticker") or "")
        operation = str(request["operation"])
        if ticker in self.failed:
            return {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE", "data": [], "order_authority": False}
        exchange = "NY" if ticker == "SOXL" else "ND"
        etf = "Y" if ticker == "SOXL" else "N"
        data: list[dict[str, str]]
        if operation in {"stock_list", "exchange_lookup", "stock_lookup"}:
            data = [identity(ticker, exchange, etf)]
        elif operation == "etf_etn_list":
            data = [{"stex_tp": exchange, "code": ticker, "cate1": "ETF", "cate2": "", "etn": "N", "mkgb": "", "upnm": ""}] if etf == "Y" else []
        elif operation == "daily_chart":
            data = [chart_row("100.0000" if request.get("price_basis") == "RAW" else "99.0000")]
        else:
            data = []
        return {
            "bridge_status": "PASS", "operation": operation, "ticker": ticker,
            "data": data, "runtime_commit": COMMIT, "retrieved_at": NOW,
            "order_authority": False,
        }


class KiwoomAdapterTests(unittest.TestCase):
    def _market_batch_stdout(self, stdout: str) -> dict:
        runtime = Path("X:/offline-kiwoom-runtime")
        runner = lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout, "")
        with mock.patch("pathlib.Path.is_file", return_value=True):
            return invoke_bridge_batch(
                [{"operation": "stock_list", "ticker": "SOXL", "fx_applied": False}],
                runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )[0]

    def _account_batch_stdout(self, stdout: str) -> dict:
        runtime = Path("X:/offline-kiwoom-runtime")
        runner = lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout, "")
        with mock.patch("pathlib.Path.is_file", return_value=True):
            return invoke_account_bridge_batch(
                [{"operation": "account_holdings_read"}], runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )[0]

    def test_soxl_mapping_comes_from_kiwoom_stock_evidence(self) -> None:
        result = resolve_instrument(
            "SOXL", stock_rows=[identity("SOXL", "NY", "Y")], exchange_rows=[],
            etf_rows=[{"stex_tp": "NY", "code": "SOXL"}], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "VERIFIED")
        self.assertEqual(result["stex_tp"], "NY")
        self.assertEqual(result["source_api_id"], "usa10099")
        self.assertFalse(result["mapping_guessed"])

    def assert_simple_stock_mapping(self, ticker: str, exchange: str) -> None:
        result = resolve_instrument(
            ticker, stock_rows=[identity(ticker, exchange)], exchange_rows=[],
            etf_rows=[], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "VERIFIED")
        self.assertEqual(result["ticker"], ticker)
        self.assertEqual(result["stex_tp"], exchange)
        self.assertFalse(result["mapping_guessed"])

    def test_pgr_simple_one_to_one_mapping(self) -> None:
        self.assert_simple_stock_mapping("PGR", "NY")

    def test_jpm_simple_one_to_one_mapping(self) -> None:
        self.assert_simple_stock_mapping("JPM", "NY")

    def test_cme_simple_one_to_one_mapping(self) -> None:
        self.assert_simple_stock_mapping("CME", "ND")

    def test_v_simple_one_to_one_mapping(self) -> None:
        self.assert_simple_stock_mapping("V", "NY")

    def test_existing_mvll_nbis_and_soxl_mappings_are_unchanged(self) -> None:
        for ticker, exchange, is_etf in (
            ("MVLL", "ND", False),
            ("NBIS", "ND", False),
            ("SOXL", "NY", True),
        ):
            with self.subTest(ticker=ticker):
                result = resolve_instrument(
                    ticker,
                    stock_rows=[identity(ticker, exchange, "Y" if is_etf else "N")],
                    exchange_rows=[],
                    etf_rows=[{"stex_tp": exchange, "code": ticker}] if is_etf else [],
                    runtime_commit=COMMIT,
                    verified_at=NOW,
                )
                self.assertEqual(result["mapping_status"], "VERIFIED")
                self.assertEqual(result["stex_tp"], exchange)

    def test_brk_b_special_mapping_remains_unsupported(self) -> None:
        result = resolve_instrument(
            "BRK.B", stock_rows=[identity("BRKb", "NY")], exchange_rows=[],
            etf_rows=[], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "NOT_FOUND")
        self.assertIsNone(result["stex_tp"])

    def test_brkb_does_not_silently_become_canonical_brk_b(self) -> None:
        result = resolve_instrument(
            "BRKb", stock_rows=[identity("BRKb", "NY")], exchange_rows=[],
            etf_rows=[], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "VERIFIED")
        self.assertEqual(result["ticker"], "BRKB")
        self.assertNotEqual(result["ticker"], "BRK.B")

    def test_cost_remains_unresolved_without_authorized_evidence(self) -> None:
        result = resolve_instrument(
            "COST", stock_rows=[], exchange_rows=[], etf_rows=[],
            runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "NOT_FOUND")

    def test_bridge_request_preserves_all_four_target_symbols_exactly(self) -> None:
        for ticker in ("PGR", "JPM", "CME", "V"):
            with self.subTest(ticker=ticker):
                request = validate_bridge_request({
                    "operation": "stock_lookup", "ticker": ticker, "fx_applied": False,
                })
                self.assertEqual(request["ticker"], ticker)

    def test_unknown_ticker_never_falls_back_to_na(self) -> None:
        result = resolve_instrument(
            "ZZZZ", stock_rows=[], exchange_rows=[], etf_rows=[], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "NOT_FOUND")
        self.assertIsNone(result["stex_tp"])

    def test_ambiguous_ticker_fails_closed(self) -> None:
        result = resolve_instrument(
            "DUP", stock_rows=[identity("DUP", "NY"), identity("DUP", "ND")],
            exchange_rows=[], etf_rows=[], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "AMBIGUOUS")

    def test_identity_mismatch_fails_closed(self) -> None:
        result = resolve_instrument(
            "SOXL", stock_rows=[identity("SOXL", "NY", "Y")], exchange_rows=[],
            etf_rows=[{"stex_tp": "ND", "code": "SOXL"}], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "IDENTITY_MISMATCH")

    def test_unknown_exchange_code_fails_closed(self) -> None:
        result = resolve_instrument(
            "SOXL", stock_rows=[identity("SOXL", "XX", "Y")], exchange_rows=[],
            etf_rows=[], runtime_commit=COMMIT, verified_at=NOW,
        )
        self.assertEqual(result["mapping_status"], "IDENTITY_MISMATCH")

    def test_raw_and_adjusted_series_remain_separate(self) -> None:
        raw = normalize_series([chart_row("100")], ticker="SOXL", completed_session=SESSION, price_basis="RAW")
        adjusted = normalize_series([chart_row("90")], ticker="SOXL", completed_session=SESSION, price_basis="ADJUSTED")
        self.assertEqual(raw["price_basis"], "RAW")
        self.assertEqual(adjusted["price_basis"], "ADJUSTED")
        self.assertNotEqual(raw["completed_close"], adjusted["completed_close"])

    def test_fx_applied_request_is_rejected(self) -> None:
        with self.assertRaisesRegex(Exception, "FX_APPLIED_PRICE_REJECTED"):
            validate_bridge_request({
                "operation": "daily_chart", "ticker": "SOXL", "completed_session": SESSION,
                "price_basis": "RAW", "fx_applied": True,
            })

    def test_order_operation_is_blocked(self) -> None:
        with self.assertRaisesRegex(Exception, "KIWOOM_ORDER_ENDPOINT_BLOCKED"):
            validate_bridge_request({"operation": "order", "ticker": "SOXL", "fx_applied": False})
        self.assertTrue(blocked_api_target("kt10000", "/api/dostk/ordr"))

    def test_request_extra_secret_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(Exception, "INVALID_BRIDGE_REQUEST"):
            validate_bridge_request({"operation": "stock_list", "ticker": "SOXL", "APP_SECRET": "secret"})

    def test_bridge_sanitizes_token_and_secret_from_worker_output(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")
        payload = {
            "bridge_status": "PASS", "runtime_commit": COMMIT, "retrieved_at": NOW,
            "data": [{**identity("SOXL", "NY", "Y"), "APP_SECRET": "secret"}],
            "oauth_token": "token", "order_authority": True,
        }
        runner = lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, json.dumps(payload), "")
        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = invoke_bridge(
                {"operation": "stock_list", "ticker": "SOXL", "fx_applied": False},
                runtime=runtime,
                policy={"external_python_relative_path": ".venv\\Scripts\\python.exe", "maximum_attempts": 1, "request_timeout_seconds": 2},
                runner=runner,
            )
        rendered = json.dumps(result)
        self.assertNotIn("oauth_token", rendered)
        self.assertNotIn("APP_SECRET", rendered)
        self.assertFalse(result["order_authority"])

    def test_http_429_opens_without_retry_storm(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")
        calls = []
        def runner(*args, **kwargs):
            calls.append(1)
            payload = {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "HTTP_429", "order_authority": False}
            return subprocess.CompletedProcess(args[0], 2, json.dumps(payload), "")
        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = invoke_bridge(
                {"operation": "stock_list", "ticker": "SOXL", "fx_applied": False}, runtime=runtime,
                policy={"external_python_relative_path": ".venv\\Scripts\\python.exe", "maximum_attempts": 3, "request_timeout_seconds": 2, "retry_backoff_seconds": [0]},
                runner=runner,
            )
        self.assertEqual(result["failure_type"], "HTTP_429")
        self.assertEqual(len(calls), 1)

    def test_batch_bridge_reuses_one_worker_and_sanitizes_results(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")
        requests = [
            {"operation": "stock_list", "ticker": "SOXL", "fx_applied": False},
            {"operation": "etf_etn_list", "ticker": "SOXL", "fx_applied": False},
        ]
        raw_results = [
            {"bridge_status": "PASS", "runtime_commit": COMMIT, "retrieved_at": NOW, "data": [{**identity("SOXL", "NY", "Y"), "token": "hidden"}]},
            {"bridge_status": "PASS", "runtime_commit": COMMIT, "retrieved_at": NOW, "data": [{"stex_tp": "NY", "code": "SOXL", "cate1": "ETF", "token": "hidden"}]},
        ]
        payload = {"bridge_status": "PASS", "bridge_batch": True, "results": raw_results, "order_authority": False}
        calls = []
        def runner(*args, **kwargs):
            calls.append(1)
            return subprocess.CompletedProcess(args[0], 0, json.dumps(payload), "")
        with mock.patch("pathlib.Path.is_file", return_value=True):
            results = invoke_bridge_batch(
                requests, runtime=runtime,
                policy={"external_python_relative_path": ".venv\\Scripts\\python.exe", "request_timeout_seconds": 2, "minimum_request_interval_seconds": 0.25},
                runner=runner,
            )
        self.assertEqual(len(calls), 1)
        self.assertNotIn("token", json.dumps(results))
        self.assertTrue(all(item["order_authority"] is False for item in results))

    def test_batch_bridge_accepts_valid_final_json_after_cp949_diagnostics(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")
        request = {"operation": "stock_list", "ticker": "SOXL", "fx_applied": False}
        payload = {
            "bridge_status": "PASS",
            "results": [{
                "bridge_status": "PASS", "runtime_commit": COMMIT,
                "retrieved_at": NOW, "data": [identity("SOXL")],
            }],
            "order_authority": False,
        }
        raw_stdout = "진단 메시지".encode("cp949") + b"\n" + json.dumps(payload).encode("ascii")
        raw_stderr = "경고".encode("cp949")

        def runner(*args, **kwargs):
            self.assertEqual("utf-8", kwargs["encoding"])
            self.assertEqual("replace", kwargs["errors"])
            return subprocess.CompletedProcess(
                args[0], 0,
                raw_stdout.decode(kwargs["encoding"], errors=kwargs["errors"]),
                raw_stderr.decode(kwargs["encoding"], errors=kwargs["errors"]),
            )

        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = invoke_bridge_batch(
                [request], runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )
        self.assertEqual("PASS", result[0]["bridge_status"])
        self.assertEqual("SOXL", result[0]["data"][0]["stk_cd"])

    def test_account_bridge_accepts_valid_final_json_after_cp949_diagnostics(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")
        payload = {
            "bridge_status": "PASS",
            "results": [{
                "bridge_status": "PASS", "runtime_commit": COMMIT,
                "retrieved_at": NOW, "data": [],
                "pagination": {
                    "api_id": "ust21070", "pages": 1, "exhausted": True,
                    "complete": True, "secret_fields_retained": False,
                },
            }],
            "order_authority": False,
        }
        raw_stdout = "계좌 진단".encode("cp949") + b"\n" + json.dumps(payload).encode("ascii")

        def runner(*args, **kwargs):
            self.assertEqual("replace", kwargs["errors"])
            return subprocess.CompletedProcess(
                args[0], 0,
                raw_stdout.decode(kwargs["encoding"], errors=kwargs["errors"]), "",
            )

        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = invoke_account_bridge_batch(
                [{"operation": "account_holdings_read"}], runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )
        self.assertEqual("PASS", result[0]["bridge_status"])
        self.assertTrue(result[0]["pagination"]["complete"])

    def test_replacement_tainted_pass_json_is_local_protocol_failure(self) -> None:
        market_payload = {
            "bridge_status": "PASS", "diagnostic": "TAINT",
            "results": [{"bridge_status": "PASS", "data": [identity("SOXL")]}],
        }
        account_payload = {
            "bridge_status": "PASS", "diagnostic": "TAINT",
            "results": [{"bridge_status": "PASS", "data": []}],
        }
        for invoke, payload in (
            (self._market_batch_stdout, market_payload),
            (self._account_batch_stdout, account_payload),
        ):
            raw = json.dumps(payload, separators=(",", ":")).encode("ascii")
            tainted = raw.replace(b"TAINT", b"\x81").decode("utf-8", errors="replace")
            self.assertIn("\ufffd", tainted)
            result = invoke(tainted)
            self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
            self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])
            self.assertNotEqual("PASS", result["bridge_status"])

    def test_replacement_tainted_provider_failure_is_not_provider_evidence(self) -> None:
        payload = {
            "bridge_status": "PASS", "diagnostic": "TAINT",
            "results": [{
                "bridge_status": "KIWOOM_API_UNAVAILABLE",
                "failure_type": "HTTP_429", "data": [],
            }],
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("ascii")
        tainted = raw.replace(b"TAINT", b"\x81").decode("utf-8", errors="replace")
        for invoke in (self._market_batch_stdout, self._account_batch_stdout):
            result = invoke(tainted)
            self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
            self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])
            self.assertNotEqual("HTTP_429", result["failure_type"])

    def test_ascii_escaped_replacement_character_remains_valid_json(self) -> None:
        market_payload = {
            "bridge_status": "PASS", "diagnostic": "\ufffd",
            "results": [{"bridge_status": "PASS", "data": [identity("SOXL")]}],
        }
        account_payload = {
            "bridge_status": "PASS", "diagnostic": "\ufffd",
            "results": [{"bridge_status": "PASS", "data": []}],
        }
        for invoke, payload in (
            (self._market_batch_stdout, market_payload),
            (self._account_batch_stdout, account_payload),
        ):
            stdout = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
            self.assertIn("\\ufffd", stdout)
            self.assertNotIn("\ufffd", stdout)
            result = invoke(stdout)
            self.assertEqual("PASS", result["bridge_status"])

    def test_malformed_final_line_never_backtracks_to_previous_pass(self) -> None:
        market_payload = {
            "bridge_status": "PASS",
            "results": [{"bridge_status": "PASS", "data": [identity("SOXL")]}],
        }
        account_payload = {
            "bridge_status": "PASS",
            "results": [{"bridge_status": "PASS", "data": []}],
        }
        for invoke, payload in (
            (self._market_batch_stdout, market_payload),
            (self._account_batch_stdout, account_payload),
        ):
            stdout = json.dumps(payload, ensure_ascii=True) + "\n{malformed-final"
            result = invoke(stdout)
            self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
            self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])
            self.assertNotEqual("PASS", result["bridge_status"])

    def test_malformed_final_line_never_backtracks_to_provider_failure(self) -> None:
        payload = {
            "bridge_status": "PASS",
            "results": [{
                "bridge_status": "KIWOOM_API_UNAVAILABLE",
                "failure_type": "HTTP_429", "data": [],
            }],
        }
        stdout = json.dumps(payload, ensure_ascii=True) + "\nnot-json-final"
        for invoke in (self._market_batch_stdout, self._account_batch_stdout):
            result = invoke(stdout)
            self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
            self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])
            self.assertNotEqual("HTTP_429", result["failure_type"])

    def test_trailing_nonempty_diagnostic_is_protocol_failure(self) -> None:
        payload = {
            "bridge_status": "PASS",
            "results": [{"bridge_status": "PASS", "data": []}],
        }
        stdout = json.dumps(payload, ensure_ascii=True) + "\nhuman diagnostic after machine output"
        for invoke in (self._market_batch_stdout, self._account_batch_stdout):
            result = invoke(stdout)
            self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
            self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])

    def test_preceding_diagnostics_and_trailing_blank_lines_are_supported(self) -> None:
        market_payload = {
            "bridge_status": "PASS",
            "results": [{"bridge_status": "PASS", "data": [identity("SOXL")]}],
        }
        account_payload = {
            "bridge_status": "PASS",
            "results": [{"bridge_status": "PASS", "data": []}],
        }
        for invoke, payload in (
            (self._market_batch_stdout, market_payload),
            (self._account_batch_stdout, account_payload),
        ):
            stdout = "diagnostic one\ndiagnostic two\n" + json.dumps(
                payload, ensure_ascii=True,
            ) + "\n  \n\t\n"
            result = invoke(stdout)
            self.assertEqual("PASS", result["bridge_status"])

    def test_malformed_worker_output_is_local_protocol_failure_not_timeout(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")
        runner = lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "not-json\nstill-not-json", "",
        )
        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = invoke_bridge_batch(
                [{"operation": "stock_list", "ticker": "SOXL", "fx_applied": False}],
                runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )[0]
        self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
        self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])
        self.assertNotEqual("TIMEOUT", result["failure_type"])
        with mock.patch("pathlib.Path.is_file", return_value=True):
            account_result = invoke_account_bridge_batch(
                [{"operation": "account_holdings_read"}], runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )[0]
        self.assertEqual("BRIDGE_OUTPUT_INVALID", account_result["bridge_status"])
        self.assertEqual("LOCAL_PROTOCOL_FAILURE", account_result["failure_type"])
        self.assertNotEqual("TIMEOUT", account_result["failure_type"])

    def test_local_worker_launch_failure_is_not_provider_failure(self) -> None:
        runtime = Path("X:/offline-kiwoom-runtime")

        def runner(*args, **kwargs):
            raise OSError("test-only local launch failure")

        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = invoke_bridge_batch(
                [{"operation": "stock_list", "ticker": "SOXL", "fx_applied": False}],
                runtime=runtime,
                policy={
                    "external_python_relative_path": ".venv\\Scripts\\python.exe",
                    "request_timeout_seconds": 2,
                },
                runner=runner,
            )[0]
        self.assertEqual("BRIDGE_TRANSPORT_FAILURE", result["bridge_status"])
        self.assertEqual("LOCAL_TRANSPORT_FAILURE", result["failure_type"])
        self.assertNotEqual("KIWOOM_API_UNAVAILABLE", result["bridge_status"])

    def test_worker_request_uses_policy_bounded_retry(self) -> None:
        class Response:
            def __init__(self, body):
                self.body = body

        class Client:
            def __init__(self):
                self.calls = 0

            def request(self, **kwargs):
                self.calls += 1
                return Response(None if self.calls == 1 else {"return_code": 0, "list": []})

        client = Client()
        session = {
            "client": client, "pacer": lambda: None, "maximum_attempts": 2,
            "retry_backoff_seconds": 0.0,
            "retryable_failure_types": {"SCHEMA_MISMATCH"},
            "immediate_open_failure_types": {"HTTP_429", "AUTHENTICATION_FAILURE"},
        }
        result = _request(session, "usa10099", "/api/us/stkinfo", {"stex_tp": "%"})
        self.assertEqual(result["return_code"], 0)
        self.assertEqual(client.calls, 2)

    def test_worker_request_does_not_retry_http_429(self) -> None:
        class RateLimitError(RuntimeError):
            status_code = 429

        class Client:
            def __init__(self):
                self.calls = 0

            def request(self, **kwargs):
                self.calls += 1
                raise RateLimitError("rate limited")

        client = Client()
        session = {
            "client": client, "pacer": lambda: None, "maximum_attempts": 3,
            "retry_backoff_seconds": 0.0,
            "retryable_failure_types": {"TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH"},
            "immediate_open_failure_types": {"HTTP_429", "AUTHENTICATION_FAILURE"},
        }
        with self.assertRaises(RateLimitError):
            _request(session, "usa10099", "/api/us/stkinfo", {"stex_tp": "%"})
        self.assertEqual(client.calls, 1)

    def test_batch_snapshot_path_is_offline_and_complete(self) -> None:
        fake = FakeBridge()
        snapshot = build_snapshot_with_batch(
            ["SOXL", "NBIS"], completed_session=SESSION,
            batch_bridge_call=lambda requests: [fake(request) for request in requests],
            generated_at=NOW, portfolio_state_hash="f" * 64, preflight_status="PASS",
        )
        self.assertEqual(snapshot["data_status"], "PASS")
        self.assertEqual(snapshot["preflight_status"], "PASS")

    def test_one_ticker_failure_remains_local(self) -> None:
        snapshot = build_snapshot(
            ["SOXL", "BAD"], completed_session=SESSION, bridge_call=FakeBridge({"BAD"}),
            generated_at=NOW, portfolio_state_hash="a" * 64,
        )
        statuses = {item["ticker"]: item["status"] for item in snapshot["ticker_results"]}
        self.assertEqual(statuses, {"SOXL": "PASS", "BAD": "DATA_BLOCKED"})
        self.assertEqual(snapshot["data_status"], "PARTIAL")

    def test_failed_global_preflight_blocks_without_ticker_calls(self) -> None:
        preflight = {
            "official_runtime_commit": COMMIT,
            "provider_health": {
                "last_success": None, "last_failure": NOW, "consecutive_failures": 1,
                "failure_type": "AUTHENTICATION_FAILURE", "circuit_state": "OPEN", "retry_after": None,
            },
        }
        snapshot = build_preflight_blocked_snapshot(
            ["SOXL", "NBIS"], completed_session=SESSION, generated_at=NOW,
            portfolio_state_hash="e" * 64, preflight=preflight,
        )
        self.assertEqual(snapshot["data_status"], "DATA_INCOMPLETE")
        self.assertTrue(all(item["failure_reason"] == "GLOBAL_KIWOOM_PREFLIGHT_FAILED" for item in snapshot["ticker_results"]))

    def test_snapshot_schema_and_semantics_pass_offline(self) -> None:
        snapshot = build_snapshot(
            ["SOXL", "NBIS"], completed_session=SESSION, bridge_call=FakeBridge(),
            generated_at=NOW, portfolio_state_hash="b" * 64,
        )
        errors = validate_instance(snapshot, SCHEMAS / "kiwoom-market-snapshot.schema.json")
        errors.extend(validate_snapshot_semantics(snapshot))
        self.assertEqual(errors, [])
        self.assertFalse(snapshot["order_authority"])
        self.assertEqual(snapshot["operational_shadow_session_increment"], 0)

    def test_portfolio_state_remains_unchanged(self) -> None:
        state_path = REPO_ROOT / "stock-strategy-system" / "portfolio_state.json"
        before = hashlib.sha256(state_path.read_bytes()).hexdigest()
        build_snapshot(
            ["SOXL"], completed_session=SESSION, bridge_call=FakeBridge(),
            generated_at=NOW, portfolio_state_hash=before,
        )
        after = hashlib.sha256(state_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_preflight_reports_shadow_only_and_no_secret_output(self) -> None:
        readonly = {
            "official_runtime_commit": COMMIT,
            "official_runtime_remote": "https://github.com/Kiwoom-Securities/Kiwoom-REST-API.git",
            "egress_ip_preflight_url": "https://example.invalid/ip",
        }
        rate = {"external_python_relative_path": ".venv\\Scripts\\python.exe"}
        runtime = Path("X:/offline-kiwoom-runtime")
        with mock.patch("kiwoom_provider_preflight._git_commit", return_value=COMMIT), \
                mock.patch("kiwoom_provider_preflight._git_remote", return_value=readonly["official_runtime_remote"]), \
                mock.patch("pathlib.Path.is_file", return_value=True), \
                mock.patch("pathlib.Path.is_dir", return_value=True):
            result = run_preflight(
                runtime=runtime, readonly_policy=readonly, rate_policy=rate, generated_at=NOW,
                bridge_call=lambda request: {"bridge_status": "PASS", "authenticated": True, "order_authority": False},
                ip_checker=lambda: "RESOLVED_NOT_REPORTED",
            )
        self.assertEqual(result["capability_status"], "AVAILABLE")
        self.assertEqual(result["provider_state"], "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED")
        self.assertFalse(result["secrets_exposed"])

    def test_comparison_uses_raw_close_and_never_promotes(self) -> None:
        kiwoom = build_snapshot(
            ["SOXL"], completed_session=SESSION, bridge_call=FakeBridge(),
            generated_at=NOW, portfolio_state_hash="c" * 64,
        )
        primary = {"session": {"us_session_date": SESSION}, "symbols": {"SOXL": {"bar_date": SESSION, "close": 100.04}}}
        result = compare_snapshots(
            kiwoom, primary,
            tolerance_policy={"absolute_usd_floor": 0.05, "relative_fraction": 0.001},
            decision_boundaries=None, generated_at=NOW,
        )
        self.assertEqual(result["comparison_status"], "MATCH")
        self.assertFalse(result["provider_promotion"])
        self.assertFalse(result["order_authority"])

    def test_decision_boundary_flip_is_conflict(self) -> None:
        kiwoom = build_snapshot(
            ["SOXL"], completed_session=SESSION, bridge_call=FakeBridge(),
            generated_at=NOW, portfolio_state_hash="d" * 64,
        )
        primary = {"session": {"us_session_date": SESSION}, "symbols": {"SOXL": {"bar_date": SESSION, "close": 100.04}}}
        result = compare_snapshots(
            kiwoom, primary,
            tolerance_policy={"absolute_usd_floor": 0.05, "relative_fraction": 0.001},
            decision_boundaries={"SOXL": 100.02}, generated_at=NOW,
        )
        self.assertEqual(result["comparison_status"], "CONFLICT")
        self.assertTrue(result["results"][0]["decision_boundary_flip"])

    def test_source_registry_keeps_kiwoom_guarded_scoped_and_read_only(self) -> None:
        registry = json.loads((REPO_ROOT / "workspace" / "policies" / "source_capabilities.json").read_text(encoding="utf-8"))
        errors = validate_registry(registry, SCHEMAS / "source-capability.schema.json")
        self.assertEqual(errors, [])
        kiwoom = next(item for item in registry["providers"] if item["provider"] == "kiwoom_rest")
        self.assertTrue(kiwoom["enabled"])
        self.assertEqual(kiwoom["activation_status"], "ENABLED_GUARDED_SCOPED")
        self.assertEqual(kiwoom["role"], "OPERATIONAL_PRIMARY_SCOPED")
        self.assertFalse(kiwoom["order_authority"])
        self.assertFalse(kiwoom["independent_crosscheck_eligible"])

    def test_output_cannot_alias_portfolio_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_BE_UNDER_WORKSPACE_OUTPUTS|OUTPUT_PATH_ALIASES_PROTECTED_INPUT"):
            validate_shadow_output_path(
                REPO_ROOT / "stock-strategy-system" / "portfolio_state.json",
                REPO_ROOT,
            )


if __name__ == "__main__":
    unittest.main()
