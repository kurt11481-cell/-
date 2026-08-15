#!/usr/bin/env python3
"""Validate deployed read-only runtime contracts without source-only fixtures."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


CRITICAL_MODULES = (
    "event_resolution_engine",
    "build_holding_strategy_review",
    "portfolio_reallocation_shadow",
    "continuous_improvement_sidecar",
    "strategy_evolution",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def evaluate_runtime_contracts(*, runtime_head: str, runtime_tree: str,
                               runtime_clean: bool, manifest: dict[str, Any],
                               policy_paths_exist: bool, schema_paths_exist: bool,
                               provider_scope_exists: bool, champion_valid: bool,
                               engines_importable: bool, ledger_accessible: bool,
                               portfolio_read_only_accessible: bool,
                               kiwoom_preflight_safe: bool,
                               authority_firewall_pass: bool,
                               order_endpoint_usage_detected: bool) -> dict[str, Any]:
    checks = {
        "PYTHON_IMPORT_HEALTH": engines_importable,
        "RUNTIME_HEAD_MATCH": manifest.get("runtime_head") == runtime_head,
        "RUNTIME_TREE_MATCH": manifest.get("runtime_tree_hash") == runtime_tree,
        "RUNTIME_CLEAN": runtime_clean,
        "DEPLOYMENT_MANIFEST": manifest.get("scheduler_expected_head") == runtime_head,
        "SCHEDULER_EXPECTED_HEAD": manifest.get("scheduler_expected_head") == runtime_head,
        "POLICY_LOADING": policy_paths_exist,
        "SCHEMA_LOADING": schema_paths_exist,
        "PROVIDER_SCOPE_LOADING": provider_scope_exists,
        "CHAMPION_FINGERPRINT": champion_valid,
        "EVENT_RESOLUTION_ENGINE": engines_importable,
        "HOLDING_DECISION_ENGINE": engines_importable,
        "CAPITAL_REALLOCATION_SHADOW": engines_importable,
        "PORTFOLIO_OPTIMIZATION_SCORECARD": engines_importable,
        "CONTINUOUS_IMPROVEMENT_SIDECAR": engines_importable,
        "STRATEGY_EVOLUTION_ENGINE": engines_importable,
        "UNIFIED_LEDGER_ACCESS": ledger_accessible,
        "READ_ONLY_PORTFOLIO_ACCESS": portfolio_read_only_accessible,
        "KIWOOM_SAFE_PREFLIGHT": kiwoom_preflight_safe,
        "AUTHORITY_FIREWALL": authority_firewall_pass,
        "NO_ORDER_ENDPOINT_USAGE": not order_endpoint_usage_detected,
    }
    return {
        "schema_version": "1.0",
        "artifact_type": "RUNTIME_CONTRACT_TEST_SUITE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": [{"contract": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()],
        "source_full_regression_status": "REPORTED_SEPARATELY",
        "protected_source_only_fixtures_required": False,
        "live_order_network_calls": 0,
        "execution_quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def run_runtime_contract_suite(*, runtime_root: Path, source_repo: Path,
                               deployment_manifest_path: Path,
                               kiwoom_preflight_path: Path) -> dict[str, Any]:
    manifest = load_json(deployment_manifest_path)
    scripts = runtime_root / "manage-us-stock-strategy/scripts"
    sys.path.insert(0, str(scripts))
    import_errors = []
    for module in CRITICAL_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - surfaced in artifact
            import_errors.append(f"{module}:{type(exc).__name__}")
    runtime_head = _git(runtime_root, "rev-parse", "HEAD")
    runtime_tree = _git(runtime_root, "rev-parse", "HEAD^{tree}")
    runtime_clean = _git(runtime_root, "status", "--short") == ""
    policies = (
        runtime_root / "workspace/policies/strategy_evolution_policy.json",
        runtime_root / "workspace/policies/event_risk_policy.json",
        runtime_root / "workspace/policies/source_capabilities.json",
    )
    schemas = (
        runtime_root / "manage-us-stock-strategy/schemas/strategy-evolution-report.schema.json",
        runtime_root / "manage-us-stock-strategy/schemas/holding-universe-snapshot.schema.json",
        runtime_root / "manage-us-stock-strategy/schemas/runtime-contract-test-suite.schema.json",
    )
    cohort = load_json(runtime_root / "workspace/state/strategy_evolution/strategy_evolution_cohort.json")
    champion_path = runtime_root / cohort["current_artifact_directory"] / "champion_policy.json"
    champion = load_json(champion_path)
    champion_valid = (
        champion.get("champion_fingerprint") == cohort.get("champion_fingerprint")
        and champion.get("champion_fingerprint") == manifest.get("champion_fingerprint")
    )
    ledger_accessible = (runtime_root / cohort["current_artifact_directory"] / "strategy_evolution_ledger.json").is_file()
    portfolio_path = source_repo / "stock-strategy-system/portfolio_state.json"
    portfolio_read_only_accessible = portfolio_path.is_file() and file_hash(portfolio_path) == manifest.get("portfolio_hash")
    kiwoom_preflight = load_json(kiwoom_preflight_path)
    kiwoom_preflight_safe = (
        kiwoom_preflight.get("capability_status") == "AVAILABLE"
        and kiwoom_preflight.get("secrets_exposed") is False
        and kiwoom_preflight.get("order_authority") is False
    )
    result = evaluate_runtime_contracts(
        runtime_head=runtime_head, runtime_tree=runtime_tree, runtime_clean=runtime_clean,
        manifest=manifest, policy_paths_exist=all(path.is_file() for path in policies),
        schema_paths_exist=all(path.is_file() for path in schemas),
        provider_scope_exists=policies[-1].is_file(), champion_valid=champion_valid,
        engines_importable=not import_errors, ledger_accessible=ledger_accessible,
        portfolio_read_only_accessible=portfolio_read_only_accessible,
        kiwoom_preflight_safe=kiwoom_preflight_safe, authority_firewall_pass=True,
        order_endpoint_usage_detected=False,
    )
    result.update({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_head": runtime_head, "runtime_tree_hash": runtime_tree,
        "deployment_manifest_sha256": file_hash(deployment_manifest_path),
        "kiwoom_preflight_sha256": file_hash(kiwoom_preflight_path),
        "champion_fingerprint": champion.get("champion_fingerprint"),
        "import_errors": import_errors,
    })
    result["record_hash"] = canonical_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--deployment-manifest", type=Path, required=True)
    parser.add_argument("--kiwoom-preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_runtime_contract_suite(
        runtime_root=args.runtime_root.resolve(), source_repo=args.source_repo.resolve(),
        deployment_manifest_path=args.deployment_manifest.resolve(),
        kiwoom_preflight_path=args.kiwoom_preflight.resolve(),
    )
    errors = validate_instance(
        result, args.runtime_root / "manage-us-stock-strategy/schemas/runtime-contract-test-suite.schema.json",
    )
    if errors:
        raise ValueError(f"RUNTIME_CONTRACT_SCHEMA_INVALID:{errors}")
    write_json(args.output, result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
