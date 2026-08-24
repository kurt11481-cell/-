#!/usr/bin/env python3
"""CURRENT-only trusted Instrument Identity resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from instrument_identity_artifact import (
    AUTHORITY_ID,
    TICKER_NAMESPACE,
    InstrumentIdentityLoadError,
    LoadedInstrumentIdentityRegistry,
    _load_active_instrument_identity_from_root,
    load_active_instrument_identity,
)


RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)
TICKER_PATTERN = re.compile(r"[A-Z][A-Z0-9.]{0,9}")
MIC_PATTERN = re.compile(r"[A-Z]{4}")
IDENTITY_REASONS = {
    "OK",
    "INVALID_INPUT",
    "ARTIFACT_NOT_ACTIVATED",
    "UNKNOWN_SYMBOL",
    "AMBIGUOUS_SECURITY",
    "OUT_OF_EFFECTIVE_RANGE",
    "PRIMARY_MIC_NOT_VERIFIED",
    "INTEGRITY_FAILURE",
    "TEMPORAL_VIOLATION",
}


@dataclass(frozen=True)
class InstrumentIdentityView:
    authority_status: str
    authority_reason: str
    authority_id: str | None
    registry_version: str | None
    registry_hash: str | None
    activation_cohort_id: str | None
    ticker_namespace: str | None
    ticker: str | None
    security_name: str | None
    instrument_type: str | None
    security_class: str | None
    primary_listing_venue_name: str | None
    primary_listing_segment_mic: str | None
    primary_listing_operating_mic: str | None
    effective_from: str | None
    effective_from_basis: str | None
    effective_to: str | None
    authority_as_of: str | None
    source_packet_id: str | None
    source_packet_hash: str | None
    source_ref_ids: tuple[str, ...]
    decision_as_of: str
    order_authority: bool = False


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
    decision_as_of: str,
    ticker: str | None = None,
    loaded: LoadedInstrumentIdentityRegistry | None = None,
) -> InstrumentIdentityView:
    artifact = loaded.artifact if loaded is not None else {}
    activation = loaded.activation if loaded is not None else {}
    return InstrumentIdentityView(
        authority_status="NOT_VERIFIED",
        authority_reason=reason if reason in IDENTITY_REASONS else "INTEGRITY_FAILURE",
        authority_id=str(artifact.get("authority_id") or AUTHORITY_ID),
        registry_version=artifact.get("registry_version"),
        registry_hash=loaded.registry_hash if loaded is not None else None,
        activation_cohort_id=activation.get("activation_cohort_id"),
        ticker_namespace=str(artifact.get("ticker_namespace") or TICKER_NAMESPACE),
        ticker=ticker,
        security_name=None,
        instrument_type=None,
        security_class=None,
        primary_listing_venue_name=None,
        primary_listing_segment_mic=None,
        primary_listing_operating_mic=None,
        effective_from=None,
        effective_from_basis=None,
        effective_to=None,
        authority_as_of=artifact.get("authority_as_of"),
        source_packet_id=artifact.get("source_packet_id"),
        source_packet_hash=artifact.get("source_packet_hash"),
        source_ref_ids=(),
        decision_as_of=decision_as_of,
    )


def _resolve(
    ticker: str,
    *,
    decision_as_of: str,
    authority_mode: str,
    loader,
) -> InstrumentIdentityView:
    safe_ticker = ticker if isinstance(ticker, str) and TICKER_PATTERN.fullmatch(ticker) else None
    if authority_mode != "CURRENT" or safe_ticker is None:
        return _failure_view(
            "INVALID_INPUT",
            decision_as_of=str(decision_as_of),
            ticker=safe_ticker,
        )
    try:
        cutoff = _strict_timestamp(decision_as_of)
    except (TypeError, ValueError):
        return _failure_view("INVALID_INPUT", decision_as_of=str(decision_as_of), ticker=safe_ticker)
    try:
        loaded = loader()
    except InstrumentIdentityLoadError as exc:
        return _failure_view(exc.reason, decision_as_of=decision_as_of, ticker=safe_ticker)
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
            "INTEGRITY_FAILURE", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    if any(value > cutoff for value in temporal_values):
        return _failure_view(
            "TEMPORAL_VIOLATION", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    if safe_ticker not in artifact["scope"]:
        return _failure_view(
            "UNKNOWN_SYMBOL", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    matches = [record for record in artifact["records"] if record.get("ticker") == safe_ticker]
    if not matches:
        return _failure_view(
            "UNKNOWN_SYMBOL", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    if len(matches) != 1:
        return _failure_view(
            "AMBIGUOUS_SECURITY", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    record = matches[0]
    cutoff_date = cutoff.date()
    effective_from = record.get("effective_from")
    effective_to = record.get("effective_to")
    if effective_from is not None and cutoff_date < date.fromisoformat(effective_from):
        return _failure_view(
            "OUT_OF_EFFECTIVE_RANGE", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    if effective_to is not None and cutoff_date > date.fromisoformat(effective_to):
        return _failure_view(
            "OUT_OF_EFFECTIVE_RANGE", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    operating_mic = record.get("primary_listing_operating_mic")
    if not isinstance(operating_mic, str) or MIC_PATTERN.fullmatch(operating_mic) is None:
        return _failure_view(
            "PRIMARY_MIC_NOT_VERIFIED", decision_as_of=decision_as_of, ticker=safe_ticker, loaded=loaded
        )
    return InstrumentIdentityView(
        authority_status="VERIFIED",
        authority_reason="OK",
        authority_id=artifact["authority_id"],
        registry_version=artifact["registry_version"],
        registry_hash=loaded.registry_hash,
        activation_cohort_id=activation["activation_cohort_id"],
        ticker_namespace=artifact["ticker_namespace"],
        ticker=record["ticker"],
        security_name=record["security_name"],
        instrument_type=record["instrument_type"],
        security_class=record["security_class"],
        primary_listing_venue_name=record["primary_listing_venue_name"],
        primary_listing_segment_mic=record["primary_listing_segment_mic"],
        primary_listing_operating_mic=operating_mic,
        effective_from=effective_from,
        effective_from_basis=record["effective_from_basis"],
        effective_to=effective_to,
        authority_as_of=artifact["authority_as_of"],
        source_packet_id=artifact["source_packet_id"],
        source_packet_hash=artifact["source_packet_hash"],
        source_ref_ids=tuple(record["source_ref_ids"]),
        decision_as_of=decision_as_of,
    )


def _resolve_instrument_identity_from_root(
    ticker: str,
    *,
    trusted_root: Path,
    decision_as_of: str,
    authority_mode: Literal["CURRENT"] = "CURRENT",
) -> InstrumentIdentityView:
    """Resolve through the fixed-layout temporary-root seam used by synthetic tests."""
    return _resolve(
        ticker,
        decision_as_of=decision_as_of,
        authority_mode=authority_mode,
        loader=lambda: _load_active_instrument_identity_from_root(trusted_root),
    )


def resolve_instrument_identity(
    ticker: str,
    *,
    decision_as_of: str | None = None,
    authority_mode: Literal["CURRENT"] = "CURRENT",
) -> InstrumentIdentityView:
    """Resolve exact canonical ticker identity from fixed activated authority only."""
    cutoff = decision_as_of or datetime.now(timezone.utc).isoformat()
    return _resolve(
        ticker,
        decision_as_of=cutoff,
        authority_mode=authority_mode,
        loader=load_active_instrument_identity,
    )
