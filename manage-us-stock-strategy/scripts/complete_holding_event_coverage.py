#!/usr/bin/env python3
"""Build a data-only successor event bundle and immutable v2 baseline links.

The operational same-session event archive is immutable.  This module therefore
derives a separately hashed research bundle, validates it, and links candidate
baselines without changing the active baseline index, portfolio, provider scope,
strategy state, quantity authority, or order authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from current_event_risk import PRIMARY_SOURCE_TYPES, record_hash, validate_bundle_semantics
from holding_baseline_operationalization import validate_event_link
from holding_research import baseline_payload, research_packet_payload
from validation_common import canonical_hash, file_hash, load_json, parse_datetime, validate_instance, write_json


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
LEDGER_SCHEMA = SCHEMAS / "event-risk-completion-ledger.schema.json"
EVENT_LINK_SCHEMA = SCHEMAS / "baseline-event-link.schema.json"
BASELINE_SCHEMA = SCHEMAS / "holding-research-baseline.schema.json"
MANIFEST_SCHEMA = SCHEMAS / "holding-event-completion-manifest.schema.json"
PORTFOLIO_PATH = ROOT / "stock-strategy-system" / "portfolio_state.json"
ACTIVE_INDEX_PATH = ROOT / "workspace/research/holding-baselines/active-index.json"

TARGET_TICKERS = {"SOXL", "MVLL", "NBIS", "MRVL"}
REQUIRED_CATEGORIES = {
    "NBIS": {
        "LATEST_EARNINGS", "NEXT_OFFICIALLY_ANNOUNCED_EARNINGS", "FINANCING",
        "DILUTION", "WARRANTS", "CONVERTIBLE_INSTRUMENTS", "MATERIAL_CONTRACTS",
        "TRADING_HALT_OR_LISTING_ISSUE", "REGULATORY_ISSUE",
    },
    "MVLL": {
        "SPONSOR_NOTICE", "SPLIT_OR_REVERSE_SPLIT", "PRODUCT_STRUCTURE_CHANGE",
        "LIQUIDATION_OR_TERMINATION", "MATERIAL_TRACKING_OR_DERIVATIVES_NOTICE",
    },
    "MRVL": {
        "LATEST_EARNINGS", "NEXT_OFFICIALLY_ANNOUNCED_EARNINGS", "GUIDANCE", "FINANCING",
        "PREFERRED_OR_SERIES_A_CONVERSION", "ACQUISITION_RELATED_EQUITY_OVERHANG",
        "MATERIAL_CUSTOMER_PROGRAM_EVENT",
    },
    "SOXL": {
        "SPONSOR_NOTICE", "SPLIT_OR_REVERSE_SPLIT", "INDEX_OR_METHODOLOGY_CHANGE",
        "PRODUCT_LIQUIDATION_OR_STRUCTURE_CHANGE",
    },
}
EFFECT_RANK = {"CONTEXT_ONLY": 0, "EVENT_REVIEW_REQUIRED": 1, "WAIT_REQUIRED": 2}
MATERIALITY_RANK = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def _maximum(values: list[str], ranking: dict[str, int], default: str) -> str:
    return max(values, key=lambda item: ranking.get(item, -1), default=default)


def _require_repo_path(path: Path, allowed_relative_root: str) -> Path:
    target = path.resolve()
    allowed = (ROOT / allowed_relative_root).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise ValueError(f"OUTPUT_OUTSIDE_ALLOWED_ROOT:{allowed_relative_root}") from exc
    protected = {
        PORTFOLIO_PATH.resolve(),
        (ROOT / "stock-strategy-system/alert_policy.json").resolve(),
        (ROOT / "workspace/policies/instrument_registry.json").resolve(),
        (ROOT / "workspace/policies/source_capabilities.json").resolve(),
        (ROOT / "workspace/state/event_risk_archive/2026-08-13/event_risk_bundle.json").resolve(),
        ACTIVE_INDEX_PATH.resolve(),
    }
    if target in protected:
        raise ValueError("OUTPUT_PATH_ALIASES_PROTECTED_INPUT")
    return target


def _contains_true_order_authority(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (key == "order_authority" and item is not False) or _contains_true_order_authority(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_true_order_authority(item) for item in value)
    return False


def validate_completion_ledger(ledger: dict[str, Any], base_bundle: dict[str, Any], base_path: Path) -> list[str]:
    errors = validate_instance(ledger, LEDGER_SCHEMA)
    if errors:
        return errors
    cutoff = parse_datetime(ledger["analysis_cutoff"])
    if ledger["base_bundle_id"] != base_bundle.get("bundle_id"):
        errors.append("BASE_BUNDLE_ID_MISMATCH")
    if ledger["base_bundle_file_hash"] != file_hash(base_path):
        errors.append("BASE_BUNDLE_FILE_HASH_MISMATCH")
    if ledger["market_session"] != base_bundle.get("market_session"):
        errors.append("BASE_BUNDLE_SESSION_MISMATCH")
    if cutoff < parse_datetime(base_bundle["analysis_cutoff"]):
        errors.append("COMPLETION_CUTOFF_PRECEDES_BASE_BUNDLE")
    if ledger["checked_at"] != ledger["analysis_cutoff"]:
        errors.append("CHECKED_AT_MUST_EQUAL_ANALYSIS_CUTOFF")

    routes = ledger["evidence_routes"]
    route_ids = [item["evidence_id"] for item in routes]
    if len(route_ids) != len(set(route_ids)):
        errors.append("DUPLICATE_EVIDENCE_ROUTE_ID")
    route_by_id = {item["evidence_id"]: item for item in routes}
    for route in routes:
        parsed = urlparse(route["source_url"])
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"NON_HTTPS_OFFICIAL_ROUTE:{route['evidence_id']}")
        if route["source_type"] not in PRIMARY_SOURCE_TYPES:
            errors.append(f"NON_PRIMARY_SOURCE_ROUTE:{route['evidence_id']}")
        if route["ticker"] not in TARGET_TICKERS:
            errors.append(f"OUT_OF_SCOPE_EVIDENCE_ROUTE:{route['evidence_id']}")
        if parse_datetime(route["checked_at"]) > cutoff:
            errors.append(f"ROUTE_CHECKED_AFTER_CUTOFF:{route['evidence_id']}")

    seen_categories: dict[str, set[str]] = defaultdict(set)
    category_ids: set[str] = set()
    for category in ledger["required_category_checks"]:
        category_id = category["category_id"]
        if category_id in category_ids:
            errors.append(f"DUPLICATE_REQUIRED_CATEGORY_ID:{category_id}")
        category_ids.add(category_id)
        ticker = category["ticker"]
        seen_categories[ticker].add(category["required_category"])
        required = set(category["required_source_route_ids"])
        checked = set(category["checked_source_route_ids"])
        if required != checked:
            errors.append(f"REQUIRED_ROUTE_CHECK_INCOMPLETE:{category_id}")
        if any(route_id not in route_by_id for route_id in required):
            errors.append(f"UNREGISTERED_REQUIRED_ROUTE:{category_id}")
        if any(route_by_id[route_id]["ticker"] != ticker for route_id in required if route_id in route_by_id):
            errors.append(f"CROSS_TICKER_ROUTE:{category_id}")
        evidence_ids = set(category["evidence_ids"])
        if not evidence_ids.issubset(required):
            errors.append(f"CATEGORY_EVIDENCE_NOT_REQUIRED_ROUTE:{category_id}")
        if category["announcement_status"] == "NOT_YET_ANNOUNCED_AS_OF_CUTOFF":
            if category["published_at"] is not None or category["effective_at"] is not None:
                errors.append(f"UNANNOUNCED_CATEGORY_HAS_EVENT_DATE:{category_id}")
            if any(route_by_id[route_id]["route_result"] != "ROUTE_CHECKED_NO_ANNOUNCEMENT" for route_id in required if route_id in route_by_id):
                errors.append(f"UNANNOUNCED_CATEGORY_ROUTE_RESULT_INVALID:{category_id}")
        published = category.get("published_at")
        if published is not None and parse_datetime(published) > cutoff:
            errors.append(f"FUTURE_CATEGORY_PUBLISHED_AT:{category_id}")
        if category.get("order_authority") is not False:
            errors.append(f"CATEGORY_ORDER_AUTHORITY_PROHIBITED:{category_id}")
    for ticker, expected in REQUIRED_CATEGORIES.items():
        actual = seen_categories.get(ticker, set())
        if actual != expected:
            errors.append(f"REQUIRED_CATEGORY_SET_MISMATCH:{ticker}:{sorted(expected - actual)}:{sorted(actual - expected)}")

    event_ids: set[str] = set()
    for event in ledger["event_additions"]:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            errors.append("EVENT_ADDITION_ID_MISSING")
            continue
        if event_id in event_ids:
            errors.append(f"DUPLICATE_EVENT_ADDITION_ID:{event_id}")
        event_ids.add(event_id)
        ticker = event.get("ticker")
        if ticker not in TARGET_TICKERS or event.get("applies_to") != [ticker]:
            errors.append(f"EVENT_ADDITION_TICKER_SCOPE_INVALID:{event_id}")
        evidence_ids = event.get("evidence_ids") or []
        if any(item not in route_by_id for item in evidence_ids):
            errors.append(f"EVENT_ADDITION_EVIDENCE_UNREGISTERED:{event_id}")
        if any(route_by_id[item]["ticker"] != ticker for item in evidence_ids if item in route_by_id):
            errors.append(f"EVENT_ADDITION_EVIDENCE_TICKER_MISMATCH:{event_id}")
        published = event.get("published_at")
        if published is not None and parse_datetime(published) > cutoff:
            errors.append(f"FUTURE_EVENT_ADDITION:{event_id}")

    targets = ledger["link_targets"]
    expected_targets = {("SOXL", "soxl-20260814-v2"), ("MVLL", "mvll-20260814-v2"),
                        ("NBIS", "nbis-20260814-v2"), ("MRVL", "mvll-20260814-v2")}
    actual_targets = {(item["ticker"], item["baseline_id"]) for item in targets}
    if actual_targets != expected_targets or len(targets) != 4:
        errors.append("BASELINE_EVENT_LINK_TARGET_SET_MISMATCH")
    if _contains_true_order_authority(ledger):
        errors.append("ORDER_AUTHORITY_PROHIBITED")
    return list(dict.fromkeys(errors))


def _prepare_event(event: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(event)
    value["retrieved_at"] = ledger["checked_at"]
    value["first_seen_at"] = ledger["checked_at"]
    value["analysis_cutoff"] = ledger["analysis_cutoff"]
    value["record_hash"] = "0" * 64
    value["record_hash"] = record_hash(value)
    return value


def _build_category_records(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    route_by_id = {item["evidence_id"]: item for item in ledger["evidence_routes"]}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in ledger["required_category_checks"]:
        grouped[(item["ticker"], item["bundle_event_category"])].append(item)
    records: list[dict[str, Any]] = []
    for (ticker, event_category), items in sorted(grouped.items()):
        required_ids = sorted({value for item in items for value in item["required_source_route_ids"]})
        checked_ids = sorted({value for item in items for value in item["checked_source_route_ids"]})
        required_urls = sorted({route_by_id[value]["source_url"] for value in required_ids})
        checked_urls = sorted({route_by_id[value]["source_url"] for value in checked_ids})
        published = [item["published_at"] for item in items if item["published_at"]]
        effective = [item["effective_at"] for item in items if item["effective_at"]]
        dates = published + effective
        announced = any(item["announcement_status"] == "ANNOUNCED" for item in items)
        record = {
            "category_id": f"{ticker}:{event_category}",
            "ticker": ticker,
            "event_category": event_category,
            "required_source_routes": required_urls,
            "checked_source_routes": checked_urls,
            "coverage_start": min(dates) if dates else None,
            "coverage_end": max(dates) if dates else None,
            "last_checked_at": ledger["checked_at"],
            "published_at": max(published) if published else None,
            "effective_at": max(effective) if effective else None,
            "retrieved_at": ledger["checked_at"],
            "analysis_cutoff": ledger["analysis_cutoff"],
            "materiality": _maximum([item["materiality"] for item in items], MATERIALITY_RANK, "UNKNOWN"),
            "coverage_status": "COMPLETE_FOR_REQUIRED_CATEGORIES",
            "event_effect": _maximum([item["event_effect"] for item in items], EFFECT_RANK, "CONTEXT_ONLY"),
            "announcement_status": "ANNOUNCED" if announced else "NOT_YET_ANNOUNCED_AS_OF_CUTOFF",
            "next_refresh_trigger": "AT_NEW_OFFICIAL_DISCLOSURE_OR_EVENT_EFFECTIVE",
            "point_in_time_eligible": all(item["point_in_time_eligible"] for item in items),
            "claim_ids": sorted({value for item in items for value in item["claim_ids"]}),
            "evidence_ids": sorted({value for item in items for value in item["evidence_ids"]}),
            "record_hash": "0" * 64,
            "order_authority": False,
        }
        record["record_hash"] = record_hash(record)
        records.append(record)
    return records


def build_successor_bundle(base_bundle: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    successor = deepcopy(base_bundle)
    successor["bundle_id"] = ledger["successor_bundle_id"]
    successor["analysis_cutoff"] = ledger["analysis_cutoff"]
    successor["generated_at"] = ledger["checked_at"]

    existing_ids = {item["event_id"] for item in successor["events"]}
    for event in successor["events"]:
        event["analysis_cutoff"] = ledger["analysis_cutoff"]
        event["record_hash"] = record_hash(event)
    for event in ledger["event_additions"]:
        if event["event_id"] in existing_ids:
            raise ValueError(f"EVENT_ADDITION_ALREADY_EXISTS:{event['event_id']}")
        successor["events"].append(_prepare_event(event, ledger))
        existing_ids.add(event["event_id"])
    successor["events"] = sorted(successor["events"], key=lambda item: (item["ticker"], item["event_id"]))

    preserved_categories = []
    for category in successor["category_coverage"]:
        if category["ticker"] in TARGET_TICKERS:
            continue
        category["analysis_cutoff"] = ledger["analysis_cutoff"]
        category["record_hash"] = record_hash(category)
        preserved_categories.append(category)
    completed_categories = _build_category_records(ledger)
    successor["category_coverage"] = sorted(
        preserved_categories + completed_categories,
        key=lambda item: (item["ticker"], item["event_category"]),
    )

    categories_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for category in completed_categories:
        categories_by_ticker[category["ticker"]].append(category)
    routes_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for route in ledger["evidence_routes"]:
        routes_by_ticker[route["ticker"]].append(route)
    events_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in successor["events"]:
        events_by_ticker[event["ticker"]].append(event)
    for coverage in successor["ticker_coverage"]:
        ticker = coverage["ticker"]
        if ticker not in TARGET_TICKERS:
            continue
        categories = categories_by_ticker[ticker]
        coverage["event_ids"] = sorted(item["event_id"] for item in events_by_ticker[ticker])
        coverage["category_ids"] = sorted(item["category_id"] for item in categories)
        coverage["checked_source_types"] = sorted({item["source_type"] for item in routes_by_ticker[ticker]})
        coverage["missing_fields"] = []
        coverage["event_data_incomplete"] = False
        coverage["coverage_status"] = "COMPLETE_FOR_REQUIRED_CATEGORIES"
        coverage["event_effect"] = _maximum(
            [item["event_effect"] for item in categories], EFFECT_RANK, "CONTEXT_ONLY"
        )
        completion_note = "Required holding-baseline event categories were checked on official routes as of the successor cutoff; unannounced status is not proof that no event exists."
        coverage["notes"] = list(dict.fromkeys(list(coverage.get("notes") or []) + [completion_note]))

    statuses = {item["coverage_status"] for item in successor["ticker_coverage"]}
    if "INVALID" in statuses:
        successor["coverage_status"] = "INVALID"
    elif "SOURCE_UNAVAILABLE" in statuses or "PARTIAL_BLOCKING" in statuses:
        successor["coverage_status"] = "PARTIAL_BLOCKING"
    elif "STALE" in statuses:
        successor["coverage_status"] = "STALE"
    elif "PARTIAL_NONBLOCKING" in statuses:
        successor["coverage_status"] = "PARTIAL_NONBLOCKING"
    else:
        successor["coverage_status"] = "COMPLETE_FOR_REQUIRED_CATEGORIES"
    successor["event_data_status"] = (
        "EVENT_DATA_INCOMPLETE"
        if any(item["event_data_incomplete"] for item in successor["ticker_coverage"])
        else "COMPLETE"
    )
    successor["bundle_status"] = (
        "EVENT_REVIEW_REQUIRED"
        if successor["coverage_status"] in {"PARTIAL_BLOCKING", "SOURCE_UNAVAILABLE", "STALE", "INVALID"}
        else "PARTIAL"
        if successor["coverage_status"] == "PARTIAL_NONBLOCKING"
        else "COMPLETE"
    )
    successor["provider_readiness_mutated"] = False
    successor["strategy_state_mutated"] = False
    successor["quantity_authority"] = False
    successor["order_authority"] = False
    errors = validate_bundle_semantics(successor)
    if errors:
        raise ValueError(";".join(errors))
    return successor


def build_completion_event_link(baseline: dict[str, Any], event_bundle: dict[str, Any], *,
                                event_bundle_path: Path, ticker: str, entity_role: str,
                                link_created_at: str) -> dict[str, Any]:
    """Map the canonical complete status into the legacy candidate-link contract.

    This helper is intentionally confined to the non-operational completion
    artifact.  The semantic-fingerprint-governed live compiler is unchanged.
    """
    coverage = next((row for row in event_bundle["ticker_coverage"] if row["ticker"] == ticker), None)
    if coverage is None:
        coverage_status, event_effect, link_status = "UNAVAILABLE", "INVALID", "MISSING"
    else:
        raw_coverage = coverage.get("coverage_status", "INVALID")
        coverage_status = "COMPLETE" if raw_coverage == "COMPLETE_FOR_REQUIRED_CATEGORIES" else raw_coverage
        raw_effect = coverage.get("event_effect", "INVALID")
        event_effect = "EVENT_REVIEW_PENDING" if raw_effect == "EVENT_REVIEW_REQUIRED" else raw_effect
        if event_effect in {"EVENT_REVIEW_PENDING", "WAIT_REQUIRED"}:
            link_status = "EVENT_REVIEW_PENDING"
        elif coverage_status == "COMPLETE" and event_effect == "CONTEXT_ONLY":
            link_status = "VALID"
        elif coverage_status == "PARTIAL_NONBLOCKING" and event_effect == "CONTEXT_ONLY":
            link_status = "PARTIAL_NONBLOCKING"
        else:
            link_status = "INVALID"
    link = {
        "schema_version": "2.6.12",
        "baseline_event_link_id": f"{baseline['baseline_id']}--{ticker}--{event_bundle['bundle_id']}",
        "ticker": ticker,
        "entity_role": entity_role,
        "baseline_id": baseline["baseline_id"],
        "baseline_hash": baseline["baseline_hash"],
        "event_bundle_id": event_bundle["bundle_id"],
        "event_bundle_hash": file_hash(event_bundle_path),
        "event_coverage_status": coverage_status,
        "event_effect": event_effect,
        "analysis_cutoff": event_bundle["analysis_cutoff"],
        "link_created_at": link_created_at,
        "link_validation_status": link_status,
        "link_hash": "0" * 64,
        "order_authority": False,
    }
    link["link_hash"] = canonical_hash(_without_hash(link, "link_hash"))
    return link


def build_links(ledger: dict[str, Any], successor: dict[str, Any], successor_path: Path,
                links_output_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for target in ledger["link_targets"]:
        baseline_path = (ROOT / target["baseline_path"]).resolve()
        try:
            baseline_path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError("BASELINE_PATH_OUTSIDE_REPOSITORY") from exc
        baseline = load_json(baseline_path)
        if baseline.get("baseline_id") != target["baseline_id"]:
            raise ValueError(f"BASELINE_ID_MISMATCH:{target['ticker']}")
        baseline_errors = validate_instance(baseline, BASELINE_SCHEMA)
        if baseline.get("baseline_hash") != canonical_hash(baseline_payload(baseline)):
            baseline_errors.append("BASELINE_HASH_MISMATCH")
        if baseline.get("research_packet_hash") != canonical_hash(research_packet_payload(baseline)):
            baseline_errors.append("RESEARCH_PACKET_HASH_MISMATCH")
        if baseline_errors:
            raise ValueError(f"BASELINE_INTEGRITY_FAILED:{target['ticker']}:{baseline_errors}")
        link = build_completion_event_link(
            baseline,
            successor,
            event_bundle_path=successor_path,
            ticker=target["ticker"],
            entity_role=target["entity_role"],
            link_created_at=ledger["checked_at"],
        )
        validation = validate_event_link(
            link, schema_path=EVENT_LINK_SCHEMA, baseline=baseline, event_bundle_path=successor_path
        )
        if validation["validation_status"] != "PASSED":
            raise ValueError(f"EVENT_LINK_VALIDATION_FAILED:{target['ticker']}:{validation['errors']}")
        output = _require_repo_path(links_output_dir / target["output_name"], "workspace/research/baseline-event-links")
        write_json(output, link)
        results.append({
            "ticker": target["ticker"],
            "baseline_id": baseline["baseline_id"],
            "path": output.relative_to(ROOT).as_posix(),
            "file_hash": file_hash(output),
            "link_hash": link["link_hash"],
            "validation_status": "PASSED",
        })
    return sorted(results, key=lambda item: item["ticker"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-bundle", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--successor-output", type=Path, required=True)
    parser.add_argument("--links-output-dir", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    args = parser.parse_args()

    base_path = args.base_bundle.resolve()
    ledger_path = args.source_ledger.resolve()
    successor_path = _require_repo_path(args.successor_output, "workspace/research/event-evidence")
    links_output_dir = args.links_output_dir.resolve()
    _require_repo_path(links_output_dir / "path-probe.json", "workspace/research/baseline-event-links")
    manifest_path = _require_repo_path(args.manifest_output, "workspace/research/event-evidence")
    base_bundle = load_json(base_path)
    ledger = load_json(ledger_path)
    errors = validate_completion_ledger(ledger, base_bundle, base_path)
    if errors:
        raise SystemExit(";".join(errors))

    portfolio_before = file_hash(PORTFOLIO_PATH)
    active_bundle_before = file_hash(base_path)
    active_index_before = file_hash(ACTIVE_INDEX_PATH)
    successor = build_successor_bundle(base_bundle, ledger)
    write_json(successor_path, successor)
    links = build_links(ledger, successor, successor_path, links_output_dir)
    portfolio_after = file_hash(PORTFOLIO_PATH)
    if portfolio_before != portfolio_after:
        raise SystemExit("PORTFOLIO_STATE_MUTATED")
    if active_bundle_before != file_hash(base_path):
        raise SystemExit("ACTIVE_EVENT_BUNDLE_MUTATED")
    if active_index_before != file_hash(ACTIVE_INDEX_PATH):
        raise SystemExit("ACTIVE_BASELINE_INDEX_MUTATED")

    manifest = {
        "schema_version": "2.6.13",
        "manifest_id": f"{ledger['successor_bundle_id']}--manifest",
        "market_session": ledger["market_session"],
        "analysis_cutoff": ledger["analysis_cutoff"],
        "change_classification": "DATA_ONLY",
        "active_bundle_id": base_bundle["bundle_id"],
        "active_bundle_file_hash": active_bundle_before,
        "successor_bundle_id": successor["bundle_id"],
        "successor_bundle_path": successor_path.relative_to(ROOT).as_posix(),
        "successor_bundle_file_hash": file_hash(successor_path),
        "successor_bundle_canonical_hash": canonical_hash(successor),
        "source_ledger_path": ledger_path.relative_to(ROOT).as_posix(),
        "source_ledger_canonical_hash": canonical_hash(ledger),
        "baseline_event_links": links,
        "active_baseline_index_hash": active_index_before,
        "active_bundle_mutated": False,
        "active_baseline_index_mutated": False,
        "portfolio_state_hash_before": portfolio_before,
        "portfolio_state_hash_after": portfolio_after,
        "portfolio_mutated": False,
        "provider_readiness_mutated": False,
        "strategy_state_mutated": False,
        "baseline_activation_mutated": False,
        "quantity_authority": False,
        "order_authority": False,
    }
    manifest_errors = validate_instance(manifest, MANIFEST_SCHEMA)
    if manifest_errors:
        raise SystemExit(";".join(manifest_errors))
    write_json(manifest_path, manifest)
    print(json.dumps({
        "status": "HOLDING_EVENT_COVERAGE_COMPLETED",
        "successor_bundle_id": successor["bundle_id"],
        "target_coverage": {
            item["ticker"]: {"coverage_status": item["coverage_status"], "event_effect": item["event_effect"]}
            for item in successor["ticker_coverage"] if item["ticker"] in TARGET_TICKERS
        },
        "baseline_event_links": links,
        "portfolio_mutated": False,
        "order_authority": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
