---
id: redesign-t2-claude-md-proposal-2026-10-12
title: 재설계 T2 배포 8절 5 — CLAUDE.md 문구 제안(주문 1단계·일지 자동·연구 기록)
date: 2026-10-12
base: CLAUDE.md sha256 d02538b23acb…(106줄)
status: 적용됨 — 사용자 "결정 redesign-t2: CLAUDE.md 승인"(2026-10-12 13:31 KST), Cowork가 3곳 반영(CLAUDE.md 106→115줄, sha256 2d2f914cc31b…), 커밋은 사용자 한 줄
authority: 문구만. 권한 변경은 사용자 결정 A7 a(주문 1단계)와 T2 병합(756e43e)으로 이미 정해진 것을 적는 것
---

## 바꿀 곳 3군데 (영문 원문 그대로 붙일 문장)

1. 맨 위 두 줄 뒤에 추가:
```
Order stage 1 (user decision A7 a; redesign T2 merged 2026-10-12): the auto-core decide run issues LOC order tickets
(quantity_authority "ORDER_TICKET_HUMAN_ENTRY", tickets only) that the user enters in Kiwoom; everything else keeps
quantity_authority "none" and execution_quantity null. While decision_mode is compare (until the user's "켜"), tickets
are labeled 비교 중 and are not entered.
```
2. Hard safety의 일지 줄: `portfolio_review_journal.py` (later the auto-core). → `portfolio_review_journal.py`, or by the auto-core decide run in recording mode only (decision_mode apply; entries core_decision, order_ticket, ticket_outcome with AUTO_CORE).
3. Hard safety 끝("Deterministic rules outrank LLM output." 다음 줄)에 추가:
```
- The only LLM input to the auto-core is the research record written by the 06:40 integrated check
  (workspace/outputs/research-records/<KST date>/research-record.json, schema auto-core-research-record). A missing or
  invalid record blocks every buy ticket, never sells. A Cowork session that changes or accepts a card updates
  docs/claude/card-evidence-registry.json in the same session (otherwise that symbol gets no ticket).
```

## 커널 지침(프로젝트 지침) 2절 — 선택, 사용자가 붙여 넣음

"켜"(기록 모드) 전에 붙이기를 권한다. 비교 모드에서는 주문표를 입력하지 않으므로 지금 충돌은 없다.
```
주문 1단계(사용자 결정 A7 a, T2 2026-10-12): 자동 운영 코어 주문표에만 quantity_authority=ORDER_TICKET_HUMAN_ENTRY(사용자가 키움에 직접 입력). 그 밖은 quantity_authority=none·execution_quantity=null 그대로. 비교 모드 주문표는 입력하지 않는다.
```
