#!/usr/bin/env python3
"""Run bounded Kiwoom read-only discovery without granting universe authority."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kiwoom_candidate_discovery_bridge import (
    classify_instrument, deduplicate_candidates, invoke_discovery_bridge_batch,
)
from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


DEFAULT_OPERATIONS = (
    "condition_list",
    "volume_rank_stock", "volume_rank_etf", "volume_surge_stock", "volume_surge_etf",
    "change_rate_stock", "change_rate_etf", "market_cap_rank_stock",
    "market_cap_rank_etf", "new_high_low_stock", "new_high_low_etf",
    "price_movement_stock", "price_movement_etf",
)


def build_artifact(results: list[dict[str, Any]], runtime_commit: str | None = None,
                   identity_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = [row for result in results if result.get("bridge_status") == "PASS"
            and result.get("operation") != "condition_list"
            for row in result.get("data") or []]
    failures = [failure for result in results for failure in result.get("ticker_failures") or []]
    statuses = {str(result.get("operation")): str(result.get("bridge_status")) for result in results}
    operation_failures = [
        {"operation": result.get("operation"), "status": result.get("bridge_status"),
         "failure_type": result.get("failure_type")}
        for result in results if result.get("bridge_status") != "PASS"
    ]
    candidates = deduplicate_candidates(rows)
    identities = {}
    for result in identity_results or []:
        if result.get("bridge_status") != "PASS" or not result.get("data"):
            continue
        row = result["data"][0]
        key = (str(row.get("canonical_ticker") or ""), str(row.get("stex_tp") or ""))
        if all(key):
            identities[key] = row
    for candidate in candidates:
        key = (candidate["canonical_ticker"], str(candidate.get("stex_tp") or ""))
        identity = identities.get(key)
        candidate["identity_status"] = "VERIFIED" if identity else "PENDING"
        if identity:
            candidate.update({field: identity.get(field) for field in
                              ("stk_nm", "stk_enm", "isEtf", "mkgb", "upgb") if identity.get(field) is not None})
            candidate["instrument_class"] = classify_instrument(candidate)
            candidate["lifecycle_state"] = "IDENTITY_VERIFIED"
            candidate["remaining_conditions"] = ["MARKET_PHASE_VERIFICATION_REQUIRED", "TECHNICAL_HISTORY_PENDING", "DEEP_RESEARCH_PENDING", "USER_WATCHLIST_APPROVAL_REQUIRED"]
        else:
            candidate["remaining_conditions"] = ["IDENTITY_VERIFICATION_PENDING", "USER_WATCHLIST_APPROVAL_REQUIRED"]
    passed = sum(status == "PASS" for status in statuses.values())
    status = ("CANDIDATE_DISCOVERY_OPERATION_COMPLETE" if passed == len(statuses) and statuses
              else "CANDIDATE_DISCOVERY_PARTIAL" if passed else "CANDIDATE_DISCOVERY_FAILED")
    value = {
        "schema_version": "1.0", "status": status, "provider": "KIWOOM_REST",
        "runtime_commit": runtime_commit or next((result.get("runtime_commit") for result in results
                                                   if result.get("runtime_commit")), None),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "operation_statuses": statuses, "operation_failures": operation_failures,
        "candidates": candidates,
        "ticker_failures": failures, "deduplicated_count": len(candidates),
        "watchlist_authority": False, "active_universe_authority": False,
        "new_buy_authority": False, "portfolio_mutation": False,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
        "record_hash": "0" * 64,
    }
    value["record_hash"] = canonical_hash({key: item for key, item in value.items() if key != "record_hash"})
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    before = file_hash(args.portfolio_state)
    policy = load_json(args.policy)
    results = invoke_discovery_bridge_batch(
        [{"operation": operation} for operation in DEFAULT_OPERATIONS], runtime=args.runtime,
        policy=policy, rate_policy=load_json(args.rate_policy),
    )
    preliminary = deduplicate_candidates([
        row for result in results if result.get("bridge_status") == "PASS"
        for row in result.get("data") or []
    ])
    ranked = sorted(preliminary, key=lambda item: (-len(item.get("discovery_sources") or []),
                                                    int(item.get("rank") or 999999),
                                                    item["canonical_ticker"]))
    identity_requests = [{"operation": "security_info", "ticker": item["canonical_ticker"],
                          "exchange": item.get("stex_tp")}
                         for item in ranked[:int(policy["maximum_identity_lookups"])]
                         if item.get("stex_tp")]
    identity_results = invoke_discovery_bridge_batch(identity_requests, runtime=args.runtime,
                                                      policy=policy,
                                                      rate_policy=load_json(args.rate_policy)) if identity_requests else []
    value = build_artifact(results, identity_results=identity_results)
    if before != file_hash(args.portfolio_state):
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("CANDIDATE_DISCOVERY_SCHEMA_FAILED:" + ";".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, value)
    print(value["status"])
    return 0 if value["status"] != "CANDIDATE_DISCOVERY_FAILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
