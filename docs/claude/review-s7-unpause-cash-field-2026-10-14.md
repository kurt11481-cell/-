---
id: review-s7-unpause-cash-field-2026-10-14
type: review
status: current
as_of: 2026-10-14
tickers: [BE, DELL, LITE, MU, MVLL, NBIS, SOXL]
summary: 통합점검 대시보드 확인사항 2건 검토(Cowork, 2026-10-14 10:4x KST) — S7 신규·추가 매수 정지 해제는 사실, 주문 가능 USD 필드 누락은 v3.12.4로 이미 수정. 사용자 결정 없음, 대시보드 갱신 안 함(기록은 예약 점검만 씀)
consumers: [다음 Cowork 확인(2026-10-15 06:40 실행 기록의 writer·stLeads·현금 칸), integrated-check-v3.12.4-change-2026-10-14.md, integrated-check-needs-recheck-saveticker-2026-10-14.md]
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 통합점검 확인사항 검토 — S7 정지 해제 · 주문 가능 USD 필드 (2026-10-14)

## 1. 결론
- 사용자가 고를 것 없음. 매수를 막는 것은 R-REC1(⑤) 하나뿐이고 의도대로 동작 중.
- 대시보드는 갱신하지 않음: `runs`는 06:40 예약 점검만 쓰고 Cowork는 `orders`만 씀(dashboard-order-panel-2026-10-07.md 2절, 4절). 06:52 실행 기록은 다음 점검이 "직전 기록"으로 읽으므로 사후 수정 금지(규칙 파일 v3.12.4 0)·2)단계).

## 2. 항목 1 — S7 정지 해제: 근거 확인됨
- 10/13 세션: 노출 E 1.5037, 신규·추가 매수 정지 모두 paused=false, band WITHIN_BAND, status VERIFIED (workspace/outputs/exposure-review/2026-10-13/portfolio-exposure-review.20261013T233738295224Z.json).
- 10/12 세션까지는 FAIL_CLOSED:hwm_line_or_pause_state_missing_or_corrupt · undeclared_cash_flow(· 일부 exposure_or_equity_or_v_unavailable)로 정지 — 같은 폴더 10/12 파일 5건. 판정 코드: manage-us-stock-strategy/scripts/portfolio_exposure.py 1165~1177행(fail-closed 사유 또는 열린 검토선이 있을 때만 정지).
- 정정: 사용자 문구의 "매수 요건 ② 미통과"는 auto-core 산출물과 다름. workspace/outputs/auto-core/LATEST_DECISION.json(생성 2026-10-14 08:37 KST, evaluation_session 2026-10-13, compare 모드)에서 BE·DELL·LITE·MU의 ②는 "통과 (E 1.5037 · 현금 $12469.19)". 막힘은 ⑤ "미충족 RG2,RG3"(RG1·RG4 ok, 충격 사건 2026-10-08 EV3a)과 마지막 칸 "사용자 주문 입력" 대기. (MVLL은 종목 상한·상품 승인 없음, NBIS는 카드 표 0으로 별도 막힘.)
- 종가는 30분봉 종가 근사(APPROXIMATE_CLOSE), 수익률 세션 134 < 창 252(short_history=true) — 같은 산출물.

## 3. 항목 2 — 주문 가능 USD 필드: 원인 확인, 수정 이미 적용
- 원인: v3.12.1 규칙이 `overseas accounts cash-by-currency`(ust21120)를 지정. 키움 스펙(spec_show ust21120)에는 fx_entr만 있고 fc_ord_alowa·fc_pymn_alowa는 `overseas accounts cash`(ust21110)에만 있음.
- 수정: v3.12.4가 2026-10-14 10:26~10:28 KST 적용(integrated-check-v3.12.4-change-2026-10-14.md 7행, 26행). 주문 가능·출금 가능은 ust21110, 총자산용 외화예수금 fx_entr는 ust21120.
- 실조회(읽기 전용, profile 실전계좌 · mode real, 2026-10-14 10:4x KST): cash → USD fc_entra = fc_pymn_alowa = fc_ord_alowa = 12469.19, cash-by-currency → fx_entr 12469.19. auto-core 현금 12469.19, 노출 검토 cash_usd 12469.18과 일치(정산 중 금액 없음).
- 대시보드의 "주문 가능 필드 없음"은 06:52 실행(v3.12.2) 기록. 새 규칙은 다음 실행(2026-10-15 06:40)부터.

## 4. 확인 필요 (미해결)
- 대시보드 화면에 "② 미통과"로 적혀 있는지 — 화면·저장소 원문을 이번에 열지 않음. 재검토 문서(integrated-check-needs-recheck-saveticker-2026-10-14.md 16행)는 "② 통과"로 적음.
- 예약 작업에 들어간 v3.12.4 본문 바이트 해시(목록 조회가 본문을 주지 않음, change 문서 48행). 첫 실행 기록의 writer·stLeads 필드로 대신 확인.

## 5. 바뀔 조건
- 2026-10-15 06:40 실행에서 현금 칸에 여전히 필드 누락이 나오거나 fc_ord_alowa가 fc_pymn_alowa와 달라지면(정산 중 금액 발생) 다시 검토.
- 새 R-REC1 RG2·RG3 충족 또는 새 충격 사건이 열리면 ⑤ 결론이 바뀜.

## 6. 후속
- Cowork: 2026-10-15 06:40 실행 후 기록 읽기로 현금 칸 정상화 확인(읽기만, 사용자 조작 0).
- 이 문서는 표시·기록용. 정책·상태·권한·주문 변경 없음.
