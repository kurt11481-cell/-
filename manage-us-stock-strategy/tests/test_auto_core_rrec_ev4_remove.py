"""rrec-ev4-remove (user decision "rrec-ev4: REMOVE", 2026-10-19, docs/claude/rrec-ev4-remove-decision-2026-10-19.md):
R-REC1 has no account-line event EV4 any more. Account drawdown is left to the S7 review lines (L2 and below pause
new buys until a journal review), which this change does not touch.

X1 an account below the EV4 line and no other event: R-REC1 ok  X2 a benchmark event with the account below the
line too is the benchmark event alone  X3 the S7 L2 pause still blocks buy requirement (2)  X4 an old record's
account.ev4_open is not read  X5 (E1) rrec1 equals the base rrec1 called with ev4_sessions=[] on seeded inputs
X6 sessions without a record raise no EV4_UNDETERMINED. Synthetic inputs only (TEST_ONLY). No Kiwoom, no network.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_inputs as inputs  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import helpers  # noqa: E402
import test_auto_core_decide as decide_fixture  # noqa: E402
import test_auto_core_tickets as tickets_fixture  # noqa: E402
from validation_common import validate_instance, write_json  # noqa: E402

Scenario = tickets_fixture.Scenario
V6_FIRST = rules.C["V6_FIRST_LINE_USD"]
REQ5_NO_EVENT = "\ud1b5\uacfc (\uc5f4\ub9b0 \uc774\ubca4\ud2b8 \uc5c6\uc74c)"
BLOCKED = "\ub9c9\ud798"
S7_NEW_BUY_PAUSED = "S7 \uc2e0\uaddc \ub9e4\uc218 \uba48\ucda4"


def mu_row(result):
    return next(row for row in result["rows"] if row["code"] == "MU")


def req5_reasons(result):
    return [reason for item in result["planned"]["blocked"] for reason in item["reasons"]
            if reason.startswith("REQ5_RREC1")]


def event_kinds(shock):
    return sorted({kind for event in shock.get("events") or [] for kind in event["kinds"]})


# ---------------------------------------------------------------------------------------------
# X1-X3 on evaluate_session (test_auto_core_tickets.Scenario)
# ---------------------------------------------------------------------------------------------

class AccountLineTests(unittest.TestCase):
    def test_x1_account_below_the_line_without_another_event_is_ok(self):
        # The input of the removed SessionEv4Tests (SOXL 10, $5,000): on the base code its only R-REC1 event was
        # this session's EV4 (open, MU requirement (5) blocked, REQ5_RREC1).
        result = Scenario(cash="5000").run()
        self.assertLessEqual(Decimal(str(result["account"]["total"])), V6_FIRST)
        self.assertEqual((result["shock"]["status"], result["shock"]["open"], result["shock"]["events"]),
                         ("ok", False, []))
        self.assertEqual(mu_row(result)["c"][4], {"s": "ok", "t": REQ5_NO_EVENT})
        self.assertEqual(req5_reasons(result), [])
        self.assertNotIn("ev4_open", result["account"])
        self.assertNotIn("ev4_backfill", result)

    def test_x2_benchmark_event_with_the_account_below_the_line_is_the_event_alone(self):
        crash = helpers.zigzag(len(tickets_fixture.DAYS) - 1, 500, 2.0, 0.3) + [470.0]
        low = Scenario(soxx=crash, cash="5000").run()
        high = Scenario(soxx=crash).run()  # $30,000: above the V6 first line
        self.assertLessEqual(Decimal(str(low["account"]["total"])), V6_FIRST)
        self.assertGreater(Decimal(str(high["account"]["total"])), V6_FIRST)
        self.assertEqual(low["shock"]["event"]["date"], tickets_fixture.LAST)
        self.assertIn("EV2", low["shock"]["event"]["kinds"])
        self.assertNotIn("EV4", event_kinds(low["shock"]))
        self.assertEqual(low["shock"], high["shock"])  # event date, kinds, rg and status of the event alone
        self.assertEqual(low["shocks"], high["shocks"])

    def test_x3_the_s7_l2_pause_still_blocks_requirement_2(self):
        original = helpers.s7_runner

        def paused_runner(**kwargs):
            inner = original(**kwargs)

            def run(proposals):
                # portfolio_exposure: an open L2 line pauses add and new-buy recommendations (REVIEW_LINE_OPEN:L2)
                review = copy.deepcopy(inner(proposals))
                review["review_lines"]["open_events"] = [{"line_id": "L2", "pause_add_recommendations": True,
                                                          "pause_new_buy_recommendations": True}]
                for kind in ("add_recommendations", "new_buy_recommendations"):
                    review["pauses"][kind] = {"paused": True, "reasons": ["REVIEW_LINE_OPEN:L2"]}
                return review
            return run

        free = Scenario(cash="5000").run()
        self.assertNotIn(S7_NEW_BUY_PAUSED, mu_row(free)["c"][1]["t"])
        with mock.patch.object(helpers, "s7_runner", paused_runner):
            result = Scenario(cash="5000").run()
        self.assertEqual((result["shock"]["status"], result["shock"]["open"]), ("ok", False))  # R-REC1 ok
        cell = mu_row(result)["c"][1]
        self.assertEqual(cell["s"], "no")
        self.assertTrue(cell["t"].startswith(BLOCKED), cell)
        self.assertIn(S7_NEW_BUY_PAUSED, cell["t"])
        self.assertTrue(result["exposure"]["S7"]["pauses"]["new_buy"])
        self.assertEqual(tickets_fixture.tickets_of(result, "MU", "buy"), [])


# ---------------------------------------------------------------------------------------------
# X4 and X6 through decide (test_auto_core_decide.Env, temporary folders)
# ---------------------------------------------------------------------------------------------

DAYS = decide_fixture.DAYS
S1, S2, S3 = DAYS[-4], DAYS[-3], DAYS[-2]  # the three sessions before today's evaluation session


def run_day_of(session):
    """The KST run day whose decide evaluates `session` (the day after it)."""
    return (date.fromisoformat(session) + timedelta(days=1)).isoformat()


class DecideRecordTests(unittest.TestCase):
    def setUp(self):
        self.env = decide_fixture.Env()
        self.addCleanup(self.env.close)
        self.base = self.env.run()  # a real record to copy (today's file is written again by each run)

    def record(self, session, **changes):
        """A previous decision.json of the run day that evaluates `session`."""
        item = decide_fixture._as_of(copy.deepcopy(self.base), run_day_of(session))
        self.assertEqual(item["evaluation_session"], session)
        item.update(changes)
        folder = self.env.output / run_day_of(session)
        folder.mkdir(exist_ok=True)
        write_json(folder / decide_module.DECISION_FILE, item)
        return item

    def assert_no_ev4(self, decision):
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        self.assertNotIn("ev4_backfill", decision)
        self.assertNotIn("ev4_open", decision["account"])
        self.assertNotIn("EV4", event_kinds(decision["shock"]))
        self.assertEqual([alert for alert in decision["alerts"]
                          if alert["code"] == "EV4_UNDETERMINED" or "EV4" in alert["line"]], [])

    def test_x4_an_old_record_with_ev4_open_makes_no_event(self):
        # On the base code S2 (and S3, judged from S2's total) became EV4 sessions and R-REC1 opened.
        self.record(S2, account=dict(self.base["account"], total=20000.0, ev4_open=True))
        decision = self.env.run()
        self.assert_no_ev4(decision)
        self.assertEqual(decision["shock"], self.base["shock"])
        self.assertEqual(decision["shock"]["open"], False)

    def test_x6_sessions_without_a_record_raise_no_ev4_exception(self):
        # The first record (S1) ended before F1 (no account); S2 and S3 have none. On the base code every one of
        # them was an EV4_UNDETERMINED session: NEIGHBOR_CLEAR beside today's total, NEIGHBOR_NONE without it.
        self.record(S1, status="FAIL", reasons=["UNEXPECTED_ERROR:TEST_ONLY"], account={}, f6_ran=False, tickets=[])
        for case in ("neighbor_total", "no_known_total"):
            with self.subTest(case=case):
                if case == "no_known_total":  # today's total unknown: no cash in the broker snapshot
                    write_json(self.env.day_dir / decide_module.SNAPSHOT_FILE, {
                        "holdings": [{"ticker": "SOXL", "held_quantity": 40}], "cash": {}})
                decision = self.env.run()
                self.assert_no_ev4(decision)
                self.assertEqual(decision["shock"], self.base["shock"])


# ---------------------------------------------------------------------------------------------
# X5 (E1): rrec1 on seeded synthetic inputs equals the base rrec1 called with ev4_sessions=[].
# E1_EXPECTED[seed] = the first 16 hex digits of sha256(e1_dump(base result)); E1_EXPECTED_ALL = sha256 of the
# seeds' dumps joined with "\n". Measured on the base code (main 80d3a1d) by loading this file over the base
# modules and calling the base rules.rrec1(**e1_inputs(seed), ev4_sessions=[]) - the script is in
# docs/claude/rrec-ev4-remove-report.md 2.
# ---------------------------------------------------------------------------------------------

E1_SEEDS = range(320)
E1_N = 100


def e1_dump(result):
    return json.dumps(result, ensure_ascii=True, default=str)  # key order kept: the dict must match as written


def e1_fact(fact_id, day, rng):
    announced = rng.choice(["T16:05:00-04:00", "T09:00:00-04:00", "T20:05:00Z", ""])
    value = {"fact_id": fact_id, "event_session": day, "root_thesis_damage": True,
             "announced_at": day + announced if announced else ""}
    if rng.random() < 0.25:
        value["damage_source"] = inputs.DAMAGE_DOMAIN_SOURCE  # a thesis-damage-domain fact: RG1 only
    return value


def e1_inputs(seed):
    """rrec1 keyword arguments: EV1 crashes, an EV2 slide, -1.2% dips (EV3 (b) with a fact on the day), EV3 (a)
    dates, the candidate's own -10% days (EV5), a flat run below EMA50 (DS1, RG2 no), a new low after the event
    (RG3 no), damage facts with or without the domain marker, card acceptance dates, research sessions None / all /
    one missing / from a later start, rg2_series default / None / a GRID series, earlier evaluation sessions."""
    rng = random.Random(seed)
    days = helpers.sessions("2026-03-02", E1_N)
    closes = helpers.zigzag(E1_N, 500, rng.choice([1.0, 2.0, 3.0]), rng.choice([-0.3, 0.0, 0.3]))
    crashes = sorted(rng.sample(range(42, E1_N), rng.randint(0, 2)))
    for k in crashes:
        closes[k] = round(closes[k - 1] * rng.choice([0.95, 0.9]), 4)
    if rng.random() < 0.3:
        start = rng.randint(45, E1_N - 8)
        for k in range(start, start + 7):
            closes[k] = round(closes[k - 1] * 0.993, 4)
    dips = sorted(rng.sample(range(42, E1_N), rng.randint(0, 2)))
    for k in dips:
        closes[k] = round(closes[k - 1] * 0.988, 4)
    if rng.random() < 0.3:
        level = closes[rng.randint(40, 60)]
        for k in range(rng.randint(60, E1_N - 3), E1_N):
            closes[k] = round(level + (1.5 if k % 2 else -1.5), 4)
    lows = None
    if crashes and rng.random() < 0.4:
        lows = [round(value * 0.99, 4) for value in closes]
        after = min(crashes[-1] + rng.randint(1, 4), E1_N - 1)
        lows[after] = round(closes[crashes[-1]] * 0.95, 4)
    through = rng.choice([E1_N - 1, E1_N - 1, rng.randint(80, E1_N - 2)])
    day = days[through]
    window = days[max(0, through - 59):through + 1]
    candidate = None
    if rng.random() < 0.6:
        own = helpers.zigzag(E1_N, 200, 3.0, 0.2)
        for k in sorted(rng.sample(range(42, E1_N), rng.randint(0, 2))):
            own[k] = round(own[k - 1] * 0.9, 4)
        candidate = rules.build_series(helpers.bars("X", days, own)["adjusted"], days, day)
    facts = None if rng.random() < 0.15 else []
    if facts is not None:
        dip_days = [days[k] for k in dips if k <= through]
        for number in range(rng.randint(0, 2)):
            on = rng.choice(dip_days) if dip_days and rng.random() < 0.5 else rng.choice(window)
            facts.append(e1_fact(f"E{seed}F{number}", on, rng))
    arguments = {"benchmark": rules.build_series(helpers.bars("SOXX", days, closes, lows=lows)["adjusted"], days, day),
                 "candidate": candidate, "evaluation_session": day,
                 "ev3_user_dates": [rng.choice(window)] if rng.random() < 0.3 else [],
                 "thesis_damage": facts, "candidate_symbol": "X" if candidate is not None else None}
    coverage = rng.choice(["none", "all", "all", "gap", "late"])
    if coverage == "all":
        arguments["research_sessions"] = list(days[:through + 1])
    elif coverage == "gap":
        missing = rng.choice(window)
        arguments["research_sessions"] = [item for item in days[:through + 1] if item != missing]
    elif coverage == "late":
        arguments["research_sessions"] = list(days[rng.randint(through - 50, through):through + 1])
    leg = rng.choice(["default", "default", "none", "grid"])
    if leg == "none":
        arguments["rg2_series"] = None
    elif leg == "grid":
        grid = helpers.zigzag(E1_N, 150, 1.0, rng.choice([-0.2, 0.1]))
        arguments["rg2_series"] = rules.build_series(helpers.bars("GRID", days, grid)["adjusted"], days, day)
    if rng.random() < 0.5:
        accepted = rng.choice(window)
        arguments["card_accepted_on"] = accepted if rng.random() < 0.5 else run_day_of(accepted)
    return arguments


E1_EXPECTED = (
    "8ed5e917ee6db29d", "1e7bd1bbefe216d6", "10910ff395b4db18", "5f421a8b082c827e", "f9142cb9ed3573f9", "840bb56ad50946c7",
    "97a1c85612569998", "eaff6bd3ff288da7", "a6775ebc72258c9a", "9657756e02b44086", "f91524e09a4a9cbd", "1c14c0bf00e485a1",
    "017f02e50f679990", "f1090a500ff18e8b", "0a34dd955c27a302", "6cd7110ce2e5976b", "cff1f866f2d2e3ae", "4365af690b200737",
    "37dc29acfa7cca98", "f9142cb9ed3573f9", "9e9fb55d93f74b44", "67b2561bcee83b86", "a921cf6975442953", "9d7a33ad9e06e7d1",
    "6f71bffd6ce09d39", "f9142cb9ed3573f9", "88ffe8274ca9c50d", "a7d17bc01d89d9bd", "1cae69e3e540ffa6", "6bda00289501bc32",
    "a93d555ab17c7c76", "8fe535ed8cf27e07", "d6be565353dfe81d", "4d5db8c89d7ad1e6", "8ccc43c8973e97ee", "393c9b12565e02bb",
    "38e2cabf5d411050", "82c4f221d82e0d08", "9f6d210a6128619b", "63044eb09e7571e3", "58a2d3cf8da6bff6", "ad2c7f0f21dad8cf",
    "c2fd58fd6d6ab190", "6942729072d5ecaa", "dc0699a43232ca9b", "276d2634dff2cd2d", "6f71bffd6ce09d39", "6dac551b8f0ad93c",
    "caf31c87a891ec7d", "b3c141dcb7fed971", "5cbd4ba308c49acb", "58eb9f76f6889810", "23f7b407c3418551", "344a8f1803ec786c",
    "7c8ddd5d3c8ce581", "deb5b7e69baf24fd", "1f62bdc79209856e", "6d0e806758193710", "a4a3bddfabfde757", "88a6ff526828294d",
    "ffa8ec0206911636", "b3acd65ef27345ff", "a072bc5677f8662b", "f9142cb9ed3573f9", "5ea28f8cbf515ad4", "5e8a68636761537b",
    "7c77afa3410cb0f5", "86ecb415785f982a", "4786d310e9400884", "f1be30a3ebe99716", "fb4cbb25378c2817", "a186c8fd960672a9",
    "675c55a1832431cb", "20c031304c92f20a", "204d3187e9583cae", "8292852a65a547e4", "6320595618bd20b7", "37465f773b92156d",
    "a4b288082764b028", "e93c2bd18785ed90", "c46ee4bae1af9aec", "a2bba21ac08b51ad", "0bcfb8e20378b121", "f9142cb9ed3573f9",
    "7c2a436058b6e0ca", "d2ad797120fdf140", "caa393f0dd52b29d", "8f0f466486d82377", "50753bee5779645b", "829ee097e96f0707",
    "decab0f9c472b935", "82d50c8ca8fde262", "93b0fba376804a60", "56dc9672b3ddbca9", "6e6098f47d9e32bf", "ec917fc97cca4bba",
    "5fd62c67d18649ec", "40131f6abc5170e9", "ddcd86c1d216dc82", "e6bc8d7092a56716", "506975d19e3b370a", "45e8f62bf078f239",
    "e85802255d0eb92b", "022bda8035b33f4f", "359266f5570fc327", "49e693d5d36c195d", "773a0fa5e6599532", "b8c3bc1a1a15ce58",
    "41ce0462574c19e1", "770e2b40e0c0d8d2", "6f71bffd6ce09d39", "d30ab9a5a495686c", "5db5a7659c413887", "5399b2ca15c81a6d",
    "ab68b8649668fe28", "9ce35051529b0d2d", "435dff5576a0735f", "59c538fb30772650", "2757bb2b771604f3", "f80edfa4a67bdba8",
    "f35fb6e80f3dcabb", "10c527980b55c828", "0393e95433fee83f", "29abf98c2d632164", "017cf0ede89ce333", "0537e5d43dc012fb",
    "db06afea6fc449cf", "5f2f2d9fe6f11256", "6c29e5d4c210557b", "b4baa878bce0b8a4", "6efecb30dfb2c9fe", "6ed16d7bd9dd5553",
    "f9142cb9ed3573f9", "d3b1f890b7299c8b", "10a529a24e1026f2", "04fdbf1a7e258558", "7bbeeb62f1ff7f2d", "a7e7a353db769b19",
    "2f3866e718664785", "b6ed305adaa9bd54", "f9142cb9ed3573f9", "1296524a65e72109", "a539c1cdcb324860", "be08da450f93645a",
    "f9142cb9ed3573f9", "41ac012e64a2474e", "5d69c47b7f57db4a", "aacafc5211958442", "58c456f6eb935ddc", "fa5afc9514a8fb5d",
    "7cbe3b68911140dc", "8acbe8cb2a1ce3c9", "d1fc31471065fa0f", "a25f7718b285e607", "dc91e80827449a1b", "e4045d1339bc85e7",
    "86b929ad199fc791", "f9142cb9ed3573f9", "62ce9b5b416cb83a", "c4ee1a70e102e736", "a682f25b75b409c1", "d47b8f7967943413",
    "6d5f553ba5ba7ddc", "4ffccd588b10bb01", "1ae944686766c402", "b03cf74de5b7bf8c", "fcdcab6df87c34fe", "b5509b08809d2cdb",
    "79ab42090e981a8e", "aac524f17b64f297", "fa9da096b31668e0", "0fb2c3e3d124ae3a", "35e5fee7f78a280e", "f5593666ace7a9b8",
    "39df033bce8d4a2c", "76bd30f8d72658f0", "5158662045d8b115", "aa276e53f49fc766", "cab44f5725cc05c5", "6984d7cb0589b3f5",
    "6379888fee29f4fb", "b3b78414b89e126b", "169d5906dee421ad", "818fc8d1d7615098", "0f4bac9e4e475d50", "de67ae8bf358e7db",
    "e983f597a43aca2d", "856a8c93d597732e", "b8fd9a25fbb8edd2", "fc8643dcf39fb877", "0ec26702531da68d", "839a4f17f1e517fb",
    "40894fd764116d20", "8c0235c36c9ff9f8", "d3d2eab553c646cf", "fe67bddee747a22d", "021f32cea56af343", "84149b99f588d14c",
    "4d85e0ca1d6cbf1f", "e9ffb16915bb02b2", "f9142cb9ed3573f9", "85358d759342e073", "844653386c900983", "1207ad3851b6b76b",
    "5f973352f1afa78b", "02f24a8bae3f9ef7", "ed8a58d2b37d6d8f", "2cf7a50a578dda4a", "c7467890b402b4eb", "416f080b656fc2d9",
    "2f502fb520a15c57", "2f15b4a498adc661", "84c19fa44253495c", "91e079b071acdc1f", "13f5a6f105c20eba", "1340cfe7cfbfef03",
    "cb25df45f8dd805e", "8aaa535172ded49f", "7aed7999d9dde04c", "2250acfb659aad7e", "906bd7bd28fb94fa", "8b5bc118d11e67a9",
    "72e0bb266b9b3f7d", "f5d333cd869ac5bd", "2b60a1bc1c4d7839", "7ac4b3920cfafe5b", "85980b58e69487d8", "7d57b39a0e5db458",
    "f9142cb9ed3573f9", "cb5821dc178ec3df", "1fa715aa9460944e", "d59a62a761bf1d65", "6f71bffd6ce09d39", "ffa8ec0206911636",
    "9751d27df38a124b", "0585b57cf339b18c", "2466fb7ed64a9df9", "26ef9784e730cce7", "9e0190bc9a75cf4b", "a7b0e4d0fe5c9181",
    "4815e9cf9a9efe69", "6f71bffd6ce09d39", "a15e790736499a7d", "0e31d05e00961cec", "2e07d37784a7dc21", "35a1420e84adac2f",
    "6d3b319544a61993", "d181fec5177e386c", "5c55550b42bafdc0", "c3744510213eb363", "5066e62ae12f90ad", "5e8c7dbee4a562da",
    "ad4a08ced41a0913", "4d95aff39a8fc750", "0e5834e75977118d", "3518f484b3f29a4c", "aa47b48adcab7f8c", "3c3728356e397fc3",
    "537fe2c29622dafc", "f977f4ea21e526df", "db0e98789603f53f", "2e5e3a34b174890d", "89814dcb9d5cd3da", "c21c387b8e5d9619",
    "52f0a7694d1c3738", "78ba504713d6d096", "1be73d80a6c29f6e", "5b4fe0fcf8ada8bc", "12c66369b4807ae6", "f1ab86d637596577",
    "5b085b0787dc0077", "e8d73645f2e84ba8", "e7312a885fb5978c", "cd6bfbba577e16d6", "3fcf7506596f7c31", "0fc1a58113e09a55",
    "b762ddbb744f77cc", "7e1673e144c16e79", "7e3472e520dafca1", "e660cfcba6398218", "a581f14df28e5d35", "c8319728c6bb9f66",
    "043ab7481b3bf7a3", "d915ec7698250e5f", "dc1ef58428dab702", "b5aa764a886dc2b6", "279b6d21c5108372", "d08a0f16cdd8af9a",
    "92d124a6bcb9c646", "e1b644e43996eb96", "2bb5c252a91cda4c", "7c1ac05a3622c1f6", "c1e26ffa56c21f31", "c2d374554dbc8190",
    "9a69446b57a603a4", "b5e4ceffc011ef78", "000816f1e81e2729", "c661be118a109049", "460dce8c8349f3e6", "0ad370192889ae93",
    "c1b2e52d35ec9f04", "4283a507ffe550a1", "d5ee6fbd89b1de44", "e4bedba5e5fe4a06", "571bcc7a5461a3c9", "d1b2053b5adeb811",
    "7cc7326ab5a4b67d", "36916cbd700784cb", "0d4c420a435682cd", "dbfc9fbc0a24401c", "e7c8251ea68fff1e", "8dd871ff0045293a",
    "8241f4b987d410d2", "3593d2505dc36f75", "61dac451f61fdeaf", "cdd0ef74e3843f3f", "807136e053f48be0", "92a2fe01ca8e5ffd",
    "f181570bd83affda", "def3b4a1e0dfcbfa",
)
E1_EXPECTED_ALL = "129a009c822ec2598c50b83a1ccc2896c1a6d647947cf17e1396717ffc27abc3"


class CoreEquivalenceTests(unittest.TestCase):
    def test_x5_rrec1_equals_the_base_called_without_ev4_sessions(self):
        dumps, kinds, statuses, gates = [], set(), set(), set()
        for seed in E1_SEEDS:
            result = rules.rrec1(**e1_inputs(seed))
            dump = e1_dump(result)
            with self.subTest(seed=seed):
                self.assertEqual(hashlib.sha256(dump.encode()).hexdigest()[:16], E1_EXPECTED[seed])
            dumps.append(dump)
            kinds |= set(event_kinds(result))
            statuses.add(result["status"])
            gates |= {f"{key}:{value}" for key, value in (result.get("rg") or {}).items()}
            gates |= {"DS1"} if result.get("ds1") else set()
            gates |= {"DAMAGE"} if result.get("rg1_damage") else set()
            gates |= {"GAP"} if any(reason.startswith("EV3B_RECORD_GAP") for reason in result["reasons"]) else set()
            gates |= {"CLOSED"} if result.get("closed_at") else set()
            gates |= {"NO_EVENT"} if not result["events"] else set()
        self.assertEqual(hashlib.sha256("\n".join(dumps).encode()).hexdigest(), E1_EXPECTED_ALL)
        # The seeded inputs reach every event kind, status and gate state the change could touch.
        self.assertEqual(kinds, {"EV1", "EV2", "EV3a", "EV3b", "EV5"})
        self.assertEqual(statuses, {"ok", "no", "unk"})
        self.assertLessEqual({"RG1:no", "RG1:unk", "RG2:no", "RG3:no", "RG4:no", "RG1:ok", "RG2:ok", "RG3:ok",
                              "RG4:ok", "DS1", "DAMAGE", "GAP", "CLOSED", "NO_EVENT"}, gates)


if __name__ == "__main__":
    unittest.main()
