"""Tests of the API pilot runner (llm_runner.py).

Every run uses a temporary folder as the repository root, a fake git_show and a fake run_job. The repository's
llm_runner.py is imported only; it is never run against the repository root (no process, no git, no network).
"""

import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
REPO = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("llm_runner", SCRIPT_DIR / "llm_runner.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

KST = MODULE.KST
FAKE_KEY = "fake-key-FOR-TEST-7Q9Z"
PY = "PYTHON-EXE"
DAY = "2026-11-08"
NEXT_DAY = "2026-11-09"
REF = "카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9AAAAAAAAAAAAAAAAAAAA · 선택지 A · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH"
APPROVED_KST = "2026-11-07 10:00:00 KST"
OK_LINE = "llm-iccheck %s OK findings=1 dropped=0" % DAY


def at(hm, day=DAY):
    year, month, dom = (int(part) for part in day.split("-"))
    hour, minute = (int(part) for part in hm.split(":"))
    return datetime(year, month, dom, hour, minute, 0, tzinfo=KST)


def entry(enabled):
    if enabled:
        return {"enabled": True, "approved_ref": REF, "approved_kst": APPROVED_KST}
    return {"enabled": False, "approved_ref": "", "approved_kst": ""}


def schedule_obj(*on):
    return {name: entry(name in on) for name in MODULE.JOB_NAMES}


def encode(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def schedule_bytes(*on):
    return encode(schedule_obj(*on))


class FakeGit:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def __call__(self, repo_root, rel):
        self.calls.append((Path(repo_root), rel))
        return self.data


class FakeRun:
    """Returns the queued results in order; an exception instance is raised instead."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def __call__(self, argv, cwd, timeout):
        self.calls.append((list(argv), cwd, timeout))
        result = self.results.pop(0) if self.results else (0, OK_LINE + "\n")
        if isinstance(result, BaseException):
            raise result
        return result


class RunnerCase(unittest.TestCase):
    def new_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        self.assertFalse(root.is_relative_to(REPO.resolve()))
        return root

    def make_script(self, root, name):
        path = root / "manage-us-stock-strategy" / "scripts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fake pilot, never run\n", encoding="ascii")
        return path

    def run_at(self, root, hm, git_bytes, run_job, day=DAY, dry_run=False):
        git = git_bytes if isinstance(git_bytes, FakeGit) else FakeGit(git_bytes)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code, summary = MODULE.run_once(at(hm, day), repo_root=root, git_show=git, run_job=run_job,
                                            python=PY, dry_run=dry_run)
        return code, summary, out.getvalue()

    def day_file(self, root, day=DAY):
        return root / "workspace" / "outputs" / "llm" / "runner" / (day + ".json")

    def day_doc(self, root, day=DAY):
        return json.loads(self.day_file(root, day).read_text(encoding="utf-8"))


class RepositorySwitchFileTests(RunnerCase):
    """(가) Format only: the enabled values are not asserted, so switching a pilot on later keeps this green."""

    def test_repository_switch_file_format(self):
        raw = (REPO / MODULE.SCHEDULE_REL).read_bytes()
        # Windows checkouts may hold CRLF; the committed blob the runner reads holds LF.
        raw = raw.replace(b"\r\n", b"\n")
        obj = json.loads(raw.decode("utf-8"))
        self.assertIsInstance(obj, dict)
        self.assertEqual(list(obj), list(MODULE.JOB_NAMES))
        self.assertEqual(raw, encode(obj))
        git = FakeGit(raw)
        status, reason, enabled = MODULE.load_schedule(self.new_root(), datetime.now(KST), git)
        self.assertEqual((status, reason), ("OK", None))
        self.assertEqual(enabled, [name for name in MODULE.JOB_NAMES if obj[name]["enabled"] is True])
        self.assertEqual(git.calls[0][1], "docs/claude/llm-pilots-schedule.json")


class CommittedVersionOnlyTests(RunnerCase):
    """(나) The working-tree switch file is never read; only git_show decides."""

    def write_worktree_schedule(self, root, data):
        path = root / "docs" / "claude" / "llm-pilots-schedule.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_worktree_on_but_committed_off_runs_nothing(self):
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        self.write_worktree_schedule(root, schedule_bytes("iccheck"))
        run = FakeRun()
        git = FakeGit(schedule_bytes())
        code, summary, _ = self.run_at(root, "07:35", git, run)
        self.assertEqual(code, 0)
        self.assertEqual(run.calls, [])
        self.assertEqual(summary["due"], 0)
        self.assertEqual(git.calls, [(root, MODULE.SCHEDULE_REL)])
        self.assertEqual(self.day_doc(root)["schedule"], {"status": "OK", "reason": None, "enabled": []})

    def test_worktree_off_but_committed_on_runs_once(self):
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        self.write_worktree_schedule(root, schedule_bytes())
        run = FakeRun()
        code, summary, _ = self.run_at(root, "07:35", schedule_bytes("iccheck"), run)
        self.assertEqual(code, 0)
        self.assertEqual(len(run.calls), 1)
        self.assertEqual(summary["ran"], 1)
        self.assertEqual(self.day_doc(root)["schedule"], {"status": "OK", "reason": None, "enabled": ["iccheck"]})

    def test_default_git_show_reads_head_blob_only(self):
        root = self.new_root()
        seen = []

        def fake_run(argv, **kwargs):
            seen.append((argv, kwargs))
            return SimpleNamespace(returncode=0, stdout=b"{}")

        with mock.patch.object(MODULE.subprocess, "run", fake_run):
            self.assertEqual(MODULE.default_git_show(root, MODULE.SCHEDULE_REL), b"{}")
        self.assertEqual(seen[0][0], ["git", "-C", str(root), "show", "HEAD:docs/claude/llm-pilots-schedule.json"])
        self.assertTrue(seen[0][1]["capture_output"])
        self.assertEqual(seen[0][1]["timeout"], 30)
        with mock.patch.object(MODULE.subprocess, "run", lambda argv, **kw: SimpleNamespace(returncode=128,
                                                                                             stdout=b"")):
            self.assertIsNone(MODULE.default_git_show(root, MODULE.SCHEDULE_REL))
        with mock.patch.object(MODULE.subprocess, "run", mock.Mock(side_effect=FileNotFoundError("git"))):
            self.assertIsNone(MODULE.default_git_show(root, MODULE.SCHEDULE_REL))


class ScheduleRejectionTests(RunnerCase):
    def test_missing_committed_file(self):
        """(다)"""
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        run = FakeRun()
        code, summary, _ = self.run_at(root, "07:35", None, run)
        self.assertEqual(code, 2)
        self.assertEqual(summary["schedule"], "SCHEDULE_MISSING")
        self.assertEqual(run.calls, [])
        doc = self.day_doc(root)
        self.assertEqual(doc["schedule"], {"status": "SCHEDULE_MISSING", "reason": "GIT_SHOW", "enabled": []})
        self.assertEqual(doc["runs"], [])
        self.assertEqual(doc["last_check_kst"], "2026-11-08T07:35:00+09:00")

    def test_invalid_switch_text_rejects_everything(self):
        """(라) iccheck is switched on correctly in every case; one fault elsewhere stops all."""

        def with_fault(fault):
            obj = schedule_obj("iccheck")
            fault(obj)
            return encode(obj)

        def set_entry(name, **values):
            def fault(obj):
                obj[name] = dict(entry(True), **values)
            return fault

        cases = [
            ("not json", b"{not json", "NOT_JSON"),
            ("not utf-8", b"\xff\xfe{}", "NOT_JSON"),
            ("top-level list", b"[]\n", "NOT_OBJECT"),
            ("unknown job", with_fault(lambda obj: obj.update(review=entry(False))), "UNKNOWN_JOB"),
            ("enabled as text", with_fault(lambda obj: obj["news-submit"].update(enabled="true")), "BAD_ENTRY"),
            ("extra key", with_fault(lambda obj: obj["news-submit"].update(note="")), "BAD_ENTRY"),
            ("missing key", with_fault(lambda obj: obj["news-submit"].pop("approved_kst")), "BAD_ENTRY"),
            ("entry not object", with_fault(lambda obj: obj.update({"news-submit": False})), "BAD_ENTRY"),
            ("ref not text", with_fault(lambda obj: obj["news-submit"].update(approved_ref=None)), "BAD_ENTRY"),
            ("empty ref", with_fault(set_entry("news-submit", approved_ref="")), "BAD_REF"),
            ("no cmsg", with_fault(set_entry("news-submit", approved_ref=REF.replace("cmsg_", "card_"))),
             "BAD_REF"),
            ("short cmsg", with_fault(set_entry("news-submit", approved_ref="cmsg_ABC user_01KuMGKfZu1SBYxtMmg4vAiH")),
             "BAD_REF"),
            ("no CEO account", with_fault(set_entry("news-submit", approved_ref=REF.replace(
                "user_01KuMGKfZu1SBYxtMmg4vAiH", "user_01OTHERACCOUNT0000000000"))), "BAD_REF"),
            ("kst format", with_fault(set_entry("news-submit", approved_kst="2026-11-07 10:00 KST")), "BAD_KST"),
            ("kst not a date", with_fault(set_entry("news-submit", approved_kst="2026-13-40 10:00:00 KST")),
             "BAD_KST"),
            ("kst after now", with_fault(set_entry("news-submit", approved_kst="2026-11-08 07:36:00 KST")),
             "BAD_KST"),
        ]
        for label, data, reason in cases:
            with self.subTest(case=label):
                root = self.new_root()
                self.make_script(root, "llm_pilot_iccheck.py")
                self.make_script(root, "llm_pilot_news.py")
                run = FakeRun()
                code, summary, _ = self.run_at(root, "07:35", data, run)
                self.assertEqual(code, 2)
                self.assertEqual(summary["schedule"], "SCHEDULE_INVALID")
                self.assertEqual(run.calls, [])
                doc = self.day_doc(root)
                self.assertEqual(doc["schedule"], {"status": "SCHEDULE_INVALID", "reason": reason, "enabled": []})
                self.assertEqual(doc["runs"], [])

    def test_approval_at_the_same_second_is_accepted(self):
        status, reason, enabled = MODULE.load_schedule(
            self.new_root(), at("10:00", "2026-11-07"), FakeGit(schedule_bytes("iccheck")))
        self.assertEqual((status, reason, enabled), ("OK", None, ["iccheck"]))

    def test_missing_job_counts_as_off(self):
        obj = schedule_obj("iccheck")
        del obj["news-collect"]
        status, reason, enabled = MODULE.load_schedule(self.new_root(), at("07:35"), FakeGit(encode(obj)))
        self.assertEqual((status, reason, enabled), ("OK", None, ["iccheck"]))


class TimingTests(RunnerCase):
    def test_due_window(self):
        """(마) 0 <= now - slot < 60 minutes."""
        for hm, expected in (("07:29", 0), ("07:30", 1), ("08:29", 1), ("08:30", 0)):
            with self.subTest(hm=hm):
                root = self.new_root()
                self.make_script(root, "llm_pilot_iccheck.py")
                run = FakeRun()
                code, summary, _ = self.run_at(root, hm, schedule_bytes("iccheck"), run)
                self.assertEqual(code, 0)
                self.assertEqual(len(run.calls), expected)
                self.assertEqual(summary["due"], expected)
                self.assertEqual(len(self.day_doc(root)["runs"]), expected)

    def test_one_run_per_slot(self):
        """(바)"""
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        run = FakeRun()
        self.run_at(root, "07:35", schedule_bytes("iccheck"), run)
        self.assertEqual(len(run.calls), 1)
        self.run_at(root, "07:45", schedule_bytes("iccheck"), run)
        self.assertEqual(len(run.calls), 1)
        runs = self.day_doc(root)["runs"]
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "OK")
        self.assertEqual(runs[0]["line"], OK_LINE)
        self.assertEqual(runs[0]["exit_code"], 0)
        self.assertEqual(runs[0]["started_kst"], "2026-11-08T07:35:00+09:00")
        self.assertEqual(runs[0]["finished_kst"], "2026-11-08T07:35:00+09:00")
        # The next day is a new day file and the slot runs again.
        self.run_at(root, "07:35", schedule_bytes("iccheck"), run, day=NEXT_DAY)
        self.assertEqual(len(run.calls), 2)
        self.assertEqual(run.calls[1][0][-1], NEXT_DAY)
        self.assertEqual(len(self.day_doc(root, NEXT_DAY)["runs"]), 1)
        self.assertEqual(len(self.day_doc(root)["runs"]), 1)

    def test_started_entry_blocks_a_second_start(self):
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        started = {"schema": "llm-runner-day-1", "day": DAY, "last_check_kst": None, "schedule": None,
                   "runs": [{"job": "iccheck", "slot": "07:30", "started_kst": "2026-11-08T07:30:00+09:00",
                             "finished_kst": None, "exit_code": None, "status": "STARTED", "line": None}]}
        path = self.day_file(root)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(started), encoding="utf-8")
        run = FakeRun()
        code, summary, _ = self.run_at(root, "07:40", schedule_bytes("iccheck"), run)
        self.assertEqual(code, 0)
        self.assertEqual(run.calls, [])
        self.assertEqual(summary["due"], 0)
        self.assertEqual(self.day_doc(root)["runs"], started["runs"])

    def test_started_entry_is_written_before_the_call(self):
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        seen = []

        def run(argv, cwd, timeout):
            seen.append(self.day_doc(root)["runs"])
            return 0, OK_LINE

        self.run_at(root, "07:35", schedule_bytes("iccheck"), run)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], [{"job": "iccheck", "slot": "07:30", "started_kst": "2026-11-08T07:35:00+09:00",
                                    "finished_kst": None, "exit_code": None, "status": "STARTED", "line": None}])

    def test_two_slots_of_one_job(self):
        """(사)"""
        root = self.new_root()
        self.make_script(root, "llm_pilot_news.py")
        run = FakeRun((0, "llm-news %s OK n=1\n" % DAY), (0, "llm-news %s OK n=2\n" % DAY))
        self.run_at(root, "22:05", schedule_bytes("news-collect"), run)
        self.assertEqual(len(run.calls), 1)
        self.run_at(root, "23:05", schedule_bytes("news-collect"), run)
        self.assertEqual(len(run.calls), 2)
        runs = self.day_doc(root)["runs"]
        self.assertEqual([(r["job"], r["slot"], r["status"]) for r in runs],
                         [("news-collect", "22:00", "OK"), ("news-collect", "23:00", "OK")])

    def test_script_not_built(self):
        """(아)"""
        root = self.new_root()
        run = FakeRun()
        code, summary, _ = self.run_at(root, "19:35", schedule_bytes("news-submit"), run)
        self.assertEqual(code, 0)
        self.assertEqual(run.calls, [])
        self.assertEqual(summary["not_built"], 1)
        self.assertEqual(summary["ran"], 0)
        runs = self.day_doc(root)["runs"]
        self.assertEqual(len(runs), 1)
        self.assertEqual((runs[0]["job"], runs[0]["slot"], runs[0]["status"], runs[0]["exit_code"], runs[0]["line"]),
                         ("news-submit", "19:30", "NOT_BUILT", None, ""))
        self.run_at(root, "19:45", schedule_bytes("news-submit"), run)
        self.assertEqual(run.calls, [])
        self.assertEqual(len(self.day_doc(root)["runs"]), 1)


class LaunchTests(RunnerCase):
    def test_argv_cwd_and_timeout(self):
        """(자)"""
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        run = FakeRun()
        self.run_at(root, "07:35", schedule_bytes("iccheck"), run)
        self.assertEqual(run.calls, [([PY, str(root / "manage-us-stock-strategy" / "scripts" / "llm_pilot_iccheck.py"),
                                       "--day", DAY], str(root), 900)])

        root = self.new_root()
        self.make_script(root, "llm_pilot_news.py")
        run = FakeRun()
        self.run_at(root, "22:05", schedule_bytes("news-collect"), run)
        self.assertEqual(run.calls, [([PY, str(root / "manage-us-stock-strategy" / "scripts" / "llm_pilot_news.py"),
                                       "--phase", "collect", "--day", DAY], str(root), 900)])

    def test_default_run_job_passes_no_process_settings_and_captures(self):
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        seen = []

        def fake_run(argv, **kwargs):
            seen.append((argv, kwargs))
            return SimpleNamespace(returncode=0, stdout="noise\n" + OK_LINE + "\n", stderr="stderr text")

        with mock.patch.object(MODULE.subprocess, "run", fake_run):
            code, summary, _ = self.run_at(root, "07:35", schedule_bytes("iccheck"), None)
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 1)
        argv, kwargs = seen[0]
        self.assertEqual(argv, [PY, str(root / "manage-us-stock-strategy" / "scripts" / "llm_pilot_iccheck.py"),
                                "--day", DAY])
        self.assertNotIn("env", kwargs)
        self.assertIs(kwargs["capture_output"], True)
        self.assertEqual(kwargs["timeout"], 900)
        self.assertEqual(kwargs["cwd"], str(root))
        text = self.day_file(root).read_text(encoding="utf-8")
        self.assertNotIn("stderr text", text)
        self.assertNotIn("noise", text)
        self.assertEqual(self.day_doc(root)["runs"][0]["line"], OK_LINE)

    def test_failure_does_not_block_the_next_job(self):
        """(차)"""
        second = (0, "llm-srccheck %s OK n=0\n" % DAY)
        cases = (
            ("timeout", subprocess.TimeoutExpired(["x"], 900), "TIMEOUT", None, ""),
            ("oserror", OSError("secret launch detail"), "LAUNCH_ERROR:OSError", None, ""),
            ("api error", (7, "llm-iccheck %s API_ERROR findings=0 dropped=0\n" % DAY), "API_ERROR", 7,
             "llm-iccheck %s API_ERROR findings=0 dropped=0" % DAY),
        )
        for label, first, status, exit_code, line in cases:
            with self.subTest(case=label):
                root = self.new_root()
                self.make_script(root, "llm_pilot_iccheck.py")
                self.make_script(root, "llm_pilot_srccheck.py")
                run = FakeRun(first, second)
                code, summary, _ = self.run_at(root, "08:15", schedule_bytes("iccheck", "srccheck-submit"), run)
                self.assertEqual(code, 0)
                self.assertEqual([Path(call[0][1]).name for call in run.calls],
                                 ["llm_pilot_iccheck.py", "llm_pilot_srccheck.py"])
                self.assertEqual(run.calls[1][0][2:], ["--phase", "submit", "--day", DAY])
                self.assertEqual(summary["ran"], 2)
                runs = self.day_doc(root)["runs"]
                self.assertEqual((runs[0]["status"], runs[0]["exit_code"], runs[0]["line"]), (status, exit_code, line))
                self.assertEqual(runs[1]["status"], "OK")
                self.assertNotIn("secret launch detail", self.day_file(root).read_text(encoding="utf-8"))
                self.assertIsNotNone(runs[0]["finished_kst"])

    def test_line_filter(self):
        """(카)"""
        cases = (
            ("korean text", (3, "llm-iccheck %s OK 한글\n" % DAY), "", "EXIT_3"),
            ("no llm- prefix", (3, "done %s OK\n" % DAY), "", "EXIT_3"),
            ("too long", (0, "llm-iccheck " + "x" * 201 + "\n"), "", "EXIT_0"),
            ("trailing blank lines", (0, OK_LINE + "\n\n   \n"), OK_LINE, "OK"),
            ("last line is not the good one", (5, OK_LINE + "\nTraceback tail\n"), "", "EXIT_5"),
            ("no status word", (4, "llm-iccheck finished\n"), "llm-iccheck finished", "EXIT_4"),
            ("empty output", (9, ""), "", "EXIT_9"),
        )
        for label, result, line, status in cases:
            with self.subTest(case=label):
                root = self.new_root()
                self.make_script(root, "llm_pilot_iccheck.py")
                self.run_at(root, "07:35", schedule_bytes("iccheck"), FakeRun(result))
                run = self.day_doc(root)["runs"][0]
                self.assertEqual((run["line"], run["status"], run["exit_code"]), (line, status, result[0]))
        self.assertEqual(MODULE.pick_line("llm-a " + "y" * 200), "llm-a " + "y" * 200)

    def test_no_key_text_reaches_the_record(self):
        """(타)"""
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        run = FakeRun((0, "debug " + FAKE_KEY + "\n" + OK_LINE + "\n"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MODULE.main([], now=at("07:35"), repo_root=root, git_show=FakeGit(schedule_bytes("iccheck")),
                               run_job=run)
        self.assertEqual(code, 0)
        self.assertEqual(len(run.calls), 1)
        self.assertNotIn(FAKE_KEY, out.getvalue())
        for path in root.rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_KEY.encode("ascii"), path.read_bytes(), path)
        source = (SCRIPT_DIR / "llm_runner.py").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
        for word in ("environ", "anthropic", "API_KEY", "INVESTV2"):
            with self.subTest(word=word):
                self.assertNotIn(word, source)
                self.assertNotIn(word.lower(), source.lower())


class DayFileTests(RunnerCase):
    def test_broken_day_file_stops_everything(self):
        """(파)"""
        good_run = {"job": "iccheck", "slot": "07:30"}
        cases = (
            ("not json", b"this is { not json"),
            ("not utf-8", b"\xff\xfe\x00"),
            ("not an object", b"[]"),
            ("wrong schema", json.dumps({"schema": "x", "day": DAY, "runs": []}).encode()),
            ("wrong day", json.dumps({"schema": "llm-runner-day-1", "day": NEXT_DAY, "runs": []}).encode()),
            ("runs not a list", json.dumps({"schema": "llm-runner-day-1", "day": DAY, "runs": {}}).encode()),
            ("run without job", json.dumps({"schema": "llm-runner-day-1", "day": DAY,
                                            "runs": [{"slot": "07:30"}]}).encode()),
            ("run with numeric slot", json.dumps({"schema": "llm-runner-day-1", "day": DAY,
                                                  "runs": [dict(good_run, slot=730)]}).encode()),
            ("run not an object", json.dumps({"schema": "llm-runner-day-1", "day": DAY, "runs": ["x"]}).encode()),
        )
        for label, data in cases:
            with self.subTest(case=label):
                root = self.new_root()
                self.make_script(root, "llm_pilot_iccheck.py")
                path = self.day_file(root)
                path.parent.mkdir(parents=True)
                path.write_bytes(data)
                run = FakeRun()
                git = FakeGit(schedule_bytes("iccheck"))
                code, summary, _ = self.run_at(root, "07:35", git, run)
                self.assertEqual(code, 2)
                self.assertEqual(summary["schedule"], "DAY_FILE_BAD")
                self.assertEqual(run.calls, [])
                self.assertEqual(path.read_bytes(), data)
                self.assertEqual(sorted(p.name for p in path.parent.iterdir()), [path.name])

    def test_dry_run_starts_and_writes_nothing(self):
        """(하)"""
        root = self.new_root()
        run = FakeRun()
        code, summary, out = self.run_at(root, "07:35", schedule_bytes("iccheck"), run, dry_run=True)
        self.assertEqual(code, 0)
        self.assertEqual(run.calls, [])
        self.assertIn("due iccheck 07:30", out.splitlines())
        self.assertEqual(summary["due"], 1)
        self.assertFalse((root / "workspace" / "outputs" / "llm" / "runner").exists())
        self.assertFalse((root / "workspace").exists())

    def test_dry_run_with_rejected_schedule_writes_nothing(self):
        root = self.new_root()
        code, summary, _ = self.run_at(root, "07:35", None, FakeRun(), dry_run=True)
        self.assertEqual((code, summary["schedule"]), (2, "SCHEDULE_MISSING"))
        self.assertFalse((root / "workspace").exists())


class ConstantTests(unittest.TestCase):
    def test_constants(self):
        """(거)"""
        expected = (
            ("iccheck", ("07:30",), "llm_pilot_iccheck.py", ()),
            ("srccheck-submit", ("08:10",), "llm_pilot_srccheck.py", ("--phase", "submit")),
            ("srccheck-collect", ("10:10",), "llm_pilot_srccheck.py", ("--phase", "collect")),
            ("pdfcmp-submit", ("13:10",), "llm_pilot_pdfcmp.py", ("--phase", "submit")),
            ("pdfcmp-collect", ("15:10", "17:10"), "llm_pilot_pdfcmp.py", ("--phase", "collect")),
            ("news-submit", ("19:30",), "llm_pilot_news.py", ("--phase", "submit")),
            ("news-collect", ("22:00", "23:00"), "llm_pilot_news.py", ("--phase", "collect")),
        )
        self.assertIsInstance(MODULE.JOBS, tuple)
        self.assertEqual(tuple((job.name, job.times, job.script, job.args) for job in MODULE.JOBS), expected)
        self.assertEqual(tuple(MODULE.JOB_NAMES), tuple(row[0] for row in expected))
        self.assertEqual(MODULE.SCHEDULE_REL, "docs/claude/llm-pilots-schedule.json")
        self.assertEqual(MODULE.CATCH_UP_MINUTES, 60)
        self.assertEqual(MODULE.JOB_TIMEOUT_SECONDS, 900)
        self.assertEqual(MODULE.CEO_ACCOUNT_ID, "user_01KuMGKfZu1SBYxtMmg4vAiH")


class MainTests(RunnerCase):
    def test_unexpected_exception(self):
        """(너)"""
        out = io.StringIO()
        with mock.patch.object(MODULE, "run_once", side_effect=RuntimeError("secret text")), \
                contextlib.redirect_stdout(out):
            code = MODULE.main([])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "llm-runner ERROR RuntimeError\n")
        self.assertNotIn("secret text", out.getvalue())

    def test_summary_line(self):
        root = self.new_root()
        self.make_script(root, "llm_pilot_iccheck.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MODULE.main([], now=at("07:35"), repo_root=root, git_show=FakeGit(schedule_bytes("iccheck")),
                               run_job=FakeRun())
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "llm-runner 2026-11-08 07:35 schedule=OK due=1 ran=1 not_built=0\n")

        root = self.new_root()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MODULE.main(["--dry-run"], now=at("07:35"), repo_root=root,
                               git_show=FakeGit(schedule_bytes("iccheck")), run_job=FakeRun())
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines(),
                         ["due iccheck 07:30", "llm-runner 2026-11-08 07:35 schedule=OK due=1 ran=0 not_built=0"])
        self.assertTrue(re.fullmatch(r"[\x20-\x7e\n]*", out.getvalue()))

        root = self.new_root()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MODULE.main([], now=at("07:35"), repo_root=root, git_show=FakeGit(None), run_job=FakeRun())
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "llm-runner 2026-11-08 07:35 schedule=SCHEDULE_MISSING due=0 ran=0 "
                                         "not_built=0\n")


if __name__ == "__main__":
    unittest.main()
