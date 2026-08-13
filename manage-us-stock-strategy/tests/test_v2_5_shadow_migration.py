from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from migrate_v2_5_shadow_runtime import migrate_runtime
from validation_common import canonical_hash, validate_instance


class V25ShadowMigrationTests(unittest.TestCase):
    def test_delivery_history_is_preserved_without_replay(self):
        tactical = {"last_processed_us_session": "2026-08-12", "deliveries": {"old-tactical": {"sent": True}}}
        holding = {"last_processed_session": "2026-08-12", "deliveries": {"old-holding": {"sent": True}}}
        value = migrate_runtime(tactical_runtime=tactical, holding_runtime=holding,
                                policy_version="2026-08-13-v2.5", migrated_at="2026-08-13T00:00:00Z")
        self.assertIn("old-tactical", value["namespaces"]["trade_review"]["deliveries"])
        self.assertIn("old-holding", value["namespaces"]["holding_review"]["deliveries"])
        self.assertFalse(value["delivery_replay_allowed"])

    def test_shadow_runtime_contains_no_brokerage_facts(self):
        value = migrate_runtime(tactical_runtime={"deliveries": {}}, holding_runtime={"deliveries": {}},
                                policy_version="2026-08-13-v2.5")
        encoded = json.dumps(value)
        for forbidden in ("available_cash_usd", "average_cost_usd", "position_cost_basis_usd", '"holdings"', '"fills"', '"orders"'):
            self.assertNotIn(forbidden, encoded)

    def test_shadow_schema_and_paths(self):
        value = migrate_runtime(tactical_runtime={"deliveries": {}}, holding_runtime={"deliveries": {}},
                                policy_version="2026-08-13-v2.5")
        errors = validate_instance(value, ROOT / "manage-us-stock-strategy/schemas/v2-5-shadow-runtime.schema.json")
        self.assertEqual(errors, [])
        self.assertTrue((ROOT / "workspace/state/v2_5_shadow").is_dir())
        self.assertTrue((ROOT / "workspace/outputs/v2_5_shadow").is_dir())

    def test_migration_does_not_mutate_portfolio_fixture(self):
        portfolio = {"state_revision": 10, "holdings": {"SOXL": 75}, "available_cash_usd": 0}
        before = canonical_hash(portfolio)
        migrate_runtime(tactical_runtime={"deliveries": {}}, holding_runtime={"deliveries": {}},
                        policy_version="2026-08-13-v2.5")
        self.assertEqual(canonical_hash(portfolio), before)


if __name__ == "__main__":
    unittest.main()
