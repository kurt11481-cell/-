#!/usr/bin/env python3
"""I0 broker reconciliation: propose (read-only), show, and user-confirmed apply.

propose  Read the Kiwoom account (read-only), build one proposal, never write state.
show     Render the proposal difference table for the user (deterministic).
apply    Write the proposal to portfolio state only with the user's confirmation code.
         Run apply only in Cowork after the user typed "confirm <code>" in that conversation,
         or from the user's own terminal (--confirmed-via USER_TERMINAL). Agents, scheduled
         tasks, Claude Code, Codex and Judge sessions never run it.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from apply_user_confirmed_broker_snapshot import (
    CONFIRMATION_METHODS, apply_confirmed, default_ledger_path, ledger_status, preview_updated_state,
)
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
        for warning in proposal.get("warnings") or []:
            key = f"warning_{warning}"
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
    extra = {"reader": reader} if reader is not None else {}
    results, snapshot, before = collect_broker_snapshot(
        runtime=runtime, rate_policy=load_json(args.rate_policy), broker_policy=broker_policy,
        snapshot_role=args.snapshot_role, portfolio_state=state_path, **extra,
    )
    ledger = ledger_status(args.ledger or default_ledger_path(state_path))
    output_directory = _unique_directory(
        Path(args.output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    proposal = reconciliation_proposal(
        snapshot, load_json(state_path), results=results,
        maximum_age_seconds=int(broker_policy["maximum_age_seconds"]),
        portfolio_state_path=repo_relative(state_path),
        snapshot_path=repo_relative(output_directory / SNAPSHOT_FILE),
        ledger_last_hash_after=ledger["last_portfolio_hash_after"], ledger_integrity_ok=ledger["chain_ok"],
        post_apply_check=alert_engine_check(load_json(args.alert_policy)),
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
            backup_directory=args.backup_directory, ledger_path=args.ledger,
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(messages["apply_rejected"].format(reason=str(exc) or type(exc).__name__))
        return 2
    backup_root = Path(args.backup_directory) if args.backup_directory else state_path.parent / "backups"
    print(messages["apply_success"].format(before=audit["state_revision_before"], after=audit["state_revision_after"],
                                           backup=repo_relative(backup_root / audit["backup_file"])))
    return 0


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
    propose.add_argument("--ledger", type=Path)
    propose.add_argument("--snapshot-role", default="POST_CLOSE_BROKER_SNAPSHOT",
                         choices=("PRE_OPEN_BROKER_SNAPSHOT", "POST_CLOSE_BROKER_SNAPSHOT"))
    propose.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
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
    apply.add_argument("--ledger", type=Path)
    apply.add_argument("--backup-directory", type=Path)
    return parser


def main(argv: list[str] | None = None, *, reader: Callable[..., list[dict[str, Any]]] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    if args.command == "propose":
        return cmd_propose(args, reader)
    if args.command == "show":
        return cmd_show(args)
    return cmd_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
