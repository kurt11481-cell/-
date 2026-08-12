#!/usr/bin/env python3
"""Build and validate an immutable pre-open baseline from post-market artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


def build_baseline(report: dict[str, Any], manifest: dict[str, Any], *, git_commit: str,
                   strategy_version: str, policy_version: str, run_manifest_hash: str | None = None) -> dict[str, Any]:
    if report.get("run_phase") != "POST_MARKET":
        raise ValueError("baseline source must be a POST_MARKET report")
    components = report.get("component_artifacts") or {}
    payload = {
        "schema_version": "2.4", "run_phase": "POST_MARKET",
        "post_market_run_id": manifest.get("run_id") or f"POST-MARKET-{report.get('market_session')}",
        "post_market_session": report["market_session"], "generated_at": report["generated_at"],
        "git_commit": git_commit, "strategy_version": strategy_version, "policy_version": policy_version,
        "market_snapshot_hash": components["market_snapshot_hash"],
        "event_snapshot_hash": components["event_snapshot_hash"],
        "holding_strategy_hash": canonical_hash(report.get("holding_strategies")),
        "tactical_radar_hash": components["tactical_radar_hash"],
        "capital_redeployment_hash": components["capital_redeployment_hash"],
        "run_manifest_hash": run_manifest_hash or canonical_hash(manifest),
        "portfolio_strategy_report_hash": canonical_hash(report),
        "order_authority": False,
    }
    payload["baseline_hash"] = canonical_hash(payload)
    return payload


def validate_baseline(baseline: dict[str, Any], schema: Path) -> list[str]:
    errors = validate_instance(baseline, schema)
    if errors:
        return errors
    expected = canonical_hash({key: value for key, value in baseline.items() if key != "baseline_hash"})
    if baseline.get("baseline_hash") != expected:
        errors.append("post-market baseline hash mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--strategy-version", required=True)
    parser.add_argument("--policy-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    baseline = build_baseline(load_json(args.report), load_json(args.manifest), git_commit=args.git_commit,
        strategy_version=args.strategy_version, policy_version=args.policy_version, run_manifest_hash=file_hash(args.manifest))
    errors = validate_baseline(baseline, Path(__file__).resolve().parents[1] / "schemas" / "post-market-baseline.schema.json")
    if errors:
        raise SystemExit("baseline validation failed: " + "; ".join(errors))
    write_json(args.output, baseline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
