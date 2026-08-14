#!/usr/bin/env python3
"""Run a fresh read-only Kiwoom account snapshot and future visibility audit."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from broker_visibility_audit import build_audit
from kiwoom_account_readonly_bridge import invoke_account_bridge_batch
from kiwoom_broker_shadow import normalize_snapshot
from run_kiwoom_broker_shadow import OPERATIONS
from validation_common import file_hash, load_json, validate_instance, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--broker-policy", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    before = file_hash(args.portfolio_state)
    broker_policy = load_json(args.broker_policy)
    results = invoke_account_bridge_batch([{"operation": operation} for operation in OPERATIONS],
                                          runtime=args.runtime, policy=load_json(args.rate_policy))
    snapshot = normalize_snapshot(results, snapshot_role="PRE_OPEN_BROKER_SNAPSHOT",
                                  generated_at=datetime.now(timezone.utc).isoformat(),
                                  maximum_age_seconds=int(broker_policy["maximum_age_seconds"]))
    audit = build_audit(results=results, snapshot=snapshot)
    if before != file_hash(args.portfolio_state):
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    errors = validate_instance(audit, args.schema)
    if errors:
        raise SystemExit("BROKER_VISIBILITY_SCHEMA_FAILED:" + ";".join(errors))
    args.output_directory.mkdir(parents=True, exist_ok=True)
    write_json(args.output_directory / "broker_snapshot.shadow.json", snapshot)
    write_json(args.output_directory / "future_execution_broker_visibility.json", audit)
    print(audit["current_readonly_readiness"])
    print(audit["broker_visibility_for_live_execution"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
