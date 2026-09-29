#!/usr/bin/env python3
"""Verify the official documentation MCP without broker or portfolio access."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlparse

TOOLS = {"spec_search", "spec_show", "spec_groups", "get_example"}
CASES = [
    ("P1-01", "ust21050", "ust21050"),
    ("P1-02", "해외주식 예수금", "ust21110"),
    ("P1-03", "미국주식 원장잔고확인", "ust21070"),
    ("P1-04", "미국주식 일 차트", "usa06012"),
    ("P1-05", "exrt_appl_tp", "usa06012"),
]


def digest(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit_server(output: Path) -> None:
    """Guard and record a test server; leave upstream source unchanged."""
    audit = {"http_requests": [], "connections": [], "blocked": [], "credential_reads": []}
    addresses: set[str] = set()
    original_resolve = socket.getaddrinfo
    allowed_host = "raw.githubusercontent.com"
    write_json(output, audit)

    def record(category, value):
        audit[category].append(value)
        write_json(output, audit)

    def resolve(host, port, *args, **kwargs):
        name = host.decode() if isinstance(host, bytes) else str(host)
        if name not in {allowed_host, "127.0.0.1", "::1", "localhost"}:
            record("blocked", {"kind": "dns", "host": name})
            raise PermissionError("Documentation test blocked a non-documentation host")
        rows = original_resolve(host, port, *args, **kwargs)
        if name == allowed_host:
            addresses.update(str(row[4][0]) for row in rows)
        return rows

    def hook(event, args):
        if event == "urllib.Request":
            url = str(args[0])
            parsed = urlparse(url)
            allowed = (parsed.scheme == "https" and parsed.hostname == allowed_host
                       and parsed.path.startswith("/Kiwoom-Securities/Kiwoom-REST-API/main/examples/"))
            record("http_requests", {"url": url, "allowed": allowed})
            if not allowed:
                record("blocked", {"kind": "url", "host": parsed.hostname})
                raise PermissionError("Documentation test blocked a non-example URL")
        elif event == "socket.connect" and isinstance(args[1], tuple):
            host, port = str(args[1][0]), args[1][1]
            allowed = host in {"127.0.0.1", "::1"} or (host in addresses and port == 443)
            record("connections", {"host": host, "port": port, "allowed": allowed})
            if not allowed:
                record("blocked", {"kind": "connect", "host": host, "port": port})
                raise PermissionError("Documentation test blocked an unapproved connection")
        elif event == "open" and isinstance(args[0], (str, bytes)):
            name = Path(os.fsdecode(args[0])).name.lower()
            if name == ".env" or name.startswith(".env.") or name in {"credentials.json", "secrets.json", "token.json", "tokens.json"}:
                record("credential_reads", name)
                raise PermissionError("Documentation test blocked a credential file")

    socket.getaddrinfo = resolve
    sys.addaudithook(hook)
    from kiwoom_spec_mcp.server import main
    main()


def decode(result):
    if result.isError:
        raise RuntimeError("MCP returned isError")
    structured = result.structuredContent
    if structured is not None:
        return structured["result"] if set(structured) == {"result"} else structured
    texts = [item.text for item in result.content if item.type == "text"]
    return json.loads(texts[0]) if len(texts) == 1 else [json.loads(text) for text in texts]


async def verify(args) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    source_pin = json.loads(args.source_pin.read_text(encoding="utf-8"))
    expected = json.loads(args.expected_examples.read_text(encoding="utf-8"))
    local = json.loads(args.runtime_spec.read_text(encoding="utf-8"))
    local_apis = {value["meta"]["API ID"]: value for value in local["apis"].values()}
    pin_checks = {item["relative_path"]: digest((args.spec_project.parent / item["relative_path"]).read_bytes()) == item["sha256"]
                  for item in source_pin["files"]}
    result = {"schema_version": "1.0", "status": "RUNNING", "scope": "DOCUMENTATION_ONLY",
              "source_pin_checks": pin_checks, "rounds": [],
              "human_time_savings": "NOT_MEASURED", "broker_authority": False,
              "portfolio_mutation": False}
    if not all(pin_checks.values()):
        raise RuntimeError("Pinned official source changed")
    audit_path = args.output.parent / "network_audit.json"
    env = {"KIWOOM_MCP_TRANSPORT": "stdio", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
           "PYTHONNOUSERSITE": "1", "OTEL_SDK_DISABLED": "true", "FASTMCP_CHECK_FOR_UPDATES": "off",
           "FASTMCP_SHOW_SERVER_BANNER": "false"}
    # The SDK adds only its standard OS environment, not broker/profile/proxy values.
    result["explicit_environment_keys"] = sorted(env)
    server = StdioServerParameters(command=sys.executable,
        args=["-I", "-B", str(Path(__file__).resolve()), "--audit-server", "--audit-output", str(audit_path)],
        cwd=str(args.spec_project), env=env)
    start = time.perf_counter()
    with (args.output.parent / "mcp_server.stderr.log").open("w", encoding="utf-8") as errlog:
        async with stdio_client(server, errlog=errlog) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                init = await session.initialize()
                result["server_info"] = init.serverInfo.model_dump(mode="json")
                listed = await session.list_tools()
                result["tools"] = [tool.model_dump(mode="json") for tool in listed.tools]
                result["tool_allowlist_match"] = {tool.name for tool in listed.tools} == TOOLS
                result["readonly_annotations"] = all(tool.annotations and tool.annotations.readOnlyHint
                                                      and not tool.annotations.destructiveHint for tool in listed.tools)
                if not result["tool_allowlist_match"] or not result["readonly_annotations"]:
                    raise RuntimeError("Unexpected MCP tool exposure")

                async def call(name, arguments):
                    async with asyncio.timeout(40):
                        return decode(await session.call_tool(name, arguments))

                groups = await call("spec_groups", {})
                result["groups"] = groups
                result["overseas_group_present"] = any(item["market"] == "overseas" for item in groups)
                for order in [CASES, list(reversed(CASES))]:
                    rows = []
                    for case_id, query, api_id in order:
                        before = time.perf_counter()
                        found = await call("spec_search", {"query": query, "market": "overseas", "limit": 30})
                        spec = await call("spec_show", {"api_id": api_id})
                        example = await call("get_example", {"api_id": api_id})
                        base = {key: value for key, value in spec.items() if key != "cli"}
                        code_hash = digest(example.get("code", ""))
                        row = {"case_id": case_id, "query": query, "api_id": api_id,
                               "search_match": any(item.get("api_id") == api_id for item in found),
                               "overseas_only": all(item.get("market") == "overseas" for item in found),
                               "spec_matches_local": base == local_apis[api_id],
                               "example_path": example.get("path"), "example_source": example.get("source"),
                               "example_hash": code_hash,
                               "example_matches_pinned_source": code_hash == expected[api_id]["sha256"],
                               "cli_metadata": spec.get("cli"),
                               "duration_seconds": round(time.perf_counter() - before, 4)}
                        if "error" in example:
                            row["example_error"] = example["error"]
                        row["pass"] = all(row[key] for key in ["search_match", "overseas_only", "spec_matches_local", "example_matches_pinned_source"])
                        rows.append(row)
                    result["rounds"].append(rows)
                result["english_queries"] = {}
                for query in ["account deposit", "US holdings", "daily bar"]:
                    value = await call("spec_search", {"query": query, "market": "overseas"})
                    result["english_queries"][query] = {"result_count": len(value), "requires_korean_or_id": not bool(value)}
                unknown = await call("spec_show", {"api_id": "__UNKNOWN_PILOT_API__"})
                result["unknown_api_preserved_as_error"] = bool(unknown.get("error"))
    result["duration_seconds"] = round(time.perf_counter() - start, 4)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    result["network_audit"] = audit
    result["broker_network_requests"] = 0 if not audit["blocked"] and all(item["allowed"] for item in audit["http_requests"]) else None
    result["credential_file_reads"] = len(audit["credential_reads"])
    result["status"] = "PASS" if (all(row["pass"] for rows in result["rounds"] for row in rows)
        and result["unknown_api_preserved_as_error"] and result["overseas_group_present"]
        and result["broker_network_requests"] == 0 and result["credential_file_reads"] == 0) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-server", action="store_true")
    parser.add_argument("--audit-output", type=Path)
    parser.add_argument("--spec-project", type=Path)
    parser.add_argument("--source-pin", type=Path)
    parser.add_argument("--expected-examples", type=Path)
    parser.add_argument("--runtime-spec", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.audit_server:
        if args.audit_output is None:
            parser.error("--audit-output is required")
        audit_server(args.audit_output)
        return 0
    for field in ["spec_project", "source_pin", "expected_examples", "runtime_spec", "output"]:
        if getattr(args, field) is None:
            parser.error("--" + field.replace("_", "-") + " is required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = asyncio.run(verify(args))
    except Exception as exc:
        result = {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc), "human_time_savings": "NOT_MEASURED"}
    write_json(args.output, result)
    print(json.dumps({"status": result["status"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
