#!/usr/bin/env python3
"""Offline residual P8 attacks and coherent runtime continuation controls."""

from dataclasses import dataclass
from types import SimpleNamespace
import unittest

import test_k2_bridge_evidence_integrity as pipeline
from portfolio_decision_order_intent import compile_order_intent_artifact


@dataclass(frozen=True)
class RuntimeContinuation:
    """Portable fixture matching the inspected Kiwoom Continuation dataclass."""

    has_next: bool
    next_key: str | None
    cont_yn: str | None


class K2ContinuationCoherenceTests(unittest.TestCase):
    setUp = pipeline.K2BridgeEvidenceIntegrityTests.setUp
    tearDown = pipeline.K2BridgeEvidenceIntegrityTests.tearDown
    inputs = pipeline.K2BridgeEvidenceIntegrityTests.inputs
    instruction = staticmethod(pipeline.K2BridgeEvidenceIntegrityTests.instruction)
    worker_result = pipeline.K2BridgeEvidenceIntegrityTests.worker_result
    invoke_sanitizer = pipeline.K2BridgeEvidenceIntegrityTests.invoke_sanitizer
    final_sell = pipeline.K2BridgeEvidenceIntegrityTests.final_sell
    assert_both_blocked = pipeline.K2BridgeEvidenceIntegrityTests.assert_both_blocked

    def contradiction(self, metadata):
        for representation in (metadata, SimpleNamespace(**metadata)):
            # A valid following page proves the bridge rejects the contradiction
            # itself, rather than merely running out of mock responses.
            pages = [pipeline.page([], representation),
                     pipeline.page([], RuntimeContinuation(False, None, None))]
            with self.subTest(boundary="read_pages", representation=type(representation).__name__):
                offline_session = pipeline.session(pages)
                _, pagination = pipeline.bridge._read_pages(offline_session, "account_open_items")
                self.assertFalse(pagination["complete"])
                self.assertFalse(pagination["exhausted"])
                self.assertEqual(offline_session["client"].fetch_page.call_count, 1)
            raw, offline_session = self.worker_result(pages)
            result = self.invoke_sanitizer(raw)
            with self.subTest(boundary="worker", representation=type(representation).__name__):
                self.assertEqual(result["bridge_status"], "PARTIAL")
                self.assertFalse(result["pagination"]["complete"])
                self.assertFalse(result["pagination"]["exhausted"])
                self.assertEqual(offline_session["client"].fetch_page.call_count, 1)
            self.assert_both_blocked(result)

    def test_p8_1_n_with_unconsumed_token(self):
        self.contradiction({"cont_yn": "N", "next_key": "UNCONSUMED_PAGE"})

    def test_p8_2_has_next_true_n_null_token(self):
        self.contradiction({"has_next": True, "cont_yn": "N", "next_key": None})

    def test_p8_3_has_next_true_null_indicator_null_token(self):
        self.contradiction({"has_next": True, "cont_yn": None, "next_key": None})

    def test_p8_4_has_next_false_y_valid_token(self):
        self.contradiction({"has_next": False, "cont_yn": "Y", "next_key": "UNCONSUMED_PAGE"})

    def test_p8_5_all_terminal_indicators_reject_tokens_and_has_next_true(self):
        for terminal in (None, "", "N", "n"):
            with self.subTest(terminal=terminal):
                self.contradiction({"has_next": False, "cont_yn": terminal, "next_key": "UNCONSUMED_PAGE"})
                self.contradiction({"has_next": True, "cont_yn": terminal, "next_key": None})

    def test_p8_6_continue_indicators_require_token_and_consistent_has_next(self):
        for indicator in ("Y", "2", "MORE", "TRUE", "y"):
            with self.subTest(indicator=indicator):
                self.contradiction({"has_next": False, "cont_yn": indicator, "next_key": "UNCONSUMED_PAGE"})
                self.contradiction({"has_next": True, "cont_yn": indicator})
                for token in (None, "", " ", 42, True, [], {}):
                    with self.subTest(token=token):
                        self.contradiction({"has_next": True, "cont_yn": indicator, "next_key": token})

    def test_p8_7_has_next_must_be_boolean_when_present(self):
        for invalid in (None, 0, 1, "false", "true", [], {}):
            with self.subTest(has_next=invalid):
                self.contradiction({"has_next": invalid, "cont_yn": "N", "next_key": None})
                self.contradiction({"has_next": invalid, "cont_yn": "Y", "next_key": "UNCONSUMED_PAGE"})
        for invalid in (42, True, [], {}, "UNKNOWN"):
            with self.subTest(cont_yn=invalid):
                self.contradiction({"has_next": False, "cont_yn": invalid, "next_key": None})

    def assert_terminal_ready(self, continuation):
        raw, offline_session = self.worker_result([pipeline.page([], continuation)])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "PASS")
        self.assertTrue(result["pagination"]["complete"])
        self.assertTrue(result["pagination"]["exhausted"])
        self.assertEqual(result["pagination"]["pages"], 1)
        self.assertEqual(offline_session["client"].fetch_page.call_count, 1)
        for sell_path in ("manual_best_bid", "fixed_limit"):
            classification, intent = self.final_sell(result, sell_path=sell_path)
            self.assertEqual(classification["open_order_conflict_status"], "VERIFIED_NONE")
            self.assertEqual(intent["state"], "ORDER_INSTRUCTION_READY", intent["blockers"])

    def test_pc1_legitimate_runtime_false_none_none_terminal(self):
        self.assert_terminal_ready(RuntimeContinuation(False, None, None))
        self.assert_terminal_ready({"has_next": False, "cont_yn": None, "next_key": None})

    def test_pc2_legitimate_n_without_token_terminal(self):
        self.assert_terminal_ready(RuntimeContinuation(False, None, "N"))
        self.assert_terminal_ready({"has_next": False, "cont_yn": "N", "next_key": None})

    def test_pc3_pc4_coherent_continue_then_actual_final_page(self):
        for indicator in ("Y", "2", "MORE", "TRUE"):
            raw, offline_session = self.worker_result([
                pipeline.page([], RuntimeContinuation(True, "offline-cursor", indicator)),
                pipeline.page([], RuntimeContinuation(False, None, None)),
            ])
            result = self.invoke_sanitizer(raw)
            self.assertEqual(result["bridge_status"], "PASS")
            self.assertTrue(result["pagination"]["complete"])
            self.assertTrue(result["pagination"]["exhausted"])
            self.assertEqual(result["pagination"]["pages"], 2)
            self.assertEqual(offline_session["client"].fetch_page.call_count, 2)
            next_call = offline_session["client"].fetch_page.call_args_list[1].kwargs
            self.assertEqual(next_call["cont_yn"], indicator)
            self.assertEqual(next_call["next_key"], "offline-cursor")
            for sell_path in ("manual_best_bid", "fixed_limit"):
                classification, intent = self.final_sell(result, sell_path=sell_path)
                self.assertEqual(classification["open_order_conflict_status"], "VERIFIED_NONE")
                self.assertEqual(intent["state"], "ORDER_INSTRUCTION_READY", intent["blockers"])

    def test_coherent_continue_still_respects_page_limit_and_no_progress(self):
        raw, _ = self.worker_result([
            pipeline.page([], RuntimeContinuation(True, "cursor", "Y")),
        ], maximum_pages=1)
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "PARTIAL")
        self.assert_both_blocked(result)
        raw, _ = self.worker_result([
            pipeline.page([], RuntimeContinuation(True, "cursor", "Y")),
            pipeline.page([], RuntimeContinuation(True, "cursor", "Y")),
        ])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "KIWOOM_PAGINATION_NO_PROGRESS")
        self.assert_both_blocked(result)

    def test_later_page_contradiction_never_completes(self):
        raw, offline_session = self.worker_result([
            pipeline.page([], RuntimeContinuation(True, "first-cursor", "Y")),
            pipeline.page([], RuntimeContinuation(False, "UNCONSUMED_PAGE", "N")),
            pipeline.page([], RuntimeContinuation(False, None, None)),
        ])
        result = self.invoke_sanitizer(raw)
        self.assertEqual(result["bridge_status"], "PARTIAL")
        self.assertEqual(offline_session["client"].fetch_page.call_count, 2)
        self.assert_both_blocked(result)

    def test_freshness_microsecond_boundary_and_earliest_expiry_unchanged(self):
        args, _ = self.inputs()
        args["evidence"]["broker_observed_state"]["open_order_evidence"]["retrieved_at"] = "2026-08-21T13:55:00+00:00"
        args["now"] = "2026-08-21T14:09:59.999999+00:00"
        ready = self.instruction(compile_order_intent_artifact(**args), "PGR")
        self.assertEqual(ready["state"], "ORDER_INSTRUCTION_READY", ready["blockers"])
        self.assertEqual(ready["valid_until"], "2026-08-21T14:10:00+00:00")
        args["now"] = "2026-08-21T14:10:00+00:00"
        blocked = self.instruction(compile_order_intent_artifact(**args), "PGR")
        self.assertEqual(blocked["state"], "ORDER_BLOCKED")
        self.assertIn("OPEN_ORDER_EVIDENCE_STALE", blocked["blockers"])
        self.assertEqual(ready["valid_until"], blocked["valid_until"])


if __name__ == "__main__":
    unittest.main()
