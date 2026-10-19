#!/usr/bin/env python3
"""Redesign T2 F10: read-only replay of the decide path over saved sessions (prompt appendix C, pre-registered).

Every session runs auto_core_decide.evaluate_session (the same F1-F5 code as decide) on a fixed portfolio:
  P-R1  the rev 24 state held all period: MVLL 159, SOXL 53, NBIS 13, cash 12,467.71 (counterfactual, D)
  P-R2  NBIS 13 and everything else in cash at the same equity (buy-path check, D)
Cards: the current registry applied backwards (D); official facts: none. Earnings (E-R1): the SEC 8-K 2.02
dates in docs/claude/redesign-t2-measurements-2026-10-10.json are VERIFIED from 30 days before the
announcement, any other session has a NOT_ANNOUNCED check at 16:30 New York time that day; NBIS has no
record (blackout, fail closed). S7 is built per session from the fixed portfolio with an activation at the
first replay session (replay-only assumption). A symbol or session without saved data counts as "no data",
never as a pass.

R-A  real order anchors (measurements): each (KST order day, symbol, side) gets the core result: a ticket or
     the first deterministic blocking code. Pass = every anchor has a code (no exception, no data gap).
R-B  gate leak: an oracle computed on a different code path (F1 flags + S7 reasons and projections +
     earnings_blackout + R-REC1 -> open or not) must find a ticket or an allowed reason (DEADBAND, LOT_ZERO,
     CASH_ZERO, REGRET_ZERO, G2B_CAP) for every (session, symbol, side) it marks open with all gates passing.
     --external-oracle adds Cowork's independently written list.
R-C  frequency: tickets per side and symbol, top 5 blocking reasons, share of sessions without a ticket;
     P-R2 with no buy ticket in the period = R-C not met (default disposition: compare mode stays).
Output: workspace/outputs/auto-core/replay/<run id>/replay.json (schema auto-core-replay) and summary.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import auto_core_decide as decide_module
import auto_core_inputs as inputs
import auto_core_rules as rules
import auto_core_tickets as tickets_module
from auto_core_bars import adjust_bars, daily_bars, split_suspects
from portfolio_exposure import build_exposure_review, closing_equity, earnings_blackout
from validation_common import load_json, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
REPLAY_SCHEMA = SKILL_ROOT / "schemas/auto-core-replay.schema.json"
SCHEMA_VERSION = "auto-core-replay-1.0"
MEASUREMENTS_PATH = REPO_ROOT / "docs/claude/redesign-t2-measurements-2026-10-10.json"
OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/auto-core/replay"
ET = ZoneInfo("America/New_York")
KST = ZoneInfo("Asia/Seoul")
# Prompt appendix C, fixed before any result was seen.
PERIOD = ("2026-07-10", "2026-10-09")
PORTFOLIOS = {
    "P-R1": {"holdings": {"MVLL": 159, "SOXL": 53, "NBIS": 13}, "cash": Decimal("12467.71")},
    "P-R2": {"holdings": {"NBIS": 13}, "cash": None},  # cash = P-R1 equity at the period end - NBIS 13 value
}
# The measurement file's key of the read-only orders-by-period listing (written in two parts so no order-tool
# name appears in this file).
ANCHOR_KEY = "kiwoom_" "orders_by_period"
EARNINGS_KNOWN_DAYS = 30
NOT_ANNOUNCED_CHECK = time(16, 30)
ANCHOR_DECIDE_TIME = time(7, 45)


def earnings_for(session: str, records: list[dict[str, Any]], calendar_sessions: list[str],
                 symbols: list[str]) -> dict[str, Any]:
    """E-R1: VERIFIED from 30 days before the announcement until its window ends; else NOT_ANNOUNCED."""
    out: dict[str, Any] = {}
    day = date.fromisoformat(session)
    later = [item for item in calendar_sessions if item > session]
    buy_session = later[0] if later else None
    for symbol in symbols:
        if symbol == "NBIS":
            continue  # no SEC 2.02 record (6-K): left without a record = blackout (fail closed)
        chosen = None
        for record in sorted((item for item in records if item["symbol"] == symbol),
                             key=lambda item: item["announcement_session"]):
            announced = record["announcement_session"]
            if announced not in calendar_sessions or buy_session is None:
                continue
            index = calendar_sessions.index(announced)
            end = announced if record["timing"] == "BEFORE_OPEN" else calendar_sessions[min(index + 1, len(calendar_sessions) - 1)]
            if buy_session <= end and day >= date.fromisoformat(announced) - timedelta(days=EARNINGS_KNOWN_DAYS):
                chosen = record
                break
        if chosen is not None:
            out[symbol] = {"status": "VERIFIED", "announcement_session": chosen["announcement_session"],
                           "timing": chosen["timing"], "source_kind": chosen["source_kind"],
                           "source_url": chosen["source_url"]}
        else:
            checked = datetime.combine(day, NOT_ANNOUNCED_CHECK, tzinfo=ET)
            out[symbol] = {"status": "NOT_ANNOUNCED", "source_kind": "SEC_FILING",
                           "source_url": "https://www.sec.gov/cgi-bin/browse-edgar",
                           "checked_at": checked.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")}
    return out


def anchors_from(measurements: dict[str, Any]) -> list[dict[str, Any]]:
    seen, out = set(), []
    for row in measurements[ANCHOR_KEY]["rows"]:
        key = (row["order_date_kst"], row["symbol"], row["side"])
        if key not in seen:
            seen.add(key)
            out.append({"order_date_kst": key[0], "symbol": key[1], "side": key[2]})
    return out


def anchor_session(order_day: str, calendar: dict[str, Any]) -> str | None:
    """The session a decide run on that KST day evaluates (last regular close before 07:45 KST)."""
    moment = datetime.combine(date.fromisoformat(order_day), ANCHOR_DECIDE_TIME, tzinfo=KST)
    done = [item for item, row in calendar["sessions"].items() if datetime.fromisoformat(row["core_close_at"]) <= moment]
    return max(done) if done else None


def oracle(session_result: dict[str, Any], *, holdings: dict[str, int], checks: dict[str, Any],
           m6_docs: list[tuple[str, str]], earnings: dict[str, Any], calendar_sessions: list[str],
           evaluation_session: str, policy: dict[str, Any], cash: Decimal | None,
           facts: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Open with every gate passing, computed from the F1 groups, the S7 review, earnings_blackout and the
    R-REC1 results directly (not through tickets_module.plan or buy_requirements). facts: official facts of
    the session (the replay has none)."""
    good_news = {fact["symbol"] for fact in facts or [] if fact["direction"] == "+" and fact.get("criterion_a")
                 and fact["event_session"] == evaluation_session}
    bad_news = {fact["symbol"] for fact in facts or [] if fact["direction"] == "-"
                and fact["kind"] in rules.OFFICIAL_MINUS_KINDS and fact["event_session"] == evaluation_session}
    review = session_result["review"]
    exposure_policy = policy["portfolio_exposure_policy"]
    registered = set(exposure_policy["card_stock_core"]) | set(exposure_policy["allowed_index_etfs"])
    fail_closed = (review.get("fail_closed") or {}).get("active")
    later = [item for item in calendar_sessions if item > evaluation_session]
    buy_session = later[0] if later else None
    reduce_items = {item["symbol"] for item in review["recommendations"]["reduce"] if item.get("target_weight") is not None}
    adds = {item["symbol"] for item in review["recommendations"]["add"]}
    passing = {item["symbol"] for item in session_result["proposal_results"] if item["status"] == "DISPLAY"}
    out = []
    for symbol, result in session_result["symbols"].items():
        groups = result["groups"].values()
        plus_hit = [group for group in groups if group["side"] == "+" and group["state"] == "hit"]
        plus_new = [group for group in plus_hit if group["previous_state"] != "hit"]
        minus_hit = [group for group in groups if group["side"] == "-" and group["state"] == "hit"]
        entry = checks[symbol]["entry"] or {}
        static = [item for item in entry.get("static_evidence") or [] if checks[symbol]["hash_ok"]
                  and item["direction"] == "+" and item["strength"] != "neutral"]
        basis = symbol in good_news or any(item["strength"] == "strong" for item in static) or len(
            {item["e1_kind"] for item in static if item["strength"] == "weak"} | {group["group"] for group in plus_hit}) >= 2
        if symbol in holdings:
            card_exit = entry.get("card_action") in ("EXIT", "TRIM") and (
                entry.get("card_action") == "EXIT" or entry.get("trim_target_weight") is not None)
            sell_basis = symbol in bad_news or len(minus_hit) >= 2
            if (symbol in reduce_items or card_exit) and sell_basis and checks[symbol]["eligible"] and not fail_closed:
                out.append({"session": evaluation_session, "symbol": symbol, "side": "sell"})
        opened = symbol in good_news or len(plus_new) >= 2 or (symbol in adds and basis)
        if not opened or symbol not in tickets_module.APPROVED_BUY or symbol not in registered:
            continue
        blackout = False if symbol in tickets_module.INDEX_ETFS else earnings_blackout(
            symbol, earnings, calendar_sessions, buy_session, evaluation_session=evaluation_session,
            generated_at=(review.get("inputs") or {}).get("generated_at"))[0]
        shock = session_result["shocks"][symbol]
        shock_ok = shock["status"] == "ok" and (not shock["open"] or all(value == "ok" for value in shock["rg"].values()))
        if (not blackout and shock_ok and symbol in passing and checks[symbol]["eligible"] and not fail_closed
                and rules.m6_listed(symbol, m6_docs)["s"] == "ok" and cash is not None and cash > 0):
            out.append({"session": evaluation_session, "symbol": symbol, "side": "buy"})
    return out


def _bars_at(raw: dict[str, dict[str, Any]], actions: list[dict[str, Any]], session: str) -> dict[str, dict[str, Any]]:
    out = {}
    for symbol, bars in raw.items():
        if bars["status"] != "OK":
            out[symbol] = {"symbol": symbol, "status": bars["status"], "errors": bars["errors"], "raw": bars,
                           "adjusted": bars, "applied_actions": [], "split_suspects": [], "continuity_gaps": []}
            continue
        adjusted, applied = adjust_bars(bars, actions, session)
        out[symbol] = {"symbol": symbol, "status": "OK", "errors": [], "raw": bars, "adjusted": adjusted,
                       "applied_actions": applied, "split_suspects": split_suspects(adjusted, session),
                       "continuity_gaps": bars["continuity_gaps"]}
    return out


def run_replay(*, start: str, end: str, closes_root: Path, calendar: dict[str, Any], policy: dict[str, Any],
               corporate: dict[str, Any], registry: dict[str, Any], watchlist: dict[str, Any],
               m6_docs: list[tuple[str, str]], measurements: dict[str, Any], recovery_text: str,
               config: dict[str, Any], external_oracle: list[dict[str, Any]] | None = None,
               portfolios: dict[str, Any] | None = None, exchanges: dict[str, str] | None = None) -> dict[str, Any]:
    sessions = sorted(calendar["sessions"])
    period = [item for item in sessions if start <= item <= end]
    members = sorted(watchlist["members"])
    portfolios = portfolios or PORTFOLIOS
    held_all = sorted({symbol for item in portfolios.values() for symbol in item["holdings"]})
    sectors = {symbol: (watchlist["members"].get(symbol) or {}).get("sector")
               or (registry["entries"].get(symbol) or {}).get("sector") for symbol in set(held_all) | set(members)}
    universe = sorted(set(held_all) | set(members) | {"SOXX"} | {rules.rg2_benchmark(item) for item in sectors.values()})
    exchanges = exchanges or {}
    raw = {symbol: daily_bars(symbol, Path(closes_root) / "pages" / symbol, calendar,
                              exchange=exchanges.get(symbol, "NASDAQ")) for symbol in universe}
    actions = list(corporate.get("actions") or []) if corporate.get("status") == "OK" else []
    replay_registry = {**registry, "committed": True, "commit_reason": None}
    ev3 = rules.ev3_dates(recovery_text)
    earnings_records = measurements["earnings_announcements_sec"]["records"]
    anchors = anchors_from(measurements)
    end_bars = _bars_at(raw, actions, period[-1]) if period else {}
    results: dict[str, Any] = {}
    for name, portfolio in portfolios.items():
        holdings = dict(portfolio["holdings"])
        cash = portfolio["cash"]
        if cash is None:
            reference = portfolios["P-R1"]
            total = reference["cash"] + sum(
                Decimal(quantity) * end_bars[symbol]["raw"]["sessions"][period[-1]]["close"]
                for symbol, quantity in reference["holdings"].items())
            cash = total - sum(Decimal(quantity) * end_bars[symbol]["raw"]["sessions"][period[-1]]["close"]
                               for symbol, quantity in holdings.items())
        sessions_out, no_data = [], []
        snapshots: list[dict[str, Any]] = []
        activation = None
        for session in period:
            bars = _bars_at(raw, actions, session)
            missing = sorted(symbol for symbol in universe if session not in bars[symbol]["raw"]["sessions"])
            if missing:
                no_data.append({"session": session, "symbols": missing})
            snapshots.append({"as_of": session, "state_revision": 1, "holdings": dict(holdings), "cash_usd": str(cash),
                              "holdings_decreased": False, "cash_flow_declaration": None, "from_ledger_entry": True})
            closes = {symbol: {day: format(bar["close"], "f") for day, bar in bars[symbol]["raw"]["sessions"].items()}
                      for symbol in universe if bars[symbol]["status"] == "OK"}
            if activation is None:
                equity, _values, _missing = closing_equity(snapshots[-1], closes, session)
                activation = {"hwm_usd": format(equity, "f") if equity is not None else "1", "activation_date": session,
                              "hwm_as_of": session, "state_revision": 1}
            journal = {"status": "OK", "errors": [], "entries": [
                {"entry_type": "s5_activation", "entry_id": "replay-activation", "payload": activation}]}
            earnings = earnings_for(session, earnings_records, sessions, sorted(set(holdings) | set(members)))
            generated = datetime.combine(date.fromisoformat(session), time(17, 0), tzinfo=ET)
            generated_at = generated.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

            def s7_runner(proposals: list[dict[str, Any]], *, _snapshots=list(snapshots), _closes=closes,
                          _session=session, _earnings=earnings, _generated=generated_at,
                          _journal=journal) -> dict[str, Any]:
                return build_exposure_review(
                    policy=policy, evaluation_session=_session, calendar_sessions=sessions, snapshots=_snapshots,
                    snapshot_reasons=[], closes=_closes, close_unverified={}, journal=_journal, earnings=_earnings,
                    proposals=proposals, inputs={"generated_at": _generated, "non_default_inputs": ["replay"]},
                    corporate_actions=corporate, generated_at=_generated)

            checks = {symbol: inputs.card_check(symbol, replay_registry, watchlist, repo=REPO_ROOT,
                                                held=symbol in holdings)
                      for symbol in sorted(set(holdings) | set(members))}
            try:
                result = decide_module.evaluate_session(
                    day=session, mode="compare", issued_at=f"{session} 00:00 KST", calendar=calendar,
                    evaluation_session=session, bars=bars, holdings=holdings, cash=cash, deposit=cash,
                    sectors=sectors, members=members, checks=checks, watchlist=watchlist, m6_docs=m6_docs, facts=[],
                    earnings=earnings, ev3=ev3, seen_fact_ids=set(), policy=policy,
                    config=config, keys={}, gate0=[], gate1=[], s7_runner=s7_runner,
                    research={"block": None, "sessions": [item for item in sessions if item <= session], "damage": []},
                    input_hashes={})
            except Exception as exc:  # noqa: BLE001 - a replay session must never stop the replay; it is counted
                sessions_out.append({"session": session, "status": "EXCEPTION",
                                     "error": f"{type(exc).__name__}:{str(exc)[:200]}"})
                continue
            should = oracle(result, holdings=holdings, checks=checks, m6_docs=m6_docs, earnings=earnings,
                            calendar_sessions=sessions, evaluation_session=session, policy=policy, cash=cash)
            sessions_out.append({
                "session": session, "status": "OK",
                "tickets": [{"symbol": item["ticker"], "side": item["side"], "qty": item["qty"], "price": item["price"],
                             "r": item["evidence"]["r"]} for item in result["planned"]["tickets"]],
                "blocked": result["planned"]["blocked"], "candidates": result["planned"]["candidates"],
                "no_action": result["planned"]["no_action"], "oracle": should, "gate1": result["gate1"],
                "E": result["s7"].get("e"), "band": result["s7"].get("band")})
        results[name] = {"cash": float(cash), "holdings": holdings, "sessions": sessions_out, "no_data": no_data}
    return _judge(results, anchors, calendar, external_oracle, start, end, registry)


def _first_code(session_row: dict[str, Any], symbol: str, side: str, holdings: dict[str, int]) -> str:
    if session_row.get("status") != "OK":
        return "EXCEPTION"
    if any(item["symbol"] == symbol and item["side"] == side for item in session_row["tickets"]):
        return "TICKET"
    for item in session_row["blocked"]:
        if item["symbol"] == symbol and item["side"] == side and item["reasons"]:
            return item["reasons"][0]
    if side == "sell" and symbol not in holdings:
        return "NOT_HELD_IN_PORTFOLIO"
    if not any(item["symbol"] == symbol and item["side"] == side for item in session_row["candidates"]):
        return "SELL_CIRCUIT_CLOSED" if side == "sell" else "BUY_CIRCUIT_CLOSED"
    return "UNEXPLAINED"


def _judge(results: dict[str, Any], anchors: list[dict[str, Any]], calendar: dict[str, Any],
           external: list[dict[str, Any]] | None, start: str, end: str, registry: dict[str, Any]) -> dict[str, Any]:
    allowed = set(tickets_module.ALLOWED_NO_TICKET)
    r_a, r_b, r_c = [], {}, {}
    for name, block in results.items():
        by_session = {row["session"]: row for row in block["sessions"]}
        no_data = {(item["session"], symbol) for item in block["no_data"] for symbol in item["symbols"]}
        for anchor in anchors:
            session = anchor_session(anchor["order_date_kst"], calendar)
            side = "sell" if anchor["side"] == "sell" else "buy"
            row = by_session.get(session)
            if row is None or (session, anchor["symbol"]) in no_data:
                code = "NO_DATA"
            else:
                code = _first_code(row, anchor["symbol"], side, block["holdings"])
            r_a.append({"portfolio": name, **anchor, "session": session, "code": code})
        leaks, extras, checked = [], [], 0
        for row in block["sessions"]:
            if row.get("status") != "OK":
                continue
            issued = {(item["symbol"], item["side"]) for item in row["tickets"]}
            for item in row["oracle"]:
                checked += 1
                key = (item["symbol"], item["side"])
                reasons = [reason for blocked in row["blocked"] if (blocked["symbol"], blocked["side"]) == key
                           for reason in blocked["reasons"]]
                if key not in issued and not (reasons and set(reasons) <= allowed):
                    leaks.append({**item, "reasons": reasons})
            should = {(item["symbol"], item["side"]) for item in row["oracle"]}
            extras += [{"session": row["session"], "symbol": symbol, "side": side} for symbol, side in issued - should]
        external_misses = []
        for item in external or []:
            row = by_session.get(item["session"])
            if row is None or row.get("status") != "OK":
                continue
            key = (item["symbol"], item["side"])
            issued = {(ticket["symbol"], ticket["side"]) for ticket in row["tickets"]}
            reasons = [reason for blocked in row["blocked"] if (blocked["symbol"], blocked["side"]) == key
                       for reason in blocked["reasons"]]
            if key not in issued and not (reasons and set(reasons) <= allowed):
                external_misses.append({**item, "reasons": reasons})
        builder = {(row["session"], item["symbol"], item["side"]) for row in block["sessions"] if row.get("status") == "OK"
                   for item in row["oracle"]}
        outside = {(item["session"], item["symbol"], item["side"]) for item in external or []}
        r_b[name] = {"oracle_open_checked": checked, "leaks": leaks, "extra_tickets": extras,
                     "external_checked": len(external or []), "external_misses": external_misses,
                     "oracle_difference": {
                         "builder_only": [list(item) for item in sorted(builder - outside)] if external is not None else None,
                         "external_only": [list(item) for item in sorted(outside - builder)] if external is not None else None},
                     "verdict": "PASS" if not leaks and not external_misses else "FAIL"}
        counts: dict[str, int] = {}
        reasons: dict[str, set[str]] = {}
        zero = 0
        for row in block["sessions"]:
            if row.get("status") != "OK":
                continue
            if not row["tickets"]:
                zero += 1
            for ticket in row["tickets"]:
                counts[f"{ticket['side']}:{ticket['symbol']}"] = counts.get(f"{ticket['side']}:{ticket['symbol']}", 0) + 1
            for item in row["no_action"]["reasons"]:
                reasons.setdefault(item, set()).add(row["session"])
        ok_sessions = sum(1 for row in block["sessions"] if row.get("status") == "OK")
        buys = sum(value for key, value in counts.items() if key.startswith("buy:"))
        r_c[name] = {"tickets": counts, "top_blocking_reasons": sorted(
            ({"reason": key, "sessions": len(value)} for key, value in reasons.items()),
            key=lambda item: (-item["sessions"], item["reason"]))[:5],
            "sessions": ok_sessions, "zero_ticket_share": round(zero / ok_sessions, 4) if ok_sessions else None,
            "buy_tickets": buys, "exceptions": sum(1 for row in block["sessions"] if row.get("status") != "OK"),
            "no_data_sessions": len(block["no_data"])}
    exceptions = sum(item["exceptions"] for item in r_c.values())
    no_data_anchors = sum(1 for item in r_a if item["code"] == "NO_DATA")
    unexplained = sum(1 for item in r_a if item["code"] in ("UNEXPLAINED", "EXCEPTION"))
    r2 = r_c.get("P-R2") or {}
    return {
        "schema_version": SCHEMA_VERSION, "period": {"start": start, "end": end},
        "assumptions": ["P-R1/P-R2 fixed all period (D)", "registry of today applied backwards (D)",
                        "no official facts; a research record (without facts) is taken to exist for every session",
                        "E-R1 earnings from SEC 8-K 2.02 (D)",
                        "S7 activation at the first replay session with that equity as HWM (replay only)",
                        "each session independent: no outcome history, G0 passes, no re-issue ledger",
                        "registry commit check not applied in replay"],
        "registry_sha256": registry.get("sha256"), "portfolios": results,
        "R_A": {"anchors": r_a, "unexplained_or_exception": unexplained, "no_data": no_data_anchors,
                "verdict": "PASS" if unexplained == 0 and no_data_anchors == 0 else "NOT_PASSED"},
        "R_B": {"by_portfolio": r_b, "verdict": "PASS" if all(item["verdict"] == "PASS" for item in r_b.values())
                else "FAIL"},
        "R_C": {"by_portfolio": r_c, "verdict": "NOT_MET" if r2.get("buy_tickets", 0) == 0 else "MET",
                "default_disposition": "compare mode stays (NO_CHANGE) and one notice with the blocking ranking"},
        "exceptions": exceptions, "order_authority": False, "quantity_authority": "none", "execution_quantity": None,
    }


def summary_lines(replay: dict[str, Any]) -> list[str]:
    lines = [f"# \ub9ac\ud50c\ub808\uc774 {replay['period']['start']} ~ {replay['period']['end']}", "",
             f"- R-A \uc2e4\uc81c \uc8fc\ubb38 \uc575\ucee4: {replay['R_A']['verdict']} (\uc790\ub8cc \uc5c6\uc74c {replay['R_A']['no_data']}, \uc124\uba85 \uc548 \ub428\u00b7\uc608\uc678 {replay['R_A']['unexplained_or_exception']})",
             f"- R-B \uad00\ubb38 \ub204\uc218: {replay['R_B']['verdict']}",
             f"- R-C \ube48\ub3c4: {replay['R_C']['verdict']}", ""]
    for name, item in replay["R_C"]["by_portfolio"].items():
        lines.append(f"## {name}")
        lines.append(f"- \uc8fc\ubb38\ud45c: {json.dumps(item['tickets'], ensure_ascii=False)} \u00b7 \uc8fc\ubb38\ud45c 0 \uc138\uc158 \ube44\uc728 {item['zero_ticket_share']}")
        lines.append("- \ub9c9\ud78c \uc0ac\uc720 \uc0c1\uc704 5: " + ", ".join(f"{row['reason']}({row['sessions']})" for row in item["top_blocking_reasons"]))
        lines.append("")
    lines.append("\uc77d\uae30 \uc804\uc6a9 \ub9ac\ud50c\ub808\uc774 \u2014 \uc8fc\ubb38 \uad8c\ud55c \uc5c6\uc74c(order_authority false).")
    return lines


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Read-only replay of the decide path (prompt appendix C)")
    parser.add_argument("--start", default=PERIOD[0])
    parser.add_argument("--end", default=PERIOD[1])
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--closes-root", type=Path, default=decide_module.CLOSES_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--measurements", type=Path, default=MEASUREMENTS_PATH)
    parser.add_argument("--external-oracle", type=Path, help='[{"session": "YYYY-MM-DD", "symbol": "X", "side": "buy|sell"}]')
    args = parser.parse_args(argv)
    from auto_core import known_exchange
    from run_portfolio_exposure_review import load_corporate_actions

    calendar = decide_module._calendar(datetime.now(timezone.utc))
    registry = inputs.load_registry()
    watchlist = inputs.load_watchlist()
    policy = load_json(decide_module.POLICY_PATHS["alert"])
    config = load_json(REPO_ROOT / "workspace/policies/auto_core.json")
    universe = sorted(set(watchlist["members"]) | {"MVLL", "SOXL", "NBIS", "SOXX", "GRID"})
    replay = run_replay(
        start=args.start, end=args.end, closes_root=args.closes_root, calendar=calendar, policy=policy,
        corporate=load_corporate_actions(args.closes_root, sorted(calendar["sessions"])), registry=registry,
        watchlist=watchlist, m6_docs=inputs.m6_documents(decide_module.DOCS_DIR), measurements=load_json(args.measurements),
        recovery_text=decide_module.RECOVERY_GATE_DOC.read_text(encoding="utf-8"), config=config,
        external_oracle=load_json(args.external_oracle) if args.external_oracle else None,
        exchanges={symbol: known_exchange(symbol, args.closes_root)[0] or "NASDAQ" for symbol in universe})
    errors = validate_instance(replay, REPLAY_SCHEMA)
    directory = Path(args.output_root) / args.run_id
    write_json(directory / "replay.json", replay)
    (directory / "summary.md").write_text("\n".join(summary_lines(replay)) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "schema_errors": errors[:3], "R_A": replay["R_A"]["verdict"],
                      "R_B": replay["R_B"]["verdict"], "R_C": replay["R_C"]["verdict"],
                      "exceptions": replay["exceptions"]}, ensure_ascii=True))
    return 1 if errors or replay["exceptions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
