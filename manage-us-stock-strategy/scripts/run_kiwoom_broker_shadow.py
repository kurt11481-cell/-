#!/usr/bin/env python3
"""Run one sanitized, read-only Kiwoom U.S. account Shadow snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from kiwoom_broker_shadow import normalize_snapshot, reconciliation_proposal
from kiwoom_account_readonly_bridge import invoke_account_bridge_batch
from validation_common import file_hash, load_json, validate_instance, write_json


OPERATIONS = (
    "account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
    "account_open_items", "account_fills_read", "account_realized_pnl_read",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--broker-policy", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--snapshot-role", required=True)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    before = file_hash(args.portfolio_state)
    broker_policy = load_json(args.broker_policy)
    results = invoke_account_bridge_batch([{"operation": operation} for operation in OPERATIONS],
                                          runtime=args.runtime, policy=load_json(args.rate_policy))
    generated_at = datetime.now(timezone.utc).isoformat()
    snapshot = normalize_snapshot(results, snapshot_role=args.snapshot_role, generated_at=generated_at,
                                  maximum_age_seconds=int(broker_policy["maximum_age_seconds"]))
    proposal = reconciliation_proposal(snapshot, load_json(args.portfolio_state), expected_before_hash=before)
    after = file_hash(args.portfolio_state)
    if before != after:
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    errors = validate_instance(snapshot, Path(__file__).resolve().parents[1] / "schemas/kiwoom-broker-shadow.schema.json")
    if errors:
        raise SystemExit("BROKER_SHADOW_SCHEMA_FAILED:" + ";".join(errors))
    args.output_directory.mkdir(parents=True, exist_ok=True)
    write_json(args.output_directory / "kiwoom_broker_snapshot.shadow.json", snapshot)
    write_json(args.output_directory / "reconciliation_proposal.json", proposal)
    print(snapshot["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
