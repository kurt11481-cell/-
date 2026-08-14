#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from holding_baseline_operationalization import build_issuer_valuation_snapshot, validate_managed_output_path
from validation_common import load_json, write_json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    validate_managed_output_path(args.output, repo_root=repo_root,
                                 allowed_relative_root="workspace/research/valuation-snapshots",
                                 protected=[args.input])
    write_json(args.output, build_issuer_valuation_snapshot(load_json(args.input)))
    return 0

if __name__ == "__main__": raise SystemExit(main())
