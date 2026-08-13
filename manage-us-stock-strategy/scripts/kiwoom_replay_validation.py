#!/usr/bin/env python3
"""Deterministic Kiwoom history and technical validation for replay-only use."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from build_market_snapshot import (
    INDICATOR_FORMULA_VERSION,
    atr_series,
    derive_timing_features,
    indicator_validation,
    rsi,
    safe_float,
)


DECISION_FIELDS = (
    "ema10_reclaim_confirmed",
    "ema20_reclaim_confirmed",
    "ema20_failed_reclaim_confirmed",
    "decisive_breach_ema20",
    "breakout_confirmed",
    "breakout_acceptance_confirmed",
    "failed_higher_high_confirmed",
    "overheat_rejection_confirmed",
)


def _frame(series: dict[str, Any], cutoff: str) -> pd.DataFrame:
    rows = [row for row in series.get("bars", []) if str(row.get("session")) <= cutoff]
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    frame = pd.DataFrame(rows).set_index("session")
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    return frame.dropna().sort_index()


def calculate_kiwoom_technical(
    raw_series: dict[str, Any], adjusted_series: dict[str, Any], *,
    cutoff: str, minimum_history_bars: int,
) -> dict[str, Any]:
    """Calculate policy-authoritative local indicators from Kiwoom Adjusted OHLCV."""
    raw = _frame(raw_series, cutoff)
    adjusted = _frame(adjusted_series, cutoff)
    errors: list[str] = []
    if raw.empty or adjusted.empty:
        errors.append("SERIES_UNAVAILABLE")
    if not raw.empty and raw.index[-1].date().isoformat() != cutoff:
        errors.append("RAW_CUTOFF_MISMATCH")
    if not adjusted.empty and adjusted.index[-1].date().isoformat() != cutoff:
        errors.append("ADJUSTED_CUTOFF_MISMATCH")
    if len(adjusted) < minimum_history_bars:
        errors.append("INSUFFICIENT_HISTORY")
    if errors:
        return {
            "status": "KIWOOM_TECHNICAL_INSUFFICIENT_HISTORY" if "INSUFFICIENT_HISTORY" in errors else "KIWOOM_TECHNICAL_INVALID",
            "cutoff": cutoff, "history_rows": len(adjusted),
            "minimum_history_bars": minimum_history_bars,
            "formula_version": INDICATOR_FORMULA_VERSION,
            "technical_price_basis": "Kiwoom Adjusted OHLC rescaled to latest Kiwoom Raw close",
            "indicators": {}, "decision_signature": {}, "validation_errors": errors,
            "future_leakage": False, "order_authority": False,
        }
    latest_raw = float(raw["close"].iloc[-1])
    latest_adjusted = float(adjusted["close"].iloc[-1])
    if latest_raw <= 0 or latest_adjusted <= 0:
        errors.append("INVALID_LATEST_SCALE")
        scale = math.nan
    else:
        scale = latest_raw / latest_adjusted
    technical = adjusted.copy()
    technical[["open", "high", "low", "close"]] *= scale
    ema10 = technical["close"].ewm(span=10, adjust=False).mean()
    ema20 = technical["close"].ewm(span=20, adjust=False).mean()
    atr14 = atr_series(technical, 14)
    ema12 = technical["close"].ewm(span=12, adjust=False).mean()
    ema26 = technical["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    prior_volume = technical["volume"].iloc[-21:-1]
    rvol = safe_float(technical["volume"].iloc[-1] / prior_volume.mean()) if len(prior_volume) == 20 and prior_volume.mean() > 0 else None
    validation = indicator_validation(technical, ema10, ema20, atr14)
    if validation.get("status") != "passed":
        errors.extend(str(item) for item in validation.get("errors", []))
    timing = derive_timing_features(technical, ema10, ema20, atr14)
    indicators = {
        "close": safe_float(technical["close"].iloc[-1]),
        "ema10": safe_float(ema10.iloc[-1]),
        "ema20": safe_float(ema20.iloc[-1]),
        "atr14": safe_float(atr14.iloc[-1]),
        "rsi14": rsi(technical["close"]),
        "macd": safe_float(macd.iloc[-1]),
        "macd_signal": safe_float(macd_signal.iloc[-1]),
        "rvol20": rvol,
    }
    if any(value is None or not math.isfinite(float(value)) for value in indicators.values()):
        errors.append("NONFINITE_INDICATOR")
    signature = {field: bool(timing.get(field)) for field in DECISION_FIELDS}
    return {
        "status": "KIWOOM_TECHNICAL_VALIDATED" if not errors else "KIWOOM_TECHNICAL_INVALID",
        "cutoff": cutoff, "history_rows": len(adjusted),
        "minimum_history_bars": minimum_history_bars,
        "formula_version": INDICATOR_FORMULA_VERSION,
        "technical_price_basis": "Kiwoom Adjusted OHLC rescaled to latest Kiwoom Raw close",
        "indicators": indicators, "decision_signature": signature,
        "validation_errors": list(dict.fromkeys(errors)),
        "future_leakage": False, "order_authority": False,
    }


def compare_technical_decisions(
    kiwoom: dict[str, Any] | None, yfinance: dict[str, Any] | None,
) -> tuple[str, bool, list[str]]:
    if not isinstance(kiwoom, dict) or not isinstance(yfinance, dict):
        return "NOT_EVALUATED", False, ["TECHNICAL_INPUT_MISSING"]
    if kiwoom.get("status") != "KIWOOM_TECHNICAL_VALIDATED" or yfinance.get("status") not in {"YFINANCE_TECHNICAL_VALIDATED", "KIWOOM_TECHNICAL_VALIDATED"}:
        return "INCONCLUSIVE", False, ["TECHNICAL_INPUT_INVALID"]
    if kiwoom.get("formula_version") != yfinance.get("formula_version"):
        return "INCONCLUSIVE", False, ["FORMULA_VERSION_MISMATCH"]
    left = kiwoom.get("decision_signature") or {}
    right = yfinance.get("decision_signature") or {}
    flip = any(left.get(field) is not right.get(field) for field in DECISION_FIELDS)
    return ("CONFLICT" if flip else "MATCH"), flip, (["TECHNICAL_DECISION_FLIP"] if flip else ["TECHNICAL_DECISIONS_EQUIVALENT"])


def replay_status_axes(
    *, market_data_valid: bool, technical_status: str,
    research_context_status: str, event_context_status: str,
    portfolio_context_status: str,
) -> dict[str, str | bool]:
    """Keep provider/technical validity distinct from missing strategy archives."""
    if not market_data_valid:
        execution = "DATA_BLOCKED"
        market_status = "DATA_BLOCKED"
    else:
        market_status = "VALIDATED"
        if technical_status != "KIWOOM_TECHNICAL_VALIDATED":
            execution = "DATA_BLOCKED"
        elif research_context_status != "COMPLETE":
            execution = "RESEARCH_REFRESH_REQUIRED"
        elif event_context_status != "COMPLETE":
            execution = "EVENT_REVIEW_PENDING"
        elif portfolio_context_status != "COMPLETE":
            execution = "PORTFOLIO_REVIEW_PENDING"
        else:
            execution = "HUMAN_REVIEW_REQUIRED"
    return {
        "market_data_status": market_status,
        "technical_status": technical_status,
        "research_context_status": research_context_status,
        "event_context_status": event_context_status,
        "portfolio_context_status": portfolio_context_status,
        "execution_status": execution,
        "order_authority": False,
    }
