#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from holding_baseline_operationalization import validate_valuation_snapshot
from validation_common import load_json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    args = parser.parse_args()
    result = validate_valuation_snapshot(load_json(args.input), args.schema)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == "PASSED" else 2

if __name__ == "__main__": raise SystemExit(main())
