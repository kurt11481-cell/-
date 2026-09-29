#!/usr/bin/env python3
"""Offline K2 evidence-contract tests; no broker transport or execution."""

from __future__ import annotations

import copy
import json
import unittest
from contextlib import ExitStack
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_portfolio_decision_order_intent as fixtures
from kiwoom_account_readonly_bridge import BridgeError, _fetch_account_page
from portfolio_decision_dashboard import _sell_readiness_evidence, compile_dashboard
from portfolio_decision_order_intent import compile_order_intent_artifact
from run_manual_portfolio_analysis import _normalize_broker_state
from validation_common import validate_instance


class K2EvidenceContractTests(unittest.TestCase):
    setUp = fixtures.OrderIntentOnlyTests.setUp
    inputs = fixtures.ManualSellRuleTests.inputs
    row = fixtures.ManualSellRuleTests.row
    instruction = staticmethod(fixtures.OrderIntentOnlyTests.instruction)
    assert_blocked = fixtures.ManualSellRuleTests.assert_blocked

    def classify(self, args):
        return _sell_readiness_evidence(
            args["evidence"], "PGR", 10, 5, datetime.fromisoformat(args["now"]),
        )

    @staticmethod
    def broker(args):
        return args["evidence"]["broker_observed_state"]

    def open_evidence(self, args):
        return self.broker(args)["open_order_evidence"]

    def available_case(self, value, reason=None, *, missing=False):
        args, _ = self.inputs()
        holding = self.broker(args)["holdings"][0]
        if missing:
            holding.pop("available_shares")
        else:
            holding["available_shares"] = value
        if reason:
            self.assert_blocked(args, reason)
        else:
            self.assertEqual(self.row(args)["state"], "ORDER_INSTRUCTION_READY")
            self.assertEqual(self.classify(args)["available_shares_status"], "VERIFIED")

    def test_a1_available_ten_sell_five(self):
        self.available_case(10)

    def test_a2_available_equals_sell(self):
        self.available_case(5)

    def test_a3_available_below_sell(self):
        self.available_case(4, "AVAILABLE_SHARES_INSUFFICIENT")

    def test_a4_available_zero(self):
        self.available_case(0, "AVAILABLE_SHARES_INSUFFICIENT")

    def test_a5_available_null(self):
        self.available_case(None, "AVAILABLE_SHARES_NOT_VERIFIED")

    def test_a6_available_missing(self):
        self.available_case(None, "AVAILABLE_SHARES_NOT_VERIFIED", missing=True)

    def test_a7_invalid_nonfinite_negative_or_contradictory(self):
        for value in (True, False, "invalid", "", {}, [], float("nan"), float("inf"),
                      -float("inf"), "NaN", "Infinity", -1, 11):
            with self.subTest(value=repr(value)):
                self.available_case(value, "AVAILABLE_SHARES_NOT_VERIFIED")

    def test_a8_held_settled_and_cost_never_substitute_available(self):
        args, _ = self.inputs()
        holding = self.broker(args)["holdings"][0]
        holding.update(held_quantity=10, settled_quantity=10, average_cost=100)
        holding.pop("available_shares")
        self.assert_blocked(args, "AVAILABLE_SHARES_NOT_VERIFIED")

    def test_available_reuses_existing_decimal_numeric_semantics(self):
        for value in (5.0, "5", "5.0", 5.5):
            with self.subTest(value=value):
                self.available_case(value)

    def test_holding_duplicate_mismatch_and_operation_error_block(self):
        for case in ("duplicate", "quantity", "operation", "status"):
            args, _ = self.inputs()
            broker = self.broker(args)
            if case == "duplicate":
                broker["holdings"].append(copy.deepcopy(broker["holdings"][0]))
            elif case == "quantity":
                broker["holdings"][0]["held_quantity"] = 11
            elif case == "operation":
                broker["operation_statuses"]["account_holdings_read"] = "UNKNOWN"
            else:
                broker["status"] = "INCOMPLETE"
            with self.subTest(case=case):
                self.assert_blocked(args, "AVAILABLE_SHARES_NOT_VERIFIED")

    def test_o1_verified_complete_fresh_empty(self):
        args, _ = self.inputs()
        self.assertEqual(self.classify(args)["open_order_conflict_status"], "VERIFIED_NONE")
        self.assertEqual(self.row(args)["state"], "ORDER_INSTRUCTION_READY")

    def test_o2_nonempty_blocks_without_interpreting_provider_fields(self):
        for rows in ([{}], [{"stk_cd": "UNRELATED", "ord_remnq": "0", "ord_stat": "DONE"}]):
            args, _ = self.inputs()
            self.open_evidence(args)["data"] = rows
            self.assert_blocked(args, "OPEN_ORDER_CONFLICT_PRESENT")

    def test_o3_api_error_blocks(self):
        args, _ = self.inputs()
        self.open_evidence(args)["bridge_status"] = "KIWOOM_API_RESPONSE_ERROR"
        self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_o4_unknown_blocks(self):
        args, _ = self.inputs()
        self.open_evidence(args)["bridge_status"] = "UNKNOWN"
        self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_o5_missing_operation_or_evidence_blocks(self):
        for field in ("operation", "bridge_status", "data", "pagination", "retrieved_at", "whole"):
            args, _ = self.inputs()
            if field == "whole":
                self.broker(args).pop("open_order_evidence")
            else:
                self.open_evidence(args).pop(field)
            with self.subTest(field=field):
                self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_o6_partial_and_invalid_pagination_block(self):
        for field, value in (("complete", False), ("exhausted", False), ("complete", "true"),
                             ("pages", 0), ("pages", True), ("pages", None), ("api_id", "wrong")):
            args, _ = self.inputs()
            self.open_evidence(args)["pagination"][field] = value
            with self.subTest(field=field, value=value):
                self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")
        for status in ("PARTIAL", "WARNING"):
            args, _ = self.inputs()
            self.open_evidence(args)["bridge_status"] = status
            self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_o7_stale_own_timestamp_despite_fresh_snapshot_blocks(self):
        for stamp in ("2026-08-21T13:44:59+00:00", "2026-08-21T13:45:00+00:00"):
            args, _ = self.inputs()
            self.open_evidence(args)["retrieved_at"] = stamp
            self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_STALE")

    def test_o8_error_plus_empty_is_never_verified_none(self):
        args, _ = self.inputs()
        broker = self.broker(args)
        broker["operation_statuses"]["account_open_items"] = "KIWOOM_API_RESPONSE_ERROR"
        self.open_evidence(args).update(bridge_status="KIWOOM_API_RESPONSE_ERROR", data=[])
        self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")
        self.assertEqual(self.classify(args)["open_order_conflict_status"], "NOT_VERIFIED")

    def test_o9_user_confirmation_cannot_replace_broker_evidence(self):
        args, _ = self.inputs()
        self.broker(args).pop("open_order_evidence")
        before = self.row(args)
        self.broker(args)["user_confirmation"] = {
            "historical_open_orders": 0, "same_session_open_orders": 0, "confirmed": True,
        }
        after = self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")
        self.assertEqual(before["blockers"], after["blockers"])

    def test_open_rows_and_timestamps_invalid_or_future_block(self):
        for value in (None, {}, "", [None], ["row"]):
            args, _ = self.inputs()
            self.open_evidence(args)["data"] = value
            self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")
        for stamp in (None, "invalid", "2026-08-21T14:00:00", "2026-08-21T14:00:01+00:00"):
            args, _ = self.inputs()
            self.open_evidence(args)["retrieved_at"] = stamp
            self.assert_blocked(args)
        args, _ = self.inputs()
        self.broker(args)["operation_statuses"].pop("account_open_items")
        self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_open_expiry_shortens_intent_and_is_rechecked_at_evaluation(self):
        args, _ = self.inputs()
        self.open_evidence(args)["retrieved_at"] = "2026-08-21T13:55:00+00:00"
        row = self.row(args)
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY")
        self.assertEqual(row["valid_until"], "2026-08-21T14:10:00+00:00")
        args["now"] = "2026-08-21T14:09:59+00:00"
        self.assertEqual(self.row(args)["state"], "ORDER_INSTRUCTION_READY")
        args["now"] = "2026-08-21T14:10:00+00:00"
        stale = self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_STALE")
        self.assertEqual(row["valid_until"], stale["valid_until"])
        self.assertEqual(row["instruction_id"], stale["instruction_id"])

    def test_c1_c2_c3_combined_gates(self):
        for available, status, expected in ((5, "PASS", "ORDER_INSTRUCTION_READY"),
                                             (4, "PASS", "ORDER_BLOCKED"),
                                             (5, "KIWOOM_API_RESPONSE_ERROR", "ORDER_BLOCKED")):
            args, _ = self.inputs()
            self.broker(args)["holdings"][0]["available_shares"] = available
            self.open_evidence(args)["bridge_status"] = status
            self.assertEqual(self.row(args)["state"], expected)

    def test_c4_risk_failure_is_not_overridden(self):
        args, _ = self.inputs()
        args["report"]["portfolio"]["target_reference_risk"]["hard_cap_violations"] = ["FIXTURE_CAP"]
        self.assertEqual(self.classify(args)["blockers"], [])
        self.assert_blocked(args, "TARGET_HARD_CAP_VIOLATION")

    def test_c5_approval_session_identity_failure_is_not_overridden(self):
        for case in ("approval", "session", "identity"):
            args, authority = self.inputs()
            if case == "approval":
                args["plan"]["positions"][0]["order_intent_terms"]["terms_status"] = "UNAPPROVED"
            elif case == "session":
                authority.market_phase = "POST_CORE"
            else:
                args["integrated_snapshot"] = None
            self.assertEqual(self.classify(args)["blockers"], [])
            with self.subTest(case=case):
                self.assert_blocked(args)

    def test_buy_semantics_unchanged_when_sell_evidence_absent(self):
        case = fixtures.OrderIntentOnlyTests(methodName="runTest")
        case.setUp()
        source = fixtures.source_for_buy()
        source["broker_observed_state"].pop("open_order_evidence")
        source["broker_observed_state"]["operation_statuses"]["account_open_items"] = "UNKNOWN"
        for holding in source["broker_observed_state"]["holdings"]:
            holding.pop("available_shares")
        row = self.instruction(case.build(source), "JPM")
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY")

    def test_fixed_limit_sell_also_requires_evidence(self):
        case = fixtures.OrderIntentOnlyTests(methodName="runTest")
        case.setUp()
        source = fixtures.source_for_sell()
        source["broker_observed_state"].pop("open_order_evidence")
        row = self.instruction(case.build(source, fixtures.sell_plan()), "PGR")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("OPEN_ORDER_EVIDENCE_NOT_VERIFIED", row["blockers"])

    def test_missing_sell_evidence_is_visible_even_with_deadband(self):
        args, _ = self.inputs()
        args["report"]["portfolio"]["current_risk"]["hard_cap_violations"] = []
        args["report"]["portfolio"]["positions"][0]["deadband_status"] = "NO_TRADE_PREFERRED"
        self.broker(args).pop("open_order_evidence")
        self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_dashboard_classification_and_intent_recheck(self):
        args, authority = self.inputs()
        self.assertEqual(args["report"]["evidence"]["sell_readiness"]["PGR"]["blockers"], [])
        self.open_evidence(args)["bridge_status"] = "ERROR"
        report, validation = compile_dashboard(
            args["evidence"], args["plan"], self.policy, registry=self.registry,
            generated_at=args["now"], evidence_sha256=args["input_hashes"]["portfolio_evidence"],
            current_session_context=args["current_session_context"],
            current_session_authority_resolver=lambda *a, **k: authority,
        )
        self.assertIn("OPEN_ORDER_EVIDENCE_NOT_VERIFIED",
                      report["evidence"]["sell_readiness"]["PGR"]["blockers"])
        self.assertEqual(validation["status"], "PASS")
        # Even a previous successful Dashboard classification cannot bless changed evidence.
        self.assert_blocked(args, "OPEN_ORDER_EVIDENCE_NOT_VERIFIED")

    def test_no_network_or_gateway_no_input_mutation_and_schema_valid(self):
        args, _ = self.inputs()
        before = copy.deepcopy({key: value for key, value in args.items() if not callable(value)})
        with ExitStack() as stack:
            spies = [stack.enter_context(patch(name, side_effect=AssertionError("Network forbidden"))) for name in (
                "socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                "urllib.request.urlopen", "http.client.HTTPConnection.request",
                "kiwoom_account_readonly_bridge.invoke_account_bridge_batch",
                "kiwoom_runtime_bridge.invoke_bridge_batch", "future_order_shadow.build_gateway_dry_run",
            )]
            artifact = compile_order_intent_artifact(**args)
            for spy in spies:
                spy.assert_not_called()
        self.assertEqual(before, {key: value for key, value in args.items() if not callable(value)})
        self.assertEqual(validate_instance(artifact, fixtures.ORDER_INTENT_SCHEMA), [])
        for item in (artifact, artifact["instructions"][0]):
            self.assertFalse(item["order_authority"])
            self.assertFalse(item["automatic_order"])
            self.assertFalse(item["portfolio_mutation"])
            self.assertIsNone(item["execution_quantity"])
            self.assertEqual(item["broker_submission"], "DISABLED")


class K2AcquisitionTests(unittest.TestCase):
    def results(self):
        reader = fixtures._fixture._manual_module.account_reader_for(
            {"PGR": 10}, {"PGR": 100}, retrieved_at="2026-08-21T14:00:00+00:00",
        )
        return reader([{"operation": operation} for operation in (
            "account_holdings_read", "account_deposit_read", "account_open_items",
        )])

    def normalize(self, results):
        return _normalize_broker_state(
            results, observed_at="2026-08-21T14:00:00+00:00", maximum_age_seconds=900,
        )[0]

    def test_provider_available_rows_status_timestamp_and_pagination_preserved(self):
        results = self.results()
        results[0]["data"][0]["sell_alowq"] = "4"
        original = results[-1]
        original["data"] = [{"stk_cd": "PGR", "ord_qty": "2", "ord_remnq": "1",
                             "ord_stat": "UNINTERPRETED", "account_number": "FAKE_PRIVATE"}]
        original["access_token"] = "FAKE_PRIVATE"
        before = copy.deepcopy(results)
        broker = self.normalize(results)
        self.assertEqual(broker["holdings"][0]["available_shares"], 4)
        preserved = broker["open_order_evidence"]
        for field in ("operation", "bridge_status", "retrieved_at"):
            self.assertEqual(preserved[field], original[field])
        for field in ("api_id", "complete", "exhausted", "pages"):
            self.assertEqual(preserved["pagination"][field], original["pagination"][field])
        self.assertEqual(preserved["data"][0]["ord_remnq"], "1")
        self.assertNotIn("FAKE_PRIVATE", json.dumps(broker))
        self.assertEqual(results, before)

    def test_error_empty_rows_preserves_error_and_fails_closed(self):
        results = self.results()
        results[-1].update(bridge_status="KIWOOM_API_RESPONSE_ERROR", data=[])
        broker = self.normalize(results)
        self.assertEqual(broker["open_order_evidence"]["bridge_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(broker["open_order_evidence"]["data"], [])
        self.assertEqual(broker["operation_statuses"]["account_open_items"], "KIWOOM_API_RESPONSE_ERROR")

    def test_malformed_rows_are_not_sanitized_into_verified_empty(self):
        for data in (None, {}, [None], ["bad"]):
            results = self.results()
            results[-1]["data"] = data
            broker = self.normalize(results)
            self.assertIsNone(broker["open_order_evidence"]["data"])
            self.assertEqual(broker["open_order_evidence"]["bridge_status"], "KIWOOM_SCHEMA_MISMATCH")

    def test_missing_duplicate_and_partial_acquisition_cannot_establish_zero(self):
        results = self.results()
        self.assertIsNone(self.normalize(results[:-1])["open_order_evidence"])
        self.assertIsNone(self.normalize(results + [copy.deepcopy(results[-1])])["open_order_evidence"])
        results[-1].update(bridge_status="PARTIAL", data=[{"stk_cd": "PGR"}])
        results[-1]["pagination"].update(complete=False, exhausted=False)
        preserved = self.normalize(results)["open_order_evidence"]
        self.assertEqual(preserved["bridge_status"], "PARTIAL")
        self.assertFalse(preserved["pagination"]["complete"])
        self.assertEqual(preserved["data"][0]["stk_cd"], "PGR")

    def test_return_code_twenty_remains_api_response_error_offline(self):
        client = Mock()
        client.fetch_page.return_value = SimpleNamespace(body={"return_code": 20, "result_list": []})
        session = {"client": client, "pacer": Mock(), "maximum_attempts": 1,
                   "immediate_open_failure_types": set(), "retryable_failure_types": set()}
        with self.assertRaises(BridgeError) as caught:
            _fetch_account_page(session, "account_open_items", {}, cont_yn=None, next_key=None)
        self.assertEqual(caught.exception.status, "KIWOOM_API_RESPONSE_ERROR")
        broker_results = self.results()
        broker_results[-1].update(bridge_status=caught.exception.status, data=[])
        broker = self.normalize(broker_results)
        evidence = {"broker_observed_state": broker, "decision_as_of": broker["as_of"],
                    "broker_snapshot_as_of": broker["as_of"]}
        classified = _sell_readiness_evidence(evidence, "PGR", 10, 5, datetime.fromisoformat(broker["as_of"]))
        self.assertIn("OPEN_ORDER_EVIDENCE_NOT_VERIFIED", classified["blockers"])


if __name__ == "__main__":
    unittest.main()
