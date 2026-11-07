"""Shared helpers for the Claude API pilots (llm-iccheck and later pilots).

Display-only shadow tooling: nothing here writes outside workspace/outputs/llm/,
and no existing task reads its output. The API key is read only from the
INVESTV2_ANTHROPIC_API_KEY environment variable and is never printed, written
or put into an exception message.
"""

from __future__ import annotations

import copy
import json
import os
import re
from datetime import timedelta, timezone
from pathlib import Path

KEY_ENV = "INVESTV2_ANTHROPIC_API_KEY"

MODELS = {
    "iccheck": "claude-sonnet-5-5",
    "news": "claude-haiku-5-5",
    "pdfcmp": "claude-haiku-5-5",
    "srccheck": "claude-sonnet-5-5",
}

BUDGET_USD_MONTH = {"iccheck": 10, "news": 5, "pdfcmp": 5, "srccheck": 6}

# USD per million tokens: (input, output).
PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
HAIKU_LONG_PRICE = (0.50, 2.50)
HAIKU_LONG_THRESHOLD = 100_000
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = {
    "claude-sonnet-5-5": 0.1,
    "claude-haiku-5-5": 0.1,
    "claude-opus-5-5": 0.05,
}
BATCH_MULT = 0.5

KST = timezone(timedelta(hours=9))
REPO_ROOT = Path(__file__).resolve().parents[2]

OFFICIAL_BASE_URL = "https://api.anthropic.com"
SDK_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_CUSTOM_HEADERS",
    "ANTHROPIC_PROFILE",
)

USAGE_KEYS = (
    "ts_kst",
    "pilot",
    "model",
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "batch",
    "cost_usd_est",
    "status",
)


# ---------------------------------------------------------------- paths

def llm_dir(root) -> Path:
    return Path(root) / "workspace" / "outputs" / "llm"


def usage_path(root) -> Path:
    return llm_dir(root) / "usage.jsonl"


# ---------------------------------------------------------------- key / client

def load_key():
    value = os.environ.get(KEY_ENV)
    if value is None:
        return None
    value = value.strip()
    return value or None


def make_client(key, timeout=120.0):
    for name in SDK_ENV_VARS:
        if name in os.environ:
            del os.environ[name]
    import anthropic  # imported here so tests run without the SDK

    return anthropic.Anthropic(
        api_key=key,
        base_url=OFFICIAL_BASE_URL,
        max_retries=1,
        timeout=timeout,
    )


def api_error_label(exc) -> str:
    label = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        label += " HTTP %d" % status
    return label


# ---------------------------------------------------------------- amount stripping

ACCOUNT_KEEP = (
    "vsHwmPct",
    "firstCushionPct",
    "approachPct",
    "maxPct",
    "n",
    "reconcile",
    "exposure",
    "holdings",
)
HOLDING_KEEP = ("code", "weight", "mult")
AMOUNT_KEYS = frozenset(
    {
        "qty",
        "quantity",
        "shares",
        "value",
        "marketvalue",
        "cash",
        "amount",
        "total",
        "totalassets",
        "kiwoomtotal",
        "kiwoomdiff",
        "hwm",
        "price",
        "avgcost",
        "cost",
        "pnl",
        "lines",
    }
)

# Korean text is written as \uXXXX escapes: scripts/*.py must stay ASCII-only
# (test_language_contract). In raw regex patterns the re module decodes \uXXXX;
# replacement templates are plain strings. Decoded values are pinned in
# test_llm_pilot_common.py.
AMOUNT_TAG = "[\uae08\uc561]"
COUNT_TAG = "[\uc218\ub7c9]"

MASK_RULES = (
    # \$ amount
    (re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?"), AMOUNT_TAG),
    # N dollar / N USD
    (re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:\ub2ec\ub7ec|USD)"), AMOUNT_TAG),
    # N shares (Korean counter "ju" or English)
    (re.compile(r"\d[\d,]*\s?(?:\uc8fc|shares?)"), COUNT_TAG),
    # ticker followed by a bare integer
    (re.compile(r"\b([A-Z]{2,5})\s(\d[\d,]*)(?![\d:/%.])"), "\\1 " + COUNT_TAG),
    # old value / holding / quantity / balance followed by a bare integer
    (
        re.compile(r"(\uc61b \uac12|\ubcf4\uc720|\uc218\ub7c9|\uc794\uace0)\s?(\d[\d,]*)(?![\d:/%.])"),
        "\\1 " + COUNT_TAG,
    ),
)


def mask_text(text):
    """Mask money and share counts in free text. Returns (masked, n)."""
    total = 0
    for pattern, repl in MASK_RULES:
        text, n = pattern.subn(repl, text)
        total += n
    return text, total


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric_only(value) -> bool:
    if _is_number(value):
        return True
    if isinstance(value, dict):
        return all(_numeric_only(v) for v in value.values())
    if isinstance(value, list):
        return all(_numeric_only(v) for v in value)
    return False


def _norm_key(key) -> str:
    return str(key).lower().replace("_", "")


def _is_amount_key(key) -> bool:
    norm = _norm_key(key)
    return norm in AMOUNT_KEYS or norm.endswith("usd")


def _reconcile_word(text: str) -> str:
    head = text.split(":", 1)[0].strip()
    parts = head.split()
    return parts[0] if parts else ""


def _clean(obj, key, parent_key, counter):
    if isinstance(obj, dict):
        items = list(obj.items())
        if key == "account":
            kept = [(k, v) for k, v in items if k in ACCOUNT_KEEP]
            counter[0] += len(items) - len(kept)
            items = kept
        elif key == "holdings" and parent_key == "account":
            kept = [(k, v) for k, v in items if k in HOLDING_KEEP]
            counter[0] += len(items) - len(kept)
            items = kept
        out = {}
        for k, v in items:
            if _is_amount_key(k) and _numeric_only(v):
                counter[0] += 1
                continue
            if k == "reconcile" and isinstance(v, str):
                word = _reconcile_word(v)
                if word != v:
                    counter[0] += 1
                v = word
            new_key = k
            if isinstance(k, str):
                new_key, n = mask_text(k)
                counter[0] += n
                base, i = new_key, 2
                while new_key in out:
                    new_key = "%s~%d" % (base, i)
                    i += 1
            out[new_key] = _clean(v, k, key, counter)
        return out
    if isinstance(obj, list):
        # list items inherit the key of the list (holdings items stay "holdings")
        return [_clean(v, key, parent_key, counter) for v in obj]
    if isinstance(obj, str):
        masked, n = mask_text(obj)
        counter[0] += n
        return masked
    return obj


def strip_amounts(obj):
    """Deep-copy obj with money and share counts removed. Returns (clean, removed)."""
    counter = [0]
    clean = _clean(copy.deepcopy(obj), None, None, counter)
    return clean, counter[0]


# ---------------------------------------------------------------- lines / quotes

_QUOTE_PREFIX = re.compile(r"^\s*[A-Z]\d+\|")
_SPACES = re.compile(r"\s+")


def number_lines(text, prefix):
    return "\n".join(
        "%s%d|%s" % (prefix, i, line) for i, line in enumerate(text.splitlines(), 1)
    )


def _norm_space(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


def quote_ok(lines, line_no, quote) -> bool:
    if not isinstance(line_no, int) or isinstance(line_no, bool):
        return False
    if not isinstance(quote, str):
        return False
    q = _norm_space(_QUOTE_PREFIX.sub("", quote, count=1))
    if len(q) < 6:
        return False
    if not 1 <= line_no <= len(lines):
        return False
    return q in _norm_space(lines[line_no - 1])


# ---------------------------------------------------------------- usage / budget

def _get(obj, name, default=0):
    if isinstance(obj, dict):
        value = obj.get(name, default)
    else:
        value = getattr(obj, name, default)
    return default if value is None else value


def _base_model(model: str) -> str:
    return re.sub(r"-\d{8}$", "", model)


def estimate_cost(model, usage, batch=False) -> float:
    base = _base_model(str(model))
    if base not in PRICES:
        raise ValueError("unknown model for pricing")
    inp = int(_get(usage, "input_tokens"))
    out = int(_get(usage, "output_tokens"))
    cw = int(_get(usage, "cache_creation_input_tokens"))
    cr = int(_get(usage, "cache_read_input_tokens"))
    in_price, out_price = PRICES[base]
    if base == "claude-haiku-5-5" and inp + cw + cr > HAIKU_LONG_THRESHOLD:
        in_price, out_price = HAIKU_LONG_PRICE
    cost = (
        inp * in_price
        + cw * in_price * CACHE_WRITE_MULT
        + cr * in_price * CACHE_READ_MULT[base]
        + out * out_price
    ) / 1_000_000
    if batch:
        cost *= BATCH_MULT
    return cost


def append_usage(root, record) -> None:
    path = usage_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({k: record.get(k) for k in USAGE_KEYS}, ensure_ascii=False)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def month_spend(root, pilot, month) -> float:
    """Sum cost_usd_est for pilot in month (YYYY-MM). Raises on any unreadable line."""
    path = usage_path(root)
    if not path.exists():
        return 0.0
    total = 0.0
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            if raw.strip() == "":
                continue
            rec = json.loads(raw)
            if not isinstance(rec, dict):
                raise ValueError("usage line is not an object")
            cost = rec.get("cost_usd_est")
            if not _is_number(cost):
                raise ValueError("usage line has no numeric cost")
            ts = rec.get("ts_kst")
            if not isinstance(ts, str):
                raise ValueError("usage line has no ts_kst")
            if rec.get("pilot") == pilot and ts[:7] == month:
                total += float(cost)
    return total


# ---------------------------------------------------------------- files

def atomic_write_text(path, text) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


FAILED_LINE = "\U0000ac80\U0000d1a0 \U0000babb \U0000d568: %s (%s)\n"


def write_failed(day_dir, code, reason_ko) -> None:
    atomic_write_text(Path(day_dir) / "failed.md", FAILED_LINE % (reason_ko, code))


# ---------------------------------------------------------------- responses

def response_text(message) -> str:
    parts = []
    for block in _get(message, "content", []) or []:
        if _get(block, "type", None) == "text":
            parts.append(str(_get(block, "text", "")))
    return "".join(parts)


def check_message(message, expected_model):
    model = _get(message, "model", "")
    if not isinstance(model, str) or not re.fullmatch(
        re.escape(expected_model) + r"(?:-\d{8})?", model
    ):
        return "MODEL_MISMATCH"
    stop = _get(message, "stop_reason", None)
    if stop == "refusal":
        return "REFUSAL"
    if stop == "max_tokens":
        return "MAX_TOKENS"
    if stop != "end_turn":
        return "BAD_STOP"
    return None
