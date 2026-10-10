"""Scheduled prompts that call kiwoom_query must state profile and real mode.

Rule: CLAUDE.md "Kiwoom query rules" (user standing rule 2026-10-07). Every
kiwoom_query call passes options "profile": "실전계좌" and "mode": "real".
This test only reads the prompt files; it never writes or fixes them.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = REPO_ROOT / "docs" / "claude" / "scheduled-prompts"

QUERY_TOKEN = "kiwoom_query"
PROFILE_RE = re.compile(r'"profile"\s*:\s*"실전계좌"')
MODE_RE = re.compile(r'"mode"\s*:\s*"real"')


def has_query(text):
    return QUERY_TOKEN in text


def violates_profile_rule(text):
    """True when the text calls kiwoom_query but no single line carries both values."""
    if not has_query(text):
        return False
    for line in text.splitlines():
        if PROFILE_RE.search(line) and MODE_RE.search(line):
            return False
    return True


class ProfileRuleHelperTests(unittest.TestCase):
    def test_rule_line_present_passes(self):
        text = 'kiwoom_query options {"profile": "실전계좌", "mode": "real"}'
        self.assertFalse(violates_profile_rule(text))

    def test_profile_only_is_violation(self):
        text = 'kiwoom_query options {"profile": "실전계좌"}'
        self.assertTrue(violates_profile_rule(text))

    def test_mode_only_is_violation(self):
        text = 'kiwoom_query options {"mode": "real"}'
        self.assertTrue(violates_profile_rule(text))

    def test_values_split_across_lines_is_violation(self):
        text = 'kiwoom_query options\n{"profile": "실전계좌"}\n{"mode": "real"}\n'
        self.assertTrue(violates_profile_rule(text))

    def test_no_query_is_not_checked(self):
        self.assertFalse(violates_profile_rule("no broker call here\nplain text"))

    def test_whitespace_variant_passes(self):
        text = 'kiwoom_query {"profile":"실전계좌","mode":"real"}'
        self.assertFalse(violates_profile_rule(text))

    def test_wrong_profile_value_is_violation(self):
        text = 'kiwoom_query {"profile": "모의계좌", "mode": "real"}'
        self.assertTrue(violates_profile_rule(text))


class ScheduledPromptRepoTests(unittest.TestCase):
    def test_all_scheduled_prompts_state_profile_and_mode(self):
        self.assertTrue(
            PROMPT_DIR.is_dir(),
            f"scheduled prompt folder missing: {PROMPT_DIR}",
        )
        files = sorted(PROMPT_DIR.rglob("*.txt"))
        checked = []
        violations = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            if not has_query(text):
                continue
            checked.append(path)
            if violates_profile_rule(text):
                violations.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertTrue(
            checked,
            "no scheduled prompt mentions kiwoom_query; check would be silently empty",
        )
        self.assertEqual(violations, [], f"prompts missing profile/mode rule: {violations}")


if __name__ == "__main__":
    unittest.main()
