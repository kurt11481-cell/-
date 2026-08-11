#!/usr/bin/env python3
"""Build a completed-session technical snapshot from yfinance market data.

yfinance is an unofficial Yahoo Finance wrapper. The caller must independently
verify the official U.S. trading calendar and completed close before treating
the snapshot as actionable.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time as time_module
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:  # Keep deterministic tests/imports usable before installation.
    yf = None


ET = ZoneInfo("America/New_York")
UTC = timezone.utc
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"
MARKET_SNAPSHOT_SCHEMA_VERSION = "1.0"
INDICATOR_FORMULA_VERSION = "2026-08-05-ema-atr-v2"
TIMING_FEATURE_VERSION = "2026-08-05-timing-features-v1"
INDICATOR_TOLERANCE = 1e-8
DEFAULT_MARKET_DATA_PROVIDER = "yfinance"
DEFAULT_REQUEST_DELAY_SECONDS = 1.0


class SnapshotError(RuntimeError):
    pass


class RequestPacer:
    """Enforce a minimum interval between external market-data requests."""

    def __init__(
        self,
        minimum_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
        *,
        clock: Any = time_module.monotonic,
        sleeper: Any = time_module.sleep,
    ) -> None:
        if not finite(minimum_delay_seconds) or float(minimum_delay_seconds) < 0:
            raise ValueError("minimum request delay must be a non-negative number")
        self.minimum_delay_seconds = float(minimum_delay_seconds)
        self._clock = clock
        self._sleeper = sleeper
        self._last_request_at: float | None = None

    def wait(self) -> None:
        now = float(self._clock())
        if self._last_request_at is not None:
            remaining = self.minimum_delay_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleeper(remaining)
        self._last_request_at = float(self._clock())


def finite(value: Any) -> bool:
    # pandas commonly returns NumPy scalar types from ``Series.iloc``.  Treat
    # those as real numbers too; otherwise valid integer volume values become
    # null when timing-window records are serialized.
    return isinstance(value, (int, float, np.integer, np.floating)) and math.isfinite(
        float(value)
    )


def safe_float(value: Any) -> float | None:
    return float(value) if finite(value) else None


def _flatten_yfinance_columns(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Return one ticker with ordinary OHLCV column names."""

    result = frame.copy()
    if isinstance(result.columns, pd.MultiIndex):
        selected = None
        for level in range(result.columns.nlevels):
            values = {str(value) for value in result.columns.get_level_values(level)}
            if ticker in values:
                selected = result.xs(ticker, axis=1, level=level, drop_level=True)
                break
        if selected is None:
            raise SnapshotError(f"{ticker} yfinance response has no matching column level")
        result = selected
    result.columns = [str(column).strip() for column in result.columns]
    return result


def yfinance_frame_to_chart_result(
    ticker: str, frame: pd.DataFrame
) -> dict[str, Any]:
    """Convert a yfinance daily DataFrame into the builder's chart schema."""

    data = _flatten_yfinance_columns(frame, ticker)
    columns = {column.lower(): column for column in data.columns}
    required = ("open", "high", "low", "close", "adj close", "volume")
    missing = [field for field in required if field not in columns]
    if missing:
        raise SnapshotError(
            f"{ticker} yfinance response is missing columns: {', '.join(missing)}"
        )
    data = data.dropna(subset=[columns["close"], columns["adj close"]]).sort_index()
    if data.empty:
        raise SnapshotError(f"{ticker} yfinance response has no valid daily rows")

    timestamps: list[int] = []
    for index_value in pd.to_datetime(data.index):
        bar_date = index_value.date()
        close_time = datetime(
            bar_date.year, bar_date.month, bar_date.day, 16, 0, tzinfo=ET
        )
        timestamps.append(int(close_time.timestamp()))

    def values(name: str) -> list[float | None]:
        return [safe_float(value) for value in data[columns[name]].tolist()]

    events: dict[str, dict[str, Any]] = {}
    split_column = columns.get("stock splits")
    if split_column:
        split_events: dict[str, Any] = {}
        for position, value in enumerate(data[split_column].tolist()):
            split_value = safe_float(value)
            if split_value is not None and split_value > 0:
                epoch = timestamps[position]
                split_events[str(epoch)] = {
                    "date": epoch,
                    "splitRatio": str(split_value),
                }
        if split_events:
            events["splits"] = split_events

    dividend_column = columns.get("dividends")
    if dividend_column:
        dividend_events: dict[str, Any] = {}
        for position, value in enumerate(data[dividend_column].tolist()):
            dividend = safe_float(value)
            if dividend is not None and dividend != 0:
                epoch = timestamps[position]
                dividend_events[str(epoch)] = {"date": epoch, "amount": dividend}
        if dividend_events:
            events["dividends"] = dividend_events

    return {
        "meta": {
            "symbol": ticker,
            "exchangeTimezoneName": "America/New_York",
        },
        "timestamp": timestamps,
        "indicators": {
            "quote": [
                {
                    "open": values("open"),
                    "high": values("high"),
                    "low": values("low"),
                    "close": values("close"),
                    "volume": values("volume"),
                }
            ],
            "adjclose": [{"adjclose": values("adj close")}],
        },
        "events": events,
        "_provider": "yfinance",
        "_provider_version": getattr(yf, "__version__", None),
        "_request_mode": "sequential_single_ticker",
    }


def fetch_yfinance_chart(
    ticker: str,
    years: int = 3,
    *,
    pacer: RequestPacer | None = None,
) -> dict[str, Any]:
    """Fetch unadjusted daily OHLCV and corporate actions through yfinance."""

    if yf is None:
        raise SnapshotError(
            "yfinance is not installed; install the bundled requirements.txt first"
        )
    now = datetime.now(UTC)
    start = (now - timedelta(days=366 * years)).date().isoformat()
    end = (now + timedelta(days=1)).date().isoformat()
    request_pacer = pacer or RequestPacer()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request_pacer.wait()
            kwargs = {
                "tickers": ticker,
                "start": start,
                "end": end,
                "interval": "1d",
                "actions": True,
                "auto_adjust": False,
                "repair": False,
                "prepost": False,
                "threads": False,
                "progress": False,
                "timeout": 15,
                "multi_level_index": False,
            }
            try:
                frame = yf.download(**kwargs)
            except TypeError:
                # Preserve compatibility with older supported yfinance releases.
                kwargs.pop("multi_level_index")
                frame = yf.download(**kwargs)
            if frame is None or frame.empty:
                raise SnapshotError("empty yfinance download")
            return yfinance_frame_to_chart_result(ticker, frame)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time_module.sleep(max(DEFAULT_REQUEST_DELAY_SECONDS, 2.0**attempt))
    raise SnapshotError(f"{ticker} yfinance request failed: {last_error}")


def fetch_chart(
    session: urllib.request.OpenerDirector,
    ticker: str,
    years: int = 3,
    *,
    pacer: RequestPacer | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    params = {
        "period1": int((now - timedelta(days=366 * years)).timestamp()),
        "period2": int((now + timedelta(days=1)).timestamp()),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    last_error: Exception | None = None
    request_pacer = pacer or RequestPacer()
    for attempt in range(3):
        try:
            request_pacer.wait()
            request_url = (
                f"{URL.format(ticker=ticker)}?{urllib.parse.urlencode(params)}"
            )
            request = urllib.request.Request(
                request_url, headers={"User-Agent": USER_AGENT}
            )
            with session.open(request, timeout=15) as response:
                status = response.getcode()
                if status in (401, 429):
                    raise SnapshotError(f"Yahoo HTTP {status}")
                payload = json.loads(response.read().decode("utf-8"))
            chart = payload.get("chart") or {}
            if chart.get("error"):
                raise SnapshotError(str(chart["error"]))
            results = chart.get("result") or []
            if not results:
                raise SnapshotError("empty chart result")
            result = results[0]
            result["_provider"] = "yahoo-chart"
            result["_provider_version"] = None
            result["_request_mode"] = "sequential_single_ticker"
            return result
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            SnapshotError,
        ) as exc:
            last_error = exc
            if attempt < 2:
                time_module.sleep(1.5 * (2**attempt))
    raise SnapshotError(f"{ticker} chart request failed: {last_error}")


def chart_frame(result: dict[str, Any]) -> pd.DataFrame:
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") or []
    adjclose_blocks = indicators.get("adjclose") or []
    if not timestamps or not quotes:
        raise SnapshotError("missing timestamp or quote arrays")
    quote = quotes[0]
    adj = adjclose_blocks[0].get("adjclose") if adjclose_blocks else quote.get("close")
    length = len(timestamps)
    columns = {
        "open": quote.get("open", [None] * length),
        "high": quote.get("high", [None] * length),
        "low": quote.get("low", [None] * length),
        "close": quote.get("close", [None] * length),
        "volume": quote.get("volume", [None] * length),
        "adjclose": adj or [None] * length,
    }
    frame = pd.DataFrame(columns, index=pd.to_datetime(timestamps, unit="s", utc=True))
    frame.index = frame.index.tz_convert(ET)
    for column in frame:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["close", "adjclose"]).sort_index()
    if frame.empty:
        raise SnapshotError("no valid completed price rows")
    return frame


def rsi(series: pd.Series, period: int = 14) -> float | None:
    if len(series) < period + 2:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False).mean()
    last_gain = safe_float(gain.iloc[-1])
    last_loss = safe_float(loss.iloc[-1])
    if last_gain is None or last_loss is None:
        return None
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    if last_gain == 0:
        return 0.0
    rs = gain / loss.replace(0, np.nan)
    value = 100 - 100 / (1 + rs)
    return safe_float(value.iloc[-1])


def build_account_summary(
    state: dict[str, Any],
    holdings: dict[str, Any],
    symbol_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Return holdings value and only use cash when the broker snapshot verified it."""
    holdings_value = 0.0
    value_complete = True
    for ticker, shares in holdings.items():
        row = symbol_metrics.get(ticker)
        if row and finite(row.get("close")):
            holdings_value += float(shares) * float(row["close"])
        else:
            value_complete = False

    broker_snapshot = state.get("last_confirmed_broker_snapshot") or {}
    cash_verified = bool(broker_snapshot.get("cash_verified"))
    brokerage_cash = state.get("brokerage_cash_usd")
    available_cash = state.get("available_cash_usd")
    cash_estimate = state.get("cash_pct_estimate")
    account_value = None
    account_value_is_estimate = False
    account_value_status = "unavailable_incomplete_holdings_value"

    if value_complete and cash_verified and finite(brokerage_cash):
        account_value = holdings_value + float(brokerage_cash)
        account_value_status = "verified_holdings_plus_verified_brokerage_cash"
    elif value_complete and finite(cash_estimate) and 0 <= float(cash_estimate) < 1:
        account_value = holdings_value / (1 - float(cash_estimate))
        account_value_is_estimate = True
        account_value_status = "estimated_from_holdings_and_cash_fraction"
    elif value_complete and not cash_verified:
        account_value_status = "unavailable_unverified_cash"
    elif value_complete:
        account_value_status = "unavailable_missing_verified_cash_value"

    return {
        "holdings_market_value_usd": holdings_value if value_complete else None,
        "cash_verified": cash_verified,
        "brokerage_cash_usd": (
            brokerage_cash if cash_verified and finite(brokerage_cash) else None
        ),
        "available_cash_usd": (
            available_cash if cash_verified and finite(available_cash) else None
        ),
        "account_value_usd": account_value,
        "account_value_is_estimate": account_value_is_estimate,
        "account_value_status": account_value_status,
    }
def normalized_technical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return split-adjusted OHLC rescaled to the latest raw-close price basis.

    Yahoo's adjusted close is suitable for historical indicators but can be on a
    different scale from the executable raw close after a split. Applying each
    row's adjustment factor and then rescaling the full series to the latest raw
    close preserves split continuity while keeping today's EMA/ATR levels directly
    comparable with the current quote.
    """

    latest_close = safe_float(frame["close"].iloc[-1])
    latest_adjusted = safe_float(frame["adjclose"].iloc[-1])
    if latest_close is None or latest_adjusted in (None, 0):
        raise SnapshotError("invalid latest close or adjusted close")
    factor = (frame["adjclose"] / frame["close"]).replace([np.inf, -np.inf], np.nan)
    scale = latest_close / latest_adjusted
    technical = pd.DataFrame(index=frame.index)
    for column in ("open", "high", "low", "close"):
        technical[column] = frame[column] * factor * scale
    technical["volume"] = frame["volume"]
    technical = technical.dropna(subset=["open", "high", "low", "close"])
    if technical.empty:
        raise SnapshotError("no valid split-adjusted OHLC rows")
    return technical


def recursive_ema_last(series: pd.Series, span: int) -> float | None:
    clean = series.dropna().astype(float)
    if clean.empty:
        return None
    alpha = 2.0 / (span + 1.0)
    value = float(clean.iloc[0])
    for item in clean.iloc[1:]:
        value = alpha * float(item) + (1.0 - alpha) * value
    return value if math.isfinite(value) else None


def atr_series(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    values = pd.Series(np.nan, index=true_range.index, dtype=float)
    if len(true_range) < period:
        return values
    values.iloc[period - 1] = float(true_range.iloc[:period].mean())
    for position in range(period, len(true_range)):
        values.iloc[position] = (
            values.iloc[position - 1] * (period - 1) + true_range.iloc[position]
        ) / period
    return values


def recursive_wilder_atr_last(frame: pd.DataFrame, period: int = 14) -> float | None:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1).dropna()
    if len(true_range) < period:
        return None
    value = float(true_range.iloc[:period].mean())
    for item in true_range.iloc[period:]:
        value = (value * (period - 1) + float(item)) / period
    return value if math.isfinite(value) else None


def indicator_validation(
    technical: pd.DataFrame,
    ema10: pd.Series,
    ema20: pd.Series,
    atr14: pd.Series,
) -> dict[str, Any]:
    errors: list[str] = []
    ema10_reference = recursive_ema_last(technical["close"], 10)
    ema20_reference = recursive_ema_last(technical["close"], 20)
    atr14_reference = recursive_wilder_atr_last(technical, 14)
    ema10_last = safe_float(ema10.iloc[-1])
    ema20_last = safe_float(ema20.iloc[-1])
    ema10_error = (
        abs(ema10_last - ema10_reference)
        if ema10_last is not None and ema10_reference is not None
        else None
    )
    ema20_error = (
        abs(ema20_last - ema20_reference)
        if ema20_last is not None and ema20_reference is not None
        else None
    )
    atr14_last = safe_float(atr14.iloc[-1])
    atr14_error = (
        abs(atr14_last - atr14_reference)
        if atr14_last is not None and atr14_reference is not None
        else None
    )
    if ema10_error is None or ema10_error > INDICATOR_TOLERANCE:
        errors.append("EMA10 independent calculation mismatch")
    if ema20_error is None or ema20_error > INDICATOR_TOLERANCE:
        errors.append("EMA20 independent calculation mismatch")
    if atr14_error is None or atr14_error > INDICATOR_TOLERANCE:
        errors.append("ATR14 independent calculation mismatch")
    ohlc_valid = bool(
        (
            (technical["high"] >= technical[["open", "close", "low"]].max(axis=1))
            & (technical["low"] <= technical[["open", "close", "high"]].min(axis=1))
            & (technical[["open", "high", "low", "close"]] > 0).all(axis=1)
        ).all()
    )
    if not ohlc_valid:
        errors.append("OHLC integrity check failed")
    history_sufficient = len(technical) >= 252
    if not history_sufficient:
        errors.append("fewer than 252 valid OHLC rows")
    if atr14_last is None:
        errors.append("ATR14 is unavailable")
    return {
        "status": "passed" if not errors else "failed",
        "formula_version": INDICATOR_FORMULA_VERSION,
        "ema10_independent_error": safe_float(ema10_error),
        "ema20_independent_error": safe_float(ema20_error),
        "atr14_independent_error": safe_float(atr14_error),
        "tolerance": INDICATOR_TOLERANCE,
        "ohlc_integrity": ohlc_valid,
        "history_sufficient": history_sufficient,
        "errors": errors,
    }


def slope_value(series: pd.Series, window: int, lookback: int) -> tuple[float | None, float | None]:
    ma = series.rolling(window).mean()
    current = safe_float(ma.iloc[-1]) if len(ma) else None
    previous = safe_float(ma.iloc[-1 - lookback]) if len(ma) > lookback else None
    return current, previous


def return_over_rows(series: pd.Series, rows: int) -> float | None:
    clean = series.dropna()
    if len(clean) <= rows:
        return None
    return safe_float(clean.iloc[-1] / clean.iloc[-1 - rows] - 1)


def recent_split(result: dict[str, Any], latest_bar: pd.Timestamp) -> bool:
    events = result.get("events") or {}
    splits = events.get("splits") or {}
    for item in splits.values():
        epoch = item.get("date")
        if epoch:
            event_time = pd.Timestamp(datetime.fromtimestamp(int(epoch), UTC)).tz_convert(ET)
            if abs((latest_bar.date() - event_time.date()).days) <= 10:
                return True
    return False


def _direction(current: float | None, previous: float | None, atr: float | None) -> str | None:
    """Classify a three-session EMA change on an ATR-normalized basis."""

    if current is None or previous is None or atr in (None, 0):
        return None
    normalized = (current - previous) / atr
    if normalized > 0.10:
        return "rising"
    if normalized < -0.10:
        return "falling"
    return "neutral"


def _consecutive(condition: pd.Series) -> int:
    count = 0
    for value in reversed(condition.fillna(False).tolist()):
        if not bool(value):
            break
        count += 1
    return count


def _cross_count(close: pd.Series, ema: pd.Series, lookback: int = 8) -> int:
    values = (close - ema).tail(lookback + 1).dropna()
    signs: list[int] = []
    for value in values:
        if value > 0:
            signs.append(1)
        elif value < 0:
            signs.append(-1)
    return sum(1 for left, right in zip(signs, signs[1:]) if left != right)


def _relative_volume_at(volume: pd.Series, position: int, lookback: int = 20) -> float | None:
    absolute = position if position >= 0 else len(volume) + position
    if absolute < lookback or absolute >= len(volume):
        return None
    prior = volume.iloc[absolute - lookback:absolute].mean()
    current = safe_float(volume.iloc[absolute])
    if current is None or not finite(prior) or float(prior) <= 0:
        return None
    return safe_float(current / float(prior))


def _recent_ema_test(
    frame: pd.DataFrame,
    ema: pd.Series,
    atr: pd.Series,
    *,
    end_position: int = -1,
    maximum_age: int = 3,
) -> tuple[int | None, float | None]:
    """Find the most recent prior EMA-zone test, excluding the signal bar."""

    signal = end_position if end_position >= 0 else len(frame) + end_position
    for age in range(1, maximum_age + 1):
        position = signal - age
        if position < 0:
            break
        values = (
            safe_float(frame["low"].iloc[position]),
            safe_float(frame["high"].iloc[position]),
            safe_float(ema.iloc[position]),
            safe_float(atr.iloc[position]),
        )
        if any(value is None for value in values):
            continue
        low, high, ema_value, atr_value = values
        assert low is not None and high is not None
        assert ema_value is not None and atr_value is not None
        if low <= ema_value + 0.25 * atr_value and high >= ema_value - 0.25 * atr_value:
            return age, _relative_volume_at(frame["volume"], position)
    return None, None


def _reclaim_confirmed(
    frame: pd.DataFrame,
    ema: pd.Series,
    atr: pd.Series,
    *,
    position: int = -1,
) -> tuple[bool, int | None, float | None]:
    absolute = position if position >= 0 else len(frame) + position
    if absolute <= 0:
        return False, None, None
    close = safe_float(frame["close"].iloc[absolute])
    previous_close = safe_float(frame["close"].iloc[absolute - 1])
    ema_value = safe_float(ema.iloc[absolute])
    atr_value = safe_float(atr.iloc[absolute])
    signal_rvol = _relative_volume_at(frame["volume"], absolute)
    age, test_rvol = _recent_ema_test(
        frame, ema, atr, end_position=absolute, maximum_age=3
    )
    confirmed = bool(
        close is not None
        and previous_close is not None
        and ema_value is not None
        and atr_value is not None
        and signal_rvol is not None
        and age is not None
        and test_rvol is not None
        and close >= ema_value + 0.10 * atr_value
        and close > previous_close
        and test_rvol <= 1.0
        and signal_rvol >= 1.0
        and signal_rvol >= 1.2 * test_rvol
    )
    return confirmed, age, test_rvol


def derive_timing_features(
    technical: pd.DataFrame,
    ema10: pd.Series,
    ema20: pd.Series,
    atr14: pd.Series,
) -> dict[str, Any]:
    """Derive fixed, completed-bar timing features used by the policy evaluator."""

    close = technical["close"]
    current_close = safe_float(close.iloc[-1])
    previous_close = safe_float(close.iloc[-2]) if len(close) >= 2 else None
    current_atr = safe_float(atr14.iloc[-1])
    previous_atr = safe_float(atr14.iloc[-2]) if len(atr14) >= 2 else None
    current_ema10 = safe_float(ema10.iloc[-1])
    current_ema20 = safe_float(ema20.iloc[-1])
    previous_ema20 = safe_float(ema20.iloc[-2]) if len(ema20) >= 2 else None
    ema10_old = safe_float(ema10.iloc[-4]) if len(ema10) >= 4 else None
    ema20_old = safe_float(ema20.iloc[-4]) if len(ema20) >= 4 else None

    ema10_reclaim, ema10_test_age, ema10_test_rvol = _reclaim_confirmed(
        technical, ema10, atr14
    )
    ema20_reclaim, ema20_test_age, ema20_test_rvol = _reclaim_confirmed(
        technical, ema20, atr14
    )
    previous_ema20_reclaim, _, _ = _reclaim_confirmed(
        technical, ema20, atr14, position=-2
    )

    prior20_high = (
        safe_float(technical["high"].iloc[-21:-1].max())
        if len(technical) >= 21
        else None
    )
    breakout_level_previous = (
        safe_float(technical["high"].iloc[-22:-2].max())
        if len(technical) >= 22
        else None
    )
    previous_breakout = bool(
        len(technical) >= 22
        and previous_close is not None
        and previous_atr is not None
        and breakout_level_previous is not None
        and previous_close >= breakout_level_previous + 0.10 * previous_atr
        and (_relative_volume_at(technical["volume"], -2) or 0) >= 1.2
    )
    breakout_acceptance = bool(
        previous_breakout
        and current_close is not None
        and current_atr is not None
        and breakout_level_previous is not None
        and current_close >= breakout_level_previous
        and safe_float(technical["low"].iloc[-1]) is not None
        and float(technical["low"].iloc[-1])
        >= breakout_level_previous - 0.25 * current_atr
    )

    prior5_high_before_signal = (
        safe_float(technical["high"].iloc[-7:-2].max())
        if len(technical) >= 7
        else None
    )
    failed_higher_high = bool(
        prior5_high_before_signal is not None
        and safe_float(technical["high"].iloc[-2]) is not None
        and float(technical["high"].iloc[-2]) > prior5_high_before_signal
        and previous_close is not None
        and previous_close < prior5_high_before_signal
        and current_close is not None
        and safe_float(technical["low"].iloc[-2]) is not None
        and current_close < float(technical["low"].iloc[-2])
    )

    high = safe_float(technical["high"].iloc[-1])
    low = safe_float(technical["low"].iloc[-1])
    open_value = safe_float(technical["open"].iloc[-1])
    rvol = _relative_volume_at(technical["volume"], -1)
    range_value = high - low if high is not None and low is not None else None
    close_position = (
        (current_close - low) / range_value
        if current_close is not None and low is not None and range_value not in (None, 0)
        else None
    )
    overheat_rejection = bool(
        high is not None
        and current_close is not None
        and current_ema20 is not None
        and current_atr is not None
        and close_position is not None
        and rvol is not None
        and high >= current_ema20 + 2.5 * current_atr
        and current_close <= current_ema20 + 2.0 * current_atr
        and close_position <= 0.35
        and rvol >= 1.2
    )

    previous_low = safe_float(technical["low"].iloc[-2]) if len(technical) >= 2 else None
    ema20_failed_reclaim = bool(
        previous_ema20_reclaim
        and current_close is not None
        and previous_low is not None
        and current_close < previous_low
    )
    prior10_low = (
        safe_float(technical["low"].iloc[-11:-1].min())
        if len(technical) >= 11
        else None
    )
    prior10_low_previous = (
        safe_float(technical["low"].iloc[-12:-2].min())
        if len(technical) >= 12
        else None
    )
    avg_dollar_volume = (
        safe_float((technical["close"].iloc[-21:-1] * technical["volume"].iloc[-21:-1]).mean())
        if len(technical) >= 21
        else None
    )
    opening_gap = (
        open_value / previous_close - 1
        if open_value is not None and previous_close not in (None, 0)
        else None
    )
    extension_atr = (
        (current_close - current_ema20) / current_atr
        if current_close is not None and current_ema20 is not None and current_atr not in (None, 0)
        else None
    )

    return {
        "timing_feature_version": TIMING_FEATURE_VERSION,
        "ema10_direction_3d": _direction(current_ema10, ema10_old, current_atr),
        "ema20_direction_3d": _direction(current_ema20, ema20_old, current_atr),
        "ema10_change_3d_atr": safe_float(
            (current_ema10 - ema10_old) / current_atr
            if current_ema10 is not None and ema10_old is not None and current_atr not in (None, 0)
            else None
        ),
        "ema20_change_3d_atr": safe_float(
            (current_ema20 - ema20_old) / current_atr
            if current_ema20 is not None and ema20_old is not None and current_atr not in (None, 0)
            else None
        ),
        "close_below_ema10_consecutive": _consecutive(close < ema10),
        "close_below_ema20_consecutive": _consecutive(close < ema20),
        "ema20_cross_count_8d": _cross_count(close, ema20, 8),
        "ema10_reclaim_confirmed": ema10_reclaim,
        "ema10_test_age_sessions": ema10_test_age,
        "ema10_test_relative_volume": ema10_test_rvol,
        "ema20_reclaim_confirmed": ema20_reclaim,
        "ema20_test_age_sessions": ema20_test_age,
        "ema20_test_relative_volume": ema20_test_rvol,
        "ema20_failed_reclaim_confirmed": ema20_failed_reclaim,
        "decisive_breach_ema20": bool(
            current_close is not None
            and current_ema20 is not None
            and current_atr is not None
            and current_close <= current_ema20 - 0.25 * current_atr
        ),
        "breakout_confirmed": bool(
            current_close is not None
            and current_atr is not None
            and prior20_high is not None
            and current_close >= prior20_high + 0.10 * current_atr
            and (rvol or 0) >= 1.2
        ),
        "breakout_acceptance_confirmed": breakout_acceptance,
        "failed_higher_high_confirmed": failed_higher_high,
        "overheat_rejection_confirmed": overheat_rejection,
        "close_position_in_range": safe_float(close_position),
        "prior_10d_low": prior10_low,
        "prior_10d_low_prev": prior10_low_previous,
        "atr14_prev": previous_atr,
        "average_dollar_volume_20d_usd": avg_dollar_volume,
        "opening_gap_fraction": safe_float(opening_gap),
        "extension_above_ema20_atr": safe_float(extension_atr),
    }


def timing_window_records(
    technical: pd.DataFrame,
    ema10: pd.Series,
    ema20: pd.Series,
    atr14: pd.Series,
    rows: int = 30,
) -> list[dict[str, Any]]:
    start = max(0, len(technical) - rows)
    records: list[dict[str, Any]] = []
    for position in range(start, len(technical)):
        index = technical.index[position]
        records.append(
            {
                "bar_date": index.date().isoformat(),
                "open": safe_float(technical["open"].iloc[position]),
                "high": safe_float(technical["high"].iloc[position]),
                "low": safe_float(technical["low"].iloc[position]),
                "close": safe_float(technical["close"].iloc[position]),
                "volume": safe_float(technical["volume"].iloc[position]),
                "ema10": safe_float(ema10.iloc[position]),
                "ema20": safe_float(ema20.iloc[position]),
                "atr14": safe_float(atr14.iloc[position]),
                "relative_volume_20d": _relative_volume_at(
                    technical["volume"], position
                ),
            }
        )
    return records


def calculate_metrics(ticker: str, result: dict[str, Any]) -> tuple[dict[str, Any], pd.Series]:
    frame = chart_frame(result)
    adj = frame["adjclose"]
    technical = normalized_technical_frame(frame)
    tech_close = technical["close"]
    latest = frame.iloc[-1]
    ma20 = safe_float(tech_close.rolling(20).mean().iloc[-1])
    ma50, ma50_5d_ago = slope_value(tech_close, 50, 5)
    ma100 = safe_float(tech_close.rolling(100).mean().iloc[-1])
    ma200 = safe_float(tech_close.rolling(200).mean().iloc[-1])
    ema10_series = tech_close.ewm(span=10, adjust=False).mean()
    ema20_series = tech_close.ewm(span=20, adjust=False).mean()
    atr14_values = atr_series(technical, 14)
    ema10 = safe_float(ema10_series.iloc[-1])
    ema20 = safe_float(ema20_series.iloc[-1])
    ema10_prev = safe_float(ema10_series.iloc[-2]) if len(ema10_series) >= 2 else None
    ema20_prev = safe_float(ema20_series.iloc[-2]) if len(ema20_series) >= 2 else None
    ema10_3d_ago = safe_float(ema10_series.iloc[-4]) if len(ema10_series) >= 4 else None
    ema20_3d_ago = safe_float(ema20_series.iloc[-4]) if len(ema20_series) >= 4 else None
    atr14 = safe_float(atr14_values.iloc[-1])
    close_raw = safe_float(latest["close"])
    atr14_pct = atr14 / close_raw if atr14 is not None and close_raw else None
    distance_from_ema20 = (
        close_raw / ema20 - 1 if close_raw is not None and ema20 not in (None, 0) else None
    )
    prior_20d_high = (
        safe_float(technical["high"].iloc[-21:-1].max())
        if len(technical) >= 21
        else None
    )
    prior_20d_close_high = (
        safe_float(tech_close.iloc[-21:-1].max()) if len(tech_close) >= 21 else None
    )
    low_20d = safe_float(technical["low"].tail(20).min()) if len(technical) >= 20 else None
    high_20d = safe_float(technical["high"].tail(20).max()) if len(technical) >= 20 else None
    calculation_check = indicator_validation(
        technical, ema10_series, ema20_series, atr14_values
    )
    timing_features = derive_timing_features(
        technical, ema10_series, ema20_series, atr14_values
    )
    # Convert to a timezone-naive calendar index before monthly grouping to avoid
    # silent timezone dropping warnings from pandas.
    monthly_periods = tech_close.index.tz_localize(None).to_period("M")
    monthly = tech_close.groupby(monthly_periods).last()
    ma10m = safe_float(monthly.tail(10).mean()) if len(monthly) >= 10 else None
    ema12 = tech_close.ewm(span=12, adjust=False).mean()
    ema26 = tech_close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    daily_returns = adj.pct_change().dropna()
    vol63 = (
        safe_float(daily_returns.tail(63).std(ddof=1) * math.sqrt(252))
        if len(daily_returns) >= 63
        else None
    )
    avg_volume20 = frame["volume"].iloc[-21:-1].mean() if len(frame) >= 21 else math.nan
    volume_ratio = safe_float(latest["volume"] / avg_volume20) if avg_volume20 else None
    high52 = adj.tail(252).max() if len(adj) else math.nan
    drawdown52 = safe_float(adj.iloc[-1] / high52 - 1) if finite(high52) else None
    provider = str(result.get("_provider") or "yahoo-chart")
    source = (
        "yfinance download (unofficial Yahoo Finance API wrapper)"
        if provider == "yfinance"
        else "Unofficial Yahoo Finance chart endpoint"
    )
    metrics = {
        "ticker": ticker,
        "bar_date": frame.index[-1].date().isoformat(),
        "open": safe_float(latest["open"]),
        "high": safe_float(latest["high"]),
        "low": safe_float(latest["low"]),
        "close": safe_float(latest["close"]),
        "close_prev": safe_float(frame["close"].iloc[-2]) if len(frame) >= 2 else None,
        "adjusted_close": safe_float(latest["adjclose"]),
        "volume": safe_float(latest["volume"]),
        "return_1d": return_over_rows(adj, 1),
        "return_1m": return_over_rows(adj, 21),
        "total_return_6m": return_over_rows(adj, 126),
        "total_return_12m": return_over_rows(adj, 252),
        "absolute_momentum_12m": return_over_rows(adj, 252),
        "ma20": ma20,
        "ema10": ema10,
        "ema20": ema20,
        "ema10_prev": ema10_prev,
        "ema20_prev": ema20_prev,
        "ema10_3d_ago": ema10_3d_ago,
        "ema20_3d_ago": ema20_3d_ago,
        "ema10_above_ema20": (
            bool(ema10 > ema20) if ema10 is not None and ema20 is not None else None
        ),
        "ema20_rising_3d": (
            bool(ema20 > ema20_3d_ago)
            if ema20 is not None and ema20_3d_ago is not None
            else None
        ),
        "atr14": atr14,
        "atr14_pct": safe_float(atr14_pct),
        "distance_from_ema20_fraction": safe_float(distance_from_ema20),
        "prior_20d_high": prior_20d_high,
        "prior_20d_close_high": prior_20d_close_high,
        "low_20d": low_20d,
        "high_20d": high_20d,
        "ma50": ma50,
        "ma50_5d_ago": ma50_5d_ago,
        "ma100": ma100,
        "ma200": ma200,
        "ma10m": ma10m,
        "rsi14": rsi(adj),
        "macd": safe_float(macd.iloc[-1]),
        "macd_signal": safe_float(signal.iloc[-1]),
        "volatility_63d_annualized": vol63,
        "volume_ratio_to_20d": volume_ratio,
        "drawdown_from_52w_high": drawdown52,
        "history_rows": int(len(frame)),
        "corporate_action_unresolved": recent_split(result, frame.index[-1]),
        "technical_price_basis": "split-adjusted OHLC rescaled to latest raw close",
        "quote_crosscheck": None,
        "timing_window": timing_window_records(
            technical, ema10_series, ema20_series, atr14_values
        ),
        "indicator_validation": calculation_check,
        "source": source,
        "source_provider": provider,
        "source_provider_version": result.get("_provider_version"),
        "source_request_mode": result.get("_request_mode"),
    }
    metrics.update(timing_features)
    return metrics, daily_returns.tail(63).rename(ticker)


def build_snapshot(
    state: dict[str, Any],
    tickers: list[str],
    *,
    provider: str = DEFAULT_MARKET_DATA_PROVIDER,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
) -> dict[str, Any]:
    session = urllib.request.build_opener()
    pacer = RequestPacer(request_delay_seconds)
    symbol_metrics: dict[str, Any] = {}
    returns: list[pd.Series] = []
    errors: list[str] = []
    for ticker in tickers:
        try:
            if provider == "yfinance":
                result = fetch_yfinance_chart(ticker, pacer=pacer)
            elif provider == "yahoo-chart":
                result = fetch_chart(session, ticker, pacer=pacer)
            else:
                raise SnapshotError(f"unsupported market-data provider: {provider}")
            metrics, series = calculate_metrics(ticker, result)
            symbol_metrics[ticker] = metrics
            returns.append(series)
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")

    bar_dates = sorted({row["bar_date"] for row in symbol_metrics.values()})
    latest_bar_date = max(bar_dates) if bar_dates else None
    now_et = datetime.now(UTC).astimezone(ET)
    complete = bool(latest_bar_date) and (
        latest_bar_date < now_et.date().isoformat()
        or (latest_bar_date == now_et.date().isoformat() and now_et.hour >= 17)
    )
    correlations: dict[str, Any] = {}
    if returns:
        joined = pd.concat(returns, axis=1, join="inner")
        if len(joined) >= 20:
            correlations = joined.corr().round(6).to_dict()

    holdings = state.get("holdings") or {}
    account_summary = build_account_summary(state, holdings, symbol_metrics)

    return {
        "schema_version": MARKET_SNAPSHOT_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "session": {
            "exchange_timezone": "America/New_York",
            "us_session_date": latest_bar_date,
            "expected_us_session_date": None,
            "is_trading_day": None,
            "regular_session_complete": complete,
            "is_early_close": None,
            "official_calendar_verified": False,
            "calendar_verification_status": "unverified",
            "calendar_source_type": None,
            "calendar_source": None,
            "calendar_verified_at_utc": None,
        },
        "account": account_summary,
        "symbols": symbol_metrics,
        "analytics": {"correlations_63d": correlations},
        "collection_provenance": {
            "provider": provider,
            "provider_version": (
                getattr(yf, "__version__", None) if provider == "yfinance" else None
            ),
            "provider_role": "unofficial research data",
            "request_mode": "sequential_single_ticker",
            "minimum_request_delay_seconds": request_delay_seconds,
            "threads": False,
            "prepost": False,
            "auto_adjust": False,
            "repair": False,
            "independent_completed_close_crosscheck_required": True,
        },
        "indicator_provenance": {
            "formula_version": INDICATOR_FORMULA_VERSION,
            "execution_price_basis": "unadjusted daily OHLC",
            "technical_price_basis": "split-adjusted OHLC rescaled to latest raw close",
            "ema_formula": "pandas ewm(span=N, adjust=False); alpha=2/(N+1)",
            "atr_formula": "Wilder ATR14 seeded with mean(TR1..TR14), then ATR=((prior*13)+TR)/14",
            "relative_volume_formula": "completed-session volume divided by mean volume of the prior 20 completed sessions",
            "timing_feature_version": TIMING_FEATURE_VERSION,
            "ema_direction_formula": "(EMA_t - EMA_t-3) / ATR14: rising > 0.10, falling < -0.10, otherwise neutral",
            "quote_crosscheck_tolerance": "max(USD 0.05, 0.10% of completed raw close)",
            "source_role": "unofficial yfinance/Yahoo research data requiring independent session and quote verification",
        },
        "errors": errors,
        "limitations": [
            "yfinance/Yahoo data are unofficial and require official calendar/session and independent close verification.",
            "Sequential requests are rate-limited to reduce temporary Yahoo blocking risk; the delay is not a service-level guarantee.",
            "Valuation, market breadth, credit spreads, rates, and earnings revisions require separate sourced checks.",
        ],
    }


def self_test() -> None:
    index = pd.date_range("2025-01-02", periods=300, freq="B", tz=ET)
    prices = pd.Series(np.linspace(80, 120, len(index)), index=index)
    assert return_over_rows(prices, 21) is not None
    assert rsi(prices) is not None
    current, old = slope_value(prices, 50, 5)
    assert current is not None and old is not None and current > old
    raw = pd.DataFrame(
        {
            "open": prices - 0.2,
            "high": prices + 0.5,
            "low": prices - 0.5,
            "close": prices,
            "volume": np.full(len(prices), 1_000_000),
            "adjclose": prices,
        },
        index=index,
    )
    technical = normalized_technical_frame(raw)
    ema10 = technical["close"].ewm(span=10, adjust=False).mean()
    ema20 = technical["close"].ewm(span=20, adjust=False).mean()
    atr14 = atr_series(technical)
    check = indicator_validation(technical, ema10, ema20, atr14)
    assert check["status"] == "passed"
    assert ema10.iloc[-1] > ema20.iloc[-1]
    assert safe_float(atr14.iloc[-1]) is not None
    features = derive_timing_features(technical, ema10, ema20, atr14)
    assert features["timing_feature_version"] == TIMING_FEATURE_VERSION
    assert features["ema10_direction_3d"] == "rising"
    assert MARKET_SNAPSHOT_SCHEMA_VERSION == "1.0"
    print("Self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--provider",
        choices=("yfinance", "yahoo-chart"),
        default=DEFAULT_MARKET_DATA_PROVIDER,
        help="Unofficial market-data collector. Live policy still requires an independent close cross-check.",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
        help="Minimum delay between external ticker requests; live collection requires at least 1.0 second.",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.state or not args.output:
        parser.error("--state and --output are required")
    if not finite(args.request_delay_seconds) or args.request_delay_seconds < 1.0:
        parser.error("--request-delay-seconds must be at least 1.0 for live collection")
    state = json.loads(args.state.read_text(encoding="utf-8"))
    tickers = args.tickers or sorted(set((state.get("holdings") or {}) | (state.get("baseline_target_shares") or {})))
    invalid = [ticker for ticker in tickers if not TICKER_RE.fullmatch(ticker)]
    if invalid:
        print(f"Invalid tickers: {invalid}", file=sys.stderr)
        return 2
    snapshot = build_snapshot(
        state,
        tickers,
        provider=args.provider,
        request_delay_seconds=args.request_delay_seconds,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    return 0 if not snapshot["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
