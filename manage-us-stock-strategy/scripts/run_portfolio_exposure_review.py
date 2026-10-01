#!/usr/bin/env python3
"""Run one S5 portfolio exposure review (read-only inputs, display-only output).

Reads the alert policy, portfolio state, reconciliation ledger, decision journal, saved close
histories and the session calendar, calls portfolio_exposure.build_exposure_review and writes one
result file under workspace/outputs/exposure-review/<session>/. It never writes state, policy, the
ledger or the journal, never calls a broker, and its output grants no order or quantity authority.

Confirmed holdings history comes from the reconciliation ledger: the current state is replayed
backwards through each applied proposal's recorded changes (user decision P1, recompute every run).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from apply_user_confirmed_broker_snapshot import default_ledger_path, ledger_status
from kiwoom_broker_shadow import PROPOSAL_SCHEMA_VERSION
from portfolio_exposure import (
    LATEST_SESSION_STATUS, ExposureError, build_exposure_review, exposure_config, exposure_display_block,
    render_exposure_line,
)
from portfolio_review_journal import DEFAULT_JOURNAL_PATH, load_journal
from regular_session_close_history import (
    CloseHistoryError, build_history, closes_by_session, history_errors, load_calendar,
)
from validate_holding_card import validate_card
from validation_common import canonical_hash, load_json, validate_instance


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
REVIEW_SCHEMA = SKILL_ROOT / "schemas/portfolio-exposure-review.schema.json"
LOCALE_PATH = SKILL_ROOT / "assets/locales/portfolio-exposure-ko-KR.json"
DEFAULT_STATE = REPO_ROOT / "stock-strategy-system/portfolio_state.json"
DEFAULT_POLICY = REPO_ROOT / "stock-strategy-system/alert_policy.json"
DEFAULT_JOURNAL = REPO_ROOT / DEFAULT_JOURNAL_PATH
EXCHANGE_TIMEZONE = "America/New_York"
DEFAULT_CLOSES_ROOT = REPO_ROOT / "workspace/outputs/regular-session-closes"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/exposure-review"
DEFAULT_ACTIVATION = REPO_ROOT / "workspace/policies/session_calendar_activation.json"
CALENDAR_ARTIFACT_ROOT = REPO_ROOT / "workspace/calendar-authority/artifacts"
CALENDAR_ARTIFACT_NAME = "us-equities-core-session-v2.calendar.json"
REVIEW_FILE_PREFIX = "portfolio-exposure-review"
HISTORY_SUFFIX = ".close-history.json"
PROTECTED_OUTPUT_PARENTS = ("stock-strategy-system", "workspace/policies", "workspace/state")


class ReviewRunError(ValueError):
    """Input problem that prevents a review from being produced at all."""


def _hash_or_none(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _cash_text(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return format(number, "f") if number.is_finite() else None


def read_ledger_entries(ledger_path: Path) -> list[dict[str, Any]]:
    entries = []
    for raw in Path(ledger_path).read_bytes().splitlines():
        if raw.strip():
            entry = json.loads(raw.decode("utf-8"))
            if isinstance(entry, dict):
                entries.append(entry)
    return entries


def reconstruct_snapshots(state: dict[str, Any], entries: list[dict[str, Any]], *, chain_ok: bool,
                          ledger_exists: bool) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Confirmed (as_of, holdings, cash) after every applied reconciliation, oldest first.

    The current state must equal the last ledger entry's after-hash; then each entry's recorded
    changes are undone in reverse. An entry that cannot be replayed (older proposal type, broken
    revision link, or one that recorded an outside change) ends the history there: earlier sessions
    then have no confirmed snapshot and fail closed in the review. Returns (snapshots, reasons the
    current snapshot is not verified, notes).
    """
    reasons: list[str] = []
    notes: list[str] = []
    record = state.get("last_confirmed_broker_snapshot")
    broker = record if isinstance(record, dict) else {}
    holdings = {str(key): value for key, value in (state.get("holdings") or {}).items()}
    cash, as_of = state.get("available_cash_usd"), broker.get("as_of")

    def snapshot(revision: Any, *, decreased: bool = False, block: Any = None, from_entry: bool = False) -> dict[str, Any]:
        return {"as_of": as_of, "state_revision": revision, "holdings": dict(holdings), "cash_usd": _cash_text(cash),
                "holdings_decreased": decreased, "cash_flow_declaration": block, "from_ledger_entry": from_entry}

    current = snapshot(state.get("state_revision"))
    if broker.get("verified") is not True or broker.get("holdings_complete") is not True:
        reasons.append("BROKER_SNAPSHOT_NOT_VERIFIED_COMPLETE")
    if broker.get("cash_verified") is not True:
        reasons.append("BROKER_CASH_NOT_VERIFIED")
    if ledger_exists and not chain_ok:
        reasons.append("LEDGER_INTEGRITY_FAILED")
        return [current], reasons, notes
    if not ledger_exists or not entries:
        notes.append("RECONCILIATION_LEDGER_EMPTY_STATE_SNAPSHOT_ONLY")
        return [current], reasons, notes
    if entries[-1].get("portfolio_hash_after") != canonical_hash(state) or (
            entries[-1].get("state_revision_after") != state.get("state_revision")):
        reasons.append("STATE_CHANGED_OUTSIDE_LEDGER")
        return [current], reasons, notes
    snapshots: list[dict[str, Any]] = []
    base_revision: Any = state.get("state_revision")
    with_base = True
    for index in range(len(entries) - 1, -1, -1):
        entry = entries[index]
        changes = entry.get("changes")
        replayable = (entry.get("event") == "APPLY" and entry.get("proposal_schema_version") == PROPOSAL_SCHEMA_VERSION
                      and isinstance(changes, list) and all(isinstance(item, dict) for item in changes))
        linked = index == len(entries) - 1 or entry.get("state_revision_after") == entries[index + 1].get(
            "state_revision_before")
        if not replayable or not linked:
            notes.append(f"LEDGER_HISTORY_NOT_REPLAYABLE_AT_REVISION:{entry.get('state_revision_after')}")
            break
        decreased = any(
            item.get("field") == "holdings" and isinstance(item.get("old_value"), int)
            and not isinstance(item.get("old_value"), bool)
            and (item.get("new_value") or 0) < item["old_value"] for item in changes)
        snapshots.append(snapshot(entry.get("state_revision_after"), decreased=decreased,
                                  block=entry.get("cash_flow_declaration"), from_entry=True))
        if entry.get("state_changed_outside_ledger") is True:
            # The values this entry replaced were changed outside the ledger and were never confirmed.
            notes.append(f"LEDGER_ENTRY_RECORDED_OUTSIDE_CHANGE_AT_REVISION:{entry.get('state_revision_after')}")
            with_base = False
            break
        for item in changes:
            field, key, old = item.get("field"), item.get("key"), item.get("old_value")
            if field == "holdings":
                if old is None:
                    holdings.pop(str(key), None)
                else:
                    holdings[str(key)] = old
            elif field == "available_cash_usd":
                cash = old
            elif field == "last_confirmed_broker_snapshot" and key == "as_of":
                as_of = old
        base_revision = entry.get("state_revision_before")
    if with_base:
        # State before the earliest replayed entry (written by an earlier confirmed apply).
        snapshots.append(snapshot(base_revision))
    ordered = [item for item in reversed(snapshots) if isinstance(item["as_of"], str)]
    return ordered or [current], reasons, notes


def reproduce_history(history: dict[str, Any], pages_dir: Path, calendar: dict[str, Any]
                      ) -> tuple[dict[str, Any] | None, list[str]]:
    """Rebuild the history from the saved pages with this run's calendar; the stored file must match.

    The history file is only a cache of the pages. A close that cannot be derived again from the
    evidence pages (edited history, stale history, extra or missing page) is not used.
    """
    try:
        rebuilt = build_history(symbol=history["symbol"], exchange=history["exchange"],
                                page_paths=sorted(Path(pages_dir).glob("*.json")), calendar=calendar)
    except CloseHistoryError as exc:
        return None, [f"CLOSE_HISTORY_PAGES_INVALID:{exc}"]

    def key(document: dict[str, Any]) -> list[Any]:
        return [[(page["file_name"], page["sha256"]) for page in document["pages"]],
                [(item["session_date"], item["close"], item["bar_cntr_tm"], item["close_type"], item["page_sha256"])
                 for item in document["sessions"]]]

    if key(rebuilt) != key(history):
        return None, ["CLOSE_HISTORY_NOT_REPRODUCIBLE_FROM_PAGES"]
    return rebuilt, []


def load_close_histories(symbols: list[str], closes_root: Path, calendar: dict[str, Any]
                         ) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, list[str]]], dict[str, Any]]:
    """Load history/<SYMBOL>.close-history.json for each symbol; an invalid history is treated as absent.

    Verification status is decided here, not taken from the file: the calendar authority is this
    run's, and closes count as verified only when they were reproduced from the saved pages.
    """
    closes: dict[str, dict[str, str]] = {}
    unverified: dict[str, dict[str, list[str]]] = {}
    report: dict[str, Any] = {}
    calendar_active = calendar["identity"]["authority_status"] == "ACTIVE"
    for symbol in sorted(set(symbols)):
        path = Path(closes_root) / "history" / f"{symbol}{HISTORY_SUFFIX}"
        if not path.is_file():
            report[symbol] = {"status": "MISSING"}
            continue
        pages_dir = Path(closes_root) / "pages" / symbol
        try:
            history = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            report[symbol] = {"status": "INVALID", "errors": ["CLOSE_HISTORY_NOT_JSON"]}
            continue
        errors = history_errors(history, pages_dir=pages_dir if pages_dir.is_dir() else None)
        if not errors and history["symbol"] != symbol:
            errors.append("CLOSE_HISTORY_SYMBOL_MISMATCH")
        if not errors and history["calendar"]["calendar_sha256"] != calendar["identity"]["calendar_sha256"]:
            errors.append("CLOSE_HISTORY_CALENDAR_MISMATCH")
        source = history
        if not errors and pages_dir.is_dir():
            rebuilt, errors = reproduce_history(history, pages_dir, calendar)
            source = rebuilt if rebuilt is not None else history
        if errors:
            report[symbol] = {"status": "INVALID", "errors": errors}
            continue
        closes[symbol] = closes_by_session(source)
        extra = [] if pages_dir.is_dir() else ["CLOSE_HISTORY_PAGES_NOT_VERIFIED"]
        if not calendar_active:
            extra.append("SESSION_CALENDAR_NOT_ACTIVE")
        unverified[symbol] = {}
        for item in source["sessions"]:
            reasons = sorted(set(item["unverified_reasons"]) | set(extra))
            if reasons:
                unverified[symbol][item["session_date"]] = reasons
        report[symbol] = {"status": "OK", "history_hash": history["history_hash"],
                          "first_session": history["first_session"], "last_session": history["last_session"],
                          "session_count": history["session_count"],
                          "reproduced_from_pages": pages_dir.is_dir()}
    return closes, unverified, report


def load_cards(cards_path: Path | None, fact_pack_path: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Only a card that passes validate_holding_card against its fact pack is used (default D4)."""
    if cards_path is None or fact_pack_path is None:
        return {}, {"status": "NOT_PROVIDED"}
    try:
        card, fact_pack = load_json(cards_path), load_json(fact_pack_path)
    except (OSError, ValueError):
        return {}, {"status": "INVALID", "errors": ["CARD_OR_FACT_PACK_NOT_JSON"]}
    errors = validate_card(card, fact_pack)
    if errors:
        return {}, {"status": "INVALID", "errors": errors}
    session = (fact_pack.get("source") or {}).get("expected_completed_us_session")
    cards = {position["ticker"]: {"action": position.get("action"), "valid": True, "session_date": session}
             for position in card.get("positions") or [] if isinstance(position, dict) and position.get("ticker")}
    return cards, {"status": "OK", "session_date": session, "card_sha256": canonical_hash(card)}


def expected_completed_session(calendar: dict[str, Any], now: datetime) -> str | None:
    completed = [date_text for date_text, row in calendar["sessions"].items()
                 if datetime.fromisoformat(row["core_close_at"]) <= now]
    return max(completed) if completed else None


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def resolve_session(calendar: dict[str, Any], now: datetime, requested: str | None) -> tuple[str, str, list[str]]:
    """(evaluation session, status, fail-closed reasons).

    The default is the latest completed session, which is only known when the calendar covers today.
    A calendar that ends earlier would present its last session as "the latest" (the ACTIVE calendar
    ends 2026-08-29), so the default then fails. An explicitly requested older session is allowed
    for inspection but is labelled and fails closed.
    """
    identity = calendar["identity"]
    today = now.astimezone(ZoneInfo(EXCHANGE_TIMEZONE)).date().isoformat()
    latest = expected_completed_session(calendar, now)
    if requested is not None and requested not in calendar["sessions"]:
        raise ReviewRunError("EVALUATION_SESSION_NOT_IN_CALENDAR")
    if not identity["coverage_start"] <= today <= identity["coverage_end"]:
        if requested is None:
            raise ReviewRunError(f"SESSION_CALENDAR_DOES_NOT_COVER_TODAY:{identity['coverage_end']}")
        return requested, "CALENDAR_DOES_NOT_COVER_TODAY", [
            f"EVALUATION_SESSION_NOT_VERIFIED_LATEST:CALENDAR_ENDS_{identity['coverage_end']}"]
    if latest is None:
        raise ReviewRunError("NO_COMPLETED_SESSION_IN_CALENDAR")
    if requested is None or requested == latest:
        return latest, LATEST_SESSION_STATUS, []
    if requested > latest:
        raise ReviewRunError("EVALUATION_SESSION_NOT_COMPLETED")
    return requested, "NOT_LATEST_COMPLETED_SESSION", [f"EVALUATION_SESSION_NOT_LATEST:{latest}"]


def resolve_calendar_path(calendar: Path | None, activation: Path) -> Path:
    if calendar is not None:
        return calendar
    try:
        active_hash = str(json.loads(activation.read_text(encoding="utf-8-sig")).get("active_calendar_hash") or "")
    except (OSError, ValueError) as exc:
        raise ReviewRunError("SESSION_CALENDAR_ACTIVATION_UNREADABLE") from exc
    return CALENDAR_ARTIFACT_ROOT / active_hash / CALENDAR_ARTIFACT_NAME


def summary_lines(review: dict[str, Any], messages: dict[str, str]) -> list[str]:
    lines = [messages["summary_prefix"] + render_exposure_line(exposure_display_block(review), messages)]
    reduce = review["recommendations"]["reduce"]
    if reduce:
        lines.append(messages["summary_reduce"].format(
            count=len(reduce), urgent=messages["summary_reduce_urgent"] if review["band"]["urgent_reduce"] else ""))
    if review["recommendations"]["add"]:
        lines.append(messages["summary_add"].format(count=len(review["recommendations"]["add"])))
    if review["recommendations"]["warnings"]:
        lines.append(messages["summary_warning"].format(codes=", ".join(review["recommendations"]["warnings"])))
    active = [item["id"] for item in review["fail_closed"]["triggers"] if item["active"]]
    if active:
        lines.append(messages["summary_unverified"].format(codes=", ".join(active)))
    lines.append(messages["summary_no_order"])
    return lines


def run(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else current_time()
    if now.tzinfo is None:
        raise ReviewRunError("NOW_REQUIRES_OFFSET")
    state_path, policy_path = Path(args.state), Path(args.policy)
    ledger_path = Path(args.ledger) if args.ledger else default_ledger_path(state_path)
    journal_path = Path(args.journal) if args.journal else DEFAULT_JOURNAL
    output_root = Path(args.output_root).resolve()
    for protected in PROTECTED_OUTPUT_PARENTS:
        blocked = (REPO_ROOT / protected).resolve()
        if output_root == blocked or blocked in output_root.parents:
            raise ReviewRunError("OUTPUT_ROOT_PROTECTED")
    watched = [state_path, policy_path, ledger_path, journal_path]
    before = [_hash_or_none(path) for path in watched]

    policy = load_json(policy_path)
    config = exposure_config(policy)
    state = load_json(state_path)
    if not isinstance(state, dict):
        raise ReviewRunError("PORTFOLIO_STATE_NOT_OBJECT")
    # Calendar authority always comes from the production activation file; there is no override.
    calendar_path = resolve_calendar_path(Path(args.calendar) if args.calendar else None, DEFAULT_ACTIVATION)
    try:
        calendar = load_calendar(calendar_path, DEFAULT_ACTIVATION)
    except (CloseHistoryError, OSError) as exc:
        raise ReviewRunError(f"SESSION_CALENDAR_UNAVAILABLE:{exc}") from exc
    calendar_sessions = sorted(calendar["sessions"])
    session, session_status, session_reasons = resolve_session(calendar, now, args.session)

    status = ledger_status(ledger_path)
    entries = read_ledger_entries(ledger_path) if status["exists"] and status["chain_ok"] else []
    snapshots, snapshot_reasons, ledger_notes = reconstruct_snapshots(
        state, entries, chain_ok=status["chain_ok"], ledger_exists=status["exists"])

    cards, card_report = load_cards(Path(args.cards) if args.cards else None,
                                    Path(args.fact_pack) if args.fact_pack else None)
    earnings = load_json(args.earnings).get("earnings") if args.earnings else None
    proposals = load_json(args.proposals).get("proposals") if args.proposals else None
    symbols = {config["benchmark"], config["supplement"]}
    for snapshot in snapshots:
        symbols.update(symbol for symbol, quantity in snapshot["holdings"].items()
                       if isinstance(quantity, int) and quantity > 0)
    symbols.update(symbol for symbol, card in cards.items() if card.get("action") == "ADD")
    symbols.update(str(item.get("symbol")) for item in proposals or [] if isinstance(item, dict) and item.get("symbol"))
    closes, unverified, history_report = load_close_histories(sorted(symbols), Path(args.closes_root), calendar)
    journal = load_journal(journal_path)
    defaults = (("policy", policy_path, DEFAULT_POLICY), ("state", state_path, DEFAULT_STATE),
                ("ledger", ledger_path, default_ledger_path(DEFAULT_STATE)),
                ("journal", journal_path, DEFAULT_JOURNAL),
                ("closes_root", Path(args.closes_root), DEFAULT_CLOSES_ROOT))
    non_default = [name for name, used, default in defaults if Path(used).resolve() != Path(default).resolve()]
    if args.now:
        non_default.append("now")
    inputs = {
        "generated_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy_canonical_sha256": canonical_hash(policy), "state_canonical_sha256": canonical_hash(state),
        "state_revision": state.get("state_revision"), "ledger_entries": status["entries"],
        "ledger_last_entry_sha256": status["last_entry_sha256"], "ledger_replay_notes": ledger_notes,
        "journal_status": journal["status"],
        "journal_head_sha256": journal["head_sha256"], "calendar": calendar["identity"],
        "evaluation_session_status": session_status,
        "latest_completed_session": expected_completed_session(calendar, now),
        "close_histories": history_report, "cards": card_report,
        "earnings_provided": earnings is not None, "proposals_provided": len(proposals or []),
        # A review built from anything but the production files is labelled on every display line.
        "non_default_inputs": non_default,
    }
    review = build_exposure_review(
        policy=policy, evaluation_session=session, calendar_sessions=calendar_sessions, snapshots=snapshots,
        snapshot_reasons=snapshot_reasons, closes=closes, close_unverified=unverified, journal=journal,
        cards=cards, earnings=earnings, proposals=proposals, inputs=inputs, evaluation_reasons=session_reasons)
    errors = validate_instance(review, REVIEW_SCHEMA)
    if errors:
        raise ReviewRunError("EXPOSURE_REVIEW_SCHEMA_FAILED:" + ";".join(errors[:5]))
    if [_hash_or_none(path) for path in watched] != before:
        raise ReviewRunError("READ_ONLY_INPUT_MUTATION_DETECTED")
    target = output_root / session / f"{REVIEW_FILE_PREFIX}.{now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write((json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if [_hash_or_none(path) for path in watched] != before:
        raise ReviewRunError("READ_ONLY_INPUT_MUTATION_DETECTED")
    return review, target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="S5 portfolio exposure review (read-only, display-only)")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--ledger", type=Path, help="default: reconciliation_ledger.jsonl next to the state file")
    parser.add_argument("--journal", type=Path, help=f"default: {DEFAULT_JOURNAL_PATH}")
    parser.add_argument("--closes-root", type=Path, default=DEFAULT_CLOSES_ROOT)
    parser.add_argument("--calendar", type=Path, help="session-calendar artifact; default: the ACTIVE artifact")
    parser.add_argument("--session", help="completed U.S. session YYYY-MM-DD; default: latest completed session. "
                                          "An older session is labelled and fails closed")
    parser.add_argument("--cards", type=Path, help="holding card JSON (used only with --fact-pack and when valid)")
    parser.add_argument("--fact-pack", type=Path)
    parser.add_argument("--earnings", type=Path, help='{"earnings": {"SYM": {"status": "VERIFIED", ...}}}')
    parser.add_argument("--proposals", type=Path, help='{"proposals": [{"kind": "new_buy_within_band", ...}]}')
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--now", help="ISO timestamp with offset used as now (tests; the result is labelled)")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    try:
        review, target = run(args)
    except (ReviewRunError, ExposureError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc) or type(exc).__name__}))
        return 2
    messages = load_json(LOCALE_PATH)["messages"]
    print("\n".join(summary_lines(review, messages)))
    print(messages["summary_path"].format(path=str(target)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
