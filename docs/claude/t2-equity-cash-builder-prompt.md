---
id: t2-equity-cash-builder-prompt
title: 재설계 T2 — 판정의 총자산·노출(N)·계좌 점검선(V6)·EV4 현금을 승인된 현금 정의(키움 주문가능 + T1 가드)로
date: 2026-10-13
class: 권한·한도 변경(K3 — 매수 관문 입력의 측정 정의). 수동 경로: 이 Builder(worktree) → 별도 Judge 세션 → 사용자 병합
decision: 사용자 "결정 t2-equity-cash: 나"(2026-10-13 09:21 KST) + "결정 t2-equity-cash: 지금 진행"(13:00 KST)
evidence: docs/claude/redesign-t2-compare-b7-2026-10-13.md "재검토" 절 · docs/claude/redesign-t2-firstrun-report-2026-10-13.md
model: Opus · xhigh · 새 worktree (claude --worktree t2-equity-cash)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 관문 기준값(V6 선·EV4 비율·N 상한·종목 상한) 불변 · 주문표 수량·가격 규칙 불변 · 키움 호출 없음
weekly_user_touch: 0 (일회성: Builder 1·Judge 1·병합 1)
---

# 목표

판정(decide)이 쓰는 **총자산**을 "계좌에 속한 돈 전체"로 바로잡는다. 지금은 체결일 기준 수량(poss_qty) + **결제된 돈만**(fc_entra)이라, 매도 뒤 결제 전에는 자산이 결제 예정 매도대금만큼 낮게, 매수 뒤 결제 전에는 산 주식과 아직 안 나간 현금을 둘 다 세서 높게 잡힌다.

## 근거 (읽기 전용 확인, base = main HEAD)

- 규칙 파일 docs/claude/integrated-check-prompt-v3.12.2-2026-10-09.txt 56행 1-1 ②: "총자산·노출 계산의 USD 현금 = fc_entra(계좌에 속한 돈 전체)". 같은 줄은 fc_entra를 "외화 예수금, 정산 중 매도대금 포함"이라 적었으나, T1 F1(사용자 2026-10-09/10-10)에서 fc_entra는 **결제된 돈만**으로 확인됨: manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py 39~41행, references/broker-snapshot-reconciliation.md 101행. 승인된 현금 정의 = 키움 주문가능 `fc_ord_alowa`(kiwoom_broker_shadow.py `CASH_BASIS = "KIWOOM_ORDER_AVAILABLE_USD"`) + 가드 `order_available_cash_errors()`(같은 파일 252행 근처).
- 2026-10-13 실측(브로커 스냅샷 08:46): 외화예수금 9,396.68 = 출금가능 9,396.68, 주문가능 12,469.18(= 예수금 + D+1 매도 결제 3,072.51), SOXL settled 75 > held 53. 코어 총자산 24,622.65 → N 1.4022, V6 review, EV4 열림(10-12) / 주문가능 기준이면 27,695.15 → N 1.2466(LLM과 같음), EV4 없음.
- 코어 안 불일치: S7(portfolio_exposure)은 상태 파일 스냅샷 현금(= 주문가능 정의)을 쓰고, 판정 매수 현금(auto_core_decide 476행 `cash`)도 주문가능인데, 규칙 파일 N·V6·EV4만 `deposit`(fc_entra)을 쓴다: auto_core_decide.py 477행 → 817행 `tickets_module.rule_file_nominal(holdings, closes_raw, deposit, multipliers)` → 818행 `rules.v6_account(nominal.get("total"))` → 867행 `rules.ev4_open(nominal.get("total"), ...)`.

# 바꿀 것

1. **총자산용 현금 선택 함수 1개**(auto_core_decide.py 또는 auto_core_tickets.py, 순수 함수, Decimal):
   - 입력: 브로커 스냅샷의 cash(`order_available_cash`, `withdrawable_cash`, `foreign_currency_deposit`)와 holdings 행의 (`settled_quantity`, `held_quantity`).
   - 가드: kiwoom_broker_shadow.order_available_cash_errors(order_available, withdrawable, [(settled, held), ...])를 **그대로 import해서** 쓴다(복제 구현 금지). 오류가 없으면 → (주문가능, `"ORDER_AVAILABLE"`).
   - 가드 실패 또는 값 누락이면 → (**세 값 중 알려진 것의 최솟값**, `"MIN_FALLBACK:<사유 코드>"`). 매도 결제 전이면 예수금, 매수 결제 전이면 주문가능이 최솟값이 되어 어느 쪽이든 자산을 부풀리지 않는다(매수 쪽으로 보수적). 세 값이 모두 없으면 (None, `"CASH_UNAVAILABLE"`) — 지금의 `DEPOSIT_UNAVAILABLE`과 같은 결과(N 없음).
2. 817행 호출의 `deposit` 자리에 위 현금을 넣는다. `rule_file_nominal`의 인자 이름·docstring을 "USD 현금(총자산용, 위 선택 함수 결과)"으로 고친다. 결과 status 문자열 `DEPOSIT_UNAVAILABLE`은 그대로 두거나 `CASH_UNAVAILABLE`로 바꾸되, 그 문자열을 읽는 곳(grep)을 모두 같이 고친다.
3. 결정 기록에 표시용 칸 1개: `exposure["cash_basis"]`(문자열). 결정 스키마(manage-us-stock-strategy/schemas/auto-core-decision.schema.json)가 exposure 키를 막으면 이 칸만 선택 속성으로 추가. 통합점검 대시보드용 runCore 등 다른 출력은 바꾸지 않는다.
4. 그 밖은 바꾸지 않는다: 판정 매수 현금 `cash`(476행)·G1 상태 대조(486행)·S7·주문표 수량/가격 계산·관문 기준값(rules.C의 V6·EV4·N 상한·종목 상한)·대조 모듈(auto_core_compare)·리플레이.

# 테스트 — 새 파일 `manage-us-stock-strategy/tests/test_auto_core_equity_cash.py`

- T1 2026-10-13 값: holdings MVLL 159·NBIS 13·SOXL 53, 종가 MVLL 35.806·NBIS 209.98·SOXL 128.3599, 예수금 9,396.68, 출금가능 9,396.68, 주문가능 12,469.18, SOXL (settled 75, held 53) → basis ORDER_AVAILABLE, total 27,695.15(센트), N 1.2466(소수 4자리), `ev4_open(total, "30255.3600")` False, `v6_account(total)["state"]` == "none".
- T2 매도 결제 전인데 settled > held 행이 없음(가드 실패 CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS) → basis MIN_FALLBACK:…, 현금 = 예수금.
- T3 매수 결제 전(주문가능 < 출금가능 − 1, 가드 실패 CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE) → 현금 = 주문가능(최솟값), 산 주식 + 현금 이중 계산 없음.
- T4 세 값이 같음(미결제 없음) → 총자산·N·V6·EV4가 변경 전 코드와 같다(골든).
- T5 값 누락 → MIN_FALLBACK(알려진 값의 최솟값) / 모두 없음 → N None(지금과 같은 결과).
- T6 불변: 기존 decide 픽스처(test_auto_core_decide 등)로 만든 결정 기록에서 `exposure.N`·`exposure.cash_basis`·`account`(total·state·cushion·ev4_open)·R-REC1 이벤트 목록 밖의 값(주문표 qty·price·gates·decision_key·blocked, 트리거 state)이 변경 전과 같다. 픽스처가 미결제 없는 경우면 이 값들도 같아야 한다.
- 기존 테스트 파일은 고치지 않는다. 기존 테스트가 이 변경 때문에 깨지면 멈추고 보고서에 이유를 적는다(값 고정 테스트를 임의로 바꾸지 않는다).

# 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 파일은 auto_core_decide.py, auto_core_tickets.py(필요할 때만), schemas/auto-core-decision.schema.json(필요할 때만), 새 테스트, 보고서뿐.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1을 실행하지 않는다(테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`).
3. 가드는 import한 함수 하나만 쓴다. 가드 실패에서 주문가능을 그대로 쓰지 않는다. 추정 금액(가격 × 수량으로 만든 매도대금)을 쓰지 않는다 — 브로커가 준 세 값만.
4. 스크립트 ASCII만(한국어는 `\u` 이스케이프). 정책·상태 파일·workspace/policies·stock-strategy-system 쓰기 금지.
5. **커밋하지 않는다.** 변경은 worktree에 둔다(병합은 사용자 스크립트가 파일 목록을 확인하고 커밋한다).

# 보고 `docs/claude/t2-equity-cash-report.md` (worktree 안에 새로)

바꾼 함수·줄(diff 요약), 선택 함수 규칙, 테스트 목록과 결과(Ran 수, 대상·전체 스위트 새 실패 0 — 기준선과 비교), 2026-10-13 값의 계산 결과, 남은 위험(열린 매수 주문 예약금으로 주문가능이 줄어드는 날은 자산이 낮게 잡힘 — 보수적; 규칙 파일 문구 정정은 별도 ⑪).

# Judge 확인 항목 (별도 세션, 읽기만)

1. 바뀐 파일·줄이 위 범위뿐이고, 관문 기준값·주문표 계산·S7·대조·G1 대조가 그대로다.
2. 선택 함수: 가드 통과 → 주문가능, 실패·누락 → 알려진 값의 최솟값, 모두 없음 → None. 가드는 kiwoom_broker_shadow에서 import(복제 없음). 가격으로 추정한 금액이 없다.
3. T1 값이 실제로 27,695.15·1.2466·EV4 없음·V6 none이다(테스트가 하드코딩된 결과만 비교하지 않고 함수를 거친다).
4. 매수 결제 전 이중 계산이 없다(T3), 미결제 없을 때 결과 불변(T4·T6).
5. 권한 표지·주문 경로·정책/상태 쓰기 없음, 키움 호출 없음, 커밋 없음.
6. 대상·전체 테스트 새 실패 0.
