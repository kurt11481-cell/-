from __future__ import annotations

import copy
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import portfolio_decision_dashboard as dashboard  # noqa: E402
import render_holding_cards as renderer  # noqa: E402
import validate_holding_card as validator  # noqa: E402
from build_holding_fact_pack import fact_pack_hash  # noqa: E402
from test_build_holding_fact_pack import (  # noqa: E402
    DECISION_AS_OF, RUN_ID, build, make_analysis, release_analysis,
)
from validation_common import audit_schema_dialect, load_json, validate_instance  # noqa: E402

SCHEMA_PATH = SKILL_ROOT / "schemas/holding-card.schema.json"
PLAN_SCHEMA_PATH = SKILL_ROOT / "schemas/portfolio-decision-plan.schema.json"
DEFAULT_ACTIONS = {"AAA": "TRIM", "BBB": "HOLD"}


def make_position(pack: dict, ticker: str, action: str | None = None, **overrides: object) -> dict:
    action = action or DEFAULT_ACTIONS[ticker]
    position: dict = {
        "ticker": ticker,
        "action": action,
        "conviction": "LOW",
        "rationale": "one line reason",
        "rule_result": "rule note",
        "rule_agreement": "SAME",
        "cash_and_alternatives": "cash note",
        "numbers": copy.deepcopy(pack["tickers"][ticker]["display"]),
        "thesis": {"statement": "thesis", "status": "VALID", "change_vs_previous": "no change"},
        "thesis_kill": False,
        "material_risk": "strongest counter case",
        "kill_criteria": {"conditions": ["close <= boundary"], "current_distance": "far"},
        "next_event": "2026-10-06 investor day",
        "change_conditions": ["if X then TRIM"],
        "data_status": {"summary": "grade UNVERIFIED", "missing": []},
        "past_performance": "n/a",
    }
    if action == "TRIM":
        position["reason_tag"] = "TRIM_CONCENTRATION"
    elif action == "EXIT":
        position["reason_tag"] = "EXIT_THESIS"
    elif action == "HOLD":
        position["review_required"] = False
    position.update(overrides)
    return position


def bind(card: dict, pack: dict) -> dict:
    card["evidence_binding"] = {"expected_run_id": RUN_ID, "expected_decision_as_of": DECISION_AS_OF}
    card["fact_pack_sha256"] = fact_pack_hash(pack)
    return card


def make_card(pack: dict | None = None, positions: list[dict] | None = None) -> tuple[dict, dict]:
    pack = pack if pack is not None else build()
    card = {
        "card_id": "card-2026-09-30",
        "as_of": DECISION_AS_OF,
        "header": {
            "conclusion_primary": "c1",
            "conclusion_secondary": "c2",
            "status": "s",
            "exposure": "e",
            "upcoming_events": "u",
        },
        "positions": positions if positions is not None else [make_position(pack, t) for t in sorted(pack["tickers"])],
    }
    return bind(card, pack), pack


def position_of(card: dict, ticker: str) -> dict:
    return next(item for item in card["positions"] if item["ticker"] == ticker)


class AcceptedCardTests(unittest.TestCase):
    def test_valid_card_is_accepted_and_schema_valid(self) -> None:
        card, pack = make_card()
        self.assertEqual(validator.validate_card(card, pack), [])
        self.assertEqual(validate_instance(card, SCHEMA_PATH), [])

    def test_every_action_is_accepted_when_it_is_labeled(self) -> None:
        for ticker, action in (("AAA", "EXIT"), ("AAA", "TRIM"), ("BBB", "HOLD")):
            with self.subTest(ticker=ticker, action=action):
                card, pack = make_card()
                card["positions"] = [make_position(pack, "AAA", "TRIM"), make_position(pack, "BBB", "HOLD")]
                card["positions"][0 if ticker == "AAA" else 1] = make_position(pack, ticker, action)
                self.assertEqual(validator.validate_card(card, pack), [])
        card, pack = make_card()
        card["positions"] = [
            make_position(pack, "AAA", "ADD", rule_agreement="DIFFERENT", rule_disagreement_reason="why"),
            make_position(pack, "BBB", "HOLD"),
        ]
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_card_is_accepted_at_a_different_time_format_for_the_same_instant(self) -> None:
        card, pack = make_card()
        card["evidence_binding"]["expected_decision_as_of"] = "2026-09-30T11:21:14.980095Z"
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_optional_market_environment(self) -> None:
        card, pack = make_card()
        card["header"]["market_environment"] = {"status": "SAVE_NOT_RECEIVED", "label": "EXTERNAL_REFERENCE", "lines": []}
        self.assertEqual(validator.validate_card(card, pack), [])
        card["header"]["market_environment"] = {"status": "SAVE_PROVIDED", "label": "EXTERNAL_REFERENCE", "lines": ["x"]}
        self.assertEqual(validator.validate_card(card, pack), [])
        card["header"]["market_environment"]["lines"] = []
        self.assertEqual(validator.validate_card(card, pack), ["MARKET_ENVIRONMENT_LINES_MISSING"])
        card["header"]["market_environment"] = {"status": "SAVE_PROVIDED", "label": "OTHER", "lines": ["x"]}
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in validator.validate_card(card, pack)))


class Rejection1OrderFieldTests(unittest.TestCase):
    NAMES = (
        "order_intent_terms", "proposed_quantity", "limit_price", "target_weight_pct", "plan_status",
        "order_quantity", "execution_quantity", "buy_quantity", "sell_shares", "trade_amount",
        "target_position_size", "order_type", "time_in_force", "stop_price",
    )

    def test_forbidden_names_are_rejected_at_every_depth(self) -> None:
        for name in self.NAMES:
            for place in ("root", "position", "numbers", "header"):
                with self.subTest(name=name, place=place):
                    card, pack = make_card()
                    target = {
                        "root": card, "position": card["positions"][0],
                        "numbers": card["positions"][0]["numbers"], "header": card["header"],
                    }[place]
                    target[name] = 1
                    errors = validator.validate_card(card, pack)
                    self.assertTrue(any(item.startswith("ORDER_FIELD_FORBIDDEN:") and item.endswith("." + name) for item in errors), errors)

    def test_forbidden_name_inside_a_list_of_objects_is_found(self) -> None:
        card, pack = make_card()
        card["header"]["market_environment"] = {
            "status": "SAVE_PROVIDED", "label": "EXTERNAL_REFERENCE", "lines": [{"proposed_quantity": 5}],
        }
        errors = validator.validate_card(card, pack)
        self.assertTrue(any("lines[0].proposed_quantity" in item for item in errors), errors)

    def test_korean_order_key_is_rejected(self) -> None:
        card, pack = make_card()
        card["positions"][0][chr(0xC8FC) + chr(0xBB38) + chr(0xC218) + chr(0xB7C9)] = 1
        self.assertTrue(any(item.startswith("ORDER_FIELD_FORBIDDEN") for item in validator.validate_card(card, pack)))

    def test_display_only_and_fact_names_are_not_flagged(self) -> None:
        for name in ("held_quantity", "weight_pct", "loss_limit_remaining_pct", "loss_limit_boundary_usd",
                     "market_value_usd", "mark_price_usd", "review_required", "reason_tag", "rule_agreement"):
            with self.subTest(name=name):
                self.assertFalse(validator.is_forbidden_key(name))
        card, _ = make_card()
        self.assertEqual(validator.forbidden_keys(card), [])

    def test_schema_itself_defines_none_of_the_forbidden_fields(self) -> None:
        def names(node: object) -> list[str]:
            found: list[str] = []
            if isinstance(node, dict):
                for key, child in node.items():
                    if key == "properties" and isinstance(child, dict):
                        found.extend(child.keys())
                    found.extend(names(child))
            elif isinstance(node, list):
                for child in node:
                    found.extend(names(child))
            return found

        defined = names(load_json(SCHEMA_PATH))
        self.assertTrue(defined)
        for name in defined:
            self.assertFalse(validator.is_forbidden_key(name), name)
        for name in ("order_intent_terms", "proposed_quantity", "limit_price", "target_weight_pct", "plan_status"):
            self.assertNotIn(name, defined)

    def test_schema_uses_the_plan_field_names_it_borrows(self) -> None:
        plan, card = load_json(PLAN_SCHEMA_PATH), load_json(SCHEMA_PATH)
        self.assertEqual(
            card["properties"]["evidence_binding"]["properties"].keys(),
            plan["properties"]["evidence_binding"]["properties"].keys(),
        )
        plan_fields = plan["properties"]["positions"]["items"]["properties"]
        card_fields = card["properties"]["positions"]["items"]["properties"]
        for name in ("action", "rationale", "thesis_kill", "material_risk"):
            self.assertIn(name, plan_fields)
            self.assertIn(name, card_fields)
        self.assertEqual(audit_schema_dialect(card), [])


class Rejection2EmptyJudgmentTests(unittest.TestCase):
    def test_blank_rationale_is_rejected(self) -> None:
        for value in ("", "   ", "\n\t"):
            with self.subTest(value=repr(value)):
                card, pack = make_card()
                card["positions"][0]["rationale"] = value
                self.assertIn("JUDGMENT_EMPTY:AAA", validator.validate_card(card, pack))

    def test_blank_or_missing_action_and_conviction_are_rejected(self) -> None:
        for field in ("action", "conviction", "rationale"):
            for change in ("blank", "missing", "null"):
                with self.subTest(field=field, change=change):
                    card, pack = make_card()
                    if change == "blank":
                        card["positions"][0][field] = " "
                    elif change == "missing":
                        del card["positions"][0][field]
                    else:
                        card["positions"][0][field] = None
                    self.assertIn("JUDGMENT_EMPTY:AAA", validator.validate_card(card, pack))

    def test_whitespace_rationale_alone_fails_only_for_that_reason(self) -> None:
        card, pack = make_card()
        card["positions"][1]["rationale"] = "   "
        self.assertEqual(validator.validate_card(card, pack), ["JUDGMENT_EMPTY:BBB"])


class Rejection3WithholdTests(unittest.TestCase):
    def test_withhold_is_rejected_when_the_fact_pack_does_not_allow_it(self) -> None:
        for reason in ("BROKER_UNAVAILABLE", "IDENTITY_UNVERIFIED"):
            with self.subTest(reason=reason):
                card, pack = make_card()
                card["positions"][0] = make_position(pack, "AAA", "WITHHELD", withheld_reason=reason)
                self.assertEqual(validator.validate_card(card, pack), ["WITHHOLD_NOT_ALLOWED:AAA"])

    def test_withhold_without_a_reason_or_with_an_unknown_reason_is_rejected(self) -> None:
        card, pack = make_card()
        card["positions"][0] = make_position(pack, "AAA", "WITHHELD")
        self.assertEqual(validator.validate_card(card, pack), ["WITHHOLD_NOT_ALLOWED:AAA"])
        card["positions"][0]["withheld_reason"] = "TOO_UNCERTAIN"
        errors = validator.validate_card(card, pack)
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in errors), errors)

    def test_withheld_reason_on_a_normal_action_is_rejected(self) -> None:
        card, pack = make_card()
        card["positions"][0]["withheld_reason"] = "BROKER_UNAVAILABLE"
        self.assertEqual(validator.validate_card(card, pack), ["WITHHOLD_NOT_ALLOWED:AAA"])

    def test_broker_unavailable_allows_withhold(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["status"] = "UNAVAILABLE"
        analysis["broker_observed_state"]["holdings"] = []
        pack = build(analysis)
        card, _ = make_card(pack, [
            make_position(pack, "AAA", "WITHHELD", withheld_reason="BROKER_UNAVAILABLE"),
            make_position(pack, "BBB", "WITHHELD", withheld_reason="BROKER_UNAVAILABLE"),
        ])
        self.assertEqual(validator.validate_card(card, pack), [])
        card["positions"][0]["withheld_reason"] = "IDENTITY_UNVERIFIED"
        self.assertEqual(validator.validate_card(card, pack), ["WITHHOLD_NOT_ALLOWED:AAA"])

    def test_identity_unverified_allows_withhold_only_for_that_ticker(self) -> None:
        analysis = make_analysis()
        analysis["last_verified_finalized_bars"][0]["identity_authority_status"] = "NOT_VERIFIED"
        pack = build(analysis)
        card, _ = make_card(pack, [
            make_position(pack, "AAA", "WITHHELD", withheld_reason="IDENTITY_UNVERIFIED"),
            make_position(pack, "BBB", "WITHHELD", withheld_reason="IDENTITY_UNVERIFIED"),
        ])
        self.assertEqual(validator.validate_card(card, pack), ["WITHHOLD_NOT_ALLOWED:BBB"])


class Rejection4RuleDisagreementTests(unittest.TestCase):
    def test_action_against_the_rule_direction_needs_a_label_and_reason(self) -> None:
        card, pack = make_card()
        card["positions"][0] = make_position(pack, "AAA", "HOLD")  # rule: REDUCE
        self.assertEqual(validator.validate_card(card, pack), ["RULE_DISAGREEMENT_UNLABELED:AAA"])
        card["positions"][0]["rule_agreement"] = "DIFFERENT"
        self.assertEqual(validator.validate_card(card, pack), ["RULE_DISAGREEMENT_UNLABELED:AAA"])
        card["positions"][0]["rule_disagreement_reason"] = "   "
        self.assertEqual(validator.validate_card(card, pack), ["RULE_DISAGREEMENT_UNLABELED:AAA"])
        card["positions"][0]["rule_disagreement_reason"] = "specific reason"
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_add_against_reduce_and_trim_or_exit_against_hold_are_unlabeled(self) -> None:
        card, pack = make_card()
        card["positions"][0] = make_position(pack, "AAA", "ADD")
        self.assertEqual(validator.validate_card(card, pack), ["RULE_DISAGREEMENT_UNLABELED:AAA"])
        for action in ("TRIM", "EXIT", "ADD"):
            with self.subTest(action=action):
                card, pack = make_card()
                card["positions"][1] = make_position(pack, "BBB", action)  # rule: HOLD
                self.assertEqual(validator.validate_card(card, pack), ["RULE_DISAGREEMENT_UNLABELED:BBB"])

    def test_claiming_a_difference_that_does_not_exist_is_rejected(self) -> None:
        card, pack = make_card()
        card["positions"][0]["rule_agreement"] = "DIFFERENT"
        card["positions"][0]["rule_disagreement_reason"] = "reason"
        self.assertEqual(validator.validate_card(card, pack), ["RULE_AGREEMENT_LABEL_MISMATCH:AAA"])

    def test_breach_makes_the_rule_direction_reduce(self) -> None:
        analysis = make_analysis()
        analysis["historical_daily_evidence"][1]["records"][-1]["price"] = 80.0  # BBB boundary 80
        pack = build(analysis)
        card, _ = make_card(pack, [make_position(pack, "AAA", "TRIM"), make_position(pack, "BBB", "HOLD")])
        self.assertEqual(validator.validate_card(card, pack), ["RULE_DISAGREEMENT_UNLABELED:BBB"])

    def test_no_rule_direction_means_nothing_to_oppose(self) -> None:
        from test_build_holding_fact_pack import make_policy
        policy = make_policy()
        del policy["holding_risk_rules"]["positions"]["BBB"]
        pack = build(policy=policy)
        card, _ = make_card(pack, [make_position(pack, "AAA", "TRIM"), make_position(pack, "BBB", "EXIT")])
        self.assertEqual(validator.validate_card(card, pack), [])


class Rejection5ConvictionCapTests(unittest.TestCase):
    def test_conviction_above_the_cap_is_rejected(self) -> None:
        for conviction in ("MEDIUM", "HIGH"):
            with self.subTest(conviction=conviction):
                card, pack = make_card()
                card["positions"][0]["conviction"] = conviction
                self.assertEqual(validator.validate_card(card, pack), ["CONVICTION_CAP_VIOLATION:AAA"])

    def test_released_cap_allows_high_conviction(self) -> None:
        pack = build(release_analysis())
        card, _ = make_card(pack)
        for position in card["positions"]:
            position["conviction"] = "HIGH"
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_missing_cap_in_the_fact_pack_fails_closed(self) -> None:
        pack = build(release_analysis())
        del pack["status"]["confidence_cap"]
        card, _ = make_card(pack)
        card["positions"][0]["conviction"] = "MEDIUM"
        self.assertEqual(validator.validate_card(card, pack), ["CONVICTION_CAP_VIOLATION:AAA"])
        card["positions"][0]["conviction"] = "LOW"
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_unreleased_conditions_keep_high_conviction_rejected(self) -> None:
        for change in ({"preflight_status": "FAIL"}, {"broker_diff_status": "DIFFERENT"}, {"evidence_grade": "GRADE_Z"}):
            with self.subTest(change=change):
                analysis = release_analysis()
                analysis.update(change)
                pack = build(analysis)
                card, _ = make_card(pack)
                card["positions"][0]["conviction"] = "HIGH"
                self.assertEqual(validator.validate_card(card, pack), ["CONVICTION_CAP_VIOLATION:AAA"])


class Rejection6NumberMismatchTests(unittest.TestCase):
    def test_each_number_field_must_match_the_fact_pack(self) -> None:
        for field in validator.NUMBER_FIELDS:
            with self.subTest(field=field):
                card, pack = make_card()
                original = card["positions"][0]["numbers"][field]
                card["positions"][0]["numbers"][field] = 12345.5 if original != 12345.5 else 1
                self.assertEqual(validator.validate_card(card, pack), [f"NUMBER_MISMATCH:AAA:{field}"])

    def test_null_versus_value_is_a_mismatch(self) -> None:
        card, pack = make_card()
        card["positions"][0]["numbers"]["weight_pct"] = None
        self.assertEqual(validator.validate_card(card, pack), ["NUMBER_MISMATCH:AAA:weight_pct"])

    def test_pack_null_requires_card_null(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["status"] = "INCOMPLETE"
        analysis["broker_observed_state"]["holdings"] = []
        pack = build(analysis)
        card, _ = make_card(pack)
        self.assertEqual(validator.validate_card(card, pack), [])
        card["positions"][0]["numbers"]["held_quantity"] = 100
        self.assertEqual(validator.validate_card(card, pack), ["NUMBER_MISMATCH:AAA:held_quantity"])

    def test_rounding_drift_is_a_mismatch_and_equal_int_float_is_not(self) -> None:
        card, pack = make_card()
        card["positions"][0]["numbers"]["weight_pct"] = 41.90001
        self.assertEqual(validator.validate_card(card, pack), ["NUMBER_MISMATCH:AAA:weight_pct"])
        card["positions"][0]["numbers"]["weight_pct"] = pack["tickers"]["AAA"]["display"]["weight_pct"]
        card["positions"][0]["numbers"]["held_quantity"] = 100.0
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_missing_number_field_is_rejected_by_schema(self) -> None:
        card, pack = make_card()
        del card["positions"][0]["numbers"]["weight_pct"]
        errors = validator.validate_card(card, pack)
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in errors), errors)


class Rejection7BindingTests(unittest.TestCase):
    def test_run_id_mismatch(self) -> None:
        card, pack = make_card()
        card["evidence_binding"]["expected_run_id"] = "manual-other-run-id-000000"
        self.assertEqual(validator.validate_card(card, pack), ["RUN_ID_MISMATCH"])

    def test_as_of_mismatch(self) -> None:
        card, pack = make_card()
        card["evidence_binding"]["expected_decision_as_of"] = "2026-09-30T11:21:15.980095+00:00"
        self.assertEqual(validator.validate_card(card, pack), ["AS_OF_MISMATCH"])
        card["evidence_binding"]["expected_decision_as_of"] = "2026-09-30T20:21:14.980095+09:00"
        self.assertEqual(validator.validate_card(card, pack), [])

    def test_fact_pack_changed_after_the_card_was_bound(self) -> None:
        card, pack = make_card()
        pack["portfolio"]["cash_weight_pct"] = 9.99
        self.assertEqual(validator.validate_card(card, pack), ["FACT_PACK_HASH_MISMATCH"])

    def test_missing_binding_fields_are_rejected_by_schema(self) -> None:
        card, pack = make_card()
        del card["evidence_binding"]["expected_run_id"]
        errors = validator.validate_card(card, pack)
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in errors), errors)

    def test_invalid_fact_pack_is_reported(self) -> None:
        card, pack = make_card()
        pack["order_authority"] = True
        errors = validator.validate_card(card, pack)
        self.assertTrue(any(item.startswith("FACT_PACK_INVALID") for item in errors), errors)
        self.assertTrue(any(item.startswith("FACT_PACK_INVALID") for item in validator.validate_card(card, {})))


class ReasonTagAndHoldFlagTests(unittest.TestCase):
    def test_trim_and_exit_require_one_reason_tag(self) -> None:
        for action, ticker in (("TRIM", "AAA"), ("EXIT", "AAA")):
            with self.subTest(action=action):
                card, pack = make_card()
                card["positions"][0] = make_position(pack, ticker, action)
                del card["positions"][0]["reason_tag"]
                self.assertIn(f"REASON_TAG_MISSING:{ticker}", validator.validate_card(card, pack))

    def test_trim_accepts_only_trim_tags_and_exit_only_exit_tags(self) -> None:
        for tag in sorted(validator.TRIM_TAGS):
            with self.subTest(trim=tag):
                card, pack = make_card()
                card["positions"][0]["reason_tag"] = tag
                self.assertEqual(validator.validate_card(card, pack), [])
        for tag in sorted(validator.EXIT_TAGS):
            with self.subTest(exit=tag):
                card, pack = make_card()
                card["positions"][0] = make_position(pack, "AAA", "EXIT", reason_tag=tag)
                self.assertEqual(validator.validate_card(card, pack), [])
        card, pack = make_card()
        card["positions"][0]["reason_tag"] = "EXIT_THESIS"
        self.assertEqual(validator.validate_card(card, pack), ["REASON_TAG_INVALID:AAA"])
        card["positions"][0] = make_position(pack, "AAA", "EXIT", reason_tag="TRIM_RISK")
        self.assertEqual(validator.validate_card(card, pack), ["REASON_TAG_INVALID:AAA"])

    def test_unknown_tag_is_rejected_by_schema(self) -> None:
        card, pack = make_card()
        card["positions"][0]["reason_tag"] = "TRIM_WHATEVER"
        errors = validator.validate_card(card, pack)
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in errors), errors)

    def test_tag_is_not_allowed_on_add_hold_or_withheld(self) -> None:
        card, pack = make_card()
        card["positions"][1]["reason_tag"] = "TRIM_RISK"
        self.assertEqual(validator.validate_card(card, pack), ["REASON_TAG_NOT_ALLOWED:BBB"])
        card["positions"][0] = make_position(
            pack, "AAA", "ADD", reason_tag="TRIM_RISK", rule_agreement="DIFFERENT", rule_disagreement_reason="r"
        )
        self.assertIn("REASON_TAG_NOT_ALLOWED:AAA", validator.validate_card(card, pack))

    def test_hold_requires_a_boolean_review_flag(self) -> None:
        card, pack = make_card()
        del card["positions"][1]["review_required"]
        self.assertEqual(validator.validate_card(card, pack), ["HOLD_REVIEW_FLAG_MISSING:BBB"])
        card["positions"][1]["review_required"] = True
        self.assertEqual(validator.validate_card(card, pack), [])
        card["positions"][1]["review_required"] = "yes"
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in validator.validate_card(card, pack)))

    def test_review_flag_is_not_allowed_outside_hold(self) -> None:
        card, pack = make_card()
        card["positions"][0]["review_required"] = False
        self.assertEqual(validator.validate_card(card, pack), ["HOLD_REVIEW_FLAG_NOT_ALLOWED:AAA"])
        card["positions"][0] = make_position(
            pack, "AAA", "ADD", review_required=True, rule_agreement="DIFFERENT", rule_disagreement_reason="r"
        )
        self.assertIn("HOLD_REVIEW_FLAG_NOT_ALLOWED:AAA", validator.validate_card(card, pack))

    def test_ticker_set_must_match_the_fact_pack(self) -> None:
        card, pack = make_card()
        card["positions"].pop()
        self.assertEqual(validator.validate_card(card, pack), ["TICKER_SET_MISMATCH"])
        card, pack = make_card()
        card["positions"][1] = copy.deepcopy(card["positions"][0])
        self.assertEqual(validator.validate_card(card, pack), ["TICKER_SET_MISMATCH"])
        card, pack = make_card()
        extra = make_position(pack, "BBB")
        extra["ticker"] = "CCC"
        card["positions"].append(extra)
        self.assertEqual(validator.validate_card(card, pack), ["TICKER_SET_MISMATCH"])


class ValidatorCliTests(unittest.TestCase):
    def test_cli_pass_and_fail_exit_codes(self) -> None:
        card, pack = make_card()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "pack.json").write_text(json.dumps(pack), encoding="utf-8")
            (root / "card.json").write_text(json.dumps(card), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = validator.main(["--card", str(root / "card.json"), "--fact-pack", str(root / "pack.json")])
            self.assertEqual((code, json.loads(buffer.getvalue())["status"]), (0, "PASS"))
            card["evidence_binding"]["expected_run_id"] = "manual-other-run-id-000000"
            (root / "card.json").write_text(json.dumps(card), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = validator.main(["--card", str(root / "card.json"), "--fact-pack", str(root / "pack.json")])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(buffer.getvalue())["errors"], ["RUN_ID_MISMATCH"])
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = validator.main(["--card", str(root / "missing.json"), "--fact-pack", str(root / "pack.json")])
            self.assertEqual(code, 2)


def minimal_plan(with_order_terms: bool = False) -> dict:
    position: dict = {
        "ticker": "AAA", "action": "HOLD", "rationale": "r", "investment_horizon": "h", "target_status": "APPROVED",
    }
    if with_order_terms:
        position["order_intent_terms"] = {
            "terms_status": "APPROVED_ORDER_INTENT_ONLY",
            "production_target_approval_status": "APPROVED_PRODUCTION_TARGET",
            "proposed_quantity": 1, "order_type": "LIMIT", "limit_price": 1.0, "approved_price_rule": None,
            "time_in_force": "DAY", "valid_from": DECISION_AS_OF, "valid_until": DECISION_AS_OF,
            "why_now": "w", "decision_change_trigger": "t", "thesis_status": "ACTIVE",
            "kill_condition": None, "funding_source": "NOT_APPLICABLE",
        }
    return {
        "plan_id": "plan-1", "as_of": DECISION_AS_OF, "plan_status": "CURRENT_APPROVED",
        "evidence_binding": {"expected_run_id": RUN_ID, "expected_decision_as_of": DECISION_AS_OF},
        "target_type": "MINIMUM_SAFETY_REFERENCE", "positions": [position],
        "material_unknowns": [], "decision_change_triggers": [],
    }


class DashboardRejectsCardTests(unittest.TestCase):
    """dashboard is imported and called, never modified."""

    def test_control_a_real_plan_is_accepted_by_dashboard_validation(self) -> None:
        self.assertEqual(dashboard.validate_plan(minimal_plan()), [])
        self.assertEqual(dashboard.validate_plan(minimal_plan(with_order_terms=True)), [])

    def test_dashboard_rejects_a_card_as_a_plan(self) -> None:
        card, _ = make_card()
        self.assertEqual(dashboard.validate_plan(card), ["DECISION_PLAN_SCHEMA_INVALID"])

    def test_dashboard_rejects_a_card_dressed_up_with_plan_fields(self) -> None:
        card, _ = make_card()
        dressed = dict(
            card, plan_id="card-plan-1", plan_status="CURRENT_APPROVED", target_type="MINIMUM_SAFETY_REFERENCE",
            material_unknowns=[], decision_change_triggers=[],
        )
        self.assertEqual(dashboard.validate_plan(dressed), ["DECISION_PLAN_SCHEMA_INVALID"])
        self.assertTrue(validator.validate_card(dressed, make_card()[1]))

    def test_dashboard_refuses_to_materialize_a_card_file(self) -> None:
        card, _ = make_card()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "workspace/outputs/x/portfolio-decision-plan.json"
            with self.assertRaises(dashboard.ContractError) as raised:
                dashboard.write_decision_plan(card, target, root=root)
            self.assertIn("DECISION_PLAN_INVALID", str(raised.exception))
            self.assertFalse(target.exists())

    def test_card_validator_rejects_a_plan_file(self) -> None:
        _, pack = make_card()
        errors = validator.validate_card(minimal_plan(), pack)
        self.assertIn("ORDER_FIELD_FORBIDDEN:$.plan_status", errors)
        self.assertTrue(any(item.startswith("CARD_SCHEMA_INVALID") for item in errors))
        errors = validator.validate_card(minimal_plan(with_order_terms=True), pack)
        for path in ("order_intent_terms", "order_intent_terms.proposed_quantity", "order_intent_terms.limit_price"):
            self.assertIn(f"ORDER_FIELD_FORBIDDEN:$.positions[0].{path}", errors)


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.messages = renderer.load_messages()
        self.card, self.pack = make_card()

    def render(self) -> str:
        return renderer.render_markdown(self.card, self.pack, self.messages)

    def test_header_has_five_lines_and_one_table_per_holding(self) -> None:
        text = self.render()
        header = text.split("\n\n---\n\n")[0]
        labels = self.messages["header_labels"]
        for key in ("conclusion_primary", "conclusion_secondary", "status", "exposure", "upcoming_events"):
            self.assertIn(f"- **{labels[key]}:**", header)
        self.assertEqual(len([line for line in header.splitlines() if line.startswith("- **")]), 5)
        for row in self.messages["rows"].values():
            self.assertEqual(text.count(f"| {row} |"), 2, row)
        self.assertEqual(text.count("# AAA"), 1)
        self.assertEqual(text.count("# BBB"), 1)

    def test_market_environment_line_when_save_is_missing_or_present(self) -> None:
        self.assertIn(self.messages["market_not_received"], self.render())
        self.assertNotIn("EXTERNAL_REFERENCE", self.render())
        self.card["header"]["market_environment"] = {
            "status": "SAVE_PROVIDED", "label": "EXTERNAL_REFERENCE", "lines": ["S&P 500 -0.8%", "48h schedule"],
        }
        text = self.render()
        self.assertEqual(text.count("EXTERNAL_REFERENCE"), 2)
        self.assertIn("S&P 500 -0.8%", text)
        self.assertNotIn(self.messages["market_not_received"], text)
        self.card["header"]["market_environment"] = {"status": "SAVE_NOT_RECEIVED", "label": "EXTERNAL_REFERENCE", "lines": []}
        self.assertIn(self.messages["market_not_received"], self.render())

    def test_banner_shows_the_confidence_cap_and_its_reasons(self) -> None:
        text = self.render()
        self.assertTrue(text.startswith("증거 UNVERIFIED"))
        self.assertIn("확신도 상한 유지", text)
        self.assertIn("preflight PASS 아님", text)
        pack = build(release_analysis())
        card, _ = make_card(pack)
        self.assertIn("확신도 상한 없음", renderer.render_markdown(card, pack, self.messages))

    def test_rule_cell_carries_deterministic_values_from_the_fact_pack(self) -> None:
        text = self.render()
        row = next(line for line in text.splitlines() if line.startswith("| 규칙 결과 |") and "HR-AAA" in line)
        for expected in ("HR-AAA-MAXLOSS-60", "기준선 $4.00", "2026-09-29 확정 종가 $8.00", "**위반 아님**", "-50.0% 남음",
                         "프리마켓 마크 기준 -55.6%는 참고값", "reduce", "미평가"):
            self.assertIn(expected, row)

    def test_numbers_cell_is_display_only_and_matches_the_fact_pack(self) -> None:
        text = self.render()
        row = next(line for line in text.splitlines() if line.startswith("| 숫자 |") and "100주" in line)
        for expected in ("100주", "평단 $10.00", "마크 $9.00(참고용)", "평가액 $900.00", "비중 41.9%",
                         "평가손익 -$100.00 (-10.0%)", "레버리지 3배", "확정 종가 $8.00", "표시 전용"):
            self.assertIn(expected, row)

    def test_judgment_cell_shows_tag_cap_and_no_quantity_notice(self) -> None:
        text = self.render()
        trim = next(line for line in text.splitlines() if line.startswith("| 판단 |") and "TRIM" in line)
        for expected in ("**TRIM", "확신도 낮음(상한)", "TRIM_CONCENTRATION", "**규칙과 같음**", "수량·시점은 제시하지 않는다."):
            self.assertIn(expected, trim)
        hold = next(line for line in text.splitlines() if line.startswith("| 판단 |") and "HOLD" in line)
        self.assertIn("검토 필요 표시 없음", hold)

    def test_difference_from_the_rule_and_review_flag_are_rendered(self) -> None:
        self.card["positions"][0] = make_position(
            self.pack, "AAA", "HOLD", rule_agreement="DIFFERENT", rule_disagreement_reason="because of Y",
            review_required=True,
        )
        text = self.render()
        self.assertIn("규칙과 다름: because of Y", text)
        self.assertIn("검토 필요 표시", text)

    def test_missing_values_render_as_needs_check_not_zero(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["status"] = "INCOMPLETE"
        analysis["broker_observed_state"]["holdings"] = []
        pack = build(analysis)
        card, _ = make_card(pack)
        text = renderer.render_markdown(card, pack, self.messages)
        row = next(line for line in text.splitlines() if line.startswith("| 숫자 |"))
        self.assertIn("확인 필요주", row)
        self.assertIn("브로커 보유 관측 없음", text)

    def test_table_cells_survive_pipes_and_newlines(self) -> None:
        self.card["positions"][0]["cash_and_alternatives"] = "a | b\nc"
        text = self.render()
        row = next(line for line in text.splitlines() if line.startswith("| 현금·대안 대비 |") and "a / b c" in line)
        self.assertEqual(len(re.findall(r"(?<!\\)\|", row)), 3)

    def test_invalid_card_is_never_rendered(self) -> None:
        self.card["positions"][0]["numbers"]["weight_pct"] = 1
        with self.assertRaises(renderer.RenderError) as raised:
            self.render()
        self.assertIn("NUMBER_MISMATCH:AAA:weight_pct", str(raised.exception))

    def test_render_is_deterministic(self) -> None:
        self.assertEqual(self.render(), self.render())

    def test_cli_writes_create_only_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "pack.json").write_text(json.dumps(self.pack), encoding="utf-8")
            (root / "card.json").write_text(json.dumps(self.card), encoding="utf-8")
            args = ["--card", str(root / "card.json"), "--fact-pack", str(root / "pack.json")]
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(renderer.main(args), 0)
            output = root / "cards.md"
            self.assertTrue(output.is_file())
            self.assertIn("AAA", output.read_text(encoding="utf-8"))
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(renderer.main(args), 2)
            self.card["evidence_binding"]["expected_run_id"] = "manual-other-run-id-000000"
            (root / "card.json").write_text(json.dumps(self.card), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(renderer.main(args + ["--output", str(root / "second.md")]), 2)
            self.assertFalse((root / "second.md").exists())


@unittest.skipUnless(shutil.which("git"), "git is required for check-ignore")
class GitignoreTests(unittest.TestCase):
    def ignored(self, path: str) -> bool:
        result = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO_ROOT, capture_output=True, text=True)
        return result.returncode == 0

    def test_holding_cards_outputs_are_git_ignored(self) -> None:
        for name in ("fact-pack.json", "card.json", "cards.md"):
            for folder in ("2026-09-30", "2026-09-30-r2"):
                with self.subTest(name=name, folder=folder):
                    self.assertTrue(self.ignored(f"workspace/outputs/holding-cards/{folder}/{name}"))

    def test_gitignore_lists_the_folder_exactly_once(self) -> None:
        lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual([line.strip() for line in lines].count("workspace/outputs/holding-cards/"), 1)

    def test_source_files_are_not_ignored(self) -> None:
        for path in (
            "manage-us-stock-strategy/scripts/build_holding_fact_pack.py",
            "manage-us-stock-strategy/scripts/validate_holding_card.py",
            "manage-us-stock-strategy/scripts/render_holding_cards.py",
            "manage-us-stock-strategy/schemas/holding-card.schema.json",
            "manage-us-stock-strategy/assets/locales/holding-card-ko-KR.json",
            "docs/claude/i1-builder-report-2026-09-30.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(self.ignored(path))


if __name__ == "__main__":
    unittest.main()
