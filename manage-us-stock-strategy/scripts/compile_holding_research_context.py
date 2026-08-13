#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from holding_research import compile_context
from validation_common import load_json, validate_instance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--baseline-schema", type=Path, required=True)
    parser.add_argument("--output-schema", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = compile_context(load_json(args.profile), load_json(args.baseline), load_json(args.overlay), baseline_schema=args.baseline_schema)
    errors = validate_instance(value, args.output_schema)
    if errors:
        raise SystemExit("compiled context validation failed: " + "; ".join(errors))
    if args.output:
        args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
