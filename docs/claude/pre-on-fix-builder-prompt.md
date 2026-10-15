---
id: pre-on-fix-builder-prompt
title: "켜" 전 코어 수정 3건 — ④ 휴장 날 중복 입력 문구 · ① r4 E 창 끝 마감 뒤 행 · ⑥ G0_TICKET_SESSION_NOT_YET 예외 알림
date: 2026-10-15
class: 권한 경로(auto_core*.py, tests/test_auto_core*.py) — dev-run class authority(경로 때문). 의미: 일반 변경(표시 문구·결과 분류 창·예외 알림). 관문 기준값·상수·회로·요건·수량·가격 불변
decision: 사용자 "결정 pre-on-fix: a"(2026-10-15 16:32 KST, Cowork 대화) — 근거 docs/claude/pre-on-roadmap-review-2026-10-15.md 1절, 요건 docs/claude/redesign-t2-judge2-report-2026-10-11.md G절 "켜" 전 1·4·6(:168, :171-175, :177)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 pre-on-fix -ApproveAuthority — 경로 때문에 붙는 플래그)
---

```dev-run
{"task_id": "pre-on-fix", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 50, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_t1_safety.py", "manage-us-stock-strategy/tests/test_auto_core_preon_fix.py", "docs/claude/pre-on-fix-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): no-new-session entry text names the issue day (no re-entry), F6 last order day cut at session close, G0 ticket-session-not-yet exception alert"}
```

## 배경
T2 "켜"(decision_mode apply) 전에 고칠 항목 3건이다(redesign-t2 Judge 2차 G절). 지금은 비교 모드라 셋 다 실제 주문에 영향이 없다. 독립 계산기 docs/claude/t2rc-oracle.py는 next_action·alerts를 읽지 않는다. G0는 코어의 outcomes를 그대로 쓴다(:1833-1834). 그래서 이 변경은 t2-rc C1 셈에 영향이 없어야 한다. 아래 "지켜야 할 것"이 그 조건이다.

## 바꿀 것 (세 가지만)

1. **④ 새 세션 없음 날 입력 문구**(auto_core_decide.py `_no_new_session`, :939-940 근처)
   - 지금: apply 모드에서 넘어온 주문표가 있으면 next_action_for_user = "주문표 N건 — 저녁 키움 입력"이다. 같은 주문표를 발행일 저녁에 이미 넣었는지 알 수 없다. 그날은 미체결 조회도 하지 않으므로 중복 입력을 표시로만 막을 수 있다(judge2 :171-175).
   - 바꿀 내용: 그 문구에 다음을 넣는다.
     - (a) 이것이 <발행 KST 날짜>에 나간 같은 주문표라는 것. 넘어온 주문표의 issued_day를 쓰고, 날짜가 여럿이면 모두 쓴다.
     - (b) "이미 입력했으면 다시 넣지 않음".
     - (c) 아직 넣지 않았을 때만 저녁 키움 입력.
     - 예: `주문표 1건 — 11/26 발행분과 같은 주문표: 이미 입력했으면 다시 넣지 않음(안 넣었으면 저녁 키움 입력)`.
     - 문구는 한 줄이다. 알림 ⑩(docs/claude/scheduled-prompts/auto-core-alert.txt:125)이 그대로 보낸다.
   - 같은 날 dashboard.runCore.tickets의 해당 항목에 같은 뜻의 짧은 표지 필드를 하나 더해도 된다(예: `"carried": {"issued_day": "...", "note": "이미 입력했으면 다시 넣지 않음"}`). dashboard.orders 행은 바꾸지 않는다. 알림 4c(:83)가 이미 있는 orders 문서를 바꾸지 않아서 효과가 없기 때문이다.
   - 새 세션이 있는 날의 문구(:798 "주문표 N건 — 저녁 키움 입력")는 그대로다.
2. **① r4 E — 창 끝 날짜의 마감 뒤 행**(auto_core_tickets.py `ticket_rows`, :531-573)
   - 지금은 발행일 하한(ord_time ≥ 발행 시각)만 있다. 그래서 끝 날짜(그 주문표 세션 정규장 마감의 KST 날짜, `order_days` :509-522)에 마감 뒤(D+1 05:00~07:45 KST 등)에 따로 넣은 같은 종목·방향 주문이 그 주문표의 결과로 분류된다(judge2 :168).
   - 바꿀 내용: 끝 날짜 행은 ord_time ≤ 그 세션 core_close_at의 KST 시각인 것만 쓴다(조기 마감이면 그 시각, 예: 03:00 KST). 마감 시각은 calendar의 같은 행에서 읽는다.
     - ticket_rows가 calendar를 받지 않으면 호출부(auto_core_decide.py `read_outcomes`, :290-345 근처)에서 마감 시각을 넘겨준다.
     - 끝 날짜 행의 ord_time을 못 읽으면 발행일과 같이 결과 unknown이다(note `ORD_TIME_UNREADABLE`, fail closed).
     - 마감 시각을 못 구하면 `ORDER_WINDOW_UNKNOWN`과 같은 처리다.
     - 발행일과 끝 날짜가 같은 날이면 두 경계를 모두 적용한다.
   - 결과 상태 이름은 새로 만들지 않는다(filled·partial·unfilled·not_entered·changed와 기존 unknown/note만). 계산기 CLASSIFIED(:1233)와 맞춘다.
3. **⑥ G0_TICKET_SESSION_NOT_YET 예외 알림**(auto_core_decide.py :329 → gate0 :698 → HOLD :771-773)
   - 지금: 이 이상 상태는 HOLD 사유로만 남는다. exceptions 목록(:683-760)에 없으므로 push가 없다(judge2 :177).
   - 바꿀 내용: outcome_block reasons에 `G0_TICKET_SESSION_NOT_YET:`가 있으면 exceptions에 한 줄을 더한다. `("G0_TICKET_SESSION_NOT_YET", "주문표 세션 이전 상태 — 새 주문표 없음, Cowork 확인")`. 다른 예외와 같이 push True다.
   - 관문(gate0)·HOLD 동작은 그대로다. 새 세션 없음 날(`_no_new_session`)에는 이 사유가 생기지 않으므로 그 경로는 바꾸지 않는다.

## 테스트
새 파일 `manage-us-stock-strategy/tests/test_auto_core_preon_fix.py`(기존 test_auto_core_decide·tickets의 도우미 방식을 따른다). 항목마다 최소 2개를 쓴다.
- **④:**
  - apply 모드 새 세션 없음 날, 넘어온 주문표 1건 → next_action_for_user에 발행일·"이미 입력했으면 다시 넣지 않음"이 있다.
  - 발행일이 다른 2건 → 두 날짜가 모두 나온다.
  - compare 모드 → None 그대로.
  - 새 세션 있는 날 문구 → 지금과 같다.
- **①:**
  - 끝 날짜 05:30 KST 행(여름 마감 05:00) → 제외되어 not_entered/unfilled 쪽으로 분류된다.
  - 04:59 행 → 포함.
  - 조기 마감(03:00) 날 03:30 행 → 제외.
  - 끝 날짜 ord_time 못 읽음 → unknown(ORD_TIME_UNREADABLE).
  - 발행일 하한 동작 → 지금과 같다.
- **⑥:**
  - 넘어온 주문표 세션 > 평가 세션인 새 세션 날 → status HOLD, reasons 유지, alerts에 code G0_TICKET_SESSION_NOT_YET push True.
  - 그 사유가 없는 날 → 그 알림 없음.

고칠 수 있는 기존 테스트:
- 위 의미 때문에 문구·고정 자료가 맞지 않게 된 기존 테스트(예: test_auto_core_decide.py :809·:921·:1119 근처의 새 세션 없음 테스트, t1_safety의 F6 행 테스트)는 **기대 문구·고정 자료 값만** 고친다. 고친 곳마다 보고서에 파일:행·전후·이유를 적는다.
- 골든·불변 테스트(test_auto_core_risk1r GOLDEN 8개 키, test_auto_core_compare_fix T5 불변)는 바뀌면 고치지 않는다. 바뀌면 원인을 보고서에 적고 그 회차는 BLOCKED로 둔다.

## 지켜야 할 것 (C1 영향 0 조건)
- allowed_paths 밖은 건드리지 않는다. 규칙 파일·카드·등록부·정책·상태·스키마·CONSTANTS·POLICY_EXPECTED·관문 기준값 불변. 회로·요건·관문·수량·가격·후보 계산은 바꾸지 않는다.
- 새 세션 없음 날에 S7 검토나 다른 입력 파일을 새로 쓰지 않는다. 지금 그날 쓰는 파일 목록을 바꾸지 않는다(계산기가 그날을 NOT_CHECKED로 두는 전제, t2rc-oracle.py :1294-1306).
- decision.json의 candidates·tickets·buy_requirements·symbols·evidence·outcomes 스키마와 값은 ①의 분류 결과 말고는 바꾸지 않는다. 스키마 파일을 고칠 필요가 생기면 BLOCKED다.
- 키움 호출·주문 경로·권한 표지 없음. auto_core.py를 실행하는 명령은 쓰지 않는다(테스트는 `-p "test_auto_core*"`).
- docstring·주석은 ASCII만 쓴다(test_language_contract). 한국어 문구는 기존처럼 \u 이스케이프로 쓴다.
- CRLF 파일의 줄 끝을 바꾸지 않는다.

## 보고 `docs/claude/pre-on-fix-report.md`
- 바꾼 줄(파일:행)과 항목별 새 동작 한 문단
- 새 테스트 목록, 고친 기존 테스트(값·이유)
- 대상·전체 테스트 결과(Ran 수, 새 실패 0), 골든 8키 불변 확인
- 남은 위험

## Judge 확인 항목
1. 범위: allowed_paths 안이고, 바뀐 의미는 위 세 가지뿐이다. 회로·요건·관문·수량·가격·후보 계산과 스키마는 불변이다.
2. ④: apply 모드 새 세션 없음 날에만 발행일·"이미 입력했으면 다시 넣지 않음"이 나온다. compare 모드와 새 세션 날 문구는 불변이다. dashboard.orders 불변, 그날 새 입력 파일 쓰기 없음.
3. ①: 끝 날짜 행은 세션 core_close_at KST 시각 이하만 쓴다. 못 읽으면 unknown(fail closed)이다. 결과 상태 이름 추가 없음. 발행일 하한 불변.
4. ⑥: G0_TICKET_SESSION_NOT_YET이면 예외 알림 push True. gate0·HOLD 불변.
5. 골든 8키·T5 불변 테스트 불변. 권한 표지·주문 경로·정책/상태 쓰기·키움 호출 없음. 대상·전체 테스트 새 실패 0.
