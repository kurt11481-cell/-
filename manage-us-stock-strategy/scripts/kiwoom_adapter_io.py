#!/usr/bin/env python3
"""Atomic output and alias protection for Kiwoom shadow artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def validate_shadow_output_path(output: Path, repo_root: Path, protected: list[Path] | None = None) -> None:
    root = repo_root.resolve()
    target = output.resolve()
    output_root = (root / "workspace" / "outputs").resolve()
    if output_root not in target.parents:
        raise ValueError("OUTPUT_MUST_BE_UNDER_WORKSPACE_OUTPUTS")
    canonical = {
        (root / "stock-strategy-system" / "portfolio_state.json").resolve(),
        (root / "stock-strategy-system" / "alert_policy.json").resolve(),
        (root / "stock-strategy-system" / "alert_runtime_state.json").resolve(),
    }
    canonical.update(item.resolve() for item in (protected or []))
    if target in canonical:
        raise ValueError("OUTPUT_PATH_ALIASES_PROTECTED_INPUT")


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
