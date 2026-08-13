#!/usr/bin/env python3
"""Build an immutable yfinance raw/adjustment-aware replay evidence bundle."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from build_market_snapshot import (
    RequestPacer,
    chart_frame,
    configure_yfinance_ca_bundle,
    fetch_yfinance_chart,
)
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from validation_common import validate_instance


def _actions(result: dict[str, Any], cutoff: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for action_type, rows in (result.get("events") or {}).items():
        for key, row in (rows or {}).items():
            if not isinstance(row, dict):
                continue
            epoch = row.get("date")
            if isinstance(epoch, (int, float)):
                action_session = datetime.fromtimestamp(
                    int(epoch), timezone.utc
                ).astimezone(ZoneInfo("America/New_York")).date().isoformat()
                if action_session > cutoff:
                    continue
            else:
                action_session = None
            value = {
                "action_type": str(action_type), "source_key": str(key),
                "session": action_session,
            }
            for field in ("date", "amount", "numerator", "denominator", "splitRatio"):
                if field in row:
                    value[field] = row[field]
            output.append(value)
    return output


def build_evidence(tickers: list[str], *, completed_session: str, generated_at: str) -> dict[str, Any]:
    tls = configure_yfinance_ca_bundle()
    pacer = RequestPacer(1.0)
    records: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    provider_version = None
    for ticker in tickers:
        try:
            result = fetch_yfinance_chart(ticker, pacer=pacer)
            provider_version = result.get("_provider_version") or provider_version
            frame = chart_frame(result)
            frame = frame[frame.index.date.astype(str) <= completed_session]
            if frame.empty or frame.index[-1].date().isoformat() != completed_session:
                raise ValueError("COMPLETED_SESSION_MISSING")
            bars = [{
                "session": index.date().isoformat(),
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "adjusted_close": float(row["adjclose"]), "volume": float(row["volume"]),
            } for index, row in frame.iterrows()]
            records[ticker] = {
                "ticker": ticker, "completed_session": completed_session,
                "bars": bars, "corporate_actions": _actions(result, completed_session),
                "request_contract": {
                    "interval": "1d", "auto_adjust": False, "actions": True,
                    "prepost": False, "threads": False, "repair": False, "progress": False,
                },
                "status": "PRIMARY_VALIDATED", "order_authority": False,
            }
        except Exception as exc:
            errors.append({"ticker": ticker, "error_type": type(exc).__name__, "message": str(exc)[:160]})
    return {
        "schema_version": "1.0", "generated_at": generated_at,
        "analysis_cutoff": generated_at, "completed_session": completed_session,
        "provider": "yfinance", "provider_role": "PRIMARY_VALIDATED_NOT_OFFICIAL",
        "provider_version": provider_version, "tls_provenance": tls,
        "request_contract": {
            "interval": "1d", "auto_adjust": False, "actions": True,
            "prepost": False, "threads": False, "repair": False,
            "progress": False, "request_mode": "sequential_single_ticker",
            "minimum_request_delay_seconds": 1.0,
        },
        "records": records, "errors": errors,
        "independent_verified": False, "official_close_verified": False,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    validate_shadow_output_path(args.output, args.repo_root, [args.schema])
    value = build_evidence(args.ticker, completed_session=args.completed_session, generated_at=args.generated_at)
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, value)
    print(json.dumps({
        "completed_session": value["completed_session"],
        "validated": len(value["records"]), "errors": len(value["errors"]),
        "provider_role": value["provider_role"], "order_authority": False,
    }, separators=(",", ":")))
    return 0 if not value["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
