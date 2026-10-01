#!/usr/bin/env python3
"""Pure S5 (r2) portfolio exposure, review-line and recommendation calculations.

No file, clock or network access: every input is passed in and the same input gives the same output.
The result is display only. It carries target weights, never order quantities or amounts, and keeps
order_authority=false, quantity_authority="none", execution_quantity=null.

Rules (docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md, "S5 final proposal r2"):
  R0 common fail-closed      fail_closed triggers pause add and new-buy recommendations
  R1 exposure E = max(N, V)  nominal_exposure, sox_equivalent_ratio
  R2 risk budget and band    band_state, reduce and add recommendations, projected exposure <= target
  R3 composition             single-stock nominal cap, earnings blackout, MU -> DRAM substitution ban
  R4 HWM review lines        evaluate_review_lines
  R5 single-stock peak       evaluate_peak_reviews
  R6 cash-flow declaration   cash_flow_evidence.cash_flow_chain (hold when undeclared)
  R9 swap                    sell leg first; the buy leg needs verified cash
Threshold values come from alert_policy.json; this module never hard-codes or changes them.
"""

from __future__ import annotations

import math
from datetime import date
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any

from cash_flow_evidence import cash_flow_chain
from validation_common import canonical_hash


SCHEMA_VERSION = "portfolio-exposure-review-1.0"
ARTIFACT_TYPE = "PORTFOLIO_EXPOSURE_REVIEW"
EXPOSURE_SECTION = "portfolio_exposure_policy"
LINES_SECTION = "portfolio_review_lines"
ZERO = Decimal("0")
ONE = Decimal("1")
CENT = Decimal("0.01")
# Display resolution of target weights (0.1 percentage point). Targets are searched on this grid.
WEIGHT_STEP = Decimal("0.001")
# Data-integrity guard, not a strategy threshold: raw (unadjusted) closes are used, so a
# session-to-session close ratio at or beyond these bounds may be an unadjusted split.
SPLIT_GUARD_LOW = 0.5
SPLIT_GUARD_HIGH = 2.0
FAIL_CLOSED_TRIGGERS = (
    "exposure_or_equity_or_v_unavailable",
    "unregistered_instrument_held",
    "hwm_line_or_pause_state_missing_or_corrupt",
    "decision_journal_missing_or_corrupt",
    "broker_snapshot_older_than_broker_snapshot_max_age_calendar_days",
    "required_price_missing",
    "undeclared_cash_flow",
)
# User decision P2 (2026-10-01): the grades live in portfolio_exposure_policy.alert_grade_mapping.
# D is reused for the portfolio -20% line and the hard ceiling; an add recommendation is never above B.
GRADE_KEYS = (
    "REVIEW_LINE_WITHOUT_PAUSE", "REVIEW_LINE_WITH_PAUSE", "EXPOSURE_HARD_CEILING", "EXPOSURE_ABOVE_BAND",
    "PEAK_REVIEW", "FAIL_CLOSED_UNVERIFIED", "ADD_RECOMMENDATION",
)
ALLOWED_GRADES = ("B", "C", "D")
LATEST_SESSION_STATUS = "LATEST_COMPLETED_SESSION"
JOURNAL_ACTIVATION = "s5_activation"
JOURNAL_LINE_REVIEW = "line_review_completed"
JOURNAL_PEAK_REVIEW = "peak_review_card_completed"
CARD_REDUCE_ACTIONS = ("TRIM", "EXIT")


class ExposureError(ValueError):
    """Invalid policy or input shape. Data gaps are reported in the result, not raised."""


def _dec(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value.quantize(CENT):.2f}"


def _plain(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _num(value: Decimal | float | None, places: int = 6) -> float | None:
    return None if value is None else round(float(value), places)


def floor_to_step(value: Decimal) -> Decimal:
    return (value / WEIGHT_STEP).to_integral_value(rounding=ROUND_FLOOR) * WEIGHT_STEP


def exposure_config(policy: dict[str, Any]) -> dict[str, Any]:
    """Read both S5 sections. Missing or malformed values raise; nothing is defaulted."""
    section, lines = policy.get(EXPOSURE_SECTION), policy.get(LINES_SECTION)
    if not isinstance(section, dict) or not isinstance(lines, dict):
        raise ExposureError("S5_POLICY_SECTION_MISSING")
    try:
        if section["order_authority"] is not False or section["quantity_authority"] != "none" or (
                section["execution_quantity"] is not None):
            raise ExposureError("S5_POLICY_AUTHORITY_FIELDS_INVALID")
        thresholds = section["thresholds"]
        multipliers = {str(symbol): Decimal(str(value)) for symbol, value in section["nominal_multipliers"].items()
                       if symbol != "cash"}
        reduce_order = list(section["reduce_order"])
        supplement = str(reduce_order[-1])
        if supplement not in multipliers or section["add_default"] != f"card_add_stock_else_{supplement}":
            raise ExposureError("S5_POLICY_SUPPLEMENT_INSTRUMENT_INCONSISTENT")
        configured = [(str(item["id"]), Decimal(str(item["fraction_of_hwm"])), bool(item["pause_add_recommendations"]),
                       bool(item["pause_new_buy_recommendations"]), str(item["action"])) for item in lines["lines"]]
        grades = {str(key).upper(): str(value) for key, value in section["alert_grade_mapping"].items()}
        if sorted(grades) != sorted(GRADE_KEYS) or any(value not in ALLOWED_GRADES for value in grades.values()) or (
                grades["ADD_RECOMMENDATION"] != section["add_recommendation_classification"]["max_alert_grade"]):
            raise ExposureError("S5_POLICY_ALERT_GRADE_MAPPING_INVALID")
        step = Decimal(str(lines["further_lines_step"]))
        if not configured or step <= 0 or lines["further_lines_action"] != f"same_as_{configured[-1][0]}":
            raise ExposureError("S5_POLICY_REVIEW_LINES_INVALID")
        all_lines = [{"id": name, "fraction": fraction, "pause_add": pause_add, "pause_new_buy": pause_buy,
                      "action": action} for name, fraction, pause_add, pause_buy, action in configured]
        index, fraction = len(configured), configured[-1][1] - step
        while fraction > 0:
            index += 1
            all_lines.append({"id": f"L{index}", "fraction": fraction, "pause_add": configured[-1][2],
                              "pause_new_buy": configured[-1][3], "action": configured[-1][4]})
            fraction -= step
        return {
            "policy_version": str(section["policy_version"]), "status": str(section["status"]),
            "target": Decimal(str(section["target_exposure"])),
            "reduce_gte": Decimal(str(thresholds["reduce_when_exposure_gte"])),
            "add_lte": Decimal(str(thresholds["add_when_exposure_lte"])),
            "projected_lte": Decimal(str(thresholds["exposure_increasing_projected_exposure_lte"])),
            "hard_gte": Decimal(str(thresholds["hard_ceiling_when_exposure_gte"])),
            "multipliers": multipliers, "benchmark": str(section["sox_equivalent"]["benchmark"]),
            "window": int(section["sox_equivalent"]["window_sessions"]),
            "minimum": int(section["sox_equivalent"]["minimum_sessions"]),
            "card_stock_core": [str(item) for item in section["card_stock_core"]],
            "allowed_index_etfs": [str(item) for item in section["allowed_index_etfs"]],
            "sell_only": [str(item) for item in section["sell_only_holdings"]],
            "supplement": supplement,
            "cap": Decimal(str(section["single_stock_nominal_cap"])),
            "cap_exempt": [str(item) for item in section["single_stock_cap_exempt"]],
            "peak_drawdown": Decimal(str(section["single_stock_peak_review"]["drawdown_from_peak"])),
            "blackout_substitution_prohibited": {
                str(symbol): [str(item) for item in items]
                for symbol, items in section["blackout_substitution_prohibited"].items()},
            "max_add_grade": str(section["add_recommendation_classification"]["max_alert_grade"]),
            "grades": grades,
            "lines": all_lines,
            "hwm_initial": Decimal(str(lines["hwm_initial_usd"])), "hwm_initial_as_of": str(lines["hwm_initial_as_of"]),
            "broker_max_age_days": int(policy["broker_snapshot_max_age_calendar_days"]),
        }
    except ExposureError:
        raise
    except (KeyError, TypeError, ValueError, InvalidOperation, IndexError) as exc:
        raise ExposureError(f"S5_POLICY_FIELD_INVALID:{exc}") from exc


# ---------------------------------------------------------------------------------------------
# R1 exposure
# ---------------------------------------------------------------------------------------------

def nominal_exposure(weights: dict[str, Decimal], multipliers: dict[str, Decimal]) -> Decimal | None:
    """N = sum(multiplier x weight). None when any held instrument is unregistered (no default)."""
    if any(symbol not in multipliers for symbol in weights):
        return None
    return sum((multipliers[symbol] * weight for symbol, weight in weights.items()), ZERO)


def common_window(symbols: list[str], closes: dict[str, dict[str, str]], sessions: list[str],
                  evaluation_session: str, max_returns: int) -> tuple[list[str], list[str]]:
    """Sessions used for V, and the reasons V cannot be computed over them.

    The window is the last max_returns + 1 sessions ending at evaluation_session, but it never
    starts before the latest "first available close" among the symbols (listing date or the
    provider's retention start). A close missing after that start is a gap. The window is never
    shortened around a gap: a gap makes V unavailable, it is not a "short history".
    """
    if evaluation_session not in sessions:
        return [], ["V_EVALUATION_SESSION_NOT_IN_CALENDAR"]
    span = sessions[:sessions.index(evaluation_session) + 1]

    def has_close(symbol: str, session: str) -> bool:
        return _dec((closes.get(symbol) or {}).get(session)) is not None

    first_available = {symbol: next((session for session in span if has_close(symbol, session)), None)
                       for symbol in symbols}
    missing = sorted(symbol for symbol, first in first_available.items() if first is None)
    if missing:
        return [], [f"V_HISTORY_MISSING:{symbol}" for symbol in missing]
    start = max(first_available.values())
    window = [session for session in span if session >= start][-(max_returns + 1):]
    gaps = [f"V_HISTORY_GAP:{symbol}:{session}" for symbol in sorted(symbols) for session in window
            if not has_close(symbol, session)]
    return window, gaps


def daily_returns(symbol: str, closes: dict[str, dict[str, str]], window: list[str]) -> tuple[list[float], list[str]]:
    """Simple close-to-close returns over the window and split-guard flags."""
    values = [float(Decimal(str(closes[symbol][session]))) for session in window]
    returns, flags = [], []
    for index in range(1, len(values)):
        ratio = values[index] / values[index - 1] if values[index - 1] > 0 else float("nan")
        if not math.isfinite(ratio) or ratio <= SPLIT_GUARD_LOW or ratio >= SPLIT_GUARD_HIGH:
            flags.append(f"SPLIT_GUARD:{symbol}:{window[index]}")
        returns.append(ratio - 1.0)
    return returns, flags


def _sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = math.fsum(values) / len(values)
    return math.sqrt(math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1))


def volatility_ratio(weights: dict[str, Decimal], returns: dict[str, list[float]],
                     benchmark_returns: list[float]) -> float | None:
    """V = std(sum(weight x return)) / std(benchmark), current weights held fixed, cash return 0."""
    benchmark_std = _sample_std(benchmark_returns)
    if not benchmark_std:
        return None
    held = [(float(weight), returns[symbol]) for symbol, weight in weights.items() if weight != 0]
    portfolio = [math.fsum(weight * series[index] for weight, series in held)
                 for index in range(len(benchmark_returns))]
    portfolio_std = _sample_std(portfolio)
    return None if portfolio_std is None else portfolio_std / benchmark_std


class ExposureModel:
    """Exposure for arbitrary weights over one fixed return window (used for current and projected E)."""

    def __init__(self, config: dict[str, Any], closes: dict[str, dict[str, str]], sessions: list[str],
                 evaluation_session: str, symbols: list[str]) -> None:
        self.config = config
        self.symbols = sorted(set(symbols))
        self.reasons: list[str] = []
        self.returns: dict[str, list[float]] = {}
        self.benchmark_returns: list[float] = []
        benchmark = config["benchmark"]
        registered = [symbol for symbol in self.symbols if symbol in config["multipliers"]]
        self.window, gaps = common_window(registered + [benchmark], closes, sessions, evaluation_session,
                                          config["window"])
        self.return_count = max(len(self.window) - 1, 0)
        self.history_gap = bool(gaps)
        if len(registered) != len(self.symbols):
            self.reasons.append("UNREGISTERED_INSTRUMENT")
        if gaps:
            self.reasons.extend(gaps)
        elif self.return_count < config["minimum"]:
            self.reasons.append(f"V_HISTORY_BELOW_MINIMUM:{self.return_count}")
        else:
            flags: list[str] = []
            for symbol in registered + [benchmark]:
                series, symbol_flags = daily_returns(symbol, closes, self.window)
                flags.extend(symbol_flags)
                if symbol == benchmark:
                    self.benchmark_returns = series
                if symbol in registered:
                    self.returns[symbol] = series
            self.reasons.extend(flags)
        self.volatility_available = not self.reasons
        self.short_history = self.return_count < config["window"]

    def nominal(self, weights: dict[str, Decimal]) -> Decimal | None:
        return nominal_exposure({symbol: weight for symbol, weight in weights.items() if weight != 0},
                                self.config["multipliers"])

    def volatility(self, weights: dict[str, Decimal]) -> float | None:
        if not self.volatility_available:
            return None
        active = {symbol: weight for symbol, weight in weights.items() if weight != 0}
        if any(symbol not in self.returns for symbol in active):
            return None
        return volatility_ratio(active, self.returns, self.benchmark_returns)

    def parts(self, weights: dict[str, Decimal]) -> tuple[Decimal | None, float | None]:
        return self.nominal(weights), self.volatility(weights)


def new_entry_block_reason(model: ExposureModel) -> str:
    """Why an instrument that is not yet held cannot be recommended on V grounds."""
    return "V_HISTORY_GAP_BLOCKS_NEW_ENTRY" if model.history_gap else "V_HISTORY_BELOW_MINIMUM_BLOCKS_NEW_ENTRY"


def effective_exposure(nominal: Decimal | None, volatility: float | None) -> float | None:
    """E = max(N, V); None when either part is unavailable."""
    if nominal is None or volatility is None:
        return None
    return max(float(nominal), volatility)


def _gte(nominal: Decimal | None, volatility: float | None, threshold: Decimal) -> bool:
    """E >= threshold, compared before rounding. True as soon as one available part reaches it."""
    return (nominal is not None and nominal >= threshold) or (
        volatility is not None and volatility >= float(threshold))


def _lte(nominal: Decimal | None, volatility: float | None, threshold: Decimal) -> bool:
    """E <= threshold needs both parts."""
    return nominal is not None and volatility is not None and nominal <= threshold and (
        volatility <= float(threshold))


def band_state(nominal: Decimal | None, volatility: float | None, config: dict[str, Any]) -> str:
    if _gte(nominal, volatility, config["hard_gte"]):
        return "HARD_CEILING"
    if _gte(nominal, volatility, config["reduce_gte"]):
        return "ABOVE_BAND"
    if nominal is None or volatility is None:
        return "UNAVAILABLE"
    if _lte(nominal, volatility, config["add_lte"]):
        return "ADD_ZONE"
    return "WITHIN_BAND"


# ---------------------------------------------------------------------------------------------
# Positions, equity, snapshots
# ---------------------------------------------------------------------------------------------

def snapshot_for(snapshots: list[dict[str, Any]], session: str) -> dict[str, Any] | None:
    """Latest confirmed reconciliation whose broker as_of date is on or before the session."""
    chosen = None
    for snapshot in snapshots:
        if isinstance(snapshot.get("as_of"), str) and _date(snapshot["as_of"]) and snapshot["as_of"] <= session:
            chosen = snapshot
    return chosen


def held(snapshot: dict[str, Any]) -> dict[str, int]:
    return {str(symbol): int(quantity) for symbol, quantity in (snapshot.get("holdings") or {}).items()
            if isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0}


def closing_equity(snapshot: dict[str, Any], closes: dict[str, dict[str, str]],
                   session: str) -> tuple[Decimal | None, dict[str, Decimal], list[str]]:
    """Equity = confirmed holdings x regular-session close + confirmed cash (unrounded)."""
    cash = _dec(snapshot.get("cash_usd"))
    values: dict[str, Decimal] = {}
    missing: list[str] = []
    for symbol, quantity in held(snapshot).items():
        close = _dec((closes.get(symbol) or {}).get(session))
        if close is None or close <= 0:
            missing.append(symbol)
        else:
            values[symbol] = Decimal(quantity) * close
    if cash is None or cash < 0:
        return None, values, sorted(missing) + ["CASH"]
    if missing:
        return None, values, sorted(missing)
    return sum(values.values(), cash), values, []


def sale_pending_holds(snapshots: list[dict[str, Any]]) -> list[tuple[str, str | None]]:
    """Default rule until Kiwoom unsettled-proceeds fields are measured (prompt 8.5).

    A reconciliation that shows a smaller holding may not yet include the sale proceeds in cash, so
    line evaluation is on hold from its as_of until a reconciliation with a later as_of date exists.
    """
    holds: list[tuple[str, str | None]] = []
    for index, snapshot in enumerate(snapshots):
        if snapshot.get("holdings_decreased") is not True or not isinstance(snapshot.get("as_of"), str):
            continue
        later = [item["as_of"] for item in snapshots[index + 1:]
                 if isinstance(item.get("as_of"), str) and item["as_of"] > snapshot["as_of"]]
        holds.append((snapshot["as_of"], min(later) if later else None))
    return holds


def _in_hold(session: str, holds: list[tuple[str, str | None]]) -> bool:
    return any(start <= session and (end is None or session < end) for start, end in holds)


# ---------------------------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------------------------

def journal_view(journal: dict[str, Any]) -> dict[str, Any]:
    """Split verified journal entries by type. More than one activation is treated as corrupt."""
    status, errors = journal.get("status"), list(journal.get("errors") or [])
    entries = [entry for entry in journal.get("entries") or [] if isinstance(entry, dict)]
    activations = [entry for entry in entries if entry.get("entry_type") == JOURNAL_ACTIVATION]
    if status == "OK" and len(activations) > 1:
        status, errors = "CORRUPT", errors + ["MULTIPLE_S5_ACTIVATION_ENTRIES"]
    activation = None
    if status == "OK" and activations:
        payload = activations[0].get("payload") or {}
        hwm, when = _dec(payload.get("hwm_usd")), _date(payload.get("activation_date"))
        revision = payload.get("state_revision")
        if hwm is None or hwm <= 0 or when is None or not isinstance(revision, int) or isinstance(revision, bool):
            status, errors = "CORRUPT", errors + ["S5_ACTIVATION_ENTRY_INVALID"]
        else:
            activation = {"activation_date": when.isoformat(), "hwm": hwm, "hwm_as_of": payload.get("hwm_as_of"),
                          "state_revision": revision, "entry_id": activations[0].get("entry_id")}
    return {
        "status": status, "errors": errors, "activation": activation,
        "line_reviews": [entry for entry in entries if entry.get("entry_type") == JOURNAL_LINE_REVIEW],
        "peak_reviews": [entry for entry in entries if entry.get("entry_type") == JOURNAL_PEAK_REVIEW],
    }


# ---------------------------------------------------------------------------------------------
# R4 review lines and R6 holds
# ---------------------------------------------------------------------------------------------

def evaluate_review_lines(*, config: dict[str, Any], activation: dict[str, Any] | None,
                          line_reviews: list[dict[str, Any]], sessions: list[str], evaluation_session: str,
                          snapshots: list[dict[str, Any]], closes: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Recompute HWM, line breaches and pauses from the activation record forward (decision P1)."""
    result: dict[str, Any] = {
        "status": "NOT_ACTIVATED", "reasons": [], "hwm_usd": None, "hwm_date": None, "closing_equity_usd": None,
        "evaluated_through": None, "lines": [], "events": [], "open_events": [], "next_line": None,
        "skipped_sessions": [], "cash_flow": None, "sale_pending_hold": False, "unmatched_journal_reviews": [],
        "ledger_unconfirmed_revisions": [], "automatic_sell": False,
    }
    if activation is None:
        result["reasons"].append("S5_NOT_ACTIVATED")
        return result
    # From the activation revision on, every state revision must be confirmed by a replayed ledger
    # entry. A state without one (ledger missing, unreplayable entry, revision that came from nowhere)
    # could carry an undeclared cash flow, so nothing is evaluated and the HWM stays where it was.
    revisions = [snapshot["state_revision"] for snapshot in snapshots
                 if isinstance(snapshot.get("state_revision"), int) and not isinstance(snapshot["state_revision"], bool)]
    confirmed = {snapshot["state_revision"] for snapshot in snapshots
                 if snapshot.get("from_ledger_entry") is True and isinstance(snapshot.get("state_revision"), int)}
    first = activation["state_revision"]
    unconfirmed = [revision for revision in range(first, max(revisions + [first]) + 1) if revision not in confirmed]
    if unconfirmed:
        result.update({
            "status": "UNVERIFIED", "hwm_usd": _plain(activation["hwm"]), "hwm_date": activation.get("hwm_as_of"),
            "ledger_unconfirmed_revisions": unconfirmed,
            "reasons": [("ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY" if revision == first
                         else "POST_ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY") + f":{revision}"
                        for revision in unconfirmed]})
        return result
    chain_items = [{"as_of": snapshot.get("as_of"), "state_revision": snapshot.get("state_revision"),
                    "block": snapshot.get("cash_flow_declaration"),
                    "post_activation": isinstance(snapshot.get("state_revision"), int)
                    and snapshot["state_revision"] > activation["state_revision"]}
                   for snapshot in snapshots if snapshot.get("from_ledger_entry") is True]
    chain = cash_flow_chain(chain_items, start_date=activation["activation_date"])
    post_activation = [snapshot for snapshot in snapshots if isinstance(snapshot.get("state_revision"), int)
                       and snapshot["state_revision"] > activation["state_revision"]]
    sale_holds = sale_pending_holds(post_activation)
    cash_holds: list[tuple[str, str | None]] = []
    open_start: str | None = None
    for step in chain["steps"]:
        if not step["post_activation"]:
            continue
        if step["status"] == "HOLD" and open_start is None:
            open_start = str(step["as_of"])
        elif step["status"] == "CLEAR" and open_start is not None:
            cash_holds.append((open_start, str(step["as_of"])))
            open_start = None
    if open_start is not None:
        cash_holds.append((open_start, None))
    result["cash_flow"] = {"hold_active": chain["hold_active"], "hold_from": chain["hold_from"],
                           "covered_through": chain["covered_through"], "adjustments": chain["adjustments"],
                           "steps": [step for step in chain["steps"] if step["post_activation"]]}
    result["sale_pending_hold"] = any(end is None for _, end in sale_holds)

    hwm, hwm_date = activation["hwm"], activation.get("hwm_as_of")
    triggered: set[str] = set()
    pending = list(chain["adjustments"])
    events: list[dict[str, Any]] = []
    equity: Decimal | None = None
    status = "EVALUATED"
    if evaluation_session not in sessions:
        result["status"], result["reasons"] = "UNVERIFIED", ["EVALUATION_SESSION_NOT_IN_CALENDAR"]
        return result
    # The activation session itself is judged too: its equity may already sit below a line of the
    # rechecked HWM (the high between the policy start date and activation).
    todo = [session for session in sessions if activation["activation_date"] <= session <= evaluation_session]
    for session in todo:
        if _in_hold(session, cash_holds) or _in_hold(session, sale_holds):
            result["skipped_sessions"].append(session)
            continue
        snapshot = snapshot_for(snapshots, session)
        if snapshot is None:
            status = "UNVERIFIED"
            result["reasons"].append(f"NO_CONFIRMED_SNAPSHOT:{session}")
            break
        equity, _, missing = closing_equity(snapshot, closes, session)
        if equity is None:
            # D5: a missing close is never skipped; skipping would understate the HWM.
            status = "UNVERIFIED"
            result["reasons"].append(f"EQUITY_GAP:{session}:{','.join(missing)}")
            break
        for adjustment in [item for item in pending if item["effective_date"] <= session]:
            hwm += Decimal(adjustment["amount_usd"])
            pending.remove(adjustment)
        if equity > hwm:
            hwm, hwm_date = equity, session
            triggered.clear()
        for line in config["lines"]:
            if line["id"] not in triggered and equity <= hwm * line["fraction"]:
                triggered.add(line["id"])
                events.append({"line_id": line["id"], "fraction": line["fraction"], "hwm": hwm,
                               "hwm_date": hwm_date, "breach_date": session, "equity": equity,
                               "pause_add": line["pause_add"], "pause_new_buy": line["pause_new_buy"],
                               "action": line["action"]})
        result["evaluated_through"] = session
    held_now = bool(todo) and (_in_hold(evaluation_session, cash_holds) or _in_hold(evaluation_session, sale_holds))
    if status == "EVALUATED" and held_now:
        status = "HELD"
        result["reasons"].append("LINE_EVALUATION_ON_HOLD")

    reviewed: set[tuple[str, str]] = set()
    for entry in line_reviews:
        payload = entry.get("payload") or {}
        match = next((event for event in events if event["line_id"] == payload.get("line_id")
                      and event["breach_date"] == payload.get("breach_date")
                      and _dec(payload.get("hwm")) == event["hwm"]), None)
        if match is None or payload.get("review_status") != "completed":
            result["unmatched_journal_reviews"].append(
                {"entry_id": entry.get("entry_id"), "line_id": payload.get("line_id"),
                 "breach_date": payload.get("breach_date")})
        else:
            reviewed.add((match["line_id"], match["breach_date"]))
    rendered_events = []
    for event in events:
        done = (event["line_id"], event["breach_date"]) in reviewed
        rendered_events.append({
            "line_id": event["line_id"], "fraction_of_hwm": _num(event["fraction"], 2),
            "hwm": _plain(event["hwm"]), "hwm_date": event["hwm_date"], "breach_date": event["breach_date"],
            "closing_equity_usd": _plain(event["equity"]), "threshold_usd": _plain(event["hwm"] * event["fraction"]),
            "action": event["action"], "pause_add_recommendations": event["pause_add"],
            "pause_new_buy_recommendations": event["pause_new_buy"],
            "review_status": "completed" if done else "open",
            "alert_grade": config["grades"]["REVIEW_LINE_WITH_PAUSE" if event["pause_add"] or event["pause_new_buy"]
                                        else "REVIEW_LINE_WITHOUT_PAUSE"],
        })
    result.update({
        "status": status, "hwm_usd": _plain(hwm), "hwm_date": hwm_date,
        "closing_equity_usd": _plain(equity) if result["evaluated_through"] == evaluation_session else None,
        "events": rendered_events, "open_events": [item for item in rendered_events if item["review_status"] == "open"],
    })
    current = equity if result["evaluated_through"] == evaluation_session else None
    for line in config["lines"]:
        threshold = hwm * line["fraction"]
        result["lines"].append({
            "line_id": line["id"], "fraction_of_hwm": _num(line["fraction"], 2), "threshold_usd": _plain(threshold),
            "triggered_in_current_drawdown": line["id"] in triggered,
            "distance_pct": _num((current - threshold) / current * 100, 2) if current else None,
        })
    remaining = [item for item in result["lines"] if not item["triggered_in_current_drawdown"]]
    result["next_line"] = remaining[0] if remaining else None
    return result


# Open fail-closed reasons that are expected before activation and do not block the proposal.
ACTIVATION_ALLOWED_REASONS = {
    "hwm_line_or_pause_state_missing_or_corrupt": ("S5_NOT_ACTIVATED",),
    "decision_journal_missing_or_corrupt": ("JOURNAL_MISSING",),
}


def activation_blockers(triggers: dict[str, list[str]], non_default_inputs: list[str]) -> list[str]:
    """Everything that must be clean before an activation record may be proposed.

    Only "not activated yet" and "no journal file yet" may be open. Any other fail-closed reason
    (unverified or missing closes, stale reconciliation, ledger problems, V unavailable, a session
    that is not the latest) or any non-default input blocks the proposal.
    """
    blockers = [f"FAIL_CLOSED:{name}:{reason}" for name in FAIL_CLOSED_TRIGGERS for reason in triggers.get(name) or []
                if reason not in ACTIVATION_ALLOWED_REASONS.get(name, ())]
    if non_default_inputs:
        blockers.append("NON_DEFAULT_INPUTS:" + ",".join(str(item) for item in non_default_inputs))
    return blockers


def review_activation_blockers(review: dict[str, Any]) -> list[str]:
    """activation_blockers recomputed from a finished review (the journal checks this again)."""
    triggers = {item["id"]: list(item["reasons"]) for item in review["fail_closed"]["triggers"]}
    return activation_blockers(triggers, list((review.get("inputs") or {}).get("non_default_inputs") or []))


def activation_candidate(*, config: dict[str, Any], sessions: list[str], evaluation_session: str,
                         snapshots: list[dict[str, Any]], closes: dict[str, dict[str, str]],
                         close_unverified: dict[str, dict[str, list[str]]], blockers: list[str]) -> dict[str, Any]:
    """HWM recheck for the activation record: closing-equity high from the policy start date.

    READY needs a complete window of verified closes for every instrument held in it and no blocker.
    """
    window = [session for session in sessions if config["hwm_initial_as_of"] <= session <= evaluation_session]
    candidate: dict[str, Any] = {
        "status": "NOT_READY", "reasons": [], "window_start": config["hwm_initial_as_of"],
        "window_end": evaluation_session, "activation_date": evaluation_session, "sessions": [],
        "hwm_usd": None, "hwm_as_of": None, "hwm_policy_initial_usd": _plain(config["hwm_initial"]),
        "hwm_difference_usd": None, "state_revision": None,
    }
    if not window or window[0] != config["hwm_initial_as_of"]:
        candidate["reasons"].append("HWM_WINDOW_START_NOT_IN_CALENDAR")
        return candidate
    best: tuple[Decimal, str] | None = None
    for session in window:
        snapshot = snapshot_for(snapshots, session)
        equity, _, missing = closing_equity(snapshot, closes, session) if snapshot else (None, {}, ["SNAPSHOT"])
        if equity is None:
            candidate["reasons"].append(f"EQUITY_GAP:{session}:{','.join(missing)}")
            continue
        candidate["sessions"].append({"session_date": session, "closing_equity_usd": _plain(equity)})
        if best is None or equity > best[0]:
            best = (equity, session)
        for symbol in sorted(held(snapshot)):
            for reason in (close_unverified.get(symbol) or {}).get(session) or []:
                code = f"CLOSE_UNVERIFIED:{symbol}:{reason}"
                if code not in candidate["reasons"]:
                    candidate["reasons"].append(code)
    candidate["reasons"].extend(blockers)
    latest = snapshot_for(snapshots, evaluation_session)
    if latest is not None and latest.get("from_ledger_entry") is not True:
        # The state an activation is bound to must itself be confirmed by a reconciliation ledger entry.
        candidate["reasons"].append("ACTIVATION_STATE_NOT_CONFIRMED_BY_LEDGER_ENTRY")
    if candidate["reasons"] or best is None or latest is None or not isinstance(latest.get("state_revision"), int):
        return candidate
    candidate.update({"status": "READY", "hwm_usd": _plain(best[0]), "hwm_as_of": best[1],
                      "hwm_difference_usd": _plain(best[0] - config["hwm_initial"]),
                      "state_revision": latest["state_revision"]})
    return candidate


# ---------------------------------------------------------------------------------------------
# R5 single-instrument peak review
# ---------------------------------------------------------------------------------------------

def evaluate_peak_reviews(*, config: dict[str, Any], activation: dict[str, Any] | None,
                          peak_reviews: list[dict[str, Any]], sessions: list[str], evaluation_session: str,
                          snapshots: list[dict[str, Any]], closes: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Forward peak since activation (or the first reconciled date of a later entry); -30% rewrite trigger."""
    current = snapshot_for(snapshots, evaluation_session)
    symbols = sorted(held(current)) if current else []
    factor = ONE - config["peak_drawdown"]
    items: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    matched_ids: set[Any] = set()
    for symbol in symbols:
        item: dict[str, Any] = {"symbol": symbol, "status": "NO_BASELINE_PEAK", "reasons": [], "basis_date": None,
                                "peak": None, "peak_date": None, "close": None, "threshold": None,
                                "events": [], "open_events": [], "pause_add_recommendations": True,
                                "automatic_sell": False}
        items.append(item)
        if activation is None:
            item["reasons"].append("S5_NOT_ACTIVATED")
            continue
        # First reconciled date of the current continuous holding run.
        first = None
        for snapshot in snapshots:
            if not isinstance(snapshot.get("as_of"), str) or snapshot["as_of"] > evaluation_session:
                continue
            if symbol in held(snapshot):
                first = first or snapshot["as_of"]
            else:
                first = None
        basis = max(activation["activation_date"], first) if first else None
        if basis is None:
            item["reasons"].append("FIRST_RECONCILED_DATE_UNKNOWN")
            continue
        item["basis_date"] = basis
        span = [session for session in sessions if basis <= session <= evaluation_session]
        if not span:
            item["reasons"].append("NO_SESSION_SINCE_BASIS_DATE")
            continue
        peak: Decimal | None = None
        peak_date: str | None = None
        armed = True
        events: list[dict[str, Any]] = []
        gap = None
        for session in span:
            close = _dec((closes.get(symbol) or {}).get(session))
            if close is None or close <= 0:
                gap = session
                break
            if peak is None or close > peak:
                peak, peak_date, armed = close, session, True
            if armed and close <= peak * factor:
                armed = False
                events.append({"peak": peak, "peak_date": peak_date, "breach_date": session, "close": close})
        if gap is not None:
            item["status"] = "UNVERIFIED"
            item["reasons"].append(f"CLOSE_GAP:{gap}")
            continue
        rendered = []
        for event in events:
            entry = next((candidate for candidate in peak_reviews
                          if (candidate.get("payload") or {}).get("symbol") == symbol
                          and (candidate.get("payload") or {}).get("breach_date") == event["breach_date"]
                          and _dec((candidate.get("payload") or {}).get("peak")) == event["peak"]
                          and (candidate.get("payload") or {}).get("review_status") == "completed"), None)
            if entry is not None:
                matched_ids.add(id(entry))
            rendered.append({"peak": _plain(event["peak"]), "peak_date": event["peak_date"],
                             "breach_date": event["breach_date"], "close": _plain(event["close"]),
                             "threshold": _plain(event["peak"] * factor),
                             "review_status": "completed" if entry is not None else "open",
                             "alert_grade": config["grades"]["PEAK_REVIEW"]})
        open_events = [event for event in rendered if event["review_status"] == "open"]
        item.update({"status": "REVIEW_OPEN" if open_events else "OK", "peak": _plain(peak), "peak_date": peak_date,
                     "close": _plain(_dec(closes[symbol][evaluation_session])), "threshold": _plain(peak * factor),
                     "events": rendered, "open_events": open_events,
                     "pause_add_recommendations": bool(open_events)})
    for entry in peak_reviews:
        if id(entry) not in matched_ids:
            payload = entry.get("payload") or {}
            unmatched.append({"entry_id": entry.get("entry_id"), "symbol": payload.get("symbol"),
                              "breach_date": payload.get("breach_date")})
    return {"items": items, "unmatched_journal_reviews": unmatched}


# ---------------------------------------------------------------------------------------------
# R3 earnings blackout
# ---------------------------------------------------------------------------------------------

def earnings_blackout(symbol: str, earnings: dict[str, Any] | None, calendar_sessions: list[str],
                      buy_session: str | None) -> tuple[bool, str]:
    """Two sessions before the announcement through the first session after results.

    An unverified, stale or uncheckable earnings date is a blackout. AFTER_CLOSE and unknown timing
    end at the next session; BEFORE_OPEN ends at the announcement session itself.
    """
    record = (earnings or {}).get(symbol)
    if not isinstance(record, dict) or record.get("status") != "VERIFIED":
        return True, "EARNINGS_DATE_UNVERIFIED"
    announced = record.get("announcement_session")
    if buy_session is None or buy_session not in calendar_sessions or announced not in calendar_sessions:
        return True, "EARNINGS_WINDOW_NOT_CHECKABLE"
    index = calendar_sessions.index(announced)
    if index < 2:
        return True, "EARNINGS_WINDOW_NOT_CHECKABLE"
    start = calendar_sessions[index - 2]
    if record.get("timing") == "BEFORE_OPEN":
        end = announced
    elif index + 1 < len(calendar_sessions):
        end = calendar_sessions[index + 1]
    else:
        return True, "EARNINGS_WINDOW_NOT_CHECKABLE"
    if buy_session > end:
        # The verified date is already behind us, so the next announcement is not known.
        return True, "EARNINGS_DATE_STALE"
    return (True, "EARNINGS_BLACKOUT") if start <= buy_session <= end else (False, "OUTSIDE_EARNINGS_BLACKOUT")


# ---------------------------------------------------------------------------------------------
# R2 / R3 recommendations
# ---------------------------------------------------------------------------------------------

def cap_limit(symbol: str, config: dict[str, Any]) -> Decimal | None:
    """Largest weight allowed by the single-stock nominal cap; None for exempt index leveraged ETFs."""
    if symbol in config["cap_exempt"] or symbol not in config["multipliers"]:
        return None
    multiplier = config["multipliers"][symbol]
    return config["cap"] / multiplier if multiplier > 0 else None


def cap_breaches(weights: dict[str, Decimal], config: dict[str, Any]) -> list[dict[str, Any]]:
    breaches = []
    for symbol in sorted(weights):
        limit = cap_limit(symbol, config)
        if limit is not None and weights[symbol] * config["multipliers"][symbol] > config["cap"]:
            breaches.append({"symbol": symbol, "nominal": weights[symbol] * config["multipliers"][symbol],
                             "limit_weight": limit})
    return breaches


def _within_target(model: ExposureModel, weights: dict[str, Decimal], config: dict[str, Any]) -> bool:
    nominal, volatility = model.parts(weights)
    if nominal is None or nominal > config["projected_lte"]:
        return False
    if model.volatility_available:
        return volatility is not None and volatility <= float(config["projected_lte"])
    return True  # reduce only: V is unavailable, the result carries the unverified label


def reduce_recommendations(*, model: ExposureModel, weights: dict[str, Decimal], config: dict[str, Any],
                           cards: dict[str, Any], urgent: bool) -> tuple[list[dict[str, Any]], list[str]]:
    """Reduce order: (1) single-stock cap excess incl. sell-only (2) card TRIM/EXIT (3) the supplement ETF."""
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    projected = dict(weights)
    for breach in cap_breaches(weights, config):
        target = floor_to_step(breach["limit_weight"])
        projected[breach["symbol"]] = target
        items.append({"order": 1, "basis": "single_stock_cap_excess_including_sell_only",
                      "symbol": breach["symbol"], "current_weight": _num(weights[breach["symbol"]]),
                      "target_weight": _num(target, 3)})
    for symbol in sorted(cards):
        card = cards[symbol]
        if symbol in weights and card.get("valid") is True and card.get("action") in CARD_REDUCE_ACTIONS:
            # A TRIM size is the card's judgment (no target here); EXIT means zero.
            items.append({"order": 2, "basis": "card_trim_or_exit", "symbol": symbol,
                          "current_weight": _num(weights[symbol]), "card_action": card["action"],
                          "target_weight": 0.0 if card["action"] == "EXIT" else None})
    supplement = config["supplement"]
    if _within_target(model, projected, config):
        pass
    elif supplement not in projected or projected[supplement] <= 0:
        warnings.append("EXCESS_UNRESOLVED_NO_SUBSTITUTE")
    else:
        candidate = floor_to_step(projected[supplement])
        trial = dict(projected)
        resolved = False
        while candidate >= 0:
            trial[supplement] = candidate
            if _within_target(model, trial, config):
                resolved = True
                break
            candidate -= WEIGHT_STEP
        target = candidate if resolved else ZERO
        trial[supplement] = target
        items.append({"order": 3, "basis": supplement, "symbol": supplement,
                      "current_weight": _num(weights[supplement]), "target_weight": _num(target, 3)})
        projected = trial
        if not resolved:
            warnings.append("EXCESS_UNRESOLVED_NO_SUBSTITUTE")
    nominal, volatility = model.parts(projected)
    for item in items:
        item.update({"action": "reduce", "urgent": urgent, "alert_grade": config["grades"][
            "EXPOSURE_HARD_CEILING" if urgent else "EXPOSURE_ABOVE_BAND"]})
    summary = {"projected_nominal": _num(nominal, 4), "projected_sox_equivalent": _num(volatility, 4),
               "projected_effective": _num(effective_exposure(nominal, volatility), 4)}
    for item in items:
        item["projected_after_all_steps"] = summary
    return items, warnings


def increase_blockers(symbol: str, *, config: dict[str, Any], weights: dict[str, Decimal],
                      peaks: dict[str, dict[str, Any]], earnings: dict[str, Any] | None,
                      calendar_sessions: list[str], buy_session: str | None) -> list[str]:
    """Instrument-level reasons an exposure-increasing recommendation must be omitted."""
    reasons: list[str] = []
    if symbol not in config["multipliers"]:
        return ["UNREGISTERED_INSTRUMENT"]
    if symbol in config["sell_only"]:
        return ["SELL_ONLY_HOLDING"]
    if symbol not in config["card_stock_core"] and symbol not in config["allowed_index_etfs"]:
        return ["NOT_AN_S5_NEW_BUY_INSTRUMENT"]
    peak = peaks.get(symbol)
    if symbol in weights and weights[symbol] > 0 and (peak is None or peak.get("pause_add_recommendations")):
        reasons.append("PEAK_REVIEW_PAUSE:" + str((peak or {}).get("status", "NO_BASELINE_PEAK")))
    if symbol in config["card_stock_core"]:
        blackout, code = earnings_blackout(symbol, earnings, calendar_sessions, buy_session)
        if blackout:
            reasons.append(code)
    for source, substitutes in config["blackout_substitution_prohibited"].items():
        if symbol in substitutes and earnings_blackout(source, earnings, calendar_sessions, buy_session)[0]:
            reasons.append(f"BLACKOUT_SUBSTITUTION_PROHIBITED:{source}")
    return reasons


def projected_increase_reasons(model: ExposureModel, weights: dict[str, Decimal], symbol: str,
                               config: dict[str, Any]) -> list[str]:
    """Projected E <= target (both parts, before rounding) and the single-stock cap."""
    reasons: list[str] = []
    nominal, volatility = model.parts(weights)
    if not _lte(nominal, volatility, config["projected_lte"]):
        reasons.append("PROJECTED_EXPOSURE_ABOVE_TARGET" if nominal is not None and volatility is not None
                       else "PROJECTED_EXPOSURE_UNAVAILABLE")
    limit = cap_limit(symbol, config)
    if limit is not None and weights.get(symbol, ZERO) * config["multipliers"][symbol] > config["cap"]:
        reasons.append("SINGLE_STOCK_CAP")
    if sum(weights.values(), ZERO) > ONE:
        reasons.append("VERIFIED_CASH_INSUFFICIENT")
    return reasons


def add_recommendations(*, candidates: list[str], model: ExposureModel, weights: dict[str, Decimal],
                        config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Raise every candidate one grid step at a time while the joint projected E stays within target."""
    projected = dict(weights)
    for symbol in candidates:
        projected.setdefault(symbol, ZERO)
    start = {symbol: projected[symbol] for symbol in candidates}
    stopped: dict[str, list[str]] = {}
    active = list(candidates)
    while active:
        for symbol in list(active):
            trial = dict(projected)
            trial[symbol] = floor_to_step(trial[symbol]) + WEIGHT_STEP
            reasons = projected_increase_reasons(model, trial, symbol, config)
            if reasons:
                stopped[symbol] = reasons
                active.remove(symbol)
            else:
                projected = trial
    nominal, volatility = model.parts(projected)
    items, omitted = [], []
    for symbol in candidates:
        if projected[symbol] > start[symbol]:
            items.append({"action": "add", "symbol": symbol, "current_weight": _num(start[symbol]),
                          "target_weight": _num(projected[symbol], 3),
                          "projected_nominal": _num(nominal, 4), "projected_sox_equivalent": _num(volatility, 4),
                          "projected_effective": _num(effective_exposure(nominal, volatility), 4),
                          "nature": "return_seeking", "authority_basis": "user_approved_risk_budget",
                          "return_gate": "not_passed", "oos_and_shadow": "skipped", "output": "display_only",
                          "alert_grade": config["grades"]["ADD_RECOMMENDATION"]})
        else:
            omitted.append({"kind": "add", "symbol": symbol, "reasons": stopped.get(symbol, [])})
    return items, omitted


# ---------------------------------------------------------------------------------------------
# Top-level review
# ---------------------------------------------------------------------------------------------

def build_exposure_review(*, policy: dict[str, Any], evaluation_session: str, calendar_sessions: list[str],
                          snapshots: list[dict[str, Any]], snapshot_reasons: list[str],
                          closes: dict[str, dict[str, str]], close_unverified: dict[str, dict[str, list[str]]],
                          journal: dict[str, Any], cards: dict[str, Any] | None = None,
                          earnings: dict[str, Any] | None = None,
                          proposals: list[dict[str, Any]] | None = None,
                          inputs: dict[str, Any] | None = None,
                          evaluation_reasons: list[str] | None = None) -> dict[str, Any]:
    """One deterministic review for the completed session `evaluation_session`.

    calendar_sessions  ascending session dates (may extend past the evaluation session)
    snapshots          ascending confirmed reconciliations: as_of, state_revision, holdings, cash_usd,
                       holdings_decreased, cash_flow_declaration, from_ledger_entry
    snapshot_reasons   why the reconciliation history is not verified (empty when it is)
    closes             {symbol: {session: close}} approximate regular-session closes
    close_unverified   {symbol: {session: [reason]}} for closes that exist but are not verified
    journal            {"status": OK|MISSING|CORRUPT, "entries": [...], "errors": [...]}
    evaluation_reasons why the evaluation session is not known to be the latest completed session
    """
    config = exposure_config(policy)
    cards, proposals = cards or {}, proposals or []
    if _date(evaluation_session) is None or evaluation_session not in calendar_sessions:
        raise ExposureError("EVALUATION_SESSION_NOT_IN_CALENDAR")
    sessions = [session for session in calendar_sessions if session <= evaluation_session]
    later = [session for session in calendar_sessions if session > evaluation_session]
    buy_session = later[0] if later else None
    triggers: dict[str, list[str]] = {name: [] for name in FAIL_CLOSED_TRIGGERS}
    triggers["exposure_or_equity_or_v_unavailable"].extend(evaluation_reasons or [])
    # A reconciliation dated after the evaluation session says nothing about this session: it is not
    # used for holdings, and it cannot lift a cash-flow or sale hold that covers this session.
    later_reconciliations = sum(1 for snapshot in snapshots
                                if isinstance(snapshot.get("as_of"), str) and snapshot["as_of"] > evaluation_session)
    snapshots = [snapshot for snapshot in snapshots
                 if isinstance(snapshot.get("as_of"), str) and snapshot["as_of"] <= evaluation_session]

    current = snapshot_for(snapshots, evaluation_session)
    holdings = held(current) if current else {}
    if current is None:
        triggers["exposure_or_equity_or_v_unavailable"].append("NO_CONFIRMED_SNAPSHOT")
    triggers["exposure_or_equity_or_v_unavailable"].extend(snapshot_reasons)
    if current is not None:
        age = (_date(evaluation_session) - _date(current["as_of"])).days
        if age > config["broker_max_age_days"]:
            triggers["broker_snapshot_older_than_broker_snapshot_max_age_calendar_days"].append(
                f"BROKER_SNAPSHOT_AGE_DAYS:{age}")

    equity, values, missing = closing_equity(current, closes, evaluation_session) if current else (None, {}, [])
    for symbol in missing:
        triggers["required_price_missing"].append(f"CLOSE_MISSING:{symbol}:{evaluation_session}")
    if _dec((closes.get(config["benchmark"]) or {}).get(evaluation_session)) is None:
        triggers["required_price_missing"].append(f"CLOSE_MISSING:{config['benchmark']}:{evaluation_session}")
    unregistered = sorted(symbol for symbol in holdings if symbol not in config["multipliers"])
    for symbol in unregistered:
        triggers["unregistered_instrument_held"].append(f"UNREGISTERED:{symbol}")

    weights: dict[str, Decimal] = {}
    cash_weight: Decimal | None = None
    if equity is not None and equity > 0:
        weights = {symbol: value / equity for symbol, value in values.items()}
        cash_weight = _dec(current["cash_usd"]) / equity
    elif current is not None:
        triggers["exposure_or_equity_or_v_unavailable"].append("EQUITY_UNAVAILABLE")

    model = ExposureModel(config, closes, sessions, evaluation_session, list(holdings))
    usable = equity is not None and equity > 0
    # Current N is computed from values over equity in one division, so a boundary such as exactly
    # 1.85 is compared before any rounding of the individual weights.
    nominal = (sum((config["multipliers"][symbol] * value for symbol, value in values.items()), ZERO) / equity
               if usable and not unregistered else None)
    volatility = (model.volatility(weights) if weights else 0.0) if usable else None
    effective = effective_exposure(nominal, volatility)
    if nominal is None and equity is not None:
        triggers["exposure_or_equity_or_v_unavailable"].append("NOMINAL_UNAVAILABLE")
    if volatility is None and equity is not None:
        triggers["exposure_or_equity_or_v_unavailable"].extend(
            [f"V_UNAVAILABLE:{reason}" for reason in model.reasons] or ["V_UNAVAILABLE"])
    band = band_state(nominal, volatility, config)

    view = journal_view(journal)
    # Closes that exist but are not verified (calendar authority, bar-label basis, page hashes) keep
    # their values on display and fail closed. Only sessions this review actually uses are checked.
    used_from = view["activation"]["activation_date"] if view["activation"] else config["hwm_initial_as_of"]
    used = set(model.window) | {session for session in sessions if session >= used_from}
    for symbol in sorted(set(holdings) | {config["benchmark"]}):
        per_session = close_unverified.get(symbol) or {}
        for reason in sorted({reason for session in used for reason in per_session.get(session) or []}):
            triggers["required_price_missing"].append(f"CLOSE_UNVERIFIED:{symbol}:{reason}")
    if view["status"] != "OK":
        triggers["decision_journal_missing_or_corrupt"].extend(
            [f"JOURNAL_{view['status']}"] + [str(item) for item in view["errors"]])
    lines = evaluate_review_lines(
        config=config, activation=view["activation"], line_reviews=view["line_reviews"], sessions=sessions,
        evaluation_session=evaluation_session, snapshots=snapshots, closes=closes)
    peaks = evaluate_peak_reviews(
        config=config, activation=view["activation"], peak_reviews=view["peak_reviews"], sessions=sessions,
        evaluation_session=evaluation_session, snapshots=snapshots, closes=closes)
    # HELD is fail-closed too: while line evaluation is on hold nothing may be added or bought.
    if lines["status"] in ("NOT_ACTIVATED", "UNVERIFIED", "HELD"):
        triggers["hwm_line_or_pause_state_missing_or_corrupt"].extend(lines["reasons"] or [lines["status"]])
    if lines["ledger_unconfirmed_revisions"]:
        triggers["undeclared_cash_flow"].append("CASH_FLOW_NOT_VERIFIABLE_WITHOUT_LEDGER_ENTRY")
    for item in lines["unmatched_journal_reviews"] + peaks["unmatched_journal_reviews"]:
        triggers["hwm_line_or_pause_state_missing_or_corrupt"].append(f"JOURNAL_REVIEW_UNMATCHED:{item['entry_id']}")
    if lines["cash_flow"] and lines["cash_flow"]["hold_active"]:
        reasons = [reason for step in lines["cash_flow"]["steps"] if step["status"] == "HOLD"
                   for reason in step["reasons"]]
        triggers["undeclared_cash_flow"].extend(sorted(set(reasons)) or ["CASH_FLOW_HOLD"])
    if lines["sale_pending_hold"]:
        triggers["exposure_or_equity_or_v_unavailable"].append("SALE_PROCEEDS_PENDING_CASH_CONFIRMATION")
    for item in peaks["items"]:
        if item["status"] == "UNVERIFIED":
            triggers["required_price_missing"].extend(f"PEAK_{reason}:{item['symbol']}" for reason in item["reasons"])
    fail_closed_active = any(triggers.values())
    candidate = None
    if view["activation"] is None and view["status"] != "CORRUPT":
        candidate = activation_candidate(
            config=config, sessions=sessions, evaluation_session=evaluation_session, snapshots=snapshots,
            closes=closes, close_unverified=close_unverified,
            blockers=activation_blockers(triggers, list((inputs or {}).get("non_default_inputs") or [])))
    open_pause_lines = [event["line_id"] for event in lines["open_events"]
                        if event["pause_add_recommendations"] or event["pause_new_buy_recommendations"]]

    def pause(kind: str) -> dict[str, Any]:
        reasons = [f"FAIL_CLOSED:{name}" for name in FAIL_CLOSED_TRIGGERS if triggers[name]]
        reasons += [f"REVIEW_LINE_OPEN:{line_id}" for line_id in open_pause_lines]
        if kind == "new_buy" and band in ("ABOVE_BAND", "HARD_CEILING"):
            reasons.append("EXPOSURE_HARD_CEILING" if band == "HARD_CEILING" else "EXPOSURE_ABOVE_BAND")
        return {"paused": bool(reasons), "reasons": reasons}

    pauses = {"add_recommendations": pause("add"), "new_buy_recommendations": pause("new_buy")}
    peak_by_symbol = {item["symbol"]: item for item in peaks["items"]}
    breaches = cap_breaches(weights, config)
    recommendations: dict[str, Any] = {"reduce": [], "add": [], "omitted": [], "proposals": [], "warnings": []}
    if breaches:
        recommendations["warnings"].append("SINGLE_STOCK_CAP_EXCEEDED")
    valid_cards = {symbol: card for symbol, card in cards.items()
                   if isinstance(card, dict) and card.get("valid") is True
                   and card.get("session_date") == evaluation_session}

    if band in ("ABOVE_BAND", "HARD_CEILING") and weights:
        items, warnings = reduce_recommendations(model=model, weights=weights, config=config, cards=valid_cards,
                                                 urgent=band == "HARD_CEILING")
        recommendations["reduce"] = items
        recommendations["warnings"].extend(warnings)

    def blockers(symbol: str) -> list[str]:
        reasons = increase_blockers(symbol, config=config, weights=weights, peaks=peak_by_symbol, earnings=earnings,
                                    calendar_sessions=calendar_sessions, buy_session=buy_session)
        if symbol not in holdings:
            # A new instrument's own closes must be verified too (held ones already fail closed above).
            per_session = close_unverified.get(symbol) or {}
            reasons += [f"CANDIDATE_CLOSE_UNVERIFIED:{reason}" for reason in sorted(
                {reason for session in sessions for reason in per_session.get(session) or []})]
        return reasons

    def projection_model(symbols: list[str]) -> ExposureModel:
        extra = [symbol for symbol in symbols if symbol not in holdings]
        return model if not extra else ExposureModel(config, closes, sessions, evaluation_session,
                                                     list(holdings) + extra)

    if band == "ADD_ZONE" and equity is not None:
        if pauses["add_recommendations"]["paused"]:
            recommendations["omitted"].append({"kind": "add", "symbol": None,
                                               "reasons": pauses["add_recommendations"]["reasons"]})
        else:
            card_adds = [symbol for symbol in sorted(valid_cards) if valid_cards[symbol].get("action") == "ADD"]
            candidates = card_adds or [config["supplement"]]
            eligible = []
            for symbol in candidates:
                reasons = blockers(symbol)
                if not reasons and not projection_model([symbol]).volatility_available:
                    reasons = [new_entry_block_reason(projection_model([symbol]))]
                if reasons:
                    # The default supplement is never replaced by another instrument.
                    recommendations["omitted"].append({"kind": "add", "symbol": symbol, "reasons": reasons})
                else:
                    eligible.append(symbol)
            if eligible:
                joint = projection_model(eligible)
                if not joint.volatility_available:
                    recommendations["omitted"].extend(
                        {"kind": "add", "symbol": symbol, "reasons": [new_entry_block_reason(joint)]}
                        for symbol in eligible)
                else:
                    items, omitted = add_recommendations(candidates=eligible, model=joint, weights=weights,
                                                         config=config)
                    recommendations["add"] = items
                    recommendations["omitted"].extend(omitted)

    for index, proposal in enumerate(proposals):
        recommendations["proposals"].append(_evaluate_proposal(
            index, proposal, config=config, weights=weights, band=band, pauses=pauses, blockers=blockers,
            projection_model=projection_model, equity_available=equity is not None))

    alerts: list[dict[str, Any]] = []
    if fail_closed_active:
        alerts.append({"code": "S5_FAIL_CLOSED_UNVERIFIED", "grade": config["grades"]["FAIL_CLOSED_UNVERIFIED"],
                       "label": "UNVERIFIED"})
    if band == "HARD_CEILING":
        alerts.append({"code": "S5_EXPOSURE_HARD_CEILING", "grade": config["grades"]["EXPOSURE_HARD_CEILING"]})
    elif band == "ABOVE_BAND":
        alerts.append({"code": "S5_EXPOSURE_ABOVE_BAND", "grade": config["grades"]["EXPOSURE_ABOVE_BAND"]})
    for event in lines["open_events"]:
        alerts.append({"code": f"S5_REVIEW_LINE_{event['line_id']}", "grade": event["alert_grade"],
                       "breach_date": event["breach_date"]})
    for item in peaks["items"]:
        for event in item["open_events"]:
            alerts.append({"code": f"S5_PEAK_REVIEW_{item['symbol']}", "grade": event["alert_grade"],
                           "breach_date": event["breach_date"]})
    if recommendations["add"]:
        alerts.append({"code": "S5_ADD_RECOMMENDATION", "grade": config["grades"]["ADD_RECOMMENDATION"]})
    if fail_closed_active:
        for alert in alerts:
            alert.setdefault("label", "UNVERIFIED")

    exposure_status = ("UNAVAILABLE" if effective is None else "UNVERIFIED" if fail_closed_active else "VERIFIED")
    available = [value for value in (float(nominal) if nominal is not None else None, volatility) if value is not None]
    review: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "artifact_type": ARTIFACT_TYPE,
        "display_only": True, "order_authority": False, "quantity_authority": "none", "execution_quantity": None,
        "recommendation_output": "target_weights_only",
        "policy": {"policy_version": config["policy_version"], "status": config["status"],
                   "target_exposure": _num(config["target"], 4), "reduce_when_exposure_gte": _num(config["reduce_gte"], 4),
                   "add_when_exposure_lte": _num(config["add_lte"], 4),
                   "hard_ceiling_when_exposure_gte": _num(config["hard_gte"], 4),
                   "single_stock_nominal_cap": _num(config["cap"], 4)},
        "evaluation_session": evaluation_session, "next_session": buy_session,
        "close_basis": {"definition": "FINAL_REGULAR_SESSION_30M_BAR_CLOSE", "label": "APPROXIMATE_CLOSE",
                        "official_close": False},
        "snapshot": None if current is None else {
            "as_of": current["as_of"], "state_revision": current.get("state_revision"),
            "age_calendar_days": (_date(evaluation_session) - _date(current["as_of"])).days,
            "later_reconciliations_not_used": later_reconciliations},
        "equity": {"status": "AVAILABLE" if equity is not None else "UNAVAILABLE", "closing_equity_usd": _money(equity),
                   "cash_usd": _money(_dec(current["cash_usd"])) if current is not None else None,
                   "cash_weight": _num(cash_weight)},
        "positions": [{
            "symbol": symbol, "registered": symbol in config["multipliers"],
            "nominal_multiplier": _num(config["multipliers"].get(symbol), 2),
            "close": (closes.get(symbol) or {}).get(evaluation_session), "weight": _num(weights.get(symbol)),
            "nominal_contribution": _num(weights[symbol] * config["multipliers"][symbol])
            if symbol in weights and symbol in config["multipliers"] else None,
            "single_stock_cap_applies": cap_limit(symbol, config) is not None or symbol not in config["multipliers"],
        } for symbol in sorted(holdings)],
        "exposure": {
            "status": exposure_status, "nominal": _num(nominal, 4), "sox_equivalent": _num(volatility, 4),
            "effective": _num(effective, 4),
            "effective_lower_bound": _num(max(available), 4) if available else None,
            "measure": "max(nominal, sox_equivalent_volatility_ratio)", "benchmark": config["benchmark"],
            "return_sessions_used": model.return_count, "window_sessions": config["window"],
            "minimum_sessions": config["minimum"], "window_start": model.window[0] if model.window else None,
            "window_end": model.window[-1] if model.window else None,
            "short_history": bool(model.volatility_available and model.short_history),
            "unavailable_reasons": list(model.reasons),
        },
        "band": {"state": band, "urgent_reduce": band == "HARD_CEILING",
                 "block_all_new_buys": band == "HARD_CEILING"},
        "single_stock_cap": {"breaches": [{"symbol": item["symbol"], "nominal": _num(item["nominal"]),
                                           "limit_weight": _num(item["limit_weight"]),
                                           "block_new_buy": True} for item in breaches]},
        "fail_closed": {
            "active": fail_closed_active,
            "triggers": [{"id": name, "active": bool(triggers[name]), "reasons": triggers[name]}
                         for name in FAIL_CLOSED_TRIGGERS],
            "pause": ["add_recommendations", "new_buy_recommendations"] if fail_closed_active else [],
            "continue_with_unverified_label": ["reduce_recommendations", "warnings"] if fail_closed_active else [],
        },
        "pauses": pauses, "review_lines": lines, "peak_reviews": peaks["items"],
        "recommendations": recommendations, "alerts": alerts,
        "activation": None if view["activation"] is None else {
            "activation_date": view["activation"]["activation_date"], "hwm_usd": _plain(view["activation"]["hwm"]),
            "hwm_as_of": view["activation"]["hwm_as_of"], "state_revision": view["activation"]["state_revision"],
            "entry_id": view["activation"]["entry_id"]},
        "activation_candidate": candidate,
    }
    if fail_closed_active:
        for item in recommendations["reduce"]:
            item["label"] = "UNVERIFIED"
    review["inputs"] = dict(inputs or {})
    review["review_id"] = review_content_hash(review)
    return review


def review_content_hash(review: dict[str, Any]) -> str:
    """review_id covers every field except itself."""
    return canonical_hash({key: value for key, value in review.items() if key != "review_id"})


def _evaluate_proposal(index: int, proposal: Any, *, config: dict[str, Any], weights: dict[str, Decimal], band: str,
                       pauses: dict[str, Any], blockers: Any, projection_model: Any,
                       equity_available: bool) -> dict[str, Any]:
    """Exposure-increasing requests that originate elsewhere: a new buy inside the band or a swap."""
    result: dict[str, Any] = {"index": index, "kind": None, "status": "OMITTED", "reasons": [], "legs": []}
    if not isinstance(proposal, dict) or proposal.get("kind") not in ("new_buy_within_band", "swap_buy_leg"):
        result["reasons"].append("PROPOSAL_KIND_INVALID")
        return result
    kind, symbol = proposal["kind"], str(proposal.get("symbol") or "")
    target = _dec(proposal.get("target_weight"))
    result["kind"] = kind
    if not equity_available or target is None or not ZERO < target <= ONE or target != floor_to_step(target):
        result["reasons"].append("PROPOSAL_TARGET_INVALID" if equity_available else "EQUITY_UNAVAILABLE")
        return result
    projected = dict(weights)
    if kind == "swap_buy_leg":
        sell_symbol, sell_target = str(proposal.get("sell_symbol") or ""), _dec(proposal.get("sell_target_weight"))
        if not sell_symbol or sell_target is None or sell_target < 0:
            result["reasons"].append("SWAP_SELL_LEG_INVALID")
            return result
        if sell_symbol in weights and sell_target < weights[sell_symbol]:
            # R9 step 1: the sell leg is shown first. The buy leg below is judged on the confirmed
            # holdings and verified cash only, so unsettled or expected sale proceeds never fund it.
            result["legs"].append({"action": "reduce", "symbol": sell_symbol, "step": 1,
                                   "current_weight": _num(weights[sell_symbol]),
                                   "target_weight": _num(sell_target, 3)})
            result["status"] = "SELL_LEG_ONLY"
    if target <= weights.get(symbol, ZERO):
        result["reasons"].append("PROPOSAL_NOT_AN_INCREASE")
        return result
    reasons = list(pauses["new_buy_recommendations"]["reasons"])
    if band == "UNAVAILABLE" and not reasons:
        reasons.append("EXPOSURE_UNAVAILABLE")
    reasons += blockers(symbol)
    if not reasons:
        model = projection_model([symbol])
        if not model.volatility_available:
            reasons.append(new_entry_block_reason(model))
        else:
            projected[symbol] = target
            reasons += projected_increase_reasons(model, projected, symbol, config)
    if reasons:
        result["reasons"] = reasons
        if kind == "swap_buy_leg":
            result["buy_leg"] = "WITHHELD"
        return result
    result["legs"].append({"action": "buy", "symbol": symbol, "current_weight": _num(weights.get(symbol, ZERO)),
                           "target_weight": _num(target, 3), "step": 2 if kind == "swap_buy_leg" else 1,
                           "alert_grade": config["max_add_grade"], "output": "display_only"})
    result["status"] = "DISPLAY"
    return result


# ---------------------------------------------------------------------------------------------
# Display (cards, fact pack, status): E, distance to the next line, pause state
# ---------------------------------------------------------------------------------------------

def exposure_display_block(review: dict[str, Any]) -> dict[str, Any]:
    """Small display-only block. It carries no target weights, quantities or amounts."""
    lines = review["review_lines"]
    next_line = lines.get("next_line") or {}
    return {
        "display_only": True, "source": ARTIFACT_TYPE, "review_id": review["review_id"],
        "evaluation_session": review["evaluation_session"], "close_label": review["close_basis"]["label"],
        "exposure_status": review["exposure"]["status"], "effective_exposure": review["exposure"]["effective"],
        "effective_exposure_lower_bound": review["exposure"]["effective_lower_bound"],
        "short_history": review["exposure"]["short_history"], "band_state": review["band"]["state"],
        "review_lines_status": lines["status"], "next_line_id": next_line.get("line_id"),
        "next_line_distance_pct": next_line.get("distance_pct"),
        "open_review_lines": [event["line_id"] for event in lines["open_events"]],
        "add_paused": review["pauses"]["add_recommendations"]["paused"],
        "new_buy_paused": review["pauses"]["new_buy_recommendations"]["paused"],
        "fail_closed_active": review["fail_closed"]["active"],
        "fail_closed_triggers": [item["id"] for item in review["fail_closed"]["triggers"] if item["active"]],
        "non_default_inputs": list((review.get("inputs") or {}).get("non_default_inputs") or []),
        "evaluation_session_status": (review.get("inputs") or {}).get("evaluation_session_status"),
    }


def display_block_errors(block: Any) -> list[str]:
    """Shape check before another artifact copies the block."""
    required = {"display_only": bool, "source": str, "review_id": str, "evaluation_session": str,
                "exposure_status": str, "band_state": str, "review_lines_status": str, "add_paused": bool,
                "new_buy_paused": bool, "fail_closed_active": bool, "short_history": bool}
    if not isinstance(block, dict):
        return ["EXPOSURE_DISPLAY_BLOCK_NOT_OBJECT"]
    errors = [f"EXPOSURE_DISPLAY_BLOCK_FIELD:{name}" for name, kind in required.items()
              if not isinstance(block.get(name), kind)]
    if block.get("display_only") is not True or block.get("source") != ARTIFACT_TYPE:
        errors.append("EXPOSURE_DISPLAY_BLOCK_NOT_DISPLAY_ONLY")
    return errors


def render_exposure_line(block: dict[str, Any], messages: dict[str, str]) -> str:
    """One line: E, distance to the next review line, pause state. Text comes from the locale file."""
    status, value = block["exposure_status"], block.get("effective_exposure")
    lower = block.get("effective_exposure_lower_bound")
    if status == "VERIFIED" and value is not None:
        exposure = messages["exposure_verified"].format(value=f"{value:.2f}")
    elif value is not None:
        exposure = messages["exposure_unverified"].format(value=f"{value:.2f}")
    elif lower is not None:
        exposure = messages["exposure_lower_bound"].format(value=f"{lower:.2f}")
    else:
        exposure = messages["exposure_unavailable"]
    if block.get("short_history"):
        exposure += messages["short_history_suffix"]
    if block.get("open_review_lines"):
        line = messages["line_open"].format(lines=", ".join(block["open_review_lines"]))
    elif block["review_lines_status"] == "NOT_ACTIVATED":
        line = messages["line_not_activated"]
    elif block["review_lines_status"] != "EVALUATED" or block.get("next_line_distance_pct") is None:
        line = messages["line_on_hold"]
    else:
        line = messages["line_distance"].format(line=block["next_line_id"],
                                                distance=f"{block['next_line_distance_pct']:.1f}")
    if block["add_paused"] and block["new_buy_paused"]:
        pause = messages["pause_add_and_new_buy"]
    elif block["new_buy_paused"]:
        pause = messages["pause_new_buy"]
    elif block["add_paused"]:
        pause = messages["pause_add"]
    else:
        pause = messages["pause_none"]
    text = messages["line_template"].format(exposure=exposure, line=line, pause=pause,
                                            session=block["evaluation_session"])
    if block.get("evaluation_session_status") not in (None, LATEST_SESSION_STATUS):
        text += messages["not_latest_session_suffix"]
    if block.get("non_default_inputs"):
        text += messages["non_default_suffix"]
    return text
