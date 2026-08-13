#!/usr/bin/env python3
"""Resolve a U.S. ticker from sanitized Kiwoom identity evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from validation_common import canonical_hash, load_json, validate_instance


STATUSES = {"VERIFIED", "AMBIGUOUS", "NOT_FOUND", "API_UNAVAILABLE", "IDENTITY_MISMATCH"}
US_EXCHANGE_CODES = {"NA", "ND", "NY"}


def _rows(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def resolve_instrument(
    ticker: str,
    *,
    stock_rows: list[dict[str, Any]],
    exchange_rows: list[dict[str, Any]],
    etf_rows: list[dict[str, Any]],
    runtime_commit: str,
    verified_at: str,
    api_available: bool = True,
) -> dict[str, Any]:
    symbol = ticker.strip().upper()
    if not api_available:
        core = {
            "ticker": symbol, "mapping_status": "API_UNAVAILABLE",
            "stex_tp": None, "security_name": None, "instrument_class": None,
            "source_api_id": None, "verified_at": verified_at,
            "official_runtime_commit": runtime_commit, "mapping_guessed": False,
            "order_authority": False,
        }
        return {**core, "mapping_hash": canonical_hash(core)}
    primary = [row for row in _rows(stock_rows) if str(row.get("stk_cd", "")).strip().upper() == symbol]
    source_api_id = "usa10099"
    if not primary:
        primary = [row for row in _rows(exchange_rows) if str(row.get("stk_cd", "")).strip().upper() == symbol]
        source_api_id = "usa10098"
    unique = {
        (str(row.get("stk_cd", "")).strip().upper(), str(row.get("stex_tp", "")).strip().upper()): row
        for row in primary if row.get("stk_cd") and row.get("stex_tp")
    }
    invalid_exchange = any(exchange not in US_EXCHANGE_CODES for _, exchange in unique)
    etf_matches = [row for row in _rows(etf_rows) if str(row.get("code", "")).strip().upper() == symbol]
    status = "NOT_FOUND"
    stex_tp: str | None = None
    name: str | None = None
    instrument_class: str | None = None
    if invalid_exchange:
        status = "IDENTITY_MISMATCH"
    elif len(unique) > 1:
        status = "AMBIGUOUS"
    elif len(unique) == 1:
        (_, stex_tp), row = next(iter(unique.items()))
        etf_exchanges = {str(item.get("stex_tp", "")).strip().upper() for item in etf_matches if item.get("stex_tp")}
        identity_is_etf = str(row.get("isEtf", "")).strip().upper() == "Y"
        if etf_exchanges and stex_tp not in etf_exchanges:
            status = "IDENTITY_MISMATCH"
        else:
            status = "VERIFIED"
        name = str(row.get("stk_enm") or row.get("stk_nm") or "").strip() or None
        instrument_class = "ETF" if identity_is_etf or etf_matches else "STOCK_OR_OTHER"
    core = {
        "ticker": symbol,
        "mapping_status": status,
        "stex_tp": stex_tp,
        "security_name": name,
        "instrument_class": instrument_class,
        "source_api_id": source_api_id if primary else None,
        "verified_at": verified_at,
        "official_runtime_commit": runtime_commit,
        "mapping_guessed": False,
        "order_authority": False,
    }
    return {**core, "mapping_hash": canonical_hash(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--stock-evidence", required=True, type=Path)
    parser.add_argument("--exchange-evidence", required=True, type=Path)
    parser.add_argument("--etf-evidence", required=True, type=Path)
    parser.add_argument("--runtime-commit", required=True)
    parser.add_argument("--verified-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate_shadow_output_path(args.output, args.repo_root, [args.stock_evidence, args.exchange_evidence, args.etf_evidence, args.schema])
    result = resolve_instrument(
        args.ticker,
        stock_rows=load_json(args.stock_evidence),
        exchange_rows=load_json(args.exchange_evidence),
        etf_rows=load_json(args.etf_evidence),
        runtime_commit=args.runtime_commit,
        verified_at=args.verified_at,
    )
    errors = validate_instance(result, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output, result)
    return 0 if result["mapping_status"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
