#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shadow_acceptance import record_attempt, semantic_fingerprint
from validation_common import load_json, validate_instance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--attempts-root", type=Path, required=True)
    parser.add_argument("--sessions-root", type=Path)
    parser.add_argument("--attempt-schema", type=Path, required=True)
    parser.add_argument("--progress-schema", type=Path, required=True)
    parser.add_argument("--lock-policy", type=Path)
    args = parser.parse_args()
    lock_policy = None
    if args.lock_policy:
        policy = load_json(args.lock_policy)
        lock_policy = policy.get("single_session_lock") or {}
    attempt, progress = record_attempt(load_json(args.input), progress_path=args.progress,
                                       attempts_root=args.attempts_root,
                                       fingerprint=semantic_fingerprint(args.repo_root),
                                       sessions_root=args.sessions_root,
                                       lock_policy=lock_policy)
    errors = validate_instance(attempt, args.attempt_schema) + validate_instance(progress, args.progress_schema)
    if errors:
        raise SystemExit("shadow ledger validation failed: " + "; ".join(errors))
    print(json.dumps({"attempt": attempt, "progress": progress}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
