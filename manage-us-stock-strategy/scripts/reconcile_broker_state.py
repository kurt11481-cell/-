#!/usr/bin/env python3
"""I0 broker reconciliation: propose (read-only), show, user-confirmed apply, and the auto-core path.

propose  Read the Kiwoom account (read-only), build one proposal, never write state.
show     Render the proposal difference table for the user (deterministic).
apply    Write the proposal to portfolio state only with the user's confirmation code.
         Run apply only in Cowork after the user typed "confirm <code>" in that conversation,
         or from the user's own terminal (--confirmed-via USER_TERMINAL: an interactive console
         only, the code typed once more). Agents, scheduled tasks, Claude Code, Codex and Judge
         sessions never run it.
auto     Redesign T1 F4 (run by the auto-core Windows task): the same read plus transaction history,
         daily fills and day trades, judged by invariants I1-I5 (auto_core_reconcile.py). In mode
         "compare" (workspace/policies/auto_core.json) it never writes and records would_apply; in mode
         "apply" it writes only when I1-I5 pass and the kill switch is off. No human code is involved.
         Result: workspace/outputs/auto-core/<YYYY-MM-DD>/reconcile.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import auto_core_reconcile as auto_core_reconcile
from apply_user_confirmed_broker_snapshot import (
    CONFIRMATION_METHODS, apply_confirmed, default_backup_directory, default_ledger_path, ledger_status,
    preview_updated_state,
)
from cash_flow_evidence import CashFlowError, build_declaration, read_ledger_blocks
from kiwoom_broker_shadow import DEFAULT_PORTFOLIO_STATE_PATH, PROPOSAL_SCHEMA_VERSION, reconciliation_proposal
from run_kiwoom_broker_shadow import collect_broker_snapshot, repo_relative
from validation_common import file_hash, load_json, validate_instance, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_SCHEMA = SKILL_ROOT / "schemas/kiwoom-reconciliation-proposal.schema.json"
LOCALE_PATH = SKILL_ROOT / "assets/locales/reconcile-broker-state-ko-KR.json"
PROPOSAL_FILE = "reconciliation_proposal.json"
SNAPSHOT_FILE = "kiwoom_broker_snapshot.shadow.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/reconciliation"
AUTO_OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/auto-core"
AUTO_RESULT_FILE = "reconcile.json"
DAY_FOLDER = re.compile(r"\d{4}-\d{2}-\d{2}")
LEVERAGED_SCOPE = "leveraged_holding_risk_and_watchlist"
ALERT_CHECK_NAME = "evaluate_alerts.leveraged_state_integrity_errors"
KST = timezone(timedelta(hours=9))


def _messages() -> dict[str, str]:
    return load_json(LOCALE_PATH)["messages"]


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _kst(value: Any, pattern: str = "%Y-%m-%d %H:%M:%S") -> str:
    parsed = _parse(value)
    return parsed.astimezone(KST).strftime(pattern) if parsed else "?"


def alert_engine_check(alert_policy: dict[str, Any]) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    """Run the alert engine's leveraged state-integrity validation on a patched copy of the state."""
    def check(portfolio: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        from evaluate_alerts import leveraged_state_integrity_errors

        preview = preview_updated_state(portfolio, proposal)
        session_date = proposal["confirmed_snapshot_record"]["as_of"]
        rules = alert_policy.get("holding_risk_rules") or {}
        positions = set(rules.get("positions") or {})
        de_minimis = set(rules.get("de_minimis_manual_exit_positions") or {})
        positive = {ticker for ticker, quantity in (preview.get("holdings") or {}).items()
                    if isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0}
        mismatch = bool(positive - positions - de_minimis) or bool(positions - positive)
        if alert_policy.get("daily_engine_scope") != LEVERAGED_SCOPE:
            return {"check": ALERT_CHECK_NAME, "session_date": session_date, "status": "NOT_APPLICABLE",
                    "errors": [], "policy_positions_mismatch": mismatch}
        errors = leveraged_state_integrity_errors(preview, alert_policy, session_date)
        return {"check": ALERT_CHECK_NAME, "session_date": session_date, "status": "FAIL" if errors else "PASS",
                "errors": list(errors), "policy_positions_mismatch": mismatch}
    return check


def _unique_directory(base: Path) -> Path:
    candidate, index = base, 1
    while candidate.exists():
        candidate = base.with_name(f"{base.name}-{index}")
        index += 1
    return candidate


def resolve_proposal_path(value: str | None, output_root: Path) -> Path:
    if value and value != "latest":
        path = Path(value)
        return path / PROPOSAL_FILE if path.is_dir() else path
    candidates = sorted(path for path in Path(output_root).glob(f"*/{PROPOSAL_FILE}") if path.is_file())
    if not candidates:
        raise ValueError("NO_PROPOSAL_FOUND")
    return candidates[-1]


def _format(value: Any, messages: dict[str, str]) -> str:
    if value is None:
        return messages["missing_value"]
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        text = f"{value:,.4f}".rstrip("0").rstrip(".")
        return text or "0"
    return str(value)


def _cash_flow_lines(block: Any, messages: dict[str, str]) -> list[str]:
    """S5 R6 declaration shown inside the same table the user confirms (nothing when there is no block)."""
    if not isinstance(block, dict):
        return []
    evidence = block.get("evidence") or {}
    excluded = block.get("excluded_from_cash_flow") or {}
    values = {
        "period_from": evidence.get("period_from"), "period_to": evidence.get("period_to"),
        "net": block.get("new_external_net_usd"), "declared": block.get("declared_cash_flow_usd"),
        "remainder": block.get("undeclared_remainder_usd"), "dividend": excluded.get("dividend_settlement_usd"),
        "fees": excluded.get("fees_usd"), "taxes": excluded.get("taxes_usd"),
        "codes": ", ".join(evidence.get("unresolved") or []),
    }
    key = {"NO_EXTERNAL_FLOW": "show_cash_flow_none", "DECLARED_IN_FULL": "show_cash_flow_declared",
           "PARTIALLY_DECLARED": "show_cash_flow_partial", "UNDECLARED": "show_cash_flow_undeclared",
           }.get(block.get("declaration_status"), "show_cash_flow_unresolved")
    return [messages[key].format(**values), messages["show_cash_flow_excluded"].format(**values)]


def render_proposal(proposal: dict[str, Any], *, now: datetime | None = None) -> list[str]:
    """Deterministic Korean difference table (P3 4-1) shown to the user before any confirmation."""
    messages = _messages()
    now = now or datetime.now(timezone.utc)
    source = proposal.get("source") or {}
    minutes = int(proposal.get("maximum_age_seconds") or 0) // 60
    lines = [messages["show_header"].format(
        retrieved_kst=_kst(source.get("earliest_required_retrieved_at")), minutes=minutes,
        expires_hm=_kst(proposal.get("expires_at"), "%H:%M"))]
    updated = _parse(proposal.get("state_last_updated_at"))
    generated = _parse(proposal.get("generated_at"))
    age = (messages["show_age_days"].format(days=(generated.date() - updated.astimezone(timezone.utc).date()).days)
           if updated and generated else messages["show_age_unknown"])
    lines.append(messages["show_state"].format(
        revision=proposal.get("expected_state_revision"),
        updated=_kst(proposal.get("state_last_updated_at"), "%Y-%m-%d"), age=age))
    status = proposal.get("status")
    if status == "NO_CHANGE_REQUIRED":
        lines.append(messages["show_no_change"])
        return lines
    if status != "USER_CONFIRMATION_REQUIRED":
        blocking = set(proposal.get("unresolved_fields") or [])
        for warning in proposal.get("warnings") or []:
            # A ledger code that blocks this proposal has its own stop message.
            key = (f"blocked_{warning}" if warning in blocking and f"blocked_{warning}" in messages
                   else f"warning_{warning}")
            if key in messages and warning in {"STATE_CHANGED_OUTSIDE_LEDGER", "LEDGER_INTEGRITY_FAILED"}:
                lines.append(messages[key])
        lines.append(messages["show_blocked"].format(codes=", ".join(proposal.get("unresolved_fields") or [])))
        return lines
    if proposal.get("change_kind") == "METADATA_ONLY":
        lines.append(messages["show_metadata_only"])
    lines += ["", messages["show_table_header"], messages["show_table_rule"]]
    for change in proposal.get("changes") or []:
        field, key = change.get("field"), change.get("key")
        derived = field in {"position_cost_basis_usd", "aggregate_cost_basis_usd"}
        if field == "last_confirmed_broker_snapshot":
            label = messages["row_record"].format(key=key)
        else:
            label = messages[f"row_{field}"].format(ticker=key)
        broker = messages["derived_marker"] if derived else _format(change.get("new_value"), messages)
        lines.append(f"| {label} | {_format(change.get('old_value'), messages)} | {broker} | "
                     f"{_format(change.get('new_value'), messages)} |")
    lines.append("")
    check = proposal.get("post_apply_checks") or {}
    if check.get("status") == "PASS":
        lines.append(messages["show_check_pass"])
    elif check.get("status") == "FAIL":
        lines.append(messages["show_check_fail"].format(errors="; ".join(check.get("errors") or [])))
    else:
        lines.append(messages["show_check_other"].format(status=check.get("status")))
    lines.append(messages["show_unchanged"])
    for warning in proposal.get("warnings") or []:
        if f"warning_{warning}" in messages:
            lines.append(messages[f"warning_{warning}"])
    differs = [item["ticker"] for item in proposal.get("cost_basis_crosscheck") or [] if item.get("status") == "DIFFERS"]
    if differs:
        lines.append(messages["show_crosscheck_differs"].format(tickers=", ".join(differs)))
    fills = proposal.get("recent_fills") or []
    lines.append(messages["show_fills_none"] if not fills else messages["show_fills_some"].format(
        items=", ".join(f"{item.get('ticker')} {item.get('time')}" for item in fills)))
    lines += _cash_flow_lines(proposal.get("cash_flow_declaration"), messages)
    expires = _parse(proposal.get("expires_at"))
    if expires is None or now > expires:
        lines.append(messages["show_expired"].format(expires_hm=_kst(proposal.get("expires_at"), "%H:%M")))
    else:
        lines.append(messages["show_confirm"].format(code=proposal.get("confirm_code")))
    return lines


def cmd_propose(args: argparse.Namespace, reader: Callable[..., list[dict[str, Any]]] | None) -> int:
    messages = _messages()
    readonly_policy = load_json(args.readonly_policy)
    official_runtime = Path(str(readonly_policy["official_runtime_path"])).resolve()
    runtime = (args.runtime or official_runtime).resolve()
    if runtime != official_runtime:
        raise SystemExit("KIWOOM_RUNTIME_PATH_MISMATCH")
    broker_policy = load_json(args.broker_policy)
    state_path = Path(args.portfolio_state)
    # S5 R6: the declaration is validated before any broker read. Evidence is a saved, sanitized
    # transaction-history file; this command reads no extra broker API for it.
    declaration = None
    try:
        if args.cash_flow_evidence is not None:
            declaration = build_declaration(
                load_json(args.cash_flow_evidence), declared_usd=args.declare_cash_flow_usd,
                prior_blocks=read_ledger_blocks(default_ledger_path(state_path)))
        elif args.declare_cash_flow_usd is not None:
            raise CashFlowError("CASH_FLOW_EVIDENCE_REQUIRED")
    except (CashFlowError, OSError, ValueError) as exc:
        print(messages["propose_cash_flow_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    extra = {"reader": reader} if reader is not None else {}
    results, snapshot, before = collect_broker_snapshot(
        runtime=runtime, rate_policy=load_json(args.rate_policy), broker_policy=broker_policy,
        snapshot_role=args.snapshot_role, portfolio_state=state_path, **extra,
    )
    ledger = ledger_status(default_ledger_path(state_path))
    output_directory = _unique_directory(
        Path(args.output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    proposal = reconciliation_proposal(
        snapshot, load_json(state_path), results=results,
        maximum_age_seconds=int(broker_policy["maximum_age_seconds"]),
        portfolio_state_path=repo_relative(state_path),
        snapshot_path=repo_relative(output_directory / SNAPSHOT_FILE),
        ledger_last_hash_after=ledger["last_portfolio_hash_after"],
        ledger_last_hash_before=ledger["last_portfolio_hash_before"], ledger_integrity_ok=ledger["chain_ok"],
        post_apply_check=alert_engine_check(load_json(args.alert_policy)),
        cash_flow_declaration=declaration,
    )
    if file_hash(state_path) != before:
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    errors = validate_instance(proposal, PROPOSAL_SCHEMA)
    if errors:
        raise SystemExit("RECONCILIATION_PROPOSAL_SCHEMA_FAILED:" + ";".join(errors))
    output_directory.mkdir(parents=True)
    write_json(output_directory / SNAPSHOT_FILE, snapshot)
    write_json(output_directory / PROPOSAL_FILE, proposal)
    if file_hash(state_path) != before:
        raise SystemExit("PORTFOLIO_STATE_MUTATION_DETECTED")
    status = proposal["status"]
    if status == "NO_CHANGE_REQUIRED":
        print(messages["propose_no_change"])
    elif status == "USER_CONFIRMATION_REQUIRED":
        key = "propose_metadata_only" if proposal["change_kind"] == "METADATA_ONLY" else "propose_values"
        print(messages[key].format(expires_kst=_kst(proposal["expires_at"], "%H:%M")))
    else:
        print(messages["propose_blocked"].format(codes=", ".join(proposal["unresolved_fields"])))
    print(messages["propose_path"].format(path=repo_relative(output_directory / PROPOSAL_FILE)))
    return 2 if status == "BLOCKED" else 0


def cmd_show(args: argparse.Namespace) -> int:
    proposal = load_json(resolve_proposal_path(args.proposal, args.output_root))
    print("\n".join(render_proposal(proposal)))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    messages = _messages()
    try:
        if args.confirmed_via == "USER_TERMINAL":
            from portfolio_review_journal import TERMINAL_NOT_INTERACTIVE, user_terminal_rejection

            rejection = user_terminal_rejection(args.confirm, messages["apply_terminal_retype"])
            if rejection == TERMINAL_NOT_INTERACTIVE:
                print(messages["apply_terminal_not_interactive"])
                return 2
            if rejection is not None:
                raise ValueError(rejection)
        proposal_path = resolve_proposal_path(args.proposal, args.output_root)
        proposal = load_json(proposal_path)
        if not isinstance(proposal, dict) or proposal.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
            raise ValueError("PROPOSAL_TYPE_NOT_KIWOOM")
        if args.confirmed_via == "COWORK_CHAT_USER_MESSAGE" and not (args.user_message or "").strip():
            print(messages["apply_user_message_required"])
            return 2
        if args.portfolio_state is not None:
            state_path = Path(args.portfolio_state)
        elif proposal.get("portfolio_state_path") == DEFAULT_PORTFOLIO_STATE_PATH:
            state_path = REPO_ROOT / DEFAULT_PORTFOLIO_STATE_PATH
        else:
            raise ValueError("PROPOSAL_STATE_PATH_NOT_DEFAULT")
        code = args.confirm.strip().upper()
        confirmation = {
            "confirmed": True, "proposal_id": proposal.get("proposal_id"), "bundle_id": proposal.get("bundle_id"),
            "confirm_code": code, "confirmation_method": args.confirmed_via,
            "user_message": args.user_message if args.user_message else code,
        }
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        audit = apply_confirmed(
            state_path=state_path, proposal=proposal, confirmation=confirmation,
            audit_path=proposal_path.parent / f"apply_audit.{stamp}.json",
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(messages["apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    print(messages["apply_success"].format(
        before=audit["state_revision_before"], after=audit["state_revision_after"],
        backup=repo_relative(default_backup_directory(state_path) / audit["backup_file"])))
    return 0


def kst_day(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(KST).date().isoformat()


def previous_reconcile(output_root: Path, day: str) -> dict[str, Any] | None:
    """The latest reconcile.json of an earlier day folder (a rerun on the same day never sees itself)."""
    folders = sorted(path for path in Path(output_root).glob(f"*/{AUTO_RESULT_FILE}")
                     if DAY_FOLDER.fullmatch(path.parent.name) and path.parent.name < day)
    if not folders:
        return None
    try:
        value = load_json(folders[-1])
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def compare_reference(output_root: Path, day: str) -> dict[str, Any] | None:
    """The earlier run whose would_apply (or applied) block the compare check starts from.

    It is the latest earlier run, looking back past runs that held only because a settlement due on their own
    day was not shown yet (T1 r3 C4 b): those keep the streak, so the next day continues from the run before.
    """
    folders = sorted((path for path in Path(output_root).glob(f"*/{AUTO_RESULT_FILE}")
                      if DAY_FOLDER.fullmatch(path.parent.name) and path.parent.name < day), reverse=True)
    for path in folders:
        try:
            value = load_json(path)
        except (OSError, ValueError):
            return None
        if not isinstance(value, dict):
            return None
        if value.get("applied") or value.get("would_apply") or not (
                value.get("status") == "HOLD" and auto_core_reconcile.d0_only(value.get("reasons"))):
            return value
    return None


def _auto_stop(mode: str, status: str, reasons: list[str], provenance: dict[str, Any] | None) -> dict[str, Any]:
    return {"schema_version": auto_core_reconcile.RESULT_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(), "mode": mode, "status": status,
            "reasons": reasons, "kill_switch": "KILL_SWITCH_ON" in reasons, "warnings": [], "invariants": None,
            "cash_flow_evidence": None, "proposal": None, "would_apply": None, "applied": None,
            "holdings_change": [], "fills": [], "compare_check": None, "state_revision": None,
            "provenance": provenance, "account_identifier_stored": False, "inferred_fills": False,
            "order_authority": False, "quantity_authority": "none", "execution_quantity": None}


def reconcile_auto(*, config: dict[str, Any] | None, config_reasons: list[str], provenance: dict[str, Any],
                   output_directory: Path, compare_baseline: dict[str, Any] | None,
                   readonly_policy_path: Path, rate_policy_path: Path, broker_policy_path: Path,
                   alert_policy_path: Path, state_path: Path, journal_path: Path, runtime: Path | None = None,
                   reader: Callable[..., list[dict[str, Any]]] | None = None,
                   now: Callable[[], datetime] | None = None, evidence_root: Path | None = None,
                   previous_run: dict[str, Any] | None = None, config_path: Path | None = None,
                   provenance_source: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    """F4 entry used by `auto` and by auto_core.py daily. Never raises; failures become FAIL results.

    previous_run: the latest earlier reconcile.json (today's settlement read while pending, T1 r3 C4 a).
    config_path, provenance_source: read again by apply_auto_core just before a write (T1 r3 C1).
    """
    if config is None and any(reason != "AUTO_CORE_CONFIG_MISSING" for reason in config_reasons):
        return _auto_stop("compare", "FAIL", list(config_reasons), provenance)
    # Without the approved configuration the run compares only (it never writes) and says why.
    mode = config["mode"] if config else "compare"
    if config and config["kill_switch"] is True:
        return _auto_stop(mode, "HOLD", ["KILL_SWITCH_ON"], provenance)
    guard = auto_core_reconcile.apply_guard_reasons(mode, provenance)
    if guard:
        return _auto_stop(mode, "FAIL", guard, provenance)
    try:
        readonly_policy = load_json(readonly_policy_path)
        official_runtime = Path(str(readonly_policy["official_runtime_path"])).resolve()
        if (runtime or official_runtime).resolve() != official_runtime:
            raise auto_core_reconcile.AutoReconcileError("KIWOOM_RUNTIME_PATH_MISMATCH")
        from portfolio_exposure import journal_view
        from portfolio_review_journal import load_journal

        activation = journal_view(load_journal(journal_path)).get("activation") or {}
        extra: dict[str, Any] = {"evidence_root": evidence_root, "previous_run": previous_run,
                                 "config_path": config_path, "provenance_source": provenance_source}
        if reader is not None:
            extra["reader"] = reader
        if now is not None:
            extra["now"] = now
        result = auto_core_reconcile.run_auto(
            mode=mode, kill_switch=False, state_path=state_path,
            journal_activation_date=activation.get("activation_date"), runtime=official_runtime,
            rate_policy=load_json(rate_policy_path), broker_policy=load_json(broker_policy_path),
            post_apply_check=alert_engine_check(load_json(alert_policy_path)),
            output_directory=output_directory, provenance=provenance, compare_baseline=compare_baseline, **extra)
    except (auto_core_reconcile.AutoReconcileError, CashFlowError, OSError, ValueError, KeyError, TypeError,
            RuntimeError) as exc:
        # RuntimeError covers a sanitized BridgeError (its message is only a status code).
        return _auto_stop(mode, "FAIL", [str(exc) or type(exc).__name__], provenance)
    result["provenance"] = provenance
    if config_reasons:
        result["reasons"] = list(config_reasons) + result["reasons"]
        result["status"] = "HOLD" if result["status"] == "OK" else result["status"]
    return result


def cmd_auto(args: argparse.Namespace, reader: Callable[..., list[dict[str, Any]]] | None) -> int:
    day = args.date or kst_day()
    output_directory = Path(args.output_root) / day
    config, config_reasons = auto_core_reconcile.load_config(args.config)
    provenance = auto_core_reconcile.git_provenance()
    reference = compare_reference(Path(args.output_root), day)
    baseline = (reference or {}).get("applied") or (reference or {}).get("would_apply")
    result = reconcile_auto(
        config=config, config_reasons=config_reasons, provenance=provenance, output_directory=output_directory,
        compare_baseline=baseline, readonly_policy_path=args.readonly_policy, rate_policy_path=args.rate_policy,
        broker_policy_path=args.broker_policy, alert_policy_path=args.alert_policy,
        state_path=Path(args.portfolio_state), journal_path=args.journal, runtime=args.runtime, reader=reader,
        previous_run=previous_reconcile(Path(args.output_root), day), config_path=args.config)
    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(output_directory / AUTO_RESULT_FILE, result)
    print(json.dumps({"status": result["status"], "mode": result["mode"], "reasons": result["reasons"][:5],
                      "path": repo_relative(output_directory / AUTO_RESULT_FILE)}, ensure_ascii=True))
    return 1 if result["status"] == "FAIL" else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="I0 broker reconciliation (read-only propose, confirmed apply)")
    commands = parser.add_subparsers(dest="command", required=True)
    propose = commands.add_parser("propose", help="read-only Kiwoom read and proposal; never writes state")
    propose.add_argument("--runtime", type=Path)
    propose.add_argument("--readonly-policy", type=Path, default=REPO_ROOT / "workspace/policies/kiwoom-readonly-policy.json")
    propose.add_argument("--rate-policy", type=Path, default=REPO_ROOT / "workspace/policies/kiwoom-rate-limit-policy.json")
    propose.add_argument("--broker-policy", type=Path,
                         default=REPO_ROOT / "workspace/policies/kiwoom-broker-readonly-policy.json")
    propose.add_argument("--alert-policy", type=Path, default=REPO_ROOT / "stock-strategy-system/alert_policy.json")
    propose.add_argument("--portfolio-state", type=Path, default=REPO_ROOT / DEFAULT_PORTFOLIO_STATE_PATH)
    propose.add_argument("--snapshot-role", default="POST_CLOSE_BROKER_SNAPSHOT",
                         choices=("PRE_OPEN_BROKER_SNAPSHOT", "POST_CLOSE_BROKER_SNAPSHOT"))
    propose.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    propose.add_argument("--cash-flow-evidence", type=Path,
                         help="S5 R6: sanitized transaction-history evidence from cash_flow_evidence.py normalize")
    propose.add_argument("--declare-cash-flow-usd",
                         help="S5 R6: user-declared net deposit (+) or withdrawal (-) in USD, e.g. 500.00")
    show = commands.add_parser("show", help="render the proposal difference table")
    show.add_argument("--proposal", default="latest")
    show.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    apply = commands.add_parser("apply", help="apply one proposal after the user's explicit confirmation code")
    apply.add_argument("--confirm", required=True, help="confirmation code the user typed for this proposal")
    apply.add_argument("--confirmed-via", required=True, choices=CONFIRMATION_METHODS)
    apply.add_argument("--user-message", help="the user's confirmation message, verbatim (required for Cowork)")
    apply.add_argument("--proposal", default="latest")
    apply.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    apply.add_argument("--portfolio-state", type=Path)
    auto = commands.add_parser("auto", help="auto-core reconciliation under invariants I1-I5 (compare or apply)")
    auto.add_argument("--config", type=Path, default=auto_core_reconcile.CONFIG_PATH)
    auto.add_argument("--date", help="result folder date YYYY-MM-DD (default: today in Korea)")
    auto.add_argument("--runtime", type=Path)
    auto.add_argument("--readonly-policy", type=Path, default=REPO_ROOT / "workspace/policies/kiwoom-readonly-policy.json")
    auto.add_argument("--rate-policy", type=Path, default=REPO_ROOT / "workspace/policies/kiwoom-rate-limit-policy.json")
    auto.add_argument("--broker-policy", type=Path,
                      default=REPO_ROOT / "workspace/policies/kiwoom-broker-readonly-policy.json")
    auto.add_argument("--alert-policy", type=Path, default=REPO_ROOT / "stock-strategy-system/alert_policy.json")
    auto.add_argument("--portfolio-state", type=Path, default=REPO_ROOT / DEFAULT_PORTFOLIO_STATE_PATH)
    auto.add_argument("--journal", type=Path, default=REPO_ROOT / "stock-strategy-system/decision_journal.json")
    auto.add_argument("--output-root", type=Path, default=AUTO_OUTPUT_ROOT)
    return parser


def main(argv: list[str] | None = None, *, reader: Callable[..., list[dict[str, Any]]] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    if args.command == "propose":
        return cmd_propose(args, reader)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "auto":
        return cmd_auto(args, reader)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
