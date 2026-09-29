#!/usr/bin/env python3
"""Compile a file-first, read-only portfolio manual-advisory dashboard.

This module performs deterministic arithmetic only.  It never calls a broker,
market-data provider, SEC endpoint, scheduler, or order path, and it never
mutates portfolio or policy state.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
import re
import subprocess
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from validation_common import file_hash, load_json, validate_instance
from validate_run_manifest import SECRET_KEY
from session_authority import derive_us_market_session_authority
from integrated_authority_snapshot import (
    IntegratedAuthoritySnapshot, IntegratedAuthorityLoadError,
    derive_us_market_session_authority_from_snapshot,
    load_production_integrated_authority_snapshot,
    resolve_instrument_identity_from_snapshot,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-plan.schema.json"
DASHBOARD_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-dashboard.schema.json"
MANUAL_EVIDENCE_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
LEGACY_MANUAL_EVIDENCE_SCHEMA_VERSION = "2.0"
CURRENT_SESSION_CONTEXT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-current-session-context.schema.json"
REQUEST_ACCOUNTING_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-request-accounting.schema.json"
ORDER_INTENT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/portfolio-decision-order-intent.schema.json"
ORDER_INTENT_SCRIPT = ROOT / "manage-us-stock-strategy/scripts/portfolio_decision_order_intent.py"
DEFAULT_RISK_POLICY = ROOT / "manage-us-stock-strategy/assets/portfolio-decision-risk-envelope-v0.2.json"
DEFAULT_ALERT_POLICY = ROOT / "stock-strategy-system/alert_policy.json"
DEFAULT_PORTFOLIO_STATE = ROOT / "stock-strategy-system/portfolio_state.json"
DEFAULT_OUTPUT_ROOT = ROOT / "workspace/outputs/portfolio-decision-dashboard"
ALLOWED_MODES = {"INITIAL_COMPILE", "POST_SELL_RECOMPILE", "HISTORICAL_REPLAY"}
CURRENT_PLAN_STATUS = "CURRENT_APPROVED"


class ContractError(ValueError):
    """Raised when an input contract is structurally or semantically invalid."""


def _integer_quantity(value: Any) -> int | None:
    number = _decimal(value)
    if number is None or number < 0 or number != number.to_integral_value():
        return None
    return int(number)


def _ticker(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    if not normalized or len(normalized) > 24:
        return None
    return normalized


def _json_number(value: Decimal | float | int | None) -> float | int | None:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _value(value: Decimal | float | int | None, label: str, unit: str) -> dict[str, Any]:
    return {"value": _json_number(value), "value_status": label, "unit": unit}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manual_evidence_schema_bytes(
    evidence: dict[str, Any], *, root: Path = ROOT, allow_legacy_replay: bool = False,
) -> bytes:
    """Select the strict 2.1 contract or a deterministic 2.0 replay view.

    Version 2.1 makes the K3 snapshot provenance field mandatory. Historical
    2.0 artifacts remain replayable by changing only the version constant and
    removing that newly introduced required field from the same checked-in
    schema. Unknown versions are intentionally validated against strict 2.1.
    """
    schema_path = root / MANUAL_EVIDENCE_SCHEMA.relative_to(ROOT)
    schema_bytes = schema_path.read_bytes()
    if (
        evidence.get("schema_version") != LEGACY_MANUAL_EVIDENCE_SCHEMA_VERSION
        or not allow_legacy_replay
    ):
        return schema_bytes
    schema = json.loads(schema_bytes.decode("utf-8"))
    schema["properties"]["schema_version"]["const"] = LEGACY_MANUAL_EVIDENCE_SCHEMA_VERSION
    schema["required"] = [
        name
        for name in schema["required"]
        if name != "integrated_authority_snapshot_provenance"
    ]
    return _json_bytes(schema)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if len(value) == 40 else None


def implementation_provenance_paths(risk_path: Path) -> list[Path]:
    return [
        Path(__file__).resolve(), Path(__file__).with_name("validation_common.py"),
        Path(__file__).with_name("validate_run_manifest.py"),
        Path(__file__).with_name("session_authority.py"),
        Path(__file__).with_name("session_calendar_artifact.py"),
        Path(__file__).with_name("validate_registry_consistency.py"),
        Path(__file__).with_name("instrument_identity_authority.py"),
        Path(__file__).with_name("instrument_identity_artifact.py"),
        Path(__file__).with_name("integrated_authority_snapshot.py"),
        MANUAL_EVIDENCE_SCHEMA, PLAN_SCHEMA, DASHBOARD_SCHEMA,
        CURRENT_SESSION_CONTEXT_SCHEMA, REQUEST_ACCOUNTING_SCHEMA, risk_path.resolve(),
        ORDER_INTENT_SCHEMA, ORDER_INTENT_SCRIPT,
        *[Path(__file__).with_name(name) for name in (
            "evaluate_alerts.py", "timing_engine.py", "validate_technical_snapshot.py",
            "portfolio_policy_gates.py",
        )],
    ]


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _floor_shares(nav: Any, target_weight_pct: Any, price: Any) -> int | None:
    nav_value = _decimal(nav)
    target_value = _decimal(target_weight_pct)
    price_value = _decimal(price)
    if nav_value is None or target_value is None or price_value is None or price_value <= 0:
        return None
    return int((nav_value * target_value / Decimal("100") / price_value).to_integral_value(rounding=ROUND_FLOOR))


def _swing_direction(row: dict[str, Any]) -> tuple[str, list[str]]:
    """Project a candidate without treating legacy arithmetic as approval."""
    action = row["action"]
    current = _integer_quantity(row["current_quantity"]["value"])
    target = _integer_quantity(row["target_shares_reference"]["value"])
    quantity_only = {"BLOCKED_NAV_REQUIRED", "BLOCKED_TARGET_WEIGHT_REQUIRED", "TARGET_HARD_CAP_VIOLATION",
                     "DIRECTION_ONLY_EVIDENCE_NO_QUANTITY_AUTHORITY"}
    issues = [item for item in row.get("blockers") or [] if item not in quantity_only]
    if current is None:
        issues.append("CURRENT_QUANTITY_NOT_VERIFIED")
    if action == "HOLD" and target is not None and current != target:
        issues.append("HOLD_TARGET_MUST_EQUAL_CURRENT")
    if action == "EXIT" and target is not None and target != 0:
        issues.append("EXIT_TARGET_MUST_BE_ZERO")
    if action == "TRIM" and target is not None and current is not None:
        if target == 0:
            issues.append("TRIM_FULL_REDUCTION_REQUIRES_EXIT_REVIEW")
        elif target >= current:
            issues.append("TRIM_TARGET_MUST_REDUCE_HOLDING")
    if action == "ADD" and target is not None and current is not None and target <= current:
        issues.append("BUY_ADD_TARGET_MUST_INCREASE_HOLDING")
    direction = "BUY" if action == "ADD" and current == 0 else action
    return ("DEFERRED" if issues else direction), sorted(set(issues))


def _manual_local_timing_row_scope(row: dict[str, Any]) -> bool:
    return bool(
        row.get("action") == "TRIM"
        and _integer_quantity((row.get("current_quantity") or {}).get("value")) is not None
        and set(row.get("blockers") or []) <= {
            "DIRECTION_ONLY_EVIDENCE_NO_QUANTITY_AUTHORITY",
            "BLOCKED_CANONICAL_PRICE_REQUIRED", "BLOCKED_NAV_REQUIRED",
            "BLOCKED_TARGET_WEIGHT_REQUIRED",
        }
    )


def _manual_local_timing_gate(report: dict[str, Any]) -> bool:
    evidence = report["evidence"]
    if evidence.get("current_freshness") != "CURRENT_SESSION_CONTEXT_VERIFIED":
        return False
    if not set(evidence.get("canonical_gate_blockers") or []) <= {
        "FINALIZED_BAR_PREFLIGHT_NOT_PASS", "FINALIZED_BAR_NOT_VERIFIED",
    }:
        return False
    return all(
        issue in {"NAV_BLOCKED_REQUIRED_CORE_EVIDENCE",
                  "FINALIZED_BAR_PREFLIGHT_NOT_PASS", "FINALIZED_BAR_NOT_VERIFIED"}
        or issue.startswith("MISSING_VERIFIED_CANONICAL_PRICE:")
        for issue in evidence.get("issues") or []
    )


def _manual_capture_only_direction_gate(
    report: dict[str, Any], evidence: dict[str, Any],
    holding_timing_inputs: dict[str, Any] | None,
    parent_capture_artifacts: list[tuple[bytes, str]] | None,
) -> bool:
    """Retain the older Manual direction when no timing input was supplied."""
    if (holding_timing_inputs is not None or not parent_capture_artifacts
            or report["compile_mode"] != "INITIAL_COMPILE"
            or evidence.get("run_mode") != "MANUAL_READ_ONLY"
            or (evidence.get("manual_analysis_view") or {}).get("decision_evidence_scope")
            != "EXISTING_HOLDINGS_AND_CASH_DIRECTION_ONLY"
            or "DIRECTION_SCOPE_INPUTS_NOT_VERIFIED" in report["evidence"]["canonical_gate_blockers"]
            or not _manual_local_timing_gate(report)):
        return False
    from run_manual_portfolio_analysis import validate_manual_direction_evidence
    return validate_manual_direction_evidence(
        evidence, parent_capture_artifacts, analysis_observed_at=report["generated_at"],
    )


def _safe_swing_text(value: str) -> str:
    """Redact the whole field on credential-like labels; never inspect credentials.

    Reuse manifest secret-key classification and extend it for display-only
    account/header fields. Whole-field redaction avoids partial token suffixes.
    This is a labelled-text boundary, not a detector for arbitrary unlabelled data.
    """
    # Normalize a comparison-only copy before tokenization, so compatibility
    # separators cannot split a sensitive label. Return the original text below.
    label_working_value = unicodedata.normalize("NFKC", value)
    labels = re.findall(
        r"\b(\w+(?:(?:[^\S\r\n]|[-－])+\w+)*)[\"']?\s*[:=：＝]", label_working_value)
    sensitive = {"app_key", "app_secret", "account", "account_id", "account_number",
                 "account_no", "token", "authorization", "cookie", "raw_broker_response",
                 "order_id", "credential_path"}
    sensitive = {label.replace("_", "") for label in sensitive}
    for label in labels:
        parts = re.split(r"[\s-]+", label.casefold())
        for start in range(len(parts)):
            candidate = " ".join(parts[start:])
            canonical = re.sub(r"[\s_-]+", "", candidate)
            # Suffixes allow prose before a label, but must end at its delimiter.
            if canonical in sensitive or SECRET_KEY.search(candidate):
                return "[민감정보 제거]"
    if re.search(r"\b(?:Bearer|Basic)\s+\S+|-----BEGIN [^-]*PRIVATE KEY-----|"
                 r"(?:^|[\\/])\.env(?:\b|$)|[a-z]:[\\/][^\r\n]*(?:credential|secret)",
                 value, re.IGNORECASE):
        return "[민감정보 제거]"
    return value


def _holding_timing_projection(
    report: dict[str, Any], evidence: dict[str, Any], inputs: dict[str, Any] | None,
    *, parent_capture_artifacts: list[tuple[bytes, str]] | None = None,
    authority_resolver: Callable[..., Any] = derive_us_market_session_authority,
) -> dict[str, dict[str, Any]]:
    """Re-evaluate the existing reduce-review event, never its quantity authority.

    Input objects are not approval receipts. Policy and anchor/fill state must
    match the existing canonical files; the technical producer owns its rules.
    This optional Manual-only projection does not define a general timing PASS.
    """
    if inputs is None:
        return {}
    try:
        if (not isinstance(inputs, dict)
                or not {"snapshot", "state", "policy"} <= set(inputs)
                or set(inputs) - {"snapshot", "state", "policy", "capture_artifacts", "corporate_action_artifacts"}):
            return {}
        capture_provided = "capture_artifacts" in inputs
        if capture_provided:
            artifacts = inputs["capture_artifacts"]
            if (not isinstance(artifacts, list) or not artifacts
                    or any(not isinstance(item, tuple) or len(item) != 2
                           or not isinstance(item[0], bytes) or not isinstance(item[1], str)
                           for item in artifacts)):
                return {}
        snapshot, state, policy = (inputs[k] for k in ("snapshot", "state", "policy"))
        if not all(isinstance(x, dict) for x in (snapshot, state, policy)):
            return {}
        if state != load_json(DEFAULT_PORTFOLIO_STATE) or policy != load_json(DEFAULT_ALERT_POLICY):
            return {}
        # Revalidate consumed acquisition bytes; report flags/content hashes alone
        # are not evidence eligibility or request/response provenance.
        from run_manual_portfolio_analysis import validate_manual_direction_evidence
        if not validate_manual_direction_evidence(
                evidence, parent_capture_artifacts, analysis_observed_at=report["generated_at"]):
            return {}
        view = evidence.get("manual_analysis_view") or {}
        local_bars = view.get("local_regular_bar_coherence") or {}
        if (view.get("provider_finalization_verified") != "NOT_VERIFIED"
                or not isinstance(local_bars, dict) or not local_bars
                or any(not isinstance(item, dict) or item.get("status") != "PASS"
                       for item in local_bars.values())):
            return {}
        if (view.get("decision_evidence_scope")
                != "EXISTING_HOLDINGS_AND_CASH_DIRECTION_ONLY"
                 or report["compile_mode"] != "INITIAL_COMPILE"
                 or evidence.get("run_mode") != "MANUAL_READ_ONLY"
                 or not _manual_local_timing_gate(report)):
            return {}
        cutoff = _parse_timestamp(evidence.get("decision_as_of"))
        built = _parse_timestamp(snapshot.get("generated_at_utc"))
        if cutoff is None or built is None or not 0 <= (cutoff - built).total_seconds() <= 900:
            return {}
        session = evidence.get("expected_completed_us_session")
        if not session or (snapshot.get("session") or {}).get("us_session_date") != session:
            return {}
        # Combined Manual evidence must consume its bound ACTIVE cohort for
        # both confirmation identities and sessions, never a legacy fallback.
        from instrument_identity_authority import resolve_instrument_identity
        identity_resolver = resolve_instrument_identity
        provenance = evidence.get("integrated_authority_snapshot_provenance") or {}
        if provenance.get("authority_source") == "K3_COMBINED_PRODUCTION":
            bound = load_production_integrated_authority_snapshot(
                trusted_root=ROOT,
                decision_as_of=provenance["snapshot_decision_as_of"],
                resolved_at=evidence["observed_at"], run_id=evidence["manual_run_id"],
            )
            if bound.provenance(authority_source="K3_COMBINED_PRODUCTION",
                                report_decision_as_of=evidence["decision_as_of"]) != provenance:
                return {}
            identity_resolver = partial(resolve_instrument_identity_from_snapshot, bound)
            authority_resolver = partial(derive_us_market_session_authority_from_snapshot, bound)
        elif provenance.get("authority_source") != "LEGACY_INDEPENDENT":
            return {}
        timing_policy = policy.get("holding_timing_rules") or {}
        if (timing_policy.get("status") != "approved_review_only"
                or policy.get("daily_engine_scope") != "leveraged_holding_risk_and_watchlist"
                or timing_policy.get("formula_version") != (snapshot.get("indicator_provenance") or {}).get("formula_version")
                or timing_policy.get("timing_feature_version") != (snapshot.get("indicator_provenance") or {}).get("timing_feature_version")):
            return {}
        # Reuse the verified Manual memory-only Broker view, not the age of a
        # historical ledger snapshot. Canonical anchors/fills remain untouched;
        # any inconsistency with fresh holdings still fails the evaluator.
        broker_holdings, broker_costs, issues, _ = _extract_holdings(evidence)
        if issues:
            return {}
        broker = evidence.get("broker_observed_state") or {}
        broker_as_of = _parse_timestamp(broker.get("as_of"))
        if (broker.get("status") != "AVAILABLE"
                or broker.get("source") != "KIWOOM_ACCOUNT_READ_ONLY"
                or (broker.get("operation_statuses") or {}).get("account_holdings_read") != "PASS"
                or broker_as_of is None or broker_as_of > cutoff):
            return {}
        if any(_decimal(qty) is None or _decimal(qty) < 0
               or _decimal(qty) != _decimal(qty).to_integral_value()
               or (_decimal(qty) > 0 and
                   (_decimal(broker_costs.get(ticker)) is None or _decimal(broker_costs.get(ticker)) <= 0))
               for ticker, qty in broker_holdings.items()):
            return {}
        timing_state = copy.deepcopy(state)
        timing_state["holdings"] = {ticker: _json_number(_decimal(qty)) for ticker, qty in broker_holdings.items()}
        timing_state["average_cost_usd"] = {ticker: _json_number(_decimal(cost)) for ticker, cost in broker_costs.items()}
        timing_state["position_cost_basis_usd"] = {
            ticker: _json_number(_decimal(qty) * _decimal(broker_costs[ticker]))
            for ticker, qty in broker_holdings.items() if _decimal(qty) > 0
        }
        # as_of is the genuine observation's New York calendar date because
        # the existing age check compares it to a U.S. completed-session date.
        # No clock/cutoff backdating or completed-session substitution. Retain
        # the full observation timestamp separately in the existing field.
        timing_state["last_confirmed_broker_snapshot"] = {
            "verified": True, "holdings_complete": True,
            "source": "KIWOOM_ACCOUNT_READ_ONLY",
            "as_of": broker_as_of.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
            "as_of_timestamp_kst": broker_as_of.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
            "cash_verified": False,
        }
        # Orderable cash is not this evaluator's available/settled cash. The
        # projection exports reduction-review events only, never buy watches.
        timing_state["available_cash_usd"] = None
        from evaluate_alerts import evaluate
        # The existing evaluator validates state/anchors, calendar, snapshot,
        # cross-checks, hard-risk precedence and rearm before returning events.
        evaluated = evaluate(timing_state, policy, snapshot, {})
        if evaluated.get("state") in {"STATE_MISMATCH", "DATA_INCOMPLETE"}:
            return {}
        directions = {
            row["ticker"]: "TRIM" if _manual_local_timing_row_scope(row)
            else _swing_direction(row)[0]
            for row in report["portfolio"]["positions"]
        }
        result = {}
        for ticker, rule in (timing_policy.get("positions") or {}).items():
            if directions.get(ticker) != "TRIM":
                continue
            event = next((item for item in evaluated.get("candidates") or []
                          if item.get("symbol") == ticker
                          and item.get("event_type") == "holding_timing_review"), None)
            kiwoom_only = False
            # Current facts are the validated Broker inputs already evaluated
            # above. Historical quantity/cost equality is not a second gate.
            # Approved anchors and explicit fill/rearm checks remain in evaluate.
            qty = _decimal(broker_holdings.get(ticker))
            cost = _decimal(broker_costs.get(ticker))
            if qty is None or qty <= 0 or cost is None or cost <= 0:
                continue
            rule = (timing_policy.get("positions") or {}).get(ticker) or {}
            required = [ticker, rule.get("confirmation_symbol")]
            if any(not symbol for symbol in required):
                continue
            symbol_rows = snapshot.get("symbols")
            if (not isinstance(symbol_rows, dict)
                    or any(not isinstance(symbol_rows.get(symbol), dict)
                           or symbol_rows[symbol].get("corporate_action_unresolved") is not False
                           for symbol in required)):
                continue
            if not capture_provided:
                # The parent RAW bar was recomputed from consumed capture bytes
                # by validate_manual_direction_evidence above. With no separate
                # technical capture, bind every comparable OHLCV value to the
                # actual timing row before accepting the ordinary event.
                bar = (local_bars.get(ticker) or {}).get("bar")
                timing_row = symbol_rows[ticker]
                if (not isinstance(bar, dict) or bar.get("session") != session
                        or timing_row.get("bar_date") != session
                        or any(_decimal(bar.get(field)) is None
                               or _decimal(timing_row.get(field)) is None
                               or _decimal(bar[field]) != _decimal(timing_row[field])
                               for field in ("open", "high", "low", "close", "volume"))):
                    continue
            if not capture_provided:
                # P1/P2: matching parent RAW bars and an ordinary event do not
                # supply the required ADJUSTED history or reviewed CA binding.
                continue
            identities = [identity_resolver(symbol, decision_as_of=evidence["decision_as_of"]) for symbol in required]
            if any(identity.authority_status != "VERIFIED" for identity in identities):
                continue
            # The rendered current_context has no MIC. Resolve the real close
            # using each approved instrument identity, including confirmation.
            closes = []
            for identity in identities:
                authority = authority_resolver(
                    report["generated_at"], decision_as_of=report["generated_at"],
                    primary_listing_operating_mic=getattr(identity, "primary_listing_operating_mic", None),
                )
                completed = getattr(authority, "expected_completed_session", None)
                closed_at = _parse_timestamp(getattr(completed, "core_close_at", None))
                if (getattr(authority, "authority_status", None) != "VERIFIED"
                        or getattr(completed, "session_date", None) != session
                        or closed_at is None or closed_at > cutoff):
                    break
                closes.append(closed_at)
            if len(closes) != len(required):
                continue
            if capture_provided:
                # Both consumed RAW capture sets must agree even when the
                # ordinary evaluator already found an independently checked event.
                from run_manual_portfolio_analysis import (
                    _parent_capture_evidence, _same_scope_raw_bar_coherence,
                )
                combined_artifacts = list(dict.fromkeys(
                    (parent_capture_artifacts or []) + inputs["capture_artifacts"]
                ))
                combined_captures = _parent_capture_evidence(
                    combined_artifacts, run_id=evidence["manual_run_id"],
                    observed_at=report["generated_at"],
                )
                if any(_same_scope_raw_bar_coherence(
                        combined_captures, ticker=symbol, completed_session=session,
                ) != "PASS" for symbol in required):
                    continue
                # Actual technical captures and explicit CA confirmation remain
                # required even when independent closes produced an event.
                from validate_technical_snapshot import validate_manual_kiwoom_snapshot
                validation = validate_manual_kiwoom_snapshot(
                    snapshot, required_symbols=required, expected_session_date=session,
                    capture_artifacts=inputs["capture_artifacts"],
                    run_id=evidence["manual_run_id"], decision_as_of=evidence["decision_as_of"],
                    analysis_observed_at=report["generated_at"], policy=policy, closed_at=closes,
                    corporate_action_artifacts=inputs.get("corporate_action_artifacts"),
                )
                if validation.get("status") != "verified":
                    continue
                if (validation.get("local_regular_bar_coherence") != "PASS"
                        or validation.get("technical_analysis_eligibility") != "YES"
                        or validation.get("provider_finalization_verified") != "NOT_VERIFIED"):
                    continue
            if event is None and capture_provided:
                # Only missing independent closes authorize the existing Manual
                # fallback. A fully checked snapshot must use its ordinary event.
                if validation.get("timing_source_mode") != "KIWOOM_ONLY":
                    continue
                from evaluate_alerts import exact_loss_boundary, rules_hash
                from timing_engine import evaluate_holding_timing
                position = policy["holding_risk_rules"]["positions"][ticker]
                boundary = exact_loss_boundary(float(cost), position["maximum_loss_fraction_from_average_cost"])
                event, _ = evaluate_holding_timing(
                    state=timing_state, policy=policy, symbol=ticker,
                    row=snapshot["symbols"][ticker], proxy_row=snapshot["symbols"][required[1]],
                    hard_boundary=boundary, rules_hash=rules_hash(policy),
                    suppress_for_hard_risk=snapshot["symbols"][ticker]["close"] <= boundary,
                )
                if event is not None:
                    event["technical_validation_status"] = "verified"
                    kiwoom_only = True
            if (not event or event.get("event_type") != "holding_timing_review"
                    or event.get("side") != "reduce" or event.get("grade") != "B"
                    or event.get("watch_only") is not False
                    or event.get("technical_validation_status") != "verified"
                    or event.get("actionable") is not False):
                continue
            calendar_time = _parse_timestamp(snapshot["session"].get("calendar_verified_at_utc"))
            if calendar_time is None or calendar_time > cutoff:
                continue
            from validate_technical_snapshot import independent_close_missing
            invalid_crosscheck_time = False
            for symbol, closed_at in zip(required, closes):
                row = snapshot["symbols"][symbol]
                if kiwoom_only and independent_close_missing(row):
                    continue
                checked = _parse_timestamp((row.get("quote_crosscheck") or {}).get("verified_at_utc"))
                if checked is None or not closed_at <= checked <= cutoff:
                    invalid_crosscheck_time = True
                    break
            if invalid_crosscheck_time:
                continue
            bar_price = ((local_bars.get(ticker) or {}).get("bar") or {}).get("close")
            if _decimal(bar_price) != _decimal(event.get("close")):
                continue
            # Only non-sensitive identifiers and consumed-content hashes persist.
            identifiers = {"policy_version": timing_policy.get("policy_version"),
                           "tranche_id": event.get("tranche_id"), "trigger_path": event.get("trigger_path")}
            if any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", v) for v in identifiers.values()):
                continue
            result[ticker] = {
                "status": "VERIFIED_REDUCTION_REVIEW", "event_type": "holding_timing_review",
                "side": "reduce", "grade": "B", "session": session, **identifiers,
                "snapshot_sha256": _sha256_bytes(_json_bytes(snapshot)),
                "state_sha256": _sha256_bytes(_json_bytes(state)),
                "policy_sha256": _sha256_bytes(_json_bytes(policy)),
                "manual_evidence_sha256": _sha256_bytes(_json_bytes(evidence)),
            }
            if kiwoom_only:
                result[ticker].update(timing_source_mode="KIWOOM_ONLY",
                                      independent_close_status="NOT_VERIFIED")
        return result
    except (KeyError, TypeError, ValueError, OSError, ArithmeticError, IntegratedAuthorityLoadError):
        return {}


def _swing_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive every displayed position field from canonical dashboard rows."""
    rows = []
    for row in report["portfolio"]["positions"]:
        direction, conflicts = _swing_direction(row)
        timing = row.get("holding_timing_evidence") or {}
        local_timing = (row["ticker"] in (report["evidence"].get("manual_holding_timing_local_prices") or {})
                        and _manual_local_timing_row_scope(row)
                        and _manual_local_timing_gate(report))
        # A capture-only Manual direction has no optional technical timing input.
        # Its validated direction remains visible while canonical price and
        # quantity gates retain their own blocked status.
        legacy_direction = (
            report["evidence"].get("manual_capture_only_direction") is True
            and not local_timing and row.get("holding_timing_evidence") is None
            and report["compile_mode"] == "INITIAL_COMPILE"
            and report["evidence"].get("evidence_grade") == "GRADE_B"
            and "DIRECTION_ONLY_EVIDENCE_NO_QUANTITY_AUTHORITY" in (row.get("blockers") or [])
            and "BLOCKED_TARGET_WEIGHT_REQUIRED" in (row.get("blockers") or [])
            and _manual_local_timing_row_scope(row)
            and _manual_local_timing_gate(report)
        )
        if local_timing or legacy_direction:
            direction = "TRIM"
        current = row["current_quantity"]["value"]
        candidate = "BUY" if row["action"] == "ADD" and current == 0 else row["action"]
        issues = list(conflicts) + list(row.get("blockers") or [])
        if report["evidence"]["portfolio_evidence_status"] != "VERIFIED":
            issues.append("CURRENT_PORTFOLIO_EVIDENCE_NOT_VERIFIED")
        if (report["evidence"].get("canonical_gate_blockers")
                or any(issue.startswith("INPUT_") for issue in report["evidence"]["issues"])):
            issues.append("CANONICAL_EVIDENCE_CONTRACT_NOT_VERIFIED")
            if not (local_timing or legacy_direction):
                direction = "DEFERRED"
        if report["evidence"]["current_freshness"] != "CURRENT_SESSION_CONTEXT_VERIFIED":
            issues.append("CURRENT_SESSION_EVIDENCE_NOT_VERIFIED")
            direction = "DEFERRED"
        rows.append({
            "ticker": row["ticker"], "candidate_direction": candidate,
            "direction": direction, "current_qty": current,
            "current_qty_status": row["current_quantity"]["value_status"],
            "price": (report["evidence"].get("manual_holding_timing_local_prices") or {}).get(row["ticker"])
                     if local_timing else row["canonical_price_usd"]["value"],
            "price_status": "LOCAL_ACCEPTED_FOR_TIMING" if local_timing
                            else row["canonical_price_usd"]["value_status"],
            "price_session": timing.get("session") if local_timing else row["price_session"],
            "timing_status": (row.get("holding_timing_evidence") or {}).get("status", "NOT_VERIFIED"),
            "quantity_status": "NOT_VERIFIED" if issues else "POLICY_REQUIRED",
            "shadow_target_qty": None, "shadow_delta_qty": None,
            "shadow_buy_qty": None, "shadow_sell_qty": None,
            "shadow_cash_impact": None, "target_weight_pct": None,
            "reason": _safe_swing_text(row["rationale"]) + (
                " [LOCAL_REGULAR_BAR_COHERENCE=PASS; PROVIDER_FINALIZATION=NOT_VERIFIED; "
                + ("KIWOOM_ONLY; 독립 종가 NOT_VERIFIED; "
                   if timing.get("timing_source_mode") == "KIWOOM_ONLY" else "")
                + "Manual 기존 보유 timing 한정]"
                if local_timing else ""),
            "invalidation": [_safe_swing_text(item) for item in row.get("decision_change_triggers") or []],
            "blockers": sorted(set(issues + [
                "SHADOW_QUANTITY_POLICY_NOT_ACTIVATED",
                "MANUAL_LOOP_READINESS_NOT_VERIFIED",
            ] + ([] if row.get("holding_timing_evidence") else ["BOUND_APPROVED_TECHNICAL_SIGNAL_NOT_VERIFIED"]) + (["BUY_ADD_OUTSIDE_FIRST_SHADOW_SCOPE"] if candidate in {"BUY", "ADD"} else []))),
            "execution_status": "DISABLED",
        })
    return rows


def _build_swing_action_contract(
    report: dict[str, Any], evidence: dict[str, Any], plan: dict[str, Any],
    risk_policy: dict[str, Any], evidence_sha256: str | None,
) -> dict[str, Any]:
    """Stage-one derived view only; no quantity-policy activation or sizing."""
    return {
        "contract_version": "1.0", "stage": "CONTRACT_ONLY",
        "scope": "EXISTING_HOLDINGS_AND_CASH_FIRST",
        "source_binding": {
            "evidence_run_id": report["evidence"]["run_id"],
            "evidence_sha256": evidence_sha256,
            "plan_id": plan["plan_id"],
            "plan_content_sha256": _sha256_bytes(_json_bytes(plan)),
            "risk_policy_version": risk_policy["policy_version"],
            "risk_policy_content_sha256": _sha256_bytes(_json_bytes(risk_policy)),
            "decision_as_of": evidence.get("decision_as_of"),
            "broker_snapshot_as_of": evidence.get("broker_snapshot_as_of"),
            "account_identity_status": "NOT_VERIFIED",
            "policy_approval_binding": "NOT_VERIFIED",
            "freshness": report["evidence"]["current_freshness"],
        },
        "rows": _swing_rows(report),
        "cash": {
            "alternative": "KEEP_CASH", "decision_status": "REVIEW_REQUIRED",
            "nav_cash_usd": dict(report["cash_semantics"]["current_cash_usd"]),
            "orderable_cash_usd": dict(report["cash_semantics"]["verified_orderable_cash_usd"]),
            "snapshot_alignment": "NOT_VERIFIED",
            "shadow_cash_impact": None, "expected_proceeds_are_orderable": False,
        },
        "order_authority": False, "quantity_authority": "none",
        "execution_quantity": None, "broker_submission": "disabled",
    }


def validate_swing_action_contract(
    report: dict[str, Any], *, schema_bytes: bytes | None = None,
    evidence: dict[str, Any] | None = None, plan: dict[str, Any] | None = None,
    risk_policy: dict[str, Any] | None = None, evidence_sha256: str | None = None,
    holding_timing_inputs: dict[str, Any] | None = None,
    parent_capture_artifacts: list[tuple[bytes, str]] | None = None,
    current_session_authority_resolver: Callable[..., Any] = derive_us_market_session_authority,
) -> list[str]:
    """Validate a derived view; hash authenticity requires consumed inputs.

    Without those inputs hash checks are FORMAT_ONLY, not provenance approval.
    The compiler supplies its consumed inputs; standalone renderers cannot prove
    authenticity of an entire report that has been coherently replaced.
    """
    view = report.get("swing_action_plan")
    if "swing_action_plan" not in report:
        return []  # Historical reports predate this additive contract.
    errors = validate_instance(report, DASHBOARD_SCHEMA, schema_bytes=schema_bytes)
    if errors:
        # Shared schema diagnostics may contain raw invalid values or property names.
        return ["SWING_SCHEMA_INVALID"]
    source_rows = report["portfolio"]["positions"]
    for row in source_rows:
        timing = row.get("holding_timing_evidence") or {}
        if (("timing_source_mode" in timing) != ("independent_close_status" in timing)):
            errors.append("SWING_TIMING_SOURCE_MODE_MISMATCH")
        if row.get("holding_timing_evidence") is not None and (
                (_swing_direction(row)[0] != "TRIM"
                 and not (row["ticker"] in (report["evidence"].get("manual_holding_timing_local_prices") or {})
                          and _manual_local_timing_row_scope(row)))
                or report["compile_mode"] != "INITIAL_COMPILE"
                or report["evidence"]["current_freshness"] != "CURRENT_SESSION_CONTEXT_VERIFIED"
                or (report["evidence"].get("canonical_gate_blockers")
                    and not (row["ticker"] in (report["evidence"].get("manual_holding_timing_local_prices") or {})
                             and _manual_local_timing_gate(report)))):
            errors.append("SWING_TIMING_SCOPE_MISMATCH")
    if [row["ticker"] for row in view["rows"]] != [row["ticker"] for row in source_rows]:
        errors.append("SWING_POSITION_SCOPE_MISMATCH")
    for index, (row, expected) in enumerate(zip(view["rows"], _swing_rows(report))):
        if row != expected:
            errors.append(f"SWING_DERIVED_ROW_MISMATCH:{index}")
    binding = view["source_binding"]
    for name, expected in (
        ("evidence_run_id", report["evidence"]["run_id"]),
        ("decision_as_of", report["evidence"]["decision_as_of"]),
        ("freshness", report["evidence"]["current_freshness"]),
        ("plan_id", report["plan"]["plan_id"]),
    ):
        if binding[name] != expected:
            errors.append(f"SWING_SOURCE_BINDING_MISMATCH:{name}")
    for key, source_key in (("nav_cash_usd", "current_cash_usd"), ("orderable_cash_usd", "verified_orderable_cash_usd")):
        if view["cash"][key] != report["cash_semantics"][source_key]:
            errors.append(f"SWING_CASH_SEMANTICS_MISMATCH:{key}")
    if any(item is not None for item in (
            evidence, plan, risk_policy, evidence_sha256,
            holding_timing_inputs, parent_capture_artifacts)):
        if evidence is None or plan is None or risk_policy is None:
            errors.append("SWING_PROVENANCE_INPUTS_INCOMPLETE")
        else:
            expected_binding = _build_swing_action_contract(
                report, evidence, plan, risk_policy, evidence_sha256,
            )["source_binding"]
            if binding != expected_binding:
                errors.append("SWING_CONSUMED_INPUT_BINDING_MISMATCH")
    if evidence is not None:
        expected_capture_only = _manual_capture_only_direction_gate(
            report, evidence, holding_timing_inputs, parent_capture_artifacts,
        )
        if (report["evidence"].get("manual_capture_only_direction") is True) != expected_capture_only:
            errors.append("SWING_CAPTURE_ONLY_DIRECTION_BINDING_MISMATCH")
        expected_timing = _holding_timing_projection(
            report, evidence, holding_timing_inputs,
            parent_capture_artifacts=parent_capture_artifacts,
            authority_resolver=current_session_authority_resolver,
        )
        for row in source_rows:
            if row.get("holding_timing_evidence") != expected_timing.get(row["ticker"]):
                errors.append("SWING_TIMING_CONSUMED_INPUT_MISMATCH")
        expected_local_prices = {
            ticker: (holding_timing_inputs["snapshot"]["symbols"][ticker]["close"])
            for ticker, timing in expected_timing.items()
            if isinstance(holding_timing_inputs, dict)
        }
        if (report["evidence"].get("manual_holding_timing_local_prices") or {}) != expected_local_prices:
            errors.append("SWING_LOCAL_PRICE_BINDING_MISMATCH")
        if expected_local_prices:
            if (report["evidence"].get("provider_finalization_verified") != "NOT_VERIFIED"
                    or report["evidence"].get("local_regular_bar_coherence") != "PASS"
                    or report["evidence"].get("technical_analysis_eligibility") != "YES"):
                errors.append("SWING_LOCAL_SEMANTIC_STATUS_MISMATCH")
        elif any(key in report["evidence"] for key in (
                "provider_finalization_verified", "local_regular_bar_coherence",
                "technical_analysis_eligibility")):
            errors.append("SWING_LOCAL_SEMANTIC_STATUS_UNBOUND")
    return sorted(set(errors))


def _require_valid_swing_view(report: dict[str, Any]) -> None:
    """Fail before rendering/persistence; never echo untrusted validation values."""
    if validate_swing_action_contract(report):
        raise ContractError("SWING_ACTION_CONTRACT_INVALID")


def _safe_swing_report(report: dict[str, Any]) -> dict[str, Any]:
    """Keep legacy repeats of Swing narrative safe without mutating the caller."""
    _require_valid_swing_view(report)
    if "swing_action_plan" not in report:
        return report
    safe = copy.deepcopy(report)
    for row in safe["portfolio"]["positions"]:
        row["rationale"] = _safe_swing_text(row["rationale"])
        row["decision_change_triggers"] = [_safe_swing_text(item) for item in row.get("decision_change_triggers") or []]
    for row in safe["stage1"]["sell_advisories"]:
        row["reason"] = _safe_swing_text(row["reason"])
    for field in ("material_unknowns", "decision_change_triggers"):
        safe["plan"][field] = [_safe_swing_text(item) for item in safe["plan"].get(field) or []]
    return safe


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def validate_plan(
    plan: dict[str, Any], schema_path: Path = PLAN_SCHEMA, *, schema_bytes: bytes | None = None,
) -> list[str]:
    errors = validate_instance(plan, schema_path, schema_bytes=schema_bytes)
    if errors:
        return ["DECISION_PLAN_SCHEMA_INVALID"]
    seen: set[str] = set()
    for index, position in enumerate(plan.get("positions") or []):
        ticker = _ticker(position.get("ticker")) if isinstance(position, dict) else None
        if ticker is None:
            continue
        if ticker in seen:
            errors.append(f"$.positions[{index}]: DUPLICATE_TICKER:{ticker}")
        seen.add(ticker)
        weight = position.get("target_weight_pct")
        weight_decimal = _decimal(weight)
        if weight is not None and (weight_decimal is None or weight_decimal < 0 or weight_decimal > Decimal("100")):
            errors.append(f"$.positions[{index}].target_weight_pct: TARGET_WEIGHT_OUTSIDE_0_100")
    cash_target = plan.get("cash_target_pct")
    cash_decimal = _decimal(cash_target)
    if cash_target is not None and (cash_decimal is None or cash_decimal < 0 or cash_decimal > Decimal("100")):
        errors.append("$.cash_target_pct: CASH_TARGET_OUTSIDE_0_100")
    supplied = [p.get("target_weight_pct") for p in plan.get("positions", []) if p.get("target_weight_pct") is not None]
    supplied_total = sum((_decimal(value) or Decimal("0")) for value in supplied)
    if supplied_total > Decimal("100"):
        errors.append("$: TARGET_ALLOCATION_EXCEEDS_100_PERCENT")
    if cash_target is not None:
        if cash_decimal is not None and supplied_total + cash_decimal > Decimal("100"):
            errors.append("$: TARGET_ALLOCATION_EXCEEDS_100_PERCENT")
    priority = plan.get("buy_priority") or []
    unknown_priority = [item for item in priority if item not in seen]
    if unknown_priority:
        errors.append("$.buy_priority: UNKNOWN_TICKER:" + ",".join(unknown_priority))
    return sorted(set(errors))


def write_decision_plan(plan: dict[str, Any], path: Path, *, root: Path = ROOT) -> Path:
    """Validate and materialize supplied plan content without granting authority."""
    try:
        errors = validate_plan(plan)
    except (AttributeError, TypeError) as exc:
        raise ContractError("DECISION_PLAN_INVALID: malformed plan object") from exc
    if errors:
        raise ContractError("DECISION_PLAN_INVALID:" + "; ".join(errors))
    if ".." in path.parts:
        raise ContractError("OUTPUT_PATH_TRAVERSAL")
    approved_outputs = root.resolve() / "workspace" / "outputs"
    target = path.resolve()
    try:
        _trusted_output(approved_outputs, target)
    except ContractError as exc:
        raise ContractError("OUTPUT_OUTSIDE_APPROVED_OUTPUTS") from exc
    payload = _json_bytes(plan)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return target


def _extract_holdings(evidence: dict[str, Any]) -> tuple[dict[str, int], dict[str, Decimal], list[str], str]:
    broker = evidence.get("broker_observed_state") or {}
    issues: list[str] = []
    holdings: dict[str, int] = {}
    costs: dict[str, Decimal] = {}
    if broker.get("status") != "AVAILABLE":
        return {}, {}, ["BROKER_HOLDINGS_NOT_AVAILABLE"], "BROKER_OBSERVED_STATE"
    raw = broker.get("holdings")
    if not isinstance(raw, list) or not raw:
        return {}, {}, ["MISSING_HOLDINGS"], "BROKER_OBSERVED_STATE"
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            issues.append(f"INVALID_HOLDING_RECORD:{index}")
            continue
        ticker = _ticker(item.get("ticker"))
        quantity = _integer_quantity(item.get("held_quantity"))
        if ticker is None or quantity is None:
            issues.append(f"INVALID_HOLDING_CORE_FIELDS:{index}")
            continue
        if ticker in holdings:
            issues.append(f"DUPLICATE_BROKER_TICKER:{ticker}")
            continue
        holdings[ticker] = quantity
        average_cost = _decimal(item.get("average_cost"))
        if average_cost is not None and average_cost >= 0:
            costs[ticker] = average_cost
    if not holdings:
        issues.append("MISSING_HOLDINGS")
    return holdings, costs, issues, "BROKER_OBSERVED_STATE"


def _extract_cash(evidence: dict[str, Any]) -> tuple[Decimal | None, Decimal | None, list[str]]:
    broker = evidence.get("broker_observed_state") or {}
    cash = broker.get("cash") or {}
    issues: list[str] = []
    current_cash = _decimal(cash.get("foreign_currency_deposit"))
    if current_cash is not None and current_cash < 0:
        current_cash = None
    if cash.get("cash_status") not in {"VERIFIED_POSITIVE", "VERIFIED_ZERO"}:
        current_cash = None
    if current_cash is None:
        issues.append("MISSING_CURRENT_CASH")
    verified_orderable = _decimal(evidence.get("verified_orderable_cash_usd"))
    if verified_orderable is not None and verified_orderable < 0:
        verified_orderable = None
    if evidence.get("orderable_cash_status") != "VERIFIED" or verified_orderable is None:
        verified_orderable = None
        issues.append("MISSING_VERIFIED_ORDERABLE_CASH")
    return current_cash, verified_orderable, issues


def _sell_readiness_evidence(
    evidence: dict[str, Any], ticker: str, current_quantity: Any,
    proposed_quantity: Any, evaluation_time: datetime | None,
) -> dict[str, Any]:
    """Classify factual SELL evidence without granting execution authority."""
    blockers: list[str] = []
    broker = evidence.get("broker_observed_state")
    broker = broker if isinstance(broker, dict) else {}
    operations = broker.get("operation_statuses")
    operations = operations if isinstance(operations, dict) else {}
    holdings = broker.get("holdings")
    matches = [
        item for item in holdings
        if isinstance(item, dict) and _ticker(item.get("ticker")) == ticker
    ] if isinstance(holdings, list) else []
    holding = matches[0] if len(matches) == 1 else {}
    held = _integer_quantity(holding.get("held_quantity"))
    available = _decimal(holding.get("available_shares"))
    current = _integer_quantity(current_quantity)
    quantity = _integer_quantity(proposed_quantity)
    available_status = "NOT_VERIFIED"
    if (broker.get("status") != "AVAILABLE" or operations.get("account_holdings_read") != "PASS"
            or held is None or current is None or held != current
            or available is None or available < 0 or available > held):
        blockers.append("AVAILABLE_SHARES_NOT_VERIFIED")
        available = None
    elif quantity is not None and quantity > available:
        available_status = "INSUFFICIENT"
        blockers.append("AVAILABLE_SHARES_INSUFFICIENT")
    else:
        available_status = "VERIFIED"

    open_evidence = broker.get("open_order_evidence")
    open_evidence = open_evidence if isinstance(open_evidence, dict) else {}
    pagination = open_evidence.get("pagination")
    pagination = pagination if isinstance(pagination, dict) else {}
    rows = open_evidence.get("data")
    retrieved = _parse_timestamp(open_evidence.get("retrieved_at"))
    cutoff = _parse_timestamp(evidence.get("decision_as_of"))
    snapshot_time = _parse_timestamp(evidence.get("broker_snapshot_as_of"))
    broker_time = _parse_timestamp(broker.get("as_of"))
    open_blockers: list[str] = []
    if (open_evidence.get("operation") != "account_open_items"
            or open_evidence.get("bridge_status") != "PASS"
            or operations.get("account_open_items") != "PASS"
            or pagination.get("api_id") != "ust21050"
            or type(pagination.get("pages")) is not int or pagination["pages"] < 1
            or pagination.get("complete") is not True
            or pagination.get("exhausted") is not True
            or not isinstance(rows, list)
            or any(not isinstance(item, dict) for item in rows)):
        open_blockers.append("OPEN_ORDER_EVIDENCE_NOT_VERIFIED")
    if isinstance(rows, list) and rows:
        open_blockers.append("OPEN_ORDER_CONFLICT_PRESENT")
    freshness_end = None
    if (retrieved is None or evaluation_time is None or cutoff is None
            or snapshot_time is None or broker_time is None):
        open_blockers.append("OPEN_ORDER_EVIDENCE_NOT_VERIFIED")
    elif retrieved > min(evaluation_time, cutoff, snapshot_time, broker_time):
        open_blockers.append("OPEN_ORDER_EVIDENCE_FROM_FUTURE")
    else:
        # Reuse the canonical broker contract and Manual Intent's exclusive end.
        freshness_end = retrieved + timedelta(seconds=900)
        if evaluation_time >= freshness_end:
            open_blockers.append("OPEN_ORDER_EVIDENCE_STALE")
    blockers.extend(open_blockers)
    return {
        "available_shares_status": available_status,
        "available_shares": _json_number(available),
        "open_order_conflict_status": "VERIFIED_NONE" if not open_blockers else "NOT_VERIFIED",
        "open_order_valid_until": freshness_end.isoformat() if freshness_end is not None else None,
        "blockers": sorted(set(blockers)),
    }


def _extract_prices(evidence: dict[str, Any], required: set[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    prices: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    for item in evidence.get("last_verified_finalized_bars") or []:
        if not isinstance(item, dict):
            continue
        ticker = _ticker(item.get("ticker"))
        bar = item.get("bar") or {}
        price = _decimal(bar.get("price"))
        valid = bool(
            ticker and price is not None and price > 0 and item.get("status") == "VERIFIED"
            and item.get("session_authority_status") == "VERIFIED"
            and bar.get("bar_finalized") is True
            and bar.get("stable") is True
            and bar.get("comparable_to_regular_close") is True
            and bar.get("market_session_type") == "REGULAR_COMPLETED"
            and bar.get("price_basis") == "RAW_REGULAR_SESSION_CLOSE"
            and bar.get("currency") == "USD"
        )
        if valid:
            prices[ticker] = {
                "price": price,
                "value_status": "VERIFIED",
                "basis": "RAW_REGULAR_SESSION_CLOSE",
                "session": item.get("bar_date") or bar.get("reported_session"),
                "provider": bar.get("provider"),
                "provider_timestamp": bar.get("provider_timestamp"),
            }
    for ticker in sorted(required - set(prices)):
        issues.append(f"MISSING_VERIFIED_CANONICAL_PRICE:{ticker}")
    return prices, issues


def _instrument_mapping(
    ticker: str, risk_policy: dict[str, Any], registry: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    fallback = (risk_policy.get("fallback_instrument_mapping") or {}).get(ticker)
    registered = ((registry or {}).get("instruments") or {}).get(ticker)
    if fallback is None and registered is None:
        return None, "RISK_MAPPING_REQUIRED"
    if fallback is None:
        factor = _decimal(registered.get("leverage_factor"))
        if factor is None or registered.get("leverage_factor_status") not in {
            "verified", "verified_by_existing_active_policy"
        } or factor < 0:
            return None, "RISK_MAPPING_UNVERIFIED"
        instrument_class = "NORMAL_STOCK" if factor == 1 else "LEVERAGED_PRODUCT"
        return {
            "instrument_class": instrument_class,
            "leverage_factor": factor,
            "growth_ai_semiconductor_cluster": registered.get("theme") in {
                "ai_infrastructure", "leveraged_semiconductor", "semiconductor"
            },
            "mapping_source": "INSTRUMENT_REGISTRY",
        }, None
    mapping = dict(fallback)
    mapping["mapping_source"] = "USER_APPROVED_FALLBACK"
    if registered is not None:
        registered_factor = _decimal(registered.get("leverage_factor"))
        fallback_factor = _decimal(fallback["leverage_factor"])
        if registered_factor is not None and registered_factor != fallback_factor:
            return None, "RISK_MAPPING_CONFLICT"
        if registered_factor is not None:
            mapping["mapping_source"] = "INSTRUMENT_REGISTRY_CONFIRMED"
    mapping["leverage_factor"] = _decimal(mapping["leverage_factor"])
    return mapping, None


def _risk_status(value: Decimal | None, *, low: Any = None, high: Any = None,
                 hard_low: Any = None, hard_high: Any = None) -> str:
    if value is None:
        return "BLOCKED"
    low_value, high_value = _decimal(low), _decimal(high)
    hard_low_value, hard_high_value = _decimal(hard_low), _decimal(hard_high)
    if hard_low_value is not None and value < hard_low_value:
        return "VIOLATION"
    if hard_high_value is not None and value > hard_high_value:
        return "VIOLATION"
    if low_value is not None and value < low_value:
        return "WARNING"
    if high_value is not None and value > high_value:
        return "WARNING"
    return "PASS"


def calculate_risk_metrics(
    weights: dict[str, Decimal], cash_pct: Decimal | None,
    mappings: dict[str, dict[str, Any]], policy: dict[str, Any],
) -> dict[str, Any]:
    zero = Decimal("0")
    leveraged = sum((weight for ticker, weight in weights.items() if mappings[ticker]["leverage_factor"] > 1), zero)
    cluster_book = sum((weight for ticker, weight in weights.items() if mappings[ticker]["growth_ai_semiconductor_cluster"]), zero)
    cluster_adjusted = sum((
        weight * mappings[ticker]["leverage_factor"] for ticker, weight in weights.items()
        if mappings[ticker]["growth_ai_semiconductor_cluster"]
    ), zero)
    overall_adjusted = sum((weight * mappings[ticker]["leverage_factor"] for ticker, weight in weights.items()), zero)
    checks: list[dict[str, Any]] = []
    cash_rule = policy["cash"]
    checks.append({"metric": "CASH_PCT", "value": cash_pct,
                   "status": _risk_status(cash_pct, low=cash_rule["target_min_pct"], high=cash_rule["target_max_pct"], hard_low=cash_rule["hard_floor_pct"])})
    lev_rule = policy["all_daily_reset_leveraged_products"]
    checks.append({"metric": "LEVERAGED_PRODUCTS_PCT", "value": leveraged,
                   "status": _risk_status(leveraged, low=lev_rule["target_min_pct"], high=lev_rule["target_max_pct"], hard_high=lev_rule["hard_cap_pct"])})
    for ticker, weight in sorted(weights.items()):
        klass = mappings[ticker]["instrument_class"]
        rule = None
        if klass == "SINGLE_3X_ETF":
            rule = policy["single_3x_etf"]
        elif klass == "SINGLE_2X_SINGLE_STOCK_ETF":
            rule = policy["single_2x_single_stock_etf"]
        elif klass == "NORMAL_STOCK":
            rule = policy["single_normal_stock"]
        if rule:
            checks.append({"metric": f"POSITION_PCT:{ticker}", "value": weight,
                           "status": _risk_status(weight, low=rule["target_min_pct"], high=rule["target_max_pct"], hard_high=rule["hard_cap_pct"])})
    cluster_rule = policy["growth_ai_semiconductor_cluster"]
    checks.extend([
        {"metric": "GROWTH_AI_SEMI_BOOK_PCT", "value": cluster_book,
         "status": _risk_status(cluster_book, hard_high=cluster_rule["book_hard_cap_pct"])},
        {"metric": "GROWTH_AI_SEMI_LEVERAGE_ADJUSTED_PCT", "value": cluster_adjusted,
         "status": _risk_status(cluster_adjusted, hard_high=cluster_rule["leverage_adjusted_hard_cap_pct"])},
    ])
    overall_rule = policy["overall_leverage_adjusted_exposure_proxy"]
    checks.append({"metric": "OVERALL_LEVERAGE_ADJUSTED_PROXY_PCT", "value": overall_adjusted,
                   "status": _risk_status(overall_adjusted, low=overall_rule["target_min_pct"], high=overall_rule["target_max_pct"], hard_high=overall_rule["hard_cap_pct"])})
    for item in checks:
        item["value"] = _json_number(item["value"])
    violations = [item["metric"] for item in checks if item["status"] == "VIOLATION"]
    aggregate_status = (
        "VIOLATION" if violations else
        "BLOCKED" if any(i["status"] == "BLOCKED" for i in checks) else
        "WARNING" if any(i["status"] == "WARNING" for i in checks) else "PASS"
    )
    return {
        "cash_pct": _value(cash_pct, "DERIVED" if cash_pct is not None else "PROVISIONAL", "PCT"),
        "leveraged_products_pct": _value(leveraged, "DERIVED", "PCT"),
        "growth_ai_semiconductor_book_pct": _value(cluster_book, "DERIVED", "PCT"),
        "growth_ai_semiconductor_leverage_adjusted_pct": _value(cluster_adjusted, "DERIVED", "PCT"),
        "overall_leverage_adjusted_proxy_pct": _value(overall_adjusted, "DERIVED", "PCT"),
        "checks": checks,
        "hard_cap_violations": violations,
        "status": aggregate_status,
    }


def _event_context(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"status": "NOT_PROVIDED", "current_high_count": None, "new_high_count": None,
                "affected_tickers": [], "automatic_target_change": False}
    summary = value.get("summary") or {}
    high = value.get("current_high_count", summary.get("current_high_count", 0))
    new = value.get("new_high_count", summary.get("new_high_count", 0))
    affected = value.get("affected_tickers", summary.get("affected_tickers", []))
    status = value.get("status") or ("ASSET_REVIEW_REQUIRED" if high or new or affected else "AVAILABLE")
    return {"status": status, "current_high_count": int(high or 0), "new_high_count": int(new or 0),
            "affected_tickers": sorted({_ticker(item) for item in affected if _ticker(item)}),
             "automatic_target_change": False}


def _evaluate_current_session_context(
    context: Any, evidence: dict[str, Any], evidence_sha256: str | None,
    schema_bytes: bytes, dashboard_generated_at: str,
    authority_resolver: Callable[..., Any],
) -> dict[str, Any]:
    if context is None:
        return {"status": "ABSENT", "verified": False, "blockers": ["CURRENT_SESSION_CONTEXT_REQUIRED"],
                "schema_errors": [], "context": None}
    if not isinstance(context, dict):
        return {"status": "PRESENT_INVALID", "verified": False,
                "blockers": ["CURRENT_SESSION_CONTEXT_INVALID"], "schema_errors": ["$: type"], "context": None}
    schema_errors = validate_instance(context, CURRENT_SESSION_CONTEXT_SCHEMA, schema_bytes=schema_bytes)
    blockers = [f"CURRENT_SESSION_CONTEXT_SCHEMA_INVALID:{item}" for item in schema_errors]
    if not schema_errors:
        expected_pairs = (
            ("expected_evidence_run_id", evidence.get("manual_run_id"), "CURRENT_CONTEXT_RUN_ID_MISMATCH"),
            ("expected_evidence_sha256", evidence_sha256, "CURRENT_CONTEXT_EVIDENCE_SHA256_MISMATCH"),
            ("expected_evidence_decision_as_of", evidence.get("decision_as_of"), "CURRENT_CONTEXT_DECISION_AS_OF_MISMATCH"),
            ("expected_completed_us_session", evidence.get("expected_completed_us_session"), "CURRENT_CONTEXT_SESSION_MISMATCH"),
            ("market_phase", evidence.get("market_phase"), "CURRENT_CONTEXT_MARKET_PHASE_MISMATCH"),
            ("session_authority_market_phase", evidence.get("session_authority_market_phase"), "CURRENT_CONTEXT_AUTHORITY_PHASE_MISMATCH"),
            ("calendar_policy_identity", evidence.get("calendar_policy_identity"), "CURRENT_CONTEXT_CALENDAR_POLICY_MISMATCH"),
            ("calendar_hash", evidence.get("calendar_hash"), "CURRENT_CONTEXT_CALENDAR_HASH_MISMATCH"),
            ("session_activation_cohort_id", evidence.get("session_activation_cohort_id"), "CURRENT_CONTEXT_SESSION_COHORT_MISMATCH"),
        )
        for field, expected, reason in expected_pairs:
            if expected is None or context.get(field) != expected:
                blockers.append(reason)
        if evidence_sha256 is None:
            blockers.append("EVIDENCE_RAW_SHA256_REQUIRED")
        if context.get("context_status") != "VERIFIED_CURRENT_SESSION":
            blockers.append("CURRENT_SESSION_CONTEXT_NOT_VERIFIED")
        context_time = _parse_timestamp(context.get("context_generated_at"))
        evidence_time = _parse_timestamp(evidence.get("decision_as_of"))
        if context_time is None or evidence_time is None or context_time < evidence_time:
            blockers.append("CURRENT_CONTEXT_GENERATED_BEFORE_EVIDENCE")
        evaluation_time = _parse_timestamp(dashboard_generated_at)
        if context_time is not None and (evaluation_time is None or context_time > evaluation_time):
            blockers.append("CURRENT_CONTEXT_GENERATED_AFTER_EVALUATION")
        try:
            canonical_runtime = authority_resolver(
                dashboard_generated_at,
                primary_listing_operating_mic=context.get("primary_listing_operating_mic"),
                decision_as_of=dashboard_generated_at,
            )
        except (OSError, ValueError):
            canonical_runtime = None
        if canonical_runtime is None or canonical_runtime.authority_status != "VERIFIED":
            blockers.append("CURRENT_CONTEXT_CANONICAL_RUNTIME_NOT_VERIFIED")
        else:
            current_expected_session = (
                canonical_runtime.expected_completed_session.session_date
                if canonical_runtime.expected_completed_session is not None else None
            )
            if context.get("expected_completed_us_session") != current_expected_session:
                blockers.append("CURRENT_CONTEXT_NOT_CURRENT_CANONICAL_SESSION")
            if context.get("session_authority_market_phase") != canonical_runtime.market_phase:
                blockers.append("CURRENT_CONTEXT_NOT_CURRENT_CANONICAL_PHASE")
            if context.get("calendar_policy_identity") != canonical_runtime.calendar_policy_identity:
                blockers.append("CURRENT_CONTEXT_RUNTIME_CALENDAR_POLICY_MISMATCH")
            if context.get("calendar_hash") != canonical_runtime.calendar_hash:
                blockers.append("CURRENT_CONTEXT_RUNTIME_CALENDAR_HASH_MISMATCH")
            if context.get("session_activation_cohort_id") != canonical_runtime.activation_cohort_id:
                blockers.append("CURRENT_CONTEXT_RUNTIME_SESSION_COHORT_MISMATCH")
        expected_session = evidence.get("expected_completed_us_session")
        if evidence.get("market_phase") == "REGULAR_COMPLETED" and (
            evidence.get("current_session_finalization_status") != "VERIFIED"
            or evidence.get("last_verified_finalized_bar_date") != expected_session
        ):
            blockers.append("CURRENT_CONTEXT_CANONICAL_SESSION_RELATION_FAILED")
    verified = not blockers
    status = "VERIFIED" if verified else ("PRESENT_INVALID" if schema_errors else "PRESENT_MISMATCH")
    return {"status": status, "verified": verified, "blockers": sorted(set(blockers)),
            "schema_errors": schema_errors, "context": context}


def _evaluate_request_accounting(
    accounting: Any, evidence: dict[str, Any], evidence_sha256: str | None,
    schema_bytes: bytes,
) -> dict[str, Any]:
    operations = (evidence.get("broker_observed_state") or {}).get("operation_statuses")
    if accounting is None:
        if operations is None or operations == {}:
            return {"status": "ABSENT", "verified": False, "issues": [], "details": None}
        if not isinstance(operations, dict) or any(
            not isinstance(name, str) or not name or not isinstance(status, str) or not status
            for name, status in operations.items()
        ):
            return {"status": "PRESENT_INVALID", "verified": False,
                    "issues": ["LEGACY_OPERATION_STATUS_INVALID"], "details": None}
        return {"status": "PRESENT_UNVERIFIED", "verified": False,
                "issues": ["VERIFIED_REQUEST_ACCOUNTING_ARTIFACT_REQUIRED"], "details": None}
    if not isinstance(accounting, dict):
        return {"status": "PRESENT_INVALID", "verified": False,
                "issues": ["REQUEST_ACCOUNTING_NOT_OBJECT"], "details": None}
    schema_errors = validate_instance(accounting, REQUEST_ACCOUNTING_SCHEMA, schema_bytes=schema_bytes)
    issues = [f"REQUEST_ACCOUNTING_SCHEMA_INVALID:{item}" for item in schema_errors]
    if not schema_errors:
        total = accounting["http_request_count"]
        if not accounting["operation_counts"]:
            issues.append("REQUEST_ACCOUNTING_OPERATION_COUNTS_EMPTY")
        if not accounting["endpoint_counts"]:
            issues.append("REQUEST_ACCOUNTING_ENDPOINT_COUNTS_EMPTY")
        if accounting["successful_request_count"] + accounting["failed_request_count"] != total:
            issues.append("REQUEST_ACCOUNTING_RESULT_TOTAL_MISMATCH")
        if sum(accounting["operation_counts"].values()) != total:
            issues.append("REQUEST_ACCOUNTING_OPERATION_TOTAL_MISMATCH")
        if sum(accounting["endpoint_counts"].values()) != total:
            issues.append("REQUEST_ACCOUNTING_ENDPOINT_TOTAL_MISMATCH")
        if accounting["retry_count"] > total:
            issues.append("REQUEST_ACCOUNTING_RETRY_COUNT_EXCEEDS_REQUESTS")
    if issues:
        return {"status": "PRESENT_INVALID", "verified": False,
                "issues": sorted(set(issues)), "details": accounting}
    binding_issues: list[str] = []
    if accounting.get("verification_status") != "VERIFIED_EXACT":
        binding_issues.append("REQUEST_ACCOUNTING_NOT_VERIFIED_EXACT")
    if accounting.get("source_run_id") != evidence.get("manual_run_id"):
        binding_issues.append("REQUEST_ACCOUNTING_RUN_ID_MISMATCH")
    if evidence_sha256 is None or accounting.get("source_artifact_sha256") != evidence_sha256:
        binding_issues.append("REQUEST_ACCOUNTING_SOURCE_SHA256_MISMATCH")
    return {
        "status": "VERIFIED" if not binding_issues else "PRESENT_UNVERIFIED",
        "verified": not binding_issues,
        "issues": sorted(set(binding_issues)),
        "details": accounting,
    }


def _canonical_evidence_gate(
    evidence: dict[str, Any], plan: dict[str, Any], compile_mode: str, schema_bytes: bytes,
    *, input_mode: str = "MANUAL_READ_ONLY",
    parent_capture_artifacts: list[tuple[bytes, str]] | None = None,
    analysis_observed_at: str | None = None,
) -> tuple[list[str], list[str], set[str]]:
    schema_errors = validate_instance(evidence, MANUAL_EVIDENCE_SCHEMA, schema_bytes=schema_bytes)
    schema = json.loads(schema_bytes.decode("utf-8"))
    phases = set(schema["properties"]["market_phase"]["enum"])
    blockers = [f"CANONICAL_EVIDENCE_SCHEMA_INVALID:{item}" for item in schema_errors]
    direction_scope_verified = False
    direction_scope_declared = (evidence.get("manual_analysis_view") or {}).get("decision_evidence_scope") is not None
    if (input_mode == "MANUAL_READ_ONLY" and compile_mode == "INITIAL_COMPILE"
            and direction_scope_declared and analysis_observed_at is not None):
        from run_manual_portfolio_analysis import validate_manual_direction_evidence
        direction_scope_verified = validate_manual_direction_evidence(
            evidence, parent_capture_artifacts, analysis_observed_at=analysis_observed_at,
        )
    required_values = {
        "EVIDENCE_GRADE_NOT_GRADE_B": evidence.get("evidence_grade") == ("GRADE_A" if input_mode == "LIVE_READ_ONLY" else "GRADE_B"),
        "MANUAL_DATA_NOT_VERIFIED_REAL": evidence.get("manual_data_verification_status") == "VERIFIED_REAL_DATA",
        "RUN_PROVENANCE_NOT_VERIFIED_MANUAL": evidence.get("run_provenance_status") == ("VERIFIED_SCHEDULED" if input_mode == "LIVE_READ_ONLY" else "VERIFIED_MANUAL"),
        "PREFLIGHT_NOT_PASS": evidence.get("preflight_status") == "PASS" or direction_scope_verified,
        "BROKER_SNAPSHOT_NOT_AVAILABLE": evidence.get("broker_snapshot_status") == "AVAILABLE",
        "BROKER_OBSERVED_STATE_NOT_AVAILABLE": (evidence.get("broker_observed_state") or {}).get("status") == "AVAILABLE",
        "ORDERABLE_CASH_NOT_VERIFIED": evidence.get("orderable_cash_status") == "VERIFIED",
        "FINALIZED_BAR_PREFLIGHT_NOT_PASS": evidence.get("finalized_bar_preflight_status") == "PASS",
        "FINALIZED_BAR_NOT_VERIFIED": evidence.get("last_verified_finalized_bar_status") == "VERIFIED",
        "IDENTITY_AUTHORITY_NOT_VERIFIED": evidence.get("identity_authority_status") == "VERIFIED",
        "SESSION_AUTHORITY_NOT_VERIFIED": evidence.get("session_authority_status") == "VERIFIED",
        "AUTHORITY_COHORT_NOT_MATCHED": evidence.get("integrated_authority_cohort_status") == "MATCHED",
        "DECISION_QUALITY_NOT_ELIGIBLE": (evidence.get("provenance") or {}).get("decision_quality_eligible") is True,
    }
    if direction_scope_declared and not direction_scope_verified:
        blockers.append("DIRECTION_SCOPE_INPUTS_NOT_VERIFIED")
    blockers.extend(reason for reason, satisfied in required_values.items() if not satisfied)
    operations = (evidence.get("broker_observed_state") or {}).get("operation_statuses") or {}
    for operation in ("account_holdings_read", "account_deposit_read"):
        if not isinstance(operations, dict) or operations.get(operation) != "PASS":
            blockers.append(f"CORE_BROKER_OPERATION_NOT_PASS:{operation}")

    view = evidence.get("manual_analysis_view") or {}
    handoff_present = isinstance(view, dict) and "acquisition_handoff" in view
    handoff_verified = False
    if handoff_present or parent_capture_artifacts is not None:
        from run_manual_portfolio_analysis import validate_manual_acquisition_handoff
        handoff_verified = (
            input_mode == "MANUAL_READ_ONLY"
            and analysis_observed_at is not None
            and validate_manual_acquisition_handoff(
                evidence, parent_capture_artifacts,
                analysis_observed_at=analysis_observed_at, maximum_age_seconds=900,
            )
        )
        if not handoff_verified:
            blockers.append("ACQUISITION_HANDOFF_NOT_VERIFIED")

    decision_time = _parse_timestamp(evidence.get("decision_as_of"))
    observed_time = _parse_timestamp(evidence.get("observed_at"))
    broker_time = _parse_timestamp(evidence.get("broker_snapshot_as_of"))
    if decision_time is None or observed_time is None or broker_time is None:
        blockers.append("EVIDENCE_FRESHNESS_TIMESTAMP_INVALID")
    else:
        if broker_time > decision_time:
            blockers.append("EVIDENCE_FROM_FUTURE")
        if observed_time > decision_time and not handoff_verified:
            view = evidence.get("manual_analysis_view")
            view = view if isinstance(view, dict) else {}
            analysis_time = _parse_timestamp(view.get("analysis_observed_at"))
            acquisition_time = _parse_timestamp(view.get("acquisition_completed_at"))
            if analysis_time == observed_time and acquisition_time == decision_time:
                # A later analysis is not a later Broker response, but remains
                # ineligible for the fresh gate. Self-asserted metadata grants no pass.
                blockers.append("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE")
            else:
                blockers.append("EVIDENCE_FROM_FUTURE")
        if (decision_time - broker_time).total_seconds() > 900:
            blockers.append("BROKER_SNAPSHOT_STALE")

    evidence_run_id = evidence.get("manual_run_id")
    evidence_as_of = evidence.get("decision_as_of")
    binding = plan.get("evidence_binding") or {}
    if compile_mode == "POST_SELL_RECOMPILE":
        refresh = plan.get("post_sell_refresh") or {}
        if not refresh:
            blockers.append("POST_SELL_REFRESH_BINDING_REQUIRED")
        if (refresh.get("prior_run_id"), refresh.get("prior_decision_as_of")) != (
            binding.get("expected_run_id"), binding.get("expected_decision_as_of"),
        ):
            blockers.append("POST_SELL_PRIOR_BINDING_MISMATCH")
        if evidence_run_id == refresh.get("prior_run_id"):
            blockers.append("POST_SELL_FRESH_RUN_REQUIRED")
        current_time = _parse_timestamp(evidence_as_of)
        prior_time = _parse_timestamp(refresh.get("prior_decision_as_of"))
        if current_time is None or prior_time is None or current_time <= prior_time:
            blockers.append("POST_SELL_DECISION_AS_OF_NOT_LATER")
        plan_time = _parse_timestamp(plan.get("as_of"))
        if plan_time is None or prior_time is None or plan_time > prior_time:
            blockers.append("PLAN_AS_OF_AFTER_BOUND_EVIDENCE")
    else:
        if evidence_run_id != binding.get("expected_run_id"):
            blockers.append("EVIDENCE_RUN_ID_BINDING_MISMATCH")
        if evidence_as_of != binding.get("expected_decision_as_of"):
            blockers.append("EVIDENCE_DECISION_AS_OF_BINDING_MISMATCH")
        plan_time = _parse_timestamp(plan.get("as_of"))
        evidence_time = _parse_timestamp(evidence_as_of)
        if plan_time is None or evidence_time is None or plan_time > evidence_time:
            blockers.append("PLAN_AS_OF_AFTER_BOUND_EVIDENCE")
    return schema_errors, sorted(set(blockers)), phases


def compile_dashboard(
    evidence: dict[str, Any], plan: dict[str, Any], risk_policy: dict[str, Any],
    *, compile_mode: str = "INITIAL_COMPILE", registry: dict[str, Any] | None = None,
    event_context: dict[str, Any] | None = None, run_id: str = "portfolio-decision-test",
    generated_at: str | None = None, runtime_advisory_authority: str | None = None,
    current_session_context: dict[str, Any] | None = None,
    request_accounting: dict[str, Any] | None = None,
    evidence_sha256: str | None = None,
    current_session_authority_resolver: Callable[..., Any] = derive_us_market_session_authority,
    evidence_schema_bytes: bytes | None = None, plan_schema_bytes: bytes | None = None,
    dashboard_schema_bytes: bytes | None = None, current_context_schema_bytes: bytes | None = None,
    request_accounting_schema_bytes: bytes | None = None,
    input_mode: str = "MANUAL_READ_ONLY", scheduled_provenance: dict[str, Any] | None = None,
    expected_runtime_head: str | None = None,
    parent_capture_artifacts: list[tuple[bytes, str]] | None = None,
    holding_timing_inputs: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if compile_mode not in ALLOWED_MODES:
        raise ContractError("INVALID_COMPILE_MODE")
    evidence_schema_bytes = evidence_schema_bytes or manual_evidence_schema_bytes(
        evidence,
        allow_legacy_replay=compile_mode == "HISTORICAL_REPLAY",
    )
    plan_schema_bytes = plan_schema_bytes or PLAN_SCHEMA.read_bytes()
    dashboard_schema_bytes = dashboard_schema_bytes or DASHBOARD_SCHEMA.read_bytes()
    current_context_schema_bytes = current_context_schema_bytes or CURRENT_SESSION_CONTEXT_SCHEMA.read_bytes()
    request_accounting_schema_bytes = request_accounting_schema_bytes or REQUEST_ACCOUNTING_SCHEMA.read_bytes()
    generated = generated_at or _now()
    trigger_provenance = None
    if input_mode == "LIVE_READ_ONLY":
        if not isinstance(plan, dict) or plan.get("plan_status") != CURRENT_PLAN_STATUS:
            raise ContractError("CURRENT_APPROVED_DECISION_PLAN_REQUIRED")
        if compile_mode != "INITIAL_COMPILE":
            raise ContractError("SCHEDULED_INITIAL_COMPILE_REQUIRED")
        if not evidence_sha256 or not expected_runtime_head:
            raise ContractError("SCHEDULED_EXPECTED_HEAD_AND_EVIDENCE_HASH_REQUIRED")
        from run_manual_portfolio_analysis import validate_scheduled_input
        try:
            trigger_provenance = validate_scheduled_input(
                evidence, scheduled_provenance, evidence_sha256=evidence_sha256,
                expected_head=expected_runtime_head, runtime_repo=ROOT,
                session_authority_resolver=current_session_authority_resolver,
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise ContractError(str(exc)) from exc
    elif input_mode != "MANUAL_READ_ONLY" or scheduled_provenance is not None:
        raise ContractError("INVALID_INPUT_MODE")
    elif (evidence.get("run_mode") != "MANUAL_READ_ONLY"
          or evidence.get("trigger_type") != "USER_INITIATED"
          or evidence.get("operator_initiated") is not True
          or evidence.get("scheduled_occurrence_id") is not None
          or evidence.get("report_type") != "MANUAL_PORTFOLIO_ANALYSIS_PREFLIGHT"
          or (evidence.get("provenance") or {}).get("execution_origin") != "MANUAL"
          or (evidence.get("provenance") or {}).get("decision_mode") != "MANUAL_READ_ONLY"
          or (evidence.get("provenance") or {}).get("run_provenance_status") != "VERIFIED_MANUAL"
          or (evidence.get("provenance") or {}).get("evidence_grade") != evidence.get("evidence_grade")):
        raise ContractError("MANUAL_INPUT_MODE_MISMATCH")
    if not isinstance(plan, dict):
        raise ContractError("DECISION_PLAN_INVALID")
    plan_errors = validate_plan(plan, schema_bytes=plan_schema_bytes)
    if plan_errors:
        raise ContractError("DECISION_PLAN_INVALID:" + "; ".join(plan_errors))
    evidence_schema_errors, evidence_gate_blockers, canonical_phases = _canonical_evidence_gate(
        evidence, plan, compile_mode, evidence_schema_bytes, input_mode=input_mode,
        parent_capture_artifacts=parent_capture_artifacts, analysis_observed_at=generated,
    )
    current_context_result = _evaluate_current_session_context(
        current_session_context, evidence, evidence_sha256, current_context_schema_bytes, generated,
        current_session_authority_resolver,
    )
    request_accounting_result = _evaluate_request_accounting(
        request_accounting, evidence, evidence_sha256, request_accounting_schema_bytes,
    )
    positions = {item["ticker"]: item for item in plan["positions"]}
    holdings, costs, holding_issues, holding_source = _extract_holdings(evidence)
    current_cash, orderable_cash, cash_issues = _extract_cash(evidence)
    # Display Broker orderable cash separately; never expand the old funding cap.
    settled_cash = _decimal(
        ((evidence.get("broker_observed_state") or {}).get("cash") or {}).get("settled_available_cash")
    )
    funding_cash = (
        min(orderable_cash, settled_cash)
        if orderable_cash is not None and settled_cash is not None and settled_cash >= 0
        else None
    )
    required_tickers = set(holdings) | set(positions)
    prices, price_issues = _extract_prices(evidence, required_tickers)
    issues = holding_issues + cash_issues + price_issues + evidence_gate_blockers
    warnings: list[str] = []
    input_authority_blockers: list[str] = []
    if evidence.get("order_authority") is not False:
        input_authority_blockers.append("INPUT_ORDER_AUTHORITY_NOT_FALSE")
    if evidence.get("execution_quantity") is not None:
        input_authority_blockers.append("INPUT_EXECUTION_QUANTITY_NOT_NULL")
    broker_input = evidence.get("broker_observed_state") or {}
    if broker_input.get("portfolio_mutation") is True or broker_input.get("canonical_apply") is True:
        input_authority_blockers.append("INPUT_PORTFOLIO_MUTATION_DETECTED")
    issues.extend(input_authority_blockers)
    if evidence.get("broker_diff_status") == "DIFFERENT":
        warnings.append("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL")
    operations = (evidence.get("broker_observed_state") or {}).get("operation_statuses") or {}
    open_items_status = operations.get("account_open_items") if isinstance(operations, dict) else None
    if open_items_status != "PASS":
        warnings.append("OPEN_ITEMS_VISIBILITY_UNAVAILABLE")
    if (evidence.get("broker_observed_state") or {}).get("scope_complete") is not True:
        warnings.append("AUXILIARY_SCOPE_INCOMPLETE_CORE_MAY_REMAIN_VERIFIED")
    request_accounting_status = request_accounting_result["status"]
    if request_accounting_status == "PRESENT_INVALID":
        warnings.append("REQUEST_ACCOUNTING_INVALID")
    elif request_accounting_status == "PRESENT_UNVERIFIED":
        warnings.append("REQUEST_ACCOUNTING_NOT_CANONICALLY_VERIFIABLE")

    mappings: dict[str, dict[str, Any]] = {}
    for ticker in sorted(required_tickers):
        mapping, mapping_issue = _instrument_mapping(ticker, risk_policy, registry)
        if mapping_issue:
            issues.append(f"{mapping_issue}:{ticker}")
        elif mapping:
            mappings[ticker] = mapping

    nav: Decimal | None = None
    values: dict[str, Decimal] = {}
    weights: dict[str, Decimal] = {}
    positive_holdings = {ticker for ticker, quantity in holdings.items() if quantity > 0}
    if current_cash is not None and holdings and all(ticker in prices for ticker in positive_holdings):
        values = {
            ticker: Decimal(quantity) * prices[ticker]["price"] if quantity > 0 else Decimal("0")
            for ticker, quantity in holdings.items()
        }
        nav = current_cash + sum(values.values())
        if nav <= 0:
            nav = None
            issues.append("NAV_NOT_POSITIVE")
        else:
            weights = {ticker: value / nav * Decimal("100") for ticker, value in values.items()}
    else:
        issues.append("NAV_BLOCKED_REQUIRED_CORE_EVIDENCE")
    core_blockers = bool(
        holding_issues or current_cash is None
        or input_authority_blockers
        or evidence_gate_blockers
        or any(issue.endswith(tuple(f":{ticker}" for ticker in positive_holdings)) for issue in price_issues)
    )
    evidence_contract_verified = not evidence_gate_blockers
    core_status = (
        "BLOCKED" if nav is None or core_blockers else
        "VERIFIED" if evidence_contract_verified else "PARTIAL"
    )
    current_risk = None
    if nav is not None and set(weights) <= set(mappings):
        current_risk = calculate_risk_metrics(weights, current_cash / nav * Decimal("100"), mappings, risk_policy)
    current_violations = set((current_risk or {}).get("hard_cap_violations") or [])
    target_weights = {
        ticker: _decimal(item["target_weight_pct"]) for ticker, item in positions.items()
        if item.get("target_weight_pct") is not None and ticker in mappings
    }
    target_risk = calculate_risk_metrics(
        target_weights, _decimal(plan["cash_target_pct"]) if plan.get("cash_target_pct") is not None else None,
        mappings, risk_policy,
    ) if set(target_weights) <= set(mappings) else None
    target_violations = set((target_risk or {}).get("hard_cap_violations") or [])

    position_rows: list[dict[str, Any]] = []
    direction_only_evidence = (
        (evidence.get("manual_analysis_view") or {}).get("decision_evidence_scope")
            == "EXISTING_HOLDINGS_AND_CASH_DIRECTION_ONLY"
    )
    all_tickers = sorted(set(holdings) | set(positions))
    for ticker in all_tickers:
        source = positions.get(ticker)
        current_quantity = holdings.get(ticker, 0)
        price = prices.get(ticker, {}).get("price")
        current_weight = weights.get(ticker) if nav is not None else None
        blockers: list[str] = []
        if direction_only_evidence:
            blockers.append("DIRECTION_ONLY_EVIDENCE_NO_QUANTITY_AUTHORITY")
        if source is None:
            blockers.append("BLOCKED_DECISION_PLAN_POSITION_REQUIRED")
            source = {"ticker": ticker, "action": "HOLD", "target_status": "BLOCKED",
                      "rationale": "Decision Plan entry required", "investment_horizon": "Not specified"}
        target_weight = source.get("target_weight_pct")
        if target_weight is None:
            blockers.append("BLOCKED_TARGET_WEIGHT_REQUIRED")
        if price is None:
            blockers.append("BLOCKED_CANONICAL_PRICE_REQUIRED")
        if ticker not in mappings:
            blockers.append("BLOCKED_RISK_MAPPING_REQUIRED")
        if nav is None:
            blockers.append("BLOCKED_NAV_REQUIRED")
        target_shares = None
        delta = None
        if not blockers and target_weight is not None and price and nav is not None:
            target_shares = _floor_shares(nav, target_weight, price)
            delta = target_shares - current_quantity
        if target_violations:
            blockers.append("TARGET_HARD_CAP_VIOLATION")
            delta = None
        deadband = False
        if (delta is not None and current_weight is not None and target_weight is not None
                and abs((_decimal(target_weight) or Decimal("0")) - current_weight)
                    < (_decimal(risk_policy["deadband"]["absolute_percentage_points"]) or Decimal("0"))
                and not current_violations and not target_violations
                and not blockers and source.get("thesis_kill") is not True):
            deadband = True
            delta = 0
        direction_conflict = bool(
            delta is not None and ((source["action"] in {"TRIM", "EXIT"} and delta > 0)
                                   or (source["action"] == "ADD" and delta < 0))
        )
        if direction_conflict:
            blockers.append("ACTION_TARGET_DIRECTION_CONFLICT")
            delta = None
        position_rows.append({
            "ticker": ticker,
            "action": source["action"],
            "target_status": source["target_status"],
            "current_quantity": _value(current_quantity, "VERIFIED" if ticker in holdings else "DERIVED", "SHARES"),
            "average_cost_usd": _value(costs.get(ticker), "VERIFIED" if ticker in costs else "NOT_VERIFIED", "USD"),
            "canonical_price_usd": _value(price, "VERIFIED" if price is not None else "NOT_VERIFIED", "USD"),
            "price_session": prices.get(ticker, {}).get("session"),
            "current_market_value_usd": _value(values.get(ticker, Decimal("0") if nav is not None else None), "DERIVED" if nav is not None else "PROVISIONAL", "USD"),
            "current_weight_pct": _value(current_weight, "DERIVED" if current_weight is not None else "PROVISIONAL", "PCT"),
            "target_weight_pct": _value(_decimal(target_weight) if target_weight is not None else None, "VERIFIED" if target_weight is not None else "NOT_VERIFIED", "PCT"),
            "target_shares_reference": _value(target_shares, "DERIVED" if target_shares is not None else "PROVISIONAL", "SHARES"),
            "share_delta": _value(delta, "DERIVED" if delta is not None else "PROVISIONAL", "SHARES"),
            "deadband_status": "NO_TRADE_PREFERRED" if deadband else "NOT_APPLIED",
            "calculation_status": "BLOCKED" if blockers else ("NO_TRADE_PREFERRED" if deadband else "CALCULATED_MANUAL_ADVISORY"),
            "blockers": sorted(set(blockers)),
            "rationale": _safe_swing_text(source["rationale"]),
            "investment_horizon": source["investment_horizon"],
            "material_risk": source.get("material_risk"),
            "decision_change_triggers": [_safe_swing_text(item) for item in source.get("decision_change_triggers") or []],
        })

    replay = compile_mode == "HISTORICAL_REPLAY" or plan["plan_status"] in {"HISTORICAL", "REPLAY_ONLY"}
    stage1_rows: list[dict[str, Any]] = []
    for row in position_rows:
        delta = row["share_delta"]["value"]
        if row["action"] not in {"TRIM", "EXIT"}:
            continue
        sell = abs(delta) if isinstance(delta, int) and delta < 0 else 0 if delta == 0 else None
        stage1_rows.append({
            "ticker": row["ticker"], "action": row["action"],
            "current_shares": row["current_quantity"]["value"],
            "target_shares_reference": row["target_shares_reference"]["value"],
            "calculated_sell_shares": sell,
            "current_weight_pct": row["current_weight_pct"]["value"],
            "target_weight_pct": row["target_weight_pct"]["value"],
            "reason": row["rationale"], "risk_violation_addressed": sorted(current_violations),
            "status": row["calculation_status"], "blockers": row["blockers"],
        })
    sell_rows = [row for row in stage1_rows if isinstance(row["calculated_sell_shares"], int) and row["calculated_sell_shares"] > 0]
    expected_proceeds = None
    if sell_rows and all(row["ticker"] in prices for row in sell_rows):
        expected_proceeds = sum((
            Decimal(row["calculated_sell_shares"]) * prices[row["ticker"]]["price"] for row in sell_rows
        ), Decimal("0"))
    post_sell_estimated_cash = (
        current_cash + expected_proceeds if current_cash is not None and expected_proceeds is not None else None
    )
    if any(row["calculated_sell_shares"] is None for row in stage1_rows) or nav is None:
        stage1_status = "BLOCKED"
    elif replay:
        stage1_status = "REPLAY_ONLY"
    elif evidence.get("market_phase") not in canonical_phases or evidence.get("market_phase") != "REGULAR_COMPLETED":
        stage1_status = "PROVISIONAL"
    elif evidence.get("current_session_finalization_status") != "VERIFIED":
        stage1_status = "PROVISIONAL"
    elif plan["plan_status"] != CURRENT_PLAN_STATUS or any(row.get("target_status") != "APPROVED" for row in position_rows):
        stage1_status = "PROVISIONAL"
    elif core_status == "VERIFIED" and current_context_result["verified"]:
        stage1_status = "FINAL_MANUAL_ADVISORY_ELIGIBLE"
    elif core_status == "VERIFIED":
        stage1_status = "READY_FOR_DECISION_PLAN_PREPARATION"
    else:
        stage1_status = "BLOCKED"

    add_rows = [row for row in position_rows if row["action"] == "ADD"]
    buy_rows = [row for row in add_rows if isinstance(row["share_delta"]["value"], int) and row["share_delta"]["value"] > 0]
    buy_advisories: list[dict[str, Any]] = []
    stage2_blockers: list[str] = []
    post_initial_buy_cash = None
    if replay:
        stage2_status = "REPLAY_ONLY"
        stage2_blockers.append("HISTORICAL_PLAN_CANNOT_CREATE_CURRENT_BUY_ADVISORY")
    elif compile_mode != "POST_SELL_RECOMPILE":
        stage2_status = "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED"
        stage2_blockers.append("BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED")
    elif orderable_cash is None:
        stage2_status = "BLOCKED"
        stage2_blockers.append("VERIFIED_ORDERABLE_CASH_REQUIRED")
    elif funding_cash is None:
        stage2_status = "BLOCKED"
        stage2_blockers.append("CONSERVATIVE_CASH_REQUIRED")
    elif core_status != "VERIFIED":
        stage2_status = "BLOCKED"
        stage2_blockers.append("POST_SELL_CANONICAL_EVIDENCE_NOT_VERIFIED")
    elif not current_context_result["verified"]:
        stage2_status = "BLOCKED"
        stage2_blockers.extend(current_context_result["blockers"])
    elif evidence.get("market_phase") not in {"REGULAR_INTRADAY", "REGULAR_COMPLETED"}:
        stage2_status = "BLOCKED"
        stage2_blockers.append("POST_SELL_SESSION_NOT_ELIGIBLE")
    elif plan["plan_status"] != CURRENT_PLAN_STATUS or any(row.get("target_status") != "APPROVED" for row in position_rows):
        stage2_status = "PROVISIONAL"
        stage2_blockers.append("CURRENT_APPROVED_PLAN_REQUIRED")
    elif any(row["blockers"] for row in add_rows):
        stage2_status = "BLOCKED"
        stage2_blockers.append("BUY_INPUT_BLOCKED")
    else:
        requested_cost = Decimal("0")
        capped_gaps: dict[str, int] = {}
        for row in buy_rows:
            gap = int(row["share_delta"]["value"])
            if int(row["current_quantity"]["value"]) == 0:
                full_target = int(row["target_shares_reference"]["value"])
                entry_fraction = _decimal(risk_policy["new_position_initial_entry"]["maximum_fraction_of_full_target"])
                capped_target = int((Decimal(full_target) * entry_fraction).to_integral_value(rounding=ROUND_FLOOR))
                gap = min(gap, capped_target)
            capped_gaps[row["ticker"]] = max(0, gap)
            requested_cost += Decimal(capped_gaps[row["ticker"]]) * prices[row["ticker"]]["price"]
        eligible_gaps = {ticker: gap for ticker, gap in capped_gaps.items() if gap > 0}
        priority = plan.get("buy_priority") or []
        insufficient_cash = requested_cost > funding_cash
        eligible = set(eligible_gaps)
        if insufficient_cash and not priority:
            stage2_status = "BLOCKED"
            stage2_blockers.append("BUY_ALLOCATION_PRIORITY_REQUIRED")
        elif insufficient_cash and (len(priority) != len(eligible) or set(priority) != eligible):
            stage2_status = "BLOCKED"
            stage2_blockers.append("BUY_ALLOCATION_PRIORITY_INCOMPLETE")
        else:
            order = list(priority) if insufficient_cash else [
                item["ticker"] for item in plan["positions"] if item["ticker"] in eligible_gaps
            ]
            cash_left = funding_cash
            simulated_holdings = dict(holdings)
            allocations = {ticker: 0 for ticker in eligible_gaps}
            for ticker in order:
                price = prices[ticker]["price"]
                maximum = min(eligible_gaps[ticker], _floor_shares(cash_left, Decimal("100"), price) or 0)
                for _ in range(maximum):
                    candidate_holdings = dict(simulated_holdings)
                    candidate_holdings[ticker] = candidate_holdings.get(ticker, 0) + 1
                    candidate_values = {
                        name: Decimal(qty) * prices[name]["price"] for name, qty in candidate_holdings.items()
                    }
                    candidate_weights = {
                        name: value / nav * Decimal("100") for name, value in candidate_values.items()
                    } if nav else {}
                    candidate_cash_pct = (cash_left - price) / nav * Decimal("100") if nav else None
                    candidate_risk = calculate_risk_metrics(candidate_weights, candidate_cash_pct, mappings, risk_policy)
                    if candidate_risk["hard_cap_violations"]:
                        break
                    simulated_holdings = candidate_holdings
                    cash_left -= price
                    allocations[ticker] += 1
            for ticker in order:
                buy_advisories.append({
                    "ticker": ticker,
                    "target_gap_shares": eligible_gaps[ticker],
                    "calculated_buy_shares": allocations[ticker],
                    "price_usd": _json_number(prices[ticker]["price"]),
                    "estimated_cost_usd": _json_number(Decimal(allocations[ticker]) * prices[ticker]["price"]),
                    "quantity_status": "CALCULATED_MANUAL_ADVISORY",
                })
            post_initial_buy_cash = cash_left
            stage2_status = "FINAL_MANUAL_ADVISORY_ELIGIBLE"

    if direction_only_evidence:
        stage1_status = stage2_status = "BLOCKED"
        buy_advisories = []
        stage2_blockers.append("DIRECTION_ONLY_EVIDENCE_NO_QUANTITY_AUTHORITY")
    event = _event_context(event_context)
    current_authority_eligible = (
        stage1_status == "FINAL_MANUAL_ADVISORY_ELIGIBLE"
        or stage2_status == "FINAL_MANUAL_ADVISORY_ELIGIBLE"
    )
    derived_runtime_authority = (
        "CURRENT_MANUAL_ADVISORY_ELIGIBLE" if current_authority_eligible else "NOT_VERIFIED_BY_RUNTIME"
    )
    report = {
        "schema_version": "1.0",
        "report_type": "PORTFOLIO_DECISION_DASHBOARD_MANUAL_ADVISORY",
        "run_id": run_id,
        "generated_at": generated,
        "compile_mode": compile_mode,
        **({"trigger_provenance": trigger_provenance} if trigger_provenance is not None else {}),
        "evidence": {
            "portfolio_evidence_status": core_status,
            "evidence_grade": evidence.get("evidence_grade", "NOT_VERIFIED"),
            "portfolio_evidence_grade_display": "GRADE_B_AT_ARTIFACT_TIME" if replay and evidence.get("evidence_grade") == "GRADE_B" else evidence.get("evidence_grade", "NOT_VERIFIED"),
            "run_id": evidence.get("manual_run_id") or evidence.get("run_id"),
            "decision_as_of": evidence.get("decision_as_of"),
            "market_phase": evidence.get("market_phase"),
            "decision_quality_eligible": (evidence.get("provenance") or {}).get("decision_quality_eligible") is True,
            "holding_source": holding_source,
            "broker_system_mismatch": evidence.get("broker_diff_status"),
            "scope_complete": (evidence.get("broker_observed_state") or {}).get("scope_complete") is True,
            "open_items_status": open_items_status or "NOT_AVAILABLE",
            "sell_readiness": {
                ticker: _sell_readiness_evidence(
                    evidence, ticker, holdings.get(ticker),
                    (position.get("order_intent_terms") or {}).get("proposed_quantity"),
                    _parse_timestamp(generated),
                )
                for ticker, position in sorted(positions.items())
                if position.get("action") in {"TRIM", "EXIT"}
            },
            "request_accounting_status": request_accounting_status,
            "request_accounting": dict(sorted(operations.items())) if isinstance(operations, dict) else {},
            "request_accounting_contract": request_accounting_result["details"],
            "request_accounting_issues": request_accounting_result["issues"],
            "canonical_schema_sha256": _sha256_bytes(evidence_schema_bytes),
            "canonical_schema_errors": evidence_schema_errors,
            "failure_code": ("SCHEDULED_SCHEMA_INVALID" if input_mode == "LIVE_READ_ONLY" else "GRADE_B_SCHEMA_INVALID") if evidence_schema_errors else None,
            "canonical_gate_blockers": evidence_gate_blockers,
            "issues": sorted(set(issues)),
            "warnings": sorted(set(warnings)),
            "current_freshness": "HISTORICAL_REPLAY" if replay else (
                "CURRENT_SESSION_CONTEXT_VERIFIED" if current_context_result["verified"] else "CURRENT_SESSION_CONTEXT_NOT_VERIFIED"
            ),
        },
        "current_context": {
            "status": current_context_result["status"],
            "verified": current_context_result["verified"],
            "blockers": current_context_result["blockers"],
            "schema_errors": current_context_result["schema_errors"],
            "expected_completed_us_session": (
                current_session_context.get("expected_completed_us_session")
                if isinstance(current_session_context, dict) else None
            ),
            "market_phase": current_session_context.get("market_phase") if isinstance(current_session_context, dict) else None,
        },
        "plan": {
            "plan_id": plan["plan_id"], "as_of": plan["as_of"], "plan_status": plan["plan_status"],
            "target_type": plan["target_type"], "cash_target_pct": plan.get("cash_target_pct"),
            "evidence_binding": plan["evidence_binding"],
            "post_sell_refresh": plan.get("post_sell_refresh"),
            "material_unknowns": [_safe_swing_text(item) for item in plan.get("material_unknowns") or []],
            "decision_change_triggers": [_safe_swing_text(item) for item in plan.get("decision_change_triggers") or []],
            "temporal_status": "HISTORICAL_REPLAY" if replay else "CURRENT_OR_PROVISIONAL",
        },
        "portfolio": {
            "nav_usd": _value(nav, "DERIVED" if nav is not None else "PROVISIONAL", "USD"),
            "positions": position_rows,
            "current_risk": current_risk,
            "target_reference_risk": target_risk,
            "risk_mapping_status": "CONFLICT" if any("RISK_MAPPING_CONFLICT" in issue for issue in issues) else (
                "BLOCKED" if any("RISK_MAPPING_" in issue for issue in issues) else "VERIFIED_OR_CONFIRMED_FALLBACK"
            ),
        },
        "stage1": {
            "status": stage1_status,
            "sell_advisories": stage1_rows,
            "expected_sale_proceeds_usd": _value(expected_proceeds, "ESTIMATED" if expected_proceeds is not None else "PROVISIONAL", "USD"),
            "post_sell_estimated_cash_usd": _value(post_sell_estimated_cash, "ESTIMATED" if post_sell_estimated_cash is not None else "PROVISIONAL", "USD"),
            "order_created": False,
        },
        "stage2": {
            "status": stage2_status,
            "verified_orderable_cash_usd": _value(orderable_cash, "VERIFIED" if orderable_cash is not None else "NOT_VERIFIED", "USD"),
            "buy_candidates": [row["ticker"] for row in buy_rows],
            "buy_candidate_references": [
                {"ticker": row["ticker"], "target_shares_reference": row["target_shares_reference"]["value"]}
                for row in add_rows
            ],
            "buy_advisories": buy_advisories,
            "blockers": sorted(set(stage2_blockers)),
            "order_created": False,
        },
        "cash_semantics": {
            "current_cash_usd": _value(current_cash, "VERIFIED" if current_cash is not None else "NOT_VERIFIED", "USD"),
            "verified_orderable_cash_usd": _value(orderable_cash, "VERIFIED" if orderable_cash is not None else "NOT_VERIFIED", "USD"),
            "post_sell_estimated_cash_usd": _value(post_sell_estimated_cash, "ESTIMATED" if post_sell_estimated_cash is not None else "PROVISIONAL", "USD"),
            "post_initial_buy_estimated_cash_usd": _value(post_initial_buy_cash, "ESTIMATED" if post_initial_buy_cash is not None else "PROVISIONAL", "USD"),
            "full_target_reference_cash_pct": _value(_decimal(plan["cash_target_pct"]) if plan.get("cash_target_pct") is not None else None,
                                                        "VERIFIED" if plan.get("cash_target_pct") is not None else "NOT_VERIFIED", "PCT"),
            "full_target_reference_cash_usd": _value(
                nav * (_decimal(plan["cash_target_pct"]) or Decimal("0")) / Decimal("100")
                if nav is not None and plan.get("cash_target_pct") is not None else None,
                "DERIVED" if nav is not None and plan.get("cash_target_pct") is not None else "PROVISIONAL", "USD",
            ),
            "expected_proceeds_treated_as_orderable_cash": False,
        },
        "event_context": event,
        "authority": {
            "artifact_time_quantity_authority": evidence.get("quantity_authority", "none"),
            "current_runtime_advisory_authority": derived_runtime_authority,
            "runtime_authority_cli_input": runtime_advisory_authority,
            "runtime_authority_cli_input_effect": "DISPLAY_ONLY_NO_AUTHORITY_EFFECT" if runtime_advisory_authority else "NOT_PROVIDED",
            "ready_for_decision_plan_preparation": bool(
                stage1_status in {"READY_FOR_DECISION_PLAN_PREPARATION", "FINAL_MANUAL_ADVISORY_ELIGIBLE"}
            ),
            "manual_advisory_label": "CALCULATED_MANUAL_ADVISORY",
            "broker_order_authority": False,
            "execution_quantity": None,
            "automatic_order": False,
        },
        "safety": {
            "network_access": False, "kiwoom_call": False, "broker_call": False,
            "sec_live_request": False, "save_access": False, "task_scheduler_mutation": False,
            "portfolio_mutation": False, "policy_mutation": False, "orders": "NONE",
        },
    }
    if _manual_capture_only_direction_gate(
            report, evidence, holding_timing_inputs, parent_capture_artifacts):
        report["evidence"]["manual_capture_only_direction"] = True
    bound_timing = _holding_timing_projection(
        report, evidence, holding_timing_inputs,
        parent_capture_artifacts=parent_capture_artifacts,
        authority_resolver=current_session_authority_resolver,
    )
    for row in report["portfolio"]["positions"]:
        if row["ticker"] in bound_timing:
            row["holding_timing_evidence"] = bound_timing[row["ticker"]]
    local_prices = {
        ticker: holding_timing_inputs["snapshot"]["symbols"][ticker]["close"]
        for ticker, timing in bound_timing.items()
        if isinstance(holding_timing_inputs, dict)
    }
    if local_prices:
        report["evidence"]["manual_holding_timing_local_prices"] = local_prices
        report["evidence"].update(
            provider_finalization_verified="NOT_VERIFIED",
            local_regular_bar_coherence="PASS",
            technical_analysis_eligibility="YES",
        )
    report["swing_action_plan"] = _build_swing_action_contract(
        report, evidence, plan, risk_policy, evidence_sha256,
    )
    schema_errors = validate_instance(report, DASHBOARD_SCHEMA, schema_bytes=dashboard_schema_bytes)
    swing_errors = validate_swing_action_contract(
        report, schema_bytes=dashboard_schema_bytes, evidence=evidence, plan=plan,
        risk_policy=risk_policy, evidence_sha256=evidence_sha256,
        holding_timing_inputs=holding_timing_inputs,
        parent_capture_artifacts=parent_capture_artifacts,
        current_session_authority_resolver=current_session_authority_resolver,
    )
    stage2_gate_verified = bool(
        compile_mode == "POST_SELL_RECOMPILE"
        and core_status == "VERIFIED"
        and evidence.get("market_phase") in {"REGULAR_INTRADAY", "REGULAR_COMPLETED"}
        and orderable_cash is not None
        and funding_cash is not None
        and plan["plan_status"] == CURRENT_PLAN_STATUS
        and not evidence_gate_blockers
        and current_context_result["verified"]
    )
    invariants = {
        "dashboard_schema": not schema_errors,
        "swing_action_contract": not swing_errors,
        "order_authority_false": report["authority"]["broker_order_authority"] is False,
        "execution_quantity_null": report["authority"]["execution_quantity"] is None,
        "automatic_order_false": report["authority"]["automatic_order"] is False,
        "expected_proceeds_not_orderable": report["cash_semantics"]["expected_proceeds_treated_as_orderable_cash"] is False,
        "canonical_evidence_schema": not evidence_schema_errors,
        "canonical_evidence_gate_enforced": not current_authority_eligible or not evidence_gate_blockers,
        "current_session_context_gate_enforced": not current_authority_eligible or current_context_result["verified"],
        "stage2_firewall": stage2_status != "FINAL_MANUAL_ADVISORY_ELIGIBLE" or stage2_gate_verified,
        "request_accounting_has_no_authority_effect": report["authority"]["broker_order_authority"] is False,
        "portfolio_mutation_false": report["safety"]["portfolio_mutation"] is False,
        "policy_mutation_false": report["safety"]["policy_mutation"] is False,
        "network_false": report["safety"]["network_access"] is False,
    }
    validation_status = "FAIL" if schema_errors or evidence_schema_errors or not all(invariants.values()) else (
        "BLOCKED" if core_status == "BLOCKED" else "PASS"
    )
    validation = {
        "schema_version": "1.0", "run_id": run_id, "generated_at": generated,
        "status": validation_status, "schema_errors": schema_errors,
        "invariants": invariants, "input_issues": sorted(set(issues)),
        "swing_action_contract_errors": swing_errors,
        "network_used": False, "broker_used": False, "order_path_used": False,
    }
    return report, validation


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "확인 필요"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _render_markdown_legacy(report: dict[str, Any]) -> str:
    stage1 = report["stage1"]
    stage2 = report["stage2"]
    conclusion = "위험 축소 우선" if any((row.get("calculated_sell_shares") or 0) > 0 for row in stage1["sell_advisories"]) else (
        "매수 검토" if stage2["buy_advisories"] else "현금 유지 / 보유 검토"
    )
    lines = [
        "# 포트폴리오 조정안", "",
        f"- 기준 시각: {report['evidence'].get('decision_as_of') or '확인 필요'}",
        f"- Evidence Grade: {report['evidence']['portfolio_evidence_grade_display']}",
        f"- 시장 상태: {report['evidence'].get('market_phase') or '확인 필요'}",
        f"- 오늘의 결론: **{conclusion}**", "",
        "> 이 문서는 계산된 수동 검토 자료입니다. 매수·매도 주문을 만들거나 전송하지 않습니다.", "",
        "## 지금 할 일 — 1단계", "",
        f"상태: {stage1['status']}", "",
        "| 종목 | 현재 주수 | 목표 참고 주수 | 수동 매도 참고 | 현재 비중 | 목표 비중 | 이유 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    if stage1["sell_advisories"]:
        for row in stage1["sell_advisories"]:
            lines.append(
                f"| {row['ticker']} | {_fmt(row['current_shares'])} | {_fmt(row['target_shares_reference'])} | "
                f"{_fmt(row['calculated_sell_shares'])} | {_fmt(row['current_weight_pct'])}% | "
                f"{_fmt(row['target_weight_pct'])}% | {row['reason']} |"
            )
    else:
        lines.append("| 해당 없음 | - | - | - | - | - | 현재 계획에 축소·정리 항목 없음 |")
    lines += ["", "## 2단계 매수", "", f"상태: {stage2['status']}", ""]
    if stage2["status"] == "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED":
        lines.append("매도 체결 후 Kiwoom 계좌를 다시 확인해야 매수 수량을 계산할 수 있습니다.")
    if stage2["buy_advisories"]:
        lines += ["", "| 종목 | 계산된 수동 매수 참고 | 예상 소요액 |", "|---|---:|---:|"]
        for row in stage2["buy_advisories"]:
            lines.append(f"| {row['ticker']} | {_fmt(row['calculated_buy_shares'])}주 | ${_fmt(row['estimated_cost_usd'])} |")
    else:
        candidates = ", ".join(stage2["buy_candidates"]) or "없음"
        lines += [f"매수 후보: {candidates}", "", "현재 최종 매수 수량: 계산 금지 / BLOCKED"]
    lines += ["", "## 종목별 판단 카드", ""]
    action_ko = {"ADD": "늘림", "HOLD": "유지", "TRIM": "축소", "EXIT": "정리 검토"}
    for row in report["portfolio"]["positions"]:
        lines += [
            f"### {row['ticker']}", "",
            f"- 판단: {action_ko[row['action']]}",
            f"- 현재 비중 / 목표 비중: {_fmt(row['current_weight_pct']['value'])}% / {_fmt(row['target_weight_pct']['value'])}%",
            f"- 현재 주수 / 목표 참고 주수: {_fmt(row['current_quantity']['value'])}주 / {_fmt(row['target_shares_reference']['value'])}주",
            f"- 조정 참고: {_fmt(row['share_delta']['value'])}주",
            f"- 핵심 이유: {row['rationale']}",
            f"- 가장 큰 위험: {row.get('material_risk') or '계획에 명시되지 않음'}",
            f"- 판단이 바뀌는 조건: {', '.join(row['decision_change_triggers']) or '계획에 명시되지 않음'}", "",
        ]
    risk = report["portfolio"].get("current_risk") or {}
    lines += ["## 포트폴리오 건강", "", "| 항목 | 현재 | 상태 |", "|---|---:|---|"]
    labels = {
        "CASH_PCT": "현금", "LEVERAGED_PRODUCTS_PCT": "레버리지 상품",
        "GROWTH_AI_SEMI_BOOK_PCT": "Growth/AI/Semi 장부",
        "GROWTH_AI_SEMI_LEVERAGE_ADJUSTED_PCT": "Growth/AI/Semi 레버리지 조정",
        "OVERALL_LEVERAGE_ADJUSTED_PROXY_PCT": "전체 레버리지 조정 proxy",
    }
    for check in risk.get("checks", []):
        if check["metric"].startswith("POSITION_PCT:"):
            continue
        lines.append(f"| {labels.get(check['metric'], check['metric'])} | {_fmt(check['value'])}% | {check['status']} |")
    if "OPEN_ITEMS_VISIBILITY_UNAVAILABLE" in report["evidence"]["warnings"]:
        lines += ["", "> 실제 주문 전 Kiwoom에서 미체결 주문이 없는지 확인이 필요합니다."]
    lines += [
        "", "## 권한과 현금 구분", "",
        f"- 현재 현금: ${_fmt(report['cash_semantics']['current_cash_usd']['value'])}",
        f"- 검증된 주문가능 현금: ${_fmt(report['cash_semantics']['verified_orderable_cash_usd']['value'])}",
        f"- 매도 후 추정 현금: ${_fmt(report['cash_semantics']['post_sell_estimated_cash_usd']['value'])}",
        f"- 전체 목표 참고 현금: ${_fmt(report['cash_semantics']['full_target_reference_cash_usd']['value'])}",
        f"- 현재 수동 검토 권한: {report['authority']['current_runtime_advisory_authority']}",
        "- Broker Order Authority: FALSE",
        "- execution_quantity: NULL",
        "- automatic_order: FALSE", "",
    ]
    return "\n".join(lines) + "\n"


def _render_html_legacy(report: dict[str, Any]) -> str:
    markdown = _render_markdown_legacy(report)
    first = report["stage1"]["sell_advisories"]
    stage1_rows = "".join(
        f"<tr><td>{html.escape(row['ticker'])}</td><td>{_fmt(row['current_shares'])}</td>"
        f"<td>{_fmt(row['target_shares_reference'])}</td><td>{_fmt(row['calculated_sell_shares'])}</td>"
        f"<td>{html.escape(row['reason'])}</td></tr>" for row in first
    ) or "<tr><td colspan='5'>현재 계획에 축소·정리 항목이 없습니다.</td></tr>"
    cards = "".join(
        f"<article><h3>{html.escape(row['ticker'])}</h3><p><strong>{html.escape(row['action'])}</strong></p>"
        f"<p>현재 {_fmt(row['current_quantity']['value'])}주 · 목표 참고 {_fmt(row['target_shares_reference']['value'])}주</p>"
        f"<p>{html.escape(row['rationale'])}</p></article>" for row in report["portfolio"]["positions"]
    )
    blocked = report["stage2"]["status"] == "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED"
    buy_text = "매도 체결 후 Kiwoom 계좌를 다시 확인해야 매수 수량을 계산할 수 있습니다." if blocked else report["stage2"]["status"]
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>포트폴리오 조정안</title><style>
body{{font-family:"Malgun Gothic","맑은 고딕","Segoe UI",Arial,sans-serif;margin:0;background:#f4f7fb;color:#172033}}
main{{max-width:1120px;margin:auto;padding:28px}}.hero{{background:#173b66;color:white;padding:26px;border-radius:18px}}
.notice{{background:#fff4d6;border-left:5px solid #d39500;padding:14px;margin:18px 0}}section{{background:white;padding:20px;margin:18px 0;border-radius:14px;box-shadow:0 5px 20px #16324f14}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #dce3ec;padding:10px;text-align:left}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}article{{border:1px solid #dce3ec;border-radius:12px;padding:14px}}
.status{{font-size:1.1rem;font-weight:700;color:#8a4200}}small{{color:#526173}}pre{{white-space:pre-wrap;background:#f7f8fa;padding:12px;border-radius:8px}}
</style></head><body><main>
<header class="hero"><h1>포트폴리오 조정안</h1><p>기준 시각: {html.escape(str(report['evidence'].get('decision_as_of') or '확인 필요'))}</p><p>Evidence Grade: {html.escape(report['evidence']['portfolio_evidence_grade_display'])} · 시장 상태: {html.escape(str(report['evidence'].get('market_phase') or '확인 필요'))}</p></header>
<div class="notice">계산된 수동 검토 자료이며, 매수·매도 주문을 만들거나 전송하지 않습니다.</div>
<section><h2>지금 할 일 — 1단계</h2><p class="status">{html.escape(report['stage1']['status'])}</p><table><thead><tr><th>종목</th><th>현재 주수</th><th>목표 참고</th><th>수동 매도 참고</th><th>이유</th></tr></thead><tbody>{stage1_rows}</tbody></table></section>
<section><h2>2단계 매수</h2><p class="status">{html.escape(report['stage2']['status'])}</p><p>{html.escape(buy_text)}</p><p>매수 후보: {html.escape(', '.join(report['stage2']['buy_candidates']) or '없음')}</p></section>
<section><h2>종목별 판단</h2><div class="cards">{cards}</div></section>
<section><h2>권한</h2><p>Broker Order Authority = FALSE · execution_quantity = NULL · automatic_order = FALSE</p><small>현재 수동 검토 권한: {html.escape(report['authority']['current_runtime_advisory_authority'])}</small></section>
<details><summary>동일 의미의 Markdown 원문</summary><pre>{html.escape(markdown)}</pre></details>
</main></body></html>"""


def _display(value: Any, digits: int = 2) -> str:
    if value is None:
        return "확인 필요"
    if isinstance(value, bool):
        return str(value).upper()
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _current_context_explanation(status: str) -> str:
    return {
        "VERIFIED": "현재 세션 확인 자료가 Grade B 원본 실행·해시·판단 시각·세션과 정확히 일치합니다.",
        "ABSENT": "현재 세션 확인 자료가 없어 계산은 계획 준비용이며 최종 수동 검토는 차단됩니다.",
        "PRESENT_INVALID": "현재 세션 확인 자료의 형식이 유효하지 않아 최종 수동 검토는 차단됩니다.",
        "PRESENT_MISMATCH": "현재 세션 확인 자료가 Grade B 원본 또는 정규 세션과 일치하지 않아 최종 수동 검토는 차단됩니다.",
    }.get(status, "현재 세션 확인 상태를 판정할 수 없습니다.")


def _request_accounting_explanation(status: str) -> str:
    return {
        "VERIFIED": "요청 횟수가 같은 Grade B 실행과 원본 해시에 정확히 결속되어 검증되었습니다.",
        "ABSENT": "검증 가능한 요청 회계 자료가 없습니다.",
        "PRESENT_INVALID": "요청 회계의 형식 또는 합계가 유효하지 않습니다.",
        "PRESENT_UNVERIFIED": "요청 흔적은 있으나 같은 Grade B 원본 실행과 정확히 결속되지 않았습니다.",
    }.get(status, "요청 회계 상태를 판정할 수 없습니다.")


def _dashboard_display_semantics(report: dict[str, Any]) -> dict[str, str]:
    """Return beginner-facing labels without changing canonical report semantics."""
    freshness = str(report["evidence"].get("current_freshness") or "NOT_AVAILABLE")
    context_status = str(report["current_context"].get("status") or "NOT_AVAILABLE")
    accounting_status = str(report["evidence"].get("request_accounting_status") or "NOT_AVAILABLE")
    current_data_labels = {
        "CURRENT_SESSION_CONTEXT_VERIFIED": "현재 자료",
        "CURRENT_SESSION_CONTEXT_NOT_VERIFIED": "현재 자료 여부 확인 불가",
        "HISTORICAL_REPLAY": "과거 자료 / 현재 판단 사용 불가",
    }
    session_labels = {
        "VERIFIED": "확인됨",
        "ABSENT": "확인되지 않음",
        "PRESENT_MISMATCH": "확인되지 않음",
        "PRESENT_INVALID": "확인되지 않음",
    }
    accounting_labels = {
        "VERIFIED": "검증됨",
        "PRESENT_UNVERIFIED": "미검증",
        "ABSENT": "없음",
        "PRESENT_INVALID": "형식 오류",
    }
    return {
        "current_data_status": f"{current_data_labels.get(freshness, '확인 필요')} ({freshness})",
        "current_session_verification": f"{session_labels.get(context_status, '확인 필요')} ({context_status})",
        "request_accounting": f"{accounting_labels.get(accounting_status, '확인 필요')} ({accounting_status})",
    }


def _render_swing_action_plan(report: dict[str, Any], *, as_html: bool = False) -> str:
    _require_valid_swing_view(report)
    view = report.get("swing_action_plan")
    if view is None:
        return ""
    summary = [
        "지금 할 일 = 보유·현금 정책과 Manual 근거 준비 상태 확인",
        "현재 판단 = 기존 방향 후보 검토; 새 Shadow 수량은 산출 보류",
        "보류 이유 = 정책 승인 결속·Manual 준비·기술 신호 미확인",
        "개발·운영 상태 = 출력 계약 구현; 수량 기능과 실행은 비활성",
        "다음 확인 = 해당 종목의 정책 공백과 근거 시점",
    ]
    labels = {"HOLD": "유지", "TRIM": "축소", "EXIT": "청산", "BUY": "신규매수", "ADD": "추가", "DEFERRED": "보류"}
    headers = ["종목", "근거 시점 보유", "원래 후보", "현재 검토", "시점", "Shadow 수량", "수량 상태", "실행", "근거", "무효화·재평가"]
    def concise(value: str) -> str:
        return value if len(value) <= 120 else value[:117] + "..."
    rows = [[
        row["ticker"], _display(row["current_qty"]), labels[row["candidate_direction"]],
        labels[row["direction"]], row["timing_status"], "미산출", row["quantity_status"], row["execution_status"],
        concise(row["reason"]), concise("; ".join(row["invalidation"]) or "확인 필요"),
    ] for row in view["rows"]]
    cash = view["cash"]
    notes = [
        f"판단 기준시각: {view['source_binding']['decision_as_of'] or '확인 필요'} · 자료 상태: {view['source_binding']['freshness']}",
        "Cash는 독립 검토 대안이며, 현금 유지가 확정된 것은 아닙니다.",
        f"NAV용 현금: {_display(cash['nav_cash_usd']['value'])} USD · 주문가능현금: {_display(cash['orderable_cash_usd']['value'])} USD",
        "현금 시점 정합성: NOT_VERIFIED · 예상 매도대금은 주문가능현금이 아닙니다.",
        "아래 기존 수동 참고 계산은 새 Swing 수량 승인이나 주문 지시가 아닙니다.",
        "출처 해시는 입력 없는 표시 검증에서 형식만 확인합니다. 원본 진위·승인은 NOT_VERIFIED입니다.",
    ]
    details = [
        f"{row['ticker']}: {row['reason']} | 무효화·재평가: {', '.join(row['invalidation']) or '확인 필요'} | 미확인: {', '.join(row['blockers'])}"
        for row in view["rows"]
    ]
    if as_html:
        table = "<thead><tr>" + "".join(f"<th>{html.escape(x)}</th>" for x in headers) + "</tr></thead><tbody>"
        table += "".join("<tr>" + "".join(f"<td>{html.escape(x)}</td>" for x in row) + "</tr>" for row in rows) + "</tbody>"
        return ("<section><h2>[한눈에 보기]</h2>" + "".join(f"<p>{html.escape(x)}</p>" for x in summary)
                + "<h2>Swing Action Plan — 계약 준비</h2><table>" + table + "</table>"
                + "".join(f"<p>{html.escape(x)}</p>" for x in notes)
                + "<details><summary>근거와 미확인</summary>" + "".join(f"<p>{html.escape(x)}</p>" for x in details)
                + "</details></section>")
    def cell(value: str) -> str:
        return html.escape(value).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")
    lines = ["[한눈에 보기]", ""] + summary + ["", "## Swing Action Plan — 계약 준비", ""]
    lines += ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines += ["| " + " | ".join(cell(x) for x in row) + " |" for row in rows]
    lines += [""] + ["- " + cell(x) for x in notes] + [""] + ["- " + cell(x) for x in details]
    return "\n".join(lines) + "\n\n"


def render_markdown(report: dict[str, Any]) -> str:
    report = _safe_swing_report(report)
    evidence = report["evidence"]
    current_context = report["current_context"]
    display = _dashboard_display_semantics(report)
    stage1 = report["stage1"]
    stage2 = report["stage2"]
    event = report["event_context"]
    lines = [_render_swing_action_plan(report)] if report.get("swing_action_plan") is not None else []
    lines += [
        "# 포트폴리오 의사결정 대시보드", "",
        f"- 생성 시각: {report['generated_at']} — 생성 당시 결과의 표시이며 현재 재수용 검증이 아닙니다.",
        f"- 판단 시각: {evidence.get('decision_as_of') or '확인 필요'}",
        f"- Evidence Run: {evidence.get('run_id') or '확인 필요'}",
        f"- Evidence Grade: {evidence['portfolio_evidence_grade_display']}",
        f"- 현재 자료 상태: {display['current_data_status']}",
        f"- 현재 세션 확인 결과: {display['current_session_verification']}",
        f"- 요청 회계 상태: {display['request_accounting']}",
        f"- 시장 단계: {evidence.get('market_phase') or '확인 필요'}", "",
        "> 수동 검토용 계산 자료이며, 매수·매도 주문을 만들거나 전송하지 않습니다.", "",
        "## 위험 축소 1단계", "", f"상태: {stage1['status']}", "",
        "| 종목 | 현재 주식 | 목표 참고 주식 | 계산 매도 주식 | 현재 비중 | 목표 비중 | 근거 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    if stage1["sell_advisories"]:
        for row in stage1["sell_advisories"]:
            lines.append(
                f"| {row['ticker']} | {_display(row['current_shares'])} | {_display(row['target_shares_reference'])} | "
                f"{_display(row['calculated_sell_shares'])} | {_display(row['current_weight_pct'])}% | "
                f"{_display(row['target_weight_pct'])}% | {row['reason']} |"
            )
    else:
        lines.append("| 해당 없음 | - | - | - | - | - | 계획상 축소·청산 항목 없음 |")

    lines += ["", "## 2단계 매수", "", f"상태: {stage2['status']}", ""]
    if stage2["status"] == "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED":
        lines.append("매도 체결 후 새 broker-observed Grade B run으로 다시 계산해야 합니다.")
    if stage2["buy_advisories"]:
        lines += [
            "| 종목 | 목표 참고 주식 | 목표 격차 | 계산 매수 주식 | 기준 가격 | 예상 소요액 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        references = {item["ticker"]: item["target_shares_reference"] for item in stage2["buy_candidate_references"]}
        for row in stage2["buy_advisories"]:
            lines.append(
                f"| {row['ticker']} | {_display(references.get(row['ticker']))}주 | {_display(row['target_gap_shares'])}주 | "
                f"{_display(row['calculated_buy_shares'])}주 | ${_display(row['price_usd'])} | "
                f"${_display(row['estimated_cost_usd'])} |"
            )
    else:
        lines += ["| 종목 | 목표 참고 주식 | 최종 매수 주식 |", "|---|---:|---|"]
        if stage2["buy_candidate_references"]:
            for row in stage2["buy_candidate_references"]:
                lines.append(f"| {row['ticker']} | {_display(row['target_shares_reference'])}주 | 산출 보류 / BLOCKED |")
        else:
            lines.append("| 없음 | - | 산출 보류 / BLOCKED |")
    if stage2["blockers"]:
        lines.append(f"차단 사유: {', '.join(stage2['blockers'])}")

    lines += ["", "## 종목 판단", ""]
    actions = {"ADD": "늘림", "HOLD": "유지", "TRIM": "축소", "EXIT": "전량 정리"}
    for row in report["portfolio"]["positions"]:
        lines += [
            f"### {row['ticker']}", "",
            f"- 판단: {actions[row['action']]}",
            f"- 현재/목표 비중: {_display(row['current_weight_pct']['value'])}% / {_display(row['target_weight_pct']['value'])}%",
            f"- 현재/목표 참고 주식: {_display(row['current_quantity']['value'])}주 / {_display(row['target_shares_reference']['value'])}주",
            f"- 계산 변화: {_display(row['share_delta']['value'])}주",
            f"- 근거: {row['rationale']}",
            f"- 주요 위험: {row.get('material_risk') or '계획에 기재되지 않음'}",
            f"- 판단 변경 조건: {', '.join(row['decision_change_triggers']) or '계획에 기재되지 않음'}", "",
        ]

    lines += [
        "## 근거·요청·이벤트", "",
        f"- Canonical schema SHA-256: {evidence['canonical_schema_sha256']}",
        f"- 현재 세션 확인 결과: {display['current_session_verification']}",
        f"- 현재 세션 설명: {_current_context_explanation(current_context['status'])}",
        f"- 현재성 차단 사유: {', '.join(current_context['blockers']) or '없음'}",
        f"- 요청 회계 상태: {display['request_accounting']}",
        f"- 요청 회계 설명: {_request_accounting_explanation(evidence['request_accounting_status'])}",
    ]
    for name, status in evidence.get("request_accounting", {}).items():
        lines.append(f"  - {name}: {status}")
    lines += [
        f"- Event context: {event['status']}",
        f"- HIGH events (current/new): {_display(event['current_high_count'])}/{_display(event['new_high_count'])}",
        f"- Affected tickers: {', '.join(event['affected_tickers']) or '없음'}",
        f"- Automatic target change: {_display(event['automatic_target_change'])}", "",
        "## 권한과 현금 의미", "",
        f"- 현재 현금: ${_display(report['cash_semantics']['current_cash_usd']['value'])}",
        f"- 검증된 주문 가능 현금: ${_display(report['cash_semantics']['verified_orderable_cash_usd']['value'])}",
        f"- 매도 후 추정 현금: ${_display(report['cash_semantics']['post_sell_estimated_cash_usd']['value'])}",
        f"- 현재 런타임 수동자문 권한: {report['authority']['current_runtime_advisory_authority']}",
        f"- CLI authority input effect: {report['authority']['runtime_authority_cli_input_effect']}",
        "- Broker Order Authority: FALSE", "- execution_quantity: NULL", "- automatic_order: FALSE", "",
    ]
    return "\n".join(lines) + "\n"


def render_html(report: dict[str, Any]) -> str:
    report = _safe_swing_report(report)
    evidence = report["evidence"]
    current_context = report["current_context"]
    display = _dashboard_display_semantics(report)
    stage1_rows = "".join(
        f"<tr><td>{html.escape(row['ticker'])}</td><td>{_display(row['current_shares'])}</td>"
        f"<td>{_display(row['target_shares_reference'])}</td><td>{_display(row['calculated_sell_shares'])}</td>"
        f"<td>{html.escape(row['reason'])}</td></tr>" for row in report["stage1"]["sell_advisories"]
    ) or "<tr><td colspan='5'>계획상 축소·청산 항목이 없습니다.</td></tr>"
    references = {
        item["ticker"]: item["target_shares_reference"]
        for item in report["stage2"]["buy_candidate_references"]
    }
    buy_rows = "".join(
        f"<tr><td>{html.escape(row['ticker'])}</td><td>{_display(references.get(row['ticker']))}</td>"
        f"<td>{_display(row['target_gap_shares'])}</td><td>{_display(row['calculated_buy_shares'])}</td>"
        f"<td>${_display(row['price_usd'])}</td><td>${_display(row['estimated_cost_usd'])}</td></tr>"
        for row in report["stage2"]["buy_advisories"]
    )
    if not buy_rows:
        buy_rows = "".join(
            f"<tr><td>{html.escape(row['ticker'])}</td><td>{_display(row['target_shares_reference'])}</td>"
            "<td>-</td><td>산출 보류 / BLOCKED</td><td>-</td><td>-</td></tr>"
            for row in report["stage2"]["buy_candidate_references"]
        ) or "<tr><td colspan='6'>후보 없음 · 산출 보류 / BLOCKED</td></tr>"
    request_rows = "".join(
        f"<li>{html.escape(name)}: {html.escape(str(status))}</li>"
        for name, status in evidence.get("request_accounting", {}).items()
    )
    event = report["event_context"]
    markdown = render_markdown(report)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>포트폴리오 의사결정 대시보드</title><style>
body{{font-family:"Malgun Gothic","Segoe UI",sans-serif;margin:0;background:#f4f7fb;color:#172033}}main{{max-width:1120px;margin:auto;padding:28px}}
.hero{{background:#173b66;color:white;padding:26px;border-radius:18px}}.notice{{background:#fff4d6;border-left:5px solid #d39500;padding:14px;margin:18px 0}}
section{{background:white;padding:20px;margin:18px 0;border-radius:14px;box-shadow:0 5px 20px #16324f14}}table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #dce3ec;padding:10px;text-align:left}}.status{{font-weight:700;color:#8a4200}}pre{{white-space:pre-wrap;background:#f7f8fa;padding:12px}}
</style></head><body><main>
{_render_swing_action_plan(report, as_html=True)}
<header class="hero"><h1>포트폴리오 의사결정 대시보드</h1><p>판단 시각: {html.escape(str(evidence.get('decision_as_of') or '확인 필요'))}</p><p>Evidence Run: {html.escape(str(evidence.get('run_id') or '확인 필요'))} · Grade: {html.escape(evidence['portfolio_evidence_grade_display'])}</p><p>현재 자료 상태: {html.escape(display['current_data_status'])}</p><p>현재 세션 확인 결과: {html.escape(display['current_session_verification'])}</p><p>요청 회계 상태: {html.escape(display['request_accounting'])}</p><p>시장 단계: {html.escape(str(evidence.get('market_phase') or '확인 필요'))}</p></header>
<div class="notice">생성 시각: {html.escape(str(report['generated_at']))} — 생성 당시 결과의 표시이며 현재 재수용 검증이 아닙니다.<br>수동 검토용 계산 자료이며, 매수·매도 주문을 만들거나 전송하지 않습니다.</div>
<section><h2>위험 축소 1단계</h2><p class="status">{html.escape(report['stage1']['status'])}</p><table><thead><tr><th>종목</th><th>현재 주식</th><th>목표 참고</th><th>계산 매도</th><th>근거</th></tr></thead><tbody>{stage1_rows}</tbody></table></section>
<section><h2>2단계 매수</h2><p class="status">{html.escape(report['stage2']['status'])}</p><table><thead><tr><th>종목</th><th>목표 참고</th><th>목표 격차</th><th>계산 매수</th><th>기준 가격</th><th>예상 소요액</th></tr></thead><tbody>{buy_rows}</tbody></table><p>차단 사유: {html.escape(', '.join(report['stage2']['blockers']) or '없음')}</p></section>
<section><h2>근거·요청·이벤트</h2><p>Canonical schema SHA-256: {html.escape(evidence['canonical_schema_sha256'])}</p><p>현재 세션 확인 결과: {html.escape(display['current_session_verification'])}</p><p>현재 세션 설명: {html.escape(_current_context_explanation(current_context['status']))}</p><p>현재성 차단 사유: {html.escape(', '.join(current_context['blockers']) or '없음')}</p><p>요청 회계 상태: {html.escape(display['request_accounting'])}</p><p>요청 회계 설명: {html.escape(_request_accounting_explanation(evidence['request_accounting_status']))}</p><ul>{request_rows}</ul><p>Event context: {html.escape(event['status'])} · HIGH current/new: {_display(event['current_high_count'])}/{_display(event['new_high_count'])} · affected: {html.escape(', '.join(event['affected_tickers']) or '없음')} · automatic target change: {_display(event['automatic_target_change'])}</p></section>
<section><h2>권한</h2><p>Broker Order Authority = FALSE · execution_quantity = NULL · automatic_order = FALSE</p><p>현재 런타임 수동자문 권한: {html.escape(report['authority']['current_runtime_advisory_authority'])}</p><small>CLI authority input effect: {html.escape(report['authority']['runtime_authority_cli_input_effect'])}</small></section>
<details><summary>동일 의미의 Markdown 원문</summary><pre>{html.escape(markdown)}</pre></details>
</main></body></html>"""


def _trusted_output(root: Path, output_root: Path) -> Path:
    trusted = Path(os.path.abspath(root))
    output = Path(os.path.abspath(output_root))
    try:
        if os.path.commonpath((os.path.normcase(str(trusted)), os.path.normcase(str(output)))) != os.path.normcase(str(trusted)):
            raise ContractError("OUTPUT_OUTSIDE_REPOSITORY")
    except ValueError as exc:
        raise ContractError("OUTPUT_OUTSIDE_REPOSITORY") from exc
    return output


def write_run(
    report: dict[str, Any], validation: dict[str, Any], *, output_root: Path,
    source_paths: dict[str, Path | None], implementation_paths: list[Path], root: Path = ROOT,
    consumed_hashes: dict[str, str] | None = None,
    order_intent_artifact: dict[str, Any] | None = None,
) -> Path:
    report = _safe_swing_report(report)
    output = _trusted_output(root, output_root)
    run_dir = output / report["run_id"]
    run_dir.mkdir(parents=True, exist_ok=False)
    decision_bytes = _json_bytes(report)
    validation_bytes = _json_bytes(validation)
    md_bytes = render_markdown(report).encode("utf-8")
    html_bytes = render_html(report).encode("utf-8")
    artifacts = {
        "portfolio-decision.json": decision_bytes,
        "validation-report.json": validation_bytes,
        "portfolio-decision-dashboard.md": md_bytes,
        "portfolio-decision-dashboard.html": html_bytes,
    }
    if order_intent_artifact is not None:
        artifacts["portfolio-decision-order-intent.json"] = _json_bytes(order_intent_artifact)
    manifest = {
        "schema_version": "1.0", "run_id": report["run_id"], "generated_at": report["generated_at"],
        "git_commit": _git_commit(root),
        "source_artifacts": {
            name: ({"path": path.relative_to(root).as_posix(),
                    "sha256": (consumed_hashes or {}).get(name) or file_hash(path)} if path else None)
            for name, path in source_paths.items()
        },
        "implementation_hashes": {
            path.relative_to(root).as_posix(): file_hash(path) for path in implementation_paths
        },
        "consumed_hashes": dict(sorted((consumed_hashes or {}).items())),
        "artifact_hashes": {name: _sha256_bytes(payload) for name, payload in artifacts.items()},
        "create_only": True, "immutable_derived_output": True,
        "order_authority": False, "execution_quantity": None, "automatic_order": False,
    }
    for name, payload in {**artifacts, "run-manifest.json": _json_bytes(manifest)}.items():
        with (run_dir / name).open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    return run_dir


def discover_historical_replay(root: Path = ROOT) -> dict[str, Any]:
    evidence_candidates: list[Path] = []
    rejected_schema_errors: dict[str, list[str]] = {}
    base = root / "workspace/outputs/manual-portfolio-analysis"
    if base.exists():
        for path in base.glob("*/manual-portfolio-analysis.json"):
            try:
                source_bytes = path.read_bytes()
                candidate = json.loads(source_bytes.decode("utf-8"))
                schema_bytes = manual_evidence_schema_bytes(
                    candidate, root=root, allow_legacy_replay=True,
                )
                errors = validate_instance(
                    candidate, root / MANUAL_EVIDENCE_SCHEMA.relative_to(ROOT), schema_bytes=schema_bytes,
                )
                if candidate.get("evidence_grade") == "GRADE_B" and not errors:
                    evidence_candidates.append(path)
                elif candidate.get("evidence_grade") == "GRADE_B":
                    rejected_schema_errors[path.relative_to(root).as_posix()] = errors
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
    plan_candidates = [
        path for path in (root / "workspace").rglob("*.json")
        if "portfolio-decision-plan" in path.name.lower()
    ] if (root / "workspace").exists() else []
    evidence_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    plan_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if not evidence_candidates:
        status = "BLOCKED_REAL_FIXTURE_NOT_FOUND"
    elif not plan_candidates:
        status = "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND"
    else:
        status = "READY_FOR_HISTORICAL_REPLAY"
    return {
        "status": status,
        "real_grade_b_fixture": evidence_candidates[0].relative_to(root).as_posix() if evidence_candidates else None,
        "historical_decision_plan": plan_candidates[0].relative_to(root).as_posix() if plan_candidates else None,
        "rejected_grade_b_schema_errors": rejected_schema_errors,
        "current_advisory_created": False,
    }


def _snapshot_authority_hashes(
    snapshot: IntegratedAuthoritySnapshot, evidence: dict[str, Any],
) -> dict[str, str]:
    """Bind supplied evidence to the consumed cohort without reopening authority files."""
    current = snapshot.provenance(authority_source="K3_COMBINED_PRODUCTION")
    supplied = evidence.get("integrated_authority_snapshot_provenance")
    stable_fields = (
        "authority_source", "combined_activation_manifest_sha256", "activation_cohort_id",
        "instrument_identity_artifact_sha256", "session_calendar_artifact_sha256",
        "identity_registry_version", "session_calendar_version",
    )
    evidence_fields = {
        "identity_authority_id": snapshot.identity.artifact["authority_id"],
        "identity_registry_hash": current["instrument_identity_artifact_sha256"],
        "identity_registry_version": current["identity_registry_version"],
        "identity_activation_cohort_id": current["activation_cohort_id"],
        "calendar_hash": current["session_calendar_artifact_sha256"],
        "calendar_policy_identity": snapshot.session.artifact["calendar_policy_identity"],
        "session_activation_cohort_id": current["activation_cohort_id"],
    }
    if (
        not isinstance(supplied, dict)
        or any(supplied.get(key) != current[key] for key in stable_fields)
        or any(evidence.get(key) != value for key, value in evidence_fields.items())
        or supplied.get("run_id") != evidence.get("manual_run_id")
        or supplied.get("report_decision_as_of") != evidence.get("decision_as_of")
    ):
        raise ContractError("INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH")
    evidence_time = _parse_timestamp(evidence.get("decision_as_of"))
    snapshot_time = _parse_timestamp(supplied.get("snapshot_decision_as_of"))
    resolved_time = _parse_timestamp(supplied.get("authority_resolved_at"))
    evaluation_time = _parse_timestamp(snapshot.snapshot_decision_as_of)
    if (
        None in (evidence_time, snapshot_time, resolved_time, evaluation_time)
        or not snapshot_time <= evidence_time <= evaluation_time
        or resolved_time > evaluation_time
    ):
        raise ContractError("INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH")
    return {
        key: current[key] for key in (
            "combined_activation_manifest_sha256", "instrument_identity_artifact_sha256",
            "session_calendar_artifact_sha256",
        )
    } | {"integrated_authority_snapshot_provenance": _sha256_bytes(_json_bytes(current))}


def _load_risk_registry_inputs(registry_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Read the canonical downstream inputs once, retaining consumed-byte hashes."""
    canonical_path = (ROOT / "workspace/policies/instrument_registry.json").resolve()
    if registry_path.resolve() != canonical_path:
        raise ContractError("POLICY_REGISTRY_MISMATCH")
    try:
        registry_bytes = canonical_path.read_bytes()
        policy_bytes = DEFAULT_ALERT_POLICY.read_bytes()
        registry = json.loads(registry_bytes.decode("utf-8"))
        policy = json.loads(policy_bytes.decode("utf-8"))
        if not isinstance(registry, dict) or not isinstance(policy, dict):
            raise ValueError("Canonical inputs must be objects")
    except (OSError, ValueError) as exc:
        raise ContractError("POLICY_REGISTRY_MISMATCH") from exc
    return registry, policy, {
        "instrument_registry": _sha256_bytes(registry_bytes),
        "alert_policy": _sha256_bytes(policy_bytes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a read-only portfolio decision dashboard")
    parser.add_argument("--portfolio-evidence", type=Path)
    parser.add_argument("--decision-plan", type=Path)
    parser.add_argument("--risk-policy", type=Path, default=DEFAULT_RISK_POLICY)
    parser.add_argument("--event-context", type=Path)
    parser.add_argument("--instrument-registry", type=Path)
    parser.add_argument("--current-session-context", type=Path)
    parser.add_argument("--request-accounting", type=Path)
    parser.add_argument("--parent-capture", type=Path, action="append",
                        help="Existing Manual request/response capture; repeat for each artifact")
    parser.add_argument("--holding-timing-snapshot", type=Path,
                        help="Existing technical snapshot; canonical local state/policy are reused")
    parser.add_argument("--holding-timing-capture", type=Path, action="append",
                        help="Existing RAW/ADJUSTED request/response bytes for scoped Kiwoom-only timing")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="INITIAL_COMPILE")
    parser.add_argument("--runtime-advisory-authority")
    parser.add_argument("--discover-historical-replay", action="store_true")
    parser.add_argument("--materialize-plan-only", action="store_true",
                        help="Validate and create only the supplied decision plan JSON")
    parser.add_argument("--input-mode", choices=("MANUAL_READ_ONLY", "LIVE_READ_ONLY"), default="MANUAL_READ_ONLY")
    parser.add_argument("--scheduled-provenance", type=Path)
    parser.add_argument("--expected-runtime-head")
    args = parser.parse_args(argv)
    if args.parent_capture or args.holding_timing_snapshot or args.holding_timing_capture:
        if (args.input_mode != "MANUAL_READ_ONLY" or args.mode != "INITIAL_COMPILE"
                or args.materialize_plan_only or args.discover_historical_replay):
            parser.error("MANUAL_INPUT_SCOPE_REQUIRED")
        if args.holding_timing_capture and not args.holding_timing_snapshot:
            parser.error("TIMING_SNAPSHOT_REQUIRED")
        if args.holding_timing_snapshot and not args.parent_capture:
            parser.error("TIMING_PARENT_CAPTURES_REQUIRED")
    if args.input_mode == "LIVE_READ_ONLY":
        if (not args.scheduled_provenance or not args.expected_runtime_head
                or args.materialize_plan_only or args.discover_historical_replay):
            parser.error("Scheduled compilation requires supplied provenance and expected runtime HEAD")
    elif args.scheduled_provenance or args.expected_runtime_head:
        parser.error("Scheduled inputs require explicit LIVE_READ_ONLY input mode")
    parent_captures = None
    timing_inputs = None
    manual_input_hashes: dict[str, str] = {}
    try:
        if args.parent_capture:
            parent_captures = []
            for index, path in enumerate(args.parent_capture):
                raw = path.read_bytes()
                digest = _sha256_bytes(raw)
                parent_captures.append((raw, digest))
                manual_input_hashes[f"parent_capture_{index}"] = digest
        if args.holding_timing_snapshot:
            snapshot_bytes = args.holding_timing_snapshot.read_bytes()
            state_bytes = DEFAULT_PORTFOLIO_STATE.read_bytes()
            timing_inputs = {"snapshot": json.loads(snapshot_bytes), "state": json.loads(state_bytes)}
            if not all(isinstance(value, dict) for value in timing_inputs.values()):
                raise ValueError("OBJECT_REQUIRED")
            manual_input_hashes.update(holding_timing_snapshot=_sha256_bytes(snapshot_bytes),
                                       holding_timing_state=_sha256_bytes(state_bytes))
            if args.holding_timing_capture:
                timing_inputs["capture_artifacts"] = []
                for index, path in enumerate(args.holding_timing_capture):
                    raw = path.read_bytes()
                    digest = _sha256_bytes(raw)
                    timing_inputs["capture_artifacts"].append((raw, digest))
                    manual_input_hashes[f"holding_timing_capture_{index}"] = digest
    except (OSError, ValueError, UnicodeError):
        # No raw input, path or exception text is disclosed by this new boundary.
        parser.error("MANUAL_INPUT_ARTIFACT_INVALID")
    if args.materialize_plan_only:
        if args.discover_historical_replay:
            parser.error("--materialize-plan-only cannot be combined with --discover-historical-replay")
        if args.decision_plan is None or not args.run_id:
            parser.error("--materialize-plan-only requires --decision-plan and --run-id")
        if args.run_id in {".", ".."} or "/" in args.run_id or "\\" in args.run_id or ":" in args.run_id:
            parser.error("--run-id must be a single directory name")
        try:
            target = write_decision_plan(
                load_json(args.decision_plan),
                args.output_root / args.run_id / "portfolio-decision-plan.json", root=ROOT,
            )
        except (ContractError, OSError, ValueError) as exc:
            parser.error(str(exc))
        print(target)
        return 0
    if args.discover_historical_replay:
        print(json.dumps(discover_historical_replay(), ensure_ascii=False, indent=2))
        return 0
    if args.portfolio_evidence is None or args.decision_plan is None:
        parser.error("--portfolio-evidence and --decision-plan are required")
    evidence_path = args.portfolio_evidence.resolve()
    plan_path = args.decision_plan.resolve()
    risk_path = args.risk_policy.resolve()
    event_path = args.event_context.resolve() if args.event_context else None
    current_context_path = args.current_session_context.resolve() if args.current_session_context else None
    request_accounting_path = args.request_accounting.resolve() if args.request_accounting else None
    evidence_bytes = evidence_path.read_bytes()
    plan_bytes = plan_path.read_bytes()
    evidence_value = json.loads(evidence_bytes.decode("utf-8"))
    evidence_schema_bytes = manual_evidence_schema_bytes(
        evidence_value,
        allow_legacy_replay=args.mode == "HISTORICAL_REPLAY",
    )
    plan_schema_bytes = PLAN_SCHEMA.read_bytes()
    dashboard_schema_bytes = DASHBOARD_SCHEMA.read_bytes()
    current_context_schema_bytes = CURRENT_SESSION_CONTEXT_SCHEMA.read_bytes()
    request_accounting_schema_bytes = REQUEST_ACCOUNTING_SCHEMA.read_bytes()
    plan_value = json.loads(plan_bytes.decode("utf-8"))
    risk_bytes = risk_path.read_bytes()
    risk = json.loads(risk_bytes.decode("utf-8"))
    registry_path = args.instrument_registry.resolve() if args.instrument_registry else ROOT / risk["instrument_registry_path"]
    try:
        registry, alert_policy, registry_hashes = _load_risk_registry_inputs(registry_path)
    except ContractError as exc:
        parser.error(str(exc))
    if timing_inputs is not None:
        timing_inputs["policy"] = alert_policy
        manual_input_hashes["holding_timing_policy"] = registry_hashes["alert_policy"]
    event_bytes = event_path.read_bytes() if event_path else None
    current_context_bytes = current_context_path.read_bytes() if current_context_path else None
    request_accounting_bytes = request_accounting_path.read_bytes() if request_accounting_path else None
    generated = _now()
    seed = _sha256_bytes((file_hash(evidence_path) + file_hash(plan_path) + generated).encode("utf-8"))[:12]
    run_id = args.run_id or f"portfolio-decision-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{seed}"
    current_context = json.loads(current_context_bytes.decode("utf-8")) if current_context_bytes else None
    authority_resolver = derive_us_market_session_authority
    authority_hashes: dict[str, str] = {}
    snapshot = None
    if args.mode != "HISTORICAL_REPLAY":
        try:
            snapshot = load_production_integrated_authority_snapshot(
                trusted_root=ROOT, decision_as_of=generated, resolved_at=generated, run_id=run_id,
            )
            authority_hashes = _snapshot_authority_hashes(snapshot, evidence_value)
        except (IntegratedAuthorityLoadError, ContractError, OSError) as exc:
            parser.error(str(exc))
        authority_resolver = partial(derive_us_market_session_authority_from_snapshot, snapshot)
    scheduled_bytes = args.scheduled_provenance.read_bytes() if args.scheduled_provenance else None
    report, validation = compile_dashboard(
        evidence_value, plan_value, risk, compile_mode=args.mode,
        input_mode=args.input_mode, expected_runtime_head=args.expected_runtime_head,
        scheduled_provenance=json.loads(scheduled_bytes) if scheduled_bytes else None,
        registry=registry, event_context=json.loads(event_bytes.decode("utf-8")) if event_bytes else None,
        run_id=run_id, generated_at=generated,
        runtime_advisory_authority=args.runtime_advisory_authority,
        current_session_context=current_context,
        current_session_authority_resolver=authority_resolver,
        request_accounting=(
            json.loads(request_accounting_bytes.decode("utf-8")) if request_accounting_bytes else None
        ),
        evidence_sha256=_sha256_bytes(evidence_bytes),
        evidence_schema_bytes=evidence_schema_bytes, plan_schema_bytes=plan_schema_bytes,
        dashboard_schema_bytes=dashboard_schema_bytes,
        current_context_schema_bytes=current_context_schema_bytes,
        request_accounting_schema_bytes=request_accounting_schema_bytes,
        parent_capture_artifacts=parent_captures,
        holding_timing_inputs=timing_inputs,
    )
    from portfolio_decision_order_intent import compile_order_intent_artifact

    input_hashes = {
        **manual_input_hashes,
        **authority_hashes,
        **({"scheduled_provenance": _sha256_bytes(scheduled_bytes)} if scheduled_bytes else {}),
        "portfolio_evidence": _sha256_bytes(evidence_bytes),
        "decision_plan": _sha256_bytes(plan_bytes),
        "portfolio_decision": _sha256_bytes(_json_bytes(report)),
        "validation_report": _sha256_bytes(_json_bytes(validation)),
        "risk_policy": _sha256_bytes(risk_bytes),
        **registry_hashes,
        **({"current_session_context": _sha256_bytes(current_context_bytes)} if current_context_bytes is not None else {}),
        **({"request_accounting": _sha256_bytes(request_accounting_bytes)} if request_accounting_bytes is not None else {}),
    }
    order_intent_artifact = compile_order_intent_artifact(
        report, validation, plan_value, evidence_value, risk, registry,
        risk_envelope_sha256=_sha256_bytes(risk_bytes), input_hashes=input_hashes,
        now=generated,
        trigger_provenance=report.get("trigger_provenance"),
        current_session_context=current_context,
        current_session_authority_resolver=authority_resolver,
        integrated_snapshot=snapshot, alert_policy=alert_policy,
    )
    implementation_paths = implementation_provenance_paths(risk_path)
    if authority_hashes:
        implementation_paths.append(ROOT / "manage-us-stock-strategy/scripts/integrated_authority_snapshot.py")
    run_dir = write_run(
        report, validation, output_root=args.output_root.resolve(), root=ROOT,
        source_paths={"portfolio_evidence": evidence_path, "decision_plan": plan_path,
                      "risk_policy": risk_path, "instrument_registry": registry_path,
                      "alert_policy": DEFAULT_ALERT_POLICY,
                      "event_context": event_path, "portfolio_evidence_schema": MANUAL_EVIDENCE_SCHEMA,
                      "current_session_context": current_context_path,
                      "request_accounting": request_accounting_path},
        implementation_paths=implementation_paths,
        order_intent_artifact=order_intent_artifact,
        consumed_hashes={
            **manual_input_hashes,
            **authority_hashes,
            **({"scheduled_provenance": _sha256_bytes(scheduled_bytes)} if scheduled_bytes else {}),
            "portfolio_evidence": _sha256_bytes(evidence_bytes),
            "decision_plan": _sha256_bytes(plan_bytes),
            "portfolio_evidence_schema": _sha256_bytes(evidence_schema_bytes),
            "decision_plan_schema": _sha256_bytes(plan_schema_bytes),
            "dashboard_schema": _sha256_bytes(dashboard_schema_bytes),
            "current_session_context_schema": _sha256_bytes(current_context_schema_bytes),
            "request_accounting_schema": _sha256_bytes(request_accounting_schema_bytes),
            "risk_policy": _sha256_bytes(risk_bytes),
            **registry_hashes,
            **({"event_context": _sha256_bytes(event_bytes)} if event_bytes is not None else {}),
            **({"current_session_context": _sha256_bytes(current_context_bytes)} if current_context_bytes is not None else {}),
            **({"request_accounting": _sha256_bytes(request_accounting_bytes)} if request_accounting_bytes is not None else {}),
        },
    )
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
