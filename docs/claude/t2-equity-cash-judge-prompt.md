---
id: t2-equity-cash-judge-prompt
title: t2-equity-cash 독립 Judge (읽기 전용)
date: 2026-10-13
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — Builder 세션과 다른 세션
---

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 쓰는 파일은 맨 끝의 보고서 1개뿐이다.

## 읽을 것

1. 지시문: docs/claude/t2-equity-cash-builder-prompt.md (메인 체크아웃)
2. Builder 보고: .claude/worktrees/t2-equity-cash/docs/claude/t2-equity-cash-report.md
3. 변경: 메인 체크아웃과 worktree의 같은 경로 파일 비교
   - manage-us-stock-strategy/scripts/auto_core_decide.py
   - manage-us-stock-strategy/scripts/auto_core_tickets.py
   - 새 파일 .claude/worktrees/t2-equity-cash/manage-us-stock-strategy/tests/test_auto_core_equity_cash.py
   - worktree `git status`로 바뀐 파일이 이 4개(코드 2 + 테스트 + 보고서)뿐인지 확인
4. 근거 코드: manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py `order_available_cash_errors`, auto_core_rules.py `v6_account`·`ev4_open`, auto_core_replay.py의 `evaluate_session` 호출

## 돌려도 되는 것

- worktree 안에서: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` (Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되니 이 패턴으로만).
- 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지. 커밋·병합 금지.

## 판정 항목 (지시문 "Judge 확인 항목" 1~6 + 아래)

1. 바뀐 파일·줄이 지시문 범위뿐. 관문 기준값(rules.C)·주문표 수량/가격·S7·대조 모듈·G1 대조·리플레이 불변.
2. `equity_cash`: 가드 통과 → 주문가능, 실패·누락 → 알려진 값의 최솟값, 모두 없음 → None. 가드는 kiwoom_broker_shadow에서 import(복제 없음). 가격으로 추정한 금액 없음.
3. 2026-10-13 값(총자산 27,695.15·N 1.2466·EV4 없음·V6 none)이 함수를 거친 계산으로 확인된다.
4. 매수 결제 전 이중 계산 없음(T3), 미결제 없을 때 결과 불변(T4·T6).
5. 권한 표지(order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY) 줄·주문 경로·정책/상태 쓰기 없음, 키움 호출 없음, 커밋 없음.
6. 대상 테스트 통과(새 실패 0).
7. 추가: 바뀐 상태 문자열 CASH_UNAVAILABLE를 읽는 곳이 깨지지 않았나. runCore 출력 키가 그대로인가(cash_basis 미포함). 결정 스키마(exposure)가 새 칸을 받아들이나.
8. 추가: Builder 보고 6절 위험 1(낮게 잡힌 날의 EV4가 ev4_sessions에 남아 며칠 매수를 막음)이 변경 전보다 나빠지지 않았나(변경 전에는 매도 다음 날마다 같은 일이 생겼다) — 의견만.

## 출력

- 한국어 표 `| 항목 | PASS/FAIL | 근거(파일:줄) |`, 고칠 최소 항목(있으면), 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
- 같은 내용을 **새 파일 하나** `docs/claude/t2-equity-cash-judge-report-2026-10-13.md`(메인 체크아웃)에 저장한다. 그 밖의 파일은 쓰지 않는다.
