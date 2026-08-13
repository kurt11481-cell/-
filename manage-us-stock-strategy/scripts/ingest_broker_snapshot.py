#!/usr/bin/env python3
"""Ingest broker-screenshot metadata without extracting facts or mutating portfolio state."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SUPPORTED = {".png", ".jpeg", ".jpg", ".webp"}


def ingest(paths: list[Path], *, bundle_id: str, sensitive_login_or_otp_visible: bool = False) -> dict[str, Any]:
    if not paths:
        raise ValueError("at least one broker screenshot is required")
    pages: list[dict[str, Any]] = []
    for index, path in enumerate(paths, 1):
        if path.suffix.lower() not in SUPPORTED:
            raise ValueError(f"unsupported broker screenshot type: {path.suffix}")
        payload = path.read_bytes()
        if not payload:
            raise ValueError(f"empty broker screenshot: {path.name}")
        pages.append({"page_number": index, "page_count": len(paths), "file_name": path.name,
                      "media_type": path.suffix.lower().lstrip("."),
                      "evidence_sha256": hashlib.sha256(payload).hexdigest()})
    return {"schema_version": "2.5", "bundle_id": bundle_id,
            "authority_state": "UNTRUSTED_USER_SUPPLIED_EVIDENCE", "page_count": len(paths),
            "pages": pages, "contains_sensitive_login_or_otp": sensitive_login_or_otp_visible,
            "order_authority": False}
