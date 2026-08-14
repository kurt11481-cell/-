#!/usr/bin/env python3
"""Create the external immutable deployment-provenance manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from deployment_provenance import build_provenance
from validation_common import validate_instance, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--preopen-task", required=True, type=Path)
    parser.add_argument("--postclose-task", required=True, type=Path)
    parser.add_argument("--kiwoom-runtime", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    value = build_provenance(
        repo=repo, task_configs=[args.preopen_task, args.postclose_task],
        code_paths=[repo / "manage-us-stock-strategy/scripts/shadow_acceptance.py",
                    repo / "manage-us-stock-strategy/scripts/dual_run_scheduler.py",
                    repo / "manage-us-stock-strategy/scripts/deployment_provenance.py"],
        policy_paths=[repo / "stock-strategy-system/alert_policy.json",
                      repo / "workspace/policies/dual_run_scheduler_policy.json",
                      repo / "workspace/policies/kiwoom-session-aware-priority-policy.json",
                      repo / "workspace/policies/source_capabilities.json"],
        provider_scope_path=repo / "workspace/policies/kiwoom-session-aware-priority-policy.json",
        progress_path=repo / "workspace/state/integrated_shadow/shadow_progress.json",
        dependency_paths={"python": args.python, "kiwoom_runtime": args.kiwoom_runtime},
    )
    errors = validate_instance(value, args.schema)
    if errors:
        raise SystemExit("DEPLOYMENT_PROVENANCE_SCHEMA_FAILED:" + ";".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, value)
    print(value["status"])
    return 0 if value["status"] == "DEPLOYMENT_PROVENANCE_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
