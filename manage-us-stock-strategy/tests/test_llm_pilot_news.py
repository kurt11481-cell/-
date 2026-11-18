import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "llm_pilot_news.py"
SPEC = importlib.util.spec_from_file_location("llm_pilot_news", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
ICC_SPEC = importlib.util.spec_from_file_location("llm_pilot_iccheck_for_news", SCRIPT_DIR / "llm_pilot_iccheck.py")
ICCHECK = importlib.util.module_from_spec(ICC_SPEC)
assert ICC_SPEC.loader is not None
ICC_SPEC.loader.exec_module(ICCHECK)
import llm_pilot_common as COMMON  # noqa: E402

PREREG_REL = "docs/claude/llm-news-prereg-v1.json"
PREREG_SRC = REPO / PREREG_REL
FAKE_KEY = "fake-key-FOR-TEST-7Q9Z"
MODEL = MODULE.MODELS["news"]
DAY = "2026-11-18"
DAY2 = "2026-11-19"
NOW = datetime(2026, 11, 18, 19, 30, 0, tzinfo=MODULE.KST)
COLLECT_AT = datetime(2026, 11, 18, 22, 0, 0, tzinfo=MODULE.KST)
NOW2 = datetime(2026, 11, 19, 19, 30, 0, tzinfo=MODULE.KST)
COLLECT2_AT = datetime(2026, 11, 19, 22, 0, 0, tzinfo=MODULE.KST)
PUB1 = datetime(2026, 11, 18, 5, 0, 0, tzinfo=timezone.utc)
PUB2 = datetime(2026, 11, 19, 5, 0, 0, tzinfo=timezone.utc)
REASON = "Contract win stated in the text."
FORBIDDEN_PARAM_KEYS = {"thinking", "temperature", "fallbacks", "stream", "speed", "cache_control",
                        "betas", "extra_headers", "top_p", "tools"}


def load_prereg_json():
    return json.loads(PREREG_SRC.read_bytes().decode("utf-8"))


PREREG = load_prereg_json()


def flat(uid, title, summary="Plain summary text.", pub=PUB1):
    item = {"uuid": uid, "title": title, "providerPublishTime": int(pub.timestamp())}
    if summary is not None:
        item["summary"] = summary
    return item


def nested(uid, title, summary, pub_iso):
    return {"id": "outer-" + uid, "content": {"id": uid, "title": title, "summary": summary,
                                              "pubDate": pub_iso}}


def basic_feed():
    return {
        "MU": [flat("mu-1", "Micron Technology (NASDAQ: MU) raises guidance",
                    "Micron said demand for $MU memory is strong.")],
        "NVDA": [nested("nv-1", "Nvidia wins data center deal with Nebius",
                        "NVIDIA and Nebius Group signed a deal. https://example.com/x",
                        "2026-11-18T06:00:00Z")],
    }


def day2_feed():
    return {
        "MU": [flat("mu-2", "Micron opens a new fab", "Micron Technology opened a fab.", pub=PUB2)],
        "NVDA": [nested("nv-2", "Nvidia ships new racks", "NVDA shipped racks.", "2026-11-19T06:00:00Z")],
    }


class Fetcher:
    def __init__(self, feed):
        self.feed = feed
        self.calls = []

    def __call__(self, symbol):
        self.calls.append(symbol)
        value = self.feed.get(symbol, [])
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


def usage_ns(inp=200, out=60):
    return SimpleNamespace(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=0,
                           cache_read_input_tokens=None)


def message(text, model=MODEL, stop="end_turn", usage=None):
    return SimpleNamespace(model=model, stop_reason=stop,
                           content=[SimpleNamespace(type="text", text=text)],
                           usage=usage if usage is not None else usage_ns())


def succeeded(cid, msg):
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=msg))


def errored(cid, kind):
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(
        type="errored", error=SimpleNamespace(type="error", error=SimpleNamespace(type=kind, message="detail"))))


def summary_text(cid):
    return "첫째 줄 사실 %s\n둘째 줄 사실\n셋째 줄 사실" % cid


class APIStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class FakeBatches:
    def __init__(self):
        self.created = []
        self.calls = []
        self.retrieved = []
        self.create_exc = None
        self.retrieve_exc = None
        self.status = {}
        self.override = {}
        self.model = MODEL
        self.usage = None

    def create(self, requests):
        self.calls.append("create")
        if self.create_exc is not None:
            raise self.create_exc
        self.created.append(copy.deepcopy(requests))
        return SimpleNamespace(id="msgbatch_%d" % len(self.created), processing_status="in_progress")

    def retrieve(self, batch_id):
        self.calls.append("retrieve")
        self.retrieved.append(batch_id)
        if self.retrieve_exc is not None:
            raise self.retrieve_exc
        return SimpleNamespace(id=batch_id, processing_status=self.status.get(batch_id, "ended"))

    def results(self, batch_id):
        self.calls.append("results")
        requests = self.created[int(batch_id.split("_")[1]) - 1]
        out = []
        for req in reversed(requests):  # results come in no particular order
            cid = req["custom_id"]
            if cid in self.override:
                if self.override[cid] is not None:
                    out.append(self.override[cid])
                continue
            usage = copy.deepcopy(self.usage) if self.usage is not None else None
            if cid.startswith("L"):
                text = json.dumps({"label": "good", "reason": REASON})
            else:
                text = summary_text(cid)
            out.append(succeeded(cid, message(text, model=self.model, usage=usage)))
        return iter(out)


class Factory:
    def __init__(self):
        self.batches = FakeBatches()
        self.client = SimpleNamespace(messages=SimpleNamespace(batches=self.batches))
        self.called = 0
        self.keys_ok = []

    def __call__(self, key):
        self.called += 1
        self.keys_ok.append(key == FAKE_KEY)
        return self.client


class NewsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        dst = self.root / PREREG_REL
        dst.parent.mkdir(parents=True)
        dst.write_bytes(PREREG_SRC.read_bytes())
        self.prereg_path = dst
        self.news = self.root / "workspace" / "outputs" / "llm" / "news"
        self.usage = self.root / "workspace" / "outputs" / "llm" / "usage.jsonl"
        self.records = self.news / "records.jsonl"
        self.out = io.StringIO()
        self.err = io.StringIO()
        self.factory = Factory()

    def tearDown(self):
        self.tmp.cleanup()

    # -- helpers
    @contextlib.contextmanager
    def env(self, key=True):
        with mock.patch.dict(os.environ, {MODULE.KEY_ENV: FAKE_KEY} if key else {}):
            if not key:
                os.environ.pop(MODULE.KEY_ENV, None)
            with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
                yield

    def submit(self, feed=None, day=DAY, now=NOW, key=True, dry_run=False, factory=None, fetcher=None):
        fetcher = fetcher if fetcher is not None else Fetcher(feed if feed is not None else basic_feed())
        with self.env(key):
            return MODULE.run_submit(day, repo_root=self.root, client_factory=factory or self.factory,
                                     fetcher=fetcher, now=now, dry_run=dry_run)

    def collect(self, day=DAY, now=COLLECT_AT, key=True, dry_run=False):
        with self.env(key):
            return MODULE.run_collect(day, repo_root=self.root, client_factory=self.factory, now=now,
                                      dry_run=dry_run)

    def day_dir(self, day=DAY):
        return self.news / day

    def batch_doc(self, day=DAY):
        return json.loads((self.day_dir(day) / "batch.json").read_text(encoding="utf-8"))

    def record_lines(self):
        return self.records.read_text(encoding="utf-8").splitlines()

    def usage_lines(self):
        return self.usage.read_text(encoding="utf-8").splitlines() if self.usage.exists() else []

    def all_files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def sent(self, batch=0):
        return self.factory.batches.created[batch]

    def assert_chain(self):
        lines = self.record_lines()
        self.assertEqual(json.loads(lines[0])["prev_sha256"], "")
        for prev, line in zip(lines, lines[1:]):
            self.assertEqual(json.loads(line)["prev_sha256"],
                             hashlib.sha256(prev.encode("utf-8")).hexdigest())
        return lines

    def assert_no_key_anywhere(self):
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_KEY.encode("utf-8"), path.read_bytes(), str(path))
        self.assertNotIn(FAKE_KEY, self.out.getvalue())
        self.assertNotIn(FAKE_KEY, self.err.getvalue())

    # ------------------------------------------------------------ 1. pre-registration
    def test_prereg_pinned_by_repo_json(self):
        canonical = json.dumps(PREREG, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(hashlib.sha256(canonical.encode("utf-8")).hexdigest(), MODULE.PREREG_SHA256)
        self.assertEqual(hashlib.sha256(PREREG["label_system_prompt"].encode("utf-8")).hexdigest(),
                         MODULE.LABEL_PROMPT_SHA256)
        self.assertEqual(len(PREREG["universe"]), 30)
        prereg, reason = MODULE.load_prereg(self.root)
        self.assertEqual(prereg, PREREG)
        self.assertIsNone(reason)
        self.assertEqual(PREREG["model"]["id"], MODEL)

    def test_prereg_one_char_changed_halts(self):
        raw = PREREG_SRC.read_bytes()
        self.prereg_path.write_bytes(raw.replace(b"Marvell Technology", b"Marvell Technologx", 1))
        self.assertEqual(MODULE.load_prereg(self.root), (None, "PREREG_MISMATCH"))
        fetcher = Fetcher(basic_feed())
        code, status, line = self.submit(fetcher=fetcher)
        self.assertEqual((code, status), (10, "PREREG_MISMATCH"))
        self.assertTrue((self.news / "HALT").exists())
        self.assertIn("(PREREG_MISMATCH)", (self.day_dir() / "failed.md").read_text(encoding="utf-8"))
        self.assertEqual(self.factory.called, 0)
        self.assertEqual(self.factory.batches.calls, [])
        self.assertEqual(fetcher.calls, [])
        # the halt marker stops later submits
        self.prereg_path.write_bytes(raw)
        self.assertEqual(self.submit()[:2], (10, "HALTED"))
        self.assertEqual(self.factory.batches.calls, [])

    def test_prompt_hash_mismatch_also_halts(self):
        doc = load_prereg_json()
        doc["label_system_prompt"] += " "
        self.prereg_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(MODULE.load_prereg(self.root), (None, "PREREG_MISMATCH"))
        self.prereg_path.write_text("{not json", encoding="utf-8")
        self.assertEqual(MODULE.load_prereg(self.root), (None, "PREREG_MISMATCH"))
        self.prereg_path.unlink()
        self.assertEqual(MODULE.load_prereg(self.root), (None, "PREREG_MISMATCH"))

    # ------------------------------------------------------------ 2. masking
    def mask(self, text, target):
        return MODULE.mask_item_text(text, target, PREREG)

    def test_mask_other_and_target(self):
        self.assertEqual(self.mask("Nvidia invests in Nebius", "NBIS"), "[OTHER] invests in [COMPANY]")

    def test_mask_mu_forms(self):
        for text in ("Micron Technology (MU)", "NASDAQ:MU", "Nasdaq: MU", "(NASDAQ: MU)", "$MU", "MU.O",
                     "nasdaq : MU", "(Nasdaq:MU)"):
            out = self.mask(text, "MU")
            self.assertIn("[COMPANY]", out, text)
            self.assertNotIn("MU", out, text)
            self.assertNotIn("Micron", out, text)
        self.assertEqual(self.mask("micron-scale parts", "MU"), "micron-scale parts")
        # a standalone 2-letter symbol is kept by the pre-registration
        self.assertEqual(self.mask("MU shares rise", "MU"), "MU shares rise")

    def test_mask_be_on_arm(self):
        self.assertEqual(self.mask("to be or not to be", "BE"), "to be or not to be")
        self.assertEqual(self.mask("Be ready", "BE"), "Be ready")
        for text in ("Bloom Energy", "(BE)", "NYSE: BE"):
            out = self.mask(text, "BE")
            self.assertEqual(out, "[COMPANY]", text)
        self.assertEqual(self.mask("on track", "ON"), "on track")
        self.assertEqual(self.mask("onsemi", "ON"), "[COMPANY]")
        self.assertEqual(self.mask("ON Semiconductor", "ON"), "[COMPANY]")
        self.assertEqual(self.mask("arm of the company", "ARM"), "arm of the company")
        self.assertEqual(self.mask("Arm Holdings", "ARM"), "[COMPANY]")
        self.assertEqual(self.mask("Arm", "ARM"), "[COMPANY]")

    def test_mask_url_and_standalone(self):
        out = self.mask("Read https://finance.example.com/n/abc?x=1 and www.example.org/y now", "MU")
        self.assertNotIn("http", out)
        self.assertNotIn("example", out)
        self.assertEqual(self.mask("AMD beats while NVDA lags", "AMD"), "[COMPANY] beats while [OTHER] lags")
        self.assertEqual(self.mask("Advanced Micro Devices and Nvidia", "AMD"), "[COMPANY] and [OTHER]")

    def test_mask_is_stable_on_second_pass(self):
        samples = ("Micron Technology (NASDAQ: MU) and $NVDA.O", "Nvidia invests in Nebius",
                   "MU shares rise; Arm Holdings and arm", "KLA Corp (NASDAQ:KLAC) and Super Micro Computer")
        for text in samples:
            for target in ("MU", "NBIS", "ARM", "KLAC"):
                once = self.mask(text, target)
                self.assertEqual(self.mask(once, target), once, (text, target))

    # ------------------------------------------------------------ normalize / fetch
    def test_normalize_both_forms(self):
        flat_item = MODULE.normalize_item(flat("a-1", "  Title A  ", None))
        self.assertEqual(flat_item, {"item_id": "a-1", "title": "Title A", "summary": "",
                                     "published_at": "2026-11-18T05:00:00Z"})
        nest = MODULE.normalize_item(nested("b-1", "Title B", "Sum B", "2026-11-18T06:07:08Z"))
        self.assertEqual(nest, {"item_id": "b-1", "title": "Title B", "summary": "Sum B",
                                "published_at": "2026-11-18T06:07:08Z"})
        self.assertIsNone(MODULE.normalize_item(nested("c-1", "T", "S", "not a time")))
        self.assertIsNone(MODULE.normalize_item(nested("c-2", "T", "S", "2026-11-18T06:07:08")))
        self.assertIsNone(MODULE.normalize_item({"uuid": "d", "title": "T", "providerPublishTime": "x"}))
        self.assertIsNone(MODULE.normalize_item({"uuid": "", "title": "T", "providerPublishTime": 1}))
        self.assertIsNone(MODULE.normalize_item(flat("e", "   ")))
        self.assertIsNone(MODULE.normalize_item("text"))

    def test_fetch_items_failure_is_none(self):
        self.assertIsNone(MODULE.fetch_items("MU", Fetcher({"MU": RuntimeError("down")})))
        self.assertIsNone(MODULE.fetch_items("MU", Fetcher({"MU": None})))
        self.assertEqual(MODULE.fetch_items("MU", Fetcher({"MU": [{"a": 1}]})), [{"a": 1}])

    # ------------------------------------------------------------ 3. request shape
    def test_request_shape(self):
        code, status, line = self.submit()
        self.assertEqual((code, status), (0, "SUBMITTED"))
        self.assertEqual(line, "llm-news %s SUBMITTED items=2 requests=4 symbols_failed=0" % DAY)
        self.assertEqual(self.factory.batches.calls, ["create"])
        self.assertEqual(self.factory.keys_ok, [True])
        reqs = self.sent()
        self.assertEqual([r["custom_id"] for r in reqs], ["L0001", "S0001", "L0002", "S0002"])
        for req in reqs:
            self.assertEqual(set(req), {"custom_id", "params"})
            params = req["params"]
            self.assertEqual(params["model"], MODEL)
            self.assertEqual(params["max_tokens"], PREREG["model"]["max_tokens"])
            self.assertFalse(FORBIDDEN_PARAM_KEYS & set(params), req["custom_id"])
            self.assertEqual(params["output_config"]["effort"], "low")
            self.assertEqual(len(params["messages"]), 1)
            self.assertEqual(params["messages"][0]["role"], "user")
        label_mu, summary_mu, label_nv, summary_nv = (r["params"] for r in reqs)
        for label in (label_mu, label_nv):
            self.assertEqual(label["system"], PREREG["label_system_prompt"])
            self.assertEqual(label["output_config"]["format"],
                             {"type": "json_schema", "schema": PREREG["label_schema"]})
        mu_text = label_mu["messages"][0]["content"]
        self.assertTrue(mu_text.startswith("Title: [COMPANY] [COMPANY] raises guidance\nSummary: "))
        for needle in ("MU", "Micron", "micron", "NASDAQ"):
            self.assertNotIn(needle, mu_text)
        nv_text = label_nv["messages"][0]["content"]
        for needle in ("Nvidia", "NVIDIA", "NVDA", "Nebius", "http", "example.com"):
            self.assertNotIn(needle, nv_text)
        self.assertIn("[COMPANY]", nv_text)
        self.assertIn("[OTHER]", nv_text)
        for summary in (summary_mu, summary_nv):
            self.assertEqual(summary["system"], MODULE.SUMMARY_SYSTEM)
            self.assertEqual(summary["output_config"], {"effort": "low"})
        self.assertIn("Micron Technology (NASDAQ: MU)", summary_mu["messages"][0]["content"])
        self.assertIn("Nebius Group", summary_nv["messages"][0]["content"])

    # ------------------------------------------------------------ 4. picking
    def test_pick_rules(self):
        self.news.mkdir(parents=True)
        (self.news / "seen.json").write_text(json.dumps({"seen-1": "2026-11-17T19:30:00+09:00"}),
                                             encoding="utf-8")
        long_title = "Micron " + "x" * 294
        self.assertEqual(len(long_title), 301)
        feed = {
            "MU": [
                flat("seen-1", "Already seen item"),
                flat("old-1", "Old item", pub=datetime(2026, 11, 17, 9, 29, 0, tzinfo=timezone.utc)),
                flat("blank-1", "   "),
                flat("nosum-1", "Micron no summary item", None),
                flat("dup-1", "Shared item"),
                flat("long-1", long_title),
                {"uuid": "badtime-1", "title": "Bad time", "providerPublishTime": "yesterday"},
                nested("nest-1", "MU shares climb after upgrade", "Shares moved.", "2026-11-18T07:00:00Z"),
                flat("future-1", "Future item", pub=datetime(2026, 11, 18, 11, 0, 0, tzinfo=timezone.utc)),
            ],
            "NVDA": [flat("dup-1", "Shared item")],
        }
        code, status, _line = self.submit(feed)
        self.assertEqual((code, status), (0, "SUBMITTED"))
        doc = self.batch_doc()
        self.assertEqual([(i["symbol"], i["item_id"]) for i in doc["items"]],
                         [("MU", "nosum-1"), ("MU", "dup-1"), ("MU", "long-1"), ("MU", "nest-1")])
        self.assertEqual(doc["counts"], {"symbols_failed": 0, "skipped": 2, "mask_leak": 0, "items": 4})
        self.assertEqual(len(doc["items"][2]["title"]), 300)
        stamp = NOW.isoformat(timespec="seconds")
        self.assertTrue(all(i["first_seen_at"] == stamp for i in doc["items"]))
        seen = json.loads((self.news / "seen.json").read_text(encoding="utf-8"))
        self.assertEqual(seen["seen-1"], "2026-11-17T19:30:00+09:00")
        for item_id in ("old-1", "nosum-1", "dup-1", "long-1", "nest-1", "future-1"):
            self.assertEqual(seen[item_id], stamp)
        self.assertNotIn("blank-1", seen)
        reqs = {r["custom_id"]: r["params"]["messages"][0]["content"] for r in self.sent()}
        self.assertTrue(reqs["L0001"].endswith("\nSummary: "))
        self.assertEqual(reqs["L0004"], "Title: MU shares climb after upgrade\nSummary: Shares moved.")
        self.assertNotIn("old-1", json.dumps(self.sent()))

    def test_mask_leak_is_not_sent(self):
        real = MODULE.mask_item_text
        state = {"under": 0}

        def leaky(text, target, prereg):
            if "LEAKME" in text and state["under"] == 0:
                state["under"] += 1
                return text  # masks too little once
            return real(text, target, prereg)

        feed = {"MU": [flat("leak-1", "Micron LEAKME item"), flat("ok-1", "MU alone in title")]}
        with mock.patch.object(MODULE, "mask_item_text", side_effect=leaky):
            code, status, _line = self.submit(feed)
        self.assertEqual((code, status), (0, "SUBMITTED"))
        doc = self.batch_doc()
        self.assertEqual(doc["counts"]["mask_leak"], 1)
        self.assertEqual([i["item_id"] for i in doc["items"]], ["ok-1"])
        self.assertNotIn("LEAKME", json.dumps(self.sent()))

    # ------------------------------------------------------------ 5. once per day
    def test_submit_once(self):
        self.assertEqual(self.submit()[:2], (0, "SUBMITTED"))
        self.assertEqual(self.submit()[:2], (0, "ALREADY_DONE"))
        self.assertEqual(self.factory.batches.calls, ["create"])

    def test_started_only_is_unknown(self):
        self.day_dir().mkdir(parents=True)
        (self.day_dir() / "submit-started").write_text("x\n", encoding="utf-8")
        fetcher = Fetcher(basic_feed())
        self.assertEqual(self.submit(fetcher=fetcher)[:2], (12, "SUBMIT_UNKNOWN"))
        self.assertEqual(self.factory.called, 0)
        self.assertEqual(fetcher.calls, [])
        self.assertIn("(SUBMIT_UNKNOWN)", (self.day_dir() / "failed.md").read_text(encoding="utf-8"))

    def test_create_error_never_resends(self):
        self.factory.batches.create_exc = APIStatusError("secret text", 529)
        code, status, _line = self.submit()
        self.assertEqual((code, status), (7, "API_ERROR"))
        failed = (self.day_dir() / "failed.md").read_text(encoding="utf-8")
        self.assertIn("APIStatusError HTTP 529", failed)
        self.assertNotIn("secret text", failed)
        self.assertTrue((self.day_dir() / "submit-started").exists())
        self.assertFalse((self.day_dir() / "batch.json").exists())
        self.factory.batches.create_exc = None
        self.assertEqual(self.submit()[:2], (12, "SUBMIT_UNKNOWN"))
        self.assertEqual(self.factory.batches.calls, ["create"])
        self.assertIn("(API_ERROR)", (self.day_dir() / "failed.md").read_text(encoding="utf-8"))

    def test_create_404_halts(self):
        self.factory.batches.create_exc = APIStatusError("model x not found", 404)
        self.assertEqual(self.submit()[:2], (10, "MODEL_NOT_FOUND"))
        self.assertTrue((self.news / "HALT").exists())
        self.assertIn("(MODEL_NOT_FOUND)", (self.day_dir() / "failed.md").read_text(encoding="utf-8"))
        self.assertEqual(self.submit(day=DAY2, now=NOW2, feed=day2_feed())[:2], (10, "HALTED"))
        self.assertEqual(self.factory.batches.calls, ["create"])

    # ------------------------------------------------------------ 6. nothing new
    def test_no_items_and_nothing_to_collect(self):
        feed = {"MU": [flat("old-1", "Old item", pub=PUB1 - timedelta(days=2))]}
        code, status, line = self.submit(feed)
        self.assertEqual((code, status), (0, "NO_ITEMS"))
        self.assertEqual(self.factory.batches.calls, [])
        self.assertEqual(self.factory.called, 0)
        self.assertEqual(self.batch_doc(), {"schema": "llm-news-batch-1", "day": DAY, "status": "NO_ITEMS",
                                            "items": []})
        self.assertIn("old-1", json.loads((self.news / "seen.json").read_text(encoding="utf-8")))
        self.assertFalse(self.records.exists())
        code, status, line = self.collect()
        self.assertEqual((code, status), (0, "NOTHING_TO_COLLECT"))
        self.assertEqual(line, "llm-news %s NOTHING_TO_COLLECT late=0" % DAY)
        self.assertEqual(self.factory.batches.calls, [])

    def test_all_fetches_failed(self):
        feed = {sym: None for sym in PREREG["universe"]}
        feed["MU"] = RuntimeError("down")
        code, status, line = self.submit(feed)
        self.assertEqual((code, status), (11, "FETCH_FAILED"))
        self.assertEqual(line, "llm-news %s FETCH_FAILED symbols_failed=30" % DAY)
        self.assertIn("(FETCH_FAILED)", (self.day_dir() / "failed.md").read_text(encoding="utf-8"))
        self.assertEqual(self.factory.batches.calls, [])

    def test_some_fetches_failed_are_counted(self):
        feed = basic_feed()
        feed["AMD"] = None
        feed["TSM"] = RuntimeError("down")
        code, status, line = self.submit(feed)
        self.assertEqual(line, "llm-news %s SUBMITTED items=2 requests=4 symbols_failed=2" % DAY)
        self.assertEqual(self.batch_doc()["counts"]["symbols_failed"], 2)

    # ------------------------------------------------------------ 7. budget, key, halt
    def seed_usage(self, cost, pilot="news", ts="2026-11-03T22:00:00+09:00"):
        self.usage.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts_kst": ts, "pilot": pilot, "model": MODEL, "input_tokens": 1,
                                 "output_tokens": 1, "cache_creation_input_tokens": 0,
                                 "cache_read_input_tokens": 0, "batch": True, "cost_usd_est": cost,
                                 "status": "RECEIVED"}) + "\n")

    def test_budget_stop(self):
        self.seed_usage(100.0, pilot="iccheck")
        self.seed_usage(9.0, ts="2026-10-20T22:00:00+09:00")
        self.seed_usage(4.5)
        self.assertEqual(self.submit()[:2], (0, "SUBMITTED"))
        self.seed_usage(0.5)
        code, status, _line = self.submit(day=DAY2, now=NOW2, feed=day2_feed())
        self.assertEqual((code, status), (5, "BUDGET_STOP"))
        self.assertEqual(self.factory.batches.calls, ["create"])
        self.assertIn("(BUDGET_STOP)", (self.day_dir(DAY2) / "failed.md").read_text(encoding="utf-8"))

    def test_budget_unreadable_stops(self):
        self.usage.parent.mkdir(parents=True)
        self.usage.write_text("{broken\n", encoding="utf-8")
        self.assertEqual(self.submit()[:2], (5, "BUDGET_STOP"))
        self.assertEqual(self.factory.batches.calls, [])

    def test_no_key(self):
        code, status, _line = self.submit(key=False)
        self.assertEqual((code, status), (4, "NO_KEY"))
        self.assertEqual(self.factory.called, 0)
        self.assertEqual((self.day_dir() / "failed.md").read_text(encoding="utf-8"),
                         "검토 못 함: 키 없음 (NO_KEY)\n")

    def test_halt_marker(self):
        self.news.mkdir(parents=True)
        (self.news / "HALT").write_text("MODEL_MISMATCH 2026-11-17T22:00:00+09:00\n", encoding="utf-8")
        fetcher = Fetcher(basic_feed())
        self.assertEqual(self.submit(fetcher=fetcher)[:2], (10, "HALTED"))
        self.assertEqual(fetcher.calls, [])
        self.assertEqual(self.factory.called, 0)
        self.assertFalse(self.day_dir().exists())

    # ------------------------------------------------------------ 8. normal collect
    def test_collect_ok(self):
        self.factory.batches.usage = usage_ns(inp=60000, out=300)
        self.assertEqual(self.submit()[:2], (0, "SUBMITTED"))
        lines = self.record_lines()
        self.assertEqual(len(lines), 1)
        header = json.loads(lines[0])
        self.assertEqual(header, {"schema": "llm-news-records-1", "start_day": DAY,
                                  "prereg_sha256": MODULE.PREREG_SHA256, "prev_sha256": ""})
        code, status, line = self.collect()
        self.assertEqual((code, status), (0, "OK"))
        self.assertEqual(line, "llm-news %s OK labels=2 summaries=2 errors=0 dropped=0 late=0" % DAY)
        lines = self.assert_chain()
        self.assertEqual(len(lines), 3)
        doc = self.batch_doc()
        for raw, item in zip(lines[1:], doc["items"]):
            rec = json.loads(raw)
            self.assertEqual(list(rec.keys()), PREREG["record"]["fields"])
            self.assertEqual(rec["symbol"], item["symbol"])
            self.assertEqual(rec["item_id"], item["item_id"])
            self.assertEqual(rec["published_at"], item["published_at"])
            self.assertEqual(rec["first_seen_at"], NOW.isoformat(timespec="seconds"))
            self.assertEqual(rec["submitted_at"], doc["submitted_at"])
            self.assertEqual(rec["received_at"], "2026-11-18T22:00:00+09:00")
            self.assertEqual(rec["label"], "good")
            self.assertEqual(rec["reason"], REASON)
            self.assertEqual(rec["model"], MODEL)
        self.assertEqual([json.loads(x)["symbol"] for x in lines[1:]], ["MU", "NVDA"])
        digest = (self.day_dir() / "digest.md").read_text(encoding="utf-8")
        self.assertTrue(digest.startswith("# 뉴스 요약 %s\n" % DAY))
        self.assertIn("## MU", digest)
        self.assertLess(digest.index("## MU"), digest.index("## NVDA"))
        self.assertIn("- Micron Technology (NASDAQ: MU) raises guidance", digest)
        self.assertIn("  첫째 줄 사실 S0001", digest)
        self.assertIn("  셋째 줄 사실", digest)
        for word in ("good", "bad", "unknown", "label", REASON, "Contract"):
            self.assertNotIn(word, digest)
        self.assertTrue(digest.endswith("표시 전용: 매매 판단·주문과 연결하지 않는다\n"))
        collected = json.loads((self.day_dir() / "collected.json").read_text(encoding="utf-8"))
        self.assertEqual(collected, {"schema": "llm-news-collected-1", "day": DAY,
                                     "received_at": "2026-11-18T22:00:00+09:00", "labels": 2,
                                     "summaries": 2, "errors": 0, "dropped": 0})
        usage = self.usage_lines()
        self.assertEqual(len(usage), 1)
        u = json.loads(usage[0])
        self.assertEqual(tuple(u.keys()), COMMON.USAGE_KEYS)
        self.assertEqual(u["ts_kst"], "2026-11-18T22:00:00+09:00")
        self.assertEqual(u["pilot"], "news")
        self.assertEqual(u["model"], MODEL)
        self.assertIs(u["batch"], True)
        self.assertEqual(u["status"], "RECEIVED")
        self.assertEqual(u["input_tokens"], 240000)
        per_message = {"input_tokens": 60000, "output_tokens": 300}
        expected = 4 * MODULE.estimate_cost(MODEL, per_message, batch=True)
        self.assertAlmostEqual(u["cost_usd_est"], expected, places=12)
        lumped = MODULE.estimate_cost(MODEL, {"input_tokens": 240000, "output_tokens": 1200}, batch=True)
        self.assertNotAlmostEqual(u["cost_usd_est"], lumped, places=6)
        self.assertTrue((self.day_dir() / "usage-done").exists())
        self.assertAlmostEqual(MODULE.month_spend(self.root, "news", "2026-11"), expected, places=12)
        self.assertFalse((self.day_dir() / "failed.md").exists())

    # ------------------------------------------------------------ 9. pending, done
    def test_pending_then_ok_then_done(self):
        self.submit()
        self.factory.batches.status["msgbatch_1"] = "in_progress"
        before = self.all_files()
        code, status, line = self.collect()
        self.assertEqual((code, status), (0, "PENDING"))
        self.assertEqual(line, "llm-news %s PENDING late=0" % DAY)
        self.assertEqual(self.all_files(), before)
        self.assertNotIn("results", self.factory.batches.calls)
        self.factory.batches.status["msgbatch_1"] = "ended"
        self.assertEqual(self.collect(now=COLLECT_AT + timedelta(hours=1))[:2], (0, "OK"))
        n_lines = len(self.record_lines())
        self.assertEqual(self.collect()[:2], (0, "ALREADY_DONE"))
        self.assertEqual(len(self.record_lines()), n_lines)
        self.assertEqual(self.factory.batches.calls.count("results"), 1)

    # ------------------------------------------------------------ 10. late receipt
    def test_late_receipt_is_kept(self):
        self.submit()
        late = datetime(2026, 11, 18, 23, 40, 0, tzinfo=MODULE.KST)
        self.assertEqual(self.collect(now=late)[:2], (0, "OK"))
        lines = self.record_lines()
        self.assertEqual(len(lines), 3)
        for raw in lines[1:]:
            self.assertEqual(json.loads(raw)["received_at"], "2026-11-18T23:40:00+09:00")

    # ------------------------------------------------------------ 11. two days, late collection
    def test_two_days_and_late_collection(self):
        self.assertEqual(self.submit()[:2], (0, "SUBMITTED"))
        self.factory.batches.status["msgbatch_1"] = "in_progress"
        self.assertEqual(self.collect()[:2], (0, "PENDING"))
        self.assertEqual(self.collect(now=COLLECT_AT + timedelta(hours=1))[:2], (0, "PENDING"))
        self.assertEqual(self.submit(feed=day2_feed(), day=DAY2, now=NOW2)[:2], (0, "SUBMITTED"))

        old_day = "2026-11-15"  # four days before DAY2: outside the late window
        old_dir = self.news / old_day
        old_dir.mkdir(parents=True)
        old_batch = {"schema": "llm-news-batch-1", "day": old_day, "status": "SUBMITTED",
                     "batch_id": "msgbatch_old", "submitted_at": "2026-11-15T19:30:00+09:00",
                     "prereg_sha256": MODULE.PREREG_SHA256, "counts": {}, "items": []}
        (old_dir / "batch.json").write_text(json.dumps(old_batch), encoding="utf-8")
        old_before = {p.name: p.read_bytes() for p in old_dir.iterdir()}

        self.factory.batches.status["msgbatch_1"] = "ended"
        code, status, line = self.collect(day=DAY2, now=COLLECT2_AT)
        self.assertEqual((code, status), (0, "OK"))
        self.assertTrue(line.endswith(" late=1"), line)
        lines = self.assert_chain()
        self.assertEqual(len(lines), 5)
        self.assertEqual(sum(1 for x in lines if '"schema":"llm-news-records-1"' in x), 1)
        self.assertEqual(json.loads(lines[0])["start_day"], DAY)
        recs = [json.loads(x) for x in lines[1:]]
        self.assertEqual([r["item_id"] for r in recs], ["mu-1", "nv-1", "mu-2", "nv-2"])
        self.assertEqual([r["received_at"] for r in recs], ["2026-11-19T22:00:00+09:00"] * 4)
        self.assertEqual(recs[0]["submitted_at"], "2026-11-18T19:30:00+09:00")
        self.assertEqual(recs[2]["submitted_at"], "2026-11-19T19:30:00+09:00")
        self.assertTrue((self.day_dir(DAY) / "collected.json").exists())
        self.assertNotIn("msgbatch_old", self.factory.batches.retrieved)
        self.assertEqual({p.name: p.read_bytes() for p in old_dir.iterdir()}, old_before)
        self.assertEqual(len(self.usage_lines()), 2)

    # ------------------------------------------------------------ 12. broken record
    def test_broken_chain_halts(self):
        self.submit()
        self.collect()
        self.submit(feed=day2_feed(), day=DAY2, now=NOW2)
        lines = self.record_lines()
        lines[1] = lines[1].replace('"label":"good"', '"label":"gooe"')
        self.records.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        tampered = self.records.read_bytes()
        code, status, _line = self.collect(day=DAY2, now=COLLECT2_AT)
        self.assertEqual((code, status), (10, "RECORDS_BROKEN"))
        self.assertEqual(self.records.read_bytes(), tampered)
        self.assertTrue((self.news / "HALT").exists())
        self.assertFalse((self.day_dir(DAY2) / "collected.json").exists())
        self.assertIn("(RECORDS_BROKEN)", (self.day_dir(DAY2) / "failed.md").read_text(encoding="utf-8"))

    def test_missing_record_file_is_broken(self):
        self.submit()
        self.records.unlink()
        self.assertEqual(self.collect()[:2], (10, "RECORDS_BROKEN"))
        self.assertFalse(self.records.exists())

    # ------------------------------------------------------------ 13. model checks
    def test_model_mismatch_halts_but_usage_is_kept(self):
        self.submit()
        self.factory.batches.override["S0002"] = succeeded(
            "S0002", message("text", model="claude-haiku-5-5-latest"))
        before = self.records.read_bytes()
        self.assertEqual(self.collect()[:2], (10, "MODEL_MISMATCH"))
        self.assertEqual(self.records.read_bytes(), before)
        self.assertTrue((self.news / "HALT").exists())
        self.assertEqual(len(self.usage_lines()), 1)
        self.assertFalse((self.day_dir() / "collected.json").exists())
        self.assertFalse((self.day_dir() / "digest.md").exists())
        self.assertEqual(self.submit(day=DAY2, now=NOW2, feed=day2_feed())[:2], (10, "HALTED"))

    def test_errored_not_found_halts(self):
        self.submit()
        self.factory.batches.override["L0001"] = errored("L0001", "not_found_error")
        before = self.records.read_bytes()
        self.assertEqual(self.collect()[:2], (10, "MODEL_NOT_FOUND"))
        self.assertEqual(self.records.read_bytes(), before)
        self.assertTrue((self.news / "HALT").exists())

    def test_dated_model_passes(self):
        self.factory.batches.model = "claude-haiku-5-5-20261001"
        self.submit()
        self.assertEqual(self.collect()[:2], (0, "OK"))
        self.assertEqual(json.loads(self.record_lines()[1])["model"], "claude-haiku-5-5-20261001")

    # ------------------------------------------------------------ 14. item-level failures
    def test_item_failures_are_dropped_and_counted(self):
        feed = {"MU": [flat("a-%d" % i, "Item %d" % i) for i in range(1, 5)]}
        self.submit(feed)
        b = self.factory.batches
        b.override["L0001"] = errored("L0001", "invalid_request_error")
        b.override["L0002"] = succeeded("L0002", message(json.dumps({"label": "maybe", "reason": "x"})))
        b.override["L0003"] = succeeded("L0003", message("", stop="refusal"))
        b.override["L0004"] = succeeded("L0004", message(json.dumps({"label": "bad", "reason": "r" * 500})))
        code, status, line = self.collect()
        self.assertEqual((code, status), (0, "OK"))
        self.assertEqual(line, "llm-news %s OK labels=1 summaries=4 errors=1 dropped=2 late=0" % DAY)
        lines = self.assert_chain()
        self.assertEqual(len(lines), 2)
        rec = json.loads(lines[1])
        self.assertEqual((rec["item_id"], rec["label"]), ("a-4", "bad"))
        self.assertEqual(rec["reason"], "r" * 200)

    def test_missing_result_counts_as_error(self):
        self.submit()
        self.factory.batches.override["S0001"] = None
        self.factory.batches.override["X9"] = None
        code, status, line = self.collect()
        self.assertEqual(line, "llm-news %s OK labels=2 summaries=1 errors=1 dropped=0 late=0" % DAY)
        digest = (self.day_dir() / "digest.md").read_text(encoding="utf-8")
        self.assertIn("- Micron Technology (NASDAQ: MU) raises guidance\n\n## NVDA", digest)

    # ------------------------------------------------------------ 15. rerun safety
    def test_rerun_after_lost_marker(self):
        self.submit()
        self.collect()
        records_before = self.records.read_bytes()
        (self.day_dir() / "collected.json").unlink()
        self.assertEqual(self.collect(now=COLLECT_AT + timedelta(hours=1))[:2], (0, "OK"))
        self.assertEqual(self.records.read_bytes(), records_before)
        self.assertEqual(len(self.usage_lines()), 1)

    # ------------------------------------------------------------ 15-1. other collect paths
    def test_collect_no_batch(self):
        code, status, line = self.collect()
        self.assertEqual((code, status, line), (0, "NO_BATCH", "llm-news %s NO_BATCH late=0" % DAY))
        self.assertFalse((self.day_dir() / "failed.md").exists())
        self.assertEqual(self.factory.called, 0)

    def test_collect_no_key(self):
        self.submit()
        self.assertEqual(self.collect(key=False)[:2], (4, "NO_KEY"))
        self.assertIn("(NO_KEY)", (self.day_dir() / "failed.md").read_text(encoding="utf-8"))
        self.assertNotIn("retrieve", self.factory.batches.calls)

    def test_collect_prereg_sha_differs(self):
        self.submit()
        doc = self.batch_doc()
        doc["prereg_sha256"] = "0" * 64
        (self.day_dir() / "batch.json").write_text(json.dumps(doc), encoding="utf-8")
        self.assertEqual(self.collect()[:2], (10, "PREREG_MISMATCH"))
        self.assertTrue((self.news / "HALT").exists())
        self.assertNotIn("retrieve", self.factory.batches.calls)

    def test_collect_retrieve_error(self):
        self.submit()
        self.factory.batches.retrieve_exc = APIStatusError("secret text", 500)
        records_before = self.records.read_bytes()
        self.assertEqual(self.collect()[:2], (7, "API_ERROR"))
        self.assertEqual(self.records.read_bytes(), records_before)
        self.assertEqual(self.usage_lines(), [])
        failed = (self.day_dir() / "failed.md").read_text(encoding="utf-8")
        self.assertIn("(API_ERROR)", failed)
        self.assertNotIn("secret text", failed)
        self.factory.batches.retrieve_exc = None
        self.assertEqual(self.collect()[:2], (0, "OK"))
        self.assertFalse((self.day_dir() / "failed.md").exists())

    # ------------------------------------------------------------ 15-2. dry run
    def test_submit_dry_run_writes_nothing(self):
        code, status, line = self.submit(key=False, dry_run=True)
        self.assertEqual((code, status), (0, "DRY_RUN"))
        self.assertEqual(line, "llm-news %s DRY_RUN items=2 symbols_failed=0" % DAY)
        self.assertFalse(self.news.exists())
        self.assertFalse((self.root / "workspace").exists())
        self.assertEqual(self.factory.called, 0)

    def test_submit_dry_run_bad_prereg_no_halt(self):
        self.prereg_path.write_bytes(PREREG_SRC.read_bytes().replace(b"Nebius", b"Nebiux", 1))
        code, status, _line = self.submit(dry_run=True)
        self.assertEqual((code, status), (10, "PREREG_MISMATCH"))
        self.assertFalse((self.root / "workspace").exists())

    def test_collect_dry_run(self):
        self.submit()
        before = self.all_files()
        code, status, line = self.collect(dry_run=True, key=False)
        self.assertEqual((code, status, line), (0, "DRY_RUN", "llm-news %s DRY_RUN" % DAY))
        self.assertEqual(self.all_files(), before)
        self.assertEqual(self.factory.batches.calls, ["create"])

    # ------------------------------------------------------------ 16. key and paths
    def test_no_key_value_and_writes_under_llm_only(self):
        self.submit()
        self.collect()
        self.assert_no_key_anywhere()
        for rel in self.all_files():
            if rel == PREREG_REL:
                continue
            self.assertTrue(rel.startswith("workspace/outputs/llm/"), rel)

    def test_script_source_contract(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(text.isascii())
        for word in ("environ", "zoneinfo", "subprocess", "import requests", "urllib", "fallbacks",
                     "advisor", "socket", "http.client", "auto_core", "kiwoom"):
            self.assertNotIn(word, text, word)

    # ------------------------------------------------------------ pinned constants
    def test_exit_codes_and_korean_text(self):
        for name, value in ICCHECK.EXIT_CODES.items():
            if name in MODULE.EXIT_CODES:
                self.assertEqual(MODULE.EXIT_CODES[name], value, name)
        expected = {"SUBMITTED": 0, "NO_ITEMS": 0, "PENDING": 0, "NO_BATCH": 0, "NOTHING_TO_COLLECT": 0,
                    "DRY_RUN": 0, "UNEXPECTED": 1, "HALTED": 10, "PREREG_MISMATCH": 10,
                    "MODEL_MISMATCH": 10, "MODEL_NOT_FOUND": 10, "RECORDS_BROKEN": 10,
                    "FETCH_FAILED": 11, "SUBMIT_UNKNOWN": 12}
        for name, value in expected.items():
            self.assertEqual(MODULE.EXIT_CODES[name], value, name)
        self.assertEqual(MODULE.SUMMARY_SYSTEM,
                         "뉴스 기사 하나의 제목과 요약이 주어진다. 투자 권유·등급·점수 없이 사실만 한국어 3줄로 쓴다.")
        self.assertEqual(MODULE.DIGEST_TITLE, "# 뉴스 요약 %s")
        self.assertEqual(MODULE.DIGEST_FOOTER, "표시 전용: 매매 판단·주문과 연결하지 않는다")
        self.assertEqual(MODULE.REASON_KO, {
            "prereg": "사전 등록 불일치",
            "no_key": "키 없음",
            "usage_unreadable": "사용 기록을 읽을 수 없음",
            "budget_spent": "이달 예산을 다 씀",
            "fetch_failed": "기사 가져오기 실패",
            "submit_unknown": "제출 여부 모름",
            "call_failed": "API 호출 실패 ",
            "bad_shape": "응답 형식 다름",
            "model_not_found": "모델 없음",
            "model_mismatch": "응답 모델 다름",
            "records_broken": "기록 사슬 깨짐",
            "unexpected": "예상 못 한 오류 (%s)",
        })

    # ------------------------------------------------------------ 17. main
    def run_main(self, argv, **kwargs):
        with self.env(True):
            return MODULE.main(argv, repo_root=self.root, client_factory=self.factory,
                               fetcher=kwargs.get("fetcher", Fetcher(basic_feed())), now=kwargs.get("now", NOW))

    def test_main_requires_phase(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(["--day", DAY])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_main_submit_and_collect_lines(self):
        self.assertEqual(self.run_main(["--phase", "submit", "--day", DAY]), 0)
        self.assertEqual(self.out.getvalue().splitlines()[-1],
                         "llm-news %s SUBMITTED items=2 requests=4 symbols_failed=0" % DAY)
        self.assertEqual(self.run_main(["--phase", "collect"], now=COLLECT_AT), 0)
        last = self.out.getvalue().splitlines()[-1]
        self.assertEqual(last, "llm-news %s OK labels=2 summaries=2 errors=0 dropped=0 late=0" % DAY)
        self.assertTrue(last.isascii() and len(last) <= 200)

    def test_main_unexpected(self):
        with mock.patch.object(MODULE, "run_submit", side_effect=RuntimeError("secret text")):
            code = self.run_main(["--phase", "submit", "--day", DAY])
        self.assertEqual(code, 1)
        self.assertEqual(self.out.getvalue().splitlines()[-1], "llm-news %s UNEXPECTED" % DAY)
        self.assertNotIn("secret text", self.out.getvalue() + self.err.getvalue())
        failed = (self.day_dir() / "failed.md").read_text(encoding="utf-8")
        self.assertEqual(failed, "검토 못 함: 예상 못 한 오류 (RuntimeError) (UNEXPECTED)\n")

    def test_main_month_spend_error_is_budget_stop(self):
        with mock.patch.object(MODULE, "month_spend", side_effect=ValueError("bad line")):
            code = self.run_main(["--phase", "submit", "--day", DAY])
        self.assertEqual(code, 5)
        self.assertEqual(self.out.getvalue().splitlines()[-1], "llm-news %s BUDGET_STOP" % DAY)
        self.assertEqual(self.factory.batches.calls, [])


if __name__ == "__main__":
    unittest.main()
