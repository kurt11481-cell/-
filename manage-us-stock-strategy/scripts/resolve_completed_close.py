#!/usr/bin/env python3
"""Resolve validated web evidence against one deterministic crosscheck request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from price_evidence import compare_close
from validation_common import load_json


def resolve(request: dict, evidence: dict) -> dict:
    primary = {"ticker": request["ticker"], "primary_session": request["completed_session"],
               "primary_close": request["primary_close"], "primary_price_basis": request["price_basis"],
               "currency": request["currency"], "primary_provider": "yfinance"}
    result = compare_close(primary, evidence, request.get("decision_boundaries") or [])
    return {**evidence, **result, "request_id": request["request_id"],
            "final_crosscheck_status": result["crosscheck_status"], "order_authority": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(resolve(load_json(args.request), load_json(args.evidence)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
