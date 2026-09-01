#!/usr/bin/env python3
"""Small deterministic validation helpers for the checked-in schema dialect."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SUPPORTED_SCHEMA_KEYS = {
    "$schema", "$id", "$ref", "title", "description", "type", "const",
    "enum", "required", "properties", "additionalProperties", "items",
    "minItems", "uniqueItems", "minLength", "pattern", "format", "minimum",
}
SUPPORTED_SCHEMA_TYPES = {"null", "boolean", "integer", "number", "string", "array", "object"}
SUPPORTED_FORMATS = {"date-time", "date", "uri"}


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("date-time must include an offset")
    return parsed


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def audit_schema_dialect(schema: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if not isinstance(schema, dict):
        return [f"{path}: schema node must be an object"]
    for key in schema:
        if key not in SUPPORTED_SCHEMA_KEYS:
            errors.append(f"{path}: unsupported schema keyword {key}")
    expected_type = schema.get("type")
    if expected_type is not None:
        type_values = expected_type if isinstance(expected_type, list) else [expected_type]
        if not type_values or any(item not in SUPPORTED_SCHEMA_TYPES for item in type_values):
            errors.append(f"{path}.type: unsupported schema type {expected_type!r}")
    format_name = schema.get("format")
    if format_name is not None and format_name not in SUPPORTED_FORMATS:
        errors.append(f"{path}.format: unsupported format {format_name!r}")
    if "required" in schema and not isinstance(schema["required"], list):
        errors.append(f"{path}.required: must be an array")
    properties = schema.get("properties", {})
    if properties is not None:
        if not isinstance(properties, dict):
            errors.append(f"{path}.properties: must be an object")
        else:
            for name, child in properties.items():
                errors.extend(audit_schema_dialect(child, f"{path}.properties.{name}"))
    for key in ("items", "additionalProperties"):
        child = schema.get(key)
        if isinstance(child, dict):
            errors.extend(audit_schema_dialect(child, f"{path}.{key}"))
    return errors


def validate_instance(
    instance: Any, schema_path: str | Path, *, schema_bytes: bytes | None = None,
) -> list[str]:
    schema_file = Path(schema_path).resolve()
    schema = json.loads(schema_bytes.decode("utf-8")) if schema_bytes is not None else load_json(schema_file)
    errors = audit_schema_dialect(schema)
    if errors:
        return errors
    return _validate(instance, schema, schema_file.parent, "$")


def _validate(value: Any, schema: dict[str, Any], base: Path, path: str) -> list[str]:
    errors: list[str] = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or ref.startswith(("http://", "https://", "#")):
            return [f"{path}: unsupported reference {ref!r}"]
        target = (base / ref).resolve()
        if not target.is_file() or target.parent != base.resolve():
            return [f"{path}: unresolved or out-of-directory reference {ref}"]
        referenced = load_json(target)
        dialect_errors = audit_schema_dialect(referenced)
        return dialect_errors or _validate(value, referenced, target.parent, path)

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is outside enum")

    expected = schema.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(value, item) for item in choices):
            errors.append(f"{path}: expected type {choices}, got {type(value).__name__}")
            return errors

    if isinstance(value, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                errors.append(f"{path}: missing required property {name}")
        properties = schema.get("properties", {})
        for name, child_value in value.items():
            if name in properties:
                errors.extend(_validate(child_value, properties[name], base, f"{path}.{name}"))
            else:
                additional = schema.get("additionalProperties", True)
                if additional is False:
                    errors.append(f"{path}: unexpected property {name}")
                elif isinstance(additional, dict):
                    errors.extend(_validate(child_value, additional, base, f"{path}.{name}"))

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than minItems")
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for item in value:
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if marker in seen:
                    errors.append(f"{path}: duplicate item violates uniqueItems")
                    break
                seen.add(marker)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_validate(item, item_schema, base, f"{path}[{index}]"))

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: does not match pattern")
        format_name = schema.get("format")
        try:
            if format_name == "date-time":
                parse_datetime(value)
            elif format_name == "date":
                date.fromisoformat(value)
            elif format_name == "uri":
                parsed = urlparse(value)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError("invalid URI")
        except ValueError as exc:
            errors.append(f"{path}: invalid {format_name}: {exc}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
    return errors
