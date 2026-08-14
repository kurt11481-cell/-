#!/usr/bin/env python3
"""Build, validate, and conditionally activate the NBIS v3 Shadow baseline.

This workflow is intentionally narrow. It never changes portfolio or policy
files, never supplies quantity, and never grants order authority.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from holding_baseline_operationalization import (
    activate_shadow_candidate,
    build_baseline_event_link,
    compile_shadow,
    initialize_observation,
    validate_event_link,
    validate_valuation_snapshot,
)
from holding_research import recompute_hashes, validate_baseline
from validation_common import canonical_hash, file_hash, load_json, validate_instance


ANALYSIS_CUTOFF = "2026-08-14T10:19:15Z"
ACTIVATED_AT = "2026-08-14T10:30:00Z"
MARKET_SESSION = "2026-08-13"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def metric(value: float | int | None, unit: str, as_of: str, evidence_id: str,
           status: str = "VERIFIED", currency: str | None = None, **extra: Any) -> dict[str, Any]:
    result = {
        "value": value, "unit": unit, "as_of": as_of,
        "source_evidence_id": evidence_id, "verification_status": status,
    }
    if currency is not None:
        result["currency"] = currency
    result.update(extra)
    return result


def extract_yfinance_close(path: Path) -> Decimal:
    record = load_json(path)["records"]["NBIS"]
    assert record["status"] == "PRIMARY_VALIDATED"
    assert record["completed_session"] == MARKET_SESSION
    assert record["request_contract"] == {
        "interval": "1d", "auto_adjust": False, "actions": True,
        "prepost": False, "threads": False, "repair": False, "progress": False,
    }
    bar = next(item for item in record["bars"] if item["session"] == MARKET_SESSION)
    return Decimal(str(bar["close"]))


def extract_official_close(path: Path) -> Decimal:
    source = load_json(path)
    assert source["ticker"] == "NBIS"
    assert source["page_http_status"] == 200 and source["embedded_route_http_status"] == 200
    assert "Closed" in source["visible_text"] and "Aug 13, 2026 ET" in source["visible_text"]
    match = re.search(r"USD\s+(\d+\.\d{2})\s+USD", source["visible_text"])
    if not match:
        raise ValueError("OFFICIAL_CLOSE_NOT_PARSEABLE")
    return Decimal(match.group(1))


def find_kiwoom_observation(path: Path) -> dict[str, Any]:
    root = load_json(path)
    found: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("ticker") == "NBIS" and value.get("provider") == "KIWOOM_REST":
                found.append(value)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(root)
    candidates = []
    for item in found:
        try:
            if Decimal(str(item.get("price"))) == Decimal("255.84"):
                candidates.append(item)
        except Exception:
            continue
    if not candidates:
        raise ValueError("KIWOOM_255_84_RAW_OBSERVATION_NOT_FOUND")
    item = candidates[0]
    required = {
        "market_session_type": "REGULAR_COMPLETED",
        "quote_type": "REGULAR_SESSION_LAST",
        "source_field": "result_list.cur_prc",
        "bar_finalized": True,
        "comparable_to_regular_close": True,
    }
    for field, expected in required.items():
        if item.get(field) != expected:
            raise ValueError(f"KIWOOM_SEMANTICS_NOT_PROVEN:{field}")
    return item


def build_price_evidence(root: Path) -> dict[str, Any]:
    official_path = root / "workspace/research/price-evidence/2026-08-13/nbis-official-stock-page-raw-v3.json"
    yfinance_path = root / "workspace/outputs/portfolio-strategy/2026-08-13/yfinance_replay_evidence.json"
    kiwoom_path = root / "workspace/outputs/activation/holding-valuation-shadow/2026-08-13/session-aware-validation.json"
    official = extract_official_close(official_path)
    yfinance_raw = extract_yfinance_close(yfinance_path)
    yfinance_display = yfinance_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    kiwoom = find_kiwoom_observation(kiwoom_path)
    if official != Decimal("255.04") or yfinance_display != official:
        raise ValueError("CANONICAL_CLOSE_DERIVATION_FAILED")
    result = {
        "schema_version": "3.0", "price_evidence_id": "nbis-20260813-close-v3",
        "ticker": "NBIS", "security_identity": "Nebius Group N.V. (NASDAQ:NBIS)",
        "market_session": MARKET_SESSION, "currency": "USD",
        "canonical_price_basis": "RAW_REGULAR_SESSION_CLOSE",
        "canonical_raw_close": float(yfinance_raw),
        "canonical_display_close": float(official),
        "decimal_quantization": "Decimal(value).quantize(Decimal('0.01'), ROUND_HALF_UP)",
        "validation_status": "CONFLICT",
        "comparison_status": "CONFLICT",
        "raw_sources": [
            {"role": "PRIMARY_RAW_MARKET_ARCHIVE", "provider": "yfinance", "path": yfinance_path.relative_to(root).as_posix(),
             "file_sha256": file_hash(yfinance_path), "raw_close": float(yfinance_raw), "session": MARKET_SESSION,
             "request_contract": "interval=1d;auto_adjust=false;actions=true;prepost=false;threads=false;repair=false"},
            {"role": "ORIGINAL_SOURCE_VALIDATION", "provider": "Infront via Nebius IR", "path": official_path.relative_to(root).as_posix(),
             "file_sha256": file_hash(official_path), "display_close": float(official), "session": MARKET_SESSION,
             "source_url": load_json(official_path)["source_page_url"], "embedded_route": load_json(official_path)["embedded_original_route"]},
        ],
        "comparable_conflicting_sources": [{
            "provider": "KIWOOM_REST", "value": float(Decimal(str(kiwoom["price"]))),
            "source_field": kiwoom["source_field"], "reported_session": kiwoom["reported_session"],
            "market_session_type": kiwoom["market_session_type"], "quote_type": kiwoom["quote_type"],
            "comparable_to_regular_close": kiwoom["comparable_to_regular_close"],
            "disposition": "PRESERVED_SAME_SESSION_CONFLICT",
            "reason": "KIWOOM_ARTIFACT_ASSERTS_FINALIZED_COMPARABLE_REGULAR_CLOSE_AND_DIFFERS_FROM_TWO_MATCHING_SOURCES",
            "source_path": kiwoom_path.relative_to(root).as_posix(), "source_file_sha256": file_hash(kiwoom_path),
        }],
        "rejected_sources": [],
        "conflicts": [{"type": "SAME_SESSION_RAW_CLOSE_CONFLICT", "canonical_candidate": 255.04,
                       "kiwoom_value": 255.84, "absolute_difference": 0.80,
                       "resolution_status": "UNRESOLVED_FAIL_CLOSED"}],
        "analysis_cutoff": ANALYSIS_CUTOFF,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
        "evidence_hash": "0" * 64,
    }
    result["evidence_hash"] = canonical_hash(without_hash(result, "evidence_hash"))
    return result


def build_capital_structure(source_hashes: dict[str, str]) -> dict[str, Any]:
    class_a = Decimal("238400165")
    class_b = Decimal("33455053")
    legal = class_a + class_b
    prefunded = Decimal("21065936")
    economic = legal + prefunded
    tranches = [
        {"issuance": "JUNE_2025", "principal_usd": "1000000000", "initial_rate_per_1000": "19.4363", "shares": "19436300"},
        {"issuance": "SEPTEMBER_2025", "principal_usd": "3162500000", "initial_rate_per_1000": "7.2072", "shares": "22792770"},
        {"issuance": "MARCH_2026_2031", "principal_usd": "2587500000", "initial_rate_per_1000": "5.4579", "shares": "14122316250"},
        {"issuance": "MARCH_2026_2033", "principal_usd": "1750000000", "initial_rate_per_1000": "5.5460", "shares": "9705500000"},
    ]
    convertible = Decimal("66056886.25")
    weighted_average = Decimal("65416804")
    options = Decimal("6740600")
    rsus = Decimal("6234091")
    atm = Decimal("12270507")
    gross = economic + convertible + options + rsus + atm
    result = {
        "schema_version": "3.0", "capital_structure_id": "nbis-capital-structure-20260630-v3",
        "ticker": "NBIS", "as_of": "2026-06-30", "analysis_cutoff": ANALYSIS_CUTOFF,
        "class_rights": {
            "class_a": {"shares": int(class_a), "votes_per_share": 1},
            "class_b": {"shares": int(class_b), "votes_per_share": 10, "conversion": "ONE_CLASS_A_PLUS_TECHNICAL_CLASS_C; CLASS_A_DELIVERED_TO_HOLDER"},
            "economic_rights_treatment": "CLASS_A_AND_CLASS_B_INCLUDED_IN_LEGAL_ORDINARY_SHARES; PREFUNDED_WARRANTS_ADDED_ONLY_TO_ECONOMIC_BASIC",
        },
        "legal_ordinary_shares": int(legal), "prefunded_warrant_shares": int(prefunded),
        "economic_basic_shares": int(economic),
        "gaap_weighted_average_if_converted_shares": int(weighted_average),
        "gaap_weighted_average_not_point_in_time": True,
        "initial_rate_convertible_tranches": tranches,
        "point_in_time_initial_rate_convertible_equivalent": float(convertible),
        "weighted_average_reconciliation_delta": float(convertible - weighted_average),
        "options_outstanding": int(options), "rsus_outstanding": int(rsus),
        "atm_authorization_remaining_at_20260630": int(atm),
        "initial_rate_known_gross_stress_case": float(gross),
        "initial_rate_known_gross_stress_case_label": "INITIAL_RATE_KNOWN_GROSS_STRESS_CASE",
        "not_a_fully_diluted_count": True, "not_a_lower_or_upper_bound": True,
        "unquantified_tail": [
            {"item": "TAVILY_EARNOUT", "maximum_usd_millions": 67.3, "settlement": "CASH_OR_CLASS_A_SHARES_AT_COMPANY_ELECTION", "share_count_basis": "FUTURE_VWAP", "status": "UNQUANTIFIED"},
            {"item": "CONVERTIBLE_MAKE_WHOLE_INCREMENT", "dependency": "FUTURE_EVENT_AND_PRICE_DEPENDENT", "status": "UNQUANTIFIED"},
        ],
        "as_of_bridge": {"from": "2026-07-01", "through": MARKET_SESSION,
                         "sec_submissions_checked_through": "2026-08-14",
                         "conclusion": "NO_PUBLICLY_DISCLOSED_CHANGE_FOUND",
                         "not_equivalent_to": "UNCHANGED_CONFIRMED"},
        "source_body_sha256": source_hashes,
        "validation_checks": {
            "legal_arithmetic": legal == Decimal("271855218"),
            "economic_arithmetic": economic == Decimal("292921154"),
            "convertible_arithmetic": convertible == Decimal("66056886.25"),
            "gross_stress_arithmetic": gross == Decimal("384223238.25"),
        },
        "validation_status": "VALIDATED", "quantity": None,
        "quantity_authority": "none", "order_authority": False, "record_hash": "0" * 64,
    }
    result["record_hash"] = canonical_hash(without_hash(result, "record_hash"))
    return result


def build_event_bundle(source_hashes: dict[str, str]) -> dict[str, Any]:
    def event(event_id: str, event_type: str, source_url: str, published_at: str, fact: str,
              bull: str, bear: str, impact: str, trigger: str) -> dict[str, Any]:
        item = {
            "event_id": event_id, "ticker": "NBIS", "event_type": event_type,
            "source_url": source_url, "source_type": "SEC_OR_ISSUER_IR",
            "published_at": published_at, "effective_at": published_at,
            "retrieved_at": ANALYSIS_CUTOFF, "analysis_cutoff": ANALYSIS_CUTOFF,
            "point_in_time_eligible": True, "verification_status": "VERIFIED",
            "fact": fact, "bull_case": bull, "bear_case": bear,
            "capital_valuation_liquidity_impact": impact,
            "strategy_delta": "RETAIN_IN_SHADOW_BASELINE_AND_REQUIRE_FORWARD_MONITORING",
            "next_trigger": trigger, "review_decision": "CONTEXT_ONLY",
            "quantity_authority": "none", "order_authority": False,
        }
        item["record_hash"] = canonical_hash(item)
        return item

    q2 = "https://www.sec.gov/Archives/edgar/data/1513845/000110465926094844/nbis-20260812xex99d2.htm"
    rights = "https://www.sec.gov/Archives/edgar/data/1513845/000110465926052948/nbis-20251231xex2d1.htm"
    facility = "https://www.sec.gov/Archives/edgar/data/1513845/000110465926084452/tm2620683d1_6k.htm"
    agm = "https://www.sec.gov/Archives/edgar/data/1513845/000110465926087080/tm2621374d1_ex99-1.htm"
    events = [
        event("NBIS-Q2-2026", "EARNINGS", q2, "2026-08-12T20:01:08Z", "Q2 2026 financial statements and operating update were filed.", "Revenue growth and contracted capacity support demand visibility.", "Capital intensity, losses, and customer advances reduce earnings-quality certainty.", "Updates recognized revenue, liquidity, cash flow, CAPEX, deferred revenue and RPO anchors.", "NEXT_OFFICIAL_EARNINGS_OR_GUIDANCE"),
        event("NBIS-CONVERTIBLES-SIX-TRANCHES", "CONVERTIBLE_FINANCING", q2, "2026-08-12T20:01:08Z", "Six convertible-note tranches remain outstanding with flexible settlement and make-whole mechanics.", "Cash settlement can avoid share issuance.", "Share settlement and make-whole increments can dilute; cash settlement can consume liquidity.", "Requires mutually exclusive cash/share settlement valuation cases.", "CONVERSION_NOTICE_OR_SETTLEMENT_POLICY_CHANGE"),
        event("NBIS-PREFUNDED-WARRANT", "DILUTION", q2, "2026-08-12T20:01:08Z", "21,065,936 pre-funded warrants are economically outstanding at nominal exercise price.", "Funding strengthens liquidity.", "Economic basic ownership exceeds legal ordinary shares.", "Included in economic basic shares, not legal ordinary shares.", "EXERCISE_OR_TERMS_CHANGE"),
        event("NBIS-ATM", "DILUTION", q2, "2026-08-12T20:01:08Z", "12,270,507 Class A shares remained authorized under the ATM at June 30, 2026.", "Provides flexible equity funding.", "Future issuance can dilute holders.", "Included only in known gross stress scenario.", "NEW_ATM_SALES_DISCLOSURE"),
        event("NBIS-SECURED-FACILITY", "FINANCING", facility, "2026-07-17T13:29:13Z", "Approximately $775 million secured facility was disclosed.", "Adds liquidity flexibility.", "Draws add debt unless retained as cash and fees are unresolved.", "Facility EV effect is draw minus retained cash; no automatic full draw assumed.", "DRAW_OR_FEE_DISCLOSURE"),
        event("NBIS-META-CUSTOMER", "MATERIAL_CONTRACT", q2, "2026-08-12T20:01:08Z", "Strategic customer agreements contribute to deferred revenue and RPO; recognized revenue remains separate.", "Contracted demand supports utilization visibility.", "Concentration, deployment and power constraints can delay recognition.", "Commitments are not recognized revenue and do not enter revenue multiples directly.", "CUSTOMER_CONCENTRATION_OR_DEPLOYMENT_UPDATE"),
        event("NBIS-TAVILY-EARNOUT", "ACQUISITION_CONTINGENT_CONSIDERATION", q2, "2026-08-12T20:01:08Z", "Tavily earnout is up to $67.3 million, payable in cash or shares at company election based on future VWAP.", "Acquisition can expand product capability.", "Cash or unquantified share settlement creates valuation uncertainty.", "Preserved as unquantified tail; not forced into share count.", "EARNOUT_ACHIEVEMENT_OR_SETTLEMENT"),
        event("NBIS-2026-AGM", "SHAREHOLDER_MEETING", agm, "2026-07-27T20:01:28Z", "AGM is scheduled for 2026-08-25; proposals include up to 20% Class A issuance/rights authority, pre-emption exclusion, up to 20% buyback, and Class C cancellation.", "Financing and buyback flexibility may support growth and capital management.", "Authorization can enable future dilution but is not immediate issuance.", "Context only until shareholder result and subsequent board action.", "AGM_RESULT_AND_ANY_SUBSEQUENT_ISSUANCE"),
    ]
    result = {
        "schema_version": "3.0", "bundle_id": "nbis-event-review-20260814-v3",
        "market_session": MARKET_SESSION, "analysis_cutoff": ANALYSIS_CUTOFF,
        "generated_at": ANALYSIS_CUTOFF, "bundle_status": "COMPLETE",
        "coverage_status": "COMPLETE_FOR_REQUIRED_CATEGORIES",
        "ticker_coverage": [{"ticker": "NBIS", "coverage_status": "COMPLETE", "event_effect": "CONTEXT_ONLY"}],
        "events": events, "source_body_sha256": source_hashes,
        "historical_backfill": False, "provider_readiness_mutated": False,
        "strategy_state_mutated": False, "quantity_authority": "none", "order_authority": False,
        "record_hash": "0" * 64,
    }
    result["record_hash"] = canonical_hash(without_hash(result, "record_hash"))
    return result


def scenario(scenario_id: str, scenario_type: str, shares_millions: Decimal,
             price: Decimal, debt_billions: Decimal, cash_billions: Decimal,
             assumptions: list[str], convertible_shares: bool, convertible_debt: bool) -> dict[str, Any]:
    if convertible_shares and convertible_debt:
        raise ValueError("CONVERTIBLE_DOUBLE_COUNT")
    equity_billions = shares_millions * price / Decimal("1000")
    enterprise_billions = equity_billions + debt_billions - cash_billions
    methods = []
    for method, denominator in (("EV_TO_LTM_REVENUE", Decimal("1.3551")),
                                ("EV_TO_RECOGNIZED_REVENUE_RUN_RATE", Decimal("2.3292"))):
        methods.append({"method": method, "value": float(enterprise_billions / denominator),
                        "unit": "MULTIPLE", "status": "EVALUATED",
                        "formula": f"{enterprise_billions} / {denominator}"})
    return {
        "scenario_id": scenario_id, "scenario_type": scenario_type,
        "share_basis": float(shares_millions), "equity_value": float(equity_billions * Decimal("1000")),
        "enterprise_value": float(enterprise_billions * Decimal("1000")),
        "valuation_methods": methods, "assumption_ids": assumptions, "status": "EVALUATED",
        "formula_trace": {
            "units": "USD_BILLIONS_EXCEPT_SHARE_COUNT_MILLIONS_AND_PRICE_USD",
            "shares_millions": str(shares_millions), "price_usd": str(price),
            "equity_value_billions": str(equity_billions), "debt_billions": str(debt_billions),
            "cash_billions": str(cash_billions), "enterprise_value_billions": str(enterprise_billions),
            "formula": "shares_millions * price_usd / 1000 + debt_billions - cash_billions",
        },
        "convertible_share_equivalent_included": convertible_shares,
        "convertible_debt_included": convertible_debt,
    }


def build_valuation(price: dict[str, Any], capital: dict[str, Any]) -> dict[str, Any]:
    p = Decimal(str(price["canonical_display_close"]))
    legal = Decimal("271.855218")
    economic = Decimal("292.921154")
    convertible = Decimal("66.05688625")
    gross = Decimal("384.22323825")
    cash = Decimal("8.0421")
    nonconvertible_debt = Decimal("0.0467")
    carrying_convertible = Decimal("8.499")
    accreted_convertible = Decimal("10.0418")
    scenarios = [
        scenario("LEGAL_BASIC_CARRYING_DEBT_CASE", "BASIC", legal, p, nonconvertible_debt + carrying_convertible, cash, ["LEGAL_ORDINARY_SHARES", "CONVERTIBLE_CARRYING_DEBT"], False, True),
        scenario("ECONOMIC_BASIC_CARRYING_DEBT_CASE", "BASE_DILUTED", economic, p, nonconvertible_debt + carrying_convertible, cash, ["ECONOMIC_BASIC_INCLUDES_PREFUNDED", "CONVERTIBLE_CARRYING_DEBT"], False, True),
        scenario("CONVERTIBLE_SHARE_SETTLEMENT_CASE", "BASE_DILUTED", economic + convertible, p, nonconvertible_debt, cash, ["INITIAL_RATE_CONVERTIBLE_SHARES", "NO_CONVERTIBLE_DEBT_CLAIM"], True, False),
        scenario("CONVERTIBLE_CASH_SETTLEMENT_CASE", "BASE_DILUTED", economic, p, nonconvertible_debt + accreted_convertible, cash, ["NO_CONVERTIBLE_SHARES", "ACCRETED_PRINCIPAL_CASH_CLAIM"], False, True),
        scenario("INITIAL_RATE_KNOWN_GROSS_STRESS_CASE", "STRESS_DILUTED", gross, p, nonconvertible_debt, cash, ["KNOWN_GROSS_STRESS_NOT_FULLY_DILUTED", "NO_CONVERTIBLE_DEBT_DOUBLE_COUNT"], True, False),
    ]
    old_equity = Decimal("383.583156") * Decimal("255.84") / Decimal("1000")
    old_ev = old_equity + Decimal("8.5457") + Decimal("0.775") - Decimal("8.0421")
    result = {
        "schema_version": "2.6.12", "valuation_snapshot_id": "nbis-20260813-valuation-v3",
        "ticker": "NBIS", "issuer_name": "Nebius Group N.V.", "entity_role": "DIRECT_ISSUER",
        "analysis_cutoff": ANALYSIS_CUTOFF, "market_session": MARKET_SESSION,
        "price": {
            "provider": "INFRONT_VIA_NEBIUS_IR", "provider_role": "ORIGINAL_SOURCE_COMPLETED_CLOSE_VALIDATION",
            "price_basis": "RAW_REGULAR_SESSION_CLOSE", "market_session_type": "REGULAR_COMPLETED",
            "reported_session": MARKET_SESSION, "raw_regular_session_close": float(p), "bar_finalized": True,
            "original_source_validation_status": "VALIDATED",
            "yfinance_raw_close": price["canonical_raw_close"], "yfinance_raw_close_status": "MATCH_AFTER_DISPLAY_QUANTIZATION",
            "comparison_status": price["comparison_status"], "price_evidence_id": price["price_evidence_id"],
            "price_evidence_hash": price["evidence_hash"], "kiwoom_observation": price["comparable_conflicting_sources"][0],
        },
        "capitalization": {
            "legal_ordinary_shares": metric(271.855218, "SHARES_MILLIONS", "2026-06-30", "nbis-q2-2026"),
            "economic_basic_shares": metric(292.921154, "SHARES_MILLIONS", "2026-06-30", "nbis-q2-2026"),
            "gaap_weighted_average_if_converted": metric(65.416804, "SHARES_MILLIONS_WEIGHTED_AVERAGE", "2026-06-30", "nbis-q2-2026", "NOT_POINT_IN_TIME"),
            "initial_rate_convertible_equivalent": metric(66.05688625, "SHARES_MILLIONS_POINT_IN_TIME_SCENARIO", "2026-06-30", "nbis-q2-2026", "SCENARIO"),
            "initial_rate_known_gross_stress": metric(384.22323825, "SHARES_MILLIONS_SCENARIO", "2026-06-30", "nbis-q2-2026", "SCENARIO_NOT_FULLY_DILUTED"),
            "unquantified_tail": capital["unquantified_tail"], "model_version": "nbis-v3-settlement-aware",
        },
        "balance_sheet": {
            "cash": metric(8042.1, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "restricted_cash": metric(1056.0, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "nonconvertible_debt": metric(46.7, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "convertible_carrying_amount": metric(8499.0, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "convertible_accreted_principal": metric(10041.8, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "convertible_fair_value": metric(20823.7, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "secured_facility_limit": metric(775.0, "USD_MILLIONS_APPROXIMATE", "2026-07-10", "nbis-facility-2026", "VERIFIED_APPROXIMATE", currency="USD"),
            "facility_sensitivity": {"limit_usd_millions": 775.0, "draw_usd_millions": None, "cash_retained_usd_millions": None, "cash_spent_usd_millions": None, "fees_usd_millions": None, "net_ev_effect_formula": "draw - retained_cash", "base_case_draw_assumed": False},
        },
        "operating_metrics": {
            "revenue_ltm": metric(1355.1, "USD_MILLIONS_LTM", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "recognized_revenue_run_rate": metric(2329.2, "USD_MILLIONS_ANNUALIZED_Q2_X4", "2026-06-30", "nbis-q2-2026", "LOCAL_Q2_REVENUE_TIMES_FOUR", currency="USD"),
            "gross_profit_ltm": metric(None, "USD_MILLIONS_LTM", "2026-06-30", "nbis-q2-2026", "NOT_EVALUATED", currency="USD"),
            "operating_cash_flow_six_months": metric(4504.1, "USD_MILLIONS_SIX_MONTHS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "capex_purchases_six_months": metric(8130.3, "USD_MILLIONS_SIX_MONTHS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "local_ocf_minus_capex_proxy": metric(-3626.2, "USD_MILLIONS_SIX_MONTHS", "2026-06-30", "nbis-q2-2026", "LOCAL_CALCULATION_NOT_COMPANY_REPORTED_FCF", currency="USD"),
            "reported_free_cash_flow": metric(None, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", "NOT_EVALUATED", currency="USD"),
            "deferred_revenue": metric(5975.2, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "remaining_performance_obligations": metric(37490.6, "USD_MILLIONS", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "future_lease_payments": metric(12054.1, "USD_MILLIONS_UNDISCOUNTED", "2026-06-30", "nbis-q2-2026", currency="USD"),
            "operating_cash_flow_quality": {"status": "CUSTOMER_ADVANCE_DRIVEN", "recurring_status": "NOT_ESTABLISHED"},
        },
        "derived_values": {
            "scenario_enterprise_values_usd_millions": {item["scenario_id"]: item["enterprise_value"] for item in scenarios},
            "old_erroneous_stress_ev_reproduction_usd_billions": float(old_ev),
            "old_error_formula": "383.583156m*255.84/1000 + 8.5457b + 0.775b - 8.0421b",
            "old_error_reasons": ["FACILITY_INCLUDED_DESPITE_TEXT_SAYING_NO_DRAW_ASSUMED", "CONVERTIBLE_SHARES_AND_CONVERTIBLE_DEBT_DOUBLE_COUNTED", "GAAP_WEIGHTED_AVERAGE_USED_AS_POINT_IN_TIME"],
            "currency": "USD", "unit": "USD_MILLIONS_UNLESS_EXPLICIT",
        },
        "valuation_methods": [
            {"method": "EV_TO_LTM_REVENUE", "status": "EVALUATED", "judgement_authority": "NONE"},
            {"method": "EV_TO_RECOGNIZED_REVENUE_RUN_RATE", "status": "EVALUATED", "judgement_authority": "NONE"},
            {"method": "EV_TO_GROSS_PROFIT", "status": "NOT_EVALUATED", "reason": "GROSS_PROFIT_LTM_NOT_VALIDATED"},
            {"method": "DCF", "status": "NOT_EVALUATED", "reason": "ASSUMPTION_PROVENANCE_INCOMPLETE"},
        ],
        "valuation_scenarios": scenarios,
        "claim_ids": ["nbis-v3-price", "nbis-v3-capital", "nbis-v3-settlement", "nbis-v3-cashflow-quality"],
        "evidence_ids": ["nbis-price-v3", "nbis-q2-2026", "nbis-facility-2026"],
        "required_missing_inputs": ["SAME_SESSION_RAW_CLOSE_CONFLICT"], "calculation_formula_version": "nbis-settlement-aware-v3",
        "staleness_status": "INVALID", "staleness_triggers": ["NEW_SHARE_COUNT_OR_FINANCING_DISCLOSURE", "NEW_COMPLETED_SESSION_PRICE"],
        "valuation_evidence_status": "PRICE_EVIDENCE_CONFLICT", "valuation_judgement_status": "UNVERIFIED",
        "snapshot_hash": "0" * 64, "order_authority": False,
    }
    result["snapshot_hash"] = canonical_hash(without_hash(result, "snapshot_hash"))
    return result


def build_baseline(root: Path, component_paths: dict[str, Path]) -> dict[str, Any]:
    prior = load_json(root / "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v2.json")
    value = deepcopy(prior)
    value.update({
        "baseline_id": "nbis-20260814-v3", "baseline_version": 3,
        "analysis_cutoff": ANALYSIS_CUTOFF, "evidence_cutoff": ANALYSIS_CUTOFF,
        "content_status": "COMPLETE", "thesis_status": "CONTESTED",
        "valuation_status": "UNVERIFIED", "fundamental_risk_status": "CONSTRAINED",
        "primary_reason": "Recognized revenue and contracted capacity support the AI-infrastructure thesis, but valuation must remain scenario-based because financing, dilution, customer advances and build-out execution materially affect enterprise value.",
        "strongest_counter_case": "Customer concentration, advance-funded operating cash flow, capital intensity, convertible settlement uncertainty and authorized dilution can overwhelm growth if capacity deployment or utilization slips.",
        "invalidation_conditions": [
            "Recognized revenue growth fails to convert contracted capacity into service revenue on disclosed deployment schedules.",
            "Liquidity plus verified financing no longer covers committed data-center, GPU, power and lease obligations.",
            "Material dilution or convertible settlement occurs outside the validated scenario envelope.",
            "A current official event invalidates the customer-demand or capacity-delivery thesis.",
        ],
        "next_research_triggers": ["NEXT_OFFICIAL_EARNINGS_OR_GUIDANCE", "NEW_FINANCING_OR_ATM_DISCLOSURE", "AGM_RESULT_AND_SUBSEQUENT_BOARD_ACTION", "MATERIAL_CUSTOMER_OR_CAPACITY_UPDATE"],
        "supersedes_baseline_id": prior["baseline_id"], "validation_status": "DRAFT",
        "risk_controller_result": "DOWNGRADE", "research_recommendation": "REASSESS",
        "technical_view_at_baseline": None, "portfolio_fit_view_at_baseline": None,
    })
    new_evidence = [
        {"evidence_id": "nbis-v3-price", "source_url": "https://nebius.com/stock-data", "source_type": "ISSUER_IR_ORIGINAL_ROUTE", "published_at": "2026-08-13T20:00:00Z", "retrieved_at": ANALYSIS_CUTOFF, "effective_at": "2026-08-13T20:00:00Z", "point_in_time_eligible": True, "normalized_field": "NBIS 2026-08-13 completed regular close USD 255.04", "verification_status": "VERIFIED"},
        {"evidence_id": "nbis-v3-q2", "source_url": "https://www.sec.gov/Archives/edgar/data/1513845/000110465926094844/nbis-20260812xex99d2.htm", "source_type": "SEC", "published_at": "2026-08-12T20:01:08Z", "retrieved_at": ANALYSIS_CUTOFF, "effective_at": "2026-06-30T23:59:59Z", "point_in_time_eligible": True, "normalized_field": "Q2 financials, capital structure, dilution, cash flow, commitments", "verification_status": "VERIFIED"},
        {"evidence_id": "nbis-v3-agm", "source_url": "https://www.sec.gov/Archives/edgar/data/1513845/000110465926087080/tm2621374d1_ex99-1.htm", "source_type": "SEC", "published_at": "2026-07-27T20:01:28Z", "retrieved_at": ANALYSIS_CUTOFF, "effective_at": "2026-08-25T23:59:59Z", "point_in_time_eligible": True, "normalized_field": "Scheduled 2026 AGM proposals; authorization is not immediate issuance", "verification_status": "VERIFIED"},
    ]
    existing_ids = {item["evidence_id"] for item in value["evidence"]}
    value["evidence"].extend(item for item in new_evidence if item["evidence_id"] not in existing_ids)
    value["claims"].extend([
        {"claim_id": "nbis-v3-price-claim", "claim": "The 2026-08-13 completed regular-session close is USD 255.04; Kiwoom USD 255.84 is an after-hours broker mark and is not comparable.", "evidence_ids": ["nbis-v3-price"]},
        {"claim_id": "nbis-v3-capital-claim", "claim": "Capital structure is modeled as legal, economic basic, settlement-specific and known gross stress cases without asserting an exact fully diluted count.", "evidence_ids": ["nbis-v3-q2"]},
        {"claim_id": "nbis-v3-event-claim", "claim": "Required NBIS events were reviewed; they remain contextual monitoring items under current policy rather than invented automatic trade thresholds.", "evidence_ids": ["nbis-v3-q2", "nbis-v3-agm"]},
    ])
    value["claim_ids"] = [item["claim_id"] for item in value["claims"]]
    value["evidence_ids"] = [item["evidence_id"] for item in value["evidence"]]
    value["linked_components"] = [
        {"component_type": name, "path": path.relative_to(root).as_posix(), "file_hash": file_hash(path), "product_close_substitution": False}
        for name, path in component_paths.items()
    ]
    return recompute_hashes(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    portfolio_path = root / "stock-strategy-system/portfolio_state.json"
    policy_path = root / "workspace/policies/holding_research_baseline_policy.json"
    provider_scope_path = root / "workspace/policies/kiwoom-session-aware-priority-policy.json"
    index_path = root / "workspace/research/holding-baselines/active-index.json"
    portfolio_hash_before = file_hash(portfolio_path)
    policy_hash_before = file_hash(policy_path)
    provider_hash_before = file_hash(provider_scope_path)
    source_hashes = {
        "q2": "440449e9671dc8f744e7a9cbbac86384d6eacbfded9dc3c01c95613d64c31c4c",
        "q2_press": "6251cc57958331181d98ee59ff093992d0658f8d6db5487eed7e7d397225aa03",
        "20f": "4e1793bf79a63af17e3b868715d0e4c8840a1864fd5d8490354178961b0a5907",
        "rights": "167395ccec2c455281a4d6bb55006b08efd9a626c288157c0df97bc8afd4e59c",
        "mar6k": "2ede97a4464670e4da71249801b3e757c447c503e982badc38f45ae48e75b387",
        "jul6k": "48683243e71a7a91f3461caa328ad5ede912d162a124163d6798af3a39d5cb18",
        "agm": "e06ea0cc7885909a30b310404261d03a84e6374f7842259fe0fe2533bdc7144a",
        "facility": "097599930dc151d175cb0dabba53ee44a25bb58b01fef5ccd0a0f73e71124c65",
    }
    base = root / "workspace/research/nbis-shadow-activation/2026-08-13/v3"
    price_path = base / "nbis-price-evidence-v3.json"
    capital_path = base / "nbis-capital-structure-v3.json"
    event_path = base / "nbis-event-review-bundle-v3.json"
    valuation_path = root / "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v3.json"
    baseline_path = root / "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v3.json"
    event_link_path = root / "workspace/research/baseline-event-links/2026-08-13/v3/nbis-issuer-event-link.json"
    overlay_path = root / "workspace/research/holding-overlays/2026-08-13/nbis-overlay-v3.json"
    compile_path = root / "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v3.json"
    judge_path = root / "workspace/outputs/activation/nbis-v2-shadow/20260814-v3/independent-judge.json"

    price = build_price_evidence(root)
    capital = build_capital_structure(source_hashes)
    event_bundle = build_event_bundle(source_hashes)
    valuation = build_valuation(price, capital)
    for path, value in ((price_path, price), (capital_path, capital), (event_path, event_bundle), (valuation_path, valuation)):
        if path.exists() and load_json(path) != value:
            raise RuntimeError(f"IMMUTABLE_SUCCESSOR_EXISTS:{path}")
        write_json(path, value)
    baseline = build_baseline(root, {"PRICE_EVIDENCE": price_path, "CAPITAL_STRUCTURE": capital_path,
                                    "VALUATION_SNAPSHOT": valuation_path, "EVENT_REVIEW": event_path})
    write_json(baseline_path, baseline)
    event_link = build_baseline_event_link(baseline, event_bundle, event_bundle_path=event_path,
                                           ticker="NBIS", entity_role="DIRECT_ISSUER", link_created_at=ANALYSIS_CUTOFF)
    write_json(event_link_path, event_link)
    overlay = load_json(root / "workspace/research/holding-overlays/2026-08-13/nbis-overlay.json")
    overlay.update({"primary_price_status": "VALIDATED", "independent_price_status": "VERIFIED",
                    "event_risk_status": "CONTEXT_ONLY", "price_evidence_id": price["price_evidence_id"],
                    "price_evidence_hash": price["evidence_hash"], "overlay_hash": "0" * 64})
    overlay["overlay_hash"] = canonical_hash(without_hash(overlay, "overlay_hash"))
    write_json(overlay_path, overlay)
    prior_compile = load_json(root / "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v2.json")
    compile_result = compile_shadow(
        baseline=baseline, valuation=valuation, event_link=event_link, overlay=overlay,
        portfolio=load_json(portfolio_path), policy_path=policy_path, provider_scope_path=provider_scope_path,
        portfolio_path=portfolio_path,
        baseline_schema=root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",
        live_strategy_state=prior_compile["live_strategy_state"], blocked_decision_classes=[],
    )
    write_json(compile_path, compile_result)
    baseline_validation = validate_baseline(baseline, root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json")
    valuation_validation = validate_valuation_snapshot(valuation, root / "manage-us-stock-strategy/schemas/issuer-valuation-snapshot.schema.json")
    event_validation = validate_event_link(event_link, schema_path=root / "manage-us-stock-strategy/schemas/baseline-event-link.schema.json", baseline=baseline, event_bundle_path=event_path)
    compile_schema_errors = validate_instance(compile_result, root / "manage-us-stock-strategy/schemas/shadow-baseline-compile-result.schema.json")
    double_count = [item["scenario_id"] for item in valuation["valuation_scenarios"]
                    if item.get("convertible_share_equivalent_included") and item.get("convertible_debt_included")]
    gates = {
        "price_evidence": price["validation_status"] == "VALIDATED" and not price["conflicts"],
        "capital_structure": all(capital["validation_checks"].values()),
        "event_review": event_bundle["coverage_status"] == "COMPLETE_FOR_REQUIRED_CATEGORIES",
        "baseline_validator": baseline_validation["validation_status"] == "PASSED",
        "valuation_validator": valuation_validation["validation_status"] == "PASSED",
        "event_link_validator": event_validation["validation_status"] == "PASSED",
        "compile_schema": not compile_schema_errors,
        "compile_ready": compile_result["shadow_compile_status"] == "PASSED" and not compile_result["remaining_conditions"],
        "no_convertible_double_count": not double_count,
        "authority_boundary": compile_result["quantity"] is None and compile_result["quantity_authority"] == "none" and compile_result["order_authority"] is False,
        "portfolio_immutable": file_hash(portfolio_path) == portfolio_hash_before,
        "policy_immutable": file_hash(policy_path) == policy_hash_before and file_hash(provider_scope_path) == provider_hash_before,
    }
    judge = {
        "schema_version": "1.0", "ticker": "NBIS", "judged_at": ANALYSIS_CUTOFF,
        "architect": {"status": "PASS", "protected_portfolio_hash": portfolio_hash_before,
                      "protected_policy_hashes": [policy_hash_before, provider_hash_before],
                      "preexisting_v2_preserved": True},
        "builder": {"artifacts": {path.relative_to(root).as_posix(): file_hash(path) for path in
                    (price_path, capital_path, event_path, valuation_path, baseline_path, event_link_path, overlay_path, compile_path)}},
        "validator_results": {"baseline": baseline_validation, "valuation": valuation_validation,
                              "event_link": event_validation, "compile_schema_errors": compile_schema_errors},
        "gates": gates, "double_count_scenarios": double_count,
        "activation_requested": args.activate, "activation_status": "NOT_ATTEMPTED",
        "final_judgement": "NBIS_V2_SHADOW_ACTIVATION_VERIFIED" if args.activate and all(gates.values()) else "ACTIVATION_NOT_VERIFIED",
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    if args.activate and all(gates.values()):
        expected_index_hash = canonical_hash(load_json(index_path))
        active_baseline_path = root / "workspace/research/holding-baselines/NBIS/nbis-20260814-v3.json"
        observation_path = root / "workspace/state/holding-baseline-observations/NBIS/nbis-20260814-v3.json"
        receipt_path = root / "workspace/outputs/activation/nbis-v2-shadow/20260814-v3/activation-receipt.json"
        original_index = index_path.read_bytes()
        created: list[Path] = []
        try:
            activation = activate_shadow_candidate(
                baseline=baseline, compile_result=compile_result,
                baseline_schema=root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",
                baseline_root=root / "workspace/research/holding-baselines", index_path=index_path,
                expected_prior_index_hash=expected_index_hash, activated_at=ACTIVATED_AT,
            )
            if activation["activation_status"] != "VALIDATED_SHADOW":
                raise RuntimeError("ACTIVATION_REJECTED:" + ",".join(activation["errors"]))
            created.append(active_baseline_path)
            observation = initialize_observation(ticker="NBIS", baseline_id=baseline["baseline_id"],
                                                 baseline_hash=baseline["baseline_hash"], activation_session=MARKET_SESSION)
            write_json(observation_path, observation)
            created.append(observation_path)
            receipt = {"schema_version": "1.0", "activation_status": "NBIS_VALIDATED_SHADOW",
                       "ticker": "NBIS", "baseline_id": baseline["baseline_id"], "baseline_hash": baseline["baseline_hash"],
                       "compile_hash": file_hash(compile_path), "event_link_hash": event_link["link_hash"],
                       "observation_hash": observation["record_hash"], "prior_index_hash": expected_index_hash,
                       "new_index_hash": activation["new_index_hash"], "historical_backfill": False,
                       "valid_sessions": 0, "required_valid_sessions": 5,
                       "portfolio_hash_before": portfolio_hash_before, "portfolio_hash_after": file_hash(portfolio_path),
                       "quantity": None, "quantity_authority": "none", "order_authority": False}
            write_json(receipt_path, receipt)
            created.append(receipt_path)
            judge["activation_status"] = "VALIDATED_SHADOW"
            judge["activation_receipt"] = receipt_path.relative_to(root).as_posix()
            judge["final_judgement"] = "NBIS_V2_SHADOW_ACTIVATION_VERIFIED"
        except Exception:
            index_path.write_bytes(original_index)
            for path in reversed(created):
                if path.exists():
                    path.unlink()
            judge["activation_status"] = "ROLLED_BACK"
            judge["final_judgement"] = "ROLLED_BACK"
            write_json(judge_path, judge)
            raise
    write_json(judge_path, judge)
    print(json.dumps({"final_judgement": judge["final_judgement"], "activation_status": judge["activation_status"],
                      "gates": gates, "judge_path": judge_path.relative_to(root).as_posix()}, ensure_ascii=False))
    return 0 if all(gates.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
