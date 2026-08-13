#!/usr/bin/env python3
"""Validate schema and deterministic semantics for Kiwoom shadow snapshots."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from validation_common import load_json, validate_instance


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_snapshot_semantics(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if snapshot.get("provider_state") != "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED":
        errors.append("Kiwoom provider authority must remain shadow-not-accepted")
    if snapshot.get("primary_provider") != "yfinance":
        errors.append("yfinance must remain Primary")
    if snapshot.get("order_authority") is not False:
        errors.append("order_authority must be false")
    if snapshot.get("operational_shadow_session_increment") != 0:
        errors.append("adapter snapshots must not increment operational Shadow")
    session = snapshot.get("completed_session")
    runtime_commit = snapshot.get("official_runtime_commit")
    has_pass = any(item.get("status") == "PASS" for item in snapshot.get("ticker_results", []))
    if has_pass and (not isinstance(runtime_commit, str) or re.fullmatch(r"[0-9a-f]{40}", runtime_commit) is None):
        errors.append("validated ticker data requires one official runtime commit")
    lock = snapshot.get("session_lock") or {}
    if lock.get("status") != "LOCKED" or lock.get("completed_session") != session:
        errors.append("completed-session lock mismatch")
    for index, item in enumerate(snapshot.get("ticker_results", [])):
        prefix = f"ticker_results[{index}]: "
        if item.get("order_authority") is not False:
            errors.append(prefix + "order_authority must be false")
        identity = item.get("identity")
        if isinstance(identity, dict):
            if identity.get("mapping_guessed") is not False:
                errors.append(prefix + "exchange mapping must never be guessed")
            if identity.get("order_authority") is not False:
                errors.append(prefix + "identity order_authority must be false")
            if item.get("status") == "PASS" and identity.get("official_runtime_commit") != runtime_commit:
                errors.append(prefix + "identity runtime commit mismatch")
        raw = item.get("raw")
        adjusted = item.get("adjusted")
        if raw is adjusted and raw is not None:
            errors.append(prefix + "raw and adjusted series must be separate objects")
        for expected, series in (("RAW", raw), ("ADJUSTED", adjusted)):
            if series is None:
                continue
            if series.get("price_basis") != expected:
                errors.append(prefix + f"{expected} price basis mismatch")
            if series.get("fx_applied") is not False:
                errors.append(prefix + "FX-applied data is prohibited")
            if series.get("completed_session") != session:
                errors.append(prefix + "series session mismatch")
            if series.get("order_authority") is not False:
                errors.append(prefix + "series order_authority must be false")
            for bar_index, bar in enumerate(series.get("bars", [])):
                values = [bar.get(name) for name in ("open", "high", "low", "close", "volume")]
                if not all(_finite(value) for value in values):
                    errors.append(prefix + f"bar {bar_index} has non-finite OHLCV")
                    continue
                if min(values[:4]) <= 0 or values[4] < 0:
                    errors.append(prefix + f"bar {bar_index} has invalid OHLCV sign")
                if values[1] < max(values[0], values[2], values[3]) or values[2] > min(values[0], values[1], values[3]):
                    errors.append(prefix + f"bar {bar_index} violates OHLC invariants")
        if item.get("status") == "PASS":
            if not isinstance(identity, dict) or identity.get("mapping_status") != "VERIFIED":
                errors.append(prefix + "PASS requires verified identity")
            if not raw or not adjusted or raw.get("status") != "PASS" or adjusted.get("status") != "PASS":
                errors.append(prefix + "PASS requires separate valid raw and adjusted series")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    args = parser.parse_args()
    snapshot = load_json(args.snapshot)
    errors = validate_instance(snapshot, args.schema)
    if isinstance(snapshot, dict):
        errors.extend(validate_snapshot_semantics(snapshot))
    result = {"valid": not errors, "errors": errors, "order_authority": False}
    if args.output:
        validate_shadow_output_path(args.output, args.repo_root, [args.snapshot, args.schema])
        atomic_write_json(args.output, result)
    else:
        print("PASS" if not errors else "FAIL\n" + "\n".join(errors))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
