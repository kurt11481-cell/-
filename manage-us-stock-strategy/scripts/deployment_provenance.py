#!/usr/bin/env python3
"""Build and validate immutable Scheduled Task deployment provenance."""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, load_json


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          text=True).stdout.strip()


def build_provenance(*, repo: Path, task_configs: list[Path], code_paths: list[Path],
                     policy_paths: list[Path], provider_scope_path: Path,
                     progress_path: Path, dependency_paths: dict[str, Path]) -> dict[str, Any]:
    head = _git(repo, "rev-parse", "HEAD")
    clean = not bool(_git(repo, "status", "--short"))
    failures: list[str] = []
    tasks: list[dict[str, Any]] = []
    expected = {
        "automation": ("PRE_OPEN_T_MINUS_30", "America/New_York", "090000"),
        "post-close-portfolio-strategy": ("REGULAR_CLOSE_T_PLUS_30", "America/New_York", "163000"),
    }
    for path in task_configs:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        task_id = str(data.get("id") or "")
        phase, timezone_name, start = expected.get(task_id, ("UNKNOWN", "", ""))
        rule = str(data.get("rrule") or "")
        prompt = str(data.get("prompt") or "")
        active = data.get("status") == "ACTIVE"
        schedule_ok = timezone_name in rule and start in rule
        phase_ok = phase in prompt
        task = {
            "task_id": task_id, "enabled": active, "run_phase": phase,
            "timezone": timezone_name, "schedule": rule,
            "configured_working_directories": data.get("cwds") or [],
            "execution_environment": data.get("execution_environment") or "CODEX_APP_THREAD",
            "actual_executable_command": "CODEX_APP_MANAGED_AGENT",
            "command_visibility": "APP_MANAGED_NOT_EXPOSED",
            "task_config_path": str(path.resolve()), "task_config_sha256": _sha(path),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "schedule_valid": schedule_ok, "phase_prompt_valid": phase_ok,
        }
        if not active: failures.append(f"TASK_NOT_ACTIVE:{task_id}")
        if not schedule_ok: failures.append(f"TASK_SCHEDULE_INVALID:{task_id}")
        if not phase_ok: failures.append(f"TASK_PHASE_PROMPT_INVALID:{task_id}")
        tasks.append(task)
    if set(expected) != {task["task_id"] for task in tasks}:
        failures.append("TASK_ID_SET_MISMATCH")
    if not clean:
        failures.append("RUNTIME_WORKTREE_DIRTY")
    missing = [name for name, path in dependency_paths.items() if not path.exists()]
    failures.extend(f"DEPENDENCY_MISSING:{name}" for name in missing)
    progress = load_json(progress_path)
    value = {
        "schema_version": "1.0",
        "status": "DEPLOYMENT_PROVENANCE_VERIFIED" if not failures else "DEPLOYMENT_PROVENANCE_NOT_VERIFIED",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "runtime_repository_path": str(repo.resolve()), "runtime_head": head,
        "runtime_clean": clean,
        "code_hashes": {str(path.relative_to(repo)).replace("\\", "/"): _sha(path) for path in code_paths},
        "policy_hashes": {str(path.relative_to(repo)).replace("\\", "/"): _sha(path) for path in policy_paths},
        "provider_scope_hash": _sha(provider_scope_path),
        "semantic_cohort_id": str(progress["cohort_id"]), "tasks": tasks,
        "dependency_paths": {name: {"path": str(path), "exists": path.exists()} for name, path in dependency_paths.items()},
        "failure_reasons": failures, "counting_enabled": not failures,
        "order_authority": False,
    }
    value["record_hash"] = canonical_hash(value)
    return value


def verify_provenance(value: dict[str, Any], *, expected_head: str, runtime_repo: Path) -> list[str]:
    failures = list(value.get("failure_reasons") or [])
    if value.get("status") != "DEPLOYMENT_PROVENANCE_VERIFIED": failures.append("STATUS_NOT_VERIFIED")
    if value.get("runtime_head") != expected_head: failures.append("RUNTIME_HEAD_MISMATCH")
    if Path(str(value.get("runtime_repository_path"))).resolve() != runtime_repo.resolve():
        failures.append("RUNTIME_PATH_MISMATCH")
    if value.get("runtime_clean") is not True: failures.append("RUNTIME_WORKTREE_DIRTY")
    if value.get("counting_enabled") is not True: failures.append("COUNTING_DISABLED")
    payload = {key: item for key, item in value.items() if key != "record_hash"}
    if canonical_hash(payload) != value.get("record_hash"): failures.append("RECORD_HASH_INVALID")
    return list(dict.fromkeys(failures))
