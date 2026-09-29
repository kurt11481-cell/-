from __future__ import annotations

import copy
import io
import json
import subprocess
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from kiwoom_broker_shadow import normalize_snapshot, reconciliation_proposal
import kiwoom_account_readonly_bridge as bridge
from kiwoom_account_readonly_bridge import validate_request
from kiwoom_runtime_bridge import blocked_api_target
from validation_common import file_hash, load_json, validate_instance


class KiwoomBrokerShadowTests(unittest.TestCase):
    def results(self):
        at = "2026-08-14T13:00:00Z"
        def value(operation, data):
            return {"bridge_status": "PASS", "operation": operation, "data": data,
                    "retrieved_at": at, "account_identifier_stored": False, "order_authority": False}
        return [
            value("account_holdings_read", [{"stk_cd": "NBIS", "frgn_stk_nm": "Nebius", "crnc_code": "USD", "qty": "15", "poss_qty": "15", "sell_alowq": "15", "frgn_stk_book_uv": "215"}]),
            value("account_deposit_read", [{"crnc_code": "USD", "crnc_nm": "US Dollar", "fc_entra": "0", "fc_pymn_alowa": "0", "fc_ord_alowa": "0"}]),
            value("account_deposit_detail_read", [{"d1_usd_sell_excta": "5000", "d1_usd_buy_excta": "0", "d2_usd_sell_excta": "0", "d2_usd_buy_excta": "0"}]),
            value("account_open_items", []), value("account_fills_read", []), value("account_realized_pnl_read", []),
        ]

    def test_masking_and_no_account_identifier(self):
        value = normalize_snapshot(self.results(), snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                   generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        self.assertFalse(value["account_identifier_stored"])
        self.assertNotIn("account_number", str(value).lower())

    def test_cash_semantics_excludes_unsettled(self):
        value = normalize_snapshot(self.results(), snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                   generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        self.assertEqual(value["cash"]["settled_available_cash"], 0)
        self.assertEqual(value["cash"]["cash_status"], "VERIFIED_ZERO")
        self.assertEqual(value["cash"]["unsettled_funds"]["d1_sell_settlement_usd"], 5000)

    def test_stale_snapshot(self):
        value = normalize_snapshot(self.results(), snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                   generated_at="2026-08-14T14:00:01Z", maximum_age_seconds=900)
        self.assertEqual(value["broker_snapshot_freshness_status"], "STALE")

    def test_no_fill_inference_or_auto_apply(self):
        before = file_hash(ROOT / "stock-strategy-system/portfolio_state.json")
        portfolio = load_json(ROOT / "stock-strategy-system/portfolio_state.json")
        snap = normalize_snapshot(self.results(), snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        proposal = reconciliation_proposal(snap, portfolio, expected_before_hash=before)
        self.assertFalse(proposal["auto_apply"])
        self.assertFalse(proposal["fill_inference_performed"])
        self.assertEqual(before, file_hash(ROOT / "stock-strategy-system/portfolio_state.json"))

    def test_state_revision_is_bound(self):
        portfolio = load_json(ROOT / "stock-strategy-system/portfolio_state.json")
        snap = normalize_snapshot(self.results(), snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        proposal = reconciliation_proposal(snap, portfolio, expected_before_hash="a" * 64)
        self.assertEqual(proposal["current_state_revision"], portfolio["state_revision"])
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")

    def test_read_operations_allowlisted_and_writes_denied(self):
        self.assertEqual(validate_request({"operation": "account_holdings_read"})["operation"], "account_holdings_read")
        self.assertTrue(blocked_api_target("usa10075", "/api/us/ordr"))
        with self.assertRaises(Exception):
            validate_request({"operation": "order_modify"})

    def test_authority_boundary(self):
        snap = normalize_snapshot(self.results(), snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at="2026-08-14T13:05:00Z", maximum_age_seconds=900)
        self.assertEqual(snap["quantity_authority"], "none")
        self.assertFalse(snap["order_authority"])
        self.assertEqual(validate_instance(snap, ROOT / "manage-us-stock-strategy/schemas/kiwoom-broker-shadow.schema.json"), [])



class AccountBridgeErrorPreservationTests(unittest.TestCase):
    def setUp(self):
        self.guards = ExitStack()
        self.addCleanup(self.guards.close)
        self.network_guards = [self.guards.enter_context(patch(
            target, side_effect=AssertionError("Offline test: network/process forbidden"),
        )) for target in ("socket.socket.connect", "socket.socket.connect_ex",
                          "socket.create_connection", "subprocess.Popen")]
        self.env_loader = self.guards.enter_context(patch.object(bridge, "_load_env_without_echo"))
        self.runtime_session = self.guards.enter_context(patch.object(
            bridge, "_runtime_session", side_effect=AssertionError("Real runtime forbidden"),
        ))

    def tearDown(self):
        for guard in self.network_guards:
            guard.assert_not_called()

    def invoke(self, stdout, *, exit_code=2, operations=("account_deposit_read",)):
        runner = Mock(return_value=subprocess.CompletedProcess(
            ["offline-worker"], exit_code, stdout, "synthetic-secret-in-stderr",
        ))
        with patch.object(Path, "is_file", return_value=True):
            result = bridge.invoke_account_bridge_batch(
                [{"operation": op} for op in operations], runtime=Path("offline-runtime"),
                policy={"external_python_relative_path": "python.exe", "request_timeout_seconds": 1},
                runner=runner,
            )
        runner.assert_called_once()
        self.assertEqual(json.loads(runner.call_args.kwargs["input"]),
                         [{"operation": op} for op in operations])
        return result

    def test_worker_initialization_exception_is_safe(self):
        secret = "SYNTHETIC-ONLY-account-token-secret-authorization-env-value"
        self.runtime_session.side_effect = RuntimeError(secret)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = bridge.external_worker('[{"operation":"account_deposit_read"}]', Path("offline"))
        self.assertEqual(result, {
            "bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
            "failure_stage": "runtime_initialization",
            "order_authority": False,
        })
        self.assertNotIn(secret, json.dumps(result) + stdout.getvalue() + stderr.getvalue())
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")
        self.env_loader.assert_called_once()
        self.runtime_session.assert_called_once()

    def test_worker_validation_and_environment_stages(self):
        invalid = bridge.external_worker("{", Path("offline"))
        self.assertEqual(invalid["failure_stage"], "request_validation")
        self.assertNotIn("exception_type", invalid)
        self.runtime_session.assert_not_called()
        self.env_loader.side_effect = OSError("synthetic-secret")
        result = bridge.external_worker('[{"operation":"account_deposit_read"}]', Path("offline"))
        self.assertEqual(result["failure_stage"], "environment_load")
        self.assertNotIn("exception_type", result)
        self.assertNotIn("synthetic-secret", json.dumps(result))

    def test_exact_historical_error_preserves_classification_and_exit(self):
        payload = {"bridge_status": "KIWOOM_API_UNAVAILABLE",
                   "failure_type": "EMPTY_RESPONSE", "order_authority": False}
        for code in (2, 0):
            with self.subTest(exit_code=code):
                result = self.invoke(json.dumps(payload), exit_code=code)[0]
                self.assertEqual(result["bridge_status"], "KIWOOM_API_UNAVAILABLE")
                self.assertEqual(result["failure_type"], "EMPTY_RESPONSE")
                self.assertEqual(result["child_exit_code"], code)
                self.assertFalse(result["order_authority"])
                self.assertEqual(bridge._sanitize(result, "account_deposit_read"), result)

    def test_error_fanout_mapping_and_sensitive_fields_dropped(self):
        secret = "SYNTHETIC-ONLY-account-token-secret-authorization-env-value"
        payload = {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
                   "order_authority": False, "exception_type": "RuntimeError",
                   "failure_stage": "runtime_initialization",
                   "message": secret, "account_number": secret, "token": secret,
                   "secret": secret, "credential": secret, "authorization": secret,
                   "data": [{"fc_ord_alowa": secret}], "child_exit_code": 99}
        operations = ("account_holdings_read", "account_open_items", "account_deposit_read")
        result = self.invoke(json.dumps(payload), operations=operations)
        self.assertEqual([row["operation"] for row in result], list(operations))
        for row in result:
            self.assertEqual(row["child_exit_code"], 2)
            self.assertNotIn("exception_type", row)
            self.assertEqual(row["failure_stage"], "runtime_initialization")
            self.assertFalse(row["portfolio_mutation"])
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn("synthetic-secret-in-stderr", json.dumps(result))
        snapshot = normalize_snapshot(result, snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                      generated_at="2026-09-19T00:00:00Z", maximum_age_seconds=900)
        self.assertNotEqual(snapshot["cash"]["cash_status"], "VERIFIED_ZERO")

    def test_failure_results_discard_untrusted_metadata_and_account_values(self):
        marker = "SYNTHETIC_ONLY_FAILURE_SECRET"
        for operation in bridge.ACCOUNT_APIS:
            field = bridge.SAFE_FIELDS[operation][0]
            for status in ("KIWOOM_API_UNAVAILABLE", marker):
                for code in (0, 2):
                    with self.subTest(operation=operation, status=status, exit_code=code):
                        row = {"bridge_status": status, "failure_type": "EMPTY_RESPONSE",
                               "failure_stage": "account_batch", "child_exit_code": 99,
                               "runtime_commit": {"token": marker}, "retrieved_at": marker,
                               "data": [{field: {"credential": marker}}],
                               "pagination": {"api_id": {"token": marker}, "pages": marker,
                                              "complete": True, "exhausted": True}}
                        result = self.invoke(json.dumps({"results": [row]}), exit_code=code,
                                             operations=(operation,))[0]
                        self.assertNotIn(marker, json.dumps(result))
                        self.assertEqual(result["bridge_status"], status if status != marker
                                         else "BRIDGE_OUTPUT_INVALID")
                        self.assertEqual(result["failure_type"], "EMPTY_RESPONSE")
                        self.assertEqual(result["failure_stage"], "account_batch")
                        self.assertEqual(result["child_exit_code"], code)
                        self.assertIsNone(result["runtime_commit"])
                        self.assertIsNone(result["retrieved_at"])
                        self.assertEqual(result["data"], [])
                        self.assertEqual(result["pagination"], {"complete": False, "exhausted": False})
                        self.assertFalse(result["order_authority"])

    def test_sanitizer_detected_failure_discards_untrusted_payload(self):
        marker = "SYNTHETIC_ONLY_FAILURE_SECRET"
        for status in ("PASS", "PARTIAL"):
            with self.subTest(status=status):
                row = {"bridge_status": status, "runtime_commit": marker, "retrieved_at": marker,
                       "data": [{"stk_cd": {"credential": marker}}, None],
                       "pagination": {"api_id": marker, "pages": marker,
                                      "complete": True, "exhausted": True}}
                result = self.invoke(json.dumps({"results": [row]}), exit_code=0,
                                     operations=("account_open_items",))[0]
                self.assertEqual(result["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")
                self.assertEqual(result["failure_type"], "SCHEMA_MISMATCH")
                self.assertNotIn(marker, json.dumps(result))
                self.assertEqual(result["data"], [])
                self.assertEqual(result["pagination"], {"complete": False, "exhausted": False})


    def test_malformed_json_and_unexpected_top_level_remain_invalid(self):
        for stdout in ("", "{", "[]", "null"):
            with self.subTest(stdout=stdout):
                result = self.invoke(stdout)[0]
                self.assertEqual(result["bridge_status"], "BRIDGE_OUTPUT_INVALID")
                self.assertEqual(result["failure_type"], "LOCAL_PROTOCOL_FAILURE")
                self.assertEqual(result["child_exit_code"], 2)

    def test_missing_success_results_type_and_count_remain_batch_errors(self):
        for payload in (
            {"bridge_status": "PASS"},
            {"bridge_status": "PASS", "results": {}},
            {"bridge_status": "PASS", "results": []},
            {"bridge_status": "PASS", "results": [{}, {}]},
            {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
             "order_authority": False, "results": []},
            {"bridge_status": "KIWOOM_API_UNAVAILABLE", "order_authority": False},
            {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
             "order_authority": True},
        ):
            with self.subTest(payload=payload):
                result = self.invoke(json.dumps(payload))[0]
                self.assertEqual(result["bridge_status"], "BRIDGE_BATCH_OUTPUT_INVALID")
                self.assertEqual(result["failure_type"], "LOCAL_PROTOCOL_FAILURE")

    def test_single_success_contract_unchanged(self):
        row = {"bridge_status": "PASS", "operation": "account_deposit_read",
               "data": [{"crnc_code": "USD", "fc_ord_alowa": "123"}],
               "runtime_commit": "a" * 40, "retrieved_at": "2026-09-19T00:00:00Z",
               "pagination": {"api_id": "ust21110", "pages": 1, "complete": True,
                              "exhausted": True, "secret_fields_retained": False},
               "order_authority": False}
        result = self.invoke(json.dumps({"bridge_status": "PASS", "results": [row]}), exit_code=0)
        self.assertEqual(result[0]["bridge_status"], "PASS")
        self.assertEqual(result[0]["operation"], "account_deposit_read")
        self.assertEqual(result[0]["data"][0]["fc_ord_alowa"], "123")
        self.assertEqual(result[0]["runtime_commit"], "a" * 40)
        self.assertEqual(result[0]["retrieved_at"], row["retrieved_at"])
        self.assertEqual(result[0]["pagination"], row["pagination"])
        self.assertEqual(result, [bridge._sanitize(row, "account_deposit_read")])
        self.assertNotIn("child_exit_code", result[0])
        self.assertNotIn("exception_type", result[0])

    def test_multiple_success_order_and_mapping_unchanged(self):
        rows = KiwoomBrokerShadowTests().results()
        for row in rows:
            row["runtime_commit"] = "a" * 40
            row["pagination"] = {"api_id": bridge.ACCOUNT_APIS[row["operation"]][0],
                                 "pages": 1, "complete": True, "exhausted": True,
                                 "secret_fields_retained": False}
        operations = tuple(row["operation"] for row in rows)
        result = self.invoke(json.dumps({"bridge_status": "PASS", "results": rows}),
                             exit_code=0, operations=operations)
        self.assertEqual(result, [bridge._sanitize(row, op) for row, op in zip(rows, operations)])
        self.assertEqual([row["operation"] for row in result], list(operations))
        self.assertEqual(result[0]["data"][0]["stk_cd"], "NBIS")
        self.assertEqual(result[1]["data"][0]["fc_ord_alowa"], "0")
        self.assertEqual(result[2]["data"][0]["d1_usd_sell_excta"], "5000")
        self.assertEqual(result[3]["data"], [])
        for actual, original in zip(result, rows):
            self.assertEqual(actual["runtime_commit"], original["runtime_commit"])
            self.assertEqual(actual["retrieved_at"], original["retrieved_at"])
            self.assertEqual(actual["pagination"], original["pagination"])

    def test_exception_metadata_rejects_message_shaped_values(self):
        result = bridge._sanitize({
            "bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
            "exception_type": "RuntimeError: synthetic-secret", "failure_stage": "synthetic-secret",
            "child_exit_code": True,
        }, "account_deposit_read")
        self.assertNotIn("exception_type", result)
        self.assertNotIn("failure_stage", result)
        self.assertNotIn("child_exit_code", result)

    def test_untrusted_diagnostic_strings_are_not_exposed(self):
        marker = "SYNTHETIC_PRIVATE_TOKEN_12345678"
        error = {"bridge_status": "KIWOOM_API_UNAVAILABLE",
                 "failure_type": "Authorization: " + marker,
                 "exception_type": marker, "message": marker,
                 "failure_stage": marker, "order_authority": False}
        for payload in (error, {"results": [error]}):
            with self.subTest(envelope="results" in payload):
                result = self.invoke(json.dumps(payload))[0]
                self.assertEqual(result["bridge_status"], "KIWOOM_API_UNAVAILABLE")
                self.assertEqual(result["failure_type"], "EMPTY_RESPONSE")
                self.assertNotIn(marker, json.dumps(result))
                self.assertNotIn("exception_type", result)
                self.assertNotIn("failure_stage", result)
        result = self.invoke(json.dumps({"results": [{**error, "bridge_status": marker}]}))[0]
        self.assertEqual(result["bridge_status"], "BRIDGE_OUTPUT_INVALID")
        self.assertNotIn(marker, json.dumps(result))

    def test_custom_exception_class_and_message_are_not_exposed(self):
        marker = "SYNTHETIC_PRIVATE_TOKEN_12345678"
        exception = type(marker, (bridge.BridgeError,), {})(marker, marker)
        self.runtime_session.side_effect = exception
        result = bridge.external_worker('[{"operation":"account_deposit_read"}]', Path("offline"))
        self.assertEqual(result["bridge_status"], "KIWOOM_API_UNAVAILABLE")
        self.assertEqual(result["failure_type"], "EMPTY_RESPONSE")
        self.assertEqual(result["failure_stage"], "runtime_initialization")
        self.assertNotIn(marker, json.dumps(result))
        self.assertNotIn("exception_type", result)
        self.assertNotIn(marker, json.dumps(self.invoke(json.dumps(result))))

        # Exercise the per-operation Worker error path through the real page reader.
        fetch = Mock(side_effect=exception)
        self.runtime_session.side_effect = None
        self.runtime_session.return_value = {
            "client": SimpleNamespace(fetch_page=fetch), "pacer": Mock(), "commit": "a" * 40,
            "maximum_attempts": 1, "maximum_history_pages": 1,
            "immediate_open_failure_types": set(), "retryable_failure_types": set(),
        }
        result = bridge.external_worker('[{"operation":"account_deposit_read"}]', Path("offline"))
        fetch.assert_called_once()
        self.assertEqual(result["results"][0]["bridge_status"], "KIWOOM_API_UNAVAILABLE")
        self.assertEqual(result["results"][0]["failure_type"], "EMPTY_RESPONSE")
        self.assertNotIn(marker, json.dumps(result))
        self.assertNotIn(marker, json.dumps(self.invoke(json.dumps(result), exit_code=0)))

    def test_existing_fixed_failure_classifications_are_preserved(self):
        for failure_type in ("EMPTY_RESPONSE", "API_RESPONSE_ERROR", "SCHEMA_MISMATCH", "HTTP_429",
                             "AUTHENTICATION_FAILURE", "TIMEOUT", "LOCAL_PROTOCOL_FAILURE",
                             "LOCAL_TRANSPORT_FAILURE", "LOCAL_RUNTIME_UNAVAILABLE"):
            with self.subTest(failure_type=failure_type):
                result = self.invoke(json.dumps({"bridge_status": "KIWOOM_API_UNAVAILABLE",
                    "failure_type": failure_type, "order_authority": False}))[0]
                self.assertEqual(result["failure_type"], failure_type)
                self.assertEqual(result["child_exit_code"], 2)

    def test_result_exit_code_comes_only_from_parent(self):
        row = {"bridge_status": "KIWOOM_API_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE",
               "child_exit_code": 0}
        for code in (2, -1, 0):
            with self.subTest(actual_exit=code):
                result = self.invoke(json.dumps({"results": [row]}), exit_code=code)[0]
                self.assertEqual(result["child_exit_code"], code)
                self.assertEqual(result["bridge_status"], "KIWOOM_API_UNAVAILABLE")
        success = {"bridge_status": "PASS", "data": [], "child_exit_code": 99}
        result = self.invoke(json.dumps({"results": [success]}), exit_code=0)[0]
        self.assertEqual(result["bridge_status"], "PASS")
        self.assertNotIn("child_exit_code", result)

    def test_nonzero_success_payload_blocks_both_sell_paths(self):
        from test_k2_bridge_evidence_integrity import K2BridgeEvidenceIntegrityTests, NOW

        case = K2BridgeEvidenceIntegrityTests(methodName="runTest")
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.addCleanup(case.tearDown)
        for code in (2, -1):
            for status in ("PASS", "PARTIAL"):
                with self.subTest(actual_exit=code, status=status):
                    row = {"bridge_status": status, "data": [], "retrieved_at": NOW,
                           "pagination": {"api_id": "ust21050", "pages": 1,
                                          "complete": True, "exhausted": True},
                           "child_exit_code": 0, "order_authority": False}
                    result = self.invoke(json.dumps({"bridge_status": "PASS", "results": [row]}),
                                         exit_code=code, operations=("account_open_items",))[0]
                    self.assertEqual(result["bridge_status"], "BRIDGE_TRANSPORT_FAILURE")
                    self.assertEqual(result["failure_type"], "LOCAL_TRANSPORT_FAILURE")
                    self.assertEqual(result["child_exit_code"], code)
                    case.assert_both_blocked(result)

    def test_nonzero_success_batch_cannot_verify_empty_accounts_or_zero_cash(self):
        from run_manual_portfolio_analysis import _normalize_broker_state

        rows = KiwoomBrokerShadowTests().results()
        rows[0]["data"] = []
        operations = tuple(row["operation"] for row in rows)
        result = self.invoke(json.dumps({"bridge_status": "PASS", "results": rows}),
                             exit_code=2, operations=operations)
        self.assertEqual([row["operation"] for row in result], list(operations))
        self.assertTrue(all(row["child_exit_code"] == 2 for row in result))
        snapshot = normalize_snapshot(result, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                      generated_at="2026-08-14T13:00:00Z", maximum_age_seconds=900)
        self.assertFalse(snapshot["scope_complete"])
        self.assertTrue(all(status == "BRIDGE_TRANSPORT_FAILURE"
                            for status in snapshot["operation_statuses"].values()))
        self.assertEqual(snapshot["cash"]["cash_status"], "UNVERIFIED")
        self.assertIsNone(snapshot["cash"]["settled_available_cash"])
        self.assertIsNone(snapshot["cash"]["order_available_cash"])
        broker, status = _normalize_broker_state(result, observed_at="2026-08-14T13:00:00Z",
                                                maximum_age_seconds=900)
        self.assertEqual(status, "UNAVAILABLE")
        self.assertFalse(broker["scope_complete"])
        self.assertNotIn(broker["open_order_evidence"]["bridge_status"], {"PASS", "PARTIAL"})
        self.assertFalse(broker["canonical_apply"])
        self.assertFalse(broker["order_authority"])


if __name__ == "__main__":
    unittest.main()
