#!/usr/bin/env python3
"""sdk_agent.py - the dev-pipeline Judge on API credits through the Claude Agent SDK (devq-api stage 1).

Started only by tools/dev-run.ps1 (Start-JudgeApi) after `devpipe.py pick-route` printed `ROUTE api`:

    python tools/dev_pipeline/sdk_agent.py --role judge --cli <claude.exe> --cwd <worktree>
        --prompt-file-line "<the Judge prompt line>" --max-turns <n> --budget <usd> --out <judge-N.json>

It starts the same claude.exe as the subscription Judge (`claude -p`) with the same model, effort, tools,
turns and setting/MCP limits, and writes the final result in the `claude -p --output-format json` shape plus
route, api_error_status and kst_end, so devpipe parse_judge_envelope reads it unchanged.

Key handling: INVESTV2_DEVQ_API_KEY is taken out of this process environment first thing, together with the
other Anthropic variables below; the CLI gets only env={"ANTHROPIC_API_KEY": <key>}. The key, or any part of
it, is never printed or written (exceptions are recorded by type name and HTTP status only). The SDK is
imported only here. Standard output is one line: SDK-AGENT <role> <ok|error> turns=<n>.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime
import json
import math
import os
import sys
from pathlib import Path

KEY_ENV = "INVESTV2_DEVQ_API_KEY"
# Removed from this process right after the key is read (the CLI must not pick up any other credential,
# endpoint or profile): llm_pilot_common.SDK_ENV_VARS plus the pilots' own key name.
CLEARED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS",
               "ANTHROPIC_PROFILE", "INVESTV2_ANTHROPIC_API_KEY")
SDK_MODULE = "claude_agent_sdk"
KST = datetime.timezone(datetime.timedelta(hours=9))

# The subscription Judge command in tools/dev-run.ps1 (Start-JudgeSubscription), as SDK options.
JUDGE_MODEL = "opus"
JUDGE_EFFORT = "xhigh"
JUDGE_TOOLS = ("Read", "Grep", "Glob")
JUDGE_DISALLOWED_TOOLS = ("mcp__*",)
JUDGE_SETTING_SOURCES = ("project",)
JUDGE_EXTRA_ARGS = {"permission-prompts": "none"}
MAX_BUDGET_USD = 8  # same as devpipe.JUDGE_MAX_BUDGET_USD (a test keeps them equal)
MAX_TURNS_LIMIT = 300
PROMPT_LINE_LIMIT = 400

ENVELOPE_KEYS = ("type", "subtype", "is_error", "result", "num_turns", "total_cost_usd", "usage", "modelUsage",
                 "session_id", "duration_ms", "route", "api_error_status", "kst_end")
REDACTED = "[redacted]"


def take_key(environ):
    """Pop the dev-queue key and every cleared name from environ (os.environ: also from the process). '' = none."""
    key = environ.pop(KEY_ENV, None)
    for name in CLEARED_ENV:
        environ.pop(name, None)
    return key or None


def kst_now_text():
    return datetime.datetime.now(KST).isoformat(timespec="seconds")


def http_status(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def plain(value, depth=0):
    """A JSON-safe copy (dataclasses and mappings become dicts; anything else unknown becomes its type name)."""
    if depth > 20:
        return None
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return plain(dataclasses.asdict(value), depth + 1)
    if isinstance(value, dict):
        return {str(k): plain(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v, depth + 1) for v in value]
    return type(value).__name__


def redact(value, key):
    """Replace the key wherever it appears in a string (defence in depth: the CLI never prints it)."""
    if not key:
        return value
    if isinstance(value, str):
        return value.replace(key, REDACTED)
    if isinstance(value, dict):
        return {k: redact(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    return value


def error_envelope(subtype, turns=0, error_type=None, status=None):
    envelope = {"type": "result", "subtype": subtype, "is_error": True, "result": None, "num_turns": turns,
                "total_cost_usd": None, "usage": None, "modelUsage": None, "session_id": None, "duration_ms": None,
                "route": "api", "api_error_status": http_status(status), "kst_end": kst_now_text()}
    if error_type:
        envelope["error_type"] = error_type
    return envelope


def result_envelope(message):
    """The final ResultMessage in the `claude -p --output-format json` keys. An is_error that is not a bool counts
    as an error (parse_judge_envelope accepts only is_error false)."""
    is_error = getattr(message, "is_error", None)
    turns = getattr(message, "num_turns", None)
    cost = getattr(message, "total_cost_usd", None)
    result = getattr(message, "result", None)
    return {
        "type": "result",
        "subtype": plain(getattr(message, "subtype", None)),
        "is_error": is_error if isinstance(is_error, bool) else True,
        "result": result if isinstance(result, str) else None,
        "num_turns": turns if isinstance(turns, int) and not isinstance(turns, bool) else None,
        "total_cost_usd": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost)
        else None,
        "usage": plain(getattr(message, "usage", None)),
        "modelUsage": plain(getattr(message, "model_usage", None)),
        "session_id": plain(getattr(message, "session_id", None)),
        "duration_ms": plain(getattr(message, "duration_ms", None)),
        "route": "api",
        "api_error_status": http_status(getattr(message, "api_error_status", None)),
        "kst_end": kst_now_text(),
    }


def build_options(sdk, args, key):
    return sdk.ClaudeAgentOptions(
        cli_path=args.cli,
        system_prompt={"type": "preset", "preset": "claude_code"},
        model=JUDGE_MODEL,
        effort=JUDGE_EFFORT,
        tools=list(JUDGE_TOOLS),
        disallowed_tools=list(JUDGE_DISALLOWED_TOOLS),
        max_turns=args.max_turns,
        max_budget_usd=args.budget,
        strict_mcp_config=True,
        setting_sources=list(JUDGE_SETTING_SOURCES),
        extra_args=dict(JUDGE_EXTRA_ARGS),
        env={"ANTHROPIC_API_KEY": key},
        cwd=args.cwd,
    )


async def run_query(sdk, prompt, options):
    """(last ResultMessage or None, assistant messages seen, exception or None). The CLI ends a failed run with an
    error result and then a non-zero exit (the SDK raises after yielding the result): the result wins."""
    last, seen, error = None, 0, None
    try:
        async for message in sdk.query(prompt=prompt, options=options):
            if isinstance(message, sdk.ResultMessage):
                last = message
            elif isinstance(message, sdk.AssistantMessage):
                seen += 1
    except Exception as exc:  # noqa: BLE001 - every failure must still end as one envelope
        error = exc
    return last, seen, error


def bad_arguments(args):
    prompt = args.prompt_file_line
    if not prompt or len(prompt) > PROMPT_LINE_LIMIT or any(not 32 <= ord(ch) < 127 for ch in prompt):
        return "prompt"
    if not 1 <= args.max_turns <= MAX_TURNS_LIMIT:
        return "max_turns"
    if not (math.isfinite(args.budget) and 0 < args.budget <= MAX_BUDGET_USD):
        return "budget"
    if not args.cli or not args.cwd:
        return "paths"
    return None


def build_envelope(args, key, sdk_loader):
    if not key:
        return error_envelope("no_key")
    problem = bad_arguments(args)
    if problem:
        return error_envelope("bad_arguments:%s" % problem)
    try:
        sdk = sdk_loader()
        options = build_options(sdk, args, key)
    except Exception as exc:  # noqa: BLE001 - import or option errors happen before any work
        return error_envelope("sdk_setup_error", error_type=type(exc).__name__)
    last, seen, error = asyncio.run(run_query(sdk, args.prompt_file_line, options))
    if last is not None:
        envelope = result_envelope(last)
        if error is not None:
            envelope["error_type"] = type(error).__name__
        return envelope
    if error is not None:
        return error_envelope("sdk_exception", turns=seen, error_type=type(error).__name__,
                              status=getattr(error, "api_error_status", None))
    return error_envelope("no_result", turns=seen)


def load_sdk():
    import importlib
    return importlib.import_module(SDK_MODULE)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Investment_V2 dev pipeline Judge through the Agent SDK (devq-api)")
    parser.add_argument("--role", choices=("judge",), required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--prompt-file-line", required=True)
    parser.add_argument("--max-turns", type=int, required=True)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv=None, environ=None, sdk_loader=load_sdk):
    environ = os.environ if environ is None else environ
    key = take_key(environ)  # first: the key never stays in this process environment
    args = parse_args(argv)
    envelope = redact(build_envelope(args, key, sdk_loader), key)
    key = None
    ok = envelope.get("is_error") is False
    turns = envelope.get("num_turns")
    try:
        Path(args.out).write_bytes(json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
    except OSError:
        ok = False
    print("SDK-AGENT %s %s turns=%s" % (args.role, "ok" if ok else "error", turns if isinstance(turns, int) else "none"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
