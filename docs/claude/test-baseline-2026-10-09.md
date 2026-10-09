---
id: test-baseline-2026-10-09
title: 전체 테스트 기준선 (A6) — FX-1009 fx-3 Builder 0단계
date: 2026-10-09
class: K0 기록
plan: docs/claude/fx1009-fix-plan-2026-10-09.md 5-3절 3번 · 부록 A6
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 전체 테스트 기준선 2026-10-09

이후 모든 Builder는 이 목록과 비교해 "새 실패 0"을 판정한다. 실패를 고치지 않았고, 코드 변경 전(작업 트리 clean) 상태에서 잰 값이다.

## 측정 조건

| 항목 | 값 |
|---|---|
| 실행 시각 | 2026-10-09 15:13 (로컬, KST) 시작, 319.155초 |
| git HEAD | c7b8f6dbad45c12d268165c906fd57418c11ac92 (브랜치 codex/master-recovery-expansion, worktree fx-dst, 작업 트리 clean) |
| Python | 3.13.15 |
| 명령 | `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` |
| 실행 주체 | test-runner 서브에이전트(Haiku). 출력은 위치 정보일 뿐이라 원본 출력 파일에서 직접 다시 셌다 |

## 결과

`Ran 2492 tests in 319.155s` · `FAILED (failures=18, errors=9, skipped=2)` → 실패 id 합계 27.

개수 검증: 원본 출력의 `FAIL:` 줄 18개, `ERROR:` 줄 8개를 직접 셌다. 9번째 ERROR(아래 E9)는 캡처된 출력 앞부분이 잘려 헤더가 없었고, `test_holding_baseline_observation_audit.py`를 단독 실행해 `ERROR: setUpClass (...)` 1건으로 확인했다. 따라서 18 + 9 = 27이 요약과 일치한다.

## ERROR 9건 (입력 파일 없음 — 이 worktree에 gitignore된 workspace/outputs 등이 없음)

| # | test id | 원인 |
|---|---|---|
| E1 | test_materialize_kiwoom_session_aware_acceptance_candidate.KiwoomAcceptanceCandidateMaterializationTest.test_05_materialized_candidate_passes_binding_validator | source artifact 9개 없음 |
| E2 | test_mvll_canonical_volume_lineage.MvllCanonicalVolumeLineageTests (setUpClass) | FileNotFoundError workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/kiwoom_daily_snapshot.json |
| E3 | test_nbis_v3_shadow_activation.NbisV3ShadowActivationTests.test_price_evidence_preserves_same_session_kiwoom_conflict | FileNotFoundError workspace/outputs/portfolio-strategy/2026-08-13/yfinance_replay_evidence.json |
| E4 | test_nbis_v4_kiwoom_price_authority.NBISV4KiwoomPriceAuthorityTests.test_live_price_artifact_schema_and_semantics | FileNotFoundError workspace/outputs/activation/holding-valuation-shadow/2026-08-13/kiwoom-finalized-snapshot.json |
| E5 | test_nbis_v4_kiwoom_price_authority.NBISV4KiwoomPriceAuthorityTests.test_valuation_uses_kiwoom_and_no_double_count | 위와 같은 파일 |
| E6 | test_portfolio_decision_order_intent.OrderIntentOnlyTests.test_lmt_candidate_classification_is_verified_but_non_actionable | FileNotFoundError workspace/outputs/lmt-instrument-registry-candidate-prep/lmt-instrument-registry-patch-candidate-v1.json |
| E7 | test_provider_limitation_audit.ProviderLimitationAuditTests (setUpClass) | FileNotFoundError workspace/outputs/portfolio-strategy/2026-08-13/kiwoom_market_snapshot.json |
| E8 | test_validate_research_packet.ResearchPacketHardeningTests.test_snapshot_fixture_declares_contract_version | FileNotFoundError stock-strategy-system/market_snapshot.example.json |
| E9 | test_holding_baseline_observation_audit.HoldingBaselineObservationAuditTests (setUpClass) | FileNotFoundError workspace/outputs/activation/nbis-v2-shadow/20260814-v4/activation-receipt.json |

## FAIL 18건

| # | test id | 원인 |
|---|---|---|
| F1 | test_instrument_identity_authority.InstrumentIdentityAuthorityTest.test_15_current_fixed_activation_is_exactly_bound | 'VERIFIED' != 'NOT_VERIFIED' |
| F2 | test_materialize_instrument_identity_artifact.ConfirmationIdentityCandidateTest.test_candidate_support_does_not_replace_active_registry | 'UNKNOWN_SYMBOL' != 'INTEGRITY_FAILURE' |
| F3 | test_materialize_kiwoom_session_aware_acceptance_candidate.SyntheticPredecessorDriftTest.test_12_allowed_drift_is_recorded_and_validates | 'source artifact missing' 9건 |
| F4 | test_portfolio_decision_dashboard.PortfolioDecisionDashboardTests.test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan | fixture.is_file() False |
| F5 | test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_bom_raw_sha_mismatch_rejected | current Acceptance binding 835d4f46…e429c 가 manifest 0개와 일치 |
| F6 | …InvariantAndContractTests.test_crlf_raw_sha_mismatch_rejected | 같음 |
| F7 | …InvariantAndContractTests.test_duplicate_provider_scope_fails_closed | 같음 |
| F8 | …InvariantAndContractTests.test_extended_provider_scope_candidate_validates_without_activation | 같음 |
| F9 | …InvariantAndContractTests.test_guarded_priority_requires_locked_acceptance_manifest | 같음 |
| F10 | …InvariantAndContractTests.test_historical_and_inactive_candidate_are_not_current_acceptance | 같음 |
| F11 | …InvariantAndContractTests.test_malformed_provider_scope_fails_closed | 같음 |
| F12 | …InvariantAndContractTests.test_missing_acceptance_hash_blocks_guarded_transition | 같음 |
| F13 | …InvariantAndContractTests.test_scope_acceptance_hash_mismatch_blocks_guarded_transition | 같음 |
| F14 | …InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='BRK.B') | 같음 |
| F15 | …InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='BRKb') | 같음 |
| F16 | …InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='COST') | 같음 |
| F17 | …InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='ZZZZ') | 같음 |
| F18 | test_v2_6_7_session_aware_kiwoom_priority.PriorityAndScopeTests.test_scope_04_checked_in_provider_scopes_are_complete_and_locked | 같음 |

F5~F18의 모듈 접두어는 `test_v2_6_7_session_aware_kiwoom_priority`이다.

## 해석 한계

- 모든 실패는 이 worktree에 없는 workspace/outputs·stock-strategy-system 입력, 또는 현재 acceptance manifest 부재에서 나온 환경 의존 실패로 보인다. 메인 체크아웃에서는 통과하는지 확인하지 않았다(확인 필요).
- 이 목록은 "이 worktree의 이 HEAD에서 이미 실패하던 것"의 고정이다. 코드가 옳다는 증거가 아니다.
- 비교 방법: 이후 전체 실행의 ERROR/FAIL id 집합에서 위 27개를 뺀 나머지가 "새 실패"이다. 27개 중 일부가 통과로 바뀌는 것은 새 실패가 아니다.
- test-runner 출력 뒤에 붙은 `NO_MATERIAL_PREOPEN_CHANGE` / `Self-test passed`는 테스트 결과가 아니라 뒤따르는 스크립트 메시지이다.
