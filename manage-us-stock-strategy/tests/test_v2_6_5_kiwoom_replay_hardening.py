from __future__ import annotations

import json
import multiprocessing
import os
import socket
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
sys.path.insert(0, str(SCRIPTS))

from build_kiwoom_market_snapshot import normalize_series
from build_yfinance_replay_evidence import _actions
from compare_kiwoom_yfinance import compare_snapshots
from kiwoom_replay_validation import (
    calculate_kiwoom_technical, compare_technical_decisions, replay_status_axes,
)
from kiwoom_runtime_bridge import BridgeError, _daily_chart_pages
from point_in_time_context import (
    append_checkpoint, baseline_reference, build_checkpoint, validate_checkpoint_hash,
    validate_hash_chain,
)
from run_kiwoom_candidate_primary_replay import apply_current_context, current_context_status
from shadow_acceptance import (
    SingleSessionLockCollision, acquire_owned_lock, release_owned_lock,
)
from validation_common import load_json, validate_instance
from validate_kiwoom_market_snapshot import validate_snapshot_semantics


NOW = "2026-08-14T00:00:00+00:00"


def _lock_process(path: str, queue: multiprocessing.Queue) -> None:
    try:
        lock = acquire_owned_lock(Path(path), purpose="test", target_resource="test", now=NOW)
        queue.put((True, lock["owner_token"]))
    except SingleSessionLockCollision:
        queue.put((False, None))


def chart_row(day: int, close: float = 100.0) -> dict[str, str]:
    session = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
    return {
        "dt": session.strftime("%Y%m%d"), "open_pric": str(close - 1),
        "high_pric": str(close + 1), "low_pric": str(close - 2),
        "cur_prc": str(close), "acc_trde_qty": str(1000 + day),
        "pred_pre": "0", "flu_rt": "0", "acc_trde_prica": "0",
        "upd_stkpc_tp": "0", "upd_rt": "1",
    }


class Continuation:
    def __init__(self, cont_yn: str, next_key: str | None):
        self.cont_yn = cont_yn
        self.next_key = next_key


class Response:
    def __init__(self, rows, cont_yn="N", next_key=None):
        self.body = {"return_code": 0, "result_list": rows}
        self.continuation = Continuation(cont_yn, next_key)


class PageClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.kwargs = []

    def fetch_page(self, **kwargs):
        self.kwargs.append(kwargs)
        value = self.responses[self.calls]
        self.calls += 1
        return value


def session(client, minimum=5, pages=5, no_progress=1, pacer=None):
    return {
        "client": client, "pacer": pacer or (lambda: None), "maximum_attempts": 1,
        "retry_backoff_seconds": 0.0, "retryable_failure_types": set(),
        "immediate_open_failure_types": {"HTTP_429", "AUTHENTICATION_FAILURE"},
        "minimum_history_bars": minimum, "history_buffer_bars": 0,
        "maximum_history_pages": pages, "no_progress_page_limit": no_progress,
    }


class LockOwnershipTests(unittest.TestCase):
    def test_lock_01_owner_acquires_and_releases(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.lock"; lock = acquire_owned_lock(path, purpose="p", target_resource="r", now=NOW)
            self.assertTrue(path.exists()); self.assertTrue(release_owned_lock(lock)); self.assertFalse(path.exists())

    def test_lock_02_foreign_live_collision(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; path.write_text(json.dumps({"owner_token":"foreign","pid":1,"hostname":socket.gethostname(),"created_at":NOW}),encoding="utf-8")
            with self.assertRaises(SingleSessionLockCollision): acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW)

    def test_lock_03_foreign_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; original=b"foreign-live-lock"; path.write_bytes(original)
            with self.assertRaises(SingleSessionLockCollision): acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW)
            self.assertEqual(path.read_bytes(),original)

    def test_lock_04_collision_cannot_delete_foreign(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; path.write_text("foreign",encoding="utf-8")
            try: acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW)
            except SingleSessionLockCollision: pass
            self.assertTrue(path.exists())

    def test_lock_05_proven_dead_stale_quarantined(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; old="2026-08-13T00:00:00+00:00"
            path.write_text(json.dumps({"owner_token":"dead","pid":999999,"hostname":socket.gethostname(),"created_at":old}),encoding="utf-8")
            lock=acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW,stale_recovery_enabled=True,stale_ttl_seconds=60,process_alive=lambda _:False)
            self.assertTrue(any(Path(d).glob("x.lock.stale.*"))); self.assertTrue(release_owned_lock(lock))

    def test_lock_06_uncertain_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; value={"owner_token":"unknown","pid":42,"hostname":socket.gethostname(),"created_at":"2026-08-13T00:00:00+00:00"}; path.write_text(json.dumps(value),encoding="utf-8"); before=path.read_bytes()
            with self.assertRaises(SingleSessionLockCollision): acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW,stale_recovery_enabled=True,stale_ttl_seconds=60,process_alive=lambda _:None)
            self.assertEqual(path.read_bytes(),before)

    def test_lock_07_exception_owner_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; lock=acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW)
            try: raise RuntimeError("test")
            except RuntimeError: self.assertTrue(release_owned_lock(lock))
            self.assertFalse(path.exists())

    def test_lock_08_two_processes_not_both_acquire(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"x.lock"); queue=multiprocessing.Queue(); processes=[multiprocessing.Process(target=_lock_process,args=(path,queue)) for _ in range(2)]
            for process in processes: process.start()
            for process in processes: process.join(10)
            results=[queue.get(timeout=2)[0] for _ in processes]
            self.assertEqual(sum(results),1)

    def test_lock_09_collision_does_not_modify_progress(self):
        with tempfile.TemporaryDirectory() as d:
            progress=Path(d)/"progress.json"; progress.write_text('{"valid_shadow_sessions":0}',encoding="utf-8"); before=progress.read_bytes(); lock=progress.with_suffix(".json.lock"); lock.write_text("foreign",encoding="utf-8")
            with self.assertRaises(SingleSessionLockCollision): acquire_owned_lock(lock,purpose="p",target_resource=str(progress),now=NOW)
            self.assertEqual(progress.read_bytes(),before)

    def test_lock_10_fault_detects_collision(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.lock"; path.write_text("foreign",encoding="utf-8")
            detected=False
            try: acquire_owned_lock(path,purpose="p",target_resource="r",now=NOW)
            except SingleSessionLockCollision as exc: detected=str(exc)=="SINGLE_SESSION_LOCK_COLLISION"
            self.assertTrue(detected); self.assertTrue(path.exists())


class HistoryPaginationTests(unittest.TestCase):
    def test_hist_01_multiple_pages_reach_minimum(self):
        client=PageClient([Response([chart_row(1),chart_row(2)],"Y","a"),Response([chart_row(3),chart_row(4)],"Y","b"),Response([chart_row(5)],"N",None)])
        rows,meta=_daily_chart_pages(session(client),ticker="AAPL",stex_tp="ND",completed_session="2026-08-12",price_basis="RAW")
        self.assertEqual(len(rows),5); self.assertEqual(meta["status"],"SUFFICIENT")
        self.assertNotIn("retry_on_auth_failure", client.kwargs[0])

    def test_hist_02_raw_adjusted_each_sufficient(self):
        for basis in ("RAW","ADJUSTED"):
            client=PageClient([Response([chart_row(i) for i in range(5)])]); _,meta=_daily_chart_pages(session(client),ticker="AAPL",stex_tp="ND",completed_session="2026-08-12",price_basis=basis); self.assertEqual(meta["status"],"SUFFICIENT")

    def test_hist_03_identical_duplicates_deduplicate(self):
        rows=[chart_row(1),chart_row(1),chart_row(2)]; result=normalize_series(rows,ticker="AAPL",completed_session="2025-01-03",price_basis="RAW",minimum_history_bars=2); self.assertEqual(result["history_bar_count"],2)

    def test_hist_04_conflicting_duplicates_fail(self):
        rows=[chart_row(1,100),chart_row(1,110)]; result=normalize_series(rows,ticker="AAPL",completed_session="2025-01-02",price_basis="RAW"); self.assertIn("CONFLICTING_DUPLICATE_BAR:2025-01-02",result["validation_errors"])

    def test_hist_05_no_progress_fails_closed(self):
        repeated=[chart_row(1),chart_row(2)]; client=PageClient([Response(repeated,"Y","a"),Response(repeated,"Y","b")])
        with self.assertRaisesRegex(BridgeError,"KIWOOM_PAGINATION_NO_PROGRESS"): _daily_chart_pages(session(client,minimum=5),ticker="AAPL",stex_tp="ND",completed_session="2026-08-12",price_basis="RAW")

    def test_hist_06_exhaustion_is_insufficient(self):
        client=PageClient([Response([chart_row(1),chart_row(2)],"N",None)]); _,meta=_daily_chart_pages(session(client,minimum=5),ticker="AAPL",stex_tp="ND",completed_session="2026-08-12",price_basis="RAW"); self.assertEqual(meta["status"],"INSUFFICIENT_HISTORY")

    def test_hist_07_pacer_applies_each_page(self):
        calls=[]; client=PageClient([Response([chart_row(1),chart_row(2)],"Y","a"),Response([chart_row(3),chart_row(4)],"Y","b"),Response([chart_row(5)])]); _daily_chart_pages(session(client,pacer=lambda:calls.append(1)),ticker="AAPL",stex_tp="ND",completed_session="2026-08-12",price_basis="RAW"); self.assertEqual(len(calls),3)

    def test_hist_08_raw_adjusted_same_end(self):
        raw=normalize_series([chart_row(1),chart_row(2)],ticker="AAPL",completed_session="2025-01-03",price_basis="RAW",minimum_history_bars=2); adj=normalize_series([chart_row(1),chart_row(2)],ticker="AAPL",completed_session="2025-01-03",price_basis="ADJUSTED",minimum_history_bars=2); self.assertEqual(raw["bars"][-1]["session"],adj["bars"][-1]["session"])

    def test_hist_09_future_bar_rejected(self):
        result=normalize_series([chart_row(1),chart_row(10)],ticker="AAPL",completed_session="2025-01-02",price_basis="RAW"); self.assertTrue(any(x.startswith("FUTURE_BAR_REJECTED") for x in result["validation_errors"]))

    def test_hist_10_minimum_loaded_from_policy(self):
        policy=load_json(ROOT/"workspace/policies/kiwoom-rate-limit-policy.json"); self.assertEqual(policy["history_policy"]["minimum_history_bars"],252)


def synthetic_series(price_basis="ADJUSTED", corruption=0.0):
    rows=[]
    start=datetime(2025,1,1,tzinfo=timezone.utc)
    for i in range(260):
        session=(start+timedelta(days=i)).date().isoformat(); close=100+i*0.1+(corruption if i==259 else 0)
        rows.append({"session":session,"open":close-1,"high":close+1,"low":close-2,"close":close,"volume":1000+i})
    return {"ticker":"AAPL","price_basis":price_basis,"fx_applied":False,"completed_session":rows[-1]["session"],"completed_close":rows[-1]["close"],"bars":rows,"history_bar_count":260,"minimum_history_bars":252,"history_status":"SUFFICIENT","validation_errors":[],"pagination":None,"status":"PASS","order_authority":False}


class AdjustedComparisonTests(unittest.TestCase):
    def snapshot(self, adjusted=None):
        raw=synthetic_series("RAW"); return {"completed_session":raw["completed_session"],"ticker_results":[{"ticker":"AAPL","raw":raw,"adjusted":adjusted or synthetic_series()}]}
    def primary(self):
        raw=synthetic_series("RAW"); return {"session":{"us_session_date":raw["completed_session"]},"symbols":{"AAPL":{"bar_date":raw["completed_session"],"close":raw["completed_close"]}}}
    def policy(self,basis="COMPATIBLE"): return {"basis_status":basis,"reuse_approved_raw_tolerance_for_same_basis":True,"minimum_common_sessions":252}
    def compare(self, adjusted=None, policy=None, kt=None, yt=None): return compare_snapshots(self.snapshot(adjusted),self.primary(),tolerance_policy={"absolute_usd_floor":0.05,"relative_fraction":0.001},decision_boundaries=None,generated_at=NOW,adjustment_policy=policy or self.policy(),yfinance_adjusted_series={"AAPL":synthetic_series()},kiwoom_technical={"AAPL":kt} if kt else None,yfinance_technical={"AAPL":yt} if yt else None)
    def test_adj_01_same_basis_match(self): self.assertEqual(self.compare()["results"][0]["adjusted_comparison_status"],"MATCH")
    def test_adj_02_same_basis_conflict(self): self.assertEqual(self.compare(synthetic_series(corruption=10))["results"][0]["adjusted_comparison_status"],"CONFLICT")
    def test_adj_03_unknown_inconclusive(self): self.assertEqual(self.compare(policy=self.policy("UNKNOWN"))["results"][0]["adjusted_comparison_status"],"INCONCLUSIVE")
    def test_adj_04_incompatible_explicit(self): self.assertEqual(self.compare(policy=self.policy("INCOMPATIBLE"))["results"][0]["adjustment_basis_status"],"INCOMPATIBLE")
    def test_adj_05_raw_match_cannot_hide_conflict(self): self.assertEqual(self.compare(synthetic_series(corruption=10))["comparison_status"],"CONFLICT")
    def test_adj_06_adjusted_does_not_overwrite_raw(self): self.assertEqual(self.compare(synthetic_series(corruption=10))["results"][0]["raw_comparison_status"],"MATCH")
    def test_adj_07_indicator_mismatch_reported(self):
        base={"status":"KIWOOM_TECHNICAL_VALIDATED","formula_version":"v","decision_signature":{"ema10_reclaim_confirmed":False}}; other=json.loads(json.dumps(base)); other["status"]="YFINANCE_TECHNICAL_VALIDATED"; other["decision_signature"]["ema10_reclaim_confirmed"]=True; self.assertEqual(compare_technical_decisions(base,other)[0],"CONFLICT")
    def test_adj_08_decision_flip_blocks(self):
        base=calculate_kiwoom_technical(synthetic_series("RAW"),synthetic_series(),cutoff=synthetic_series()["completed_session"],minimum_history_bars=252); other=json.loads(json.dumps(base)); other["status"]="YFINANCE_TECHNICAL_VALIDATED"; field=next(iter(other["decision_signature"])); other["decision_signature"][field]=not other["decision_signature"][field]; self.assertTrue(self.compare(kt=base,yt=other)["results"][0]["technical_decision_flip"])
    def test_adj_09_soxl_direct_only(self): self.assertNotIn("SOXX",json.dumps(self.snapshot()))
    def test_adj_10_mvll_direct_only(self): self.assertNotIn("MRVL",json.dumps(self.snapshot()))
    def test_adj_11_proxy_multiplication_absent(self): self.assertNotIn("times_multiple",json.dumps(self.compare()))
    def test_adj_12_fault_detects_adjusted_conflict(self): self.assertIn("ADJUSTED_SERIES_CONFLICT",self.compare(synthetic_series(corruption=10))["results"][0]["adjusted_comparison_reason_codes"])


class KiwoomTimingRecordTests(unittest.TestCase):
    def calculate(self, raw=None, adjusted=None, **kwargs):
        raw = raw if raw is not None else synthetic_series("RAW")
        adjusted = adjusted if adjusted is not None else synthetic_series()
        return calculate_kiwoom_technical(raw, adjusted, cutoff=raw["completed_session"],
                                        minimum_history_bars=252, **kwargs)

    def snapshot(self, record, *, crosscheck=False):
        from validate_technical_snapshot import EXPECTED_SCHEMA_VERSION, EXPECTED_FORMULA_VERSION, EXPECTED_TIMING_FEATURE_VERSION
        record = json.loads(json.dumps(record))
        date = record["bar_date"]
        if crosscheck:
            record["quote_crosscheck"] = {
                "status": "verified", "independent_of_builder": True,
                "source": "SYNTHETIC_TEST_ONLY", "source_url": "https://example.invalid/test-close",
                "bar_date": date, "verified_at_utc": date + "T22:00:00+00:00",
                "completed_close": record["close"], "difference_usd": 0,
                "tolerance_usd": max(0.05, 0.001 * record["close"]),
            }
        return {
            "schema_version": EXPECTED_SCHEMA_VERSION, "generated_at_utc": date + "T22:00:00+00:00",
            "session": {"us_session_date": date, "expected_us_session_date": date,
                        "regular_session_complete": True, "is_early_close": False,
                        "official_calendar_verified": True, "calendar_verification_status": "verified_trading_day",
                        "calendar_source_type": "official_exchange_or_regulator", "calendar_source": "SYNTHETIC_TEST_ONLY",
                        "calendar_verified_at_utc": date + "T22:00:00+00:00"},
            "indicator_provenance": {"formula_version": EXPECTED_FORMULA_VERSION,
                "timing_feature_version": EXPECTED_TIMING_FEATURE_VERSION,
                "technical_price_basis": record["technical_price_basis"],
                "ema_formula": "existing ewm adjust=False", "atr_formula": "existing Wilder ATR14"},
            "symbols": {"AAPL": record}, "errors": [],
        }

    def test_optional_projection_preserves_legacy_calculation_and_inputs(self):
        raw, adjusted = synthetic_series("RAW"), synthetic_series()
        before = json.dumps([raw, adjusted], sort_keys=True)
        legacy = self.calculate(raw, adjusted)
        extended = self.calculate(raw, adjusted, include_timing_record=True)
        self.assertEqual(legacy, {k: v for k, v in extended.items() if k != "timing_record"})
        self.assertEqual(before, json.dumps([raw, adjusted], sort_keys=True))
        row = extended["timing_record"]
        self.assertEqual(len(row["timing_window"]), 30)
        self.assertEqual(row["source_provider"], "KIWOOM_REST")
        self.assertNotIn("Yahoo", row["source"])
        self.assertIsNone(row["quote_crosscheck"])
        self.assertTrue(row["corporate_action_unresolved"])
        self.assertFalse(extended["order_authority"])

    def test_real_technical_validator_accepts_calculation_only_with_fixture_crosscheck(self):
        from validate_technical_snapshot import validate_snapshot
        row = self.calculate(include_timing_record=True)["timing_record"]
        missing = validate_snapshot(self.snapshot(row), required_symbols=["AAPL"])
        self.assertEqual(missing["status"], "rejected")
        self.assertTrue(any("cross-check" in error for error in missing["errors"]))
        complete = validate_snapshot(self.snapshot(row, crosscheck=True), required_symbols=["AAPL"])
        self.assertEqual(complete["errors"], [])
        self.assertEqual(complete["status"], "verified")  # Synthetic numerical/schema test, not live source acceptance.

    def test_binding_errors_do_not_produce_a_timing_record(self):
        for field, value in (("ticker", "OTHER"), ("price_basis", "RAW"),
                             ("status", "DATA_BLOCKED"), ("completed_session", "2099-01-01"),
                             ("validation_errors", ["FUTURE_BAR_REJECTED"])):
            adjusted = synthetic_series(); adjusted[field] = value
            with self.subTest(field=field):
                result = self.calculate(adjusted=adjusted, include_timing_record=True)
                self.assertNotIn("timing_record", result)
                self.assertIn("TIMING_INPUT_BINDING_INVALID", result["validation_errors"])

    def test_short_history_does_not_lower_consumer_minimum(self):
        adjusted = synthetic_series(); adjusted["bars"] = adjusted["bars"][-100:]
        result = self.calculate(adjusted=adjusted, include_timing_record=True)
        self.assertNotIn("timing_record", result)
        self.assertIn("INSUFFICIENT_HISTORY", result["validation_errors"])
        raw, adjusted = synthetic_series("RAW"), synthetic_series()
        result = calculate_kiwoom_technical(raw, adjusted, cutoff=raw["completed_session"],
                                          minimum_history_bars=1, include_timing_record=True)
        self.assertNotIn("timing_record", result)
        self.assertIn("TIMING_HISTORY_MINIMUM_NOT_MET", result["validation_errors"])


class PointInTimeTests(unittest.TestCase):
    def checkpoint(self,session="2026-08-12",current="2026-08-12",previous=None): return build_checkpoint(market_session=session,current_completed_session=current,analysis_cutoff="2026-08-13T00:00:00+00:00",created_at="2026-08-13T00:01:00+00:00",portfolio_state_revision=13,portfolio_hash="a"*64,event_evidence_cutoff="2026-08-12T23:59:00+00:00",event_bundle_hash="b"*64,active_baselines=[{"baseline_id":"NBIS","baseline_hash":"c"*64}],policy_hashes={"alert":"d"*64},registry_hash="e"*64,source_artifact_hashes={"portfolio":"a"*64},previous_record_hash=previous)
    def test_pit_01_no_backfill(self):
        with self.assertRaisesRegex(ValueError,"HISTORICAL_BACKFILL"): self.checkpoint("2026-08-11","2026-08-12")
    def test_pit_02_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.checkpoint(); append_checkpoint(Path(d),c)
            with self.assertRaises(FileExistsError): append_checkpoint(Path(d),c)
    def test_pit_03_hash_chain(self):
        first=self.checkpoint(); second=self.checkpoint("2026-08-13","2026-08-13",first["record_hash"]); self.assertTrue(validate_hash_chain([first,second]))
    def test_pit_04_current_portfolio_not_prior(self):
        with self.assertRaises(ValueError): self.checkpoint("2026-08-01","2026-08-12")
    def test_pit_05_event_cutoff(self):
        with self.assertRaisesRegex(ValueError,"EVENT_EVIDENCE"): build_checkpoint(market_session="2026-08-12",current_completed_session="2026-08-12",analysis_cutoff="2026-08-13T00:00:00+00:00",created_at=NOW,portfolio_state_revision=13,portfolio_hash="a"*64,event_evidence_cutoff="2026-08-14T00:00:00+00:00",event_bundle_hash=None,active_baselines=[],policy_hashes={},registry_hash="e"*64,source_artifact_hashes={},previous_record_hash=None)
    def test_pit_06_baseline_session_specific(self): self.assertEqual(self.checkpoint()["market_session"],"2026-08-12")
    def test_pit_07_no_secret_or_account(self): self.assertNotIn("account_number",json.dumps(self.checkpoint()).lower())
    def test_pit_08_schema_and_portfolio_immutability(self):
        path=ROOT/"stock-strategy-system/portfolio_state.json"; before=path.read_bytes(); value=self.checkpoint(); self.assertTrue(validate_checkpoint_hash(value)); self.assertEqual(validate_instance(value,SCHEMAS/"point-in-time-context-checkpoint.schema.json"),[]); self.assertEqual(path.read_bytes(),before)
    def test_pit_09_baseline_reference_uses_semantic_hash(self):
        path=ROOT/"workspace/research/holding-baselines/SOXL/soxl-20260813-v1.json"
        reference, artifact_hash=baseline_reference(path)
        self.assertEqual(reference["baseline_id"],"soxl-20260813-v1")
        self.assertEqual(reference["baseline_hash"],load_json(path)["baseline_hash"])
        self.assertEqual(len(artifact_hash),64)
    def test_pit_10_invalid_baseline_hash_fails_closed(self):
        path=ROOT/"workspace/research/holding-baselines/SOXL/soxl-20260813-v1.json"
        with tempfile.TemporaryDirectory() as directory:
            corrupted=load_json(path); corrupted["baseline_hash"]="0"*64
            target=Path(directory)/"baseline.json"; target.write_text(json.dumps(corrupted),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"BASELINE_HASH_MISMATCH"):
                baseline_reference(target)


class ReplayScopingTests(unittest.TestCase):
    def test_missing_research_does_not_block_market_data(self):
        value=replay_status_axes(market_data_valid=True,technical_status="KIWOOM_TECHNICAL_VALIDATED",research_context_status="PARTIAL_EXPECTED_NO_ARCHIVE",event_context_status="UNAVAILABLE",portfolio_context_status="UNAVAILABLE"); self.assertEqual(value["market_data_status"],"VALIDATED"); self.assertEqual(value["execution_status"],"RESEARCH_REFRESH_REQUIRED")
    def test_invalid_market_is_data_blocked(self):
        value=replay_status_axes(market_data_valid=False,technical_status="KIWOOM_TECHNICAL_INVALID",research_context_status="COMPLETE",event_context_status="COMPLETE",portfolio_context_status="COMPLETE"); self.assertEqual(value["execution_status"],"DATA_BLOCKED")

    def test_future_yfinance_action_is_excluded(self):
        future=int(datetime(2026,8,14,tzinfo=timezone.utc).timestamp())
        result={"events":{"dividends":{"future":{"date":future,"amount":1.0}}}}
        self.assertEqual(_actions(result,"2026-08-12"),[])

    def test_completed_close_mismatch_is_rejected(self):
        raw=synthetic_series("RAW"); adjusted=synthetic_series()
        raw["completed_close"] += 1.0
        snapshot={
            "provider_state":"SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED",
            "primary_provider":"yfinance", "order_authority":False,
            "operational_shadow_session_increment":0,
            "completed_session":raw["completed_session"],
            "official_runtime_commit":"a"*40,
            "session_lock":{"status":"LOCKED","completed_session":raw["completed_session"]},
            "ticker_results":[{"ticker":"AAPL","status":"PASS","order_authority":False,
                "identity":{"mapping_status":"VERIFIED","mapping_guessed":False,"order_authority":False,"official_runtime_commit":"a"*40},
                "raw":raw,"adjusted":adjusted}],
        }
        self.assertTrue(any("completed close mismatch" in error for error in validate_snapshot_semantics(snapshot)))

    def test_current_context_validates_active_baseline_without_historical_reuse(self):
        index=load_json(ROOT/"workspace/research/holding-baselines/active-index.json")
        context=current_context_status(session="2026-08-13",event_bundle=None,baseline_index=index,repo_root=ROOT)
        self.assertEqual(context["baseline_validation_status"],"COMPLETE")
        self.assertIn("SOXL",context["active_baseline_hashes"])
        self.assertFalse(context["historical_context_reuse"])

    def test_current_context_keeps_incomplete_event_visible(self):
        dry={"results":[{"ticker":"SOXL","holding_status":"VERIFIED_HELD","strategy_or_opportunity_state":"STRATEGY_REFRESH_REQUIRED"}]}
        context={"event_context_status":"REVIEW_REQUIRED","active_baseline_hashes":{"SOXL":"a"*64}}
        updated=apply_current_context(dry,context)
        self.assertEqual(updated["results"][0]["research_context_status"],"COMPLETE")
        self.assertEqual(updated["results"][0]["event_context_status"],"REVIEW_REQUIRED")
        self.assertEqual(updated["results"][0]["strategy_or_opportunity_state"],"STRATEGY_REFRESH_REQUIRED")


if __name__ == "__main__": unittest.main()
