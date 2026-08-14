from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

from deployment_provenance import verify_provenance
from validation_common import canonical_hash


class DeploymentProvenanceTests(unittest.TestCase):
    def artifact(self):
        value = {"schema_version": "1.0", "status": "DEPLOYMENT_PROVENANCE_VERIFIED",
                 "runtime_repository_path": str(ROOT), "runtime_head": "a" * 40,
                 "runtime_clean": True, "failure_reasons": [], "counting_enabled": True,
                 "order_authority": False}
        value["record_hash"] = canonical_hash(value)
        return value

    def test_exact_clean_head_passes(self):
        self.assertEqual(verify_provenance(self.artifact(), expected_head="a" * 40, runtime_repo=ROOT), [])

    def test_mismatched_head_and_dirty_disable_counting(self):
        value = self.artifact(); value["runtime_clean"] = False; value["counting_enabled"] = False
        value["record_hash"] = canonical_hash({k: v for k, v in value.items() if k != "record_hash"})
        errors = verify_provenance(value, expected_head="b" * 40, runtime_repo=ROOT)
        self.assertIn("RUNTIME_HEAD_MISMATCH", errors)
        self.assertIn("RUNTIME_WORKTREE_DIRTY", errors)
        self.assertIn("COUNTING_DISABLED", errors)
