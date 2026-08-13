#!/usr/bin/env python3
"""Cohort-based, append-only v2.6 operational Shadow acceptance ledger."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from validation_common import canonical_hash, file_hash


REQUIRED_BASELINE_TICKERS = ("NBIS", "MVLL", "SOXL")
SEMANTIC_DEFAULTS = (
    "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json",
    "manage-us-stock-strategy/schemas/compiled-holding-research-context.schema.json",
    "manage-us-stock-strategy/schemas/raw-web-close-evidence.schema.json",
    "manage-us-stock-strategy/scripts/holding_research.py",
    "manage-us-stock-strategy/scripts/web_close_evidence.py",
    "manage-us-stock-strategy/scripts/price_evidence.py",
    "manage-us-stock-strategy/scripts/build_price_crosscheck_queue.py",
    "manage-us-stock-strategy/scripts/build_new_buy_strategy_draft.py",
    "manage-us-stock-strategy/scripts/build_new_buy_approval_proposal.py",
    "manage-us-stock-strategy/scripts/staged_promotion.py",
    "manage-us-stock-strategy/scripts/shadow_acceptance.py",
    "workspace/policies/holding_research_baseline_policy.json",
    "workspace/policies/web_completed_close_evidence_policy.json",
    "workspace/policies/shadow_acceptance_policy.json",
)
ROUTE_REGISTRY_PATH = "workspace/policies/web_completed_close_route_registry.json"


def semantic_fingerprint(root: Path, paths: Iterable[str] = SEMANTIC_DEFAULTS) -> str:
    payload: dict[str, str | None] = {}
    for relative in sorted(paths):
        path = root / relative
        payload[relative.replace("\\", "/")] = file_hash(path) if path.is_file() else None
    alert_path = root / "stock-strategy-system/alert_policy.json"
    registry_path = root / "workspace/policies/instrument_registry.json"
    route_registry_path = root / ROUTE_REGISTRY_PATH
    if alert_path.is_file():
        alert = json.loads(alert_path.read_text(encoding="utf-8"))
        payload["approved_alert_policy_semantics"] = canonical_hash({
            "strategy_version": alert.get("strategy_version"),
            "holding_risk_rules": alert.get("holding_risk_rules"),
            "holding_timing_rules": alert.get("holding_timing_rules"),
            "quantity_authority": alert.get("quantity_authority"),
            "order_authority": alert.get("order_authority"),
        })
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        instruments = registry.get("instruments") or {}
        payload["leveraged_confirmation_semantics"] = canonical_hash({
            ticker: {
                "research_instrument_type": (instruments.get(ticker) or {}).get("research_instrument_type"),
                "confirmation_mode": (instruments.get(ticker) or {}).get("confirmation_mode"),
                "confirmation_proxy": (instruments.get(ticker) or {}).get("confirmation_proxy"),
            }
            for ticker in ("MVLL", "SOXL")
        })
    if route_registry_path.is_file():
        route_registry = json.loads(route_registry_path.read_text(encoding="utf-8"))
        stable_fields = (
            "route_id", "ticker_scope", "exchange_scope", "instrument_class_scope", "source_type",
            "source_domain", "source_url_template", "price_basis", "source_field_label", "currency",
            "authentication_requirement", "route_fingerprint",
        )
        payload["web_route_semantics"] = canonical_hash({
            "registry_version": route_registry.get("registry_version"),
            "routes": [{key: route.get(key) for key in stable_fields} for route in route_registry.get("routes", [])],
        })
    return canonical_hash(payload)


def cohort_id(fingerprint: str) -> str:
    return f"integrated-shadow-{fingerprint[:16]}"


def initial_progress(fingerprint: str, started_at: str) -> dict[str, Any]:
    return {
        "schema_version": "2.6", "cohort_id": cohort_id(fingerprint),
        "semantic_fingerprint": fingerprint, "started_at": started_at,
        "observed_attempts": 0, "valid_shadow_sessions": 0, "excluded_attempts": 0,
        "critical_violations": [], "counted_sessions": [],
        "baseline_overlay_sessions": {ticker: 0 for ticker in REQUIRED_BASELINE_TICKERS},
        "independent_price_covered_sessions": 0, "missing_expected_sessions": [],
        "last_attempt_hash": None, "checkpoint_status": "FIRST_VALID_SESSION_PENDING",
        "promotion_status": "EXPLICIT_USER_APPROVAL_REQUIRED", "order_authority": False,
    }


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, str, Any, dict[str, Any] | None]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield path, str(key), child, value
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def critical_violations(report: dict[str, Any], *, portfolio_hash_before: str,
                        portfolio_hash_after: str) -> list[str]:
    violations: list[str] = []
    if portfolio_hash_before.lower() != portfolio_hash_after.lower():
        violations.append("PORTFOLIO_STATE_MUTATED")
    for path, key, value, parent in _walk(report):
        if key == "order_authority" and value is not False:
            violations.append(f"ORDER_AUTHORITY_TRUE:{path}")
        if key == "quantity" and value is not None:
            authority = parent.get("quantity_authority") if isinstance(parent, dict) else None
            if authority != "deterministic_existing_policy":
                violations.append(f"UNAPPROVED_NON_NULL_QUANTITY:{path}")
        if key in {"fill", "fills", "fill_price", "fill_date", "tranche_consumed"} and value is not None and value is not False and value != [] and value != {}:
            confirmed = parent.get("user_confirmed") is True if isinstance(parent, dict) else False
            if not confirmed:
                violations.append(f"FILL_INFERENCE_WITHOUT_CONFIRMATION:{path}.{key}")
    if report.get("historical_alert_replay") is True:
        violations.append("HISTORICAL_ALERT_REPLAY")
    if report.get("duplicate_urgent_delivery") is True:
        violations.append("DUPLICATE_URGENT_DELIVERY")
    if report.get("cross_ticker_failure_propagation") is True:
        violations.append("CROSS_TICKER_FAILURE_PROPAGATION")
    flag_map = {
        "broker_extraction_applied_without_user_confirmation": "BROKER_EXTRACTION_APPLIED_WITHOUT_USER_CONFIRMATION",
        "policy_threshold_changed_during_run": "POLICY_THRESHOLD_CHANGED_DURING_RUN",
        "incomplete_baseline_produced_hold": "INCOMPLETE_BASELINE_PRODUCED_HOLD",
        "stale_baseline_technical_reused": "STALE_BASELINE_TECHNICAL_REUSED",
        "stale_baseline_portfolio_fit_reused": "STALE_BASELINE_PORTFOLIO_FIT_REUSED",
        "llm_raw_strategy_signal_used": "LLM_RAW_STRATEGY_SIGNAL_USED",
    }
    for flag, violation in flag_map.items():
        if report.get(flag) is True:
            violations.append(violation)
    leveraged = report.get("leveraged_separation") or {}
    soxl = leveraged.get("SOXL") or {}
    mvll = leveraged.get("MVLL") or {}
    if soxl and (soxl.get("confirmation_mode") != "DIRECTION_ONLY" or soxl.get("product_close_substitution") is not False):
        violations.append("SOXL_PRODUCT_PROXY_SEPARATION_FAILED")
    if soxl.get("proxy_times_multiple_used_as_direct_validation") is True:
        violations.append("SOXX_MULTIPLE_USED_AS_SOXL_CLOSE")
    if mvll and (mvll.get("confirmation_mode") != "DAILY_MULTIPLE" or mvll.get("product_close_substitution") is not False):
        violations.append("MVLL_PRODUCT_UNDERLYING_SEPARATION_FAILED")
    if mvll.get("underlying_used_as_product_close") is True:
        violations.append("MRVL_USED_AS_MVLL_CLOSE")
    price = report.get("price_evidence") or {}
    if price.get("shadow_crosscheck_status") == "MATCH" and price.get("live_execution_upgraded") is True:
        violations.append("SHADOW_MATCH_PROMOTED_LIVE_EXECUTION")
    return list(dict.fromkeys(violations))


def classify_attempt(raw: dict[str, Any], *, progress: dict[str, Any]) -> dict[str, Any]:
    attempt = deepcopy(raw)
    exclusions: list[str] = []
    violations = critical_violations(attempt.get("report") or {},
                                    portfolio_hash_before=str(attempt.get("portfolio_hash_before") or ""),
                                    portfolio_hash_after=str(attempt.get("portfolio_hash_after") or ""))
    if attempt.get("attempt_type") != "SCHEDULED_POST_MARKET":
        exclusions.append(f"ATTEMPT_TYPE_EXCLUDED:{attempt.get('attempt_type')}")
    if attempt.get("run_phase") != "POST_MARKET":
        exclusions.append("RUN_PHASE_NOT_POST_MARKET")
    if attempt.get("automation_name") != "Morning Portfolio Strategy":
        exclusions.append("AUTOMATION_NAME_MISMATCH")
    if attempt.get("official_session_status") != "VALIDATED":
        exclusions.append("OFFICIAL_SESSION_NOT_VALIDATED")
    if attempt.get("expected_scheduled_session") is not True:
        exclusions.append("STALE_OR_UNEXPECTED_SESSION")
    if attempt.get("delivery_status") != "DELIVERED" or not attempt.get("delivery_id"):
        exclusions.append("DELIVERY_NOT_VERIFIED")
    if attempt.get("branch") != "main":
        exclusions.append("NOT_COMMITTED_MAIN")
    if attempt.get("working_tree_clean") is not True:
        exclusions.append("WORKING_TREE_NOT_CLEAN")
    if attempt.get("deployment_status") != "PASS":
        exclusions.append("DEPLOYMENT_NOT_VALIDATED")
    if attempt.get("registry_status") != "VALIDATED":
        exclusions.append("REGISTRY_NOT_VALIDATED")
    for ticker in REQUIRED_BASELINE_TICKERS:
        if (attempt.get("baseline_coverage") or {}).get(ticker) != "VALIDATED_SHADOW":
            exclusions.append(f"BASELINE_COVERAGE_INCOMPLETE:{ticker}")
    if not attempt.get("run_manifest_hash") or not attempt.get("report_hash"):
        exclusions.append("REQUIRED_ARTIFACT_HASH_MISSING")
    session = attempt.get("completed_session")
    if not session:
        exclusions.append("COMPLETED_SESSION_MISSING")
    elif session in progress.get("counted_sessions", []):
        exclusions.append("DUPLICATE_SESSION")
    if attempt.get("historical_backfill") is True:
        violations.append("HISTORICAL_BACKFILL_PROHIBITED")
    if violations:
        exclusions.append("CRITICAL_VIOLATION")
    attempt["schema_version"] = "2.6"
    attempt["order_authority"] = False
    attempt["critical_violations"] = violations
    attempt["exclusion_reasons"] = list(dict.fromkeys(exclusions))
    attempt["counts_as_valid_session"] = not exclusions and not violations
    attempt["previous_attempt_hash"] = progress.get("last_attempt_hash")
    payload = {key: value for key, value in attempt.items() if key not in {"attempt_hash", "report"}}
    attempt["attempt_hash"] = canonical_hash(payload)
    attempt.pop("report", None)
    return attempt


def apply_attempt(progress: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(progress)
    updated["observed_attempts"] += 1
    updated["last_attempt_hash"] = attempt["attempt_hash"]
    updated["critical_violations"] = list(dict.fromkeys(updated.get("critical_violations", []) + attempt.get("critical_violations", [])))
    if attempt["counts_as_valid_session"]:
        updated["valid_shadow_sessions"] += 1
        updated["counted_sessions"].append(attempt["completed_session"])
        for ticker in REQUIRED_BASELINE_TICKERS:
            if (attempt.get("baseline_coverage") or {}).get(ticker) == "VALIDATED_SHADOW":
                updated["baseline_overlay_sessions"][ticker] = updated["baseline_overlay_sessions"].get(ticker, 0) + 1
        if (attempt.get("independent_price_coverage") or {}).get("status") in {"COVERED", "NOT_REQUIRED"}:
            updated["independent_price_covered_sessions"] += 1
    else:
        updated["excluded_attempts"] += 1
    count = updated["valid_shadow_sessions"]
    if count >= 60:
        updated["checkpoint_status"] = "CHECKPOINT_60_REVIEW_REQUIRED"
    elif count >= 20:
        updated["checkpoint_status"] = "CHECKPOINT_20_REVIEW_REQUIRED"
    elif count >= 10:
        updated["checkpoint_status"] = "CHECKPOINT_10_REVIEW_REQUIRED"
    elif count >= 5:
        updated["checkpoint_status"] = "CHECKPOINT_5_REVIEW_REQUIRED"
    elif count > 0:
        updated["checkpoint_status"] = "CHECKPOINT_1_REVIEW_REQUIRED"
    else:
        updated["checkpoint_status"] = "FIRST_VALID_SESSION_PENDING"
    updated["promotion_status"] = "EXPLICIT_USER_APPROVAL_REQUIRED"
    updated["order_authority"] = False
    return updated


def build_session_record(attempt: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    """Materialize a privacy-safe record only for an eligible counted session."""
    if attempt.get("counts_as_valid_session") is not True:
        raise ValueError("excluded attempt cannot become a session record")
    if attempt.get("portfolio_hash_before") != attempt.get("portfolio_hash_after"):
        raise ValueError("portfolio state changed")
    value = {
        "schema_version": "2.6", "cohort_id": progress["cohort_id"],
        "completed_session": attempt["completed_session"], "attempt_id": attempt["attempt_id"],
        "attempt_hash": attempt["attempt_hash"], "git_commit": attempt["git_commit"],
        "run_manifest_hash": attempt["run_manifest_hash"], "report_hash": attempt["report_hash"],
        "baseline_coverage": deepcopy(attempt.get("baseline_coverage") or {}),
        "independent_price_coverage": deepcopy(attempt.get("independent_price_coverage") or {}),
        "live_strategy_hash": attempt["live_strategy_hash"],
        "shadow_strategy_hash": attempt["shadow_strategy_hash"],
        "artifact_references": deepcopy(attempt.get("artifact_references") or {}),
        "portfolio_state_unchanged": True, "quantity_authority": "none", "order_authority": False,
    }
    value["session_record_hash"] = canonical_hash(value)
    return value


def validate_hash_chain(attempts: list[dict[str, Any]]) -> bool:
    previous = None
    for attempt in attempts:
        if attempt.get("previous_attempt_hash") != previous:
            return False
        payload = {key: value for key, value in attempt.items() if key != "attempt_hash"}
        if canonical_hash(payload) != attempt.get("attempt_hash"):
            return False
        previous = attempt["attempt_hash"]
    return True


def checkpoint_audit(progress: dict[str, Any], checkpoint: int, generated_at: str) -> dict[str, Any]:
    if checkpoint not in {1, 5, 10, 20, 60}:
        raise ValueError("unsupported checkpoint")
    baseline_coverage = {
        ticker: progress.get("baseline_overlay_sessions", {}).get(ticker, 0)
        for ticker in REQUIRED_BASELINE_TICKERS
    }
    eligible = (
        checkpoint >= 20
        and progress.get("valid_shadow_sessions", 0) >= checkpoint
        and not progress.get("critical_violations")
        and all(value >= 5 for value in baseline_coverage.values())
        and progress.get("independent_price_covered_sessions", 0) > 0
    )
    value = {
        "schema_version": "2.6", "cohort_id": progress["cohort_id"], "checkpoint": checkpoint,
        "generated_at": generated_at, "valid_sessions": progress["valid_shadow_sessions"],
        "baseline_coverage": baseline_coverage,
        "independent_price_coverage": progress.get("independent_price_covered_sessions", 0),
        "critical_violations": progress.get("critical_violations", []),
        "promotion_eligible": eligible, "explicit_user_approval_required": True,
        "promotion_state": (
            "LIVE_READ_ONLY_DELIVERY_VERIFIED" if checkpoint == 1 and progress.get("valid_shadow_sessions", 0) >= 1
            else "NOT_ELIGIBLE"
        ),
        "promotion_scope": None,
        "order_authority": False,
    }
    value["audit_hash"] = canonical_hash(value)
    return value


def validate_promotion_review(review: dict[str, Any], progress: dict[str, Any],
                              audit: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if review.get("cohort_id") != progress.get("cohort_id") or review.get("cohort_id") != audit.get("cohort_id"):
        errors.append("COHORT_MISMATCH")
    if review.get("checkpoint_audit_hash") != audit.get("audit_hash"):
        errors.append("CHECKPOINT_AUDIT_HASH_MISMATCH")
    if progress.get("valid_shadow_sessions", 0) < 20 or audit.get("checkpoint") != 20:
        errors.append("TWENTY_SESSION_CHECKPOINT_NOT_MET")
    if audit.get("promotion_eligible") is not True:
        errors.append("PROMOTION_COVERAGE_NOT_MET")
    if review.get("review_status") == "USER_APPROVED" and not review.get("user_approval_reference"):
        errors.append("EXPLICIT_USER_APPROVAL_REFERENCE_MISSING")
    return {"validation_status": "PASSED" if not errors else "FAILED", "errors": errors,
            "automatic_promotion": False, "order_authority": False}


def record_missing_expected_session(progress: dict[str, Any], session: str) -> dict[str, Any]:
    updated = deepcopy(progress)
    if session not in updated["missing_expected_sessions"] and session not in updated["counted_sessions"]:
        updated["missing_expected_sessions"].append(session)
    return updated


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record_attempt(raw: dict[str, Any], *, progress_path: Path, attempts_root: Path,
                   fingerprint: str, now: str | None = None,
                   sessions_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    now = now or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lock_path = progress_path.with_suffix(progress_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = None
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
        descriptor = None
        if progress_path.exists():
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            if progress.get("semantic_fingerprint") != fingerprint:
                progress = initial_progress(fingerprint, now)
        else:
            progress = initial_progress(fingerprint, now)
        attempt = classify_attempt(raw, progress=progress)
        attempt_path = attempts_root / progress["cohort_id"] / f"{attempt['attempt_id']}.json"
        if attempt_path.exists():
            raise ValueError("attempt_id already exists; append-only ledger rejects overwrite")
        updated = apply_attempt(progress, attempt)
        _atomic_write(attempt_path, attempt)
        if attempt["counts_as_valid_session"] and sessions_root is not None:
            session = build_session_record(attempt, updated)
            session_path = sessions_root / progress["cohort_id"] / attempt["completed_session"] / "session_record.json"
            if session_path.exists():
                raise ValueError("counted session record already exists")
            _atomic_write(session_path, session)
        _atomic_write(progress_path, updated)
        return attempt, updated
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock_path.exists():
            lock_path.unlink()
