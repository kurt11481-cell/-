---
id: cf-b2n-report
title: "cf-b2n Builder 보고 — 외부 유출을 브로커 잔액 두 조회 일치로 인정(대조 I3 예외 B2-N)"
date: 2026-10-25
class: "권한·한도(K3) 수동 경로 — worktree Builder 보고. 다음: 별도 읽기 전용 Judge(Opus) → 병합은 사장 결정"
prompt: "cf-b2n-builder-prompt (2026-10-25), 사장 \"결정 cashflow-proof: B2-N\"(2026-10-23 09:25) · \"결정 cashflow-proof 착수: 승인\"(2026-10-25 08:12)"
worktree: ".claude/worktrees/cf-b2n (branch worktree-cf-b2n, base 5a289b8) — 커밋하지 않음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 0. 실행 경과
- 1차 Builder(08:14 시작)가 보고·종료 기록 없이 끊겼다(원인 확인 필요 — 이 세션에서 확인할 수단 없음). 2차(09:0x, 이 보고)는 처음부터 다시 쓰지 않고 남은 변경을 `git diff`로 읽어 원래 지시문과 대조한 뒤 이어서 마쳤다.
- 2차에서 고친 것: (1) `auto_core_reconcile.py` 머리 docstring의 `I4  the` → `I4 the` 공백 1칸 삭제(의도치 않은 변경)를 원래대로 되돌림 (2) 달력 모듈 import 실패(ImportError)도 이 분기의 HOLD로 남도록 `outflow_ledger`의 예외 목록에 추가(전에는 실행 전체가 예외로 끝날 수 있었음). 나머지(분기·조회·문서·테스트)는 지시문과 맞아 그대로 둠.
- 실행하지 않은 것: `auto_core.py`, `reconcile_broker_state.py apply`, 작업 등록 스크립트, `kiwoomcli`, 키움 호출 — 없음. 상태·정책·일지·원장 파일 쓰기 없음. git commit/push/stash 없음.

## 1. 바뀐 줄 (파일:행, 작업 사본 기준)
| 파일 | 행 | 내용 |
|---|---|---|
| manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py | 32-33 | `ACCOUNT_APIS["account_deposit_by_date_read"] = ("ust21132", "/api/us/acnt")` |
| 同 | 50-51 | 본문 틀 `{"base_dt": ""}` (실측 전: 틀이 다르면 조회 실패 → I3 HOLD) |
| 同 | 58 | `DATED_PARAMETERS`: `("base_dt",)` — YYYYMMDD 한 칸만 본문에 들어감 |
| 同 | 99 | `SAFE_FIELDS`: `("crnc_code", "fx_entr", "won_entr")` 만 남김(계좌 표시 칸 없음) |
| manage-us-stock-strategy/scripts/auto_core_reconcile.py | 12-13 | 머리 설명 I3에 B2-N 한 줄 |
| 同 | 97-102 | 상수 `LEDGER_OPERATION`, `OUTFLOW_MATCH_USD = 0.05`, 사유 코드 2개 |
| 同 | 726-820 | `production_calendar`, `ledger_days`, `ledger_balance`, `unverified_outflow`(2c~2g 판정) |
| 同 | 831-832, 841-842 | `explain_change`에 선택 인자 `outflow_ledger`(기본 None = 기존 동작) + docstring |
| 同 | 890-896 | 예외 분기: R < −1.00 이고 I3 사유가 `CASH_CHANGE_NOT_EXPLAINED:<R>` 하나뿐일 때만 호출 |
| 同 | 906 | I3 결과에 `unverified_outflow_usd`·`unverified_outflow_basis` (통과할 때만) |
| 同 | 1078-1079, 1084-1085 | `run_auto` 선택 인자 `calendar_loader`(기본 운영 달력) + docstring |
| 同 | 1167-1184 | `outflow_ledger` 콜백: 달력 → base_before/base_after → ust21132 2건 읽기(같은 쌍은 1번만), 실패는 이 분기 사유로만 |
| 同 | 1197-1198, 1216-1217 | 두 `explain_change` 호출(기록 기준·직전 실행 비교)에 콜백 전달 |
| 同 | 1246-1248, 1253 | 통과 시 warnings에 `UNVERIFIED_EXTERNAL_OUTFLOW:<금액>` 1줄 |
| manage-us-stock-strategy/references/broker-snapshot-reconciliation.md | 228, 282-303 | I3 표 행에 예외·`UNVERIFIED_OUTFLOW_*` 사유, 본문에 B2-N 단락 |
| docs/claude/automation-redesign-2026-10-10.md | 111 | 불변 조건 3 끝에 지시문 문장 그대로 1문장 |
| manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py | 새 파일 | 22개 시험(아래 4절) |
| docs/claude/cf-b2n-report.md | 새 파일 | 이 보고 |

허용 목록 밖 파일 변경 없음. 스키마 변경 없음 — `auto-core-result.schema.json:32`의 I3 객체는 `required`만 있고 추가 필드를 막지 않는다(warnings도 문자열 배열). "날짜 읽기 요청을 만드는 파일"은 따로 쓰지 않았다(요청은 `run_auto` 안 콜백에서 만듦, `plan_reads`·`dated_requests` 무변경).

## 2. 규칙 요약 (2a~2g ↔ 코드)
`explain_change`가 기존대로 I3 사유를 모두 만든 뒤, 아래를 **모두** 만족할 때만 사유를 비우고 통과시킨다. 하나라도 어긋나면 `CASH_CHANGE_NOT_EXPLAINED:<R>` 뒤에 B2-N 사유 1개를 붙여 HOLD.
- 2a 유출만: `difference < -CASH_TOLERANCE_USD` (`auto_core_reconcile.py:891`). R > +1.00(입금·이자)은 콜백도 부르지 않는다.
- 2b 다른 I3 사유 없음: `i3_reasons == ["CASH_CHANGE_NOT_EXPLAINED:<R>"]` (`:892`) — FILL_*, SETTLEMENT_*(D0 계열 포함, D0일 때는 이 사유 자체가 안 생김), FLOW_ROW_*/UNCLASSIFIED, OPEN_ORDERS_PRESENT, 기준 미상 중 하나라도 있으면 분기에 안 들어가고 ust21132도 읽지 않는다. I1·I2·I4·I5는 손대지 않음(I1 실패면 explain_change 자체를 안 부름).
- 2c 날짜: `ledger_days` — 운영 달력(ACTIVE, decide run과 같은 로더)의 `core_close_at` 기준 `expected_completed_session`(재사용)으로 기준 스냅숏 시각·이번 스냅숏 시각까지 끝난 마지막 미국 거래일. 달력이 두 시각을 덮지 않거나, 끝난 세션이 없거나, 둘이 같으면 HOLD(`UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:CALENDAR_COVERAGE|NO_COMPLETED_SESSION|CALENDAR`, `UNVERIFIED_OUTFLOW_SPAN_MISMATCH:NO_SESSION_BETWEEN:<day>`). `ledger_balance` — 그 날 조회 결과가 정확히 1건·`bridge_status` PASS·pagination complete·USD 행 1개·`fx_entr`/`won_entr` 숫자여야 함. "내역 없음"은 ust21132에 빈 PASS 승격 규칙이 없으므로 실패로 남아 HOLD(`…LEDGER_UNAVAILABLE:<YYYYMMDD>[:USD_ROW|:VALUE]`). 조회기 예외는 `…:READ_FAILED`.
- 2d 구간: I3가 센 체결(`cash_window`)의 `session_date`(recon-dt 뒤 미국 주문일)가 모두 (base_before, base_after] 안. 밖이면 `UNVERIFIED_OUTFLOW_SPAN_MISMATCH:<날짜들>`.
- 2e 일치: L = fx_entr(after) − fx_entr(before) − `trades` − `flows`. `trades`·`flows`는 R 계산에 쓴 것과 같은 값(REUSE): 체결 정산액(수수료 포함; 세션별 ust21610 당일매매 총액과 수수료 범위 안에서 묶인 값)과 ust21100 분류 흐름. L < −1.00 이고 |R − L| ≤ 0.05가 아니면 `UNVERIFIED_OUTFLOW_NOT_MATCHED:<R>:<L>`.
- 2f 금액 상한: −R ≤ 기준 기록 주문가능액. 아니면 `UNVERIFIED_OUTFLOW_ABOVE_BASELINE_CASH:<금액>:<기준>`.
- 2g 원화: won_entr(after) > won_entr(before)이면 `UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:<전>:<후>`. 같거나 줄면 통과.
- 통과 시: I3 `status` PASS, `reasons` [], `unexplained_usd`는 그대로(−82.93 등) 남기고, `unverified_outflow_usd`(양수)와 `unverified_outflow_basis`(base_before/after, fx_entr 두 값, won_entr 두 값, 세션 목록, fill_cash_usd, flow_cash_usd, ledger_residual_usd L, snapshot_residual_usd R)를 붙인다. 결과 warnings에 `UNVERIFIED_EXTERNAL_OUTFLOW:<금액>` 1줄(경고는 HOLD 사유가 아님 — 06:40 점검에 보이도록).
- 직전 실행 비교(compare_check)도 같은 규칙. 같은 날짜 쌍이면 조회를 다시 하지 않는다.
- `cash_flow_evidence.py` 무변경 → 신고는 그대로 `NO_EXTERNAL_FLOW`, `new_external_net_usd` 0.00 → HWM 조정 0.

## 3. 검토 순서
- NO_CHANGE: 지금 그대로면 10/22 출금 −82.93이 I3 HOLD를 영구히 만든다(키움에 출금 기록 조회가 없어 다음 실행에서도 자연 해소 안 됨) → 사장 결정 B2-N대로 변경.
- REMOVE/SIMPLIFY: 없앨 블록 없음. 판정을 순수 함수 `unverified_outflow` 하나에 모으고, 조회·달력은 콜백으로 분리해 기존 호출자(인자 없음)는 동작이 같다.
- REUSE: R의 `trades`·`flows`(같은 체결 정산·분류 흐름), `expected_completed_session`(노출 점검과 같은 "끝난 세션" 정의), 운영 달력 로더(`load_production_snapshot`/`calendar_from_snapshot`), 브리지의 날짜 읽기 틀(`DATED_PARAMETERS`·`request_params` 되돌림), `_read_passed`.
- REPLACE: 없음(I3 판정식·허용 범위·조회 창·정산 규칙 그대로).
- ADD: ust21132 읽기 1개(I1 밖, 후보일 때만), 예외 분기, 결과 필드 2개, 경고 1줄, 문서 2곳, 시험 파일 1개.

## 4. 시험

### 4-1. 새 파일 `test_auto_core_reconcile_outflow.py` — 22개 모두 통과
지시문 항목 ↔ 시험:
- 10-23 재현(R −82.93, ust21132 10/20 82.94·10/22 150.04, 10/21 체결 순현금 +150.03) → I3 PASS, 82.93, basis 전체 값: `Oct23ReplayTests.test_withdrawal_matched_by_the_ledger_passes_as_unverified_outflow`, 날짜 `test_the_ledger_days_are_the_last_closed_us_sessions`; 경고 `UNVERIFIED_EXTERNAL_OUTFLOW:82.93`·신고 `NO_EXTERNAL_FLOW`·hwm_adjustment가 출금 없는 같은 실행과 같음: `OutflowRunTests.test_withdrawal_is_recorded_with_a_warning_and_no_hwm_adjustment`; apply에서 원장 신고 `NO_EXTERNAL_FLOW`·`new_external_net_usd` 0.00: `test_apply_records_the_cash_and_keeps_the_declaration`.
- 유입(R +50, L +50) → HOLD·조회 0: `test_inflow_is_never_admitted`.
- 차이 0.06 → HOLD(0.05는 통과): `test_match_within_five_cents_passes_and_six_cents_holds`, 실행 경로 `test_mismatch_holds_and_writes_nothing`(apply인데 파일 무변경).
- 원장에 유출이 안 보임(L ≥ −1.00) → HOLD: `test_ledger_without_an_outflow_holds`.
- ust21132 조회 실패·"내역 없음"·USD 행 없음·값 불량·조회기 예외·달력 실패 → HOLD, I1 PASS 유지: `test_unreadable_ledger_holds`, `test_failed_or_no_record_ledger_read_holds_outside_i1`, `test_reader_or_calendar_failure_holds`, `test_ledger_days_fail_closed`.
- 체결 session_date 구간 밖(앞·뒤) → HOLD: `test_fill_session_outside_the_ledger_days_holds`.
- 다른 I3 사유(FILL_AMOUNT_UNAVAILABLE, OPEN_ORDERS_PRESENT) 동반 → 예외 미적용·조회 0: `test_another_i3_reason_keeps_the_exception_off`.
- 유출 > 기준 주문가능액 → HOLD: `test_outflow_above_the_baseline_order_available_cash_holds`.
- won_entr 증가 → HOLD(감소는 통과): `test_krw_deposit_rise_holds`(함수·실행 두 곳).
- |R| ≤ 1이면 ust21132·달력 호출 0: `test_cash_within_tolerance_makes_no_ledger_read`.
- 콜백 없는 기존 호출은 recon-dt 재현 그대로 HOLD: `test_without_the_ledger_callback_the_old_hold_stays`; 비교 실행 같은 규칙·조회 1쌍: `test_compare_check_uses_the_same_rule_and_one_read`.
- 브리지: 날짜 한 칸만, 계좌 칸 거부, SAFE_FIELDS 3칸, 빈 PASS 승격 없음, 금지어 없음: `BridgeReadTests` 2개; I1·plan 목록에 없음: `test_the_ledger_read_is_not_an_i1_read`.
- "정책 허용 없음 → HOLD": 해당 없음 — 계좌 브리지는 정책 파일의 허용 목록을 읽지 않는다(5절). 허용은 코드의 `ACCOUNT_APIS` 하나이고, 거기 없는 조작은 `OPERATION_NOT_ALLOWLISTED`로 거절된다.

### 4-2. 기준선·이후 (이름 목록)
- **기준선 이름 목록: Cowork가 별도 측정.** 이 worktree에는 1차 실행의 커밋 안 된 변경이 이미 있어 변경 전 상태를 다시 잴 수 없었다(stash·두 번째 worktree는 쓰지 않음).
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` (변경 후, 2026-10-25 09:1x KST): Ran 527, failures=1, skipped=1.
  - FAIL: test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR') — `CARD_SECTION_CHANGED`, `CARD_NOT_ACCEPTED_IN_WATCHLIST`
- 전체 `-p "test_*.py"` (변경 후, 두 번 실행해 같은 결과): Ran 3317, failures=24, errors=9, skipped=3.
  - ERROR: setUpClass (test_holding_baseline_observation_audit.HoldingBaselineObservationAuditTests)
  - ERROR: test_materialize_kiwoom_session_aware_acceptance_candidate.KiwoomAcceptanceCandidateMaterializationTest.test_05_materialized_candidate_passes_binding_validator
  - ERROR: setUpClass (test_mvll_canonical_volume_lineage.MvllCanonicalVolumeLineageTests)
  - ERROR: test_nbis_v3_shadow_activation.NbisV3ShadowActivationTests.test_price_evidence_preserves_same_session_kiwoom_conflict
  - ERROR: test_nbis_v4_kiwoom_price_authority.NBISV4KiwoomPriceAuthorityTests.test_live_price_artifact_schema_and_semantics
  - ERROR: test_nbis_v4_kiwoom_price_authority.NBISV4KiwoomPriceAuthorityTests.test_valuation_uses_kiwoom_and_no_double_count
  - ERROR: test_portfolio_decision_order_intent.OrderIntentOnlyTests.test_lmt_candidate_classification_is_verified_but_non_actionable
  - ERROR: setUpClass (test_provider_limitation_audit.ProviderLimitationAuditTests)
  - ERROR: test_validate_research_packet.ResearchPacketHardeningTests.test_snapshot_fixture_declares_contract_version
  - FAIL: test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')
  - FAIL: test_evaluate_timing_integration.EvaluateTimingIntegrationTests.test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch
  - FAIL: test_evaluate_timing_integration.EvaluateTimingIntegrationTests.test_technical_validation_failure_does_not_hide_hard_risk
  - FAIL: test_instrument_identity_authority.InstrumentIdentityAuthorityTest.test_15_current_fixed_activation_is_exactly_bound
  - FAIL: test_kiwoom_account_bodies.KiwoomAccountBodiesTests.test_other_bodies_unchanged  ← **이번 변경 때문**
  - FAIL: test_materialize_instrument_identity_artifact.ConfirmationIdentityCandidateTest.test_candidate_support_does_not_replace_active_registry
  - FAIL: test_materialize_kiwoom_session_aware_acceptance_candidate.SyntheticPredecessorDriftTest.test_12_allowed_drift_is_recorded_and_validates
  - FAIL: test_portfolio_decision_dashboard.PortfolioDecisionDashboardTests.test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan
  - FAIL: test_reconcile_broker_state.AccountReturnCodeTests.test_account_routes_are_read_only  ← **이번 변경 때문**
  - FAIL: test_scheduled_prompt_kiwoom_profile.ScheduledPromptRepoTests.test_all_scheduled_prompts_state_profile_and_mode
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_bom_raw_sha_mismatch_rejected
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_crlf_raw_sha_mismatch_rejected
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_duplicate_provider_scope_fails_closed
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_extended_provider_scope_candidate_validates_without_activation
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_guarded_priority_requires_locked_acceptance_manifest
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_historical_and_inactive_candidate_are_not_current_acceptance
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_malformed_provider_scope_fails_closed
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_missing_acceptance_hash_blocks_guarded_transition
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_scope_acceptance_hash_mismatch_blocks_guarded_transition
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='BRK.B')
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='BRKb')
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='COST')
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_unapproved_provider_symbols_fail_closed (ticker='ZZZZ')
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority.PriorityAndScopeTests.test_scope_04_checked_in_provider_scopes_are_complete_and_locked
- 판단(기준선 측정 전 잠정): 31개는 이번 diff가 건드리지 않는 자료를 읽는다 — worktree에 없는 `workspace/outputs/…`·`stock-strategy-system/market_snapshot.example.json`(FileNotFoundError), 수락 manifest 해시(`matches=[]`), 실제 카드 등록부(PLTR), 실제 상태의 SOXL 수량(timing), `docs/claude/scheduled-prompts/pending-cardreuse/diff-v3.2-v3.3.txt`. Cowork 기준선과 이름을 비교해 확정 필요.
- **이번 변경으로 생긴 실패 2개(지시문끼리 충돌 — 해결 안 하고 보고):** 두 기존 시험이 계좌 TR·본문 집합을 정확히 고정한다. 지시문 1("ACCOUNT_APIS에 ust21132 추가")과 "기존 테스트 파일 무변경"·허용 파일 목록(이 두 파일 없음)을 함께 지킬 수 없다. 별도 dict로 우회하면 이 "경로는 읽기 전용" 고정 시험이 새 경로를 못 보게 되므로 우회하지 않았다. 병합 때 필요한 정확한 변경(사장 결정 뒤 Cowork 또는 이 worktree 재지시):
  - `manage-us-stock-strategy/tests/test_reconcile_broker_state.py:178-181` — 주석에 ust21132(cf-b2n) 추가, 기대 집합 마지막 줄을 `"ust21100", "ust21150", "ust21610", "ust21132"})`로.
  - `manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py:26` 다음 줄에 `    "account_deposit_by_date_read": {"base_dt": ""},` 추가(GOLDEN_OTHER_BODIES).
  - 두 줄을 넣으면 두 시험은 통과해야 한다(ACCOUNT_APIS·ACCOUNT_BODIES 값이 그대로 일치). 이 세션에서는 넣지 않았으므로 미확인.

## 5. 정책 파일
- **변경 필요 없음(실행 기준).** 계좌 읽기 브리지(`kiwoom_account_readonly_bridge.py`)는 허용 대상을 코드의 `ACCOUNT_APIS`로만 정한다. `allowed_api_targets`를 읽는 코드는 `kiwoom_candidate_discovery_bridge.py:27`뿐이고(자기 정책 파일), `workspace/policies/kiwoom-broker-readonly-policy.json`은 자동 코어에서 `maximum_age_seconds` 등만 읽힌다. 그 파일의 `allowed_api_targets`(6-13행)에는 T1이 넣은 ust21100·ust21150·ust21610도 없다(같은 선례). `kiwoom-readonly-policy.json`의 `allowed_operations`는 시세 브리지용이다.
- 문서 정합성을 원하면(선택, 사장 승인 시 Cowork): `workspace/policies/kiwoom-broker-readonly-policy.json` → `$.allowed_api_targets`에 `"ust21132:/api/us/acnt"` 추가(같이 맞추려면 `"ust21100:/api/us/acnt"`, `"ust21150:/api/us/acnt"`, `"ust21610:/api/us/acnt"`도). 실행 동작은 바뀌지 않는다.

## 6. 남은 위험 (반드시 포함 항목)
- (a) **증명 아님:** ust21132 `fx_entr`와 스냅숏 주문가능액 `fc_ord_alowa`는 같은 잔액을 다른 TR로 읽은 값이다(진단 문서: 0.01~0.03 차이). 그래서 이 예외는 출금을 "증명"하지 않고, 일시적 오독을 걸러 기록을 허용하는 데까지만이다. 거래내역에 없는 수수료·정정도 같은 모양이면 유출로 기록된다(2f 상한·2g 원화 조건이 범위를 좁힐 뿐).
- (b) **HWM 조정 0:** 신고 블록이 `NO_EXTERNAL_FLOW`로 남아 출금액이 손실로 남는다(지분식 HWM이 그만큼 낮게 보임 — 보수적 방향).
- (c) **유입은 여전히 HOLD:** R > +1.00(입금·이자·환전 유입)은 이 분기에 들어가지 않는다(조회도 안 함).
- (d) **06:15 시점 ust21132 가용성:** 진단상 당일 값은 장 마감 뒤 생성된다(10/23 "내역 없음"). 06:15 KST(EDT 기준 마감 05:00 뒤 1시간 15분)에 직전 미국 거래일(base_after) 값이 있는지는 **첫 실행에서 확인 필요** — 없으면 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:<날짜>`로 HOLD(fail-closed). 본문 틀 `{"base_dt": ""}`도 실측 전이다(틀리면 조회 실패 → HOLD). 첫 실행 결과의 I3 reasons로 바로 보인다.
- (e) **recon-dt2(주문표 주문일 창) 미해결** — 이 작업 범위 밖, 그대로 남음.
- 그 밖: 겨울(EST)에는 마감이 06:00 KST라 06:15 실행과 간격이 15분으로 줄어 (d) 위험이 커진다. 달력이 기준 기록 시각을 덮지 못하면(아주 오래된 기준) HOLD. 기존 시험 2개가 계좌 TR 집합을 고정하고 있어 이번 추가로 실패한다 → 4-2의 두 줄 변경이 병합 전에 필요하다(Judge 판단 대상). 1차 Builder가 끊긴 원인은 확인하지 못했다. 새 시험 파일만 작업 사본 LF(색인은 모든 파일 LF라 커밋 결과는 같음).

## 7. 최소 수정 1회 (Cowork 지시 2026-10-25 09:4x KST, 같은 worktree)
- 허용 파일에 두 시험 파일 추가 → 4-2에 적은 변경만 넣음(다른 줄·다른 시험·기대값 무변경, 작업 사본 CRLF 유지 — `git ls-files --eol` 두 파일 모두 `w/crlf`, 혼합 없음).
  - `manage-us-stock-strategy/tests/test_reconcile_broker_state.py:178` 주석 끝에 `; cf-b2n adds ust21132 (read-only)`, `:181` 기대 집합에 `"ust21132"` 1개 추가.
  - `manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py:27` `"account_deposit_by_date_read": {"base_dt": ""},` 추가 — `kiwoom_account_readonly_bridge.py:51`의 ACCOUNT_BODIES 키·값과 같음.
- 읽기 전용 경로 시험: `test_account_routes_are_read_only`(`test_reconcile_broker_state.py:182-185`)는 `ACCOUNT_APIS.values()` 전체를 돌며 경로 `/api/us/acnt`·금지어 없음·`ordr` 없음을 검사하므로 ust21132(`kiwoom_account_readonly_bridge.py:33`)도 검사 대상에 들어간다(별도 dict 우회 없음).
- 지시문 파일 `docs/claude/cf-b2n-builder-prompt.md`는 이 worktree에 없고 원 저장소 경로 읽기가 이 세션 권한으로 거부돼 "지켜야 할 것" 1~7 원문은 다시 열지 못했다(확인 필요). 이번 지시에 적힌 제한(두 줄 외 변경 금지, 커밋·push 금지)대로만 했다. 실행하지 않은 것: `auto_core.py`, `reconcile_broker_state.py apply`, 키움 호출, git commit/push/stash, 상태·정책·일지 쓰기.
- 다시 돌린 결과 (2026-10-25 KST, 변경 후):
  - `-p "test_reconcile_broker_state.py"`: Ran 56, OK.
  - `-p "test_kiwoom_account_bodies.py"`: Ran 3, OK.
  - `-p "test_auto_core*"`: Ran 527, failures=1, skipped=1 — FAIL: test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR') (4-2와 같음).
  - 전체 `-p "test_*.py"`: Ran 3317, failures=22, errors=9, skipped=3. 4-2 목록(failures=24, errors=9)에서 `test_kiwoom_account_bodies.KiwoomAccountBodiesTests.test_other_bodies_unchanged`와 `test_reconcile_broker_state.AccountReturnCodeTests.test_account_routes_are_read_only` 2개만 빠졌고, 남은 31개 이름은 4-2 목록과 같다:
    - ERROR: setUpClass (test_holding_baseline_observation_audit.HoldingBaselineObservationAuditTests)
    - ERROR: test_materialize_kiwoom_session_aware_acceptance_candidate.KiwoomAcceptanceCandidateMaterializationTest.test_05_materialized_candidate_passes_binding_validator
    - ERROR: setUpClass (test_mvll_canonical_volume_lineage.MvllCanonicalVolumeLineageTests)
    - ERROR: test_nbis_v3_shadow_activation.NbisV3ShadowActivationTests.test_price_evidence_preserves_same_session_kiwoom_conflict
    - ERROR: test_nbis_v4_kiwoom_price_authority.NBISV4KiwoomPriceAuthorityTests.test_live_price_artifact_schema_and_semantics
    - ERROR: test_nbis_v4_kiwoom_price_authority.NBISV4KiwoomPriceAuthorityTests.test_valuation_uses_kiwoom_and_no_double_count
    - ERROR: test_portfolio_decision_order_intent.OrderIntentOnlyTests.test_lmt_candidate_classification_is_verified_but_non_actionable
    - ERROR: setUpClass (test_provider_limitation_audit.ProviderLimitationAuditTests)
    - ERROR: test_validate_research_packet.ResearchPacketHardeningTests.test_snapshot_fixture_declares_contract_version
    - FAIL: test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')
    - FAIL: test_evaluate_timing_integration.EvaluateTimingIntegrationTests.test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch
    - FAIL: test_evaluate_timing_integration.EvaluateTimingIntegrationTests.test_technical_validation_failure_does_not_hide_hard_risk
    - FAIL: test_instrument_identity_authority.InstrumentIdentityAuthorityTest.test_15_current_fixed_activation_is_exactly_bound
    - FAIL: test_materialize_instrument_identity_artifact.ConfirmationIdentityCandidateTest.test_candidate_support_does_not_replace_active_registry
    - FAIL: test_materialize_kiwoom_session_aware_acceptance_candidate.SyntheticPredecessorDriftTest.test_12_allowed_drift_is_recorded_and_validates
    - FAIL: test_portfolio_decision_dashboard.PortfolioDecisionDashboardTests.test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan
    - FAIL: test_scheduled_prompt_kiwoom_profile.ScheduledPromptRepoTests.test_all_scheduled_prompts_state_profile_and_mode
    - FAIL: test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests 13개(test_bom_raw_sha_mismatch_rejected, test_crlf_raw_sha_mismatch_rejected, test_duplicate_provider_scope_fails_closed, test_extended_provider_scope_candidate_validates_without_activation, test_guarded_priority_requires_locked_acceptance_manifest, test_historical_and_inactive_candidate_are_not_current_acceptance, test_malformed_provider_scope_fails_closed, test_missing_acceptance_hash_blocks_guarded_transition, test_scope_acceptance_hash_mismatch_blocks_guarded_transition, test_unapproved_provider_symbols_fail_closed ×4: BRK.B·BRKb·COST·ZZZZ)
    - FAIL: test_v2_6_7_session_aware_kiwoom_priority.PriorityAndScopeTests.test_scope_04_checked_in_provider_scopes_are_complete_and_locked
  - 남은 31개가 변경 전부터 있던 것인지는 4-2대로 Cowork 기준선 이름 목록과 비교해 확정 필요.

## 8. 최소 수정 2회 (Cowork 지시 2026-10-25 10:5x KST, 같은 worktree — Judge PASS 뒤 찾은 결함)
- 결함(지시문의 2026-10-23 실조회·사양 인용): ust21132는 `won_entr`를 본문 최상위에 두고 `result_list` 행에는 없다. 1회차 브리지는 행만 SAFE_FIELDS로 옮겨(`kiwoom_account_readonly_bridge.py` 옛 295~303행) 행의 `won_entr`가 늘 None → `ledger_balance`(`auto_core_reconcile.py:772-774`)가 `…:VALUE`로 HOLD → 실운영에서 B2-N이 통과할 수 없었다(안전 방향). 시험 픽스처가 행 안에 `won_entr`를 넣어 가렸다. 사양 원문은 이 저장소에 없어(검색 결과 없음) 지시문의 실조회 본문만 근거로 했다.
- 바뀐 줄 (작업 사본 기준):
  - `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py:303-308` — 한 페이지 행을 `page_rows`로 만든 뒤, `operation == "account_deposit_by_date_read"`일 때만 각 행의 `won_entr`를 `response.body.get("won_entr")`로 둔다(본문에 없으면 None → 지금처럼 `:VALUE` HOLD; 행 안 값은 쓰지 않음). 다른 조작·다른 필드·SAFE_FIELDS 무변경.
  - `manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py:18` `from types import SimpleNamespace`; `:46` `ledger_row` 주석("브리지가 최상위 won_entr를 붙인 뒤의 행") — 값 무변경; `:338-339` 주석 정정: FILL_AMOUNT_UNAVAILABLE이면 매도가 계산에서 빠져(`auto_core_reconcile.py:383-385`) R = 1246.24 − 1000.00 = +246.24 유입 → 2a(`auto_core_reconcile.py:891`)에서 막혀 조회 0(Judge 지적대로; 1회차 주석 "잔차도 유출"은 틀림).
  - 같은 파일 `BridgeReadTests` 새 시험 2개(`:387-416`): `test_the_top_level_krw_deposit_is_attached_to_each_row`(실제 모양: 최상위 `won_entr "000000000000"`, 행에는 crnc_code·fx_entr·evlt_amt·crnc_rt·chg_entr·chg_evlt_amt·evlt_amt_wght만 → 행에 `won_entr`가 붙고 `ledger_balance`가 fx_entr 150.02·won_entr 0으로 읽음), `test_without_a_top_level_krw_deposit_the_row_value_stays_none`(최상위 없음·행 안 "5" → None, `…:20261022:VALUE`; `account_deposit_read`는 최상위 `won_entr`를 받지 않음). `_read_pages`를 오프라인 가짜 client로 부른다(키움 호출 없음).
- 줄바꿈: 브리지 작업 사본 CRLF 유지(`git ls-files --eol` w/crlf, LF만 끝나는 줄 0), 새 시험 파일은 이전처럼 LF(CRLF 줄 0).
- 시험 (2026-10-25 KST, 변경 후):
  - `-p "test_auto_core_reconcile_outflow.py"`: Ran 24, OK(22 → 24).
  - `-p "test_reconcile_broker_state.py"`: Ran 56, OK. `-p "test_kiwoom_account_bodies.py"`: Ran 3, OK.
  - `-p "test_auto_core*"`: Ran 529, failures=1, skipped=1 — FAIL: test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR') (7절과 같음).
  - 전체 `-p "test_*.py"`: Ran 3319, failures=22, errors=9, skipped=3. 실패·오류 31개 이름은 7절 목록과 같다(ERROR 9: holding_baseline_observation_audit setUpClass, materialize_kiwoom_session_aware_acceptance_candidate test_05, mvll_canonical_volume_lineage setUpClass, nbis_v3_shadow_activation, nbis_v4_kiwoom_price_authority 2개, portfolio_decision_order_intent, provider_limitation_audit setUpClass, validate_research_packet; FAIL 22: auto_core_decide PLTR, evaluate_timing_integration 2개, instrument_identity_authority test_15, materialize_instrument_identity_artifact, materialize_kiwoom_session_aware_acceptance_candidate test_12, portfolio_decision_dashboard, scheduled_prompt_kiwoom_profile, v2_6_7_session_aware_kiwoom_priority 14개). 새로 생긴 실패 0.
- 실행하지 않은 것: `auto_core.py`, `reconcile_broker_state.py apply`, 키움 호출, git commit/push/stash, 상태·정책·일지 쓰기. 바뀐 파일은 허용 3개뿐.
- 남은 위험 추가: 실제 응답의 최상위 `won_entr` 표기("000000000000" 같은 0 채움)가 `_decimal`로 0이 되는 것은 시험으로 확인했지만, 원화 잔액이 있을 때의 실제 표기(부호·소수점)는 실조회 전이다 — 읽지 못하면 `…:VALUE` HOLD(fail-closed). 6절 (d)의 06:15 가용성 확인과 같은 첫 실행에서 보인다.
