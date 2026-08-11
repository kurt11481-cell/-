"""Regression tests for the deterministic research-packet trust boundary."""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def locate_strategy_system_root() -> Path:
    configured = os.environ.get("STOCK_STRATEGY_SYSTEM_ROOT")
    if configured:
        candidate = Path(configured).resolve()
        if (candidate / "alert_policy.json").is_file():
            return candidate
        raise RuntimeError(
            "STOCK_STRATEGY_SYSTEM_ROOT does not contain alert_policy.json: "
            f"{candidate}"
        )

    candidates = [
        SKILL_ROOT.parent / "stock-strategy-system",
        SKILL_ROOT.parents[1],
        Path.cwd() / "stock-strategy-system",
    ]
    for candidate in candidates:
        candidate = candidate.resolve()
        if (candidate / "alert_policy.json").is_file():
            return candidate
    raise RuntimeError("cannot locate stock-strategy-system from the skill test path")


STRATEGY_SYSTEM_ROOT = locate_strategy_system_root()
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_research_packet.py"
POLICY_PATH = STRATEGY_SYSTEM_ROOT / "alert_policy.json"
SNAPSHOT_EXAMPLE_PATH = STRATEGY_SYSTEM_ROOT / "market_snapshot.example.json"

SPEC = importlib.util.spec_from_file_location(
    "workspace_validate_research_packet", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ResearchPacketHardeningTests(unittest.TestCase):
    def test_validator_self_test(self) -> None:
        VALIDATOR.self_test()

    def test_active_policy_keeps_watchlist_separate_from_buy_authority(self) -> None:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        harness = policy["decision_harness"]
        self.assertFalse(harness["packet_to_candidate_adapter_enabled"])
        for symbol in ("SOXL", "DRAM", "NBIS", "BE"):
            instrument = harness["instrument_registry"][symbol]
            self.assertTrue(instrument["watchlist_approved"], symbol)
            self.assertFalse(instrument["new_buy_instrument_approved"], symbol)
        for rule in harness["approved_rule_registry"].values():
            self.assertIn(
                rule["quantity_authority"],
                {"none", "fixed", "versioned_anchor_and_shared_tranche_slots"},
            )

    def test_snapshot_fixture_declares_contract_version(self) -> None:
        snapshot = json.loads(SNAPSHOT_EXAMPLE_PATH.read_text(encoding="utf-8"))
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            snapshot["schema_version"],
            policy["decision_harness"]["schema_contract"]["market_snapshot"],
        )


if __name__ == "__main__":
    unittest.main()
