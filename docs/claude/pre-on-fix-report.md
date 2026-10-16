---
id: pre-on-fix-report
title: "켜" 전 코어 수정 3건 Builder 보고 — ④ 휴장 날 입력 문구 · ① r4 E 마감 뒤 행 · ⑥ G0_TICKET_SESSION_NOT_YET 알림
date: 2026-10-15
prompt: docs/claude/pre-on-fix-builder-prompt.md
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태·스키마 쓰기 없음
---

# 바꾼 줄과 새 동작

## ④ 새 세션 없음 날 입력 문구 (auto_core_decide.py)
- `_no_new_session` :946 — `next_action_for_user`가 새 도우미 `_carried_entry_line(orders, open_tickets)`를 부른다(apply 모드이고 넘어온 주문 행이 있을 때만. 조건은 전과 같다).
- `_carried_entry_line` :951-969 (신규) — 넘어온 주문 행의 `id`로 open_tickets의 `issued_day`를 찾아 M/D로 쓴다. 날짜가 여럿이면 정렬해서 `·`로 잇는다. 읽을 수 없으면 `?`로 보인다(추정하지 않음).
- 새 동작: apply 모드 새 세션 없음 날 문구는 `주문표 N건 — 10/17 발행분과 같은 주문표: 이미 입력했으면 다시 넣지 않음(안 넣었으면 저녁 키움 입력)`이다(한 줄). compare 모드는 None 그대로다. 새 세션 날 문구(:805 `주문표 N건 — 저녁 키움 입력`)는 그대로다. dashboard.orders·runCore.tickets·그날 쓰는 파일·읽기(없음)는 바꾸지 않았다. 선택 사항인 runCore.tickets `carried` 표지는 넣지 않았다(스키마·C1 영향을 피하려고).

## ① r4 E — 끝 날짜 마감 뒤 행 (auto_core_tickets.py, auto_core_decide.py)
- `session_close` :525-538 (신규) — 티켓 세션의 calendar `core_close_at`을 KST datetime으로 돌려준다(조기 마감이면 그 시각). 세션이 calendar에 없거나, 읽을 수 없거나, 시간대가 없으면 None이다.
- `ticket_rows` :546 — 필수 키워드 인자 `close_at`이 추가됐다. :552-555는 docstring이다. :559-562에서 `close_at` None이면 note `ORDER_WINDOW_UNKNOWN`(fail closed)이다. :593-598에서 끝 날짜(close_at의 KST 날짜) 행은 `ord_time <= close_at의 KST 시각`만 쓴다. 그 날 ord_time을 못 읽으면 `ORD_TIME_UNREADABLE`이다. 발행일과 끝 날짜가 같으면 두 경계를 모두 적용한다. 발행일 하한(:585-592)은 그대로다.
- `read_outcomes` :333-334 — `session_close`가 None이면 창을 모르는 경우와 같게 처리한다(`ORDER_WINDOW_UNKNOWN` + `OUTCOME_UNKNOWN`, 티켓은 open). :343에서 `close_at`을 넘긴다. :299-300은 docstring이다.
- 새 동작: 마감 뒤(여름 05:00, 겨울 06:00, 조기 마감 03:00 KST 뒤)에 따로 넣은 같은 종목·방향 행은 그 주문표의 결과가 아니다. 결과 상태 이름은 그대로다(filled·partial·unfilled·not_entered·changed와 기존 unknown note).

## ⑥ G0_TICKET_SESSION_NOT_YET 예외 알림 (auto_core_decide.py)
- :709-713 — outcome_block reasons에 `G0_TICKET_SESSION_NOT_YET:`가 하나라도 있으면 exceptions에 `("G0_TICKET_SESSION_NOT_YET", "주문표 세션 이전 상태 — 새 주문표 없음, Cowork 확인")`을 한 번 더한다. 이 알림은 alert_candidates :463-464에서 push True가 된다. 경로가 하나라 compare 모드에서도 push다(다른 예외 알림과 같다). gate0(:700)·HOLD(:778-780)·새 세션 없음 경로는 그대로다.

# 테스트

## 새 테스트 `manage-us-stock-strategy/tests/test_auto_core_preon_fix.py` (18개)
- ④ NoNewSessionEntryLineTests
  - `test_one_carried_ticket_names_its_issue_day`: 문구 전체가 같다. orders 행 불변, 읽기 0, 그날 파일 목록 불변, 스키마 유효, reasons [], 알림은 NO_NEW_SESSION(push False)뿐이다.
  - `test_two_issue_days_are_both_named`: `10/16·10/17`, 2건.
  - `test_compare_mode_has_no_user_line`: None.
  - `test_the_new_session_day_line_is_unchanged`: `주문표 1건 — 저녁 키움 입력`.
  - `test_an_unreadable_issue_day_shows_as_unknown`: `?`.
- ① SessionCloseBoundTests(8개)·ReadOutcomesCloseTests(3개)
  - 여름 05:30 행 제외 → not_entered. 04:59·05:00 포함 → filled.
  - 겨울 마감 06:00(05:30 포함, 06:01 제외).
  - 조기 마감 03:00 날 03:30 제외, 02:59 포함.
  - 끝 날짜 ord_time ""·"x"·"25:00:00" → ORD_TIME_UNREADABLE.
  - close_at None → ORDER_WINDOW_UNKNOWN.
  - 발행일 하한 불변.
  - 발행일 = 끝 날짜면 두 경계를 모두 적용.
  - read_outcomes 경유: 05:30 → not_entered, attributed 없음. 04:59 → filled, attributed. 끝 날짜 시각을 못 읽으면 open + OUTCOME_UNKNOWN. 시간대 없는 core_close_at → ORDER_WINDOW_UNKNOWN + OUTCOME_UNKNOWN.
- ⑥ TicketSessionNotYetAlertTests
  - `test_the_anomaly_is_pushed_and_the_hold_is_unchanged`(compare·apply): HOLD, 두 reasons 유지, open 2건, 읽기는 account_open_items뿐이다. 알림은 정확히 1개 `{"code": "G0_TICKET_SESSION_NOT_YET", "line": ..., "push": true}`이고 스키마는 유효하다.
  - `test_no_alert_without_the_reason`: 알림 없음.

## 고친 기존 테스트 (기대값·고정 자료·새 인자만. 단언 삭제·skip 없음)
| 파일:행(수정 후) | 전 | 후 | 이유 |
|---|---|---|---|
| test_auto_core_tickets.py:277-280 `chosen` | `tk.ticket_rows(ticket, rows, set(attributed))` | `close_at=tk.session_close(ticket, helpers.calendar(CALENDAR_DAYS))`를 넘긴다 | ticket_rows의 새 필수 인자(fail closed. 기본값 없음) |
| test_auto_core_tickets.py:317-318 | 끝 날짜(10/15) 행 ord_time `""` → note None 기대 | ord_time `"00:30:00"`, 주석 갱신 | 끝 날짜에서는 ord_time을 읽어야 한다(①). 그 단언의 목적(발행 시각은 발행일에만 필요)은 유지 |
| test_auto_core_t1_safety.py:281-285 | — | `_close()` 도우미(10/02 05:00 KST) 추가 | 새 필수 인자 |
| test_auto_core_t1_safety.py:289-290, 300-301, 333, 341-346 | `ticket_rows(..., set())` 등 | `close_at=_close()` 추가 | 새 필수 인자. 기대값은 그대로 |
| test_auto_core_t1_safety.py:318-320 | 10/02 행 ord_time 기본 `17:30:00` | `ord_time="00:30:00"` | 10/02는 끝 날짜다. 17:30은 마감(05:00) 뒤라 이제 제외된다. 테스트 목적(다른 날 같은 번호는 중복이 아님)을 지키려고 세션 안 시각으로 바꿈 |
| test_auto_core_decide.py:1044-1049 `test_the_ledger_alone_keeps_a_later_row_out_across_a_hold_day` | 행 `08:10:00`, 주석 "Only the ledger keeps it from T'" | 행 `04:30:00`, 주석 갱신 | 08:10은 T 세션 마감 뒤라 이제 T의 것이 아니다. 04:30이면 T 결과·HOLD 날 장부 이월·d3 단언이 모두 그대로 성립한다 |
| test_auto_core_decide.py:1067-1074 `test_compare_mode_keeps_no_list` | d1 T 기대 `filled` | d1 T 기대 `not_entered`, 주석 갱신 | 08:10 행은 T 마감 뒤라 T의 것이 아니고 T'의 것이다(d2 `filled` 그대로). 이 테스트 목적인 compare 모드 attributed_orders [] 단언은 그대로다 |
| test_auto_core_decide.py:1082, 1090 `test_within_one_run_a_row_counts_once_in_both_modes` | 행 `08:00:00`, 주석 | 행 `04:30:00`, 주석 갱신 | 08:00은 A 마감(05:00) 뒤다. 04:30이면 A filled·B not_entered·장부 단언이 그대로다 |

골든·불변 테스트는 고치지 않았고 그대로 통과한다.
- test_auto_core_risk1r `test_tickets_without_risk_1r_hash_as_before`(GOLDEN 8키)
- test_auto_core_compare_fix `test_t5_decide_record_unchanged_except_margins`·`test_t5_margins_differ_only_for_hit_event_groups`

# 결과
- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` → **Ran 423, OK (skipped=1)**. 수정 전 같은 명령은 Ran 405, skipped=1이었다(새 18개 추가).
- 새 파일만: `-p "test_auto_core_preon_fix.py"` → Ran 18, OK.
- risk1r·compare_fix 계열: `-p "test_auto_core_[rc][io]*.py"` → Ran 60, OK(GOLDEN·T5 포함).
- 전체: `-p "test_*.py"` → Ran 3105, failures 19 · errors 9 · skipped 3.
  - 실패·오류는 모두 auto-core 밖이다: test_v2_6_7_session_aware_kiwoom_priority(수락 manifest binding matches=[]), test_materialize_kiwoom_session_aware_acceptance_candidate, test_instrument_identity_authority, test_materialize_instrument_identity_artifact, test_nbis_v3/v4, test_portfolio_decision_*, test_validate_research_packet, test_evaluate_timing_integration, setUpClass 3건(holding_baseline·mvll·provider_limitation).
  - 바뀐 두 모듈(auto_core_decide·auto_core_tickets)을 import하는 테스트는 test_auto_core* 9개 파일뿐이고 모두 통과했다. 그래서 새 실패는 0으로 판단한다.
  - HEAD 기준선을 따로 돌리지는 않았다. 파이프라인의 측정 기준선과 대조가 필요하다.
- 스키마 감사 `validate_schema_contracts.py` → PASS, errors [].
- 줄 끝: 고친 기존 파일 5개는 CRLF를 유지했다. 바뀐 줄만 diff에 나온다. 새 테스트 파일은 Write 도구로 썼다.

# 지켜야 할 것 확인
- 바꾼 파일은 allowed_paths 안이다(scripts 2개, tests 4개, 이 보고서).
- 스키마·정책·상태·카드·등록부·CONSTANTS·POLICY_EXPECTED·관문 기준값·회로·요건·수량·가격·후보 계산은 바꾸지 않았다.
- decision.json에서 바뀌는 것은 ① 분류 결과(마감 뒤 행 제외), ④ next_action_for_user 문구, ⑥ alerts 한 줄뿐이다.
- 키움 호출·주문 경로·권한 표지 추가는 없다. auto_core.py 실행 명령은 쓰지 않았다.
- 새 세션 없음 날 쓰는 파일은 그대로 decision.json·LATEST_DECISION.json뿐이다(테스트로 확인). S7·compare.json은 쓰지 않는다.
- t2rc-oracle.py는 코어 outcomes를 그대로 G0에 쓴다(:1833-1835). 재분류하지 않으므로 ①은 계산기와 같은 G0를 낸다. 계산기는 next_action·alerts를 읽지 않는다.

# 남은 위험
1. ① 뒤로는 같은 종목·방향의 연속 주문표 두 장의 창이 겹치지 않는다(앞 장은 마감 시각까지, 뒷 장은 발행 시각부터). 그래서 r4 장부(attributed_orders)는 이 경우 이중 방어가 된다. 기존 테스트 이름 "ledger alone"은 그대로 두었다.
2. 마감 뒤(D+1 05:00~07:45 KST)에 사용자가 앞 주문표를 늦게 넣은 경우가 있다. 이 주문은 다음 세션 LOC가 되므로 앞 주문표는 not_entered(또는 unfilled)로 분류된다. 그 행은 뒷 주문표의 발행 시각 전이면 어느 주문표의 것도 아니다. 의도된 동작이지만 실제로 생기면 T1 대조 불일치(OUTCOME_MISMATCH_WITH_RECONCILE) 알림으로 보일 수 있다.
3. ord_time을 KST로 읽는 가정(T1 `_clock`)은 발행일 하한과 같다. 바뀐 가정은 없다.
4. 시간대 없는 `core_close_at`은 이제 ORDER_WINDOW_UNKNOWN(fail closed)이다. 운영 calendar에는 오프셋이 있다는 전제다(helpers.calendar와 같음).
5. manage-us-stock-strategy/references/auto-core-decision.md는 allowed_paths 밖이라 이 세 동작을 반영하지 않았다. 문서 후속은 Cowork(docs)에서 한다.
6. 전체 스위트 실패 28건은 이 변경과 무관하다고 판단했지만, HEAD 기준선은 직접 재지 않았다(위 결과 절).
