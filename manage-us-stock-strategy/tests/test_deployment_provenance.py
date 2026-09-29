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


def current_deployment_fixture(root):
    """Temporary byte fixtures; Git identity is mocked by each consuming test."""
    import json
    from unittest.mock import patch
    from deployment_provenance import build_provenance
    code_names = (
        "manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py",
        "manage-us-stock-strategy/scripts/portfolio_decision_dashboard.py",
        "manage-us-stock-strategy/scripts/portfolio_decision_order_intent.py",
        "manage-us-stock-strategy/scripts/deployment_provenance.py",
        "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json",
    )
    policy_names = ("workspace/policies/continuous_improvement_policy.json",)
    for name in code_names + policy_names:
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
    scope = root / "workspace/policies/kiwoom-session-aware-priority-policy.json"
    scope.write_bytes((ROOT / scope.relative_to(root)).read_bytes())
    progress = root / "workspace/state/integrated_shadow/shadow_progress.json"
    progress.parent.mkdir(parents=True, exist_ok=True)
    progress.write_text(json.dumps({"cohort_id": "fixture-deployment-cohort"}), encoding="utf-8")
    tasks = []
    for task_id, phase, start in (("automation", "PRE_OPEN_T_MINUS_30", "090000"),
                                 ("post-close-portfolio-strategy", "REGULAR_CLOSE_T_PLUS_30", "163000")):
        target = root / "test-home/.codex/automations" / task_id / "automation.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'id = "{task_id}"\nstatus = "ACTIVE"\nprompt = "{phase}"\n'
                          f'rrule = "DTSTART;TZID=America/New_York:20260814T{start}"\n', encoding="utf-8")
        tasks.append(target)
    with patch("deployment_provenance._git", side_effect=fixture_git):
        return build_provenance(repo=root, task_configs=tasks, code_paths=[root / p for p in code_names],
                                policy_paths=[root / p for p in policy_names], provider_scope_path=scope,
                                progress_path=progress, dependency_paths={})


def fixture_git(repo, *args):
    return "a" * 40 if args[0] == "rev-parse" else "main" if args[0] == "branch" else ""


class CurrentDeploymentProvenanceTests(unittest.TestCase):
    def test_current_bytes_and_head_and_no_repair(self):
        import copy
        import tempfile
        from unittest.mock import patch
        from deployment_provenance import verify_current_provenance
        cases = ("match", "code", "policy", "task", "scope", "cohort", "head", "dirty", "branch", "record", "coverage", "missing")
        expected_errors = (None, "CURRENT_HASH_MISMATCH", "CURRENT_HASH_MISMATCH", "CURRENT_TASK_HASH_MISMATCH",
                           "CURRENT_PROVIDER_SCOPE_HASH_MISMATCH", "CURRENT_SEMANTIC_COHORT_MISMATCH",
                           "CURRENT_HEAD_MISMATCH", "CURRENT_RUNTIME_WORKTREE_DIRTY", "CURRENT_BRANCH_NOT_MAIN",
                           "RECORD_HASH_INVALID", "CURRENT_HASH_COVERAGE_MISSING", "CURRENT_TASK_NOT_VERIFIED")
        for case, expected in zip(cases, expected_errors):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest = current_deployment_fixture(root)
                scope = root / "workspace/policies/kiwoom-session-aware-priority-policy.json"
                progress = root / "workspace/state/integrated_shadow/shadow_progress.json"
                if case in {"code", "policy", "task"}:
                    target = (root / next(iter(manifest[case + "_hashes"]))) if case != "task" else Path(manifest["tasks"][0]["task_config_path"])
                    target.write_bytes(target.read_bytes() + b" ")
                elif case == "scope": scope.write_bytes(b"{}")
                elif case == "cohort": progress.write_bytes(b'{"cohort_id":"changed"}')
                elif case == "record": manifest["record_hash"] = "0" * 64
                elif case == "coverage": manifest["code_hashes"] = {}
                elif case == "missing": Path(manifest["tasks"][0]["task_config_path"]).unlink()
                before = copy.deepcopy(manifest)
                files = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
                def git_state(repo, *args):
                    if case == "head" and args[0] == "rev-parse": return "b" * 40
                    if case == "dirty" and args[0] == "status": return " M changed"
                    if case == "branch" and args[0] == "branch": return "builder"
                    return fixture_git(repo, *args)
                with patch("deployment_provenance._git", side_effect=git_state), \
                        patch("deployment_provenance.Path.home", return_value=root / "test-home"):
                    errors = verify_current_provenance(manifest, expected_head="a" * 40, runtime_repo=root,
                                                       provider_scope_path=scope, progress_path=progress)
                if expected is None: self.assertEqual(errors, [])
                else: self.assertTrue(any(e.startswith(expected) for e in errors), errors)
                self.assertEqual(manifest, before)
                self.assertEqual({p: p.read_bytes() for p in root.rglob("*") if p.is_file()}, files)


def supply_task_config(manifest, task_id, config_path):
    """Make an internally consistent manifest assertion, including its digest."""
    import hashlib
    import tomllib
    raw = config_path.read_bytes()
    value = tomllib.loads(raw.decode("utf-8"))
    task = next(t for t in manifest["tasks"] if t["task_id"] == task_id)
    task.update(task_config_path=str(config_path), task_config_sha256=hashlib.sha256(raw).hexdigest(),
                prompt_sha256=hashlib.sha256(value["prompt"].encode("utf-8")).hexdigest(),
                schedule=value["rrule"])
    manifest["record_hash"] = canonical_hash({k: v for k, v in manifest.items() if k != "record_hash"})


class RegisteredTaskBindingTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from unittest.mock import patch
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = current_deployment_fixture(self.root)
        self.home = self.root / "test-home"
        self.task_id = "post-close-portfolio-strategy"
        self.canonical = self.home / ".codex/automations" / self.task_id / "automation.toml"
        for mocked in (patch("deployment_provenance.Path.home", return_value=self.home),
                       patch("deployment_provenance._git", side_effect=fixture_git)):
            mocked.start()
            self.addCleanup(mocked.stop)

    def verify(self):
        import copy
        from deployment_provenance import verify_current_provenance
        before = copy.deepcopy(self.manifest)
        files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        errors = verify_current_provenance(
            self.manifest, expected_head="a" * 40, runtime_repo=self.root,
            provider_scope_path=self.root / "workspace/policies/kiwoom-session-aware-priority-policy.json",
            progress_path=self.root / "workspace/state/integrated_shadow/shadow_progress.json",
        )
        self.assertEqual(self.manifest, before)
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, files)
        return errors

    def alternate(self, *, identical=False):
        alternate = self.root / "alternate-active.toml"
        raw = self.canonical.read_bytes()
        alternate.write_bytes(raw if identical else raw.replace(b'prompt = "REGULAR_CLOSE_T_PLUS_30"',
                                                                b'prompt = "REGULAR_CLOSE_T_PLUS_30 alternate"'))
        supply_task_config(self.manifest, self.task_id, alternate)
        return alternate

    def assert_alternate_is_otherwise_valid(self):
        from unittest.mock import patch
        # Control: the former supplied-path read accepts this exact manifest.
        with patch("deployment_provenance._read_registered_task_config", side_effect=lambda task, p: Path(p).read_bytes()):
            self.assertEqual(self.verify(), [])

    def test_t1_t9_canonical_config_reads_registered_bytes(self):
        from unittest.mock import patch
        import deployment_provenance as module
        with patch.object(module, "read_once_no_reparse", wraps=module.read_once_no_reparse) as reader:
            self.assertEqual(self.verify(), [])
        self.assertEqual(reader.call_count, 2)
        self.assertEqual({c.args[0] for c in reader.call_args_list},
                         {self.home / ".codex/automations" / task / "automation.toml" for task in module.REGISTERED_TASK_PHASES})
        self.assertTrue(all(c.args[1] == self.home for c in reader.call_args_list))

    def test_t2_t10_alternate_active_config_is_not_authority(self):
        self.alternate()
        self.assert_alternate_is_otherwise_valid()
        self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())

    def test_t3_byte_identical_copy_is_not_authority(self):
        alternate = self.alternate(identical=True)
        self.assertEqual(alternate.read_bytes(), self.canonical.read_bytes())
        self.assert_alternate_is_otherwise_valid()
        self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())

    def test_t4_other_registered_task_is_not_the_claimed_task(self):
        sibling = self.home / ".codex/automations/automation/automation.toml"
        supply_task_config(self.manifest, self.task_id, sibling)
        self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())
        self.canonical.write_bytes(sibling.read_bytes())
        supply_task_config(self.manifest, self.task_id, self.canonical)
        self.assertIn(f"CURRENT_TASK_BINDING_MISMATCH:{self.task_id}", self.verify())

    def test_t5_paused_canonical_task_cannot_be_hidden_by_active_copy(self):
        self.alternate(identical=True)
        self.canonical.write_bytes(self.canonical.read_bytes().replace(b'"ACTIVE"', b'"PAUSED"'))
        self.assert_alternate_is_otherwise_valid()
        self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())

    def test_canonical_paused_state_blocks_even_with_matching_hash(self):
        self.canonical.write_bytes(self.canonical.read_bytes().replace(b'"ACTIVE"', b'"PAUSED"'))
        supply_task_config(self.manifest, self.task_id, self.canonical)
        self.assertIn(f"CURRENT_TASK_BINDING_MISMATCH:{self.task_id}", self.verify())

    def test_t6_current_prompt_and_schedule_changes_invalidate_stored_hash(self):
        original = self.canonical.read_bytes()
        for old, new in ((b"163000", b"173000"), (b"REGULAR_CLOSE_T_PLUS_30", b"changed-prompt")):
            with self.subTest(field=old):
                self.canonical.write_bytes(original.replace(old, new))
                errors = self.verify()
                self.assertIn(f"CURRENT_TASK_HASH_MISMATCH:{self.task_id}", errors)
                self.assertIn(f"CURRENT_TASK_BINDING_MISMATCH:{self.task_id}", errors)

    def test_t7_relative_and_traversal_paths_are_rejected(self):
        task = next(t for t in self.manifest["tasks"] if t["task_id"] == self.task_id)
        for candidate in (Path(".codex/automations") / self.task_id / "automation.toml",
                          self.canonical.parent / ".." / self.task_id / "automation.toml"):
            with self.subTest(path=str(candidate)):
                task["task_config_path"] = str(candidate)
                self.manifest["record_hash"] = canonical_hash({k: v for k, v in self.manifest.items() if k != "record_hash"})
                self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())

    def test_t7_canonical_directory_reparse_redirection_is_rejected(self):
        import os
        import subprocess
        redirected = self.root / "redirected-task"
        redirected.mkdir()
        (redirected / "automation.toml").write_bytes(self.canonical.read_bytes())
        task_directory = self.canonical.parent
        self.assertTrue(task_directory.resolve().is_relative_to(self.root.resolve()))
        self.assertTrue(redirected.resolve().is_relative_to(self.root.resolve()))
        self.canonical.unlink()
        task_directory.rmdir()
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(task_directory), str(redirected)],
                           cwd=self.root, check=True, capture_output=True)
        else:
            task_directory.symlink_to(redirected, target_is_directory=True)
        self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())

    def test_host_case_semantics_do_not_authorize_a_different_file(self):
        import os
        from unittest.mock import patch
        from deployment_provenance import _read_registered_task_config
        spelling = str(self.canonical).swapcase()
        if os.name == "nt":
            self.assertEqual(_read_registered_task_config(self.task_id, spelling), self.canonical.read_bytes())
        else:
            with self.assertRaises(ValueError): _read_registered_task_config(self.task_id, spelling)
        with patch("deployment_provenance.read_once_no_reparse") as reader:
            with self.assertRaises(ValueError): _read_registered_task_config("../automation", str(self.canonical))
            reader.assert_not_called()

    def test_t11_reparse_swap_at_read_fails_without_mutation(self):
        from unittest.mock import patch
        from authority_artifact_io import AuthorityArtifactIOError
        for error in (AuthorityArtifactIOError("REPARSE_POINT"), PermissionError("READ_DENIED")):
            with self.subTest(error=type(error).__name__), patch("deployment_provenance.read_once_no_reparse", side_effect=error):
                self.assertIn(f"CURRENT_TASK_NOT_VERIFIED:{self.task_id}", self.verify())
