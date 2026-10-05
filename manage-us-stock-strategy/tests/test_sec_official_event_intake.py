from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

from sec_official_event_intake import (
    DEFAULT_RULES_PATH,
    EVENTS_SCHEMA,
    MANIFEST_SCHEMA,
    MIN_REQUEST_INTERVAL_SECONDS,
    VALIDATION_SCHEMA,
    IntakeError,
    SecAdapter,
    SecResponse,
    aggregate_routine_prospectus,
    audit_static_boundaries,
    build_dashboard_view,
    discover_portfolio_context,
    is_routine_prospectus_watch,
    map_event_type,
    materiality_rule_reason,
    normalize_submissions,
    overall_result,
    parse_ticker_association,
    render_dashboard_html,
    render_dashboard_markdown,
    route_materiality,
    run_pipeline,
    sort_dashboard_events,
    validate_sec_url,
    validated_watchlist_groups,
)
from validation_common import file_hash, load_json, validate_instance


FIXTURE_ROOT = ROOT / "manage-us-stock-strategy/tests/fixtures/sec"
DECISION_AS_OF = datetime(2026, 8, 30, 1, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class SecOfficialEventIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_json(DEFAULT_RULES_PATH)
        cls.association = load_json(FIXTURE_ROOT / "company_tickers_exchange.synthetic.json")
        cls.mrvl_submission = load_json(FIXTURE_ROOT / "MRVL.submissions.synthetic.json")

    def response(self, payload: dict, *, ticker: str = "MRVL") -> SecResponse:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        cik = str(payload.get("cik", "1835632")).zfill(10)
        return SecResponse(
            url=f"https://data.sec.gov/submissions/CIK{cik}.json",
            endpoint=f"submissions/{ticker}",
            status=200,
            content_type="application/json",
            body=body,
            headers={"Content-Type": "application/json"},
            retrieved_at="2026-08-30T01:00:00+00:00",
        )

    def build_submission(self, ticker: str, cik: str, name: str) -> dict:
        value = copy.deepcopy(self.mrvl_submission)
        value["cik"] = str(int(cik))
        value["name"] = name
        value["tickers"] = [ticker]
        recent = value["filings"]["recent"]
        recent["accessionNumber"] = [item.replace("0001835632", cik) for item in recent["accessionNumber"]]
        return value

    def make_adapter(self, *, fail_ticker: str | None = None, max_retries: int = 0) -> SecAdapter:
        association_bytes = (FIXTURE_ROOT / "company_tickers_exchange.synthetic.json").read_bytes()
        by_cik = {
            str(row[0]).zfill(10): (str(row[2]), str(row[1]))
            for row in self.association["data"]
        }

        def transport(url: str, headers: dict[str, str], timeout: float):
            self.assertEqual("GuardedPortfolioManager/0.1 test-contact@example.invalid", headers["User-Agent"])
            if url.endswith("company_tickers_exchange.json"):
                return 200, {"Content-Type": "application/json", "ETag": "synthetic"}, association_bytes
            cik = url.split("CIK", 1)[1].split(".json", 1)[0]
            ticker, name = by_cik[cik]
            if ticker == fail_ticker:
                return 503, {"Content-Type": "application/json"}, b"{}"
            payload = self.build_submission(ticker, cik, name)
            return 200, {"Content-Type": "application/json", "Last-Modified": "synthetic"}, json.dumps(payload).encode("utf-8")

        clock = FakeClock()
        return SecAdapter(
            user_agent="GuardedPortfolioManager/0.1 test-contact@example.invalid",
            transport=transport,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
            max_retries=max_retries,
        )

    def run_mock_pipeline(self, base: Path, *, run_id: str = "sec-test", fail_ticker: str | None = None) -> tuple[dict, Path, Path, Path]:
        portfolio = base / "portfolio_state.json"
        policy = base / "alert_policy.json"
        portfolio.write_text(json.dumps({"last_updated_at": "2026-08-29T00:00:00+00:00"}), encoding="utf-8")
        policy.write_text(json.dumps({"schema_version": "test"}), encoding="utf-8")
        manifest = run_pipeline(
            output_root=base / "outputs",
            run_id=run_id,
            decision_as_of=DECISION_AS_OF,
            adapter=self.make_adapter(fail_ticker=fail_ticker),
            portfolio_artifact_root=base / "portfolio-artifacts",
            portfolio_path=portfolio,
            policy_path=policy,
        )
        return manifest, Path(manifest["artifact_paths"]["run_manifest"]).parent, portfolio, policy

    def dashboard_event(
        self,
        *,
        ticker: str = "MRVL",
        form: str = "10-Q",
        filing_date: str = "2026-08-29",
        accepted_at: str | None = "2026-08-29T20:00:00+00:00",
        accession: str = "0000000000-26-000001",
        event_type: str = "PERIODIC_FINANCIAL",
        materiality: str = "HIGH",
        relevance: str = "HOLDING",
        impact: str = "ASSET_REVIEW_REQUIRED",
        items: list[str] | None = None,
        underlying: bool = False,
    ) -> dict:
        return {
            "ticker": ticker,
            "form": form,
            "filing_date": filing_date,
            "accepted_at": accepted_at,
            "accession_number": accession,
            "event_type": event_type,
            "materiality": materiality,
            "portfolio_relevance": relevance,
            "decision_impact": impact,
            "items_if_available": items or [],
            "underlying_company_relevance": underlying,
            "verification_status": "OFFICIAL_SOURCE_VERIFIED",
            "source_authority": "OFFICIAL_SEC",
        }

    def dashboard_outputs(
        self, events: list[dict], scheduled_summary: dict | None = None
    ) -> tuple[str, str]:
        model = {
            "run_time": "2026-08-30T01:00:00+00:00",
            "source_status": "PASS",
            "context": {"status": "LAST_KNOWN", "as_of": "2026-08-29T00:00:00+00:00"},
            "lookback_days": (scheduled_summary or {}).get("lookback_days", 14),
            "events": events,
            "ownership_coverage": "PARTIAL",
            "company_status": {ticker: "PASS" for ticker in ("MRVL", "NBIS", "MU", "BE", "DELL", "PWR", "LITE")},
            "scheduled_summary": scheduled_summary,
        }
        return render_dashboard_markdown(**model), render_dashboard_html(model)

    def routine_flood(self, count: int, *, form: str = "424B2", relevance: str = "WATCHLIST") -> list[dict]:
        return [
            self.dashboard_event(
                ticker="MU",
                form=form,
                filing_date=f"2026-08-{17 + (index % 13):02d}",
                accepted_at=f"2026-08-{17 + (index % 13):02d}T{10 + (index % 10):02d}:00:00+00:00",
                accession=f"0000019617-26-{index:06d}",
                event_type="OFFERING_PROSPECTUS",
                materiality="MEDIUM",
                relevance=relevance,
                impact="WATCH",
            )
            for index in range(count)
        ]

    def test_user_agent_required_before_transport(self) -> None:
        called = False

        def transport(url, headers, timeout):
            nonlocal called
            called = True
            return 200, {"Content-Type": "application/json"}, b"{}"

        adapter = SecAdapter(user_agent="", transport=transport)
        with self.assertRaisesRegex(IntakeError, "SEC_USER_AGENT_REQUIRED"):
            adapter.request_json("https://www.sec.gov/files/company_tickers_exchange.json", "ticker_association")
        self.assertFalse(called)
        self.assertEqual(0, adapter.accounting.http_request_count)

    def test_host_allowlist_and_https(self) -> None:
        validate_sec_url("https://www.sec.gov/files/company_tickers_exchange.json")
        validate_sec_url("https://data.sec.gov/submissions/CIK0000000001.json")
        for url in ("http://www.sec.gov/files/x.json", "https://sec.gov/x", "https://example.com/x"):
            with self.subTest(url=url), self.assertRaisesRegex(IntakeError, "NETWORK_SCOPE_VIOLATION"):
                validate_sec_url(url)

    def test_rate_limiter_never_exceeds_one_request_per_second(self) -> None:
        clock = FakeClock()
        starts: list[float] = []

        def transport(url, headers, timeout):
            starts.append(clock.monotonic())
            return 200, {"Content-Type": "application/json"}, b"{}"

        adapter = SecAdapter(user_agent="test invalid", transport=transport, sleep=clock.sleep, monotonic=clock.monotonic)
        adapter.request_json("https://www.sec.gov/files/one.json", "one")
        adapter.request_json("https://www.sec.gov/files/two.json", "two")
        self.assertGreaterEqual(starts[1] - starts[0], MIN_REQUEST_INTERVAL_SECONDS)

    def test_429_retry_is_bounded_and_counted(self) -> None:
        clock = FakeClock()
        statuses = [429, 429, 200]

        def transport(url, headers, timeout):
            status = statuses.pop(0)
            return status, {"Content-Type": "application/json"}, b"{}"

        adapter = SecAdapter(user_agent="test invalid", transport=transport, sleep=clock.sleep, monotonic=clock.monotonic, max_retries=2)
        adapter.request_json("https://www.sec.gov/files/x.json", "x")
        self.assertEqual(3, adapter.accounting.http_request_count)
        self.assertEqual(2, adapter.accounting.retry_count)
        self.assertEqual(2, adapter.accounting.failed_request_count)

    def test_5xx_retry_is_bounded(self) -> None:
        clock = FakeClock()

        def transport(url, headers, timeout):
            return 503, {"Content-Type": "application/json"}, b"{}"

        adapter = SecAdapter(user_agent="test invalid", transport=transport, sleep=clock.sleep, monotonic=clock.monotonic, max_retries=2)
        with self.assertRaisesRegex(IntakeError, "SEC_PARTIAL_SOURCE"):
            adapter.request_json("https://data.sec.gov/submissions/CIK0000000001.json", "submissions/TST")
        self.assertEqual(3, adapter.accounting.http_request_count)
        self.assertEqual(2, adapter.accounting.retry_count)

    def test_invalid_json_fails_closed(self) -> None:
        def transport(url, headers, timeout):
            return 200, {"Content-Type": "application/json"}, b"not-json"

        adapter = SecAdapter(user_agent="test invalid", transport=transport)
        with self.assertRaisesRegex(IntakeError, "SEC_SOURCE_INVALID"):
            adapter.request_json("https://www.sec.gov/files/x.json", "x")

    def test_ticker_to_cik_mapping_is_exact(self) -> None:
        mapping = parse_ticker_association(self.association, ["MRVL", "NBIS"])
        self.assertEqual("0001835632", mapping["MRVL"]["cik"])
        self.assertEqual("0001513845", mapping["NBIS"]["cik"])
        with self.assertRaisesRegex(IntakeError, "SEC_IDENTITY_CONFLICT"):
            parse_ticker_association(self.association, ["MRV-L"])

    def test_identity_conflict_has_no_punctuation_fallback(self) -> None:
        identity = parse_ticker_association(self.association, ["MRVL"])["MRVL"]
        payload = copy.deepcopy(self.mrvl_submission)
        payload["name"] = "Marvell Technology Inc"
        with self.assertRaisesRegex(IntakeError, "SEC_IDENTITY_CONFLICT"):
            normalize_submissions(
                payload=payload, identity=identity, response=self.response(payload),
                decision_as_of=DECISION_AS_OF, lookback_days=14, rules=self.rules,
            )

    def test_accession_dedup_lookback_and_future_exclusion(self) -> None:
        identity = parse_ticker_association(self.association, ["MRVL"])["MRVL"]
        events, partial = normalize_submissions(
            payload=self.mrvl_submission, identity=identity, response=self.response(self.mrvl_submission),
            decision_as_of=DECISION_AS_OF, lookback_days=14, rules=self.rules,
        )
        self.assertFalse(partial)
        accessions = [event["accession_number"] for event in events]
        self.assertEqual(len(accessions), len(set(accessions)))
        self.assertEqual(4, len(events))
        self.assertTrue(all("2026-08-17" <= event["filing_date"] <= "2026-08-30" for event in events))

    def test_all_configured_forms_normalize_without_invention(self) -> None:
        identity = parse_ticker_association(self.association, ["MRVL"])["MRVL"]
        payload = copy.deepcopy(self.mrvl_submission)
        forms = self.rules["forms_of_interest"]
        payload["filings"]["recent"] = {
            "accessionNumber": [f"0001835632-26-{index:06d}" for index in range(len(forms))],
            "filingDate": ["2026-08-29"] * len(forms),
            "reportDate": [""] * len(forms),
            "acceptanceDateTime": ["2026-08-29T20:00:00.000Z"] * len(forms),
            "form": forms,
            "primaryDocument": ["document.htm"] * len(forms),
            "items": [""] * len(forms),
        }
        events, _ = normalize_submissions(
            payload=payload, identity=identity, response=self.response(payload),
            decision_as_of=DECISION_AS_OF, lookback_days=14, rules=self.rules,
        )
        self.assertEqual(set(forms), {event["form"] for event in events})
        self.assertIsNone(map_event_type("FORM_THAT_IS_NOT_PRESENT", self.rules))

    def test_materiality_separates_event_type_from_trade_signal(self) -> None:
        high = route_materiality(ticker="NBIS", form="424B5", event_type="OFFERING_PROSPECTUS", items=[], rules=self.rules)
        low = route_materiality(ticker="MRVL", form="8-K", event_type="CURRENT_REPORT", items=["9.01"], rules=self.rules)
        watch_periodic = route_materiality(ticker="MU", form="10-Q", event_type="PERIODIC_FINANCIAL", items=[], rules=self.rules)
        self.assertEqual(("HIGH", "HOLDING", "ASSET_REVIEW_REQUIRED"), high)
        self.assertEqual(("LOW", "HOLDING", "NO_CHANGE"), low)
        self.assertEqual(("HIGH", "WATCHLIST", "WATCH"), watch_periodic)
        self.assertNotIn("SELL", {high[2], low[2], watch_periodic[2]})

    def test_watch_ticker_routing_never_escalates_to_asset_review(self) -> None:
        for ticker in self.rules["watch"]:
            with self.subTest(ticker=ticker):
                material_8k = route_materiality(ticker=ticker, form="8-K", event_type="CURRENT_REPORT", items=["2.02", "9.01"], rules=self.rules)
                admin_8k = route_materiality(ticker=ticker, form="8-K", event_type="CURRENT_REPORT", items=["9.01"], rules=self.rules)
                shelf = route_materiality(ticker=ticker, form="S-3", event_type="SHELF_REGISTRATION", items=[], rules=self.rules)
                insider = route_materiality(ticker=ticker, form="4", event_type="INSIDER_OWNERSHIP", items=[], rules=self.rules)
                self.assertEqual(("HIGH", "WATCHLIST", "WATCH"), material_8k)
                self.assertEqual(("MEDIUM", "WATCHLIST", "WATCH"), admin_8k)
                self.assertEqual(("HIGH", "WATCHLIST", "WATCH"), shelf)
                self.assertEqual(("MEDIUM", "WATCHLIST", "WATCH"), insider)

    def test_holding_routing_is_unchanged_for_material_8k(self) -> None:
        for ticker in self.rules["holdings"]:
            with self.subTest(ticker=ticker):
                self.assertEqual(
                    ("HIGH", "HOLDING", "ASSET_REVIEW_REQUIRED"),
                    route_materiality(ticker=ticker, form="8-K", event_type="CURRENT_REPORT", items=["1.01"], rules=self.rules),
                )

    def test_unclassified_ticker_fails_closed(self) -> None:
        for ticker in ("PGR", "JPM", "CME", "V", "SOXL"):
            with self.subTest(ticker=ticker), self.assertRaisesRegex(IntakeError, "SEC_SOURCE_INVALID"):
                route_materiality(ticker=ticker, form="10-Q", event_type="PERIODIC_FINANCIAL", items=[], rules=self.rules)

    def test_rules_watchlist_matches_current_target_and_partition(self) -> None:
        watchlist, holdings, watch = validated_watchlist_groups(self.rules)
        self.assertEqual(["MRVL", "NBIS", "MU", "BE", "DELL", "PWR", "LITE"], watchlist)
        self.assertEqual(["MRVL", "NBIS"], holdings)
        self.assertEqual(["MU", "BE", "DELL", "PWR", "LITE"], watch)
        self.assertTrue({"PGR", "JPM", "CME", "V"}.isdisjoint(watchlist))
        self.assertNotIn("challengers", self.rules)

    def test_watchlist_validation_fails_closed_on_empty_or_inconsistent_rules(self) -> None:
        def variant(**changes: object) -> dict:
            value = copy.deepcopy(self.rules)
            value.update(changes)
            return value

        broken = {
            "empty_watchlist": variant(corporate_watchlist=[]),
            "missing_watchlist": {key: item for key, item in self.rules.items() if key != "corporate_watchlist"},
            "missing_watch_group": {key: item for key, item in self.rules.items() if key != "watch"},
            "unclassified_symbol": variant(corporate_watchlist=[*self.rules["corporate_watchlist"], "XYZ"]),
            "symbol_in_both_groups": variant(watch=[*self.rules["watch"], "MRVL"]),
            "duplicate_symbol": variant(corporate_watchlist=[*self.rules["corporate_watchlist"], "MU"]),
            "non_string_symbol": variant(corporate_watchlist=[*self.rules["corporate_watchlist"], 7]),
            "not_a_dict": [],
        }
        for name, rules in broken.items():
            with self.subTest(case=name), self.assertRaisesRegex(IntakeError, "SEC_SOURCE_INVALID"):
                validated_watchlist_groups(rules)

    def test_pipeline_with_empty_watchlist_fails_before_network_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            rules_path = base / "rules.json"
            rules_path.write_text(json.dumps({**self.rules, "corporate_watchlist": [], "holdings": [], "watch": []}), encoding="utf-8")
            called = False

            def transport(url, headers, timeout):
                nonlocal called
                called = True
                return 200, {"Content-Type": "application/json"}, b"{}"

            adapter = SecAdapter(user_agent="GuardedPortfolioManager/0.1 test-contact@example.invalid", transport=transport)
            with self.assertRaisesRegex(IntakeError, "SEC_SOURCE_INVALID"):
                run_pipeline(
                    output_root=base / "outputs", run_id="empty-watchlist", decision_as_of=DECISION_AS_OF,
                    rules_path=rules_path, adapter=adapter,
                    portfolio_artifact_root=base / "portfolio-artifacts",
                    portfolio_path=base / "portfolio_state.json", policy_path=base / "alert_policy.json",
                )
            self.assertFalse(called)
            self.assertFalse((base / "outputs").exists())

    def test_dashboard_lists_come_from_rules_not_hardcoded_symbols(self) -> None:
        markdown, html_output = self.dashboard_outputs([])
        for ticker in ("MU", "BE", "DELL", "PWR", "LITE"):
            self.assertIn(f"{ticker}: ", markdown)
            self.assertIn(f"<strong>{ticker}</strong>", html_output)
        for output in (markdown, html_output):
            for retired in ("PGR", "JPM", "CME"):
                self.assertNotIn(retired, output)
        self.assertIn("MRVL -> MVLL:", markdown)
        self.assertIn("DERIVED_MAPPING_NOT_ENTITY_EQUIVALENCE", markdown)

    def test_pipeline_emits_watchlist_relevance_for_watch_tickers_and_schema_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, run_dir, _, _ = self.run_mock_pipeline(Path(directory))
            self.assertEqual(self.rules["corporate_watchlist"], manifest["watchlist"])
            events = load_json(run_dir / "normalized-events.json")["events"]
            self.assertFalse(validate_instance(load_json(run_dir / "normalized-events.json"), EVENTS_SCHEMA))
            relevance_by_ticker = {event["ticker"]: event["portfolio_relevance"] for event in events}
            self.assertEqual({"MRVL", "NBIS", "MU", "BE", "DELL", "PWR", "LITE"}, set(relevance_by_ticker))
            for ticker, relevance in relevance_by_ticker.items():
                self.assertEqual("HOLDING" if ticker in self.rules["holdings"] else "WATCHLIST", relevance)
            self.assertFalse(any(event["decision_impact"] == "ASSET_REVIEW_REQUIRED" for event in events if event["ticker"] in self.rules["watch"]))
            self.assertTrue({"PGR", "JPM", "CME", "V"}.isdisjoint(relevance_by_ticker))

    def test_mvll_relation_is_derived_and_not_cik_equivalence(self) -> None:
        identity = parse_ticker_association(self.association, ["MRVL"])["MRVL"]
        events, _ = normalize_submissions(
            payload=self.mrvl_submission, identity=identity, response=self.response(self.mrvl_submission),
            decision_as_of=DECISION_AS_OF, lookback_days=14, rules=self.rules,
        )
        self.assertTrue(all(event["underlying_company_relevance"] for event in events))
        self.assertTrue(all(event["leveraged_vehicle"] == "MVLL" for event in events))
        self.assertTrue(all(event["derived_relation_status"] == "DERIVED_MAPPING_NOT_ENTITY_EQUIVALENCE" for event in events))

    def test_soxl_is_deferred_not_mapped(self) -> None:
        self.assertNotIn("SOXL", self.rules["corporate_watchlist"])
        self.assertEqual("DEFERRED_TO_SECTOR_OR_FUND_SOURCE", self.rules["deferred_symbols"]["SOXL"])

    def test_partial_company_source_does_not_block_other_companies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, run_dir, _, _ = self.run_mock_pipeline(Path(directory), fail_ticker="NBIS")
            self.assertEqual("PARTIAL", manifest["pipeline_status"])
            self.assertEqual("SEC_PARTIAL_SOURCE", manifest["company_source_status"]["NBIS"])
            self.assertTrue(all(manifest["company_source_status"][ticker] == "PASS" for ticker in ("MRVL", "MU", "BE", "DELL", "PWR", "LITE")))
            self.assertTrue((run_dir / "normalized-events.json").is_file())

    def test_request_accounting_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, _, _, _ = self.run_mock_pipeline(Path(directory))
            accounting = manifest["request_accounting"]
            self.assertEqual(8, accounting["http_request_count"])
            self.assertEqual(8, accounting["successful_request_count"])
            self.assertEqual(0, accounting["failed_request_count"])
            self.assertEqual(0, accounting["retry_count"])
            self.assertEqual({"data.sec.gov": 7, "www.sec.gov": 1}, accounting["host_counts"])

    def test_raw_evidence_hash_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, run_dir, _, _ = self.run_mock_pipeline(Path(directory))
            raw = run_dir / "raw/company_tickers_exchange.json"
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), manifest["raw_source_hashes"]["raw/company_tickers_exchange.json"])
            metadata = load_json(run_dir / "raw/source-metadata.json")
            self.assertEqual(8, len(metadata["sources"]))
            self.assertNotIn("test-contact@example.invalid", json.dumps(metadata))

    def test_artifact_provenance_and_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, run_dir, _, _ = self.run_mock_pipeline(Path(directory))
            self.assertEqual(file_hash(Path(__file__).parents[1] / "scripts/sec_official_event_intake.py"), manifest["implementation_hashes"]["sec_official_event_intake.py"])
            self.assertEqual(file_hash(DEFAULT_RULES_PATH), next(iter(manifest["rules_hashes"].values())))
            self.assertFalse(validate_instance(load_json(run_dir / "normalized-events.json"), EVENTS_SCHEMA))
            self.assertFalse(validate_instance(load_json(run_dir / "validation-report.json"), VALIDATION_SCHEMA))
            self.assertFalse(validate_instance(manifest, MANIFEST_SCHEMA))
            manifest_text = (run_dir / "run-manifest.json").read_text(encoding="utf-8")
            self.assertNotIn("test-contact@example.invalid", manifest_text)

    def test_create_only_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.run_mock_pipeline(base, run_id="same-run")
            with self.assertRaisesRegex(IntakeError, "RUN_COLLISION"):
                self.run_mock_pipeline(base, run_id="same-run")

    def test_latest_genuine_grade_b_portfolio_context_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            older = root / "manual-old"
            newer = root / "manual-new"
            older.mkdir()
            newer.mkdir()
            common = {
                "evidence_grade": "GRADE_B", "manual_data_verification_status": "VERIFIED_REAL_DATA",
                "run_provenance_status": "VERIFIED_MANUAL", "preflight_status": "PASS", "order_authority": False,
                "provenance": {"evidence_grade": "GRADE_B"},
            }
            (older / "manual-portfolio-analysis.json").write_text(json.dumps({**common, "decision_as_of": "2026-08-28T00:00:00+00:00"}), encoding="utf-8")
            newest = newer / "manual-portfolio-analysis.json"
            newest.write_text(json.dumps({**common, "decision_as_of": "2026-08-29T00:00:00+00:00"}), encoding="utf-8")
            before = newest.read_bytes()
            context = discover_portfolio_context(root, decision_as_of=DECISION_AS_OF)
            self.assertEqual("LAST_KNOWN", context["status"])
            self.assertEqual("2026-08-29T00:00:00+00:00", context["as_of"])
            self.assertEqual(before, newest.read_bytes())

    def test_dashboard_01_routine_prospectus_flood_is_excluded_from_high_top_events(self) -> None:
        high = self.dashboard_event(accession="high-1")
        events = [high, *self.routine_flood(30)]
        view = build_dashboard_view(events)
        self.assertEqual(["high-1"], [event["accession_number"] for event in view["high_events"]])
        self.assertTrue(all(not is_routine_prospectus_watch(event) for event in view["high_events"]))
        self.assertEqual(0, view["individual_routine_top_events"])

    def test_dashboard_01b_legacy_challenger_artifacts_still_aggregate_as_routine(self) -> None:
        events = [self.dashboard_event(accession="high-1"), *self.routine_flood(12, relevance="CHALLENGER")]
        view = build_dashboard_view(events)
        self.assertEqual(["high-1"], [event["accession_number"] for event in view["high_events"]])
        self.assertEqual(12, view["routine_event_count"])

    def test_dashboard_02_same_form_flood_becomes_one_aggregate_row(self) -> None:
        aggregates = aggregate_routine_prospectus(self.routine_flood(25))
        self.assertEqual(1, len(aggregates))
        self.assertEqual(25, aggregates[0]["count"])
        self.assertEqual("424B2", aggregates[0]["form"])

    def test_dashboard_03_prospectus_is_not_confirmed_convertible_or_dilution(self) -> None:
        events = [*self.routine_flood(20), *self.routine_flood(3, form="424B3")]
        view = build_dashboard_view(events)
        markdown, html_output = self.dashboard_outputs(events)
        self.assertEqual("NOT_VERIFIED", view["confirmed_convertible_dilution"])
        for output in (markdown, html_output):
            self.assertIn("NOT_VERIFIED", output)
            self.assertIn("전환 조건이나 경제적 희석을 확정하지 않습니다", output)

    def test_dashboard_04_latest_equal_priority_mrvl_10q_is_first(self) -> None:
        old = self.dashboard_event(
            form="8-K", event_type="CURRENT_REPORT", filing_date="2026-08-20",
            accepted_at="2026-08-20T18:00:00+00:00", accession="old-8k", items=["2.02", "9.01"],
        )
        latest = self.dashboard_event(
            form="10-Q", filing_date="2026-08-29", accepted_at="2026-08-29T20:00:00+00:00",
            accession="latest-10q",
        )
        ordered = build_dashboard_view([old, latest])["high_events"]
        self.assertEqual("latest-10q", ordered[0]["accession_number"])

    def test_dashboard_05_impact_priority_is_descending(self) -> None:
        watch = self.dashboard_event(accession="watch", impact="WATCH")
        review = self.dashboard_event(accession="review", impact="ASSET_REVIEW_REQUIRED")
        recompile = self.dashboard_event(accession="recompile", impact="PORTFOLIO_RECOMPILE_REQUIRED")
        self.assertEqual(
            ["recompile", "review", "watch"],
            [event["accession_number"] for event in sort_dashboard_events([watch, review, recompile])],
        )

    def test_dashboard_06_materiality_priority_is_descending(self) -> None:
        low = self.dashboard_event(accession="low", materiality="LOW", impact="WATCH")
        medium = self.dashboard_event(accession="medium", materiality="MEDIUM", impact="WATCH")
        high = self.dashboard_event(accession="high", materiality="HIGH", impact="WATCH")
        self.assertEqual(
            ["high", "medium", "low"],
            [event["accession_number"] for event in sort_dashboard_events([low, medium, high])],
        )

    def test_dashboard_07_accepted_at_then_filing_date_are_descending(self) -> None:
        latest_acceptance = self.dashboard_event(
            accession="accepted-latest", filing_date="2026-08-28", accepted_at="2026-08-30T01:00:00+00:00"
        )
        latest_filing = self.dashboard_event(
            accession="filing-latest", filing_date="2026-08-29", accepted_at="2026-08-29T23:00:00+00:00"
        )
        self.assertEqual(
            "accepted-latest", sort_dashboard_events([latest_filing, latest_acceptance])[0]["accession_number"]
        )
        no_accept_old = self.dashboard_event(accession="no-accept-old", filing_date="2026-08-28", accepted_at=None)
        no_accept_new = self.dashboard_event(accession="no-accept-new", filing_date="2026-08-29", accepted_at=None)
        self.assertEqual(
            "no-accept-new", sort_dashboard_events([no_accept_old, no_accept_new])[0]["accession_number"]
        )
        accepted_old = self.dashboard_event(
            accession="accepted-old", filing_date="2026-08-28", accepted_at="2026-08-28T23:00:00+00:00"
        )
        missing_new = self.dashboard_event(
            accession="missing-new", filing_date="2026-08-29", accepted_at=None
        )
        self.assertEqual(
            "missing-new", sort_dashboard_events([accepted_old, missing_new])[0]["accession_number"]
        )

    def test_dashboard_08_high_count_matches_actual_high_events(self) -> None:
        events = [
            self.dashboard_event(accession=f"high-{index}") for index in range(7)
        ] + self.routine_flood(20)
        view = build_dashboard_view(events)
        self.assertEqual(7, view["high_event_count"])
        self.assertEqual(7, len(view["high_events"]))

    def test_dashboard_09_all_high_events_are_visible_with_accessions(self) -> None:
        events = [self.dashboard_event(accession=f"visible-{index}") for index in range(7)]
        markdown, html_output = self.dashboard_outputs(events)
        for event in events:
            self.assertIn(event["accession_number"], markdown)
            self.assertIn(event["accession_number"], html_output)
        self.assertIn("현재 HIGH 검토 공시 수: **7건**", markdown)
        self.assertIn("현재 HIGH 검토 공시 수</small><strong>7건", html_output)

    def test_dashboard_10_every_high_event_has_deterministic_rule_reason(self) -> None:
        events = [
            self.dashboard_event(accession="periodic"),
            self.dashboard_event(
                accession="current", form="8-K", event_type="CURRENT_REPORT", items=["2.02", "9.01"]
            ),
            self.dashboard_event(accession="foreign", ticker="NBIS", form="6-K", event_type="FOREIGN_CURRENT_REPORT"),
        ]
        for event in events:
            reason = materiality_rule_reason(event)
            self.assertTrue(reason.strip())
            self.assertIn(event["event_type"], reason)
            self.assertIn(event["decision_impact"], reason)

    def test_dashboard_11_nbis_6k_reason_preserves_content_uncertainty(self) -> None:
        event = self.dashboard_event(
            ticker="NBIS", form="6-K", event_type="FOREIGN_CURRENT_REPORT", accession="nbis-6k"
        )
        reason = materiality_rule_reason(event)
        self.assertIn("Filing content materiality not interpreted in v0.1", reason)
        self.assertNotIn("dilution confirmed", reason.casefold())
        self.assertNotIn("earnings deterioration", reason.casefold())

    def test_dashboard_12_markdown_html_semantic_parity(self) -> None:
        events = [
            self.dashboard_event(accession="parity-high"),
            *self.routine_flood(8),
            *self.routine_flood(2, form="424B3"),
        ]
        markdown, html_output = self.dashboard_outputs(events)
        shared_tokens = (
            "SEC 공시 자동 분석", "확인 필요한 종목이 있습니다", "ASSET_REVIEW_REQUIRED",
            "parity-high", "왜 중요한가", "확인된 사실", "아직 모르는 것",
            "424B2", "424B3", "NOT_VERIFIED", "OFFICIAL_SEC",
            "order_authority=false", "execution_quantity=null",
        )
        for token in shared_tokens:
            self.assertIn(token, markdown)
            self.assertIn(token, html_output)

    def test_dashboard_13_routine_watch_does_not_change_result_escalation(self) -> None:
        high = self.dashboard_event(accession="result-high")
        self.assertEqual("ASSET_REVIEW_REQUIRED", overall_result([high]))
        events = [high, *self.routine_flood(30)]
        self.assertEqual("ASSET_REVIEW_REQUIRED", overall_result(events))
        self.assertEqual("ASSET_REVIEW_REQUIRED", build_dashboard_view(events)["result"])

    def test_dashboard_14_two_forms_create_two_aggregate_rows_not_events(self) -> None:
        events = [*self.routine_flood(20), *self.routine_flood(4, form="424B3")]
        view = build_dashboard_view(events)
        self.assertEqual(2, len(view["routine_aggregates"]))
        self.assertEqual(24, view["routine_event_count"])
        self.assertEqual(0, view["individual_routine_top_events"])

    def test_dashboard_15_korean_first_labels_and_internal_display_separation(self) -> None:
        markdown, html_output = self.dashboard_outputs([self.dashboard_event()])
        for output in (markdown, html_output):
            self.assertIn("SEC 공시 자동 분석", output)
            self.assertIn("오늘의 결론", output)
            self.assertIn("지금 확인할 중요 공시", output)
            self.assertIn("확인 필요한 종목이 있습니다", output)
            self.assertIn("ASSET_REVIEW_REQUIRED", output)

    def test_dashboard_16_form_codes_have_korean_descriptions(self) -> None:
        events = [
            self.dashboard_event(form="10-Q", event_type="PERIODIC_FINANCIAL", accession="form-10q"),
            self.dashboard_event(form="8-K", event_type="CURRENT_REPORT", accession="form-8k"),
            self.dashboard_event(ticker="NBIS", form="6-K", event_type="FOREIGN_CURRENT_REPORT", accession="form-6k"),
        ]
        markdown, html_output = self.dashboard_outputs(events)
        for output in (markdown, html_output):
            self.assertIn("분기보고서 (10-Q)", output)
            self.assertIn("중요 수시공시 (8-K)", output)
            self.assertIn("해외기업 수시공시 (6-K)", output)

    def test_dashboard_17_scheduled_counts_are_distinct_and_visible(self) -> None:
        summary = {
            "filings_in_lookback_window": 478,
            "new_since_previous_count": 21,
            "new_high_since_previous_count": 0,
            "high_filings_in_lookback_window": 3,
            "freshness_status": "CURRENT_RUN",
            "lookback_days": 7,
        }
        events = [self.dashboard_event(accession=f"scheduled-{index}") for index in range(3)]
        markdown, html_output = self.dashboard_outputs(events, summary)
        for output in (markdown, html_output):
            self.assertIn("최근 7일 공시 수", output)
            self.assertIn("478건", output)
            self.assertIn("21건", output)
            self.assertIn("0건", output)
            self.assertIn("3건", output)
            self.assertIn("최신 자동 실행 결과", output)
        self.assertNotEqual(summary["filings_in_lookback_window"], summary["new_since_previous_count"])

    def test_dashboard_18_verified_unknown_and_no_trade_inference(self) -> None:
        markdown, html_output = self.dashboard_outputs([self.dashboard_event()])
        for output in (markdown, html_output):
            self.assertIn("확인된 사실", output)
            self.assertIn("공식 SEC filing 존재", output)
            self.assertIn("아직 모르는 것", output)
            self.assertIn("filing 본문 영향", output)
            self.assertIn("매수/매도 신호", output)
            self.assertNotIn("BUY", output)
            self.assertNotIn("SELL", output)

    def test_dashboard_18b_last_known_has_korean_display_without_internal_mutation(self) -> None:
        summary = {"freshness_status": "LAST_KNOWN"}
        markdown, html_output = self.dashboard_outputs([], summary)
        for output in (markdown, html_output):
            self.assertIn("이전 정상 결과", output)
            self.assertIn("LAST_KNOWN", output)

    def test_dashboard_19_jpm_routine_aggregation_is_beginner_compact(self) -> None:
        events = [*self.routine_flood(460), *self.routine_flood(15, form="424B3")]
        view = build_dashboard_view(events)
        markdown, html_output = self.dashboard_outputs(events)
        self.assertEqual(475, view["routine_event_count"])
        self.assertEqual(2, len(view["routine_aggregates"]))
        for output in (markdown, html_output):
            self.assertIn("일상적인 증권 발행 관련 공시", output)
            self.assertIn("475건", output)
            self.assertIn("424B2", output)
            self.assertIn("460건", output)
            self.assertIn("424B3", output)
            self.assertIn("15건", output)

    def test_dashboard_20_windows_font_meta_and_korean_utf8_bom(self) -> None:
        events = [self.dashboard_event()]
        _, html_output = self.dashboard_outputs(events)
        self.assertIn('<meta charset="utf-8">', html_output)
        self.assertIn('font-family:"Malgun Gothic","맑은 고딕","Segoe UI",Arial,sans-serif', html_output)
        self.assertNotIn("Inter", html_output)
        self.assertNotIn("Noto Sans KR", html_output)
        with tempfile.TemporaryDirectory() as directory:
            _, run_dir, _, _ = self.run_mock_pipeline(Path(directory))
            html_bytes = (run_dir / "dashboard.html").read_bytes()
            markdown_bytes = (run_dir / "dashboard.md").read_bytes()
            self.assertTrue(html_bytes.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(markdown_bytes.startswith(b"\xef\xbb\xbf"))
            self.assertIn("SEC 공시 자동 분석", html_bytes.decode("utf-8-sig"))

    def test_no_broker_portfolio_policy_scheduler_or_order_path(self) -> None:
        boundaries = audit_static_boundaries()
        self.assertFalse(boundaries["broker_path_present"])
        self.assertFalse(boundaries["order_path_present"])
        self.assertFalse(boundaries["scheduler_path_present"])
        with tempfile.TemporaryDirectory() as directory:
            manifest, _, portfolio, policy = self.run_mock_pipeline(Path(directory))
            before = {"portfolio": file_hash(portfolio), "policy": file_hash(policy)}
            self.assertFalse(manifest["broker_call"])
            self.assertFalse(manifest["portfolio_mutation"])
            self.assertFalse(manifest["policy_mutation"])
            self.assertFalse(manifest["task_scheduler_activated"])
            self.assertEqual("NONE", manifest["orders"])
            self.assertFalse(manifest["order_authority"])
            self.assertIsNone(manifest["execution_quantity"])
            self.assertFalse(manifest["automatic_order"])
            self.assertEqual(before, {"portfolio": file_hash(portfolio), "policy": file_hash(policy)})


if __name__ == "__main__":
    unittest.main()
