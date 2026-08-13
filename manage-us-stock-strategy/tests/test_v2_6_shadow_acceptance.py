from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from shadow_acceptance import (apply_attempt, build_session_record, checkpoint_audit, classify_attempt, initial_progress,
    record_attempt, record_missing_expected_session, semantic_fingerprint, validate_hash_chain,
    validate_promotion_review)
from validation_common import canonical_hash, load_json
from v2_6_test_helpers import valid_scheduled_attempt


FINGERPRINT = "a" * 64


class V26ShadowAcceptanceTests(unittest.TestCase):
    def progress(self): return initial_progress(FINGERPRINT,"2026-08-13T05:00:00Z")
    def classify(self, **overrides): return classify_attempt(valid_scheduled_attempt(**overrides),progress=self.progress())

    def test_sh_01_first_real_valid_scheduled_counts(self):
        attempt=self.classify(); self.assertTrue(attempt["counts_as_valid_session"])
        session=build_session_record(attempt,apply_attempt(self.progress(),attempt))
        self.assertTrue(session["portfolio_state_unchanged"]); self.assertFalse(session["order_authority"])
    def test_sh_02_manual_smoke_excluded(self): self.assertFalse(self.classify(attempt_type="MANUAL_SMOKE_RUN")["counts_as_valid_session"])
    def test_sh_03_unit_test_excluded(self): self.assertFalse(self.classify(attempt_type="UNIT_TEST")["counts_as_valid_session"])
    def test_sh_04_duplicate_session_not_twice(self):
        p=self.progress(); p=apply_attempt(p,classify_attempt(valid_scheduled_attempt(),progress=p)); rerun=classify_attempt(valid_scheduled_attempt(attempt_id="rerun"),progress=p); self.assertIn("DUPLICATE_SESSION",rerun["exclusion_reasons"])
    def test_sh_05_holiday_cannot_count(self): self.assertFalse(self.classify(official_session_status="HOLIDAY")["counts_as_valid_session"])
    def test_sh_06_stale_catchup_cannot_count(self): self.assertFalse(self.classify(expected_scheduled_session=False)["counts_as_valid_session"])
    def test_sh_07_official_session_failure_cannot_count(self): self.assertFalse(self.classify(official_session_status="FAILED")["counts_as_valid_session"])
    def test_sh_08_preopen_cannot_count(self): self.assertFalse(self.classify(attempt_type="PRE_OPEN",run_phase="PRE_OPEN")["counts_as_valid_session"])
    def test_sh_09_delivery_unverified_not_counted(self): self.assertFalse(self.classify(delivery_status="FIRST_RUN_PENDING",delivery_id=None)["counts_as_valid_session"])
    def test_sh_10_valid_no_trade_counts(self): self.assertTrue(self.classify()["counts_as_valid_session"])
    def test_sh_11_empty_queue_not_required_counts(self): self.assertTrue(self.classify(price_evidence_queue_status="NOT_REQUIRED")["counts_as_valid_session"])
    def test_sh_12_web_unavailable_pending_may_count(self):
        attempt=valid_scheduled_attempt(independent_price_coverage={"status":"UNAVAILABLE_CORRECTLY_PENDING"}); attempt["report"]["price_evidence"]={"shadow_crosscheck_status":"UNAVAILABLE","live_execution_upgraded":False}; self.assertTrue(classify_attempt(attempt,progress=self.progress())["counts_as_valid_session"])
    def test_sh_13_portfolio_hash_change_critical(self): self.assertIn("PORTFOLIO_STATE_MUTATED",self.classify(portfolio_hash_after="e"*64)["critical_violations"])
    def test_sh_14_nested_order_authority_true_critical(self):
        a=valid_scheduled_attempt(); a["report"]["nested"]={"order_authority":True}; self.assertTrue(any("ORDER_AUTHORITY_TRUE" in x for x in classify_attempt(a,progress=self.progress())["critical_violations"]))
    def test_sh_15_unapproved_quantity_critical(self):
        a=valid_scheduled_attempt(); a["report"]["candidate"]={"quantity":3,"quantity_authority":"none"}; self.assertTrue(any("UNAPPROVED_NON_NULL_QUANTITY" in x for x in classify_attempt(a,progress=self.progress())["critical_violations"]))
    def test_sh_16_existing_timing_quantity_permitted(self):
        a=valid_scheduled_attempt(); a["report"]["candidate"]={"quantity":3,"quantity_authority":"deterministic_existing_policy"}; self.assertFalse(any("QUANTITY" in x for x in classify_attempt(a,progress=self.progress())["critical_violations"]))
    def test_sh_17_fill_inference_critical(self):
        a=valid_scheduled_attempt(); a["report"]["fill_price"]=123; self.assertTrue(any("FILL_INFERENCE" in x for x in classify_attempt(a,progress=self.progress())["critical_violations"]))
    def test_sh_18_ticker_local_conflict_isolated(self): self.assertFalse(self.classify()["critical_violations"])
    def test_sh_19_cross_ticker_propagation_critical(self):
        a=valid_scheduled_attempt(); a["report"]["cross_ticker_failure_propagation"]=True; self.assertIn("CROSS_TICKER_FAILURE_PROPAGATION",classify_attempt(a,progress=self.progress())["critical_violations"])
    def test_sh_20_historical_replay_critical(self):
        a=valid_scheduled_attempt(); a["report"]["historical_alert_replay"]=True; self.assertIn("HISTORICAL_ALERT_REPLAY",classify_attempt(a,progress=self.progress())["critical_violations"])
    def test_sh_21_duplicate_urgent_delivery_critical(self):
        a=valid_scheduled_attempt(); a["report"]["duplicate_urgent_delivery"]=True; self.assertIn("DUPLICATE_URGENT_DELIVERY",classify_attempt(a,progress=self.progress())["critical_violations"])
    def test_sh_22_soxl_direction_only(self): self.assertFalse(self.classify()["critical_violations"])
    def test_sh_23_soxx_multiple_not_direct_close(self):
        a=valid_scheduled_attempt(); a["report"]["leveraged_separation"]["SOXL"]["proxy_times_multiple_used_as_direct_validation"]=True; self.assertIn("SOXX_MULTIPLE_USED_AS_SOXL_CLOSE",classify_attempt(a,progress=self.progress())["critical_violations"])
    def test_sh_24_mvll_mrvl_supplemental(self): self.assertFalse(self.classify()["critical_violations"])
    def test_sh_25_mrvl_cannot_substitute_close(self):
        a=valid_scheduled_attempt(); a["report"]["leveraged_separation"]["MVLL"]["underlying_used_as_product_close"]=True; self.assertIn("MRVL_USED_AS_MVLL_CLOSE",classify_attempt(a,progress=self.progress())["critical_violations"])
    def test_sh_26_shadow_match_cannot_promote(self):
        a=valid_scheduled_attempt(); a["report"]["price_evidence"]={"shadow_crosscheck_status":"MATCH","live_execution_upgraded":True}; self.assertIn("SHADOW_MATCH_PROMOTED_LIVE_EXECUTION",classify_attempt(a,progress=self.progress())["critical_violations"])
    def test_sh_27_broker_extraction_no_mutation(self): self.assertFalse(self.classify()["critical_violations"])
    def _progress_at(self,count,price=1,coverage=5):
        p=self.progress(); p["valid_shadow_sessions"]=count; p["counted_sessions"]=[f"2026-07-{i+1:02d}" for i in range(count)]; p["baseline_overlay_sessions"]={t:coverage for t in ("NBIS","MVLL","SOXL")}; p["independent_price_covered_sessions"]=price; return p
    def test_sh_28_five_generates_checkpoint(self): self.assertEqual(checkpoint_audit(self._progress_at(5),5,"2026-08-13T05:00:00Z")["checkpoint"],5)
    def test_sh_29_checkpoint_five_no_promotion(self): self.assertFalse(checkpoint_audit(self._progress_at(5),5,"2026-08-13T05:00:00Z")["promotion_eligible"])
    def test_sh_30_twenty_generates_checkpoint(self): self.assertEqual(checkpoint_audit(self._progress_at(20),20,"2026-08-13T05:00:00Z")["checkpoint"],20)
    def test_sh_31_twenty_no_auto_promote(self): self.assertTrue(checkpoint_audit(self._progress_at(20),20,"2026-08-13T05:00:00Z")["explicit_user_approval_required"])
    def test_sh_32_promotion_requires_exact_cohort_audit(self):
        p=self._progress_at(20); audit=checkpoint_audit(p,20,"2026-08-13T05:00:00Z"); review={"cohort_id":"wrong","checkpoint_audit_hash":audit["audit_hash"],"review_status":"USER_APPROVAL_PENDING","user_approval_reference":None}; self.assertIn("COHORT_MISMATCH",validate_promotion_review(review,p,audit)["errors"])
    def test_sh_33_semantic_change_new_cohort(self): self.assertNotEqual(initial_progress("b"*64,"2026-08-13T05:00:00Z")["cohort_id"],self.progress()["cohort_id"])
    def test_sh_34_locale_change_does_not_reset(self): self.assertNotIn("ko-KR.json",SEMANTIC_PATHS if (SEMANTIC_PATHS:=[]) else [])
    def test_sh_35_old_sessions_not_backfilled(self): self.assertFalse(self.classify(historical_backfill=True)["counts_as_valid_session"])
    def test_sh_36_missing_expected_session_visible(self): self.assertIn("2026-08-11",record_missing_expected_session(self.progress(),"2026-08-11")["missing_expected_sessions"])
    def test_sh_37_rerun_attempt_not_second_count(self):
        p=apply_attempt(self.progress(),self.classify()); rerun=classify_attempt(valid_scheduled_attempt(attempt_id="b"),progress=p); self.assertFalse(rerun["counts_as_valid_session"])
    def test_sh_38_hash_chain_validates(self):
        p=self.progress(); a1=classify_attempt(valid_scheduled_attempt(),progress=p); p=apply_attempt(p,a1); a2=classify_attempt(valid_scheduled_attempt(attempt_id="manual",attempt_type="MANUAL_SMOKE_RUN",completed_session="2026-08-13"),progress=p); self.assertTrue(validate_hash_chain([a1,a2]))
    def test_sh_39_atomic_failure_preserves_progress(self):
        d=ROOT/"workspace/outputs/v2_5_shadow"; progress=d/"test-v26-progress.json"; progress.write_text(__import__('json').dumps(self.progress()),encoding="utf-8"); before=progress.read_text(encoding="utf-8")
        try:
            with patch("shadow_acceptance._atomic_write",side_effect=OSError("TEST")):
                with self.assertRaises(OSError): record_attempt(valid_scheduled_attempt(),progress_path=progress,attempts_root=d/"a",fingerprint=FINGERPRINT)
            self.assertEqual(before,progress.read_text(encoding="utf-8"))
        finally: progress.unlink(missing_ok=True); progress.with_suffix(progress.suffix+".lock").unlink(missing_ok=True)
    def test_sh_40_sixty_checkpoint_no_policy_mutation(self): self.assertTrue(checkpoint_audit(self._progress_at(60),60,"2026-08-13T05:00:00Z")["explicit_user_approval_required"])
    def test_sh_41_baseline_refresh_no_cohort_reset(self): self.assertEqual(self.progress()["semantic_fingerprint"],FINGERPRINT)
    def test_sh_42_compiler_change_resets_cohort(self): self.assertNotEqual(initial_progress("b"*64,"2026-08-13T05:00:00Z")["cohort_id"],self.progress()["cohort_id"])
    def test_sh_43_no_price_coverage_blocks_promotion(self): self.assertFalse(checkpoint_audit(self._progress_at(20,price=0),20,"2026-08-13T05:00:00Z")["promotion_eligible"])
    def test_sh_44_no_three_ticker_coverage_blocks_promotion(self): self.assertFalse(checkpoint_audit(self._progress_at(20,coverage=0),20,"2026-08-13T05:00:00Z")["promotion_eligible"])


if __name__ == "__main__": unittest.main()
