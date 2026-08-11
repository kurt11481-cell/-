"""Regression tests for append-only v2 outcome evaluation."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "evaluate_outcome.py"
SPEC = importlib.util.spec_from_file_location("evaluate_outcome", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OutcomeEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(
            (SKILL_ROOT / "tests" / "fixtures" / "decision-record.valid.test-only.json").read_text(encoding="utf-8")
        )
        self.outcome = {
            "decision_id": self.decision["decision_id"],
            "original_decision_sha256": MODULE.canonical_sha256(self.decision),
            "observed_at_utc": "2026-08-20T12:00:00+00:00",
            "triggered_confirmation_condition_ids": ["C1"],
            "triggered_invalidation_condition_ids": [],
            "security_return_fraction": 0.05,
            "benchmark_return_fraction": 0.03,
            "transaction_cost_fraction": 0.001,
            "slippage_fraction": 0.001,
            "evidence_ids": ["OUTCOME-E1"]
        }

    def test_confirmed_outcome_is_calibration_eligible(self) -> None:
        result = MODULE.evaluate(self.decision, self.outcome)
        self.assertEqual(result["classification"], "CONFIRMED", result)
        self.assertAlmostEqual(result["net_security_return_fraction"], 0.048)
        self.assertAlmostEqual(result["excess_return_fraction"], 0.018)
        self.assertTrue(result["decision_record_unchanged"])

    def test_wrong_decision_hash_rejects(self) -> None:
        self.outcome["original_decision_sha256"] = "0" * 64
        result = MODULE.evaluate(self.decision, self.outcome)
        self.assertEqual(result["classification"], "REJECTED")

    def test_both_confirmation_and_invalidation_revises(self) -> None:
        self.outcome["triggered_invalidation_condition_ids"] = ["I1"]
        result = MODULE.evaluate(self.decision, self.outcome)
        self.assertEqual(result["classification"], "REVISED", result)


if __name__ == "__main__":
    unittest.main()
