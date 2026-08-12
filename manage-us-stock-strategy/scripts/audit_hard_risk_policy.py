#!/usr/bin/env python3
"""Create an explicit hard-risk approval/provenance audit artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from portfolio_policy_gates import hard_risk_rule_audit
from validation_common import load_json, validate_instance, write_json


def build_audit(policy: dict, generated_at: str) -> dict:
    positions = ((policy.get("holding_risk_rules") or {}).get("positions") or {})
    rules = [hard_risk_rule_audit(policy, symbol) for symbol in sorted(positions)]
    statuses = {item["policy_authority_status"] for item in rules}
    if statuses == {"VERIFIED"}:
        overall = "VERIFIED"
    elif "UNVERIFIED" in statuses:
        overall = "POLICY_AUTHORITY_UNVERIFIED"
    else:
        overall = "PARTIAL"
    return {
        "schema_version": "2.4",
        "generated_at": generated_at,
        "policy_version": str((policy.get("holding_risk_rules") or {}).get("rule_version") or "UNVERSIONED"),
        "rules": rules,
        "overall_status": overall,
        "order_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    outputs = (root / "workspace" / "outputs").resolve()
    try:
        args.output.resolve().relative_to(outputs)
    except ValueError as exc:
        raise SystemExit("--output must be under workspace/outputs") from exc
    if args.output.resolve() == args.policy.resolve():
        raise SystemExit("output may not alias policy input")
    audit = build_audit(load_json(args.policy), args.generated_at)
    errors = validate_instance(audit, root / "manage-us-stock-strategy" / "schemas" / "hard-risk-policy-audit.schema.json")
    if errors:
        raise SystemExit("hard-risk policy audit validation failed: " + "; ".join(errors))
    write_json(args.output, audit)
    print(json.dumps({"status": audit["overall_status"], "rules": len(audit["rules"]), "order_authority": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
