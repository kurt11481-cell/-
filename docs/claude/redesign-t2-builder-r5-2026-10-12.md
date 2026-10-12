---
id: redesign-t2-builder-r5-2026-10-12
title: 재설계 T2 Builder r5 — P-2(PWR·LITE 정책 등록)에 맞춘 테스트 2개 (테스트만)
date: 2026-10-12
from: docs/claude/redesign-t2-merge-decision-2026-10-12.md "P-2 보류 이유" (사용자 2026-10-12 11:34 KST "매수 주문표 막힘을 해결하라")
class: 테스트만 수정. 운영 코드·스키마·정책·상태 변경 0. P-2 정책 반영은 Cowork가 사용자 승인(11:21)으로 이미 했다
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: T2 Builder(같은 worktree t2-core) · Cowork(diff·변이 확인 → 병합 스크립트) · 관제판 redesign-t2
---

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: medium · 세션: 기존 worktree `t2-core`에서 새 Claude Code 세션 · 이유: 테스트 2개의 기대값·입력만 바꾸는 작은 수정**

## 사용자 조작 (Windows PowerShell, 한 번)
```
cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\t2-core"
claude --model sonnet --effort medium
```
첫 메시지로 이 한 줄만:
```
Read ../../../docs/claude/redesign-t2-builder-r5-2026-10-12.md and do sections 1-3 exactly.
```
끝나면 Cowork에 "T2 r5 완료"만 보낸다.

## 0. 왜

- 사용자가 P-2를 승인했다(2026-10-12 11:21 KST).
- Cowork가 이 worktree의 `stock-strategy-system/alert_policy.json`에 P-2를 반영했다(sha256 98ef14e0dfe1…). 바뀐 줄은 둘이다.
  - `nominal_multipliers`에 `"PWR": 1, "LITE": 1`
  - `card_stock_core`에 `"PWR", "LITE"`
- 그 뒤 전체 스위트에서 새로 실패하는 테스트는 아래 2개뿐이다(Cowork 실측: P-2 있음/없음 두 사본 대조). 둘 다 실제 정책 파일을 읽는다.
  1. `test_portfolio_exposure.PolicyValueTests.test_real_policy_carries_the_fixed_r2_values`: 실제 정책의 배수를 고정한 테스트.
  2. `test_auto_core_tickets.BuyTicketTests.test_policy_unregistered_instrument_has_no_ticket`: PWR이 실제 정책에 없다는 전제.

## 1. 고칠 것 (테스트 파일만)

```
R5-1 tests/test_portfolio_exposure.py · PolicyValueTests.test_real_policy_carries_the_fixed_r2_values
 - 기대 배수에 "PWR": 1, "LITE": 1을 더한다(다른 값은 그대로).
 - 같은 테스트에 card_stock_core == ["BE", "MU", "NBIS", "DELL", "AMD", "PWR", "LITE"] 단언을 더한다(정책 고정 범위를 넓힘, 약화 아님).

R5-2 tests/test_auto_core_tickets.py · BuyTicketTests
 - test_policy_unregistered_instrument_has_no_ticket: 실제 정책에 기대지 않게 한다. Scenario를 만든 뒤 run() 전에
   scenario.policy["portfolio_exposure_policy"]의 card_stock_core와 nominal_multipliers에서 PWR을 뺀다(테스트 안의 사본만).
   단언은 그대로(PWR 주문표 0, 사유 POLICY_UNREGISTERED_INSTRUMENT).
 - 새 테스트 test_registered_instrument_is_not_blocked_by_policy_registration: 같은 Scenario에서 PWR을 사본 정책에
   (없으면) 등록한 뒤 run() → PWR 매수 막힘 사유에 POLICY_UNREGISTERED_INSTRUMENT가 없고, PWR 매수 주문표가 1건 나온다.
   이 Scenario에서 다른 관문 때문에 주문표가 안 나오면 억지로 맞추지 말고 "막힘 사유에 POLICY_UNREGISTERED_INSTRUMENT 없음"만 단언하고 보고에 적는다.
```

## 2. 지켜야 할 것

- 바꾸는 파일은 위 테스트 2개와 보고 1개뿐이다.
  - scripts·schemas·references·등록부·정책·상태·일지·.claude·CLAUDE.md·tools는 0줄이다.
  - `stock-strategy-system/alert_policy.json`과 `workspace/policies/auto_core.json`은 Cowork가 바꾼 상태 그대로 두고 되돌리지 않는다.
- 기존 단언은 삭제·완화하지 않는다. 테스트 수가 줄면 안 된다. 키움 실제 호출은 0이다. 줄바꿈은 원본을 유지한다.
- 실행할 것:
  - `-p "test_auto_core*"`, `-p "test_portfolio_exposure*"`, `-p "test_run_portfolio_exposure_review*"`, `-p "test_portfolio_status*"`: 모두 OK여야 한다.
  - 전체 스위트(test-runner): 실패 id 집합이 기준선 28줄(r4 보고)과 같아야 한다. 원본 로그에서 직접 센다.
- 커밋하지 않는다(병합은 Cowork 스크립트가 한다).

## 3. 보고

docs/claude/redesign-t2-builder-report-2026-10-10.md 끝에 "# r5" 절을 쓴다.
- 요약: BLOCKED 여부, 바뀐 파일, 테스트 수, 전체 스위트 결과
- R5-1·R5-2에서 바꾼 곳(파일:테스트 이름)
- 새 테스트가 주문표 1건까지 단언했는지 여부
- 새로 찾은 사실(고치지 않음)
