#!/usr/bin/env python3
"""Redesign T2 F4-F6: buy requirements, gates G0-G5, the order-ticket calculator and outcome classification.

Order stage 1 (ORDER_INTENT): a ticket carries a LOC quantity and price for the user to enter in Kiwoom.
order_authority stays false, execution_quantity null; only a ticket carries
quantity_authority "ORDER_TICKET_HUMAN_ENTRY". There is no order path here: fills come only from the
broker's daily order-fill rows (ust21150 cntr_qty, cntr_uv) and nothing is inferred from a price.

Sizing is the order-instruction design section 7 (docs/claude/order-instruction-design-2026-10-06.md):
policy gap x step r (r from the evidence ladder G3, then the section 5 regret table, which only lowers it),
first entry 1/2, then the cash (G4), deadband and lot checks, which only lower it. The buy target is whatever
the S7 module's proposal evaluation (new_buy_within_band) passes on its 0.001 grid: no new exposure maths.
Pure functions: inputs are passed in; nothing here reads a file, a clock or the network.
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Any, Callable
from zoneinfo import ZoneInfo

from auto_core_reconcile import _clock as order_clock  # T1's ust21150 ord_time reading (KST, "17:29:23" or "172923")
from portfolio_exposure import WEIGHT_STEP, earnings_blackout, effective_exposure, floor_to_step

import auto_core_rules as rules


KST = ZoneInfo("Asia/Seoul")
CENT = Decimal("0.01")
# value, source (prompt D16: gate values are copied, never changed here).
SIZING: dict[str, tuple[Any, str]] = {
    "STEPS": ((Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(1)), "design 5 / 7-1 2: steps 0, 1/3, 1/2, 1"),
    "C_ONLY_R_CAP": (Fraction(1, 3), "design 3 G3: common rule C alone caps the step at 1/3 (user decision Q2 a')"),
    "REGRET_BUDGET": (Decimal("0.03"), "design 5 / 13 K3-2: regret budget 3% of equity"),
    "DEADBAND": (Decimal("0.02"), "design 7-1 4 / K3-2: ticket amount < 2% of equity -> no ticket"),
    "FIRST_ENTRY": (Decimal("0.5"), "design 7-1 1: first entry at most 1/2 of the whole target"),
    "CASH_BUFFER": (Decimal("0.0025"), "design 3 G4: qty x LOC cap x (1 + 0.25%) <= order-available cash"),
    "SCENARIO_RETURNS": (60, "design 5: 5-session returns of the last 60 sessions (60 returns, 65 closes)"),
    "SCENARIO_HORIZON": (5, "design 5: 5-session return"),
    "UP_QUANTILE": (0.9, "design 5: 90th percentile (linear interpolation, numpy 'linear')"),
    "DOWN_QUANTILE": (0.1, "design 5: 10th percentile"),
    "TAIL_SESSIONS": (60, "design 5: worst 1-day return of the last 60 sessions (display row)"),
    "BUY_CAP_SIGMA": (Decimal("0.5"), "design 7-2: planned buy LOC cap = reference x (1 + 0.5 sigma60)"),
    "SELL_FLOOR_SIGMA": (Decimal("1"), "design 7-2: planned reduce LOC floor = reference x (1 - sigma60)"),
    "PRICE_RANGE": (Decimal("0.01"), "design 9-1 2-2: valid range = approximate close +/- 1%"),
    "MULT_PLACES": (Decimal("0.0001"), "design 9-1 2-2: multiplier to 4 decimals (10/9 SOXL-2 0.9165)"),
    "TICKET_FEE_RATE": (Decimal("0.0025"), "dashboard-order-panel 3 feeRate default 0.0025"),
    "MEASURED_FEE_RATE": (Decimal("0.000699"), "redesign-t2-measurements fees_measured (check line display only)"),
    "R1_ATR_MULT": (Decimal("0.75"), "trade-timing-validation.md Stop and invalidation: 20EMA - 0.75 ATR14; display-only 1R (user decision ext-1012-setup B, 2026-10-12)"),
}
S = {name: value for name, (value, _source) in SIZING.items()}
# Policy values the code relies on; checked against alert_policy through the S7 review on every run.
POLICY_EXPECTED = {"target_exposure": 1.55, "reduce_when_exposure_gte": 1.85,
                   "hard_ceiling_when_exposure_gte": 1.9, "single_stock_nominal_cap": 0.4}
# Rule file 3) buy requirement (2): approved new-buy products (PWR, LITE: user approval 2026-10-08).
APPROVED_BUY = ("BE", "MU", "NBIS", "DELL", "AMD", "SOXL", "TQQQ", "DRAM", "PWR", "LITE")
INDEX_ETFS = ("SOXL", "TQQQ", "DRAM")
# Rule file 2-3) (1): not in the policy multipliers but counted as 1x in N (user-approved stocks, MVLL's base).
ONE_X_UNREGISTERED = ("PWR", "LITE", "MRVL")
ALLOWED_NO_TICKET = ("DEADBAND", "LOT_ZERO", "CASH_ZERO", "REGRET_ZERO", "G2B_CAP")
AUTHORITY = {"order_authority": False, "quantity_authority": "ORDER_TICKET_HUMAN_ENTRY", "execution_quantity": None}
SIDE_NAMES = {"sell": "\ub9e4\ub3c4", "buy": "\ub9e4\uc218"}  # Korean side names in ust21150 slby_tp_nm
LOC_TYPE = "Limit On Close"  # ust21150 frgn_trde_tp of a LOC order (measurements 2026-10-10)
ATTRIBUTION_DAYS = 30  # r4 R4-1: attributed order days kept (run day included); no ticket window reaches further back
ISSUED_AT = re.compile(r"\d{4}-\d{2}-\d{2} ([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))? KST")  # ticket issuedAt


def fraction_text(value: Fraction) -> str:
    return "0" if value == 0 else str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _money(value: Decimal) -> float:
    return float(value.quantize(CENT))


# ---------------------------------------------------------------------------------------------
# Evidence (G3) and buy requirement (3)
# ---------------------------------------------------------------------------------------------

def official_evidence(symbol: str, facts: list[dict[str, Any]], *, evaluation_session: str,
                      previous_session: str | None, seen_fact_ids: set[str]) -> dict[str, list[str]]:
    """Official facts counted as strong evidence, new ones only (F3): + with criterion (a); - of the kill,
    dilution, customer-change or guidance kind. New = event on the evaluation session, or on the session
    before it and not in the previous decide record."""
    out: dict[str, list[str]] = {"+": [], "-": []}
    for fact in facts:
        if fact["symbol"] != symbol:
            continue
        new = fact["event_session"] == evaluation_session or (
            previous_session is not None and fact["event_session"] == previous_session
            and fact["fact_id"] not in seen_fact_ids)
        if not new:
            continue
        if fact["direction"] == "+" and fact.get("criterion_a") is True:
            out["+"].append(fact["fact_id"])
        elif fact["direction"] == "-" and fact["kind"] in rules.OFFICIAL_MINUS_KINDS:
            out["-"].append(fact["fact_id"])
    return out


def evidence_summary(*, side: str, result: dict[str, Any], check: dict[str, Any], official: dict[str, list[str]],
                     config: dict[str, Any]) -> dict[str, Any]:
    """Evidence of one direction for one symbol: strong / weak kinds, the step ceiling r_max (G3), whether
    the evidence that appeared today alone meets the basis (circuit), and the composition label."""
    direction = "+" if side == "buy" else "-"
    price = rules.price_evidence(result, direction)
    entry = check.get("entry") or {}
    static = [item for item in entry.get("static_evidence") or []
              if check.get("hash_ok") and item["direction"] == direction and item["strength"] != "neutral"
              and side == "buy"]
    static_strong = [item["id"] for item in static if item["strength"] == "strong"]
    static_weak_kinds = sorted({item["e1_kind"] for item in static if item["strength"] == "weak"})
    official_ids = list(official.get(direction) or [])
    strong = static_strong + official_ids
    weak_kinds = sorted(set(static_weak_kinds) | set(price["groups"]))
    new_strong = official_ids
    new_kinds = price["new_groups"]
    r_max = Fraction(1) if strong else Fraction(1, 2) if len(weak_kinds) >= 2 else Fraction(0)
    common_only = bool(price["groups"]) and not strong and not static_weak_kinds and not price["card_defined"]
    if common_only:
        r_max = min(r_max, S["C_ONLY_R_CAP"])
    cap = config.get("research_only_strong_r_cap")
    research_only = bool(official_ids) and not static_strong
    if research_only and cap is not None:
        r_max = min(r_max, Fraction(str(cap)))
    if not check.get("eligible"):
        r_max = Fraction(0)
    composition = ("C \ub2e8\ub3c5" if common_only else  # "C \ub2e8\ub3c5"
                   "\uce74\ub4dc \ud45c {} + \uc0c8 {}".format(len(static_strong) + len(static_weak_kinds),
                                                         len(new_strong) + len(new_kinds)))
    return {
        "side": side, "strong": strong, "weak_kinds": weak_kinds, "static_strong": static_strong,
        "static_weak_kinds": static_weak_kinds, "price_groups": price["groups"], "price_ids": price["ids"],
        "official": official_ids, "new_strong": new_strong, "new_kinds": new_kinds,
        "basis_met": bool(strong) or len(weak_kinds) >= 2,
        "new_basis_met": bool(new_strong) or len(new_kinds) >= 2,
        "common_only": common_only, "research_only_strong": research_only,
        "r_max": fraction_text(r_max), "composition": composition,
        "ids": sorted(set(strong) | set(price["ids"]) | {f"{check.get('symbol')}:{kind}" for kind in static_weak_kinds}),
    }


# ---------------------------------------------------------------------------------------------
# Exposure block (rule file N, S7 values) and buy requirements 1-6
# ---------------------------------------------------------------------------------------------

def rule_file_nominal(holdings: dict[str, int], closes: dict[str, Decimal | None], cash: Decimal | None,
                      multipliers: dict[str, Any]) -> dict[str, Any]:
    """N = sum(multiplier x weight), weight = value / (sum(poss_qty x close) + cash) (rule file 1) and 2-3)(1)).
    cash = the USD cash of the total equity, auto_core_decide.equity_cash's choice (t2-equity-cash 2026-10-13:
    Kiwoom order-available behind T1's cash check, else the smallest known snapshot cash value; the fc_entra the
    rule file names holds settled money only, T1 F1). The total also feeds V6 and EV4.
    PWR, LITE, MRVL count as 1x (labelled); any other unregistered holding makes N unknown."""
    values: dict[str, Decimal] = {}
    for symbol, quantity in holdings.items():
        close = closes.get(symbol)
        if close is None:
            return {"n": None, "status": f"CLOSE_MISSING:{symbol}", "total": None, "assumed_one_x": []}
        values[symbol] = Decimal(quantity) * close
    if cash is None:
        return {"n": None, "status": "CASH_UNAVAILABLE", "total": None, "assumed_one_x": []}
    total = sum(values.values(), Decimal(0)) + cash
    assumed = sorted(symbol for symbol in values if symbol not in multipliers and symbol in ONE_X_UNREGISTERED)
    unknown = sorted(symbol for symbol in values if symbol not in multipliers and symbol not in ONE_X_UNREGISTERED)
    if unknown:
        return {"n": None, "status": "MULTIPLIER_UNREGISTERED:" + ",".join(unknown), "total": total,
                "assumed_one_x": assumed}
    if total <= 0:
        return {"n": None, "status": "TOTAL_NOT_POSITIVE", "total": total, "assumed_one_x": assumed}
    n = sum((Decimal(str(multipliers.get(symbol, 1))) * value for symbol, value in values.items()), Decimal(0)) / total
    weights = {symbol: value / total for symbol, value in values.items()}
    single = {symbol: Decimal(str(multipliers.get(symbol, 1))) * weight for symbol, weight in weights.items()
              if symbol not in INDEX_ETFS}
    return {"n": float(n), "status": "OK", "total": total, "assumed_one_x": assumed,
            "single_nominal": {symbol: float(value) for symbol, value in single.items()}}


def s7_summary(review: dict[str, Any] | None, evaluation_session: str, previous_session: str | None) -> dict[str, Any]:
    if not review:
        return {"present": False, "fresh": False, "latest": False}
    session = review.get("evaluation_session")
    exposure = review.get("exposure") or {}
    return {
        "present": True, "session": session, "latest": session == evaluation_session,
        "fresh": session in (evaluation_session, previous_session), "e": exposure.get("effective"),
        "n": exposure.get("nominal"), "v": exposure.get("sox_equivalent"), "status": exposure.get("status"),
        "band": (review.get("band") or {}).get("state"),
        "new_buy_paused": (review.get("pauses") or {}).get("new_buy_recommendations", {}).get("paused"),
        "add_paused": (review.get("pauses") or {}).get("add_recommendations", {}).get("paused"),
        "fail_closed": (review.get("fail_closed") or {}).get("active"),
        "fail_closed_triggers": [item["id"] for item in (review.get("fail_closed") or {}).get("triggers") or []
                                 if item.get("active")],
        "cap_breaches": [item["symbol"] for item in (review.get("single_stock_cap") or {}).get("breaches") or []],
        "hwm_usd": (review.get("review_lines") or {}).get("hwm_usd"),
        "policy": review.get("policy") or {},
    }


def policy_mismatches(s7: dict[str, Any]) -> list[str]:
    policy = s7.get("policy") or {}
    return [f"POLICY_THRESHOLD_CHANGED:{key}" for key, value in POLICY_EXPECTED.items()
            if policy.get(key) is None or abs(float(policy[key]) - value) > 1e-9]


def buy_requirements(*, symbol: str, held: bool, s7: dict[str, Any], nominal: dict[str, Any],
                     peaks: dict[str, dict[str, Any]], earnings: dict[str, Any] | None, calendar_sessions: list[str],
                     buy_session: str | None, evaluation_session: str, generated_at: str | None,
                     cash: Decimal | None, close: Decimal | None, check: dict[str, Any], evidence: dict[str, Any],
                     watch_status: str | None, m6: dict[str, Any], shock: dict[str, Any],
                     research_block: str | None) -> dict[str, Any]:
    """The rule file's buy-requirement row (cells ok|no|unk|wait with a one-line text) for one symbol.
    research_block: why today's research record is not OK (None = OK)."""
    cells: list[dict[str, str]] = []
    # (1) earnings blackout (index ETFs have no earnings date, but without an OK research record they are not ok
    # either: r2 R2-1, every buy needs it).
    if symbol in INDEX_ETFS and research_block is not None:
        cells.append({"s": "no", "t": "\ub9c9\ud798 RESEARCH_RECORD_NOT_OK:" + research_block})
    elif symbol in INDEX_ETFS:
        cells.append({"s": "ok", "t": "\ud1b5\uacfc (\uc9c0\uc218 ETF \u2014 \ud574\ub2f9 \uc5c6\uc74c)"})
    else:
        blackout, code = earnings_blackout(symbol, earnings, calendar_sessions, buy_session,
                                           evaluation_session=evaluation_session, generated_at=generated_at)
        cells.append({"s": "no" if blackout else "ok", "t": ("\ub9c9\ud798 " if blackout else "\ud1b5\uacfc ") + code})
    # (2) exposure, cash, product approval.
    reasons = []
    unknown = False
    if nominal.get("n") is None:
        reasons.append("N " + str(nominal.get("status")))
    elif nominal["n"] >= POLICY_EXPECTED["reduce_when_exposure_gte"]:
        reasons.append(f"N {nominal['n']:.2f} \u2265 1.85")
    if not s7.get("fresh"):
        reasons.append("S7 \uac80\ud1a0 \uc5c6\uc74c/\uc624\ub798\ub428")
    elif s7.get("e") is None or s7["e"] >= POLICY_EXPECTED["reduce_when_exposure_gte"]:
        reasons.append(f"E {s7.get('e')} \u2265 1.85" if s7.get("e") is not None else "E \uc5c6\uc74c")
    if s7.get("new_buy_paused"):
        reasons.append("S7 \uc2e0\uaddc \ub9e4\uc218 \uba48\ucda4")
    if held:
        if s7.get("add_paused"):
            reasons.append("S7 \ucd94\uac00 \uba48\ucda4")
        if symbol in (s7.get("cap_breaches") or []) or (nominal.get("single_nominal") or {}).get(symbol, 0) > \
                POLICY_EXPECTED["single_stock_nominal_cap"]:
            reasons.append("\uc885\ubaa9 \uc0c1\ud55c")
        if rules.r5_state(peaks.get(symbol) or {}) == "review":
            reasons.append("R5 \uac80\ud1a0")
    if cash is None:
        unknown = True
        reasons.append("\ud604\uae08 \ud655\uc778 \ud544\uc694")
    elif close is not None and cash < close:
        reasons.append(f"\ud604\uae08 ${cash} < 1\uc8fc")
    if symbol not in APPROVED_BUY:
        reasons.append("\uc0c1\ud488 \uc2b9\uc778 \uc5c6\uc74c")
    cells.append({"s": "unk" if unknown and len(reasons) == 1 else "no" if reasons else "ok",
                  "t": ("\ub9c9\ud798 " + " \u00b7 ".join(reasons)) if reasons else
                  f"\ud1b5\uacfc (E {s7.get('e')} \u00b7 \ud604\uae08 ${cash})"})
    # (3) evidence: card table N + new M; a watch card that is not accepted needs checking.
    entry_missing = check.get("entry") is None
    if not held and (entry_missing or not str(watch_status or "").startswith("\uc218\ub77d")):
        cells.append({"s": "unk", "t": "\ud655\uc778 \ud544\uc694(\uce74\ub4dc \ubbf8\uc218\ub77d/\ub4f1\ub85d\ubd80 \uc5c6\uc74c)"})
    else:
        cells.append({"s": "ok" if evidence["basis_met"] else "no",
                      "t": ("\ud1b5\uacfc " if evidence["basis_met"] else "\ub9c9\ud798 ") + evidence["composition"]})
    cells.append({"s": m6["s"], "t": m6["t"]})
    # (5) R-REC1: an open event needs RG1-RG4; missing data blocks.
    if shock.get("status") == "unk":
        cells.append({"s": "unk", "t": "\ud655\uc778 \ud544\uc694(\ub9c9\ud798) " + ",".join(shock.get("reasons") or [])})
    elif shock.get("open"):
        missing = [key for key, value in (shock.get("rg") or {}).items() if value != "ok"]
        cells.append({"s": "ok" if not missing else "unk" if "unk" in (shock.get("rg") or {}).values() else "no",
                      "t": "\ud1b5\uacfc RG1~RG4" if not missing else "\ub9c9\ud798 \ubbf8\ucda9\uc871 " + ",".join(missing)})
    else:
        cells.append({"s": "ok", "t": "\ud1b5\uacfc (\uc5f4\ub9b0 \uc774\ubca4\ud2b8 \uc5c6\uc74c)"})
    cells.append({"s": "wait", "t": "\uc0ac\uc6a9\uc790 \uc8fc\ubb38 \uc785\ub825"})
    return {"code": symbol, "add": held, "c": cells}


# ---------------------------------------------------------------------------------------------
# Scenarios, regret table (design 5), price (design 7-2)
# ---------------------------------------------------------------------------------------------

def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def scenarios(closes: list[float]) -> dict[str, Any]:
    """Up/down = 90th/10th percentile of the last 60 five-session returns; worst = worst 1-day of 60."""
    count, horizon = S["SCENARIO_RETURNS"], S["SCENARIO_HORIZON"]
    if len(closes) < count + horizon:
        return {"status": "unk", "reason": "SCENARIO_HISTORY_SHORT"}
    window = closes[-(count + horizon):]
    returns = [window[index] / window[index - horizon] - 1 for index in range(horizon, len(window))]
    daily = [closes[index] / closes[index - 1] - 1 for index in range(len(closes) - S["TAIL_SESSIONS"], len(closes))]
    return {"status": "ok", "up": quantile(returns, S["UP_QUANTILE"]), "down": quantile(returns, S["DOWN_QUANTILE"]),
            "worst_day": min(daily), "returns_used": len(returns)}


def step_quantity(delta: int, step: Fraction) -> int:
    return delta if step == 1 else math.floor(delta * step)


def regret_table(*, side: str, delta: int, reference: Decimal, up: float, down: float, equity: Decimal,
                 candidate: dict[str, Any] | None = None, worst_day: float | None = None,
                 sigma: float | None = None) -> dict[str, Any]:
    """Rows for every step 0, 1/3, 1/2, 1: regret = best step's P&L in that scenario - this step's P&L.

    Sell: selling q avoids q x reference x return; with a redeployment candidate the proceeds earn the
    candidate's return in the same scenario (design 5 bridge: hold / sell -> cash / sell -> candidate). Buy:
    buying q earns q x reference x return. The tail row (worst 1-day) and LOC non-fill are display rows.
    """
    ref = float(reference)
    columns = [("up", "cash", up, 0.0), ("down", "cash", down, 0.0)]
    if side == "sell" and candidate is not None:
        columns += [("up", candidate["symbol"], up, candidate["up"]), ("down", candidate["symbol"], down,
                                                                         candidate["down"])]

    def pnl(quantity: int, own: float, other: float) -> float:
        return quantity * ref * (other - own) if side == "sell" else quantity * ref * own

    steps = S["STEPS"]
    quantities = {step: step_quantity(delta, step) for step in steps}
    rows = []
    for step in steps:
        regrets = {}
        for scenario, path, own, other in columns:
            best = max(pnl(quantities[item], own, other) for item in steps)
            regrets[f"{scenario}:{path}"] = round(best - pnl(quantities[step], own, other), 2)
        worst = max(regrets.values())
        rows.append({"r": fraction_text(step), "qty": quantities[step], "regret": regrets,
                     "max_regret": round(worst, 2), "max_regret_pct": round(worst / float(equity), 4)})
    tail_rows = []
    if worst_day is not None:
        for step in steps:
            quantity = quantities[step]
            if side == "sell":
                fills = sigma is not None and (1 + worst_day) >= (1 - float(S["SELL_FLOOR_SIGMA"]) * sigma)
                effective = quantity if fills else 0
                regret = (delta - effective) * ref * abs(min(worst_day, 0.0))
            else:
                fills = True
                regret = quantity * ref * abs(min(worst_day, 0.0))
            tail_rows.append({"r": fraction_text(step), "qty": quantity, "scenario": "worst_1d",
                              "return": round(worst_day, 4), "loc_fills": fills, "regret": round(regret, 2)})
    return {"rows": rows, "tail_rows": tail_rows, "columns": [f"{s}:{p}" for s, p, _o, _x in columns],
            "budget": round(float(equity * S["REGRET_BUDGET"]), 2)}


def choose_step(table: dict[str, Any], r_max: Fraction) -> tuple[Fraction, str]:
    """r_max when its worst regret is within the budget; else the step <= r_max with the smallest worst
    regret (ties -> the smaller step). Never above r_max."""
    rows = {Fraction(row["r"]): row for row in table["rows"]}
    if r_max <= 0:
        return Fraction(0), "R_MAX_ZERO"
    if rows[r_max]["max_regret"] <= table["budget"]:
        return r_max, "WITHIN_REGRET_BUDGET"
    allowed = sorted((step for step in rows if step <= r_max), key=lambda step: (rows[step]["max_regret"], step))
    return allowed[0], "MINIMAX_REGRET"


def loc_price(side: str, reference: Decimal, sigma: float) -> dict[str, Any]:
    """LOC price (design 7-2): buy cap = ref x (1 + 0.5 sigma) cent down; sell floor = ref x (1 - sigma) cent up.
    The multiplier is rounded to 4 decimals in the same direction, and the price is ref x multiplier, so the
    dashboard conversion (Kiwoom reference close x mult) gives the same price at the reference."""
    sigma_d = Decimal(str(sigma))
    if side == "buy":
        mult = (1 + S["BUY_CAP_SIGMA"] * sigma_d).quantize(S["MULT_PLACES"], rounding=ROUND_FLOOR)
        price = (reference * mult).quantize(CENT, rounding=ROUND_FLOOR)
        direction, rule = "down", "\uae30\uc900\uac00 \u00d7 (1 + 0.5\u03c360) \uc13c\ud2b8 \ub0b4\ub9bc"
    else:
        mult = (1 - S["SELL_FLOOR_SIGMA"] * sigma_d).quantize(S["MULT_PLACES"], rounding=ROUND_CEILING)
        price = (reference * mult).quantize(CENT, rounding=ROUND_CEILING)
        direction, rule = "up", "\uae30\uc900\uac00 \u00d7 (1 \u2212 \u03c360) \uc13c\ud2b8 \uc62c\ub9bc"
    low = (reference * (1 - S["PRICE_RANGE"])).quantize(CENT)
    high = (reference * (1 + S["PRICE_RANGE"])).quantize(CENT)
    return {"price": price, "rule": rule, "calc": {"mult": float(mult), "round": direction, "lo": float(low),
                                                   "hi": float(high), "label": "\ud0a4\uc6c0 \uae30\uc900\uc885\uac00 \u00d7 mult"}}


def decision_key(symbol: str, side: str, evidence_ids: list[str], section_hash: str | None, gap_source: str) -> str:
    text = "|".join([symbol, side, ",".join(sorted(evidence_ids)), section_hash or "", gap_source])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------
# 1R (display and record only; user decision ext-1012-setup B, 2026-10-12)
# ---------------------------------------------------------------------------------------------

R1_BASIS = "EMA20-0.75xATR14@evaluation_session"
R1_PLACES = Decimal("0.000001")
R1_UNK_LINE = "1R \ud655\uc778 \ud544\uc694(\uc9c0\ud45c \uc5c6\uc74c)"


def _r1_number(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except Exception:  # noqa: BLE001 - an unreadable input counts as missing
        return None
    return number if number.is_finite() else None


def risk_1r(reference: Any, ema20: Any, atr14: Any, sigma: Any, qty: Any, equity: Any) -> dict[str, Any]:
    """1R of a buy ticket: the invalidation line EMA20 - 0.75 ATR14 of the evaluation session (cent down) and
    the loss down to it per share (r_pct of the reference, r_sigma = r_pct / sigma60) and for the ticket's
    quantity (loss_usd, loss_pct_equity). Grade D, display and record only: nothing here feeds a gate, a
    quantity, a price or a sell. A missing or invalid input gives status unk (never an exception); a reference
    at or below the line gives below_band."""
    out: dict[str, Any] = {"status": "unk", "reason": None, "invalidation": None, "r_pct": None, "r_sigma": None,
                           "loss_usd": None, "loss_pct_equity": None, "basis": R1_BASIS, "grade": "D",
                           "display_only": True, "line": R1_UNK_LINE}
    values = [_r1_number(item) for item in (reference, ema20, atr14, sigma, qty, equity)]
    if any(item is None for item in values):
        return {**out, "reason": "INDICATOR_MISSING"}
    ref, ema, atr, sig, count, total = values
    if ref <= 0 or atr < 0 or sig <= 0 or count < 1 or total <= 0:
        return {**out, "reason": "INDICATOR_INVALID"}
    invalidation = (ema - S["R1_ATR_MULT"] * atr).quantize(CENT, rounding=ROUND_FLOOR)
    per_share = ref - invalidation
    if per_share <= 0:
        return {**out, "status": "below_band", "invalidation": format(invalidation, "f"),
                "line": "1R(\ud45c\uc2dc\ub9cc) \uae30\uc900\uac00\uac00 \ubb34\ud6a8\uc120 "
                        f"${invalidation} \uc544\ub798 \u2014 \uc14b\uc5c5 \uc5c6\uc74c"}
    r_pct = (per_share / ref).quantize(R1_PLACES, rounding=ROUND_HALF_UP)
    r_sigma = (r_pct / sig).quantize(CENT, rounding=ROUND_HALF_UP)
    loss = (count * per_share).quantize(CENT, rounding=ROUND_HALF_UP)
    share = (loss / total).quantize(R1_PLACES, rounding=ROUND_HALF_UP)
    # The line is written from the recorded values, so the screen and the record agree.
    line = ("1R(\ud45c\uc2dc\ub9cc) \ubb34\ud6a8\uc120 "
            f"${invalidation} \u00b7 \uae30\uc900\uac00 \ub300\ube44 "
            f"-{(r_pct * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}% "
            f"({r_sigma.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}\u03c3) \u00b7 \uc57d "
            f"${loss.quantize(Decimal('1'), rounding=ROUND_HALF_UP)} = \uc790\uc0b0 "
            f"{(share * 100).quantize(CENT, rounding=ROUND_HALF_UP)}% \u00b7 \uc790\ub3d9 \ub9e4\ub3c4 \uc5c6\uc74c")
    return {**out, "status": "ok", "invalidation": format(invalidation, "f"), "r_pct": format(r_pct, "f"),
            "r_sigma": format(r_sigma, "f"), "loss_usd": format(loss, "f"), "loss_pct_equity": format(share, "f"),
            "line": line}


def risk_1r_share_text(item: dict[str, Any] | None) -> str | None:
    """'W' of the line (loss as % of equity, 2 decimals) for the alert line; None unless status ok."""
    if not item or item.get("status") != "ok" or item.get("loss_pct_equity") is None:
        return None
    return format((Decimal(item["loss_pct_equity"]) * 100).quantize(CENT, rounding=ROUND_HALF_UP), "f")


# ---------------------------------------------------------------------------------------------
# Re-issue ledger (design 7-3, R-NE1 as decided in prompt D8)
# ---------------------------------------------------------------------------------------------

def update_keys(keys: dict[str, dict[str, Any]], outcomes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """New ledger after today's classified apply-mode outcomes. Filled or partly filled ends the key; an
    unfilled market test counts (2 = closed); not entered does not count, but 2 in a row closes the key."""
    ledger = {key: dict(value) for key, value in keys.items()}
    for outcome in outcomes:
        if outcome.get("mode") != "apply" or outcome.get("decision_key") is None:
            continue
        item = ledger.setdefault(outcome["decision_key"], {"first_cap": outcome.get("price"), "market_tests": 0,
                                                            "consecutive_not_entered": 0, "closed": False,
                                                            "closed_reason": None})
        state, filled = outcome["state"], int(outcome.get("filled_qty") or 0)
        if state in ("filled", "partial") or (state == "changed" and filled > 0):
            item.update(closed=True, closed_reason="FILLED")
        elif state in ("unfilled", "changed"):
            item["market_tests"] += 1
            item["consecutive_not_entered"] = 0
            if item["market_tests"] >= 2:
                item.update(closed=True, closed_reason="UNFILLED_TWICE")
        elif state == "not_entered":
            item["consecutive_not_entered"] += 1
            if item["consecutive_not_entered"] >= 2:
                item.update(closed=True, closed_reason="NOT_ENTERED_TWICE")
        item["last_ticket_id"] = outcome.get("ticket_id")
    return ledger


# ---------------------------------------------------------------------------------------------
# F6 outcome classification
# ---------------------------------------------------------------------------------------------

def _quantity(value: Any) -> int | None:
    try:
        number = Decimal(str(value).strip())
    except Exception:  # noqa: BLE001 - any unreadable cell is unknown
        return None
    return int(number) if number == number.to_integral_value() and number >= 0 else None


def _price(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value).strip())
    except Exception:  # noqa: BLE001
        return None
    return number if number.is_finite() and number >= 0 else None


def ticket_session_ended(ticket: dict[str, Any], evaluation_session: str) -> bool:
    """r3 R3-1: a ticket is classified only after its session has ended (ticket session <= the evaluation session
    of the run). Until then it stays open: no classification, no ledger change, no journal entry."""
    return ticket["session"] <= evaluation_session


def order_days(ticket: dict[str, Any], calendar: dict[str, Any]) -> list[str] | None:
    """r3 R3-2: the KST order days (ust21150 ord_dt) that can hold the ticket's order: from its issue KST day to the
    KST day of its session's regular close (the operating calendar's core_close_at: 05:00 KST in summer, 06:00 in
    winter, earlier on an early close). A weekday ticket gives its issue day and the next day; a Saturday ticket
    for Monday gives Saturday to Tuesday. None = the window is unknown (fail closed): the session is not in the
    calendar, or it closes before the issue day."""
    row = (calendar.get("sessions") or {}).get(ticket["session"])
    if row is None:
        return None
    first = date.fromisoformat(ticket["issued_day"])
    last = datetime.fromisoformat(row["core_close_at"]).astimezone(KST).date()
    if last < first:
        return None
    return [(first + timedelta(days=offset)).isoformat() for offset in range((last - first).days + 1)]


def issue_time(ticket: dict[str, Any]) -> time | None:
    """r4 R4-1: the KST time of day of the ticket's issuedAt ("YYYY-MM-DD HH:MM KST"); None = unreadable."""
    match = ISSUED_AT.fullmatch(str(ticket.get("issuedAt") or "").strip())
    return time(int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)) if match else None


def ticket_rows(ticket: dict[str, Any], dated_rows: list[tuple[str, dict[str, Any]]],
                attributed: set[tuple[str, str]]) -> dict[str, Any]:
    """r4 R4-1: the order rows that can be the ticket's, from (KST order day, ust21150 row) pairs of its order
    days: its ticker and side, an (ord_dt, ord_no) not attributed to a ticket already, and on its issue KST day
    only ord_time >= the issue time (an order placed before the ticket was issued is not for it). orders = the
    (ord_dt, ord_no) of the rows kept. A candidate row without an order number, or an issue-day row whose order
    time (or the ticket's issue time) cannot be read, makes the outcome unknown (note set, fail closed).
    t1-safety (judge2 G 2, T1's FILL_ROW_DUPLICATE_CONFLICT rule): an (ord_dt, ord_no) that comes twice as the
    very same row counts once; a candidate row whose (ord_dt, ord_no) also comes as a different row makes the
    outcome unknown (ORD_NO_DUPLICATE_CONFLICT)."""
    side_name = SIDE_NAMES[ticket["side"]]
    start = issue_time(ticket)
    rows: list[dict[str, Any]] = []
    orders: list[dict[str, str]] = []
    by_order: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for day, row in dated_rows:
        by_order.setdefault((day, str(row.get("ord_no") or "").strip()), []).append(row)
    used: set[tuple[str, str]] = set()
    for day, row in dated_rows:
        if str(row.get("stk_cd") or "").strip().upper() != ticket["ticker"] \
                or str(row.get("slby_tp_nm") or "").strip() != side_name:
            continue
        number = str(row.get("ord_no") or "").strip()
        if not number:
            return {"rows": [], "orders": [], "note": "ORD_NO_UNREADABLE"}
        if any(other != row for other in by_order[(day, number)]):
            return {"rows": [], "orders": [], "note": "ORD_NO_DUPLICATE_CONFLICT"}
        if (day, number) in used:  # the very same row again: counted once
            continue
        used.add((day, number))
        if (day, number) in attributed:
            continue
        if day == ticket["issued_day"]:
            if start is None:
                return {"rows": [], "orders": [], "note": "ISSUED_AT_UNREADABLE"}
            placed = order_clock(row.get("ord_time"))
            if placed is None:
                return {"rows": [], "orders": [], "note": "ORD_TIME_UNREADABLE"}
            if placed < start:
                continue
        rows.append(row)
        orders.append({"ord_dt": day, "ord_no": number})
    return {"rows": rows, "orders": orders, "note": None}


def attribute_orders(ledger: list[dict[str, Any]], new: list[dict[str, Any]], run_day: str) -> list[dict[str, Any]]:
    """r4 R4-1: the attributed-order ledger after a recording-mode classification: the carried entries, then
    today's, each (ord_dt, ord_no) once, only order days of the last ATTRIBUTION_DAYS calendar days (run day
    included)."""
    first = (date.fromisoformat(run_day) - timedelta(days=ATTRIBUTION_DAYS - 1)).isoformat()
    kept, seen = [], set()
    for entry in list(ledger) + list(new):
        pair = (entry["ord_dt"], entry["ord_no"])
        if entry["ord_dt"] < first or pair in seen:
            continue
        seen.add(pair)
        kept.append(dict(entry))
    return kept


def classify_outcome(ticket: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """not_entered | filled | partial | unfilled | changed from the broker's order rows of that symbol and side.

    rows are ust21150 rows (query_tp 1: orders with or without fills) of the ticket's order days (order_days),
    as chosen by ticket_rows (r4 R4-1). Filled quantities and the average fill price come from cntr_qty and cntr_uv only.
    """
    side_name = SIDE_NAMES[ticket["side"]]
    mine = [row for row in rows if str(row.get("stk_cd") or "").strip().upper() == ticket["ticker"]
            and str(row.get("slby_tp_nm") or "").strip() == side_name]
    base = {"ticket_id": ticket["ticket_id"], "ticker": ticket["ticker"], "side": ticket["side"],
            "decision_key": ticket.get("decision_key"), "mode": ticket.get("mode"), "price": ticket.get("price"),
            "qty": ticket["qty"], "rows": len(mine), "filled_qty": 0, "average_fill_price": None, "note": None}
    if not mine:
        return {**base, "state": "not_entered"}
    ordered, filled, cancelled, amount = 0, 0, 0, Decimal(0)
    as_ticket = True
    low, high = Decimal(str(ticket["priceCalc"]["lo"])), Decimal(str(ticket["priceCalc"]["hi"]))
    mult = Decimal(str(ticket["priceCalc"]["mult"]))
    for row in mine:
        qty, done, cancel = _quantity(row.get("ord_qty")), _quantity(row.get("cntr_qty")), _quantity(row.get("cncl_qty"))
        order_price, fill_price = _price(row.get("ord_uv")), _price(row.get("cntr_uv"))
        if qty is None or done is None or cancel is None or order_price is None:
            return {**base, "state": "unknown", "note": "ROW_UNREADABLE"}
        ordered += qty
        filled += done
        cancelled += cancel
        if done:
            if fill_price is None or fill_price <= 0:
                return {**base, "state": "unknown", "note": "FILL_PRICE_UNREADABLE"}
            amount += fill_price * done
        if str(row.get("frgn_trde_tp") or "").strip() != LOC_TYPE:
            as_ticket = False
        if not (low * mult).quantize(CENT, rounding=ROUND_FLOOR) <= order_price <= \
                (high * mult).quantize(CENT, rounding=ROUND_CEILING):
            as_ticket = False
    if ordered != ticket["qty"] or cancelled:
        as_ticket = False
    average = float((amount / filled).quantize(Decimal("0.0001"))) if filled else None
    result = {**base, "filled_qty": filled, "average_fill_price": average}
    if not as_ticket:
        return {**result, "state": "changed", "note": "QTY_TYPE_PRICE_OR_CANCEL_DIFFERS"}
    if filled == ticket["qty"]:
        return {**result, "state": "filled"}
    if filled > 0:
        return {**result, "state": "partial"}
    return {**result, "state": "unfilled"}


def reconcile_mismatch(outcome: dict[str, Any], session: str, reconcile_fills: list[dict[str, Any]] | None) -> bool:
    """True when the T1 reconciliation's explained fills (I2) of that ticker, side and session disagree."""
    if reconcile_fills is None:
        return False
    side = "SELL" if outcome["side"] == "sell" else "BUY"
    counted = sum(int(item.get("quantity") or 0) for item in reconcile_fills
                  if item.get("ticker") == outcome["ticker"] and item.get("side") == side
                  and item.get("session_date") == session)
    return counted != int(outcome.get("filled_qty") or 0)


# ---------------------------------------------------------------------------------------------
# The plan: circuit (D5), gates, tickets
# ---------------------------------------------------------------------------------------------

def proposal_targets(symbol: str, multipliers: dict[str, Any], cap: float, projected_lte: float,
                     cap_exempt: list[str]) -> list[Decimal]:
    """The 0.001 grid a buy target is searched on: up to the single-stock cap (0.4 / multiplier) or, for a
    cap-exempt ETF, to the nominal bound projected_lte / multiplier (N alone would exceed the target)."""
    multiplier = Decimal(str(multipliers[symbol])) if symbol in multipliers else None
    if multiplier is None or multiplier <= 0:
        return [WEIGHT_STEP]
    bound = Decimal(str(projected_lte)) / multiplier if symbol in cap_exempt else Decimal(str(cap)) / multiplier
    bound = min(floor_to_step(bound), Decimal(1))
    count = int(bound / WEIGHT_STEP)
    return [WEIGHT_STEP * index for index in range(1, count + 1)]


def best_target(symbol: str, evaluations: list[dict[str, Any]]) -> tuple[Decimal | None, list[str]]:
    """Largest grid weight whose S7 proposal evaluation passed with no reason (status DISPLAY)."""
    mine = [item for item in evaluations if item["symbol"] == symbol]
    passing = [Decimal(str(item["target_weight"])) for item in mine if item["status"] == "DISPLAY"]
    if passing:
        return max(passing), []
    # The reason shown is that of the smallest target above the current weight (targets at or below it only
    # say PROPOSAL_NOT_AN_INCREASE).
    increases = [item for item in mine if item.get("reasons") != ["PROPOSAL_NOT_AN_INCREASE"]] or mine
    first = min(increases, key=lambda item: Decimal(str(item["target_weight"])), default=None)
    return None, list((first or {}).get("reasons") or ["S7_NO_PROPOSAL"])


def plan(ctx: dict[str, Any]) -> dict[str, Any]:
    """Circuit, gates and tickets for one evaluation session (decide and replay share this path)."""
    symbols, checks = ctx["symbols"], ctx["checks"]
    review, s7 = ctx["review"], ctx["s7"]
    holdings, equity = ctx["holdings"], ctx["equity"]
    weights, closes, sigmas = ctx["weights"], ctx["closes"], ctx["sigmas"]
    config = ctx["config"]
    blocked: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    tickets: list[dict[str, Any]] = []
    global_reasons = list(ctx["gate0"]["reasons"]) + list(ctx["gate1"]["reasons"])
    reduce_items = {item["symbol"]: item for item in (review or {}).get("recommendations", {}).get("reduce") or []}
    add_symbols = {item["symbol"] for item in (review or {}).get("recommendations", {}).get("add") or []}

    # t2rc-corefix 4: the redeployment candidate is the first ranked one whose sell circuit is not open today
    # (a symbol sold today is one of them), so a sold first-ranked symbol gives way to the next.
    if ctx.get("redeploy_ranked") is not None:
        selling = {symbol for symbol in holdings if _sell_gap_sources(checks, symbol, reduce_items)[0]
                   and ctx["evidence"][symbol]["sell"]["basis_met"]}
        ctx["redeploy_candidate"] = next((dict(item) for item in ctx["redeploy_ranked"]
                                          if item["symbol"] not in selling), None)

    # Sells (circuit D5): a held symbol with an S7 reduce item or a card EXIT/TRIM target and sell evidence.
    for symbol in sorted(holdings):
        check = checks.get(symbol) or {}
        evidence = ctx["evidence"][symbol]["sell"]
        gap_sources, trim_missing = _sell_gap_sources(checks, symbol, reduce_items)
        if trim_missing:
            blocked.append({"symbol": symbol, "side": "sell", "reasons": ["CARD_TRIM_SIZE_MISSING"]})
        if not gap_sources or not evidence["basis_met"]:
            continue
        source, target = min(gap_sources, key=lambda item: item[1])
        candidates.append({"symbol": symbol, "side": "sell", "gap_source": source, "target_weight": float(target)})
        reasons = list(global_reasons) + list(check.get("reasons") or []) + ctx["data_reasons"].get(symbol, [])
        ticket = _sell_ticket(ctx, symbol, source, target, evidence, check, reasons, blocked)
        if ticket:
            tickets.append(ticket)

    # Buys (circuit D5): evidence that appeared today alone meets the basis, or an S7 add + requirement (3).
    for row in ctx["buy_rows"]:
        symbol = row["code"]
        evidence = ctx["evidence"][symbol]["buy"]
        opened = evidence["new_basis_met"] or (symbol in add_symbols and evidence["basis_met"])
        if not opened:
            continue
        candidates.append({"symbol": symbol, "side": "buy", "trigger": "NEW_EVIDENCE" if evidence["new_basis_met"]
                           else "S7_ADD_RECOMMENDATION"})
        # r2 R2-1: without an OK research record of the day every buy (index ETFs included) is blocked.
        research = [f"RESEARCH_RECORD_NOT_OK:{ctx['research_block']}"] if ctx["research_block"] is not None else []
        reasons = list(global_reasons) + research + list((checks.get(symbol) or {}).get("reasons") or []) + \
            ctx["data_reasons"].get(symbol, [])
        ticket = _buy_ticket(ctx, symbol, row, evidence, reasons, blocked)
        if ticket:
            tickets.append(ticket)

    tickets = _limit_daily(tickets, config, blocked)
    reduce_plan = list((review or {}).get("recommendations", {}).get("reduce") or [])
    sells = [ticket for ticket in tickets if ticket["side"] == "sell"]
    for ticket in sells:
        line = plan_premise(ticket, reduce_plan, sells, blocked, candidates)
        ticket["gap"]["plan_premise"] = line
        ticket["after_sale"]["plan_premise"] = line
    for index, ticket in enumerate(sorted(tickets, key=lambda item: (item["side"] != "sell", item["ticker"]))):
        ticket["ticket_id"] = f"AT-{ctx['run_day'].replace('-', '')}-{ticket['ticker']}-{index + 1}"
    no_action = not tickets
    top = []
    for item in blocked:
        for reason in item["reasons"]:
            if reason not in top:
                top.append(reason)
    if not candidates:
        top = ["NO_CIRCUIT_OPEN"]
    return {"candidates": candidates, "tickets": tickets, "blocked": blocked,
            "no_action": {"value": no_action, "reasons": top[:5] if no_action else []}}


def _sell_gap_sources(checks: dict[str, Any], symbol: str, reduce_items: dict[str, Any]
                      ) -> tuple[list[tuple[str, Decimal]], bool]:
    """The sell gap sources of a held symbol (S7 reduce item, card EXIT or TRIM target) and whether a TRIM card
    lacks its size. Pure: plan() records the missing TRIM size itself."""
    entry = (checks.get(symbol) or {}).get("entry") or {}
    gap_sources: list[tuple[str, Decimal]] = []
    trim_missing = False
    if symbol in reduce_items and reduce_items[symbol].get("target_weight") is not None:
        gap_sources.append(("S7_REDUCE_" + str(reduce_items[symbol]["order"]),
                            Decimal(str(reduce_items[symbol]["target_weight"]))))
    if entry.get("card_action") == "EXIT":
        gap_sources.append(("CARD_EXIT", Decimal(0)))
    elif entry.get("card_action") == "TRIM":
        if entry.get("trim_target_weight") is None:
            trim_missing = True
        else:
            gap_sources.append(("CARD_TRIM", Decimal(str(entry["trim_target_weight"]))))
    return gap_sources, trim_missing


def _sigma_and_ref(ctx: dict[str, Any], symbol: str) -> tuple[Decimal | None, float | None]:
    return ctx["closes"].get(symbol), ctx["sigmas"].get(symbol)


def reissue_block(ledger: dict[str, Any], config: dict[str, Any]) -> str | None:
    """Why a decision key may not get a ticket today (design 7-3, R-NE1 as in prompt D8 and section 7 Q2).

    A closed key never gets one. After a not-entered ticket the same decision is issued again only when the
    Q2 answer was a or b, which P-1 records by putting reissue_buy_cap_not_above_first in the configuration
    (true = a, false = b); without the key (Q2 c or no answer) that decision is not issued again (it lapses;
    a new key - new evidence or a card change - starts afresh). No user step either way.
    """
    if ledger.get("closed"):
        return "DECISION_KEY_CLOSED:" + str(ledger.get("closed_reason"))
    if ledger.get("consecutive_not_entered") and "reissue_buy_cap_not_above_first" not in config:
        return "NOT_ENTERED_NO_REISSUE"
    return None


def enter_window(issue_day: str, session_row: dict[str, Any]) -> str:
    """r4 R4-2: when to enter the ticket in Kiwoom: from 17:00 KST of the issue day to the session's open (the
    operating calendar's core_open_at in KST: 22:30 in summer, 23:30 in winter). The open's KST date is written
    when it is not the issue day (a Saturday ticket for Monday, a ticket across a holiday)."""
    issued = date.fromisoformat(issue_day)
    opens = datetime.fromisoformat(session_row["core_open_at"]).astimezone(KST)
    start = f"\ud55c\uad6d {issued.month}/{issued.day} 17:00 \uc774\ud6c4 ~ "
    if opens.date() == issued:
        return start + f"\uc815\uaddc\uc7a5 \uac1c\uc7a5 \uc804({opens:%H:%M})"
    return start + f"{opens.month}/{opens.day} {opens:%H:%M} \uac1c\uc7a5 \uc804"


def _common_ticket(ctx: dict[str, Any], *, symbol: str, side: str, qty: int, price_info: dict[str, Any],
                   reference: Decimal, evidence: dict[str, Any], gates: dict[str, Any], regret: dict[str, Any],
                   key: str, reason: str, r_text: str) -> dict[str, Any]:
    price = price_info["price"]
    amount = (price * qty).quantize(CENT)
    fee = (amount * S["MEASURED_FEE_RATE"]).quantize(CENT)
    session_row = ctx["calendar"]["sessions"][ctx["buy_session"]]
    closes = datetime.fromisoformat(session_row["core_close_at"]).astimezone(KST)
    return {
        "ticket_id": None, "mode": ctx["mode"], "issuedAt": ctx["issued_at"], "session": ctx["buy_session"],
        "enterWindow": enter_window(ctx["run_day"], session_row),
        "fillAt": f"{closes.month}/{closes.day} {closes:%H:%M} (\ud55c\uad6d) \uc815\uaddc\uc7a5 \uc885\uac00",
        "ref": {"price": float(reference), "label": f"{ctx['evaluation_session']} \uadfc\uc0ac \uc885\uac00"},
        "ifUnfilled": "\uc7ac\uc8fc\ubb38\ud558\uc9c0 \uc54a\uc74c \u2014 \ub2e4\uc74c \uc544\uce68 \uacb0\uacfc \ubd84\ub958, \uac19\uc740 \uacb0\uc815 \uc7ac\ubc1c\ud589 1\ud68c(\ubbf8\uc785\ub825\uc740 \ud69f\uc218 \uc81c\uc678)",
        "ticker": symbol, "side": side, "type": "LOC", "price": float(price), "priceRule": price_info["rule"],
        "priceCalc": price_info["calc"], "qty": qty, "amount": float(amount), "feeRate": float(S["TICKET_FEE_RATE"]),
        "check_line": f"{qty}\uc8fc \u00d7 ${price} = \uc57d ${amount} (\uc2e4\uce21 \uc218\uc218\ub8cc 0.0699% \uc57d ${fee})",
        "reason": reason,
        "evidence": {"strong": evidence["strong"], "weak": evidence["weak_kinds"],
                     "composition": evidence["composition"], "r_max": evidence["r_max"], "r": r_text},
        "gates": gates, "regret": regret, "decision_key": key, "inputs": dict(ctx["input_hashes"]),
        "authority": dict(AUTHORITY),
    }


def _sell_ticket(ctx: dict[str, Any], symbol: str, source: str, target: Decimal, evidence: dict[str, Any],
                 check: dict[str, Any], reasons: list[str], blocked: list[dict[str, Any]]) -> dict[str, Any] | None:
    reference, sigma = _sigma_and_ref(ctx, symbol)
    gates = {"G0": ctx["gate0"]["ok"], "G1": ctx["gate1"]["ok"], "G2": True, "G2b": "n/a", "G3": evidence["r_max"],
             "G4": "n/a", "G5": "not_applicable_sell"}
    if reasons:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": reasons})
        return None
    if reference is None or sigma is None or ctx["equity"] is None:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": ["G1_PRICE_OR_SIGMA_MISSING"]})
        return None
    held = ctx["holdings"][symbol]
    delta = held - int(math.floor(target * ctx["equity"] / reference))
    r_max = Fraction(evidence["r_max"])
    if delta < 1:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": ["LOT_ZERO"]})
        return None
    scenario = ctx["scenarios"].get(symbol) or {"status": "unk"}
    if scenario["status"] != "ok":
        blocked.append({"symbol": symbol, "side": "sell", "reasons": ["SCENARIO_UNAVAILABLE"]})
        return None
    candidate = ctx.get("redeploy_candidate")
    table = regret_table(side="sell", delta=delta, reference=reference, up=scenario["up"], down=scenario["down"],
                         equity=ctx["equity"], candidate=candidate if candidate and candidate["symbol"] != symbol else None,
                         worst_day=scenario["worst_day"], sigma=sigma)
    step, why = choose_step(table, r_max)
    if step == 0:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": ["REGRET_ZERO" if r_max > 0 else "G3_R_MAX_ZERO"]})
        return None
    qty = step_quantity(delta, step)
    if qty < 1:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": ["LOT_ZERO"]})
        return None
    if Decimal(qty) * reference < ctx["equity"] * S["DEADBAND"]:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": ["DEADBAND"]})
        return None
    key = decision_key(symbol, "sell", evidence["ids"], (check.get("entry") or {}).get("section_sha256"), source)
    ledger = ctx["keys"].get(key) or {}
    stop = reissue_block(ledger, ctx["config"])
    if stop:
        blocked.append({"symbol": symbol, "side": "sell", "reasons": [stop]})
        return None
    price_info = loc_price("sell", reference, sigma)
    ticket = _common_ticket(ctx, symbol=symbol, side="sell", qty=qty, price_info=price_info, reference=reference,
                            evidence=evidence, gates=gates, regret={**table, "chosen": fraction_text(step), "why": why},
                            key=key, reason=f"{source} \u00b7 \ub9e4\ub3c4 \uadfc\uac70 {evidence['composition']}",
                            r_text=fraction_text(step))
    ticket["gap"] = {"source": source, "target_weight": float(target), "delta": delta}
    ticket["after_sale"] = after_sale_path(ctx, symbol, qty, reference)
    return ticket


def _buy_ticket(ctx: dict[str, Any], symbol: str, row: dict[str, Any], evidence: dict[str, Any], reasons: list[str],
                blocked: list[dict[str, Any]]) -> dict[str, Any] | None:
    reasons = list(reasons)
    cells = row["c"]
    labels = ("REQ1_EARNINGS", "REQ2_EXPOSURE_CASH_PRODUCT", "REQ3_EVIDENCE", "REQ4_M6", "REQ5_RREC1")
    for label, cell in zip(labels, cells[:5]):
        if cell["s"] != "ok":
            reasons.append(f"{label}:{cell['s']}")
    if symbol not in ctx["policy_instruments"]:
        reasons.append("POLICY_UNREGISTERED_INSTRUMENT")
    target, s7_reasons = best_target(symbol, ctx["proposal_results"])
    if target is None:
        reasons += ["G2:" + reason for reason in s7_reasons[:3]]
    if reasons:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": reasons})
        return None
    reference, sigma = _sigma_and_ref(ctx, symbol)
    if reference is None or sigma is None or ctx["equity"] is None:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["G1_PRICE_OR_SIGMA_MISSING"]})
        return None
    held = symbol in ctx["holdings"]
    current = Decimal(str(ctx["weights"].get(symbol, 0)))
    goal = target if held else floor_to_step(target * S["FIRST_ENTRY"])
    delta = int(math.floor((goal - current) * ctx["equity"] / reference))
    r_max = Fraction(evidence["r_max"])
    if delta < 1:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["LOT_ZERO"]})
        return None
    scenario = ctx["scenarios"].get(symbol) or {"status": "unk"}
    if scenario["status"] != "ok":
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["SCENARIO_UNAVAILABLE"]})
        return None
    table = regret_table(side="buy", delta=delta, reference=reference, up=scenario["up"], down=scenario["down"],
                         equity=ctx["equity"], worst_day=scenario["worst_day"], sigma=sigma)
    step, why = choose_step(table, r_max)
    if step == 0:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["REGRET_ZERO" if r_max > 0 else "G3_R_MAX_ZERO"]})
        return None
    qty = step_quantity(delta, step)
    if qty < 1:  # r2 R2-12: zero shares after the step is a lot problem, not cash or the G2b cap
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["LOT_ZERO"]})
        return None
    entry = (ctx["checks"].get(symbol) or {}).get("entry") or {}
    key = decision_key(symbol, "buy", evidence["ids"], entry.get("section_sha256"), "S7_TARGET")
    ledger = ctx["keys"].get(key) or {}
    stop = reissue_block(ledger, ctx["config"])
    if stop:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": [stop]})
        return None
    price_info = loc_price("buy", reference, sigma)
    if ctx["config"].get("reissue_buy_cap_not_above_first") is True and ledger.get("consecutive_not_entered") and \
            ledger.get("first_cap") is not None and price_info["price"] > Decimal(str(ledger["first_cap"])):
        price_info["price"] = Decimal(str(ledger["first_cap"]))
        price_info["rule"] += " \u00b7 \uccab \uc0c1\ud55c \uc774\ud558(\ubbf8\uc785\ub825 \ub4a4 \uc7ac\ubc1c\ud589)"
    gates: dict[str, Any] = {"G0": True, "G1": True, "G2": float(target), "G2b": "n/a", "G3": evidence["r_max"],
                             "G4": None, "G5": row["c"][4]["s"]}
    pct = ctx["config"].get("max_buy_ticket_pct_of_equity")
    if pct is not None:
        limit = int(math.floor(ctx["equity"] * Decimal(str(pct)) / price_info["price"]))
        if qty > limit:
            qty = limit
            gates["G2b"] = f"size_capped:{limit}"
        if qty < 1:
            blocked.append({"symbol": symbol, "side": "buy", "reasons": ["G2B_CAP"]})
            return None
    cash = ctx["cash"]
    if cash is None:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["CASH_UNKNOWN"]})
        return None
    affordable = int(math.floor(cash / (price_info["price"] * (1 + S["CASH_BUFFER"]))))
    if qty > affordable:
        qty = affordable
        gates["G4"] = f"cash_capped:{affordable}"
    if qty < 1:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["CASH_ZERO"]})
        return None
    gates["G4"] = gates["G4"] or "ok"
    if Decimal(qty) * reference < ctx["equity"] * S["DEADBAND"]:
        blocked.append({"symbol": symbol, "side": "buy", "reasons": ["DEADBAND"]})
        return None
    ticket = _common_ticket(ctx, symbol=symbol, side="buy", qty=qty, price_info=price_info, reference=reference,
                            evidence=evidence, gates=gates, regret={**table, "chosen": fraction_text(step), "why": why},
                            key=key, reason=f"\ub9e4\uc218 \uadfc\uac70 {evidence['composition']} \u00b7 S7 \ubaa9\ud45c {target}",
                            r_text=fraction_text(step))
    ticket["gap"] = {"source": "S7_TARGET", "target_weight": float(goal), "whole_target": float(target),
                     "current_weight": float(current), "delta": delta, "first_entry": not held}
    # 1R after the ticket is complete: display and record only, it changes nothing above.
    ticket["risk_1r"] = _ticket_risk_1r(ctx, symbol, reference, sigma, qty)
    return ticket


def _ticket_risk_1r(ctx: dict[str, Any], symbol: str, reference: Decimal, sigma: float, qty: int) -> dict[str, Any]:
    marks = (ctx.get("indicators") or {}).get(symbol) or {}
    try:
        return risk_1r(reference, marks.get("ema20"), marks.get("atr14"), sigma, qty, ctx["equity"])
    except Exception:  # noqa: BLE001 - a 1R failure is shown as unk and never blocks the ticket
        return {**risk_1r(None, None, None, None, None, None), "reason": "CALC_FAILED"}


def _limit_daily(tickets: list[dict[str, Any]], config: dict[str, Any], blocked: list[dict[str, Any]]
                 ) -> list[dict[str, Any]]:
    """G2b count (only when max_tickets_per_day is set): sells first, then larger amounts first."""
    limit = config.get("max_tickets_per_day")
    if limit is None or len(tickets) <= int(limit):
        return tickets
    ordered = sorted(tickets, key=lambda item: (item["side"] != "sell", -item["amount"], item["ticker"]))
    kept, dropped = ordered[:int(limit)], ordered[int(limit):]
    for ticket in dropped:
        blocked.append({"symbol": ticket["ticker"], "side": ticket["side"], "reasons": ["G2B_CAP"]})
    return kept


# ---------------------------------------------------------------------------------------------
# After-sale path (design 7-4, display only)
# ---------------------------------------------------------------------------------------------

# S7 reduce order (portfolio_exposure.reduce_recommendations) -> label of the step.
REDUCE_STEP_LABELS = {1: "\uc0c1\ud55c \ucd08\uacfc\ubd84", 2: "\uce74\ub4dc TRIM/EXIT", 3: "\ubcf4\ucda9 ETF"}


def plan_premise(ticket: dict[str, Any], reduce_plan: list[dict[str, Any]], sells: list[dict[str, Any]],
                 blocked: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> str:
    """One display line for a sell ticket (r2 R2-6, Judge K1 23b): the earlier steps of the S7 reduce plan its
    gap assumes and whether today has a ticket for each, and the projected E when only this ticket fills. The
    quantity is not changed (design 7-1: a missing earlier step can only make it sell less than needed)."""
    after = ticket.get("after_sale") or {}
    alone = "\uc774 \uc8fc\ubb38\ud45c\ub9cc \uccb4\uacb0 \uc2dc \uc608\uc0c1 E " + str(after.get("e"))
    source = ticket["gap"]["source"]
    if not source.startswith("S7_REDUCE_"):
        return "\uce74\ub4dc \ubaa9\ud45c(" + source + ") \u2014 S7 \uacc4\ud68d \uc21c\uc11c \uc544\ub2d8 \u00b7 " + alone
    order = int(source.rsplit("_", 1)[1])
    parts = []
    for item in sorted(reduce_plan, key=lambda value: (value.get("order", 0), value.get("symbol") or "")):
        symbol = item.get("symbol")
        if item.get("order", 0) >= order or symbol == ticket["ticker"]:
            continue
        issued = next((other for other in sells if other["ticker"] == symbol), None)
        reasons = [reason for other in blocked if other["symbol"] == symbol and other["side"] == "sell"
                   for reason in other["reasons"]]
        if issued is not None:
            state = "\uc624\ub298 \uc8fc\ubb38\ud45c \uc788\uc74c(" + str(issued["qty"]) + "\uc8fc)"
        elif reasons:
            state = "\uc624\ub298 \uc8fc\ubb38\ud45c \uc5c6\uc74c(" + reasons[0] + ")"
        elif any(other["symbol"] == symbol and other["side"] == "sell" for other in candidates):
            state = "\uc624\ub298 \uc8fc\ubb38\ud45c \uc5c6\uc74c"
        else:
            state = "\uc624\ub298 \uc8fc\ubb38\ud45c \uc5c6\uc74c(\ub9e4\ub3c4 \uadfc\uac70 \uc5c6\uc74c)"
        label = REDUCE_STEP_LABELS.get(item.get("order"), str(item.get("basis")))
        parts.append("\uc55e \uc21c\uc11c " + f"{symbol} {label} \u2014 " + state)
    head = " \u00b7 ".join(parts) if parts else "\uc55e \uc21c\uc11c \uc5c6\uc74c"
    return "S7 \uacc4\ud68d \uc804\uc81c: " + head + " \u00b7 " + alone


def after_sale_path(ctx: dict[str, Any], symbol: str, qty: int, reference: Decimal) -> dict[str, Any]:
    """Projected E, N and cash after the sale, and the swap pair (design 7-1 5): the redeployment candidate's
    largest share count with projected E <= the target. Unfunded projection: never cash, never a buy ticket."""
    model_for: Callable[[list[str]], Any] | None = ctx.get("model_for")
    equity, weights = ctx["equity"], {key: Decimal(str(value)) for key, value in ctx["weights"].items()}
    after = dict(weights)
    after[symbol] = after.get(symbol, Decimal(0)) - Decimal(qty) * reference / equity
    cash_after = (ctx["cash"] or Decimal(0)) + Decimal(qty) * reference
    out: dict[str, Any] = {"display_only": True, "unfunded_projection": True, "cash_after": _money(cash_after),
                           "schedule": "D \ub9e4\ub3c4 LOC \u2192 D+1 \ub300\uc870 \u2192 \uc0c8 \uc0c1\ud0dc\ub85c \ub9e4\uc218 \uc7ac\uacc4\uc0b0 \u2192 D+1 \uc800\ub141 LOC"}
    if model_for is None:
        out["projection"] = "unavailable"
        return out
    model = model_for(sorted(after))
    nominal, volatility = model.parts(after)
    projected = effective_exposure(nominal, volatility)
    out.update(n=None if nominal is None else round(float(nominal), 4),
               v=None if volatility is None else round(volatility, 4),
               e=None if projected is None else round(projected, 4))
    target = POLICY_EXPECTED["target_exposure"]
    out["buy_requirement_2_opens"] = projected is not None and projected < POLICY_EXPECTED["reduce_when_exposure_gte"]
    candidate = ctx.get("redeploy_candidate")
    if candidate and candidate["symbol"] != symbol and ctx["closes"].get(candidate["symbol"]):
        price = ctx["closes"][candidate["symbol"]]
        joint = model_for(sorted(set(after) | {candidate["symbol"]}))
        best = 0
        if joint.volatility_available:
            for shares in range(1, int(cash_after / price) + 1):
                trial = dict(after)
                trial[candidate["symbol"]] = trial.get(candidate["symbol"], Decimal(0)) + Decimal(shares) * price / equity
                n_trial, v_trial = joint.parts(trial)
                e_trial = effective_exposure(n_trial, v_trial)
                if e_trial is None or e_trial > target:
                    break
                best = shares
        out["swap_pair"] = {"sell": f"{symbol} {qty}\uc8fc", "buy_next_day": f"{candidate['symbol']} {best}\uc8fc",
                            "projected_e_limit": target, "buy_is_ticket": False}
    else:
        out["swap_pair"] = None
    return out
