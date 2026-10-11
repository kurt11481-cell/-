---
id: redesign-t2-builder-r4-2026-10-11
title: 재설계 T2 Builder 추가 지시 r4 — 주문 행 귀속 겹침(C)·입력 창 문구(D), 마지막 Builder 수정
date: 2026-10-11
from: .claude/worktrees/t2-core/docs/claude/redesign-t2-builder-report-2026-10-10.md "# r3" 끝 "새로 찾은 사실" C·D (Cowork 판단: F6 귀속 규칙의 결함과 표시 오류 — 사용자 결정 없이 고친다)
class: T2와 같음(권한·한도 변경). 범위·금지는 docs/claude/redesign-t2-builder-prompt-2026-10-10.md 4절 그대로
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: T2 Builder(같은 worktree t2-core) · T2 Judge 2차(r2~r4 변경분) · 관제판 redesign-t2
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 기존 worktree `t2-core`에서 새 Claude Code 세션 · 이유: Judge 2차 전 마지막 작은 수정**

## 사용자 조작 (Windows PowerShell, 한 번)
```
cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\t2-core"
claude --model opus --effort xhigh
```
첫 메시지로 이 한 줄만:
```
Read ../../../docs/claude/redesign-t2-builder-r4-2026-10-11.md and do sections 1-3 exactly.
```
끝나면 바로 Judge 2차를 시작해도 된다(docs/claude/redesign-t2-judge2-prompt-2026-10-11.md의 사용자 조작). Builder가 BLOCKED.md를 썼을 때만 Cowork에 먼저 알린다.

## 0. 왜, 그리고 멈춤 규칙

r3가 찾은 C는 결과 분류가 주문 행을 잘못된 주문표에 붙일 수 있는 결함이다(같은 종목·방향 주문표가 이어 나오고 사용자가 앞 주문표를 KST 자정 뒤에 입력하면, 다음 주문표가 그 행을 자기 것으로 센다). 기록 모드에서 R-NE1·재발행 집계를 틀리게 하므로 "켜" 전에 고쳐야 하고, Judge를 두 번 돌리지 않으려고 지금 묶는다. D는 토요일 주문표의 입력 창 문구가 개장일을 적지 않는 표시 오류다.

**멈춤 규칙(이번이 마지막 Builder 수정):** 이 지시 밖에서 새로 찾은 사실은 고치지 말고 보고의 "새로 찾은 사실"에만 적는다. Judge 2차와 Cowork가 "켜" 전 조건으로 정한다.

## 1. 고칠 것

```
R4-1 주문 행 귀속 (C)
 - 원장에 attributed_orders(ord_dt + ord_no 쌍 목록)를 둔다. 결과 분류가 어떤 주문표에 주문 행을 쓰면(filled·partial·unfilled·changed 모두) 그 행의
   (ord_dt, ord_no)를 attributed_orders에 넣는다. 다음 분류는 이 목록의 행을 빼고 시작한다. 원장 이어받기(ledger_carry·R3-3)에 함께 이어진다.
   보관 기간: 최근 30 달력일 주문일만 남긴다(그 밖은 어떤 주문표 창에도 들어갈 수 없다).
 - 발행일(주문표 issued_day KST)의 행은 ord_time ≥ 그 주문표 발행 시각(issuedAt의 KST 시:분:초)인 것만 쓴다. 발행 전 주문은 그 주문표에 대한 주문일 수 없다.
 - 기록 모드에서만 원장(attributed_orders)을 갱신한다(비교 모드는 지금처럼 원장 갱신 없음). 비교 모드 분류도 같은 두 규칙으로 행을 고르되 목록은
   그날 결과 안에서만 쓴다.
 - 테스트: 평일 T(세션 D) 행을 D+1 00:30 KST에 입력 → T는 D+1 실행에서 filled, D+1 발행 T′(같은 종목·방향)는 D+2 실행에서 그 행을 빼고
   not_entered / 발행일 07:00 KST 행(발행 07:45 전)은 무시 / attributed_orders 30일 정리 / 이어받기(HOLD 날을 건너도 목록 유지).

R4-2 입력 창 문구 (D)
 - enterWindow = "한국 <발행일 M/D> 17:00 이후 ~ <세션 개장 KST 날짜 M/D> <개장 KST 시각> 개장 전" — 개장 시각은 운영 달력 core_open_at을 KST로 바꾼 값
   (여름 22:30, 겨울 23:30). 발행일과 개장일이 같으면 지금처럼 날짜 하나만. fillAt은 그대로.
 - 테스트: 평일 · 토요일→월요일 · 휴장 뒤 화요일 · 겨울 시각.
```

## 2. 지켜야 할 것

- 1차 Judge PASS 항목과 r2·r3 변경을 깨지 않는다. 기존 테스트 약화 0, 테스트 수 감소 0, 대상 테스트 OK, 전체 스위트 실패 줄 = 기준선 28줄과 같은 id.
- 스크립트 ASCII(한국어 문구는 \uXXXX), 줄바꿈 원본 유지, 스키마 감사 PASS(decision 스키마에 attributed_orders 추가), 키움 실제 호출 0.

## 3. 보고

docs/claude/redesign-t2-builder-report-2026-10-10.md 끝에 "# r4" 절: 요약(BLOCKED 여부·바뀐 파일·테스트 수·전체 스위트), R4-1·R4-2 바꾼 곳(파일:함수)·테스트 이름, r3 "새로 찾은 사실" C·D 아래 "해결(r4):" 줄, 새로 고른 것과 이유, 새로 찾은 사실(고치지 않음).
