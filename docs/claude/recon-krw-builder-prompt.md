---
id: recon-krw-builder-prompt
title: "B2-N 대조: 원화 예수금 증가 ₩1,000 이하는 증가로 보지 않음 — recon-krw"
date: 2026-10-29
class: "authority(K3 — 대조 불변 조건 3의 B2-N 증거 요건 완화, H2 표시). 개발 큐 authority: Builder Opus → Judge → 병합은 사장 승인 + -ApproveAuthority"
source: "사장 결정 카드 '착수 승인'(사장실 회사PC 스레드 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9QHE589S4MyHb9pkNFdjPiT, 제안 recon-krw-2026-10-29, 2026-10-29 07:31 KST, 계정=사장). 제안서 docs/claude/recon-krw-2026-10-29.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
2026-10-29 06:15 대조가 `UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:0:9`로 보류됐다(recon-fb 뒤 원장 행 문제는 지났다). `auto_core_reconcile.py`의 `unverified_outflow`(844~845행 근처)는 원화 예수금(`won_entr`)이 base_before 대비 **어떤 양이든** 늘면 보류한다. 10/20 ₩0 → 10/26 ₩9(약 $0.007)가 걸렸다.

바꿀 것: 원화 예수금 증가가 **₩1,000 이하**이면 증가로 보지 않는다. 1,000 초과 증가는 지금처럼 같은 사유로 보류.

## 바꿀 내용 (`manage-us-stock-strategy/scripts/auto_core_reconcile.py`)
1. 상수 `KRW_RISE_TOLERANCE`(원, 값 1000)를 `OUTFLOW_MATCH_USD` 근처에 정의한다. 주석 1줄: 극소액(이자·반올림) 증가만 허용, 환전 유입 오인 방지 목적은 그대로.
2. `unverified_outflow`의 원화 증가 비교 한 줄만 바꾼다: 증가분(`after − before`)이 `KRW_RISE_TOLERANCE`를 **초과**할 때만 지금의 `UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:<before>:<after>` 사유로 보류. 값 형식·정수/문자열 해석 방식은 기존 코드 그대로 따른다.
3. 결과 dict의 키·사유 문자열·`unverified_outflow_basis` 키는 바꾸지 않는다(기존 테스트가 dict 전체를 비교한다). 새 키·새 경고 문자열 없음.
4. docstring과 `references/broker-snapshot-reconciliation.md`의 B2-N 설명(원화 증가 금지 문장)에 "₩1,000 이하 증가는 허용" 조건을 같은 내용으로 적는다.

## 테스트 (`manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py`)
기존 테스트 함수는 한 줄도 바꾸지 않는다(바뀌어야만 통과하는 기존 테스트가 있으면 멈추고 보고에 적는다). 같은 파일 끝에 새 클래스 `KrwRiseToleranceTests`를 추가한다. `core.unverified_outflow`를 직접 부르는 단위 테스트(기존 `AvailableCashLimitTests.judge`·`FallbackLedgerTests` 방식):
a. 10-29 재현: won_entr before 0 → after 9, 나머지 조건 충족(잔차 −173.64, 기준 82.93, trades 150.03) → 통과, `unverified_outflow_usd` "173.64".
b. 증가 정확히 1000 → 통과(경계 포함).
c. 증가 1001 → 보류, 사유 `UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:<before>:<after>`.
d. 큰 증가(예: 0 → 1,000,000) → 보류.
e. 원화 감소·변화 없음 → 기존대로 통과.
f. 원화가 ₩9 증가해도 달러 일치(0.05)·한도·창 조건이 어긋나면 기존 사유로 보류(허용이 다른 조건을 풀지 않음).
- 실행: 환경 변수 `PYTHONDONTWRITEBYTECODE=1`을 켠 채 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` **만** 돌린다. 전체 스위트·기준선 비교는 파이프라인이 한다. `test_kiwoom_order_block_hook.py`나 `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다(보호 경로에 .pyc가 생기면 STOP_PROTECTED). 해시 계산 등 허용 목록 밖 셸 작업은 하지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·`kiwoomcli` 실행 금지. 키움 호출·예약 작업 변경·상태/정책/일지/원장 쓰기 없음. "auto_core.py"가 든 명령 금지.
2. `cash_flow_evidence.py`, I1·I2·I4·I5, CASH_TOLERANCE_USD, OUTFLOW_MATCH_USD, FILL_WINDOW_MAXIMUM_DAYS, 정산 규칙, `ledger_days`·`ledger_balance`·fallback(recon-fb) 조건, 한도 식(recon-cap3) 무변경. 유입 인정·HWM 조정 코드 추가 금지.
3. 주문·권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch) 변경 없음. 한도·관문·매도 차단 변경 없음.
4. 판단이 안 되면 보류(fail-closed). 원화 값 해석 불가는 기존대로 보류.
5. 허용 파일만. 각 파일의 기존 줄바꿈(CRLF 등) 유지.
6. git commit·push·병합 없음.

## 보고 docs/claude/recon-krw-report.md
바뀐 줄(파일:행), 상수 값과 비교 방식(초과일 때만 보류), 대상 테스트 결과, 남은 위험. 반드시 포함: (a) 이 변경은 제약 완화(H2) — 원화 ₩1,000 이하 증가는 환전 유입 구분에 쓰이지 않음; ₩9 출처가 외부 KRW 입금이었다면 허용이 맞지 않는 반례(확인 필요) (b) HWM 조정 0 그대로 (c) 2026-10-29 결과는 병합 뒤 다음 실행(10/30 06:15)에서 확인 필요; 이후 조건(0.05 일치·한도) 첫 평가라 통과 여부는 확인 필요 (d) 겨울 시간(11/01~) 영향 확인 필요. 이 보고서 문장에는 주문·권한 표지 문자열을 그대로 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 `unverified_outflow`·상수·docstring, 참조 문서, 테스트 파일(새 클래스만)뿐이다. 결과 dict 키·basis 키 무변경.
2. 1000 이하만 허용, 1001 이상은 같은 사유로 보류. 감소·무변화 동작 불변.
3. 다른 조건(0.05·한도·창·fallback)이 원화 허용과 무관하게 그대로.
4. 반례 탐색: 소액 KRW 분할 입금을 반복해 우회할 수 있는지(비교는 base_before 대비 누적 증가이므로 누적 1,000 초과 시 보류인지), 환전 유입이 1,000원 이하로 위장될 수 있는지.
5. 주문·권한 줄 변경 없음, 허용 파일만, 줄바꿈 유지, 새 실패 0(파이프라인 checks), 보고 (a)~(d).

```dev-run
{"task_id": "recon-krw", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_reconcile.py", "manage-us-stock-strategy/references/broker-snapshot-reconciliation.md", "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py", "docs/claude/recon-krw-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(reconcile): B2-N ignores KRW deposit rises of 1000 won or less"}
```
