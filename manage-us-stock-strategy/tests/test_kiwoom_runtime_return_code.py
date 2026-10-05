#!/usr/bin/env python3
"""I4 R6 item 5: a Kiwoom market response without return_code is a failure, not a success."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from kiwoom_runtime_bridge import BridgeError, _fetch_page, _request, _return_code_ok  # noqa: E402


def session_for(body, *, page=False):
    calls = []

    def respond(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(body=body, continuation=None)

    client = SimpleNamespace(fetch_page=respond) if page else SimpleNamespace(request=respond)
    return {
        "client": client, "pacer": lambda: None, "maximum_attempts": 1,
        "retry_backoff_seconds": 0.0, "retryable_failure_types": set(),
        "immediate_open_failure_types": {"HTTP_429", "AUTHENTICATION_FAILURE"},
    }, calls


class ReturnCodeContractTest(unittest.TestCase):
    def test_only_an_explicit_zero_is_success(self):
        for body in ({"return_code": 0}, {"return_code": "0"}, {"return_code": "0000"}):
            with self.subTest(body=body):
                self.assertTrue(_return_code_ok(body))
        for body in ({}, {"return_code": None}, {"return_code": 20}, {"return_code": "1"},
                     {"return_code": False}, {"return_msg": "OK"}):
            with self.subTest(body=body):
                self.assertFalse(_return_code_ok(body))

    def test_missing_return_code_fails_request(self):
        session, calls = session_for({"list": [{"stk_cd": "SOXL"}]})
        with self.assertRaises(BridgeError) as caught:
            _request(session, "usa10099", "/api/us/stkinfo", {"stex_tp": "%"})
        self.assertEqual("KIWOOM_RETURN_CODE_MISSING", caught.exception.status)
        self.assertEqual(1, len(calls))

    def test_missing_return_code_fails_page_fetch(self):
        session, _ = session_for({"stk_dt_pole_chart_qry": [{"dt": "20260813"}]}, page=True)
        with self.assertRaises(BridgeError) as caught:
            _fetch_page(session, "usa06012", "/api/us/chart", {"stk_cd": "SOXL"},
                        cont_yn=None, next_key=None)
        self.assertEqual("KIWOOM_RETURN_CODE_MISSING", caught.exception.status)

    def test_explicit_null_or_nonzero_return_code_stays_unavailable(self):
        for body in ({"return_code": None, "list": []}, {"return_code": 20, "list": []}):
            with self.subTest(body=body):
                session, _ = session_for(body)
                with self.assertRaises(BridgeError) as caught:
                    _request(session, "usa10099", "/api/us/stkinfo", {"stex_tp": "%"})
                self.assertEqual("KIWOOM_API_UNAVAILABLE", caught.exception.status)

    def test_explicit_zero_still_passes(self):
        session, _ = session_for({"return_code": 0, "list": []})
        self.assertEqual({"return_code": 0, "list": []},
                         _request(session, "usa10099", "/api/us/stkinfo", {"stex_tp": "%"}))
        session, _ = session_for({"return_code": 0, "rows": []}, page=True)
        response = _fetch_page(session, "usa06012", "/api/us/chart", {"stk_cd": "SOXL"},
                               cont_yn=None, next_key=None)
        self.assertEqual(0, response.body["return_code"])


if __name__ == "__main__":
    unittest.main()
