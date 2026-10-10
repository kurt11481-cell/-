#!/usr/bin/env python3
"""Redesign T1 F3/F4: automatic broker reconciliation under invariants I1-I5 (no human code).

One read-only Kiwoom read (holdings, cash, cash detail, open orders, fills, daily order fills, day trades,
transaction history) is judged against the last recorded state:

I1  every required read returned return_code 0 (a verified no-data declaration counts as zero rows)
I2  per ticker, the held-quantity change since the last record equals the broker fills (buy - sell)
I3  the order-available cash change since the snapshot of the last record (broker to broker) equals the
    actual settlement amounts of the fills since then (pending: cash-detail dN excta by settlement date;
    settled: transaction-history trade rows fc_exct_amt) plus the classified transaction-history rows
    (deposit, withdrawal, dividend, tax, fee, FX), within 1.00 USD
I4  the state hash and revision equal the last ledger entry and the ledger hash chain is intact
I5  no field other than holdings, cash and cost basis would change

Fills come only from broker fill records (ust21150 quantities; ust21610 binds them per session and ticker and
gives the gross amounts that bound the settlement amounts); nothing is inferred from prices. The ust21610 fee
column (cmsn_altx) is an estimate and is not used. Average cost is the broker's frgn_stk_book_uv and is not
part of the explanation.
The cash-flow evidence (F3) is built from the same transaction-history read and declared in full
automatically, so the HWM never needs a human declaration.

mode "compare" never writes: it records what would have been applied. mode "apply" writes through
apply_user_confirmed_broker_snapshot.apply_auto_core only when I1-I5, the cash-flow evidence and the
kill switch all allow it. Any doubt is a HOLD: the state stays unchanged and the next run retries.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from apply_user_confirmed_broker_snapshot import (
    AUTO_CORE_INVARIANTS, _assert_untouched, apply_auto_core, default_ledger_path, ledger_status,
    preview_updated_state,
)
from cash_flow_evidence import (
    CashFlowError, build_declaration, classify_row, load_classification, normalize_transaction_history,
    read_ledger_blocks,
)
from kiwoom_account_readonly_bridge import invoke_account_bridge_batch
from kiwoom_broker_shadow import NEVER_TOUCHED_FIELDS, normalize_snapshot, reconciliation_proposal
from validation_common import canonical_hash, file_hash, load_json, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
EVIDENCE_ROOT = REPO_ROOT / "workspace/private_inputs/cash_flow_evidence"
PROPOSAL_SCHEMA = SKILL_ROOT / "schemas/kiwoom-reconciliation-proposal.schema.json"
SNAPSHOT_SCHEMA = SKILL_ROOT / "schemas/kiwoom-broker-shadow.schema.json"
KST = ZoneInfo("Asia/Seoul")
ET = ZoneInfo("America/New_York")
SNAPSHOT_OPERATIONS = (
    "account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
    "account_open_items", "account_fills_read", "account_realized_pnl_read",
)
# I1: the reads whose return_code must be 0. Realized P&L is display only.
I1_SNAPSHOT_OPERATIONS = ("account_holdings_read", "account_deposit_read", "account_deposit_detail_read",
                          "account_open_items", "account_fills_read")
CASH_TOLERANCE_USD = Decimal("1.00")
# R2-1: a settlement amount may differ from the gross (quantity x price) by at most the fee range.
SETTLEMENT_FEE_RATE = Decimal("0.005")
SETTLEMENT_FEE_FIXED_USD = Decimal("0.50")
# Cash-detail (ust21160) settlement slots with amounts; D0 has a date but no amount fields.
SETTLEMENT_SLOTS = ("d1", "d2", "d3", "d4")
# T1 r3 C4: today's settlement (D0) before the broker's morning processing. Its amount is the previous run's
# read of that date's pending slot when there is one (a); otherwise the date is left open (b).
CARRIED_SOURCE = "PENDING_PREVIOUS_RUN"
D0_SOURCE = "D0_NOT_SHOWN"
D0_NOT_SHOWN = "SETTLEMENT_D0_NOT_SHOWN"
D0_ONLY = re.compile(r"(?:I3:)?" + D0_NOT_SHOWN + r":\d{4}-\d{2}-\d{2}")
SNAPSHOT_FILE = "kiwoom_broker_snapshot.shadow.json"
# R2-2: where a human-path ledger entry's proposal (and through it the recorded snapshot) is found.
BASELINE_SEARCH_ROOTS = (REPO_ROOT / "workspace/outputs/reconciliation", REPO_ROOT / "workspace/outputs/auto-core")
BASELINE_UNKNOWN = "BASELINE_ORDER_AVAILABLE_UNKNOWN"
FILL_WINDOW_MAXIMUM_DAYS = 14
# T1 r3 C4: in compare mode the record stays where it is; past this share of the window the user is told to
# switch recording on before the window limit stops the run.
STALE_WINDOW_SHARE = Decimal("0.8")
TRANSACTION_HISTORY_MAXIMUM_DAYS = 365
FILL_SIDES = {"\ub9e4\ub3c4": "SELL", "\ub9e4\uc218": "BUY"}  # Korean side names: sell, buy
FLOW_IN, FLOW_OUT = "\uc785\uae08", "\ucd9c\uae08"  # Korean memo words: money in, money out
EXTERNAL_CLASSES = ("DEPOSIT", "WITHDRAWAL", "FX")
SIGNED_BY_MEMO_CLASSES = ("DIVIDEND", "FEE_TAX_INTEREST", "CORPORATE_ACTION")
CLOCK = re.compile(r"([01]\d|2[0-3]):?([0-5]\d):?([0-5]\d)")
RESULT_SCHEMA_VERSION = "auto-core-reconcile-1.0"


class AutoReconcileError(ValueError):
    """A collection or input problem that ends the auto reconciliation (FAIL, nothing written)."""


# ---------------------------------------------------------------------------------------------
# Small parsers (fail closed: None means unreadable, never zero)
# ---------------------------------------------------------------------------------------------

def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _quantity(value: Any) -> int | None:
    number = _decimal(value)
    if number is None or number < 0 or number != number.to_integral_value():
        return None
    return int(number)


def _compact_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{8}", text):
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def _clock(value: Any) -> time | None:
    match = CLOCK.fullmatch(str(value or "").strip())
    return time(int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _ymd(value: date) -> str:
    return value.strftime("%Y%m%d")


# ---------------------------------------------------------------------------------------------
# Window and request planning
# ---------------------------------------------------------------------------------------------

def record_time(state: dict[str, Any]) -> datetime | None:
    """When the recorded holdings and cash were read (the last confirmed snapshot's earliest read)."""
    record = state.get("last_confirmed_broker_snapshot")
    return _parse_utc(record.get("as_of_timestamp")) if isinstance(record, dict) else None


def evidence_period_start(ledger_blocks: list[Any], activation_date: str | None) -> date | None:
    """Start of the next cash-flow evidence period.

    It is the last recorded evidence period_to (the day is covered again, so rows that Kiwoom
    processed later on that day are never skipped; rows already counted are deduplicated by key in
    build_declaration), or the S5 activation date when no evidence was recorded yet.
    """
    ends = []
    for block in ledger_blocks:
        try:
            ends.append(date.fromisoformat(block["evidence"]["period_to"]))
        except (KeyError, TypeError, ValueError):
            continue
    if ends:
        return max(ends)
    try:
        return date.fromisoformat(str(activation_date)) if activation_date else None
    except ValueError:
        return None


def plan_reads(*, recorded_at: datetime, evidence_from: date, now: datetime) -> dict[str, Any]:
    """Dates of the dated reads. Fills are read from the KST day before the last record through today."""
    today = now.astimezone(KST).date()
    record_day = recorded_at.astimezone(KST).date()
    fill_from = record_day - timedelta(days=1)
    history_from = min(evidence_from, record_day)
    return {"today": today, "fill_dates": [fill_from + timedelta(days=offset)
                                           for offset in range((today - fill_from).days + 1)],
            "history_from": history_from, "evidence_from": evidence_from}


def dated_requests(plan: dict[str, Any]) -> list[dict[str, Any]]:
    requests = [{"operation": "account_daily_fills_read", "params": {"ord_dt": _ymd(day)}}
                for day in plan["fill_dates"]]
    requests.append({"operation": "account_transaction_history_read",
                     "params": {"strt_dt": _ymd(plan["history_from"]), "end_dt": _ymd(plan["today"])}})
    return requests


# ---------------------------------------------------------------------------------------------
# I1 required reads
# ---------------------------------------------------------------------------------------------

def _read_passed(result: dict[str, Any]) -> bool:
    pagination = result.get("pagination")
    return (result.get("bridge_status") == "PASS"
            and (not isinstance(pagination, dict) or pagination.get("complete") is True))


def _failure_reason(result: dict[str, Any], label: str) -> str:
    code = result.get("provider_return_code")
    detail = f":{code}" if type(code) is int else ""
    return f"REQUIRED_READ_NOT_PASS:{label}:{result.get('bridge_status')}{detail}"


def invariant_i1(snapshot_results: list[dict[str, Any]], dated_results: list[dict[str, Any]],
                 expected_dated: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    for operation in I1_SNAPSHOT_OPERATIONS:
        matches = [item for item in snapshot_results if item.get("operation") == operation]
        if len(matches) != 1:
            reasons.append(f"REQUIRED_READ_MISSING:{operation}")
        elif not _read_passed(matches[0]):
            reasons.append(_failure_reason(matches[0], operation))
    for request in expected_dated:
        matches = [item for item in dated_results if item.get("operation") == request["operation"]
                   and item.get("request_params") == request["params"]]
        label = request["operation"] + ":" + ",".join(request["params"][key] for key in sorted(request["params"]))
        if len(matches) != 1:
            reasons.append(f"REQUIRED_READ_MISSING:{label}")
        elif not _read_passed(matches[0]):
            reasons.append(_failure_reason(matches[0], label))
    return {"status": "FAIL" if reasons else "PASS", "reasons": reasons}


# ---------------------------------------------------------------------------------------------
# Fills (ust21150 quantities and times; ust21610 amounts and fees)
# ---------------------------------------------------------------------------------------------

def parse_fills(dated_results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Every filled order row, with its KST fill time. ord_dt is the KST order day; a fill clock earlier
    than the order clock is on the next KST day (a U.S. session ends after midnight KST)."""
    fills: dict[tuple[str, str], dict[str, Any]] = {}
    errors: list[str] = []
    for result in dated_results:
        if result.get("operation") != "account_daily_fills_read" or not _read_passed(result):
            continue
        order_day = _compact_date((result.get("request_params") or {}).get("ord_dt"))
        if order_day is None:
            errors.append("FILL_ORDER_DATE_INVALID")
            continue
        for index, row in enumerate(result.get("data") or []):
            if not isinstance(row, dict):
                errors.append(f"FILL_ROW_NOT_OBJECT:{_ymd(order_day)}:{index}")
                continue
            filled = _quantity(row.get("cntr_qty"))
            if filled is None:
                errors.append(f"FILL_QUANTITY_INVALID:{_ymd(order_day)}:{index}")
                continue
            if filled == 0:
                continue
            ticker = str(row.get("stk_cd") or "").strip().upper()
            side = FILL_SIDES.get(str(row.get("slby_tp_nm") or "").strip())
            price = _decimal(row.get("cntr_uv"))
            ordered_at, filled_at = _clock(row.get("ord_time")), _clock(row.get("cntr_time"))
            order_number = str(row.get("ord_no") or "").strip()
            label = f"{_ymd(order_day)}:{index}"
            if not ticker or not order_number:
                errors.append(f"FILL_ROW_KEY_INVALID:{label}")
                continue
            if side is None:
                errors.append(f"FILL_SIDE_UNKNOWN:{label}")
                continue
            if str(row.get("crnc_code") or "").strip().upper() not in ("USD", ""):
                errors.append(f"FILL_CURRENCY_NOT_USD:{label}")
                continue
            if price is None or price <= 0:
                errors.append(f"FILL_PRICE_INVALID:{label}")
                continue
            if ordered_at is None or filled_at is None:
                errors.append(f"FILL_TIME_INVALID:{label}")
                continue
            fill_day = order_day + timedelta(days=1) if filled_at < ordered_at else order_day
            moment = datetime.combine(fill_day, filled_at, tzinfo=KST)
            item = {"order_date": _ymd(order_day), "ticker": ticker, "side": side, "quantity": filled,
                    "price": str(price), "filled_at_kst": moment.isoformat(),
                    "session_date": moment.astimezone(ET).date().isoformat()}
            key = (_ymd(order_day), order_number)
            if key in fills and fills[key] != item:
                errors.append(f"FILL_ROW_DUPLICATE_CONFLICT:{label}")
                continue
            fills[key] = item
    ordered = sorted(fills.values(), key=lambda item: (item["filled_at_kst"], item["ticker"], item["side"]))
    return ordered, errors


def fills_after(fills: list[dict[str, Any]], moment: datetime) -> list[dict[str, Any]]:
    return [item for item in fills if datetime.fromisoformat(item["filled_at_kst"]) > moment]


def fill_net(fills: list[dict[str, Any]]) -> dict[str, int]:
    net: dict[str, int] = {}
    for item in fills:
        net[item["ticker"]] = net.get(item["ticker"], 0) + (item["quantity"] if item["side"] == "BUY"
                                                            else -item["quantity"])
    return net


def day_trade_requests(fills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sessions = sorted({item["session_date"] for item in fills})
    return [{"operation": "account_day_trades_read", "params": {"base_dt": session.replace("-", "")}}
            for session in sessions]


def fill_sessions(fills: list[dict[str, Any]], day_trade_results: list[dict[str, Any]]
                  ) -> tuple[list[dict[str, Any]], list[str]]:
    """The fills bound to the broker's day-trade read, one bundle per U.S. session.

    Each (session, ticker) group must appear in that session's day-trade read (ust21610) with exactly the
    same bought and sold quantities. The read gives the gross amounts (quantity x price) only: its fee
    column is an estimate and is not used.
    """
    groups: dict[tuple[str, str], dict[str, int]] = {}
    last_day: dict[str, date] = {}
    for item in fills:
        group = groups.setdefault((item["session_date"], item["ticker"]), {"BUY": 0, "SELL": 0})
        group[item["side"]] += item["quantity"]
        day = datetime.fromisoformat(item["filled_at_kst"]).date()
        last_day[item["session_date"]] = max(day, last_day.get(item["session_date"], day))
    sessions: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for (session, ticker), quantities in sorted(groups.items()):
        base = session.replace("-", "")
        results = [item for item in day_trade_results if item.get("operation") == "account_day_trades_read"
                   and (item.get("request_params") or {}).get("base_dt") == base and _read_passed(item)]
        rows = [row for result in results for row in result.get("data") or []
                if isinstance(row, dict) and str(row.get("stk_cd") or "").strip().upper() == ticker]
        if len(rows) != 1:
            errors.append(f"FILL_AMOUNT_UNAVAILABLE:{session}:{ticker}")
            continue
        row = rows[0]
        bought, sold = _decimal(row.get("tdy_buyq")), _decimal(row.get("tdy_sellq"))
        buy_amount, sell_amount = _decimal(row.get("tdy_buy_amt")), _decimal(row.get("tdy_sell_amt"))
        if any(value is None or value < 0 for value in (bought, sold, buy_amount, sell_amount)):
            errors.append(f"FILL_AMOUNT_INVALID:{session}:{ticker}")
            continue
        if bought != quantities["BUY"] or sold != quantities["SELL"]:
            errors.append(f"FILL_SOURCES_DISAGREE:{session}:{ticker}")
            continue
        bundle = sessions.setdefault(session, {
            "session_date": session, "last_fill_day": last_day[session],
            "gross": {"SELL": Decimal("0"), "BUY": Decimal("0")}, "quantities": {}})
        bundle["gross"]["SELL"] += sell_amount
        bundle["gross"]["BUY"] += buy_amount
        for side in ("BUY", "SELL"):
            if quantities[side]:
                bundle["quantities"][(ticker, side)] = quantities[side]
    return [sessions[key] for key in sorted(sessions)], errors


def settlement_slots(snapshot_results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Pending settlements by Korean settlement date from the cash-detail read (ust21160).

    Each dN slot is a settlement date with its sell amount (proceeds after fees) and buy amount (cost with
    fees). An amount that is not readable stays None (judged only where the slot is used). D0 has no amount
    fields, so an amount settling today is not visible here.
    """
    rows = [row for result in snapshot_results
            if result.get("operation") == "account_deposit_detail_read" and _read_passed(result)
            for row in result.get("data") or [] if isinstance(row, dict)]
    if len(rows) != 1:
        return [], ["SETTLEMENT_DETAIL_UNAVAILABLE"]
    slots, errors, seen = [], [], set()
    for name in SETTLEMENT_SLOTS:
        text = str(rows[0].get(f"{name}_setl_dt") or "").strip()
        sell, buy = _decimal(rows[0].get(f"{name}_usd_sell_excta")), _decimal(rows[0].get(f"{name}_usd_buy_excta"))
        if not text:
            if sell or buy:
                errors.append(f"SETTLEMENT_SLOT_DATE_MISSING:{name}")
            continue
        day = _compact_date(text)
        if day is None or day in seen:
            errors.append(f"SETTLEMENT_SLOT_DATE_INVALID:{name}")
            continue
        seen.add(day)
        slots.append({"slot": name, "settlement_date": day,
                      "SELL": sell if sell is not None and sell >= 0 else None,
                      "BUY": buy if buy is not None and buy >= 0 else None})
    return slots, errors


def settlement_rows(rows: list[dict[str, Any]], table: dict[str, Any]) -> list[dict[str, Any]]:
    """Transaction-history trade rows (settled fills): settlement day, ticker, side, quantity, amount.

    fc_exct_amt is the settled amount with fees (sell: proceeds, buy: cost). Unreadable values stay None and
    are judged only where a row is used.
    """
    trades = []
    for row in rows:
        kind, memo = str(row.get("deal_kind_nm") or "").strip(), str(row.get("rmrk_nm") or "").strip()
        if classify_row(kind, memo, table)[0] != "TRADE":
            continue
        found = {side for word, side in FILL_SIDES.items() if word in memo}
        trades.append({
            "key": f"{row.get('deal_dt')}:{str(row.get('deal_no') or '').strip()}",
            "settlement_date": _compact_date(row.get("deal_dt")),
            "ticker": str(row.get("stk_cd") or "").strip().upper(),
            "side": next(iter(found)) if len(found) == 1 else None,
            "quantity": _quantity(row.get("deal_qty")), "amount": _decimal(row.get("fc_exct_amt")),
            "usd": str(row.get("crnc_code") or "").strip().upper() == "USD"})
    return trades


def _within_fee_range(settled: Decimal, gross: Decimal) -> bool:
    return abs(settled - gross) <= gross * SETTLEMENT_FEE_RATE + SETTLEMENT_FEE_FIXED_USD


def _bundle_failures(day: date, amounts: dict[str, Any], sessions: list[dict[str, Any]]) -> list[str]:
    """Why these sessions cannot be the whole settlement of this date (empty: they are)."""
    failures = [f"SETTLEMENT_BEFORE_FILL:{day.isoformat()}:{item['session_date']}"
                for item in sessions if day <= item["last_fill_day"]]
    if amounts["source"] == D0_SOURCE:
        # Today's amount is not shown: only the date order is checked here; explain_change checks the cash
        # residual against these sessions' gross.
        return failures
    for side in ("SELL", "BUY"):
        gross = sum((item["gross"][side] for item in sessions), Decimal("0"))
        if not _within_fee_range(amounts[side], gross):
            failures.append(f"SETTLEMENT_OUTSIDE_FEE_RANGE:{day.isoformat()}:{side}:{_money(amounts[side] - gross)}")
    if amounts["source"] == "SETTLED":
        expected: dict[tuple[str, str], int] = {}
        for item in sessions:
            for key, quantity in item["quantities"].items():
                expected[key] = expected.get(key, 0) + quantity
        if expected != amounts["quantities"]:
            failures.append(f"SETTLEMENT_QUANTITY_MISMATCH:{day.isoformat()}")
    return failures


def _partitions(count: int, parts: int):
    """Every split of `count` ordered items into `parts` non-empty consecutive runs, as (start, end) pairs."""
    if parts == 1:
        yield [(0, count)]
        return
    for first in range(1, count - parts + 2):
        for rest in _partitions(count - first, parts - 1):
            yield [(0, first)] + [(start + first, end + first) for start, end in rest]


def _settlement_detail(day: date, amounts: dict[str, Any], sessions: list[dict[str, Any]]) -> dict[str, Any]:
    detail = {"settlement_date": day.isoformat(), "source": amounts["source"],
              "sessions": [item["session_date"] for item in sessions],
              "sell_usd": _money(amounts["SELL"]) if amounts["SELL"] is not None else None,
              "buy_usd": _money(amounts["BUY"]) if amounts["BUY"] is not None else None,
              "gross_sell_usd": _money(sum((item["gross"]["SELL"] for item in sessions), Decimal("0"))),
              "gross_buy_usd": _money(sum((item["gross"]["BUY"] for item in sessions), Decimal("0")))}
    if "carried_from" in amounts:
        detail["carried_from"] = amounts["carried_from"]
    return detail


def _assign(sessions: list[dict[str, Any]], dated: dict[date, dict[str, Any]]
            ) -> tuple[Decimal, list[dict[str, Any]], list[str]]:
    """The first assignment of the sessions (in order) to the dates (in order) that passes, as (cash, details,
    []), else (0, [], failures). A date left open (D0_SOURCE) adds nothing to the cash."""
    days = sorted(dated)
    if not days:
        return Decimal("0"), [], ["SETTLEMENT_AMOUNT_NOT_FOUND:" + ",".join(item["session_date"] for item in sessions)]
    candidates = list(_partitions(len(sessions), len(days))) if len(days) <= len(sessions) else []
    for runs in candidates:
        failures = [failure for day, (start, end) in zip(days, runs)
                    for failure in _bundle_failures(day, dated[day], sessions[start:end])]
        if failures:
            if len(candidates) == 1:
                return Decimal("0"), [], failures
            continue
        details = [_settlement_detail(day, dated[day], sessions[start:end]) for day, (start, end) in zip(days, runs)]
        return sum((dated[day]["SELL"] - dated[day]["BUY"] for day in days if dated[day]["source"] != D0_SOURCE),
                   Decimal("0")), details, []
    return Decimal("0"), [], ["SETTLEMENT_NOT_MATCHED_TO_FILLS:" + ",".join(day.isoformat() for day in days)]


def fill_settlement(fills: list[dict[str, Any]], day_trade_results: list[dict[str, Any]], *,
                    slots: list[dict[str, Any]], slot_errors: list[str], trades: list[dict[str, Any]],
                    today: date | None = None, carried: dict[date, dict[str, Any]] | None = None
                    ) -> tuple[Decimal, list[dict[str, Any]], list[str]]:
    """Cash effect of the fills from the broker's actual settlement amounts (redesign T1 r2, R2-1).

    A fill moves the order-available cash by its settlement amount, fees included: while pending, the
    cash-detail slot of its settlement date holds it (dN sell/buy excta); once settled, the transaction-history
    trade rows of that date hold it (fc_exct_amt). Amounts are known per settlement date, not per fill, so the
    sessions are matched to dates in order: the sessions settling on one date, together, must equal that
    date's amounts within the fee range on each side (|settlement - gross| <= gross x 0.5% + 0.50), and a
    settled date's rows must carry exactly their quantities. A date can only hold fills from earlier KST days,
    so slots and rows dated on or before the first fill's KST day belong to fills before the baseline and are
    never counted (that cash is already in the baseline; a settlement does not move the order-available cash).

    T1 r3 C4: a settlement due today (KST, `today`) shows no amount before the broker's morning processing (D0
    has no slot amounts and the trade row comes later). (a) When the previous run read that date's pending
    slot (`carried`), that amount stands for it. (b) Otherwise, if every other date matches with today's left
    open, the only failure is SETTLEMENT_D0_NOT_SHOWN:<today> and the open date adds no cash (explain_change
    checks the residual against those sessions' gross).
    """
    if not fills:
        return Decimal("0"), [], []
    sessions, errors = fill_sessions(fills, day_trade_results)
    if errors:
        return Decimal("0"), [], errors
    first_day = min(item["last_fill_day"] for item in sessions)
    sides = {key for item in sessions for key in item["quantities"]}
    dated: dict[date, dict[str, Any]] = {}
    for row in trades:
        if row["settlement_date"] is None or row["settlement_date"] <= first_day \
                or row["ticker"] not in {ticker for ticker, _ in sides}:
            continue
        if row["side"] is None or row["quantity"] is None or row["amount"] is None or row["amount"] < 0 \
                or not row["usd"]:
            errors.append(f"SETTLEMENT_ROW_INVALID:{row['key']}")
            continue
        if (row["ticker"], row["side"]) not in sides:
            continue
        entry = dated.setdefault(row["settlement_date"], {"source": "SETTLED", "SELL": Decimal("0"),
                                                          "BUY": Decimal("0"), "quantities": {}})
        entry[row["side"]] += row["amount"]
        key = (row["ticker"], row["side"])
        entry["quantities"][key] = entry["quantities"].get(key, 0) + row["quantity"]
    for slot in slots:
        readable = slot["SELL"] is not None and slot["BUY"] is not None
        if slot["settlement_date"] <= first_day or (readable and not slot["SELL"] and not slot["BUY"]):
            continue
        if not readable:
            errors.append(f"SETTLEMENT_SLOT_AMOUNT_INVALID:{slot['slot']}")
            continue
        if slot["settlement_date"] in dated:
            errors.append(f"SETTLEMENT_DATE_BOTH_SETTLED_AND_PENDING:{slot['settlement_date'].isoformat()}")
            continue
        dated[slot["settlement_date"]] = {"source": "PENDING", "SELL": slot["SELL"], "BUY": slot["BUY"]}
    errors += slot_errors
    if errors:
        return Decimal("0"), [], errors
    unseen_today = today is not None and today > first_day and today not in dated
    if unseen_today and today in (carried or {}):
        dated[today] = {**carried[today], "source": CARRIED_SOURCE}
        unseen_today = False
    total, details, failures = _assign(sessions, dated)
    if failures and unseen_today:
        open_total, open_details, open_failures = _assign(
            sessions, {**dated, today: {"source": D0_SOURCE, "SELL": None, "BUY": None}})
        if not open_failures:
            return open_total, open_details, [f"{D0_NOT_SHOWN}:{today.isoformat()}"]
    return total, details, failures


def carried_settlements(previous: dict[str, Any] | None, today: date) -> dict[date, dict[str, Any]]:
    """T1 r3 C4 (a): today's settlement amounts as the previous run read them while they were pending.

    They are that run's I3 settlement entry of this date with source PENDING (the cash-detail slot of the date,
    a broker read of an earlier day). An unreadable entry is not used (the date then stays unseen).
    """
    invariants = previous.get("invariants") if isinstance(previous, dict) else None
    i3 = invariants.get("I3") if isinstance(invariants, dict) else None
    entries = i3.get("settlements") if isinstance(i3, dict) else None
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict) or item.get("source") != "PENDING" \
                or item.get("settlement_date") != today.isoformat():
            continue
        sell, buy = _decimal(item.get("sell_usd")), _decimal(item.get("buy_usd"))
        if sell is None or buy is None or sell < 0 or buy < 0:
            return {}
        return {today: {"SELL": sell, "BUY": buy, "carried_from": str(previous.get("generated_at") or "")}}
    return {}


# ---------------------------------------------------------------------------------------------
# Transaction-history rows (F3 evidence and I3 flows)
# ---------------------------------------------------------------------------------------------

def history_rows(dated_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for result in dated_results:
        if result.get("operation") == "account_transaction_history_read" and _read_passed(result):
            return [row for row in result.get("data") or [] if isinstance(row, dict)]
    return []


def flow_cash(rows: list[dict[str, Any]], *, after: datetime, until: datetime,
              table: dict[str, Any]) -> tuple[Decimal, list[dict[str, Any]], list[str]]:
    """USD cash effect of the non-trade rows processed after the last record (KST deal day + time).

    Trades are explained by the fills. Deposits, withdrawals and FX use the reviewed table's sign;
    dividends, fees, taxes, interest and corporate-action cash take their sign from the memo
    (FLOW_IN +, FLOW_OUT -). Anything else is unresolved and fails closed.
    """
    total, items, errors = Decimal("0"), [], []
    record_day = after.astimezone(KST).date()
    for index, row in enumerate(rows):
        deal_day = _compact_date(row.get("deal_dt"))
        if deal_day is None:
            errors.append(f"FLOW_ROW_DATE_INVALID:{index}")
            continue
        clock = _clock(row.get("proc_time"))
        if clock is None:
            if deal_day < record_day:
                continue
            if deal_day == record_day:
                errors.append(f"FLOW_ROW_TIME_UNKNOWN:{deal_day.isoformat()}:{row.get('deal_no')}")
                continue
            moment = datetime.combine(deal_day, time(0, 0), tzinfo=KST)
        else:
            moment = datetime.combine(deal_day, clock, tzinfo=KST)
        if not after < moment <= until:
            continue
        kind, memo = str(row.get("deal_kind_nm") or "").strip(), str(row.get("rmrk_nm") or "").strip()
        classification, sign = classify_row(kind, memo, table)
        key = f"{deal_day.isoformat()}:{str(row.get('deal_no') or '').strip()}"
        currency = str(row.get("crnc_code") or "").strip().upper()
        if classification == "TRADE":
            continue
        if classification in ("UNCLASSIFIED", "TRANSFER_SIGN_UNKNOWN"):
            errors.append(f"FLOW_ROW_{classification}:{key}")
            continue
        if currency != "USD":
            if classification == "FX":
                errors.append(f"FLOW_FX_ROW_CURRENCY_NOT_USD:{key}")
            continue
        amount = _decimal(row.get("fc_exct_amt"))
        if amount is None or amount < 0:
            errors.append(f"FLOW_ROW_AMOUNT_INVALID:{key}")
            continue
        if classification in SIGNED_BY_MEMO_CLASSES:
            # The memo only (as the reviewed table's sign_fields): the deposit/withdrawal kind name holds both words.
            incoming, outgoing = FLOW_IN in memo, FLOW_OUT in memo
            sign = 1 if incoming and not outgoing else -1 if outgoing and not incoming else None
        if sign is None:
            errors.append(f"FLOW_ROW_SIGN_UNKNOWN:{key}")
            continue
        signed = amount * sign
        total += signed
        items.append({"key": key, "classification": classification, "signed_amount_usd": _money(signed),
                      "processed_at_kst": moment.isoformat()})
    return total, items, errors


def cash_flow_evidence_block(rows: list[dict[str, Any]], *, period_from: date, period_to: date,
                             prior_blocks: list[Any], table: dict[str, Any]
                             ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """F3: sanitized evidence for [period_from, period_to] and a declaration in full (no human input).

    Returns (evidence, declaration, reasons). Any normalization failure or unresolved row is a HOLD.
    """
    in_period = [row for row in rows
                 if (day := _compact_date(row.get("deal_dt"))) is not None and period_from <= day <= period_to]
    raw = {"return_code": 0, "result_list": in_period}
    raw_sha256 = hashlib.sha256(json.dumps(in_period, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")).encode("utf-8")).hexdigest()
    try:
        evidence = normalize_transaction_history(
            raw, period_from=period_from.isoformat(), period_to=period_to.isoformat(), raw_sha256=raw_sha256,
            table=table, collection="AUTO_CORE_BRIDGE_READ")
    except CashFlowError as exc:
        return None, None, [str(exc) or "CASH_FLOW_EVIDENCE_INVALID"]
    if evidence["unresolved"]:
        return evidence, None, ["CASH_FLOW_EVIDENCE_UNRESOLVED:" + ",".join(evidence["unresolved"])]
    try:
        draft = build_declaration(evidence, declared_usd=None, prior_blocks=prior_blocks)
        declaration = build_declaration(evidence, declared_usd=draft["new_external_net_usd"],
                                        prior_blocks=prior_blocks)
    except CashFlowError as exc:
        return evidence, None, [str(exc)]
    return evidence, declaration, []


def write_evidence(evidence: dict[str, Any], root: Path) -> Path:
    """Create-once by content: the same evidence on a rerun reuses the same file."""
    path = Path(root) / (f"auto-core-{evidence['period_from']}_{evidence['period_to']}-"
                         f"{evidence['evidence_hash'][:12]}.json")
    if not path.exists():
        write_json(path, evidence)
    return path


# ---------------------------------------------------------------------------------------------
# Invariants I2-I5
# ---------------------------------------------------------------------------------------------

def explain_change(*, baseline_holdings: Any, baseline_time: datetime, cash_baseline: dict[str, Any],
                   broker_holdings: dict[str, int], broker_cash: Decimal, fills: list[dict[str, Any]],
                   fill_errors: list[str], day_trade_results: list[dict[str, Any]],
                   rows: list[dict[str, Any]], slots: list[dict[str, Any]], slot_errors: list[str],
                   open_order_count: int, now: datetime, table: dict[str, Any],
                   carried: dict[date, dict[str, Any]] | None = None) -> dict[str, Any]:
    """I2 and I3 for one baseline (the last record, or the previous run's would_apply).

    cash_baseline is {"cash": Decimal | None, "at": datetime | None, "reason": unknown-baseline code,
    "reference": where it came from}: for the last record, the order-available cash and generated_at of
    that record's own broker snapshot (R2-2); it never falls back to the state's cash.
    When today's settlement is left open (T1 r3 C4 b), the cash residual is that settlement: it must lie within
    the fee range of the sessions put on today (one 0.50 per side, plus the 1.00 tolerance), else
    SETTLEMENT_D0_OUTSIDE_FEE_RANGE. The run holds either way; the open date never makes I3 pass.
    """
    window = fills_after(fills, baseline_time)
    net = fill_net(window)
    i2_reasons = list(fill_errors)
    changes: list[dict[str, Any]] = []
    if not isinstance(baseline_holdings, dict) or any(
            not isinstance(value, int) or isinstance(value, bool) for value in baseline_holdings.values()):
        i2_reasons.append("RECORDED_HOLDINGS_INVALID")
        baseline_holdings = {}
    for ticker in sorted(set(baseline_holdings) | set(broker_holdings) | set(net)):
        recorded, actual, moved = baseline_holdings.get(ticker, 0), broker_holdings.get(ticker, 0), net.get(ticker, 0)
        if recorded != actual or moved:
            changes.append({"ticker": ticker, "recorded": recorded, "broker": actual, "fills_net": moved})
        if recorded + moved != actual:
            i2_reasons.append(f"QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:{ticker}")
    i3_reasons: list[str] = []
    baseline_cash, cash_at = cash_baseline.get("cash"), cash_baseline.get("at")
    trades = flows = Decimal("0")
    settlements: list[dict[str, Any]] = []
    flow_items: list[dict[str, Any]] = []
    cash_window: list[dict[str, Any]] = []
    if baseline_cash is None or cash_at is None:
        i3_reasons.append(cash_baseline.get("reason") or BASELINE_UNKNOWN)
    else:
        cash_window = fills_after(fills, cash_at)
        trades, settlements, trade_errors = fill_settlement(
            cash_window, day_trade_results, slots=slots, slot_errors=slot_errors,
            trades=settlement_rows(rows, table), today=now.astimezone(KST).date(), carried=carried)
        flows, flow_items, flow_errors = flow_cash(rows, after=cash_at, until=now, table=table)
        i3_reasons += trade_errors + flow_errors
    if open_order_count:
        # Open orders reserve order-available cash, so the change cannot be explained by fills alone.
        i3_reasons.append(f"OPEN_ORDERS_PRESENT:{open_order_count}")
    difference = None
    if baseline_cash is not None and cash_at is not None:
        difference = broker_cash - baseline_cash - trades - flows
        unseen = next((item for item in settlements if item["source"] == D0_SOURCE), None)
        if unseen is not None:
            gross_sell, gross_buy = Decimal(unseen["gross_sell_usd"]), Decimal(unseen["gross_buy_usd"])
            allowed = ((gross_sell + gross_buy) * SETTLEMENT_FEE_RATE + CASH_TOLERANCE_USD
                       + SETTLEMENT_FEE_FIXED_USD * sum(1 for gross in (gross_sell, gross_buy) if gross))
            off = difference - (gross_sell - gross_buy)
            unseen["residual_usd"] = _money(difference)
            if abs(off) > allowed:
                i3_reasons.append(f"SETTLEMENT_D0_OUTSIDE_FEE_RANGE:{unseen['settlement_date']}:{_money(off)}")
        elif abs(difference) > CASH_TOLERANCE_USD:
            i3_reasons.append(f"CASH_CHANGE_NOT_EXPLAINED:{_money(difference)}")
    return {
        "I2": {"status": "FAIL" if i2_reasons else "PASS", "reasons": i2_reasons,
               "fills_counted": len(window)},
        "I3": {"status": "FAIL" if i3_reasons else "PASS", "reasons": i3_reasons,
               "baseline": cash_baseline.get("reference"),
               "baseline_cash_usd": _money(baseline_cash) if baseline_cash is not None else None,
               "broker_cash_usd": _money(broker_cash), "fills_counted": len(cash_window),
               "fill_cash_usd": _money(trades), "settlements": settlements,
               "flow_cash_usd": _money(flows), "unexplained_usd": _money(difference) if difference is not None else None,
               "flows": flow_items},
        "holdings_change": changes, "fills": window,
    }


def _last_ledger_entry(ledger_path: Path) -> dict[str, Any] | None:
    lines = [line for line in Path(ledger_path).read_bytes().splitlines() if line.strip()] \
        if Path(ledger_path).is_file() else []
    try:
        entry = json.loads(lines[-1].decode("utf-8")) if lines else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return entry if isinstance(entry, dict) else None


def _find_proposal(proposal_id: str, roots: tuple[Path, ...] | list[Path]) -> dict[str, Any] | None:
    """The saved reconciliation proposal with this id (newest folders first), or None."""
    for root in roots:
        for path in sorted(Path(root).glob("*/reconciliation_proposal.json"), reverse=True):
            try:
                proposal = load_json(path)
            except (OSError, ValueError):
                continue
            if isinstance(proposal, dict) and proposal.get("proposal_id") == proposal_id:
                return proposal
    return None


def baseline_snapshot(state: dict[str, Any], ledger_path: Path, *,
                      roots: tuple[Path, ...] | list[Path] | None = None) -> dict[str, Any]:
    """R2-2: the I3 baseline is the broker snapshot of the last record (broker to broker).

    The last ledger entry names that snapshot: an auto-core entry directly (auto_core.snapshot path and hash),
    a human-path entry through its proposal_id (the saved proposal names the snapshot path and hash). The
    snapshot must be schema-valid, hash to that value and to the state's recorded evidence_sha256. Its
    order-available cash and generated_at are the baseline. Anything missing is unknown: there is no fallback
    to the state's cash, which may still hold the old minimum definition.
    """
    def unknown(detail: str) -> dict[str, Any]:
        return {"cash": None, "at": None, "reason": f"{BASELINE_UNKNOWN}:{detail}",
                "reference": {"status": "UNKNOWN", "detail": detail}}

    last = _last_ledger_entry(ledger_path)
    if last is None:
        return unknown("LEDGER_LAST_ENTRY_UNREADABLE")
    named = (last.get("auto_core") or {}).get("snapshot") if isinstance(last.get("auto_core"), dict) else None
    if isinstance(named, dict):
        source, path_text, expected = "AUTO_CORE_LEDGER_ENTRY", named.get("path"), named.get("snapshot_hash")
    elif isinstance(last.get("proposal_id"), str) and last["proposal_id"]:
        proposal = _find_proposal(last["proposal_id"], BASELINE_SEARCH_ROOTS if roots is None else roots)
        if proposal is None:
            return unknown("PROPOSAL_NOT_FOUND")
        source_block = proposal.get("source") or {}
        source, path_text, expected = ("LEDGER_PROPOSAL_ID", source_block.get("snapshot_path"),
                                       source_block.get("snapshot_hash"))
    else:
        return unknown("LEDGER_ENTRY_NAMES_NO_SNAPSHOT")
    if not isinstance(path_text, str) or not path_text or not isinstance(expected, str):
        return unknown("SNAPSHOT_REFERENCE_INVALID")
    path = Path(path_text) if Path(path_text).is_absolute() else REPO_ROOT / path_text
    try:
        snapshot = load_json(path)
    except (OSError, ValueError):
        return unknown("SNAPSHOT_NOT_FOUND")
    if not isinstance(snapshot, dict) or validate_instance(snapshot, SNAPSHOT_SCHEMA):
        return unknown("SNAPSHOT_SCHEMA_INVALID")
    content_hash = canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
    if snapshot.get("snapshot_hash") != expected or content_hash != expected:
        return unknown("SNAPSHOT_HASH_MISMATCH")
    if (state.get("last_confirmed_broker_snapshot") or {}).get("evidence_sha256") != expected:
        return unknown("SNAPSHOT_NOT_THE_RECORDED_EVIDENCE")
    cash = _decimal((snapshot.get("cash") or {}).get("order_available_cash"))
    generated_at = _parse_utc(snapshot.get("generated_at"))
    if cash is None:
        return unknown("ORDER_AVAILABLE_CASH_MISSING")
    if generated_at is None:
        return unknown("GENERATED_AT_INVALID")
    return {"cash": cash, "at": generated_at, "reason": None,
            "reference": {"status": "OK", "source": source, "snapshot_path": path_text, "snapshot_hash": expected,
                          "order_available_cash_usd": _money(cash), "generated_at": snapshot["generated_at"]}}


def invariant_i4(state: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    status = ledger_status(ledger_path)
    reasons = []
    if not status["exists"] or status["entries"] == 0:
        reasons.append("LEDGER_MISSING")
    elif not status["chain_ok"]:
        reasons.append("LEDGER_INTEGRITY_FAILED")
    else:
        if status["last_portfolio_hash_after"] != canonical_hash(state):
            reasons.append("STATE_CHANGED_OUTSIDE_LEDGER")
        last = _last_ledger_entry(ledger_path) or {}
        if last.get("state_revision_after") != state.get("state_revision"):
            reasons.append("STATE_REVISION_NOT_LAST_LEDGER_REVISION")
    return {"status": "FAIL" if reasons else "PASS", "reasons": reasons,
            "ledger_entries": status["entries"], "state_revision": state.get("state_revision")}


def invariant_i5(state: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    if proposal.get("status") != "USER_CONFIRMATION_REQUIRED":
        return {"status": "PASS", "reasons": [], "note": "NOTHING_TO_WRITE"}
    reasons = []
    try:
        preview = preview_updated_state(state, proposal)
        _assert_untouched(state, preview)
        for field in NEVER_TOUCHED_FIELDS:
            if canonical_hash(state.get(field)) != canonical_hash(preview.get(field)):
                reasons.append(f"NEVER_TOUCHED_FIELD_CHANGED:{field}")
    except (ValueError, KeyError, TypeError) as exc:
        reasons.append(str(exc) or type(exc).__name__)
    return {"status": "FAIL" if reasons else "PASS", "reasons": reasons}


# ---------------------------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------------------------

def _broker_holdings(snapshot: dict[str, Any]) -> dict[str, int] | None:
    holdings: dict[str, int] = {}
    for item in snapshot.get("holdings") or []:
        quantity = item.get("held_quantity")
        if not isinstance(quantity, (int, float)) or isinstance(quantity, bool) or quantity != int(quantity):
            return None
        holdings[item["ticker"]] = int(quantity)
    return holdings


def proposal_warnings(proposal: dict[str, Any]) -> list[str]:
    """T1 r3 C3: what the proposal flags without blocking a record (its warnings and the post-apply alert
    check errors), carried to reconcile.json, result.json and LATEST.json."""
    return ([f"PROPOSAL_WARNING:{code}" for code in proposal.get("warnings") or []]
            + [f"POST_APPLY_CHECK_ERROR:{error}" for error in (proposal.get("post_apply_checks") or {}).get("errors") or []])


def d0_only(reasons: Any) -> bool:
    """True when the only reason left is today's settlement not shown yet (T1 r3 C4 b)."""
    return isinstance(reasons, list) and bool(reasons) and all(
        isinstance(reason, str) and D0_ONLY.fullmatch(reason) for reason in reasons)


def baseline_stale(reconcile: dict[str, Any]) -> bool:
    """T1 r3 C4: the fill window since the last record holds more than 80% of its limit (or exceeds it)."""
    days = (reconcile.get("fill_window") or {}).get("days")
    if not isinstance(days, int):
        found = [re.fullmatch(r"FILL_WINDOW_TOO_LONG:(\d+)", reason) for reason in reconcile.get("reasons") or []
                 if isinstance(reason, str)]
        days = next((int(match.group(1)) for match in found if match), None)
    return days is not None and days > FILL_WINDOW_MAXIMUM_DAYS * STALE_WINDOW_SHARE


def would_apply_block(proposal: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """What the state would hold after this proposal (or now, when nothing changes)."""
    patch = proposal.get("proposed_patch") or {}
    source = patch if proposal.get("status") == "USER_CONFIRMATION_REQUIRED" else state
    return {"holdings": dict(source.get("holdings") or {}),
            "available_cash_usd": source.get("available_cash_usd"),
            "average_cost_usd": dict(source.get("average_cost_usd") or {}),
            "as_of": proposal["confirmed_snapshot_record"]["as_of"],
            "as_of_timestamp": proposal["confirmed_snapshot_record"]["as_of_timestamp"],
            "proposal_id": proposal.get("proposal_id"), "change_kind": proposal.get("change_kind")}


def run_auto(*, mode: str, kill_switch: bool, state_path: Path, journal_activation_date: str | None,
             runtime: Path, rate_policy: dict[str, Any], broker_policy: dict[str, Any],
             post_apply_check: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
             output_directory: Path, provenance: dict[str, Any],
             compare_baseline: dict[str, Any] | None = None, previous_run: dict[str, Any] | None = None,
             reader: Callable[..., list[dict[str, Any]]] = invoke_account_bridge_batch,
             now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
             evidence_root: Path | None = None, table: dict[str, Any] | None = None,
             config_path: Path | None = None,
             provenance_source: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    """One auto reconciliation. Writes only reconcile outputs, evidence, and (apply mode) the state.

    previous_run is the latest earlier reconcile.json (T1 r3 C4 a). config_path and provenance_source are what
    apply_auto_core reads again just before a write (T1 r3 C1; defaults: the policy file and git).
    """
    if mode not in ("compare", "apply"):
        raise AutoReconcileError("AUTO_CORE_MODE_INVALID")
    evidence_root = Path(evidence_root) if evidence_root is not None else EVIDENCE_ROOT
    table = table or load_classification()
    state_path = Path(state_path)
    ledger_path = default_ledger_path(state_path)
    output_directory = Path(output_directory)
    before = file_hash(state_path)
    state = load_json(state_path)
    started = now()
    recorded_at = record_time(state)
    if recorded_at is None:
        raise AutoReconcileError("LAST_RECORD_TIME_UNKNOWN")
    blocks = read_ledger_blocks(ledger_path)
    evidence_from = evidence_period_start(blocks, journal_activation_date)
    if evidence_from is None:
        raise AutoReconcileError("CASH_FLOW_PERIOD_START_UNKNOWN")
    plan = plan_reads(recorded_at=recorded_at, evidence_from=evidence_from, now=started)
    if len(plan["fill_dates"]) > FILL_WINDOW_MAXIMUM_DAYS:
        raise AutoReconcileError(f"FILL_WINDOW_TOO_LONG:{len(plan['fill_dates'])}")
    if (plan["today"] - plan["history_from"]).days > TRANSACTION_HISTORY_MAXIMUM_DAYS:
        raise AutoReconcileError("TRANSACTION_HISTORY_PERIOD_TOO_LONG")

    # One read: the snapshot reads, then the dated reads, then the day trades of the sessions with fills.
    snapshot_results = reader([{"operation": operation} for operation in SNAPSHOT_OPERATIONS],
                              runtime=runtime, policy=rate_policy)
    expected = dated_requests(plan)
    dated_results = reader(expected, runtime=runtime, policy=rate_policy)
    fills, fill_errors = parse_fills(dated_results)
    baseline_time = _parse_utc((compare_baseline or {}).get("as_of_timestamp"))
    earliest = min(recorded_at, baseline_time) if baseline_time is not None else recorded_at
    needed = day_trade_requests(fills_after(fills, earliest))
    day_results = reader(needed, runtime=runtime, policy=rate_policy) if needed else []
    generated_at = now().isoformat()
    snapshot = normalize_snapshot(snapshot_results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                  generated_at=generated_at,
                                  maximum_age_seconds=int(broker_policy["maximum_age_seconds"]))
    snapshot_errors = validate_instance(snapshot, SNAPSHOT_SCHEMA)
    if snapshot_errors:
        raise AutoReconcileError("BROKER_SHADOW_SCHEMA_FAILED:" + ";".join(snapshot_errors[:3]))
    if file_hash(state_path) != before:
        raise AutoReconcileError("PORTFOLIO_STATE_MUTATION_DETECTED")

    invariants: dict[str, Any] = {"I1": invariant_i1(snapshot_results, dated_results + day_results,
                                                     expected + needed)}
    reasons: list[str] = []
    rows = history_rows(dated_results)
    evidence, declaration, evidence_reasons = (None, None, ["CASH_FLOW_EVIDENCE_NOT_READ"])
    if not any(reason.startswith("REQUIRED_READ") and "transaction_history" in reason
               for reason in invariants["I1"]["reasons"]):
        evidence, declaration, evidence_reasons = cash_flow_evidence_block(
            rows, period_from=plan["evidence_from"], period_to=plan["today"], prior_blocks=blocks, table=table)
    evidence_path = write_evidence(evidence, evidence_root) if evidence is not None else None

    ledger = ledger_status(ledger_path)
    # The proposal names a create-once copy: a later run on the same day rewrites the plain file, while the
    # next day's I3 baseline must still find the snapshot behind this record (R2-2).
    kept_snapshot = output_directory / f"kiwoom_broker_snapshot.{snapshot['snapshot_hash'][:16]}.shadow.json"
    proposal = reconciliation_proposal(
        snapshot, state, results=snapshot_results, maximum_age_seconds=int(broker_policy["maximum_age_seconds"]),
        portfolio_state_path=_repo_relative(state_path),
        snapshot_path=_repo_relative(kept_snapshot),
        ledger_last_hash_after=ledger["last_portfolio_hash_after"],
        ledger_last_hash_before=ledger["last_portfolio_hash_before"], ledger_integrity_ok=ledger["chain_ok"],
        post_apply_check=post_apply_check, cash_flow_declaration=declaration)
    proposal_errors = validate_instance(proposal, PROPOSAL_SCHEMA)
    if proposal_errors:
        raise AutoReconcileError("RECONCILIATION_PROPOSAL_SCHEMA_FAILED:" + ";".join(proposal_errors[:3]))
    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(output_directory / SNAPSHOT_FILE, snapshot)
    if not kept_snapshot.exists():
        write_json(kept_snapshot, snapshot)
    write_json(output_directory / "reconciliation_proposal.json", proposal)

    broker_holdings = _broker_holdings(snapshot)
    broker_cash = _decimal((snapshot.get("cash") or {}).get("order_available_cash"))
    open_order_count = len(snapshot.get("open_orders") or [])
    slots, slot_errors = settlement_slots(snapshot_results)
    carried = carried_settlements(previous_run, plan["today"])
    explained: dict[str, Any] = {"holdings_change": [], "fills": []}
    if broker_holdings is None or broker_cash is None or invariants["I1"]["status"] != "PASS":
        reason = "BROKER_SNAPSHOT_UNUSABLE" if invariants["I1"]["status"] == "PASS" else "I1_FAILED"
        invariants["I2"] = {"status": "FAIL", "reasons": [reason]}
        invariants["I3"] = {"status": "FAIL", "reasons": [reason]}
    else:
        explained = explain_change(
            baseline_holdings=state.get("holdings"), baseline_time=recorded_at,
            cash_baseline=baseline_snapshot(state, ledger_path),
            broker_holdings=broker_holdings, broker_cash=broker_cash, fills=fills, fill_errors=fill_errors,
            day_trade_results=day_results, rows=rows, slots=slots, slot_errors=slot_errors,
            open_order_count=open_order_count, now=now(), table=table, carried=carried)
        invariants["I2"], invariants["I3"] = explained["I2"], explained["I3"]
    invariants["I4"] = invariant_i4(state, ledger_path)
    invariants["I5"] = invariant_i5(state, proposal)

    compare = None
    if compare_baseline is not None and broker_holdings is not None and broker_cash is not None \
            and invariants["I1"]["status"] == "PASS":
        if baseline_time is not None:
            # The previous run's would_apply cash is that run's broker order-available amount.
            previous_cash = _decimal(compare_baseline.get("available_cash_usd"))
            check = explain_change(
                baseline_holdings=compare_baseline.get("holdings"), baseline_time=baseline_time,
                cash_baseline={"cash": previous_cash, "at": baseline_time, "reason": "RECORDED_CASH_INVALID",
                               "reference": {"status": "OK" if previous_cash is not None else "UNKNOWN",
                                             "source": "PREVIOUS_RUN_WOULD_APPLY"}},
                broker_holdings=broker_holdings, broker_cash=broker_cash, fills=fills, fill_errors=fill_errors,
                day_trade_results=day_results, rows=rows, slots=slots, slot_errors=slot_errors,
                open_order_count=open_order_count, now=now(), table=table, carried=carried)
            compare = {"explained": check["I2"]["status"] == "PASS" and check["I3"]["status"] == "PASS",
                       "reasons": check["I2"]["reasons"] + check["I3"]["reasons"]}

    failed = [name for name in AUTO_CORE_INVARIANTS if invariants[name]["status"] != "PASS"]
    reasons += [f"{name}:{reason}" for name in failed for reason in invariants[name]["reasons"]]
    reasons += evidence_reasons
    if proposal["status"] == "BLOCKED":
        reasons += [f"PROPOSAL_BLOCKED:{code}" for code in proposal["unresolved_fields"]]
    recordable = not reasons
    if kill_switch:
        reasons.append("KILL_SWITCH_ON")
    would_apply = would_apply_block(proposal, state) if recordable else None
    applied = None
    if recordable and not kill_switch and mode == "apply" and proposal["status"] == "USER_CONFIRMATION_REQUIRED":
        # I5: the state is hashed again just before the write; apply_auto_core re-checks it too.
        if file_hash(state_path) != before:
            raise AutoReconcileError("PORTFOLIO_STATE_MUTATION_DETECTED")
        audit = apply_auto_core(
            state_path=state_path, proposal=proposal, invariants=invariants,
            provenance={**provenance, "mode": "apply"},
            audit_path=output_directory / f"apply_audit.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json",
            config_path=config_path, provenance_source=provenance_source)
        applied = {**would_apply, "state_revision_before": audit["state_revision_before"],
                   "state_revision_after": audit["state_revision_after"],
                   "portfolio_hash_after": audit["portfolio_hash_after"]}
    elif file_hash(state_path) != before:
        raise AutoReconcileError("PORTFOLIO_STATE_MUTATION_DETECTED")
    status = "HOLD" if reasons else "OK"
    return {
        "schema_version": RESULT_SCHEMA_VERSION, "generated_at": generated_at, "mode": mode,
        "status": status, "reasons": reasons, "kill_switch": kill_switch,
        # Never a reason to hold: shown so a record with warnings reaches the 06:40 check (T1 r3 C3).
        "warnings": proposal_warnings(proposal),
        "fill_window": {"days": len(plan["fill_dates"]), "maximum_days": FILL_WINDOW_MAXIMUM_DAYS},
        "invariants": invariants,
        "cash_flow_evidence": {
            "status": "HOLD" if evidence_reasons else "OK", "reasons": evidence_reasons,
            "period_from": plan["evidence_from"].isoformat(), "period_to": plan["today"].isoformat(),
            "evidence_path": _repo_relative(evidence_path) if evidence_path else None,
            "declaration_status": (declaration or {}).get("declaration_status"),
            "hwm_adjustment_usd": (declaration or {}).get("hwm_adjustment_usd")},
        "proposal": {"proposal_id": proposal["proposal_id"], "status": proposal["status"],
                     "change_kind": proposal["change_kind"], "warnings": proposal["warnings"],
                     "path": _repo_relative(output_directory / "reconciliation_proposal.json")},
        "would_apply": would_apply, "applied": applied,
        "holdings_change": explained["holdings_change"], "fills": explained["fills"],
        "compare_check": compare, "state_revision": state.get("state_revision"),
        "account_identifier_stored": False, "inferred_fills": False, "order_authority": False,
        "quantity_authority": "none", "execution_quantity": None,
    }


# ---------------------------------------------------------------------------------------------
# Configuration and run provenance (F6: commit SHA + dirty paths replace the acceptance pin)
# ---------------------------------------------------------------------------------------------

CONFIG_PATH = REPO_ROOT / "workspace/policies/auto_core.json"
CONFIG_SCHEMA = SKILL_ROOT / "schemas/auto-core-config.schema.json"
PIN_SCOPE_PATH = SKILL_ROOT / "assets/kiwoom-acceptance-pin-scope.json"
# The auto-core's own code joins the former pin list in the guarded set.
AUTO_CORE_GUARDED_PATHS = (
    "manage-us-stock-strategy/scripts/auto_core.py",
    "manage-us-stock-strategy/scripts/auto_core_reconcile.py",
    "manage-us-stock-strategy/scripts/collect_30m.ps1",
    "manage-us-stock-strategy/scripts/run_auto_core.ps1",
    "manage-us-stock-strategy/schemas/auto-core-config.schema.json",
    "manage-us-stock-strategy/schemas/auto-core-result.schema.json",
)
# T1 r3 C2: every tracked file under these folders is guarded too (the apply path imports and reads them:
# validation_common.py, evaluate_alerts.py, portfolio_exposure.py, schemas, assets, ...).
GUARDED_PREFIXES = ("manage-us-stock-strategy/scripts/", "manage-us-stock-strategy/schemas/",
                    "manage-us-stock-strategy/assets/")
# Generated data, not code: never listed as dirty.
DATA_PREFIXES = ("workspace/outputs/", "workspace/private_inputs/")
DIRTY_LIST_LIMIT = 200


def load_config(path: Path = CONFIG_PATH) -> tuple[dict[str, Any] | None, list[str]]:
    """(config, reasons). A missing file is not an error here; the caller decides (no write without it)."""
    path = Path(path)
    if not path.is_file():
        return None, ["AUTO_CORE_CONFIG_MISSING"]
    try:
        config = load_json(path)
    except (OSError, ValueError):
        return None, ["AUTO_CORE_CONFIG_UNREADABLE"]
    errors = validate_instance(config, CONFIG_SCHEMA)
    if errors:
        return None, ["AUTO_CORE_CONFIG_INVALID:" + ";".join(errors[:3])]
    return config, []


def guarded_paths(pin_scope_path: Path = PIN_SCOPE_PATH) -> list[str]:
    """Former Kiwoom acceptance pin list (kept, status RETIRED) plus the auto-core's own files.

    git_provenance also guards every tracked file under GUARDED_PREFIXES; this list keeps the pinned files
    outside them (three boundary tests) guarded as well.
    """
    try:
        pinned = list(load_json(pin_scope_path).get("required_implementation_paths") or [])
    except (OSError, ValueError, AttributeError):
        pinned = []
    return sorted(set(pinned) | set(AUTO_CORE_GUARDED_PATHS) | {
        Path(pin_scope_path).resolve().relative_to(REPO_ROOT).as_posix()
        if Path(pin_scope_path).resolve().is_relative_to(REPO_ROOT) else str(pin_scope_path)})


def git_provenance(repo: Path = REPO_ROOT, *, guarded: list[str] | None = None,
                   runner: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Commit SHA and dirty paths of the code that runs; never raises.

    guarded_dirty_paths: every tracked file under GUARDED_PREFIXES with an uncommitted change (modified,
    staged, deleted or renamed; both names of a rename), plus any dirty path in `guarded` (tracked or not).
    """
    import subprocess

    run = runner or subprocess.run
    guarded = guarded if guarded is not None else guarded_paths()
    try:
        head = run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                   encoding="utf-8", check=False, timeout=30)
        status = run(["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                     capture_output=True, text=True, encoding="utf-8", check=False, timeout=60)
    except (OSError, ValueError) as exc:
        return {"status": "UNAVAILABLE", "reason": type(exc).__name__, "commit_sha": None,
                "dirty_paths": [], "guarded_dirty_paths": []}
    commit = (head.stdout or "").strip().lower()
    if head.returncode != 0 or status.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        return {"status": "UNAVAILABLE", "reason": "GIT_COMMAND_FAILED", "commit_sha": None,
                "dirty_paths": [], "guarded_dirty_paths": []}
    paths: list[str] = []
    tracked: set[str] = set()
    entries = (status.stdout or "").split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:].replace("\\", "/")
        names = [path]
        if "R" in code or "C" in code:
            # The source path of a rename or copy follows.
            if index < len(entries) and entries[index]:
                names.append(entries[index].replace("\\", "/"))
            index += 1
        paths.append(path)
        if code != "??":
            tracked.update(names)
    dirty = sorted({path for path in paths if not path.startswith(DATA_PREFIXES)})
    guarded_set = set(guarded)
    guarded_dirty = {path for path in dirty if path in guarded_set} | {
        path for path in tracked if path.startswith(GUARDED_PREFIXES)}
    return {"status": "OK", "commit_sha": commit, "dirty_paths": dirty[:DIRTY_LIST_LIMIT],
            "dirty_count": len(dirty), "guarded_dirty_paths": sorted(guarded_dirty)}


def apply_guard_reasons(mode: str, provenance: dict[str, Any]) -> list[str]:
    """F6 (widened by T1 r3 C2): in apply mode, unknown provenance or an uncommitted guarded file is a FAIL
    before any read (nothing written); apply_auto_core repeats it just before the write (C1)."""
    if mode != "apply":
        return []
    if provenance.get("status") != "OK" or not provenance.get("commit_sha"):
        return ["GIT_PROVENANCE_UNAVAILABLE"]
    if provenance.get("guarded_dirty_paths"):
        return ["GUARDED_FILES_UNCOMMITTED:" + ",".join(provenance["guarded_dirty_paths"])]
    return []


def _repo_relative(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()
