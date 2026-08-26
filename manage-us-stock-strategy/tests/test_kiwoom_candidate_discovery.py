from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from kiwoom_candidate_discovery_bridge import (
    blocked_api_target, classify_instrument, classify_liquidity,
    deduplicate_candidates, invoke_discovery_bridge_batch, validate_request,
)
from kiwoom_runtime_bridge import BridgeError
from run_kiwoom_candidate_discovery import build_artifact
from validation_common import load_json, validate_instance


class KiwoomCandidateDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_json(ROOT / "workspace/policies/kiwoom-candidate-discovery-readonly-policy.json")
        cls.rate_policy = {
            "external_python_relative_path": "manage-us-stock-strategy/scripts/kiwoom_candidate_discovery_bridge.py",
        }

    def invoke_with(self, runner):
        return invoke_discovery_bridge_batch(
            [{"operation": "volume_rank_stock"}],
            runtime=ROOT,
            policy=self.policy,
            rate_policy=self.rate_policy,
            runner=runner,
        )[0]

    @staticmethod
    def completed(stdout: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    def test_readonly_allowlist_and_order_denylist(self):
        self.assertEqual(validate_request({"operation": "volume_rank_stock"}, self.policy)["operation"], "volume_rank_stock")
        self.assertTrue(blocked_api_target(self.policy, "ust20000", "/api/us/ordr"))
        with self.assertRaises(BridgeError):
            validate_request({"operation": "buy_order"}, self.policy)

    def test_condition_search_requires_exact_sequence(self):
        with self.assertRaises(BridgeError):
            validate_request({"operation": "condition_search"}, self.policy)
        self.assertEqual(validate_request({"operation": "condition_search", "condition_sequence": "7"}, self.policy)["condition_sequence"], "7")
        with self.assertRaises(BridgeError):
            validate_request({"operation": "security_info", "ticker": "AAPL"}, self.policy)
        value = validate_request({"operation": "security_info", "ticker": "AAPL", "exchange": "ND"}, self.policy)
        self.assertEqual(value["ticker"], "AAPL")

    def test_dedup_and_instrument_classification(self):
        rows = [
            {"canonical_ticker": "SOXL", "stex_tp": "NY", "stk_enm": "DIREXION SEMICONDUCTOR BULL 3X", "source_operation": "volume_rank_etf"},
            {"canonical_ticker": "SOXL", "stex_tp": "NY", "stk_enm": "DIREXION SEMICONDUCTOR BULL 3X", "source_operation": "change_rate_etf"},
            {"canonical_ticker": "AAPL", "stex_tp": "ND", "stk_enm": "APPLE INC", "source_operation": "volume_rank_stock"},
        ]
        values = deduplicate_candidates(rows)
        self.assertEqual(len(values), 2)
        self.assertEqual(next(x for x in values if x["canonical_ticker"] == "SOXL")["instrument_class"], "leveraged_etf")
        self.assertEqual(classify_instrument({"stk_enm": "ABC ADR", "source_operation": "volume_rank_stock"}), "adr")
        self.assertEqual(classify_instrument({"stk_enm": "ABC SPON ADS EACH REP 1 ORD", "source_operation": "volume_rank_stock"}), "adr")
        self.assertEqual(classify_instrument({"stk_enm": "ABC CORP UNIT 1 SH", "source_operation": "volume_rank_stock"}), "unsupported_product")
        self.assertEqual(classify_instrument({"stk_enm": "ABC C/WTS 2029", "source_operation": "volume_rank_stock"}), "unsupported_product")
        self.assertEqual(classify_liquidity({"acc_trde_qty": "0"}), "LOW_LIQUIDITY_CANDIDATE")
        self.assertEqual(classify_liquidity({"acc_trde_qty": "1467"}), "UNVERIFIED_NO_APPROVED_THRESHOLD")

    def test_ticker_local_malformed_record_does_not_erase_other_candidates(self):
        results = [
            {"bridge_status": "PASS", "operation": "volume_rank_stock", "runtime_commit": "a" * 40,
             "data": [{"canonical_ticker": "AAPL", "stex_tp": "ND", "stk_enm": "APPLE", "source_operation": "volume_rank_stock"}],
             "ticker_failures": [{"operation": "volume_rank_stock", "row_index": 2, "reason": "MALFORMED_RECORD"}]},
        ]
        value = build_artifact(results)
        self.assertEqual(value["deduplicated_count"], 1)
        self.assertEqual(len(value["ticker_failures"]), 1)
        self.assertEqual(value["operation_failures"], [])
        self.assertIsNone(value["quantity"])
        self.assertFalse(value["order_authority"])
        errors = validate_instance(value, ROOT / "manage-us-stock-strategy/schemas/kiwoom-candidate-discovery-acceptance.schema.json")
        self.assertEqual(errors, [])

    def test_malformed_final_line_is_local_protocol_failure(self):
        prior = {"results": [{"bridge_status": "PASS", "operation": "volume_rank_stock"}]}
        result = self.invoke_with(lambda *args, **kwargs: self.completed(
            json.dumps(prior) + "\n{malformed\n"
        ))
        self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
        self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])

    def test_previous_provider_failure_plus_malformed_final_is_local_protocol_failure(self):
        prior = {"results": [{
            "bridge_status": "KIWOOM_API_UNAVAILABLE",
            "failure_type": "HTTP_429",
            "operation": "volume_rank_stock",
        }]}
        result = self.invoke_with(lambda *args, **kwargs: self.completed(
            json.dumps(prior) + "\nnot-json\n"
        ))
        self.assertEqual("BRIDGE_OUTPUT_INVALID", result["bridge_status"])
        self.assertEqual("LOCAL_PROTOCOL_FAILURE", result["failure_type"])

    def test_actual_subprocess_timeout_remains_timeout(self):
        def timeout_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

        result = self.invoke_with(timeout_runner)
        self.assertEqual("KIWOOM_API_UNAVAILABLE", result["bridge_status"])
        self.assertEqual("TIMEOUT", result["failure_type"])

    def test_local_subprocess_failure_is_local_transport_failure(self):
        def transport_runner(*args, **kwargs):
            raise OSError("test-only local launch failure")

        result = self.invoke_with(transport_runner)
        self.assertEqual("BRIDGE_TRANSPORT_FAILURE", result["bridge_status"])
        self.assertEqual("LOCAL_TRANSPORT_FAILURE", result["failure_type"])

    def test_clean_provider_failure_is_preserved(self):
        payload = {"results": [{
            "bridge_status": "KIWOOM_API_UNAVAILABLE",
            "failure_type": "HTTP_429",
            "operation": "volume_rank_stock",
        }]}
        result = self.invoke_with(lambda *args, **kwargs: self.completed(json.dumps(payload)))
        self.assertEqual("KIWOOM_API_UNAVAILABLE", result["bridge_status"])
        self.assertEqual("HTTP_429", result["failure_type"])

    def test_clean_success_is_preserved(self):
        payload = {"results": [{
            "bridge_status": "PASS",
            "operation": "volume_rank_stock",
            "data": [],
            "ticker_failures": [],
            "order_authority": False,
        }]}
        result = self.invoke_with(lambda *args, **kwargs: self.completed(json.dumps(payload)))
        self.assertEqual("PASS", result["bridge_status"])
        self.assertFalse(result["order_authority"])


if __name__ == "__main__":
    unittest.main()
