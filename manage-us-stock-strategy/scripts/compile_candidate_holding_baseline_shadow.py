#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from holding_baseline_operationalization import compile_shadow, validate_managed_output_path
from validation_common import load_json, write_json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--valuation", type=Path)
    parser.add_argument("--event-link", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--provider-scope", type=Path, required=True)
    parser.add_argument("--baseline-schema", type=Path, required=True)
    parser.add_argument("--live-strategy-state", required=True)
    parser.add_argument("--blocked-decision-class", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    protected = [args.baseline, args.event_link, args.overlay, args.portfolio,
                 args.policy, args.provider_scope, args.baseline_schema]
    if args.valuation: protected.append(args.valuation)
    validate_managed_output_path(args.output, repo_root=repo_root,
                                 allowed_relative_root="workspace/research/shadow-compiles",
                                 protected=protected)
    value = compile_shadow(baseline=load_json(args.baseline), valuation=load_json(args.valuation) if args.valuation else None,
                           event_link=load_json(args.event_link), overlay=load_json(args.overlay),
                           portfolio=load_json(args.portfolio), policy_path=args.policy,
                           provider_scope_path=args.provider_scope, portfolio_path=args.portfolio,
                           baseline_schema=args.baseline_schema, live_strategy_state=args.live_strategy_state,
                           blocked_decision_classes=args.blocked_decision_class)
    write_json(args.output, value)
    return 0 if value["shadow_compile_status"] != "FAILED" else 2

if __name__ == "__main__": raise SystemExit(main())
