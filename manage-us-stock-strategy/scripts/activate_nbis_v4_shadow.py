#!/usr/bin/env python3
"""Atomically activate the independently judged NBIS v4 baseline in Shadow only."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from holding_baseline_operationalization import initialize_observation, validate_baseline
from us_stock_price_authority import validate_price_authority_artifact
from validation_common import canonical_hash, file_hash, load_json, validate_instance


SESSION = "2026-08-13"
BASELINE_REL = "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v4.json"
COMPILE_REL = "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v4.json"
PRICE_REL = "workspace/research/nbis-shadow-activation/2026-08-13/v4/nbis-price-authority-v4.json"
VALUATION_REL = "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v4.json"
EVENT_REL = "workspace/research/baseline-event-links/2026-08-13/v4/nbis-issuer-event-link.json"
INDEX_REL = "workspace/research/holding-baselines/active-index.json"
TARGET_REL = "workspace/research/holding-baselines/NBIS/nbis-20260814-v4.json"
OBS_REL = "workspace/state/holding-baseline-observations/NBIS/nbis-20260814-v4.json"
RECEIPT_REL = "workspace/outputs/activation/nbis-v2-shadow/20260814-v4/activation-receipt.json"


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    result = deepcopy(value)
    result.pop(field, None)
    return result


def _protected(root: Path) -> dict[str, str]:
    paths = {
        "portfolio": root / "stock-strategy-system/portfolio_state.json",
        "holding_policy": root / "workspace/policies/holding_research_baseline_policy.json",
        "kiwoom_priority_policy": root / "workspace/policies/kiwoom-session-aware-priority-policy.json",
        "alert_policy": root / "stock-strategy-system/alert_policy.json",
        "live_runtime": root / "workspace/state/holding_strategy_runtime.json",
        "alert_runtime": root / "stock-strategy-system/alert_runtime_state.json",
        "tactical_runtime": root / "workspace/state/tactical_radar_runtime.json",
        "automation_runtime": root / "workspace/state/automation_delivery_runtime.json",
    }
    return {name: file_hash(path) for name, path in paths.items()}


def _preconditions(root: Path, judge: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if judge.get("final_judgment") != "NBIS_V2_SHADOW_PREACTIVATION_VERIFIED":
        raise ValueError("PREACTIVATION_JUDGMENT_NOT_VERIFIED")
    if judge.get("full_suite", {}).get("failures") != 0:
        raise ValueError("FULL_SUITE_NOT_ZERO_FAILURES")
    baseline, compile_result, price, valuation, event_link = (
        load_json(root / relative) for relative in
        (BASELINE_REL, COMPILE_REL, PRICE_REL, VALUATION_REL, EVENT_REL)
    )
    baseline_validation = validate_baseline(
        baseline, root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json"
    )
    if baseline_validation.get("validation_status") != "PASSED":
        raise ValueError("BASELINE_REVALIDATION_FAILED")
    if validate_price_authority_artifact(price):
        raise ValueError("KIWOOM_PRICE_REVALIDATION_FAILED")
    if price.get("canonical_provider") != "KIWOOM_REST" or price.get("canonical_price") != 255.84:
        raise ValueError("KIWOOM_CANONICAL_PRICE_MISMATCH")
    if price.get("blocking") is not False or price.get("order_authority") is not False:
        raise ValueError("PRICE_AUTHORITY_BOUNDARY_FAILED")
    if valuation.get("valuation_evidence_status") != "DIRECT_SCENARIO_VALIDATED":
        raise ValueError("VALUATION_NOT_VALIDATED")
    if valuation.get("valuation_judgement_status") not in {"UNCLASSIFIED", "APPROVED_DETERMINISTIC"}:
        raise ValueError("VALUATION_JUDGMENT_INVALID")
    if (event_link.get("link_validation_status") not in {"VALID", "PARTIAL_NONBLOCKING"} or
            event_link.get("event_effect") != "CONTEXT_ONLY"):
        raise ValueError("EVENT_LINK_NOT_ACTIVATABLE")
    if compile_result.get("shadow_compile_status") != "PASSED" or compile_result.get("remaining_conditions"):
        raise ValueError("SHADOW_COMPILE_NOT_READY")
    if (compile_result.get("quantity") is not None or
            compile_result.get("quantity_authority") != "none" or
            compile_result.get("order_authority") is not False):
        raise ValueError("AUTHORITY_BOUNDARY_VIOLATION")
    if compile_result.get("candidate_baseline_hash") != baseline.get("baseline_hash"):
        raise ValueError("COMPILE_BASELINE_HASH_MISMATCH")
    if compile_result.get("valuation_snapshot_hash") != valuation.get("snapshot_hash"):
        raise ValueError("COMPILE_VALUATION_HASH_MISMATCH")
    if compile_result.get("event_link_hash") != event_link.get("link_hash"):
        raise ValueError("COMPILE_EVENT_HASH_MISMATCH")
    expected = judge.get("protected_hashes") or {}
    current = _protected(root)
    if expected != current:
        raise ValueError("PROTECTED_HASH_CHANGED_SINCE_JUDGMENT")
    return baseline, compile_result, price, valuation, event_link


def activate(root: Path, judge_path: Path) -> dict[str, Any]:
    judge = load_json(judge_path)
    baseline, compile_result, price, valuation, event_link = _preconditions(root, judge)
    index_path, target_path, obs_path, receipt_path = (
        root / relative for relative in (INDEX_REL, TARGET_REL, OBS_REL, RECEIPT_REL)
    )
    if target_path.exists() or obs_path.exists() or receipt_path.exists():
        raise ValueError("ACTIVATION_TARGET_ALREADY_EXISTS")
    index_before_bytes = index_path.read_bytes()
    index_before = json.loads(index_before_bytes.decode("utf-8"))
    if file_hash(index_path) != judge.get("active_index_file_hash"):
        raise ValueError("ACTIVE_INDEX_CHANGED_SINCE_JUDGMENT")
    unrelated_before = deepcopy({k: v for k, v in index_before["active"].items() if k != "NBIS"})
    protected_before = _protected(root)
    lock_path = receipt_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    owner = str(uuid.uuid4())
    descriptor = None
    created: list[Path] = []
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump({"owner_token": owner, "purpose": "NBIS_V4_SHADOW_ACTIVATION"}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        activated_at = datetime.now(timezone.utc).isoformat()
        activated = deepcopy(baseline)
        activated["validation_status"] = "VALIDATED_SHADOW"
        activated["activated_at"] = activated_at
        _atomic_json(target_path, activated)
        created.append(target_path)
        previous = index_before["active"].get("NBIS")
        index_after = deepcopy(index_before)
        index_after["active"]["NBIS"] = {
            "baseline_id": baseline["baseline_id"],
            "baseline_version": baseline["baseline_version"],
            "baseline_hash": baseline["baseline_hash"],
            "research_packet_hash": baseline["research_packet_hash"],
            "activated_at": activated_at,
            "baseline_path": TARGET_REL,
            "supersedes_baseline_id": previous.get("baseline_id") if previous else None,
        }
        index_after["updated_at"] = activated_at
        _atomic_json(index_path, index_after)
        observation = initialize_observation(
            ticker="NBIS", baseline_id=baseline["baseline_id"],
            baseline_hash=baseline["baseline_hash"], activation_session=SESSION,
        )
        observation["backfill"] = False
        observation["historical_sessions"] = []
        observation["record_hash"] = canonical_hash(_without_hash(observation, "record_hash"))
        _atomic_json(obs_path, observation)
        created.append(obs_path)
        protected_after = _protected(root)
        receipt = {
            "schema_version": "1.0",
            "receipt_id": f"nbis-v4-shadow-{uuid.uuid4()}",
            "ticker": "NBIS", "mode": "SHADOW", "activated_at": activated_at,
            "activation_session": SESSION, "baseline_id": baseline["baseline_id"],
            "baseline_hash": baseline["baseline_hash"],
            "compile_hash": file_hash(root / COMPILE_REL),
            "price_authority_hash": price["evidence_hash"],
            "valuation_snapshot_hash": valuation["snapshot_hash"],
            "event_link_hash": event_link["link_hash"],
            "prior_index_hash": canonical_hash(index_before),
            "new_index_hash": canonical_hash(index_after),
            "observation_hash": observation["record_hash"],
            "required_valid_sessions": 5, "valid_sessions": 0,
            "backfill": False, "historical_sessions": [],
            "portfolio_hash_before": protected_before["portfolio"],
            "portfolio_hash_after": protected_after["portfolio"],
            "policy_hash_before": protected_before["holding_policy"],
            "policy_hash_after": protected_after["holding_policy"],
            "live_runtime_hash_before": protected_before["live_runtime"],
            "live_runtime_hash_after": protected_after["live_runtime"],
            "quantity": None, "quantity_authority": "none", "order_authority": False,
            "validation_status": "NBIS_V2_SHADOW_ACTIVATION_VERIFIED",
            "receipt_hash": "0" * 64,
        }
        receipt["receipt_hash"] = canonical_hash(_without_hash(receipt, "receipt_hash"))
        _atomic_json(receipt_path, receipt)
        created.append(receipt_path)

        # Independent post-write reload validation.
        reloaded_index, reloaded_observation, reloaded_receipt = (
            load_json(path) for path in (index_path, obs_path, receipt_path)
        )
        errors = validate_instance(
            reloaded_receipt,
            root / "manage-us-stock-strategy/schemas/holding-baseline-activation-receipt.schema.json",
        )
        if errors or reloaded_receipt["receipt_hash"] != canonical_hash(_without_hash(reloaded_receipt, "receipt_hash")):
            raise ValueError("ACTIVATION_RECEIPT_INVALID")
        if list(ticker for ticker in reloaded_index["active"] if ticker == "NBIS") != ["NBIS"]:
            raise ValueError("NBIS_INDEX_CARDINALITY_INVALID")
        if reloaded_index["active"]["NBIS"]["baseline_hash"] != baseline["baseline_hash"]:
            raise ValueError("NBIS_ACTIVE_BASELINE_HASH_MISMATCH")
        if {k: v for k, v in reloaded_index["active"].items() if k != "NBIS"} != unrelated_before:
            raise ValueError("UNRELATED_TICKER_STATE_CHANGED")
        if (reloaded_observation.get("required_valid_sessions") != 5 or
                reloaded_observation.get("valid_sessions") != [] or
                reloaded_observation.get("observed_sessions") != [] or
                reloaded_observation.get("backfill") is not False or
                reloaded_observation.get("historical_sessions") != []):
            raise ValueError("OBSERVATION_NOT_ZERO_OF_FIVE")
        if _protected(root) != protected_before:
            raise ValueError("PROTECTED_STATE_MUTATED")
        return {
            "status": "NBIS_V2_SHADOW_ACTIVATION_VERIFIED",
            "baseline_id": baseline["baseline_id"],
            "receipt_path": RECEIPT_REL,
            "observation": "0/5",
            "quantity": None, "quantity_authority": "none", "order_authority": False,
        }
    except Exception:
        _atomic_bytes(index_path, index_before_bytes)
        for path in reversed(created):
            if path.exists():
                path.unlink()
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock_path.exists():
            try:
                existing = json.loads(lock_path.read_text(encoding="utf-8"))
                if existing.get("owner_token") == owner:
                    lock_path.unlink()
            except (json.JSONDecodeError, OSError):
                pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    try:
        result = activate(Path(args.repo_root).resolve(), Path(args.judge).resolve())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "NBIS_V2_SHADOW_ACTIVATION_ROLLED_BACK", "blocker": str(exc),
                          "quantity": None, "quantity_authority": "none", "order_authority": False},
                         ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
