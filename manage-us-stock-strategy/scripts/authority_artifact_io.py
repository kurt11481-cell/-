#!/usr/bin/env python3
"""Narrow immutable-authority artifact I/O primitives.

This module owns byte-level canonical JSON and fixed-root, no-reparse,
single-handle reads only. Authority-specific paths and semantics remain in the
Session and Instrument Identity loaders.
"""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
from typing import Any


class AuthorityArtifactIOError(ValueError):
    """A byte/path integrity failure without authority-specific semantics."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the shared canonical UTF-8 JSON representation."""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _require_descendant(path: Path, trusted_root: Path) -> None:
    root_text = os.path.normcase(os.fspath(trusted_root))
    path_text = os.path.normcase(os.fspath(path))
    try:
        common = os.path.commonpath((root_text, path_text))
    except ValueError as exc:
        raise AuthorityArtifactIOError("PATH_NOT_CONFINED") from exc
    if common != root_text:
        raise AuthorityArtifactIOError("PATH_NOT_CONFINED")


def _windows_final_path(handle: int) -> str:
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
        return "\\\\" + value[8:]
    return value[4:] if value.startswith("\\\\?\\") else value


def _windows_open_checked(path: Path, *, directory: bool) -> int:
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
    flags = 0x00200000  # FILE_FLAG_OPEN_REPARSE_POINT
    if directory:
        flags |= 0x02000000  # FILE_FLAG_BACKUP_SEMANTICS
    handle = create_file(
        os.fspath(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ; block substitution and mutation
        None,
        3,  # OPEN_EXISTING
        flags,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())

    class FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [("file_attributes", wintypes.DWORD), ("reparse_tag", wintypes.DWORD)]

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    info = FileAttributeTagInfo()
    get_info = kernel32.GetFileInformationByHandleEx
    get_info.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    if not get_info(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
        error = ctypes.WinError(ctypes.get_last_error())
        close_handle(handle)
        raise error
    if info.file_attributes & 0x00000400:  # FILE_ATTRIBUTE_REPARSE_POINT
        close_handle(handle)
        raise AuthorityArtifactIOError("REPARSE_POINT")
    try:
        final_path = _windows_final_path(handle)
    except Exception:
        close_handle(handle)
        raise
    if os.path.normcase(os.path.abspath(final_path)) != os.path.normcase(os.path.abspath(path)):
        close_handle(handle)
        raise AuthorityArtifactIOError("FINAL_PATH_MISMATCH")
    return int(handle)


def _windows_read_handle(handle: int) -> bytes:
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


def _read_windows_no_reparse(path: Path, trusted_root: Path) -> bytes:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    handles: list[int] = []
    try:
        handles.append(_windows_open_checked(trusted_root, directory=True))
        relative_parts = path.relative_to(trusted_root).parts
        current = trusted_root
        for component in relative_parts[:-1]:
            current = current / component
            handles.append(_windows_open_checked(current, directory=True))
        file_handle = _windows_open_checked(path, directory=False)
        handles.append(file_handle)
        return _windows_read_handle(file_handle)
    finally:
        for handle in reversed(handles):
            close_handle(handle)


def _read_posix_no_symlink(path: Path, trusted_root: Path) -> bytes:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    handles: list[int] = []
    try:
        current_handle = os.open(trusted_root, directory_flags)
        handles.append(current_handle)
        relative_parts = path.relative_to(trusted_root).parts
        for component in relative_parts[:-1]:
            current_handle = os.open(component, directory_flags, dir_fd=current_handle)
            handles.append(current_handle)
        file_handle = os.open(relative_parts[-1], file_flags, dir_fd=current_handle)
        with os.fdopen(file_handle, "rb") as stream:
            return stream.read()
    finally:
        for handle in reversed(handles):
            os.close(handle)


def read_once_no_reparse(path: Path, trusted_root: Path) -> bytes:
    """Read a confined file once from a checked handle without following aliases."""
    trusted = _lexical_absolute(trusted_root)
    target = _lexical_absolute(path)
    _require_descendant(target, trusted)
    if os.name == "nt":
        return _read_windows_no_reparse(target, trusted)
    return _read_posix_no_symlink(target, trusted)


def decode_canonical_object(raw: bytes) -> dict[str, Any]:
    """Decode only the exact shared canonical object representation."""
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
            raise ValueError("NON_CANONICAL_JSON")
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AuthorityArtifactIOError("NON_CANONICAL_JSON") from exc
