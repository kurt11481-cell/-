#!/usr/bin/env python3
"""Run a lightweight, non-actionable tactical screen from canonical inputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import load_json, write_json


def _lane_for(symbol: str, universe: dict[str, Any]) -> str | None:
    for lane, values in (universe.get("lanes") or {}).items():
        if symbol in values.get("symbols", []):
            return lane
    return None


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _market_integrity(market: dict[str, Any], row: dict[str, Any] | None, market_session: str | None) -> list[str]:
    reasons: list[str] = []
    session = market.get("session") or {}
    if (
        session.get("official_calendar_verified") is not True
        or session.get("calendar_verification_status") != "verified_trading_day"
    ):
        reasons.append("official completed-session calendar is not verified")
    if session.get("regular_session_complete") is not True:
        reasons.append("regular session is not complete")
    if not market_session or session.get("us_session_date") != market_session:
        reasons.append("market snapshot session mismatch")
    if not isinstance(row, dict):
        reasons.append("canonical completed-session market data unavailable")
        return reasons
    if row.get("bar_date") != market_session:
        reasons.append("symbol bar date does not match the completed session")
    if not all(_positive_number(row.get(field)) for field in ("open", "high", "low", "close", "close_prev", "volume")):
        reasons.append("completed-session OHLCV is incomplete or invalid")
    if row.get("corporate_action_unresolved") is not False:
        reasons.append("corporate-action status is unresolved")
    indicator = row.get("indicator_validation") or {}
    if indicator.get("status") != "passed" or indicator.get("errors") != []:
        reasons.append("deterministic indicator validation did not pass")
    crosscheck = row.get("quote_crosscheck") or {}
    if (
        crosscheck.get("status") != "verified"
        or crosscheck.get("independent_of_builder") is not True
        or crosscheck.get("bar_date") != market_session
    ):
        reasons.append("independent completed-close cross-check did not pass")
    return reasons


def screen(universe: dict[str, Any], registry: dict[str, Any], market: dict[str, Any], events: dict[str, Any], *, generated_at: str, analysis_cutoff: str, market_session: str | None) -> dict[str, Any]:
    candidates = universe.get("candidates") or {}
    instruments = registry.get("instruments") or {}
    symbols = market.get("symbols") or {}
    event_status = events.get("coverage_status", "EVENT_DATA_INCOMPLETE")
    rows: list[dict[str, Any]] = []
    survivors: list[str] = []
    validated_market_rows = 0
    for symbol, candidate in candidates.items():
        instrument = instruments.get(symbol) or {}
        market_row = symbols.get(symbol)
        market_reasons = _market_integrity(market, market_row, market_session)
        market_valid = not market_reasons
        if market_valid:
            validated_market_rows += 1
        evidence = "PASS" if market_valid else "FAIL"
        identity = instrument.get("identity_status", "UNVERIFIED")
        technical = "VALIDATED" if market_valid else "UNAVAILABLE"
        event_gate = "EVENT_DATA_INCOMPLETE" if event_status != "COMPLETE" else "CLEAR"
        reasons: list[str] = list(market_reasons)
        if candidate.get("watchlist_approved") is not True:
            reasons.append("watchlist research is not approved")
        if identity == "user_supplied_pending_primary_verification":
            reasons.append("primary identity verification remains pending")
        row = {
            "symbol": symbol,
            "lane": _lane_for(symbol, universe),
            "identity_status": identity,
            "watchlist_approved": candidate.get("watchlist_approved") is True,
            "new_buy_approved": candidate.get("new_buy_approved") is True and instrument.get("new_buy_instrument_approved") is True,
            "evidence": evidence,
            "valuation": "UNVERIFIED",
            "technical": technical,
            "event_risk": event_gate,
            "portfolio_eligibility": "RESEARCH_ONLY",
            "screen_status": "SURVIVES" if not reasons and evidence == "PASS" else "REJECTED",
            "reasons": reasons,
        }
        if row["screen_status"] == "SURVIVES":
            survivors.append(symbol)
        rows.append(row)
    max_candidates = int((universe.get("screening") or {}).get("deep_research_shortlist_maximum", 5))
    shortlist = survivors[:max_candidates]
    if validated_market_rows == len(candidates):
        data_status = "VALIDATED"
    elif validated_market_rows:
        data_status = "PARTIAL"
    else:
        data_status = "DATA_INCOMPLETE"
    final_status = "SHORTLIST_READY" if shortlist else ("DATA_INCOMPLETE" if data_status == "DATA_INCOMPLETE" else "WAIT_NO_TRADE")
    reasons = [] if shortlist else ["No candidate passed Stage 1."]
    if data_status == "DATA_INCOMPLETE":
        reasons.append("The live provider failed; stale market data were not substituted.")
    return {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "analysis_cutoff": analysis_cutoff,
        "market_session": market_session,
        "data_status": data_status,
        "event_status": event_status,
        "universe": list(candidates),
        "stage_one": rows,
        "shortlist": shortlist,
        "deep_research_candidates": shortlist,
        "preferred_candidate": None,
        "alternative_candidate": None,
        "final_status": final_status,
        "reasons": reasons,
        "missing_permissions": ["new-buy instrument approval", "approved quantity or sizing authority", "approved risk budget and maximum-loss rule"],
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = screen(load_json(args.universe), load_json(args.registry), load_json(args.market), load_json(args.events), generated_at=args.generated_at, analysis_cutoff=args.analysis_cutoff, market_session=args.market_session)
    write_json(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
