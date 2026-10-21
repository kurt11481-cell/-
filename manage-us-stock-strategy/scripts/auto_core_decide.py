#!/usr/bin/env python3
"""Redesign T2 F8: the second auto-core run, `decide` (Tuesday-Saturday 07:45 KST, after T1 `daily` at 06:15).

 1 configuration, kill switch (HOLD), decision_mode, git provenance, Kiwoom profile alias (none = FAIL before
   any read; apply mode with an uncommitted guarded file = FAIL, as T1 C2/C6)
 2 the same KST day's T1 result.json; missing or FAIL = HOLD (no ticket)
 3 inputs: 30-minute pages, close histories, corporate actions, calendar, card registry (F2), research record
   (F3; when today's is missing it is looked for every 5 minutes until 08:30 KST, then the run goes on without
   it: buys blocked), watchlist, alert policy, previous decision.json. The S7 review is run again with the
   research record's earnings and the buy-target proposals (read-only output under <day>/s7/).
 4 F6 outcome classification (read-only ust21150 order fills and ust21050 open orders only) of the tickets left
   unclassified by the latest record whose F6 ran (f6_ran); a record that ends before F6 or fails carries that
   record's ledger and tickets (carried_from) and commits nothing. A ticket is classified only after its
   session ended, from the rows of its issue KST day to the KST day of its session's close (r3 R3-1, R3-2).
   An order row counts for one ticket only: rows already attributed to a ticket (attributed_orders, kept in the
   recording-mode ledger) are left out, and issue-day rows placed before the ticket was issued too (r4 R4-1).
   A run whose evaluation session is that record's (no new session, e.g. a U.S. holiday) judges nothing new:
   OK, no ticket, no journal entry, no push, ledger and tickets carried, compare streak kept (r3 R3-3)
 5 F1 judgments  6 F4 requirements and gates  7 F5 tickets  8 F9 compare  9 alert candidates
10 F7 journal (recording mode only)  11 decision.json + LATEST_DECISION.json (T1 files are not touched)
No retry inside a run; the same day twice gives the same result (recording mode: a decision of the same run
day already in the journal is not written again; a different one is kept only as decision.rerun-<time>.json,
HOLD).
Exit code 0 = OK/HOLD, 1 = FAIL.
No order path exists here: tickets are for the user to enter; order_authority stays false.
"""

from __future__ import annotations

import copy
import json
import math
import time as time_module
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import auto_core_compare as compare_module
import auto_core_inputs as inputs
import auto_core_reconcile as core
import auto_core_rules as rules
import auto_core_tickets as tickets_module
from auto_core_bars import load_symbol
from kiwoom_broker_shadow import order_available_cash_errors
from reconcile_broker_state import AUTO_OUTPUT_ROOT, AUTO_RESULT_FILE, DAY_FOLDER, kst_day
from validation_common import canonical_hash, load_json, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
DECISION_SCHEMA = SKILL_ROOT / "schemas/auto-core-decision.schema.json"
DECISION_FILE = "decision.json"
LATEST_DECISION_FILE = "LATEST_DECISION.json"
COMPARE_FILE = "compare.json"
RERUN_PREFIX = "decision.rerun-"
S7_FOLDER = "s7"
SCHEMA_VERSION = "auto-core-decision-1.0"
CLOSES_ROOT = REPO_ROOT / "workspace/outputs/regular-session-closes"
DOCS_DIR = REPO_ROOT / "docs/claude"
RECOVERY_GATE_DOC = DOCS_DIR / "recovery-gate-R-REC1-2026-10-09.md"
KST = ZoneInfo("Asia/Seoul")
RESEARCH_WAIT_UNTIL = time(8, 30)
RESEARCH_POLL_SECONDS = 300
T1_RESULT_FILE = "result.json"
SNAPSHOT_FILE = "kiwoom_broker_snapshot.shadow.json"
CASH_TOLERANCE = Decimal("1.00")
# t2-equity-cash (user 2026-10-13): the snapshot cash values behind the total equity and its basis labels.
EQUITY_CASH_FIELDS = ("order_available_cash", "withdrawable_cash", "foreign_currency_deposit")
EQUITY_CASH_ORDER_AVAILABLE = "ORDER_AVAILABLE"
EQUITY_CASH_FALLBACK = "MIN_FALLBACK"
EQUITY_CASH_UNAVAILABLE = "CASH_UNAVAILABLE"
POLICY_PATHS = {
    "readonly": REPO_ROOT / "workspace/policies/kiwoom-readonly-policy.json",
    "rate": REPO_ROOT / "workspace/policies/kiwoom-rate-limit-policy.json",
    "alert": REPO_ROOT / "stock-strategy-system/alert_policy.json",
    "state": REPO_ROOT / "stock-strategy-system/portfolio_state.json",
    "journal": REPO_ROOT / "stock-strategy-system/decision_journal.json",
}
NOT_FOR_ENTRY = "\ube44\uad50 \uc911(\uc785\ub825 \ub300\uc0c1 \uc544\ub2d8)"  # "\ube44\uad50 \uc911(\uc785\ub825 \ub300\uc0c1 \uc544\ub2d8)"


class DecideFailure(RuntimeError):
    """The first failure of a decide run (status FAIL, exit 1)."""


def _decimal(value: Any) -> Decimal | None:
    return core._decimal(value)


def _file_record(path: Path | None, *, fresh: Any = None) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return {"path": core._repo_relative(path) if path else None, "sha256": None, "fresh": fresh}
    import hashlib
    return {"path": core._repo_relative(Path(path)), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "fresh": fresh}


def previous_decisions(output_root: Path, day: str) -> list[tuple[str, dict[str, Any] | None]]:
    """[(run day, decision or None if unreadable)] for every earlier decision.json, oldest first."""
    found = []
    for path in sorted(Path(output_root).glob(f"*/{DECISION_FILE}")):
        if not DAY_FOLDER.fullmatch(path.parent.name) or path.parent.name >= day:
            continue
        try:
            found.append((path.parent.name, load_json(path)))
        except (OSError, ValueError):
            found.append((path.parent.name, None))
    return found


def ledger_carry(previous_all: list[tuple[str, dict[str, Any] | None]]) -> dict[str, Any]:
    """The re-issue ledger and the unclassified tickets to start from (r2 R2-2): those of the most recent record
    whose F6 classification ran and stood (f6_ran true), however many records came after it. Its unclassified
    tickets are its open_tickets plus the tickets it issued. An unreadable record after it may have been such a
    record: unreadable_after makes G0 fail (fail closed). Its evaluation session decides r3 R3-3 (no new session).
    Its attributed_orders (r4 R4-1) come with the keys."""
    unreadable_after = False
    for run_day, item in reversed(previous_all):
        if item is None:
            unreadable_after = True
            continue
        if item.get("f6_ran") is True:
            pending = [dict(ticket) for ticket in item.get("open_tickets") or []]
            for ticket in item.get("tickets") or []:
                if not any(other["ticket_id"] == ticket["ticket_id"] for other in pending):
                    pending.append({**ticket, "issued_day": item["run_day_kst"]})
            return {"keys": dict(item.get("keys") or {}), "open_tickets": pending, "carried_from": run_day,
                    "attributed_orders": [dict(entry) for entry in item.get("attributed_orders") or []],
                    "unreadable_after": unreadable_after, "evaluation_session": item.get("evaluation_session"),
                    "source": item}
    return {"keys": {}, "open_tickets": [], "carried_from": None, "attributed_orders": [],
            "unreadable_after": unreadable_after, "evaluation_session": None, "source": None}


# ---------------------------------------------------------------------------------------------
# The cash of the total equity (t2-equity-cash)
# ---------------------------------------------------------------------------------------------

def equity_cash(cash: dict[str, Any] | None, holdings: list[dict[str, Any]] | None) -> tuple[Decimal | None, str]:
    """(USD cash, basis) of the total equity behind the rule-file N and the V6 account line (t2-equity-cash,
    user 2026-10-13), from the broker snapshot's three cash values only (no amount is estimated from prices).

    The approved cash, Kiwoom order-available (fc_ord_alowa, T1 F1), when T1's one cash check
    (kiwoom_broker_shadow.order_available_cash_errors on the snapshot's (settled_quantity, held_quantity) rows)
    passes: ORDER_AVAILABLE. A failed check, or a missing order-available or withdrawable value: the smallest known
    of the three, MIN_FALLBACK:<reason> - the settled deposit before a sale settles, order-available before a buy
    settles, so the total is never raised (cautious for buys). None of the three: (None, CASH_UNAVAILABLE) and the
    rule-file N stays unknown. The buy cash and G1 keep order-available as they are."""
    values = {field: _decimal((cash or {}).get(field)) for field in EQUITY_CASH_FIELDS}
    known = [value for value in values.values() if value is not None]
    if not known:
        return None, EQUITY_CASH_UNAVAILABLE
    missing = [field for field in EQUITY_CASH_FIELDS[:2] if values[field] is None]
    if missing:
        return min(known), f"{EQUITY_CASH_FALLBACK}:CASH_VALUE_MISSING:" + ",".join(missing)
    quantities = [(_decimal(row.get("settled_quantity")), _decimal(row.get("held_quantity")))
                  for row in holdings or [] if isinstance(row, dict)]
    errors = order_available_cash_errors(values["order_available_cash"], values["withdrawable_cash"], quantities)
    if errors:
        return min(known), f"{EQUITY_CASH_FALLBACK}:{errors[0]}"
    return values["order_available_cash"], EQUITY_CASH_ORDER_AVAILABLE


def snapshot_holdings(snapshot: dict[str, Any] | None) -> dict[str, int]:
    """{ticker: held quantity > 0} of a broker snapshot (F1's holdings)."""
    holdings: dict[str, int] = {}
    for item in (snapshot or {}).get("holdings") or []:
        quantity = item.get("held_quantity")
        if isinstance(quantity, (int, float)) and not isinstance(quantity, bool) and quantity > 0:
            holdings[str(item["ticker"]).upper()] = int(quantity)
    return holdings


# ---------------------------------------------------------------------------------------------
# Broker reads (F6 only: daily order fills and open orders)
# ---------------------------------------------------------------------------------------------

def read_outcomes(pending: list[dict[str, Any]], *, reader: Callable[..., list[dict[str, Any]]], runtime: Path,
                  rate_policy: dict[str, Any], run_day: str, reconcile_fills: list[dict[str, Any]] | None,
                  evaluation_session: str, calendar: dict[str, Any],
                  attributed_orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify the pending tickets whose session has ended (r3 R3-1: ticket session <= the evaluation session)
    from the broker's order rows of their order days (r3 R3-2: the issue KST day to the KST day of the session's
    close, tickets_module.order_days); read open orders (G0). A ticket before the end of its session stays open
    (G0_TICKET_SESSION_NOT_YET: no read, no classification, no ledger change); a failed read or an unknown
    order-day window leaves its ticket unclassified (OUTCOME_UNKNOWN).
    r4 R4-1: tickets are classified oldest first, each from tickets_module.ticket_rows: rows of the ledger's
    attributed_orders and rows a ticket classified earlier in this run took are left out, and so are issue-day
    rows placed before the ticket was issued and last-order-day rows placed after the session's close
    (pre-on-fix 1; an unknown close is ORDER_WINDOW_UNKNOWN). attributed = the (ord_dt, ord_no, ticket_id) of the rows taken by
    the outcomes that update the ledger (not those that disagree with T1, r2 R2-7); the caller keeps them only
    in recording mode."""
    windows = {ticket["ticket_id"]: tickets_module.order_days(ticket, calendar) for ticket in pending
               if tickets_module.ticket_session_ended(ticket, evaluation_session)}
    days = sorted({day for window in windows.values() for day in window or []})
    requests = [{"operation": "account_open_items"}] + [
        {"operation": "account_daily_fills_read", "params": {"ord_dt": day.replace("-", "")}} for day in days]
    results = reader(requests, runtime=runtime, policy=rate_policy)
    open_result = next((item for item in results if item.get("operation") == "account_open_items"), None)
    reasons: list[str] = []
    open_count = None
    if open_result is None or not core._read_passed(open_result):
        reasons.append("OPEN_ORDERS_READ_FAILED")
    else:
        open_count = len(open_result.get("data") or [])
    rows_by_day: dict[str, list[dict[str, Any]]] = {}
    failed_days: set[str] = set()
    for day in days:
        match = next((item for item in results if item.get("operation") == "account_daily_fills_read"
                      and (item.get("request_params") or {}).get("ord_dt") == day.replace("-", "")), None)
        if match is None or not core._read_passed(match):
            failed_days.add(day)
        else:
            rows_by_day[day] = [row for row in match.get("data") or [] if isinstance(row, dict)]
    outcomes, still_open, attributed = [], [], []
    taken = {(entry["ord_dt"], entry["ord_no"]) for entry in attributed_orders}
    for ticket in sorted(pending, key=lambda item: (str(item.get("issued_day") or ""), str(item.get("issuedAt") or ""))):
        if ticket["ticket_id"] not in windows:  # r3 R3-1: its session has not ended
            still_open.append(ticket)
            reasons.append(f"G0_TICKET_SESSION_NOT_YET:{ticket['ticket_id']}")
            continue
        needed = windows[ticket["ticket_id"]]
        close_at = tickets_module.session_close(ticket, calendar)
        if needed is None or close_at is None:  # r3 R3-2 / pre-on-fix 1: the order-day window is unknown
            still_open.append(ticket)
            reasons += [f"ORDER_WINDOW_UNKNOWN:{ticket['ticket_id']}", f"OUTCOME_UNKNOWN:{ticket['ticket_id']}"]
            continue
        if any(day in failed_days for day in needed):
            still_open.append(ticket)
            reasons.append(f"OUTCOME_UNKNOWN:{ticket['ticket_id']}")
            continue
        chosen = tickets_module.ticket_rows(ticket, [(day, row) for day in needed for row in rows_by_day.get(day, [])],
                                            taken, close_at=close_at)
        outcome = tickets_module.classify_outcome(ticket, chosen["rows"]) if chosen["note"] is None else None
        if outcome is None or outcome["state"] == "unknown":
            still_open.append(ticket)
            reasons.append(f"OUTCOME_UNKNOWN:{ticket['ticket_id']}")
            continue
        taken.update((order["ord_dt"], order["ord_no"]) for order in chosen["orders"])
        outcome["session"] = ticket["session"]
        outcome["classified_on"] = run_day
        outcome["reconcile_mismatch"] = tickets_module.reconcile_mismatch(outcome, ticket["session"], reconcile_fills)
        if outcome["reconcile_mismatch"]:
            reasons.append(f"OUTCOME_MISMATCH_WITH_RECONCILE:{ticket['ticket_id']}")
        else:
            attributed += [{**order, "ticket_id": ticket["ticket_id"]} for order in chosen["orders"]]
        outcomes.append(outcome)
    return {"outcomes": outcomes, "open_tickets": still_open, "open_orders": open_count, "reasons": reasons,
            "attributed": attributed}


# ---------------------------------------------------------------------------------------------
# S7 review with the research earnings and the buy-target proposals
# ---------------------------------------------------------------------------------------------

def run_s7(output_directory: Path, earnings: dict[str, Any] | None, proposals: list[dict[str, Any]]) -> dict[str, Any]:
    """The S7 review with the research earnings and the buy-target proposals. Inputs and the review file go under
    <day>/s7/ (r2 R2-11), never workspace/outputs/exposure-review, whose latest file the integrated check, cards
    and the status screen read."""
    from run_portfolio_exposure_review import build_parser, run

    folder = Path(output_directory) / S7_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    arguments = ["--output-root", str(folder)]
    if earnings is not None:
        write_json(folder / "s7-earnings.json", {"earnings": earnings})
        arguments += ["--earnings", str(folder / "s7-earnings.json")]
    if proposals:
        write_json(folder / "s7-proposals.json", {"proposals": proposals})
        arguments += ["--proposals", str(folder / "s7-proposals.json")]
    review, target = run(build_parser().parse_args(arguments))
    return {"review": review, "path": core._repo_relative(target)}


def s7_model_factory(policy: dict[str, Any], adjusted_closes: dict[str, dict[str, str]], sessions: list[str],
                     evaluation_session: str) -> Callable[[list[str]], Any]:
    from portfolio_exposure import ExposureModel, exposure_config

    config = exposure_config(policy)
    span = [session for session in sessions if session <= evaluation_session]
    return lambda symbols: ExposureModel(config, adjusted_closes, span, evaluation_session, symbols)


# ---------------------------------------------------------------------------------------------
# Alerts (rule file alerts 1 2 3 4 6 9 10 and 11, repetition against the previous decision)
# ---------------------------------------------------------------------------------------------

def alert_candidates(*, decision: dict[str, Any], previous: dict[str, Any] | None, mode: str,
                     exceptions: list[tuple[str, str]], previous_run_missing: bool) -> tuple[list[dict[str, Any]], dict[str, str]]:
    states: dict[str, str] = {}
    lines: list[tuple[str, str, bool]] = []  # code, line, repeat-suppressed kind
    for symbol, result in decision["symbols"].items():
        held = result["role"] == "held"
        evidence = decision["evidence"].get(symbol, {})
        sell = evidence.get("sell") or {}
        if held and sell.get("basis_met"):
            states[f"1:{symbol}"] = ",".join(sell.get("ids") or [])
            lines.append((f"1:{symbol}", f"{symbol} \ub9e4\ub3c4 \uadfc\uac70 \ucda9\uc871({sell.get('composition')}) \u2014 \ub9e4\ub3c4\ub294 \uc8fc\ubb38\ud45c\ub85c\ub9cc", True))
        for trigger in result["triggers"]:
            if trigger["side"] == "alert" and trigger["state"] == "review":
                states[f"2:{symbol}:{trigger['id']}"] = "review"
                lines.append((f"2:{symbol}:{trigger['id']}", f"{symbol} {trigger['name']}({trigger['id']}) \u2014 \uac80\ud1a0 \uac1c\uc2dc(\uadfc\uac70 \uc544\ub2d8)", True))
            if trigger["id"] in ("C1-", "C2-") and held and trigger["state"] == "hit":
                states[f"9:{symbol}:{trigger['id']}"] = "hit"
                lines.append((f"9:{symbol}:{trigger['id']}", f"\uacfc\uc5f4 \uacbd\ubcf4 {symbol} {trigger['id']} \u2014 \ub9e4\ub3c4 \uadfc\uac70 1/2(\ucc28\uc775 \uc2e4\ud604 \uac80\ud1a0)", True))
            if trigger["id"] in ("C1+", "C2+") and trigger["state"] == "hit" and result.get("buy_approved"):
                states[f"9:{symbol}:{trigger['id']}"] = "hit"
                lines.append((f"9:{symbol}:{trigger['id']}", f"\uacfc\ub9e4\ub3c4 \uacbd\ubcf4 {symbol} {trigger['id']} \u2014 \ub9e4\uc218 \uadfc\uac70 1/2, \ub9e4\uc218 \uc9c0\uc2dc \uc544\ub2d8", True))
        if result.get("nocard"):
            states[f"10:{symbol}"] = "review"
            lines.append((f"10:{symbol}", f"\uce74\ub4dc \uc5c6\uc74c {symbol} \u2014 \uacf5\ud1b5 \uaddc\uce59\ub9cc\uc73c\ub85c \uc810\uac80 \uc911", True))
    account = decision["account"]
    if account.get("state") in ("near", "review"):
        states["2:V6"] = account["state"]
        lines.append(("2:V6", f"\uacc4\uc88c \uc810\uac80\uc120 V6 {account['state']} (\ucd1d\uc790\uc0b0 ${account.get('total')})", True))
    band = ((decision.get("exposure") or {}).get("S7") or {}).get("band")
    if band in ("ABOVE_BAND", "HARD_CEILING"):
        states["2:EXP"] = band
        lines.append(("2:EXP", f"\ub178\ucd9c \ub300\uc5ed {band} (E {decision['exposure']['S7'].get('E')})", True))
    for symbol in decision["exposure"].get("caps") or []:
        states[f"2:CAP:{symbol}"] = "review"
        lines.append((f"2:CAP:{symbol}", f"\uc885\ubaa9 \uc0c1\ud55c \ucd08\uacfc {symbol}(\uac80\ud1a0 \uac1c\uc2dc, \ub9e4\ub3c4 \uadfc\uac70 \uc544\ub2d8)", True))
    for item in decision["exposure"].get("peaks") or []:
        if item["state"] in ("near", "review"):
            states[f"2:R5:{item['symbol']}"] = item["state"]
            lines.append((f"2:R5:{item['symbol']}", f"\uace0\uc810 \u221230% {item['symbol']} {item['state']}", True))
    shock = decision.get("shock") or {}
    states["2:RREC"] = "open" if shock.get("open") else "closed" if shock.get("open") is False else "unk"
    if previous is not None and ((previous.get("alert_states") or {}).get("2:RREC") or states["2:RREC"]) != states["2:RREC"]:
        opened_text = "\uc5f4\ub9bc" if shock.get("open") else "\ub2eb\ud798"
        lines.append(("2:RREC", f"R-REC1 \uc774\ubca4\ud2b8 {opened_text}", True))
    # ev-rg1-hyper C-2: uncleared official thesis damage (portfolio or a candidate) blocks buys until a card is
    # accepted again; the state is "<fact ids>|<blocked symbols>" and only exists while such a fact does.
    by_symbol = shock.get("by_symbol") or {}
    damage_ids = sorted(set(shock.get("rg1_damage") or []) | {fact_id for item in by_symbol.values()
                                                              for fact_id in item.get("rg1_damage") or []})
    damage_blocked = sorted(symbol for symbol, item in by_symbol.items() if item.get("rg1_damage"))
    if damage_ids:
        states["2:RG1DMG"] = ",".join(damage_ids) + "|" + ",".join(damage_blocked)
    for row in decision["buy_requirements"]:
        if row["c"][2]["s"] == "ok" and decision["symbols"].get(row["code"], {}).get("buy_approved"):
            states[f"4:{row['code']}"] = "ok"
            kind_text = "\ucd94\uac00" if row["add"] else "\uc2e0\uaddc"
            lines.append((f"4:{row['code']}", f"\ub9e4\uc218 \uadfc\uac70 \ud6c4\ubcf4 \ucda9\uc871({kind_text}) {row['code']} \u2014 \ub9e4\uc218 \uc9c0\uc2dc \uc544\ub2d8", True))
    for symbol, record in (decision.get("earnings_calendar") or {}).items():
        if record.get("status") == "VERIFIED":
            states[f"6:{symbol}"] = str(record.get("announcement_session"))
            lines.append((f"6:{symbol}", f"\uc2e4\uc801\uc77c \uacf5\uc9c0 {symbol} {record.get('announcement_session')}", True))
    if previous_run_missing:
        lines.append(("11", "\uc9c1\uc804 decide \uc2e4\ud589 \ub204\ub77d", False))
    if decision.get("t1_mismatch"):
        lines.append(("3", "\uc794\uace0 \ubd88\uc77c\uce58\u00b7\ubbf8\uccb4\uacb0 \u2014 " + decision["t1_mismatch"], False))
    previous_states = (previous or {}).get("alert_states") or {}
    alerts = []
    for code, line, suppressible in lines:
        changed = previous is None or previous_states.get(code) != states.get(code)
        if suppressible and not changed:
            continue
        suffix = " (\uc9c1\uc804 \uae30\ub85d \uc5c6\uc74c)" if previous is None else ""
        alerts.append({"code": code, "line": line + suffix, "push": mode == "apply"})
    for code, line in exceptions:
        alerts.append({"code": code, "line": line, "push": True})
    # ev-rg1-hyper C-2: an exception (push in every mode) on the day the facts or the blocked symbols first appear or
    # change; no symbol code or fact id in the line (they are in buy requirement (5) and rg1_damage).
    if damage_ids and previous_states.get("2:RG1DMG") != states["2:RG1DMG"]:
        alerts.append({"code": "2:RG1DMG", "push": True,
                       "line": f"R-REC1 RG1 \uacf5\uc2dd \ud14c\uc81c \ud6fc\uc190 {len(damage_ids)}\uac74 \u2014 "
                               f"\uce74\ub4dc \uc7ac\uc218\ub77d \uc804 \ub9e4\uc218 \ub9c9\ud798 {len(damage_blocked)}\uc885\ubaa9"
                               "(\ub300\uc2dc\ubcf4\ub4dc \ub9e4\uc218 \uc694\uac74 \u2464)"})
    if mode == "apply":
        for ticket in decision["tickets"]:
            price_text = "\ub9e4\ub3c4 \ud558\ud55c" if ticket["side"] == "sell" else "\ub9e4\uc218 \uc0c1\ud55c"
            share = tickets_module.risk_1r_share_text(ticket.get("risk_1r")) if ticket["side"] == "buy" else None
            alerts.append({"code": f"TICKET:{ticket['ticket_id']}", "push": True,
                           "line": f"\uc8fc\ubb38\ud45c {ticket['ticker']} {ticket['qty']}\uc8fc LOC {price_text} ${ticket['price']}"
                           + ("" if share is None else f" \u00b7 1R \uc790\uc0b0 {share}%")})
    return alerts, states


# ---------------------------------------------------------------------------------------------
# The decide run
# ---------------------------------------------------------------------------------------------

def decide(*, output_root: Path = AUTO_OUTPUT_ROOT, config_path: Path = core.CONFIG_PATH, now: datetime | None = None,
           clock: Callable[[], datetime] | None = None, sleeper: Callable[[float], None] = time_module.sleep,
           reader: Callable[..., list[dict[str, Any]]] | None = None,
           exposure_runner: Callable[[Path, dict[str, Any] | None, list[dict[str, Any]]], dict[str, Any]] = run_s7,
           provenance: dict[str, Any] | None = None, provenance_source: Callable[[], dict[str, Any]] | None = None,
           policy_paths: dict[str, Path] | None = None, closes_root: Path = CLOSES_ROOT,
           research_root: Path = inputs.RESEARCH_ROOT, registry_path: Path = inputs.REGISTRY_PATH,
           watchlist_path: Path = inputs.WATCHLIST_PATH, docs_dir: Path = DOCS_DIR,
           explained_path: Path = compare_module.EXPLAINED_PATH, repo: Path = REPO_ROOT,
           registry_committed_check: Callable[[Path, Path], tuple[bool, str | None]] = inputs.registry_committed,
           calendar_loader: Callable[[datetime], dict[str, Any]] | None = None,
           score_runner: Callable[[Path], Any] | None = None,
           bars_loader: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    paths = {**POLICY_PATHS, **(policy_paths or {})}
    clock = clock or (lambda: datetime.now(timezone.utc))
    now = now or clock()
    day = kst_day(now)
    output_directory = Path(output_root) / day
    decision: dict[str, Any] = _empty_decision(day, now)
    exceptions: list[tuple[str, str]] = []
    previous_all = previous_decisions(Path(output_root), day)
    previous = next((item for _day, item in reversed(previous_all) if item is not None), None)
    carry = ledger_carry(previous_all)
    try:
        # 1 configuration, kill switch, provenance, profile alias.
        config, config_reasons = core.load_config(config_path)
        if config is None:
            raise DecideFailure(";".join(config_reasons) or "AUTO_CORE_CONFIG_MISSING")
        mode = config.get("decision_mode", "compare")
        decision.update(mode=config["mode"], decision_mode=mode)
        provenance = provenance if provenance is not None else core.git_provenance(repo)
        decision.update(commit_sha=provenance.get("commit_sha"), dirty_paths=provenance.get("dirty_paths") or [])
        if config["kill_switch"]:
            decision["status"], decision["reasons"] = "HOLD", ["KILL_SWITCH_ON"]
            return _finish(decision, output_root, output_directory, carry)
        guard = core.apply_guard_reasons(mode, provenance)
        if guard:
            raise DecideFailure(guard[0])
        from auto_core import StepFailure, kiwoom_profile
        try:
            kiwoom_profile(paths["readonly"])
        except StepFailure as exc:
            raise DecideFailure(str(exc)) from exc
        # 2 T1 result of the same KST day.
        t1_path = output_directory / T1_RESULT_FILE
        t1 = load_json(t1_path) if t1_path.is_file() else None
        decision["inputs"]["t1_result"] = _file_record(t1_path if t1 else None)
        if t1 is None or t1.get("status") == "FAIL":
            decision["status"] = "HOLD"
            decision["reasons"] = ["T1_RESULT_MISSING" if t1 is None else "T1_NOT_OK"]
            return _finish(decision, output_root, output_directory, carry)
        return _run(decision=decision, config=config, mode=mode, provenance=provenance, t1=t1, paths=paths,
                    output_root=Path(output_root), output_directory=output_directory, day=day, now=now, clock=clock,
                    sleeper=sleeper, reader=reader, exposure_runner=exposure_runner,
                    provenance_source=provenance_source, closes_root=closes_root, research_root=research_root,
                    registry_path=registry_path, watchlist_path=watchlist_path, docs_dir=docs_dir,
                    explained_path=explained_path, repo=repo, registry_committed_check=registry_committed_check,
                    calendar_loader=calendar_loader, score_runner=score_runner, bars_loader=bars_loader,
                    previous=previous, carry=carry,
                    previous_all=previous_all, config_path=config_path, exceptions=exceptions)
    except DecideFailure as exc:
        decision["status"] = "FAIL"
        decision["reasons"].append(str(exc))
    except Exception as exc:  # noqa: BLE001 - a scheduled run must always leave a FAIL record
        decision["status"] = "FAIL"
        decision["reasons"].append(f"UNEXPECTED_ERROR:{type(exc).__name__}:{str(exc)[:200]}")
    return _finish(decision, output_root, output_directory, carry)


def _empty_decision(day: str, now: datetime) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "run_day_kst": day, "generated_at": now.isoformat(),
        "evaluation_session": None, "buy_session": None, "status": "OK", "reasons": [], "mode": "compare",
        "decision_mode": "compare", "commit_sha": None, "dirty_paths": [], "inputs": {}, "symbols": {},
        "evidence": {}, "buy_requirements": [], "exposure": {}, "shock": {}, "account": {}, "earnings_calendar": {},
        "tickets": [], "no_action": {"value": True, "reasons": []}, "outcomes": [], "open_tickets": [],
        "keys": {}, "attributed_orders": [], "f6_ran": False, "carried_from": None, "no_new_session": False,
        "facts_seen": [],
        "journal": {"would_append": [], "appended": []}, "compare": {"status": compare_module.NOT_COMPARED},
        "alerts": [], "alert_states": {}, "dashboard": {"runCore": {}, "orders": []}, "candidates": [],
        "blocked": [], "next_action_for_user": None, "next_action_for_cowork": None,
        "order_authority": False, "execution_quantity": None,
    }


def _wait_for_research(research_root: Path, day: str, clock: Callable[[], datetime],
                       sleeper: Callable[[float], None]) -> dict[str, Any]:
    started = clock()
    waited = 0
    while not inputs.research_record_exists(research_root, day):
        current = clock().astimezone(KST)
        if current.time() >= RESEARCH_WAIT_UNTIL or current.date().isoformat() != day:
            break
        sleeper(RESEARCH_POLL_SECONDS)
        waited += RESEARCH_POLL_SECONDS
    return {"found": inputs.research_record_exists(research_root, day), "waited_seconds": waited,
            "started_at": started.isoformat(), "until_kst": RESEARCH_WAIT_UNTIL.strftime("%H:%M")}


def _calendar(now: datetime) -> dict[str, Any]:
    from regular_session_close_history import calendar_from_snapshot, load_production_snapshot

    snapshot, failure = load_production_snapshot(now)
    if snapshot is None:
        raise DecideFailure(f"SESSION_CALENDAR_UNAVAILABLE:{failure}")
    return calendar_from_snapshot(snapshot)


def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provenance: dict[str, Any], t1: dict[str, Any],
         paths: dict[str, Path], output_root: Path, output_directory: Path, day: str, now: datetime,
         clock: Callable[[], datetime], sleeper: Callable[[float], None], reader: Any, exposure_runner: Any,
         provenance_source: Any, closes_root: Path, research_root: Path, registry_path: Path, watchlist_path: Path,
         docs_dir: Path, explained_path: Path, repo: Path, registry_committed_check: Any, calendar_loader: Any,
         score_runner: Any, bars_loader: Any, previous: dict[str, Any] | None, carry: dict[str, Any],
         previous_all: list[tuple[str, Any]], config_path: Path,
         exceptions: list[tuple[str, str]]) -> dict[str, Any]:
    from run_portfolio_exposure_review import expected_completed_session, load_corporate_actions

    calendar = (calendar_loader or _calendar)(now)
    sessions = sorted(calendar["sessions"])
    evaluation_session = expected_completed_session(calendar, now)
    if evaluation_session is None:
        raise DecideFailure("NO_COMPLETED_SESSION")
    later = [session for session in sessions if session > evaluation_session]
    earlier = [session for session in sessions if session < evaluation_session]
    buy_session = later[0] if later else None
    previous_session = earlier[-1] if earlier else None
    decision.update(evaluation_session=evaluation_session, buy_session=buy_session)
    # r3 R3-3: no session closed since the ledger source (a U.S. holiday before this run): nothing new to judge.
    # It comes before R2-5, which is only for a rerun of the same run day.
    if carry["carried_from"] is not None and not carry["unreadable_after"] \
            and carry["evaluation_session"] == evaluation_session:
        return _no_new_session(decision=decision, carry=carry, previous=previous, previous_all=previous_all,
                               config=config, mode=mode, calendar=calendar, explained_path=explained_path,
                               output_root=output_root, output_directory=output_directory, day=day)
    journal_path = paths["journal"]
    from portfolio_review_journal import load_journal
    journal_start = load_journal(journal_path)
    # Broker snapshot and reconciliation of T1 (no new broker reconciliation here).
    snapshot_path = output_directory / SNAPSHOT_FILE
    snapshot = load_json(snapshot_path) if snapshot_path.is_file() else None
    reconcile_path = output_directory / AUTO_RESULT_FILE
    reconcile = load_json(reconcile_path) if reconcile_path.is_file() else None
    decision["inputs"].update(broker_snapshot=_file_record(snapshot_path if snapshot else None),
                              reconcile=_file_record(reconcile_path if reconcile else None))
    holdings = snapshot_holdings(snapshot)
    cash = None
    if snapshot is not None:
        cash = _decimal((snapshot.get("cash") or {}).get("order_available_cash"))
    # t2-equity-cash: the cash of the total equity (rule-file N, V6); `cash` stays the buy cash and G1's.
    total_cash, cash_basis = equity_cash((snapshot or {}).get("cash"), (snapshot or {}).get("holdings"))
    gate1: list[str] = []
    if reconcile is None or reconcile.get("status") != "OK":
        gate1.append("G1_RECONCILE_NOT_OK")
    if snapshot is None:
        gate1.append("G1_BROKER_SNAPSHOT_MISSING")
    state = load_json(paths["state"])
    state_holdings = {key: value for key, value in (state.get("holdings") or {}).items() if value}
    state_cash = _decimal(state.get("available_cash_usd"))
    if snapshot is not None and (state_holdings != holdings or state_cash is None or cash is None
                                 or abs(state_cash - cash) > CASH_TOLERANCE):
        gate1.append("G1_STATE_NOT_EQUAL_BROKER")
        decision["t1_mismatch"] = "\uc0c1\ud0dc \ud30c\uc77c \u2260 \ube0c\ub85c\ucee4"
    # Registry, watchlist, M6, research record.
    registry = inputs.load_registry(registry_path, repo=repo, committed_check=registry_committed_check)
    watchlist = inputs.load_watchlist(watchlist_path)
    m6_docs = inputs.m6_documents(docs_dir)
    wait = _wait_for_research(research_root, day, clock, sleeper)
    # The R-REC1 window (60 sessions to the evaluation session): damage facts and recorded sessions (r2 R2-4).
    window = [session for session in sessions if session <= evaluation_session][-rules.C["RREC_WINDOW_SESSIONS"]:]
    research = inputs.load_research(root=research_root, run_day=day, calendar_sessions=sessions,
                                    decide_time=clock(), registry=registry, window_start=window[0])
    today_record = research["today"]
    research_ok = today_record["status"] == "OK"
    facts = research["facts"] if research_ok else None
    research_block = None if research_ok else (today_record["reasons"] or [today_record["status"]])[0]
    decision["inputs"].update(
        registry={**_file_record(registry_path), "status": registry["status"], "committed": registry["committed"]},
        research_record={**_file_record(Path(research_root) / day / inputs.RESEARCH_FILE),
                         "status": today_record["status"], "reasons": today_record["reasons"],
                         "dropped": today_record["dropped"], "wait": wait},
        watchlist={**_file_record(watchlist_path), "status": watchlist["status"]},
        state=_file_record(paths["state"]), alert_policy=_file_record(paths["alert"]),
        recovery_gate_doc=_file_record(docs_dir / RECOVERY_GATE_DOC.name),
        previous_decision={"run_day_kst": (previous or {}).get("run_day_kst")},
        calendar={"sha256": calendar["identity"]["calendar_sha256"], "authority": calendar["identity"]["authority_status"]})
    # Symbols: held (broker), watch members, the R-REC1 benchmarks.
    members = sorted(watchlist["members"])
    policy = load_json(paths["alert"])
    multipliers = dict(policy["portfolio_exposure_policy"]["nominal_multipliers"])
    sectors = {symbol: (watchlist["members"].get(symbol) or {}).get("sector")
               or ((registry["entries"].get(symbol) or {}).get("sector")) for symbol in set(holdings) | set(members)}
    benchmarks = {"SOXX"} | {rules.rg2_benchmark(sector) for sector in sectors.values()}
    universe = sorted(set(holdings) | set(members) | benchmarks)
    corporate = load_corporate_actions(closes_root, sessions)
    from auto_core import known_exchange
    bars = {}
    for symbol in universe:
        if bars_loader is not None:
            bars[symbol] = bars_loader(symbol, evaluation_session)
            continue
        exchange, _last = known_exchange(symbol, closes_root)
        bars[symbol] = load_symbol(symbol, pages_root=Path(closes_root) / "pages", calendar=calendar,
                                   corporate_actions=corporate, evaluation_session=evaluation_session,
                                   exchange=exchange or "NASDAQ")
        for suspect in bars[symbol]["split_suspects"]:
            exceptions.append(("SPLIT_SUSPECTED", f"\ubd84\ud560 \uc758\uc2ec {suspect} \u2014 \uacf5\uc2dd \ubd84\ud560 \uae30\ub85d \ud544\uc694"))
    # F6 outcome classification of the unclassified tickets of the ledger source (r2 R2-2: the latest record
    # whose F6 ran, however many HOLD/FAIL records came after it). r3: only tickets whose session has ended, each
    # read over its own order days (issue KST day to the KST day of its session's close).
    pending = [dict(ticket) for ticket in carry["open_tickets"]]
    gate0: list[str] = []
    readonly = load_json(paths["readonly"])
    if reader is None:
        from kiwoom_account_readonly_bridge import invoke_account_bridge_batch as reader
    outcome_block = read_outcomes(pending, reader=reader, runtime=Path(str(readonly["official_runtime_path"])).resolve(),
                                  rate_policy=load_json(paths["rate"]), run_day=day,
                                  reconcile_fills=(reconcile or {}).get("fills") if reconcile else None,
                                  evaluation_session=evaluation_session, calendar=calendar,
                                  attributed_orders=carry["attributed_orders"])
    decision.update(outcomes=outcome_block["outcomes"], open_tickets=outcome_block["open_tickets"])
    gate0 += outcome_block["reasons"]
    if outcome_block["open_orders"]:
        gate0.append(f"G0_OPEN_ORDERS:{outcome_block['open_orders']}")
    if any(reason.startswith("OUTCOME_MISMATCH_WITH_RECONCILE") for reason in outcome_block["reasons"]):
        # The broker-classified outcome and T1's explained fills disagree: not journaled, no new ticket today.
        exceptions.append(("OUTCOME_MISMATCH_WITH_RECONCILE",
                           "\uc8fc\ubb38\ud45c \uacb0\uacfc\uc640 T1 \uccb4\uacb0 \ub300\uc870\uac00 \ub2e4\ub984 \u2014 Cowork \ud655\uc778"))
    if any(reason.startswith(("OUTCOME_UNKNOWN", "OPEN_ORDERS_READ")) for reason in outcome_block["reasons"]):
        exceptions.append(("OUTCOME_UNKNOWN", "\uc8fc\ubb38\ud45c \uacb0\uacfc \ubd84\ub958 \uc2e4\ud328 \u2014 \uc624\ub298 \uc0c8 \uc8fc\ubb38\ud45c \uc5c6\uc74c"))
    if any(reason.startswith("G0_TICKET_SESSION_NOT_YET:") for reason in outcome_block["reasons"]):
        # pre-on-fix 6 (judge2 G 6): a carried ticket whose session is after the evaluation session on a new-session
        # day is an anomaly; gate0 keeps the HOLD and this pushes it.
        exceptions.append(("G0_TICKET_SESSION_NOT_YET",
                           "\uc8fc\ubb38\ud45c \uc138\uc158 \uc774\uc804 \uc0c1\ud0dc \u2014 \uc0c8 \uc8fc\ubb38\ud45c \uc5c6\uc74c, Cowork \ud655\uc778"))
    if carry["unreadable_after"]:
        gate0.append("G0_PREVIOUS_DECISION_UNREADABLE")
    keys = dict(carry["keys"])
    attributed = [dict(entry) for entry in carry["attributed_orders"]]
    if mode == "apply":
        # r2 R2-7: an outcome that disagrees with T1's explained fills neither closes nor reopens its key.
        keys = tickets_module.update_keys(keys, [outcome for outcome in outcome_block["outcomes"]
                                                 if not outcome.get("reconcile_mismatch")])
        # r4 R4-1: the rows today's outcomes took join the ledger (compare mode keeps the source's list).
        attributed = tickets_module.attribute_orders(attributed, outcome_block["attributed"], day)
    decision.update(keys=keys, attributed_orders=attributed, f6_ran=True)
    # F1-F5 for the evaluation session (auto_core_replay runs the same function).
    recovery_text = (docs_dir / RECOVERY_GATE_DOC.name).read_text(encoding="utf-8") \
        if (docs_dir / RECOVERY_GATE_DOC.name).is_file() else ""
    seen: set[str] = set()
    for _day, item in previous_all:
        seen.update((item or {}).get("facts_seen") or [])
    checks ={symbol: inputs.card_check(symbol, registry, watchlist, repo=repo, held=symbol in holdings)
              for symbol in sorted(set(holdings) | set(members))}
    for check in checks.values():
        for reason in check["reasons"]:
            if reason in ("CARD_SECTION_CHANGED", "REGISTRY_UNCOMMITTED") and not any(
                    reason in (item or {}).get("registry_flags", []) for _day, item in previous_all[-1:]):
                exceptions.append((reason, f"{reason} {check['symbol']} \u2014 Cowork \ub4f1\ub85d\ubd80 \ud655\uc778"))
    decision["registry_flags"] = sorted({reason for check in checks.values() for reason in check["reasons"]
                                         if reason in ("CARD_SECTION_CHANGED", "REGISTRY_UNCOMMITTED")})
    earnings = today_record["earnings"] if research_ok else None

    def s7_runner(proposals: list[dict[str, Any]]) -> dict[str, Any]:
        run = exposure_runner(output_directory, earnings, proposals)
        decision["inputs"]["s7_review"] = {"path": run.get("path"), "review_id": run["review"].get("review_id"),
                                           "evaluation_session": run["review"].get("evaluation_session")}
        return run["review"]

    session = evaluate_session(
        day=day, mode=mode, issued_at=now.astimezone(KST).strftime("%Y-%m-%d %H:%M KST"), calendar=calendar,
        evaluation_session=evaluation_session, bars=bars, holdings=holdings, cash=cash, deposit=total_cash,
        sectors=sectors, members=members, checks=checks, watchlist=watchlist, m6_docs=m6_docs, facts=facts,
        earnings=earnings, ev3=rules.ev3_dates(recovery_text), seen_fact_ids=seen,
        policy=policy, config=config, keys=keys, gate0=gate0, gate1=gate1, s7_runner=s7_runner,
        research={"block": research_block, "sessions": research["sessions"], "damage": research["damage"]},
        input_hashes={"registry": registry.get("sha256"),
                      "research_record": decision["inputs"]["research_record"]["sha256"],
                      "t1_result": decision["inputs"]["t1_result"]["sha256"]},
        hold_range=True)  # close-confirm e: every ticket carries its hold range (priceCalc band, hold)
    gate1 = session["gate1"]
    decision.update(symbols={symbol: _symbol_view(result) for symbol, result in session["symbols"].items()},
                    evidence=session["evidence"], buy_requirements=session["rows"], tickets=session["planned"]["tickets"],
                    candidates=session["planned"]["candidates"], blocked=session["planned"]["blocked"],
                    no_action=session["planned"]["no_action"], account=session["account"],
                    exposure=session["exposure"], shock=session["shock"], earnings_calendar=session["earnings_calendar"],
                    facts_seen=session["facts_seen"])
    decision["exposure"]["cash_basis"] = cash_basis  # t2-equity-cash: display only (not in runCore)
    decision["reasons"] = sorted(set(gate0 + gate1))
    if decision["reasons"]:
        decision["status"] = "HOLD"
    # F9 compare and the streak.
    block = compare_module.compare(decision, today_record.get("integrated_check_run"), registry["entries"], research_ok)
    explained, explained_errors = compare_module.load_explained(explained_path)
    history = [(run_day, compare_module.streak_block(item)) for run_day, item in previous_all] + [(day, block)]
    block.update(streak=compare_module.streak(history, explained), required=int(config.get("decision_compare_days_required") or 5),
                 explained_errors=explained_errors)
    decision["compare"] = block
    if block["streak"] >= block["required"]:
        decision["next_action_for_cowork"] = "\ud310\uc815 \ub300\uc870 5\uc77c \u2014 \uc644\ub8cc \ud310\uc815 \ud544\uc694"
    elif block["unexplained"] and not compare_module.day_passes(day, block["unexplained"], explained):
        decision["next_action_for_cowork"] = f"\ud310\uc815 \ucc28\uc774 {len(block['unexplained'])}\uac74 \u2014 \uc124\uba85 \uae30\ub85d \ud544\uc694"
    compare_document = {"schema_version": compare_module.COMPARE_SCHEMA_VERSION, "run_day_kst": day,
                        "evaluation_session": evaluation_session, **block}
    compare_errors = validate_instance(compare_document, compare_module.COMPARE_SCHEMA)
    if compare_errors:
        raise DecideFailure("COMPARE_SCHEMA_INVALID:" + ";".join(compare_errors[:3]))
    # Alerts, dashboard bundle.
    previous_day = previous["run_day_kst"] if previous else None
    scheduled = [d for d in _scheduled_days(day)]
    missing_previous = previous_day is not None and scheduled and previous_day < scheduled[0]
    decision["alerts"], decision["alert_states"] = alert_candidates(
        decision=decision, previous=previous, mode=mode, exceptions=exceptions, previous_run_missing=bool(missing_previous))
    decision["dashboard"] = _dashboard(decision, mode)
    if mode == "apply" and decision["tickets"]:
        start = _earliest_entry_start([(day, ticket.get("session")) for ticket in decision["tickets"]], calendar)
        decision["next_action_for_user"] = f"\uc8fc\ubb38\ud45c {len(decision['tickets'])}\uac74 \u2014 " + (
            f"{start} \uc774\ud6c4 \ud0a4\uc6c0 \uc785\ub825" if start else "\uc800\ub141 \ud0a4\uc6c0 \uc785\ub825")
    # F7 journal (recording mode only).
    decision_sha = decision_identity_hash(decision)
    from portfolio_review_journal import JOURNAL_CORE_DECISION, JournalError, append_auto_core_entries, auto_core_payloads
    planned_entries = [entry_type for entry_type, _payload in auto_core_payloads(decision, decision_sha)]
    decision["journal"] = {"would_append": planned_entries, "appended": []}
    schema_errors = validate_instance(decision, DECISION_SCHEMA)
    if schema_errors:  # checked before the journal or any file is written
        raise DecideFailure("DECISION_SCHEMA_INVALID:" + ";".join(schema_errors[:3]))
    if mode == "apply":
        # r2 R2-5: a core_decision of this evaluation session is already in the journal - only for a rerun of the
        # same run day (r3 R3-3). Another run day with that session is R3-3 above; one that still gets here (an
        # unreadable record after the ledger source, or a source that failed after its journal write) is refused
        # by append_auto_core_entries (CORE_DECISION_ALREADY_RECORDED -> FAIL, fail closed).
        recorded = [entry for entry in journal_start.get("entries") or []
                    if entry.get("entry_type") == JOURNAL_CORE_DECISION
                    and entry.get("evaluation_session") == evaluation_session
                    and (entry.get("payload") or {}).get("run_day_kst") == day]
        if recorded:
            decision["journal"].update(decision_sha256=decision_sha, already_recorded=recorded[-1].get("review_id"))
            if recorded[-1].get("review_id") == decision_sha:
                return decision  # the same decision: nothing is written and that day's decision.json stays
            return _rerun(decision, output_directory, now)

        def recheck() -> list[str]:
            fresh, reasons = core.load_config(config_path)
            if fresh is None:
                return reasons or ["AUTO_CORE_CONFIG_MISSING"]
            found = []
            if fresh.get("decision_mode") != "apply":
                found.append("DECISION_MODE_CHANGED")
            if fresh.get("kill_switch"):
                found.append("KILL_SWITCH_ON")
            current = (provenance_source or (lambda: core.git_provenance(repo)))()
            found += core.apply_guard_reasons("apply", current)
            return found
        try:
            written = append_auto_core_entries(journal_path=journal_path, decision=decision, decision_sha256=decision_sha,
                                               expected_head=journal_start["head_sha256"], recheck=recheck)
            decision["journal"] = {"would_append": planned_entries, "appended": [entry["entry_type"] for entry in written],
                                   "decision_sha256": decision_sha}
            try:
                code = (score_runner or _score)(journal_path)
                if code not in (None, 0):  # r2 R2-8: a non-zero scorer exit is a warning like an exception
                    decision["journal"]["score_warning"] = f"SCORER_EXIT:{code}"
            except Exception as exc:  # noqa: BLE001 - a scorer failure is a warning only
                decision["journal"]["score_warning"] = f"{type(exc).__name__}:{str(exc)[:120]}"
        except JournalError as exc:
            decision["status"] = "FAIL"
            decision["reasons"].append(f"JOURNAL_WRITE_REFUSED:{exc}")
            decision["journal"] = {"would_append": planned_entries, "appended": []}
    return _finish(decision, output_root, output_directory, carry, compare_document)


def decision_identity_hash(decision: dict[str, Any]) -> str:
    """decision_sha256 (the journal review_id): the canonical hash of the decision without what changes between
    two runs on the same inputs (r2 R2-5, so that a same-day rerun is recognised): the run time, the journal
    block, the dirty-path list, the research-record wait, the S7 review file and id (a new file every run; it also
    reads the journal), and the tickets' issue time."""
    view = {key: value for key, value in decision.items() if key not in ("journal", "generated_at", "dirty_paths")}
    view["inputs"] = {key: value for key, value in (decision.get("inputs") or {}).items() if key != "s7_review"}
    if isinstance(view["inputs"].get("research_record"), dict):
        view["inputs"]["research_record"] = {key: value for key, value in view["inputs"]["research_record"].items()
                                             if key != "wait"}
    view["tickets"] = [{**{key: value for key, value in ticket.items() if key != "issuedAt"},
                        "inputs": {key: value for key, value in (ticket.get("inputs") or {}).items()
                                   if key != "s7_review_id"}} for ticket in decision.get("tickets") or []]
    dashboard = decision.get("dashboard") or {}
    view["dashboard"] = {**dashboard, "orders": [{key: value for key, value in order.items() if key != "issuedAt"}
                                                 for order in dashboard.get("orders") or []]}
    return canonical_hash(view)


def _rerun(decision: dict[str, Any], output_directory: Path, now: datetime) -> dict[str, Any]:
    """r2 R2-5: the journal already holds a different core_decision for this evaluation session. Nothing is
    written to the journal; the day's decision.json, compare.json and LATEST_DECISION.json stay; this result is
    kept only as decision.rerun-<HHMMSS KST>.json (HOLD, no ticket offered) with a push for Cowork."""
    decision["status"] = "HOLD"
    decision["reasons"] = sorted(set(decision["reasons"]) | {"CORE_DECISION_ALREADY_RECORDED_DIFFERENT"})
    decision["dashboard"] = {**decision["dashboard"], "orders": []}
    decision["next_action_for_user"] = None
    decision["alerts"] = [alert for alert in decision["alerts"] if not alert["code"].startswith("TICKET:")] + [
        {"code": "CORE_DECISION_ALREADY_RECORDED_DIFFERENT", "push": True,
         "line": "\uac19\uc740 \ub0a0 \uc7ac\uc2e4\ud589 \uacb0\uacfc\uac00 \uae30\ub85d\ub41c \uacb0\uc815\uacfc \ub2e4\ub984 \u2014 Cowork \ud655\uc778(decision.rerun \ud30c\uc77c)"}]
    stamp = now.astimezone(KST).strftime("%H%M%S")
    target, index = Path(output_directory) / f"{RERUN_PREFIX}{stamp}.json", 1
    while target.exists():
        target, index = Path(output_directory) / f"{RERUN_PREFIX}{stamp}-{index}.json", index + 1
    decision["journal"]["rerun_file"] = target.name
    write_json(target, decision)
    return decision


def _no_new_session(*, decision: dict[str, Any], carry: dict[str, Any], previous: dict[str, Any] | None,
                    previous_all: list[tuple[str, Any]], config: dict[str, Any], mode: str, calendar: dict[str, Any],
                    explained_path: Path, output_root: Path, output_directory: Path, day: str) -> dict[str, Any]:
    """r3 R3-3: the evaluation session is the ledger source's (the latest record with f6_ran true): no U.S.
    session has closed since (a holiday before this run). Nothing new is judged: status OK, no ticket, no journal
    entry, no push, no broker read. The source's keys, attributed orders (r4 R4-1) and unclassified tickets are
    carried (carried_from) and f6_ran stays true, so the ledger source carries on. F6 keeps the R3-1 rule: a ticket whose session has not
    ended stays open; one whose session ended but that the source could not classify (a failed read there) also
    stays open for the next run with a new session, because no outcome is classified on a day that writes no
    journal entry. The compare streak is kept (the integrated check has the same session: no new judgment). The
    source's judgment views of the same session, its alert states (the next run's repetition base) and the
    dashboard rows of the tickets still before their session are kept, so the user still sees what to enter;
    decision.json is a normal OK record, so the next run's alert 11 (previous run missing) does not fire."""
    source = carry["source"]
    evaluation_session = decision["evaluation_session"]
    open_tickets = [dict(ticket) for ticket in carry["open_tickets"]]
    not_yet = [ticket["ticket_id"] for ticket in open_tickets
               if not tickets_module.ticket_session_ended(ticket, evaluation_session)]
    dashboard = source.get("dashboard") or {}
    run_core = copy.deepcopy(dashboard.get("runCore") or {})
    if "tickets" in run_core:
        run_core["tickets"] = [item for item in run_core["tickets"] if item.get("id") in not_yet]
    orders = [copy.deepcopy(order) for order in dashboard.get("orders") or [] if order.get("id") in not_yet]
    block: dict[str, Any] = {"status": compare_module.NO_NEW_SESSION, "same_session_as": carry["carried_from"]}
    explained, explained_errors = compare_module.load_explained(explained_path)
    history = [(run_day, compare_module.streak_block(item)) for run_day, item in previous_all] + [(day, block)]
    block.update(streak=compare_module.streak(history, explained),
                 required=int(config.get("decision_compare_days_required") or 5), explained_errors=explained_errors)
    decision["inputs"].update(
        calendar={"sha256": calendar["identity"]["calendar_sha256"], "authority": calendar["identity"]["authority_status"]},
        previous_decision={"run_day_kst": (previous or {}).get("run_day_kst")},
        no_new_session={"source_run_day": carry["carried_from"], "evaluation_session": evaluation_session,
                        "not_yet": not_yet,
                        "deferred": [ticket["ticket_id"] for ticket in open_tickets if ticket["ticket_id"] not in not_yet]})
    for key, empty in (("symbols", {}), ("evidence", {}), ("buy_requirements", []), ("exposure", {}), ("shock", {}),
                       ("account", {}), ("earnings_calendar", {}), ("facts_seen", []), ("alert_states", {})):
        decision[key] = copy.deepcopy(source.get(key) or empty)
    if source.get("registry_flags") is not None:
        decision["registry_flags"] = list(source["registry_flags"])
    decision.update(
        status="OK", reasons=[], no_new_session=True, f6_ran=True, carried_from=carry["carried_from"],
        keys=dict(carry["keys"]), attributed_orders=[dict(entry) for entry in carry["attributed_orders"]],
        open_tickets=open_tickets, tickets=[], outcomes=[], candidates=[], blocked=[],
        no_action={"value": True, "reasons": ["NO_NEW_SESSION"]}, compare=block,
        journal={"would_append": [], "appended": []}, dashboard={"runCore": run_core, "orders": orders},
        alerts=[{"code": "NO_NEW_SESSION", "push": False,
                 "line": f"\uc0c8 \ubbf8\uad6d \uc138\uc158 \uc5c6\uc74c \u2014 \ud3c9\uac00 \uc138\uc158 {evaluation_session} "
                         "\uadf8\ub300\ub85c(\uc8fc\ubb38\ud45c\u00b7\uc77c\uc9c0 \uc5c6\uc74c)"}],
        next_action_for_user=(_carried_entry_line(orders, open_tickets, calendar) if mode == "apply" and orders else None),
        next_action_for_cowork=None)
    return _finish(decision, output_root, output_directory, carry)


def _earliest_entry_start(pairs: list[tuple[Any, Any]], calendar: dict[str, Any] | None) -> str | None:
    """enter-window: 'M/D(<weekday>) HH:MM' of the earliest entry start (tickets_module.entry_start) of the
    (issue day, session) pairs; None when there is none or any of them cannot be read (not guessed)."""
    sessions = (calendar or {}).get("sessions") or {}
    starts = [tickets_module.entry_start(issued, sessions.get(session)) if isinstance(session, str) else None
              for issued, session in pairs]
    if not starts or None in starts:
        return None
    return tickets_module.entry_start_text(min(starts))


def _carried_entry_line(orders: list[dict[str, Any]], open_tickets: list[dict[str, Any]],
                        calendar: dict[str, Any] | None = None) -> str:
    """pre-on-fix 4 (judge2 G 4): the user line of a no-new-session day that carries order rows. They are the
    same tickets issued earlier (every issue KST day is named, M/D); the day reads no open order, so the line
    says not to enter them again if already entered (enter only if not). An unreadable issue day shows as "?"
    (visible, not guessed). enter-window: "if not" names the earliest entry start of those tickets' sessions
    (M/D(<weekday>) HH:MM); when one cannot be read, the line keeps "in the evening"."""
    by_id = {ticket["ticket_id"]: ticket for ticket in open_tickets}
    issued = {ticket_id: str(ticket.get("issued_day") or "") for ticket_id, ticket in by_id.items()}
    days = set()
    for order in orders:
        try:
            value = date.fromisoformat(issued.get(order.get("id"), ""))
            days.add((value.isoformat(), f"{value.month}/{value.day}"))
        except ValueError:
            days.add(("~", "?"))
    names = "\u00b7".join(name for _key, name in sorted(days))
    start = _earliest_entry_start([(issued.get(order.get("id")), (by_id.get(order.get("id")) or {}).get("session"))
                                   for order in orders], calendar)
    when = f"{start} \uc774\ud6c4" if start else "\uc800\ub141"
    return (f"\uc8fc\ubb38\ud45c {len(orders)}\uac74 \u2014 {names} \ubc1c\ud589\ubd84\uacfc \uac19\uc740 \uc8fc\ubb38\ud45c: "
            "\uc774\ubbf8 \uc785\ub825\ud588\uc73c\uba74 \ub2e4\uc2dc \ub123\uc9c0 \uc54a\uc74c"
            f"(\uc548 \ub123\uc5c8\uc73c\uba74 {when} \ud0a4\uc6c0 \uc785\ub825)")


def card_accepted_on(check: dict[str, Any]) -> str | None:
    """ev-rg1-hyper: the registry accepted.date (strict YYYY-MM-DD) of a card_check entry; None without one."""
    return rules.iso_day((((check or {}).get("entry") or {}).get("accepted") or {}).get("date"))


def portfolio_accepted_on(accepted_on: dict[str, str | None], holdings: dict[str, int]) -> str | None:
    """ev-rg1-hyper R0: the portfolio card date = the earliest accepted.date of the holdings; None when there is no
    holding or one of them has no registry entry or date (nothing is cleared)."""
    dates = [accepted_on.get(symbol) for symbol in sorted(holdings)]
    return min(dates) if dates and None not in dates else None


def _bars_with_close(item: dict[str, Any] | None, session: str, price: Decimal) -> dict[str, Any] | None:
    """close-confirm e: a copy of one symbol's load_symbol result whose `session` bar has close = price, high =
    max(high, price) and low = min(low, price) (None stays None) in both the raw and the adjusted bars (one copy
    when they are the same object); every other session and field is the input's. The input is not changed (E7).
    None = it cannot be built: no usable bars (status not OK), no such session, or the session's raw and adjusted
    closes differ (a split adjustment reaching the evaluation session)."""
    if item is None or item.get("status") != "OK":
        return None
    raw, adjusted = item["raw"], item["adjusted"]
    raw_bar, adjusted_bar = raw["sessions"].get(session), adjusted["sessions"].get(session)
    if raw_bar is None or adjusted_bar is None or raw_bar["close"] != adjusted_bar["close"]:
        return None

    def replaced(daily: dict[str, Any], bar: dict[str, Any]) -> dict[str, Any]:
        moved = {**bar, "close": price, "high": None if bar["high"] is None else max(bar["high"], price),
                 "low": None if bar["low"] is None else min(bar["low"], price)}
        return {**daily, "sessions": {**daily["sessions"], session: moved}}

    raw_b = replaced(raw, raw_bar)
    return {**item, "raw": raw_b, "adjusted": raw_b if adjusted is raw else replaced(adjusted, adjusted_bar)}


def evaluate_session(*, day: str, mode: str, issued_at: str, calendar: dict[str, Any], evaluation_session: str,
                     bars: dict[str, dict[str, Any]], holdings: dict[str, int], cash: Decimal | None,
                     deposit: Decimal | None, sectors: dict[str, Any], members: list[str],
                     checks: dict[str, dict[str, Any]], watchlist: dict[str, Any], m6_docs: list[tuple[str, str]],
                     facts: list[dict[str, Any]] | None, earnings: dict[str, Any] | None, ev3: list[str],
                     seen_fact_ids: set[str], policy: dict[str, Any], config: dict[str, Any],
                     keys: dict[str, Any], gate0: list[str], gate1: list[str],
                     s7_runner: Callable[[list[dict[str, Any]]], dict[str, Any]],
                     research: dict[str, Any], input_hashes: dict[str, Any],
                     hold_range: bool = False) -> dict[str, Any]:
    """F1 judgments, F4 requirements and gates, F5 tickets for one evaluation session.

    decide and auto_core_replay both call this (one implementation). bars are load_symbol outputs for every
    symbol in holdings, members and the R-REC1 benchmarks; checks are card_check results; s7_runner runs the
    S7 review with the given buy-target proposals and returns the review document. facts: official facts of the
    recent research records (None = today's record is not OK). research: {block: why today's record is not OK
    or None, sessions: sessions with a valid record in the R-REC1 window, damage: root-thesis-damage facts of
    those records}.
    cash: the buy cash (order-available). deposit: the USD cash of the total equity behind the rule-file N and V6
    (t2-equity-cash: decide passes equity_cash's choice, the replay its one cash; the keyword name is kept).
    hold_range (close-confirm e, user decision 2026-10-20): decide passes True, so plan() gets ctx["hold_eval"]
    and every ticket its hold range (tickets_module.hold_range); False (the replay, the default) keeps the tickets
    as before.
    """
    sessions = sorted(calendar["sessions"])
    later = [item for item in sessions if item > evaluation_session]
    earlier = [item for item in sessions if item < evaluation_session]
    buy_session = later[0] if later else None
    previous_session = earlier[-1] if earlier else None
    multipliers = dict(policy["portfolio_exposure_policy"]["nominal_multipliers"])
    universe = sorted(bars)
    gate1 = list(gate1)
    series = {}
    for symbol in universe:
        if bars[symbol]["status"] == "OK" and not bars[symbol]["split_suspects"]:
            series[symbol] = rules.build_series(bars[symbol]["adjusted"], sessions, evaluation_session)
    damage = list(research["damage"])

    # close-confirm e: the per-symbol calls below are shared with hold_eval (the same calls with the same arguments).
    def raw_closes(by_symbol: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return {symbol: by_symbol[symbol]["raw"]["sessions"].get(evaluation_session, {}).get("close")
                for symbol in universe if by_symbol[symbol]["status"] == "OK"}

    def judge(symbol: str, symbol_bars: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
        held = symbol in holdings
        check = checks[symbol]
        own_facts = None if facts is None else [fact for fact in facts if fact["symbol"] == symbol]
        # Card triggers judge even on a hash mismatch; static evidence counts only when the hash matches.
        result = rules.evaluate_symbol(symbol=symbol, role="held" if held else "member", bars=symbol_bars,
                                       calendar=calendar, evaluation_session=evaluation_session,
                                       registry_entry=check["entry"], held=held, member=symbol in members,
                                       multiplier=multipliers.get(symbol), facts=own_facts,
                                       buy_approved=symbol in tickets_module.APPROVED_BUY)
        official = tickets_module.official_evidence(symbol, facts or [], evaluation_session=evaluation_session,
                                                    previous_session=previous_session, seen_fact_ids=seen_fact_ids)
        return result, {side: tickets_module.evidence_summary(side=side, result=result, check=check,
                                                               official=official, config=config)
                        for side in ("buy", "sell")}

    closes_raw = raw_closes(bars)
    nominal = tickets_module.rule_file_nominal(holdings, closes_raw, deposit, multipliers)
    account = rules.v6_account(nominal.get("total"))
    symbols_out, evidence, shocks = {}, {}, {}
    for symbol in sorted(set(holdings) | set(members)):
        symbols_out[symbol], evidence[symbol] = judge(symbol, bars.get(symbol))
    facts_seen = sorted({fact_id for item in evidence.values() for side in item.values()
                         for fact_id in side["official"]} | set(seen_fact_ids))
    # S7 with the buy-target proposals of every symbol whose buy circuit may open (D5): new evidence alone, or the
    # S7 supplement with requirement (3) met (S7 adds only the supplement when no card ADD is passed to it).
    exposure_policy = policy["portfolio_exposure_policy"]
    cap = float(exposure_policy["single_stock_nominal_cap"])
    projected_lte = float(exposure_policy["thresholds"]["exposure_increasing_projected_exposure_lte"])
    proposal_symbols = sorted(symbol for symbol in symbols_out
                              if evidence[symbol]["buy"]["new_basis_met"]
                              or (symbol == exposure_policy["reduce_order"][-1] and evidence[symbol]["buy"]["basis_met"]))
    proposals, proposal_index = [], []
    for symbol in proposal_symbols:
        for target in tickets_module.proposal_targets(symbol, multipliers, cap, projected_lte,
                                                      list(exposure_policy["single_stock_cap_exempt"])):
            proposals.append({"kind": "new_buy_within_band", "symbol": symbol, "target_weight": float(target)})
            proposal_index.append((symbol, target))
    review = s7_runner(proposals)
    s7 = tickets_module.s7_summary(review, evaluation_session, previous_session)
    gate1 += tickets_module.policy_mismatches(s7)
    if not s7["latest"]:
        gate1.append("G1_S7_NOT_LATEST_SESSION")
    if s7.get("fail_closed"):
        gate1.append("G1_S7_FAIL_CLOSED:" + ",".join(s7.get("fail_closed_triggers") or []))
    proposal_results = []
    for item in review.get("recommendations", {}).get("proposals") or []:
        if 0 <= item["index"] < len(proposal_index):
            symbol, target = proposal_index[item["index"]]
            proposal_results.append({"symbol": symbol, "target_weight": float(target), "status": item["status"],
                                     "reasons": item.get("reasons") or []})
    peaks = {item["symbol"]: item for item in review.get("peak_reviews") or []}
    account["s7_hwm_usd"] = s7.get("hwm_usd")
    # t2rc-corefix 1 (rule file 102): events, C0, L0, RG3, RG4, DS1 and the record-gap check on SOXX for every
    # candidate; the sector's RG2 benchmark (GRID for 'A1 power') is only the benchmark leg of RG2.
    # ev-rg1-hyper: a damage fact is cleared only by a later card acceptance (registry accepted.date) - the
    # candidate's own card; for the portfolio the earliest card of the holdings (none if a holding has no date).
    accepted_on = {symbol: card_accepted_on(checks[symbol]) for symbol in symbols_out}

    def shock_of(symbol: str, by_symbol: dict[str, Any]) -> dict[str, Any]:
        return rules.rrec1(benchmark=by_symbol.get(rules.C["RREC_BENCHMARK"]),
                           candidate=by_symbol.get(symbol), evaluation_session=evaluation_session,
                           ev3_user_dates=ev3, thesis_damage=damage,
                           candidate_symbol=symbol, research_sessions=research["sessions"],
                           rg2_series=by_symbol.get(rules.rg2_benchmark(sectors.get(symbol))),
                           card_accepted_on=accepted_on[symbol])

    for symbol in sorted(symbols_out):
        shocks[symbol] = shock_of(symbol, series)
    portfolio_shock = rules.rrec1(benchmark=series.get("SOXX"), candidate=None, evaluation_session=evaluation_session,
                                  ev3_user_dates=ev3, thesis_damage=damage,
                                  research_sessions=research["sessions"],
                                  card_accepted_on=portfolio_accepted_on(accepted_on, holdings))
    exposure = {
        "N": nominal.get("n"), "N_status": nominal.get("status"), "N_assumed_one_x": nominal.get("assumed_one_x"),
        "S7": {"E": s7.get("e"), "band": s7.get("band"), "fresh": s7.get("fresh"), "session": s7.get("session"),
               "pauses": {"new_buy": s7.get("new_buy_paused"), "add": s7.get("add_paused")}},
        "caps": s7.get("cap_breaches") or [],
        "peaks": [{"symbol": symbol, "state": rules.r5_state(item), "peak": item.get("peak"), "close": item.get("close"),
                   "threshold": item.get("threshold")} for symbol, item in sorted(peaks.items())],
    }
    shock = {**portfolio_shock, "by_symbol": {symbol: {"status": item["status"], "open": item["open"], "rg": item["rg"]}
                                              | ({"rg1_damage": item["rg1_damage"]} if "rg1_damage" in item else {})
                                              for symbol, item in shocks.items()}}

    def requirement_row(symbol: str, nominal_of: dict[str, Any], closes_of: dict[str, Any],
                        evidence_of: dict[str, Any], shock_of_symbol: dict[str, Any]) -> dict[str, Any]:
        return tickets_module.buy_requirements(
            symbol=symbol, held=symbol in holdings, s7=s7, nominal=nominal_of, peaks=peaks, earnings=earnings,
            calendar_sessions=sessions, buy_session=buy_session, evaluation_session=evaluation_session,
            generated_at=(review.get("inputs") or {}).get("generated_at"), cash=cash, close=closes_of.get(symbol),
            check=checks[symbol], evidence=evidence_of["buy"],
            watch_status=(watchlist["members"].get(symbol) or {}).get("cardStatus"),
            m6=rules.m6_listed(symbol, m6_docs), shock=shock_of_symbol, research_block=research["block"])

    def data_reason(result: dict[str, Any]) -> list[str]:
        return ([] if result["status"] == "OK" and (result.get("indicators") or {}).get("sigma60")
                else ["G1_SYMBOL_DATA:" + ",".join(result["reasons"] or ["SIGMA_UNAVAILABLE"])])

    rows = []
    for symbol in sorted(symbols_out):
        rows.append(requirement_row(symbol, nominal, closes_raw, evidence[symbol], shocks[symbol]))
    data_reasons = {symbol: data_reason(result) for symbol, result in symbols_out.items()}
    equity = _decimal((review.get("equity") or {}).get("closing_equity_usd"))
    weights = {item["symbol"]: item["weight"] for item in review.get("positions") or [] if item.get("weight") is not None}
    adjusted_for_s7 = {symbol: {item: format(bar["close"], "f") for item, bar in bars[symbol]["adjusted"]["sessions"].items()}
                       for symbol in universe if bars[symbol]["status"] == "OK"}
    model_for = s7_model_factory(policy, adjusted_for_s7, sessions, evaluation_session)
    scenario = {symbol: tickets_module.scenarios(item["close"]) for symbol, item in series.items() if item}
    policy_instruments = set(exposure_policy["card_stock_core"]) | set(exposure_policy["allowed_index_etfs"])
    redeploy_ranked = redeploy_ranking(rows=rows, checks=checks, evidence=evidence, scenarios=scenario,
                                       policy_instruments=policy_instruments)

    def known(closes_of: dict[str, Any]) -> dict[str, Any]:
        return {symbol: value for symbol, value in closes_of.items() if value is not None}

    def sigma_of(result: dict[str, Any]) -> Any:
        return (result.get("indicators") or {}).get("sigma60")

    def marks_of(result: dict[str, Any]) -> dict[str, Any]:
        return {key: (result.get("indicators") or {}).get(key) for key in ("ema20", "atr14")}

    ctx = {
        "run_day": day, "mode": mode, "evaluation_session": evaluation_session, "buy_session": buy_session,
        "calendar": calendar, "issued_at": issued_at, "symbols": symbols_out, "checks": checks, "review": review,
        "s7": s7, "holdings": holdings, "equity": equity, "weights": weights, "cash": cash,
        "closes": known(closes_raw),
        "sigmas": {symbol: sigma_of(item) for symbol, item in symbols_out.items()},
        "config": config, "gate0": {"ok": not gate0, "reasons": list(gate0)},
        "gate1": {"ok": not gate1, "reasons": gate1}, "evidence": evidence, "buy_rows": rows,
        "data_reasons": data_reasons, "proposal_results": proposal_results,
        "policy_instruments": policy_instruments,
        "scenarios": scenario, "keys": keys, "model_for": model_for, "redeploy_ranked": redeploy_ranked,
        "input_hashes": {**input_hashes, "s7_review_id": review.get("review_id")},
        "research_block": research["block"],
        # risk1r: evaluation-session EMA20 and ATR14 for the display-only 1R of a buy ticket.
        "indicators": {symbol: marks_of(item) for symbol, item in symbols_out.items()},
    }

    def hold_eval(symbol: str, price: Decimal) -> dict[str, Any] | None:
        """close-confirm e: plan()'s ctx at the time of the call (a shallow copy) with `symbol`'s evaluation-session
        close replaced by `price` (_bars_with_close) and that symbol recomputed by the same calls as above: series,
        F1 and evidence (judge), rule-file N, R-REC1 (shock_of), its buy-requirement row, data reason, sigma60,
        scenario and 1R marks. S7 (review, s7, equity, weights, proposal evaluations), the other symbols, cash,
        gates, keys and the redeployment candidate stay; model_for is None (the after-sale projection is display
        only) and hold_eval None (no recursion). None = the bars of that close cannot be built (DATA)."""
        changed = _bars_with_close(bars.get(symbol), evaluation_session, price)
        if changed is None:
            return None
        bars_b = {**bars, symbol: changed}
        series_b = {key: value for key, value in series.items() if key != symbol}
        if changed["status"] == "OK" and not changed["split_suspects"]:
            series_b[symbol] = rules.build_series(changed["adjusted"], sessions, evaluation_session)
        closes_b = raw_closes(bars_b)
        result, evidence_b = judge(symbol, changed)
        row = requirement_row(symbol, tickets_module.rule_file_nominal(holdings, closes_b, deposit, multipliers),
                              closes_b, evidence_b, shock_of(symbol, series_b))
        view = dict(ctx)
        scenarios_b = {key: value for key, value in view["scenarios"].items() if key != symbol}
        if series_b.get(symbol):
            scenarios_b[symbol] = tickets_module.scenarios(series_b[symbol]["close"])
        view.update(symbols={**view["symbols"], symbol: result}, evidence={**view["evidence"], symbol: evidence_b},
                    closes=known(closes_b), sigmas={**view["sigmas"], symbol: sigma_of(result)},
                    buy_rows=[row if item["code"] == symbol else item for item in view["buy_rows"]],
                    data_reasons={**view["data_reasons"], symbol: data_reason(result)}, scenarios=scenarios_b,
                    indicators={**view["indicators"], symbol: marks_of(result)}, model_for=None, hold_eval=None)
        return view

    if hold_range:
        ctx["hold_eval"] = hold_eval
    planned = tickets_module.plan(ctx)
    for ticket in planned["tickets"]:
        ticket["mode"] = mode
        if mode == "compare":
            ticket["note"] = NOT_FOR_ENTRY
    return {"symbols": symbols_out, "evidence": evidence, "rows": rows, "planned": planned, "s7": s7, "review": review,
            "nominal": nominal, "account": account, "exposure": exposure, "shock": shock, "shocks": shocks,
            "earnings_calendar": {symbol: record for symbol, record in (earnings or {}).items()},
            "facts_seen": facts_seen, "gate1": gate1, "proposal_results": proposal_results, "series": series,
            "buy_session": buy_session}


# Buy requirement cells a redeployment candidate must pass: (1) earnings, (3) evidence, (4) M6, (5) R-REC1.
REDEPLOY_REQUIRED_CELLS = (0, 2, 3, 4)


def redeploy_ranking(*, rows: list[dict[str, Any]], checks: dict[str, dict[str, Any]],
                     evidence: dict[str, dict[str, Any]], scenarios: dict[str, dict[str, Any]],
                     policy_instruments: set[str]) -> list[dict[str, Any]]:
    """t2rc-corefix 4 (Judge S3, S5): the ranked redeployment candidates of the sell regret bridge. A candidate
    passes buy requirements (1), (3), (4), (5) that day, is an approved policy product (card_stock_core +
    allowed_index_etfs, so a sell-only holding is not one), has an eligible card and scenario returns. (2), the
    S7 pauses and the E after the sale are not filtered: the D+1 gates see the new state and the cash columns
    are always there. Rank: strong evidence count, weak kind count, code. plan() leaves out the symbols whose
    sell circuit is open that day and takes the first remaining one."""
    ranked = sorted((row["code"] for row in rows
                     if (checks.get(row["code"]) or {}).get("eligible") and row["code"] in policy_instruments
                     and all(row["c"][index]["s"] == "ok" for index in REDEPLOY_REQUIRED_CELLS)
                     and (scenarios.get(row["code"]) or {}).get("status") == "ok"),
                    key=lambda symbol: (-len(evidence[symbol]["buy"]["strong"]),
                                        -len(evidence[symbol]["buy"]["weak_kinds"]), symbol))
    return [{"symbol": symbol, "up": scenarios[symbol]["up"], "down": scenarios[symbol]["down"]} for symbol in ranked]


def _score(journal_path: Path) -> Any:
    import score_decision_journal

    return score_decision_journal.main(["--journal", str(journal_path)])


def _scheduled_days(day: str) -> list[str]:
    """The previous scheduled decide day (Tuesday-Saturday) before `day`."""
    current = date.fromisoformat(day) - timedelta(days=1)
    while current.weekday() not in (1, 2, 3, 4, 5):
        current -= timedelta(days=1)
    return [current.isoformat()]


def _symbol_view(result: dict[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in ("symbol", "role", "status", "reasons", "indicators", "triggers", "groups",
                                         "c7_notes", "buy_approved", "nocard") if key in result} | {
        "margins": result.get("margins") or {}}


def _dashboard(decision: dict[str, Any], mode: str) -> dict[str, Any]:
    vocabulary = {"hit": "hit", "review": "hit", "near": "near", "pending": "wait", "none": "none", "unk": "unk",
                  "info": "info"}
    triggers = []
    for symbol, result in decision["symbols"].items():
        items = [{"id": trigger["id"], "name": trigger["name"], "state": vocabulary.get(trigger["state"], "unk")}
                 for trigger in result["triggers"] if trigger["state"] not in ("none",)]
        quiet = "\u00b7".join(trigger["id"] for trigger in result["triggers"] if trigger["state"] == "none")
        triggers.append({"code": symbol, "role": "\ubcf4\uc720" if result["role"] == "held" else "\uad00\uc2ec",
                         "items": items, "quiet": quiet})
    tickets = [{"id": ticket["ticket_id"], "ticker": ticket["ticker"], "side": ticket["side"], "qty": ticket["qty"],
                "price": ticket["price"], "note": ticket.get("note"), "risk1r": _risk1r_line(ticket)}
               for ticket in decision["tickets"]]
    orders = []
    if mode == "apply":
        for ticket in decision["tickets"]:
            risk1r = _risk1r_line(ticket)
            orders.append({"id": ticket["ticket_id"], "status": "official", "source": "auto-core",
                           "issuedAt": ticket["issuedAt"], "session": ticket["session"],
                           "enterWindow": ticket["enterWindow"], "fillAt": ticket["fillAt"], "ref": ticket["ref"],
                           "ifUnfilled": ticket["ifUnfilled"], "ticker": ticket["ticker"], "side": ticket["side"],
                           "type": "LOC", "price": ticket["price"], "priceRule": ticket["priceRule"],
                           "priceCalc": ticket["priceCalc"], "qty": ticket["qty"], "amount": ticket["amount"],
                           "feeRate": ticket["feeRate"], "reason": ticket["reason"],
                           "evidence": ticket["evidence"]["composition"] + f" \u00b7 r {ticket['evidence']['r']}"
                           + ("" if risk1r is None else " \u00b7 " + risk1r),
                           "afterSale": _after_sale_line(ticket.get("after_sale")), "outcome": {"state": "pending"}})
    return {"runCore": {"triggers": triggers, "buyReq": {"rows": decision["buy_requirements"]},
                        "exposure": {key: value for key, value in decision["exposure"].items() if key != "cash_basis"},
                        "shock": {key: decision["shock"].get(key) for key in ("open", "events", "event", "rg", "ds1")},
                        "peakReviews": decision["exposure"].get("peaks"), "tickets": tickets,
                        "account": {key: decision["account"].get(key) for key in ("state", "total", "first_cushion_pct")}},
            "orders": orders}


def _risk1r_line(ticket: dict[str, Any]) -> str | None:
    """risk1r: the display-only 1R line of a buy ticket (None for a sell or a ticket without one)."""
    if ticket.get("side") != "buy":
        return None
    return (ticket.get("risk_1r") or {}).get("line")


def _after_sale_line(after: dict[str, Any] | None) -> str | None:
    if not after:
        return None
    pair = after.get("swap_pair") or {}
    return (f"\uc608\uc0c1 E {after.get('e')} \u00b7 \ud604\uae08 ${after.get('cash_after')}"
            + (f" \u00b7 \uad50\uccb4 {pair.get('sell')} \u2192 {pair.get('buy_next_day')}" if pair else "")
            + (" \u00b7 " + after["plan_premise"] if after.get("plan_premise") else ""))


def _settle(decision: dict[str, Any], carry: dict[str, Any]) -> None:
    """r2 R2-2: a record that ended before F6, or failed, commits nothing. It copies the ledger source's keys,
    attributed orders (r4 R4-1) and unclassified tickets (carried_from = the source run day, so a reader sees no break) and keeps f6_ran false,
    so the next run classifies again from the source. A FAIL record also offers no ticket (the schema's "a HOLD
    or FAIL day has no ticket": nothing of it was journaled) and pushes DECIDE_FAIL."""
    if decision["status"] == "FAIL" or not decision["f6_ran"]:
        decision.update(f6_ran=False, keys=dict(carry["keys"]), carried_from=carry["carried_from"],
                        attributed_orders=[dict(entry) for entry in carry["attributed_orders"]],
                        open_tickets=[dict(ticket) for ticket in carry["open_tickets"]])
    if decision["status"] != "FAIL":
        return
    if decision["tickets"]:
        decision["no_action"] = {"value": True, "reasons": ["DECIDE_FAIL"]}
    decision.update(tickets=[], outcomes=[], next_action_for_user=None)
    run_core = dict(decision["dashboard"].get("runCore") or {})
    if "tickets" in run_core:
        run_core["tickets"] = []
    decision["dashboard"] = {**decision["dashboard"], "runCore": run_core, "orders": []}
    decision["alerts"] = [alert for alert in decision["alerts"] if not alert["code"].startswith("TICKET:")]
    if not any(alert["code"] == "DECIDE_FAIL" for alert in decision["alerts"]):
        decision["alerts"].append({"code": "DECIDE_FAIL", "push": True,
                                   "line": "decide \uc2e4\ud328 \u2014 " + ",".join(decision["reasons"][:3])})


def _finish(decision: dict[str, Any], output_root: Path, output_directory: Path, carry: dict[str, Any],
            compare_document: dict[str, Any] | None = None) -> dict[str, Any]:
    _settle(decision, carry)
    errors = validate_instance(decision, DECISION_SCHEMA)
    if errors:
        decision["status"] = "FAIL"
        decision["reasons"].append("DECISION_SCHEMA_INVALID:" + ";".join(errors[:3]))
        _settle(decision, carry)
    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(output_directory / DECISION_FILE, decision)
    write_json(Path(output_root) / LATEST_DECISION_FILE, decision)
    if compare_document is not None:
        write_json(output_directory / COMPARE_FILE, compare_document)
    return decision
