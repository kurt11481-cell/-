#!/usr/bin/env python3
"""Read-only portfolio status view (I7).

Reads timestamps and status codes from existing files and writes one summary
JSON plus a one-line Korean summary. It never writes state, policy or ledger
files and never places or infers orders. Missing inputs are reported as
MISSING and never fail the command.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
LOCALE_PATH = SKILL_ROOT / "assets/locales/portfolio-status-ko-KR.json"
KST = timezone(timedelta(hours=9))
SCHEMA_VERSION = "1.0"
DEFAULT_STALE_DAYS = 4.0
SEPARATOR = " " + chr(0xB7) + " "
ANALYSIS_FILE = "manual-portfolio-analysis.json"
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}")

DEFAULT_PATHS = {
    "state": "stock-strategy-system/portfolio_state.json",
    "ledger": "stock-strategy-system/reconciliation_ledger.jsonl",
    "analysis_dir": "workspace/outputs/manual-portfolio-analysis",
    "baseline_index": "workspace/research/holding-baselines/active-index.json",
    "cards_dir": "workspace/outputs/holding-cards",
    "journal": "stock-strategy-system/decision_journal.json",
    "output": "workspace/outputs/status/latest.json",
}


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def age_days(now: datetime, moment: datetime | None) -> float | None:
    if moment is None:
        return None
    return round((now - moment).total_seconds() / 86400, 2)


def kst_date(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(KST).strftime("%Y-%m-%d")


def short_date(value: str | None) -> str:
    if not value:
        return "-"
    return f"{int(value[5:7])}/{int(value[8:10])}"


def read_json(path: Path) -> tuple[Any, str]:
    if not path.is_file():
        return None, "MISSING"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), "OK"
    except (OSError, ValueError):
        return None, "INVALID"


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def timestamp_item(data: dict[str, Any], key: str, now: datetime, stale_days: float,
                   fallback_key: str | None = None) -> dict[str, Any]:
    moment = parse_datetime(data.get(key)) or (parse_datetime(data.get(fallback_key)) if fallback_key else None)
    if moment is None:
        return {"status": "INVALID", "value": None, "date": None, "age_days": None, "stale": None}
    age = age_days(now, moment)
    return {"status": "OK", "value": moment.isoformat(), "date": kst_date(moment),
            "age_days": age, "stale": age > stale_days}


def missing_item(status: str) -> dict[str, Any]:
    return {"status": status}


def state_items(path: Path, now: datetime, stale_days: float) -> tuple[dict[str, Any], dict[str, Any]]:
    data, status = read_json(path)
    if status != "OK" or not isinstance(data, dict):
        return missing_item(status if status != "OK" else "INVALID"), missing_item(status if status != "OK" else "INVALID")
    state_item = timestamp_item(data, "last_updated_at", now, stale_days)
    broker = as_dict(data.get("last_confirmed_broker_snapshot"))
    if not broker:
        return state_item, missing_item("MISSING")
    return state_item, timestamp_item(broker, "as_of_timestamp", now, stale_days, fallback_key="as_of")


def latest_analysis(directory: Path, now: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    if not directory.is_dir():
        return missing_item("MISSING"), missing_item("MISSING")
    runs = sorted((p for p in directory.iterdir() if (p / ANALYSIS_FILE).is_file()), key=lambda p: p.name)
    if not runs:
        return missing_item("MISSING"), missing_item("MISSING")
    data, status = read_json(runs[-1] / ANALYSIS_FILE)
    if status != "OK" or not isinstance(data, dict):
        return {"status": "INVALID", "run_id": runs[-1].name}, missing_item("INVALID")
    moment = parse_datetime(data.get("decision_as_of"))
    observed = as_dict(data.get("broker_observed_state"))
    op_status = as_dict(observed.get("operation_statuses")).get("account_open_items")
    analysis = {
        "status": "OK",
        "run_id": data.get("manual_run_id") or runs[-1].name,
        "decision_as_of": moment.isoformat() if moment else None,
        "date": kst_date(moment),
        "age_days": age_days(now, moment),
        "broker_diff_status": data.get("broker_diff_status"),
        "broker_snapshot_as_of": data.get("broker_snapshot_as_of"),
    }
    if not isinstance(op_status, str):
        return analysis, {"status": "UNKNOWN", "bridge_status": None}
    return analysis, {"status": "PASS" if op_status == "PASS" else "ERROR", "bridge_status": op_status}


def latest_reconciliation(path: Path, now: datetime) -> dict[str, Any]:
    if not path.is_file():
        return missing_item("MISSING")
    last: dict[str, Any] | None = None
    valid = invalid = 0
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return missing_item("INVALID")
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            invalid += 1
            continue
        if isinstance(entry, dict):
            valid += 1
            last = entry
        else:
            invalid += 1
    if last is None:
        return {"status": "MISSING" if not invalid else "INVALID", "entry_count": 0, "invalid_lines": invalid}
    moment = parse_datetime(last.get("confirmed_at"))
    return {
        "status": "OK", "entry_count": valid, "invalid_lines": invalid,
        "confirmed_at": moment.isoformat() if moment else None, "date": kst_date(moment),
        "age_days": age_days(now, moment), "event": last.get("event"),
        "state_revision_after": last.get("state_revision_after"),
    }


def baseline_items(path: Path, now: datetime) -> dict[str, Any]:
    data, status = read_json(path)
    if status != "OK" or not isinstance(data, dict):
        return missing_item(status if status != "OK" else "INVALID")
    tickers: dict[str, Any] = {}
    for ticker, record in sorted(as_dict(data.get("active")).items()):
        record = as_dict(record)
        moment = parse_datetime(record.get("activated_at"))
        tickers[ticker] = {
            "baseline_id": record.get("baseline_id"),
            "activated_at": moment.isoformat() if moment else None,
            "date": kst_date(moment), "age_days": age_days(now, moment),
        }
    return {"status": "OK", "tickers": tickers}


def latest_card(directory: Path, now: datetime) -> dict[str, Any]:
    if not directory.is_dir():
        return missing_item("MISSING")
    dates = []
    for path in directory.iterdir():
        if path.is_dir() and DATE_DIR.match(path.name):
            try:
                dates.append(datetime.strptime(path.name[:10], "%Y-%m-%d").date())
            except ValueError:
                continue
    if not dates:
        return missing_item("MISSING")
    card_date = max(dates)
    names = [card_date.isoformat()]
    return {"status": "OK", "date": names[-1], "age_days": float((now.astimezone(KST).date() - card_date).days)}


def journal_pending(path: Path) -> dict[str, Any]:
    # Assumed schema (decision ledger is not built yet): a list of entries, or
    # {"entries": [...]}. An entry without a truthy "outcome" is pending scoring.
    data, status = read_json(path)
    if status != "OK":
        return {**missing_item(status), "assumed_schema": True}
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return {**missing_item("INVALID"), "assumed_schema": True}
    pending = sum(1 for entry in entries if isinstance(entry, dict) and not entry.get("outcome"))
    return {"status": "OK", "entry_count": len(entries), "pending_count": pending, "assumed_schema": True}


def collect_warnings(report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    state, broker = report["state"], report["broker_snapshot"]
    if state["status"] == "MISSING":
        warnings.append("STATE_MISSING")
    elif state.get("stale"):
        warnings.append("STATE_STALE")
    if broker["status"] == "MISSING":
        warnings.append("BROKER_SNAPSHOT_MISSING")
    elif broker.get("stale"):
        warnings.append("BROKER_SNAPSHOT_STALE")
    analysis = report["latest_analysis"]
    if analysis["status"] == "OK" and analysis.get("broker_diff_status") != "MATCH":
        warnings.append("BROKER_DIFF_NOT_MATCH")
    if report["latest_analysis"]["status"] == "OK" and report["open_orders"]["status"] != "PASS":
        warnings.append("OPEN_ORDERS_NOT_PASS")
    return warnings


def load_messages() -> dict[str, Any]:
    return json.loads(LOCALE_PATH.read_text(encoding="utf-8"))["messages"]


def days_text(value: float | None) -> int:
    return 0 if value is None else max(int(value), 0)


def build_summary(report: dict[str, Any], messages: dict[str, Any]) -> str:
    parts: list[str] = []
    state, broker = report["state"], report["broker_snapshot"]
    if state["status"] == "OK":
        parts.append(messages["state_ok"].format(date=short_date(state["date"]), days=days_text(state["age_days"])))
    else:
        parts.append(messages["state_missing" if state["status"] == "MISSING" else "state_invalid"])
    if broker["status"] == "OK":
        parts.append(messages["broker_snapshot_ok"].format(date=short_date(broker["date"]), days=days_text(broker["age_days"])))
    else:
        parts.append(messages["broker_snapshot_missing"])
    analysis = report["latest_analysis"]
    diff = analysis.get("broker_diff_status") if analysis["status"] == "OK" else None
    if analysis["status"] != "OK":
        parts.append(messages["diff_missing"])
    else:
        parts.append(messages[{"MATCH": "diff_match", "DIFFERENT": "diff_different"}.get(diff, "diff_unknown")])
    orders = report["open_orders"]
    if orders["status"] == "PASS":
        parts.append(messages["open_orders_pass"])
    elif orders["status"] == "ERROR":
        parts.append(messages["open_orders_error"].format(code=orders["bridge_status"]))
    else:
        parts.append(messages["open_orders_missing"])
    recon = report["latest_reconciliation"]
    if recon["status"] == "OK":
        parts.append(messages["reconciliation_ok"].format(date=short_date(recon["date"]), count=recon["entry_count"]))
    else:
        parts.append(messages["reconciliation_missing"])
    card = report["latest_card"]
    parts.append(messages["card_ok"].format(date=short_date(card["date"])) if card["status"] == "OK"
                 else messages["card_missing"])
    journal = report["scoring_pending"]
    parts.append(messages["journal_ok"].format(count=journal["pending_count"]) if journal["status"] == "OK"
                 else messages["journal_missing"])
    line = SEPARATOR.join(parts)
    if report["warnings"]:
        labels = ", ".join(messages["warnings"][code] for code in report["warnings"])
        line = f"{messages['warning_prefix']}: {labels} | {line}"
    return line


def build_report(paths: dict[str, Path], now: datetime, stale_days: float) -> dict[str, Any]:
    state, broker = state_items(paths["state"], now, stale_days)
    analysis, open_orders = latest_analysis(paths["analysis_dir"], now)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "portfolio_status",
        "generated_at": now.isoformat(),
        "stale_days_threshold": stale_days,
        "read_only": True,
        "order_authority": False,
        "state": state,
        "broker_snapshot": broker,
        "latest_analysis": analysis,
        "open_orders": open_orders,
        "latest_reconciliation": latest_reconciliation(paths["ledger"], now),
        "baselines": baseline_items(paths["baseline_index"], now),
        "latest_card": latest_card(paths["cards_dir"], now),
        "scoring_pending": journal_pending(paths["journal"]),
    }
    report["warnings"] = collect_warnings(report)
    return report


def resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    root = Path(args.root)
    return {key: Path(getattr(args, key)) if getattr(args, key) else root / rel
            for key, rel in DEFAULT_PATHS.items()}


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only portfolio status view")
    parser.add_argument("--root", default=str(REPO_ROOT), help="base folder for the default input paths")
    for key in DEFAULT_PATHS:
        parser.add_argument(f"--{key.replace('_', '-')}", dest=key, default=None,
                            help=f"override (default: <root>/{DEFAULT_PATHS[key]})")
    parser.add_argument("--now", default=None, help="ISO timestamp used as now (tests)")
    parser.add_argument("--stale-days", type=float, default=DEFAULT_STALE_DAYS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    now = parse_datetime(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print("invalid --now", file=sys.stderr)
        return 2
    paths = resolve_paths(args)
    report = build_report(paths, now, args.stale_days)
    report["summary_ko"] = build_summary(report, load_messages())
    output = paths["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(report["summary_ko"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
