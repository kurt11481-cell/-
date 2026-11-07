import importlib.util
import json
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("llm_pilot_common", SCRIPT_DIR / "llm_pilot_common.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


FAKE_KEY = "fake-key-FOR-TEST-7Q9Z"
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
SDK_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_CUSTOM_HEADERS",
    "ANTHROPIC_PROFILE",
)


def fake_record():
    return {
        "date": "2026-11-06",
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
                "s7": {"session": "2026-11-06", "fresh": True, "e": 0.62, "band": "mid",
                       "newBuyPaused": False},
                "capBreaches": [],
            },
        },
        "status": [
            {"name": "잔고", "value": RECON},
            {"name": "시나리오", "value": "06:40 점검 · 10/28 실적 · 3.0% 한도 · 3:1 분할"},
        ],
        "notes": ["AAA 4321주 유지", "지정가 $98.76", "차이 98.76 달러"],
        "positions": {"AAA": {"marketValue": 533432.45, "avg_cost": 123.45, "pnlUsd": 56.78,
                              "weight": 0.54}},
    }


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def numeric_only(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, dict):
        return all(numeric_only(x) for x in v.values())
    if isinstance(v, list):
        return all(numeric_only(x) for x in v)
    return False


class StripAmountsTests(unittest.TestCase):
    def test_strip_amounts_removes_money_and_counts(self):
        original = fake_record()
        clean, removed = MODULE.strip_amounts(original)
        self.assertEqual(original, fake_record(), "original must not change")
        self.assertGreater(removed, 0)

        account = clean["account"]
        allowed = {"vsHwmPct", "firstCushionPct", "approachPct", "maxPct", "n", "reconcile",
                   "exposure", "holdings"}
        self.assertTrue(set(account.keys()) <= allowed, set(account.keys()) - allowed)
        self.assertNotIn("openOrders", account)
        self.assertNotIn("firstCushionUsd", account)
        for item in account["holdings"]:
            self.assertTrue(set(item.keys()) <= {"code", "weight", "mult"}, item)
        self.assertEqual([h["weight"] for h in account["holdings"]], [0.54, 0.46])
        self.assertEqual([h["mult"] for h in account["holdings"]], [1, 3])
        self.assertEqual(account["vsHwmPct"], -0.4)
        self.assertEqual(account["exposure"]["s7"]["e"], 0.62)
        self.assertEqual(account["reconcile"], "일치")
        self.assertEqual(clean["positions"]["AAA"], {"weight": 0.54})

        for key, value in walk(clean):
            norm = str(key).lower().replace("_", "")
            if norm in MODULE.AMOUNT_KEYS or norm.endswith("usd"):
                self.assertFalse(numeric_only(value), (key, value))

        text = json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True)
        self.assertIsNone(re.search(r"\$\s?\d", text))
        self.assertIsNone(re.search(r"\d\s?주", text))
        self.assertIsNone(re.search(r"\d\s?(달러|USD)", text))
        for secret in SECRET_NUMBERS:
            self.assertNotIn(secret, text)
        self.assertIn("키움 AAA [수량]·BBB [수량] = 상태 파일 · 주문 가능 [금액]", text)
        for keep in ("06:40", "10/28", "3.0%", "3:1"):
            self.assertIn(keep, text)

    def test_mask_text_decision_forms(self):
        text = (
            "| **AAA 4321주 유지** · 2026-10-08 | AAA ② 4321주 LOC $98.76 |\n"
            "| 상태 파일은 대조 보류로 옛 값 4321 | 키움 AAA 4321·BBB 8765 |\n"
            "| 06:40 점검 · 10/28 · 3.0% · 3:1 분할 | 12 달러 · 7 USD · 5 shares · 보유 33 |\n"
        )
        masked, n = MODULE.mask_text(text)
        self.assertGreater(n, 0)
        for secret in ("4321", "8765", "98.76", "12 달러", "7 USD", "5 shares", "보유 33"):
            self.assertNotIn(secret, masked)
        for keep in ("06:40", "10/28", "3.0%", "3:1", "2026-10-08"):
            self.assertIn(keep, masked)
        self.assertIn("옛 값 [수량]", masked)
        self.assertIn("키움 AAA [수량]·BBB [수량]", masked)
        self.assertIn("LOC [금액]", masked)

    def test_escaped_korean_text_decodes_verbatim(self):
        # scripts/*.py are ASCII-only, so Korean is stored as unicode escapes; pin decoded values.
        self.assertTrue((SCRIPT_DIR / "llm_pilot_common.py").read_text(encoding="utf-8").isascii())
        self.assertEqual(MODULE.AMOUNT_TAG, "[금액]")
        self.assertEqual(MODULE.COUNT_TAG, "[수량]")
        self.assertEqual(MODULE.FAILED_LINE, "검토 못 함: %s (%s)\n")
        # The re module decodes \\uXXXX in patterns; decoded, they equal the spec patterns.
        decoded = [
            re.sub(r"\\u([0-9a-f]{4})", lambda m: chr(int(m.group(1), 16)), pattern.pattern)
            for pattern, _repl in MODULE.MASK_RULES
        ]
        self.assertEqual(
            decoded,
            [
                r"\$\s?\d[\d,]*(?:\.\d+)?",
                r"\d[\d,]*(?:\.\d+)?\s?(?:달러|USD)",
                r"\d[\d,]*\s?(?:주|shares?)",
                r"\b([A-Z]{2,5})\s(\d[\d,]*)(?![\d:/%.])",
                r"(옛 값|보유|수량|잔고)\s?(\d[\d,]*)(?![\d:/%.])",
            ],
        )
        self.assertEqual([repl for _p, repl in MODULE.MASK_RULES],
                         ["[금액]", "[금액]", "[수량]", "\\1 [수량]", "\\1 [수량]"])
        # Each Korean word in the escaped patterns matches its literal form.
        for literal, expected in (
            ("12달러", "[금액]"),
            ("12 달러", "[금액]"),
            ("7주", "[수량]"),
            ("옛 값 9", "옛 값 [수량]"),
            ("보유 9", "보유 [수량]"),
            ("수량 9", "수량 [수량]"),
            ("잔고 9", "잔고 [수량]"),
        ):
            self.assertEqual(MODULE.mask_text(literal), (expected, 1), literal)

    def test_mask_text_leaves_plain_text(self):
        masked, n = MODULE.mask_text("결정 없음 · AAA 비교 중")
        self.assertEqual((masked, n), ("결정 없음 · AAA 비교 중", 0))


class LineAndQuoteTests(unittest.TestCase):
    LINES = ['{"vsHwmPct": -0.4,', '  "reconcile":   "일치"', "third row text here"]

    def test_number_lines(self):
        self.assertEqual(MODULE.number_lines("a\n\nb", "R"), "R1|a\nR2|\nR3|b")

    def test_quote_ok(self):
        q = MODULE.quote_ok
        self.assertTrue(q(self.LINES, 1, '"vsHwmPct": -0.4,'))
        self.assertTrue(q(self.LINES, 2, '"reconcile": "일치"'))
        self.assertTrue(q(self.LINES, 3, "R3|third row"))
        self.assertTrue(q(self.LINES, 3, "D3| third   row"))
        self.assertFalse(q(self.LINES, 1, "vsHwm"))
        self.assertFalse(q(self.LINES, 2, '"vsHwmPct"'))
        self.assertFalse(q(self.LINES, 0, '"vsHwmPct"'))
        self.assertFalse(q(self.LINES, 4, '"vsHwmPct"'))
        self.assertFalse(q(self.LINES, True, '"vsHwmPct"'))


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _rec(self, ts, pilot, cost):
        return {"ts_kst": ts, "pilot": pilot, "model": "claude-sonnet-5-5", "input_tokens": 1,
                "output_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                "batch": False, "cost_usd_est": cost, "status": "RECEIVED"}

    def test_month_spend_filters_pilot_and_month(self):
        self.assertEqual(MODULE.month_spend(self.root, "iccheck", "2026-11"), 0.0)
        MODULE.append_usage(self.root, self._rec("2026-11-02T07:00:00+09:00", "iccheck", 1.25))
        MODULE.append_usage(self.root, self._rec("2026-11-05T07:00:00+09:00", "iccheck", 0.5))
        MODULE.append_usage(self.root, self._rec("2026-10-31T07:00:00+09:00", "iccheck", 4.0))
        MODULE.append_usage(self.root, self._rec("2026-11-03T07:00:00+09:00", "news", 2.0))
        self.assertAlmostEqual(MODULE.month_spend(self.root, "iccheck", "2026-11"), 1.75)
        self.assertAlmostEqual(MODULE.month_spend(self.root, "news", "2026-11"), 2.0)
        lines = MODULE.usage_path(self.root).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(list(json.loads(lines[0]).keys()), list(MODULE.USAGE_KEYS))

    def test_month_spend_raises_on_broken_line(self):
        MODULE.append_usage(self.root, self._rec("2026-11-02T07:00:00+09:00", "iccheck", 1.0))
        with open(MODULE.usage_path(self.root), "a", encoding="utf-8") as fh:
            fh.write("{not json\n")
        with self.assertRaises(ValueError):
            MODULE.month_spend(self.root, "iccheck", "2026-11")

    def test_month_spend_raises_on_missing_cost(self):
        path = MODULE.usage_path(self.root)
        path.parent.mkdir(parents=True)
        path.write_text('{"ts_kst": "2026-11-02T07:00:00+09:00", "pilot": "iccheck"}\n',
                        encoding="utf-8")
        with self.assertRaises(ValueError):
            MODULE.month_spend(self.root, "iccheck", "2026-11")

    def test_estimate_cost(self):
        ec = MODULE.estimate_cost
        self.assertAlmostEqual(
            ec("claude-sonnet-5-5", {"input_tokens": 1_000_000, "output_tokens": 100_000}), 3.0)
        self.assertAlmostEqual(
            ec("claude-sonnet-5-5", {"input_tokens": 1_000_000, "output_tokens": 100_000},
               batch=True), 1.5)
        self.assertAlmostEqual(
            ec("claude-sonnet-5-5", {"cache_read_input_tokens": 1_000_000}), 0.2)
        self.assertAlmostEqual(
            ec("claude-opus-5-5", {"cache_read_input_tokens": 1_000_000}), 0.2)
        self.assertAlmostEqual(
            ec("claude-sonnet-5-5", {"cache_creation_input_tokens": 1_000_000}), 2.5)
        self.assertAlmostEqual(
            ec("claude-haiku-5-5", {"input_tokens": 100_000, "output_tokens": 1_000_000}),
            0.01 + 0.5)
        self.assertAlmostEqual(
            ec("claude-haiku-5-5", {"input_tokens": 100_001, "output_tokens": 1_000_000}),
            100_001 * 0.5 / 1_000_000 + 2.5)
        self.assertAlmostEqual(
            ec("claude-sonnet-5-5-20261001",
               SimpleNamespace(input_tokens=1_000_000, output_tokens=0,
                               cache_creation_input_tokens=None, cache_read_input_tokens=None)),
            2.0)
        with self.assertRaises(ValueError):
            ec("claude-unknown", {"input_tokens": 1})

    def test_atomic_write_and_failed(self):
        day_dir = self.root / "workspace" / "outputs" / "llm" / "iccheck" / "2026-11-06"
        MODULE.write_failed(day_dir, "NO_RECORD", "오늘 연구 기록 없음")
        self.assertEqual((day_dir / "failed.md").read_bytes().decode("utf-8"),
                         "검토 못 함: 오늘 연구 기록 없음 (NO_RECORD)\n")
        self.assertEqual(sorted(p.name for p in day_dir.iterdir()), ["failed.md"])
        MODULE.atomic_write_text(day_dir / "x.txt", "a\nb\n")
        self.assertEqual((day_dir / "x.txt").read_bytes(), b"a\nb\n")


class KeyAndClientTests(unittest.TestCase):
    def test_load_key(self):
        with mock.patch.dict(os.environ, {MODULE.KEY_ENV: "  " + FAKE_KEY + "\n"}):
            self.assertEqual(MODULE.load_key(), FAKE_KEY)
        with mock.patch.dict(os.environ, {MODULE.KEY_ENV: "   "}):
            self.assertIsNone(MODULE.load_key())
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(MODULE.KEY_ENV, None)
            self.assertIsNone(MODULE.load_key())

    def test_make_client_clears_sdk_env_and_pins_base_url(self):
        calls = []

        class FakeAnthropic:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        fake = types.ModuleType("anthropic")
        fake.Anthropic = FakeAnthropic
        env = {name: "x-" + name for name in SDK_VARS}
        with mock.patch.dict(os.environ, env), mock.patch.dict(sys.modules, {"anthropic": fake}):
            client = MODULE.make_client(FAKE_KEY)
            for name in SDK_VARS:
                self.assertNotIn(name, os.environ)
        self.assertIsInstance(client, FakeAnthropic)
        self.assertEqual(calls, [{"api_key": FAKE_KEY, "base_url": "https://api.anthropic.com",
                                  "max_retries": 1, "timeout": 120.0}])
        self.assertIsNot(sys.modules.get("anthropic"), fake)

    def test_api_error_label_hides_message(self):
        class APIStatusError(Exception):
            def __init__(self, msg, status_code):
                super().__init__(msg)
                self.status_code = status_code

        label = MODULE.api_error_label(APIStatusError("invalid x-api-key " + FAKE_KEY, 429))
        self.assertEqual(label, "APIStatusError HTTP 429")
        self.assertNotIn(FAKE_KEY, label)
        self.assertNotIn("invalid", label)
        self.assertEqual(MODULE.api_error_label(ValueError("secret " + FAKE_KEY)), "ValueError")


class MessageTests(unittest.TestCase):
    def _msg(self, model="claude-sonnet-5-5", stop="end_turn"):
        return SimpleNamespace(model=model, stop_reason=stop, content=[
            SimpleNamespace(type="thinking", thinking="ignored"),
            SimpleNamespace(type="text", text='{"a": '),
            SimpleNamespace(type="text", text="1}"),
        ])

    def test_check_message(self):
        cm = MODULE.check_message
        expected = "claude-sonnet-5-5"
        self.assertIsNone(cm(self._msg(), expected))
        self.assertIsNone(cm(self._msg(model="claude-sonnet-5-5-20261001"), expected))
        self.assertEqual(cm(self._msg(model="claude-sonnet-5"), expected), "MODEL_MISMATCH")
        self.assertEqual(cm(self._msg(model="claude-sonnet-5-5-2026"), expected), "MODEL_MISMATCH")
        self.assertEqual(cm(self._msg(model="claude-opus-5-5"), expected), "MODEL_MISMATCH")
        self.assertEqual(cm(self._msg(stop="refusal"), expected), "REFUSAL")
        self.assertEqual(cm(self._msg(stop="max_tokens"), expected), "MAX_TOKENS")
        self.assertEqual(cm(self._msg(stop="tool_use"), expected), "BAD_STOP")

    def test_response_text_skips_thinking(self):
        self.assertEqual(MODULE.response_text(self._msg()), '{"a": 1}')


if __name__ == "__main__":
    unittest.main()
