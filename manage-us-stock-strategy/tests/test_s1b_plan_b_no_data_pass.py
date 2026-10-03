#!/usr/bin/env python3
"""S1b plan B (K3): the provider's first-page no-data declaration becomes an empty PASS.

Design: docs/claude/s1b-plan-b-design-2026-10-03.md. Each negative case changes exactly one
condition (C1-C7) of the positive fixture unless its name says the conditions break together.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

import kiwoom_account_readonly_bridge as bridge
import test_reconcile_broker_state as reconcile_fixtures
from kiwoom_broker_shadow import normalize_snapshot
from portfolio_decision_dashboard import _sell_readiness_evidence
from run_manual_portfolio_analysis import _normalize_broker_state

NOW = "2026-10-03T14:00:00+00:00"
AT = "2026-10-03T13:00:00+00:00"
OBSERVED = "2026-10-03T13:05:00+00:00"
COMMIT = "a" * 40
OPEN_MESSAGE = "[2000](571758:해당 계좌의미체결내역이 없습니다.)"
PNL_MESSAGE = "[2000](571758:조회내역이 없습니다.)"
DECLARED = {"account_open_items": ("ust21050", OPEN_MESSAGE),
            "account_realized_pnl_read": ("ust21630", PNL_MESSAGE)}
OTHER_OPERATIONS = ("account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
                    "account_fills_read")
TERMINAL = {"cont_yn": "N", "next_key": None, "has_next": False}
MARKER = "SYNTHETIC_ONLY_PLAN_B_MARKER"
ACCOUNT_DIGITS = "5012345678"


def other(operation):
    return next(item for item in DECLARED if item != operation)


def body(operation, **changes):
    return {"return_code": 20, "return_msg": DECLARED[operation][1], **changes}


def without(mapping, key):
    return {name: value for name, value in mapping.items() if name != key}


def page(body_value, continuation=TERMINAL):
    return SimpleNamespace(body=body_value, continuation=continuation)


def session(pages, *, attempts=1, retryable=(), maximum_pages=3):
    return {
        "client": SimpleNamespace(fetch_page=Mock(side_effect=list(pages))), "pacer": Mock(),
        "commit": COMMIT, "maximum_attempts": attempts, "maximum_history_pages": maximum_pages,
        "retry_backoff_seconds": 0.0, "immediate_open_failure_types": set(),
        "retryable_failure_types": set(retryable),
    }


def run_worker(operation, pages, **kwargs):
    offline = session(pages, **kwargs)
    with patch.object(bridge, "_load_env_without_echo"), \
            patch.object(bridge, "_runtime_session", return_value=offline), \
            patch.object(bridge, "utc_now", return_value=NOW):
        worker = bridge.external_worker(json.dumps([{"operation": operation}]), Path("X:/offline-only"))
    return worker, offline


def sanitize_worker_output(stdout_value, operation, *, exit_code=0):
    runner = Mock(return_value=subprocess.CompletedProcess(
        args=[], returncode=exit_code, stdout=json.dumps(stdout_value), stderr=""))
    with patch.object(Path, "is_file", return_value=True):
        return bridge.invoke_account_bridge_batch(
            [{"operation": operation}], runtime=Path("X:/offline-only"),
            policy={"external_python_relative_path": "offline-python", "request_timeout_seconds": 1},
            runner=runner)[0]


def end_to_end(operation, pages, **kwargs):
    worker, offline = run_worker(operation, pages, **kwargs)
    return worker, sanitize_worker_output(worker, operation), offline


def promoted_pagination(operation):
    return {"api_id": DECLARED[operation][0], "pages": 1, "exhausted": True, "complete": True,
            "secret_fields_retained": False, "terminated_by": "PROVIDER_NO_DATA_DECLARATION"}


def plan_a_marks(body_value):
    """Plan A's mark rule restated independently of the implementation."""
    code, message = body_value.get("return_code"), body_value.get("return_msg")
    code = code if type(code) is int else None
    return code, code == 20 and isinstance(message, str) and message.startswith("[2000]")


def promoted_result(operation, retrieved_at, commit=COMMIT):
    worker, _ = run_worker(operation, [page(body(operation))])
    result = sanitize_worker_output(worker, operation)
    result.update(retrieved_at=retrieved_at, runtime_commit=commit)
    return result


def passing_result(operation, data, retrieved_at):
    return {"bridge_status": "PASS", "operation": operation, "data": data, "retrieved_at": retrieved_at,
            "runtime_commit": COMMIT, "account_identifier_stored": False, "portfolio_mutation": False,
            "quantity_authority": "none", "order_authority": False,
            "pagination": {"api_id": bridge.ACCOUNT_APIS[operation][0], "pages": 1, "exhausted": True,
                           "complete": True, "secret_fields_retained": False}}


def account_results(retrieved_at=AT):
    return [
        passing_result("account_holdings_read", [{"stk_cd": "PGR", "qty": "10", "poss_qty": "10",
                                                  "sell_alowq": "10", "frgn_stk_book_uv": "100"}], retrieved_at),
        passing_result("account_deposit_read", [{"crnc_code": "USD", "fc_pymn_alowa": "1",
                                                 "fc_ord_alowa": "1"}], retrieved_at),
        passing_result("account_deposit_detail_read", [{}], retrieved_at),
        promoted_result("account_open_items", retrieved_at),
        passing_result("account_fills_read", [], retrieved_at),
        promoted_result("account_realized_pnl_read", retrieved_at),
    ]


def readiness_evidence(broker):
    return {"broker_observed_state": broker, "decision_as_of": AT, "broker_snapshot_as_of": AT}


class ExplodingContinuation:
    @property
    def cont_yn(self):
        raise RuntimeError(MARKER)


class PlanBCase(unittest.TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.create_connection"):
            guard = patch(name, side_effect=AssertionError("Live network forbidden"))
            guard.start()
            self.addCleanup(guard.stop)

    def assert_promoted(self, operation, worker, result, offline):
        self.assertEqual(worker["bridge_status"], "PASS")
        for item in (worker["results"][0], result):
            self.assertEqual(item["bridge_status"], "PASS")
            self.assertEqual(item["data"], [])
            self.assertEqual(item["pagination"], promoted_pagination(operation))
            self.assertEqual(item["retrieved_at"], NOW)
            self.assertEqual(item["runtime_commit"], COMMIT)
            self.assertFalse(item["order_authority"])
            for key in ("failure_type", "provider_return_code", "no_data_declared"):
                self.assertNotIn(key, item)
        self.assertEqual(offline["client"].fetch_page.call_count, 1)

    def assert_error(self, worker, result, expected_marks):
        self.assertEqual(worker["results"][0]["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(result["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(result["failure_type"], "API_RESPONSE_ERROR")
        self.assertEqual(result["data"], [])
        self.assertIsNone(result["retrieved_at"])
        self.assertEqual((result["provider_return_code"], result["no_data_declared"]), expected_marks)
        self.assertNotIn("terminated_by", json.dumps(worker) + json.dumps(result))

    def assert_not_promoted(self, operation, body_value, continuation=TERMINAL):
        worker, result, _ = end_to_end(operation, [page(body_value, continuation)])
        self.assert_error(worker, result, plan_a_marks(body_value))


class PromotionTests(PlanBCase):
    def test_open_items_declaration_is_an_empty_pass(self):
        worker, result, offline = end_to_end("account_open_items", [page(body("account_open_items"))])
        self.assert_promoted("account_open_items", worker, result, offline)

    def test_realized_pnl_declaration_is_an_empty_pass(self):
        worker, result, offline = end_to_end(
            "account_realized_pnl_read", [page(body("account_realized_pnl_read"))])
        self.assert_promoted("account_realized_pnl_read", worker, result, offline)

    def test_absent_or_object_continuation_promotes_before_the_strict_check(self):
        continuations = (("none", None), ("empty dict", {}), ("bare object", SimpleNamespace()),
                         ("final object", SimpleNamespace(cont_yn="N", next_key=None, has_next=False)),
                         ("empty strings", {"cont_yn": "", "next_key": ""}))
        for label, continuation in continuations:
            for operation in DECLARED:
                with self.subTest(continuation=label, operation=operation):
                    worker, result, offline = end_to_end(operation, [page(body(operation), continuation)])
                    self.assert_promoted(operation, worker, result, offline)
        # Contrast: the same missing headers on a code-0 empty page stay incomplete under the strict check.
        rows, pagination = bridge._read_pages(session([SimpleNamespace(
            body={"return_code": 0, "result_list": []}, continuation=None)]), "account_open_items")
        self.assertEqual(rows, [])
        self.assertFalse(pagination["complete"])
        self.assertNotIn("terminated_by", pagination)

    def test_retry_settings_do_not_repeat_the_declared_call(self):
        for operation in DECLARED:
            with self.subTest(operation=operation):
                worker, result, offline = end_to_end(
                    operation, [page(body(operation)), page(body(operation))], attempts=2,
                    retryable=("TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH"))
                self.assert_promoted(operation, worker, result, offline)


class NegativeTests(PlanBCase):
    def test_c1_other_operations_keep_the_error(self):
        for operation in OTHER_OPERATIONS:
            for message in (OPEN_MESSAGE, PNL_MESSAGE):
                with self.subTest(operation=operation, message=message):
                    self.assert_not_promoted(operation, {"return_code": 20, "return_msg": message})

    def test_c2_return_code_variants_keep_the_error(self):
        codes = (("string", "20"), ("float", 20.0), ("bool true", True), ("bool false", False),
                 ("nineteen", 19), ("twenty-one", 21), ("negative", -1))
        for operation in DECLARED:
            for label, code in codes:
                with self.subTest(operation=operation, code=label):
                    self.assert_not_promoted(operation, body(operation, return_code=code))
            with self.subTest(operation=operation, code="missing key"):
                self.assert_not_promoted(operation, without(body(operation), "return_code"))

    def test_c3_message_variants_break_c3_with_c4(self):
        for operation, (_, message) in DECLARED.items():
            variants = (("none", None), ("int", 2000), ("list", [message]),
                        ("other prefix", message.replace("[2000]", "[2001]", 1)))
            for label, variant in variants:
                with self.subTest(operation=operation, message=label):
                    self.assert_not_promoted(operation, body(operation, return_msg=variant))
            with self.subTest(operation=operation, message="missing key"):
                self.assert_not_promoted(operation, without(body(operation), "return_msg"))

    def test_c4a_code_table_blocks_a_message_listed_outside_it(self):
        foreign = "[2000](571757:해당 계좌의미체결내역이 없습니다.)"
        with patch.dict(bridge.NO_DATA_PASS_MESSAGES,
                        {"account_open_items": frozenset({OPEN_MESSAGE, foreign})}):
            self.assert_not_promoted("account_open_items", body("account_open_items", return_msg=foreign))
            worker, result, offline = end_to_end("account_open_items", [page(body("account_open_items"))])
            self.assert_promoted("account_open_items", worker, result, offline)

    def test_c4b_message_must_match_exactly(self):
        spacing = {"account_open_items": ("계좌의미체결", "계좌의 미체결"),
                   "account_realized_pnl_read": ("조회내역이", "조회 내역이")}
        for operation, (_, message) in DECLARED.items():
            variants = {
                "trailing space": message + " ",
                "trailing newline": message + "\n",
                "no period": message.replace(".)", ")"),
                "no closing paren": message[:-1],
                "space after code": message.replace("571758:", "571758: "),
                "spacing": message.replace(*spacing[operation]),
                "appended text": message + MARKER,
                "nfd": unicodedata.normalize("NFD", message),
                "full-width closing paren": message[:-1] + "）",
                "other operation message": DECLARED[other(operation)][1],
            }
            for label, variant in variants.items():
                with self.subTest(operation=operation, variant=label):
                    self.assertNotEqual(variant, message)
                    self.assertTrue(variant.startswith("[2000](571758:"))
                    self.assert_not_promoted(operation, body(operation, return_msg=variant))

    def test_c4_code_changes_break_code_and_message_together(self):
        replacements = (("571757", "(571757:"), ("571759", "(571759:"), ("u3 no data", "(501724:"),
                        ("u3 period", "(501058:"), ("five digits", "(57175:"), ("seven digits", "(5717580:"),
                        ("full-width digits", "(５７１７５８:"), ("no colon", "(571758"),
                        ("space after paren", "( 571758:"))
        for operation, (_, message) in DECLARED.items():
            for label, replacement in replacements:
                with self.subTest(operation=operation, code=label):
                    variant = message.replace("(571758:", replacement, 1)
                    self.assertNotEqual(variant, message)
                    self.assert_not_promoted(operation, body(operation, return_msg=variant))

    def test_c5_declaration_after_a_continuation_page_keeps_the_error(self):
        rows = {"account_open_items": [{"stk_cd": "PGR", "ord_qty": "1", "ord_remnq": "1"}],
                "account_realized_pnl_read": [{"stk_cd": "PGR"}]}
        for operation in DECLARED:
            with self.subTest(operation=operation):
                first = SimpleNamespace(body={"return_code": 0, "result_list": rows[operation]},
                                        continuation={"cont_yn": "Y", "next_key": "cursor"})
                worker, result, offline = end_to_end(operation, [first, page(body(operation))])
                self.assert_error(worker, result, (20, True))
                self.assertEqual(offline["client"].fetch_page.call_count, 2)
                self.assertNotIn("PGR", json.dumps(worker) + json.dumps(result))

    def test_c6_any_extra_top_level_key_keeps_the_error(self):
        extras = (("empty result_list", {"result_list": []}), ("null result_list", {"result_list": None}),
                  ("result_list with row", {"result_list": [{"stk_cd": "PGR"}]}),
                  ("other list key", {"output": []}), ("other key", {MARKER: "x"}))
        for operation in DECLARED:
            for label, extra in extras:
                with self.subTest(operation=operation, extra=label):
                    self.assert_not_promoted(operation, body(operation, **extra))

    def test_c7_continuation_values_outside_the_allowlist_keep_the_error(self):
        cases = {"cont_yn": ("Y", "2", "MORE", "TRUE", "n", "N ", " ", "X", 0, False, ["N"], {"N": 1}),
                 "next_key": ("k", " ", 0, False),
                 "has_next": (True, None, 0, "false")}
        for operation in DECLARED:
            for field, values in cases.items():
                for value in values:
                    with self.subTest(operation=operation, field=field, value=repr(value)):
                        self.assert_not_promoted(operation, body(operation), {**TERMINAL, field: value})
            with self.subTest(operation=operation, field="object cont_yn"):
                self.assert_not_promoted(operation, body(operation),
                                         SimpleNamespace(cont_yn="Y", next_key=None, has_next=False))

    def test_message_less_twenty_keeps_the_error(self):
        for operation in DECLARED:
            for label, body_value in (("no message", {"return_code": 20}),
                                      ("locked test input", {"return_code": 20, "result_list": []})):
                with self.subTest(operation=operation, case=label):
                    self.assert_not_promoted(operation, body_value, {"cont_yn": "N", "next_key": None})


class JudgementSafetyTests(PlanBCase):
    def test_hostile_inputs_never_escape_the_judgement(self):
        cases = (
            ("message dict", body("account_open_items", return_msg={"text": OPEN_MESSAGE}), TERMINAL),
            ("message list", body("account_open_items", return_msg=[OPEN_MESSAGE]), TERMINAL),
            ("code dict", body("account_open_items", return_code={"code": 20}), TERMINAL),
            ("cont_yn list", body("account_open_items"), {**TERMINAL, "cont_yn": ["N"]}),
            ("cont_yn dict", body("account_open_items"), {**TERMINAL, "cont_yn": {"N": 1}}),
            ("exploding continuation", body("account_open_items"), ExplodingContinuation()),
            ("integer key", {**body("account_open_items"), 1: "x"}, TERMINAL),
        )
        for label, body_value, continuation in cases:
            with self.subTest(case=label):
                response = page(body_value, continuation)
                self.assertIs(bridge._no_data_terminal("account_open_items", body_value, response), False)
                with self.assertRaises(bridge.BridgeError) as caught:
                    bridge._fetch_account_page(session([response]), "account_open_items", {},
                                               cont_yn=None, next_key=None)
                error = caught.exception
                self.assertEqual((error.status, error.failure_type),
                                 ("KIWOOM_API_RESPONSE_ERROR", "API_RESPONSE_ERROR"))
                self.assertEqual((error.provider_return_code, error.no_data_declared), plan_a_marks(body_value))
                self.assertIs(error.no_data_terminal, False)
                worker, result, _ = end_to_end("account_open_items", [page(body_value, continuation)])
                self.assert_error(worker, result, plan_a_marks(body_value))
                self.assertNotIn(MARKER, json.dumps(worker) + json.dumps(result))
        unknown = body("account_open_items")
        self.assertIs(bridge._no_data_terminal("account_unknown", unknown, page(unknown)), False)

    def test_read_pages_reraises_the_original_exception_object(self):
        cases = (("not terminal", "KIWOOM_API_RESPONSE_ERROR", False),
                 ("other status", "KIWOOM_SCHEMA_MISMATCH", True),
                 ("no judgement attribute", "KIWOOM_API_RESPONSE_ERROR", None))
        for label, status, terminal in cases:
            with self.subTest(case=label):
                original = bridge.BridgeError(status, "API_RESPONSE_ERROR")
                if terminal is not None:
                    original.no_data_terminal = terminal
                with patch.object(bridge, "_fetch_account_page", side_effect=original), \
                        self.assertRaises(bridge.BridgeError) as caught:
                    bridge._read_pages(session([]), "account_open_items")
                self.assertIs(caught.exception, original)
        foreign = RuntimeError(MARKER)
        with patch.object(bridge, "_fetch_account_page", side_effect=foreign), \
                self.assertRaises(RuntimeError) as caught:
            bridge._read_pages(session([]), "account_open_items")
        self.assertIs(caught.exception, foreign)


class TableTests(PlanBCase):
    def test_tables_bind_codes_and_messages_per_operation(self):
        synthetic = {"account_open_items": ("111111", "[2000](111111:SYNTHETIC OPEN NONE)"),
                     "account_realized_pnl_read": ("222222", "[2000](222222:SYNTHETIC PNL NONE)")}
        with patch.dict(bridge.NO_DATA_PASS_MESSAGE_CODES,
                        {operation: frozenset({code}) for operation, (code, _) in synthetic.items()}), \
                patch.dict(bridge.NO_DATA_PASS_MESSAGES,
                           {operation: frozenset({message}) for operation, (_, message) in synthetic.items()}):
            for operation, (_, own) in synthetic.items():
                foreign = synthetic[other(operation)][1]
                with self.subTest(operation=operation):
                    worker, result, offline = end_to_end(operation, [page({"return_code": 20, "return_msg": own})])
                    self.assert_promoted(operation, worker, result, offline)
                    self.assert_not_promoted(operation, {"return_code": 20, "return_msg": foreign})
                    self.assert_not_promoted(operation, body(operation))
                    # Listed for this operation but carrying the other operation's code: the code table still blocks.
                    with patch.dict(bridge.NO_DATA_PASS_MESSAGES, {operation: frozenset({own, foreign})}):
                        self.assert_not_promoted(operation, {"return_code": 20, "return_msg": foreign})

    def test_production_tables_are_locked(self):
        self.assertEqual(bridge.NO_DATA_PASS_MESSAGE_CODES, {
            "account_open_items": frozenset({"571758"}),
            "account_realized_pnl_read": frozenset({"571758"}),
        })
        self.assertEqual(bridge.NO_DATA_PASS_MESSAGES, {
            "account_open_items": frozenset({OPEN_MESSAGE}),
            "account_realized_pnl_read": frozenset({PNL_MESSAGE}),
        })
        self.assertEqual(bridge.NO_DATA_TERMINATION, "PROVIDER_NO_DATA_DECLARATION")

    def test_each_message_starts_with_a_code_of_its_own_operation(self):
        self.assertEqual(set(bridge.NO_DATA_PASS_MESSAGES), set(bridge.NO_DATA_PASS_MESSAGE_CODES))
        for operation, messages in bridge.NO_DATA_PASS_MESSAGES.items():
            for message in messages:
                with self.subTest(operation=operation):
                    self.assertTrue(any(message.startswith(f"[2000]({code}:")
                                        for code in bridge.NO_DATA_PASS_MESSAGE_CODES[operation]))


class SanitizerTests(PlanBCase):
    @staticmethod
    def promoted_row(operation, **changes):
        row = {"bridge_status": "PASS", "operation": operation, "data": [],
               "pagination": promoted_pagination(operation), "runtime_commit": COMMIT, "retrieved_at": NOW,
               "account_identifier_stored": False, "portfolio_mutation": False,
               "quantity_authority": "none", "order_authority": False}
        row.update(changes)
        return row

    @staticmethod
    def through_parent(row, operation):
        return sanitize_worker_output({"bridge_status": "PASS", "results": [row], "order_authority": False},
                                      operation)

    def test_promoted_row_keeps_its_display_basis(self):
        for operation in DECLARED:
            with self.subTest(operation=operation):
                result = self.through_parent(self.promoted_row(operation), operation)
                self.assertEqual(result["bridge_status"], "PASS")
                self.assertEqual(result["pagination"], promoted_pagination(operation))

    def test_forged_or_inconsistent_basis_is_dropped_without_changing_anything_else(self):
        open_items, realized = "account_open_items", "account_realized_pnl_read"

        def paged(**changes):
            return self.promoted_row(open_items, pagination={**promoted_pagination(open_items), **changes})

        def paged_without(key):
            return self.promoted_row(open_items, pagination=without(promoted_pagination(open_items), key))

        cases = (
            ("raw [None] data", self.promoted_row(realized, data=[None])),
            ("data with row", self.promoted_row(realized, data=[{"stk_cd": "PGR"}])),
            ("data missing", without(self.promoted_row(realized), "data")),
            ("data none", self.promoted_row(realized, data=None)),
            ("data string", self.promoted_row(realized, data="x")),
            ("pages true", paged(pages=True)), ("pages float", paged(pages=1.0)),
            ("pages string", paged(pages="1")), ("pages two", paged(pages=2)),
            ("complete false", paged(complete=False)), ("complete missing", paged_without("complete")),
            ("exhausted false", paged(exhausted=False)), ("exhausted missing", paged_without("exhausted")),
            ("other basis", paged(terminated_by="OTHER")), ("non-string basis", paged(terminated_by=1)),
            ("partial", self.promoted_row(open_items, bridge_status="PARTIAL")),
            ("error status", self.promoted_row(open_items, bridge_status="KIWOOM_API_RESPONSE_ERROR",
                                               failure_type="API_RESPONSE_ERROR")),
            ("open items [None] downgrade", self.promoted_row(open_items, data=[None])),
            ("other operation", {**self.promoted_row(open_items), "operation": "account_fills_read"}),
        )
        for label, row in cases:
            with self.subTest(case=label):
                operation = row["operation"]
                plain = copy.deepcopy(row)
                if isinstance(plain.get("pagination"), dict):
                    plain["pagination"].pop("terminated_by", None)
                result = self.through_parent(row, operation)
                self.assertNotIn("terminated_by", result.get("pagination") or {})
                self.assertEqual(result, self.through_parent(plain, operation))

    def test_nonzero_child_exit_drops_the_promotion(self):
        for operation in DECLARED:
            with self.subTest(operation=operation):
                worker, _ = run_worker(operation, [page(body(operation))])
                result = sanitize_worker_output(worker, operation, exit_code=2)
                self.assertNotEqual(result["bridge_status"], "PASS")
                self.assertNotIn("terminated_by", json.dumps(result))

    def test_sanitize_is_idempotent_and_survives_manual_normalization(self):
        for operation in DECLARED:
            with self.subTest(operation=operation):
                _, result, _ = end_to_end(operation, [page(body(operation))])
                self.assertEqual(bridge._sanitize(copy.deepcopy(result), operation), result)
        broker, _ = _normalize_broker_state(account_results(), observed_at=OBSERVED, maximum_age_seconds=900)
        self.assertEqual(broker["open_order_evidence"]["pagination"], promoted_pagination("account_open_items"))

    def test_basis_is_display_only_for_every_gate(self):
        with_basis = account_results()
        without_basis = copy.deepcopy(with_basis)
        for item in without_basis:
            item["pagination"].pop("terminated_by", None)
        broker_a, status_a = _normalize_broker_state(with_basis, observed_at=OBSERVED, maximum_age_seconds=900)
        broker_b, status_b = _normalize_broker_state(without_basis, observed_at=OBSERVED, maximum_age_seconds=900)
        self.assertEqual(status_a, status_b)
        stripped = copy.deepcopy(broker_a)
        self.assertEqual(stripped["open_order_evidence"]["pagination"].pop("terminated_by"),
                         "PROVIDER_NO_DATA_DECLARATION")
        self.assertEqual(stripped, broker_b)
        evaluation = datetime.fromisoformat(AT)
        self.assertEqual(_sell_readiness_evidence(readiness_evidence(broker_a), "PGR", 10, 5, evaluation),
                         _sell_readiness_evidence(readiness_evidence(broker_b), "PGR", 10, 5, evaluation))

        def snapshot(results):
            return normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                      generated_at=OBSERVED, maximum_age_seconds=900)
        self.assertEqual(snapshot(with_basis), snapshot(without_basis))

    def test_no_message_code_or_marker_is_stored(self):
        for operation, (_, message) in DECLARED.items():
            with self.subTest(operation=operation, path="promoted"):
                worker, result, _ = end_to_end(operation, [page(body(operation))])
                text = json.dumps(worker, ensure_ascii=False) + json.dumps(result, ensure_ascii=False)
                for token in ("571758", "[2000]", "return_msg", "없습니다", "조회내역", "미체결내역"):
                    self.assertNotIn(token, text)
            with self.subTest(operation=operation, path="rejected"):
                forged = body(operation, return_msg=message[:-1] + ACCOUNT_DIGITS + MARKER + ")")
                worker, result, _ = end_to_end(operation, [page(forged)])
                text = json.dumps(worker, ensure_ascii=False) + json.dumps(result, ensure_ascii=False)
                for token in (MARKER, ACCOUNT_DIGITS, "return_msg", "[2000]", "571758"):
                    self.assertNotIn(token, text)


class IntendedEffectTests(PlanBCase):
    def test_manual_normalization_sees_both_reads_verified(self):
        broker, status = _normalize_broker_state(account_results(), observed_at=OBSERVED, maximum_age_seconds=900)
        self.assertEqual(status, "AVAILABLE")
        self.assertTrue(broker["scope_complete"])
        self.assertEqual(broker["operation_statuses"]["account_open_items"], "PASS")
        self.assertEqual(broker["operation_statuses"]["account_realized_pnl_read"], "PASS")
        self.assertEqual(broker["as_of"], AT)
        evidence = broker["open_order_evidence"]
        self.assertEqual((evidence["bridge_status"], evidence["data"]), ("PASS", []))

    def test_dashboard_sees_verified_none_and_keeps_the_freshness_window(self):
        broker, _ = _normalize_broker_state(account_results(), observed_at=OBSERVED, maximum_age_seconds=900)
        evaluation = datetime.fromisoformat(AT)
        fresh = _sell_readiness_evidence(readiness_evidence(broker), "PGR", 10, 5, evaluation)
        self.assertEqual(fresh["open_order_conflict_status"], "VERIFIED_NONE")
        self.assertNotIn("OPEN_ORDER_EVIDENCE_NOT_VERIFIED", fresh["blockers"])
        stale = _sell_readiness_evidence(readiness_evidence(broker), "PGR", 10, 5,
                                         evaluation + timedelta(seconds=900))
        self.assertEqual(stale["open_order_conflict_status"], "NOT_VERIFIED")
        self.assertIn("OPEN_ORDER_EVIDENCE_STALE", stale["blockers"])

    def test_shadow_snapshot_and_reconciliation_proposal_see_open_orders_verified(self):
        now = datetime.now(timezone.utc)
        retrieved_at = reconcile_fixtures.utc(now - timedelta(seconds=30))
        promoted = {operation: promoted_result(operation, retrieved_at, commit="c" * 40) for operation in DECLARED}
        results = [promoted.get(item["operation"], item) for item in reconcile_fixtures.account_results(
            retrieved_at, statuses={"account_open_items": "PASS"})]
        snapshot = normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                      generated_at=reconcile_fixtures.utc(now), maximum_age_seconds=900)
        self.assertTrue(snapshot["scope_complete"])
        self.assertEqual((snapshot["open_orders"], snapshot["realized_pnl"]), ([], []))
        text = json.dumps(snapshot)
        for token in ("terminated_by", "PROVIDER_NO_DATA_DECLARATION", "provider_return_code",
                      "no_data_declared", "571758"):
            self.assertNotIn(token, text)
        proposal = reconcile_fixtures.make_proposal(reconcile_fixtures.base_state(), now=now, results=results)
        self.assertIs(proposal["open_orders_verified"], True)
        self.assertIs(proposal["confirmed_snapshot_record"]["open_orders_verified"], True)
        self.assertNotIn("OPEN_ORDERS_UNVERIFIED", proposal["warnings"])
        self.assertFalse(proposal["order_authority"])


if __name__ == "__main__":
    unittest.main()
