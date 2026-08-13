from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
from render_beginner_portfolio_report import render_beginner_summary
from validation_common import load_json, validate_instance


class V25BeginnerRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.locale = load_json(ROOT / "manage-us-stock-strategy/assets/locales/ko-KR.json")

    def holding(self, state, code, *, risk=False, execution="NOT_APPLICABLE"):
        return {"ticker": "TEST", "strategy_state": state, "display_action_code": code,
                "primary_reason_code": "TEST_REASON", "effective_price_status": "PRIMARY_VALIDATED",
                "execution_state": execution, "hard_risk_active": risk}

    def render(self, holding, **extra):
        report = {"data_status": extra.get("data_status", "VALIDATED"), "holding_strategies": [holding],
                  "tactical_radar_result": {"candidate_dispositions": []}, "snapshot_request": extra.get("snapshot_request", {})}
        return render_beginner_summary(report, self.locale)

    def test_v25_ui_01_hold(self):
        self.assertEqual(self.render(self.holding("HOLD", "HOLD_NO_ACTION"))["display_action"], "그대로 보유")

    def test_v25_ui_02_add_watch(self):
        self.assertEqual(self.render(self.holding("ADD_ON_WATCH", "ADD_WAIT"))["display_action"], "추가매수는 아직 기다리기")

    def test_v25_ui_03_add_pending_price(self):
        value = self.render(self.holding("ADD_REVIEW", "ADD_REVIEW", execution="VERIFICATION_PENDING"))
        self.assertEqual(value["display_action"], "추가매수 조건은 보이지만 가격 확인 중")

    def test_v25_ui_04_reduction(self):
        self.assertEqual(self.render(self.holding("REDUCTION_REVIEW", "REDUCE_REVIEW"))["display_action"], "일부 줄이기 검토")

    def test_v25_ui_05_hard_risk_priority(self):
        report = {"data_status": "VALIDATED", "holding_strategies": [self.holding("ADD_REVIEW", "ADD_REVIEW", risk=True)],
                  "tactical_radar_result": {"candidate_dispositions": [{"ticker": "BUY", "opportunity_state": "READY", "execution_state": "VERIFICATION_PENDING", "price_evidence": {"effective_price_status": "PRIMARY_VALIDATED"}}]}, "snapshot_request": {}}
        self.assertEqual(render_beginner_summary(report, self.locale)["display_action_code"], "RISK_REVIEW")

    def test_v25_ui_06_data_incomplete_not_no_alert(self):
        value = render_beginner_summary({"data_status": "DATA_INCOMPLETE", "holding_strategies": [], "tactical_radar_result": {"candidate_dispositions": []}, "snapshot_request": {}}, self.locale)
        self.assertEqual(value["display_action_code"], "DATA_ISSUE")
        self.assertNotEqual(value["display_action"], self.locale["messages"]["alert_none"])

    def test_v25_ui_07_core_python_ascii(self):
        for path in (ROOT / "manage-us-stock-strategy/scripts").glob("*.py"):
            self.assertTrue(path.read_text(encoding="utf-8").isascii(), path.name)

    def test_v25_ui_08_no_order_notice_and_schema(self):
        value = self.render(self.holding("HOLD", "HOLD_NO_ACTION"))
        self.assertTrue(value["no_order_notice"])
        self.assertEqual(validate_instance(value, ROOT / "manage-us-stock-strategy/schemas/beginner-portfolio-summary.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
