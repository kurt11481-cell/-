---
id: recon-fb-builder-prompt
title: "B2-N 대조: 직전 거래일 달러 예수금 행이 없으면 그 앞 거래일 행으로 대신 대조 — recon-fallback"
date: 2026-10-28
class: "authority(K3 — 대조 불변 조건 3의 B2-N 증거 요건 완화, H2 표시). 개발 큐 authority: Builder Opus → Judge → 병합은 사장 승인 + -ApproveAuthority"
source: "사장 결정 카드 '착수 승인'(사장실 회사PC 스레드 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9Dp5L8zK87C48ngGqFy7yKi, 제안 recon-fallback-2026-10-28, 2026-10-28 08:23 KST, 계정=사장). 제안서 docs/claude/recon-fallback-2026-10-28.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
2026-10-27·28 두 번 06:15 대조가 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:<직전 거래일>:USD_ROW`로 보류됐다. 키움 ust21132는 직전 미국 거래일(`base_after`)의 달러 예수금 행을 06:15에 주지 않는다(조회 응답: result_list 비어 있음, "내역이 없습니다"). 반면 그 앞 거래일 행은 있다(10/26 행 fx_entr 59.32). `auto_core_reconcile.py`의 `unverified_outflow`(778행~)는 `base_before`와 `base_after` 두 행을 모두 요구한다.

바꿀 것: `base_after` 읽기가 **성공했지만 USD 행이 하나도 없을 때만**, `base_after` 바로 앞 거래일(fallback)의 행으로 `base_after` 자리를 대신한다. 그 외(읽기 실패, USD 행 2개 이상, 값 해석 불가)는 지금처럼 보류.

## 바꿀 내용 (`manage-us-stock-strategy/scripts/auto_core_reconcile.py`)
1. `outflow_ledger`(1171행~): `days`의 두 날을 읽은 뒤, `base_after` 읽기가 성공(통과 상태)했고 그 읽기의 USD 행이 0개이면, 같은 운영 달력(`calendar_loader or production_calendar`)에서 `base_after`보다 앞선 가장 늦은 세션 날짜 `fallback`을 구한다. `fallback > base_before`일 때만 `fallback` 날짜의 같은 ust21132 읽기를 **한 번 더** 하고 결과를 `results`에 덧붙여 `{"days": days, "results": results, "fallback": fallback}`로 돌려준다. 조건이 하나라도 안 맞으면 `fallback` 키 없이 지금과 같은 값을 돌려준다(읽기 횟수도 지금과 같다 — `base_after` 행이 있을 때는 3번째 읽기를 하지 않는다). `ledger_reads` 캐시 키도 이 경우를 헷갈리지 않게 한다.
2. `unverified_outflow`: `ledger`에 `fallback`(date)이 있고 `base_after` 행이 "읽기 성공, USD 행 0개"일 때만 다음을 모두 확인한 뒤 `after` 대신 `fallback`을 쓴다. 하나라도 어긋나면 지금과 같은 사유로 보류한다(`LEDGER_UNAVAILABLE:<base_after>:USD_ROW` 그대로).
   - `fallback > base_before` 이고 `fallback < base_after`.
   - 계산 창(`window`)의 모든 `session_date`가 `base_before < session_date <= fallback`. (fallback 뒤 세션 체결이 있으면 행에 안 들어 있다.)
   - `fallback` 행이 정상(`ledger_balance` 통과: 읽기 성공, USD 행 정확히 1개, 값 해석 가능).
   그 뒤 계산은 지금 그대로: `ledger_residual = fx(fallback) − fx(before) − trades − flows`, `|residual − ledger_residual| ≤ OUTFLOW_MATCH_USD`, `ledger_residual < −CASH_TOLERANCE_USD`, 한도(기준 주문가능액 + max(0, trades + flows)), 원화 예수금 증가 금지(fallback 행 기준).
3. 결과 `unverified_outflow_basis`의 **키는 바꾸지 않는다**(기존 테스트가 dict 전체를 비교한다 — recon-cap 1차 실패 원인). fallback을 쓰면 `base_after` 값이 fallback 날짜가 되고 `fx_entr_after_usd`·`won_entr_after`도 그 행 값이 된다. 이것이 사용 표시다. 새 키·새 경고 문자열은 만들지 않는다.
4. docstring과 `references/broker-snapshot-reconciliation.md`의 B2-N 설명(295~315행 근처)에 위 조건을 같은 내용으로 적는다.

안전 방향(Judge가 확인): fallback 이후~base_after 사이에 출금·입금이 있었다면 스냅숏 잔차 R에는 들어가고 원장 잔차 L에는 안 들어가 |R−L| > 0.05 → 보류. 놓치는 쪽이 아니라 막는 쪽으로 틀린다.

## 테스트 (`manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py`)
기존 테스트 함수는 한 줄도 바꾸지 않는다(바뀌어야만 통과하는 기존 테스트가 있으면 멈추고 보고에 적는다). 같은 파일 끝에 새 클래스 `FallbackLedgerTests`를 추가한다. `core.unverified_outflow`를 직접 부르는 단위 테스트(기존 `AvailableCashLimitTests.judge` 방식):
a. 10-27 재현: days (10/20, 10/27), fallback 10/26, 기준 82.93, trades 150.03, flows 0, residual −173.64, 읽기 10/20 USD 82.94 · 10/27 통과·행 없음 · 10/26 USD 59.30 → 통과, `unverified_outflow_usd` "173.64", basis `base_after` "2026-10-26".
b. `base_after` 행이 있으면 fallback 키가 있어도 `base_after`를 쓴다(basis `base_after` = after).
c. 창에 fallback 뒤 세션(예: 2026-10-27) 체결이 있으면 보류, 사유는 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261027:USD_ROW`.
d. `base_after` 읽기가 실패(상태 오류)면 fallback이 있어도 보류(사유 `...:20261027`).
e. `base_after` 행이 2개이면 보류(`...:USD_ROW`).
f. fallback 행이 없거나 USD 행이 0개·값 해석 불가이면 보류.
g. `fallback <= base_before`이면 보류.
h. fallback 뒤에 추가 출금이 있었던 경우(residual −183.64, fallback 행은 59.30 그대로) → `UNVERIFIED_OUTFLOW_NOT_MATCHED`.
i. 한도 초과·원화 증가는 fallback 때도 그대로 보류.
j. 가능하면 실행 단위 테스트 1개(`OutflowRunTests` 방식, `LedgerBroker`와 합성 달력): `base_after` 응답이 빈 목록이고 fallback > before일 때 읽기 요청이 3번이고 기록된다; `base_after` 행이 있으면 읽기 요청이 2번이다. 기존 헬퍼로 30줄 안에 만들 수 없으면 만들지 말고 보고에 이유를 적는다.
- 실행: 환경 변수 `PYTHONDONTWRITEBYTECODE=1`을 켠 채 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` **만** 돌린다. 전체 스위트·기준선 비교는 파이프라인이 한다. `test_kiwoom_order_block_hook.py`나 `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다(보호 경로에 .pyc가 생기면 STOP_PROTECTED). 해시 계산 등 허용 목록 밖 셸 작업은 하지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·`kiwoomcli` 실행 금지. 키움 호출·예약 작업 변경·상태/정책/일지/원장 쓰기 없음. "auto_core.py"가 든 명령 금지.
2. `cash_flow_evidence.py`, I1·I2·I4·I5, CASH_TOLERANCE_USD, OUTFLOW_MATCH_USD, FILL_WINDOW_MAXIMUM_DAYS, 정산 규칙, `ledger_days`·`ledger_balance`의 기존 동작(날짜 규칙·사유 이름) 무변경. 한도 식(recon-cap3)·원화 증가 금지·유출만 인정 무변경. 유입 인정·HWM 조정 코드 추가 금지.
3. 주문·권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch) 변경 없음. 한도·관문·매도 차단 변경 없음.
4. 판단이 안 되면 보류(fail-closed). 읽기 실패는 fallback 사유가 아니다.
5. 허용 파일만. 각 파일의 기존 줄바꿈(CRLF 등) 유지.
6. git commit·push·병합 없음.

## 보고 docs/claude/recon-fb-report.md
바뀐 줄(파일:행), fallback 조건 4가지(읽기 성공·USD 0행 / fallback 날짜 범위 / 창 세션 ≤ fallback / fallback 행 정상), 읽기 횟수 변화(평소 2, fallback 때만 3), 대상 테스트 결과, 남은 위험. 반드시 포함: (a) 이 변경은 증거 요건 완화(H2) — `base_after` 행 없이도 통과할 수 있게 되는 경로가 1개 생김; fallback 이후 사건은 R–L 불일치로 보류됨 (b) HWM 조정 0 그대로 — 출금은 손실로 남음 (c) 2026-10-28 06:15 결과는 병합 뒤 다음 실행(10/29 06:15)에서 확인 필요 (d) 겨울 시간(11/01~) 영향은 확인 필요. 이 보고서 문장에는 주문·권한 표지 문자열을 그대로 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 `outflow_ledger`·`unverified_outflow`·docstring, 참조 문서, 테스트 파일(새 클래스만)뿐이다. basis 키 무변경.
2. fallback이 "읽기 성공 + USD 0행"에서만 켜진다(읽기 실패·2행·값 오류는 보류). fallback은 base_after 바로 앞 거래일 하나뿐이고 `> base_before`.
3. 창의 모든 세션이 fallback 이하일 때만 통과. 한도·0.05 일치·원화 증가 금지·유출만 인정이 fallback 때도 그대로.
4. `base_after` 행이 있는 경우의 동작·읽기 횟수가 지금과 같다(기존 테스트 무변경 통과).
5. 반례 탐색: fallback 뒤 입금·출금이 R–L로 걸러지는지, 임의 입금이 "유출"로 둔갑할 수 있는 길이 새로 생기는지.
6. 주문·권한 줄 변경 없음, 허용 파일만, 줄바꿈 유지, 새 실패 0(파이프라인 checks), 보고 (a)~(d).

```dev-run
{"task_id": "recon-fb", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_reconcile.py", "manage-us-stock-strategy/references/broker-snapshot-reconciliation.md", "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py", "docs/claude/recon-fb-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(reconcile): B2-N falls back to the previous trading day ledger row when the latest day has none"}
```
