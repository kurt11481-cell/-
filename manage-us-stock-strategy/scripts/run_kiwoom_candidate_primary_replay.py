#!/usr/bin/env python3
"""Run an immutable Kiwoom-candidate-Primary market-data replay.

The runner intentionally reuses an immutable yfinance evidence bundle and a
sanitized Kiwoom snapshot. It never writes portfolio, policy, runtime, cohort,
or provider-authority files and never counts replay cases as operational
Shadow sessions.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compare_kiwoom_yfinance import compare_snapshots
from kiwoom_adapter_io import atomic_write_json, validate_shadow_output_path
from kiwoom_replay_validation import calculate_kiwoom_technical, replay_status_axes
from point_in_time_context import baseline_reference
from validation_common import canonical_hash, file_hash, load_json, validate_instance


def _bars(value: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in value.get("bars", []) if isinstance(row, dict)]


def _series_view(value: dict[str, Any], cutoff: str, minimum: int) -> dict[str, Any]:
    bars = [deepcopy(row) for row in _bars(value) if str(row.get("session")) <= cutoff]
    complete = next((row for row in reversed(bars) if row.get("session") == cutoff), None)
    status = "PASS" if complete is not None and len(bars) >= minimum else "DATA_BLOCKED"
    return {
        "ticker": value.get("ticker"), "price_basis": value.get("price_basis"),
        "fx_applied": False, "completed_session": cutoff,
        "completed_close": complete.get("close") if complete else None,
        "bars": bars, "history_bar_count": len(bars),
        "minimum_history_bars": minimum,
        "history_status": "SUFFICIENT" if len(bars) >= minimum else "INSUFFICIENT_HISTORY",
        "validation_errors": [] if status == "PASS" else [
            "INSUFFICIENT_HISTORY" if complete is not None else "COMPLETED_SESSION_MISSING"
        ],
        "pagination": None, "status": status, "order_authority": False,
    }


def _yfinance_series(record: dict[str, Any], ticker: str, cutoff: str, *, adjusted: bool) -> dict[str, Any]:
    output: list[dict[str, Any]] = []
    for row in record.get("bars", []):
        session = str(row.get("session"))
        if session > cutoff:
            continue
        close = float(row["close"])
        factor = float(row.get("adjusted_close", close)) / close if adjusted and close else 1.0
        output.append({
            "session": session,
            "open": float(row["open"]) * factor,
            "high": float(row["high"]) * factor,
            "low": float(row["low"]) * factor,
            "close": float(row.get("adjusted_close", close)) if adjusted else close,
            "volume": float(row["volume"]),
        })
    completed = next((row for row in reversed(output) if row["session"] == cutoff), None)
    return {
        "ticker": ticker, "price_basis": "ADJUSTED" if adjusted else "RAW",
        "fx_applied": False, "completed_session": cutoff,
        "completed_close": completed.get("close") if completed else None,
        "bars": output, "history_bar_count": len(output),
        "minimum_history_bars": 1,
        "history_status": "SUFFICIENT" if output else "INSUFFICIENT_HISTORY",
        "validation_errors": [] if completed else ["COMPLETED_SESSION_MISSING"],
        "pagination": None, "status": "PASS" if completed else "DATA_BLOCKED",
        "order_authority": False,
    }


def _primary_snapshot(session: str, yfinance: dict[str, dict[str, Any]], generated_at: str) -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    for ticker, record in yfinance.items():
        row = next((bar for bar in record.get("bars", []) if bar.get("session") == session), None)
        if row:
            symbols[ticker] = {"bar_date": session, "close": float(row["close"])}
    return {
        "schema_version": "1.1", "generated_at_utc": generated_at,
        "session": {"us_session_date": session}, "symbols": symbols,
        "collection_provenance": {
            "provider": "yfinance", "provider_role": "INDEPENDENT_SHADOW_REPLAY_ONLY",
        },
        "order_authority": False,
    }


def _boundary_map(portfolio: dict[str, Any], alert_policy: dict[str, Any]) -> dict[str, float]:
    costs = portfolio.get("average_cost_usd") or {}
    rules = ((alert_policy.get("hard_risk_policy") or {}).get("rules") or {})
    boundaries: dict[str, float] = {}
    for ticker, rule in rules.items():
        cost = costs.get(ticker)
        fraction = rule.get("maximum_loss_fraction_from_average_cost") if isinstance(rule, dict) else None
        if isinstance(cost, (int, float)) and isinstance(fraction, (int, float)):
            boundaries[str(ticker)] = float(cost) * (1.0 - float(fraction))
    return boundaries


def current_context_status(
    *, session: str, event_bundle: dict[str, Any] | None,
    baseline_index: dict[str, Any] | None, repo_root: Path,
) -> dict[str, Any]:
    """Validate current context without borrowing it for historical replay."""
    event_status = "UNAVAILABLE"
    if isinstance(event_bundle, dict):
        same_session = event_bundle.get("market_session") == session
        event_status = (
            "COMPLETE" if same_session and event_bundle.get("coverage_status") == "COMPLETE"
            else "REVIEW_REQUIRED"
        )
    baselines: dict[str, str] = {}
    baseline_errors: list[str] = []
    active = baseline_index.get("active") if isinstance(baseline_index, dict) else None
    for ticker, entry in (active.items() if isinstance(active, dict) else []):
        try:
            relative = Path(str(entry["baseline_path"]))
            target = (repo_root / relative).resolve()
            target.relative_to(repo_root.resolve())
            reference, _ = baseline_reference(target)
            if reference["baseline_id"] != entry.get("baseline_id"):
                raise ValueError("BASELINE_ID_MISMATCH")
            if reference["baseline_hash"] != entry.get("baseline_hash"):
                raise ValueError("BASELINE_INDEX_HASH_MISMATCH")
            baselines[str(ticker)] = reference["baseline_hash"]
        except (KeyError, OSError, ValueError) as exc:
            baseline_errors.append(f"{ticker}:{type(exc).__name__}:{exc}")
    return {
        "event_context_status": event_status,
        "active_baseline_hashes": baselines,
        "baseline_validation_status": (
            "COMPLETE" if isinstance(active, dict) and len(baselines) == len(active) and not baseline_errors
            else "PARTIAL" if baselines else "UNAVAILABLE"
        ),
        "baseline_validation_errors": baseline_errors,
        "historical_context_reuse": False,
        "order_authority": False,
    }


def apply_current_context(dry_run: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(dry_run)
    active = context.get("active_baseline_hashes") or {}
    event_status = str(context.get("event_context_status") or "UNAVAILABLE")
    for row in value.get("results", []):
        ticker = str(row.get("ticker"))
        row["research_context_status"] = "COMPLETE" if ticker in active else "REFRESH_REQUIRED"
        row["event_context_status"] = event_status
        if row.get("strategy_or_opportunity_state") != "DATA_BLOCKED":
            if row["research_context_status"] != "COMPLETE" or event_status != "COMPLETE":
                row["strategy_or_opportunity_state"] = (
                    "STRATEGY_REFRESH_REQUIRED" if row.get("holding_status") == "VERIFIED_HELD"
                    else "TECHNICAL_SCREEN_AVAILABLE_RESEARCH_PENDING"
                )
    value["current_context"] = deepcopy(context)
    return value


def run_replay(
    *, kiwoom: dict[str, Any], yfinance_evidence: dict[str, Any], sessions: list[str],
    replay_policy: dict[str, Any], tolerance: dict[str, Any], portfolio: dict[str, Any],
    alert_policy: dict[str, Any], generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    minimum = int((replay_policy["market_data_provider_replay"]["minimum_history_bars"] ))
    yfinance = yfinance_evidence.get("records") or {}
    kiwoom_items = {str(item.get("ticker")): item for item in kiwoom.get("ticker_results", [])}
    tickers = sorted(kiwoom_items)
    boundaries = _boundary_map(portfolio, alert_policy)
    cases: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for session in sessions:
        session_items: list[dict[str, Any]] = []
        y_adjusted: dict[str, Any] = {}
        k_technical: dict[str, Any] = {}
        y_technical: dict[str, Any] = {}
        for ticker in tickers:
            item = kiwoom_items[ticker]
            raw = _series_view(item.get("raw") or {}, session, minimum)
            adjusted = _series_view(item.get("adjusted") or {}, session, minimum)
            status = "PASS" if raw["status"] == adjusted["status"] == "PASS" else "DATA_BLOCKED"
            session_items.append({
                "ticker": ticker, "identity": deepcopy(item.get("identity")),
                "raw": raw, "adjusted": adjusted, "status": status,
                "order_authority": False,
            })
            k_technical[ticker] = calculate_kiwoom_technical(
                raw, adjusted, cutoff=session, minimum_history_bars=minimum,
            )
            record = yfinance.get(ticker) or {}
            y_raw = _yfinance_series(record, ticker, session, adjusted=False)
            y_adjusted[ticker] = _yfinance_series(record, ticker, session, adjusted=True)
            y_result = calculate_kiwoom_technical(
                y_raw, y_adjusted[ticker], cutoff=session, minimum_history_bars=minimum,
            )
            if y_result["status"] == "KIWOOM_TECHNICAL_VALIDATED":
                y_result["status"] = "YFINANCE_TECHNICAL_VALIDATED"
                y_result["technical_price_basis"] = "yfinance Adjusted OHLC rescaled to latest yfinance Raw close"
            y_technical[ticker] = y_result
        session_snapshot = {
            "schema_version": kiwoom.get("schema_version", "1.0"),
            "generated_at": generated_at, "completed_session": session,
            "provider": "KIWOOM_REST", "primary_provider": "yfinance",
            "provider_state": "SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
            "official_runtime_commit": kiwoom.get("official_runtime_commit"),
            "session_lock": {"status": "LOCKED", "completed_session": session},
            "ticker_results": session_items, "data_status": "PARTIAL" if any(
                item["status"] != "PASS" for item in session_items
            ) else "COMPLETE",
            "operational_shadow_session_increment": 0, "order_authority": False,
        }
        comparison = compare_snapshots(
            session_snapshot, _primary_snapshot(session, yfinance, generated_at),
            tolerance_policy=tolerance, decision_boundaries=boundaries,
            generated_at=generated_at,
            adjustment_policy=replay_policy["adjustment_basis_policy"],
            yfinance_adjusted_series=y_adjusted,
            kiwoom_technical=k_technical, yfinance_technical=y_technical,
        )
        comparisons.append(comparison)
        comparison_map = {row["ticker"]: row for row in comparison["results"]}
        for ticker in tickers:
            item = kiwoom_items[ticker]
            k_result = k_technical[ticker]
            y_result = y_technical[ticker]
            compared = comparison_map[ticker]
            axes = replay_status_axes(
                market_data_valid=compared["raw_comparison_status"] == "MATCH",
                technical_status=k_result["status"],
                research_context_status="PARTIAL_EXPECTED_NO_ARCHIVE",
                event_context_status="PARTIAL_EXPECTED_NO_ARCHIVE",
                portfolio_context_status="PARTIAL_EXPECTED_NO_ARCHIVE",
            )
            cases.append({
                "ticker": ticker, "session": session,
                "identity_status": (item.get("identity") or {}).get("mapping_status"),
                "exchange_mapping": (item.get("identity") or {}).get("stex_tp"),
                "kiwoom_raw_status": (_series_view(item.get("raw") or {}, session, 1))["status"],
                "yfinance_raw_status": "PASS" if ticker in (_primary_snapshot(session, yfinance, generated_at)["symbols"]) else "DATA_BLOCKED",
                "raw_comparison_status": compared["raw_comparison_status"],
                "kiwoom_adjusted_status": (_series_view(item.get("adjusted") or {}, session, 1))["status"],
                "yfinance_adjusted_status": y_adjusted[ticker]["status"],
                "adjustment_basis_status": compared["adjustment_basis_status"],
                "adjusted_comparison_status": compared["adjusted_comparison_status"],
                "kiwoom_technical_status": k_result["status"],
                "kiwoom_history_rows": k_result["history_rows"],
                "yfinance_technical_status": y_result["status"],
                "technical_indicator_shadow_status": compared["technical_indicator_shadow_status"],
                "technical_decision_flip": compared["technical_decision_flip"],
                "kiwoom_decision_signature": deepcopy(k_result.get("decision_signature") or {}),
                "yfinance_decision_signature": deepcopy(y_result.get("decision_signature") or {}),
                "comparison_reason_codes": deepcopy(compared.get("adjusted_comparison_reason_codes") or []),
                "corporate_action_status": "NO_UNRESOLVED_CONFLICT",
                "status_axes": axes, "order_authority": False,
            })
    total = len(cases)
    counts = {
        "raw_evaluated": sum(row["raw_comparison_status"] in {"MATCH", "CONFLICT"} for row in cases),
        "raw_matches": sum(row["raw_comparison_status"] == "MATCH" for row in cases),
        "raw_conflicts": sum(row["raw_comparison_status"] == "CONFLICT" for row in cases),
        "kiwoom_technical_evaluated": total,
        "kiwoom_technical_pass": sum(row["kiwoom_technical_status"] == "KIWOOM_TECHNICAL_VALIDATED" for row in cases),
        "yfinance_technical_evaluated": total,
        "yfinance_technical_pass": sum(row["yfinance_technical_status"] == "YFINANCE_TECHNICAL_VALIDATED" for row in cases),
        "adjusted_explicitly_classified": sum(row["adjustment_basis_status"] in {"COMPATIBLE", "INCOMPATIBLE"} for row in cases),
        "adjusted_same_basis_conflicts": sum(
            row["adjustment_basis_status"] == "COMPATIBLE" and row["adjusted_comparison_status"] == "CONFLICT"
            for row in cases
        ),
        "technical_decision_flips": sum(bool(row["technical_decision_flip"]) for row in cases),
    }
    market_pass = all((
        total == len(sessions) * len(tickers), counts["raw_matches"] == total,
        counts["kiwoom_technical_pass"] == total,
        counts["yfinance_technical_pass"] == total,
        counts["adjusted_explicitly_classified"] == total,
        counts["adjusted_same_basis_conflicts"] == 0,
        counts["technical_decision_flips"] == 0,
    ))
    summary = {
        "schema_version": "1.0", "generated_at": generated_at,
        "replay_mode": "REPLAY_VALIDATION_ONLY",
        "official_sessions": sessions, "tickers": tickers,
        "historical_replay_sessions": len(sessions), "case_count": total,
        "market_data_provider_replay": "PASS" if market_pass else "PARTIAL",
        "full_strategy_context_replay": "PARTIAL_EXPECTED_NO_ARCHIVE",
        "counts": counts,
        "ticker_failures": sorted({row["ticker"] for row in cases if row["kiwoom_technical_status"] != "KIWOOM_TECHNICAL_VALIDATED"}),
        "historical_backfill_generated": False,
        "provider_authority_changed": False,
        "valid_operational_sessions_increment": 0,
        "order_authority": False,
    }
    summary["summary_hash"] = canonical_hash(summary)
    latest = sessions[-1]
    dry_rows = []
    for ticker in tickers:
        case = next(row for row in reversed(cases) if row["ticker"] == ticker and row["session"] == latest)
        held = int((portfolio.get("holdings") or {}).get(ticker, 0)) > 0
        dry_rows.append({
            "ticker": ticker, "holding_status": "VERIFIED_HELD" if held else "NOT_HELD",
            "market_data_status": case["status_axes"]["market_data_status"],
            "technical_status": case["kiwoom_technical_status"],
            "research_context_status": "REFRESH_REQUIRED",
            "event_context_status": "REVIEW_REQUIRED",
            "portfolio_context_status": "COMPLETE" if held else "ELIGIBILITY_REVIEW_REQUIRED",
            "strategy_or_opportunity_state": (
                "DATA_BLOCKED" if case["status_axes"]["market_data_status"] != "VALIDATED"
                or case["kiwoom_technical_status"] != "KIWOOM_TECHNICAL_VALIDATED"
                else "STRATEGY_REFRESH_REQUIRED" if held else "TECHNICAL_SCREEN_AVAILABLE_RESEARCH_PENDING"
            ),
            "delivery_status": "NOT_DELIVERED_VALIDATION_ONLY",
            "quantity": None, "order_authority": False,
        })
    dry_run = {
        "schema_version": "1.0", "run_mode": "CURRENT_SESSION_READ_ONLY_DRY_RUN",
        "session": latest, "results": dry_rows, "alert_delivered": False,
        "runtime_mutated": False, "operational_session_increment": 0,
        "order_authority": False,
    }
    return {"schema_version": "1.0", "results": cases, "order_authority": False}, summary, dry_run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--kiwoom-snapshot", required=True, type=Path)
    parser.add_argument("--yfinance-evidence", required=True, type=Path)
    parser.add_argument("--prior-replay-summary", required=True, type=Path)
    parser.add_argument("--replay-policy", required=True, type=Path)
    parser.add_argument("--rate-policy", required=True, type=Path)
    parser.add_argument("--tolerance-policy", required=True, type=Path)
    parser.add_argument("--portfolio-state", required=True, type=Path)
    parser.add_argument("--alert-policy", required=True, type=Path)
    parser.add_argument("--current-kiwoom-snapshot", type=Path)
    parser.add_argument("--current-yfinance-evidence", type=Path)
    parser.add_argument("--current-session")
    parser.add_argument("--current-event-bundle", type=Path)
    parser.add_argument("--current-baseline-index", type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    for output in ("replay_cases.json", "replay_summary.json", "current_session_dry_run.json"):
        protected = [
            args.kiwoom_snapshot, args.yfinance_evidence, args.prior_replay_summary,
            args.portfolio_state, args.alert_policy,
        ]
        protected.extend(path for path in (
            args.current_kiwoom_snapshot, args.current_yfinance_evidence,
            args.current_event_bundle, args.current_baseline_index,
        ) if path)
        validate_shadow_output_path(args.output_dir / output, args.repo_root, protected)
    policy = load_json(args.replay_policy)
    minimum = int((load_json(args.rate_policy).get("history_policy") or {})["minimum_history_bars"])
    policy = deepcopy(policy)
    policy["market_data_provider_replay"]["minimum_history_bars"] = minimum
    tolerance = load_json(args.tolerance_policy)["approved_direct_close_tolerance"]
    prior = load_json(args.prior_replay_summary)
    sessions = list(prior["official_sessions"])
    cases, summary, dry = run_replay(
        kiwoom=load_json(args.kiwoom_snapshot),
        yfinance_evidence=load_json(args.yfinance_evidence), sessions=sessions,
        replay_policy=policy, tolerance=tolerance,
        portfolio=load_json(args.portfolio_state), alert_policy=load_json(args.alert_policy),
        generated_at=args.generated_at,
    )
    current_inputs = (args.current_kiwoom_snapshot, args.current_yfinance_evidence, args.current_session)
    if any(current_inputs) and not all(current_inputs):
        raise SystemExit("CURRENT_SESSION_INPUTS_MUST_BE_COMPLETE")
    if all(current_inputs):
        _, current_summary, dry = run_replay(
            kiwoom=load_json(args.current_kiwoom_snapshot),
            yfinance_evidence=load_json(args.current_yfinance_evidence),
            sessions=[str(args.current_session)], replay_policy=policy,
            tolerance=tolerance, portfolio=load_json(args.portfolio_state),
            alert_policy=load_json(args.alert_policy), generated_at=args.generated_at,
        )
        dry["provider_comparison_summary"] = current_summary["counts"]
        dry["market_data_provider_status"] = current_summary["market_data_provider_replay"]
        context = current_context_status(
            session=str(args.current_session),
            event_bundle=load_json(args.current_event_bundle) if args.current_event_bundle else None,
            baseline_index=load_json(args.current_baseline_index) if args.current_baseline_index else None,
            repo_root=args.repo_root,
        )
        dry = apply_current_context(dry, context)
        dry["current_context_hashes"] = {
            "event_bundle": file_hash(args.current_event_bundle) if args.current_event_bundle else None,
            "baseline_index": file_hash(args.current_baseline_index) if args.current_baseline_index else None,
        }
    summary["input_hashes"] = {
        "kiwoom_snapshot": file_hash(args.kiwoom_snapshot),
        "yfinance_evidence": file_hash(args.yfinance_evidence),
        "prior_replay_summary": file_hash(args.prior_replay_summary),
        "replay_policy": file_hash(args.replay_policy),
        "portfolio_state": file_hash(args.portfolio_state),
    }
    summary["summary_hash"] = canonical_hash({
        key: value for key, value in summary.items() if key != "summary_hash"
    })
    errors = validate_instance(summary, args.schema)
    if errors:
        raise SystemExit("; ".join(errors))
    atomic_write_json(args.output_dir / "replay_cases.json", cases)
    atomic_write_json(args.output_dir / "replay_summary.json", summary)
    atomic_write_json(args.output_dir / "current_session_dry_run.json", dry)
    print(json.dumps({
        "market_data_provider_replay": summary["market_data_provider_replay"],
        "full_strategy_context_replay": summary["full_strategy_context_replay"],
        "counts": summary["counts"], "ticker_failures": summary["ticker_failures"],
        "order_authority": False,
    }, separators=(",", ":")))
    return 0 if summary["market_data_provider_replay"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
