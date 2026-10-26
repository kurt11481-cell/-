"""t2rc-eqnone4: the independent calculator (docs/claude/t2rc-oracle.py) must not divide by a missing equity, and the
runner pin (docs/claude/t2rc-check-run.ps1 line 16) must equal the calculator's LF-normalized sha256.

The calculator is loaded read-only with importlib; nothing is written. TEST_ONLY data.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORACLE_PATH = ROOT / "docs/claude/t2rc-oracle.py"
RUNNER_PATH = ROOT / "docs/claude/t2rc-check-run.ps1"


def load_oracle():
    spec = importlib.util.spec_from_file_location("t2rc_oracle_eq_none", ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Obj:
    pass


def make_env(equity, with_series=True):
    ser = _Obj()
    ser.index = {"2026-10-23": 0}
    ser.raw_c = [100.0]
    ctx = _Obj()
    ctx.ser = {"AAA": ser} if with_series else {}
    return {"ctx": ctx, "dec": {"evaluation_session": "2026-10-23"},
            "s7": {"equity": {"closing_equity_usd": equity}}, "held": {"AAA": 5}}


class OraclePinTest(unittest.TestCase):
    def test_runner_pin_equals_oracle_lf_sha256(self):
        actual = hashlib.sha256(ORACLE_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        runner = RUNNER_PATH.read_text(encoding="utf-8")
        found = re.findall(r'^\$ExpectedOracleSha256 = "([0-9a-f]{64})"', runner, re.MULTILINE)
        self.assertEqual(len(found), 1, "runner pin line not found")
        self.assertEqual(actual, found[0], "oracle LF sha256 actual=%s runner pin=%s" % (actual, found[0]))


class WeightsNowEquityNoneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = load_oracle()

    def test_equity_none_returns_none_pair(self):
        self.assertEqual(self.oracle.weights_now(make_env(None)), (None, None))

    def test_equity_missing_string_returns_none_pair(self):
        self.assertEqual(self.oracle.weights_now(make_env("")), (None, None))

    def test_equity_present_unchanged(self):
        w, eq = self.oracle.weights_now(make_env(1000.0))
        self.assertEqual(eq, 1000.0)
        self.assertAlmostEqual(w["AAA"], 5 * 100.0 / 1000.0)

    def test_no_series_branch_unchanged(self):
        self.assertEqual(self.oracle.weights_now(make_env(1000.0, with_series=False)), (None, 1000.0))


class TicketCheckEquityNoneTest(unittest.TestCase):
    """Static check of the ticket_check call site: an equity None must be recorded as a failed match before the
    arithmetic that multiplies by eq (no TypeError)."""

    def test_call_site_guards_eq_none(self):
        lines = ORACLE_PATH.read_text(encoding="utf-8").splitlines()
        call = next(i for i, ln in enumerate(lines) if ln.strip() == "w, eq = weights_now(env)" and "ticket_check" in "\n".join(lines[max(0, i - 25):i]))
        guard = "\n".join(lines[call + 1:call + 5])
        self.assertIn("eq is None", guard)
        self.assertIn("EQUITY_MISSING", guard)
        self.assertIn('out["match"] = False', guard)
        self.assertIn("return out", guard)


if __name__ == "__main__":
    unittest.main()
