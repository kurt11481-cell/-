---
id: t1-safety-report
title: "켜" 전 안전 수정 2건 Builder 보고 — EV4 유실(judge2 G 5) · F6 중복 ord_no(judge2 G 2, r4 F)
date: 2026-10-13
prompt: docs/claude/t1-safety-builder-prompt.md
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음 · 커밋 없음(파이프라인이 함)
---

# t1-safety Builder 보고

## 1. 바꾼 파일·함수

| 파일 | 함수·위치 | 내용 |
|---|---|---|
| `manage-us-stock-strategy/scripts/auto_core_decide.py` | `snapshot_holdings` (새, 166행) | F1의 보유 수량 읽기(스냅샷 `held_quantity` > 0)를 함수로 뺌. `_run`(622행)과 EV4 복구가 같은 함수를 부름(복제 없음) |
| 같은 파일 | `_first_decide_session`, `_rebuilt_total`, `ev4_backfill_plan`, `ev4_backfill_resolve` (새, 175~285행) | 수정 1 본체 |
| 같은 파일 | `_run` (727행 plan, 756~763행 결과·알림) | plan을 만들어 `evaluate_session`에 넘기고, `decision["ev4_backfill"]`과 `EV4_UNDETERMINED` push 줄을 붙임 |
| 같은 파일 | `evaluate_session` (954행 선택 인자 `ev4_backfill=None`, 1035~1038행, 1107행) | 이 세션 S7 hwm·총자산으로 plan을 마무리하고, 열림 세션을 `ev4_all`에 더함. 리플레이는 인자를 넘기지 않으므로 동작 불변 |
| `manage-us-stock-strategy/scripts/auto_core_tickets.py` | `ticket_rows` (531~575행) | 수정 2: 같은 (ord_dt, ord_no) 같은 행 1번, 다른 행이면 `ORD_NO_DUPLICATE_CONFLICT` |
| `manage-us-stock-strategy/scripts/auto_core_rules.py` | `CONSTANTS["RREC_EV4_NEIGHBOR_MARGIN"]` (59행, 새) | 1.03. 기존 상수에 비율 1.03이 없어(V6_APPROACH_USD는 달러 값) 출처 문장과 함께 1개 추가. 기존 상수 값은 그대로 |
| `manage-us-stock-strategy/schemas/auto-core-decision.schema.json` | 최상위 `ev4_backfill` (선택 속성) | `additionalProperties: false`라 추가. required 목록은 그대로(옛 기록도 유효) |
| `manage-us-stock-strategy/tests/test_auto_core_t1_safety.py` | 새 테스트 19개 | 아래 4절 |

auto_core_compare·replay·reconcile·inputs·bars는 손대지 않았다. 권한 표지(`order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`) 줄은 만들거나 바꾸지 않았다. 스크립트·테스트·스키마 모두 ASCII(한국어 알림 문구는 \u 이스케이프).

## 2. 수정 1 — HOLD/FAIL로 F1 전에 끝난 날의 EV4

대상 세션은 R-REC1 창(평가 세션까지 60세션) 안에서, 첫 decide 기록의 evaluation_session부터(그 세션 포함) 오늘 평가 세션 앞까지 중 `account.ev4_open`이 bool로 남은 기록이 없는 세션이다. 첫 기록에 evaluation_session이 없으면(달력 전에 끝난 HOLD) 그 run day 전의 마지막 세션, 즉 그 기록이 평가했을 세션을 쓴다. 대상 세션마다 그 세션 다음 KST 날짜 폴더의 `kiwoom_broker_snapshot.shadow.json`과 decide가 이미 읽은 bars의 그 세션 raw 종가로 F1과 같은 함수(`snapshot_holdings` → `equity_cash` → `tickets.rule_file_nominal` → `rules.ev4_open`)를 불러 다시 구한다(REBUILT). 못 구하면(스냅샷 없음·읽기 실패·종가 또는 봉 없음·현금 없음) 앞뒤로 가장 가까운 알려진 총자산(F1까지 간 기록, 다시 구한 세션, 오늘 평가 세션) 중 하나라도 `rules.ev4_open(total / 1.03, hwm)`이 참이면 열림(NEIGHBOR_NEAR), 아니면 열림 아님(NEIGHBOR_CLEAR)으로 본다. S7 hwm은 그 세션 기록에 `s7_hwm_usd`가 있으면 그 값, 없으면 오늘 결정의 S7 hwm이다. 열림 세션은 `ev4_all`에 더해져 R-REC1 사건(EV4)이 된다. 결정 기록에는 `ev4_backfill`(세션·방법·결과·총자산·이웃·이유)이 남는다. REBUILT가 아닌 세션이 하나라도 있으면 alerts에 push 줄 하나(code `EV4_UNDETERMINED`, line `EV4_UNDETERMINED:<세션들> — EV4 미확정(기록·스냅샷 없음), 이웃 총자산 3% 규칙으로 판정`)가 붙는다.

지시문에 없던 판단 3가지(모두 fail-closed 쪽):
- **이웃이 하나도 없음**(알려진 총자산이 아예 없음, 오늘 총자산도 없음): 방법 `NEIGHBOR_NONE`, 열림으로 본다. 지시문의 세 값(REBUILT·NEIGHBOR_NEAR·NEIGHBOR_CLEAR)으로는 표시할 수 없어 네 번째 값을 더했다. 이 경우 오늘 rule-file N도 모르므로 매수 요건 (2)가 이미 매수를 막는다.
- **첫 기록 세션 포함**: "첫 기록 이후"를 그 세션 포함으로 읽었다. 첫 기록이 F1 전에 끝났으면 그 세션도 비어 있기 때문이다.
- **F1 이후 FAIL 기록**(스키마·일지 거절 등으로 account가 남음)은 기존처럼 덮인 세션으로 본다(기존 `ev4_sessions` 규칙과 같음).

R3-3(새 세션 없음) 기록과 F1 전에 끝난 기록에는 `ev4_backfill` 키가 없다(스키마 선택 속성). 리플레이(`auto_core_replay`)는 바꾸지 않았다.

## 3. 수정 2 — F6 같은 날 조회 안의 중복 ord_no

`ticket_rows`는 먼저 조회한 모든 행을 (ord_dt, ord_no)로 묶는다. 이 주문표의 후보 행(종목·매수/매도 일치)마다, 같은 (ord_dt, ord_no)에 그 행과 **다른 행**이 하나라도 있으면 결과 없이 note `ORD_NO_DUPLICATE_CONFLICT`를 돌려준다. `read_outcomes`는 지금 `ORD_NO_UNREADABLE`처럼 그 주문표를 open으로 두고 `OUTCOME_UNKNOWN:<id>`를 남기며, G0에서 막혀 그날 새 주문표도 없다. **완전히 같은 행**이 두 번 오면 한 번만 쓴다. T1의 `FILL_ROW_DUPLICATE_CONFLICT`(auto_core_reconcile.py 291~294행)와 같은 규칙이다. T1은 정규화한 체결 항목을 비교하고, F6은 원래 행 dict 전체를 비교하므로 F6 쪽이 같거나 더 엄격하다. 그 밖의 분류(종목·방향 거르기, ord_no 없음, 발행 시각 전 행, 이미 귀속된 행, `classify_outcome`)는 그대로다.

지시문에 없던 판단 2가지(fail-closed 쪽): (a) 같은 번호의 다른 행이 다른 종목·방향 행이어도 충돌로 본다(같은 주문번호가 두 주문을 가리키므로). (b) 충돌 검사는 "이미 귀속된 행" 건너뛰기보다 앞에 둔다. 같은 번호가 다른 날에 오면 중복이 아니다(키가 (ord_dt, ord_no)이기 때문, 테스트 있음).

## 4. 테스트

새 파일 `manage-us-stock-strategy/tests/test_auto_core_t1_safety.py`(test_auto_core_decide.Env 픽스처 재사용, 모두 합성 TEST_ONLY):

| 이름 | 확인 |
|---|---|
| S1 `test_s1_record_before_f1_with_snapshot_below_the_line_is_rebuilt_and_opens_rrec1` | 전날 기록 FAIL(account 없음) + 스냅샷 총자산 선 아래 → `ev4_backfill` REBUILT true, shock events에 그 세션 EV4, shock open. 수정 전 경로(plan 없음)에는 없음 |
| S1b `test_s1_record_without_evaluation_session_counts_from_its_run_day` | 달력 전 HOLD 기록(evaluation_session null)도 그 run day 전 마지막 세션부터 대상 |
| S2 `test_s2_rebuilt_above_the_line_changes_nothing_else` | 선 위 → REBUILT false, EV4 없음, push 없음, `ev4_backfill` 말고 결정 기록 전체가 수정 전 경로와 같음(골든) |
| S3 `test_s3_no_record_no_snapshot_neighbor_within_three_percent_opens` | 기록·스냅샷 없음 + 이웃 총자산 = 선 × 1.02 → NEIGHBOR_NEAR 열림, EV4 사건, push `EV4_UNDETERMINED:<두 세션>` |
| S4 `test_s4_no_record_no_snapshot_neighbors_far_stays_closed_with_a_push` | 이웃 = 선 × 1.05 → NEIGHBOR_CLEAR, EV4 없음, push 있음, push 줄과 `ev4_backfill`만 다르고 나머지는 같음 |
| S4b `test_s4_snapshot_without_the_holding_bars_is_not_rebuilt` | 스냅샷의 보유 종목 봉 없음 → 다시 구하지 않음(reason `CLOSE_MISSING:ZZZZ`) → 이웃 규칙 |
| S5 `test_s5_sessions_before_the_first_record_are_not_targets` | 첫(유일한) 기록 전 세션은 대상 아님 → `[]`, 골든 같음 |
| S5b `test_s5_existing_fixture_without_records_is_unchanged` | 기존 픽스처(이전 기록 없음) 결과 불변 |
| S6 `test_s6_every_record_reached_f1_gives_the_same_decision` | 모든 기록이 F1까지 감 → `[]`, 주문표·관문·shock·account·exposure·alerts·status와 결정 기록 전체가 수정 전 경로와 같음 |
| `test_record_before_f1_is_absent_key_and_schema_valid` | T1 FAIL HOLD 기록에는 키 없음, 스키마 유효 |
| Ev4Resolve 4개 | 기록 hwm 우선, 이웃 없음 = 열림(NEIGHBOR_NONE), plan 없음 = [], 상수 1.03과 출처 |
| F1 `test_f1_the_same_row_twice_counts_once` | 같은 행 2번 → 1번(filled 5, 10 아님) |
| F2 `test_f2_a_different_row_with_the_same_order_number_is_unknown` | 체결 수량이 다른 행·다른 종목 행 → `ORD_NO_DUPLICATE_CONFLICT` |
| F2b `test_f2_through_read_outcomes_the_ticket_stays_open` | read_outcomes: outcome 없음, open 유지, `OUTCOME_UNKNOWN:<id>`, 귀속 없음 |
| F2c `test_f2_same_number_on_another_day_is_not_a_duplicate` | 다른 날 같은 번호는 중복 아님 |
| F3 `test_f3_no_duplicate_classifies_as_before` | 중복 없음 → 기존과 같은 행 선택·partial 분류, 기존 note(ORD_NO_UNREADABLE·ORD_TIME_UNREADABLE)·귀속 건너뛰기 불변 |

"수정 전과 같다"(골든)는 `ev4_backfill_plan`을 수정 전 동작(plan 없음 → 대상 0)으로 바꾼 같은 실행과 비교한다.

결과:
- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_t1_safety.py"` → 19 tests OK.
- auto-core 전체: `-p "test_auto_core*.py"` → 379 tests OK (skipped=1, 기존 skip). 수정 전 360개도 수정 후 그대로 통과(기존 테스트 파일은 고치지 않음).
- 전체 `-p "test_*.py"` → Ran 3022 · FAILED (failures=19, errors=9, skipped=3). 숫자는 t2-equity-cash 보고의 기준선(failures=19, errors=9)과 같다. 남은 28건은 모두 test_v2_6_7_session_aware_kiwoom_priority(acceptance manifest binding 못 찾음), nbis_v3/v4, materialize_*, instrument_identity, holding_baseline_observation_audit, mvll_canonical_volume_lineage, provider_limitation_audit, portfolio_decision_order_intent/dashboard, validate_research_packet, evaluate_timing_integration에 있다. 바뀐 모듈(auto_core_decide·tickets·rules, decision 스키마)을 import하는 테스트는 test_auto_core*뿐이므로 이 28건은 이번 변경과 무관하다. **새 실패 0.** 중간 실행에서 test_language_contract·test_v2_5_beginner_renderer의 "scripts/*.py ASCII" 검사 2건이 실패했다. 알림 문구가 이스케이프 대신 한국어 문자로 저장된 것이 원인이었고, \u 이스케이프로 고친 뒤 두 파일 모두 OK다.
- 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → PASS, errors [].

## 5. 실데이터(읽기 전용) — 하지 못함

2026-10-13 결정 기록으로 오늘 결정을 다시 만드는 확인은 **하지 못했다**. 이 worktree에는 `workspace/outputs/auto-core/`가 없다(추적되지 않는 실행 출력이다). 메인 저장소 경로 읽기는 이 헤드리스 세션에서 권한이 거부되었다. 예상만 적는다. 첫 decide 기록의 evaluation_session(10/12 세션 예상) 전 세션은 대상이 아니다. 그 뒤 기록들이 모두 F1까지 갔으면 `ev4_backfill`은 `[]`이고 shock은 그대로다(S6과 같은 경로). **Judge 또는 Cowork가 실데이터로 확인할 항목**: 병합 뒤 첫 decide 기록의 `ev4_backfill`과 `alerts`에 `EV4_UNDETERMINED`가 있는지 본다. 있으면 해당 세션의 run-day 폴더에 스냅샷이 있는지 확인한다.

## 6. 남은 위험(fail-open 또는 판단 경계)

1. **NEIGHBOR_CLEAR는 추정이다.** 앞뒤 이웃이 선의 1.03배를 넘어도 빈 세션 하루만 선 아래였을 수 있다(장중이 아니라 종가 기준 하루 3% 넘는 급락). push 줄로 보이게만 했고, 막지는 않는다(지시문 규칙대로).
2. **판정이 고정되지 않는다.** 복구 결과는 이후 기록에 EV4로 남지 않고 run마다 다시 계산된다. 빈 세션의 "뒤 이웃"이 오늘 평가 세션이면, 오늘 총자산이 바뀌면서 다음 날 판정이 NEAR↔CLEAR로 바뀔 수 있다. 매일 `ev4_backfill`에 보인다.
3. **오늘 보유하지 않은 종목.** 과거 스냅샷의 종목이 오늘 universe(보유·관심·벤치마크)에 없으면 봉이 없어 REBUILT가 안 되고 이웃 규칙으로 간다(지시문: decide가 이미 읽은 bars만 씀).
4. **스냅샷 위치 가정.** 세션 다음 KST 날짜 폴더의 T1 스냅샷을 그 세션의 장 마감 뒤 상태로 본다. T1이 그날 실패해 스냅샷이 없으면 이웃 규칙이 적용된다. 스냅샷 날짜·시각은 검증하지 않는다.
5. **F1 뒤 FAIL 기록**(account 있음)은 기존과 같이 그 `ev4_open`을 믿는다. 이번 범위 밖이다.
6. **R3-3(새 세션 없음) 날**은 source의 shock을 복사하므로 복구하지 않는다(기존 동작). 다음 새 세션 run에서 다시 계산된다.
7. 수정 2는 F6 행 비교만 한다. T1 대조와 F6가 서로 다른 중복 판정을 내는 경우(T1은 정규화 항목 비교)는 `OUTCOME_UNKNOWN` 또는 `OUTCOME_MISMATCH_WITH_RECONCILE`로 막힌다. 열리는 쪽은 없다.

## 7. 사용자·운영 영향

weekly_user_touch 0. 병합은 `.\tools\dev-merge.ps1 t1-safety -ApproveAuthority`(경로 때문에 붙는 플래그). 주문표 수량·가격 규칙, 관문 기준값, EV1~EV5 정의, RG1~RG4는 바뀌지 않았다. 새 동작은 막는 쪽으로만 작동한다. 수정 1(EV4 사건 추가)은 R-REC1을 거쳐 매수만 막고 매도는 막지 않는다. 수정 2(F6 unknown)는 기존 `ORD_NO_UNREADABLE`과 같이 G0을 막아 그날 새 주문표(매도 포함)가 없고 push가 간다. 이는 기존 fail-closed 경로와 같다.
