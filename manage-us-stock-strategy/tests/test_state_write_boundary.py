#!/usr/bin/env python3
"""Pinned analysis -> state-write boundary tests (I4 R6).

test_04 and test_08 originally lived in the released
test_manual_portfolio_analysis.py; they are kept there and repeated here, in a
pinned file, with the same assertions and a wider sentinel set. Only fixture
helpers are imported from that module, never its TestCase classes.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
TESTS = ROOT / "manage-us-stock-strategy" / "tests"
for entry in (SCRIPTS, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import manual_data_guards as guards  # noqa: E402
import run_manual_portfolio_analysis as manual  # noqa: E402
from test_manual_portfolio_analysis import (  # noqa: E402
    OBSERVED_AT,
    PREVIOUS_DAY,
    account_reader_for,
    market_reader_for,
    synthetic_authority_view,
    synthetic_identity_view,
    system_portfolio,
)
from validation_common import validate_instance  # noqa: E402


MODULE_PATH = SCRIPTS / "run_manual_portfolio_analysis.py"
PINNED_MANUAL_MODULES = (
    SCRIPTS / "manual_data_guards.py",
    SCRIPTS / "scheduled_input_gate.py",
)
SCHEMA = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
PROVENANCE_POLICY = ROOT / "workspace/policies/continuous_improvement_policy.json"
FORBIDDEN_MODULES = {
    "run_portfolio_strategy_orchestrator",
    "automation_delivery",
    "shadow_acceptance",
    "apply_user_confirmed_broker_snapshot",
    "migrate_integrated_shadow_cohort",
    # R6 additions: other state or journal writers stay out of the analysis path.
    "reconcile_broker_state",
    "portfolio_review_journal",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    return imported


class ManualAnalysisStateWriteBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance_policy = json.loads(PROVENANCE_POLICY.read_text(encoding="utf-8"))

    def setUp(self):
        def identity_resolver(ticker, *, decision_as_of=None, authority_mode="CURRENT"):
            del decision_as_of, authority_mode
            return synthetic_identity_view(ticker=ticker, operating_mic="XNAS")

        def session_resolver(observed_at, *, primary_listing_operating_mic,
                             decision_as_of=None, authority_mode="CURRENT"):
            del observed_at, decision_as_of, authority_mode
            return synthetic_authority_view(mic=primary_listing_operating_mic,
                                            expected_session=PREVIOUS_DAY)

        for name, side_effect in (("resolve_instrument_identity", identity_resolver),
                                  ("derive_us_market_session_authority", session_resolver)):
            patcher = patch.object(manual, name, side_effect=side_effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def build_report(self, *, run_manual_preflight=None, **kwargs) -> dict:
        state = system_portfolio()
        return (run_manual_preflight or manual.run_manual_preflight)(
            manual_run_id=kwargs.pop("manual_run_id", "manual-boundary-test-0001"),
            system_portfolio=state,
            system_portfolio_source="TEST_ONLY/system-portfolio.json",
            system_portfolio_sha256="a" * 64,
            provenance_policy=self.provenance_policy,
            account_reader=account_reader_for(state["holdings"], state["average_cost_usd"]),
            market_reader=market_reader_for(sorted(state["holdings"])),
            maximum_broker_age_seconds=900,
            decision_as_of=OBSERVED_AT,
            observed_at=OBSERVED_AT,
            **kwargs,
        )

    def test_04_writer_order_and_mutation_sentinels_are_never_called(self):
        calls = []

        def fail(name):
            def sentinel(*args, **kwargs):
                calls.append(name)
                raise AssertionError(f"forbidden capability called: {name}")
            return sentinel

        with patch("pathlib.Path.write_text", side_effect=fail("file_writer")), \
             patch("pathlib.Path.write_bytes", side_effect=fail("byte_writer")), \
             patch("pathlib.Path.unlink", side_effect=fail("file_delete")), \
             patch("os.replace", side_effect=fail("atomic_overwrite")), \
             patch("os.rename", side_effect=fail("rename")):
            report = self.build_report()
        self.assertEqual([], calls)
        self.assertEqual("REPORT_ONLY_CREATE_ONLY", report["mutation_status"])
        self.assertFalse(report["order_authority"])
        self.assertEqual("none", report["quantity_authority"])
        self.assertIsNone(report["execution_quantity"])
        self.assertEqual([], validate_instance(report, SCHEMA))

    def test_08_forbidden_high_level_entrypoints_are_absent_and_not_called(self):
        self.assertTrue(FORBIDDEN_MODULES.isdisjoint(_imported_modules(MODULE_PATH)))
        for pinned in PINNED_MANUAL_MODULES:
            with self.subTest(module=pinned.name):
                self.assertTrue(FORBIDDEN_MODULES.isdisjoint(_imported_modules(pinned)))

        calls = []
        fake_modules = {}
        for name in FORBIDDEN_MODULES:
            fake = types.ModuleType(name)
            fake.main = lambda *args, _name=name, **kwargs: calls.append(_name)
            fake_modules[name] = fake
        spec = importlib.util.spec_from_file_location("manual_boundary_isolated_import", MODULE_PATH)
        self.assertIsNotNone(spec)
        isolated = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, fake_modules):
            assert spec.loader is not None
            spec.loader.exec_module(isolated)
            with patch.object(isolated, "resolve_instrument_identity", manual.resolve_instrument_identity), \
                 patch.object(isolated, "derive_us_market_session_authority",
                              manual.derive_us_market_session_authority):
                self.build_report(run_manual_preflight=isolated.run_manual_preflight)
        self.assertEqual([], calls)

    def test_normalization_failure_hard_fails_and_never_uses_empty_broker_holdings(self):
        with patch.object(guards, "normalize_snapshot", side_effect=ValueError("BROKER_OPERATION_NOT_ALLOWLISTED")):
            report = self.build_report()
        self.assertIn(guards.BROKER_NORMALIZATION_FAILED, report["hard_fail_reasons"])
        self.assertIn("BROKER_HOLDINGS_UNAVAILABLE", report["hard_fail_reasons"])
        self.assertEqual("FAIL", report["preflight_status"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])
        self.assertEqual("UNAVAILABLE", report["broker_snapshot_status"])
        self.assertEqual("UNKNOWN", report["broker_diff_status"])
        self.assertEqual("SYSTEM_PORTFOLIO_STATE_FALLBACK", report["manual_analysis_view"]["holding_source"])
        self.assertEqual({"AAA": 1.0}, report["manual_analysis_view"]["holdings"])
        self.assertFalse(report["order_authority"])
        self.assertEqual([], validate_instance(report, SCHEMA))


if __name__ == "__main__":
    unittest.main()
