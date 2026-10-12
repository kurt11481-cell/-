#!/usr/bin/env python3
"""Redesign T1 F5: the deterministic daily auto-core (one Windows task, no human input, no orders).

daily   1 read the kill switch and workspace/policies/auto_core.json, record the git commit SHA and dirty paths
        2 Kiwoom account reads + transaction-history evidence (F2, F3) and the auto reconciliation (F4,
          reconcile_broker_state.reconcile_auto): compare mode never writes, apply mode writes only when
          invariants I1-I5 pass
        3 30-minute bars (collect_30m.ps1, read-only kiwoomcli) for held symbols, the watchlist members and
          the benchmark, then the regular-session close histories (build --update, never changes a close)
        4 the exposure review (run_portfolio_exposure_review.py, read-only)
        5 workspace/outputs/auto-core/<YYYY-MM-DD>/result.json and workspace/outputs/auto-core/LATEST.json

The account reads run before the 30-minute collection so the broker snapshot is judged and (in apply mode)
written while it is fresh (the proposal expires 15 minutes after the read); a first collection of a new
symbol can take minutes. There are no retries inside a run: the first failure stops it (status FAIL,
exit 1) and the next scheduled run is the retry. Running twice on one day gives the same result: the
reconciliation of an already written snapshot is NO_CHANGE, saved 30-minute pages are reused and the
compare streak is counted against the previous day's result only.
A run that fails at any step never counts toward the compare streak (it is reset to 0); a run held only
because a settlement due that day is not shown yet keeps it (no +1, no reset). Kiwoom is read only with the
policy's token profile alias: without one the run fails before any read.
Exit code: 0 for OK or HOLD, 1 for FAIL.

decide  redesign T2 (auto_core_decide.py): judgments, buy requirements and gates, LOC order tickets for the
        user to enter (order stage 1), outcome classification, decision journal, compare with the integrated
        check. It reads that day's daily result and never repeats the broker reconciliation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import auto_core_reconcile as core
from reconcile_broker_state import (
    AUTO_OUTPUT_ROOT, AUTO_RESULT_FILE, DAY_FOLDER, KST, compare_reference, kst_day, previous_reconcile,
    reconcile_auto,
)
from validation_common import load_json, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
RESULT_SCHEMA = SKILL_ROOT / "schemas/auto-core-result.schema.json"
RESULT_FILE = "result.json"
LATEST_FILE = "LATEST.json"
RESULT_SCHEMA_VERSION = "auto-core-result-1.0"
CLOSES_ROOT = REPO_ROOT / "workspace/outputs/regular-session-closes"
WATCHLIST_PATH = REPO_ROOT / "docs/claude/watchlist-registry.json"
COLLECT_SCRIPT = Path(__file__).resolve().with_name("collect_30m.ps1")
FIRST_COLLECTION_DAY = date(2026, 4, 1)
EXCHANGES = {"ND": "NASDAQ", "NY": "NYSE", "NA": "AMEX"}
READY_FOR_RECORDING = "\uae30\ub85d \ubaa8\ub4dc \ucf24 \uc900\ube44\ub428"  # "ready to switch recording on" (Korean)
# "recording mode needed (baseline old)" (Korean): compare mode past 80% of the fill window (T1 r3 C4).
RECORDING_NEEDED_BASELINE_OLD = "\uae30\ub85d \ubaa8\ub4dc \ucf1c\uae30 \ud544\uc694(\uae30\uc900 \uc624\ub798\ub428)"
POLICY_PATHS = {
    "readonly": REPO_ROOT / "workspace/policies/kiwoom-readonly-policy.json",
    "rate": REPO_ROOT / "workspace/policies/kiwoom-rate-limit-policy.json",
    "broker": REPO_ROOT / "workspace/policies/kiwoom-broker-readonly-policy.json",
    "alert": REPO_ROOT / "stock-strategy-system/alert_policy.json",
    "state": REPO_ROOT / "stock-strategy-system/portfolio_state.json",
    "journal": REPO_ROOT / "stock-strategy-system/decision_journal.json",
}


class StepFailure(RuntimeError):
    """The first failure of a run; the run stops and reports FAIL."""


def kiwoom_profile(readonly_policy_path: Path) -> str:
    """T1 r3 C6: the policy's token profile alias (standing rule 2026-10-07); none means no Kiwoom read."""
    try:
        policy = load_json(readonly_policy_path)
    except (OSError, ValueError) as exc:
        raise StepFailure("KIWOOM_READONLY_POLICY_UNREADABLE") from exc
    alias = policy.get("token_profile_alias") if isinstance(policy, dict) else None
    if not isinstance(alias, str) or not alias.strip():
        raise StepFailure("KIWOOM_PROFILE_ALIAS_MISSING")
    return alias


# ---------------------------------------------------------------------------------------------
# Symbols and 30-minute collection
# ---------------------------------------------------------------------------------------------

def symbols_for_run(*, output_directory: Path, state_path: Path, watchlist_path: Path,
                    extra: list[str]) -> list[str]:
    """Held symbols (broker read of this run, else the state) + watchlist members + configured extras."""
    held: set[str] = set()
    snapshot_path = output_directory / "kiwoom_broker_snapshot.shadow.json"
    if snapshot_path.is_file():
        for item in load_json(snapshot_path).get("holdings") or []:
            if isinstance(item.get("held_quantity"), (int, float)) and item["held_quantity"] > 0:
                held.add(str(item["ticker"]).upper())
    else:
        for symbol, quantity in (load_json(state_path).get("holdings") or {}).items():
            if isinstance(quantity, int) and quantity > 0:
                held.add(str(symbol).upper())
    try:
        members = [str(item.get("code") or "").upper() for item in load_json(watchlist_path).get("members") or []
                   if isinstance(item, dict)]
    except (OSError, ValueError) as exc:
        raise StepFailure("WATCHLIST_UNREADABLE") from exc
    symbols = held | {symbol for symbol in members if symbol} | {str(symbol).upper() for symbol in extra}
    return sorted(symbols)


def history_path(symbol: str, closes_root: Path = CLOSES_ROOT) -> Path:
    return closes_root / "history" / f"{symbol}.close-history.json"


def known_exchange(symbol: str, closes_root: Path = CLOSES_ROOT) -> tuple[str | None, str | None]:
    """(exchange, last_session) of an existing history, else (None, None)."""
    path = history_path(symbol, closes_root)
    if not path.is_file():
        return None, None
    history = json.loads(path.read_text(encoding="utf-8-sig"))
    return history.get("exchange"), history.get("last_session")


def resolve_exchange(symbol: str, *, runtime: Path, rate_policy: dict[str, Any],
                     reader: Callable[..., list[dict[str, Any]]] | None = None) -> str:
    """Dynamic Kiwoom identity lookup (usa10098, read-only) for a symbol without a history; no guessing."""
    if reader is None:
        from kiwoom_runtime_bridge import invoke_bridge_batch as reader
    results = reader([{"operation": "exchange_lookup", "ticker": symbol, "fx_applied": False}],
                     runtime=runtime, policy=rate_policy)
    rows = [row for result in results if result.get("bridge_status") == "PASS"
            for row in result.get("data") or [] if isinstance(row, dict)
            and str(row.get("stk_cd") or "").upper() == symbol]
    codes = {str(row.get("stex_tp") or "") for row in rows}
    if len(codes) != 1 or next(iter(codes)) not in EXCHANGES:
        raise StepFailure(f"EXCHANGE_UNRESOLVED:{symbol}")
    return EXCHANGES[next(iter(codes))]


def collect_bars(symbol: str, exchange: str, *, newest: date, oldest: date, profile: str,
                 pages_root: Path, runner: Callable[..., Any] = subprocess.run) -> None:
    """Run collect_30m.ps1 (read-only kiwoomcli usa06011). Saved pages are reused; no retry."""
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
               "-File", str(COLLECT_SCRIPT), "-Symbol", symbol, "-Exchange", exchange,
               "-Newest", newest.strftime("%Y%m%d"), "-Oldest", oldest.strftime("%Y%m%d"),
               "-KiwoomProfile", profile, "-OutRoot", str(pages_root)]
    completed = runner(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       check=False, timeout=3600)
    if completed.returncode != 0:
        raise StepFailure(f"BAR_COLLECTION_FAILED:{symbol}:{completed.returncode}")


def update_history(symbol: str, exchange: str, *, now: datetime, closes_root: Path = CLOSES_ROOT) -> dict[str, Any]:
    """regular_session_close_history build --update in-process with the active production calendar."""
    from regular_session_close_history import (
        CloseHistoryError, _write, build_history, calendar_from_snapshot, history_errors, load_production_snapshot,
    )

    snapshot, failure = load_production_snapshot(now)
    if snapshot is None:
        raise StepFailure(f"SESSION_CALENDAR_UNAVAILABLE:{failure}")
    try:
        history = build_history(symbol=symbol, exchange=exchange,
                                page_paths=sorted((closes_root / "pages" / symbol).glob("*.json")),
                                calendar=calendar_from_snapshot(snapshot), reference_closes=None)
        errors = history_errors(history)
        if errors:
            raise CloseHistoryError(errors[0])
        _write(history_path(symbol, closes_root), history, update=True)
    except (CloseHistoryError, OSError, ValueError) as exc:
        raise StepFailure(f"CLOSE_HISTORY_FAILED:{symbol}:{exc}") from exc
    return {"symbol": symbol, "last_session": history["last_session"], "sessions": history["session_count"],
            "continuity": history["continuity"]["status"]}


# ---------------------------------------------------------------------------------------------
# Exposure review summary
# ---------------------------------------------------------------------------------------------

def run_exposure() -> dict[str, Any]:
    from run_portfolio_exposure_review import ReviewRunError, build_parser, run

    try:
        review, target = run(build_parser().parse_args([]))
    except (ReviewRunError, OSError, ValueError, KeyError) as exc:
        raise StepFailure(f"EXPOSURE_REVIEW_FAILED:{exc}") from exc
    exposure, lines = review.get("exposure") or {}, review.get("review_lines") or {}
    return {
        "E": exposure.get("effective"), "N": exposure.get("nominal"), "status": exposure.get("status"),
        "band": (review.get("band") or {}).get("state"),
        "lines": {"status": lines.get("status"), "hwm_usd": lines.get("hwm_usd"),
                  "next_line": (lines.get("next_line") or {}).get("line_id"), "reasons": lines.get("reasons") or []},
        "holds": [item["id"] for item in (review.get("fail_closed") or {}).get("triggers") or [] if item.get("active")],
        "evaluation_session": review.get("evaluation_session"),
        "path": core._repo_relative(target),
    }


# ---------------------------------------------------------------------------------------------
# Compare streak
# ---------------------------------------------------------------------------------------------

def _previous_result(output_root: Path, day: str) -> dict[str, Any] | None:
    folders = sorted(path for path in Path(output_root).glob(f"*/{RESULT_FILE}")
                     if DAY_FOLDER.fullmatch(path.parent.name) and path.parent.name < day)
    try:
        return load_json(folders[-1]) if folders else None
    except (OSError, ValueError):
        return None


def _ledger_snapshot_after(state_path: Path, since: str) -> dict[str, Any] | None:
    """Holdings and cash right after the first ledger entry confirmed after `since` (human path)."""
    from apply_user_confirmed_broker_snapshot import default_ledger_path, ledger_status
    from run_portfolio_exposure_review import read_ledger_entries, reconstruct_snapshots

    ledger_path = default_ledger_path(state_path)
    status = ledger_status(ledger_path)
    if not status["exists"] or not status["chain_ok"]:
        return None
    entries = read_ledger_entries(ledger_path)
    # Only a human-path entry counts here; the auto-core's own writes are what is being compared.
    later = [entry for entry in entries if str(entry.get("confirmed_at") or "") > since
             and entry.get("confirmation_method") != "AUTO_CORE_INVARIANTS"]
    if not later:
        return None
    snapshots, _, _ = reconstruct_snapshots(load_json(state_path), entries, chain_ok=True, ledger_exists=True)
    revision = later[0].get("state_revision_after")
    return next((item for item in snapshots if item.get("state_revision") == revision), {"missing": revision})


def compare_streak(*, reconcile: dict[str, Any], previous_reconcile_result: dict[str, Any] | None,
                   previous_result: dict[str, Any] | None, state_path: Path) -> dict[str, Any]:
    """Consecutive days on which the previous day's would_apply proved right.

    Right means: the first human-path ledger entry after that run holds the same holdings and cash
    (within 1.00 USD), or, with no such entry, today's read is explained from it by broker fills and
    classified cash flows (the same I2/I3 checks). Anything else resets the streak to 0, except a day held
    only because a settlement due today is not shown yet (T1 r3 C4 b): it keeps the streak (no +1, no reset)
    and records why. previous_reconcile_result is the compare reference (reconcile_broker_state.compare_reference).
    """
    previous_compare = (previous_result or {}).get("compare") or {}
    previous_streak = int(previous_compare.get("streak") or 0)
    baseline = (previous_reconcile_result or {}).get("applied") or (previous_reconcile_result or {}).get("would_apply")
    if reconcile.get("status") != "OK":
        check = reconcile.get("compare_check")
        if reconcile.get("status") == "HOLD" and core.d0_only(reconcile.get("reasons")) and (
                not isinstance(check, dict) or check.get("explained") is True or core.d0_only(check.get("reasons"))):
            return {"streak": previous_streak, "last_mismatch": previous_compare.get("last_mismatch"),
                    "basis": "KEPT_D0_SETTLEMENT_NOT_SHOWN", "kept_reasons": list(reconcile["reasons"])[:10]}
        return {"streak": 0, "last_mismatch": {"reason": "TODAY_NOT_OK", "codes": reconcile.get("reasons", [])[:10]}}
    if not isinstance(baseline, dict):
        return {"streak": 0, "last_mismatch": {"reason": "NO_PREVIOUS_WOULD_APPLY", "codes": []}}
    human = _ledger_snapshot_after(state_path, str(previous_reconcile_result.get("generated_at") or ""))
    if human is not None:
        if "missing" in human:
            return {"streak": 0, "last_mismatch": {"reason": "LEDGER_SNAPSHOT_NOT_REPLAYABLE", "codes": []}}
        same_holdings = {key: value for key, value in (human.get("holdings") or {}).items() if value} == \
            {key: value for key, value in (baseline.get("holdings") or {}).items() if value}
        cash_human, cash_core = core._decimal(human.get("cash_usd")), core._decimal(baseline.get("available_cash_usd"))
        same_cash = cash_human is not None and cash_core is not None and abs(cash_human - cash_core) <= Decimal("1.00")
        if same_holdings and same_cash:
            return {"streak": previous_streak + 1, "last_mismatch": None, "basis": "HUMAN_LEDGER_ENTRY"}
        return {"streak": 0, "last_mismatch": {"reason": "HUMAN_LEDGER_DIFFERS",
                                               "codes": [code for code, same in (("HOLDINGS", same_holdings),
                                                                                 ("CASH", same_cash)) if not same]}}
    check = reconcile.get("compare_check") or {}
    if check.get("explained") is True:
        return {"streak": previous_streak + 1, "last_mismatch": None, "basis": "EXPLAINED_BY_FILLS"}
    return {"streak": 0, "last_mismatch": {"reason": "NOT_EXPLAINED_BY_FILLS", "codes": check.get("reasons", [])[:10]}}


# ---------------------------------------------------------------------------------------------
# The daily run
# ---------------------------------------------------------------------------------------------

def daily(*, output_root: Path = AUTO_OUTPUT_ROOT, config_path: Path = core.CONFIG_PATH,
          now: datetime | None = None, reader: Callable[..., list[dict[str, Any]]] | None = None,
          exchange_reader: Callable[..., list[dict[str, Any]]] | None = None,
          collector: Callable[..., None] = collect_bars, history_updater: Callable[..., dict[str, Any]] = update_history,
          exposure_runner: Callable[[], dict[str, Any]] = run_exposure,
          provenance: dict[str, Any] | None = None, policy_paths: dict[str, Path] | None = None,
          closes_root: Path = CLOSES_ROOT, watchlist_path: Path = WATCHLIST_PATH,
          evidence_root: Path | None = None,
          provenance_source: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    """provenance_source computes the provenance again just before an apply-mode write (default git)."""
    paths = {**POLICY_PATHS, **(policy_paths or {})}
    # A fixed clock is passed down only when the caller fixes one (tests); otherwise each step reads the
    # real clock, so a snapshot is never stamped earlier than its own reads.
    fixed_clock = (lambda: now) if now is not None else None
    now = now or datetime.now(timezone.utc)
    day = kst_day(now)
    output_directory = Path(output_root) / day
    config, config_reasons = core.load_config(config_path)
    provenance = provenance if provenance is not None else core.git_provenance()
    mode = config["mode"] if config else "compare"
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION, "run_day_kst": day, "generated_at": now.isoformat(),
        "status": "OK", "reasons": [], "mode": mode, "kill_switch": bool(config and config["kill_switch"]),
        "commit_sha": provenance.get("commit_sha"), "dirty_paths": provenance.get("dirty_paths") or [],
        "guarded_dirty_paths": provenance.get("guarded_dirty_paths") or [],
        "steps": {}, "invariants": None, "would_apply": None, "applied": None, "holdings_change": [],
        "warnings": [], "exposure": None, "compare": {"streak": 0, "last_mismatch": None},
        "next_action_for_user": None,
        "order_authority": False, "quantity_authority": "none", "execution_quantity": None,
        "account_identifier_stored": False,
    }
    previous_result = _previous_result(output_root, day)
    reference = compare_reference(Path(output_root), day)
    stale = False
    try:
        # 1-2 configuration, kill switch, profile alias, account reads and the auto reconciliation.
        profile = None if result["kill_switch"] else kiwoom_profile(paths["readonly"])
        baseline = (reference or {}).get("applied") or (reference or {}).get("would_apply")
        reconcile = reconcile_auto(
            config=config, config_reasons=config_reasons, provenance=provenance, output_directory=output_directory,
            compare_baseline=baseline, readonly_policy_path=paths["readonly"], rate_policy_path=paths["rate"],
            broker_policy_path=paths["broker"], alert_policy_path=paths["alert"], state_path=paths["state"],
            journal_path=paths["journal"], reader=reader, now=fixed_clock, evidence_root=evidence_root,
            previous_run=previous_reconcile(Path(output_root), day), config_path=config_path,
            provenance_source=provenance_source)
        stale = mode == "compare" and core.baseline_stale(reconcile)
        output_directory.mkdir(parents=True, exist_ok=True)
        write_json(output_directory / AUTO_RESULT_FILE, reconcile)
        result["steps"]["reconcile"] = {"status": reconcile["status"], "path": core._repo_relative(
            output_directory / AUTO_RESULT_FILE)}
        result.update(invariants=reconcile.get("invariants"), would_apply=reconcile.get("would_apply"),
                      applied=reconcile.get("applied"), holdings_change=reconcile.get("holdings_change") or [],
                      warnings=list(reconcile.get("warnings") or []))
        result["reasons"] += reconcile["reasons"]
        if reconcile["status"] == "FAIL":
            raise StepFailure("RECONCILE_FAILED")
        if "KILL_SWITCH_ON" in reconcile["reasons"]:
            result["status"] = "HOLD"
            return _finish(result, output_root, output_directory)
        result["compare"] = compare_streak(reconcile=reconcile, previous_reconcile_result=reference,
                                           previous_result=previous_result, state_path=paths["state"])
        # 3 30-minute bars and close histories.
        readonly = load_json(paths["readonly"])
        runtime = Path(str(readonly["official_runtime_path"])).resolve()
        rate_policy = load_json(paths["rate"])
        today = now.astimezone(KST).date()
        histories = []
        for symbol in symbols_for_run(output_directory=output_directory, state_path=paths["state"],
                                      watchlist_path=watchlist_path, extra=list((config or {}).get("symbols_extra") or [])):
            exchange, last_session = known_exchange(symbol, closes_root)
            if exchange is None:
                exchange = resolve_exchange(symbol, runtime=runtime, rate_policy=rate_policy, reader=exchange_reader)
            oldest = date.fromisoformat(last_session) if last_session else FIRST_COLLECTION_DAY
            collector(symbol, exchange, newest=today, oldest=min(oldest, today), profile=profile,
                      pages_root=closes_root / "pages")
            histories.append(history_updater(symbol, exchange, now=now, closes_root=closes_root))
        result["steps"]["bars"] = {"status": "OK", "histories": histories}
        # 4 exposure review (read-only).
        result["exposure"] = exposure_runner()
        result["steps"]["exposure"] = {"status": "OK", "path": result["exposure"]["path"]}
    except StepFailure as exc:
        result["status"] = "FAIL"
        result["reasons"].append(str(exc))
        return _finish(result, output_root, output_directory, stale=stale)
    except Exception as exc:  # noqa: BLE001 - the scheduled run must always leave a FAIL record
        # Any other error is still the first failure: stop, record it, let the next run retry.
        result["status"] = "FAIL"
        result["reasons"].append(f"UNEXPECTED_ERROR:{type(exc).__name__}:{str(exc)[:200]}")
        return _finish(result, output_root, output_directory, stale=stale)
    if result["reasons"]:
        result["status"] = "HOLD"
    required = int((config or {}).get("compare_days_required") or 3)
    if mode == "compare" and result["compare"]["streak"] >= required:
        result["next_action_for_user"] = READY_FOR_RECORDING
    return _finish(result, output_root, output_directory, stale=stale)


def _finish(result: dict[str, Any], output_root: Path, output_directory: Path, *, stale: bool = False
            ) -> dict[str, Any]:
    if stale:
        # T1 r3 C4: compare mode keeps the last record, whose fill window is now past 80% of its limit. The run
        # itself is not failed for it (over the limit the reconciliation still fails and writes nothing).
        result["next_action_for_user"] = RECORDING_NEEDED_BASELINE_OLD
    errors = validate_instance(result, RESULT_SCHEMA)
    if errors:
        result["status"] = "FAIL"
        result["reasons"].append("RESULT_SCHEMA_INVALID:" + ";".join(errors[:3]))
    if result["status"] == "FAIL":
        # T1 r3 C5: a day failed at any step (bars and exposure included) never counts toward the streak.
        result["compare"] = {"streak": 0, "last_mismatch": {"reason": "RUN_FAILED", "codes": result["reasons"][:10]}}
    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(output_directory / RESULT_FILE, result)
    write_json(Path(output_root) / LATEST_FILE, result)
    return result


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Deterministic daily auto-core (read-only broker, no orders)")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("daily", help="collect, reconcile (compare/apply), close histories, exposure")
    run.add_argument("--output-root", type=Path, default=AUTO_OUTPUT_ROOT)
    run.add_argument("--config", type=Path, default=core.CONFIG_PATH)
    # Redesign T2 F8: judgments, requirements and gates, order tickets (stage 1), outcomes, journal, compare.
    decide_parser = commands.add_parser("decide", help="judge, gate and size LOC tickets for the user (no orders)")
    decide_parser.add_argument("--output-root", type=Path, default=AUTO_OUTPUT_ROOT)
    decide_parser.add_argument("--config", type=Path, default=core.CONFIG_PATH)
    args = parser.parse_args(argv)
    if args.command == "decide":
        from auto_core_decide import decide

        decision = decide(output_root=args.output_root, config_path=args.config)
        print(json.dumps({"status": decision["status"], "decision_mode": decision["decision_mode"],
                          "reasons": decision["reasons"][:5], "tickets": len(decision["tickets"]),
                          "no_action": decision["no_action"]["value"],
                          "next_action_for_user": decision["next_action_for_user"]}, ensure_ascii=True))
        return 1 if decision["status"] == "FAIL" else 0
    result = daily(output_root=args.output_root, config_path=args.config)
    print(json.dumps({"status": result["status"], "mode": result["mode"], "reasons": result["reasons"][:5],
                      "streak": result["compare"]["streak"], "next_action_for_user": result["next_action_for_user"]},
                     ensure_ascii=True))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
