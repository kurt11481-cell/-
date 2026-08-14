from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_nbis_v3_shadow_activation import (  # noqa: E402
    build_price_evidence,
    scenario,
)
from holding_baseline_operationalization import validate_valuation_snapshot  # noqa: E402


class NbisV3ShadowActivationTests(unittest.TestCase):
    def test_price_evidence_preserves_same_session_kiwoom_conflict(self):
        evidence = build_price_evidence(ROOT)
        self.assertEqual(evidence["canonical_display_close"], 255.04)
        self.assertEqual(evidence["comparison_status"], "CONFLICT")
        self.assertEqual(evidence["validation_status"], "CONFLICT")
        self.assertEqual(
            evidence["comparable_conflicting_sources"][0]["disposition"],
            "PRESERVED_SAME_SESSION_CONFLICT",
        )
        self.assertFalse(evidence["order_authority"])

    def test_convertible_share_and_debt_double_count_fails(self):
        with self.assertRaisesRegex(ValueError, "CONVERTIBLE_DOUBLE_COUNT"):
            scenario(
                "bad", "STRESS_DILUTED", 300, 255, 8, 8,
                ["bad"], convertible_shares=True, convertible_debt=True,
            )

    def test_v3_snapshot_conflict_is_not_activatable(self):
        path = ROOT / "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v3.json"
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        result = validate_valuation_snapshot(
            snapshot,
            ROOT / "manage-us-stock-strategy/schemas/issuer-valuation-snapshot.schema.json",
        )
        self.assertEqual(result["validation_status"], "FAILED")
        self.assertIn("PRICE_EVIDENCE_CONFLICT", result["errors"])
        self.assertNotIn("PRICE_PROVIDER_NOT_APPROVED_FOR_VALUATION", result["errors"])

    def test_original_source_requires_explicit_kiwoom_scope(self):
        path = ROOT / "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v3.json"
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        broken = deepcopy(snapshot)
        broken["price"]["kiwoom_observation"]["disposition"] = "UNKNOWN"
        broken["snapshot_hash"] = "0" * 64
        result = validate_valuation_snapshot(
            broken,
            ROOT / "manage-us-stock-strategy/schemas/issuer-valuation-snapshot.schema.json",
        )
        self.assertIn("PRICE_PROVIDER_NOT_APPROVED_FOR_VALUATION", result["errors"])


if __name__ == "__main__":
    unittest.main()
