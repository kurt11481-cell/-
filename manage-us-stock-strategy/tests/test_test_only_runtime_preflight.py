from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "manage-us-stock-strategy"
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import test_only_runtime_preflight as preflight


HEAD = "A" * 40
TREE = "B" * 40


class TestOnlyRuntimePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent / f".test-only-preflight-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.deployment = self._write("deployment.json", {
            "status": "DEPLOYMENT_PROVENANCE_VERIFIED",
            "runtime_head": HEAD,
        })
        self.calendar = self._write("calendar.json", {
            "official_calendar_verified": True,
            "is_trading_day": True,
            "source_url": "https://www.nyse.com/trade/hours-calendars",
        })
        self.kiwoom = self._write("kiwoom.json", {
            "capability_status": "AVAILABLE",
            "order_authority": False,
            "secrets_exposed": False,
        })
        self.protected = self._write("protected.json", {"unchanged": True})

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def _write(self, name: str, value: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def _clock(self) -> dict:
        return {
            "status": "VERIFIED",
            "system_utc": datetime.now(timezone.utc).isoformat(),
            "derived_america_new_york": "2026-08-17T20:00:00-04:00",
            "configured_timezone": "Korea Standard Time",
            "clock_sync_source": "TEST_FIXTURE",
            "clock_sync_status": "PASS",
        }

    def _run(self, injection: str = "NONE") -> dict:
        config = self.root / f"{injection}.config.json"
        output = self.root / f"{injection}.result.json"
        preflight.prepare_config(
            config_path=config,
            output_path=output,
            runtime=self.runtime,
            deployment_manifest=self.deployment,
            calendar_evidence=self.calendar,
            kiwoom_preflight=self.kiwoom,
            expected_head=HEAD,
            expected_tree=TREE,
            git_executable=Path(sys.executable),
            schema=SKILL / "schemas" / "test-only-runtime-preflight.schema.json",
            protected_paths=[self.protected],
            failure_injection=injection,
        )
        original_git = preflight.git_value
        original_clock = preflight.collect_host_clock_evidence
        preflight.git_value = lambda _runtime, *args, **_kwargs: {
            ("rev-parse", "HEAD"): HEAD,
            ("rev-parse", "HEAD^{tree}"): TREE,
            ("status", "--porcelain"): "",
        }[args]
        preflight.collect_host_clock_evidence = self._clock
        try:
            result, _ = preflight.run_preflight(config)
        finally:
            preflight.git_value = original_git
            preflight.collect_host_clock_evidence = original_clock
        return result

    def test_runtime_preflight_passes_without_running_production(self) -> None:
        result = self._run()
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["production_runtime_invoked"])
        self.assertFalse(result["maturity_eligible"])
        self.assertTrue(result["protected_state_unchanged"])

    def test_failure_injections_fail_closed(self) -> None:
        for injection in sorted(preflight.ALLOWED_FAILURE_INJECTIONS - {"NONE"}):
            with self.subTest(injection=injection):
                result = self._run(injection)
                self.assertEqual(result["status"], "FAIL_CLOSED")
                self.assertEqual(result["portfolio_effect"], "NONE")
                self.assertEqual(result["core_counter_effect"], "NONE")
                self.assertFalse(result["genuine_artifact_created"])

    def test_config_hash_tampering_is_rejected(self) -> None:
        config = self.root / "tamper.json"
        preflight.prepare_config(
            config_path=config,
            output_path=self.root / "output.json",
            runtime=self.runtime,
            deployment_manifest=self.deployment,
            calendar_evidence=self.calendar,
            kiwoom_preflight=self.kiwoom,
            expected_head=HEAD,
            expected_tree=TREE,
            git_executable=Path(sys.executable),
            schema=SKILL / "schemas" / "test-only-runtime-preflight.schema.json",
            protected_paths=[],
        )
        value = json.loads(config.read_text(encoding="utf-8"))
        value["expected_runtime_head"] = "C" * 40
        config.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "PREFLIGHT_CONFIG_HASH_MISMATCH"):
            preflight.run_preflight(config)


if __name__ == "__main__":
    unittest.main()
