"""API pilot 4 (llm-srccheck): daily re-check of already verified official facts.

Facts that the research record or the official filing intake already marks as
verified and that carry a source URL are re-checked once against that URL: one
Message Batch request per fact, with the server web fetch tool limited to the
URL's own host, one use and citations on. The answer is a verdict line and a
quoted evidence line.

Submit phase (08:10 KST): collect at most DAILY_MAX targets that were never sent
before (seen.jsonl), check the month budget, create one batch, write batch.json
and append the targets to seen.jsonl.

Collect phase (10:10 KST): for the day folder and the three days before it,
every folder with batch.json and no checks.json is collected when its batch has
ended: usage lines once, checks.json, checks.md and the cumulative checks.jsonl.

Display only: the research record, the filing intake output, the integrated
check and the core never read these files and are never written. Writes only
under workspace/outputs/llm/. The script itself never requests any web address;
the only network call is the Anthropic Batch API through the shared client.

Usage: python manage-us-stock-strategy/scripts/llm_pilot_srccheck.py --phase submit|collect
       [--day YYYY-MM-DD] [--dry-run]
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_pilot_common import (  # noqa: E402
    BUDGET_USD_MONTH,
    KST,
    MODELS,
    REPO_ROOT,
    api_error_label,
    append_usage,
    atomic_write_text,
    check_message,
    estimate_cost,
    llm_dir,
    load_key,
    make_client,
    month_spend,
    response_text,
    write_failed,
)

PILOT = "srccheck"
MAX_TOKENS = 4096
EST_INPUT_TOKENS_PER_TARGET = 30_000
EST_OUTPUT_TOKENS_PER_TARGET = 4_096
DAILY_MAX = 5
SEC_LOOKBACK_DAYS = 2  # day-2 .. day
COLLECT_LOOKBACK_DAYS = 3  # day-3 .. day
QUOTE_MIN_CHARS = 6
EVIDENCE_JSON_CHARS = 200
EVIDENCE_MD_CHARS = 60
FIELD_MAX_CHARS = 300

BATCH_SCHEMA = "llm-srccheck-batch-1"
CHECKS_SCHEMA = "llm-srccheck-checks-1"

EXIT_CODES = {
    # same names as llm_pilot_pdfcmp / llm_pilot_news keep the same values
    "SUBMITTED": 0,
    "PENDING": 0,
    "WAITING": 0,
    "DONE_ALREADY": 0,
    "NO_BATCH": 0,
    "DRY_RUN": 0,
    "UNEXPECTED": 1,
    "NO_KEY": 4,
    "BUDGET_STOP": 5,
    "API_ERROR": 7,
    # this pilot
    "CHECKED": 0,
    "NO_TARGETS": 0,
}

# Filing forms re-checked (insider Form 4 and 144 are left out).
SEC_FORMS = ("8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A", "6-K", "20-F", "DEF 14A")
SEC_FIRST_FORMS = ("8-K", "8-K/A")

# Hosts the web fetch may open, fixed letter for letter by the task prompt
# (docs/claude/llm-srccheck-builder-prompt.md section 3).
ALLOWED_HOSTS = (
    "www.sec.gov",
    "www.federalreserve.gov",
    "www.bls.gov",
    "www.bea.gov",
    "home.treasury.gov",
    "fred.stlouisfed.org",
    "investors.delltechnologies.com",
    "investors.quantaservices.com",
    "investor.lumentum.com",
    "investor.marvell.com",
    "www.bloomenergy.com",
    "investor.bloomenergy.com",
    "investors.micron.com",
    "ir.crowdstrike.com",
    "nebius.com",
)
SEC_HOST = ALLOWED_HOSTS[0]
SEC_PATH_PREFIX = "/Archives/edgar/data/"
SEC_DOC_URL = "https://" + SEC_HOST + SEC_PATH_PREFIX + "%d/%s/%s"
BLOCKED_WORDS = ("cgi-bin", "efts", "daily-index", "rss", "browse-edgar")
URL_SCHEME = "https://"

WEB_FETCH_TYPE = "web_fetch_20260209"
WEB_FETCH_RESULT_TYPE = "web_fetch_tool_result"
WEB_FETCH_MAX_CONTENT_TOKENS = 20_000

_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SPACES = re.compile(r"\s+")
_CIK_RE = re.compile(r"[0-9]+")
_ACCESSION_RE = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_DOC_RE = re.compile(r"[A-Za-z0-9._-]+")
_VALUE_EDGE = "*`_ \t"

# Korean text is written as \uXXXX escapes: scripts/*.py must stay ASCII-only
# (test_language_contract). Decoded values are pinned in test_llm_pilot_srccheck.py.

V_MATCH = "\ub9de\uc74c"
V_MISMATCH = "\ud2c0\ub9bc"
V_UNDECIDED = "\ubbf8\uc815"
V_UNVERIFIABLE = "\ud655\uc778 \ubd88\uac00"
VERDICTS = (V_MATCH, V_MISMATCH, V_UNDECIDED, V_UNVERIFIABLE)

LABEL_VERDICT = "\ud310\uc815"
LABEL_EVIDENCE = "\uadfc\uac70"
LABEL_URL = "URL"
LABEL_CLAIM = "\uc8fc\uc7a5"

# Fixed instruction (task prompt section 4, letter for letter).
INSTRUCTION = (
    "\uc544\ub798 URL \ud558\ub098\ub9cc web_fetch\ub85c \ud55c \ubc88 \uc5f0\ub2e4. "
    "\ub2e4\ub978 URL\uc740 \uc5f4\uc9c0 \uc54a\ub294\ub2e4. "
    "\uc8fc\uc7a5\uc774 \uc6d0\ubb38\uacfc \ub9de\ub294\uc9c0 \ubcf8\ub2e4. "
    "\ub2f5\uc740 \ub450 \uc904\ub85c\ub9cc: "
    "`\ud310\uc815: \ub9de\uc74c|\ud2c0\ub9bc|\ubbf8\uc815|\ud655\uc778 \ubd88\uac00` / "
    "`\uadfc\uac70: <\uc6d0\ubb38 \ubb38\uc7a5 \uadf8\ub300\ub85c \ud55c \uc904>`. "
    "\uc8fc\uc7a5 \uc77c\ubd80\ub9cc \uc6d0\ubb38\uc5d0 \uc788\uc73c\uba74 `\ud310\uc815: \ubbf8\uc815`. "
    "\uc5f4 \uc218 \uc5c6\uac70\ub098 \uc6d0\ubb38\uc5d0 \ud574\ub2f9 \ub0b4\uc6a9\uc774 "
    "\uc5c6\uc73c\uba74 `\ud310\uc815: \ud655\uc778 \ubd88\uac00`."
)

# Claim sentences: built only from the allowed fields (task prompt sections 1-2).
TIMING_KO = {
    "BEFORE_OPEN": "\uc7a5 \uc2dc\uc791 \uc804",
    "AFTER_CLOSE": "\uc7a5 \ub9c8\uac10 \ud6c4",
}
# "<sym> earnings announcement day is <session>(<timing>) (source kind <kind>)"
CLAIM_EARNINGS = "%s\uc758 \uc2e4\uc801 \ubc1c\ud45c\uc77c\uc740 %s%s\uc774\ub2e4 (\ucd9c\ucc98 \uc885\ub958 %s)"
# "<sym> official fact (kind <kind>, event session <s>, announced at <t>): <summary>"
CLAIM_FACT = (
    "%s \uacf5\uc2dd \uc0ac\uc2e4(\uc885\ub958 %s, \uc0ac\uac74 \uc138\uc158 %s, "
    "\ubc1c\ud45c \uc2dc\uac01 %s): %s"
)
# "<company>(<ticker>)'s <form> document"
CLAIM_SEC_HEAD = "%s(%s)\uc758 %s \uc11c\ub958"
CLAIM_SEC_AND = "\uc774\uace0, "
CLAIM_SEC_REPORT = "\ubcf4\uace0 \uae30\uc900\uc77c %s"
CLAIM_SEC_ITEMS = "\ud56d\ubaa9 %s"
CLAIM_END = "\uc774\ub2e4"

REASON_KO = {
    "no_key": "\ud0a4 \uc5c6\uc74c",
    "usage_unreadable": "\uc0ac\uc6a9 \uae30\ub85d\uc744 \uc77d\uc744 \uc218 \uc5c6\uc74c",
    "budget_spent": "\uc774\ub2ec \uc608\uc0b0\uc744 \ub118\uc74c",
    "call_failed": "API \ud638\ucd9c \uc2e4\ud328 ",
    "bad_shape": "\uc751\ub2f5 \ud615\uc2dd \ub2e4\ub984",
    "unexpected": "\uc608\uc0c1 \ubabb \ud55c \uc624\ub958 (%s)",
}

MD_HEAD = (
    "\ucd9c\ucc98 \ud655\uc778 %s: \ub9de\uc74c %d \u00b7 \ud2c0\ub9bc %d \u00b7 \ubbf8\uc815 %d "
    "\u00b7 \ud655\uc778 \ubd88\uac00 %d (%d\uac74)"
)
MD_TABLE_HEAD = (
    "| # | \ucd9c\ucc98 | URL | \uc8fc\uc7a5 | \ud310\uc815 | \uc0ac\uc720 | \uadfc\uac70(60\uc790) |\n"
    "|---|---|---|---|---|---|---|"
)
MD_FOOTER = "\ud45c\uc2dc \uc804\uc6a9: \uc6d0\uc7a5\u00b7\ud1b5\ud569\uc810\uac80\u00b7\ucf54\uc5b4\ub294 \uc774 \uacb0\uacfc\ub97c \uc77d\uc9c0 \uc54a\ub294\ub2e4"


# ---------------------------------------------------------------- small helpers

def valid_day(text):
    if not isinstance(text, str) or not _DAY_RE.fullmatch(text):
        raise ValueError("day must be YYYY-MM-DD")
    date.fromisoformat(text)
    return text


def pilot_dir(root) -> Path:
    return llm_dir(root) / PILOT


def day_dir_for(root, day) -> Path:
    return pilot_dir(root) / day


def seen_path(root) -> Path:
    return pilot_dir(root) / "seen.jsonl"


def checks_log_path(root) -> Path:
    return pilot_dir(root) / "checks.jsonl"


def _days_back(day, n):
    """[day-n, ..., day] as YYYY-MM-DD strings, oldest first."""
    base = date.fromisoformat(day)
    return [(base - timedelta(days=i)).isoformat() for i in range(n, -1, -1)]


def _iso(moment) -> str:
    return moment.astimezone(KST).isoformat(timespec="seconds")


def _clock(now):
    if now is None:
        return lambda: datetime.now(KST)
    fixed = now.astimezone(KST)
    return lambda: fixed


def _attr(obj, name, default=None):
    if isinstance(obj, dict):
        value = obj.get(name, default)
    else:
        value = getattr(obj, name, default)
    return default if value is None else value


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _line(day, status, extra="") -> str:
    text = "llm-srccheck %s %s" % (day, status)
    if extra:
        text += " " + extra
    return _ascii(text)[:200]


def _ascii(text) -> str:
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def _norm_space(text) -> str:
    return _SPACES.sub(" ", str(text)).strip()


def _field(value):
    """A claim field: a non-empty one-line string, or None."""
    if not isinstance(value, str):
        return None
    value = _norm_space(value)[:FIELD_MAX_CHARS]
    return value or None


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def _read_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8-sig"))


def _append_jsonl(path, records) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- URL rule (no URL library)

def split_url(url):
    """(host, path) of an https URL, or None."""
    if not isinstance(url, str) or not url.startswith(URL_SCHEME):
        return None
    rest = url[len(URL_SCHEME):]
    slash = rest.find("/")
    if slash < 0:
        return rest, ""
    return rest[:slash], rest[slash:]


def url_reason(url):
    """None when the URL may be fetched, else HOST_NOT_ALLOWED|ROOT_PAGE|BLOCKED_PATH|BAD_URL."""
    parts = split_url(url)
    if parts is None:
        return "BAD_URL"
    if "?" in url or "#" in url or any(ch.isspace() for ch in url):
        return "BAD_URL"
    host, path = parts
    if not host:
        return "BAD_URL"
    if ".." in path.split("/"):
        return "BAD_URL"
    if host.lower() not in ALLOWED_HOSTS:
        return "HOST_NOT_ALLOWED"
    if path in ("", "/"):
        return "ROOT_PAGE"
    lowered = url.lower()
    if any(word in lowered for word in BLOCKED_WORDS):
        return "BLOCKED_PATH"
    if host.lower() == SEC_HOST and not path.startswith(SEC_PATH_PREFIX):
        return "BLOCKED_PATH"
    return None


def url_allowed(url) -> bool:
    return url_reason(url) is None


def url_host(url) -> str:
    return split_url(url)[0].lower()


def sec_document_url(event):
    """Archive URL built from cik, accession number and primary document, or None."""
    cik = event.get("cik")
    accession = event.get("accession_number")
    doc = event.get("primary_document")
    if not (isinstance(cik, str) and _CIK_RE.fullmatch(cik)):
        return None
    if not (isinstance(accession, str) and _ACCESSION_RE.fullmatch(accession)):
        return None
    if not (isinstance(doc, str) and _DOC_RE.fullmatch(doc)):
        return None
    return SEC_DOC_URL % (int(cik), accession.replace("-", ""), doc)


# ---------------------------------------------------------------- claim sentences

def claim_text(target) -> str:
    f = target["fields"]
    kind = target["kind"]
    if kind == "earnings":
        timing = f.get("timing")
        timing_text = "(%s)" % TIMING_KO.get(timing, timing) if timing else ""
        return CLAIM_EARNINGS % (f["symbol"], f["announcement_session"], timing_text, f["source_kind"])
    if kind == "fact":
        return CLAIM_FACT % (f["symbol"], f["kind"], f["event_session"], f["announced_at"], f["summary_ko"])
    if kind == "sec":
        extras = []
        if f.get("report_date"):
            extras.append(CLAIM_SEC_REPORT % f["report_date"])
        if f.get("items"):
            extras.append(CLAIM_SEC_ITEMS % ", ".join(f["items"]))
        text = CLAIM_SEC_HEAD % (f["company_name"], f["ticker"], f["form"])
        if extras:
            text += CLAIM_SEC_AND + ", ".join(extras)
        return text + CLAIM_END
    raise ValueError("unknown target kind")


# ---------------------------------------------------------------- targets

def _research_targets(root, day, skipped):
    """Targets from the research record: (facts, earnings). Missing file -> none."""
    path = Path(root) / "workspace" / "outputs" / "research-records" / day / "research-record.json"
    if not path.is_file():
        return [], []
    try:
        record = _read_json(path)
    except (OSError, ValueError):
        skipped.append({"key": "file:research-record/%s" % day, "reason": "BROKEN_FILE"})
        return [], []
    if not isinstance(record, dict):
        skipped.append({"key": "file:research-record/%s" % day, "reason": "BROKEN_FILE"})
        return [], []

    facts = []
    raw_facts = record.get("official_facts")
    if isinstance(raw_facts, list):
        for item in raw_facts:
            if not isinstance(item, dict):
                continue
            url = item.get("source_url")
            if not isinstance(url, str) or not url:
                continue
            fields = {name: _field(item.get(name)) for name in
                      ("symbol", "kind", "event_session", "announced_at", "summary_ko")}
            if any(value is None for value in fields.values()):
                skipped.append({"key": url, "reason": "MISSING_FIELDS"})
                continue
            facts.append({"key": url, "url": url, "source": "a", "kind": "fact", "fields": fields})

    earnings = []
    raw_earnings = record.get("earnings")
    if isinstance(raw_earnings, dict):
        for symbol in sorted(k for k in raw_earnings if isinstance(k, str)):
            item = raw_earnings[symbol]
            if not isinstance(item, dict) or item.get("status") != "VERIFIED":
                continue  # NOT_ANNOUNCED cannot be checked against a source
            url = item.get("source_url")
            if not isinstance(url, str) or not url:
                continue
            fields = {
                "symbol": _field(symbol),
                "announcement_session": _field(item.get("announcement_session")),
                "source_kind": _field(item.get("source_kind")),
            }
            if any(value is None for value in fields.values()):
                skipped.append({"key": url, "reason": "MISSING_FIELDS"})
                continue
            timing = _field(item.get("timing"))
            if timing is not None:
                fields["timing"] = timing
            earnings.append({"key": url, "url": url, "source": "a", "kind": "earnings", "fields": fields})
    return facts, earnings


def _sec_targets(root, day, skipped):
    base = Path(root) / "workspace" / "outputs" / "official-event-intake" / "sec"
    out = []
    for folder_day in _days_back(day, SEC_LOOKBACK_DAYS):
        day_folder = base / folder_day
        if not day_folder.is_dir():
            continue
        for path in sorted(day_folder.glob("*/normalized-events.json")):
            label = "file:sec/%s/%s" % (folder_day, path.parent.name)
            try:
                doc = _read_json(path)
            except (OSError, ValueError):
                skipped.append({"key": label, "reason": "BROKEN_FILE"})
                continue
            events = doc.get("events") if isinstance(doc, dict) else None
            if not isinstance(events, list):
                skipped.append({"key": label, "reason": "BROKEN_FILE"})
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                if event.get("verification_status") != "OFFICIAL_SOURCE_VERIFIED":
                    continue
                form = event.get("form")
                if form not in SEC_FORMS:
                    continue  # insider Form 4 / 144 and other forms are left out
                accession = event.get("accession_number")
                key = "sec:%s" % accession if isinstance(accession, str) else "sec:?"
                url = sec_document_url(event)
                if url is None:
                    skipped.append({"key": key, "reason": "BAD_SEC_FIELDS"})
                    continue
                fields = {
                    "ticker": _field(event.get("ticker")),
                    "company_name": _field(event.get("company_name")),
                    "form": form,
                }
                if fields["ticker"] is None or fields["company_name"] is None:
                    skipped.append({"key": key, "reason": "MISSING_FIELDS"})
                    continue
                report_date = _field(event.get("report_date"))
                if report_date is not None:
                    fields["report_date"] = report_date
                items = event.get("items_if_available")
                if isinstance(items, list):
                    clean = [v for v in (_field(x) for x in items) if v is not None]
                    if clean:
                        fields["items"] = clean
                filing_date = event.get("filing_date")
                out.append({
                    "key": key,
                    "url": url,
                    "source": "b",
                    "kind": "sec",
                    "fields": fields,
                    "order": filing_date if isinstance(filing_date, str) else "",
                })
    # filing_date newest first, then 8-K / 8-K/A ahead of the rest (stable sorts)
    out.sort(key=lambda t: t["order"], reverse=True)
    out.sort(key=lambda t: 0 if t["fields"]["form"] in SEC_FIRST_FORMS else 1)
    return out


def read_seen(root):
    """Keys already sent. A broken line raises (fail closed: never resend blindly)."""
    path = seen_path(root)
    keys = set()
    if not path.exists():
        return keys
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            if raw.strip() == "":
                continue
            rec = json.loads(raw)
            if not isinstance(rec, dict) or not isinstance(rec.get("key"), str):
                raise ValueError("seen.jsonl line has no key")
            keys.add(rec["key"])
    return keys


def collect_targets(root, day):
    """Return (targets, skipped): at most DAILY_MAX targets never sent before."""
    day = valid_day(day)
    skipped = []
    facts, earnings = _research_targets(root, day, skipped)
    sec = _sec_targets(root, day, skipped)
    seen = read_seen(root)
    targets = []
    for target in facts + earnings + sec:
        if target["key"] in seen:
            continue
        reason = url_reason(target["url"])
        if reason is not None:
            skipped.append({"key": target["key"], "reason": reason})
            seen.add(target["key"])  # report each refused key once per day
            continue
        seen.add(target["key"])
        target.pop("order", None)
        target["claim"] = claim_text(target)
        targets.append(target)
    return targets[:DAILY_MAX], skipped


# ---------------------------------------------------------------- submit

def estimate_submit_cost(n_targets) -> float:
    one = estimate_cost(
        MODELS[PILOT],
        {"input_tokens": EST_INPUT_TOKENS_PER_TARGET, "output_tokens": EST_OUTPUT_TOKENS_PER_TARGET},
        batch=True,
    )
    return one * n_targets


def web_fetch_tool(host):
    return {
        "type": WEB_FETCH_TYPE,
        "name": "web_fetch",
        "max_uses": 1,
        "allowed_domains": [host],
        "max_content_tokens": WEB_FETCH_MAX_CONTENT_TOKENS,
        "citations": {"enabled": True},
    }


def request_text(url, claim) -> str:
    return "%s\n\n%s: %s\n%s: %s" % (INSTRUCTION, LABEL_URL, url, LABEL_CLAIM, claim)


def build_request(custom_id, url, claim):
    return {
        "custom_id": custom_id,
        "params": {
            "model": MODELS[PILOT],
            "max_tokens": MAX_TOKENS,
            "tools": [web_fetch_tool(url_host(url))],
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": request_text(url, claim)}],
                }
            ],
        },
    }


def _remove_stale_failed(out_dir) -> None:
    path = Path(out_dir) / "failed.md"
    if path.exists():
        path.unlink()


def run_submit(day, *, repo_root=REPO_ROOT, client_factory=None, now=None, dry_run=False):
    """Return (exit_code, status, lines); the last line is the status line."""
    day = valid_day(day)
    root = Path(repo_root)
    clock = _clock(now)
    started = clock()
    out_dir = day_dir_for(root, day)

    def done(status, extra="", before=()):
        return EXIT_CODES[status], status, list(before) + [_line(day, status, extra)]

    def fail(status, reason_ko, extra=""):
        write_failed(out_dir, status, reason_ko)
        return done(status, extra)

    # 1. once a day
    if (out_dir / "checks.json").exists():
        return done("DONE_ALREADY")
    if (out_dir / "batch.json").exists():
        return done("PENDING")

    # 2. targets (read only)
    targets, skipped = collect_targets(root, day)
    counts = "targets=%d skipped=%d" % (len(targets), len(skipped))
    if dry_run:
        listing = ["target %s %s %s" % (t["source"], _ascii(t["key"]), _ascii(t["url"])) for t in targets]
        listing += ["skipped %s %s" % (_ascii(s["key"]), s["reason"]) for s in skipped]
        return done("DRY_RUN", counts, listing)
    if not targets:
        return done("NO_TARGETS", counts)

    # 3. key; only load_key() reads it and the value goes to the client factory alone
    key = load_key()
    if key is None:
        return fail("NO_KEY", REASON_KO["no_key"])

    # 4. month budget before any call; an unreadable usage file stops too
    try:
        spent = month_spend(root, PILOT, started.strftime("%Y-%m"))
    except Exception:
        return fail("BUDGET_STOP", REASON_KO["usage_unreadable"])
    if spent + estimate_submit_cost(len(targets)) > BUDGET_USD_MONTH[PILOT]:
        return fail("BUDGET_STOP", REASON_KO["budget_spent"])

    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None

    # 5. one batch, one request per target
    items = []
    for i, target in enumerate(targets, 1):
        items.append({
            "custom_id": "t%d" % i,
            "key": target["key"],
            "url": target["url"],
            "claim": target["claim"],
            "source": target["source"],
        })
    requests = [build_request(item["custom_id"], item["url"], item["claim"]) for item in items]
    try:
        batch = client.messages.batches.create(requests=requests)
    except Exception as exc:
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    batch_id = _attr(batch, "id", None)
    if not isinstance(batch_id, str) or not batch_id:
        return fail("API_ERROR", REASON_KO["bad_shape"])

    # 6. batch file, then seen (a sent key is never sent again, whatever the result)
    doc = {
        "schema": BATCH_SCHEMA,
        "day": day,
        "status": "SUBMITTED",
        "batch_id": batch_id,
        "model": MODELS[PILOT],
        "submitted_at": _iso(clock()),
        "items": items,
        "skipped": skipped,
    }
    atomic_write_text(out_dir / "batch.json", _dump(doc))
    _append_jsonl(seen_path(root), [{"key": item["key"], "day": day, "url": item["url"]} for item in items])
    _remove_stale_failed(out_dir)
    return done("SUBMITTED", "requests=%d %s" % (len(requests), counts))


# ---------------------------------------------------------------- answer parsing

def _field_pattern(label):
    return re.compile(
        r"^[ \t>*_`-]*" + re.escape(label) + r"[ \t*_`]*[:\uff1a][ \t]*(.*?)[ \t]*$",
        re.MULTILINE,
    )


_VERDICT_LINE = _field_pattern(LABEL_VERDICT)
_EVIDENCE_LINE = _field_pattern(LABEL_EVIDENCE)


def parse_answer(text):
    """{"verdict", "evidence"} from the last verdict and evidence lines, or None (PARSE_FAIL)."""
    if not isinstance(text, str):
        return None
    verdicts = _VERDICT_LINE.findall(text)
    evidences = _EVIDENCE_LINE.findall(text)
    if not verdicts or not evidences:
        return None
    verdict = _norm_space(verdicts[-1].strip(_VALUE_EDGE))
    evidence = evidences[-1].strip(_VALUE_EDGE)
    if verdict not in VERDICTS or not evidence:
        return None
    return {"verdict": verdict, "evidence": evidence}


def citation_texts(message):
    out = []
    for block in _attr(message, "content", []) or []:
        if _attr(block, "type", None) != "text":
            continue
        for cite in _attr(block, "citations", []) or []:
            text = _attr(cite, "cited_text", None)
            if isinstance(text, str) and text.strip():
                out.append(text)
    return out


def quote_overlaps(cited, evidence) -> bool:
    a = _norm_space(cited)
    b = _norm_space(evidence)
    if len(a) < QUOTE_MIN_CHARS or len(b) < QUOTE_MIN_CHARS:
        return False
    match = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return match.size >= QUOTE_MIN_CHARS


def block_types(message):
    return [str(_attr(block, "type", "?")) for block in _attr(message, "content", []) or []]


def fetch_check(message, url):
    """(reason, error_code): reason None when every fetch result is the input URL, letter for letter."""
    blocks = [b for b in _attr(message, "content", []) or [] if _attr(b, "type", None) == WEB_FETCH_RESULT_TYPE]
    if not blocks:
        return "NO_FETCH_RESULT", None
    refused = None
    for block in blocks:
        result = _attr(block, "content", None)
        kind = str(_attr(result, "type", ""))
        code = _attr(result, "error_code", None)
        if "error" in kind or code is not None:
            if refused is None:
                refused = str(code) if code is not None else kind
            continue
        if _attr(result, "url", None) != url:
            return "URL_MISMATCH", None
    if refused is not None:
        return "FETCH_REFUSED", refused[:80]
    return None, None


def evaluate(result, url, expected_model):
    row = {
        "verdict": V_UNVERIFIABLE,
        "model_verdict": None,
        "reason": None,
        "evidence": None,
        "block_types": [],
        "stop_reason": None,
        "fetch_error": None,
    }
    if result is None:
        row["reason"] = "NO_RESULT"
        return row
    kind = _attr(result, "type", None)
    if kind != "succeeded":
        row["reason"] = str(kind).upper() if isinstance(kind, str) and kind else "NO_RESULT"
        return row
    message = _attr(result, "message", None)
    if message is None:
        row["reason"] = "NO_RESULT"
        return row
    row["block_types"] = block_types(message)
    stop = _attr(message, "stop_reason", None)
    row["stop_reason"] = stop if isinstance(stop, str) else None
    problem = check_message(message, expected_model)
    if problem:
        row["reason"] = problem
        return row
    reason, code = fetch_check(message, url)
    if reason:
        row["reason"] = reason
        row["fetch_error"] = code
        return row
    parsed = parse_answer(response_text(message))
    if parsed is None:
        row["reason"] = "PARSE_FAIL"
        return row
    row["model_verdict"] = parsed["verdict"]
    row["evidence"] = parsed["evidence"][:EVIDENCE_JSON_CHARS]
    if parsed["verdict"] == V_UNVERIFIABLE:
        return row
    if not any(quote_overlaps(text, parsed["evidence"]) for text in citation_texts(message)):
        row["reason"] = "NO_CITATION"
        return row
    row["verdict"] = parsed["verdict"]
    return row


# ---------------------------------------------------------------- collect

def _usage_numbers(usage) -> dict:
    out = {}
    for name in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        value = _attr(usage, name, None)
        out[name] = value if _is_int(value) else 0
    return out


def _message_cost(model, numbers) -> float:
    try:
        return estimate_cost(model, numbers, batch=True)
    except ValueError:
        # a model without a price is priced as the pinned model
        return estimate_cost(MODELS[PILOT], numbers, batch=True)


def _cell(text) -> str:
    return _norm_space(text).replace("|", "/")


def verdict_counts(rows):
    return {
        "match": sum(1 for r in rows if r["verdict"] == V_MATCH),
        "mismatch": sum(1 for r in rows if r["verdict"] == V_MISMATCH),
        "undecided": sum(1 for r in rows if r["verdict"] == V_UNDECIDED),
        "unverifiable": sum(1 for r in rows if r["verdict"] == V_UNVERIFIABLE),
        "total": len(rows),
    }


def render_md(doc) -> str:
    c = doc["counts"]
    lines = [
        MD_HEAD % (doc["day"], c["match"], c["mismatch"], c["undecided"], c["unverifiable"], c["total"]),
        "",
        MD_TABLE_HEAD,
    ]
    for i, row in enumerate(doc["rows"], 1):
        lines.append(
            "| %d | %s | %s | %s | %s | %s | %s |"
            % (
                i,
                row["source"],
                _cell(row["url"]),
                _cell(row["claim"]),
                row["verdict"],
                row["reason"] or "-",
                _cell((row["evidence"] or "-")[:EVIDENCE_MD_CHARS]),
            )
        )
    lines.append("")
    lines.append(MD_FOOTER)
    return "\n".join(lines) + "\n"


def _write_usage_once(root, folder, entries, received_at) -> None:
    usage_done = folder / "usage-done"
    if usage_done.exists():
        return
    expected = MODELS[PILOT]
    for entry in entries:
        res = _attr(entry, "result", None)
        message = _attr(res, "message", None)
        if _attr(res, "type", None) != "succeeded" or message is None:
            continue
        model = _attr(message, "model", "")
        model = model if isinstance(model, str) and model else expected
        numbers = _usage_numbers(_attr(message, "usage", None))
        record = dict(numbers)
        record.update(
            {
                "ts_kst": received_at,
                "pilot": PILOT,
                "model": model,
                "batch": True,
                "cost_usd_est": _message_cost(model, numbers),
                "status": check_message(message, expected) or "OK",
            }
        )
        append_usage(root, record)
    atomic_write_text(usage_done, received_at + "\n")


def collect_folder(root, folder_day, client, clock):
    """Collect one day folder. Returns the status (WAITING|CHECKED|API_ERROR) and an extra text."""
    folder = day_dir_for(root, folder_day)
    batch = _read_json(folder / "batch.json")
    if not isinstance(batch, dict) or batch.get("status") != "SUBMITTED":
        raise ValueError("batch.json is not a submitted batch")
    batch_id = batch.get("batch_id")
    items = batch.get("items")
    if not isinstance(batch_id, str) or not isinstance(items, list):
        raise ValueError("batch.json has a bad shape")
    for item in items:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in
                                                 ("custom_id", "key", "url", "claim", "source")):
            raise ValueError("batch.json item has a bad shape")

    try:
        info = client.messages.batches.retrieve(batch_id)
    except Exception as exc:
        write_failed(folder, "API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
        return "API_ERROR", ""
    if _attr(info, "processing_status", None) != "ended":
        return "WAITING", ""
    try:
        entries = list(client.messages.batches.results(batch_id))
    except Exception as exc:
        write_failed(folder, "API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
        return "API_ERROR", ""
    received_at = _iso(clock())
    expected = MODELS[PILOT]

    _write_usage_once(root, folder, entries, received_at)

    sent = [item["custom_id"] for item in items]
    by_id = {}
    for entry in entries:
        custom_id = _attr(entry, "custom_id", None)
        if custom_id in sent and custom_id not in by_id:
            by_id[custom_id] = _attr(entry, "result", None)

    rows = []
    for item in items:
        row = {
            "custom_id": item["custom_id"],
            "key": item["key"],
            "url": item["url"],
            "source": item["source"],
            "claim": item["claim"],
        }
        row.update(evaluate(by_id.get(item["custom_id"]), item["url"], expected))
        rows.append(row)

    counts = verdict_counts(rows)
    doc = {
        "schema": CHECKS_SCHEMA,
        "day": folder_day,
        "batch_id": batch_id,
        "model": expected,
        "submitted_at": batch.get("submitted_at"),
        "received_at": received_at,
        "counts": counts,
        "rows": rows,
        "skipped": batch.get("skipped") or [],
        "display_only": True,
    }
    atomic_write_text(folder / "checks.json", _dump(doc))
    atomic_write_text(folder / "checks.md", render_md(doc))
    _append_jsonl(
        checks_log_path(root),
        [{"day": folder_day, "key": r["key"], "url": r["url"], "verdict": r["verdict"], "reason": r["reason"]}
         for r in rows],
    )
    _remove_stale_failed(folder)
    extra = "match=%d mismatch=%d undecided=%d unverifiable=%d n=%d" % (
        counts["match"], counts["mismatch"], counts["undecided"], counts["unverifiable"], counts["total"])
    return "CHECKED", extra


def run_collect(day, *, repo_root=REPO_ROOT, client_factory=None, now=None, dry_run=False):
    """Return (exit_code, status, lines); the last line is the status line."""
    day = valid_day(day)
    root = Path(repo_root)
    clock = _clock(now)
    out_dir = day_dir_for(root, day)

    folders = [
        d for d in _days_back(day, COLLECT_LOOKBACK_DAYS)
        if (day_dir_for(root, d) / "batch.json").exists() and not (day_dir_for(root, d) / "checks.json").exists()
    ]
    if not folders:
        if (out_dir / "checks.json").exists():
            return EXIT_CODES["DONE_ALREADY"], "DONE_ALREADY", [_line(day, "DONE_ALREADY")]
        return EXIT_CODES["NO_BATCH"], "NO_BATCH", [_line(day, "NO_BATCH")]
    if dry_run:
        return EXIT_CODES["DRY_RUN"], "DRY_RUN", [_line(day, "DRY_RUN", "folders=" + ",".join(folders))]

    key = load_key()
    if key is None:
        write_failed(out_dir, "NO_KEY", REASON_KO["no_key"])
        return EXIT_CODES["NO_KEY"], "NO_KEY", [_line(day, "NO_KEY")]
    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None

    results = []
    for folder_day in folders:
        status, extra = collect_folder(root, folder_day, client, clock)
        results.append((folder_day, status, extra))

    final = [r for r in results if r[0] == day] or [results[-1]]
    final_day, final_status, final_extra = final[0]
    lines = [_line(d, s, e) for d, s, e in results if d != final_day]
    lines.append(_line(final_day, final_status, final_extra))
    return EXIT_CODES[final_status], final_status, lines


# ---------------------------------------------------------------- main

def _write_unexpected(out_dir, exc) -> None:
    try:
        write_failed(out_dir, "UNEXPECTED", REASON_KO["unexpected"] % type(exc).__name__)
    except Exception:
        pass


def main(argv=None, *, repo_root=REPO_ROOT, client_factory=None, now=None) -> int:
    parser = argparse.ArgumentParser(description="llm-srccheck: re-check verified official facts at their source (display only)")
    parser.add_argument("--phase", required=True, choices=("submit", "collect"))
    parser.add_argument("--day", type=valid_day, default=None, help="KST date YYYY-MM-DD (default: today KST)")
    parser.add_argument("--dry-run", action="store_true", help="list the targets only; no key, no call, no write")
    args = parser.parse_args(argv)
    day = args.day or (now or datetime.now(KST)).astimezone(KST).date().isoformat()
    try:
        if args.phase == "submit":
            code, _status, lines = run_submit(
                day, repo_root=repo_root, client_factory=client_factory, now=now, dry_run=args.dry_run,
            )
        else:
            code, _status, lines = run_collect(
                day, repo_root=repo_root, client_factory=client_factory, now=now, dry_run=args.dry_run,
            )
    except Exception as exc:
        code = EXIT_CODES["UNEXPECTED"]
        lines = [_line(day, "UNEXPECTED")]
        if not args.dry_run:
            _write_unexpected(day_dir_for(repo_root, day), exc)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
