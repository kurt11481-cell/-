---
id: enter-window2-builder-prompt
title: 주문표 입력 시작 표시 — 주말·겨울 프리마켓 시작에 맞춤 (enterWindow · 입력 안내 문구)
date: 2026-10-20
class: 권한 경로(auto_core*.py, tests/test_auto_core*.py) — dev-run class authority(경로 때문). 의미: 일반 변경(표시 문구만). 관문 기준값·상수·회로·요건·수량·가격·결과 분류 불변
decision: 사용자 "결정 enter-window: a"(2026-10-20 19:35 KST, Cowork 대화). 근거 사실(사용자 2026-10-20 19:22·19:26·19:29 KST): ① 키움 미국 LOC 접수 = 프리마켓 시작 ~ 정규장 마감(NASDAQ 마감 5분 전 접수 불가·10분 전 정정·취소 불가, NYSE 2분) ② 금요일 세션(토 새벽 마감)까지는 평일과 같고, 토 아침 ~ 월요일 프리마켓 시작 전은 접수 불가 ③ 주간거래(데이장)는 회사 거래시간에서 뺀다. 기록 docs/claude/order-receipt-process-review-2026-10-09.md 4절
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음
retry_of: enter-window (BLOCKED 2026-10-20 10:49Z — 기대 문구가 allowed_paths 밖 tests/test_auto_core_preon_fix.py :38-41에 있음, Builder BLOCKED.md a안 채택)
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 enter-window2 -ApproveAuthority — 경로 때문에 붙는 플래그)
---

```dev-run
{"task_id": "enter-window2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_enter_window.py", "manage-us-stock-strategy/references/auto-core-decision.md", "manage-us-stock-strategy/tests/test_auto_core_preon_fix.py", "docs/claude/enter-window2-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): ticket entry window starts at the session-day pre-market open (weekend, winter)"}
```

## 배경
주문표의 입력 안내가 키움 접수 시간과 어긋난다. 지금은 비교 모드라 실제 주문 영향은 없고, T2 "켜" 전에 고친다. 독립 계산기 docs/claude/t2rc-oracle.py는 enterWindow·next_action_for_user를 읽지 않는다(2026-10-20 grep 결과 0건). 그래서 이 변경은 t2-rc C1 셈에 영향이 없어야 한다.

어긋나는 곳(2026-10-20 커밋 4fe10b3 기준 행):
1. `auto_core_tickets.py` `enter_window`(:826-836): 시작을 "발행 KST 날짜 17:00"으로 고정한다.
   - 토요일 07:45 주문표(월요일 세션)는 "한국 10/17 17:00 이후 ~ 10/19 22:30 개장 전"이 된다(테스트 test_auto_core_tickets.py:772). 10/17(토)에는 접수가 안 된다.
   - 겨울(미국 서머타임 종료 뒤, 개장 23:30 KST)에는 프리마켓이 18:00 KST에 열리는데도 17:00으로 쓴다.
2. `auto_core_decide.py` :700: next_action_for_user = "주문표 N건 — 저녁 키움 입력". 날짜가 없다. 토요일 알림(⑩, docs/claude/scheduled-prompts/auto-core-alert.txt)이 이 문구를 그대로 보내므로 "오늘(토) 저녁"으로 읽힌다.
3. `auto_core_decide.py` `_carried_entry_line`(:846-863)의 "(안 넣었으면 저녁 키움 입력)"도 날짜가 없다.

## 바꿀 것

1. **입력 시작 = 세션 개장일(KST)의 프리마켓 시작.**
   - 프리마켓 시작 = 그 세션 calendar `core_open_at`(KST) − 5시간 30분.
     - 여름: 22:30 → 17:00
     - 겨울: 23:30 → 18:00(겨울 값은 사용자 사실의 예상치, 확인 필요 — 보고서에 적는다)
   - 이 값은 표시용 상수 하나(예 `PREMARKET_LEAD = timedelta(hours=5, minutes=30)`)로 둔다. 관문·CONSTANTS·POLICY_EXPECTED·auto-core-config에는 넣지 않는다. 주석에 출처(사용자 2026-10-20, 키움 LOC 접수 = 프리마켓 시작 ~ 정규장 마감)를 ASCII로 적는다.
   - 시작 = max(발행 KST 날짜의 07:45 이후, 개장일 프리마켓 시작). 실제로는 늘 개장일 프리마켓 시작이 된다. 개장일이 발행일보다 앞서면 지금처럼 fail closed 쪽을 지킨다. 지금 코드에 그 경우 처리가 없으면 보고서에 적기만 하고 동작은 바꾸지 않는다.
   - 문구:
     - 개장일 = 발행일: "한국 <M/D> <HH:MM> 이후 ~ 정규장 개장 전(<open HH:MM>)"
     - 개장일 ≠ 발행일: "한국 <open M/D>(<요일>) <HH:MM> 이후 ~ <open HH:MM> 개장 전"
     - 요일은 한국어 한 글자(월~일).
   - 끝("개장 전")은 바꾸지 않는다. 회사 운영 방식이 저녁 입력이다. LOC 접수 마감(마감 5분 전)보다 이른 안전 쪽이다.
2. **입력 안내 문구에 날짜.**
   - :700 문구를 "주문표 N건 — <M/D>(<요일>) <HH:MM> 이후 키움 입력"으로 바꾼다. 날짜·시각은 1의 입력 시작이다.
   - 주문표들의 세션이 서로 다르면(정상은 아님) 가장 이른 시작을 쓰고 보고서에 남긴다.
   - `_carried_entry_line`의 "(안 넣었으면 저녁 키움 입력)"은 "(안 넣었으면 <M/D>(<요일>) <HH:MM> 이후 키움 입력)"으로 바꾼다. 그 주문표 세션의 입력 시작을 쓰고, 못 구하면 지금 문구를 그대로 둔다(추측하지 않는다).
3. **문서.** `references/auto-core-decision.md` :160-162 "Entry window (r4)" 줄을 새 정의로 고친다.
   - 프리마켓 시작 = core_open_at − 5h30m
   - 주말·휴일은 개장일 날짜
   - 주간거래는 회사 거래시간 밖

## 테스트
새 파일 `manage-us-stock-strategy/tests/test_auto_core_enter_window.py`(기존 test_auto_core_tickets의 CALENDAR·도우미 방식을 따른다).
- 평일 여름: 발행 10/14, 세션 10/14 → "한국 10/14 17:00 이후 ~ 정규장 개장 전(22:30)"(지금과 같음)
- 토요일 여름: 발행 10/17, 세션 10/19 → 시작이 10/19(월) 17:00
- 휴일 다음: 기존 test_tuesday_after_a_holiday 자료 → 시작이 개장일 날짜
- 겨울: 개장 23:30 KST 세션 → 시작 18:00(발행일 = 개장일), 토요일 겨울 → 월요일 18:00
- 조기 마감 날: 개장 시각은 같으므로 시작 17:00(여름)
- :700 문구: apply 모드 새 세션 날 주문표 1건 → 날짜·시각 포함 / 토요일 → 월요일 날짜 / compare 모드 → None 그대로
- `_carried_entry_line`: 입력 시작을 구할 수 있으면 날짜 포함, 못 구하면 지금 문구

고칠 수 있는 기존 테스트:
- 문구 때문에 기대값이 바뀌는 기존 테스트는 **기대 문구만** 고친다.
  - test_auto_core_tickets.py :766-790 근처 enterWindow
  - test_auto_core_preon_fix.py :38-41 상수 CARRIED·NEW_SESSION_LINE: 날짜·시각 자리를 더하고 :90·:110·:127 기대값을 맞춘다. :130-131 "입력 시작을 못 구하면 지금 문구"는 그대로 둔다. 2026-10-20 1회차 Builder 확인 결과다.
  - test_auto_core_decide.py :414·:835는 assertIsNotNone만 보므로 영향이 없다.
- 고친 곳마다 보고서에 파일:행·전후·이유를 적는다.
- 골든·불변 테스트(test_auto_core_risk1r GOLDEN 8개 키, test_auto_core_compare_fix T5 불변)는 바뀌면 고치지 않는다. 바뀌면 원인을 보고서에 적고 그 회차는 BLOCKED로 둔다.

## 지켜야 할 것
- allowed_paths 밖은 건드리지 않는다. 규칙 파일·카드·등록부·정책·상태·스키마·CONSTANTS·POLICY_EXPECTED·관문 기준값은 그대로다.
- 회로·요건·관문·수량·가격·후보 계산·결과 분류(`order_days`·`ticket_rows`·`session_close`)는 바꾸지 않는다. 토·일이 order_days에 들어가는 것도 그대로 둔다(분류 영향 없음, 2026-10-20 재검토).
- enterWindow는 스키마상 문자열 1자 이상이다. 스키마 파일은 고치지 않는다(고칠 필요가 생기면 BLOCKED).
- 키움 호출·주문 경로·권한 표지 없음. auto_core.py를 실행하는 명령은 쓰지 않는다(테스트는 `-p "test_auto_core*"`).
- docstring·주석은 ASCII만 쓴다(test_language_contract). 한국어 문구는 기존처럼 \u 이스케이프로 쓴다.
- CRLF 파일의 줄 끝을 바꾸지 않는다.

## 보고 `docs/claude/enter-window2-report.md`
- 바꾼 줄(파일:행)과 항목별 새 동작 한 문단
- 새 테스트 목록, 고친 기존 테스트(값·이유)
- 대상·전체 테스트 결과(Ran 수, 새 실패 0), 골든 8키 불변 확인
- 남은 위험: 겨울 18:00은 11/3 첫 겨울 세션에 확인. 알림 지시문의 확인 대기 문구(auto-core-alert.txt read.py `n='주문표 %d건 — 저녁 키움 입력 …'`)는 예약 지시문이라 이 작업 범위 밖이다.

## Judge 확인 항목
1. 범위: allowed_paths 안이고, 바뀐 의미는 표시 문구 셋(enterWindow 시작, :700 안내, carried 안내)과 문서 한 줄뿐이다. 회로·요건·관문·수량·가격·결과 분류·스키마는 그대로다.
2. 입력 시작 = 개장일 core_open_at − 5h30m이다. 토요일 주문표는 월요일 날짜, 겨울은 18:00이다. 끝 "개장 전"은 그대로다. 상수는 표시용이고 관문·설정에 쓰이지 않는다.
3. :700·carried 문구에 입력 시작 날짜·시각이 있다. 못 구하면 추측하지 않고 지금 문구를 쓴다. compare 모드에서는 None이다.
4. 골든 8키·T5 불변 테스트는 그대로다. 권한 표지·주문 경로·정책/상태 쓰기·키움 호출 없음. 대상·전체 테스트 새 실패 0.
