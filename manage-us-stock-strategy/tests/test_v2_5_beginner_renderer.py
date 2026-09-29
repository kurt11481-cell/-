from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
from render_beginner_portfolio_report import render_beginner_summary
from validation_common import load_json, validate_instance


class V25BeginnerRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.locale = load_json(ROOT / "manage-us-stock-strategy/assets/locales/ko-KR.json")

    def holding(self, state, code, *, risk=False, execution="NOT_APPLICABLE"):
        return {"ticker": "TEST", "strategy_state": state, "display_action_code": code,
                "primary_reason_code": "TEST_REASON", "effective_price_status": "PRIMARY_VALIDATED",
                "execution_state": execution, "hard_risk_active": risk}

    def render(self, holding, **extra):
        report = {"data_status": extra.get("data_status", "VALIDATED"), "holding_strategies": [holding],
                  "tactical_radar_result": {"candidate_dispositions": []}, "snapshot_request": extra.get("snapshot_request", {})}
        return render_beginner_summary(report, self.locale)

    def test_v25_ui_01_hold(self):
        self.assertEqual(self.render(self.holding("HOLD", "HOLD_NO_ACTION"))["display_action"], "그대로 보유")

    def test_v25_ui_02_add_watch(self):
        self.assertEqual(self.render(self.holding("ADD_ON_WATCH", "ADD_WAIT"))["display_action"], "추가매수는 아직 기다리기")

    def test_v25_ui_03_add_pending_price(self):
        value = self.render(self.holding("ADD_REVIEW", "ADD_REVIEW", execution="VERIFICATION_PENDING"))
        self.assertEqual(value["display_action"], "추가매수 조건은 보이지만 가격 확인 중")

    def test_v25_ui_04_reduction(self):
        self.assertEqual(self.render(self.holding("REDUCTION_REVIEW", "REDUCE_REVIEW"))["display_action"], "일부 줄이기 검토")

    def test_v25_ui_05_hard_risk_priority(self):
        report = {"data_status": "VALIDATED", "holding_strategies": [self.holding("ADD_REVIEW", "ADD_REVIEW", risk=True)],
                  "tactical_radar_result": {"candidate_dispositions": [{"ticker": "BUY", "opportunity_state": "READY", "execution_state": "VERIFICATION_PENDING", "price_evidence": {"effective_price_status": "PRIMARY_VALIDATED"}}]}, "snapshot_request": {}}
        self.assertEqual(render_beginner_summary(report, self.locale)["display_action_code"], "RISK_REVIEW")

    def test_v25_ui_06_data_incomplete_not_no_alert(self):
        value = render_beginner_summary({"data_status": "DATA_INCOMPLETE", "holding_strategies": [], "tactical_radar_result": {"candidate_dispositions": []}, "snapshot_request": {}}, self.locale)
        self.assertEqual(value["display_action_code"], "DATA_ISSUE")
        self.assertNotEqual(value["display_action"], self.locale["messages"]["alert_none"])

    def test_v25_ui_07_core_python_ascii(self):
        for path in (ROOT / "manage-us-stock-strategy/scripts").glob("*.py"):
            self.assertTrue(path.read_text(encoding="utf-8").isascii(), path.name)

    def test_v25_ui_08_no_order_notice_and_schema(self):
        value = self.render(self.holding("HOLD", "HOLD_NO_ACTION"))
        self.assertTrue(value["no_order_notice"])
        self.assertEqual(validate_instance(value, ROOT / "manage-us-stock-strategy/schemas/beginner-portfolio-summary.schema.json"), [])


class ManualPhaseAReviewTests(unittest.TestCase):
    """Synthetic local evidence only; no production authority or broker calls."""

    def setUp(self):
        import tempfile
        from unittest.mock import patch
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manual_root = self.root / "manual"
        self.evidence_root = self.root / "evidence"
        self.evidence_root.mkdir()
        self.output_root = self.root / "reports"
        self.guard = patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN"))
        self.guard.start(); self.addCleanup(self.guard.stop)
        self.proc_guard = patch("subprocess.Popen", side_effect=AssertionError("SUBPROCESS_FORBIDDEN"))
        self.proc_guard.start(); self.addCleanup(self.proc_guard.stop)
        self.authority = {"order_authority": False, "quantity_authority": "none", "execution_quantity": None,
                          "automatic_order": False, "broker_submission": "disabled"}
        self.manual = self.manual_fixture()
        self.write_manual()

    @staticmethod
    def schema_fixture(schema):
        # Populate irrelevant mandatory fields; all decision-affecting fields below are explicit.
        if "const" in schema: return schema["const"]
        if "enum" in schema: return schema["enum"][0]
        kind = schema.get("type", "object")
        if isinstance(kind, list):
            if "null" in kind: return None
            kind = kind[0]
        if kind == "object":
            return {k: ManualPhaseAReviewTests.schema_fixture(schema.get("properties", {}).get(k, {})) for k in schema.get("required", [])}
        if kind == "array":
            if schema.get("uniqueItems") and "enum" in schema.get("items", {}): return schema["items"]["enum"][:schema.get("minItems", 0)]
            return [ManualPhaseAReviewTests.schema_fixture(schema.get("items", {})) for _ in range(schema.get("minItems", 0))]
        if kind == "null": return None
        if kind == "boolean": return False
        if kind in {"integer", "number"}: return schema.get("minimum", 0)
        if schema.get("format") == "date-time": return "2026-08-13T05:00:00Z"
        if schema.get("format") == "date": return "2026-08-12"
        if "64" in schema.get("pattern", ""): return "a" * 64
        return "TEST_ONLY"

    def manual_fixture(self):
        from validation_common import canonical_hash
        m = self.schema_fixture(load_json(ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"))
        m.update(manual_run_id="manual-synthetic-001", decision_as_of="2026-08-13T05:00:00Z",
                 report_type="MANUAL_PORTFOLIO_ANALYSIS_PREFLIGHT", run_mode="MANUAL_READ_ONLY",
                 preflight_status="PASS", evidence_grade="UNVERIFIED", broker_diff_status="MATCH",
                 identity_authority_status="VERIFIED", session_authority_status="VERIFIED",
                 integrated_authority_cohort_status="MATCHED", identity_activation_cohort_id="TEST_COHORT",
                 session_activation_cohort_id="TEST_COHORT", expected_completed_us_session="2026-08-12",
                 identity_registry_hash="b" * 64, calendar_hash="c" * 64)
        m["system_portfolio_state"].update(holdings={"NBIS": 13}, average_cost_usd={"NBIS": 100},
                                          available_cash_usd=120.10, state_revision=13,
                                          source_path="TEST_ONLY", source_sha256="d" * 64)
        m["broker_observed_state"].update(status="AVAILABLE", scope_complete=True,
            holdings=[{"ticker": "NBIS", "held_quantity": 13, "average_cost": 100, "currency": "USD"}],
            operation_statuses={"account_open_items": "PASS"},
            cash={"settled_available_cash": 120.10, "cash_status": "VERIFIED_POSITIVE", "currency": "USD"})
        m["integrated_authority_snapshot_provenance"].update(
            authority_source="K3_COMBINED_SHADOW", combined_activation_manifest_sha256="a" * 64,
            activation_cohort_id="TEST_COHORT", instrument_identity_artifact_sha256="b" * 64,
            session_calendar_artifact_sha256="c" * 64, authority_resolved_at=m["decision_as_of"],
            snapshot_decision_as_of=m["decision_as_of"], report_decision_as_of=m["decision_as_of"], run_id=m["manual_run_id"])
        m["integrated_authority_snapshot_provenance"]["identity_registry_version"] = m["identity_registry_version"]
        m["last_verified_finalized_bars"] = [{"ticker": "NBIS", "identity_authority_status": "VERIFIED",
            "identity_authority_reason": "OK", "primary_listing_segment_mic": "XNGS", "primary_listing_operating_mic": "XNAS",
            "session_authority_status": "VERIFIED", "session_authority_reason": "OK", "status": "VERIFIED",
            "bar_date": "2026-08-12", "technical_authority": True, "reason": None,
            "bar": {"price": 110, "bar_finalized": True, "indicative_only": False, "currency": "USD",
                    "price_basis": "RAW_REGULAR_SESSION_CLOSE", "provider_timestamp": "2026-08-13T04:59:00Z"}}]
        m["manual_analysis_view"].update(holdings={"NBIS": 13}, full_holding_analysis_performed=False)
        return m

    def put(self, path, value):
        import json, hashlib
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def write_manual(self):
        self.manual_path = self.manual_root / self.manual["manual_run_id"] / "manual-portfolio-analysis.json"
        self.manual_hash = self.put(self.manual_path, self.manual)

    def bundle(self, ticker="NBIS", **overlay_changes):
        from holding_research import compile_context, recompute_hashes
        from v2_6_test_helpers import valid_baseline, valid_overlay
        from validation_common import canonical_hash
        self.bundle_dir = self.evidence_root / ticker
        self.baseline = valid_baseline(ticker); self.baseline["content_status"] = "COMPLETE"
        self.baseline = recompute_hashes(self.baseline)
        self.overlay = valid_overlay(ticker, independent_price_status="NOT_REQUIRED", **overlay_changes)
        self.profile = {"ticker": ticker, "research_instrument_type": self.baseline["baseline_type"],
                        "identity_status": "verified_by_existing_active_policy"}
        if ticker in {"MVLL", "SOXL"}:
            self.profile.update(confirmation_proxy="MRVL" if ticker == "MVLL" else "SOXX",
                                confirmation_mode="DAILY_MULTIPLE" if ticker == "MVLL" else "DIRECTION_ONLY")
        portfolio = {"holdings": self.manual["system_portfolio_state"]["holdings"], "state_revision": 13}
        state_hash = self.put(self.bundle_dir / "portfolio.json", portfolio)
        self.manual["system_portfolio_state"]["source_sha256"] = state_hash
        self.write_manual()
        self.market = {"session": {"us_session_date": "2026-08-12", "regular_session_complete": True},
                       "symbols": {ticker: {"bar_date": "2026-08-12", "close": 110, "corporate_action_unresolved": False,
                                            "indicator_validation": {"status": "passed", "errors": []}}}}
        self.events = {"schema_version": "1.0", "snapshot_id": "TEST_ONLY", "snapshot_mode": "HISTORICAL",
                       "generated_at": self.manual["decision_as_of"], "analysis_cutoff": self.manual["decision_as_of"],
                       "market_session": "2026-08-12", "coverage_status": "COMPLETE", "events": [], "order_authority": False}
        self.manifest = self.schema_fixture(load_json(ROOT / "manage-us-stock-strategy/schemas/run-manifest.schema.json"))
        self.manifest.update(run_id="TEST_ONLY", analysis_id="TEST_ONLY", run_type="VALIDATION_TEST",
                             analysis_cutoff=self.manual["decision_as_of"], market_session="2026-08-12")
        self.manifest["input_hashes"].update(evidence_packet_hash=self.manual_hash, portfolio_state_hash=state_hash,
            market_snapshot_hash=self.put(self.bundle_dir / "market.json", self.market),
            event_snapshot_hash=self.put(self.bundle_dir / "events.json", self.events),
            instrument_registry_hash=self.put(self.bundle_dir / "registry.json", {"instruments": {ticker: self.profile}}),
            combined_activation_manifest_hash="a" * 64, instrument_identity_artifact_hash="b" * 64, session_calendar_artifact_hash="c" * 64)
        self.refresh_bundle()

    def refresh_bundle(self):
        from holding_research import compile_context
        from validation_common import canonical_hash
        self.put(self.bundle_dir / "baseline.json", self.baseline)
        self.put(self.bundle_dir / "overlay.json", self.overlay)
        compiled = compile_context(self.profile, self.baseline, self.overlay,
            baseline_schema=ROOT / "manage-us-stock-strategy/schemas/holding-research-baseline.schema.json")
        self.manifest["result_provenance"].update(research_packet_hash=self.baseline["research_packet_hash"],
            decision_record_hash=self.overlay["overlay_hash"], deterministic_gate_hash=canonical_hash(compiled), deterministic_gate_result="PASS")
        self.put(self.bundle_dir / "run_manifest.json", self.manifest)

    def review(self):
        from render_beginner_portfolio_report import build_manual_review
        value = build_manual_review(self.manual_root, evidence_roots=[self.evidence_root], test_evidence=True)
        for key, expected in self.authority.items(): self.assertEqual(value[key], expected)
        self.assertEqual(value["evidence_label"], "TEST")
        return value

    def test_a1_selection_uses_decision_time_not_mtime(self):
        import copy, os
        newer = copy.deepcopy(self.manual); newer["manual_run_id"] = "manual-synthetic-002"
        newer["decision_as_of"] = "2026-08-13T06:00:00Z"
        newer["integrated_authority_snapshot_provenance"].update(run_id=newer["manual_run_id"],
            snapshot_decision_as_of=newer["decision_as_of"], report_decision_as_of=newer["decision_as_of"])
        p = self.manual_root / newer["manual_run_id"] / "manual-portfolio-analysis.json"
        self.put(p, newer); os.utime(p, (1, 1))
        self.assertEqual(self.review()["manual_run_id"], newer["manual_run_id"])

    def test_a1_latest_failure_not_hidden(self):
        self.manual["preflight_status"] = "FAIL"; self.write_manual()
        self.assertEqual(self.review()["status"], "RUN_FAILED")

    def test_a1_ambiguous_same_time_blocks(self):
        import copy
        from render_beginner_portfolio_report import ManualReviewError
        other = copy.deepcopy(self.manual); other["manual_run_id"] = "manual-synthetic-002"
        self.put(self.manual_root / other["manual_run_id"] / "manual-portfolio-analysis.json", other)
        with self.assertRaisesRegex(ManualReviewError, "AMBIGUOUS"): self.review()

    def test_a1_id_mismatch_and_broken_json_do_not_fallback(self):
        from render_beginner_portfolio_report import ManualReviewError
        self.manual["manual_run_id"] = "manual-wrong-id"; self.put(self.manual_path, self.manual)
        with self.assertRaisesRegex(ManualReviewError, "RUN_PATH"): self.review()

    def test_a2_normal_strategy_countercase_portfolio(self):
        from render_beginner_portfolio_report import render_manual_review
        self.bundle()
        value = self.review()
        self.assertEqual(value["status"], "REVIEW_COMPLETE")
        self.assertEqual(value["rows"][0]["strategy_state"], "HOLD")
        self.assertTrue(value["rows"][0]["strongest_counter_case"])
        self.assertTrue(value["rows"][0]["invalidation"])
        self.assertEqual(value["portfolio_review"]["comparison"], {"NBIS": "HOLD"})
        summary, detail = render_manual_review(value)
        self.assertIn(self.baseline["strongest_counter_case"], summary)
        self.assertIn(self.baseline["claim_ids"][0], detail)

    def test_a2_existing_compiler_add_path(self):
        self.bundle(technical_status="READY")
        self.assertEqual(self.review()["rows"][0]["strategy_state"], "ADD_REVIEW")

    def test_a3_missing_research_stays_partial(self):
        value = self.review()
        self.assertEqual(value["status"], "PARTIAL")
        self.assertEqual(value["rows"][0]["status"], "DECISION_DEFERRED")
        self.assertIsNone(value["rows"][0]["strategy_state"])

    def test_a3_execution_evidence_failure_does_not_suppress_strategy(self):
        self.manual["broker_observed_state"]["scope_complete"] = False
        self.manual["broker_observed_state"]["operation_statuses"]["account_open_items"] = "ERROR"
        self.bundle()
        result = self.review()
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["rows"][0]["status"], "REVIEW_COMPLETE")

    def test_a4_cohort_mismatch_defers(self):
        self.bundle(); self.manifest["input_hashes"]["session_calendar_artifact_hash"] = "f" * 64
        self.put(self.bundle_dir / "run_manifest.json", self.manifest)
        self.assertIn("COHORT", self.review()["rows"][0]["blocker"])

    def test_a4_changed_bound_file_rejected(self):
        self.bundle(); self.market["symbols"]["NBIS"]["close"] = 111
        self.put(self.bundle_dir / "market.json", self.market)
        self.assertIn("BOUND_INPUT_MISSING", self.review()["rows"][0]["blocker"])

    def test_a4_future_retrieval_rejected_even_with_recomputed_hash(self):
        from holding_research import recompute_hashes
        self.bundle(); self.baseline["evidence"][0]["retrieved_at"] = "2026-08-14T00:00:00Z"
        self.baseline = recompute_hashes(self.baseline); self.refresh_bundle()
        self.assertIn("FUTURE_RESEARCH", self.review()["rows"][0]["blocker"])

    def test_a4_wrong_product_rejected(self):
        self.bundle(); self.profile["research_instrument_type"] = "SINGLE_STOCK_LEVERAGED_ETF"
        self.manifest["input_hashes"]["instrument_registry_hash"] = self.put(self.bundle_dir / "registry.json", {"instruments": {"NBIS": self.profile}})
        self.refresh_bundle()
        self.assertIn("ISSUER_PRODUCT", self.review()["rows"][0]["blocker"])

    def test_a4_broker_mark_cannot_be_completed_price(self):
        self.manual["last_verified_finalized_bars"][0]["bar"]["price_basis"] = "BROKER_MARK"
        self.bundle()
        self.assertIn("COMPLETED_PRICE", self.review()["rows"][0]["blocker"])

    def test_a4_false_gate_pass_rejected(self):
        self.bundle(); self.manifest["result_provenance"]["deterministic_gate_hash"] = "f" * 64
        self.put(self.bundle_dir / "run_manifest.json", self.manifest)
        self.assertIn("COMPILED_GATE", self.review()["rows"][0]["blocker"])

    def test_a5_difference_preserves_observation_and_ledger(self):
        self.manual["broker_diff_status"] = "DIFFERENT"
        self.manual["system_portfolio_state"].update(holdings={"NBIS": 15}, available_cash_usd=63.69)
        self.bundle()
        value = self.review(); row = value["rows"][0]
        self.assertEqual((row["observed_quantity"], row["ledger_quantity"]), (13, 15))
        self.assertEqual((value["broker_cash"]["settled_available_cash"], value["ledger_cash"]), (120.10, 63.69))
        self.assertEqual(row["status"], "DECISION_DEFERRED")

    def test_a6_empty_input_never_hold(self):
        self.manual["broker_observed_state"]["holdings"] = []; self.write_manual()
        value = self.review()
        self.assertEqual(value["status"], "PARTIAL"); self.assertEqual(value["rows"], [])

    def test_a6_one_missing_ticker_preserves_other_review(self):
        self.manual["broker_observed_state"]["holdings"].append({"ticker": "SOXL", "held_quantity": 75})
        self.manual["system_portfolio_state"]["holdings"]["SOXL"] = 75
        self.bundle()
        rows = {r["ticker"]: r for r in self.review()["rows"]}
        self.assertEqual(rows["NBIS"]["status"], "REVIEW_COMPLETE")
        self.assertEqual(rows["SOXL"]["status"], "DECISION_DEFERRED")

    def test_a7_quantity_authority_never_inherited(self):
        self.bundle(quantity=3, quantity_authority="deterministic_existing_policy",
                    deterministic_existing_policy={"rule_id": "TEST_ONLY", "action_on_breach": None})
        value = self.review()
        self.assertEqual(value["rows"][0]["status"], "REVIEW_COMPLETE")
        self.assertNotIn("quantity", value["rows"][0])

    def test_a9_output_retry_is_identical_no_source_changes(self):
        from render_beginner_portfolio_report import write_manual_review
        self.bundle(); before = {p: p.read_bytes() for p in self.root.rglob("*.json")}
        value = self.review(); first = write_manual_review(value, self.output_root)
        files = {p: p.read_bytes() for p in first.iterdir()}
        self.assertEqual(first, write_manual_review(self.review(), self.output_root))
        for p, content in {**before, **files}.items(): self.assertEqual(content, p.read_bytes())

    def test_a9_publication_failure_leaves_no_final_or_staging_output(self):
        from unittest.mock import patch
        from render_beginner_portfolio_report import ManualReviewError, write_manual_review
        with patch("os.rename", side_effect=OSError("TEST_PUBLICATION_FAILURE")):
            with self.assertRaises(ManualReviewError): write_manual_review(self.review(), self.output_root)
        self.assertEqual(list(self.output_root.iterdir()), [])

    def test_a9_protected_output_and_run_traversal_rejected(self):
        from render_beginner_portfolio_report import ManualReviewError, write_manual_review, select_manual_result
        with self.assertRaisesRegex(ManualReviewError, "PROTECTED_OUTPUT"):
            write_manual_review(self.review(), ROOT / "stock-strategy-system")
        with self.assertRaisesRegex(ManualReviewError, "INVALID_RUN_ID"):
            select_manual_result(self.manual_root, "../escape")

    def test_a9_existing_corrupt_report_not_overwritten(self):
        from render_beginner_portfolio_report import ManualReviewError, write_manual_review
        value = self.review(); path = write_manual_review(value, self.output_root)
        (path / "01_SUMMARY_KO.md").write_text("original", encoding="utf-8")
        with self.assertRaisesRegex(ManualReviewError, "COLLISION"): write_manual_review(value, self.output_root)
        self.assertEqual((path / "01_SUMMARY_KO.md").read_text(), "original")

    def test_a10_cli_returns_report_paths_without_broker(self):
        import contextlib, io, json
        from render_beginner_portfolio_report import manual_review_main
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = manual_review_main(["--manual-root", str(self.manual_root), "--evidence-root", str(self.evidence_root),
                                       "--output-root", str(self.output_root), "--test-evidence"])
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["status"], "PARTIAL")
        self.assertTrue(Path(result["summary"]).is_file())

    def test_a10_invalid_input_still_has_failure_report(self):
        import contextlib, io, json
        from render_beginner_portfolio_report import manual_review_main
        self.manual_path.write_text("{broken", encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = manual_review_main(["--manual-root", str(self.manual_root), "--output-root", str(self.output_root)])
        self.assertEqual(result, 2)
        saved = json.loads(stdout.getvalue())
        self.assertEqual(saved["status"], "RUN_FAILED")
        self.assertTrue(Path(saved["summary"]).exists())

    def test_a4_snapshot_time_can_precede_acquisition_completion(self):
        p = self.manual["integrated_authority_snapshot_provenance"]
        p["snapshot_decision_as_of"] = "2026-08-13T04:59:58Z"
        p["authority_resolved_at"] = "2026-08-13T04:59:58Z"
        self.bundle()
        self.assertEqual(self.review()["status"], "REVIEW_COMPLETE")

    def test_a4_future_manual_identity_rejected(self):
        self.manual["integrated_authority_snapshot_provenance"]["snapshot_decision_as_of"] = "2026-08-14T00:00:00Z"
        self.bundle()
        self.assertIn("MANUAL_IDENTITY", ";".join(self.review()["blockers"]))

    def test_a2_product_and_issuer_evidence_remain_distinct(self):
        import copy
        self.manual["broker_observed_state"]["holdings"].append({"ticker": "MVLL", "held_quantity": 5})
        self.manual["system_portfolio_state"]["holdings"]["MVLL"] = 5
        bar = copy.deepcopy(self.manual["last_verified_finalized_bars"][0]); bar["ticker"] = "MVLL"
        self.manual["last_verified_finalized_bars"].append(bar)
        self.bundle("NBIS"); self.bundle("MVLL")
        value = self.review(); self.assertEqual(value["status"], "REVIEW_COMPLETE")
        self.assertEqual([r["valuation_basis"] for r in value["rows"]], ["NBIS_ISSUER", "MRVL_ISSUER"])

    def test_a4_missing_underlying_component_blocks_product(self):
        from holding_research import recompute_hashes
        self.manual["broker_observed_state"]["holdings"][0]["ticker"] = "MVLL"
        self.manual["system_portfolio_state"]["holdings"] = {"MVLL": 13}
        self.manual["last_verified_finalized_bars"][0]["ticker"] = "MVLL"
        self.bundle("MVLL"); self.baseline["linked_components"] = []
        self.baseline = recompute_hashes(self.baseline); self.refresh_bundle()
        self.assertIn("PRODUCT_UNDERLYING", self.review()["rows"][0]["blocker"])

    def test_a9_duplicate_json_key_is_not_silently_accepted(self):
        from render_beginner_portfolio_report import ManualReviewError
        self.manual_path.write_text('{"manual_run_id":"first","manual_run_id":"second"}', encoding="utf-8")
        with self.assertRaises(ManualReviewError): self.review()

    def test_a9_report_does_not_enable_embedded_html(self):
        from holding_research import recompute_hashes
        from render_beginner_portfolio_report import render_manual_review
        self.bundle(); self.baseline["primary_reason"] = '<script>bad()</script> | [unsafe](file:///secret)'
        self.baseline = recompute_hashes(self.baseline); self.refresh_bundle()
        summary, _ = render_manual_review(self.review())
        self.assertNotIn('<script>', summary); self.assertNotIn('[unsafe]', summary)

    def test_a9_symlink_input_rejected(self):
        import os
        from render_beginner_portfolio_report import ManualReviewError, _review_read
        link = self.root / "link.json"
        try: os.symlink(self.manual_path, link)
        except OSError: self.skipTest("Windows symlink privilege unavailable")
        with self.assertRaisesRegex(ManualReviewError, "LINK_PATH"): _review_read(link)

    def test_a9_phase_a_source_remains_ascii(self):
        self.assertTrue((ROOT / "manage-us-stock-strategy/scripts/render_beginner_portfolio_report.py").read_text(encoding="utf-8").isascii())

    def test_a9_input_change_before_publication_is_rejected(self):
        from render_beginner_portfolio_report import ManualReviewError, write_manual_review
        value = self.review(); self.manual["broker_diff_status"] = "DIFFERENT"; self.write_manual()
        with self.assertRaisesRegex(ManualReviewError, "INPUT_CHANGED"):
            write_manual_review(value, self.output_root)

    def test_a2_validation_bundle_cannot_look_like_real_evidence(self):
        from render_beginner_portfolio_report import build_manual_review
        self.bundle()
        value = build_manual_review(self.manual_root, evidence_roots=[self.evidence_root])
        self.assertEqual(value["evidence_label"], "TEST")

    def test_a2_reference_concentration_is_not_target_allocation(self):
        self.bundle(); result = self.review()
        self.assertEqual(result["portfolio_review"]["holdings_only_reference_weights"], {"NBIS": 1.0})
        self.assertNotIn("target_weights", result)


if __name__ == "__main__":
    unittest.main()
