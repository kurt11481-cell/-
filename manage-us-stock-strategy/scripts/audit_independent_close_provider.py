#!/usr/bin/env python3
"""Audit a structured independent-close provider without enabling it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance


def audit_provider(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if record.get("independent_from_yahoo") is not True:
        errors.append("PROVIDER_NOT_INDEPENDENT_FROM_YAHOO")
    if record.get("source_timestamp_supported") is not True:
        errors.append("SOURCE_TIMESTAMP_UNSUPPORTED")
    if record.get("enabled") is True:
        if not record.get("sample_comparisons") or not record.get("shadow_session_results"):
            errors.append("ACCEPTANCE_RECORD_INCOMPLETE")
        if not record.get("user_approval_reference"):
            errors.append("EXPLICIT_USER_APPROVAL_MISSING")
        if record.get("provider_state") != "ENABLED":
            errors.append("PROVIDER_STATE_NOT_ENABLED")
    if record.get("independent_crosscheck_eligible") is True and record.get("enabled") is not True:
        errors.append("DISABLED_PROVIDER_CANNOT_BE_CROSSCHECK_ELIGIBLE")
    return {"audit_status": "PASSED" if not errors else "FAILED", "errors": errors,
            "provider_state": record.get("provider_state"), "enabled": record.get("enabled") is True,
            "independent_crosscheck_eligible": record.get("independent_crosscheck_eligible") is True,
            "order_authority": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    args = parser.parse_args()
    record = load_json(args.record)
    schema_errors = validate_instance(record, args.schema)
    result = audit_provider(record, load_json(args.policy))
    result["errors"] = schema_errors + result["errors"]
    if result["errors"]:
        result["audit_status"] = "FAILED"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["audit_status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
