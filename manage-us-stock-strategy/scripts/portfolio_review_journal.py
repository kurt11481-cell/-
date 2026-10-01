#!/usr/bin/env python3
"""S5 decision journal: human confirmations only (activation, line review done, peak review done).

HWM, line breaches, pauses and instrument peaks are recomputed on every run (user decision P1); this
journal stores only what a person confirmed. Every entry comes from a proposal built from one
portfolio exposure review, and is written only with that proposal's confirmation code.

propose-activation / propose-line-review / propose-peak-review   build a proposal; never write the journal
show    render the proposal for the user
apply   append the entry. Run apply only in Cowork after the user typed "confirm <code>" for that
        proposal in the current conversation, or from the user's own terminal
        (--confirmed-via USER_TERMINAL). Agents, scheduled tasks, Claude Code, Codex and Judge
        sessions never run it, and never type or guess the code.
verify  check the journal hash chain

The journal has no order or quantity authority and never touches portfolio state, policy or the
reconciliation ledger.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from portfolio_exposure import (
    JOURNAL_ACTIVATION, JOURNAL_LINE_REVIEW, JOURNAL_PEAK_REVIEW, review_activation_blockers, review_content_hash,
)
from validation_common import canonical_hash, load_json, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
JOURNAL_SCHEMA = SKILL_ROOT / "schemas/portfolio-review-journal.schema.json"
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
S5_ENTRY_TYPES = (JOURNAL_ACTIVATION, JOURNAL_LINE_REVIEW, JOURNAL_PEAK_REVIEW)
CONFIRMATION_METHODS = ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL")
GENESIS_HASH = "0" * 64
PROPOSAL_MAX_AGE_SECONDS = 3600
CONCLUSIONS = ("continue", "other")
PAYLOAD_FIELDS = {
    JOURNAL_ACTIVATION: ("activation_date", "hwm_usd", "hwm_as_of", "hwm_policy_initial_usd", "hwm_difference_usd",
                         "state_revision", "window_start", "window_end", "close_basis"),
    JOURNAL_LINE_REVIEW: ("line_id", "hwm", "breach_date", "review_status", "conclusion", "conclusion_note"),
    JOURNAL_PEAK_REVIEW: ("symbol", "peak", "peak_date", "breach_date", "review_status"),
}
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
    return {"status": "OK", "entries": document["entries"], "errors": [], "head_sha256": previous}


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
    proposal: dict[str, Any] = {
        "schema_version": PROPOSAL_SCHEMA_VERSION, "proposal_type": PROPOSAL_TYPE,
        "proposal_id": "", "confirm_code": "", "entry_type": entry_type, "payload": payload,
        "review_id": review["review_id"], "evaluation_session": review["evaluation_session"],
        "generated_at": _utc_iso(now), "expires_at": _utc_iso(now + timedelta(seconds=PROPOSAL_MAX_AGE_SECONDS)),
        "journal_path": journal_path, "expected_journal_head_sha256": journal["head_sha256"],
        "expected_entry_count": len(journal["entries"]),
        "auto_apply": False, "order_authority": False, "quantity_authority": "none",
    }
    proposal["proposal_id"] = proposal_content_hash(proposal)
    proposal["confirm_code"] = proposal["proposal_id"][:8].upper()
    return proposal


def _atomic_write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
            json.dump(document, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def apply_proposal(*, journal_path: Path, proposal: dict[str, Any], confirmation: dict[str, Any],
                   now: datetime | None = None) -> dict[str, Any]:
    """Append one confirmed entry. Every check fails closed; nothing else is written."""
    errors = validate_instance(proposal, PROPOSAL_SCHEMA)
    if errors:
        raise JournalError("JOURNAL_PROPOSAL_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    if proposal_content_hash(proposal) != proposal["proposal_id"] or (
            proposal["confirm_code"] != proposal["proposal_id"][:8].upper()):
        raise JournalError("JOURNAL_PROPOSAL_INTEGRITY_MISMATCH")
    if sorted(proposal["payload"]) != sorted(PAYLOAD_FIELDS[proposal["entry_type"]]):
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
    confirmed_at = _utc_iso(current_time)
    entry = {
        "entry_type": proposal["entry_type"], "entry_id": proposal["proposal_id"],
        "sequence": len(journal["entries"]) + 1, "previous_entry_sha256": journal["head_sha256"],
        "confirm_code": proposal["confirm_code"], "confirmation_method": confirmation["confirmation_method"],
        "user_message": message, "user_confirmed_at": confirmed_at,
        "review_id": proposal["review_id"], "evaluation_session": proposal["evaluation_session"],
        "payload": proposal["payload"], "order_authority": False, "quantity_authority": "none",
    }
    document = {"schema_version": JOURNAL_SCHEMA_VERSION, "journal_type": JOURNAL_TYPE,
                "order_authority": False, "quantity_authority": "none", "entries": journal["entries"] + [entry]}
    errors = validate_instance(document, JOURNAL_SCHEMA)
    if errors:
        raise JournalError("JOURNAL_ENTRY_SCHEMA_INVALID: " + "; ".join(errors[:5]))
    _atomic_write(Path(journal_path), document)
    written = load_journal(journal_path)
    if written["status"] != "OK" or written["head_sha256"] != canonical_hash(entry):
        raise JournalError("JOURNAL_WRITE_VERIFICATION_FAILED")
    return entry


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


def cmd_apply(args: argparse.Namespace) -> int:
    messages = _messages()
    try:
        proposal = load_json(args.proposal)
        if not isinstance(proposal, dict):
            raise JournalError("JOURNAL_PROPOSAL_NOT_OBJECT")
        if args.confirmed_via == "COWORK_CHAT_USER_MESSAGE" and not (args.user_message or "").strip():
            raise JournalError("USER_CONFIRMATION_MESSAGE_REQUIRED")
        code = args.confirm.strip().upper()
        entry = apply_proposal(
            journal_path=_resolve_journal(args, proposal), proposal=proposal,
            confirmation={"confirm_code": code, "confirmation_method": args.confirmed_via,
                          "user_message": args.user_message if args.user_message else code})
    except (JournalError, OSError, ValueError, KeyError, TypeError) as exc:
        print(messages["journal_apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    print(messages["journal_apply_success"].format(sequence=entry["sequence"], entry_type=entry["entry_type"]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="S5 decision journal (human confirmations only)")
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
