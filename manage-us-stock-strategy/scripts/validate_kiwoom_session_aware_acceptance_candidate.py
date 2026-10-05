#!/usr/bin/env python3
"""Validate an inactive superseding Kiwoom Acceptance candidate.

Schema 1.2 candidates (I4 R6) read their pin list from the pinned pin-scope
asset and their symbol scope from the bound active priority policy, and bind
authority files by normalized text hash. Schema 1.1 candidates keep the
historical raw-byte, fixed-scope contract below unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import file_hash, load_json, validate_instance
from validate_kiwoom_session_aware_acceptance import validate_acceptance
from validate_skill_deployment import normalized_text_sha256
from validate_source_capabilities import validate_registry


CANDIDATE_EVIDENCE_STATE = (
    "KIWOOM_SESSION_AWARE_GUARDED_PRIORITY_SUPERSEDING_CANDIDATE_INACTIVE"
)
V12_SCHEMA_VERSION = "1.2"
V12_HASH_GOVERNANCE = "IMPLEMENTATION_AND_AUTHORITY_BINDINGS_NORMALIZED_TEXT_SHA256"
V12_HASH_MODE = "NORMALIZED_TEXT_SHA256"
PIN_SCOPE_RELATIVE_PATH = "manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json"
PIN_SCOPE_SCHEMA_RELATIVE_PATH = "manage-us-stock-strategy/schemas/kiwoom-acceptance-pin-scope.schema.json"
IMPLEMENTATION_DRIFT_PREFIX = "implementation hash mismatch: "
# Historical schema 1.1 contract (08-28 11 -> 15 symbol transition); not used for 1.2.
ACTIVE_PROVIDER_SCOPE = (
    "SOXL", "MVLL", "NBIS", "BE", "TOST", "NOW", "FSLY", "SOXX", "MRVL", "AAPL", "IBM",
)
EXPECTED_PROVIDER_SCOPE = ACTIVE_PROVIDER_SCOPE + ("PGR", "JPM", "CME", "V")
REQUIRED_IMPLEMENTATION_PATHS = (
    "manage-us-stock-strategy/scripts/session_aware_market_data.py",
    "manage-us-stock-strategy/scripts/run_kiwoom_session_aware_validation.py",
    "manage-us-stock-strategy/scripts/build_kiwoom_session_observation.py",
    "manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py",
    "manage-us-stock-strategy/scripts/build_kiwoom_market_snapshot.py",
    "manage-us-stock-strategy/scripts/validate_kiwoom_market_snapshot.py",
    "manage-us-stock-strategy/scripts/kiwoom_provider_preflight.py",
    "manage-us-stock-strategy/scripts/validate_kiwoom_session_aware_acceptance.py",
    "manage-us-stock-strategy/scripts/validate_kiwoom_session_aware_acceptance_candidate.py",
    "manage-us-stock-strategy/scripts/materialize_kiwoom_session_aware_acceptance_candidate.py",
    "manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py",
    "manage-us-stock-strategy/tests/test_manual_portfolio_analysis.py",
    "manage-us-stock-strategy/schemas/kiwoom-session-aware-acceptance-manifest.schema.json",
    "manage-us-stock-strategy/schemas/kiwoom-session-aware-priority-policy.schema.json",
    "manage-us-stock-strategy/schemas/kiwoom-provider-scope.schema.json",
    "manage-us-stock-strategy/schemas/source-capability.schema.json",
)


def _confined_binding_path(
    binding: Any,
    *,
    name: str,
    repo_root: Path,
    errors: list[str],
    expected_path: Path | None = None,
) -> Path | None:
    if not isinstance(binding, dict):
        errors.append(f"candidate binding malformed: {name}")
        return None
    relative = str(binding.get("repository_path") or "")
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        errors.append(f"candidate binding path escapes repository: {name}")
        return None
    if expected_path is not None and candidate != expected_path.resolve():
        errors.append(f"candidate binding path mismatch: {name}")
    if not candidate.is_file():
        errors.append(f"candidate binding file missing: {name}")
        return None
    expected_hash = str(binding.get("raw_sha256") or "").lower()
    if file_hash(candidate).lower() != expected_hash:
        errors.append(f"candidate binding raw hash mismatch: {name}")
    if binding.get("hash_mode") != "RAW_BYTES_SHA256":
        errors.append(f"candidate binding hash mode mismatch: {name}")
    return candidate


def _policy_acceptance_bindings(policy: dict[str, Any], *, errors: list[str], label: str) -> set[str]:
    bindings = {
        str((policy.get("acceptance_evidence") or {}).get(
            "session_aware_acceptance_manifest_sha256"
        ) or "").lower()
    }
    scopes = policy.get("provider_scopes")
    if not isinstance(scopes, list):
        errors.append(f"{label} provider scopes missing")
        return bindings
    seen: set[str] = set()
    for index, scope in enumerate(scopes):
        if not isinstance(scope, dict):
            errors.append(f"{label} provider scope malformed: {index}")
            continue
        ticker = str(scope.get("ticker") or "").upper()
        if not ticker:
            errors.append(f"{label} provider scope ticker missing: {index}")
        elif ticker in seen:
            errors.append(f"{label} duplicate provider scope ticker: {ticker}")
        seen.add(ticker)
        bindings.add(str(scope.get("acceptance_artifact_hash") or "").lower())
        if scope.get("order_authority") is not False:
            errors.append(f"{label} provider scope order authority must be false: {ticker or index}")
    return bindings


def validate_candidate_acceptance(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    manifest_schema: Path,
    provider_scope_policy: dict[str, Any],
    provider_scope_policy_path: Path,
    priority_schema: Path,
    source_registry: dict[str, Any],
    source_registry_path: Path,
    source_schema: Path,
    repo_root: Path,
    pin_scope_path: Path | None = None,
) -> list[str]:
    """Validate a candidate while leaving every active acceptance pointer unchanged."""
    arguments = dict(
        manifest=manifest, manifest_path=manifest_path, manifest_schema=manifest_schema,
        provider_scope_policy=provider_scope_policy,
        provider_scope_policy_path=provider_scope_policy_path,
        priority_schema=priority_schema, source_registry=source_registry,
        source_registry_path=source_registry_path, source_schema=source_schema,
        repo_root=repo_root,
    )
    if manifest.get("schema_version") == V12_SCHEMA_VERSION:
        return _validate_candidate_v12(**arguments, pin_scope_path=pin_scope_path)
    return _validate_candidate_v11(**arguments)


def _validate_candidate_v11(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    manifest_schema: Path,
    provider_scope_policy: dict[str, Any],
    provider_scope_policy_path: Path,
    priority_schema: Path,
    source_registry: dict[str, Any],
    source_registry_path: Path,
    source_schema: Path,
    repo_root: Path,
) -> list[str]:
    """Historical 1.1 contract: raw-byte bindings and the fixed 11 -> 15 symbol scope."""
    errors = validate_instance(manifest, manifest_schema)
    errors.extend(validate_instance(provider_scope_policy, priority_schema))
    errors.extend(validate_registry(source_registry, source_schema))
    repo_root = repo_root.resolve()

    if manifest.get("schema_version") != "1.1":
        errors.append("candidate schema version mismatch")
    if manifest.get("evidence_state") != CANDIDATE_EVIDENCE_STATE:
        errors.append("candidate evidence state mismatch")
    if manifest.get("candidate_status") != "INACTIVE_SUPERSEDING_CANDIDATE":
        errors.append("candidate status mismatch")
    if manifest.get("activation_performed") is not False:
        errors.append("candidate activation must be false")
    if manifest.get("order_authority") is not False:
        errors.append("candidate order authority must be false")
    if manifest.get("quantity_authority") != "none":
        errors.append("candidate quantity authority must be none")
    if manifest.get("execution_quantity") is not None:
        errors.append("candidate execution quantity must be null")
    if manifest.get("hash_governance") != "IMPLEMENTATION_BINDINGS_NORMALIZED_TEXT_SHA256":
        errors.append("candidate implementation hash governance mismatch")

    supersedes = str(manifest.get("supersedes_acceptance_sha256") or "").lower()
    manifest_sha = file_hash(manifest_path).lower()
    if manifest_sha == supersedes:
        errors.append("candidate Acceptance ID must differ from active Acceptance ID")

    bindings = manifest.get("authority_bindings") or {}
    provider_binding = bindings.get("provider_scope_policy")
    active_policy_path = _confined_binding_path(
        bindings.get("active_priority_policy"),
        name="active_priority_policy",
        repo_root=repo_root,
        errors=errors,
    )
    _confined_binding_path(
        provider_binding,
        name="provider_scope_policy",
        repo_root=repo_root,
        errors=errors,
        expected_path=provider_scope_policy_path,
    )
    _confined_binding_path(
        bindings.get("source_registry"),
        name="source_registry",
        repo_root=repo_root,
        errors=errors,
        expected_path=source_registry_path,
    )
    active_acceptance_path = _confined_binding_path(
        bindings.get("active_acceptance_manifest"),
        name="active_acceptance_manifest",
        repo_root=repo_root,
        errors=errors,
    )
    if active_acceptance_path is not None and file_hash(active_acceptance_path).lower() != supersedes:
        errors.append("active Acceptance binding does not match supersedes ID")

    scope_contract = manifest.get("provider_scope_contract") or {}
    scopes = provider_scope_policy.get("provider_scopes")
    scope_symbols: list[str] = []
    if isinstance(scopes, list):
        scope_symbols = [
            str(scope.get("ticker") or "").upper()
            for scope in scopes if isinstance(scope, dict)
        ]
    if tuple(scope_symbols) != EXPECTED_PROVIDER_SCOPE:
        errors.append(f"candidate provider scope mismatch: {scope_symbols}")
    if scope_contract.get("count") != len(EXPECTED_PROVIDER_SCOPE):
        errors.append("candidate provider scope count mismatch")
    if scope_contract.get("symbols") != list(EXPECTED_PROVIDER_SCOPE):
        errors.append("candidate provider scope contract symbols mismatch")
    provider_raw_sha = file_hash(provider_scope_policy_path).lower()
    if str(scope_contract.get("provider_scope_policy_raw_sha256") or "").lower() != provider_raw_sha:
        errors.append("provider scope contract raw hash mismatch")
    if isinstance(provider_binding, dict) and str(provider_binding.get("raw_sha256") or "").lower() != provider_raw_sha:
        errors.append("provider scope authority binding raw hash mismatch")

    candidate_pointer_bindings = _policy_acceptance_bindings(
        provider_scope_policy, errors=errors, label="candidate"
    )
    if candidate_pointer_bindings != {supersedes}:
        errors.append(f"candidate wrapper has split active Acceptance authority: {candidate_pointer_bindings}")

    if active_policy_path is not None:
        active_policy = load_json(active_policy_path)
        active_symbols = tuple(
            str(scope.get("ticker") or "").upper()
            for scope in active_policy.get("provider_scopes", []) if isinstance(scope, dict)
        )
        if active_symbols != ACTIVE_PROVIDER_SCOPE:
            errors.append(f"active K2 provider scope changed: {active_symbols}")
        active_bindings = _policy_acceptance_bindings(active_policy, errors=errors, label="active")
        if active_bindings != {supersedes}:
            errors.append(f"active K2 has split Acceptance authority: {active_bindings}")

    kiwoom_rows = [
        row for row in source_registry.get("providers", [])
        if isinstance(row, dict) and row.get("provider") == "kiwoom_rest"
    ]
    if len(kiwoom_rows) != 1:
        errors.append("source registry requires exactly one kiwoom_rest row")
    elif str(kiwoom_rows[0].get("acceptance_artifact_sha256") or "").lower() != supersedes:
        errors.append("source registry active Acceptance binding changed")

    implementation_hashes = manifest.get("implementation_hashes") or {}
    if set(implementation_hashes) != set(REQUIRED_IMPLEMENTATION_PATHS):
        errors.append("candidate required implementation path set mismatch")
    for relative, expected in implementation_hashes.items():
        candidate = (repo_root / relative).resolve()
        try:
            candidate.relative_to(repo_root)
        except ValueError:
            errors.append(f"implementation path escapes repository: {relative}")
            continue
        if not candidate.is_file():
            errors.append(f"implementation file missing: {relative}")
        elif normalized_text_sha256(candidate).lower() != str(expected).lower():
            errors.append(f"implementation hash mismatch: {relative}")

    for name, evidence in (manifest.get("source_artifacts") or {}).items():
        relative = str((evidence or {}).get("repository_path") or "")
        candidate = (repo_root / relative).resolve()
        try:
            candidate.relative_to(repo_root)
        except ValueError:
            errors.append(f"source artifact path escapes repository: {name}")
            continue
        if not candidate.is_file():
            errors.append(f"source artifact missing: {name}")
        elif file_hash(candidate).lower() != str((evidence or {}).get("sha256") or "").lower():
            errors.append(f"source artifact raw hash mismatch: {name}")

    invariants = manifest.get("invariants") or {}
    if (
        invariants.get("portfolio_unchanged") is not True
        or str(invariants.get("portfolio_sha256_before") or "").lower()
        != str(invariants.get("portfolio_sha256_after") or "").lower()
    ):
        errors.append("candidate portfolio immutability failed")
    return errors


def normalized_sha256(path: Path) -> str:
    """Line-ending and BOM independent hash used for every schema 1.2 binding."""
    return normalized_text_sha256(path).lower()


def confined_repo_path(relative: Any, repo_root: Path) -> Path | None:
    """Resolve a repository-relative path, or None when it escapes the repository."""
    if not isinstance(relative, str) or not relative:
        return None
    repo_root = repo_root.resolve()
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        return None
    return candidate


def ordered_policy_symbols(policy: dict[str, Any]) -> tuple[str, ...]:
    """Ticker order exactly as the policy lists it; malformed rows yield an empty tuple."""
    scopes = policy.get("provider_scopes")
    if not isinstance(scopes, list) or any(not isinstance(scope, dict) for scope in scopes):
        return ()
    return tuple(str(scope.get("ticker") or "").upper() for scope in scopes)


def load_pin_scope(path: Path, repo_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load and schema-check the pinned pin-scope asset."""
    schema = confined_repo_path(PIN_SCOPE_SCHEMA_RELATIVE_PATH, repo_root)
    if not path.is_file():
        return None, ["pin scope file missing"]
    if schema is None or not schema.is_file():
        return None, ["pin scope schema missing"]
    try:
        scope = load_json(path)
    except (OSError, ValueError):
        return None, ["pin scope unreadable"]
    errors = [f"pin scope invalid: {error}" for error in validate_instance(scope, schema)]
    if PIN_SCOPE_RELATIVE_PATH not in (scope.get("required_implementation_paths") or []):
        errors.append("pin scope must pin itself")
    if PIN_SCOPE_SCHEMA_RELATIVE_PATH not in (scope.get("required_implementation_paths") or []):
        errors.append("pin scope must pin its schema")
    return (scope if not errors else None), errors


def predecessor_implementation_drift(
    predecessor: dict[str, Any], repo_root: Path,
) -> tuple[list[dict[str, str]], list[str]]:
    """Every predecessor-pinned file whose normalized hash changed, plus hard errors."""
    drift: list[dict[str, str]] = []
    errors: list[str] = []
    hashes = predecessor.get("implementation_hashes")
    if not isinstance(hashes, dict) or not hashes:
        return [], ["predecessor implementation hashes missing"]
    for relative, pinned in sorted(hashes.items()):
        path = confined_repo_path(relative, repo_root)
        if path is None:
            errors.append(f"predecessor implementation path escapes repository: {relative}")
            continue
        if not path.is_file():
            errors.append(f"predecessor implementation file missing: {relative}")
            continue
        current = normalized_sha256(path)
        if current != str(pinned).lower():
            drift.append({
                "repository_path": relative,
                "pinned_sha256": str(pinned).lower(),
                "current_sha256": current,
            })
    return drift, errors


def allowed_drift_for(pin_scope: dict[str, Any], predecessor_sha256: str) -> list[str]:
    """Drift is excusable only when the allowance names this exact predecessor."""
    bound = str(pin_scope.get("allowed_drift_predecessor_sha256") or "").lower()
    if bound != str(predecessor_sha256 or "").lower():
        return []
    return list(pin_scope.get("allowed_predecessor_drift") or [])


def disallowed_predecessor_errors(
    predecessor_errors: list[str], allowed_drift: list[str],
) -> list[str]:
    """Only implementation drift on explicitly allowed paths may be superseded."""
    allowed = {IMPLEMENTATION_DRIFT_PREFIX + relative for relative in allowed_drift}
    return [error for error in predecessor_errors if error not in allowed]


def _confined_normalized_binding(
    binding: Any,
    *,
    name: str,
    repo_root: Path,
    errors: list[str],
    expected_path: Path | None = None,
) -> Path | None:
    if not isinstance(binding, dict):
        errors.append(f"candidate binding malformed: {name}")
        return None
    candidate = confined_repo_path(binding.get("repository_path"), repo_root)
    if candidate is None:
        errors.append(f"candidate binding path escapes repository: {name}")
        return None
    if expected_path is not None and candidate != expected_path.resolve():
        errors.append(f"candidate binding path mismatch: {name}")
    if not candidate.is_file():
        errors.append(f"candidate binding file missing: {name}")
        return None
    if normalized_sha256(candidate) != str(binding.get("sha256") or "").lower():
        errors.append(f"candidate binding normalized hash mismatch: {name}")
    return candidate


def _validate_candidate_v12(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    manifest_schema: Path,
    provider_scope_policy: dict[str, Any],
    provider_scope_policy_path: Path,
    priority_schema: Path,
    source_registry: dict[str, Any],
    source_registry_path: Path,
    source_schema: Path,
    repo_root: Path,
    pin_scope_path: Path | None,
) -> list[str]:
    """Schema 1.2: pin list from the pinned asset, scope from the bound active policy."""
    errors = validate_instance(manifest, manifest_schema)
    errors.extend(validate_instance(provider_scope_policy, priority_schema))
    errors.extend(validate_registry(source_registry, source_schema))
    repo_root = repo_root.resolve()

    if manifest.get("schema_version") != V12_SCHEMA_VERSION:
        errors.append("candidate schema version mismatch")
    if manifest.get("evidence_state") != CANDIDATE_EVIDENCE_STATE:
        errors.append("candidate evidence state mismatch")
    if manifest.get("candidate_status") != "INACTIVE_SUPERSEDING_CANDIDATE":
        errors.append("candidate status mismatch")
    if manifest.get("activation_performed") is not False:
        errors.append("candidate activation must be false")
    if manifest.get("order_authority") is not False:
        errors.append("candidate order authority must be false")
    if manifest.get("quantity_authority") != "none":
        errors.append("candidate quantity authority must be none")
    if manifest.get("execution_quantity") is not None:
        errors.append("candidate execution quantity must be null")
    if manifest.get("hash_governance") != V12_HASH_GOVERNANCE:
        errors.append("candidate hash governance mismatch")
    for legacy in ("authority_bindings", "provider_scope_contract"):
        if legacy in manifest:
            errors.append(f"candidate carries legacy raw binding block: {legacy}")
    governance = manifest.get("candidate_governance")
    if not isinstance(governance, dict):
        errors.append("candidate governance missing")
        return errors
    if governance.get("hash_mode") != V12_HASH_MODE:
        errors.append("candidate governance hash mode mismatch")

    supersedes = str(manifest.get("supersedes_acceptance_sha256") or "").lower()
    if manifest_path.is_file() and normalized_sha256(manifest_path) == supersedes:
        errors.append("candidate Acceptance ID must differ from active Acceptance ID")

    bindings = governance.get("authority_bindings") or {}
    active_policy_path = _confined_normalized_binding(
        bindings.get("active_priority_policy"), name="active_priority_policy",
        repo_root=repo_root, errors=errors,
    )
    _confined_normalized_binding(
        bindings.get("provider_scope_policy"), name="provider_scope_policy",
        repo_root=repo_root, errors=errors, expected_path=provider_scope_policy_path,
    )
    _confined_normalized_binding(
        bindings.get("source_registry"), name="source_registry",
        repo_root=repo_root, errors=errors, expected_path=source_registry_path,
    )
    active_acceptance_path = _confined_normalized_binding(
        bindings.get("active_acceptance_manifest"), name="active_acceptance_manifest",
        repo_root=repo_root, errors=errors,
    )
    if active_acceptance_path is not None and normalized_sha256(active_acceptance_path) != supersedes:
        errors.append("active Acceptance binding does not match supersedes ID")

    candidate_pointers = _policy_acceptance_bindings(
        provider_scope_policy, errors=errors, label="candidate",
    )
    if candidate_pointers != {supersedes}:
        errors.append(f"candidate wrapper has split active Acceptance authority: {candidate_pointers}")
    candidate_symbols = ordered_policy_symbols(provider_scope_policy)
    scope_contract = governance.get("provider_scope") or {}
    provider_sha = normalized_sha256(provider_scope_policy_path) if provider_scope_policy_path.is_file() else ""
    if str(scope_contract.get("provider_scope_policy_sha256") or "").lower() != provider_sha:
        errors.append("provider scope contract normalized hash mismatch")
    if not candidate_symbols or scope_contract.get("symbols") != list(candidate_symbols):
        errors.append("candidate provider scope contract symbols mismatch")
    if scope_contract.get("count") != len(candidate_symbols):
        errors.append("candidate provider scope count mismatch")

    active_policy: dict[str, Any] | None = None
    if active_policy_path is not None:
        active_policy = load_json(active_policy_path)
        if ordered_policy_symbols(active_policy) != candidate_symbols:
            errors.append("candidate provider scope differs from bound active scope")
        active_pointers = _policy_acceptance_bindings(active_policy, errors=errors, label="active")
        if active_pointers != {supersedes}:
            errors.append(f"active K2 has split Acceptance authority: {active_pointers}")

    kiwoom_rows = [
        row for row in source_registry.get("providers", [])
        if isinstance(row, dict) and row.get("provider") == "kiwoom_rest"
    ]
    if len(kiwoom_rows) != 1:
        errors.append("source registry requires exactly one kiwoom_rest row")
    elif str(kiwoom_rows[0].get("acceptance_artifact_sha256") or "").lower() != supersedes:
        errors.append("source registry active Acceptance binding changed")

    expected_pin_path = (pin_scope_path or repo_root / PIN_SCOPE_RELATIVE_PATH).resolve()
    pin_binding = governance.get("pin_scope") or {}
    bound_pin_path = confined_repo_path(pin_binding.get("repository_path"), repo_root)
    pin_scope: dict[str, Any] | None = None
    if bound_pin_path is None or bound_pin_path != expected_pin_path:
        errors.append("pin scope binding path mismatch")
    else:
        pin_scope, pin_errors = load_pin_scope(bound_pin_path, repo_root)
        errors.extend(pin_errors)
        if bound_pin_path.is_file() and normalized_sha256(bound_pin_path) != str(pin_binding.get("sha256") or "").lower():
            errors.append("pin scope normalized hash mismatch")
    implementation_hashes = manifest.get("implementation_hashes") or {}
    if pin_scope is not None:
        if pin_binding.get("pin_scope_id") != pin_scope.get("pin_scope_id"):
            errors.append("pin scope id mismatch")
        if set(implementation_hashes) != set(pin_scope["required_implementation_paths"]):
            errors.append("candidate required implementation path set mismatch")
    for relative, expected in implementation_hashes.items():
        candidate = confined_repo_path(relative, repo_root)
        if candidate is None:
            errors.append(f"implementation path escapes repository: {relative}")
        elif not candidate.is_file():
            errors.append(f"implementation file missing: {relative}")
        elif normalized_sha256(candidate) != str(expected).lower():
            errors.append(f"implementation hash mismatch: {relative}")

    if active_acceptance_path is not None and pin_scope is not None and active_policy is not None:
        predecessor = load_json(active_acceptance_path)
        drift, drift_errors = predecessor_implementation_drift(predecessor, repo_root)
        errors.extend(drift_errors)
        allowed = allowed_drift_for(pin_scope, supersedes)
        for item in drift:
            if item["repository_path"] not in allowed:
                errors.append(f"predecessor drift not allowed: {item['repository_path']}")
        recorded = governance.get("predecessor_implementation_drift")
        if not isinstance(recorded, list) or sorted(
            json.dumps(item, sort_keys=True) for item in recorded if isinstance(item, dict)
        ) != sorted(json.dumps(item, sort_keys=True) for item in drift) or len(recorded) != len(drift):
            errors.append("candidate predecessor drift record mismatch")
        predecessor_errors = validate_acceptance(
            manifest=predecessor,
            manifest_path=active_acceptance_path,
            manifest_schema=manifest_schema,
            priority_policy=active_policy,
            priority_schema=priority_schema,
            source_registry=source_registry,
            source_schema=source_schema,
            repo_root=repo_root,
        )
        for error in disallowed_predecessor_errors(predecessor_errors, allowed):
            errors.append(f"active Acceptance invalid beyond allowed drift: {error}")

    for name, evidence in (manifest.get("source_artifacts") or {}).items():
        candidate = confined_repo_path((evidence or {}).get("repository_path"), repo_root)
        if candidate is None:
            errors.append(f"source artifact path escapes repository: {name}")
        elif not candidate.is_file():
            errors.append(f"source artifact missing: {name}")
        elif file_hash(candidate).lower() != str((evidence or {}).get("sha256") or "").lower():
            errors.append(f"source artifact raw hash mismatch: {name}")

    invariants = manifest.get("invariants") or {}
    if (
        invariants.get("portfolio_unchanged") is not True
        or str(invariants.get("portfolio_sha256_before") or "").lower()
        != str(invariants.get("portfolio_sha256_after") or "").lower()
    ):
        errors.append("candidate portfolio immutability failed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-schema", required=True, type=Path)
    parser.add_argument("--provider-scope-policy", required=True, type=Path)
    parser.add_argument("--priority-schema", required=True, type=Path)
    parser.add_argument("--source-registry", required=True, type=Path)
    parser.add_argument("--source-schema", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--pin-scope", type=Path, default=None)
    args = parser.parse_args()
    errors = validate_candidate_acceptance(
        manifest=load_json(args.manifest),
        manifest_path=args.manifest,
        manifest_schema=args.manifest_schema,
        provider_scope_policy=load_json(args.provider_scope_policy),
        provider_scope_policy_path=args.provider_scope_policy,
        priority_schema=args.priority_schema,
        source_registry=load_json(args.source_registry),
        source_registry_path=args.source_registry,
        source_schema=args.source_schema,
        repo_root=args.repo_root,
        pin_scope_path=args.pin_scope,
    )
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
