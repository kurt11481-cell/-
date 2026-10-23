---
id: recon-dt-builder-prompt
title: "키움 ust21150 ord_dt를 미국 주문일로 해석 — 대조 체결 시각(커밋 1) + 주문표 주문일 창(커밋 2) (관제판 recon-dt)"
date: 2026-10-23
class: "권한·한도(K3) — 대조 불변 조건 I2·I3가 읽는 체결 증거의 시각 해석. 불변 조건 자체·허용 범위·한도는 불변. 수동 경로: worktree Builder → 별도 읽기 전용 Judge(Opus) → 병합은 사장 결정"
source: "사장 \"결정 recon-dt: a\"(2026-10-23 08:45 KST, 투자_V2 비서실 — 직접 입력). 진단 docs/claude/recon-hold-2026-10-23.md(재검토 2회 반영)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
키움 일별 주문체결(ust21150)의 `ord_dt`는 **미국(ET) 주문일**이다. 지금 코드는 이를 KST 날짜로 읽어 KST 이른 아침(미국 전날 시간외) 체결을 하루 앞당긴다. 그 결과 2026-10-22·23 자동 대조가 I2 `QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:MVLL`, I3 `FILL_AMOUNT_UNAVAILABLE:2026-10-20:BE/NBIS`로 HOLD였다. 체결 시각 해석만 바로잡는다. 출금 증거(cashflow-api-gap)는 이 작업 범위가 아니다 — 고친 뒤에도 10-23 재생은 현금 잔차 −82.95(출금)로 HOLD가 남는 것이 정상이다.

증거(진단 문서 "독립 재검토 반영"·"2차 재검토 반영" 절): 10-23 reconcile.json fills에 order_date 20261021인 BE 19주가 filled_at_kst 2026-10-21T06:15:28로 계산됐는데, 10-21 06:15 스냅숏에는 BE 주문이 없고 10-22 06:15:07 스냅숏에는 BE 19주가 아직 '접수'(ord_time 06:13:46) — 실제 체결은 2026-10-22 06:15:28 KST(= 10/21 17:15 ET 시간외).

## 커밋 1 — 대조 체결 시각 (필수)
파일: manage-us-stock-strategy/scripts/auto_core_reconcile.py, manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, 새 테스트 manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py

규칙(정밀):
1. D = ord_dt를 미국 동부 거래일로 본다.
2. 체결 시각 c(cntr_time)의 KST 날짜 k는 {D, D+1} 중에서, (k, c, Asia/Seoul)을 America/New_York으로 바꾼 시각이 **D 04:00 ET 이상 ~ D 20:00 ET 이하**인 쪽 하나(zoneinfo로 DST 자동 처리 — 2026-11-01 뒤 경계 1시간 이동). 둘 다 아니면(예: 키움 주간거래) 그 행은 `FILL_TIME_OUTSIDE_US_SESSION:<label>` 오류로 남겨 HOLD(fail-closed). 두 후보는 24시간 차이라 답은 최대 하나.
3. 주문 시각 o(ord_time)는 같은 방식으로 KST 날짜를 정하되 창은 "D−1 20:00 ET 이후 ~ 체결 시각 이하"(예약·주간거래 시간에 넣은 정상 주문을 막지 않게). 주문 > 체결이면 `FILL_TIME_INVALID`.
4. 이 규칙이 기존 "cntr_time < ord_time이면 다음 날"(285행 근처)을 대체한다.
5. `session_date`는 D(ET)와 같아야 한다 — 다르면 오류(HOLD).
6. 체결 시각이 스냅숏 시각보다 늦으면 오류(HOLD).
7. 독스트링(244~245행 근처, 185~196행 plan_reads 독스트링)의 "KST day" 표현을 사실대로 고친다. 조회 창 범위(plan_reads·FILL_WINDOW_MAXIMUM_DAYS=14)는 바꾸지 않는다. 정산일 규칙(497~498행 근처)은 고친 뒤에도 성립하는지 확인만 하고 보고에 적는다. flow_cash의 ust21100 deal_dt KST 가정(590~612행 근처)은 고치지 않고 보고에 "cashflow-api-gap 조사 항목"으로 적는다.
8. 참조 문서 231~233행(체결 KST 시각 규칙)과 215행 근처의 같은 가정을 새 규칙으로 고친다.

테스트(기존 테스트 파일은 고치지 않음, 실제 키움·네트워크 없음, 합성 행 사용):
- 2026-10-21 ET 주문일 행들 재현: MVLL 매도 159(ord 06:13:17, cntr 06:13:18), BE 매수 19(06:13:46 / 06:15:28), NBIS 매도 13(— / 06:20:18), BE 매수 9(— / 06:40:50), SOXL 매도 82(22:22:07 / 22:22:23), LITE 매수 9(22:24:57 / 22:24:57), SOXL 매수 6(22:26:17 / 22:26:43) — 시간외 4건은 filled_at_kst 2026-10-22, 정규장 3건은 2026-10-21, session_date 모두 2026-10-21.
- 기준 시각 2026-10-21T06:15:04+09:00 이후로 MVLL·BE·NBIS가 fills_after에 들어간다(지금은 MVLL이 빠짐).
- 자정 넘김(ord 23:59:58, cntr 00:00:03 KST, 같은 D), EST 사례(2026-11-02 ET 주문, 시간외 체결 KST 08:30·10:30 경계 — 20:00 ET = EST 10:00 KST), 주간거래 시각(KST 12:00 체결) → FILL_TIME_OUTSIDE_US_SESSION, 주문 > 체결 → 오류.
- 10-23 상황 통합 재생(가능하면 기존 테스트의 픽스처 방식 재사용): I2 PASS, I3의 FILL_AMOUNT_UNAVAILABLE 사라짐, 현금 잔차만 남아(출금 −82.93 미반영) HOLD 유지.

## 커밋 2 — 주문표 주문일 창 (별도 커밋·별도 테스트)
파일: manage-us-stock-strategy/scripts/auto_core_tickets.py(520~533행 order_days, 559~604행 ord_time 창), 필요할 때만 auto_core_decide.py(195~199행), 새 테스트 manage-us-stock-strategy/tests/test_auto_core_tickets_orddt.py
- order_days가 "KST order days (ust21150 ord_dt)"로 가정한다. ord_dt = ET 주문일로 고친다: 주문표 세션 S의 주문은 ord_dt = S(ET) 하나(시간외 포함). 발행일 필터 `ord_time ≥ 발행 시각`이 KST 자정 뒤 정규장 주문(00~05/06시)을 빼는 문제와, 마지막 날 `≤ 05:00` 필터가 다음 세션 주문을 잘못 붙이는 문제를 커밋 1의 시각 규칙(KST 실제 시각 비교)으로 바로잡는다.
- 이 변경은 주문표 결과 원장(ticket_outcome 귀속)만 바뀐다. 상태 파일 쓰기·티켓 발행 조건·가격·수량 규칙은 바꾸지 않는다.
- 테스트: 평일 발행 주문표에 KST 22:3x 주문(같은 ET 날)·KST 01:30 주문(같은 ET 날 정규장)·다음 ET 세션 주문(오귀속 안 됨)·토요일 발행→월요일 세션.

## 검토 순서 (보고에 한 줄씩)
NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD. 위 규칙이 최소임을 보인다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·작업 등록 스크립트·`kiwoomcli`를 실행하지 않는다. Windows 예약 작업을 만들거나 바꾸거나 실행하지 않는다. 키움 호출 없음. 상태·정책·일지 파일을 읽어 쓰지 않는다.
2. 불변 조건 I1~I5의 판정식·허용 범위(현금 $1 등)·FILL_WINDOW_MAXIMUM_DAYS·정산 허용·cash_flow_evidence.py를 바꾸지 않는다. 출금·외부 흐름을 인정하는 코드를 넣지 않는다.
3. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어 있는 줄을 만들거나 지우거나 바꾸지 않는다. 한도·예산·관문 규칙 변경 없음. 매도를 막는 조건을 추가하지 않는다.
4. 판정을 느슨하게 하는 쪽으로 바꾸지 않는다: 새 시각 규칙에서 판단이 안 되면 HOLD(오류)로 남긴다.
5. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`처럼 패턴으로만 돌린다("auto_core.py"가 들어간 명령 금지). 시작 전에 같은 명령과 전체 스위트(`python -m unittest discover -s manage-us-stock-strategy/tests`)를 한 번 돌려 실패 목록을 기준선으로 남기고, 끝난 뒤 같은 명령으로 **새 실패 0**을 보인다.
6. 아래 허용 파일 밖을 만들거나 고치지 않는다. CRLF 줄바꿈을 일괄 변환하지 않는다(각 파일의 기존 줄바꿈 유지).
   허용: manage-us-stock-strategy/scripts/auto_core_reconcile.py, manage-us-stock-strategy/scripts/auto_core_tickets.py, manage-us-stock-strategy/scripts/auto_core_decide.py(필요할 때만), manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py, manage-us-stock-strategy/tests/test_auto_core_tickets_orddt.py, docs/claude/recon-dt-report.md
7. git commit·push·병합·강제·브랜치 삭제를 하지 않는다(권한상 거절됨). 변경은 worktree에 커밋하지 않은 채로 둔다 — 병합 때 Cowork가 "커밋 1"(reconcile·참조 문서·reconcile 테스트)과 "커밋 2"(tickets·decide·tickets 테스트)·보고로 나눠 커밋한다. 그래서 커밋 1과 커밋 2의 파일이 겹치지 않게 한다.

## 보고 docs/claude/recon-dt-report.md
바뀐 줄(파일:행), 규칙 요약, 테스트 결과(기준선·이후 실패 수, 새 테스트 이름), 커밋 1·커밋 2에 들어갈 파일 목록, 남은 위험. 반드시 포함: (a) 키움 사양에 ord_dt 시간대 문구가 없음 — 실관측(10/21~22)으로만 확정, 주간거래 체결은 관측 없음(창 밖 → HOLD) (b) 고친 뒤에도 10-23 재생은 출금 −82.93 때문에 HOLD(cashflow-api-gap) (c) 11/03 실행부터 FILL_WINDOW_TOO_LONG(기록이 성공해야 창이 줄어듦) (d) flow_cash deal_dt KST 가정 미수정.

## Judge 확인 항목
1. auto_core_reconcile.py diff가 체결·주문 시각의 KST 날짜 결정, session_date == D 검사, 체결 ≤ 스냅숏 검사, 독스트링뿐이다. I1~I5 판정식·허용 범위·조회 창·cash_flow_evidence 변경 없음.
2. 새 규칙이 판정을 느슨하게 하지 않는다: 판단 불가·창 밖·주문>체결은 오류(HOLD). 테스트가 이를 보인다.
3. 10-21 ET 주문일 7건 재현에서 시간외 4건이 2026-10-22 KST, 정규장 3건이 2026-10-21 KST, session_date 2026-10-21. 10-23 통합 재생에서 I2 PASS, FILL_AMOUNT_UNAVAILABLE 없음, 현금 잔차로 HOLD 유지(기록 없음).
4. 커밋 2(파일 묶음)는 주문표 귀속 창만 바꾸고 티켓 발행·가격·수량·상태 쓰기와 무관하다. 별도 커밋·별도 테스트.
5. 주문·권한 줄 변경 없음, 매도 차단 추가 없음, 허용 파일 밖 변경 없음, CRLF 유지, 기준선 대비 새 실패 0, 보고 (a)~(d) 포함.
