#!/usr/bin/env python3
"""Manual-run code provenance (I4 R6 item 7): commit, branch, code-scoped dirty state."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
TESTS = ROOT / "manage-us-stock-strategy" / "tests"
for entry in (SCRIPTS, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

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


SCHEMA = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
PROVENANCE_POLICY = ROOT / "workspace/policies/continuous_improvement_policy.json"
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def fake_git(*, commit=COMMIT, branch="codex/example", status="", fail_on=None):
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        subcommand = command[4]
        if fail_on == subcommand:
            return SimpleNamespace(returncode=128, stdout="", stderr="fatal")
        output = {"rev-parse": commit + "\n", "branch": branch + "\n", "status": status}[subcommand]
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    return runner, calls


class CollectCodeProvenanceTest(unittest.TestCase):
    def test_clean_code_tree_is_k3_eligible(self):
        runner, calls = fake_git()
        value = manual.collect_code_provenance(Path("repo"), runner=runner)
        self.assertEqual({
            "status": "CLEAN_CODE_TREE", "git_commit": COMMIT, "git_branch": "codex/example",
            "code_tree_dirty": False, "dirty_scope": "manage-us-stock-strategy/",
            "k3_evidence_eligible": True,
        }, value)
        status_call = calls[-1]
        self.assertEqual(["git", "--no-optional-locks", "-C", "repo", "status"], status_call[:5])
        self.assertEqual(["--", "manage-us-stock-strategy/"], status_call[-2:])

    def test_dirty_code_tree_is_never_k3_evidence(self):
        runner, _ = fake_git(status=" M manage-us-stock-strategy/scripts/x.py\n")
        value = manual.collect_code_provenance(Path("repo"), runner=runner)
        self.assertEqual("DIRTY_CODE_TREE", value["status"])
        self.assertTrue(value["code_tree_dirty"])
        self.assertFalse(value["k3_evidence_eligible"])

    def test_untracked_code_counts_as_dirty(self):
        runner, _ = fake_git(status="?? manage-us-stock-strategy/scripts/new.py\n")
        self.assertEqual("DIRTY_CODE_TREE", manual.collect_code_provenance(Path("repo"), runner=runner)["status"])

    def test_detached_head_has_no_branch(self):
        runner, _ = fake_git(branch="")
        value = manual.collect_code_provenance(Path("repo"), runner=runner)
        self.assertIsNone(value["git_branch"])
        self.assertEqual("CLEAN_CODE_TREE", value["status"])

    def test_git_failures_are_unavailable_not_clean(self):
        cases = [fake_git(fail_on="rev-parse")[0], fake_git(fail_on="status")[0],
                 fake_git(commit="not-a-sha")[0]]

        def raises(exc):
            def runner(command, **kwargs):
                raise exc
            return runner

        cases += [raises(FileNotFoundError("git")), raises(subprocess.TimeoutExpired("git", 30)),
                  raises(UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"))]
        for runner in cases:
            with self.subTest(runner=runner):
                value = manual.collect_code_provenance(Path("repo"), runner=runner)
                self.assertEqual("CODE_PROVENANCE_UNAVAILABLE", value["status"])
                self.assertIsNone(value["git_commit"])
                self.assertFalse(value["k3_evidence_eligible"])


class ReportCodeProvenanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance_policy = json.loads(PROVENANCE_POLICY.read_text(encoding="utf-8"))

    def setUp(self):
        def identity_resolver(ticker, *, decision_as_of=None, authority_mode="CURRENT"):
            return synthetic_identity_view(ticker=ticker, operating_mic="XNAS")

        def session_resolver(observed_at, *, primary_listing_operating_mic,
                             decision_as_of=None, authority_mode="CURRENT"):
            return synthetic_authority_view(mic=primary_listing_operating_mic, expected_session=PREVIOUS_DAY)

        for name, side_effect in (("resolve_instrument_identity", identity_resolver),
                                  ("derive_us_market_session_authority", session_resolver)):
            patcher = patch.object(manual, name, side_effect=side_effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def build_report(self, **kwargs):
        state = system_portfolio()
        return manual.run_manual_preflight(
            manual_run_id="manual-code-provenance-0001", system_portfolio=state,
            system_portfolio_source="TEST_ONLY/system-portfolio.json", system_portfolio_sha256="a" * 64,
            provenance_policy=self.provenance_policy,
            account_reader=account_reader_for(state["holdings"], state["average_cost_usd"]),
            market_reader=market_reader_for(sorted(state["holdings"])),
            maximum_broker_age_seconds=900, decision_as_of=OBSERVED_AT, observed_at=OBSERVED_AT,
            **kwargs,
        )

    def test_default_report_is_unchanged(self):
        report = self.build_report()
        self.assertNotIn("code_provenance", report)
        self.assertEqual([], validate_instance(report, SCHEMA))

    def test_clean_provenance_is_recorded_without_unknown(self):
        runner, _ = fake_git()
        baseline = self.build_report()
        report = self.build_report(code_provenance=manual.collect_code_provenance(Path("repo"), runner=runner))
        self.assertEqual("CLEAN_CODE_TREE", report["code_provenance"]["status"])
        self.assertEqual(baseline["unknowns"], report["unknowns"])
        self.assertEqual(baseline["preflight_status"], report["preflight_status"])
        self.assertEqual(baseline["evidence_grade"], report["evidence_grade"])
        self.assertEqual([], validate_instance(report, SCHEMA))

    def test_dirty_or_unavailable_provenance_is_visible_but_does_not_change_grade(self):
        baseline = self.build_report()
        for status, runner in (("DIRTY_CODE_TREE", fake_git(status=" M manage-us-stock-strategy/a.py\n")[0]),
                               ("CODE_PROVENANCE_UNAVAILABLE", fake_git(fail_on="rev-parse")[0])):
            with self.subTest(status=status):
                report = self.build_report(
                    code_provenance=manual.collect_code_provenance(Path("repo"), runner=runner))
                self.assertIn(status, report["unknowns"])
                self.assertFalse(report["code_provenance"]["k3_evidence_eligible"])
                self.assertEqual(baseline["preflight_status"], report["preflight_status"])
                self.assertEqual(baseline["evidence_grade"], report["evidence_grade"])
                self.assertEqual([], validate_instance(report, SCHEMA))

    def test_main_records_code_provenance_for_the_repository(self):
        with patch.object(manual, "collect_code_provenance", return_value={"status": "CLEAN_CODE_TREE"}) as collect, \
             patch.object(manual, "run_manual_preflight", side_effect=RuntimeError("stop")) as run, \
             patch.object(manual, "load_json", return_value={
                 "official_runtime_path": str(ROOT), "maximum_age_seconds": 900}), \
             patch.object(manual, "file_hash", return_value="a" * 64), \
             patch.object(sys, "argv", ["runner", "--runtime", str(ROOT)]):
            with self.assertRaisesRegex(RuntimeError, "stop"):
                manual.main()
        collect.assert_called_once_with(ROOT.resolve())
        self.assertEqual({"status": "CLEAN_CODE_TREE"}, run.call_args.kwargs["code_provenance"])


if __name__ == "__main__":
    unittest.main()
