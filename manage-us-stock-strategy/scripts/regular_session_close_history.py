#!/usr/bin/env python3
"""Verify saved Kiwoom 30-minute bar pages and normalize them into a regular-session close history.

The pages are the read-only Kiwoom CLI output for usa06011 (30-minute bars) that Cowork saved as
evidence files. This script never calls Kiwoom: it only reads the saved pages, checks them (page
hash, row format, session calendar, session continuity) and writes one history file per symbol.

Close definition (user decision P3, 2026-10-01): the close of the last 30-minute bar of the regular
session, with bars labelled by their START time in U.S. Eastern time. That is the 15:30 bar on a
regular day and the bar starting 30 minutes before core_close_at on an early-close day. Bars from
other sessions (pre-market, after-hours, overnight) are dropped. The value is an APPROXIMATE close,
not the official closing-auction price. A reference close, when supplied, is shown as a difference
only and never changes a verdict. Low and high prices are never used.

build   pages -> history file (create-only; --update may extend it but never change an earlier close)
verify  recompute page hashes and the history hash of an existing history file
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Any

from integrated_authority_snapshot import (
    IntegratedAuthorityLoadError, IntegratedAuthoritySnapshot, load_production_integrated_authority_snapshot,
)
from session_calendar_artifact import SessionCalendarLoadError, _semantic_validate_artifact
from validation_common import canonical_hash, validate_instance


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
HISTORY_SCHEMA = SKILL_ROOT / "schemas/regular-session-close-history.schema.json"
CALENDAR_SCHEMA = SKILL_ROOT / "schemas/session-calendar-artifact.schema.json"
# Calendar authority comes from the Production integrated authority under this root. There is no
# command-line or environment override; tests patch this module constant.
TRUSTED_ROOT = REPO_ROOT
NOT_ACTIVE_STATUS = "EXPLICIT_ARTIFACT_NOT_ACTIVE"
HASH_NOT_ACTIVE_REASON = "CALENDAR_HASH_NOT_ACTIVE_AUTHORITY"
DEFAULT_ROOT = REPO_ROOT / "workspace/outputs/regular-session-closes"
SCHEMA_VERSION = "regular-session-close-history-1.0"
ARTIFACT_TYPE = "REGULAR_SESSION_CLOSE_HISTORY"
API_ID = "usa06011"
INTERVAL_MINUTES = 30
PAGE_SIZE = 100
ROW_KEYS = ("cur_prc", "trde_qty", "open_pric", "high_pric", "low_pric", "cntr_tm", "bus_dt", "upd_stkpc_tp",
            "upd_rt")
# The last row of every 100-row page carries this value. It is a page-end marker, not an
# adjusted-price flag (Cowork measurement C13), so it is never used as one.
PAGE_END_MARKER = "1f"
TIME_LABEL = re.compile(r"(?:[01]\d|2[0-7])(?:00|30)00")
STAMP = re.compile(r"\d{14}")
SYMBOL = re.compile(r"[A-Z][A-Z0-9.]{0,11}")
# Bar labels were observed in U.S. Eastern wall-clock time only while this UTC offset was in force
# (Cowork measurements K3/C13, 2026-04-01..2026-09-30). A session under another offset stays
# unverified until the label basis is measured again (planned after 2026-11-02).
LABEL_VERIFIED_UTC_OFFSETS = ("-04:00",)


class CloseHistoryError(ValueError):
    """Fail-closed evidence error with a public reason code."""


def _positive(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def load_production_snapshot(now: datetime) -> tuple[IntegratedAuthoritySnapshot | None, str | None]:
    """(snapshot, None) when the Production integrated authority loads at `now`, else (None, loader reason)."""
    stamp = now.astimezone(timezone.utc).isoformat()
    try:
        return load_production_integrated_authority_snapshot(
            trusted_root=TRUSTED_ROOT, decision_as_of=stamp, resolved_at=stamp), None
    except IntegratedAuthorityLoadError as exc:
        return None, exc.reason


def _thaw(value: Any) -> Any:
    if isinstance(value, (dict, MappingProxyType)):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(child) for child in value]
    return value


def _calendar_from_artifact(artifact: Any, digest: str, status: str, failure: str | None) -> dict[str, Any]:
    try:
        if validate_instance(artifact, CALENDAR_SCHEMA):
            raise ValueError("SCHEMA")
        _semantic_validate_artifact(artifact)
        return {
            "sessions": {row["session_date"]: row for row in artifact["sessions"]},
            "identity": {"calendar_version": artifact["calendar_version"], "calendar_sha256": digest,
                         "coverage_start": artifact["coverage_start"], "coverage_end": artifact["coverage_end"],
                         "authority_status": status},
            # Why the calendar is not ACTIVE (None when it is, or when no authority was consulted).
            "authority_failure": failure,
        }
    except (ValueError, KeyError, TypeError, SessionCalendarLoadError) as exc:
        raise CloseHistoryError(f"CALENDAR_ARTIFACT_INVALID:{exc}") from exc


def load_calendar(calendar_path: Path, snapshot: IntegratedAuthoritySnapshot | None,
                  authority_failure: str | None = None) -> dict[str, Any]:
    """Read one session-calendar artifact and say whether it is the ACTIVE production calendar.

    ACTIVE means the Production integrated authority loaded (`snapshot`) and this file's raw sha256
    equals the session calendar hash it activates. Without a snapshot (`authority_failure` is the
    loader's reason) or with another hash the artifact is only an explicit, non-active calendar.
    """
    raw = Path(calendar_path).read_bytes()
    try:
        artifact = json.loads(raw.decode("utf-8-sig"))
    except ValueError as exc:
        raise CloseHistoryError(f"CALENDAR_ARTIFACT_INVALID:{exc}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if snapshot is None:
        return _calendar_from_artifact(artifact, digest, NOT_ACTIVE_STATUS, authority_failure)
    if digest == snapshot.session.calendar_hash:
        return _calendar_from_artifact(artifact, digest, "ACTIVE", None)
    return _calendar_from_artifact(artifact, digest, NOT_ACTIVE_STATUS, HASH_NOT_ACTIVE_REASON)


def calendar_from_snapshot(snapshot: IntegratedAuthoritySnapshot) -> dict[str, Any]:
    """The ACTIVE calendar the loader already verified (hash, schema and semantics), without a second file read."""
    return _calendar_from_artifact(_thaw(snapshot.session.artifact), snapshot.session.calendar_hash, "ACTIVE", None)


def final_bar_label(session_row: dict[str, str]) -> tuple[str, str]:
    """(cntr_tm of the bar starting 30 minutes before core_close_at, the close's UTC offset)."""
    close_text = session_row["core_close_at"]
    closed = datetime.fromisoformat(close_text)
    start = closed - timedelta(minutes=INTERVAL_MINUTES)
    return start.strftime("%Y%m%d%H%M%S"), close_text[-6:]


def parse_page(path: Path) -> dict[str, Any]:
    """Row-format checks for one saved page file. Any deviation rejects the whole file."""
    raw = Path(path).read_bytes()
    name = Path(path).name
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except ValueError as exc:
        raise CloseHistoryError(f"PAGE_NOT_JSON:{name}") from exc
    body = document.get("result") if isinstance(document, dict) else None
    rows = body.get("result_list") if isinstance(body, dict) else None
    if not isinstance(rows, list) or not rows:
        raise CloseHistoryError(f"PAGE_SHAPE_INVALID:{name}")
    if body.get("return_code") != 0:
        raise CloseHistoryError(f"PAGE_RETURN_CODE_NOT_ZERO:{name}")
    previous = None
    parsed = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or tuple(row) != ROW_KEYS or any(not isinstance(row[key], str) for key in ROW_KEYS):
            raise CloseHistoryError(f"PAGE_ROW_KEYS_INVALID:{name}:{index}")
        stamp = row["cntr_tm"]
        if STAMP.fullmatch(stamp) is None or TIME_LABEL.fullmatch(stamp[8:]) is None or row["bus_dt"] != stamp[:8]:
            raise CloseHistoryError(f"PAGE_ROW_TIME_INVALID:{name}:{index}")
        if previous is not None and stamp >= previous:
            raise CloseHistoryError(f"PAGE_ROW_ORDER_INVALID:{name}:{index}")
        previous = stamp
        if any(_positive(row[key]) is None for key in ("cur_prc", "open_pric", "high_pric", "low_pric")):
            raise CloseHistoryError(f"PAGE_ROW_PRICE_INVALID:{name}:{index}")
        marker_allowed = index % PAGE_SIZE == PAGE_SIZE - 1 or index == len(rows) - 1
        if row["upd_rt"] != "" or (row["upd_stkpc_tp"] != "" and not (
                marker_allowed and row["upd_stkpc_tp"] == PAGE_END_MARKER)):
            # An unexpected adjustment field may mean adjusted prices; raw closes are required.
            raise CloseHistoryError(f"PAGE_ADJUSTMENT_FIELD_UNEXPECTED:{name}:{index}")
        parsed.append({"cntr_tm": stamp, "close": row["cur_prc"]})
    return {"file_name": name, "sha256": hashlib.sha256(raw).hexdigest(), "row_count": len(parsed),
            "first_cntr_tm": parsed[0]["cntr_tm"], "last_cntr_tm": parsed[-1]["cntr_tm"], "rows": parsed}


def build_history(*, symbol: str, exchange: str, page_paths: list[Path], calendar: dict[str, Any],
                  reference_closes: dict[str, str] | None = None) -> dict[str, Any]:
    """Merge verified pages and pick the final regular-session bar of every calendar session."""
    if SYMBOL.fullmatch(symbol) is None:
        raise CloseHistoryError("SYMBOL_INVALID")
    if not page_paths:
        raise CloseHistoryError("NO_PAGE_FILES")
    pages = []
    confirmed: dict[str, tuple[str, str]] = {}
    seen_hashes: set[str] = set()
    for path in sorted(page_paths, key=lambda item: Path(item).name):
        # The raw page has no symbol field; the folder name is the only binding to the symbol.
        if Path(path).resolve().parent.name != symbol:
            raise CloseHistoryError(f"PAGE_FOLDER_SYMBOL_MISMATCH:{Path(path).name}")
        page = parse_page(Path(path))
        if page["sha256"] in seen_hashes:
            raise CloseHistoryError(f"PAGE_DUPLICATE:{page['file_name']}")
        seen_hashes.add(page["sha256"])
        # The newest bar of a file may still be forming; a bar counts only when a later bar exists.
        for row in page["rows"][1:]:
            known = confirmed.get(row["cntr_tm"])
            if known is not None and known[0] != row["close"]:
                raise CloseHistoryError(f"PAGE_ROWS_CONFLICT:{row['cntr_tm']}")
            if known is None:
                confirmed[row["cntr_tm"]] = (row["close"], page["sha256"])
        pages.append({key: page[key] for key in ("file_name", "sha256", "row_count", "first_cntr_tm", "last_cntr_tm")})
    observed_dates = sorted({stamp[:8] for stamp in confirmed})
    if not observed_dates:
        raise CloseHistoryError("NO_CONFIRMED_BARS")
    first, last = (f"{value[:4]}-{value[4:6]}-{value[6:8]}" for value in (observed_dates[0], observed_dates[-1]))
    identity = calendar["identity"]
    in_range = [date_text for date_text in sorted(calendar["sessions"]) if first <= date_text <= last]
    sessions, missing = [], []
    reference_closes = reference_closes or {}
    for session_date in in_range:
        label, offset = final_bar_label(calendar["sessions"][session_date])
        bar = confirmed.get(label)
        if bar is None:
            missing.append(session_date)
            continue
        reasons = []
        if identity["authority_status"] != "ACTIVE":
            reasons.append("SESSION_CALENDAR_NOT_ACTIVE")
        if offset not in LABEL_VERIFIED_UTC_OFFSETS:
            reasons.append("BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET")
        item = {"session_date": session_date, "close": bar[0], "bar_cntr_tm": label,
                "close_type": calendar["sessions"][session_date]["close_type"], "page_sha256": bar[1],
                "verified": not reasons, "unverified_reasons": reasons}
        reference = _positive(reference_closes.get(session_date)) if session_date in reference_closes else None
        if reference is not None:
            item["reference_close"] = format(reference, "f")
            item["reference_difference"] = format(Decimal(bar[0]) - reference, "f")
        sessions.append(item)
    if not sessions:
        raise CloseHistoryError("NO_REGULAR_SESSION_CLOSE_FOUND")
    # Leading and trailing sessions without a confirmed final bar are outside the history, not gaps.
    produced = [item["session_date"] for item in sessions]
    gaps = [date_text for date_text in missing if produced[0] < date_text < produced[-1]]
    uncovered = [f"{value[:4]}-{value[4:6]}-{value[6:8]}" for value in observed_dates
                 if not identity["coverage_start"] <= f"{value[:4]}-{value[4:6]}-{value[6:8]}" <= identity["coverage_end"]]
    history: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "artifact_type": ARTIFACT_TYPE, "symbol": symbol, "exchange": exchange,
        "source": {"provider": "KIWOOM", "api_id": API_ID, "collection": "COWORK_READ_ONLY_CLI_EVIDENCE_FILE",
                   "interval_minutes": INTERVAL_MINUTES, "price_adjustment": "RAW_UNADJUSTED",
                   "bar_label_basis": "BAR_START_TIME_US_EASTERN"},
        "close_definition": {"basis": "FINAL_REGULAR_SESSION_30M_BAR_CLOSE",
                             "bar_selection": "BAR_STARTING_30_MINUTES_BEFORE_CORE_CLOSE",
                             "label": "APPROXIMATE_CLOSE", "official_close": False,
                             "reference_close_use": "DIFFERENCE_DISPLAY_ONLY"},
        "calendar": identity, "pages": pages, "sessions": sessions,
        "first_session": produced[0], "last_session": produced[-1], "session_count": len(sessions),
        "continuity": {"status": "GAPS" if gaps else "CONTIGUOUS", "missing_sessions": gaps},
        "calendar_out_of_coverage_dates": uncovered,
        "order_authority": False, "quantity_authority": "none",
        "history_hash": "0" * 64,
    }
    history["history_hash"] = history_content_hash(history)
    return history


def history_content_hash(history: dict[str, Any]) -> str:
    return canonical_hash({key: value for key, value in history.items() if key != "history_hash"})


def history_errors(history: Any, *, pages_dir: Path | None = None) -> list[str]:
    """Schema, self-hash and (when the page folder is given) page-hash verification."""
    if not isinstance(history, dict):
        return ["CLOSE_HISTORY_NOT_OBJECT"]
    errors = [f"CLOSE_HISTORY_SCHEMA:{item}" for item in validate_instance(history, HISTORY_SCHEMA)]
    if errors:
        return errors
    if history_content_hash(history) != history["history_hash"]:
        errors.append("CLOSE_HISTORY_HASH_MISMATCH")
    dates = [item["session_date"] for item in history["sessions"]]
    if dates != sorted(set(dates)) or history["session_count"] != len(dates):
        errors.append("CLOSE_HISTORY_SESSIONS_NOT_ASCENDING")
    if pages_dir is not None:
        for page in history["pages"]:
            path = Path(pages_dir) / page["file_name"]
            if not path.is_file():
                errors.append(f"CLOSE_HISTORY_PAGE_MISSING:{page['file_name']}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != page["sha256"]:
                errors.append(f"CLOSE_HISTORY_PAGE_HASH_MISMATCH:{page['file_name']}")
    return errors


def closes_by_session(history: dict[str, Any]) -> dict[str, str]:
    return {item["session_date"]: item["close"] for item in history["sessions"]}


def unverified_reasons(history: dict[str, Any], sessions: list[str]) -> list[str]:
    """Reasons that make closes used from this history unverified (calendar authority, label basis, gaps)."""
    wanted = set(sessions)
    reasons = {reason for item in history["sessions"] if item["session_date"] in wanted
               for reason in item["unverified_reasons"]}
    if any(date_text in wanted for date_text in history["continuity"]["missing_sessions"]):
        reasons.add("CLOSE_HISTORY_GAP")
    return sorted(reasons)


def update_conflicts(previous: Any, history: dict[str, Any]) -> list[str]:
    """--update may only extend a valid history: every earlier session must keep the same close."""
    errors = history_errors(previous)
    if errors:
        return ["CLOSE_HISTORY_UPDATE_PREVIOUS_INVALID"] + errors
    if previous["symbol"] != history["symbol"] or previous["exchange"] != history["exchange"]:
        return ["CLOSE_HISTORY_UPDATE_SYMBOL_MISMATCH"]
    new = closes_by_session(history)
    changed = sorted(session for session, close in closes_by_session(previous).items() if new.get(session) != close)
    return [f"CLOSE_HISTORY_UPDATE_CHANGES_EARLIER_SESSION:{session}" for session in changed]


def _write(path: Path, value: dict[str, Any], *, update: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if not path.exists():
        with path.open("xb") as handle:
            handle.write(payload)
        return
    if not update:
        raise FileExistsError(str(path))
    conflicts = update_conflicts(json.loads(path.read_text(encoding="utf-8-sig")), value)
    if conflicts:
        raise CloseHistoryError(conflicts[0])
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regular-session close history from saved Kiwoom 30-minute pages")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="verify saved pages and write one history file (create-only)")
    build.add_argument("--symbol", required=True)
    build.add_argument("--exchange", required=True, choices=("NASDAQ", "NYSE", "AMEX"))
    build.add_argument("--pages-dir", type=Path, required=True, help="folder named after the symbol")
    build.add_argument("--calendar", type=Path, required=True, help="session-calendar artifact JSON")
    build.add_argument("--reference-closes", type=Path, help='optional {"closes": {"YYYY-MM-DD": "price"}}')
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--update", action="store_true",
                       help="replace an existing history only when every earlier session keeps the same close")
    verify = commands.add_parser("verify", help="re-check an existing history file")
    verify.add_argument("--history", type=Path, required=True)
    verify.add_argument("--pages-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            errors = history_errors(json.loads(args.history.read_text(encoding="utf-8-sig")), pages_dir=args.pages_dir)
            print(json.dumps({"status": "FAIL" if errors else "OK", "errors": errors}))
            return 2 if errors else 0
        reference = None
        if args.reference_closes:
            reference = json.loads(args.reference_closes.read_text(encoding="utf-8-sig")).get("closes")
        snapshot, authority_failure = load_production_snapshot(current_time())
        calendar = load_calendar(args.calendar, snapshot, authority_failure)
        history = build_history(
            symbol=args.symbol, exchange=args.exchange, page_paths=sorted(args.pages_dir.glob("*.json")),
            calendar=calendar, reference_closes=reference)
        errors = history_errors(history)
        if errors:
            raise CloseHistoryError(errors[0])
        _write(args.output, history, update=args.update)
    except FileExistsError:
        print(json.dumps({"status": "FAIL", "error": "CLOSE_HISTORY_OUTPUT_EXISTS"}))
        return 2
    except (CloseHistoryError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 2
    summary = {
        "status": "OK", "symbol": history["symbol"], "session_count": history["session_count"],
        "first_session": history["first_session"], "last_session": history["last_session"],
        "continuity": history["continuity"]["status"], "calendar_authority": history["calendar"]["authority_status"],
        "history_hash": history["history_hash"]}
    if calendar["authority_failure"]:
        # The history file keeps its schema keys; the reason is shown here only.
        summary["calendar_authority_reason"] = calendar["authority_failure"]
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
