#!/usr/bin/env python3
"""S1b plan A: sanitized observation marks on account bridge errors (gates unchanged)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

import kiwoom_account_readonly_bridge as bridge
from broker_visibility_audit import build_audit
from kiwoom_broker_shadow import normalize_snapshot
from portfolio_decision_dashboard import _sell_readiness_evidence
from run_manual_portfolio_analysis import _normalize_broker_state
from validation_common import validate_instance

AUDIT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/kiwoom-broker-visibility-audit.schema.json"
NOW = "2026-09-30T14:00:00+00:00"
MARKER = "SYNTHETIC_ONLY_RETURN_MSG_MARKER"
ACCOUNT_DIGITS = "5012345678"
MSG_OPEN = f"[2000]({ACCOUNT_DIGITS}:{MARKER} open orders none)"
MSG_PNL = f"[2000]({ACCOUNT_DIGITS}:{MARKER} realized pnl none)"
DECLARED_OPERATIONS = (("account_open_items", MSG_OPEN), ("account_realized_pnl_read", MSG_PNL))


def offline_session(body):
    return {
        "client": SimpleNamespace(fetch_page=Mock(return_value=SimpleNamespace(
            body=body, continuation={"cont_yn": "N", "next_key": None}))),
        "pacer": Mock(), "commit": "a" * 40, "maximum_attempts": 1, "maximum_history_pages": 3,
        "immediate_open_failure_types": set(), "retryable_failure_types": set(),
    }


def run_worker(operation, body):
    with patch.object(bridge, "_load_env_without_echo"), \
            patch.object(bridge, "_runtime_session", return_value=offline_session(body)), \
            patch.object(bridge, "utc_now", return_value=NOW):
        return bridge.external_worker(json.dumps([{"operation": operation}]), Path("X:/offline-only"))


def sanitize_worker_output(stdout_value, operation, *, exit_code=0):
    runner = Mock(return_value=subprocess.CompletedProcess(
        args=[], returncode=exit_code, stdout=json.dumps(stdout_value), stderr=""))
    with patch.object(Path, "is_file", return_value=True):
        return bridge.invoke_account_bridge_batch(
            [{"operation": operation}], runtime=Path("X:/offline-only"),
            policy={"external_python_relative_path": "offline-python", "request_timeout_seconds": 1},
            runner=runner)[0]


def end_to_end(operation, body):
    worker = run_worker(operation, body)
    return worker, sanitize_worker_output(worker, operation)


class ProviderMarksUnitTests(unittest.TestCase):
    def test_marks_matrix(self):
        cases = [
            (20, "[2000](x)", (20, True)),
            (20, "[2000]", (20, True)),
            (20, None, (20, False)),
            (20, "", (20, False)),
            (20, "[2001](x)", (20, False)),
            (20, "[200](x)", (20, False)),
            (20, " [2000](x)", (20, False)),
            (20, "prefix [2000](x)", (20, False)),
            (20, 2000, (20, False)),
            (20, ["[2000]"], (20, False)),
            ("20", "[2000](x)", (None, False)),
            (True, "[2000](x)", (None, False)),
            (False, "[2000](x)", (None, False)),
            (20.0, "[2000](x)", (None, False)),
            (None, "[2000](x)", (None, False)),
            (0, "[2000](x)", (0, False)),
            (21, "[2000](x)", (21, False)),
            (-1, "[2000](x)", (-1, False)),
        ]
        for code, message, expected in cases:
            with self.subTest(code=code, message=message):
                self.assertEqual(bridge._provider_marks(code, message), expected)

    def test_bool_code_is_never_reported_as_integer(self):
        for value in (True, False):
            code, declared = bridge._provider_marks(value, "[2000](x)")
            self.assertIsNone(code)
            self.assertIs(declared, False)


class WorkerMarksTests(unittest.TestCase):
    def assert_failure_shape(self, worker, result):
        self.assertEqual(worker["bridge_status"], "PASS")
        row = worker["results"][0]
        self.assertEqual(row["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(row["failure_type"], "API_RESPONSE_ERROR")
        self.assertEqual(result["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(result["failure_type"], "API_RESPONSE_ERROR")
        self.assertEqual(result["data"], [])
        self.assertIsNone(result["retrieved_at"])
        self.assertIsNone(result["runtime_commit"])
        self.assertFalse(result["order_authority"])

    def test_no_data_declaration_is_marked_for_open_orders_and_realized_pnl(self):
        for operation, message in DECLARED_OPERATIONS:
            with self.subTest(operation=operation):
                worker, result = end_to_end(operation, {"return_code": 20, "return_msg": message})
                self.assert_failure_shape(worker, result)
                self.assertEqual(worker["results"][0]["provider_return_code"], 20)
                self.assertIs(worker["results"][0]["no_data_declared"], True)
                self.assertEqual(result["provider_return_code"], 20)
                self.assertIs(result["no_data_declared"], True)

    def test_return_msg_is_never_stored_or_printed(self):
        for operation, message in DECLARED_OPERATIONS:
            with self.subTest(operation=operation):
                worker, result = end_to_end(operation, {"return_code": 20, "return_msg": message})
                for text in (json.dumps(worker), json.dumps(result)):
                    self.assertNotIn(MARKER, text)
                    self.assertNotIn(ACCOUNT_DIGITS, text)
                    self.assertNotIn("return_msg", text)
                    self.assertNotIn("[2000]", text)

    def test_negative_variants_keep_error_and_do_not_declare_no_data(self):
        cases = [
            ("no message", {"return_code": 20}, 20),
            ("message none", {"return_code": 20, "return_msg": None}, 20),
            ("other prefix", {"return_code": 20, "return_msg": f"[2001]({MARKER})"}, 20),
            ("prefix not at start", {"return_code": 20, "return_msg": f"x[2000]({MARKER})"}, 20),
            ("message not string", {"return_code": 20, "return_msg": 2000}, 20),
            ("string 20", {"return_code": "20", "return_msg": MSG_OPEN}, None),
            ("bool true", {"return_code": True, "return_msg": MSG_OPEN}, None),
            ("bool false", {"return_code": False, "return_msg": MSG_OPEN}, None),
            ("float 20", {"return_code": 20.0, "return_msg": MSG_OPEN}, None),
            ("other code", {"return_code": 21, "return_msg": MSG_OPEN}, 21),
            ("negative code", {"return_code": -1, "return_msg": MSG_OPEN}, -1),
            ("missing code", {"return_msg": MSG_OPEN}, None),
        ]
        for label, body, expected_code in cases:
            with self.subTest(case=label):
                worker, result = end_to_end("account_open_items", {**body, "result_list": []})
                self.assert_failure_shape(worker, result)
                self.assertEqual(result["provider_return_code"], expected_code)
                self.assertIs(result["no_data_declared"], False)
                self.assertNotIn(MARKER, json.dumps(worker) + json.dumps(result))

    def test_zero_return_code_is_success_without_marks(self):
        for code in (0, "0"):
            with self.subTest(code=code):
                worker, result = end_to_end("account_open_items", {
                    "return_code": code, "return_msg": MSG_OPEN, "result_list": []})
                self.assertEqual(result["bridge_status"], "PASS")
                self.assertNotIn("provider_return_code", result)
                self.assertNotIn("no_data_declared", result)
                self.assertNotIn(MARKER, json.dumps(worker) + json.dumps(result))

    def test_non_provider_failures_carry_empty_marks(self):
        # A schema mismatch after a successful return_code is not a provider error declaration.
        worker, result = end_to_end("account_open_items", {"return_code": 0, "result_list": "bad"})
        self.assertEqual(result["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")
        self.assertIsNone(result["provider_return_code"])
        self.assertIs(result["no_data_declared"], False)
        envelope = sanitize_worker_output(
            {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "TIMEOUT",
             "failure_stage": "runtime_initialization", "order_authority": False},
            "account_open_items", exit_code=2)
        self.assertIsNone(envelope["provider_return_code"])
        self.assertIs(envelope["no_data_declared"], False)

    def test_bridge_status_and_failure_type_are_unchanged_by_marks(self):
        # Same classification as test_return_code_twenty_is_still_error, with the declared message.
        _, result = end_to_end("account_open_items", {"return_code": 20, "return_msg": MSG_OPEN,
                                                        "result_list": []})
        self.assertEqual(result["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(result["failure_type"], "API_RESPONSE_ERROR")
        self.assertEqual(result["data"], [])


class SanitizerDistrustTests(unittest.TestCase):
    """Worker stdout is untrusted: the parent re-validates both marks."""

    def result(self, **fields):
        row = {"bridge_status": "KIWOOM_API_RESPONSE_ERROR", "failure_type": "API_RESPONSE_ERROR",
               "operation": "account_open_items", "runtime_commit": MARKER, "retrieved_at": MARKER,
               "order_authority": False, **fields}
        return sanitize_worker_output({"bridge_status": "PASS", "results": [row]}, "account_open_items")

    def test_forged_declaration_without_code_twenty_is_dropped(self):
        for code in (None, 0, 19, 21, "20", True, 20.0, MARKER, {"token": MARKER}):
            with self.subTest(code=code):
                result = self.result(provider_return_code=code, no_data_declared=True)
                self.assertIs(result["no_data_declared"], False)
                self.assertNotIn(MARKER, json.dumps(result))

    def test_non_integer_codes_and_non_true_declarations_are_dropped(self):
        for code in ("20", True, False, 20.0, MARKER, [20], {"token": MARKER}):
            with self.subTest(code=code):
                self.assertIsNone(self.result(provider_return_code=code)["provider_return_code"])
        for declared in ("true", 1, "yes", MARKER, [True]):
            with self.subTest(declared=declared):
                result = self.result(provider_return_code=20, no_data_declared=declared)
                self.assertEqual(result["provider_return_code"], 20)
                self.assertIs(result["no_data_declared"], False)

    def test_marks_survive_only_on_api_response_error_status(self):
        for status in ("KIWOOM_SCHEMA_MISMATCH", "KIWOOM_API_UNAVAILABLE", "BRIDGE_OUTPUT_INVALID", MARKER):
            with self.subTest(status=status):
                result = self.result(bridge_status=status, provider_return_code=20, no_data_declared=True)
                self.assertIsNone(result["provider_return_code"])
                self.assertIs(result["no_data_declared"], False)
        result = self.result(provider_return_code=20, no_data_declared=True)
        self.assertEqual((result["provider_return_code"], result["no_data_declared"]), (20, True))

    def test_pass_and_partial_results_never_carry_marks(self):
        for status in ("PASS", "PARTIAL"):
            with self.subTest(status=status):
                result = self.result(
                    bridge_status=status, provider_return_code=20, no_data_declared=True,
                    data=[], pagination={"api_id": "ust21050", "pages": 1, "complete": True,
                                         "exhausted": True})
                self.assertEqual(result["bridge_status"], status)
                self.assertNotIn("provider_return_code", result)
                self.assertNotIn("no_data_declared", result)

    def test_malformed_open_rows_downgrade_drops_marks(self):
        result = self.result(bridge_status="PASS", provider_return_code=20, no_data_declared=True,
                             data=[None], pagination={"api_id": "ust21050", "pages": 1,
                                                       "complete": True, "exhausted": True})
        self.assertEqual(result["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")
        self.assertIsNone(result["provider_return_code"])
        self.assertIs(result["no_data_declared"], False)

    def test_extra_worker_fields_still_discarded(self):
        result = self.result(provider_return_code=20, no_data_declared=True,
                             return_msg=MSG_OPEN, message=MSG_OPEN, account_number=ACCOUNT_DIGITS)
        text = json.dumps(result)
        for forbidden in (MARKER, ACCOUNT_DIGITS, "return_msg", "account_number"):
            self.assertNotIn(forbidden, text)


class GatesUnchangedTests(unittest.TestCase):
    def snapshot_results(self, open_items):
        at = "2026-09-30T13:00:00Z"

        def ok(operation, data):
            return {"bridge_status": "PASS", "operation": operation, "data": data, "retrieved_at": at,
                    "pagination": {"api_id": "x", "pages": 1, "complete": True, "exhausted": True},
                    "account_identifier_stored": False, "order_authority": False}
        return [
            ok("account_holdings_read", [{"stk_cd": "PGR", "qty": "10", "poss_qty": "10",
                                          "sell_alowq": "10", "frgn_stk_book_uv": "100"}]),
            ok("account_deposit_read", [{"crnc_code": "USD", "fc_pymn_alowa": "1", "fc_ord_alowa": "1"}]),
            ok("account_deposit_detail_read", [{}]), open_items, ok("account_fills_read", []),
            ok("account_realized_pnl_read", []),
        ]

    def declared_failure(self, operation="account_open_items"):
        _, result = end_to_end(operation, {"return_code": 20, "return_msg": MSG_OPEN})
        result.setdefault("ticker", None)
        return result

    def test_manual_analysis_and_dashboard_gates_do_not_change(self):
        failure = self.declared_failure()
        self.assertIs(failure["no_data_declared"], True)
        results = self.snapshot_results(failure)
        broker, status = _normalize_broker_state(
            results, observed_at="2026-09-30T13:05:00+00:00", maximum_age_seconds=900)
        evidence = broker["open_order_evidence"]
        self.assertEqual(evidence["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(evidence["provider_return_code"], 20)
        self.assertIs(evidence["no_data_declared"], True)
        self.assertNotIn(MARKER, json.dumps(broker))
        self.assertEqual(broker["operation_statuses"]["account_open_items"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertFalse(broker["scope_complete"])
        self.assertEqual(status, "AVAILABLE")
        as_of = broker["as_of"] or "2026-09-30T13:00:00+00:00"
        classified = _sell_readiness_evidence(
            {"broker_observed_state": {**broker, "as_of": as_of}, "decision_as_of": as_of,
             "broker_snapshot_as_of": as_of},
            "PGR", 10, 5, datetime.fromisoformat(as_of))
        self.assertIn("OPEN_ORDER_EVIDENCE_NOT_VERIFIED", classified["blockers"])
        self.assertEqual(classified["open_order_conflict_status"], "NOT_VERIFIED")

    def test_shadow_snapshot_stays_incomplete_and_carries_no_marks(self):
        results = self.snapshot_results(self.declared_failure())
        snapshot = normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                      generated_at="2026-09-30T13:05:00Z", maximum_age_seconds=900)
        self.assertFalse(snapshot["scope_complete"])
        self.assertEqual(snapshot["operation_statuses"]["account_open_items"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(snapshot["open_orders"], [])
        text = json.dumps(snapshot)
        for token in ("provider_return_code", "no_data_declared", MARKER, ACCOUNT_DIGITS):
            self.assertNotIn(token, text)


class VisibilityAuditMarksTests(unittest.TestCase):
    def result(self, operation, status="PASS", **fields):
        return {"operation": operation, "bridge_status": status, "data": [],
                "runtime_commit": "a" * 40, "order_authority": False, **fields}

    def audit(self, open_items, realized):
        results = [self.result("account_deposit_read"), self.result("account_holdings_read"),
                   self.result("account_fills_read"), open_items, realized]
        return build_audit(results=results, snapshot={
            "broker_snapshot_freshness_status": "FRESH", "cash": {"settled_available_cash": 63.69}})

    def failure(self, operation, **fields):
        return self.result(operation, "KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR", **fields)

    def test_declared_no_data_is_visible_but_stays_unknown_and_not_ready(self):
        value = self.audit(
            self.failure("account_open_items", provider_return_code=20, no_data_declared=True),
            self.failure("account_realized_pnl_read", provider_return_code=20, no_data_declared=True))
        for key in ("open_orders_visibility", "realized_pnl_visibility"):
            with self.subTest(key=key):
                self.assertEqual(value[key]["status"], "UNKNOWN")
                self.assertEqual(value[key]["provider_return_code"], 20)
                self.assertIs(value[key]["no_data_declared"], True)
                self.assertIs(value[key]["empty_result_interpreted_as_none"], False)
                self.assertIsNone(value[key]["record_count"])
                self.assertEqual(value[key]["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(value["broker_visibility_for_live_execution"], "NOT_READY")
        self.assertEqual({gap["capability"]: gap["classification"] for gap in value["capability_gaps"]}
                         ["open_orders"], "API_RESPONSE_ERROR")
        self.assertEqual(validate_instance(value, AUDIT_SCHEMA), [])

    def test_missing_forged_or_malformed_marks_default_to_none_false(self):
        forged = [
            {}, {"provider_return_code": 0, "no_data_declared": True},
            {"provider_return_code": "20", "no_data_declared": True},
            {"provider_return_code": True, "no_data_declared": True},
            {"provider_return_code": 20, "no_data_declared": "true"},
            {"provider_return_code": MARKER, "no_data_declared": MARKER},
        ]
        for fields in forged:
            with self.subTest(fields=fields):
                value = self.audit(self.failure("account_open_items", **fields),
                                   self.result("account_realized_pnl_read"))
                visibility = value["open_orders_visibility"]
                self.assertIs(visibility["no_data_declared"], False)
                self.assertIn(visibility["provider_return_code"], (None, 0, 20))
                self.assertNotIn(MARKER, json.dumps(value))
                self.assertEqual(validate_instance(value, AUDIT_SCHEMA), [])

    def test_available_visibility_carries_no_marks(self):
        value = self.audit(self.result("account_open_items"), self.result("account_realized_pnl_read"))
        for key in ("open_orders_visibility", "realized_pnl_visibility", "fills_visibility"):
            self.assertNotIn("provider_return_code", value[key])
            self.assertNotIn("no_data_declared", value[key])
        self.assertEqual(validate_instance(value, AUDIT_SCHEMA), [])

    def test_schema_rejects_wrongly_typed_marks(self):
        value = self.audit(
            self.failure("account_open_items", provider_return_code=20, no_data_declared=True),
            self.result("account_realized_pnl_read"))
        for field, bad in (("provider_return_code", "20"), ("provider_return_code", True),
                           ("no_data_declared", "true"), ("no_data_declared", None)):
            with self.subTest(field=field, bad=bad):
                broken = json.loads(json.dumps(value))
                broken["open_orders_visibility"][field] = bad
                self.assertNotEqual(validate_instance(broken, AUDIT_SCHEMA), [])


if __name__ == "__main__":
    unittest.main()
