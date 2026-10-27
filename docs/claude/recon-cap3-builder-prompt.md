---
id: recon-cap3-builder-prompt
title: "B2-N 출금 인정 한도를 '기준 현금 + 기간 중 들어온 순현금'으로 — 대조 I3 (recon-i3-2026-10-27)"
date: 2026-10-27
class: "authority(K3 — 대조 불변 조건 3의 B2-N 한도 가드 완화, H2 표시). 개발 큐 authority: Builder Opus → Judge → 병합은 사장 승인 + -ApproveAuthority"
source: "사장 \"결정 recon-cap: REPLACE\"(2026-10-27 10:16 KST, 사장실 스레드 직접 입력). 진단 docs/claude/recon-i3-2026-10-27.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 재실행 사유
2차(recon-cap2, 2026-10-27 11:28 KST STOP_PROTECTED): 지시문이 Builder에게 전체 스위트를 돌리라고 해서, test_kiwoom_order_block_hook.py가 .claude/hooks의 훅을 불러오며 .claude/hooks/__pycache__/*.pyc를 만들었다(보호 경로). 이번에는 Builder가 대상 테스트만 돌린다. 전체 스위트·기준선 비교는 파이프라인이 한다.
1차(recon-cap, 2026-10-27 10:34 KST BLOCKED): 지시문이 basis에 새 키를 요구했는데 기존 테스트가 basis dict 전체를 비교해 충돌. 이번에는 basis 키를 바꾸지 않는다.

## 목표
2026-10-27 대조 HOLD의 현금 차이 -173.64는 출금 두 번(10/22 -82.93, 10/26 -90.72)이고 남는 차이는 +0.01이다(docs/claude/recon-i3-2026-10-27.md). B2-N(`unverified_outflow`, auto_core_reconcile.py 778-820행)은 809-810행에서 "유출 금액 ≤ 기준 기록의 주문가능액"을 요구해서, 기간 중 들어온 매도 정산 현금(+150.03)에서 나간 출금을 막는다(173.64 > 82.93 → `UNVERIFIED_OUTFLOW_ABOVE_BASELINE_CASH`). 이 한도를 **기준 주문가능액 + max(0, 같은 구간 체결 정산 순현금 + 분류 흐름)**으로 바꾼다. 기간 중 실제로 계좌에 있었을 수 있는 현금의 상한이다.

## 바꿀 내용
1. `manage-us-stock-strategy/scripts/auto_core_reconcile.py` `unverified_outflow`: 809행 비교를 `amount > baseline_cash + max(Decimal("0"), trades + flows)`로 바꾼다. 사유 문자열은 `UNVERIFIED_OUTFLOW_ABOVE_AVAILABLE_CASH:<유출>:<한도>`로 바꾼다(한도 = 위 식). 결과 `unverified_outflow_basis`의 키는 바꾸지 않는다(새 키 추가 금지 — 기존 테스트가 dict 전체를 비교한다). docstring의 해당 문장도 고친다. 다른 조건(a 유출만, b 다른 I3 사유 없음, c 원장 두 날, d 체결 구간, e |R-L| ≤ 0.05·L < -1.00, g 원화 예수금 증가 금지)·순서·상수·호출부(893-896행)는 바꾸지 않는다.
2. `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md` 303·306행 근처: 한도 문장과 사유 이름을 같은 내용으로 고친다.

## 테스트 (`manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py`)
- 기존 테스트는 **`test_outflow_above_the_baseline_order_available_cash_holds` 1개만** 새 한도 기준으로 고친다(예: 같은 judge() 기본값 trades 329.17에서 residual이 1329.17을 넘는 값과 이에 맞는 after, 기대 사유 새 이름). 다른 기존 테스트 함수는 한 줄도 바꾸지 않는다.
- 새 테스트(같은 파일 끝에 추가):
  a. 10-27 재현: 기준 82.93, trades +150.03, flows 0, R -173.64, 원장 fx_entr before 82.94 · after 59.30(L = -173.67, |R-L| 0.03) → 통과, unverified_outflow_usd "173.64". 같은 값에서 R -232.97(원장도 맞춰서)이면 사유 `UNVERIFIED_OUTFLOW_ABOVE_AVAILABLE_CASH:232.97:232.96`.
  b. 경계: 유출 = 한도 → 통과, 한도 + 0.01 → HOLD(새 사유).
  c. 순매수 구간(trades 음수): 한도 = 기준 현금 그대로(음수 순현금은 한도를 줄이지 않고 늘리지도 않음) → 기준 현금 초과 유출 HOLD.
  d. 분류 흐름 양수(배당 등)도 한도에 들어간다.
- 실행: 환경 변수 `PYTHONDONTWRITEBYTECODE=1`을 켠 채 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` **만** 돌린다. 전체 스위트·기준선 비교는 파이프라인이 한다. `test_kiwoom_order_block_hook.py`나 `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다(보호 경로에 .pyc가 생기면 STOP_PROTECTED).

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·`kiwoomcli` 실행 금지. 키움 호출·예약 작업 변경·상태/정책/일지/원장 쓰기 없음. "auto_core.py"가 든 명령 금지.
2. `cash_flow_evidence.py`, I1·I2·I4·I5, CASH_TOLERANCE_USD, OUTFLOW_MATCH_USD, FILL_WINDOW_MAXIMUM_DAYS, 정산 규칙, 원장 날짜 규칙(`ledger_days`·`ledger_balance`) 무변경. 유입 인정 코드·HWM 조정 코드 추가 금지.
3. 주문·권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch) 변경 없음. 한도·관문·매도 차단 변경 없음.
4. 판단이 안 되면 HOLD(fail-closed).
5. 허용 파일만. 각 파일의 기존 줄바꿈(CRLF 등) 유지.
6. git commit·push·병합 없음.

## 보고 docs/claude/recon-cap3-report.md
바뀐 줄(파일:행), 새 한도 식, 대상 테스트 결과, 남은 위험. 반드시 포함: (a) 이 변경은 가드 완화(H2) — 한도가 넓어지는 만큼 "유출"로 기록될 수 있는 금액 범위가 커짐, 나머지 원장 일치 조건이 그대로 막음 (b) HWM 조정 0 그대로 — 출금은 손실로 남음 (c) 2026-10-27 06:15 실행의 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:20261026:USD_ROW`(직전 미국 거래일 원장 행이 06:15에 없음)는 이 변경으로 풀리지 않음 — 10/28 실행 결과로 확인 필요. 이 보고서 문장에는 주문·권한 표지 문자열을 그대로 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 809-810행 한도 식·사유 이름·docstring(basis 키 무변경), 참조 문서 한도 문장, 테스트 파일(기존 1개 함수 + 새 테스트)뿐이다.
2. 새 한도 = 기준 주문가능액 + max(0, trades + flows). 음수 순현금은 한도를 줄이거나 늘리지 않는다(테스트 c).
3. 다른 B2-N 조건·순서·상수·원장 날짜 규칙·cash_flow_evidence·I1/I2/I4/I5 무변경. 유입 인정·HWM 조정 없음.
4. 10-27 재현 테스트가 통과하고 경계 테스트가 한도 + 0.01에서 HOLD.
5. 주문·권한 줄 변경 없음, 허용 파일만, 줄바꿈 유지, 새 실패 0(파이프라인 checks), 보고 (a)~(c).

```dev-run
{"task_id": "recon-cap3", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_reconcile.py", "manage-us-stock-strategy/references/broker-snapshot-reconciliation.md", "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py", "docs/claude/recon-cap3-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(reconcile): B2-N outflow cap counts the net cash that came in during the window"}
```
