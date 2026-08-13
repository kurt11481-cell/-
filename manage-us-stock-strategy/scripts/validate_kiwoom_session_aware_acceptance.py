#!/usr/bin/env python3
"""Validate the locked evidence and authority boundary for scoped Kiwoom priority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import file_hash, load_json, validate_instance
from validate_skill_deployment import normalized_text_sha256
from validate_source_capabilities import validate_registry


def validate_acceptance(
    *, manifest: dict[str, Any], manifest_path: Path, manifest_schema: Path,
    priority_policy: dict[str, Any], priority_schema: Path,
    source_registry: dict[str, Any], source_schema: Path, repo_root: Path,
) -> list[str]:
    errors = validate_instance(manifest, manifest_schema)
    errors.extend(validate_instance(priority_policy, priority_schema))
    errors.extend(validate_registry(source_registry, source_schema))

    manifest_sha = normalized_text_sha256(manifest_path).lower()
    policy_sha = (priority_policy.get("acceptance_evidence") or {}).get(
        "session_aware_acceptance_manifest_sha256"
    )
    providers = {
        row.get("provider"): row
        for row in source_registry.get("providers", []) if isinstance(row, dict)
    }
    kiwoom = providers.get("kiwoom_rest") or {}
    if str(policy_sha or "").lower() != manifest_sha:
        errors.append("priority policy acceptance hash mismatch")
    if str(kiwoom.get("acceptance_artifact_sha256") or "").lower() != manifest_sha:
        errors.append("source registry acceptance hash mismatch")
    scopes = priority_policy.get("provider_scopes")
    if not isinstance(scopes, list) or not scopes:
        errors.append("priority policy provider scopes missing")
    else:
        seen_tickers: set[str] = set()
        for index, scope in enumerate(scopes):
            ticker = str((scope or {}).get("ticker") or "").upper()
            if not ticker:
                errors.append(f"provider scope ticker missing: {index}")
            elif ticker in seen_tickers:
                errors.append(f"duplicate provider scope ticker: {ticker}")
            seen_tickers.add(ticker)
            if str((scope or {}).get("acceptance_artifact_hash") or "").lower() != manifest_sha:
                errors.append(f"provider scope acceptance hash mismatch: {ticker or index}")
    if priority_policy.get("transition_status") != "KIWOOM_PRIMARY_GUARDED_SCOPED":
        errors.append("priority policy is not guarded scoped")
    if manifest.get("transition_outcome") != "KIWOOM_PRIMARY_GUARDED_SCOPED":
        errors.append("manifest transition outcome mismatch")
    if manifest.get("order_authority") is not False:
        errors.append("manifest order authority must be false")
    invariants = manifest.get("invariants") or {}
    if (
        invariants.get("portfolio_unchanged") is not True
        or str(invariants.get("portfolio_sha256_before")).lower()
        != str(invariants.get("portfolio_sha256_after")).lower()
    ):
        errors.append("manifest portfolio immutability failed")

    for relative, expected in (manifest.get("implementation_hashes") or {}).items():
        candidate = (repo_root / relative).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"implementation path escapes repository: {relative}")
            continue
        if not candidate.is_file():
            errors.append(f"implementation file missing: {relative}")
        elif normalized_text_sha256(candidate).lower() != str(expected).lower():
            errors.append(f"implementation hash mismatch: {relative}")

    # Source artifacts are operational evidence and may be absent in a fresh
    # clone. When present locally, every recorded hash must still match.
    for name, evidence in (manifest.get("source_artifacts") or {}).items():
        relative = str((evidence or {}).get("repository_path") or "")
        candidate = (repo_root / relative).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"source artifact path escapes repository: {name}")
            continue
        if candidate.is_file() and file_hash(candidate) != str(evidence.get("sha256") or "").lower():
            errors.append(f"source artifact hash mismatch: {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-schema", required=True, type=Path)
    parser.add_argument("--priority-policy", required=True, type=Path)
    parser.add_argument("--priority-schema", required=True, type=Path)
    parser.add_argument("--source-registry", required=True, type=Path)
    parser.add_argument("--source-schema", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_acceptance(
        manifest=load_json(args.manifest), manifest_path=args.manifest,
        manifest_schema=args.manifest_schema,
        priority_policy=load_json(args.priority_policy), priority_schema=args.priority_schema,
        source_registry=load_json(args.source_registry), source_schema=args.source_schema,
        repo_root=args.repo_root,
    )
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
