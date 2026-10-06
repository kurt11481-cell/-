"""S5 decision journal: proposals from a review, confirmation-code apply, hash chain. Temp folders only."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_review_journal as journal_module  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from portfolio_exposure import review_content_hash  # noqa: E402
from test_portfolio_exposure import EVAL, Scenario  # noqa: E402
from test_holding_card import make_card  # noqa: E402
from test_portfolio_exposure_fail_closed import line_scenario  # noqa: E402
from validation_common import canonical_hash, validate_instance  # noqa: E402

NOW = datetime.now(timezone.utc)


def not_activated_review() -> dict:
    scenario = Scenario({"SOXL": 50}, "5000")
    scenario.snapshots = [fx.snapshot("2026-09-29", {"SOXL": 50}, "5000", revision=16)]
    scenario.journal = fx.journal(status="MISSING")
    return scenario.review()


class JournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="review_journal_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "decision_journal.json"

    def proposal(self, entry_type: str, payload: dict, review: dict, now: datetime = NOW) -> dict:
        return journal_module.build_proposal(entry_type=entry_type, payload=payload, review=review,
                                             journal=journal_module.load_journal(self.path), now=now)

    def confirm(self, proposal: dict, *, code: str | None = None, method: str = "COWORK_CHAT_USER_MESSAGE",
                message: str | None = None) -> dict:
        code = proposal["confirm_code"] if code is None else code
        return {"confirm_code": code, "confirmation_method": method,
                "user_message": f"확인 {code}" if message is None else message}

    def activate(self) -> dict:
        review = not_activated_review()
        proposal = self.proposal("s5_activation", journal_module.activation_payload(review), review)
        return journal_module.apply_proposal(journal_path=self.path, proposal=proposal,
                                             confirmation=self.confirm(proposal))

    def test_missing_journal_is_reported_not_raised(self) -> None:
        self.assertEqual(journal_module.load_journal(self.path),
                         {"status": "MISSING", "entries": [], "errors": [], "head_sha256": "0" * 64})

    def test_activation_proposal_copies_the_recomputed_hwm_and_apply_needs_the_code(self) -> None:
        review = not_activated_review()
        payload = journal_module.activation_payload(review)
        self.assertEqual((payload["hwm_usd"], payload["hwm_as_of"], payload["activation_date"], payload["state_revision"]),
                         ("10000", EVAL, EVAL, 16))
        self.assertEqual(payload["hwm_policy_initial_usd"], "28473.94")
        proposal = self.proposal("s5_activation", payload, review)
        self.assertEqual(validate_instance(proposal, journal_module.PROPOSAL_SCHEMA), [])
        self.assertEqual((proposal["auto_apply"], proposal["order_authority"], proposal["quantity_authority"]),
                         (False, False, "none"))
        self.assertFalse(self.path.exists())  # proposing never writes the journal
        rejected = {
            "CONFIRM_CODE_MISMATCH": self.confirm(proposal, code="00000000"),
            "CONFIRM_CODE_REQUIRED": self.confirm(proposal, code=" "),
            "CONFIRMATION_METHOD_INVALID": self.confirm(proposal, method="SCHEDULED_TASK"),
            "USER_CONFIRMATION_MESSAGE_REQUIRED": self.confirm(proposal, message="확인"),
        }
        for reason, confirmation in rejected.items():
            with self.subTest(reason=reason), self.assertRaisesRegex(journal_module.JournalError, reason):
                journal_module.apply_proposal(journal_path=self.path, proposal=proposal, confirmation=confirmation)
        self.assertFalse(self.path.exists())
        entry = journal_module.apply_proposal(journal_path=self.path, proposal=proposal,
                                              confirmation=self.confirm(proposal))
        self.assertEqual((entry["sequence"], entry["entry_type"], entry["previous_entry_sha256"]),
                         (1, "s5_activation", "0" * 64))
        loaded = journal_module.load_journal(self.path)
        self.assertEqual((loaded["status"], len(loaded["entries"])), ("OK", 1))
        self.assertEqual(validate_instance(json.loads(self.path.read_text(encoding="utf-8")),
                                           journal_module.JOURNAL_SCHEMA), [])

    def test_tampered_or_expired_or_stale_proposals_are_rejected(self) -> None:
        review = not_activated_review()
        proposal = self.proposal("s5_activation", journal_module.activation_payload(review), review)
        tampered = copy.deepcopy(proposal)
        tampered["payload"]["hwm_usd"] = "1"
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_PROPOSAL_INTEGRITY_MISMATCH"):
            journal_module.apply_proposal(journal_path=self.path, proposal=tampered, confirmation=self.confirm(proposal))
        old = self.proposal("s5_activation", journal_module.activation_payload(review), review,
                            now=NOW - timedelta(seconds=journal_module.PROPOSAL_MAX_AGE_SECONDS + 5))
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_PROPOSAL_EXPIRED"):
            journal_module.apply_proposal(journal_path=self.path, proposal=old, confirmation=self.confirm(old))
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_PROPOSAL_SCHEMA_INVALID"):
            journal_module.apply_proposal(journal_path=self.path, proposal=dict(proposal, extra=1),
                                          confirmation=self.confirm(proposal))
        wrong_fields = copy.deepcopy(proposal)
        del wrong_fields["payload"]["hwm_as_of"]
        wrong_fields["proposal_id"] = journal_module.proposal_content_hash(wrong_fields)
        wrong_fields["confirm_code"] = wrong_fields["proposal_id"][:8].upper()
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_PAYLOAD_FIELDS_INVALID"):
            journal_module.apply_proposal(journal_path=self.path, proposal=wrong_fields,
                                          confirmation=self.confirm(wrong_fields))
        self.assertFalse(self.path.exists())
        self.activate()
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CHANGED_SINCE_PROPOSAL"):
            journal_module.apply_proposal(journal_path=self.path, proposal=proposal, confirmation=self.confirm(proposal))

    def test_second_activation_is_rejected(self) -> None:
        self.activate()
        review = not_activated_review()
        with self.assertRaisesRegex(journal_module.JournalError, "S5_ALREADY_ACTIVATED"):
            self.proposal("s5_activation", journal_module.activation_payload(review), review)

    def test_review_must_be_untampered_and_ready(self) -> None:
        review = not_activated_review()
        changed = copy.deepcopy(review)
        changed["activation_candidate"]["hwm_usd"] = "99999"
        with self.assertRaisesRegex(journal_module.JournalError, "REVIEW_HASH_MISMATCH"):
            journal_module._checked_review(changed)
        not_ready = copy.deepcopy(review)
        not_ready["activation_candidate"]["status"] = "NOT_READY"
        not_ready["review_id"] = review_content_hash(not_ready)
        with self.assertRaisesRegex(journal_module.JournalError, "ACTIVATION_CANDIDATE_NOT_READY"):
            journal_module.activation_payload(journal_module._checked_review(not_ready))
        activated = Scenario({"SOXL": 50}, "5000").review()
        with self.assertRaisesRegex(journal_module.JournalError, "S5_ALREADY_ACTIVATED"):
            journal_module.activation_payload(activated)

    def test_line_review_entry_matches_the_recomputed_event_and_releases_the_pause(self) -> None:
        self.activate()
        scenario = line_scenario(["100", "80", "80", "60", "60"])
        review = scenario.review()
        self.assertEqual([event["line_id"] for event in review["review_lines"]["open_events"]], ["L1", "L2"])
        with self.assertRaisesRegex(journal_module.JournalError, "LINE_REVIEW_OPEN_EVENT_NOT_FOUND"):
            journal_module.line_review_payload(review, "L3", "continue", "")
        with self.assertRaisesRegex(journal_module.JournalError, "LINE_REVIEW_CONCLUSION_INVALID"):
            journal_module.line_review_payload(review, "L2", "sell_everything", "")
        entries = []
        for line_id in ("L1", "L2"):
            payload = journal_module.line_review_payload(review, line_id, "continue", "TEST_ONLY")
            self.assertEqual(sorted(payload), ["breach_date", "conclusion", "conclusion_note", "hwm", "line_id",
                                               "review_status"])
            proposal = self.proposal("line_review_completed", payload, review)
            entries.append(journal_module.apply_proposal(journal_path=self.path, proposal=proposal,
                                                         confirmation=self.confirm(proposal, method="USER_TERMINAL")))
        loaded = journal_module.load_journal(self.path)
        self.assertEqual([entry["sequence"] for entry in loaded["entries"]], [1, 2, 3])
        # The recomputation with the journal's line reviews (and the scenario's own activation) clears the pause.
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000"), *entries)
        after = scenario.review()
        self.assertEqual(after["review_lines"]["open_events"], [])
        self.assertFalse(after["pauses"]["add_recommendations"]["paused"])
        self.assertEqual(after["review_lines"]["hwm_usd"], "10000")  # "continue" keeps the HWM

    def test_peak_review_entry(self) -> None:
        self.activate()
        scenario = Scenario({"SOXL": 3}, "9700")
        index = scenario.sessions.index(EVAL)
        scenario.journal = fx.journal(fx.activation_entry(scenario.sessions[index - 3], "10150"))
        for offset, price in ((3, "150"), (2, "150"), (1, "104"), (0, "100")):
            scenario.closes["SOXL"][scenario.sessions[index - offset]] = price
        scenario.snapshots = [fx.snapshot(scenario.sessions[index - 3], {"SOXL": 3}, "9700"),
                              fx.snapshot(scenario.sessions[index - 1], {"SOXL": 3}, "9700")]
        review = scenario.review()
        payload = journal_module.peak_review_payload(review, "SOXL")
        self.assertEqual((payload["peak"], payload["breach_date"]), ("150", scenario.sessions[index - 1]))
        with self.assertRaisesRegex(journal_module.JournalError, "PEAK_REVIEW_OPEN_EVENT_NOT_FOUND"):
            journal_module.peak_review_payload(review, "NBIS")
        proposal = self.proposal("peak_review_card_completed", payload, review)
        entry = journal_module.apply_proposal(journal_path=self.path, proposal=proposal,
                                              confirmation=self.confirm(proposal))
        scenario.journal = fx.journal(fx.activation_entry(scenario.sessions[index - 3], "10150"), entry)
        self.assertFalse(scenario.review()["peak_reviews"][0]["pause_add_recommendations"])

    def test_broken_chain_or_edited_entry_is_corrupt_and_never_extended(self) -> None:
        self.activate()
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["entries"][0]["payload"]["hwm_usd"] = "1"
        document["entries"].append(dict(document["entries"][0], sequence=2))
        self.path.write_text(json.dumps(document), encoding="utf-8")
        loaded = journal_module.load_journal(self.path)
        self.assertEqual((loaded["status"], loaded["errors"]), ("CORRUPT", ["JOURNAL_CHAIN_BROKEN:2"]))
        review = line_scenario(["100", "80", "80", "80", "80"]).review()
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CORRUPT"):
            self.proposal("line_review_completed", journal_module.line_review_payload(review, "L1", "continue", ""),
                          review)
        self.path.write_text("{broken", encoding="utf-8")
        self.assertEqual(journal_module.load_journal(self.path)["errors"], ["JOURNAL_NOT_JSON"])
        self.path.write_text(json.dumps({"entries": [{"id": 1}]}), encoding="utf-8")
        self.assertEqual(journal_module.load_journal(self.path)["status"], "CORRUPT")

    def test_cli_propose_show_apply_and_verify(self) -> None:
        review_path = self.tmp / "review.json"
        review_path.write_text(json.dumps(not_activated_review()), encoding="utf-8")
        output_root = self.tmp / "proposals"

        def run(*argv: str) -> tuple[int, str]:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = journal_module.main(list(argv))
            return code, buffer.getvalue()

        code, output = run("propose-activation", "--review", str(review_path), "--journal", str(self.path),
                           "--output-root", str(output_root))
        self.assertEqual(code, 0)
        self.assertIn("S7 적용 시작", output)
        proposal_path = next(output_root.glob("*/journal_proposal.json"))
        confirm_code = json.loads(proposal_path.read_text(encoding="utf-8"))["confirm_code"]
        self.assertIn(confirm_code, run("show", "--proposal", str(proposal_path))[1])
        self.assertFalse(self.path.exists())
        code, output = run("apply", "--proposal", str(proposal_path), "--confirm", confirm_code, "--confirmed-via",
                           "COWORK_CHAT_USER_MESSAGE", "--journal", str(self.path))
        self.assertEqual(code, 2)  # Cowork confirmation needs the user's message
        code, output = run("apply", "--proposal", str(proposal_path), "--confirm", "DEADBEEF", "--confirmed-via",
                           "USER_TERMINAL", "--journal", str(self.path))
        self.assertEqual((code, self.path.exists()), (2, False))
        code, output = run("apply", "--proposal", str(proposal_path), "--confirm", confirm_code, "--confirmed-via",
                           "COWORK_CHAT_USER_MESSAGE", "--user-message", f"확인 {confirm_code}", "--journal",
                           str(self.path))
        self.assertEqual(code, 0)
        code, output = run("verify", "--journal", str(self.path))
        self.assertEqual((code, json.loads(output)["status"], json.loads(output)["entry_count"]), (0, "OK", 1))
        code, output = run("propose-activation", "--review", str(review_path), "--journal", str(self.path),
                           "--output-root", str(output_root))
        self.assertEqual(code, 2)
        self.assertIn("S5_ALREADY_ACTIVATED", output)


class LastEntryRecomputeTests(unittest.TestCase):
    """A hand edit of the last entry changes only the head, so the chain cannot see it (S7 9.2-2).
    load_journal recomputes each entry's own invariants; an edit that breaks one is CORRUPT (R0)."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="review_journal_last_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "decision_journal.json"
        self.texts: dict[str, str] = {}
        self.build_every_entry_type()

    def apply(self, proposal: dict) -> list[dict]:
        confirmation = {"confirm_code": proposal["confirm_code"], "confirmation_method": "COWORK_CHAT_USER_MESSAGE",
                        "user_message": f"확인 {proposal['confirm_code']}"}
        return journal_module.apply_proposal_entries(journal_path=self.path, proposal=proposal,
                                                     confirmation=confirmation)

    def append_s5(self, entry_type: str, payload: dict, review: dict) -> None:
        proposal = journal_module.build_proposal(entry_type=entry_type, payload=payload, review=review,
                                                 journal=journal_module.load_journal(self.path), now=NOW)
        self.apply(proposal)
        self.texts[entry_type] = self.path.read_text(encoding="utf-8")

    def build_every_entry_type(self) -> None:
        """One journal through the real apply path with every entry type; a text snapshot after each."""
        review = not_activated_review()
        self.append_s5("s5_activation", journal_module.activation_payload(review), review)
        review = line_scenario(["100", "80", "80", "60", "60"]).review()
        self.append_s5("line_review_completed",
                       journal_module.line_review_payload(review, "L1", "continue", "TEST_ONLY"), review)
        scenario = Scenario({"SOXL": 3}, "9700")
        index = scenario.sessions.index(EVAL)
        scenario.journal = fx.journal(fx.activation_entry(scenario.sessions[index - 3], "10150"))
        for offset, price in ((3, "150"), (2, "150"), (1, "104"), (0, "100")):
            scenario.closes["SOXL"][scenario.sessions[index - offset]] = price
        scenario.snapshots = [fx.snapshot(scenario.sessions[index - 3], {"SOXL": 3}, "9700"),
                              fx.snapshot(scenario.sessions[index - 1], {"SOXL": 3}, "9700")]
        review = scenario.review()
        self.append_s5("peak_review_card_completed", journal_module.peak_review_payload(review, "SOXL"), review)
        card, pack = make_card()
        entries = self.apply(journal_module.build_card_proposal(
            card=card, fact_pack=pack, journal=journal_module.load_journal(self.path), now=NOW))
        self.texts["card_decision"] = self.path.read_text(encoding="utf-8")
        proposal = journal_module.build_user_decision_proposal(
            journal=journal_module.load_journal(self.path), decision_id=entries[0]["payload"]["decision_id"],
            user_action="HOLD", effective_session=None, note="", now=NOW)
        self.apply(proposal)
        self.texts["card_user_decision"] = self.path.read_text(encoding="utf-8")

    def tampered(self, stage: str, mutate) -> tuple[dict, int]:
        """Edit the last entry of that stage's journal text (the chain stays intact) and load it."""
        document = json.loads(self.texts[stage])
        mutate(document["entries"])
        self.path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return journal_module.load_journal(self.path), len(document["entries"])

    def assert_corrupt(self, stage: str, mutate, reason: str) -> None:
        loaded, sequence = self.tampered(stage, mutate)
        self.assertEqual((loaded["status"], loaded["errors"], loaded["entries"]),
                         ("CORRUPT", [f"JOURNAL_ENTRY_INCONSISTENT:{sequence}:{reason}"], []))

    def test_every_entry_type_written_by_apply_loads_ok(self) -> None:
        for stage, text in self.texts.items():
            with self.subTest(stage=stage):
                self.path.write_text(text, encoding="utf-8")
                loaded = journal_module.load_journal(self.path)
                self.assertEqual((loaded["status"], loaded["errors"]), ("OK", []))
        self.assertEqual([entry["entry_type"] for entry in loaded["entries"]],
                         ["s5_activation", "line_review_completed", "peak_review_card_completed", "card_decision",
                          "card_decision", "card_user_decision"])

    def test_edited_last_activation_entry_is_corrupt(self) -> None:
        def last(entries: list[dict]) -> dict:
            return entries[-1]

        def set_payload(key: str, value):
            return lambda entries: last(entries)["payload"].__setitem__(key, value)

        def drop_field(entries: list[dict]) -> None:
            del last(entries)["payload"]["hwm_as_of"]

        def forge_code_and_message(entries: list[dict]) -> None:
            last(entries).update(confirm_code="00000000", user_message="확인 00000000")

        cases = {
            "ACTIVATION_HWM_DIFFERENCE_MISMATCH": set_payload("hwm_usd", "1"),
            "CONFIRM_CODE_NOT_IN_USER_MESSAGE": lambda entries: last(entries).update(confirm_code="00000000"),
            "ACTIVATION_SESSION_MISMATCH": set_payload("window_end", "2999-01-01"),
            "ACTIVATION_HWM_DATE_OUTSIDE_WINDOW": set_payload("hwm_as_of", "2000-01-01"),
            "PAYLOAD_FIELDS_INVALID": drop_field,
            "CONFIRM_CODE_ENTRY_ID_MISMATCH": forge_code_and_message,
        }
        for reason, mutate in cases.items():
            with self.subTest(reason=reason):
                self.assert_corrupt("s5_activation", mutate, reason)
        self.assert_corrupt("s5_activation", lambda entries: entries[-1].update(user_message="확인"),
                            "CONFIRM_CODE_NOT_IN_USER_MESSAGE")
        self.assert_corrupt("s5_activation", lambda entries: entries[-1].update(entry_id="1" * 64),
                            "CONFIRM_CODE_ENTRY_ID_MISMATCH")

    def test_edited_last_review_entries_are_corrupt(self) -> None:
        self.assert_corrupt("line_review_completed",
                            lambda entries: entries[-1]["payload"].update(breach_date="2999-01-01"),
                            "LINE_REVIEW_BREACH_AFTER_SESSION")
        self.assert_corrupt("peak_review_card_completed",
                            lambda entries: entries[-1]["payload"].update(peak_date="2999-01-01"),
                            "PEAK_REVIEW_DATES_OUT_OF_ORDER")

    def test_edited_last_card_entries_are_corrupt(self) -> None:
        def clone_previous(entries: list[dict]) -> None:
            clone = copy.deepcopy(entries[-2])  # a chain-valid forged append of an already recorded decision
            clone.update(sequence=len(entries) + 1, previous_entry_sha256=canonical_hash(entries[-1]))
            entries.append(clone)

        cases = {
            "CARD_DECISION_ID_MISMATCH": lambda entries: entries[-1]["payload"].update(decision_id="1" * 64),
            "CARD_REVIEW_ID_MISMATCH": lambda entries: entries[-1].update(review_id="2" * 64),
            "CARD_SESSION_MISMATCH": lambda entries: entries[-1]["payload"].update(decision_session="2000-01-01"),
            "CARD_SIDECAR_ACTION_NOT_ALLOWED": lambda entries: entries[-1]["payload"].update(sidecar_action="ADD_REVIEW"),
        }
        for reason, mutate in cases.items():
            with self.subTest(reason=reason):
                self.assert_corrupt("card_decision", mutate, reason)
        loaded, sequence = self.tampered("card_decision", clone_previous)
        self.assertEqual(loaded["errors"], [f"JOURNAL_ENTRY_INCONSISTENT:{sequence}:CARD_DECISION_DUPLICATE"])
        cases = {
            "USER_DECISION_REFERENCE_INVALID": lambda entries: entries[-1]["payload"].update(ticker="ZZZ"),
            "USER_DECISION_REVIEW_ID_MISMATCH": lambda entries: entries[-1].update(review_id="2" * 64),
            "USER_DECISION_SESSION_INCONSISTENT": lambda entries: entries[-1].update(evaluation_session="2000-01-01"),
        }
        for reason, mutate in cases.items():
            with self.subTest(reason=reason):
                self.assert_corrupt("card_user_decision", mutate, reason)

    def test_a_corrupt_last_entry_is_never_extended_and_stops_the_review(self) -> None:
        review = line_scenario(["100", "80", "80", "60", "60"]).review()
        payload = journal_module.line_review_payload(review, "L2", "continue", "")
        proposal = journal_module.build_proposal(entry_type="line_review_completed", payload=payload, review=review,
                                                 journal=journal_module.load_journal(self.path), now=NOW)
        loaded, _ = self.tampered("card_user_decision", lambda entries: entries[-1]["payload"].update(ticker="ZZZ"))
        self.assertEqual(loaded["status"], "CORRUPT")
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CORRUPT"):
            journal_module.build_proposal(entry_type="line_review_completed", payload=payload, review=review,
                                          journal=loaded, now=NOW)
        with self.assertRaisesRegex(journal_module.JournalError, "JOURNAL_CORRUPT"):
            self.apply(proposal)
        # The exposure review reads the corrupt journal as R0 (decision_journal_missing_or_corrupt).
        scenario = Scenario({"SOXL": 50}, "5000")
        scenario.journal = loaded
        trigger = next(item for item in scenario.review()["fail_closed"]["triggers"]
                       if item["id"] == "decision_journal_missing_or_corrupt")
        self.assertTrue(trigger["active"])
        self.assertIn("JOURNAL_ENTRY_INCONSISTENT:6:USER_DECISION_REFERENCE_INVALID", trigger["reasons"])


if __name__ == "__main__":
    unittest.main()
