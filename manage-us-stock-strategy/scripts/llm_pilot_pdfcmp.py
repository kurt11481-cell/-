"""API pilot 3 (llm-pdfcmp): one-time comparison of a first-pass PDF classification.

Ten external PDFs that the external claims ledger already processed are uploaded
with the Files API and classified once by a Message Batch (document citations
on). The answers are compared with the ledger result (the answer table PDFS)
exactly once.

Submit phase (13:10 KST): check the ten PDFs in the read-only PDF folder (missing,
sha256 mismatch or too large -> skipped). Fewer than MIN_USED usable -> HOLD with
no call and no batch.json. Otherwise check the month budget, upload, create one
batch and write batch.json.

Collect phase (15:10 / 17:10 KST): when the batch has ended, read the results,
append usage lines, write compare.json and compare.md, then delete the uploaded
files.

Display only: the ledger, the integrated check and the core never read these
files. Writes only under workspace/outputs/llm/. The PDF folder is only read.
The original PDF file names are never sent to the API.

Usage: python manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py --phase submit|collect
       [--day YYYY-MM-DD] [--pdf-dir PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import date, datetime
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

PILOT = "pdfcmp"
MAX_TOKENS = 4096
EST_INPUT_TOKENS_PER_PDF = 60_000
EST_OUTPUT_TOKENS_PER_PDF = 4_096
MAX_PDF_BYTES = 32_000_000
MIN_USED = 8
PASS_CLASS = 8
PASS_TOPIC = 8
QUOTE_MIN_CHARS = 6
EVIDENCE_MD_CHARS = 60
EVIDENCE_JSON_CHARS = 300
TARGET_JSON_CHARS = 300

BATCH_SCHEMA = "llm-pdfcmp-batch-1"
COMPARE_SCHEMA = "llm-pdfcmp-compare-1"

EXIT_CODES = {
    # same names as llm_pilot_news.EXIT_CODES keep the same values
    "SUBMITTED": 0,
    "PENDING": 0,
    "NO_BATCH": 0,
    "DRY_RUN": 0,
    "UNEXPECTED": 1,
    "NO_KEY": 4,
    "BUDGET_STOP": 5,
    "API_ERROR": 7,
    # this pilot
    "WAITING": 0,
    "PASS": 0,
    "FAIL": 0,
    "HOLD": 0,
    "DONE_ALREADY": 0,
}

# Korean text is written as \uXXXX escapes: scripts/*.py must stay ASCII-only
# (test_language_contract, test_v2_5_beginner_renderer). Decoded values are
# pinned in test_llm_pilot_pdfcmp.py.

# Ledger raw-material folder: docs/claude/external-claims-ledger.md line 17. Read only.
DEFAULT_PDF_DIR = "E:\\\uc0ac\uc5c5\\##\uae08\ub3d9\ud55c\\chatgpt_\uc885\ubaa9\ubd84\uc11d\uacb0\uacfc\\\uc678\ubd80\uc790\ub8cc"

# common file name tail " - <stock> - <site>.pdf"
_FM = " - \uc8fc\uc2dd - \uc5d0\ud3a8\ucf54\ub9ac\uc544.pdf"

# Answer table: docs/claude/llm-pdfcmp-builder-prompt.md (from
# docs/claude/pdfcmp-pdf-selection-2026-11-25.md). Row = (pid, file name,
# sha256, answer CAND|R0, topic words). A topic word matches when it appears in
# the model's target line (case and whitespace ignored).
PDFS = (
    (
        "P01",
        "\ub9c8\uc774\ud06c\ub860 $MU ___30\ub144 \ub9d0\uae4c\uc9c0 \ud53c\uc9c0\uceecAI\uac00 "
        "\uba54\ubaa8\ub9ac\uc640 \uc2a4\ud1a0\ub9ac\uc9c0 \uc218\uc694\uc758 \uc911\uc694\ud55c "
        "\ub3d9\uc778\uc774 \ub420 \uc218 \uc788\ub2e4._" + _FM,
        "300bca2e1b23896e8dba18e2178ead47654307ca8d3071429afd0183c93a4402",
        "CAND",
        ("MU", "\ub9c8\uc774\ud06c\ub860", "\uba54\ubaa8\ub9ac"),
    ),
    (
        "P02",
        "28\ub144 \uba54\ubaa8\ub9ac Q \uc0ac\uc774\ud074\uc5d0 \ub300\ud55c \uc77c\ubc18\uc801\uc778 "
        "\uc778\uc2dd\uc774" + _FM,
        "8fdeb7c97f07236b2c804d0663fa41bad8cdfee0861c8bce07fe3c53d65553e3",
        "CAND",
        ("MU", "\ub9c8\uc774\ud06c\ub860", "\uba54\ubaa8\ub9ac"),
    ),
    (
        "P03",
        "_\ub808\ud3ec\ud2b8_ \uc0cc\ub514\uc2a4\ud06c SNDK __ \ud4e8\uc5b4 \ub0b8\ub4dc "
        "\ud50c\ub808\uc774\uc5b4" + _FM,
        "960abfa0ba0d8924d06d38cad6a618595ec6002a96ece77c518c96043ab0a2a0",
        "CAND",
        ("SNDK", "\uc0cc\ub514\uc2a4\ud06c", "\ub0b8\ub4dc", "NAND"),
    ),
    (
        "P04",
        "\ub2e8\ub3c5_ \uc5f0\uc900, \uc778\ud50c\ub808\uc774\uc158 \uc804\ub9dd \uc704\ud574 "
        "AI\u00b7\uad00\uc138\u00b7\uc5d0\ub108\uc9c0 \uc8fc\uc2dc" + _FM,
        "30a3002b62fb72bc7ef7576ac7beafacb467ed65004308081f0b142cced3c3ec",
        "CAND",
        ("\uc5f0\uc900", "Fed", "\uc778\ud50c\ub808\uc774\uc158", "\uae08\ub9ac"),
    ),
    (
        "P05",
        "\uc5f0\ud734\uae30\uac04\uc5d0\ub294 \uae00 \uc548\uc4f8\ub824\uace0 \ud588\ub294\ub370 "
        "\uc2ec\uc2ec\ud574\uc11c \uc4f0\ub294\uac70 \uc808\ub300\ub8e8 \uc544\ub2c8\uac70\ub4f1_ "
        "\ud765!" + _FM,
        "a67c86fd8a640fc799f2bac0cebaa968dd660aab4327dd0f0417389d395bfe02",
        "CAND",
        ("AMD", "INTC", "\uc778\ud154", "CPU"),
    ),
    (
        "P06",
        "\ucd94\uc138\ucd94\uc885 \ud2b8\ub808\uc774\ub529 _ \uadf8\ub798\uc11c \ub9e4\uc218\uc640 "
        "\ub9e4\ub3c4\ub294 \uc5b8\uc81c \ud574\uc694_" + _FM,
        "83a04de9ed3f51266601be05b2550baaec3f9cfaa3848ef1fe83ce28957a1bd1",
        "R0",
        ("\ucd94\uc138\ucd94\uc885", "\ub9e4\ub9e4", "\uc190\uc808", "\ub3cc\ud30c"),
    ),
    (
        "P07",
        "bbs_1790030156281.pdf",
        "f47cd947c308a93d1e19ee02e06fef2fdfdf76cc11d7b571f94bde7077480210",
        "R0",
        ("PER", "\ubc38\ub958\uc5d0\uc774\uc158", "S&P"),
    ),
    (
        "P08",
        "bbs_1791326873246.pdf",
        "35141529a39e283a51b323bdbb7f233ef5c3211bf37a1c057a12a0102215d28b",
        "R0",
        ("PER", "\ub9c8\uc9c4", "\ubc38\ub958\uc5d0\uc774\uc158"),
    ),
    (
        "P09",
        "10\uc6d4, \ub784\ubd80 \ub5a8\ub9ac\ub294 \uc870\uc815 \uc624\ub824\ub098_ \ud50c\ub7ec\uc2a4 "
        "\ubaa8\uac74\uc2a4\ud0e0\ub9ac \uc911\uac04\uc120\uac70 \uc2dc\ub098\ub9ac\uc624" + _FM,
        "4a01351c52de27259bc71599abfbe470364d446e04856b8745dfd7a45cf678f5",
        "R0",
        ("\uc911\uac04\uc120\uac70", "\ubaa8\uac74\uc2a4\ud0e0\ub9ac", "\uc120\uac70"),
    ),
    (
        "P10",
        "AI \uc778\ud504\ub77c\ud22c\uc790\uc5d0\uc11c \uc804\ub825 \ud14c\ub9c8\uc8fc\ub4e4\uc758 "
        "\uc704\uce58\ub97c \uc7ac\uc815\uc758\ud574\uc57c \ud55c\ub2e4\ub294 \uc598\uae38 "
        "\ud574\uc8fc\uace0 \uc2f6\uc5b4 \uc801\ub294 \uae00 \uc808\ub300\ub8e8 "
        "\uc544\ub2c8\uac70\ub4f1_" + _FM,
        "ddcb2546dec63baee64aa578103e37e7e12435551bf164cabf6593e7b4ec9973",
        "R0",
        ("\uc804\ub825", "\ubc1c\uc804", "\ub370\uc774\ud130\uc13c\ud130", "BYOP"),
    ),
)

# Classification instruction (fixed). Route meanings summarize
# docs/claude/external-claims-ledger.md lines 21-36 (section 1 rules 1, 3 and 4).
# Decoded text is pinned in test_llm_pilot_pdfcmp.py.
INSTRUCTION = (
    "\uc704 PDF\ub294 \uc678\ubd80 \uae00\uc774\ub2e4. \uc678\ubd80 \uc8fc\uc7a5 \uc6d0\uc7a5 "
    "\uaddc\uce59\uc73c\ub85c 1\ucc28 \ubd84\ub958\ub9cc \ud55c\ub2e4.\n"
    "\uc678\ubd80 \uc8fc\uc7a5\uc758 \ub9e4\ub9e4 \uadfc\uac70 \uac15\ub3c4\ub294 0\uc774\ub2e4. "
    "\uae08\uc561\u00b7\uc218\ub7c9\u00b7\ub9e4\ub9e4 \ud310\ub2e8\uc740 \uc4f0\uc9c0 "
    "\uc54a\ub294\ub2e4.\n"
    "\ub77c\uc6b0\ud2b8 \ub73b:\n"
    "- R1: \uc885\ubaa9 thesis\u00b7\uc774\ubca4\ud2b8 \ubcf4\uac15(\uc815\ubcf4)\n"
    "- R2: \uadfc\uac70 \ud6c4\ubcf4(\uacf5\uc2dd \uc218\uce58\ub85c \ud655\uc778\ud560 \uc218 "
    "\uc788\ub294 \uc8fc\uc7a5: SEC\u00b7IR\u00b7\ud68c\uc0ac \ubc1c\ud45c\u00b7\uacf5\uc2dd "
    "\ud1b5\uacc4)\n"
    "- R3: \ubc29\ubc95\ub860\n"
    "- R4: \uc0c8 \uc885\ubaa9 \ud6c4\ubcf4\n"
    "- P: \ud3ec\uc9c0\uc154\ub2dd \ucc38\uace0(\ud45c\uc2dc \uc804\uc6a9, \ub9cc\ub8cc\uc77c "
    "\ud544\uc218)\n"
    "- R0: \uae30\ub85d\ub9cc. \uae30\uacc4\uac00 \ud310\uc815\ud560 \uc218 \uc788\ub294 "
    "\ud655\uc778 \uc870\uac74(\ub0a0\uc9dc \ub610\ub294 \uc774\ubca4\ud2b8)\u00b7\ub9de\uc74c "
    "\uae30\uc900\u00b7\ud2c0\ub9bc \uae30\uc900\uc744 \uc801\uc744 \uc218 \uc5c6\uc73c\uba74 R0.\n"
    "\ubd84\ub958: \ub77c\uc6b0\ud2b8\uac00 R0\uc774\uba74 R0, \uadf8 \ubc16\uc774\uba74 "
    "\ud6c4\ubcf4.\n"
    "\ub2f5\uc740 \uc544\ub798 4\uc904\ub9cc \uc4f4\ub2e4:\n"
    "\ubd84\ub958: \ud6c4\ubcf4|R0\n"
    "\ub77c\uc6b0\ud2b8: R1|R2|R3|R4|P|R0\n"
    "\ub300\uc0c1: <\uc885\ubaa9 \uae30\ud638\ub098 \uc8fc\uc81c \ub0b1\ub9d0, \uc27c\ud45c\ub85c>\n"
    "\uadfc\uac70: <\uae00 \uc18d \ubb38\uc7a5 \uadf8\ub300\ub85c \ud55c \uc904>"
)

LABEL_CLASS = "\ubd84\ub958"
LABEL_ROUTE = "\ub77c\uc6b0\ud2b8"
LABEL_TARGET = "\ub300\uc0c1"
LABEL_EVIDENCE = "\uadfc\uac70"
CLASS_CAND_KO = "\ud6c4\ubcf4"
ROUTES = ("R1", "R2", "R3", "R4", "P", "R0")

REASON_KO = {
    "no_key": "\ud0a4 \uc5c6\uc74c",
    "usage_unreadable": "\uc0ac\uc6a9 \uae30\ub85d\uc744 \uc77d\uc744 \uc218 \uc5c6\uc74c",
    "budget_spent": "\uc774\ub2ec \uc608\uc0b0\uc744 \ub118\uc74c",
    "hold": "\uc4f8 \uc218 \uc788\ub294 PDF\uac00 8\uac1c \ubbf8\ub9cc (\ub2e4\uc74c \ub0a0 \ub2e4\uc2dc \ud655\uc778)",
    "upload_failed": "PDF \uc62c\ub9ac\uae30 \uc2e4\ud328 ",
    "call_failed": "API \ud638\ucd9c \uc2e4\ud328 ",
    "bad_shape": "\uc751\ub2f5 \ud615\uc2dd \ub2e4\ub984",
    "unexpected": "\uc608\uc0c1 \ubabb \ud55c \uc624\ub958 (%s)",
}

MD_HEAD = "\ud310\uc815: %s \u2014 \ubd84\ub958 %d/%d \u00b7 \uc8fc\uc81c %d/%d \u00b7 \uc778\uc6a9 \ud655\uc778 %d/%d"
MD_TABLE_HEAD = (
    "| pid | \uc815\ub2f5 | \ubaa8\ub378 \ubd84\ub958 | \ub77c\uc6b0\ud2b8 | \ub300\uc0c1 | \uc77c\uce58 "
    "| \uc778\uc6a9 | \uadfc\uac70(60\uc790) |\n"
    "|---|---|---|---|---|---|---|---|"
)
MD_MATCH = "\ubd84\ub958 %s \u00b7 \uc8fc\uc81c %s"
MD_EXCLUDED = "\uc81c\uc678 (%s)"
MD_QUOTE_OK = "\ud655\uc778"
MD_QUOTE_MISSING = "\uc5c6\uc74c"
MD_SKIPPED = "- \ube80 PDF: %s"
MD_NOT_DELETED = "- \uc9c0\uc6b0\uc9c0 \ubabb\ud55c \ud30c\uc77c: %d\uac1c"
MD_FOOTER = "\ud45c\uc2dc \uc804\uc6a9: \uc6d0\uc7a5\u00b7\ud1b5\ud569\uc810\uac80\u00b7\ucf54\uc5b4\ub294 \uc774 \uacb0\uacfc\ub97c \uc77d\uc9c0 \uc54a\ub294\ub2e4"
MD_ANSWER = {"CAND": "\ud6c4\ubcf4", "R0": "R0"}

_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SPACES = re.compile(r"\s+")
_VALUE_EDGE = "*`_ \t"


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
    text = "llm-pdfcmp %s %s" % (day, status)
    if extra:
        text += " " + extra
    return text[:200]


def _norm_space(text) -> str:
    return _SPACES.sub(" ", str(text)).strip()


def _squash(text) -> str:
    return "".join(str(text).split()).casefold()


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


# ---------------------------------------------------------------- PDF check (read only)

def check_pdfs(pdf_dir):
    """Return (usable, skipped). usable = [(row, bytes)], skipped = [{"pid", "reason"}]."""
    folder = Path(pdf_dir)
    usable = []
    skipped = []
    for row in PDFS:
        pid, name, sha, _answer, _topics = row
        path = folder / name
        try:
            if not path.is_file():
                skipped.append({"pid": pid, "reason": "MISSING"})
                continue
            if path.stat().st_size > MAX_PDF_BYTES:
                skipped.append({"pid": pid, "reason": "TOO_LARGE"})
                continue
            data = path.read_bytes()
        except OSError:
            skipped.append({"pid": pid, "reason": "MISSING"})
            continue
        if len(data) > MAX_PDF_BYTES:
            skipped.append({"pid": pid, "reason": "TOO_LARGE"})
            continue
        if hashlib.sha256(data).hexdigest() != sha:
            skipped.append({"pid": pid, "reason": "SHA_MISMATCH"})
            continue
        usable.append((row, data))
    return usable, skipped


def _skipped_text(skipped) -> str:
    return ",".join("%s:%s" % (item["pid"], item["reason"]) for item in skipped) or "-"


def estimate_submit_cost(n_pdfs) -> float:
    one = estimate_cost(
        MODELS[PILOT],
        {"input_tokens": EST_INPUT_TOKENS_PER_PDF, "output_tokens": EST_OUTPUT_TOKENS_PER_PDF},
        batch=True,
    )
    return one * n_pdfs


def build_request(pid, file_id):
    return {
        "custom_id": pid,
        "params": {
            "model": MODELS[PILOT],
            "max_tokens": MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id},
                            "citations": {"enabled": True},
                        },
                        {"type": "text", "text": INSTRUCTION},
                    ],
                }
            ],
        },
    }


def _delete_files(client, file_ids):
    """Delete each uploaded file; return the ids that could not be deleted."""
    left = []
    for file_id in file_ids:
        try:
            client.files.delete(file_id)
        except Exception:
            left.append(file_id)
    return left


def _remove_stale_failed(out_dir) -> None:
    path = Path(out_dir) / "failed.md"
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------- submit

def run_submit(day, *, repo_root=REPO_ROOT, pdf_dir=DEFAULT_PDF_DIR, client_factory=None, now=None,
               dry_run=False):
    """Return (exit_code, status, stdout_line)."""
    day = valid_day(day)
    root = Path(repo_root)
    clock = _clock(now)
    started = clock()
    base = pilot_dir(root)
    out_dir = day_dir_for(root, day)

    def done(status, extra=""):
        return EXIT_CODES[status], status, _line(day, status, extra)

    def fail(status, reason_ko, extra=""):
        if not dry_run:
            write_failed(out_dir, status, reason_ko)
        return done(status, extra)

    # 1. one time only
    if (base / "compare.json").exists():
        return done("DONE_ALREADY")
    if (base / "batch.json").exists():
        return done("PENDING")

    # 2. PDF check (read only)
    usable, skipped = check_pdfs(pdf_dir)
    counts = "used=%d skipped=%s" % (len(usable), _skipped_text(skipped))
    if dry_run:
        return done("DRY_RUN", counts)
    if len(usable) < MIN_USED:
        # no call, no batch.json, no compare.json: checked again the next day
        return fail("HOLD", REASON_KO["hold"], counts)

    # 3. key; only load_key() reads it and the value goes to the client factory alone
    key = load_key()
    if key is None:
        return fail("NO_KEY", REASON_KO["no_key"])

    # 4. month budget before any upload; an unreadable usage file stops too
    try:
        spent = month_spend(root, PILOT, started.strftime("%Y-%m"))
    except Exception:
        return fail("BUDGET_STOP", REASON_KO["usage_unreadable"])
    if spent + estimate_submit_cost(len(usable)) > BUDGET_USD_MONTH[PILOT]:
        return fail("BUDGET_STOP", REASON_KO["budget_spent"])

    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None

    # 5. upload under an ASCII name; the original file name is never sent
    uploaded = []
    try:
        for row, data in usable:
            pid = row[0]
            info = client.files.upload(file=(pid + ".pdf", data, "application/pdf"))
            file_id = _attr(info, "id", None)
            if not isinstance(file_id, str) or not file_id:
                _delete_files(client, [item["file_id"] for item in uploaded])
                return fail("API_ERROR", REASON_KO["bad_shape"])
            uploaded.append({"pid": pid, "file_id": file_id, "sha256": row[2]})
    except Exception as exc:
        _delete_files(client, [item["file_id"] for item in uploaded])
        return fail("API_ERROR", REASON_KO["upload_failed"] + api_error_label(exc))

    # 6. one batch, one request per PDF
    requests = [build_request(item["pid"], item["file_id"]) for item in uploaded]
    try:
        batch = client.messages.batches.create(requests=requests)
    except Exception as exc:
        _delete_files(client, [item["file_id"] for item in uploaded])
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    batch_id = _attr(batch, "id", None)
    if not isinstance(batch_id, str) or not batch_id:
        _delete_files(client, [item["file_id"] for item in uploaded])
        return fail("API_ERROR", REASON_KO["bad_shape"])

    # 7. batch file
    doc = {
        "schema": BATCH_SCHEMA,
        "day": day,
        "status": "SUBMITTED",
        "batch_id": batch_id,
        "model": MODELS[PILOT],
        "submitted_at": _iso(clock()),
        "items": uploaded,
        "skipped": skipped,
    }
    try:
        atomic_write_text(base / "batch.json", _dump(doc))
    except Exception:
        _delete_files(client, [item["file_id"] for item in uploaded])
        raise
    _remove_stale_failed(out_dir)
    return done("SUBMITTED", "requests=%d %s" % (len(requests), counts))


# ---------------------------------------------------------------- answer parsing

def _field_pattern(label):
    return re.compile(
        r"^[ \t>*_`-]*" + re.escape(label) + r"[ \t*_`]*[:\uff1a][ \t]*(.*?)[ \t]*$",
        re.MULTILINE,
    )


_FIELDS = {
    "class": _field_pattern(LABEL_CLASS),
    "route": _field_pattern(LABEL_ROUTE),
    "target": _field_pattern(LABEL_TARGET),
    "evidence": _field_pattern(LABEL_EVIDENCE),
}


def parse_answer(text):
    """{"class": "CAND"|"R0", "route", "target", "evidence"} or None (PARSE_FAIL)."""
    if not isinstance(text, str):
        return None
    values = {}
    for name, pattern in _FIELDS.items():
        match = pattern.search(text)
        if match is None:
            return None
        value = match.group(1).strip(_VALUE_EDGE)
        if not value:
            return None
        values[name] = value
    raw_class = values["class"]
    if raw_class == CLASS_CAND_KO:
        values["class"] = "CAND"
    elif raw_class.upper() == "R0":
        values["class"] = "R0"
    else:
        return None
    route = values["route"].upper()
    if route not in ROUTES:
        return None
    values["route"] = route
    return values


def topic_overlap(topics, target) -> bool:
    squashed = _squash(target)
    return any(_squash(word) and _squash(word) in squashed for word in topics)


def citation_texts(message):
    out = []
    for block in _attr(message, "content", []) or []:
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


def verdict(used, class_n, topic_n) -> str:
    if used < MIN_USED:
        return "HOLD"
    if class_n >= PASS_CLASS and topic_n >= PASS_TOPIC:
        return "PASS"
    return "FAIL"


# ---------------------------------------------------------------- collect

def _answer_row(pid):
    for row in PDFS:
        if row[0] == pid:
            return row
    return None


def _cell(text) -> str:
    return _norm_space(text).replace("|", "/")


def render_md(doc) -> str:
    c = doc["counts"]
    used = c["used"]
    lines = [
        MD_HEAD % (doc["verdict"], c["class_match"], used, c["topic_match"], used, c["quote_ok"], used),
        "",
        MD_TABLE_HEAD,
    ]
    for row in doc["rows"]:
        if row["excluded"]:
            match = MD_EXCLUDED % row["reason"]
        else:
            match = MD_MATCH % ("O" if row["class_match"] else "X", "O" if row["topic_match"] else "X")
            if row["reason"]:
                match += " (%s)" % row["reason"]
        quote = MD_QUOTE_OK if row["quote_ok"] else MD_QUOTE_MISSING
        model_class = MD_ANSWER.get(row["model_class"], "-") if row["model_class"] else "-"
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                row["pid"],
                MD_ANSWER[row["answer"]],
                model_class,
                _cell(row["route"] or "-"),
                _cell(row["target"] or "-"),
                match,
                quote,
                _cell((row["evidence"] or "-")[:EVIDENCE_MD_CHARS]),
            )
        )
    lines.append("")
    if doc["skipped"]:
        lines.append(MD_SKIPPED % _skipped_text(doc["skipped"]))
    if doc["files_not_deleted"]:
        lines.append(MD_NOT_DELETED % len(doc["files_not_deleted"]))
    lines.append(MD_FOOTER)
    return "\n".join(lines) + "\n"


def _write_compare(base, doc) -> None:
    atomic_write_text(base / "compare.json", _dump(doc))
    atomic_write_text(base / "compare.md", render_md(doc))


def run_collect(day, *, repo_root=REPO_ROOT, client_factory=None, now=None, dry_run=False):
    """Return (exit_code, status, stdout_line)."""
    day = valid_day(day)
    root = Path(repo_root)
    clock = _clock(now)
    base = pilot_dir(root)
    out_dir = day_dir_for(root, day)

    def done(status, extra=""):
        return EXIT_CODES[status], status, _line(day, status, extra)

    def fail(status, reason_ko):
        write_failed(out_dir, status, reason_ko)
        return done(status)

    # 1. one time only; batch file
    if (base / "compare.json").exists():
        return done("DONE_ALREADY")
    batch_path = base / "batch.json"
    if not batch_path.exists():
        return done("NO_BATCH")
    if dry_run:
        return done("DRY_RUN")
    batch = json.loads(batch_path.read_bytes().decode("utf-8"))
    if not isinstance(batch, dict) or batch.get("status") != "SUBMITTED":
        raise ValueError("batch.json is not a submitted batch")
    batch_id = batch["batch_id"]
    items = batch["items"]
    if not isinstance(batch_id, str) or not isinstance(items, list):
        raise ValueError("batch.json has a bad shape")

    # 2. key
    key = load_key()
    if key is None:
        return fail("NO_KEY", REASON_KO["no_key"])
    factory = client_factory if client_factory is not None else make_client
    client = factory(key)
    key = None

    # 3. ended yet?
    try:
        info = client.messages.batches.retrieve(batch_id)
    except Exception as exc:
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    if _attr(info, "processing_status", None) != "ended":
        return done("WAITING")

    # 4. every result
    try:
        entries = list(client.messages.batches.results(batch_id))
    except Exception as exc:
        return fail("API_ERROR", REASON_KO["call_failed"] + api_error_label(exc))
    received_at = _iso(clock())
    expected = MODELS[PILOT]
    pids_sent = [item["pid"] for item in items]

    # 5. usage: one line per result that carries a message, once
    usage_done = base / "usage-done"
    if not usage_done.exists():
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

    # 6. first result per submitted pid
    by_pid = {}
    for entry in entries:
        custom_id = _attr(entry, "custom_id", None)
        if custom_id in pids_sent and custom_id not in by_pid:
            by_pid[custom_id] = _attr(entry, "result", None)

    rows = []
    for pid in pids_sent:
        answer_row = _answer_row(pid)
        if answer_row is None:
            raise ValueError("batch.json names an unknown pid")
        row = {
            "pid": pid,
            "answer": answer_row[3],
            "model_class": None,
            "route": None,
            "target": None,
            "evidence": None,
            "class_match": False,
            "topic_match": False,
            "quote_ok": False,
            "excluded": False,
            "reason": None,
        }
        rows.append(row)
        res = by_pid.get(pid)
        if res is None:
            row["reason"] = "NO_RESULT"
            continue
        kind = _attr(res, "type", None)
        if kind != "succeeded":
            row["reason"] = str(kind).upper() if isinstance(kind, str) and kind else "NO_RESULT"
            continue
        message = _attr(res, "message", None)
        problem = check_message(message, expected)
        if problem == "MODEL_MISMATCH":
            row["excluded"] = True
            row["reason"] = problem
            continue
        if problem:
            row["reason"] = problem
            continue
        parsed = parse_answer(response_text(message))
        if parsed is None:
            row["reason"] = "PARSE_FAIL"
            continue
        row["model_class"] = parsed["class"]
        row["route"] = parsed["route"]
        row["target"] = parsed["target"][:TARGET_JSON_CHARS]
        row["evidence"] = parsed["evidence"][:EVIDENCE_JSON_CHARS]
        row["class_match"] = parsed["class"] == answer_row[3]
        row["topic_match"] = topic_overlap(answer_row[4], parsed["target"])
        row["quote_ok"] = any(quote_overlaps(text, parsed["evidence"]) for text in citation_texts(message))

    # 7. verdict
    used = sum(1 for row in rows if not row["excluded"])
    class_n = sum(1 for row in rows if not row["excluded"] and row["class_match"])
    topic_n = sum(1 for row in rows if not row["excluded"] and row["topic_match"])
    quote_n = sum(1 for row in rows if not row["excluded"] and row["quote_ok"])
    status = verdict(used, class_n, topic_n)
    file_ids = [item["file_id"] for item in items]
    doc = {
        "schema": COMPARE_SCHEMA,
        "day": day,
        "verdict": status,
        "batch_id": batch_id,
        "model": expected,
        "submitted_at": batch.get("submitted_at"),
        "received_at": received_at,
        "counts": {
            "submitted": len(pids_sent),
            "used": used,
            "class_match": class_n,
            "topic_match": topic_n,
            "quote_ok": quote_n,
            "quote_missing": used - quote_n,
        },
        "pass_rule": {"min_used": MIN_USED, "class_match": PASS_CLASS, "topic_match": PASS_TOPIC},
        "rows": rows,
        "skipped": batch.get("skipped") or [],
        "files_not_deleted": file_ids,
        "display_only": True,
    }

    # 8. compare first, then delete, then compare again with what is left
    _write_compare(base, doc)
    doc["files_not_deleted"] = _delete_files(client, file_ids)
    _write_compare(base, doc)
    _remove_stale_failed(out_dir)
    return done(
        status,
        "class=%d/%d topic=%d/%d quote=%d/%d" % (class_n, used, topic_n, used, quote_n, used),
    )


# ---------------------------------------------------------------- main

def _write_unexpected(out_dir, exc) -> None:
    try:
        write_failed(out_dir, "UNEXPECTED", REASON_KO["unexpected"] % type(exc).__name__)
    except Exception:
        pass


def main(argv=None, *, repo_root=REPO_ROOT, client_factory=None, now=None) -> int:
    parser = argparse.ArgumentParser(description="llm-pdfcmp: one-time PDF classification comparison (display only)")
    parser.add_argument("--phase", required=True, choices=("submit", "collect"))
    parser.add_argument("--day", type=valid_day, default=None, help="KST date YYYY-MM-DD (default: today KST)")
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR, help="external PDF folder (read only)")
    parser.add_argument("--dry-run", action="store_true", help="check the PDFs only; no key, no call, no write")
    args = parser.parse_args(argv)
    day = args.day or (now or datetime.now(KST)).astimezone(KST).date().isoformat()
    try:
        if args.phase == "submit":
            code, _status, line = run_submit(
                day, repo_root=repo_root, pdf_dir=args.pdf_dir, client_factory=client_factory,
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
