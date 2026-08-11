#!/usr/bin/env python3
"""Pure deterministic EMA timing rules for next-session human review candidates.

This module never places orders, infers fills, or mutates portfolio state.  It
only evaluates already-approved rules against a separately validated completed-
session snapshot.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from typing import Any


def finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _stable_hash(parts: list[Any], length: int = 20) -> str:
    encoded = "|".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def timing_anchor_errors(
    state: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    timing = policy.get("holding_timing_rules") or {}
    if timing.get("status") != "approved_review_only":
        return []
    state_plan = state.get("timing_plan") or {}
    errors: list[str] = []
    if state_plan.get("policy_version") != timing.get("policy_version"):
        errors.append("timing-plan policy version does not match active timing policy")
        return errors
    for symbol, rule in (timing.get("positions") or {}).items():
        plan = (state_plan.get("positions") or {}).get(symbol)
        if not isinstance(plan, dict):
            errors.append(f"{symbol}: timing-plan anchor is missing")
            continue
        anchor_shares = plan.get("anchor_shares")
        if not isinstance(anchor_shares, int) or anchor_shares <= 0:
            errors.append(f"{symbol}: timing-plan anchor shares are invalid")
            continue
        if anchor_shares != rule.get("anchor_shares"):
            errors.append(f"{symbol}: policy and state anchor shares disagree")
        completed = plan.get("completed_tranche_ids") or []
        if not isinstance(completed, list):
            errors.append(f"{symbol}: completed timing tranches must be a list")
            continue
        if len(completed) != len(set(completed)):
            errors.append(f"{symbol}: completed timing tranches contain duplicates")
            continue
        ordered_slots = list(rule.get("slots") or [])
        slots = {slot["id"]: slot for slot in ordered_slots}
        unknown = [item for item in completed if item not in slots]
        if unknown:
            errors.append(f"{symbol}: unknown completed timing tranche(s): {unknown}")
            continue
        expected_prefix = [slot["id"] for slot in ordered_slots[: len(completed)]]
        if completed != expected_prefix:
            errors.append(
                f"{symbol}: completed timing tranches must be the ordered slot prefix"
            )
            continue
        fill_records = plan.get("confirmed_tranche_fills") or {}
        if not isinstance(fill_records, dict):
            errors.append(f"{symbol}: confirmed tranche fills must be an object")
            continue
        if set(fill_records) != set(completed):
            errors.append(
                f"{symbol}: every completed tranche must have exactly one explicit confirmed fill record"
            )
            continue
        for tranche_id, record in fill_records.items():
            if not isinstance(record, dict):
                errors.append(f"{symbol}: confirmed fill record for {tranche_id} is invalid")
                continue
            session = record.get("session")
            try:
                date.fromisoformat(str(session))
            except ValueError:
                errors.append(
                    f"{symbol}: confirmed fill session for {tranche_id} is invalid"
                )
            trigger_path = record.get("trigger_path")
            if trigger_path not in set(slots[tranche_id].get("allowed_triggers") or []):
                errors.append(
                    f"{symbol}: confirmed fill trigger for {tranche_id} is not an approved slot trigger"
                )
            if record.get("quantity") != int(slots[tranche_id]["quantity"]):
                errors.append(
                    f"{symbol}: confirmed fill quantity for {tranche_id} does not equal the approved slot quantity"
                )
        sold = sum(int(slots[item]["quantity"]) for item in completed)
        expected = anchor_shares - sold
        current = (state.get("holdings") or {}).get(symbol)
        if current != expected:
            errors.append(
                f"{symbol}: holdings {current!r} do not equal anchor less confirmed tranches {expected}"
            )
    return errors


def _next_open_slot(rule: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any] | None:
    completed = set(plan.get("completed_tranche_ids") or [])
    for slot in rule.get("slots") or []:
        if slot.get("id") not in completed:
            return slot
    return None


def _proxy_negative(row: dict[str, Any], ema: int) -> bool:
    key = f"ema{ema}"
    direction_key = f"ema{ema}_direction_3d"
    return bool(
        finite(row.get("close"))
        and finite(row.get(key))
        and float(row["close"]) < float(row[key])
        and row.get(direction_key) != "rising"
    )


def _proxy_positive(row: dict[str, Any], ema: int) -> bool:
    key = f"ema{ema}"
    direction_key = f"ema{ema}_direction_3d"
    return bool(
        finite(row.get("close"))
        and finite(row.get(key))
        and float(row["close"]) > float(row[key])
        and row.get(direction_key) != "falling"
    )


def technical_stop_state(
    row: dict[str, Any], hard_boundary: float
) -> tuple[bool, float | None, list[str]]:
    required = (
        "close",
        "close_prev",
        "ema20",
        "ema20_prev",
        "atr14",
        "atr14_prev",
        "prior_10d_low",
        "prior_10d_low_prev",
    )
    if not all(finite(row.get(field)) for field in required):
        return False, None, ["technical stop inputs are incomplete"]
    atr = float(row["atr14"])
    prior_atr = float(row["atr14_prev"])
    level = max(
        float(row["prior_10d_low"]) - 0.25 * atr,
        float(row["ema20"]) - 0.75 * atr,
        hard_boundary,
    )
    prior_level = max(
        float(row["prior_10d_low_prev"]) - 0.25 * prior_atr,
        float(row["ema20_prev"]) - 0.75 * prior_atr,
        hard_boundary,
    )
    decisive = float(row["close"]) <= level - 0.25 * atr
    two_close = float(row["close"]) <= level and float(row["close_prev"]) <= prior_level
    return decisive or two_close, level, []


def _technical_stop_levels(
    row: dict[str, Any], hard_boundary: float
) -> tuple[float | None, float | None]:
    required = (
        "ema20",
        "ema20_prev",
        "atr14",
        "atr14_prev",
        "prior_10d_low",
        "prior_10d_low_prev",
    )
    if not all(finite(row.get(field)) for field in required):
        return None, None
    current = max(
        float(row["prior_10d_low"]) - 0.25 * float(row["atr14"]),
        float(row["ema20"]) - 0.75 * float(row["atr14"]),
        hard_boundary,
    )
    prior = max(
        float(row["prior_10d_low_prev"]) - 0.25 * float(row["atr14_prev"]),
        float(row["ema20_prev"]) - 0.75 * float(row["atr14_prev"]),
        hard_boundary,
    )
    return current, prior


def _explicit_halt_flag(row: dict[str, Any]) -> bool:
    """Recognize only an explicit provider flag; zero volume alone is not a halt."""
    value = str(row.get("trading_status") or row.get("market_status") or "").strip().lower()
    return value in {"halted", "paused", "suspended", "trading_halt"}


def _gap_risk_state(row: dict[str, Any], prior_stop_level: float | None) -> tuple[bool, dict[str, Any]]:
    if not all(finite(row.get(field)) for field in ("open", "close_prev", "atr14")):
        return False, {
            "gap_limit_fraction": None,
            "gap_through_prior_technical_stop": False,
        }
    prior_close = float(row["close_prev"])
    opening_gap = float(row.get("opening_gap_fraction", float(row["open"]) / prior_close - 1))
    gap_limit = max(0.05, float(row["atr14"]) / prior_close)
    gap_through_stop = bool(
        prior_stop_level is not None and float(row["open"]) <= prior_stop_level
    )
    return bool(abs(opening_gap) > gap_limit or gap_through_stop), {
        "opening_gap_fraction": opening_gap,
        "gap_limit_fraction": gap_limit,
        "gap_through_prior_technical_stop": gap_through_stop,
    }


def _post_fill_rearm_evidence(
    *,
    row: dict[str, Any],
    proxy: dict[str, Any],
    plan: dict[str, Any],
    rearm_policy: dict[str, Any],
) -> dict[str, Any]:
    """Verify an EMA recovery after the latest explicitly confirmed reduction.

    This is derived from the validated timing windows.  It never marks a fill or
    persists portfolio state.  If the confirmed fill predates the available
    timing window, the gate fails closed until evidence is available.
    """
    completed = list(plan.get("completed_tranche_ids") or [])
    if not completed:
        return {
            "required": False,
            "passed": True,
            "reason": "initial reduction slot does not require post-fill rearm",
            "ema": None,
            "latest_confirmed_tranche_id": None,
            "latest_confirmed_fill_session": None,
            "recovery_sessions": [],
        }
    fill_records = plan.get("confirmed_tranche_fills") or {}
    latest_id = completed[-1]
    latest_record = fill_records.get(latest_id) or {}
    fill_session = latest_record.get("session")
    confirmed_trigger = latest_record.get("trigger_path")
    ema_map = rearm_policy.get("required_ema_by_confirmed_trigger") or {}
    ema = int(ema_map.get(confirmed_trigger, 20))
    key = f"ema{ema}"
    own_window = row.get("timing_window") or []
    proxy_window = proxy.get("timing_window") or []
    own = {
        item.get("bar_date"): item
        for item in own_window
        if isinstance(item, dict) and isinstance(item.get("bar_date"), str)
    }
    other = {
        item.get("bar_date"): item
        for item in proxy_window
        if isinstance(item, dict) and isinstance(item.get("bar_date"), str)
    }
    common_sessions = sorted(set(own) & set(other))
    post_fill = [session for session in common_sessions if fill_session and session > fill_session]
    recovery = [
        session
        for session in post_fill
        if finite(own[session].get("close"))
        and finite(own[session].get(key))
        and finite(other[session].get("close"))
        and finite(other[session].get(key))
        and float(own[session]["close"]) > float(own[session][key])
        and float(other[session]["close"]) > float(other[session][key])
    ]
    minimum = int(rearm_policy.get("minimum_common_recovery_sessions", 1))
    cooldown = int(rearm_policy.get("minimum_completed_sessions_after_fill", 0))
    cooldown_passed = len(post_fill) >= cooldown
    passed = len(recovery) >= minimum and cooldown_passed
    return {
        "required": True,
        "passed": passed,
        "reason": (
            f"position and confirmation proxy recovered above {key} after the latest confirmed reduction"
            if passed
            else (
                f"no verified common-session recovery above {key} after the latest confirmed reduction"
                if len(recovery) < minimum
                else f"post-reduction cooldown has only {len(post_fill)} of {cooldown} required completed sessions"
            )
        ),
        "ema": ema,
        "latest_confirmed_tranche_id": latest_id,
        "latest_confirmed_fill_session": fill_session,
        "latest_confirmed_trigger_path": confirmed_trigger,
        "recovery_sessions": recovery,
        "completed_sessions_after_fill": len(post_fill),
        "minimum_completed_sessions_after_fill": cooldown,
        "cooldown_passed": cooldown_passed,
    }


def _trigger_states(
    symbol: str,
    row: dict[str, Any],
    proxy: dict[str, Any],
    average_cost: float,
    hard_boundary: float,
) -> tuple[dict[str, bool], dict[str, Any], list[str]]:
    technical_stop, stop_level, warnings = technical_stop_state(row, hard_boundary)
    _, prior_stop_level = _technical_stop_levels(row, hard_boundary)
    gap_risk, gap_diagnostics = _gap_risk_state(row, prior_stop_level)
    halt_risk = _explicit_halt_flag(row)
    close = float(row["close"])
    weakness10 = bool(
        row.get("close_below_ema10_consecutive", 0) >= 2
        and row.get("ema10_direction_3d") == "falling"
        and _proxy_negative(proxy, 10)
    )
    weakness20 = bool(
        row.get("decisive_breach_ema20") is True
        and row.get("ema10_above_ema20") is False
        and _proxy_negative(proxy, 20)
        and proxy.get("ema10_above_ema20") is False
    )
    failed_reclaim = bool(
        row.get("ema20_failed_reclaim_confirmed") is True
        and _proxy_negative(proxy, 20)
    )
    strength10 = bool(
        row.get("ema10_reclaim_confirmed") is True and _proxy_positive(proxy, 10)
    )
    strength20 = bool(
        row.get("ema20_reclaim_confirmed") is True and _proxy_positive(proxy, 20)
    )
    strength_extension = bool(
        (close >= float(row["prior_20d_high"]) or row.get("overheat_rejection_confirmed") is True)
        and _proxy_positive(proxy, 20)
    )
    take_profit = bool(
        close > average_cost
        and (
            row.get("overheat_rejection_confirmed") is True
            or row.get("failed_higher_high_confirmed") is True
        )
    )
    return (
        {
            "technical_stop": technical_stop,
            "weakness_20ema": weakness20,
            "weakness_failed_reclaim": failed_reclaim,
            "weakness_10ema": weakness10,
            "strength_20ema_reclaim": strength20,
            "strength_10ema_reclaim": strength10,
            "strength_extension": strength_extension,
            "take_profit_rejection": take_profit,
            "gap_risk": gap_risk,
            "halt_risk": halt_risk,
        },
        {
            "technical_stop_level_usd": stop_level,
            "prior_technical_stop_level_usd": prior_stop_level,
            **gap_diagnostics,
            "explicit_halt_flag": halt_risk,
        },
        warnings,
    )


TRIGGER_PRIORITY = [
    "technical_stop",
    "weakness_20ema",
    "weakness_failed_reclaim",
    "weakness_10ema",
    "strength_20ema_reclaim",
    "strength_10ema_reclaim",
    "strength_extension",
    "take_profit_rejection",
]

WATCH_TRIGGER_PRIORITY = ["halt_risk", "gap_risk", "weakness_10ema"]
REARMED_REDUCTION_TRIGGERS = {
    "technical_stop",
    "weakness_20ema",
    "weakness_failed_reclaim",
    "weakness_10ema",
}


def evaluate_holding_timing(
    *,
    state: dict[str, Any],
    policy: dict[str, Any],
    symbol: str,
    row: dict[str, Any],
    proxy_row: dict[str, Any],
    hard_boundary: float,
    rules_hash: str,
    suppress_for_hard_risk: bool,
) -> tuple[dict[str, Any] | None, list[str]]:
    timing = policy.get("holding_timing_rules") or {}
    if timing.get("status") != "approved_review_only":
        return None, []
    rule = (timing.get("positions") or {}).get(symbol)
    plan = ((state.get("timing_plan") or {}).get("positions") or {}).get(symbol)
    if not isinstance(rule, dict) or not isinstance(plan, dict):
        return None, [f"{symbol}: active timing rule or anchor is missing"]
    slot = _next_open_slot(rule, plan)
    if slot is None:
        return None, []

    average_cost = float((state.get("average_cost_usd") or {})[symbol])
    states, diagnostics, warnings = _trigger_states(
        symbol, row, proxy_row, average_cost, hard_boundary
    )
    allowed = set(slot.get("allowed_triggers") or [])
    rearm_policy = timing.get("weakness_rearm") or {}
    rearm_by_trigger: dict[str, dict[str, Any]] = {}
    for name in REARMED_REDUCTION_TRIGGERS:
        rearm_by_trigger[name] = _post_fill_rearm_evidence(
            row=row,
            proxy=proxy_row,
            plan=plan,
            rearm_policy=rearm_policy,
        )
    watch_only = set(rule.get("watch_only_triggers") or [])
    blocking_watch_trigger = next(
        (
            name
            for name in ("halt_risk", "gap_risk")
            if name in watch_only and states.get(name)
        ),
        None,
    )
    trigger = None if blocking_watch_trigger else next(
        (
            name
            for name in TRIGGER_PRIORITY
            if name in allowed
            and states.get(name)
            and (
                name not in REARMED_REDUCTION_TRIGGERS
                or rearm_by_trigger[name].get("passed") is True
            )
        ),
        None,
    )
    watch_trigger = blocking_watch_trigger or (None if trigger else next(
        (
            name
            for name in WATCH_TRIGGER_PRIORITY
            if name in watch_only and states.get(name)
        ),
        None,
    ))
    grade = "B" if (trigger or watch_trigger) and not suppress_for_hard_risk else "E"
    if suppress_for_hard_risk and trigger:
        warnings.append(f"{symbol}: timing review suppressed by higher-priority hard-risk event")
    event_type = "holding_timing_watch" if watch_trigger else "holding_timing_review"
    side = "observe" if watch_trigger else "reduce"
    event_key = _stable_hash(
        [
            state.get("strategy_version"),
            rules_hash,
            timing.get("policy_version"),
            symbol,
            slot.get("id"),
            side,
            plan.get("anchor_id"),
        ]
    )
    quantity = int(slot["quantity"])
    fingerprint = _stable_hash(
        [event_key, grade, quantity if trigger else None, trigger or watch_trigger or "condition_false"]
    )
    current_shares = int((state.get("holdings") or {})[symbol])
    return (
        {
            "event_type": event_type,
            "symbol": symbol,
            "side": side,
            "quantity": quantity if grade == "B" and trigger else None,
            "actionable": False,
            "maximum_grade": "B",
            "tranche_id": slot.get("id"),
            "trigger_path": trigger or watch_trigger,
            "trigger_states": states,
            "watch_only": bool(watch_trigger),
            "rearm_gate": (
                rearm_by_trigger.get(trigger)
                if trigger in REARMED_REDUCTION_TRIGGERS
                else rearm_by_trigger.get(watch_trigger)
                if watch_trigger in REARMED_REDUCTION_TRIGGERS
                else None
            ),
            "current_shares": current_shares,
            "post_trade_shares": current_shares - quantity if grade == "B" and trigger else None,
            "close": float(row["close"]),
            "average_cost_usd": average_cost,
            "hard_boundary_usd": hard_boundary,
            "technical_stop_level_usd": diagnostics.get("technical_stop_level_usd"),
            "prior_technical_stop_level_usd": diagnostics.get("prior_technical_stop_level_usd"),
            "gap_diagnostics": {
                "opening_gap_fraction": diagnostics.get("opening_gap_fraction"),
                "gap_limit_fraction": diagnostics.get("gap_limit_fraction"),
                "gap_through_prior_technical_stop": diagnostics.get(
                    "gap_through_prior_technical_stop"
                ),
            },
            "explicit_halt_flag": diagnostics.get("explicit_halt_flag"),
            "proxy_symbol": rule.get("confirmation_symbol"),
            "grade": grade,
            "event_key": event_key,
            "signal_fingerprint": fingerprint,
            "delivery_id": None,
            "duplicate": False,
            "suppressed_reason": None,
            "missing_conditions": (
                []
                if grade == "B"
                else [
                    "no approved trigger is active for the next unlocked tranche",
                    *(
                        [
                            evidence["reason"]
                            for name, evidence in rearm_by_trigger.items()
                            if name in allowed
                            and states.get(name)
                            and evidence.get("passed") is not True
                        ]
                    ),
                ]
            ),
            "validity": "next_regular_session_only",
            "fill_policy": "unlock the next tranche only after an explicit confirmed fill",
        },
        warnings,
    )


def watch_setup(
    row: dict[str, Any], *, leveraged: bool = False, proxy_row: dict[str, Any] | None = None
) -> dict[str, Any]:
    aligned = bool(
        float(row["close"]) > float(row["ema20"])
        and row.get("ema10_above_ema20") is True
        and row.get("ema10_direction_3d") == "rising"
        and row.get("ema20_direction_3d") == "rising"
    )
    extension = float(row["extension_above_ema20_atr"])
    dollar_volume_ok = float(row["average_dollar_volume_20d_usd"]) >= 10_000_000
    gap_limit = max(0.05, float(row["atr14"]) / float(row["close_prev"]))
    gap_ok = abs(float(row["opening_gap_fraction"])) <= gap_limit
    proxy_ok = True
    if leveraged:
        proxy_ok = bool(
            proxy_row
            and finite(row.get("ma50"))
            and finite(row.get("ma50_5d_ago"))
            and float(proxy_row["close"]) > float(proxy_row["ema20"])
            and proxy_row.get("ema10_above_ema20") is True
            and proxy_row.get("ema20_direction_3d") == "rising"
            and (
                float(row["close"]) >= float(row["ma50"])
                or float(row["ma50"]) >= float(row["ma50_5d_ago"])
            )
        )
    pullback = bool(
        aligned
        and (row.get("ema10_reclaim_confirmed") or row.get("ema20_reclaim_confirmed"))
        and extension <= 1.5
        and dollar_volume_ok
        and gap_ok
        and proxy_ok
    )
    breakout = bool(
        aligned
        and row.get("breakout_acceptance_confirmed") is True
        and extension <= 2.0
        and dollar_volume_ok
        and gap_ok
        and proxy_ok
    )
    setup = (
        "aligned_uptrend_pullback_reclaim"
        if pullback
        else "aligned_uptrend_breakout_acceptance"
        if breakout
        else None
    )
    return {
        "setup": setup,
        "technical_setup_detected": setup is not None,
        "aligned_uptrend": aligned,
        "liquidity_gate": dollar_volume_ok,
        "gap_gate": gap_ok,
        "leveraged_proxy_gate": proxy_ok,
        "maximum_grade": "B",
    }


def self_test() -> None:
    row = {
        "close": 110.0,
        "close_prev": 108.0,
        "ema10": 106.0,
        "ema20": 104.0,
        "ema20_prev": 103.0,
        "ema10_above_ema20": True,
        "ema10_direction_3d": "rising",
        "ema20_direction_3d": "rising",
        "atr14": 4.0,
        "atr14_prev": 4.0,
        "prior_10d_low": 100.0,
        "prior_10d_low_prev": 99.0,
        "prior_20d_high": 109.0,
        "close_below_ema10_consecutive": 0,
        "decisive_breach_ema20": False,
        "ema20_failed_reclaim_confirmed": False,
        "ema10_reclaim_confirmed": True,
        "ema20_reclaim_confirmed": False,
        "overheat_rejection_confirmed": False,
        "failed_higher_high_confirmed": False,
        "average_dollar_volume_20d_usd": 50_000_000.0,
        "opening_gap_fraction": 0.01,
        "extension_above_ema20_atr": 1.5,
        "ma50": 100.0,
        "ma50_5d_ago": 99.0,
    }
    proxy = dict(row)
    assert watch_setup(row)["technical_setup_detected"] is True
    hit, level, errors = technical_stop_state(row, 80.0)
    assert hit is False and level is not None and not errors
    print(json.dumps({"status": "passed", "technical_stop": level}))


if __name__ == "__main__":
    self_test()
