"""S7-1 Judge required fixes a-g (prompt section 9.1): each test reproduces the Judge's finding.

Synthetic inputs and temp folders only. No real holdings, prices or account data.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cash_flow_evidence as cfe  # noqa: E402
import portfolio_exposure as pe  # noqa: E402
import portfolio_review_journal as journal_module  # noqa: E402
import run_portfolio_exposure_review as runner  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from test_portfolio_exposure import EVAL, Scenario, trigger  # noqa: E402
from test_portfolio_exposure_fail_closed import declaration  # noqa: E402
from test_run_portfolio_exposure_review import POLICY, RunnerCase  # noqa: E402

LATER = "2026-10-01"  # a reconciliation dated after the evaluation session (Korean-afternoon reconcile)
DEPOSIT_ROW = {"deal_kind_nm": "입출금", "rmrk_nm": "이체입금", "fc_exct_amt": "1000.00"}


def review_of(scenario: Scenario, **overrides: Any) -> dict[str, Any]:
    arguments = dict(
        policy=scenario.policy, evaluation_session=scenario.evaluation, calendar_sessions=scenario.sessions,
        snapshots=scenario.snapshots, snapshot_reasons=scenario.snapshot_reasons, closes=scenario.closes,
        close_unverified=scenario.close_unverified, journal=scenario.journal, cards=scenario.cards,
        earnings=scenario.earnings, proposals=scenario.proposals)
    arguments.update(overrides)
    return pe.build_exposure_review(**arguments)


def flat_add_zone() -> Scenario:
    """SOXL 30 shares at a flat 100 plus cash 7,000 (E = 0.9, an add zone); activation five sessions back."""
    scenario = Scenario({"SOXL": 30}, "7000")
    index = scenario.sessions.index(EVAL)
    scenario.days = scenario.sessions[index - 4:index + 1]
    for day in scenario.days:
        scenario.closes["SOXL"][day] = "100"
    scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000", revision=1))
    return scenario


class FixAHeldFailsClosedTests(unittest.TestCase):
    """a: review_lines.status HELD must fail closed, and a later-dated reconciliation cannot lift the hold."""

    def assert_held_and_closed(self, review: dict[str, Any]) -> None:
        self.assertEqual(review["review_lines"]["status"], "HELD")
        self.assertIn("LINE_EVALUATION_ON_HOLD",
                      trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"])
        self.assertTrue(review["fail_closed"]["active"])
        self.assertTrue(review["pauses"]["add_recommendations"]["paused"])
        self.assertTrue(review["pauses"]["new_buy_recommendations"]["paused"])
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertEqual(review["recommendations"]["proposals"][0]["status"], "OMITTED")

    def test_cash_flow_hold_lifted_by_a_reconciliation_dated_after_the_session(self) -> None:
        scenario = flat_add_zone()
        row = dict(DEPOSIT_ROW, deal_dt=scenario.days[1].replace("-", ""))
        undeclared = declaration([row], None, period=(scenario.days[0], scenario.days[2]))
        late = declaration([row], "1000.00", period=(scenario.days[0], LATER), prior=[undeclared])
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 30}, "7000", revision=1, from_entry=True),
            fx.snapshot(scenario.days[2], {"SOXL": 30}, "8000", revision=2, block=undeclared, from_entry=True),
            fx.snapshot(LATER, {"SOXL": 30}, "8000", revision=3, block=late, from_entry=True),
        ]
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "NBIS", "target_weight": "0.05"}]
        review = scenario.review()
        self.assert_held_and_closed(review)
        # The declaration dated after the evaluation session is not counted for this session.
        self.assertTrue(trigger(review, "undeclared_cash_flow")["active"])
        self.assertEqual(review["review_lines"]["hwm_usd"], "10000")
        self.assertEqual(review["snapshot"]["later_reconciliations_not_used"], 1)

    def test_sale_hold_lifted_by_a_reconciliation_dated_after_the_session(self) -> None:
        scenario = flat_add_zone()
        clear = declaration([], None, period=(scenario.days[0], LATER))
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 30, "NBIS": 5}, "6000", revision=1, from_entry=True),
            fx.snapshot(scenario.days[2], {"SOXL": 30}, "6000", revision=2, decreased=True, block=clear, from_entry=True),
            fx.snapshot(LATER, {"SOXL": 30}, "7000", revision=3, block=declaration([], None, period=(scenario.days[2], LATER)),
                        from_entry=True),
        ]
        scenario.proposals = [{"kind": "new_buy_within_band", "symbol": "MU", "target_weight": "0.05"}]
        review = scenario.review()
        self.assert_held_and_closed(review)
        self.assertIn("SALE_PROCEEDS_PENDING_CASH_CONFIRMATION",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])

    def test_hold_is_lifted_once_the_session_reaches_the_later_reconciliation(self) -> None:
        scenario = flat_add_zone()
        row = dict(DEPOSIT_ROW, deal_dt=scenario.days[1].replace("-", ""))
        undeclared = declaration([row], None, period=(scenario.days[0], scenario.days[2]))
        late = declaration([row], "1000.00", period=(scenario.days[0], EVAL), prior=[undeclared])
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 30}, "7000", revision=1, from_entry=True),
            fx.snapshot(scenario.days[2], {"SOXL": 30}, "8000", revision=2, block=undeclared, from_entry=True),
            fx.snapshot(EVAL, {"SOXL": 30}, "8000", revision=3, block=late, from_entry=True),
        ]
        review = scenario.review()
        self.assertEqual((review["review_lines"]["status"], review["review_lines"]["hwm_usd"]), ("EVALUATED", "11000.00"))
        self.assertFalse(review["fail_closed"]["active"])


class FixBActivationCandidateTests(unittest.TestCase):
    """b: an activation candidate is READY only when nothing but "not activated / no journal" is open."""

    def not_activated(self) -> Scenario:
        scenario = Scenario({"SOXL": 50}, "5000")
        scenario.snapshots = [fx.snapshot("2026-09-29", {"SOXL": 50}, "5000", revision=16)]
        scenario.journal = fx.journal(status="MISSING")
        return scenario

    def assert_not_ready(self, review: dict[str, Any], fragment: str) -> None:
        candidate = review["activation_candidate"]
        self.assertEqual(candidate["status"], "NOT_READY")
        self.assertTrue(any(fragment in reason for reason in candidate["reasons"]), candidate["reasons"])
        self.assertIsNone(candidate["hwm_usd"])
        with self.assertRaisesRegex(journal_module.JournalError, "ACTIVATION_CANDIDATE_NOT_READY"):
            journal_module.activation_payload(review)

    def test_clean_inputs_are_ready(self) -> None:
        review = self.not_activated().review()
        self.assertEqual(review["activation_candidate"]["status"], "READY")
        self.assertEqual(review["activation_candidate"]["reasons"], [])
        self.assertEqual(journal_module.activation_payload(review)["hwm_usd"], "10000")

    def test_broker_reconciliation_older_than_four_days_is_not_ready(self) -> None:
        scenario = self.not_activated()
        scenario.snapshots = [fx.snapshot("2026-09-16", {"SOXL": 50}, "5000", revision=16)]  # 14 days
        self.assert_not_ready(scenario.review(), "broker_snapshot_older_than_broker_snapshot_max_age_calendar_days")

    def test_state_changed_outside_the_ledger_is_not_ready(self) -> None:
        scenario = self.not_activated()
        scenario.snapshot_reasons = ["STATE_CHANGED_OUTSIDE_LEDGER"]
        self.assert_not_ready(scenario.review(), "STATE_CHANGED_OUTSIDE_LEDGER")

    def test_unverified_closes_are_not_ready(self) -> None:
        scenario = self.not_activated()
        scenario.close_unverified = {"SOXL": {EVAL: ["SESSION_CALENDAR_NOT_ACTIVE"]}}
        self.assert_not_ready(scenario.review(), "SESSION_CALENDAR_NOT_ACTIVE")

    def test_closes_of_instruments_held_earlier_in_the_window_must_be_verified_too(self) -> None:
        scenario = self.not_activated()
        index = scenario.sessions.index(EVAL)
        start = scenario.sessions[index - 2]
        scenario.policy["portfolio_review_lines"]["hwm_initial_as_of"] = start
        scenario.snapshots = [fx.snapshot(start, {"SOXL": 50, "NBIS": 1}, "4800", revision=15),
                              fx.snapshot("2026-09-29", {"SOXL": 50}, "5000", revision=16)]
        self.assertEqual(scenario.review()["activation_candidate"]["status"], "READY")
        scenario.close_unverified = {"NBIS": {start: ["CLOSE_HISTORY_PAGES_NOT_VERIFIED"]}}
        self.assert_not_ready(scenario.review(), "CLOSE_UNVERIFIED:NBIS:CLOSE_HISTORY_PAGES_NOT_VERIFIED")

    def test_v_unavailable_or_corrupt_journal_or_stale_session_is_not_ready(self) -> None:
        scenario = self.not_activated()
        del scenario.closes["SOXX"][EVAL]
        self.assert_not_ready(scenario.review(), "required_price_missing")
        scenario = self.not_activated()
        self.assert_not_ready(review_of(scenario, evaluation_reasons=["EVALUATION_SESSION_NOT_LATEST:2026-10-01"]),
                              "EVALUATION_SESSION_NOT_LATEST")
        scenario = self.not_activated()
        scenario.journal = {"status": "CORRUPT", "entries": [], "errors": ["JOURNAL_CHAIN_BROKEN:1"]}
        self.assertIsNone(scenario.review()["activation_candidate"])

    def test_non_default_inputs_are_not_ready(self) -> None:
        scenario = self.not_activated()
        self.assert_not_ready(review_of(scenario, inputs={"non_default_inputs": ["state"]}), "NON_DEFAULT_INPUTS:state")
        self.assertEqual(review_of(scenario, inputs={"non_default_inputs": []})["activation_candidate"]["status"], "READY")

    def test_journal_refuses_a_review_whose_candidate_was_edited_to_ready(self) -> None:
        scenario = self.not_activated()
        scenario.snapshot_reasons = ["STATE_CHANGED_OUTSIDE_LEDGER"]
        review = scenario.review()
        forged = copy.deepcopy(review)
        forged["activation_candidate"].update(status="READY", reasons=[], hwm_usd="10000", hwm_as_of=EVAL,
                                              hwm_difference_usd="-18473.94", state_revision=16)
        forged["review_id"] = pe.review_content_hash(forged)
        with self.assertRaisesRegex(journal_module.JournalError, "ACTIVATION_BLOCKED"):
            journal_module.activation_payload(forged)


class FixCHistoryGapTests(unittest.TestCase):
    """c: a missing close inside the available history is not a "short history"; V is unavailable."""

    def test_one_missing_close_inside_the_window_makes_v_unavailable(self) -> None:
        scenario = Scenario({"SOXL": 62}, "3800")  # N = 1.86
        gap = scenario.sessions[scenario.sessions.index(EVAL) - 70]
        del scenario.closes["SOXL"][gap]
        review = scenario.review()
        self.assertIsNone(review["exposure"]["sox_equivalent"])
        self.assertEqual(review["exposure"]["status"], "UNAVAILABLE")
        self.assertFalse(review["exposure"]["short_history"])
        self.assertIn(f"V_HISTORY_GAP:SOXL:{gap}", review["exposure"]["unavailable_reasons"])
        self.assertIn(f"V_UNAVAILABLE:V_HISTORY_GAP:SOXL:{gap}",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
        self.assertTrue(review["pauses"]["add_recommendations"]["paused"])
        self.assertTrue(all(item["label"] == "UNVERIFIED" for item in review["recommendations"]["reduce"]))

    def test_missing_benchmark_close_inside_the_window_makes_v_unavailable(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        gap = scenario.sessions[scenario.sessions.index(EVAL) - 10]
        del scenario.closes["SOXX"][gap]
        review = scenario.review()
        self.assertIsNone(review["exposure"]["sox_equivalent"])
        self.assertIn(f"V_HISTORY_GAP:SOXX:{gap}", review["exposure"]["unavailable_reasons"])
        self.assertEqual(review["recommendations"]["add"], [])

    def test_gap_older_than_the_252_return_window_does_not_matter(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000", session_count=300)
        del scenario.closes["SOXL"][scenario.sessions[scenario.sessions.index(EVAL) - 280]]
        exposure = scenario.review()["exposure"]
        self.assertEqual((exposure["status"], exposure["return_sessions_used"], exposure["short_history"]),
                         ("VERIFIED", 252, False))

    def test_short_history_label_is_only_for_a_late_start_without_gaps(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        start = scenario.sessions.index(EVAL) - 124
        for session in scenario.sessions[:start]:
            scenario.closes["SOXL"].pop(session, None)
        exposure = scenario.review()["exposure"]
        self.assertEqual((exposure["status"], exposure["return_sessions_used"], exposure["short_history"]),
                         ("VERIFIED", 124, True))
        self.assertEqual(exposure["window_start"], scenario.sessions[start])

    def test_new_entry_candidate_with_a_gap_is_blocked(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        scenario.cards = {"MU": {"action": "ADD", "valid": True, "session_date": EVAL}}
        del scenario.closes["MU"][scenario.sessions[scenario.sessions.index(EVAL) - 30]]
        review = scenario.review()
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertEqual(review["recommendations"]["omitted"][0]["reasons"], ["V_HISTORY_GAP_BLOCKS_NEW_ENTRY"])


class FixDEvaluationSessionTests(RunnerCase):
    """d: a calendar that does not reach today must not present an old session as the latest one."""

    def run_with(self, *arguments: str) -> tuple[int, str, list[Path]]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = runner.main(["--policy", str(POLICY), "--state", str(self.state_path), "--journal",
                                str(self.journal_path), "--closes-root", str(self.closes_root), "--output-root",
                                str(self.output_root), *arguments])
        return code, buffer.getvalue(), sorted(self.output_root.glob("*/portfolio-exposure-review.*.json"))

    def test_default_session_fails_when_the_calendar_does_not_cover_today(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0, ledger=False)
        code, output, files = self.run_with("--calendar", str(self.calendar_0829), "--now",
                                            "2026-10-01T12:00:00+00:00")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["error"], "SESSION_CALENDAR_DOES_NOT_COVER_TODAY:2026-08-29")
        self.assertEqual(files, [])  # 2026-08-28 is never shown as the latest completed session

    def test_explicit_old_session_is_labelled_and_fails_closed(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0, as_of="2026-08-27")
        code, output, files = self.run_with("--calendar", str(self.calendar_0829), "--session", "2026-08-28",
                                            "--now", "2026-10-01T12:00:00+00:00")
        self.assertEqual(code, 0)
        review = json.loads(files[-1].read_text(encoding="utf-8"))
        self.assertEqual(review["evaluation_session"], "2026-08-28")
        self.assertIn("EVALUATION_SESSION_NOT_VERIFIED_LATEST:CALENDAR_ENDS_2026-08-29",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
        self.assertEqual(review["inputs"]["evaluation_session_status"], "CALENDAR_DOES_NOT_COVER_TODAY")
        self.assertIn("[최신 세션 아님]", output.splitlines()[0])
        self.assertIn("2026-08-28", output.splitlines()[0])

    def test_explicit_session_older_than_the_latest_completed_session_fails_closed(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        code, output, files = self.run_with("--calendar", str(self.calendar), "--session", "2026-09-29", "--now",
                                            "2026-10-01T12:00:00+00:00")
        self.assertEqual(code, 0)
        review = json.loads(files[-1].read_text(encoding="utf-8"))
        self.assertIn("EVALUATION_SESSION_NOT_LATEST:2026-09-30",
                      trigger(review, "exposure_or_equity_or_v_unavailable")["reasons"])
        self.assertEqual(review["activation_candidate"]["status"], "NOT_READY")
        code, output, files = self.run_with("--calendar", str(self.calendar), "--session", "2026-09-30", "--now",
                                            "2026-10-01T12:00:01+00:00")
        review = json.loads(files[-1].read_text(encoding="utf-8"))
        self.assertEqual(review["inputs"]["evaluation_session_status"], "LATEST_COMPLETED_SESSION")
        self.assertFalse(trigger(review, "exposure_or_equity_or_v_unavailable")["active"])
        self.assertNotIn("[최신 세션 아님]", output)


class FixEPostActivationLedgerTests(unittest.TestCase):
    """e: after activation every state revision must be confirmed by a ledger entry."""

    def scenario(self) -> Scenario:
        scenario = flat_add_zone()
        scenario.journal = fx.journal(fx.activation_entry(scenario.days[0], "10000", revision=16))
        return scenario

    def assert_closed(self, review: dict[str, Any], reason: str) -> None:
        self.assertEqual(review["review_lines"]["status"], "UNVERIFIED")
        self.assertIn(reason, review["review_lines"]["reasons"])
        self.assertEqual(review["review_lines"]["hwm_usd"], "10000")  # the cash jump is not booked as a gain
        self.assertEqual(review["review_lines"]["events"], [])
        self.assertIn(reason, trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"])
        self.assertEqual(trigger(review, "undeclared_cash_flow")["reasons"],
                         ["CASH_FLOW_NOT_VERIFIABLE_WITHOUT_LEDGER_ENTRY"])
        self.assertEqual(review["recommendations"]["add"], [])

    def test_state_revision_after_activation_without_any_ledger_entry(self) -> None:
        scenario = self.scenario()
        # Revision 17 came from nowhere (no ledger): cash is 2,000 higher than at activation.
        scenario.snapshots = [fx.snapshot(scenario.days[0], {"SOXL": 30}, "9000", revision=17, from_entry=False)]
        self.assert_closed(scenario.review(), "POST_ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY:17")

    def test_missing_intermediate_revision_is_not_trusted(self) -> None:
        scenario = self.scenario()
        clear = declaration([], None, period=(scenario.days[0], EVAL))
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 30}, "7000", revision=17, from_entry=False),  # entry 17 not replayable
            fx.snapshot(scenario.days[2], {"SOXL": 30}, "9000", revision=18, block=clear, from_entry=True)]
        self.assert_closed(scenario.review(), "POST_ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY:17")

    def test_revisions_confirmed_by_ledger_entries_are_evaluated(self) -> None:
        scenario = self.scenario()
        scenario.snapshots = [
            fx.snapshot(scenario.days[0], {"SOXL": 30}, "7000", revision=16, from_entry=True),
            fx.snapshot(scenario.days[2], {"SOXL": 30}, "7000", revision=17, from_entry=True,
                        block=declaration([], None, period=(scenario.days[0], scenario.days[2]))),
            fx.snapshot("2026-09-29", {"SOXL": 30}, "7000", revision=18, from_entry=True,
                        block=declaration([], None, period=(scenario.days[2], EVAL)))]
        review = scenario.review()
        self.assertEqual(review["review_lines"]["status"], "EVALUATED")
        self.assertFalse(review["fail_closed"]["active"])

    def test_no_ledger_after_activation_is_not_a_pass_even_at_the_activation_revision(self) -> None:
        scenario = self.scenario()
        # Same revision as at activation, but nothing in a ledger confirms it (ledger deleted): +2,000 cash.
        scenario.snapshots = [fx.snapshot(scenario.days[0], {"SOXL": 30}, "9000", revision=16, from_entry=False)]
        self.assert_closed(scenario.review(), "ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY:16")

    def test_activation_cannot_be_proposed_for_a_state_without_a_ledger_entry(self) -> None:
        scenario = Scenario({"SOXL": 50}, "5000")
        scenario.journal = fx.journal(status="MISSING")
        scenario.snapshots = [fx.snapshot("2026-09-29", {"SOXL": 50}, "5000", revision=16, from_entry=True)]
        self.assertEqual(scenario.review()["activation_candidate"]["status"], "READY")
        scenario.snapshots = [fx.snapshot("2026-09-29", {"SOXL": 50}, "5000", revision=16, from_entry=False)]
        candidate = scenario.review()["activation_candidate"]
        self.assertEqual((candidate["status"], candidate["reasons"]),
                         ("NOT_READY", ["ACTIVATION_STATE_NOT_CONFIRMED_BY_LEDGER_ENTRY"]))


class FixERunnerTests(RunnerCase):
    def test_runner_without_a_ledger_after_activation_fails_closed(self) -> None:
        self.write_state({"SOXL": 30}, 9000.0, revision=17, ledger=False)  # no ledger file at all
        bench = fx.benchmark_returns(len(self.sessions))
        soxl = fx.series(self.sessions, bench, last="100", multiple=2.9)
        self.write_history("SOXX", fx.series(self.sessions, bench, last="500"))
        self.write_history("SOXL", soxl)
        entry = {"entry_type": "s5_activation", "entry_id": "a" * 64, "sequence": 1,
                 "previous_entry_sha256": "0" * 64, "confirm_code": "AAAAAAAA", "confirmation_method": "USER_TERMINAL",
                 "user_message": "AAAAAAAA", "user_confirmed_at": "2026-09-29T21:00:00Z", "review_id": "b" * 64,
                 "evaluation_session": "2026-09-29",
                 "payload": {"activation_date": "2026-09-29", "hwm_usd": "10000", "hwm_as_of": "2026-09-29",
                             "hwm_policy_initial_usd": "28473.94", "hwm_difference_usd": "-18473.94",
                             "state_revision": 16, "window_start": "2026-09-29", "window_end": "2026-09-29",
                             "close_basis": "FINAL_REGULAR_SESSION_30M_BAR_CLOSE"},
                 "order_authority": False, "quantity_authority": "none"}
        self.journal_path.write_text(json.dumps({
            "schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL", "order_authority": False,
            "quantity_authority": "none", "entries": [entry]}), encoding="utf-8")
        code, _, review = self.run_review()
        self.assertEqual(code, 0)
        self.assertEqual(review["review_lines"]["status"], "UNVERIFIED")
        self.assertEqual(review["review_lines"]["hwm_usd"], "10000")
        self.assertTrue(trigger(review, "undeclared_cash_flow")["active"])
        self.assertEqual(trigger(review, "hwm_line_or_pause_state_missing_or_corrupt")["reasons"],
                         ["ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY:16", "POST_ACTIVATION_REVISION_WITHOUT_LEDGER_ENTRY:17"])


class FixFClassificationTests(unittest.TestCase):
    """f: fee, tax and interest rows are never deposits or withdrawals."""

    def classify(self, memo: str, kind: str = "입출금") -> tuple[str, int | None]:
        return cfe.classify_row(kind, memo, cfe.load_classification())

    def test_the_two_judge_strings(self) -> None:
        self.assertEqual(self.classify("수수료출금"), ("FEE_TAX_INTEREST", None))
        self.assertEqual(self.classify("예탁금이용료입금"), ("FEE_TAX_INTEREST", None))

    def test_fee_tax_and_interest_words_are_not_external_flows(self) -> None:
        for memo in ("제세금출금", "세금출금", "이자입금",
                     "환전수수료출금", "원천징수세액출금"):
            with self.subTest(memo=memo):
                self.assertEqual(self.classify(memo), ("FEE_TAX_INTEREST", None))
        rows = [{"deal_dt": "20261002", "deal_no": f"{index:09d}", "deal_kind_nm": "입출금", "rmrk_nm": memo,
                 "fc_exct_amt": "12.34", "crnc_code": "USD"}
                for index, memo in enumerate(("수수료출금", "예탁금이용료입금"), 1)]
        evidence = cfe.normalize_transaction_history({"result": {"return_code": 0, "result_list": rows}},
                                                     period_from="2026-10-01", period_to="2026-10-05",
                                                     raw_sha256="a" * 64)
        self.assertEqual((evidence["totals"]["external_net_usd"], evidence["unresolved"]), ("0.00", []))
        self.assertEqual([row["signed_amount_usd"] for row in evidence["rows"]], [None, None])
        self.assertEqual(cfe.evidence_errors(evidence), [])
        block = cfe.build_declaration(evidence, declared_usd=None, prior_blocks=[])
        self.assertEqual(block["declaration_status"], "NO_EXTERNAL_FLOW")
        with self.assertRaisesRegex(cfe.CashFlowError, "EXCEEDS_LIMIT"):
            cfe.build_declaration(evidence, declared_usd="-12.34", prior_blocks=[])

    def test_plain_transfers_are_still_external_and_unknown_rows_still_stop(self) -> None:
        self.assertEqual(self.classify("이체입금"), ("DEPOSIT", 1))
        self.assertEqual(self.classify("이체출금"), ("WITHDRAWAL", -1))
        self.assertEqual(self.classify("배당금(외화)입금"), ("DIVIDEND", None))
        self.assertEqual(self.classify("타사대체입고", "입출고"), ("UNCLASSIFIED", None))


class FixGSettingsTests(unittest.TestCase):
    """g: Claude Code denies the new journal write command and direct edits of the journal file."""

    def test_claude_code_denies_journal_apply_and_direct_journal_edits(self) -> None:
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        deny = set(settings["permissions"]["deny"])
        for rule in ("Bash(*portfolio_review_journal.py apply*)", "PowerShell(*portfolio_review_journal.py apply*)",
                     "Edit(/stock-strategy-system/decision_journal.json)"):
            self.assertIn(rule, deny)
        for rule in ("Bash(*reconcile_broker_state.py apply*)", "PowerShell(*reconcile_broker_state.py apply*)",
                     "Edit(/stock-strategy-system/portfolio_state.json)",
                     "Edit(/stock-strategy-system/reconciliation_ledger.jsonl)",
                     "Edit(/stock-strategy-system/backups/**)", "Read(./.env)", "Read(./.env.*)",
                     "mcp__*__kiwoom_order_submit"):
            self.assertIn(rule, deny)  # existing restrictions are untouched


if __name__ == "__main__":
    unittest.main()
