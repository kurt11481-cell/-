#!/usr/bin/env python3
"""Redesign T2 F1: indicators and the integrated-check common rules C1-C8, card price triggers, V6 and R-REC1.

Every definition is the rule file's (docs/claude/integrated-check-prompt-v3.12.2-2026-10-09.txt section 2)
and 3); prompt appendix A-3/A-4), computed on the regular-session daily bars of auto_core_bars.py. All values
come from the table CONSTANTS below; each carries the rule-file section it is copied from. Nothing here makes
a new threshold: the split check (auto_core_bars) only blocks a symbol.

States: hit (met, approximate close included), near (only R5 <= 0.75 P and the V6 approach line), pending
(first session of a two-session hold), none, unk (data missing), review (an alert; never evidence).
Pure functions: no file, clock or network access.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from portfolio_exposure import _sample_std  # the S7 sigma formula (sample standard deviation), reused as is


# value, source. Changing a value is an authority/limit change (prompt D16): code, report and Judge together.
CONSTANTS: dict[str, tuple[Any, str]] = {
    "EMA_SHORT": (10, "rule file 2) EMA10"),
    "EMA_MID": (20, "rule file 2) EMA20"),
    "EMA_LONG": (50, "rule file 2) EMA50"),
    "RSI_PERIOD": (14, "rule file 2) RSI14 (Wilder)"),
    "ATR_PERIOD": (14, "rule file 2) ATR14 (Wilder)"),
    "SIGMA_SESSIONS": (60, "rule file 2) sigma60, sample std of 60 daily close returns"),
    "LOOKBACK_SESSIONS": (20, "rule file 2) prior 20-session close high/low and average volume"),
    "RSI_OVERBOUGHT": (70, "rule file 3) C1- RSI14 >= 70"),
    "RSI_OVERSOLD": (30, "rule file 3) C1+ RSI14 <= 30"),
    "C1_ATR_BAND": (2.0, "rule file 3) C1 EMA20 +/- 2 x ATR14 (t-1)"),
    "C2_ATR_BAND": (2.5, "rule file 3) C2 EMA20 +/- 2.5 x ATR14 (t-1)"),
    "C2_FADE_POSITION": (0.35, "rule file 3) C2- close position <= 0.35"),
    "C2_REBOUND_POSITION": (0.65, "rule file 3) C2+ close position >= 0.65"),
    "C2_VOLUME_RATIO": (1.2, "rule file 3) C2 volume >= prior 20-session average x 1.2"),
    "C6_BAND": (0.015, "rule file 3) C6 within 1.5% of EMA20 (DL6 / X6, user decision 2026-10-03 (ii))"),
    "C7_REACTION_SESSIONS": (2, "rule file 3) C7 within 2 sessions of the announcement"),
    "EVENT_WINDOW_SESSIONS": (5, "rule file 3) event rules C2 C4 C6 C7 count for 5 sessions incl. the day"),
    "NEW_HIGH_HOLD_SESSIONS": (2, "rule file 3) new-high breakout hold = 2 sessions (user decision 2026-10-02)"),
    "C8_BY_MULTIPLIER": ({1: 0.10, 2: 0.15, 3: 0.20}, "rule file 3) C8 T without a card value: 1x 10%, 2x 15%, 3x 20%"),
    "C8_UNKNOWN_MULTIPLIER": (0.10, "rule file 3) C8 T when the multiplier needs checking: 10%"),
    "V6_HWM_USD": (Decimal("28473.94"), "rule file 3) V6 HWM"),
    "V6_FIRST_LINE_USD": (Decimal("25626.55"), "rule file 3) V6 first line (HWM x 0.9)"),
    "V6_APPROACH_USD": (Decimal("26395.34"), "rule file 3) V6 approach (first line + 3%)"),
    "V6_MAX_LINE_USD": (Decimal("22779.15"), "rule file 3) V6 maximum line (HWM x 0.8)"),
    "R5_REVIEW_FRACTION": (Decimal("0.70"), "rule file 2-3) (3) R5 close <= 0.70 x P"),
    "R5_NEAR_FRACTION": (Decimal("0.75"), "rule file 2-3) (3) R5 near close <= 0.75 x P"),
    "RREC_WINDOW_SESSIONS": (60, "recovery-gate-R-REC1 1: most recent event within 60 sessions"),
    "RREC_EV1_SIGMA": (2.0, "R-REC1 EV1 SOXX 1-day return <= -2 sigma60"),
    "RREC_EV2_SIGMA": (3.0, "R-REC1 EV2 close <= prior 20-session close high x (1 - 3 sigma60)"),
    "RREC_EV3_SIGMA": (1.0, "R-REC1 EV3 (b) same-day SOXX <= -1 sigma60"),
    "RREC_EV5_SIGMA": (2.0, "R-REC1 EV5 own 1-day return <= -2 sigma60"),
    "RREC_EV4_HWM_FRACTION": (Decimal("0.9"), "R-REC1 EV4 total <= S7 hwm_usd x 0.9 (or the V6 first line)"),
    "RREC_RG1_SESSIONS": (2, "R-REC1 RG1 two sessions after the event"),
    "RREC_RG3_SESSIONS": (2, "R-REC1 RG3 two consecutive closes above C0"),
    "RREC_RG4_DAY_SIGMA": (2.0, "R-REC1 RG4 |1-day| <= 2 sigma60"),
    "RREC_RG4_SHORT_SESSIONS": (5, "R-REC1 RG4 5-session sigma"),
    "RREC_RG4_SHORT_RATIO": (1.5, "R-REC1 RG4 5-session sigma <= 1.5 x sigma60"),
    "RREC_CLOSE_SESSIONS": (20, "R-REC1 closes 20 sessions after the last DS1 (or the event) + RG2"),
    "RREC_BENCHMARK": ("SOXX", "R-REC1 portfolio benchmark"),
    "RREC_POWER_BENCHMARK": ("GRID", "rule file 2-3) (4) sector starting 'A1 \uc804\ub825' uses GRID"),
}
C = {name: value for name, (value, _source) in CONSTANTS.items()}
POWER_SECTOR_PREFIX = "A1 \uc804\ub825"  # "A1 \uc804\ub825"
EV3_LINE = re.compile(r"^- \uc774\ubca4\ud2b8 (\d{4}-\d{2}-\d{2})\(EV")  # "^- \uc774\ubca4\ud2b8 (date)(EV"

# Merge groups ("\uac19\uc740 \uc885\ub958", rule file 3)): direction "-" is sell evidence for a held symbol (weakening for a watch
# symbol), "+" buy evidence; "alert" is a review (never evidence).
COMMON_RULES = {
    "C1-": ("overheat", "-", "state"), "C1+": ("oversold", "+", "state"),
    "C2-": ("overheat_fade", "-", "event"), "C2+": ("oversold_rebound", "+", "event"),
    "C3-": ("trend_break", "-", "state"), "C3+": ("trend_recover", "+", "state"),
    "C4-": ("false_breakout", "-", "event"), "C4+": ("false_breakdown", "+", "event"),
    "C5-": ("new_low", "-", "state"), "C5+": ("new_high", "+", "state"),
    "C6-": ("rebound_fail", "-", "event"), "C6+": ("pullback_rebound", "+", "event"),
    "C7-": ("good_news_drop", "-", "event"), "C7+": ("bad_news_rise", "+", "event"),
    "C8-": ("crash_alert", "alert", "alert"), "C8+": ("spike_alert", "alert", "alert"),
}
# Card trigger evaluation kinds (registry card_triggers[].kind) -> merge group, and the common rule a card
# definition replaces (card definition first). ema_below and ema_below_unrecovered (V3, S5) add to the group.
CARD_KINDS = {
    "ema_below": ("trend_break", None),
    "ema20_below_twice": ("trend_break", "C3-"),
    "ema_below_unrecovered": ("trend_break", None),
    "new_high_hold": ("new_high", "C5+"),
    "pullback_rebound": ("pullback_rebound", "C6+"),
    "good_news_drop": ("good_news_drop", "C7-"),
    "drop_alert": ("crash_alert", "C8-"),
    "close_at_or_below": ("stop_reference", None),
    "earnings_notice": (None, None), "log_only": (None, None), "display_only": (None, None),
}
GROUP_NAMES = {
    "overheat": "\uac15\uc138 \uacfc\uc5f4", "oversold": "\uc57d\uc138 \uacfc\ub9e4\ub3c4",
    "overheat_fade": "\uacfc\uc5f4 \ub4a4 \ubc00\ub9bc", "oversold_rebound": "\uacfc\ub9e4\ub3c4 \ub4a4 \ubc18\ub4f1",
    "trend_break": "\ucd94\uc138\uc120 \uc774\ud0c8", "trend_recover": "\ucd94\uc138 \ud68c\ubcf5",
    "false_breakout": "\uac00\uc9dc \ub3cc\ud30c", "false_breakdown": "\uac00\uc9dc \ubd95\uad34",
    "new_low": "\uc2e0\uc800\uac00 \uc774\ud0c8", "new_high": "\uc2e0\uace0\uac00 \ub3cc\ud30c",
    "rebound_fail": "\ubc18\ub4f1 \uc2e4\ud328", "pullback_rebound": "\ub20c\ub9bc \ubc18\ub4f1",
    "good_news_drop": "\ud638\uc7ac \ub4a4 \ud558\ub77d", "bad_news_rise": "\uc545\uc7ac \ub4a4 \uc0c1\uc2b9",
    "crash_alert": "\uae09\ub77d \uacbd\ubcf4", "spike_alert": "\uae09\ub4f1 \uacbd\ubcf4",
    "stop_reference": "\uc190\uc808 \ucc38\uace0\uc120",
}
OFFICIAL_MINUS_KINDS = ("kill", "dilution", "customer_change", "guidance")
C7_PLUS_KINDS = ("guidance", "dilution", "contract", "customer_change")
EVIDENCE_STATES = ("hit",)


# ---------------------------------------------------------------------------------------------
# Three-valued helpers (None = unknown)
# ---------------------------------------------------------------------------------------------

def _all(*values: bool | None) -> bool | None:
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def _any(*values: bool | None) -> bool | None:
    if any(value is True for value in values):
        return True
    return None if any(value is None for value in values) else False


# Binary floating point cannot hold a line such as 100 x 1.015 exactly; values this close count as equal, so an
# inclusive line ("<=", ">=") includes it and a strict one excludes it. A representation tolerance, not a threshold.
FLOAT_EQUAL = 1e-9


def _cmp(left: float | None, op: str, right: float | None) -> bool | None:
    if left is None or right is None:
        return None
    return {"ge": left >= right - FLOAT_EQUAL, "le": left <= right + FLOAT_EQUAL,
            "gt": left > right + FLOAT_EQUAL, "lt": left < right - FLOAT_EQUAL}[op]


def _at(values: list[Any], index: int) -> Any:
    return values[index] if 0 <= index < len(values) else None


def _f(value: Any) -> float | None:
    return None if value is None else float(value)


# ---------------------------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------------------------

def ema_series(values: list[float | None], period: int) -> list[float | None]:
    """Standard EMA, seeded with the simple mean of the first `period` values; None before that."""
    out: list[float | None] = [None] * len(values)
    if len(values) < period or any(value is None for value in values[:period]):
        return out
    alpha = 2.0 / (period + 1)
    current = math.fsum(values[:period]) / period
    out[period - 1] = current
    for index in range(period, len(values)):
        if values[index] is None:
            return out
        current = alpha * values[index] + (1 - alpha) * current
        out[index] = current
    return out


def rsi_series(closes: list[float], period: int) -> list[float | None]:
    """Wilder RSI: seed = mean gain/loss of the first `period` changes, then (previous x (n-1) + new) / n."""
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    changes = [closes[index] - closes[index - 1] for index in range(1, len(closes))]
    gain = math.fsum(max(change, 0.0) for change in changes[:period]) / period
    loss = math.fsum(max(-change, 0.0) for change in changes[:period]) / period

    def value(average_gain: float, average_loss: float) -> float:
        return 100.0 if average_loss == 0 else 100.0 - 100.0 / (1.0 + average_gain / average_loss)

    out[period] = value(gain, loss)
    for index in range(period + 1, len(closes)):
        change = changes[index - 1]
        gain = (gain * (period - 1) + max(change, 0.0)) / period
        loss = (loss * (period - 1) + max(-change, 0.0)) / period
        out[index] = value(gain, loss)
    return out


def atr_series(highs: list[float | None], lows: list[float | None], closes: list[float], period: int
               ) -> list[float | None]:
    """Wilder ATR on regular-session high/low and the previous close. An incomplete session breaks the
    chain: the ATR is unknown until `period` consecutive true ranges exist again (no value is made up)."""
    out: list[float | None] = [None] * len(closes)
    run: list[float] = []
    current: float | None = None
    for index in range(1, len(closes)):
        high, low = highs[index], lows[index]
        if high is None or low is None:
            run, current = [], None
            continue
        previous = closes[index - 1]
        true_range = max(high - low, abs(high - previous), abs(low - previous))
        if current is None:
            run.append(true_range)
            if len(run) == period:
                current = math.fsum(run) / period
        else:
            current = (current * (period - 1) + true_range) / period
        out[index] = current
    return out


def build_series(bars: dict[str, Any], calendar_sessions: list[str], through: str) -> dict[str, Any] | None:
    """Indicator series over the contiguous run of sessions ending at `through` (None when it is missing)."""
    sessions = bars["sessions"]
    if through not in sessions:
        return None
    days = sorted(day for day in sessions if day <= through)
    order = {day: index for index, day in enumerate(calendar_sessions)}
    start = 0
    for index in range(1, len(days)):
        if days[index] not in order or days[index - 1] not in order or order[days[index]] - order[days[index - 1]] != 1:
            start = index
    days = days[start:]
    close = [float(sessions[day]["close"]) for day in days]
    high = [_f(sessions[day]["high"]) for day in days]
    low = [_f(sessions[day]["low"]) for day in days]
    volume = [_f(sessions[day]["volume"]) for day in days]
    lookback, sigma_n = C["LOOKBACK_SESSIONS"], C["SIGMA_SESSIONS"]
    ret1 = [None] + [close[index] / close[index - 1] - 1 for index in range(1, len(close))]
    ret5 = [None if index < 5 else close[index] / close[index - 5] - 1 for index in range(len(close))]
    sigma = [None] * len(close)
    for index in range(sigma_n, len(close)):
        sigma[index] = _sample_std(ret1[index - sigma_n + 1:index + 1])
    hi20 = [None if index < lookback else max(close[index - lookback:index]) for index in range(len(close))]
    lo20 = [None if index < lookback else min(close[index - lookback:index]) for index in range(len(close))]
    avgv20 = [None if index < lookback or any(item is None for item in volume[index - lookback:index])
              else math.fsum(volume[index - lookback:index]) / lookback for index in range(len(close))]
    position = [None if high[index] is None or low[index] is None else
                (0.5 if high[index] == low[index] else (close[index] - low[index]) / (high[index] - low[index]))
                for index in range(len(close))]
    return {
        "days": days, "close": close, "high": high, "low": low, "volume": volume, "ret1": ret1, "ret5": ret5,
        "sigma60": sigma, "hi20": hi20, "lo20": lo20, "avgv20": avgv20, "position": position,
        "ema10": ema_series(close, C["EMA_SHORT"]), "ema20": ema_series(close, C["EMA_MID"]),
        "ema50": ema_series(close, C["EMA_LONG"]), "rsi14": rsi_series(close, C["RSI_PERIOD"]),
        "atr14": atr_series(high, low, close, C["ATR_PERIOD"]),
    }


def indicator_row(series: dict[str, Any], index: int) -> dict[str, Any]:
    """Display row at one index (approximate close; intraday drop is display only)."""
    close, previous = series["close"][index], _at(series["close"], index - 1)
    sigma, low = series["sigma60"][index], series["low"][index]
    drop = None if low is None or previous is None else low / previous - 1
    return {
        "session": series["days"][index], "close": close, "previous_close": previous,
        "change": series["ret1"][index], "ema10": series["ema10"][index], "ema20": series["ema20"][index],
        "ema50": series["ema50"][index], "rsi14": series["rsi14"][index], "atr14": series["atr14"][index],
        "sigma60": sigma, "close_high_20": series["hi20"][index], "close_low_20": series["lo20"][index],
        "average_volume_20": series["avgv20"][index], "volume": series["volume"][index],
        "regular_high": series["high"][index], "regular_low": low, "close_position": series["position"][index],
        "intraday_drop": drop, "intraday_drop_sigma": None if drop is None or not sigma else drop / sigma,
        "approximate_close": True,
    }


# ---------------------------------------------------------------------------------------------
# Raw conditions (per session index) and states
# ---------------------------------------------------------------------------------------------

def _runs(flags: list[bool | None]) -> list[int | None]:
    """Length of the run of True ending at each index (None when unknown inside the run)."""
    out: list[int | None] = []
    run: int | None = 0
    for flag in flags:
        if flag is None:
            run = None
        elif flag:
            run = None if run is None else run + 1
        else:
            run = 0
        out.append(run)
    return out


def raw_common(series: dict[str, Any], c8: dict[str, float | None]) -> dict[str, list[bool | None]]:
    """Each common rule's raw condition at every index (event rules: fired that session)."""
    s, n = series, len(series["close"])
    close, e20, atr = s["close"], s["ema20"], s["atr14"]
    band1, band2 = C["C1_ATR_BAND"], C["C2_ATR_BAND"]
    raw: dict[str, list[bool | None]] = {key: [None] * n for key in COMMON_RULES}
    below = [_cmp(close[i], "lt", e20[i]) for i in range(n)]
    above = [_cmp(close[i], "gt", e20[i]) for i in range(n)]
    below_run, above_run = _runs(below), _runs(above)
    for i in range(n):
        p_e20, p_atr = _at(e20, i - 1), _at(atr, i - 1)
        up1 = None if p_e20 is None or p_atr is None else p_e20 + band1 * p_atr
        dn1 = None if p_e20 is None or p_atr is None else p_e20 - band1 * p_atr
        up2 = None if p_e20 is None or p_atr is None else p_e20 + band2 * p_atr
        dn2 = None if p_e20 is None or p_atr is None else p_e20 - band2 * p_atr
        rsi = s["rsi14"][i]
        raw["C1-"][i] = _any(_cmp(rsi, "ge", C["RSI_OVERBOUGHT"]), _cmp(close[i], "ge", up1))
        raw["C1+"][i] = _any(_cmp(rsi, "le", C["RSI_OVERSOLD"]), _cmp(close[i], "le", dn1))
        volume_ok = (None if s["volume"][i] is None or s["avgv20"][i] is None
                     else s["volume"][i] >= C["C2_VOLUME_RATIO"] * s["avgv20"][i])
        raw["C2-"][i] = _all(_cmp(s["high"][i], "ge", up2), _cmp(s["position"][i], "le", C["C2_FADE_POSITION"]),
                             volume_ok)
        raw["C2+"][i] = _all(_cmp(s["low"][i], "le", dn2), _cmp(s["position"][i], "ge", C["C2_REBOUND_POSITION"]),
                             volume_ok)
        for rule, runs, other in (("C3-", below_run, above), ("C3+", above_run, below)):
            run = runs[i]
            if run is None:
                raw[rule][i] = None
            elif run < 2:
                raw[rule][i] = False
            else:
                raw[rule][i] = _at(other, i - run)  # the close before the run is on the other side
        line_high, line_low = _at(s["hi20"], i - 1), _at(s["lo20"], i - 1)
        raw["C4-"][i] = _all(_cmp(_at(close, i - 1), "gt", line_high), _cmp(close[i], "lt", line_high))
        raw["C4+"][i] = _all(_cmp(_at(close, i - 1), "lt", line_low), _cmp(close[i], "gt", line_low))
        band = C["C6_BAND"]
        p_close, pp_close, pp_e20 = _at(close, i - 1), _at(close, i - 2), _at(e20, i - 2)
        raw["C6-"][i] = _all(_cmp(pp_close, "lt", pp_e20), _cmp(p_close, "lt", p_e20),
                             _cmp(p_close, "ge", None if p_e20 is None else p_e20 * (1 - band)),
                             _cmp(close[i], "lt", p_close), _cmp(close[i], "lt", e20[i]))
        raw["C6+"][i] = _all(_cmp(pp_close, "gt", pp_e20), _cmp(p_close, "gt", p_e20),
                             _cmp(p_close, "le", None if p_e20 is None else p_e20 * (1 + band)),
                             _cmp(close[i], "gt", p_close), _cmp(close[i], "gt", e20[i]))
        one, five = c8.get("one_day"), c8.get("five_day")
        raw["C8-"][i] = _any(_cmp(s["ret1"][i], "le", None if one is None else -one),
                             False if five is None else _cmp(s["ret5"][i], "le", -five))
        raw["C8+"][i] = _any(_cmp(s["ret1"][i], "ge", one),
                             False if five is None else _cmp(s["ret5"][i], "ge", five))
    raw["C5-"], raw["C5+"] = _hold_state(series, "-"), _hold_state(series, "+")
    return raw


def _hold_state(series: dict[str, Any], side: str) -> list[str | None]:
    """C5 two-session hold, per index: 'hit', 'pending', 'fail' (breakout failed), 'none' or None.

    Session 1: close beyond the prior 20-session close line (low for -, high for +) and beyond EMA10 = pending,
    with that line fixed. Session 2 on the same side of the same line and EMA10 = hit; it stays hit while both
    hold. Back across the line in between = 'fail' (a failed breakout, not counted).
    """
    close, ema10 = series["close"], series["ema10"]
    line_series = series["lo20"] if side == "-" else series["hi20"]
    op = "lt" if side == "-" else "gt"
    out: list[str | None] = []
    state, line = "none", None
    for i in range(len(close)):
        if state in ("pending", "hit") and line is not None:
            holds = _all(_cmp(close[i], op, line), _cmp(close[i], op, ema10[i]))
            if holds is None:
                out.append(None)
                state, line = "none", None
                continue
            if holds:
                state = "hit"
                out.append("hit")
                continue
            crossed = _cmp(close[i], "gt" if side == "-" else "lt", line)
            state, line = "none", None
            if crossed:
                out.append("fail")
                continue
        start = _all(_cmp(close[i], op, line_series[i]), _cmp(close[i], op, ema10[i]))
        if start is None:
            out.append(None)
        elif start:
            state, line = "pending", line_series[i]
            out.append("pending")
        else:
            out.append("none")
    return out


def _event_state(raw: list[bool | None], opposite: list[bool | None] | None, index: int) -> str:
    """Event rule at `index`: hit when it fired within the 5-session window (incl. the day) and the
    opposite side of the same number has not fired since; unk when nothing fired and a day is unknown."""
    window = C["EVENT_WINDOW_SESSIONS"]
    fired = [i for i in range(max(0, index - window + 1), index + 1) if raw[i] is True]
    if fired:
        last = fired[-1]
        if opposite is not None and any(opposite[i] is True for i in range(last + 1, index + 1)):
            return "none"
        return "hit"
    if index - window + 1 < 0 or any(raw[i] is None for i in range(max(0, index - window + 1), index + 1)):
        return "unk"
    return "none"


def _state(value: Any) -> str:
    if value is None:
        return "unk"
    if value in ("hit", "pending", "none"):
        return value
    if value == "fail":
        return "none"
    return "hit" if value is True else "none"


# ---------------------------------------------------------------------------------------------
# C7 from official facts
# ---------------------------------------------------------------------------------------------

def _base_index(series: dict[str, Any], calendar: dict[str, Any], announced_at: str) -> int | None:
    """Index of the last session whose regular close is before the announcement time."""
    try:
        moment = datetime.fromisoformat(announced_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    best = None
    for index, day in enumerate(series["days"]):
        row = calendar["sessions"].get(day)
        if row is not None and datetime.fromisoformat(row["core_close_at"]) < moment:
            best = index
    return best


def raw_c7(series: dict[str, Any], calendar: dict[str, Any], facts: list[dict[str, Any]] | None
           ) -> tuple[list[bool | None], list[bool | None], list[dict[str, Any]]]:
    """C7- (official good news, criterion (a), then a close below the pre-announcement close within 2
    sessions) and C7+ (the company's own quantified bad news, then a close above it). None facts = unknown."""
    n = len(series["close"])
    if facts is None:
        return [None] * n, [None] * n, []
    minus, plus = [False] * n, [False] * n
    notes = []
    for fact in facts:
        good = fact["direction"] == "+" and fact.get("criterion_a") is True
        bad = fact["direction"] == "-" and fact["kind"] in C7_PLUS_KINDS
        if not (good or bad):
            continue
        base = _base_index(series, calendar, fact["announced_at"])
        if base is None:
            continue
        reference = series["close"][base]
        for index in range(base + 1, min(n, base + 1 + C["C7_REACTION_SESSIONS"])):
            if good and series["close"][index] < reference:
                minus[index] = True
                notes.append({"rule": "C7-", "fact_id": fact["fact_id"], "session": series["days"][index],
                              "reference_close": reference})
                break
            if bad and series["close"][index] > reference:
                plus[index] = True
                notes.append({"rule": "C7+", "fact_id": fact["fact_id"], "session": series["days"][index],
                              "reference_close": reference})
                break
    return minus, plus, notes


# ---------------------------------------------------------------------------------------------
# Card triggers
# ---------------------------------------------------------------------------------------------

def card_raw(trigger: dict[str, Any], series: dict[str, Any], common: dict[str, list[Any]]) -> list[Any]:
    """Raw value per index of one card price trigger (registry kind and params)."""
    kind, params = trigger["kind"], trigger.get("params") or {}
    close, n = series["close"], len(series["close"])
    if kind == "ema_below":
        ema = series[f"ema{int(params['ema'])}"]
        return [_cmp(close[i], "lt", ema[i]) for i in range(n)]
    if kind == "ema20_below_twice":
        runs = _runs([_cmp(close[i], "lt", series["ema20"][i]) for i in range(n)])
        return [None if run is None else run >= 2 for run in runs]
    if kind == "ema_below_unrecovered":
        ema = series[f"ema{int(params['ema'])}"]
        runs = _runs([_cmp(close[i], "lt", ema[i]) for i in range(n)])
        need = int(params["sessions"]) + 1  # the closing below, then `sessions` sessions without a recovery
        return [None if run is None else ("hit" if run >= need else "pending" if run >= 1 else "none")
                for run in runs]
    if kind == "close_at_or_below":
        price = float(params["price"])
        return [_cmp(close[i], "le", price) for i in range(n)]
    if kind == "drop_alert":
        one, five = params.get("one_day"), params.get("five_day")
        return [_any(_cmp(series["ret1"][i], "le", None if one is None else -float(one)),
                     False if five is None else _cmp(series["ret5"][i], "le", -float(five))) for i in range(n)]
    if kind == "new_high_hold":
        return list(common["C5+"])
    if kind == "pullback_rebound":
        return list(common["C6+"])
    if kind == "good_news_drop":
        return list(common["C7-"])
    return [None] * n


def _status(rule_kind: str, values: list[Any], index: int, opposite: list[Any] | None = None) -> str:
    if index < 0:
        return "unk"
    if rule_kind == "event":
        return _event_state(values, opposite, index)
    return _state(values[index])


# ---------------------------------------------------------------------------------------------
# One symbol
# ---------------------------------------------------------------------------------------------

def c8_thresholds(registry_entry: dict[str, Any] | None, multiplier: Any) -> dict[str, float | None]:
    if registry_entry and isinstance(registry_entry.get("c8"), dict):
        return {"one_day": registry_entry["c8"].get("one_day"), "five_day": registry_entry["c8"].get("five_day")}
    table = C["C8_BY_MULTIPLIER"]
    try:
        key = int(multiplier)
    except (TypeError, ValueError):
        key = None
    return {"one_day": table.get(key, C["C8_UNKNOWN_MULTIPLIER"]), "five_day": None}


def evaluate_symbol(*, symbol: str, role: str, bars: dict[str, Any] | None, calendar: dict[str, Any],
                    evaluation_session: str, registry_entry: dict[str, Any] | None, held: bool, member: bool,
                    multiplier: Any, facts: list[dict[str, Any]] | None, buy_approved: bool) -> dict[str, Any]:
    """Indicators, every trigger state at the evaluation session (and whether it is new today), and the
    merged groups that count as evidence. Data problems keep the symbol visible with unk states."""
    result: dict[str, Any] = {"symbol": symbol, "role": role, "status": "OK", "reasons": [], "indicators": None,
                              "triggers": [], "groups": {}, "c7_notes": [], "buy_approved": buy_approved,
                              "nocard": held and registry_entry is None}
    usable = bars is not None and bars.get("status") == "OK" and not bars.get("split_suspects")
    if bars is None or bars.get("status") != "OK":
        result["reasons"].append(f"BARS_{(bars or {}).get('status', 'MISSING')}")
    if bars is not None and bars.get("split_suspects"):
        result["reasons"].extend(bars["split_suspects"])
    series = build_series(bars["adjusted"], sorted(calendar["sessions"]), evaluation_session) if usable else None
    if series is None:
        if usable:
            result["reasons"].append(f"CLOSE_MISSING:{evaluation_session}")
        result["status"] = "UNK"
    t = len(series["close"]) - 1 if series is not None else -1
    c8 = c8_thresholds(registry_entry, multiplier)
    if series is not None:
        result["indicators"] = indicator_row(series, t)
        result["margins"] = group_margins(series, c8)
    common = raw_common(series, c8) if series is not None else {key: [] for key in COMMON_RULES}
    if series is not None:
        minus, plus, notes = raw_c7(series, calendar, facts)
        common["C7-"], common["C7+"] = minus, plus
        result["c7_notes"] = notes

    def status_pair(rule_kind: str, values: list[Any], opposite: list[Any] | None = None) -> tuple[str, str]:
        if series is None:
            return "unk", "unk"
        return _status(rule_kind, values, t, opposite), _status(rule_kind, values, t - 1, opposite)

    card_active = []
    if registry_entry is not None:
        for trigger in registry_entry.get("card_triggers") or []:
            when = trigger.get("active_when")
            if (when == "held" and held) or (when == "member" and member) or (
                    when == "held_or_member" and (held or member)):
                card_active.append(trigger)
    replaced = {CARD_KINDS[trigger["kind"]][1] for trigger in card_active if trigger["kind"] in CARD_KINDS}
    groups: dict[str, dict[str, Any]] = {}

    def add(rule_id: str, group: str | None, side: str, today: str, yesterday: str, source: str,
            card_defined: bool, strength: str) -> None:
        if side == "alert" and today == "hit":
            today = "review"
        if side == "alert" and yesterday == "hit":
            yesterday = "review"
        item = {"id": rule_id, "group": group, "name": GROUP_NAMES.get(group or "", rule_id), "side": side,
                "state": today, "previous_state": yesterday, "new": today in ("hit", "review") and yesterday != today,
                "source": source, "card_defined": card_defined, "strength": strength}
        if side == "+" and not buy_approved:
            item["note"] = "BUY_NOT_APPROVED_INSTRUMENT"
        result["triggers"].append(item)
        if group is None:
            return
        entry = groups.setdefault(group, {"group": group, "side": side, "state": "none", "previous_state": "none",
                                          "ids": [], "card_defined": False})
        entry["ids"].append(rule_id)
        entry["card_defined"] = entry["card_defined"] or card_defined
        rank = {"hit": 5, "review": 5, "pending": 3, "near": 3, "unk": 2, "none": 1}
        if rank.get(today, 0) > rank.get(entry["state"], 0):
            entry["state"] = today
        if rank.get(yesterday, 0) > rank.get(entry["previous_state"], 0):
            entry["previous_state"] = yesterday

    opposite = {"C2-": "C2+", "C2+": "C2-", "C4-": "C4+", "C4+": "C4-", "C6-": "C6+", "C6+": "C6-",
                "C7-": "C7+", "C7+": "C7-"}
    for rule_id, (group, side, rule_kind) in COMMON_RULES.items():
        if rule_id in replaced:
            continue
        today, yesterday = status_pair(rule_kind, common.get(rule_id, []),
                                       common.get(opposite[rule_id]) if rule_id in opposite else None)
        add(rule_id, group, side, today, yesterday, "common", False, "weak" if side in "+-" else "review")
    for trigger in card_active:
        group, replaces = CARD_KINDS.get(trigger["kind"], (None, None))
        side = trigger.get("side")
        values = card_raw(trigger, series, common) if series is not None else []
        rule_kind = "event" if trigger["kind"] in ("pullback_rebound", "good_news_drop") else "state"
        if trigger["kind"] in ("earnings_notice", "log_only", "display_only"):
            today, yesterday = "info", "info"
        else:
            # A card alias of an event rule is resolved by the opposite side of the same number, like the rule.
            today, yesterday = status_pair(rule_kind, values,
                                           common.get(opposite[replaces]) if replaces in opposite else None)
        add(trigger["id"], group, "alert" if side == "alert" else side, today, yesterday, "card", True,
            trigger.get("strength", "weak"))
    result["groups"] = groups
    if result["nocard"]:
        result["triggers"].append({"id": "NOCARD", "group": None, "name": "\uce74\ub4dc \uc5c6\uc74c",
                                   "side": "alert", "state": "review", "previous_state": None, "new": False,
                                   "source": "registry", "card_defined": False, "strength": "review"})
    return result


def group_margins(series: dict[str, Any], c8: dict[str, float | None]) -> dict[str, float | None]:
    """Relative distance (share of the close) of each group's deciding quantity to its line at the last session;
    used only to label a judgment difference DATA_DEFINITION (F9, prompt appendix B). Display only."""
    t = len(series["close"]) - 1
    close = series["close"][t]
    p_e20, p_atr = _at(series["ema20"], t - 1), _at(series["atr14"], t - 1)

    def gap(value: float | None, line: float | None) -> float | None:
        return None if value is None or line is None or not close else abs(value - line) / close

    def least(*values: float | None) -> float | None:
        known = [value for value in values if value is not None]
        return min(known) if known else None

    band1 = None if p_e20 is None or p_atr is None else C["C1_ATR_BAND"] * p_atr
    band2 = None if p_e20 is None or p_atr is None else C["C2_ATR_BAND"] * p_atr
    e20, e10 = series["ema20"][t], series["ema10"][t]
    hi_prev, lo_prev = _at(series["hi20"], t - 1), _at(series["lo20"], t - 1)
    rsi = series["rsi14"][t]
    one = c8.get("one_day")
    ret = series["ret1"][t]
    return {
        "overheat": gap(close, None if band1 is None else p_e20 + band1),
        "oversold": gap(close, None if band1 is None else p_e20 - band1),
        "overheat_fade": gap(series["high"][t], None if band2 is None else p_e20 + band2),
        "oversold_rebound": gap(series["low"][t], None if band2 is None else p_e20 - band2),
        "trend_break": gap(close, e20), "trend_recover": gap(close, e20),
        "false_breakout": gap(close, hi_prev), "false_breakdown": gap(close, lo_prev),
        "new_high": least(gap(close, series["hi20"][t]), gap(close, e10)),
        "new_low": least(gap(close, series["lo20"][t]), gap(close, e10)),
        "rebound_fail": gap(close, e20), "pullback_rebound": gap(close, e20),
        "crash_alert": None if ret is None or one is None else abs(abs(ret) - one),
        "spike_alert": None if ret is None or one is None else abs(abs(ret) - one),
        "rsi_gap": None if rsi is None else min(abs(rsi - C["RSI_OVERBOUGHT"]), abs(rsi - C["RSI_OVERSOLD"])),
    }


def price_evidence(result: dict[str, Any], side: str) -> dict[str, Any]:
    """Merged groups of one side that are hit: one per group (card definition first, rule file 3))."""
    hits = [group for group in result["groups"].values() if group["side"] == side and group["state"] == "hit"]
    new = [group for group in hits if group["previous_state"] != "hit"]
    return {"groups": sorted(group["group"] for group in hits), "new_groups": sorted(group["group"] for group in new),
            "card_defined": any(group["card_defined"] for group in hits),
            "ids": sorted(rule for group in hits for rule in group["ids"])}


# ---------------------------------------------------------------------------------------------
# Account line V6 and R5 near
# ---------------------------------------------------------------------------------------------

def v6_account(total: Decimal | None, s7_hwm: Any = None) -> dict[str, Any]:
    if total is None:
        return {"state": "unk", "total": None, "reason": "TOTAL_UNAVAILABLE", "s7_hwm_usd": s7_hwm}
    first, approach, maximum = C["V6_FIRST_LINE_USD"], C["V6_APPROACH_USD"], C["V6_MAX_LINE_USD"]
    state = "review" if total <= first else "near" if total <= approach else "none"
    return {"state": state, "total": float(total), "hwm": float(C["V6_HWM_USD"]), "first": float(first),
            "approach": float(approach), "max": float(maximum), "max_reached": total <= maximum,
            "first_cushion_pct": float(total / first - 1), "hwm_candidate": total > C["V6_HWM_USD"],
            "s7_hwm_usd": s7_hwm}


def ev4_open(total: Decimal | None, s7_hwm: Any) -> bool:
    """R-REC1 EV4 of one session: total <= the V6 first line or <= S7 hwm_usd x 0.9 (r2 R2-3: decide and the
    replay both get it from here, before R-REC1 is computed). An unknown total is not an EV4 day; the rule-file N
    is then unknown too and buy requirement (2) already blocks buys."""
    if total is None:
        return False
    return total <= C["V6_FIRST_LINE_USD"] or (
        s7_hwm is not None and total <= Decimal(str(s7_hwm)) * C["RREC_EV4_HWM_FRACTION"])


def r5_state(peak_item: dict[str, Any]) -> str:
    if peak_item.get("status") == "REVIEW_OPEN":
        return "review"
    peak, close = peak_item.get("peak"), peak_item.get("close")
    if peak is None or close is None:
        return "unk"
    return "near" if Decimal(str(close)) <= Decimal(str(peak)) * C["R5_NEAR_FRACTION"] else "none"


# ---------------------------------------------------------------------------------------------
# R-REC1 (prompt A-4)
# ---------------------------------------------------------------------------------------------

def ev3_dates(text: str) -> list[str]:
    return sorted({match.group(1) for line in text.splitlines() if (match := EV3_LINE.match(line))})


def rrec1(*, benchmark: dict[str, Any] | None, candidate: dict[str, Any] | None, evaluation_session: str,
          ev3_user_dates: list[str], thesis_damage: list[dict[str, Any]] | None, ev4_sessions: list[str],
          candidate_symbol: str | None = None, research_sessions: Any = None) -> dict[str, Any]:
    """Shock event and recovery gates for one candidate. benchmark/candidate are build_series outputs.

    thesis_damage: official facts with root_thesis_damage from the research records covering the R-REC1 window
    (None = no research record -> RG1 unknown). ev4_sessions: sessions on which the account line EV4 was open
    (earlier decide records and, r2 R2-3, the evaluation session itself). research_sessions (r2 R2-4): the
    sessions that have a valid research record; None = not tracked (every session is taken as recorded). With
    it, RG1 needs a record for every session after the event (else unknown, rg1_coverage), and a session
    without a record after the first recorded one (ev3b_coverage_start) on which the benchmark fell at least
    1 sigma60 (EV3 (b) could have opened) makes the result unknown. Data missing = "unk": an
    exposure-increasing buy is blocked; a sell is never blocked by this gate.
    """
    out: dict[str, Any] = {"status": "unk", "open": None, "events": [], "event": None, "rg": {}, "ds1": None,
                           "benchmark": None, "reasons": [], "ev3b_coverage_start": None, "rg1_coverage": None}
    if benchmark is None or benchmark["days"][-1] != evaluation_session:
        out["reasons"].append("BENCHMARK_DATA_MISSING")
        return out
    s = benchmark
    t = len(s["close"]) - 1
    if s["sigma60"][t] is None:
        out["reasons"].append("BENCHMARK_SIGMA_UNAVAILABLE")
        return out
    window_start = max(0, t - C["RREC_WINDOW_SESSIONS"] + 1)
    coverage = None if research_sessions is None else set(research_sessions)
    gaps: list[str] = []
    if coverage is not None:
        recorded = [s["days"][i] for i in range(window_start, t + 1) if s["days"][i] in coverage]
        out["ev3b_coverage_start"] = recorded[0] if recorded else None
        # Before the first record EV3 (a) (the user-designated dates) covers the window; after it, a missing
        # record on a day the benchmark fell 1 sigma60 or more (or an unknown day) could hide an EV3 (b) event.
        for i in range(window_start, t + 1):
            day, sigma, ret = s["days"][i], s["sigma60"][i], s["ret1"][i]
            if recorded and day >= recorded[0] and day not in coverage and (
                    sigma is None or ret is None or ret <= -C["RREC_EV3_SIGMA"] * sigma):
                gaps.append(day)

    def settle(result: dict[str, Any]) -> dict[str, Any]:
        if gaps:
            result.update(status="unk", open=None)
            result["reasons"].append("EV3B_RECORD_GAP:" + ",".join(gaps))
        return result

    damage_days = {fact["event_session"] for fact in thesis_damage or []}
    events = []
    for i in range(window_start, t + 1):
        sigma, ret = s["sigma60"][i], s["ret1"][i]
        day = s["days"][i]
        kinds = []
        if sigma is not None and ret is not None and ret <= -C["RREC_EV1_SIGMA"] * sigma:
            kinds.append("EV1")
        if sigma is not None and s["hi20"][i] is not None and s["close"][i] <= s["hi20"][i] * (1 - C["RREC_EV2_SIGMA"] * sigma):
            kinds.append("EV2")
        if day in ev3_user_dates:
            kinds.append("EV3a")
        if day in damage_days and sigma is not None and ret is not None and ret <= -C["RREC_EV3_SIGMA"] * sigma:
            kinds.append("EV3b")
        if day in ev4_sessions:
            kinds.append("EV4")
        if candidate is not None and day in candidate["days"]:
            j = candidate["days"].index(day)
            c_sigma, c_ret = candidate["sigma60"][j], candidate["ret1"][j]
            if c_sigma is not None and c_ret is not None and c_ret <= -C["RREC_EV5_SIGMA"] * c_sigma:
                kinds.append("EV5")
        if kinds:
            events.append({"index": i, "date": day, "kinds": kinds})
    out["events"] = [{"date": item["date"], "kinds": item["kinds"]} for item in events]
    if not events:
        out.update(status="ok", open=False)
        return settle(out)
    event = events[-1]
    e = event["index"]
    c0 = s["close"][e]
    l0 = s["low"][e]
    out["event"] = {"date": event["date"], "kinds": event["kinds"], "c0": c0, "l0": l0, "bench": None}
    if coverage is not None:
        out["rg1_coverage"] = {"from": s["days"][e + 1] if e < t else None, "to": s["days"][t],
                               "missing_sessions": [s["days"][k] for k in range(e + 1, t + 1)
                                                    if s["days"][k] not in coverage]}
    if l0 is None:
        out["reasons"].append("EVENT_LOW_UNAVAILABLE")
        out.update(status="unk", open=True)
        return settle(out)

    def ds1(i: int) -> bool | None:
        return _any(_cmp(s["close"][i], "lt", l0), _cmp(s["close"][i], "lt", s["ema50"][i]))

    def gates(i: int, last_ds1: int) -> dict[str, bool | None]:
        damage_after = None if thesis_damage is None else any(
            fact["event_session"] > s["days"][e] and fact["event_session"] <= s["days"][i] for fact in thesis_damage)
        # RG1 needs a research record for every session after the event (r2 R2-4); a known damage fact is "no".
        recorded = coverage is None or all(s["days"][k] in coverage for k in range(e + 1, i + 1))
        rg1 = None if damage_after is None else False if damage_after else _all(
            i - e >= C["RREC_RG1_SESSIONS"], True if recorded else None)
        bench_ok = _cmp(s["close"][i], "ge", s["ema50"][i])
        cand_ok = None
        if candidate is not None and s["days"][i] in candidate["days"]:
            j = candidate["days"].index(s["days"][i])
            cand_ok = _cmp(candidate["close"][j], "ge", candidate["ema50"][j])
        rg2 = _all(bench_ok, cand_ok) if candidate is not None else bench_ok
        start = max(e, last_ds1)
        lows = [s["low"][k] for k in range(start + 1, i + 1)]
        no_new_low = None if any(low is None for low in lows) else all(low >= l0 for low in lows)
        two = C["RREC_RG3_SESSIONS"]
        rg3 = _all(i - start >= two, _all(*[_cmp(s["close"][k], "gt", c0) for k in range(i - two + 1, i + 1)])
                   if i - start >= two else False, no_new_low)
        sigma, ret = s["sigma60"][i], s["ret1"][i]
        short = s["ret1"][i - C["RREC_RG4_SHORT_SESSIONS"] + 1:i + 1]
        short_sigma = None if any(value is None for value in short) else _sample_std(short)
        rg4 = None if sigma is None or ret is None or short_sigma is None else (
            abs(ret) <= C["RREC_RG4_DAY_SIGMA"] * sigma and short_sigma <= C["RREC_RG4_SHORT_RATIO"] * sigma)
        return {"RG1": rg1, "RG2": rg2, "RG3": rg3, "RG4": rg4}

    last_ds1 = e
    ds1_seen = None
    closed_at = None
    current: dict[str, bool | None] = {}
    for i in range(e + 1, t + 1):
        flag = ds1(i)
        if flag:
            last_ds1, ds1_seen = i, s["days"][i]
        current = gates(i, last_ds1)
        if all(value is True for value in current.values()):
            closed_at = s["days"][i]
            break
        if i - last_ds1 >= C["RREC_CLOSE_SESSIONS"] and current["RG2"] is True:
            closed_at = s["days"][i]
            break
    if e == t:
        current = gates(t, e)
    out["ds1"] = ds1_seen
    out["rg"] = {key: ("ok" if value is True else "no" if value is False else "unk") for key, value in current.items()}
    if closed_at is not None:
        out.update(status="ok", open=False, closed_at=closed_at)
        return settle(out)
    out["open"] = True
    out["status"] = "ok" if all(value is True for value in current.values()) else (
        "unk" if any(value is None for value in current.values()) else "no")
    return settle(out)


def rg2_benchmark(sector: str | None) -> str:
    return C["RREC_POWER_BENCHMARK"] if (sector or "").startswith(POWER_SECTOR_PREFIX) else C["RREC_BENCHMARK"]


def m6_listed(symbol: str, documents: list[tuple[str, str]]) -> dict[str, Any]:
    """Buy requirement (4): a docs/claude/m6-relative-comparison-7stock*.md file mentions the code (grep -c)."""
    if not documents:
        return {"s": "no", "t": "\ub9c9\ud798 \u2014 \ube44\uad50 \uce74\ub4dc \uc5c6\uc74c", "file": None}
    for name, text in documents:
        if symbol in text:
            return {"s": "ok", "t": f"\ud1b5\uacfc ({name})", "file": name}
    return {"s": "no", "t": "\ub9c9\ud798 \u2014 \ube44\uad50 \uce74\ub4dc\uc5d0 \uc5c6\uc74c", "file": None}
