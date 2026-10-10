"""Tests for the dev pipeline (redesign T3): tools/dev_pipeline/devpipe.py and the tools/*.ps1 scripts.

The git checks run against throw-away repositories in a temp folder; nothing here starts claude,
registers a Windows task or touches the real repository state.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools" / "dev_pipeline"
sys.path.insert(0, str(PIPELINE))
import devpipe  # noqa: E402

TASK = "t-demo"
BLOCK = {
    "task_id": TASK,
    "class": "general",
    "builder_model": "sonnet",
    "builder_effort": "high",
    "max_turns": 40,
    "builder_timeout_min": 30,
    "allowed_paths": [
        "manage-us-stock-strategy/scripts/app.py",
        "manage-us-stock-strategy/scripts/auth_gate.py",
        "manage-us-stock-strategy/scripts/newmod/",
        "manage-us-stock-strategy/tests/test_app.py",
        "docs/claude/t-demo-report.md",
    ],
    "target_tests": ["test_app*.py"],
    "commit_message": "feat: demo change",
}
TEST_APP = (b"import unittest\r\n\r\n\r\nclass T(unittest.TestCase):\r\n    def test_a(self):\r\n        pass\r\n\r\n"
            b"    def test_b(self):\r\n        pass\r\n")


def prompt_text(block):
    return "# demo task\r\n\r\n```dev-run\r\n%s\r\n```\r\n\r\n## Judge 확인 항목\r\n- J1 demo\r\n" % json.dumps(block)


def _remove_readonly(func, path, _info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_remove_readonly)
    else:
        shutil.rmtree(path, onerror=_remove_readonly)


def run_git(cwd, *args):
    proc = subprocess.run(["git", *args], cwd=str(cwd), stdin=subprocess.DEVNULL, capture_output=True)
    if proc.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), proc.stderr.decode("utf-8", "replace")))
    return proc.stdout.decode("utf-8", "replace").strip()


def judge_envelope(verdict="PASS", class_ok=True, min_fixes=None, is_error=False, last_line=None, with_json=True):
    body = {"verdict": verdict, "class_ok": class_ok, "items": [{"id": "G1", "result": verdict}],
            "min_fixes": min_fixes if min_fixes is not None else ([] if verdict == "PASS" else ["fix x"])}
    text = "| 항목 | 결과 | 근거 |\n|---|---|---|\n| G1 | %s | a.py:1 |\n\n" % verdict
    if with_json:
        text += "```json\n%s\n```\n" % json.dumps(body, ensure_ascii=False)
    text += (last_line if last_line is not None else "VERDICT: %s" % verdict) + "\n"
    envelope = {"type": "result", "subtype": "success", "is_error": is_error, "result": text, "num_turns": 5}
    return json.dumps(envelope, ensure_ascii=False).encode("utf-8")


class RepoFixture:
    """A temp main repository with one pipeline worktree at .claude/worktrees/t-demo."""

    def __init__(self, case, block=None, extra_files=None):
        self.block = dict(block or BLOCK)
        self.tmp = Path(tempfile.mkdtemp(prefix="devpipe-test-"))
        case.addCleanup(remove_tree, self.tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        files = {
            ".gitignore": b".claude/worktrees/\n.claude/settings.local.json\nCLAUDE.local.md\n"
                          b"workspace/outputs/dev-runs/\n*.log\n__pycache__/\n",
            "CLAUDE.md": b"rules\n",
            ".claude/settings.json": b"{}\n",
            "tools/dev_pipeline/authority-paths.txt": b"# test\nmanage-us-stock-strategy/scripts/auth_*.py\n",
            "tools/dev_pipeline/judge-prompt.md": b"judge\n",
            "tools/dev_pipeline/builder-rules.md": b"rules\n",
            "docs/claude/t-demo-builder-prompt.md": prompt_text(self.block).encode("utf-8"),
            "docs/claude/notes.md": b"notes\n",
            "manage-us-stock-strategy/scripts/app.py": b"def f():\r\n    return 1\r\n",
            "manage-us-stock-strategy/scripts/lf.py": b"x = 1\n",
            "manage-us-stock-strategy/scripts/auth_gate.py": b"LIMIT = 1\r\n",
            "manage-us-stock-strategy/tests/test_app.py": TEST_APP,
        }
        files.update(extra_files or {})
        for rel, data in files.items():
            target = self.repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        run_git(self.repo, "init", "-q", "-b", "main")
        for key, value in (("core.autocrlf", "false"), ("user.name", "devpipe-test"),
                           ("user.email", "devpipe-test@example.invalid"), ("commit.gpgsign", "false")):
            run_git(self.repo, "config", key, value)
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", "init")
        self.base = run_git(self.repo, "rev-parse", "HEAD")
        self.wt = self.repo / ".claude" / "worktrees" / TASK
        run_git(self.repo, "worktree", "add", "-q", "-b", "worktree-" + TASK, str(self.wt), "HEAD")
        # Claude Code copies this git-ignored file into new worktrees; the copy must not count as a change.
        (self.repo / ".claude" / "settings.local.json").write_bytes(b'{"permissions": {"allow": []}}\n')
        shutil.copy2(self.repo / ".claude" / "settings.local.json", self.wt / ".claude" / "settings.local.json")
        self.run = {
            "id": TASK, "repo": str(self.repo), "base": self.base, "main_branch": "main", "worktree": str(self.wt),
            "branch": "worktree-" + TASK, "prompt_path": devpipe.prompt_rel(TASK), "block": self.block,
            "class_initial": self.block["class"], "include_snapshot": devpipe.include_snapshot(self.repo, self.base),
            "authority_patterns": ["manage-us-stock-strategy/scripts/auth_*.py"], "python": devpipe.python_version(),
            "started_utc": "2026-10-10T00:00:00Z",
        }

    def write(self, rel, data):
        target = self.wt / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def good_change(self):
        self.write("manage-us-stock-strategy/scripts/app.py", b"def f():\r\n    return 2\r\n")

    def make_ready(self, status="READY_TO_MERGE", cls="general", class_ok=True):
        tree = devpipe.inspect_tree(self.run)
        run_dir = self.repo / devpipe.RUNS_REL / TASK
        devpipe.write_json(run_dir / "run.json", self.run)
        envelope = judge_envelope("PASS", class_ok)
        (run_dir / "judge-1.json").write_bytes(envelope)
        result = {"id": TASK, "status": status, "class": cls, "base": self.base, "main_branch": "main",
                  "diff_hash": tree["diff_hash"], "judge_file": "judge-1.json",
                  "judge_file_sha256": hashlib.sha256(envelope).hexdigest(), "class_reasons": [],
                  "started_utc": "2026-10-10T00:00:00Z", "finished_utc": "2026-10-10T00:10:00Z", "retries": 0,
                  "changed_files": tree["changed_paths"], "reasons": [], "next": "x"}
        devpipe.write_json(run_dir / "result.json", result)
        return run_dir


# ------------------------------------------------------------------------------------------------ P5

class DevRunBlockTests(unittest.TestCase):
    def test_valid_block_parses(self):
        self.assertEqual(devpipe.parse_prompt_block(prompt_text(BLOCK), TASK), BLOCK)

    def test_unknown_key_rejected(self):
        block = dict(BLOCK, extra=1)
        with self.assertRaises(devpipe.Stop) as ctx:
            devpipe.parse_prompt_block(prompt_text(block), TASK)
        self.assertIn("unknown_key:extra", ctx.exception.reason)

    def test_missing_key_rejected(self):
        block = dict(BLOCK)
        del block["target_tests"]
        self.assertIn("missing_key:target_tests", devpipe.validate_block(block, TASK))

    def test_allowed_path_overlapping_protected_rejected(self):
        for path in ("tools/dev-run.ps1", "tools/", ".claude/settings.json", "CLAUDE.md", "AGENTS.md",
                     "docs/claude/", "docs/claude/t-demo-builder-prompt.md", "manage-us-stock-strategy/tests/",
                     "manage-us-stock-strategy/tests/test_dev_pipeline.py", "workspace/policies/x.json",
                     "stock-strategy-system/", "docs/claude/_pending/", "docs/", "x/.claude/"):
            with self.subTest(path=path):
                errors = devpipe.validate_block(dict(BLOCK, allowed_paths=[path]), TASK)
                self.assertTrue(any(e.startswith("allowed_path_protected") for e in errors), errors)

    def test_wildcard_dotdot_absolute_backslash_rejected(self):
        for path, code in (("manage-us-stock-strategy/*.py", "wildcard"), ("../x.py", "dotdot"),
                           ("/etc/x", "absolute"), ("C:/x.py", "absolute"), ("a\\b.py", "backslash")):
            with self.subTest(path=path):
                errors = devpipe.validate_block(dict(BLOCK, allowed_paths=[path]), TASK)
                self.assertTrue(any(e.startswith("allowed_path_" + code) for e in errors), errors)

    def test_authority_requires_opus(self):
        errors = devpipe.validate_block(dict(BLOCK, **{"class": "authority", "builder_model": "sonnet"}), TASK)
        self.assertIn("authority_requires_opus", errors)
        self.assertEqual(devpipe.validate_block(dict(BLOCK, **{"class": "authority", "builder_model": "opus"}), TASK), [])

    def test_ranges_and_types(self):
        for key, value in (("max_turns", 0), ("max_turns", 301), ("max_turns", True), ("builder_timeout_min", 121),
                           ("target_tests", []), ("target_tests", ["x.py"]), ("commit_message", "한글"),
                           ("builder_effort", "max"), ("task_id", "other")):
            with self.subTest(key=key, value=value):
                self.assertNotEqual(devpipe.validate_block(dict(BLOCK, **{key: value}), TASK), [])

    def test_block_count_and_ascii(self):
        with self.assertRaises(devpipe.Stop):
            devpipe.parse_prompt_block("no block here", TASK)
        twice = prompt_text(BLOCK) + prompt_text(BLOCK)
        with self.assertRaises(devpipe.Stop):
            devpipe.parse_prompt_block(twice, TASK)
        non_ascii = prompt_text(BLOCK).replace("feat: demo change", "feat: 변경")
        with self.assertRaises(devpipe.Stop) as ctx:
            devpipe.parse_prompt_block(non_ascii, TASK)
        self.assertEqual(ctx.exception.reason, "BLOCK_NOT_ASCII")

    def test_id_format(self):
        for good in ("x-1", "redesign-t3", "a0"):
            self.assertTrue(devpipe.ID_RE.match(good))
        for bad in ("X-1", "-a", "a", "a_b", "a/b", "a" * 49, "a b"):
            self.assertFalse(devpipe.ID_RE.match(bad), bad)


# ----------------------------------------------------------------------------- unittest output / compare

UNITTEST_FAILED = """..F.s.E
======================================================================
FAIL: test_x (pkg.mod.C.test_x) (case='a')
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: 1 != 2

======================================================================
ERROR: setUpClass (pkg.mod.D)
----------------------------------------------------------------------
Traceback (most recent call last):
RuntimeError: boom

----------------------------------------------------------------------
Ran 12 tests in 0.010s

FAILED (failures=1, errors=1, skipped=1)
"""


class UnittestOutputTests(unittest.TestCase):
    def test_ok_with_skipped(self):
        parsed = devpipe.parse_unittest_output("....s\n----------------------------------------------------------------------\n"
                                               "Ran 5 tests in 0.001s\n\nOK (skipped=1)\n")
        self.assertEqual((parsed["ran"], parsed["status"], parsed["skipped"], parsed["failures"]), (5, "OK", 1, []))

    def test_failed_with_subtest_id(self):
        parsed = devpipe.parse_unittest_output(UNITTEST_FAILED.replace("\n", "\r\n"))
        self.assertEqual(parsed["ran"], 12)
        self.assertEqual(parsed["status"], "FAILED")
        self.assertEqual(parsed["skipped"], 1)
        self.assertEqual(parsed["failures"], ["setUpClass (pkg.mod.D)", "test_x (pkg.mod.C.test_x) (case='a')"])

    def test_missing_ran_line(self):
        parsed = devpipe.parse_unittest_output("Traceback (most recent call last):\nImportError: x\n")
        self.assertIsNone(parsed["ran"])
        stop, _, _ = devpipe.evaluate_tests(self._baseline(), [], dict(parsed, timed_out=False), {"result": "PASS"}, [])
        self.assertEqual(stop[0], "STOP_TESTS_DID_NOT_RUN")

    def _baseline(self, failures=("old (m.C.old)",), ran=10, skipped=1, schema="PASS"):
        return {"ran": ran, "skipped": skipped, "failures": list(failures), "schema": schema, "counts": {}}

    def _full(self, ran=10, skipped=1, failures=("old (m.C.old)",), status="FAILED"):
        return {"ran": ran, "skipped": skipped, "failures": list(failures), "status": status, "counts": {},
                "timed_out": False, "pattern": "test_*.py"}

    def test_compare_same_failures_is_clean(self):
        stop, reasons, new = devpipe.evaluate_tests(self._baseline(), [], self._full(), {"result": "PASS"}, [])
        self.assertEqual((stop, reasons, new), (None, [], []))

    def test_compare_new_failure(self):
        full = self._full(failures=("old (m.C.old)", "new (m.C.new)"))
        _, reasons, new = devpipe.evaluate_tests(self._baseline(), [], full, {"result": "PASS"}, [])
        self.assertEqual(new, ["new (m.C.new)"])
        self.assertIn("NEW_FAILURE:new (m.C.new)", reasons)

    def test_compare_ran_decrease_skipped_increase_schema(self):
        _, reasons, _ = devpipe.evaluate_tests(self._baseline(), [], self._full(ran=9, skipped=2), {"result": "FAIL"}, [])
        self.assertIn("RAN_DECREASED:9<10", reasons)
        self.assertIn("SKIPPED_INCREASED:2>1", reasons)
        self.assertIn("SCHEMA_FAIL", reasons)

    def test_compare_target_failure_and_no_tests(self):
        target = dict(self._full(failures=("t (m.T.t)",)), pattern="test_app*.py")
        empty = dict(self._full(ran=0, failures=(), status="NO TESTS RAN"), pattern="test_none*.py")
        _, reasons, new = devpipe.evaluate_tests(self._baseline(), [target, empty], self._full(), {"result": "PASS"}, [])
        self.assertEqual(new, ["t (m.T.t)"])
        self.assertIn("TARGET_NO_TESTS:test_none*.py", reasons)

    def test_compare_test_def_reasons_pass_through(self):
        defs = ["TEST_DEFS_DECREASED:a/test_x.py:1<2", "TEST_FILE_DELETED:a/test_y.py"]
        _, reasons, _ = devpipe.evaluate_tests(self._baseline(), [], self._full(), {"result": "PASS"}, defs)
        for item in defs:
            self.assertIn(item, reasons)

    def test_compare_expected_failures_increase(self):
        parsed = devpipe.parse_unittest_output("..x.\n------\nRan 10 tests in 0.100s\n\nOK (skipped=1, expected failures=2)\n")
        self.assertEqual(parsed["counts"].get("expected failures"), 2)
        full = dict(self._full(failures=(), status="OK"), counts=parsed["counts"])
        baseline = dict(self._baseline(failures=()), counts={"expected failures": 1})
        _, reasons, _ = devpipe.evaluate_tests(baseline, [], full, {"result": "PASS"}, [])
        self.assertIn("EXPECTED_FAILURES_INCREASED:2>1", reasons)
        baseline["counts"] = {"expected failures": 2}
        _, reasons, _ = devpipe.evaluate_tests(baseline, [], full, {"result": "PASS"}, [])
        self.assertEqual(reasons, [])


# ------------------------------------------------------------------------------------------- check-tree

class CheckTreeTests(unittest.TestCase):
    def setUp(self):
        self.fx = RepoFixture(self)

    def assert_stop(self, status, contains=None):
        with self.assertRaises(devpipe.Stop) as ctx:
            devpipe.inspect_tree(self.fx.run)
        self.assertEqual(ctx.exception.status, status, ctx.exception.reason)
        if contains:
            self.assertIn(contains, ctx.exception.reason + " " + " ".join(ctx.exception.details))
        return ctx.exception

    def test_allowed_change_is_clean(self):
        self.fx.good_change()
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertEqual(tree["changed_paths"], ["manage-us-stock-strategy/scripts/app.py"])
        self.assertEqual((tree["class"], tree["retryable"], tree["class_reasons"]), ("general", [], []))

    def test_new_file_in_allowed_dir_is_in_patch(self):
        self.fx.write("manage-us-stock-strategy/scripts/newmod/x.py", b"Y = 1\r\n")
        out = Path(self.fx.tmp) / "out"
        tree = devpipe.inspect_tree(self.fx.run, out)
        self.assertEqual(tree["changed_paths"], ["manage-us-stock-strategy/scripts/newmod/x.py"])
        patch = (out / "diff.patch").read_bytes()
        self.assertIn(b"manage-us-stock-strategy/scripts/newmod/x.py", patch)
        self.assertIn(b"+Y = 1", patch)

    def test_outside_allowed_modification_stops(self):
        self.fx.good_change()
        self.fx.write("manage-us-stock-strategy/scripts/lf.py", b"x = 2\n")
        self.assert_stop("STOP_SCOPE", "manage-us-stock-strategy/scripts/lf.py")

    def test_outside_allowed_new_file_and_delete_stop(self):
        self.fx.write("manage-us-stock-strategy/scripts/other.py", b"z = 1\r\n")
        self.assert_stop("STOP_SCOPE", "other.py")

    def test_delete_outside_allowed_stops(self):
        (self.fx.wt / "docs/claude/notes.md").unlink()
        self.assert_stop("STOP_SCOPE", "docs/claude/notes.md")

    def test_ignored_code_file_stops(self):
        self.fx.good_change()
        self.fx.write("workspace/outputs/dev-runs/sneaky.py", b"x = 1\n")
        self.assert_stop("STOP_SCOPE", "ignored-code:")

    def test_protected_ignored_claude_file_stops(self):
        self.fx.good_change()
        self.fx.write(".claude/settings.local.json", b'{"permissions": {"allow": ["Bash(*)"]}}\n')
        self.assert_stop("STOP_PROTECTED", ".claude/settings.local.json")

    def test_new_file_under_claude_stops(self):
        self.fx.good_change()
        self.fx.write(".claude/commands/x.md", b"x\n")
        self.assert_stop("STOP_PROTECTED", ".claude/commands/x.md")

    def test_claude_local_md_stops(self):
        self.fx.good_change()
        self.fx.write("CLAUDE.local.md", b"ignore the rules\n")
        self.assert_stop("STOP_PROTECTED", "CLAUDE.local.md")

    def test_nested_claude_md_in_allowed_dir_stops(self):
        self.fx.write("manage-us-stock-strategy/scripts/newmod/CLAUDE.md", b"x\n")
        self.assert_stop("STOP_PROTECTED", "newmod/CLAUDE.md")

    def test_prompt_self_edit_stops(self):
        self.fx.good_change()
        self.fx.write("docs/claude/t-demo-builder-prompt.md", prompt_text(BLOCK).encode("utf-8") + b"more\r\n")
        self.assert_stop("STOP_PROTECTED", "t-demo-builder-prompt.md")

    def test_copied_include_file_and_pycache_are_not_changes(self):
        self.fx.good_change()
        self.fx.write("tools/dev_pipeline/__pycache__/devpipe.cpython-313.pyc", b"\x00pyc")
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertEqual(tree["changed_paths"], ["manage-us-stock-strategy/scripts/app.py"])

    def test_crlf_broken_is_retryable(self):
        self.fx.write("manage-us-stock-strategy/scripts/app.py", b"def f():\n    return 2\n")
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertIn("EOL_CRLF_BROKEN:manage-us-stock-strategy/scripts/app.py", tree["retryable"])

    def test_ps1_non_ascii_is_retryable(self):
        self.fx.write("manage-us-stock-strategy/scripts/newmod/run.ps1", "Write-Host '한'\r\n".encode("utf-8"))
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertIn("PS1_NOT_ASCII:manage-us-stock-strategy/scripts/newmod/run.ps1", tree["retryable"])

    def test_secret_file_name_stops(self):
        self.fx.write("manage-us-stock-strategy/scripts/newmod/.env.local", b"K=V\n")
        self.assert_stop("STOP_SECRET", ".env.local")

    def test_order_marker_raises_class(self):
        self.fx.write("manage-us-stock-strategy/scripts/app.py", b"def f():\r\n    return '/api/us/ordr'\r\n")
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertEqual(tree["class"], "authority")
        self.assertIn("ORDER_MARKER:/api/us/ordr", tree["class_reasons"])

    def test_authority_path_raises_class(self):
        self.fx.write("manage-us-stock-strategy/scripts/auth_gate.py", b"LIMIT = 2\r\n")
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertEqual(tree["class"], "authority")
        self.assertIn("AUTHORITY_PATH:manage-us-stock-strategy/scripts/auth_gate.py", tree["class_reasons"])

    def test_order_authority_true_raises_class(self):
        self.fx.write("manage-us-stock-strategy/scripts/app.py", b"def f():\r\n    return {'order_authority': True}\r\n")
        self.assertEqual(devpipe.inspect_tree(self.fx.run)["class"], "authority")

    def test_schema_approval_const_change_raises_class(self):
        markers = ("quantity_authority", "execution_quantity", "watchlist_approved", "active_universe_approved",
                   "new_buy_instrument_approved")
        rel = "manage-us-stock-strategy/scripts/newmod/demo.schema.json"

        def schema(changed=None):
            rows = ['    "%s": {"const": %s}' % (m, "true" if m == changed else "false") for m in markers]
            return ('{\r\n  "properties": {\r\n' + ",\r\n".join(rows) + '\r\n  }\r\n}\r\n').encode("ascii")

        fx = RepoFixture(self, extra_files={rel: schema()})
        for marker in markers:
            with self.subTest(marker=marker):
                fx.write(rel, schema(marker))
                tree = devpipe.inspect_tree(fx.run)
                self.assertEqual(tree["class"], "authority")
                self.assertIn("REMOVED_LINE:%s" % marker, tree["class_reasons"])

    def test_include_snapshot_remeasured_before_builder(self):
        run_dir = self.fx.repo / devpipe.RUNS_REL / TASK
        devpipe.write_json(run_dir / "run.json", self.fx.run)
        # The main copy changes after init-run (e.g. during the baseline); Claude Code copies the new one
        # when attempt 1 creates the worktree.
        main_copy = self.fx.repo / ".claude" / "settings.local.json"
        main_copy.write_bytes(b'{"permissions": {"allow": ["Bash(ls *)"]}}\n')
        shutil.copy2(main_copy, self.fx.wt / ".claude" / "settings.local.json")
        self.fx.good_change()
        with self.assertRaises(devpipe.Stop):
            devpipe.inspect_tree(self.fx.run)  # init-run snapshot no longer matches
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(devpipe.cmd_snapshot_includes(type("A", (), {"run_dir": str(run_dir)})()), 0)
        self.assertEqual(out.getvalue().strip(), "SNAPSHOT OK files=1")
        run = devpipe.read_json(run_dir / "run.json")
        self.assertEqual(set(run["include_snapshot"]), set(run["include_snapshot_init"]))
        self.assertNotEqual(run["include_snapshot"], run["include_snapshot_init"])
        self.assertEqual(devpipe.inspect_tree(run)["changed_paths"], ["manage-us-stock-strategy/scripts/app.py"])
        # Only the worktree copy changes: still a protected change.
        self.fx.write(".claude/settings.local.json", b'{"permissions": {"allow": ["Bash(*)"]}}\n')
        with self.assertRaises(devpipe.Stop) as ctx:
            devpipe.inspect_tree(run)
        self.assertEqual(ctx.exception.status, "STOP_PROTECTED")

    def test_authority_is_never_lowered(self):
        self.fx.run["class_initial"] = "authority"
        self.fx.good_change()
        tree = devpipe.inspect_tree(self.fx.run)
        self.assertEqual(tree["class"], "authority")
        self.assertEqual(devpipe.escalate("authority", []), "authority")
        self.assertEqual(devpipe.escalate("general", ["X"]), "authority")

    def test_blocked_stops_with_first_line(self):
        self.fx.good_change()
        self.fx.write("BLOCKED.md", "정책 판단 필요\r\n둘째 줄\r\n".encode("utf-8"))
        error = self.assert_stop("BLOCKED")
        self.assertEqual(error.reason, "정책 판단 필요")

    def test_builder_commit_stops(self):
        self.fx.good_change()
        run_git(self.fx.wt, "commit", "-q", "-am", "builder committed")
        self.assert_stop("STOP_WORKTREE", "head_moved")

    def test_missing_worktree_stops(self):
        self.fx.run["worktree"] = str(self.fx.repo / ".claude" / "worktrees" / "absent")
        self.assert_stop("STOP_WORKTREE", "missing")

    def test_no_changes_stops(self):
        self.assert_stop("STOP_NO_CHANGES")

    def test_test_def_decrease_and_delete(self):
        self.fx.write("manage-us-stock-strategy/tests/test_app.py", TEST_APP.replace(b"def test_b", b"def helper_b"))
        changes = devpipe.collect_changes(self.fx.wt, self.fx.base)
        self.assertEqual(devpipe.test_def_changes(self.fx.wt, self.fx.base, changes),
                         ["TEST_DEFS_DECREASED:manage-us-stock-strategy/tests/test_app.py:1<2"])
        (self.fx.wt / "manage-us-stock-strategy/tests/test_app.py").unlink()
        changes = devpipe.collect_changes(self.fx.wt, self.fx.base)
        self.assertEqual(devpipe.test_def_changes(self.fx.wt, self.fx.base, changes),
                         ["TEST_FILE_DELETED:manage-us-stock-strategy/tests/test_app.py"])


class DiffHashTests(unittest.TestCase):
    def setUp(self):
        self.fx = RepoFixture(self)
        self.fx.good_change()

    def _hash(self):
        return devpipe.diff_hash(self.fx.wt, devpipe.collect_changes(self.fx.wt, self.fx.base))

    def test_same_content_same_hash(self):
        first = self._hash()
        self.fx.good_change()
        self.assertEqual(first, self._hash())

    def test_one_byte_changes_hash(self):
        first = self._hash()
        self.fx.write("manage-us-stock-strategy/scripts/app.py", b"def f():\r\n    return 3\r\n")
        self.assertNotEqual(first, self._hash())

    def test_ignored_files_excluded(self):
        first = self._hash()
        self.fx.write("debug.log", b"noise\n")
        self.fx.write("workspace/outputs/dev-runs/t-demo/checks.json", b"{}\n")
        self.assertEqual(first, self._hash())


# ------------------------------------------------------------------------------------------- judge

class ParseJudgeTests(unittest.TestCase):
    def test_pass(self):
        parsed = devpipe.parse_judge_envelope(judge_envelope("PASS"))
        self.assertTrue(parsed["ok"])
        self.assertEqual((parsed["verdict"], parsed["class_ok"]), ("PASS", True))

    def test_fail_keeps_min_fixes(self):
        parsed = devpipe.parse_judge_envelope(judge_envelope("FAIL", min_fixes=["add test for y"]))
        self.assertEqual((parsed["verdict"], parsed["min_fixes"]), ("FAIL", ["add test for y"]))

    def test_missing_last_line(self):
        for last in ("", "**VERDICT: PASS**", "VERDICT: PASS, with notes"):
            with self.subTest(last=last):
                parsed = devpipe.parse_judge_envelope(judge_envelope("PASS", last_line=last))
                self.assertFalse(parsed["ok"])
                self.assertEqual(parsed["error"], "NO_VERDICT_LINE")

    def test_is_error_envelope(self):
        parsed = devpipe.parse_judge_envelope(judge_envelope("PASS", is_error=True))
        self.assertEqual(parsed["error"], "ENVELOPE_IS_ERROR")
        self.assertEqual(devpipe.parse_judge_envelope(b"not json")["error"], "ENVELOPE_NOT_JSON")

    def test_no_json_block(self):
        self.assertEqual(devpipe.parse_judge_envelope(judge_envelope("PASS", with_json=False))["error"], "NO_JSON_BLOCK")

    def test_verdict_mismatch_and_pass_with_fixes(self):
        self.assertEqual(devpipe.parse_judge_envelope(judge_envelope("PASS", last_line="VERDICT: FAIL"))["error"],
                         "VERDICT_MISMATCH")
        self.assertEqual(devpipe.parse_judge_envelope(judge_envelope("PASS", min_fixes=["x"]))["error"],
                         "PASS_WITH_MIN_FIXES")

    def test_class_ok_false_makes_authority(self):
        fx = RepoFixture(self)
        fx.good_change()
        run_dir = fx.repo / devpipe.RUNS_REL / TASK
        devpipe.write_json(run_dir / "run.json", fx.run)
        devpipe.write_json(run_dir / "baseline.json", {"ran": 2, "skipped": 0, "failures": [], "schema": "MISSING"})
        checks = devpipe.run_checks(fx.run, run_dir, 1, None, with_tests=False)
        self.assertEqual(checks["status"], "OK")
        (run_dir / "judge-1.json").write_bytes(judge_envelope("PASS", class_ok=False))
        args = type("A", (), {"run_dir": str(run_dir), "attempt": 1})()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(devpipe.cmd_parse_judge(args), 0)
        self.assertEqual(out.getvalue().strip(), "JUDGE PASS attempt=1 class_ok=false")
        args = type("A", (), {"run_dir": str(run_dir), "status": "PASS", "retries": 0, "reason": None})()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(devpipe.cmd_write_result(args), 0)
        self.assertTrue(out.getvalue().startswith("DEV-RUN t-demo NEEDS_APPROVAL judge=PASS"))
        result = devpipe.read_json(run_dir / "result.json")
        self.assertEqual((result["status"], result["class"]), ("NEEDS_APPROVAL", "authority"))
        self.assertIn("JUDGE_CLASS_OK_FALSE", result["class_reasons"])
        self.assertTrue((fx.repo / "docs/claude/dev-runs/t-demo.md").is_file())
        pending = (fx.repo / "docs/claude/_pending/dev-run-t-demo.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(pending[1], "docs/claude/dev-runs/t-demo.md")


# ------------------------------------------------------------------------------------------- merge

class MergeTests(unittest.TestCase):
    def setUp(self):
        self.fx = RepoFixture(self)
        self.fx.good_change()

    def merge(self, approve=False):
        try:
            return devpipe.do_merge(self.fx.repo, TASK, approve)
        except devpipe.Stop as exc:
            return 2, exc.status + " " + exc.reason

    def test_normal_merge_fast_forwards(self):
        self.fx.make_ready()
        code, line = self.merge()
        self.assertEqual(code, 0, line)
        head = run_git(self.fx.repo, "rev-parse", "HEAD")
        self.assertEqual(run_git(self.fx.repo, "rev-parse", "HEAD^"), self.fx.base)
        self.assertEqual((self.fx.repo / "manage-us-stock-strategy/scripts/app.py").read_bytes(), b"def f():\r\n    return 2\r\n")
        message = run_git(self.fx.repo, "log", "-1", "--format=%B")
        self.assertTrue(message.startswith("feat: demo change"))
        self.assertIn("Dev-Run: t-demo base=%s" % self.fx.base[:8], message)
        result = devpipe.read_json(self.fx.repo / devpipe.RUNS_REL / TASK / "result.json")
        self.assertEqual(result["merge_sha"], head)
        self.assertEqual(self.merge()[1].split()[0], "STOP_ALREADY_MERGED")

    def test_judge_file_changed_refused(self):
        run_dir = self.fx.make_ready()
        (run_dir / "judge-1.json").write_bytes(judge_envelope("PASS") + b" ")
        code, line = self.merge()
        self.assertEqual((code, line.split()[0]), (2, "STOP_JUDGE_FILE"))
        self.assertEqual(run_git(self.fx.repo, "rev-parse", "HEAD"), self.fx.base)

    def test_diff_changed_refused(self):
        self.fx.make_ready()
        self.fx.write("manage-us-stock-strategy/scripts/app.py", b"def f():\r\n    return 9\r\n")
        self.assertEqual(self.merge()[1].split()[0], "STOP_DIFF_CHANGED")

    def test_status_fail_refused(self):
        self.fx.make_ready(status="FAIL")
        self.assertEqual(self.merge()[1].split()[0], "STOP_STATUS")

    def test_authority_needs_approval(self):
        self.fx.make_ready(status="NEEDS_APPROVAL", cls="authority")
        code, line = self.merge()
        self.assertEqual(code, 3)
        self.assertIn("NEEDS_APPROVAL: user approval needed", line)
        self.assertEqual(run_git(self.fx.repo, "rev-parse", "HEAD"), self.fx.base)
        code, line = self.merge(approve=True)
        self.assertEqual(code, 0, line)
        result = devpipe.read_json(self.fx.repo / devpipe.RUNS_REL / TASK / "result.json")
        self.assertTrue(result["approved_at"])

    def test_authority_detected_at_merge_without_record(self):
        self.fx.write("manage-us-stock-strategy/scripts/auth_gate.py", b"LIMIT = 5\r\n")
        self.fx.make_ready(status="READY_TO_MERGE", cls="general")
        code, line = self.merge()
        self.assertEqual(code, 3, line)
        self.assertEqual(run_git(self.fx.repo, "rev-parse", "HEAD"), self.fx.base)

    def test_approve_switch_only_for_needs_approval(self):
        self.fx.make_ready()
        self.assertEqual(self.merge(approve=True)[1].split()[0], "STOP_APPROVAL_NOT_APPLICABLE")

    def test_protected_change_refused(self):
        self.fx.make_ready()
        self.fx.write("CLAUDE.local.md", b"x\n")
        self.assertEqual(self.merge()[1].split()[0], "STOP_PROTECTED")

    def test_blocked_refused(self):
        self.fx.make_ready()
        self.fx.write("BLOCKED.md", b"why\n")
        self.assertEqual(self.merge()[1].split()[0], "BLOCKED")

    def test_staged_in_main_refused(self):
        self.fx.make_ready()
        (self.fx.repo / "docs/claude/notes.md").write_bytes(b"edited\n")
        run_git(self.fx.repo, "add", "docs/claude/notes.md")
        self.assertEqual(self.merge()[1].split()[0], "STOP_MAIN_STAGED")

    def test_base_moved_with_code_commit_refused(self):
        self.fx.make_ready()
        (self.fx.repo / "manage-us-stock-strategy/scripts/lf.py").write_bytes(b"x = 3\n")
        run_git(self.fx.repo, "commit", "-q", "-am", "code moved on")
        code, line = self.merge()
        self.assertEqual(line.split()[:2], ["STOP_BASE_MOVED", "non_docs_commits"])
        self.assertEqual(run_git(self.fx.wt, "rev-parse", "HEAD"), self.fx.base)
        self.assertEqual(run_git(self.fx.wt, "status", "--porcelain"), "M manage-us-stock-strategy/scripts/app.py")

    def test_base_moved_with_docs_commit_rebases_and_retests(self):
        self.fx.make_ready()
        (self.fx.repo / "docs/claude/notes.md").write_bytes(b"newer notes\n")
        run_git(self.fx.repo, "commit", "-q", "-am", "docs moved on")
        docs_head = run_git(self.fx.repo, "rev-parse", "HEAD")
        code, line = self.merge()
        self.assertEqual(code, 0, line)
        self.assertIn("mode=rebase", line)
        self.assertEqual(run_git(self.fx.repo, "rev-parse", "HEAD^"), docs_head)
        run_dir = self.fx.repo / devpipe.RUNS_REL / TASK
        self.assertEqual(devpipe.read_json(run_dir / "merge-tests.json")["new_failures"], [])


# ------------------------------------------------------------------------------------------- queue

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="devpipe-queue-"))
        self.addCleanup(remove_tree, self.tmp)
        (self.tmp / devpipe.QUEUE_REL).mkdir(parents=True)

    def _queue(self, name, first_line, mtime):
        path = self.tmp / devpipe.QUEUE_REL / name
        path.write_bytes((first_line + "\r\nnote\r\n").encode("utf-8"))
        os.utime(path, (mtime, mtime))

    def test_empty(self):
        self.assertEqual(devpipe.queue_take(self.tmp)[:2], (1, "QUEUE EMPTY"))

    def test_oldest_taken_and_moved(self):
        self._queue("b-task.txt", "b-task", 2000)
        self._queue("a-task.txt", "a-task", 3000)
        code, line, task_id = devpipe.queue_take(self.tmp)
        self.assertEqual((code, task_id), (0, "b-task"))
        self.assertFalse((self.tmp / devpipe.QUEUE_REL / "b-task.txt").exists())
        self.assertEqual(len(list((self.tmp / devpipe.RUNS_REL / "_taken").glob("*-b-task.txt"))), 1)
        self.assertEqual(devpipe.queue_take(self.tmp)[2], "a-task")
        self.assertEqual(devpipe.queue_take(self.tmp)[0], 1)

    def test_invalid_queue_file(self):
        self._queue("Bad_Name.txt", "Bad_Name", 1000)
        code, line, task_id = devpipe.queue_take(self.tmp)
        self.assertEqual((code, task_id), (2, None))
        self.assertIn("STOP_QUEUE_INVALID", line)
        latest = devpipe.read_json(self.tmp / devpipe.RUNS_REL / "LATEST.json")
        self.assertEqual(latest["status"], "STOP_QUEUE_INVALID")
        self._queue("x-1.txt", "x-2", 1000)
        self.assertEqual(devpipe.queue_take(self.tmp)[0], 2)


# ------------------------------------------------------------------------------------------- CLI flags

HELP_SAMPLE = """Usage: claude [options] [command] [prompt]

Options:
  --allowedTools, --allowed-tools <tools...>
      Comma or space-separated list of tool names to allow
  --disallowedTools, --disallowed-tools <tools...>
      Comma or space-separated list of tool names to deny
  --effort <level>                      Effort level for the current session
                                        (low, medium, high, xhigh, max)
  --model <model>                       Model for the current session.
  --output-format <format>              Output format (only works with --print):
                                        "text" (default), "json" (single
                                        result), or "stream-json"
  --permission-mode <mode>              Permission mode to use for the session
                                        (choices: "acceptEdits", "auto",
                                        "bypassPermissions", "manual")
  --permission-prompts <target>         Who answers permission prompts
                                        (choices: "host", "none", default:
                                        "host")
  -p, --print                           Print response and exit
  --setting-sources <sources>           Comma-separated list of setting sources
                                        to load (user, project, local).
  --strict-mcp-config                   Only use MCP servers from --mcp-config
  --tools <tools...>                    Specify the list of available tools
  -w, --worktree [name]                 Create a new git worktree

Commands:
  agents [options]                      Manage background agents
"""


class CliFlagTests(unittest.TestCase):
    def test_all_flags_found_hidden_one_by_probe(self):
        results = devpipe.check_cli_flags(HELP_SAMPLE, "claude.exe", prober=lambda exe, flag: flag == "--max-turns")
        by_flag = {r["flag"]: r for r in results}
        self.assertTrue(all(r["ok"] for r in results), results)
        self.assertEqual(by_flag["--max-turns"]["how"], "probe")
        self.assertEqual(by_flag["-p"]["how"], "help")

    def test_hidden_flag_missing_when_probe_fails(self):
        results = devpipe.check_cli_flags(HELP_SAMPLE, "claude.exe", prober=lambda exe, flag: False)
        missing = [r["flag"] for r in results if not r["ok"]]
        self.assertEqual(missing, ["--max-turns"])

    def test_missing_value_and_flag(self):
        help_text = HELP_SAMPLE.replace("xhigh, ", "").replace("  --strict-mcp-config", "  --strict-mcp-other")
        results = {r["flag"]: r for r in devpipe.check_cli_flags(help_text, "claude.exe", prober=lambda e, f: True)}
        self.assertEqual(results["--effort"]["how"], "value_missing")
        self.assertFalse(results["--strict-mcp-config"]["ok"])
        self.assertEqual(devpipe.parse_claude_version("2.1.296 (Claude Code)"), (2, 1, 296))
        self.assertGreaterEqual(devpipe.parse_claude_version("2.1.296"), devpipe.MIN_CLAUDE_VERSION)


# ---------------------------------------------------------------------------------------- static checks

PS1_NAMES = ("dev-run.ps1", "dev-merge.ps1", "dev-queue.ps1", "run-docs-commit.ps1", "register-dev-tasks.ps1",
             "commit-docs.ps1")
FORBIDDEN = ("bypassPermissions", "dangerously-skip-permissions", "git push", "--force", "| claude", "Invoke-Expression")
OLD_DENY = {
    "Read(./.env)", "Read(./.env.*)", "mcp__*__kiwoom_order_submit",
    "Bash(*reconcile_broker_state.py apply*)", "PowerShell(*reconcile_broker_state.py apply*)",
    "Bash(*auto_core" + ".py*)", "PowerShell(*auto_core" + ".py*)",
    "Bash(*reconcile_broker_state.py auto*)", "PowerShell(*reconcile_broker_state.py auto*)",
    "Edit(/stock-strategy-system/portfolio_state.json)", "Edit(/stock-strategy-system/reconciliation_ledger.jsonl)",
    "Edit(/stock-strategy-system/backups/**)", "Bash(*portfolio_review_journal.py apply*)",
    "PowerShell(*portfolio_review_journal.py apply*)", "Edit(/stock-strategy-system/decision_journal.json)",
}
P9_DENY = {
    "Bash(*dev-run.ps1*)", "PowerShell(*dev-run.ps1*)", "Bash(*dev-merge.ps1*)", "PowerShell(*dev-merge.ps1*)",
    "Bash(*dev-queue.ps1*)", "PowerShell(*dev-queue.ps1*)", "Edit(/.claude/settings.json)",
    "Edit(/.claude/settings.local.json)",
}
OLD_ASK = {"Edit(stock-strategy-system/**)", "Edit(workspace/policies/**)", "Bash(git commit:*)", "Bash(git push:*)"}
P9_ASK = {"Edit(/tools/**)", "Edit(/CLAUDE.md)", "Edit(/AGENTS.md)", "Edit(/.gitignore)"}


class StaticScriptTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / "tools" / name).read_bytes()

    def test_ps1_ascii_and_crlf(self):
        for name in PS1_NAMES:
            with self.subTest(name=name):
                data = self.read(name)
                self.assertTrue(all(b < 128 for b in data), name)
                self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), name)

    def test_forbidden_strings_absent(self):
        texts = {name: self.read(name).decode("ascii").lower() for name in PS1_NAMES}
        texts["devpipe.py"] = (PIPELINE / "devpipe.py").read_text(encoding="utf-8").lower()
        for name, text in texts.items():
            for word in FORBIDDEN:
                with self.subTest(name=name, word=word):
                    self.assertNotIn(word.lower(), text)

    def test_judge_command_constants(self):
        text = self.read("dev-run.ps1").decode("ascii")
        self.assertIn('--model opus --effort xhigh --tools "Read,Grep,Glob"', text)
        self.assertIn("--permission-prompts none --output-format json --strict-mcp-config", text)
        self.assertIn('--disallowedTools "mcp__*" --max-turns', text)

    def test_builder_command_constants(self):
        text = self.read("dev-run.ps1").decode("ascii")
        self.assertIn("--permission-mode acceptEdits --permission-prompts none --max-turns", text)
        self.assertIn("--output-format json --strict-mcp-config --setting-sources project", text)
        self.assertIn("$BuilderToolSet = 'Read,Edit,Write,Grep,Glob,Bash,PowerShell'", text)
        allowed = re.search(r"\$BuilderAllowedTools = @\((.*?)\n\)", text, re.S).group(1)
        rules = re.findall(r"'([^']+)'", allowed)
        self.assertIn("Bash(python -m unittest *)", rules)
        for rule in rules:
            with self.subTest(rule=rule):
                low = rule.lower()
                for word in ("commit", "push", "auto_core", "apply", "policies", "stock-strategy-system", "add",
                             "reset", "checkout", "kiwoom"):
                    self.assertNotIn(word, low)
                # Only command rules: no bare Read|Edit|Write|Grep|Glob (they would approve paths outside the
                # worktree) and no path-bound file-tool rules such as Read(/**).
                self.assertTrue(re.match(r"^(Bash|PowerShell)\(.+\)$", rule), rule)
                self.assertNotRegex(rule, r"^(Read|Edit|Write|Grep|Glob|MultiEdit|NotebookEdit)\b")
        self.assertEqual(text.count("' --worktree ' + $Id"), 1)
        self.assertIn("Read tools/dev_pipeline/builder-rules.md and docs/claude/' + $Id + '-builder-prompt.md", text)

    def test_builder_denies_git_output_and_no_index(self):
        text = self.read("dev-run.ps1").decode("ascii")
        denied = re.findall(r"'([^']+)'", re.search(r"\$BuilderDisallowedTools = @\((.*?)\n\)", text, re.S).group(1))
        self.assertEqual(set(denied), {"mcp__*", "Bash(git *--output*)", "PowerShell(git *--output*)",
                                       "Bash(git *--no-index*)", "PowerShell(git *--no-index*)"})
        self.assertIn("--disallowedTools ' + (Get-QuotedList $BuilderDisallowedTools) +", text)
        self.assertEqual(text.count("--disallowedTools"), 2)  # Builder list + Judge "mcp__*" (Judge has no Bash)
        allowed = re.search(r"\$BuilderAllowedTools = @\((.*?)\n\)", text, re.S).group(1)
        self.assertIn("git diff *", allowed)  # the deny rules above are what keep these from writing/reading files

    def test_queue_limits_fit_task_limit(self):
        queue = self.read("dev-queue.ps1").decode("ascii")
        register = self.read("register-dev-tasks.ps1").decode("ascii")
        commit_docs_seconds = int(re.search(r"^\$CommitDocsLimitSeconds = (\d+)\r?$", queue, re.M).group(1))
        dev_run_minutes = int(re.search(r"^\$DevRunLimitMinutes = (\d+)\r?$", queue, re.M).group(1))
        task_hours = int(re.search(r"^\$queueLimitHours = (\d+)\r?$", register, re.M).group(1))
        self.assertLessEqual(commit_docs_seconds / 60 + dev_run_minutes + 5, task_hours * 60)
        self.assertIn("2>&1') $CommitDocsLimitSeconds", queue)
        self.assertIn("($DevRunLimitMinutes * 60)", queue)
        self.assertNotRegex(queue, r"2>&1'\) \d+")

    def test_merge_is_fast_forward_only(self):
        source = (PIPELINE / "devpipe.py").read_text(encoding="utf-8")
        self.assertIn('git(repo, "merge", "--ff-only"', source)
        self.assertEqual(source.count('"merge", '), 1)
        self.assertNotIn('"branch", "-d', source)
        self.assertNotIn('"worktree", "remove", run', source)

    def test_register_script_names_only_two_tasks(self):
        text = self.read("register-dev-tasks.ps1").decode("ascii")
        self.assertEqual(set(re.findall(r"InvestmentV2-[A-Za-z]+", text)),
                         {"InvestmentV2-DocsCommit", "InvestmentV2-DevQueue"})
        for word in ("Unregister-ScheduledTask", "Start-ScheduledTask", "Set-ScheduledTask", "Disable-ScheduledTask"):
            self.assertNotIn(word, text)
        for word in ("-LogonType Interactive -RunLevel Limited", "-StartWhenAvailable", "-WakeToRun:$false",
                     "-MultipleInstances IgnoreNew", '"Korea Standard Time"', "APPLY_BLOCKED_TIMEZONE",
                     '$docsTime = "23:30"', "$queueIntervalMinutes = 15", "$queueLimitHours = 6", "$docsLimitMinutes = 15"):
            self.assertIn(word, text)

    def test_docs_commit_runner_keeps_commit_docs_safety(self):
        runner = self.read("run-docs-commit.ps1").decode("ascii")
        self.assertIn("commit-docs.ps1", runner)
        self.assertIn("-DryRun", runner)
        commit_docs = self.read("commit-docs.ps1").decode("ascii")
        for word in ("'^docs/claude/[^/]'", "git diff --cached --quiet", "STOP: other changes are already staged",
                     "Nothing was pushed."):
            self.assertIn(word, commit_docs)

    def test_queue_and_lock_wiring(self):
        queue = self.read("dev-queue.ps1").decode("ascii")
        for word in ("Test-LockAlive", "'queue-take'", "'prompt-committed'", "commit-docs.ps1", "dev-run.ps1",
                     "STOP_PROMPT_NOT_COMMITTED"):
            self.assertIn(word, queue)
        run = self.read("dev-run.ps1").decode("ascii")
        for word in ("[System.IO.FileMode]::CreateNew", "Exit-Lock", "finally"):
            self.assertIn(word, run)

    def test_protected_constants_cover_p6(self):
        for path in ("tools/x.ps1", ".claude/settings.json", ".claude/new.json", "CLAUDE.md", "CLAUDE.local.md",
                     "AGENTS.md", ".mcp.json", ".gitignore", ".gitattributes", ".worktreeinclude",
                     "manage-us-stock-strategy/tests/test_dev_pipeline.py", "docs/claude/dev-runs/x.md",
                     "docs/claude/_pending/x.txt", "docs/claude/_dev-queue/x.txt", "workspace/policies/a.json",
                     "stock-strategy-system/alert_policy.json", "docs/claude/t-demo-builder-prompt.md",
                     "a/b/CLAUDE.md", "a/.claude/x", "Tools/X.ps1"):
            with self.subTest(path=path):
                self.assertTrue(devpipe.is_protected(path, TASK))
        for path in ("manage-us-stock-strategy/scripts/app.py", "docs/claude/other.md",
                     "manage-us-stock-strategy/tests/test_app.py"):
            self.assertFalse(devpipe.is_protected(path, TASK), path)

    def test_authority_paths_file(self):
        patterns = devpipe.parse_authority_patterns((PIPELINE / "authority-paths.txt").read_text(encoding="utf-8"))
        regexes = [devpipe.glob_to_regex(p) for p in patterns]
        for path in ("manage-us-stock-strategy/scripts/auto_core" + ".py",
                     "manage-us-stock-strategy/scripts/auto_core_reconcile.py",
                     "manage-us-stock-strategy/scripts/apply_user_confirmed_broker_snapshot.py",
                     "manage-us-stock-strategy/scripts/reconcile_broker_state.py",
                     "manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py",
                     "manage-us-stock-strategy/scripts/portfolio_policy_gates.py",
                     "manage-us-stock-strategy/scripts/portfolio_exposure.py",
                     "manage-us-stock-strategy/scripts/run_auto_core.ps1",
                     "manage-us-stock-strategy/scripts/register_auto_core_task.ps1",
                     "manage-us-stock-strategy/scripts/collect_30m.ps1"):
            with self.subTest(path=path):
                self.assertTrue(any(rx.match(path) for rx in regexes))
                if not path.endswith(".ps1"):
                    self.assertTrue((ROOT / path).is_file(), path)
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                self.assertTrue(any(devpipe.glob_to_regex(pattern).match(p.relative_to(ROOT).as_posix())
                                    for p in ROOT.glob(pattern)), pattern)

    def test_settings_json_p9(self):
        raw = (ROOT / ".claude" / "settings.json").read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))
        settings = json.loads(raw.decode("utf-8"))
        permissions = settings["permissions"]
        self.assertTrue(set(permissions["deny"]) >= OLD_DENY | P9_DENY)
        self.assertTrue(set(permissions["ask"]) >= OLD_ASK | P9_ASK)
        self.assertEqual(len(permissions["deny"]), len(OLD_DENY | P9_DENY))
        self.assertEqual(len(permissions["ask"]), len(OLD_ASK | P9_ASK))
        self.assertNotIn("allow", permissions)
        self.assertEqual(settings["effortLevel"], "medium")
        self.assertEqual(settings["worktree"], {"baseRef": "head"})

    def test_gitignore_lines(self):
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("workspace/outputs/dev-runs/", lines)
        self.assertIn("docs/claude/_dev-queue/", lines)


if __name__ == "__main__":
    unittest.main()
