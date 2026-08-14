#!/usr/bin/env python3
"""Build immutable NBIS v4 valuation, baseline, event link, and Shadow compile.

The workflow uses a validated Kiwoom usa06012 Raw daily close as canonical.
yfinance and issuer prices are diagnostic references only.  It does not
activate the baseline or mutate portfolio, policy, live runtime, quantity, or
order authority.
"""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
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


def _find_kiwoom_finalized_record(root: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    snapshot_path = root / "workspace/outputs/activation/holding-valuation-shadow/2026-08-13/kiwoom-finalized-snapshot.json"
    validation_path = root / "workspace/outputs/activation/holding-valuation-shadow/2026-08-13/session-aware-validation.json"
    snapshot = load_json(snapshot_path)
    ticker = next(item for item in snapshot["ticker_results"] if item.get("ticker") == "NBIS")
    raw = ticker["raw"]
    bar = next(item for item in raw["bars"] if item.get("session") == MARKET_SESSION)
    validation = load_json(validation_path)
    normalized = next(
        item["kiwoom_record"] for item in validation["latest_validation"]
        if item.get("ticker") == "NBIS"
    )
    if Decimal(str(bar["close"])) != Decimal("255.84"):
        raise ValueError("KIWOOM_EXPECTED_RAW_CLOSE_NOT_FOUND")
    if Decimal(str(normalized["price"])) != Decimal(str(bar["close"])):
        raise ValueError("KIWOOM_NORMALIZED_AND_RAW_CLOSE_MISMATCH")
    if ticker.get("status") != "PASS" or raw.get("status") != "PASS" or raw.get("validation_errors"):
        raise ValueError("KIWOOM_RAW_SELF_INTEGRITY_FAILED")
    return ticker, normalized, snapshot_path


def _yfinance_close(root: Path) -> tuple[float, Path]:
    path = root / "workspace/outputs/portfolio-strategy/2026-08-13/yfinance_replay_evidence.json"
    record = load_json(path)["records"]["NBIS"]
    if record.get("status") != "PRIMARY_VALIDATED" or record.get("completed_session") != MARKET_SESSION:
        raise ValueError("YFINANCE_DIAGNOSTIC_REFERENCE_INVALID")
    bar = next(item for item in record["bars"] if item.get("session") == MARKET_SESSION)
    return float(bar["close"]), path


def build_price_authority(root: Path, generated_at: str) -> dict[str, Any]:
    ticker, normalized, snapshot_path = _find_kiwoom_finalized_record(root)
    yfinance, yfinance_path = _yfinance_close(root)
    issuer_path = root / "workspace/research/price-evidence/2026-08-13/nbis-official-stock-page-raw-v3.json"
    issuer = load_json(issuer_path)
    raw_page = ticker["raw"]["pagination"]["pages"][0]
    record = {
        "ticker": "NBIS",
        "requested_ticker": "NBIS",
        "security_identity": "Nebius Group N.V. (NASDAQ:NBIS)",
        "security_identity_status": "VERIFIED",
        "currency": "USD",
        "fx_applied": False,
        "canonical_price": float(ticker["raw"]["completed_close"]),
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
        "retrieval_timestamp": snapshot["generated_at"] if (snapshot := load_json(snapshot_path)) else raw_page["retrieved_at"],
        "retrieval_market_phase": "MARKET_CLOSED_ARCHIVED_DAILY_QUERY",
        "request_parameters": {
            "stex_tp": ticker["identity"]["stex_tp"],
            "stk_cd": "NBIS",
            "strt_dt": MARKET_SESSION.replace("-", ""),
            "upd_stkpc_tp": "0",
            "exrt_appl_tp": "0",
        },
        "bar_finalized": normalized["bar_finalized"],
        "stale_record": False,
        "corporate_action_ambiguity": False,
        "scale_error": False,
    }
    result = build_us_stock_price_authority(
        record,
        yfinance_reference=yfinance,
        external_reference=255.04,
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        generated_at=generated_at,
    )
    result["source_provenance"] = {
        "kiwoom_snapshot_path": snapshot_path.relative_to(root).as_posix(),
        "kiwoom_snapshot_sha256": file_hash(snapshot_path),
        "kiwoom_identity_api_id": ticker["identity"]["source_api_id"],
        "kiwoom_runtime_commit": ticker["identity"]["official_runtime_commit"],
        "kiwoom_daily_chart_official_example": "E:/\uc0ac\uc5c5/##\uae08\ub3d9\ud55c/runtime/Kiwoom-REST-API/examples/\ubbf8\uad6d\uc8fc\uc2dd/\ucc28\ud2b8/get_overseas_stock_daily_chart.py",
        "kiwoom_daily_chart_official_example_sha256": file_hash(Path("E:/\uc0ac\uc5c5/##\uae08\ub3d9\ud55c/runtime/Kiwoom-REST-API/examples/\ubbf8\uad6d\uc8fc\uc2dd/\ucc28\ud2b8/get_overseas_stock_daily_chart.py")),
        "yfinance_path": yfinance_path.relative_to(root).as_posix(),
        "yfinance_sha256": file_hash(yfinance_path),
        "issuer_path": issuer_path.relative_to(root).as_posix(),
        "issuer_sha256": file_hash(issuer_path),
        "issuer_source_url": issuer["source_page_url"],
    }
    result["evidence_hash"] = canonical_hash(without_hash(result, "evidence_hash"))
    return result


def _scenario(
    scenario_id: str, scenario_type: str, shares_millions: Decimal,
    price: Decimal, debt_billions: Decimal, cash_billions: Decimal,
    assumptions: list[str], convertible_shares: bool, convertible_debt: bool,
) -> dict[str, Any]:
    if convertible_shares and convertible_debt:
        raise ValueError("CONVERTIBLE_DOUBLE_COUNT")
    equity = shares_millions * price / Decimal("1000")
    enterprise = equity + debt_billions - cash_billions
    methods = []
    for method, denominator in (("EV_TO_LTM_REVENUE", Decimal("1.3551")),
                                ("EV_TO_RECOGNIZED_REVENUE_RUN_RATE", Decimal("2.3292"))):
        methods.append({
            "method": method, "value": float(enterprise / denominator),
            "unit": "MULTIPLE", "status": "EVALUATED",
            "formula": f"{enterprise} / {denominator}",
        })
    return {
        "scenario_id": scenario_id, "scenario_type": scenario_type,
        "share_basis": float(shares_millions),
        "equity_value": float(equity * Decimal("1000")),
        "enterprise_value": float(enterprise * Decimal("1000")),
        "valuation_methods": methods, "assumption_ids": assumptions,
        "status": "EVALUATED",
        "formula_trace": {
            "shares_millions": str(shares_millions), "price_usd": str(price),
            "debt_billions": str(debt_billions), "cash_billions": str(cash_billions),
            "enterprise_value_billions": str(enterprise),
        },
        "convertible_share_equivalent_included": convertible_shares,
        "convertible_debt_included": convertible_debt,
    }


def build_valuation(
    root: Path, price_authority: dict[str, Any], capital: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    prior = load_json(root / "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v3.json")
    price = Decimal(str(price_authority["canonical_price"]))
    legal = Decimal(str(capital["legal_ordinary_shares"])) / Decimal("1000000")
    economic = Decimal(str(capital["economic_basic_shares"])) / Decimal("1000000")
    convertible = Decimal(str(capital["point_in_time_initial_rate_convertible_equivalent"])) / Decimal("1000000")
    gross = Decimal(str(capital["initial_rate_known_gross_stress_case"])) / Decimal("1000000")
    cash = Decimal("8.0421")
    nonconvertible_debt = Decimal("0.0467")
    carrying_convertible = Decimal("8.499")
    accreted_convertible = Decimal("10.0418")
    scenarios = [
        _scenario("LEGAL_BASIC_CARRYING_DEBT_CASE", "BASIC", legal, price,
                  nonconvertible_debt + carrying_convertible, cash,
                  ["LEGAL_ORDINARY_SHARES", "CONVERTIBLE_CARRYING_DEBT"], False, True),
        _scenario("ECONOMIC_BASIC_CARRYING_DEBT_CASE", "BASE_DILUTED", economic, price,
                  nonconvertible_debt + carrying_convertible, cash,
                  ["PREFUNDED_WARRANTS_ECONOMIC_BASIC", "CONVERTIBLE_CARRYING_DEBT"], False, True),
        _scenario("CONVERTIBLE_SHARE_SETTLEMENT_CASE", "BASE_DILUTED", economic + convertible, price,
                  nonconvertible_debt, cash,
                  ["INITIAL_RATE_SHARE_SETTLEMENT", "NO_CONVERTIBLE_DEBT_DOUBLE_COUNT"], True, False),
        _scenario("CONVERTIBLE_CASH_SETTLEMENT_CASE", "BASE_DILUTED", economic, price,
                  nonconvertible_debt + accreted_convertible, cash,
                  ["ACCRETED_CASH_SETTLEMENT", "NO_CONVERTIBLE_SHARE_DOUBLE_COUNT"], False, True),
        _scenario("INITIAL_RATE_KNOWN_GROSS_STRESS_CASE", "STRESS_DILUTED", gross, price,
                  nonconvertible_debt, cash,
                  ["KNOWN_INITIAL_RATE_SHARES", "OPTIONS", "RSUS", "ATM", "UNQUANTIFIED_TAIL_EXCLUDED"], True, False),
    ]
    value = deepcopy(prior)
    value.update({
        "valuation_snapshot_id": "nbis-valuation-20260813-v4",
        "analysis_cutoff": generated_at,
        "price": {
            "provider": "KIWOOM_REST",
            "canonical_provider": "KIWOOM_REST",
            "provider_role": "OPERATIONAL_EXECUTION_PRIMARY",
            "raw_regular_session_close": float(price),
            "price_basis": "RAW_REGULAR_SESSION_CLOSE",
            "market_session_type": "REGULAR_COMPLETED",
            "reported_session": MARKET_SESSION,
            "bar_finalized": True,
            "price_semantics": "COMPLETED_DAILY_CLOSE",
            "market_phase": "COMPLETED_DAILY",
            "source_api_id": "usa06012",
            "source_field": "result_list.cur_prc",
            "self_integrity_status": "KIWOOM_PRICE_VALIDATED",
            "comparison_status": "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE",
            "yfinance_reference_price": price_authority["diagnostics"]["yfinance_reference_price"],
            "external_reference_price": price_authority["diagnostics"]["external_reference_price"],
            "cross_provider_difference_abs": price_authority["diagnostics"]["cross_provider_difference_abs"],
            "cross_provider_difference_pct": price_authority["diagnostics"]["cross_provider_difference_pct"],
            "divergence_blocking": False,
            "blocking": False,
            "price_authority_evidence_hash": price_authority["evidence_hash"],
        },
        "valuation_scenarios": scenarios,
        "derived_values": {
            "scenario_market_caps_usd_millions": {item["scenario_id"]: item["equity_value"] for item in scenarios},
            "scenario_enterprise_values_usd_millions": {item["scenario_id"]: item["enterprise_value"] for item in scenarios},
            "facility_net_ev_effect_formula": "draw - retained_cash",
            "facility_base_case_draw_assumed": False,
            "currency": "USD", "unit": "USD_MILLIONS_UNLESS_EXPLICIT",
        },
        "required_missing_inputs": [],
        "calculation_formula_version": "nbis-settlement-aware-v4-kiwoom-primary",
        "staleness_status": "FRESH",
        "valuation_evidence_status": "DIRECT_SCENARIO_VALIDATED",
        "valuation_judgement_status": "UNCLASSIFIED",
        "snapshot_hash": "0" * 64,
        "order_authority": False,
    })
    value["claim_ids"] = sorted(set(value["claim_ids"] + ["nbis-v4-kiwoom-price-authority"]))
    value["evidence_ids"] = sorted(set(value["evidence_ids"] + ["nbis-price-authority-v4"]))
    value["snapshot_hash"] = canonical_hash(without_hash(value, "snapshot_hash"))
    return value


def build_baseline(root: Path, component_paths: dict[str, Path], generated_at: str) -> dict[str, Any]:
    prior = load_json(root / "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v3.json")
    value = deepcopy(prior)
    value.update({
        "baseline_id": "nbis-20260814-v4", "baseline_version": 4,
        "analysis_cutoff": generated_at, "evidence_cutoff": generated_at,
        "content_status": "COMPLETE", "valuation_status": "UNCLASSIFIED",
        "supersedes_baseline_id": prior["baseline_id"],
        "supersedes_baseline_hash": prior["baseline_hash"],
        "validation_status": "DRAFT",
    })
    value["claims"] = [item for item in value["claims"] if item.get("claim_id") != "nbis-v3-price-claim"]
    value["evidence"] = [item for item in value["evidence"] if item.get("evidence_id") != "nbis-v3-price"]
    value["evidence"].append({
        "evidence_id": "nbis-v4-kiwoom-price",
        "source_url": "https://github.com/Kiwoom-Securities/Kiwoom-REST-API/blob/69642586f7d84ba9fd8a6faf1f1537c7fda6568b/examples/%EB%AF%B8%EA%B5%AD%EC%A3%BC%EC%8B%9D/%EC%B0%A8%ED%8A%B8/get_overseas_stock_daily_chart.py",
        "source_type": "KIWOOM_REST_OPERATIONAL_PRIMARY", "published_at": "2026-08-13T20:00:00Z",
        "retrieved_at": generated_at, "effective_at": "2026-08-13T20:00:00Z",
        "point_in_time_eligible": True,
        "normalized_field": "NBIS usa06012 Raw completed daily close USD 255.84; yfinance and issuer divergence retained as non-blocking diagnostics",
        "verification_status": "VERIFIED",
    })
    value["claims"].append({
        "claim_id": "nbis-v4-kiwoom-price-claim",
        "claim": "Kiwoom usa06012 Raw daily row for 2026-08-13 is the canonical NBIS valuation and Shadow-activation price at USD 255.84; external divergence is diagnostic and non-blocking.",
        "evidence_ids": ["nbis-v4-kiwoom-price"],
    })
    value["claim_ids"] = [item["claim_id"] for item in value["claims"]]
    value["evidence_ids"] = [item["evidence_id"] for item in value["evidence"]]
    value["linked_components"] = [
        {"component_type": name, "path": path.relative_to(root).as_posix(),
         "file_hash": file_hash(path), "product_close_substitution": False}
        for name, path in component_paths.items()
    ]
    return recompute_hashes(value)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_root = root / "workspace/research/nbis-shadow-activation/2026-08-13/v4"
    price_path = output_root / "nbis-price-authority-v4.json"
    valuation_path = root / "workspace/research/valuation-snapshots/2026-08-13/nbis-valuation-snapshot-v4.json"
    baseline_path = root / "workspace/research/holding-baseline-candidates/2026-08-14/nbis-20260814-v4.json"
    event_link_path = root / "workspace/research/baseline-event-links/2026-08-13/v4/nbis-issuer-event-link.json"
    overlay_path = root / "workspace/research/holding-overlays/2026-08-13/nbis-overlay-v4.json"
    compile_path = root / "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v4.json"
    build_manifest_path = root / "workspace/outputs/activation/nbis-v2-shadow/20260814-v4/build-manifest.json"
    portfolio_path = root / "stock-strategy-system/portfolio_state.json"
    policy_path = root / "workspace/policies/holding_research_baseline_policy.json"
    provider_path = root / "workspace/policies/kiwoom-session-aware-priority-policy.json"
    event_path = root / "workspace/research/nbis-shadow-activation/2026-08-13/v3/nbis-event-review-bundle-v3.json"
    capital_path = root / "workspace/research/nbis-shadow-activation/2026-08-13/v3/nbis-capital-structure-v3.json"
    generated_at = load_json(price_path)["generated_at"] if price_path.exists() else utc_now()
    protected_before = {str(path.relative_to(root)): file_hash(path) for path in
                        (portfolio_path, policy_path, provider_path,
                         root / "workspace/state/holding_strategy_runtime.json")}

    capital = load_json(capital_path)
    if capital.get("validation_status") != "VALIDATED" or not all(capital.get("validation_checks", {}).values()):
        raise ValueError("CAPITAL_STRUCTURE_V3_REVALIDATION_FAILED")
    if capital.get("record_hash") != canonical_hash(without_hash(capital, "record_hash")):
        raise ValueError("CAPITAL_STRUCTURE_V3_HASH_MISMATCH")
    event_bundle = load_json(event_path)
    if event_bundle.get("bundle_status") != "COMPLETE" or event_bundle.get("coverage_status") != "COMPLETE_FOR_REQUIRED_CATEGORIES":
        raise ValueError("EVENT_BUNDLE_V3_NOT_COMPLETE")

    price = build_price_authority(root, generated_at)
    write_json(price_path, price)
    price_errors = validate_instance(price, root / "manage-us-stock-strategy/schemas/us-stock-price-authority.schema.json")
    price_errors.extend(validate_price_authority_artifact(price))
    valuation = build_valuation(root, price, capital, generated_at)
    write_json(valuation_path, valuation)
    valuation_validation = validate_valuation_snapshot(
        valuation, root / "manage-us-stock-strategy/schemas/issuer-valuation-snapshot.schema.json")
    baseline = build_baseline(root, {
        "PRICE_AUTHORITY": price_path, "CAPITAL_STRUCTURE": capital_path,
        "VALUATION_SNAPSHOT": valuation_path, "EVENT_REVIEW": event_path,
    }, generated_at)
    write_json(baseline_path, baseline)
    baseline_validation = validate_baseline(
        baseline, root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json")
    event_link = build_baseline_event_link(
        baseline, event_bundle, event_bundle_path=event_path, ticker="NBIS",
        entity_role="DIRECT_ISSUER", link_created_at=generated_at)
    write_json(event_link_path, event_link)
    event_validation = validate_event_link(
        event_link, schema_path=root / "manage-us-stock-strategy/schemas/baseline-event-link.schema.json",
        baseline=baseline, event_bundle_path=event_path)
    overlay = deepcopy(load_json(root / "workspace/research/holding-overlays/2026-08-13/nbis-overlay-v3.json"))
    overlay.update({
        "primary_price_status": "VALIDATED",
        "independent_price_status": "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE_NONBLOCKING",
        "price_evidence_id": "nbis-20260813-kiwoom-price-authority-v4",
        "price_evidence_hash": price["evidence_hash"], "overlay_hash": "0" * 64,
    })
    overlay["overlay_hash"] = canonical_hash(without_hash(overlay, "overlay_hash"))
    write_json(overlay_path, overlay)
    prior_compile = load_json(root / "workspace/research/shadow-compiles/2026-08-13/nbis-shadow-compile-v3.json")
    compiled = compile_shadow(
        baseline=baseline, valuation=valuation, event_link=event_link, overlay=overlay,
        portfolio=load_json(portfolio_path), policy_path=policy_path,
        provider_scope_path=provider_path, portfolio_path=portfolio_path,
        baseline_schema=root / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",
        live_strategy_state=prior_compile["live_strategy_state"], blocked_decision_classes=[])
    write_json(compile_path, compiled)
    compile_schema_errors = validate_instance(
        compiled, root / "manage-us-stock-strategy/schemas/shadow-baseline-compile-result.schema.json")
    protected_after = {str(path.relative_to(root)): file_hash(path) for path in
                       (portfolio_path, policy_path, provider_path,
                        root / "workspace/state/holding_strategy_runtime.json")}
    gates = {
        "kiwoom_price_authority": not price_errors and price["price_evidence_status"] == "VALID",
        "capital_structure_reused_and_validated": True,
        "valuation": valuation_validation["validation_status"] == "PASSED",
        "event_link": event_validation["validation_status"] == "PASSED" and event_link["link_validation_status"] in {"VALID", "PARTIAL_NONBLOCKING"},
        "baseline": baseline_validation["validation_status"] == "PASSED" and baseline["content_status"] == "COMPLETE",
        "shadow_compile": not compile_schema_errors and compiled["shadow_compile_status"] == "PASSED" and not compiled["remaining_conditions"],
        "authority_boundary": compiled["quantity"] is None and compiled["quantity_authority"] == "none" and compiled["order_authority"] is False,
        "protected_inputs_unchanged": protected_before == protected_after,
    }
    manifest = {
        "schema_version": "1.0", "ticker": "NBIS", "generated_at": generated_at,
        "market_session": MARKET_SESSION, "gates": gates,
        "validator_results": {"price": price_errors, "valuation": valuation_validation,
                              "baseline": baseline_validation, "event_link": event_validation,
                              "compile_schema_errors": compile_schema_errors},
        "artifacts": {path.relative_to(root).as_posix(): file_hash(path) for path in
                      (price_path, capital_path, event_path, valuation_path, baseline_path,
                       event_link_path, overlay_path, compile_path)},
        "protected_before": protected_before, "protected_after": protected_after,
        "activation_attempted": False, "quantity": None,
        "quantity_authority": "none", "order_authority": False,
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    write_json(build_manifest_path, manifest)
    print(json.dumps({"status": "NBIS_V4_SHADOW_COMPILE_READY" if all(gates.values()) else "NBIS_V4_BUILD_BLOCKED",
                      "gates": gates, "manifest": build_manifest_path.relative_to(root).as_posix()}, ensure_ascii=False))
    return 0 if all(gates.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
