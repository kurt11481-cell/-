"""ev-rg1-hyper (decision a, docs/claude/event-strategy-2026-10-13.md 11-1; docs/claude/ev-rg1-hyper-builder-prompt.md):
an official root-thesis-damage fact keeps R-REC1 RG1 "no" until the card is accepted again, whatever the event day,
a new event, the time decay or a close; the time-decay close does not happen on a day RG1 is "no"; registry
thesis_damage_domains facts reach RG1 only.

Synthetic series only (TEST_ONLY): helpers.zigzag(100, 500, 2.0, 0.3) closes (sigma60 about 0.8%, 1.2% after a crash),
a crash day at 0.95 of the previous close (EV1), the 60-session window starts at index 40.
"""

from __future__ import annotations

import copy
import datetime as dt
import random
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
TESTS = ROOT / "manage-us-stock-strategy/tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(TESTS))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_inputs as inputs  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import auto_core_tickets as tickets  # noqa: E402
import helpers  # noqa: E402
from test_auto_core_decide import CALENDAR_DAYS, DAYS, LAST, Env, NOW, RUN_DAY  # noqa: E402
from validation_common import load_json, validate_instance, write_json  # noqa: E402

N = 100
W0 = 40  # first index of the 60-session window ending at index 99


def closes_of(*, crashes=(), dips=(), flat_from=None):
    """crash: 0.95 x the previous close (EV1); dip: 0.988 x (about -1.2%, at most -1 sigma60, above -2 sigma60);
    flat_from: from that index the closes alternate 511.5 / 514.5 (below the rising EMA50 on the low days: DS1)."""
    closes = helpers.zigzag(N, 500, 2.0, 0.3)
    for k in crashes:
        closes[k] = round(closes[k - 1] * 0.95, 4)
    for k in dips:
        closes[k] = round(closes[k - 1] * 0.988, 4)
    if flat_from is not None:
        for k in range(flat_from, N):
            closes[k] = 513.0 + (1.5 if k % 2 else -1.5)
    return closes


def world(through=N - 1, **kwargs):
    days = helpers.sessions("2026-03-02", N)
    data = helpers.bars("SOXX", days, closes_of(**kwargs))
    return rules.build_series(data["adjusted"], days, days[through]), days


def fact(fact_id, day, announced=None, **extra):
    value = {"fact_id": fact_id, "event_session": day, "root_thesis_damage": True,
             "announced_at": announced if announced is not None else f"{day}T16:05:00-04:00"}
    value.update(extra)
    return value


def next_day(day):
    return (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()


def run(series, facts=(), *, research=True, **kwargs):
    arguments = dict(benchmark=series, candidate=None, evaluation_session=series["days"][-1], ev3_user_dates=[],
                     thesis_damage=None if facts is None else list(facts), ev4_sessions=[],
                     research_sessions=list(series["days"]) if research else None)
    arguments.update(kwargs)
    return rules.rrec1(**arguments)


def view(result):
    return result["status"], result["open"], result["rg"].get("RG1")


class RuleCaseTests(unittest.TestCase):
    """S1-S7 and S9 on rrec1 (the base values in the comments were measured on the base commit a9ea338)."""

    def test_s1_damage_on_the_event_day(self):
        series, days = world(crashes=(80,))
        damage = [fact("D1", days[80])]
        self.assertEqual(view(run(series)), ("ok", False, "ok"))            # closes at index 86 without the fact
        result = run(series, damage)                                         # base: closed at 86, ok
        self.assertEqual(view(result), ("no", True, "no"))
        self.assertEqual(result["event"]["date"], days[80])
        self.assertEqual(result["rg1_damage"], ["D1"])
        accepted = run(series, damage, card_accepted_on=next_day(days[80]))  # re-accepted on its KST date
        self.assertEqual((view(accepted), accepted["closed_at"]), (("ok", False, "ok"), days[86]))
        self.assertNotIn("rg1_damage", accepted)

    def test_s2_a_new_event_does_not_forget_the_damage(self):
        series, days = world(crashes=(70, 85))
        result = run(series, [fact("D2", days[72])])                         # base: event 85 closed at 91, ok
        self.assertEqual((view(result), result["event"]["date"]), (("no", True, "no"), days[85]))

    def test_s3_time_decay_does_not_close_while_rg1_is_no(self):
        series, days = world(crashes=(60,))
        result = run(series, [fact("D3", days[62])])                         # base: time decay at 80, ok
        self.assertEqual(view(result), ("no", True, "no"))
        self.assertNotIn("closed_at", result)
        self.assertEqual(result["rg"]["RG2"], "ok")

    def test_s4_damage_after_a_close_blocks(self):
        series, days = world(crashes=(70,))
        result = run(series, [fact("D4", days[85])])                         # base: closed at 76, ok
        self.assertEqual(view(result), ("no", False, "no"))
        self.assertEqual((result["closed_at"], result["reasons"], result["rg1_damage"]),
                         (days[76], ["RG1_THESIS_DAMAGE:D4"], ["D4"]))
        self.assertEqual(result["events"], run(series)["events"])

    def test_s5_damage_without_an_event(self):
        series, days = world()
        result = run(series, [fact("D5", days[85])])                         # base: ok
        self.assertEqual(view(result), ("no", False, "no"))
        self.assertEqual((result["rg"], result["events"], result["event"]), ({"RG1": "no"}, [], None))
        self.assertEqual((result["reasons"], result["rg1_damage"]), (["RG1_THESIS_DAMAGE:D5"], ["D5"]))
        self.assertEqual(run(series, [fact("D5", days[85]), fact("A0", days[50])])["reasons"],
                         ["RG1_THESIS_DAMAGE:A0,D5"])

    def test_s6_release_boundary(self):
        series, days = world()
        day = days[85]                       # announced 16:05 New York time = the next calendar day in KST
        after_close = [fact("D6", day)]
        self.assertEqual(view(run(series, after_close, card_accepted_on=day)), ("no", False, "no"))
        self.assertEqual(view(run(series, after_close, card_accepted_on=next_day(day))), ("ok", False, None))
        short, _ = world(through=86)
        self.assertEqual(short["days"][-1], days[86])
        late = days[87]                      # accepted after the evaluation session: not yet
        self.assertEqual(view(run(short, after_close, card_accepted_on=late)), ("no", False, "no"))
        self.assertEqual(rules.damage_release_day(fact("X", day, f"{day}T09:00:00-04:00")), day)
        for announced in ("", f"{day}T16:05:00", "not a time"):
            with self.subTest(announced=announced):
                self.assertIsNone(rules.damage_release_day(fact("X", day, announced)))
                blocked = run(series, [fact("D6", day, announced)], card_accepted_on=days[90])
                self.assertEqual(view(blocked), ("no", False, "no"))
        missing = fact("D6", day)
        del missing["announced_at"]
        self.assertEqual(view(run(series, [missing], card_accepted_on=days[90])), ("no", False, "no"))
        zulu = fact("D6", day, f"{day}T20:05:00Z")
        self.assertEqual(rules.damage_release_day(zulu), next_day(day))
        self.assertEqual(view(run(series, [zulu], card_accepted_on=next_day(day))), ("ok", False, None))
        for text in ("2026-7-1", "20260701", None, 20260701):
            with self.subTest(accepted=text):
                self.assertEqual(view(run(series, after_close, card_accepted_on=text)), ("no", False, "no"))

    def test_s6b_no_retroactive_release(self):
        # event 70, damage 73, RG2-RG4 met from 76 (RG1 no), DS1 from 79 on, re-accepted at 85
        series, days = world(crashes=(70,), flat_from=79)
        damage = [fact("D6B", days[73])]
        self.assertEqual(view(run(series, damage)), ("no", True, "no"))                  # base: open, no
        self.assertEqual(view(run(series, damage, card_accepted_on=days[85])), ("no", True, "ok"))  # RG2 no (DS1)
        self.assertNotIn("closed_at", run(series, damage, card_accepted_on=days[85]))
        early = run(series, damage, card_accepted_on=next_day(days[73]))                 # before the gates were met
        self.assertEqual((view(early), early["closed_at"]), (("ok", False, "ok"), days[76]))

    def test_s7_window_edge(self):
        series, days = world()
        self.assertEqual(view(run(series, [fact("D7", days[W0])])), ("no", False, "no"))
        self.assertEqual(view(run(series, [fact("D7", days[W0 - 1])])), ("ok", False, None))

    def test_s9_thesis_damage_domain_fact_is_rg1_only(self):
        series, days = world(dips=(85,))
        self.assertLessEqual(series["ret1"][85], -series["sigma60"][85])
        self.assertGreater(series["ret1"][85], -2 * series["sigma60"][85])
        marked = run(series, [fact("D9", days[85], damage_source=inputs.DAMAGE_DOMAIN_SOURCE)])
        self.assertEqual((view(marked), marked["events"]), (("no", False, "no"), run(series)["events"]))
        plain = run(series, [fact("D9", days[85])])
        self.assertEqual((view(plain), plain["event"]["kinds"]), (("no", True, "no"), ["EV3b"]))

    def test_untracked_records_keep_rg1_unknown(self):
        series, days = world(crashes=(80,))
        self.assertEqual(run(series, None, research=False)["rg"]["RG1"], "unk")
        none_tracked = rules.rrec1(benchmark=series, candidate=None, evaluation_session=days[-1], ev3_user_dates=[],
                                   thesis_damage=None, ev4_sessions=[])
        self.assertNotIn("rg1_damage", none_tracked)

    def test_record_gap_still_wins(self):
        # R4: an EV3 (b) record gap makes the result unknown before the R3 block
        series, days = world(dips=(70,))
        result = run(series, [fact("D5", days[85])], research_sessions=[day for day in days if day != days[70]])
        self.assertEqual((result["status"], result["open"]), ("unk", None))
        self.assertEqual(result["reasons"], ["RG1_THESIS_DAMAGE:D5", f"EV3B_RECORD_GAP:{days[70]}"])

    def test_uncleared_damage_function(self):
        facts = [fact("B", "2026-05-04"), fact("A", "2026-05-05"), fact("C", "2026-04-01")]
        self.assertEqual([item["fact_id"] for item in rules.uncleared_damage(facts, "2026-04-02", "2026-05-06")],
                         ["A", "B"])
        self.assertEqual([item["fact_id"] for item in rules.uncleared_damage(facts, "2026-04-02", "2026-05-06",
                                                                               "2026-05-05")], ["A"])
        self.assertEqual(rules.uncleared_damage(facts, "2026-04-02", "2026-05-04", "2026-05-05")[0]["fact_id"], "B")


class PortfolioDateTests(unittest.TestCase):
    """S8: the portfolio card date is the earliest accepted.date of the holdings; one holding without it -> none."""

    def test_earliest_holding(self):
        dates = {"SOXL": "2026-10-04", "NBIS": "2026-10-02", "MU": "2026-09-01"}
        self.assertEqual(decide_module.portfolio_accepted_on(dates, {"SOXL": 1, "NBIS": 2}), "2026-10-02")
        self.assertIsNone(decide_module.portfolio_accepted_on({"SOXL": "2026-10-04", "NBIS": None}, {"SOXL": 1, "NBIS": 2}))
        self.assertIsNone(decide_module.portfolio_accepted_on(dates, {"SOXL": 1, "MVLL": 2}))
        self.assertIsNone(decide_module.portfolio_accepted_on(dates, {}))
        self.assertIsNone(decide_module.card_accepted_on({"entry": None}))
        self.assertIsNone(decide_module.card_accepted_on({"entry": {"accepted": {"date": "2026-10-4"}}}))
        self.assertEqual(decide_module.card_accepted_on({"entry": {"accepted": {"date": "2026-10-04"}}}), "2026-10-04")


def write_record(env, session, facts=()):
    day = next_day(session)
    write_json(env.research_root / day / "research-record.json", {
        "schema_version": "auto-core-research-record-1.0", "record_day_kst": day, "evaluation_session": session,
        "written_at": f"{session}T17:00:00-04:00", "writer": "TEST_ONLY", "earnings": {}, "official_facts": list(facts),
        "integrated_check_run": None, "order_authority": False, "quantity_authority": "none"})


def damage_fact(fact_id, session, *, symbol="SOXL", url="https://www.sec.gov/x", root=True, **extra):
    value = {"fact_id": fact_id, "symbol": symbol, "direction": "-", "kind": "thesis", "card_trigger_ids": [],
             "event_session": session, "announced_at": f"{session}T16:30:00-04:00", "source_kind": "COMPANY_IR",
             "source_url": url, "criterion_a": False, "root_thesis_damage": root, "summary_ko": "TEST_ONLY"}
    value.update(extra)
    return value


def set_registry(env, *, dates=None, domains=None):
    registry = load_json(env.registry)
    for symbol, date_text in (dates or {}).items():
        registry["symbols"][symbol]["accepted"]["date"] = date_text
    if domains is not None:
        registry["thesis_damage_domains"] = domains
    write_json(env.registry, registry)


class DecideTests(unittest.TestCase):
    """S8 / S9 / S12 / S14 through decide (the TEST_ONLY Env of test_auto_core_decide: SOXL held, MU watch, cards
    accepted 2026-10-01)."""

    def env(self, facts_by_session=None, **kwargs):
        env = Env(**kwargs)
        self.addCleanup(env.close)
        for session in DAYS[-25:-1]:
            write_record(env, session, (facts_by_session or {}).get(session, []))
        return env

    def test_s14_no_damage_adds_no_key(self):
        decision = self.env().run()
        self.assertNotIn("rg1_damage", decision["shock"])
        for item in decision["shock"]["by_symbol"].values():
            self.assertEqual(sorted(item), ["open", "rg", "status"])
        self.assertNotIn("2:RG1DMG", decision["alert_states"])
        self.assertFalse(any(alert["code"] == "2:RG1DMG" for alert in decision["alerts"]))

    def test_s8_damage_blocks_until_each_card_is_accepted_again(self):
        session = DAYS[-3]
        env = self.env({session: [damage_fact("SOXL-DMG-1", session)]})
        decision = env.run()
        self.assertEqual((decision["shock"]["status"], decision["shock"]["rg1_damage"]), ("no", ["SOXL-DMG-1"]))
        for symbol in ("MU", "SOXL"):
            entry = decision["shock"]["by_symbol"][symbol]
            self.assertEqual((entry["status"], entry["rg1_damage"]), ("no", ["SOXL-DMG-1"]))
        cells = {row["code"]: row["c"][4] for row in decision["buy_requirements"]}
        self.assertEqual(cells["MU"]["s"], "no")
        self.assertEqual(decision["alert_states"]["2:RG1DMG"], "SOXL-DMG-1|MU,SOXL")
        line = [alert for alert in decision["alerts"] if alert["code"] == "2:RG1DMG"]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0]["push"])                       # an exception: pushed in compare mode too
        self.assertEqual(decision["decision_mode"], "compare")
        self.assertNotIn("SOXL", line[0]["line"])
        self.assertNotIn("DMG", line[0]["line"])
        self.assertEqual(decision["alerts"][-1]["code"], "2:RG1DMG")
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        # SOXL (the only holding, so also the portfolio) re-accepted after the fact: only MU stays blocked
        env2 = self.env({session: [damage_fact("SOXL-DMG-1", session)]})
        set_registry(env2, dates={"SOXL": LAST})  # a KST date after the evaluation session would count a session later
        again = env2.run()
        self.assertNotIn("rg1_damage", again["shock"])
        self.assertNotIn("rg1_damage", again["shock"]["by_symbol"]["SOXL"])
        self.assertEqual(again["shock"]["by_symbol"]["MU"]["rg1_damage"], ["SOXL-DMG-1"])
        self.assertEqual(again["alert_states"]["2:RG1DMG"], "SOXL-DMG-1|MU")

    def test_s9_microsoft_ir_fact_reaches_rg1_only(self):
        session = DAYS[-3]
        msft = damage_fact("MSFT-CAPEX-1", session, symbol="MSFT", url="https://www.microsoft.com/en-us/investor/x")
        env = self.env({session: [msft]})
        set_registry(env, domains=["microsoft.com", "abc.xyz", "atmeta.com", "aboutamazon.com"])
        registry = inputs.load_registry(env.registry, repo=env.root, committed_check=lambda path, repo: (True, None))
        self.assertEqual(registry["damage_domains"], ["microsoft.com", "abc.xyz", "atmeta.com", "aboutamazon.com"])
        loaded = inputs.load_research(root=env.research_root, run_day=RUN_DAY, calendar_sessions=CALENDAR_DAYS,
                                      decide_time=NOW, registry=registry, window_start=DAYS[-60])
        self.assertEqual([(item["fact_id"], item["damage_source"]) for item in loaded["damage"]],
                         [("MSFT-CAPEX-1", inputs.DAMAGE_DOMAIN_SOURCE)])
        self.assertEqual(loaded["facts"], [])
        decision = env.run()
        self.assertEqual(decision["shock"]["rg1_damage"], ["MSFT-CAPEX-1"])
        self.assertNotIn("MSFT-CAPEX-1", decision["facts_seen"])
        for item in decision["evidence"].values():
            for side in item.values():
                self.assertNotIn("MSFT-CAPEX-1", side["official"])
        self.assertEqual(decision["shock"]["events"], self.env().run()["shock"]["events"])  # no EV3 (b) from it
        # root_thesis_damage false: dropped as before; no registry key: dropped as before
        for root, domains in ((False, ["microsoft.com"]), (True, None)):
            with self.subTest(root=root, domains=domains):
                other = self.env({session: [dict(msft, root_thesis_damage=root)]})
                if domains is not None:
                    set_registry(other, domains=domains)
                registry = inputs.load_registry(other.registry, repo=other.root,
                                                committed_check=lambda path, repo: (True, None))
                checked = inputs.check_record(load_json(other.research_root / next_day(session) / "research-record.json"),
                                              record_day=next_day(session), calendar_sessions=CALENDAR_DAYS,
                                              decide_time=NOW, registry=registry)
                self.assertEqual([item["reason"] for item in checked["dropped"]], ["SOURCE_HOST_NOT_OFFICIAL"])
                self.assertNotIn("damage_only", checked)
                self.assertNotIn("rg1_damage", other.run()["shock"])

    def test_check_record_shape_without_domain_facts(self):
        env = self.env()
        registry = inputs.load_registry(env.registry, repo=env.root, committed_check=lambda path, repo: (True, None))
        self.assertEqual(registry["damage_domains"], [])
        checked = inputs.check_record(load_json(env.research_root / RUN_DAY / "research-record.json"), record_day=RUN_DAY,
                                      calendar_sessions=CALENDAR_DAYS, decide_time=NOW, registry=registry)
        self.assertEqual(checked["status"], "OK", checked["reasons"])
        self.assertEqual(sorted(checked), ["dropped", "earnings", "evaluation_session", "facts", "integrated_check_run",
                                           "reasons", "record_day_kst", "status", "written_at"])


class TicketCellTests(unittest.TestCase):
    """S11: requirement (5) for a closed or absent event with an uncleared damage fact."""

    def fifth(self, shock):
        row = tickets.buy_requirements(
            symbol="SOXL", held=True, s7={"fresh": True, "e": 1.0}, nominal={"n": 1.0}, peaks={}, earnings=None,
            calendar_sessions=[], buy_session=None, evaluation_session="2026-10-12", generated_at=None,
            cash=Decimal("1000"), close=Decimal("10"), check={"entry": {}}, evidence={"basis_met": True, "composition": "x"},
            watch_status=None, m6={"s": "ok", "t": "x"}, shock={"reasons": [], **shock}, research_block=None)
        return row["c"][4]

    def test_cells(self):
        self.assertEqual(self.fifth({"status": "no", "open": False, "rg": {"RG1": "no"}}),
                         {"s": "no", "t": "\ub9c9\ud798 RG1 \uacf5\uc2dd \ud14c\uc81c \ud6fc\uc190(\uce74\ub4dc \uc7ac\uc218\ub77d \uc804)"})
        # the three earlier branches are unchanged
        self.assertEqual(self.fifth({"status": "unk", "open": None, "reasons": ["X"]}),
                         {"s": "unk", "t": "\ud655\uc778 \ud544\uc694(\ub9c9\ud798) X"})
        self.assertEqual(self.fifth({"status": "no", "open": True, "rg": {"RG1": "no", "RG2": "ok"}}),
                         {"s": "no", "t": "\ub9c9\ud798 \ubbf8\ucda9\uc871 RG1"})
        self.assertEqual(self.fifth({"status": "ok", "open": False, "rg": {}}),
                         {"s": "ok", "t": "\ud1b5\uacfc (\uc5f4\ub9b0 \uc774\ubca4\ud2b8 \uc5c6\uc74c)"})


class AlertTests(unittest.TestCase):
    """S12: the 2:RG1DMG state and its exception line."""

    def decision(self, shock):
        return {"symbols": {}, "evidence": {}, "account": {}, "exposure": {}, "buy_requirements": [], "tickets": [],
                "shock": shock}

    def alerts(self, shock, previous=None, mode="compare"):
        return decide_module.alert_candidates(decision=self.decision(shock), previous=previous, mode=mode,
                                              exceptions=[("SPLIT_SUSPECTED", "TEST_ONLY")], previous_run_missing=False)

    def shock(self, blocked):
        return {"open": False, "rg1_damage": ["F1"],
                "by_symbol": {symbol: ({"rg1_damage": ["F1"]} if symbol in blocked else {}) for symbol in ("MU", "SOXL")}}

    def test_first_change_and_repeat(self):
        alerts, states = self.alerts(self.shock({"MU"}))
        self.assertEqual(states["2:RG1DMG"], "F1|MU")
        self.assertEqual([alert["code"] for alert in alerts][-2:], ["SPLIT_SUSPECTED", "2:RG1DMG"])
        self.assertTrue(alerts[-1]["push"])
        self.assertNotIn("MU", alerts[-1]["line"])
        self.assertIn("1\uac74", alerts[-1]["line"])
        self.assertIn("1\uc885\ubaa9", alerts[-1]["line"])
        previous = {"alert_states": states, "run_day_kst": "2026-10-10"}
        repeat, states2 = self.alerts(self.shock({"MU"}), previous)
        self.assertEqual(states2["2:RG1DMG"], "F1|MU")
        self.assertFalse(any(alert["code"] == "2:RG1DMG" for alert in repeat))
        more, states3 = self.alerts(self.shock({"MU", "SOXL"}), {"alert_states": states2})
        self.assertEqual((states3["2:RG1DMG"], more[-1]["code"]), ("F1|MU,SOXL", "2:RG1DMG"))
        fewer, states4 = self.alerts(self.shock({"SOXL"}), {"alert_states": states3})
        self.assertEqual((states4["2:RG1DMG"], fewer[-1]["code"]), ("F1|SOXL", "2:RG1DMG"))

    def test_no_damage_no_state(self):
        alerts, states = self.alerts({"open": False, "by_symbol": {"MU": {}}})
        self.assertNotIn("2:RG1DMG", states)
        self.assertEqual([alert["code"] for alert in alerts], ["SPLIT_SUSPECTED"])
        same, _states = self.alerts({"open": False, "by_symbol": {"MU": {}}}, {"alert_states": states})
        self.assertEqual(same, alerts)


class RegistrySchemaTests(unittest.TestCase):
    """S10: the optional thesis_damage_domains key."""

    def test_schema(self):
        real = load_json(ROOT / "docs/claude/card-evidence-registry.json")
        self.assertEqual(real["thesis_damage_domains"], ["microsoft.com", "abc.xyz", "atmeta.com", "aboutamazon.com"])
        self.assertEqual(validate_instance(real, inputs.REGISTRY_SCHEMA), [])
        without = copy.deepcopy(real)
        del without["thesis_damage_domains"]
        self.assertEqual(validate_instance(without, inputs.REGISTRY_SCHEMA), [])
        for bad in (["Microsoft.com"], ["https://microsoft.com"], ["microsoft.com/investor"], ["localhost"],
                    ["abc.xyz", "abc.xyz"], "microsoft.com"):
            with self.subTest(bad=bad):
                document = copy.deepcopy(real)
                document["thesis_damage_domains"] = bad
                self.assertNotEqual(validate_instance(document, inputs.REGISTRY_SCHEMA), [])


# ---------------------------------------------------------------------------------------------------------------
# S13 strictness (R7): seeded synthetic inputs. BASE holds (status, open) of each case's accepted-None input,
# measured on the base commit a9ea338 rules (thesis-damage-domain facts removed there: the base input drops them).
# ---------------------------------------------------------------------------------------------------------------

def seeded_case(seed):
    rng = random.Random(seed)
    crashes = tuple(sorted(rng.sample(range(45, 99), rng.randint(0, 2))))
    dips = tuple(k for k in sorted(rng.sample(range(45, 99), rng.randint(0, 1))) if k not in crashes)
    flat_from = rng.choice([None, None, rng.randint(50, 95)])
    days = helpers.sessions("2026-03-02", N)
    facts = []
    for number in range(rng.randint(0, 2)):
        index = rng.randint(W0 - 5, N - 1)
        announced = rng.choice(["T16:05:00-04:00", "T09:00:00-04:00", "T20:05:00Z", ""])
        extra = {"damage_source": inputs.DAMAGE_DOMAIN_SOURCE} if rng.random() < 0.25 else {}
        facts.append(fact(f"S{seed}F{number}", days[index], days[index] + announced if announced else "", **extra))
    if rng.random() < 0.3:
        dips = tuple(sorted(set(dips) | {days.index(item["event_session"]) for item in facts[:1]
                                         if days.index(item["event_session"]) not in crashes}))
    coverage = rng.choice(["all", "all", "none", "gap"])
    gap = rng.randint(W0, N - 1)
    accepted = rng.choice([None, days[rng.randint(W0, N - 1)], next_day(days[rng.randint(W0, N - 1)])])
    return {"crashes": crashes, "dips": dips, "flat_from": flat_from, "facts": facts, "coverage": coverage,
            "gap": gap, "accepted": accepted}


def case_run(case, through=N - 1, *, accepted=None, base_input=False):
    series, days = world(through=through, crashes=case["crashes"], dips=case["dips"], flat_from=case["flat_from"])
    sessions = {"all": list(days), "none": None, "gap": [day for day in days if day != days[case["gap"]]]}[case["coverage"]]
    facts = [item for item in case["facts"] if not (base_input and "damage_source" in item)]
    return rules.rrec1(benchmark=series, candidate=None, evaluation_session=days[through], ev3_user_dates=[],
                       thesis_damage=facts, ev4_sessions=[], research_sessions=sessions, card_accepted_on=accepted)


SEEDS = range(60)
BASE = {0: ('no', True), 1: ('ok', False), 2: ('ok', False), 3: ('no', True), 4: ('ok', False), 5: ('unk', True),
        6: ('no', True), 7: ('ok', False), 8: ('unk', None), 9: ('ok', False), 10: ('ok', False), 11: ('unk', None),
        12: ('ok', False), 13: ('ok', False), 14: ('ok', False), 15: ('no', True), 16: ('ok', False), 17: ('no', True),
        18: ('ok', False), 19: ('no', True), 20: ('no', True), 21: ('no', True), 22: ('ok', False), 23: ('ok', False),
        24: ('no', True), 25: ('no', True), 26: ('ok', False), 27: ('ok', False), 28: ('no', True), 29: ('ok', False),
        30: ('ok', False), 31: ('ok', False), 32: ('ok', False), 33: ('ok', False), 34: ('ok', False), 35: ('ok', False),
        36: ('ok', False), 37: ('unk', True), 38: ('ok', False), 39: ('ok', False), 40: ('ok', False), 41: ('unk', None),
        42: ('ok', False), 43: ('ok', False), 44: ('ok', False), 45: ('ok', False), 46: ('no', True), 47: ('ok', False),
        48: ('ok', False), 49: ('ok', False), 50: ('ok', False), 51: ('ok', False), 52: ('ok', False), 53: ('ok', False),
        54: ('ok', False), 55: ('ok', False), 56: ('ok', False), 57: ('unk', None), 58: ('ok', False), 59: ('ok', False)}


class StrictnessTests(unittest.TestCase):
    """S13: no loosening against the base without a release; a release changes only sessions from its date on."""

    def test_never_looser_than_base(self):
        for seed in SEEDS:
            case = seeded_case(seed)
            with self.subTest(seed=seed):
                new = case_run(case)
                base_status, base_open = BASE[seed]
                if base_status != "ok":
                    self.assertNotEqual(new["status"], "ok", (case, new))
                if not case["facts"]:
                    self.assertEqual((new["status"], new["open"]), (base_status, base_open))

    def test_release_only_from_its_date(self):
        days = helpers.sessions("2026-03-02", N)
        checked = 0
        for seed in SEEDS:
            case = seeded_case(seed)
            if case["accepted"] is None:
                continue
            before = [index for index in range(W0 + 20, N) if days[index] < case["accepted"]][-3:]
            for through in before:
                if case["coverage"] == "gap" and case["gap"] > through:
                    continue
                with self.subTest(seed=seed, through=through):
                    self.assertEqual(case_run(case, through, accepted=case["accepted"]), case_run(case, through))
                    checked += 1
        self.assertGreater(checked, 20)


if __name__ == "__main__":
    unittest.main()
