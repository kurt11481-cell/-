---
id: enter-window3-report
title: enter-window3 Builder 보고 — 주문표 입력 시작 = 세션 개장일 프리마켓 시작
date: 2026-10-20
prompt: docs/claude/enter-window3-builder-prompt.md
base: dfa1b07
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음
---

## 1. 바꾼 줄과 새 동작

### 1-1 입력 시작 (`manage-us-stock-strategy/scripts/auto_core_tickets.py`)
- :70-76 표시용 상수 추가: `PREMARKET_LEAD = timedelta(hours=5, minutes=30)`, `ISSUE_TIME = time(7, 45)`,
  `WEEKDAYS`(월~일 한 글자, 소스는 ASCII 유지를 위해 코드포인트로 씀). 주석(ASCII)에 출처: 사용자 2026-10-20,
  키움 LOC 접수 = 프리마켓 시작 ~ 정규장 마감. SIZING·S·POLICY_EXPECTED·auto-core-config·관문에는 넣지 않았다.
- :833-835 `_entry_start(issued, opens)` = max(발행 KST 날짜 07:45, 개장(KST) − 5h30m).
- :838-848 `entry_start(issue_day, session_row)`: 같은 계산, 단 발행일·`core_open_at`이 없거나 못 읽거나
  오프셋이 없으면 None(추측하지 않음). 표시 문구용.
- :851-853 `entry_start_text(start)` = "M/D(<요일>) HH:MM".
- :856-866 `enter_window`: 시작을 "발행일 17:00" 고정에서 "개장일 프리마켓 시작"으로 바꿈.
  - 개장일 = 발행일: "한국 <M/D> <HH:MM> 이후 ~ 정규장 개장 전(<open HH:MM>)" (여름 평일은 이전과 같은 글자)
  - 개장일 ≠ 발행일: "한국 <open M/D>(<요일>) <HH:MM> 이후 ~ <open HH:MM> 개장 전"
  - 끝("개장 전", 개장 시각)은 그대로. 이전처럼 `core_open_at`이 없으면 KeyError로 실패(동작 불변).

새 동작: 토요일 07:45 주문표(월요일 세션)는 "한국 10/19(월) 17:00 이후 ~ 22:30 개장 전", 휴일 건너 화요일 세션은
"10/20(화) 17:00", 겨울(개장 23:30 KST)은 18:00, 조기 마감 날은 개장 시각이 같으므로 여름 17:00·겨울 18:00.

개장일이 발행일보다 앞서는 경우: 지금 코드에 따로 처리(fail closed)가 없다. 지시문대로 동작을 더하지 않았다.
max() 때문에 그런 입력에서는 시작이 발행일 07:45가 된다(테스트 `test_the_start_is_never_before_the_issue_days_run`,
달력에서는 생기지 않는 합성 입력). 주문표는 늘 buy_session(평가 세션 다음)으로 나오므로 실제로는 도달하지 않는다고 본다.

### 1-2 입력 안내 문구 (`manage-us-stock-strategy/scripts/auto_core_decide.py`)
- :700-702 apply 모드 새 세션 날: "주문표 N건 — <M/D>(<요일>) <HH:MM> 이후 키움 입력". 시각은 그날 주문표들
  (발행일 = run day, 각 주문표 `session`의 달력 행)의 입력 시작 중 가장 이른 것. 세션이 서로 다르면(정상 아님)
  가장 이른 시작을 쓴다. 하나라도 못 구하면 지금 문구 "주문표 N건 — 저녁 키움 입력"을 그대로 쓴다.
  compare 모드는 이전처럼 None.
- :848-856 `_earliest_entry_start(pairs, calendar)` 추가(위 계산, 빈 목록·못 읽음 → None).
- :859-882 `_carried_entry_line(orders, open_tickets, calendar=None)`: "(안 넣었으면 <M/D>(<요일>) <HH:MM> 이후
  키움 입력)". 각 order id의 open ticket `issued_day`·`session`으로 시작을 구하고 가장 이른 것을 쓴다. 달력이
  없거나(인자 생략 포함), 세션이 달력에 없거나, 발행일을 못 읽거나, 해당 open ticket이 없으면 지금 문구
  "(안 넣었으면 저녁 키움 입력)" 그대로.
- :843 `_no_new_session`이 `calendar`를 넘김.

### 1-3 문서 (`manage-us-stock-strategy/references/auto-core-decision.md` :161-169)
"Entry window (r4)" 항목을 새 정의로 바꿈: 시작 = 개장일 core_open_at(KST) − 5h30m(여름 17:00·겨울 18:00, 발행일
07:45 이전 불가), 주말·휴일 주문표는 개장일 날짜, 끝은 개장, 주간거래는 회사 거래시간 밖, 사용자 안내 두 줄과
못 구할 때 "저녁", 표시 전용.

## 2. 테스트

### 2-1 새 파일 `manage-us-stock-strategy/tests/test_auto_core_enter_window.py` (17개)
- EnterWindowTests: 평일 여름(이전 구현과 같은 글자), 토요일 여름 → 10/19(월) 17:00, 휴일 다음 → 10/20(화),
  겨울 → 18:00(같은 날·토요일→11/9(월)), 조기 마감(여름 7/3 17:00, 겨울 11/27 18:00), 발행일 07:45 하한,
  못 읽는 입력 7가지 → None, 상수가 SIZING·S·POLICY_EXPECTED에 없음, Scenario 주문표의 enterWindow·fillAt.
- NewSessionLineTests: apply → "주문표 1건 — 10/12(월) 17:00 이후 키움 입력"(토요일 발행 → 월요일 날짜),
  compare → None, entry_start가 None이면 "저녁" 문구, `_earliest_entry_start` 평일·토요일·세션 둘(가장 이른 것)·못 구함 5가지.
- CarriedLineTests: 날짜 포함, 세션 둘이면 가장 이른 시작, 못 구하면(달력 없음·발행일 없음·session 없음·
  달력에 없는 날·해당 ticket 없음·인자 2개 호출) 지금 문구.
- GoldenCauseTests: 이전 enter_window(base 구현 그대로 복사)를 끼우면 risk1r 8키가 BASE_GOLDEN(이전 값)과 같고,
  새 코드 값은 risk1r.GOLDEN과 같으며, 바뀐 키는 정확히 default·sell·pwr·decide_compare·decide_apply, 나머지
  3키는 이전 값과 같고, enterWindow 필드를 뺀 뷰는 이전·새 코드가 같다(다른 필드 변화 없음).

### 2-2 고친 기존 테스트 (기대 문구만)
| 파일:행 | 전 | 후 | 이유 |
|---|---|---|---|
| test_auto_core_tickets.py:772 | "한국 10/17 17:00 이후 ~ 10/19 22:30 개장 전" | "한국 10/19(월) 17:00 이후 ~ 22:30 개장 전" | 토요일 주문표 시작 = 월요일 프리마켓 |
| test_auto_core_tickets.py:777 | "한국 10/17 17:00 이후 ~ 10/20 22:30 개장 전" | "한국 10/20(화) 17:00 이후 ~ 22:30 개장 전" | 휴일 건너 개장일 날짜 |
| test_auto_core_tickets.py:781 | "한국 11/4 17:00 이후 ~ 정규장 개장 전(23:30)" | "한국 11/4 18:00 이후 ~ 정규장 개장 전(23:30)" | 겨울 프리마켓 18:00 |
| test_auto_core_tickets.py:782 | "한국 11/7 17:00 이후 ~ 11/9 23:30 개장 전" | "한국 11/9(월) 18:00 이후 ~ 23:30 개장 전" | 토요일·겨울 |
| test_auto_core_tickets.py:788 | "한국 10/10 17:00 이후 ~ 10/12 22:30 개장 전" | "한국 10/12(월) 17:00 이후 ~ 22:30 개장 전" | Scenario 토요일 10/10 발행 |
| test_auto_core_preon_fix.py:37-43 | CARRIED "(안 넣었으면 저녁 키움 입력)", NEW_SESSION_LINE "주문표 {count}건 — 저녁 키움 입력" | CARRIED에 `{when}` 자리, `EVENING="저녁"`, NEW_SESSION_LINE "주문표 {count}건 — {start} 이후 키움 입력" | 날짜·시각 자리 |
| test_auto_core_preon_fix.py:92 | days="10/17" | + when="10/20(화) 17:00 이후" | 화요일 세션 입력 시작 |
| test_auto_core_preon_fix.py:112-113 | days="10/16·10/17" | + when="10/20(화) 17:00 이후" | 같음 |
| test_auto_core_preon_fix.py:130-131 | NEW_SESSION_LINE.format(count=1) | 세션 2026-10-12 확인 줄 추가 + start="10/12(월) 17:00" | 토요일 10/10 발행 → 월요일 |
| test_auto_core_preon_fix.py:135 | days="?" | + when=EVENING | 인자 2개 호출 = 입력 시작을 못 구함 → 지금 문구 그대로 |

test_auto_core_decide.py :414·:835는 assertIsNotNone이라 고치지 않았다(통과).

### 2-3 GOLDEN (test_auto_core_risk1r.py :36-59)
5키만 실측값으로 바꾸고 각 키 위에 "enter-window: enterWindow 시작 문구만 바뀜(test_auto_core_enter_window
GoldenCauseTests로 확인)" 주석을 달았다. 실측은 지시문의 2회차 접두어와 모두 같다.

| 키 | 전 | 후 |
|---|---|---|
| default | 0ddc8af344e7… | e44f3d6ae695d3bb16d85bbfac6eeb9e0c0e41edd9d2e8dbaf2aa2280c0e23a0 |
| sell | 04d0c947817… | 18633988ed376dbcc8b1053009cf6f9f480f6715307211177774fb11165879d6 |
| pwr | cb46340d4e5c… | 2aabe270157c4d8a401b10d1606874ccba4220a2206e1c7728614653595404c1 |
| decide_compare | 612f246deed9… | 2e565c3b7f2d10eb10089c81cce6899b62168bb36a6ede08f78159fcf925bf95 |
| decide_apply | 91c252b86a22… | d78459cbeb51b2d7ebe70284de3d73ffbae404093fb680c4f7fa1acbe870c43b |

g2b·cash5·research_block는 그대로(측정값 = 이전 값). GoldenCauseTests 통과. test_auto_core_compare_fix(T5 불변 포함)
통과, 파일 수정 없음.

### 2-4 결과 (2026-10-20, 이 worktree)
- `-p "test_auto_core_enter_window.py"`: Ran 17, OK
- `-p "test_auto_core_tickets.py"`: Ran 59, OK · `-p "test_auto_core_preon_fix.py"`: Ran 18, OK
- `-p "test_auto_core_risk1r.py"`: GOLDEN 갱신 전 1건 실패(5키 차이, 위 표 값) → 갱신 후 대상 묶음에서 통과
- `-p "test_auto_core*"`: Ran 460, failures 1, skipped 1. 실패 1건 =
  `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')`
  (`CARD_SECTION_CHANGED`, `CARD_NOT_ACCEPTED_IN_WATCHLIST`). 실제 docs/claude/card-evidence-registry.json·카드·
  watchlist를 auto_core_inputs로 읽는 자료 검사이고, 이번에 바꾼 파일·함수를 거치지 않는다. 이번 변경이 만든
  실패가 아니라고 판단하지만 base에서 같은 실패인지는 이 세션에서 재지 못했다(git stash 등 금지) — 파이프라인
  기준선 비교로 확인 필요.
- 전체 `-p "test_*.py"`: Ran 3247, failures 21, errors 9, skipped 3. 위 PLTR 1건 밖의 29건은
  test_v2_6_7_session_aware_kiwoom_priority(acceptance manifest 0건), test_materialize_kiwoom_session_aware_acceptance_candidate,
  test_instrument_identity_authority, test_materialize_instrument_identity_artifact, test_evaluate_timing_integration,
  test_portfolio_decision_dashboard, test_portfolio_decision_order_intent, test_scheduled_prompt_kiwoom_profile,
  test_nbis_v3_shadow_activation, test_nbis_v4_kiwoom_price_authority, test_validate_research_packet,
  test_holding_baseline_observation_audit·test_mvll_canonical_volume_lineage·test_provider_limitation_audit(setUpClass)에
  있다. 이 파일들은 auto_core_tickets·auto_core_decide를 import하지 않는다(grep). 새 실패 0으로 판단, 기준선
  비교는 파이프라인 몫.
- 스키마 감사 `validate_schema_contracts.py`: PASS, errors []
- 줄바꿈: 고친 기존 파일 6개 모두 CRLF 유지(LF만 있는 줄 0, grep). scripts의 두 파일은 ASCII만(비 ASCII 0, grep).

## 3. 범위·불변 확인
- 바뀐 파일 7개 모두 allowed_paths 안(git status). 스키마·정책·상태·카드·등록부·CONSTANTS·POLICY_EXPECTED·SIZING 불변.
- 회로·요건·관문·수량·가격·후보·결과 분류(`order_days`·`ticket_rows`·`session_close`) 코드 수정 없음.
  GoldenCauseTests에서 enterWindow를 뺀 뷰가 이전과 같다.
- enterWindow는 늘 1자 이상 문자열(스키마 그대로, 결정 스키마 검사 통과).
- docs/claude/t2rc-oracle.py는 enterWindow·enter_window·next_action_for_user를 읽지 않는다(grep 0건) → t2-rc C1 셈 영향 없음.
- 키움 호출·주문 경로·권한 표지 변경 없음. auto_core.py를 실행하는 명령 없음.

## 4. 남은 위험
- 겨울 18:00은 사용자 사실의 예상치다. 11/3(첫 겨울 세션) 실제 키움 접수 시작으로 확인 필요.
- 알림 지시문 docs/claude/scheduled-prompts/auto-core-alert.txt read.py의 확인 대기 문구
  `n='주문표 %d건 — 저녁 키움 입력 …'`은 예약 지시문이라 이 작업 범위 밖이다(그대로 "저녁").
- 개장일이 발행일보다 앞서는 입력에 대한 fail closed 처리는 원래 없었고 더하지 않았다(1-1).
- 위 PLTR 등록부 실패와 전체 묶음의 29건이 base에도 있는지는 파이프라인 기준선으로 확인 필요.
