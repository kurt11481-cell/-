#!/usr/bin/env python3
"""Research-only Yahoo option-chain analyzer.

Observed chain data and model-derived sensitivities are kept separate. Signed
Call-minus-Put fields are explicitly heuristic because Yahoo OI has no long/short
or dealer attribution. This script never places orders.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import math
import re
import sys
import time as time_module
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:  # Plotting is useful but must not block the core analyzer.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    PLOTTING_AVAILABLE = True
except ImportError:  # pragma: no cover - environment dependent
    plt = None
    font_manager = None
    PLOTTING_AVAILABLE = False


ET = ZoneInfo("America/New_York")
UTC = timezone.utc
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
YAHOO_OPTION_URL = "https://query2.finance.yahoo.com/v7/finance/options/{ticker}"
YAHOO_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)


class DataError(RuntimeError):
    """Raised when a chain cannot pass a required data gate."""


def configure_font() -> str:
    if not PLOTTING_AVAILABLE:
        return "plotting-unavailable"
    available = {f.name for f in font_manager.fontManager.ttflist}
    for candidate in ("Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"):
        if candidate in available:
            plt.rcParams["font.family"] = candidate
            plt.rcParams["axes.unicode_minus"] = False
            return candidate
    return "matplotlib-default"


def normal_pdf(value: float) -> float:
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def validate_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not TICKER_RE.fullmatch(ticker):
        raise argparse.ArgumentTypeError("Ticker must match ^[A-Z][A-Z0-9.-]{0,9}$")
    return ticker


def validate_session_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Session date must use YYYY-MM-DD") from exc


def quote_age_in_hours(quote_time_utc: datetime | None, now_utc: datetime) -> float | None:
    if quote_time_utc is None:
        return None
    return (now_utc - quote_time_utc).total_seconds() / 3600


def quote_matches_expected_session(
    quote_time_utc: datetime | None, expected_session_date: date | None
) -> bool:
    if quote_time_utc is None or expected_session_date is None:
        return False
    return quote_time_utc.astimezone(ET).date() == expected_session_date


def request_json(
    session: urllib.request.OpenerDirector,
    url: str,
    params: dict[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            query = urllib.parse.urlencode(
                {key: value for key, value in (params or {}).items() if value is not None}
            )
            request_url = f"{url}?{query}" if query else url
            request = urllib.request.Request(request_url, headers={"User-Agent": USER_AGENT})
            with session.open(request, timeout=15) as response:
                status = response.getcode()
                if status in (401, 429):
                    raise DataError(f"Yahoo HTTP {status}")
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise DataError("Yahoo returned a non-object JSON payload")
            return payload
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            DataError,
        ) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time_module.sleep(1.5 * (2**attempt))
    raise DataError(f"Yahoo request failed after {retries} attempts: {last_error}")


def create_yahoo_session() -> tuple[urllib.request.OpenerDirector, str | None]:
    cookie_jar = http.cookiejar.CookieJar()
    session = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    crumb: str | None = None
    try:
        session.open(
            urllib.request.Request("https://fc.yahoo.com", headers={"User-Agent": USER_AGENT}),
            timeout=10,
        ).close()
        with session.open(
            urllib.request.Request(YAHOO_CRUMB_URL, headers={"User-Agent": USER_AGENT}),
            timeout=10,
        ) as response:
            text = response.read().decode("utf-8").strip()
            if response.getcode() == 200 and text:
                crumb = text
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        pass
    return session, crumb


def option_result(payload: dict[str, Any]) -> dict[str, Any]:
    chain = payload.get("optionChain")
    if not isinstance(chain, dict):
        raise DataError("Missing optionChain object; Yahoo schema may have changed")
    if chain.get("error"):
        raise DataError(f"Yahoo optionChain error: {chain['error']}")
    results = chain.get("result")
    if not isinstance(results, list) or not results:
        raise DataError("Ticker error, no listed options, or empty Yahoo result")
    result = results[0]
    if not isinstance(result, dict):
        raise DataError("Malformed Yahoo option result")
    return result


def expiry_date_from_epoch(epoch: int) -> date:
    # Yahoo expiry epochs are treated as UTC calendar dates. Converting midnight
    # UTC to ET first can incorrectly move the date back one day.
    return datetime.fromtimestamp(epoch, UTC).date()


def time_to_expiry_years(expiry_epoch: int, now_et: datetime) -> tuple[float, str]:
    expiry_day = expiry_date_from_epoch(expiry_epoch)
    assumed_close = datetime.combine(expiry_day, time(16, 0), tzinfo=ET)
    seconds = (assumed_close - now_et).total_seconds()
    if seconds <= 0:
        raise DataError("Selected option expiry has already passed its assumed 16:00 ET close")
    warning = "Expiry time assumes a regular 16:00 ET close; verify holidays and early closes."
    return seconds / (365.0 * 24 * 60 * 60), warning


def is_standard_monthly(expiry_day: date) -> bool:
    return expiry_day.weekday() == 4 and 15 <= expiry_day.day <= 21


def choose_expiries(
    epochs: list[int], now_et: datetime, count: int, minimum_dte: int
) -> list[int]:
    eligible = sorted(
        int(epoch)
        for epoch in epochs
        if (expiry_date_from_epoch(int(epoch)) - now_et.date()).days >= minimum_dte
    )
    if not eligible:
        return []
    priority = [eligible[0]]
    next_monthly = next(
        (
            epoch
            for epoch in eligible[1:]
            if is_standard_monthly(expiry_date_from_epoch(epoch))
        ),
        None,
    )
    if next_monthly is not None:
        priority.append(next_monthly)
    priority.extend(epoch for epoch in eligible if epoch not in priority)
    # Return fallback candidates as well. The caller stops after enough liquid
    # expiries pass the quality gate.
    return priority[: max(count * 4, count + 4)]


def select_expiry_results(
    passing: list[dict[str, Any]], limited: list[dict[str, Any]], count: int
) -> tuple[list[dict[str, Any]], bool]:
    """Prefer PASS expiries and use LIMITED only to make gaps visible."""
    chosen = passing[:count]
    if len(chosen) < count:
        chosen.extend(limited[: count - len(chosen)])
    return chosen, len(passing) < count


def set_eligibility(
    summary: dict[str, Any], pass_count: int, requested_expiries: int
) -> None:
    summary["descriptive_report_eligible"] = (
        pass_count >= requested_expiries
        and not summary.get("critical_errors")
        and bool(summary.get("official_session_verified"))
        and len(summary.get("expiries") or []) == requested_expiries
        and all(
            item.get("data_quality") == "PASS"
            and item.get("underlying_session_matches_expected")
            for item in summary.get("expiries") or []
        )
    )
    summary["alert_eligible"] = summary["descriptive_report_eligible"] and all(
        item.get("chain_freshness", {}).get("chain_quote_timestamp_verified")
        for item in summary.get("expiries") or []
    )


SIDE_FIELDS = (
    "contractSymbol",
    "lastTradeDate",
    "lastPrice",
    "bid",
    "ask",
    "change",
    "percentChange",
    "volume",
    "openInterest",
    "impliedVolatility",
    "inTheMoney",
    "contractSize",
    "currency",
)


def parse_side(items: list[dict[str, Any]], prefix: str) -> pd.DataFrame:
    columns = ["strike"] + [f"{prefix}_{field}" for field in SIDE_FIELDS]
    rows: list[dict[str, Any]] = []
    for item in items or []:
        if item.get("strike") is None:
            continue
        row: dict[str, Any] = {"strike": item.get("strike")}
        for field in SIDE_FIELDS:
            value = item.get(field)
            if field == "lastTradeDate" and value:
                value = datetime.fromtimestamp(int(value), UTC).isoformat()
            row[f"{prefix}_{field}"] = value
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def numericize(df: pd.DataFrame) -> pd.DataFrame:
    numeric_suffixes = (
        "lastPrice",
        "bid",
        "ask",
        "change",
        "percentChange",
        "volume",
        "openInterest",
        "impliedVolatility",
    )
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    for col in df.columns:
        if col.endswith(numeric_suffixes):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("call_volume", "put_volume", "call_openInterest", "put_openInterest"):
        if col in df:
            df[col] = df[col].fillna(0.0)
    return df.dropna(subset=["strike"]).sort_values("strike").reset_index(drop=True)


def mark_price(row: pd.Series, side: str) -> tuple[float, str]:
    bid = row.get(f"{side}_bid")
    ask = row.get(f"{side}_ask")
    last = row.get(f"{side}_lastPrice")
    if pd.notna(bid) and pd.notna(ask) and bid > 0 and ask >= bid:
        return float((bid + ask) / 2), "mid"
    if pd.notna(last) and last > 0:
        return float(last), "last"
    return math.nan, "missing"


def bs_greeks(
    option_type: str,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    dividend_yield: float,
    sigma: float,
) -> tuple[float, float, float, float]:
    if min(spot, strike, years, sigma) <= 0 or not math.isfinite(sigma) or sigma >= 5:
        return (math.nan,) * 4
    root_t = math.sqrt(years)
    d1 = (
        math.log(spot / strike)
        + (rate - dividend_yield + 0.5 * sigma * sigma) * years
    ) / (sigma * root_t)
    d2 = d1 - sigma * root_t
    discount_q = math.exp(-dividend_yield * years)
    discount_r = math.exp(-rate * years)
    pdf = normal_pdf(d1)
    if option_type == "call":
        delta = discount_q * normal_cdf(d1)
        theta_year = (
            -(spot * discount_q * pdf * sigma) / (2 * root_t)
            - rate * strike * discount_r * normal_cdf(d2)
            + dividend_yield * spot * discount_q * normal_cdf(d1)
        )
    else:
        delta = discount_q * (normal_cdf(d1) - 1)
        theta_year = (
            -(spot * discount_q * pdf * sigma) / (2 * root_t)
            + rate * strike * discount_r * normal_cdf(-d2)
            - dividend_yield * spot * discount_q * normal_cdf(-d1)
        )
    gamma = discount_q * pdf / (spot * sigma * root_t)
    vanna = -discount_q * pdf * d2 / sigma
    return delta, gamma, vanna, theta_year / 365.0


def enrich_chain(
    df: pd.DataFrame,
    spot: float,
    years: float,
    rate: float,
    dividend_yield: float,
    maximum_spread_fraction: float,
) -> pd.DataFrame:
    for side in ("call", "put"):
        marks = df.apply(lambda row: mark_price(row, side), axis=1)
        df[f"{side}_mark"] = [x[0] for x in marks]
        df[f"{side}_markSource"] = [x[1] for x in marks]
        bid = df.get(f"{side}_bid", pd.Series(index=df.index, dtype=float))
        ask = df.get(f"{side}_ask", pd.Series(index=df.index, dtype=float))
        midpoint = (bid + ask) / 2
        spread_fraction = (ask - bid) / midpoint.replace(0, np.nan)
        quote_ok = (bid > 0) & (ask >= bid) & (spread_fraction <= maximum_spread_fraction)
        iv = df.get(f"{side}_impliedVolatility", pd.Series(index=df.index, dtype=float))
        oi = df.get(f"{side}_openInterest", pd.Series(index=df.index, dtype=float)).fillna(0)
        contract_size = df.get(
            f"{side}_contractSize", pd.Series(index=df.index, dtype=object)
        )
        # A missing multiplier is not evidence of a standard contract. Exclude it
        # from model sensitivities until the contract terms are verified.
        contract_standard = contract_size.astype(str).eq("REGULAR")
        df[f"{side}_contractStandard"] = contract_standard
        df[f"{side}_spreadFraction"] = spread_fraction
        df[f"{side}_analysisValid"] = (
            quote_ok & (iv > 0) & (iv < 5) & (oi > 0) & contract_standard
        )

        greek_rows = []
        for _, row in df.iterrows():
            greek_rows.append(
                bs_greeks(
                    side,
                    spot,
                    float(row["strike"]),
                    years,
                    rate,
                    dividend_yield,
                    float(row.get(f"{side}_impliedVolatility", math.nan)),
                )
            )
        greek_df = pd.DataFrame(
            greek_rows,
            columns=[f"{side}_delta", f"{side}_gamma", f"{side}_vanna", f"{side}_theta"],
        )
        for col in greek_df:
            df[col] = greek_df[col].where(df[f"{side}_analysisValid"])

        multiplier = 100.0
        df[f"{side}_deltaShares"] = df[f"{side}_delta"] * oi * multiplier
        df[f"{side}_dollarDelta"] = df[f"{side}_deltaShares"] * spot
        df[f"{side}_grossGEXDollarPer1Pct"] = (
            df[f"{side}_gamma"] * oi * multiplier * spot * spot * 0.01
        )
        df[f"{side}_vannaDollarDeltaPerVolPoint"] = (
            df[f"{side}_vanna"] * oi * multiplier * spot * 0.01
        )
        df[f"{side}_thetaDollarsPerDay"] = df[f"{side}_theta"] * oi * multiplier
        df[f"{side}_indicativeMarkValue"] = (
            df[f"{side}_mark"] * oi * multiplier
        ).where(df[f"{side}_analysisValid"])

    df["heuristicSignedGEXProxy"] = (
        df["call_grossGEXDollarPer1Pct"] - df["put_grossGEXDollarPer1Pct"]
    )
    df["heuristicSignedVEXProxy"] = (
        df["call_vannaDollarDeltaPerVolPoint"]
        - df["put_vannaDollarDeltaPerVolPoint"]
    )
    return df


def calculate_max_pain(df: pd.DataFrame) -> float | None:
    strikes = df["strike"].to_numpy(dtype=float)
    call_oi = df["call_openInterest"].fillna(0).where(
        df.get("call_contractStandard", True), 0
    ).to_numpy(dtype=float)
    put_oi = df["put_openInterest"].fillna(0).where(
        df.get("put_contractStandard", True), 0
    ).to_numpy(dtype=float)
    if not len(strikes) or np.sum(call_oi + put_oi) <= 0:
        return None
    payouts = []
    for settlement in strikes:
        call_payout = np.maximum(settlement - strikes, 0) * call_oi
        put_payout = np.maximum(strikes - settlement, 0) * put_oi
        payouts.append(float(np.sum(call_payout + put_payout)))
    return float(strikes[int(np.argmin(payouts))])


def nearest_delta_strike(df: pd.DataFrame, side: str, target: float) -> float | None:
    valid = df[df[f"{side}_analysisValid"] & df[f"{side}_delta"].notna()]
    if valid.empty:
        return None
    index = (valid[f"{side}_delta"] - target).abs().idxmin()
    return float(valid.loc[index, "strike"])


def atm_implied_move(df: pd.DataFrame, spot: float) -> dict[str, float | None]:
    usable = df[
        df["call_analysisValid"]
        & df["put_analysisValid"]
        & df["call_mark"].notna()
        & df["put_mark"].notna()
    ].copy()
    if usable.empty:
        return {"atm_strike": None, "straddle": None, "fraction": None}
    index = (usable["strike"] - spot).abs().idxmin()
    row = usable.loc[index]
    straddle = float(row["call_mark"] + row["put_mark"])
    return {
        "atm_strike": float(row["strike"]),
        "straddle": straddle,
        "fraction": straddle / spot if spot else None,
    }


def liquidity_summary(df: pd.DataFrame) -> dict[str, Any]:
    spreads = []
    for side in ("call", "put"):
        bid = df[f"{side}_bid"]
        ask = df[f"{side}_ask"]
        valid = (bid > 0) & (ask >= bid)
        midpoint = (bid[valid] + ask[valid]) / 2
        spread_fraction = (ask[valid] - bid[valid]) / midpoint.replace(0, np.nan)
        spreads.extend(spread_fraction.dropna().tolist())
    return {
        "strike_rows": int(len(df)),
        "valid_call_rows": int(df["call_analysisValid"].sum()),
        "valid_put_rows": int(df["put_analysisValid"].sum()),
        "call_oi": float(df["call_openInterest"].fillna(0).sum()),
        "put_oi": float(df["put_openInterest"].fillna(0).sum()),
        "median_quoted_spread_fraction": float(np.median(spreads)) if spreads else None,
    }


def observed_trade_time_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize prints without pretending they timestamp Yahoo bid/ask quotes."""
    values: list[datetime] = []
    for side in ("call", "put"):
        column = f"{side}_lastTradeDate"
        if column not in df:
            continue
        for value in df.loc[df[f"{side}_analysisValid"], column].dropna():
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    values.append(parsed.astimezone(UTC))
            except ValueError:
                continue
    return {
        "latest_observed_trade_time_utc": max(values).isoformat() if values else None,
        "earliest_observed_trade_time_utc": min(values).isoformat() if values else None,
        "chain_quote_timestamp_verified": False,
        "note": (
            "Yahoo lastTradeDate timestamps executions, not the displayed bid/ask. "
            "The option-chain quote timestamp therefore cannot be verified."
        ),
    }


def render_charts(df: pd.DataFrame, spot: float, max_pain: float | None, output: Path) -> None:
    if not PLOTTING_AVAILABLE:
        return
    valid = df[(df["call_analysisValid"]) | (df["put_analysisValid"])].copy()
    if valid.empty:
        return
    valid["distance"] = (valid["strike"] - spot).abs()
    chart = valid.nsmallest(min(41, len(valid)), "distance").sort_values("strike")
    gaps = np.diff(chart["strike"].to_numpy())
    width = float(np.median(gaps) * 0.35) if len(gaps) else max(spot * 0.002, 0.1)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), constrained_layout=True)
    axes[0].bar(chart["strike"] - width / 2, chart["call_openInterest"], width, label="Call OI")
    axes[0].bar(chart["strike"] + width / 2, chart["put_openInterest"], width, label="Put OI")
    axes[0].axvline(spot, color="green", linestyle="--", label=f"Spot {spot:.2f}")
    if max_pain is not None:
        axes[0].axvline(max_pain, color="purple", linestyle=":", label=f"Max Pain {max_pain:.2f}")
    axes[0].set_title("Observed open interest")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].plot(chart["strike"], chart["call_impliedVolatility"], label="Call IV")
    axes[1].plot(chart["strike"], chart["put_impliedVolatility"], label="Put IV")
    axes[1].axvline(spot, color="green", linestyle="--")
    axes[1].set_title("Reported implied volatility")
    axes[1].legend()
    axes[1].grid(alpha=0.25)
    fig.savefig(output / "observed_chain.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), constrained_layout=True)
    axes[0].bar(chart["strike"] - width / 2, chart["call_grossGEXDollarPer1Pct"], width, label="Call gross GEX")
    axes[0].bar(chart["strike"] + width / 2, chart["put_grossGEXDollarPer1Pct"], width, label="Put gross GEX")
    axes[0].set_title("OI-weighted gross gamma sensitivity; no position direction")
    axes[0].legend()
    axes[0].grid(alpha=0.25)
    axes[1].plot(chart["strike"], chart["heuristicSignedGEXProxy"], label="Heuristic Call-minus-Put proxy")
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_title("Scenario proxy, not actual dealer GEX")
    axes[1].legend()
    axes[1].grid(alpha=0.25)
    fig.savefig(output / "model_sensitivities.png", dpi=150)
    plt.close(fig)


def markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Options positioning snapshot",
        "",
        f"- Ticker: {summary['ticker']}",
        f"- Run time UTC: {summary['run_time_utc']}",
        f"- Underlying regular-market price: {summary['underlying_price']}",
        f"- Underlying quote time UTC: {summary.get('underlying_quote_time_utc')}",
        f"- Expected completed U.S. session: {summary.get('expected_us_session_date')}",
        f"- Official calendar source: {summary.get('official_calendar_source')}",
        f"- Official session verified: {summary.get('official_session_verified', False)}",
        f"- Risk-free rate assumption: {summary['risk_free_rate']:.4%}",
        f"- Dividend-yield assumption: {summary['dividend_yield']:.4%}",
        f"- Descriptive-report eligible: {summary.get('descriptive_report_eligible', False)}",
        f"- Directional-alert eligible: {summary.get('alert_eligible', False)}",
        f"- Partial expiry coverage: {summary.get('partial_expiry_coverage', True)}",
        "",
        "## Conclusion",
        "",
        "Observed OI and model sensitivities are descriptive only. Directional dealer positioning is not identifiable from Yahoo OI.",
        "",
    ]
    for expiry in summary["expiries"]:
        lines.extend(
            [
                f"## Expiry {expiry['expiration_date']}",
                "",
                f"- DTE: {expiry['dte_calendar']}",
                f"- Data quality: {expiry['data_quality']}",
                f"- Max Pain reference: {expiry['max_pain']}",
                f"- Put 25-delta strike: {expiry['put_25_delta_strike']}",
                f"- Call 25-delta strike: {expiry['call_25_delta_strike']}",
                f"- ATM straddle implied move fraction: {expiry['atm_implied_move_fraction']}",
                f"- Valid Call/Put rows: {expiry['liquidity']['valid_call_rows']} / {expiry['liquidity']['valid_put_rows']}",
                f"- Latest observed option trade (not quote time): {expiry.get('chain_freshness', {}).get('latest_observed_trade_time_utc')}",
                f"- Chain quote timestamp verified: {expiry.get('chain_freshness', {}).get('chain_quote_timestamp_verified', False)}",
                f"- Warnings: {expiry.get('warnings') or ['none']}",
                "",
            ]
        )
    if summary.get("rejected_expiries"):
        lines.extend(
            [
                "## Rejected expiries",
                "",
                *[
                    f"- {item.get('expiration_date')}: {item.get('warnings')}"
                    for item in summary["rejected_expiries"]
                ],
                "",
            ]
        )
    if summary.get("errors") or summary.get("critical_errors"):
        lines.extend(
            [
                "## Collection and consistency errors",
                "",
                *[
                    f"- {item}"
                    for item in (summary.get("errors") or [])
                    + (summary.get("critical_errors") or [])
                ],
                "",
            ]
        )
    lines.extend(
        [
            "## Mandatory limitation",
            "",
            "> This analysis uses an unofficial Yahoo Finance option chain and OI-weighted model estimates. It cannot identify actual dealer or institutional positions or trade direction and must not be used as a standalone trading signal.",
            "",
        ]
    )
    return "\n".join(lines)


def analyze_expiry(
    ticker: str,
    session: urllib.request.OpenerDirector,
    crumb: str | None,
    expiry_epoch: int,
    output: Path,
    rate: float,
    dividend_yield: float,
    now_et: datetime,
    make_plots: bool,
    maximum_spread_fraction: float,
    maximum_quote_age_hours: float,
    expected_session_date: date | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"date": expiry_epoch}
    if crumb:
        params["crumb"] = crumb
    payload = request_json(session, YAHOO_OPTION_URL.format(ticker=ticker), params)
    (output / "raw_expiry.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = option_result(payload)
    quote = result.get("quote") or {}
    spot = quote.get("regularMarketPrice")
    if not isinstance(spot, (int, float)) or spot <= 0:
        raise DataError("Missing or invalid regularMarketPrice")
    options = result.get("options")
    if not isinstance(options, list) or not options:
        raise DataError("No option data for selected expiry")
    calls = options[0].get("calls") or []
    puts = options[0].get("puts") or []
    if not calls and not puts:
        raise DataError("Both Call and Put chains are empty")

    call_df = parse_side(calls, "call")
    put_df = parse_side(puts, "put")
    df = pd.merge(call_df, put_df, on="strike", how="outer")
    df = numericize(df)
    if df.empty:
        raise DataError("No valid strike rows after parsing")
    for side in ("call", "put"):
        for field in ("bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"):
            col = f"{side}_{field}"
            if col not in df:
                df[col] = math.nan if field not in ("volume", "openInterest") else 0.0

    years, time_warning = time_to_expiry_years(expiry_epoch, now_et)
    df = enrich_chain(
        df,
        float(spot),
        years,
        rate,
        dividend_yield,
        maximum_spread_fraction,
    )
    max_pain = calculate_max_pain(df)
    call_25 = nearest_delta_strike(df, "call", 0.25)
    put_25 = nearest_delta_strike(df, "put", -0.25)
    implied_move = atm_implied_move(df, float(spot))
    liquidity = liquidity_summary(df)
    trade_times = observed_trade_time_summary(df)
    quality = "PASS"
    warnings = []
    if time_warning:
        warnings.append(time_warning)
    warnings.append(trade_times["note"])
    if liquidity["valid_call_rows"] < 3 or liquidity["valid_put_rows"] < 3:
        quality = "FAIL"
        warnings.append("Fewer than three liquid valid strikes on one or both sides.")
    spread = liquidity["median_quoted_spread_fraction"]
    if spread is None or spread > 0.25:
        quality = "LIMITED" if quality == "PASS" else quality
        warnings.append("Quoted spread data are missing or median spread exceeds 25%.")
    for side in ("call", "put"):
        contract_series = df.get(
            f"{side}_contractSize", pd.Series(index=df.index, dtype=object)
        )
        if contract_series.isna().any():
            quality = "LIMITED" if quality == "PASS" else quality
            warnings.append(
                f"Missing {side.title()} contract-size metadata were excluded; contract adjustment status is incomplete."
            )
        contract_sizes = contract_series.dropna()
        if contract_sizes.astype(str).ne("REGULAR").any():
            warnings.append(
                f"Non-standard {side.title()} contracts were excluded from model sensitivities and Max Pain."
            )

    df.to_csv(output / "option_chain.csv", index=False, encoding="utf-8-sig")
    if make_plots:
        render_charts(df, float(spot), max_pain, output)
    quote_time = quote.get("regularMarketTime")
    quote_time_utc = datetime.fromtimestamp(int(quote_time), UTC) if quote_time else None
    quote_age_hours = quote_age_in_hours(quote_time_utc, datetime.now(UTC))
    if quote_age_hours is None or quote_age_hours < -1 or quote_age_hours > maximum_quote_age_hours:
        quality = "FAIL"
        warnings.append(
            f"Underlying quote timestamp is missing or older than {maximum_quote_age_hours:g} hours."
        )
    session_matches = quote_matches_expected_session(
        quote_time_utc, expected_session_date
    )
    if expected_session_date is None:
        quality = "LIMITED" if quality == "PASS" else quality
        warnings.append(
            "Official expected U.S. session date was not supplied; descriptive eligibility is withheld."
        )
    elif not session_matches:
        quality = "FAIL"
        warnings.append(
            f"Underlying quote does not match the authoritative expected session {expected_session_date.isoformat()}."
        )
    return {
        "expiration_date": expiry_date_from_epoch(expiry_epoch).isoformat(),
        "dte_calendar": (expiry_date_from_epoch(expiry_epoch) - now_et.date()).days,
        "underlying_price": float(spot),
        "underlying_quote_time_utc": (
            quote_time_utc.isoformat() if quote_time_utc else None
        ),
        "underlying_quote_age_hours": quote_age_hours,
        "underlying_session_matches_expected": session_matches,
        "chain_freshness": trade_times,
        "data_quality": quality,
        "warnings": warnings,
        "max_pain": max_pain,
        "call_25_delta_strike": call_25,
        "put_25_delta_strike": put_25,
        "atm_strike": implied_move["atm_strike"],
        "atm_straddle": implied_move["straddle"],
        "atm_implied_move_fraction": implied_move["fraction"],
        "liquidity": liquidity,
    }


def run_analysis(args: argparse.Namespace) -> Path:
    now_utc = datetime.now(UTC)
    now_et = now_utc.astimezone(ET)
    font_name = configure_font()
    session, crumb = create_yahoo_session()
    params: dict[str, Any] = {"crumb": crumb} if crumb else {}
    root_payload = request_json(session, YAHOO_OPTION_URL.format(ticker=args.ticker), params)
    root_result = option_result(root_payload)
    epochs = root_result.get("expirationDates") or []
    selected = choose_expiries(epochs, now_et, args.expiries, args.minimum_dte)
    if not selected:
        raise DataError("No eligible expiration date after the configured minimum DTE")

    run_id = now_utc.strftime("%Y%m%dT%H%M%SZ")
    root_output = Path(args.output_root).expanduser().resolve() / f"{args.ticker}_{run_id}"
    root_output.mkdir(parents=True, exist_ok=False)
    (root_output / "raw_root.json").write_text(
        json.dumps(root_payload, ensure_ascii=False), encoding="utf-8"
    )
    summary: dict[str, Any] = {
        "ticker": args.ticker,
        "run_time_utc": now_utc.isoformat(),
        "run_time_et": now_et.isoformat(),
        "risk_free_rate": args.risk_free_rate,
        "dividend_yield": args.dividend_yield,
        "font": font_name,
        "plots_available": PLOTTING_AVAILABLE,
        "source": "Unofficial Yahoo Finance option endpoint",
        "official_calendar_source": args.calendar_source,
        "expected_us_session_date": (
            args.expected_session_date.isoformat()
            if args.expected_session_date
            else None
        ),
        "official_session_verified": bool(
            args.expected_session_date and args.calendar_source
        ),
        "underlying_price": None,
        "underlying_quote_time_utc": None,
        "expiries": [],
        "errors": [],
        "critical_errors": [],
        "rejected_expiries": [],
        "partial_expiry_coverage": True,
        "descriptive_report_eligible": False,
        "alert_eligible": False,
    }
    pass_expiries: list[dict[str, Any]] = []
    limited_expiries: list[dict[str, Any]] = []
    for epoch in selected:
        if len(pass_expiries) >= args.expiries:
            break
        expiry_day = expiry_date_from_epoch(epoch).isoformat()
        expiry_output = root_output / expiry_day
        expiry_output.mkdir(parents=True, exist_ok=True)
        try:
            item = analyze_expiry(
                args.ticker,
                session,
                crumb,
                epoch,
                expiry_output,
                args.risk_free_rate,
                args.dividend_yield,
                now_et,
                PLOTTING_AVAILABLE and not args.no_plots,
                args.maximum_spread_fraction,
                args.maximum_quote_age_hours,
                args.expected_session_date,
            )
            if item["data_quality"] == "FAIL":
                summary["rejected_expiries"].append(item)
                continue
            if item["data_quality"] == "PASS":
                pass_expiries.append(item)
            else:
                limited_expiries.append(item)
        except Exception as exc:  # Preserve per-expiry failures in the manifest.
            summary["errors"].append({"expiration_date": expiry_day, "error": str(exc)})

    summary["expiries"], summary["partial_expiry_coverage"] = select_expiry_results(
        pass_expiries, limited_expiries, args.expiries
    )
    if summary["expiries"]:
        summary["underlying_price"] = summary["expiries"][0]["underlying_price"]
        summary["underlying_quote_time_utc"] = summary["expiries"][0][
            "underlying_quote_time_utc"
        ]

    if summary["expiries"]:
        prices = [item["underlying_price"] for item in summary["expiries"]]
        quote_times = [
            datetime.fromisoformat(item["underlying_quote_time_utc"])
            for item in summary["expiries"]
            if item.get("underlying_quote_time_utc")
        ]
        if max(prices) / min(prices) - 1 > 0.005:
            summary["critical_errors"].append(
                "Underlying prices differ by more than 0.5% across expiry snapshots."
            )
        if quote_times and (max(quote_times) - min(quote_times)).total_seconds() > 600:
            summary["critical_errors"].append(
                "Underlying quote timestamps differ by more than 10 minutes across expiries."
            )
    # Yahoo does not timestamp the displayed option bid/ask. Without a
    # timestamped chain source, the output remains research-only and cannot
    # drive an automated directional alert even when every other gate passes.
    set_eligibility(summary, len(pass_expiries), args.expiries)
    (root_output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root_output / "report.md").write_text(markdown_report(summary), encoding="utf-8")
    if not summary["expiries"]:
        raise DataError(f"All selected expiries failed; see {root_output / 'summary.json'}")
    return root_output


def self_test() -> None:
    call = bs_greeks("call", 100, 105, 30 / 365, 0.04, 0.01, 0.30)
    put = bs_greeks("put", 100, 95, 30 / 365, 0.04, 0.01, 0.30)
    assert 0 < call[0] < 1
    assert -1 < put[0] < 0
    assert call[1] > 0 and put[1] > 0
    assert all(math.isfinite(value) for value in call + put)
    epsilon = 1e-5
    delta_up = bs_greeks("call", 100, 105, 30 / 365, 0.04, 0.01, 0.30 + epsilon)[0]
    delta_down = bs_greeks("call", 100, 105, 30 / 365, 0.04, 0.01, 0.30 - epsilon)[0]
    finite_difference_vanna = (delta_up - delta_down) / (2 * epsilon)
    assert math.isclose(call[2], finite_difference_vanna, rel_tol=1e-5, abs_tol=1e-7)
    df = pd.DataFrame(
        {
            "strike": [90.0, 100.0, 110.0],
            "call_openInterest": [100.0, 200.0, 10.0],
            "put_openInterest": [10.0, 200.0, 100.0],
        }
    )
    df["call_contractStandard"] = True
    df["put_contractStandard"] = True
    assert calculate_max_pain(df) == 100.0
    base = pd.DataFrame(
        {
            "strike": [95.0, 100.0, 105.0],
            "call_bid": [7.0, 4.0, 2.0],
            "call_ask": [7.4, 4.2, 2.1],
            "put_bid": [1.8, 3.8, 6.8],
            "put_ask": [1.9, 4.0, 7.2],
            "call_impliedVolatility": [0.30, 0.29, 0.31],
            "put_impliedVolatility": [0.31, 0.30, 0.32],
            "call_openInterest": [100, 200, 100],
            "put_openInterest": [100, 200, 100],
            "call_contractSize": ["REGULAR"] * 3,
            "put_contractSize": ["REGULAR"] * 3,
            "call_lastTradeDate": [datetime.now(UTC).isoformat()] * 3,
            "put_lastTradeDate": [datetime.now(UTC).isoformat()] * 3,
        }
    )
    valid = enrich_chain(base.copy(), 100, 30 / 365, 0.04, 0.0, 0.25)
    assert valid["call_analysisValid"].all() and valid["put_analysisValid"].all()
    assert observed_trade_time_summary(valid)["chain_quote_timestamp_verified"] is False
    crossed = base.copy()
    crossed.loc[0, "call_ask"] = 6.0
    crossed_result = enrich_chain(crossed, 100, 30 / 365, 0.04, 0.0, 0.25)
    assert not bool(crossed_result.loc[0, "call_analysisValid"])
    wide = base.copy()
    wide.loc[0, "call_ask"] = 20.0
    wide_result = enrich_chain(wide, 100, 30 / 365, 0.04, 0.0, 0.25)
    assert not bool(wide_result.loc[0, "call_analysisValid"])
    missing_multiplier = base.copy()
    missing_multiplier.loc[0, "call_contractSize"] = None
    missing_result = enrich_chain(
        missing_multiplier, 100, 30 / 365, 0.04, 0.0, 0.25
    )
    assert not bool(missing_result.loc[0, "call_analysisValid"])
    selected, partial = select_expiry_results(
        [{"data_quality": "PASS"}],
        [{"data_quality": "LIMITED"}, {"data_quality": "LIMITED"}],
        2,
    )
    assert len(selected) == 2 and partial is True
    reference_now = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
    assert quote_age_in_hours(reference_now, reference_now) == 0
    assert quote_age_in_hours(reference_now - pd.Timedelta(hours=97), reference_now) > 96
    assert quote_matches_expected_session(
        datetime(2026, 7, 30, 20, 0, tzinfo=UTC), date(2026, 7, 30)
    )
    eligibility_summary = {
        "critical_errors": [],
        "official_session_verified": True,
        "expiries": [
            {
                "data_quality": "PASS",
                "underlying_session_matches_expected": True,
                "chain_freshness": {"chain_quote_timestamp_verified": False},
            },
            {
                "data_quality": "PASS",
                "underlying_session_matches_expected": True,
                "chain_freshness": {"chain_quote_timestamp_verified": False},
            },
        ],
    }
    set_eligibility(eligibility_summary, 2, 2)
    assert eligibility_summary["descriptive_report_eligible"] is True
    assert eligibility_summary["alert_eligible"] is False
    eligibility_summary["expiries"] = eligibility_summary["expiries"][:1]
    set_eligibility(eligibility_summary, 1, 2)
    assert eligibility_summary["descriptive_report_eligible"] is False
    now_et = datetime(2026, 7, 31, 12, 0, tzinfo=ET)
    august_weekly = int(datetime(2026, 8, 7, tzinfo=UTC).timestamp())
    august_monthly = int(datetime(2026, 8, 21, tzinfo=UTC).timestamp())
    september_weekly = int(datetime(2026, 9, 4, tzinfo=UTC).timestamp())
    chosen = choose_expiries(
        [september_weekly, august_monthly, august_weekly], now_et, 2, 1
    )
    assert chosen[:2] == [august_weekly, august_monthly]
    expired = int(datetime(2026, 7, 30, tzinfo=UTC).timestamp())
    try:
        time_to_expiry_years(expired, now_et)
        raise AssertionError("expired option should fail")
    except DataError:
        pass
    report_summary = {
        "ticker": "TEST",
        "run_time_utc": reference_now.isoformat(),
        "underlying_price": 100,
        "underlying_quote_time_utc": reference_now.isoformat(),
        "expected_us_session_date": "2026-07-31",
        "official_calendar_source": "official-test",
        "official_session_verified": True,
        "risk_free_rate": 0.04,
        "dividend_yield": 0.0,
        "descriptive_report_eligible": False,
        "alert_eligible": False,
        "partial_expiry_coverage": True,
        "expiries": [],
        "rejected_expiries": [{"expiration_date": "2026-08-07", "warnings": ["test"]}],
        "errors": [{"expiration_date": "2026-08-14", "error": "test"}],
        "critical_errors": [],
    }
    report = markdown_report(report_summary)
    assert "Directional-alert eligible: False" in report
    assert "Rejected expiries" in report and "Collection and consistency errors" in report
    assert validate_ticker("mrvl") == "MRVL"
    print("Self-test passed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", nargs="?", type=validate_ticker)
    parser.add_argument("--expiries", type=int, default=2)
    parser.add_argument("--minimum-dte", type=int, default=3)
    parser.add_argument("--risk-free-rate", type=float, default=0.045)
    parser.add_argument("--dividend-yield", type=float, default=0.0)
    parser.add_argument("--maximum-spread-fraction", type=float, default=0.25)
    parser.add_argument("--maximum-quote-age-hours", type=float, default=96.0)
    parser.add_argument("--expected-session-date", type=validate_session_date)
    parser.add_argument("--calendar-source")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.ticker:
        parser.error("ticker is required unless --self-test is used")
    if args.expiries < 1 or args.expiries > 8:
        parser.error("--expiries must be between 1 and 8")
    if args.minimum_dte < 1:
        parser.error("--minimum-dte must be at least 1; 0DTE requires a separate high-risk workflow")
    if not 0 < args.maximum_spread_fraction <= 2:
        parser.error("--maximum-spread-fraction must be in (0, 2]")
    if args.maximum_quote_age_hours <= 0:
        parser.error("--maximum-quote-age-hours must be positive")
    if bool(args.expected_session_date) != bool(args.calendar_source):
        parser.error(
            "--expected-session-date and --calendar-source must be supplied together after authoritative calendar verification"
        )
    try:
        output = run_analysis(args)
        print(output)
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        return 0 if summary.get("descriptive_report_eligible") else 2
    except DataError as exc:
        print(f"DATA_ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"UNEXPECTED_ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
