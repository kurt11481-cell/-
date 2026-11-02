# 코드 리뷰 ② 대조·원장 (2026-11-01)

status: 읽기 전용 리뷰 결과 — 코드·정책·예약 변경 없음.
작성: 사장실 회사PC 스레드 "전체 코드 리뷰 진행"

## 읽은 범위
- auto_core_reconcile.py(1446줄): B2-N(97~105행, 743~857행), I2·I3(863~945행). 나머지 I1·I4·I5·결제 슬롯·provenance는 함수 목록만 봤다(**미검토**).
- t2rc-oracle.py: 미검토. 10/31 MISMATCH는 이미 진단 문서가 있다(t2rc-mismatch-1031-pwr-factid-2026-11-01.md, 사장 결정 D+B 12:45 KST). 이 리뷰는 그 결정을 다시 열지 않는다.

## 발견

### R-1 (중, 구조) B2-N은 5일 동안 수정 4건으로 I3 통과 조건이 계속 넓어짐
- 커밋: 93beae2(10/27 순유입 한도), d82dc15(10/28 전 거래일 행 대체), f8a1ad0(10/29 KRW 1000원 이하 무시), a3c7932(10/30, S7 쪽).
- 각 수정은 사장 카드로 승인된 예외다. 그런데 모두 apply 모드에서 **상태 파일 쓰기를 허용하는 쪽**으로 조건을 넓혔다.
- 코드 자체는 fail closed다. ledger 읽기 실패, 행이 0개 또는 2개 이상, 값 불명이면 모두 HOLD다(762~790행).
- 위험: 실제 계좌에서 새 경우가 생길 때마다 예외를 하나씩 더하는 패턴이다. 예외끼리 겹칠 때(대체 행 + KRW 허용 + 순유입 한도)를 묶어 본 시험이 있는지 **확인 필요**.
- 제안: 코드 수정 대신 "B2-N 예외 조합 시험" 1건을 개발 큐 후보로 둔다(테스트만 추가, 코어 동작 불변).

### R-2 (하) 0.05 USD 일치 기준과 1.00 USD 허용 오차가 따로 있음
- 842행: ledger 잔차는 −1.00 미만이고, 스냅숏 잔차와 0.05 이내여야 한다. 의도된 설계로 보이며, 문서(references/broker-snapshot-reconciliation.md)와 일치하는지 **확인 필요**.

### 문제 없음으로 본 것
- 유입은 B2-N으로 받아들이지 않는다(928행: difference < −1.00이고 I3 사유가 그 1건일 때만).
- 미체결 주문이 있으면 I3를 막는다(910~912행).
- 기준 현금이 없으면 상태 현금으로 대신하지 않는다(872~874행 주석, 901~902행).

## 결론을 바꿀 조건
B2-N 예외 조합 시험이 이미 tests/test_auto_core_reconcile_outflow.py에 있으면 R-1은 "구조 관찰"로만 남긴다.

## 추가: I1·I4·I5 리뷰 (2026-11-02 15:3x KST, 읽기 전용)
읽은 범위: auto_core_reconcile.py 200~234행(I1 읽기 판정), 235~253행(`invariant_i1`), 1025~1069행(I4·I5·`_broker_holdings`), 1199~1290행(판정·쓰기 흐름), apply_user_confirmed_broker_snapshot.py 52~75행(`ledger_status`)·205~208행(`_assert_untouched`), kiwoom_account_readonly_bridge.py 330~430행(쪽 나눔·결과 정리), kiwoom_broker_shadow.py 210·233행(중복 행 검사).

### 결론: 새 결함 없음. 셋 다 fail-closed로 본다.
- **I1**: 필수 읽기마다 결과가 정확히 1개이고 `bridge_status == PASS`여야 한다(240~252행). 0개나 2개 이상이면 REQUIRED_READ_MISSING이다. 브리지는 쪽 나눔이 끝까지 가야만 PASS를 주고, 아니면 PARTIAL을 준다(bridge 363~365행). 실패한 결과는 pagination을 complete=false로 덮어쓴다(424~425행).
- **I4**: 원장이 없거나 0행이면 LEDGER_MISSING이다. 해시 사슬이 깨지거나 읽기·JSON 오류가 나면 LEDGER_INTEGRITY_FAILED다. 상태 해시나 리비전이 마지막 원장 줄과 다르면 FAIL이다(1025~1039행, ledger_status 61~73행).
- **I5**: 허용 목록 방식이다. `WRITTEN_STATE_FIELDS` 밖의 키가 하나라도 바뀌거나 생기거나 빠지면 거부한다(`_assert_untouched` 206~208행). 그 위에 금지 목록 `NEVER_TOUCHED_FIELDS`를 한 번 더 확인한다(kiwoom_broker_shadow.py 31~33행). 쓰기는 `USER_CONFIRMATION_REQUIRED`일 때만 일어나고, 쓰기 직전에 파일 해시를 다시 확인한다(1279~1283행).
- 같은 종목이 브로커 보유 행에 두 번 나오면 스냅숏 정규화 단계에서 HOLDING_TICKER_DUPLICATE가 된다(kiwoom_broker_shadow.py 210행). 그래서 `_broker_holdings`가 덮어쓰는 일은 없다.

### 관찰 (결함 아님, 기록만)
- O-1: `_read_passed`(224~226행)는 pagination이 dict가 아니면 완료로 본다. 브리지가 PASS를 줄 때는 이미 완료가 보장되고, "데이터 없음" 확인 응답은 pagination이 없을 수 있다. 그래서 의도된 동작으로 본다. Worker 출력의 bridge_status를 그대로 믿는 범위는 **확인 필요**(bridge 400행 이전 부분 미검토).
- O-2: 원장 해시 사슬은 자기 자신 안에서만 일관성을 본다. 원장과 상태 파일을 둘 다 서로 맞게 다시 쓰면 I4는 통과한다. 원장은 상태 파일 옆(stock-strategy-system, git 밖)에 있다. 로컬 PC 한 대 구조에서는 받아들일 만한 한계로 본다. 외부 고정점(예: 마지막 원장 해시를 매일 git 문서에 남기기)은 필요하면 별도 안건으로 둔다.
