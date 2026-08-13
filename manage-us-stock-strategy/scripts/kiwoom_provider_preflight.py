#!/usr/bin/env python3
"""Run a sanitized health preflight for the external Kiwoom read-only runtime."""

from __future__ import annotations

import argparse
import ipaddress
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kiwoom_runtime_bridge import invoke_bridge
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from provider_resilience import update_provider_health
from validation_common import load_json, validate_instance


def _git_commit(runtime: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(runtime), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True, encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _git_remote(runtime: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(runtime), "remote", "get-url", "origin"], check=True,
            capture_output=True, text=True, encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _public_ip_status(url: str, timeout_seconds: int, opener: Callable[..., Any] = urllib.request.urlopen) -> str:
    try:
        with opener(url, timeout=timeout_seconds) as response:
            value = response.read(128).decode("ascii", errors="strict").strip()
        ipaddress.ip_address(value)
        return "RESOLVED_NOT_REPORTED"
    except Exception:
        return "UNAVAILABLE"


def run_preflight(
    *, runtime: Path, readonly_policy: dict[str, Any], rate_policy: dict[str, Any],
    generated_at: str, bridge_call: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ip_checker: Callable[[], str] | None = None,
) -> dict[str, Any]:
    expected_commit = str(readonly_policy["official_runtime_commit"])
    expected_remote = str(readonly_policy["official_runtime_remote"])
    commit = _git_commit(runtime)
    remote = _git_remote(runtime)
    runtime_status = "VERIFIED" if commit == expected_commit else "MISMATCH" if commit else "UNAVAILABLE"
    remote_status = "VERIFIED" if remote == expected_remote else "MISMATCH" if remote else "UNAVAILABLE"
    python_path = runtime / str(rate_policy["external_python_relative_path"])
    env_status = "PRESENT_NOT_READ" if (runtime / ".env").is_file() else "NOT_FOUND"
    if bridge_call is None:
        bridge_call = lambda request: invoke_bridge(request, runtime=runtime, policy=rate_policy)
    auth = bridge_call({"operation": "oauth_health", "fx_applied": False}) if runtime_status == "VERIFIED" and python_path.is_file() else {
        "bridge_status": "RUNTIME_PYTHON_UNAVAILABLE", "failure_type": "EMPTY_RESPONSE", "order_authority": False,
    }
    auth_status = "AUTHENTICATED" if auth.get("bridge_status") == "PASS" and auth.get("authenticated") is True else "ACCESS_DENIED"
    if ip_checker is None:
        ip_checker = lambda: _public_ip_status(
            str(readonly_policy["egress_ip_preflight_url"]),
            int(rate_policy["request_timeout_seconds"]),
        )
    egress_status = ip_checker()
    success = runtime_status == "VERIFIED" and remote_status == "VERIFIED" and auth_status == "AUTHENTICATED" and egress_status.startswith("RESOLVED")
    failure_type = str(auth.get("failure_type") or "EMPTY_RESPONSE")
    if failure_type not in {"HTTP_429", "TIMEOUT", "EMPTY_RESPONSE", "SCHEMA_MISMATCH", "AUTHENTICATION_FAILURE"}:
        failure_type = "EMPTY_RESPONSE"
    health = update_provider_health(None, "SUCCESS" if success else failure_type, generated_at)
    return {
        "schema_version": "1.0",
        "provider": "KIWOOM_REST",
        "provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
        "generated_at": generated_at,
        "official_runtime_path_status": "VERIFIED" if runtime.is_dir() else "UNAVAILABLE",
        "official_runtime_commit": commit,
        "expected_runtime_commit": expected_commit,
        "runtime_commit_status": runtime_status,
        "official_runtime_remote": remote,
        "expected_runtime_remote": expected_remote,
        "runtime_remote_status": remote_status,
        "runtime_python_status": "VERIFIED" if python_path.is_file() else "UNAVAILABLE",
        "credential_file_status": env_status,
        "oauth_status": auth_status,
        "egress_ip_status": egress_status,
        "capability_status": "AVAILABLE" if success else "UNAVAILABLE",
        "provider_health": health,
        "secrets_exposed": False,
        "operational_shadow_session_increment": 0,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--readonly-policy", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    validate_shadow_output_path(args.output, args.repo_root, [args.readonly_policy, args.rate_policy, args.schema])
    result = run_preflight(
        runtime=args.runtime, readonly_policy=load_json(args.readonly_policy),
        rate_policy=load_json(args.rate_policy), generated_at=args.generated_at,
    )
    errors = validate_instance(result, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, result)
    return 0 if result["capability_status"] == "AVAILABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
