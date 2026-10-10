#!/usr/bin/env python3
"""devpipe.py - deterministic decisions for the Investment_V2 dev pipeline (redesign T3).

Called by tools/dev-run.ps1, tools/dev-merge.ps1 and tools/dev-queue.ps1, which stay thin. Standard
library only. Every subcommand reads and writes UTF-8 files, prints one ASCII line on stdout and exits
0 (ok), 1 (retryable or "no") or 2 (stop); `merge` also uses 3 (user approval needed).

The safety constants below (protected paths, task-id format, CLI requirements, test conditions) are
code: a task prompt or its dev-run block cannot change them. git and python run with argument lists
through subprocess and their output is kept as bytes (no shell, no PowerShell pipes). Nothing here
publishes to a remote, deletes a task branch or worktree, reads secrets, or touches an order or
broker path. A Builder's own report is never used for a decision.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

# ----------------------------------------------------------------------------------------- constants

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
MIN_CLAUDE_VERSION = (2, 1, 296)  # Claude Code installed at redesign T3 step 0a (2026-10-10)
REQUIRED_CLI_FLAGS = (
    ("-p", None),
    ("--worktree", None),
    ("--model", None),
    ("--effort", "xhigh"),
    ("--permission-mode", "acceptEdits"),
    ("--permission-prompts", "none"),
    ("--max-turns", None),
    ("--output-format", "json"),
    ("--tools", None),
    ("--allowedTools", None),
    ("--strict-mcp-config", None),
    ("--setting-sources", "project"),
    ("--disallowedTools", None),
)
CLI_FLAG_ALIASES = {"--allowedTools": ("--allowedTools", "--allowed-tools"),
                    "--disallowedTools": ("--disallowedTools", "--disallowed-tools")}
# Documented in the Claude Code CLI reference but not printed by `claude --help` (the reference says
# --help is not exhaustive). Accepted only when the CLI parser itself recognises the flag: the probe
# puts an unknown flag after it, and the parser stops at the first unknown option before any prompt is
# read, so no model is called.
HELP_HIDDEN_DOCUMENTED_FLAGS = ("--max-turns",)
PROBE_UNKNOWN_FLAG = "--zz-devpipe-probe"

RUNS_REL = "workspace/outputs/dev-runs"
WORKTREES_REL = ".claude/worktrees"
QUEUE_REL = "docs/claude/_dev-queue"
PENDING_REL = "docs/claude/_pending"
DOCS_RUNS_REL = "docs/claude/dev-runs"
TESTS_DIR_REL = "manage-us-stock-strategy/tests"
SCHEMA_AUDIT_REL = "manage-us-stock-strategy/scripts/validate_schema_contracts.py"
JUDGE_PROMPT_REL = "tools/dev_pipeline/judge-prompt.md"
BUILDER_RULES_REL = "tools/dev_pipeline/builder-rules.md"
AUTHORITY_PATHS_REL = "tools/dev_pipeline/authority-paths.txt"
FULL_SUITE_PATTERN = "test_*.py"
TARGET_TIMEOUT_S = 30 * 60
FULL_TIMEOUT_S = 60 * 60
SCHEMA_TIMEOUT_S = 10 * 60
GIT_TIMEOUT_S = 10 * 60
CLI_TIMEOUT_S = 90

# P6 protected paths: a pipeline task can never change these; changing them takes the old route
# (worktree Builder + separate Judge + user). Compared in lower case because Windows file names ignore
# case. The task's own prompt (docs/claude/<id>-builder-prompt.md) is added per task.
PROTECTED_PREFIXES = (
    "tools/",
    ".claude/",
    "docs/claude/dev-runs/",
    "docs/claude/_pending/",
    "docs/claude/_dev-queue/",
    "workspace/policies/",
    "stock-strategy-system/",
)
PROTECTED_GLOBS = ("manage-us-stock-strategy/tests/test_dev_pipeline*.py",)
# Names protected at any depth: Claude Code also loads nested CLAUDE.md and .claude folders, and a nested
# .gitignore could hide new files from the scope check. Root-level CLAUDE.md, AGENTS.md, .mcp.json,
# .gitignore, .gitattributes and .worktreeinclude are covered by the same rule.
PROTECTED_NAMES = ("claude.md", "claude.local.md", "agents.md", ".mcp.json", ".gitignore", ".gitattributes",
                   ".worktreeinclude")
PROTECTED_DIR_NAMES = (".claude",)

ORDER_MARKERS = ("/api/us/ordr", "ust2000", "ust2001", "kiwoom_order", "order_submit", "overseas orders")
ORDER_AUTHORITY_TRUE_RE = re.compile(r"order_authority\W{0,3}\s*[:=]\s*\W{0,2}true", re.I)
# A modified line also appears as a removed line, so changing any of these values raises the class.
REMOVED_LINE_MARKERS = ("order_authority", "kill_switch", "quantity_authority", "execution_quantity",
                        "watchlist_approved", "active_universe_approved", "new_buy_instrument_approved")
CHANGED_LINE_MARKERS = ("kill_switch",)
SECRET_NAME_RE = re.compile(
    r"^(\.env.*|.*\.(pem|key|p12|pfx|ppk)|credentials.*\.json|secrets.*\.json|tokens?\.json"
    r"|id_(rsa|dsa|ecdsa|ed25519).*)$", re.I)
IGNORED_CODE_SUFFIXES = (".py", ".pth", ".pyd")

BLOCK_KEYS = ("task_id", "class", "builder_model", "builder_effort", "max_turns", "builder_timeout_min",
              "allowed_paths", "target_tests", "commit_message")
BLOCK_OPEN_RE = re.compile(r"^```dev-run[ \t]*\r?$", re.M)
BLOCK_RE = re.compile(r"^```dev-run[ \t]*\r?\n(.*?)\r?\n```[ \t]*\r?$", re.M | re.S)
TARGET_TEST_RE = re.compile(r"^test[A-Za-z0-9_*-]*\.py$")
ALLOWED_PATH_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
FINAL_STATUSES = ("READY_TO_MERGE", "NEEDS_APPROVAL", "FAIL", "BLOCKED", "JUDGE_ERROR", "TIMEOUT")
STOP_STATUS_RE = re.compile(r"^STOP_[A-Z0-9_]+$")

RAN_RE = re.compile(r"^Ran (\d+) tests? in [0-9.]+s[ \t]*$", re.M)
STATUS_RE = re.compile(r"^(OK|FAILED|NO TESTS RAN)(?: \(([^)]*)\))?[ \t]*$", re.M)
FAIL_RE = re.compile(r"^={70}\n(FAIL|ERROR): (.+?)[ \t]*$", re.M)
TEST_DEF_RE = re.compile(rb"^[ \t]*(?:async[ \t]+)?def[ \t]+test_", re.M)
JSON_BLOCK_RE = re.compile(r"```json[ \t]*\n(.*?)\n```", re.S)

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


class Stop(Exception):
    """A check ended the step. status is STOP_<REASON>, BLOCKED, JUDGE_ERROR ...; details are paths."""

    def __init__(self, status, reason="", details=None):
        super().__init__("%s %s" % (status, reason))
        self.status = status
        self.reason = reason
        self.details = list(details or [])


# ----------------------------------------------------------------------------------------- utilities

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ascii_safe(text, limit=300):
    value = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in str(text))
    return value[:limit]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def write_text_crlf(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    path.write_bytes(data)


def emit(line, code):
    print(ascii_safe(line, 2000))
    return code


def kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW)
    else:
        proc.kill()


def run_cmd(args, cwd=None, env=None, timeout=None, input_bytes=None):
    """Run a program without a shell. Returns (exit code or None on timeout, stdout bytes, stderr bytes)."""
    kwargs = {"creationflags": _NO_WINDOW} if os.name == "nt" else {}
    proc = subprocess.Popen([str(a) for a in args], cwd=None if cwd is None else str(cwd), env=env,
                            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    try:
        out, err = proc.communicate(input=input_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            out, err = b"", b""
        return None, out, err
    return proc.returncode, out, err


def git(repo, *args, check=True, input_bytes=None, timeout=GIT_TIMEOUT_S):
    cmd = ["git", "--literal-pathspecs", "-c", "core.quotepath=off", "-C", str(repo)] + [str(a) for a in args]
    code, out, err = run_cmd(cmd, input_bytes=input_bytes, timeout=timeout)
    if check and code != 0:
        raise Stop("STOP_GIT", "git_%s_exit_%s:%s" % (args[0], code,
                                                     ascii_safe(err.decode("utf-8", "replace").strip(), 160)))
    return code, out


def git_text(repo, *args):
    return git(repo, *args)[1].decode("utf-8", "replace").strip()


def git_z(repo, *args):
    return [part.decode("utf-8", "replace") for part in git(repo, *args)[1].split(b"\0") if part]


def same_path(a, b):
    return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))


def prompt_rel(task_id):
    return "docs/claude/%s-builder-prompt.md" % task_id


def runs_root(repo):
    return Path(repo) / RUNS_REL


def python_version():
    return "%d.%d.%d" % sys.version_info[:3]


# ----------------------------------------------------------------------------------- path rules (P6)

def norm_rel(path):
    return str(path).replace("\\", "/")


def is_pycache(path):
    parts = norm_rel(path).lower().split("/")
    return "__pycache__" in parts[:-1] and parts[-1].endswith(".pyc") and ".claude" not in parts


def is_protected(path, task_id=None):
    low = norm_rel(path).lower()
    parts = low.split("/")
    if any(part in PROTECTED_DIR_NAMES for part in parts):
        return True
    if parts[-1] in PROTECTED_NAMES:
        return True
    if any(low.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    if any(fnmatch.fnmatchcase(low, pattern) for pattern in PROTECTED_GLOBS):
        return True
    return bool(task_id) and low == prompt_rel(task_id).lower()


def allowed_entry_overlaps_protected(entry, task_id):
    """True when an allowed_paths entry could cover a protected path (anchored rules)."""
    if not entry.endswith("/"):
        return is_protected(entry, task_id)
    low = entry.lower()
    if any(part in PROTECTED_DIR_NAMES for part in low.rstrip("/").split("/")):
        return True
    anchored = list(PROTECTED_PREFIXES) + list(PROTECTED_GLOBS) + [prompt_rel(task_id).lower()]
    for item in anchored:
        if item.startswith(low):
            return True
        if low.startswith(item if item.endswith("/") else item + "/"):
            return True
    return False


def is_allowed(path, allowed_paths):
    rel = norm_rel(path)
    for entry in allowed_paths:
        if entry.endswith("/"):
            if rel.startswith(entry):
                return True
        elif rel == entry:
            return True
    return False


def glob_to_regex(pattern):
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.I)


def parse_authority_patterns(text):
    patterns = []
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            patterns.append(line.replace("\\", "/"))
    return patterns


# ------------------------------------------------------------------------------ dev-run block (P5)

def allowed_path_error(path):
    if not isinstance(path, str) or not path:
        return "empty"
    if "*" in path:
        return "wildcard"
    if "\\" in path:
        return "backslash"
    if ".." in path:
        return "dotdot"
    if path.startswith("/") or path.startswith("~") or re.match(r"^[A-Za-z]:", path):
        return "absolute"
    if not ALLOWED_PATH_RE.match(path):
        return "characters"
    if any(seg in ("", ".") for seg in path.rstrip("/").split("/")):
        return "segment"
    return None


def validate_block(block, task_id):
    """Return a list of error codes (empty when the block is valid)."""
    if not isinstance(block, dict):
        return ["not_object"]
    errors = []
    for key in block:
        if key not in BLOCK_KEYS:
            errors.append("unknown_key:%s" % ascii_safe(key, 40))
    for key in BLOCK_KEYS:
        if key not in block:
            errors.append("missing_key:%s" % key)
    if errors:
        return errors
    if block["task_id"] != task_id:
        errors.append("task_id_mismatch")
    if block["class"] not in ("general", "authority"):
        errors.append("class")
    if block["builder_model"] not in ("opus", "sonnet"):
        errors.append("builder_model")
    if block["builder_effort"] not in ("low", "medium", "high", "xhigh"):
        errors.append("builder_effort")
    for key, low, high in (("max_turns", 1, 300), ("builder_timeout_min", 1, 120)):
        value = block[key]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            errors.append(key)
    paths = block["allowed_paths"]
    if not isinstance(paths, list) or not paths:
        errors.append("allowed_paths")
    else:
        for path in paths:
            problem = allowed_path_error(path)
            if problem:
                errors.append("allowed_path_%s:%s" % (problem, ascii_safe(path, 80)))
            elif allowed_entry_overlaps_protected(path, task_id):
                errors.append("allowed_path_protected:%s" % path)
    tests = block["target_tests"]
    if not isinstance(tests, list) or not tests:
        errors.append("target_tests")
    else:
        for pattern in tests:
            if not isinstance(pattern, str) or not TARGET_TEST_RE.match(pattern):
                errors.append("target_test:%s" % ascii_safe(pattern, 60))
    message = block["commit_message"]
    if (not isinstance(message, str) or not message.strip() or len(message) > 200
            or any(not 32 <= ord(ch) < 127 for ch in message)):
        errors.append("commit_message")
    if block["class"] == "authority" and block["builder_model"] != "opus":
        errors.append("authority_requires_opus")
    return errors


def parse_prompt_block(text, task_id):
    """Find the single ```dev-run fence, parse it and validate it. Raises Stop on any problem."""
    count = len(BLOCK_OPEN_RE.findall(text))
    if count != 1:
        raise Stop("STOP_PREFLIGHT", "BLOCK_COUNT:%d" % count)
    match = BLOCK_RE.search(text)
    if not match:
        raise Stop("STOP_PREFLIGHT", "BLOCK_UNCLOSED")
    raw = match.group(1)
    if any(ord(ch) > 127 for ch in raw):
        raise Stop("STOP_PREFLIGHT", "BLOCK_NOT_ASCII")
    try:
        block = json.loads(raw)
    except ValueError:
        raise Stop("STOP_PREFLIGHT", "BLOCK_JSON")
    errors = validate_block(block, task_id)
    if errors:
        raise Stop("STOP_PREFLIGHT", "BLOCK_INVALID:" + errors[0], errors)
    return block


# ------------------------------------------------------------------------------------- claude CLI

def help_option_blocks(text):
    blocks, current = [], None
    for line in text.splitlines():
        if re.match(r"^ {2}-{1,2}[A-Za-z]", line):
            current = {"header": line, "text": line}
            blocks.append(current)
        elif line.strip() and not line.startswith(" "):
            current = None
        elif current is not None:
            current["text"] += "\n" + line
    return blocks


def header_names(header):
    head = re.split(r"\s{2,}", header.strip())[0]
    return re.findall(r"(?<![\w-])-{1,2}[A-Za-z][\w-]*", head)


def find_flag_block(help_text, flag):
    names = CLI_FLAG_ALIASES.get(flag, (flag,))
    for block in help_option_blocks(help_text):
        if any(name in header_names(block["header"]) for name in names):
            return block
    return None


def parse_claude_version(text):
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in match.groups()) if match else None


def probe_hidden_flag(claude_exe, flag):
    code, out, err = run_cmd([claude_exe, flag, "1", PROBE_UNKNOWN_FLAG, "-p"], timeout=CLI_TIMEOUT_S)
    text = (out + err).decode("utf-8", "replace")
    return ("unknown option '%s'" % PROBE_UNKNOWN_FLAG) in text


def check_cli_flags(help_text, claude_exe=None, prober=probe_hidden_flag):
    """Return [{flag, ok, how, value}] for every required flag (how = help | probe | missing)."""
    results = []
    for flag, value in REQUIRED_CLI_FLAGS:
        block = find_flag_block(help_text, flag)
        entry = {"flag": flag, "value": value, "ok": False, "how": "missing"}
        if block is not None:
            entry["how"] = "help"
            if value is None or re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(value), block["text"]):
                entry["ok"] = True
            else:
                entry["how"] = "value_missing"
        elif flag in HELP_HIDDEN_DOCUMENTED_FLAGS and claude_exe and prober(claude_exe, flag):
            entry.update(ok=True, how="probe")
        results.append(entry)
    return results


# ------------------------------------------------------------------------------- unittest parsing

def parse_unittest_output(text):
    text = text.replace("\r\n", "\n")
    rans = RAN_RE.findall(text)
    statuses = STATUS_RE.findall(text)
    counts = {}
    if statuses and statuses[-1][1]:
        for part in statuses[-1][1].split(","):
            key, _, value = part.strip().partition("=")
            if value.strip().isdigit():
                counts[key.strip()] = int(value)
    return {
        "ran": int(rans[-1]) if rans else None,
        "status": statuses[-1][0] if statuses else None,
        "skipped": counts.get("skipped", 0),
        "counts": counts,
        "failures": sorted({m.group(2) for m in FAIL_RE.finditer(text)}),
    }


def test_env(pycache_dir):
    env = dict(os.environ)
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPYCACHEPREFIX": str(pycache_dir)})
    return env


def run_unittest(workdir, pattern, out_base, timeout_s):
    """python -m unittest discover in workdir; bytes saved to <out_base>.out/.err; parsed from stderr."""
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="devpipe-pyc-") as pyc:
        code, out, err = run_cmd([sys.executable, "-m", "unittest", "discover", "-s", TESTS_DIR_REL, "-p", pattern],
                                 cwd=workdir, env=test_env(pyc), timeout=timeout_s)
    Path(str(out_base) + ".out").write_bytes(out)
    Path(str(out_base) + ".err").write_bytes(err)
    parsed = parse_unittest_output(err.decode("utf-8", "replace"))
    parsed.update({"pattern": pattern, "exit_code": code, "timed_out": code is None})
    return parsed


def run_schema_audit(workdir, out_base):
    out_base = Path(out_base)
    if not (Path(workdir) / SCHEMA_AUDIT_REL).is_file():
        return {"result": "MISSING"}
    with tempfile.TemporaryDirectory(prefix="devpipe-pyc-") as pyc:
        code, out, err = run_cmd([sys.executable, SCHEMA_AUDIT_REL], cwd=workdir, env=test_env(pyc),
                                 timeout=SCHEMA_TIMEOUT_S)
    Path(str(out_base) + ".out").write_bytes(out)
    Path(str(out_base) + ".err").write_bytes(err)
    status = None
    try:
        status = json.loads(out.decode("utf-8")).get("status")
    except (ValueError, AttributeError):
        status = None
    if code is None:
        return {"result": "TIMEOUT", "exit_code": None}
    return {"result": "PASS" if code == 0 and status == "PASS" else "FAIL", "exit_code": code}


def evaluate_tests(baseline, targets, full, schema, def_changes):
    """Deterministic comparison against the baseline. Returns (stop or None, reasons, new_failures)."""
    base_failures = set(baseline["failures"])
    reasons, new_failures = [], set()
    for result in targets:
        if result.get("timed_out"):
            reasons.append("TEST_TIMEOUT:%s" % result["pattern"])
            continue
        if result["ran"] is None or result["status"] is None:
            return ("STOP_TESTS_DID_NOT_RUN", "target:%s" % result["pattern"]), reasons, sorted(new_failures)
        if result["ran"] == 0:
            reasons.append("TARGET_NO_TESTS:%s" % result["pattern"])
        new_failures |= set(result["failures"]) - base_failures
    if full is not None:
        if full.get("timed_out"):
            reasons.append("TEST_TIMEOUT:full")
        elif full["ran"] is None or full["status"] is None:
            return ("STOP_TESTS_DID_NOT_RUN", "full"), reasons, sorted(new_failures)
        else:
            new_failures |= set(full["failures"]) - base_failures
            if full["ran"] < baseline["ran"]:
                reasons.append("RAN_DECREASED:%d<%d" % (full["ran"], baseline["ran"]))
            if full["skipped"] > baseline["skipped"]:
                reasons.append("SKIPPED_INCREASED:%d>%d" % (full["skipped"], baseline["skipped"]))
            unexpected = full["counts"].get("unexpected successes", 0)
            if unexpected > baseline.get("counts", {}).get("unexpected successes", 0):
                reasons.append("UNEXPECTED_SUCCESSES_INCREASED")
            expected = full["counts"].get("expected failures", 0)
            if expected > baseline.get("counts", {}).get("expected failures", 0):
                reasons.append("EXPECTED_FAILURES_INCREASED:%d>%d" % (
                    expected, baseline.get("counts", {}).get("expected failures", 0)))
            if full["status"] == "FAILED" and not full["failures"]:
                reasons.append("FAILED_WITHOUT_FAILURE_IDS")
    if baseline.get("schema") == "PASS" and (schema or {}).get("result") != "PASS":
        reasons.append("SCHEMA_FAIL")
    reasons.extend(def_changes)
    reasons = ["NEW_FAILURE:%s" % item for item in sorted(new_failures)] + reasons
    return None, reasons, sorted(new_failures)


def is_test_file(path):
    return re.match(r"^test_.*\.py$", norm_rel(path).split("/")[-1]) is not None


def test_def_changes(workdir, base, changes):
    reasons = []
    for path in sorted(set(changes["modified"] + changes["added"] + changes["deleted"] + changes["untracked"])):
        if not is_test_file(path):
            continue
        if path in changes["deleted"]:
            reasons.append("TEST_FILE_DELETED:%s" % path)
            continue
        code, before = git(workdir, "show", "%s:%s" % (base, path), check=False)
        before_count = len(TEST_DEF_RE.findall(before)) if code == 0 else 0
        after_path = Path(workdir) / path
        after_count = len(TEST_DEF_RE.findall(after_path.read_bytes())) if after_path.is_file() else 0
        if after_count < before_count:
            reasons.append("TEST_DEFS_DECREASED:%s:%d<%d" % (path, after_count, before_count))
    return reasons


# ----------------------------------------------------------------------------------- tree checks

def list_worktrees(repo):
    entries, current = [], None
    for token in git(repo, "worktree", "list", "--porcelain", "-z")[1].split(b"\0"):
        if not token:
            current = None
            continue
        key, _, value = token.decode("utf-8", "replace").partition(" ")
        if key == "worktree":
            current = {"path": value}
            entries.append(current)
        elif current is not None:
            current[key] = value if value else True
    return entries


def check_worktree_identity(run):
    """Check 1: the worktree exists, is registered on branch worktree-<id>, and HEAD == base."""
    wt = Path(run["worktree"])
    if not wt.is_dir():
        raise Stop("STOP_WORKTREE", "missing")
    entry = next((e for e in list_worktrees(run["repo"]) if same_path(e["path"], wt)), None)
    if entry is None:
        raise Stop("STOP_WORKTREE", "not_registered")
    if entry.get("branch") != "refs/heads/" + run["branch"]:
        raise Stop("STOP_WORKTREE", "branch")
    if not same_path(git_text(wt, "rev-parse", "--show-toplevel"), wt):
        raise Stop("STOP_WORKTREE", "toplevel")
    code, out = git(wt, "symbolic-ref", "-q", "HEAD", check=False)
    if code != 0 or out.decode("utf-8", "replace").strip() != "refs/heads/" + run["branch"]:
        raise Stop("STOP_WORKTREE", "branch")
    if git_text(wt, "rev-parse", "HEAD") != run["base"]:
        raise Stop("STOP_WORKTREE", "head_moved")


def check_not_blocked(wt):
    """Check 2: BLOCKED.md at the worktree root ends the run (first line is the reason)."""
    path = Path(wt) / "BLOCKED.md"
    if path.is_file():
        lines = path.read_bytes().decode("utf-8", "replace").splitlines()
        raise Stop("BLOCKED", lines[0].strip() if lines else "")


def collect_changes(wt, base):
    entries = git_z(wt, "diff", "--no-renames", "--name-status", "-z", base, "--")
    modified, deleted, added = [], [], []
    for i in range(0, len(entries) - 1, 2):
        status, path = entries[i], entries[i + 1]
        if status.startswith("D"):
            deleted.append(path)
        elif status.startswith("A"):
            added.append(path)
        else:
            modified.append(path)
    return {
        "modified": sorted(modified),
        "deleted": sorted(deleted),
        "added": sorted(added),
        "untracked": sorted(git_z(wt, "ls-files", "-z", "--others", "--exclude-standard")),
        "ignored": sorted(git_z(wt, "ls-files", "-z", "--others", "--ignored", "--exclude-standard")),
    }


def changed_paths(changes):
    return sorted(set(changes["modified"] + changes["added"] + changes["deleted"] + changes["untracked"]))


def protected_violations(changes, task_id, snapshot, wt):
    """Check 3: protected paths, including ignored and untracked files (.claude/, CLAUDE.local.md ...)."""
    violations = [p for p in changed_paths(changes) if is_protected(p, task_id)]
    for path in changes["ignored"]:
        if not is_protected(path, task_id) or is_pycache(path):
            continue
        expected = snapshot.get(path)
        if expected is None or sha256_file(Path(wt) / path) != expected:
            violations.append(path)
    return sorted(set(violations))


def scope_violations(changes, allowed_paths):
    """Check 4: tracked edits/deletes and non-ignored new files outside allowed_paths; ignored code files."""
    violations = [p for p in changed_paths(changes) if not is_allowed(p, allowed_paths)]
    for path in changes["ignored"]:
        low = path.lower()
        if low.endswith(IGNORED_CODE_SUFFIXES) or (low.endswith(".pyc") and not is_pycache(path)):
            violations.append("ignored-code:" + path)
    return violations


def secret_name_violations(changes, snapshot):
    names = changed_paths(changes) + [p for p in changes["ignored"] if p not in snapshot and not is_pycache(p)]
    return sorted(p for p in names if SECRET_NAME_RE.match(norm_rel(p).split("/")[-1]))


def eol_counts(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf


def hygiene_reasons(wt, base, changes):
    """Check 5 (retryable part): line endings kept, changed .ps1 files ASCII only."""
    reasons = []
    for path in changes["modified"]:
        target = Path(wt) / path
        if not target.is_file():
            continue
        after = target.read_bytes()
        code, before = git(wt, "cat-file", "--filters", "%s:%s" % (base, path), check=False)
        if code != 0 or b"\0" in before[:8000] or b"\0" in after[:8000]:
            continue
        before_crlf, before_lf = eol_counts(before)
        after_crlf, after_lf = eol_counts(after)
        if before_crlf and not before_lf and after_lf:
            reasons.append("EOL_CRLF_BROKEN:%s" % path)
        elif before_lf and not before_crlf and after_crlf:
            reasons.append("EOL_LF_BROKEN:%s" % path)
    for path in changes["modified"] + changes["added"] + changes["untracked"]:
        target = Path(wt) / path
        if path.lower().endswith(".ps1") and target.is_file() and any(b > 127 for b in target.read_bytes()):
            reasons.append("PS1_NOT_ASCII:%s" % path)
    return reasons


def build_patch(wt, base, changes):
    """diff.patch: tracked changes against base plus every non-ignored new file."""
    parts = [git(wt, "diff", "--no-renames", "--binary", base, "--")[1]]
    for path in changes["untracked"]:
        code, out = git(wt, "diff", "--no-index", "--binary", "--", "/dev/null", path, check=False)
        if code not in (0, 1):
            raise Stop("STOP_GIT", "diff_no_index:%s" % ascii_safe(path, 80))
        parts.append(out)
    return b"".join(parts)


def patch_lines(patch):
    added, removed = [], []
    for line in patch.decode("utf-8", "replace").splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
    return added, removed


def authority_reasons(changes, patch, authority_patterns):
    """Check 5 (class part): order markers, authority paths. Only ever raises the class."""
    reasons = []
    added, removed = patch_lines(patch)
    for line in added:
        low = line.lower()
        for marker in ORDER_MARKERS:
            if marker in low:
                reasons.append("ORDER_MARKER:%s" % marker)
        if ORDER_AUTHORITY_TRUE_RE.search(line):
            reasons.append("ORDER_AUTHORITY_TRUE")
        for marker in CHANGED_LINE_MARKERS:
            if marker in low:
                reasons.append("ADDED_LINE:%s" % marker)
    for line in removed:
        low = line.lower()
        for marker in REMOVED_LINE_MARKERS:
            if marker in low:
                reasons.append("REMOVED_LINE:%s" % marker)
    if authority_patterns is None:
        reasons.append("AUTHORITY_PATHS_MISSING")
    else:
        regexes = [glob_to_regex(p) for p in authority_patterns]
        for path in changed_paths(changes):
            if any(rx.match(norm_rel(path)) for rx in regexes):
                reasons.append("AUTHORITY_PATH:%s" % path)
    return sorted(set(reasons))


def escalate(current, reasons):
    return "authority" if current == "authority" or reasons else "general"


def diff_hash(wt, changes):
    """sha256 over sorted changed paths and their content bytes (ignored files excluded)."""
    digest = hashlib.sha256()
    for path in changed_paths(changes):
        target = Path(wt) / path
        digest.update(path.encode("utf-8") + b"\0")
        if path in changes["deleted"] or not target.is_file():
            digest.update(b"D\0")
        else:
            digest.update(b"F" + hashlib.sha256(target.read_bytes()).digest() + b"\0")
    return digest.hexdigest()


def inspect_tree(run, out_dir=None):
    """Checks 1-5 and 8 (no tests). Raises Stop for checks 1-4 and secret names; returns the findings."""
    wt = Path(run["worktree"])
    check_worktree_identity(run)
    check_not_blocked(wt)
    changes = collect_changes(wt, run["base"])
    protected = protected_violations(changes, run["id"], run.get("include_snapshot", {}), wt)
    if protected:
        raise Stop("STOP_PROTECTED", protected[0], protected)
    scope = scope_violations(changes, run["block"]["allowed_paths"])
    if scope:
        raise Stop("STOP_SCOPE", scope[0], scope)
    secrets = secret_name_violations(changes, run.get("include_snapshot", {}))
    if secrets:
        raise Stop("STOP_SECRET", secrets[0], secrets)
    if not changed_paths(changes):
        raise Stop("STOP_NO_CHANGES", "empty_diff")
    retryable = hygiene_reasons(wt, run["base"], changes)
    patch = build_patch(wt, run["base"], changes)
    class_reasons = authority_reasons(changes, patch, run.get("authority_patterns"))
    if out_dir is not None:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "diff.patch").write_bytes(patch)
        write_text_crlf(Path(out_dir) / "changed-files.txt", changed_files_text(changes))
    return {
        "changes": changes,
        "changed_paths": changed_paths(changes),
        "retryable": retryable,
        "class": escalate(run["class_initial"], class_reasons),
        "class_reasons": class_reasons,
        "diff_hash": diff_hash(wt, changes),
        "patch_sha256": sha256_bytes(patch),
    }


def changed_files_text(changes):
    lines = []
    for path in changed_paths(changes):
        if path in changes["deleted"]:
            tag = "D"
        elif path in changes["modified"]:
            tag = "M"
        else:
            tag = "A"
        lines.append("%s\t%s" % (tag, path))
    return "\n".join(lines) + "\n"


def run_test_checks(run, baseline, out_dir, changes):
    """Checks 6 and 7 inside the worktree, compared with the baseline of the same base and python."""
    wt = run["worktree"]
    targets = [run_unittest(wt, pattern, Path(out_dir) / ("target-%d" % (i + 1)), TARGET_TIMEOUT_S)
               for i, pattern in enumerate(run["block"]["target_tests"])]
    full = run_unittest(wt, FULL_SUITE_PATTERN, Path(out_dir) / "full", FULL_TIMEOUT_S)
    schema = run_schema_audit(wt, Path(out_dir) / "schema")
    defs = test_def_changes(wt, run["base"], changes)
    stop, reasons, new_failures = evaluate_tests(baseline, targets, full, schema, defs)
    summary = {
        "targets": [{k: t.get(k) for k in ("pattern", "ran", "status", "skipped", "failures", "timed_out")}
                    for t in targets],
        "full": {k: full.get(k) for k in ("ran", "status", "skipped", "counts", "failures", "timed_out")},
        "schema": schema.get("result"),
        "new_failures": new_failures,
        "reasons": reasons,
    }
    return stop, summary


# ---------------------------------------------------------------------------------------- baseline

def baseline_cache_path(repo, base):
    return runs_root(repo) / "_baseline" / ("%s-py%s.json" % (base, python_version()))


def remove_temp_worktree(repo, path):
    path = Path(path)
    if not path.name.startswith(("_base-",)) or not same_path(path.parent, Path(repo) / WORKTREES_REL):
        raise Stop("STOP_INTERNAL", "temp_worktree_path")
    registered = any(same_path(e["path"], path) for e in list_worktrees(repo))
    if registered:
        git(repo, "worktree", "remove", str(path), check=False)
    if path.exists():
        # Only the pipeline's own temporary detached checkout: delete the folder, then let git forget it.
        def _retry(func, target, _info):
            os.chmod(target, 0o700)
            func(target)
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_retry)
        else:
            shutil.rmtree(path, onerror=_retry)
    git(repo, "worktree", "prune", check=False)


def ensure_baseline(repo, base, include_snapshot):
    """Full suite + schema audit at base (temporary detached worktree), cached per base SHA and python."""
    repo = Path(repo)
    cache = baseline_cache_path(repo, base)
    if cache.is_file():
        try:
            data = read_json(cache)
            if data.get("base") == base and data.get("python") == python_version() and isinstance(data.get("ran"), int):
                data["source"] = "cache"
                return data
        except (ValueError, OSError):
            pass
    temp = repo / WORKTREES_REL / ("_base-" + base[:8])
    remove_temp_worktree(repo, temp)
    git(repo, "worktree", "add", "--detach", str(temp), base)
    try:
        for rel in include_snapshot:
            source, target = repo / rel, temp / rel
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        out_base = cache.with_suffix("")
        full = run_unittest(temp, FULL_SUITE_PATTERN, Path(str(out_base) + ".full"), FULL_TIMEOUT_S)
        schema = run_schema_audit(temp, Path(str(out_base) + ".schema"))
    finally:
        remove_temp_worktree(repo, temp)
    if full.get("timed_out"):
        raise Stop("STOP_BASELINE_TIMEOUT", "full")
    if full["ran"] is None or full["status"] is None:
        raise Stop("STOP_TESTS_DID_NOT_RUN", "baseline")
    data = {"base": base, "python": python_version(), "ran": full["ran"], "skipped": full["skipped"],
            "counts": full["counts"], "failures": full["failures"], "status": full["status"],
            "schema": schema.get("result"), "computed_utc": utc_now()}
    write_json(cache, data)
    data["source"] = "computed"
    return data


# ------------------------------------------------------------------------------------------- judge

def parse_judge_envelope(raw):
    """Parse a `claude -p --output-format json` Judge result. Returns a dict with ok / error."""
    def fail(code):
        return {"ok": False, "error": code}
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return fail("ENVELOPE_NOT_JSON")
    if not isinstance(envelope, dict):
        return fail("ENVELOPE_NOT_OBJECT")
    if envelope.get("is_error") is not False:
        return fail("ENVELOPE_IS_ERROR")
    if "subtype" in envelope and envelope.get("subtype") != "success":
        return fail("ENVELOPE_SUBTYPE:%s" % ascii_safe(envelope.get("subtype"), 40))
    text = envelope.get("result")
    if not isinstance(text, str):
        return fail("NO_RESULT_TEXT")
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return fail("EMPTY_RESULT")
    last = lines[-1].strip()
    if last == "VERDICT: PASS":
        verdict = "PASS"
    elif last == "VERDICT: FAIL":
        verdict = "FAIL"
    else:
        return fail("NO_VERDICT_LINE")
    blocks = JSON_BLOCK_RE.findall("\n".join(lines[:-1]))
    if not blocks:
        return fail("NO_JSON_BLOCK")
    try:
        data = json.loads(blocks[-1])
    except ValueError:
        return fail("JSON_BLOCK_INVALID")
    if (not isinstance(data, dict) or data.get("verdict") not in ("PASS", "FAIL")
            or not isinstance(data.get("class_ok"), bool) or not isinstance(data.get("items"), list)
            or not isinstance(data.get("min_fixes"), list)):
        return fail("JSON_BLOCK_FIELDS")
    if data["verdict"] != verdict:
        return fail("VERDICT_MISMATCH")
    if verdict == "PASS" and data["min_fixes"]:
        return fail("PASS_WITH_MIN_FIXES")
    return {"ok": True, "verdict": verdict, "class_ok": data["class_ok"], "items": data["items"],
            "min_fixes": data["min_fixes"], "result_text": text}


def builder_envelope_summary(path):
    """Informational only (the Builder's own report never decides anything)."""
    try:
        envelope = json.loads(Path(path).read_bytes().decode("utf-8"))
        return {k: envelope.get(k) for k in ("is_error", "subtype", "num_turns", "total_cost_usd", "session_id")}
    except (OSError, ValueError, UnicodeDecodeError, AttributeError):
        return {"missing_or_invalid": True}


def safe_worktree_folder(wt, task_id):
    """The run folder inside the worktree (git-ignored). Refuse links so writes never leave the worktree."""
    folder = Path(wt)
    for part in RUNS_REL.split("/") + [task_id]:
        folder = folder / part
        if folder.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(folder)):
            raise Stop("STOP_PROTECTED", "link_in_run_folder")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_into(folder, name, data):
    target = Path(folder) / name
    if target.is_symlink():
        raise Stop("STOP_PROTECTED", "link_in_run_folder")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


# ---------------------------------------------------------------------------------------- commands

def load_run(run_dir):
    return read_json(Path(run_dir) / "run.json")


def include_candidates(repo, base):
    names = {".claude/settings.local.json"}
    code, data = git(repo, "show", "%s:.worktreeinclude" % base, check=False)
    if code == 0:
        for raw in data.decode("utf-8", "replace").splitlines():
            line = raw.strip()
            if line and not line.startswith(("#", "!")) and not any(c in line for c in "*?["):
                names.add(line.lstrip("/"))
    return sorted(names)


def include_snapshot(repo, base):
    """sha256 of the git-ignored files Claude Code copies into a new worktree, taken before the Builder."""
    snapshot = {}
    for rel in include_candidates(repo, base):
        source = Path(repo) / rel
        if source.is_file():
            snapshot[rel] = sha256_file(source)
    return snapshot


def is_main_checkout(repo):
    git_dir = git_text(repo, "rev-parse", "--absolute-git-dir")
    common = git_text(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return same_path(git_dir, common) and same_path(git_text(repo, "rev-parse", "--show-toplevel"), repo)


def main_branch(repo):
    code, out = git(repo, "symbolic-ref", "-q", "--short", "HEAD", check=False)
    return out.decode("utf-8", "replace").strip() if code == 0 else None


def has_staged(repo):
    return git(repo, "diff", "--cached", "--quiet", check=False)[0] != 0


def prompt_committed(repo, task_id):
    rel = prompt_rel(task_id)
    if git(repo, "cat-file", "-e", "HEAD:%s" % rel, check=False)[0] != 0:
        return False, "PROMPT_NOT_COMMITTED"
    if git(repo, "diff", "--quiet", "HEAD", "--", rel, check=False)[0] != 0:
        return False, "PROMPT_DIFFERS_FROM_HEAD"
    return True, ""


def id_in_use(repo, task_id):
    repo = Path(repo)
    if (runs_root(repo) / task_id).exists():
        return "ID_USED_RUN_FOLDER"
    wt = repo / WORKTREES_REL / task_id
    if wt.exists() or any(same_path(e["path"], wt) for e in list_worktrees(repo)):
        return "ID_USED_WORKTREE"
    if git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/worktree-%s" % task_id, check=False)[0] == 0:
        return "ID_USED_BRANCH"
    return None


def write_latest(repo, payload):
    write_json(runs_root(repo) / "LATEST.json", payload)


def cmd_preflight(args):
    repo = Path(args.repo).resolve()
    task_id = args.id
    valid_id = bool(ID_RE.match(task_id))
    shown_id = task_id if valid_id else ascii_safe(task_id, 60)
    report = {"id": shown_id, "utc": utc_now(), "mode": args.mode, "checks": [], "first_failure": None,
              "python": python_version(), "python_exe": sys.executable}

    def add(name, ok, detail="", reason=None):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok and report["first_failure"] is None:
            report["first_failure"] = reason or name

    add("ID_FORMAT", valid_id, reason="ID_FORMAT")
    git_ok = False
    try:
        main_ok = is_main_checkout(repo)
        git_ok = True
        add("MAIN_CHECKOUT", main_ok, reason="NOT_MAIN_CHECKOUT")
        branch = main_branch(repo)
        report["main_branch"] = branch
        add("MAIN_BRANCH", branch is not None, reason="MAIN_DETACHED")
    except Stop as exc:
        add("GIT", False, exc.reason, reason="GIT_NOT_RUNNABLE")

    claude_exe = shutil.which("claude")
    report["claude_exe"] = claude_exe
    flag_results = []
    if not claude_exe:
        add("CLAUDE_FOUND", False, reason="CLAUDE_NOT_FOUND")
    else:
        add("CLAUDE_FOUND", True)
        code, out, err = run_cmd([claude_exe, "--version"], timeout=CLI_TIMEOUT_S)
        version_text = (out + err).decode("utf-8", "replace").strip()
        version = parse_claude_version(version_text)
        report["claude_version"] = ".".join(map(str, version)) if version else ascii_safe(version_text, 60)
        add("CLAUDE_VERSION", version is not None and version >= MIN_CLAUDE_VERSION,
            "min=%s" % ".".join(map(str, MIN_CLAUDE_VERSION)),
            reason="CLAUDE_VERSION_LOW:%s" % report["claude_version"])
        code, out, err = run_cmd([claude_exe, "--help"], timeout=CLI_TIMEOUT_S)
        help_text = (out + err).decode("utf-8", "replace")
        flag_results = check_cli_flags(help_text, claude_exe)
        for entry in flag_results:
            reason = ("CLI_VALUE_MISSING:%s=%s" % (entry["flag"], entry["value"]) if entry["how"] == "value_missing"
                      else "CLI_FLAG_MISSING:%s" % entry["flag"])
            add("CLI_FLAG:%s" % entry["flag"], entry["ok"], entry["how"], reason=reason)
    report["cli_flags"] = flag_results

    if valid_id and git_ok:
        used = id_in_use(repo, task_id)
        add("ID_UNUSED", used is None, used or "", reason=used)
        add("MAIN_NO_STAGED", not has_staged(repo), reason="MAIN_HAS_STAGED")
        committed, why = prompt_committed(repo, task_id)
        add("PROMPT_COMMITTED", committed, why, reason=why)
        if committed:
            try:
                text = git(repo, "show", "HEAD:%s" % prompt_rel(task_id))[1].decode("utf-8", "replace")
                parse_prompt_block(text, task_id)
                add("BLOCK_VALID", True)
            except Stop as exc:
                add("BLOCK_VALID", False, exc.reason, reason=exc.reason)

    ok = report["first_failure"] is None
    report["ok"] = ok
    report_path = runs_root(repo) / "_preflight" / ("%s.json" % (task_id if valid_id else "_invalid-id"))
    write_json(report_path, report)
    flags_ok = sum(1 for e in flag_results if e["ok"])
    tail = "claude=%s flags=%d/%d report=%s" % (report.get("claude_version", "none"), flags_ok,
                                                len(REQUIRED_CLI_FLAGS), report_path.relative_to(repo).as_posix())
    if ok:
        return emit("DEV-RUN %s PREFLIGHT_OK %s" % (shown_id, tail), 0)
    line = "DEV-RUN %s STOP_PREFLIGHT reason=%s %s" % (shown_id, report["first_failure"], tail)
    if args.mode == "run" and valid_id:
        write_latest(repo, {"id": task_id, "status": "STOP_PREFLIGHT", "reasons": [report["first_failure"]],
                            "utc": utc_now(), "line": ascii_safe(line, 2000)})
    return emit(line, 2)


def cmd_init_run(args):
    repo = Path(args.repo).resolve()
    task_id = args.id
    if not ID_RE.match(task_id):
        raise Stop("STOP_PREFLIGHT", "ID_FORMAT")
    used = id_in_use(repo, task_id)
    if used:
        raise Stop("STOP_PREFLIGHT", used)
    base = git_text(repo, "rev-parse", "HEAD")
    code, raw = git(repo, "show", "%s:%s" % (base, prompt_rel(task_id)), check=False)
    if code != 0:
        raise Stop("STOP_PREFLIGHT", "PROMPT_NOT_COMMITTED")
    block = parse_prompt_block(raw.decode("utf-8", "replace"), task_id)
    code, authority_raw = git(repo, "show", "%s:%s" % (base, AUTHORITY_PATHS_REL), check=False)
    run = {
        "id": task_id,
        "repo": str(repo),
        "base": base,
        "main_branch": main_branch(repo),
        "worktree": str(repo / WORKTREES_REL / task_id),
        "branch": "worktree-%s" % task_id,
        "prompt_path": prompt_rel(task_id),
        "prompt_sha256": sha256_bytes(raw),
        "block": block,
        "class_initial": block["class"],
        "python": python_version(),
        "python_exe": sys.executable,
        "claude_exe": shutil.which("claude"),
        "started_utc": utc_now(),
        "include_snapshot": include_snapshot(repo, base),
        "authority_patterns": parse_authority_patterns(authority_raw.decode("utf-8", "replace")) if code == 0 else None,
    }
    if run["main_branch"] is None:
        raise Stop("STOP_PREFLIGHT", "MAIN_DETACHED")
    write_json(runs_root(repo) / task_id / "run.json", run)
    return emit("INIT OK base=%s model=%s effort=%s turns=%d timeout=%d class=%s" % (
        base[:8], block["builder_model"], block["builder_effort"], block["max_turns"],
        block["builder_timeout_min"], block["class"]), 0)


def cmd_baseline(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    data = ensure_baseline(run["repo"], run["base"], run["include_snapshot"])
    write_json(run_dir / "baseline.json", data)
    return emit("BASELINE OK source=%s ran=%d failures=%d skipped=%d schema=%s" % (
        data["source"], data["ran"], len(data["failures"]), data["skipped"], data["schema"]), 0)


def refresh_include_snapshot(run_dir):
    """Re-measure the main copies right before Builder attempt 1 (same path list, exact sha256 only).

    init-run's value is kept as include_snapshot_init for the record; the fix pass reuses this snapshot
    because its worktree copies were made when attempt 1 created the worktree.
    """
    run_dir = Path(run_dir)
    run = load_run(run_dir)
    run.setdefault("include_snapshot_init", run["include_snapshot"])
    run["include_snapshot"] = include_snapshot(run["repo"], run["base"])
    run["include_snapshot_utc"] = utc_now()
    write_json(run_dir / "run.json", run)
    return run


def cmd_snapshot_includes(args):
    run = refresh_include_snapshot(args.run_dir)
    return emit("SNAPSHOT OK files=%d" % len(run["include_snapshot"]), 0)


def run_checks(run, run_dir, attempt, baseline, with_tests=True):
    run_dir = Path(run_dir)
    out_dir = run_dir / ("attempt-%d" % attempt)
    result = {"attempt": attempt, "utc": utc_now(), "status": None, "reasons": [], "details": [],
              "class": run["class_initial"], "class_reasons": [],
              "builder": builder_envelope_summary(run_dir / ("builder-%d.json" % attempt))}
    try:
        tree = inspect_tree(run, out_dir)
        result.update({"changed_paths": tree["changed_paths"], "changes": tree["changes"],
                       "class": tree["class"], "class_reasons": tree["class_reasons"],
                       "diff_hash": tree["diff_hash"], "patch_sha256": tree["patch_sha256"]})
        result["reasons"].extend(tree["retryable"])
        if with_tests:
            stop, tests = run_test_checks(run, baseline, out_dir, tree["changes"])
            result["tests"] = tests
            result["baseline"] = {k: baseline.get(k) for k in ("ran", "skipped", "schema", "source")}
            result["baseline"]["failure_count"] = len(baseline["failures"])
            if stop:
                raise Stop(stop[0], stop[1])
            result["reasons"].extend(tests["reasons"])
        result["status"] = "RETRYABLE" if result["reasons"] else "OK"
    except Stop as exc:
        result["status"] = exc.status
        result["reasons"].append(exc.reason)
        result["details"] = exc.details
    write_json(run_dir / ("checks-%d.json" % attempt), result)
    return result


def cmd_check(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    baseline = read_json(run_dir / "baseline.json")
    result = run_checks(run, run_dir, args.attempt, baseline)
    status = result["status"]
    first = result["reasons"][0] if result["reasons"] else ""
    nf = len(result.get("tests", {}).get("new_failures", []))
    line = "CHECK %s attempt=%d class=%s new_failures=%d reason=%s" % (status, args.attempt, result["class"], nf, first)
    return emit(line, 0 if status == "OK" else (1 if status == "RETRYABLE" else 2))


def base_blob(run, rel):
    code, data = git(run["repo"], "show", "%s:%s" % (run["base"], rel), check=False)
    if code != 0:
        raise Stop("STOP_PREFLIGHT", "BASE_FILE_MISSING:%s" % rel)
    return data


def cmd_judge_prep(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    checks = read_json(run_dir / ("checks-%d.json" % args.attempt))
    if checks.get("status") != "OK":
        raise Stop("STOP_INTERNAL", "checks_not_ok")
    # Re-check 1-3 right before the Judge: the worktree's .claude and CLAUDE files must equal the base.
    tree = inspect_tree(run)
    if tree["diff_hash"] != checks["diff_hash"]:
        raise Stop("STOP_WORKTREE", "tree_changed_before_judge")
    attempt_dir = run_dir / ("attempt-%d" % args.attempt)
    files = {
        "judge-prompt.md": base_blob(run, JUDGE_PROMPT_REL),
        "task-prompt.md": base_blob(run, run["prompt_path"]),
        "diff.patch": (attempt_dir / "diff.patch").read_bytes(),
        "changed-files.txt": (attempt_dir / "changed-files.txt").read_bytes(),
        "checks.json": (run_dir / ("checks-%d.json" % args.attempt)).read_bytes(),
    }
    main_copy = run_dir / ("judge-%d" % args.attempt)
    wt_copy = safe_worktree_folder(run["worktree"], run["id"])
    for name, data in files.items():
        write_into(main_copy, name, data)
        write_into(wt_copy, name, data)
    return emit("JUDGE_PREP OK attempt=%d files=%d" % (args.attempt, len(files)), 0)


def cmd_parse_judge(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    envelope_path = run_dir / ("judge-%d.json" % args.attempt)
    raw = envelope_path.read_bytes() if envelope_path.is_file() else b""
    parsed = parse_judge_envelope(raw)
    parsed["envelope_sha256"] = sha256_bytes(raw)
    parsed["envelope_file"] = envelope_path.name
    checks = read_json(run_dir / ("checks-%d.json" % args.attempt))
    try:
        tree = inspect_tree(run)
        if tree["diff_hash"] != checks["diff_hash"]:
            raise Stop("STOP_WORKTREE", "tree_changed_during_judge")
    except Stop as exc:
        parsed.update(ok=False, error=exc.status + ":" + exc.reason, stop=exc.status)
    write_json(run_dir / ("judge-%d.parsed.json" % args.attempt), parsed)
    if parsed.get("stop"):
        return emit("JUDGE %s attempt=%d reason=%s" % (parsed["stop"], args.attempt, parsed["error"]), 2)
    if not parsed["ok"]:
        return emit("JUDGE JUDGE_ERROR attempt=%d reason=%s" % (args.attempt, parsed["error"]), 2)
    class_note = "" if parsed["class_ok"] else " class_ok=false"
    return emit("JUDGE %s attempt=%d%s" % (parsed["verdict"], args.attempt, class_note),
                0 if parsed["verdict"] == "PASS" else 1)


def cmd_fix_prep(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    attempt = args.attempt
    checks = read_json(run_dir / ("checks-%d.json" % attempt))
    parsed_path = run_dir / ("judge-%d.parsed.json" % attempt)
    min_fixes = []
    if parsed_path.is_file():
        parsed = read_json(parsed_path)
        if parsed.get("ok") and parsed.get("verdict") == "FAIL":
            min_fixes = parsed.get("min_fixes", [])
    rules = base_blob(run, BUILDER_RULES_REL).decode("utf-8", "replace")
    folder = "workspace/outputs/dev-runs/%s" % run["id"]
    new_failures = checks.get("tests", {}).get("new_failures", [])
    other = [r for r in checks.get("reasons", []) if not r.startswith("NEW_FAILURE:")]
    lines = [
        "# Fix pass %d for dev-run %s" % (attempt, run["id"]),
        "",
        "The task is defined only by %s/task-prompt.md (the prompt at base %s)." % (folder, run["base"][:8]),
        "Fix only the items listed below. Do not weaken, delete or skip assertions or tests.",
        "If a judgment is needed, write BLOCKED.md at the worktree root (first line = one-line reason) and stop.",
        "Do not commit, merge, push or switch branches.",
        "",
        "## Builder rules (tools/dev_pipeline/builder-rules.md at base)",
        "",
        rules.strip(),
        "",
        "## New test failures (ids not in the baseline)",
        "",
    ]
    lines += ["- %s" % item for item in new_failures] or ["- (none)"]
    lines += ["", "## Other check reasons", ""]
    lines += ["- %s" % item for item in other] or ["- (none)"]
    lines += ["", "## Judge min_fixes (verbatim)", ""]
    lines += ["- %s" % (item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)) for item in min_fixes] \
        or ["- (none)"]
    lines += ["", "Test output of the failed check: %s/attempt-%d/ (target-*.err, full.err, schema.out)." % (folder, attempt), ""]
    text = "\n".join(lines)
    write_text_crlf(run_dir / ("fix-%d.md" % attempt), text)
    wt_copy = safe_worktree_folder(run["worktree"], run["id"])
    write_into(wt_copy, "fix-%d.md" % attempt, (run_dir / ("fix-%d.md" % attempt)).read_bytes())
    write_into(wt_copy, "task-prompt.md", base_blob(run, run["prompt_path"]))
    attempt_dir = run_dir / ("attempt-%d" % attempt)
    for source in sorted(attempt_dir.glob("*")):
        if source.is_file() and source.suffix in (".out", ".err"):
            write_into(wt_copy / ("attempt-%d" % attempt), source.name, source.read_bytes())
    return emit("FIX_PREP OK attempt=%d new_failures=%d min_fixes=%d" % (attempt, len(new_failures), len(min_fixes)), 0)


def next_hint(task_id, status):
    if status == "READY_TO_MERGE":
        return ".\\tools\\dev-merge.ps1 %s" % task_id
    if status == "NEEDS_APPROVAL":
        return "user decision, then .\\tools\\dev-merge.ps1 %s -ApproveAuthority" % task_id
    return "see docs/claude/dev-runs/%s.md" % task_id


def summary_markdown(result, run, judge_texts, merge=None):
    tests = result.get("tests") or {}
    lines = [
        "# dev-run %s — %s" % (result["id"], result["status"]),
        "",
        "- 시각(UTC): %s → %s" % (result.get("started_utc"), result.get("finished_utc")),
        "- 기준 커밋(base): `%s` · 메인 브랜치: `%s`" % (result["base"], result.get("main_branch")),
        "- 등급(class): %s%s" % (result["class"], (" (사유: %s)" % ", ".join(result.get("class_reasons", [])))
                                if result.get("class_reasons") else ""),
        "- 상태: **%s** · 재시도: %d" % (result["status"], result.get("retries", 0)),
        "- 테스트: 기준선 Ran %s · 실패 %s → 변경 후 Ran %s · 새 실패 %d · skipped %s · 스키마 감사 %s" % (
            (tests.get("baseline") or {}).get("ran"), (tests.get("baseline") or {}).get("failure_count"),
            (tests.get("after") or {}).get("ran"), len(tests.get("new_failures") or []), tests.get("skipped"),
            tests.get("schema")),
        "- diff_hash: `%s`" % result.get("diff_hash"),
        "- Judge 파일 sha256: `%s`" % result.get("judge_file_sha256"),
        "- 사유: %s" % ("; ".join(result.get("reasons", [])) or "없음"),
        "- 다음: `%s`" % result.get("next"),
        "",
        "## 바뀐 파일",
        "",
    ]
    lines += ["- `%s`" % p for p in result.get("changed_files", [])] or ["- (없음)"]
    if tests.get("new_failures"):
        lines += ["", "## 새 실패", ""] + ["- `%s`" % f for f in tests["new_failures"]]
    for label, text in judge_texts:
        lines += ["", "## Judge 보고 원문 (%s)" % label, "", text.strip()]
    if merge:
        lines += ["", "## 병합", "", "- 병합 시각(UTC): %s" % merge.get("merged_at"),
                  "- 병합 커밋: `%s` · 방식: %s" % (merge.get("merge_sha"), merge.get("merge_mode"))]
        if merge.get("approved_at"):
            lines.append("- 사용자 승인(-ApproveAuthority): %s" % merge["approved_at"])
    lines += ["", "(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/%s/ 의 원본 기록입니다.)"
              % result["id"], ""]
    return "\n".join(lines)


def write_docs(repo, result, run, judge_texts, merge=None):
    task_id = result["id"]
    write_text_crlf(Path(repo) / DOCS_RUNS_REL / ("%s.md" % task_id), summary_markdown(result, run, judge_texts, merge))
    message = "docs(claude): dev-run %s %s" % (task_id, "merged" if merge else result["status"].lower())
    write_text_crlf(Path(repo) / PENDING_REL / ("dev-run-%s.txt" % task_id),
                    "%s\n%s/%s.md\n" % (message, DOCS_RUNS_REL, task_id))


def judge_texts_for(run_dir):
    texts = []
    for path in sorted(Path(run_dir).glob("judge-*.parsed.json")):
        try:
            parsed = read_json(path)
        except (ValueError, OSError):
            continue
        attempt = path.name.split("-")[1].split(".")[0]
        if parsed.get("result_text"):
            texts.append(("%s회차 %s" % (attempt, parsed.get("verdict")), parsed["result_text"]))
        else:
            texts.append(("%s회차 오류" % attempt, "판정을 읽지 못함: %s" % parsed.get("error")))
    return texts


def cmd_write_result(args):
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    status = args.status
    if status != "PASS" and status not in FINAL_STATUSES and not STOP_STATUS_RE.match(status):
        status = "STOP_UNKNOWN_STATUS"
    attempts = sorted(int(p.name.split("-")[1].split(".")[0]) for p in run_dir.glob("checks-*.json"))
    checks = read_json(run_dir / ("checks-%d.json" % attempts[-1])) if attempts else {}
    cls = checks.get("class", run["class_initial"])
    class_reasons = list(checks.get("class_reasons", []))
    judge_file, judge_sha, judge_verdict = None, None, "NONE"
    if attempts and (run_dir / ("judge-%d.parsed.json" % attempts[-1])).is_file():
        parsed = read_json(run_dir / ("judge-%d.parsed.json" % attempts[-1]))
        judge_verdict = parsed.get("verdict") if parsed.get("ok") else "ERROR"
        if parsed.get("ok") and parsed.get("class_ok") is False:
            cls, class_reasons = "authority", class_reasons + ["JUDGE_CLASS_OK_FALSE"]
        judge_file = parsed.get("envelope_file")
        judge_sha = parsed.get("envelope_sha256")
    if status == "PASS":
        status = "NEEDS_APPROVAL" if cls == "authority" else "READY_TO_MERGE"
    baseline = {}
    if (run_dir / "baseline.json").is_file():
        baseline = read_json(run_dir / "baseline.json")
    tests_raw = checks.get("tests") or {}
    full = tests_raw.get("full") or {}
    tests = {
        "baseline": {"ran": baseline.get("ran"), "skipped": baseline.get("skipped"),
                     "failure_count": len(baseline.get("failures", [])), "schema": baseline.get("schema"),
                     "source": baseline.get("source")} if baseline else None,
        "after": {"ran": full.get("ran"), "skipped": full.get("skipped"),
                  "failure_count": len(full.get("failures") or [])} if full else None,
        "new_failures": tests_raw.get("new_failures", []),
        "ran": "%s->%s" % (baseline.get("ran"), full.get("ran")),
        "skipped": "%s->%s" % (baseline.get("skipped"), full.get("skipped")),
        "schema": "%s->%s" % (baseline.get("schema"), tests_raw.get("schema")),
    }
    reasons = [r for r in (args.reason or []) if r] + [r for r in checks.get("reasons", []) if r]
    result = {
        "id": run["id"], "status": status, "class": cls, "class_reasons": sorted(set(class_reasons)),
        "base": run["base"], "main_branch": run["main_branch"], "worktree": run["worktree"], "branch": run["branch"],
        "diff_hash": checks.get("diff_hash") if status in ("READY_TO_MERGE", "NEEDS_APPROVAL") else None,
        "judge_file": judge_file if status in ("READY_TO_MERGE", "NEEDS_APPROVAL") else None,
        "judge_file_sha256": judge_sha if status in ("READY_TO_MERGE", "NEEDS_APPROVAL") else None,
        "judge_verdict": judge_verdict, "tests": tests, "retries": args.retries, "reasons": reasons,
        "changed_files": checks.get("changed_paths", []), "attempts": attempts,
        "builder_runs": [builder_envelope_summary(run_dir / ("builder-%d.json" % n)) for n in attempts],
        "started_utc": run["started_utc"], "finished_utc": utc_now(),
        "next": next_hint(run["id"], status),
    }
    line = "DEV-RUN %s %s judge=%s new_failures=%d ran=%s retries=%d next=%s" % (
        run["id"], status, judge_verdict, len(tests["new_failures"]), tests["ran"], args.retries, result["next"])
    result["line"] = ascii_safe(line, 2000)
    write_json(run_dir / "result.json", result)
    write_latest(run["repo"], {k: result[k] for k in ("id", "status", "class", "base", "line", "next", "finished_utc")})
    write_docs(run["repo"], result, run, judge_texts_for(run_dir))
    return emit(line, 0 if status in ("READY_TO_MERGE", "NEEDS_APPROVAL") else 1)


# ------------------------------------------------------------------------------------------- merge

def verify_for_merge(repo, run, result, run_dir):
    """Recompute every merge condition from main-checkout records. Raises Stop; returns the class."""
    repo = Path(repo)
    if main_branch(repo) != run["main_branch"]:
        raise Stop("STOP_MAIN_BRANCH", "main_branch_changed")
    if has_staged(repo):
        raise Stop("STOP_MAIN_STAGED", "main_has_staged_changes")
    judge_path = Path(run_dir) / str(result.get("judge_file") or "")
    if not result.get("judge_file") or not judge_path.is_file():
        raise Stop("STOP_JUDGE_FILE", "missing")
    raw = judge_path.read_bytes()
    if sha256_bytes(raw) != result.get("judge_file_sha256"):
        raise Stop("STOP_JUDGE_FILE", "sha256_changed")
    parsed = parse_judge_envelope(raw)
    if not parsed.get("ok") or parsed.get("verdict") != "PASS":
        raise Stop("STOP_JUDGE_FILE", "not_pass")
    prompt_raw = base_blob(run, run["prompt_path"])
    block = parse_prompt_block(prompt_raw.decode("utf-8", "replace"), run["id"])
    if block != run["block"]:
        raise Stop("STOP_PROMPT", "block_differs_from_run")
    code, authority_raw = git(repo, "show", "%s:%s" % (run["base"], AUTHORITY_PATHS_REL), check=False)
    run = dict(run, authority_patterns=parse_authority_patterns(authority_raw.decode("utf-8", "replace"))
               if code == 0 else None)
    tree = inspect_tree(run)
    if tree["retryable"]:
        raise Stop("STOP_HYGIENE", tree["retryable"][0], tree["retryable"])
    if tree["diff_hash"] != result.get("diff_hash"):
        raise Stop("STOP_DIFF_CHANGED", "diff_hash")
    cls = "authority" if result.get("class") == "authority" or tree["class"] == "authority" or not parsed["class_ok"] \
        else "general"
    return cls, tree


def merge_mode(repo, base, paths):
    head = git_text(repo, "rev-parse", "HEAD")
    if head == base:
        return "ff", head
    if git(repo, "merge-base", "--is-ancestor", base, head, check=False)[0] != 0:
        raise Stop("STOP_BASE_MOVED", "base_not_ancestor")
    between = git_z(repo, "diff", "--name-only", "-z", "--no-renames", base, head)
    if any(not p.startswith("docs/claude/") for p in between):
        raise Stop("STOP_BASE_MOVED", "non_docs_commits")
    if set(between) & set(paths):
        raise Stop("STOP_BASE_MOVED", "overlapping_paths")
    return "rebase", head


def restore_uncommitted(wt, base):
    """Undo the pipeline's own commit: HEAD back to base, changes kept in the working tree, nothing staged."""
    if git_text(wt, "rev-parse", "HEAD") != base:
        git(wt, "reset", "-q", "--soft", base)
    git(wt, "reset", "-q")


def commit_in_worktree(run, result, paths, run_dir):
    wt, base = run["worktree"], run["base"]
    git(wt, "reset", "-q")
    pathspec = Path(run_dir) / "merge-paths.nul"
    pathspec.write_bytes(b"\0".join(p.encode("utf-8") for p in paths))
    git(wt, "add", "--pathspec-from-file=%s" % pathspec, "--pathspec-file-nul")
    staged = sorted(git_z(wt, "diff", "--cached", "--name-only", "-z", "--no-renames", base))
    if staged != sorted(paths):
        git(wt, "reset", "-q")
        raise Stop("STOP_COMMIT", "staged_set_differs")
    message = "%s\n\nDev-Run: %s base=%s judge=%s\n" % (run["block"]["commit_message"], run["id"], base[:8],
                                                       str(result.get("judge_file_sha256"))[:8])
    message_path = Path(run_dir) / "commit-message.txt"
    message_path.write_bytes(message.encode("utf-8"))
    code, _ = git(wt, "commit", "-q", "-F", str(message_path), check=False)
    if code != 0:
        restore_uncommitted(wt, base)
        raise Stop("STOP_COMMIT", "git_commit_failed")
    commit = git_text(wt, "rev-parse", "HEAD")
    committed = sorted(git_z(wt, "diff", "--name-only", "-z", "--no-renames", base, commit))
    dirty = git(wt, "status", "--porcelain", "-z", "--untracked-files=all")[1]
    if git_text(wt, "rev-parse", "HEAD^") != base or committed != sorted(paths) or dirty:
        restore_uncommitted(wt, base)
        raise Stop("STOP_COMMIT", "commit_check")
    return commit


def patch_id(wt, a, b):
    diff = git(wt, "diff", "--no-renames", a, b)[1]
    out = git(wt, "patch-id", "--stable", input_bytes=diff)[1].decode("utf-8", "replace").split()
    return out[0] if out else ""


def rebase_and_retest(run, paths, commit, new_base, run_dir):
    wt, base = run["worktree"], run["base"]

    def undo():
        git(wt, "reset", "-q", "--keep", commit)
        restore_uncommitted(wt, base)

    old_id = patch_id(wt, base, commit)
    if git(wt, "rebase", "-q", new_base, check=False)[0] != 0:
        git(wt, "rebase", "--abort", check=False)
        restore_uncommitted(wt, base)
        raise Stop("STOP_BASE_MOVED", "rebase_conflict")
    rebased = git_text(wt, "rev-parse", "HEAD")
    if (git_text(wt, "rev-parse", "HEAD^") != new_base or patch_id(wt, new_base, rebased) != old_id
            or sorted(git_z(wt, "diff", "--name-only", "-z", "--no-renames", new_base, rebased)) != sorted(paths)):
        undo()
        raise Stop("STOP_BASE_MOVED", "patch_id_differs")
    baseline = ensure_baseline(run["repo"], new_base, run["include_snapshot"])
    write_json(Path(run_dir) / "merge-baseline.json", baseline)
    moved = dict(run, base=new_base)
    stop, tests = run_test_checks(moved, baseline, Path(run_dir) / "merge-tests", collect_changes(wt, new_base))
    write_json(Path(run_dir) / "merge-tests.json", tests)
    if stop or tests["reasons"]:
        undo()
        raise Stop("STOP_BASE_MOVED", "tests_after_rebase:%s" % (stop[0] if stop else tests["reasons"][0]))
    return rebased


def do_merge(repo, task_id, approve_authority):
    repo = Path(repo).resolve()
    if not ID_RE.match(task_id):
        raise Stop("STOP_ID_FORMAT", "id")
    if not is_main_checkout(repo):
        raise Stop("STOP_NOT_MAIN_CHECKOUT", "repo")
    run_dir = runs_root(repo) / task_id
    if not (run_dir / "result.json").is_file() or not (run_dir / "run.json").is_file():
        raise Stop("STOP_NO_RESULT", "result.json")
    result = read_json(run_dir / "result.json")
    run = read_json(run_dir / "run.json")
    if result.get("merged_at"):
        raise Stop("STOP_ALREADY_MERGED", result.get("merge_sha", ""))
    status = result.get("status")
    if approve_authority and status != "NEEDS_APPROVAL":
        raise Stop("STOP_APPROVAL_NOT_APPLICABLE", str(status))
    if status not in ("READY_TO_MERGE", "NEEDS_APPROVAL"):
        raise Stop("STOP_STATUS", str(status))
    cls, tree = verify_for_merge(repo, run, result, run_dir)
    paths = tree["changed_paths"]
    if (status == "NEEDS_APPROVAL" or cls == "authority") and not approve_authority:
        if status != "NEEDS_APPROVAL":
            # Recomputed class went up after the run: record it so the approval switch becomes valid.
            result["status"] = "NEEDS_APPROVAL"
            result["class"] = "authority"
            write_json(run_dir / "result.json", result)
        reasons = sorted(set(result.get("class_reasons", []) + tree["class_reasons"]))
        write_text_crlf(run_dir / "needs-approval.txt",
                        "\n".join(["changed files:"] + paths + ["authority reasons:"] + reasons) + "\n")
        return 3, "DEV-MERGE %s NEEDS_APPROVAL: user approval needed files=%s reasons=%s" % (
            task_id, ",".join(paths), ",".join(reasons) or "class=authority")
    mode, head = merge_mode(repo, run["base"], paths)
    if approve_authority:
        result["approved_at"] = utc_now()
        result["approved_via"] = "dev-merge -ApproveAuthority"
        write_json(run_dir / "result.json", result)
    first_commit = commit_in_worktree(run, result, paths, run_dir)
    commit = first_commit
    if mode == "rebase":
        commit = rebase_and_retest(run, paths, first_commit, head, run_dir)
    if git(repo, "merge", "--ff-only", "-q", run["branch"], check=False)[0] != 0 or \
            git_text(repo, "rev-parse", "HEAD") != commit:
        if git_text(repo, "rev-parse", "HEAD") != commit:
            if commit != first_commit:
                git(run["worktree"], "reset", "-q", "--keep", first_commit)
            restore_uncommitted(run["worktree"], run["base"])
        raise Stop("STOP_MERGE_FAILED", "ff_only_refused")
    merge = {"merged_at": utc_now(), "merge_sha": commit, "merge_mode": mode,
             "approved_at": result.get("approved_at")}
    result.update(merge)
    result["line"] = ascii_safe("DEV-MERGE %s MERGED sha=%s mode=%s" % (task_id, commit[:8], mode), 2000)
    write_json(run_dir / "result.json", result)
    write_latest(repo, {k: result.get(k) for k in ("id", "status", "class", "base", "line", "merged_at", "merge_sha")})
    write_docs(repo, result, run, judge_texts_for(run_dir), merge)
    return 0, result["line"]


def cmd_merge(args):
    try:
        code, line = do_merge(args.repo, args.id, args.approve_authority)
        return emit(line, code)
    except Stop as exc:
        return emit("DEV-MERGE %s %s reason=%s" % (ascii_safe(args.id, 60), exc.status, exc.reason), 2)


# ------------------------------------------------------------------------------------------- queue

def queue_take(repo):
    """Take the oldest queue file (moved to _taken so it never runs twice). Returns (code, line, task_id)."""
    repo = Path(repo)
    queue = repo / QUEUE_REL
    files = [p for p in queue.glob("*.txt") if p.is_file()] if queue.is_dir() else []
    if not files:
        return 1, "QUEUE EMPTY", None
    oldest = min(files, key=lambda p: (p.stat().st_mtime, p.name))
    task_id = oldest.stem
    try:
        first = oldest.read_bytes().decode("utf-8-sig").splitlines()
        first = first[0].strip() if first else ""
    except UnicodeDecodeError:
        first = ""
    taken = runs_root(repo) / "_taken"
    taken.mkdir(parents=True, exist_ok=True)
    os.replace(oldest, taken / ("%s-%s" % (utc_stamp(), oldest.name)))
    if not ID_RE.match(task_id) or first != task_id:
        line = "QUEUE STOP_QUEUE_INVALID file=%s" % ascii_safe(oldest.name, 80)
        write_latest(repo, {"id": ascii_safe(task_id, 60), "status": "STOP_QUEUE_INVALID", "utc": utc_now(),
                            "line": ascii_safe(line, 2000)})
        return 2, line, None
    return 0, "QUEUE TAKEN %s" % task_id, task_id


def cmd_queue_take(args):
    code, line, _ = queue_take(args.repo)
    return emit(line, code)


def cmd_prompt_committed(args):
    if not ID_RE.match(args.id):
        return emit("PROMPT STOP_ID_FORMAT", 2)
    ok, why = prompt_committed(Path(args.repo), args.id)
    return emit("PROMPT %s %s" % ("COMMITTED" if ok else "NOT_COMMITTED", why), 0 if ok else 1)


def cmd_write_latest(args):
    status = args.status if STOP_STATUS_RE.match(args.status) else "STOP_UNKNOWN_STATUS"
    task_id = args.id if ID_RE.match(args.id) else ascii_safe(args.id, 60)
    line = "DEV-RUN %s %s reason=%s" % (task_id, status, ascii_safe(args.reason or "", 200))
    write_latest(Path(args.repo), {"id": task_id, "status": status, "reasons": [args.reason or ""],
                                   "utc": utc_now(), "line": ascii_safe(line, 2000)})
    return emit(line, 0)


# -------------------------------------------------------------------------------------------- main

def build_parser():
    parser = argparse.ArgumentParser(description="Investment_V2 dev pipeline decisions (redesign T3)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight"); p.add_argument("--repo", required=True); p.add_argument("--id", required=True)
    p.add_argument("--mode", choices=("preflight", "run"), default="preflight"); p.set_defaults(func=cmd_preflight, kw="DEV-RUN")
    p = sub.add_parser("init-run"); p.add_argument("--repo", required=True); p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_init_run, kw="INIT")
    p = sub.add_parser("baseline"); p.add_argument("--run-dir", required=True); p.set_defaults(func=cmd_baseline, kw="BASELINE")
    p = sub.add_parser("snapshot-includes"); p.add_argument("--run-dir", required=True)
    p.set_defaults(func=cmd_snapshot_includes, kw="SNAPSHOT")
    for name, func, kw in (("check", cmd_check, "CHECK"), ("judge-prep", cmd_judge_prep, "JUDGE_PREP"),
                           ("parse-judge", cmd_parse_judge, "JUDGE"), ("fix-prep", cmd_fix_prep, "FIX_PREP")):
        p = sub.add_parser(name); p.add_argument("--run-dir", required=True)
        p.add_argument("--attempt", type=int, choices=(1, 2), required=True); p.set_defaults(func=func, kw=kw)
    p = sub.add_parser("write-result"); p.add_argument("--run-dir", required=True); p.add_argument("--status", required=True)
    p.add_argument("--retries", type=int, choices=(0, 1), default=0); p.add_argument("--reason", action="append")
    p.set_defaults(func=cmd_write_result, kw="DEV-RUN")
    p = sub.add_parser("merge"); p.add_argument("--repo", required=True); p.add_argument("--id", required=True)
    p.add_argument("--approve-authority", action="store_true"); p.set_defaults(func=cmd_merge, kw="DEV-MERGE")
    p = sub.add_parser("queue-take"); p.add_argument("--repo", required=True); p.set_defaults(func=cmd_queue_take, kw="QUEUE")
    p = sub.add_parser("prompt-committed"); p.add_argument("--repo", required=True); p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_prompt_committed, kw="PROMPT")
    p = sub.add_parser("write-latest"); p.add_argument("--repo", required=True); p.add_argument("--id", required=True)
    p.add_argument("--status", required=True); p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_write_latest, kw="DEV-RUN")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Stop as exc:
        return emit("%s %s reason=%s" % (args.kw, exc.status, exc.reason), 2)
    except Exception as exc:  # noqa: BLE001 - every failure must end as one line and exit 2
        traceback.print_exc()
        return emit("%s STOP_INTERNAL_ERROR type=%s" % (args.kw, type(exc).__name__), 2)


if __name__ == "__main__":
    sys.exit(main())
