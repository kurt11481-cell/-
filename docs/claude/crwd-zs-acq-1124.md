---
id: crwd-zs-acq-1124
type: decision-record
status: current
as_of: 2026-11-24
summary: "통합 점검(11/24 06:52) 결정 'CRWD·Zscaler 인수를 호재로 셀지' → 사장 '세지 않음 (기준 유지)'. 같은 날 CRWD Q3 FY27 실적 조기 발표를 통합 점검이 놓친 사실 기록"
authority: "order_authority=false · quantity_authority=none"
---

# CRWD·Zscaler 인수 호재 판정 (2026-11-24)

## 1. 사장 결정
- 2026-11-24 11:39:09 KST, 사장 결정 카드 "CRWD의 Zscaler 인수를 호재로 셀까요?" → **'세지 않음 (기준 유지)'** (카드 cmsg_0137MRzn9nuDvvQmVxm6WeX91rP3B555R8oJCtuvE22SKW, 누른 계정 = 사장, 사장실 회사PC 스레드 'CRWD 인수 호재 판정 검토').
- 뜻: 호재 기준 (a)(2026-10-02 사용자 결정, integrated-check-prompt-v3.10-reconstructed-2026-10-05.txt 51행: 인수는 기본 제외, 사용자 개별 지정 때만 포함)를 그대로 둔다. 이번 Zscaler 인수는 개별 지정하지 않는다.
- 통합 점검은 이 인수를 다시 '결정 필요'로 올리지 않는다(이 문서가 결정 제외 근거).
- 바뀔 조건: 사장이 인수 개별 지정을 새로 요청할 때.

## 2. 확인한 사실 (SEC 원문)
- 인수: CrowdStrike·Zscaler 공동 보도자료(8-K Ex.99.1, Zscaler 제출 0001193125-26-471211; CrowdStrike 자체 8-K 0001104659-26-130785 item 1.01·7.01은 본문 미열람). 전액 주식, 기업가치 약 $43.9B, 교환비 1.135, 거래 뒤 기존 CRWD 주주 약 84.1%, 종결 CrowdStrike FY2028 하반기 예상(Zscaler 주주·규제 승인 조건).
- 같은 날 실적: CrowdStrike 8-K item 2.02(0001535527-26-000035, 접수 2026-11-23 11:04:51Z = 06:04 ET, 장 전) Ex.99.1 — Q3 FY27 순신규 ARR $419.2M(+58%), ARR $6.26B(+27%), 매출 $1.58B(+28%), FY27 가이던스 상향(매출 $6,078.1~6,084.1M). 12/01 예정 콜은 취소되고 11/23 08:00 ET 콜로 대체.

## 3. 판정 영향
- CR4(호재 뒤 하락, watch-card-CRWD-2026-11-20.md 65행)는 인수와 무관하게 Q3 실적·가이던스 상향(기준 (a) 안)으로 성립(잠정): 11/20 종가 $229.44 → 11/23 $208.97(16:00봉 시가, 분할 보정, 잠정). 약 1개.
- 매수: 오늘 R-REC1 ⑤ 관문·분할 기록 없음으로 막힘. 돈·주문 영향 없음.

## 4. 통합 점검이 놓친 것 (시스템 처리, 코디네이터에 넘김 11:3x KST)
- research-record 2026-11-24 earnings.CRWD = 2026-12-01 VERIFIED(틀림) → 금지 구간 11/27~12/02·카드 낡음 계산 틀림. earnings-anchors.json CRWD에 2026-11-23 SEC_FILING 추가 필요.
- 카드 표 근거(08/26 기준) < 실적 11/23 → 카드 낡음, card-review-auto(11/04)로 CRWD 카드 다시 쓰기.
- 공시 피드에 CRWD·PLTR 없음(record filings.watchlistMismatch) → 개발 큐 후보.

## 5. 검토 기록
- Fable 조언 1회(high): 8건 중 반영 6건(질문 전제·권장·실적일·카드 재검토·피드·출처). 미반영 2건: 매수 요건 ② '상품 승인 있음' 표시 차이와 종가 잠정 차이 — 오늘 판정 결론을 바꾸지 않아 카드 다시 쓰기 스레드 몫으로 둠(확인 필요).
