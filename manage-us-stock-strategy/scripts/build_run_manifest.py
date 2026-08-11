#!/usr/bin/env python3
"""Build a secret-free reproducibility manifest from explicit run inputs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from validation_common import file_hash, write_json


HASH_KEYS = [
    "evidence_packet_hash", "market_snapshot_hash", "event_snapshot_hash",
    "portfolio_state_hash", "strategy_policy_hash", "alert_policy_hash",
    "instrument_registry_hash", "candidate_universe_hash",
]


def _git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _working_tree_hash(repo: Path, status: str, diff: str) -> str:
    digest = hashlib.sha256()
    digest.update(status.encode("utf-8"))
    digest.update(diff.encode("utf-8"))
    for line in status.splitlines():
        relative = line[3:].strip()
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        path = (repo / relative).resolve()
        try:
            path.relative_to(repo)
        except ValueError:
            continue
        if path.is_file():
            digest.update(relative.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def build_manifest(args: argparse.Namespace) -> dict:
    repo = args.repo.resolve()
    supplied_hashes = dict(args.hash or [])
    input_hashes = {name: file_hash(supplied_hashes[name]) if name in supplied_hashes else None for name in HASH_KEYS}
    result_files = dict(args.result_hash or [])
    git_status = _git(["status", "--porcelain"], repo)
    git_diff = _git(["diff", "HEAD"], repo)
    git_dirty = bool(git_status and git_status != "UNAVAILABLE")
    diff_hash = _working_tree_hash(repo, git_status, git_diff) if git_dirty and git_diff != "UNAVAILABLE" else None
    return {
        "schema_version": "1.0",
        "run_id": args.run_id,
        "analysis_id": args.analysis_id,
        "run_type": args.run_type,
        "generated_at": args.generated_at,
        "analysis_cutoff": args.analysis_cutoff,
        "market_session": args.market_session,
        "code_provenance": {
            "git_commit": _git(["rev-parse", "HEAD"], repo),
            "git_branch": _git(["branch", "--show-current"], repo),
            "git_dirty": git_dirty,
            "working_tree_diff_hash": diff_hash,
            "skill_version": args.skill_version,
            "schema_versions": {"decision": "2.0", "event": "1.0", "manifest": "1.0", "evaluation": "1.0"},
            "strategy_version": args.strategy_version,
            "policy_version": args.policy_version,
        },
        "llm_provenance": {
            "provider": args.llm_provider,
            "model": args.llm_model,
            "model_identifier": args.llm_identifier,
            "temperature": args.temperature,
            "max_debate_rounds": args.max_debate_rounds,
            "max_risk_rounds": args.max_risk_rounds,
        },
        "input_hashes": input_hashes,
        "tool_provenance": {
            "python_version": platform.python_version(),
            "yfinance_version": _package_version("yfinance"),
            "schema_validator_version": "repo-subset-2020-12-v1",
            "event_validator_version": "1.0",
            "manifest_validator_version": "1.0",
        },
        "result_provenance": {
            "research_packet_hash": file_hash(result_files["research_packet_hash"]) if "research_packet_hash" in result_files else None,
            "decision_record_hash": file_hash(result_files["decision_record_hash"]) if "decision_record_hash" in result_files else None,
            "tactical_screen_hash": file_hash(result_files["tactical_screen_hash"]) if "tactical_screen_hash" in result_files else None,
            "deterministic_gate_hash": file_hash(result_files["deterministic_gate_hash"]) if "deterministic_gate_hash" in result_files else None,
            "deterministic_gate_result": args.gate_result,
        },
        "secrets_recorded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--run-type", required=True, choices=["HIGH_CONSEQUENCE_ANALYSIS", "TACTICAL_SHORTLIST", "HISTORICAL_EVALUATION", "LIVE_SHADOW_REVIEW", "VALIDATION_TEST"])
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--analysis-cutoff", required=True)
    parser.add_argument("--market-session")
    parser.add_argument("--skill-version", required=True)
    parser.add_argument("--strategy-version", required=True)
    parser.add_argument("--policy-version", required=True)
    parser.add_argument("--llm-provider")
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-identifier")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-debate-rounds", type=int, default=0)
    parser.add_argument("--max-risk-rounds", type=int, default=0)
    parser.add_argument("--hash", action="append", nargs=2, metavar=("NAME", "PATH"))
    parser.add_argument("--result-hash", action="append", nargs=2, metavar=("NAME", "PATH"))
    parser.add_argument("--gate-result", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_json(args.output, build_manifest(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
