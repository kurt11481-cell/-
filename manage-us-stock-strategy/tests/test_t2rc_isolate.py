"""t2rc-isolate: the independent calculator (docs/claude/t2rc-oracle.py) treats a watch-only symbol isolated by T1
(result.json steps.bars.isolated) as not buyable, like the core's decide run (bar-isolate); an invalid isolation list
is ignored (the comparison runs as before).

The calculator is loaded read-only with importlib. Data are synthetic, in temporary folders only; the repository's
workspace/outputs is never read. TEST_ONLY data.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
ORACLE_PATH = ROOT / "docs/claude/t2rc-oracle.py"
DAY = "2026-11-14"
EV = "2026-11-13"


def load_oracle():
    spec = importlib.util.spec_from_file_location("t2rc_oracle_isolate", ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def t1_with(entries):
    return {"steps": {"bars": {"isolated": entries}}}


HELD = {"MU": 10}
MEMBERS = ["CRWD", "NVDA", "X"]


class T1IsolatedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = load_oracle()

    def iso(self, t1, held=HELD, members=MEMBERS):
        return self.oracle.t1_isolated(t1, held, members)

    # test 1
    def test_valid_list_returns_set(self):
        got = self.iso(t1_with([{"symbol": "X", "reason": "COLLECT_FAILED"}, {"symbol": "NVDA", "reason": ""}]))
        self.assertEqual(got, frozenset({"X", "NVDA"}))
        self.assertIsInstance(got, frozenset)

    def test_old_records_without_keys_return_empty(self):
        for t1 in ({}, {"steps": {}}, {"steps": {"bars": {}}}, {"steps": {"bars": {"ok": True}}}):
            with self.subTest(t1=t1):
                self.assertEqual(self.iso(t1), frozenset())

    # test 2
    def test_invalid_forms_are_ignored(self):
        cases = {
            "empty list": t1_with([]),
            "not a list": t1_with({"symbol": "X", "reason": "r"}),
            "string": t1_with("X"),
            "extra key": t1_with([{"symbol": "X", "reason": "r", "extra": 1}]),
            "missing reason": t1_with([{"symbol": "X"}]),
            "reason not str": t1_with([{"symbol": "X", "reason": None}]),
            "lower case": t1_with([{"symbol": "x", "reason": "r"}]),
            "outer space": t1_with([{"symbol": " X", "reason": "r"}]),
            "trailing space": t1_with([{"symbol": "X ", "reason": "r"}]),
            "empty symbol": t1_with([{"symbol": "", "reason": "r"}]),
            "symbol not str": t1_with([{"symbol": 7, "reason": "r"}]),
            "item not dict": t1_with(["X"]),
            "duplicate": t1_with([{"symbol": "X", "reason": "a"}, {"symbol": "X", "reason": "b"}]),
            "held": t1_with([{"symbol": "MU", "reason": "r"}]),
            "SOXX": t1_with([{"symbol": "SOXX", "reason": "r"}]),
            "GRID": t1_with([{"symbol": "GRID", "reason": "r"}]),
            "not a member": t1_with([{"symbol": "AMD", "reason": "r"}]),
            "one good one bad": t1_with([{"symbol": "X", "reason": "r"}, {"symbol": "AMD", "reason": "r"}]),
            "steps not dict": {"steps": ["bars"]},
            "bars not dict": {"steps": {"bars": "isolated"}},
            "t1 not dict": ["steps"],
        }
        for name, t1 in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.iso(t1), frozenset())

    def test_soxx_grid_rejected_even_if_listed_as_members(self):
        members = MEMBERS + ["SOXX", "GRID"]
        for sym in ("SOXX", "GRID"):
            with self.subTest(sym=sym):
                self.assertEqual(self.iso(t1_with([{"symbol": sym, "reason": "r"}]), members=members), frozenset())


class _Ind:
    def __init__(self):
        self.s = SimpleNamespace(index={"2026-11-12": 0, EV: 1}, split_suspected=False)

    def snapshot(self, i):
        return {"session": EV, "close": 10.0, "ema20": 9.0, "sigma60": 0.02}


class CircuitIsolatedTest(unittest.TestCase):
    """test 3: X and Y would both open a buy; isolating X removes only X."""

    @classmethod
    def setUpClass(cls):
        cls.oracle = load_oracle()

    def run_circuit(self, **kw):
        o = self.oracle
        ctx = SimpleNamespace(repo="unused", cal=None, ind={"X": _Ind(), "Y": _Ind()})
        ev = {"new_basis_met": True, "basis_met": True}
        with mock.patch.object(o, "registry_status", lambda repo, reg, sym, held, wm: (None, "OK")), \
                mock.patch.object(o, "compute_triggers", lambda *a, **k: {}), \
                mock.patch.object(o, "group_states", lambda trig, i: {}), \
                mock.patch.object(o, "evidence", lambda *a, **k: dict(ev)):
            return o.circuit_for_session(ctx, EV, set(), {"X", "Y"}, {}, {}, None, set(), set(), lambda s: 1, None, **kw)

    def test_buy_opens_without_isolation(self):
        opened, detail = self.run_circuit()
        self.assertEqual({(c["symbol"], c["side"]) for c in opened}, {("X", "buy"), ("Y", "buy")})
        self.assertEqual(detail["X"]["status"], "OK")

    def test_isolated_symbol_not_opened(self):
        opened, detail = self.run_circuit(isolated={"X"})
        self.assertNotIn("X", {c["symbol"] for c in opened})
        self.assertEqual(detail["X"]["status"], "ISOLATED")
        self.assertNotIn("buy", detail["X"])
        self.assertNotIn("sell", detail["X"])
        self.assertNotIn("triggers", detail["X"])
        self.assertEqual(detail["X"]["role"], "watch")
        # a symbol that is not isolated is treated as before
        self.assertEqual([(c["symbol"], c["side"]) for c in opened], [("Y", "buy")])
        self.assertEqual(detail["Y"]["status"], "OK")

    def test_default_equals_empty_isolation(self):
        self.assertEqual(self.run_circuit(), self.run_circuit(isolated=frozenset()))

    def test_isolated_keyword_only_default_empty(self):
        sig = inspect.signature(self.oracle.circuit_for_session)
        p = sig.parameters["isolated"]
        self.assertEqual(p.kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(p.default, frozenset())
        self.assertEqual(list(sig.parameters)[:11], ["ctx", "eval_session", "held", "members", "reg", "watch_members",
                                                     "facts", "s7_add", "s7_reduce", "mult_of", "c7_facts"])


class RedeployIsolatedTest(unittest.TestCase):
    """test 4: an ISOLATED symbol is never a redeployment candidate (status must be OK)."""

    @classmethod
    def setUpClass(cls):
        cls.oracle = load_oracle()

    def cands(self, x_status):
        o = self.oracle
        detail = {"MU": {"role": "held", "registry": "OK", "status": "OK"},
                  "X": {"role": "watch", "registry": "OK", "status": x_status, "buy": {}},
                  "Y": {"role": "watch", "registry": "OK", "status": "OK", "buy": {}}}
        env = {"ctx": SimpleNamespace(ind={"X": _Ind(), "Y": _Ind()}), "dec": {"evaluation_session": EV},
               "policy": {"card_stock_core": ["X", "Y"]}, "detail": detail, "open": set()}
        with mock.patch.object(o, "buy_requirements", lambda env, sym: ["ok"] * 5), \
                mock.patch.object(o, "stress_returns", lambda ind, i: (0.1, -0.1, [])):
            cands, _ = o.redeploy_candidates(env, "MU")
        return [c["symbol"] for c in cands]

    def test_ok_symbol_is_candidate(self):
        self.assertEqual(self.cands("OK"), ["X", "Y"])

    def test_isolated_symbol_left_out(self):
        self.assertEqual(self.cands("ISOLATED"), ["Y"])


class IsolatedForCheckTest(unittest.TestCase):
    """test 5: reads workspace/outputs/auto-core/<day>/result.json under the given repo only."""

    @classmethod
    def setUpClass(cls):
        cls.oracle = load_oracle()

    def write(self, repo, text):
        p = Path(repo) / "workspace/outputs/auto-core" / DAY / "result.json"
        p.parent.mkdir(parents=True)
        p.write_text(text, encoding="utf-8")

    def test_valid_result(self):
        with tempfile.TemporaryDirectory() as repo:
            self.write(repo, json.dumps(t1_with([{"symbol": "X", "reason": "COLLECT_FAILED"}])))
            self.assertEqual(self.oracle.isolated_for_check(repo, DAY, HELD, MEMBERS), frozenset({"X"}))

    def test_invalid_list_in_file_ignored(self):
        with tempfile.TemporaryDirectory() as repo:
            self.write(repo, json.dumps(t1_with([{"symbol": "MU", "reason": "r"}])))
            self.assertEqual(self.oracle.isolated_for_check(repo, DAY, HELD, MEMBERS), frozenset())

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as repo:
            self.assertEqual(self.oracle.isolated_for_check(repo, DAY, HELD, MEMBERS), frozenset())

    def test_broken_json(self):
        with tempfile.TemporaryDirectory() as repo:
            self.write(repo, '{"steps": {"bars": ')
            self.assertEqual(self.oracle.isolated_for_check(repo, DAY, HELD, MEMBERS), frozenset())


class CmdCheckWiringTest(unittest.TestCase):
    """test 6 (source check): a recording run of cmd_check would need a full decide-day fixture (decision.json, calendar,
    broker snapshot, S7 review, registry, watch list, policy, state, pages). The source check confirms the order: input
    sha check -> held/members -> isolated_for_check -> circuit_for_session(..., isolated=isolated)."""

    @classmethod
    def setUpClass(cls):
        cls.src = inspect.getsource(load_oracle().cmd_check).splitlines()

    def line_of(self, needle):
        hits = [i for i, ln in enumerate(self.src) if needle in ln]
        self.assertEqual(len(hits), 1, needle)
        return hits[0]

    def test_isolated_passed_after_sha_check(self):
        sha_end = self.line_of('reason="INPUT_SHA_MISMATCH"')
        members = self.line_of("members = [c for c in wm if c not in held]")
        read = self.line_of("isolated = isolated_for_check(repo, day, held, members)")
        call = self.line_of("opened, detail = circuit_for_session(")
        self.assertLess(sha_end, members)
        self.assertLess(members, read)
        self.assertLess(read, call)
        call_text = " ".join(self.src[call:call + 2])
        self.assertIn("isolated=isolated", call_text)

    def test_replay_call_unchanged(self):
        src = inspect.getsource(load_oracle().cmd_replay)
        self.assertIn("circuit_for_session(ctx, d, set(hold), set(members), reg, wm, [], s7_add, s7_reduce, mult_of)", src)
        self.assertNotIn("isolated", src)


class SelftestTest(unittest.TestCase):
    """test 7: the selftest command still ends with 0 (repo = an empty temp folder: no repository data read)."""

    def test_selftest_exit_zero(self):
        o = load_oracle()
        with tempfile.TemporaryDirectory() as repo, mock.patch("builtins.print"):
            self.assertEqual(o.cmd_selftest(SimpleNamespace(repo=repo)), 0)


if __name__ == "__main__":
    unittest.main()
