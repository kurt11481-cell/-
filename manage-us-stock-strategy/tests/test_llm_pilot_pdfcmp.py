import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "llm_pilot_pdfcmp.py"
SPEC = importlib.util.spec_from_file_location("llm_pilot_pdfcmp", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
NEWS_SPEC = importlib.util.spec_from_file_location("llm_pilot_news_for_pdfcmp", SCRIPT_DIR / "llm_pilot_news.py")
NEWS = importlib.util.module_from_spec(NEWS_SPEC)
assert NEWS_SPEC.loader is not None
NEWS_SPEC.loader.exec_module(NEWS)
RUNNER_SPEC = importlib.util.spec_from_file_location("llm_runner_for_pdfcmp", SCRIPT_DIR / "llm_runner.py")
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)
import llm_pilot_common as COMMON  # noqa: E402

PROMPT = REPO / "docs" / "claude" / "llm-pdfcmp-builder-prompt.md"
FAKE_KEY = "fake-key-PDFCMP-7Q9Z"
MODEL = MODULE.MODELS["pdfcmp"]
DAY = "2026-11-26"
DAY2 = "2026-11-27"
NOW = datetime(2026, 11, 26, 13, 10, 0, tzinfo=MODULE.KST)
NOW2 = datetime(2026, 11, 27, 13, 10, 0, tzinfo=MODULE.KST)
COLLECT_AT = datetime(2026, 11, 26, 15, 10, 0, tzinfo=MODULE.KST)
FORBIDDEN_PARAM_KEYS = {"thinking", "temperature", "fallbacks", "stream", "speed", "cache_control",
                        "betas", "extra_headers", "top_p", "tools", "system", "output_config"}
PIDS = ["P%02d" % i for i in range(1, 11)]

# Answer table of docs/claude/llm-pdfcmp-builder-prompt.md: (pid, answer, sha256, file name).
# File names are written as \uXXXX escapes (task prompt rule).
_FM = " - \uc8fc\uc2dd - \uc5d0\ud3a8\ucf54\ub9ac\uc544.pdf"
EXPECTED_TABLE = (
    ("P01", "CAND", "300bca2e1b23896e8dba18e2178ead47654307ca8d3071429afd0183c93a4402",
     "\ub9c8\uc774\ud06c\ub860 $MU ___30\ub144 \ub9d0\uae4c\uc9c0 \ud53c\uc9c0\uceecAI\uac00 "
     "\uba54\ubaa8\ub9ac\uc640 \uc2a4\ud1a0\ub9ac\uc9c0 \uc218\uc694\uc758 \uc911\uc694\ud55c "
     "\ub3d9\uc778\uc774 \ub420 \uc218 \uc788\ub2e4._" + _FM),
    ("P02", "CAND", "8fdeb7c97f07236b2c804d0663fa41bad8cdfee0861c8bce07fe3c53d65553e3",
     "28\ub144 \uba54\ubaa8\ub9ac Q \uc0ac\uc774\ud074\uc5d0 \ub300\ud55c \uc77c\ubc18\uc801\uc778 "
     "\uc778\uc2dd\uc774" + _FM),
    ("P03", "CAND", "960abfa0ba0d8924d06d38cad6a618595ec6002a96ece77c518c96043ab0a2a0",
     "_\ub808\ud3ec\ud2b8_ \uc0cc\ub514\uc2a4\ud06c SNDK __ \ud4e8\uc5b4 \ub0b8\ub4dc "
     "\ud50c\ub808\uc774\uc5b4" + _FM),
    ("P04", "CAND", "30a3002b62fb72bc7ef7576ac7beafacb467ed65004308081f0b142cced3c3ec",
     "\ub2e8\ub3c5_ \uc5f0\uc900, \uc778\ud50c\ub808\uc774\uc158 \uc804\ub9dd \uc704\ud574 "
     "AI\u00b7\uad00\uc138\u00b7\uc5d0\ub108\uc9c0 \uc8fc\uc2dc" + _FM),
    ("P05", "CAND", "a67c86fd8a640fc799f2bac0cebaa968dd660aab4327dd0f0417389d395bfe02",
     "\uc5f0\ud734\uae30\uac04\uc5d0\ub294 \uae00 \uc548\uc4f8\ub824\uace0 \ud588\ub294\ub370 "
     "\uc2ec\uc2ec\ud574\uc11c \uc4f0\ub294\uac70 \uc808\ub300\ub8e8 \uc544\ub2c8\uac70\ub4f1_ "
     "\ud765!" + _FM),
    ("P06", "R0", "83a04de9ed3f51266601be05b2550baaec3f9cfaa3848ef1fe83ce28957a1bd1",
     "\ucd94\uc138\ucd94\uc885 \ud2b8\ub808\uc774\ub529 _ \uadf8\ub798\uc11c \ub9e4\uc218\uc640 "
     "\ub9e4\ub3c4\ub294 \uc5b8\uc81c \ud574\uc694_" + _FM),
    ("P07", "R0", "f47cd947c308a93d1e19ee02e06fef2fdfdf76cc11d7b571f94bde7077480210",
     "bbs_1790030156281.pdf"),
    ("P08", "R0", "35141529a39e283a51b323bdbb7f233ef5c3211bf37a1c057a12a0102215d28b",
     "bbs_1791326873246.pdf"),
    ("P09", "R0", "4a01351c52de27259bc71599abfbe470364d446e04856b8745dfd7a45cf678f5",
     "10\uc6d4, \ub784\ubd80 \ub5a8\ub9ac\ub294 \uc870\uc815 \uc624\ub824\ub098_ \ud50c\ub7ec\uc2a4 "
     "\ubaa8\uac74\uc2a4\ud0e0\ub9ac \uc911\uac04\uc120\uac70 \uc2dc\ub098\ub9ac\uc624" + _FM),
    ("P10", "R0", "ddcb2546dec63baee64aa578103e37e7e12435551bf164cabf6593e7b4ec9973",
     "AI \uc778\ud504\ub77c\ud22c\uc790\uc5d0\uc11c \uc804\ub825 \ud14c\ub9c8\uc8fc\ub4e4\uc758 "
     "\uc704\uce58\ub97c \uc7ac\uc815\uc758\ud574\uc57c \ud55c\ub2e4\ub294 \uc598\uae38 "
     "\ud574\uc8fc\uace0 \uc2f6\uc5b4 \uc801\ub294 \uae00 \uc808\ub300\ub8e8 "
     "\uc544\ub2c8\uac70\ub4f1_" + _FM),
)
_PROMPT_ROW = re.compile(r"^\| (P\d\d) \| (CAND|R0) \| ([0-9a-f]{64}) \| (.+?) \| (.+?) \|\s*$")


def prompt_rows():
    rows = []
    for line in PROMPT.read_text(encoding="utf-8").splitlines():
        match = _PROMPT_ROW.match(line)
        if match:
            topics = tuple(word.strip() for word in match.group(4).split("\u00b7"))
            rows.append((match.group(1), match.group(2), match.group(3), topics, match.group(5)))
    return rows


def ko_class(answer):
    return "후보" if answer == "CAND" else "R0"


def answer_text(cls_ko, route, target, evidence):
    return "분류: %s\n라우트: %s\n대상: %s\n근거: %s" % (cls_ko, route, target, evidence)


def evidence_of(pid):
    return "이 글은 %s 의 핵심 문장이다" % pid


def usage_ns(inp=30000, out=300):
    return SimpleNamespace(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=0,
                           cache_read_input_tokens=None)


def message(text, model=MODEL, stop="end_turn", cited=None, usage=None):
    citations = [SimpleNamespace(type="page_location", cited_text=cited)] if cited else None
    return SimpleNamespace(model=model, stop_reason=stop,
                           content=[SimpleNamespace(type="text", text=text, citations=citations)],
                           usage=usage if usage is not None else usage_ns())


def succeeded(cid, msg):
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=msg))


def other(cid, kind):
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type=kind))


class APIStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class FakeFiles:
    def __init__(self):
        self.uploaded = []
        self.deleted = []
        self.fail_at = None
        self.delete_fail = set()

    def upload(self, file):
        if self.fail_at is not None and len(self.uploaded) == self.fail_at:
            raise APIStatusError("upload broke", 500)
        name, data, mime = file
        self.uploaded.append((name, len(data), mime))
        return SimpleNamespace(id="file_%02d" % len(self.uploaded), type="file")

    def delete(self, file_id):
        self.deleted.append(file_id)
        if file_id in self.delete_fail:
            raise APIStatusError("delete broke", 500)
        return SimpleNamespace(id=file_id, type="file_deleted")


class FakeBatches:
    def __init__(self):
        self.created = []
        self.calls = []
        self.create_exc = None
        self.status = "ended"
        self.override = {}

    def create(self, requests):
        self.calls.append("create")
        if self.create_exc is not None:
            raise self.create_exc
        self.created.append(copy.deepcopy(requests))
        return SimpleNamespace(id="msgbatch_%d" % len(self.created), processing_status="in_progress")

    def retrieve(self, batch_id):
        self.calls.append("retrieve")
        return SimpleNamespace(id=batch_id, processing_status=self.status)

    def results(self, batch_id):
        self.calls.append("results")
        requests = self.created[int(batch_id.split("_")[1]) - 1]
        out = []
        for req in reversed(requests):  # results come in no particular order
            pid = req["custom_id"]
            if pid in self.override:
                if self.override[pid] is not None:
                    out.append(self.override[pid])
                continue
            out.append(succeeded(pid, default_message(pid)))
        return iter(out)


def real_row(pid):
    return [row for row in MODULE.PDFS if row[0] == pid][0]


def default_message(pid, cls=None, target=None, cited=True, model=MODEL):
    row = real_row(pid)
    cls_ko = cls if cls is not None else ko_class(row[3])
    route = "R0" if cls_ko == "R0" else "R1"
    tgt = target if target is not None else row[4][0] + ", 기타"
    ev = evidence_of(pid)
    return message(answer_text(cls_ko, route, tgt, ev), model=model, cited=ev if cited else None)


class Factory:
    def __init__(self):
        self.files = FakeFiles()
        self.batches = FakeBatches()
        self.client = SimpleNamespace(files=self.files, messages=SimpleNamespace(batches=self.batches))
        self.called = 0
        self.keys_ok = []

    def __call__(self, key):
        self.called += 1
        self.keys_ok.append(key == FAKE_KEY)
        return self.client


class PdfcmpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.pdf_dir = Path(self.tmp.name) / "pdfs"
        self.pdf_dir.mkdir()
        rows = []
        for row in MODULE.PDFS:
            pid = row[0]
            name = "%s-fake-source.pdf" % pid
            data = ("%%PDF-1.4 fake %s" % pid).encode("ascii")
            (self.pdf_dir / name).write_bytes(data)
            rows.append((pid, name, hashlib.sha256(data).hexdigest(), row[3], row[4]))
        self.fake_table = tuple(rows)
        patcher = mock.patch.object(MODULE, "PDFS", self.fake_table)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.base = self.root / "workspace" / "outputs" / "llm" / "pdfcmp"
        self.usage = self.root / "workspace" / "outputs" / "llm" / "usage.jsonl"
        self.out = io.StringIO()
        self.err = io.StringIO()
        self.factory = Factory()

    def tearDown(self):
        self.tmp.cleanup()

    # -- helpers
    @contextlib.contextmanager
    def env(self, key=True):
        with mock.patch.dict(os.environ, {COMMON.KEY_ENV: FAKE_KEY} if key else {}):
            if not key:
                os.environ.pop(COMMON.KEY_ENV, None)
            with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
                yield

    def submit(self, day=DAY, now=NOW, key=True, dry_run=False):
        with self.env(key):
            return MODULE.run_submit(day, repo_root=self.root, pdf_dir=self.pdf_dir,
                                     client_factory=self.factory, now=now, dry_run=dry_run)

    def collect(self, day=DAY, now=COLLECT_AT, key=True, dry_run=False):
        with self.env(key):
            return MODULE.run_collect(day, repo_root=self.root, client_factory=self.factory, now=now,
                                      dry_run=dry_run)

    def main(self, argv, key=True, now=NOW):
        with self.env(key):
            return MODULE.main(argv, repo_root=self.root, client_factory=self.factory, now=now)

    def sent(self, batch=0):
        return self.factory.batches.created[batch]

    def compare(self):
        return json.loads((self.base / "compare.json").read_text(encoding="utf-8"))

    def usage_lines(self):
        return self.usage.read_text(encoding="utf-8").splitlines() if self.usage.exists() else []

    def all_files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def remove_pdf(self, pid):
        name = [row[1] for row in self.fake_table if row[0] == pid][0]
        (self.pdf_dir / name).unlink()

    def submitted_collect(self, **override):
        code, status, _ = self.submit()
        self.assertEqual("SUBMITTED", status)
        self.factory.batches.override.update(override)
        return self.collect()

    # ------------------------------------------------------------ submit
    def test_submit_ten_pdfs(self):
        code, status, line = self.submit()
        self.assertEqual((0, "SUBMITTED"), (code, status))
        self.assertTrue(line.startswith("llm-pdfcmp %s SUBMITTED requests=10 used=10" % DAY), line)
        self.assertEqual(1, self.factory.called)
        self.assertEqual([True], self.factory.keys_ok)
        self.assertEqual([("%s.pdf" % pid, len(("%%PDF-1.4 fake %s" % pid).encode()), "application/pdf")
                          for pid in PIDS], self.factory.files.uploaded)
        requests = self.sent()
        self.assertEqual(PIDS, [req["custom_id"] for req in requests])
        for i, req in enumerate(requests, 1):
            params = req["params"]
            self.assertEqual(MODEL, params["model"])
            self.assertEqual("claude-haiku-5-5", params["model"])
            self.assertEqual(4096, params["max_tokens"])
            self.assertFalse(FORBIDDEN_PARAM_KEYS & set(params), params.keys())
            self.assertEqual(1, len(params["messages"]))
            content = params["messages"][0]["content"]
            self.assertEqual({"type": "document", "source": {"type": "file", "file_id": "file_%02d" % i},
                              "citations": {"enabled": True}}, content[0])
            self.assertEqual({"type": "text", "text": MODULE.INSTRUCTION}, content[1])
        dump = json.dumps(requests, ensure_ascii=False)
        self.assertNotIn("fake-source", dump)
        batch = json.loads((self.base / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual("msgbatch_1", batch["batch_id"])
        self.assertEqual("SUBMITTED", batch["status"])
        self.assertEqual([{"pid": pid, "file_id": "file_%02d" % i, "sha256": self.fake_table[i - 1][2]}
                          for i, pid in enumerate(PIDS, 1)], batch["items"])
        self.assertEqual([], batch["skipped"])
        self.assertFalse((self.base / "compare.json").exists())
        self.assertFalse((self.base / DAY / "failed.md").exists())

    def test_three_missing_hold_no_call(self):
        for pid in ("P02", "P05", "P09"):
            self.remove_pdf(pid)
        code, status, line = self.submit()
        self.assertEqual((0, "HOLD"), (code, status))
        self.assertIn("used=7", line)
        self.assertIn("P02:MISSING,P05:MISSING,P09:MISSING", line)
        self.assertEqual(0, self.factory.called)
        self.assertEqual([], self.factory.files.uploaded)
        self.assertEqual([], self.factory.batches.calls)
        self.assertFalse((self.base / "batch.json").exists())
        self.assertFalse((self.base / "compare.json").exists())
        failed = (self.base / DAY / "failed.md").read_text(encoding="utf-8")
        self.assertEqual(1, len(failed.splitlines()))
        self.assertIn("(HOLD)", failed)
        self.assertEqual(["failed.md"], sorted(p.name for p in self.base.rglob("*") if p.is_file()))

    def test_hold_then_next_day_submits(self):
        names = {}
        for pid in ("P02", "P05", "P09"):
            name = [row[1] for row in self.fake_table if row[0] == pid][0]
            names[name] = (self.pdf_dir / name).read_bytes()
            self.remove_pdf(pid)
        self.assertEqual("HOLD", self.submit()[1])
        for name, data in names.items():
            (self.pdf_dir / name).write_bytes(data)
        code, status, _ = self.submit(day=DAY2, now=NOW2)
        self.assertEqual((0, "SUBMITTED"), (code, status))
        self.assertEqual(10, len(self.sent()))

    def test_sha_mismatch_and_too_large_skipped(self):
        name = [row[1] for row in self.fake_table if row[0] == "P04"][0]
        (self.pdf_dir / name).write_bytes(b"%PDF-1.4 changed bytes")
        big_name = [row[1] for row in self.fake_table if row[0] == "P07"][0]
        big = b"%PDF-1.4 " + b"x" * 200
        (self.pdf_dir / big_name).write_bytes(big)
        table = tuple(
            (row[0], row[1], hashlib.sha256(big).hexdigest(), row[3], row[4]) if row[0] == "P07" else row
            for row in self.fake_table
        )
        with mock.patch.object(MODULE, "PDFS", table), mock.patch.object(MODULE, "MAX_PDF_BYTES", 100):
            code, status, line = self.submit()
        self.assertEqual((0, "SUBMITTED"), (code, status))
        self.assertIn("used=8 skipped=P04:SHA_MISMATCH,P07:TOO_LARGE", line)
        self.assertEqual([pid for pid in PIDS if pid not in ("P04", "P07")],
                         [req["custom_id"] for req in self.sent()])
        batch = json.loads((self.base / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual([{"pid": "P04", "reason": "SHA_MISMATCH"}, {"pid": "P07", "reason": "TOO_LARGE"}],
                         batch["skipped"])

    def test_batch_exists_pending_no_resubmit(self):
        self.assertEqual("SUBMITTED", self.submit()[1])
        code, status, line = self.submit(day=DAY2, now=NOW2)
        self.assertEqual((0, "PENDING"), (code, status))
        self.assertEqual("llm-pdfcmp %s PENDING" % DAY2, line)
        self.assertEqual(1, len(self.factory.batches.created))
        self.assertEqual(10, len(self.factory.files.uploaded))
        self.assertEqual(1, self.factory.called)

    def test_compare_exists_done_already_both_phases(self):
        self.base.mkdir(parents=True)
        (self.base / "compare.json").write_text("{}\n", encoding="utf-8")
        (self.base / "batch.json").write_text("{}\n", encoding="utf-8")
        self.assertEqual((0, "DONE_ALREADY"), self.submit()[:2])
        self.assertEqual((0, "DONE_ALREADY"), self.collect()[:2])
        self.assertEqual(0, self.factory.called)
        self.assertEqual("{}\n", (self.base / "compare.json").read_text(encoding="utf-8"))

    def test_budget_stop_no_call(self):
        self.usage.parent.mkdir(parents=True, exist_ok=True)
        rec = {k: None for k in COMMON.USAGE_KEYS}
        rec.update({"ts_kst": "2026-11-02T10:00:00+09:00", "pilot": "pdfcmp", "model": MODEL,
                    "cost_usd_est": 4.99, "status": "OK", "batch": True})
        self.usage.write_text(json.dumps(rec) + "\n", encoding="utf-8")
        code, status, _ = self.submit()
        self.assertEqual((5, "BUDGET_STOP"), (code, status))
        self.assertEqual(0, self.factory.called)
        self.assertEqual([], self.factory.files.uploaded)
        self.assertFalse((self.base / "batch.json").exists())
        self.assertIn("(BUDGET_STOP)", (self.base / DAY / "failed.md").read_text(encoding="utf-8"))

    def test_budget_other_month_does_not_stop(self):
        self.usage.parent.mkdir(parents=True, exist_ok=True)
        rec = {k: None for k in COMMON.USAGE_KEYS}
        rec.update({"ts_kst": "2026-10-30T10:00:00+09:00", "pilot": "pdfcmp", "model": MODEL,
                    "cost_usd_est": 4.99, "status": "OK", "batch": True})
        self.usage.write_text(json.dumps(rec) + "\n", encoding="utf-8")
        self.assertEqual("SUBMITTED", self.submit()[1])

    def test_unreadable_usage_budget_stop(self):
        self.usage.parent.mkdir(parents=True, exist_ok=True)
        self.usage.write_text("{not json\n", encoding="utf-8")
        code, status, _ = self.submit()
        self.assertEqual((5, "BUDGET_STOP"), (code, status))
        self.assertEqual(0, self.factory.called)

    def test_estimate_is_below_budget_and_uses_batch_price(self):
        one = COMMON.estimate_cost(MODEL, {"input_tokens": 60000, "output_tokens": 4096}, batch=True)
        self.assertAlmostEqual(one * 10, MODULE.estimate_submit_cost(10))
        self.assertLess(MODULE.estimate_submit_cost(10), COMMON.BUDGET_USD_MONTH["pdfcmp"])
        self.assertEqual(5, COMMON.BUDGET_USD_MONTH["pdfcmp"])

    def test_no_key(self):
        code, status, line = self.submit(key=False)
        self.assertEqual((4, "NO_KEY"), (code, status))
        self.assertEqual("llm-pdfcmp %s NO_KEY" % DAY, line)
        self.assertEqual(0, self.factory.called)
        self.assertIn("(NO_KEY)", (self.base / DAY / "failed.md").read_text(encoding="utf-8"))

    def test_upload_failure_deletes_uploaded(self):
        self.factory.files.fail_at = 3
        code, status, _ = self.submit()
        self.assertEqual((7, "API_ERROR"), (code, status))
        self.assertEqual(["file_01", "file_02", "file_03"], self.factory.files.deleted)
        self.assertEqual([], self.factory.batches.created)
        self.assertFalse((self.base / "batch.json").exists())
        failed = (self.base / DAY / "failed.md").read_text(encoding="utf-8")
        self.assertIn("APIStatusError HTTP 500", failed)
        self.assertIn("(API_ERROR)", failed)

    def test_create_failure_deletes_all(self):
        self.factory.batches.create_exc = APIStatusError("boom", 529)
        code, status, _ = self.submit()
        self.assertEqual((7, "API_ERROR"), (code, status))
        self.assertEqual(["file_%02d" % i for i in range(1, 11)], self.factory.files.deleted)
        self.assertFalse((self.base / "batch.json").exists())

    def test_dry_run_reads_only(self):
        self.remove_pdf("P10")
        code, status, line = self.submit(key=False, dry_run=True)
        self.assertEqual((0, "DRY_RUN"), (code, status))
        self.assertEqual("llm-pdfcmp %s DRY_RUN used=9 skipped=P10:MISSING" % DAY, line)
        self.assertEqual(0, self.factory.called)
        self.assertFalse((self.root / "workspace").exists())
        self.assertEqual((0, "NO_BATCH"), self.collect(key=False, dry_run=True)[:2])
        self.assertFalse((self.root / "workspace").exists())

    def test_dry_run_hold_writes_nothing(self):
        for pid in ("P01", "P02", "P03"):
            self.remove_pdf(pid)
        code, status, _ = self.submit(key=False, dry_run=True)
        self.assertEqual((0, "DRY_RUN"), (code, status))
        self.assertFalse((self.root / "workspace").exists())

    # ------------------------------------------------------------ collect
    def test_collect_no_batch(self):
        code, status, line = self.collect()
        self.assertEqual((0, "NO_BATCH"), (code, status))
        self.assertEqual("llm-pdfcmp %s NO_BATCH" % DAY, line)
        self.assertEqual(0, self.factory.called)
        self.assertFalse((self.root / "workspace").exists())

    def test_collect_waiting_writes_nothing(self):
        self.submit()
        before = self.all_files()
        self.factory.batches.status = "in_progress"
        code, status, _ = self.collect()
        self.assertEqual((0, "WAITING"), (code, status))
        self.assertEqual(before, self.all_files())
        self.assertEqual([], self.factory.files.deleted)

    def test_collect_no_key(self):
        self.submit()
        code, status, _ = self.collect(key=False)
        self.assertEqual((4, "NO_KEY"), (code, status))
        self.assertFalse((self.base / "compare.json").exists())

    def test_collect_pass_eight_eight(self):
        code, status, line = self.submitted_collect(
            P09=succeeded("P09", default_message("P09", cls="후보", target="반도체")),
            P10=succeeded("P10", default_message("P10", cls="후보", target="반도체")),
        )
        self.assertEqual((0, "PASS"), (code, status))
        self.assertEqual("llm-pdfcmp %s PASS class=8/10 topic=8/10 quote=10/10" % DAY, line)
        doc = self.compare()
        self.assertEqual("PASS", doc["verdict"])
        self.assertEqual({"submitted": 10, "used": 10, "class_match": 8, "topic_match": 8, "quote_ok": 10,
                          "quote_missing": 0}, doc["counts"])
        md = (self.base / "compare.md").read_text(encoding="utf-8")
        self.assertEqual("판정: PASS — 분류 8/10 · 주제 8/10 · 인용 확인 10/10", md.splitlines()[0])
        self.assertIn("| P09 | R0 | 후보 | R1 | 반도체 | 분류 X · 주제 X | 확인 |", md)
        self.assertIn("| P01 | 후보 | 후보 | R1 | MU, 기타 | 분류 O · 주제 O | 확인 |", md)
        self.assertNotIn("fake-source", md)

    def test_collect_fail_class_seven(self):
        override = {pid: succeeded(pid, default_message(pid, cls="후보")) for pid in ("P06", "P07", "P08")}
        code, status, _ = self.submitted_collect(**override)
        self.assertEqual((0, "FAIL"), (code, status))
        doc = self.compare()
        self.assertEqual(7, doc["counts"]["class_match"])
        self.assertEqual(10, doc["counts"]["topic_match"])
        self.assertEqual("FAIL", doc["verdict"])

    def test_collect_fail_topic_seven(self):
        override = {pid: succeeded(pid, default_message(pid, target="무관")) for pid in ("P01", "P02", "P03")}
        code, status, _ = self.submitted_collect(**override)
        self.assertEqual("FAIL", status)
        self.assertEqual(10, self.compare()["counts"]["class_match"])
        self.assertEqual(7, self.compare()["counts"]["topic_match"])

    def test_parse_fail_counts_as_mismatch(self):
        code, status, _ = self.submitted_collect(
            P10=succeeded("P10", message("분류 결과는 R0 입니다", cited="아무 문장이나 길게")),
        )
        row = [r for r in self.compare()["rows"] if r["pid"] == "P10"][0]
        self.assertEqual("PARSE_FAIL", row["reason"])
        self.assertFalse(row["class_match"])
        self.assertFalse(row["topic_match"])
        self.assertFalse(row["excluded"])
        self.assertEqual(10, self.compare()["counts"]["used"])
        self.assertEqual(9, self.compare()["counts"]["class_match"])
        self.assertEqual("PASS", status)

    def test_failed_results_count_as_mismatch(self):
        code, status, _ = self.submitted_collect(
            P01=other("P01", "errored"),
            P02=other("P02", "expired"),
            P03=None,
            P04=succeeded("P04", default_message("P04")),
            P05=succeeded("P05", message("x", stop="max_tokens")),
            P06=succeeded("P06", message("x", stop="refusal")),
        )
        rows = {r["pid"]: r for r in self.compare()["rows"]}
        self.assertEqual("ERRORED", rows["P01"]["reason"])
        self.assertEqual("EXPIRED", rows["P02"]["reason"])
        self.assertEqual("NO_RESULT", rows["P03"]["reason"])
        self.assertEqual("MAX_TOKENS", rows["P05"]["reason"])
        self.assertEqual("REFUSAL", rows["P06"]["reason"])
        counts = self.compare()["counts"]
        self.assertEqual(10, counts["used"])
        self.assertEqual(5, counts["class_match"])
        self.assertEqual("FAIL", status)
        # usage lines only for results carrying a message: 10 - errored - expired - missing
        self.assertEqual(7, len(self.usage_lines()))

    def test_model_mismatch_dropped_from_denominator(self):
        code, status, line = self.submitted_collect(
            P10=succeeded("P10", default_message("P10", model="claude-sonnet-5-5")),
        )
        doc = self.compare()
        self.assertEqual(9, doc["counts"]["used"])
        self.assertEqual(9, doc["counts"]["class_match"])
        row = [r for r in doc["rows"] if r["pid"] == "P10"][0]
        self.assertTrue(row["excluded"])
        self.assertEqual("MODEL_MISMATCH", row["reason"])
        self.assertEqual("PASS", status)
        self.assertIn("class=9/9", line)
        md = (self.base / "compare.md").read_text(encoding="utf-8")
        self.assertIn("제외 (MODEL_MISMATCH)", md)
        # a dated snapshot of the pinned model is not a mismatch
        self.assertIsNone(COMMON.check_message(default_message("P01", model=MODEL + "-20261101"), MODEL))

    def test_model_mismatch_below_eight_hold(self):
        override = {pid: succeeded(pid, default_message(pid, model="claude-opus-5-5"))
                    for pid in ("P01", "P02", "P03")}
        code, status, _ = self.submitted_collect(**override)
        self.assertEqual((0, "HOLD"), (code, status))
        doc = self.compare()
        self.assertEqual("HOLD", doc["verdict"])
        self.assertEqual(7, doc["counts"]["used"])
        self.assertTrue((self.base / "compare.md").read_text(encoding="utf-8").startswith("판정: HOLD — 분류 7/7"))

    def test_quote_counting(self):
        override = {pid: succeeded(pid, default_message(pid, cited=False)) for pid in ("P01", "P02", "P03")}
        override["P04"] = succeeded("P04", message(
            answer_text("후보", "R2", "연준", "연준은 인플레이션 전망을 본다"), cited="전혀 다른 내용의 인용"))
        override["P05"] = succeeded("P05", message(
            answer_text("후보", "R1", "AMD", "AMD 서버 CPU 점유율이 오른다"), cited="서버  CPU   점유율이 오른다고 적었다"))
        code, status, _ = self.submitted_collect(**override)
        doc = self.compare()
        self.assertEqual(6, doc["counts"]["quote_ok"])
        self.assertEqual(4, doc["counts"]["quote_missing"])
        rows = {r["pid"]: r for r in doc["rows"]}
        self.assertFalse(rows["P04"]["quote_ok"])
        self.assertTrue(rows["P05"]["quote_ok"])
        # quote checks never change the class verdict
        self.assertEqual("PASS", status)

    def test_quote_overlap_rule(self):
        self.assertTrue(MODULE.quote_overlaps("abc  defgh", "xx abc defg yy"))
        self.assertFalse(MODULE.quote_overlaps("abcde", "abcde"))
        self.assertFalse(MODULE.quote_overlaps("abcdefgh", "zzzzzzzz"))

    def test_collect_deletes_files_and_records_leftovers(self):
        self.submit()
        self.factory.files.delete_fail = {"file_03"}
        self.collect()
        self.assertEqual(["file_%02d" % i for i in range(1, 11)], self.factory.files.deleted)
        self.assertEqual(["file_03"], self.compare()["files_not_deleted"])
        self.assertIn("지우지 못한 파일: 1개", (self.base / "compare.md").read_text(encoding="utf-8"))

    def test_collect_all_deleted(self):
        self.submitted_collect()
        self.assertEqual([], self.compare()["files_not_deleted"])
        self.assertEqual(["file_%02d" % i for i in range(1, 11)], self.factory.files.deleted)

    def test_collect_once_then_done_already(self):
        self.submitted_collect()
        calls = list(self.factory.batches.calls)
        deleted = list(self.factory.files.deleted)
        lines = self.usage_lines()
        self.assertEqual((0, "DONE_ALREADY"), self.collect()[:2])
        self.assertEqual((0, "DONE_ALREADY"), self.submit(day=DAY2, now=NOW2)[:2])
        self.assertEqual(calls, self.factory.batches.calls)
        self.assertEqual(deleted, self.factory.files.deleted)
        self.assertEqual(lines, self.usage_lines())

    def test_usage_lines_shape_and_month_spend(self):
        self.submitted_collect(P10=succeeded("P10", default_message("P10", model="claude-sonnet-5-5")))
        lines = self.usage_lines()
        self.assertEqual(10, len(lines))
        for raw in lines:
            rec = json.loads(raw)
            self.assertEqual(list(COMMON.USAGE_KEYS), list(rec.keys()))
            for key in COMMON.USAGE_KEYS:
                self.assertIsNotNone(rec[key], key)
            self.assertEqual("pdfcmp", rec["pilot"])
            self.assertIs(True, rec["batch"])
            self.assertTrue(rec["ts_kst"].startswith("2026-11-26T15:10:00"))
            self.assertIsInstance(rec["cost_usd_est"], float)
        statuses = sorted(json.loads(raw)["status"] for raw in lines)
        self.assertEqual(["MODEL_MISMATCH"] + ["OK"] * 9, statuses)
        expected_one = COMMON.estimate_cost(MODEL, {"input_tokens": 30000, "output_tokens": 300}, batch=True)
        pinned = [json.loads(raw) for raw in lines if json.loads(raw)["model"] == MODEL]
        self.assertEqual(9, len(pinned))
        for rec in pinned:
            self.assertAlmostEqual(expected_one, rec["cost_usd_est"])
        spent = COMMON.month_spend(self.root, "pdfcmp", "2026-11")
        self.assertGreater(spent, 0)
        # other pilots still read the shared file
        self.assertEqual(0.0, COMMON.month_spend(self.root, "news", "2026-11"))

    def test_unpriced_model_usage_line_still_numeric(self):
        self.submitted_collect(P10=succeeded("P10", default_message("P10", model="other-model-x")))
        rec = [json.loads(raw) for raw in self.usage_lines() if json.loads(raw)["model"] == "other-model-x"][0]
        self.assertIsInstance(rec["cost_usd_est"], float)
        COMMON.month_spend(self.root, "pdfcmp", "2026-11")

    # ------------------------------------------------------------ main / last line / key
    def test_main_last_line_and_exit_codes(self):
        code = self.main(["--phase", "submit", "--day", DAY, "--pdf-dir", str(self.pdf_dir)])
        self.assertEqual(0, code)
        code = self.main(["--phase", "collect", "--day", DAY], now=COLLECT_AT)
        self.assertEqual(0, code)
        out_lines = self.out.getvalue().splitlines()
        self.assertEqual(["llm-pdfcmp %s SUBMITTED requests=10 used=10 skipped=-" % DAY,
                          "llm-pdfcmp %s PASS class=10/10 topic=10/10 quote=10/10" % DAY], out_lines)
        for line in out_lines:
            self.assertTrue(line.isascii())
            self.assertTrue(RUNNER._LINE_OK.fullmatch(line), line)
            self.assertIsNotNone(RUNNER._LINE_STATUS.match(line), line)

    def test_main_unexpected(self):
        self.base.mkdir(parents=True)
        (self.base / "batch.json").write_text("[1, 2]\n", encoding="utf-8")
        code = self.main(["--phase", "collect", "--day", DAY])
        self.assertEqual(1, code)
        self.assertEqual("llm-pdfcmp %s UNEXPECTED" % DAY, self.out.getvalue().strip())
        self.assertIn("(UNEXPECTED)", (self.base / DAY / "failed.md").read_text(encoding="utf-8"))

    def test_key_never_written_or_printed(self):
        self.main(["--phase", "submit", "--day", DAY, "--pdf-dir", str(self.pdf_dir)])
        self.factory.files.delete_fail = {"file_02"}
        self.main(["--phase", "collect", "--day", DAY], now=COLLECT_AT)
        self.main(["--phase", "collect", "--day", DAY], now=COLLECT_AT)
        self.factory.batches.create_exc = APIStatusError("x " + FAKE_KEY, 500)
        self.main(["--phase", "submit", "--day", DAY2, "--pdf-dir", str(self.pdf_dir)], now=NOW2)
        self.assertNotIn(FAKE_KEY, self.out.getvalue())
        self.assertNotIn(FAKE_KEY, self.err.getvalue())
        files = self.all_files()
        self.assertIn("workspace/outputs/llm/pdfcmp/compare.json", files)
        for name, data in files.items():
            self.assertNotIn(FAKE_KEY.encode("utf-8"), data, name)

    def test_exit_codes(self):
        expected = {"SUBMITTED": 0, "PENDING": 0, "WAITING": 0, "PASS": 0, "FAIL": 0, "HOLD": 0,
                    "DONE_ALREADY": 0, "NO_BATCH": 0, "DRY_RUN": 0, "UNEXPECTED": 1, "NO_KEY": 4,
                    "BUDGET_STOP": 5, "API_ERROR": 7}
        self.assertEqual(expected, MODULE.EXIT_CODES)
        for name, value in MODULE.EXIT_CODES.items():
            if name in NEWS.EXIT_CODES:
                self.assertEqual(NEWS.EXIT_CODES[name], value, name)

    # ------------------------------------------------------------ parsing
    def test_parse_answer(self):
        self.assertEqual({"class": "CAND", "route": "R2", "target": "MU, 메모리", "evidence": "문장 하나"},
                         MODULE.parse_answer("분류: 후보\n라우트: R2\n대상: MU, 메모리\n근거: 문장 하나"))
        self.assertEqual("R0", MODULE.parse_answer(
            "- **분류**: r0\n- **라우트**: r0\n- **대상**: PER\n- **근거**: 글 속 문장")["class"])
        self.assertEqual("P", MODULE.parse_answer("분류: 후보\n라우트: p\n대상: x\n근거: y")["route"])
        self.assertIsNone(MODULE.parse_answer("분류: 후보|R0\n라우트: R1\n대상: x\n근거: y"))
        self.assertIsNone(MODULE.parse_answer("분류: 후보\n라우트: R9\n대상: x\n근거: y"))
        self.assertIsNone(MODULE.parse_answer("분류: 후보\n라우트: R1\n대상: x"))
        self.assertIsNone(MODULE.parse_answer("분류: 후보\n라우트: R1\n대상: \n근거: y"))
        self.assertIsNone(MODULE.parse_answer(""))

    def test_topic_overlap_ignores_case_and_space(self):
        self.assertTrue(MODULE.topic_overlap(("데이터센터",), "AI 데이터 센터 전력"))
        self.assertTrue(MODULE.topic_overlap(("Fed",), "FED, 금리"))
        self.assertTrue(MODULE.topic_overlap(("S&P",), "s & p 500"))
        self.assertFalse(MODULE.topic_overlap(("MU", "메모리"), "NVDA, GPU"))

    # ------------------------------------------------------------ contracts
    def test_script_source_contract(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(text.isascii())
        for word in ("environ", "zoneinfo", "subprocess", "import requests", "urllib", "fallbacks",
                     "advisor", "socket", "http.client", "auto_core", "kiwoom"):
            self.assertNotIn(word, text, word)
        self.assertNotIn(b"\r\n", SCRIPT.read_bytes())
        self.assertNotIn(b"\r\n", Path(__file__).read_bytes())
        # the PDF folder is only read: no write, move or delete call names in the script
        for word in ("write_bytes", "unlink(", "rename(", "rmtree", "shutil", "os.remove"):
            if word == "unlink(":
                # only the stale failed.md under workspace/outputs/llm is removed
                self.assertEqual(1, text.count(word))
                continue
            self.assertNotIn(word, text, word)

    def test_answer_table_matches_prompt(self):
        real = self.real_pdfs()
        self.assertEqual([(r[0], r[1], r[2]) for r in EXPECTED_TABLE], [(r[0], r[3], r[2]) for r in real])
        self.assertEqual([r[3] for r in EXPECTED_TABLE], [r[1] for r in real])
        rows = prompt_rows()
        self.assertEqual(10, len(rows))
        self.assertEqual([(r[0], r[1], r[2], r[3], r[4]) for r in rows],
                         [(r[0], r[3], r[2], r[4], r[1]) for r in real])

    def real_pdfs(self):
        # setUp replaced PDFS with a fake table; read the module source value instead
        spec = importlib.util.spec_from_file_location("llm_pilot_pdfcmp_contract", SCRIPT)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        return fresh.PDFS

    def test_pinned_korean_text(self):
        self.assertEqual("E:\\사업\\##금동한\\chatgpt_종목분석결과\\외부자료", MODULE.DEFAULT_PDF_DIR)
        self.assertEqual(
            "위 PDF는 외부 글이다. 외부 주장 원장 규칙으로 1차 분류만 한다.\n"
            "외부 주장의 매매 근거 강도는 0이다. 금액·수량·매매 판단은 쓰지 않는다.\n"
            "라우트 뜻:\n"
            "- R1: 종목 thesis·이벤트 보강(정보)\n"
            "- R2: 근거 후보(공식 수치로 확인할 수 있는 주장: SEC·IR·회사 발표·공식 통계)\n"
            "- R3: 방법론\n"
            "- R4: 새 종목 후보\n"
            "- P: 포지셔닝 참고(표시 전용, 만료일 필수)\n"
            "- R0: 기록만. 기계가 판정할 수 있는 확인 조건(날짜 또는 이벤트)·맞음 기준·틀림 기준을 적을 수 없으면 R0.\n"
            "분류: 라우트가 R0이면 R0, 그 밖이면 후보.\n"
            "답은 아래 4줄만 쓴다:\n"
            "분류: 후보|R0\n"
            "라우트: R1|R2|R3|R4|P|R0\n"
            "대상: <종목 기호나 주제 낱말, 쉼표로>\n"
            "근거: <글 속 문장 그대로 한 줄>",
            MODULE.INSTRUCTION,
        )
        for word in ("금액", "수량"):
            self.assertIn(word, MODULE.INSTRUCTION)  # named only to say they are not asked
        self.assertEqual(("분류", "라우트", "대상", "근거", "후보"),
                         (MODULE.LABEL_CLASS, MODULE.LABEL_ROUTE, MODULE.LABEL_TARGET, MODULE.LABEL_EVIDENCE,
                          MODULE.CLASS_CAND_KO))
        self.assertEqual({
            "no_key": "키 없음",
            "usage_unreadable": "사용 기록을 읽을 수 없음",
            "budget_spent": "이달 예산을 넘음",
            "hold": "쓸 수 있는 PDF가 8개 미만 (다음 날 다시 확인)",
            "upload_failed": "PDF 올리기 실패 ",
            "call_failed": "API 호출 실패 ",
            "bad_shape": "응답 형식 다름",
            "unexpected": "예상 못 한 오류 (%s)",
        }, MODULE.REASON_KO)
        self.assertEqual("판정: %s — 분류 %d/%d · 주제 %d/%d · 인용 확인 %d/%d", MODULE.MD_HEAD)
        self.assertEqual("| pid | 정답 | 모델 분류 | 라우트 | 대상 | 일치 | 인용 | 근거(60자) |\n"
                         "|---|---|---|---|---|---|---|---|", MODULE.MD_TABLE_HEAD)
        self.assertEqual("분류 %s · 주제 %s", MODULE.MD_MATCH)
        self.assertEqual("제외 (%s)", MODULE.MD_EXCLUDED)
        self.assertEqual(("확인", "없음"), (MODULE.MD_QUOTE_OK, MODULE.MD_QUOTE_MISSING))
        self.assertEqual("- 뺀 PDF: %s", MODULE.MD_SKIPPED)
        self.assertEqual("- 지우지 못한 파일: %d개", MODULE.MD_NOT_DELETED)
        self.assertEqual("표시 전용: 원장·통합점검·코어는 이 결과를 읽지 않는다", MODULE.MD_FOOTER)
        self.assertEqual({"CAND": "후보", "R0": "R0"}, MODULE.MD_ANSWER)

    def test_real_topic_words_match_prompt(self):
        real = self.real_pdfs()
        self.assertEqual(("MU", "마이크론", "메모리"), real[0][4])
        self.assertEqual(("SNDK", "샌디스크", "낸드", "NAND"), real[2][4])
        self.assertEqual(("연준", "Fed", "인플레이션", "금리"), real[3][4])
        self.assertEqual(("AMD", "INTC", "인텔", "CPU"), real[4][4])
        self.assertEqual(("추세추종", "매매", "손절", "돌파"), real[5][4])
        self.assertEqual(("PER", "밸류에이션", "S&P"), real[6][4])
        self.assertEqual(("PER", "마진", "밸류에이션"), real[7][4])
        self.assertEqual(("중간선거", "모건스탠리", "선거"), real[8][4])
        self.assertEqual(("전력", "발전", "데이터센터", "BYOP"), real[9][4])

    def test_evidence_cut_at_sixty_in_md(self):
        long_ev = "가" * 100
        self.submitted_collect(P01=succeeded("P01", message(answer_text("후보", "R1", "MU", long_ev), cited=long_ev)))
        md = (self.base / "compare.md").read_text(encoding="utf-8")
        self.assertIn("| " + "가" * 60 + " |", md)
        self.assertNotIn("가" * 61, md)


if __name__ == "__main__":
    unittest.main()
