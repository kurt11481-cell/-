"""Opt-in learning block of the read-only journal scorer (f-evo-loop step 1, display only, grade D).

Synthetic calendars, closes, decision folders, S7 files, museum and epochs files in temp folders only. The real
journal, decide output, state, policy and docs files are never read or written.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import portfolio_review_journal as journal_module  # noqa: E402
import score_decision_journal as scorer  # noqa: E402


def weekdays(start: str, count: int) -> list[str]:
    days, cursor = [], date.fromisoformat(start)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


S = weekdays("2026-03-02", 200)
CALENDAR = {"sessions": {day: {"core_close_at": f"{day}T20:00:00+00:00"} for day in S},
            "identity": {"calendar_version": "test", "calendar_sha256": "0" * 64,
                         "coverage_start": S[0], "coverage_end": S[-1], "authority_status": "ACTIVE"}}
NO_ACTIONS = {"status": "MISSING", "sha256": None, "errors": [], "actions": []}
NO_SPY = {"status": "MISSING", "closes": {}, "errors": []}
SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE", "ZZZ")
OK_TEXT = "통과"


def after(session: str) -> datetime:
    return datetime.fromisoformat(f"{session}T21:00:00+00:00")


def flat_closes(**overrides: dict[str, str]) -> dict[str, dict[str, str]]:
    closes = {symbol: {day: "100" for day in S} for symbol in SYMBOLS}
    for symbol, values in overrides.items():
        closes.setdefault(symbol, {day: "100" for day in S}).update(values)
    return closes


def epochs_doc(*entries: tuple[str, str]) -> dict:
    lines = [{"scope": scope, "first_run_day": day, "commit": "abc1234", "note": "test"} for scope, day in entries]
    return {"status": "OK", "document": {"schema": scorer.EPOCHS_SCHEMA, "epochs": lines}, "errors": []}


EPOCHS_ALL = epochs_doc(("ALL", "2026-01-01"))
MISSING = {"status": "MISSING", "document": None, "errors": []}


def cells(**states: tuple[str, str]) -> list[dict]:
    """Six requirement cells, ok unless overridden: c1=("no", "text") sets cell index 0 and so on."""
    out = [{"s": "ok", "t": OK_TEXT} for _ in range(5)] + [{"s": "wait", "t": "user"}]
    for name, (state, text) in states.items():
        out[int(name[1:]) - 1] = {"s": state, "t": text}
    return out


def sym(*, role: str = "member", buy_approved: bool = True, buy: bool = True, sell: bool = False,
        sigma: float | None = 0.02, status: str = "OK", row: list[dict] | None = None,
        shock_open: bool | None = False) -> dict:
    return {"role": role, "buy_approved": buy_approved, "buy": buy, "sell": sell, "sigma": sigma,
            "status": status, "row": row or cells(), "shock_open": shock_open}


def doc(i: int, specs: dict[str, dict] | None = None, *, status: str = "OK", reasons: tuple = (),
        candidates: tuple = (), blocked: tuple = (), tickets: tuple = (), shock_open: bool | None = False,
        event_date: str | None = None, research: str = "OK", generated: str | None = None, commit: str = "c1",
        **extra: object) -> dict:
    """A planned decision.json for evaluation session S[i] (run day = buy session = S[i + 1])."""
    specs = specs if specs is not None else {"ZZZ": sym(buy=False)}
    day = S[i + 1]
    document = {
        "status": status, "run_day_kst": day, "evaluation_session": S[i], "buy_session": day,
        "generated_at": generated or f"{day}T07:45:00+09:00", "commit_sha": commit, "reasons": list(reasons),
        "no_new_session": False, "carried_from": None,
        "inputs": {"research_record": {"status": research},
                   "s7_review": {"path": f"workspace/outputs/auto-core/{day}/s7/review.json"}},
        "symbols": {name: {"symbol": name, "role": spec["role"], "status": spec["status"],
                           "buy_approved": spec["buy_approved"],
                           "indicators": {"sigma60": spec["sigma"]} if spec["sigma"] is not None else {}}
                    for name, spec in specs.items()},
        "evidence": {name: {"buy": {"basis_met": spec["buy"]}, "sell": {"basis_met": spec["sell"]}}
                     for name, spec in specs.items()},
        "buy_requirements": [{"code": name, "add": spec["role"] == "held", "c": spec["row"]}
                             for name, spec in specs.items()],
        "candidates": [{"symbol": name, "side": side} for name, side in candidates],
        "blocked": [{"symbol": name, "side": side, "reasons": list(why)} for name, side, why in blocked],
        "tickets": list(tickets),
        "shock": {"status": "ok", "open": shock_open,
                  "event": {"date": event_date, "c0": 100.0} if event_date else None,
                  "by_symbol": {name: {"status": "ok", "open": spec["shock_open"], "rg": {"RG1": "no"}}
                                for name, spec in specs.items()}},
    }
    document.update(extra)
    return document


def day_item(document: dict, day: str | None = None) -> dict:
    raw = json.dumps(document, sort_keys=True).encode("utf-8")
    return {"day": day or document["run_day_kst"], "sha256": hashlib.sha256(raw).hexdigest(), "document": document}


def learn(documents: list, *, closes: dict | None = None, s7: dict | None = None, tickets: list | None = None,
          ticket_results: list | None = None, results: list | None = None, museum: dict | None = None,
          epochs: dict | None = None, previous: list | None = None, as_of: datetime | None = None,
          calendar: dict | None = CALENDAR, root_status: str = "OK") -> dict:
    items = [entry if "day" in entry and ("document" in entry or "error" in entry) else day_item(entry)
             for entry in documents]
    s7_by_day = {item["day"]: {"status": "OK", "reduce": []} for item in items}
    s7_by_day.update(s7 or {})
    return scorer.score_learning(
        decision_days=items, s7_by_day=s7_by_day, results=results or [], ticket_results=ticket_results or [],
        tickets=tickets or [], calendar=calendar, closes=closes if closes is not None else flat_closes(),
        unverified={}, corporate_actions=NO_ACTIONS, museum=museum or MISSING,
        epochs=epochs if epochs is not None else EPOCHS_ALL, previous_days=previous,
        evaluation_as_of=as_of or after(S[-1]), decisions_root_status=root_status)


def units_of(learning: dict, symbol: str, side: str = "buy") -> list[dict]:
    return [unit for unit in learning["gate_units"] if unit["symbol"] == symbol and unit["side"] == side]


def day_row(learning: dict, day: str) -> dict:
    return next(row for row in learning["decision_days"] if row["day"] == day)


def horizon(items: list[dict], sessions: int) -> dict:
    return next(item for item in items if item["horizon_sessions"] == sessions)


def episodes_of(learning: dict, symbol: str, side: str = "buy") -> list[dict]:
    return [episode for episode in learning["gate_episodes"] if episode["symbol"] == symbol and episode["side"] == side]


# ---------------------------------------------------------------------------------------------------------------
# a. default path
# ---------------------------------------------------------------------------------------------------------------

class CliCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="score_learning_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "auto-core"
        self.journal_path = self.tmp / "decision_journal.json"
        self.output_root = self.tmp / "scores"
        self.museum = self.tmp / "failure-museum.json"
        self.epochs = self.tmp / "gate-rule-epochs.json"
        self.epochs.write_text(json.dumps(EPOCHS_ALL["document"]), encoding="utf-8")
        self.inputs = {"calendar": CALENDAR, "calendar_failure": None, "closes": flat_closes(AAA={S[16]: "110"}),
                       "unverified": {}, "close_histories": {}, "corporate_actions": NO_ACTIONS, "benchmark": NO_SPY}

    def write_day(self, document: dict, day: str | None = None) -> Path:
        path = self.root / (day or document["run_day_kst"]) / "decision.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def record_journal_ticket(self) -> None:
        schema = json.loads(journal_module.JOURNAL_SCHEMA.read_text(encoding="utf-8"))
        document = {key: rule["const"] for key, rule in schema["properties"].items() if "const" in rule}
        self.journal_path.write_text(json.dumps({**document, "entries": []}), encoding="utf-8")
        decision = {"run_day_kst": S[10], "buy_session": S[11], "decision_mode": "apply",
                    "evaluation_session": S[10], "no_action": {"value": False, "reasons": []},
                    "commit_sha": "a" * 40, "outcomes": [],
                    "tickets": [{"ticket_id": "AT-20260316-AAA-1", "ticker": "AAA", "side": "buy", "type": "LOC",
                                 "price": 101, "qty": 10, "amount": 1010, "session": S[11],
                                 "decision_key": "d" * 64, "priceRule": "TEST_ONLY", "evidence": {"r": "1/2"}}]}
        journal_module.append_auto_core_entries(journal_path=self.journal_path, decision=decision,
                                                decision_sha256="e" * 64, expected_head=journal_module.GENESIS_HASH,
                                                recheck=lambda: [])

    def run_main(self, *extra: str, output_root: Path | None = None) -> tuple[int, str, dict]:
        root = output_root or self.output_root
        before = set(root.glob("*/" + scorer.REPORT_FILE)) if root.is_dir() else set()
        buffer = io.StringIO()
        with mock.patch.object(scorer, "load_inputs", return_value=self.inputs), contextlib.redirect_stdout(buffer):
            code = scorer.main(["--journal", str(self.journal_path), "--output-root", str(root),
                                "--decisions-root", str(self.root), "--evaluation-as-of", after(S[-1]).isoformat(),
                                "--event-calendar", str(self.tmp / "no-event-calendar.json"),
                                "--museum", str(self.museum), "--epochs", str(self.epochs), *extra])
        written = sorted(set(root.glob("*/" + scorer.REPORT_FILE)) - before)
        self.assertEqual(len(written), 1)
        return code, buffer.getvalue(), json.loads(written[0].read_text(encoding="utf-8"))


class DefaultPathTests(CliCase):
    def test_without_the_flag_nothing_changes_and_with_it_only_learning_is_added(self) -> None:
        self.record_journal_ticket()
        ticket = {"ticket_id": "AT-20260317-BBB-1", "mode": "compare", "ticker": "BBB", "side": "sell",
                  "type": "LOC", "price": 99.0, "qty": 5, "session": S[12], "decision_key": "k" * 64,
                  "evidence": {"weak": ["C6"]}}
        self.write_day(doc(10, {"AAA": sym(), "BBB": sym(role="held", buy=False, sell=True)}))
        self.write_day(doc(11, {"AAA": sym()}, tickets=(ticket,)))
        plain_code, plain_out, plain = self.run_main(output_root=self.tmp / "plain")
        learn_code, learn_out, learned = self.run_main("--learning", output_root=self.tmp / "learned")
        self.assertNotIn("learning", plain)
        self.assertIn("learning", learned)
        self.assertEqual(plain_code, learn_code)
        self.assertEqual(plain_code, 0)
        for key in set(plain) | set(learned):
            if key in ("learning", "close_histories"):
                continue
            with self.subTest(key=key):
                self.assertEqual(plain[key], learned[key])
        plain_lines = plain_out.splitlines()
        learn_lines = learn_out.splitlines()
        self.assertEqual(learn_lines[:len(plain_lines) - 1], plain_lines[:-1])  # the last line is the report path
        self.assertTrue(any(line.startswith("[학습 채점]") for line in learn_lines))
        self.assertFalse(any(line.startswith("[학습") for line in plain_lines))
        self.assertEqual((learned["order_authority"], learned["quantity_authority"]), (False, "none"))

    def test_the_core_style_call_never_reaches_learning_code(self) -> None:
        self.write_day(doc(10, {"AAA": sym()}))
        guard = mock.Mock(side_effect=AssertionError("learning code ran"))
        with mock.patch.object(scorer, "score_learning", guard), \
                mock.patch.object(scorer, "load_decision_days", guard), \
                mock.patch.object(scorer, "find_previous_learning", guard), \
                mock.patch.object(scorer, "load_learning_document", guard):
            code, _out, report = self.run_main()
        self.assertEqual(code, 0)
        self.assertNotIn("learning", report)
        guard.assert_not_called()


# ---------------------------------------------------------------------------------------------------------------
# b. decision days and preservation
# ---------------------------------------------------------------------------------------------------------------

def empty_frame(day: str) -> dict:
    return {"status": "HOLD", "reasons": ["T1_RESULT_MISSING"], "run_day_kst": day, "evaluation_session": None,
            "buy_session": None, "generated_at": f"{day}T07:45:00+09:00", "commit_sha": "c1", "symbols": {},
            "evidence": {}, "buy_requirements": [], "candidates": [], "blocked": [], "tickets": [], "shock": {},
            "no_new_session": False, "carried_from": None, "inputs": {}}


class DecisionDayTests(unittest.TestCase):
    def test_hold_after_the_plan_is_eligible_and_adds_its_day_gates(self) -> None:
        learning = learn([doc(10, {"AAA": sym()}, status="HOLD", reasons=("G1_S7_FAIL_CLOSED:R0",))])
        row = day_row(learning, S[11])
        self.assertEqual((row["eligible"], row["exclude_reason"]), (True, None))
        self.assertEqual(units_of(learning, "AAA")[0]["gates"], ["CIRCUIT_NEW_EVIDENCE", "G1_S7_FAIL_CLOSED"])
        self.assertFalse(units_of(learning, "AAA")[0]["binding"])

    def test_empty_frames_fail_and_other_exclusions_neither_join_nor_break(self) -> None:
        learning = learn([doc(10, {"AAA": sym()}), empty_frame(S[12]), doc(12, {"AAA": sym()}),
                          doc(13, {"AAA": sym()}, status="FAIL"), doc(14, {"AAA": sym()})])
        self.assertEqual(day_row(learning, S[12])["exclude_reason"], "PLAN_NOT_RUN")
        self.assertEqual(day_row(learning, S[14])["exclude_reason"], "STATUS_FAIL")
        episodes = episodes_of(learning, "AAA")
        self.assertEqual([(episode["first_day"], episode["days"]) for episode in episodes], [(S[11], 3)])

    def test_duplicate_sessions_no_new_session_and_shape(self) -> None:
        later = doc(10, {"AAA": sym()})
        later["run_day_kst"] = S[12]
        short = doc(13, {"AAA": sym(row=cells()[:5])})
        learning = learn([doc(10, {"AAA": sym()}), day_item(later, S[12]),
                          doc(15, {"AAA": sym()}, no_new_session=True), short])
        self.assertEqual(day_row(learning, S[11])["exclude_reason"], "DUPLICATE_SESSION")
        self.assertTrue(day_row(learning, S[12])["eligible"])
        self.assertEqual(day_row(learning, S[12])["exclude_reason"], None)
        self.assertEqual(day_row(learning, S[14])["exclude_reason"], "DECISION_SHAPE_UNKNOWN")
        self.assertEqual(day_row(learning, S[16])["exclude_reason"], "NO_NEW_SESSION")
        no_new = learn([doc(11, {"AAA": sym()}, no_new_session=True)])
        self.assertEqual(day_row(no_new, S[12])["exclude_reason"], "NO_NEW_SESSION")
        self.assertEqual(no_new["gate_units"], [])

    def test_same_day_rerun_is_rewritten_and_stays_eligible(self) -> None:
        first = learn([doc(10, {"AAA": sym()})])
        rerun = doc(10, {"AAA": sym()}, generated=f"{S[11]}T09:30:00+09:00", commit="c2")
        second = learn([rerun], previous=first["decision_days"])
        row = day_row(second, S[11])
        self.assertEqual((row["flags"], row["eligible"]), (["REWRITTEN"], True))
        self.assertEqual(row["first_sha256"], day_row(first, S[11])["sha256"])
        self.assertNotEqual(row["sha256"], row["first_sha256"])
        self.assertEqual(row["first_generated_at"], f"{S[11]}T07:45:00+09:00")

    def test_other_changes_break_preservation_and_the_mark_stays(self) -> None:
        original = doc(10, {"AAA": sym()})
        first = learn([original])
        for changed in (doc(10, {"AAA": sym()}, generated=f"{S[12]}T07:45:00+09:00"),
                        dict(doc(10, {"AAA": sym()}, commit="c9"), buy_session=S[12])):
            with self.subTest(changed=changed["generated_at"]):
                broken = learn([changed], previous=first["decision_days"])
                row = day_row(broken, S[11])
                self.assertEqual((row["flags"], row["eligible"], row["exclude_reason"]),
                                 (["PRESERVATION_BROKEN"], False, "PRESERVATION_BROKEN"))
                self.assertEqual(broken["gate_units"], [])
                again = learn([original], previous=broken["decision_days"])
                self.assertEqual(day_row(again, S[11])["flags"], ["PRESERVATION_BROKEN"])
                self.assertFalse(day_row(again, S[11])["eligible"])
                self.assertEqual(day_row(again, S[11])["first_sha256"], day_row(first, S[11])["sha256"])

    def test_a_missing_day_is_excluded_that_week_only(self) -> None:
        original = doc(10, {"AAA": sym()})
        other = doc(20, {"AAA": sym()})
        first = learn([original, other])
        gone = learn([other], previous=first["decision_days"])
        row = day_row(gone, S[11])
        self.assertEqual((row["eligible"], row["exclude_reason"], row["flags"]), (False, "MISSING_NOW", []))
        self.assertEqual(row["first_sha256"], day_row(first, S[11])["sha256"])
        self.assertEqual([item["event"] for item in row["flag_history"]], ["MISSING_NOW"])
        back = learn([original, other], previous=gone["decision_days"])
        row = day_row(back, S[11])
        self.assertEqual((row["eligible"], row["flags"]), (True, []))
        self.assertEqual([item["event"] for item in row["flag_history"]], ["MISSING_NOW", "RETURNED"])
        rerun = doc(10, {"AAA": sym()}, generated=f"{S[11]}T09:30:00+09:00", commit="c2")
        changed = learn([rerun, other], previous=gone["decision_days"])
        self.assertEqual(day_row(changed, S[11])["flags"], ["PRESERVATION_BROKEN"])

    def test_an_unreadable_folder_changes_no_mark(self) -> None:
        first = learn([doc(10, {"AAA": sym()})])
        rerun = learn([doc(10, {"AAA": sym()}, generated=f"{S[11]}T09:30:00+09:00", commit="c2")],
                      previous=first["decision_days"])
        blind = learn([], previous=rerun["decision_days"], root_status="MISSING")
        self.assertEqual(blind["decision_days"], rerun["decision_days"])
        self.assertIn("DECISIONS_ROOT_UNREADABLE", [item["reason"] for item in blind["errors"]])
        broken_file = {"day": S[11], "sha256": None, "error": "DECISION_UNREADABLE"}
        unread = learn([broken_file], previous=rerun["decision_days"])
        self.assertEqual(unread["decision_days"], rerun["decision_days"])
        self.assertIn("DECISIONS_ROOT_UNREADABLE", [item["reason"] for item in unread["errors"]])

    def test_an_unreadable_file_never_becomes_the_first_hash(self) -> None:
        learning = learn([{"day": S[11], "sha256": "f" * 64, "error": "DECISION_NOT_JSON"}, doc(20, {"AAA": sym()})])
        row = day_row(learning, S[11])
        self.assertEqual((row["first_sha256"], row["exclude_reason"]), (None, "DECISION_NOT_JSON"))
        self.assertTrue(day_row(learning, S[21])["eligible"])


# ---------------------------------------------------------------------------------------------------------------
# c, d. gate names and units
# ---------------------------------------------------------------------------------------------------------------

class GateNameAndUnitTests(unittest.TestCase):
    def test_gate_names(self) -> None:
        etf_row = cells(c1=("no", "막힘 RESEARCH_RECORD_NOT_OK:RECORD_MISSING"),
                        c2=("unk", "현금 확인 필요"))
        learning = learn([doc(10, {"SOXL": sym(row=etf_row), "AAA": sym(), "BBB": sym(row=etf_row)},
                              research="MISSING", candidates=(("AAA", "buy"), ("BBB", "buy")),
                              blocked=(("AAA", "buy", ("REQ5_RREC1:unk",)),
                                       ("BBB", "buy", ("REQ1_EARNINGS:no", "RESEARCH_RECORD_NOT_OK:RECORD_MISSING"))))],
                         closes=flat_closes(SOXL={}))
        self.assertEqual(units_of(learning, "SOXL")[0]["gates"],
                         ["CIRCUIT_NEW_EVIDENCE", "REQ2_EXPOSURE_CASH_PRODUCT_UNK", "RESEARCH_RECORD_NOT_OK"])
        self.assertEqual(units_of(learning, "AAA")[0]["gates"], ["REQ5_RREC1_UNK"])
        self.assertEqual(units_of(learning, "BBB")[0]["gates"], ["RESEARCH_RECORD_NOT_OK"])

    def test_buy_units(self) -> None:
        learning = learn([doc(10, {
            "AAA": sym(),
            "BBB": sym(),
            "CCC": sym(row=cells(c5=("no", "막힘 미충족 RG1"))),
            "DDD": sym(buy_approved=False),
            "EEE": sym(buy=False),
            "ZZZ": sym(sigma=None)},
            candidates=(("BBB", "buy"),), blocked=(("BBB", "buy", ("REQ5_RREC1:no",)),), shock_open=True)])
        self.assertEqual([(unit["gates"], unit["binding"]) for unit in units_of(learning, "AAA")],
                         [(["CIRCUIT_NEW_EVIDENCE"], True)])
        bbb = units_of(learning, "BBB")[0]
        self.assertEqual((bbb["gates"], bbb["binding"], bbb["binding_scope"]),
                         (["REQ5_RREC1"], True, "EVALUATED_GATES_ONLY"))
        self.assertEqual((bbb["shock_open"], bbb["symbol_open"], bbb["rrec1_key"], bbb["rg"]),
                         (True, False, S[10], {"RG1": "no"}))
        self.assertEqual([(unit["gates"], unit["binding"]) for unit in units_of(learning, "CCC")],
                         [(["CIRCUIT_NEW_EVIDENCE", "REQ5_RREC1"], False)])
        self.assertEqual(units_of(learning, "DDD") + units_of(learning, "EEE"), [])
        self.assertIn("G1_SYMBOL_DATA", units_of(learning, "ZZZ")[0]["gates"])
        self.assertEqual(units_of(learning, "AAA")[0]["start_session"], S[11])

    def test_a_ticketed_candidate_has_no_unit(self) -> None:
        ticket = {"ticket_id": "AT-1", "ticker": "AAA", "side": "buy", "mode": "compare", "session": S[11]}
        learning = learn([doc(10, {"AAA": sym()}, candidates=(("AAA", "buy"),), tickets=(ticket,))])
        self.assertEqual(units_of(learning, "AAA"), [])

    def test_sell_units(self) -> None:
        held = {"AAA": sym(role="held", buy=False, sell=True), "BBB": sym(role="held", buy=False),
                "CCC": sym(role="held", buy=False, sell=True), "DDD": sym(role="held", buy=False),
                "EEE": sym(role="held", buy=False)}
        trims = (("CCC", "sell", ("CARD_TRIM_SIZE_MISSING",)), ("DDD", "sell", ("CARD_TRIM_SIZE_MISSING",)))
        learning = learn([doc(10, held, blocked=trims)], s7={S[11]: {"status": "OK", "reduce": ["BBB"]}})
        gates = {symbol: [unit["gates"] for unit in units_of(learning, symbol, "sell")] for symbol in held}
        self.assertEqual(gates, {"AAA": [["CIRCUIT_SELL_NO_GAP"]], "BBB": [["CIRCUIT_SELL_NO_EVIDENCE"]],
                                 "CCC": [["CARD_TRIM_SIZE_MISSING"]],
                                 "DDD": [["CARD_TRIM_SIZE_MISSING", "CIRCUIT_SELL_NO_EVIDENCE"]], "EEE": []})

    def test_an_unreadable_s7_file_only_affects_the_no_evidence_judgment(self) -> None:
        held = {"AAA": sym(role="held", buy=False, sell=True), "BBB": sym(role="held", buy=False)}
        learning = learn([doc(10, held)], s7={S[11]: {"status": "S7_REVIEW_UNREADABLE", "reduce": []}})
        aaa = units_of(learning, "AAA", "sell")[0]
        self.assertEqual((aaa["gates"], aaa.get("status")), (["CIRCUIT_SELL_NO_GAP"], None))
        bbb = units_of(learning, "BBB", "sell")[0]
        self.assertEqual((bbb["status"], bbb["reason"]), ("NOT_SCORABLE", "S7_REVIEW_UNREADABLE"))
        self.assertEqual(episodes_of(learning, "BBB", "sell"), [])
        self.assertEqual(len(episodes_of(learning, "AAA", "sell")), 1)

    def test_s7_paths(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="score_learning_s7_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = tmp / "auto-core"
        review = root / S[11] / "s7" / "review.json"
        review.parent.mkdir(parents=True)
        review.write_text(json.dumps({"recommendations": {"reduce": [{"symbol": "BBB"}, {"symbol": "AAA"}]}}),
                          encoding="utf-8")
        (tmp / "outside.json").write_text(json.dumps({"recommendations": {"reduce": []}}), encoding="utf-8")
        inside = scorer.load_s7_reduce(doc(10), root)
        self.assertEqual(inside, {"status": "OK", "reduce": ["AAA", "BBB"]})
        backslash = doc(10)
        backslash["inputs"]["s7_review"]["path"] = f"workspace\\outputs\\auto-core\\{S[11]}\\s7\\review.json"
        self.assertEqual(scorer.load_s7_reduce(backslash, root)["status"], "OK")
        outside = doc(10)
        outside["inputs"]["s7_review"]["path"] = "../outside.json"
        self.assertEqual(scorer.load_s7_reduce(outside, root)["status"], "S7_PATH_OUTSIDE")
        absolute = doc(10)
        absolute["inputs"]["s7_review"]["path"] = str(tmp / "outside.json")
        self.assertEqual(scorer.load_s7_reduce(absolute, root)["status"], "S7_PATH_OUTSIDE")
        missing = doc(11)
        self.assertEqual(scorer.load_s7_reduce(missing, root)["status"], "S7_REVIEW_UNREADABLE")
        self.assertEqual(scorer.load_s7_reduce({"inputs": {}}, root)["status"], "S7_REVIEW_UNREADABLE")


# ---------------------------------------------------------------------------------------------------------------
# e. shock periods and episodes
# ---------------------------------------------------------------------------------------------------------------

class ShockAndEpisodeTests(unittest.TestCase):
    def test_shock_periods_follow_open_not_the_event_date(self) -> None:
        rrec = {"AAA": sym()}
        blocked = (("AAA", "buy", ("REQ5_RREC1:no",)),)
        days = [doc(10, rrec, shock_open=True, event_date=S[5], candidates=(("AAA", "buy"),), blocked=blocked),
                doc(11, rrec, shock_open=True, event_date=S[6], candidates=(("AAA", "buy"),), blocked=blocked),
                doc(12, rrec, shock_open=True, event_date=S[12], candidates=(("AAA", "buy"),), blocked=blocked),
                doc(13, rrec, shock_open=None, candidates=(("AAA", "buy"),), blocked=blocked),
                doc(14, rrec, shock_open=True, event_date=S[12], candidates=(("AAA", "buy"),), blocked=blocked),
                doc(15, {"ZZZ": sym(buy=False)}, shock_open=False),
                doc(16, rrec, shock_open=True, event_date=S[16], candidates=(("AAA", "buy"),), blocked=blocked)]
        learning = learn(days)
        periods = learning["shock_periods"]
        self.assertEqual([(period["period_id"], period["days"]) for period in periods],
                         [(S[10], [S[11], S[12], S[13], S[15]]), (S[16], [S[17]])])
        self.assertEqual(periods[0]["event_dates"], [S[5], S[6], S[12]])
        self.assertEqual(periods[0]["c0s"], [100.0])
        keys = [unit["rrec1_key"] for unit in units_of(learning, "AAA")]
        self.assertEqual(keys, [S[10], S[10], S[10], "UNKNOWN", S[10], S[16]])
        episodes = episodes_of(learning, "AAA")
        self.assertEqual([(episode["rrec1_key"], episode["days"]) for episode in episodes],
                         [(S[10], 3), ("UNKNOWN", 1), (S[10], 1), (S[16], 1)])

    def test_symbol_only_and_none_keys(self) -> None:
        blocked = (("AAA", "buy", ("REQ5_RREC1:no",)), ("BBB", "buy", ("REQ5_RREC1:no",)))
        learning = learn([doc(10, {"AAA": sym(shock_open=True), "BBB": sym()}, shock_open=False,
                              candidates=(("AAA", "buy"), ("BBB", "buy")), blocked=blocked)])
        self.assertEqual(units_of(learning, "AAA")[0]["rrec1_key"], "SYMBOL_ONLY")
        self.assertEqual(units_of(learning, "BBB")[0]["rrec1_key"], "NONE")
        self.assertEqual(learning["shock_periods"], [])

    def test_runs_and_unit_spacing(self) -> None:
        on, off = {"AAA": sym()}, {"AAA": sym(buy=False)}
        learning = learn([doc(10, on), doc(11, on, status="FAIL"), doc(12, on), doc(13, off), doc(14, on),
                          doc(20, off), doc(40, on)])
        episodes = episodes_of(learning, "AAA")
        self.assertEqual([(episode["first_day"], episode["last_day"], episode["days"], episode["unit"])
                          for episode in episodes],
                         [(S[11], S[13], 2, True), (S[15], S[15], 1, False), (S[41], S[41], 1, True)])


# ---------------------------------------------------------------------------------------------------------------
# f. values
# ---------------------------------------------------------------------------------------------------------------

class ValueTests(unittest.TestCase):
    CLOSES = flat_closes(AAA={S[16]: "110", S[31]: "90"}, BBB={S[16]: "110", S[31]: "90"})

    def test_buy_is_r_sell_is_minus_r_and_the_path_keeps_its_sign(self) -> None:
        learning = learn([doc(10, {"AAA": sym(), "BBB": sym(role="held", buy=False, sell=True)})],
                         closes=self.CLOSES)
        buy = episodes_of(learning, "AAA")[0]
        sell = episodes_of(learning, "BBB", "sell")[0]
        self.assertEqual((horizon(buy["horizons"], 5)["cf_value"], horizon(buy["horizons"], 20)["cf_value"]),
                         ("0.100000", "-0.100000"))
        self.assertEqual((horizon(sell["horizons"], 5)["cf_value"], horizon(sell["horizons"], 20)["cf_value"]),
                         ("-0.100000", "0.100000"))
        for episode in (buy, sell):
            self.assertEqual((episode["path_20"]["status"], episode["path_20"]["min"], episode["path_20"]["max"]),
                             ("SCORED", "-0.100000", "0.100000"))

    def test_pending_missing_and_outside_the_calendar(self) -> None:
        learning = learn([doc(10, {"AAA": sym()})], closes=self.CLOSES, as_of=after(S[25]))
        episode = episodes_of(learning, "AAA")[0]
        self.assertEqual([item["status"] for item in episode["horizons"]], ["SCORED", "PENDING", "PENDING"])
        self.assertEqual(episode["path_20"]["status"], "PENDING")
        gap = flat_closes(AAA={S[16]: ""})
        missing = episodes_of(learn([doc(10, {"AAA": sym()})], closes=gap), "AAA")[0]
        self.assertEqual(horizon(missing["horizons"], 5)["reason"], "TARGET_CLOSE_MISSING")
        self.assertEqual(missing["path_20"]["reason"], "PATH_CLOSE_MISSING")
        outside = doc(10, {"AAA": sym()})
        outside.update(run_day_kst="2025-12-31", buy_session="2025-12-31", evaluation_session="2025-12-30")
        early = episodes_of(learn([outside]), "AAA")[0]
        self.assertEqual({item["reason"] for item in early["horizons"]}, {"START_SESSION_NOT_IN_CALENDAR"})
        self.assertEqual(early["path_20"]["reason"], "START_SESSION_NOT_IN_CALENDAR")
        late = doc(185, {"AAA": sym()})
        tail = episodes_of(learn([late]), "AAA")[0]
        self.assertEqual(horizon(tail["horizons"], 60)["reason"], "CALENDAR_DOES_NOT_COVER_HORIZON")
        nothing = episodes_of(learn([doc(10, {"AAA": sym()})], calendar=None), "AAA")[0]
        self.assertEqual({item["reason"] for item in nothing["horizons"]}, {"SESSION_CALENDAR_UNAVAILABLE"})


# ---------------------------------------------------------------------------------------------------------------
# g. R-REC1 bundles
# ---------------------------------------------------------------------------------------------------------------

def shock_days(plan: dict[int, list[tuple[str, str]]], first: int = 10, last: int = 45) -> list[dict]:
    """Open-shock days S[first..last]; plan[i] = [(symbol, blocked reason)] for that day only."""
    days = []
    for index in range(first, last + 1):
        entries = plan.get(index, [])
        specs = {"ZZZ": sym(buy=False)} | {symbol: sym() for symbol, _reason in entries}
        days.append(doc(index, specs, shock_open=True, event_date=S[5],
                        candidates=tuple((symbol, "buy") for symbol, _reason in entries),
                        blocked=tuple((symbol, "buy", (reason,)) for symbol, reason in entries)))
    return days


class RrecBundleTests(unittest.TestCase):
    PLAN = {10: [("AAA", "REQ5_RREC1:no")], 15: [("BBB", "REQ5_RREC1:no")], 20: [("DDD", "REQ5_RREC1:unk")],
            35: [("CCC", "REQ5_RREC1:no")]}
    CLOSES = flat_closes(AAA={S[31]: "110"}, BBB={S[36]: "130"})

    def test_bundles_inside_one_period(self) -> None:
        learning = learn(shock_days(self.PLAN), closes=self.CLOSES)
        self.assertEqual(len(learning["shock_periods"]), 1)
        bundles = learning["rrec1_units"]
        self.assertEqual([(bundle["unit_id"], bundle["symbols"], bundle["n_episodes"]) for bundle in bundles],
                         [(f"{S[10]}#1", ["AAA", "BBB"], 2), (f"{S[10]}#2", ["CCC"], 1)])
        self.assertEqual(horizon(bundles[0]["horizons"], 20)["cf_value"], "0.200000")  # (0.1 + 0.3) / 2
        self.assertEqual(bundles[0]["start_session"], S[11])
        self.assertEqual([bundle["symbols"] for bundle in learning["rrec1_unk_units"]], [["DDD"]])

    def test_a_new_epoch_opens_a_new_bundle(self) -> None:
        epochs = epochs_doc(("ALL", "2026-01-01"), ("GATE:REQ5_RREC1", S[16]))
        learning = learn(shock_days(self.PLAN), closes=self.CLOSES, epochs=epochs)
        self.assertEqual([(bundle["symbols"], bundle["epoch"]) for bundle in learning["rrec1_units"]],
                         [(["AAA"], 1), (["BBB"], 2), (["CCC"], 2)])

    def test_a_pending_member_keeps_the_bundle_pending(self) -> None:
        learning = learn(shock_days(self.PLAN), closes=self.CLOSES, as_of=after(S[33]))
        self.assertEqual(horizon(learning["rrec1_units"][0]["horizons"], 20)["status"], "PENDING")


# ---------------------------------------------------------------------------------------------------------------
# h, i, j. ticket-based units
# ---------------------------------------------------------------------------------------------------------------

def source(ticket_id: str, ticker: str, side: str, session: str, *, key: str, would_fill: bool | None,
           mode: str = "compare", user_state: str = "NOT_ENTERED_COMPARE_MODE", folder_day: str | None = None) -> dict:
    return {"ticket_id": ticket_id, "ticker": ticker, "side": side, "mode": mode, "session": session,
            "decision_key": key, "would_fill": would_fill, "user_state": user_state, "folder_day": folder_day}


class SellFloorTests(unittest.TestCase):
    def test_floor_rows_reissues_and_the_next_fill(self) -> None:
        closes = flat_closes(AAA={S[51]: "98", S[52]: "95", S[55]: "105", S[70]: "80"})
        tickets = [source("AT-20260512-AAA-1", "AAA", "sell", S[50], key="K1", would_fill=False),
                   source("AT-20260513-AAA-1", "AAA", "sell", S[51], key="K1", would_fill=False),
                   source("AT-20260514-AAA-1", "AAA", "sell", S[52], key="K2", would_fill=True),
                   source("T-USER", "BBB", "sell", S[50], key="K3", would_fill=True, mode="apply",
                          user_state="unfilled"),
                   source("T-BUY", "CCC", "buy", S[50], key="K4", would_fill=False)]
        learning = learn([], tickets=tickets, closes=closes)
        rows = {row["ticket_id"]: row for row in learning["sell_floor"]}
        self.assertEqual(set(rows), {"AT-20260512-AAA-1", "AT-20260513-AAA-1", "T-USER"})
        first = rows["AT-20260512-AAA-1"]
        self.assertEqual([item["cf_value"] for item in first["horizons"]], ["0.020000", "-0.050000", "0.200000"])
        self.assertEqual(first["next_fill"], {"status": "FILLED_LATER", "session": S[52], "sessions_after": 2,
                                              "delay_value": "0.050000"})
        self.assertEqual((first["unit"], rows["AT-20260513-AAA-1"]["unit"], rows["T-USER"]["unit"]),
                         (True, False, True))
        self.assertEqual(rows["T-USER"]["next_fill"]["status"], "NO_LATER_FILL_WITHIN_5")
        self.assertEqual(first["first_day"], "2026-05-12")
        pending = learn([], tickets=tickets, closes=closes, as_of=after(S[53]))
        self.assertEqual({row["ticket_id"]: row["next_fill"]["status"] for row in pending["sell_floor"]}["T-USER"],
                         "PENDING")

    def test_the_same_ticker_needs_five_sessions(self) -> None:
        tickets = [source("A1", "AAA", "sell", S[50], key="K1", would_fill=False),
                   source("A2", "AAA", "sell", S[53], key="K2", would_fill=False),
                   source("A3", "AAA", "sell", S[55], key="K3", would_fill=False)]
        rows = learn([], tickets=tickets)["sell_floor"]
        self.assertEqual([row["unit"] for row in rows], [True, False, True])


def wave(count: int, *, amplitude: float = 0.03) -> list[str]:
    return [format(100 * (1 + amplitude * math.sin(index * 0.7)) + index * 0.05, ".4f") for index in range(count)]


class ScenarioBandTests(unittest.TestCase):
    def test_the_band_formula_equals_the_core_scenarios(self) -> None:
        import auto_core_tickets  # test-only import: the scorer never imports the core at run time

        for count in (65, 70, 90):
            closes = [float(value) for value in wave(count)]
            mine = scorer.scenario_band(closes)
            core = auto_core_tickets.scenarios(closes)
            self.assertEqual((mine["status"], core["status"]), ("ok", "ok"))
            self.assertAlmostEqual(mine["up"], core["up"], places=9)
            self.assertAlmostEqual(mine["down"], core["down"], places=9)
        self.assertEqual(scorer.scenario_band([100.0] * 64)["reason"], "SCENARIO_HISTORY_SHORT")
        self.assertEqual(auto_core_tickets.scenarios([100.0] * 64)["reason"], "SCENARIO_HISTORY_SHORT")

    def test_the_contiguous_run_equals_the_core_series_builder(self) -> None:
        import auto_core_rules  # test-only import
        import auto_core_tickets  # test-only import

        values = wave(121)
        for gap, through in ((30, 100), (60, 100), (99, 100)):
            with self.subTest(gap=gap):
                per_symbol = {S[index]: values[index] for index in range(121) if index != gap}
                bars = {"sessions": {day: {"close": float(value), "high": float(value), "low": float(value),
                                           "volume": 1.0} for day, value in per_symbol.items()}}
                series = auto_core_rules.build_series(bars, S, S[through])
                core = auto_core_tickets.scenarios(series["close"]) if series else {"status": "unk"}
                mine = scorer.scenario_band(scorer.band_closes(per_symbol, S, S[through]))
                self.assertEqual(mine["status"] == "ok", core["status"] == "ok")
                if core["status"] == "ok":
                    self.assertAlmostEqual(mine["up"], core["up"], places=9)
                    self.assertAlmostEqual(mine["down"], core["down"], places=9)
        self.assertEqual(scorer.band_closes({S[0]: "100"}, S, S[1]), [])

    def test_verdicts_and_paths(self) -> None:
        base = wave(200, amplitude=0.01)
        closes = {symbol: {S[index]: base[index] for index in range(200)} for symbol in ("AAA", "BBB", "CCC", "DDD")}
        start = float(base[100])
        closes["AAA"][S[105]] = format(start * 1.5, ".4f")
        closes["BBB"][S[105]] = format(start * 1.5, ".4f")
        closes["CCC"][S[105]] = format(start * 0.5, ".4f")
        closes["DDD"][S[105]] = base[100]
        tickets = [source("AT-20260720-AAA-1", "AAA", "buy", S[100], key="K1", would_fill=True),
                   source("AT-20260720-BBB-1", "BBB", "sell", S[100], key="K2", would_fill=True),
                   source("AT-20260720-CCC-1", "CCC", "buy", S[100], key="K3", would_fill=True),
                   source("AT-20260720-DDD-1", "DDD", "buy", S[100], key="K4", would_fill=True),
                   source("AT-20260721-DDD-1", "DDD", "buy", S[101], key="K4", would_fill=True),
                   source("SHORT-1", "AAA", "buy", S[30], key="K5", would_fill=True)]
        rows = {row["ticket_id"]: row for row in learn([], tickets=tickets, closes=closes)["scenario_band"]}
        self.assertEqual((rows["AT-20260720-AAA-1"]["verdict"], rows["AT-20260720-AAA-1"]["path"]),
                         ("UP_TAIL", "PRECELEBRATION"))
        self.assertEqual((rows["AT-20260720-BBB-1"]["verdict"], rows["AT-20260720-BBB-1"]["path"]),
                         ("UP_TAIL", "PREMORTEM"))
        self.assertEqual((rows["AT-20260720-CCC-1"]["verdict"], rows["AT-20260720-CCC-1"]["path"]),
                         ("DOWN_TAIL", "PREMORTEM"))
        self.assertEqual((rows["AT-20260720-DDD-1"]["verdict"], rows["AT-20260720-DDD-1"]["path"]), ("INSIDE", None))
        self.assertFalse(rows["AT-20260721-DDD-1"]["unit"])  # the same decision key issued again
        self.assertEqual((rows["SHORT-1"]["verdict"], rows["SHORT-1"]["reason"]),
                         ("NOT_SCORABLE", "SCENARIO_HISTORY_SHORT"))
        band = rows["AT-20260720-AAA-1"]["band"]
        expected = scorer.scenario_band(scorer.band_closes(closes["AAA"], S, S[99]))
        self.assertEqual((band["up"], band["down"]), (format(expected["up"], ".9f"), format(expected["down"], ".9f")))
        pending = learn([], tickets=tickets, closes=closes, as_of=after(S[102]))["scenario_band"]
        self.assertEqual({row["ticket_id"]: row["verdict"] for row in pending}["AT-20260720-AAA-1"], "PENDING")


def result_row(ticket_id: str, ticker: str, side: str, session: str, kinds: list | None, *,
               mode: str = "compare") -> dict:
    return {"ticket_id": ticket_id, "ticker": ticker, "side": side, "mode": mode, "session": session,
            "would_fill": True, "user": {"state": "NOT_ENTERED_COMPARE_MODE"}, "evidence_weak_kinds": kinds,
            "horizons": []}


class TriggerKindTests(unittest.TestCase):
    def test_kinds_first_ticket_per_key_and_spacing(self) -> None:
        closes = flat_closes(AAA={S[70]: "110"})
        results = [result_row("T1", "AAA", "buy", S[50], None), result_row("T2", "BBB", "sell", S[50], []),
                   result_row("T3", "AAA", "buy", S[51], ["C1", "C2"]), result_row("T4", "AAA", "buy", S[52], ["C1"]),
                   result_row("T5", "AAA", "buy", S[60], ["C1"])]
        tickets = [source("T1", "AAA", "buy", S[50], key="K1", would_fill=True),
                   source("T2", "BBB", "sell", S[50], key="K2", would_fill=True),
                   source("T3", "AAA", "buy", S[51], key="K3", would_fill=True),
                   source("T4", "AAA", "buy", S[52], key="K3", would_fill=True),
                   source("T5", "AAA", "buy", S[60], key="K5", would_fill=True)]
        rows = learn([], tickets=tickets, ticket_results=results, closes=closes)["trigger_kinds"]
        self.assertEqual([(row["ticket_id"], row["kind"], row["overlap"], row["unit"]) for row in rows],
                         [("T1", "WEAK_KINDS_NOT_RECORDED", 1, True), ("T2", "NO_WEAK_KIND", 1, True),
                          ("T3", "C1", 2, True), ("T3", "C2", 2, True), ("T5", "C1", 1, False)])
        self.assertEqual(horizon(rows[0]["horizons"], 20)["cf_value"], "0.100000")

    def test_compare_evidence_weak_reaches_the_kinds(self) -> None:
        record = {"ticket_id": "AT-20260512-AAA-1", "mode": "compare", "ticker": "AAA", "side": "buy",
                  "price": 101.0, "qty": 1, "session": S[50], "decision_key": "k1", "evidence": {"weak": ["C6"]}}
        report = scorer.score_journal({"status": "OK", "entries": [], "errors": [], "head_sha256": "0" * 64},
                                      calendar=CALENDAR, closes=flat_closes(), unverified={}, benchmark=NO_SPY,
                                      corporate_actions=NO_ACTIONS, evaluation_as_of=after(S[-1]),
                                      ticket_records=[record])
        tickets = scorer._learning_tickets([], [record], [], report["ticket_results"])
        self.assertEqual(tickets[0]["decision_key"], "k1")
        rows = learn([], tickets=tickets, ticket_results=report["ticket_results"])["trigger_kinds"]
        self.assertEqual([row["kind"] for row in rows], ["C6"])


# ---------------------------------------------------------------------------------------------------------------
# k. epochs
# ---------------------------------------------------------------------------------------------------------------

class EpochTests(unittest.TestCase):
    EPOCHS = epochs_doc(("ALL", "2026-01-01"), ("GATE:REQ5_RREC1", S[20]), ("EVIDENCE_BUY", S[40]),
                        ("GATE:SELL_FLOOR", S[40]))

    def test_unit_epochs_by_scope(self) -> None:
        blocked = (("BBB", "buy", ("REQ5_RREC1:unk",)),)
        specs = {"AAA": sym(), "BBB": sym()}
        breaker = {"ZZZ": sym(buy=False)}
        learning = learn([doc(10, specs, candidates=(("BBB", "buy"),), blocked=blocked), doc(20, breaker),
                          doc(30, specs, candidates=(("BBB", "buy"),), blocked=blocked), doc(40, breaker),
                          doc(50, specs, candidates=(("BBB", "buy"),), blocked=blocked)], epochs=self.EPOCHS)
        self.assertEqual([unit["epoch"] for unit in units_of(learning, "AAA")], [1, 1, 2])
        self.assertEqual([unit["epoch"] for unit in units_of(learning, "BBB")], [1, 2, 3])  # GATE:X counts X_UNK
        self.assertEqual([episode["epoch"] for episode in episodes_of(learning, "BBB")], [1, 2, 3])

    def test_ticket_units_use_the_ticket_day(self) -> None:
        tickets = [source(f"AT-{S[39].replace('-', '')}-AAA-1", "AAA", "sell", S[39], key="K1", would_fill=False,
                          folder_day=S[45]),
                   source("NO-DAY", "AAA", "sell", S[45], key="K2", would_fill=False, folder_day=S[41]),
                   source("NONE", "BBB", "sell", S[45], key="K3", would_fill=False)]
        rows = {row["ticket_id"]: row for row in learn([], tickets=tickets, epochs=self.EPOCHS)["sell_floor"]}
        self.assertEqual(rows[f"AT-{S[39].replace('-', '')}-AAA-1"]["first_day"], S[39])
        self.assertEqual(rows[f"AT-{S[39].replace('-', '')}-AAA-1"]["epoch"], 1)
        self.assertEqual((rows["NO-DAY"]["first_day"], rows["NO-DAY"]["epoch"]), (S[41], 2))
        self.assertEqual((rows["NONE"]["first_day"], rows["NONE"]["epoch"]), (None, None))

    def test_a_new_epoch_without_units_leaves_only_earlier_epoch_buckets(self) -> None:
        epochs = epochs_doc(("ALL", "2026-01-01"), ("EVIDENCE_BUY", S[150]))
        learning = learn([doc(10, {"AAA": sym()})], epochs=epochs, as_of=after(S[160]))
        bucket = next(item for item in learning["buckets"] if item["family"] == "GATE")
        self.assertEqual((bucket["key"], bucket["current_epoch"], bucket["finding"], bucket["conclusion_allowed"]),
                         (["buy", "CIRCUIT_NEW_EVIDENCE", 1], 2, "EARLIER_EPOCH", False))

    def test_missing_or_broken_epochs_fail_closed(self) -> None:
        for epochs in (MISSING, {"status": "INVALID", "document": None, "errors": ["NOT_JSON"]},
                       epochs_doc(("ALL", "2026-01-01"), ("GATE:", "2026-02-01")),
                       epochs_doc(("ALL", "not-a-day"))):
            with self.subTest(epochs=epochs.get("status")):
                learning = learn([doc(10, {"AAA": sym()})], epochs=epochs)
                self.assertEqual(units_of(learning, "AAA")[0]["epoch"], None)
                self.assertIn(learning["epochs"]["status"], ("MISSING", "INVALID"))
                self.assertEqual({bucket["finding"] for bucket in learning["buckets"]}, {"EPOCHS_UNAVAILABLE"})

    def test_epochs_file_loader(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="score_learning_epochs_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        good = tmp / "good.json"
        good.write_text(json.dumps({"schema": scorer.EPOCHS_SCHEMA, "description": "x", "order_authority": False,
                                    "epochs": [{"scope": "ALL", "first_run_day": "2026-01-01"}]}), encoding="utf-8")
        self.assertEqual(scorer.load_learning_document(good, scorer.EPOCHS_SCHEMA, "epochs")["status"], "OK")
        self.assertEqual(scorer.load_learning_document(tmp / "absent.json", scorer.EPOCHS_SCHEMA, "epochs")["status"],
                         "MISSING")
        wrong = tmp / "wrong.json"
        wrong.write_text(json.dumps({"schema": "other", "epochs": []}), encoding="utf-8")
        self.assertEqual(scorer.load_learning_document(wrong, scorer.EPOCHS_SCHEMA, "epochs")["status"], "INVALID")
        repo_epochs = scorer.REPO_ROOT / "docs/claude/gate-rule-epochs.json"
        if repo_epochs.is_file():  # the committed file must parse under the same rules (read only)
            loaded = scorer.load_learning_document(repo_epochs, scorer.EPOCHS_SCHEMA, "epochs")
            self.assertEqual(scorer._epoch_context(loaded)["status"], "OK")


# ---------------------------------------------------------------------------------------------------------------
# l. buckets and findings
# ---------------------------------------------------------------------------------------------------------------

EPOCH_CONTEXT = {"status": "OK", "entries": [{"scope": "ALL", "first_run_day": "2026-01-01"}]}


def item(index: int, value: str | None, *, family: str = "GATE", status: str = "SCORED", reason: str | None = None,
         session: str | None = None, symbol: str = "AAA", verdict: str | None = None) -> dict:
    primary = {"horizon_sessions": 20, "status": status}
    if value is not None:
        primary["cf_value"] = value
    if reason is not None:
        primary["reason"] = reason
    return {"family": family, "key": ["buy", "G", 1], "side": "buy", "gates": ["G"], "extra": None, "epoch": 1,
            "start_session": session or S[index], "symbol": symbol, "unit_id": f"u{index:03d}", "commit": "c1",
            "display": None, "primary": primary, "path_min": "-0.050000", "verdict": verdict}


def bucket_of(items: list[dict], family: str = "GATE") -> dict:
    return scorer._bucket(family, items, EPOCH_CONTEXT, "2026-12-01")


class BucketTests(unittest.TestCase):
    def test_sample_and_coverage(self) -> None:
        self.assertEqual(bucket_of([item(i, "0.01") for i in range(29)])["finding"], "INSUFFICIENT_SAMPLE")
        over = [item(i, "0.01") for i in range(30)] + [item(30 + i, None, status="NOT_SCORABLE",
                                                            reason="START_SESSION_NOT_IN_CALENDAR") for i in range(4)]
        bucket = bucket_of(over)
        self.assertEqual((bucket["finding"], bucket["coverage_ok"], bucket["n_unscorable"]["total"]),
                         ("INSUFFICIENT_COVERAGE", False, 4))
        within = [item(i, "0.01") for i in range(30)]
        within += [item(30 + i, None, status="NOT_SCORABLE", reason="TARGET_CLOSE_MISSING") for i in range(3)]
        within += [item(40 + i, None, status="NOT_SCORABLE", reason="CALENDAR_DOES_NOT_COVER_HORIZON")
                   for i in range(10)]
        within += [item(60 + i, None, status="PENDING") for i in range(5)]
        bucket = bucket_of(within)
        self.assertEqual((bucket["finding"], bucket["coverage_ok"], bucket["n_calendar_out"], bucket["n_pending"],
                          bucket["n_units"], bucket["conclusion_allowed"]), ("COST", True, 10, 5, 48, True))
        only_out = bucket_of([item(i, None, status="NOT_SCORABLE", reason="CALENDAR_DOES_NOT_COVER_HORIZON")
                              for i in range(5)])
        self.assertFalse(only_out["coverage_ok"])

    def test_sign_findings(self) -> None:
        self.assertEqual(bucket_of([item(i, "0.02") for i in range(30)])["finding"], "COST")
        self.assertEqual(bucket_of([item(i, "-0.02") for i in range(30)])["finding"], "PROTECT")
        mixed = [item(i, "-0.01") for i in range(15)] + [item(15 + i, "0.05") for i in range(15)]
        bucket = bucket_of(mixed)
        self.assertEqual((bucket["finding"], bucket["mean"], bucket["first_half_mean"], bucket["second_half_mean"]),
                         ("MIXED", "0.020000", "-0.010000", "0.050000"))
        self.assertEqual(bucket_of([item(i, "0.02", family="TRIGGER_KIND") for i in range(30)], "TRIGGER_KIND")[
            "finding"], "STRONG")
        self.assertEqual(bucket_of([item(i, "-0.02", family="TRIGGER_KIND") for i in range(30)], "TRIGGER_KIND")[
            "finding"], "WEAK")

    def test_band_tail_share_boundary(self) -> None:
        def band(first_down: int, second_down: int) -> dict:
            rows = []
            for half, downs in ((0, first_down), (1, second_down)):
                for index in range(15):
                    verdict = "DOWN_TAIL" if index < downs else "INSIDE"
                    rows.append(item(half * 15 + index, "0.0", family="SCENARIO_BAND", verdict=verdict))
            return bucket_of(rows, "SCENARIO_BAND")

        self.assertEqual(band(3, 3)["finding"], "DOWN_TAIL_UNDERSTATED")  # 3 / 15 = 20%
        self.assertEqual(band(3, 2)["finding"], "MIXED")
        self.assertEqual(band(3, 3)["tail_ratios"]["first_half"], {"up": "0.000000", "down": "0.200000"})

    def test_halves_sort_by_start_symbol_and_unit_and_odd_counts(self) -> None:
        rows = [item(i, "0.01" if i < 15 else "0.03") for i in range(31)]
        bucket = bucket_of(list(reversed(rows)))
        self.assertEqual((bucket["first_half_mean"], bucket["n_scored"]), ("0.010000", 31))  # floor(31/2) = 15 first
        tied = [item(0, "0.09", session=S[5], symbol="BBB"), item(1, "0.01", session=S[5], symbol="AAA")]
        self.assertEqual(bucket_of(tied)["first_half_mean"], "0.010000")
        same = [item(2, "0.05", session=S[5], symbol="AAA"), item(1, "0.07", session=S[5], symbol="AAA")]
        self.assertEqual(bucket_of(same)["first_half_mean"], "0.070000")  # unit id u001 before u002

    def test_display_only_rrec1_gate_buckets(self) -> None:
        plan = {10: [("AAA", "REQ5_RREC1:no")]}
        learning = learn(shock_days(plan))
        gate = next(bucket for bucket in learning["buckets"] if bucket["family"] == "GATE")
        self.assertEqual((gate["key"][1], gate["finding"], gate["conclusion_allowed"]),
                         ("REQ5_RREC1", "SEE_RREC1_UNITS", False))
        self.assertTrue(any(bucket["family"] == "GATE_RREC1_UNIT" for bucket in learning["buckets"]))
        symbol_only = learn([doc(10, {"AAA": sym(shock_open=True)}, shock_open=False, candidates=(("AAA", "buy"),),
                                 blocked=(("AAA", "buy", ("REQ5_RREC1:no",)),))])
        gate = next(bucket for bucket in symbol_only["buckets"] if bucket["family"] == "GATE")
        self.assertEqual((gate["key"][1], gate["finding"]), ("REQ5_RREC1@SYMBOL_ONLY", "DISPLAY_ONLY"))
        overlap = learn([doc(10, {"AAA": sym(row=cells(c5=("no", "x")))})])["overlap_summary"]
        self.assertEqual([(row["gates"], row["n"]) for row in overlap], [(["CIRCUIT_NEW_EVIDENCE", "REQ5_RREC1"], 1)])


# ---------------------------------------------------------------------------------------------------------------
# m. failure museum
# ---------------------------------------------------------------------------------------------------------------

def museum_entry(candidate_id: str, **overrides: object) -> dict:
    entry = {"candidate_id": candidate_id, "failed_assumption": "the thesis held", "category": "TIMING",
             "evidence": ["docs/claude/x.md:1"], "written_by": "Cowork test", "written_at": "2026-11-01T09:00+09:00"}
    entry.update(overrides)
    return entry


class MuseumTests(unittest.TestCase):
    RESULTS = [{"decision_id": "D1", "kind": "ANALYSIS", "horizons": [
                   {"horizon_sessions": 20, "status": "SCORED", "vs_cash": "-0.050000"}]},
               {"decision_id": "D2", "kind": "USER", "horizons": [
                   {"horizon_sessions": 20, "status": "SCORED", "vs_cash": "0.030000"}]},
               {"decision_id": "D3", "kind": "ANALYSIS", "horizons": [{"horizon_sessions": 20, "status": "PENDING"}]}]
    TICKETS = [{"ticket_id": "T1", "mode": "apply", "would_fill": True, "horizons": [],
                "user": {"state": "filled", "horizons": [
                    {"horizon_sessions": 20, "status": "SCORED", "vs_no_action": "-0.020000"}]}},
               {"ticket_id": "T2", "mode": "compare", "would_fill": True, "user": {"state": "NOT_ENTERED_COMPARE_MODE"},
                "horizons": [{"horizon_sessions": 20, "status": "SCORED", "vs_no_action": "-0.010000"}]},
               {"ticket_id": "T3", "mode": "compare", "would_fill": False, "user": {"state": "NOT_ENTERED_COMPARE_MODE"},
                "horizons": [{"horizon_sessions": 20, "status": "SCORED", "vs_no_action": "0.000000"}]}]
    IDS = ["RESULT:D1:ANALYSIS:h20", "TICKET:T1:USER:h20", "TICKET:T2:HYPOTHETICAL:h20"]

    def test_candidates_control_and_missing_or_broken_files(self) -> None:
        missing = scorer._museum(self.RESULTS, self.TICKETS, MISSING)
        self.assertEqual([item["candidate_id"] for item in missing["candidates"]], self.IDS)
        self.assertEqual(missing["control"], ["RESULT:D2:USER:h20"])
        self.assertEqual((missing["status"], missing["pending"], missing["filled"]), ("MISSING", self.IDS, 0))
        tmp = Path(tempfile.mkdtemp(prefix="score_learning_museum_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        broken = tmp / "museum.json"
        broken.write_text("{broken", encoding="utf-8")
        loaded = scorer.load_learning_document(broken, scorer.MUSEUM_SCHEMA, "entries")
        invalid = scorer._museum(self.RESULTS, self.TICKETS, loaded)
        self.assertEqual((invalid["status"], invalid["pending"]), ("INVALID", self.IDS))

    def test_entries_fill_candidates_bad_entries_are_errors_and_later_wins(self) -> None:
        document = {"schema": scorer.MUSEUM_SCHEMA, "categories": [], "entries": [
            museum_entry("RESULT:D1:ANALYSIS:h20"),
            museum_entry("TICKET:T1:USER:h20", evidence=[]),
            museum_entry("TICKET:T2:HYPOTHETICAL:h20", category="LUCK"),
            museum_entry("RESULT:D1:ANALYSIS:h20", category="THESIS", grade="C")]}
        loaded = {"status": "OK", "document": document, "errors": []}
        museum = scorer._museum(self.RESULTS, self.TICKETS, loaded)
        self.assertEqual((museum["filled"], museum["pending"]),
                         (1, ["TICKET:T1:USER:h20", "TICKET:T2:HYPOTHETICAL:h20"]))
        self.assertEqual([error["index"] for error in museum["errors"]], [1, 2])
        self.assertEqual(museum["errors"][0]["reasons"], ["FIELD_MISSING:evidence"])
        self.assertEqual(museum["entries"], [{"candidate_id": "RESULT:D1:ANALYSIS:h20", "category": "THESIS",
                                              "grade": "C"}])


# ---------------------------------------------------------------------------------------------------------------
# n. robustness, LEARNING_FAILED and the earlier block (fix 1 and 2 of the rerun)
# ---------------------------------------------------------------------------------------------------------------

class RobustnessTests(CliCase):
    def test_a_non_json_file_is_an_error_and_other_days_continue(self) -> None:
        self.write_day(doc(10, {"AAA": sym()}))
        broken = self.root / S[13] / "decision.json"
        broken.parent.mkdir(parents=True)
        broken.write_text("{broken", encoding="utf-8")
        rerun = self.root / S[11] / "decision.rerun-090000.json"
        rerun.write_text(json.dumps(doc(10, {"BBB": sym()})), encoding="utf-8")
        loaded = scorer.load_decision_days(self.root)
        self.assertEqual([(item["day"], "error" in item) for item in loaded["days"]], [(S[11], False), (S[13], True)])
        self.assertEqual(loaded["days"][1]["sha256"], hashlib.sha256(b"{broken").hexdigest())
        code, out, report = self.run_main("--learning")
        self.assertEqual(code, 0)
        learning = report["learning"]
        self.assertIn({"reason": "DECISION_NOT_JSON", "file": f"{S[13]}/decision.json"}, learning["errors"])
        self.assertTrue(day_row(learning, S[11])["eligible"])
        self.assertEqual(units_of(learning, "BBB"), [])
        self.assertIn("DECISION_NOT_JSON", out)
        self.assertEqual(scorer.load_decision_days(self.tmp / "absent")["status"], "MISSING")

    def test_the_output_root_is_still_guarded(self) -> None:
        journal = self.tmp / "ledger" / "decision_journal.json"
        for root in (journal.parent, journal.parent.parent, scorer.REPO_ROOT / "stock-strategy-system" / "x",
                     scorer.REPO_ROOT / "workspace" / "policies", scorer.REPO_ROOT / "workspace" / "state"):
            with self.subTest(root=str(root)):
                with self.assertRaises(ValueError):
                    scorer.check_output_root(root, journal)
        self.assertEqual(scorer.check_output_root(self.output_root, journal), self.output_root.resolve())

    def test_a_learning_failure_is_a_status_with_a_fixed_shape(self) -> None:
        self.write_day(doc(10, {"AAA": sym()}))
        with mock.patch.object(scorer, "score_learning", side_effect=RuntimeError("boom")):
            code, out, report = self.run_main("--learning")
        self.assertEqual(code, 0)
        learning = report["learning"]
        self.assertEqual(learning["decision_days"], [])
        self.assertEqual(len(learning["errors"]), 1)
        self.assertTrue(learning["errors"][0]["reason"].startswith(scorer.LEARNING_FAILED + ":RuntimeError"))
        self.assertTrue(scorer._learning_failed(learning))
        self.assertIn("[학습 채점] 실패 LEARNING_FAILED", out)
        shape = scorer.failed_learning(ValueError("x"))
        self.assertEqual(set(shape), {"schema", "preregistration", "label", "display_only", "decision_days", "errors"})
        self.assertEqual(shape["errors"], [{"reason": "LEARNING_FAILED:ValueError:x"}])

    def test_a_failed_week_does_not_reset_the_preservation_marks(self) -> None:
        original = doc(10, {"AAA": sym()})
        path = self.write_day(original)
        _code, _out, week0 = self.run_main("--learning")
        first_sha = day_row(week0["learning"], S[11])["first_sha256"]
        self.assertEqual(first_sha, hashlib.sha256(path.read_bytes()).hexdigest())
        path.write_text(json.dumps(doc(10, {"AAA": sym()}, generated=f"{S[13]}T07:45:00+09:00")), encoding="utf-8")
        _code, _out, week1 = self.run_main("--learning")
        self.assertEqual(day_row(week1["learning"], S[11])["flags"], ["PRESERVATION_BROKEN"])
        with mock.patch.object(scorer, "score_learning", side_effect=RuntimeError("boom")):
            _code, _out, week2 = self.run_main("--learning")
        self.assertTrue(scorer._learning_failed(week2["learning"]))
        previous = scorer.find_previous_learning(self.output_root)
        self.assertEqual(day_row({"decision_days": previous["decision_days"]}, S[11])["flags"],
                         ["PRESERVATION_BROKEN"])
        path.write_text(json.dumps(original), encoding="utf-8")  # even the original bytes do not clear the mark
        _code, _out, week3 = self.run_main("--learning")
        row = day_row(week3["learning"], S[11])
        self.assertEqual((row["flags"], row["first_sha256"], row["eligible"]), (["PRESERVATION_BROKEN"], first_sha, False))
        self.assertEqual(week3["learning"]["previous_report"], previous["path"])

    def test_previous_block_search_skips_unreadable_and_failed_reports(self) -> None:
        self.assertIsNone(scorer.find_previous_learning(self.tmp / "absent"))
        good = {"learning": {"errors": [], "decision_days": [{"day": S[11], "first_sha256": "a"}]}}
        failed = {"learning": scorer.failed_learning(RuntimeError("x"))}
        for name, content in (("20261011T002000Z", good), ("20261018T002000Z", failed),
                              ("20261018T002000Z-1", "{broken"), ("20261019T002000Z", {"no": "learning"})):
            folder = self.output_root / name
            folder.mkdir(parents=True)
            (folder / scorer.REPORT_FILE).write_text(content if isinstance(content, str) else json.dumps(content),
                                                     encoding="utf-8")
        found = scorer.find_previous_learning(self.output_root)
        self.assertEqual((found["path"], found["decision_days"][0]["day"]), ("20261011T002000Z", S[11]))

    def test_learning_values_are_display_only(self) -> None:
        self.write_day(doc(10, {"AAA": sym()}))
        _code, out, report = self.run_main("--learning")
        learning = report["learning"]
        self.assertEqual((learning["schema"], learning["label"], learning["display_only"]),
                         ("journal-learning-1.0", "COUNTERFACTUAL_D", True))
        self.assertEqual(learning["preregistration"], scorer.PREREGISTRATION)
        self.assertNotIn("order_authority", learning)
        self.assertNotIn("quantity_authority", learning)
        self.assertEqual(learning["epochs"], {"status": "OK", "count": 1})
        self.assertEqual(learning["museum"]["status"], "MISSING")
        self.assertIn("[Failure Museum] MISSING", out)


class DayFailureTests(unittest.TestCase):
    def test_one_failing_day_is_an_error_of_that_day_only(self) -> None:
        original = scorer._day_units

        def flaky(day: str, *args: object) -> list:
            if day == S[11]:
                raise KeyError("odd file")
            return original(day, *args)

        odd = doc(10, {"AAA": sym()})
        odd["tickets"] = 7  # not a list: read as no ticket, never an exception
        with mock.patch.object(scorer, "_day_units", side_effect=flaky):
            learning = learn([doc(10, {"AAA": sym()}), doc(20, {"AAA": sym()})])
        self.assertIn({"reason": "DAY_UNITS_FAILED:KeyError", "file": f"{S[11]}/decision.json"}, learning["errors"])
        self.assertEqual([unit["day"] for unit in units_of(learning, "AAA")], [S[21]])
        self.assertEqual(len(units_of(learn([odd]), "AAA")), 1)


class FindingLineTests(unittest.TestCase):
    def test_screen_texts(self) -> None:  # the scorer file stays ASCII, so the Korean is checked here
        self.assertEqual(scorer.LEARNING_MESSAGES, {
            "days": "[학습 채점] 결정 날짜 {total}일 · 자격 {eligible} · 제외 {excluded} · 보존 깨짐 {broken} (표시 전용 D)",
            "buckets": "[학습 채점] 버킷 {buckets}개 · 결론 허용 {allowed}개 (독립 단위 {minimum}건 기준)",
            "finding": "[학습 발견] {family} {key} {finding} · n {n} · 평균 {mean} · 중앙값 {median} — 표시 전용 D — "
                       "규칙 변경 근거 아님",
            "museum": "[Failure Museum] {status} · 후보 {candidates} · 채움 {filled} · 대기 {pending}",
            "errors": "[학습 채점] 오류 {count}건: {reasons}",
            "failed": "[학습 채점] 실패 {reason} — 기존 채점 결과는 그대로"})
        (SKILL_ROOT / "scripts" / "score_decision_journal.py").read_bytes().decode("ascii")

    def test_finding_lines_carry_the_display_label(self) -> None:
        learning = learn([doc(10, {"AAA": sym()})])
        learning["buckets"] = [{"family": "GATE", "key": ["buy", "G", 1], "finding": "COST", "n_scored": 30,
                                "mean": "0.010000", "median": "0.010000", "conclusion_allowed": True},
                               {"family": "SCENARIO_BAND", "key": ["buy", 1], "n_scored": 30, "mean": None,
                                "median": None, "conclusion_allowed": True,
                                "finding": ["DOWN_TAIL_UNDERSTATED", "UP_TAIL_UNDERSTATED"]}]
        lines = [line for line in scorer.render_learning(learning) if line.startswith("[학습 발견]")]
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(line.endswith("표시 전용 D — 규칙 변경 근거 아님") for line in lines))


if __name__ == "__main__":
    unittest.main()
