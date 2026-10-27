---
id: recon-cap3-report
title: "recon-cap3 Builder 보고 — B2-N 출금 인정 한도 = 기준 현금 + max(0, 기간 순현금)"
date: 2026-10-27
prompt: docs/claude/recon-cap3-builder-prompt.md
class: "authority(K3, H2 가드 완화) — 병합은 사장 결정 + -ApproveAuthority"
---

## 바뀐 줄
- `manage-us-stock-strategy/scripts/auto_core_reconcile.py`
  - 788-790행(docstring): "기준 주문가능액" 한도 문장을 "기준 주문가능액 + 같은 구간 순유입 현금(max(0, 체결 정산 현금 + 분류 흐름); 순유출은 한도를 줄이지도 늘리지도 않음)"으로 고침.
  - 810-812행(원래 809-810행, docstring이 1줄 늘어 밀림): `available = baseline_cash + max(Decimal("0"), trades + flows)`; `amount > available`이면 `UNVERIFIED_OUTFLOW_ABOVE_AVAILABLE_CASH:<유출>:<한도>`로 HOLD.
  - `unverified_outflow_basis` 키, 다른 조건(a~e, g)·순서·상수·호출부(이제 894-897행, 내용 무변경) 바뀐 것 없음.
- `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md` 302-310행: 한도 문장과 사유 이름(`UNVERIFIED_OUTFLOW_ABOVE_AVAILABLE_CASH:<outflow>:<limit>`)을 같은 내용으로 고침.
- `manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py`
  - 187-191행: 기존 테스트 `test_outflow_above_the_baseline_order_available_cash_holds` 1개만 새 한도 기준으로 고침(R -1329.20, after 0.00 → L -1329.18, 한도 1000.00 + 329.17 = 1329.17 → `...:1329.20:1329.17`). 다른 기존 테스트 함수는 바꾸지 않음.
  - 428-482행: 새 클래스 `AvailableCashLimitTests`(테스트 4개).

## 새 한도 식
`유출(-R) ≤ 기준 기록 주문가능액 + max(0, 같은 구간 체결 정산 현금(수수료 포함) + 분류 흐름)`

## 새 테스트
- a `test_oct27_two_withdrawals_out_of_the_sale_cash_pass`: 기준 82.93, trades +150.03, flows 0, R -173.64, ust21132 82.94 → 59.30(L -173.67, |R-L| 0.03) → 통과, `unverified_outflow_usd` "173.64". R -232.97(원장 after 0.00, L -232.97) → `UNVERIFIED_OUTFLOW_ABOVE_AVAILABLE_CASH:232.97:232.96`.
- b `test_outflow_equal_to_the_limit_passes_and_one_cent_more_holds`: 유출 1329.17 = 한도 → 통과, 1329.18 → HOLD(새 사유).
- c `test_net_buy_span_keeps_the_baseline_cash_as_the_limit`: trades -300.00 → 한도 1000.00(700.00으로 줄지 않음): 1000.00 통과, 1000.01 HOLD.
- d `test_classified_inflows_count_toward_the_limit`: 배당 흐름 +50.00 → 한도 150.00(150.00 통과, 150.01 HOLD); trades -50.00 + flows +80.00 → 한도 130.00(130.00 통과, 130.01 HOLD).

## 대상 테스트 결과
`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`
→ 533개 실행, 실패 1, skip 1. B2-N 테스트(기존·새 것 모두)는 통과.
- 실패 1건: `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches` (symbol='PLTR'): `['CARD_SECTION_CHANGED', 'CARD_NOT_ACCEPTED_IN_WATCHLIST']`. 실제 카드 근거 레지스트리와 카드 해시를 보는 테스트이고, 이번 diff는 그 파일들을 건드리지 않는다. 변경과 무관한 기존 실패로 보이지만 Builder는 변경 전 코드로 다시 돌려 확인하지 않았다 → 파이프라인 기준선 비교로 확인 필요.
- 전체 스위트, `test_kiwoom_order_block_hook.py`, `.claude/` 아래 파일은 실행하지 않음. 실행 뒤 작업 트리에 추적되지 않은 파일 없음(`__pycache__` 없음). 세 파일 모두 CRLF 유지(LF로 끝나는 줄 0).

## 남은 위험
- (a) 이 변경은 가드 완화(H2)다. 한도가 기간 순유입 현금만큼 넓어지므로 "확인되지 않은 유출"로 기록될 수 있는 금액 범위도 그만큼 커진다. 나머지 원장 일치 조건(R < -1.00 유출만, 다른 I3 사유 없음, 원장 두 날 읽기, 체결 구간 일치, |R-L| ≤ 0.05·L < -1.00, 원화 예수금 증가 금지)은 그대로 막는다.
- (b) HWM 조정은 0 그대로다. 현금흐름 신고(declaration)는 건드리지 않아 출금은 손실로 남는다. 유입 인정 코드·HWM 조정 코드는 추가하지 않았다.
- (c) 2026-10-27 06:15 실행의 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261026:USD_ROW`(06:15에 직전 미국 거래일 원장 행이 없음)는 이 변경으로 풀리지 않는다. 10/28 실행 결과로 확인 필요.
- 옛 사유 이름 `UNVERIFIED_OUTFLOW_ABOVE_BASELINE_CASH`는 이제 코드·참조 문서에 없고 docs/claude/의 이전 기록(cf-b2n-report, recon-i3-2026-10-27, 이전 지시문)에만 남는다. 그 이름을 읽는 코드나 스키마는 없다.
- 주문·권한 줄: 표지 없음(바뀐 것 없음). 한도·관문·매도 차단, `cash_flow_evidence.py`, I1·I2·I4·I5, 상수, 원장 날짜 규칙 무변경. 키움 호출·상태/정책/일지/원장 쓰기·커밋 없음.
