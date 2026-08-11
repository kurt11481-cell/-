#!/usr/bin/env python3
"""Fail-closed independent input gate for the pre-registered SOXL study.

This audit deliberately refuses to manufacture a five-year result from the
one-year cache.  It accepts independently supplied SOXL/SOXX calendar-complete
CSV inputs and verifies the exact data span and ten 24m/6m walk-forward folds
before any strategy engine may run.  It does not mutate policy/state and does
not place or schedule orders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OOS_START = pd.Timestamp("2021-08-05")
OOS_END = pd.Timestamp("2026-08-04")
REQUIRED_FETCH_START = pd.Timestamp("2018-08-01")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_input(path: Path, symbol: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{symbol} input missing: {path}")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError(f"{symbol}: date column missing")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.set_index("date").sort_index()
    if frame.index.has_duplicates:
        raise ValueError(f"{symbol}: duplicate sessions")
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{symbol}: missing OHLCV columns {sorted(missing)}")
    if frame[list(required)].isna().any().any():
        raise ValueError(f"{symbol}: null OHLCV values")
    if frame.index[0] > REQUIRED_FETCH_START:
        raise ValueError(
            f"{symbol}: begins {frame.index[0].date()}, later than required 2018-08-01"
        )
    if OOS_START not in frame.index or OOS_END not in frame.index:
        raise ValueError(f"{symbol}: exact OOS endpoints are absent")
    return frame


def folds() -> list[dict[str, str]]:
    result = []
    test_start = OOS_START
    for fold in range(1, 11):
        test_end_exclusive = test_start + pd.DateOffset(months=6)
        test_end = test_end_exclusive - pd.Timedelta(days=1)
        if fold == 10:
            test_end = OOS_END
        train_start = test_start - pd.DateOffset(months=24)
        train_end = test_start - pd.Timedelta(days=1)
        result.append(
            {
                "fold": fold,
                "train_start": train_start.date().isoformat(),
                "train_end": train_end.date().isoformat(),
                "test_start": test_start.date().isoformat(),
                "test_end": test_end.date().isoformat(),
            }
        )
        test_start = test_end_exclusive
    if result[-1]["test_end"] != OOS_END.date().isoformat():
        raise AssertionError("ten folds do not end on required OOS endpoint")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--soxl", type=Path, required=True)
    parser.add_argument("--soxx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "SOXL_WALK_FORWARD_PROTOCOL_2026-08-05.md",
        "status": "failed_closed",
        "policy_activation_eligible": False,
        "oos_required": [OOS_START.date().isoformat(), OOS_END.date().isoformat()],
        "folds": folds(),
        "inputs": {},
    }
    try:
        frames = {
            "SOXL": load_input(args.soxl, "SOXL"),
            "SOXX": load_input(args.soxx, "SOXX"),
        }
        shared = frames["SOXL"].index.intersection(frames["SOXX"].index)
        if not frames["SOXL"].index.equals(frames["SOXX"].index):
            raise ValueError("SOXL/SOXX session calendars differ")
        for symbol, frame in frames.items():
            output["inputs"][symbol] = {
                "path": str(args.soxl if symbol == "SOXL" else args.soxx),
                "sha256": sha256(args.soxl if symbol == "SOXL" else args.soxx),
                "first_session": frame.index[0].date().isoformat(),
                "last_session": frame.index[-1].date().isoformat(),
                "row_count": len(frame),
            }
        output["shared_session_count"] = len(shared)
        output["status"] = "input_gate_passed_strategy_engine_not_implemented"
        output["reason"] = (
            "Inputs pass the independent span/schema gate. This partial audit must not "
            "be represented as a completed walk-forward result."
        )
    except Exception as exc:  # fail closed is the required behavior
        output["reason"] = f"{type(exc).__name__}: {exc}"
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0 if output["status"] == "input_gate_passed_strategy_engine_not_implemented" else 2


if __name__ == "__main__":
    raise SystemExit(main())
