"""Card decisions in the decision journal: proposals, confirmed append, compatibility, and the read-only scorer.

Synthetic inputs and temp folders only. The real journal, state and policy files are never touched.
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import continuous_improvement_sidecar as sidecar  # noqa: E402
import portfolio_review_journal as journal_module  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
import score_decision_journal as scorer  # noqa: E402
from test_holding_card import bind, make_card, make_position  # noqa: E402
from test_portfolio_exposure import Scenario  # noqa: E402
from test_portfolio_review_journal import not_activated_review  # noqa: E402
from validate_holding_card import forbidden_keys  # noqa: E402
from validation_common import canonical_hash, validate_instance  # noqa: E402

NOW = datetime.now(timezone.utc)
CARD_SESSION = "2026-09-29"


def confirmation(proposal: dict, *, code: str | None = None, method: str = "COWORK_CHAT_USER_MESSAGE") -> dict:
    code = proposal["confirm_code"] if code is None else code
    return {"confirm_code": code, "confirmation_method": method, "user_message": f"확인 {code}"}


class JournalCardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="journal_cards_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "decision_journal.json"

    def journal(self) -> dict:
        return journal_module.load_journal(self.path)

    def card_proposal(self, card: dict | None = None, pack: dict | None = None) -> dict:
        card, pack = (card, pack) if card is not None else make_card()
        return journal_module.build_card_proposal(card=card, fact_pack=pack, journal=self.journal(), now=NOW)

    def record_card(self, card: dict | None = None, pack: dict | None = None) -> list[dict]:
        proposal = self.card_proposal(card, pack)
        return journal_module.apply_proposal_entries(journal_path=self.path, proposal=proposal,
                                                     confirmation=confirmation(proposal))

    def activate(self) -> dict:
        review = not_activated_review()
        proposal = journal_module.build_proposal(
            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
            journal=self.journal(), now=NOW)
        return journal_module.apply_proposal(journal_path=self.path, proposal=proposal,
                                             confirmation=confirmation(proposal))


class CardProposalTests(JournalCardTestCase):
    def test_proposal_records_one_decision_per_position_and_writes_nothing(self) -> None:
        card, pack = make_card()
        proposal = self.card_proposal(card, pack)
        self.assertEqual(validate_instance(proposal, journal_module.PROPOSAL_SCHEMA), [])
        self.assertFalse(self.path.exists())
        decisions = proposal["payload"]["decisions"]
        self.assertEqual([item["ticker"] for item in decisions], ["AAA", "BBB"])
        by_ticker = {item["ticker"]: item for item in decisions}
        self.assertEqual((by_ticker["AAA"]["analysis_action"], by_ticker["AAA"]["sidecar_action"]),
                         ("TRIM", "TRIM_CONCENTRATION"))
        self.assertEqual((by_ticker["BBB"]["analysis_action"], by_ticker["BBB"]["sidecar_action"]),
                         ("HOLD", "HOLD_CORE"))
        self.assertEqual(by_ticker["AAA"]["reference_close"], "8")
        self.assertEqual((by_ticker["AAA"]["decision_session"], by_ticker["AAA"]["card_state_revision"],
                          by_ticker["AAA"]["evidence_grade"]), (CARD_SESSION, 16, "UNVERIFIED"))
        self.assertEqual(proposal["review_id"], canonical_hash(card))
        self.assertEqual((proposal["auto_apply"], proposal["order_authority"], proposal["quantity_authority"]),
                         (False, False, "none"))
        self.assertEqual(forbidden_keys(proposal), [])  # no quantity, price target or order field anywhere

    def test_review_required_hold_and_trim_exit_tags_map_to_sidecar_names(self) -> None:
        _, pack = make_card()
        positions = [make_position(pack, "AAA", "EXIT", reason_tag="KEEP_CASH"),
                     make_position(pack, "BBB", "HOLD", review_required=True)]
        card, pack = make_card(pack, positions)
        decisions = {item["ticker"]: item for item in self.card_proposal(card, pack)["payload"]["decisions"]}
        self.assertEqual(decisions["AAA"]["sidecar_action"], "KEEP_CASH")
        self.assertEqual(decisions["BBB"]["sidecar_action"], "HOLD_REVIEW_REQUIRED")

    def test_allowed_sidecar_names_are_exactly_the_sidecar_decision_actions(self) -> None:
        allowed = {name for names in journal_module.ALLOWED_SIDECAR_ACTIONS.values() for name in names}
        self.assertEqual(allowed, sidecar.DECISION_ACTIONS - {"HOLD_TIGHTEN_STOP"})
        schema = json.loads((SKILL_ROOT / "schemas/portfolio-review-journal-payload.schema.json").read_text(
            encoding="utf-8"))
        self.assertEqual(set(schema["properties"]["sidecar_action"]["enum"]), sidecar.DECISION_ACTIONS)

    def test_a_card_that_fails_the_validator_is_never_proposed(self) -> None:
        card, pack = make_card()
        broken = copy.deepcopy(card)
        broken["fact_pack_sha256"] = "0" * 64
        with self.assertRaisesRegex(journal_module.JournalError, "CARD_INVALID"):
            self.card_proposal(broken, pack)
        ordered = copy.deepcopy(card)
        ordered["positions"][0]["proposed_quantity"] = 5
        with self.assertRaisesRegex(journal_module.JournalError, "CARD_INVALID.*ORDER_FIELD_FORBIDDEN"):
            self.card_proposal(ordered, pack)

    def test_withheld_positions_are_not_recorded(self) -> None:
        _, pack = make_card()
        pack["tickers"]["BBB"]["withhold_allowed"]["BROKER_UNAVAILABLE"] = True
        positions = [make_position(pack, "AAA"), make_position(pack, "BBB", "WITHHELD",
                                                               withheld_reason="BROKER_UNAVAILABLE")]
        for key in ("review_required", "reason_tag"):
            positions[1].pop(key, None)
        card, pack = make_card(pack, positions)
        payloads, withheld, _ = journal_module.card_decision_payloads(card, pack)
        self.assertEqual(([item["ticker"] for item in payloads], withheld), (["AAA"], ["BBB"]))
        only_withheld = make_card(pack, [positions[1], make_position(pack, "AAA", "WITHHELD",
                                                                     withheld_reason="BROKER_UNAVAILABLE")])
        only_withheld[1]["tickers"]["AAA"]["withhold_allowed"]["BROKER_UNAVAILABLE"] = True
        card2, pack2 = make_card(only_withheld[1], only_withheld[0]["positions"])
        for position in card2["positions"]:
            position.pop("review_required", None)
            position.pop("reason_tag", None)
        card2 = bind(card2, pack2)
        with self.assertRaisesRegex(journal_module.JournalError, "CARD_HAS_NO_RECORDABLE_POSITION"):
            journal_module.card_decision_payloads(card2, pack2)


class CardApplyTests(JournalCardTestCase):
    def test_apply_needs_the_code_and_appends_all_entries_in_one_chain(self) -> None:
        proposal = self.card_proposal()
        rejected = {
            "CONFIRM_CODE_MISMATCH": confirmation(proposal, code="00000000"),
            "CONFIRM_CODE_REQUIRED": confirmation(proposal, code=" "),
            "CONFIRMATION_METHOD_INVALID": confirmation(proposal, method="SCHEDULED_TASK"),
            "USER_CONFIRMATION_MESSAGE_REQUIRED": dict(confirmation(proposal), user_message="확인"),
        }
        for reason, attempt in rejected.items():
            with self.subTest(reason=reason), self.assertRaisesRegex(journal_module.JournalError, reason):
                journal_module.apply_proposal_entries(journal_path=self.path, proposal=proposal, confirmation=attempt)
        self.assertFalse(self.path.exists())
        entries = journal_module.apply_proposal_entries(journal_path=self.path, proposal=proposal,
                                                        confirmation=confirmation(proposal))
        self.assertEqual([(entry["sequence"], entry["payload"]["ticker"]) for entry in entries],
                         [(1, "AAA"), (2, "BBB")])
        self.assertEqual(entries[1]["previous_entry_sha256"], canonical_hash(entries[0]))
        self.assertEqual([entry["entry_id"] for entry in entries], [entry["payload"]["decision_id"] for entry in entries])
        self.assertTrue(all(entry["review_id"] == proposal["review_id"] for entry in entries))
        loaded = self.journal()
        self.assertEqual((loaded["status"], len(loaded["entries"]), loaded["head_sha256"]),
                         ("OK", 2, canonical_hash(entries[-1])))
        self.assertEqual(validate_instance(json.loads(self.path.read_text(encoding="utf-8")),
                                           journal_module.JOURNAL_SCHEMA), [])

    def test_the_same_card_cannot_be_recorded_twice(self) -> None:
        card, pack = make_card()
        proposal = self.card_proposal(card, pack)
        self.record_card(card, pack)
        with self.assertRaisesRegex(journal_module.JournalError, "CARD_ALREADY_RECORDED"):
            self.card_proposal(card, pack)
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CHANGED_SINCE_PROPOSAL"):
            journal_module.apply_proposal_entries(journal_path=self.path, proposal=proposal,
                                                  confirmation=confirmation(proposal))

    def test_a_rehashed_but_inconsistent_proposal_is_rejected(self) -> None:
        proposal = self.card_proposal()

        def rehash(document: dict) -> dict:
            document["proposal_id"] = journal_module.proposal_content_hash(document)
            document["confirm_code"] = document["proposal_id"][:8].upper()
            return document

        cases = {}
        wrong_sidecar = copy.deepcopy(proposal)
        wrong_sidecar["payload"]["decisions"][0]["sidecar_action"] = "ADD_REVIEW"  # a TRIM scored as ADD
        cases["sidecar"] = rehash(wrong_sidecar)
        forged_id = copy.deepcopy(proposal)
        forged_id["payload"]["decisions"][0]["decision_id"] = "1" * 64
        cases["decision_id"] = rehash(forged_id)
        duplicate = copy.deepcopy(proposal)
        duplicate["payload"]["decisions"][1] = copy.deepcopy(duplicate["payload"]["decisions"][0])
        cases["duplicate_ticker"] = rehash(duplicate)
        other_session = copy.deepcopy(proposal)
        other_session["payload"]["decisions"][0]["decision_session"] = "2026-09-28"
        cases["session"] = rehash(other_session)
        for name, tampered in cases.items():
            with self.subTest(case=name), self.assertRaisesRegex(journal_module.JournalError,
                                                                 "CARD_PAYLOAD_INCONSISTENT"):
                journal_module.apply_proposal_entries(journal_path=self.path, proposal=tampered,
                                                      confirmation=confirmation(tampered))
        extra_field = copy.deepcopy(proposal)
        extra_field["payload"]["decisions"][0]["proposed_quantity"] = 5
        extra_field = rehash(extra_field)
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_PAYLOAD_FIELDS_INVALID"):
            journal_module.apply_proposal_entries(journal_path=self.path, proposal=extra_field,
                                                  confirmation=confirmation(extra_field))
        self.assertFalse(self.path.exists())

    def test_user_decision_is_linked_by_id_and_a_correction_is_a_new_entry(self) -> None:
        entries = self.record_card()
        decision_id = entries[0]["payload"]["decision_id"]
        for bad_id, reason in (("abc", "DECISION_ID_TOO_SHORT"), ("f" * 12, "DECISION_NOT_FOUND")):
            with self.subTest(bad_id=bad_id), self.assertRaisesRegex(journal_module.JournalError, reason):
                journal_module.build_user_decision_proposal(journal=self.journal(), decision_id=bad_id,
                                                            user_action="TRIM", effective_session=None, note="", now=NOW)
        with self.assertRaisesRegex(journal_module.JournalError, "EFFECTIVE_SESSION_BEFORE_DECISION"):
            journal_module.build_user_decision_proposal(journal=self.journal(), decision_id=decision_id[:8],
                                                        user_action="TRIM", effective_session="2026-09-28",
                                                        note="", now=NOW)
        with self.assertRaisesRegex(journal_module.JournalError, "USER_ACTION_INVALID"):
            journal_module.build_user_decision_proposal(journal=self.journal(), decision_id=decision_id[:8],
                                                        user_action="SELL", effective_session=None, note="", now=NOW)
        written = []
        for action in ("HOLD", "TRIM"):
            proposal = journal_module.build_user_decision_proposal(
                journal=self.journal(), decision_id=decision_id[:8], user_action=action, effective_session="2026-09-30",
                note=f"user chose {action}", now=NOW)
            self.assertEqual(validate_instance(proposal, journal_module.PROPOSAL_SCHEMA), [])
            written.append(journal_module.apply_proposal(journal_path=self.path, proposal=proposal,
                                                         confirmation=confirmation(proposal)))
        loaded = self.journal()
        self.assertEqual([entry["entry_type"] for entry in loaded["entries"]],
                         ["card_decision", "card_decision", "card_user_decision", "card_user_decision"])
        self.assertEqual((written[0]["review_id"], written[0]["evaluation_session"]),
                         (entries[0]["review_id"], "2026-09-30"))
        self.assertEqual(loaded["status"], "OK")  # the first user decision stays in the chain after the correction

    def test_tampering_with_a_card_entry_breaks_the_chain(self) -> None:
        self.record_card()
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["entries"][0]["payload"]["analysis_action"] = "HOLD"
        self.path.write_text(json.dumps(document), encoding="utf-8")
        loaded = self.journal()
        self.assertEqual((loaded["status"], loaded["errors"]), ("CORRUPT", ["JOURNAL_CHAIN_BROKEN:2"]))
        card, pack = make_card()
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CORRUPT"):
            self.card_proposal(card, pack)

    def test_cli_propose_card_show_apply_user_decision_and_verify(self) -> None:
        card, pack = make_card()
        card_path, pack_path = self.tmp / "card.json", self.tmp / "fact-pack.json"
        card_path.write_text(json.dumps(card), encoding="utf-8")
        pack_path.write_text(json.dumps(pack), encoding="utf-8")
        output_root = self.tmp / "proposals"

        def run(*argv: str) -> tuple[int, str]:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = journal_module.main(list(argv))
            return code, buffer.getvalue()

        code, output = run("propose-card", "--card", str(card_path), "--fact-pack", str(pack_path),
                           "--journal", str(self.path), "--output-root", str(output_root))
        self.assertEqual(code, 0)
        self.assertIn("AAA", output)
        proposal_path = next(output_root.glob("*/journal_proposal.json"))
        code_text = json.loads(proposal_path.read_text(encoding="utf-8"))["confirm_code"]
        self.assertIn(code_text, run("show", "--proposal", str(proposal_path))[1])
        self.assertEqual(run("apply", "--proposal", str(proposal_path), "--confirm", code_text, "--confirmed-via",
                             "COWORK_CHAT_USER_MESSAGE", "--journal", str(self.path))[0], 2)  # needs the user message
        self.assertFalse(self.path.exists())
        code, output = run("apply", "--proposal", str(proposal_path), "--confirm", code_text, "--confirmed-via",
                           "COWORK_CHAT_USER_MESSAGE", "--user-message", f"확인 {code_text}", "--journal", str(self.path))
        self.assertEqual(code, 0)
        self.assertIn("1~2번 2건", output)
        self.assertEqual(run("propose-card", "--card", str(card_path), "--fact-pack", str(pack_path),
                             "--journal", str(self.path), "--output-root", str(output_root))[0], 2)
        decision_id = self.journal()["entries"][0]["payload"]["decision_id"]
        code, output = run("propose-user-decision", "--decision-id", decision_id[:10], "--user-action", "TRIM",
                           "--journal", str(self.path), "--output-root", str(output_root))
        self.assertEqual(code, 0)
        newest = sorted(output_root.glob("*/journal_proposal.json"), key=lambda item: item.stat().st_mtime)[-1]
        user_code = json.loads(newest.read_text(encoding="utf-8"))["confirm_code"]
        # hnd-check: no console here; the terminal check passes (tested in test_approval_human_check.py).
        with mock.patch.object(journal_module, "user_terminal_rejection", return_value=None):
            self.assertEqual(run("apply", "--proposal", str(newest), "--confirm", user_code, "--confirmed-via",
                                 "USER_TERMINAL", "--journal", str(self.path))[0], 0)
        code, output = run("verify", "--journal", str(self.path))
        self.assertEqual((code, json.loads(output)["status"], json.loads(output)["entry_count"]), (0, "OK", 3))


class CompatibilityTests(JournalCardTestCase):
    def test_existing_s5_activation_chain_survives_the_enum_growth_and_later_card_entries(self) -> None:
        activation = self.activate()
        before = self.journal()
        self.assertEqual((before["status"], before["head_sha256"]), ("OK", canonical_hash(activation)))
        entries = self.record_card()
        after = self.journal()
        self.assertEqual((after["status"], len(after["entries"])), ("OK", 3))
        self.assertEqual(after["entries"][0], activation)  # the old entry is byte-for-byte what it was
        self.assertEqual(entries[0]["previous_entry_sha256"], canonical_hash(activation))
        self.assertEqual(validate_instance(json.loads(self.path.read_text(encoding="utf-8")),
                                           journal_module.JOURNAL_SCHEMA), [])

    def test_s5_exposure_review_and_s7_activation_reading_ignore_card_entries(self) -> None:
        self.activate()
        scenario = Scenario({"SOXL": 50}, "5000")
        scenario.journal = self.journal()
        review_before = scenario.review()
        self.assertIsNotNone(review_before["activation"])  # the real s5_activation entry is honoured
        self.record_card()
        proposal = journal_module.build_user_decision_proposal(
            journal=self.journal(), decision_id=self.journal()["entries"][1]["payload"]["decision_id"],
            user_action="HOLD", effective_session=None, note="", now=NOW)
        journal_module.apply_proposal(journal_path=self.path, proposal=proposal, confirmation=confirmation(proposal))
        scenario.journal = self.journal()
        self.assertEqual(len(scenario.journal["entries"]), 4)
        review_after = scenario.review()
        for key in ("activation", "review_lines", "pauses", "peak_reviews", "fail_closed", "recommendations"):
            if key in review_before:
                self.assertEqual(review_after[key], review_before[key], key)
        # An S5 proposal made from a review keeps working with the longer journal.
        review = not_activated_review()
        with self.assertRaisesRegex(journal_module.JournalError, "S5_ALREADY_ACTIVATED"):
            journal_module.build_proposal(entry_type="s5_activation", payload=journal_module.activation_payload(review),
                                          review=review, journal=self.journal(), now=NOW)

    def test_existing_s5_proposal_goes_stale_once_a_card_is_recorded(self) -> None:
        # A card append moves the journal head, so an S5 proposal made before it must be made again.
        review = not_activated_review()
        proposal = journal_module.build_proposal(
            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
            journal=self.journal(), now=NOW)
        self.record_card()
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CHANGED_SINCE_PROPOSAL"):
            journal_module.apply_proposal(journal_path=self.path, proposal=proposal, confirmation=confirmation(proposal))


def weekdays(start: str, count: int) -> list[str]:
    days, cursor = [], date.fromisoformat(start)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


SESSIONS = weekdays(CARD_SESSION, 70)
CALENDAR = {"sessions": {day: {"core_close_at": f"{day}T20:00:00+00:00"} for day in SESSIONS},
            "identity": {"calendar_version": "test", "calendar_sha256": "0" * 64,
                         "coverage_start": SESSIONS[0], "coverage_end": SESSIONS[-1], "authority_status": "ACTIVE"}}
# The fixture card's decision_as_of (2026-09-30T11:21Z) is before the 2026-09-30 close: the score starts there.
START = SESSIONS[1]
S5, S20, S60 = SESSIONS[6], SESSIONS[21], SESSIONS[61]
NO_ACTIONS = {"status": "MISSING", "sha256": None, "errors": [], "actions": []}


def closes_with(**overrides: dict[str, str]) -> dict[str, dict[str, str]]:
    base = {symbol: {day: "100" for day in SESSIONS} for symbol in ("AAA", "BBB")}
    base["BBB"] = {day: "200" for day in SESSIONS}
    for symbol, values in overrides.items():
        base[symbol].update(values)
    return base


def spy_with(values: dict[str, str]) -> dict:
    return {"status": "OK", "closes": {**{day: "400" for day in SESSIONS}, **values}, "errors": []}


def after(session: str) -> datetime:
    return datetime.fromisoformat(f"{session}T21:00:00+00:00")


class ScorerTestCase(JournalCardTestCase):
    def scored(self, *, evaluation_as_of: datetime, closes: dict | None = None, benchmark: dict | None = None,
               calendar: dict | None = CALENDAR, corporate: dict | None = None, unverified: dict | None = None,
               journal: dict | None = None) -> dict:
        return scorer.score_journal(
            journal if journal is not None else self.journal(), calendar=calendar,
            calendar_failure=None if calendar is not None else "SESSION_CALENDAR_UNAVAILABLE:TEST",
            closes=closes if closes is not None else closes_with(AAA={S5: "110", S20: "90"}, BBB={S5: "210", S20: "180"}),
            unverified=unverified or {}, benchmark=benchmark if benchmark is not None else spy_with(
                {S5: "404", S20: "420"}),
            corporate_actions=corporate or NO_ACTIONS, evaluation_as_of=evaluation_as_of)

    @staticmethod
    def horizon(report: dict, ticker: str, kind: str, horizon: int) -> dict:
        row = next(item for item in report["results"] if item["ticker"] == ticker and item["kind"] == kind)
        return next(item for item in row["horizons"] if item["horizon_sessions"] == horizon)


class ScoreRuleTests(ScorerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.record_card()  # AAA TRIM, BBB HOLD, decision session 2026-09-29, start session 2026-09-30

    def test_pending_shows_the_sessions_left_and_a_future_close_is_never_used(self) -> None:
        report = self.scored(evaluation_as_of=after(SESSIONS[4]))
        item = self.horizon(report, "BBB", "ANALYSIS", 5)
        self.assertEqual((item["status"], item["remaining_sessions"], item["target_session"]), ("PENDING", 2, S5))
        self.assertEqual(self.horizon(report, "BBB", "ANALYSIS", 60)["remaining_sessions"], 57)
        # The close file already holds the day-5 close; before that session ends it still must not count.
        just_before = datetime.fromisoformat(f"{S5}T19:59:59+00:00")
        self.assertEqual(self.horizon(self.scored(evaluation_as_of=just_before), "BBB", "ANALYSIS", 5)["status"],
                         "PENDING")
        self.assertEqual(report["summary"]["pending_decisions"], 2)
        self.assertEqual(self.horizon(self.scored(evaluation_as_of=after(S5)), "BBB", "ANALYSIS", 5)["status"], "SCORED")

    def test_signs_for_hold_and_trim_against_cash_and_spy(self) -> None:
        report = self.scored(evaluation_as_of=after(S20))
        hold5 = self.horizon(report, "BBB", "ANALYSIS", 5)  # stock +5%, SPY +1%
        self.assertEqual((hold5["stock_return"], hold5["vs_cash"], hold5["vs_benchmark"]["value"]),
                         ("0.050000", "0.050000", "0.040000"))
        trim5 = self.horizon(report, "AAA", "ANALYSIS", 5)  # stock +10%, SPY +1%: trimming was wrong
        self.assertEqual((trim5["vs_cash"], trim5["vs_benchmark"]["value"]), ("-0.100000", "-0.090000"))
        trim20 = self.horizon(report, "AAA", "ANALYSIS", 20)  # stock -10%, SPY +5%: trimming was right
        self.assertEqual((trim20["vs_cash"], trim20["vs_benchmark"]["value"]), ("0.100000", "0.150000"))
        hold20 = self.horizon(report, "BBB", "ANALYSIS", 20)  # stock -10%, SPY +5%
        self.assertEqual((hold20["vs_cash"], hold20["vs_benchmark"]["value"]), ("-0.100000", "-0.150000"))

    def test_spy_is_always_reference_only_and_may_be_missing(self) -> None:
        report = self.scored(evaluation_as_of=after(S5))
        self.assertEqual(report["benchmark"]["label"], "REFERENCE_ONLY")
        self.assertEqual(self.horizon(report, "BBB", "ANALYSIS", 5)["vs_benchmark"]["label"], "REFERENCE_ONLY")
        missing = self.scored(evaluation_as_of=after(S5), benchmark={"status": "MISSING", "closes": {}, "errors": []})
        item = self.horizon(missing, "BBB", "ANALYSIS", 5)
        self.assertEqual((item["status"], item["vs_cash"], item["vs_benchmark"]["status"]),
                         ("SCORED", "0.050000", "BENCHMARK_UNAVAILABLE"))
        lines = "\n".join(scorer.render_report(report))
        self.assertIn("reference only", lines)

    def test_unverified_closes_are_labelled_reference_only(self) -> None:
        verified = self.scored(evaluation_as_of=after(S5))
        self.assertEqual(self.horizon(verified, "BBB", "ANALYSIS", 5)["price_grade"], "GRADE_B")
        flagged = self.scored(evaluation_as_of=after(S5), unverified={"BBB": {S5: ["SESSION_CALENDAR_NOT_ACTIVE"]}})
        item = self.horizon(flagged, "BBB", "ANALYSIS", 5)
        self.assertEqual((item["price_grade"], item["unverified_reasons"]), ("REFERENCE_ONLY", ["SESSION_CALENDAR_NOT_ACTIVE"]))

    def test_failures_are_statuses_not_exceptions(self) -> None:
        no_calendar = self.scored(evaluation_as_of=after(S5), calendar=None)
        self.assertEqual({item["reason"] for row in no_calendar["results"] for item in row["horizons"]},
                         {"SESSION_CALENDAR_UNAVAILABLE"})
        self.assertEqual(no_calendar["calendar"]["status"], "UNAVAILABLE")
        invalid = self.scored(evaluation_as_of=after(S5), corporate={**NO_ACTIONS, "status": "INVALID",
                                                                      "errors": ["CORPORATE_ACTIONS_NOT_JSON"]})
        self.assertEqual({item["reason"] for row in invalid["results"] for item in row["horizons"]},
                         {"CORPORATE_ACTIONS_INVALID"})
        gap = self.scored(evaluation_as_of=after(S5), closes=closes_with(AAA={S5: "110"}, BBB={}) | {"BBB": {}})
        self.assertEqual(self.horizon(gap, "BBB", "ANALYSIS", 5)["reason"], "START_CLOSE_MISSING")
        no_history = self.scored(evaluation_as_of=after(S5), closes={"AAA": closes_with()["AAA"]})
        self.assertEqual(self.horizon(no_history, "BBB", "ANALYSIS", 5)["reason"], "CLOSE_HISTORY_MISSING:BBB")
        short = {"sessions": dict(list(CALENDAR["sessions"].items())[:4]), "identity": CALENDAR["identity"]}
        self.assertEqual(self.horizon(self.scored(evaluation_as_of=after(S5), calendar=short), "BBB", "ANALYSIS", 5)["reason"],
                         "CALENDAR_DOES_NOT_COVER_HORIZON")
        outside = {"sessions": {day: row for day, row in CALENDAR["sessions"].items() if day > CARD_SESSION},
                   "identity": CALENDAR["identity"]}
        self.assertEqual(self.horizon(self.scored(evaluation_as_of=after(S5), calendar=outside), "BBB", "ANALYSIS", 5)["reason"],
                         "DECISION_SESSION_NOT_IN_CALENDAR")

    def test_an_unexplained_jump_is_not_scored_but_a_recorded_split_is_adjusted(self) -> None:
        halved = closes_with(AAA={S5: "50"})
        for day in SESSIONS:
            if day >= SESSIONS[3]:
                halved["AAA"][day] = "50"
        report = self.scored(evaluation_as_of=after(S5), closes=halved)
        self.assertEqual(self.horizon(report, "AAA", "ANALYSIS", 5)["reason"], "POSSIBLE_UNADJUSTED_SPLIT")
        action = {"symbol": "AAA", "action_type": "SPLIT", "effective_session": SESSIONS[3], "new_shares": 2,
                  "old_shares": 1, "official_source": {}, "kiwoom_crosscheck": {}, "recorded_by": "t",
                  "recorded_at": "2026-10-01T00:00:00Z"}
        adjusted = self.scored(evaluation_as_of=after(S5), closes=halved,
                               corporate={"status": "OK", "sha256": "1" * 64, "errors": [], "actions": [action]})
        item = self.horizon(adjusted, "AAA", "ANALYSIS", 5)
        self.assertEqual((item["status"], item["stock_return"]), ("SCORED", "0.000000"))  # 2:1 split, price flat

    def test_user_decision_is_scored_separately_and_the_last_entry_wins(self) -> None:
        decision_id = self.journal()["entries"][0]["payload"]["decision_id"]
        for action, session in (("HOLD", S5), ("TRIM", SESSIONS[1]), ):
            proposal = journal_module.build_user_decision_proposal(
                journal=self.journal(), decision_id=decision_id, user_action=action, effective_session=session,
                note="", now=NOW)
            journal_module.apply_proposal(journal_path=self.path, proposal=proposal, confirmation=confirmation(proposal))
        report = self.scored(evaluation_as_of=after(S20))
        kinds = sorted((row["ticker"], row["kind"], row["action"], row["start_session"]) for row in report["results"])
        self.assertEqual(kinds, [("AAA", "ANALYSIS", "TRIM", START), ("AAA", "USER", "TRIM", SESSIONS[1]),
                                 ("BBB", "ANALYSIS", "HOLD", START)])
        self.assertEqual(report["summary"]["decision_count"], 2)  # the user rows do not add decisions
        other = journal_module.build_user_decision_proposal(
            journal=self.journal(), decision_id=decision_id, user_action="OTHER", effective_session=None, note="", now=NOW)
        journal_module.apply_proposal(journal_path=self.path, proposal=other, confirmation=confirmation(other))
        report = self.scored(evaluation_as_of=after(S20))
        self.assertEqual(self.horizon(report, "AAA", "USER", 5)["reason"], "USER_ACTION_NOT_SCORABLE")

    def test_no_conclusion_before_thirty_scored_decisions(self) -> None:
        report = self.scored(evaluation_as_of=after(S20))
        self.assertFalse(report["summary"]["conclusion_allowed"])
        self.assertEqual(report["summary"]["scored_by_horizon"], {"5": 2, "20": 2, "60": 0})
        self.assertIn("30건", "\n".join(scorer.render_report(report)))

    def test_corrupt_or_missing_journal_gives_an_empty_report(self) -> None:
        missing = scorer.score_journal(
            journal_module.load_journal(self.tmp / "none.json"), calendar=CALENDAR, closes={}, unverified={},
            benchmark=spy_with({}), corporate_actions=NO_ACTIONS, evaluation_as_of=after(S5))
        self.assertEqual((missing["journal"]["status"], missing["results"]), ("MISSING", []))
        self.path.write_text("{broken", encoding="utf-8")
        corrupt = self.scored(evaluation_as_of=after(S5), journal=self.journal())
        self.assertEqual((corrupt["journal"]["status"], corrupt["results"]), ("CORRUPT", []))
        self.assertIn("JOURNAL_NOT_JSON", "\n".join(scorer.render_report(corrupt)))


MEASURED_SESSIONS = ["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"]
MEASURED_CALENDAR = {"sessions": {day: {"core_close_at": f"{day}T20:00:00Z"} for day in MEASURED_SESSIONS},
                     "identity": CALENDAR["identity"]}
MEASURED_CLOSES = {
    "MVLL": ["36.7900", "37.9300", "37.6500", "42.0300", "41.3800", "38.3600", "38.4955"],
    "NBIS": ["232.4600", "242.7900", "232.5800", "249.8900", "237.1500", "219.8100", "221.1100"],
    "SOXL": ["153.7500", "163.6600", "164.2200", "164.2100", "158.8700", "142.4700", "139.7050"],
}
MEASURED_DECISION_AS_OF = "2026-10-02T08:17:30.605734+00:00"


def measured_closes(**overrides: dict[str, str]) -> dict[str, dict[str, str]]:
    closes = {symbol: dict(zip(MEASURED_SESSIONS, values)) for symbol, values in MEASURED_CLOSES.items()}
    for symbol, values in overrides.items():
        closes[symbol].update(values)
    return closes


def card_entry(sequence: int, ticker: str, *, decision_as_of: str = MEASURED_DECISION_AS_OF,
               decision_session: str = "2026-10-01", reference_close: str | None = None) -> dict:
    return {"entry_type": "card_decision", "sequence": sequence, "payload": {
        "decision_id": f"{ticker.lower()}-decision", "ticker": ticker, "analysis_action": "HOLD",
        "sidecar_action": "HOLD_CORE", "conviction": "LOW", "decision_session": decision_session,
        "decision_as_of": decision_as_of, "reference_close": reference_close}}


def user_entry(sequence: int, ticker: str, effective_session: str) -> dict:
    return {"entry_type": "card_user_decision", "sequence": sequence, "payload": {
        "decision_id": f"{ticker.lower()}-decision", "ticker": ticker, "user_action": "HOLD",
        "effective_session": effective_session, "user_note": ""}}


class StartSessionTests(unittest.TestCase):
    """score-fix 2026-10-12: a card score starts at the first close after decision_as_of."""

    @staticmethod
    def scored(entries: list[dict], *, closes: dict | None = None,
               evaluation_as_of: datetime = datetime(2026, 10, 10, tzinfo=timezone.utc)) -> dict:
        return scorer.score_journal(
            {"status": "OK", "entries": entries, "errors": [], "head_sha256": "0" * 64}, calendar=MEASURED_CALENDAR,
            closes=closes if closes is not None else measured_closes(), unverified={},
            benchmark={"status": "MISSING", "closes": {}, "errors": []}, corporate_actions=NO_ACTIONS,
            evaluation_as_of=evaluation_as_of)

    @staticmethod
    def row(report: dict, ticker: str, kind: str = "ANALYSIS") -> dict:
        return next(item for item in report["results"] if item["ticker"] == ticker and item["kind"] == kind)

    def test_measured_hold_decisions_start_at_the_next_close(self) -> None:  # T1
        report = self.scored([card_entry(1, "MVLL", reference_close="36.7900"), card_entry(2, "NBIS"),
                              card_entry(3, "SOXL")])
        expected = {"MVLL": ("0.030987", "0.014909"), "NBIS": ("0.044438", "-0.089295"),
                    "SOXL": ("0.064455", "-0.146371")}
        for ticker, (pre_move, vs_cash) in expected.items():
            with self.subTest(ticker=ticker):
                row = self.row(report, ticker)
                self.assertEqual((row["decision_session"], row["start_session"], row["start_basis"]),
                                 ("2026-10-01", "2026-10-02", "FIRST_CLOSE_AFTER_DECISION"))
                self.assertEqual(row["pre_action_move"], pre_move)
                five = row["horizons"][0]
                self.assertEqual((five["status"], five["target_session"], five["vs_cash"]),
                                 ("SCORED", "2026-10-09", vs_cash))
                self.assertEqual([(item["status"], item["reason"]) for item in row["horizons"][1:]],
                                 [("NOT_SCORABLE", "CALENDAR_DOES_NOT_COVER_HORIZON")] * 2)
        # The recorded reference close is still compared with the decision session close (same-session check).
        self.assertEqual(self.row(report, "MVLL")["start_close_vs_recorded_reference"], "0.000000")

    def test_before_the_close_starts_the_same_day_and_at_the_close_the_next_day(self) -> None:  # T2, T3
        before = self.row(self.scored([card_entry(1, "MVLL", decision_as_of="2026-10-02T15:00:00Z")]), "MVLL")
        self.assertEqual(before["start_session"], "2026-10-02")
        at_close = self.row(self.scored([card_entry(1, "MVLL", decision_as_of="2026-10-02T20:00:00+00:00")]), "MVLL")
        self.assertEqual((at_close["start_session"], at_close["pre_action_move"]), ("2026-10-05", "0.023376"))
        self.assertEqual(at_close["horizons"][0]["reason"], "CALENDAR_DOES_NOT_COVER_HORIZON")

    def test_unreadable_time_or_no_later_session_is_not_scorable(self) -> None:
        for as_of, reason in (("not-a-time", "DECISION_AS_OF_INVALID"), ("2026-10-02T08:17:30", "DECISION_AS_OF_INVALID"),
                              ("2026-10-09T20:00:00Z", "CALENDAR_DOES_NOT_COVER_START")):
            with self.subTest(as_of=as_of):
                row = self.row(self.scored([card_entry(1, "MVLL", decision_as_of=as_of)]), "MVLL")
                self.assertEqual({(item["status"], item["reason"]) for item in row["horizons"]},
                                 {("NOT_SCORABLE", reason)})
                self.assertIsNone(row["start_session"])
        outside = self.row(self.scored([card_entry(1, "MVLL", decision_session="2026-09-30")]), "MVLL")
        self.assertEqual(outside["horizons"][0]["reason"], "DECISION_SESSION_NOT_IN_CALENDAR")

    def test_user_effective_session_rule(self) -> None:  # T4
        report = self.scored([card_entry(1, "MVLL"), user_entry(2, "MVLL", "2026-10-01"), card_entry(3, "NBIS"),
                              user_entry(4, "NBIS", "2026-10-06")])
        same = self.row(report, "MVLL", "USER")
        self.assertEqual((same["start_session"], same["start_basis"]), ("2026-10-02", "FIRST_CLOSE_AFTER_DECISION"))
        later = self.row(report, "NBIS", "USER")
        self.assertEqual((later["start_session"], later["start_basis"], later["decision_session"]),
                         ("2026-10-06", "EFFECTIVE_SESSION", "2026-10-01"))
        self.assertEqual(later["pre_action_move"], "0.074981")  # 249.89 / 232.46 - 1, before the user acted

    def test_a_split_like_jump_before_the_start_hides_only_the_pre_action_move(self) -> None:  # T5
        row = self.row(self.scored([card_entry(1, "MVLL")], closes=measured_closes(MVLL={"2026-10-01": "10"})), "MVLL")
        self.assertIsNone(row["pre_action_move"])
        self.assertEqual((row["horizons"][0]["status"], row["horizons"][0]["vs_cash"]), ("SCORED", "0.014909"))
        inside = measured_closes(MVLL={day: "15" for day in MEASURED_SESSIONS[3:]})
        row = self.row(self.scored([card_entry(1, "MVLL")], closes=inside), "MVLL")
        self.assertEqual(row["horizons"][0]["reason"], "POSSIBLE_UNADJUSTED_SPLIT")
        self.assertEqual(row["pre_action_move"], "0.030987")

    def test_no_close_after_the_evaluation_time_is_used(self) -> None:
        early = self.scored([card_entry(1, "MVLL", reference_close="36.7900")],
                            evaluation_as_of=datetime.fromisoformat("2026-10-02T19:59:59+00:00"))
        row = self.row(early, "MVLL")
        self.assertEqual(row["start_session"], "2026-10-02")
        self.assertIsNone(row["pre_action_move"])  # the start close is not final yet
        self.assertEqual(row["horizons"][0]["status"], "PENDING")
        self.assertEqual(row["start_close_vs_recorded_reference"], "0.000000")  # the 2026-10-01 close is final


class ScoreLocationTests(ScorerTestCase):
    """The journal is read only; scores go to workspace/outputs/journal-scores/ style folders only."""

    def setUp(self) -> None:
        super().setUp()
        self.record_card()
        self.output_root = self.tmp / "outputs" / "journal-scores"
        self.inputs = {"calendar": CALENDAR, "calendar_failure": None,
                       "closes": closes_with(AAA={S5: "110"}, BBB={S5: "210"}), "unverified": {},
                       "close_histories": {}, "corporate_actions": NO_ACTIONS, "benchmark": spy_with({S5: "404"})}

    def run_cli(self, *extra: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch.object(scorer, "load_inputs", return_value=self.inputs), contextlib.redirect_stdout(buffer):
            code = scorer.main(["--journal", str(self.path), "--output-root", str(self.output_root),
                                "--evaluation-as-of", after(S5).isoformat(),
                                "--decisions-root", str(self.tmp / "auto-core"), *extra])
        return code, buffer.getvalue()

    def journal_digest(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_scoring_leaves_the_journal_byte_identical_and_writes_only_under_the_output_root(self) -> None:
        before = self.journal_digest()
        writes: list[Path] = []
        real_open, real_write_text, real_write_bytes = builtins.open, Path.write_text, Path.write_bytes
        real_replace = Path.replace

        def note(target: object) -> None:
            writes.append(Path(str(target)).resolve())

        def spy_open(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in "wax+"):
                note(file)
            return real_open(file, mode, *args, **kwargs)

        def spy_text(self_path, *args, **kwargs):
            note(self_path)
            return real_write_text(self_path, *args, **kwargs)

        def spy_bytes(self_path, *args, **kwargs):
            note(self_path)
            return real_write_bytes(self_path, *args, **kwargs)

        def spy_replace(self_path, target):
            note(target)
            return real_replace(self_path, target)

        with mock.patch.object(builtins, "open", spy_open), mock.patch("io.open", spy_open), \
                mock.patch.object(Path, "write_text", spy_text), mock.patch.object(Path, "write_bytes", spy_bytes), \
                mock.patch.object(Path, "replace", spy_replace):
            code, output = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(self.journal_digest(), before)
        self.assertTrue(writes)
        root = self.output_root.resolve()
        for target in writes:
            self.assertNotEqual(target, self.path.resolve())
            self.assertIn(root, target.parents, f"write outside the score folder: {target}")
        report_path = next(self.output_root.glob("*/" + scorer.REPORT_FILE))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual((report["writes_journal"], report["order_authority"], report["quantity_authority"]),
                         (False, False, "none"))
        self.assertEqual(report["journal"]["head_sha256"], self.journal()["head_sha256"])
        self.assertIn("채점", output)
        self.assertEqual(forbidden_keys(report), [])

    def test_the_scorer_has_no_code_path_that_writes_the_journal(self) -> None:
        source = (SKILL_ROOT / "scripts/score_decision_journal.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                    and node.module == "portfolio_review_journal" for alias in node.names}
        self.assertEqual(imported, {"DEFAULT_JOURNAL_PATH", "JOURNAL_CARD_DECISION", "JOURNAL_CARD_USER_DECISION",
                                    "JOURNAL_ORDER_TICKET", "JOURNAL_TICKET_OUTCOME", "load_journal"})
        for name in ("apply_proposal", "apply_proposal_entries", "_atomic_write", "build_card_proposal",
                     "build_user_decision_proposal", "build_proposal"):
            self.assertNotIn(name, source)
            self.assertFalse(hasattr(scorer, name), name)
        self.assertEqual(sorted({node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
                                 and node.attr in {"write_text", "write_bytes", "rename", "unlink", "truncate",
                                                   "touch", "mkdir"}}), [])  # str.replace is allowed; Path writes are caught at run time
        self.assertEqual(source.count("write_json("), 1)  # the only writer, inside write_report under check_output_root

    def test_output_root_may_not_contain_the_journal_or_sit_in_a_protected_folder(self) -> None:
        for bad in (self.tmp, self.path.parent, self.path):
            with self.subTest(root=str(bad)):
                before = self.journal_digest()
                code, output = self.run_cli("--output-root", str(bad))
                self.assertEqual(code, 2)
                self.assertIn("OUTPUT_ROOT_CONTAINS_JOURNAL", output)
                self.assertEqual(self.journal_digest(), before)
        for protected in ("stock-strategy-system", "workspace/policies", "workspace/state"):
            with self.subTest(protected=protected):
                with self.assertRaisesRegex(ValueError, "OUTPUT_ROOT_IN_PROTECTED_FOLDER"):
                    scorer.check_output_root(REPO_ROOT / protected / "scores", self.path)

    def test_a_corrupt_journal_is_reported_and_stays_untouched(self) -> None:
        self.path.write_text("{broken", encoding="utf-8")
        before = self.journal_digest()
        code, output = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(self.journal_digest(), before)
        self.assertIn("JOURNAL_NOT_JSON", output)


class ReferenceClosesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="reference_closes_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, document: object) -> None:
        folder = self.tmp / scorer.REFERENCE_CLOSES_DIR
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SPY.json").write_text(json.dumps(document), encoding="utf-8")

    def test_missing_valid_and_invalid_files(self) -> None:
        self.assertEqual(scorer.load_reference_closes(self.tmp)["status"], "MISSING")
        good = {"schema_version": "reference-closes-1.0", "symbol": "SPY", "source_note": "user supplied",
                "closes": {"2026-09-29": "430.5"}}
        self.write(good)
        loaded = scorer.load_reference_closes(self.tmp)
        self.assertEqual((loaded["status"], loaded["closes"]), ("OK", {"2026-09-29": "430.5"}))
        for change in ({"symbol": "QQQ"}, {"source_note": " "}, {"closes": {}}, {"closes": {"2026-13-01": "1"}},
                       {"closes": {"2026-09-29": "-1"}}, {"extra": 1}):
            with self.subTest(change=change):
                self.write({**good, **change})
                self.assertEqual(scorer.load_reference_closes(self.tmp)["status"], "INVALID")


class GitignoreTests(unittest.TestCase):
    def ignored(self, path: str) -> bool:
        return subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO_ROOT, capture_output=True).returncode == 0

    def test_scores_and_journal_are_git_ignored_but_sources_are_not(self) -> None:
        for path in ("workspace/outputs/journal-scores/20261001T000000Z/journal-scores.json",
                     "stock-strategy-system/decision_journal.json"):
            with self.subTest(path=path):
                self.assertTrue(self.ignored(path))
        lines = [line.strip() for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines.count("workspace/outputs/journal-scores/"), 1)
        for path in ("manage-us-stock-strategy/scripts/score_decision_journal.py",
                     "manage-us-stock-strategy/tests/test_decision_journal_cards.py"):
            with self.subTest(path=path):
                self.assertFalse(self.ignored(path))


class ScriptHygieneTests(unittest.TestCase):
    def test_new_and_changed_scripts_are_ascii_only(self) -> None:
        for name in ("score_decision_journal.py", "portfolio_review_journal.py", "portfolio_status.py"):
            with self.subTest(name=name):
                (SKILL_ROOT / "scripts" / name).read_bytes().decode("ascii")


if __name__ == "__main__":
    unittest.main()
