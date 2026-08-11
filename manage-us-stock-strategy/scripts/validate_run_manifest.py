#!/usr/bin/env python3
"""Validate run manifests and reject secret-like fields."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from validation_common import load_json, parse_datetime, validate_instance


SECRET_KEY = re.compile(r"(^|_)(api_?key|secret|password|credential|access_?token|refresh_?token)($|_)", re.IGNORECASE)


def _secret_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(key):
                found.append(f"{path}.{key}")
            found.extend(_secret_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_secret_paths(child, f"{path}[{index}]"))
    return found


def validate_manifest(manifest: dict[str, Any], schema: Path) -> list[str]:
    errors = validate_instance(manifest, schema)
    try:
        if parse_datetime(manifest["generated_at"]) < parse_datetime(manifest["analysis_cutoff"]):
            errors.append("generated_at precedes analysis_cutoff")
    except (KeyError, ValueError) as exc:
        errors.append(f"manifest time comparison unavailable: {exc}")
    secret_paths = _secret_paths(manifest)
    if secret_paths:
        errors.append("secret-like fields are prohibited: " + ", ".join(secret_paths))
    if manifest.get("secrets_recorded") is not False:
        errors.append("secrets_recorded must be false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "run-manifest.schema.json")
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    errors = validate_manifest(manifest, args.schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
