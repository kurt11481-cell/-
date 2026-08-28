#!/usr/bin/env python3
"""Validate the Scheduled Runtime boundary without starting portfolio runtime logic."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from test_only_scheduler_control_plane import (
    artifact_hash,
    atomic_json_write,
    collect_host_clock_evidence,
    protected_hashes,
)
from validation_common import validate_instance


SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "TEST_ONLY_RUNTIME_PREFLIGHT"
ALLOWED_FAILURE_INJECTIONS = {
    "NONE",
    "INVALID_DEPLOYMENT_IDENTITY",
    "CLOSED_MARKET_SESSION",
    "PHASE_MISMATCH",
    "KIWOOM_PREFLIGHT_UNAVAILABLE",
    "CLOCK_INTEGRITY_FAILURE",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def git_value(runtime: Path, *args: str, git_executable: str = "git") -> str | None:
    result = subprocess.run(
        [git_executable, "-C", str(runtime), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else None


def prepare_config(
    *,
    config_path: Path,
    output_path: Path,
    runtime: Path,
    deployment_manifest: Path,
    calendar_evidence: Path,
    kiwoom_preflight: Path,
    expected_head: str,
    expected_tree: str,
    git_executable: Path,
    schema: Path,
    protected_paths: list[Path],
    failure_injection: str = "NONE",
) -> dict[str, Any]:
    if failure_injection not in ALLOWED_FAILURE_INJECTIONS:
        raise ValueError("UNSUPPORTED_FAILURE_INJECTION")
    value = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TEST_ONLY_RUNTIME_PREFLIGHT_CONFIG",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output_path.resolve()),
        "runtime_path": str(runtime.resolve()),
        "deployment_manifest_path": str(deployment_manifest.resolve()),
        "calendar_evidence_path": str(calendar_evidence.resolve()),
        "kiwoom_preflight_path": str(kiwoom_preflight.resolve()),
        "expected_runtime_head": expected_head,
        "expected_runtime_tree": expected_tree,
        "git_executable": str(git_executable.resolve()),
        "result_schema_path": str(schema.resolve()),
        "protected_paths": [str(path.resolve()) for path in protected_paths],
        "failure_injection": failure_injection,
        "test_only": True,
        "maturity_eligible": False,
        "production_runtime_invoked": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    value["config_hash"] = artifact_hash(value, "config_hash")
    atomic_json_write(config_path.resolve(), value)
    return value


def run_preflight(config_path: Path) -> tuple[dict[str, Any], Path]:
    config = load_json(config_path.resolve())
    if config.get("artifact_type") != "TEST_ONLY_RUNTIME_PREFLIGHT_CONFIG":
        raise ValueError("PREFLIGHT_CONFIG_TYPE_INVALID")
    if config.get("config_hash") != artifact_hash(config, "config_hash"):
        raise ValueError("PREFLIGHT_CONFIG_HASH_MISMATCH")
    if config.get("test_only") is not True or config.get("maturity_eligible") is not False:
        raise ValueError("PREFLIGHT_TEST_ONLY_FIREWALL_FAILED")

    injection = str(config["failure_injection"])
    runtime = Path(config["runtime_path"])
    before = protected_hashes(Path(value) for value in config["protected_paths"])
    clock = collect_host_clock_evidence()
    if injection == "CLOCK_INTEGRITY_FAILURE":
        clock = {**clock, "status": "CLOCK_INTEGRITY_FAILED"}

    git_executable = str(config["git_executable"])
    runtime_head = git_value(runtime, "rev-parse", "HEAD", git_executable=git_executable)
    runtime_tree = git_value(runtime, "rev-parse", "HEAD^{tree}", git_executable=git_executable)
    runtime_status = git_value(runtime, "status", "--porcelain", git_executable=git_executable)
    deployment = load_json(Path(config["deployment_manifest_path"]))
    calendar = load_json(Path(config["calendar_evidence_path"]))
    kiwoom = load_json(Path(config["kiwoom_preflight_path"]))

    deployment_ok = (
        deployment.get("status") == "DEPLOYMENT_PROVENANCE_VERIFIED"
        and deployment.get("runtime_head") == config["expected_runtime_head"]
        and runtime_head == config["expected_runtime_head"]
        and runtime_tree == config["expected_runtime_tree"]
        and runtime_status == ""
    )
    if injection == "INVALID_DEPLOYMENT_IDENTITY":
        deployment_ok = False
    calendar_ok = (
        calendar.get("official_calendar_verified") is True
        and calendar.get("is_trading_day") is True
        and calendar.get("source_url", "").startswith("https://")
    )
    if injection == "CLOSED_MARKET_SESSION":
        calendar_ok = False
    phase_ok = calendar_ok
    if injection == "PHASE_MISMATCH":
        phase_ok = False
    kiwoom_ok = (
        kiwoom.get("capability_status") == "AVAILABLE"
        and kiwoom.get("order_authority") is False
        and kiwoom.get("secrets_exposed") is False
    )
    if injection == "KIWOOM_PREFLIGHT_UNAVAILABLE":
        kiwoom_ok = False

    clock_ok = clock.get("status") == "VERIFIED"
    all_ok = deployment_ok and calendar_ok and phase_ok and kiwoom_ok and clock_ok
    after = protected_hashes(Path(value) for value in config["protected_paths"])
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all_ok else "FAIL_CLOSED",
        "failure_injection": injection,
        "deployment_provenance_status": "VERIFIED" if deployment_ok else "FAILED",
        "calendar_status": "VERIFIED" if calendar_ok else "FAILED",
        "phase_status": "TEST_ONLY_PREFLIGHT_ONLY" if phase_ok else "PHASE_MISMATCH",
        "kiwoom_readonly_preflight_status": "AVAILABLE" if kiwoom_ok else "UNAVAILABLE",
        "clock_status": "VERIFIED" if clock_ok else "FAILED",
        "runtime_head": runtime_head,
        "runtime_tree": runtime_tree,
        "runtime_clean": runtime_status == "",
        "protected_hashes_before": before,
        "protected_hashes_after": after,
        "protected_state_unchanged": before == after,
        "portfolio_effect": "NONE",
        "core_counter_effect": "NONE",
        "genuine_artifact_created": False,
        "test_only": True,
        "maturity_eligible": False,
        "production_runtime_invoked": False,
        "order_authority": False,
        "quantity_authority": "none",
        "execution_quantity": None,
    }
    result["artifact_hash"] = artifact_hash(result)
    errors = validate_instance(result, Path(config["result_schema_path"]))
    if errors:
        raise ValueError("PREFLIGHT_SCHEMA_INVALID:" + ";".join(errors))
    output_path = Path(config["output_path"])
    atomic_json_write(output_path, result)
    return result, output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--config", required=True, type=Path)
    prepare.add_argument("--output", required=True, type=Path)
    prepare.add_argument("--runtime", required=True, type=Path)
    prepare.add_argument("--deployment-manifest", required=True, type=Path)
    prepare.add_argument("--calendar-evidence", required=True, type=Path)
    prepare.add_argument("--kiwoom-preflight", required=True, type=Path)
    prepare.add_argument("--expected-head", required=True)
    prepare.add_argument("--expected-tree", required=True)
    prepare.add_argument("--git-executable", required=True, type=Path)
    prepare.add_argument("--schema", required=True, type=Path)
    prepare.add_argument("--protected-path", action="append", default=[])
    prepare.add_argument("--failure-injection", default="NONE")
    run = subparsers.add_parser("run")
    run.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "prepare":
        value = prepare_config(
            config_path=args.config,
            output_path=args.output,
            runtime=args.runtime,
            deployment_manifest=args.deployment_manifest,
            calendar_evidence=args.calendar_evidence,
            kiwoom_preflight=args.kiwoom_preflight,
            expected_head=args.expected_head,
            expected_tree=args.expected_tree,
            git_executable=args.git_executable,
            schema=args.schema,
            protected_paths=[Path(value) for value in args.protected_path],
            failure_injection=args.failure_injection,
        )
        print(json.dumps({"config": str(args.config.resolve()), "config_hash": value["config_hash"]}, indent=2))
        return 0
    try:
        result, path = run_preflight(args.config)
    except Exception as exc:
        config = load_json(args.config)
        error_path = Path(config["output_path"]).with_name("test-only-runtime-preflight-error.json")
        error = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "TEST_ONLY_RUNTIME_PREFLIGHT_ERROR",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
            "test_only": True,
            "maturity_eligible": False,
            "production_runtime_invoked": False,
            "portfolio_effect": "NONE",
            "core_counter_effect": "NONE",
            "order_authority": False,
            "quantity_authority": "none",
            "execution_quantity": None,
        }
        error["artifact_hash"] = artifact_hash(error)
        atomic_json_write(error_path, error)
        print(json.dumps({"status": "ERROR", "output": str(error_path)}, indent=2))
        return 1
    print(json.dumps({"status": result["status"], "output": str(path)}, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
