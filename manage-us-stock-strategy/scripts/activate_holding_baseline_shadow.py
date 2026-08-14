#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from holding_baseline_operationalization import activate_shadow_candidate
from holding_research import utc_now
from validation_common import load_json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--compile-result", type=Path, required=True)
    parser.add_argument("--baseline-schema", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--expected-prior-index-hash", required=True)
    parser.add_argument("--activated-at", default=None)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    expected_root = (repo_root / "workspace/research/holding-baselines").resolve()
    expected_index = (expected_root / "active-index.json").resolve()
    if args.baseline_root.resolve() != expected_root or args.index.resolve() != expected_index:
        parser.error("activation requires the canonical holding-baselines root and active-index path")
    result = activate_shadow_candidate(baseline=load_json(args.baseline), compile_result=load_json(args.compile_result),
                                       baseline_schema=args.baseline_schema, baseline_root=args.baseline_root,
                                       index_path=args.index, expected_prior_index_hash=args.expected_prior_index_hash,
                                       activated_at=args.activated_at or utc_now())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["activation_status"] == "VALIDATED_SHADOW" else 2

if __name__ == "__main__": raise SystemExit(main())
