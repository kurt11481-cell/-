import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "run_llm_decision_stability", SCRIPT_DIR / "run_llm_decision_stability.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def run(action="WAIT", risk="ALLOW_REVIEW"):
    return {
        "action": action,
        "risk_verdict": risk,
        "dominant_thesis_code": "WAIT_PERMISSION_AND_VALUATION",
        "invalidation_codes": [
            "VALUATION_REMAINS_UNVERIFIED",
            "NEW_BUY_AUTHORITY_REMAINS_ABSENT",
        ],
        "preferred_candidate": None,
    }


class LLMDecisionStabilityTests(unittest.TestCase):
    def test_identical_authority_outcomes_pass(self):
        result = MODULE.classify_raw_stability([run(), run(), run()])
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["critical_instability"])
        self.assertEqual(result["differences"], [])

    def test_buy_vs_wait_is_critical_for_non_held_candidate(self):
        result = MODULE.classify_raw_stability(
            [run(), run("BUY_REVIEW", "ALLOW_REVIEW"), run()]
        )
        self.assertEqual(result["status"], "DECISION_STABILITY_RISK")
        self.assertTrue(result["critical_instability"])

    def test_harness_does_not_accept_private_portfolio_inputs(self):
        source = (SCRIPT_DIR / "run_llm_decision_stability.py").read_text(encoding="utf-8")
        for private_flag in (
            '--portfolio', '--runtime', '--cash', '--holdings', '--cost-basis', '--fills'
        ):
            self.assertNotIn(f'parser.add_argument("{private_flag}"', source)


if __name__ == "__main__":
    unittest.main()
