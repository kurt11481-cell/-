#!/usr/bin/env python3
"""Create-only scheduled SEC Shadow derived views from immutable SEC runs.

This module performs no network, scheduler, broker, portfolio, policy, or order
operation.  It compares normalized SEC artifacts by ticker and accession number
and writes only new derived-view files beside the current immutable run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sec_official_event_intake import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_RULES_PATH,
    IntakeError,
    PIPELINE_VERSION,
    create_only_json,
    create_only_utf8_dashboard,
    render_dashboard_html,
    render_dashboard_markdown,
    validated_watchlist_groups,
)
from validation_common import file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
SUMMARY_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-scheduled-shadow-summary.schema.json"
ATTEMPT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-scheduled-attempt.schema.json"
SCHEDULE_CONTRACT = ROOT / "manage-us-stock-strategy/assets/sec-scheduled-shadow-contract-v0.1.json"
DEFAULT_ATTEMPT_OUTPUT_ROOT = ROOT / "workspace/outputs/official-event-intake/sec-scheduled-attempts"
SCHEDULED_DASHBOARD_JSON = "scheduled-dashboard.json"
SCHEDULED_DASHBOARD_MARKDOWN = "scheduled-dashboard.md"
SCHEDULED_DASHBOARD_HTML = "scheduled-dashboard.html"
SCHEDULED_ATTEMPT_JSON = "scheduled-attempt.json"
TASK_NAME = "GuardedPortfolio-SEC-Shadow-v0.1"
COMPATIBLE_NETWORK_ACCESS = "SEC_OFFICIAL_ONLY"
COMPATIBLE_EVENT_AUTHORITY = "OFFICIAL_SEC"
ALLOWED_FAILURE_CODES = frozenset({
    "WINDOWS_TIMEZONE_MISMATCH",
    "SEC_USER_AGENT_USER_ENV_REQUIRED",
    "SEC_USER_AGENT_REQUIRED",
    "RUNNER_NOT_FOUND",
    "PYTHON_RUNTIME_NOT_FOUND",
    "SEC_ACCESS_BLOCKED",
    "SEC_RATE_LIMITED",
    "SEC_SOURCE_INVALID",
    "SEC_IDENTITY_CONFLICT",
    "NETWORK_SCOPE_VIOLATION",
    "RUN_COLLISION",
    "PROCESS_ERROR",
})
EARLY_FAILURE_CODES = frozenset({
    "WINDOWS_TIMEZONE_MISMATCH",
    "SEC_USER_AGENT_USER_ENV_REQUIRED",
    "SEC_USER_AGENT_REQUIRED",
    "RUNNER_NOT_FOUND",
    "PYTHON_RUNTIME_NOT_FOUND",
})
ATTEMPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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


def canonical_watchlist() -> list[str]:
    try:
        watchlist, _, _ = validated_watchlist_groups(load_json(DEFAULT_RULES_PATH))
    except IntakeError as exc:
        raise IntakeError("SEC_SOURCE_INVALID", "CANONICAL_WATCHLIST_INVALID") from exc
    return watchlist


def is_canonical_successful_run(run: RunArtifact) -> bool:
    return (
        is_sec_run(run)
        and run.normalized.get("schema_version") == "0.1"
        and run.normalized.get("pipeline_version") == PIPELINE_VERSION
        and run.manifest.get("pipeline_version") == PIPELINE_VERSION
        and run.manifest.get("pipeline_status") in {"PASS", "PARTIAL"}
        and run.manifest.get("watchlist") == canonical_watchlist()
    )


def discover_latest_compatible_successful_run(
    output_root: str | Path,
    exclude_run_id: str | None = None,
) -> tuple[str, RunArtifact | None]:
    compatible: list[RunArtifact] = []
    incompatible_sec_run_found = False
    for path in Path(output_root).resolve().glob("*/*/normalized-events.json"):
        try:
            candidate = load_run_artifact(path.parent)
        except (IntakeError, OSError, ValueError):
            continue
        if exclude_run_id is not None and candidate.run_id == exclude_run_id:
            continue
        if not is_sec_run(candidate):
            continue
        if is_canonical_successful_run(candidate):
            compatible.append(candidate)
        else:
            incompatible_sec_run_found = True
    compatible.sort(key=lambda item: (item.decision_as_of, item.run_id), reverse=True)
    if compatible:
        return "PASS", compatible[0]
    if incompatible_sec_run_found:
        return "PREVIOUS_RUN_INCOMPATIBLE", None
    return "BASELINE_ONLY", None


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
        "pipeline_version": str(current.manifest["pipeline_version"]),
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
        f"PIPELINE_VERSION = {summary['pipeline_version']}",
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


def build_scheduled_dashboard_model(current: RunArtifact, summary: dict[str, Any]) -> dict[str, Any]:
    validation_path = current.run_directory / "validation-report.json"
    company_status: dict[str, str] = {}
    if validation_path.is_file():
        validation = load_json(validation_path)
        if isinstance(validation, dict) and isinstance(validation.get("company_source_status"), dict):
            company_status = {
                str(ticker): str(status) for ticker, status in validation["company_source_status"].items()
            }
    if not company_status:
        company_status = {str(ticker): "PASS" for ticker in current.manifest.get("watchlist", [])}
    context = current.normalized.get("portfolio_context")
    if not isinstance(context, dict):
        context = {"status": "NOT_VERIFIED", "as_of": None}
    return {
        "run_time": str(summary["decision_as_of"]),
        "source_status": str(summary["pipeline_status"]),
        "context": context,
        "lookback_days": int(summary["lookback_days"]),
        "events": list(current.normalized["events"]),
        "ownership_coverage": str(current.normalized.get("ownership_coverage", "NOT_VERIFIED")),
        "company_status": company_status,
        "scheduled_summary": summary,
    }


def write_scheduled_artifacts(output_root: str | Path, current_run_id: str) -> dict[str, Any]:
    current = find_run_by_id(output_root, current_run_id)
    previous_status, previous = discover_previous_run(output_root, current)
    summary = build_summary(current, previous_status, previous)
    json_path = current.run_directory / SCHEDULED_DASHBOARD_JSON
    markdown_path = current.run_directory / SCHEDULED_DASHBOARD_MARKDOWN
    html_path = current.run_directory / SCHEDULED_DASHBOARD_HTML
    if json_path.exists() or markdown_path.exists() or html_path.exists():
        raise IntakeError("RUN_COLLISION", str(current.run_directory))
    model = build_scheduled_dashboard_model(current, summary)
    create_only_json(json_path, summary)
    create_only_utf8_dashboard(markdown_path, render_dashboard_markdown(**model))
    create_only_utf8_dashboard(html_path, render_dashboard_html(model))
    return summary


def latest_known_summary(
    output_root: str | Path,
    failure_code: str,
    exclude_run_id: str | None = None,
) -> dict[str, Any]:
    if failure_code not in ALLOWED_FAILURE_CODES:
        failure_code = "PROCESS_ERROR"
    diff_status, previous = discover_latest_compatible_successful_run(output_root, exclude_run_id)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schedule_status": failure_code,
        "run_started_at": now,
        "run_finished_at": now,
        "decision_as_of": None,
        "previous_run_id": previous.run_id if previous else None,
        "previous_run_as_of": str(previous.normalized["decision_as_of"]) if previous else None,
        "freshness_status": "LAST_KNOWN" if previous else "BASELINE_ONLY",
        "diff_status": diff_status,
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }


def attempt_artifact_path(attempt_output_root: str | Path, attempt_id: str, started_at: str) -> Path:
    if not ATTEMPT_ID_PATTERN.fullmatch(attempt_id):
        raise IntakeError("SEC_SOURCE_INVALID", "ATTEMPT_ID_INVALID")
    date_directory = parse_timestamp(started_at).date().isoformat()
    return Path(attempt_output_root).resolve() / date_directory / attempt_id / SCHEDULED_ATTEMPT_JSON


def assert_attempt_available(attempt_output_root: str | Path, attempt_id: str, started_at: str) -> Path:
    path = attempt_artifact_path(attempt_output_root, attempt_id, started_at)
    if path.exists():
        raise IntakeError("RUN_COLLISION", str(path.parent))
    return path


def build_scheduled_attempt(
    *,
    summary: dict[str, Any],
    attempt_id: str,
    started_at: str,
    attempt_result: str,
    failure_code: str | None,
    network_started: bool,
    sec_live_request_count_if_known: int | None,
    runner_exit_code: int | None,
    user_agent_configured: bool,
    persistent_user_agent_configured: bool,
    timezone_id: str,
    timezone_preflight_status: str,
) -> dict[str, Any]:
    if attempt_result not in {"PASS", "PARTIAL", "FAIL", "BLOCKED"}:
        raise IntakeError("SEC_SOURCE_INVALID", "ATTEMPT_RESULT_INVALID")
    if failure_code is not None and failure_code not in ALLOWED_FAILURE_CODES:
        failure_code = "PROCESS_ERROR"
    if attempt_result in {"PASS", "PARTIAL"}:
        if failure_code is not None or summary.get("freshness_status") != "CURRENT_RUN":
            raise IntakeError("SEC_SOURCE_INVALID", "SUCCESS_ATTEMPT_INVARIANT_INVALID")
        current_run_id = str(summary["run_id"])
    else:
        if failure_code is None or summary.get("freshness_status") == "CURRENT_RUN":
            raise IntakeError("SEC_SOURCE_INVALID", "FAILURE_ATTEMPT_INVARIANT_INVALID")
        current_run_id = None
    if failure_code in EARLY_FAILURE_CODES and network_started:
        raise IntakeError("SEC_SOURCE_INVALID", "EARLY_FAILURE_NETWORK_STATE_INVALID")
    if sec_live_request_count_if_known is not None and sec_live_request_count_if_known < 0:
        raise IntakeError("SEC_SOURCE_INVALID", "REQUEST_COUNT_INVALID")

    attempt = {
        "schema_version": "0.1",
        "attempt_id": attempt_id,
        "task_name": TASK_NAME,
        "started_at": parse_timestamp(started_at).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "attempt_result": attempt_result,
        "failure_code": failure_code,
        "freshness_status": str(summary["freshness_status"]),
        "current_run_id": current_run_id,
        "last_known_run_id": summary.get("previous_run_id"),
        "last_known_run_as_of": summary.get("previous_run_as_of"),
        "diff_status": summary.get("diff_status"),
        "network_started": network_started,
        "sec_live_request_count_if_known": sec_live_request_count_if_known,
        "runner_exit_code": runner_exit_code,
        "scheduler_mode": "SCHEDULED_SHADOW",
        "lookback_days": 7,
        "user_agent_configured": user_agent_configured,
        "persistent_user_agent_configured": persistent_user_agent_configured,
        "timezone_id": timezone_id or "NOT_VERIFIED",
        "timezone_preflight_status": timezone_preflight_status,
        "portfolio_context_status": "NOT_ACCESSED_BY_SCHEDULED_ATTEMPT",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }
    errors = validate_instance(attempt, ATTEMPT_SCHEMA)
    if errors:
        raise IntakeError("SEC_SOURCE_INVALID", "SCHEDULED_ATTEMPT_SCHEMA_INVALID:" + "; ".join(errors))
    return attempt


def write_scheduled_attempt(
    *,
    attempt_output_root: str | Path,
    summary: dict[str, Any],
    attempt_id: str,
    started_at: str,
    attempt_result: str,
    failure_code: str | None,
    network_started: bool,
    sec_live_request_count_if_known: int | None,
    runner_exit_code: int | None,
    user_agent_configured: bool,
    persistent_user_agent_configured: bool,
    timezone_id: str,
    timezone_preflight_status: str,
) -> Path:
    path = assert_attempt_available(attempt_output_root, attempt_id, started_at)
    attempt = build_scheduled_attempt(
        summary=summary,
        attempt_id=attempt_id,
        started_at=started_at,
        attempt_result=attempt_result,
        failure_code=failure_code,
        network_started=network_started,
        sec_live_request_count_if_known=sec_live_request_count_if_known,
        runner_exit_code=runner_exit_code,
        user_agent_configured=user_agent_configured,
        persistent_user_agent_configured=persistent_user_agent_configured,
        timezone_id=timezone_id,
        timezone_preflight_status=timezone_preflight_status,
    )
    create_only_json(path, attempt)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SEC Scheduled Shadow v0.1 derived views")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--attempt-output-root", type=Path, default=DEFAULT_ATTEMPT_OUTPUT_ROOT)
    parser.add_argument("--attempt-id")
    parser.add_argument("--attempt-started-at")
    parser.add_argument("--attempt-result", choices=("PASS", "PARTIAL", "FAIL", "BLOCKED"))
    parser.add_argument("--network-started", choices=("true", "false"))
    parser.add_argument("--sec-live-request-count", type=int)
    parser.add_argument("--runner-exit-code", type=int)
    parser.add_argument("--user-agent-configured", choices=("true", "false"))
    parser.add_argument("--persistent-user-agent-configured", choices=("true", "false"))
    parser.add_argument("--timezone-id", default="NOT_VERIFIED")
    parser.add_argument("--timezone-preflight-status", choices=("PASS", "FAIL", "NOT_VERIFIED"), default="NOT_VERIFIED")
    parser.add_argument("--exclude-run-id")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--current-run-id")
    group.add_argument("--failure-code")
    args = parser.parse_args()
    try:
        attempt_requested = args.attempt_id is not None
        if attempt_requested:
            required_attempt_values = {
                "attempt_started_at": args.attempt_started_at,
                "attempt_result": args.attempt_result,
                "network_started": args.network_started,
                "user_agent_configured": args.user_agent_configured,
                "persistent_user_agent_configured": args.persistent_user_agent_configured,
            }
            missing = sorted(key for key, value in required_attempt_values.items() if value is None)
            if missing:
                raise IntakeError("SEC_SOURCE_INVALID", "ATTEMPT_ARGUMENT_REQUIRED:" + ",".join(missing))
            assert_attempt_available(args.attempt_output_root, args.attempt_id, args.attempt_started_at)
        if args.failure_code:
            result = latest_known_summary(args.output_root, args.failure_code, args.exclude_run_id)
        else:
            result = write_scheduled_artifacts(args.output_root, args.current_run_id)
        if attempt_requested:
            attempt_result = args.attempt_result
            if args.current_run_id and result.get("schedule_status") == "PARTIAL":
                attempt_result = "PARTIAL"
            if args.current_run_id and attempt_result not in {"PASS", "PARTIAL"}:
                raise IntakeError("SEC_SOURCE_INVALID", "CURRENT_RUN_ATTEMPT_RESULT_INVALID")
            if args.failure_code and attempt_result not in {"FAIL", "BLOCKED"}:
                raise IntakeError("SEC_SOURCE_INVALID", "FAILURE_ATTEMPT_RESULT_INVALID")
            write_scheduled_attempt(
                attempt_output_root=args.attempt_output_root,
                summary=result,
                attempt_id=args.attempt_id,
                started_at=args.attempt_started_at,
                attempt_result=attempt_result,
                failure_code=args.failure_code,
                network_started=args.network_started == "true",
                sec_live_request_count_if_known=args.sec_live_request_count,
                runner_exit_code=args.runner_exit_code,
                user_agent_configured=args.user_agent_configured == "true",
                persistent_user_agent_configured=args.persistent_user_agent_configured == "true",
                timezone_id=args.timezone_id,
                timezone_preflight_status=args.timezone_preflight_status,
            )
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
