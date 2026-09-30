from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from apply_user_confirmed_broker_snapshot import apply_confirmed
from build_broker_reconciliation_proposal import build_proposal
from ingest_broker_snapshot import ingest
from validate_broker_snapshot_extraction import validate_extraction
from validation_common import canonical_hash, load_json


class V25BrokerSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_path = ROOT / "manage-us-stock-strategy/tests/fixtures/v2_5/broker-snapshot-extraction.sample-korean.test-only.json"
        cls.sample = load_json(cls.fixture_path)
        cls.schema = ROOT / "manage-us-stock-strategy/schemas/broker-reconciliation-proposal.schema.json"

    def state(self):
        return {"schema_version": "1.3", "strategy_version": "2026-08-05-v4", "state_revision": 1,
                "holdings": {"OLD": 1}, "average_cost_usd": {"OLD": 10.0}, "position_cost_basis_usd": {"OLD": 10.0},
                "available_cash_usd": 0.0, "last_confirmed_broker_snapshot": {"verified": True}}

    def temp_image(self, suffix):
        handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        handle.write(b"TEST_IMAGE")
        handle.close()
        return Path(handle.name)

    def test_v25_bs_01_supported_upload_types(self):
        paths = [self.temp_image(ext) for ext in (".png", ".jpeg", ".jpg", ".webp")]
        try:
            self.assertEqual(ingest(paths, bundle_id="BS-TEST")["page_count"], 4)
        finally:
            for path in paths: path.unlink(missing_ok=True)

    def test_v25_bs_02_multiple_files_one_bundle(self):
        paths = [self.temp_image(".png"), self.temp_image(".jpg")]
        try:
            value = ingest(paths, bundle_id="BS-ONE")
            self.assertEqual({item["page_count"] for item in value["pages"]}, {2})
            self.assertEqual(value["bundle_id"], "BS-ONE")
        finally:
            for path in paths: path.unlink(missing_ok=True)

    def test_v25_bs_03_upload_cannot_mutate(self):
        state = self.state(); before = canonical_hash(state); path = self.temp_image(".png")
        try: ingest([path], bundle_id="BS-X")
        finally: path.unlink(missing_ok=True)
        self.assertEqual(before, canonical_hash(state))

    def test_v25_bs_04_extraction_cannot_mutate(self):
        state = self.state(); before = canonical_hash(state); build_proposal(self.sample, state)
        self.assertEqual(before, canonical_hash(state))

    def test_v25_bs_05_confirmed_proposal_atomic_apply(self):
        # v1: the library refuses every screenshot proposal, even a resolved and confirmed one. Atomic apply is
        # covered by the Kiwoom path (test_reconcile_broker_state LibraryApplyTests and CliTests).
        resolved = copy.deepcopy(self.sample)
        resolved.update(capture_date_status="VERIFIED", holdings_complete_status="VERIFIED",
                        position_currency_status="VERIFIED")
        state = self.state(); proposal = build_proposal(resolved, state)
        self.assertEqual(proposal["unresolved_fields"], [])
        directory = ROOT / "workspace/outputs/v2_5_shadow"
        state_path = directory / "test-broker-apply-state.json"; audit = directory / "test-broker-apply-audit.json"
        try:
            state_path.write_text(json.dumps(state), encoding="utf-8")
            original = state_path.read_bytes(); files_before = sorted(path.name for path in directory.iterdir())
            with self.assertRaisesRegex(ValueError, "SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED"):
                apply_confirmed(state_path=state_path, proposal=proposal,
                    confirmation={"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
                                  "account_id_masked": "****5546", "evidence_sha256": "a" * 64, "as_of": "2026-08-13",
                                  "source": "TEST_ONLY_VERIFIED_BROKER_SNAPSHOT",
                                  "holdings_complete": True, "cash_verified": False, "confirmed_at": "2026-08-13T01:00:00+00:00"},
                    proposal_schema=self.schema, audit_path=audit)
            self.assertEqual(state_path.read_bytes(), original)
            self.assertEqual(sorted(path.name for path in directory.iterdir()), files_before)  # no backup, ledger, audit
        finally:
            state_path.unlink(missing_ok=True); audit.unlink(missing_ok=True)

    def test_v25_bs_06_wrong_revision_rejected(self):
        state = self.state(); proposal = build_proposal(self.sample, state); proposal["expected_state_revision"] = 99
        directory = ROOT / "workspace/outputs/v2_5_shadow"
        state_path = directory / "test-broker-revision-state.json"; audit = directory / "test-broker-revision-audit.json"
        try:
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CONCURRENT_STATE_REVISION_MISMATCH"):
                apply_confirmed(state_path=state_path, proposal=proposal, confirmation={"confirmed": True,
                    "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"]},
                    proposal_schema=self.schema, audit_path=audit)
        finally:
            state_path.unlink(missing_ok=True); audit.unlink(missing_ok=True)

    def test_v25_bs_06a_missing_source_provenance_rejected(self):
        state = self.state(); proposal = build_proposal(self.sample, state)
        directory = ROOT / "workspace/outputs/v2_5_shadow"
        state_path = directory / "test-broker-source-state.json"; audit = directory / "test-broker-source-audit.json"
        try:
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BROKER_SOURCE_PROVENANCE_REQUIRED"):
                apply_confirmed(state_path=state_path, proposal=proposal,
                    confirmation={"confirmed": True, "proposal_id": proposal["proposal_id"],
                                  "bundle_id": proposal["bundle_id"]},
                    proposal_schema=self.schema, audit_path=audit)
        finally:
            state_path.unlink(missing_ok=True); audit.unlink(missing_ok=True)

    def test_v25_bs_07_hash_unchanged_before_confirmation(self):
        state = self.state(); before = canonical_hash(state); proposal = build_proposal(self.sample, state)
        self.assertEqual(proposal["expected_portfolio_hash_before"], before)
        self.assertEqual(canonical_hash(state), before)

    def test_v25_bs_08_raw_screenshot_git_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("workspace/private_inputs/broker_snapshots/", text)
        self.assertFalse(any(path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for path in (ROOT / "manage-us-stock-strategy/tests/fixtures/v2_5").glob("*")))

    def test_v25_bs_09_account_number_masked(self):
        self.assertEqual(self.sample["account_id_masked"], "****5546")
        self.assertNotIn("account_number", self.sample)
        self.assertNotIn("account_holder_name", self.sample)

    def test_v25_bs_10_sensitive_login_forces_reupload(self):
        value = copy.deepcopy(self.sample); value["sensitive_login_or_otp_visible"] = True
        self.assertIn("SENSITIVE_LOGIN_OR_OTP_REUPLOAD_REQUIRED", validate_extraction(value))

    def test_v25_bs_11_position_only_cannot_complete_holdings(self):
        value = copy.deepcopy(self.sample); value["scope"] = "POSITION_ONLY"; value["holdings_complete_status"] = "VERIFIED"
        self.assertIn("POSITION_ONLY_CANNOT_VERIFY_HOLDINGS_COMPLETE", validate_extraction(value))

    def test_v25_bs_12_cash_only_cannot_verify_holdings(self):
        value = copy.deepcopy(self.sample); value["scope"] = "CASH_ONLY"; value["holdings_complete_status"] = "VERIFIED"
        self.assertIn("CASH_ONLY_CANNOT_VERIFY_HOLDINGS", validate_extraction(value))

    def test_v25_bs_13_holdings_only_cannot_verify_cash(self):
        value = copy.deepcopy(self.sample); value["cash_status"] = "VERIFIED_AVAILABLE"; value["cash_classification"] = "AVAILABLE_SETTLED"
        self.assertIn("HOLDINGS_ONLY_CANNOT_VERIFY_CASH", validate_extraction(value))

    def test_v25_bs_14_full_portfolio_strict_completeness(self):
        value = copy.deepcopy(self.sample); value["scope"] = "FULL_PORTFOLIO"
        errors = validate_extraction(value)
        self.assertIn("FULL_PORTFOLIO_ACCOUNT_SCOPE_INCOMPLETE", errors)
        self.assertIn("FULL_PORTFOLIO_CASH_UNVERIFIED", errors)

    def test_v25_bs_15_broker_price_not_market_evidence(self):
        proposal = build_proposal(self.sample, self.state())
        self.assertNotIn("broker_display_price", json.dumps(proposal["proposed_patch"]))
        self.assertNotIn("market_evidence_close", json.dumps(proposal))

    def test_v25_bs_16_quantity_change_does_not_infer_fill(self):
        proposal = build_proposal(self.sample, self.state())
        self.assertFalse(proposal["inferred_fills"])
        self.assertNotIn("confirmed_trades", proposal["proposed_patch"])

    def test_v25_bs_17_margin_buying_power_rejected(self):
        value = copy.deepcopy(self.sample); value["scope"] = "CASH_ONLY"; value["cash_status"] = "VERIFIED_AVAILABLE"; value["cash_classification"] = "MARGIN_BUYING_POWER"
        self.assertIn("NON_SETTLED_OR_MARGIN_CASH_CANNOT_BECOME_AVAILABLE_CASH", validate_extraction(value))

    def test_v25_bs_18_unsettled_funds_rejected(self):
        for status in ("UNSETTLED_D_PLUS_1", "UNSETTLED_D_PLUS_2"):
            value = copy.deepcopy(self.sample); value["scope"] = "CASH_ONLY"; value["cash_status"] = "VERIFIED_AVAILABLE"; value["cash_classification"] = status
            self.assertIn("NON_SETTLED_OR_MARGIN_CASH_CANNOT_BECOME_AVAILABLE_CASH", validate_extraction(value))

    def test_v25_bs_19_two_line_sample_is_one_record_per_ticker(self):
        self.assertEqual([item["ticker"] for item in self.sample["positions"]], ["SOXL", "MVLL", "NBIS"])

    def test_v25_bs_20_ranking_date_not_capture_date(self):
        self.assertIsNone(self.sample["captured_date"])
        self.assertEqual(self.sample["capture_date_status"], "USER_CONFIRMATION_REQUIRED")

    def test_v25_bs_21_sample_values_exact(self):
        expected = [("SOXL", 75, 123.3251, 9249.3862, 10759.5, 143.46),
                    ("MVLL", 396, 41.7791, 16544.5524, 10775.16, 27.21),
                    ("NBIS", 15, 215.0, 3225.0, 3803.85, 253.59)]
        actual = [(x["ticker"], x["quantity"], x["average_cost"], x["purchase_amount"], x["valuation_amount"], x["broker_display_price"]) for x in self.sample["positions"]]
        self.assertEqual(actual, expected)
        self.assertEqual(self.sample["account_summary_krw"]["purchase_amount"], 41170617)

    def test_v25_bs_22_sample_requires_confirmation(self):
        proposal = build_proposal(self.sample, self.state())
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertIn("HOLDINGS_COMPLETENESS_USER_CONFIRMATION", proposal["unresolved_fields"])

    def test_v25_bs_23_cash_only_patch_cannot_replace_holdings(self):
        value = copy.deepcopy(self.sample)
        value.update({"scope": "CASH_ONLY", "positions": [], "holdings_complete_status": "NOT_APPLICABLE",
                      "position_currency": None, "position_currency_status": "NOT_APPLICABLE",
                      "cash_status": "VERIFIED_AVAILABLE", "available_cash": 1250.0,
                      "cash_classification": "AVAILABLE_SETTLED", "account_scope_complete": True})
        proposal = build_proposal(value, self.state())
        self.assertEqual(proposal["proposed_patch"], {"available_cash_usd": 1250.0})

    def test_v25_bs_24_position_only_patch_is_merge_scoped(self):
        value = copy.deepcopy(self.sample)
        value.update({"scope": "POSITION_ONLY", "positions": [value["positions"][0]],
                      "holdings_complete_status": "NOT_APPLICABLE", "account_scope_complete": False})
        proposal = build_proposal(value, self.state())
        self.assertEqual(set(proposal["proposed_patch"]), {"position_updates"})
        self.assertEqual(set(proposal["proposed_patch"]["position_updates"]), {"SOXL"})

    def test_v25_bs_25_shadow_acceptance_proposal_validates(self):
        artifact = load_json(ROOT / "workspace/outputs/v2_5_shadow/fixture-acceptance/broker-reconciliation-proposal.test-only.json")
        from validation_common import validate_instance
        self.assertEqual(validate_instance(artifact, self.schema), [])

    def test_v25_bs_26_apply_rejects_path_alias(self):
        state = self.state(); proposal = build_proposal(self.sample, state)
        directory = ROOT / "workspace/outputs/v2_5_shadow"
        state_path = directory / "test-broker-alias-state.json"
        try:
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BROKER_APPLY_PATH_ALIAS_REJECTED"):
                apply_confirmed(state_path=state_path, proposal=proposal,
                    confirmation={"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"]},
                    proposal_schema=self.schema, audit_path=state_path)
        finally:
            state_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
