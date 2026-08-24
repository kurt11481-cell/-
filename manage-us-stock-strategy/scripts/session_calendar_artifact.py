#!/usr/bin/env python3
"""Read-only loader for the activated U.S. core-session calendar artifact."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from authority_artifact_io import (
    AuthorityArtifactIOError,
    canonical_json_bytes,
    decode_canonical_object,
    read_once_no_reparse,
)
from validation_common import validate_instance


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"
ACTIVATION_RELATIVE_PATH = Path("workspace/policies/session_calendar_activation.json")
ARTIFACT_DIRECTORY_RELATIVE_PATH = Path("workspace/calendar-authority/artifacts")
ARTIFACT_FILENAME = "us-equities-core-session-v2.calendar.json"
CALENDAR_POLICY_IDENTITY = "US_EQUITIES_CORE_SESSION_V2"
TIMEZONE_IDENTITY = "America/New_York"
EXPECTED_OPERATING_MIC_SCOPE = ("XNYS", "XNAS", "XCBO")
EXPECTED_SOURCE_FAMILIES = ("NYSE_GROUP", "NASDAQ", "CBOE")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


class SessionCalendarLoadError(ValueError):
    """A fail-closed calendar loading result with a public reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LoadedSessionCalendar:
    activation: dict[str, Any]
    artifact: dict[str, Any]
    calendar_hash: str


def _decode_canonical_object(raw: bytes) -> dict[str, Any]:
    try:
        return decode_canonical_object(raw)
    except AuthorityArtifactIOError as exc:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc


def _strict_timestamp(value: Any) -> datetime:
    text = str(value)
    if RFC3339_PATTERN.fullmatch(text) is None:
        raise ValueError("INVALID_RFC3339")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed


def _semantic_validate_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("calendar_policy_identity") != CALENDAR_POLICY_IDENTITY:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if artifact.get("timezone_identity") != TIMEZONE_IDENTITY:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if tuple(artifact.get("operating_mic_scope") or ()) != EXPECTED_OPERATING_MIC_SCOPE:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if tuple(artifact.get("source_families") or ()) != EXPECTED_SOURCE_FAMILIES:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if artifact.get("operating_mic_agreement_status") != "VERIFIED":
        raise SessionCalendarLoadError("CONFLICTING_CALENDAR")
    try:
        et = ZoneInfo(TIMEZONE_IDENTITY)
        coverage_start = date.fromisoformat(artifact["coverage_start"])
        coverage_end = date.fromisoformat(artifact["coverage_end"])
        authority_as_of = _strict_timestamp(artifact["authority_as_of"])
        generated_at = _strict_timestamp(artifact["generated_at"])
    except ZoneInfoNotFoundError as exc:
        raise SessionCalendarLoadError("TIMEZONE_NOT_VERIFIED") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc
    if coverage_start > coverage_end or generated_at < authority_as_of:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")

    session_dates: list[date] = []
    for row in artifact.get("sessions", []):
        try:
            session_date = date.fromisoformat(row["session_date"])
            opened = _strict_timestamp(row["core_open_at"])
            closed = _strict_timestamp(row["core_close_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc
        if not coverage_start <= session_date <= coverage_end or session_date.weekday() >= 5:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE")
        if opened >= closed:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE")
        opened_et = opened.astimezone(et)
        closed_et = closed.astimezone(et)
        if opened_et.date() != session_date or closed_et.date() != session_date:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE")
        if opened.utcoffset() != opened_et.utcoffset() or closed.utcoffset() != closed_et.utcoffset():
            raise SessionCalendarLoadError("INTEGRITY_FAILURE")
        session_dates.append(session_date)
    if session_dates != sorted(session_dates) or len(session_dates) != len(set(session_dates)):
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")

    closure_dates: list[date] = []
    for row in artifact.get("closures", []):
        try:
            closure_date = date.fromisoformat(row["closure_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc
        if not coverage_start <= closure_date <= coverage_end:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE")
        closure_dates.append(closure_date)
    if closure_dates != sorted(closure_dates) or len(closure_dates) != len(set(closure_dates)):
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if set(session_dates) & set(closure_dates):
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")

    classified = set(session_dates) | set(closure_dates)
    current = coverage_start
    while current <= coverage_end:
        if current.weekday() < 5 and current not in classified:
            raise SessionCalendarLoadError("INTEGRITY_FAILURE")
        current += timedelta(days=1)


def _validate_binding(activation: dict[str, Any], artifact: dict[str, Any]) -> None:
    bindings = (
        ("calendar_policy_identity", "calendar_policy_identity"),
        ("active_calendar_version", "calendar_version"),
        ("timezone_identity", "timezone_identity"),
        ("operating_mic_scope", "operating_mic_scope"),
        ("source_families", "source_families"),
        ("coverage_start", "coverage_start"),
        ("coverage_end", "coverage_end"),
        ("source_bundle_id", "source_bundle_id"),
        ("source_bundle_hash", "source_bundle_hash"),
        ("authority_as_of", "authority_as_of"),
    )
    if any(activation.get(left) != artifact.get(right) for left, right in bindings):
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if activation.get("authority_modes_allowed") != ["CURRENT"]:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    try:
        authority_as_of = _strict_timestamp(artifact["authority_as_of"])
        generated_at = _strict_timestamp(artifact["generated_at"])
        activated_at = _strict_timestamp(activation["activated_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc
    if not authority_as_of <= generated_at <= activated_at:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")


def _load_active_session_calendar_from_root(trusted_root: Path) -> LoadedSessionCalendar:
    """Internal fixture seam. Production callers use load_active_session_calendar()."""
    trusted = Path(trusted_root)
    activation_path = trusted / ACTIVATION_RELATIVE_PATH
    try:
        activation_raw = read_once_no_reparse(activation_path, trusted)
    except FileNotFoundError as exc:
        raise SessionCalendarLoadError("ARTIFACT_NOT_ACTIVATED") from exc
    except (AuthorityArtifactIOError, OSError) as exc:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc
    activation = _decode_canonical_object(activation_raw)
    if validate_instance(activation, SCHEMA_ROOT / "session-calendar-activation.schema.json"):
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    if activation.get("activation_status") != "ACTIVE":
        raise SessionCalendarLoadError("ARTIFACT_NOT_ACTIVATED")
    if activation.get("activation_reason_code") == "CONFLICTING_CALENDAR":
        raise SessionCalendarLoadError("CONFLICTING_CALENDAR")
    active_hash = str(activation.get("active_calendar_hash") or "")
    if HASH_PATTERN.fullmatch(active_hash) is None:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    artifact_path = (
        trusted / ARTIFACT_DIRECTORY_RELATIVE_PATH / active_hash / ARTIFACT_FILENAME
    )
    try:
        artifact_raw = read_once_no_reparse(artifact_path, trusted)
    except (FileNotFoundError, AuthorityArtifactIOError, OSError) as exc:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE") from exc
    artifact_hash = hashlib.sha256(artifact_raw).hexdigest()
    if artifact_hash != active_hash:
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    artifact = _decode_canonical_object(artifact_raw)
    if validate_instance(artifact, SCHEMA_ROOT / "session-calendar-artifact.schema.json"):
        raise SessionCalendarLoadError("INTEGRITY_FAILURE")
    _semantic_validate_artifact(artifact)
    _validate_binding(activation, artifact)
    return LoadedSessionCalendar(
        activation=activation,
        artifact=artifact,
        calendar_hash=artifact_hash,
    )


def load_active_session_calendar() -> LoadedSessionCalendar:
    """Load only the fixed production activation and hash-derived artifact path."""
    return _load_active_session_calendar_from_root(ROOT)
