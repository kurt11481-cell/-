#!/usr/bin/env python3
"""Build one terminal-stable Kiwoom MVLL DAILY_VOLUME/RVOL20 lineage."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


def _rvol20(rows: list[dict[str, Any]]) -> float | None:
    ordered = sorted(rows, key=lambda row: str(row.get("session")))
    if len(ordered) < 21:
        return None
    window = ordered[-21:]
    try:
        volumes = [float(row["volume"]) for row in window]
    except (KeyError, TypeError, ValueError):
        return None
    denominator = volumes[:-1]
    return volumes[-1] / (sum(denominator) / 20.0) if sum(denominator) > 0 else None


def _observation(snapshot: dict[str, Any], path: Path) -> dict[str, Any]:
    ticker = next((row for row in snapshot.get("ticker_results") or []
                   if row.get("ticker") == "MVLL"), {})
    identity = ticker.get("identity") or {}
    raw = ticker.get("raw") or {}
    adjusted = ticker.get("adjusted") or {}
    raw_rows = sorted(raw.get("bars") or [], key=lambda row: str(row.get("session")))[-21:]
    adjusted_rows = sorted(adjusted.get("bars") or [], key=lambda row: str(row.get("session")))[-21:]
    pages = (adjusted.get("pagination") or {}).get("pages") or []
    retrieved_at = pages[0].get("retrieved_at") if pages else snapshot.get("generated_at")
    sessions = [str(row.get("session")) for row in adjusted_rows]
    volumes = [row.get("volume") for row in adjusted_rows]
    window_hash = canonical_hash({"sessions": sessions, "volumes": volumes})
    valid = all((
        ticker.get("status") == "PASS",
        identity.get("ticker") == "MVLL",
        identity.get("mapping_status") == "VERIFIED",
        identity.get("mapping_guessed") is False,
        identity.get("source_api_id") == "usa10099",
        raw.get("status") == "PASS",
        adjusted.get("status") == "PASS",
        raw.get("completed_session") == snapshot.get("completed_session"),
        adjusted.get("completed_session") == snapshot.get("completed_session"),
        adjusted.get("price_basis") == "ADJUSTED",
        adjusted.get("fx_applied") is False,
        len(raw_rows) == 21,
        len(adjusted_rows) == 21,
        [str(row.get("session")) for row in raw_rows] == sessions,
        [row.get("volume") for row in raw_rows] == volumes,
        ((adjusted.get("pagination") or {}).get("api_id") == "usa06012"),
        _rvol20(adjusted_rows) is not None,
        isinstance(retrieved_at, str),
    ))
    try:
        display_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        display_path = path.as_posix()
    return {
        "artifact_path": display_path,
        "artifact_sha256": file_hash(path),
        "retrieved_at": retrieved_at,
        "completed_session": snapshot.get("completed_session"),
        "current_session_volume": volumes[-1] if volumes else None,
        "window_hash": window_hash,
        "window_sessions": sessions,
        "window_volumes": volumes,
        "rvol20": _rvol20(adjusted_rows),
        "self_integrity": "VALID" if valid else "INVALID",
    }


def build_lineage(*, snapshots: list[tuple[Path, dict[str, Any]]],
                  diagnostic: dict[str, Any], policy: dict[str, Any],
                  minimum_stable_observations: int = 2) -> dict[str, Any]:
    observations = [_observation(value, path) for path, value in snapshots]
    observations.sort(key=lambda item: str(item.get("retrieved_at")))
    valid = [item for item in observations if item["self_integrity"] == "VALID"]
    terminal: list[dict[str, Any]] = []
    if valid:
        fingerprint = valid[-1]["window_hash"]
        for item in reversed(valid):
            if item["window_hash"] != fingerprint:
                break
            terminal.append(item)
        terminal.reverse()
    terminal_stable = len(terminal) >= minimum_stable_observations
    selected = terminal[-1] if terminal_stable else None
    session = selected.get("completed_session") if selected else None
    threshold = float(policy.get("threshold", diagnostic.get("threshold")))
    canonical_rvol = selected.get("rvol20") if selected else None
    yfinance_rvol = diagnostic.get("yfinance_rvol20")
    for item in observations:
        if item["self_integrity"] != "VALID":
            item["lineage_disposition"] = "SELF_INTEGRITY_INVALID"
        elif selected and item["window_hash"] == selected["window_hash"]:
            item["lineage_disposition"] = "TERMINAL_STABLE_SUPPORT"
        else:
            item["lineage_disposition"] = "BAR_UNSTABLE_SUPERSEDED"
    result = {
        "schema_version": "1.0",
        "lineage_id": "MVLL_CANONICAL_VOLUME_LINEAGE",
        "ticker": "MVLL",
        "provider": "KIWOOM",
        "source_api_id": "usa06012",
        "completed_session": session,
        "market_phase": "REGULAR_COMPLETED",
        "bar_finalized": terminal_stable,
        "finalization_basis": "TERMINAL_STABLE_SUFFIX_SAME_PROVIDER",
        "minimum_stable_observations": minimum_stable_observations,
        "stable_observation_count": len(terminal),
        "source_artifact_sha256": selected.get("artifact_sha256") if selected else None,
        "source_artifact_path": selected.get("artifact_path") if selected else None,
        "price_volume_basis": "ADJUSTED_PRICE_WITH_RAW_EQUAL_DAILY_VOLUME",
        "window_sessions": selected.get("window_sessions") if selected else [],
        "denominator_sessions": (selected.get("window_sessions") or [])[:-1] if selected else [],
        "signal_session": (selected.get("window_sessions") or [None])[-1] if selected else None,
        "formula_version": "RVOL20_SIGNAL_VOLUME_DIV_PRIOR_20_SESSION_MEAN_V1",
        "canonical_rvol20": canonical_rvol,
        "threshold": threshold,
        "yfinance_diagnostic_rvol20": yfinance_rvol,
        "cross_provider_divergence": (
            canonical_rvol - float(yfinance_rvol)
            if canonical_rvol is not None and isinstance(yfinance_rvol, (int, float)) else None
        ),
        "divergence_blocking": False,
        "volume_authority_status": "KIWOOM_VALID_SCOPED" if terminal_stable else "KIWOOM_LINEAGE_UNVERIFIED",
        "technical_condition_status": (
            "READY" if terminal_stable and canonical_rvol >= threshold
            else "RVOL20_NOT_MET" if terminal_stable else "NOT_EVALUATED"
        ),
        "lineage_classification": "DATA_CORRECTION",
        "semantic_change": False,
        "observations": observations,
        "quantity": None,
        "quantity_authority": "none",
        "order_authority": False,
        "record_hash": "0" * 64,
    }
    result["record_hash"] = canonical_hash({key: value for key, value in result.items()
                                             if key != "record_hash"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", action="append", required=True, type=Path)
    parser.add_argument("--diagnostic", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-stable-observations", type=int, default=2)
    args = parser.parse_args()
    value = build_lineage(
        snapshots=[(path, load_json(path)) for path in args.snapshot],
        diagnostic=load_json(args.diagnostic),
        policy=load_json(args.policy),
        minimum_stable_observations=max(2, args.minimum_stable_observations),
    )
    errors = validate_instance(value, args.schema)
    if errors or value["volume_authority_status"] != "KIWOOM_VALID_SCOPED":
        raise SystemExit("MVLL_CANONICAL_VOLUME_LINEAGE_INVALID:" + ";".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, value)
    print("MVLL_CANONICAL_VOLUME_LINEAGE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
