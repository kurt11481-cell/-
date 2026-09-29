#!/usr/bin/env python3
"""One-read combined activation loader for frozen Identity + Session authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping

from authority_artifact_io import (
    AuthorityArtifactIOError,
    decode_canonical_object,
    read_once_no_reparse,
)
from instrument_identity_artifact import (
    ARTIFACT_DIRECTORY_RELATIVE_PATH as IDENTITY_ARTIFACT_DIRECTORY,
    ARTIFACT_FILENAME as IDENTITY_ARTIFACT_FILENAME,
    InstrumentIdentityLoadError,
    LoadedInstrumentIdentityRegistry,
    _semantic_validate_artifact as _semantic_validate_identity_artifact,
    _validate_binding as _validate_identity_binding,
)
from instrument_identity_authority import _resolve as _resolve_identity
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from session_authority import _derive as _derive_session
from session_calendar_artifact import (
    ARTIFACT_DIRECTORY_RELATIVE_PATH as SESSION_ARTIFACT_DIRECTORY,
    ARTIFACT_FILENAME as SESSION_ARTIFACT_FILENAME,
    LoadedSessionCalendar,
    SessionCalendarLoadError,
    _semantic_validate_artifact as _semantic_validate_session_artifact,
    _validate_binding as _validate_session_binding,
)
from validation_common import validate_instance


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"
COMBINED_ACTIVATION_RELATIVE_PATH = Path(
    "workspace/policies/integrated_identity_session_activation.json"
)
SHADOW_OUTPUT_RELATIVE_ROOT = Path(
    "workspace/outputs/k3-combined-identity-session-activation"
)
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


class IntegratedAuthorityLoadError(ValueError):
    """Fail-closed combined activation or integrated snapshot result."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class IntegratedAuthoritySnapshot:
    combined_activation_manifest_sha256: str
    activation_cohort_id: str
    identity: LoadedInstrumentIdentityRegistry
    session: LoadedSessionCalendar
    authority_resolved_at: str
    snapshot_decision_as_of: str
    run_id: str | None

    def provenance(
        self, *, authority_source: str, report_decision_as_of: str | None = None,
    ) -> dict[str, Any]:
        """Return a JSON-compatible run binding without exposing mutable snapshot data."""
        return {
            "authority_source": authority_source,
            "combined_activation_manifest_sha256": self.combined_activation_manifest_sha256,
            "activation_cohort_id": self.activation_cohort_id,
            "instrument_identity_artifact_sha256": self.identity.registry_hash,
            "session_calendar_artifact_sha256": self.session.calendar_hash,
            "identity_registry_version": self.identity.artifact["registry_version"],
            "session_calendar_version": self.session.artifact["calendar_version"],
            "authority_resolved_at": self.authority_resolved_at,
            "snapshot_decision_as_of": self.snapshot_decision_as_of,
            "report_decision_as_of": report_decision_as_of or self.snapshot_decision_as_of,
            "run_id": self.run_id,
        }


def _strict_timestamp(value: Any) -> datetime:
    text = str(value)
    if RFC3339_PATTERN.fullmatch(text) is None:
        raise ValueError("INVALID_RFC3339")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed


def _absolute_under_root(path: Path, trusted_root: Path) -> Path:
    trusted = Path(os.path.abspath(os.fspath(trusted_root)))
    candidate = path if path.is_absolute() else trusted / path
    return Path(os.path.abspath(os.fspath(candidate)))


def _decode_manifest(raw: bytes) -> dict[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(token)

    def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if not isinstance(value, dict):
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _activation_view(manifest: Mapping[str, Any], binding_name: str) -> dict[str, Any]:
    binding = manifest[binding_name]
    return {
        **dict(binding),
        "activated_at": manifest["activated_at"],
        "authority_modes_allowed": list(manifest["authority_modes_allowed"]),
        "activation_cohort_id": manifest["activation_cohort_id"],
    }


def _read_identity_artifact(
    trusted_root: Path, binding: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    artifact_hash = str(binding.get("active_registry_hash") or "")
    if HASH_PATTERN.fullmatch(artifact_hash) is None:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    artifact_path = (
        trusted_root / IDENTITY_ARTIFACT_DIRECTORY / artifact_hash / IDENTITY_ARTIFACT_FILENAME
    )
    try:
        raw = read_once_no_reparse(artifact_path, trusted_root)
    except (FileNotFoundError, AuthorityArtifactIOError, OSError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if hashlib.sha256(raw).hexdigest() != artifact_hash:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    try:
        artifact = decode_canonical_object(raw)
    except AuthorityArtifactIOError as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if validate_instance(artifact, SCHEMA_ROOT / "instrument-identity-artifact.schema.json"):
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    try:
        _semantic_validate_identity_artifact(artifact)
    except InstrumentIdentityLoadError as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    return artifact, artifact_hash


def _read_session_artifact(
    trusted_root: Path, binding: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    artifact_hash = str(binding.get("active_calendar_hash") or "")
    if HASH_PATTERN.fullmatch(artifact_hash) is None:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    artifact_path = (
        trusted_root / SESSION_ARTIFACT_DIRECTORY / artifact_hash / SESSION_ARTIFACT_FILENAME
    )
    try:
        raw = read_once_no_reparse(artifact_path, trusted_root)
    except (FileNotFoundError, AuthorityArtifactIOError, OSError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if hashlib.sha256(raw).hexdigest() != artifact_hash:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    try:
        artifact = decode_canonical_object(raw)
    except AuthorityArtifactIOError as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if validate_instance(artifact, SCHEMA_ROOT / "session-calendar-artifact.schema.json"):
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    try:
        _semantic_validate_session_artifact(artifact)
    except SessionCalendarLoadError as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    return artifact, artifact_hash


def _validate_temporal_integrity(
    manifest: Mapping[str, Any],
    identity_artifact: Mapping[str, Any],
    session_artifact: Mapping[str, Any],
    *,
    decision_as_of: str,
) -> None:
    try:
        cutoff = _strict_timestamp(decision_as_of)
        evidence_times = (
            _strict_timestamp(manifest["activated_at"]),
            _strict_timestamp(identity_artifact["authority_as_of"]),
            _strict_timestamp(identity_artifact["generated_at"]),
            _strict_timestamp(session_artifact["authority_as_of"]),
            _strict_timestamp(session_artifact["generated_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if any(value > cutoff for value in evidence_times):
        raise IntegratedAuthorityLoadError("TEMPORAL_VIOLATION")


def load_integrated_authority_snapshot(
    manifest_path: Path,
    *,
    trusted_root: Path = ROOT,
    decision_as_of: str,
    required_activation_status: Literal["ACTIVE", "SHADOW"] = "ACTIVE",
    resolved_at: str | None = None,
    run_id: str | None = None,
) -> IntegratedAuthoritySnapshot:
    """Read one combined manifest once and freeze both validated authorities."""
    trusted = _absolute_under_root(Path("."), trusted_root)
    target = _absolute_under_root(Path(manifest_path), trusted)
    try:
        raw = read_once_no_reparse(target, trusted)
    except FileNotFoundError as exc:
        raise IntegratedAuthorityLoadError("ARTIFACT_NOT_ACTIVATED") from exc
    except (AuthorityArtifactIOError, OSError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    manifest_hash = hashlib.sha256(raw).hexdigest()
    manifest = _decode_manifest(raw)
    if validate_instance(manifest, SCHEMA_ROOT / "integrated-authority-activation.schema.json"):
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    if manifest.get("activation_status") != required_activation_status:
        raise IntegratedAuthorityLoadError("ARTIFACT_NOT_ACTIVATED")

    identity_artifact, identity_hash = _read_identity_artifact(
        trusted, manifest["instrument_identity"],
    )
    session_artifact, session_hash = _read_session_artifact(
        trusted, manifest["session_calendar"],
    )
    identity_activation = _activation_view(manifest, "instrument_identity")
    session_activation = _activation_view(manifest, "session_calendar")
    try:
        _validate_identity_binding(identity_activation, identity_artifact)
        _validate_session_binding(session_activation, session_artifact)
    except (InstrumentIdentityLoadError, SessionCalendarLoadError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    _validate_temporal_integrity(
        manifest,
        identity_artifact,
        session_artifact,
        decision_as_of=decision_as_of,
    )

    resolution_time = resolved_at or datetime.now(timezone.utc).isoformat()
    try:
        _strict_timestamp(resolution_time)
    except (TypeError, ValueError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    cohort = str(manifest["activation_cohort_id"])
    frozen_identity_activation = _freeze(identity_activation)
    frozen_identity_artifact = _freeze(identity_artifact)
    frozen_session_activation = _freeze(session_activation)
    frozen_session_artifact = _freeze(session_artifact)
    return IntegratedAuthoritySnapshot(
        combined_activation_manifest_sha256=manifest_hash,
        activation_cohort_id=cohort,
        identity=LoadedInstrumentIdentityRegistry(
            activation=frozen_identity_activation,
            artifact=frozen_identity_artifact,
            registry_hash=identity_hash,
        ),
        session=LoadedSessionCalendar(
            activation=frozen_session_activation,
            artifact=frozen_session_artifact,
            calendar_hash=session_hash,
        ),
        authority_resolved_at=resolution_time,
        snapshot_decision_as_of=decision_as_of,
        run_id=run_id,
    )


def load_production_integrated_authority_snapshot(
    *,
    trusted_root: Path = ROOT,
    decision_as_of: str,
    resolved_at: str | None = None,
    run_id: str | None = None,
) -> IntegratedAuthoritySnapshot:
    """Load the fixed Production combined authority with no legacy fallback."""
    trusted = _absolute_under_root(Path("."), trusted_root)
    return load_integrated_authority_snapshot(
        trusted / COMBINED_ACTIVATION_RELATIVE_PATH,
        trusted_root=trusted,
        decision_as_of=decision_as_of,
        required_activation_status="ACTIVE",
        resolved_at=resolved_at,
        run_id=run_id,
    )


def resolve_instrument_identity_from_snapshot(
    snapshot: IntegratedAuthoritySnapshot,
    ticker: str,
    *,
    decision_as_of: str,
):
    """Resolve Identity without reopening any activation or artifact path."""
    return _resolve_identity(
        ticker,
        decision_as_of=decision_as_of,
        authority_mode="CURRENT",
        loader=lambda: snapshot.identity,
    )


def derive_us_market_session_authority_from_snapshot(
    snapshot: IntegratedAuthoritySnapshot,
    observed_at: str,
    *,
    primary_listing_operating_mic: str | None,
    decision_as_of: str,
):
    """Derive Session Authority without reopening any activation or artifact path."""
    return _derive_session(
        observed_at,
        primary_listing_operating_mic=primary_listing_operating_mic,
        decision_as_of=decision_as_of,
        authority_mode="CURRENT",
        loader=lambda: snapshot.session,
    )


def build_combined_activation_manifest(
    *,
    trusted_root: Path = ROOT,
    identity_artifact_sha256: str,
    session_calendar_artifact_sha256: str,
    cohort_id: str,
    previous_cohort_id: str,
    activated_at: str,
    activation_status: Literal["ACTIVE", "SHADOW"] = "SHADOW",
    activation_reason: str,
) -> dict[str, Any]:
    """Build a minimal combined manifest from two validated immutable artifacts."""
    if not isinstance(cohort_id, str) or not cohort_id:
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    if not isinstance(previous_cohort_id, str) or not previous_cohort_id:
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    if cohort_id == previous_cohort_id:
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    if not isinstance(activation_reason, str) or not activation_reason:
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    trusted = _absolute_under_root(Path("."), trusted_root)
    identity_artifact, _ = _read_identity_artifact(
        trusted, {"active_registry_hash": identity_artifact_sha256},
    )
    session_artifact, _ = _read_session_artifact(
        trusted, {"active_calendar_hash": session_calendar_artifact_sha256},
    )
    manifest = {
        "activation_schema_version": "1.0",
        "activation_status": activation_status,
        "activation_reason": activation_reason,
        "activated_at": activated_at,
        "authority_modes_allowed": ["CURRENT"],
        "activation_cohort_id": cohort_id,
        "instrument_identity": {
            "authority_id": identity_artifact["authority_id"],
            "active_registry_hash": identity_artifact_sha256,
            "active_registry_version": identity_artifact["registry_version"],
            "ticker_namespace": identity_artifact["ticker_namespace"],
            "scope": identity_artifact["scope"],
            "source_packet_id": identity_artifact["source_packet_id"],
            "source_packet_hash": identity_artifact["source_packet_hash"],
            "authority_as_of": identity_artifact["authority_as_of"],
        },
        "session_calendar": {
            "calendar_policy_identity": session_artifact["calendar_policy_identity"],
            "active_calendar_hash": session_calendar_artifact_sha256,
            "active_calendar_version": session_artifact["calendar_version"],
            "timezone_identity": session_artifact["timezone_identity"],
            "operating_mic_scope": session_artifact["operating_mic_scope"],
            "source_families": session_artifact["source_families"],
            "coverage_start": session_artifact["coverage_start"],
            "coverage_end": session_artifact["coverage_end"],
            "source_bundle_id": session_artifact["source_bundle_id"],
            "source_bundle_hash": session_artifact["source_bundle_hash"],
            "authority_as_of": session_artifact["authority_as_of"],
        },
    }
    if validate_instance(manifest, SCHEMA_ROOT / "integrated-authority-activation.schema.json"):
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    _validate_temporal_integrity(
        manifest,
        identity_artifact,
        session_artifact,
        decision_as_of=activated_at,
    )
    return manifest


def write_shadow_combined_activation_manifest(
    manifest: dict[str, Any],
    destination: Path,
    *,
    trusted_root: Path = ROOT,
    before_replace: Callable[[Path, Path], None] | None = None,
) -> str:
    """Stage, validate, then atomically replace one non-authoritative Shadow file."""
    if manifest.get("activation_status") != "SHADOW":
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    trusted = _absolute_under_root(Path("."), trusted_root)
    target = _absolute_under_root(Path(destination), trusted)
    allowed_root = _absolute_under_root(SHADOW_OUTPUT_RELATIVE_ROOT, trusted)
    try:
        target.relative_to(allowed_root)
        validate_shadow_output_path(
            target,
            trusted,
            protected=[
                trusted / COMBINED_ACTIVATION_RELATIVE_PATH,
                trusted / "workspace/policies/instrument_identity_activation.json",
                trusted / "workspace/policies/session_calendar_activation.json",
            ],
        )
    except ValueError as exc:
        raise IntegratedAuthorityLoadError("OUTPUT_NOT_SHADOW") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.parent / f".{target.name}.{uuid.uuid4().hex}.staged"
    try:
        atomic_write_json(staged, manifest)
        load_integrated_authority_snapshot(
            staged,
            trusted_root=trusted,
            decision_as_of=manifest["activated_at"],
            required_activation_status="SHADOW",
            resolved_at=manifest["activated_at"],
        )
        if before_replace is not None:
            before_replace(staged, target)
        os.replace(staged, target)
    finally:
        if staged.exists():
            staged.unlink()
    return hashlib.sha256(target.read_bytes()).hexdigest()


def write_staged_production_combined_activation_candidate(
    manifest: dict[str, Any],
    destination: Path,
    *,
    trusted_root: Path = ROOT,
) -> str:
    """Write and validate a non-authoritative ACTIVE candidate under outputs."""
    if manifest.get("activation_status") != "ACTIVE":
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    trusted = _absolute_under_root(Path("."), trusted_root)
    target = _absolute_under_root(Path(destination), trusted)
    try:
        validate_shadow_output_path(
            target,
            trusted,
            protected=[
                trusted / COMBINED_ACTIVATION_RELATIVE_PATH,
                trusted / "workspace/policies/instrument_identity_activation.json",
                trusted / "workspace/policies/session_calendar_activation.json",
            ],
        )
    except ValueError as exc:
        raise IntegratedAuthorityLoadError("OUTPUT_NOT_STAGING") from exc
    atomic_write_json(target, manifest)
    load_integrated_authority_snapshot(
        target,
        trusted_root=trusted,
        decision_as_of=manifest["activated_at"],
        required_activation_status="ACTIVE",
        resolved_at=manifest["activated_at"],
    )
    return hashlib.sha256(read_once_no_reparse(target, trusted)).hexdigest()


def _verify_expected_production_target(
    target: Path,
    trusted: Path,
    expected_current_sha256: str | None,
) -> None:
    if not target.exists():
        if expected_current_sha256 is not None:
            raise IntegratedAuthorityLoadError("PRODUCTION_MANIFEST_EXPECTED_BUT_MISSING")
        return
    if expected_current_sha256 is None:
        raise IntegratedAuthorityLoadError("PRODUCTION_MANIFEST_ALREADY_ACTIVE")
    if HASH_PATTERN.fullmatch(expected_current_sha256) is None:
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    try:
        current = read_once_no_reparse(target, trusted)
    except (AuthorityArtifactIOError, OSError) as exc:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE") from exc
    if hashlib.sha256(current).hexdigest() != expected_current_sha256:
        raise IntegratedAuthorityLoadError("PRODUCTION_MANIFEST_STALE")


def write_production_combined_activation_manifest(
    manifest: dict[str, Any],
    *,
    trusted_root: Path = ROOT,
    expected_current_sha256: str | None = None,
    before_replace: Callable[[Path, Path], None] | None = None,
) -> str:
    """Validate and atomically activate exactly the fixed Production manifest."""
    if manifest.get("activation_status") != "ACTIVE":
        raise IntegratedAuthorityLoadError("INVALID_INPUT")
    trusted = _absolute_under_root(Path("."), trusted_root)
    target = trusted / COMBINED_ACTIVATION_RELATIVE_PATH
    _verify_expected_production_target(target, trusted, expected_current_sha256)
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.parent / f".{target.name}.{uuid.uuid4().hex}.staged"
    staged_hash: str | None = None
    try:
        atomic_write_json(staged, manifest)
        load_integrated_authority_snapshot(
            staged,
            trusted_root=trusted,
            decision_as_of=manifest["activated_at"],
            required_activation_status="ACTIVE",
            resolved_at=manifest["activated_at"],
        )
        staged_hash = hashlib.sha256(read_once_no_reparse(staged, trusted)).hexdigest()
        if before_replace is not None:
            before_replace(staged, target)
        _verify_expected_production_target(target, trusted, expected_current_sha256)
        os.replace(staged, target)
        final_raw = read_once_no_reparse(target, trusted)
        if hashlib.sha256(final_raw).hexdigest() != staged_hash:
            raise IntegratedAuthorityLoadError("POST_ACT_VALIDATION_FAILURE")
        load_production_integrated_authority_snapshot(
            trusted_root=trusted,
            decision_as_of=manifest["activated_at"],
            resolved_at=manifest["activated_at"],
        )
    finally:
        if staged.exists():
            staged.unlink()
    if staged_hash is None:
        raise IntegratedAuthorityLoadError("INTEGRITY_FAILURE")
    return staged_hash
