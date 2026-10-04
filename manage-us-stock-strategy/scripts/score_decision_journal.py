#!/usr/bin/env python3
"""Score the card decisions in the decision journal (Cold Path, read only).

The journal (stock-strategy-system/decision_journal.json) is only READ here, through load_journal. Scores
are written to a new folder under workspace/outputs/journal-scores/ and never into the journal: the
journal holds what a person confirmed, a score is a recomputable view of it.

For every card_decision entry (the card's analysis action) and for the latest card_user_decision of that
decision (what the user actually did) the scorer reports, at 5, 20 and 60 U.S. sessions after the
decision session:
  vs cash : ADD/HOLD  = stock return - 0 ; TRIM/EXIT = 0 - stock return
  vs SPY  : ADD/HOLD  = stock return - SPY return ; TRIM/EXIT = SPY return - stock return
Rules (same point-in-time rule as the sidecar forward outcomes, which are not touched):
  - only finished sessions count: the target session's core close must be <= evaluation_as_of;
  - closes are the verified Kiwoom 30-minute-bar approximate closes of regular_session_close_history.
    A close with unverified reasons is labelled REFERENCE_ONLY;
  - SPY is outside the Kiwoom scope: its closes come from an optional reference file
    <closes_root>/reference-closes/SPY.json and are always labelled REFERENCE_ONLY;
  - corporate actions (splits) are applied from <closes_root>/corporate-actions.json; an invalid file or an
    unexplained jump in the window makes the result NOT_SCORABLE instead of a wrong number;
  - a failure is a status, never an exception: PENDING (with the sessions left), NOT_SCORABLE (with a reason).
No order, quantity or price target exists in the output.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from corporate_actions import STATUS_INVALID, STATUS_OK, adjust_closes, applicable_actions
from portfolio_exposure import SPLIT_GUARD_HIGH, SPLIT_GUARD_LOW
from portfolio_review_journal import (
    DEFAULT_JOURNAL_PATH, JOURNAL_CARD_DECISION, JOURNAL_CARD_USER_DECISION, load_journal,
)
from validation_common import load_json, write_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
LOCALE_PATH = SKILL_ROOT / "assets/locales/portfolio-exposure-ko-KR.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/journal-scores"
DEFAULT_CLOSES_ROOT = REPO_ROOT / "workspace/outputs/regular-session-closes"
PROTECTED_OUTPUT_PARENTS = ("stock-strategy-system", "workspace/policies", "workspace/state")
REPORT_FILE = "journal-scores.json"
SCHEMA_VERSION = "journal-score-1.0"
REPORT_TYPE = "DECISION_JOURNAL_SCORES"
HORIZONS = (5, 20, 60)
BENCHMARK_SYMBOL = "SPY"
REFERENCE_CLOSES_DIR = "reference-closes"
REFERENCE_CLOSES_VERSION = "reference-closes-1.0"
MIN_SCORED_FOR_CONCLUSION = 30
LONG_ACTIONS = ("ADD", "HOLD")
REDUCE_ACTIONS = ("TRIM", "EXIT")
PRICE_SOURCE = "KIWOOM_30M_APPROX_CLOSE"
PLACES = Decimal("0.000001")


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() and number > 0 else None


def _text(number: Decimal) -> str:
    return format(number.quantize(PLACES, rounding=ROUND_HALF_EVEN), "f")


def _moment(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def load_reference_closes(closes_root: Path, symbol: str = BENCHMARK_SYMBOL) -> dict[str, Any]:
    """{status: MISSING|OK|INVALID, closes: {session: text}, errors: [...]} from reference-closes/<SYMBOL>.json."""
    path = Path(closes_root) / REFERENCE_CLOSES_DIR / f"{symbol}.json"
    if not path.is_file():
        return {"status": "MISSING", "closes": {}, "errors": []}
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"status": "INVALID", "closes": {}, "errors": ["REFERENCE_CLOSES_NOT_JSON"]}
    errors: list[str] = []
    if not isinstance(document, dict) or set(document) != {"schema_version", "symbol", "source_note", "closes"}:
        return {"status": "INVALID", "closes": {}, "errors": ["REFERENCE_CLOSES_KEYS"]}
    if document["schema_version"] != REFERENCE_CLOSES_VERSION or document["symbol"] != symbol:
        errors.append("REFERENCE_CLOSES_IDENTITY")
    if not isinstance(document["source_note"], str) or not document["source_note"].strip():
        errors.append("REFERENCE_CLOSES_SOURCE_NOTE")
    closes: dict[str, str] = {}
    raw = document["closes"]
    if not isinstance(raw, dict) or not raw:
        errors.append("REFERENCE_CLOSES_EMPTY")
    else:
        for session, value in raw.items():
            try:
                datetime.strptime(session, "%Y-%m-%d")
            except (TypeError, ValueError):
                errors.append(f"REFERENCE_CLOSES_DATE:{session}")
                continue
            if _decimal(value) is None:
                errors.append(f"REFERENCE_CLOSES_VALUE:{session}")
            else:
                closes[session] = str(value)
    if errors:
        return {"status": "INVALID", "closes": {}, "errors": errors[:5]}
    return {"status": "OK", "closes": closes, "errors": []}


def _split_suspect(closes: dict[str, str], window: list[str]) -> bool:
    """True when two consecutive sessions of the window jump like an unadjusted split."""
    previous: Decimal | None = None
    for session in window:
        current = _decimal(closes.get(session))
        if current is None:
            previous = None
            continue
        if previous is not None:
            ratio = current / previous
            if ratio <= Decimal(str(SPLIT_GUARD_LOW)) or ratio >= Decimal(str(SPLIT_GUARD_HIGH)):
                return True
        previous = current
    return False


def _not_scorable(horizon: int, reason: str, **extra: Any) -> dict[str, Any]:
    return {"horizon_sessions": horizon, "status": "NOT_SCORABLE", "reason": reason, **extra}


def _score_horizon(*, horizon: int, symbol: str, direction: str, start_session: str, sessions: list[str],
                   calendar_rows: dict[str, Any], completed: list[str], closes: dict[str, dict[str, str]],
                   unverified: dict[str, dict[str, list[str]]], benchmark: dict[str, Any],
                   evaluation_as_of: datetime) -> dict[str, Any]:
    index = sessions.index(start_session)
    if index + horizon >= len(sessions):
        return _not_scorable(horizon, "CALENDAR_DOES_NOT_COVER_HORIZON")
    target = sessions[index + horizon]
    target_closed = _moment(calendar_rows[target].get("core_close_at"))
    if target_closed is None:
        return _not_scorable(horizon, "CALENDAR_CLOSE_TIME_INVALID", target_session=target)
    if target_closed > evaluation_as_of:
        elapsed = sum(1 for session in completed if session > start_session)
        return {"horizon_sessions": horizon, "status": "PENDING", "target_session": target,
                "remaining_sessions": max(horizon - elapsed, 1)}
    per_symbol = closes.get(symbol)
    if per_symbol is None:
        return _not_scorable(horizon, f"CLOSE_HISTORY_MISSING:{symbol}", target_session=target)
    start_close, target_close = _decimal(per_symbol.get(start_session)), _decimal(per_symbol.get(target))
    if start_close is None:
        return _not_scorable(horizon, "START_CLOSE_MISSING", target_session=target)
    if target_close is None:
        return _not_scorable(horizon, "TARGET_CLOSE_MISSING", target_session=target)
    window = sessions[index:index + horizon + 1]
    if _split_suspect(per_symbol, window):
        return _not_scorable(horizon, "POSSIBLE_UNADJUSTED_SPLIT", target_session=target)
    reasons = sorted({reason for session in (start_session, target)
                      for reason in (unverified.get(symbol) or {}).get(session, [])})
    stock_return = target_close / start_close - 1
    sign = 1 if direction == "LONG" else -1
    result: dict[str, Any] = {
        "horizon_sessions": horizon, "status": "SCORED", "target_session": target,
        "observed_at": target_closed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "price_source": PRICE_SOURCE, "price_grade": "REFERENCE_ONLY" if reasons else "GRADE_B",
        "unverified_reasons": reasons, "stock_return": _text(stock_return),
        "vs_cash": _text(sign * stock_return),
    }
    spy_start, spy_target = _decimal(benchmark["closes"].get(start_session)), _decimal(benchmark["closes"].get(target))
    if benchmark["status"] != "OK":
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "BENCHMARK_UNAVAILABLE",
                                  "reason": f"REFERENCE_CLOSES_{benchmark['status']}"}
    elif spy_start is None or spy_target is None:
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "BENCHMARK_UNAVAILABLE",
                                  "reason": "BENCHMARK_CLOSE_MISSING"}
    elif _split_suspect(benchmark["closes"], window):
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "BENCHMARK_UNAVAILABLE",
                                  "reason": "POSSIBLE_UNADJUSTED_SPLIT"}
    else:
        benchmark_return = spy_target / spy_start - 1
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "OK", "label": "REFERENCE_ONLY",
                                  "benchmark_return": _text(benchmark_return),
                                  "value": _text(sign * (stock_return - benchmark_return))}
    return result


def _completed_sessions(calendar: dict[str, Any], evaluation_as_of: datetime) -> list[str]:
    """Sessions whose core close is at or before the evaluation time (the only closes that may be used)."""
    done = []
    for session in sorted(calendar["sessions"]):
        closed = _moment(calendar["sessions"][session].get("core_close_at"))
        if closed is not None and closed <= evaluation_as_of:
            done.append(session)
    return done


def _subjects(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One ANALYSIS subject per card_decision and one USER subject for the latest user decision of it."""
    latest_user: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry.get("entry_type") == JOURNAL_CARD_USER_DECISION:
            latest_user[entry["payload"]["decision_id"]] = entry  # a correction is a later entry: the last one wins
    subjects: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("entry_type") != JOURNAL_CARD_DECISION:
            continue
        payload = entry["payload"]
        subjects.append({
            "decision_id": payload["decision_id"], "kind": "ANALYSIS", "ticker": payload["ticker"],
            "action": payload["analysis_action"], "sidecar_action": payload["sidecar_action"],
            "conviction": payload["conviction"], "start_session": payload["decision_session"],
            "recorded_reference_close": payload["reference_close"], "sequence": entry["sequence"]})
        user = latest_user.get(payload["decision_id"])
        if user is not None:
            subjects.append({
                "decision_id": payload["decision_id"], "kind": "USER", "ticker": payload["ticker"],
                "action": user["payload"]["user_action"], "sidecar_action": None, "conviction": None,
                "start_session": user["payload"]["effective_session"], "recorded_reference_close": None,
                "sequence": user["sequence"]})
    return subjects


def score_journal(journal: dict[str, Any], *, calendar: dict[str, Any] | None, calendar_failure: str | None = None,
                  closes: dict[str, dict[str, str]], unverified: dict[str, dict[str, list[str]]],
                  benchmark: dict[str, Any], corporate_actions: dict[str, Any],
                  evaluation_as_of: datetime) -> dict[str, Any]:
    """The score report. Pure: no file is read or written here."""
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "report_type": REPORT_TYPE,
        "evaluation_as_of": evaluation_as_of.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "journal": {"status": journal["status"], "entry_count": len(journal["entries"]),
                    "head_sha256": journal["head_sha256"], "errors": journal["errors"]},
        "calendar": ({"status": "LOADED", **calendar["identity"]} if calendar is not None
                     else {"status": "UNAVAILABLE", "reason": calendar_failure}),
        "corporate_actions": {"status": corporate_actions["status"], "sha256": corporate_actions.get("sha256"),
                              "errors": list(corporate_actions.get("errors") or [])},
        "benchmark": {"symbol": BENCHMARK_SYMBOL, "label": "REFERENCE_ONLY", "status": benchmark["status"],
                      "errors": list(benchmark.get("errors") or [])},
        "horizons": list(HORIZONS), "results": [],
        "writes_journal": False, "order_authority": False, "quantity_authority": "none",
    }
    if journal["status"] == "CORRUPT":
        report["summary"] = _summary([])
        return report
    sessions = sorted(calendar["sessions"]) if calendar is not None else []
    completed = _completed_sessions(calendar, evaluation_as_of) if calendar is not None else []
    adjusted = closes
    if calendar is not None and corporate_actions["status"] == STATUS_OK and completed:
        actions = applicable_actions(corporate_actions["actions"], completed[-1])
        adjusted = adjust_closes({**closes, BENCHMARK_SYMBOL: benchmark["closes"]}, actions)
        benchmark = {**benchmark, "closes": adjusted.pop(BENCHMARK_SYMBOL, benchmark["closes"])}
    for subject in _subjects(journal["entries"]):
        direction = ("LONG" if subject["action"] in LONG_ACTIONS else
                     "REDUCE" if subject["action"] in REDUCE_ACTIONS else None)
        row = {key: subject[key] for key in ("decision_id", "kind", "ticker", "action", "sidecar_action",
                                             "conviction", "start_session", "sequence")}
        row["recorded_reference_close"] = subject["recorded_reference_close"]
        if direction is None:
            row["horizons"] = [_not_scorable(horizon, "USER_ACTION_NOT_SCORABLE") for horizon in HORIZONS]
        elif calendar is None:
            row["horizons"] = [_not_scorable(horizon, "SESSION_CALENDAR_UNAVAILABLE") for horizon in HORIZONS]
        elif corporate_actions["status"] == STATUS_INVALID:
            row["horizons"] = [_not_scorable(horizon, "CORPORATE_ACTIONS_INVALID") for horizon in HORIZONS]
        elif subject["start_session"] not in sessions:
            row["horizons"] = [_not_scorable(horizon, "DECISION_SESSION_NOT_IN_CALENDAR") for horizon in HORIZONS]
        else:
            row["horizons"] = [
                _score_horizon(horizon=horizon, symbol=subject["ticker"], direction=direction,
                               start_session=subject["start_session"], sessions=sessions,
                               calendar_rows=calendar["sessions"], completed=completed, closes=adjusted,
                               unverified=unverified, benchmark=benchmark, evaluation_as_of=evaluation_as_of)
                for horizon in HORIZONS]
            start_close = _decimal((adjusted.get(subject["ticker"]) or {}).get(subject["start_session"]))
            recorded = _decimal(subject["recorded_reference_close"])
            if start_close is not None and recorded is not None:
                row["start_close_vs_recorded_reference"] = _text(start_close - recorded)
        report["results"].append(row)
    report["summary"] = _summary(report["results"])
    return report


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = [row for row in results if row["kind"] == "ANALYSIS"]

    def statuses(row: dict[str, Any]) -> set[str]:
        return {item["status"] for item in row["horizons"]}

    scored_by_horizon = {str(horizon): sum(1 for row in analysis for item in row["horizons"]
                                           if item["horizon_sessions"] == horizon and item["status"] == "SCORED")
                         for horizon in HORIZONS}
    best = max(scored_by_horizon.values(), default=0)
    return {
        "decision_count": len(analysis),
        "pending_decisions": sum(1 for row in analysis if "PENDING" in statuses(row)),
        "fully_scored_decisions": sum(1 for row in analysis if statuses(row) == {"SCORED"}),
        "unscorable_decisions": sum(1 for row in analysis if "NOT_SCORABLE" in statuses(row)),
        "scored_by_horizon": scored_by_horizon,
        "min_scored_for_conclusion": MIN_SCORED_FOR_CONCLUSION,
        "conclusion_allowed": best >= MIN_SCORED_FOR_CONCLUSION,
    }


def _messages() -> dict[str, str]:
    return load_json(LOCALE_PATH)["messages"]


def _horizon_text(item: dict[str, Any], messages: dict[str, str]) -> str:
    horizon = item["horizon_sessions"]
    if item["status"] == "SCORED":
        benchmark = item["vs_benchmark"]
        spy = messages["score_vs_spy"].format(value=benchmark["value"]) if benchmark["status"] == "OK" \
            else messages["score_vs_spy_unavailable"]
        return messages["score_h_scored"].format(horizon=horizon, vs_cash=item["vs_cash"], spy=spy,
                                                 grade=item["price_grade"])
    if item["status"] == "PENDING":
        return messages["score_h_pending"].format(horizon=horizon, remaining=item["remaining_sessions"])
    return messages["score_h_unscorable"].format(horizon=horizon, reason=item["reason"])


def render_report(report: dict[str, Any]) -> list[str]:
    messages = _messages()
    if report["journal"]["status"] == "CORRUPT":
        return [messages["score_journal_unreadable"].format(reason=",".join(report["journal"]["errors"]))]
    summary = report["summary"]
    lines = [messages["score_summary"].format(
        total=summary["decision_count"], pending=summary["pending_decisions"],
        done=summary["fully_scored_decisions"], unscorable=summary["unscorable_decisions"])]
    for row in report["results"]:
        lines.append(messages["score_row"].format(
            ticker=row["ticker"], kind=row["kind"], action=row["action"], session=row["start_session"],
            horizons=" / ".join(_horizon_text(item, messages) for item in row["horizons"])))
    if not summary["conclusion_allowed"]:
        lines.append(messages["score_no_conclusion"].format(
            minimum=summary["min_scored_for_conclusion"], best=max(summary["scored_by_horizon"].values())))
    lines.append(messages["summary_no_order"])
    return lines


def check_output_root(output_root: Path, journal_path: Path, repo_root: Path = REPO_ROOT) -> Path:
    """The only place scores may be written: never the journal, never state, policy or a parent of the journal."""
    root = Path(output_root).resolve()
    journal = Path(journal_path).resolve()
    if journal == root or journal.parent == root or root in journal.parents:
        raise ValueError("OUTPUT_ROOT_CONTAINS_JOURNAL")
    for protected in PROTECTED_OUTPUT_PARENTS:
        guarded = (Path(repo_root) / protected).resolve()
        if root == guarded or guarded in root.parents:
            raise ValueError("OUTPUT_ROOT_IN_PROTECTED_FOLDER")
    return root


def write_report(report: dict[str, Any], output_root: Path, journal_path: Path, now: datetime) -> Path:
    root = check_output_root(output_root, journal_path)
    directory = root / now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    index = 1
    while directory.exists():
        directory = root / f"{now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{index}"
        index += 1
    write_json(directory / REPORT_FILE, report)
    return directory / REPORT_FILE


def load_inputs(*, tickers: list[str], closes_root: Path, calendar_path: Path | None, now: datetime) -> dict[str, Any]:
    """Calendar, close histories, corporate actions and the SPY reference file. Failures stay statuses."""
    from run_portfolio_exposure_review import (  # noqa: PLC0415 - heavy imports only when scoring from files
        ReviewRunError, load_close_histories, load_corporate_actions, load_session_calendar,
    )

    calendar: dict[str, Any] | None = None
    failure: str | None = None
    try:
        calendar, _authority = load_session_calendar(calendar_path, now)
    except (ReviewRunError, OSError, ValueError) as exc:
        failure = str(exc) or type(exc).__name__
    closes: dict[str, dict[str, str]] = {}
    unverified: dict[str, dict[str, list[str]]] = {}
    histories: dict[str, Any] = {}
    corporate: dict[str, Any] = {"status": "MISSING", "sha256": None, "errors": [], "actions": []}
    if calendar is not None:
        closes, unverified, histories = load_close_histories(sorted(set(tickers)), closes_root, calendar)
        corporate = load_corporate_actions(closes_root, sorted(calendar["sessions"]))
    return {"calendar": calendar, "calendar_failure": failure, "closes": closes, "unverified": unverified,
            "close_histories": histories, "corporate_actions": corporate,
            "benchmark": load_reference_closes(closes_root)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the card decisions in the decision journal (read only)")
    parser.add_argument("--journal", type=Path, default=REPO_ROOT / DEFAULT_JOURNAL_PATH)
    parser.add_argument("--closes-root", type=Path, default=DEFAULT_CLOSES_ROOT)
    parser.add_argument("--calendar", type=Path, default=None, help="explicit session calendar artifact (labelled if not active)")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--evaluation-as-of", default=None, help="ISO time with offset; default now")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    now = datetime.now(timezone.utc)
    evaluation_as_of = _moment(args.evaluation_as_of) if args.evaluation_as_of else now
    messages = _messages()
    if evaluation_as_of is None:
        print(messages["score_journal_unreadable"].format(reason="EVALUATION_AS_OF_INVALID"))
        return 2
    try:
        check_output_root(args.output_root, args.journal)
    except ValueError as exc:
        print(messages["score_journal_unreadable"].format(reason=str(exc)))
        return 2
    journal = load_journal(args.journal)
    tickers = [entry["payload"]["ticker"] for entry in journal["entries"]
               if entry.get("entry_type") == JOURNAL_CARD_DECISION]
    inputs = load_inputs(tickers=tickers, closes_root=args.closes_root, calendar_path=args.calendar,
                         now=evaluation_as_of) if journal["status"] == "OK" else {
        "calendar": None, "calendar_failure": None, "closes": {}, "unverified": {}, "close_histories": {},
        "corporate_actions": {"status": "MISSING", "sha256": None, "errors": [], "actions": []},
        "benchmark": {"status": "MISSING", "closes": {}, "errors": []}}
    report = score_journal(journal, evaluation_as_of=evaluation_as_of, **{
        key: inputs[key] for key in ("calendar", "calendar_failure", "closes", "unverified", "benchmark",
                                     "corporate_actions")})
    report["close_histories"] = inputs["close_histories"]
    path = write_report(report, args.output_root, args.journal, now)
    print("\n".join(render_report(report)))
    print(messages["score_path"].format(path=str(path)))
    return 2 if journal["status"] == "CORRUPT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
