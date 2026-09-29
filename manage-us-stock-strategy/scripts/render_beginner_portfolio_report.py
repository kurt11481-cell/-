#!/usr/bin/env python3
"""Render canonical portfolio codes into a deterministic beginner Korean first screen."""

from __future__ import annotations

from typing import Any


PRIORITY = {"RISK_REVIEW": 1, "BROKER_SNAPSHOT_REQUIRED": 2, "BROKER_CONFIRMATION_REQUIRED": 3,
            "DATA_ISSUE": 4, "EXIT_REVIEW": 5, "REDUCE_REVIEW": 6, "ADD_REVIEW": 7,
            "ADD_PRICE_CHECK": 7, "ADD_WAIT": 8, "STRATEGY_REVIEW": 8, "HOLD_NO_ACTION": 9}


def render_beginner_summary(report: dict[str, Any], locale: dict[str, Any]) -> dict[str, Any]:
    messages = locale.get("messages") or {}
    action_keys = locale.get("action_code_keys") or {}
    items: list[dict[str, Any]] = []
    for holding in report.get("holding_strategies", []):
        code = holding.get("display_action_code", "DATA_ISSUE")
        if holding.get("hard_risk_active"):
            code = "RISK_REVIEW"
        elif holding.get("execution_state") == "VERIFICATION_PENDING" and holding.get("strategy_state") == "ADD_REVIEW":
            code = "ADD_PRICE_CHECK"
        items.append({"ticker": holding.get("ticker"), "display_action_code": code,
                      "display_action": messages.get(action_keys.get(code), code),
                      "primary_reason_code": holding.get("primary_reason_code"),
                      "price_evidence_display_code": holding.get("effective_price_status", "DATA_BLOCKED"),
                      "execution_display_code": holding.get("execution_state")})
    for candidate in (report.get("tactical_radar_result") or {}).get("candidate_dispositions", []):
        if candidate.get("opportunity_state") not in {"READY", "NEAR_TRIGGER"}:
            continue
        code = "ADD_PRICE_CHECK" if candidate.get("execution_state") == "VERIFICATION_PENDING" else ("ADD_REVIEW" if candidate.get("opportunity_state") == "READY" else "ADD_WAIT")
        items.append({"ticker": candidate.get("ticker"), "display_action_code": code,
                      "display_action": messages.get(action_keys.get(code), code),
                      "primary_reason_code": candidate.get("primary_blocker"),
                      "price_evidence_display_code": (candidate.get("price_evidence") or {}).get("effective_price_status", "DATA_BLOCKED"),
                      "execution_display_code": candidate.get("execution_state")})
    request = report.get("snapshot_request") or {}
    if request.get("snapshot_request_status") == "REQUIRED":
        items.append({"ticker": "PORTFOLIO", "display_action_code": "BROKER_SNAPSHOT_REQUIRED",
                      "display_action": messages.get("action_broker_snapshot_required"),
                      "primary_reason_code": "BROKER_SNAPSHOT_REQUIRED",
                      "price_evidence_display_code": "NOT_APPLICABLE", "execution_display_code": request.get("execution_effect")})
    if report.get("data_status") == "DATA_INCOMPLETE" and not any(item["display_action_code"] == "RISK_REVIEW" for item in items):
        items.append({"ticker": "GLOBAL", "display_action_code": "DATA_ISSUE",
                      "display_action": messages.get("action_data_issue"), "primary_reason_code": "DATA_INCOMPLETE",
                      "price_evidence_display_code": "DATA_BLOCKED", "execution_display_code": "DATA_BLOCKED"})
    if not items:
        items.append({"ticker": "PORTFOLIO", "display_action_code": "HOLD_NO_ACTION",
                      "display_action": messages.get("action_hold_no_action"), "primary_reason_code": "NO_CHANGE",
                      "price_evidence_display_code": "PRIMARY_VALIDATED", "execution_display_code": "NOT_APPLICABLE"})
    items.sort(key=lambda item: (PRIORITY.get(item["display_action_code"], 99), str(item["ticker"])))
    top = items[0]
    price_code = top["price_evidence_display_code"]
    price_text = {"PRIMARY_VALIDATED": messages.get("price_primary_validated"),
                  "INDEPENDENT_VERIFIED": messages.get("price_independent_verified"),
                  "PRICE_CONFLICT": messages.get("price_conflict"),
                  "DATA_BLOCKED": messages.get("summary_data_issue")}.get(price_code, messages.get("price_verification_pending"))
    urgency = "URGENT" if top["display_action_code"] == "RISK_REVIEW" else ("REVIEW" if PRIORITY.get(top["display_action_code"], 99) <= 7 else ("WAIT" if PRIORITY.get(top["display_action_code"], 99) == 8 else "NONE"))
    return {"schema_version": "2.5", "locale": "ko-KR", "display_action_code": top["display_action_code"],
            "display_action": top["display_action"], "display_urgency": urgency,
            "why": str(top.get("primary_reason_code") or messages.get("generic_review_reason", "REVIEW_REQUIRED")),
            "price_verification": str(price_text or messages.get("generic_price_review", "PRICE_REVIEW_REQUIRED")),
            "what_changes_decision": messages.get("what_changes_decision", "NEXT_VALIDATED_EVIDENCE"),
            "no_order_notice": messages.get("no_order_notice", "NO_ORDER_PLACED_OR_SCHEDULED"),
            "items": items, "order_authority": False}


# Phase A reads saved evidence only. No runner, broker, policy writer or scheduler.
class ManualReviewError(ValueError):
    pass


def _review_time(value: Any):
    from datetime import datetime
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.utcoffset() is None:
            raise ValueError("timezone required")
        return result
    except (ValueError, TypeError) as exc:
        raise ManualReviewError("INVALID_TIMESTAMP") from exc


def _review_path(path):
    from pathlib import Path
    import stat
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0)
                                 & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ManualReviewError("LINK_PATH_NOT_ALLOWED")
    return path


def _review_read(path):
    import hashlib
    import json
    path = _review_path(path)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ManualReviewError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ManualReviewError("INPUT_TOO_LARGE")
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ManualReviewError("NONFINITE_JSON")))
        if not isinstance(value, dict):
            raise ManualReviewError("OBJECT_REQUIRED")
        return value, hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise ManualReviewError("INPUT_UNREADABLE:" + path.name) from exc


def _review_schema(value, name):
    from pathlib import Path
    from validation_common import validate_instance
    schema = Path(__file__).resolve().parents[1] / "schemas" / (name + ".schema.json")
    errors = validate_instance(value, schema)
    if errors:
        raise ManualReviewError("SCHEMA_INVALID:" + name)


def select_manual_result(manual_root, run_id=None):
    """Select by decision time, including failed runs; ambiguity never falls back."""
    import re
    root = _review_path(manual_root)
    if run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}", run_id):
        raise ManualReviewError("INVALID_RUN_ID")
    paths = [root / run_id / "manual-portfolio-analysis.json"] if run_id else sorted(root.glob("*/manual-portfolio-analysis.json"))
    candidates = []
    for path in paths:
        data, digest = _review_read(path)
        # An unreadable or unidentifiable run prevents silently choosing an older success.
        if data.get("manual_run_id") != path.parent.name:
            raise ManualReviewError("RUN_PATH_ID_MISMATCH")
        candidates.append((_review_time(data.get("decision_as_of")), path, data, digest))
    if not candidates:
        raise ManualReviewError("NO_MANUAL_RESULT")
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise ManualReviewError("AMBIGUOUS_LATEST_RUN")
    _, path, data, digest = candidates[0]
    _review_schema(data, "manual-portfolio-analysis")
    if data.get("run_mode") != "MANUAL_READ_ONLY" or data.get("report_type") != "MANUAL_PORTFOLIO_ANALYSIS_PREFLIGHT":
        raise ManualReviewError("NOT_MANUAL_EVIDENCE")
    return path, data, digest


def _review_identity(manual):
    import re
    provenance = manual.get("integrated_authority_snapshot_provenance") or {}
    cutoff = _review_time(manual["decision_as_of"])
    if (manual.get("identity_authority_status") != "VERIFIED"
            or manual.get("session_authority_status") != "VERIFIED"
            or manual.get("integrated_authority_cohort_status") != "MATCHED"
            or provenance.get("run_id") != manual["manual_run_id"]
            or _review_time(provenance.get("snapshot_decision_as_of")) > cutoff
            or _review_time(provenance.get("report_decision_as_of")) != cutoff
            or _review_time(provenance.get("authority_resolved_at")) > cutoff):
        raise ManualReviewError("MANUAL_IDENTITY_BINDING_UNVERIFIED")
    cohort = provenance.get("activation_cohort_id")
    if not cohort or manual.get("identity_activation_cohort_id") != cohort or manual.get("session_activation_cohort_id") != cohort:
        raise ManualReviewError("COHORT_MISMATCH")
    for key in ("combined_activation_manifest_sha256", "instrument_identity_artifact_sha256", "session_calendar_artifact_sha256"):
        if not isinstance(provenance.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", provenance[key]):
            raise ManualReviewError("AUTHORITY_HASH_MISSING")
    if (manual.get("identity_registry_version") != provenance.get("identity_registry_version")
            or manual.get("identity_registry_hash") != provenance.get("instrument_identity_artifact_sha256")
            or manual.get("calendar_hash") != provenance.get("session_calendar_artifact_sha256")):
        raise ManualReviewError("AUTHORITY_IDENTITY_HASH_MISMATCH")
    return provenance


def _review_catalog(roots):
    """An in-memory index of existing JSON; never persists an index or creates evidence."""
    import re
    by_hash, manifests, diagnostics = {}, [], []
    seen = set()
    for root in roots:
        root = _review_path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if path in seen:
                continue
            seen.add(path)
            # Saved tests/replicas are not research sources, even with matching tickers.
            if any(re.search(r"(^|[-_])(test|tests|fixture|fixtures|replica|candidate)([-_]|$)", part.lower()) for part in path.relative_to(root).parts):
                continue
            try:
                value, digest = _review_read(path)
            except ManualReviewError:
                diagnostics.append("UNREADABLE_EVIDENCE:" + str(path))
                continue
            by_hash.setdefault(digest, (path, value))
            if path.name == "run_manifest.json":
                manifests.append((path, value, digest))
    return by_hash, manifests, diagnostics


def _review_bundle(manual, manual_hash, ticker, catalog):
    """Reuse an existing manifest's hashes, not filenames or a self-asserted PASS."""
    from pathlib import Path
    from holding_research import compile_context, validate_baseline, validate_overlay_hash
    from validation_common import canonical_hash
    import math
    by_hash, manifests, _ = catalog
    provenance = _review_identity(manual)
    cutoff = _review_time(manual["decision_as_of"])
    session = manual.get("expected_completed_us_session")
    matches, reasons = [], []
    for manifest_path, manifest, manifest_hash in manifests:
        inputs = manifest.get("input_hashes") or {}
        if inputs.get("evidence_packet_hash") != manual_hash:
            continue
        try:
            _review_schema(manifest, "run-manifest")
            if manual.get("evidence_grade") != "GRADE_B" and manifest.get("run_type") != "VALIDATION_TEST":
                raise ManualReviewError("MANUAL_EVIDENCE_GRADE_UNVERIFIED")
            if _review_time(manifest["analysis_cutoff"]) != cutoff or manifest.get("market_session") != session:
                raise ManualReviewError("MANIFEST_TIME_MISMATCH")
            for field, source in (("combined_activation_manifest_hash", "combined_activation_manifest_sha256"),
                                  ("instrument_identity_artifact_hash", "instrument_identity_artifact_sha256"),
                                  ("session_calendar_artifact_hash", "session_calendar_artifact_sha256")):
                if not provenance.get(source) or inputs.get(field) != provenance[source]:
                    raise ManualReviewError("MANIFEST_COHORT_HASH_MISMATCH")
            if inputs.get("portfolio_state_hash") != manual["system_portfolio_state"].get("source_sha256"):
                raise ManualReviewError("PORTFOLIO_HASH_MISMATCH")
            loaded = {}
            for name, field in (("market", "market_snapshot_hash"), ("events", "event_snapshot_hash"),
                                ("registry", "instrument_registry_hash"), ("portfolio", "portfolio_state_hash")):
                if inputs.get(field) not in by_hash:
                    raise ManualReviewError("BOUND_INPUT_MISSING:" + name)
                loaded[name] = by_hash[inputs[field]]
            result = manifest.get("result_provenance") or {}
            # Baseline packet/overlay use their existing canonical hashes, unlike raw file hashes above.
            baselines = [(p, v) for p, v in by_hash.values() if v.get("ticker") == ticker
                         and v.get("research_packet_hash") == result.get("research_packet_hash") and "baseline_id" in v]
            overlays = [(p, v) for p, v in by_hash.values() if v.get("ticker") == ticker
                        and v.get("overlay_hash") == result.get("decision_record_hash") and "market_session" in v]
            if len(baselines) != 1 or len(overlays) != 1:
                raise ManualReviewError("BASELINE_OVERLAY_BINDING_MISSING_OR_AMBIGUOUS")
            bp, baseline = baselines[0]; op, overlay = overlays[0]
            schema_root = Path(__file__).resolve().parents[1] / "schemas"
            check = validate_baseline(baseline, schema_root / "holding-research-baseline.schema.json")
            if check["validation_status"] != "PASSED" or baseline.get("content_status") != "COMPLETE":
                raise ManualReviewError("BASELINE_NOT_COMPLETE")
            for field in ("analysis_cutoff", "evidence_cutoff"):
                if _review_time(baseline[field]) > cutoff:
                    raise ManualReviewError("FUTURE_BASELINE")
            for evidence in baseline["evidence"]:
                for field in ("published_at", "retrieved_at", "effective_at", "evidence_cutoff"):
                    if _review_time(evidence.get(field)) > cutoff:
                        raise ManualReviewError("FUTURE_RESEARCH_EVIDENCE")
            _review_schema(overlay, "holding-research-overlay")
            if not validate_overlay_hash(overlay) or overlay["market_session"] != session:
                raise ManualReviewError("OVERLAY_HASH_OR_SESSION_MISMATCH")
            portfolio = loaded["portfolio"][1]
            if overlay["portfolio_state_revision"] != manual["system_portfolio_state"].get("state_revision"):
                raise ManualReviewError("OVERLAY_STATE_MISMATCH")
            if portfolio.get("holdings") != manual["system_portfolio_state"].get("holdings"):
                raise ManualReviewError("PORTFOLIO_CONTENT_MISMATCH")
            profile = dict((loaded["registry"][1].get("instruments") or {}).get(ticker) or {})
            if not profile or profile.get("identity_status") not in {"VERIFIED", "VERIFIED_PRIMARY", "verified_primary_sources", "verified_by_existing_active_policy"}:
                raise ManualReviewError("RESEARCH_IDENTITY_UNVERIFIED")
            profile["ticker"] = ticker
            expected_type = profile.get("research_instrument_type")
            if expected_type not in {"ISSUER_EQUITY", "SINGLE_STOCK_LEVERAGED_ETF", "SECTOR_LEVERAGED_ETF"} or baseline["baseline_type"] != expected_type:
                raise ManualReviewError("ISSUER_PRODUCT_MISMATCH")
            market = loaded["market"][1]
            market_session = market.get("session") or {}
            if market_session.get("us_session_date") != session or market_session.get("regular_session_complete") is not True:
                raise ManualReviewError("MARKET_NOT_COMPLETED")
            row = (market.get("symbols") or {}).get(ticker) or {}
            bars = [v for v in manual["last_verified_finalized_bars"] if v.get("ticker") == ticker]
            if len(bars) != 1:
                raise ManualReviewError("MANUAL_BAR_MISSING_OR_AMBIGUOUS")
            bar = bars[0]; raw = bar.get("bar") or {}
            price = raw.get("price")
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
                raise ManualReviewError("INVALID_COMPLETED_PRICE")
            if (bar.get("status") != "VERIFIED" or bar.get("technical_authority") is not True
                    or bar.get("bar_date") != session or raw.get("bar_finalized") is not True
                    or raw.get("indicative_only") is not False or raw.get("currency") != "USD"
                    or raw.get("price_basis") != "RAW_REGULAR_SESSION_CLOSE"
                    or row.get("close") != raw.get("price") or row.get("bar_date") != session
                    or row.get("corporate_action_unresolved") is not False
                    or (row.get("indicator_validation") or {}).get("status") != "passed"
                    or (row.get("indicator_validation") or {}).get("errors") != []
                    or _review_time(raw.get("provider_timestamp")) > cutoff):
                raise ManualReviewError("COMPLETED_PRICE_BINDING_FAILED")
            events = loaded["events"][1]
            _review_schema(events, "event-snapshot")
            if events.get("market_session") != session or _review_time(events["analysis_cutoff"]) > cutoff or events["coverage_status"] != "COMPLETE":
                raise ManualReviewError("EVENT_COVERAGE_INCOMPLETE")
            relevant = [e for e in events["events"] if e["ticker"] in {ticker, "GLOBAL"}]
            for event in relevant:
                if event["validation_status"] != "VALIDATED" or event["point_in_time_eligible"] is not True:
                    raise ManualReviewError("EVENT_UNVERIFIED")
                for field in ("announced_at", "retrieved_at"):
                    if _review_time(event.get(field)) > cutoff:
                        raise ManualReviewError("FUTURE_EVENT_KNOWLEDGE")
            if overlay["event_risk_status"] != ("KNOWN_EVENT" if relevant else "CLEAR"):
                raise ManualReviewError("EVENT_OVERLAY_MISMATCH")
            if (overlay["primary_price_status"] != "VALIDATED" or overlay["technical_status"] in {"UNAVAILABLE", "INVALID"}
                    or overlay["risk_status"] == "UNVERIFIED" or overlay["portfolio_fit_status"] in {"UNVERIFIED", "BLOCKED"}
                    or overlay["independent_price_status"] in {"PENDING", "UNAVAILABLE", "INCONCLUSIVE", "CONFLICT"}
                    or overlay["hard_risk_observation"] == "DATA_BLOCKED"):
                raise ManualReviewError("OVERLAY_EVIDENCE_INCOMPLETE")
            if overlay["hard_risk_observation"] == "PRIMARY_BREACH_OBSERVED":
                raise ManualReviewError("HARD_RISK_POLICY_BINDING_REVIEW_REQUIRED")
            if expected_type != "ISSUER_EQUITY":
                components = baseline.get("linked_components") or []
                if (not profile.get("confirmation_proxy") or not any(
                        c.get("ticker") == profile["confirmation_proxy"] and c.get("confirmation_mode") == profile.get("confirmation_mode")
                        for c in components) or overlay.get("leveraged_confirmation_status") != "ALIGNED"):
                    raise ManualReviewError("PRODUCT_UNDERLYING_BINDING_INCOMPLETE")
            compiled = compile_context(profile, baseline, overlay,
                                       baseline_schema=schema_root / "holding-research-baseline.schema.json")
            _review_schema(compiled, "compiled-holding-research-context")
            if result.get("deterministic_gate_result") != "PASS" or result.get("deterministic_gate_hash") != canonical_hash(compiled):
                raise ManualReviewError("COMPILED_GATE_BINDING_FAILED")
            if compiled["remaining_conditions"] or compiled["strategy_state"] in {"STRATEGY_REFRESH_REQUIRED", "DATA_BLOCKED"}:
                raise ManualReviewError("STRATEGY_INPUT_INCOMPLETE")
            # Deliberately project only analytical fields. Existing quantity authority is never copied.
            review = {k: compiled[k] for k in ("strategy_state", "primary_reason", "strongest_counter_case", "invalidation",
                       "next_review_trigger", "claim_ids", "valuation_basis", "valuation_applicability", "portfolio_fit_status")}
            review["status"] = "REVIEW_COMPLETE"
            review["completed_close"] = price
            review["evidence_run_type"] = manifest["run_type"]
            review["baseline_hash"] = baseline["baseline_hash"]
            review["overlay_hash"] = overlay["overlay_hash"]
            review["sources"] = [(str(manifest_path), manifest_hash)] + [(str(p), h) for h, (p, _) in by_hash.items() if p in {bp, op}]
            review["claims"] = baseline["claims"]
            review["evidence"] = baseline["evidence"]
            review["sources"].extend((str(p), inputs[field]) for (name, field) in
                                    (("market", "market_snapshot_hash"), ("events", "event_snapshot_hash"),
                                     ("registry", "instrument_registry_hash"), ("portfolio", "portfolio_state_hash"))
                                    for p, _ in [loaded[name]])
            matches.append(review)
        except (ManualReviewError, KeyError, TypeError, ValueError) as exc:
            reasons.append(str(exc))
    if len(matches) != 1:
        raise ManualReviewError("AMBIGUOUS_RESEARCH" if len(matches) > 1 else ";".join(sorted(set(reasons))) or "BOUND_RESEARCH_NOT_FOUND")
    return matches[0]


def build_manual_review(manual_root, *, run_id=None, evidence_roots=(), test_evidence=False):
    """Build an ephemeral read-only view; original provenance is retained, never promoted."""
    import math
    path, manual, digest = select_manual_result(manual_root, run_id)
    broker = manual["broker_observed_state"]
    system = manual["system_portfolio_state"]
    blockers, analysis_blockers = [], []
    try:
        _review_identity(manual)
    except ManualReviewError as exc:
        blockers.append(str(exc))
        analysis_blockers.append(str(exc))
    if manual["preflight_status"] != "PASS":
        blockers.append("PREFLIGHT_" + manual["preflight_status"])
        if manual["preflight_status"] == "FAIL":
            analysis_blockers.append("PREFLIGHT_FAIL")
    if broker.get("scope_complete") is not True:
        blockers.append("BROKER_SCOPE_INCOMPLETE")
    if manual.get("broker_diff_status") != "MATCH":
        blockers.append("BROKER_SYSTEM_DIFFERENCE")
    statuses = broker.get("operation_statuses") or {}
    blockers.extend("BROKER_OPERATION:" + str(k) + ":" + str(v) for k, v in statuses.items() if v != "PASS")
    catalog = _review_catalog(evidence_roots)
    holdings = broker.get("holdings") or []
    rows, seen = [], set()
    for holding in holdings:
        if not isinstance(holding, dict):
            raise ManualReviewError("MALFORMED_HOLDING")
        ticker = holding.get("ticker")
        quantity = holding.get("held_quantity")
        if not isinstance(ticker, str) or ticker in seen or isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity < 0:
            raise ManualReviewError("INVALID_OR_DUPLICATE_HOLDING")
        seen.add(ticker)
        if quantity == 0:
            continue
        row = {"ticker": ticker, "observed_quantity": quantity,
               "ledger_quantity": (system.get("holdings") or {}).get(ticker),
               "broker_average_cost": holding.get("average_cost"),
               "ledger_average_cost": (system.get("average_cost_usd") or {}).get(ticker),
               "status": "DECISION_DEFERRED", "strategy_state": None}
        try:
            if (analysis_blockers or broker.get("status") != "AVAILABLE"
                    or quantity != (system.get("holdings") or {}).get(ticker)):
                raise ManualReviewError("MANUAL_INPUT_PARTIAL")
            row.update(_review_bundle(manual, digest, ticker, catalog))
        except (ManualReviewError, ValueError, TypeError) as exc:
            row["blocker"] = str(exc)
        rows.append(row)
    if not rows:
        blockers.append("NO_VERIFIED_POSITIVE_HOLDINGS_REVIEW")
    if any(isinstance(q, (int, float)) and not isinstance(q, bool) and q > 0 and t not in seen
           for t, q in (system.get("holdings") or {}).items()):
        blockers.append("LEDGER_HOLDING_MISSING_FROM_BROKER")
    complete = bool(rows) and not blockers and all(r["status"] == "REVIEW_COMPLETE" for r in rows)
    reference_values = {r["ticker"]: r["observed_quantity"] * r["completed_close"] for r in rows} if complete else {}
    reference_total = sum(reference_values.values())
    reference_weights = {t: round(v / reference_total, 6) for t, v in reference_values.items()} if reference_total else {}
    status = "RUN_FAILED" if manual["preflight_status"] == "FAIL" or broker.get("status") != "AVAILABLE" else ("REVIEW_COMPLETE" if complete else "PARTIAL")
    return {"status": status, "manual_run_id": manual["manual_run_id"], "decision_as_of": manual["decision_as_of"],
            "source_path": str(path.absolute()), "source_sha256": digest, "source_grade": manual["evidence_grade"],
            "evidence_label": "TEST" if test_evidence or any(r.get("evidence_run_type") == "VALIDATION_TEST" for r in rows) else "ARCHIVED_MANUAL_REVIEW",
            "source_preflight": manual["preflight_status"], "source_provenance": manual["provenance"],
            "source_manifest": "NOT_PRESENT" if not (path.parent / "run_manifest.json").exists() else "PRESENT_NOT_VALIDATED",
            "rows": rows, "blockers": blockers, "evidence_diagnostics": catalog[2],
            "broker_cash": broker.get("cash"), "ledger_cash": system.get("available_cash_usd"),
            "current_price_evidence": manual["current_price_evidence"],
            "completed_bars": manual["last_verified_finalized_bars"],
            "portfolio_review": {"status": "REVIEW_COMPLETE" if complete else "DECISION_DEFERRED",
                "comparison": {r["ticker"]: r.get("strategy_state") for r in rows},
                "completed_close_holdings_values_usd": reference_values,
                "holdings_only_reference_weights": reference_weights,
                "cash_alternative": "CASH_REMAINS_AN_ALTERNATIVE; NO_ALLOCATION_APPROVED"},
            "next_action": ("\ud1b5\ud569 \ubcf4\uace0\uc11c\uc758 \uc804\ub7b5 \uadfc\uac70\uc640 \ubc18\ub860\uc744 \uac80\ud1a0\ud558\uc138\uc694." if complete else
                            "\ubcf4\uace0\uc11c\uc5d0 \ud45c\uc2dc\ub41c \ubbf8\ud655\uc778 \uc790\ub8cc\uc640 \uacc4\uc88c\xb7\uc7a5\ubd80 \ucc28\uc774\uc758 \uc6d0\uc778\uc744 \ud655\uc778\ud558\uc138\uc694."),
            "order_authority": False, "quantity_authority": "none", "execution_quantity": None,
            "automatic_order": False, "broker_submission": "disabled"}


def render_manual_review(review):
    import html
    import json
    def safe(value):
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        return html.escape(text, quote=True).replace("|", "&#124;").replace("\n", " ").replace("`", "&#96;").replace("[", "&#91;").replace("]", "&#93;")
    labels = {"PARTIAL": "\uc790\ub8cc \ubcf4\uc644 \ud544\uc694", "RUN_FAILED": "\uc785\ub825 \uac80\uc99d \uc2e4\ud328", "REVIEW_COMPLETE": "\uadfc\uac70\xb7\ubc18\ub860 \uac80\ud1a0 \uc644\ub8cc",
              "DECISION_DEFERRED": "\ud310\ub2e8 \uc720\ubcf4", "TEST": "\uac80\uc99d\uc6a9 \uac00\uc0c1 \uc790\ub8cc", "ARCHIVED_MANUAL_REVIEW": "\uc800\uc7a5\ub41c Manual \uc790\ub8cc",
              "HOLD": "\ubcf4\uc720 \uac80\ud1a0", "ADD_REVIEW": "\ucd94\uac00\ub9e4\uc218 \uac80\ud1a0", "ADD_ON_WATCH": "\ucd94\uac00\ub9e4\uc218 \uad00\ucc30",
              "REDUCTION_REVIEW": "\ucd95\uc18c \uac80\ud1a0", "EXIT_REVIEW": "\uc804\ub7c9 \ub9e4\ub3c4 \uac80\ud1a0", None: "\ud310\ub2e8 \uc720\ubcf4"}
    reasons = {"BROKER_SCOPE_INCOMPLETE": "\uacc4\uc88c \uc870\ud68c \ubc94\uc704\uac00 \uc644\uc804\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.",
               "BROKER_SYSTEM_DIFFERENCE": "\uad00\uce21\ud55c \uacc4\uc88c\uc640 \uc2dc\uc2a4\ud15c \uc7a5\ubd80\uc5d0 \ucc28\uc774\uac00 \uc788\uc2b5\ub2c8\ub2e4.",
               "MANUAL_INPUT_PARTIAL": "\ud574\ub2f9 \uc885\ubaa9\uc758 \uad00\uce21\xb7\uc7a5\ubd80 \uc77c\uce58 \ub610\ub294 \uac80\uc99d \uc785\ub825\uc774 \ubd80\uc871\ud569\ub2c8\ub2e4.",
               "BOUND_RESEARCH_NOT_FOUND": "\uc774 \uc2e4\ud589\uc5d0 \uc5f0\uacb0\ub41c \uc804\ub7b5\xb7\ubc18\ub860 \uadfc\uac70\ub97c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.",
               "NO_VERIFIED_POSITIVE_HOLDINGS_REVIEW": "\uac80\ud1a0\ud560 \ubcf4\uc720 \uc790\ub8cc\uac00 \ud655\uc778\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4."}
    def reason(value):
        return reasons.get(value, "\uc785\ub825 \uc790\ub8cc \uac80\uc99d\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \uae30\uc220 \uadfc\uac70\uc5d0 \uc6d0\uc778\uc744 \uae30\ub85d\ud588\uc2b5\ub2c8\ub2e4.")
    technical = ["# \uae30\uc220 \uadfc\uac70", "", "run_id: " + safe(review["manual_run_id"]), "source: " + safe(review["source_path"]),
                 "SHA256(raw bytes): " + review["source_sha256"], "\uc6d0\ubcf8 manifest: " + review["source_manifest"],
                 "\uc6d0\ubcf8 evidence grade(\uc7ac\uc778\uc99d \uc544\ub2d8): " + safe(review["source_grade"]),
                 "\uc6d0\ubcf8 provenance: " + safe(review["source_provenance"]),
                 "", "## \uac00\uaca9\uc758 \uad6c\ubd84", "\uc7a5\uc911 \ud45c\uc2dc\uac00\uaca9(reference only): " + safe(review["current_price_evidence"]),
                 "\uac80\uc99d\ub41c \uacfc\uac70 \uc644\ub8cc \ubd09(\ud604\uc7ac \uac00\uaca9 \uc544\ub2d8): " + safe(review["completed_bars"]),
                 "", "## \uc785\ub825 \uc81c\uc678 \ub0b4\uc5ed", safe(review["evidence_diagnostics"])]
    for row in review["rows"]:
        technical += ["", "## " + safe(row["ticker"]), "Broker \ud3c9\ub2e8: " + safe(row["broker_average_cost"]),
                      "\uc7a5\ubd80 \ud3c9\ub2e8: " + safe(row["ledger_average_cost"]), "\ucd9c\ucc98: " + safe(row.get("sources", [])),
                      "\uc8fc\uc7a5: " + safe(row.get("claims", [])), "\uc99d\uac70: " + safe(row.get("evidence", [])),
                      "\ucc28\ub2e8\uc0ac\uc720: " + safe(row.get("blocker"))]
    # Keep raw codes in the evidence file; the first screen is understandable without logs.
    friendly = ["# \ud3ec\ud2b8\ud3f4\ub9ac\uc624 \ud1b5\ud569 \uac80\ud1a0", "", "**" + labels.get(review["status"], "\ud310\ub2e8 \uc720\ubcf4") + " \xb7 " + labels[review["evidence_label"]] + "**",
                "", "\uc790\ub8cc \uae30\uc900: " + safe(review["decision_as_of"]) + " \u2014 \ud604\uc7ac \uacc4\uc88c\xb7\uac00\uaca9\uc774 \uc544\ub2d9\ub2c8\ub2e4.",
                "\uc6d0\ubcf8 \uc218\uc9d1 \ud310\uc815\uacfc \uc804\uccb4 \uc804\ub7b5 \uac80\ud1a0 \ud310\uc815\uc744 \uad6c\ubd84\ud588\uc2b5\ub2c8\ub2e4.", "",
                "| \uc885\ubaa9 | \ub2f9\uc2dc \uad00\uce21 \uc218\ub7c9 | \uc7a5\ubd80 \uc218\ub7c9 | \uac80\ud1a0 | \uc804\ub7b5 \ud6c4\ubcf4 |", "|---|---:|---:|---|---|"]
    for row in review["rows"]:
        friendly.append("| " + " | ".join([safe(row["ticker"]), safe(row["observed_quantity"]), safe(row["ledger_quantity"]),
                        labels.get(row["status"], "\ud310\ub2e8 \uc720\ubcf4"), labels.get(row.get("strategy_state"), "\ud310\ub2e8 \uc720\ubcf4")]) + " |")
    cash = review["broker_cash"] or {}
    friendly += ["", "\ub2f9\uc2dc \uad00\uce21 \ud604\uae08: $" + safe(cash.get("settled_available_cash")) + " / \uc7a5\ubd80 \ud604\uae08: $" + safe(review["ledger_cash"]),
                 "\ucc28\uc774\ub97c \uccb4\uacb0\xb7\ub9e4\ub3c4\ub300\uae08\uc73c\ub85c \ucd94\uc815\ud558\uac70\ub098 \uc7a5\ubd80\uc5d0 \ubc18\uc601\ud558\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.", "", "**\ud3ec\ud2b8\ud3f4\ub9ac\uc624 \uac80\ud1a0:** " + labels.get(review["portfolio_review"]["status"], "\ud310\ub2e8 \uc720\ubcf4")]
    for row in review["rows"]:
        friendly += ["", "**" + safe(row["ticker"]) + "**"]
        if row["status"] != "REVIEW_COMPLETE":
            friendly.append(reason(row.get("blocker"))); continue
        for label, key in (("\uc804\ub7b5 \uadfc\uac70", "primary_reason"), ("\uac00\uc7a5 \uac15\ud55c \ubc18\ub860", "strongest_counter_case"),
                           ("\ud310\ub2e8 \ud3d0\uae30 \uc870\uac74", "invalidation"), ("\ub2e4\uc74c \uac80\ud1a0 \uc870\uac74", "next_review_trigger"), ("\uae30\uc5c5\xb7\uc0c1\ud488 \uae30\uc900", "valuation_basis")):
            friendly.append(label + ": " + safe(row[key]))
    if review["blockers"]:
        friendly += ["", "**\ub0a8\uc740 \ud655\uc778 \uc0ac\ud56d**"]
        friendly.extend("- " + text for text in dict.fromkeys(reason(v) for v in review["blockers"]))
    weights = review["portfolio_review"].get("holdings_only_reference_weights", {})
    if weights:
        friendly += ["", "\uacfc\uac70 \uc644\ub8cc \uc885\uac00 \uae30\uc900 \ubcf4\uc720\uc885\ubaa9 \ub0b4 \ube44\uc911(\ud604\uae08 \uc81c\uc678): " + safe({t: str(round(w * 100, 2)) + "%" for t, w in weights.items()}),
                     "\ud604\uae08\ub3c4 \ub300\uc548\uc73c\ub85c \ub0a8\uae41\ub2c8\ub2e4. \uc704 \ube44\uc911\uc740 \ubaa9\ud45c\ube44\uc911\xb7\ud604\uc7ac NAV\xb7\uc704\ud5d8\ud55c\ub3c4 \ud310\uc815\uc774 \uc544\ub2d9\ub2c8\ub2e4."]
    friendly += ["", "**\uc9c0\uae08 \ud560 \uc77c \ud55c \uac00\uc9c0:** " + review["next_action"], "", "\uc8fc\ubb38 \uad8c\ud55c \uc5c6\uc74c \xb7 \uc2e4\ud589 \uc218\ub7c9 \uc5c6\uc74c \xb7 Broker \uc81c\ucd9c \ube44\ud65c\uc131"]
    technical += ["", "## \uc6d0\ub798 \uc0c1\ud0dc \ucf54\ub4dc\uc640 \ubcf4\uace0\uc11c \ub0b4\ubd80 \uac12", safe({k: review[k] for k in ("status", "blockers", "portfolio_review", "order_authority", "quantity_authority", "execution_quantity", "automatic_order", "broker_submission")})]
    return "\n".join(friendly) + "\n", "\n".join(technical) + "\n"


def write_manual_review(review, output_root):
    """Publish the two completed Markdown files together; identical retry reuses output."""
    import hashlib
    import os
    import shutil
    import tempfile
    from pathlib import Path
    source_refs = [(review["source_path"], review["source_sha256"])] if review["source_sha256"] != "NOT_VERIFIED" else []
    source_refs.extend(ref for row in review["rows"] for ref in row.get("sources", []))
    for source, digest in source_refs:
        if hashlib.sha256(_review_path(source).read_bytes()).hexdigest() != digest:
            raise ManualReviewError("INPUT_CHANGED_BEFORE_OUTPUT")
    root = _review_path(output_root)
    repo = Path(__file__).resolve().parents[2]
    allowed = repo / "workspace" / "outputs" / "phase-a-review"
    if root.is_relative_to(repo) and not root.is_relative_to(allowed):
        raise ManualReviewError("PROTECTED_OUTPUT_PATH")
    if any(part.lower() in {".git", "state", "policies", "runtime", "scripts", "schemas", "stock-strategy-system"} for part in root.parts):
        raise ManualReviewError("PROTECTED_OUTPUT_PATH")
    summary, technical = render_manual_review(review)
    content_id = hashlib.sha256((summary + "\0" + technical).encode("utf-8")).hexdigest()
    target = root / ("manual-review-" + content_id)
    contents = {"01_SUMMARY_KO.md": summary, "02_EVIDENCE_KO.md": technical}
    def existing():
        _review_path(target)
        return target.is_dir() and set(p.name for p in target.iterdir()) == set(contents) and all(
            _review_path(target / name).read_bytes() == body.encode("utf-8") for name, body in contents.items())
    if target.exists():
        if existing():
            return target
        raise ManualReviewError("OUTPUT_COLLISION_OR_INCOMPLETE")
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".phase-a-", dir=root))
    try:
        for name, body in contents.items():
            with (staging / name).open("xb") as handle:
                handle.write(body.encode("utf-8")); handle.flush(); os.fsync(handle.fileno())
        _review_path(root)
        try:
            os.rename(staging, target)
        except OSError:
            if not existing():
                raise ManualReviewError("OUTPUT_PUBLICATION_FAILED")
        return target
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def manual_review_main(argv=None):
    import argparse
    import json
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Read saved Manual evidence and render a Phase A review; no broker access")
    parser.add_argument("--manual-root", type=Path, default=repo / "workspace/outputs/manual-portfolio-analysis")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-root", type=Path, action="append")
    parser.add_argument("--output-root", type=Path, default=repo / "workspace/outputs/phase-a-review")
    parser.add_argument("--test-evidence", action="store_true")
    args = parser.parse_args(argv)
    try:
        review = build_manual_review(args.manual_root, run_id=args.run_id,
                    evidence_roots=args.evidence_root or [repo / "workspace/research"], test_evidence=args.test_evidence)
    except (ManualReviewError, OSError) as exc:
        review = {"status": "RUN_FAILED", "manual_run_id": args.run_id or "NOT_VERIFIED",
                  "decision_as_of": "NOT_VERIFIED", "source_path": str(args.manual_root),
                  "source_sha256": "NOT_VERIFIED", "source_grade": "UNVERIFIED", "source_preflight": "NOT_VERIFIED",
                  "source_manifest": "NOT_VERIFIED", "source_provenance": {}, "rows": [], "blockers": [str(exc)],
                  "evidence_diagnostics": [], "broker_cash": None, "ledger_cash": None,
                  "current_price_evidence": [], "completed_bars": [], "portfolio_review": {"status": "DECISION_DEFERRED"},
                  "evidence_label": "TEST" if args.test_evidence else "ARCHIVED_MANUAL_REVIEW",
                  "next_action": "\uc785\ub825 \uacb0\uacfc\uc758 \uc624\ub958 \ud56d\ubaa9\uc744 \ud655\uc778\ud558\uc138\uc694.",
                  "order_authority": False, "quantity_authority": "none", "execution_quantity": None,
                  "automatic_order": False, "broker_submission": "disabled"}
    try:
        target = write_manual_review(review, args.output_root)
        print(json.dumps({"status": review["status"], "summary": str(target / "01_SUMMARY_KO.md"),
                          "technical": str(target / "02_EVIDENCE_KO.md"), "order_authority": False}, ensure_ascii=True))
        return 2 if review["status"] == "RUN_FAILED" else 0
    except (ManualReviewError, OSError) as exc:
        print(json.dumps({"status": "RUN_FAILED", "reason": str(exc), "order_authority": False}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(manual_review_main())
