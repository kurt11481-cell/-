#!/usr/bin/env python3
"""Validate official calendar evidence and create inactive immutable candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from authority_artifact_io import canonical_json_bytes
from materialize_instrument_identity_artifact import (
    MaterializationError as CreateOnlyWriteError,
    _create_only_write,
)
from session_calendar_artifact import _semantic_validate_artifact
from validation_common import validate_instance


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SCHEMA_ROOT = SCRIPT_DIR.parent / "schemas"

CALENDAR_POLICY_IDENTITY = "US_EQUITIES_CORE_SESSION_V2"
TIMEZONE_IDENTITY = "America/New_York"
EXPECTED_OPERATING_MIC_SCOPE = ("XNYS", "XNAS", "XCBO")
EXPECTED_SOURCE_FAMILIES = ("NYSE_GROUP", "NASDAQ", "CBOE")
FAMILY_TO_MIC = dict(zip(EXPECTED_SOURCE_FAMILIES, EXPECTED_OPERATING_MIC_SCOPE))
OFFICIAL_HOSTS = {
    "NYSE_GROUP": {"www.nyse.com", "nyse.com"},
    "NASDAQ": {"www.nasdaqtrader.com", "nasdaqtrader.com", "www.nasdaq.com", "nasdaq.com"},
    "CBOE": {"www.cboe.com", "cboe.com", "cdn.cboe.com"},
}

SOURCE_BUNDLE_FILENAME = "us-equities-core-session-v2.sources.json"
ARTIFACT_FILENAME = "us-equities-core-session-v2.calendar.json"
SOURCE_BUNDLE_DIRECTORY = Path("workspace/calendar-authority/source-bundles")
ARTIFACT_DIRECTORY = Path("workspace/calendar-authority/artifacts")
ACTIVATION_RELATIVE_PATH = Path("workspace/policies/session_calendar_activation.json")
HASH_RE = re.compile(r"[0-9a-f]{64}")
TIME_RE = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]")


class CalendarMaterializationError(ValueError):
    """Fail-closed materialization error with a stable reason code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CalendarMaterializationResult:
    evidence_packet_path: Path
    evidence_packet_sha256: str
    evidence_packet_write_status: str
    candidate_artifact_path: Path
    candidate_artifact_sha256: str
    candidate_artifact_write_status: str
    source_bundle_id: str
    calendar_version: str
    coverage_start: str
    coverage_end: str
    source_count: int
    claim_count: int
    claim_source_edge_count: int
    session_count: int
    closure_count: int
    activation_unchanged: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "MATERIALIZED_INACTIVE_CANDIDATE",
            "evidence_packet_path": str(self.evidence_packet_path),
            "evidence_packet_sha256": self.evidence_packet_sha256,
            "evidence_packet_write_status": self.evidence_packet_write_status,
            "candidate_artifact_path": str(self.candidate_artifact_path),
            "candidate_artifact_sha256": self.candidate_artifact_sha256,
            "candidate_artifact_write_status": self.candidate_artifact_write_status,
            "source_bundle_id": self.source_bundle_id,
            "calendar_version": self.calendar_version,
            "coverage_start": self.coverage_start,
            "coverage_end": self.coverage_end,
            "source_count": self.source_count,
            "claim_count": self.claim_count,
            "claim_source_edge_count": self.claim_source_edge_count,
            "session_count": self.session_count,
            "closure_count": self.closure_count,
            "activation_unchanged": self.activation_unchanged,
            "ready_for_activation": False,
        }


def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", field) from exc


def _parse_timestamp(value: Any, field: str) -> datetime:
    text = str(value)
    if not text.endswith("Z") and not re.search(r"[+-][0-9]{2}:[0-9]{2}$", text):
        raise CalendarMaterializationError("INTEGRITY_FAILURE", field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", field) from exc
    if parsed.tzinfo is None:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", field)
    return parsed


def _require_exact_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    if set(value) != expected:
        raise CalendarMaterializationError(
            "INTEGRITY_FAILURE",
            f"{field} keys missing={sorted(expected - set(value))} extra={sorted(set(value) - expected)}",
        )


def _official_source_summary(sources: list[dict[str, Any]]) -> tuple[str, str]:
    statuses = {source["content_capture_status"] for source in sources}
    if statuses == {"CAPTURED"}:
        return "YES", "VERIFIED"
    if statuses == {"NOT_CAPTURED"}:
        return "NO", "NOT_CAPTURED"
    return "MIXED", "MIXED"


def _validate_source(source: dict[str, Any], authority_date: date) -> None:
    expected = {
        "source_id",
        "source_family",
        "operating_mic",
        "official_url",
        "title",
        "retrieved_date",
        "retrieval_time_basis",
        "content_capture_status",
        "content_sha256",
        "source_scope",
        "effective_from",
        "effective_to",
        "source_effective_basis",
    }
    _require_exact_keys(source, expected, f"source:{source.get('source_id')}")
    family = source["source_family"]
    if family not in FAMILY_TO_MIC or source["operating_mic"] != FAMILY_TO_MIC[family]:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "source family/MIC")
    parsed_url = urlsplit(source["official_url"])
    if parsed_url.scheme != "https" or parsed_url.hostname not in OFFICIAL_HOSTS[family]:
        raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"non-official source host:{family}")
    if not source["source_id"] or not source["title"] or not source["retrieval_time_basis"]:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "source identity")
    if _parse_date(source["retrieved_date"], "retrieved_date") > authority_date:
        raise CalendarMaterializationError("TEMPORAL_VIOLATION", source["source_id"])
    capture = source["content_capture_status"]
    content_hash = source["content_sha256"]
    if capture == "NOT_CAPTURED" and content_hash is not None:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "dishonest content hash")
    if capture == "CAPTURED" and (not isinstance(content_hash, str) or HASH_RE.fullmatch(content_hash) is None):
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "missing captured content hash")
    scopes = source["source_scope"]
    if not isinstance(scopes, list) or not scopes or len(scopes) != len(set(scopes)):
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "source_scope")
    if not set(scopes).issubset({"REGULAR_HOURS", "HOLIDAYS", "EARLY_CLOSES"}):
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "source_scope")


def _local_timestamp(session_date: date, clock: str, et: ZoneInfo) -> str:
    if TIME_RE.fullmatch(clock) is None:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", f"clock:{clock}")
    hour, minute, second = (int(part) for part in clock.split(":"))
    return datetime.combine(session_date, time(hour, minute, second), tzinfo=et).isoformat(timespec="seconds")


def _validate_reviewed_packet(packet: dict[str, Any]) -> tuple[date, date, datetime, dict[str, dict[str, Any]]]:
    top_keys = {
        "packet_schema_version",
        "packet_identity",
        "calendar_policy_identity",
        "timezone_identity",
        "authority_as_of",
        "authority_as_of_time_basis",
        "generated_at",
        "coverage_start",
        "coverage_end",
        "calendar_version",
        "operating_mic_scope",
        "source_families",
        "sources",
        "calendars",
    }
    _require_exact_keys(packet, top_keys, "packet")
    if packet["packet_schema_version"] != "1.0" or packet["calendar_policy_identity"] != CALENDAR_POLICY_IDENTITY:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "packet identity")
    if packet["timezone_identity"] != TIMEZONE_IDENTITY:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "timezone")
    if tuple(packet["operating_mic_scope"]) != EXPECTED_OPERATING_MIC_SCOPE:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "operating MIC scope")
    if tuple(packet["source_families"]) != EXPECTED_SOURCE_FAMILIES:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "source families")
    coverage_start = _parse_date(packet["coverage_start"], "coverage_start")
    coverage_end = _parse_date(packet["coverage_end"], "coverage_end")
    if coverage_start > coverage_end:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "coverage")
    authority_as_of = _parse_timestamp(packet["authority_as_of"], "authority_as_of")
    generated_at = _parse_timestamp(packet["generated_at"], "generated_at")
    if generated_at < authority_as_of:
        raise CalendarMaterializationError("TEMPORAL_VIOLATION", "generated_at")
    et = ZoneInfo(TIMEZONE_IDENTITY)
    sources = packet["sources"]
    if not isinstance(sources, list) or len(sources) < 3:
        raise CalendarMaterializationError("SOURCE_UNAVAILABLE", "official sources")
    source_ids = [source.get("source_id") for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "duplicate source_id")
    source_by_id = {source["source_id"]: source for source in sources}
    for source in sources:
        _validate_source(source, authority_as_of.date())
        if _parse_date(source["effective_from"], "effective_from") > coverage_start:
            raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"coverage start:{source['source_id']}")
        if _parse_date(source["effective_to"], "effective_to") < coverage_end:
            raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"coverage end:{source['source_id']}")
    if {source["source_family"] for source in sources} != set(EXPECTED_SOURCE_FAMILIES):
        raise CalendarMaterializationError("SOURCE_UNAVAILABLE", "source family")

    calendars = packet["calendars"]
    if not isinstance(calendars, list) or len(calendars) != 3:
        raise CalendarMaterializationError("SOURCE_UNAVAILABLE", "calendar families")
    by_family: dict[str, dict[str, Any]] = {}
    calendar_keys = {
        "source_family",
        "operating_mic",
        "source_ids",
        "regular_open",
        "regular_close",
        "closures",
        "early_closes",
    }
    dated_keys = {"session_date", "label"}
    early_keys = {"session_date", "label", "core_close"}
    for calendar in calendars:
        _require_exact_keys(calendar, calendar_keys, "calendar")
        family = calendar["source_family"]
        if family in by_family or FAMILY_TO_MIC.get(family) != calendar["operating_mic"]:
            raise CalendarMaterializationError("INTEGRITY_FAILURE", "calendar family/MIC")
        refs = calendar["source_ids"]
        if not refs or len(refs) != len(set(refs)):
            raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"source refs:{family}")
        capabilities: set[str] = set()
        for source_id in refs:
            source = source_by_id.get(source_id)
            if source is None or source["source_family"] != family:
                raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"source ref:{source_id}")
            capabilities.update(source["source_scope"])
        if not {"REGULAR_HOURS", "HOLIDAYS"}.issubset(capabilities):
            raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"source capability:{family}")
        _local_timestamp(coverage_start, calendar["regular_open"], et)
        _local_timestamp(coverage_start, calendar["regular_close"], et)
        if calendar["regular_open"] >= calendar["regular_close"]:
            raise CalendarMaterializationError("INTEGRITY_FAILURE", f"regular hours:{family}")
        seen: set[str] = set()
        for closed in calendar["closures"]:
            _require_exact_keys(closed, dated_keys, "closure")
            closed_date = _parse_date(closed["session_date"], "closure date")
            if not coverage_start <= closed_date <= coverage_end or closed_date.weekday() >= 5:
                raise CalendarMaterializationError("INTEGRITY_FAILURE", f"closure:{closed_date}")
            if closed["session_date"] in seen or not closed["label"]:
                raise CalendarMaterializationError("INTEGRITY_FAILURE", f"duplicate closure:{closed_date}")
            seen.add(closed["session_date"])
        if calendar["early_closes"] and "EARLY_CLOSES" not in capabilities:
            raise CalendarMaterializationError("SOURCE_UNAVAILABLE", f"early close capability:{family}")
        for early in calendar["early_closes"]:
            _require_exact_keys(early, early_keys, "early_close")
            early_date = _parse_date(early["session_date"], "early close date")
            if not coverage_start <= early_date <= coverage_end or early_date.weekday() >= 5:
                raise CalendarMaterializationError("INTEGRITY_FAILURE", f"early close:{early_date}")
            if early["session_date"] in seen or not early["label"]:
                raise CalendarMaterializationError("INTEGRITY_FAILURE", f"duplicate day:{early_date}")
            _local_timestamp(early_date, early["core_close"], et)
            if not calendar["regular_open"] < early["core_close"] < calendar["regular_close"]:
                raise CalendarMaterializationError("INTEGRITY_FAILURE", f"early close clock:{family}")
            seen.add(early["session_date"])
        by_family[family] = calendar
    if tuple(by_family) != EXPECTED_SOURCE_FAMILIES:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "calendar order")
    return coverage_start, coverage_end, authority_as_of, source_by_id


def _build_claims(packet: dict[str, Any], coverage_start: date, coverage_end: date) -> list[dict[str, Any]]:
    et = ZoneInfo(TIMEZONE_IDENTITY)
    claims: list[dict[str, Any]] = []
    for calendar in packet["calendars"]:
        family = calendar["source_family"]
        mic = calendar["operating_mic"]
        closures = {row["session_date"]: row for row in calendar["closures"]}
        early_closes = {row["session_date"]: row for row in calendar["early_closes"]}
        current = coverage_start
        while current <= coverage_end:
            if current.weekday() < 5:
                day = current.isoformat()
                claim = {
                    "claim_id": f"{family}:{day}",
                    "source_family": family,
                    "operating_mic": mic,
                    "session_date": day,
                    "is_session": day not in closures,
                    "core_open_at": None,
                    "core_close_at": None,
                    "close_type": None,
                    "closure_label": None,
                    "source_ids": list(calendar["source_ids"]),
                }
                if day in closures:
                    claim["closure_label"] = closures[day]["label"]
                else:
                    claim["core_open_at"] = _local_timestamp(current, calendar["regular_open"], et)
                    if day in early_closes:
                        claim["core_close_at"] = _local_timestamp(current, early_closes[day]["core_close"], et)
                        claim["close_type"] = "EARLY"
                    else:
                        claim["core_close_at"] = _local_timestamp(current, calendar["regular_close"], et)
                        claim["close_type"] = "REGULAR"
                claims.append(claim)
            current += timedelta(days=1)
    return claims


def _common_calendar(claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_day: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_day.setdefault(claim["session_date"], []).append(claim)
    sessions: list[dict[str, Any]] = []
    closures: list[dict[str, Any]] = []
    decision_fields = ("is_session", "core_open_at", "core_close_at", "close_type")
    for session_date in sorted(by_day):
        rows = by_day[session_date]
        if tuple(row["source_family"] for row in rows) != EXPECTED_SOURCE_FAMILIES:
            raise CalendarMaterializationError("CALENDAR_CONFLICT", f"missing family:{session_date}")
        baseline = tuple(rows[0][field] for field in decision_fields)
        if any(tuple(row[field] for field in decision_fields) != baseline for row in rows[1:]):
            raise CalendarMaterializationError("CALENDAR_CONFLICT", session_date)
        if rows[0]["is_session"]:
            sessions.append(
                {
                    "session_date": session_date,
                    "core_open_at": rows[0]["core_open_at"],
                    "core_close_at": rows[0]["core_close_at"],
                    "close_type": rows[0]["close_type"],
                }
            )
        else:
            closures.append({"closure_date": session_date})
    return sessions, closures


def build_materialization(
    packet: dict[str, Any],
) -> tuple[bytes, str, dict[str, Any], bytes, str, dict[str, int]]:
    coverage_start, coverage_end, _authority_as_of, _sources = _validate_reviewed_packet(packet)
    claims = _build_claims(packet, coverage_start, coverage_end)
    sessions, closures = _common_calendar(claims)
    edges = [
        {"claim_id": claim["claim_id"], "source_id": source_id}
        for claim in claims
        for source_id in claim["source_ids"]
    ]
    bytes_status, hash_status = _official_source_summary(packet["sources"])
    bundle = {
        "source_bundle_schema_version": "1.0",
        "source_bundle_id": packet["packet_identity"],
        "calendar_policy_identity": CALENDAR_POLICY_IDENTITY,
        "timezone_identity": TIMEZONE_IDENTITY,
        "authority_as_of": packet["authority_as_of"],
        "authority_as_of_time_basis": packet["authority_as_of_time_basis"],
        "generated_at": packet["generated_at"],
        "coverage_start": packet["coverage_start"],
        "coverage_end": packet["coverage_end"],
        "operating_mic_scope": list(EXPECTED_OPERATING_MIC_SCOPE),
        "source_families": list(EXPECTED_SOURCE_FAMILIES),
        "source_content_bytes_captured": bytes_status,
        "source_content_hash_status": hash_status,
        "official_sources": packet["sources"],
        "calendar_claims": claims,
        "claim_source_edges": edges,
        "operating_mic_agreement_status": "VERIFIED",
        "conflicts": [],
    }
    bundle_errors = validate_instance(bundle, SCHEMA_ROOT / "session-calendar-source-bundle.schema.json")
    if bundle_errors:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "; ".join(bundle_errors[:4]))
    bundle_bytes = canonical_json_bytes(bundle)
    bundle_hash = hashlib.sha256(bundle_bytes).hexdigest()
    artifact = {
        "artifact_schema_version": "2.0",
        "calendar_policy_identity": CALENDAR_POLICY_IDENTITY,
        "timezone_identity": TIMEZONE_IDENTITY,
        "operating_mic_scope": list(EXPECTED_OPERATING_MIC_SCOPE),
        "source_families": list(EXPECTED_SOURCE_FAMILIES),
        "coverage_start": packet["coverage_start"],
        "coverage_end": packet["coverage_end"],
        "source_bundle_id": packet["packet_identity"],
        "source_bundle_hash": bundle_hash,
        "calendar_version": packet["calendar_version"],
        "generated_at": packet["generated_at"],
        "authority_as_of": packet["authority_as_of"],
        "operating_mic_agreement_status": "VERIFIED",
        "sessions": sessions,
        "closures": closures,
    }
    artifact_errors = validate_instance(artifact, SCHEMA_ROOT / "session-calendar-artifact.schema.json")
    if artifact_errors:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "; ".join(artifact_errors[:4]))
    try:
        _semantic_validate_artifact(artifact)
    except Exception as exc:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", f"candidate loader:{exc}") from exc
    artifact_bytes = canonical_json_bytes(artifact)
    artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
    return (
        bundle_bytes,
        bundle_hash,
        artifact,
        artifact_bytes,
        artifact_hash,
        {
            "source_count": len(packet["sources"]),
            "claim_count": len(claims),
            "claim_source_edge_count": len(edges),
            "session_count": len(sessions),
            "closure_count": len(closures),
        },
    )


def _activation_fingerprint(trusted_root: Path) -> tuple[str, str | None]:
    activation = Path(os.path.abspath(os.fspath(trusted_root))) / ACTIVATION_RELATIVE_PATH
    if not activation.exists() and not activation.is_symlink():
        return "ABSENT", None
    try:
        raw = activation.read_bytes()
    except OSError as exc:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "activation fingerprint") from exc
    return "PRESENT", hashlib.sha256(raw).hexdigest()


def materialize_evidence_and_candidate(
    packet: dict[str, Any],
    *,
    trusted_root: Path = REPO_ROOT,
) -> CalendarMaterializationResult:
    """Create only the content-addressed evidence bundle and inactive candidate."""
    bundle_bytes, bundle_hash, artifact, artifact_bytes, artifact_hash, validation = build_materialization(packet)
    if HASH_RE.fullmatch(bundle_hash) is None or HASH_RE.fullmatch(artifact_hash) is None:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "hash")
    before_activation = _activation_fingerprint(trusted_root)
    bundle_relative = SOURCE_BUNDLE_DIRECTORY / bundle_hash / SOURCE_BUNDLE_FILENAME
    artifact_relative = ARTIFACT_DIRECTORY / artifact_hash / ARTIFACT_FILENAME
    try:
        bundle_path, bundle_status = _create_only_write(trusted_root, bundle_relative, bundle_bytes)
        artifact_path, artifact_status = _create_only_write(trusted_root, artifact_relative, artifact_bytes)
    except CreateOnlyWriteError as exc:
        raise CalendarMaterializationError(exc.code, exc.detail) from exc
    after_activation = _activation_fingerprint(trusted_root)
    if before_activation != after_activation:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "activation boundary changed")
    return CalendarMaterializationResult(
        evidence_packet_path=bundle_path,
        evidence_packet_sha256=bundle_hash,
        evidence_packet_write_status=bundle_status,
        candidate_artifact_path=artifact_path,
        candidate_artifact_sha256=artifact_hash,
        candidate_artifact_write_status=artifact_status,
        source_bundle_id=artifact["source_bundle_id"],
        calendar_version=artifact["calendar_version"],
        coverage_start=artifact["coverage_start"],
        coverage_end=artifact["coverage_end"],
        source_count=validation["source_count"],
        claim_count=validation["claim_count"],
        claim_source_edge_count=validation["claim_source_edge_count"],
        session_count=validation["session_count"],
        closure_count=validation["closure_count"],
        activation_unchanged=True,
    )


def _load_packet(path_text: str) -> dict[str, Any]:
    raw = sys.stdin.buffer.read() if path_text == "-" else Path(path_text).read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "packet JSON") from exc
    if not isinstance(value, dict):
        raise CalendarMaterializationError("INTEGRITY_FAILURE", "packet object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="Reviewed calendar evidence JSON path, or - for stdin")
    parser.add_argument("--trusted-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        packet = _load_packet(args.packet)
        if args.dry_run:
            bundle_bytes, bundle_hash, artifact, artifact_bytes, artifact_hash, validation = build_materialization(packet)
            print(
                json.dumps(
                    {
                        "status": "DRY_VALIDATED",
                        "evidence_packet_sha256": bundle_hash,
                        "candidate_artifact_sha256": artifact_hash,
                        "evidence_packet_bytes": len(bundle_bytes),
                        "candidate_artifact_bytes": len(artifact_bytes),
                        "calendar_version": artifact["calendar_version"],
                        **validation,
                        "ready_for_activation": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        result = materialize_evidence_and_candidate(packet, trusted_root=args.trusted_root)
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    except CalendarMaterializationError as exc:
        print(json.dumps({"status": "FAILED", "reason": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
