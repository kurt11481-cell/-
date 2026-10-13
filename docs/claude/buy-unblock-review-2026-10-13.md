---
id: buy-unblock-review-2026-10-13
title: 매수 막힘(S7·R-REC1) 해소 방법 재검토
date: 2026-10-13
status: 사용자 결정 대기
consumers: 관제판 r-cashflow-hold · rrec-rg1-bootstrap · 다음 Cowork 대조 세션 · redesign-t2 "켜" 전 회차
---

## 1. 결론
- 막힘은 3개다. ② S7과 ⑤ RG1은 시스템 결함, ⑤ RG2·RG3은 시장 조건(사용자 규칙 R-REC1)이다.
- 결함 둘을 고치면 이번 주 매수 가능 여부는 시장 조건만으로 정해진다. 가장 이른 판정은 10/15 KST decide(미국 10/13·10/14 종가 조건 충족 시).
- 10/8 사건 지정 철회는 효과가 없다(아래 3절). 쓰지 않는다.

## 2. ② S7 FAIL_CLOSED — 원인 정밀화와 정정
- 현금 흐름 증거 연쇄: r20(10/7까지 덮음) 뒤 r21~r23·r25 증거 없음, r24 증거 10/09~10/10 → 10/08 공백(CASH_FLOW_COVERAGE_GAP). covered_through 2026-10-07에서 멈춤.
- 코어 증거 시작일 = 원장 블록의 마지막 period_to(auto_core_reconcile.py evidence_period_start) = 10/10. 그래서 코어는 매일 10/10부터만 읽고(오늘 제안 10/10~10/13) 10/08을 다시 덮지 않는다.
- **정정**: redesign-t2-firstrun-report 15절 "T1 켜 뒤 첫 코어 기록에서 풀리는 설계"는 틀렸다. 켜도 영구 HOLD다.
- 시뮬레이션(cash_flow_chain, 읽기 전용, 현행 단계 재현 확인): r26 증거 10/10~10/13 → HOLD(COVERAGE_GAP) / 10/08~10/13 NO_EXTERNAL_FLOW → CLEAR, covered 10/13, hold 해제.
- 해소: (1) 지금 — 기존 전환 경로로 대조 1회(ust21100 10/08~오늘 증거 첨부, propose --cash-flow-evidence) → 사용자 "확인 <코드>" 1회 → apply. 다음 S7 계산에서 멈춤 해제 예상(실행 결과로 확인). (2) 재발 방지 — 코어 증거 시작일을 S7 covered_through+1 기준으로(일반 변경, 파이프라인).
- 남는 확인: 10/08 이후 USD 입금·출금·환전 여부(ust21100에 환전·출금이 안 보인 사례 있음, firstrun 15절 뒤 12:49).

## 3. ⑤ R-REC1 — 시뮬레이션(auto_core_rules.rrec1, 2026-10-12 세션, 읽기 전용, 코어 결과 재현 확인)
| 경우 | 사건 | RG1 | RG2 | RG3 | 상태 |
|---|---|---|---|---|---|
| 현행 | EV3a 10/08 (C0 563.185, L0 555.82) | unk(10/09 연구 기록 없음) | no | no | 막힘 |
| RG1 수정(기록 전 세션 미요구) | 같음 | ok | no | no | 막힘(시장 조건만 남음) |
| 10/08 지정 철회 | EV2 09/15 (C0 498.89, L0 496.58) | unk | no | no | 막힘 — 효과 없음 |
- DS1 10/12: SOXX 544.85 < EMA50 545.76 → RG3 재시작.
- RG1 수정 뒤 종목별 남는 조건(근사, 2026-10-12 기준):
  - SOXX 기준(MU·DELL·LITE·NBIS): SOXX 종가 > 563.19 연속 2세션(+3.4%), 그 사이 저가 ≥ 555.82, 종목 종가 ≥ 종목 EMA50(DELL +12.7%·LITE +5.7% 통과, MU −0.3%, NBIS −6.1%).
  - GRID 기준(PWR·BE): GRID C0 178.30·L0 176.98, EMA50 180.36. GRID 종가 ≥ 180.36(+1.0%) 연속 2세션(DS1 없어야 함), 저가 ≥ 176.98, 종목 ≥ EMA50(PWR +5.8%·BE +1.6% 통과). BE는 실적 금지 구간 10/20~10/23.
- RG1 수정 = rrec-rg1-bootstrap B(firstrun 17절). 매수 관문 의미 변경 → K3(사용자 결정 + 독립 Judge). 근거: 10/09 세션은 연구 기록 도입(10/13) 전이며, 10/10 통합 점검은 RG1 충족(공식 훼손 없음)으로 기록.

## 4. 주문표 입력
- 막힘이 풀려도 decision_mode compare → 주문표는 "비교 중", 입력 대상 아님. 이번 주 입력하려면 5거래일 대조 전 "켜" 결정 필요(정책 파일 변경, judge2 G절 "켜" 전 항목 9건 + ⑪).
- 순서: ⑤가 실제로 통과하는 날 결정한다(그 전 결정은 사용자 손만 늘림).

## 5. 사용자 손(이번 주)
- 확인 코드 1회(2절 대조) · 결정 1회(rrec-rg1-bootstrap B) · 병합 1회 · (⑤ 통과 시) "켜" 결정 1회.

## 6. 진행
- 18:40 사용자 propose(--cash-flow-evidence workspace/private_inputs/cash_flow_evidence/evidence_20261008_20261013.json, ust21100 10/08~10/13 3행 모두 매매, 외부 0, unresolved 0) → Cowork show(경고 없음, 알림 엔진 통과, 입출금 신고 NO_EXTERNAL_FLOW) → 사용자 "확인 612A12A7"(18:41) → apply: revision 25 → 26.
- 검증(읽기 전용, 출력은 저장소 밖): run_portfolio_exposure_review --session 2026-10-13(근사, 종가 없음) → cash_flow hold_active false, covered_through 2026-10-13, r26 CLEAR. undeclared_cash_flow 사유 사라짐. 남은 사유는 10/13 종가 미수집(required_price_missing·EQUITY_GAP)뿐 → 10/14 06:15 코어 실행에서 S7 멈춤 해제 확인 필요. L1(−10%)은 멈춤 없음, L2(−20%)만 멈춤(alert_policy).
- 효과: 코어 증거 시작일(마지막 period_to)이 10/13이 되어 다음 코어 증거가 끊기지 않는다. 재발 방지 코드 수정(2절 (2))은 별도.

## 7. 결정과 다음 (18:43~)
- 2절 (2) 재발 방지 코드 수정은 하지 않는다(NO_CHANGE): 공백은 사람 대조 경로(T4 은퇴 예정)에서만 생겼고, 코어는 자기 마지막 period_to부터 이어 읽어 공백을 만들지 않는다. r26으로 10/13까지 이어짐.
- 사용자 "결정 rrec-rg1-bootstrap: B"(18:43). 매수 관문 의미 변경 → 프로젝트 관례(t2-equity-cash)대로 K3 수동 경로. 지시문 docs/claude/rrec-rg1-builder-prompt.md, Judge docs/claude/rrec-rg1-judge-prompt.md. 병합 스크립트는 Builder 보고의 sha256으로 Cowork가 쓴다. 마감 10/15 07:45 decide 전.
- 관제판: r-cashflow-hold(waiting, 10/14 확인), rrec-rg1(active) 갱신.

## 8. rrec-rg1 병합 (20:38)
- Builder 1차 STOP(cmp-fix3 테스트 1건이 옛 동작 고정) → 추가 범위(그 테스트 입력 1줄·주석) → 대상 360 OK, 전체 새 실패 0 → 독립 Judge PASS(docs/claude/rrec-rg1-judge-report.md, 무작위 30,000건 신·구 비교) → 사용자 병합 스크립트 → main f8c0a8a(55803bf).
- 병합 뒤 메인 확인: sha256 일치, 대상 테스트 OK, 실데이터 2026-10-12 SOXX·MU·PWR 모두 RG1 ok · RG2 no · RG3 no · RG4 ok (status no).
- 남은 막힘: ⑤ RG2·RG3(시장 조건, 3절 종목별 조건). ② S7은 10/14 06:15 코어 실행으로 해제 확인.
- Judge 의견 3건 기본 NO_CHANGE(관제판 rrec-rg1 note). 문서 표류 references/auto-core-decision.md 88~89행은 후속 문서 수정.
