#!/usr/bin/env python3
"""Build a locally hashed v2.6 holding-research baseline candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from holding_research import recompute_hashes
from validation_common import load_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    record = recompute_hashes(load_json(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "ticker": record.get("ticker"),
        "research_packet_hash": record["research_packet_hash"],
        "baseline_hash": record["baseline_hash"],
        "order_authority": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
