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


def validate_snapshot(
    snapshot: dict[str, Any],
    *,
    required_symbols: list[str] | None = None,
    expected_session_date: str | None = None,
    require_official_calendar: bool = True,
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

    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "status": "verified" if not errors else "rejected",
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
