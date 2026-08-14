#!/usr/bin/env python3
"""Apply audited official-source corrections and deterministic coverage semantics."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from current_event_risk import record_hash, validate_bundle_semantics
from validation_common import load_json, validate_instance, write_json


LEDGER_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "event-risk-source-ledger.schema.json"

EVENT_TYPE_TO_CATEGORY = {
    "EARNINGS_RELEASE": "RECENT_EARNINGS",
    "EARNINGS_SCHEDULE": "NEXT_EARNINGS",
    "GUIDANCE": "GUIDANCE",
    "FINANCING": "FINANCING_DILUTION",
    "DILUTION": "FINANCING_DILUTION",
    "MAJOR_CUSTOMER_OR_CONTRACT": "MAJOR_CUSTOMER_OR_CONTRACT",
    "CORPORATE_ACTION": "CORPORATE_ACTION",
    "ETF_SPLIT_OR_REVERSE_SPLIT": "CORPORATE_ACTION",
    "ETF_PRODUCT_STRUCTURE": "ETF_PRODUCT_STRUCTURE",
    "EX_DIVIDEND": "EX_DIVIDEND",
    "DELISTING_OR_TRADING_HALT": "DELISTING_OR_TRADING_HALT",
    "REGULATORY": "REGULATORY",
    "INVESTOR_DAY": "INVESTOR_DAY",
}

MISSING_FIELD_TO_CATEGORY = {
    "next_official_earnings_date": "NEXT_EARNINGS",
    "official_q2_2026_results_release_or_sec_8k": "RECENT_EARNINGS",
    "post_earnings_sec_financing_and_dilution_sweep": "FINANCING_DILUTION",
    "current_financing_dilution_and_regulatory_sweep": "FINANCING_DILUTION",
    "current_exchange_halt_or_delisting_notice_sweep": "DELISTING_OR_TRADING_HALT",
    "current_sponsor_corporate_action_notice_feed": "CORPORATE_ACTION",
    "authoritative_complete_negative_corporate_action_assertion": "CORPORATE_ACTION",
}

SEVERITY_RANK = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
EFFECT_RANK = {"CONTEXT_ONLY": 0, "EVENT_REVIEW_REQUIRED": 1, "WAIT_REQUIRED": 2}


def _maximum(values: list[str], ranking: dict[str, int], default: str) -> str:
    return max(values or [default], key=lambda value: ranking[value])


def _replace_event_reference(bundle: dict[str, Any], old_id: str, new_id: str) -> None:
    for coverage in bundle["ticker_coverage"]:
        coverage["event_ids"] = [new_id if value == old_id else value for value in coverage["event_ids"]]


def apply_source_corrections(bundle: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    errors = validate_instance(ledger, LEDGER_SCHEMA)
    if errors:
        raise ValueError("SOURCE_LEDGER_INVALID:" + ";".join(errors))
    evidence_routes = {route["evidence_id"]: route for route in ledger["evidence_routes"]}
    if len(evidence_routes) != len(ledger["evidence_routes"]):
        raise ValueError("SOURCE_LEDGER_DUPLICATE_EVIDENCE_ID")
    for route in evidence_routes.values():
        if route["checked_at"] > ledger["analysis_cutoff"]:
            raise ValueError(f"SOURCE_ROUTE_AFTER_CUTOFF:{route['evidence_id']}")
    for correction in ledger["corrections"]:
        patch_ticker = correction["event_patch"].get("ticker")
        for evidence_id in correction["evidence_ids"]:
            route = evidence_routes.get(evidence_id)
            if route is None:
                raise ValueError(f"CORRECTION_EVIDENCE_NOT_REGISTERED:{evidence_id}")
            if patch_ticker and route["ticker"] != patch_ticker:
                raise ValueError(f"CORRECTION_EVIDENCE_TICKER_MISMATCH:{evidence_id}")
    corrected = deepcopy(bundle)
    corrected["analysis_cutoff"] = ledger["analysis_cutoff"]
    corrected["generated_at"] = ledger["checked_at"]
    by_id = {event["event_id"]: event for event in corrected["events"]}

    for correction in ledger["corrections"]:
        target_id = correction["target_event_id"]
        prior_id = correction.get("replaces_event_id") or target_id
        event = by_id.pop(prior_id, None)
        if event is None:
            if not correction["create_if_missing"]:
                raise ValueError(f"CORRECTION_TARGET_MISSING:{prior_id}")
            event = {}
            corrected["events"].append(event)
        event.update(correction["event_patch"])
        event["event_id"] = target_id
        event["analysis_cutoff"] = ledger["analysis_cutoff"]
        event["retrieved_at"] = ledger["checked_at"]
        event["first_seen_at"] = min(event.get("first_seen_at") or ledger["checked_at"], ledger["checked_at"])
        event["claim_ids"] = correction["claim_ids"]
        event["evidence_ids"] = correction["evidence_ids"]
        event["record_hash"] = None
        event["record_hash"] = record_hash(event)
        by_id[target_id] = event
        if prior_id != target_id:
            _replace_event_reference(corrected, prior_id, target_id)

    for event in corrected["events"]:
        event["analysis_cutoff"] = ledger["analysis_cutoff"]
        event.setdefault("claim_ids", [f"CLAIM:{event['event_id']}"])
        event.setdefault("evidence_ids", [f"EVIDENCE:{event['event_id']}"])
        event["record_hash"] = None
        event["record_hash"] = record_hash(event)

    coverage_by_ticker = {item["ticker"]: item for item in corrected["ticker_coverage"]}
    tost = coverage_by_ticker["TOST"]
    tost["missing_fields"] = [
        value for value in tost["missing_fields"]
        if value != "official_q2_2026_results_release_or_sec_8k"
    ]
    tost["notes"] = [
        "The August 4, 2026 Form 8-K and Exhibit 99.1 verify the Q2 2026 results; next-event and financing/regulatory sweeps remain incomplete."
    ]
    mvll = coverage_by_ticker["MVLL"]
    if "MVLL-20260626-3FOR1-FORWARD-SPLIT" not in mvll["event_ids"]:
        mvll["event_ids"].append("MVLL-20260626-3FOR1-FORWARD-SPLIT")
    mvll["notes"] = [
        "GraniteShares verified MVLL's 3-for-1 forward split with June 24 record date, June 25 payable date, and June 26 effective date.",
        "MRVL issuer events remain supplemental thesis context and are not MVLL product-structure events."
    ]
    coverage_by_ticker["FSLY"]["notes"] = [
        "The exact Q2 2026 release and Investor Supplement are verified separately from the September 22 Investor Day."
    ]

    for item in corrected["ticker_coverage"]:
        prior_status = item.pop("status")
        prior_effect = item.pop("strategy_effect")
        item["coverage_status"] = (
            "PARTIAL_NONBLOCKING" if prior_effect == "CONTEXT_ONLY"
            else "PARTIAL_BLOCKING"
        ) if item["missing_fields"] else "COMPLETE_FOR_REQUIRED_CATEGORIES"
        item["event_effect"] = (
            "CONTEXT_ONLY" if prior_effect == "CONTEXT_ONLY"
            else "EVENT_REVIEW_REQUIRED"
        )
        item["event_data_incomplete"] = bool(item["missing_fields"])
        if prior_status in {"UNAVAILABLE", "INVALID"}:
            item["coverage_status"] = "SOURCE_UNAVAILABLE" if prior_status == "UNAVAILABLE" else "INVALID"

    category_coverage = build_category_coverage(corrected)
    corrected["category_coverage"] = category_coverage
    category_by_ticker: dict[str, list[str]] = defaultdict(list)
    for category in category_coverage:
        category_by_ticker[category["ticker"]].append(category["category_id"])
    for item in corrected["ticker_coverage"]:
        item["category_ids"] = sorted(category_by_ticker[item["ticker"]])

    statuses = {item["coverage_status"] for item in corrected["ticker_coverage"]}
    if "INVALID" in statuses:
        corrected["coverage_status"] = "INVALID"
    elif "SOURCE_UNAVAILABLE" in statuses or "PARTIAL_BLOCKING" in statuses:
        corrected["coverage_status"] = "PARTIAL_BLOCKING"
    elif "STALE" in statuses:
        corrected["coverage_status"] = "STALE"
    elif "PARTIAL_NONBLOCKING" in statuses:
        corrected["coverage_status"] = "PARTIAL_NONBLOCKING"
    else:
        corrected["coverage_status"] = "COMPLETE_FOR_REQUIRED_CATEGORIES"
    corrected["event_data_status"] = (
        "EVENT_DATA_INCOMPLETE" if any(item["event_data_incomplete"] for item in corrected["ticker_coverage"])
        else "COMPLETE"
    )
    corrected["bundle_status"] = (
        "EVENT_REVIEW_REQUIRED" if corrected["coverage_status"] == "PARTIAL_BLOCKING"
        else "PARTIAL" if corrected["coverage_status"] != "COMPLETE_FOR_REQUIRED_CATEGORIES"
        else "COMPLETE"
    )
    return corrected


def build_category_coverage(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    events_by_ticker_category: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    missing_by_ticker_category: dict[tuple[str, str], list[str]] = defaultdict(list)
    coverage_by_ticker = {item["ticker"]: item for item in bundle["ticker_coverage"]}
    for event in bundle["events"]:
        if event["ticker"] == "GLOBAL":
            continue
        category = EVENT_TYPE_TO_CATEGORY.get(event["event_type"])
        if category:
            events_by_ticker_category[(event["ticker"], category)].append(event)
    for item in bundle["ticker_coverage"]:
        for missing in item["missing_fields"]:
            category = MISSING_FIELD_TO_CATEGORY.get(missing, "REGULATORY")
            missing_by_ticker_category[(item["ticker"], category)].append(missing)

    categories: list[dict[str, Any]] = []
    for ticker, category in sorted(set(events_by_ticker_category) | set(missing_by_ticker_category)):
        events = events_by_ticker_category[(ticker, category)]
        missing = missing_by_ticker_category[(ticker, category)]
        ticker_coverage = coverage_by_ticker[ticker]
        dates = [
            value for event in events for value in (event.get("published_at"), event.get("effective_at")) if value
        ]
        published = [event["published_at"] for event in events if event.get("published_at")]
        effective = [event["effective_at"] for event in events if event.get("effective_at")]
        checked_routes = sorted({event["source_url"] for event in events})
        required_routes = sorted(set(checked_routes) | {f"REQUIRED:{field}" for field in missing})
        blocking = bool(missing) and ticker_coverage["event_effect"] != "CONTEXT_ONLY"
        coverage_status = (
            "PARTIAL_BLOCKING" if blocking else "PARTIAL_NONBLOCKING"
        ) if missing else "COMPLETE_FOR_REQUIRED_CATEGORIES"
        effects = [event["policy_effect"] for event in events]
        if blocking:
            effects.append("EVENT_REVIEW_REQUIRED")
        event_effect = _maximum(effects, EFFECT_RANK, "CONTEXT_ONLY")
        if coverage_status == "PARTIAL_NONBLOCKING":
            event_effect = "CONTEXT_ONLY"
        record = {
            "category_id": f"{ticker}:{category}",
            "ticker": ticker,
            "event_category": category,
            "required_source_routes": required_routes,
            "checked_source_routes": checked_routes,
            "coverage_start": min(dates) if dates else None,
            "coverage_end": max(dates) if dates else None,
            "last_checked_at": bundle["analysis_cutoff"],
            "published_at": max(published) if published else None,
            "effective_at": max(effective) if effective else None,
            "retrieved_at": max([event["retrieved_at"] for event in events] or [bundle["analysis_cutoff"]]),
            "analysis_cutoff": bundle["analysis_cutoff"],
            "materiality": _maximum([event["severity"] for event in events], SEVERITY_RANK, "UNKNOWN"),
            "coverage_status": coverage_status,
            "event_effect": event_effect,
            "announcement_status": "ANNOUNCED" if events else "SEARCH_INCOMPLETE",
            "next_refresh_trigger": (
                "AT_EVENT_EFFECTIVE_OR_NEW_OFFICIAL_DISCLOSURE" if events and not missing
                else "WHEN_REQUIRED_OFFICIAL_ROUTE_IS_RECHECKED"
            ),
            "point_in_time_eligible": bool(events) and all(event["point_in_time_eligible"] for event in events),
            "claim_ids": sorted({value for event in events for value in event["claim_ids"]}),
            "evidence_ids": sorted({value for event in events for value in event["evidence_ids"]}),
            "record_hash": None,
            "order_authority": False,
        }
        record["record_hash"] = record_hash(record)
        categories.append(record)
    return categories


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corrected = apply_source_corrections(load_json(args.bundle), load_json(args.source_ledger))
    errors = validate_bundle_semantics(corrected)
    if errors:
        raise SystemExit(";".join(errors))
    write_json(args.output, corrected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
