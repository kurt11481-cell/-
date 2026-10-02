#!/usr/bin/env python3
"""Pure validation and split adjustment of the official corporate-action record (S7, K2).

No file, clock or network access: the caller reads corporate-actions.json and passes the parsed
document and the run's session calendar. The record is the runtime input contract for the policy basis
`sox_equivalent.return_basis = split_adjusted_regular_session_close`. Adjustment is backward and anchored
to the latest raw close: every close before an effective session is multiplied by old_shares/new_shares.
The raw close history is never rewritten; adjusted closes are built fresh on every run.

Nothing here writes or edits a record. Records are added only by Cowork, from an official issuer
source plus the Kiwoom adjusted-price flag.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from regular_session_close_history import SYMBOL


SCHEMA_VERSION = "corporate-actions-1.0"
ARTIFACT_TYPE = "CORPORATE_ACTIONS"
FILE_NAME = "corporate-actions.json"
ACTION_SPLIT = "SPLIT"
STATUS_MISSING = "MISSING"
STATUS_OK = "OK"
STATUS_INVALID = "INVALID"
INVALID_REASON = "CORPORATE_ACTIONS_INVALID"
# Kiwoom pages end with a pagination marker "1f" in upd_stkpc_tp; it is not an adjustment flag.
PAGE_END_MARKER = "1f"
UPD_RT_TOLERANCE = Decimal("0.005")
HUNDRED = Decimal("100")
DATE_TEXT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DOCUMENT_KEYS = {"schema_version", "artifact_type", "actions"}
ACTION_KEYS = {"symbol", "action_type", "effective_session", "new_shares", "old_shares", "official_source",
               "kiwoom_crosscheck", "recorded_by", "recorded_at"}
SOURCE_KEYS = {"issuer", "url", "published_date"}
CROSSCHECK_KEYS = {"api_id", "adjusted", "dt", "upd_stkpc_tp", "upd_rt"}


def _date(value: Any) -> date | None:
    """Strict YYYY-MM-DD only: dates are compared as text, so no other spelling may pass."""
    if not isinstance(value, str) or DATE_TEXT.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def price_factor(action: dict[str, Any]) -> Decimal:
    """Multiplier for closes before the effective session: old_shares / new_shares."""
    return Decimal(action["old_shares"]) / Decimal(action["new_shares"])


def _action_errors(index: int, action: Any, calendar_sessions: set[str]) -> list[str]:
    tag = f"CORPORATE_ACTION_INVALID:{index}"
    if not isinstance(action, dict) or set(action) != ACTION_KEYS:
        return [f"{tag}:KEYS"]
    errors: list[str] = []
    symbol = action["symbol"]
    if not isinstance(symbol, str) or SYMBOL.fullmatch(symbol) is None:
        errors.append(f"{tag}:SYMBOL")
    if action["action_type"] != ACTION_SPLIT:
        errors.append(f"{tag}:ACTION_TYPE")
    shares_ok = _positive_int(action["new_shares"]) and _positive_int(action["old_shares"])
    if not shares_ok or action["new_shares"] == action["old_shares"]:
        errors.append(f"{tag}:SHARES")
    effective = action["effective_session"]
    if _date(effective) is None or effective not in calendar_sessions:
        errors.append(f"{tag}:EFFECTIVE_SESSION_NOT_IN_CALENDAR")
        effective = None
    source = action["official_source"]
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        errors.append(f"{tag}:OFFICIAL_SOURCE_KEYS")
    else:
        if not _text(source["issuer"]):
            errors.append(f"{tag}:OFFICIAL_SOURCE_ISSUER")
        if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
            errors.append(f"{tag}:OFFICIAL_SOURCE_URL")
        published = _date(source["published_date"])
        if published is None or (effective is not None and published > date.fromisoformat(effective)):
            errors.append(f"{tag}:OFFICIAL_SOURCE_PUBLISHED_DATE")
    crosscheck = action["kiwoom_crosscheck"]
    if not isinstance(crosscheck, dict) or set(crosscheck) != CROSSCHECK_KEYS or any(
            not isinstance(value, str) for value in crosscheck.values()):
        errors.append(f"{tag}:KIWOOM_CROSSCHECK_KEYS")
    else:
        if effective is None or crosscheck["dt"] != effective.replace("-", ""):
            errors.append(f"{tag}:KIWOOM_CROSSCHECK_DT")
        flag = crosscheck["upd_stkpc_tp"].strip()
        if not flag or flag == PAGE_END_MARKER:
            errors.append(f"{tag}:KIWOOM_CROSSCHECK_UPD_STKPC_TP")
        rate_ok = False
        if shares_ok and action["new_shares"] != action["old_shares"]:
            try:
                reported = Decimal(crosscheck["upd_rt"])
                rate_ok = reported.is_finite() and abs(reported - (price_factor(action) - 1) * HUNDRED) <= UPD_RT_TOLERANCE
            except (InvalidOperation, ValueError):
                pass
        if not rate_ok:
            errors.append(f"{tag}:KIWOOM_CROSSCHECK_UPD_RT")
    if not _text(action["recorded_by"]):
        errors.append(f"{tag}:RECORDED_BY")
    if _date(action["recorded_at"]) is None:
        errors.append(f"{tag}:RECORDED_AT")
    return errors


def validate_corporate_actions(document: Any, calendar_sessions: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """(actions, errors). Any error makes the whole file INVALID: the returned actions are then empty."""
    if not isinstance(document, dict) or set(document) != DOCUMENT_KEYS:
        return [], ["CORPORATE_ACTIONS_DOCUMENT_KEYS"]
    errors: list[str] = []
    if document["schema_version"] != SCHEMA_VERSION:
        errors.append("CORPORATE_ACTIONS_SCHEMA_VERSION")
    if document["artifact_type"] != ARTIFACT_TYPE:
        errors.append("CORPORATE_ACTIONS_ARTIFACT_TYPE")
    actions = document["actions"]
    if not isinstance(actions, list):
        return [], errors + ["CORPORATE_ACTIONS_ACTIONS_NOT_LIST"]
    sessions = set(calendar_sessions)
    seen: set[tuple[Any, Any]] = set()
    for index, action in enumerate(actions):
        errors.extend(_action_errors(index, action, sessions))
        if isinstance(action, dict) and set(action) == ACTION_KEYS:
            key = (action["symbol"], action["effective_session"])
            if key in seen:
                errors.append(f"CORPORATE_ACTION_INVALID:{index}:DUPLICATE")
            seen.add(key)
    return ([] if errors else [dict(action) for action in actions]), errors


def adjust_closes(closes: dict[str, dict[str, str]], actions: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """New {symbol: {session: close}} with every close before each effective session rescaled.

    Several records for one symbol multiply. A close that is not a finite Decimal is kept as is, so a
    gap stays a gap. The input dictionaries are not modified.
    """
    adjusted = {symbol: dict(per_session) for symbol, per_session in closes.items()}
    for symbol in {action["symbol"] for action in actions}:
        per_session = adjusted.get(symbol)
        if not per_session:
            continue
        mine = [action for action in actions if action["symbol"] == symbol]
        for session, value in list(per_session.items()):
            # old/new products are kept as integers and divided once, so 300 x 1/3 stays exactly 100.
            numerator, denominator = 1, 1
            for action in mine:
                if session < action["effective_session"]:
                    numerator *= action["old_shares"]
                    denominator *= action["new_shares"]
            if numerator == denominator:
                continue
            try:
                close = Decimal(str(value))
            except (InvalidOperation, ValueError):
                continue
            if close.is_finite():
                per_session[session] = format(close * numerator / denominator, "f")
    return adjusted


def applicable_actions(actions: list[dict[str, Any]], evaluation_session: str) -> list[dict[str, Any]]:
    """Records already in effect at the evaluation session (a later split is not visible in its closes)."""
    return [action for action in actions if action["effective_session"] <= evaluation_session]


def applied_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"symbol": action["symbol"], "effective_session": action["effective_session"],
             "new_shares": action["new_shares"], "old_shares": action["old_shares"],
             "price_factor": format(price_factor(action), "f")} for action in actions]


def split_reconciliation_symbols(snapshot: dict[str, Any], held_symbols: list[str], session: str,
                                 actions: list[dict[str, Any]]) -> list[str]:
    """Reasons a snapshot cannot value `session`: it predates a split of a symbol it holds.

    Holdings are never rescaled by the split ratio (no quantity inference); the session's equity is
    unverified until a later reconciliation confirms the post-split quantity.
    """
    as_of = snapshot.get("as_of")
    if not isinstance(as_of, str):
        return []
    return [f"SPLIT_RECONCILIATION_REQUIRED:{action['symbol']}:{action['effective_session']}"
            for action in sorted(actions, key=lambda item: (item["symbol"], item["effective_session"]))
            if action["symbol"] in held_symbols and as_of < action["effective_session"] <= session]
