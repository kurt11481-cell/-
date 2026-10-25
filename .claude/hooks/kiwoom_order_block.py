#!/usr/bin/env python3
"""PreToolUse hook: refuse tool calls that carry a Kiwoom order marker (K3 kiwoom-block, 2026-10-25).

Reads the hook JSON from stdin. Exit 2 (refuse, one-line reason on stderr) when a target tool's input
carries an order marker, or when a target tool's input cannot be read (fail closed); otherwise exit 0.

Targets: Bash, PowerShell and Monitor (field "command"); mcp__ tools whose name contains "kiwoom" (the whole input);
mcp__ tools that run a shell on a device, named ending in device_bash, start_process or
interact_with_process (the command field only). File-writing tools are never targets, so documents may
quote the markers. This hook only adds refusals: it has no allow path, no bypass switch and no test branch.
"""

import json
import re
import sys

MARKERS = (
    ("kiwoomcli", re.compile(r"kiwoomcli", re.IGNORECASE)),
    ("overseas orders", re.compile(r"overseas\s+orders", re.IGNORECASE)),
    ("ust20000-ust20003", re.compile(r"ust2000[0-3]", re.IGNORECASE)),
    ("/api/us/ordr", re.compile(r"/api/us/ordr", re.IGNORECASE)),
    # --confirm as a whole flag; --confirmed-via (and any longer flag name) passes.
    ("--confirm", re.compile(r"--confirm(?![A-Za-z0-9_-])", re.IGNORECASE)),
    # confirm set to true as text: JSON "confirm": true, YAML confirm: true, Python confirm=True.
    ("confirm true", re.compile(r"(?<![A-Za-z0-9_-])confirm[\"']?\s*[:=]\s*[\"']?(true|1|yes|on)(?![A-Za-z0-9_])",
                                re.IGNORECASE)),
)
ORDER_TOOL_SUFFIXES = ("kiwoom_order_submit", "kiwoom_order_preview")
SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")
DEVICE_SHELL_SUFFIXES = ("device_bash", "start_process", "interact_with_process")
DEVICE_COMMAND_FIELDS = ("command", "cmd", "input", "script")
# Shell quoting and escape characters are dropped before matching, so kiwoom"cli, kiw^oomcli,
# kiwoom`cli and "overseas" "orders" still match. Also dropped: the bash backtick, the $ of bash $'...'
# and $"...", backslashes and backslash-newline escapes, so --con\firm, kiwoom\cli, --con$'f'irm and
# a --con\<newline>firm continuation match too. The quote-only strip is checked as well, so a boundary
# that only the wider strip removes cannot hide a match: this can only add matches.
QUOTE_CHARS = re.compile(r"[\"'`^]")
STRIP_CHARS = re.compile(r"\\\r?\n|[\"'`^\\]|\$(?=[\"'])")
TRUE_TEXT = {"true", "1", "yes", "y", "on"}


def refuse(reason):
    sys.stderr.write("kiwoom_order_block: refused - " + reason + "\n")
    return 2


def target_kind(tool_name):
    if tool_name in SHELL_TOOLS:
        return "shell"
    if not tool_name.startswith("mcp__"):
        return None
    lowered = tool_name.lower()
    if "kiwoom" in lowered:
        return "kiwoom_mcp"
    if lowered.endswith(DEVICE_SHELL_SUFFIXES):
        return "device_shell"
    return None


def find_marker(text):
    for variant in (text, QUOTE_CHARS.sub("", text), STRIP_CHARS.sub("", text)):
        for label, pattern in MARKERS:
            if pattern.search(variant):
                return label
    return None


def is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in TRUE_TEXT
    return False


def is_confirm_key(key):
    # The exec MCP turns an option key into a flag with key.replace("_", "-").lstrip("-"),
    # so "confirm", "-confirm" and "--confirm" all become --confirm.
    return isinstance(key, str) and key.strip().replace("_", "-").lstrip("-").lower() == "confirm"


def has_true_confirm(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if is_confirm_key(key) and is_true(item):
                return True
            if has_true_confirm(item):
                return True
    elif isinstance(value, list):
        return any(has_true_confirm(item) for item in value)
    return False


def check(payload):
    if not isinstance(payload, dict):
        return refuse("hook input is not a JSON object")
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name:
        return refuse("hook input has no tool_name")
    kind = target_kind(tool_name)
    if kind is None:
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return refuse(tool_name + ": hook input has no tool_input object")

    if kind == "shell":
        command = tool_input.get("command")
        if not isinstance(command, str):
            return refuse(tool_name + ": tool_input has no command string")
        texts = [command]
    elif kind == "device_shell":
        texts = [tool_input[field] for field in DEVICE_COMMAND_FIELDS
                 if isinstance(tool_input.get(field), str)]
        if not texts:
            return refuse(tool_name + ": tool_input has no command field")
    else:
        if tool_name.lower().endswith(ORDER_TOOL_SUFFIXES):
            return refuse(tool_name + ": Kiwoom order tool")
        if has_true_confirm(tool_input):
            return refuse(tool_name + ": confirm is true")
        texts = [json.dumps(tool_input, ensure_ascii=False)]

    for text in texts:
        label = find_marker(text)
        if label:
            return refuse(tool_name + ": order marker '" + label + "'")
    return 0


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig")
        payload = json.loads(raw)
    except Exception:
        # The settings matcher only sends target tools here, so unreadable input is refused.
        return refuse("hook input is not readable JSON")
    try:
        return check(payload)
    except Exception as exc:
        return refuse("hook error " + type(exc).__name__)


if __name__ == "__main__":
    sys.exit(main())
