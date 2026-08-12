#!/usr/bin/env python3
"""Build a strictly indicative premarket snapshot without daily authority."""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance, write_json


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0


def build_snapshot(records: list[dict[str, Any]], *, generated_at: str, upcoming_session: str,
                   latest_completed_session: str, provider_status: str, global_failure: str | None = None,
                   official_upcoming_session_verified: bool = False,
                   session_verification_status: str = "unverified") -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for raw in records:
        quote = float(raw["quote"]) if _positive(raw.get("quote")) else None
        close = float(raw["reference_completed_close"]) if _positive(raw.get("reference_completed_close")) else None
        bid = float(raw["bid"]) if _positive(raw.get("bid")) else None
        ask = float(raw["ask"]) if _positive(raw.get("ask")) else None
        spread = ask - bid if bid is not None and ask is not None and ask >= bid else None
        gap = quote / close - 1 if quote is not None and close is not None else None
        quality = "VALIDATED_INDICATIVE" if quote is not None and close is not None and raw.get("quote_timestamp") else ("PARTIAL" if quote is not None else "DATA_INCOMPLETE")
        normalized.append({
            "ticker": raw["ticker"], "quote": quote, "bid": bid, "ask": ask, "spread": spread,
            "quote_timestamp": raw.get("quote_timestamp"), "timezone": raw.get("timezone") or "America/New_York",
            "provider": raw.get("provider") or "UNVERIFIED", "source_identifier": raw.get("source_identifier") or "UNVERIFIED",
            "premarket_session": upcoming_session, "latest_completed_regular_session": latest_completed_session,
            "reference_completed_close": close, "gap_fraction": gap,
            "volume": float(raw["volume"]) if isinstance(raw.get("volume"), (int, float)) and not isinstance(raw.get("volume"), bool) and raw["volume"] >= 0 else None,
            "data_quality": quality, "indicative_only": True, "completed_regular_session": False,
            "daily_indicator_authority": False, "hard_risk_authority": False, "order_authority": False,
        })
    if provider_status == "UNAVAILABLE":
        global_failure = global_failure or "GLOBAL_PREMARKET_DATA_OUTAGE"
    return {"schema_version": "2.4", "run_phase": "PRE_OPEN", "generated_at": generated_at,
        "upcoming_regular_session": upcoming_session, "latest_completed_regular_session": latest_completed_session,
        "official_upcoming_session_verified": official_upcoming_session_verified,
        "session_verification_status": session_verification_status,
        "provider_status": provider_status, "global_failure": global_failure, "records": normalized,
        "order_authority": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quotes", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--upcoming-session", required=True)
    parser.add_argument("--latest-completed-session", required=True)
    parser.add_argument("--provider-status", choices=["AVAILABLE", "PARTIAL", "UNAVAILABLE"], required=True)
    parser.add_argument("--official-upcoming-session-verified", action="store_true")
    parser.add_argument("--session-verification-status", choices=["verified_trading_day", "unverified", "closed", "holiday"], default="unverified")
    parser.add_argument("--global-failure")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    quotes = load_json(args.quotes)
    if not isinstance(quotes, list):
        raise SystemExit("--quotes must contain a JSON array")
    snapshot = build_snapshot(quotes, generated_at=args.generated_at,
        upcoming_session=args.upcoming_session, latest_completed_session=args.latest_completed_session,
        provider_status=args.provider_status, global_failure=args.global_failure,
        official_upcoming_session_verified=args.official_upcoming_session_verified,
        session_verification_status=args.session_verification_status)
    errors = validate_instance(snapshot, Path(__file__).resolve().parents[1] / "schemas" / "premarket-snapshot.schema.json")
    if errors:
        raise SystemExit("premarket snapshot validation failed: " + "; ".join(errors))
    write_json(args.output, snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
