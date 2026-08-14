#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from holding_baseline_operationalization import build_baseline_event_link, validate_managed_output_path
from holding_research import utc_now
from validation_common import load_json, write_json

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--event-bundle", type=Path, required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--entity-role", choices=("DIRECT_PRODUCT", "DIRECT_ISSUER", "SUPPLEMENTAL_UNDERLYING"), required=True)
    parser.add_argument("--link-created-at", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    validate_managed_output_path(args.output, repo_root=repo_root,
                                 allowed_relative_root="workspace/research/baseline-event-links",
                                 protected=[args.baseline, args.event_bundle])
    value = build_baseline_event_link(load_json(args.baseline), load_json(args.event_bundle),
                                      event_bundle_path=args.event_bundle, ticker=args.ticker,
                                      entity_role=args.entity_role, link_created_at=args.link_created_at or utc_now())
    write_json(args.output, value)
    return 0

if __name__ == "__main__": raise SystemExit(main())
