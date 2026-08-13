#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from holding_research import activate_baseline, utc_now
from validation_common import load_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--activated-at", default=None)
    parser.add_argument("--mode", choices=("SHADOW", "MIGRATION"), default="SHADOW")
    args = parser.parse_args()
    result = activate_baseline(load_json(args.input), schema_path=args.schema,
                               baseline_root=args.baseline_root, index_path=args.index,
                               activated_at=args.activated_at or utc_now(), mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["activation_status"] == "VALIDATED_SHADOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
