#!/usr/bin/env python3
"""K3 kiwoom-token-reuse: the bridges share kiwoomcli's alias file token and recover a rejected token once.

Offline only: the official runtime is replaced by fakes that mirror the pinned runtime commit
(KiwoomAuth.get_access_token reuse with a 600 s refresh buffer, recover_from_auth_failure = clear +
issue, KiwoomClient.fetch_page retrying 401/8005/8031/8103 by itself). No network, no keyring, no files
outside a temporary directory.
"""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import kiwoom_account_readonly_bridge as account_bridge  # noqa: E402
import kiwoom_candidate_discovery_bridge as discovery_bridge  # noqa: E402
import kiwoom_runtime_bridge as bridge  # noqa: E402


ALIAS = "실전계좌"
POLICY = {"provider": "KIWOOM_REST", "token_profile_alias": ALIAS}
COMMIT = "6" * 40
TOKEN_PREFIX = "fake-secret-token"
VALID = 86400
NEAR_EXPIRY = 300
AUTH_FAIL = {"return_code": 3, "return_msg": "[8005:Token이 유효하지 않습니다]"}
MARKET_OK = {"return_code": 0, "list": [{"stk_cd": "SOXL", "stex_tp": "NYSE"}]}
ACCOUNT_OK = {"return_code": 0, "result_list": [{"stk_cd": "SOXL", "qty": "1"}]}
HTTP_401 = "HTTP_401"
HTTP_429 = "HTTP_429"


class FakeAuthenticationError(Exception):
    """Stands in for kiwoom.core.errors.AuthenticationError (raised on HTTP 401 without retry)."""


class FakeHTTPRequestError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class FakeTokenFile:
    """The alias's shared token file as (token, seconds_left); None when absent."""

    def __init__(self, seconds_left: int | None = None) -> None:
        self.record = None if seconds_left is None else (f"{TOKEN_PREFIX}-cached", seconds_left)
        self.saves: list[str] = []


class FakeAuth:
    """Mirrors KiwoomAuth at the pinned runtime commit, for the methods the bridge reaches."""

    def __init__(self, store: FakeTokenFile, *, mode: str, has_credentials: bool) -> None:
        self.store = store
        self.mode = mode
        self.has_credentials = has_credentials
        self.issued = 0
        self.recoveries = 0

    def status(self) -> SimpleNamespace:
        return SimpleNamespace(has_credentials=self.has_credentials)

    def get_access_token(self) -> str:
        record = self.store.record
        if record is not None and record[1] > 600:
            return record[0]
        return self.refresh_access_token()

    def refresh_access_token(self) -> str:
        if not self.has_credentials:
            raise FakeAuthenticationError("credentials not found")
        self.issued += 1
        token = f"{TOKEN_PREFIX}-{self.issued}"
        self.store.record = (token, VALID)
        self.store.saves.append(token)
        return token

    def authorization_header(self) -> str:
        return f"Bearer {self.get_access_token()}"

    def recover_from_auth_failure(self) -> str:
        self.recoveries += 1
        self.store.record = None
        return self.refresh_access_token()


class FakeClient:
    """Mirrors KiwoomClient.request/fetch_page, including fetch_page's own auth retry."""

    def __init__(self, auth: object, outcomes: list[object]) -> None:
        self.auth = auth
        self.outcomes = outcomes
        self.sent = 0

    def request(self, *, api_id: str, path: str, body: dict | None = None,
                extra_headers: dict | None = None, retry_on_auth_failure: bool = True, **_: object):
        header = self.auth.authorization_header()
        self.sent += 1
        outcome = self.outcomes.pop(0)
        if outcome == HTTP_429:
            raise FakeHTTPRequestError(429)
        if outcome == HTTP_401:
            if retry_on_auth_failure:
                self.auth.recover_from_auth_failure()
                return self.request(api_id=api_id, path=path, body=body,
                                    extra_headers=extra_headers, retry_on_auth_failure=False)
            raise FakeAuthenticationError(f"401 after retry with {header}")
        if outcome.get("return_code") in (8005, 8031, 8103) and retry_on_auth_failure:
            self.auth.recover_from_auth_failure()
            return self.request(api_id=api_id, path=path, body=body,
                                extra_headers=extra_headers, retry_on_auth_failure=False)
        return SimpleNamespace(body=dict(outcome), continuation=None)

    def fetch_page(self, *, api_id: str, path: str, body: dict | None = None,
                   cont_yn: str | None = None, next_key: str | None = None, **_: object):
        headers = {key: value for key, value in (("cont-yn", cont_yn), ("next-key", next_key)) if value}
        return self.request(api_id=api_id, path=path, body=body, extra_headers=headers or None)


@contextmanager
def offline_runtime(*, store: FakeTokenFile, outcomes: list[object], policy: object = POLICY,
                    has_credentials: bool = True, profiles: dict[str, str] | None = None,
                    auth_mode: str | None = None):
    state = SimpleNamespace(get_auth_calls=[], auth=None, client=None)
    registered = {ALIAS: "real"} if profiles is None else profiles

    def get_auth(mode=None, *, profile=None, secret_provider=None, token_store_kind="file"):
        state.get_auth_calls.append({"mode": mode, "profile": profile, "token_store_kind": token_store_kind})
        if profile not in registered:
            raise LookupError("alias not registered")
        if mode is not None and mode != registered[profile]:
            raise ValueError("mode does not match the alias")
        state.auth = FakeAuth(store, mode=auth_mode or registered[profile], has_credentials=has_credentials)
        return state.auth

    def get_client(mode=None, *, profile=None, auth=None, timeout_seconds=30):
        state.client = FakeClient(auth, outcomes)
        return state.client

    kiwoom = ModuleType("kiwoom")
    kiwoom.get_auth, kiwoom.get_client = get_auth, get_client
    errors = ModuleType("kiwoom.core.errors")
    errors.AuthenticationError = FakeAuthenticationError
    modules = {"kiwoom": kiwoom, "kiwoom.core": ModuleType("kiwoom.core"), "kiwoom.core.errors": errors}
    sleeps: list[float] = []
    with tempfile.TemporaryDirectory() as tmp:
        policy_path = Path(tmp) / "kiwoom-readonly-policy.json"
        if isinstance(policy, str):
            policy_path.write_text(policy, encoding="utf-8")
        elif policy is not None:
            policy_path.write_text(json.dumps(policy, ensure_ascii=False), encoding="utf-8")
        with patch.dict(sys.modules, modules), \
                patch.object(bridge, "READONLY_POLICY_PATH", policy_path), \
                patch.object(bridge, "_runtime_commit", return_value=COMMIT), \
                patch.object(bridge, "_load_env_without_echo"), \
                patch.object(account_bridge, "_load_env_without_echo"), \
                patch.object(bridge.time, "monotonic", return_value=1000.0), \
                patch.object(bridge.time, "sleep", side_effect=sleeps.append):
            yield state, sleeps


def market(requests: list[dict] | dict, **kwargs: object) -> dict:
    """A list runs as one batch session; a single dict returns that request's own result."""
    return bridge.external_worker(json.dumps(requests), Path("."), **kwargs)


def lookups(*tickers: str) -> list[dict]:
    return [{"operation": "exchange_lookup", "ticker": ticker} for ticker in tickers]


def account(*operations: str) -> dict:
    return account_bridge.external_worker(json.dumps([{"operation": op} for op in operations]), Path("."))


class AuthFailureJudgmentTest(unittest.TestCase):
    def test_one_judgment_for_bodies_and_exceptions(self):
        for body in (AUTH_FAIL, {"return_code": 8005}, {"return_code": "8031"}, {"return_code": 8103},
                     {"return_code": "3", "return_msg": "x [8103: device]"},
                     {"return_code": 3, "return_msg": "[8031:mode]"}):
            with self.subTest(body=body):
                self.assertTrue(bridge._auth_failure(SimpleNamespace(body=body)))
        for body in ({"return_code": 0}, {"return_code": 3, "return_msg": "[2000](571758:none)"},
                     {"return_code": 3}, {"return_code": 20, "return_msg": "[8005:x]"},
                     {"return_code": True, "return_msg": "[8005:x]"}, {"return_code": None},
                     {"return_code": 1700}, {}, {"return_msg": "[8005:x]"}):
            with self.subTest(body=body):
                self.assertFalse(bridge._auth_failure(SimpleNamespace(body=body)))
        self.assertFalse(bridge._auth_failure(SimpleNamespace(body=None)))
        self.assertTrue(bridge._auth_failure(FakeHTTPRequestError(401)))
        self.assertTrue(bridge._auth_failure(bridge.KiwoomAuthFailure()))
        self.assertTrue(bridge._auth_failure(FakeAuthenticationError("x"), (FakeAuthenticationError,)))
        self.assertFalse(bridge._auth_failure(FakeAuthenticationError("x")))
        for status_code in (403, 429, 500):
            self.assertFalse(bridge._auth_failure(FakeHTTPRequestError(status_code)))
        self.assertEqual("AUTHENTICATION_FAILURE", bridge._exception_failure(bridge.KiwoomAuthFailure()))

    def test_every_session_caller_shares_the_same_session_builder(self):
        self.assertIs(account_bridge._runtime_session, bridge._runtime_session)
        self.assertIs(discovery_bridge._runtime_session, bridge._runtime_session)


class SharedTokenTest(unittest.TestCase):
    def test_t1_valid_file_token_is_reused_without_issuance(self):
        store = FakeTokenFile(VALID)
        with offline_runtime(store=store, outcomes=[dict(MARKET_OK)]) as (state, _):
            health = market({"operation": "oauth_health"})
            data = market(lookups("SOXL")[0])
        self.assertEqual(("PASS", True), (health["bridge_status"], health["authenticated"]))
        self.assertEqual("PASS", data["bridge_status"])
        self.assertEqual(0, state.auth.issued)
        self.assertEqual([], store.saves)
        self.assertEqual([{"mode": "real", "profile": ALIAS, "token_store_kind": "file"}] * 2,
                         state.get_auth_calls)

    def test_t2_missing_or_expiring_token_is_issued_once_into_the_same_file(self):
        for seconds_left in (None, NEAR_EXPIRY):
            with self.subTest(seconds_left=seconds_left):
                store = FakeTokenFile(seconds_left)
                with offline_runtime(store=store, outcomes=[dict(MARKET_OK), dict(MARKET_OK)]) as (state, _):
                    result = market(lookups("SOXL", "SOXL"))
                self.assertEqual(["PASS", "PASS"], [item["bridge_status"] for item in result["results"]])
                self.assertEqual(1, state.auth.issued)
                self.assertEqual([f"{TOKEN_PREFIX}-1"], store.saves)
                self.assertEqual((f"{TOKEN_PREFIX}-1", VALID), store.record)


class SingleRecoveryTest(unittest.TestCase):
    def test_t3_return_code_3_with_8005_recovers_once_and_paces_the_retry(self):
        store = FakeTokenFile(VALID)
        with offline_runtime(store=store, outcomes=[dict(AUTH_FAIL), dict(MARKET_OK)]) as (state, sleeps):
            result = market(lookups("SOXL")[0])
        self.assertEqual("PASS", result["bridge_status"])
        self.assertEqual([{"stk_cd": "SOXL", "stex_tp": "NYSE"}],
                         [{key: row[key] for key in ("stk_cd", "stex_tp")} for row in result["data"]])
        self.assertEqual((1, 1, 2), (state.auth.recoveries, state.auth.issued, state.client.sent))
        self.assertEqual([f"{TOKEN_PREFIX}-1"], store.saves)
        self.assertEqual([0.25], sleeps)

    def test_t3_account_page_recovers_once(self):
        store = FakeTokenFile(VALID)
        with offline_runtime(store=store, outcomes=[dict(AUTH_FAIL), dict(ACCOUNT_OK)]) as (state, _):
            result = account("account_holdings_read")
        self.assertEqual("PASS", result["results"][0]["bridge_status"])
        self.assertEqual(1, state.auth.recoveries)
        self.assertEqual({"mode": "real", "profile": ALIAS, "token_store_kind": "file"}, state.get_auth_calls[0])

    def test_t3_response_after_recovery_still_needs_a_zero_return_code(self):
        for retried, status in (({"return_code": 20, "list": []}, "KIWOOM_API_UNAVAILABLE"),
                                ({"list": [{"stk_cd": "SOXL", "stex_tp": "NYSE"}]}, "KIWOOM_RETURN_CODE_MISSING")):
            with self.subTest(status=status):
                with offline_runtime(store=FakeTokenFile(VALID), outcomes=[dict(AUTH_FAIL), retried]) as (state, _):
                    result = market(lookups("SOXL")[0])
                self.assertEqual(status, result["bridge_status"])
                self.assertEqual(1, state.auth.recoveries)

    def test_t4_failed_recovery_opens_the_circuit(self):
        with offline_runtime(store=FakeTokenFile(VALID), outcomes=[dict(AUTH_FAIL), dict(AUTH_FAIL)]) as (state, _):
            result = market(lookups("SOXL", "NBIS", "MVLL"), maximum_attempts=2)
        first, *rest = result["results"]
        self.assertEqual(("KIWOOM_API_UNAVAILABLE", "AUTHENTICATION_FAILURE"),
                         (first["bridge_status"], first["failure_type"]))
        self.assertEqual(["KIWOOM_CIRCUIT_OPEN"] * 2, [item["bridge_status"] for item in rest])
        self.assertEqual((1, 2), (state.auth.recoveries, state.client.sent))

    def test_t5_second_failure_in_the_same_session_is_not_recovered(self):
        outcomes = [dict(AUTH_FAIL), dict(MARKET_OK), dict(AUTH_FAIL)]
        with offline_runtime(store=FakeTokenFile(VALID), outcomes=outcomes) as (state, _):
            result = market(lookups("SOXL", "SOXL", "SOXL"), maximum_attempts=2)
        self.assertEqual(["PASS", "KIWOOM_API_UNAVAILABLE", "KIWOOM_CIRCUIT_OPEN"],
                         [item["bridge_status"] for item in result["results"]])
        self.assertEqual("AUTHENTICATION_FAILURE", result["results"][1]["failure_type"])
        self.assertEqual((1, 3), (state.auth.recoveries, state.client.sent))

    def test_t5_runtime_client_own_retry_shares_the_single_budget(self):
        # fetch_page retries HTTP 401 and return_code 8005 by itself; that retry spends the same budget.
        outcomes = [HTTP_401, HTTP_401, {"return_code": 8005}]
        with offline_runtime(store=FakeTokenFile(VALID), outcomes=outcomes) as (state, _):
            result = account("account_holdings_read", "account_deposit_read")
        self.assertEqual([("KIWOOM_API_UNAVAILABLE", "AUTHENTICATION_FAILURE")] * 2,
                         [(item["bridge_status"], item["failure_type"]) for item in result["results"]])
        self.assertEqual((1, 3), (state.auth.recoveries, state.client.sent))

    def test_t8_http_429_is_not_recovered(self):
        with offline_runtime(store=FakeTokenFile(VALID), outcomes=[HTTP_429]) as (state, _):
            result = market(lookups("SOXL", "NBIS"), maximum_attempts=2)
        self.assertEqual([("KIWOOM_API_UNAVAILABLE", "HTTP_429"), ("KIWOOM_CIRCUIT_OPEN", "HTTP_429")],
                         [(item["bridge_status"], item["failure_type"]) for item in result["results"]])
        self.assertEqual((0, 0, 1), (state.auth.recoveries, state.auth.issued, state.client.sent))


class FailClosedTest(unittest.TestCase):
    def assert_closed(self, result: dict, state: SimpleNamespace) -> None:
        self.assertEqual(("KIWOOM_API_UNAVAILABLE", "AUTHENTICATION_FAILURE"),
                         (result["bridge_status"], result["failure_type"]))
        self.assertIsNone(state.client)
        if state.auth is not None:
            self.assertEqual((0, 0), (state.auth.issued, state.auth.recoveries))

    def test_t6_missing_or_unusable_alias_fails_closed_before_get_auth(self):
        for policy in ({"provider": "KIWOOM_REST"}, {"token_profile_alias": ""},
                       {"token_profile_alias": "   "}, {"token_profile_alias": 7},
                       {"token_profile_alias": None}, ["token_profile_alias"], "{not json", None):
            with self.subTest(policy=policy):
                with offline_runtime(store=FakeTokenFile(), outcomes=[], policy=policy) as (state, _):
                    result = market({"operation": "oauth_health"})
                    batch = account("account_holdings_read")
                self.assert_closed(result, state)
                self.assertEqual([], state.get_auth_calls)
                self.assertEqual(("KIWOOM_API_UNAVAILABLE", "AUTHENTICATION_FAILURE", "runtime_initialization"),
                                 (batch["bridge_status"], batch["failure_type"], batch["failure_stage"]))

    def test_t6_missing_credentials_fail_closed_even_with_a_cached_token(self):
        for seconds_left in (None, VALID):
            with self.subTest(seconds_left=seconds_left):
                store = FakeTokenFile(seconds_left)
                with offline_runtime(store=store, outcomes=[], has_credentials=False) as (state, _):
                    result = market({"operation": "oauth_health"})
                self.assert_closed(result, state)
                self.assertEqual([], store.saves)

    def test_t6_unregistered_or_non_real_alias_fails_closed(self):
        for options in ({"profiles": {"other": "real"}}, {"profiles": {ALIAS: "demo"}}, {"auth_mode": "demo"}):
            with self.subTest(options=options):
                with offline_runtime(store=FakeTokenFile(VALID), outcomes=[], **options) as (state, _):
                    result = market({"operation": "oauth_health"})
                self.assert_closed(result, state)
                self.assertEqual([{"mode": "real", "profile": ALIAS, "token_store_kind": "file"}],
                                 state.get_auth_calls)


class NoTokenOutputTest(unittest.TestCase):
    def run_main(self, module: ModuleType, payload: list[dict]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["bridge", "--external-worker"]), \
                patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            code = module.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_t7_no_token_in_result_stdout_or_stderr(self):
        leaky = {"return_code": 3, "return_msg": f"[8005:{TOKEN_PREFIX}-cached rejected]"}
        cases = (
            (bridge, lookups("SOXL", "NBIS"), [dict(leaky), HTTP_401]),
            (bridge, lookups("SOXL"), [dict(leaky), dict(MARKET_OK)]),
            (account_bridge, [{"operation": "account_holdings_read"}], [HTTP_401, HTTP_401]),
            (account_bridge, [{"operation": "account_holdings_read"}], [dict(leaky), dict(ACCOUNT_OK)]),
        )
        for module, payload, outcomes in cases:
            with self.subTest(module=module.__name__, outcomes=len(outcomes)):
                with offline_runtime(store=FakeTokenFile(VALID), outcomes=outcomes) as (state, _):
                    code, out, err = self.run_main(module, payload)
                self.assertIn(code, (0, 2))
                self.assertEqual(1, state.auth.recoveries)
                json.loads(out.strip().splitlines()[-1])
                self.assertNotIn(TOKEN_PREFIX, out + err)
                self.assertNotIn("8005:", out + err)


if __name__ == "__main__":
    unittest.main()
