#!/usr/bin/env python3
"""Archive the prior integrated-Shadow cohort and start the current semantics at zero."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from shadow_acceptance import initial_progress, semantic_fingerprint


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def migrate(root: Path, *, generated_at: str) -> dict:
    progress_path = root / "workspace/state/integrated_shadow/shadow_progress.json"
    prior = json.loads(progress_path.read_text(encoding="utf-8"))
    fingerprint = semantic_fingerprint(root)
    current = initial_progress(fingerprint, generated_at)
    if prior.get("semantic_fingerprint") == fingerprint:
        if prior.get("valid_shadow_sessions") != 0 or prior.get("observed_attempts") != 0:
            raise ValueError("CURRENT_SEMANTIC_COHORT_NOT_ZERO")
        return {"status": "COHORT_ALREADY_CURRENT", "cohort_id": prior["cohort_id"], "changed": False}

    archive_path = (root / "workspace/state/integrated_shadow/cohorts" /
                    prior["cohort_id"] / "superseded_progress.json")
    archived = {
        "schema_version": "1.0",
        "cohort_status": "COHORT_SUPERSEDED",
        "superseded_at": generated_at,
        "superseded_by": current["cohort_id"],
        "reason": "GLOBAL_AUTHORITY_VOLUME_AND_DUAL_RUN_SEMANTICS_CHANGE",
        "prior_progress": deepcopy(prior),
        "order_authority": False,
    }
    if archive_path.exists():
        existing = json.loads(archive_path.read_text(encoding="utf-8"))
        if existing != archived:
            raise ValueError("COHORT_ARCHIVE_CONFLICT")
    else:
        _atomic_write(archive_path, archived)
    _atomic_write(progress_path, current)
    return {
        "status": "COHORT_SUPERSEDED_AND_ZERO_INITIALIZED",
        "prior_cohort_id": prior["cohort_id"],
        "cohort_id": current["cohort_id"],
        "semantic_fingerprint": fingerprint,
        "archive_path": archive_path.relative_to(root).as_posix(),
        "changed": True,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    generated_at = datetime.now(timezone.utc).isoformat()
    print(json.dumps(migrate(Path(args.repo_root).resolve(), generated_at=generated_at), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
