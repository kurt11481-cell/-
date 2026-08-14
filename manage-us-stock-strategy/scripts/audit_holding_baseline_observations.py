#!/usr/bin/env python3
"""Audit holding-baseline Shadow observations without counting a session."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from holding_baseline_operationalization import FORMULA_VERSION
from validation_common import canonical_hash, file_hash, load_json


SUBJECTS = {
    "SOXL": {
        "compile": "workspace/research/shadow-compiles/2026-08-13/v2.6.14/soxl-shadow-compile.json",
        "observation": "workspace/state/holding-baseline-observations/SOXL/soxl-20260814-v2.json",
        "receipt": None,
    },
    "NBIS": {
        "compile": "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v4.json",
        "observation": "workspace/state/holding-baseline-observations/NBIS/nbis-20260814-v4.json",
        "receipt": "workspace/outputs/activation/nbis-v2-shadow/20260814-v4/activation-receipt.json",
    },
    "MVLL": {
        "compile": "workspace/research/shadow-compiles/2026-08-13/mvll-shadow-compile-v3.json",
        "observation": "workspace/state/holding-baseline-observations/MVLL/mvll-20260814-v3.json",
        "receipt": "workspace/outputs/activation/mvll-v2-shadow/20260814-v3/activation-receipt.json",
    },
}


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def audit(root: Path) -> dict[str, Any]:
    portfolio = root / "stock-strategy-system/portfolio_state.json"
    portfolio_before = file_hash(portfolio)
    policy_path = root / "workspace/policies/holding_research_baseline_policy.json"
    provider_path = root / "workspace/policies/kiwoom-session-aware-priority-policy.json"
    index = load_json(root / "workspace/research/holding-baselines/active-index.json")
    results = []
    for ticker, paths in SUBJECTS.items():
        active = index["active"][ticker]
        baseline_path = root / active["baseline_path"]
        baseline = load_json(baseline_path)
        compile_path = root / paths["compile"]
        compiled = load_json(compile_path)
        observation_path = root / paths["observation"]
        observation = load_json(observation_path)
        receipt = load_json(root / paths["receipt"]) if paths["receipt"] else None
        violations = []
        if observation["baseline_id"] != active["baseline_id"] or observation["baseline_hash"] != active["baseline_hash"]:
            violations.append("OBSERVATION_SUBJECT_MISMATCH")
        if compiled["candidate_baseline_id"] != active["baseline_id"] or compiled["candidate_baseline_hash"] != active["baseline_hash"]:
            violations.append("COMPILE_SUBJECT_MISMATCH")
        if observation.get("order_authority") is not False or compiled.get("order_authority") is not False:
            violations.append("ORDER_AUTHORITY_VIOLATION")
        if compiled.get("quantity") is not None or compiled.get("quantity_authority") != "none":
            violations.append("QUANTITY_AUTHORITY_VIOLATION")
        if ticker == "MVLL" and "EMA10_RECLAIM_RVOL20" not in compiled.get("blocked_decision_classes", []):
            violations.append("MVLL_TECHNICAL_BLOCK_MISSING")
        if observation.get("valid_sessions"):
            violations.append("UNEXPECTED_PRE_AUDIT_SESSION_COUNT")
        activation_time = receipt["activated_at"] if receipt else active["activated_at"]
        valid_count = len(observation.get("valid_sessions", []))
        results.append({
            "ticker": ticker,
            "subject_binding": {
                "baseline_id": active["baseline_id"], "baseline_sha256": file_hash(baseline_path),
                "baseline_hash": active["baseline_hash"], "compile_sha256": file_hash(compile_path),
                "strategy_content_sha256": canonical_hash(baseline),
                "policy_sha256": file_hash(policy_path), "provider_scope_sha256": file_hash(provider_path),
                "compiler_semantic_version": FORMULA_VERSION, "activation_timestamp": activation_time,
                "observation_record_hash": observation["record_hash"],
            },
            "kiwoom_price_authority": "REQUIRED_PER_FUTURE_SESSION",
            "diagnostic_shadow_divergence_blocking": False,
            "context_axes": {
                "technical_status": compiled.get("technical_status"),
                "event_status": compiled.get("event_status"),
                "risk_status": compiled.get("risk_status"),
                "portfolio_fit_status": compiled.get("portfolio_fit_status"),
            },
            "live_strategy_state": compiled.get("live_strategy_state"),
            "shadow_strategy_state": compiled.get("shadow_strategy_state"),
            "live_shadow_classification": (
                "POLICY_EQUIVALENT" if compiled.get("live_strategy_state") == compiled.get("shadow_strategy_state")
                else "EXPECTED_BASELINE_OR_FRESH_CONTEXT_EFFECT"
            ),
            "technical_boundary_block": "EMA10_RECLAIM_RVOL20" if ticker == "MVLL" else None,
            "valid_sessions": valid_count, "required_valid_sessions": observation["required_valid_sessions"],
            "remaining_sessions": observation["required_valid_sessions"] - valid_count,
            "observation_status": "SHADOW_OBSERVATION_IN_PROGRESS" if valid_count < observation["required_valid_sessions"] else "BASELINE_SHADOW_OBSERVATION_PASS_USER_APPROVAL_REQUIRED",
            "counting_eligibility": "EXCLUDED_AUDIT_RUN_NOT_A_DELIVERED_SCHEDULED_SESSION",
            "audit_increment": 0, "backfill": False, "promotion_authority": False,
            "quantity": None, "quantity_authority": "none", "order_authority": False,
            "critical_violations": violations,
        })
    portfolio_after = file_hash(portfolio)
    result = {
        "schema_version": "2.6.14", "audit_id": "holding-baseline-five-session-audit-20260814",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "READ_ONLY_OBSERVATION_AUDIT", "subjects": results,
        "overall_status": "SHADOW_OBSERVATION_IN_PROGRESS",
        "operational_session_increment": 0, "manual_or_replay_counted": False,
        "portfolio_hash_before": portfolio_before, "portfolio_hash_after": portfolio_after,
        "portfolio_unchanged": portfolio_before == portfolio_after,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
        "audit_hash": "0" * 64,
    }
    result["audit_hash"] = canonical_hash(_without_hash(result, "audit_hash"))
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = audit(root)
    output = root / "workspace/outputs/activation/holding-baseline-observation-audit/20260814/audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    violations = [v for row in result["subjects"] for v in row["critical_violations"]]
    print(json.dumps({"status": result["overall_status"] if not violations else "OBSERVATION_AUDIT_BLOCKED",
                      "subjects": {row["ticker"]: f'{row["valid_sessions"]}/{row["required_valid_sessions"]}' for row in result["subjects"]},
                      "violations": violations, "output": output.relative_to(root).as_posix()}, ensure_ascii=False))
    return 0 if not violations and result["portfolio_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
