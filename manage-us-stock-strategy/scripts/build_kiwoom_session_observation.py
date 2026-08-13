#!/usr/bin/env python3
"""Build a read-only, session-aware Kiwoom broker quote snapshot."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from kiwoom_runtime_bridge import invoke_bridge_batch
from session_aware_market_data import kiwoom_broker_quote_observation
from validation_common import load_json, validate_instance


BatchCall = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


def _number(value: Any) -> float | None:
    try:
        result = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def build_session_snapshot(
    tickers: list[str], *, reported_session: str | None, generated_at: str,
    batch_call: BatchCall, explicit_session_type: str | None = None,
) -> dict[str, Any]:
    symbols = list(dict.fromkeys(item.strip().upper() for item in tickers if item.strip()))
    requests = [{"operation": "market_quote", "ticker": ticker, "fx_applied": False} for ticker in symbols]
    responses = batch_call(requests)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for ticker, response in zip(symbols, responses):
        rows = response.get("data") if isinstance(response, dict) else None
        row = rows[0] if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict) else None
        price = _number(row.get("cur_prc")) if row else None
        if response.get("bridge_status") != "PASS" or price is None:
            error = str(response.get("bridge_status") or "QUOTE_UNAVAILABLE")
            if response.get("bridge_status") == "PASS" and price is None:
                error = "QUOTE_FIELD_UNAVAILABLE"
            errors.append({"ticker": ticker, "error": error})
            continue
        records.append(kiwoom_broker_quote_observation(
            ticker=ticker, reported_session=reported_session, price=price,
            provider_timestamp=str(response.get("retrieved_at") or generated_at),
            source_field="cur_prc", explicit_session_type=explicit_session_type,
        ))
    status = "PASS" if len(records) == len(symbols) and symbols else "PARTIAL" if records else "DATA_INCOMPLETE"
    return {
        "schema_version": "1.0", "generated_at": generated_at,
        "reported_session": reported_session, "provider": "KIWOOM_REST",
        "provider_role": "KIWOOM_OPERATIONAL_PRIMARY", "data_status": status,
        "records": records, "errors": errors, "operational_session_increment": 0,
        "quantity_authority": False, "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--reported-session")
    parser.add_argument("--explicit-session-type")
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--readonly-policy", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    readonly = load_json(args.readonly_policy)
    if args.runtime.resolve() != Path(str(readonly["official_runtime_path"])).resolve():
        raise SystemExit("KIWOOM_RUNTIME_PATH_MISMATCH")
    validate_shadow_output_path(args.output, args.repo_root, [args.readonly_policy, args.rate_policy, args.schema])
    rate_policy = load_json(args.rate_policy)
    value = build_session_snapshot(
        args.ticker, reported_session=args.reported_session, generated_at=args.generated_at,
        explicit_session_type=args.explicit_session_type,
        batch_call=lambda requests: invoke_bridge_batch(requests, runtime=args.runtime, policy=rate_policy),
    )
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, value)
    print(json.dumps({"data_status": value["data_status"], "records": len(value["records"]), "errors": len(value["errors"]), "order_authority": False}, separators=(",", ":")))
    return 0 if value["data_status"] != "DATA_INCOMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
