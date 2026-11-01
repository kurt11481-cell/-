"""coreinput: decide's docs/claude judgment inputs (R-REC1 document, M6 documents, watchlist, compare explanations).

An uncommitted, missing or linked input blocks every buy ticket and drops the redeployment candidate. Its reasons never
enter a sell gate, card_check or _plan_sell, but without the candidate a sell's regret columns, step, quantity and
swap_pair can differ or that day can have no sell ticket (CandidateCarriesTheSellTests). decide never fails because of
it and the push comes once per change. All inputs are synthetic (TEST_ONLY); no network, no Kiwoom.
"""

from __future__ import annotations

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

import test_auto_core_decide as decide_fixture  # noqa: E402
import test_auto_core_tickets as tickets_tests  # noqa: E402

decide_module = decide_fixture.decide_module
inputs = decide_fixture.inputs
tk = tickets_tests.tk
helpers = tickets_tests.helpers
Env = decide_fixture.Env
write_json = decide_fixture.write_json
DAYS = tickets_tests.DAYS

RECOVERY = "recovery-gate-R-REC1-2026-10-09.md"
M6 = "m6-relative-comparison-7stock-TEST.md"
WATCHLIST = "watchlist-registry.json"
REGISTRY = "card-evidence-registry.json"
EXPLAINED = "explained.json"
RECOVERY_LABEL = "docs/claude/" + RECOVERY
PREVIOUS_DAY = "2026-10-01"


def committed(path, repo):
    return True, None


def uncommitted(*names, reason="REGISTRY_UNCOMMITTED"):
    """A committed check that fails for the given file names only."""
    return lambda path, repo: (False, reason) if Path(path).name in names else (True, None)


def buys(decision):
    return [ticket for ticket in decision["tickets"] if ticket["side"] == "buy"]


def blocked_buy_reasons(decision, symbol="MU"):
    return [reason for item in decision["blocked"] if item["symbol"] == symbol and item["side"] == "buy"
            for reason in item["reasons"]]


def guard_of(decision):
    return decision["inputs"]["core_input_guard"]


class BuyCase(unittest.TestCase):
    """The setting that gives one MU buy ticket when nothing blocks it."""

    def setUp(self):
        self.env = Env(holdings={"SOXL": 10})
        self.addCleanup(self.env.close)
        self.env.write_good_news()

    def assert_buy_blocked(self, decision, reason):
        self.assertIn(decision["status"], ("OK", "HOLD"), decision["reasons"])
        self.assertEqual(buys(decision), [])
        self.assertIn(reason, guard_of(decision)["reasons"])
        self.assertEqual(guard_of(decision)["status"], "BLOCKED")
        self.assertIn(reason, blocked_buy_reasons(decision))
        self.assertEqual(decide_fixture.validate_instance(decision, decide_module.DECISION_SCHEMA), [])


class AllCommittedTests(BuyCase):
    def test_a_all_committed_changes_nothing(self):
        plain = self.env.run()
        checked = self.env.run(input_committed_check=committed)
        self.assertEqual(len(buys(plain)), 1, plain["blocked"])
        guard = guard_of(checked)
        self.assertEqual((guard["status"], guard["reasons"], guard["details"]), ("OK", [], {}))
        self.assertEqual(checked["tickets"], plain["tickets"])
        self.assertEqual(checked["blocked"], plain["blocked"])
        self.assertEqual(checked["reasons"], plain["reasons"])
        self.assertFalse(any(alert["code"] == "CORE_INPUT_UNCOMMITTED" for alert in checked["alerts"]))

    def test_a_guard_lists_every_input_with_its_hash(self):
        guard = guard_of(self.env.run(input_committed_check=committed))
        expected = ["docs/claude/" + name for name in (RECOVERY, M6, WATCHLIST)]
        self.assertEqual(guard["checked"], sorted(expected))
        self.assertEqual(sorted(guard["sha256"]), sorted(expected))
        self.assertTrue(all(len(value) == 64 for value in guard["sha256"].values()))


class BlockedInputTests(BuyCase):
    def test_b_uncommitted_recovery_document_blocks_buys(self):
        decision = self.env.run(input_committed_check=uncommitted(RECOVERY))
        reason = f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}"
        self.assert_buy_blocked(decision, reason)
        self.assertEqual(guard_of(decision)["details"], {RECOVERY_LABEL: "REGISTRY_UNCOMMITTED"})

    def test_c_missing_recovery_document_blocks_buys(self):
        (self.env.docs / RECOVERY).unlink()
        decision = self.env.run(input_committed_check=committed)
        self.assert_buy_blocked(decision, f"CORE_INPUT_MISSING:{RECOVERY_LABEL}")
        self.assertNotIn(RECOVERY_LABEL, guard_of(decision)["sha256"])

    def test_d_new_uncommitted_m6_file_blocks_buys(self):
        name = "m6-relative-comparison-7stock-NEW.md"
        (self.env.docs / name).write_text("MU", encoding="utf-8")
        decision = self.env.run(input_committed_check=uncommitted(name))
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:docs/claude/{name}")

    def test_d_existing_uncommitted_m6_file_blocks_buys(self):
        decision = self.env.run(input_committed_check=uncommitted(M6))
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:docs/claude/{M6}")

    def test_e_uncommitted_watchlist_blocks_buys(self):
        decision = self.env.run(input_committed_check=uncommitted(WATCHLIST))
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:docs/claude/{WATCHLIST}")

    def test_e_missing_watchlist_makes_no_guard_reason(self):
        self.env.watchlist.unlink()
        decision = self.env.run(input_committed_check=committed)
        self.assertEqual(decision["inputs"]["watchlist"]["status"], "UNREADABLE")
        self.assertEqual(guard_of(decision)["reasons"], [])
        self.assertEqual(buys(decision), [])

    def test_f_git_failure_blocks_buys_with_its_reason(self):
        decision = self.env.run(input_committed_check=uncommitted(RECOVERY, reason="REGISTRY_GIT_UNAVAILABLE"))
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
        self.assertEqual(guard_of(decision)["details"][RECOVERY_LABEL], "REGISTRY_GIT_UNAVAILABLE")

    def test_f_committed_check_exception_blocks_buys(self):
        def raises(path, repo):
            if Path(path).name == RECOVERY:
                raise RuntimeError("TEST_ONLY")
            return True, None

        decision = self.env.run(input_committed_check=raises)
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
        self.assertEqual(guard_of(decision)["details"][RECOVERY_LABEL], "RuntimeError")

    def test_f_unexpected_guard_error_blocks_buys_and_decide_does_not_fail(self):
        original = Path.glob
        seen = []

        def second_m6_glob_fails(path, pattern, *args, **kwargs):  # the first one is m6_documents, the second the guard
            if pattern.startswith(inputs.M6_PREFIX):
                seen.append(pattern)
                if len(seen) == 2:
                    raise OSError("TEST_ONLY")
            return original(path, pattern, *args, **kwargs)

        with mock.patch.object(Path, "glob", second_m6_glob_fails):
            decision = self.env.run(input_committed_check=committed)
        self.assertEqual(len(seen), 2)
        self.assertNotEqual(decision["status"], "FAIL", decision["reasons"])
        self.assert_buy_blocked(decision, "CORE_INPUT_GUARD_ERROR:OSError")

    def test_g_symbolic_link_blocks_buys_even_when_its_target_is_committed(self):
        with mock.patch.object(Path, "is_symlink", lambda path: path.name == RECOVERY):
            decision = self.env.run(input_committed_check=committed)
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
        self.assertEqual(guard_of(decision)["details"], {RECOVERY_LABEL: "SYMLINK"})

    def test_k_registry_check_is_used_when_no_input_check_is_given(self):
        decision = self.env.run(registry_committed_check=uncommitted(RECOVERY))
        self.assertTrue(decision["inputs"]["registry"]["committed"])
        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")

    def test_guard_reason_stays_out_of_the_gates_and_the_decision_reasons(self):
        decision = self.env.run(input_committed_check=uncommitted(RECOVERY))
        self.assertEqual([reason for reason in decision["reasons"] if reason.startswith("CORE_INPUT")], [])

    def test_guard_runs_before_the_research_wait(self):
        order = []
        original = decide_module._wait_for_research

        def wait(*args):
            order.append("wait")
            return original(*args)

        def check(path, repo):
            order.append(Path(path).name)
            return True, None

        with mock.patch.object(decide_module, "_wait_for_research", wait):
            self.env.run(input_committed_check=check)
        self.assertEqual(order[:3], [RECOVERY, WATCHLIST, M6])
        self.assertEqual(order[3], "wait")


class ExplainedFileTests(BuyCase):
    def explained_path(self):
        path = self.env.root / EXPLAINED
        write_json(path, {"schema_version": "redesign-t2-compare-explained-1.0", "items": []})
        return path

    def test_h_uncommitted_explanation_only_changes_the_compare_block(self):
        base = self.env.run(input_committed_check=committed)
        self.explained_path()
        decision = self.env.run(input_committed_check=uncommitted(EXPLAINED))
        self.assertEqual(decision["compare"]["explained_errors"], ["EXPLAINED_FILE_UNCOMMITTED"])
        self.assertEqual(decision["tickets"], base["tickets"])
        self.assertEqual(decision["blocked"], base["blocked"])
        self.assertEqual(guard_of(decision)["reasons"], [])

    def test_h_committed_or_absent_explanation_stays_as_before(self):
        self.assertEqual(self.env.run(input_committed_check=uncommitted(EXPLAINED))["compare"]["explained_errors"], [])
        self.explained_path()
        self.assertEqual(self.env.run(input_committed_check=committed)["compare"]["explained_errors"], [])

    def test_h_uncommitted_explanation_explains_nothing_and_keeps_the_load_errors(self):
        (self.env.root / EXPLAINED).write_text("{broken", encoding="utf-8")
        decision = self.env.run(input_committed_check=uncommitted(EXPLAINED))
        self.assertEqual(decision["compare"]["explained_errors"],
                         ["EXPLAINED_FILE_UNCOMMITTED", "EXPLAINED_FILE_UNREADABLE"])

    def test_h_link_or_check_exception_counts_as_uncommitted(self):
        path = self.explained_path()
        with mock.patch.object(Path, "is_symlink", lambda item: item.name == EXPLAINED):
            self.assertEqual(decide_module._committed_explained(path, committed, self.env.root),
                             ([], ["EXPLAINED_FILE_UNCOMMITTED"]))

        def raises(item, repo):
            raise RuntimeError("TEST_ONLY")

        self.assertEqual(decide_module._committed_explained(path, raises, self.env.root),
                         ([], ["EXPLAINED_FILE_UNCOMMITTED"]))

    def test_h_no_new_session_day_uses_the_same_check(self):
        self.explained_path()
        first = self.env.run(input_committed_check=committed)
        first.update(run_day_kst=PREVIOUS_DAY, f6_ran=True)  # the same evaluation session: nothing new today
        (self.env.output / PREVIOUS_DAY).mkdir()
        write_json(self.env.output / PREVIOUS_DAY / "decision.json", first)
        decision = self.env.run(input_committed_check=uncommitted(EXPLAINED))
        self.assertTrue(decision["no_new_session"])
        self.assertEqual(decision["compare"]["explained_errors"], ["EXPLAINED_FILE_UNCOMMITTED"])


class AlertTests(BuyCase):
    LINE = ("자동 코어 입력 문서 미커밋 — 매수 주문표 막힘·재배치 후보 빠짐(매도는 후보 없는 날처럼 계산): "
            f"{RECOVERY_LABEL} — Cowork 커밋 확인")

    def setUp(self):
        super().setUp()
        self.base = self.env.run(input_committed_check=committed)
        (self.env.output / PREVIOUS_DAY).mkdir()

    def alerts_after(self, previous_reasons):
        record = decide_fixture._as_of(copy.deepcopy(self.base), PREVIOUS_DAY)  # an earlier session: a new one today
        record["inputs"]["core_input_guard"]["reasons"] = previous_reasons
        write_json(self.env.output / PREVIOUS_DAY / "decision.json", record)
        decision = self.env.run(input_committed_check=uncommitted(RECOVERY))
        self.assertFalse(decision["no_new_session"])
        self.assertEqual(buys(decision), [])
        return [alert for alert in decision["alerts"] if alert["code"] == "CORE_INPUT_UNCOMMITTED"]

    def test_i_first_day_pushes_once(self):
        self.assertEqual(self.alerts_after([]),
                         [{"code": "CORE_INPUT_UNCOMMITTED", "line": self.LINE, "push": True}])

    def test_i_same_reasons_as_the_previous_record_do_not_push(self):
        self.assertEqual(self.alerts_after([f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}"]), [])

    def test_i_changed_reasons_push_again(self):
        alerts = self.alerts_after(["CORE_INPUT_UNCOMMITTED:docs/claude/other.md"])
        self.assertEqual([alert["push"] for alert in alerts], [True])

    def test_l_first_day_line_names_the_candidate_and_not_the_old_wording(self):
        line = self.alerts_after([])[0]["line"]
        self.assertIn("재배치 후보", line)
        self.assertNotIn("매도 그대로", line)


def plan_ctx(ranked, **extra):
    return {"symbols": {}, "checks": {"A": {"entry": {"card_action": "EXIT"}}, "B": {"entry": {"card_action": "HOLD"}}},
            "review": {}, "s7": {}, "holdings": {"A": 10, "B": 5}, "equity": Decimal("10000"), "weights": {},
            "closes": {}, "sigmas": {}, "config": {}, "gate0": {"ok": False, "reasons": ["G0_TEST"]},
            "gate1": {"ok": True, "reasons": []}, "buy_rows": [], "data_reasons": {}, "run_day": "2026-10-10",
            "evidence": {symbol: {"sell": {"basis_met": True, "r_max": "1/3"}} for symbol in ("A", "B")},
            "redeploy_ranked": ranked, **extra}


def sell_results(planned):
    return ([ticket for ticket in planned["tickets"] if ticket["side"] == "sell"],
            [item for item in planned["blocked"] if item["side"] == "sell"])


class RedeployCandidateTests(unittest.TestCase):
    RANKED = [{"symbol": "A", "up": 0.1, "down": -0.1}, {"symbol": "B", "up": 0.2, "down": -0.2}]

    def test_j_input_block_drops_the_candidate_and_sells_as_on_a_day_without_candidates(self):
        blocked = plan_ctx(self.RANKED, input_block=["CORE_INPUT_UNCOMMITTED:x"])
        planned = tk.plan(blocked)
        self.assertIsNone(blocked["redeploy_candidate"])
        self.assertEqual(sell_results(planned), sell_results(tk.plan(plan_ctx([]))))

    def test_j_without_input_block_the_candidate_stays(self):
        for extra in ({}, {"input_block": []}):
            ctx = plan_ctx(self.RANKED, **extra)
            tk.plan(ctx)
            self.assertEqual(ctx["redeploy_candidate"], self.RANKED[1])

    def test_j_replay_without_a_ranking_gets_no_candidate_key_unless_blocked(self):
        ctx = plan_ctx(None)
        tk.plan(ctx)
        self.assertNotIn("redeploy_candidate", ctx)

    def test_j_a_real_sell_ticket_is_the_one_issued_without_a_candidate(self):
        def scenario():
            item = tickets_tests.Scenario(holdings={"SOXL": 400}, cash="3000")
            item.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.falling_soxl())
            return item

        original = decide_module.evaluate_session

        def with_block(**kwargs):
            return original(**kwargs, input_block=["CORE_INPUT_UNCOMMITTED:x"])

        with mock.patch.object(decide_module, "redeploy_ranking", return_value=[]):
            without_candidates = scenario().run()
        with mock.patch.object(decide_module, "evaluate_session", side_effect=with_block):
            blocked = scenario().run()
        sells = tickets_tests.tickets_of(blocked, "SOXL", "sell")
        self.assertEqual(len(sells), 1, blocked["planned"]["blocked"])
        self.assertEqual(sell_results(blocked["planned"]), sell_results(without_candidates["planned"]))
        self.assertEqual(sells[0]["regret"]["columns"], ["up:cash", "down:cash"])


class CandidateCarriesTheSellTests(unittest.TestCase):
    """The candidate's columns can be what issues a sell: without them (a guard block or a day without a candidate)
    the same numbers choose step 0, so that day has no sell ticket."""

    CANDIDATE = {"symbol": "MU", "up": 0.6, "down": -0.01}

    def result(self, ranked, input_block=()):
        scenario = tickets_tests.Scenario(holdings={"SOXL": 400}, cash="3000")
        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.falling_soxl())
        original = tk.plan

        def shaped(ctx):
            ctx["scenarios"]["SOXL"].update(up=0.3, down=-0.01)
            ctx["evidence"]["SOXL"]["sell"]["r_max"] = "1/3"
            ctx.update(redeploy_ranked=ranked, input_block=list(input_block))
            return original(ctx)

        with mock.patch.object(tk, "plan", shaped):
            return scenario.run()

    def test_candidate_issues_one_third_and_a_guard_block_ends_in_regret_zero(self):
        issued = self.result([self.CANDIDATE])
        sells = tickets_tests.tickets_of(issued, "SOXL", "sell")
        self.assertEqual(len(sells), 1, issued["planned"]["blocked"])
        self.assertEqual(sells[0]["regret"]["chosen"], "1/3")
        self.assertEqual(sells[0]["regret"]["columns"], ["up:cash", "down:cash", "up:MU", "down:MU"])
        guarded = self.result([self.CANDIDATE], input_block=["CORE_INPUT_UNCOMMITTED:x"])
        self.assertEqual(tickets_tests.tickets_of(guarded, "SOXL", "sell"), [])
        self.assertEqual(tickets_tests.blocked_reasons(guarded, "SOXL", "sell"), ["REGRET_ZERO"])
        self.assertEqual(sell_results(guarded["planned"]), sell_results(self.result([])["planned"]))


class SellThroughDecideTests(unittest.TestCase):
    def env(self):
        env = Env(holdings={"SOXL": 400}, cash="3000", soxl_closes=tickets_tests.falling_soxl())
        self.addCleanup(env.close)
        return env

    def test_a_sell_that_needs_no_candidate_gets_its_ticket_with_its_hold_range(self):
        decision = self.env().run(input_committed_check=uncommitted(RECOVERY, M6, WATCHLIST))
        self.assertEqual(guard_of(decision)["status"], "BLOCKED")
        sells = [ticket for ticket in decision["tickets"] if ticket["side"] == "sell"]
        self.assertEqual(len(sells), 1, decision["blocked"])
        self.assertEqual(sells[0]["priceCalc"]["hold"]["status"], "ok")
        self.assertEqual(sells[0]["regret"]["columns"], ["up:cash", "down:cash"])
        self.assertEqual(buys(decision), [])
        plain = self.env().run()
        self.assertEqual([(ticket["ticker"], ticket["side"]) for ticket in plain["tickets"] if ticket["side"] == "sell"],
                         [(sells[0]["ticker"], "sell")])


if __name__ == "__main__":
    unittest.main()
