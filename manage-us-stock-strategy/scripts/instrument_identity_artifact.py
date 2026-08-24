#!/usr/bin/env python3
"""Read-only loader for the activated Instrument Identity registry."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from authority_artifact_io import (
    AuthorityArtifactIOError,
    decode_canonical_object,
    read_once_no_reparse,
)
from validation_common import validate_instance


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"
ACTIVATION_RELATIVE_PATH = Path("workspace/policies/instrument_identity_activation.json")
ARTIFACT_DIRECTORY_RELATIVE_PATH = Path("workspace/instrument-identity-authority/artifacts")
ARTIFACT_FILENAME = "us-equity-instrument-identity-current-v1.registry.json"
AUTHORITY_ID = "US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1"
TICKER_NAMESPACE = "US_EXCHANGE_LISTED"
EXPECTED_SCOPE = ("BE", "DRAM", "FSLY", "MVLL", "NBIS", "NOW", "SOXL", "TOST")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)
MIC_PATTERN = re.compile(r"[A-Z]{4}")
ACCEPTED_EXPLICIT_MIC_PAIRS = {
    ("XNYS", "XNYS"),
    ("ARCX", "XNYS"),
    ("BATS", "XCBO"),
    ("XNGS", "XNAS"),
    ("XNMS", "XNAS"),
}
EQUITY_SECURITY_CLASSES = {
    "COMMON_STOCK",
    "CLASS_A_COMMON_STOCK",
    "CLASS_A_ORDINARY_SHARES",
}
ETF_SECURITY_CLASSES = {"ACTIVELY_MANAGED_ETF", "LEVERAGED_ETF"}


class InstrumentIdentityLoadError(ValueError):
    """A fail-closed registry loading result with a public reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LoadedInstrumentIdentityRegistry:
    activation: dict[str, Any]
    artifact: dict[str, Any]
    registry_hash: str


def _strict_timestamp(value: Any) -> datetime:
    text = str(value)
    if RFC3339_PATTERN.fullmatch(text) is None:
        raise ValueError("INVALID_RFC3339")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed


def _semantic_validate_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("authority_id") != AUTHORITY_ID:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    if artifact.get("ticker_namespace") != TICKER_NAMESPACE:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    if tuple(artifact.get("scope") or ()) != EXPECTED_SCOPE:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    if artifact.get("order_authority") is not False:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    try:
        authority_as_of = _strict_timestamp(artifact["authority_as_of"])
        generated_at = _strict_timestamp(artifact["generated_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
    if generated_at < authority_as_of:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")

    records = artifact.get("records")
    if not isinstance(records, list):
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    tickers = [record.get("ticker") for record in records if isinstance(record, dict)]
    if tickers != sorted(tickers) or tuple(tickers) != EXPECTED_SCOPE:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    if len(tickers) != len(set(tickers)):
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")

    authority_date = authority_as_of.date()
    for record in records:
        try:
            ticker = record["ticker"]
            segment_mic = record["primary_listing_segment_mic"]
            operating_mic = record["primary_listing_operating_mic"]
            instrument_type = record["instrument_type"]
            security_class = record["security_class"]
            effective_from = record["effective_from"]
            effective_from_basis = record["effective_from_basis"]
            effective_to = record["effective_to"]
            source_ref_ids = record["source_ref_ids"]
        except (KeyError, TypeError) as exc:
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
        if ticker not in EXPECTED_SCOPE or record.get("record_status") != "VERIFIED":
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        if MIC_PATTERN.fullmatch(str(segment_mic)) is None:
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        if MIC_PATTERN.fullmatch(str(operating_mic)) is None:
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        if (segment_mic, operating_mic) not in ACCEPTED_EXPLICIT_MIC_PAIRS:
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        allowed_classes = (
            EQUITY_SECURITY_CLASSES if instrument_type == "EQUITY" else ETF_SECURITY_CLASSES
        )
        if security_class not in allowed_classes:
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        if effective_from_basis == "CURRENT_AS_OF_ONLY":
            if effective_from is not None:
                raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
            start_date = None
        elif effective_from_basis == "VERIFIED_DATE":
            try:
                start_date = date.fromisoformat(effective_from)
            except (TypeError, ValueError) as exc:
                raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
            if start_date > authority_date:
                raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        else:
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        if effective_to is not None:
            try:
                end_date = date.fromisoformat(effective_to)
            except (TypeError, ValueError) as exc:
                raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
            if (start_date is not None and end_date < start_date) or end_date < authority_date:
                raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
        if not source_ref_ids or len(source_ref_ids) != len(set(source_ref_ids)):
            raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")


def _validate_binding(activation: dict[str, Any], artifact: dict[str, Any]) -> None:
    bindings = (
        ("authority_id", "authority_id"),
        ("active_registry_version", "registry_version"),
        ("ticker_namespace", "ticker_namespace"),
        ("scope", "scope"),
        ("source_packet_id", "source_packet_id"),
        ("source_packet_hash", "source_packet_hash"),
        ("authority_as_of", "authority_as_of"),
    )
    if any(activation.get(left) != artifact.get(right) for left, right in bindings):
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    if activation.get("authority_modes_allowed") != ["CURRENT"]:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    try:
        authority_as_of = _strict_timestamp(artifact["authority_as_of"])
        generated_at = _strict_timestamp(artifact["generated_at"])
        activated_at = _strict_timestamp(activation["activated_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
    if not authority_as_of <= generated_at <= activated_at:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")


def _load_active_instrument_identity_from_root(
    trusted_root: Path,
) -> LoadedInstrumentIdentityRegistry:
    """Internal fixed-layout fixture seam; production callers use the public loader."""
    activation_path = trusted_root / ACTIVATION_RELATIVE_PATH
    try:
        activation_raw = read_once_no_reparse(activation_path, trusted_root)
    except FileNotFoundError as exc:
        raise InstrumentIdentityLoadError("ARTIFACT_NOT_ACTIVATED") from exc
    except (AuthorityArtifactIOError, OSError) as exc:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
    try:
        activation = decode_canonical_object(activation_raw)
    except AuthorityArtifactIOError as exc:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
    if validate_instance(activation, SCHEMA_ROOT / "instrument-identity-activation.schema.json"):
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    if activation.get("activation_status") != "ACTIVE":
        raise InstrumentIdentityLoadError("ARTIFACT_NOT_ACTIVATED")
    if activation.get("activation_reason_code") == "IDENTITY_CONFLICT":
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    active_hash = str(activation.get("active_registry_hash") or "")
    if HASH_PATTERN.fullmatch(active_hash) is None:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    artifact_path = (
        trusted_root / ARTIFACT_DIRECTORY_RELATIVE_PATH / active_hash / ARTIFACT_FILENAME
    )
    try:
        artifact_raw = read_once_no_reparse(artifact_path, trusted_root)
    except (FileNotFoundError, AuthorityArtifactIOError, OSError) as exc:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
    registry_hash = hashlib.sha256(artifact_raw).hexdigest()
    if registry_hash != active_hash:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    try:
        artifact = decode_canonical_object(artifact_raw)
    except AuthorityArtifactIOError as exc:
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE") from exc
    if validate_instance(artifact, SCHEMA_ROOT / "instrument-identity-artifact.schema.json"):
        raise InstrumentIdentityLoadError("INTEGRITY_FAILURE")
    _semantic_validate_artifact(artifact)
    _validate_binding(activation, artifact)
    return LoadedInstrumentIdentityRegistry(
        activation=activation,
        artifact=artifact,
        registry_hash=registry_hash,
    )


def load_active_instrument_identity() -> LoadedInstrumentIdentityRegistry:
    """Load only the fixed production activation and hash-derived registry path."""
    return _load_active_instrument_identity_from_root(ROOT)
