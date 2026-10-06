# I0-b (나) 정책만 SIMPLIFY — Builder 보고 (2026-10-06, K3)

- 작업: 관제판 `r-i0b`. 지시문 `docs/claude/i0b-policy-builder-prompt-2026-10-06.md` §2, 설계 `docs/claude/i0b-fill-confirmation-design-2026-10-06.md` §5·§7-2.
- Builder: Claude Code(Opus 5.5 · xhigh), worktree `i0b-policy`, 브랜치 `worktree-i0b-policy`(Cowork 정정, Judge 권고 5), HEAD `dfca99d`. **커밋·푸시 안 함.**
- 사용자 결정(Cowork, 2026-10-06): 결정 1 "예", 결정 2 "(나) 정책만 지금 수정", 결정 3 "MVLL+SOXL, gap·halt 일시 중단 수용".
- 이 세션의 사용자 승인: 정책 편집 계획(키 경로 `holding_timing_rules.positions.MVLL`·`.SOXL` 삭제, 그 밖 바이트 불변, 아래 2-5의 1~3번 처리 방침 포함)에 **"승인"**.
- 하지 않은 것: `portfolio_state.json`·원장·백업 쓰기, `apply`(대조·저널), 키움 접속·키움 도구, 주문 경로, 체결 기록 작성·체결 추론, 고정 27개·`deployment_gate`·`holding_risk_rules`·`SKILL.md`·`assets/locales/ko-KR.json` 수정, 이관 스크립트 밖 스크립트 수정, 줄바꿈 일괄 변환, `.env*`·토큰·계좌번호 읽기.
- 권한 불변: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`.
- **소비처(이 보고를 읽는 곳)**
  - Cowork: Judge 지시문 작성(설계 §7-2 Judge 9항목), 병합 확인(지시문 §3-4), 관제판 `r-i0b` 갱신
  - 독립 Judge(별도 세션): 7절 "Judge가 볼 곳"
  - S7 2차(`p-s7-p2`) Builder 지시문: 완료 기준 "MVLL·SOXL gap·halt watch-only 복구", 6절 2번의 대시보드 테스트 픽스처
  - 키움 재고정 절차(`kiwoom-token-reuse-builder-report-2026-10-06.md` §8의 8·9번): cohort 이관 순서(6절 1번)

## 0. 결론

1. 정책에서 `holding_timing_rules.positions`의 MVLL·SOXL 두 키만 지웠습니다(`"positions": {}`). 그 밖의 키·값·순서는 그대로이고, 파일은 CRLF 그대로입니다(960줄 → 932줄).
2. 실제 r19 상태 + 새 정책으로 `leveraged_state_integrity_errors` = `[]`입니다. 원가 한도(holding_risk_rules)와 등록부 검사는 그대로 돕니다.
3. shadow cohort를 `--reason HOLDING_BASELINE_SEMANTIC_CHANGE`로 이관했습니다(이전 카운터는 모두 0). `shadow_progress.json`은 CRLF 28줄 그대로이고, 바뀐 줄은 3줄뿐입니다.
4. 대상 테스트 모듈은 기준선 대비 **새 실패 0, 해소 7**입니다. 전체 스위트(변경 전/후 사본 비교)도 **새 실패 0, 해소 7**입니다(4-2). `validate_schema_contracts.py`는 PASS입니다.
5. 지시문에 없던 사실 3가지를 정책 편집 승인 전에 사용자에게 알렸습니다(2-5).
   - shadow 지문이 이미 5269cfd로 바뀌어 있었습니다.
   - locale 문구의 방향어가 실제 표 순서와 반대였습니다("아래" → "위"로 씀).
   - 대시보드 타이밍 테스트 묶음이 실제 정책·실제 상태에 묶여 있습니다(이번에는 고치지 않음).

## 1. 기준

| 항목 | 기대 | 실제 |
|---|---|---|
| `stock-strategy-system/alert_policy.json` blob | `b593448f7058e4d7c0a1a1f01293027fd06dcad2` | 같음 |
| `manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json` blob | `8bfe61dbca13d7d23ac43ebdcbda5d36929ac17e` | 같음 |
| `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md` blob | `ddcd3da2d8c9fcf096eaafe9af191153037dad97` | 같음 |
| `manage-us-stock-strategy/tests/test_evaluate_timing_integration.py` blob | `26cf61717b4c13e29a3cb27334f894ec32685bc9` | 같음 |
| `workspace/state/integrated_shadow/shadow_progress.json` blob | `4d7d3d52457b136136169025501530be67a53890` | 같음 |
| worktree 상태 사본(`.worktreeinclude`) | r19, MVLL 278 · NBIS 13 · SOXL 75 | r19(`last_updated_at` 2026-10-06T13:20:28.453816Z), MVLL 278 · NBIS 13 · SOXL 75 |
| 상태 `timing_plan` | — | `policy_version` `2026-08-05-ema-timing-v4`, MVLL anchor id `MVLL-20260731-R3-396`(체결 기록 0), SOXL anchor id `SOXL-20260731-R3-99`(체결 기록 1) |
| `deployment_gate` 대상 6개 정규화 해시 | 정책의 `required_source_*` | 6개 모두 일치(timing_engine `DAC71EA7…`, evaluator `66B52485…`, skill `D24D721C…`, builder `8EF03089…`, yfinance contract `32F36475…`, output locale `5A0F54DE…`) |
| 고정 27개(`kiwoom-acceptance-pin-scope.json`) | 정규화 해시 기록 | 27개 기록(7절 대조에 사용) |

- 기준 해시(변경 전): `alert_policy.json` 원시 `EBC8B8B2…12F2C2`, 정규화 `BA0AB8B9…5E14CE`, CRLF 960줄, bare LF 0, BOM 없음. `shadow_progress.json` 원시 `24148CD7…8DEC01`, CRLF 28줄.

## 2. 사실 확인 (읽기만)

### 2-1. `holding_timing_rules.positions = {}`일 때 동작

| 위치 | 빈 positions에서 | 판정 |
|---|---|---|
| `timing_engine.timing_anchor_errors`(`timing_engine.py:31-108`) | `policy_version` 비교(39-41행)는 반복 **전에** 그대로 돈다. 반복 대상이 없어 anchor 오류는 0 | 예외 없음. 버전 불일치는 여전히 F(T4) |
| `timing_engine.evaluate_holding_timing`(394-411행) | 정책 positions의 종목에 대해서만 호출됨(아래 두 줄) → 호출 0회 | 예외 없음 |
| `evaluate_alerts.py:875-916` 타이밍 반복 | `for symbol in {}` → 타이밍 후보 0 | 예외 없음 |
| `evaluate_alerts.leveraged_state_integrity_errors`(439-583행) | `holding_risk_rules`(원가 한도·등록부·신원) 검사는 타이밍 정책과 무관하게 그대로 | fail-open 아님(T2) |
| `build_holding_fact_pack._timing`(253-266행) | MVLL·SOXL → `NOT_APPLICABLE`/`NO_TIMING_RULE_FOR_TICKER`(지금은 `NOT_EVALUATED`/`ALERT_RESULT_NOT_PROVIDED`) | 예외 없음. 방향 판단 영향 없음(전에도 `NOT_EVALUATED`) |
| `portfolio_decision_dashboard.py:357-430` | 반복 대상 없음 → 타이밍 투영 `{}` | 예외 없음 |
| `shadow_acceptance.semantic_fingerprint`(223-229행) | `holding_timing_rules`를 해시에 넣음 → 지문 변경 | 이관으로 처리(3-3) |
| `validate_mvll_volume_authority.py:49` | `definitions.pullback_reclaim_relative_volume_minimum`만 읽음(유지) | 영향 없음 |
| `validate_technical_snapshot.py:276-288, 479` | `manual_corporate_action_clearance`·`second_quote_crosscheck`만 읽음(유지). CA 영수증은 `canonical_hash(policy)`에 묶이지만 승인 핀 목록이 `[]`이라 무효화될 영수증 없음 | 영향 없음 |
| `validate_research_packet.py:593` | `holding_risk_rules.positions`만 읽음 | 영향 없음 |
| `reconcile_broker_state.alert_engine_check`(61-80행) | 같은 `leveraged_state_integrity_errors` 호출 → 지금 상태로 PASS | 대조 표의 상시 FAIL 해소 |
| `kiwoom_broker_shadow.py:352-354`(고정 파일) | 경고 `TIMING_PLAN_TICKER_CHANGED`는 **상태**의 timing_plan 키로 냄 → 계속 뜸 | 수정 안 함(설계 §5-3) |
| `evaluate_alerts.rules_hash` | `040b2db32617bf53` → `db9fc92a3b1d2306` | 중복 억제 1회 초기화(무해, 설계 §1-8) |

- 메모리 실행(파일 쓰기 없음, 상태 바이트 동일 확인): 현재 정책이면 `['MVLL: holdings 278 do not equal anchor less confirmed tranches 396']`, 빈 positions면 `[]`입니다. Windows에서도 설계 §1-3을 재현했습니다.
- 빈 positions의 대가(결정 3에서 수용): MVLL·SOXL은 anchor 검사 대상에서 빠집니다.
  - 메모리 실행에서 SOXL 보유를 98로 바꿔도 F가 나오지 않습니다. 보유 변경은 대조(propose/apply, 원장, 확인 코드) 경로로만 들어옵니다.
  - 0주가 되거나 등록부 밖 종목이 생기면 `holding_risk_rules` 검사로 여전히 `STATE_MISMATCH`입니다(T2).
  - gap·halt watch-only, SOXL weakness_10ema 감시, SOXL-R50 재무장 잠금도 함께 빠집니다(설계 §11 결정 3).

### 2-2. 실제 정책을 읽고 MVLL·SOXL 슬롯을 단언하던 테스트

| 테스트 | 단언 | 설계 §7-2 목록 |
|---|---|---|
| `test_evaluate_timing_integration.test_active_policy_generates_only_review_candidate` | MVLL-R25 후보 99주 | 있음 |
| `test_evaluate_timing_integration.test_unreconciled_holding_change_fails_closed` | SOXL 98 → anchor 오류로 F(정책 SOXL 슬롯에 기댐) | 있음(모듈) |
| `test_v2_5_leveraged_confirmation.test_v25_lv_07_existing_rules_unchanged` | 슬롯 수량 [24,24,24,27]·[99,99,99,99] | 있음 |
| `test_v2_6_12_holding_valuation_shadow.InvariantTests.test_inv_06_timing_quantities_unchanged` | 같음 | 있음 |
| `test_v2_6_3_free_web_new_buy.test_inv_06_timing_quantities_unchanged` | 같음 | 있음 |
| `test_v2_6_integration.test_int_12_hard_risk_and_quantities_unchanged` | SOXL 첫 슬롯 24 | 있음 |
| `test_portfolio_exposure.test_first_stage_keeps_the_old_controls` | SOXL·MVLL 슬롯 존재, SOXL watch-only에 weakness_10ema | **없음(추가)** |
| `test_portfolio_decision_dashboard`의 `ManualStep2TimingTests`와 이를 쓰는 7개 클래스 | `EvaluateTimingIntegrationTests.setUp`의 실제 정책·실제 상태로 `VERIFIED_REDUCTION_REVIEW`(MVLL 슬롯), 한 곳은 "Broker=396" | 있음(모듈). 이번에 고치지 않음(2-5의 3번) |

- 엔진의 슬롯 동작은 `test_timing_engine`의 합성 정책 픽스처(56행)가 계속 덮습니다. 대상은 anchor 등식, 첫 슬롯 수량, 체결 기록 요구, 재무장, weakness_10ema watch-only, gap·halt watch-only, 원가 한도 우선입니다. 8건 모두 통과합니다.

### 2-3. 기준선(변경 전) 대상 테스트

`python -m unittest discover -s manage-us-stock-strategy/tests -p "<모듈>.py"`, 모듈별 실행.

| 모듈 | 실행 | 실패+오류 | 원인 |
|---|---|---|---|
| test_evaluate_timing_integration | 10 | 6(실패 5 + 오류 1) | r19(MVLL anchor) — 설계 §1-3 예상과 같음 |
| test_timing_engine | 8 | 0 | |
| test_v2_5_leveraged_confirmation | 8 | 0 | |
| test_v2_6_integration | 15 | 0 | |
| test_v2_6_shadow_acceptance | 44 | 0 | |
| test_build_holding_fact_pack | 36 | 0 | |
| test_reconcile_broker_state | 56 | 0 | |
| test_kiwoom_broker_shadow | 24 | 0 | |
| test_portfolio_decision_dashboard | 306 | 155 | 150 환경(`IntegratedAuthorityLoadError: INTEGRITY_FAILURE`, worktree), 4 r19(`ManualStep2TimingTests`), 1 `test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan`(원인 미분석, 변경 뒤 같은 메시지) |
| test_mvll_volume_authority | 3 | 0 | |
| test_v2_6_12_holding_valuation_shadow | 88 | 0 | |
| test_v2_6_3_free_web_new_buy | 70 | 0 | |
| test_v2_6_7_session_aware_kiwoom_priority | 42 | 12 | 11 환경(acceptance manifest 없음), 1 shadow 지문(5269cfd, 2-5의 1번) |
| test_state_write_boundary | 3 | 0 | |
| test_manual_portfolio_analysis | 115 | 3 | 환경(`INTEGRITY_FAILURE`) |
| test_portfolio_exposure | 57 | 0 | |

### 2-4. shadow 카운터

- `shadow_progress.json`(이관 전, 원시 `24148CD7…`)의 정수 카운터 8개(`observed_attempts`, `valid_shadow_sessions`, `valid_finalized_sessions`, `valid_paired_operational_days`, `preopen_success_count`, `postclose_success_count`, `excluded_attempts`, `independent_price_covered_sessions`)는 모두 0입니다.
- `baseline_overlay_sessions`(NBIS·MVLL·SOXL)도 모두 0입니다.
- 목록 5개(`paired_operational_days`, `pending_preopen_sessions`, `critical_violations`, `counted_sessions`, `missing_expected_sessions`)는 모두 비어 있고, `last_attempt_hash`는 null입니다.
- 이관 직전에 원시 해시가 같음을 다시 확인했습니다.

### 2-5. 지시문에 없던 사실 (정책 편집 승인 전에 사용자에게 알림)

1. **shadow 지문은 이미 바뀌어 있었습니다.**
   - 기록된 지문은 `4f11526e…`인데, 변경 전 worktree에서 다시 계산하면 `3cdbd274…`였습니다.
   - R9 커밋 `706c940` 기준으로 입력을 비교하면 다른 곳은 `workspace/policies/kiwoom-readonly-policy.json` 하나뿐입니다(5269cfd에서 `token_profile_alias` 키 추가). 정책 의미·레지스트리·경로 의미는 같았습니다.
   - 이 사실은 `kiwoom-token-reuse-builder-report-2026-10-06.md` §0-3에 이미 적혀 있고, 이관은 재고정 8번 뒤(§8-9)로 미뤄져 있었습니다.
   - 따라서 이번 보관 파일 하나에 두 변화(별칭 키, 타이밍 슬롯 삭제)가 함께 들어갑니다.
   - 사유 enum 4개 가운데 이번 변경에 가장 가까운 값은 `HOLDING_BASELINE_SEMANTIC_CHANGE`입니다(보유 종목의 anchor 기준선 의미가 정책에서 빠짐). 이전에 이 값을 쓴 곳은 v2.6.12 보유 research baseline 변경(`integrated-shadow-8c22…`)이고, 별칭 키 변화는 이 값으로 설명되지 않습니다.
   - 그래도 지시대로 이 값으로 이관했습니다. 사유 값으로 판단하는 코드는 없습니다(R9 보고 §5-1).
2. **locale 문구 방향.** `render_proposal`(`reconcile_broker_state.py:177-187`)은 '적용 후 알림 엔진 검사' 줄을 경고 줄보다 **먼저(위)** 찍습니다. 기존 `warning_POST_APPLY_ALERT_ENGINE_CHECK_FAILED`도 "(위 검사 줄 참조)"라고 씁니다. 그래서 지시문 문구의 "아래"를 "위"로 바꿔 썼습니다.
3. **대시보드 타이밍 테스트 묶음은 실제 정책·실제 상태에 묶여 있습니다.**
   - `ManualStep2TimingTests.setUp`이 `EvaluateTimingIntegrationTests.setUp`(실제 `alert_policy.json` + 실제 `portfolio_state.json`)을 그대로 씁니다. `TechnicalTimingConsumerAlignmentTests`, `ManualKiwoomOnlyTimingTests`, `ManualTimingEvidenceContractTests`, `ManualCorporateActionClearanceTests` 등이 다시 이 클래스를 씁니다.
   - 그래서 r19부터는 상태 원인으로, 이번 변경부터는 정책 원인으로도 통과할 수 없습니다.
   - worktree에서 실행되는 것은 `ManualStep2TimingTests` 12건뿐이고(나머지는 환경 원인), 그중 4건이 실패합니다. 변경 전후 메시지는 같습니다.
   - 진단(파일 수정 없음): 메모리에서 `with_timing_positions(policy, "MVLL", "SOXL")` + MVLL 보유 396으로 setUp을 패치하자 12건 모두 통과했습니다.
   - 이번에는 고치지 않았습니다(6절 2번 후속 제안).
4. 같은 모듈의 `test_unreconciled_holding_change_fails_closed`는 정책 SOXL 슬롯의 anchor 검사에 기대고 있었습니다. 새 정책에서는 통과할 수 없어 합성 SOXL 블록을 쓰도록 바꿨습니다(3-5).
5. worktree의 `alert_policy.json`은 전부 CRLF(960줄)였습니다. 원본 폴더 파일은 CRLF·LF가 섞여 있을 수 있습니다(설계 §6-7, 확인 필요 6절 4번).

## 3. 변경

### 3-1. 정책 `stock-strategy-system/alert_policy.json`

- 방법: 바이트 블록 하나만 잘라 냈습니다(재직렬화 없음).
  - 497~525행 `"positions": { "SOXL": {…}, "MVLL": {…} },`(29줄, 1,866바이트)를 `    "positions": {},` 1줄로 바꿨습니다.
  - 블록 앞뒤 바이트가 같음을 확인했습니다.
- 확인:

| 항목 | 결과 |
|---|---|
| JSON 파싱 | OK |
| 키 경로 diff | 삭제된 말단 경로 59개가 모두 `holding_timing_rules.positions.MVLL.*`·`.SOXL.*` 아래. 추가는 `holding_timing_rules.positions`(빈 객체) 1개. 값이 바뀐 말단 0 |
| 최상위·`holding_timing_rules` 키 순서 | 같음 |
| `deployment_gate`, `holding_risk_rules`, `holding_timing_rules`의 나머지 키(`status`, `policy_version`, `formula_version`, `timing_feature_version`, `definitions`, `risk_overlay_rules`, `weakness_rearm`, `watch_confirmations` 등) | 같음 |
| 원시 sha256 | `EBC8B8B28BF2620629ED8A8D2259761921D006060321162C9F0D85A5DC12F2C2` → `860FB038182ED0020FE9C19EB0ACACF1ED3645C49CF36CDEE1C14771BE279557` |
| 정규화 sha256(UTF-8, LF) | `BA0AB8B99146565DEF60AEADE570EA06819173730AE2E7BD69369930CF5E14CE` → `3F4E1BB568933F0E0AA06E5E9BF08FD02A17898AD0C0BA30AB51567A6D8E234C` |
| `canonical_hash` | `063f98288514b7ec…` → `d3f04b10a8d5a379805162dd30d9f16d8c91d6a24ed8969770fb98f7160dd82c` |
| 줄 수 / CRLF / bare LF / BOM | 960/960/0/없음 → 932/932/0/없음 |

- `policy_version`(`2026-08-05-ema-timing-v4`)은 그대로 뒀습니다. 상태 `timing_plan.policy_version`과 달라지면 그 자체로 F이기 때문입니다(`timing_engine.py:39-41`, T4).
- `watch_confirmations.SOXL`(watchlist 기술 확인용)은 그대로입니다. 지시문 범위 밖입니다.

### 3-2. 이관 스크립트 `manage-us-stock-strategy/scripts/migrate_integrated_shadow_cohort.py`(K2)

- `DEFAULT_REASON = "GLOBAL_AUTHORITY_VOLUME_AND_DUAL_RUN_SEMANTICS_CHANGE"`(기존 고정값 그대로)를 정의했습니다.
- `allowed_reasons()`는 `schemas/superseded-shadow-cohort.schema.json`의 `reason` enum을 읽습니다.
- `migrate(..., reason=DEFAULT_REASON)`은 enum 밖 값을 **쓰기 전에** `ValueError("UNSUPPORTED_SUPERSEDED_COHORT_REASON")`로 거부합니다.
- CLI는 `--reason`(기본값 그대로, `choices=allowed_reasons()`)입니다.
- 그 밖 동작은 그대로입니다. CRLF 81줄 → 94줄. 새 enum 값은 추가하지 않았습니다.
- 새 테스트 `manage-us-stock-strategy/tests/test_migrate_integrated_shadow_cohort.py`(3건, 임시 폴더, 지문 함수 패치):
  - `test_default_reason_is_unchanged`: CLI 기본값 → 보관 사유가 기존 값이고 스키마 PASS
  - `test_explicit_reason_is_recorded`: `--reason HOLDING_BASELINE_SEMANTIC_CHANGE` → 기록되고 스키마 PASS, 새 진행 파일 카운터 0
  - `test_reason_outside_schema_enum_is_rejected_before_any_write`: 함수는 `ValueError`, CLI는 종료 코드 2. 진행 파일 바이트는 같고 `cohorts/`는 생기지 않음
- `test_state_write_boundary`·`test_manual_portfolio_analysis`의 분석 경로 import 금지 목록에 이 스크립트가 그대로 있고, 두 모듈 모두 기준선과 같은 결과입니다.

### 3-3. 이관 실행

- 명령: `python manage-us-stock-strategy/scripts/migrate_integrated_shadow_cohort.py --repo-root <worktree> --reason HOLDING_BASELINE_SEMANTIC_CHANGE`
- 출력: `COHORT_SUPERSEDED_AND_ZERO_INITIALIZED`, `integrated-shadow-4f11526e20929f11` → `integrated-shadow-a0d3e69e9bc23a1b`, 지문 `a0d3e69e9bc23a1b3205171a32f2a82880ee6ae728f39c0f7bdbf16dd6652c32`

| 확인 | 결과 |
|---|---|
| `shadow_progress.json` 줄 수 | CRLF 28줄 → CRLF 28줄 |
| 바뀐 줄 | 3행 `cohort_id`, 4행 `semantic_fingerprint`, 5행 `started_at`(`2026-10-06T14:26:56.819038+00:00`)뿐 |
| 원시 sha256 | `24148CD7…8DEC01` → `99108823F88B5E4A9234E83F5DF75E54A6932847A9E7873E3863381455756F21` |
| 새 보관 파일 | `workspace/state/integrated_shadow/cohorts/integrated-shadow-4f11526e20929f11/superseded_progress.json`, CRLF 36줄, 원시 `73412D106EA5F35563D3148DBA8A4BEA1E1307924B69324B19CFC1EBC36118A6` |
| 보관 파일 스키마(`superseded-shadow-cohort.schema.json`) | PASS(오류 0), `reason=HOLDING_BASELINE_SEMANTIC_CHANGE`, `order_authority=false`, `prior_progress` = 이관 전 파일과 같음 |
| 새 진행 파일 스키마(`shadow-progress-state.schema.json`) | PASS(오류 0) |
| 다시 계산한 지문 = 저장 지문 | 예 |

### 3-4. K0 문구

- 두 파일 모두 고정 27개 목록, `deployment_gate` 6개(`output_locale`는 `assets/locales/ko-KR.json`), 설치 스킬 해시 검사(`validate_skill_deployment.ARTIFACTS`)에 없습니다. `kiwoom-acceptance-pin-scope.json`과 `validate_skill_deployment.py`로 확인했습니다.
- `assets/locales/reconcile-broker-state-ko-KR.json`: `warning_TIMING_PLAN_TICKER_CHANGED` 값만 "주의: timing_plan 종목의 수량이 바뀝니다. 위 '적용 후 알림 엔진 검사' 결과를 확인하세요."로 바꿨습니다(2-5의 2번, "아래" → "위").
  - 키 집합은 같고, 바뀐 키는 1개입니다. CRLF 53줄 그대로이고, 원시 `4CB6899C…`, 정규화 `38722350…`입니다.
- `references/broker-snapshot-reconciliation.md` 절차 4: "apply (the alert engine may stop … I0-b) or hold (do I0-b first)." 부분만 아래로 바꿨습니다. 나머지 절차는 그대로입니다. CRLF 183 → 185줄.
  > apply or hold. Timing slots were removed from the approved policy (`holding_timing_rules.positions` is empty since I0-b, 2026-10-06), so the check should not report timing-anchor errors. If the post-apply check fails, explain its errors to the user before any confirmation; if the cause is unknown, do not apply.
- `test_reconcile_broker_state.test_cowork_procedure_documents_the_confirmation_rules`(문구 조각 확인)는 통과합니다.

### 3-5. 테스트 갱신

| 파일 | 바꾼 것 |
|---|---|
| `test_evaluate_timing_integration.py` | 테스트 전용 상수 `RETIRED_TIMING_POSITIONS`(삭제한 정책 블록을 그대로 옮긴 것. 정책 백업과 `==` 확인)와 `with_timing_positions(policy, *symbols)`를 추가했습니다. 아래 줄 참고 |
| ↳ `test_active_policy_generates_only_review_candidate` | MVLL-R25 후보 대신 "`STATE_MISMATCH` 아님, 타이밍 후보(`holding_timing_review`/`_watch`) 없음, 모든 후보·watchlist 수량 null"을 단언합니다. watch 상태 단언은 그대로. 이름은 지시문 추적을 위해 유지 |
| ↳ `test_unreconciled_holding_change_fails_closed` | 합성 SOXL 블록 정책(`with_timing_positions(self.policy, "SOXL")`)으로 같은 단언(SOXL 98 → F, anchor 경고) |
| ↳ 새 T1 `test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch` | 합성 MVLL·SOXL 블록. 메모리 MVLL 396이면 B 후보가 MVLL-R25·99주·actionable=false 하나뿐이고, 395면 `STATE_MISMATCH`/F와 "MVLL: holdings 395 do not equal anchor less confirmed tranches 396" |
| ↳ 새 T2 `test_i0b_t2_holding_risk_checks_still_run_without_timing_positions` | 실제 정책 positions `{}`. NBIS 10% 경계 → D(경계 90.0, breached). 원가 한도 후보 종목 = `holding_risk_rules.positions` 3종목. 등록부 밖 종목 `ZZZT` → `STATE_MISMATCH`/F와 "neither a holding-risk rule" |
| ↳ 새 T3 `test_i0b_t3_real_policy_and_state_pass_integrity_without_state_write` | 실제 정책 + 실제(worktree) 상태 파일 → 무결성 오류 `[]`, 실행 전후 상태 파일 바이트가 같음 |
| ↳ 새 T4 `test_i0b_t4_timing_plan_policy_version_mismatch_still_fails` | 상태 사본의 `timing_plan.policy_version`을 바꾸면 `STATE_MISMATCH`/F와 버전 불일치 경고 |
| `test_v2_5_leveraged_confirmation.py` `test_v25_lv_07` | 슬롯 수량 단언 → `positions == {}`(원가 한도 단언 유지) |
| `test_v2_6_12_holding_valuation_shadow.py` `test_inv_06` | 같음(이름 유지) |
| `test_v2_6_3_free_web_new_buy.py` `test_inv_06` | 같음(이름 유지) |
| `test_v2_6_integration.py` `test_int_12` | SOXL 첫 슬롯 24 → `positions == {}` |
| `test_portfolio_exposure.py` `test_first_stage_keeps_the_old_controls` | 슬롯·weakness_10ema 단언 → `positions == {}`(설계 §7-2 목록 밖, 2-2) |

- 모든 테스트 파일은 CRLF 그대로입니다. 새 파일 1개는 이웃 파일처럼 CRLF로 썼습니다.
- 옛 정책 대조(Judge 항목 3, 임시 폴더에서 `STOCK_STRATEGY_SYSTEM_ROOT` 지정, 실제 파일은 그대로):

| 새 테스트 | 옛 정책 + r19 상태 사본 | 옛 정책 + MVLL 396 상태 사본(임시) |
|---|---|---|
| T1 | 통과 | 통과 |
| T2 | 실패: 첫 줄 전제 `positions == {}`(옛 정책은 슬롯이 있음) | 같음(전제 줄에서만 실패) |
| T3 | 실패: `['MVLL: holdings 278 …396']`(이번 변경이 고친 바로 그 오류) | 통과 |
| T4 | 통과 | 통과 |

- T2의 NBIS 경계 부분은 기존 `test_nbis_exact_ten_percent_boundary_generates_hard_risk_review`와 같은 계산입니다. 이 테스트는 r18 상태 + 옛 정책에서 통과했습니다(설계 §1-3).

## 4. 테스트

### 4-1. 대상 모듈 (변경 후, 기준선 대비)

| 모듈 | 실행 전/후 | 실패+오류 전/후 | 새 실패 | 해소 |
|---|---|---|---|---|
| test_evaluate_timing_integration | 10/14 | 6/0 | 0 | 6 |
| test_timing_engine | 8/8 | 0/0 | 0 | 0 |
| test_v2_5_leveraged_confirmation | 8/8 | 0/0 | 0 | 0 |
| test_v2_6_integration | 15/15 | 0/0 | 0 | 0 |
| test_v2_6_shadow_acceptance | 44/44 | 0/0 | 0 | 0 |
| test_build_holding_fact_pack | 36/36 | 0/0 | 0 | 0 |
| test_reconcile_broker_state | 56/56 | 0/0 | 0 | 0 |
| test_kiwoom_broker_shadow | 24/24 | 0/0 | 0 | 0 |
| test_portfolio_decision_dashboard | 306/306 | 155/155(같은 id, 같은 메시지) | 0 | 0 |
| test_mvll_volume_authority | 3/3 | 0/0 | 0 | 0 |
| test_v2_6_12_holding_valuation_shadow | 88/88 | 0/0 | 0 | 0 |
| test_v2_6_3_free_web_new_buy | 70/70 | 0/0 | 0 | 0 |
| test_v2_6_7_session_aware_kiwoom_priority | 42/42 | 12/11 | 0 | 1(`test_provider_authority_change_starts_zero_count_cohort`, 이관으로 지문 일치) |
| test_state_write_boundary(고정, 수정 안 함) | 3/3 | 0/0 | 0 | 0 |
| test_manual_portfolio_analysis | 115/115 | 3/3 | 0 | 0 |
| test_portfolio_exposure | 57/57 | 0/0 | 0 | 0 |
| test_migrate_integrated_shadow_cohort(새) | —/3 | —/0 | 0 | — |

- 해소된 `test_evaluate_timing_integration` 6건: `test_active_policy_generates_only_review_candidate`, `test_exact_one_share_nbil_de_minimis_exception_does_not_cause_mismatch`, `test_explicitly_confirmed_nbil_exit_can_leave_zero_without_inferred_fill`, `test_technical_validation_failure_does_not_hide_hard_risk`, `test_nbis_exact_ten_percent_boundary_generates_hard_risk_review`, `test_missing_held_ohlcv_provenance_fails_closed`.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → `{"status": "PASS", "errors": []}`.

### 4-2. 전체 스위트 (서브에이전트 1회)

- 방법:
  - 스크래치패드에 `.git`을 뺀 worktree 사본 2개를 만들었습니다.
  - `fs_before`는 바꾼 파일 11개를 HEAD blob(CRLF)으로 되돌리고 새 파일 2개를 지운 사본입니다. `alert_policy.json`·`shadow_progress.json`은 저장해 둔 변경 전 바이트와 같음을 확인했습니다. `fs_after`는 변경 후 사본입니다.
  - 각 사본 루트에서 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"`를 돌렸습니다.
  - 실제 worktree에서는 전체 스위트를 돌리지 않았습니다(테스트가 쓰는 파일로 worktree가 더러워지지 않게).

| 사본 | 실행 | 실패 | 오류 | 건너뜀 |
|---|---|---|---|---|
| fs_before | 2485 | 36 | 285 | 4 |
| fs_after | 2492(+7 = 새 T1~T4 + 이관 테스트 3) | 30 | 284 | 4 |

- **새 실패: 0.**
- 해소 7: 4-1의 `test_evaluate_timing_integration` 6건 + `test_v2_6_7…test_provider_authority_change_starts_zero_count_cohort`.
- 공통 실패 314(두 사본에서 같은 id). 주요 묶음:
  - `IntegratedAuthorityLoadError: INTEGRITY_FAILURE` 273
  - acceptance manifest 없음 14
  - `False is not true` 9(카드·저널 gitignore 검사 등)
  - 사본에 없는 산출물 `FileNotFoundError` 7
  - `NOT_VERIFIED != VERIFIED_REDUCTION_REVIEW` 2(대시보드, 2-5의 3번)
  - `.git` 없음(`git ls-files` 128) 2
  - 그 밖 1건씩
- 결과 파일(스크래치패드, 저장소 밖): `full_compare.json`, `full_before.txt`, `full_after.txt`.

## 5. 경계

| 확인 | 결과 |
|---|---|
| `git diff --stat HEAD` | 11개 파일 수정: `alert_policy.json`, `shadow_progress.json`, 이관 스크립트, locale 1, reference 1, 테스트 6(`test_evaluate_timing_integration`, `test_portfolio_exposure`, `test_v2_5_leveraged_confirmation`, `test_v2_6_12_holding_valuation_shadow`, `test_v2_6_3_free_web_new_buy`, `test_v2_6_integration`). 새 파일 3: 보관 파일 1, 새 테스트 1, 이 보고서 |
| 지시문 예상과 차이 | 테스트 1개(`test_portfolio_exposure`)가 예상 목록 밖(2-2). 그 밖은 예상과 같음 |
| 고정 27개 정규화 해시 | 27개 모두 0번 기록과 같음(diff 0) |
| `deployment_gate` 대상 6개 정규화 해시 | 0번과 같고 required 값과도 일치 |
| `portfolio_state.json`(worktree 사본) | 원시 `C62CA19F…` 전후 같음(바이트 동일) |
| `alert_runtime_state.json`(worktree 사본) | 원시 `5A4E611F…` 전후 같음 |
| `reconciliation_ledger.jsonl`, `backups/` | worktree에 없음(원본 폴더에만 있음). 접근·수정 안 함 |
| `holding_risk_rules` | 키·값 diff 0 |
| 권한 3필드 | 바꾼 파일에 `quantity_authority`·`execution_quantity` 추가 줄 0. `order_authority` 추가 줄은 `false` 3곳(보관 파일, 새 진행 파일, 새 테스트 단언). pin scope 값 `false`/`none`/`null` 그대로 |
| 새 코드에서 `confirmed_trades` | 추가 줄 0 |
| 새 코드에서 `confirmed_tranche_fills` | 추가 줄 0 |
| 새 코드에서 `timing_plan` | 추가 줄 3, 쓰기 0. ① locale 문구 ② T4 테스트 이름 ③ T4의 `state["timing_plan"]["policy_version"] = "SYNTHETIC-STALE-TIMING-PLAN"`(`copy.deepcopy`한 메모리 사본, 파일 쓰기 없음) |

- grep 방법: `git diff HEAD -U0`의 `+` 줄과 새 파일 전체에서 토큰을 찾았습니다(스크래치 스크립트 `boundary.py`).

## 6. 확인 필요 · 남는 점

1. **cohort 이관 순서(키움 재고정과 겹침).**
   - 이 브랜치는 `shadow_progress.json`을 바꿉니다. 재고정 §8의 8번(포인터 17곳)이 의미 입력을 또 바꾸므로 9번 이관은 그대로 필요합니다. 이번 이관이 그것을 대신하지 않습니다.
   - 권장 순서: 이 브랜치를 먼저 병합하고, 재고정 9번에서 카운터 0을 확인한 뒤 `--reason SESSION_AWARE_KIWOOM_PROVIDER_AUTHORITY_CHANGE`로 이관합니다(이번에 추가한 인자).
   - 재고정 이관이 원본 폴더에서 먼저 일어나면 `shadow_progress.json` 병합이 충돌합니다. 그때는 이 브랜치의 이관을 버리고 지문을 다시 계산해 한 번 더 이관해야 합니다(카운터 0 확인 필요).
2. **대시보드 타이밍 테스트 픽스처(후속 K2 제안).**
   - `ManualStep2TimingTests.setUp`이 실제 정책·상태 대신 합성 타이밍 블록(`test_evaluate_timing_integration.with_timing_positions`)과 anchor에 맞춘 메모리 보유를 쓰도록 바꾸는 작업입니다. 위의 7개 클래스 약 150건이 다시 회귀를 잡게 됩니다.
   - 이번 진단(메모리 패치)에서 worktree에서 실행 가능한 12건은 모두 통과했습니다.
   - 나머지 클래스는 worktree 환경 원인(`INTEGRITY_FAILURE`)으로 확인하지 못했습니다. 원본 폴더 또는 바이트 사본에서 확인해야 합니다.
   - "Broker=396" 단언(`test_stale_internal_timing_quantity_does_not_override_valid_broker_and_anchor`)도 함께 봐야 합니다.
3. **원본 폴더 대시보드 테스트 현황.** 원본 폴더에서는 위 묶음이 r19부터 상태 원인으로 실패하고 있을 것으로 봅니다. 이 세션은 원본 폴더에서 테스트를 돌리지 않았습니다.
4. **병합 뒤 줄바꿈.**
   - worktree 파일은 전부 CRLF입니다. 원본 폴더의 `alert_policy.json`은 CRLF·LF가 섞여 있을 수 있습니다(설계 §6-7). 병합 뒤 원시 해시는 원본 폴더 기준으로 다시 재야 합니다.
   - 정규화 해시는 `3F4E1BB5…`로 같아야 합니다.
   - 원시 해시를 쓰는 곳은 예약 clone 배포 manifest(재개 때 재생성)와 기록용뿐입니다.
5. **원본 폴더의 shadow 카운터.** 이 세션은 worktree 사본(HEAD)만 확인했습니다. 병합 전에 원본 폴더 `shadow_progress.json`이 HEAD와 같고 카운터가 0인지 Cowork가 확인해야 합니다.
6. **보관 사유의 정확도.** 2-5의 1번대로, 보관 파일 `reason`은 이번 변경 쪽만 설명합니다. 지문 차이에 별칭 키 추가(5269cfd)가 함께 들어 있다는 사실은 이 보고서에만 남아 있습니다.
7. **이름과 내용이 어긋난 테스트 3개.** `test_active_policy_generates_only_review_candidate`, `test_inv_06_timing_quantities_unchanged`(2곳)의 이름은 추적을 위해 그대로 두었고, 단언은 "타이밍 positions 없음"으로 바뀌었습니다. 이름 정리는 S7 2차에서 하면 됩니다.
8. **`test_portfolio_decision_dashboard`의 실패 1건** `test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan`("False is not true")은 원인을 분석하지 않았습니다. 변경 전후 같은 메시지라 이번 변경과는 무관합니다.
9. **잃는 것(결정 3, 재확인).**
   - MVLL·SOXL gap·halt watch-only, SOXL weakness_10ema 감시, SOXL-R50 재무장 잠금이 S7 2차까지 빠집니다.
   - MVLL·SOXL 보유 변경에 대한 anchor 2차 검사도 빠집니다.
   - 예약 자동화를 재개하기 전에 S7 2차에서 gap·halt를 복구해야 합니다(관제판 `p-s7-p2` 완료 기준).
10. **등록부 트리거는 그대로입니다.** MVLL 전량 매도나 새 종목 매수 때는 `holding_risk_rules` 검사로 다시 `STATE_MISMATCH`가 됩니다(설계 §1-7, §4-B). 그 순간 T3도 실패합니다. 이것은 의도한 경보입니다.

## 7. Judge가 볼 곳 (설계 §7-2의 9항목)

| # | 항목 | 볼 곳 · 재현 |
|---|---|---|
| 1 | 정책에서 바뀐 키가 승인된 2개뿐, 그 밖 바이트 같음 | `git diff HEAD -- stock-strategy-system/alert_policy.json`(29줄 삭제, 1줄 추가). 3-1 표. 원시·정규화 해시 재계산 |
| 2 | 상태 쓰기·체결 기록·체결 추론 없음 | 5절. `git diff --stat HEAD`에 `portfolio_state.json` 없음. 추가 줄 grep(`confirmed_trades`·`confirmed_tranche_fills` 0) |
| 3 | validator 약화 없음 | `git diff HEAD -- manage-us-stock-strategy/scripts/`에 `timing_engine.py`·`evaluate_alerts.py` 없음. T1·T4는 옛 정책에서도 통과, T2는 전제 줄에서만 실패(3-5 표) |
| 4 | 고정 27개·스크립트·`deployment_gate` diff 0 | 5절. 바뀐 스크립트는 이관 스크립트 1개뿐(고정 27개 밖) |
| 5 | 실제 상태로 무결성 PASS | `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_evaluate_timing_integration.py"`(14건 OK, T3 포함) |
| 6 | 소비처 영향 | 2-1 표: fact pack `NOT_APPLICABLE`, 대시보드 투영 `{}`, 대조 사전 검사가 같은 함수로 PASS |
| 7 | 이관 전 카운터 0 | 2-4, 3-3 |
| 8 | D5와의 차이(gap·halt 일시 중단)가 사용자 결정으로 기록됨, S7 2차 복구 | 설계 §11 결정 3, 이 보고서 6절 9번. S7 2차 지시문 반영은 Cowork 몫 |
| 9 | 권한 3필드 불변 | 5절 |

- 추가로 볼 것: 2-5의 1번(지문에 5269cfd 별칭 키 포함, 보관 사유), 2-5의 2번("위"로 쓴 문구), 6절 1번(병합 순서), 6절 2번(대시보드 픽스처).

Builder 완료, worktree i0b-policy, 새 실패 수 0
