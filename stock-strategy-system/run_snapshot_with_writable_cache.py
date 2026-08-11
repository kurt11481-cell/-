"""Run the installed snapshot builder with a workspace-local yfinance cache."""

from __future__ import annotations

import runpy
import sys
import os
from pathlib import Path

import yfinance as yf


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIRECTORY = WORKSPACE_ROOT / ".runtime-cache" / "yfinance"


def main() -> None:
    builder_path_text = os.environ.get("STOCK_STRATEGY_BUILDER_PATH")
    if not builder_path_text:
        raise RuntimeError("STOCK_STRATEGY_BUILDER_PATH is required")
    builder_path = Path(builder_path_text)
    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(CACHE_DIRECTORY))
    sys.argv[0] = str(builder_path)
    runpy.run_path(str(builder_path), run_name="__main__")


if __name__ == "__main__":
    main()
