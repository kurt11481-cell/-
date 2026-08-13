#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from holding_research import evaluate_freshness, utc_now
from validation_common import load_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--max-age-days", type=int, required=True)
    args = parser.parse_args()
    result = evaluate_freshness(load_json(args.input), as_of=args.as_of or utc_now(), max_age_days=args.max_age_days)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["freshness_status"] == "FRESH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
