#!/usr/bin/env python3
"""Validate canonical and installed Skill artifacts against the deployment gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ARTIFACTS = {
    "timing_engine": "scripts/timing_engine.py",
    "evaluator": "scripts/evaluate_alerts.py",
    "skill": "SKILL.md",
    "builder": "scripts/build_market_snapshot.py",
    "yfinance_contract": "references/yfinance-data.md",
    "output_locale": "assets/locales/ko-KR.json",
}


def normalized_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def validate_deployment(policy: dict[str, Any], source_root: Path, installed_root: Path) -> dict[str, Any]:
    gate = policy.get("deployment_gate") or {}
    errors: list[str] = []
    artifacts: list[dict[str, Any]] = []
    if gate.get("deployment_hash_normalization") != "utf8_without_bom_and_lf_line_endings":
        errors.append("UNSUPPORTED_HASH_NORMALIZATION")

    for name, relative in ARTIFACTS.items():
        source_path = source_root / relative
        installed_path = installed_root / relative
        required = str(gate.get(f"required_source_{name}_sha256") or "").upper()
        observed_claim = str(gate.get(f"observed_installed_{name}_sha256") or "").upper()
        source_hash = normalized_text_sha256(source_path) if source_path.is_file() else None
        installed_hash = normalized_text_sha256(installed_path) if installed_path.is_file() else None
        status = "MATCH" if source_hash == installed_hash == required == observed_claim else "MISMATCH"
        if status != "MATCH":
            errors.append(f"DEPLOYMENT_HASH_MISMATCH:{name}")
        artifacts.append({
            "artifact": name,
            "relative_path": relative.replace("\\", "/"),
            "required_hash": required or None,
            "policy_observed_hash": observed_claim or None,
            "source_hash": source_hash,
            "installed_hash": installed_hash,
            "status": status,
        })

    if gate.get("status") != "verified_installed_skill_sync":
        errors.append("DEPLOYMENT_STATUS_NOT_VERIFIED")
    if gate.get("automatic_timing_monitor_allowed") is not True:
        errors.append("AUTOMATIC_MONITOR_NOT_ALLOWED")
    return {
        "validation_status": "PASS" if not errors else "FAIL",
        "automatic_timing_monitor_allowed": not errors,
        "hash_normalization": gate.get("deployment_hash_normalization"),
        "artifacts": artifacts,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--source-skill-root", type=Path, required=True)
    parser.add_argument("--installed-skill-root", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8-sig"))
    result = validate_deployment(policy, args.source_skill_root, args.installed_skill_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
