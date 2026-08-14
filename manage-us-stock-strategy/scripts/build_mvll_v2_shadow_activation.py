#!/usr/bin/env python3
"""Build the non-authoritative MVLL v2 Shadow activation packet.

Kiwoom remains the direct-price authority for both MVLL and its MRVL
underlying.  yfinance is retained only as a diagnostic reference.  This
builder does not activate a baseline, change a live strategy, or create an
order/quantity.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from holding_baseline_operationalization import (
    build_baseline_event_link,
    compile_shadow,
    validate_event_link,
    validate_valuation_snapshot,
)
from holding_research import recompute_hashes, validate_baseline
from us_stock_price_authority import (
    build_us_stock_price_authority,
    validate_price_authority_artifact,
)
from validation_common import canonical_hash, file_hash, load_json, validate_instance


MARKET_SESSION = "2026-08-13"
AUTHORITY_POLICY_VERSION = "2026-08-14-kiwoom-execution-primary-v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def _kiwoom_record(root: Path, ticker: str) -> tuple[dict[str, Any], dict[str, Any], Path]:
    snapshot_path = root / "workspace/outputs/activation/holding-valuation-shadow/2026-08-13/kiwoom-finalized-snapshot.json"
    validation_path = root / "workspace/outputs/activation/holding-valuation-shadow/2026-08-13/session-aware-validation.json"
    snapshot = load_json(snapshot_path)
    item = next(row for row in snapshot["ticker_results"] if row.get("ticker") == ticker)
    raw = item["raw"]
    bar = next(row for row in raw["bars"] if row.get("session") == MARKET_SESSION)
    validation = load_json(validation_path)
    normalized = next(
        row["kiwoom_record"] for row in validation["latest_validation"]
        if row.get("ticker") == ticker
    )
    if Decimal(str(normalized["price"])) != Decimal(str(bar["close"])):
        raise ValueError(f"{ticker}_KIWOOM_NORMALIZED_AND_RAW_CLOSE_MISMATCH")
    if item.get("status") != "PASS" or raw.get("status") != "PASS" or raw.get("validation_errors"):
        raise ValueError(f"{ticker}_KIWOOM_RAW_SELF_INTEGRITY_FAILED")
    if raw.get("completed_session") != MARKET_SESSION:
        raise ValueError(f"{ticker}_KIWOOM_SESSION_MISMATCH")
    return item, normalized, snapshot_path


def _yfinance_close(root: Path, ticker: str) -> tuple[float, Path]:
    path = root / "workspace/outputs/portfolio-strategy/2026-08-13/yfinance_replay_evidence.json"
    record = load_json(path)["records"][ticker]
    if record.get("status") != "PRIMARY_VALIDATED" or record.get("completed_session") != MARKET_SESSION:
        raise ValueError(f"{ticker}_YFINANCE_DIAGNOSTIC_REFERENCE_INVALID")
    bar = next(item for item in record["bars"] if item.get("session") == MARKET_SESSION)
    return float(bar["close"]), path


def build_price_authority(root: Path, ticker: str, generated_at: str) -> dict[str, Any]:
    item, normalized, snapshot_path = _kiwoom_record(root, ticker)
    yfinance, yfinance_path = _yfinance_close(root, ticker)
    raw_page = item["raw"]["pagination"]["pages"][0]
    record = {
        "ticker": ticker,
        "requested_ticker": ticker,
        "security_identity": item["identity"]["security_name"],
        "security_identity_status": "VERIFIED",
        "currency": "USD",
        "fx_applied": False,
        "canonical_price": float(item["raw"]["completed_close"]),
        "api_status": "SUCCESS",
        "source_api_id": "usa06012",
        "source_endpoint": "/api/us/chart",
        "source_field": "result_list.cur_prc",
        "official_field_meaning": "CURRENT_PRICE_CLOSE_IN_DAILY_CHART",
        "target_session": MARKET_SESSION,
        "returned_row_date": MARKET_SESSION,
        "market_phase": "COMPLETED_DAILY",
        "price_semantics": "COMPLETED_DAILY_CLOSE",
        "price_basis": "RAW_REGULAR_SESSION_CLOSE",
        "retrieval_timestamp": load_json(snapshot_path)["generated_at"],
        "retrieval_market_phase": "MARKET_CLOSED_ARCHIVED_DAILY_QUERY",
        "request_parameters": {
            "stex_tp": item["identity"]["stex_tp"],
            "stk_cd": ticker,
            "strt_dt": MARKET_SESSION.replace("-", ""),
            "upd_stkpc_tp": "0",
            "exrt_appl_tp": "0",
        },
        "bar_finalized": bool(normalized["bar_finalized"]),
        "stale_record": False,
        "corporate_action_ambiguity": False,
        "scale_error": False,
    }
    result = build_us_stock_price_authority(
        record,
        yfinance_reference=yfinance,
        external_reference=None,
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        generated_at=generated_at,
    )
    result["source_provenance"] = {
        "kiwoom_snapshot_path": snapshot_path.relative_to(root).as_posix(),
        "kiwoom_snapshot_sha256": file_hash(snapshot_path),
        "kiwoom_identity_api_id": item["identity"]["source_api_id"],
        "kiwoom_runtime_commit": item["identity"]["official_runtime_commit"],
        "yfinance_path": yfinance_path.relative_to(root).as_posix(),
        "yfinance_sha256": file_hash(yfinance_path),
        "diagnostic_classification": "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE",
    }
    result["evidence_hash"] = canonical_hash(without_hash(result, "evidence_hash"))
    return result


def _method(method: str, value: float | None, denominator: float | None, status: str,
            evidence_id: str | None = None) -> dict[str, Any]:
    return {
        "method": method,
        "value": value,
        "denominator": denominator,
        "unit": "MULTIPLE" if method.startswith("EV_TO_") else "FRACTION",
        "status": status,
        "denominator_evidence_id": evidence_id,
        "judgement_authority": "NONE",
    }


def _scenario(scenario_id: str, scenario_type: str, shares: Decimal, price: Decimal,
              cash: Decimal, debt: Decimal, preferred: Decimal, other_claims: Decimal,
              assumptions: list[str]) -> dict[str, Any]:
    equity = shares * price
    enterprise = equity + debt + preferred + other_claims - cash
    revenue = {
        "BEAR": Decimal("10260"),
        "BASE": Decimal("10800"),
        "BULL": Decimal("11340"),
    }
    local_fcf_proxy = Decimal("1932.4")
    methods = [
        _method(f"EV_TO_REVENUE_{case}", float(enterprise / amount), float(amount), "EVALUATED", "mrvl-v2-q2-guidance")
        for case, amount in revenue.items()
    ]
    methods.extend([
        _method("LOCAL_OCF_MINUS_CAPEX_PROXY_YIELD", float(local_fcf_proxy / equity), float(equity), "EVALUATED", "mrvl-v2-q1-cash-flow"),
        _method("EV_TO_EBITDA", None, None, "NOT_EVALUATED"),
        _method("FORWARD_PE", None, None, "NOT_EVALUATED"),
        _method("DCF", None, None, "NOT_EVALUATED"),
    ])
    return {
        "scenario_id": scenario_id,
        "scenario_type": scenario_type,
        "share_basis": float(shares),
        "equity_value": float(equity),
        "enterprise_value": float(enterprise),
        "valuation_methods": methods,
        "assumption_ids": assumptions,
        "status": "EVALUATED",
        "formula_trace": {
            "equity_value": "shares_millions * kiwoom_raw_close_usd",
            "enterprise_value": "equity_value + debt + preferred_claims + other_claims - cash",
            "price_authority": "KIWOOM_REST",
            "local_fcf_proxy": "Q1_FY2027_OCF_MINUS_CAPEX_X4_NOT_COMPANY_REPORTED_FCF",
        },
        "convertible_share_equivalent_included": "SERIES_A_CONVERTED" in assumptions,
        "convertible_debt_included": False,
    }


def build_valuation(root: Path, price_authority: dict[str, Any], generated_at: str) -> dict[str, Any]:
    price = Decimal(str(price_authority["canonical_price"]))
    basic = Decimal("874.8")
    base = Decimal("886.1")
    series_a = Decimal("21.778")
    celestial = Decimal("24.4")
    customer_warrant = Decimal("4.2")
    stress = base + series_a + celestial + customer_warrant
    cash, debt, preferred, max_cash_earnout = map(Decimal, ("3843.6", "4961.3", "2000", "233"))
    scenarios = [
        _scenario("MRVL_LEGAL_BASIC", "BASIC", basic, price, cash, debt, preferred, Decimal("0"), ["LEGAL_COMMON_SHARES_AS_OF_2026-05-21"]),
        _scenario("MRVL_BASE_DILUTED", "BASE_DILUTED", base, price, cash, debt, preferred, Decimal("0"), ["Q1_FY2027_DILUTED_WEIGHTED_AVERAGE"]),
        _scenario("MRVL_KNOWN_GROSS_STRESS", "STRESS_DILUTED", stress, price, cash, debt, Decimal("0"), max_cash_earnout,
                  ["SERIES_A_CONVERTED", "CELESTIAL_MAX_24_4M_SHARES", "CUSTOMER_WARRANT_MAX_4_2M", "CELESTIAL_MAX_233M_CASH"]),
    ]
    value = {
        "schema_version": "2.6.12",
        "valuation_snapshot_id": "mrvl-valuation-20260813-v3",
        "ticker": "MRVL",
        "issuer_name": "Marvell Technology, Inc.",
        "entity_role": "UNDERLYING_ISSUER",
        "analysis_cutoff": generated_at,
        "market_session": MARKET_SESSION,
        "price": {
            "provider": "KIWOOM_REST", "canonical_provider": "KIWOOM_REST",
            "raw_regular_session_close": float(price), "currency": "USD",
            "price_basis": "RAW_REGULAR_SESSION_CLOSE", "market_session_type": "REGULAR_COMPLETED",
            "reported_session": MARKET_SESSION, "bar_finalized": True,
            "comparison_status": "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE",
            "yfinance_reference_price": price_authority["diagnostics"]["yfinance_reference_price"],
            "cross_provider_difference_pct": price_authority["diagnostics"]["cross_provider_difference_pct"],
            "price_authority_evidence_hash": price_authority["evidence_hash"],
            "self_integrity_status": "KIWOOM_PRICE_VALIDATED", "divergence_blocking": False,
            "blocking": False,
        },
        "capitalization": {
            "basic_shares": {"value": float(basic), "unit": "SHARES_MILLIONS", "as_of": "2026-05-21", "source_evidence_id": "mrvl-v2-10q-cover", "currency": None, "verification_status": "VERIFIED"},
            "diluted_shares_base": {"value": float(base), "unit": "SHARES_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-eps", "currency": None, "verification_status": "VERIFIED"},
            "diluted_shares_stress": {"value": float(stress), "unit": "SHARES_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-known-gross-stress", "currency": None, "verification_status": "VERIFIED"},
        },
        "balance_sheet": {
            "cash": {"value": float(cash), "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-balance", "currency": "USD", "verification_status": "VERIFIED"},
            "restricted_cash": {"value": None, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-balance", "currency": "USD", "verification_status": "NOT_EVALUATED"},
            "debt": {"value": float(debt), "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-debt", "currency": "USD", "verification_status": "VERIFIED"},
            "convertible_debt": {"value": 0.0, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-series-a-equity", "currency": "USD", "verification_status": "VERIFIED"},
            "preferred_claims": {"value": float(preferred), "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-series-a", "currency": "USD", "verification_status": "VERIFIED"},
            "other_claims": {"value": float(max_cash_earnout), "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-celestial-max-cash", "currency": "USD", "verification_status": "STRESS_ONLY"},
        },
        "operating_metrics": {
            "revenue_ltm": {"value": None, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-revenue", "currency": "USD", "verification_status": "NOT_EVALUATED"},
            "annualized_revenue_run_rate": {"value": 9672.0, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-revenue", "currency": "USD", "verification_status": "LOCAL_ANNUALIZATION"},
            "gross_profit": {"value": 1259.778, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-gaap-gross-margin", "currency": "USD", "verification_status": "DERIVED_FROM_REPORTED"},
            "operating_cash_flow": {"value": 638.8, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-cash-flow", "currency": "USD", "verification_status": "VERIFIED"},
            "capex": {"value": 155.7, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-cash-flow", "currency": "USD", "verification_status": "VERIFIED"},
            "free_cash_flow": {"value": None, "unit": "USD_MILLIONS", "as_of": "2026-05-02", "source_evidence_id": "mrvl-v2-q1-cash-flow", "currency": "USD", "verification_status": "NOT_COMPANY_REPORTED"},
        },
        "derived_values": {
            "q2_revenue_guidance_usd_millions": {"bear": 2565.0, "base": 2700.0, "bull": 2835.0},
            "annualized_guidance_scenarios_usd_millions": {"bear": 10260.0, "base": 10800.0, "bull": 11340.0},
            "local_ocf_minus_capex_proxy_q1_usd_millions": 483.1,
            "local_ocf_minus_capex_proxy_annualized_usd_millions": 1932.4,
            "known_stress_share_bridge_millions": {"base": 886.1, "series_a": 21.778, "celestial": 24.4, "customer_warrant": 4.2, "total": float(stress)},
        },
        "valuation_methods": [
            {"method": "EV_REVENUE_BEAR_BASE_BULL", "status": "EVALUATED", "judgement_authority": "NONE"},
            {"method": "LOCAL_OCF_MINUS_CAPEX_PROXY_YIELD", "status": "EVALUATED", "company_reported_fcf": False, "judgement_authority": "NONE"},
            {"method": "EV_TO_EBITDA", "status": "NOT_EVALUATED", "reason": "NO_APPROVED_POINT_IN_TIME_EBITDA_INPUT"},
            {"method": "FORWARD_PE", "status": "NOT_EVALUATED", "reason": "NO_APPROVED_POINT_IN_TIME_CONSENSUS_ESTIMATE"},
            {"method": "DCF", "status": "NOT_EVALUATED", "reason": "ASSUMPTION_PROVENANCE_INCOMPLETE"},
        ],
        "valuation_scenarios": scenarios,
        "claim_ids": ["mrvl-v2-capital-structure", "mrvl-v2-q2-guidance", "mrvl-v2-celestial-overhang", "mrvl-v2-series-a"],
        "evidence_ids": ["mrvl-v2-10q", "mrvl-v2-10k", "mrvl-v2-q1-ir", price_authority["evidence_hash"]],
        "required_missing_inputs": [],
        "calculation_formula_version": "mvll-mrvl-valuation-v2.6.14-1",
        "staleness_status": "FRESH",
        "staleness_triggers": ["NEW_MRVL_10Q", "NEW_MRVL_EARNINGS", "CAPITAL_STRUCTURE_CHANGE", "KIWOOM_PRICE_SESSION_CHANGE"],
        "valuation_evidence_status": "SCENARIO_VALIDATED",
        "valuation_judgement_status": "UNCLASSIFIED",
        "snapshot_hash": "0" * 64,
        "order_authority": False,
    }
    value["snapshot_hash"] = canonical_hash(without_hash(value, "snapshot_hash"))
    return value


def build_event_review(root: Path, generated_at: str) -> dict[str, Any]:
    source_bundle = root / "workspace/research/event-evidence/event-risk-2026-08-13-holding-completion-20260814T073717Z.json"
    return {
        "schema_version": "2.6.14",
        "bundle_id": "mvll-mrvl-event-review-20260814-v3",
        "analysis_cutoff": generated_at,
        "source_bundle_path": source_bundle.relative_to(root).as_posix(),
        "source_bundle_sha256": file_hash(source_bundle),
        "ticker_coverage": [
            {"ticker": "MVLL", "coverage_status": "COMPLETE", "event_effect": "CONTEXT_ONLY"},
            {"ticker": "MRVL", "coverage_status": "COMPLETE", "event_effect": "CONTEXT_ONLY"},
        ],
        "review_resolutions": [
            {"event": "MRVL_SERIES_A_CONVERSION", "resolution": "REPRESENTED_IN_KNOWN_GROSS_STRESS_SHARE_SCENARIO", "shares_millions": 21.778},
            {"event": "MRVL_CELESTIAL_EARNOUT", "resolution": "REPRESENTED_IN_KNOWN_GROSS_STRESS_SHARE_AND_CASH_SCENARIO", "shares_millions": 24.4, "cash_usd_millions": 233.0},
            {"event": "MRVL_CUSTOMER_WARRANT", "resolution": "REPRESENTED_IN_KNOWN_GROSS_STRESS_SHARE_SCENARIO", "shares_millions": 4.2},
            {"event": "MRVL_Q2_FY2027_GUIDANCE", "resolution": "REPRESENTED_AS_BEAR_BASE_BULL_REVENUE_SCENARIOS"},
            {"event": "MVLL_PRODUCT_SPLIT_AND_STRUCTURE", "resolution": "PRODUCT_CONTEXT_ONLY_NO_UNDERLYING_SUBSTITUTION"},
        ],
        "sources": [
            {"source_type": "SEC_FILING", "url": "https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/mrvl-20260502.htm", "published_at": "2026-05-28T00:00:00Z"},
            {"source_type": "ISSUER_IR", "url": "https://investor.marvell.com/news-events/press-releases/detail/1023/marvell-technology-inc-reports-first-quarter-of-fiscal-year-2027-financial-results", "published_at": "2026-05-27T20:05:00Z"},
            {"source_type": "ETF_SPONSOR", "url": "https://graniteshares.com/etfs/mvll/", "published_at": None},
        ],
        "validation_status": "PASSED",
        "quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
    }


def build_baseline(root: Path, price: dict[str, Any], valuation: dict[str, Any],
                   event_review_path: Path, generated_at: str) -> dict[str, Any]:
    candidate_path = root / "workspace/research/holding-baseline-candidates/2026-08-14/mvll-20260814-v2.json"
    value = deepcopy(load_json(candidate_path))
    # Older interrupted builder runs may have left a non-schema diagnostic
    # field in the mutable candidate path.  Artifact provenance belongs in the
    # build manifest, not in the immutable baseline contract.
    value.pop("component_artifacts", None)
    value.update({
        "baseline_id": "mvll-20260814-v3",
        "baseline_version": 3,
        "supersedes_baseline_id": value["baseline_id"],
        "supersedes_baseline_hash": value["baseline_hash"],
        "analysis_cutoff": generated_at,
        "evidence_cutoff": generated_at,
        "content_status": "COMPLETE",
        "valuation_status": "UNCLASSIFIED",
        "validation_status": "VALIDATED_SHADOW",
        "primary_reason": "MVLL is a daily-reset 2x MRVL product. Direct MVLL price authority is Kiwoom, while the MRVL issuer scenario packet now covers verified base and known gross-stress capitalization, official Q2 revenue guidance, liquidity, Series A conversion, customer warrant, and Celestial earnout. The valuation judgement remains UNCLASSIFIED and cannot authorize an add.",
        "risk_controller_result": "DOWNGRADE",
        "research_recommendation": "REASSESS",
    })
    value["linked_components"] = [
        {"ticker": "MRVL", "role": "UNDERLYING_THESIS", "confirmation_mode": "DAILY_MULTIPLE", "product_close_substitution": False, "valuation_applies_to": "MRVL_ISSUER_NOT_MVLL_TARGET_PRICE"},
        {"ticker": "MVLL", "role": "DIRECT_PRODUCT_PRICE", "confirmation_mode": "DIRECT", "product_close_substitution": False, "valuation_applies_to": "NOT_APPLICABLE_TO_PRODUCT"},
    ]
    value["next_research_triggers"] = list(dict.fromkeys(value["next_research_triggers"] + [
        "Rebuild MRVL scenario valuation after the next 10-Q or material capital-structure filing.",
        "Keep EMA10_RECLAIM_RVOL20 blocked until the deterministic RVOL boundary conflict is resolved.",
    ]))
    value["evidence"].extend([
        {"evidence_id": "mvll-v2-e5", "source_url": "https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/mrvl-20260502.htm", "source_type": "SEC_FILING", "published_at": "2026-05-28T00:00:00Z", "retrieved_at": generated_at, "effective_at": "2026-05-02T20:00:00Z", "point_in_time_eligible": True, "normalized_field": "capital_structure_and_contingent_consideration", "verification_status": "VERIFIED"},
        {"evidence_id": "mvll-v2-e6", "source_url": "https://investor.marvell.com/news-events/press-releases/detail/1023/marvell-technology-inc-reports-first-quarter-of-fiscal-year-2027-financial-results", "source_type": "ISSUER_IR", "published_at": "2026-05-27T20:05:00Z", "retrieved_at": generated_at, "effective_at": "2026-05-27T20:05:00Z", "point_in_time_eligible": True, "normalized_field": "q1_results_and_q2_guidance", "verification_status": "VERIFIED"},
    ])
    value["evidence_ids"] = list(dict.fromkeys(value["evidence_ids"] + ["mvll-v2-e5", "mvll-v2-e6"]))
    value["claims"].extend([
        {"claim_id": "mvll-v2-c7", "claim_type": "CAPITAL_STRUCTURE", "normalized_claim": "MRVL known gross stress includes 21.778 million Series A conversion shares, up to 24.4 million Celestial earnout shares, up to 4.2 million customer-warrant shares, and up to $233 million Celestial cash consideration; no price multiple is applied to MVLL.", "evidence_ids": ["mvll-v2-e5"]},
        {"claim_id": "mvll-v2-c8", "claim_type": "VALUATION", "normalized_claim": "MRVL scenario evidence uses Kiwoom Raw close and official Q2 revenue guidance; valuation judgement remains UNCLASSIFIED and is not an MVLL target price or add authority.", "evidence_ids": ["mvll-v2-e5", "mvll-v2-e6"]},
    ])
    value["claim_ids"] = list(dict.fromkeys(value["claim_ids"] + ["mvll-v2-c7", "mvll-v2-c8"]))
    return recompute_hashes(value)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    generated_at = utc_now()
    out_root = root / "workspace/research/mvll-shadow-activation/2026-08-13/v3"
    mvll_price_path = out_root / "mvll-price-authority-v3.json"
    mrvl_price_path = out_root / "mrvl-price-authority-v3.json"
    event_review_path = out_root / "mvll-mrvl-event-review-v3.json"
    valuation_path = root / "workspace/research/valuation-snapshots/2026-08-13/mrvl-valuation-snapshot-v3.json"
    baseline_path = root / "workspace/research/holding-baseline-candidates/2026-08-14/mvll-20260814-v3.json"
    mvll_link_path = root / "workspace/research/baseline-event-links/2026-08-13/v2.6.14/mvll-v3-product-event-link.json"
    mrvl_link_path = root / "workspace/research/baseline-event-links/2026-08-13/v2.6.14/mrvl-v3-underlying-event-link.json"
    overlay_path = root / "workspace/research/holding-overlays/2026-08-13/mvll-overlay-v3.json"
    compile_path = root / "workspace/research/shadow-compiles/2026-08-13/mvll-shadow-compile-v3.json"
    manifest_path = root / "workspace/outputs/activation/mvll-v2-shadow/20260814-v3/build-manifest.json"

    mvll_price = build_price_authority(root, "MVLL", generated_at)
    mrvl_price = build_price_authority(root, "MRVL", generated_at)
    write_json(mvll_price_path, mvll_price)
    write_json(mrvl_price_path, mrvl_price)
    price_schema = root / "manage-us-stock-strategy/schemas/us-stock-price-authority.schema.json"
    mvll_price_errors = validate_instance(mvll_price, price_schema) + validate_price_authority_artifact(mvll_price)
    mrvl_price_errors = validate_instance(mrvl_price, price_schema) + validate_price_authority_artifact(mrvl_price)

    valuation = build_valuation(root, mrvl_price, generated_at)
    write_json(valuation_path, valuation)
    valuation_validation = validate_valuation_snapshot(
        valuation, root / "manage-us-stock-strategy/schemas/issuer-valuation-snapshot.schema.json")

    event_review = build_event_review(root, generated_at)
    write_json(event_review_path, event_review)
    baseline = build_baseline(root, mvll_price, valuation, event_review_path, generated_at)
    write_json(baseline_path, baseline)
    baseline_schema = root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json"
    baseline_validation = validate_baseline(baseline, baseline_schema)

    mvll_link = build_baseline_event_link(
        baseline, event_review, event_bundle_path=event_review_path, ticker="MVLL",
        entity_role="DIRECT_PRODUCT", link_created_at=generated_at)
    mrvl_link = build_baseline_event_link(
        baseline, event_review, event_bundle_path=event_review_path, ticker="MRVL",
        entity_role="SUPPLEMENTAL_UNDERLYING", link_created_at=generated_at)
    write_json(mvll_link_path, mvll_link)
    write_json(mrvl_link_path, mrvl_link)
    link_schema = root / "manage-us-stock-strategy/schemas/baseline-event-link.schema.json"
    mvll_link_validation = validate_event_link(mvll_link, schema_path=link_schema, baseline=baseline, event_bundle_path=event_review_path)
    mrvl_link_validation = validate_event_link(mrvl_link, schema_path=link_schema, baseline=baseline, event_bundle_path=event_review_path)

    overlay = deepcopy(load_json(root / "workspace/research/holding-overlays/2026-08-13/mvll-overlay.json"))
    overlay.update({
        "primary_price_status": "VALIDATED",
        "independent_price_status": "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE_NONBLOCKING",
        "event_risk_status": "CONTEXT_ONLY",
        "price_evidence_id": "mvll-20260813-kiwoom-price-authority-v3",
        "price_evidence_hash": mvll_price["evidence_hash"],
        "overlay_hash": "0" * 64,
    })
    overlay["overlay_hash"] = canonical_hash(without_hash(overlay, "overlay_hash"))
    write_json(overlay_path, overlay)

    compiled = compile_shadow(
        baseline=baseline, valuation=valuation, event_link=mvll_link, overlay=overlay,
        portfolio=load_json(root / "stock-strategy-system/portfolio_state.json"),
        policy_path=root / "workspace/policies/holding_research_baseline_policy.json",
        provider_scope_path=root / "workspace/policies/kiwoom-session-aware-priority-policy.json",
        portfolio_path=root / "stock-strategy-system/portfolio_state.json",
        baseline_schema=baseline_schema,
        live_strategy_state="UNCHANGED",
        blocked_decision_classes=["EMA10_RECLAIM_RVOL20"],
    )
    write_json(compile_path, compiled)
    compile_errors = validate_instance(compiled, root / "manage-us-stock-strategy/schemas/shadow-baseline-compile-result.schema.json")

    gates = {
        "mvll_kiwoom_price": not mvll_price_errors and not mvll_price["blocking"],
        "mrvl_kiwoom_price": not mrvl_price_errors and not mrvl_price["blocking"],
        "valuation": valuation_validation["validation_status"] == "PASSED" and valuation["valuation_evidence_status"] == "SCENARIO_VALIDATED",
        "event_links": mvll_link_validation["validation_status"] == "PASSED" and mrvl_link_validation["validation_status"] == "PASSED" and mvll_link["link_validation_status"] == "VALID" and mrvl_link["link_validation_status"] == "VALID",
        "baseline": baseline_validation["validation_status"] == "PASSED" and baseline["content_status"] == "COMPLETE",
        "shadow_compile": not compile_errors and compiled["shadow_compile_status"] == "PASSED" and not compiled["remaining_conditions"],
        "technical_block_preserved": "EMA10_RECLAIM_RVOL20" in compiled["blocked_decision_classes"],
        "authority_boundary": compiled["quantity"] is None and compiled["quantity_authority"] == "none" and compiled["order_authority"] is False,
    }
    artifacts = [mvll_price_path, mrvl_price_path, event_review_path, valuation_path, baseline_path,
                 mvll_link_path, mrvl_link_path, overlay_path, compile_path]
    manifest = {
        "schema_version": "2.6.14", "build_id": "mvll-v3-shadow-build-20260814",
        "generated_at": generated_at, "market_session": MARKET_SESSION, "gates": gates,
        "validator_results": {"mvll_price": mvll_price_errors, "mrvl_price": mrvl_price_errors,
                              "valuation": valuation_validation, "baseline": baseline_validation,
                              "mvll_event_link": mvll_link_validation, "mrvl_event_link": mrvl_link_validation,
                              "compile_schema_errors": compile_errors},
        "artifacts": {path.relative_to(root).as_posix(): file_hash(path) for path in artifacts},
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    write_json(manifest_path, manifest)
    status = "MVLL_V2_SHADOW_COMPILE_READY" if all(gates.values()) else "MVLL_V2_BUILD_BLOCKED"
    print(json.dumps({"status": status, "gates": gates, "manifest": manifest_path.relative_to(root).as_posix()}, ensure_ascii=False))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
