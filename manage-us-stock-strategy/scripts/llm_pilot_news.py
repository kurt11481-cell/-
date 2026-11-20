"""API pilot 2 (llm-news): news digest and anonymized shadow labels via Message Batches.

Submit phase (19:30 KST): fetch the new news items of the 30 pre-registered
symbols and send one Message Batch with two requests per item:
  - a label request on the anonymized title and summary (shadow score; it is
    appended to the hash-chained record and never displayed), and
  - a Korean 3-line summary request on the original text (display only).

Collect phase (22:00 and 23:00 KST): fetch the batch results, append the valid
labels to workspace/outputs/llm/news/records.jsonl and write the display digest
(no label, reason or score in it).

Symbols, aliases, masking rules, the label prompt and schema, the message
template and the record fields all come from the pre-registration
docs/claude/llm-news-prereg-v1.json, pinned by sha256. Writes only under
workspace/outputs/llm/, plus one copy of the certifi CA bundle (CA_COPY_NAME
under CA_COPY_DIR) when the bundle path is not ASCII. No existing task reads
these files.

Usage: python manage-us-stock-strategy/scripts/llm_pilot_news.py --phase submit|collect [--day YYYY-MM-DD] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_pilot_common import (  # noqa: E402
    BUDGET_USD_MONTH,
    KEY_ENV,
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

PILOT = "news"
PREREG_REL = "docs/claude/llm-news-prereg-v1.json"
# Both values are copied from the task prompt (docs/claude/llm-news2-builder-prompt.md)
# and from docs/claude/llm-news-prereg-v1.md; never recomputed here.
PREREG_SHA256 = "a8b6f930d7a06ff73f146bfee0236e8f4f6169fbeed7663eacaa4ab43f3262e8"
LABEL_PROMPT_SHA256 = "448d2519a4726f600f83e05c750107aaf290756a9c66a6c23d98d59979351db5"

FRESH_HOURS = 24
REASON_MAX_CHARS = 200
TITLE_MAX_CHARS = 300
SUMMARY_MAX_CHARS = 2000
LOOKBACK_DAYS = 3
ERROR_MESSAGE_MAX_CHARS = 200
ERROR_TYPE_MAX_CHARS = 80

# curl (under curl_cffi) cannot open a CA bundle whose path is not ASCII, so a
# copy of the certifi bundle is kept at this ASCII path for the news fetch.
CA_COPY_DIR = Path("C:/ProgramData/InvestmentV2")
CA_COPY_NAME = "certifi-cacert.pem"
# per-process cache of the news fetch: "bundle" (path or None), "session"
_FETCH_STATE = {}

BATCH_SCHEMA = "llm-news-batch-1"
FETCH_ERRORS_SCHEMA = "llm-news-fetch-errors-1"
RECORDS_SCHEMA = "llm-news-records-1"
COLLECTED_SCHEMA = "llm-news-collected-1"

EXIT_CODES = {
    # same names as llm_pilot_iccheck.EXIT_CODES keep the same values
    "OK": 0,
    "ALREADY_DONE": 0,
    "DRY_RUN": 0,
    "NO_KEY": 4,
    "BUDGET_STOP": 5,
    "API_ERROR": 7,
    # this pilot
    "SUBMITTED": 0,
    "NO_ITEMS": 0,
    "PENDING": 0,
    "NO_BATCH": 0,
    "NOTHING_TO_COLLECT": 0,
    "UNEXPECTED": 1,
    "HALTED": 10,
    "PREREG_MISMATCH": 10,
    "MODEL_MISMATCH": 10,
    "MODEL_NOT_FOUND": 10,
    "RECORDS_BROKEN": 10,
    "FETCH_FAILED": 11,
    "SUBMIT_UNKNOWN": 12,
}

# Korean text is written as \UXXXXXXXX escapes: scripts/*.py must stay ASCII-only
# (test_language_contract, test_v2_5_beginner_renderer). The decoded values are
# pinned verbatim in test_llm_pilot_news.py.
SUMMARY_SYSTEM = (
    "\U0000b274\U0000c2a4 \U0000ae30\U0000c0ac \U0000d558\U0000b098\U0000c758 "
    "\U0000c81c\U0000baa9\U0000acfc \U0000c694\U0000c57d\U0000c774 "
    "\U0000c8fc\U0000c5b4\U0000c9c4\U0000b2e4. "
    "\U0000d22c\U0000c790 \U0000ad8c\U0000c720\U000000b7\U0000b4f1\U0000ae09\U000000b7\U0000c810\U0000c218 "
    "\U0000c5c6\U0000c774 \U0000c0ac\U0000c2e4\U0000b9cc \U0000d55c\U0000ad6d\U0000c5b4 "
    "3\U0000c904\U0000b85c \U0000c4f4\U0000b2e4."
)
DIGEST_TITLE = "# \U0000b274\U0000c2a4 \U0000c694\U0000c57d %s"
DIGEST_FOOTER = (
    "\U0000d45c\U0000c2dc \U0000c804\U0000c6a9: \U0000b9e4\U0000b9e4 "
    "\U0000d310\U0000b2e8\U000000b7\U0000c8fc\U0000bb38\U0000acfc "
    "\U0000c5f0\U0000acb0\U0000d558\U0000c9c0 \U0000c54a\U0000b294\U0000b2e4"
)
REASON_KO = {
    "prereg": "\U0000c0ac\U0000c804 \U0000b4f1\U0000b85d \U0000bd88\U0000c77c\U0000ce58",
    "no_key": "\U0000d0a4 \U0000c5c6\U0000c74c",
    "usage_unreadable": "\U0000c0ac\U0000c6a9 \U0000ae30\U0000b85d\U0000c744 \U0000c77d\U0000c744 \U0000c218 \U0000c5c6\U0000c74c",
    "budget_spent": "\U0000c774\U0000b2ec \U0000c608\U0000c0b0\U0000c744 \U0000b2e4 \U0000c500",
    "fetch_failed": "\U0000ae30\U0000c0ac \U0000ac00\U0000c838\U0000c624\U0000ae30 \U0000c2e4\U0000d328",
    "submit_unknown": "\U0000c81c\U0000cd9c \U0000c5ec\U0000bd80 \U0000baa8\U0000b984",
    "call_failed": "API \U0000d638\U0000cd9c \U0000c2e4\U0000d328 ",
    "bad_shape": "\U0000c751\U0000b2f5 \U0000d615\U0000c2dd \U0000b2e4\U0000b984",
    "model_not_found": "\U0000baa8\U0000b378 \U0000c5c6\U0000c74c",
    "model_mismatch": "\U0000c751\U0000b2f5 \U0000baa8\U0000b378 \U0000b2e4\U0000b984",
    "records_broken": "\U0000ae30\U0000b85d \U0000c0ac\U0000c2ac \U0000ae68\U0000c9d0",
    "unexpected": "\U0000c608\U0000c0c1 \U0000babb \U0000d55c \U0000c624\U0000b958 (%s)",
}

_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_CUSTOM_ID = re.compile(r"([LS])(\d{4,})")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_EDGE_L = r"(?<![A-Za-z0-9])"
_EDGE_R = r"(?![A-Za-z0-9])"
_EXCHANGE = r"(?i:nasdaq|nyse)"
_MASK_CACHE = {}


# ---------------------------------------------------------------- small helpers

def valid_day(text):
    if not isinstance(text, str) or not _DAY_RE.fullmatch(text):
        raise ValueError("day must be YYYY-MM-DD")
    date.fromisoformat(text)
    return text


def news_dir(root) -> Path:
    return llm_dir(root) / PILOT


def day_dir_for(root, day) -> Path:
    return news_dir(root) / day


def halt_path(root) -> Path:
    return news_dir(root) / "HALT"


def records_path(root) -> Path:
    return news_dir(root) / "records.jsonl"


def seen_path(root) -> Path:
    return news_dir(root) / "seen.json"


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha256(value) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(text)


def _dump_line(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _line(day, status, extra="") -> str:
    text = "llm-news %s %s" % (day, status)
    if extra:
        text += " " + extra
    return text[:200]


def _write_halt(root, status, moment) -> None:
    atomic_write_text(halt_path(root), "%s %s\n" % (status, _iso(moment)))


# ---------------------------------------------------------------- pre-registration

def load_prereg(root):
    """Return (prereg, None) or (None, "PREREG_MISMATCH")."""
    path = Path(root) / PREREG_REL
    try:
        prereg = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None, "PREREG_MISMATCH"
    if not isinstance(prereg, dict) or canonical_sha256(prereg) != PREREG_SHA256:
        return None, "PREREG_MISMATCH"
    prompt = prereg.get("label_system_prompt")
    if not isinstance(prompt, str) or _sha256_text(prompt) != LABEL_PROMPT_SHA256:
        return None, "PREREG_MISMATCH"
    model = prereg.get("model")
    if not isinstance(model, dict) or model.get("id") != MODELS[PILOT]:
        return None, "PREREG_MISMATCH"
    return prereg, None


# ---------------------------------------------------------------- masking

def _alias_pattern(alias, case_sensitive):
    body = r"\s+".join(re.escape(word) for word in alias.split())
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(_EDGE_L + body + _EDGE_R, flags)


def _ticker_form_patterns(symbol):
    s = re.escape(symbol)
    return (
        # (NASDAQ: MU) - exchange prefix inside parentheses
        re.compile(r"\(\s*" + _EXCHANGE + r"\s*:\s*" + s + r"\s*\)"),
        # NASDAQ:MU, Nasdaq: MU
        re.compile(_EDGE_L + _EXCHANGE + r"\s*:\s*" + s + _EDGE_R),
        # (MU)
        re.compile(r"\(\s*" + s + r"\s*\)"),
        # $MU
        re.compile(r"\$" + s + _EDGE_R),
        # MU.O
        re.compile(_EDGE_L + s + r"\.O" + _EDGE_R),
    )


def _mask_rules(target, prereg):
    masking = prereg["masking"]
    universe = prereg["universe"]
    aliases = prereg["aliases"]
    key = (target, canonical_sha256({"u": universe, "a": aliases, "m": masking}))
    rules = _MASK_CACHE.get(key)
    if rules is not None:
        return rules
    if target not in universe:
        raise ValueError("target is not in the pre-registered universe")
    tags = {
        sym: (masking["target"] if sym == target else masking["other_universe"]) for sym in universe
    }
    case_sensitive = set(masking["case_sensitive_aliases"])
    built = []
    # 1. ticker forms (case-sensitive symbol; the exchange prefix in any case)
    for sym in universe:
        for pattern in _ticker_form_patterns(sym):
            built.append((pattern, tags[sym]))
    # 2. aliases as whole words, longest first over the whole universe
    pairs = [(alias, sym) for sym in universe for alias in aliases.get(sym, [])]
    pairs.sort(key=lambda pair: -len(pair[0]))
    for alias, sym in pairs:
        built.append((_alias_pattern(alias, alias in case_sensitive), tags[sym]))
    # 3. standalone uppercase symbol of 3 or more letters
    for sym in universe:
        if len(sym) >= 3:
            built.append((re.compile(_EDGE_L + re.escape(sym) + _EDGE_R), tags[sym]))
    rules = tuple(built)
    _MASK_CACHE[key] = rules
    return rules


def mask_item_text(text, target, prereg) -> str:
    """Apply the pre-registered masking rules for target to text."""
    text = _URL.sub("", text)
    for pattern, tag in _mask_rules(target, prereg):
        text = pattern.sub(lambda _match, _tag=tag: _tag, text)
    return text


# ---------------------------------------------------------------- news items

def _write_ca_copy(target, data) -> None:
    """Write data to target atomically: temp file in the same folder, fsync, replace."""
    tmp = target.with_name(target.name + ".tmp")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise


def ascii_ca_bundle(src=None, copy_dir=None):
    """ASCII path of a CA bundle copy, or None to keep the default fetch.

    None when the source path is already ASCII, when certifi is missing, when
    the copy folder path is not ASCII, or on any OSError. The copy is compared
    with the source on every call and rewritten when it differs or is missing.
    """
    if src is None:
        try:
            import certifi  # imported here so tests run without it
        except ImportError:
            return None
        src = certifi.where()
    if str(src).isascii():
        return None
    if copy_dir is None:
        copy_dir = CA_COPY_DIR
    if not str(copy_dir).isascii():
        return None
    folder = Path(copy_dir)
    target = folder / CA_COPY_NAME
    try:
        folder.mkdir(parents=True, exist_ok=True)
        data = Path(src).read_bytes()
        try:
            current = target.read_bytes()
        except FileNotFoundError:
            current = None
        if current != data:
            _write_ca_copy(target, data)
    except OSError:
        return None
    return str(target)


def default_fetcher(symbol):
    import yfinance  # imported here so tests run without it

    if "bundle" not in _FETCH_STATE:
        _FETCH_STATE["bundle"] = ascii_ca_bundle()
    bundle = _FETCH_STATE["bundle"]
    if bundle is None:
        return yfinance.Ticker(symbol).news
    if "session" not in _FETCH_STATE:
        from curl_cffi.requests import Session

        _FETCH_STATE["session"] = Session(impersonate="chrome", verify=bundle)
    return yfinance.Ticker(symbol, session=_FETCH_STATE["session"]).news


def _printable_ascii(text) -> str:
    return "".join(ch if " " <= ch <= "~" else "?" for ch in text)


def _clean_error_message(exc) -> str:
    """str(exc) with addresses hidden, one line, printable ASCII, at most ERROR_MESSAGE_MAX_CHARS."""
    try:
        text = _URL.sub("[url]", str(exc))
        for ch in ("\r", "\n", "\t"):
            text = text.replace(ch, " ")
        return _printable_ascii(text)[:ERROR_MESSAGE_MAX_CHARS]
    except Exception:
        return ""


def _clean_type_name(name) -> str:
    return _printable_ascii(str(name))[:ERROR_TYPE_MAX_CHARS]


def fetch_items_detail(symbol, fetcher=None):
    """(raw news list, None) on success, or (None, error dict) when the fetch failed.

    The error dict keeps why it failed (diagnosis only):
    {"symbol", "kind": "exception" | "not_list", "type", "message"}.
    """
    fetcher = fetcher if fetcher is not None else default_fetcher
    try:
        raw = fetcher(symbol)
    except Exception as exc:
        return None, {
            "symbol": symbol,
            "kind": "exception",
            "type": _clean_type_name(type(exc).__name__),
            "message": _clean_error_message(exc),
        }
    if not isinstance(raw, (list, tuple)):
        return None, {
            "symbol": symbol,
            "kind": "not_list",
            "type": _clean_type_name(type(raw).__name__),
            "message": "",
        }
    return list(raw), None


def fetch_items(symbol, fetcher=None):
    """Raw news list of symbol, or None when the fetch failed."""
    return fetch_items_detail(symbol, fetcher)[0]


def fetch_errors_path(root, day) -> Path:
    return day_dir_for(root, day) / "fetch-errors.json"


def _write_fetch_errors(root, day, stamp, errors, total) -> None:
    """Write the per-symbol fetch errors of this attempt; an OSError never stops the submit."""
    path = fetch_errors_path(root, day)
    doc = {
        "schema": FETCH_ERRORS_SCHEMA,
        "day": day,
        "written_kst": stamp,
        "symbols_failed": len(errors),
        "symbols_total": total,
        "errors": errors,
    }
    try:
        atomic_write_text(path, json.dumps(doc, ensure_ascii=True, sort_keys=True, indent=1) + "\n")
    except OSError:
        try:
            tmp = path.with_name(path.name + ".tmp")
            if tmp.is_file():
                tmp.unlink()
        except OSError:
            pass


def _remove_fetch_errors(root, day) -> None:
    """Remove a fetch-errors.json left by an earlier attempt; an OSError never stops the submit."""
    path = fetch_errors_path(root, day)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _parse_epoch(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _parse_iso(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc)


def _published(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def normalize_item(raw):
    """{"item_id", "title", "summary", "published_at"} or None (skipped)."""
    if not isinstance(raw, dict):
        return None
    content = raw.get("content")
    if isinstance(content, dict):
        item_id = content.get("id")
        title = content.get("title")
        summary = content.get("summary")
        moment = _parse_iso(content.get("pubDate"))
    else:
        item_id = raw.get("uuid")
        title = raw.get("title")
        summary = raw.get("summary")
        moment = _parse_epoch(raw.get("providerPublishTime"))
    if not isinstance(item_id, str) or not item_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    if moment is None:
        return None
    summary = summary.strip() if isinstance(summary, str) else ""
    return {
        "item_id": item_id.strip(),
        "title": title.strip()[:TITLE_MAX_CHARS],
        "summary": summary[:SUMMARY_MAX_CHARS],
        "published_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def read_seen(root):
    path = seen_path(root)
    if not path.exists():
        return {}
    data = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("seen.json is not an object")
    return data


def write_seen(root, seen, new_seen) -> None:
    merged = dict(seen)
    merged.update(new_seen)
    atomic_write_text(seen_path(root), json.dumps(merged, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


# ---------------------------------------------------------------- submit

def run_submit(day, *, repo_root=REPO_ROOT, client_factory=None, fetcher=None, now=None, dry_run=False):
    """Return (exit_code, status, stdout_line)."""
    day = valid_day(day)
    root = Path(repo_root)
    clock = _clock(now)
    started = clock()
    stamp = _iso(started)
    out_dir = day_dir_for(root, day)

    def done(status, extra=""):
        return EXIT_CODES[status], status, _line(day, status, extra)

    def fail(status, reason_ko, extra=""):
        if not dry_run:
            write_failed(out_dir, status, reason_ko)
        return done(status, extra)

    # 1. halt marker
    if halt_path(root).exists():
        return done("HALTED")

    # 2. one submission per day: never send twice
    if (out_dir / "batch.json").exists():
        return done("ALREADY_DONE")
    if (out_dir / "submit-started").exists():
        if dry_run or (out_dir / "failed.md").exists():
            return done("SUBMIT_UNKNOWN")  # keep the first failure reason
        return fail("SUBMIT_UNKNOWN", REASON_KO["submit_unknown"])

    # 3. pre-registration
    prereg, _reason = load_prereg(root)
    if prereg is None:
        if not dry_run:
            _write_halt(root, "PREREG_MISMATCH", started)
        return fail("PREREG_MISMATCH", REASON_KO["prereg"])

    # 4. key (skipped by the dry run); only load_key() reads it and the value
    # goes to the client factory alone
    key = None
    if not dry_run:
        key = load_key()
        if key is None:
            return fail("NO_KEY", REASON_KO["no_key"])

    # 5. month budget before any call; an unreadable usage file stops too
    if not dry_run:
        try:
            spent = month_spend(root, PILOT, started.strftime("%Y-%m"))
        except Exception:
            return fail("BUDGET_STOP", REASON_KO["usage_unreadable"])
        if spent >= BUDGET_USD_MONTH[PILOT]:
            return fail("BUDGET_STOP", REASON_KO["budget_spent"])

    # 6. fetch in pre-registered order
    fetched = []
    symbols_failed = 0
    fetch_errors = []
    for sym in prereg["universe"]:
        raw, error = fetch_items_detail(sym, fetcher)
        if raw is None:
            symbols_failed += 1
            fetch_errors.append(error)
            continue
        fetched.append((sym, raw))
    # diagnosis only: why each symbol failed (latest attempt); never written by the dry run
    if not dry_run:
        if fetch_errors:
            _write_fetch_errors(root, day, stamp, fetch_errors, len(prereg["universe"]))
        else:
            _remove_fetch_errors(root, day)
    if not fetched:
        first = fetch_errors[0] if fetch_errors else None
        reason = REASON_KO["fetch_failed"]
        if first is not None:
            reason += " [" + first["symbol"] + " " + first["type"] + "]"
        return fail("FETCH_FAILED", reason, "symbols_failed=%d" % symbols_failed)

    # 7. pick: first sighting only, published within FRESH_HOURS before now
    seen = read_seen(root)
    new_seen = {}
    picked = []
    skipped = 0
    for sym, raw_items in fetched:
        for raw in raw_items:
            item = normalize_item(raw)
            if item is None:
                skipped += 1
                continue
            item_id = item["item_id"]
            if item_id in seen or item_id in new_seen:
                continue
            new_seen[item_id] = stamp
            age = started - _published(item["published_at"])
            if timedelta(0) <= age <= timedelta(hours=FRESH_HOURS):
                item["symbol"] = sym
                item["first_seen_at"] = stamp
                picked.append(item)

    # mask, then re-check: a second pass must change nothing
    mask_leak = 0
    items = []
    for item in picked:
        sym = item["symbol"]
        masked_title = mask_item_text(item["title"], sym, prereg)
        masked_summary = mask_item_text(item["summary"], sym, prereg)
        if (
            mask_item_text(masked_title, sym, prereg) != masked_title
            or mask_item_text(masked_summary, sym, prereg) != masked_summary
        ):
            mask_leak += 1
            continue
        item["masked_title"] = masked_title
        item["masked_summary"] = masked_summary
        item["n"] = len(items) + 1
        items.append(item)

    # 9. dry run: report and stop; nothing written, no client
    if dry_run:
        return done("DRY_RUN", "items=%d symbols_failed=%d" % (len(items), symbols_failed))

    # 8. nothing to send
    if not items:
        doc = {"schema": BATCH_SCHEMA, "day": day, "status": "NO_ITEMS", "items": []}
        atomic_write_text(out_dir / "batch.json", json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        write_seen(root, seen, new_seen)
        return done("NO_ITEMS", "symbols_failed=%d" % symbols_failed)

    # 10. requests
    requests = build_requests(items, prereg)

    # 11. one create call; the start marker goes first so a crash never re-sends
    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None
    stale_failed = out_dir / "failed.md"
    if stale_failed.exists():
        stale_failed.unlink()
    atomic_write_text(out_dir / "submit-started", stamp + "\n")
    try:
        batch = client.messages.batches.create(requests=requests)
    except Exception as exc:
        if getattr(exc, "status_code", None) == 404:
            _write_halt(root, "MODEL_NOT_FOUND", clock())
            return fail("MODEL_NOT_FOUND", REASON_KO["model_not_found"])
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    batch_id = _attr(batch, "id", None)
    if not isinstance(batch_id, str) or not batch_id:
        return fail("API_ERROR", REASON_KO["bad_shape"])

    # 12. batch file, seen ids, record header
    doc = {
        "schema": BATCH_SCHEMA,
        "day": day,
        "status": "SUBMITTED",
        "batch_id": batch_id,
        "submitted_at": _iso(clock()),
        "prereg_sha256": PREREG_SHA256,
        "counts": {
            "symbols_failed": symbols_failed,
            "skipped": skipped,
            "mask_leak": mask_leak,
            "items": len(items),
        },
        "items": [
            {
                "n": item["n"],
                "symbol": item["symbol"],
                "item_id": item["item_id"],
                "published_at": item["published_at"],
                "first_seen_at": item["first_seen_at"],
                "title": item["title"],
            }
            for item in items
        ],
    }
    atomic_write_text(out_dir / "batch.json", json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    write_seen(root, seen, new_seen)
    ensure_records_header(root, day)

    # 13. result line
    return done(
        "SUBMITTED",
        "items=%d requests=%d symbols_failed=%d" % (len(items), len(requests), symbols_failed),
    )


# ---------------------------------------------------------------- requests

def build_requests(items, prereg):
    model_cfg = prereg["model"]
    template = prereg["user_message_template"]
    requests = []
    for item in items:
        n = item["n"]
        label_text = template.format(title=item["masked_title"], summary=item["masked_summary"])
        summary_text = template.format(title=item["title"], summary=item["summary"])
        requests.append({
            "custom_id": "L%04d" % n,
            "params": {
                "model": MODELS[PILOT],
                "max_tokens": model_cfg["max_tokens"],
                "system": prereg["label_system_prompt"],
                "messages": [{"role": "user", "content": label_text}],
                "output_config": {
                    "format": {"type": "json_schema", "schema": prereg["label_schema"]},
                    "effort": model_cfg["effort"],
                },
            },
        })
        requests.append({
            "custom_id": "S%04d" % n,
            "params": {
                "model": MODELS[PILOT],
                "max_tokens": model_cfg["max_tokens"],
                "system": SUMMARY_SYSTEM,
                "messages": [{"role": "user", "content": summary_text}],
                "output_config": {"effort": model_cfg["effort"]},
            },
        })
    return requests


# ---------------------------------------------------------------- shadow record

def ensure_records_header(root, day) -> None:
    path = records_path(root)
    if path.exists():
        return
    header = {"schema": RECORDS_SCHEMA, "start_day": day, "prereg_sha256": PREREG_SHA256, "prev_sha256": ""}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(_dump_line(header) + "\n")


def read_records(root):
    """(lines, records) when the whole chain checks out, else None."""
    try:
        text = records_path(root).read_bytes().decode("utf-8")
    except (OSError, ValueError):
        return None
    if not text.endswith("\n"):
        return None
    lines = text[:-1].split("\n")
    records = []
    prev = None
    for i, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except ValueError:
            return None
        if not isinstance(obj, dict):
            return None
        if i == 0:
            if (
                obj.get("schema") != RECORDS_SCHEMA
                or obj.get("prereg_sha256") != PREREG_SHA256
                or obj.get("prev_sha256") != ""
                or not isinstance(obj.get("start_day"), str)
            ):
                return None
        else:
            if obj.get("prev_sha256") != _sha256_text(prev):
                return None
            records.append(obj)
        prev = line
    return lines, records


def parse_label(text, prereg):
    """(label, reason) or None."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict) or set(data.keys()) != {"label", "reason"}:
        return None
    allowed = prereg["label_schema"]["properties"]["label"]["enum"]
    if data["label"] not in allowed or not isinstance(data["reason"], str):
        return None
    return data["label"], data["reason"][:REASON_MAX_CHARS]


def _usage_numbers(usage) -> dict:
    out = {}
    for name in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        if isinstance(usage, dict):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)
        out[name] = value if _is_int(value) else 0
    return out


def _is_not_found(result) -> bool:
    error = _attr(result, "error", None)
    kinds = (_attr(error, "type", None), _attr(_attr(error, "error", None), "type", None))
    return any(isinstance(kind, str) and "not_found" in kind for kind in kinds)


def _one_line(text) -> str:
    return " ".join(str(text).split())


def render_digest(day, prereg, items, summaries) -> str:
    lines = [DIGEST_TITLE % day, ""]
    for sym in prereg["universe"]:
        mine = [item for item in items if item["symbol"] == sym]
        if not mine:
            continue
        lines.append("## " + sym)
        lines.append("")
        for item in mine:
            lines.append("- " + _one_line(item["title"]))
            for part in summaries.get(item["n"], "").splitlines():
                if part.strip():
                    lines.append("  " + part.strip())
        lines.append("")
    lines.append(DIGEST_FOOTER)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- collect

def _collect_day(day, root, client_factory, clock):
    """Collect one submitted day. Return (exit_code, status, extra)."""
    out_dir = day_dir_for(root, day)

    def result(status, extra=""):
        return EXIT_CODES[status], status, extra

    def fail(status, reason_ko):
        write_failed(out_dir, status, reason_ko)
        return result(status)

    def halt(status, reason_ko):
        _write_halt(root, status, clock())
        return fail(status, reason_ko)

    # 1. done already
    if (out_dir / "collected.json").exists():
        return result("ALREADY_DONE")

    # 2. batch file
    batch_path = out_dir / "batch.json"
    if not batch_path.exists():
        return result("NO_BATCH")
    batch = json.loads(batch_path.read_bytes().decode("utf-8"))
    if not isinstance(batch, dict):
        raise ValueError("batch.json is not an object")
    if batch.get("status") == "NO_ITEMS":
        return result("NOTHING_TO_COLLECT")
    if batch.get("status") != "SUBMITTED":
        raise ValueError("unknown batch status")

    # 3. pre-registration
    prereg, _reason = load_prereg(root)
    if prereg is None or batch.get("prereg_sha256") != PREREG_SHA256:
        return halt("PREREG_MISMATCH", REASON_KO["prereg"])

    # 4. key
    key = load_key()
    if key is None:
        return fail("NO_KEY", REASON_KO["no_key"])
    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None

    # 5. ended yet?
    batch_id = batch["batch_id"]
    try:
        info = client.messages.batches.retrieve(batch_id)
    except Exception as exc:
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    if _attr(info, "processing_status", None) != "ended":
        return result("PENDING")

    # 6. read every result; received_at is the time the results were read
    try:
        entries = list(client.messages.batches.results(batch_id))
    except Exception as exc:
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    received_at = _iso(clock())

    # 6-1. usage first, once per day; cost summed per message (long-context price is per request)
    usage_done = out_dir / "usage-done"
    if not usage_done.exists():
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        cost = 0.0
        for entry in entries:
            res = _attr(entry, "result", None)
            if _attr(res, "type", None) != "succeeded":
                continue
            numbers = _usage_numbers(_attr(_attr(res, "message", None), "usage", None))
            cost += estimate_cost(MODELS[PILOT], numbers, batch=True)
            for name in totals:
                totals[name] += numbers[name]
        usage_record = dict(totals)
        usage_record.update(
            {
                "ts_kst": received_at,
                "pilot": PILOT,
                "model": MODELS[PILOT],
                "batch": True,
                "cost_usd_est": cost,
                "status": "RECEIVED",
            }
        )
        append_usage(root, usage_record)
        atomic_write_text(usage_done, received_at + "\n")

    # 7. classify results by custom_id
    items = sorted(batch["items"], key=lambda item: item["n"])
    numbers_sent = {item["n"] for item in items}
    labels = {}
    summaries = {}
    answered = set()
    errors = 0
    dropped = 0
    for entry in entries:
        custom_id = _attr(entry, "custom_id", None)
        res = _attr(entry, "result", None)
        kind = _attr(res, "type", None)
        match = _CUSTOM_ID.fullmatch(custom_id) if isinstance(custom_id, str) else None
        known = (
            match is not None
            and int(match.group(2)) in numbers_sent
            and custom_id not in answered
        )
        if known:
            answered.add(custom_id)
        if kind != "succeeded":
            if kind == "errored" and _is_not_found(res):
                return halt("MODEL_NOT_FOUND", REASON_KO["model_not_found"])
            errors += 1
            continue
        message = _attr(res, "message", None)
        problem = check_message(message, MODELS[PILOT])
        if problem == "MODEL_MISMATCH":
            return halt("MODEL_MISMATCH", REASON_KO["model_mismatch"])
        if not known:
            errors += 1
            continue
        if problem:
            dropped += 1
            continue
        n = int(match.group(2))
        text = response_text(message)
        if match.group(1) == "L":
            parsed = parse_label(text, prereg)
            if parsed is None:
                dropped += 1
                continue
            labels[n] = (parsed[0], parsed[1], _attr(message, "model", ""))
        else:
            text = text.strip()
            if not text:
                dropped += 1
                continue
            summaries[n] = text
    errors += 2 * len(items) - len(answered)

    # 8. append to the shadow record after checking the whole chain
    chain = read_records(root)
    if chain is None:
        return halt("RECORDS_BROKEN", REASON_KO["records_broken"])
    lines, existing = chain
    done_keys = {(rec.get("submitted_at"), rec.get("item_id")) for rec in existing}
    fields = prereg["record"]["fields"]
    prev = lines[-1]
    chunk = []
    for item in items:
        n = item["n"]
        if n not in labels or (batch["submitted_at"], item["item_id"]) in done_keys:
            continue
        label, reason, model = labels[n]
        values = {
            "symbol": item["symbol"],
            "item_id": item["item_id"],
            "published_at": item["published_at"],
            "first_seen_at": item["first_seen_at"],
            "submitted_at": batch["submitted_at"],
            "received_at": received_at,
            "label": label,
            "reason": reason,
            "model": model,
            "prev_sha256": _sha256_text(prev),
        }
        line = _dump_line({name: values[name] for name in fields})
        chunk.append(line + "\n")
        prev = line
    if chunk:
        with open(records_path(root), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(chunk))

    # 10. display digest (no label, reason or score)
    atomic_write_text(out_dir / "digest.md", render_digest(day, prereg, items, summaries))

    # 11. collected marker
    collected = {
        "schema": COLLECTED_SCHEMA,
        "day": day,
        "received_at": received_at,
        "labels": len(labels),
        "summaries": len(summaries),
        "errors": errors,
        "dropped": dropped,
    }
    atomic_write_text(out_dir / "collected.json", json.dumps(collected, ensure_ascii=False, indent=1) + "\n")
    failed_path = out_dir / "failed.md"
    if failed_path.exists():
        failed_path.unlink()
    return result(
        "OK",
        "labels=%d summaries=%d errors=%d dropped=%d" % (len(labels), len(summaries), errors, dropped),
    )


def _write_unexpected(out_dir, exc) -> None:
    try:
        write_failed(out_dir, "UNEXPECTED", REASON_KO["unexpected"] % type(exc).__name__)
    except Exception:
        pass


def run_collect(day, *, repo_root=REPO_ROOT, client_factory=None, now=None, dry_run=False):
    """Return (exit_code, status, stdout_line)."""
    day = valid_day(day)
    root = Path(repo_root)
    clock = _clock(now)
    out_dir = day_dir_for(root, day)

    # dry run: local files only, no key, no call, no write
    if dry_run:
        if (out_dir / "collected.json").exists():
            status = "ALREADY_DONE"
        elif not (out_dir / "batch.json").exists():
            status = "NO_BATCH"
        else:
            status = "DRY_RUN"
        return EXIT_CODES[status], status, _line(day, status)

    # 0. late collection of the previous LOOKBACK_DAYS days, oldest first
    late = 0
    base = date.fromisoformat(day)
    for back in range(LOOKBACK_DAYS, 0, -1):
        prior = (base - timedelta(days=back)).isoformat()
        prior_dir = day_dir_for(root, prior)
        if (prior_dir / "collected.json").exists() or not (prior_dir / "batch.json").exists():
            continue
        try:
            _code, prior_status, _extra = _collect_day(prior, root, client_factory, clock)
        except Exception as exc:
            _write_unexpected(prior_dir, exc)
            continue
        if prior_status == "OK":
            late += 1

    code, status, extra = _collect_day(day, root, client_factory, clock)
    extra = (extra + " " if extra else "") + "late=%d" % late
    return code, status, _line(day, status, extra)


# ---------------------------------------------------------------- main

def main(argv=None, *, repo_root=REPO_ROOT, client_factory=None, fetcher=None, now=None) -> int:
    parser = argparse.ArgumentParser(description="llm-news: news digest and shadow labels (display only)")
    parser.add_argument("--phase", required=True, choices=("submit", "collect"))
    parser.add_argument("--day", type=valid_day, default=None, help="KST date YYYY-MM-DD (default: today KST)")
    parser.add_argument("--dry-run", action="store_true", help="count only; no key, no call, no write")
    args = parser.parse_args(argv)
    day = args.day or (now or datetime.now(KST)).astimezone(KST).date().isoformat()
    try:
        if args.phase == "submit":
            code, _status, line = run_submit(
                day, repo_root=repo_root, client_factory=client_factory, fetcher=fetcher,
                now=now, dry_run=args.dry_run,
            )
        else:
            code, _status, line = run_collect(
                day, repo_root=repo_root, client_factory=client_factory, now=now, dry_run=args.dry_run,
            )
    except Exception as exc:
        code = EXIT_CODES["UNEXPECTED"]
        line = _line(day, "UNEXPECTED")
        if not args.dry_run:
            _write_unexpected(day_dir_for(repo_root, day), exc)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
