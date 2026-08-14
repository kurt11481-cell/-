#!/usr/bin/env python3
"""Independent disk-and-test judge for the NBIS v4 Shadow activation gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from typing import Any

from holding_baseline_operationalization import validate_baseline, validate_valuation_snapshot
from us_stock_price_authority import validate_price_authority_artifact
from validation_common import canonical_hash, file_hash, load_json, validate_instance


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _run(root: Path, args: list[str]) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *args], cwd=root, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    combined = result.stdout + "\n" + result.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    return {
        "returncode": result.returncode,
        "tests": int(match.group(1)) if match else None,
        "failures": 0 if result.returncode == 0 else 1,
        "result": "PASS" if result.returncode == 0 else "FAIL",
        "diagnostic_tail": [line for line in combined.splitlines()
                            if re.search(r"^(FAILED|FAIL:|ERROR:|Ran |OK$)", line)][-20:],
    }


def _protected(root: Path) -> dict[str, str]:
    return {
        "portfolio": file_hash(root / "stock-strategy-system/portfolio_state.json"),
        "holding_policy": file_hash(root / "workspace/policies/holding_research_baseline_policy.json"),
        "kiwoom_priority_policy": file_hash(root / "workspace/policies/kiwoom-session-aware-priority-policy.json"),
        "alert_policy": file_hash(root / "stock-strategy-system/alert_policy.json"),
        "live_runtime": file_hash(root / "workspace/state/holding_strategy_runtime.json"),
        "alert_runtime": file_hash(root / "stock-strategy-system/alert_runtime_state.json"),
        "tactical_runtime": file_hash(root / "workspace/state/tactical_radar_runtime.json"),
        "automation_runtime": file_hash(root / "workspace/state/automation_delivery_runtime.json"),
    }


def _recursive_true(value: Any, key: str, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for name, item in value.items():
            child = f"{path}.{name}"
            if name == key and item is True:
                found.append(child)
            found.extend(_recursive_true(item, key, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_recursive_true(item, key, f"{path}[{index}]"))
    return found


def judge(root: Path, output: Path) -> dict[str, Any]:
    rel = {
        "price": "workspace/research/nbis-shadow-activation/2026-08-13/v4/nbis-price-authority-v4.json",
        "capital": "workspace/research/nbis-shadow-activation/2026-08-13/v3/nbis-capital-structure-v3.json",
        "valuation": "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v4.json",
        "baseline": "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v4.json",
        "parent": "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v3.json",
        "event": "workspace/research/baseline-event-links/2026-08-13/v4/nbis-issuer-event-link.json",
        "compile": "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v4.json",
        "manifest": "workspace/outputs/activation/nbis-v2-shadow/20260814-v4/build-manifest.json",
    }
    docs = {name: load_json(root / path) for name, path in rel.items()}
    errors: list[str] = []
    price_errors = validate_price_authority_artifact(docs["price"])
    errors.extend(f"PRICE:{item}" for item in price_errors)
    if docs["price"].get("canonical_provider") != "KIWOOM_REST" or docs["price"].get("canonical_price") != 255.84:
        errors.append("KIWOOM_CANONICAL_PRICE_INVALID")
    if docs["price"].get("blocking") is not False:
        errors.append("DIAGNOSTIC_DIVERGENCE_BLOCKING")

    valuation_validation = validate_valuation_snapshot(
        docs["valuation"], root / "manage-us-stock-strategy/schemas/issuer-valuation-snapshot.schema.json"
    )
    errors.extend(f"VALUATION:{item}" for item in valuation_validation["errors"])
    if docs["valuation"].get("valuation_evidence_status") != "DIRECT_SCENARIO_VALIDATED":
        errors.append("VALUATION_EVIDENCE_NOT_DIRECT_SCENARIO_VALIDATED")
    price = Decimal("255.84")
    expected = {
        "LEGAL_BASIC_CARRYING_DEBT_CASE": (Decimal("271.855218") * price, Decimal("271.855218") * price + Decimal("503.6")),
        "ECONOMIC_BASIC_CARRYING_DEBT_CASE": (Decimal("292.921154") * price, Decimal("292.921154") * price + Decimal("503.6")),
        "CONVERTIBLE_SHARE_SETTLEMENT_CASE": (Decimal("358.97804025") * price, Decimal("358.97804025") * price - Decimal("7995.4")),
        "CONVERTIBLE_CASH_SETTLEMENT_CASE": (Decimal("292.921154") * price, Decimal("292.921154") * price + Decimal("2046.4")),
        "INITIAL_RATE_KNOWN_GROSS_STRESS_CASE": (Decimal("384.22323825") * price, Decimal("384.22323825") * price - Decimal("7995.4")),
    }
    for scenario in docs["valuation"]["valuation_scenarios"]:
        equity, enterprise = expected[scenario["scenario_id"]]
        if abs(Decimal(str(scenario["equity_value"])) - equity) > Decimal("0.000001"):
            errors.append(f"MARKET_CAP_ARITHMETIC:{scenario['scenario_id']}")
        if abs(Decimal(str(scenario["enterprise_value"])) - enterprise) > Decimal("0.000001"):
            errors.append(f"EV_ARITHMETIC:{scenario['scenario_id']}")
        if scenario.get("convertible_share_equivalent_included") and scenario.get("convertible_debt_included"):
            errors.append(f"CONVERTIBLE_DOUBLE_COUNT:{scenario['scenario_id']}")

    baseline_validation = validate_baseline(
        docs["baseline"], root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json"
    )
    errors.extend(f"BASELINE:{item}" for item in baseline_validation["errors"])
    if docs["baseline"].get("content_status") != "COMPLETE":
        errors.append("BASELINE_NOT_COMPLETE")
    if (docs["baseline"].get("supersedes_baseline_id") != docs["parent"].get("baseline_id") or
            docs["baseline"].get("supersedes_baseline_hash") != docs["parent"].get("baseline_hash")):
        errors.append("BASELINE_PARENT_HASH_MISMATCH")
    event_schema_errors = validate_instance(
        docs["event"], root / "manage-us-stock-strategy/schemas/baseline-event-link.schema.json"
    )
    errors.extend(f"EVENT:{item}" for item in event_schema_errors)
    if (docs["event"].get("link_validation_status") not in {"VALID", "PARTIAL_NONBLOCKING"} or
            docs["event"].get("event_effect") != "CONTEXT_ONLY"):
        errors.append("EVENT_LINK_NOT_ACTIVATABLE")
    compile_schema_errors = validate_instance(
        docs["compile"], root / "manage-us-stock-strategy/schemas/shadow-baseline-compile-result.schema.json"
    )
    errors.extend(f"COMPILE:{item}" for item in compile_schema_errors)
    if docs["compile"].get("shadow_compile_status") != "PASSED" or docs["compile"].get("remaining_conditions"):
        errors.append("SHADOW_COMPILE_NOT_READY")
    if (docs["compile"].get("candidate_baseline_hash") != docs["baseline"].get("baseline_hash") or
            docs["compile"].get("valuation_snapshot_hash") != docs["valuation"].get("snapshot_hash") or
            docs["compile"].get("event_link_hash") != docs["event"].get("link_hash")):
        errors.append("COMPILE_LINEAGE_MISMATCH")
    if (docs["compile"].get("quantity") is not None or
            docs["compile"].get("quantity_authority") != "none" or
            docs["compile"].get("order_authority") is not False):
        errors.append("COMPILE_AUTHORITY_BOUNDARY")
    for name, document in docs.items():
        errors.extend(f"{name}:{item}" for item in _recursive_true(document, "order_authority"))

    targeted = _run(root, ["-m", "unittest",
        "manage-us-stock-strategy/tests/test_nbis_v4_kiwoom_price_authority.py",
        "manage-us-stock-strategy/tests/test_v2_6_7_session_aware_kiwoom_priority.py", "-v"])
    full = _run(root, ["-m", "unittest", "discover", "-s", "manage-us-stock-strategy/tests", "-p", "test_*.py", "-v"])
    if targeted["returncode"] != 0:
        errors.append("TARGETED_TEST_FAILURE")
    if full["returncode"] != 0:
        errors.append("FULL_SUITE_FAILURE")
    diff = subprocess.run(["git", "diff", "--check"], cwd=root, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if diff.returncode != 0:
        errors.append("GIT_DIFF_CHECK_FAILED")
    protected = _protected(root)
    manifest = docs["manifest"]
    if not all(manifest.get("gates", {}).values()):
        errors.append("BUILD_MANIFEST_GATE_FAILED")
    status = "NBIS_V2_SHADOW_PREACTIVATION_VERIFIED" if not errors else "NBIS_V2_SHADOW_PREACTIVATION_BLOCKED"
    result = {
        "schema_version": "1.0", "final_judgment": status,
        "errors": errors, "targeted_tests": targeted, "full_suite": full,
        "schema_and_semantic_validation": "PASS" if not any(item.startswith(("PRICE:", "VALUATION:", "BASELINE:", "EVENT:", "COMPILE:")) for item in errors) else "FAIL",
        "price_lineage": "PASS" if "KIWOOM_CANONICAL_PRICE_INVALID" not in errors else "FAIL",
        "valuation_arithmetic": "PASS" if not any("ARITHMETIC" in item or "DOUBLE_COUNT" in item for item in errors) else "FAIL",
        "baseline_parent_hash": "PASS" if "BASELINE_PARENT_HASH_MISMATCH" not in errors else "FAIL",
        "compile_lineage": "PASS" if "COMPILE_LINEAGE_MISMATCH" not in errors else "FAIL",
        "protected_hashes": protected,
        "active_index_file_hash": file_hash(root / "workspace/research/holding-baselines/active-index.json"),
        "artifact_hashes": {name: file_hash(root / path) for name, path in rel.items()},
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    _atomic_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    result = judge(Path(args.repo_root).resolve(), Path(args.output).resolve())
    print(json.dumps({"final_judgment": result["final_judgment"], "errors": result["errors"],
                      "targeted_tests": result["targeted_tests"], "full_suite": result["full_suite"],
                      "output": str(Path(args.output))}, ensure_ascii=False))
    return 0 if result["final_judgment"] == "NBIS_V2_SHADOW_PREACTIVATION_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
