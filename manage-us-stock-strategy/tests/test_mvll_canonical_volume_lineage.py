from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from build_mvll_canonical_volume_lineage import build_lineage
from provider_limitation_audit import build_audit
from validation_common import load_json, write_json


class MvllCanonicalVolumeLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.early = load_json(ROOT / "workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/kiwoom_daily_snapshot.json")
        cls.final = load_json(ROOT / "workspace/outputs/activation/holding-valuation-shadow/2026-08-13/kiwoom-finalized-snapshot.json")
        cls.diagnostic = load_json(ROOT / "workspace/research/provider-evidence/kiwoom/2026-08-14/mvll-volume-authority-acceptance.json")
        cls.policy = {"threshold": 1.0}

    def build(self, final_count=2):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            values = [("early.json", self.early)] + [(f"final-{i}.json", self.final) for i in range(final_count)]
            pairs = []
            for name, value in values:
                path = base / name
                write_json(path, value)
                pairs.append((path, value))
            return build_lineage(snapshots=pairs, diagnostic=self.diagnostic,
                                 policy=self.policy, minimum_stable_observations=2)

    def test_terminal_stability_selects_later_provider_record_without_averaging(self):
        value = self.build()
        self.assertEqual(value["volume_authority_status"], "KIWOOM_VALID_SCOPED")
        self.assertAlmostEqual(value["canonical_rvol20"], 0.8924874478089728)
        self.assertEqual(value["technical_condition_status"], "RVOL20_NOT_MET")
        self.assertEqual(value["observations"][0]["lineage_disposition"], "BAR_UNSTABLE_SUPERSEDED")
        self.assertFalse(value["divergence_blocking"])

    def test_one_terminal_observation_fails_closed(self):
        value = self.build(final_count=1)
        self.assertEqual(value["volume_authority_status"], "KIWOOM_LINEAGE_UNVERIFIED")
        self.assertFalse(value["bar_finalized"])

    def test_provider_audit_uses_canonical_lineage(self):
        lineage = self.build()
        base = ROOT / "workspace/outputs/portfolio-strategy/2026-08-13"
        value = build_audit(
            kiwoom_snapshot=load_json(base / "kiwoom_market_snapshot.json"),
            yfinance_snapshot=load_json(base / "yfinance_shadow_snapshot.json"),
            extended_snapshot=load_json(ROOT / "workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/kiwoom_extended_hours_snapshot_v2.json"),
            provider_policy=load_json(ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json"),
            volume_lineage=lineage,
        )["MVLL"]
        self.assertAlmostEqual(value["kiwoom_rvol20"], lineage["canonical_rvol20"])
        self.assertTrue(value["lineage_consistent"])
        self.assertEqual(value["blocked_decision_classes"], [])


if __name__ == "__main__":
    unittest.main()
