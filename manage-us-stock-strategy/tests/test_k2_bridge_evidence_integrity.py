#!/usr/bin/env python3
"""Offline Judge reproductions from raw account pages through both SELL paths."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_portfolio_decision_order_intent as fixtures
import kiwoom_account_readonly_bridge as bridge
from portfolio_decision_dashboard import compile_dashboard
from portfolio_decision_order_intent import compile_order_intent_artifact
from run_manual_portfolio_analysis import _normalize_broker_state
from validation_common import canonical_hash


NOW = "2026-08-21T14:00:00+00:00"
VALID_ROW = {"stk_cd": "PGR", "ord_qty": "1", "ord_remnq": "1"}


def page(rows, continuation):
    return SimpleNamespace(body={"return_code": 0, "result_list": rows}, continuation=continuation)


def session(pages, *, maximum_pages=3):
    return {
        "client": SimpleNamespace(fetch_page=Mock(side_effect=pages)), "pacer": Mock(),
        "commit": "a" * 40, "maximum_attempts": 1, "maximum_history_pages": maximum_pages,
        "immediate_open_failure_types": set(), "retryable_failure_types": set(),
    }


class K2BridgeEvidenceIntegrityTests(unittest.TestCase):
    inputs = fixtures.ManualSellRuleTests.inputs
    instruction = staticmethod(fixtures.OrderIntentOnlyTests.instruction)

    def setUp(self):
        fixtures.OrderIntentOnlyTests.setUp(self)
        self.network_guards = ExitStack()
        self.addCleanup(self.network_guards.close)
        self.network_spies = [self.network_guards.enter_context(patch(
            name, side_effect=AssertionError("Live network or gateway forbidden"),
        )) for name in (
            "socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
            "urllib.request.urlopen", "http.client.HTTPConnection.request",
            "future_order_shadow.build_gateway_dry_run",
        )]

    def tearDown(self):
        for spy in self.network_spies:
            spy.assert_not_called()

    def worker_result(self, pages, *, maximum_pages=3):
        offline_session = session(pages, maximum_pages=maximum_pages)
        with patch.object(bridge, "_load_env_without_echo") as env_loader, \
                patch.object(bridge, "_runtime_session", return_value=offline_session), \
                patch.object(bridge, "utc_now", return_value=NOW):
            result = bridge.external_worker(
                json.dumps([{"operation": "account_open_items"}]),
                Path("X:/offline-only-not-accessed"), maximum_pages=maximum_pages,
            )
            env_loader.assert_called_once()
        self.assertEqual(result["bridge_status"], "PASS")
        return result, offline_session

    def invoke_sanitizer(self, worker_result):
        runner = Mock(return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(worker_result), stderr="",
        ))
        with patch.object(Path, "is_file", return_value=True):
            result = bridge.invoke_account_bridge_batch(
                [{"operation": "account_open_items"}], runtime=Path("X:/offline-only-not-accessed"),
                policy={"external_python_relative_path": "offline-python", "request_timeout_seconds": 1},
                runner=runner,
            )
        runner.assert_called_once()
        return result[0]

    def final_sell(self, open_result, *, sell_path):
        args, authority = self.inputs()
        source = args["evidence"]
        reader = fixtures._fixture._manual_module.account_reader_for(
            {"PGR": 10}, {"PGR": 100}, orderable_cash=8000, retrieved_at=NOW,
        )
        account_results = reader([{"operation": operation} for operation in (
            "account_holdings_read", "account_deposit_read", "account_open_items",
        )])
        account_results[-1] = copy.deepcopy(open_result)
        broker, status = _normalize_broker_state(account_results, observed_at=NOW, maximum_age_seconds=900)
        self.assertEqual(status, "AVAILABLE")
        source["broker_observed_state"] = broker
        self.assertEqual(broker["open_order_evidence"]["bridge_status"], open_result["bridge_status"])
        if sell_path == "fixed_limit":
            args["plan"]["positions"][0]["order_intent_terms"].update(
                limit_price=200, approved_price_rule=None,
            )
        sha = hashlib.sha256(fixtures._fixture.evidence_raw_bytes(source)).hexdigest()
        args["input_hashes"]["portfolio_evidence"] = sha
        args["current_session_context"] = fixtures._fixture.current_context(source, sha)
        report, validation = compile_dashboard(
            source, args["plan"], self.policy, registry=self.registry,
            generated_at=NOW, evidence_sha256=sha,
            current_session_context=args["current_session_context"],
            current_session_authority_resolver=lambda *a, **k: authority,
        )
        self.assertEqual(validation["status"], "PASS", validation)
        args.update(report=report, validation=validation)
        args["input_hashes"].update(
            portfolio_decision=canonical_hash(report), validation_report=canonical_hash(validation),
            decision_plan=canonical_hash(args["plan"]),
        )
        artifact = compile_order_intent_artifact(**args)
        for item in (artifact, artifact["instructions"][0]):
            self.assertFalse(item["order_authority"])
            self.assertFalse(item["automatic_order"])
            self.assertFalse(item["portfolio_mutation"])
            self.assertIsNone(item["execution_quantity"])
            self.assertEqual(item["broker_submission"], "DISABLED")
        return report["evidence"]["sell_readiness"]["PGR"], self.instruction(artifact, "PGR")

    def assert_both_blocked(self, result):
        for sell_path in ("manual_best_bid", "fixed_limit"):
            with self.subTest(sell_path=sell_path):
                classification, intent = self.final_sell(result, sell_path=sell_path)
                self.assertEqual(classification["open_order_conflict_status"], "NOT_VERIFIED")
                self.assertEqual(intent["state"], "ORDER_BLOCKED", intent["blockers"])
                self.assertIn("OPEN_ORDER_EVIDENCE_NOT_VERIFIED", intent["blockers"])

    def malformed_rows_case(self, rows):
        with self.subTest(boundary="read_pages"):
            with self.assertRaises(bridge.BridgeError) as caught:
                bridge._read_pages(session([page(rows, {"cont_yn": "N", "next_key": None})]), "account_open_items")
            self.assertEqual(caught.exception.status, "KIWOOM_SCHEMA_MISMATCH")
        raw, _ = self.worker_result([page(rows, {"cont_yn": "N", "next_key": None})])
        result = self.invoke_sanitizer(raw)
        with self.subTest(boundary="worker_status"):
            self.assertEqual(result["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")
        self.assert_both_blocked(result)

    def incomplete_case(self, continuation):
        with self.subTest(boundary="read_pages"):
            _, pagination = bridge._read_pages(session([page([], continuation)]), "account_open_items")
            self.assertFalse(pagination["complete"])
            self.assertFalse(pagination["exhausted"])
        raw, offline_session = self.worker_result([page([], continuation)])
        result = self.invoke_sanitizer(raw)
        with self.subTest(boundary="worker_status"):
            self.assertEqual(result["bridge_status"], "PARTIAL")
            self.assertFalse(result["pagination"]["complete"])
            self.assertFalse(result["pagination"]["exhausted"])
            self.assertEqual(offline_session["client"].fetch_page.call_count, 1)
        self.assert_both_blocked(result)

    def test_r1_raw_null_row(self):
        self.malformed_rows_case([None])

    def test_r2_raw_string_row(self):
        self.malformed_rows_case(["INVALID"])

    def test_r3_raw_numeric_row(self):
        self.malformed_rows_case([42])

    def test_r4_valid_then_null_row(self):
        self.malformed_rows_case([VALID_ROW, None])

    def test_r5_null_then_valid_row(self):
        self.malformed_rows_case([None, VALID_ROW])

    def test_r6_valid_then_string_row(self):
        self.malformed_rows_case([VALID_ROW, "INVALID"])

    def test_r7_y_null_key(self):
        self.incomplete_case({"cont_yn": "Y", "next_key": None})

    def test_r8_y_missing_key(self):
        self.incomplete_case({"cont_yn": "Y"})

    def test_r9_y_empty_or_invalid_key(self):
        for token in ("", " ", 42, True, [], {}):
            with self.subTest(token=token):
                self.incomplete_case({"cont_yn": "Y", "next_key": token})

    def test_p1_valid_final_page_preserves_ready(self):
        for continuation in ({"cont_yn": "N", "next_key": None},
                             SimpleNamespace(cont_yn="N", next_key=None),
                             SimpleNamespace(cont_yn=None, next_key=None)):
            raw, _ = self.worker_result([page([], continuation)])
            result = self.invoke_sanitizer(raw)
            self.assertEqual(result["bridge_status"], "PASS")
            self.assertTrue(result["pagination"]["complete"])
            self.assertTrue(result["pagination"]["exhausted"])
            for sell_path in ("manual_best_bid", "fixed_limit"):
                classification, intent = self.final_sell(result, sell_path=sell_path)
                self.assertEqual(classification["open_order_conflict_status"], "VERIFIED_NONE")
                self.assertEqual(intent["state"], "ORDER_INSTRUCTION_READY", intent["blockers"])

    def test_p2_valid_continuation_preserves_cursor_and_completion(self):
        for indicator in ("Y", "2", "MORE", "TRUE"):
            raw, offline_session = self.worker_result([
                page([], {"cont_yn": indicator, "next_key": "offline-cursor"}),
                page([], {"cont_yn": "N", "next_key": None}),
            ])
            result = self.invoke_sanitizer(raw)
            self.assertEqual(result["bridge_status"], "PASS")
            self.assertEqual(result["pagination"]["pages"], 2)
            self.assertTrue(result["pagination"]["complete"])
            self.assertEqual(offline_session["client"].fetch_page.call_args_list[1].kwargs["next_key"], "offline-cursor")
            self.assertEqual(offline_session["client"].fetch_page.call_args_list[1].kwargs["cont_yn"], indicator)
            for sell_path in ("manual_best_bid", "fixed_limit"):
                _, intent = self.final_sell(result, sell_path=sell_path)
                self.assertEqual(intent["state"], "ORDER_INSTRUCTION_READY", intent["blockers"])

    def test_p6_malformed_continuation_metadata(self):
        for continuation in (None, [], "INVALID", 42, {},
                             {"cont_yn": 42}, {"cont_yn": True}, {"cont_yn": []},
                             {"cont_yn": "INVALID"}, {"cont_yn": "N", "next_key": {}},
                             {"cont_yn": None, "next_key": "unexpected-cursor"}):
            with self.subTest(continuation=continuation):
                self.incomplete_case(continuation)

    def test_second_page_malformed_rows_never_keep_first_page_success(self):
        raw, _ = self.worker_result([
            page([VALID_ROW], {"cont_yn": "Y", "next_key": "offline-cursor"}),
            page([None], {"cont_yn": "N", "next_key": None}),
        ])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")
        self.assert_both_blocked(result)

    def test_worker_output_sanitizer_rejects_lossy_rows_independently(self):
        for rows in ([None], ["INVALID"], [42], [VALID_ROW, None], [None, VALID_ROW], [VALID_ROW, "INVALID"]):
            raw = {"results": [{
                "operation": "account_open_items", "bridge_status": "PASS", "retrieved_at": NOW,
                "data": rows, "pagination": {"api_id": "ust21050", "pages": 1,
                                               "complete": True, "exhausted": True},
            }]}
            result = self.invoke_sanitizer(raw)
            with self.subTest(rows=rows):
                self.assertEqual(result["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")
                self.assertFalse(result["pagination"]["complete"])
                self.assertFalse(result["pagination"]["exhausted"])
            self.assert_both_blocked(result)

    def test_valid_dict_field_allowlist_and_nonempty_block_are_preserved(self):
        row = {**VALID_ROW, "unsupported_field": "FAKE_PRIVATE"}
        raw, _ = self.worker_result([page([row], {"cont_yn": "N", "next_key": None})])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "PASS")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["ord_remnq"], "1")
        self.assertNotIn("FAKE_PRIVATE", json.dumps(result))
        for sell_path in ("manual_best_bid", "fixed_limit"):
            classification, intent = self.final_sell(result, sell_path=sell_path)
            self.assertEqual(classification["open_order_conflict_status"], "NOT_VERIFIED")
            self.assertEqual(intent["state"], "ORDER_BLOCKED")
            self.assertIn("OPEN_ORDER_CONFLICT_PRESENT", intent["blockers"])

    def test_page_budget_exhaustion_and_no_progress_remain_fail_closed(self):
        raw, _ = self.worker_result([page([], {"cont_yn": "Y", "next_key": "cursor"})], maximum_pages=1)
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "PARTIAL")
        self.assert_both_blocked(result)
        raw, _ = self.worker_result([
            page([], {"cont_yn": "Y", "next_key": "cursor"}),
            page([], {"cont_yn": "Y", "next_key": "cursor"}),
        ])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "KIWOOM_PAGINATION_NO_PROGRESS")
        self.assert_both_blocked(result)

    def test_return_code_twenty_is_still_error(self):
        response = page([], {"cont_yn": "N", "next_key": None})
        response.body["return_code"] = 20
        raw, _ = self.worker_result([response])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assert_both_blocked(result)


if __name__ == "__main__":
    unittest.main()
