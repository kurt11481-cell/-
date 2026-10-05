#!/usr/bin/env python3
"""Materialize a canonical inactive schema 1.2 Kiwoom Acceptance superseding candidate.

The active Acceptance is found through the active priority policy binding, the
symbol scope is read from that policy, and the pin list comes from the pinned
pin-scope asset. The active Acceptance may be superseded only when every one
of its validation errors is implementation drift on a path the pin scope
explicitly allows for that exact predecessor; anything else fails closed.
"""

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
from validation_common import load_json, validate_instance
from validate_kiwoom_session_aware_acceptance import validate_acceptance
from validate_kiwoom_session_aware_acceptance_candidate import (
    CANDIDATE_EVIDENCE_STATE,
    PIN_SCOPE_RELATIVE_PATH,
    V12_HASH_GOVERNANCE,
    V12_HASH_MODE,
    V12_SCHEMA_VERSION,
    allowed_drift_for,
    confined_repo_path,
    disallowed_predecessor_errors,
    load_pin_scope,
    normalized_sha256,
    ordered_policy_symbols,
    predecessor_implementation_drift,
    validate_candidate_acceptance,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SCHEMA_ROOT = SCRIPT_DIR.parent / "schemas"
CANONICAL_EVIDENCE_ROOT = Path("workspace/research/provider-evidence/kiwoom")
CANDIDATE_FILENAME = "session-aware-priority-acceptance-inactive-superseding-candidate.json"
HASH_RE = re.compile(r"[a-f0-9]{64}")
COMMIT_RE = re.compile(r"[a-f0-9]{40}")
LEGACY_CANDIDATE_KEYS = ("authority_bindings", "provider_scope_contract")


class AcceptanceCandidateMaterializationError(ValueError):
    """A deterministic candidate input, validation, or create-only failure."""


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise AcceptanceCandidateMaterializationError(f"path escapes repository: {path}") from exc


def _normalized_binding(path: Path, repo_root: Path) -> dict[str, str]:
    return {
        "repository_path": _relative_to_repo(path, repo_root),
        "sha256": normalized_sha256(path),
    }


def policy_acceptance_binding(policy: dict[str, Any]) -> str:
    """The single Acceptance ID a priority policy points to; a split binding fails."""
    scopes = policy.get("provider_scopes")
    if not isinstance(scopes, list) or not scopes or any(not isinstance(scope, dict) for scope in scopes):
        raise AcceptanceCandidateMaterializationError("provider scope malformed")
    values = {
        str((policy.get("acceptance_evidence") or {}).get(
            "session_aware_acceptance_manifest_sha256"
        ) or "").lower(),
        *(str(scope.get("acceptance_artifact_hash") or "").lower() for scope in scopes),
    }
    if len(values) != 1:
        raise AcceptanceCandidateMaterializationError("active policy Acceptance binding split")
    binding = next(iter(values))
    if HASH_RE.fullmatch(binding) is None:
        raise AcceptanceCandidateMaterializationError("active Acceptance hash invalid")
    return binding


def resolve_active_manifest(binding: str, evidence_root: Path) -> Path:
    """Find exactly one evidence file whose normalized hash is the bound Acceptance ID."""
    matches = []
    for path in sorted(evidence_root.rglob("*.json")):
        try:
            if normalized_sha256(path) == binding:
                matches.append(path)
        except (OSError, UnicodeError):
            continue
    if len(matches) != 1:
        raise AcceptanceCandidateMaterializationError(
            f"active Acceptance binding must resolve to exactly one manifest: {len(matches)}"
        )
    return matches[0]


def build_candidate_manifest(
    *,
    active_priority_policy_path: Path,
    provider_scope_policy_path: Path,
    source_registry_path: Path,
    repo_root: Path,
    generated_at: str,
    repository_base_commit: str,
    pin_scope_path: Path | None = None,
    evidence_root: Path | None = None,
) -> tuple[dict[str, Any], bytes, str]:
    """Build deterministic bytes after validating the active authority modulo allowed drift."""
    repo_root = repo_root.resolve()
    try:
        parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcceptanceCandidateMaterializationError("generated_at must be ISO-8601") from exc
    if parsed_generated_at.tzinfo is None:
        raise AcceptanceCandidateMaterializationError("generated_at timezone required")
    if COMMIT_RE.fullmatch(repository_base_commit) is None:
        raise AcceptanceCandidateMaterializationError("repository_base_commit must be lowercase git SHA")

    pin_path = (pin_scope_path or repo_root / PIN_SCOPE_RELATIVE_PATH).resolve()
    pin_scope, pin_errors = load_pin_scope(pin_path, repo_root)
    if pin_scope is None:
        raise AcceptanceCandidateMaterializationError(f"pin scope invalid: {pin_errors}")

    active_policy = load_json(active_priority_policy_path)
    provider_scope_policy = load_json(provider_scope_policy_path)
    source_registry = load_json(source_registry_path)
    for label, policy in (("active priority", active_policy), ("provider scope", provider_scope_policy)):
        policy_errors = validate_instance(
            policy, SCHEMA_ROOT / "kiwoom-session-aware-priority-policy.schema.json",
        )
        if policy_errors:
            raise AcceptanceCandidateMaterializationError(f"{label} policy invalid: {policy_errors}")

    active_acceptance_sha = policy_acceptance_binding(active_policy)
    if policy_acceptance_binding(provider_scope_policy) != active_acceptance_sha:
        raise AcceptanceCandidateMaterializationError(
            "provider scope wrapper must retain the active Acceptance binding while inactive"
        )
    kiwoom_rows = [
        row for row in source_registry.get("providers", [])
        if isinstance(row, dict) and row.get("provider") == "kiwoom_rest"
    ]
    if len(kiwoom_rows) != 1 or str(
        kiwoom_rows[0].get("acceptance_artifact_sha256") or ""
    ).lower() != active_acceptance_sha:
        raise AcceptanceCandidateMaterializationError("source registry Acceptance binding split")
    allowed_drift = allowed_drift_for(pin_scope, active_acceptance_sha)

    active_symbols = ordered_policy_symbols(active_policy)
    candidate_symbols = ordered_policy_symbols(provider_scope_policy)
    if not active_symbols or len(set(active_symbols)) != len(active_symbols) or not all(active_symbols):
        raise AcceptanceCandidateMaterializationError("active provider scope malformed")
    if candidate_symbols != active_symbols:
        raise AcceptanceCandidateMaterializationError(
            f"provider scope must equal the active ordered scope: {candidate_symbols}"
        )

    active_manifest_path = resolve_active_manifest(
        active_acceptance_sha, (evidence_root or repo_root / CANONICAL_EVIDENCE_ROOT).resolve(),
    )
    active_manifest = load_json(active_manifest_path)
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
    blocking = disallowed_predecessor_errors(active_errors, allowed_drift)
    if blocking:
        raise AcceptanceCandidateMaterializationError(
            f"current active Acceptance invalid beyond allowed drift: {blocking}"
        )
    drift, drift_errors = predecessor_implementation_drift(active_manifest, repo_root)
    if drift_errors:
        raise AcceptanceCandidateMaterializationError(f"predecessor implementation invalid: {drift_errors}")

    implementation_hashes: dict[str, str] = {}
    for relative in pin_scope["required_implementation_paths"]:
        path = confined_repo_path(relative, repo_root)
        if path is None or not path.is_file():
            raise AcceptanceCandidateMaterializationError(
                f"required implementation file missing: {relative}"
            )
        implementation_hashes[relative] = normalized_sha256(path)

    candidate = deepcopy(active_manifest)
    for legacy in LEGACY_CANDIDATE_KEYS:
        candidate.pop(legacy, None)
    candidate.update({
        "schema_version": V12_SCHEMA_VERSION,
        "evidence_state": CANDIDATE_EVIDENCE_STATE,
        "generated_at": generated_at,
        "repository_base_commit": repository_base_commit,
        "implementation_hashes": implementation_hashes,
        "candidate_status": "INACTIVE_SUPERSEDING_CANDIDATE",
        "supersedes_acceptance_sha256": active_acceptance_sha,
        "hash_governance": V12_HASH_GOVERNANCE,
        "candidate_governance": {
            "hash_mode": V12_HASH_MODE,
            "pin_scope": {
                **_normalized_binding(pin_path, repo_root),
                "pin_scope_id": pin_scope["pin_scope_id"],
            },
            "authority_bindings": {
                "provider_scope_policy": _normalized_binding(provider_scope_policy_path, repo_root),
                "active_priority_policy": _normalized_binding(active_priority_policy_path, repo_root),
                "source_registry": _normalized_binding(source_registry_path, repo_root),
                "active_acceptance_manifest": _normalized_binding(active_manifest_path, repo_root),
            },
            "provider_scope": {
                "count": len(active_symbols),
                "symbols": list(active_symbols),
                "provider_scope_policy_sha256": normalized_sha256(provider_scope_policy_path),
                "order_authority": False,
            },
            "predecessor_implementation_drift": drift,
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
    active_priority_policy_path: Path,
    provider_scope_policy_path: Path,
    source_registry_path: Path,
    repo_root: Path,
    output_root: Path,
    generated_at: str,
    repository_base_commit: str,
    pin_scope_path: Path | None = None,
    evidence_root: Path | None = None,
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
        active_priority_policy_path=active_priority_policy_path,
        provider_scope_policy_path=provider_scope_policy_path,
        source_registry_path=source_registry_path,
        repo_root=repo_root,
        generated_at=generated_at,
        repository_base_commit=repository_base_commit,
        pin_scope_path=pin_scope_path,
        evidence_root=evidence_root,
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
        pin_scope_path=pin_scope_path,
    )
    if errors:
        raise AcceptanceCandidateMaterializationError(
            f"materialized candidate validation failed: {errors}"
        )
    governance = candidate["candidate_governance"]
    return {
        "status": "PASS",
        "candidate_status": candidate["candidate_status"],
        "candidate_path": str(candidate_path),
        "candidate_raw_sha256": candidate_sha,
        "write_status": write_status,
        "supersedes_acceptance_sha256": candidate["supersedes_acceptance_sha256"],
        "provider_scope_policy_sha256": governance["provider_scope"]["provider_scope_policy_sha256"],
        "provider_scope_count": governance["provider_scope"]["count"],
        "provider_scope_symbols": governance["provider_scope"]["symbols"],
        "pin_scope_id": governance["pin_scope"]["pin_scope_id"],
        "superseded_implementation_drift": [
            item["repository_path"] for item in governance["predecessor_implementation_drift"]
        ],
        "activation_performed": False,
        "quantity_authority": "none",
        "execution_quantity": None,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-priority-policy", required=True, type=Path)
    parser.add_argument("--provider-scope-policy", required=True, type=Path)
    parser.add_argument("--source-registry", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--repository-base-commit", required=True)
    parser.add_argument("--pin-scope", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = materialize_candidate(
            active_priority_policy_path=args.active_priority_policy,
            provider_scope_policy_path=args.provider_scope_policy,
            source_registry_path=args.source_registry,
            repo_root=args.repo_root,
            output_root=args.output_root,
            generated_at=args.generated_at,
            repository_base_commit=args.repository_base_commit,
            pin_scope_path=args.pin_scope,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except AcceptanceCandidateMaterializationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
