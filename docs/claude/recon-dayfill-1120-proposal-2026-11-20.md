# 매도 체결 뒤 계좌 대조 HOLD 진단·해결안 (recon-dayfill-1120)

작성 2026-11-20 KST · 사장실 회사PC 스레드 '매도 뒤 계좌 대조 막힘 고치기' · 계기: 사장 직접 입력 2026-11-20 09:36 KST "매도체결하면 맨날 불일치나서 막히는데 검토하고 해결좀 해줘" · 새 결정 없음(제안만)

## 0. 결론
- 11/20 HOLD 사유 3개(I2 체결 시각·I2 SOXL 수량·I3 현금 3771.28)는 원인 하나: 11/19 SOXL 74주 매도가 **키움 주간거래(한국 낮)** 체결(주문 11:34:06, 체결 12:44:27 KST @51.00 = ET 11/18 22:44)이었다. 코어는 주문일 D의 04:00~20:00 ET 체결만 인정한다(의도된 fail-closed).
- 이 상태는 **스스로 풀리지 않는다.** 08:38 KST 수동 대조(rev 44, as_of 2026-11-19T23:38:07Z = KST 11/20)는 기록일을 11/20으로만 옮겼고, 조회 창이 '기록일 전날'부터라 11/19 주간거래 행을 매일 다시 읽어 같은 오류로 HOLD한다(11/21 06:15 실행 예상 HOLD — 실행 뒤 확인 필요). 방치하면 12/03 실행부터 FILL_WINDOW_TOO_LONG.
- 수동 대조에 `--cash-flow-evidence`가 빠져 S7 검토선이 11/19부터 보류(hold_active true, covered_through 11-18, s7-rerun-0926). 다음 대조가 증거를 붙여 성공하면 풀린다.
- "맨날"의 실체: 매도 때마다 **다른** 사유였다. 10/22~24 주문일 해석 결함(10/25 병합 해결), 10/27~29 출금 증거(10/30 해결), 11/19 06:15에 남은 SOXL 72주 매도 주문(OPEN_ORDERS_PRESENT, 정정완료 23:36:01), 11/20 주간거래 체결. 정규장·시간외 체결은 OK로 기록됐다(10/21·10/30).

## 1. 근거 (원문 행)
| 항목 | 위치 |
|---|---|
| 체결 행 | workspace/outputs/auto-core/2026-11-20/kiwoom_broker_snapshot.shadow.json fills[0] (ord_time 11:34:06, cntr_time 12:44:27, cntr_uv 51.0000) |
| 판정 창 04:00~20:00 ET | manage-us-stock-strategy/scripts/auto_core_reconcile.py 96, 259~267, 315~319 |
| 수량 사유 | 같은 파일 881~894 |
| 현금 사유 3830.60 − 59.32 | 같은 파일 915~926 · reconciliation_proposal.json cash_components.unsettled_component 3771.28 |
| 미체결 주문이면 매수·매도 무관 HOLD | 같은 파일 910~912 |
| 조회 창 = 기록 KST일 −1 ~ 오늘 | 같은 파일 171~174, 198~208 |
| 체결 오류는 기록 시각과 무관하게 I2 FAIL | 같은 파일 883 |
| 자동 기록은 사유 0일 때만 | 같은 파일 1275~1280 |
| 주간거래 HOLD는 설계 | recon-dt-report.md 53·81행(test_kiwoom_day_session_fill_holds), recon-hold-2026-10-23.md 39·51행 |
| 증거 누락 → S7 보류, 뒤 대조로 해제 | cash_flow_evidence.py 393~397, 401~422 · broker-snapshot-reconciliation.md 189~209 |
| 사장 운영지침: 주간거래는 회사 거래시간에서 뺌 | order-receipt-process-review-2026-10-09.md 87행 (2026-10-20 19:29 KST) |
| 11/20 독립 대조 NOT_CHECKED | 2026-11-20/t2rc-check.json input_sha_mismatch ["state"] — 07:45 판정 뒤 08:39 수동 적용으로 state가 바뀐 결과(별도 결함 아님) |

## 2. 해결안 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)
| 순서 | 내용 | 분류·승인 경로 |
|---|---|---|
| NO_CHANGE (지금 할 일) | 11/21 00:00 KST 이후 Cowork에서 수동 대조 1회 더, `propose --cash-flow-evidence workspace/private_inputs/cash_flow_evidence/auto-core-<그날 파일>.json` 포함. 기록일이 11/21 이후가 되면 11/19 행이 조회 창 밖 → 다음 자동 실행부터 OK, S7 보류도 풀림. 재발 방지는 10/20 지침대로 주간거래에 주문 안 넣기 + 정규장 마감 뒤 미체결 주문 남기지 않기 | 개발 변경 없음. apply는 사장 "확인 <코드>"(Cowork) 또는 사장 터미널만(CLAUDE.md 23~28행) |
| REMOVE/SIMPLIFY | (a) OPEN_ORDERS_PRESENT를 매수 미체결에만 적용(910~912) (b) 체결 오류를 기록 시각 뒤일 수 있는 행으로 한정(883) | 대조 불변 조건 → K3(CLAUDE.md 66~82행). (a)는 매도 미체결이 주문가능금액을 묶는지 확인 필요 |
| REUSE | 체결 시각 창을 주문 시각 창(320~321, D−1 20:00 ET 초과 ~ D 20:00 ET)으로 넓혀 주간거래 체결 인정 | K3 + 10/20 지침 변경이 먼저. 관측 1건뿐, 정산 슬롯·ust21610 수량·주간거래 정확한 시간 확인 필요 |
| REPLACE | 수동 대조 경로를 '자동 HOLD 때 공식 탈출구'로 CLAUDE.md에 다시 정의(증거 필수·기록일 조건) | CLAUDE.md 개정 → K3·수동 경로 |
| ADD | (i) S5 활성 뒤 propose에 증거 없으면 거부/경고 (ii) 사장 주문 할 일 알림에 "주간거래 입력 금지 — 대조가 이틀 막힘" 한 줄 (iii) 참조 문서 'never observed' → '2026-11-19 관측' | (i) 대조 기록 경로라 K3 가능성(파이프라인 판정, 확인 필요) (ii) `예약 작업 변경 승인: 사장님 주문 할 일 알림` (iii) 문서만 |

권장: NO_CHANGE(지침 유지) + ADD (ii)·(iii). 주간거래 매도를 계속 쓰고 싶다면 그때 REUSE(K3).

## 3. 연결표 (analysis-linkage-map 1절 8번)
| 칸 | 내용 | 상태 |
|---|---|---|
| ① 자료 | 키움 ust21150 체결·주문가능금액 (reconcile.json) | 연결 |
| ② 읽는 점검 | auto_core_reconcile.py 270~336 → G1 (decision.json reasons) | 연결 |
| ③ 바뀌는 행동 | HOLD면 주문표 없음(매수·매도 모두) — 2026-11-20 LATEST_DECISION.json | 연결 |
| ④ 사장 행동 | 주문 입력 시간대(10/20 지침) | **끊김**: 지침이 주문표·알림 문구에 없음(order-receipt-process-review 87행의 '소비처'가 구현 안 됨) → ADD (ii)로 메움, 승인 = 위 예약 변경 승인 한 줄 |
| ⑤ 끊김 알림 | HOLD 사유는 통합 점검·결과 모음이 전달 | 연결(사유별 안내는 없음 — ADD (ii)) |

## 4. 검토 기록
검토 완결: 원문 확인 14/16 · 내장 재검토 1회(Fable 조언 1건 — 반영 4건: 11/19 OPEN_ORDERS 원인·체결가·자동 기록 조건 1275행·FILL_WINDOW_TOO_LONG 시점) · 미해결 3(11/21 실행 결과, 매도 미체결이 주문가능금액에 주는 영향, SALE_PROCEEDS_PENDING_CASH_CONFIRMATION 해제 조건) · 자료 시점 2026-11-20 09:26 KST · 바뀔 조건: 11/21 06:15 reconcile.json이 OK면 2절 NO_CHANGE의 수동 대조 불필요.
