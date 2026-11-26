import contextlib
import copy
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
SCRIPT = SCRIPT_DIR / "llm_pilot_srccheck.py"
SPEC = importlib.util.spec_from_file_location("llm_pilot_srccheck", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
PDFCMP_SPEC = importlib.util.spec_from_file_location("llm_pilot_pdfcmp_for_srccheck", SCRIPT_DIR / "llm_pilot_pdfcmp.py")
PDFCMP = importlib.util.module_from_spec(PDFCMP_SPEC)
assert PDFCMP_SPEC.loader is not None
PDFCMP_SPEC.loader.exec_module(PDFCMP)
RUNNER_SPEC = importlib.util.spec_from_file_location("llm_runner_for_srccheck", SCRIPT_DIR / "llm_runner.py")
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)
import llm_pilot_common as COMMON  # noqa: E402

PROMPT = REPO / "docs" / "claude" / "llm-srccheck-builder-prompt.md"
FAKE_KEY = "fake-key-SRCCHECK-4K8W"
MODEL = MODULE.MODELS["srccheck"]
DAY = "2026-11-26"
DAY2 = "2026-11-27"
NOW = datetime(2026, 11, 26, 8, 10, 0, tzinfo=MODULE.KST)
NOW2 = datetime(2026, 11, 27, 8, 10, 0, tzinfo=MODULE.KST)
COLLECT_AT = datetime(2026, 11, 26, 10, 10, 0, tzinfo=MODULE.KST)
COLLECT_AT2 = datetime(2026, 11, 27, 10, 10, 0, tzinfo=MODULE.KST)

URL_FACT = "https://investors.micron.com/news-releases/fact-a"
URL_EARN = "https://investors.micron.com/events/q1-2027"
URL_DELL_NA = "https://investors.delltechnologies.com/news/not-announced"
URL_SEC_8K = "https://www.sec.gov/Archives/edgar/data/1571996/000157199626000101/dell-8k.htm"
URL_SEC_10Q = "https://www.sec.gov/Archives/edgar/data/723125/000072312526000045/mu-20261127.htm"
KEY_8K = "sec:0001571996-26-000101"
KEY_10Q = "sec:0000723125-26-000045"
KEY_BAD_DOC = "sec:0000723125-26-000077"

CLAIM_FACT = "MU 공식 사실(종류 guidance, 사건 세션 2026-11-24, 발표 시각 2026-11-24T21:05:00+00:00): 가이던스 상향"
CLAIM_EARN = "MU의 실적 발표일은 2026-12-17(장 마감 후)이다 (출처 종류 COMPANY_IR)"
CLAIM_8K = "Dell Technologies Inc.(DELL)의 8-K 서류이고, 보고 기준일 2026-11-17, 항목 2.02, 9.01이다"
CLAIM_10Q = "Micron Technology(MU)의 10-Q 서류이고, 보고 기준일 2026-11-27이다"

EXPECTED_HOSTS = (
    "www.sec.gov", "www.federalreserve.gov", "www.bls.gov", "www.bea.gov", "home.treasury.gov",
    "fred.stlouisfed.org", "investors.delltechnologies.com", "investors.quantaservices.com",
    "investor.lumentum.com", "investor.marvell.com", "www.bloomenergy.com", "investor.bloomenergy.com",
    "investors.micron.com", "ir.crowdstrike.com", "nebius.com",
)
EXPECTED_INSTRUCTION = (
    "아래 URL 하나만 web_fetch로 한 번 연다. 다른 URL은 열지 않는다. 주장이 원문과 맞는지 본다. "
    "답은 두 줄로만: `판정: 맞음|틀림|미정|확인 불가` / `근거: <원문 문장 그대로 한 줄>`. "
    "주장 일부만 원문에 있으면 `판정: 미정`. 열 수 없거나 원문에 해당 내용이 없으면 `판정: 확인 불가`."
)
SENTINEL = "SENTINEL_NOT_SENT"


# ---------------------------------------------------------------- fixtures

def fact(n, url, symbol="MU", summary="가이던스 상향"):
    return {
        "fact_id": "%s_FACT_ID_%d" % (SENTINEL, n),
        "symbol": symbol,
        "direction": "+",
        "kind": "guidance",
        "card_trigger_ids": ["%s_TRIGGER" % SENTINEL],
        "event_session": "2026-11-24",
        "announced_at": "2026-11-24T21:05:00+00:00",
        "source_kind": "%s_FACT_SOURCE_KIND" % SENTINEL,
        "source_url": url,
        "criterion_a": True,
        "root_thesis_damage": False,
        "summary_ko": summary,
    }


def research_record(facts=None, earnings=None):
    return {
        "schema_version": "auto-core-research-record-1.0",
        "record_day_kst": DAY,
        "evaluation_session": "2026-11-25",
        "written_at": "2026-11-26T06:40:00+09:00",
        "writer": "%s_WRITER" % SENTINEL,
        "earnings": earnings if earnings is not None else {
            "MU": {
                "status": "VERIFIED",
                "announcement_session": "2026-12-17",
                "timing": "AFTER_CLOSE",
                "source_kind": "COMPANY_IR",
                "source_url": URL_EARN,
                "checked_at": "%s_CHECKED_AT" % SENTINEL,
            },
            "DELL": {
                "status": "NOT_ANNOUNCED",
                "source_kind": "COMPANY_IR",
                "source_url": URL_DELL_NA,
            },
        },
        "official_facts": facts if facts is not None else [fact(1, URL_FACT)],
        "integrated_check_run": {"note": "%s_RUN" % SENTINEL},
        "order_authority": "%s_ORDER" % SENTINEL,
        "quantity_authority": "%s_QUANTITY" % SENTINEL,
    }


def sec_event(form, accession, cik, doc, ticker, company, filing_date, report_date=None, items=()):
    return {
        "event_id": "sec-%s" % ("0" * 24),
        "source_authority": "OFFICIAL_SEC",
        "source_name": "SEC_EDGAR_COMPANY_SUBMISSIONS",
        "source_url": "https://data.example.invalid/submissions/%s_SUBMISSIONS.json" % SENTINEL,
        "ticker": ticker,
        "cik": cik,
        "company_name": company,
        "accession_number": accession,
        "form": form,
        "filing_date": filing_date,
        "accepted_at": "%s_ACCEPTED" % SENTINEL,
        "report_date": report_date,
        "primary_document": doc,
        "items_if_available": list(items),
        "event_type": "CURRENT_REPORT",
        "materiality": "HIGH",
        "portfolio_relevance": "HOLDING",
        "root_theses": ["%s_THESIS" % SENTINEL],
        "verification_status": "OFFICIAL_SOURCE_VERIFIED",
        "interpretation_status": "DERIVED_RULE_BASED",
        "decision_impact": "WATCH",
        "retrieved_at": "2026-11-25T12:05:00+09:00",
        "raw_source_sha256": "a" * 64,
        "underlying_company_relevance": True,
        "leveraged_vehicle": None,
        "derived_relation_status": None,
    }


def default_events():
    return [
        sec_event("10-Q", "0000723125-26-000045", "0000723125", "mu-20261127.htm", "MU",
                  "Micron Technology", "2026-11-20", report_date="2026-11-27"),
        sec_event("8-K", "0001571996-26-000101", "0001571996", "dell-8k.htm", "DELL",
                  "Dell Technologies Inc.", "2026-11-18", report_date="2026-11-17", items=("2.02", "9.01")),
        sec_event("4", "0000723125-26-000050", "0000723125", "form4.xml", "MU", "Micron Technology",
                  "2026-11-21"),
        sec_event("144", "0000723125-26-000051", "0000723125", "form144.xml", "MU", "Micron Technology",
                  "2026-11-21"),
        sec_event("8-K", "0000723125-26-000077", "0000723125", "sub/doc.htm", "MU", "Micron Technology",
                  "2026-11-22"),
    ]


def sec_doc(events):
    return {
        "schema_version": "0.1",
        "pipeline_version": "0.1",
        "decision_as_of": "2026-11-25T12:00:00+09:00",
        "lookback_days": 7,
        "ownership_coverage": "%s_COVERAGE" % SENTINEL,
        "portfolio_context": {"status": "%s_PORTFOLIO" % SENTINEL, "as_of": None, "source_path": None,
                              "source_sha256": None},
        "deferred_symbols": {"XYZ": "%s_DEFERRED" % SENTINEL},
        "events": events,
    }


# ---------------------------------------------------------------- fake API

def usage_ns(inp=25000, out=400):
    return SimpleNamespace(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=0,
                           cache_read_input_tokens=None)


def evidence_for(url):
    return "The original page at %s states this exact fact." % url.rsplit("/", 1)[-1]


def fetch_ok(url):
    return SimpleNamespace(type="web_fetch_tool_result", tool_use_id="srvtoolu_1",
                           content=SimpleNamespace(type="web_fetch_result", url=url,
                                                   content=SimpleNamespace(type="document")))


def fetch_error(code="url_not_accessible"):
    return SimpleNamespace(type="web_fetch_tool_result", tool_use_id="srvtoolu_1",
                           content=SimpleNamespace(type="web_fetch_tool_error", error_code=code))


def make_message(url, verdict="맞음", fetch="ok", cited=True, text=None, model=MODEL, stop="end_turn",
                 fetched_url=None):
    content = [SimpleNamespace(type="server_tool_use", name="web_fetch", input={"url": url})]
    if fetch == "ok":
        content.append(fetch_ok(fetched_url or url))
    elif fetch == "error":
        content.append(fetch_error())
    ev = evidence_for(url)
    body = text if text is not None else "판정: %s\n근거: %s" % (verdict, ev)
    citations = None
    if cited is True:
        citations = [SimpleNamespace(type="char_location", cited_text=ev)]
    elif isinstance(cited, str):
        citations = [SimpleNamespace(type="char_location", cited_text=cited)]
    content.append(SimpleNamespace(type="text", text=body, citations=citations))
    return SimpleNamespace(model=model, stop_reason=stop, content=content, usage=usage_ns())


def succeeded(cid, msg):
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=msg))


def other(cid, kind):
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type=kind))


_URL_IN_TEXT = re.compile(r"^URL: (\S+)$", re.MULTILINE)


def request_url(req):
    return _URL_IN_TEXT.search(req["params"]["messages"][0]["content"][0]["text"]).group(1)


class APIStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class FakeBatches:
    def __init__(self):
        self.created = []
        self.calls = []
        self.create_exc = None
        self.status = "ended"
        self.override = {}  # custom_id -> callable(url) -> entry or None

    def create(self, requests):
        self.calls.append("create")
        if self.create_exc is not None:
            raise self.create_exc
        self.created.append(copy.deepcopy(requests))
        return SimpleNamespace(id="msgbatch_%d" % len(self.created), processing_status="in_progress")

    def retrieve(self, batch_id):
        self.calls.append("retrieve")
        status = self.status(batch_id) if callable(self.status) else self.status
        return SimpleNamespace(id=batch_id, processing_status=status)

    def results(self, batch_id):
        self.calls.append("results")
        requests = self.created[int(batch_id.split("_")[1]) - 1]
        out = []
        for req in reversed(requests):  # results come in no particular order
            cid = req["custom_id"]
            url = request_url(req)
            if cid in self.override:
                entry = self.override[cid](url)
                if entry is not None:
                    out.append(entry)
                continue
            out.append(succeeded(cid, make_message(url)))
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


# ---------------------------------------------------------------- tests

class SrccheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.base = self.root / "workspace" / "outputs" / "llm" / "srccheck"
        self.usage = self.root / "workspace" / "outputs" / "llm" / "usage.jsonl"
        self.out = io.StringIO()
        self.err = io.StringIO()
        self.factory = Factory()

    def tearDown(self):
        self.tmp.cleanup()

    # -- fixture writers
    def write_record(self, record=None, day=DAY):
        path = self.root / "workspace" / "outputs" / "research-records" / day / "research-record.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record if record is not None else research_record(), ensure_ascii=False),
                        encoding="utf-8")
        return path

    def write_sec(self, events=None, day=DAY, run="20261126T120000", raw=None):
        path = self.root / "workspace" / "outputs" / "official-event-intake" / "sec" / day / run / "normalized-events.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            path.write_text(raw, encoding="utf-8")
        else:
            path.write_text(json.dumps(sec_doc(events if events is not None else default_events())),
                            encoding="utf-8")
        return path

    def write_default(self):
        self.write_record()
        self.write_sec()

    # -- runners
    @contextlib.contextmanager
    def env(self, key=True):
        with mock.patch.dict(os.environ, {COMMON.KEY_ENV: FAKE_KEY} if key else {}):
            if not key:
                os.environ.pop(COMMON.KEY_ENV, None)
            with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
                yield

    def submit(self, day=DAY, now=NOW, key=True, dry_run=False):
        with self.env(key):
            return MODULE.run_submit(day, repo_root=self.root, client_factory=self.factory, now=now,
                                     dry_run=dry_run)

    def collect(self, day=DAY, now=COLLECT_AT, key=True, dry_run=False):
        with self.env(key):
            return MODULE.run_collect(day, repo_root=self.root, client_factory=self.factory, now=now,
                                      dry_run=dry_run)

    def main(self, argv, key=True, now=NOW):
        with self.env(key):
            return MODULE.main(argv, repo_root=self.root, client_factory=self.factory, now=now)

    def targets(self, day=DAY):
        return MODULE.collect_targets(self.root, day)

    def sent(self, batch=0):
        return self.factory.batches.created[batch]

    def checks(self, day=DAY):
        return json.loads((self.base / day / "checks.json").read_text(encoding="utf-8"))

    def rows_by_cid(self, day=DAY):
        return {row["custom_id"]: row for row in self.checks(day)["rows"]}

    def lines(self, path):
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def all_files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def submitted_collect(self, **override):
        self.write_default()
        _code, status, _ = self.submit()
        self.assertEqual("SUBMITTED", status)
        self.factory.batches.override.update(override)
        return self.collect()

    # ------------------------------------------------------------ targets
    def test_targets_default_order_fields_and_claims(self):
        self.write_default()
        targets, skipped = self.targets()
        self.assertEqual([URL_FACT, URL_EARN, KEY_8K, KEY_10Q], [t["key"] for t in targets])
        self.assertEqual([URL_FACT, URL_EARN, URL_SEC_8K, URL_SEC_10Q], [t["url"] for t in targets])
        self.assertEqual(["a", "a", "b", "b"], [t["source"] for t in targets])
        self.assertEqual([CLAIM_FACT, CLAIM_EARN, CLAIM_8K, CLAIM_10Q], [t["claim"] for t in targets])
        self.assertEqual([{"key": KEY_BAD_DOC, "reason": "BAD_SEC_FIELDS"}], skipped)
        # only the allowed fields are kept for the claim
        self.assertEqual({"symbol", "kind", "event_session", "announced_at", "summary_ko"},
                         set(targets[0]["fields"]))
        self.assertEqual({"symbol", "announcement_session", "timing", "source_kind"}, set(targets[1]["fields"]))
        self.assertEqual({"ticker", "company_name", "form", "report_date", "items"}, set(targets[2]["fields"]))
        self.assertNotIn(URL_DELL_NA, [t["url"] for t in targets])  # NOT_ANNOUNCED is left out

    def test_targets_verified_only_and_timing_optional(self):
        earnings = {
            "AAA": {"status": "VERIFIED", "announcement_session": "2026-12-01", "source_kind": "SEC_FILING",
                    "source_url": "https://investor.marvell.com/news/aaa"},
            "BBB": {"status": "NOT_ANNOUNCED", "source_kind": "COMPANY_IR",
                    "source_url": "https://investor.marvell.com/news/bbb"},
            "CCC": {"status": "VERIFIED", "announcement_session": "2026-12-02", "timing": "BEFORE_OPEN",
                    "source_kind": "COMPANY_IR"},
            "DDD": {"status": "PENDING", "announcement_session": "2026-12-03", "source_kind": "COMPANY_IR",
                    "source_url": "https://investor.marvell.com/news/ddd"},
            "EEE": {"status": "VERIFIED", "announcement_session": "2026-12-04", "timing": "BEFORE_OPEN",
                    "source_kind": "COMPANY_IR", "source_url": "https://investor.marvell.com/news/eee"},
        }
        self.write_record(research_record(facts=[], earnings=earnings))
        targets, skipped = self.targets()
        self.assertEqual(["https://investor.marvell.com/news/aaa", "https://investor.marvell.com/news/eee"],
                         [t["url"] for t in targets])
        self.assertEqual("AAA의 실적 발표일은 2026-12-01이다 (출처 종류 SEC_FILING)", targets[0]["claim"])
        self.assertEqual("EEE의 실적 발표일은 2026-12-04(장 시작 전)이다 (출처 종류 COMPANY_IR)", targets[1]["claim"])
        self.assertEqual([], skipped)

    def test_targets_url_rules_in_collection(self):
        bad = [
            ("https://investors.delltechnologies.com/", "ROOT_PAGE"),
            ("https://investors.delltechnologies.com", "ROOT_PAGE"),
            ("https://www.globenewswire.com/news-release/2026/11/24/x.html", "HOST_NOT_ALLOWED"),
            ("https://investor.marvell.com/rss/news", "BLOCKED_PATH"),
            ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany", "BAD_URL"),
            ("https://www.sec.gov/cgi-bin/browse-edgar", "BLOCKED_PATH"),
            ("https://www.sec.gov/Archives/edgar/data/1/efts/x.htm", "BLOCKED_PATH"),
            ("https://www.sec.gov/Archives/edgar/daily-index/2026/x.idx", "BLOCKED_PATH"),
            ("http://investors.micron.com/news/x", "BAD_URL"),
        ]
        facts = [fact(i, url) for i, (url, _r) in enumerate(bad)] + [fact(99, URL_FACT)]
        self.write_record(research_record(facts=facts, earnings={}))
        targets, skipped = self.targets()
        self.assertEqual([URL_FACT], [t["url"] for t in targets])
        self.assertEqual([{"key": url, "reason": reason} for url, reason in bad], skipped)

    def test_url_reason_table(self):
        cases = {
            URL_FACT: None,
            URL_SEC_8K: None,
            "https://Investors.Micron.com/news/x": None,
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261105a.htm": None,
            "https://fred.stlouisfed.org/series/DGS10": None,
            "https://nebius.com/newsroom/x": None,
            "https://www.sec.gov/": "ROOT_PAGE",
            "https://ir.crowdstrike.com": "ROOT_PAGE",
            "https://www.sec.gov/cgi-bin/browse-edgar": "BLOCKED_PATH",
            "https://www.sec.gov/edgar/search/x": "BLOCKED_PATH",
            "https://www.sec.gov/Archives/edgar/data/1/2/RSS.xml": "BLOCKED_PATH",
            "https://www.sec.gov/Archives/edgar/data/1/Browse-Edgar/x": "BLOCKED_PATH",
            "https://www.sec.gov/Archives/edgar/data/1/EFTS/x": "BLOCKED_PATH",
            "https://www.sec.gov/Archives/edgar/data/1/Daily-Index/x": "BLOCKED_PATH",
            "https://www.sec.gov/Archives/edgar/data/1/CGI-BIN/x": "BLOCKED_PATH",
            "https://investor.marvell.com/rss": "BLOCKED_PATH",
            "https://data.sec.gov/submissions/CIK0000723125.json": "HOST_NOT_ALLOWED",
            "https://sec.gov/Archives/edgar/data/1/2/x.htm": "HOST_NOT_ALLOWED",
            "https://www.globenewswire.com/news-release/x.html": "HOST_NOT_ALLOWED",
            "https://investors.micron.com.evil.example/news/x": "HOST_NOT_ALLOWED",
            "https://evil.example/investors.micron.com/x": "HOST_NOT_ALLOWED",
            "https://www.sec.gov@evil.example/Archives/edgar/data/1/2/x.htm": "HOST_NOT_ALLOWED",
            "https://www.sec.gov:443/Archives/edgar/data/1/2/x.htm": "HOST_NOT_ALLOWED",
            "https://investors.micron.com/news?id=1": "BAD_URL",
            "https://investors.micron.com/news#top": "BAD_URL",
            "https://investors.micron.com/news x": "BAD_URL",
            "https://www.sec.gov/Archives/edgar/data/../../cgi-bin/x": "BAD_URL",
            "ftp://www.sec.gov/Archives/edgar/data/1/2/x.htm": "BAD_URL",
            "https:///x": "BAD_URL",
            None: "BAD_URL",
            "": "BAD_URL",
        }
        for url, reason in cases.items():
            self.assertEqual(reason, MODULE.url_reason(url), url)
            self.assertEqual(reason is None, MODULE.url_allowed(url), url)

    def test_sec_url_build(self):
        self.assertEqual(URL_SEC_10Q, MODULE.sec_document_url(
            {"cik": "0000723125", "accession_number": "0000723125-26-000045", "primary_document": "mu-20261127.htm"}))
        bad = [
            {"cik": "07231X5", "accession_number": "0000723125-26-000045", "primary_document": "a.htm"},
            {"cik": 723125, "accession_number": "0000723125-26-000045", "primary_document": "a.htm"},
            {"cik": "0000723125", "accession_number": "000072312526000045", "primary_document": "a.htm"},
            {"cik": "0000723125", "accession_number": "0000723125-26-00004", "primary_document": "a.htm"},
            {"cik": "0000723125", "accession_number": "0000723125-26-000045", "primary_document": "a/b.htm"},
            {"cik": "0000723125", "accession_number": "0000723125-26-000045", "primary_document": None},
            {"cik": "0000723125", "accession_number": "0000723125-26-000045", "primary_document": "a b.htm"},
        ]
        for event in bad:
            self.assertIsNone(MODULE.sec_document_url(event), event)

    def test_targets_insider_forms_and_unverified_left_out(self):
        unverified = sec_event("8-K", "0000000001-26-000001", "0000000001", "x.htm", "ZZZ", "Zed", "2026-11-25")
        unverified["verification_status"] = "NOT_VERIFIED"
        self.write_sec(default_events() + [unverified])
        targets, _ = self.targets()
        self.assertEqual([KEY_8K, KEY_10Q], [t["key"] for t in targets])
        self.assertEqual(MODULE.SEC_FORMS,
                         ("8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A", "6-K", "20-F", "DEF 14A"))

    def test_targets_seen_keys_left_out(self):
        self.write_default()
        self.base.mkdir(parents=True)
        (self.base / "seen.jsonl").write_text(
            json.dumps({"key": URL_FACT, "day": "2026-11-20", "url": URL_FACT}) + "\n"
            + json.dumps({"key": KEY_8K, "day": "2026-11-20", "url": URL_SEC_8K}) + "\n",
            encoding="utf-8")
        targets, _ = self.targets()
        self.assertEqual([URL_EARN, KEY_10Q], [t["key"] for t in targets])

    def test_targets_broken_seen_fails_closed(self):
        self.write_default()
        self.base.mkdir(parents=True)
        (self.base / "seen.jsonl").write_text("{broken\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.targets()
        code = self.main(["--phase", "submit", "--day", DAY])
        self.assertEqual(1, code)
        self.assertEqual("llm-srccheck %s UNEXPECTED" % DAY, self.out.getvalue().splitlines()[-1])
        self.assertEqual(0, self.factory.called)

    def test_targets_same_key_once_a_day(self):
        facts = [fact(1, URL_FACT), fact(2, URL_FACT)]
        earnings = {"MU": {"status": "VERIFIED", "announcement_session": "2026-12-17", "source_kind": "COMPANY_IR",
                           "source_url": URL_FACT}}
        self.write_record(research_record(facts=facts, earnings=earnings))
        targets, _ = self.targets()
        self.assertEqual([URL_FACT], [t["key"] for t in targets])
        self.assertEqual("fact", targets[0]["kind"])

    def test_targets_order_and_daily_max(self):
        facts = [fact(i, "https://investors.quantaservices.com/news/f%d" % i) for i in range(1, 4)]
        self.write_record(research_record(facts=facts))
        events = default_events() + [
            sec_event("8-K/A", "0000000002-26-000001", "0000000002", "b.htm", "BBB", "Bee", "2026-11-19"),
            sec_event("10-K", "0000000003-26-000001", "0000000003", "c.htm", "CCC", "Cee", "2026-11-25"),
        ]
        self.write_sec(events)
        targets, _ = self.targets()
        self.assertEqual(MODULE.DAILY_MAX, 5)
        self.assertEqual(
            ["https://investors.quantaservices.com/news/f1", "https://investors.quantaservices.com/news/f2",
             "https://investors.quantaservices.com/news/f3", URL_EARN, "sec:0000000002-26-000001"],
            [t["key"] for t in targets])
        # SEC order alone: 8-K group by filing date, then the rest by filing date
        self.write_record(research_record(facts=[], earnings={}))
        targets, _ = self.targets()
        self.assertEqual(["sec:0000000002-26-000001", KEY_8K, "sec:0000000003-26-000001", KEY_10Q],
                         [t["key"] for t in targets])

    def test_targets_broken_sec_file_skipped(self):
        self.write_record(research_record(facts=[], earnings={}))
        self.write_sec(raw="{not json", run="run-a")
        self.write_sec(raw=json.dumps({"events": "nope"}), run="run-b")
        self.write_sec(run="run-c")
        targets, skipped = self.targets()
        self.assertEqual([KEY_8K, KEY_10Q], [t["key"] for t in targets])
        self.assertIn({"key": "file:sec/%s/run-a" % DAY, "reason": "BROKEN_FILE"}, skipped)
        self.assertIn({"key": "file:sec/%s/run-b" % DAY, "reason": "BROKEN_FILE"}, skipped)

    def test_targets_sec_three_days_and_duplicates(self):
        self.write_sec(day="2026-11-24")  # day-2
        self.write_sec(day="2026-11-25")  # day-1, same accessions
        self.write_sec([sec_event("8-K", "0000000009-26-000009", "0000000009", "z.htm", "ZZZ", "Zed",
                                  "2026-11-23")], day="2026-11-23")  # day-3: not read
        targets, _ = self.targets()
        self.assertEqual([KEY_8K, KEY_10Q], [t["key"] for t in targets])

    def test_targets_broken_or_missing_record(self):
        self.write_sec()
        targets, skipped = self.targets()
        self.assertEqual([KEY_8K, KEY_10Q], [t["key"] for t in targets])
        path = self.write_record()
        path.write_text("[1, 2", encoding="utf-8")
        targets, skipped = self.targets()
        self.assertEqual([KEY_8K, KEY_10Q], [t["key"] for t in targets])
        self.assertIn({"key": "file:research-record/%s" % DAY, "reason": "BROKEN_FILE"}, skipped)

    # ------------------------------------------------------------ submit
    def test_submit_requests(self):
        self.write_default()
        code, status, lines = self.submit()
        self.assertEqual((0, "SUBMITTED"), (code, status))
        self.assertEqual("llm-srccheck %s SUBMITTED requests=4 targets=4 skipped=1" % DAY, lines[-1])
        self.assertEqual([True], self.factory.keys_ok)
        requests = self.sent()
        self.assertEqual(["t1", "t2", "t3", "t4"], [r["custom_id"] for r in requests])
        urls = [URL_FACT, URL_EARN, URL_SEC_8K, URL_SEC_10Q]
        claims = [CLAIM_FACT, CLAIM_EARN, CLAIM_8K, CLAIM_10Q]
        hosts = ["investors.micron.com", "investors.micron.com", "www.sec.gov", "www.sec.gov"]
        for req, url, claim, host in zip(requests, urls, claims, hosts):
            params = req["params"]
            self.assertEqual({"model", "max_tokens", "tools", "messages"}, set(params))
            self.assertEqual("claude-sonnet-5-5", params["model"])
            self.assertEqual(MODEL, params["model"])
            self.assertEqual(4096, params["max_tokens"])
            self.assertEqual([{"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 1,
                               "allowed_domains": [host], "max_content_tokens": 20000,
                               "citations": {"enabled": True}}], params["tools"])
            self.assertEqual([{"role": "user", "content": [
                {"type": "text", "text": EXPECTED_INSTRUCTION + "\n\nURL: " + url + "\n주장: " + claim}]}],
                params["messages"])
        dump = json.dumps(requests, ensure_ascii=False)
        for word in ("cache_control", "betas", "advisor", "fallback", "code_execution", "system", "thinking"):
            self.assertNotIn(word, dump)
        batch = json.loads((self.base / DAY / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual("msgbatch_1", batch["batch_id"])
        self.assertEqual("SUBMITTED", batch["status"])
        self.assertEqual([{"custom_id": "t%d" % i, "key": k, "url": u, "claim": c, "source": s}
                          for i, (k, u, c, s) in enumerate(zip([URL_FACT, URL_EARN, KEY_8K, KEY_10Q], urls, claims,
                                                               ["a", "a", "b", "b"]), 1)], batch["items"])
        seen = [json.loads(x) for x in self.lines(self.base / "seen.jsonl")]
        self.assertEqual([{"key": k, "day": DAY, "url": u} for k, u in
                          zip([URL_FACT, URL_EARN, KEY_8K, KEY_10Q], urls)], seen)
        self.assertFalse((self.base / DAY / "failed.md").exists())

    def test_submit_sends_no_value_outside_the_allowed_fields(self):
        self.write_default()
        self.submit()
        dump = json.dumps(self.sent(), ensure_ascii=False)
        self.assertNotIn(SENTINEL, dump)
        self.assertNotIn("2026-11-20", dump)  # filing_date orders only
        self.assertNotIn("2026-11-18", dump)
        self.assertNotIn("HOLDING", dump)
        self.assertNotIn("DERIVED_RULE_BASED", dump)
        self.assertNotIn("data.example.invalid", dump)

    def test_submit_idempotent(self):
        self.write_default()
        (self.base / DAY).mkdir(parents=True)
        (self.base / DAY / "batch.json").write_text("{}", encoding="utf-8")
        self.assertEqual((0, "PENDING"), self.submit()[:2])
        (self.base / DAY / "checks.json").write_text("{}", encoding="utf-8")
        self.assertEqual((0, "DONE_ALREADY"), self.submit()[:2])
        self.assertEqual(0, self.factory.called)
        self.assertFalse((self.base / "seen.jsonl").exists())

    def test_submit_no_targets(self):
        code, status, lines = self.submit()
        self.assertEqual((0, "NO_TARGETS"), (code, status))
        self.assertEqual("llm-srccheck %s NO_TARGETS targets=0 skipped=0" % DAY, lines[-1])
        self.assertEqual(0, self.factory.called)
        self.assertEqual({}, self.all_files())

    def test_submit_budget_stop(self):
        self.write_default()
        rec = {k: None for k in COMMON.USAGE_KEYS}
        rec.update({"ts_kst": "2026-11-02T08:10:00+09:00", "pilot": "srccheck", "cost_usd_est": 5.9})
        COMMON.append_usage(self.root, rec)
        code, status, _ = self.submit()
        self.assertEqual((5, "BUDGET_STOP"), (code, status))
        self.assertEqual(0, self.factory.called)
        self.assertFalse((self.base / DAY / "batch.json").exists())
        self.assertFalse((self.base / "seen.jsonl").exists())
        self.assertIn("BUDGET_STOP", (self.base / DAY / "failed.md").read_text(encoding="utf-8"))
        # last month and other pilots do not count
        self.usage.write_text("", encoding="utf-8")
        rec.update({"ts_kst": "2026-10-30T08:10:00+09:00"})
        COMMON.append_usage(self.root, rec)
        rec.update({"ts_kst": "2026-11-02T08:10:00+09:00", "pilot": "news"})
        COMMON.append_usage(self.root, rec)
        self.assertEqual("SUBMITTED", self.submit()[1])

    def test_submit_budget_unreadable(self):
        self.write_default()
        self.usage.parent.mkdir(parents=True)
        self.usage.write_text("not json\n", encoding="utf-8")
        self.assertEqual((5, "BUDGET_STOP"), self.submit()[:2])
        self.assertEqual(0, self.factory.called)

    def test_submit_no_key(self):
        self.write_default()
        self.assertEqual((4, "NO_KEY"), self.submit(key=False)[:2])
        self.assertEqual(0, self.factory.called)
        self.assertFalse((self.base / "seen.jsonl").exists())

    def test_submit_create_error_writes_nothing_but_failed(self):
        self.write_default()
        self.factory.batches.create_exc = APIStatusError("server says " + FAKE_KEY, 529)
        code, status, _ = self.submit()
        self.assertEqual((7, "API_ERROR"), (code, status))
        files = self.all_files()
        self.assertEqual(["workspace/outputs/llm/srccheck/%s/failed.md" % DAY],
                         [p for p in files if p.startswith("workspace/outputs/llm")])
        text = files["workspace/outputs/llm/srccheck/%s/failed.md" % DAY].decode("utf-8")
        self.assertIn("APIStatusError HTTP 529", text)
        self.assertNotIn(FAKE_KEY, text)

    def test_submit_next_day_does_not_resend(self):
        self.write_default()
        self.assertEqual("SUBMITTED", self.submit()[1])
        self.write_record(day=DAY2)
        self.assertEqual("NO_TARGETS", self.submit(day=DAY2, now=NOW2)[1])  # SEC day-2 folder still read
        self.assertEqual(1, len(self.factory.batches.created))

    def test_submit_dry_run(self):
        self.write_default()
        before = self.all_files()
        code, status, lines = self.submit(dry_run=True, key=False)
        self.assertEqual((0, "DRY_RUN"), (code, status))
        self.assertEqual(before, self.all_files())
        self.assertEqual(0, self.factory.called)
        self.assertEqual("target a %s %s" % (URL_FACT, URL_FACT), lines[0])
        self.assertEqual("target b %s %s" % (KEY_8K, URL_SEC_8K), lines[2])
        self.assertEqual("skipped %s BAD_SEC_FIELDS" % KEY_BAD_DOC, lines[4])
        self.assertEqual("llm-srccheck %s DRY_RUN targets=4 skipped=1" % DAY, lines[-1])
        self.assertTrue(all(line.isascii() for line in lines))

    # ------------------------------------------------------------ collect
    def test_collect_all_match(self):
        code, status, lines = self.submitted_collect()
        self.assertEqual((0, "CHECKED"), (code, status))
        self.assertEqual(["llm-srccheck %s CHECKED match=4 mismatch=0 undecided=0 unverifiable=0 n=4" % DAY], lines)
        doc = self.checks()
        self.assertEqual({"match": 4, "mismatch": 0, "undecided": 0, "unverifiable": 0, "total": 4}, doc["counts"])
        self.assertTrue(doc["display_only"])
        row = doc["rows"][0]
        self.assertEqual({"custom_id", "key", "url", "source", "claim", "verdict", "model_verdict", "reason",
                          "evidence", "block_types", "stop_reason", "fetch_error"}, set(row))
        self.assertEqual(("맞음", "맞음", None), (row["verdict"], row["model_verdict"], row["reason"]))
        self.assertEqual(["server_tool_use", "web_fetch_tool_result", "text"], row["block_types"])
        self.assertEqual("end_turn", row["stop_reason"])
        self.assertEqual(evidence_for(URL_FACT), row["evidence"])
        md = (self.base / DAY / "checks.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual("출처 확인 %s: 맞음 4 · 틀림 0 · 미정 0 · 확인 불가 0 (4건)" % DAY, md[0])
        self.assertEqual("| # | 출처 | URL | 주장 | 판정 | 사유 | 근거(60자) |", md[2])
        self.assertEqual("| 1 | a | %s | %s | 맞음 | - | %s |" % (URL_FACT, CLAIM_FACT, evidence_for(URL_FACT)[:60]),
                         md[4])
        self.assertEqual("표시 전용: 원장·통합점검·코어는 이 결과를 읽지 않는다", md[-1])
        log = [json.loads(x) for x in self.lines(self.base / "checks.jsonl")]
        self.assertEqual([{"day": DAY, "key": URL_FACT, "url": URL_FACT, "verdict": "맞음", "reason": None},
                          {"day": DAY, "key": URL_EARN, "url": URL_EARN, "verdict": "맞음", "reason": None},
                          {"day": DAY, "key": KEY_8K, "url": URL_SEC_8K, "verdict": "맞음", "reason": None},
                          {"day": DAY, "key": KEY_10Q, "url": URL_SEC_10Q, "verdict": "맞음", "reason": None}], log)
        usage = [json.loads(x) for x in self.lines(self.usage)]
        self.assertEqual(4, len(usage))
        for rec in usage:
            self.assertEqual(list(COMMON.USAGE_KEYS), list(rec))
            self.assertEqual(("srccheck", MODEL, True, "OK"), (rec["pilot"], rec["model"], rec["batch"], rec["status"]))
            self.assertEqual("2026-11-26T10:10:00+09:00", rec["ts_kst"])
            self.assertEqual(0, rec["cache_read_input_tokens"])
        expected = COMMON.estimate_cost(MODEL, {"input_tokens": 25000, "output_tokens": 400}, batch=True)
        self.assertAlmostEqual(4 * expected, COMMON.month_spend(self.root, "srccheck", "2026-11"))
        # once: a second collect finds nothing to do
        self.assertEqual((0, "DONE_ALREADY"), self.collect()[:2])
        self.assertEqual(4, len(self.lines(self.usage)))
        self.assertEqual(4, len(self.lines(self.base / "checks.jsonl")))

    def test_collect_verdict_reasons(self):
        mismatch = lambda u: succeeded("t1", make_message(u, fetched_url=u + "-other"))  # noqa: E731
        refused = lambda u: succeeded("t2", make_message(u, fetch="error"))  # noqa: E731
        no_fetch = lambda u: succeeded("t3", make_message(u, fetch=None))  # noqa: E731
        no_cite = lambda u: succeeded("t4", make_message(u, verdict="틀림", cited="zzzzzz qqqqqq"))  # noqa: E731
        self.submitted_collect(t1=mismatch, t2=refused, t3=no_fetch, t4=no_cite)
        rows = self.rows_by_cid()
        self.assertEqual(("확인 불가", None, "URL_MISMATCH"), (rows["t1"]["verdict"], rows["t1"]["model_verdict"],
                                                           rows["t1"]["reason"]))
        self.assertEqual(("확인 불가", "FETCH_REFUSED", "url_not_accessible"),
                         (rows["t2"]["verdict"], rows["t2"]["reason"], rows["t2"]["fetch_error"]))
        self.assertEqual(("확인 불가", "NO_FETCH_RESULT"), (rows["t3"]["verdict"], rows["t3"]["reason"]))
        self.assertEqual(["server_tool_use", "text"], rows["t3"]["block_types"])
        self.assertEqual(("확인 불가", "틀림", "NO_CITATION"),
                         (rows["t4"]["verdict"], rows["t4"]["model_verdict"], rows["t4"]["reason"]))
        md = (self.base / DAY / "checks.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual("출처 확인 %s: 맞음 0 · 틀림 0 · 미정 0 · 확인 불가 4 (4건)" % DAY, md[0])

    def test_collect_parse_and_batch_failures(self):
        parse_fail = lambda u: succeeded("t1", make_message(u, text="맞는 것 같다"))  # noqa: E731
        errored = lambda u: other("t2", "errored")  # noqa: E731
        expired = lambda u: other("t3", "expired")  # noqa: E731
        missing = lambda u: None  # noqa: E731
        self.submitted_collect(t1=parse_fail, t2=errored, t3=expired, t4=missing)
        rows = self.rows_by_cid()
        self.assertEqual(("확인 불가", "PARSE_FAIL"), (rows["t1"]["verdict"], rows["t1"]["reason"]))
        self.assertEqual(("확인 불가", "ERRORED"), (rows["t2"]["verdict"], rows["t2"]["reason"]))
        self.assertEqual(("확인 불가", "EXPIRED"), (rows["t3"]["verdict"], rows["t3"]["reason"]))
        self.assertEqual(("확인 불가", "NO_RESULT"), (rows["t4"]["verdict"], rows["t4"]["reason"]))
        self.assertEqual(1, len(self.lines(self.usage)))  # only the succeeded one

    def test_collect_undecided_and_model_unverifiable(self):
        undecided = lambda u: succeeded("t1", make_message(u, verdict="미정"))  # noqa: E731
        unverifiable = lambda u: succeeded("t2", make_message(u, verdict="확인 불가", cited=False))  # noqa: E731
        stop = lambda u: succeeded("t3", make_message(u, stop="pause_turn"))  # noqa: E731
        maxed = lambda u: succeeded("t4", make_message(u, stop="max_tokens"))  # noqa: E731
        self.submitted_collect(t1=undecided, t2=unverifiable, t3=stop, t4=maxed)
        rows = self.rows_by_cid()
        self.assertEqual(("미정", None), (rows["t1"]["verdict"], rows["t1"]["reason"]))
        self.assertEqual(("확인 불가", "확인 불가", None),
                         (rows["t2"]["verdict"], rows["t2"]["model_verdict"], rows["t2"]["reason"]))
        self.assertEqual(("확인 불가", "BAD_STOP", "pause_turn"),
                         (rows["t3"]["verdict"], rows["t3"]["reason"], rows["t3"]["stop_reason"]))
        self.assertEqual(("확인 불가", "MAX_TOKENS"), (rows["t4"]["verdict"], rows["t4"]["reason"]))
        statuses = sorted(json.loads(x)["status"] for x in self.lines(self.usage))
        self.assertEqual(["BAD_STOP", "MAX_TOKENS", "OK", "OK"], statuses)

    def test_collect_model_mismatch_usage_once(self):
        other_model = lambda u: succeeded("t1", make_message(u, model="claude-opus-5-5"))  # noqa: E731
        self.submitted_collect(t1=other_model)
        rows = self.rows_by_cid()
        self.assertEqual(("확인 불가", "MODEL_MISMATCH"), (rows["t1"]["verdict"], rows["t1"]["reason"]))
        usage = [json.loads(x) for x in self.lines(self.usage)]
        self.assertEqual(4, len(usage))
        mism = [rec for rec in usage if rec["status"] == "MODEL_MISMATCH"]
        self.assertEqual(1, len(mism))
        self.assertEqual("claude-opus-5-5", mism[0]["model"])
        self.assertTrue((self.base / DAY / "usage-done").exists())
        # a second collect after usage-done adds no usage line
        (self.base / DAY / "checks.json").unlink()
        self.assertEqual("CHECKED", self.collect()[1])
        self.assertEqual(4, len(self.lines(self.usage)))
        self.assertEqual(8, len(self.lines(self.base / "checks.jsonl")))
        COMMON.month_spend(self.root, "srccheck", "2026-11")

    def test_collect_waiting_and_no_batch_write_nothing(self):
        self.assertEqual((0, "NO_BATCH"), self.collect()[:2])
        self.assertEqual({}, self.all_files())
        self.assertEqual(0, self.factory.called)
        self.write_default()
        self.submit()
        self.factory.batches.status = "in_progress"
        before = self.all_files()
        code, status, lines = self.collect()
        self.assertEqual((0, "WAITING"), (code, status))
        self.assertEqual(["llm-srccheck %s WAITING" % DAY], lines)
        self.assertEqual(before, self.all_files())

    def test_collect_previous_day_waiting_is_collected_next_day(self):
        self.write_default()
        self.submit()
        self.factory.batches.status = "in_progress"
        self.assertEqual("WAITING", self.collect()[1])
        # next day: one new fact, submitted, then both batches have ended
        url2 = "https://ir.crowdstrike.com/news-releases/next"
        self.write_record(research_record(facts=[fact(1, url2, symbol="CRWD")], earnings={}), day=DAY2)
        self.assertEqual("SUBMITTED", self.submit(day=DAY2, now=NOW2)[1])
        self.assertEqual(1, len(self.sent(1)))
        self.factory.batches.status = "ended"
        code, status, lines = self.collect(day=DAY2, now=COLLECT_AT2)
        self.assertEqual((0, "CHECKED"), (code, status))
        self.assertEqual(["llm-srccheck %s CHECKED match=4 mismatch=0 undecided=0 unverifiable=0 n=4" % DAY,
                          "llm-srccheck %s CHECKED match=1 mismatch=0 undecided=0 unverifiable=0 n=1" % DAY2], lines)
        self.assertEqual(4, self.checks(DAY)["counts"]["total"])
        self.assertEqual(1, self.checks(DAY2)["counts"]["total"])
        self.assertEqual(5, len(self.lines(self.base / "checks.jsonl")))
        self.assertEqual(5, len(self.lines(self.usage)))

    def test_collect_last_line_falls_back_to_latest_processed_folder(self):
        self.write_default()
        self.submit()
        self.factory.batches.status = "in_progress"
        code, status, lines = self.collect(day=DAY2, now=COLLECT_AT2)
        self.assertEqual((0, "WAITING"), (code, status))
        self.assertEqual(["llm-srccheck %s WAITING" % DAY], lines)
        self.factory.batches.status = "ended"
        self.assertEqual(["llm-srccheck %s CHECKED match=4 mismatch=0 undecided=0 unverifiable=0 n=4" % DAY],
                         self.collect(day=DAY2, now=COLLECT_AT2)[2])
        self.assertEqual((0, "NO_BATCH"), self.collect(day=DAY2, now=COLLECT_AT2)[:2])

    def test_collect_window_is_three_days(self):
        self.write_default()
        self.submit()
        self.factory.batches.status = "in_progress"
        self.assertEqual("NO_BATCH", self.collect(day="2026-11-30")[1])
        self.assertEqual("WAITING", self.collect(day="2026-11-29")[1])

    def test_collect_api_errors(self):
        self.write_default()
        self.submit()

        def broken(batch_id):
            raise APIStatusError("down " + FAKE_KEY, 500)
        self.factory.batches.retrieve = broken
        code, status, _ = self.collect()
        self.assertEqual((7, "API_ERROR"), (code, status))
        text = (self.base / DAY / "failed.md").read_text(encoding="utf-8")
        self.assertIn("APIStatusError HTTP 500", text)
        self.assertNotIn(FAKE_KEY, text)
        self.assertFalse((self.base / DAY / "checks.json").exists())
        self.assertEqual((4, "NO_KEY"), self.collect(key=False)[:2])

    def test_collect_dry_run(self):
        self.write_default()
        self.submit()
        before = self.all_files()
        code, status, lines = self.collect(dry_run=True, key=False)
        self.assertEqual((0, "DRY_RUN"), (code, status))
        self.assertEqual(["llm-srccheck %s DRY_RUN folders=%s" % (DAY, DAY)], lines)
        self.assertEqual(before, self.all_files())

    # ------------------------------------------------------------ parsing
    def test_parse_answer(self):
        self.assertEqual({"verdict": "맞음", "evidence": "abc def"}, MODULE.parse_answer("판정: 맞음\n근거: abc def"))
        self.assertEqual({"verdict": "확인 불가", "evidence": "x"},
                         MODULE.parse_answer("**판정:** 확인 불가\n- 근거: `x`"))
        self.assertEqual({"verdict": "틀림", "evidence": "second"},
                         MODULE.parse_answer("판정: 맞음\n근거: first\n다시 보니\n판정: 틀림\n근거: second"))
        self.assertEqual("미정", MODULE.parse_answer("판정： 미정\n근거： y")["verdict"])
        for text in ("판정: 아마 맞음\n근거: x", "판정: 맞음", "근거: x", "판정: 맞음\n근거:   ", None,
                     "설명 판정: 맞음\n근거: x"):
            self.assertIsNone(MODULE.parse_answer(text), text)

    def test_quote_overlap_and_citations(self):
        self.assertTrue(MODULE.quote_overlaps("revenue of the quarter rose", "the quarter rose sharply"))
        self.assertFalse(MODULE.quote_overlaps("abc", "abc"))
        self.assertFalse(MODULE.quote_overlaps("completely other", "nothing alike here"))
        msg = SimpleNamespace(content=[
            SimpleNamespace(type="web_fetch_tool_result", citations=[SimpleNamespace(cited_text="not from text")]),
            SimpleNamespace(type="text", text="a", citations=[SimpleNamespace(cited_text="kept quote")]),
        ])
        self.assertEqual(["kept quote"], MODULE.citation_texts(msg))

    def test_fetch_check_shapes(self):
        url = URL_FACT
        msg = lambda *blocks: SimpleNamespace(content=list(blocks))  # noqa: E731
        self.assertEqual((None, None), MODULE.fetch_check(msg(fetch_ok(url)), url))
        self.assertEqual(("URL_MISMATCH", None), MODULE.fetch_check(msg(fetch_ok(url + "/")), url))
        self.assertEqual(("URL_MISMATCH", None), MODULE.fetch_check(msg(fetch_ok(url.upper())), url))
        self.assertEqual(("URL_MISMATCH", None),
                         MODULE.fetch_check(msg(fetch_ok(url), fetch_ok("https://investors.micron.com/x")), url))
        self.assertEqual(("FETCH_REFUSED", "too_many_requests"),
                         MODULE.fetch_check(msg(fetch_error("too_many_requests")), url))
        no_code = SimpleNamespace(type="web_fetch_tool_result", content=SimpleNamespace(type="web_fetch_tool_error"))
        self.assertEqual(("FETCH_REFUSED", "web_fetch_tool_error"), MODULE.fetch_check(msg(no_code), url))
        dict_block = {"type": "web_fetch_tool_result", "content": {"type": "web_fetch_result", "url": url}}
        self.assertEqual((None, None), MODULE.fetch_check(msg(dict_block), url))
        self.assertEqual(("NO_FETCH_RESULT", None), MODULE.fetch_check(msg(), url))

    # ------------------------------------------------------------ key never written
    def test_fake_key_never_written_or_printed(self):
        self.write_default()
        self.assertEqual(0, self.main(["--phase", "submit", "--day", DAY]))
        self.factory.batches.override["t1"] = lambda u: other("t1", "errored")
        self.assertEqual(0, self.main(["--phase", "collect", "--day", DAY], now=COLLECT_AT))
        self.factory.batches.create_exc = APIStatusError("bad " + FAKE_KEY, 400)
        self.write_record(research_record(facts=[fact(1, "https://investor.lumentum.com/news/z")], earnings={}),
                          day=DAY2)
        self.assertEqual(7, self.main(["--phase", "submit", "--day", DAY2], now=NOW2))
        self.assertNotIn(FAKE_KEY, self.out.getvalue() + self.err.getvalue())
        for name, data in self.all_files().items():
            self.assertNotIn(FAKE_KEY.encode("utf-8"), data, name)

    # ------------------------------------------------------------ main / lines
    def test_main_lines_and_exit_codes(self):
        self.write_default()
        self.assertEqual(0, self.main(["--phase", "submit", "--day", DAY]))
        self.assertEqual(0, self.main(["--phase", "collect"], now=COLLECT_AT))  # day defaults to KST today
        printed = self.out.getvalue().splitlines()
        self.assertEqual("llm-srccheck %s SUBMITTED requests=4 targets=4 skipped=1" % DAY, printed[0])
        self.assertTrue(printed[-1].startswith("llm-srccheck %s CHECKED" % DAY))
        for line in printed:
            self.assertTrue(RUNNER._LINE_OK.fullmatch(line), line)
            self.assertIsNotNone(RUNNER._LINE_STATUS.match(line), line)
        self.assertEqual("CHECKED", RUNNER.status_of(RUNNER.pick_line(self.out.getvalue()), 0))

    def test_main_unexpected(self):
        self.write_default()
        self.submit()
        (self.base / DAY / "batch.json").write_text("[]", encoding="utf-8")
        self.assertEqual(1, self.main(["--phase", "collect", "--day", DAY], now=COLLECT_AT))
        self.assertEqual("llm-srccheck %s UNEXPECTED" % DAY, self.out.getvalue().splitlines()[-1])
        self.assertIn("UNEXPECTED", (self.base / DAY / "failed.md").read_text(encoding="utf-8"))

    def test_exit_codes(self):
        expected = {"SUBMITTED": 0, "PENDING": 0, "WAITING": 0, "CHECKED": 0, "DONE_ALREADY": 0, "NO_TARGETS": 0,
                    "NO_BATCH": 0, "DRY_RUN": 0, "UNEXPECTED": 1, "NO_KEY": 4, "BUDGET_STOP": 5, "API_ERROR": 7}
        self.assertEqual(expected, MODULE.EXIT_CODES)
        for name, value in PDFCMP.EXIT_CODES.items():
            if name in MODULE.EXIT_CODES:
                self.assertEqual(value, MODULE.EXIT_CODES[name], name)

    # ------------------------------------------------------------ pinned constants
    def test_korean_constants(self):
        self.assertEqual(EXPECTED_INSTRUCTION, MODULE.INSTRUCTION)
        self.assertEqual(("맞음", "틀림", "미정", "확인 불가"), MODULE.VERDICTS)
        self.assertEqual(("판정", "근거", "주장"), (MODULE.LABEL_VERDICT, MODULE.LABEL_EVIDENCE, MODULE.LABEL_CLAIM))
        self.assertEqual({"BEFORE_OPEN": "장 시작 전", "AFTER_CLOSE": "장 마감 후"}, MODULE.TIMING_KO)
        self.assertEqual(PDFCMP.MD_FOOTER, MODULE.MD_FOOTER)
        self.assertEqual({
            "no_key": "키 없음",
            "usage_unreadable": "사용 기록을 읽을 수 없음",
            "budget_spent": "이달 예산을 넘음",
            "call_failed": "API 호출 실패 ",
            "bad_shape": "응답 형식 다름",
            "unexpected": "예상 못 한 오류 (%s)",
        }, MODULE.REASON_KO)
        self.assertEqual(MODULE.MODELS["srccheck"], "claude-sonnet-5-5")
        self.assertEqual(MODULE.BUDGET_USD_MONTH["srccheck"], 6)
        one = COMMON.estimate_cost(MODEL, {"input_tokens": 30000, "output_tokens": 4096}, batch=True)
        self.assertAlmostEqual(5 * one, MODULE.estimate_submit_cost(5))

    # ------------------------------------------------------------ source contract
    def test_script_source_contract(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(text.isascii())
        for word in ("environ", "zoneinfo", "subprocess", "import requests", "urllib", "fallbacks",
                     "advisor", "socket", "http.client", "auto_core", "kiwoom"):
            self.assertNotIn(word, text, word)
        for word in ("urlopen", "httpx", "aiohttp", "import http", "requests.get", "count_tokens",
                     "cache_control", "betas", "code_execution"):
            self.assertNotIn(word, text, word)
        # "sec.gov" appears only in the allowed-host list; the archive URL is assembled from it
        self.assertEqual(['    "www.sec.gov",'], [line for line in text.splitlines() if "sec.gov" in line])
        self.assertEqual(1, text.count("batches.create("))

    def test_allowed_hosts_match_prompt(self):
        self.assertEqual(EXPECTED_HOSTS, MODULE.ALLOWED_HOSTS)
        prompt = PROMPT.read_text(encoding="utf-8")
        start = prompt.index("`ALLOWED_HOSTS`(")
        end = prompt.index("- `www.sec.gov`", start)
        hosts = tuple(re.findall(r"`([a-z0-9.-]+\.[a-z]+)`", prompt[start:end]))
        self.assertEqual(EXPECTED_HOSTS, hosts)
        self.assertEqual(("cgi-bin", "efts", "daily-index", "rss", "browse-edgar"), MODULE.BLOCKED_WORDS)
        self.assertEqual("/Archives/edgar/data/", MODULE.SEC_PATH_PREFIX)

    # ------------------------------------------------------------ llm-srcfix
    def test_web_fetch_version_without_dynamic_filtering(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("web_fetch_20260209", text)
        self.assertEqual("web_fetch_20250910", MODULE.WEB_FETCH_TYPE)
        self.assertEqual({"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 1,
                          "allowed_domains": ["www.sec.gov"], "max_content_tokens": 20000,
                          "citations": {"enabled": True}}, MODULE.web_fetch_tool("www.sec.gov"))

    def test_def14a_claim_names_meeting_date(self):
        self.assertEqual("주주총회일 %s", MODULE.CLAIM_SEC_MEETING)
        proxy = {"kind": "sec", "fields": {"ticker": "MU", "company_name": "Micron Technology",
                                           "form": "DEF 14A", "report_date": "2027-01-14", "items": []}}
        claim = MODULE.claim_text(proxy)
        self.assertEqual("Micron Technology(MU)의 DEF 14A 서류이고, 주주총회일 2027-01-14이다", claim)
        self.assertIn("주주총회일 2027-01-14", claim)
        self.assertNotIn("보고 기준일", claim)
        current = {"kind": "sec", "fields": {"ticker": "DELL", "company_name": "Dell Technologies Inc.",
                                             "form": "8-K", "report_date": "2026-11-17",
                                             "items": ["2.02", "9.01"]}}
        claim_8k = MODULE.claim_text(current)
        self.assertEqual(CLAIM_8K, claim_8k)
        self.assertNotIn("주주총회일", claim_8k)
        no_date = {"kind": "sec", "fields": {"ticker": "MU", "company_name": "Micron Technology",
                                             "form": "DEF 14A", "report_date": None, "items": []}}
        self.assertEqual("Micron Technology(MU)의 DEF 14A 서류이다", MODULE.claim_text(no_date))


if __name__ == "__main__":
    unittest.main()
