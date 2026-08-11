"""Merge independently verified session and completed-close evidence into a snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))

    snapshot["session"].update(evidence["session"])
    verified_at = evidence["quotes_verified_at_utc"]
    for symbol, quote in evidence["quotes"].items():
        row = snapshot["symbols"][symbol]
        builder_close = float(row["close"])
        second_close = float(quote["completed_close"])
        difference = abs(builder_close - second_close)
        tolerance = max(0.05, 0.001 * builder_close)
        row["quote_crosscheck"] = {
            "status": "verified" if difference <= tolerance else "rejected",
            "independent_of_builder": True,
            "source": quote["source"],
            "source_url": quote["source_url"],
            "bar_date": quote["bar_date"],
            "completed_close": second_close,
            "verified_at_utc": verified_at,
            "difference_usd": difference,
            "tolerance_usd": tolerance,
        }

    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
