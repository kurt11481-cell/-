#!/usr/bin/env python3
"""Pure CURRENT-only U.S. core-session authority derivation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from session_calendar_artifact import (
    CALENDAR_POLICY_IDENTITY,
    EXPECTED_OPERATING_MIC_SCOPE,
    TIMEZONE_IDENTITY,
    LoadedSessionCalendar,
    SessionCalendarLoadError,
    _load_active_session_calendar_from_root,
    load_active_session_calendar,
)


RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)
AUTHORITY_REASONS = {
    "OK",
    "INVALID_INPUT",
    "TEMPORAL_VIOLATION",
    "ARTIFACT_NOT_ACTIVATED",
    "INTEGRITY_FAILURE",
    "OUT_OF_COVERAGE",
    "WRONG_EXCHANGE_SCOPE",
    "TIMEZONE_NOT_VERIFIED",
    "CONFLICTING_CALENDAR",
}


@dataclass(frozen=True)
class SessionWindow:
    session_date: str
    core_open_at: str
    core_close_at: str
    close_type: str


@dataclass(frozen=True)
class SessionAuthorityView:
    contract_version: str
    authority_mode: str
    authority_status: str
    authority_reason: str
    calendar_policy_identity: str
    primary_listing_operating_mic: str | None
    operating_mic_scope: tuple[str, ...]
    timezone_identity: str
    calendar_version: str | None
    calendar_hash: str | None
    source_bundle_id: str | None
    coverage_start: str | None
    coverage_end: str | None
    authority_as_of: str | None
    activation_cohort_id: str | None
    observed_at: str
    decision_as_of: str
    current_et_date: str | None
    market_phase: str | None
    current_date_session: SessionWindow | None
    expected_completed_session: SessionWindow | None


def _strict_timestamp(value: str) -> datetime:
    text = str(value)
    if RFC3339_PATTERN.fullmatch(text) is None:
        raise ValueError("INVALID_RFC3339")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed


def _failure_view(
    reason: str,
    *,
    observed_at: str,
    decision_as_of: str,
    authority_mode: str,
    primary_listing_operating_mic: str | None,
    loaded: LoadedSessionCalendar | None = None,
    current_et_date: str | None = None,
    market_phase: str | None = None,
    current_date_session: SessionWindow | None = None,
) -> SessionAuthorityView:
    artifact = loaded.artifact if loaded is not None else {}
    return SessionAuthorityView(
        contract_version="2.0",
        authority_mode=authority_mode,
        authority_status="NOT_VERIFIED",
        authority_reason=reason if reason in AUTHORITY_REASONS else "INTEGRITY_FAILURE",
        calendar_policy_identity=str(
            artifact.get("calendar_policy_identity") or CALENDAR_POLICY_IDENTITY
        ),
        primary_listing_operating_mic=primary_listing_operating_mic,
        operating_mic_scope=tuple(
            artifact.get("operating_mic_scope") or EXPECTED_OPERATING_MIC_SCOPE
        ),
        timezone_identity=str(artifact.get("timezone_identity") or TIMEZONE_IDENTITY),
        calendar_version=artifact.get("calendar_version"),
        calendar_hash=loaded.calendar_hash if loaded is not None else None,
        source_bundle_id=artifact.get("source_bundle_id"),
        coverage_start=artifact.get("coverage_start"),
        coverage_end=artifact.get("coverage_end"),
        authority_as_of=artifact.get("authority_as_of"),
        activation_cohort_id=(
            loaded.activation.get("activation_cohort_id") if loaded is not None else None
        ),
        observed_at=observed_at,
        decision_as_of=decision_as_of,
        current_et_date=current_et_date,
        market_phase=market_phase,
        current_date_session=current_date_session,
        expected_completed_session=None,
    )


def _window(row: dict[str, str]) -> SessionWindow:
    return SessionWindow(
        session_date=row["session_date"],
        core_open_at=row["core_open_at"],
        core_close_at=row["core_close_at"],
        close_type=row["close_type"],
    )


def _derive(
    observed_at: str,
    *,
    primary_listing_operating_mic: str | None,
    decision_as_of: str | None,
    authority_mode: str,
    loader,
) -> SessionAuthorityView:
    cutoff_text = decision_as_of if decision_as_of is not None else observed_at
    if authority_mode != "CURRENT":
        return _failure_view(
            "INVALID_INPUT",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=str(authority_mode),
            primary_listing_operating_mic=primary_listing_operating_mic,
        )
    try:
        observed = _strict_timestamp(observed_at)
        cutoff = _strict_timestamp(cutoff_text)
    except (TypeError, ValueError):
        return _failure_view(
            "INVALID_INPUT",
            observed_at=str(observed_at),
            decision_as_of=str(cutoff_text),
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
        )
    if cutoff > observed:
        return _failure_view(
            "TEMPORAL_VIOLATION",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
        )
    try:
        loaded = loader()
    except SessionCalendarLoadError as exc:
        return _failure_view(
            exc.reason,
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
        )
    artifact = loaded.artifact
    activation = loaded.activation
    try:
        temporal_values = (
            _strict_timestamp(artifact["authority_as_of"]),
            _strict_timestamp(artifact["generated_at"]),
            _strict_timestamp(activation["activated_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return _failure_view(
            "INTEGRITY_FAILURE",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
            loaded=loaded,
        )
    if any(value > cutoff for value in temporal_values):
        return _failure_view(
            "TEMPORAL_VIOLATION",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
            loaded=loaded,
        )
    if primary_listing_operating_mic not in loaded.activation["operating_mic_scope"]:
        return _failure_view(
            "WRONG_EXCHANGE_SCOPE",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
            loaded=loaded,
        )
    try:
        et = ZoneInfo(TIMEZONE_IDENTITY)
    except ZoneInfoNotFoundError:
        return _failure_view(
            "TIMEZONE_NOT_VERIFIED",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
            loaded=loaded,
        )
    cutoff_et = cutoff.astimezone(et)
    current_date = cutoff_et.date()
    coverage_start = date.fromisoformat(artifact["coverage_start"])
    coverage_end = date.fromisoformat(artifact["coverage_end"])
    sessions = {row["session_date"]: row for row in artifact["sessions"]}
    current_row = sessions.get(current_date.isoformat())
    current_window = _window(current_row) if current_row is not None else None
    if current_row is None:
        market_phase = "NON_TRADING_DATE"
    else:
        opened = _strict_timestamp(current_row["core_open_at"])
        closed = _strict_timestamp(current_row["core_close_at"])
        if cutoff < opened:
            market_phase = "PRE_CORE"
        elif cutoff < closed:
            market_phase = "CORE_OPEN"
        else:
            market_phase = "POST_CORE"
    if not coverage_start <= current_date <= coverage_end:
        return _failure_view(
            "OUT_OF_COVERAGE",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
            loaded=loaded,
            current_et_date=current_date.isoformat(),
            market_phase=market_phase,
            current_date_session=current_window,
        )
    prior_rows = [row for row in artifact["sessions"] if row["session_date"] < current_date.isoformat()]
    if not prior_rows:
        return _failure_view(
            "OUT_OF_COVERAGE",
            observed_at=observed_at,
            decision_as_of=cutoff_text,
            authority_mode=authority_mode,
            primary_listing_operating_mic=primary_listing_operating_mic,
            loaded=loaded,
            current_et_date=current_date.isoformat(),
            market_phase=market_phase,
            current_date_session=current_window,
        )
    expected = _window(prior_rows[-1])
    return SessionAuthorityView(
        contract_version="2.0",
        authority_mode="CURRENT",
        authority_status="VERIFIED",
        authority_reason="OK",
        calendar_policy_identity=artifact["calendar_policy_identity"],
        primary_listing_operating_mic=primary_listing_operating_mic,
        operating_mic_scope=tuple(artifact["operating_mic_scope"]),
        timezone_identity=artifact["timezone_identity"],
        calendar_version=artifact["calendar_version"],
        calendar_hash=loaded.calendar_hash,
        source_bundle_id=artifact["source_bundle_id"],
        coverage_start=artifact["coverage_start"],
        coverage_end=artifact["coverage_end"],
        authority_as_of=artifact["authority_as_of"],
        activation_cohort_id=activation["activation_cohort_id"],
        observed_at=observed_at,
        decision_as_of=cutoff_text,
        current_et_date=current_date.isoformat(),
        market_phase=market_phase,
        current_date_session=current_window,
        expected_completed_session=expected,
    )


def _derive_us_market_session_authority_from_root(
    observed_at: str,
    *,
    primary_listing_operating_mic: str | None,
    trusted_root: Path,
    decision_as_of: str | None = None,
    authority_mode: Literal["CURRENT"] = "CURRENT",
) -> SessionAuthorityView:
    """Internal synthetic-fixture seam; never used by the production call graph."""
    return _derive(
        observed_at,
        primary_listing_operating_mic=primary_listing_operating_mic,
        decision_as_of=decision_as_of,
        authority_mode=authority_mode,
        loader=lambda: _load_active_session_calendar_from_root(trusted_root),
    )


def derive_us_market_session_authority(
    observed_at: str,
    *,
    primary_listing_operating_mic: str | None,
    decision_as_of: str | None = None,
    authority_mode: Literal["CURRENT"] = "CURRENT",
) -> SessionAuthorityView:
    """Derive CURRENT authority from only the fixed production activation path."""
    return _derive(
        observed_at,
        primary_listing_operating_mic=primary_listing_operating_mic,
        decision_as_of=decision_as_of,
        authority_mode=authority_mode,
        loader=load_active_session_calendar,
    )
