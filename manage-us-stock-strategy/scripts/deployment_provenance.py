#!/usr/bin/env python3
"""Build and validate immutable Scheduled Task deployment provenance."""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from authority_artifact_io import read_once_no_reparse
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


REGISTERED_TASK_PHASES = {
    "automation": "PRE_OPEN_T_MINUS_30",
    "post-close-portfolio-strategy": "REGULAR_CLOSE_T_PLUS_30",
}


def _read_registered_task_config(task_id: str, supplied_path: str) -> bytes:
    """Treat the supplied path only as an assertion about a registered task.

    The local Codex convention is Path.home()/.codex/automations/<id>/automation.toml.
    Neither the manifest nor runtime_repo selects the automation root. Reuse the
    existing checked-handle reader to reject reparse points and path swaps.
    """
    if task_id not in REGISTERED_TASK_PHASES:
        raise ValueError("REGISTERED_TASK_ID_NOT_RECOGNIZED")
    home = Path.home().absolute()
    expected = home / ".codex" / "automations" / task_id / "automation.toml"
    supplied = Path(supplied_path)
    if not supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError("REGISTERED_TASK_CONFIG_PATH_INVALID")
    # Path equality follows host case semantics; copies, siblings and aliases
    # must not acquire authority merely because their bytes or file IDs match.
    if supplied.absolute() != expected or supplied.resolve(strict=True) != expected:
        raise ValueError("REGISTERED_TASK_CONFIG_PATH_MISMATCH")
    return read_once_no_reparse(expected, home)


def verify_current_provenance(
    value: dict[str, Any], *, expected_head: str, runtime_repo: Path,
    provider_scope_path: Path, progress_path: Path,
    required_code_paths: tuple[str, ...] = (),
    required_policy_paths: tuple[str, ...] = (),
) -> list[str]:
    """Revalidate stored bindings against current bytes without repairing anything.

    The legacy verifier remains an artifact-only check. Callers seeking current
    deployment proof must use this function and supply their required coverage.
    """
    failures = verify_provenance(value, expected_head=expected_head, runtime_repo=runtime_repo)
    repo = runtime_repo.resolve()
    try:
        if _git(repo, "rev-parse", "HEAD") != expected_head:
            failures.append("CURRENT_HEAD_MISMATCH")
        if _git(repo, "status", "--short"):
            failures.append("CURRENT_RUNTIME_WORKTREE_DIRTY")
        if _git(repo, "branch", "--show-current") != "main":
            failures.append("CURRENT_BRANCH_NOT_MAIN")
    except (OSError, subprocess.SubprocessError):
        failures.append("CURRENT_GIT_NOT_VERIFIED")
    if value.get("order_authority") is not False:
        failures.append("ORDER_AUTHORITY_NOT_FALSE")
    for field, required in (("code_hashes", required_code_paths), ("policy_hashes", required_policy_paths)):
        hashes = value.get(field)
        if not isinstance(hashes, dict) or not hashes:
            failures.append(f"CURRENT_HASH_COVERAGE_MISSING:{field}")
            continue
        for name in required:
            if name not in hashes:
                failures.append(f"CURRENT_HASH_COVERAGE_MISSING:{name}")
        for name, expected in hashes.items():
            try:
                target = (repo / name).resolve()
                if Path(name).is_absolute() or not target.is_relative_to(repo):
                    raise ValueError("HASH_PATH_OUTSIDE_RUNTIME")
                if _sha(target) != expected:
                    failures.append(f"CURRENT_HASH_MISMATCH:{name}")
            except (OSError, TypeError, ValueError):
                failures.append(f"CURRENT_HASH_NOT_VERIFIED:{name}")
    expected_tasks = REGISTERED_TASK_PHASES
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or any(not isinstance(t, dict) for t in tasks):
        failures.append("CURRENT_TASKS_NOT_VERIFIED")
        tasks = []
    if len(tasks) != 2 or {t.get("task_id") for t in tasks} != set(expected_tasks):
        failures.append("CURRENT_TASK_ID_SET_MISMATCH")
    for task in tasks:
        task_id = task.get("task_id")
        try:
            raw = _read_registered_task_config(task_id, task["task_config_path"])
            current = tomllib.loads(raw.decode("utf-8"))
            prompt = str(current.get("prompt") or "")
            if hashlib.sha256(raw).hexdigest() != task.get("task_config_sha256"):
                failures.append(f"CURRENT_TASK_HASH_MISMATCH:{task_id}")
            if (current.get("id") != task_id or current.get("status") != "ACTIVE"
                    or current.get("rrule") != task.get("schedule")
                    or hashlib.sha256(prompt.encode("utf-8")).hexdigest() != task.get("prompt_sha256")
                    or expected_tasks.get(task_id, "UNKNOWN") not in prompt
                    or "America/New_York" not in str(current.get("rrule"))
                    or ("090000" if task_id == "automation" else "163000") not in str(current.get("rrule"))
                    or (current.get("cwds") or []) != task.get("configured_working_directories")
                    or (current.get("execution_environment") or "CODEX_APP_THREAD") != task.get("execution_environment")
                    or task.get("run_phase") != expected_tasks.get(task_id)
                    or task.get("enabled") is not True
                    or task.get("schedule_valid") is not True
                    or task.get("phase_prompt_valid") is not True):
                failures.append(f"CURRENT_TASK_BINDING_MISMATCH:{task_id}")
        except (OSError, KeyError, TypeError, ValueError):
            failures.append(f"CURRENT_TASK_NOT_VERIFIED:{task_id}")
    try:
        if _sha(provider_scope_path) != value.get("provider_scope_hash"):
            failures.append("CURRENT_PROVIDER_SCOPE_HASH_MISMATCH")
        if load_json(progress_path).get("cohort_id") != value.get("semantic_cohort_id"):
            failures.append("CURRENT_SEMANTIC_COHORT_MISMATCH")
    except (OSError, TypeError, ValueError):
        failures.append("CURRENT_POLICY_CONTEXT_NOT_VERIFIED")
    return list(dict.fromkeys(failures))
