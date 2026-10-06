from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy" / "scripts"))

import migrate_integrated_shadow_cohort as migration  # noqa: E402
from shadow_acceptance import initial_progress  # noqa: E402
from validation_common import load_json, validate_instance  # noqa: E402


SUPERSEDED_SCHEMA = ROOT / "manage-us-stock-strategy" / "schemas" / "superseded-shadow-cohort.schema.json"
OLD_FINGERPRINT = "a" * 64
NEW_FINGERPRINT = "b" * 64
STAMP = "2026-10-06T00:00:00+00:00"
OUT_OF_ENUM_REASON = "I0B_TIMING_SLOT_RETIREMENT"


class MigrateIntegratedShadowCohortReasonTests(unittest.TestCase):
    """--reason is optional, schema-enum bound, and the default archive reason is unchanged."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.progress = self.root / "workspace/state/integrated_shadow/shadow_progress.json"
        self.progress.parent.mkdir(parents=True)
        prior = initial_progress(OLD_FINGERPRINT, "2026-10-05T00:00:00+00:00")
        self.progress.write_text(json.dumps(prior, indent=2) + "\n", encoding="utf-8")
        patcher = patch.object(migration, "semantic_fingerprint", return_value=NEW_FINGERPRINT)
        patcher.start()
        self.addCleanup(patcher.stop)

    def archive(self) -> dict:
        return load_json(self.root / "workspace/state/integrated_shadow/cohorts"
                         / f"integrated-shadow-{OLD_FINGERPRINT[:16]}" / "superseded_progress.json")

    def run_cli(self, *extra: str) -> int:
        argv = ["migrate_integrated_shadow_cohort.py", "--repo-root", str(self.root), *extra]
        with patch.object(sys, "argv", argv), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return migration.main()

    def test_default_reason_is_unchanged(self) -> None:
        self.assertEqual(migration.DEFAULT_REASON, "GLOBAL_AUTHORITY_VOLUME_AND_DUAL_RUN_SEMANTICS_CHANGE")
        self.assertEqual(self.run_cli(), 0)
        archive = self.archive()
        self.assertEqual(archive["reason"], "GLOBAL_AUTHORITY_VOLUME_AND_DUAL_RUN_SEMANTICS_CHANGE")
        self.assertEqual(validate_instance(archive, SUPERSEDED_SCHEMA), [])
        self.assertEqual(load_json(self.progress)["semantic_fingerprint"], NEW_FINGERPRINT)

    def test_explicit_reason_is_recorded(self) -> None:
        self.assertEqual(self.run_cli("--reason", "HOLDING_BASELINE_SEMANTIC_CHANGE"), 0)
        archive = self.archive()
        self.assertEqual(archive["reason"], "HOLDING_BASELINE_SEMANTIC_CHANGE")
        self.assertEqual(archive["prior_progress"]["semantic_fingerprint"], OLD_FINGERPRINT)
        self.assertFalse(archive["order_authority"])
        self.assertEqual(validate_instance(archive, SUPERSEDED_SCHEMA), [])
        current = load_json(self.progress)
        self.assertEqual((current["semantic_fingerprint"], current["observed_attempts"],
                          current["valid_shadow_sessions"]), (NEW_FINGERPRINT, 0, 0))

    def test_reason_outside_schema_enum_is_rejected_before_any_write(self) -> None:
        self.assertNotIn(OUT_OF_ENUM_REASON, load_json(SUPERSEDED_SCHEMA)["properties"]["reason"]["enum"])
        before = self.progress.read_bytes()
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_SUPERSEDED_COHORT_REASON"):
            migration.migrate(self.root, generated_at=STAMP, reason=OUT_OF_ENUM_REASON)
        with self.assertRaises(SystemExit) as raised:
            self.run_cli("--reason", OUT_OF_ENUM_REASON)
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(self.progress.read_bytes(), before)
        self.assertFalse((self.root / "workspace/state/integrated_shadow/cohorts").exists())


if __name__ == "__main__":
    unittest.main()
