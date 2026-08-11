#!/usr/bin/env python3
"""Point-in-time SOXL EMA-policy backtest through 2026-08-04.

This script does not mutate strategy state and never places an order.  It
replays completed-close signals at the next regular-session open.  Nasdaq raw
OHLCV is used as the primary price history; Yahoo adjusted-close factors are
used only to normalize distributions/splits for technical indicators and are
cross-checked against Nasdaq raw closes.

Three studies are deliberately separated:

1. buy_hold_99: buy 99 shares at the first test-session open and hold;
2. active_staged_overlay_99: the active SOXL 24/24/24 reduction slots, with a
   hypothetical period-start anchor and every B review assumed approved at the
   following open (the 27-share residual remains untouched);
3. research_binary_long_cash: a non-active research completion of the watch
   entry rules and holding exit triggers, using full-notional long/cash trades.

The third study is not the live policy and must never be presented as such.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


NASDAQ_URL = "https://api.nasdaq.com/api/quote/{ticker}/historical"
NASDAQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_HEADERS = {"User-Agent": NASDAQ_HEADERS["User-Agent"]}

# Official NYSE full-day closures over the frozen data interval.  The list is
# transcribed from the NYSE 2024-2026 holiday calendars and includes the
# 2025-01-09 national day-of-mourning closure.  Weekends are handled separately.
NYSE_FULL_CLOSURES = {
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18",
    "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27",
    "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03",
}
NYSE_EARLY_CLOSES = {
    "2024-07-03", "2024-11-29", "2024-12-24",
    "2025-07-03", "2025-11-28", "2025-12-24",
    "2026-07-02",
}
NYSE_CALENDAR_URL = "https://www.nyse.com/markets/hours-calendars"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def expected_nyse_sessions(start: str, end: str) -> pd.DatetimeIndex:
    sessions = pd.date_range(start, end, freq="B")
    closures = pd.to_datetime(sorted(NYSE_FULL_CLOSURES))
    return sessions.difference(closures).sort_values()


def official_calendar_audit(
    frames: dict[str, pd.DataFrame], start: str, end: str
) -> dict[str, Any]:
    expected = expected_nyse_sessions(start, end)
    symbols: dict[str, Any] = {}
    all_pass = True
    for ticker, frame in frames.items():
        actual = pd.DatetimeIndex(frame.index)
        missing = expected.difference(actual)
        extra = actual.difference(expected)
        passed = missing.empty and extra.empty and actual[-1] == pd.Timestamp(end)
        all_pass = all_pass and passed
        symbols[ticker] = {
            "expected_session_count": int(len(expected)),
            "final_row_count": int(len(actual)),
            "missing_expected_sessions": [item.date().isoformat() for item in missing],
            "unexpected_sessions": [item.date().isoformat() for item in extra],
            "latest_session": actual[-1].date().isoformat(),
            "passed": passed,
        }
    return {
        "status": "passed" if all_pass else "failed",
        "official_source": NYSE_CALENDAR_URL,
        "interval": {"start": start, "end": end},
        "full_closures_applied": sorted(
            item for item in NYSE_FULL_CLOSURES if start <= item <= end
        ),
        "early_close_sessions_present": sorted(
            item for item in NYSE_EARLY_CLOSES if start <= item <= end
        ),
        "symbols": symbols,
    }


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_price(value: Any) -> float:
    text = str(value).replace("$", "").replace(",", "").strip()
    return float(text)


def fetch_nasdaq(ticker: str, start: str, end: str) -> pd.DataFrame:
    params = {
        "assetclass": "etf",
        "fromdate": start,
        "todate": end,
        "limit": 5000,
    }
    url = f"{NASDAQ_URL.format(ticker=ticker)}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=NASDAQ_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    status = payload.get("status") or {}
    if status.get("rCode") != 200 or not payload.get("data"):
        raise RuntimeError(f"Nasdaq history failed for {ticker}: {status}")
    rows = (((payload["data"] or {}).get("tradesTable") or {}).get("rows") or [])
    if not rows:
        raise RuntimeError(f"Nasdaq history is empty for {ticker}")
    records = []
    invalid_rows: list[dict[str, Any]] = []
    for row in rows:
        parsed_day: pd.Timestamp | None = None
        try:
            parsed_day = pd.Timestamp(datetime.strptime(row["date"], "%m/%d/%Y").date())
            record = {
                "date": parsed_day,
                "open": parse_price(row["open"]),
                "high": parse_price(row["high"]),
                "low": parse_price(row["low"]),
                "close": parse_price(row["close"]),
                "volume": parse_price(row["volume"]),
            }
        except (KeyError, TypeError, ValueError):
            # Nasdaq occasionally emits an N/A placeholder row.  It is not a
            # completed OHLCV bar and must not enter the signal history.
            invalid_rows.append(
                {
                    "date": parsed_day.date().isoformat() if parsed_day is not None else row.get("date"),
                    "reason": "unparseable_or_NA_OHLCV",
                }
            )
            continue
        records.append(record)
    frame = pd.DataFrame(records).set_index("date").sort_index()
    if frame.index.has_duplicates:
        raise RuntimeError(f"Nasdaq returned duplicate dates for {ticker}")
    frame.attrs["source_url"] = url
    frame.attrs["raw_response_rows"] = len(rows)
    frame.attrs["valid_parsed_rows"] = len(frame)
    frame.attrs["invalid_rows"] = invalid_rows
    frame.attrs["placeholder_volume_dates"] = [
        day.date().isoformat()
        for day in frame.index[np.isclose(frame["volume"].astype(float), 9_999_999.0)]
    ]
    return frame


def fetch_yahoo(ticker: str, start: str, end: str) -> tuple[pd.DataFrame, dict[str, Any], str]:
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    url = f"{YAHOO_URL.format(ticker=ticker)}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=YAHOO_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    chart = payload.get("chart") or {}
    if chart.get("error") or not chart.get("result"):
        raise RuntimeError(f"Yahoo history failed for {ticker}: {chart.get('error')}")
    result = chart["result"][0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators") or {}).get("quote", [{}])[0]
    adjusted = (result.get("indicators") or {}).get("adjclose", [{}])[0].get("adjclose")
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(timestamps, unit="s", utc=True).date,
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
            "adjclose": adjusted,
        }
    )
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date").sort_index()
    invalid_mask = frame[["open", "high", "low", "close", "volume", "adjclose"]].isna().any(axis=1)
    invalid_dates = [day.date().isoformat() for day in frame.index[invalid_mask]]
    frame = frame.loc[~invalid_mask].copy()
    if frame.index.has_duplicates:
        raise RuntimeError(f"Yahoo returned duplicate dates for {ticker}")
    frame.attrs["raw_response_rows"] = len(timestamps)
    frame.attrs["valid_parsed_rows"] = len(frame)
    frame.attrs["invalid_dates"] = invalid_dates
    return frame, result.get("events") or {}, url


def yahoo_dividends(events: dict[str, Any]) -> dict[pd.Timestamp, float]:
    result: dict[pd.Timestamp, float] = {}
    for item in (events.get("dividends") or {}).values():
        day = pd.Timestamp(datetime.fromtimestamp(int(item["date"]), tz=timezone.utc).date())
        result[day] = result.get(day, 0.0) + float(item["amount"])
    return result


def combined_history(
    ticker: str, start: str, end: str
) -> tuple[pd.DataFrame, dict[str, Any]]:
    official = fetch_nasdaq(ticker, start, end)
    yahoo, events, yahoo_url = fetch_yahoo(ticker, start, end)
    expected = expected_nyse_sessions(start, end)
    common = official.index.intersection(yahoo.index).intersection(expected)
    joined = official.loc[common].join(
        yahoo.loc[common, ["close", "adjclose"]], how="inner", rsuffix="_yahoo"
    )
    joined["close_difference"] = (joined["close"] - joined["close_yahoo"]).abs()
    joined["close_tolerance"] = np.maximum(0.05, joined["close"] * 0.001)
    failures = joined[joined["close_difference"] > joined["close_tolerance"]]
    if not failures.empty:
        raise RuntimeError(
            f"{ticker}: {len(failures)} Nasdaq/Yahoo close mismatches above tolerance"
        )
    missing_yahoo = expected.difference(yahoo.index)
    if not missing_yahoo.empty:
        raise RuntimeError(
            f"{ticker}: Yahoo is missing expected sessions: "
            + ", ".join(day.date().isoformat() for day in missing_yahoo)
        )

    records: list[dict[str, Any]] = []
    fallback_sessions: list[str] = []
    volume_corrected_sessions: list[str] = []
    for day in expected:
        yahoo_row = yahoo.loc[day]
        factor = float(yahoo_row["adjclose"]) / float(yahoo_row["close"])
        if not math.isfinite(factor) or factor <= 0:
            raise RuntimeError(f"{ticker}: invalid Yahoo adjustment factor on {day.date()}")
        if day in official.index:
            source_row = official.loc[day]
            ohlc_source = "Nasdaq"
            volume = float(source_row["volume"])
            volume_source = "Nasdaq"
            if math.isclose(volume, 9_999_999.0, rel_tol=0.0, abs_tol=0.01):
                volume = float(yahoo_row["volume"])
                volume_source = "Yahoo_fallback_for_Nasdaq_placeholder_9999999"
                volume_corrected_sessions.append(day.date().isoformat())
        else:
            source_row = yahoo_row
            ohlc_source = "Yahoo_fallback_for_missing_or_NA_Nasdaq_bar"
            volume = float(yahoo_row["volume"])
            volume_source = "Yahoo_fallback_for_missing_or_NA_Nasdaq_bar"
            fallback_sessions.append(day.date().isoformat())
        values = {
            "open": float(source_row["open"]),
            "high": float(source_row["high"]),
            "low": float(source_row["low"]),
            "close": float(source_row["close"]),
            "volume": volume,
        }
        if not all(math.isfinite(value) and value > 0 for value in values.values()):
            raise RuntimeError(f"{ticker}: invalid repaired OHLCV on {day.date()}")
        records.append(
            {
                "date": day,
                **values,
                "adjclose": values["close"] * factor,
                "ohlc_source": ohlc_source,
                "volume_source": volume_source,
                "adjustment_factor_source": "Yahoo_adjclose_divided_by_Yahoo_raw_close",
                "is_early_close": day.date().isoformat() in NYSE_EARLY_CLOSES,
            }
        )
    frame = pd.DataFrame(records).set_index("date").sort_index()
    if len(frame) < 252:
        raise RuntimeError(f"{ticker}: only {len(frame)} calendar-complete rows")
    frame.attrs["nasdaq_url"] = official.attrs["source_url"]
    frame.attrs["yahoo_url"] = yahoo_url
    quality = {
        "nasdaq_response_rows": int(official.attrs["raw_response_rows"]),
        "nasdaq_valid_parsed_rows": int(official.attrs["valid_parsed_rows"]),
        "nasdaq_invalid_rows": official.attrs["invalid_rows"],
        "nasdaq_placeholder_volume_dates": official.attrs["placeholder_volume_dates"],
        "yahoo_response_rows": int(yahoo.attrs["raw_response_rows"]),
        "yahoo_valid_parsed_rows": int(yahoo.attrs["valid_parsed_rows"]),
        "yahoo_invalid_dates": yahoo.attrs["invalid_dates"],
        "raw_common_valid_rows_before_repair": int(len(common)),
        "calendar_expected_rows": int(len(expected)),
        "final_rows_after_repair": int(len(frame)),
        "nasdaq_missing_expected_sessions": [
            day.date().isoformat() for day in expected.difference(official.index)
        ],
        "yahoo_missing_expected_sessions": [
            day.date().isoformat() for day in expected.difference(yahoo.index)
        ],
        "fallback_sessions": fallback_sessions,
        "volume_corrected_sessions": volume_corrected_sessions,
        "first_date": frame.index[0].date().isoformat(),
        "last_date": frame.index[-1].date().isoformat(),
        "maximum_close_difference_usd": float(joined["close_difference"].max()) if not joined.empty else None,
        "mismatch_count_above_tolerance": int(len(failures)),
        "nasdaq_url": official.attrs["source_url"],
        "yahoo_url": yahoo_url,
        "events": events,
    }
    return frame, quality


def technical_components(frame: pd.DataFrame, builder: Any):
    technical = builder.normalized_technical_frame(frame)
    ema10 = technical["close"].ewm(span=10, adjust=False).mean()
    ema20 = technical["close"].ewm(span=20, adjust=False).mean()
    atr14 = builder.atr_series(technical, 14)
    return technical, ema10, ema20, atr14


def point_in_time_row(
    raw_frame: pd.DataFrame,
    technical: pd.DataFrame,
    ema10: pd.Series,
    ema20: pd.Series,
    atr14: pd.Series,
    position: int,
    builder: Any,
) -> dict[str, Any]:
    if position < 252:
        raise ValueError("policy warm-up requires at least 252 completed bars")
    # The live builder normalizes adjusted history to the raw close of the
    # signal date.  The full-history technical frame is normalized to the
    # final backtest date, so rescale every causal series by one constant here.
    # This keeps the signal-date raw price, EMA, ATR, and cost boundary on the
    # same executable basis without changing any scale-invariant signal flag.
    raw_close = float(raw_frame["close"].iloc[position])
    scale = raw_close / float(technical["close"].iloc[position])
    partial = technical.iloc[: position + 1].copy()
    for column in ("open", "high", "low", "close"):
        partial[column] = partial[column] * scale
    e10 = ema10.iloc[: position + 1] * scale
    e20 = ema20.iloc[: position + 1] * scale
    atr = atr14.iloc[: position + 1] * scale
    features = builder.derive_timing_features(partial, e10, e20, atr)
    row: dict[str, Any] = {
        "close": raw_close,
        "close_prev": float(partial["close"].iloc[-2]),
        "ema10": float(e10.iloc[-1]),
        "ema20": float(e20.iloc[-1]),
        "ema10_prev": float(e10.iloc[-2]),
        "ema20_prev": float(e20.iloc[-2]),
        "ema10_above_ema20": bool(e10.iloc[-1] > e20.iloc[-1]),
        "atr14": float(atr.iloc[-1]),
        "atr14_prev": float(atr.iloc[-2]),
        "ma50": float(partial["close"].rolling(50).mean().iloc[-1]),
        "ma50_5d_ago": float(partial["close"].rolling(50).mean().iloc[-6]),
        "prior_20d_high": float(partial["high"].iloc[-21:-1].max()),
    }
    row.update(features)
    return row


def metric_summary(
    name: str,
    initial_capital: float,
    values: list[tuple[pd.Timestamp, float]],
    trades: list[dict[str, Any]],
    costs_usd: float,
    exposure: list[float],
) -> dict[str, Any]:
    series = pd.Series({day: value for day, value in values}).sort_index()
    augmented = pd.concat(
        [pd.Series([initial_capital], index=[series.index[0] - pd.Timedelta(days=1)]), series]
    )
    returns = augmented.pct_change().dropna()
    drawdown = augmented / augmented.cummax() - 1.0
    elapsed_days = max(1, (series.index[-1] - series.index[0]).days + 1)
    total_return = float(series.iloc[-1] / initial_capital - 1.0)
    cagr = float((series.iloc[-1] / initial_capital) ** (365.25 / elapsed_days) - 1.0)
    vol = float(returns.std(ddof=1) * math.sqrt(252)) if len(returns) > 1 else None
    sharpe = (
        float(returns.mean() / returns.std(ddof=1) * math.sqrt(252))
        if len(returns) > 1 and returns.std(ddof=1) > 0
        else None
    )
    # Standard zero-target downside deviation: include every observation in
    # the denominator and replace positive returns with zero.  This differs
    # from the non-standard deviation of only negative-return observations.
    downside_shortfall = np.minimum(returns.to_numpy(dtype=float), 0.0)
    downside_deviation_daily = float(np.sqrt(np.mean(np.square(downside_shortfall))))
    sortino = (
        float(returns.mean() / downside_deviation_daily * math.sqrt(252))
        if downside_deviation_daily > 0
        else None
    )
    turnover = sum(abs(float(item["notional_usd"])) for item in trades) / initial_capital
    return {
        "name": name,
        "start_value_usd": initial_capital,
        "end_value_usd": float(series.iloc[-1]),
        "total_return": total_return,
        "cagr": cagr,
        "annualized_volatility": vol,
        "maximum_drawdown": float(drawdown.min()),
        "sharpe_rf0": sharpe,
        "downside_deviation_annualized_target0": downside_deviation_daily * math.sqrt(252),
        "sortino_target0": sortino,
        "worst_day": float(returns.min()),
        "trade_count": len(trades),
        "turnover_multiple": float(turnover),
        "estimated_cost_usd": float(costs_usd),
        "average_equity_exposure": float(np.mean(exposure)) if exposure else None,
    }


@dataclass
class Portfolio:
    cash: float
    shares: float = 0.0
    average_cost: float | None = None
    completed_slots: list[str] = field(default_factory=list)
    pending: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = field(default_factory=list)
    costs: float = 0.0


def execute_buy(portfolio: Portfolio, day: pd.Timestamp, open_price: float, cost_rate: float):
    execution = open_price * (1.0 + cost_rate)
    shares = portfolio.cash / execution
    notional = shares * open_price
    portfolio.costs += notional * cost_rate
    portfolio.cash = 0.0
    portfolio.shares = shares
    portfolio.average_cost = execution
    portfolio.trades.append(
        {
            "date": day.date().isoformat(),
            "side": "buy",
            "shares": shares,
            "open_price": open_price,
            "execution_price": execution,
            "notional_usd": notional,
            "reason": portfolio.pending.get("reason") if portfolio.pending else "initial",
        }
    )


def execute_sell(
    portfolio: Portfolio,
    day: pd.Timestamp,
    open_price: float,
    quantity: float,
    cost_rate: float,
):
    quantity = min(quantity, portfolio.shares)
    execution = open_price * (1.0 - cost_rate)
    notional = quantity * open_price
    portfolio.costs += notional * cost_rate
    portfolio.cash += quantity * execution
    portfolio.shares -= quantity
    portfolio.trades.append(
        {
            "date": day.date().isoformat(),
            "side": "sell",
            "shares": quantity,
            "open_price": open_price,
            "execution_price": execution,
            "notional_usd": notional,
            "reason": portfolio.pending.get("reason") if portfolio.pending else None,
            "slot_id": portfolio.pending.get("slot_id") if portfolio.pending else None,
        }
    )


def run_buy_hold(
    frame: pd.DataFrame,
    dividends: dict[pd.Timestamp, float],
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_rate: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    test = frame.loc[start:end]
    first_open = float(test["open"].iloc[0])
    initial = 99.0 * first_open * (1.0 + cost_rate)
    portfolio = Portfolio(cash=initial)
    portfolio.pending = {"reason": "period_start_buy"}
    execute_buy(portfolio, test.index[0], first_open, cost_rate)
    portfolio.pending = None
    values: list[tuple[pd.Timestamp, float]] = []
    exposures: list[float] = []
    for day, bar in test.iterrows():
        if day in dividends:
            portfolio.cash += portfolio.shares * dividends[day]
        value = portfolio.cash + portfolio.shares * float(bar["close"])
        values.append((day, value))
        exposures.append(portfolio.shares * float(bar["close"]) / value)
    return (
        metric_summary("buy_hold_99", initial, values, portfolio.trades, portfolio.costs, exposures),
        portfolio.trades,
    )


def run_staged_overlay(
    frame: pd.DataFrame,
    proxy_frame: pd.DataFrame,
    technical: pd.DataFrame,
    proxy_technical: pd.DataFrame,
    components: tuple[pd.Series, pd.Series, pd.Series],
    proxy_components: tuple[pd.Series, pd.Series, pd.Series],
    dividends: dict[pd.Timestamp, float],
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_rate: float,
    state_template: dict[str, Any],
    policy: dict[str, Any],
    builder: Any,
    timing: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    test = frame.loc[start:end]
    first_open = float(test["open"].iloc[0])
    initial = 99.0 * first_open * (1.0 + cost_rate)
    portfolio = Portfolio(cash=initial)
    portfolio.pending = {"reason": "period_start_buy"}
    execute_buy(portfolio, test.index[0], first_open, cost_rate)
    portfolio.pending = None
    state = copy.deepcopy(state_template)
    state["holdings"]["SOXL"] = 99
    state["average_cost_usd"]["SOXL"] = portfolio.average_cost
    state["timing_plan"]["positions"]["SOXL"]["completed_tranche_ids"] = []
    hard_boundary = float(portfolio.average_cost) * 0.8
    e10, e20, atr = components
    pe10, pe20, patr = proxy_components
    values: list[tuple[pd.Timestamp, float]] = []
    exposures: list[float] = []
    alerts: list[dict[str, Any]] = []
    for day, bar in test.iterrows():
        shares_before_open = portfolio.shares
        if day in dividends:
            portfolio.cash += shares_before_open * dividends[day]
        if portfolio.pending:
            slot_id = portfolio.pending["slot_id"]
            quantity = float(portfolio.pending["quantity"])
            execute_sell(portfolio, day, float(bar["open"]), quantity, cost_rate)
            portfolio.completed_slots.append(slot_id)
            state["holdings"]["SOXL"] = int(round(portfolio.shares))
            state["timing_plan"]["positions"]["SOXL"]["completed_tranche_ids"] = list(
                portfolio.completed_slots
            )
            portfolio.pending = None
        value = portfolio.cash + portfolio.shares * float(bar["close"])
        values.append((day, value))
        exposures.append(portfolio.shares * float(bar["close"]) / value if value else 0.0)
        if bool(bar["is_early_close"]):
            alerts.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "F",
                    "trigger": None,
                    "quantity": None,
                    "suppressed_reason": "unadjusted early-close volume is rejected by the active snapshot validator",
                }
            )
            continue
        location = technical.index.get_loc(day)
        proxy_location = proxy_technical.index.get_loc(day)
        row = point_in_time_row(frame, technical, e10, e20, atr, location, builder)
        proxy_row = point_in_time_row(
            proxy_frame, proxy_technical, pe10, pe20, patr, proxy_location, builder
        )
        hard_risk = row["close"] <= hard_boundary
        candidate, warnings = timing.evaluate_holding_timing(
            state=state,
            policy=policy,
            symbol="SOXL",
            row=row,
            proxy_row=proxy_row,
            hard_boundary=hard_boundary,
            rules_hash="backtest-2026-08-05",
            suppress_for_hard_risk=hard_risk,
        )
        if hard_risk:
            alerts.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "D",
                    "trigger": "hard_maximum_loss_review",
                    "quantity": None,
                    "note": "active policy has no deterministic quantity authority",
                }
            )
        if candidate and candidate.get("grade") == "B" and portfolio.pending is None:
            portfolio.pending = {
                "reason": candidate["trigger_path"],
                "slot_id": candidate["tranche_id"],
                "quantity": candidate["quantity"],
            }
            alerts.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "B",
                    "trigger": candidate["trigger_path"],
                    "quantity": candidate["quantity"],
                    "slot_id": candidate["tranche_id"],
                    "warnings": warnings,
                }
            )
    return (
        metric_summary(
            "active_staged_overlay_99",
            initial,
            values,
            portfolio.trades,
            portfolio.costs,
            exposures,
        ),
        portfolio.trades,
        alerts,
    )


def run_binary_research(
    frame: pd.DataFrame,
    proxy_frame: pd.DataFrame,
    technical: pd.DataFrame,
    proxy_technical: pd.DataFrame,
    components: tuple[pd.Series, pd.Series, pd.Series],
    proxy_components: tuple[pd.Series, pd.Series, pd.Series],
    dividends: dict[pd.Timestamp, float],
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_rate: float,
    builder: Any,
    timing: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    test = frame.loc[start:end]
    initial = 99.0 * float(test["open"].iloc[0]) * (1.0 + cost_rate)
    portfolio = Portfolio(cash=initial)
    values: list[tuple[pd.Timestamp, float]] = []
    exposures: list[float] = []
    e10, e20, atr = components
    pe10, pe20, patr = proxy_components
    for day, bar in test.iterrows():
        shares_before_open = portfolio.shares
        if day in dividends:
            portfolio.cash += shares_before_open * dividends[day]
        if portfolio.pending:
            if portfolio.pending["side"] == "buy":
                execute_buy(portfolio, day, float(bar["open"]), cost_rate)
            else:
                execute_sell(
                    portfolio, day, float(bar["open"]), portfolio.shares, cost_rate
                )
                portfolio.average_cost = None
            portfolio.pending = None
        value = portfolio.cash + portfolio.shares * float(bar["close"])
        values.append((day, value))
        exposures.append(portfolio.shares * float(bar["close"]) / value if value else 0.0)
        if bool(bar["is_early_close"]):
            continue
        location = technical.index.get_loc(day)
        proxy_location = proxy_technical.index.get_loc(day)
        row = point_in_time_row(frame, technical, e10, e20, atr, location, builder)
        proxy_row = point_in_time_row(
            proxy_frame, proxy_technical, pe10, pe20, patr, proxy_location, builder
        )
        if portfolio.shares <= 1e-12:
            setup = timing.watch_setup(row, leveraged=True, proxy_row=proxy_row)
            if setup.get("technical_setup_detected"):
                portfolio.pending = {"side": "buy", "reason": setup["setup"]}
        else:
            assert portfolio.average_cost is not None
            hard_boundary = portfolio.average_cost * 0.8
            states, _, _ = timing._trigger_states(
                "SOXL", row, proxy_row, portfolio.average_cost, hard_boundary
            )
            trigger = None
            if row["close"] <= hard_boundary:
                trigger = "research_full_exit_on_hard_boundary"
            else:
                for name in (
                    "technical_stop",
                    "weakness_20ema",
                    "weakness_failed_reclaim",
                    "weakness_10ema",
                    "take_profit_rejection",
                ):
                    if states.get(name):
                        trigger = name
                        break
            if trigger:
                portfolio.pending = {"side": "sell", "reason": trigger}
    return (
        metric_summary(
            "research_binary_long_cash_NOT_ACTIVE",
            initial,
            values,
            portfolio.trades,
            portfolio.costs,
            exposures,
        ),
        portfolio.trades,
    )


def run_staged_diagnostic(
    *,
    name: str,
    weakness10_watch_only: bool,
    frame: pd.DataFrame,
    proxy_frame: pd.DataFrame,
    technical: pd.DataFrame,
    proxy_technical: pd.DataFrame,
    components: tuple[pd.Series, pd.Series, pd.Series],
    proxy_components: tuple[pd.Series, pd.Series, pd.Series],
    dividends: dict[pd.Timestamp, float],
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_rate: float,
    policy: dict[str, Any],
    builder: Any,
    timing: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Non-active sensitivity with a weakness reset and 3-session cooldown.

    After a weakness-trigger fill, another weakness tranche requires both SOXL
    and SOXX to have closed back above the EMA associated with the filled
    trigger.  All B-grade reductions, including technical-stop reviews, require
    three subsequently completed sessions between fills.  A D-grade hard-risk
    review remains unsized and is never suppressed by this diagnostic.
    """

    test = frame.loc[start:end]
    first_open = float(test["open"].iloc[0])
    initial = 99.0 * first_open * (1.0 + cost_rate)
    portfolio = Portfolio(cash=initial)
    portfolio.pending = {"reason": "period_start_buy"}
    execute_buy(portfolio, test.index[0], first_open, cost_rate)
    portfolio.pending = None
    hard_boundary = float(portfolio.average_cost) * 0.8
    e10, e20, atr = components
    pe10, pe20, patr = proxy_components
    slots = policy["holding_timing_rules"]["positions"]["SOXL"]["slots"]
    completed: list[str] = []
    last_fill_position: int | None = None
    reset_required_ema: int | None = None
    values: list[tuple[pd.Timestamp, float]] = []
    exposures: list[float] = []
    events: list[dict[str, Any]] = []
    for test_position, (day, bar) in enumerate(test.iterrows()):
        shares_before_open = portfolio.shares
        if day in dividends:
            portfolio.cash += shares_before_open * dividends[day]
        if portfolio.pending:
            pending = dict(portfolio.pending)
            execute_sell(
                portfolio,
                day,
                float(bar["open"]),
                float(pending["quantity"]),
                cost_rate,
            )
            completed.append(pending["slot_id"])
            last_fill_position = test_position
            if pending["reason"] == "weakness_10ema":
                reset_required_ema = 10
            elif pending["reason"] in ("weakness_20ema", "weakness_failed_reclaim"):
                reset_required_ema = 20
            portfolio.pending = None
        value = portfolio.cash + portfolio.shares * float(bar["close"])
        values.append((day, value))
        exposures.append(portfolio.shares * float(bar["close"]) / value if value else 0.0)
        if bool(bar["is_early_close"]):
            events.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "F",
                    "trigger": None,
                    "quantity": None,
                    "suppressed_reason": "unadjusted early-close volume is rejected by the active snapshot validator",
                }
            )
            continue
        location = technical.index.get_loc(day)
        proxy_location = proxy_technical.index.get_loc(day)
        row = point_in_time_row(
            frame, technical, e10, e20, atr, location, builder
        )
        proxy_row = point_in_time_row(
            proxy_frame, proxy_technical, pe10, pe20, patr, proxy_location, builder
        )

        if reset_required_ema is not None:
            key = f"ema{reset_required_ema}"
            recovered = bool(
                float(row["close"]) > float(row[key])
                and float(proxy_row["close"]) > float(proxy_row[key])
            )
            if recovered:
                events.append(
                    {
                        "signal_date": day.date().isoformat(),
                        "event": "weakness_reset_rearmed",
                        "ema": reset_required_ema,
                    }
                )
                reset_required_ema = None

        hard_risk = row["close"] <= hard_boundary
        if hard_risk:
            events.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "D",
                    "trigger": "hard_maximum_loss_review",
                    "quantity": None,
                    "note": "active policy has no deterministic quantity authority",
                }
            )
            continue
        next_slot = next((slot for slot in slots if slot["id"] not in completed), None)
        if not next_slot or not next_slot.get("allowed_triggers"):
            continue
        states, _, _ = timing._trigger_states(
            "SOXL", row, proxy_row, float(portfolio.average_cost), hard_boundary
        )
        if weakness10_watch_only and states.get("weakness_10ema"):
            events.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "B-watch",
                    "trigger": "weakness_10ema",
                    "quantity": None,
                    "suppressed_reason": "diagnostic weakness_10ema watch-only",
                }
            )
        allowed = set(next_slot.get("allowed_triggers") or [])
        trigger = next(
            (
                item
                for item in timing.TRIGGER_PRIORITY
                if item in allowed
                and states.get(item)
                and not (weakness10_watch_only and item == "weakness_10ema")
            ),
            None,
        )
        if not trigger:
            continue
        cooldown_complete = bool(
            last_fill_position is None or test_position - last_fill_position >= 3
        )
        if not cooldown_complete:
            events.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "B-suppressed",
                    "trigger": trigger,
                    "quantity": None,
                    "suppressed_reason": "three-completed-session cooldown",
                }
            )
            continue
        if trigger in ("weakness_10ema", "weakness_20ema", "weakness_failed_reclaim") and reset_required_ema is not None:
            events.append(
                {
                    "signal_date": day.date().isoformat(),
                    "grade": "B-suppressed",
                    "trigger": trigger,
                    "quantity": None,
                    "suppressed_reason": f"recovery above EMA{reset_required_ema} not yet observed in SOXL and SOXX",
                }
            )
            continue
        portfolio.pending = {
            "reason": trigger,
            "slot_id": next_slot["id"],
            "quantity": int(next_slot["quantity"]),
        }
        events.append(
            {
                "signal_date": day.date().isoformat(),
                "grade": "B-diagnostic",
                "trigger": trigger,
                "quantity": int(next_slot["quantity"]),
                "slot_id": next_slot["id"],
            }
        )
    return (
        metric_summary(
            name,
            initial,
            values,
            portfolio.trades,
            portfolio.costs,
            exposures,
        ),
        portfolio.trades,
        events,
    )


def soxx_buy_hold_total_return(
    frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, builder: Any
) -> float:
    # Use one internally consistent adjusted price basis for both endpoints.
    # The normalized frame remains on the latest raw-close scale, but its
    # returns are identical to adjusted-total-return price relatives.
    test = builder.normalized_technical_frame(frame).loc[start:end]
    return float(test["close"].iloc[-1] / test["open"].iloc[0] - 1.0)


def causality_audit(
    frame: pd.DataFrame,
    builder: Any,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, Any]:
    """Compare full-history causal calculations with independently truncated runs."""

    technical, ema10, ema20, atr14 = technical_components(frame, builder)
    candidates = list(frame.loc[start:end].index[::40])
    if end not in candidates:
        candidates.append(end)
    numeric_keys = (
        "close",
        "ema10",
        "ema20",
        "atr14",
        "prior_20d_high",
        "extension_above_ema20_atr",
    )
    flag_keys = (
        "ema10_direction_3d",
        "ema20_direction_3d",
        "ema10_reclaim_confirmed",
        "ema20_reclaim_confirmed",
        "ema20_failed_reclaim_confirmed",
        "decisive_breach_ema20",
        "breakout_acceptance_confirmed",
        "failed_higher_high_confirmed",
        "overheat_rejection_confirmed",
    )
    maximum_difference = 0.0
    mismatches: list[str] = []
    for day in candidates:
        position = frame.index.get_loc(day)
        full_row = point_in_time_row(
            frame, technical, ema10, ema20, atr14, position, builder
        )
        truncated = frame.loc[:day]
        tt, te10, te20, tatr = technical_components(truncated, builder)
        short_row = point_in_time_row(
            truncated, tt, te10, te20, tatr, len(truncated) - 1, builder
        )
        for key in numeric_keys:
            difference = abs(float(full_row[key]) - float(short_row[key]))
            maximum_difference = max(maximum_difference, difference)
            tolerance = max(1e-8, abs(float(short_row[key])) * 1e-10)
            if difference > tolerance:
                mismatches.append(f"{day.date()}:{key}:{difference}")
        for key in flag_keys:
            if full_row.get(key) != short_row.get(key):
                mismatches.append(f"{day.date()}:{key}:flag_mismatch")
    return {
        "status": "passed" if not mismatches else "failed",
        "checked_dates": [item.date().isoformat() for item in candidates],
        "maximum_numeric_difference": maximum_difference,
        "mismatches": mismatches,
        "method": "full-history causal series versus independently truncated history",
    }


def run(cost_bps: float, args: argparse.Namespace, modules: dict[str, Any]):
    builder = modules["builder"]
    timing = modules["timing"]
    policy = modules["policy"]
    state = modules["state"]
    soxl = modules["soxl"]
    soxx = modules["soxx"]
    divs = modules["soxl_dividends"]
    t, e10, e20, atr = technical_components(soxl, builder)
    pt, pe10, pe20, patr = technical_components(soxx, builder)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    cost_rate = cost_bps / 10_000.0
    bh, bh_trades = run_buy_hold(soxl, divs, start, end, cost_rate)
    staged, staged_trades, alerts = run_staged_overlay(
        soxl,
        soxx,
        t,
        pt,
        (e10, e20, atr),
        (pe10, pe20, patr),
        divs,
        start,
        end,
        cost_rate,
        state,
        policy,
        builder,
        timing,
    )
    diagnostic_a, diagnostic_a_trades, diagnostic_a_events = run_staged_diagnostic(
        name="diagnostic_A_reset_3session_cooldown_NOT_ACTIVE",
        weakness10_watch_only=False,
        frame=soxl,
        proxy_frame=soxx,
        technical=t,
        proxy_technical=pt,
        components=(e10, e20, atr),
        proxy_components=(pe10, pe20, patr),
        dividends=divs,
        start=start,
        end=end,
        cost_rate=cost_rate,
        policy=policy,
        builder=builder,
        timing=timing,
    )
    diagnostic_b, diagnostic_b_trades, diagnostic_b_events = run_staged_diagnostic(
        name="diagnostic_B_reset_cooldown_weakness10_watch_NOT_ACTIVE",
        weakness10_watch_only=True,
        frame=soxl,
        proxy_frame=soxx,
        technical=t,
        proxy_technical=pt,
        components=(e10, e20, atr),
        proxy_components=(pe10, pe20, patr),
        dividends=divs,
        start=start,
        end=end,
        cost_rate=cost_rate,
        policy=policy,
        builder=builder,
        timing=timing,
    )
    binary, binary_trades = run_binary_research(
        soxl,
        soxx,
        t,
        pt,
        (e10, e20, atr),
        (pe10, pe20, patr),
        divs,
        start,
        end,
        cost_rate,
        builder,
        timing,
    )
    return {
        "cost_bps_per_fill": cost_bps,
        "metrics": [bh, staged, diagnostic_a, diagnostic_b, binary],
        "trades": {
            "buy_hold_99": bh_trades,
            "active_staged_overlay_99": staged_trades,
            "diagnostic_A_reset_3session_cooldown_NOT_ACTIVE": diagnostic_a_trades,
            "diagnostic_B_reset_cooldown_weakness10_watch_NOT_ACTIVE": diagnostic_b_trades,
            "research_binary_long_cash_NOT_ACTIVE": binary_trades,
        },
        "staged_alerts": alerts,
        "diagnostic_events": {
            "A_reset_3session_cooldown_NOT_ACTIVE": diagnostic_a_events,
            "B_reset_cooldown_weakness10_watch_NOT_ACTIVE": diagnostic_b_events,
        },
        "soxx_buy_hold_total_return_before_cost": soxx_buy_hold_total_return(
            soxx, start, end, builder
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2025-08-05")
    parser.add_argument("--end", default="2026-08-04")
    parser.add_argument("--warmup-start", default="2024-06-01")
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    system = root / "stock-strategy-system"
    scripts = system / "skill-staging" / "manage-us-stock-strategy" / "scripts"
    builder = load_module("snapshot_builder", scripts / "build_market_snapshot.py")
    timing = load_module("timing_engine", scripts / "timing_engine.py")
    policy = json.loads((system / "alert_policy.json").read_text(encoding="utf-8"))
    state = json.loads((system / "portfolio_state.json").read_text(encoding="utf-8"))
    if policy["holding_timing_rules"]["policy_version"] != "2026-08-05-ema-timing-v2":
        raise RuntimeError("unexpected active timing-policy version")
    soxl, q_soxl = combined_history("SOXL", args.warmup_start, args.end)
    soxx, q_soxx = combined_history("SOXX", args.warmup_start, args.end)
    calendar_audit = official_calendar_audit(
        {"SOXL": soxl, "SOXX": soxx}, args.warmup_start, args.end
    )
    if calendar_audit["status"] != "passed":
        raise RuntimeError(f"official-session audit failed: {calendar_audit}")
    if not soxl.index.equals(soxx.index):
        raise RuntimeError("SOXL and SOXX final calendar-complete indexes differ")
    soxl_events = q_soxl["events"]
    modules = {
        "builder": builder,
        "timing": timing,
        "policy": policy,
        "state": state,
        "soxl": soxl,
        "soxx": soxx,
        "soxl_dividends": yahoo_dividends(soxl_events),
    }
    base = run(args.cost_bps, args, modules)
    sensitivity = {}
    for cost in (0.0, 5.0, 10.0, 20.0):
        result = base if cost == args.cost_bps else run(cost, args, modules)
        sensitivity[str(cost)] = {
            item["name"]: item["total_return"] for item in result["metrics"]
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"soxl_ema_policy_{args.start}_{args.end}"
    soxl_technical, _, _, _ = technical_components(soxl, builder)
    soxx_technical, _, _, _ = technical_components(soxx, builder)
    trades = []
    for strategy, items in base["trades"].items():
        for item in items:
            trades.append({"strategy": strategy, **item})
    artifact_text = {
        f"{stem}_SOXL_input.csv": soxl.to_csv(index_label="date"),
        f"{stem}_SOXX_input.csv": soxx.to_csv(index_label="date"),
        f"{stem}_SOXL_adjusted_OHLCV.csv": soxl_technical.to_csv(index_label="date"),
        f"{stem}_SOXX_adjusted_OHLCV.csv": soxx_technical.to_csv(index_label="date"),
        f"{stem}_trades.csv": pd.DataFrame(trades).to_csv(index=False),
    }
    generated_artifact_hashes = {
        name: sha256_bytes(value.encode("utf-8")) for name, value in artifact_text.items()
    }
    source_hashes = {
        "alert_policy.json": sha256_bytes((system / "alert_policy.json").read_bytes()),
        "portfolio_state.json": sha256_bytes((system / "portfolio_state.json").read_bytes()),
        "timing_engine.py": sha256_bytes((scripts / "timing_engine.py").read_bytes()),
        "build_market_snapshot.py": sha256_bytes(
            (scripts / "build_market_snapshot.py").read_bytes()
        ),
        Path(__file__).name: sha256_bytes(Path(__file__).read_bytes()),
    }
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_period": {"start": args.start, "end": args.end},
        "latest_completed_session_assumption": args.end,
        "validation_classification": {
            "status": "in_sample_mechanical_replay_only",
            "policy_formed_on": "2026-08-05",
            "test_ends": args.end,
            "predictive_validation": False,
            "reason": "The 2026-08-05 policy is replayed mechanically over an already observable period; no untouched holdout or walk-forward validation is available.",
        },
        "official_calendar_audit": calendar_audit,
        "policy_version": policy["holding_timing_rules"]["policy_version"],
        "formula_version": policy["holding_timing_rules"]["formula_version"],
        "timing_feature_version": policy["holding_timing_rules"]["timing_feature_version"],
        "benchmark_identity": {
            "SOXL": "Daily 300% of the NYSE Semiconductor Index before fees and expenses; daily reset",
            "SOXX": "Tracks the NYSE Semiconductor Index before fees and expenses",
            "issuer_sources": {
                "SOXL": "https://www.direxion.com/product/daily-semiconductor-bull-bear-3x-etfs",
                "SOXX": "https://www.ishares.com/us/products/239705/fund",
            },
        },
        "hash_manifest_sha256": {
            "source_files": source_hashes,
            "generated_inputs_and_artifacts": generated_artifact_hashes,
            "encoding": "UTF-8",
        },
        "execution_assumptions": {
            "signal_time": "completed regular-session close",
            "execution_time": "next regular-session open",
            "slippage_and_cost_bps_per_fill": args.cost_bps,
            "fractional_shares_binary_research_only": True,
            "cash_yield": 0.0,
            "tax": "excluded",
            "fx": "excluded; USD-only",
            "dividends": "cash credited on ex-date from Yahoo events",
        },
        "diagnostic_definitions_NOT_ACTIVE": {
            "A": "After a weakness fill, both SOXL and SOXX must close above the relevant EMA before another weakness tranche; every B reduction requires three subsequently completed sessions between fills.",
            "B": "Same as A, but weakness_10ema is logged as watch-only and cannot schedule a sale.",
            "hard_risk": "D-grade hard maximum-loss remains unsized, is logged, and is never executed or suppressed.",
        },
        "data_quality": {"SOXL": q_soxl, "SOXX": q_soxx},
        "lookahead_audit": {
            "SOXL": causality_audit(soxl, builder, pd.Timestamp(args.start), pd.Timestamp(args.end)),
            "SOXX": causality_audit(soxx, builder, pd.Timestamp(args.start), pd.Timestamp(args.end)),
        },
        "base_case": base,
        "cost_sensitivity_total_returns": sensitivity,
        "limitations": [
            "The live policy is a review-alert overlay, not an autonomous trading strategy.",
            "The active hard-loss review has no deterministic sale quantity, so it is logged but not executed in the staged overlay.",
            "The one-year staged overlay uses a hypothetical period-start cost anchor; the current USD 123.32 average cost cannot be applied before the actual acquisition dates without look-ahead.",
            "All B alerts are assumed human-approved and filled at next open only for the simulation.",
            "The 27-share SOXL residual has no EMA sale trigger and remains held.",
            "The binary long/cash study completes missing entry/exit/size/reset rules and is not active policy.",
            "Diagnostic A and B are predeclared sensitivity tests only; neither changes or optimizes the active policy.",
            "SOXX is the policy confirmation proxy and references the same NYSE Semiconductor Index as SOXL; SOXL's daily reset prevents interpreting its multi-day return as three times SOXX.",
            "One year is a single high-volatility regime and is insufficient for parameter optimization.",
            "This is an in-sample mechanical replay of a policy formed after the tested period, not predictive validation.",
        ],
    }
    for name, value in artifact_text.items():
        (args.output_dir / name).write_bytes(value.encode("utf-8"))
    (args.output_dir / f"{stem}_results.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": "passed", "results": str(args.output_dir / f'{stem}_results.json'), "metrics": base["metrics"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
