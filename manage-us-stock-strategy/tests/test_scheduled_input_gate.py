#!/usr/bin/env python3
"""Pinned tests for the scheduled input validation gate (I4 R6).

The gate moved from run_manual_portfolio_analysis.py to scheduled_input_gate.py.
These tests call the pinned gate directly, repeat the registered-task checks
from test_manual_portfolio_analysis.ScheduledRegisteredTaskBindingTests, and
prove the released adapter still delegates to this gate.
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
TESTS = ROOT / "manage-us-stock-strategy" / "tests"
for entry in (SCRIPTS, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import run_manual_portfolio_analysis as manual  # noqa: E402
import scheduled_input_gate as gate  # noqa: E402


class ScheduledInputGateShapeTest(unittest.TestCase):
    def test_missing_run_or_manifest_is_rejected_before_any_read(self):
        verify = Mock(side_effect=AssertionError("deployment must not be read"))
        with patch("deployment_provenance.verify_current_provenance", verify):
            for supplied in (None, {}, {"run": None}, {"run": {}},
                             {"run": {"provenance_evidence": {}}},
                             {"run": {"provenance_evidence": {}}, "deployment_provenance": None}):
                with self.subTest(supplied=supplied), self.assertRaisesRegex(
                        ValueError, "^SCHEDULED_PROVENANCE_REQUIRED$"):
                    gate.validate_scheduled_input(
                        {}, supplied, evidence_sha256="a" * 64, expected_head="a" * 40,
                    )
        verify.assert_not_called()

    def test_adapter_name_is_a_thin_delegate_to_the_pinned_gate(self):
        sentinel = {"run_provenance_status": "VERIFIED_SCHEDULED_GENUINE"}
        with patch.object(gate, "validate_scheduled_input", return_value=sentinel) as pinned:
            result = manual.validate_scheduled_input(
                {"e": 1}, {"s": 2}, evidence_sha256="b" * 64, expected_head="c" * 40,
            )
        self.assertIs(sentinel, result)
        kwargs = pinned.call_args.kwargs
        self.assertEqual("b" * 64, kwargs["evidence_sha256"])
        self.assertEqual("c" * 40, kwargs["expected_head"])
        self.assertIs(manual.derive_run_provenance, kwargs["provenance_deriver"])

    def test_only_the_adapter_reaches_the_gate_and_only_with_the_canonical_deriver(self):
        """provenance_deriver is a test seam; no production caller may pass anything else."""
        importers = {}
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name == "scheduled_input_gate.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                if any(name.split(".")[0] == "scheduled_input_gate" for name in names):
                    importers.setdefault(path.name, []).append(type(node).__name__)
        self.assertEqual({"run_manual_portfolio_analysis.py": ["Import"]}, importers)

        tree = ast.parse((SCRIPTS / "run_manual_portfolio_analysis.py").read_text(encoding="utf-8"))
        gate_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "scheduled_input_gate"
        ]
        self.assertEqual(["validate_scheduled_input"], [call.func.attr for call in gate_calls])
        deriver = [keyword.value for keyword in gate_calls[0].keywords if keyword.arg == "provenance_deriver"]
        self.assertEqual(1, len(deriver))
        self.assertIsInstance(deriver[0], ast.Name)
        self.assertEqual("derive_run_provenance", deriver[0].id)
        canonical_imports = [
            node for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "continuous_improvement_sidecar"
            and any(alias.name == "derive_run_provenance" and alias.asname is None for alias in node.names)
        ]
        self.assertEqual(1, len(canonical_imports))
        rebinds = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.FunctionDef))
            and ("derive_run_provenance" in [getattr(target, "id", None) for target in getattr(node, "targets", [])]
                 or getattr(getattr(node, "target", None), "id", None) == "derive_run_provenance"
                 or getattr(node, "name", None) == "derive_run_provenance")
        ]
        self.assertEqual([], rebinds)


class ScheduledInputGateRegisteredTaskTest(unittest.TestCase):
    """Same fixture as test_manual_portfolio_analysis.ScheduledRegisteredTaskBindingTests."""

    def setUp(self):
        from test_portfolio_decision_dashboard import scheduled_compilation_fixture
        from test_deployment_provenance import fixture_git
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args = scheduled_compilation_fixture(self.root)
        self.home = self.root / "test-home"
        for mocked in (patch("deployment_provenance.Path.home", return_value=self.home),
                       patch("deployment_provenance._git", side_effect=fixture_git)):
            mocked.start()
            self.addCleanup(mocked.stop)

    def validate(self, *, validator=None, **extra):
        source, supplied = self.args["evidence"], self.args["scheduled_provenance"]
        before = copy.deepcopy((source, supplied))
        files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        try:
            return (validator or gate.validate_scheduled_input)(
                source, supplied, evidence_sha256=self.args["input_hashes"]["portfolio_evidence"],
                expected_head="a" * 40, runtime_repo=self.root,
                session_authority_resolver=self.args["current_session_authority_resolver"],
                **extra,
            )
        finally:
            self.assertEqual((source, supplied), before)
            self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, files)

    def test_canonical_registered_provenance_passes(self):
        result = self.validate()
        self.assertEqual(result["run_provenance_status"], "VERIFIED_SCHEDULED_GENUINE")
        self.assertTrue(result["actual_scheduled_run"])
        self.assertEqual(result["operational_grade"], "GRADE_A_CANDIDATE")
        self.assertFalse(result["scheduled_maturity_promoted"])

    def test_adapter_and_gate_agree_and_adapter_uses_its_deriver_name(self):
        direct = self.validate()
        with patch.object(manual, "derive_run_provenance", wraps=manual.derive_run_provenance) as derive:
            through_adapter = self.validate(validator=manual.validate_scheduled_input)
        self.assertEqual(direct, through_adapter)
        derive.assert_called_once()

    def test_masquerade_with_alternate_config_blocks_before_provenance_derivation(self):
        from test_deployment_provenance import supply_task_config
        supplied = self.args["scheduled_provenance"]
        task_id = supplied["task_id"]
        canonical = self.home / ".codex/automations" / task_id / "automation.toml"
        alternate = self.root / "forged-active.toml"
        alternate.write_bytes(canonical.read_bytes())
        canonical.write_bytes(canonical.read_bytes().replace(b'"ACTIVE"', b'"PAUSED"'))
        supply_task_config(supplied["deployment_provenance"], task_id, alternate)
        digest = supplied["deployment_provenance"]["record_hash"]
        supplied["run"]["runtime_manifest_hash"] = digest
        supplied["run"]["provenance_evidence"]["runtime_manifest_hash"] = digest
        with patch("deployment_provenance._read_registered_task_config",
                   side_effect=lambda task, p: Path(p).read_bytes()):
            self.assertTrue(self.validate()["actual_scheduled_run"])
        deriver = Mock(wraps=gate.derive_run_provenance)
        with self.assertRaisesRegex(ValueError, "SCHEDULED_DEPLOYMENT_NOT_VERIFIED:.*CURRENT_TASK_NOT_VERIFIED"):
            self.validate(provenance_deriver=deriver)
        deriver.assert_not_called()

    def test_canonical_path_does_not_promote_grade_b(self):
        from test_portfolio_decision_dashboard import bind_scheduled_fixture
        self.args["evidence"]["evidence_grade"] = "GRADE_B"
        self.args["evidence"]["provenance"]["evidence_grade"] = "GRADE_B"
        bind_scheduled_fixture(self.args)
        with self.assertRaisesRegex(ValueError, "SCHEDULED_EVIDENCE_MODE_MISMATCH"):
            self.validate()

    def test_failed_provenance_derivation_blocks(self):
        deriver = Mock(return_value={"run_provenance_status": "UNVERIFIED", "decision_quality_eligible": False})
        with self.assertRaisesRegex(ValueError, "SCHEDULED_CANONICAL_PROVENANCE_NOT_VERIFIED"):
            self.validate(provenance_deriver=deriver)
        deriver.assert_called_once()


if __name__ == "__main__":
    unittest.main()
