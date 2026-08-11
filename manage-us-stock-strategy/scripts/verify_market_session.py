#!/usr/bin/env python3
"""Attach explicit official-calendar verification to a market snapshot.

This tool does not discover or infer an exchange session. A caller must supply
the already-verified session date, official HTTPS source, and verification
timestamp. Every collected symbol must share that completed bar date.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class SessionVerificationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SessionVerificationError("snapshot top level must be an object")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SessionVerificationError("verified-at-utc must include a timezone offset")
    return parsed


def verify(
    snapshot: dict[str, Any],
    *,
    expected_session_date: str,
    calendar_source: str,
    verified_at_utc: str,
    is_early_close: bool,
) -> dict[str, Any]:
    try:
        datetime.strptime(expected_session_date, "%Y-%m-%d")
    except ValueError as exc:
        raise SessionVerificationError("expected session date must be YYYY-MM-DD") from exc
    parsed_source = urlparse(calendar_source)
    if parsed_source.scheme != "https" or not parsed_source.netloc:
        raise SessionVerificationError("calendar source must be an HTTPS URL")
    parse_timestamp(verified_at_utc)

    symbols = snapshot.get("symbols")
    if not isinstance(symbols, dict) or not symbols:
        raise SessionVerificationError("snapshot contains no symbols")
    mismatches = sorted(
        symbol
        for symbol, row in symbols.items()
        if not isinstance(row, dict) or row.get("bar_date") != expected_session_date
    )
    if mismatches:
        raise SessionVerificationError(
            "symbol bar dates do not match the verified session: " + ", ".join(mismatches)
        )
    session = snapshot.get("session")
    if not isinstance(session, dict):
        raise SessionVerificationError("snapshot session is missing")
    if session.get("us_session_date") != expected_session_date:
        raise SessionVerificationError("snapshot session date conflicts with verified date")
    if session.get("regular_session_complete") is not True:
        raise SessionVerificationError("snapshot does not contain a completed regular session")
    if is_early_close:
        raise SessionVerificationError(
            "unadjusted early-close volume cannot authorize timing validation"
        )

    session.update(
        {
            "expected_us_session_date": expected_session_date,
            "is_trading_day": True,
            "is_early_close": False,
            "official_calendar_verified": True,
            "calendar_verification_status": "verified_trading_day",
            "calendar_source_type": "official_exchange_or_regulator",
            "calendar_source": calendar_source,
            "calendar_verified_at_utc": verified_at_utc,
        }
    )
    return snapshot


def self_test() -> None:
    fixture = {
        "session": {
            "us_session_date": "2026-08-10",
            "regular_session_complete": True,
        },
        "symbols": {"TEST": {"bar_date": "2026-08-10"}},
    }
    result = verify(
        fixture,
        expected_session_date="2026-08-10",
        calendar_source="https://www.nyse.com/trade/hours-calendars",
        verified_at_utc="2026-08-11T14:00:00+00:00",
        is_early_close=False,
    )
    assert result["session"]["official_calendar_verified"] is True
    rejected = False
    try:
        verify(
            fixture,
            expected_session_date="2026-08-11",
            calendar_source="https://www.nyse.com/trade/hours-calendars",
            verified_at_utc="2026-08-11T14:00:00+00:00",
            is_early_close=False,
        )
    except SessionVerificationError:
        rejected = True
    assert rejected
    print("Self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-session-date")
    parser.add_argument("--calendar-source")
    parser.add_argument("--verified-at-utc")
    parser.add_argument("--is-early-close", choices=("true", "false"), default="false")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    required = (
        args.snapshot,
        args.output,
        args.expected_session_date,
        args.calendar_source,
        args.verified_at_utc,
    )
    if any(value is None for value in required):
        parser.error(
            "--snapshot, --output, --expected-session-date, --calendar-source, "
            "and --verified-at-utc are required"
        )
    try:
        result = verify(
            read_json(args.snapshot),
            expected_session_date=args.expected_session_date,
            calendar_source=args.calendar_source,
            verified_at_utc=args.verified_at_utc,
            is_early_close=args.is_early_close == "true",
        )
        atomic_write_json(args.output, result)
        print(args.output.resolve())
        return 0
    except (OSError, json.JSONDecodeError, SessionVerificationError) as exc:
        print(f"SESSION_VERIFICATION_ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
