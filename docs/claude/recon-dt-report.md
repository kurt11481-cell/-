---
id: recon-dt-report
title: "recon-dt Builder 보고 — ust21150 ord_dt = 미국(ET) 주문일 (커밋 1 구현 · 커밋 2 보류)"
date: 2026-10-23
class: "권한·한도(K3) 수동 경로 Builder (worktree recon-dt). Judge 전 상태, 커밋하지 않음"
source: "docs/claude/recon-dt-builder-prompt.md(이 세션에 붙여 넣은 원문), 사장 \"결정 recon-dt: a\"(2026-10-23 08:45 KST)"
---

# recon-dt Builder 보고

## 결론 (먼저)
- **커밋 1(대조 체결 시각) 구현 완료.** 새 테스트 11건 통과. 10-21 ET 주문일 7건 재현, 10-23 통합 재생에서 I2 PASS · FILL_AMOUNT_UNAVAILABLE 사라짐 · 현금 잔차(출금 −82.93)로 HOLD 유지.
- **기준선 대비 새 실패 1건 — 기존 테스트가 옛 가정을 기대값으로 고정.** `test_auto_core.DailyTests.test_day_held_only_for_an_unseen_settlement_keeps_the_streak`(tests/test_auto_core.py:1409~1436)는 미국 10/14 시간외 체결(KST 10/15 07:07)을 `ord_dt "20261015"`(KST 날짜)로 넣어 둔 픽스처다(1414행). 새 규칙에선 이 행이 "미국 10/15 주문 → KST 10/16 07:07 체결"이 되어 KST 10/16 06:15 실행의 스냅숏보다 늦으므로 `FILL_AFTER_SNAPSHOT`로 HOLD된다(의도한 fail-closed). 허용 파일 밖이라 고치지 않았다. **고칠 곳은 1414행 `"20261015"` → `"20261014"` 한 글자뿐**이며, 그 고친 픽스처로 원래 테스트 본문을 그대로 돌린 사본이 새 테스트 파일에서 통과한다(`CorrectedDailyFixture.test_after_hours_fill_dated_by_its_us_order_day_keeps_the_streak`).
- **커밋 2(주문표 주문일 창)는 구현하지 않고 되돌렸다.** 기존 테스트 4개 파일이 "ord_dt = KST 날짜"를 기대값으로 고정하고 있어, 기존 테스트를 고치지 않고는 새 실패 0을 지킬 수 없다(아래 "커밋 2 충돌 실측"). 지켜야 할 것 5·6(새 실패 0, 허용 파일 밖 금지)을 어기지 않으려고 보류했다.
- 사장 결정이 필요한 것: (1) 위 1414행 한 글자 수정을 커밋 1에 포함할지(허용 파일 추가 승인), (2) 커밋 2를 기존 테스트 기대값 수정까지 포함한 후속 작업으로 다시 낼지. 기본 처리(결정 없음): 이 worktree는 병합하지 않음(NO_CHANGE).

## 커밋 1 — 바뀐 줄
manage-us-stock-strategy/scripts/auto_core_reconcile.py
- 92~95행: `US_DAY_OPEN, US_DAY_CLOSE = time(4, 0), time(20, 0)`와 근거 주석(ord_dt = ET 주문일, 2026-10-21/22 실관측, 키움 사양에 시간대 문구 없음).
- 189~191행: `plan_reads` 독스트링 — "KST day" → ord_dt(ET 주문일)를 기록 KST 날짜 전날부터 오늘 KST 날짜까지 읽으며, 체결은 주문일 또는 다음 KST 날이므로 기록 뒤 체결이 모두 들어온다. **조회 창 계산·FILL_WINDOW_MAXIMUM_DAYS=14는 그대로.**
- 249~257행: 새 함수 `_kst_moment(clock, order_day, low, high, low_open=False)` — KST 날짜 후보 {D, D+1} 중 [low, high](low_open이면 (low, high]) 안에 드는 것 하나, 없거나 둘이면 None.
- 261~264행: `parse_fills` 독스트링을 새 규칙으로.
- 305~319행: 옛 줄 `fill_day = order_day + 1 if cntr_time < ord_time`(구 286행)를 대체 —
  - 체결: D 04:00 ET ≤ 시각 ≤ D 20:00 ET인 KST 날짜(zoneinfo, DST 자동). 없으면 `FILL_TIME_OUTSIDE_US_SESSION:<label>`.
  - 주문: D−1 20:00 ET < 시각 ≤ 체결 시각. 없으면(주문 > 체결 포함) `FILL_TIME_INVALID:<label>`.
  - `session_date`(ET 날짜) ≠ D면 `FILL_SESSION_DATE_MISMATCH:<label>`(구성상 도달 불가인 방어 검사). 기록되는 `session_date`는 D.
- 329~332행: 새 함수 `fills_after_snapshot(fills, snapshot_at)` → `FILL_AFTER_SNAPSHOT:<ord_dt>:<ticker>:<side>`.
- 1005행(`run_auto`): 스냅숏 `generated_at` 직후 `fill_errors += fills_after_snapshot(...)` — fill_errors는 기존대로 I2 사유가 되어 HOLD.

manage-us-stock-strategy/references/broker-snapshot-reconciliation.md
- 215~217행: ust21150 조회 범위 문구(ord_dt = ET 주문일, 기록 KST 날짜 전날 ~ 오늘 KST 날짜).
- 231~241행: 체결 KST 시각 규칙과 세 오류 코드.

바꾸지 않은 것(확인): I1~I5 판정식, `CASH_TOLERANCE_USD` 1.00, 정산 수수료 범위, `FILL_WINDOW_MAXIMUM_DAYS`, `cash_flow_evidence.py`, `flow_cash`, 주문·권한 줄(`order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`), 매도 차단 조건. 새 오류는 모두 그 행을 체결에서 빼고 I2를 FAIL로 만든다(느슨해지는 경로 없음).

## 규칙 요약
D = ord_dt(미국 동부 주문일). 체결 KST 시각 = cntr_time을 KST 날짜 D 또는 D+1에 놓았을 때 D 04:00~20:00 ET 안에 드는 쪽(EDT: KST D 17:00 ~ D+1 09:00, EST: KST D 18:00 ~ D+1 10:00). 주문 시각은 D−1 20:00 ET 초과 ~ 체결 이하. 세션 = D. 창 밖·주문>체결·체결>스냅숏은 HOLD.

## 정산일 규칙 확인 (fill_settlement 독스트링 "A date can only hold fills from earlier KST days", 구 497~499행 — 수정 없음)
여전히 성립한다. 체결 KST 날짜는 최대 D+1(20:00 ET = KST D+1 09:00/10:00)이고, ET D 거래의 국내 정산일은 KST D+2 이후다(기존 픽스처: 미국 10/13 → KST 10/15, test_auto_core.py:49~51). 새 규칙으로 시간외 체결의 `last_fill_day`가 하루 늦어져도(D → D+1) D+2 정산 슬롯은 `SETTLEMENT_BEFORE_FILL`에 걸리지 않는다. 10-23 재생에서 10/21 세션이 KST 10/23 슬롯에 맞는 것을 테스트가 보인다.

## flow_cash (수정 안 함 — cashflow-api-gap 조사 항목)
`flow_cash`(auto_core_reconcile.py 615~639행 근처)는 ust21100 `deal_dt`+`proc_time`을 KST로 가정한다. 이번 범위가 아니라 고치지 않았다. ust21100의 날짜 시간대도 ord_dt처럼 ET일 수 있으므로 cashflow-api-gap 작업에서 실관측으로 확인해야 한다.

## 테스트
- 기준선(변경 전, 이 worktree):
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`: 494건, 실패 1(`test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches` PLTR — 카드 레지스트리 해시, 무관), 건너뜀 1.
  - 전체 `python -m unittest discover -s manage-us-stock-strategy/tests`: 3284건, 실패 22 · 오류 9 · 건너뜀 3(auto_core 쪽은 위 PLTR 1건뿐, 나머지는 v2_6_7·evaluate_timing·identity 등 기존 실패).
- 이후(커밋 1만 적용, auto_core_tickets.py 원상 복구 상태):
  - `test_auto_core*`: 505건(+11), 실패 2 = 기준선 PLTR 1 + **새 실패 1**(`test_day_held_only_for_an_unseen_settlement_keeps_the_streak`, 옛 가정 픽스처 — 위 결론 참고).
  - 전체: 3295건(+11), 실패 23 · 오류 9 · 건너뜀 3. 기준선 실패·오류 목록과 이름까지 같고, 늘어난 것은 위 1건뿐.
- 새 테스트(manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py, 11건, 키움·네트워크 없음, 합성 행):
  - `OrderDayIsUsDayTests`: `test_oct21_after_hours_fills_fall_on_the_next_kst_day`(시간외 4건 KST 10/22, 정규장 3건 KST 10/21, session 모두 10/21, BE 19 체결 06:15:28 > 10/22 06:15:07 스냅숏, day-trade 조회는 20261021 하나), `test_after_the_oct21_record_every_fill_counts_including_mvll`(기준 10/21 06:15:04 이후 7건 모두, MVLL 포함), `test_fill_after_kst_midnight_is_the_same_us_day`, `test_winter_time_moves_the_kst_bounds_one_hour`(2026-11-02 EST: KST 08:30·10:00 포함, 10:30·17:59:59 창 밖, EDT 대비 09:30/09:00), `test_kiwoom_day_session_fill_holds`(KST 12:00 → FILL_TIME_OUTSIDE_US_SESSION), `test_order_after_fill_or_outside_its_window_holds`, `test_reserved_order_before_the_session_is_accepted`(KST 10:00 = 전날 21:00 ET 예약 주문 통과), `test_fill_later_than_the_snapshot_holds`.
  - `Oct23ReplayTests.test_quantities_pass_and_only_the_withdrawal_holds`: 기록 10/21 06:15:04 → 실행 10/23 06:15. I2 PASS(7건), I3 사유는 `CASH_CHANGE_NOT_EXPLAINED:-82.93` 하나, 10/21 세션 → KST 10/23 정산. 금액은 합성(실제 reconcile.json은 worktree 밖이라 읽지 않음).
  - `CorrectedDailyFixture`(test_auto_core.DailyTests 재사용, load_tests로 두 건만 실행): 고친 픽스처(ord_dt 20261014)로 원래 시나리오 통과, 옛 픽스처(20261015)는 `I2:FILL_AFTER_SNAPSHOT:20261015:AAA:SELL`로 HOLD·기록 없음.

## 커밋 2 충돌 실측 (구현 보류 근거)
커밋 2의 핵심 두 줄만 임시로 넣고(`order_days` → `[ticket["session"]]`, `ticket_rows`에서 ord_dt ≠ 세션인 행 제외) `test_auto_core*`를 돌린 뒤 되돌렸다. 결과 505건 중 실패 29 = 기준선 PLTR 1 + 커밋 1 픽스처 1 + **커밋 2 때문에 새로 깨진 27건(서브테스트 포함, 테스트 메서드 23개)**:
- test_auto_core_tickets.py (7): OrderWindowTests의 weekday·saturday·winter·early_close(기대값이 "발행 KST일 ~ 마감 KST일" 목록, 230~250행), OrderAttributionTests의 issue_day_rows·attributed_rows·unreadable_cells(세션 10/14 주문표에 ord_dt "2026-10-15" 00:30 행을 같은 주문으로 기대, 284~319행).
- test_auto_core_preon_fix.py (9): SessionCloseBoundTests의 summer_close·winter_close·early_close·unreadable_order_time×3·issue_day_and_last_day(마감 KST일 행 "2026-10-15" 04:59/05:30 등, 167~216행), ReadOutcomesCloseTests 2건(세션 10/01에 `{"20261002": …}` 행, 231~245행).
- test_auto_core_decide.py (10): OrderWindowTests의 weekday·saturday×2·failed_read·monday_holiday, OrderAttributionTests의 after_midnight·disagrees_with_t1·ledger_alone·within_one_run×2.
- test_auto_core_t1_safety.py (1): test_f2_same_number_on_another_day_is_not_a_duplicate(세션 10/01에 ord_dt 10/02 00:30 행, 106~113행).

이 기대값들은 "KST 자정 뒤 주문 = 다음 KST ord_dt"라는 옛 가정의 표현이라 ET 해석과 양립하지 않는다(예: 세션 10/14 주문표에 ord_dt 2026-10-15 04:59 행 — ET 해석에선 미국 10/15 15:59 주문, 다른 세션). 그래서 커밋 2는 이 테스트들의 기대값 수정이 함께 허용돼야 한다.

후속 설계안(승인 시): `order_days` = [세션 S](ord_dt = S), `ticket_rows`는 ord_dt = S 행만 보고 주문 KST 실제 시각을 커밋 1의 `_kst_moment`(창: S−1 20:00 ET 초과 ~ S 20:00 ET, 못 정하면 ORD_TIME_UNREADABLE)로 정한 뒤 "발행 시각(issuedAt 날짜+시각) 이상 ~ 세션 마감(session_close) 이하"로 거른다. 토요일 발행→월요일 세션도 같은 식(ord_dt = 월요일). 귀속 원장 키 (ord_dt, ord_no)와 30일 보존은 그대로. 영향은 ticket_outcome 귀속뿐(상태·발행·가격·수량 무관). 남는 미관측: 주말·전날에 넣은 예약 주문의 ord_dt가 입력일인지 세션일인지 — 실관측 1건으로 확인 필요.

## 커밋 1 · 커밋 2 파일 목록
- 커밋 1: manage-us-stock-strategy/scripts/auto_core_reconcile.py, manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py (+ 승인되면 manage-us-stock-strategy/tests/test_auto_core.py 1414행 한 글자)
- 커밋 2: 없음(보류). auto_core_tickets.py·auto_core_decide.py는 변경 없음(탐침 후 원상 복구, git diff로 확인).
- 보고: docs/claude/recon-dt-report.md

## 검토 순서
- NO_CHANGE: 불가 — 10-22·23 HOLD의 I2·I3 FILL 사유가 시각 해석 오류에서 나오며, 고치지 않으면 시간외 체결이 있는 날마다 같은 HOLD가 반복된다.
- REMOVE/SIMPLIFY: 옛 "cntr < ord면 다음 날" 줄을 지웠다. 주문 시각 없이 체결 시각만으로 날짜를 정하므로 규칙이 더 단순해졌다(주문 시각은 검증에만 씀).
- REUSE: 기존 `KST`·`ET`(zoneinfo), `_clock`, fill_errors → I2 경로, 오류 코드 `FILL_TIME_INVALID`를 그대로 썼다. `day_trade_requests`·`fill_sessions`·정산 매칭은 그대로.
- REPLACE: 날짜 결정 한 줄을 `_kst_moment` 창 판정으로 바꿨다.
- ADD(최소): 창 밖·스냅숏 뒤 체결 오류 2종과 session_date 방어 검사 1종 — 모두 HOLD 쪽이다. 조회 창·불변 조건·허용 범위는 추가·변경 없음.

## 남은 위험
- (a) 키움 사양에 ord_dt 시간대 문구가 없다. ET 해석은 2026-10-21~22 실관측(10/22 KST 06:13~06:40 시간외 체결이 ord_dt 20261021, 10/22 06:15:07 스냅숏의 BE 19 '접수' ord_time 06:13:46)으로만 확정했다(진단 docs/claude/recon-hold-2026-10-23.md — 이 worktree 밖이라 이 세션에서 원문을 열지 못함, 프롬프트 요약에 근거). 키움 주간거래 체결은 관측이 없다 → 창 밖으로 HOLD. KST 자정 뒤 정규장 주문(KST 00~05시)의 ord_dt가 ET 날짜라는 것도 직접 관측은 없고 같은 해석의 귀결이다(어긋나면 FILL_TIME_INVALID/OUTSIDE로 HOLD).
- (b) 고친 뒤에도 10-23 재생은 출금 −82.93(증거 행 없음) 때문에 `CASH_CHANGE_NOT_EXPLAINED`로 HOLD다(cashflow-api-gap). 프롬프트 목표 절의 −82.95와 테스트 절의 −82.93이 다르다 — 테스트는 −82.93을 썼다. 실제 값은 실행 결과에서 확인 필요.
- (c) 11/03 실행부터 `FILL_WINDOW_TOO_LONG`: 기록이 10/21에 머물면 조회 창이 14일을 넘는다. 기록(apply)이 성공해야 창이 줄어든다 — (b)가 풀리기 전엔 기록이 안 된다.
- (d) `flow_cash`의 ust21100 deal_dt KST 가정은 고치지 않았다(위 절).
- (e) 예약 주문: 주문 창 하한(D−1 20:00 ET)보다 이른 주문(예: 전날 시간외 중 다음 날 예약)이 ord_dt D로 오면 FILL_TIME_INVALID로 HOLD된다(관측 없음, fail-closed).
- (f) 커밋 1만 들어가면 주문표 귀속(커밋 2 범위)은 그대로 KST 가정이다. KST 자정 뒤에 넣은 주문(ord_dt = 같은 ET 날)은 발행일 필터 `ord_time ≥ 발행 시각`에 걸려 not_entered로 분류될 수 있지만, 대조 쪽 session_date가 이제 맞으므로 `reconcile_mismatch`(auto_core_tickets.py:682~690)가 `OUTCOME_MISMATCH_WITH_RECONCILE`로 드러낸다(조용히 틀리지 않음). 상태·티켓 발행·가격·수량에는 영향 없음.
- (g) 커밋 2 후속에는 references/auto-core-decision.md 30~37행(주문일 창 설명)도 같이 고쳐야 한다(이번 허용 파일 밖).

## 지킨 것
auto_core.py·reconcile apply·kiwoomcli·예약 작업 실행 없음, 키움 호출 없음, 상태·정책·일지 파일 읽기/쓰기 없음, 커밋·푸시 없음, 줄바꿈 유지(LF 파일, `git diff --stat`과 `--ignore-cr-at-eol` 결과 동일), 테스트는 패턴 명령으로만 실행.

## 최소 수정 1회 (Cowork 지시 2026-10-23 09:3x KST)
허용 파일에 manage-us-stock-strategy/tests/test_auto_core.py를 추가해, `DailyTests.test_day_held_only_for_an_unseen_settlement_keeps_the_streak`의 픽스처 키 한 곳과 주석 한 줄만 바꿨다. 커밋 2(주문표)는 이번에도 하지 않았고 auto_core_tickets.py는 손대지 않았다.

### 바뀐 줄 (`git diff -- manage-us-stock-strategy/tests/`: 1 file, +2 −1)
- 1412행(새 줄, 기존 주석 바로 아래): `# ord_dt is the U.S. (ET) order day, so the fill is keyed 20261014, not the KST date 20261015.`
- 1415행(구 1414행): `fills={"20261015": [...]}` → `fills={"20261014": [...]}`. 같은 줄의 나머지(fill 인자)와 다른 줄·다른 테스트·기대값은 그대로.
- 줄바꿈: `git ls-files --eol` 결과 `i/lf w/crlf`로 수정 전과 같다(mixed 아님). `git diff --stat`과 `--ignore-cr-at-eol --stat` 결과가 같다(+2 −1).

### 테스트 수 비교
| 실행 | 기준선(변경 전) | 앞 실행(커밋 1) | 이번(커밋 1 + 최소 수정) |
|---|---|---|---|
| `-p "test_auto_core*"` | 494건, 실패 1 · 건너뜀 1 | 505건, 실패 2 · 건너뜀 1 | **505건, 실패 1 · 건너뜀 1** |
| 전체 | 3284건, 실패 22 · 오류 9 · 건너뜀 3 | 3295건, 실패 23 · 오류 9 · 건너뜀 3 | **3295건, 실패 22 · 오류 9 · 건너뜀 3** |

늘어난 11건은 새 파일 test_auto_core_reconcile_orddt.py의 테스트다. 앞 실행의 새 실패 1건(`test_day_held_only_for_an_unseen_settlement_keeps_the_streak`)은 이번에 통과한다 → **새 실패 0**.

### 실패 이름 목록 (이번 전체 실행, 출력의 `FAIL:`/`ERROR:` 줄)
- `test_auto_core*` 쪽: FAIL `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches` (symbol='PLTR') 1건뿐 — 기준선과 같다.
- 그 밖의 실패 21: test_evaluate_timing_integration 2(`test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch`, `test_technical_validation_failure_does_not_hide_hard_risk`), test_instrument_identity_authority 1(`test_15_current_fixed_activation_is_exactly_bound`), test_materialize_instrument_identity_artifact 1(`test_candidate_support_does_not_replace_active_registry`), test_materialize_kiwoom_session_aware_acceptance_candidate 1(`test_12_allowed_drift_is_recorded_and_validates`), test_portfolio_decision_dashboard 1(`test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan`), test_scheduled_prompt_kiwoom_profile 1(`test_all_scheduled_prompts_state_profile_and_mode`), test_v2_6_7_session_aware_kiwoom_priority 14(InvariantAndContractTests의 bom_raw_sha·crlf_raw_sha·duplicate_provider_scope·extended_provider_scope·guarded_priority·historical_and_inactive·malformed_provider_scope·missing_acceptance_hash·scope_acceptance_hash_mismatch, unapproved_provider_symbols 서브테스트 4개(BRK.B·BRKb·COST·ZZZZ), PriorityAndScopeTests `test_scope_04_checked_in_provider_scopes_are_complete_and_locked`).
- 오류 9: setUpClass 3(test_holding_baseline_observation_audit, test_mvll_canonical_volume_lineage, test_provider_limitation_audit), test_materialize_kiwoom_session_aware_acceptance_candidate `test_05_materialized_candidate_passes_binding_validator`, test_nbis_v3_shadow_activation `test_price_evidence_preserves_same_session_kiwoom_conflict`, test_nbis_v4_kiwoom_price_authority 2(`test_live_price_artifact_schema_and_semantics`, `test_valuation_uses_kiwoom_and_no_double_count`), test_portfolio_decision_order_intent `test_lmt_candidate_classification_is_verified_but_non_actionable`, test_validate_research_packet `test_snapshot_fixture_declares_contract_version`.

### 기준선과의 이름 비교 — 한계
- 앞 실행 보고는 기준선 실패의 수와 "이름까지 같다"만 적었고 이름 목록 원문은 남기지 않았다. 이번 세션에서 HEAD 기준선을 다시 돌리려 했으나(임시 worktree) 권한 거부로 못 했다 → 이름 단위 대조는 **확인 필요**.
- 대신 확인한 것: (1) 수는 기준선과 정확히 같다(실패 22 · 오류 9, 늘어난 11건은 모두 새 파일의 통과 테스트). (2) auto_core 밖 실패·오류가 나는 14개 테스트 파일은 이번에 바뀐 파일(auto_core_reconcile.py, broker-snapshot-reconciliation.md, test_auto_core.py)을 참조하지 않는다(검색 결과, test_materialize_kiwoom_session_aware_acceptance_candidate.py 467·472행은 다른 스크립트 경로 목록). (3) 오류 일부는 worktree에 없는 workspace/outputs 파일(예: nbis-v2-shadow/20260814-v4/activation-receipt.json) 때문이며 이번 변경과 무관하다.
- 이 판단이 바뀔 조건: Judge가 HEAD에서 같은 명령으로 뽑은 실패 이름 목록이 위 목록과 다를 때.

### 남은 메모
- 새 파일의 `CorrectedDailyFixture`(고친 픽스처 사본 + 옛 픽스처 HOLD 확인)는 이제 원래 테스트가 같은 시나리오를 통과하므로 첫 번째 건이 중복이다. 이번 지시 범위(바꿀 수 있는 것은 test_auto_core.py 두 줄)를 지키려고 그대로 두었다. 옛 픽스처(20261015)가 `I2:FILL_AFTER_SNAPSHOT`으로 HOLD되는 두 번째 건은 회귀 검사로 의미가 있다.
- 커밋 1 파일 목록은 이제 manage-us-stock-strategy/scripts/auto_core_reconcile.py, manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py, manage-us-stock-strategy/tests/test_auto_core.py(+2 −1). 커밋·push 하지 않았다.
- 이번 세션에서도 auto_core.py·apply·키움·예약 작업 실행 없음, 상태·정책·일지 접근 없음.
