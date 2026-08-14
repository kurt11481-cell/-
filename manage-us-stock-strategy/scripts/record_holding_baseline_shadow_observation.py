#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from holding_baseline_operationalization import initialize_observation, record_observation, validate_managed_output_path
from validation_common import load_json, write_json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path)
    parser.add_argument("--ticker")
    parser.add_argument("--baseline-id")
    parser.add_argument("--baseline-hash")
    parser.add_argument("--activation-session")
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    protected = [path for path in (args.state, args.observation) if path]
    validate_managed_output_path(args.output, repo_root=repo_root,
                                 allowed_relative_root="workspace/state/holding_baseline_observations",
                                 protected=protected)
    if args.state:
        value = load_json(args.state)
        if args.observation: value = record_observation(value, load_json(args.observation))
    else:
        if not all((args.ticker, args.baseline_id, args.baseline_hash, args.activation_session)):
            parser.error("initialization requires ticker, baseline-id, baseline-hash, and activation-session")
        value = initialize_observation(ticker=args.ticker, baseline_id=args.baseline_id,
                                       baseline_hash=args.baseline_hash, activation_session=args.activation_session)
    write_json(args.output, value)
    return 0

if __name__ == "__main__": raise SystemExit(main())
