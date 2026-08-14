#!/usr/bin/env python3
"""Atomically activate the validated MVLL successor in Shadow only."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

from holding_baseline_operationalization import activate_shadow_candidate, initialize_observation
from us_stock_price_authority import validate_price_authority_artifact
from validation_common import canonical_hash, file_hash, load_json, validate_instance


SESSION = "2026-08-13"
BASELINE_REL = "workspace/research/holding-baseline-candidates/2026-08-14/mvll-20260814-v3.json"
COMPILE_REL = "workspace/research/shadow-compiles/2026-08-13/mvll-shadow-compile-v3.json"
PRICE_REL = "workspace/research/mvll-shadow-activation/2026-08-13/v3/mvll-price-authority-v3.json"
VALUATION_REL = "workspace/research/valuation-snapshots/2026-08-13/mrvl-valuation-snapshot-v3.json"
EVENT_REL = "workspace/research/baseline-event-links/2026-08-13/v2.6.14/mvll-v3-product-event-link.json"
INDEX_REL = "workspace/research/holding-baselines/active-index.json"
TARGET_REL = "workspace/research/holding-baselines/MVLL/mvll-20260814-v3.json"
OBS_REL = "workspace/state/holding-baseline-observations/MVLL/mvll-20260814-v3.json"
RECEIPT_REL = "workspace/outputs/activation/mvll-v2-shadow/20260814-v3/activation-receipt.json"


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    paths = {name: root / rel for name, rel in {
        "baseline": BASELINE_REL, "compile": COMPILE_REL, "price": PRICE_REL,
        "valuation": VALUATION_REL, "event": EVENT_REL, "index": INDEX_REL,
        "target": TARGET_REL, "observation": OBS_REL, "receipt": RECEIPT_REL,
    }.items()}
    portfolio = root / "stock-strategy-system/portfolio_state.json"
    policy = root / "workspace/policies/holding_research_baseline_policy.json"
    live_runtime = root / "workspace/state/holding_strategy_runtime.json"
    protected_before = {"portfolio": file_hash(portfolio), "policy": file_hash(policy), "live_runtime": file_hash(live_runtime)}

    baseline = load_json(paths["baseline"])
    compiled = load_json(paths["compile"])
    price = load_json(paths["price"])
    valuation = load_json(paths["valuation"])
    event_link = load_json(paths["event"])
    manifest = load_json(root / "workspace/outputs/activation/mvll-v2-shadow/20260814-v3/build-manifest.json")
    errors: list[str] = []
    if not all(manifest.get("gates", {}).values()): errors.append("BUILD_MANIFEST_GATE_FAILED")
    errors.extend(validate_price_authority_artifact(price))
    if price.get("canonical_provider") != "KIWOOM_REST": errors.append("CANONICAL_PROVIDER_NOT_KIWOOM")
    if valuation.get("valuation_evidence_status") != "SCENARIO_VALIDATED": errors.append("VALUATION_NOT_VALIDATED")
    if valuation.get("valuation_judgement_status") != "UNCLASSIFIED": errors.append("UNEXPECTED_VALUATION_JUDGEMENT")
    if event_link.get("link_validation_status") not in {"VALID", "PARTIAL_NONBLOCKING"}: errors.append("EVENT_LINK_NOT_ACTIVATABLE")
    if compiled.get("shadow_compile_status") != "PASSED" or compiled.get("remaining_conditions"): errors.append("SHADOW_COMPILE_NOT_READY")
    if "EMA10_RECLAIM_RVOL20" not in compiled.get("blocked_decision_classes", []): errors.append("TECHNICAL_BOUNDARY_BLOCK_MISSING")
    if compiled.get("quantity") is not None or compiled.get("quantity_authority") != "none" or compiled.get("order_authority") is not False:
        errors.append("AUTHORITY_BOUNDARY_VIOLATION")
    if errors:
        print(json.dumps({"status": "MVLL_V2_SHADOW_ACTIVATION_BLOCKED", "errors": errors}, ensure_ascii=False))
        return 1

    index_before_bytes = paths["index"].read_bytes()
    index_before = json.loads(index_before_bytes.decode("utf-8"))
    prior_index_hash = canonical_hash(index_before)
    owned_preexistence = {key: paths[key].exists() for key in ("target", "observation", "receipt")}
    owned_previous = {key: paths[key].read_bytes() if owned_preexistence[key] else None for key in owned_preexistence}
    activated_at = datetime.now(timezone.utc).isoformat()
    try:
        activation = activate_shadow_candidate(
            baseline=baseline, compile_result=compiled,
            baseline_schema=root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",
            baseline_root=root / "workspace/research/holding-baselines",
            index_path=paths["index"], expected_prior_index_hash=prior_index_hash,
            activated_at=activated_at,
        )
        if activation.get("activation_status") not in {"ACTIVATED", "VALIDATED_SHADOW"}:
            raise RuntimeError("ACTIVATION_REJECTED:" + json.dumps(activation, ensure_ascii=False, sort_keys=True))
        observation = initialize_observation(
            ticker="MVLL", baseline_id=baseline["baseline_id"], baseline_hash=baseline["baseline_hash"],
            activation_session=SESSION,
        )
        _atomic_json(paths["observation"], observation)
        protected_after = {"portfolio": file_hash(portfolio), "policy": file_hash(policy), "live_runtime": file_hash(live_runtime)}
        if protected_before != protected_after:
            raise RuntimeError("PROTECTED_STATE_MUTATION")
        reloaded_index = load_json(paths["index"])
        active = reloaded_index["active"]["MVLL"]
        if active["baseline_id"] != baseline["baseline_id"] or active["baseline_hash"] != baseline["baseline_hash"]:
            raise RuntimeError("ACTIVE_INDEX_RELOAD_MISMATCH")
        if load_json(paths["observation"])["valid_sessions"]:
            raise RuntimeError("OBSERVATION_BACKFILL_PROHIBITED")
        receipt = {
            "schema_version": "1.0", "receipt_id": f"mvll-v3-shadow-{uuid4()}",
            "ticker": "MVLL", "mode": "SHADOW", "activated_at": activated_at,
            "activation_session": SESSION, "baseline_id": baseline["baseline_id"],
            "baseline_hash": baseline["baseline_hash"], "compile_hash": file_hash(paths["compile"]),
            "price_authority_hash": price["evidence_hash"], "valuation_snapshot_hash": valuation["snapshot_hash"],
            "event_link_hash": event_link["link_hash"], "prior_index_hash": prior_index_hash,
            "new_index_hash": canonical_hash(reloaded_index), "observation_hash": observation["record_hash"],
            "required_valid_sessions": 5, "valid_sessions": 0, "backfill": False, "historical_sessions": [],
            "portfolio_hash_before": protected_before["portfolio"], "portfolio_hash_after": protected_after["portfolio"],
            "policy_hash_before": protected_before["policy"], "policy_hash_after": protected_after["policy"],
            "live_runtime_hash_before": protected_before["live_runtime"], "live_runtime_hash_after": protected_after["live_runtime"],
            "quantity": None, "quantity_authority": "none", "order_authority": False,
            "technical_boundary_block": "EMA10_RECLAIM_RVOL20",
            "validation_status": "MVLL_VALIDATED_SHADOW_WITH_DECISION_CLASS_BLOCK",
            "receipt_hash": "0" * 64,
        }
        receipt["receipt_hash"] = canonical_hash(_without_hash(receipt, "receipt_hash"))
        _atomic_json(paths["receipt"], receipt)
        schema_errors = validate_instance(receipt, root / "manage-us-stock-strategy/schemas/holding-baseline-activation-receipt.schema.json")
        if schema_errors:
            raise RuntimeError("RECEIPT_SCHEMA_FAILED:" + ";".join(schema_errors))
    except Exception as exc:
        _atomic_bytes(paths["index"], index_before_bytes)
        for key in ("target", "observation", "receipt"):
            if owned_preexistence[key]:
                _atomic_bytes(paths[key], owned_previous[key] or b"")
            elif paths[key].exists():
                paths[key].unlink()
        print(json.dumps({"status": "MVLL_V2_SHADOW_ACTIVATION_ROLLED_BACK", "error": repr(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({"status": "MVLL_VALIDATED_SHADOW_WITH_DECISION_CLASS_BLOCK", "baseline_id": baseline["baseline_id"],
                      "observation": "0/5", "receipt": RECEIPT_REL, "order_authority": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
