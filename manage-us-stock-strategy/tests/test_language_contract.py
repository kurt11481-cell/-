from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))
SCRIPT = SCRIPT_ROOT / "evaluate_alerts.py"
SPEC = importlib.util.spec_from_file_location("evaluate_alerts_language", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LanguageContractTests(unittest.TestCase):
    def test_python_core_is_ascii_only(self) -> None:
        for path in SCRIPT_ROOT.glob("*.py"):
            self.assertTrue(path.read_text(encoding="utf-8").isascii(), path.name)

    def test_internal_result_is_english_and_output_is_localized(self) -> None:
        result = {
            "headline_key": MODULE.HEADLINE_NONE_KEY,
            "headline": MODULE.CANONICAL_ENGLISH_MESSAGES[
                MODULE.HEADLINE_NONE_KEY
            ],
            "state": "DAILY_REVIEW",
            "grade": "E",
            "strategy_version": "test",
            "rules_hash": "test",
            "us_session_date": "2026-08-05",
            "expected_us_session_date": "2026-08-05",
            "official_calendar_verified": True,
            "state_updated_at": "2026-08-06T00:00:00+09:00",
            "risk_freeze_active": False,
            "warnings": [],
            "candidates": [],
            "watchlist": [],
        }
        self.assertTrue(result["headline"].isascii())
        english = MODULE.render_markdown(result, "en-US")
        korean = MODULE.render_markdown(result, "ko-KR")
        self.assertIn(MODULE.CANONICAL_ENGLISH_MESSAGES["alert_none"], english)
        self.assertIn(
            MODULE.load_output_messages("ko-KR")["alert_none"], korean
        )
        self.assertNotEqual(english.splitlines()[0], korean.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
