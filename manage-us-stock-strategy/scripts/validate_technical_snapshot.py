#!/usr/bin/env python3
"""Validate a market snapshot before using technical indicators in a decision.

This gate checks session provenance, an independent completed-close cross-check,
required fields, formula-version consistency, OHLC integrity, and internal
EMA/ATR/timing-feature calculations. It does not authorize a trade.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


EXPECTED_SCHEMA_VERSION = "1.0"
EXPECTED_FORMULA_VERSION = "2026-08-05-ema-atr-v2"
EXPECTED_TIMING_FEATURE_VERSION = "2026-08-05-timing-features-v1"
RELATIVE_TOLERANCE = 1e-7


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def close_enough(actual: float, expected: float) -> bool:
    scale = max(1.0, abs(actual), abs(expected))
    return abs(actual - expected) <= RELATIVE_TOLERANCE * scale


def parse_aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _window_rvol(window: list[dict[str, Any]], index: int) -> float | None:
    absolute = index if index >= 0 else len(window) + index
    if absolute < 20 or absolute >= len(window):
        return None
    prior = [float(item["volume"]) for item in window[absolute - 20:absolute]]
    if not prior or sum(prior) <= 0:
        return None
    return float(window[absolute]["volume"]) / (sum(prior) / len(prior))


def _window_reclaim(
    window: list[dict[str, Any]], index: int, ema_field: str
) -> tuple[bool, int | None, float | None]:
    absolute = index if index >= 0 else len(window) + index
    if absolute <= 0:
        return False, None, None
    signal = window[absolute]
    signal_rvol = _window_rvol(window, absolute)
    age: int | None = None
    test_rvol: float | None = None
    for candidate_age in range(1, 4):
        position = absolute - candidate_age
        if position < 0:
            break
        test = window[position]
        if (
            float(test["low"])
            <= float(test[ema_field]) + 0.25 * float(test["atr14"])
            and float(test["high"])
            >= float(test[ema_field]) - 0.25 * float(test["atr14"])
        ):
            age = candidate_age
            test_rvol = _window_rvol(window, position)
            break
    confirmed = bool(
        signal_rvol is not None
        and age is not None
        and test_rvol is not None
        and float(signal["close"])
        >= float(signal[ema_field]) + 0.10 * float(signal["atr14"])
        and float(signal["close"]) > float(window[absolute - 1]["close"])
        and test_rvol <= 1.0
        and signal_rvol >= 1.0
        and signal_rvol >= 1.2 * test_rvol
    )
    return confirmed, age, test_rvol


def _validate_timing_window(row: dict[str, Any], prefix: str, errors: list[str]) -> None:
    window = row.get("timing_window")
    if not isinstance(window, list) or len(window) < 25:
        errors.append(prefix + "timing_window must contain at least 25 completed bars")
        return
    dates: list[str] = []
    for index, item in enumerate(window):
        if not isinstance(item, dict):
            errors.append(prefix + f"timing_window[{index}] is not an object")
            return
        dates.append(str(item.get("bar_date")))
        for field in ("open", "high", "low", "close", "ema10", "ema20", "atr14"):
            if not finite(item.get(field)) or float(item[field]) <= 0:
                errors.append(prefix + f"timing_window[{index}].{field} is invalid")
                return
        if not finite(item.get("volume")) or float(item["volume"]) < 0:
            errors.append(prefix + f"timing_window[{index}].volume is invalid")
            return
        if float(item["high"]) < max(float(item["open"]), float(item["low"]), float(item["close"])):
            errors.append(prefix + f"timing_window[{index}] high violates OHLC integrity")
        if float(item["low"]) > min(float(item["open"]), float(item["high"]), float(item["close"])):
            errors.append(prefix + f"timing_window[{index}] low violates OHLC integrity")
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        errors.append(prefix + "timing_window dates must be unique and increasing")
    if dates[-1] != row.get("bar_date"):
        errors.append(prefix + "timing_window latest date does not match symbol bar_date")

    last = window[-1]
    previous = window[-2]
    for field in ("open", "high", "low", "close", "volume", "ema10", "ema20", "atr14"):
        if not close_enough(float(last[field]), float(row[field])):
            errors.append(prefix + f"timing_window latest {field} conflicts with symbol field")

    below10 = 0
    for item in reversed(window):
        if float(item["close"]) < float(item["ema10"]):
            below10 += 1
        else:
            break
    below20 = 0
    for item in reversed(window):
        if float(item["close"]) < float(item["ema20"]):
            below20 += 1
        else:
            break
    if row.get("close_below_ema10_consecutive") != below10:
        errors.append(prefix + "consecutive closes below EMA10 mismatch")
    if row.get("close_below_ema20_consecutive") != below20:
        errors.append(prefix + "consecutive closes below EMA20 mismatch")

    signs = []
    for item in window[-9:]:
        difference = float(item["close"]) - float(item["ema20"])
        if difference > 0:
            signs.append(1)
        elif difference < 0:
            signs.append(-1)
    crosses = sum(1 for left, right in zip(signs, signs[1:]) if left != right)
    if row.get("ema20_cross_count_8d") != crosses:
        errors.append(prefix + "EMA20 crossing count mismatch")

    atr = float(last["atr14"])
    prior20_high = max(float(item["high"]) for item in window[-21:-1])
    prior10_low = min(float(item["low"]) for item in window[-11:-1])
    prior10_low_prev = min(float(item["low"]) for item in window[-12:-2])
    avg_dollar_volume = sum(
        float(item["close"]) * float(item["volume"]) for item in window[-21:-1]
    ) / 20
    expected_numeric = {
        "prior_20d_high": prior20_high,
        "prior_10d_low": prior10_low,
        "prior_10d_low_prev": prior10_low_prev,
        "atr14_prev": float(previous["atr14"]),
        "average_dollar_volume_20d_usd": avg_dollar_volume,
        "opening_gap_fraction": float(last["open"]) / float(previous["close"]) - 1,
        "extension_above_ema20_atr": (float(last["close"]) - float(last["ema20"])) / atr,
        "close_position_in_range": (
            (float(last["close"]) - float(last["low"]))
            / (float(last["high"]) - float(last["low"]))
            if float(last["high"]) != float(last["low"])
            else 0.5
        ),
    }
    for field, expected in expected_numeric.items():
        if not finite(row.get(field)) or not close_enough(float(row[field]), expected):
            errors.append(prefix + f"{field} timing-window calculation mismatch")

    ema10_reclaim, age10, test_rvol10 = _window_reclaim(window, -1, "ema10")
    ema20_reclaim, age20, test_rvol20 = _window_reclaim(window, -1, "ema20")
    previous_reclaim20, _, _ = _window_reclaim(window, -2, "ema20")
    boolean_expected = {
        "ema10_reclaim_confirmed": ema10_reclaim,
        "ema20_reclaim_confirmed": ema20_reclaim,
        "ema20_failed_reclaim_confirmed": previous_reclaim20
        and float(last["close"]) < float(previous["low"]),
        "decisive_breach_ema20": float(last["close"])
        <= float(last["ema20"]) - 0.25 * atr,
    }
    current_rvol = _window_rvol(window, -1) or 0.0
    boolean_expected["breakout_confirmed"] = bool(
        float(last["close"]) >= prior20_high + 0.10 * atr and current_rvol >= 1.2
    )
    prior_breakout_level = max(float(item["high"]) for item in window[-22:-2])
    previous_rvol = _window_rvol(window, -2) or 0.0
    previous_breakout = bool(
        float(previous["close"])
        >= prior_breakout_level + 0.10 * float(previous["atr14"])
        and previous_rvol >= 1.2
    )
    boolean_expected["breakout_acceptance_confirmed"] = bool(
        previous_breakout
        and float(last["close"]) >= prior_breakout_level
        and float(last["low"]) >= prior_breakout_level - 0.25 * atr
    )
    prior5 = max(float(item["high"]) for item in window[-7:-2])
    boolean_expected["failed_higher_high_confirmed"] = bool(
        float(previous["high"]) > prior5
        and float(previous["close"]) < prior5
        and float(last["close"]) < float(previous["low"])
    )
    close_position = expected_numeric["close_position_in_range"]
    boolean_expected["overheat_rejection_confirmed"] = bool(
        float(last["high"]) >= float(last["ema20"]) + 2.5 * atr
        and float(last["close"]) <= float(last["ema20"]) + 2.0 * atr
        and close_position <= 0.35
        and current_rvol >= 1.2
    )
    for field, expected in boolean_expected.items():
        if row.get(field) is not expected:
            errors.append(prefix + f"{field} timing-window calculation mismatch")
    optional_expected = {
        "ema10_test_age_sessions": age10,
        "ema10_test_relative_volume": test_rvol10,
        "ema20_test_age_sessions": age20,
        "ema20_test_relative_volume": test_rvol20,
    }
    for field, expected in optional_expected.items():
        actual = row.get(field)
        if expected is None:
            if actual is not None:
                errors.append(prefix + f"{field} must be null")
        elif not finite(actual) or not close_enough(float(actual), float(expected)):
            errors.append(prefix + f"{field} timing-window calculation mismatch")


def independent_close_missing(row: dict[str, Any]) -> bool:
    """Absence only. Partial evidence, price values and conflicts are not absence."""
    value = row.get("quote_crosscheck")
    return value is None or value == {} or (
        isinstance(value, dict) and set(value) == {"status"}
        and value["status"] in {"NOT_VERIFIED", "not_verified", "PENDING", "pending"}
    )


def validate_snapshot(
    snapshot: dict[str, Any], *, required_symbols: list[str] | None = None,
    expected_session_date: str | None = None, require_official_calendar: bool = True,
) -> dict[str, Any]:
    """Legacy/public validation remains strict, including Scheduled and BUY/ADD."""
    return _validate_snapshot(
        snapshot, required_symbols=required_symbols,
        expected_session_date=expected_session_date,
        require_official_calendar=require_official_calendar,
    )


def validate_manual_corporate_actions(
    artifacts: Any, *, captures: list[tuple[bytes, str]], required_symbols: list[str],
    run_id: str, completed_session: str, decision_as_of: str, policy: dict[str, Any],
) -> bool:
    """Check reviewed documentary receipts against consumed bytes; no I/O or approval.

    Receipt hashes must be pinned by the canonical approved policy supplied by
    the Dashboard. Hash consistency alone is not documentary authenticity.
    The empty production-candidate pin set intentionally clears nothing.
    """
    from current_event_risk import validate_bundle_semantics, PRIMARY_SOURCE_TYPES
    from validation_common import canonical_hash
    from urllib.parse import urlparse
    try:
        owner = policy["holding_timing_rules"]["manual_corporate_action_clearance"]
        if (set(owner) != {"status", "version", "scope", "approval_source", "reviewed_receipt_sha256"}
                or owner["status"] != "APPROVED"
                or owner["version"] != "manual-ca-clearance-v1"
                or owner["scope"] != "MANUAL_EXISTING_HOLDING_ONLY"
                or owner["approval_source"] != "USER_APPROVED_CA_CLEARANCE_AND_INPUT_BINDING"):
            return False
        if (not isinstance(required_symbols, list) or not required_symbols
                or len(required_symbols) != len(set(required_symbols))):
            return False
        # Exclude only the pin list to avoid a circular policy/receipt hash.
        policy_context = json.loads(json.dumps(policy))
        policy_context["holding_timing_rules"]["manual_corporate_action_clearance"]["reviewed_receipt_sha256"] = []
        policy_context_hash = canonical_hash(policy_context)
        pins = owner["reviewed_receipt_sha256"]
        if (not isinstance(pins, list) or not pins or len(pins) != len(set(pins))
                or any(not isinstance(h, str) or len(h) != 64
                       or any(c not in "0123456789abcdef" for c in h) for h in pins)):
            return False
        if not isinstance(artifacts, dict) or set(artifacts) != {
                "event_bundle_artifact", "source_artifacts", "adjustment_bindings"}:
            return False

        def unpack(pair):
            raw, expected = pair
            if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("CA_BYTES_MISMATCH")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("CA_OBJECT_REQUIRED")
            return value, expected

        def time(value):
            if not parse_aware_timestamp(value):
                raise ValueError("CA_TIME_INVALID")
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        cutoff = time(decision_as_of)
        bundle, bundle_hash = unpack(artifacts["event_bundle_artifact"])
        if validate_bundle_semantics(bundle) or bundle["analysis_cutoff"] != decision_as_of:
            return False
        sources = artifacts["source_artifacts"]
        bindings = artifacts["adjustment_bindings"]
        if (not isinstance(sources, dict) or not isinstance(bindings, list)
                or any(not isinstance(b, dict) for b in bindings)
                or len({b["ticker"] for b in bindings}) != len(bindings)):
            return False
        source_map = {}
        domains = {
            "MVLL": {"graniteshares.com", "sec.gov"},
            "MRVL": {"marvell.com", "sec.gov"},
            "SOXL": {"direxion.com", "sec.gov"},
            "SOXX": {"ishares.com", "blackrock.com", "sec.gov"},
        }
        for evidence_id, pair in sources.items():
            doc, digest = unpack(pair)
            url = urlparse(doc["source_url"])
            host = url.hostname or ""
            ticker = doc["ticker"]
            if (doc["evidence_id"] != evidence_id or ticker not in domains
                    or url.scheme != "https" or url.username or url.password or url.query or url.fragment
                    or not any(host == d or host.endswith("." + d) for d in domains[ticker])
                    or doc["source_type"] not in PRIMARY_SOURCE_TYPES
                    or not isinstance(doc["extracted_text"], str) or not doc["extracted_text"].strip()
                    or doc["capture_kind"] not in {"ORIGINAL_DOCUMENT", "EXTRACTED_TEXT"}
                    or time(doc["retrieved_at"]) > cutoff):
                return False
            source_map[evidence_id] = (doc, digest)
        # Work from actual consumed request/response pairs, not input PASS flags.
        from run_manual_portfolio_analysis import _parent_capture_evidence
        from build_kiwoom_market_snapshot import normalize_series
        actual = {}
        for cap in _parent_capture_evidence(captures, run_id=run_id, observed_at=decision_as_of):
            reqs = cap.get("requests")
            if (not isinstance(reqs, list) or len(reqs) != len(cap["results"])
                    or cap.get("request_sha256") != canonical_hash(reqs)):
                return False
            started, ended = time(cap["started_at"]), time(cap["observed_at"])
            if not started <= ended <= cutoff:
                return False
            for req, response in zip(reqs, cap["results"]):
                ticker, basis = req.get("ticker"), req.get("price_basis")
                if ticker not in required_symbols:
                    continue
                if (req.get("operation") != "daily_chart" or basis not in {"RAW", "ADJUSTED"}
                        or req.get("completed_session") != completed_session
                        or req.get("fx_applied") is not False
                        or response.get("ticker") != ticker or response.get("operation") != "daily_chart"
                        or response.get("requested_price_basis") != basis
                        or response.get("bridge_status") != "PASS"
                        or response.get("order_authority") is not False):
                    return False
                retrieved = time(response["retrieved_at"])
                if (not started <= retrieved <= ended
                        or not 0 <= (cutoff - retrieved).total_seconds() <= 900):
                    return False
                key = (ticker, basis)
                if key in actual:
                    return False
                series = normalize_series(response.get("data"), ticker=ticker,
                    completed_session=completed_session, price_basis=basis,
                    minimum_history_bars=252 if basis == "ADJUSTED" else 1,
                    pagination=response.get("pagination"))
                if series["status"] != "PASS":
                    return False
                actual[key] = (cap["source_sha256"], series)
        for ticker in required_symbols:
            binding = next(b for b in bindings if b["ticker"] == ticker)
            if set(binding) != {"ticker", "event_ids", "evidence_ids", "capture_sha256", "treatment_evidence_ids"}:
                return False
            capture_hashes = {b: actual[ticker, b][0] for b in ("RAW", "ADJUSTED")}
            if binding["capture_sha256"] != capture_hashes:
                return False
            dates = [row["session"] for row in actual[ticker, "ADJUSTED"][1]["bars"]]
            start = min(dates)
            cats = [c for c in bundle["category_coverage"]
                    if c["ticker"] == ticker and c["event_category"] == "CORPORATE_ACTION"]
            if len(cats) != 1:
                return False
            cat = cats[0]
            if (cat["coverage_status"] != "COMPLETE_FOR_REQUIRED_CATEGORIES"
                    or cat["event_effect"] != "CONTEXT_ONLY"
                    or not cat["evidence_ids"]
                    or not cat["required_source_routes"]
                    or cat["checked_source_routes"] != cat["required_source_routes"]
                    or cat["announcement_status"] not in {"ANNOUNCED", "NOT_YET_ANNOUNCED_AS_OF_CUTOFF"}
                    or cat["point_in_time_eligible"] is not True
                    or not cat["coverage_start"] or not cat["coverage_end"]
                    or cat["coverage_start"][:10] > start or cat["coverage_end"][:10] < completed_session
                    or not time(cat["last_checked_at"]) <= time(cat["retrieved_at"]) <= cutoff):
                return False
            events = [e for e in bundle["events"] if e["ticker"] == ticker
                      and e["event_type"] in {"CORPORATE_ACTION", "ETF_SPLIT_OR_REVERSE_SPLIT", "EX_DIVIDEND"}]
            ids = sorted(e["event_id"] for e in events)
            if (sorted(binding["event_ids"]) != ids
                    or not binding["evidence_ids"] or len(binding["evidence_ids"]) != len(set(binding["evidence_ids"]))
                    or set(cat["evidence_ids"]) - set(binding["evidence_ids"])):
                return False
            for evidence_id in binding["evidence_ids"]:
                if source_map[evidence_id][0]["ticker"] != ticker:
                    return False
            for event in events:
                if (event["verification_status"] != "VERIFIED" or not event["point_in_time_eligible"]
                        or event["instrument_role"] != "DIRECT" or event["applies_to"] != [ticker]
                        or event["policy_effect"] != "CONTEXT_ONLY"
                        or not event["evidence_ids"] or set(event["evidence_ids"]) - set(binding["evidence_ids"])
                        or not event["effective_at"]):
                    return False
            receipts = binding["treatment_evidence_ids"]
            if not isinstance(receipts, list) or len(receipts) != 1:
                return False
            receipt, digest = unpack(sources[receipts[0]])
            if digest not in pins or receipt["ticker"] != ticker:
                return False
            review = receipt["reviewed_treatment"]
            expected_sources = {i: source_map[i][1] for i in binding["evidence_ids"]}
            if (review["event_bundle_sha256"] != bundle_hash
                    or review["capture_sha256"] != capture_hashes
                    or review["source_sha256"] != expected_sources
                    or review["policy_context_sha256"] != policy_context_hash
                    or review["run_id"] != run_id or review["completed_session"] != completed_session
                    or review["decision_as_of"] != decision_as_of
                    or review["history_start"] != start
                    or review["technical_price_basis"] != "split-adjusted OHLC rescaled to latest raw close"
                    or review["adjustment_semantics_verified"] is not True
                    or review["prehistory_effects_resolved"] is not True
                    or review["conflict"] is not False
                    or set(review["event_treatment"]) != set(ids)):
                return False
            for event in events:
                # Event treatment is relative to the consumed completed history,
                # not a later analysis clock. Exact effective-session interpretation
                # remains part of the independently reviewed receipt.
                effective_date = time(event["effective_at"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
                future = effective_date > completed_session
                expected = "NOT_YET_EFFECTIVE" if future else "VERIFIED_APPLIED"
                if review["event_treatment"][event["event_id"]] != expected:
                    return False
            if not events and cat["announcement_status"] != "NOT_YET_ANNOUNCED_AS_OF_CUTOFF":
                return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, StopIteration, OverflowError, ArithmeticError):
        return False


def validate_manual_kiwoom_snapshot(
    snapshot: dict[str, Any], *, required_symbols: list[str], expected_session_date: str,
    capture_artifacts: list[tuple[bytes, str]], run_id: str, decision_as_of: str,
    analysis_observed_at: str, policy: dict[str, Any], closed_at: list[datetime],
    corporate_action_artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bound calculation validation, not standalone Manual authority approval.

    The Dashboard owns canonical policy, Manual scope, account/identity/session
    and Direction gates. This wrapper additionally binds actual acquisition
    bytes and recomputes the existing RAW/ADJUSTED producer. No network calls.
    """
    failure = {"status": "rejected", "errors": ["MANUAL_KIWOOM_TIMING_BINDING_INVALID"],
               "independent_close_status": "NOT_VERIFIED",
               "provider_finalization_verified": "NOT_VERIFIED",
               "local_regular_bar_coherence": "NOT_VERIFIED",
               "technical_analysis_eligibility": "NO"}
    try:
        exception = ((policy.get("holding_timing_rules") or {}).get("second_quote_crosscheck") or {}).get(
            "manual_existing_holding_exception")
        if exception != {
            "status": "APPROVED",
            "version": "2026-09-23-manual-existing-holding-kiwoom-only-v1",
            "approval_source": "USER_K3_BOUNDARY_RESET_MANUAL_EXISTING_HOLDING_KIWOOM_ONLY",
            "scope": "MANUAL_EXISTING_HOLDING_ONLY",
            "missing_independent_close": "CONDITIONAL_NON_BLOCKING",
            "conflicting_independent_close": "EXISTING_POLICY_PRESERVED",
        }:
            return failure
        from run_manual_portfolio_analysis import _parent_capture_evidence, local_regular_bar_coherence
        from validation_common import canonical_hash
        from build_kiwoom_market_snapshot import normalize_series
        from kiwoom_runtime_bridge import RUNTIME_APIS
        from kiwoom_replay_validation import calculate_kiwoom_technical

        def timestamp(value):
            if not parse_aware_timestamp(value):
                raise ValueError("INVALID_TIME")
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        cutoff, observed = timestamp(decision_as_of), timestamp(analysis_observed_at)
        built = timestamp(snapshot["generated_at_utc"])
        if not cutoff <= observed or not 0 <= (observed - built).total_seconds() <= 900 or built > cutoff:
            return failure
        if len(required_symbols) != len(set(required_symbols)) or len(closed_at) != len(required_symbols):
            return failure
        closes = dict(zip(required_symbols, closed_at))
        captures = _parent_capture_evidence(capture_artifacts, run_id=run_id, observed_at=analysis_observed_at)
        series = {}
        local_statuses = {}
        for capture in captures:
            requests = capture.get("requests")
            if (not isinstance(requests, list) or len(requests) != len(capture["results"])
                    or capture.get("request_sha256") != canonical_hash(requests)):
                return failure
            start, end = timestamp(capture["started_at"]), timestamp(capture["observed_at"])
            if not start <= end <= built:
                return failure
            for request, response in zip(requests, capture["results"]):
                if not isinstance(request, dict) or not isinstance(response, dict):
                    return failure
                symbol = request.get("ticker")
                if symbol not in required_symbols or request.get("operation") != "daily_chart":
                    continue
                basis = request.get("price_basis")
                key = (symbol, basis)
                if (basis not in {"RAW", "ADJUSTED"} or key in series
                        or request.get("completed_session") != expected_session_date
                        or request.get("fx_applied") is not False
                        or response.get("operation") != "daily_chart" or response.get("ticker") != symbol
                        or response.get("requested_price_basis") not in (None, basis)
                        or response.get("source_provider") not in (None, "KIWOOM_REST")
                        or response.get("bridge_status") != "PASS"
                        or response.get("order_authority") is not False):
                    return failure
                retrieved = timestamp(response.get("retrieved_at"))
                if (not start <= retrieved <= end or not closes[symbol] <= retrieved <= cutoff
                        or not 0 <= (observed - retrieved).total_seconds() <= 900):
                    return failure
                pagination = response.get("pagination")
                if not isinstance(pagination, dict):
                    return failure
                pages = pagination.get("pages")
                if (pagination.get("api_id") != RUNTIME_APIS["daily_chart"][0]
                        or pagination.get("status") != "SUFFICIENT" or not isinstance(pages, list) or not pages
                        or pagination.get("pages_fetched") != len(pages)
                        or any(not isinstance(page, dict) for page in pages)
                        or [p.get("page_index") for p in pages] != list(range(1, len(pages) + 1))):
                    return failure
                if any(not start <= timestamp(p.get("retrieved_at")) <= retrieved
                       or p.get("api_id") != pagination.get("api_id") for p in pages):
                    return failure
                if basis == "ADJUSTED":
                    rows = response.get("data")
                    if not isinstance(rows, list) or not rows:
                        return failure
                    if len(pages) == 1:
                        counts = [len(rows)]
                    else:
                        counts = [page.get("row_count") for page in pages]
                        if (any(not isinstance(count, int) or isinstance(count, bool) or count < 1
                                for count in counts) or sum(counts) != len(rows)):
                            return failure
                    expected_date = expected_session_date.replace("-", "")
                    expected_rows = []
                    offset = 0
                    for page, count in zip(pages, counts):
                        page_rows = rows[offset:offset + count]
                        offset += count
                        if any(not isinstance(row, dict) for row in page_rows):
                            return failure
                        dates = [str(row.get("dt", "")) for row in page_rows]
                        if any(len(date) != 8 or not date.isdigit() for date in dates):
                            return failure
                        if (page.get("row_count") not in (None, count)
                                or page.get("first_session") not in (None, min(dates))
                                or page.get("last_session") not in (None, max(dates))):
                            return failure
                        if expected_date in dates:
                            if timestamp(page.get("retrieved_at")) < closes[symbol]:
                                return failure
                            expected_rows.extend(row for row in page_rows
                                                 if str(row["dt"]) == expected_date)
                    if (not expected_rows or normalize_series(
                            expected_rows, ticker=symbol,
                            completed_session=expected_session_date,
                            price_basis=basis, minimum_history_bars=1,
                    )["status"] != "PASS"):
                        return failure
                if basis == "RAW":
                    local = local_regular_bar_coherence(
                        response, request=request, captures=captures,
                        expected_completed_session=expected_session_date,
                        core_close_at=closes[symbol].isoformat(),
                        observed_at=analysis_observed_at,
                    )
                    local_statuses[symbol] = local["status"]
                    if local["status"] != "PASS":
                        return dict(failure, local_regular_bar_coherence=local["status"])
                normalized = normalize_series(
                    response.get("data"), ticker=symbol, completed_session=expected_session_date,
                    price_basis=basis, minimum_history_bars=252 if basis == "ADJUSTED" else 1,
                    pagination=pagination,
                )
                if normalized["status"] != "PASS":
                    return failure
                series[key] = normalized
        if (set(local_statuses) == set(required_symbols)
                and all(status == "PASS" for status in local_statuses.values())):
            failure = dict(failure, local_regular_bar_coherence="PASS")
        if not validate_manual_corporate_actions(
                corporate_action_artifacts, captures=capture_artifacts,
                required_symbols=required_symbols, run_id=run_id,
                completed_session=expected_session_date, decision_as_of=decision_as_of, policy=policy):
            return failure
        missing = set()
        for symbol in required_symbols:
            row = snapshot["symbols"][symbol]
            if (row.get("source_provider") != "KIWOOM_REST"
                    or row.get("corporate_action_unresolved") is not False):
                return failure
            calculation = calculate_kiwoom_technical(
                series[(symbol, "RAW")], series[(symbol, "ADJUSTED")],
                cutoff=expected_session_date, minimum_history_bars=252, include_timing_record=True,
            )
            generated = calculation.get("timing_record")
            if calculation["status"] != "KIWOOM_TECHNICAL_VALIDATED" or not generated:
                return failure
            # The calculator intentionally does not approve corporate actions or
            # independent evidence. Every calculated field must match the input.
            if any(row.get(k) != v for k, v in generated.items()
                   if k not in {"corporate_action_unresolved", "quote_crosscheck"}):
                return failure
            if independent_close_missing(row):
                missing.add(symbol)
        result = _validate_snapshot(
            snapshot, required_symbols=required_symbols,
            expected_session_date=expected_session_date,
            require_official_calendar=True, missing_close_symbols=frozenset(missing),
        )
        if missing:
            result["timing_source_mode"] = "KIWOOM_ONLY"
        result["provider_finalization_verified"] = "NOT_VERIFIED"
        result["local_regular_bar_coherence"] = (
            "PASS" if set(local_statuses) == set(required_symbols)
            and all(status == "PASS" for status in local_statuses.values()) else "NOT_VERIFIED"
        )
        result["technical_analysis_eligibility"] = "YES" if result["status"] == "verified" else "NO"
        return result
    except (KeyError, TypeError, ValueError, OverflowError, ArithmeticError):
        return failure



def _validate_snapshot(
    snapshot: dict[str, Any],
    *,
    required_symbols: list[str] | None = None,
    expected_session_date: str | None = None,
    require_official_calendar: bool = True,
    missing_close_symbols: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if snapshot.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {EXPECTED_SCHEMA_VERSION!r}"
        )
    if not parse_aware_timestamp(snapshot.get("generated_at_utc")):
        errors.append("generated_at_utc must be a timezone-aware ISO timestamp")

    provenance = snapshot.get("indicator_provenance") or {}
    formula_version = provenance.get("formula_version")
    if formula_version != EXPECTED_FORMULA_VERSION:
        errors.append(
            f"indicator formula version must be {EXPECTED_FORMULA_VERSION!r}"
        )
    if provenance.get("technical_price_basis") != (
        "split-adjusted OHLC rescaled to latest raw close"
    ):
        errors.append("technical price basis is missing or unsupported")
    if not provenance.get("ema_formula") or not provenance.get("atr_formula"):
        errors.append("EMA/ATR formula provenance is incomplete")
    if provenance.get("timing_feature_version") != EXPECTED_TIMING_FEATURE_VERSION:
        errors.append("timing feature provenance is missing or unsupported")

    session = snapshot.get("session") or {}
    session_date = session.get("us_session_date")
    expected_date = expected_session_date or session.get("expected_us_session_date")
    if not isinstance(session_date, str):
        errors.append("session.us_session_date is missing")
    if expected_date is not None and expected_date != session_date:
        errors.append(
            f"session date {session_date!r} does not match expected {expected_date!r}"
        )
    if session.get("regular_session_complete") is not True:
        errors.append("regular U.S. session is not marked complete")
    if not isinstance(session.get("is_early_close"), bool):
        errors.append("session.is_early_close must be verified as true or false")
    elif session.get("is_early_close") is True:
        errors.append("unadjusted early-close volume cannot validate timing signals")
    if require_official_calendar:
        if session.get("official_calendar_verified") is not True:
            errors.append("official trading calendar is not verified")
        if session.get("calendar_verification_status") != "verified_trading_day":
            errors.append(
                "calendar_verification_status must be 'verified_trading_day'"
            )
        if not session.get("calendar_source_type"):
            errors.append("official calendar source type is missing")
        if not session.get("calendar_source"):
            errors.append("official calendar source is missing")
        if not parse_aware_timestamp(session.get("calendar_verified_at_utc")):
            errors.append("calendar_verified_at_utc is missing or timezone-naive")
    elif session.get("official_calendar_verified") is not True:
        warnings.append("official calendar verification was explicitly bypassed")

    source_errors = snapshot.get("errors")
    if not isinstance(source_errors, list):
        errors.append("top-level errors field must be a list")
    elif source_errors:
        relevant_prefixes = tuple(f"{symbol}:" for symbol in (required_symbols or []))
        relevant = [
            item
            for item in source_errors
            if not relevant_prefixes
            or not isinstance(item, str)
            or item.startswith(relevant_prefixes)
        ]
        if relevant:
            errors.append("snapshot contains source/build errors for required symbols")

    symbols = snapshot.get("symbols") or {}
    if not isinstance(symbols, dict) or not symbols:
        errors.append("snapshot has no symbol records")
        symbols = {}
    selected = required_symbols or sorted(symbols)
    for ticker in selected:
        row = symbols.get(ticker)
        if not isinstance(row, dict):
            errors.append(f"{ticker}: required symbol record is missing")
            continue
        prefix = f"{ticker}: "
        if row.get("bar_date") != session_date:
            errors.append(prefix + "bar_date does not match verified session date")
        if not row.get("source"):
            errors.append(prefix + "market-data source is missing")
        if row.get("technical_price_basis") != provenance.get("technical_price_basis"):
            errors.append(prefix + "technical price basis conflicts with provenance")
        required_positive = (
            "open",
            "high",
            "low",
            "close",
            "ema10",
            "ema20",
            "ema10_prev",
            "ema20_prev",
            "ema10_3d_ago",
            "ema20_3d_ago",
            "atr14",
            "prior_20d_high",
            "prior_10d_low",
            "prior_10d_low_prev",
            "atr14_prev",
            "average_dollar_volume_20d_usd",
        )
        for field in required_positive:
            value = row.get(field)
            if not finite(value) or float(value) <= 0:
                errors.append(prefix + f"{field} must be finite and positive")
        volume = row.get("volume")
        if not finite(volume) or float(volume) < 0:
            errors.append(prefix + "volume must be finite and nonnegative")
        history_rows = row.get("history_rows")
        if not isinstance(history_rows, int) or history_rows < 252:
            errors.append(prefix + "at least 252 history rows are required")

        if all(finite(row.get(field)) for field in ("open", "high", "low", "close")):
            open_value = float(row["open"])
            high_value = float(row["high"])
            low_value = float(row["low"])
            close_value = float(row["close"])
            if high_value < max(open_value, low_value, close_value):
                errors.append(prefix + "high violates OHLC integrity")
            if low_value > min(open_value, high_value, close_value):
                errors.append(prefix + "low violates OHLC integrity")

        rsi14 = row.get("rsi14")
        if not finite(rsi14) or not 0 <= float(rsi14) <= 100:
            errors.append(prefix + "rsi14 must be between 0 and 100")
        volume_ratio = row.get("volume_ratio_to_20d")
        if not finite(volume_ratio) or float(volume_ratio) < 0:
            errors.append(prefix + "volume_ratio_to_20d is invalid")
        atr14_pct = row.get("atr14_pct")
        distance = row.get("distance_from_ema20_fraction")
        if not finite(atr14_pct) or float(atr14_pct) <= 0:
            errors.append(prefix + "atr14_pct must be finite and positive")
        if not finite(distance):
            errors.append(prefix + "distance_from_ema20_fraction is invalid")

        if all(finite(row.get(field)) for field in ("atr14", "close", "atr14_pct")):
            expected_atr_pct = float(row["atr14"]) / float(row["close"])
            if not close_enough(float(row["atr14_pct"]), expected_atr_pct):
                errors.append(prefix + "atr14_pct calculation mismatch")
        if all(
            finite(row.get(field))
            for field in ("close", "ema20", "distance_from_ema20_fraction")
        ):
            expected_distance = float(row["close"]) / float(row["ema20"]) - 1
            if not close_enough(
                float(row["distance_from_ema20_fraction"]), expected_distance
            ):
                errors.append(prefix + "EMA20 distance calculation mismatch")

        if finite(row.get("ema10")) and finite(row.get("ema20")):
            expected_above = float(row["ema10"]) > float(row["ema20"])
            if row.get("ema10_above_ema20") is not expected_above:
                errors.append(prefix + "ema10_above_ema20 flag mismatch")
        if finite(row.get("ema20")) and finite(row.get("ema20_3d_ago")):
            expected_rising = float(row["ema20"]) > float(row["ema20_3d_ago"])
            if row.get("ema20_rising_3d") is not expected_rising:
                errors.append(prefix + "ema20_rising_3d flag mismatch")

        if row.get("timing_feature_version") != EXPECTED_TIMING_FEATURE_VERSION:
            errors.append(prefix + "timing feature version mismatch")
        for field in (
            "ema10_change_3d_atr",
            "ema20_change_3d_atr",
            "opening_gap_fraction",
            "extension_above_ema20_atr",
            "close_position_in_range",
        ):
            if not finite(row.get(field)):
                errors.append(prefix + f"{field} must be finite")
        for field in (
            "close_below_ema10_consecutive",
            "close_below_ema20_consecutive",
            "ema20_cross_count_8d",
        ):
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(prefix + f"{field} must be a nonnegative integer")
        for field in (
            "ema10_reclaim_confirmed",
            "ema20_reclaim_confirmed",
            "ema20_failed_reclaim_confirmed",
            "decisive_breach_ema20",
            "breakout_confirmed",
            "breakout_acceptance_confirmed",
            "failed_higher_high_confirmed",
            "overheat_rejection_confirmed",
        ):
            if not isinstance(row.get(field), bool):
                errors.append(prefix + f"{field} must be boolean")

        if all(finite(row.get(field)) for field in ("ema10", "ema10_3d_ago", "atr14")):
            expected = (float(row["ema10"]) - float(row["ema10_3d_ago"])) / float(row["atr14"])
            if not close_enough(float(row["ema10_change_3d_atr"]), expected):
                errors.append(prefix + "EMA10 normalized direction mismatch")
            direction = "rising" if expected > 0.10 else "falling" if expected < -0.10 else "neutral"
            if row.get("ema10_direction_3d") != direction:
                errors.append(prefix + "EMA10 direction classification mismatch")
        if all(finite(row.get(field)) for field in ("ema20", "ema20_3d_ago", "atr14")):
            expected = (float(row["ema20"]) - float(row["ema20_3d_ago"])) / float(row["atr14"])
            if not close_enough(float(row["ema20_change_3d_atr"]), expected):
                errors.append(prefix + "EMA20 normalized direction mismatch")
            direction = "rising" if expected > 0.10 else "falling" if expected < -0.10 else "neutral"
            if row.get("ema20_direction_3d") != direction:
                errors.append(prefix + "EMA20 direction classification mismatch")

        # Only the bound Manual wrapper may exempt a genuinely absent close.
        # Present malformed/conflicting evidence still takes the strict path.
        if ticker not in missing_close_symbols:
            crosscheck = row.get("quote_crosscheck") or {}
            if crosscheck.get("status") != "verified":
                errors.append(prefix + "independent completed-close cross-check is not verified")
            if crosscheck.get("independent_of_builder") is not True:
                errors.append(prefix + "quote cross-check independence is not verified")
            if crosscheck.get("bar_date") != session_date:
                errors.append(prefix + "quote cross-check session mismatch")
            if not crosscheck.get("source") or not crosscheck.get("source_url"):
                errors.append(prefix + "quote cross-check provenance is incomplete")
            if not parse_aware_timestamp(crosscheck.get("verified_at_utc")):
                errors.append(prefix + "quote cross-check timestamp is invalid")
            second_close = crosscheck.get("completed_close")
            if finite(row.get("close")) and finite(second_close):
                difference = abs(float(row["close"]) - float(second_close))
                tolerance = max(0.05, 0.001 * float(row["close"]))
                if difference > tolerance + 1e-12:
                    errors.append(prefix + "independent close exceeds approved tolerance")
                if not finite(crosscheck.get("difference_usd")):
                    errors.append(prefix + "quote cross-check difference is missing")
                elif not close_enough(float(crosscheck["difference_usd"]), difference):
                    errors.append(prefix + "quote cross-check difference mismatch")
                if not finite(crosscheck.get("tolerance_usd")):
                    errors.append(prefix + "quote cross-check tolerance is missing")
                elif not close_enough(float(crosscheck["tolerance_usd"]), tolerance):
                    errors.append(prefix + "quote cross-check tolerance mismatch")
            else:
                errors.append(prefix + "quote cross-check completed close is invalid")

            proxy_check = crosscheck.get("leveraged_proxy_check")
            if proxy_check is not None:
                if not isinstance(proxy_check, dict):
                    errors.append(prefix + "leveraged proxy check must be an object")
                else:
                    proxy_symbol = proxy_check.get("proxy_symbol")
                    proxy_row = symbols.get(proxy_symbol) if isinstance(proxy_symbol, str) else None
                    if proxy_check.get("role") != "supplemental_integrity_check_not_a_quote_substitute":
                        errors.append(prefix + "leveraged proxy check role is invalid")
                    if proxy_check.get("required_for_resolution") is not True:
                        errors.append(prefix + "leveraged proxy resolution gate is not explicit")
                    if proxy_check.get("status") != "corroborated":
                        errors.append(prefix + "leveraged proxy relationship is not corroborated")
                    if proxy_check.get("bar_date") != session_date:
                        errors.append(prefix + "leveraged proxy check session mismatch")
                    if not isinstance(proxy_row, dict):
                        errors.append(prefix + "leveraged proxy symbol is missing")
                    else:
                        required_values = (
                            row.get("close"),
                            row.get("close_prev"),
                            proxy_row.get("close"),
                            proxy_row.get("close_prev"),
                            proxy_check.get("leverage_multiple"),
                            proxy_check.get("maximum_tracking_error_fraction"),
                        )
                        if not all(finite(value) and float(value) > 0 for value in required_values):
                            errors.append(prefix + "leveraged proxy check inputs are invalid")
                        elif proxy_row.get("bar_date") != session_date:
                            errors.append(prefix + "leveraged proxy bar date mismatch")
                        else:
                            product_return = float(row["close"]) / float(row["close_prev"]) - 1.0
                            proxy_return = float(proxy_row["close"]) / float(proxy_row["close_prev"]) - 1.0
                            expected_return = float(proxy_check["leverage_multiple"]) * proxy_return
                            tracking_error = product_return - expected_return
                            recorded = {
                                "product_return_fraction": product_return,
                                "proxy_return_fraction": proxy_return,
                                "expected_product_return_fraction": expected_return,
                                "tracking_error_fraction": tracking_error,
                            }
                            for field, expected_value in recorded.items():
                                if not finite(proxy_check.get(field)) or not close_enough(
                                    float(proxy_check[field]), expected_value
                                ):
                                    errors.append(prefix + f"leveraged proxy {field} mismatch")
                            if abs(tracking_error) > float(
                                proxy_check["maximum_tracking_error_fraction"]
                            ) + 1e-12:
                                errors.append(prefix + "leveraged proxy tracking error exceeds tolerance")

        _validate_timing_window(row, prefix, errors)

        calculation = row.get("indicator_validation") or {}
        if calculation.get("status") != "passed":
            errors.append(prefix + "builder indicator validation did not pass")
        if calculation.get("formula_version") != formula_version:
            errors.append(prefix + "builder formula version mismatch")
        if calculation.get("errors") != []:
            errors.append(prefix + "builder reported indicator calculation errors")
        if calculation.get("ohlc_integrity") is not True:
            errors.append(prefix + "builder OHLC integrity check did not pass")
        if calculation.get("history_sufficient") is not True:
            errors.append(prefix + "builder history sufficiency check did not pass")

    crosscheck_errors = [item for item in errors if "cross-check" in item or "independent close" in item or "leveraged proxy" in item]
    technical_errors = [item for item in errors if any(token in item for token in (
        "EMA", "ATR", "RVOL", "RSI", "timing", "indicator", "history sufficiency", "formula"
    ))]
    primary_errors = [item for item in errors if item not in crosscheck_errors and item not in technical_errors]
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "status": "verified" if not errors else "rejected",
        "primary_validation_status": "VALIDATED" if not primary_errors else "INVALID",
        "technical_validation_status": "VALIDATED" if not technical_errors else "INVALID",
        "independent_close_status": "NOT_VERIFIED" if missing_close_symbols else ("VERIFIED" if not crosscheck_errors else "PENDING"),
        "actionable_timing_status": "VERIFIED" if not errors else "BLOCKED",
        "primary_validation_errors": primary_errors,
        "technical_validation_errors": technical_errors,
        "independent_close_errors": crosscheck_errors,
        "schema_version": "1.0",
        "formula_version": formula_version,
        "session_date": session_date,
        "required_symbols": selected,
        "checked_symbol_count": len(selected),
        "official_calendar_required": require_official_calendar,
        "errors": errors,
        "warnings": warnings,
        "snapshot_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "scope_note": (
            "This gate validates snapshot structure, provenance, and internal calculations; "
            "the independent completed-close cross-check is structural and does not authorize an order."
        ),
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def valid_fixture() -> dict[str, Any]:
    window: list[dict[str, Any]] = []
    start = datetime(2026, 7, 7)
    for index in range(30):
        close = 97.65 + 0.15 * index
        volume = 1_300_000.0 if index == 29 else 1_000_000.0
        prior = [item["volume"] for item in window[max(0, index - 20):index]]
        relative_volume = (
            volume / (sum(prior) / 20) if len(prior) == 20 else None
        )
        window.append(
            {
                "bar_date": (start + timedelta(days=index)).date().isoformat(),
                "open": close - 0.2,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": volume,
                "ema10": close - 1.0,
                "ema20": close - 2.0,
                "atr14": 4.0,
                "relative_volume_20d": relative_volume,
            }
        )
    last = window[-1]
    previous = window[-2]
    prior20_high = max(item["high"] for item in window[-21:-1])
    prior10_low = min(item["low"] for item in window[-11:-1])
    prior10_low_prev = min(item["low"] for item in window[-12:-2])
    average_dollar_volume = sum(
        item["close"] * item["volume"] for item in window[-21:-1]
    ) / 20
    payload = {
        "schema_version": "1.0",
        "generated_at_utc": "2026-08-05T22:30:00+00:00",
        "session": {
            "us_session_date": "2026-08-05",
            "expected_us_session_date": "2026-08-05",
            "regular_session_complete": True,
            "is_early_close": False,
            "official_calendar_verified": True,
            "calendar_verification_status": "verified_trading_day",
            "calendar_source_type": "primary_exchange_calendar",
            "calendar_source": "https://www.nyse.com/markets/hours-calendars",
            "calendar_verified_at_utc": "2026-08-05T22:31:00+00:00",
        },
        "indicator_provenance": {
            "formula_version": EXPECTED_FORMULA_VERSION,
            "technical_price_basis": "split-adjusted OHLC rescaled to latest raw close",
            "ema_formula": "pandas ewm(span=N, adjust=False); alpha=2/(N+1)",
            "atr_formula": "Wilder ATR14 seeded with mean(TR1..TR14), then ATR=((prior*13)+TR)/14",
            "timing_feature_version": EXPECTED_TIMING_FEATURE_VERSION,
        },
        "symbols": {
            "TEST": {
                "bar_date": "2026-08-05",
                "source": "fixture",
                "technical_price_basis": "split-adjusted OHLC rescaled to latest raw close",
                "open": last["open"],
                "high": last["high"],
                "low": last["low"],
                "close": last["close"],
                "close_prev": previous["close"],
                "volume": last["volume"],
                "ema10": last["ema10"],
                "ema20": last["ema20"],
                "ema10_prev": previous["ema10"],
                "ema20_prev": previous["ema20"],
                "ema10_3d_ago": window[-4]["ema10"],
                "ema20_3d_ago": window[-4]["ema20"],
                "ema10_above_ema20": True,
                "ema20_rising_3d": True,
                "timing_feature_version": EXPECTED_TIMING_FEATURE_VERSION,
                "ema10_direction_3d": "rising",
                "ema20_direction_3d": "rising",
                "ema10_change_3d_atr": (last["ema10"] - window[-4]["ema10"]) / 4.0,
                "ema20_change_3d_atr": (last["ema20"] - window[-4]["ema20"]) / 4.0,
                "close_below_ema10_consecutive": 0,
                "close_below_ema20_consecutive": 0,
                "ema20_cross_count_8d": 0,
                "ema10_reclaim_confirmed": True,
                "ema20_reclaim_confirmed": True,
                "ema20_failed_reclaim_confirmed": False,
                "decisive_breach_ema20": False,
                "breakout_confirmed": False,
                "breakout_acceptance_confirmed": False,
                "failed_higher_high_confirmed": False,
                "overheat_rejection_confirmed": False,
                "close_position_in_range": 0.5,
                "prior_10d_low": prior10_low,
                "prior_10d_low_prev": prior10_low_prev,
                "atr14_prev": previous["atr14"],
                "average_dollar_volume_20d_usd": average_dollar_volume,
                "opening_gap_fraction": last["open"] / previous["close"] - 1.0,
                "extension_above_ema20_atr": 0.5,
                "atr14": 4.0,
                "atr14_pct": 4.0 / 102.0,
                "distance_from_ema20_fraction": 0.02,
                "prior_20d_high": prior20_high,
                "ema10_test_age_sessions": 1,
                "ema10_test_relative_volume": 1.0,
                "ema20_test_age_sessions": 1,
                "ema20_test_relative_volume": 1.0,
                "rsi14": 58.0,
                "volume_ratio_to_20d": 1.3,
                "history_rows": 252,
                "timing_window": window,
                "quote_crosscheck": {
                    "status": "verified",
                    "independent_of_builder": True,
                    "source": "fixture independent source",
                    "source_url": "https://example.test/independent-close",
                    "bar_date": "2026-08-05",
                    "completed_close": 102.02,
                    "verified_at_utc": "2026-08-05T22:32:00+00:00",
                    "difference_usd": 0.02,
                    "tolerance_usd": 0.102
                },
                "indicator_validation": {
                    "status": "passed",
                    "formula_version": EXPECTED_FORMULA_VERSION,
                    "errors": [],
                    "ohlc_integrity": True,
                    "history_sufficient": True,
                },
            }
        },
        "errors": [],
    }
    return payload


def self_test() -> None:
    fixture = valid_fixture()
    passed = validate_snapshot(fixture, required_symbols=["TEST"])
    assert passed["status"] == "verified", passed
    broken = json.loads(json.dumps(fixture))
    broken["symbols"]["TEST"]["ema10_above_ema20"] = False
    rejected = validate_snapshot(broken, required_symbols=["TEST"])
    assert rejected["status"] == "rejected"
    assert any("ema10_above_ema20" in item for item in rejected["errors"])
    print("Self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--required-symbols", nargs="+")
    parser.add_argument("--expected-session-date")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.snapshot:
        parser.error("--snapshot is required")
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    result = validate_snapshot(
        snapshot,
        required_symbols=args.required_symbols,
        expected_session_date=args.expected_session_date,
        require_official_calendar=True,
    )
    if args.output:
        atomic_write_json(args.output, result)
        print(args.output.resolve())
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
