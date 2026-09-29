#!/usr/bin/env python3
"""Run one sanitized, read-only Kiwoom U.S. account Shadow snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kiwoom_broker_shadow import normalize_snapshot, reconciliation_proposal
from kiwoom_account_readonly_bridge import invoke_account_bridge_batch
from validation_common import file_hash, load_json, validate_instance, write_json


OPERATIONS = (
    "account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
    "account_open_items", "account_fills_read", "account_realized_pnl_read",
)
REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_SCHEMA = Path(__file__).resolve().parents[1] / "schemas/kiwoom-broker-shadow.schema.json"


def repo_relative(path: Path) -> str:
    """Repository-relative POSIX path so a proposal made on Windows resolves on the Linux VM."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def collect_broker_snapshot(*, runtime: Path, rate_policy: dict[str, Any], broker_policy: dict[str, Any],
                            snapshot_role: str, portfolio_state: Path,
                            reader: Callable[..., list[dict[str, Any]]] = invoke_account_bridge_batch,
                            ) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    """Read the account once (read-only), normalize it, and prove the state file was not touched."""
    before = file_hash(portfolio_state)
    results = reader([{"operation": operation} for operation in OPERATIONS], runtime=runtime, policy=rate_policy)
    generated_at = datetime.now(timezone.utc).isoformat()
    snapshot = normalize_snapshot(results, snapshot_role=snapshot_role, generated_at=generated_at,
                                  maximum_age_seconds=int(broker_policy["maximum_age_seconds"]))
    if file_hash(portfolio_state) != before:
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    errors = validate_instance(snapshot, SNAPSHOT_SCHEMA)
    if errors:
        raise SystemExit("BROKER_SHADOW_SCHEMA_FAILED:" + ";".join(errors))
    return results, snapshot, before


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--broker-policy", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--snapshot-role", required=True)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    broker_policy = load_json(args.broker_policy)
    results, snapshot, before = collect_broker_snapshot(
        runtime=args.runtime, rate_policy=load_json(args.rate_policy), broker_policy=broker_policy,
        snapshot_role=args.snapshot_role, portfolio_state=args.portfolio_state,
    )
    # Shadow output only: without the post-apply alert-engine check this proposal stays BLOCKED.
    # Applicable proposals come from reconcile_broker_state.py propose.
    proposal = reconciliation_proposal(
        snapshot, load_json(args.portfolio_state), results=results,
        maximum_age_seconds=int(broker_policy["maximum_age_seconds"]),
        portfolio_state_path=repo_relative(args.portfolio_state),
        snapshot_path=repo_relative(args.output_directory / "kiwoom_broker_snapshot.shadow.json"),
    )
    if file_hash(args.portfolio_state) != before:
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    write_json(args.output_directory / "kiwoom_broker_snapshot.shadow.json", snapshot)
    write_json(args.output_directory / "reconciliation_proposal.json", proposal)
    print(snapshot["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
