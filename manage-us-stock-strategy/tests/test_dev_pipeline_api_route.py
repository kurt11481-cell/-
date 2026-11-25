"""Tests for devq-api stage 1 (dev-pipeline Judge on API credits through the Agent SDK).

Covers devpipe pick-route / api-spend-record / route-fallback / judge_routes / test_env, sdk_agent.py with a fake
claude_agent_sdk module, and static checks of tools/dev-run.ps1. Everything runs in temporary folders with fake
keys: no claude, no real SDK, no API call, no Windows task and no real ledger or user environment variable.
"""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools" / "dev_pipeline"
sys.path.insert(0, str(PIPELINE))
import devpipe  # noqa: E402
import sdk_agent  # noqa: E402

TASK = "t-api"
FAKE_KEY = "sk-ant-api03-FAKEKEY-for-tests-only-0123456789abcdef"
KEY_NAMES = ("INVESTV2_DEVQ_API_KEY", "INVESTV2_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
             "ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS", "ANTHROPIC_PROFILE")
GOOD_REF = "card cmsg_0137MRzn9nuDvvQmVxm6WeX9TESTTESTTESTTESTTEST option A by user_01KuMGKfZu1SBYxtMmg4vAiH"
GOOD_KST = "2026-11-25 09:32:27 KST"
ON = {"judge_enabled": True, "approved_ref": GOOD_REF, "approved_kst": GOOD_KST}
OFF = {"judge_enabled": False, "approved_ref": "", "approved_kst": ""}
# 2026-11-25 10:00 KST
NOW = datetime.datetime(2026, 11, 25, 1, 0, tzinfo=datetime.timezone.utc)
# The keys devpipe and the proposal read from a `claude -p --output-format json` Judge envelope.
CLAUDE_P_KEYS = ("type", "subtype", "is_error", "result", "num_turns", "total_cost_usd", "usage", "modelUsage",
                 "session_id", "duration_ms")


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


def run_main(argv):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = devpipe.main(argv)
    return code, out.getvalue().strip()


def judge_text(verdict="PASS"):
    body = {"verdict": verdict, "class_ok": True, "items": [{"id": "G1", "result": verdict}],
            "min_fixes": [] if verdict == "PASS" else ["fix x"]}
    return ("| 항목 | 결과 | 근거 |\n|---|---|---|\n| G1 | %s | a.py:1 |\n\n```json\n%s\n```\nVERDICT: %s\n"
            % (verdict, json.dumps(body, ensure_ascii=False), verdict))


def api_envelope(is_error=True, turns=0, status=None, result=None, subtype="success", cost=0.5):
    return {"type": "result", "subtype": subtype, "is_error": is_error, "result": result, "num_turns": turns,
            "total_cost_usd": cost, "usage": None, "modelUsage": None, "session_id": "s", "duration_ms": 10,
            "route": "api", "api_error_status": status, "kst_end": "2026-11-25T10:00:00+09:00"}


def patch_now(moment=NOW):
    return mock.patch.object(devpipe, "kst_now", return_value=moment.astimezone(devpipe.KST))


def patch_sdk(present=True):
    real = importlib.util.find_spec

    def fake(name, *args, **kwargs):
        if name == devpipe.API_SDK_MODULE:
            return object() if present else None
        return real(name, *args, **kwargs)
    return mock.patch.object(devpipe.importlib.util, "find_spec", side_effect=fake)


class ApiRepo:
    """A temp main repository with docs/claude/devq-api-route.json committed and an empty run folder."""

    def __init__(self, case, head_config=ON):
        self.tmp = Path(tempfile.mkdtemp(prefix="devq-api-test-")).resolve()
        case.addCleanup(remove_tree, self.tmp)
        self.repo = self.tmp / "repo"
        (self.repo / "docs" / "claude").mkdir(parents=True)
        (self.repo / ".gitignore").write_bytes(b"workspace/outputs/dev-runs/\n")
        run_git(self.repo, "init", "-q", "-b", "main")
        for key, value in (("core.autocrlf", "false"), ("user.name", "devq-api-test"),
                           ("user.email", "devq-api-test@example.invalid"), ("commit.gpgsign", "false")):
            run_git(self.repo, "config", key, value)
        if head_config is not None:
            self.write_config(head_config)
        else:
            (self.repo / "docs" / "claude" / "notes.md").write_bytes(b"notes\n")
        self.commit("init")
        self.root = self.repo / devpipe.RUNS_REL
        self.run_dir = self.root / TASK
        devpipe.write_json(self.run_dir / "run.json", {"id": TASK, "repo": str(self.repo)})

    def write_config(self, config):
        data = config if isinstance(config, bytes) else (json.dumps(config) + "\n").encode("utf-8")
        (self.repo / devpipe.API_ROUTE_REL).write_bytes(data)

    def commit(self, message):
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", message)

    def ledger(self, *entries):
        with open(self.root / devpipe.API_SPEND_NAME, "a", encoding="utf-8", newline="\n") as handle:
            for entry in entries:
                handle.write((entry if isinstance(entry, str) else json.dumps(entry)) + "\n")

    def pick(self, role="judge", key="yes", sdk=True, moment=NOW):
        with patch_now(moment), patch_sdk(sdk):
            return run_main(["pick-route", "--run-dir", str(self.run_dir), "--role", role, "--key-present", key])


def spend(kind, usd, task=TASK, attempt=1, kst="2026-11-25T09:00:00+09:00"):
    return {"kst": kst, "id": task, "attempt": attempt, "kind": kind, "usd": usd}


# ------------------------------------------------------------------------------------------ pick-route

class PickRouteTests(unittest.TestCase):
    def test_all_conditions_give_api_with_full_budget(self):
        fx = ApiRepo(self)
        self.assertEqual(fx.pick(), (0, "ROUTE api reason=ok budget=8.00"))

    def test_subscription_table(self):
        cases = []

        def head_off(fx):
            fx.write_config(OFF)
            fx.commit("off")
        cases.append(("head_off", head_off, {}, "disabled"))

        def worktree_only_on(fx):
            fx.write_config(OFF)
            fx.commit("off")
            fx.write_config(ON)  # uncommitted: the working tree is never read
        cases.append(("worktree_only_on", worktree_only_on, {}, "disabled"))

        def bad_ref(fx):
            fx.write_config(dict(ON, approved_ref="card cmsg_short option A by user_01KuMGKfZu1SBYxtMmg4vAiH"))
            fx.commit("bad ref")
        cases.append(("approved_ref_format", bad_ref, {}, "config_invalid"))

        def other_user(fx):
            fx.write_config(dict(ON, approved_ref=GOOD_REF.replace("user_01KuMGKfZu1SBYxtMmg4vAiH", "user_someone")))
            fx.commit("other user")
        cases.append(("approved_ref_other_user", other_user, {}, "config_invalid"))

        def bad_kst(fx):
            fx.write_config(dict(ON, approved_kst="2026-11-25T09:32:27+09:00"))
            fx.commit("bad kst")
        cases.append(("approved_kst_format", bad_kst, {}, "config_invalid"))

        def extra_key(fx):
            fx.write_config(dict(ON, monthly_cap_usd=500))
            fx.commit("extra key")
        cases.append(("extra_key_cannot_raise_cap", extra_key, {}, "config_invalid"))

        def string_true(fx):
            fx.write_config(dict(ON, judge_enabled="true"))
            fx.commit("string")
        cases.append(("judge_enabled_not_bool", string_true, {}, "config_invalid"))

        def not_json(fx):
            fx.write_config(b"{judge_enabled: true}\n")
            fx.commit("not json")
        cases.append(("not_json", not_json, {}, "config_invalid"))

        def off_file(fx):
            (fx.root / devpipe.API_OFF_NAME).write_bytes(b"")
        cases.append(("off_file", off_file, {}, "off_file"))

        def closed(fx):
            (fx.root / (devpipe.API_CLOSED_PREFIX + "2026-11")).write_bytes(b"{}\n")
        cases.append(("closed_month", closed, {}, "closed_month"))

        cases.append(("no_key", lambda fx: None, {"key": "no"}, "no_key"))
        cases.append(("no_sdk", lambda fx: None, {"sdk": False}, "no_sdk"))

        def low(fx):
            fx.ledger(spend("reserve", 8, attempt=1), spend("actual", 57.5, attempt=1))
        cases.append(("remaining_below_floor", low, {}, "cap"))

        def unreadable(fx):
            fx.ledger(spend("reserve", 1), "{not json")
        cases.append(("ledger_unreadable", unreadable, {}, "cap"))

        def bad_entry(fx):
            fx.ledger(spend("reserve", -1))
        cases.append(("ledger_negative", bad_entry, {}, "cap"))

        def no_tz(fx):
            fx.ledger(spend("reserve", 1, kst="2026-11-25T09:00:00"))
        cases.append(("ledger_kst_without_offset", no_tz, {}, "cap"))

        def ledger_dir(fx):
            (fx.root / devpipe.API_SPEND_NAME).mkdir()
        cases.append(("ledger_is_a_folder", ledger_dir, {}, "cap"))

        cases.append(("builder_role", lambda fx: None, {"role": "builder"}, "builder_stage1"))

        for name, prepare, kwargs, reason in cases:
            with self.subTest(case=name):
                fx = ApiRepo(self)
                prepare(fx)
                self.assertEqual(fx.pick(**kwargs), (0, "ROUTE subscription reason=%s" % reason))

    def test_file_missing_in_head_is_disabled(self):
        fx = ApiRepo(self, head_config=None)
        fx.write_config(ON)  # present only in the working tree
        self.assertEqual(fx.pick(), (0, "ROUTE subscription reason=disabled"))

    def test_head_on_wins_over_working_tree_off(self):
        fx = ApiRepo(self)
        fx.write_config(OFF)  # uncommitted
        self.assertEqual(fx.pick(), (0, "ROUTE api reason=ok budget=8.00"))

    def test_budget_is_the_remaining_amount_below_the_per_judge_cap(self):
        fx = ApiRepo(self)
        fx.ledger(spend("reserve", 8, task="a-run"), spend("actual", 55.5, task="a-run"))
        self.assertEqual(fx.pick(), (0, "ROUTE api reason=ok budget=4.50"))
        fx.ledger(spend("reserve", 1.5, task="b-run"))
        self.assertEqual(fx.pick(), (0, "ROUTE api reason=ok budget=3.00"))  # exactly the floor still runs
        fx.ledger(spend("reserve", 0.01, task="c-run"))
        self.assertEqual(fx.pick(), (0, "ROUTE subscription reason=cap"))

    def test_constants(self):
        self.assertEqual((devpipe.DEVQ_API_MONTHLY_CAP_USD, devpipe.DEVQ_API_MIN_REMAINING_USD,
                          devpipe.JUDGE_MAX_BUDGET_USD), (60, 3, 8))
        self.assertEqual(sdk_agent.MAX_BUDGET_USD, devpipe.JUDGE_MAX_BUDGET_USD)
        self.assertEqual(devpipe.API_CLOSE_STATUSES, (401, 403, 429))

    def test_repository_switch_is_off(self):
        raw = (ROOT / devpipe.API_ROUTE_REL).read_bytes()
        self.assertEqual(json.loads(raw.decode("utf-8")), OFF)


class MonthBoundaryTests(unittest.TestCase):
    def test_kst_month(self):
        utc = datetime.timezone.utc
        self.assertEqual(devpipe.kst_month(datetime.datetime(2026, 11, 30, 16, 0, tzinfo=utc)), "2026-12")
        self.assertEqual(devpipe.kst_month(datetime.datetime(2026, 11, 30, 14, 59, tzinfo=utc)), "2026-11")

    def test_new_kst_month_resets_spend_and_closure(self):
        fx = ApiRepo(self)
        fx.ledger(spend("reserve", 8, kst="2026-11-30T23:30:00+09:00"), spend("actual", 58, kst="2026-11-30T23:50:00+09:00"))
        (fx.root / (devpipe.API_CLOSED_PREFIX + "2026-11")).write_bytes(b"{}\n")
        late_november = datetime.datetime(2026, 11, 30, 14, 59, tzinfo=datetime.timezone.utc)  # 23:59 KST
        self.assertEqual(fx.pick(moment=late_november), (0, "ROUTE subscription reason=closed_month"))
        december = datetime.datetime(2026, 11, 30, 16, 0, tzinfo=datetime.timezone.utc)  # 12-01 01:00 KST
        self.assertEqual(fx.pick(moment=december), (0, "ROUTE api reason=ok budget=8.00"))

    def test_entry_month_is_taken_in_kst(self):
        entries = devpipe.read_spend_entries(self._ledger([spend("reserve", 5, kst="2026-11-30T16:00:00+00:00"),
                                                            spend("reserve", 2, task="x", kst="2026-11-30T14:59:00+00:00")]))
        self.assertEqual(devpipe.month_spend(entries, "2026-12"), 5)
        self.assertEqual(devpipe.month_spend(entries, "2026-11"), 2)

    def _ledger(self, entries):
        folder = Path(tempfile.mkdtemp(prefix="devq-api-ledger-"))
        self.addCleanup(remove_tree, folder)
        path = folder / devpipe.API_SPEND_NAME
        path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
        return path


class LedgerTests(unittest.TestCase):
    def test_reserve_counts_until_actual_replaces_it(self):
        month = "2026-11"
        reserve_only = [dict(spend("reserve", 8), month=month)]
        self.assertEqual(devpipe.month_spend(reserve_only, month), 8)
        closed = reserve_only + [dict(spend("actual", 1.25), month=month)]
        self.assertEqual(devpipe.month_spend(closed, month), 1.25)
        two_runs = closed + [dict(spend("reserve", 8, task="t-other", attempt=2), month=month)]
        self.assertEqual(devpipe.month_spend(two_runs, month), 9.25)
        # A reused (id, attempt): each actual closes the reserve written right before it.
        reused = closed + [dict(spend("reserve", 8), month=month), dict(spend("actual", 2), month=month)]
        self.assertEqual(devpipe.month_spend(reused, month), 3.25)
        timeout_then_run = [dict(spend("reserve", 8), month=month), dict(spend("reserve", 6), month=month),
                            dict(spend("actual", 1), month=month)]
        self.assertEqual(devpipe.month_spend(timeout_then_run, month), 9)

    def test_api_spend_record_reserve_and_actual_from_envelope(self):
        fx = ApiRepo(self)
        with patch_now():
            self.assertEqual(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1",
                                       "--kind", "reserve", "--usd", "8.00"])[0], 0)
            # No envelope yet: nothing is written and the reserve keeps counting.
            self.assertEqual(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1",
                                       "--kind", "actual"]), (1, "API_SPEND SKIP kind=actual reason=no_cost"))
            (fx.run_dir / "judge-1.json").write_text(json.dumps(api_envelope(False, 7, cost=1.75)), encoding="utf-8")
            self.assertEqual(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1",
                                       "--kind", "actual"]), (0, "API_SPEND OK kind=actual attempt=1 usd=1.7500"))
        lines = (fx.root / devpipe.API_SPEND_NAME).read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(line) for line in lines], [
            {"kst": "2026-11-25T10:00:00+09:00", "id": TASK, "attempt": 1, "kind": "reserve", "usd": 8.0},
            {"kst": "2026-11-25T10:00:00+09:00", "id": TASK, "attempt": 1, "kind": "actual", "usd": 1.75}])
        self.assertEqual(devpipe.month_spend(devpipe.read_spend_entries(fx.root / devpipe.API_SPEND_NAME), "2026-11"),
                         1.75)

    def test_actual_ignores_subscription_envelope_and_bad_values(self):
        fx = ApiRepo(self)
        envelope = api_envelope(False, 7, cost=1.0)
        del envelope["route"]
        (fx.run_dir / "judge-1.json").write_text(json.dumps(envelope), encoding="utf-8")
        self.assertEqual(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1",
                                   "--kind", "actual"])[0], 1)
        self.assertEqual(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1",
                                   "--kind", "reserve"]), (2, "API_SPEND STOP_API_SPEND reason=usd"))
        for value in ("nan", "inf", "-1"):
            with self.subTest(value=value):
                self.assertEqual(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1",
                                           "--kind", "reserve", "--usd", value])[0], 2)
        self.assertFalse((fx.root / devpipe.API_SPEND_NAME).exists())


# -------------------------------------------------------------------------------------- route-fallback

class RouteFallbackTests(unittest.TestCase):
    def fallback(self, envelope, moment=NOW):
        fx = ApiRepo(self)
        if envelope is not None:
            (fx.run_dir / "judge-1.json").write_text(json.dumps(envelope), encoding="utf-8")
        with patch_now(moment):
            code, line = run_main(["route-fallback", "--run-dir", str(fx.run_dir), "--attempt", "1"])
        closed = sorted(p.name for p in fx.root.glob(devpipe.API_CLOSED_PREFIX + "*"))
        return fx, code, line, closed

    def test_pre_work_error_runs_again_without_closing(self):
        fx, code, line, closed = self.fallback(api_envelope(True, 0, subtype="sdk_exception"))
        self.assertEqual((code, line), (0, "FALLBACK yes reason=pre_work_error:status=none:turns=0 closed=no"))
        self.assertEqual(closed, [])
        self.assertFalse((fx.run_dir / "judge-1.json").exists())
        self.assertEqual(json.loads((fx.run_dir / "judge-1.api.json").read_text(encoding="utf-8"))["route"], "api")

    def test_auth_error_closes_the_month(self):
        fx, code, line, closed = self.fallback(api_envelope(True, 1, status=401, result="Invalid API key"))
        self.assertEqual((code, line), (0, "FALLBACK yes reason=pre_work_error:status=401:turns=1 closed=2026-11"))
        self.assertEqual(closed, ["_api-closed-2026-11"])
        marker = json.loads((fx.root / "_api-closed-2026-11").read_text(encoding="utf-8"))
        self.assertEqual((marker["id"], marker["attempt"], marker["api_error_status"]), (TASK, 1, 401))

    def test_credit_balance_400_closes_the_month(self):
        _, code, line, closed = self.fallback(api_envelope(True, 1, status=400, result="Credit balance is too low"))
        self.assertEqual(code, 0)
        self.assertEqual(closed, ["_api-closed-2026-11"])
        _, code, line, closed = self.fallback(api_envelope(True, 0, status=400, result="Usage LIMIT reached"))
        self.assertEqual(closed, ["_api-closed-2026-11"])

    def test_other_pre_work_errors_do_not_close(self):
        for status, result in ((400, "bad request"), (500, "server error"), (529, "overloaded"), (None, None)):
            with self.subTest(status=status):
                _, code, line, closed = self.fallback(api_envelope(True, 0, status=status, result=result))
                self.assertEqual(code, 0)
                self.assertTrue(line.endswith("closed=no"), line)
                self.assertEqual(closed, [])

    def test_rate_limit_and_forbidden_close(self):
        for status in (403, 429):
            with self.subTest(status=status):
                _, code, _, closed = self.fallback(api_envelope(True, 1, status=status))
                self.assertEqual((code, closed), (0, ["_api-closed-2026-11"]))

    def test_no_second_run_after_work_or_on_budget_stop(self):
        cases = (
            (api_envelope(True, 3, status=401), "FALLBACK no reason=after_work:turns=3"),
            (api_envelope(True, 5, subtype="error_max_budget_usd"), "FALLBACK no reason=max_budget"),
            (api_envelope(True, 1, subtype="error_max_budget_usd"), "FALLBACK no reason=max_budget"),
            (api_envelope(False, 6, result=judge_text()), "FALLBACK no reason=not_error"),
            (api_envelope(True, None), "FALLBACK no reason=turns_unknown"),
            (dict(api_envelope(True, 0), route=None), "FALLBACK no reason=not_api_envelope"),
            (None, "FALLBACK no reason=no_envelope"),
        )
        for envelope, expected in cases:
            with self.subTest(expected=expected):
                fx, code, line, closed = self.fallback(envelope)
                self.assertEqual((code, line, closed), (1, expected, []))
                self.assertFalse((fx.run_dir / "judge-1.api.json").exists())

    def test_month_of_the_closure_is_kst(self):
        december = datetime.datetime(2026, 11, 30, 16, 0, tzinfo=datetime.timezone.utc)
        _, _, line, closed = self.fallback(api_envelope(True, 0, status=429), moment=december)
        self.assertTrue(line.endswith("closed=2026-12"))
        self.assertEqual(closed, ["_api-closed-2026-12"])


# ------------------------------------------------------------------------------- result.json routes

class JudgeRoutesTests(unittest.TestCase):
    OLD_RESULT_KEYS = {"id", "status", "class", "class_reasons", "base", "main_branch", "worktree", "branch",
                       "diff_hash", "judge_file", "judge_file_sha256", "judge_verdict", "tests", "retries", "reasons",
                       "changed_files", "attempts", "builder_runs", "started_utc", "finished_utc", "next", "line"}

    def test_write_result_adds_judge_routes(self):
        fx = ApiRepo(self)
        run = {"id": TASK, "repo": str(fx.repo), "base": "0" * 40, "main_branch": "main", "worktree": "wt",
               "branch": "worktree-" + TASK, "class_initial": "general", "started_utc": "2026-11-25T00:00:00Z"}
        devpipe.write_json(fx.run_dir / "run.json", run)
        for attempt in (1, 2):
            devpipe.write_json(fx.run_dir / ("checks-%d.json" % attempt), {"class": "general", "reasons": []})
        sub = api_envelope(False, 4, result=judge_text("FAIL"))
        del sub["route"]
        (fx.run_dir / "judge-1.api.json").write_text(json.dumps(api_envelope(True, 0)), encoding="utf-8")
        (fx.run_dir / "judge-1.json").write_text(json.dumps(sub), encoding="utf-8")
        (fx.run_dir / "judge-2.json").write_text(json.dumps(api_envelope(False, 5, result=judge_text())),
                                                 encoding="utf-8")
        args = type("A", (), {"run_dir": str(fx.run_dir), "status": "JUDGE_ERROR", "retries": 1, "reason": None})()
        with contextlib.redirect_stdout(io.StringIO()):
            devpipe.cmd_write_result(args)
        expected = [{"attempt": 1, "route": "fallback"}, {"attempt": 2, "route": "api"}]
        result = devpipe.read_json(fx.run_dir / "result.json")
        self.assertEqual(result["judge_routes"], expected)
        self.assertEqual(set(result) - self.OLD_RESULT_KEYS, {"judge_routes"})
        self.assertEqual(devpipe.read_json(fx.root / "LATEST.json")["judge_routes"], expected)

    def test_routes_per_attempt(self):
        fx = ApiRepo(self)
        sub = api_envelope(False, 4)
        del sub["route"]
        (fx.run_dir / "judge-1.json").write_text(json.dumps(sub), encoding="utf-8")
        (fx.run_dir / "judge-2.json").write_bytes(b"not json")
        self.assertEqual(devpipe.judge_routes(fx.run_dir, [1, 2, 3]),
                         [{"attempt": 1, "route": "subscription"}, {"attempt": 2, "route": "subscription"}])


# -------------------------------------------------------------------------------------------- test_env

class TestEnvTests(unittest.TestCase):
    def test_key_names_never_reach_a_test_run(self):
        fake = {"INVESTV2_DEVQ_API_KEY": FAKE_KEY, "INVESTV2_ANTHROPIC_API_KEY": FAKE_KEY,
                "ANTHROPIC_API_KEY": FAKE_KEY, "DEVQ_KEEP_ME": "1"}
        with mock.patch.dict(os.environ, fake):
            env = devpipe.test_env("pyc")
        for name in devpipe.API_KEY_ENV_NAMES:
            self.assertNotIn(name, {k.upper() for k in env})
        self.assertNotIn(FAKE_KEY, json.dumps(env))
        self.assertEqual(env["DEVQ_KEEP_ME"], "1")
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")


# ------------------------------------------------------------------------------------------- sdk_agent

FAKE_SDK_SOURCE = '''
import dataclasses
import hashlib
import json
import os

PLAN = None
CALLS = []
WATCHED = %r


class ClaudeAgentOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@dataclasses.dataclass
class AssistantMessage:
    content: list


@dataclasses.dataclass
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    total_cost_usd: float = None
    usage: dict = None
    result: str = None
    model_usage: dict = None
    api_error_status: int = None


class ResultError(Exception):
    def __init__(self, message, api_error_status=None):
        super().__init__(message)
        self.api_error_status = api_error_status


def _plan():
    if PLAN is not None:
        return PLAN
    with open(os.environ["FAKE_SDK_PLAN"], encoding="utf-8") as handle:
        return json.load(handle)


async def query(*, prompt, options):
    plan = _plan()
    env = options.kwargs.get("env", {})
    record = {"prompt": prompt, "options": {k: v for k, v in options.kwargs.items() if k != "env"},
              "env_names": sorted(env),
              "env_sha256": {k: hashlib.sha256(v.encode("utf-8")).hexdigest() for k, v in env.items()},
              "process_env_names": sorted(name for name in WATCHED if name in os.environ)}
    CALLS.append(record)
    if os.environ.get("FAKE_SDK_RECORD"):
        with open(os.environ["FAKE_SDK_RECORD"], "w", encoding="utf-8") as handle:
            json.dump(record, handle)
    for _ in range(plan.get("assistant", 0)):
        yield AssistantMessage(content=[])
    if plan.get("result") is not None:
        yield ResultMessage(**plan["result"])
    if plan.get("raise"):
        raise ResultError(plan["raise"]["message"], plan["raise"].get("status"))
''' % (KEY_NAMES,)

PASS_RESULT = {"subtype": "success", "duration_ms": 1200, "duration_api_ms": 1100, "is_error": False, "num_turns": 3,
               "session_id": "sess-1", "total_cost_usd": 1.25, "usage": {"input_tokens": 10, "output_tokens": 5},
               "result": judge_text(), "model_usage": {"claude-opus": {"costUSD": 1.25}}}


def agent_argv(out, budget="8.00", prompt="Read workspace/outputs/dev-runs/t-api/judge-prompt.md and follow it exactly."):
    return ["--role", "judge", "--cli", "C:/fake/claude.exe", "--cwd", "C:/fake/worktree", "--prompt-file-line",
            prompt, "--max-turns", "80", "--budget", budget, "--out", str(out)]


class SdkAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="devq-api-sdk-"))
        self.addCleanup(remove_tree, self.tmp)
        self.fake = types.ModuleType("claude_agent_sdk")
        patcher = mock.patch.dict(sys.modules, {"claude_agent_sdk": self.fake})
        patcher.start()
        self.addCleanup(patcher.stop)
        exec(compile(FAKE_SDK_SOURCE, "fake_claude_agent_sdk", "exec"), self.fake.__dict__)

    def run_agent(self, plan, environ=None, argv=None):
        self.fake.PLAN = plan
        self.fake.CALLS.clear()
        if environ is None:
            environ = {name: FAKE_KEY if name == "INVESTV2_DEVQ_API_KEY" else "other-fake-value" for name in KEY_NAMES}
            environ["KEEP"] = "1"
        out = self.tmp / "judge-1.json"
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = sdk_agent.main(argv or agent_argv(out), environ=environ)
        raw = out.read_bytes() if out.is_file() else b""
        return code, stdout.getvalue(), raw, environ

    def test_options_match_the_subscription_judge(self):
        code, stdout, raw, environ = self.run_agent({"assistant": 2, "result": PASS_RESULT})
        self.assertEqual((code, stdout), (0, "SDK-AGENT judge ok turns=3\n"))
        call = self.fake.CALLS[0]
        options = call["options"]
        self.assertEqual(options["system_prompt"], {"type": "preset", "preset": "claude_code"})
        self.assertEqual((options["model"], options["effort"]), ("opus", "xhigh"))
        self.assertEqual(options["tools"], ["Read", "Grep", "Glob"])
        self.assertEqual(options["disallowed_tools"], ["mcp__*"])
        self.assertIs(options["strict_mcp_config"], True)
        self.assertEqual(options["setting_sources"], ["project"])
        self.assertEqual(options["extra_args"], {"permission-prompts": "none"})
        self.assertEqual((options["max_turns"], options["max_budget_usd"]), (80, 8.0))
        self.assertEqual((options["cli_path"], options["cwd"]), ("C:/fake/claude.exe", "C:/fake/worktree"))
        self.assertNotIn("allowed_tools", options)
        self.assertNotIn("permission_mode", options)
        self.assertEqual(call["prompt"], "Read workspace/outputs/dev-runs/t-api/judge-prompt.md and follow it exactly.")
        self.assertEqual(call["env_names"], ["ANTHROPIC_API_KEY"])
        self.assertEqual(call["env_sha256"]["ANTHROPIC_API_KEY"], hashlib.sha256(FAKE_KEY.encode("utf-8")).hexdigest())
        for name in KEY_NAMES:
            self.assertNotIn(name, environ)
        self.assertEqual(environ["KEEP"], "1")

    def test_envelope_reads_like_claude_p(self):
        _, _, raw, _ = self.run_agent({"assistant": 2, "result": PASS_RESULT})
        envelope = json.loads(raw.decode("utf-8"))
        self.assertTrue(set(CLAUDE_P_KEYS) <= set(envelope))
        self.assertEqual(set(envelope), set(sdk_agent.ENVELOPE_KEYS))
        self.assertEqual((envelope["route"], envelope["total_cost_usd"], envelope["num_turns"]), ("api", 1.25, 3))
        self.assertEqual(envelope["modelUsage"], {"claude-opus": {"costUSD": 1.25}})
        self.assertTrue(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$", envelope["kst_end"]))
        parsed = devpipe.parse_judge_envelope(raw)
        self.assertTrue(parsed["ok"], parsed)
        self.assertEqual((parsed["verdict"], parsed["class_ok"]), ("PASS", True))

    def test_no_key_never_calls_the_sdk(self):
        environ = {"ANTHROPIC_API_KEY": "other-fake-value"}
        code, stdout, raw, environ = self.run_agent({"result": PASS_RESULT}, environ=environ)
        self.assertEqual((code, stdout), (1, "SDK-AGENT judge error turns=0\n"))
        self.assertEqual(self.fake.CALLS, [])
        envelope = json.loads(raw.decode("utf-8"))
        self.assertEqual((envelope["is_error"], envelope["subtype"], envelope["num_turns"]), (True, "no_key", 0))
        self.assertEqual(environ, {})
        self.assertEqual(devpipe.fallback_decision(envelope)[0], True)

    def test_exception_before_work_records_type_and_status_only(self):
        plan = {"raise": {"message": "boom message text that must not be copied", "status": 401}}
        code, stdout, raw, _ = self.run_agent(plan)
        self.assertEqual((code, stdout), (1, "SDK-AGENT judge error turns=0\n"))
        envelope = json.loads(raw.decode("utf-8"))
        self.assertEqual((envelope["is_error"], envelope["subtype"], envelope["error_type"], envelope["api_error_status"],
                          envelope["num_turns"], envelope["result"]), (True, "sdk_exception", "ResultError", 401, 0, None))
        self.assertNotIn(b"boom", raw)
        self.assertEqual(devpipe.fallback_decision(envelope), (True, "pre_work_error:status=401:turns=0", True))

    def test_exception_after_work_is_not_run_again(self):
        code, _, raw, _ = self.run_agent({"assistant": 4, "raise": {"message": "x"}})
        envelope = json.loads(raw.decode("utf-8"))
        self.assertEqual((code, envelope["num_turns"]), (1, 4))
        self.assertEqual(devpipe.fallback_decision(envelope)[0], False)

    def test_error_result_then_exit_error_keeps_the_result(self):
        result = dict(PASS_RESULT, is_error=True, num_turns=1, result="API Error: credit balance too low",
                      api_error_status=400, total_cost_usd=0.0)
        code, _, raw, _ = self.run_agent({"result": result, "raise": {"message": "exit 1", "status": 400}})
        envelope = json.loads(raw.decode("utf-8"))
        self.assertEqual((code, envelope["subtype"], envelope["num_turns"], envelope["api_error_status"],
                          envelope["error_type"]), (1, "success", 1, 400, "ResultError"))
        self.assertEqual(devpipe.fallback_decision(envelope), (True, "pre_work_error:status=400:turns=1", True))
        self.assertEqual(devpipe.parse_judge_envelope(raw)["error"], "ENVELOPE_IS_ERROR")

    def test_non_bool_is_error_counts_as_error(self):
        _, _, raw, _ = self.run_agent({"result": dict(PASS_RESULT, is_error=None)})
        self.assertIs(json.loads(raw.decode("utf-8"))["is_error"], True)

    def test_key_is_redacted_from_any_text(self):
        result = dict(PASS_RESULT, result="echo " + FAKE_KEY + "\n" + judge_text())
        _, stdout, raw, _ = self.run_agent({"result": result})
        self.assertNotIn(FAKE_KEY.encode("utf-8"), raw)
        self.assertIn(sdk_agent.REDACTED.encode("utf-8"), raw)
        self.assertNotIn(FAKE_KEY, stdout)

    def test_bad_arguments_fail_before_the_sdk(self):
        out = self.tmp / "judge-1.json"
        for argv in (agent_argv(out, budget="9"), agent_argv(out, budget="0"), agent_argv(out, budget="nan"),
                     agent_argv(out, prompt="line\nbreak"), agent_argv(out, prompt="")):
            with self.subTest(argv=argv):
                code, _, raw, _ = self.run_agent({"result": PASS_RESULT}, argv=argv)
                envelope = json.loads(raw.decode("utf-8"))
                self.assertEqual((code, envelope["is_error"], envelope["num_turns"]), (1, True, 0))
                self.assertTrue(envelope["subtype"].startswith("bad_arguments:"))
        self.assertEqual(self.fake.CALLS, [])

    def test_missing_sdk_is_a_pre_work_error(self):
        out = self.tmp / "judge-1.json"
        environ = {"INVESTV2_DEVQ_API_KEY": FAKE_KEY}

        def missing():
            raise ModuleNotFoundError("No module named 'claude_agent_sdk'")
        with contextlib.redirect_stdout(io.StringIO()):
            code = sdk_agent.main(agent_argv(out), environ=environ, sdk_loader=missing)
        envelope = json.loads(out.read_bytes().decode("utf-8"))
        self.assertEqual((code, envelope["subtype"], envelope["error_type"], envelope["num_turns"]),
                         (1, "sdk_setup_error", "ModuleNotFoundError", 0))
        self.assertTrue(devpipe.fallback_decision(envelope)[0])

    def test_key_never_reaches_envelope_stdout_ledger_or_route_lines(self):
        fx = ApiRepo(self)
        out = fx.run_dir / "judge-1.json"
        self.fake.PLAN = {"result": dict(PASS_RESULT, is_error=True, num_turns=0, api_error_status=401,
                                         result="Invalid API key " + FAKE_KEY)}
        environ = {"INVESTV2_DEVQ_API_KEY": FAKE_KEY}
        lines = []
        with patch_now(), patch_sdk(True):
            lines.append(run_main(["pick-route", "--run-dir", str(fx.run_dir), "--role", "judge",
                                   "--key-present", "yes"])[1])
            lines.append(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1", "--kind",
                                   "reserve", "--usd", "8.00"])[1])
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                sdk_agent.main(agent_argv(out), environ=environ)
            lines.append(stdout.getvalue())
            lines.append(run_main(["api-spend-record", "--run-dir", str(fx.run_dir), "--attempt", "1", "--kind",
                                   "actual"])[1])
            lines.append(run_main(["route-fallback", "--run-dir", str(fx.run_dir), "--attempt", "1"])[1])
        self.assertTrue(lines[-1].startswith("FALLBACK yes"), lines)
        blob = "\n".join(lines).encode("utf-8")
        for path in sorted(fx.root.rglob("*")):
            if path.is_file():
                blob += path.read_bytes()
        self.assertNotIn(FAKE_KEY.encode("utf-8"), blob)
        self.assertNotIn(FAKE_KEY[-20:].encode("utf-8"), blob)
        self.assertTrue((fx.root / "_api-closed-2026-11").is_file())

    def test_end_to_end_in_its_own_process(self):
        """sdk_agent.py as dev-run starts it: a fresh python, fake SDK first on PYTHONPATH, fake keys only."""
        fake_dir = self.tmp / "fake"
        (fake_dir / "claude_agent_sdk").mkdir(parents=True)
        (fake_dir / "claude_agent_sdk" / "__init__.py").write_text(FAKE_SDK_SOURCE, encoding="utf-8")
        plan = self.tmp / "plan.json"
        plan.write_text(json.dumps({"assistant": 2, "result": PASS_RESULT}), encoding="utf-8")
        record = self.tmp / "record.json"
        out = self.tmp / "judge-1.json"
        env = {k: v for k, v in os.environ.items() if k.upper() not in KEY_NAMES and k.upper() != "PYTHONPATH"}
        env.update({name: "other-fake-value" for name in KEY_NAMES})
        env.update({"INVESTV2_DEVQ_API_KEY": FAKE_KEY, "PYTHONPATH": str(fake_dir), "FAKE_SDK_PLAN": str(plan),
                    "FAKE_SDK_RECORD": str(record), "PYTHONIOENCODING": "utf-8"})
        proc = subprocess.run([sys.executable, str(PIPELINE / "sdk_agent.py")] + agent_argv(out), env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(proc.stdout.decode("ascii").splitlines(), ["SDK-AGENT judge ok turns=3"])
        seen = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(seen["process_env_names"], [])  # all seven names gone from the agent process
        self.assertEqual(seen["env_names"], ["ANTHROPIC_API_KEY"])
        self.assertEqual(seen["env_sha256"]["ANTHROPIC_API_KEY"], hashlib.sha256(FAKE_KEY.encode("utf-8")).hexdigest())
        for data in (proc.stdout, proc.stderr, out.read_bytes(), record.read_bytes()):
            self.assertNotIn(FAKE_KEY.encode("utf-8"), data)
        self.assertTrue(devpipe.parse_judge_envelope(out.read_bytes())["ok"])


# ------------------------------------------------------------------------------- dev-run.ps1 (static)

class DevRunStaticTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "tools" / "dev-run.ps1").read_bytes().decode("ascii")

    def function(self, name):
        return re.search(r"^function %s\b[^\n]*\{\r?\n(.*?)^\}\r?$" % re.escape(name), self.text, re.S | re.M).group(1)

    def test_keys_removed_at_start_and_given_to_one_child_only(self):
        removal = ("foreach ($keyName in @('INVESTV2_DEVQ_API_KEY', 'INVESTV2_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY')) {\r\n"
                   "    [Environment]::SetEnvironmentVariable($keyName, $null, 'Process')\r\n}\r\n")
        self.assertIn(removal, self.text)
        self.assertLess(self.text.index(removal), self.text.index("$IdPattern = "))
        self.assertEqual(self.text.count("GetEnvironmentVariable('INVESTV2_DEVQ_API_KEY', 'User')"), 2)
        self.assertIn("[string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable('INVESTV2_DEVQ_API_KEY', 'User'))",
                      self.function("Start-Judge"))
        api = self.function("Start-JudgeApi")
        self.assertIn("$keyEnv = @{ 'INVESTV2_DEVQ_API_KEY' = [Environment]::GetEnvironmentVariable(", api)
        self.assertIn("-ExtraEnv $keyEnv", api)
        self.assertLess(api.index("-ExtraEnv $keyEnv"), api.index("$keyEnv.Clear()"))
        self.assertLess(api.index("$keyEnv = $null"), api.index("Wait-Captured"))
        self.assertEqual(self.text.count("$keyEnv"), 4)  # set, passed to Start-Captured, cleared, dropped
        self.assertEqual(self.text.count("EnvironmentVariables["), 1)
        self.assertIn("$psi.EnvironmentVariables[", self.function("Start-Captured"))
        for word in ("$env:INVESTV2", "$env:ANTHROPIC", "set INVESTV2", "set ANTHROPIC", "SetEnvironmentVariable('INVESTV2"):
            self.assertNotIn(word, self.text)
        for line in self.text.splitlines():
            if "Write-Log" in line or "Write-Output" in line:
                self.assertNotIn("keyEnv", line)
                self.assertNotIn("GetEnvironmentVariable", line)

    def test_judge_route_order(self):
        body = self.function("Start-Judge")
        order = ["@('pick-route', ", "'--kind', 'reserve'", "Start-JudgeApi -Attempt", "'--kind', 'actual'",
                 "@('route-fallback', ", "ROUTE_FALLBACK judge-", "Start-JudgeSubscription -Attempt"]
        positions = [body.index(item) for item in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("'--role', 'judge'", body)
        self.assertIn("if ($api.TimedOut) { return $api }", body)
        self.assertEqual(self.text.count("Start-JudgeSubscription -Attempt"), 1)
        self.assertEqual(self.text.count("Start-JudgeApi -Attempt"), 1)
        for word in ("Write-Log ('ROUTE judge-' + $Attempt + ' api reason=ok budget='",
                     "Write-Log ('ROUTE judge-' + $Attempt + ' subscription reason='",
                     "Write-Log ('ROUTE_FALLBACK judge-' + $Attempt + ' reason='"):
            self.assertIn(word, body)
        # The Builder never takes the api route.
        self.assertNotIn("pick-route", self.function("Start-Builder"))
        self.assertNotIn("ExtraEnv", self.function("Start-Builder"))

    def test_subscription_command_and_api_values_match(self):
        sub = self.function("Start-JudgeSubscription")
        self.assertIn('--model opus --effort xhigh --tools "Read,Grep,Glob"', sub)
        self.assertIn("--max-turns ' + $JudgeMaxTurns", sub)
        self.assertIn("-WorkingDirectory $worktree -TimeoutSeconds ($JudgeTimeoutMinutes * 60)", sub)
        api = self.function("Start-JudgeApi")
        for word in ("--role judge --cli \"' + $script:claude", "--cwd \"' + $worktree", "(Get-JudgePromptText)",
                     "--max-turns ' + $JudgeMaxTurns", "--budget ' + $Budget",
                     "-WorkingDirectory $repo -ExtraEnv $keyEnv", "-TimeoutSeconds ($JudgeTimeoutMinutes * 60)"):
            self.assertIn(word, api)
        self.assertIn("(Get-JudgePromptText)", api)
        self.assertIn("Get-JudgePromptText", sub)
        self.assertIn("$sdkAgent = Join-Path $PSScriptRoot 'dev_pipeline\\sdk_agent.py'", self.text)
        self.assertIn("$JudgeMaxTurns = 80", self.text)
        self.assertIn("$JudgeTimeoutMinutes = 45", self.text)

    def test_route_line_pattern_matches_devpipe_output(self):
        pattern = re.search(r"-cmatch '(\^ROUTE api [^']+)'", self.function("Start-Judge")).group(1)
        for budget in (8, 3, 4.5, 7.99):
            line = "ROUTE api reason=ok budget=%.2f" % budget
            self.assertTrue(re.match(pattern, line), line)
        self.assertFalse(re.match(pattern, "ROUTE subscription reason=cap"))
        self.assertIn("-cmatch '^FALLBACK yes '", self.function("Start-Judge"))

    def test_wait_captured_keeps_the_timeout_kill(self):
        wait = self.function("Wait-Captured")
        for word in ("WaitForExit($TimeoutSeconds * 1000)", "Stop-ProcessTree -ProcessId $proc.Id",
                     "[void]$proc.WaitForExit(60000)", "$code = $proc.ExitCode"):
            self.assertIn(word, wait)
        self.assertIn("return (Wait-Captured -Process $proc -TimeoutSeconds $TimeoutSeconds)",
                      self.function("Invoke-Captured"))


HARNESS_DEVPIPE = r'''import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
with open(ROOT / "devpipe-calls.jsonl", "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"argv": args, "key_env": "INVESTV2_DEVQ_API_KEY" in os.environ,
                             "anthropic_env": "ANTHROPIC_API_KEY" in os.environ}) + "\n")
plan = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))
if args[0] == "pick-route":
    print(plan["route_line"])
    sys.exit(plan.get("route_code", 0))
if args[0] == "api-spend-record":
    kind = args[args.index("--kind") + 1]
    print("API_SPEND OK kind=" + kind)
    sys.exit(plan.get("reserve_code", 0) if kind == "reserve" else 0)
if args[0] == "route-fallback":
    line = plan["fallback_line"]
    if line.startswith("FALLBACK yes"):
        run_dir = Path(args[args.index("--run-dir") + 1])
        os.replace(run_dir / "judge-1.json", run_dir / "judge-1.api.json")
    print(line)
    sys.exit(0 if line.startswith("FALLBACK yes") else 1)
print("UNKNOWN")
sys.exit(2)
'''

HARNESS_SDK_AGENT = r'''import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
key = os.environ.get("INVESTV2_DEVQ_API_KEY")
with open(ROOT / "sdk-calls.jsonl", "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"argv": args, "key_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest() if key else None,
                             "anthropic_env": "ANTHROPIC_API_KEY" in os.environ, "cwd": os.getcwd()}) + "\n")
envelope = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))["sdk_envelope"]
Path(args[args.index("--out") + 1]).write_text(json.dumps(envelope), encoding="utf-8")
print("SDK-AGENT judge %s turns=%s" % ("error" if envelope["is_error"] else "ok", envelope["num_turns"]))
'''

HARNESS_CLAUDE = (
    "@echo off\r\n"
    "if defined INVESTV2_DEVQ_API_KEY (echo KEY>>\"%~dp0claude-env.txt\") else (echo NOKEY>>\"%~dp0claude-env.txt\")\r\n"
    "if defined ANTHROPIC_API_KEY (echo ANTHROPIC>>\"%~dp0claude-env.txt\")\r\n"
    "echo {\"type\": \"result\", \"subtype\": \"success\", \"is_error\": false, \"result\": \"subscription\", "
    "\"num_turns\": 2}\r\n")

HARNESS_TAIL = (
    "\r\n# ---- test harness (test_dev_pipeline_api_route.py): replaces the main block of the copy ----\r\n"
    "$script:fakeUserKey = [Environment]::GetEnvironmentVariable('HARNESS_FAKE_USER_KEY', 'Process')\r\n"
    "[Environment]::SetEnvironmentVariable('HARNESS_FAKE_USER_KEY', $null, 'Process')\r\n"
    "$python = [Environment]::GetEnvironmentVariable('HARNESS_PYTHON', 'Process')\r\n"
    "$script:claude = Join-Path $repo 'fake-claude.cmd'\r\n"
    "New-Item -ItemType Directory -Force -Path $script:runDir | Out-Null\r\n"
    "New-Item -ItemType Directory -Force -Path $worktree | Out-Null\r\n"
    "$script:consoleDir = Join-Path $script:runDir 'console'\r\n"
    "New-Item -ItemType Directory -Force -Path $script:consoleDir | Out-Null\r\n"
    "$script:logPath = Join-Path $script:runDir 'log.txt'\r\n"
    "$result = Start-Judge -Attempt 1\r\n"
    "Write-Output ('HARNESS code=' + $result.Code + ' timeout=' + $result.TimedOut)\r\n")

USER_KEY_READ = "[Environment]::GetEnvironmentVariable('INVESTV2_DEVQ_API_KEY', 'User')"


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell is not available")
class StartJudgeCopyTests(unittest.TestCase):
    """Runs a copy of dev-run.ps1's definitions (everything before its main block, never the script itself) in a
    temporary folder whose devpipe.py, sdk_agent.py and claude are fakes. The user-scope key read is replaced by a
    fake value in the copy, so no real user variable is read; the parent process gets fake keys that the copy's
    start-up removal must clear."""

    def harness(self, plan, user_key=FAKE_KEY):
        tmp = Path(tempfile.mkdtemp(prefix="devq-api-ps-")).resolve()
        self.addCleanup(remove_tree, tmp)
        text = (ROOT / "tools" / "dev-run.ps1").read_bytes().decode("ascii")
        self.assertEqual(text.count("# ---- main ----"), 1)
        self.assertEqual(text.count(USER_KEY_READ), 2)
        prefix = text[:text.index("# ---- main ----")].replace(USER_KEY_READ, "$script:fakeUserKey")
        self.assertNotIn("'User'", prefix)
        (tmp / "tools" / "dev_pipeline").mkdir(parents=True)
        script = tmp / "tools" / "judge-harness.ps1"
        script.write_bytes((prefix + HARNESS_TAIL).encode("ascii"))
        (tmp / "tools" / "dev_pipeline" / "devpipe.py").write_text(HARNESS_DEVPIPE, encoding="utf-8")
        (tmp / "tools" / "dev_pipeline" / "sdk_agent.py").write_text(HARNESS_SDK_AGENT, encoding="utf-8")
        (tmp / "fake-claude.cmd").write_bytes(HARNESS_CLAUDE.encode("ascii"))
        (tmp / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k.upper() not in KEY_NAMES}
        env.update({"INVESTV2_DEVQ_API_KEY": "fake-parent-value", "INVESTV2_ANTHROPIC_API_KEY": "fake-parent-value",
                    "ANTHROPIC_API_KEY": "fake-parent-value", "HARNESS_FAKE_USER_KEY": user_key,
                    "HARNESS_PYTHON": sys.executable})
        result = subprocess.run([shutil.which("powershell.exe"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
                                 "Bypass", "-File", str(script), TASK], cwd=str(tmp), env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        run_dir = tmp / "workspace" / "outputs" / "dev-runs" / TASK

        def lines(name):
            path = tmp / name
            return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        out = {"stdout": result.stdout.decode("ascii", "replace").strip(), "run_dir": run_dir, "tmp": tmp,
               "log": (run_dir / "log.txt").read_bytes().decode("ascii"), "devpipe": lines("devpipe-calls.jsonl"),
               "sdk": lines("sdk-calls.jsonl"),
               "claude": (tmp / "claude-env.txt").read_text(encoding="ascii").split() if (tmp / "claude-env.txt").exists()
               else None}
        blob = b""
        for path in run_dir.rglob("*"):
            if path.is_file():
                blob += path.read_bytes()
        self.assertNotIn(FAKE_KEY.encode("utf-8"), blob + result.stdout + result.stderr)
        self.assertNotIn(b"fake-parent-value", blob + result.stdout + result.stderr)
        for call in out["devpipe"]:
            self.assertEqual((call["key_env"], call["anthropic_env"]), (False, False), call)
        return out

    def test_subscription_route_runs_claude_only(self):
        out = self.harness({"route_line": "ROUTE subscription reason=disabled"})
        self.assertEqual(out["stdout"], "HARNESS code=0 timeout=False")
        self.assertEqual([c["argv"] for c in out["devpipe"]],
                         [["pick-route", "--run-dir", str(out["run_dir"]), "--role", "judge", "--key-present", "yes"]])
        self.assertEqual(out["sdk"], [])
        self.assertEqual(out["claude"], ["NOKEY"])
        self.assertIn("ROUTE judge-1 subscription reason=disabled", out["log"])
        self.assertIn("JUDGE start attempt=1\n", out["log"].replace("\r\n", "\n"))

    def test_api_route_gives_the_key_to_the_sdk_child_only(self):
        envelope = api_envelope(False, 5, result="judge text", cost=1.5)
        out = self.harness({"route_line": "ROUTE api reason=ok budget=8.00", "sdk_envelope": envelope,
                            "fallback_line": "FALLBACK no reason=not_error"})
        self.assertEqual(out["stdout"], "HARNESS code=0 timeout=False")
        rd = str(out["run_dir"])
        self.assertEqual([c["argv"] for c in out["devpipe"]], [
            ["pick-route", "--run-dir", rd, "--role", "judge", "--key-present", "yes"],
            ["api-spend-record", "--run-dir", rd, "--attempt", "1", "--kind", "reserve", "--usd", "8.00"],
            ["api-spend-record", "--run-dir", rd, "--attempt", "1", "--kind", "actual"],
            ["route-fallback", "--run-dir", rd, "--attempt", "1"]])
        self.assertEqual(len(out["sdk"]), 1)
        sdk = out["sdk"][0]
        self.assertEqual(sdk["key_sha256"], hashlib.sha256(FAKE_KEY.encode("utf-8")).hexdigest())
        self.assertFalse(sdk["anthropic_env"])
        self.assertEqual(Path(sdk["cwd"]).resolve(), out["tmp"])  # python in the main checkout, CLI via --cwd
        argv = sdk["argv"]
        self.assertEqual(argv[:2], ["--role", "judge"])
        self.assertEqual(argv[argv.index("--cli") + 1], str(out["tmp"] / "fake-claude.cmd"))
        self.assertEqual(argv[argv.index("--cwd") + 1], str(out["tmp"] / ".claude" / "worktrees" / TASK))
        self.assertEqual(argv[argv.index("--prompt-file-line") + 1],
                         "Read workspace/outputs/dev-runs/t-api/judge-prompt.md and follow it exactly.")
        self.assertEqual((argv[argv.index("--max-turns") + 1], argv[argv.index("--budget") + 1]), ("80", "8.00"))
        self.assertEqual(argv[argv.index("--out") + 1], str(out["run_dir"] / "judge-1.json"))
        self.assertIsNone(out["claude"])
        for word in ("ROUTE judge-1 api reason=ok budget=8.00", "JUDGE start attempt=1 route=api",
                     "JUDGE end attempt=1 route=api exit=0 timeout=False"):
            self.assertIn(word, out["log"])
        self.assertNotIn("ROUTE_FALLBACK", out["log"])
        self.assertEqual(json.loads((out["run_dir"] / "judge-1.json").read_text(encoding="utf-8"))["route"], "api")

    def test_pre_work_failure_runs_the_subscription_judge_once(self):
        out = self.harness({"route_line": "ROUTE api reason=ok budget=5.50", "sdk_envelope": api_envelope(True, 0),
                            "fallback_line": "FALLBACK yes reason=pre_work_error:status=401:turns=0 closed=2026-11"})
        self.assertEqual(out["stdout"], "HARNESS code=0 timeout=False")
        self.assertEqual(len(out["sdk"]), 1)
        self.assertEqual(out["claude"], ["NOKEY"])
        self.assertIn("ROUTE_FALLBACK judge-1 reason=pre_work_error:status=401:turns=0", out["log"])
        self.assertLess(out["log"].index("ROUTE_FALLBACK"), out["log"].index("JUDGE start attempt=1\r\n"))
        self.assertEqual(json.loads((out["run_dir"] / "judge-1.api.json").read_text(encoding="utf-8"))["route"], "api")
        self.assertEqual(json.loads((out["run_dir"] / "judge-1.json").read_text(encoding="utf-8"))["result"],
                         "subscription")

    def test_ledger_or_route_failures_fall_back_to_subscription(self):
        cases = (({"route_line": "ROUTE api reason=ok budget=8.00", "reserve_code": 2}, "spend_record_failed"),
                 ({"route_line": "ROUTE STOP_INTERNAL_ERROR type=KeyError", "route_code": 2}, "pick_route_failed"),
                 ({"route_line": "ROUTE api reason=ok budget=800"}, "pick_route_failed"))
        for plan, reason in cases:
            with self.subTest(reason=reason, plan=plan):
                out = self.harness(plan)
                self.assertEqual(out["sdk"], [])
                self.assertEqual(out["claude"], ["NOKEY"])
                self.assertIn("ROUTE judge-1 subscription reason=" + reason, out["log"])

    def test_no_user_key_is_passed_as_key_present_no(self):
        out = self.harness({"route_line": "ROUTE subscription reason=no_key"}, user_key="")
        self.assertEqual(out["devpipe"][0]["argv"][-2:], ["--key-present", "no"])


class RequirementsTests(unittest.TestCase):
    def test_sdk_is_pinned(self):
        lines = [line.strip() for line in (PIPELINE / "requirements-sdk.txt").read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.strip().startswith("#")]
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], r"^claude-agent-sdk==\d+\.\d+\.\d+$")

    def test_sdk_imported_only_by_sdk_agent(self):
        source = (PIPELINE / "devpipe.py").read_text(encoding="utf-8")
        self.assertNotIn("import claude_agent_sdk", source)
        self.assertNotIn("import_module(", source)
        for name in ("devpipe.py", "sdk_agent.py"):
            text = (PIPELINE / name).read_text(encoding="utf-8")
            for word in ("INVESTV2_DEVQ_API_KEY\"]", "print(key", "environ[KEY_ENV]"):
                self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
