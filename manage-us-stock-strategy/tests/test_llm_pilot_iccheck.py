import contextlib
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
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("llm_pilot_iccheck", SCRIPT_DIR / "llm_pilot_iccheck.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


FAKE_KEY = "fake-key-FOR-TEST-7Q9Z"
DAY = "2026-11-06"
NOW = datetime(2026, 11, 7, 7, 0, 0, tzinfo=MODULE.KST)
RECON = "일치: 키움 AAA 4321·BBB 8765 = 상태 파일 · 주문 가능 $98765.43 · 미체결 없음"
SECRET_NUMBERS = (
    "987654.32",
    "991234.56",
    "987650.01",
    "55667.08",
    "912345.67",
    "923456.78",
    "934567.89",
    "24689.13",
    "4321",
    "8765",
    "98765.43",
    "123.45",
    "533432.45",
    "56.78",
    "497676.7",
    "98.76",
    "71.09",
)
DECISION_ROWS = [
    "# 결정 색인",
    "| **AAA 4321주 유지** · 2026-10-08 | 새 근거가 생기면 다시 카드 |",
    "| 상태 파일은 대조 보류로 옛 값 4321 | 확인 필요 |",
    "| 사장 주문 기록 | AAA ② 4321주 LOC $98.76 · 키움 AAA 4321·BBB 8765 |",
    "| 노출 상한 S7 밴드 mid 유지 · 2026-11-01 | 신규 매수 정지 해제 |",
]
DECISION_QUOTE = "노출 상한 S7 밴드 mid 유지"
FORBIDDEN_REQUEST_KEYS = {"thinking", "cache_control", "fallbacks", "temperature", "top_p",
                          "tools", "tool_choice", "betas", "extra_headers"}


def fake_record():
    return {
        "date": DAY,
        "account": {
            "total": 987654.32,
            "hwm": 991234.56,
            "vsHwmPct": -0.4,
            "kiwoomTotal": 987650.01,
            "kiwoomDiff": 71.09,
            "cash": 55667.08,
            "lines": {"max": 912345.67, "first": 923456.78, "approach": 934567.89},
            "firstCushionPct": 2.5,
            "firstCushionUsd": 24689.13,
            "approachPct": 1.2,
            "maxPct": 6.1,
            "n": 3,
            "reconcile": RECON,
            "holdings": [
                {"code": "AAA", "qty": 4321, "close": 123.45, "value": 533432.45,
                 "weight": 0.54, "mult": 1, "contrib": 0.31},
                {"code": "BBB", "qty": 8765, "close": 56.78, "value": 497676.70,
                 "weight": 0.46, "mult": 3, "contrib": 0.22},
            ],
            "openOrders": [{"code": "AAA", "qty": 4321, "price": 98.76}],
            "exposure": {
                "n": 3,
                "nStatus": "ok",
                "s7": {"session": DAY, "fresh": True, "e": 0.62, "band": "mid",
                       "newBuyPaused": False},
                "capBreaches": [],
            },
        },
        "status": [
            {"name": "잔고", "value": RECON},
            {"name": "시나리오", "value": "06:40 점검 · 10/28 실적"},
        ],
        "notes": ["AAA 4321주 유지", "지정가 $98.76"],
    }


def sent_record_lines():
    clean, _ = MODULE.strip_amounts(fake_record())
    return json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True).splitlines()


def line_no_containing(lines, needle):
    for i, line in enumerate(lines, 1):
        if needle in line:
            return i
    raise AssertionError("needle not found: " + needle)


def finding(rline, rtext, dline, dtext, severity="mid"):
    return {"summary_ko": "밴드 표기가 결정과 다름.", "record_quote": {"line": rline, "text": rtext},
            "decision_quote": {"line": dline, "text": dtext}, "severity": severity}


def three_findings():
    rlines = sent_record_lines()
    band = line_no_containing(rlines, '"band"')
    dline = line_no_containing(DECISION_ROWS, DECISION_QUOTE)
    return {
        "findings": [
            finding(band, 'R%d|"band": "mid"' % band, dline, DECISION_QUOTE, "high"),
            finding(band, "이 글은 기록 어디에도 없다", dline, DECISION_QUOTE),
            finding(band, '"band', dline, DECISION_QUOTE, "low"),
        ],
        "checked_lines": {"record": len(rlines), "decisions": len(DECISION_ROWS)},
    }


def make_message(payload=None, model="claude-sonnet-5-5", stop="end_turn", text=None):
    if text is None:
        text = json.dumps(payload if payload is not None else three_findings(), ensure_ascii=False)
    return SimpleNamespace(
        model=model,
        stop_reason=stop,
        content=[SimpleNamespace(type="thinking", thinking="..."), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=5000, output_tokens=800, cache_creation_input_tokens=None,
                              cache_read_input_tokens=0),
    )


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, message=None, count=12345, stream_exc=None):
        self.message = message if message is not None else make_message()
        self.count = count
        self.stream_exc = stream_exc
        self.calls = []
        self.count_kwargs = []
        self.stream_kwargs = []
        self.messages = self

    def count_tokens(self, **kwargs):
        self.calls.append("count_tokens")
        self.count_kwargs.append(kwargs)
        return SimpleNamespace(input_tokens=self.count)

    def stream(self, **kwargs):
        self.calls.append("stream")
        self.stream_kwargs.append(kwargs)
        if self.stream_exc is not None:
            raise self.stream_exc
        return FakeStream(self.message)


class Factory:
    def __init__(self, client=None):
        self.client = client if client is not None else FakeClient()
        self.called = 0

    def __call__(self, key):
        self.called += 1
        self.got_key = key == FAKE_KEY
        return self.client


class APIStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


def all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_keys(v)


class IccheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = io.StringIO()
        self.err = io.StringIO()
        rec = self.root / "workspace" / "outputs" / "research-records" / DAY / "research-record.json"
        rec.parent.mkdir(parents=True)
        rec.write_text(json.dumps(fake_record(), ensure_ascii=False, indent=1), encoding="utf-8")
        self.record_path = rec
        dec = self.root / "docs" / "claude" / "active-decisions.md"
        dec.parent.mkdir(parents=True)
        dec.write_bytes(("\r\n".join(DECISION_ROWS) + "\r\n").encode("utf-8"))
        self.decisions_path = dec
        self.day_dir = self.root / "workspace" / "outputs" / "llm" / "iccheck" / DAY
        self.usage = self.root / "workspace" / "outputs" / "llm" / "usage.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    # -- helpers
    def call(self, factory=None, dry_run=False, key=True):
        env = {MODULE.KEY_ENV: FAKE_KEY} if key else {}
        with mock.patch.dict(os.environ, env):
            if not key:
                os.environ.pop(MODULE.KEY_ENV, None)
            with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
                return MODULE.run(DAY, repo_root=self.root, client_factory=factory,
                                  dry_run=dry_run, now=NOW)

    def assert_no_key_anywhere(self):
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_KEY.encode("utf-8"), path.read_bytes(), str(path))
        self.assertNotIn(FAKE_KEY, self.out.getvalue())
        self.assertNotIn(FAKE_KEY, self.err.getvalue())

    def failed_text(self):
        return (self.day_dir / "failed.md").read_text(encoding="utf-8")

    def usage_lines(self):
        if not self.usage.exists():
            return []
        return self.usage.read_text(encoding="utf-8").splitlines()

    # -- (가) no record
    def test_no_record(self):
        self.record_path.unlink()
        factory = Factory()
        self.assertEqual(self.call(factory), (3, "NO_RECORD"))
        self.assertEqual(factory.called, 0)
        self.assertEqual(self.failed_text(), "검토 못 함: 오늘 연구 기록 없음 (NO_RECORD)\n")
        self.assertFalse((self.day_dir / "review.json").exists())
        self.assert_no_key_anywhere()

    def test_bad_record_and_missing_decisions(self):
        self.record_path.write_text("{broken", encoding="utf-8")
        factory = Factory()
        self.assertEqual(self.call(factory), (9, "BAD_INPUT"))
        self.assertIn("연구 기록을 읽을 수 없음", self.failed_text())
        self.record_path.write_text(json.dumps(fake_record()), encoding="utf-8")
        self.decisions_path.unlink()
        self.assertEqual(self.call(factory), (9, "BAD_INPUT"))
        self.assertIn("결정 색인 없음", self.failed_text())
        self.assertEqual(factory.called, 0)
        self.assert_no_key_anywhere()

    # -- (나) no key
    def test_no_key(self):
        factory = Factory()
        self.assertEqual(self.call(factory, key=False), (4, "NO_KEY"))
        self.assertEqual(factory.called, 0)
        self.assertEqual(self.failed_text(), "검토 못 함: 키 없음 (NO_KEY)\n")
        self.assert_no_key_anywhere()

    # -- (다) budget
    def _seed_usage(self, cost, ts="2026-11-03T07:00:00+09:00", pilot="iccheck"):
        self.usage.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts_kst": ts, "pilot": pilot, "model": "claude-sonnet-5-5",
                                 "input_tokens": 1, "output_tokens": 1,
                                 "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                                 "batch": False, "cost_usd_est": cost, "status": "RECEIVED"}) + "\n")

    def test_budget_spent(self):
        self._seed_usage(10.0)
        self._seed_usage(9.0, ts="2026-10-20T07:00:00+09:00")
        client = FakeClient()
        factory = Factory(client)
        self.assertEqual(self.call(factory), (5, "BUDGET_STOP"))
        self.assertEqual(factory.called, 0)
        self.assertEqual(client.calls, [])
        self.assertIn("(BUDGET_STOP)", self.failed_text())
        self.assert_no_key_anywhere()

    def test_budget_unreadable_usage(self):
        self.usage.parent.mkdir(parents=True, exist_ok=True)
        self.usage.write_text("{not json\n", encoding="utf-8")
        client = FakeClient()
        factory = Factory(client)
        self.assertEqual(self.call(factory), (5, "BUDGET_STOP"))
        self.assertEqual(client.calls, [])
        self.assertIn("사용 기록을 읽을 수 없음", self.failed_text())
        self.assert_no_key_anywhere()

    def test_budget_worst_case_estimate(self):
        self._seed_usage(9.9)
        # 100000 input * 2.00/M + 16000 output * 10.00/M = 0.36 -> 10.26 > 10
        client = FakeClient(count=100_000)
        self.assertEqual(self.call(Factory(client)), (5, "BUDGET_STOP"))
        self.assertEqual(client.calls, ["count_tokens"])
        self.assertIn("예상 최대 비용", self.failed_text())
        self.assert_no_key_anywhere()

    # -- (라) too large
    def test_too_large(self):
        client = FakeClient(count=150_001)
        self.assertEqual(self.call(Factory(client)), (6, "TOO_LARGE"))
        self.assertEqual(client.calls, ["count_tokens"])
        self.assertEqual(client.stream_kwargs, [])
        self.assertEqual(self.usage_lines(), [])
        self.assert_no_key_anywhere()

    # -- (마) normal path
    def test_ok_path(self):
        self.day_dir.mkdir(parents=True)
        (self.day_dir / "failed.md").write_text("old\n", encoding="utf-8")
        client = FakeClient()
        factory = Factory(client)
        self.assertEqual(self.call(factory), (0, "OK"))
        self.assertEqual(factory.called, 1)
        self.assertTrue(factory.got_key)
        self.assertEqual(client.calls, ["count_tokens", "stream"])
        self.assertFalse((self.day_dir / "failed.md").exists())

        review = json.loads((self.day_dir / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["schema"], "llm-iccheck-review-1")
        self.assertEqual(review["day"], DAY)
        self.assertEqual(review["display"], "none")
        self.assertEqual(review["model"], "claude-sonnet-5-5")
        self.assertEqual(len(review["findings"]), 1)
        self.assertEqual(review["findings"][0]["severity"], "high")
        self.assertEqual(review["dropped_findings"], 2)
        self.assertGreater(review["removed_amount_items"], 0)
        self.assertGreater(review["masked_decision_items"], 0)
        self.assertEqual(review["usage"]["cache_creation_input_tokens"], 0)
        self.assertEqual(set(review["input_sha256"].keys()), {"record", "decisions"})
        self.assertTrue((self.day_dir / "alert.md").exists())
        alert = (self.day_dir / "alert.md").read_text(encoding="utf-8")
        self.assertIn(DECISION_QUOTE, alert)
        self.assertIn("높음", alert)

        lines = self.usage_lines()
        self.assertEqual(len(lines), 1)
        usage = json.loads(lines[0])
        self.assertEqual(usage["pilot"], "iccheck")
        self.assertIs(usage["batch"], False)
        self.assertGreater(usage["cost_usd_est"], 0)
        self.assertAlmostEqual(review["cost_usd_est"], usage["cost_usd_est"])

        self.assertEqual(len(client.stream_kwargs), 1)
        sent = client.stream_kwargs[0]
        self.assertEqual(set(sent.keys()), {"model", "max_tokens", "system", "messages", "output_config"})
        self.assertEqual(sent["model"], "claude-sonnet-5-5")
        self.assertEqual(sent["max_tokens"], 16000)
        self.assertEqual(sent["system"], MODULE.SYSTEM_PROMPT)
        self.assertEqual(sent["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(sent["output_config"]["format"]["schema"], MODULE.SCHEMA)
        self.assertEqual(sent["output_config"]["effort"], "medium")
        self.assertEqual(set(sent["output_config"].keys()), {"format", "effort"})
        for kwargs in (sent, client.count_kwargs[0]):
            self.assertEqual(FORBIDDEN_REQUEST_KEYS & set(all_keys(kwargs)), set())
        self.assertEqual(client.count_kwargs[0]["messages"], sent["messages"])
        blocks = sent["messages"][0]["content"]
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0]["text"].startswith("결정 색인(D행)\nD1|"))
        self.assertTrue(blocks[1]["text"].startswith("오늘 연구 기록(R행, 금액·수량 지움)\nR1|"))
        record_block = blocks[1]["text"]
        for secret in SECRET_NUMBERS:
            self.assertNotIn(secret, record_block)
        self.assertIn('"weight": 0.54', record_block)
        self.assert_no_key_anywhere()

    # -- (마-2) amounts and counts never leave in either block
    def test_amount_forms_never_sent(self):
        client = FakeClient()
        self.assertEqual(self.call(Factory(client)), (0, "OK"))
        for kwargs in (client.count_kwargs[0], client.stream_kwargs[0]):
            text = json.dumps(kwargs, ensure_ascii=False)
            for secret in ("4321", "8765", "98.76", "98765.43"):
                self.assertNotIn(secret, text)
        decision_block = client.stream_kwargs[0]["messages"][0]["content"][0]["text"]
        self.assertIn("옛 값 [수량]", decision_block)
        self.assertIn("키움 AAA [수량]·BBB [수량]", decision_block)
        self.assertIn("LOC [금액]", decision_block)
        record_block = client.stream_kwargs[0]["messages"][0]["content"][1]["text"]
        self.assertIn('"reconcile": "일치"', record_block)
        self.assertIn("키움 AAA [수량]·BBB [수량]", record_block)
        self.assert_no_key_anywhere()

    def test_findings_capped_at_ten(self):
        payload = three_findings()
        good = payload["findings"][0]
        payload["findings"] = [good] * 12
        client = FakeClient(message=make_message(payload))
        self.assertEqual(self.call(Factory(client)), (0, "OK"))
        review = json.loads((self.day_dir / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(len(review["findings"]), 10)
        self.assertEqual(review["dropped_findings"], 2)
        self.assert_no_key_anywhere()

    def test_no_findings_writes_no_alert(self):
        payload = {"findings": [], "checked_lines": {"record": 3, "decisions": 5}}
        client = FakeClient(message=make_message(payload))
        self.assertEqual(self.call(Factory(client)), (0, "OK"))
        self.assertTrue((self.day_dir / "review.json").exists())
        self.assertFalse((self.day_dir / "alert.md").exists())
        self.assert_no_key_anywhere()

    # -- (바) model mismatch
    def test_model_mismatch(self):
        client = FakeClient(message=make_message(model="claude-sonnet-5"))
        self.assertEqual(self.call(Factory(client)), (8, "BAD_RESPONSE"))
        self.assertFalse((self.day_dir / "review.json").exists())
        self.assertEqual(len(self.usage_lines()), 1)
        self.assertIn("MODEL_MISMATCH", self.failed_text())
        self.assert_no_key_anywhere()

    # -- (사) refusal / max_tokens / bad shape
    def test_refusal_max_tokens_and_bad_shape(self):
        cases = [
            (make_message(stop="refusal"), "REFUSAL"),
            (make_message(stop="max_tokens"), "MAX_TOKENS"),
            (make_message(text='{"findings": [], "checked_lines": {"record": 1, "decisions": 1}, "x": 1}'),
             "응답 형식 다름"),
            (make_message(text="not json"), "응답 형식 다름"),
            (make_message(payload={"findings": [finding(1, "abcdefg", 1, "abcdefg", "urgent")],
                                   "checked_lines": {"record": 1, "decisions": 1}}),
             "응답 형식 다름"),
            (make_message(payload={"findings": [finding("1", "abcdefg", 1, "abcdefg")],
                                   "checked_lines": {"record": 1, "decisions": 1}}),
             "응답 형식 다름"),
        ]
        for i, (message, expect) in enumerate(cases, 1):
            with self.subTest(expect=expect, i=i):
                client = FakeClient(message=message)
                self.assertEqual(self.call(Factory(client)), (8, "BAD_RESPONSE"))
                self.assertIn(expect, self.failed_text())
                self.assertFalse((self.day_dir / "review.json").exists())
                self.assertEqual(len(self.usage_lines()), i)
        self.assert_no_key_anywhere()

    # -- (아) second run
    def test_second_run_already_done(self):
        self.assertEqual(self.call(Factory()), (0, "OK"))
        client = FakeClient()
        factory = Factory(client)
        self.assertEqual(self.call(factory), (0, "ALREADY_DONE"))
        self.assertEqual(factory.called, 0)
        self.assertEqual(client.calls, [])
        self.assertEqual(len(self.usage_lines()), 1)
        self.assert_no_key_anywhere()

    # -- (자) dry run
    def test_dry_run(self):
        factory = Factory()
        self.assertEqual(self.call(factory, dry_run=True, key=False), (0, "DRY_RUN"))
        self.assertEqual(factory.called, 0)
        preview_path = self.day_dir / "request-preview.json"
        self.assertTrue(preview_path.exists())
        preview_text = preview_path.read_text(encoding="utf-8")
        preview = json.loads(preview_text)
        self.assertEqual(set(preview.keys()), {
            "model", "max_tokens", "output_config", "system_sha256", "record_lines",
            "decision_lines", "record_sha256", "decisions_sha256", "removed_amount_items",
            "masked_decision_items"})
        self.assertEqual(preview["model"], "claude-sonnet-5-5")
        self.assertEqual(preview["decision_lines"], len(DECISION_ROWS))
        self.assertEqual(preview["record_lines"], len(sent_record_lines()))
        for body in ("노출 상한", "reconcile", '"band"', "결정 색인", "독립 검토자"):
            self.assertNotIn(body, preview_text)
        self.assertFalse((self.day_dir / "review.json").exists())
        self.assertEqual(self.usage_lines(), [])
        self.assert_no_key_anywhere()

    # -- (차) API error
    def test_api_error_hides_message_and_key(self):
        exc = APIStatusError("overloaded; invalid x-api-key " + FAKE_KEY, 529)
        client = FakeClient(stream_exc=exc)
        self.assertEqual(self.call(Factory(client)), (7, "API_ERROR"))
        text = self.failed_text()
        self.assertIn("APIStatusError", text)
        self.assertIn("529", text)
        self.assertNotIn(FAKE_KEY, text)
        self.assertNotIn("overloaded", text)
        self.assertNotIn("invalid x-api-key", text)
        self.assertEqual(self.usage_lines(), [])
        self.assert_no_key_anywhere()

    # -- main: stdout line and unexpected errors
    def test_main_prints_ascii_line(self):
        with mock.patch.dict(os.environ, {MODULE.KEY_ENV: FAKE_KEY}):
            with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
                code = MODULE.main(["--day", DAY], repo_root=self.root, client_factory=Factory(), now=NOW)
        self.assertEqual(code, 0)
        line = self.out.getvalue()
        self.assertEqual(line, "llm-iccheck 2026-11-06 OK findings=1 dropped=2\n")
        line.encode("ascii")
        self.assert_no_key_anywhere()

    def test_main_unexpected_error(self):
        def boom(key):
            raise RuntimeError("factory failed with " + key)

        with mock.patch.dict(os.environ, {MODULE.KEY_ENV: FAKE_KEY}):
            with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
                code = MODULE.main(["--day", DAY], repo_root=self.root, client_factory=boom, now=NOW)
        self.assertEqual(code, 1)
        self.assertEqual(self.failed_text(),
                         "검토 못 함: 예상 못 한 오류 (RuntimeError) (UNEXPECTED)\n")
        self.assertEqual(self.out.getvalue(), "llm-iccheck 2026-11-06 UNEXPECTED findings=0 dropped=0\n")
        self.assertEqual(self.err.getvalue(), "")
        self.assertIsNone(re.search("Traceback", self.out.getvalue() + self.err.getvalue()))
        self.assert_no_key_anywhere()

    def test_day_must_be_iso_date(self):
        with self.assertRaises(ValueError):
            MODULE.run("../2026-11-06", repo_root=self.root, client_factory=Factory(), now=NOW)
        self.assertFalse((self.root / "workspace" / "outputs" / "llm").exists())


# Verbatim text from the task prompt (llm-iccheck-builder-prompt, SYSTEM_PROMPT block).
# The script stores it as unicode escapes (scripts/*.py are ASCII-only); this pins the decoded value.
EXPECTED_SYSTEM_PROMPT = """너는 투자 운영 기록의 독립 검토자다. 사용자 메시지에 두 자료가 있다.
- 결정 색인: 행마다 "D<번호>|"가 붙어 있다. 지금 효력이 있는 결정과 조건·만료가 적혀 있다.
- 오늘 연구 기록: 행마다 "R<번호>|"가 붙어 있다. 아침 통합점검이 쓴 JSON이다. 금액·수량은 지워져 [금액]·[수량]으로 보이며, 이것은 오류가 아니다.

할 일: 오늘 연구 기록이 결정 색인의 현재 결정과 어긋나는 곳을 찾는다. 예: 폐지되거나 대체된 기준을 아직 쓰는 문장, 결정과 다른 비율·기한·조건, 만료가 지난 결정을 살아 있는 것처럼 쓰는 곳, 날짜·세션이 서로 맞지 않는 곳.

규칙:
1. 발견마다 R행 하나와 D행 하나를 인용한다. line에는 행 번호만 쓰고, text에는 그 행의 글자를 6자 이상 그대로 옮긴다. 고쳐 쓰거나 줄이지 않는다.
2. 두 자료에 적힌 것만 근거로 한다. 추측, 일반론, 시장 전망, 매매 권고는 쓰지 않는다.
3. 발견은 중요한 것부터 최대 10개다. 어긋난 곳이 없으면 findings를 빈 목록으로 낸다.
4. summary_ko는 한국어 한두 문장으로, 무엇이 어떻게 다른지 쓴다.
5. severity: high = 오늘 지시나 보유 판단이 결정과 반대로 읽힐 수 있음, mid = 날짜·만료·조건·비율이 어긋남, low = 표기·설명만 다름.
6. checked_lines에는 읽은 R행 수와 D행 수를 적는다."""


class EscapedTextTests(unittest.TestCase):
    """The script source is ASCII-only; its decoded Korean text must match the task prompt."""

    def test_script_source_is_ascii(self):
        self.assertTrue((SCRIPT_DIR / "llm_pilot_iccheck.py").read_text(encoding="utf-8").isascii())

    def test_system_prompt_verbatim(self):
        self.assertEqual(MODULE.SYSTEM_PROMPT, EXPECTED_SYSTEM_PROMPT)

    def test_block_headers_and_alert_text(self):
        self.assertEqual(MODULE.DECISION_HEADER, "결정 색인(D행)\n")
        self.assertEqual(MODULE.RECORD_HEADER, "오늘 연구 기록(R행, 금액·수량 지움)\n")
        self.assertEqual(MODULE.SEVERITY_KO, {"high": "높음", "mid": "중간", "low": "낮음"})
        self.assertEqual(MODULE.ALERT_TITLE, "# 기록 대조 검토 %s — 결정 색인과 어긋난 곳 %d건")
        self.assertEqual(MODULE.ALERT_ITEM, "- %s · %s · R%d \"%s\" · D%d \"%s\"")
        self.assertEqual(MODULE.ALERT_FOOTER, "표시 전용: 코어 입력·매매 근거가 아님.")

    def test_failure_reasons_verbatim(self):
        self.assertEqual(
            MODULE.REASON_KO,
            {
                "no_record": "오늘 연구 기록 없음",
                "bad_record": "연구 기록을 읽을 수 없음",
                "no_decisions": "결정 색인 없음",
                "bad_decisions": "결정 색인을 읽을 수 없음",
                "no_key": "키 없음",
                "usage_unreadable": "사용 기록을 읽을 수 없음",
                "budget_spent": "이달 예산을 다 씀",
                "count_failed": "토큰 세기 실패 ",
                "count_shape": "토큰 수 응답 형식 다름",
                "too_large": "입력이 너무 큼",
                "budget_worst": "예상 최대 비용이 이달 예산을 넘음",
                "call_failed": "API 호출 실패 ",
                "bad_message": "응답 이상 ",
                "bad_shape": "응답 형식 다름",
                "unexpected": "예상 못 한 오류 (%s)",
            },
        )


if __name__ == "__main__":
    unittest.main()
