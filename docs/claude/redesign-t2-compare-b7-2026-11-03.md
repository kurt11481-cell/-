---
id: redesign-t2-compare-b7-2026-11-03
title: "T2 비교 모드 미설명 차이(B7) 설명 기록 — 10-27·10-28·10-29·10-30·10-31·11-03"
date: "2026-11-03"
status: "기록 26건(LLM_ERROR) · 미설명 유지 1건(사유 있음) · 코드 수정 필요 0"
authority: "표시·기록 전용 · 주문·정책·상태·관문 무관"
consumers: "auto_core_compare.py R2 연속 일수(다음 decide) · t2-gate REMOVE-v2 조건 1(차이 분류 의무) · '켜' 판정 세션"
source: "workspace/outputs/auto-core/2026-10-27·28·29·30·31·11-03/compare.json·decision.json·s7 · 통합점검 대시보드 runs 같은 날짜 · regular-session-closes/history(SOXX·SOXL·PWR) · 규칙 파일 v3.12.10(10-27~10-31)·v3.12.11(11-03)"
---

## 결론
- 계기: 사장 지시(2026-11-03 19:38 KST) "사장 결정이 매번 남아서 방치된다. 최대한 스스로 해결해서 통합점검 매도매수 지시에 빈틈이 생기지 않게 해라". 코어 next_action_for_cowork "판정 차이 4건 — 설명 기록 필요"가 10-28 뒤 처리되지 않았다(explained.json 마지막 항목 10-28).
- redesign-t2-compare-explained.json에 **LLM_ERROR 26건** 추가(30 → 56건): 매수 요건 ③ 17건 · R5:SOXL 3건 · RREC:RG1 2건 · 10-27 트리거 3건 · 11-03 SOXL:crash_alert 1건.
- R2 하루 통과(day_passes 313~318행): 10-27·28·29·30 통과, 10-31 탈락(아래 미설명 1건), 11-03 통과. R2 연속 셈은 t2-gate REMOVE-v2로 '켜' 조건에서 빠졌고 기록·표시만 한다.
- t2-gate REMOVE-v2 조건 1(C1 창 10-17 실행분부터 모든 비교일의 unexplained 분류): 이 기록으로 10-27~11-03 미분류 0. 10-20·10-22 남은 것은 redesign-t2-compare-b7-2026-10-23.md '미설명으로 둔 것'에 사유가 있다.

## 미설명으로 둔 것 (1건)
- **10-31 buyReq:SOXL:3** (코어 ok '통과 C 단독' / LLM wait): 코어는 + 쪽 가격 단서 2개(C1+ 새 충족 + C2+ 사건형 창 5일째)로 basis_met. C2+ 사건일은 세션 10-26이고 그날 충족 여유가 0.07%(정규장 저가 84.2265 vs EMA20(t−1) − 2.5×ATR14(t−1) 선, decision.json margins.oversold_rebound 0.00065)였다. 그 차이는 10-28~10-31 compare.json에서 **B2(경계 MARGIN 0.0007 ≤ 0.03)**로 이미 허용된 차이다. LLM은 사건일에 C2+를 미충족으로 봤고 그 뒤 창도 세지 않았다 → ③ 차이는 B2 경계 차이에서 파생된 것이라 LLM_ERROR로도 CORE_BUG로도 적지 않는다. 원인은 코어 밖(경계값 입력 — LLM은 30분봉 잠정 저가, 코어는 정규장 저가)이다.

## 같은 실수가 반복된다 — 다음 규칙 개정 후보
- ③ 카드 표 근거 누락: 10-24에 같은 유형을 LLM_ERROR로 적었는데 10-27~11-03 매일 BE·DELL·MU에서 다시 났다(17건).
- R-REC1 EV2를 세션마다 판정하지 않음: 10-27·28 LLM_ERROR 뒤 10-29·30에 반복, 11-03 실행에서도 "11/2는 새 사건 아님(≤ −2σ60 아님)"이라고 EV1만 봤다(코어 사건일 11-02 EV2, 재계산 문턱 542.36 vs 종가 453.63 — 11-02 종가는 겨울 봉 미확인 상태).
- R5 state 칸에 label 문구를 넣음(10-22부터 반복).
- 사건형 5세션 창(C2·C4)을 빼먹음(10-23·24·27).
- 제안(통합점검 규칙 파일 개정 묶음 후보): 결정론으로 계산되는 값(트리거·매수 요건·R5·R-REC1)은 코어 decision.json 값을 그대로 옮기고, LLM은 공식 사실·뉴스 판정만 맡는다. 예약 작업 지시문 변경이라 사장 직접 입력 '예약 작업 변경 승인: 보유·관심 종목 통합 점검'이 필요하다.

## 코드 수정이 필요한 것
- 없음(코어 쪽 결함 0건). 별건: validate_integrated_authority_production.py 108-109행 개장·마감 시각 -04:00 고정(dst-label2-report.md 남은 위험 (d)) — 이 기록과 무관, 위치만 적는다.

검토 완결: 원문 확인 — 6일 compare.json unexplained·decision.json buy_requirements ③·대시보드 runs buyReq ③ 문구·S7 peak_reviews SOXL(10-27~29)·SOXX/PWR/SOXL close-history 재계산·규칙 파일 v3.12.10·v3.12.11 101·102·108·112·113·124·134행은 사장실 회사PC 스레드가 직접 확인 · 하위 에이전트 0 · 미해결 0 · 계좌 금액 없음.
