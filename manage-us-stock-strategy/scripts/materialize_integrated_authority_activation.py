#!/usr/bin/env python3
"""Materialize one caller-cohorted, non-authoritative K3 Shadow manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrated_authority_snapshot import (
    ROOT,
    build_combined_activation_manifest,
    write_shadow_combined_activation_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and validate a non-authoritative combined Identity/Session manifest",
    )
    parser.add_argument("--trusted-root", type=Path, default=ROOT)
    parser.add_argument("--identity-artifact-sha256", required=True)
    parser.add_argument("--session-calendar-artifact-sha256", required=True)
    parser.add_argument("--cohort-id", required=True)
    parser.add_argument("--previous-cohort-id", required=True)
    parser.add_argument("--activated-at", required=True)
    parser.add_argument("--activation-reason", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = build_combined_activation_manifest(
        trusted_root=args.trusted_root,
        identity_artifact_sha256=args.identity_artifact_sha256,
        session_calendar_artifact_sha256=args.session_calendar_artifact_sha256,
        cohort_id=args.cohort_id,
        previous_cohort_id=args.previous_cohort_id,
        activated_at=args.activated_at,
        activation_status="SHADOW",
        activation_reason=args.activation_reason,
    )
    manifest_hash = write_shadow_combined_activation_manifest(
        manifest,
        args.output,
        trusted_root=args.trusted_root,
    )
    print(json.dumps({
        "status": "PASS",
        "activation_status": "SHADOW",
        "activation_cohort_id": args.cohort_id,
        "combined_activation_manifest_sha256": manifest_hash,
        "output": str(args.output),
        "production_cutover_performed": False,
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
        "broker_submission": "disabled",
    }, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
