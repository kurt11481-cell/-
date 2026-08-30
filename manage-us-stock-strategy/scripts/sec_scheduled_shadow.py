#!/usr/bin/env python3
"""Create-only scheduled SEC Shadow derived views from immutable SEC runs.

This module performs no network, scheduler, broker, portfolio, policy, or order
operation.  It compares normalized SEC artifacts by ticker and accession number
and writes only new derived-view files beside the current immutable run.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sec_official_event_intake import (
    DEFAULT_OUTPUT_ROOT,
    IntakeError,
    create_only_json,
    create_only_write,
)
from validation_common import file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
SUMMARY_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-scheduled-shadow-summary.schema.json"
SCHEDULE_CONTRACT = ROOT / "manage-us-stock-strategy/assets/sec-scheduled-shadow-contract-v0.1.json"
SCHEDULED_DASHBOARD_JSON = "scheduled-dashboard.json"
SCHEDULED_DASHBOARD_MARKDOWN = "scheduled-dashboard.md"
COMPATIBLE_NETWORK_ACCESS = "SEC_OFFICIAL_ONLY"
COMPATIBLE_EVENT_AUTHORITY = "OFFICIAL_SEC"
ALLOWED_FAILURE_CODES = frozenset({
    "SEC_USER_AGENT_REQUIRED",
    "SEC_ACCESS_BLOCKED",
    "SEC_RATE_LIMITED",
    "SEC_SOURCE_INVALID",
    "SEC_IDENTITY_CONFLICT",
    "NETWORK_SCOPE_VIOLATION",
    "RUN_COLLISION",
    "PROCESS_ERROR",
})


@dataclass(frozen=True)
class RunArtifact:
    run_directory: Path
    normalized: dict[str, Any]
    manifest: dict[str, Any]

    @property
    def run_id(self) -> str:
        return str(self.manifest["run_id"])

    @property
    def decision_as_of(self) -> datetime:
        return parse_timestamp(str(self.normalized["decision_as_of"]))


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise IntakeError("SEC_SOURCE_INVALID", "INVALID_DECISION_AS_OF") from exc
    if parsed.tzinfo is None:
        raise IntakeError("SEC_SOURCE_INVALID", "DECISION_AS_OF_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def load_run_artifact(run_directory: str | Path) -> RunArtifact:
    directory = Path(run_directory).resolve()
    normalized_path = directory / "normalized-events.json"
    manifest_path = directory / "run-manifest.json"
    if not normalized_path.is_file() or not manifest_path.is_file():
        raise IntakeError("SEC_SOURCE_INVALID", f"INCOMPLETE_RUN_ARTIFACT:{directory}")
    normalized = load_json(normalized_path)
    manifest = load_json(manifest_path)
    if not isinstance(normalized, dict) or not isinstance(manifest, dict):
        raise IntakeError("SEC_SOURCE_INVALID", f"INVALID_RUN_ARTIFACT:{directory}")
    if manifest.get("run_id") != directory.name:
        raise IntakeError("SEC_SOURCE_INVALID", f"RUN_ID_DIRECTORY_MISMATCH:{directory}")
    return RunArtifact(directory, normalized, manifest)


def find_run_by_id(output_root: str | Path, run_id: str) -> RunArtifact:
    matches = list(Path(output_root).resolve().glob(f"*/{run_id}/normalized-events.json"))
    if len(matches) != 1:
        code = "PREVIOUS_RUN_NOT_FOUND" if not matches else "RUN_COLLISION"
        raise IntakeError(code, run_id)
    return load_run_artifact(matches[0].parent)


def is_sec_run(run: RunArtifact) -> bool:
    events = run.normalized.get("events")
    return (
        run.manifest.get("network_access") == COMPATIBLE_NETWORK_ACCESS
        and isinstance(events, list)
        and all(
            isinstance(event, dict) and event.get("source_authority") == COMPATIBLE_EVENT_AUTHORITY
            for event in events
        )
    )


def runs_are_compatible(current: RunArtifact, previous: RunArtifact) -> bool:
    return (
        is_sec_run(current)
        and is_sec_run(previous)
        and current.normalized.get("schema_version") == previous.normalized.get("schema_version")
        and current.normalized.get("pipeline_version") == previous.normalized.get("pipeline_version")
        and current.manifest.get("pipeline_version") == previous.manifest.get("pipeline_version")
        and current.manifest.get("watchlist") == previous.manifest.get("watchlist")
    )


def discover_previous_run(
    output_root: str | Path,
    current: RunArtifact,
) -> tuple[str, RunArtifact | None]:
    prior_candidates: list[RunArtifact] = []
    for path in Path(output_root).resolve().glob("*/*/normalized-events.json"):
        if path.parent == current.run_directory:
            continue
        try:
            candidate = load_run_artifact(path.parent)
        except (IntakeError, OSError, ValueError):
            continue
        if candidate.decision_as_of < current.decision_as_of:
            prior_candidates.append(candidate)
    prior_candidates.sort(key=lambda item: (item.decision_as_of, item.run_id), reverse=True)
    for candidate in prior_candidates:
        if runs_are_compatible(current, candidate):
            return "PASS", candidate
    if prior_candidates:
        return "PREVIOUS_RUN_INCOMPATIBLE", None
    return "BASELINE_ONLY", None


def filing_identity(event: dict[str, Any]) -> tuple[str, str]:
    ticker = str(event.get("ticker", "")).strip()
    accession = str(event.get("accession_number", "")).strip()
    if not ticker or not accession:
        raise IntakeError("SEC_SOURCE_INVALID", "MISSING_FILING_IDENTITY")
    return ticker, accession


def derive_accession_diff(
    current_events: list[dict[str, Any]],
    previous_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    previous_identities = {filing_identity(event) for event in previous_events}
    return [event for event in current_events if filing_identity(event) not in previous_identities]


def build_summary(
    current: RunArtifact,
    previous_status: str,
    previous: RunArtifact | None,
) -> dict[str, Any]:
    current_events = current.normalized.get("events")
    if not isinstance(current_events, list) or not all(isinstance(event, dict) for event in current_events):
        raise IntakeError("SEC_SOURCE_INVALID", "CURRENT_EVENTS_INVALID")
    if not is_sec_run(current):
        raise IntakeError("SEC_SOURCE_INVALID", "CURRENT_RUN_NOT_SEC")
    new_events: list[dict[str, Any]] | None = None
    if previous_status == "PASS" and previous is not None:
        previous_events = previous.normalized.get("events")
        if not isinstance(previous_events, list) or not all(isinstance(event, dict) for event in previous_events):
            raise IntakeError("SEC_SOURCE_INVALID", "PREVIOUS_EVENTS_INVALID")
        new_events = derive_accession_diff(current_events, previous_events)
    pipeline_status = str(current.manifest.get("pipeline_status", ""))
    if pipeline_status not in {"PASS", "PARTIAL"}:
        raise IntakeError("SEC_SOURCE_INVALID", "CURRENT_PIPELINE_STATUS_INVALID")
    if pipeline_status == "PARTIAL":
        schedule_status = "PARTIAL"
    elif new_events is not None and not new_events:
        schedule_status = "NO_NEW_FILINGS"
    else:
        schedule_status = "PASS"
    summary = {
        "schema_version": "0.1",
        "run_mode": "SCHEDULED_SHADOW",
        "run_id": current.run_id,
        "schedule_status": schedule_status,
        "pipeline_status": pipeline_status,
        "run_started_at": str(current.manifest["started_at"]),
        "run_finished_at": str(current.manifest["finished_at"]),
        "decision_as_of": str(current.normalized["decision_as_of"]),
        "freshness_status": "CURRENT_RUN",
        "filings_in_lookback_window": len(current_events),
        "high_filings_in_lookback_window": sum(event.get("materiality") == "HIGH" for event in current_events),
        "previous_run_id": previous.run_id if previous else None,
        "previous_run_as_of": str(previous.normalized["decision_as_of"]) if previous else None,
        "diff_status": previous_status,
        "new_since_previous_count": len(new_events) if new_events is not None else None,
        "new_high_since_previous_count": (
            sum(event.get("materiality") == "HIGH" for event in new_events)
            if new_events is not None else None
        ),
        "diff_identity": "ticker+accession_number",
        "lookback_days": int(current.normalized["lookback_days"]),
        "watchlist": list(current.manifest["watchlist"]),
        "source": "SEC",
        "schedule_contract_sha256": file_hash(SCHEDULE_CONTRACT),
        "current_normalized_sha256": file_hash(current.run_directory / "normalized-events.json"),
        "current_run_manifest_sha256": file_hash(current.run_directory / "run-manifest.json"),
        "previous_normalized_sha256": (
            file_hash(previous.run_directory / "normalized-events.json") if previous else None
        ),
        "previous_run_manifest_sha256": (
            file_hash(previous.run_directory / "run-manifest.json") if previous else None
        ),
        "user_agent_source": "ENVIRONMENT_VARIABLE",
        "plaintext_artifact_storage": False,
        "historical_artifact_mutation": False,
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }
    errors = validate_instance(summary, SUMMARY_SCHEMA)
    if errors:
        raise IntakeError("SEC_SOURCE_INVALID", "SCHEDULED_SUMMARY_SCHEMA_INVALID:" + "; ".join(errors))
    return summary


def render_scheduled_dashboard(summary: dict[str, Any]) -> str:
    def display(value: Any) -> str:
        return "NOT_APPLICABLE" if value is None else str(value)

    return "\n".join([
        "# SEC SCHEDULED SHADOW DERIVED VIEW",
        "",
        "This file is a create-only derived view. It does not mutate historical SEC evidence.",
        "",
        f"SCHEDULE_STATUS = {summary['schedule_status']}",
        f"PIPELINE_STATUS = {summary['pipeline_status']}",
        f"RUN_ID = {summary['run_id']}",
        f"RUN_STARTED_AT = {summary['run_started_at']}",
        f"RUN_FINISHED_AT = {summary['run_finished_at']}",
        f"DECISION_AS_OF = {summary['decision_as_of']}",
        f"FRESHNESS_STATUS = {summary['freshness_status']}",
        f"FILINGS_IN_LOOKBACK_WINDOW = {summary['filings_in_lookback_window']}",
        f"HIGH_FILINGS_IN_LOOKBACK_WINDOW = {summary['high_filings_in_lookback_window']}",
        f"PREVIOUS_RUN_ID = {display(summary['previous_run_id'])}",
        f"PREVIOUS_RUN_AS_OF = {display(summary['previous_run_as_of'])}",
        f"DIFF_STATUS = {summary['diff_status']}",
        f"NEW_SINCE_PREVIOUS_COUNT = {display(summary['new_since_previous_count'])}",
        f"NEW_HIGH_SINCE_PREVIOUS_COUNT = {display(summary['new_high_since_previous_count'])}",
        "DIFF_IDENTITY = ticker+accession_number",
        "USER_AGENT_SOURCE = ENVIRONMENT_VARIABLE",
        "PLAINTEXT_ARTIFACT_STORAGE = NO",
        "ORDER_AUTHORITY = FALSE",
        "EXECUTION_QUANTITY = NULL",
        "AUTOMATIC_ORDER = FALSE",
        "",
    ])


def write_scheduled_artifacts(output_root: str | Path, current_run_id: str) -> dict[str, Any]:
    current = find_run_by_id(output_root, current_run_id)
    previous_status, previous = discover_previous_run(output_root, current)
    summary = build_summary(current, previous_status, previous)
    json_path = current.run_directory / SCHEDULED_DASHBOARD_JSON
    markdown_path = current.run_directory / SCHEDULED_DASHBOARD_MARKDOWN
    if json_path.exists() or markdown_path.exists():
        raise IntakeError("RUN_COLLISION", str(current.run_directory))
    create_only_json(json_path, summary)
    create_only_write(markdown_path, render_scheduled_dashboard(summary))
    return summary


def latest_known_summary(output_root: str | Path, failure_code: str) -> dict[str, Any]:
    if failure_code not in ALLOWED_FAILURE_CODES:
        failure_code = "PROCESS_ERROR"
    candidates: list[RunArtifact] = []
    for path in Path(output_root).resolve().glob("*/*/normalized-events.json"):
        try:
            candidate = load_run_artifact(path.parent)
        except (IntakeError, OSError, ValueError):
            continue
        if is_sec_run(candidate):
            candidates.append(candidate)
    candidates.sort(key=lambda item: (item.decision_as_of, item.run_id), reverse=True)
    previous = candidates[0] if candidates else None
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schedule_status": failure_code,
        "run_started_at": now,
        "run_finished_at": now,
        "decision_as_of": None,
        "previous_run_id": previous.run_id if previous else None,
        "previous_run_as_of": str(previous.normalized["decision_as_of"]) if previous else None,
        "freshness_status": "LAST_KNOWN" if previous else "BASELINE_ONLY",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SEC Scheduled Shadow v0.1 derived views")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--current-run-id")
    group.add_argument("--failure-code")
    args = parser.parse_args()
    try:
        if args.failure_code:
            result = latest_known_summary(args.output_root, args.failure_code)
        else:
            result = write_scheduled_artifacts(args.output_root, args.current_run_id)
    except (IntakeError, FileExistsError, OSError, ValueError, KeyError) as exc:
        code = exc.code if isinstance(exc, IntakeError) else "PROCESS_ERROR"
        print(json.dumps({
            "schedule_status": code,
            "freshness_status": "LAST_KNOWN",
            "order_authority": False,
        }, separators=(",", ":")), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
