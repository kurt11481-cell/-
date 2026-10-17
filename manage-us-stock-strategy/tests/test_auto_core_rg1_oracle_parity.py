"""ev-rg1-hyper parity: the core rrec1 and the independent calculator (docs/claude/t2rc-oracle.py, loaded read-only with
importlib; it never imports auto_core*) give the same status and RG1 on the same synthetic inputs, and the calculator's
R-REC1 fact loader keeps the same records and damage facts as auto_core_inputs.load_research (G-1-1).

The calculator gets the core's indicator arrays (close, low, ret1, sigma60, hi20, EMA50), so only the R-REC1 logic is
compared. TEST_ONLY data; nothing is written outside a temporary folder.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "manage-us-stock-strategy/tests"
sys.path.insert(0, str(TESTS))

import test_auto_core_rg1_damage as cases  # noqa: E402  (also puts scripts and fixtures on the path)
import auto_core_inputs as inputs  # noqa: E402
import helpers  # noqa: E402
from validation_common import write_json  # noqa: E402

ORACLE_PATH = ROOT / "docs/claude/t2rc-oracle.py"


def load_oracle():
    spec = importlib.util.spec_from_file_location("t2rc_oracle_parity", ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load_oracle()


class _Obj:
    pass


def oracle_inputs(series):
    s, i = _Obj(), _Obj()
    s.dates = list(series["days"])
    s.index = {day: k for k, day in enumerate(s.dates)}
    s.c, s.l = list(series["close"]), list(series["low"])
    i.ret, i.sigma, i.hi20, i.ema50 = series["ret1"], series["sigma60"], series["hi20"], series["ema50"]
    return {"SOXX": s, "X": s}, {"SOXX": i, "X": i}


def both(series, facts, *, sessions="all", gap=None, accepted=None):
    """(core status, core RG1), (calculator status, calculator RG1); every fact sits in the last record."""
    days = list(series["days"])
    covered = [day for day in days if day != gap] if sessions == "gap" else days
    core = cases.rules.rrec1(benchmark=series, candidate=None, evaluation_session=days[-1], ev3_user_dates=[],
                             thesis_damage=list(facts), ev4_sessions=[],
                             research_sessions=None if sessions == "none" else covered, card_accepted_on=accepted)
    records = {day: [] for day in covered}
    records[days[-1]] = list(facts)
    ser, ind = oracle_inputs(series)
    mine = oracle.rrec1(None, ser, ind, days[-1], "X", "SOXX", set(), records, None, None, (), accepted_on=accepted)
    core_rg1 = core["rg"].get("RG1") if "rg" in mine else None
    return (core["status"], core_rg1), (mine["status"], (mine.get("rg") or {}).get("RG1"))


class RuleParityTests(unittest.TestCase):
    def check(self, series, facts, **kwargs):
        core, mine = both(series, facts, **kwargs)
        self.assertEqual(core, mine)
        return core

    def test_named_cases(self):
        fact, nd = cases.fact, cases.next_day
        series, days = cases.world(crashes=(80,))
        self.assertEqual(self.check(series, [fact("D1", days[80])]), ("no", "no"))                      # S1
        self.assertEqual(self.check(series, [fact("D1", days[80])], accepted=nd(days[80])), ("ok", None))
        series, days = cases.world(crashes=(70, 85))
        self.assertEqual(self.check(series, [fact("D2", days[72])]), ("no", "no"))                      # S2
        series, days = cases.world(crashes=(60,))
        self.assertEqual(self.check(series, [fact("D3", days[62])]), ("no", "no"))                      # S3
        series, days = cases.world(crashes=(70,))
        self.assertEqual(self.check(series, [fact("D4", days[85])]), ("no", "no"))                      # S4
        series, days = cases.world()
        self.assertEqual(self.check(series, [fact("D5", days[85])]), ("no", "no"))                      # S5
        self.assertEqual(self.check(series, [fact("D6", days[85])], accepted=days[85]), ("no", "no"))   # S6
        self.assertEqual(self.check(series, [fact("D6", days[85])], accepted=nd(days[85])), ("ok", None))
        self.assertEqual(self.check(series, [fact("D7", days[cases.W0])]), ("no", "no"))                # S7
        self.assertEqual(self.check(series, [fact("D7", days[cases.W0 - 1])]), ("ok", None))
        series, days = cases.world(crashes=(70,), flat_from=79)                                         # S6b
        self.assertEqual(self.check(series, [fact("D6B", days[73])], accepted=days[85]), ("no", "ok"))
        self.assertEqual(self.check(series, [fact("D6B", days[73])], accepted=nd(days[73])), ("ok", None))
        series, days = cases.world(dips=(85,))                                                          # S9
        marked = fact("D9", days[85], damage_source=inputs.DAMAGE_DOMAIN_SOURCE)
        self.assertEqual(self.check(series, [marked]), ("no", "no"))
        self.assertEqual(self.check(series, [fact("D9", days[85])]), ("no", "no"))

    def test_seeded_cases(self):
        # Events before index 50 are left out: the calculator stops at a missing EMA50 (its own data-gap rule, older
        # than this change), the core does not.
        compared = 0
        for seed in cases.SEEDS:
            case = cases.seeded_case(seed)
            if any(k < 50 for k in case["crashes"] + case["dips"]):
                continue
            series, days = cases.world(crashes=case["crashes"], dips=case["dips"], flat_from=case["flat_from"])
            with self.subTest(seed=seed):
                for accepted in (None, case["accepted"]):
                    core, mine = both(series, case["facts"], sessions=case["coverage"], gap=days[case["gap"]],
                                      accepted=accepted)
                    self.assertEqual(core, mine, case)
                compared += 1
        self.assertGreater(compared, 15)


class LoaderParityTests(unittest.TestCase):
    """S15 (G-1-1): which records and damage facts reach rrec1 in the core and in the calculator."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.days = helpers.sessions("2026-09-01", 30)
        self.decide = datetime.fromisoformat(f"{self.days[-1]}T19:00:00-04:00")

    def record(self, record_day, session, facts):
        write_json(self.root / "workspace/outputs/research-records" / record_day / "research-record.json", {
            "schema_version": "auto-core-research-record-1.0", "record_day_kst": record_day, "evaluation_session": session,
            "written_at": f"{session}T17:00:00-04:00", "writer": "TEST_ONLY", "earnings": {}, "official_facts": facts,
            "integrated_check_run": None, "order_authority": False, "quantity_authority": "none"})

    def fact(self, fact_id, session, announced=None, **extra):
        value = {"fact_id": "DMG-" + fact_id, "symbol": "SOXL", "direction": "-", "kind": "thesis", "card_trigger_ids": [],
                 "event_session": session, "announced_at": announced or f"{session}T16:30:00-04:00",
                 "source_kind": "SEC_FILING", "source_url": "https://www.sec.gov/x", "criterion_a": False,
                 "root_thesis_damage": True, "summary_ko": "TEST_ONLY"}
        value.update(extra)
        return value

    def calendar(self):
        cal = object.__new__(oracle.Calendar)
        cal.sessions = list(self.days)
        cal.close_at = {day: f"{day}T16:00:00-04:00" for day in self.days}
        cal.open_at = {day: f"{day}T09:30:00-04:00" for day in self.days}
        cal.index = {day: k for k, day in enumerate(self.days)}
        return cal

    def test_same_records_and_first_versions(self):
        d = self.days
        nd = cases.next_day
        self.record(nd(d[3]), d[3], [self.fact("F1", d[3])])
        # a fact without an offset: the whole record fails the schema (no coverage either)
        self.record(nd(d[5]), d[5], [self.fact("F9", d[5]), self.fact("F8", d[5], f"{d[5]}T16:30:00")])
        late = (self.decide + timedelta(minutes=5)).isoformat()
        self.record(nd(d[7]), d[7], [self.fact("F2", d[7], late), self.fact("F3", d[8]),
                                     self.fact("F4", d[7], summary_ko="x" * 201), self.fact("F5", d[7])])
        # two records of one evaluation session; the same fact_id in another version later
        self.record(nd(d[10]), d[10], [self.fact("F6", d[10], f"{d[10]}T09:00:00-04:00")])
        self.record(nd(nd(d[10])), d[10], [self.fact("F6", d[10], f"{d[10]}T17:00:00-04:00"), self.fact("F7", d[10])])
        self.record(nd(d[12]), d[12], [self.fact("F6", d[12], f"{d[12]}T16:30:00-04:00", event_session=d[12])])
        registry = {"status": "OK", "entries": {"SOXL": {"official_domains": []}}, "damage_domains": []}
        core = inputs.load_research(root=self.root / "workspace/outputs/research-records", run_day=nd(d[-1]),
                                    calendar_sessions=self.days, decide_time=self.decide, registry=registry,
                                    window_start=d[0])
        reg = {"symbols": {"SOXL": {"official_domains": []}}}
        mine = oracle.load_rrec1_records(str(self.root), nd(d[-1]), self.decide, reg, self.calendar())
        self.assertEqual(sorted(mine), core["sessions"])
        self.assertNotIn(d[5], core["sessions"])
        first = {}
        for session in sorted(mine):
            for item in mine[session]:
                first.setdefault(item["fact_id"], item["announced_at"])
        self.assertEqual(first, {item["fact_id"]: item["announced_at"] for item in core["damage"]})
        self.assertEqual(sorted(first), ["DMG-F1", "DMG-F5", "DMG-F6", "DMG-F7"])
        self.assertEqual(first["DMG-F6"], f"{d[10]}T09:00:00-04:00")
        # the C7 history of the calculator is unchanged: it still reads the record the schema rejects
        history, _files = oracle.load_research_history(str(self.root), nd(d[-1]), self.decide, reg, self.calendar())
        self.assertIn(d[5], history)

    def test_domain_facts(self):
        d = self.days
        nd = cases.next_day
        msft = self.fact("M1", d[4], source_url="https://www.microsoft.com/en-us/investor/x", symbol="MSFT")
        self.record(nd(d[4]), d[4], [msft, dict(msft, fact_id="DMG-M2", root_thesis_damage=False), self.fact("F1", d[4])])
        for domains in ([], ["microsoft.com"]):
            with self.subTest(domains=domains):
                core = inputs.load_research(root=self.root / "workspace/outputs/research-records", run_day=nd(d[-1]),
                                            calendar_sessions=self.days, decide_time=self.decide,
                                            registry={"status": "OK", "entries": {}, "damage_domains": domains},
                                            window_start=d[0])
                mine = oracle.load_rrec1_records(str(self.root), nd(d[-1]), self.decide,
                                                 {"symbols": {}, "thesis_damage_domains": domains}, self.calendar())
                core_view = [(item["fact_id"], item.get("damage_source")) for item in core["damage"]]
                mine_view = [(item["fact_id"], item.get("damage_source")) for item in mine[d[4]]]
                self.assertEqual(core_view, mine_view)
                self.assertEqual(core_view, [("DMG-F1", None)] + ([("DMG-M1", "THESIS_DAMAGE_DOMAIN")] if domains else []))
                # the calculator's other fact consumers never see the marked fact
                facts, dropped = oracle.validate_facts(
                    {"written_at": f"{d[4]}T17:00:00-04:00", "official_facts": [msft]},
                    {"symbols": {}, "thesis_damage_domains": domains}, self.calendar(), d[4], self.decide, [])
                self.assertEqual((facts, dropped), ([], [["DMG-M1", "DOMAIN"]]))

    # Judge 1 item 6: a thesis-damage-domain fact goes through every remaining check in both loaders.
    def domain_fact(self, fact_id, session, **extra):
        return self.fact(fact_id, session, source_url="https://www.microsoft.com/en-us/investor/x", symbol="MSFT", **extra)

    def loaders(self):
        d = self.days
        nd = cases.next_day
        core = inputs.load_research(root=self.root / "workspace/outputs/research-records", run_day=nd(d[-1]),
                                    calendar_sessions=self.days, decide_time=self.decide,
                                    registry={"status": "OK", "entries": {}, "damage_domains": ["microsoft.com"]},
                                    window_start=d[0])
        mine = oracle.load_rrec1_records(str(self.root), nd(d[-1]), self.decide,
                                         {"symbols": {}, "thesis_damage_domains": ["microsoft.com"]}, self.calendar())
        return core, mine

    def test_domain_fact_on_a_non_session_day_is_dropped_by_both(self):
        d = self.days
        saturday = cases.next_day(d[3])
        self.assertEqual(datetime.fromisoformat(saturday).weekday(), 5)
        self.assertNotIn(saturday, d)
        self.record(cases.next_day(d[4]), d[4], [self.domain_fact("SAT", saturday), self.fact("F1", d[4])])
        core, mine = self.loaders()
        self.assertEqual([item["fact_id"] for item in core["damage"]], ["DMG-F1"])
        self.assertEqual([item["fact_id"] for item in mine[d[4]]], ["DMG-F1"])
        _facts, dropped = oracle.validate_facts(
            {"written_at": f"{d[4]}T17:00:00-04:00", "official_facts": [self.domain_fact("SAT", saturday)]},
            {"symbols": {}}, self.calendar(), d[4], self.decide, [], damage_domains=["microsoft.com"])
        self.assertEqual(dropped, [["DMG-SAT", "EVENT_SESSION"]])

    def test_domain_fact_with_an_unknown_source_kind_is_dropped(self):
        d = self.days
        self.record(cases.next_day(d[4]), d[4], [self.domain_fact("KND", d[4], source_kind="BLOG"), self.fact("F1", d[4])])
        core, mine = self.loaders()
        self.assertEqual([item["fact_id"] for item in mine[d[4]]], ["DMG-F1"])
        # The core rejects the whole record by the schema enum (record-level difference already there, out of scope).
        self.assertEqual((core["damage"], core["sessions"]), ([], []))
        _facts, dropped = oracle.validate_facts(
            {"written_at": f"{d[4]}T17:00:00-04:00", "official_facts": [self.domain_fact("KND", d[4], source_kind="BLOG")]},
            {"symbols": {}}, self.calendar(), d[4], self.decide, [], damage_domains=["microsoft.com"])
        self.assertEqual(dropped, [["DMG-KND", "SOURCE_KIND"]])

    def test_default_call_matches_the_base_calculator(self):
        # BASE_KEEP / BASE_DROPPED: the base calculator (sha256_lf 5607b09b...) on default_call_inputs().
        given = default_call_inputs()
        keep, dropped = oracle.validate_facts(given["rr"], given["reg"], given["cal"], given["eval_session"],
                                              given["decide_at"], given["prev_seen"])
        self.assertEqual((keep, dropped), (BASE_KEEP, BASE_DROPPED))


def default_call_inputs():
    """Fixed validate_facts inputs (no damage_domains): official, other host, bad kind, non-session day, http URL, bad
    direction, previous-session facts seen / not seen (the second with a U+2212 minus)."""
    days = helpers.sessions("2026-09-01", 30)
    cal = object.__new__(oracle.Calendar)
    cal.sessions = list(days)
    cal.close_at = {day: f"{day}T16:00:00-04:00" for day in days}
    cal.open_at = {day: f"{day}T09:30:00-04:00" for day in days}
    cal.index = {day: k for k, day in enumerate(days)}

    def item(fact_id, **extra):
        value = {"fact_id": fact_id, "symbol": "SOXL", "source_url": "https://www.sec.gov/x", "source_kind": "SEC_FILING",
                 "event_session": days[5], "direction": "-", "root_thesis_damage": True}
        value.update(extra)
        return value

    facts = [item("DMG-A1"), item("DMG-A2", symbol="MSFT", source_url="https://www.microsoft.com/en-us/investor/x"),
             item("DMG-A3", source_kind="BLOG"), item("DMG-A4", event_session="2026-09-05"),
             item("DMG-A5", source_url="http://www.sec.gov/x"), item("DMG-A6", direction="x"),
             item("DMG-P1", event_session=days[4], source_url="https://ir.example.com/x"),
             item("DMG-P2", event_session=days[4], direction="\u2212", root_thesis_damage=False)]
    return {"rr": {"written_at": f"{days[5]}T17:00:00-04:00", "official_facts": facts},
            "reg": {"symbols": {"SOXL": {"official_domains": ["example.com"]}}}, "cal": cal, "eval_session": days[5],
            "decide_at": datetime.fromisoformat(f"{days[-1]}T19:00:00-04:00"), "prev_seen": ["DMG-P1"]}


BASE_KEEP = [
    {"fact_id": "DMG-A1", "symbol": "SOXL", "source_url": "https://www.sec.gov/x", "source_kind": "SEC_FILING",
     "event_session": "2026-09-08", "direction": "-", "root_thesis_damage": True, "new": True},
    {"fact_id": "DMG-P1", "symbol": "SOXL", "source_url": "https://ir.example.com/x", "source_kind": "SEC_FILING",
     "event_session": "2026-09-07", "direction": "-", "root_thesis_damage": True, "new": False},
    {"fact_id": "DMG-P2", "symbol": "SOXL", "source_url": "https://www.sec.gov/x", "source_kind": "SEC_FILING",
     "event_session": "2026-09-07", "direction": "-", "root_thesis_damage": False, "new": True}]
BASE_DROPPED = [["DMG-A2", "DOMAIN"], ["DMG-A3", "SOURCE_KIND"], ["DMG-A4", "EVENT_SESSION"], ["DMG-A5", "URL"],
                ["DMG-A6", "DIRECTION"]]


if __name__ == "__main__":
    unittest.main()
