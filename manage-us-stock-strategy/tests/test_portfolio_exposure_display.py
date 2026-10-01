"""S5 display line (E, distance to the next review line, pause state) in the fact pack and the card header."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_holding_fact_pack as builder  # noqa: E402
import render_holding_cards as renderer  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
import validate_holding_card as validator  # noqa: E402
from portfolio_exposure import exposure_display_block, render_exposure_line  # noqa: E402
from test_build_holding_fact_pack import (  # noqa: E402
    EXPECTED_SESSION, build, make_analysis, make_baselines, make_policy, make_state,
)
from test_holding_card import make_card  # noqa: E402
from test_portfolio_exposure import Scenario  # noqa: E402
from test_portfolio_exposure_fail_closed import line_scenario  # noqa: E402

MESSAGES = renderer.load_messages(renderer.S5_LOCALE_PATH)


def build_with(review: dict | None) -> dict:
    return builder.build_fact_pack(make_analysis(), make_state(), make_baselines(), make_policy(), None, review)


class FactPackDisplayTests(unittest.TestCase):
    def test_fact_pack_is_unchanged_without_an_exposure_review(self) -> None:
        self.assertEqual(build_with(None), build())
        self.assertNotIn("s5_exposure", build()["portfolio"])

    def test_block_is_copied_from_the_review_without_targets(self) -> None:
        review = Scenario({"MVLL": 60, "NBIS": 5, "SOXL": 40}, "2000").review()  # reduce recommendations exist
        self.assertTrue(review["recommendations"]["reduce"])
        pack = build_with(review)
        block = pack["portfolio"]["s5_exposure"]
        expected = dict(exposure_display_block(review), matches_expected_completed_session=False)
        self.assertEqual(block, expected)
        self.assertEqual(validator.forbidden_keys(pack), [])  # no order, quantity or target-weight style keys
        self.assertFalse(any("target" in key or "weight" in key or "quantity" in key for key in block))
        self.assertEqual({key: value for key, value in pack.items() if key != "portfolio"},
                         {key: value for key, value in build().items() if key != "portfolio"})
        self.assertEqual((pack["order_authority"], pack["quantity_authority"]), (False, "none"))

    def test_session_match_flag(self) -> None:
        scenario = Scenario({"SOXL": 30}, "7000")
        scenario.evaluation = EXPECTED_SESSION
        scenario.journal = fx.journal(status="MISSING")
        block = build_with(scenario.review())["portfolio"]["s5_exposure"]
        self.assertEqual((block["evaluation_session"], block["matches_expected_completed_session"]),
                         (EXPECTED_SESSION, True))

    def test_tampered_or_malformed_review_is_rejected(self) -> None:
        review = Scenario({"SOXL": 30}, "7000").review()
        changed = copy.deepcopy(review)
        changed["exposure"]["effective"] = 0.1
        for bad in (changed, {"review_id": "x"}, []):
            with self.assertRaises(builder.FactPackError) as raised:
                build_with(bad)
            self.assertEqual(str(raised.exception), "EXPOSURE_REVIEW_INVALID")


class CardHeaderTests(unittest.TestCase):
    def render(self, review: dict | None) -> str:
        card, pack = make_card(build_with(review))
        self.assertEqual(validator.validate_card(card, pack), [])
        return renderer.render_markdown(card, pack, renderer.load_messages()).split("\n\n---\n\n")[0]

    def test_header_gets_one_s5_line_only_when_the_block_exists(self) -> None:
        plain = self.render(None)
        self.assertEqual(len([line for line in plain.splitlines() if line.startswith("- **")]), 5)
        self.assertNotIn("S5", plain)
        review = Scenario({"SOXL": 30}, "7000").review()
        header = self.render(review)
        lines = [line for line in header.splitlines() if line.startswith("- **")]
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[5], "- **S5 노출:** 노출 E 0.90 · 다음 검토선 L1까지 10.0% · 권고 멈춤 없음 "
                                   "(2026-09-30 근사 종가 기준)")

    def test_line_wording_for_each_state(self) -> None:
        def line(review: dict) -> str:
            return render_exposure_line(exposure_display_block(review), MESSAGES)

        unverified = Scenario({"SOXL": 62}, "3800")
        unverified.journal = fx.journal(status="MISSING")
        self.assertEqual(line(unverified.review()), "노출 E 1.86(미확인) · 검토선 미적용(적용 시작 기록 없음) · "
                                                     "채우기·신규 매수 권고 멈춤 (2026-09-30 근사 종가 기준)")
        above = Scenario({"SOXL": 62}, "3800").review()
        self.assertIn("노출 E 1.86 · ", line(above))
        self.assertIn(" · 신규 매수 권고 멈춤 ", line(above))
        open_line = line_scenario(["100", "80", "80", "60", "60"]).review()
        self.assertIn("검토선 L1, L2 발동(검토 대기) · 채우기·신규 매수 권고 멈춤", line(open_line))
        lower_bound = Scenario({"SOXL": 70}, "3000")
        del lower_bound.closes["SOXX"]["2026-09-30"]
        self.assertIn("노출 E 미확인(최소 2.10)", line(lower_bound.review()))
        nothing = Scenario({"SOXL": 70}, "3000")
        del nothing.closes["SOXL"]["2026-09-30"]
        self.assertIn("노출 E 미확인 · 검토선 판정 보류", line(nothing.review()))

    def test_malformed_block_is_not_rendered(self) -> None:
        pack = build_with(Scenario({"SOXL": 30}, "7000").review())
        pack["portfolio"]["s5_exposure"] = {"display_only": True}
        card, pack = make_card(pack)
        with self.assertRaises(renderer.RenderError) as raised:
            renderer.render_markdown(card, pack, renderer.load_messages())
        self.assertEqual(str(raised.exception), "S5_EXPOSURE_BLOCK_INVALID")


if __name__ == "__main__":
    unittest.main()
