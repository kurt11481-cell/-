#!/usr/bin/env python3
"""K3 kiwoom-block: the PreToolUse order-marker hook refuses order markers and the proposed settings only add.

The hook runs as a subprocess with synthetic hook JSON on stdin. No Kiwoom tool, CLI, network or
credential is touched; the settings files are only parsed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "kiwoom_order_block.py"
CURRENT_SETTINGS = ROOT / ".claude" / "settings.json"
PROPOSED_SETTINGS = ROOT / "docs" / "claude" / "kiwoom-block-settings-proposed.json"

ALLOWED_DENY_ADDITIONS = (
    "mcp__*__kiwoom_order_preview",
    "Bash(*overseas orders*)",
    "PowerShell(*overseas orders*)",
    "Bash(*kiwoomcli*)",
    "PowerShell(*kiwoomcli*)",
)

# Text markers, each as it would appear inside a command or a tool input.
TEXT_MARKERS = {
    "kiwoomcli": "kiwoomcli overseas candles stock-minute --code NVDA",
    "overseas orders": "python -m kiwoom_cli overseas orders buy --code NVDA",
    "ust2000x": "echo ust20001",
    "/api/us/ordr": "curl -X POST https://example.invalid/api/us/ordr",
    "--confirm": "python -m kiwoom_cli domestic orders buy --confirm",
    "confirm true": "python -c \"import kiwoom_exec_mcp.server as s; s.kiwoom_order_submit('x', confirm=True)\"",
}

# One tool per target family: (tool_name, builder of tool_input from a command string).
TARGET_TOOLS = {
    "Bash": ("Bash", lambda text: {"command": text}),
    "PowerShell": ("PowerShell", lambda text: {"command": text}),
    "kiwoom_mcp": ("mcp__kiwoom_exec__kiwoom_query",
                   lambda text: {"command_path": text, "options": {"profile": "TEST_ONLY", "mode": "real"}}),
    "device_bash": ("mcp__remote-devices__device_bash", lambda text: {"command": text}),
    "Monitor": ("Monitor", lambda text: {"command": text, "description": "x", "timeout_ms": 1000}),
}
SHELL_FAMILIES = ("Bash", "PowerShell", "Monitor", "device_bash")

# Shell texts that carry a marker only after quoting or escape characters are removed.
FALSE_NEGATIVE_VARIANTS = (
    r"C:\venv\Scripts\kiwoomcli.exe overseas candles stock-minute",
    "KIWOOMCLI --version",
    'kiwoom"cli --version',
    "kiw^oomcli --version",
    "& kiwoom`cli --version",
    'cmd /c "python -m kiwoom_cli "overseas" "orders" buy"',
    "python -m kiwoom_cli overseas    orders sell",
    "python -m kiwoom_cli OVERSEAS ORDERS cancel",
    "echo UST20003",
    'cmd /c "python -m kiwoom_cli domestic orders buy --confirm"',
    "python -m kiwoom_cli domestic orders buy --confirm;echo done",
    "python -m kiwoom_cli exchange request --confirm=1",
    "python -m kiwoom_cli exchange request --CONFIRM",
    "python -m kiwoom_cli exchange request\n--confirm",
    "\nKiwoomCLI.exe --version\n",
    'echo "ust20001"',
    "python -m kiwoom_cli exchange request --confirm=true",
    "echo '{\"confirm\": true}' > x.json",
    "echo confirm: TRUE",
    r"python -m kiwoom_cli domestic orders buy --con\firm",
    r"kiwoom\cli --version",
    "python -m kiwoom_cli domestic orders buy --con$'f'irm",
    "python -m kiwoom_cli domestic orders buy --con\\\nfirm",
    # fix2: bash turns both into exactly --confirm ($'\0' and $'\x00' expand to nothing). The wider strip
    # alone leaves --confirm0, so these passed in the first fix1 hook (judge2 regression).
    "python -m kiwoom_cli domestic orders buy --con\"\"firm$'\\0'",
    "python -m kiwoom_cli domestic orders buy --con''firm$'\\x00'",
)

# A quote-only strip leaves a backslash that ends the marker; the wider strip removes it and joins the text.
BOUNDARY_CASES = (
    r'python -m kiwoom_cli domestic orders buy --con"firm\-x"',
    "python -m kiwoom_cli domestic orders buy --con\"\"firm\\\n-x",
    "python -c \"f(a\\con'firm'=True)\"",
)


def load_hook_module():
    spec = importlib.util.spec_from_file_location("kiwoom_order_block_under_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refused_before_fix1(markers, text: str) -> bool:
    # Reference for the hook before fix1: the raw text and the quote-only strip, nothing else.
    quote_only = re.compile(r"[\"'`^]")
    return any(pattern.search(variant) for variant in (text, quote_only.sub("", text)) for _, pattern in markers)


def run_hook(stdin_bytes: bytes) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(HOOK)], input=stdin_bytes, capture_output=True, timeout=30)
    return result.returncode, result.stderr.decode("utf-8", "replace")


def run_tool(tool_name: str, tool_input: object) -> tuple[int, str]:
    payload = {"session_id": "TEST_ONLY", "hook_event_name": "PreToolUse",
               "tool_name": tool_name, "tool_input": tool_input}
    return run_hook(json.dumps(payload).encode("utf-8"))


class HookRefusesOrderMarkers(unittest.TestCase):
    def assert_refused(self, tool_name: str, tool_input: object) -> None:
        code, stderr = run_tool(tool_name, tool_input)
        self.assertEqual(code, 2, f"{tool_name} {tool_input!r} was not refused")
        self.assertIn("kiwoom_order_block: refused", stderr)

    def test_every_text_marker_is_refused_on_every_target_family(self):
        for marker, text in TEXT_MARKERS.items():
            for family, (tool_name, build) in TARGET_TOOLS.items():
                with self.subTest(marker=marker, family=family):
                    self.assert_refused(tool_name, build(text))

    def test_preview_tool_with_a_confirm_option_is_refused_under_any_name(self):
        # kiwoom_order_preview forwards options as CLI flags, so a confirm option would submit a real order.
        for tool_name in ("mcp__kiwoom_exec__kiwoom_order_preview", "mcp__kiwoom_exec__kiwoom_query"):
            with self.subTest(tool_name=tool_name):
                self.assert_refused(tool_name, {"command_path": "domestic stocks info", "options": {"confirm": True}})

    def test_order_tool_names_are_refused_whatever_the_input(self):
        for tool_name in ("mcp__kiwoom_exec__kiwoom_order_submit", "mcp__kiwoom_exec__kiwoom_order_preview",
                          "mcp__remote-devices__kiwoom_order_submit", "mcp__x__KIWOOM_ORDER_PREVIEW"):
            with self.subTest(tool_name=tool_name):
                self.assert_refused(tool_name, {"command_path": "domestic orders buy", "options": {}})
                self.assert_refused(tool_name, {})

    def test_true_confirm_in_a_kiwoom_tool_input_is_refused(self):
        tool_name = TARGET_TOOLS["kiwoom_mcp"][0]
        for tool_input in ({"command_path": "overseas accounts cash", "confirm": True},
                           {"command_path": "overseas accounts cash", "options": {"confirm": True}},
                           {"command_path": "overseas accounts cash", "options": {"confirm": "true"}},
                           {"command_path": "overseas accounts cash", "options": {"Confirm": 1}},
                           {"command_path": "overseas accounts cash", "options": [{"confirm": "yes"}]},
                           {"command_path": "overseas accounts cash", "options": {"-confirm": True}},
                           {"command_path": "overseas accounts cash", "options": {" _confirm": True}},
                           {"command_path": "overseas accounts cash", "options": "confirm: true"}):
            with self.subTest(tool_input=tool_input):
                self.assert_refused(tool_name, tool_input)

    def test_false_negative_variants_are_still_refused(self):
        for text in FALSE_NEGATIVE_VARIANTS:
            for family in SHELL_FAMILIES:
                tool_name, build = TARGET_TOOLS[family]
                with self.subTest(text=text, family=family):
                    self.assert_refused(tool_name, build(text))

    def test_everything_refused_before_fix1_is_still_refused(self):
        # fix2 (judge2 R2): the current hook refuses at least what the hook before fix1 refused.
        markers = load_hook_module().MARKERS
        inputs = FALSE_NEGATIVE_VARIANTS + BOUNDARY_CASES + tuple(TEXT_MARKERS.values())
        reference_refused = [text for text in inputs if refused_before_fix1(markers, text)]
        for text in FALSE_NEGATIVE_VARIANTS[-2:] + BOUNDARY_CASES:
            self.assertIn(text, reference_refused)
        for text in reference_refused:
            for family in SHELL_FAMILIES:
                tool_name, build = TARGET_TOOLS[family]
                with self.subTest(text=text, family=family):
                    self.assert_refused(tool_name, build(text))

    def test_other_device_shell_tools_are_checked_on_their_command_field(self):
        self.assert_refused("mcp__plugin_desktop-commander_desktop-commander__start_process",
                            {"command": "kiwoomcli overseas orders buy --confirm", "timeout_ms": 1000})
        self.assert_refused("mcp__remote-devices__start_process", {"command": "echo ust20000"})
        self.assert_refused("mcp__plugin_desktop-commander_desktop-commander__interact_with_process",
                            {"pid": 1, "input": "kiwoomcli overseas orders sell --confirm"})

    def test_monitor_command_is_checked(self):
        # Monitor runs its command in the same shell as Bash; a ws-only call has no command and is refused.
        self.assert_refused("Monitor", {"command": "echo ust20000", "description": "x", "timeout_ms": 1000})
        self.assert_refused("Monitor", {"command": "python -m kiwoom_cli domestic orders buy --con\\firm",
                                        "description": "x", "timeout_ms": 1000})
        code, stderr = run_tool("Monitor", {"command": "git status", "description": "x", "timeout_ms": 1000})
        self.assertEqual(code, 0, stderr)
        code, _ = run_tool("Monitor", {"ws": {"url": "wss://example.invalid/stream"}, "description": "x",
                                       "timeout_ms": 1000})
        self.assertEqual(code, 2)

    def test_unreadable_or_incomplete_input_is_refused(self):
        for stdin_bytes in (b"", b"not json", b"{\"tool_name\": \"Bash\"", b"[]", b"null",
                            b"\xff\xfe\x00garbage"):
            with self.subTest(stdin=stdin_bytes):
                code, _ = run_hook(stdin_bytes)
                self.assertEqual(code, 2)
        for payload in ({"tool_input": {"command": "git status"}},
                        {"tool_name": "", "tool_input": {"command": "git status"}},
                        {"tool_name": "Bash"},
                        {"tool_name": "Bash", "tool_input": "git status"},
                        {"tool_name": "Bash", "tool_input": {}},
                        {"tool_name": "PowerShell", "tool_input": {"command": ["git", "status"]}},
                        {"tool_name": "mcp__kiwoom_exec__kiwoom_query", "tool_input": None},
                        {"tool_name": "mcp__remote-devices__device_bash", "tool_input": {"pid": 1}}):
            with self.subTest(payload=payload):
                code, _ = run_hook(json.dumps(payload).encode("utf-8"))
                self.assertEqual(code, 2)


class HookPassesOrdinaryWork(unittest.TestCase):
    def assert_passed(self, tool_name: str, tool_input: object) -> None:
        code, stderr = run_tool(tool_name, tool_input)
        self.assertEqual(code, 0, f"{tool_name} {tool_input!r} was refused: {stderr}")

    def test_ordinary_shell_commands_pass(self):
        for text in ("git status",
                     'python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*"',
                     "python manage-us-stock-strategy/scripts/validate_schema_contracts.py",
                     "python tool.py --confirmed-via USER_TERMINAL",
                     "python tool.py --confirmation-code-file x.txt",
                     "python tool.py --confirm-export-path x.txt",
                     "python tool.py --confirm_code_file=1",
                     "echo confirm_code=1 unconfirm=true confirmed=true",
                     "Get-ChildItem docs/claude",
                     "rg -n order_ticket docs/claude",
                     "python manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py --help",
                     "powershell -File manage-us-stock-strategy/scripts/collect_30m.ps1 -Symbol NVDA",
                     r"python C:\Users\TEST_ONLY\AppData\Local\Temp\x.py",
                     "Get-ChildItem E:\\\uc0ac\uc5c5\\##\uae08\ub3d9\ud55c\\\ucf54\ub371\uc2a4\uc800\uc7a5\uc18c\\docs\\claude",
                     r"python manage-us-stock-strategy\scripts\validate_schema_contracts.py"):
            for family in ("Bash", "PowerShell", "device_bash"):
                tool_name, build = TARGET_TOOLS[family]
                with self.subTest(text=text, family=family):
                    self.assert_passed(tool_name, build(text))

    def test_ordinary_kiwoom_read_query_passes(self):
        self.assert_passed("mcp__kiwoom_exec__kiwoom_query",
                           {"command_path": "overseas accounts cash",
                            "options": {"profile": "TEST_ONLY", "mode": "real", "confirm": False}})
        self.assert_passed("mcp__kiwoom_exec__kiwoom_commands", {})

    def test_file_writing_tools_may_quote_markers(self):
        text = "kiwoomcli overseas orders buy --confirm ust20000 /api/us/ordr"
        for tool_name, tool_input in (
                ("Write", {"file_path": "docs/claude/x.md", "content": text}),
                ("Edit", {"file_path": "docs/claude/x.md", "old_string": "a", "new_string": text}),
                ("Read", {"file_path": "docs/claude/" + text}),
                ("mcp__plugin_desktop-commander_desktop-commander__write_file",
                 {"path": "docs/claude/x.md", "content": text}),
                ("mcp__remote-devices__write_file", {"path": "docs/claude/x.md", "content": text})):
            with self.subTest(tool_name=tool_name):
                self.assert_passed(tool_name, tool_input)

    def test_device_shell_tools_check_only_the_command_field(self):
        self.assert_passed("mcp__remote-devices__device_bash",
                           {"command": "git status", "description": "kiwoomcli overseas orders --confirm"})

    def test_mcp_tools_without_kiwoom_in_the_name_pass(self):
        self.assert_passed("mcp__claude_ai_Dropbox__search", {"query": "kiwoomcli overseas orders buy --confirm"})
        self.assert_passed("mcp__claude_ai_Dropbox__search", {"query": "x", "confirm": True})

    def test_non_target_tools_pass_even_with_odd_input(self):
        for payload in ({"tool_name": "Write", "tool_input": None},
                        {"tool_name": "Glob"},
                        {"tool_name": "mcp__claude_ai_Dropbox__search", "tool_input": "x"}):
            with self.subTest(payload=payload):
                code, _ = run_hook(json.dumps(payload).encode("utf-8"))
                self.assertEqual(code, 0)


class HookFileShape(unittest.TestCase):
    def test_hook_is_ascii_crlf_and_standard_library_only(self):
        raw = HOOK.read_bytes()
        raw.decode("ascii")
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        imports = set(re.findall(rb"^(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", raw, re.MULTILINE))
        self.assertEqual(imports, {b"json", b"re", b"sys"})

    def test_hook_has_no_environment_or_bypass_branch(self):
        text = HOOK.read_text(encoding="ascii")
        for forbidden in ("os.environ", "getenv", "import os", "argv"):
            self.assertNotIn(forbidden, text)


class ProposedSettingsOnlyAdd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = json.loads(CURRENT_SETTINGS.read_text(encoding="utf-8"))
        cls.proposed = json.loads(PROPOSED_SETTINGS.read_text(encoding="utf-8"))

    def test_existing_deny_and_ask_entries_are_kept_in_order(self):
        current_deny = self.current["permissions"]["deny"]
        proposed_deny = self.proposed["permissions"]["deny"]
        self.assertEqual(proposed_deny[:len(current_deny)], current_deny)
        self.assertEqual(self.proposed["permissions"]["ask"], self.current["permissions"]["ask"])

    def test_allow_is_unchanged(self):
        self.assertEqual(self.proposed["permissions"].get("allow"), self.current["permissions"].get("allow"))
        self.assertEqual(set(self.proposed["permissions"]), set(self.current["permissions"]))

    def test_added_deny_entries_come_from_the_approved_list(self):
        added = self.proposed["permissions"]["deny"][len(self.current["permissions"]["deny"]):]
        self.assertGreaterEqual(len(added), 3)
        self.assertLessEqual(len(added), len(ALLOWED_DENY_ADDITIONS))
        self.assertEqual(len(added), len(set(added)))
        for entry in added:
            self.assertIn(entry, ALLOWED_DENY_ADDITIONS)
        for required in ALLOWED_DENY_ADDITIONS[:3]:
            self.assertIn(required, added)

    def test_only_the_hooks_key_is_added_and_other_keys_are_unchanged(self):
        self.assertEqual(set(self.proposed) - set(self.current), {"hooks"})
        self.assertEqual(set(self.current) - set(self.proposed), set())
        for key in self.current:
            if key != "permissions":
                self.assertEqual(self.proposed[key], self.current[key], key)

    def test_hook_entry_runs_this_hook_for_every_target_and_no_file_tool(self):
        entries = self.proposed["hooks"]["PreToolUse"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(set(self.proposed["hooks"]), {"PreToolUse"})
        matcher = entries[0]["matcher"]
        commands = entries[0]["hooks"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "command")
        self.assertIn(".claude/hooks/kiwoom_order_block.py", commands[0]["command"])
        targets = ("Bash", "PowerShell", "Monitor", "mcp__kiwoom_exec__kiwoom_query", "mcp__kiwoom_exec__kiwoom_order_submit",
                   "mcp__kiwoom_exec__kiwoom_commands", "mcp__kiwoom_spec__spec_search",
                   "mcp__remote-devices__device_bash", "mcp__remote-devices__start_process",
                   "mcp__plugin_desktop-commander_desktop-commander__start_process",
                   "mcp__plugin_desktop-commander_desktop-commander__interact_with_process")
        others = ("Write", "Edit", "Read", "Glob", "Grep", "NotebookEdit",
                  "mcp__plugin_desktop-commander_desktop-commander__write_file", "mcp__remote-devices__write_file")
        pattern = re.compile(matcher)
        for name in targets:
            with self.subTest(target=name):
                self.assertIsNotNone(pattern.fullmatch(name))
                self.assertIsNotNone(pattern.search(name))
        for name in others:
            with self.subTest(other=name):
                self.assertIsNone(pattern.search(name))

    def test_proposed_file_is_ascii_and_crlf(self):
        raw = PROPOSED_SETTINGS.read_bytes()
        raw.decode("ascii")
        self.assertIn(b"\r\n", raw)
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
