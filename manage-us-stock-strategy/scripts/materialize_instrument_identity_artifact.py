#!/usr/bin/env python3
"""Offline II-B2 evidence-packet and identity-candidate materializer.

This module performs deterministic validation and create-only writes. It never
uses the network, writes an activation manifest, invokes Session Authority, or
invokes M1/Kiwoom code.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SCHEMA_ROOT = SCRIPT_DIR.parent / "schemas"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from authority_artifact_io import (  # noqa: E402
    canonical_json_bytes,
)
from validation_common import validate_instance  # noqa: E402


EXPECTED_SCOPE = ("BE", "DRAM", "FSLY", "MVLL", "NBIS", "NOW", "SOXL", "TOST")
AUTHORITY_ID = "US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1"
TICKER_NAMESPACE = "US_EXCHANGE_LISTED"
EVIDENCE_PACKET_FILENAME = "us-equity-instrument-identity-current-v1.sources.json"
ARTIFACT_FILENAME = "us-equity-instrument-identity-current-v1.registry.json"
SOURCE_PACKET_DIRECTORY = Path("workspace/instrument-identity-authority/source-packets")
ARTIFACT_DIRECTORY = Path("workspace/instrument-identity-authority/artifacts")
ACTIVATION_RELATIVE_PATH = Path("workspace/policies/instrument_identity_activation.json")
HASH_RE = re.compile(r"[0-9a-f]{64}")
REQUIRED_CLAIMS = (
    "SECURITY_IDENTITY",
    "INSTRUMENT_TYPE_OR_CLASS",
    "PRIMARY_LISTING_VENUE",
    "PRIMARY_LISTING_SEGMENT_MIC",
    "PRIMARY_LISTING_OPERATING_MIC",
    "EFFECTIVE_DATE_BASIS",
)
MIC_CLAIMS = {
    "PRIMARY_LISTING_SEGMENT_MIC",
    "PRIMARY_LISTING_OPERATING_MIC",
}
EXPECTED_RECORD_FACTS: dict[str, tuple[str, str, str, str, str, str | None, str]] = {
    "BE": ("EQUITY", "COMMON_STOCK", "XNYS", "XNYS", "New York Stock Exchange", None, "CURRENT_AS_OF_ONLY"),
    "DRAM": ("ETF", "ACTIVELY_MANAGED_ETF", "BATS", "XCBO", "Cboe BZX Exchange", "2026-04-02", "VERIFIED_DATE"),
    "FSLY": ("EQUITY", "CLASS_A_COMMON_STOCK", "XNGS", "XNAS", "Nasdaq Global Select Market", "2025-12-09", "VERIFIED_DATE"),
    "MVLL": ("ETF", "LEVERAGED_ETF", "XNMS", "XNAS", "Nasdaq Global Market", "2025-03-07", "VERIFIED_DATE"),
    "NBIS": ("EQUITY", "CLASS_A_ORDINARY_SHARES", "XNGS", "XNAS", "Nasdaq Global Select Market", "2024-10-21", "VERIFIED_DATE"),
    "NOW": ("EQUITY", "COMMON_STOCK", "XNYS", "XNYS", "New York Stock Exchange", None, "CURRENT_AS_OF_ONLY"),
    "SOXL": ("ETF", "LEVERAGED_ETF", "ARCX", "XNYS", "NYSE Arca", None, "CURRENT_AS_OF_ONLY"),
    "TOST": ("EQUITY", "CLASS_A_COMMON_STOCK", "XNYS", "XNYS", "New York Stock Exchange", "2021-09-22", "VERIFIED_DATE"),
}
CLAIM_CAPABILITY_SCOPES = {
    "SECURITY_IDENTITY": {"SECURITY_IDENTITY", "CURRENT_SECURITY_NAME", "LEGAL_ISSUER"},
    "INSTRUMENT_TYPE_OR_CLASS": {"INSTRUMENT_TYPE", "SECURITY_CLASS", "SECURITY_CLASS_CHANGE", "FUND_IDENTITY"},
    "PRIMARY_LISTING_VENUE": {
        "CURRENT_PRIMARY_LISTING_VENUE",
        "PRIMARY_LISTING_VENUE",
        "PRIMARY_LISTING",
        "CURRENT_LISTING",
        "LISTING_TRANSFER",
    },
    "PRIMARY_LISTING_SEGMENT_MIC": {"SEGMENT_MIC", "MIC_IDENTITY", "OPRT_SGMT_RELATIONSHIP"},
    "PRIMARY_LISTING_OPERATING_MIC": {"OPERATING_MIC", "OPERATING_MIC_RELATIONSHIP", "OPRT_SGMT_RELATIONSHIP"},
    "EFFECTIVE_DATE_BASIS": {
        "EFFECTIVE_FROM",
        "FIRST_TRADING_DATE",
        "LISTING_START",
        "LISTING_TRANSFER",
        "CURRENT_LISTING",
        "CURRENT_PRIMARY_LISTING_VENUE",
    },
}
ANCILLARY_SOURCE_IDS = {"ISO10383_AUGUST_2026_ANNEX", "NBIS_SEC_20F_INDEX"}


class MaterializationError(ValueError):
    """A deterministic packet, artifact, or create-only integrity failure."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class MaterializationResult:
    evidence_packet_path: Path
    evidence_packet_sha256: str
    evidence_packet_write_status: str
    candidate_registry_path: Path
    candidate_registry_sha256: str
    candidate_registry_write_status: str
    registry_version: str
    authority_id: str
    authority_as_of: str
    scope_count: int
    record_count: int
    source_count: int
    claim_link_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_packet_path": str(self.evidence_packet_path),
            "evidence_packet_sha256": self.evidence_packet_sha256,
            "evidence_packet_write_status": self.evidence_packet_write_status,
            "candidate_registry_path": str(self.candidate_registry_path),
            "candidate_registry_sha256": self.candidate_registry_sha256,
            "candidate_registry_write_status": self.candidate_registry_write_status,
            "registry_version": self.registry_version,
            "authority_id": self.authority_id,
            "authority_as_of": self.authority_as_of,
            "scope_count": self.scope_count,
            "record_count": self.record_count,
            "source_count": self.source_count,
            "claim_link_count": self.claim_link_count,
            "order_authority": False,
            "quantity_authority": "none",
            "execution_quantity": None,
            "activation_created": False,
        }


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MaterializationError("INTEGRITY_FAILURE", field) from exc


def _parse_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise MaterializationError("INTEGRITY_FAILURE", field) from exc
    if parsed.tzinfo is None:
        raise MaterializationError("INTEGRITY_FAILURE", f"{field}: timezone required")
    return parsed


def _schema_errors(packet: dict[str, Any]) -> list[str]:
    return validate_instance(
        packet,
        SCHEMA_ROOT / "instrument-identity-evidence-packet.schema.json",
    )


def _validate_source(source: dict[str, Any], authority_date: date) -> None:
    source_id = source["source_id"]
    if source["source_id_semantics"] != "INTERNAL_EVIDENCE_PACKET_REFERENCE":
        raise MaterializationError("INTEGRITY_FAILURE", source_id)
    if not source["source_reference"].startswith("https://"):
        raise MaterializationError("INTEGRITY_FAILURE", f"{source_id}: source_reference")
    if _parse_date(source["retrieved_date"], f"{source_id}.retrieved_date") > authority_date:
        raise MaterializationError("TEMPORAL_VIOLATION", source_id)
    if source["retrieval_time_precision"] != "DATE_ONLY_KST":
        raise MaterializationError("INTEGRITY_FAILURE", f"{source_id}: retrieval precision")
    content_hash = source["content_sha256"]
    content_status = source["content_hash_status"]
    if content_status == "NOT_CAPTURED":
        if content_hash is not None:
            raise MaterializationError("INTEGRITY_FAILURE", f"{source_id}: invented content hash")
    elif content_status == "VERIFIED":
        if not isinstance(content_hash, str) or HASH_RE.fullmatch(content_hash) is None:
            raise MaterializationError("INTEGRITY_FAILURE", f"{source_id}: missing verified content hash")
    else:
        raise MaterializationError("INTEGRITY_FAILURE", f"{source_id}: content hash status")
    ticker = source["ticker"]
    if ticker is None and source["source_family"] != "ISO_10383":
        raise MaterializationError("INTEGRITY_FAILURE", f"{source_id}: common non-ISO source")
    effective_date = source["publication_or_effective_date"]
    if effective_date is not None:
        parsed = _parse_date(effective_date, f"{source_id}.publication_or_effective_date")
        if parsed > authority_date and source_id != "ISO10383_AUGUST_2026_ANNEX":
            raise MaterializationError("TEMPORAL_VIOLATION", source_id)
        if parsed > authority_date and source["claim_scope"] != ["CURRENT_MIC_CHANGE_CROSSCHECK"]:
            raise MaterializationError("TEMPORAL_VIOLATION", source_id)


def _validate_normalized_record(record: dict[str, Any], authority_date: date) -> None:
    ticker = record["ticker"]
    normalized = record["normalized_record"]
    if normalized["ticker"] != ticker:
        raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: normalized ticker")
    expected = EXPECTED_RECORD_FACTS.get(ticker)
    if expected is None:
        raise MaterializationError("INTEGRITY_FAILURE", ticker)
    actual = (
        normalized["instrument_type"],
        normalized["security_class"],
        normalized["primary_listing_segment_mic"],
        normalized["primary_listing_operating_mic"],
        normalized["primary_listing_venue_name"],
        normalized["effective_from"],
        normalized["effective_from_basis"],
    )
    if actual != expected:
        raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: exact record assertion")
    if ticker == "DRAM" and (
        normalized["instrument_type"] != "ETF"
        or normalized["security_class"] != "ACTIVELY_MANAGED_ETF"
    ):
        raise MaterializationError("INTEGRITY_FAILURE", "DRAM_SPOT_ETF_CONTAMINATION")
    if normalized["effective_from_basis"] == "CURRENT_AS_OF_ONLY":
        if normalized["effective_from"] is not None:
            raise MaterializationError("TEMPORAL_VIOLATION", ticker)
    else:
        effective_from = _parse_date(normalized["effective_from"], f"{ticker}.effective_from")
        if effective_from > authority_date:
            raise MaterializationError("TEMPORAL_VIOLATION", ticker)
    if normalized["effective_to"] is not None:
        raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: effective_to")


def validate_evidence_packet(packet: dict[str, Any]) -> dict[str, int]:
    """Validate a reviewed evidence packet without writing any bytes."""
    errors = _schema_errors(packet)
    if errors:
        raise MaterializationError("INTEGRITY_FAILURE", "; ".join(errors[:4]))
    if tuple(packet["scope"]) != EXPECTED_SCOPE:
        raise MaterializationError("INTEGRITY_FAILURE", "scope")
    authority_date = _parse_date(packet["authority_as_of"], "authority_as_of")
    artifact_authority = _parse_datetime(packet["artifact_authority_as_of"], "artifact_authority_as_of")
    generated_at = _parse_datetime(packet["generated_at"], "generated_at")
    if artifact_authority.date() != authority_date:
        raise MaterializationError("INTEGRITY_FAILURE", "authority date normalization")
    if generated_at < artifact_authority:
        raise MaterializationError("TEMPORAL_VIOLATION", "generated_at")

    sources = packet["claims"]
    source_ids = [source["source_id"] for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise MaterializationError("INTEGRITY_FAILURE", "duplicate source_id")
    source_by_id = {source["source_id"]: source for source in sources}
    for source in sources:
        _validate_source(source, authority_date)

    records = packet["records"]
    tickers = [record["ticker"] for record in records]
    if tuple(tickers) != EXPECTED_SCOPE or len(records) != len(EXPECTED_SCOPE):
        raise MaterializationError("INTEGRITY_FAILURE", "record scope/order")
    claim_link_count = 0
    used_source_ids: set[str] = set()
    for record in records:
        ticker = record["ticker"]
        _validate_normalized_record(record, authority_date)
        links = record["claim_links"]
        claim_types = [link["claim_type"] for link in links]
        if tuple(claim_types) != REQUIRED_CLAIMS or len(set(claim_types)) != len(REQUIRED_CLAIMS):
            raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: claim coverage/order")
        for link in links:
            claim_type = link["claim_type"]
            linked_sources: list[dict[str, Any]] = []
            for source_id in link["source_ids"]:
                source = source_by_id.get(source_id)
                if source is None:
                    raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: unknown source {source_id}")
                if source["ticker"] not in (None, ticker):
                    raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: wrong-ticker source {source_id}")
                linked_sources.append(source)
                used_source_ids.add(source_id)
            if not any(
                CLAIM_CAPABILITY_SCOPES[claim_type].intersection(source["claim_scope"])
                for source in linked_sources
            ):
                raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: unsupported {claim_type}")
            if claim_type in MIC_CLAIMS and any(
                source["source_family"] != "ISO_10383" for source in linked_sources
            ):
                raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: non-ISO MIC source")
            if claim_type == "PRIMARY_LISTING_SEGMENT_MIC" and not any(
                "SEGMENT_MIC" in source["claim_scope"] for source in linked_sources
            ):
                raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: segment MIC source")
            if claim_type == "PRIMARY_LISTING_OPERATING_MIC" and not any(
                {"OPERATING_MIC", "OPERATING_MIC_RELATIONSHIP", "OPRT_SGMT_RELATIONSHIP"}.intersection(source["claim_scope"])
                for source in linked_sources
            ):
                raise MaterializationError("INTEGRITY_FAILURE", f"{ticker}: operating MIC source")
            claim_link_count += len(link["source_ids"])
    unused = set(source_by_id) - used_source_ids
    if unused - ANCILLARY_SOURCE_IDS:
        raise MaterializationError("INTEGRITY_FAILURE", f"unlinked sources: {sorted(unused)}")
    return {
        "source_count": len(sources),
        "record_count": len(records),
        "required_claim_count": len(records) * len(REQUIRED_CLAIMS),
        "claim_link_count": claim_link_count,
    }


def build_candidate_artifact(packet: dict[str, Any], packet_hash: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for evidence_record in packet["records"]:
        source_ref_ids = sorted(
            {
                source_id
                for link in evidence_record["claim_links"]
                for source_id in link["source_ids"]
            }
        )
        records.append(
            {
                **evidence_record["normalized_record"],
                "source_ref_ids": source_ref_ids,
            }
        )
    artifact = {
        "artifact_schema_version": "1.0",
        "authority_id": AUTHORITY_ID,
        "registry_version": packet["registry_version"],
        "ticker_namespace": TICKER_NAMESPACE,
        "scope": list(EXPECTED_SCOPE),
        "generated_at": packet["generated_at"],
        "authority_as_of": packet["artifact_authority_as_of"],
        "source_packet_id": packet["source_packet_id"],
        "source_packet_hash": packet_hash,
        "order_authority": False,
        "records": records,
    }
    errors = validate_instance(
        artifact,
        SCHEMA_ROOT / "instrument-identity-artifact.schema.json",
    )
    if errors:
        raise MaterializationError("INTEGRITY_FAILURE", "; ".join(errors[:4]))
    return artifact


def build_materialization(packet: dict[str, Any]) -> tuple[bytes, str, dict[str, Any], bytes, str, dict[str, int]]:
    validation = validate_evidence_packet(packet)
    packet_bytes = canonical_json_bytes(packet)
    packet_hash = hashlib.sha256(packet_bytes).hexdigest()
    artifact = build_candidate_artifact(packet, packet_hash)
    artifact_bytes = canonical_json_bytes(artifact)
    artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
    return packet_bytes, packet_hash, artifact, artifact_bytes, artifact_hash, validation


def _confined_path(trusted_root: Path, relative: Path) -> Path:
    root = Path(os.path.abspath(os.fspath(trusted_root)))
    if relative.is_absolute() or ".." in relative.parts:
        raise MaterializationError("INTEGRITY_FAILURE", "PATH_NOT_CONFINED")
    target = Path(os.path.abspath(os.fspath(root / relative)))
    try:
        if os.path.commonpath((os.path.normcase(str(root)), os.path.normcase(str(target)))) != os.path.normcase(str(root)):
            raise MaterializationError("INTEGRITY_FAILURE", "PATH_NOT_CONFINED")
    except ValueError as exc:
        raise MaterializationError("INTEGRITY_FAILURE", "PATH_NOT_CONFINED") from exc
    return target


def _writer_pre_create_test_seam() -> None:
    """Deterministic test synchronization point; never changes writer inputs."""


def _windows_final_path(handle: int) -> Path:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    get_final_path.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_final_path(handle, buffer, len(buffer), 0)
    if length == 0 or length >= len(buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def _windows_normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _windows_handle_attributes(handle: int) -> int:
    from ctypes import wintypes

    class FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [("file_attributes", wintypes.DWORD), ("reparse_tag", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_info = kernel32.GetFileInformationByHandleEx
    get_info.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    info = FileAttributeTagInfo()
    if not get_info(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(info.file_attributes)


def _verify_windows_handle(
    handle: int,
    *,
    expected_path: Path,
    directory: bool,
    expected_parent: Path | None = None,
) -> Path:
    attributes = _windows_handle_attributes(handle)
    if attributes & 0x00000400:  # FILE_ATTRIBUTE_REPARSE_POINT
        raise MaterializationError("INTEGRITY_FAILURE", "REPARSE_POINT")
    if bool(attributes & 0x00000010) != directory:  # FILE_ATTRIBUTE_DIRECTORY
        raise MaterializationError("INTEGRITY_FAILURE", "FILE_TYPE_MISMATCH")
    final_path = _windows_final_path(handle)
    if _windows_normalized_path(final_path) != _windows_normalized_path(expected_path):
        raise MaterializationError("INTEGRITY_FAILURE", "FINAL_PATH_MISMATCH")
    if expected_parent is not None:
        if _windows_normalized_path(final_path.parent) != _windows_normalized_path(expected_parent):
            raise MaterializationError("INTEGRITY_FAILURE", "PARENT_HANDLE_MISMATCH")
    return final_path


def _open_windows_root(trusted_root: Path) -> int:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        os.fspath(trusted_root),
        0x001000A1,  # SYNCHRONIZE | FILE_READ_ATTRIBUTES | FILE_TRAVERSE | FILE_LIST_DIRECTORY
        0x00000001,  # FILE_SHARE_READ; deny write/delete/rename sharing
        None,
        3,  # OPEN_EXISTING
        0x00200000 | 0x02000000,  # OPEN_REPARSE_POINT | BACKUP_SEMANTICS
        None,
    )
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    return int(handle)


def _nt_open_relative(
    parent_handle: int,
    name: str,
    *,
    desired_access: int,
    create_disposition: int,
    create_options: int,
    file_attributes: int,
) -> int:
    from ctypes import wintypes

    if not name or name in (".", "..") or "\\" in name or "/" in name:
        raise MaterializationError("INTEGRITY_FAILURE", "PATH_NOT_CONFINED")

    class UnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", wintypes.LPWSTR),
        ]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.ULONG),
            ("root_directory", wintypes.HANDLE),
            ("object_name", ctypes.POINTER(UnicodeString)),
            ("attributes", wintypes.ULONG),
            ("security_descriptor", wintypes.LPVOID),
            ("security_quality_of_service", wintypes.LPVOID),
        ]

    class IoStatusBlock(ctypes.Structure):
        _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]

    ntdll = ctypes.WinDLL("ntdll")
    nt_create_file = ntdll.NtCreateFile
    nt_create_file.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(ObjectAttributes),
        ctypes.POINTER(IoStatusBlock),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    ]
    nt_create_file.restype = wintypes.LONG
    rtl_ntstatus_to_dos_error = ntdll.RtlNtStatusToDosError
    rtl_ntstatus_to_dos_error.argtypes = [wintypes.LONG]
    rtl_ntstatus_to_dos_error.restype = wintypes.ULONG

    name_buffer = ctypes.create_unicode_buffer(name)
    name_length = len(name.encode("utf-16-le"))
    unicode_name = UnicodeString(
        name_length,
        name_length + ctypes.sizeof(ctypes.c_wchar),
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    object_attributes = ObjectAttributes(
        ctypes.sizeof(ObjectAttributes),
        wintypes.HANDLE(parent_handle),
        ctypes.pointer(unicode_name),
        0x00000040,  # OBJ_CASE_INSENSITIVE
        None,
        None,
    )
    io_status = IoStatusBlock()
    handle = wintypes.HANDLE()
    status = nt_create_file(
        ctypes.byref(handle),
        desired_access,
        ctypes.byref(object_attributes),
        ctypes.byref(io_status),
        None,
        file_attributes,
        0x00000001,  # FILE_SHARE_READ; deny write/delete/rename sharing
        create_disposition,
        create_options,
        None,
        0,
    )
    if status < 0:
        unsigned_status = ctypes.c_ulong(status).value
        if unsigned_status == 0xC0000035:  # STATUS_OBJECT_NAME_COLLISION
            raise FileExistsError(name)
        error_code = int(rtl_ntstatus_to_dos_error(status))
        raise OSError(error_code, ctypes.FormatError(error_code), name)
    if handle.value is None:
        raise MaterializationError("INTEGRITY_FAILURE", "INVALID_HANDLE")
    return int(handle.value)


def _read_windows_handle(handle: int) -> bytes:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    read_file = kernel32.ReadFile
    read_file.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    read_file.restype = wintypes.BOOL
    chunks: list[bytes] = []
    while True:
        buffer = ctypes.create_string_buffer(65536)
        count = wintypes.DWORD()
        if not read_file(handle, buffer, len(buffer), ctypes.byref(count), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if count.value == 0:
            return b"".join(chunks)
        chunks.append(buffer.raw[: count.value])


def _write_windows_handle(handle: int, expected: bytes) -> None:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    write_file = kernel32.WriteFile
    write_file.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    write_file.restype = wintypes.BOOL
    offset = 0
    while offset < len(expected):
        chunk = expected[offset : offset + 0xFFFFFFFF]
        count = wintypes.DWORD()
        buffer = ctypes.create_string_buffer(chunk)
        if not write_file(handle, buffer, len(chunk), ctypes.byref(count), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if count.value == 0:
            raise MaterializationError("INTEGRITY_FAILURE", "short write")
        offset += count.value
    if not kernel32.FlushFileBuffers(handle):
        raise ctypes.WinError(ctypes.get_last_error())


def _create_only_write_windows(
    trusted_root: Path,
    relative_path: Path,
    expected: bytes,
    final_path: Path,
) -> tuple[Path, str]:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    set_file_pointer = kernel32.SetFilePointerEx
    set_file_pointer.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
    set_file_pointer.restype = wintypes.BOOL

    handles: list[int] = []
    try:
        root_handle = _open_windows_root(trusted_root)
        handles.append(root_handle)
        current_handle = root_handle
        current_path = _verify_windows_handle(
            root_handle,
            expected_path=trusted_root,
            directory=True,
        )
        for component in relative_path.parent.parts:
            child_handle = _nt_open_relative(
                current_handle,
                component,
                desired_access=0x001000A1,
                create_disposition=3,  # FILE_OPEN_IF
                create_options=0x00000001 | 0x00000020 | 0x00200000,
                file_attributes=0x00000010,
            )
            handles.append(child_handle)
            expected_child = current_path / component
            current_path = _verify_windows_handle(
                child_handle,
                expected_path=expected_child,
                directory=True,
                expected_parent=current_path,
            )
            current_handle = child_handle

        _writer_pre_create_test_seam()
        try:
            file_handle = _nt_open_relative(
                current_handle,
                relative_path.name,
                desired_access=0xC0100080,  # GENERIC_READ | GENERIC_WRITE | SYNCHRONIZE | READ_ATTRIBUTES
                create_disposition=2,  # FILE_CREATE
                create_options=0x00000020 | 0x00000040 | 0x00200000,
                file_attributes=0x00000001,  # FILE_ATTRIBUTE_READONLY
            )
        except FileExistsError:
            file_handle = _nt_open_relative(
                current_handle,
                relative_path.name,
                desired_access=0x80100080,  # GENERIC_READ | SYNCHRONIZE | READ_ATTRIBUTES
                create_disposition=1,  # FILE_OPEN
                create_options=0x00000020 | 0x00000040 | 0x00200000,
                file_attributes=0,
            )
            handles.append(file_handle)
            current_path = _windows_final_path(current_handle)
            _verify_windows_handle(
                file_handle,
                expected_path=current_path / relative_path.name,
                directory=False,
                expected_parent=current_path,
            )
            existing = _read_windows_handle(file_handle)
            if existing != expected:
                raise MaterializationError("INTEGRITY_FAILURE", f"existing bytes mismatch: {final_path}")
            return final_path, "ALREADY_PRESENT_VERIFIED"

        handles.append(file_handle)
        current_path = _windows_final_path(current_handle)
        root_path = _windows_final_path(root_handle)
        verified_file_path = _verify_windows_handle(
            file_handle,
            expected_path=current_path / relative_path.name,
            directory=False,
            expected_parent=current_path,
        )
        try:
            common = os.path.commonpath(
                (_windows_normalized_path(root_path), _windows_normalized_path(verified_file_path))
            )
        except ValueError as exc:
            raise MaterializationError("INTEGRITY_FAILURE", "PATH_NOT_CONFINED") from exc
        if common != _windows_normalized_path(root_path):
            raise MaterializationError("INTEGRITY_FAILURE", "PATH_NOT_CONFINED")

        _write_windows_handle(file_handle, expected)
        if not set_file_pointer(file_handle, 0, None, 0):  # FILE_BEGIN
            raise ctypes.WinError(ctypes.get_last_error())
        if _read_windows_handle(file_handle) != expected:
            raise MaterializationError("INTEGRITY_FAILURE", f"post-write mismatch: {final_path}")
        return final_path, "CREATED"
    finally:
        for handle in reversed(handles):
            close_handle(handle)


def _create_only_write_posix(
    trusted_root: Path,
    relative_path: Path,
    expected: bytes,
    final_path: Path,
) -> tuple[Path, str]:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    directory_handles: list[int] = []
    file_handle: int | None = None
    try:
        current_handle = os.open(trusted_root, directory_flags)
        directory_handles.append(current_handle)
        for component in relative_path.parent.parts:
            try:
                os.mkdir(component, mode=0o755, dir_fd=current_handle)
            except FileExistsError:
                pass
            current_handle = os.open(component, directory_flags, dir_fd=current_handle)
            directory_handles.append(current_handle)

        _writer_pre_create_test_seam()
        try:
            file_handle = os.open(
                relative_path.name,
                file_flags | os.O_CREAT | os.O_EXCL,
                0o444,
                dir_fd=current_handle,
            )
        except FileExistsError:
            file_handle = os.open(relative_path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current_handle)
            existing_chunks: list[bytes] = []
            while True:
                chunk = os.read(file_handle, 65536)
                if not chunk:
                    break
                existing_chunks.append(chunk)
            if b"".join(existing_chunks) != expected:
                raise MaterializationError("INTEGRITY_FAILURE", f"existing bytes mismatch: {final_path}")
            return final_path, "ALREADY_PRESENT_VERIFIED"

        file_stat = os.fstat(file_handle)
        if not stat.S_ISREG(file_stat.st_mode):
            raise MaterializationError("INTEGRITY_FAILURE", "FILE_TYPE_MISMATCH")
        view = memoryview(expected)
        while view:
            written = os.write(file_handle, view)
            if written <= 0:
                raise MaterializationError("INTEGRITY_FAILURE", f"short write: {final_path}")
            view = view[written:]
        os.fsync(file_handle)
        os.lseek(file_handle, 0, os.SEEK_SET)
        persisted_chunks: list[bytes] = []
        while True:
            chunk = os.read(file_handle, 65536)
            if not chunk:
                break
            persisted_chunks.append(chunk)
        if b"".join(persisted_chunks) != expected:
            raise MaterializationError("INTEGRITY_FAILURE", f"post-write mismatch: {final_path}")
        return final_path, "CREATED"
    finally:
        if file_handle is not None:
            os.close(file_handle)
        for handle in reversed(directory_handles):
            os.close(handle)


def _create_only_write(trusted_root: Path, relative_path: Path, expected: bytes) -> tuple[Path, str]:
    root = Path(os.path.abspath(os.fspath(trusted_root)))
    final_path = _confined_path(root, relative_path)
    try:
        if os.name == "nt":
            return _create_only_write_windows(root, relative_path, expected, final_path)
        return _create_only_write_posix(root, relative_path, expected, final_path)
    except MaterializationError:
        raise
    except OSError as exc:
        raise MaterializationError("INTEGRITY_FAILURE", str(final_path)) from exc


def materialize_evidence_and_candidate(
    packet: dict[str, Any],
    *,
    trusted_root: Path = REPO_ROOT,
) -> MaterializationResult:
    """Validate and create content-addressed packet/artifact files only."""
    (
        packet_bytes,
        packet_hash,
        _artifact,
        artifact_bytes,
        artifact_hash,
        validation,
    ) = build_materialization(packet)
    if HASH_RE.fullmatch(packet_hash) is None or HASH_RE.fullmatch(artifact_hash) is None:
        raise MaterializationError("INTEGRITY_FAILURE", "hash")
    packet_relative = SOURCE_PACKET_DIRECTORY / packet_hash / EVIDENCE_PACKET_FILENAME
    artifact_relative = ARTIFACT_DIRECTORY / artifact_hash / ARTIFACT_FILENAME
    packet_path, packet_status = _create_only_write(trusted_root, packet_relative, packet_bytes)
    artifact_path, artifact_status = _create_only_write(trusted_root, artifact_relative, artifact_bytes)
    activation_path = _confined_path(trusted_root, ACTIVATION_RELATIVE_PATH)
    if activation_path.exists() or activation_path.is_symlink():
        raise MaterializationError("INTEGRITY_FAILURE", "activation boundary changed")
    return MaterializationResult(
        evidence_packet_path=packet_path,
        evidence_packet_sha256=packet_hash,
        evidence_packet_write_status=packet_status,
        candidate_registry_path=artifact_path,
        candidate_registry_sha256=artifact_hash,
        candidate_registry_write_status=artifact_status,
        registry_version=packet["registry_version"],
        authority_id=AUTHORITY_ID,
        authority_as_of=packet["artifact_authority_as_of"],
        scope_count=len(EXPECTED_SCOPE),
        record_count=validation["record_count"],
        source_count=validation["source_count"],
        claim_link_count=validation["claim_link_count"],
    )


def _load_packet(path_text: str) -> dict[str, Any]:
    if path_text == "-":
        raw = sys.stdin.buffer.read()
    else:
        raw = Path(path_text).read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterializationError("INTEGRITY_FAILURE", "packet JSON") from exc
    if not isinstance(value, dict):
        raise MaterializationError("INTEGRITY_FAILURE", "packet object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="Reviewed packet JSON path, or - for stdin")
    parser.add_argument("--trusted-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        packet = _load_packet(args.packet)
        if args.dry_run:
            validation = validate_evidence_packet(packet)
            print(json.dumps({"status": "DRY_VALIDATED", **validation}, sort_keys=True))
            return 0
        result = materialize_evidence_and_candidate(packet, trusted_root=args.trusted_root)
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    except MaterializationError as exc:
        print(json.dumps({"status": "FAILED", "reason": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
