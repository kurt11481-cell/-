# 재설계 T2 둘째 운영일 점검 (2026-10-14 09:1x KST, Cowork 예약 점검)

## 1. 자동 실행
- 06:15 daily(예약, 사람 손 없음): HOLD `I3:CASH_CHANGE_NOT_EXPLAINED:3.05`. 06:15 키움 스냅숏(auto-core/2026-10-14/kiwoom_broker_snapshot.09f2d6795cd88b15.shadow.json): 예수금 9,396.68 · 미결제 매도대금 3,072.51 · 주문가능 12,472.23(= 9,396.68 + 3,072.51 + 3.04, 3.04 원인 확인 필요). SOXL 매도 정산은 08:07:05에 처리(ust21100 행). 정산 뒤 08:37 스냅숏은 예수금·주문가능 모두 12,469.19.
- 07:45 decide(예약): HOLD `G1_RECONCILE_NOT_OK`·`G1_STATE_NOT_EQUAL_BROKER`(06:15 daily 결과를 따름).
- 08:19 커밋 4051391(EV4 재구성·F6 중복 ord_no fail-closed, 이 세션 밖에서 병합) 뒤 08:37 daily·decide 재실행(이 세션 밖): daily OK(I3 차이 0.01), decide OK(사유 없음, S7 E 1.5037·멈춤 해제, N 1.2481, cash_basis ORDER_AVAILABLE, 주문표 0).
- 08:50 결과 알림: 통합점검 runs/2026-10-14 core = 08:37 decide(version 2).
- 판단: 실행 스크립트는 고쳐짐. 다만 **정산일 06:15에는 키움 주문가능액이 정산 처리 전 값이라 I3가 멈출 수 있다**(안전한 쪽 실패). 매도가 있을 때마다 되풀이될 수 있음 → 설계 과제(정산 처리 뒤 재대조 또는 실행 시각 조정, 확인 필요).

## 2. 예탁금 이용료(+$1.47) API 행
- ust21100 2026-10-09~10-14(kind all, 원화대용 포함, 전 페이지) 행 3개: 10/09 MVLL 매도 정산 2행(외화예수금잔고 9,395.21까지), 10/14 SOXL 매도 정산 1행(22주 @ $139.76, 정산 3,072.51, 잔고 12,469.19). 이용료 행 없음.
- 9,395.21 + 3,072.51 = 12,467.72, 실제 12,469.19 → 차이 1.47이 행 없이 잔고에 들어 있다. **이 API는 예탁금 이용료를 보여 주지 않는다**(확인된 사례 1건). 분기 처리는 사용자 결정대로 보류, 다음 지급 2027-01-10 전 cashflow-api-gap에서 다룬다.

## 3. 판정 대조(decide 08:37, 세션 10-13): B7 9건, 연속 0
| 항목 | 코어 | LLM | 판정 |
|---|---|---|---|
| buyReq ② BE·DELL·MU·NBIS·SOXL | ok | unk | 통합점검 규칙 파일 1-1 ②가 현금을 `overseas accounts cash-by-currency`(ust21120)에서 읽게 하는데, fc_ord_alowa는 `overseas accounts cash`(ust21110)에 있다(코어 브리지 kiwoom_account_readonly_bridge.py 22·57행). LLM은 규칙대로 "주문 가능 현금 필드 없음 → 확인 필요". LLM 오류도 코어 결함도 아닌 **규칙 파일 결함** → ⑪에서 명령 교체 필요. S7 멈춤이 풀린 동안 매일 되풀이. |
| MU:rebound_fail / MU:pullback_rebound | hit / none | false / true | **CORE_BUG**. 코어 C6±(auto_core_rules.py 330~337행)에 반등·눌림(전일 대비) 조건이 없다. 규칙 문구와 사전 등록 읽기(c-rule-replay-preregistration 79행 (ii))로는 10-09가 반등 세션이 아니어서 10-12 C6-는 성립하지 않고, C6+(10-07)는 10-13까지 유지. 10/13 같은 두 항목의 LLM_ERROR 설명은 Cowork 오판 → CORE_BUG로 정정. |
| MVLL:pullback_rebound | hit | info | 양쪽 모두 10-13 C6+ 충족을 인정. LLM은 규칙 115행(매수 불가 상품 + 쪽 "표시만")대로 state info로 적음 → 표기 차이, 대조 분류 과제. |
| MVLL:trend_recover | hit | 없음 | 상태형 C3 "유지 중" 해석 차이(통합점검이 10/13에 올린 "상태형 C3 해석" 결정 대기와 같은 문제). 10/13은 여유 1.05%로 B2였고 오늘 3.01%로 B7. |

설명 기록: docs/claude/redesign-t2-compare-explained.json — 10-13 MU 2건 정정, 10-14 MU 2건 CORE_BUG 추가. 나머지는 결정 뒤 기록.

## 4. 다음(우선순위)
1. c6-fix: 코어 C6±에 반등·눌림 조건 추가(판정 변경 — 권한 경로 dev-run, 사용자 승인 필요).
2. ⑪ 규칙 파일: 현금 명령 cash-by-currency → cash(규칙 파일·해시 변경, 사용자 승인).
3. 대조 분류: 매수 불가 상품 + 쪽 LLM info = 충족(B5 LLM_INFO_STATE 범위).
4. 사용자 결정: 상태형 C3 해석.
5. 정산일 06:15 I3 멈춤 설계.
