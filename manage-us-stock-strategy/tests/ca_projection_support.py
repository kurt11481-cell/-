# Test-only helper (no scripts/ or production authority). Extracted verbatim (AST-identical
# across all three) from external read-only originals; only technical_projection, timestamp,
# TIMING_TICKERS are kept. Hardcoded repo path replaced by the repository ROOT.
# original: E:\사업\##금동한\chatgpt md_주식\ca-k3-boundary-reset-candidate-20260928T035112Z\successor-bundle\bundle_support.py
#   sha256: f4c5e058d6761d962dff599e8816a4281b0c6cc97390fa7e93309dac07e2eda7
# original: E:\사업\##금동한\chatgpt md_주식\ca-k3-boundary-reset-repair-20260928T060205Z\successor-bundle\bundle_support.py
#   sha256: 150519beedcd2cc457e982390971c6829560124f3286f32a3b4f7a5e45be9a48
# original: E:\사업\##금동한\chatgpt md_주식\ca-k3-official-source-observation-candidate-20260928T090844Z\successor-bundle\bundle_support.py
#   sha256: 171aa4be65c28250fc5c7417b957e8a00eed9fad41469c3bae814b92f3d6b7fe
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TIMING_TICKERS = ("MVLL", "SOXL", "MRVL", "SOXX")


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return result


def technical_projection(capture_artifacts, *, run_id, completed_session, generated_at,
                         corporate_action_artifacts=None, policy=None, decision_as_of=None):
    """Use actual saved pairs and the existing calculator. Unresolved stays true."""
    from run_manual_portfolio_analysis import _parent_capture_evidence
    from build_kiwoom_market_snapshot import normalize_series
    from kiwoom_replay_validation import calculate_kiwoom_technical
    from validation_common import canonical_hash
    from kiwoom_runtime_bridge import validate_bridge_request
    captures = _parent_capture_evidence(capture_artifacts, run_id=run_id, observed_at=generated_at)
    series = {}
    for cap in captures:
        reqs = cap.get("requests", [])
        if cap.get("request_sha256") != canonical_hash(reqs) or len(reqs) != len(cap["results"]):
            raise ValueError("TECHNICAL_REQUEST_BINDING_INVALID")
        for req, response in zip(reqs, cap["results"]):
            symbol, basis = req.get("ticker"), req.get("price_basis")
            if symbol not in TIMING_TICKERS:
                continue
            key = symbol, basis
            if (key in series or basis not in {"RAW", "ADJUSTED"}
                    or req != validate_bridge_request(req)
                    or req.get("completed_session") != completed_session
                    or req.get("fx_applied") is not False
                    or response.get("operation") != "daily_chart"
                    or response.get("ticker") != symbol
                    or response.get("requested_price_basis") != basis
                    or response.get("bridge_status") != "PASS"):
                raise ValueError("TECHNICAL_PAIR_MISMATCH")
            when = timestamp(response["retrieved_at"])
            if not timestamp(cap["started_at"]) <= when <= timestamp(cap["observed_at"]) <= timestamp(generated_at):
                raise ValueError("TECHNICAL_TEMPORAL_ORDER_INVALID")
            if not 0 <= (timestamp(generated_at) - when).total_seconds() <= 900:
                raise ValueError("TECHNICAL_FRESHNESS_INVALID")
            series[key] = normalize_series(response.get("data"), ticker=symbol,
                completed_session=completed_session, price_basis=basis,
                minimum_history_bars=252 if basis == "ADJUSTED" else 1,
                pagination=response.get("pagination"))
    records = {}
    for symbol in TIMING_TICKERS:
        if (symbol, "RAW") not in series or (symbol, "ADJUSTED") not in series:
            raise ValueError("TIMING_RECORD_INPUT_MISSING")
        result = calculate_kiwoom_technical(series[symbol, "RAW"], series[symbol, "ADJUSTED"],
            cutoff=completed_session, minimum_history_bars=252, include_timing_record=True)
        if result["status"] != "KIWOOM_TECHNICAL_VALIDATED":
            raise ValueError("TIMING_CALCULATION_INVALID")
        records[symbol] = result["timing_record"]
    if corporate_action_artifacts is not None:
        from validate_technical_snapshot import validate_manual_corporate_actions
        if validate_manual_corporate_actions(corporate_action_artifacts, captures=capture_artifacts,
                required_symbols=list(TIMING_TICKERS), run_id=run_id,
                completed_session=completed_session, decision_as_of=decision_as_of or generated_at,
                policy=policy or {}):
            for row in records.values():
                row["corporate_action_unresolved"] = False
    return records
