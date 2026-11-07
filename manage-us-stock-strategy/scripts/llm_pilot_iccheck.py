"""API pilot 1 (llm-iccheck): compare the day's research record with the decision index.

Sends the 06:40 integrated-check research record (amounts and share counts
stripped) and docs/claude/active-decisions.md (amounts masked) to Claude and
keeps only findings whose quotes match the cited lines verbatim.

Display-only shadow: writes only under workspace/outputs/llm/iccheck/<day>/ and
workspace/outputs/llm/usage.jsonl. No existing task reads these files and the
auto-core input is unchanged.

Usage: python manage-us-stock-strategy/scripts/llm_pilot_iccheck.py [--day YYYY-MM-DD] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
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
    mask_text,
    month_spend,
    number_lines,
    quote_ok,
    response_text,
    strip_amounts,
    write_failed,
)

PILOT = "iccheck"
MAX_TOKENS = 16000
MAX_INPUT_TOKENS = 150_000
MAX_FINDINGS = 10

EXIT_CODES = {
    "OK": 0,
    "ALREADY_DONE": 0,
    "DRY_RUN": 0,
    "NO_RECORD": 3,
    "NO_KEY": 4,
    "BUDGET_STOP": 5,
    "TOO_LARGE": 6,
    "API_ERROR": 7,
    "BAD_RESPONSE": 8,
    "BAD_INPUT": 9,
}

# Korean text is written as \UXXXXXXXX escapes: scripts/*.py must stay ASCII-only
# (test_language_contract, test_v2_5_beginner_renderer). The decoded values are
# pinned verbatim against the task prompt in test_llm_pilot_iccheck.py.
SYSTEM_PROMPT = (
    "\U0000b108\U0000b294 \U0000d22c\U0000c790 \U0000c6b4\U0000c601 \U0000ae30\U0000b85d\U0000c758 \U0000b3c5\U0000b9bd \U0000ac80\U0000d1a0\U0000c790\U0000b2e4. \U0000c0ac\U0000c6a9\U0000c790 \U0000ba54\U0000c2dc\U0000c9c0\U0000c5d0 \U0000b450 \U0000c790\U0000b8cc\U0000ac00 \U0000c788\U0000b2e4.\n"
    "- \U0000acb0\U0000c815 \U0000c0c9\U0000c778: \U0000d589\U0000b9c8\U0000b2e4 \"D<\U0000bc88\U0000d638>|\"\U0000ac00 \U0000bd99\U0000c5b4 \U0000c788\U0000b2e4. \U0000c9c0\U0000ae08 \U0000d6a8\U0000b825\U0000c774 \U0000c788\U0000b294 \U0000acb0\U0000c815\U0000acfc \U0000c870\U0000ac74\U000000b7\U0000b9cc\U0000b8cc\U0000ac00 \U0000c801\U0000d600 \U0000c788\U0000b2e4.\n"
    "- \U0000c624\U0000b298 \U0000c5f0\U0000ad6c \U0000ae30\U0000b85d: \U0000d589\U0000b9c8\U0000b2e4 \"R<\U0000bc88\U0000d638>|\"\U0000ac00 \U0000bd99\U0000c5b4 \U0000c788\U0000b2e4. \U0000c544\U0000ce68 \U0000d1b5\U0000d569\U0000c810\U0000ac80\U0000c774 \U0000c4f4 JSON\U0000c774\U0000b2e4. \U0000ae08\U0000c561\U000000b7\U0000c218\U0000b7c9\U0000c740 \U0000c9c0\U0000c6cc\U0000c838 [\U0000ae08\U0000c561]\U000000b7[\U0000c218\U0000b7c9]\U0000c73c\U0000b85c \U0000bcf4\U0000c774\U0000ba70, \U0000c774\U0000ac83\U0000c740 \U0000c624\U0000b958\U0000ac00 \U0000c544\U0000b2c8\U0000b2e4.\n"
    "\n"
    "\U0000d560 \U0000c77c: \U0000c624\U0000b298 \U0000c5f0\U0000ad6c \U0000ae30\U0000b85d\U0000c774 \U0000acb0\U0000c815 \U0000c0c9\U0000c778\U0000c758 \U0000d604\U0000c7ac \U0000acb0\U0000c815\U0000acfc \U0000c5b4\U0000ae0b\U0000b098\U0000b294 \U0000acf3\U0000c744 \U0000cc3e\U0000b294\U0000b2e4. \U0000c608: \U0000d3d0\U0000c9c0\U0000b418\U0000ac70\U0000b098 \U0000b300\U0000ccb4\U0000b41c \U0000ae30\U0000c900\U0000c744 \U0000c544\U0000c9c1 \U0000c4f0\U0000b294 \U0000bb38\U0000c7a5, \U0000acb0\U0000c815\U0000acfc \U0000b2e4\U0000b978 \U0000be44\U0000c728\U000000b7\U0000ae30\U0000d55c\U000000b7\U0000c870\U0000ac74, \U0000b9cc\U0000b8cc\U0000ac00 \U0000c9c0\U0000b09c \U0000acb0\U0000c815\U0000c744 \U0000c0b4\U0000c544 \U0000c788\U0000b294 \U0000ac83\U0000cc98\U0000b7fc \U0000c4f0\U0000b294 \U0000acf3, \U0000b0a0\U0000c9dc\U000000b7\U0000c138\U0000c158\U0000c774 \U0000c11c\U0000b85c \U0000b9de\U0000c9c0 \U0000c54a\U0000b294 \U0000acf3.\n"
    "\n"
    "\U0000addc\U0000ce59:\n"
    "1. \U0000bc1c\U0000acac\U0000b9c8\U0000b2e4 R\U0000d589 \U0000d558\U0000b098\U0000c640 D\U0000d589 \U0000d558\U0000b098\U0000b97c \U0000c778\U0000c6a9\U0000d55c\U0000b2e4. line\U0000c5d0\U0000b294 \U0000d589 \U0000bc88\U0000d638\U0000b9cc \U0000c4f0\U0000ace0, text\U0000c5d0\U0000b294 \U0000adf8 \U0000d589\U0000c758 \U0000ae00\U0000c790\U0000b97c 6\U0000c790 \U0000c774\U0000c0c1 \U0000adf8\U0000b300\U0000b85c \U0000c62e\U0000ae34\U0000b2e4. \U0000ace0\U0000ccd0 \U0000c4f0\U0000ac70\U0000b098 \U0000c904\U0000c774\U0000c9c0 \U0000c54a\U0000b294\U0000b2e4.\n"
    "2. \U0000b450 \U0000c790\U0000b8cc\U0000c5d0 \U0000c801\U0000d78c \U0000ac83\U0000b9cc \U0000adfc\U0000ac70\U0000b85c \U0000d55c\U0000b2e4. \U0000cd94\U0000ce21, \U0000c77c\U0000bc18\U0000b860, \U0000c2dc\U0000c7a5 \U0000c804\U0000b9dd, \U0000b9e4\U0000b9e4 \U0000ad8c\U0000ace0\U0000b294 \U0000c4f0\U0000c9c0 \U0000c54a\U0000b294\U0000b2e4.\n"
    "3. \U0000bc1c\U0000acac\U0000c740 \U0000c911\U0000c694\U0000d55c \U0000ac83\U0000bd80\U0000d130 \U0000cd5c\U0000b300 10\U0000ac1c\U0000b2e4. \U0000c5b4\U0000ae0b\U0000b09c \U0000acf3\U0000c774 \U0000c5c6\U0000c73c\U0000ba74 findings\U0000b97c \U0000be48 \U0000baa9\U0000b85d\U0000c73c\U0000b85c \U0000b0b8\U0000b2e4.\n"
    "4. summary_ko\U0000b294 \U0000d55c\U0000ad6d\U0000c5b4 \U0000d55c\U0000b450 \U0000bb38\U0000c7a5\U0000c73c\U0000b85c, \U0000bb34\U0000c5c7\U0000c774 \U0000c5b4\U0000b5bb\U0000ac8c \U0000b2e4\U0000b978\U0000c9c0 \U0000c4f4\U0000b2e4.\n"
    "5. severity: high = \U0000c624\U0000b298 \U0000c9c0\U0000c2dc\U0000b098 \U0000bcf4\U0000c720 \U0000d310\U0000b2e8\U0000c774 \U0000acb0\U0000c815\U0000acfc \U0000bc18\U0000b300\U0000b85c \U0000c77d\U0000d790 \U0000c218 \U0000c788\U0000c74c, mid = \U0000b0a0\U0000c9dc\U000000b7\U0000b9cc\U0000b8cc\U000000b7\U0000c870\U0000ac74\U000000b7\U0000be44\U0000c728\U0000c774 \U0000c5b4\U0000ae0b\U0000b0a8, low = \U0000d45c\U0000ae30\U000000b7\U0000c124\U0000ba85\U0000b9cc \U0000b2e4\U0000b984.\n"
    "6. checked_lines\U0000c5d0\U0000b294 \U0000c77d\U0000c740 R\U0000d589 \U0000c218\U0000c640 D\U0000d589 \U0000c218\U0000b97c \U0000c801\U0000b294\U0000b2e4."
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings", "checked_lines"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["summary_ko", "record_quote", "decision_quote", "severity"],
                "properties": {
                    "summary_ko": {"type": "string"},
                    "record_quote": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["line", "text"],
                        "properties": {"line": {"type": "integer"}, "text": {"type": "string"}},
                    },
                    "decision_quote": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["line", "text"],
                        "properties": {"line": {"type": "integer"}, "text": {"type": "string"}},
                    },
                    "severity": {"type": "string", "enum": ["high", "mid", "low"]},
                },
            },
        },
        "checked_lines": {
            "type": "object",
            "additionalProperties": False,
            "required": ["record", "decisions"],
            "properties": {"record": {"type": "integer"}, "decisions": {"type": "integer"}},
        },
    },
}

SEVERITIES = ("high", "mid", "low")
SEVERITY_KO = {"high": "\U0000b192\U0000c74c", "mid": "\U0000c911\U0000ac04", "low": "\U0000b0ae\U0000c74c"}

# Korean user-facing strings (unicode escapes; see the note above SYSTEM_PROMPT).
DECISION_HEADER = "\U0000acb0\U0000c815 \U0000c0c9\U0000c778(D\U0000d589)\n"
RECORD_HEADER = "\U0000c624\U0000b298 \U0000c5f0\U0000ad6c \U0000ae30\U0000b85d(R\U0000d589, \U0000ae08\U0000c561\U000000b7\U0000c218\U0000b7c9 \U0000c9c0\U0000c6c0)\n"
ALERT_TITLE = "# \U0000ae30\U0000b85d \U0000b300\U0000c870 \U0000ac80\U0000d1a0 %s \U00002014 \U0000acb0\U0000c815 \U0000c0c9\U0000c778\U0000acfc \U0000c5b4\U0000ae0b\U0000b09c \U0000acf3 %d\U0000ac74"
ALERT_ITEM = "- %s \U000000b7 %s \U000000b7 R%d \"%s\" \U000000b7 D%d \"%s\""
ALERT_FOOTER = "\U0000d45c\U0000c2dc \U0000c804\U0000c6a9: \U0000cf54\U0000c5b4 \U0000c785\U0000b825\U000000b7\U0000b9e4\U0000b9e4 \U0000adfc\U0000ac70\U0000ac00 \U0000c544\U0000b2d8."
REASON_KO = {
    "no_record": "\U0000c624\U0000b298 \U0000c5f0\U0000ad6c \U0000ae30\U0000b85d \U0000c5c6\U0000c74c",
    "bad_record": "\U0000c5f0\U0000ad6c \U0000ae30\U0000b85d\U0000c744 \U0000c77d\U0000c744 \U0000c218 \U0000c5c6\U0000c74c",
    "no_decisions": "\U0000acb0\U0000c815 \U0000c0c9\U0000c778 \U0000c5c6\U0000c74c",
    "bad_decisions": "\U0000acb0\U0000c815 \U0000c0c9\U0000c778\U0000c744 \U0000c77d\U0000c744 \U0000c218 \U0000c5c6\U0000c74c",
    "no_key": "\U0000d0a4 \U0000c5c6\U0000c74c",
    "usage_unreadable": "\U0000c0ac\U0000c6a9 \U0000ae30\U0000b85d\U0000c744 \U0000c77d\U0000c744 \U0000c218 \U0000c5c6\U0000c74c",
    "budget_spent": "\U0000c774\U0000b2ec \U0000c608\U0000c0b0\U0000c744 \U0000b2e4 \U0000c500",
    "count_failed": "\U0000d1a0\U0000d070 \U0000c138\U0000ae30 \U0000c2e4\U0000d328 ",
    "count_shape": "\U0000d1a0\U0000d070 \U0000c218 \U0000c751\U0000b2f5 \U0000d615\U0000c2dd \U0000b2e4\U0000b984",
    "too_large": "\U0000c785\U0000b825\U0000c774 \U0000b108\U0000bb34 \U0000d07c",
    "budget_worst": "\U0000c608\U0000c0c1 \U0000cd5c\U0000b300 \U0000be44\U0000c6a9\U0000c774 \U0000c774\U0000b2ec \U0000c608\U0000c0b0\U0000c744 \U0000b118\U0000c74c",
    "call_failed": "API \U0000d638\U0000cd9c \U0000c2e4\U0000d328 ",
    "bad_message": "\U0000c751\U0000b2f5 \U0000c774\U0000c0c1 ",
    "bad_shape": "\U0000c751\U0000b2f5 \U0000d615\U0000c2dd \U0000b2e4\U0000b984",
    "unexpected": "\U0000c608\U0000c0c1 \U0000babb \U0000d55c \U0000c624\U0000b958 (%s)",
}
_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


# ---------------------------------------------------------------- helpers

def valid_day(text):
    if not isinstance(text, str) or not _DAY_RE.fullmatch(text):
        raise ValueError("day must be YYYY-MM-DD")
    date.fromisoformat(text)
    return text


def day_dir_for(root, day) -> Path:
    return llm_dir(root) / PILOT / day


def record_path_for(root, day) -> Path:
    return Path(root) / "workspace" / "outputs" / "research-records" / day / "research-record.json"


def decisions_path_for(root) -> Path:
    return Path(root) / "docs" / "claude" / "active-decisions.md"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_request(decision_text: str, record_text: str) -> dict:
    return {
        "model": MODELS[PILOT],
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DECISION_HEADER + number_lines(decision_text, "D")},
                    {
                        "type": "text",
                        "text": RECORD_HEADER + number_lines(record_text, "R"),
                    },
                ],
            }
        ],
        "output_config": {
            "format": {"type": "json_schema", "schema": SCHEMA},
            "effort": "medium",
        },
    }


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _quote_valid(q) -> bool:
    return (
        isinstance(q, dict)
        and set(q.keys()) == {"line", "text"}
        and _is_int(q["line"])
        and isinstance(q["text"], str)
    )


def parse_response(text):
    """Return (findings, checked_lines) or None when the shape is wrong."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict) or set(data.keys()) != {"findings", "checked_lines"}:
        return None
    findings = data["findings"]
    checked = data["checked_lines"]
    if not isinstance(findings, list):
        return None
    for f in findings:
        if not isinstance(f, dict) or set(f.keys()) != {
            "summary_ko",
            "record_quote",
            "decision_quote",
            "severity",
        }:
            return None
        if not isinstance(f["summary_ko"], str) or f["severity"] not in SEVERITIES:
            return None
        if not _quote_valid(f["record_quote"]) or not _quote_valid(f["decision_quote"]):
            return None
    if (
        not isinstance(checked, dict)
        or set(checked.keys()) != {"record", "decisions"}
        or not _is_int(checked["record"])
        or not _is_int(checked["decisions"])
    ):
        return None
    return findings, checked


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


def _render_alert(day, findings) -> str:
    lines = [ALERT_TITLE % (day, len(findings)), ""]
    for f in findings:
        lines.append(
            ALERT_ITEM
            % (
                SEVERITY_KO[f["severity"]],
                f["summary_ko"],
                f["record_quote"]["line"],
                f["record_quote"]["text"],
                f["decision_quote"]["line"],
                f["decision_quote"]["text"],
            )
        )
    lines.append("")
    lines.append(ALERT_FOOTER)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- run

def _fail(day_dir, status, reason_ko):
    write_failed(day_dir, status, reason_ko)
    return EXIT_CODES[status], status, 0, 0


def run_detail(day, *, repo_root=REPO_ROOT, client_factory=None, dry_run=False, now=None):
    """Return (exit_code, status, findings_kept, findings_dropped)."""
    day = valid_day(day)
    root = Path(repo_root)
    now = (now or datetime.now(KST)).astimezone(KST)
    out_dir = day_dir_for(root, day)
    review_path = out_dir / "review.json"

    # 1. already done
    if review_path.exists():
        kept = dropped = 0
        try:
            prev = json.loads(review_path.read_text(encoding="utf-8"))
            kept = len(prev.get("findings") or [])
            dropped = int(prev.get("dropped_findings") or 0)
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return 0, "ALREADY_DONE", kept, dropped

    # 2. research record
    rec_path = record_path_for(root, day)
    if not rec_path.exists():
        return _fail(out_dir, "NO_RECORD", REASON_KO["no_record"])
    try:
        record = json.loads(rec_path.read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        return _fail(out_dir, "BAD_INPUT", REASON_KO["bad_record"])

    # 3. decision index
    dec_path = decisions_path_for(root)
    if not dec_path.exists():
        return _fail(out_dir, "BAD_INPUT", REASON_KO["no_decisions"])
    try:
        dec_bytes = dec_path.read_bytes()
        dec_raw = dec_bytes.decode("utf-8-sig")
    except (OSError, ValueError):
        return _fail(out_dir, "BAD_INPUT", REASON_KO["bad_decisions"])

    # 4. inputs
    clean, removed = strip_amounts(record)
    record_text = json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True)
    record_lines = record_text.splitlines()
    decision_text, masked = mask_text(dec_raw)
    decision_lines = decision_text.splitlines()
    record_sha = _sha256_text(record_text)
    decisions_sha = hashlib.sha256(dec_bytes).hexdigest()

    # 5. request
    request = build_request(decision_text, record_text)

    # 6. dry run
    if dry_run:
        preview = {
            "model": request["model"],
            "max_tokens": request["max_tokens"],
            "output_config": request["output_config"],
            "system_sha256": _sha256_text(SYSTEM_PROMPT),
            "record_lines": len(record_lines),
            "decision_lines": len(decision_lines),
            "record_sha256": record_sha,
            "decisions_sha256": decisions_sha,
            "removed_amount_items": removed,
            "masked_decision_items": masked,
        }
        atomic_write_text(
            out_dir / "request-preview.json",
            json.dumps(preview, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        )
        return 0, "DRY_RUN", 0, 0

    # 7. key
    key = load_key()
    if key is None:
        return _fail(out_dir, "NO_KEY", REASON_KO["no_key"])

    # 8. budget before the call
    budget = BUDGET_USD_MONTH[PILOT]
    month = now.strftime("%Y-%m")
    try:
        spent = month_spend(root, PILOT, month)
    except Exception:
        return _fail(out_dir, "BUDGET_STOP", REASON_KO["usage_unreadable"])
    if spent >= budget:
        return _fail(out_dir, "BUDGET_STOP", REASON_KO["budget_spent"])

    # 9. client, token count, worst-case cost
    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None
    try:
        counted = client.messages.count_tokens(
            model=request["model"],
            system=request["system"],
            messages=request["messages"],
            output_config=request["output_config"],
        )
    except Exception as exc:
        return _fail(out_dir, "API_ERROR", REASON_KO["count_failed"] + api_error_label(exc))
    input_tokens = counted.get("input_tokens") if isinstance(counted, dict) else getattr(
        counted, "input_tokens", None
    )
    if not _is_int(input_tokens):
        return _fail(out_dir, "BAD_RESPONSE", REASON_KO["count_shape"])
    if input_tokens > MAX_INPUT_TOKENS:
        return _fail(out_dir, "TOO_LARGE", REASON_KO["too_large"])
    worst = spent + estimate_cost(
        request["model"], {"input_tokens": input_tokens, "output_tokens": MAX_TOKENS}
    )
    if worst > budget:
        return _fail(out_dir, "BUDGET_STOP", REASON_KO["budget_worst"])

    # 10. call
    try:
        with client.messages.stream(
            model=request["model"],
            max_tokens=request["max_tokens"],
            system=request["system"],
            messages=request["messages"],
            output_config=request["output_config"],
        ) as stream:
            message = stream.get_final_message()
    except Exception as exc:
        return _fail(out_dir, "API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))

    # 11. usage (always once a response arrived)
    usage = _usage_numbers(getattr(message, "usage", None))
    cost = estimate_cost(request["model"], usage, batch=False)
    problem = check_message(message, request["model"])
    resp_model = getattr(message, "model", None)
    resp_model = resp_model if isinstance(resp_model, str) else ""
    usage_record = dict(usage)
    usage_record.update(
        {
            "ts_kst": now.isoformat(timespec="seconds"),
            "pilot": PILOT,
            "model": resp_model,
            "batch": False,
            "cost_usd_est": cost,
            "status": problem or "RECEIVED",
        }
    )
    append_usage(root, usage_record)

    # 12. response checks
    if problem:
        return _fail(out_dir, "BAD_RESPONSE", REASON_KO["bad_message"] + problem)
    parsed = parse_response(response_text(message))
    if parsed is None:
        return _fail(out_dir, "BAD_RESPONSE", REASON_KO["bad_shape"])
    findings, checked = parsed

    # 13. keep only verbatim-quoted findings
    dropped = max(0, len(findings) - MAX_FINDINGS)
    kept = []
    for f in findings[:MAX_FINDINGS]:
        if quote_ok(record_lines, f["record_quote"]["line"], f["record_quote"]["text"]) and quote_ok(
            decision_lines, f["decision_quote"]["line"], f["decision_quote"]["text"]
        ):
            kept.append(f)
        else:
            dropped += 1

    # 14. outputs
    alert_path = out_dir / "alert.md"
    if kept:
        atomic_write_text(alert_path, _render_alert(day, kept))
    elif alert_path.exists():
        alert_path.unlink()
    review = {
        "schema": "llm-iccheck-review-1",
        "day": day,
        "generated_at_kst": now.isoformat(timespec="seconds"),
        "model": resp_model,
        "input_sha256": {"record": record_sha, "decisions": decisions_sha},
        "removed_amount_items": removed,
        "masked_decision_items": masked,
        "findings": kept,
        "dropped_findings": dropped,
        "checked_lines": checked,
        "usage": usage,
        "cost_usd_est": cost,
        "display": "none",
    }
    atomic_write_text(review_path, json.dumps(review, ensure_ascii=False, indent=1) + "\n")
    failed_path = out_dir / "failed.md"
    if failed_path.exists():
        failed_path.unlink()
    return 0, "OK", len(kept), dropped


def run(day, *, repo_root=REPO_ROOT, client_factory=None, dry_run=False, now=None):
    code, status, _kept, _dropped = run_detail(
        day, repo_root=repo_root, client_factory=client_factory, dry_run=dry_run, now=now
    )
    return code, status


# ---------------------------------------------------------------- main

def main(argv=None, *, repo_root=REPO_ROOT, client_factory=None, now=None) -> int:
    parser = argparse.ArgumentParser(description="llm-iccheck: research record vs decision index (display only)")
    parser.add_argument("--day", type=valid_day, default=None, help="KST date YYYY-MM-DD (default: today KST)")
    parser.add_argument("--dry-run", action="store_true", help="write request-preview.json only, no key, no call")
    args = parser.parse_args(argv)
    day = args.day or (now or datetime.now(KST)).astimezone(KST).date().isoformat()
    try:
        code, status, kept, dropped = run_detail(
            day, repo_root=repo_root, client_factory=client_factory, dry_run=args.dry_run, now=now
        )
    except Exception as exc:
        code, status, kept, dropped = 1, "UNEXPECTED", 0, 0
        try:
            write_failed(day_dir_for(repo_root, day), status, REASON_KO["unexpected"] % type(exc).__name__)
        except Exception:
            pass
    print("llm-iccheck %s %s findings=%d dropped=%d" % (day, status, kept, dropped))
    return code


if __name__ == "__main__":
    sys.exit(main())
