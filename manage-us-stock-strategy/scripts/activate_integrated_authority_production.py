#!/usr/bin/env python3
"""Stage and explicitly activate the fixed K3 Production combined manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrated_authority_snapshot import (
    COMBINED_ACTIVATION_RELATIVE_PATH,
    ROOT,
    IntegratedAuthorityLoadError,
    build_combined_activation_manifest,
    write_production_combined_activation_manifest,
    write_staged_production_combined_activation_candidate,
)
from validation_common import file_hash, load_json


IDENTITY_ACTIVATION = Path("workspace/policies/instrument_identity_activation.json")
SESSION_ACTIVATION = Path("workspace/policies/session_calendar_activation.json")


def _legacy_baseline(
    root: Path,
    *,
    expected_identity_hash: str,
    expected_legacy_cohort_id: str,
) -> dict[str, object]:
    identity_path = root / IDENTITY_ACTIVATION
    session_path = root / SESSION_ACTIVATION
    identity = load_json(identity_path)
    session = load_json(session_path)
    if identity.get("activation_status") != "ACTIVE" or session.get("activation_status") != "ACTIVE":
        raise IntegratedAuthorityLoadError("LEGACY_PRODUCTION_NOT_ACTIVE")
    identity_cohort = identity.get("activation_cohort_id")
    session_cohort = session.get("activation_cohort_id")
    if identity_cohort != session_cohort or identity_cohort != expected_legacy_cohort_id:
        raise IntegratedAuthorityLoadError("LEGACY_PRODUCTION_COHORT_MISMATCH")
    if identity.get("active_registry_hash") != expected_identity_hash:
        raise IntegratedAuthorityLoadError("CONFLICTING_IDENTITY_PRODUCTION_EVIDENCE")
    return {
        "identity_activation_path": IDENTITY_ACTIVATION.as_posix(),
        "identity_activation_sha256": file_hash(identity_path),
        "identity_artifact_sha256": identity["active_registry_hash"],
        "identity_activation_version": identity["activation_schema_version"],
        "session_activation_path": SESSION_ACTIVATION.as_posix(),
        "session_activation_sha256": file_hash(session_path),
        "session_artifact_sha256": session["active_calendar_hash"],
        "session_activation_version": session["activation_schema_version"],
        "legacy_shared_cohort_id": identity_cohort,
        "legacy_session_coverage_start": session["coverage_start"],
        "legacy_session_coverage_end": session["coverage_end"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage a validated K3 ACTIVE manifest and optionally apply the first Production cutover",
    )
    parser.add_argument("--trusted-root", type=Path, default=ROOT)
    parser.add_argument("--identity-artifact-sha256", required=True)
    parser.add_argument("--session-calendar-artifact-sha256", required=True)
    parser.add_argument("--cohort-id", required=True)
    parser.add_argument("--expected-legacy-cohort-id", required=True)
    parser.add_argument("--activated-at", required=True)
    parser.add_argument("--activation-reason", required=True)
    parser.add_argument("--stage-output", required=True, type=Path)
    parser.add_argument("--apply-production-cutover", action="store_true")
    args = parser.parse_args()

    root = args.trusted_root.resolve()
    baseline = _legacy_baseline(
        root,
        expected_identity_hash=args.identity_artifact_sha256,
        expected_legacy_cohort_id=args.expected_legacy_cohort_id,
    )
    manifest = build_combined_activation_manifest(
        trusted_root=root,
        identity_artifact_sha256=args.identity_artifact_sha256,
        session_calendar_artifact_sha256=args.session_calendar_artifact_sha256,
        cohort_id=args.cohort_id,
        previous_cohort_id=args.expected_legacy_cohort_id,
        activated_at=args.activated_at,
        activation_status="ACTIVE",
        activation_reason=args.activation_reason,
    )
    staged_hash = write_staged_production_combined_activation_candidate(
        manifest,
        args.stage_output,
        trusted_root=root,
    )
    production_hash = None
    if args.apply_production_cutover:
        production_hash = write_production_combined_activation_manifest(
            manifest,
            trusted_root=root,
            expected_current_sha256=None,
        )
        if production_hash != staged_hash:
            raise IntegratedAuthorityLoadError("STAGED_PRODUCTION_HASH_MISMATCH")

    print(json.dumps({
        "status": "PASS",
        "legacy_baseline": baseline,
        "activation_status": "ACTIVE",
        "activation_cohort_id": args.cohort_id,
        "staged_manifest_path": str(args.stage_output),
        "staged_manifest_sha256": staged_hash,
        "production_manifest_path": (
            COMBINED_ACTIVATION_RELATIVE_PATH.as_posix()
            if args.apply_production_cutover
            else None
        ),
        "production_manifest_sha256": production_hash,
        "production_cutover_performed": args.apply_production_cutover,
        "automatic_rollback": False,
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
        "broker_submission": "disabled",
    }, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
