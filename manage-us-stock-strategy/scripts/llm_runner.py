"""API pilot runner (llm-runner): start each switched-on pilot once per KST slot.

Called every 10 minutes by the Windows task InvestmentV2-LLMPilots through
run_llm_pilots.ps1. The runner itself calls no API and reads no key: it only
decides which pilot slot is due and starts the pilot script as a child process
(the child inherits the parent process settings unchanged).

The switch file docs/claude/llm-pilots-schedule.json is read from the committed
version only (git show HEAD:...), never from the working tree. Any format error
rejects the whole file and no pilot runs (fail closed).

Writes only workspace/outputs/llm/runner/<KST date>.json (atomic write). The
pilot's stderr is not kept; of its stdout only the last line is kept, and only
when it is a short ASCII line starting with "llm-".

Usage: python manage-us-stock-strategy/scripts/llm_runner.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_pilot_common import (  # noqa: E402
    KST,
    REPO_ROOT,
    atomic_write_text,
    llm_dir,
)


class Job(NamedTuple):
    name: str
    times: Tuple[str, ...]
    script: str
    args: Tuple[str, ...]


# iccheck, srccheck and news times follow docs/claude/api-pilots-2026-11-06.md section 4.
# pdfcmp times are provisional (the design has none); pilot task 4 fixes them.
JOBS = (
    Job("iccheck", ("07:30",), "llm_pilot_iccheck.py", ()),
    Job("srccheck-submit", ("08:10",), "llm_pilot_srccheck.py", ("--phase", "submit")),
    Job("srccheck-collect", ("10:10",), "llm_pilot_srccheck.py", ("--phase", "collect")),
    Job("pdfcmp-submit", ("13:10",), "llm_pilot_pdfcmp.py", ("--phase", "submit")),
    Job("pdfcmp-collect", ("15:10", "17:10"), "llm_pilot_pdfcmp.py", ("--phase", "collect")),
    Job("news-submit", ("19:30",), "llm_pilot_news.py", ("--phase", "submit")),
    Job("news-collect", ("22:00", "23:00"), "llm_pilot_news.py", ("--phase", "collect")),
)
JOB_NAMES = tuple(job.name for job in JOBS)
SCHEDULE_REL = "docs/claude/llm-pilots-schedule.json"
CEO_ACCOUNT_ID = "user_01KuMGKfZu1SBYxtMmg4vAiH"
CATCH_UP_MINUTES = 60
JOB_TIMEOUT_SECONDS = 900

DAY_SCHEMA = "llm-runner-day-1"
ENTRY_KEYS = frozenset({"enabled", "approved_ref", "approved_kst"})

_REF_CARD = re.compile(r"cmsg_[0-9A-Za-z]{20,}")
_KST_STAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} KST", re.ASCII)
_LINE_OK = re.compile(r"llm-[a-z-]+ [\x20-\x7e]{1,200}")
_LINE_STATUS = re.compile(r"llm-[a-z-]+ \d{4}-\d{2}-\d{2} ([A-Z_]+)", re.ASCII)


# ---------------------------------------------------------------- switch file

def default_git_show(repo_root, rel):
    """Committed bytes of rel at HEAD, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", "HEAD:" + rel],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _approved_time(text):
    if not _KST_STAMP.fullmatch(text):
        return None
    try:
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
    except ValueError:
        return None


def load_schedule(repo_root, now, git_show):
    """Read the committed switch file. Returns (status, reason, enabled_names)."""
    raw = git_show(repo_root, SCHEDULE_REL)
    if raw is None:
        return ("SCHEDULE_MISSING", "GIT_SHOW", [])
    try:
        if not isinstance(raw, (bytes, bytearray)):
            raise ValueError("not bytes")
        obj = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ("SCHEDULE_INVALID", "NOT_JSON", [])
    if not isinstance(obj, dict):
        return ("SCHEDULE_INVALID", "NOT_OBJECT", [])
    for name in obj:
        if name not in JOB_NAMES:
            return ("SCHEDULE_INVALID", "UNKNOWN_JOB", [])
    enabled = []
    for name in JOB_NAMES:
        if name not in obj:
            continue  # a missing job counts as switched off
        entry = obj[name]
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            return ("SCHEDULE_INVALID", "BAD_ENTRY", [])
        if not isinstance(entry["enabled"], bool):
            return ("SCHEDULE_INVALID", "BAD_ENTRY", [])
        ref = entry["approved_ref"]
        stamp = entry["approved_kst"]
        if not isinstance(ref, str) or not isinstance(stamp, str):
            return ("SCHEDULE_INVALID", "BAD_ENTRY", [])
        if not entry["enabled"]:
            continue
        if not _REF_CARD.search(ref) or CEO_ACCOUNT_ID not in ref:
            return ("SCHEDULE_INVALID", "BAD_REF", [])
        approved = _approved_time(stamp)
        if approved is None or approved > now:
            return ("SCHEDULE_INVALID", "BAD_KST", [])
        enabled.append(name)
    return ("OK", None, enabled)


# ---------------------------------------------------------------- day record

def day_path(repo_root, day) -> Path:
    return llm_dir(repo_root) / "runner" / (day + ".json")


def new_day(day):
    return {
        "schema": DAY_SCHEMA,
        "day": day,
        "last_check_kst": None,
        "schedule": None,
        "runs": [],
    }


def read_day(path, day):
    """The day record, a fresh one when the file is absent, or None when it is unusable."""
    path = Path(path)
    if not path.exists():
        return new_day(day)
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    if doc.get("schema") != DAY_SCHEMA or doc.get("day") != day:
        return None
    runs = doc.get("runs")
    if not isinstance(runs, list):
        return None
    for run in runs:
        if not isinstance(run, dict):
            return None
        if not isinstance(run.get("job"), str) or not isinstance(run.get("slot"), str):
            return None
    return doc


def write_day(path, doc) -> None:
    atomic_write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------- one pilot

def default_run_job(argv, cwd, timeout):
    """Run one pilot. Returns (returncode, stdout); stderr is captured and dropped."""
    result = subprocess.run(
        argv,
        cwd=cwd,
        timeout=timeout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout


def pick_line(stdout) -> str:
    if not isinstance(stdout, str):
        return ""
    for line in reversed(stdout.splitlines()):
        if line.strip() == "":
            continue
        return line if _LINE_OK.fullmatch(line) else ""
    return ""


def status_of(line, exit_code) -> str:
    match = _LINE_STATUS.match(line)
    if match:
        return match.group(1)
    return "EXIT_%s" % (exit_code,)


def _minutes(hm) -> int:
    hour, minute = hm.split(":")
    return int(hour) * 60 + int(minute)


def _iso(moment) -> str:
    return moment.astimezone(KST).isoformat(timespec="seconds")


# ---------------------------------------------------------------- one pass

def run_once(now=None, *, repo_root=REPO_ROOT, git_show=None, run_job=None,
             python=sys.executable, dry_run=False):
    if now is None:
        now = datetime.now(KST)

        def clock():
            return datetime.now(KST)
    else:
        now = now.astimezone(KST)
        fixed = now

        def clock():
            return fixed
    repo_root = Path(repo_root)
    if git_show is None:
        git_show = default_git_show
    if run_job is None:
        run_job = default_run_job

    day = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H:%M")
    summary = {"day": day, "hm": hm, "schedule": None, "due": 0, "ran": 0, "not_built": 0}

    path = day_path(repo_root, day)
    doc = read_day(path, day)
    if doc is None:
        summary["schedule"] = "DAY_FILE_BAD"
        return 2, summary

    status, reason, enabled = load_schedule(repo_root, now, git_show)
    schedule = {"status": status, "reason": reason, "enabled": list(enabled)}
    summary["schedule"] = status
    if status != "OK":
        if not dry_run:
            doc["last_check_kst"] = _iso(now)
            doc["schedule"] = schedule
            write_day(path, doc)
        return 2, summary

    now_minutes = now.hour * 60 + now.minute
    scripts_dir = repo_root / "manage-us-stock-strategy" / "scripts"
    for job in JOBS:
        if job.name not in enabled:
            continue
        for slot in job.times:
            late = now_minutes - _minutes(slot)
            if not 0 <= late < CATCH_UP_MINUTES:
                continue
            if any(run["job"] == job.name and run["slot"] == slot for run in doc["runs"]):
                continue  # one run per slot per day, whatever its outcome; no retry
            summary["due"] += 1
            if dry_run:
                print("due %s %s" % (job.name, slot))
                continue
            script = scripts_dir / job.script
            if not script.is_file():
                stamp = _iso(clock())
                doc["runs"].append({
                    "job": job.name,
                    "slot": slot,
                    "started_kst": stamp,
                    "finished_kst": stamp,
                    "exit_code": None,
                    "status": "NOT_BUILT",
                    "line": "",
                })
                summary["not_built"] += 1
                write_day(path, doc)
                continue

            entry = {
                "job": job.name,
                "slot": slot,
                "started_kst": _iso(clock()),
                "finished_kst": None,
                "exit_code": None,
                "status": "STARTED",
                "line": None,
            }
            doc["runs"].append(entry)
            write_day(path, doc)

            argv = [python, str(script), *job.args, "--day", day]
            exit_code = None
            line = ""
            try:
                exit_code, stdout = run_job(argv, str(repo_root), JOB_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                exit_code = None
                run_status = "TIMEOUT"
            except Exception as exc:
                exit_code = None
                run_status = "LAUNCH_ERROR:" + type(exc).__name__
            else:
                line = pick_line(stdout)
                run_status = status_of(line, exit_code)
            entry["finished_kst"] = _iso(clock())
            entry["exit_code"] = exit_code
            entry["line"] = line
            entry["status"] = run_status
            summary["ran"] += 1
            write_day(path, doc)

    if not dry_run:
        doc["last_check_kst"] = _iso(now)
        doc["schedule"] = schedule
        write_day(path, doc)
    return 0, summary


# ---------------------------------------------------------------- entry point

def main(argv=None, *, now=None, repo_root=REPO_ROOT, git_show=None, run_job=None) -> int:
    parser = argparse.ArgumentParser(description="Run due Claude API pilot slots once.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print due slots only; start nothing and write nothing")
    args = parser.parse_args(argv)
    try:
        code, summary = run_once(now, repo_root=repo_root, git_show=git_show,
                                 run_job=run_job, dry_run=args.dry_run)
    except Exception as exc:
        print("llm-runner ERROR %s" % type(exc).__name__)
        return 1
    print("llm-runner %s %s schedule=%s due=%d ran=%d not_built=%d" % (
        summary["day"], summary["hm"], summary["schedule"],
        summary["due"], summary["ran"], summary["not_built"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
