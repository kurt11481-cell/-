#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from holding_research import build_overlay
from validation_common import load_json, validate_instance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = build_overlay(**load_json(args.context))
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("overlay validation failed: " + "; ".join(errors))
    if args.output:
        args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
