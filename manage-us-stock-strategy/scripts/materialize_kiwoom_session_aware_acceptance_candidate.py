#!/usr/bin/env python3
"""Materialize a canonical inactive Kiwoom Acceptance superseding candidate."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from authority_artifact_io import canonical_json_bytes
from validation_common import file_hash, load_json, validate_instance
from validate_kiwoom_session_aware_acceptance import validate_acceptance
from validate_kiwoom_session_aware_acceptance_candidate import (
    ACTIVE_PROVIDER_SCOPE,
    CANDIDATE_EVIDENCE_STATE,
    EXPECTED_PROVIDER_SCOPE,
    REQUIRED_IMPLEMENTATION_PATHS,
    validate_candidate_acceptance,
)
from validate_skill_deployment import normalized_text_sha256


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SCHEMA_ROOT = SCRIPT_DIR.parent / "schemas"
CANONICAL_EVIDENCE_ROOT = Path("workspace/research/provider-evidence/kiwoom")
CANDIDATE_FILENAME = "session-aware-priority-acceptance-pgr-jpm-cme-v-inactive-superseding-candidate.json"
HASH_RE = re.compile(r"[a-f0-9]{64}")
COMMIT_RE = re.compile(r"[a-f0-9]{40}")


class AcceptanceCandidateMaterializationError(ValueError):
    """A deterministic candidate input, validation, or create-only failure."""


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise AcceptanceCandidateMaterializationError(f"path escapes repository: {path}") from exc


def _raw_binding(path: Path, repo_root: Path) -> dict[str, str]:
    return {
        "repository_path": _relative_to_repo(path, repo_root),
        "raw_sha256": file_hash(path).lower(),
        "hash_mode": "RAW_BYTES_SHA256",
    }


def _policy_bindings(policy: dict[str, Any]) -> set[str]:
    scopes = policy.get("provider_scopes")
    if not isinstance(scopes, list) or any(not isinstance(scope, dict) for scope in scopes):
        raise AcceptanceCandidateMaterializationError("provider scope malformed")
    return {
        str((policy.get("acceptance_evidence") or {}).get(
            "session_aware_acceptance_manifest_sha256"
        ) or "").lower(),
        *(str(scope.get("acceptance_artifact_hash") or "").lower() for scope in scopes),
    }


def build_candidate_manifest(
    *,
    active_manifest_path: Path,
    active_priority_policy_path: Path,
    provider_scope_policy_path: Path,
    source_registry_path: Path,
    repo_root: Path,
    generated_at: str,
    repository_base_commit: str,
) -> tuple[dict[str, Any], bytes, str]:
    """Build deterministic bytes after validating the current active K2 authority."""
    repo_root = repo_root.resolve()
    try:
        parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcceptanceCandidateMaterializationError("generated_at must be ISO-8601") from exc
    if parsed_generated_at.tzinfo is None:
        raise AcceptanceCandidateMaterializationError("generated_at timezone required")
    if COMMIT_RE.fullmatch(repository_base_commit) is None:
        raise AcceptanceCandidateMaterializationError("repository_base_commit must be lowercase git SHA")

    active_manifest = load_json(active_manifest_path)
    active_policy = load_json(active_priority_policy_path)
    provider_scope_policy = load_json(provider_scope_policy_path)
    source_registry = load_json(source_registry_path)
    active_errors = validate_acceptance(
        manifest=active_manifest,
        manifest_path=active_manifest_path,
        manifest_schema=SCHEMA_ROOT / "kiwoom-session-aware-acceptance-manifest.schema.json",
        priority_policy=active_policy,
        priority_schema=SCHEMA_ROOT / "kiwoom-session-aware-priority-policy.schema.json",
        source_registry=source_registry,
        source_schema=SCHEMA_ROOT / "source-capability.schema.json",
        repo_root=repo_root,
    )
    if active_errors:
        raise AcceptanceCandidateMaterializationError(
            f"current active Acceptance invalid: {active_errors}"
        )

    policy_errors = validate_instance(
        provider_scope_policy,
        SCHEMA_ROOT / "kiwoom-session-aware-priority-policy.schema.json",
    )
    if policy_errors:
        raise AcceptanceCandidateMaterializationError(
            f"provider scope policy invalid: {policy_errors}"
        )
    scopes = provider_scope_policy.get("provider_scopes") or []
    symbols = tuple(str(scope.get("ticker") or "").upper() for scope in scopes)
    if symbols != EXPECTED_PROVIDER_SCOPE:
        raise AcceptanceCandidateMaterializationError(
            f"provider scope must be exact ordered 15-symbol set: {symbols}"
        )

    active_acceptance_sha = file_hash(active_manifest_path).lower()
    if HASH_RE.fullmatch(active_acceptance_sha) is None:
        raise AcceptanceCandidateMaterializationError("active Acceptance hash invalid")
    if _policy_bindings(active_policy) != {active_acceptance_sha}:
        raise AcceptanceCandidateMaterializationError("active policy Acceptance binding split")
    if _policy_bindings(provider_scope_policy) != {active_acceptance_sha}:
        raise AcceptanceCandidateMaterializationError(
            "provider scope wrapper must retain the active Acceptance binding while inactive"
        )
    active_symbols = tuple(
        str(scope.get("ticker") or "").upper()
        for scope in active_policy.get("provider_scopes", [])
    )
    if active_symbols != ACTIVE_PROVIDER_SCOPE:
        raise AcceptanceCandidateMaterializationError("active 11-symbol provider scope changed")
    kiwoom_rows = [
        row for row in source_registry.get("providers", [])
        if isinstance(row, dict) and row.get("provider") == "kiwoom_rest"
    ]
    if len(kiwoom_rows) != 1 or str(
        kiwoom_rows[0].get("acceptance_artifact_sha256") or ""
    ).lower() != active_acceptance_sha:
        raise AcceptanceCandidateMaterializationError("source registry Acceptance binding split")

    implementation_hashes: dict[str, str] = {}
    for relative in REQUIRED_IMPLEMENTATION_PATHS:
        path = repo_root / relative
        if not path.is_file():
            raise AcceptanceCandidateMaterializationError(
                f"required implementation file missing: {relative}"
            )
        implementation_hashes[relative] = normalized_text_sha256(path).lower()

    candidate = deepcopy(active_manifest)
    candidate.update({
        "schema_version": "1.1",
        "evidence_state": CANDIDATE_EVIDENCE_STATE,
        "generated_at": generated_at,
        "repository_base_commit": repository_base_commit,
        "implementation_hashes": implementation_hashes,
        "candidate_status": "INACTIVE_SUPERSEDING_CANDIDATE",
        "supersedes_acceptance_sha256": active_acceptance_sha,
        "hash_governance": "IMPLEMENTATION_BINDINGS_NORMALIZED_TEXT_SHA256",
        "authority_bindings": {
            "provider_scope_policy": _raw_binding(provider_scope_policy_path, repo_root),
            "active_priority_policy": _raw_binding(active_priority_policy_path, repo_root),
            "source_registry": _raw_binding(source_registry_path, repo_root),
            "active_acceptance_manifest": _raw_binding(active_manifest_path, repo_root),
        },
        "provider_scope_contract": {
            "count": len(EXPECTED_PROVIDER_SCOPE),
            "symbols": list(EXPECTED_PROVIDER_SCOPE),
            "provider_scope_policy_raw_sha256": file_hash(provider_scope_policy_path).lower(),
            "order_authority": False,
        },
        "activation_performed": False,
        "quantity_authority": "none",
        "execution_quantity": None,
        "order_authority": False,
    })
    candidate_bytes = canonical_json_bytes(candidate)
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    if candidate_sha == active_acceptance_sha:
        raise AcceptanceCandidateMaterializationError(
            "candidate Acceptance ID must differ from active Acceptance ID"
        )
    return candidate, candidate_bytes, candidate_sha


def _create_only(path: Path, expected: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
        return "CREATED"
    except FileExistsError:
        if path.read_bytes() != expected:
            raise AcceptanceCandidateMaterializationError(
                f"existing candidate bytes mismatch: {path}"
            )
        return "ALREADY_PRESENT_VERIFIED"


def materialize_candidate(
    *,
    active_manifest_path: Path,
    active_priority_policy_path: Path,
    provider_scope_policy_path: Path,
    source_registry_path: Path,
    repo_root: Path,
    output_root: Path,
    generated_at: str,
    repository_base_commit: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    canonical_root = (repo_root / CANONICAL_EVIDENCE_ROOT).resolve()
    resolved_output = output_root.resolve()
    try:
        resolved_output.relative_to(canonical_root)
    except ValueError as exc:
        raise AcceptanceCandidateMaterializationError(
            "output root must remain inside canonical Kiwoom evidence root"
        ) from exc
    candidate, candidate_bytes, candidate_sha = build_candidate_manifest(
        active_manifest_path=active_manifest_path,
        active_priority_policy_path=active_priority_policy_path,
        provider_scope_policy_path=provider_scope_policy_path,
        source_registry_path=source_registry_path,
        repo_root=repo_root,
        generated_at=generated_at,
        repository_base_commit=repository_base_commit,
    )
    candidate_path = resolved_output / candidate_sha / CANDIDATE_FILENAME
    write_status = _create_only(candidate_path, candidate_bytes)
    errors = validate_candidate_acceptance(
        manifest=candidate,
        manifest_path=candidate_path,
        manifest_schema=SCHEMA_ROOT / "kiwoom-session-aware-acceptance-manifest.schema.json",
        provider_scope_policy=load_json(provider_scope_policy_path),
        provider_scope_policy_path=provider_scope_policy_path,
        priority_schema=SCHEMA_ROOT / "kiwoom-session-aware-priority-policy.schema.json",
        source_registry=load_json(source_registry_path),
        source_registry_path=source_registry_path,
        source_schema=SCHEMA_ROOT / "source-capability.schema.json",
        repo_root=repo_root,
    )
    if errors:
        raise AcceptanceCandidateMaterializationError(
            f"materialized candidate validation failed: {errors}"
        )
    return {
        "status": "PASS",
        "candidate_status": candidate["candidate_status"],
        "candidate_path": str(candidate_path),
        "candidate_raw_sha256": candidate_sha,
        "write_status": write_status,
        "supersedes_acceptance_sha256": candidate["supersedes_acceptance_sha256"],
        "provider_scope_policy_raw_sha256": candidate["provider_scope_contract"][
            "provider_scope_policy_raw_sha256"
        ],
        "provider_scope_count": candidate["provider_scope_contract"]["count"],
        "provider_scope_symbols": candidate["provider_scope_contract"]["symbols"],
        "activation_performed": False,
        "quantity_authority": "none",
        "execution_quantity": None,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-manifest", required=True, type=Path)
    parser.add_argument("--active-priority-policy", required=True, type=Path)
    parser.add_argument("--provider-scope-policy", required=True, type=Path)
    parser.add_argument("--source-registry", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--repository-base-commit", required=True)
    args = parser.parse_args()
    try:
        result = materialize_candidate(
            active_manifest_path=args.active_manifest,
            active_priority_policy_path=args.active_priority_policy,
            provider_scope_policy_path=args.provider_scope_policy,
            source_registry_path=args.source_registry,
            repo_root=args.repo_root,
            output_root=args.output_root,
            generated_at=args.generated_at,
            repository_base_commit=args.repository_base_commit,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except AcceptanceCandidateMaterializationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
