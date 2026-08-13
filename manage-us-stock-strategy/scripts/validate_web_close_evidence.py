#!/usr/bin/env python3
"""Validate a Codex-acquired web close evidence artifact without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from price_evidence import validate_web_evidence
from validation_common import load_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    errors = validate_web_evidence(load_json(args.artifact))
    print(json.dumps({"status": "VALIDATED" if not errors else "REJECTED", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
