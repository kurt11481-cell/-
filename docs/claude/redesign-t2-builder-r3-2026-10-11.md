---
id: redesign-t2-builder-r3-2026-10-11
title: 재설계 T2 Builder 추가 지시 r3 — 결과 분류의 날짜 창·휴장일 (r2 보고 "새로 찾은 사실" A·B)
date: 2026-10-11
from: .claude/worktrees/t2-core/docs/claude/redesign-t2-builder-report-2026-10-10.md "# r2" 끝 "새로 찾은 사실" A·B (Cowork 판단: 지시문 F6의 날짜 정의가 틀렸다 — 지시문 쪽 결함이라 사용자 결정 없이 고친다)
class: T2와 같음(권한·한도 변경). 범위·금지는 docs/claude/redesign-t2-builder-prompt-2026-10-10.md 4절 그대로
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: T2 Builder(같은 worktree t2-core) · T2 Judge 2차(r2 + r3 변경분) · 관제판 redesign-t2
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 기존 worktree `t2-core`에서 새 Claude Code 세션 · 이유: Judge 2차 전에 같은 범위의 작은 수정 하나를 묶는다**

## 사용자 조작 (Windows PowerShell, 한 번)
```
cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\t2-core"
claude --model opus --effort xhigh
```
첫 메시지로 이 한 줄만:
```
Read ../../../docs/claude/redesign-t2-builder-r3-2026-10-11.md and do sections 1-3 exactly.
```
끝나면 Cowork에 "T2 r3 완료"만 보낸다.

## 0. 왜

r2 보고가 찾은 A는 지시문 F6의 결함이다. "주문일 = 발행 KST 날짜와 그다음 날"은 평일 주문표에만 맞는다. 토요일 07:45에 나온 주문표(세션 = 미국 월요일)는 사용자가 월요일 저녁(KST)에 입력하므로 주문일이 월요일이고, 화요일 실행이 토·일만 조회해 **매주 미입력으로 잘못 센다**. 미국 월요일 휴장이면 화요일 실행이 세션이 열리기도 전의 주문표를 분류한다. 기록 모드에서는 둘 다 R-NE1(연속 미입력 2회 → 결정 닫힘)을 틀리게 만든다. B(새 세션이 없는 날 R2-5 규칙으로 HOLD + rerun 파일 + 다음 날 누락 알림)도 같은 원인이다. 사용자 결정이 필요한 정책이 아니라 날짜 계산 결함이라 이번에 고친다.

## 1. 고칠 것

```
R3-1 분류 시점: 주문표는 그 세션이 끝난 뒤에만 분류한다
 - ticket.session ≤ 이번 평가 세션일 때만 F6 분류. 아니면 그 주문표는 열린 채 이어 간다(분류·원장 변경·일지 없음).
 - 열린 주문표가 아직 세션 전이면 G0는 그날 새 주문표를 막는다(같은 결정의 중복 발행 방지 — 설계 G0 "남은 미체결 주문이 없거나 지시서에
   반영됨"). 사유 G0_TICKET_SESSION_NOT_YET.

R3-2 주문일 조회 창: 발행 KST 날짜 ~ 그 세션이 끝나는 KST 날짜
 - 세션 S(미국 날짜)의 주문은 발행일 D(KST)부터 S 마감(KST로 S 다음 날 새벽, 여름 05:00·겨울 06:00, 조기 폐장은 운영 달력의 core_close_at)까지 들어올 수
   있다. ust21150은 D부터 "S 마감 시각의 KST 날짜"까지 모든 날짜를 조회한다(빈 날은 측정된 "자료 없음" 0건 그대로).
 - 예: 토요일 10/17 발행·세션 미국 10/19(월) → 10/17·10/18·10/19·10/20 조회. 평일 D 발행·세션 D → D·D+1(지금과 같음).
 - 창 안의 조회 하나라도 실패하면 OUTCOME_UNKNOWN(지금 규칙 그대로).

R3-3 새 세션이 없는 날(미국 휴장 다음 실행 등)
 - 이번 평가 세션 = 원장 출처 기록(f6_ran = true인 가장 최근 기록)의 평가 세션이면: status OK, no_new_session true, 주문표 0, 일지 쓰기 0,
   원장·미분류 주문표는 출처에서 그대로 이어받고(carried_from), F6는 R3-1 규칙대로만(대개 분류할 것 없음), 대조 연속 일수는 그대로 유지
   (통합 점검도 같은 세션이라 새 판정 아님), push 없음. 그날 decision.json은 정상으로 쓴다(다음 날 ⑪ 누락 알림이 나지 않게).
 - R2-5(같은 평가 세션의 core_decision이 이미 있음)는 같은 run_day 재실행에만 적용한다. 다른 run_day에서 같은 평가 세션이면 R3-3이 먼저다.
 - f6_ran은 R3-3 날에도 true(분류할 것이 있었다면 했으므로)로 둔다 — 이어받기 출처가 계속 이어지게.

R3-4 리플레이: R3-1·R3-2와 같은 함수를 쓴다(리플레이는 세션마다 독립이라 영향이 거의 없지만 복제 구현 금지).
```

테스트(가짜 자료):
- 토요일 발행(세션 = 월요일) → 월요일 KST 주문일 행이 있으면 화요일 실행에서 filled / 행이 없으면 not_entered — 조회 날짜 4개 확인.
- 월요일 미국 휴장: 토요일 발행(세션 = 화요일 미국) → 화요일 07:45 실행은 no_new_session, 주문표 열린 채, 일지 0, 새 주문표 0, push 0, decision.json 있음 → 수요일 실행에서 분류.
- 평일 발행은 지금과 같은 두 날짜.
- 같은 run_day 재실행은 R2-5 그대로(기존 테스트 통과).
- 조기 폐장 세션의 마감 KST 날짜 계산.

## 2. 지켜야 할 것

- 1차 Judge PASS 항목과 r2 변경을 깨지 않는다. 기존 테스트 약화 0, 테스트 수 감소 0, 대상 테스트 OK, 전체 스위트 실패 줄 = 기준선 28줄과 같은 id.
- 스크립트 ASCII(한국어 문구는 \uXXXX), 줄바꿈 원본 유지, 스키마 감사 PASS(decision 스키마에 no_new_session 추가), 키움 실제 호출 0.

## 3. 보고

docs/claude/redesign-t2-builder-report-2026-10-10.md 끝에 "# r3" 절: 요약(BLOCKED 여부·바뀐 파일·테스트 수·전체 스위트), R3-1~4 바꾼 곳(파일:함수)·테스트 이름, r2 "새로 찾은 사실" A·B 아래에 "해결(r3):" 줄, 새로 고른 것과 이유.
