#!/usr/bin/env python3
"""Read-only post-activation validation for fixed K3 Production authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import integrated_authority_snapshot as integrated
from integrated_authority_snapshot import (
    COMBINED_ACTIVATION_RELATIVE_PATH,
    ROOT,
    derive_us_market_session_authority_from_snapshot,
    load_integrated_authority_snapshot,
    load_production_integrated_authority_snapshot,
    resolve_instrument_identity_from_snapshot,
)
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the active K3 Production snapshot without a broker")
    parser.add_argument("--trusted-root", type=Path, default=ROOT)
    parser.add_argument("--decision-as-of", required=True)
    parser.add_argument("--expected-cohort-id", required=True)
    parser.add_argument("--expected-identity-sha256", required=True)
    parser.add_argument("--expected-session-sha256", required=True)
    parser.add_argument("--expected-coverage-end", required=True)
    parser.add_argument("--target-session-date", required=True)
    parser.add_argument("--ticker", action="append", default=[])
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    reads: list[str] = []
    original = integrated.read_once_no_reparse

    def counted(path: Path, trusted_root: Path) -> bytes:
        reads.append(str(Path(path)))
        return original(path, trusted_root)

    integrated.read_once_no_reparse = counted
    try:
        snapshot = (
            load_integrated_authority_snapshot(
                args.manifest_path,
                trusted_root=args.trusted_root,
                decision_as_of=args.decision_as_of,
                required_activation_status="ACTIVE",
                resolved_at=args.decision_as_of,
                run_id="k3-production-pre-act-validation",
            )
            if args.manifest_path is not None
            else load_production_integrated_authority_snapshot(
                trusted_root=args.trusted_root,
                decision_as_of=args.decision_as_of,
                resolved_at=args.decision_as_of,
                run_id="k3-production-post-act-validation",
            )
        )
        construction_reads = len(reads)
        results = []
        for ticker in args.ticker:
            identity = resolve_instrument_identity_from_snapshot(
                snapshot,
                ticker,
                decision_as_of=args.decision_as_of,
            )
            session = derive_us_market_session_authority_from_snapshot(
                snapshot,
                args.decision_as_of,
                primary_listing_operating_mic=identity.primary_listing_operating_mic,
                decision_as_of=args.decision_as_of,
            )
            results.append({
                "ticker": ticker,
                "identity_status": identity.authority_status,
                "session_status": session.authority_status,
                "cohort_id": identity.activation_cohort_id,
            })
        later_reads = len(reads) - construction_reads
    finally:
        integrated.read_once_no_reparse = original

    sessions = snapshot.session.artifact["sessions"]
    target_session = next(
        (dict(item) for item in sessions if item["session_date"] == args.target_session_date),
        None,
    )
    manifest_name = (
        args.manifest_path.name
        if args.manifest_path is not None
        else COMBINED_ACTIVATION_RELATIVE_PATH.name
    )
    manifest_read_count = sum(Path(path).name == manifest_name for path in reads)
    checks = {
        "combined_manifest_read_once": manifest_read_count == 1,
        "authority_composition_reads": construction_reads == 3,
        "later_resolver_reads": later_reads == 0,
        "shared_cohort": snapshot.activation_cohort_id == args.expected_cohort_id,
        "identity_artifact": snapshot.identity.registry_hash == args.expected_identity_sha256,
        "session_artifact": snapshot.session.calendar_hash == args.expected_session_sha256,
        "coverage_end": snapshot.session.artifact["coverage_end"] == args.expected_coverage_end,
        "target_session_regular": bool(
            target_session
            and target_session.get("close_type") == "REGULAR"
            and str(target_session.get("core_open_at", "")).endswith("09:30:00-04:00")
            and str(target_session.get("core_close_at", "")).endswith("16:00:00-04:00")
        ),
        "all_tickers_verified": all(
            item["identity_status"] == "VERIFIED"
            and item["session_status"] == "VERIFIED"
            and item["cohort_id"] == args.expected_cohort_id
            for item in results
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "status": status,
        "authority_source": (
            "STAGED_PRODUCTION_CANDIDATE"
            if args.manifest_path is not None
            else "FIXED_PRODUCTION_COMBINED_MANIFEST"
        ),
        "checks": checks,
        "construction_read_count": construction_reads,
        "combined_manifest_read_count": manifest_read_count,
        "later_resolver_read_count": later_reads,
        "activation_cohort_id": snapshot.activation_cohort_id,
        "combined_activation_manifest_sha256": snapshot.combined_activation_manifest_sha256,
        "identity_artifact_sha256": snapshot.identity.registry_hash,
        "session_artifact_sha256": snapshot.session.calendar_hash,
        "coverage_end": snapshot.session.artifact["coverage_end"],
        "target_session": target_session,
        "ticker_results": results,
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
        "broker_submission": "disabled",
    }
    if args.output is not None:
        validate_shadow_output_path(
            args.output.resolve(),
            args.trusted_root.resolve(),
            protected=[
                args.trusted_root.resolve() / COMBINED_ACTIVATION_RELATIVE_PATH,
                args.trusted_root.resolve() / "workspace/policies/instrument_identity_activation.json",
                args.trusted_root.resolve() / "workspace/policies/session_calendar_activation.json",
            ],
        )
        atomic_write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
