"""Regression tests for the v2 deterministic decision gate."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SKILL_ROOT.parent
SCRIPT = SKILL_ROOT / "scripts" / "validate_decision_record.py"
SPEC = importlib.util.spec_from_file_location("validate_decision_record", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DecisionRecordValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            (WORKSPACE_ROOT / "workspace" / "policies" / "instrument_registry.json").read_text(encoding="utf-8")
        )
        cls.universe = json.loads(
            (WORKSPACE_ROOT / "workspace" / "policies" / "tactical_candidate_universe.json").read_text(encoding="utf-8")
        )

    def read_fixture(self, name: str):
        return json.loads((SKILL_ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8"))

    def test_valid_watch_only_fixture_passes(self) -> None:
        result = MODULE.validate_record(
            self.read_fixture("decision-record.valid.test-only.json"),
            self.registry,
            self.universe,
        )
        self.assertEqual(result["status"], "WATCH_ONLY", result)
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["order_authority"])

    def test_non_held_sell_and_lookahead_fixture_fails(self) -> None:
        result = MODULE.validate_record(
            self.read_fixture("decision-record.invalid.test-only.json"),
            self.registry,
            self.universe,
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertTrue(any("look-ahead" in item for item in result["errors"]))
        self.assertTrue(any("NOT_HELD" in item for item in result["errors"]))

    def test_risk_controller_cannot_upgrade(self) -> None:
        record = self.read_fixture("decision-record.valid.test-only.json")
        record["trader_proposal"]["action"] = "CONDITIONAL_BUY"
        record["risk_review"].update(
            {"verdict": "DOWNGRADE", "input_action": "CONDITIONAL_BUY", "output_action": "BUY_REVIEW"}
        )
        record["portfolio_decision"]["action"] = "BUY_REVIEW"
        record["final_action"] = "BUY_REVIEW"
        record["deterministic_gate"]["status"] = "REJECTED"
        result = MODULE.validate_record(record, self.registry, self.universe)
        self.assertEqual(result["status"], "REJECTED")
        self.assertTrue(any("DOWNGRADE" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
