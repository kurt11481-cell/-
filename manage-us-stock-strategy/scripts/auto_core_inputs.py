#!/usr/bin/env python3
"""Redesign T2 F2/F3: the two contracts through which judgment reaches the auto-core.

F2 card registry (docs/claude/card-evidence-registry.json): the machine-readable fields of accepted cards.
   A symbol is ticket-eligible (buy or sell) only when its entry exists, its acceptance is valid, the card
   section hash still matches and the registry file is committed in git. Otherwise judgments and alerts go on
   but no ticket is made for it.
F3 research record (workspace/outputs/research-records/<KST date>/research-record.json): what the LLM research
   task found (earnings dates in the p-earn shape, official company facts, the integrated-check run copy).
   Every item is checked deterministically; an item that fails is dropped with its reason, and a file that
   fails its schema counts as "no research record" (buys are then blocked, official evidence is 0).
Read only: nothing here writes a file or calls a broker.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from validation_common import load_json, validate_instance


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
REGISTRY_PATH = REPO_ROOT / "docs/claude/card-evidence-registry.json"
REGISTRY_RELATIVE = "docs/claude/card-evidence-registry.json"
REGISTRY_SCHEMA = SKILL_ROOT / "schemas/auto-core-card-registry.schema.json"
RESEARCH_SCHEMA = SKILL_ROOT / "schemas/auto-core-research-record.schema.json"
RESEARCH_ROOT = REPO_ROOT / "workspace/outputs/research-records"
RESEARCH_FILE = "research-record.json"
WATCHLIST_PATH = REPO_ROOT / "docs/claude/watchlist-registry.json"
M6_PREFIX = "m6-relative-comparison-7stock"
ET = ZoneInfo("America/New_York")
ACCEPTED_PREFIX = "\uc218\ub77d"  # "\uc218\ub77d"
QUOTE_MAX = 160
SUMMARY_MAX = 200
SOURCE_KINDS = ("SEC_FILING", "COMPANY_PRESS_RELEASE", "COMPANY_IR")
FACT_CHECK_NOT_BEFORE = time(16, 0)
RESEARCH_LOOKBACK_DAYS = 10
# ev-rg1-hyper: a root-thesis-damage fact accepted only through the registry's thesis_damage_domains carries this
# marker; it reaches R-REC1 RG1 alone (never facts, evidence, C7 or EV3 (b)).
DAMAGE_DOMAIN_SOURCE = "THESIS_DAMAGE_DOMAIN"
# Card trigger kind -> allowed sides (r2 R2-9): alert and log kinds are never evidence, evidence kinds are + or -.
# The schema dialect (validation_common) has no if/then, so the registry schema states this rule and the loader
# enforces it: a mismatch makes that symbol ineligible (REGISTRY_KIND_SIDE_INVALID, no ticket).
KIND_SIDES = {
    "drop_alert": ("alert", "info"), "close_at_or_below": ("alert", "info"), "log_only": ("alert", "info"),
    "earnings_notice": ("alert", "info"), "display_only": ("alert", "info"),
    "ema_below": ("+", "-"), "ema20_below_twice": ("+", "-"), "ema_below_unrecovered": ("+", "-"),
    "new_high_hold": ("+", "-"), "pullback_rebound": ("+", "-"), "good_news_drop": ("+", "-"),
}


# ---------------------------------------------------------------------------------------------
# F2 card registry
# ---------------------------------------------------------------------------------------------

def section_text(text: str, heading: str) -> str | None:
    """Heading line + following lines up to the next heading of the same or a higher level (LF joined)."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the file's final newline is not a line of the last section
    level = len(heading) - len(heading.lstrip("#"))
    for index, line in enumerate(lines):
        if line != heading:
            continue
        end = len(lines)
        for later in range(index + 1, len(lines)):
            candidate = lines[later]
            if candidate.startswith("#"):
                depth = len(candidate) - len(candidate.lstrip("#"))
                if candidate[depth:depth + 1] == " " and depth <= level:
                    end = later
                    break
        return "\n".join(lines[index:end])
    return None


def section_sha256(text: str, heading: str) -> str | None:
    body = section_text(text, heading)
    return None if body is None else hashlib.sha256(body.encode("utf-8")).hexdigest()


def registry_committed(path: Path, repo: Path, runner: Callable[..., Any] = subprocess.run) -> tuple[bool, str | None]:
    """(committed, reason): the registry is tracked and has no uncommitted change (staged or not)."""
    try:
        relative = Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return False, "REGISTRY_OUTSIDE_REPOSITORY"
    try:
        tracked = runner(["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", relative],
                         capture_output=True, text=True, encoding="utf-8", check=False, timeout=30)
        status = runner(["git", "-C", str(repo), "status", "--porcelain=v1", "--", relative],
                        capture_output=True, text=True, encoding="utf-8", check=False, timeout=30)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False, "REGISTRY_GIT_UNAVAILABLE"
    if tracked.returncode != 0:
        return False, "REGISTRY_UNCOMMITTED"
    if status.returncode != 0:
        return False, "REGISTRY_GIT_UNAVAILABLE"
    return (False, "REGISTRY_UNCOMMITTED") if (status.stdout or "").strip() else (True, None)


def kind_side_mismatches(entry: dict[str, Any] | None) -> list[str]:
    """Card trigger ids whose side is not allowed for their kind (KIND_SIDES)."""
    return [str(trigger.get("id")) for trigger in (entry or {}).get("card_triggers") or []
            if isinstance(trigger, dict) and trigger.get("side") not in KIND_SIDES.get(trigger.get("kind"), ())]


def load_registry(path: Path = REGISTRY_PATH, *, repo: Path = REPO_ROOT,
                  committed_check: Callable[[Path, Path], tuple[bool, str | None]] = registry_committed
                  ) -> dict[str, Any]:
    """{status OK|MISSING|INVALID, errors, entries, sha256, committed, commit_reason, damage_domains}.

    damage_domains (ev-rg1-hyper): the top-level thesis_damage_domains in lower case; empty unless status is OK."""
    path = Path(path)
    result: dict[str, Any] = {"status": "MISSING", "errors": [], "entries": {}, "sha256": None,
                              "committed": False, "commit_reason": "REGISTRY_MISSING", "path": REGISTRY_RELATIVE,
                              "damage_domains": []}
    if not path.is_file():
        return result
    raw = path.read_bytes()
    result["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        return {**result, "status": "INVALID", "errors": ["REGISTRY_NOT_JSON"]}
    errors = validate_instance(document, REGISTRY_SCHEMA)
    for symbol, entry in (document.get("symbols") or {}).items() if isinstance(document, dict) else []:
        for item in (entry or {}).get("static_evidence") or []:
            if isinstance(item, dict) and len(str(item.get("quote") or "")) > QUOTE_MAX:
                errors.append(f"QUOTE_TOO_LONG:{symbol}:{item.get('id')}")
    if errors:
        return {**result, "status": "INVALID", "errors": errors[:10]}
    committed, reason = committed_check(path, repo)
    invalid = {symbol: ids for symbol, entry in document["symbols"].items() if (ids := kind_side_mismatches(entry))}
    return {**result, "status": "OK", "entries": document["symbols"], "committed": committed,
            "commit_reason": reason, "kind_side_invalid": invalid,
            "damage_domains": [str(domain).lower() for domain in document.get("thesis_damage_domains") or []]}


def load_watchlist(path: Path = WATCHLIST_PATH) -> dict[str, Any]:
    """{status, members {code: {card, cardStatus, sector}}}; an unreadable file means no members (fail closed)."""
    try:
        document = load_json(path)
        members = {str(item["code"]).upper(): {"card": item.get("card"), "cardStatus": item.get("cardStatus"),
                                               "sector": item.get("sector")}
                   for item in document["members"] if isinstance(item, dict) and item.get("code")}
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "UNREADABLE", "members": {}}
    return {"status": "OK", "members": members}


def card_check(symbol: str, registry: dict[str, Any], watchlist: dict[str, Any], *, repo: Path = REPO_ROOT,
               held: bool) -> dict[str, Any]:
    """Registry status of one symbol: entry, acceptance, section hash, commit -> ticket eligibility."""
    entry = registry["entries"].get(symbol) if registry["status"] == "OK" else None
    out: dict[str, Any] = {"symbol": symbol, "entry": entry, "eligible": False, "reasons": [], "hash_ok": False,
                           "accepted": False}
    if registry["status"] != "OK":
        out["reasons"].append(f"REGISTRY_{registry['status']}")
        return out
    if entry is None:
        out["reasons"].append("NOCARD" if held else "REGISTRY_ENTRY_MISSING")
        return out
    document = Path(repo) / entry["card_doc"]
    try:
        digest = section_sha256(document.read_text(encoding="utf-8-sig"), entry["card_section"])
    except OSError:
        digest = None
    out["hash_ok"] = digest == entry["section_sha256"]
    if not out["hash_ok"]:
        out["reasons"].append("CARD_SECTION_CHANGED")
    if kind_side_mismatches(entry):
        out["reasons"].append("REGISTRY_KIND_SIDE_INVALID")
    if entry["role"] == "watch":
        status = str((watchlist["members"].get(symbol) or {}).get("cardStatus") or "")
        out["accepted"] = status.startswith(ACCEPTED_PREFIX)
        if not out["accepted"]:
            out["reasons"].append("CARD_NOT_ACCEPTED_IN_WATCHLIST")
    else:
        out["accepted"] = bool(entry["accepted"].get("text"))
    if not registry["committed"]:
        out["reasons"].append(registry["commit_reason"] or "REGISTRY_UNCOMMITTED")
    out["eligible"] = not out["reasons"]
    return out


def m6_documents(docs_dir: Path) -> list[tuple[str, str]]:
    return [(path.name, path.read_text(encoding="utf-8-sig"))
            for path in sorted(Path(docs_dir).glob(M6_PREFIX + "*.md"))]


# ---------------------------------------------------------------------------------------------
# F3 research records
# ---------------------------------------------------------------------------------------------

def _moment(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _host_allowed(url: Any, domains: list[str]) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    allowed = ["sec.gov"] + [domain.lower() for domain in domains]
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def check_record(document: Any, *, record_day: str, calendar_sessions: list[str], decide_time: datetime,
                 registry: dict[str, Any]) -> dict[str, Any]:
    """{status OK|INVALID, reasons, facts (kept), dropped [{fact_id, reason}], earnings, integrated_check_run}.

    ev-rg1-hyper: a root_thesis_damage fact whose https host is not sec.gov or the symbol's official domain but
    matches the registry damage_domains goes through the remaining checks and, if it passes, into damage_only
    (a key present only when it has one) instead of facts: R-REC1 RG1 only."""
    out: dict[str, Any] = {"status": "INVALID", "reasons": [], "facts": [], "dropped": [], "earnings": None,
                           "integrated_check_run": None, "evaluation_session": None, "written_at": None,
                           "record_day_kst": record_day}
    errors = validate_instance(document, RESEARCH_SCHEMA)
    if errors:
        out["reasons"] = ["RESEARCH_RECORD_SCHEMA_INVALID"] + errors[:3]
        return out
    session = document["evaluation_session"]
    written = _moment(document["written_at"])
    out.update(evaluation_session=session, written_at=document["written_at"])
    if document["record_day_kst"] != record_day:
        out["reasons"].append("RESEARCH_RECORD_DAY_MISMATCH")
        return out
    if session not in calendar_sessions:
        out["reasons"].append("RESEARCH_RECORD_SESSION_NOT_IN_CALENDAR")
        return out
    not_before = datetime.combine(date.fromisoformat(session), FACT_CHECK_NOT_BEFORE, tzinfo=ET)
    if written is None or written < not_before or written > decide_time:
        out["reasons"].append("RESEARCH_RECORD_WRITTEN_AT_OUT_OF_RANGE")
        return out
    entries = registry.get("entries") or {}
    damage_domains = list(registry.get("damage_domains") or [])
    damage_only: list[dict[str, Any]] = []
    for fact in document["official_facts"]:
        domains = list((entries.get(fact["symbol"]) or {}).get("official_domains") or [])
        reason = None
        official = _host_allowed(fact["source_url"], domains)
        damage_domain = (not official and fact["root_thesis_damage"] is True
                         and _host_allowed(fact["source_url"], damage_domains))
        if fact["source_kind"] not in SOURCE_KINDS:
            reason = "SOURCE_KIND_INVALID"
        elif not official and not damage_domain:
            reason = "SOURCE_HOST_NOT_OFFICIAL"
        elif fact["event_session"] not in calendar_sessions or fact["event_session"] > session:
            reason = "EVENT_SESSION_INVALID"
        elif _moment(fact["announced_at"]) is None or _moment(fact["announced_at"]) > decide_time:
            reason = "ANNOUNCED_AT_INVALID"
        elif len(fact["summary_ko"]) > SUMMARY_MAX:
            reason = "SUMMARY_TOO_LONG"
        if reason:
            out["dropped"].append({"fact_id": fact["fact_id"], "symbol": fact["symbol"], "reason": reason})
        elif damage_domain:
            damage_only.append({**fact, "damage_source": DAMAGE_DOMAIN_SOURCE})
        else:
            out["facts"].append(dict(fact))
    out.update(status="OK", earnings=document["earnings"], integrated_check_run=document["integrated_check_run"])
    if damage_only:
        out["damage_only"] = damage_only
    return out


def load_research(*, root: Path = RESEARCH_ROOT, run_day: str, calendar_sessions: list[str], decide_time: datetime,
                  registry: dict[str, Any], lookback_days: int = RESEARCH_LOOKBACK_DAYS,
                  window_start: str | None = None) -> dict[str, Any]:
    """Today's record (status, earnings, run copy), the official facts of the last `lookback_days` valid records
    (C7 and new official evidence) and, over the R-REC1 window (record days from window_start, r2 R2-4), the
    root-thesis-damage facts (RG1, EV3 (b); ev-rg1-hyper: with the thesis-damage-domain facts, marked damage_source,
    RG1 only) and the evaluation sessions that have a valid record. Records dated after run_day are ignored."""
    available = sorted(path.parent.name for path in Path(root).glob(f"*/{RESEARCH_FILE}")
                       if path.parent.name <= run_day)
    days = available[-lookback_days:]
    window = [day for day in available if window_start is not None and day >= window_start]
    today: dict[str, Any] = {"status": "MISSING", "reasons": ["RESEARCH_RECORD_MISSING"], "facts": [],
                             "dropped": [], "earnings": None, "integrated_check_run": None,
                             "record_day_kst": run_day, "evaluation_session": None, "written_at": None}
    facts: dict[str, dict[str, Any]] = {}
    damage: dict[str, dict[str, Any]] = {}
    sessions: set[str] = set()
    for day in sorted(set(days) | set(window)):
        path = Path(root) / day / RESEARCH_FILE
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            checked = {**today, "status": "INVALID", "reasons": ["RESEARCH_RECORD_NOT_JSON"], "record_day_kst": day}
        else:
            checked = check_record(document, record_day=day, calendar_sessions=calendar_sessions,
                                   decide_time=decide_time, registry=registry)
        if checked["status"] == "OK":
            for fact in checked["facts"]:
                if day in days:
                    facts.setdefault(fact["fact_id"], {**fact, "record_day_kst": day})
                if day in window and fact.get("root_thesis_damage"):
                    damage.setdefault(fact["fact_id"], {**fact, "record_day_kst": day})
            # ev-rg1-hyper: a thesis-damage-domain fact (marked) joins only the damage facts (RG1), never facts.
            for fact in checked.get("damage_only") or []:
                if day in window:
                    damage.setdefault(fact["fact_id"], {**fact, "record_day_kst": day})
            if day in window:
                sessions.add(checked["evaluation_session"])
        if day == run_day:
            today = checked
    return {"today": today, "facts": sorted(facts.values(), key=lambda item: (item["event_session"], item["fact_id"])),
            "days": days, "window_days": window, "sessions": sorted(sessions),
            "damage": sorted(damage.values(), key=lambda item: (item["event_session"], item["fact_id"]))}


def research_record_exists(root: Path, run_day: str) -> bool:
    return (Path(root) / run_day / RESEARCH_FILE).is_file()
