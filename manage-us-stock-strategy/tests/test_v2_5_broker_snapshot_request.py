from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
from evaluate_broker_snapshot_request import evaluate_broker_snapshot_request
from validation_common import load_json, validate_instance


class V25BrokerSnapshotRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_json(ROOT / "workspace/policies/broker_snapshot_policy.json")

    def state(self, *, verified=True, complete=True, as_of="2026-08-11"):
        return {"holdings": {"NBIS": 15}, "average_cost_usd": {"NBIS": 215.0}, "unreconciled_holding_changes": [],
                "last_confirmed_broker_snapshot": {"verified": verified, "holdings_complete": complete,
                    "cash_verified": True, "as_of": as_of, "account_id_masked": "****5546"}}

    def call(self, *, state=None, cash="VERIFIED_ZERO", holdings=None, radar=None, runtime=None, unreconciled=None):
        return evaluate_broker_snapshot_request(portfolio_state=state or self.state(),
            cash_gate_result={"cash_status": cash}, holding_strategies=holdings or [{"ticker": "NBIS", "strategy_state": "HOLD", "policy_rule_id": "HR-NBIS"}],
            holding_risk_result={"state": "DAILY_REVIEW"}, tactical_radar_result=radar or {"candidate_dispositions": []},
            latest_completed_session="2026-08-11", broker_snapshot_policy=self.policy,
            unreconciled_user_change_state=unreconciled or [], runtime=runtime)

    def reasons(self, result):
        return {item["reason_code"] for item in result["reason_codes"]}

    def test_v25_sr_01_stale_full_required(self):
        result, _ = self.call(cash="STALE")
        self.assertEqual((result["snapshot_request_status"], result["required_scope"]), ("REQUIRED", "FULL_PORTFOLIO"))

    def test_v25_sr_02_incomplete_holdings_required(self):
        result, _ = self.call(state=self.state(complete=False), cash="UNVERIFIED")
        self.assertIn("BROKER_HOLDINGS_INCOMPLETE", self.reasons(result))

    def test_v25_sr_03_ready_cash_unverified_is_cash_only(self):
        radar = {"candidate_dispositions": [{"ticker": "NOW", "opportunity_state": "READY"}]}
        result, _ = self.call(cash="UNVERIFIED", radar=radar)
        self.assertEqual((result["snapshot_request_status"], result["required_scope"]), ("REQUIRED", "CASH_ONLY"))

    def test_v25_sr_04_fresh_hold_not_required(self):
        result, _ = self.call()
        self.assertEqual(result["snapshot_request_status"], "NOT_REQUIRED")

    def test_v25_sr_05_market_outage_not_a_broker_reason(self):
        result, _ = self.call()
        self.assertNotIn("GLOBAL_INDEPENDENT_CLOSE_OUTAGE", self.reasons(result))

    def test_v25_sr_06_deployment_mismatch_not_a_broker_reason(self):
        result, _ = self.call()
        self.assertNotIn("DEPLOYMENT_HASH_MISMATCH", self.reasons(result))

    def test_v25_sr_07_same_request_deduplicated(self):
        first, runtime = self.call(cash="STALE")
        second, _ = self.call(cash="STALE", runtime=runtime)
        self.assertTrue(first["notify"])
        self.assertFalse(second["notify"])

    def test_v25_sr_08_scope_expansion_renotifies(self):
        radar = {"candidate_dispositions": [{"ticker": "NOW", "opportunity_state": "READY"}]}
        first, runtime = self.call(cash="UNVERIFIED", radar=radar)
        second, _ = self.call(state=self.state(complete=False), cash="UNVERIFIED", radar=radar, runtime=runtime)
        self.assertEqual((first["required_scope"], second["required_scope"]), ("CASH_ONLY", "FULL_PORTFOLIO"))
        self.assertTrue(second["notify"])

    def test_v25_sr_09_received_not_verified(self):
        result, _ = self.call(state=self.state(verified=False), cash="UNVERIFIED")
        self.assertEqual(result["snapshot_request_status"], "REQUIRED")

    def test_v25_sr_10_confirmed_fresh_state_closes_runtime(self):
        _, runtime = self.call(cash="STALE")
        result, closed = self.call(runtime=runtime)
        self.assertEqual(result["snapshot_request_status"], "NOT_REQUIRED")
        self.assertTrue(all(item["status"] == "VERIFIED" for item in closed["requests"].values()))

    def test_v25_sr_11_request_does_not_erase_strategy(self):
        holding = {"ticker": "NBIS", "strategy_state": "ADD_REVIEW", "policy_rule_id": "HR-NBIS"}
        radar = {"candidate_dispositions": [{"ticker": "NOW", "opportunity_state": "READY"}]}
        result, _ = self.call(cash="UNVERIFIED", holdings=[holding], radar=radar)
        self.assertEqual(holding["strategy_state"], "ADD_REVIEW")
        self.assertEqual(radar["candidate_dispositions"][0]["opportunity_state"], "READY")
        self.assertEqual(result["execution_effect"], "CASH_BLOCKED")

    def test_v25_sr_12_schema(self):
        result, _ = self.call(cash="STALE")
        self.assertEqual(validate_instance(result, ROOT / "manage-us-stock-strategy/schemas/broker-snapshot-request.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
