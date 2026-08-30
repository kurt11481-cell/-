from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

from save_daily_pipeline import (
    DEFAULT_LOCALE_PATH,
    DEFAULT_RULES_PATH,
    EVENTS_SCHEMA,
    MANIFEST_SCHEMA,
    VALIDATION_SCHEMA,
    PdfDocument,
    PipelineError,
    audit_static_paths,
    extract_date,
    extract_events,
    extract_tickers,
    load_pdf,
    map_event_type,
    map_portfolio_relevance,
    map_root_theses,
    route_materiality,
    run_pipeline,
    validate_schedule,
    validate_source,
)
from validation_common import file_hash, load_json, validate_instance


SAMPLE_PDF = ROOT.parent / "runtime/save-automation/fixtures/offline-replay/2026-08-28/SAVE_DAILY_2026-08-28.pdf"


class SaveDailyPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_json(DEFAULT_RULES_PATH)

    def make_blank_pdf(self, path: Path) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with path.open("wb") as stream:
            writer.write(stream)

    def sample_document(self, source: Path) -> PdfDocument:
        pages = (
            "SAVE 브리핑 자료 2026 년 08 월 2 8 일 ( 금 )",
            "오늘의 소식 2026 년 08 월 2 8 일 ( 금 )",
            "엔비디아, AI 매출 가이던스 상향 ( 원문 ) 오늘의 소식 "
            + "엔비디아가 AI 반도체 수요와 데이터센터 투자에 힘입어 가이던스를 상향했다고 SAVE가 보도함 - "
            + "이 내용은 SOXL과 NBIS root thesis 검토에 관련될 수 있으나 주문 신호가 아님 " * 2,
            "2026 년 7 월 4 주 차 주요 일정 1. 실적발표 - 구글, 테슬라, 인텔",
            "경제지표 02:00 - 미국 - 베이커휴즈 주요 일정 - 07 월 13 일 ( 월 )",
        )
        return PdfDocument(
            source_path=source.resolve(),
            source_sha256="a" * 64,
            source_file_size=1000,
            source_accessed_at="2026-08-30T00:00:00+00:00",
            page_count=len(pages),
            page_texts=pages,
            metadata={"/CreationDate": "D:20260828183922+09'00'"},
        )

    def run_sample(self, base: Path, run_id: str = "save-daily-test") -> tuple[dict, Path]:
        source = base / "SAVE_DAILY_2026-08-28.pdf"
        source.write_bytes(b"mocked-pdf")
        portfolio = base / "portfolio_state.json"
        policy = base / "alert_policy.json"
        portfolio.write_text(json.dumps({"last_updated_at": "2026-08-12T21:24:00+09:00"}), encoding="utf-8")
        policy.write_text(json.dumps({"schema_version": "test"}), encoding="utf-8")
        document = self.sample_document(source)
        with mock.patch("save_daily_pipeline.load_pdf", return_value=document):
            manifest = run_pipeline(
                source_path=source,
                expected_report_date="2026-08-28",
                output_root=base / "outputs",
                run_id=run_id,
                portfolio_path=portfolio,
                policy_path=policy,
            )
        run_dir = Path(manifest["artifact_paths"]["run_manifest"]).parent
        return manifest, run_dir

    def test_01_valid_pdf_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.pdf"
            self.make_blank_pdf(path)
            document = load_pdf(path)
            self.assertEqual(document.page_count, 1)
            self.assertEqual(len(document.source_sha256), 64)

    def test_02_missing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PipelineError, "EXTERNAL_FIXTURE_ACCESS_BLOCKED"):
                load_pdf(Path(directory) / "missing.pdf")

    def test_03_corrupt_invalid_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupt.pdf"
            path.write_bytes(b"not-a-pdf")
            with self.assertRaisesRegex(PipelineError, "INVALID_PDF"):
                load_pdf(path)

    def test_04_empty_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SAVE_DAILY_2026-08-28.pdf"
            self.make_blank_pdf(path)
            with self.assertRaisesRegex(PipelineError, "EMPTY_EXTRACTION"):
                run_pipeline(source_path=path, output_root=Path(directory) / "outputs")

    def test_05_report_date_extraction(self) -> None:
        self.assertEqual(extract_date("2026 년 08 월 2 8 일 ( 금 )"), "2026-08-28")
        self.assertEqual(extract_date("SAVE_DAILY_2026-08-28.pdf"), "2026-08-28")

    def test_06_filename_date_comparison(self) -> None:
        source = validate_source(self.sample_document(Path("SAVE_DAILY_2026-08-28.pdf")), self.rules, "2026-08-28")
        self.assertEqual(source["status"], "PASS")
        self.assertEqual(source["date_evidence"]["filename"], "2026-08-28")

    def test_07_section_extraction(self) -> None:
        document = self.sample_document(Path("SAVE_DAILY_2026-08-28.pdf"))
        events, raw_count = extract_events(document.page_texts, "2026-08-28", self.rules)
        self.assertEqual(raw_count, 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["section"], "TODAY_NEWS")

    def test_08_ticker_mapping(self) -> None:
        self.assertEqual(extract_tickers("마벨 (MRVL) and $NBIS", self.rules), ["MRVL", "NBIS"])

    def test_09_root_thesis_mapping(self) -> None:
        roots = map_root_theses("AI 클라우드 GPU 데이터센터 전력과 반도체 메모리", self.rules)
        self.assertIn("AI_INFRASTRUCTURE", roots)
        self.assertIn("SEMICONDUCTOR", roots)
        self.assertIn("DATA_CENTER_POWER", roots)
        self.assertNotIn("AI_INFRASTRUCTURE", map_root_theses("AI 모델 발표", self.rules))

    def test_10_event_type_mapping(self) -> None:
        self.assertEqual(map_event_type("AI 기업 무이자 전환사채 발행", self.rules), "CONVERTIBLE")
        self.assertEqual(map_event_type("연준 잭슨홀 연설", self.rules), "FED")

    def test_11_duplicate_handling(self) -> None:
        pages = [
            "SAVE 2026-08-28",
            "오늘의 소식 2026-08-28",
            "워시 잭슨홀 연설 시험대 오늘의 소식 연준 의장 워시의 잭슨홀 연설과 국채금리 영향 " * 5,
            "월가 워시 잭슨홀 메시지 주목 오늘의 소식 워시 의장의 잭슨홀 연설과 인플레이션 대응 " * 5,
            "2026 년 7 월 4 주 차 주요 일정",
        ]
        events, raw_count = extract_events(pages, "2026-08-28", self.rules)
        self.assertEqual(raw_count, 2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["duplicate_status"], "CLUSTERED")
        self.assertEqual(events[0]["article_count"], 2)

    def test_12_materiality_routing(self) -> None:
        title = "NBIS 실적 가이던스"
        relevance = map_portfolio_relevance(title, title, ["NBIS"], ["AI_INFRASTRUCTURE"], "GUIDANCE", self.rules)
        materiality, impact, materiality_reason, impact_reason = route_materiality(
            title, title, "GUIDANCE", ["AI_INFRASTRUCTURE"], relevance, self.rules,
        )
        self.assertEqual(materiality, "HIGH")
        self.assertEqual(impact, "REPRICE_REQUIRED")
        self.assertEqual(materiality_reason, "DIRECT_PORTFOLIO_TICKER_AND_MATERIAL_EVENT_TYPE")
        self.assertEqual(impact_reason, "DIRECT_HOLDING_REPRICE_EVENT")

    def test_13_schedule_conflict_handling(self) -> None:
        schedule = validate_schedule(
            self.sample_document(Path("SAVE_DAILY_2026-08-28.pdf")).page_texts,
            "2026-08-28",
            self.rules,
        )
        self.assertEqual(schedule["status"], "CONFLICTING")
        self.assertEqual(schedule["auto_use"], "NO")
        self.assertEqual(schedule["date_conflict_status"], "SECTION_DATE_CONFLICT")
        self.assertEqual(schedule["visual_validation"], "NOT_VERIFIED")

    def test_14_visual_validation_required_path(self) -> None:
        schedule = validate_schedule(["SAVE 2026-08-28", "오늘의 소식 2026-08-28"], "2026-08-28", self.rules)
        self.assertEqual(schedule["status"], "PARTIAL")
        self.assertEqual(schedule["visual_validation"], "NOT_VERIFIED")

    def test_15_no_network_path(self) -> None:
        source = ast.parse((SCRIPT_ROOT / "save_daily_pipeline.py").read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(source)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in ast.walk(source)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        self.assertTrue(imported.isdisjoint({"requests", "httpx", "socket", "urllib", "selenium", "playwright"}))
        self.assertEqual(
            {key: audit_static_paths()[key] for key in ("network_path_present", "broker_path_present", "order_path_present")},
            {"network_path_present": False, "broker_path_present": False, "order_path_present": False},
        )

    def test_16_no_save_login(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, _ = self.run_sample(Path(directory), "save-login-test")
            self.assertEqual(manifest["save_login"], "NO")

    def test_17_no_broker_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, _ = self.run_sample(Path(directory), "broker-test")
            self.assertEqual(manifest["broker_call"], "NO")

    def test_18_no_portfolio_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, _ = self.run_sample(base, "portfolio-test")
            self.assertEqual(manifest["portfolio_mutation"], "NO")
            self.assertEqual(manifest["protected_input_hashes"]["portfolio_state"], file_hash(base / "portfolio_state.json"))

    def test_19_no_policy_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, _ = self.run_sample(base, "policy-test")
            self.assertEqual(manifest["policy_mutation"], "NO")
            self.assertEqual(manifest["protected_input_hashes"]["alert_policy"], file_hash(base / "alert_policy.json"))

    def test_20_no_order_submission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, _ = self.run_sample(Path(directory), "order-test")
            self.assertEqual(manifest["orders"], "NONE")
            self.assertFalse(manifest["order_authority"])
            self.assertIsNone(manifest["execution_quantity"])
            self.assertFalse(manifest["automatic_order"])

    def test_21_create_only_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            _manifest, run_dir = self.run_sample(base, "create-only-test")
            original_hash = file_hash(run_dir / "dashboard.html")
            source = base / "SAVE_DAILY_2026-08-28.pdf"
            with mock.patch("save_daily_pipeline.load_pdf", return_value=self.sample_document(source)):
                with self.assertRaisesRegex(PipelineError, "RUN_COLLISION"):
                    run_pipeline(
                        source_path=source,
                        expected_report_date="2026-08-28",
                        output_root=base / "outputs",
                        run_id="create-only-test",
                        portfolio_path=base / "portfolio_state.json",
                        policy_path=base / "alert_policy.json",
                    )
            self.assertEqual(file_hash(run_dir / "dashboard.html"), original_hash)

    def test_22_existing_run_collision_prevents_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, _ = self.run_sample(base, "collision-test")
            self.assertTrue(Path(manifest["artifact_paths"]["run_manifest"]).is_file())
            collision = base / "outputs/2026-08-28/collision-test"
            self.assertTrue(collision.is_dir())

    def test_23_dashboard_html_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _manifest, run_dir = self.run_sample(Path(directory), "html-test")
            content = (run_dir / "dashboard.html").read_text(encoding="utf-8")
            self.assertIn("SAVE DAILY PORTFOLIO RADAR", content)
            self.assertIn("Order Authority", content)

    def test_24_dashboard_markdown_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _manifest, run_dir = self.run_sample(Path(directory), "markdown-test")
            content = (run_dir / "dashboard.md").read_text(encoding="utf-8")
            self.assertIn("## TODAY'S RESULT", content)
            self.assertIn("Automatic Order: OFF", content)

    def test_25_artifact_schemas_and_request_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, run_dir = self.run_sample(Path(directory), "schema-test")
            normalized = load_json(run_dir / "normalized-events.json")
            validation = load_json(run_dir / "validation-report.json")
            self.assertEqual(validate_instance(normalized, EVENTS_SCHEMA), [])
            self.assertEqual(validate_instance(validation, VALIDATION_SCHEMA), [])
            self.assertEqual(validate_instance(manifest, MANIFEST_SCHEMA), [])
            self.assertEqual(manifest["request_accounting"], "NOT_VERIFIED")
            self.assertEqual(set(manifest["artifact_hashes"]), {"normalized-events.json", "validation-report.json", "dashboard.html", "dashboard.md"})
            for name, digest in manifest["artifact_hashes"].items():
                self.assertEqual(digest, file_hash(run_dir / name))
            self.assertEqual(manifest["visual_validation"], "NOT_VERIFIED")
            self.assertEqual(set(manifest["implementation_provenance"]["schemas"]), {"normalized_events", "validation_report", "run_manifest"})
            self.assertEqual(len(manifest["implementation_provenance"]["save_daily_pipeline.py"]), 64)
            self.assertTrue(manifest["dependency_provenance"]["declared_pypdf_requirement"].startswith("pypdf"))
            self.assertTrue(manifest["dependency_provenance"]["runtime_pypdf_version"])
            self.assertTrue(manifest["dependency_provenance"]["python_version"])
            self.assertEqual(manifest["static_path_evidence"], {
                "network_path_present": False,
                "broker_path_present": False,
                "order_path_present": False,
            })

    def test_26_parenthetical_uppercase_false_positives(self) -> None:
        value = "(IG) (R) (LBO) (TPU) (CB) (CAPEX) (EPS)"
        self.assertEqual(extract_tickers(value, self.rules), [])

    def test_27_explicit_positive_tickers(self) -> None:
        value = "MRVL NVDA JPM CME Visa"
        self.assertEqual(extract_tickers(value, self.rules), ["CME", "JPM", "MRVL", "NVDA", "V"])

    def test_28_unrelated_legal_and_regulatory_are_low_no_change(self) -> None:
        for title, event_type in (
            ("FTC YouTube account suspension investigation", "REGULATORY"),
            ("Meta political hedging for congressional inquiry", "LEGAL"),
        ):
            relevance = map_portfolio_relevance(title, title, [], [], event_type, self.rules)
            materiality, impact, _materiality_reason, _impact_reason = route_materiality(
                title, title, event_type, [], relevance, self.rules,
            )
            self.assertEqual(relevance, [])
            self.assertEqual(materiality, "LOW")
            self.assertEqual(impact, "NO_CHANGE")

    def test_29_direct_relevant_capital_structure_can_be_high(self) -> None:
        title = "NBIS convertible financing"
        roots = ["AI_INFRASTRUCTURE"]
        relevance = map_portfolio_relevance(title, title, ["NBIS"], roots, "CONVERTIBLE", self.rules)
        materiality, impact, reason, _impact_reason = route_materiality(
            title, title, "CONVERTIBLE", roots, relevance, self.rules,
        )
        self.assertEqual(materiality, "HIGH")
        self.assertEqual(impact, "REPRICE_REQUIRED")
        self.assertEqual(reason, "DIRECT_PORTFOLIO_TICKER_AND_MATERIAL_EVENT_TYPE")

    @unittest.skipUnless(SAMPLE_PDF.is_file(), "external SAVE fixture unavailable")
    def test_30_actual_sample_semantic_contract(self) -> None:
        document = load_pdf(SAMPLE_PDF)
        events, _raw_count = extract_events(document.page_texts, "2026-08-28", self.rules)
        ftc = next(event for event in events if "FTC" in event["title"] and "유튜브" in event["title"])
        meta = next(event for event in events if "메타" in event["title"] and "정치적 헤지" in event["title"])
        ai = next(event for event in events if "전환사채" in event["title"] and "AI" in event["title"])
        for unrelated in (ftc, meta):
            self.assertEqual(unrelated["portfolio_relevance"], [])
            self.assertNotEqual(unrelated["materiality"], "HIGH")
            self.assertEqual(unrelated["decision_impact"], "NO_CHANGE")
        self.assertIn("AI_INFRASTRUCTURE", ai["root_theses"])
        self.assertIn(ai["materiality"], {"MEDIUM", "HIGH"})


if __name__ == "__main__":
    unittest.main()
