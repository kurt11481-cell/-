#!/usr/bin/env python3
"""Validate the user-approved MVLL Kiwoom DAILY_VOLUME/RVOL20 scope."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


def _without_hash(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "record_hash"}


def _rvol20(rows: list[dict[str, Any]]) -> float | None:
    ordered = sorted(rows, key=lambda row: str(row.get("session") or row.get("bar_date")))
    if len(ordered) < 21:
        return None
    volumes = [float(row["volume"]) for row in ordered[-21:] if isinstance(row.get("volume"), (int, float))]
    if len(volumes) != 21 or sum(volumes[:-1]) <= 0:
        return None
    return volumes[-1] / (sum(volumes[:-1]) / 20.0)


def build_acceptance(*, kiwoom: dict[str, Any], yfinance: dict[str, Any], policy: dict[str, Any],
                     alert_policy: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    ticker = next((row for row in kiwoom.get("ticker_results") or [] if row.get("ticker") == "MVLL"), {})
    identity = ticker.get("identity") or {}
    adjusted = ticker.get("adjusted") or {}
    raw = ticker.get("raw") or {}
    krows = sorted(adjusted.get("bars") or [], key=lambda row: str(row.get("session")))
    raw_rows = sorted(raw.get("bars") or [], key=lambda row: str(row.get("session")))
    yrow = (yfinance.get("symbols") or {}).get("MVLL") or {}
    yrows = sorted(yrow.get("timing_window") or [], key=lambda row: str(row.get("bar_date")))
    k_window = krows[-21:]
    raw_window = raw_rows[-21:]
    y_window = yrows[-21:]
    k_sessions = [str(row.get("session")) for row in k_window]
    y_sessions = [str(row.get("bar_date")) for row in y_window]
    duplicates = len(k_sessions) - len(set(k_sessions))
    expected_count = int(policy["window_sessions"]) + 1
    missing = max(0, expected_count - len(set(k_sessions)))
    raw_adjusted_match = (
        [str(row.get("session")) for row in raw_window] == k_sessions
        and [row.get("volume") for row in raw_window] == [row.get("volume") for row in k_window]
    )
    threshold = float(alert_policy["holding_timing_rules"]["definitions"]["pullback_reclaim_relative_volume_minimum"])
    krvol, yrvol = _rvol20(k_window), _rvol20([
        {"session": row.get("bar_date"), "volume": row.get("volume")} for row in y_window
    ])
    session = str(kiwoom.get("completed_session"))
    identity_valid = (
        identity.get("ticker") == "MVLL" and identity.get("mapping_status") == "VERIFIED"
        and identity.get("mapping_guessed") is False and identity.get("source_api_id") == "usa10099"
    )
    corporate_action_clear = yrow.get("corporate_action_unresolved") is False
    valid = all((
        ticker.get("status") == "PASS", adjusted.get("status") == "PASS",
        adjusted.get("price_basis") == "ADJUSTED", adjusted.get("fx_applied") is False,
        adjusted.get("completed_session") == session, yrow.get("bar_date") == session,
        identity_valid, len(k_window) == expected_count, len(y_window) == expected_count,
        k_sessions == y_sessions, duplicates == 0, missing == 0, raw_adjusted_match,
        corporate_action_clear, krvol is not None, yrvol is not None,
    ))
    result = {
        "schema_version": "1.0", "ticker": "MVLL", "data_class": "DAILY_VOLUME",
        "decision_class": "RVOL20", "market_session": session,
        "acceptance_status": "VALID" if valid else "INVALID",
        "volume_authority_status": "KIWOOM_VALID_SCOPED" if valid else "UNRESOLVED",
        "technical_condition_status": ("READY" if valid and krvol >= threshold else
                                       "RVOL20_NOT_MET" if valid else "INVALID"),
        "kiwoom_rvol20": krvol, "yfinance_rvol20": yrvol, "threshold": threshold,
        "same_session_window": k_sessions == y_sessions,
        "volume_semantics": policy["volume_semantics"],
        "identity_status": "VERIFIED" if identity_valid else "INVALID",
        "missing_bar_count": missing, "duplicate_session_count": duplicates,
        "raw_adjusted_volume_match": raw_adjusted_match,
        "corporate_action_status": "NO_UNRESOLVED_ACTION" if corporate_action_clear else "AMBIGUOUS",
        "source_artifacts": source_hashes,
        "diagnostic_divergence": (krvol - yrvol) if krvol is not None and yrvol is not None else None,
        "blocking": False, "volume_averaged": False, "record_hash": "0" * 64,
        "quantity": None, "quantity_authority": "none", "order_authority": False,
    }
    result["record_hash"] = canonical_hash(_without_hash(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kiwoom", required=True, type=Path)
    parser.add_argument("--yfinance", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--alert-policy", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build_acceptance(
        kiwoom=load_json(args.kiwoom), yfinance=load_json(args.yfinance),
        policy=load_json(args.policy), alert_policy=load_json(args.alert_policy),
        source_hashes={"kiwoom": file_hash(args.kiwoom), "yfinance": file_hash(args.yfinance),
                       "policy": file_hash(args.policy), "alert_policy": file_hash(args.alert_policy)},
    )
    errors = validate_instance(result, args.schema)
    if errors or result["acceptance_status"] != "VALID":
        raise SystemExit("MVLL_VOLUME_AUTHORITY_INVALID:" + ";".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print("MVLL_VOLUME_AUTHORITY_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
