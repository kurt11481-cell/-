#!/usr/bin/env python3
"""Deterministic v2.6.12 valuation, event-link, Shadow compile, and observation gates.

This module is research-only.  It never supplies quantity or order authority and
never writes the canonical portfolio state.
"""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from holding_research import validate_baseline, validate_overlay_hash
from validation_common import canonical_hash, file_hash, parse_datetime, validate_instance


FORMULA_VERSION = "holding-valuation-v2.6.12-1"
VALUATION_NUMERIC_SECTIONS = ("capitalization", "balance_sheet", "operating_metrics")
VALID_EVENT_LINKS = {"VALID", "PARTIAL_NONBLOCKING"}
VALID_VALUATION_EVIDENCE = {"SCENARIO_VALIDATED", "DIRECT_SCENARIO_VALIDATED", "NOT_APPLICABLE"}


def validate_managed_output_path(output: Path, *, repo_root: Path,
                                 allowed_relative_root: str,
                                 protected: list[Path] | None = None) -> Path:
    """Require a write target to remain inside one managed artifact directory."""
    target = output.resolve()
    allowed = (repo_root / allowed_relative_root).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise ValueError(f"OUTPUT_OUTSIDE_ALLOWED_ROOT:{allowed_relative_root}") from exc
    protected_paths = {
        (repo_root / "stock-strategy-system/portfolio_state.json").resolve(),
        (repo_root / "stock-strategy-system/alert_policy.json").resolve(),
        (repo_root / "workspace/policies/instrument_registry.json").resolve(),
        (repo_root / "workspace/policies/source_capabilities.json").resolve(),
    }
    protected_paths.update(path.resolve() for path in (protected or []))
    if target in protected_paths:
        raise ValueError("OUTPUT_PATH_ALIASES_PROTECTED_INPUT")
    return target


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
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


def _without_hash(record: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != field}


def _metric(value: float | int | None, *, unit: str, as_of: str, evidence_id: str,
            currency: str | None = None, status: str = "VERIFIED") -> dict[str, Any]:
    return {
        "value": value,
        "currency": currency,
        "unit": unit,
        "as_of": as_of,
        "source_evidence_id": evidence_id,
        "verification_status": status,
    }


def _metric_value(section: dict[str, Any], name: str) -> float | None:
    item = section.get(name)
    if not isinstance(item, dict) or not isinstance(item.get("value"), (int, float)):
        return None
    return float(item["value"])


def _scenario(scenario_id: str, kind: str, shares: float | None, close: float | None,
              cash: float | None, debt: float | None, preferred_claims: float | None,
              other_claims: float | None, methods: list[dict[str, Any]],
              assumptions: list[str]) -> dict[str, Any]:
    if shares is None or close is None:
        return {"scenario_id": scenario_id, "scenario_type": kind, "share_basis": shares,
                "equity_value": None, "enterprise_value": None, "valuation_methods": [],
                "assumption_ids": assumptions, "status": "INCOMPLETE"}
    equity = shares * close
    if None in (cash, debt, preferred_claims, other_claims):
        enterprise = None
        status = "INCOMPLETE"
    else:
        enterprise = equity + float(debt) + float(preferred_claims) + float(other_claims) - float(cash)
        status = "EVALUATED"
    scenario_methods: list[dict[str, Any]] = []
    for method in methods:
        denominator = method.get("denominator")
        value = None if enterprise is None or not isinstance(denominator, (int, float)) or denominator <= 0 else enterprise / float(denominator)
        scenario_methods.append({
            "method": method["method"], "value": value, "unit": method["unit"],
            "status": "EVALUATED" if value is not None else "NOT_EVALUATED",
            "denominator_evidence_id": method.get("denominator_evidence_id"),
        })
    return {"scenario_id": scenario_id, "scenario_type": kind, "share_basis": shares,
            "equity_value": equity, "enterprise_value": enterprise,
            "valuation_methods": scenario_methods, "assumption_ids": assumptions,
            "status": status}


def build_issuer_valuation_snapshot(spec: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic snapshot from a source-normalized, point-in-time spec."""
    price = deepcopy(spec["price"])
    close = price.get("raw_regular_session_close")
    capitalization = deepcopy(spec["capitalization"])
    balance = deepcopy(spec["balance_sheet"])
    metrics = deepcopy(spec["operating_metrics"])
    basic = _metric_value(capitalization, "basic_shares")
    diluted_base = _metric_value(capitalization, "diluted_shares_base")
    diluted_stress = _metric_value(capitalization, "diluted_shares_stress")
    cash = _metric_value(balance, "cash")
    debt = _metric_value(balance, "debt")
    preferred = _metric_value(balance, "preferred_claims")
    other_claims = _metric_value(balance, "other_claims")
    revenue_ltm = _metric_value(metrics, "revenue_ltm")
    run_rate = _metric_value(metrics, "annualized_revenue_run_rate")
    method_specs: list[dict[str, Any]] = []
    if revenue_ltm:
        method_specs.append({"method": "EV_TO_LTM_REVENUE", "denominator": revenue_ltm,
                             "unit": "MULTIPLE", "denominator_evidence_id": metrics["revenue_ltm"]["source_evidence_id"]})
    if run_rate:
        method_specs.append({"method": "EV_TO_ANNUALIZED_REVENUE_RUN_RATE", "denominator": run_rate,
                             "unit": "MULTIPLE", "denominator_evidence_id": metrics["annualized_revenue_run_rate"]["source_evidence_id"]})
    stress_debt = spec.get("stress_debt", debt)
    stress_preferred = spec.get("stress_preferred_claims", preferred)
    scenarios = [
        _scenario(f"{spec['ticker']}-basic", "BASIC", basic, close, cash, debt, preferred, other_claims,
                  method_specs, ["BASIC_SHARES_ONLY"]),
        _scenario(f"{spec['ticker']}-base-diluted", "BASE_DILUTED", diluted_base, close, cash, debt,
                  preferred, other_claims, method_specs, spec.get("base_assumption_ids", [])),
        _scenario(f"{spec['ticker']}-stress-diluted", "STRESS_DILUTED", diluted_stress, close, cash, stress_debt,
                  stress_preferred, other_claims, method_specs, spec.get("stress_assumption_ids", [])),
    ]
    required_missing = list(spec.get("required_missing_inputs", []))
    constitution_price_authority = (
        price.get("canonical_provider") == "KIWOOM_REST"
        and isinstance(price.get("price_authority_evidence_hash"), str)
    )
    kiwoom_self_integrity_valid = (
        price.get("self_integrity_status") == "KIWOOM_PRICE_VALIDATED"
        and price.get("divergence_blocking") is False
        and price.get("blocking") is False
    )
    price_valid = (
        price.get("provider") == "KIWOOM_REST"
        and price.get("price_basis") == "RAW_REGULAR_SESSION_CLOSE"
        and price.get("market_session_type") == "REGULAR_COMPLETED"
        and price.get("reported_session") == spec.get("market_session")
        and price.get("bar_finalized") is True
        and isinstance(close, (int, float)) and close > 0
        and (kiwoom_self_integrity_valid if constitution_price_authority
             else price.get("comparison_status") != "CONFLICT")
    )
    scenario_complete = all(item["status"] == "EVALUATED" for item in scenarios)
    if not price_valid:
        evidence_status = ("PRICE_EVIDENCE_CONFLICT"
                           if price.get("comparison_status") == "CONFLICT" and not constitution_price_authority
                           else "INVALID")
    elif required_missing:
        evidence_status = "PARTIAL"
    elif scenario_complete:
        evidence_status = "SCENARIO_VALIDATED"
    else:
        evidence_status = "PARTIAL"
    judgment = spec.get("valuation_judgement_status", "UNCLASSIFIED")
    if evidence_status in {"PRICE_EVIDENCE_CONFLICT", "INVALID", "STALE"}:
        judgment = "UNVERIFIED"
    if judgment not in {"UNCLASSIFIED", "UNVERIFIED", "NOT_APPLICABLE"}:
        judgment = "UNVERIFIED"
    result = {
        "schema_version": "2.6.12",
        "valuation_snapshot_id": spec["valuation_snapshot_id"], "ticker": spec["ticker"],
        "issuer_name": spec["issuer_name"], "entity_role": spec["entity_role"],
        "analysis_cutoff": spec["analysis_cutoff"], "market_session": spec["market_session"],
        "price": price, "capitalization": capitalization, "balance_sheet": balance,
        "operating_metrics": metrics,
        "derived_values": {
            "equity_value_basic": scenarios[0]["equity_value"],
            "equity_value_diluted_base": scenarios[1]["equity_value"],
            "equity_value_diluted_stress": scenarios[2]["equity_value"],
            "enterprise_value_basic": scenarios[0]["enterprise_value"],
            "enterprise_value_base": scenarios[1]["enterprise_value"],
            "enterprise_value_stress": scenarios[2]["enterprise_value"],
            "currency": "USD", "unit": "USD_MILLIONS",
        },
        "valuation_methods": sorted({item["method"] for item in method_specs}) and [
            {"method": item["method"], "status": "EVALUATED", "judgement_authority": "NONE"}
            for item in method_specs
        ] or [{"method": "NOT_EVALUATED", "status": "NOT_EVALUATED", "judgement_authority": "NONE"}],
        "valuation_scenarios": scenarios,
        "claim_ids": list(spec["claim_ids"]), "evidence_ids": list(spec["evidence_ids"]),
        "required_missing_inputs": required_missing,
        "calculation_formula_version": FORMULA_VERSION,
        "staleness_status": "FRESH" if price_valid else "INVALID",
        "staleness_triggers": list(spec["staleness_triggers"]),
        "valuation_evidence_status": evidence_status,
        "valuation_judgement_status": judgment,
        "snapshot_hash": "0" * 64, "order_authority": False,
    }
    result["snapshot_hash"] = canonical_hash(_without_hash(result, "snapshot_hash"))
    return result


def validate_valuation_snapshot(record: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    errors = validate_instance(record, schema_path)
    price = record.get("price") if isinstance(record.get("price"), dict) else {}
    provider = price.get("provider")
    kiwoom_observation = price.get("kiwoom_observation")
    kiwoom_scope_explicit = isinstance(kiwoom_observation, dict) and (
        (
            kiwoom_observation.get("disposition") == "REJECTED_NOT_COMPARABLE_SESSION"
            and kiwoom_observation.get("market_session_type") != "REGULAR_COMPLETED"
            and kiwoom_observation.get("comparable_to_regular_close") is False
        )
        or (
            kiwoom_observation.get("disposition") == "PRESERVED_SAME_SESSION_CONFLICT"
            and kiwoom_observation.get("market_session_type") == "REGULAR_COMPLETED"
            and kiwoom_observation.get("comparable_to_regular_close") is True
        )
    )
    original_source_resolution = (
        provider == "INFRONT_VIA_NEBIUS_IR"
        and price.get("provider_role") == "ORIGINAL_SOURCE_COMPLETED_CLOSE_VALIDATION"
        and price.get("original_source_validation_status") == "VALIDATED"
        and price.get("yfinance_raw_close_status") == "MATCH_AFTER_DISPLAY_QUANTIZATION"
        and kiwoom_scope_explicit
    )
    if provider != "KIWOOM_REST" and not original_source_resolution:
        errors.append("PRICE_PROVIDER_NOT_APPROVED_FOR_VALUATION")
    if price.get("price_basis") != "RAW_REGULAR_SESSION_CLOSE": errors.append("PRICE_BASIS_NOT_RAW_REGULAR_CLOSE")
    if price.get("market_session_type") != "REGULAR_COMPLETED": errors.append("PRICE_SESSION_NOT_REGULAR_COMPLETED")
    if price.get("bar_finalized") is not True: errors.append("PRICE_BAR_NOT_FINALIZED")
    if price.get("reported_session") != record.get("market_session"): errors.append("PRICE_SESSION_MISMATCH")
    constitution_price_authority = (
        provider == "KIWOOM_REST"
        and isinstance(price.get("price_authority_evidence_hash"), str)
    )
    kiwoom_valid = (
        provider == "KIWOOM_REST"
        and price.get("self_integrity_status") == "KIWOOM_PRICE_VALIDATED"
        and price.get("divergence_blocking") is False
        and price.get("blocking") is False
    )
    if constitution_price_authority and not kiwoom_valid:
        errors.append("KIWOOM_SELF_INTEGRITY_NOT_VALIDATED")
    if price.get("comparison_status") == "CONFLICT" and not constitution_price_authority:
        errors.append("PRICE_EVIDENCE_CONFLICT")
    for section_name in VALUATION_NUMERIC_SECTIONS:
        section = record.get(section_name)
        if not isinstance(section, dict):
            errors.append(f"{section_name.upper()}_MISSING")
            continue
        for name, item in section.items():
            if isinstance(item, dict) and "value" in item:
                for field in ("unit", "as_of", "source_evidence_id", "verification_status"):
                    if not item.get(field): errors.append(f"METRIC_METADATA_MISSING:{section_name}:{name}:{field}")
                try: date.fromisoformat(str(item.get("as_of")))
                except ValueError: errors.append(f"METRIC_AS_OF_INVALID:{section_name}:{name}")
    local_hash = canonical_hash(_without_hash(record, "snapshot_hash"))
    if record.get("snapshot_hash") != local_hash: errors.append("SNAPSHOT_HASH_MISMATCH")
    if record.get("order_authority") is not False: errors.append("ORDER_AUTHORITY_PROHIBITED")
    return {"validation_status": "PASSED" if not errors else "FAILED", "errors": list(dict.fromkeys(errors)),
            "locally_computed_snapshot_hash": local_hash, "order_authority": False}


def build_baseline_event_link(baseline: dict[str, Any], event_bundle: dict[str, Any], *,
                              event_bundle_path: Path, ticker: str, entity_role: str,
                              link_created_at: str) -> dict[str, Any]:
    coverage = next((row for row in event_bundle.get("ticker_coverage", []) if row.get("ticker") == ticker), None)
    if coverage is None:
        coverage_status, event_effect, link_status = "UNAVAILABLE", "INVALID", "MISSING"
    else:
        coverage_status = coverage.get("coverage_status", "INVALID")
        event_effect = coverage.get("event_effect", "INVALID")
        if event_effect == "EVENT_REVIEW_REQUIRED":
            event_effect = "EVENT_REVIEW_PENDING"
        if coverage_status == "PARTIAL_NONBLOCKING" and event_effect == "CONTEXT_ONLY":
            link_status = "PARTIAL_NONBLOCKING"
        elif coverage_status == "COMPLETE" and event_effect in {"CONTEXT_ONLY", "CLEAR"}:
            link_status = "VALID"
        elif coverage_status in {"PARTIAL_BLOCKING", "EVENT_REVIEW_REQUIRED"}:
            link_status = "EVENT_REVIEW_PENDING"
        else:
            link_status = "INVALID"
    result = {
        "schema_version": "2.6.12", "baseline_event_link_id": f"{baseline['baseline_id']}--{ticker}--{event_bundle['bundle_id']}",
        "ticker": ticker, "entity_role": entity_role, "baseline_id": baseline["baseline_id"],
        "baseline_hash": baseline["baseline_hash"], "event_bundle_id": event_bundle["bundle_id"],
        "event_bundle_hash": file_hash(event_bundle_path), "event_coverage_status": coverage_status,
        "event_effect": event_effect if event_effect in {"CONTEXT_ONLY", "EVENT_REVIEW_PENDING", "WAIT_REQUIRED", "INVALID"} else "INVALID",
        "analysis_cutoff": event_bundle["analysis_cutoff"], "link_created_at": link_created_at,
        "link_validation_status": link_status, "link_hash": "0" * 64, "order_authority": False,
    }
    result["link_hash"] = canonical_hash(_without_hash(result, "link_hash"))
    return result


def validate_event_link(record: dict[str, Any], *, schema_path: Path, baseline: dict[str, Any],
                        event_bundle_path: Path) -> dict[str, Any]:
    errors = validate_instance(record, schema_path)
    if record.get("baseline_hash") != baseline.get("baseline_hash"): errors.append("BASELINE_HASH_MISMATCH")
    if record.get("event_bundle_hash") != file_hash(event_bundle_path): errors.append("EVENT_BUNDLE_HASH_MISMATCH")
    local = canonical_hash(_without_hash(record, "link_hash"))
    if record.get("link_hash") != local: errors.append("LINK_HASH_MISMATCH")
    return {"validation_status": "PASSED" if not errors else "FAILED", "errors": list(dict.fromkeys(errors)),
            "locally_computed_link_hash": local, "order_authority": False}


def compile_shadow(*, baseline: dict[str, Any], valuation: dict[str, Any] | None,
                   event_link: dict[str, Any], overlay: dict[str, Any], portfolio: dict[str, Any],
                   policy_path: Path, provider_scope_path: Path, portfolio_path: Path,
                   baseline_schema: Path, live_strategy_state: str,
                   blocked_decision_classes: list[str] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    baseline_validation = validate_baseline(baseline, baseline_schema)
    if baseline_validation["validation_status"] != "PASSED": errors.extend(baseline_validation["errors"])
    if not validate_overlay_hash(overlay): errors.append("OVERLAY_HASH_INVALID")
    if any(item.get("ticker") != baseline.get("ticker") for item in (overlay, event_link)): errors.append("TICKER_IDENTITY_MISMATCH")
    if event_link.get("baseline_hash") != baseline.get("baseline_hash"): errors.append("EVENT_LINK_BASELINE_HASH_MISMATCH")
    if event_link.get("link_hash") != canonical_hash(_without_hash(event_link, "link_hash")): errors.append("EVENT_LINK_HASH_MISMATCH")
    if valuation and valuation.get("snapshot_hash") != canonical_hash(_without_hash(valuation, "snapshot_hash")):
        errors.append("VALUATION_SNAPSHOT_HASH_MISMATCH")
    for component in baseline.get("linked_components") or []:
        if component.get("product_close_substitution") is not False:
            errors.append("SUPPLEMENTAL_PRICE_SUBSTITUTION_PROHIBITED")
    evidence_status = "NOT_APPLICABLE" if baseline.get("valuation_applicability") == "NOT_APPLICABLE_TO_PRODUCT" else (
        valuation.get("valuation_evidence_status") if valuation else "UNVERIFIED")
    judgement_status = "NOT_APPLICABLE" if baseline.get("valuation_applicability") == "NOT_APPLICABLE_TO_PRODUCT" else (
        valuation.get("valuation_judgement_status") if valuation else "UNVERIFIED")
    remaining: list[str] = []
    if baseline.get("content_status") != "COMPLETE": remaining.append("BASELINE_CONTENT_INCOMPLETE")
    if evidence_status not in VALID_VALUATION_EVIDENCE: remaining.append("VALUATION_EVIDENCE_NOT_VALIDATED")
    if event_link.get("link_validation_status") not in VALID_EVENT_LINKS: remaining.append("EVENT_LINK_NOT_ACTIVATABLE")
    if overlay.get("primary_price_status") != "VALIDATED": remaining.append("PRIMARY_PRICE_NOT_VALIDATED")
    if errors: remaining.extend(errors)
    hard_risk = overlay.get("hard_risk_observation") == "PRIMARY_BREACH_OBSERVED"
    signal, state = "NONE", "HOLD"
    if baseline.get("content_status") != "COMPLETE" or evidence_status not in VALID_VALUATION_EVIDENCE:
        state = "STRATEGY_REFRESH_REQUIRED"
    elif errors or overlay.get("primary_price_status") != "VALIDATED":
        state = "DATA_BLOCKED"
    elif event_link.get("link_validation_status") not in VALID_EVENT_LINKS:
        state = "STRATEGY_REFRESH_REQUIRED"
    elif hard_risk:
        action = ((overlay.get("deterministic_existing_policy") or {}).get("action_on_breach"))
        if action == "exit_review": signal, state = "EXIT_CANDIDATE", "EXIT_REVIEW"
        elif action == "reduction_review": signal, state = "REDUCE_CANDIDATE", "REDUCTION_REVIEW"
        else: state = "STRATEGY_REFRESH_REQUIRED"; remaining.append("HARD_RISK_ACTION_AUTHORITY_REQUIRED")
    elif overlay.get("risk_status") in {"VETO", "HARD_RISK"}:
        signal, state = "EXIT_CANDIDATE", "EXIT_REVIEW"
    elif overlay.get("risk_status") == "CONSTRAINED" or overlay.get("portfolio_fit_status") == "CONSTRAINED":
        signal, state = "REDUCE_CANDIDATE", "REDUCTION_REVIEW"
    elif judgement_status in {"ATTRACTIVE", "FAIR"} and overlay.get("technical_status") == "READY" and event_link.get("event_effect") == "CONTEXT_ONLY" and overlay.get("portfolio_fit_status") == "FITS":
        signal, state = "ADD_CANDIDATE", "ADD_REVIEW"
    elif overlay.get("technical_status") in {"WATCH", "DETERIORATING"}:
        state = "ADD_ON_WATCH" if baseline.get("research_recommendation") == "POTENTIAL_ADD_CASE" else "HOLD"
    if evidence_status in {"UNVERIFIED", "PARTIAL", "STALE", "INVALID", "PRICE_EVIDENCE_CONFLICT"} and signal == "ADD_CANDIDATE":
        signal, state = "NONE", "STRATEGY_REFRESH_REQUIRED"; remaining.append("UNVERIFIED_VALUATION_CANNOT_ADD")
    blocked = list(blocked_decision_classes or [])
    if baseline.get("ticker") == "MVLL" and "EMA10_RECLAIM_RVOL20" not in blocked:
        blocked.append("EMA10_RECLAIM_RVOL20")
    compile_status = "FAILED" if errors else ("PENDING" if remaining else "PASSED")
    result = {
        "schema_version": "2.6.12", "mode": "NON_AUTHORITATIVE_SHADOW", "ticker": baseline["ticker"],
        "candidate_baseline_id": baseline["baseline_id"], "candidate_baseline_hash": baseline["baseline_hash"],
        "valuation_snapshot_id": valuation.get("valuation_snapshot_id") if valuation else None,
        "valuation_snapshot_hash": valuation.get("snapshot_hash") if valuation else None,
        "event_link_id": event_link["baseline_event_link_id"], "event_link_hash": event_link["link_hash"],
        "overlay_hash": overlay["overlay_hash"], "portfolio_state_revision": int(portfolio["state_revision"]),
        "portfolio_state_hash": file_hash(portfolio_path), "policy_hash": file_hash(policy_path),
        "provider_scope_hash": file_hash(provider_scope_path), "thesis_status": baseline["thesis_status"],
        "valuation_evidence_status": evidence_status, "valuation_judgement_status": judgement_status,
        "technical_status": overlay["technical_status"],
        "event_status": "CONTEXT_ONLY" if event_link.get("link_validation_status") in VALID_EVENT_LINKS else "EVENT_REVIEW_PENDING",
        "risk_status": overlay["risk_status"], "portfolio_fit_status": overlay["portfolio_fit_status"],
        "strategy_signal": signal, "primary_reason": baseline["primary_reason"],
        "strongest_counter_case": baseline["strongest_counter_case"],
        "invalidation": baseline["invalidation_conditions"], "next_review_trigger": baseline["next_research_triggers"],
        "remaining_conditions": list(dict.fromkeys(remaining)), "shadow_compile_status": compile_status,
        "live_strategy_state": live_strategy_state, "shadow_strategy_state": state,
        "blocked_decision_classes": sorted(set(blocked)),
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    return result


def activate_shadow_candidate(*, baseline: dict[str, Any], compile_result: dict[str, Any],
                              baseline_schema: Path, baseline_root: Path, index_path: Path,
                              expected_prior_index_hash: str, activated_at: str) -> dict[str, Any]:
    validation = validate_baseline(baseline, baseline_schema)
    if validation["validation_status"] != "PASSED":
        return {"activation_status": "REJECTED", "errors": validation["errors"], "index_updated": False, "order_authority": False}
    if compile_result.get("shadow_compile_status") != "PASSED":
        return {"activation_status": "REJECTED", "errors": ["SHADOW_COMPILE_NOT_PASSED"], "index_updated": False, "order_authority": False}
    if compile_result.get("candidate_baseline_id") != baseline.get("baseline_id") or compile_result.get("candidate_baseline_hash") != baseline.get("baseline_hash"):
        return {"activation_status": "REJECTED", "errors": ["COMPILE_BASELINE_IDENTITY_MISMATCH"], "index_updated": False, "order_authority": False}
    if compile_result.get("valuation_evidence_status") not in VALID_VALUATION_EVIDENCE:
        return {"activation_status": "REJECTED", "errors": ["VALUATION_NOT_ACTIVATABLE"], "index_updated": False, "order_authority": False}
    if compile_result.get("event_status") not in {"CLEAR", "CONTEXT_ONLY"}:
        return {"activation_status": "REJECTED", "errors": ["EVENT_LINK_NOT_ACTIVATABLE"], "index_updated": False, "order_authority": False}
    if compile_result.get("quantity") is not None or compile_result.get("quantity_authority") != "none" or compile_result.get("order_authority") is not False:
        return {"activation_status": "REJECTED", "errors": ["AUTHORITY_BOUNDARY_VIOLATION"], "index_updated": False, "order_authority": False}
    index = json.loads(index_path.read_text(encoding="utf-8"))
    actual_index_hash = canonical_hash(index)
    if actual_index_hash != expected_prior_index_hash:
        return {"activation_status": "REJECTED", "errors": ["PRIOR_INDEX_HASH_MISMATCH"], "index_updated": False, "order_authority": False}
    ticker = baseline["ticker"]
    previous = (index.get("active") or {}).get(ticker)
    activated = deepcopy(baseline)
    activated["validation_status"] = "VALIDATED_SHADOW"
    activated["activated_at"] = activated_at
    target = baseline_root / ticker / f"{baseline['baseline_id']}.json"
    if target.resolve().parent != (baseline_root / ticker).resolve():
        return {"activation_status": "REJECTED", "errors": ["BASELINE_TARGET_PATH_INVALID"],
                "index_updated": False, "order_authority": False}
    if target.exists() and json.loads(target.read_text(encoding="utf-8")) != activated:
        return {"activation_status": "REJECTED", "errors": ["IMMUTABLE_BASELINE_EXISTS"], "index_updated": False, "order_authority": False}
    if not target.exists(): _atomic_write_json(target, activated)
    workspace_ancestors = [parent for parent in baseline_root.resolve().parents if parent.name == "workspace"]
    if workspace_ancestors:
        repository_root = workspace_ancestors[0].parent
        portable_target = target.resolve().relative_to(repository_root.resolve()).as_posix()
    else:
        portable_target = target.resolve().relative_to(index_path.resolve().parent).as_posix()
    index["active"][ticker] = {
        "baseline_id": baseline["baseline_id"], "baseline_version": baseline["baseline_version"],
        "baseline_hash": baseline["baseline_hash"], "research_packet_hash": baseline["research_packet_hash"],
        "activated_at": activated_at, "baseline_path": portable_target,
        "supersedes_baseline_id": previous.get("baseline_id") if previous else None,
    }
    index["updated_at"] = activated_at
    _atomic_write_json(index_path, index)
    return {"activation_status": "VALIDATED_SHADOW", "errors": [], "index_updated": True,
            "ticker": ticker, "previous_baseline_id": previous.get("baseline_id") if previous else None,
            "new_index_hash": canonical_hash(index), "historical_alert_replay_count": 0,
            "quantity_authority": "none", "order_authority": False}


def initialize_observation(*, ticker: str, baseline_id: str, baseline_hash: str,
                           activation_session: str) -> dict[str, Any]:
    result = {"schema_version": "2.6.12", "ticker": ticker, "baseline_id": baseline_id,
              "baseline_hash": baseline_hash, "activation_session": activation_session,
              "required_valid_sessions": 5, "observed_sessions": [], "valid_sessions": [],
              "excluded_sessions": [], "live_shadow_differences": [], "critical_violations": [],
              "status": "FIRST_OBSERVATION_SESSION_PENDING", "previous_record_hash": None,
              "record_hash": "0" * 64, "order_authority": False}
    result["record_hash"] = canonical_hash(_without_hash(result, "record_hash"))
    return result


def record_observation(state: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    prior_hash = result["record_hash"]
    session = observation.get("market_session")
    eligible = all([
        observation.get("run_phase") == "POST_MARKET_FINALIZED",
        observation.get("official_session_verified") is True,
        observation.get("bar_finalized") is True,
        observation.get("delivery_verified") is True,
        observation.get("clean_committed_main") is True,
        observation.get("portfolio_hash_unchanged") is True,
        observation.get("policy_hash_unchanged") is True,
        observation.get("manual") is False,
        observation.get("replay") is False,
        observation.get("order_authority") is False,
        isinstance(session, str), session > state["activation_session"],
        session not in result["valid_sessions"],
    ])
    if eligible:
        result["observed_sessions"].append(observation)
        result["valid_sessions"].append(session)
    else:
        result["excluded_sessions"].append({"market_session": session, "reason": "OBSERVATION_NOT_ELIGIBLE"})
    violations = list(observation.get("critical_violations") or [])
    if observation.get("order_authority") is not False: violations.append("ORDER_AUTHORITY_TRUE")
    if observation.get("portfolio_mutated") is True: violations.append("PORTFOLIO_MUTATION")
    result["critical_violations"] = sorted(set(result["critical_violations"] + violations))
    if result["critical_violations"]: result["status"] = "CRITICAL_VIOLATION"
    elif len(result["valid_sessions"]) >= 5: result["status"] = "FIVE_SESSION_REVIEW_REQUIRED"
    elif result["valid_sessions"]: result["status"] = "OBSERVING"
    result["previous_record_hash"] = prior_hash
    result["record_hash"] = canonical_hash(_without_hash(result, "record_hash"))
    return result
