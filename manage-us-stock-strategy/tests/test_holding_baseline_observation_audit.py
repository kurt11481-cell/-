from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("observation_audit", SCRIPTS / "audit_holding_baseline_observations.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class HoldingBaselineObservationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = module.audit(ROOT)
        cls.rows = {row["ticker"]: row for row in cls.audit["subjects"]}

    def test_audit_01_exact_three_ticker_subjects(self):
        self.assertEqual(set(self.rows), {"SOXL", "NBIS", "MVLL"})

    def test_audit_02_subject_ids_unique(self):
        self.assertEqual(len({x["subject_binding"]["baseline_id"] for x in self.rows.values()}), 3)

    def test_audit_03_baseline_sha_bound(self):
        self.assertTrue(all(len(x["subject_binding"]["baseline_sha256"]) == 64 for x in self.rows.values()))

    def test_audit_04_baseline_hash_bound(self):
        self.assertTrue(all(len(x["subject_binding"]["baseline_hash"]) == 64 for x in self.rows.values()))

    def test_audit_05_compile_sha_bound(self):
        self.assertTrue(all(len(x["subject_binding"]["compile_sha256"]) == 64 for x in self.rows.values()))

    def test_audit_06_strategy_content_sha_bound(self):
        self.assertTrue(all(len(x["subject_binding"]["strategy_content_sha256"]) == 64 for x in self.rows.values()))

    def test_audit_07_policy_sha_bound(self):
        self.assertEqual(len({x["subject_binding"]["policy_sha256"] for x in self.rows.values()}), 1)

    def test_audit_08_provider_sha_bound(self):
        self.assertEqual(len({x["subject_binding"]["provider_scope_sha256"] for x in self.rows.values()}), 1)

    def test_audit_09_compiler_semantic_version_bound(self):
        self.assertTrue(all(x["subject_binding"]["compiler_semantic_version"] == module.FORMULA_VERSION for x in self.rows.values()))

    def test_audit_10_activation_timestamp_bound(self):
        self.assertTrue(all(x["subject_binding"]["activation_timestamp"] for x in self.rows.values()))

    def test_audit_11_audit_never_increments(self):
        self.assertTrue(all(x["audit_increment"] == 0 for x in self.rows.values()))

    def test_audit_12_observation_is_zero_of_five(self):
        self.assertTrue(all((x["valid_sessions"], x["required_valid_sessions"]) == (0, 5) for x in self.rows.values()))

    def test_audit_13_no_backfill(self):
        self.assertTrue(all(x["backfill"] is False for x in self.rows.values()))

    def test_audit_14_no_promotion_authority(self):
        self.assertTrue(all(x["promotion_authority"] is False for x in self.rows.values()))

    def test_audit_15_order_authority_false(self):
        self.assertTrue(all(x["order_authority"] is False for x in self.rows.values()))

    def test_audit_16_quantity_authority_none(self):
        self.assertTrue(all(x["quantity"] is None and x["quantity_authority"] == "none" for x in self.rows.values()))

    def test_audit_17_portfolio_immutable(self):
        self.assertTrue(self.audit["portfolio_unchanged"])
        self.assertEqual(self.audit["portfolio_hash_before"], self.audit["portfolio_hash_after"])

    def test_audit_18_ticker_local_no_critical_violations(self):
        self.assertTrue(all(not x["critical_violations"] for x in self.rows.values()))

    def test_audit_19_mvll_boundary_block_preserved(self):
        self.assertEqual(self.rows["MVLL"]["technical_boundary_block"], "EMA10_RECLAIM_RVOL20")

    def test_audit_20_diagnostic_divergence_nonblocking(self):
        self.assertTrue(all(x["diagnostic_shadow_divergence_blocking"] is False for x in self.rows.values()))

    def test_audit_21_status_remains_in_progress(self):
        self.assertEqual(self.audit["overall_status"], "SHADOW_OBSERVATION_IN_PROGRESS")
        self.assertTrue(all(x["observation_status"] == "SHADOW_OBSERVATION_IN_PROGRESS" for x in self.rows.values()))

    def test_audit_22_operational_counter_unchanged(self):
        self.assertEqual(self.audit["operational_session_increment"], 0)
        self.assertFalse(self.audit["manual_or_replay_counted"])


if __name__ == "__main__":
    unittest.main()
