from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from automation_delivery import mark_configured, update_delivery
from validation_common import load_json, validate_instance
from validate_skill_deployment import ARTIFACTS, normalized_text_sha256, validate_deployment


class V24AutomationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_json(ROOT / "workspace" / "state" / "automation_delivery_runtime.json")

    def test_configuration_is_not_delivery_verification(self):
        configured = mark_configured(self.runtime, "morning_portfolio_strategy")
        self.assertEqual(configured["automations"]["morning_portfolio_strategy"]["status"], "FIRST_RUN_PENDING")
        self.assertNotEqual(configured["automations"]["morning_portfolio_strategy"]["status"], "DELIVERY_VERIFIED")

    def test_first_valid_output_verifies_delivery_and_preserves_portfolio_hash(self):
        result = update_delivery(self.runtime, "morning_portfolio_strategy", attempted_at="2026-08-13T00:00:00+00:00",
            success=True, completed_session="2026-08-12", output_artifact="workspace/outputs/test/report.json",
            notification_status="DELIVERED", git_commit="abc", policy_version="v2.4",
            portfolio_hash_before="a" * 64, portfolio_hash_after="a" * 64)
        self.assertEqual(result["automations"]["morning_portfolio_strategy"]["status"], "DELIVERY_VERIFIED")
        self.assertEqual(validate_instance(result, ROOT / "manage-us-stock-strategy" / "schemas" / "automation-delivery-runtime.schema.json"), [])

    def test_failure_records_reason_and_hash_change_fails(self):
        result = update_delivery(self.runtime, "preopen_portfolio_risk_refresh", attempted_at="2026-08-13T12:45:00+00:00",
            success=True, completed_session="2026-08-12", output_artifact="workspace/outputs/test/preopen.json",
            notification_status="FAILED", git_commit="abc", policy_version="v2.4",
            portfolio_hash_before="a" * 64, portfolio_hash_after="b" * 64)
        row = result["automations"]["preopen_portfolio_risk_refresh"]
        self.assertEqual(row["status"], "FAILED")
        self.assertEqual(row["failure_reason"], "PORTFOLIO_STATE_HASH_CHANGED")

    def test_no_windows_scheduler_artifact_exists(self):
        forbidden = list(ROOT.rglob("*.xml")) + list(ROOT.rglob("*.job"))
        self.assertFalse(any("task" in path.name.lower() or "schedule" in path.name.lower() for path in forbidden))

    def test_deployment_gate_hashes_match_canonical_source(self):
        policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        gate = policy["deployment_gate"]
        source = ROOT / "manage-us-stock-strategy"
        for name, relative in ARTIFACTS.items():
            digest = normalized_text_sha256(source / relative)
            self.assertEqual(digest, gate[f"required_source_{name}_sha256"])
            self.assertEqual(digest, gate[f"observed_installed_{name}_sha256"])

    def test_deployment_validator_detects_mismatch(self):
        policy = load_json(ROOT / "stock-strategy-system" / "alert_policy.json")
        result = validate_deployment(policy, ROOT / "manage-us-stock-strategy", ROOT / "manage-us-stock-strategy")
        self.assertEqual(result["validation_status"], "PASS")
        broken = json.loads(json.dumps(policy))
        broken["deployment_gate"]["required_source_skill_sha256"] = "0" * 64
        result = validate_deployment(broken, ROOT / "manage-us-stock-strategy", ROOT / "manage-us-stock-strategy")
        self.assertEqual(result["validation_status"], "FAIL")
        self.assertIn("DEPLOYMENT_HASH_MISMATCH:skill", result["errors"])


if __name__ == "__main__":
    unittest.main()
