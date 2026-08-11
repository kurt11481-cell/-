#!/usr/bin/env python3
"""Audit the supported schema dialect and validate JSON instances independently."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validation_common import audit_schema_dialect, load_json, validate_instance


def _references(value: object) -> list[str]:
    references: list[str] = []
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            references.append(ref)
        for child in value.values():
            references.extend(_references(child))
    elif isinstance(value, list):
        for child in value:
            references.extend(_references(child))
    return references


def audit_directory(schema_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(schema_dir.glob("*.schema.json")):
        try:
            schema = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: unreadable schema: {exc}")
            continue
        for error in audit_schema_dialect(schema):
            errors.append(f"{path.name}: {error}")
        for ref in _references(schema):
            if ref.startswith(("http://", "https://", "#")):
                errors.append(f"{path.name}: unsupported reference {ref}")
                continue
            target = (schema_dir / ref).resolve()
            if target.parent != schema_dir.resolve() or not target.is_file():
                errors.append(f"{path.name}: unresolved or out-of-directory reference {ref}")
    if not list(schema_dir.glob("*.schema.json")):
        errors.append("no schema files found")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", type=Path, default=Path(__file__).resolve().parents[1] / "schemas")
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--instance", type=Path)
    args = parser.parse_args()

    errors = audit_directory(args.schema_dir)
    if bool(args.schema) != bool(args.instance):
        errors.append("--schema and --instance must be supplied together")
    elif args.schema and args.instance:
        try:
            errors.extend(validate_instance(load_json(args.instance), args.schema))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"instance could not be read: {exc}")
    result = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
