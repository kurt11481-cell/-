---
id: state-fixture2-report
title: "state-fixture2 Builder 보고 — 타이밍 통합 시험이 저장소 안 합성 상태를 읽게"
date: 2026-11-01
---

## (a) 바꾼 줄
- `manage-us-stock-strategy/tests/test_evaluate_timing_integration.py:41` — 새 상수 `TIMING_STATE_FIXTURE`(fixture 경로) 추가.
- 같은 파일 `:103` — `setUp`이 실제 상태 파일 대신 `TIMING_STATE_FIXTURE`를 읽는다.
- 같은 파일 `:326` — `test_i0b_t3_...`의 `state_path`를 `TIMING_STATE_FIXTURE`로 바꿨다. 이 시험은 바이트를 읽기만 하고 쓰지 않는다.
- 줄바꿈은 CRLF 그대로다(바뀐 3줄 모두 CRLF 확인).
- `test_portfolio_decision_dashboard.py`는 고치지 않았다. `ManualStep2TimingTests.setUp`이 `case.setUp()`으로 상태를 이어받기 때문에 출처가 저절로 바뀐다.
- 새 파일 `manage-us-stock-strategy/tests/fixtures/portfolio_state.timing.test-only.json`.
- 단언·기대값·skip 변경 없음. scripts·정책·실제 상태 파일 변경 없음.

## (b) fixture 키 목록
최상위: `test_only`, `schema_version`, `strategy_version`, `state_revision`, `state_status`, `strategy_mode`, `last_updated_at`, `last_confirmed_broker_snapshot`(verified, authority_state, source, scope, account_id_masked, account_identifier_stored, evidence_bundle_id, evidence_sha256, confirmed_at, as_of, as_of_timestamp, holdings_complete, cash_verified, cash_verified_scope, open_orders_verified, confirmation_method, proposal_id), `holdings`, `average_cost_usd`, `position_cost_basis_usd`, `aggregate_cost_basis_usd`, `brokerage_cash_usd`, `available_cash_usd`, `cash_pct_estimate`, `current_stage`, `confirmed_trades`, `unreconciled_holding_changes`, `holding_change_reconciliations`, `pending_candidates`, `timing_plan`(policy_version, order_authority, positions[SOXL·MVLL: anchor_id, anchor_shares, completed_tranche_ids, confirmed_tranche_fills]), `state_notes`.
빼 둔 키: `broker_display_snapshot`, `archived_prior_strategy`(시험 코드가 읽지 않는다).
대부분 합성값이다. 실제 현금·원가·평균단가·브로커 표시값·계좌 식별자·메모를 옮기지 않았다. 체결 기록의 수량과 trigger_path는 시험 슬롯 값(수량 검사·허용 목록) 때문에 실제와 같고, 체결 날짜(session, confirmed_at_kst)는 실제와 다른 합성값이다. 수량 숫자는 적지 않는다.
- 보유 종목은 MVLL·SOXL·NBIS뿐이다. 수량은 시험이 전제하는 타이밍 anchor(시험 파일 안 `RETIRED_TIMING_POSITIONS`)와 맞춘 값이다.
- SOXL 평균단가는 `test_technical_validation_failure_does_not_hide_hard_risk`가 낮은 종가에서는 하드 리스크, 기본 종가에서는 비위반이 되도록 고른 둥근 합성값이다(처음 값으로는 이 시험이 실패해 바꿨다).
- 처음엔 fixture에 `test_only: true` 표시 키를 넣었다. `evaluate_alerts`는 모르는 키를 거부하지 않았고 시험이 통과했다.

## (c) 대상 테스트 전·후 결과 마지막 3줄
`test_evaluate_timing_integration.py` 전:
```
Ran 14 tests in 0.044s

FAILED (failures=8, errors=1)
```
후:
```
Ran 14 tests in 0.063s

OK
```
`test_portfolio_decision_dashboard.py` 전:
```
Ran 306 tests in 71.257s

FAILED (failures=249)
```
후:
```
Ran 306 tests in 267.550s

FAILED (failures=1)
```
두 명령은 지시문 그대로 실행했다(앞에 환경 변수·옵션 없음).

## (d) 남은 실패
- `test_portfolio_decision_dashboard.PortfolioDecisionDashboardTests.test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan` — git 밖 `workspace/outputs/manual-portfolio-analysis/...` 파일에 의존한다(1502~1504행 `assertTrue(fixture.is_file())`). 지시문 5항에 따라 이번 범위 밖이라 손대지 않았다. 원인 확인은 이 시험 코드 읽기까지만 했다.

## (e) 실제 상태 파일을 읽는 다른 테스트 후보 (이번 범위 밖)
`portfolio_state.json` 또는 `DEFAULT_PORTFOLIO_STATE`를 언급하는 시험 파일(Grep 건수 합계 56건, 31개 파일). 언급이 곧 실제 파일을 읽는다는 뜻은 아니며 파일별로 읽는지는 확인하지 않았다(확인 필요).
test_auto_core.py, test_auto_core_decide.py, test_continuous_improvement_sidecar.py, test_dev_pipeline.py, test_event_resolution_integration.py, test_kiwoom_broker_shadow.py, 키움 주문 차단 훅 시험 1개, test_manual_portfolio_analysis.py, test_portfolio_decision_dashboard.py(남은 `DEFAULT_PORTFOLIO_STATE` 언급 포함), test_portfolio_exposure_judge_fixes.py, test_portfolio_reallocation_shadow.py, test_reconcile_broker_state.py, test_run_portfolio_exposure_review.py, test_s7_calendar_binding.py, test_save_daily_pipeline.py, test_sec_official_event_intake.py, test_test_only_scheduler_control_plane.py, test_v2_1_hardening.py, test_v2_3_portfolio_strategy.py, test_v2_4_dual_phase.py, test_v2_4_preopen_refresh.py, test_v2_6_12_holding_valuation_shadow.py, test_v2_6_13_holding_event_completion.py, test_v2_6_3_free_web_new_buy.py, test_v2_6_4_kiwoom_adapter.py, test_v2_6_5_kiwoom_replay_hardening.py, test_v2_6_7_session_aware_kiwoom_priority.py, test_v2_6_8_finalized_postmarket_automation.py, test_v2_6_9_current_event_risk.py, test_v2_6_holding_research_baseline.py, test_v2_6_integration.py.

## 점검 메모
- 이 세션에서 셸 `sed -i` 편집과 `$'\r'` 같은 이스케이프 포함 명령은 승인 불가로 거부되었다. 그래서 시험 파일은 Edit 도구로 고쳤고, 줄바꿈은 Grep으로 확인했다. 전체 스위트·기준선 비교는 파이프라인 몫이다.
- 표지 없음.
