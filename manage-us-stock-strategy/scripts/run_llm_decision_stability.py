#!/usr/bin/env python3
"""Run privacy-safe repeated LLM reviews for a public tactical candidate.

Only public market/event evidence and non-sensitive research authority flags are
sent to the model. Portfolio holdings, cash, cost basis, fills, and runtime state
are never loaded by this harness. The model remains untrusted; deterministic
policy forces an unapproved new-buy candidate to WAIT with no quantity or order.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from validation_common import load_json, write_json


class LLMReview(BaseModel):
    """Strict structured output from the untrusted model."""

    model_config = ConfigDict(extra="forbid")

    identity_summary: str
    technical_summary: str
    bull_case: str
    bear_case: str
    research_manager_status: Literal[
        "RESEARCH_COMPLETE", "RESEARCH_CONDITIONAL", "RESEARCH_REJECTED"
    ]
    action: Literal["WAIT", "CONDITIONAL_BUY", "BUY_REVIEW"]
    risk_verdict: Literal["ALLOW_REVIEW", "DOWNGRADE", "VETO"]
    dominant_thesis_code: Literal[
        "WAIT_PERMISSION_AND_VALUATION",
        "WAIT_DATA_INCOMPLETE",
        "CONDITIONAL_TECHNICAL_WATCH",
        "BUY_REVIEW_ALL_GATES_PASS",
    ]
    strongest_counter_thesis: str
    invalidation_codes: list[
        Literal[
            "TECHNICAL_REGIME_INVALIDATES",
            "EVENT_OR_DATA_GAP",
            "VALUATION_REMAINS_UNVERIFIED",
            "NEW_BUY_AUTHORITY_REMAINS_ABSENT",
        ]
    ] = Field(min_length=1)
    preferred_candidate: Literal["NBIS"] | None
    unknowns: list[str]
    event_risk_status: Literal["KNOWN_EVENT", "EVENT_DATA_INCOMPLETE"]
    quantity: None = None
    order_authority: Literal[False] = False


THESIS_SUMMARIES = {
    "WAIT_PERMISSION_AND_VALUATION": (
        "WAIT: NBIS is research-eligible, but new-buy authority, valuation, sizing, "
        "and risk-budget gates are not approved."
    ),
    "WAIT_DATA_INCOMPLETE": (
        "WAIT: event or decision evidence is incomplete and cannot authorize a new buy."
    ),
    "CONDITIONAL_TECHNICAL_WATCH": (
        "The validated technical snapshot supports continued research only; earlier "
        "valuation and permission gates remain unresolved."
    ),
    "BUY_REVIEW_ALL_GATES_PASS": (
        "The model proposed BUY_REVIEW, but deterministic policy independently checks "
        "and limits that proposal."
    ),
}

INVALIDATION_DESCRIPTIONS = {
    "TECHNICAL_REGIME_INVALIDATES": "A later validated completed-session technical regime invalidates the setup.",
    "EVENT_OR_DATA_GAP": "A material event or data-integrity gap makes the candidate evidence incomplete.",
    "VALUATION_REMAINS_UNVERIFIED": "A reliable current valuation gate remains unavailable.",
    "NEW_BUY_AUTHORITY_REMAINS_ABSENT": "Explicit new-buy, risk-budget, and quantity authority remain absent.",
}


SYSTEM_INSTRUCTIONS = """You are an untrusted research component inside a human-review-only U.S. stock decision system. Use only the immutable JSON evidence bundle supplied in the user message. Do not use outside facts.

Perform a bounded role-separated review: identity/data auditor, technical analyst, Bull Researcher, Bear Researcher, Research Manager, Trader, and independent Risk Controller.

Authority rules:
- Evidence integrity, valuation, technical validation, event risk, and deterministic permission gates are ordered. A later gate cannot repair an earlier failure.
- The candidate is not verified as held. Use only WAIT, CONDITIONAL_BUY, or BUY_REVIEW.
- Watchlist approval is not new-buy approval.
- Missing valuation cannot be invented.
- Missing event coverage must remain EVENT_DATA_INCOMPLETE; it is not proof of no event.
- Do not infer or propose a quantity. quantity must be null.
- Do not create cash, holdings, fills, leverage approval, short authority, or order authority.
- Risk Controller may preserve or downgrade; it may never upgrade.
- If Trader returns WAIT, Risk Controller must return ALLOW_REVIEW because no lower-intensity action exists.
- If Trader returns CONDITIONAL_BUY or BUY_REVIEW while new-buy authority is absent, Risk Controller must return DOWNGRADE or VETO.

Return a concise structured review. This is a repeated stability validation, not a trading instruction."""


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dotenv(path: Path) -> None:
    """Load local credentials without logging values or overriding the process."""

    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def selected_market_fields(row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "ticker", "bar_date", "close", "close_prev", "return_1d", "return_1m",
        "ema10", "ema20", "ema10_direction_3d", "ema20_direction_3d",
        "ema10_above_ema20", "atr14", "volume_ratio_to_20d",
        "ma50", "ma200", "rsi14", "macd", "macd_signal",
        "drawdown_from_52w_high", "corporate_action_unresolved",
        "indicator_validation", "quote_crosscheck",
    )
    return {field: row.get(field) for field in fields}


def build_public_bundle(args: argparse.Namespace) -> dict[str, Any]:
    market = load_json(args.market)
    events = load_json(args.events)
    screen = load_json(args.screen)
    technical = load_json(args.technical_validation)
    registry = load_json(args.registry)
    universe = load_json(args.universe)

    session = require_object(market.get("session"), "market session")
    if session.get("calendar_verification_status") != "verified_trading_day":
        raise ValueError("market session is not officially verified")
    if technical.get("status") != "verified":
        raise ValueError("technical snapshot is not verified")
    if args.symbol not in (screen.get("shortlist") or []):
        raise ValueError(f"{args.symbol} is not in the validated shortlist")
    symbols = require_object(market.get("symbols"), "market symbols")
    row = symbols.get(args.symbol)
    if not isinstance(row, dict):
        raise ValueError(f"missing market row for {args.symbol}")
    instrument = require_object(registry.get("instruments"), "instrument registry").get(args.symbol)
    candidate = require_object(universe.get("candidates"), "candidate universe").get(args.symbol)
    if not isinstance(instrument, dict) or not isinstance(candidate, dict):
        raise ValueError(f"missing registry/universe identity for {args.symbol}")
    stage_row = next(
        (item for item in screen.get("stage_one", []) if item.get("symbol") == args.symbol),
        None,
    )
    if not isinstance(stage_row, dict):
        raise ValueError(f"missing tactical screen row for {args.symbol}")

    bundle = {
        "bundle_version": "1.0",
        "privacy_scope": "public_market_event_and_non_sensitive_research_authority_only",
        "prohibited_private_inputs": [
            "portfolio holdings", "cash", "cost basis", "fills", "runtime state"
        ],
        "analysis_cutoff_utc": args.analysis_cutoff,
        "symbol": args.symbol,
        "position_status": "NOT_HELD_FOR_VALIDATION_FIXTURE",
        "market_session": session.get("us_session_date"),
        "market_session_verification": session,
        "market": selected_market_fields(row),
        "technical_validation": technical,
        "event_snapshot": {
            "coverage_status": events.get("coverage_status"),
            "coverage_notes": events.get("coverage_notes") or [],
            "events": events.get("events") or [],
            "order_authority": False,
        },
        "screen": stage_row,
        "authority": {
            "watchlist_approved": candidate.get("watchlist_approved"),
            "new_buy_approved": candidate.get("new_buy_approved"),
            "short_approved": candidate.get("short_approved"),
            "instrument_new_buy_approved": instrument.get("new_buy_instrument_approved"),
            "quantity_authority": None,
            "order_authority": False,
        },
        "source_hashes": {
            "market_snapshot": file_hash(args.market),
            "event_snapshot": file_hash(args.events),
            "tactical_screen": file_hash(args.screen),
            "technical_validation": file_hash(args.technical_validation),
            "instrument_registry": file_hash(args.registry),
            "tactical_universe": file_hash(args.universe),
        },
    }
    bundle["bundle_sha256"] = canonical_hash(bundle)
    return bundle


def analyst(role: str, stance: str, confidence: str, summary: str, claim_ids: list[str], unknowns: list[str], impact: str, status: str) -> dict[str, Any]:
    return {
        "role": role,
        "stance": stance,
        "confidence": confidence,
        "summary": summary,
        "claim_ids": claim_ids,
        "unknowns": unknowns,
        "decision_impact": impact,
        "status": status,
    }


def build_record(review: LLMReview, bundle: dict[str, Any], registry: dict[str, Any], universe: dict[str, Any], run_index: int, created_at: str) -> dict[str, Any]:
    model_action = "WAIT" if review.research_manager_status == "RESEARCH_REJECTED" else review.action
    if model_action == "WAIT":
        risk_verdict, risk_output = "ALLOW_REVIEW", "WAIT"
        risk_reasons = ["WAIT is preserved without authority upgrade."]
        gate_warnings = ["new buy is not approved for this candidate"]
    else:
        risk_verdict = "VETO" if review.risk_verdict == "VETO" else "DOWNGRADE"
        risk_output = "WAIT"
        risk_reasons = ["Watchlist research is not new-buy, risk-budget, or quantity approval."]
        gate_warnings = [
            "watchlist approval is not new-buy approval",
            "new buy is not approved for this candidate",
        ]

    event = bundle["event_snapshot"]
    first_event = event["events"][0] if event["events"] else None
    unknowns = sorted(set(review.unknowns + event["coverage_notes"] + ["Current valuation is unverified."]))
    manager_status = review.research_manager_status
    if manager_status == "RESEARCH_COMPLETE":
        manager_status = "RESEARCH_CONDITIONAL"
    market_session = bundle["market_session"]
    session_close = f"{market_session}T20:00:00+00:00"
    market_retrieval = bundle["market"]["quote_crosscheck"]["verified_at_utc"]
    invalidations = [
        INVALIDATION_DESCRIPTIONS[code] for code in dict.fromkeys(review.invalidation_codes)
    ]
    conditions = [
        {"id": "C1", "kind": "CONFIRMATION", "description": "A future cycle independently verifies valuation, technical entry, event coverage, risk budget, quantity, and explicit new-buy authority."}
    ] + [
        {"id": f"I{index}", "kind": "INVALIDATION", "description": description}
        for index, description in enumerate(invalidations, start=1)
    ]
    evidence = [
        {
            "id": "E1", "claim": "NBIS identity is registered for research and is not approved as a new buy.",
            "record_type": "VERIFIED_FACT", "source_url": None, "source_type": "primary",
            "published_at_utc": bundle["analysis_cutoff_utc"], "retrieved_at_utc": bundle["analysis_cutoff_utc"],
            "effective_at_utc": bundle["analysis_cutoff_utc"], "observation_session": market_session,
            "units": None, "price_basis": None, "formula_version": universe["universe_version"],
            "confidence": "HIGH", "contradiction_status": "NONE", "actionable": True,
            "notes": "Research permission is intentionally separate from purchase authority."
        },
        {
            "id": "E2", "claim": "NBIS completed-session close and technical features passed independent close and technical validation.",
            "record_type": "VERIFIED_FACT", "source_url": bundle["market"]["quote_crosscheck"]["source_url"],
            "source_type": "market_data", "published_at_utc": session_close,
            "retrieved_at_utc": market_retrieval, "effective_at_utc": session_close,
            "observation_session": market_session, "units": "USD per share",
            "price_basis": "raw completed regular-session close; locally calculated adjusted indicators",
            "formula_version": bundle["technical_validation"].get("formula_version"), "confidence": "HIGH",
            "contradiction_status": "NONE", "actionable": True,
            "notes": "The LLM did not recalculate or repair technical indicators."
        },
        {
            "id": "E3", "claim": "Verified macro events are present while corporate and market-structure event coverage remains incomplete.",
            "record_type": "VERIFIED_FACT", "source_url": first_event.get("source_identifier") if first_event else None,
            "source_type": "primary" if first_event else "calculation",
            "published_at_utc": first_event.get("retrieved_at") if first_event else bundle["analysis_cutoff_utc"],
            "retrieved_at_utc": first_event.get("retrieved_at") if first_event else bundle["analysis_cutoff_utc"],
            "effective_at_utc": first_event.get("retrieved_at") if first_event else bundle["analysis_cutoff_utc"],
            "observation_session": market_session, "units": None, "price_basis": None,
            "formula_version": None, "confidence": "HIGH" if first_event else "LOW",
            "contradiction_status": "NONE", "actionable": False,
            "notes": "Missing coverage is not interpreted as no event."
        },
        {
            "id": "E4", "claim": "Current valuation is unavailable and cannot pass the ordered new-buy gate.",
            "record_type": "CALCULATION", "source_url": None, "source_type": "calculation",
            "published_at_utc": bundle["analysis_cutoff_utc"], "retrieved_at_utc": bundle["analysis_cutoff_utc"],
            "effective_at_utc": bundle["analysis_cutoff_utc"], "observation_session": market_session,
            "units": None, "price_basis": None, "formula_version": "ordered-gates-v2.1",
            "confidence": "HIGH", "contradiction_status": "NONE", "actionable": True,
            "notes": "A validated technical snapshot cannot repair an unverified valuation gate."
        },
    ]
    analysts = [
        analyst("identity_data_auditor", "NEUTRAL", "HIGH", review.identity_summary, ["E1", "E2"], [], "NO_CHANGE", "RESEARCH_COMPLETE"),
        analyst("fundamental_valuation_analyst", "NEUTRAL", "LOW", "Current valuation is unverified; no new-buy conclusion is permitted.", ["E4"], ["Current valuation is unverified."], "CONDITIONAL", "RESEARCH_CONDITIONAL"),
        analyst("market_technical_analyst", "NEUTRAL", "HIGH", review.technical_summary, ["E2"], [], "CONDITIONAL", "RESEARCH_COMPLETE"),
        analyst("news_macro_analyst", "NEUTRAL", "MEDIUM", "Macro events are context-only and event coverage remains incomplete.", ["E3"], event["coverage_notes"], "CONDITIONAL", "RESEARCH_CONDITIONAL"),
        analyst("bull_researcher", "BULLISH", "MEDIUM", review.bull_case, ["E2"], unknowns, "SUPPORTS", "RESEARCH_COMPLETE"),
        analyst("bear_researcher", "BEARISH", "HIGH", review.bear_case, ["E1", "E3", "E4"], unknowns, "OPPOSES", "RESEARCH_COMPLETE"),
    ]
    manager = analyst(
        "research_manager", "NEUTRAL", "HIGH", THESIS_SUMMARIES[review.dominant_thesis_code],
        ["E1", "E2", "E3", "E4"], unknowns, "CONDITIONAL", manager_status,
    )
    manager.update({"accepted_claim_ids": ["E1", "E2", "E3", "E4"], "rejected_claim_ids": [], "unresolved_conflicts": event["coverage_notes"]})
    return {
        "schema_version": "2.0", "decision_id": f"NBIS-V21-STABILITY-{run_index:02d}",
        "created_at_utc": created_at, "test_only": True, "symbol": "NBIS",
        "instrument_registry_version": registry["registry_version"],
        "tactical_universe_version": universe["universe_version"],
        "portfolio_state_revision": None, "policy_version": "v2.1-public-shadow-stability-v1",
        "research_packet": {
            "schema_version": "2.0", "analysis_id": f"NBIS-V21-STABILITY-ANALYSIS-{run_index:02d}",
            "analysis_kind": "TACTICAL_SELECTION", "symbol": "NBIS",
            "analysis_cutoff_utc": bundle["analysis_cutoff_utc"], "generated_at_utc": created_at,
            "analysis_session_date": market_session, "evidence": evidence,
            "analyst_outputs": analysts, "research_manager": manager,
            "strongest_counter_thesis": review.strongest_counter_thesis,
            "invalidation_conditions": invalidations, "unresolved_conditions": unknowns,
        },
        "trader_proposal": {
            "symbol": "NBIS", "position_status": "NOT_HELD", "action": model_action,
            "quantity": None, "policy_rule_id": None, "claim_ids": ["E1", "E2", "E3", "E4"],
            "setup": "Public-evidence tactical research stability validation only.",
            "invalidation_condition_ids": [f"I{index}" for index in range(1, len(invalidations) + 1)],
            "expiry": None, "next_material_event": first_event.get("event_type") if first_event else None,
            "event_time": first_event.get("scheduled_at") if first_event else None,
            "event_risk_status": "EVENT_DATA_INCOMPLETE",
            "event_source": first_event.get("source_identifier") if first_event else None,
            "event_policy_effect": "EVENT_DATA_INCOMPLETE", "order_authority": False,
        },
        "risk_review": {
            "verdict": risk_verdict, "input_action": model_action, "output_action": risk_output,
            "reasons": risk_reasons, "claim_ids": ["E1", "E3", "E4"],
            "may_upgrade": False, "order_authority": False,
        },
        "portfolio_decision": {
            "action": "WAIT", "quantity": None, "preferred_candidate": None,
            "alternative_candidate": None, "strategic_allocation_change": False,
            "portfolio_fit": "BLOCKED",
            "constraints": ["New buy is not approved.", "Valuation is unverified.", "No risk budget or quantity authority exists."],
            "wait_reason": "Earlier ordered gates remain unresolved.", "order_authority": False,
        },
        "deterministic_gate": {
            "status": "WATCH_ONLY", "validated_at_utc": created_at,
            "errors": [], "warnings": gate_warnings, "order_authority": False,
        },
        "final_action": "WAIT", "human_decision": "NO_TRADE",
        "evaluation_plan": {"conditions": conditions, "checkpoints": ["next validated evidence cycle", "next material event update"]},
        "artifact_hashes": bundle["source_hashes"], "record_locked": True, "order_authority": False,
    }


def classify_raw_stability(runs: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "action": {item["action"] for item in runs},
        "risk_verdict": {item["risk_verdict"] for item in runs},
        "dominant_thesis_code": {item["dominant_thesis_code"] for item in runs},
        "invalidation_codes": {json.dumps(sorted(item["invalidation_codes"])) for item in runs},
        "preferred_candidate": {item["preferred_candidate"] for item in runs},
    }
    differences = [field for field, values in fields.items() if len(values) > 1]
    authority_classes = {
        "BUY_SIDE" if item["action"] in {"CONDITIONAL_BUY", "BUY_REVIEW"} else "NO_TRADE"
        for item in runs
    }
    critical = len(authority_classes) > 1 or (
        any(item["risk_verdict"] == "VETO" for item in runs)
        and any(item["risk_verdict"] == "ALLOW_REVIEW" for item in runs)
    )
    return {
        "status": "DECISION_STABILITY_RISK" if critical else "PASS",
        "critical_instability": critical,
        "run_count": len(runs),
        "differences": differences,
        "authority_classes": sorted(authority_classes),
        "compared_fields": sorted(fields),
        "note": "Minor prose differences are intentionally excluded.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--screen", required=True, type=Path)
    parser.add_argument("--technical-validation", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--symbol", default="NBIS", choices=["NBIS"])
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--runs", type=int, default=3, help="Validation setting only; not a trading rule.")
    parser.add_argument("--model", default="gpt-5.6-terra")
    parser.add_argument("--reasoning-effort", default="medium", choices=["none", "low", "medium", "high", "xhigh"])
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.runs < 3:
        raise SystemExit("at least three validation runs are required")
    if args.env_file:
        load_dotenv(args.env_file)
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is unavailable; no network call was made")

    from openai import OpenAI

    args.output_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_public_bundle(args)
    write_json(args.output_dir / "llm-stability-input.json", bundle)
    prompt = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    client = OpenAI()
    registry = load_json(args.registry)
    universe = load_json(args.universe)
    raw_runs: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for index in range(1, args.runs + 1):
        response = client.responses.parse(
            model=args.model, reasoning={"effort": args.reasoning_effort},
            instructions=SYSTEM_INSTRUCTIONS, input=prompt, text_format=LLMReview,
            store=False, max_output_tokens=1800,
        )
        review = response.output_parsed
        if review is None:
            raise RuntimeError(f"run {index} returned no parsed output")
        raw = review.model_dump(mode="json")
        raw_runs.append(raw)
        created_at = datetime.now(timezone.utc).isoformat()
        record = build_record(review, bundle, registry, universe, index, created_at)
        record_path = args.output_dir / f"decision_record_run_{index}.json"
        output_path = args.output_dir / f"llm_output_run_{index}.json"
        write_json(record_path, record)
        write_json(output_path, {
            "schema_version": "1.0", "run_index": index, "provider": "OpenAI",
            "model_requested": args.model, "model_returned": response.model,
            "response_id": response.id, "reasoning_effort": args.reasoning_effort,
            "temperature": None, "store": False,
            "privacy_scope": bundle["privacy_scope"],
            "input_bundle_sha256": bundle["bundle_sha256"],
            "immutable_prompt_sha256": prompt_hash, "structured_output": raw,
            "secrets_recorded": False, "order_authority": False,
        })
        run_summaries.append({
            "run_index": index, "model_returned": response.model,
            "model_action": review.action, "model_risk_verdict": review.risk_verdict,
            "final_action": record["final_action"],
            "dominant_thesis_code": review.dominant_thesis_code,
            "invalidation_codes": review.invalidation_codes,
            "decision_record": str(record_path), "llm_output": str(output_path),
        })
    stability = classify_raw_stability(raw_runs)
    write_json(args.output_dir / "llm-stability-result.json", stability)
    write_json(args.output_dir / "llm-stability-run-summary.json", {
        "schema_version": "1.0", "validation_setting_runs": args.runs,
        "provider": "OpenAI", "model": args.model,
        "reasoning_effort": args.reasoning_effort, "temperature": None,
        "openai_sdk_version": importlib.metadata.version("openai"),
        "privacy_scope": bundle["privacy_scope"],
        "input_bundle_sha256": bundle["bundle_sha256"],
        "immutable_prompt_sha256": prompt_hash, "stability": stability,
        "runs": run_summaries, "secrets_recorded": False, "order_authority": False,
    })
    print(json.dumps({"status": stability["status"], "runs": run_summaries}, indent=2))
    return 0 if stability["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
