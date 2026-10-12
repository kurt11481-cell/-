#!/usr/bin/env python3
"""Decision journal: human confirmations only (S5 activation, line review done, peak review done,
card decisions and the user's own decision on a card).

HWM, line breaches, pauses and instrument peaks are recomputed on every run (user decision P1); this
journal stores only what a person confirmed. Every S5 entry comes from a proposal built from one
portfolio exposure review, every card entry from a card that passed validate_holding_card (or from
the user's own decision on a recorded card decision). Each is written only with that proposal's
confirmation code. Scores are never stored here: score_decision_journal.py reads this file only.

propose-activation / propose-line-review / propose-peak-review   build a proposal; never write the journal
propose-card            card + fact pack -> one proposal that records one entry per recordable position
propose-user-decision   the user's own decision on a recorded card decision (a correction is a new entry)
show    render the proposal for the user
apply   append the entry. Run apply only in Cowork after the user typed "confirm <code>" for that
        proposal in the current conversation, or from the user's own terminal
        (--confirmed-via USER_TERMINAL). Agents, scheduled tasks, Claude Code, Codex and Judge
        sessions never run it, and never type or guess the code.
verify  check the journal hash chain

Redesign T2 F7: in recording mode the auto-core appends core_decision, order_ticket and ticket_outcome
entries through append_auto_core_entries (confirmation_method AUTO_CORE, no code, no user message). The
human propose/apply path above never accepts AUTO_CORE.

The journal has no order or quantity authority and never touches portfolio state, policy or the
reconciliation ledger.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from portfolio_exposure import (
    JOURNAL_ACTIVATION, JOURNAL_LINE_REVIEW, JOURNAL_PEAK_REVIEW, review_activation_blockers, review_content_hash,
)
from validate_holding_card import validate_card
from validation_common import canonical_hash, load_json, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
JOURNAL_SCHEMA = SKILL_ROOT / "schemas/portfolio-review-journal.schema.json"
PAYLOAD_SCHEMA = SKILL_ROOT / "schemas/portfolio-review-journal-payload.schema.json"
PROPOSAL_SCHEMA = SKILL_ROOT / "schemas/portfolio-review-journal-proposal.schema.json"
REVIEW_SCHEMA = SKILL_ROOT / "schemas/portfolio-exposure-review.schema.json"
LOCALE_PATH = SKILL_ROOT / "assets/locales/portfolio-exposure-ko-KR.json"
DEFAULT_JOURNAL_PATH = "stock-strategy-system/decision_journal.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/exposure-review/journal-proposals"
PROPOSAL_FILE = "journal_proposal.json"
JOURNAL_SCHEMA_VERSION = "decision-journal-1.0"
PROPOSAL_SCHEMA_VERSION = "decision-journal-proposal-1.0"
JOURNAL_TYPE = "DECISION_JOURNAL"
PROPOSAL_TYPE = "DECISION_JOURNAL_ENTRY"
JOURNAL_CARD_DECISION = "card_decision"
JOURNAL_CARD_USER_DECISION = "card_user_decision"
S5_ENTRY_TYPES = (JOURNAL_ACTIVATION, JOURNAL_LINE_REVIEW, JOURNAL_PEAK_REVIEW)
CARD_ENTRY_TYPES = (JOURNAL_CARD_DECISION, JOURNAL_CARD_USER_DECISION)
CONFIRMATION_METHODS = ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL")
# Redesign T2 F7: entries the auto-core appends in recording mode (never through propose/apply above).
JOURNAL_CORE_DECISION = "core_decision"
JOURNAL_ORDER_TICKET = "order_ticket"
JOURNAL_TICKET_OUTCOME = "ticket_outcome"
AUTO_CORE_ENTRY_TYPES = (JOURNAL_CORE_DECISION, JOURNAL_ORDER_TICKET, JOURNAL_TICKET_OUTCOME)
AUTO_CORE_METHOD = "AUTO_CORE"
TICKET_AUTHORITY = {"order_authority": False, "quantity_authority": "ORDER_TICKET_HUMAN_ENTRY",
                    "execution_quantity": None}
GENESIS_HASH = "0" * 64
PROPOSAL_MAX_AGE_SECONDS = 3600
CONCLUSIONS = ("continue", "other")
CARD_DECISION_FIELDS = ("card_id", "card_sha256", "fact_pack_sha256", "decision_id", "ticker", "decision_as_of",
                        "decision_session", "analysis_action", "sidecar_action", "conviction", "reference_close",
                        "evidence_grade", "card_state_revision")
USER_DECISION_FIELDS = ("decision_id", "ticker", "user_action", "effective_session", "user_note")
# What a card_decision proposal carries: the entry payloads are expanded one entry per position at apply.
CARD_PROPOSAL_PAYLOAD_FIELDS = ("card_id", "card_sha256", "fact_pack_sha256", "decisions")
PAYLOAD_FIELDS = {
    JOURNAL_ACTIVATION: ("activation_date", "hwm_usd", "hwm_as_of", "hwm_policy_initial_usd", "hwm_difference_usd",
                         "state_revision", "window_start", "window_end", "close_basis"),
    JOURNAL_LINE_REVIEW: ("line_id", "hwm", "breach_date", "review_status", "conclusion", "conclusion_note"),
    JOURNAL_PEAK_REVIEW: ("symbol", "peak", "peak_date", "breach_date", "review_status"),
    JOURNAL_CARD_DECISION: CARD_DECISION_FIELDS,
    JOURNAL_CARD_USER_DECISION: USER_DECISION_FIELDS,
    JOURNAL_CORE_DECISION: ("run_day_kst", "buy_session", "decision_mode", "no_action", "blocked_reasons",
                            "ticket_ids", "commit_sha", "decision_sha256"),
    JOURNAL_ORDER_TICKET: ("ticket_id", "ticker", "side", "order_type", "price", "qty", "amount", "buy_session",
                           "decision_key", "price_rule", "evidence_r", "authority"),
    JOURNAL_TICKET_OUTCOME: ("ticket_id", "ticker", "side", "outcome_state", "filled_qty", "average_fill_price",
                             "decision_key", "classified_on"),
}
# Card action -> the sidecar DECISION_ACTIONS name it is scored under (G3 decision 4, 2026-09-30).
# A card's TRIM/EXIT reason_tag is already a sidecar name; HOLD depends on review_required.
ALLOWED_SIDECAR_ACTIONS = {
    "ADD": ("ADD_REVIEW",),
    "HOLD": ("HOLD_CORE", "HOLD_REVIEW_REQUIRED"),
    "TRIM": ("TRIM_CONCENTRATION", "TRIM_RISK", "TRIM_TECHNICAL", "TRIM_PROFIT", "TRIM_VALUATION"),
    "EXIT": ("EXIT_HARD_STOP", "EXIT_THESIS", "ROTATE_REVIEW", "KEEP_CASH"),
}
DECIMAL_TEXT = re.compile(r"[0-9]+(\.[0-9]+)?")
MIN_DECISION_ID_PREFIX = 8
KST = timezone(timedelta(hours=9))


class JournalError(ValueError):
    """Fail-closed journal error with a public reason code."""


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def load_journal(path: Path) -> dict[str, Any]:
    """Read and verify the journal. Never raises for a missing or bad file."""
    path = Path(path)
    result: dict[str, Any] = {"status": "MISSING", "entries": [], "errors": [], "head_sha256": GENESIS_HASH}
    if not path.is_file():
        return result
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {**result, "status": "CORRUPT", "errors": ["JOURNAL_NOT_JSON"]}
    errors = validate_instance(document, JOURNAL_SCHEMA)
    if errors:
        return {**result, "status": "CORRUPT", "errors": ["JOURNAL_SCHEMA_INVALID"] + errors[:5]}
    previous = GENESIS_HASH
    for index, entry in enumerate(document["entries"]):
        if entry["previous_entry_sha256"] != previous or entry["sequence"] != index + 1:
            return {**result, "status": "CORRUPT", "errors": [f"JOURNAL_CHAIN_BROKEN:{index + 1}"]}
        previous = canonical_hash(entry)
    inconsistent = entry_inconsistencies(document["entries"])
    if inconsistent:
        return {**result, "status": "CORRUPT", "errors": inconsistent}
    return {"status": "OK", "entries": document["entries"], "errors": [], "head_sha256": previous}


def _entry_inconsistency(entry: dict[str, Any], decisions: dict[str, dict[str, Any]]) -> str | None:
    """Reason code if one chained entry contradicts itself or an earlier entry, else None.

    The chain commits every entry except the last to the entry after it, so a hand edit of the last
    entry changes only the head. Every rule here is one apply_proposal_entries already enforces when
    it writes the entry, recomputed from the entry's own fields. Rules that need another source
    (card file, price history) are not checked here."""
    entry_type, payload = entry["entry_type"], entry["payload"]
    # Redesign T2 F7: an auto-core entry has no confirmation code or user message; it is checked here, before
    # the code checks below (which would otherwise fail on the null message).
    if entry["confirmation_method"] == AUTO_CORE_METHOD or entry_type in AUTO_CORE_ENTRY_TYPES:
        return _auto_core_inconsistency(entry)
    code = entry["confirm_code"]
    if not isinstance(code, str) or not isinstance(entry["user_message"], str):
        return "CONFIRMATION_FIELDS_INVALID"
    if code not in entry["user_message"].upper():
        return "CONFIRM_CODE_NOT_IN_USER_MESSAGE"
    expected_fields = CARD_DECISION_FIELDS if entry_type == JOURNAL_CARD_DECISION else PAYLOAD_FIELDS[entry_type]
    if sorted(payload) != sorted(expected_fields):
        return "PAYLOAD_FIELDS_INVALID"
    # A card proposal's code is not derived from a decision id (one proposal appends several entries).
    if entry_type != JOURNAL_CARD_DECISION and code != entry["entry_id"][:8].upper():
        return "CONFIRM_CODE_ENTRY_ID_MISMATCH"
    session = date.fromisoformat(entry["evaluation_session"])
    if entry_type == JOURNAL_ACTIVATION:
        if not entry["evaluation_session"] == payload["activation_date"] == payload["window_end"]:
            return "ACTIVATION_SESSION_MISMATCH"
        if not (date.fromisoformat(payload["window_start"]) <= date.fromisoformat(payload["hwm_as_of"])
                <= date.fromisoformat(payload["window_end"])):
            return "ACTIVATION_HWM_DATE_OUTSIDE_WINDOW"
        if Decimal(payload["hwm_usd"]) - Decimal(payload["hwm_policy_initial_usd"]) != Decimal(
                payload["hwm_difference_usd"]):
            return "ACTIVATION_HWM_DIFFERENCE_MISMATCH"
    elif entry_type == JOURNAL_LINE_REVIEW:
        if date.fromisoformat(payload["breach_date"]) > session:
            return "LINE_REVIEW_BREACH_AFTER_SESSION"
    elif entry_type == JOURNAL_PEAK_REVIEW:
        if not date.fromisoformat(payload["peak_date"]) <= date.fromisoformat(payload["breach_date"]) <= session:
            return "PEAK_REVIEW_DATES_OUT_OF_ORDER"
    elif entry_type == JOURNAL_CARD_DECISION:
        if payload["decision_id"] != entry["entry_id"] or payload["decision_id"] != card_decision_id(
                payload["card_sha256"], payload["ticker"]):
            return "CARD_DECISION_ID_MISMATCH"
        if entry["review_id"] != payload["card_sha256"]:
            return "CARD_REVIEW_ID_MISMATCH"
        if entry["evaluation_session"] != payload["decision_session"]:
            return "CARD_SESSION_MISMATCH"
        if payload["sidecar_action"] not in ALLOWED_SIDECAR_ACTIONS.get(payload["analysis_action"], ()):
            return "CARD_SIDECAR_ACTION_NOT_ALLOWED"
        if payload["decision_id"] in decisions:
            return "CARD_DECISION_DUPLICATE"
    elif entry_type == JOURNAL_CARD_USER_DECISION:
        decision = decisions.get(payload["decision_id"])
        if decision is None or decision["ticker"] != payload["ticker"]:
            return "USER_DECISION_REFERENCE_INVALID"
        if entry["review_id"] != decision["card_sha256"]:
            return "USER_DECISION_REVIEW_ID_MISMATCH"
        if entry["evaluation_session"] != payload["effective_session"] or (
                payload["effective_session"] < decision["decision_session"]):
            return "USER_DECISION_SESSION_INCONSISTENT"
    return None


def _auto_core_inconsistency(entry: dict[str, Any]) -> str | None:
    """Self-consistency of one auto-core entry (F7): method, null code and message, exact payload fields."""
    if entry["confirmation_method"] != AUTO_CORE_METHOD or entry["entry_type"] not in AUTO_CORE_ENTRY_TYPES:
        return "AUTO_CORE_ENTRY_TYPE_OR_METHOD_INVALID"
    if entry["confirm_code"] is not None or entry["user_message"] is not None:
        return "AUTO_CORE_CONFIRMATION_FIELDS_NOT_NULL"
    payload = entry["payload"]
    if sorted(payload) != sorted(PAYLOAD_FIELDS[entry["entry_type"]]):
        return "PAYLOAD_FIELDS_INVALID"
    if entry["entry_type"] == JOURNAL_ORDER_TICKET and payload["authority"] != TICKET_AUTHORITY:
        return "ORDER_TICKET_AUTHORITY_INVALID"
    if entry["entry_type"] == JOURNAL_CORE_DECISION and entry["review_id"] != payload["decision_sha256"]:
        return "CORE_DECISION_REVIEW_ID_MISMATCH"
    return None


def entry_inconsistencies(entries: list[dict[str, Any]]) -> list[str]:
    """JOURNAL_ENTRY_INCONSISTENT:<sequence>:<reason> for the first entry that contradicts itself, else []."""
    decisions: dict[str, dict[str, Any]] = {}
    for entry in entries:
        try:
            reason = _entry_inconsistency(entry, decisions)
        except (KeyError, TypeError, ValueError, ArithmeticError):
            reason = "ENTRY_MALFORMED"
        if reason is not None:
            return [f"JOURNAL_ENTRY_INCONSISTENT:{entry.get('sequence')}:{reason}"]
        if entry["entry_type"] == JOURNAL_CARD_DECISION:
            decisions[entry["payload"]["decision_id"]] = entry["payload"]
    return []


def proposal_content_hash(proposal: dict[str, Any]) -> str:
    return canonical_hash({key: value for key, value in proposal.items() if key not in {"proposal_id", "confirm_code"}})


def _checked_review(review: Any) -> dict[str, Any]:
    if not isinstance(review, dict) or validate_instance(review, REVIEW_SCHEMA):
        raise JournalError("REVIEW_SCHEMA_INVALID")
    if review_content_hash(review) != review.get("review_id"):
        raise JournalError("REVIEW_HASH_MISMATCH")
    return review


def activation_payload(review: dict[str, Any]) -> dict[str, Any]:
    candidate = review.get("activation_candidate")
    if review.get("activation") is not None:
        raise JournalError("S5_ALREADY_ACTIVATED")
    if not isinstance(candidate, dict) or candidate.get("status") != "READY":
        raise JournalError("ACTIVATION_CANDIDATE_NOT_READY")
    # Checked again here, from the review's own fail-closed triggers and inputs: activation is
    # proposed only when nothing but "not activated / no journal yet" is open and inputs are default.
    blockers = review_activation_blockers(review)
    if blockers:
        raise JournalError("ACTIVATION_BLOCKED: " + ", ".join(blockers[:5]))
    return {"activation_date": candidate["activation_date"], "hwm_usd": candidate["hwm_usd"],
            "hwm_as_of": candidate["hwm_as_of"], "hwm_policy_initial_usd": candidate["hwm_policy_initial_usd"],
            "hwm_difference_usd": candidate["hwm_difference_usd"], "state_revision": candidate["state_revision"],
            "window_start": candidate["window_start"], "window_end": candidate["window_end"],
            "close_basis": review["close_basis"]["definition"]}


def line_review_payload(review: dict[str, Any], line_id: str, conclusion: str, note: str) -> dict[str, Any]:
    if conclusion not in CONCLUSIONS:
        raise JournalError("LINE_REVIEW_CONCLUSION_INVALID")
    events = [event for event in review["review_lines"]["open_events"] if event["line_id"] == line_id]
    if len(events) != 1:
        raise JournalError("LINE_REVIEW_OPEN_EVENT_NOT_FOUND" if not events else "LINE_REVIEW_OPEN_EVENT_AMBIGUOUS")
    event = events[0]
    return {"line_id": line_id, "hwm": event["hwm"], "breach_date": event["breach_date"],
            "review_status": "completed", "conclusion": conclusion, "conclusion_note": note}


def peak_review_payload(review: dict[str, Any], symbol: str) -> dict[str, Any]:
    events = [event for item in review["peak_reviews"] if item["symbol"] == symbol for event in item["open_events"]]
    if len(events) != 1:
        raise JournalError("PEAK_REVIEW_OPEN_EVENT_NOT_FOUND" if not events else "PEAK_REVIEW_OPEN_EVENT_AMBIGUOUS")
    event = events[0]
    return {"symbol": symbol, "peak": event["peak"], "peak_date": event["peak_date"],
            "breach_date": event["breach_date"], "review_status": "completed"}


def build_proposal(*, entry_type: str, payload: dict[str, Any], review: dict[str, Any], journal: dict[str, Any],
                   journal_path: str = DEFAULT_JOURNAL_PATH, now: datetime) -> dict[str, Any]:
    """One non-mutating proposal. A corrupt journal is never extended."""
    if entry_type not in S5_ENTRY_TYPES:
        raise JournalError("JOURNAL_ENTRY_TYPE_INVALID")
    if journal["status"] == "CORRUPT":
        raise JournalError("JOURNAL_CORRUPT")
    # A review produced by the runner records the journal it read; it must be this journal, unchanged.
    reviewed_head = (review.get("inputs") or {}).get("journal_head_sha256")
    if reviewed_head is not None and reviewed_head != journal["head_sha256"]:
        raise JournalError("REVIEW_JOURNAL_HEAD_MISMATCH")
    if entry_type == JOURNAL_ACTIVATION and any(
            entry.get("entry_type") == JOURNAL_ACTIVATION for entry in journal["entries"]):
        raise JournalError("S5_ALREADY_ACTIVATED")
    return _proposal_document(entry_type=entry_type, payload=payload, review_id=review["review_id"],
                              evaluation_session=review["evaluation_session"], journal=journal,
                              journal_path=journal_path, now=now)


def _proposal_document(*, entry_type: str, payload: dict[str, Any], review_id: str, evaluation_session: str,
                       journal: dict[str, Any], journal_path: str, now: datetime) -> dict[str, Any]:
    proposal: dict[str, Any] = {
        "schema_version": PROPOSAL_SCHEMA_VERSION, "proposal_type": PROPOSAL_TYPE,
        "proposal_id": "", "confirm_code": "", "entry_type": entry_type, "payload": payload,
        "review_id": review_id, "evaluation_session": evaluation_session,
        "generated_at": _utc_iso(now), "expires_at": _utc_iso(now + timedelta(seconds=PROPOSAL_MAX_AGE_SECONDS)),
        "journal_path": journal_path, "expected_journal_head_sha256": journal["head_sha256"],
        "expected_entry_count": len(journal["entries"]),
        "auto_apply": False, "order_authority": False, "quantity_authority": "none",
    }
    proposal["proposal_id"] = proposal_content_hash(proposal)
    proposal["confirm_code"] = proposal["proposal_id"][:8].upper()
    return proposal


def _decimal_text(value: Any) -> str | None:
    """A positive finite number as plain decimal text, or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return format(number, "f") if number.is_finite() and number > 0 else None


def card_decision_id(card_sha256: str, ticker: str) -> str:
    return canonical_hash({"card_sha256": card_sha256, "ticker": ticker})


def sidecar_action_for(position: dict[str, Any]) -> str:
    """Map one card position to the sidecar action name it is scored under (G3 decision 4)."""
    action = position.get("action")
    if action == "HOLD":
        return "HOLD_REVIEW_REQUIRED" if position.get("review_required") is True else "HOLD_CORE"
    if action == "ADD":
        return "ADD_REVIEW"
    if action in ("TRIM", "EXIT") and position.get("reason_tag") in ALLOWED_SIDECAR_ACTIONS[action]:
        return position["reason_tag"]
    raise JournalError(f"CARD_ACTION_NOT_MAPPABLE:{position.get('ticker')}")


def card_decision_payloads(card: dict[str, Any], fact_pack: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], str]:
    """(entry payloads sorted by ticker, withheld tickers, card sha256) for a card the validator accepted."""
    errors = validate_card(card, fact_pack)
    if errors:
        raise JournalError("CARD_INVALID: " + ", ".join(errors[:5]))
    source, status = fact_pack["source"], fact_pack.get("status") or {}
    session = source.get("expected_completed_us_session")
    if not isinstance(session, str) or not session:
        raise JournalError("CARD_SESSION_MISSING")
    card_sha256 = canonical_hash(card)
    payloads: list[dict[str, Any]] = []
    withheld: list[str] = []
    for position in sorted(card["positions"], key=lambda item: item["ticker"]):
        ticker = position["ticker"]
        if position["action"] == "WITHHELD":
            withheld.append(ticker)  # a withheld judgment has nothing to score
            continue
        close = fact_pack["tickers"][ticker].get("confirmed_close")
        close_text = _decimal_text(close.get("price_usd")) if isinstance(close, dict) and close.get(
            "session") == session else None
        revision = status.get("state_revision")
        payloads.append({
            "card_id": card["card_id"], "card_sha256": card_sha256, "fact_pack_sha256": card["fact_pack_sha256"],
            "decision_id": card_decision_id(card_sha256, ticker), "ticker": ticker,
            "decision_as_of": source["decision_as_of"], "decision_session": session,
            "analysis_action": position["action"], "sidecar_action": sidecar_action_for(position),
            "conviction": position["conviction"], "reference_close": close_text,
            "evidence_grade": status.get("evidence_grade") if isinstance(status.get("evidence_grade"), str) else None,
            "card_state_revision": revision if isinstance(revision, int) and not isinstance(revision, bool) else None,
        })
    if not payloads:
        raise JournalError("CARD_HAS_NO_RECORDABLE_POSITION")
    return payloads, withheld, card_sha256


def build_card_proposal(*, card: dict[str, Any], fact_pack: dict[str, Any], journal: dict[str, Any],
                        journal_path: str = DEFAULT_JOURNAL_PATH, now: datetime) -> dict[str, Any]:
    """One non-mutating proposal: one entry per recordable position of one validated card."""
    if journal["status"] == "CORRUPT":
        raise JournalError("JOURNAL_CORRUPT")
    payloads, _withheld, card_sha256 = card_decision_payloads(card, fact_pack)
    if any((entry.get("payload") or {}).get("card_sha256") == card_sha256 for entry in journal["entries"]
           if entry.get("entry_type") == JOURNAL_CARD_DECISION):
        raise JournalError("CARD_ALREADY_RECORDED")
    payload = {"card_id": card["card_id"], "card_sha256": card_sha256,
               "fact_pack_sha256": card["fact_pack_sha256"], "decisions": payloads}
    return _proposal_document(entry_type=JOURNAL_CARD_DECISION, payload=payload, review_id=card_sha256,
                              evaluation_session=payloads[0]["decision_session"], journal=journal,
                              journal_path=journal_path, now=now)


def find_card_decision(journal: dict[str, Any], decision_id: str) -> dict[str, Any]:
    """The recorded card_decision entry for a full id or a unique prefix of at least 8 characters."""
    text = decision_id.strip().lower()
    if len(text) < MIN_DECISION_ID_PREFIX:
        raise JournalError("DECISION_ID_TOO_SHORT")
    found = [entry for entry in journal["entries"] if entry.get("entry_type") == JOURNAL_CARD_DECISION
             and entry["payload"]["decision_id"].startswith(text)]
    if len(found) != 1:
        raise JournalError("DECISION_NOT_FOUND" if not found else "DECISION_ID_AMBIGUOUS")
    return found[0]


def build_user_decision_proposal(*, journal: dict[str, Any], decision_id: str, user_action: str,
                                 effective_session: str | None, note: str, now: datetime,
                                 journal_path: str = DEFAULT_JOURNAL_PATH) -> dict[str, Any]:
    """The user's own decision on a recorded card decision. A correction is simply another entry."""
    if journal["status"] == "CORRUPT":
        raise JournalError("JOURNAL_CORRUPT")
    if user_action not in ("ADD", "HOLD", "TRIM", "EXIT", "OTHER"):
        raise JournalError("USER_ACTION_INVALID")
    decision = find_card_decision(journal, decision_id)["payload"]
    session = effective_session or decision["decision_session"]
    if validate_instance({"effective_session": session}, PAYLOAD_SCHEMA):
        raise JournalError("EFFECTIVE_SESSION_INVALID")
    if session < decision["decision_session"]:
        raise JournalError("EFFECTIVE_SESSION_BEFORE_DECISION")
    payload = {"decision_id": decision["decision_id"], "ticker": decision["ticker"], "user_action": user_action,
               "effective_session": session, "user_note": note}
    return _proposal_document(entry_type=JOURNAL_CARD_USER_DECISION, payload=payload,
                              review_id=decision["card_sha256"], evaluation_session=session, journal=journal,
                              journal_path=journal_path, now=now)


def _atomic_write(path: Path, document: dict[str, Any], newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline=newline) as output:
            json.dump(document, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _entry_items(proposal: dict[str, Any], journal: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """(entry_id, payload) for every entry the proposal appends. Card proposals are re-checked field by field."""
    entry_type, payload = proposal["entry_type"], proposal["payload"]
    if entry_type == JOURNAL_CARD_DECISION:
        if any(entry.get("entry_type") == JOURNAL_CARD_DECISION and entry["payload"]["card_sha256"] == payload["card_sha256"]
               for entry in journal["entries"]):
            raise JournalError("CARD_ALREADY_RECORDED")
        if proposal["review_id"] != payload["card_sha256"]:
            raise JournalError("CARD_PAYLOAD_INCONSISTENT")
        items: list[tuple[str, dict[str, Any]]] = []
        tickers: set[str] = set()
        for decision in payload["decisions"]:
            if not isinstance(decision, dict) or sorted(decision) != sorted(CARD_DECISION_FIELDS) or (
                    validate_instance(decision, PAYLOAD_SCHEMA)):
                raise JournalError("JOURNAL_PAYLOAD_FIELDS_INVALID")
            if (decision["card_id"], decision["card_sha256"], decision["fact_pack_sha256"]) != (
                    payload["card_id"], payload["card_sha256"], payload["fact_pack_sha256"]) or (
                    decision["decision_session"] != proposal["evaluation_session"]) or (
                    decision["decision_id"] != card_decision_id(decision["card_sha256"], decision["ticker"])) or (
                    decision["sidecar_action"] not in ALLOWED_SIDECAR_ACTIONS[decision["analysis_action"]]) or (
                    decision["ticker"] in tickers):
                raise JournalError("CARD_PAYLOAD_INCONSISTENT")
            tickers.add(decision["ticker"])
            items.append((decision["decision_id"], decision))
        return items
    if entry_type == JOURNAL_CARD_USER_DECISION:
        if validate_instance(payload, PAYLOAD_SCHEMA):
            raise JournalError("JOURNAL_PAYLOAD_FIELDS_INVALID")
        decision = find_card_decision(journal, payload["decision_id"])["payload"]
        if payload["decision_id"] != decision["decision_id"] or payload["ticker"] != decision["ticker"] or (
                payload["effective_session"] < decision["decision_session"]) or (
                proposal["review_id"] != decision["card_sha256"]) or (
                proposal["evaluation_session"] != payload["effective_session"]):
            raise JournalError("USER_DECISION_PAYLOAD_INCONSISTENT")
    return [(proposal["proposal_id"], payload)]


def apply_proposal(*, journal_path: Path, proposal: dict[str, Any], confirmation: dict[str, Any],
                   now: datetime | None = None) -> dict[str, Any]:
    """Append the confirmed entry (the last one when a card proposal appends several)."""
    return apply_proposal_entries(journal_path=journal_path, proposal=proposal, confirmation=confirmation,
                                  now=now)[-1]


def apply_proposal_entries(*, journal_path: Path, proposal: dict[str, Any], confirmation: dict[str, Any],
                           now: datetime | None = None) -> list[dict[str, Any]]:
    """Append every entry of one confirmed proposal in one atomic write. Every check fails closed."""
    errors = validate_instance(proposal, PROPOSAL_SCHEMA)
    if errors:
        raise JournalError("JOURNAL_PROPOSAL_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    if proposal_content_hash(proposal) != proposal["proposal_id"] or (
            proposal["confirm_code"] != proposal["proposal_id"][:8].upper()):
        raise JournalError("JOURNAL_PROPOSAL_INTEGRITY_MISMATCH")
    expected_fields = (CARD_PROPOSAL_PAYLOAD_FIELDS if proposal["entry_type"] == JOURNAL_CARD_DECISION
                       else PAYLOAD_FIELDS[proposal["entry_type"]])
    if sorted(proposal["payload"]) != sorted(expected_fields):
        raise JournalError("JOURNAL_PAYLOAD_FIELDS_INVALID")
    code = confirmation.get("confirm_code")
    if not isinstance(code, str) or not code.strip():
        raise JournalError("CONFIRM_CODE_REQUIRED")
    if code.strip().upper() != proposal["confirm_code"]:
        raise JournalError("CONFIRM_CODE_MISMATCH")
    if confirmation.get("confirmation_method") not in CONFIRMATION_METHODS:
        raise JournalError("CONFIRMATION_METHOD_INVALID")
    message = confirmation.get("user_message")
    if not isinstance(message, str) or proposal["confirm_code"] not in message.upper():
        raise JournalError("USER_CONFIRMATION_MESSAGE_REQUIRED")
    # Expiry and the recorded time use the real clock; a caller's now can only move time forward.
    real_now = datetime.now(timezone.utc)
    current_time = real_now if now is None else max(now, real_now)
    expires_at = _parse(proposal["expires_at"])
    if expires_at is None or current_time > expires_at:
        raise JournalError("JOURNAL_PROPOSAL_EXPIRED")
    journal = load_journal(journal_path)
    if journal["status"] == "CORRUPT":
        raise JournalError("JOURNAL_CORRUPT")
    if journal["head_sha256"] != proposal["expected_journal_head_sha256"] or (
            len(journal["entries"]) != proposal["expected_entry_count"]):
        raise JournalError("JOURNAL_CHANGED_SINCE_PROPOSAL")
    if proposal["entry_type"] == JOURNAL_ACTIVATION and any(
            entry.get("entry_type") == JOURNAL_ACTIVATION for entry in journal["entries"]):
        raise JournalError("S5_ALREADY_ACTIVATED")
    items = _entry_items(proposal, journal)
    confirmed_at = _utc_iso(current_time)
    entries: list[dict[str, Any]] = []
    previous = journal["head_sha256"]
    for offset, (entry_id, entry_payload) in enumerate(items):
        entry = {
            "entry_type": proposal["entry_type"], "entry_id": entry_id,
            "sequence": len(journal["entries"]) + 1 + offset, "previous_entry_sha256": previous,
            "confirm_code": proposal["confirm_code"], "confirmation_method": confirmation["confirmation_method"],
            "user_message": message, "user_confirmed_at": confirmed_at,
            "review_id": proposal["review_id"], "evaluation_session": proposal["evaluation_session"],
            "payload": entry_payload, "order_authority": False, "quantity_authority": "none",
        }
        previous = canonical_hash(entry)
        entries.append(entry)
    document = {"schema_version": JOURNAL_SCHEMA_VERSION, "journal_type": JOURNAL_TYPE,
                "order_authority": False, "quantity_authority": "none", "entries": journal["entries"] + entries}
    errors = validate_instance(document, JOURNAL_SCHEMA)
    if errors:
        raise JournalError("JOURNAL_ENTRY_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    _atomic_write(Path(journal_path), document)
    written = load_journal(journal_path)
    if written["status"] != "OK" or written["head_sha256"] != previous or (
            len(written["entries"]) != len(journal["entries"]) + len(entries)):
        raise JournalError("JOURNAL_WRITE_VERIFICATION_FAILED")
    return entries


def auto_core_payloads(decision: dict[str, Any], decision_sha256: str) -> list[tuple[str, dict[str, Any]]]:
    """(entry_type, payload) for one decide record: one core_decision (no action included), one order_ticket per
    ticket and one ticket_outcome per classified outcome."""
    items: list[tuple[str, dict[str, Any]]] = [(JOURNAL_CORE_DECISION, {
        "run_day_kst": decision["run_day_kst"], "buy_session": decision["buy_session"],
        "decision_mode": decision["decision_mode"], "no_action": decision["no_action"]["value"],
        "blocked_reasons": list(decision["no_action"]["reasons"])[:5],
        "ticket_ids": [ticket["ticket_id"] for ticket in decision["tickets"]],
        "commit_sha": decision["commit_sha"], "decision_sha256": decision_sha256})]
    for ticket in decision["tickets"]:
        items.append((JOURNAL_ORDER_TICKET, {
            "ticket_id": ticket["ticket_id"], "ticker": ticket["ticker"], "side": ticket["side"],
            "order_type": ticket["type"], "price": format(Decimal(str(ticket["price"])), "f"), "qty": ticket["qty"],
            "amount": format(Decimal(str(ticket["amount"])), "f"), "buy_session": ticket["session"],
            "decision_key": ticket["decision_key"], "price_rule": ticket["priceRule"],
            "evidence_r": ticket["evidence"]["r"], "authority": dict(TICKET_AUTHORITY)}))
    for outcome in decision["outcomes"]:
        if outcome.get("state") not in ("filled", "partial", "unfilled", "not_entered", "changed") or \
                outcome.get("mode") != "apply" or outcome.get("reconcile_mismatch"):
            continue
        average = outcome.get("average_fill_price")
        items.append((JOURNAL_TICKET_OUTCOME, {
            "ticket_id": outcome["ticket_id"], "ticker": outcome["ticker"], "side": outcome["side"],
            "outcome_state": outcome["state"], "filled_qty": int(outcome.get("filled_qty") or 0),
            "average_fill_price": None if average is None else format(Decimal(str(average)), "f"),
            "decision_key": outcome.get("decision_key"), "classified_on": decision["run_day_kst"]}))
    return items


def append_auto_core_entries(*, journal_path: Path, decision: dict[str, Any], decision_sha256: str,
                             expected_head: str, recheck: Any, now: datetime | None = None) -> list[dict[str, Any]]:
    """Redesign T2 F7: append the decide record's entries (recording mode only; the caller decides that).

    Fails closed (JournalError, nothing written) when: recheck() (re-reads the configuration, kill switch and
    git provenance just before the write) returns any reason, the journal is not OK, its head differs from the
    head read at decide start, or a core_decision of the same evaluation session already exists (idempotent).
    The hash chain, schema and atomic replace are those of apply_proposal_entries; the file keeps its line
    endings. The human propose/apply path does not accept AUTO_CORE.
    """
    reasons = list(recheck() or [])
    if reasons:
        raise JournalError("AUTO_CORE_RECHECK_FAILED:" + ",".join(reasons))
    journal = load_journal(journal_path)
    if journal["status"] != "OK":
        raise JournalError(f"JOURNAL_{journal['status']}")
    if journal["head_sha256"] != expected_head:
        raise JournalError("JOURNAL_CHANGED_SINCE_DECIDE_START")
    if any(entry.get("entry_type") == JOURNAL_CORE_DECISION
           and entry.get("evaluation_session") == decision["evaluation_session"] for entry in journal["entries"]):
        raise JournalError("CORE_DECISION_ALREADY_RECORDED")
    recorded_at = _utc_iso(now or datetime.now(timezone.utc))
    previous = journal["head_sha256"]
    entries: list[dict[str, Any]] = []
    for offset, (entry_type, payload) in enumerate(auto_core_payloads(decision, decision_sha256)):
        if validate_instance(payload, PAYLOAD_SCHEMA):
            raise JournalError("JOURNAL_PAYLOAD_FIELDS_INVALID")
        entry = {
            "entry_type": entry_type, "entry_id": canonical_hash({"entry_type": entry_type, "payload": payload}),
            "sequence": len(journal["entries"]) + 1 + offset, "previous_entry_sha256": previous,
            "confirm_code": None, "confirmation_method": AUTO_CORE_METHOD, "user_message": None,
            "user_confirmed_at": recorded_at, "review_id": decision_sha256,
            "evaluation_session": decision["evaluation_session"], "payload": payload,
            "order_authority": False, "quantity_authority": "none",
        }
        previous = canonical_hash(entry)
        entries.append(entry)
    document = {"schema_version": JOURNAL_SCHEMA_VERSION, "journal_type": JOURNAL_TYPE,
                "order_authority": False, "quantity_authority": "none", "entries": journal["entries"] + entries}
    errors = validate_instance(document, JOURNAL_SCHEMA) or entry_inconsistencies(document["entries"])
    if errors:
        raise JournalError("JOURNAL_ENTRY_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    newline = "\r\n" if b"\r\n" in Path(journal_path).read_bytes() else "\n"
    if load_journal(journal_path)["head_sha256"] != expected_head:
        raise JournalError("JOURNAL_CHANGED_SINCE_DECIDE_START")
    _atomic_write(Path(journal_path), document, newline=newline)
    written = load_journal(journal_path)
    if written["status"] != "OK" or written["head_sha256"] != previous:
        raise JournalError("JOURNAL_WRITE_VERIFICATION_FAILED")
    return entries


def _messages() -> dict[str, str]:
    return load_json(LOCALE_PATH)["messages"]


def render_proposal(proposal: dict[str, Any], *, now: datetime | None = None) -> list[str]:
    messages = _messages()
    now = now or datetime.now(timezone.utc)
    expires = _parse(proposal.get("expires_at"))
    payload = proposal.get("payload") or {}
    lines = [messages["journal_show_header"].format(
        entry_type=proposal.get("entry_type"),
        expires_hm=expires.astimezone(KST).strftime("%H:%M") if expires else "?")]
    if proposal.get("entry_type") == JOURNAL_ACTIVATION:
        lines.append(messages["journal_show_activation"].format(
            activation_date=payload.get("activation_date"), hwm=payload.get("hwm_usd"),
            hwm_as_of=payload.get("hwm_as_of"), policy_hwm=payload.get("hwm_policy_initial_usd"),
            difference=payload.get("hwm_difference_usd"), revision=payload.get("state_revision")))
    elif proposal.get("entry_type") == JOURNAL_LINE_REVIEW:
        lines.append(messages["journal_show_line_review"].format(
            line_id=payload.get("line_id"), hwm=payload.get("hwm"), breach_date=payload.get("breach_date"),
            conclusion=payload.get("conclusion")))
    elif proposal.get("entry_type") == JOURNAL_CARD_DECISION:
        decisions = [item for item in payload.get("decisions") or [] if isinstance(item, dict)]
        lines.append(messages["journal_show_card_decision"].format(
            card_id=payload.get("card_id"), count=len(decisions), session=proposal.get("evaluation_session")))
        for item in decisions:
            lines.append(messages["journal_show_card_decision_row"].format(
                ticker=item.get("ticker"), action=item.get("analysis_action"), sidecar=item.get("sidecar_action"),
                conviction=item.get("conviction"), reference_close=item.get("reference_close") or "-",
                decision_id=str(item.get("decision_id"))[:MIN_DECISION_ID_PREFIX]))
    elif proposal.get("entry_type") == JOURNAL_CARD_USER_DECISION:
        lines.append(messages["journal_show_user_decision"].format(
            ticker=payload.get("ticker"), action=payload.get("user_action"), session=payload.get("effective_session"),
            decision_id=str(payload.get("decision_id"))[:MIN_DECISION_ID_PREFIX]))
    else:
        lines.append(messages["journal_show_peak_review"].format(
            symbol=payload.get("symbol"), peak=payload.get("peak"), peak_date=payload.get("peak_date"),
            breach_date=payload.get("breach_date")))
    lines.append(messages["summary_no_order"])
    if expires is None or now > expires:
        lines.append(messages["journal_show_expired"])
    else:
        lines.append(messages["journal_show_confirm"].format(code=proposal.get("confirm_code")))
    return lines


def _unique_directory(base: Path) -> Path:
    candidate, index = base, 1
    while candidate.exists():
        candidate = base.with_name(f"{base.name}-{index}")
        index += 1
    return candidate


def _resolve_journal(args: argparse.Namespace, proposal: dict[str, Any] | None = None) -> Path:
    if getattr(args, "journal", None) is not None:
        return Path(args.journal)
    if proposal is not None and proposal.get("journal_path") != DEFAULT_JOURNAL_PATH:
        raise JournalError("PROPOSAL_JOURNAL_PATH_NOT_DEFAULT")
    return REPO_ROOT / DEFAULT_JOURNAL_PATH


def cmd_propose(args: argparse.Namespace) -> int:
    messages = _messages()
    try:
        review = _checked_review(load_json(args.review))
        if args.command == "propose-activation":
            entry_type, payload = JOURNAL_ACTIVATION, activation_payload(review)
        elif args.command == "propose-line-review":
            entry_type = JOURNAL_LINE_REVIEW
            payload = line_review_payload(review, args.line_id, args.conclusion, args.note or "")
        else:
            entry_type, payload = JOURNAL_PEAK_REVIEW, peak_review_payload(review, args.symbol)
        journal_path = _resolve_journal(args)
        proposal = build_proposal(
            entry_type=entry_type, payload=payload, review=review, journal=load_journal(journal_path),
            journal_path=DEFAULT_JOURNAL_PATH if args.journal is None else str(args.journal),
            now=datetime.now(timezone.utc))
        errors = validate_instance(proposal, PROPOSAL_SCHEMA)
        if errors:
            raise JournalError("JOURNAL_PROPOSAL_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    except (JournalError, OSError, ValueError, KeyError) as exc:
        print(messages["journal_apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    directory = _unique_directory(Path(args.output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    write_json(directory / PROPOSAL_FILE, proposal)
    print("\n".join(render_proposal(proposal)))
    print(messages["journal_propose_path"].format(path=str(directory / PROPOSAL_FILE)))
    return 0


def _write_proposal(proposal: dict[str, Any], output_root: Path, messages: dict[str, str]) -> None:
    errors = validate_instance(proposal, PROPOSAL_SCHEMA)
    if errors:
        raise JournalError("JOURNAL_PROPOSAL_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    directory = _unique_directory(Path(output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    write_json(directory / PROPOSAL_FILE, proposal)
    print("\n".join(render_proposal(proposal)))
    print(messages["journal_propose_path"].format(path=str(directory / PROPOSAL_FILE)))


def cmd_propose_card(args: argparse.Namespace) -> int:
    messages = _messages()
    try:
        card, fact_pack = load_json(args.card), load_json(args.fact_pack)
        if not isinstance(card, dict) or not isinstance(fact_pack, dict):
            raise JournalError("CARD_OR_FACT_PACK_NOT_OBJECT")
        journal_path = _resolve_journal(args)
        proposal = build_card_proposal(
            card=card, fact_pack=fact_pack, journal=load_journal(journal_path),
            journal_path=DEFAULT_JOURNAL_PATH if args.journal is None else str(args.journal),
            now=datetime.now(timezone.utc))
        withheld = card_decision_payloads(card, fact_pack)[1]
        if withheld:
            print(messages["journal_propose_card_withheld"].format(tickers=", ".join(withheld)))
        _write_proposal(proposal, args.output_root, messages)
    except (JournalError, OSError, ValueError, KeyError, TypeError) as exc:
        print(messages["journal_apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    return 0


def cmd_propose_user_decision(args: argparse.Namespace) -> int:
    messages = _messages()
    try:
        journal_path = _resolve_journal(args)
        proposal = build_user_decision_proposal(
            journal=load_journal(journal_path), decision_id=args.decision_id, user_action=args.user_action,
            effective_session=args.effective_session, note=args.note or "",
            journal_path=DEFAULT_JOURNAL_PATH if args.journal is None else str(args.journal),
            now=datetime.now(timezone.utc))
        _write_proposal(proposal, args.output_root, messages)
    except (JournalError, OSError, ValueError, KeyError, TypeError) as exc:
        print(messages["journal_apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    messages = _messages()
    try:
        proposal = load_json(args.proposal)
        if not isinstance(proposal, dict):
            raise JournalError("JOURNAL_PROPOSAL_NOT_OBJECT")
        if args.confirmed_via == "COWORK_CHAT_USER_MESSAGE" and not (args.user_message or "").strip():
            raise JournalError("USER_CONFIRMATION_MESSAGE_REQUIRED")
        code = args.confirm.strip().upper()
        entries = apply_proposal_entries(
            journal_path=_resolve_journal(args, proposal), proposal=proposal,
            confirmation={"confirm_code": code, "confirmation_method": args.confirmed_via,
                          "user_message": args.user_message if args.user_message else code})
    except (JournalError, OSError, ValueError, KeyError, TypeError) as exc:
        print(messages["journal_apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    if len(entries) == 1:
        print(messages["journal_apply_success"].format(sequence=entries[0]["sequence"],
                                                        entry_type=entries[0]["entry_type"]))
    else:
        print(messages["journal_apply_success_many"].format(
            first=entries[0]["sequence"], last=entries[-1]["sequence"], count=len(entries),
            entry_type=entries[0]["entry_type"]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decision journal (human confirmations only)")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("propose-activation", "propose-line-review", "propose-peak-review"):
        propose = commands.add_parser(name, help="build a proposal from one exposure review; never writes the journal")
        propose.add_argument("--review", type=Path, required=True)
        propose.add_argument("--journal", type=Path)
        propose.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
        if name == "propose-line-review":
            propose.add_argument("--line-id", required=True)
            propose.add_argument("--conclusion", required=True, choices=CONCLUSIONS)
            propose.add_argument("--note")
        if name == "propose-peak-review":
            propose.add_argument("--symbol", required=True)
    card = commands.add_parser("propose-card", help="record one validated card (one entry per position); never writes")
    card.add_argument("--card", type=Path, required=True)
    card.add_argument("--fact-pack", type=Path, required=True)
    card.add_argument("--journal", type=Path)
    card.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    user = commands.add_parser("propose-user-decision",
                               help="record the user's own decision on a card decision; never writes")
    user.add_argument("--decision-id", required=True, help="card decision id (a unique prefix of 8+ characters works)")
    user.add_argument("--user-action", required=True, choices=("ADD", "HOLD", "TRIM", "EXIT", "OTHER"))
    user.add_argument("--effective-session", help="U.S. session date the decision refers to (default: the card session)")
    user.add_argument("--note")
    user.add_argument("--journal", type=Path)
    user.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    show = commands.add_parser("show", help="render one proposal")
    show.add_argument("--proposal", type=Path, required=True)
    apply = commands.add_parser("apply", help="append one entry after the user's explicit confirmation code")
    apply.add_argument("--proposal", type=Path, required=True)
    apply.add_argument("--confirm", required=True, help="confirmation code the user typed for this proposal")
    apply.add_argument("--confirmed-via", required=True, choices=CONFIRMATION_METHODS)
    apply.add_argument("--user-message", help="the user's confirmation message, verbatim (required for Cowork)")
    apply.add_argument("--journal", type=Path)
    verify = commands.add_parser("verify", help="check the journal hash chain")
    verify.add_argument("--journal", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    if args.command == "propose-card":
        return cmd_propose_card(args)
    if args.command == "propose-user-decision":
        return cmd_propose_user_decision(args)
    if args.command.startswith("propose-"):
        return cmd_propose(args)
    if args.command == "show":
        print("\n".join(render_proposal(load_json(args.proposal))))
        return 0
    if args.command == "apply":
        return cmd_apply(args)
    journal = load_journal(_resolve_journal(args))
    print(json.dumps({"status": journal["status"], "entry_count": len(journal["entries"]),
                      "errors": journal["errors"], "head_sha256": journal["head_sha256"]}))
    return 0 if journal["status"] != "CORRUPT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
