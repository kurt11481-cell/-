---
id: recon-dayfill-k3-proposal-2026-11-20
title: "계좌 대조 — 키움 주간거래 체결 인정 (K3 수정안) 3판"
date: 2026-11-20
class: "K3(권한·한도: reconciliation invariants, CLAUDE.md 66~82행) — 수동 경로: 회사PC worktree Builder → 별도 읽기 전용 Judge → 병합은 사장 본인 터미널 -ApproveAuthority"
source: "진단 docs/claude/recon-dayfill-1120-proposal-2026-11-20.md · 사장 결정 카드 2026-11-20 10:31:48 KST '주간거래 체결도 인정 (K3)'"
authority: "order_authority=false · quantity_authority 변경 없음 · 새 종류의 키움 호출·쓰기 없음(기존 읽기 연산만 — 주간거래 세션의 ust21610 base_dt D 읽기가 실행 때 추가로 요청될 수 있음) · 정책·상태·원장 쓰기 규칙 변경 없음"
---

# 계좌 대조 — 키움 주간거래 체결 인정 (K3 수정안) 3판

## 0. 사장 결정 기록
| 시각(KST) | 무엇 | 근거 |
|---|---|---|
| 2026-11-20 10:31:48 | 방향 채택: '주간거래 체결도 인정 (K3)' | 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9QTU7J3C1FSmMGuCX4yomjX(질문 "주간거래 매도 막힘을 어떻게 해결할까요?", 고른 항목 B, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장) |
| 2026-11-20 10:46:50 | **착수 승인**: 이 수정안 id(recon-dayfill-k3-proposal-2026-11-20, 2판)로 Builder·Judge 시작 | 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9CPkiBkh2XFVNiNt4yr8xzx(질문 "recon-dayfill-k3-proposal-2026-11-20 수정안으로 Builder·Judge를 시작할까요?", 고른 항목 A '착수 (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장, 하네스 wake 기록). 같은 날 KST 1회(CLAUDE.md 69~77행) |
| 2026-11-20 11:12:57 | **착수 승인(3판)**: T3 주문 시각 수정본으로 Builder 이어가기 | 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9GoGrxTNSa3zPYaChwiv6CE(질문 "recon-dayfill-k3-proposal-2026-11-20 3판(T3 주문 시각 수정)으로 Builder를 이어갈까요?", 고른 항목 A '이어서 진행 (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장, 하네스 wake 기록). 같은 날 KST 1회 |
| 2026-11-20 11:31:43 | **병합 승인**: 커밋 d9998bd(브랜치 worktree-recon-dayfill-k3-t3, Judge PASS)를 오늘 병합 | 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9UmuhSC4JjnbdGSyBAVQaGD(질문 "recon-dayfill-k3(커밋 d9998bd, Judge PASS)를 오늘 병합할까요?", 고른 항목 A '병합 승인 (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장). 실행 = 사장 본인 PowerShell 한 줄 docs/claude/recon-dayfill-k3-merge-2026-11-20.ps1(수동 경로라 dev-merge.ps1 대신 전용 스크립트, 오늘 KST만). 스레드는 병합을 실행하지 않음 |

방향 채택은 착수 승인이 아니다. 코드는 아직 바뀌지 않았다.

## 1. 바꾸는 규칙
### 1-1. 체결 시각 창 (auto_core_reconcile.py 96·315~319행)
지금: 주문일 D(ust21150 ord_dt, ET 거래일)의 체결은 D 04:00 ~ D 20:00 ET 안이어야 한다. 밖이면 `FILL_TIME_OUTSIDE_US_SESSION` HOLD.

바꾼 뒤: **D−1 20:00 ET 초과 ~ D 20:00 ET 이하**. 이미 쓰는 주문 시각 창의 아래 끝(320~321행)과 같다(REUSE). moment < D 04:00 ET이면 `segment: "DAY_SESSION"`. 세션 날짜는 D.
- 지금 통과하는 체결의 KST 시각은 하나도 바뀌지 않는다(다른 후보는 24시간 떨어져 늘 창 밖).
- KST 후보 {D, D+1} 중 정확히 하나(반열림 24시간). 10:00:00 KST(EST): D 10:00 = D−1 20:00 ET 제외, D+1 10:00 = D 20:00 ET 포함(시간외 끝).
- 세션 날짜 검사(323~325행): 정규·시간외는 moment의 ET 날짜 == D, DAY_SESSION은 ∈ {D−1, D}(주간거래 창 안에 ET 자정이 있음 — 겨울 KST 14:00~18:00, 여름 13:00~17:00은 ET 날짜 D).
- 관측 근거: 2026-11-20/reconcile.json `I2:FILL_TIME_OUTSIDE_US_SESSION:20261119:3`(ord_dt 20261119 읽기의 3번 행) = snapshot fills[0] SOXL 74주 주문 11:34:06·체결 12:44:27 KST @51.00(= ET 11/18 22:34·22:44). 11/20 06:15 스냅숏 보유 29, d2 매도 정산 3771.28(= 3774.00 − 2.72). 06:15 d1 = 그날·d2 = 다음 영업일 관측(10/21·10/22 스냅숏)으로 d2 = 11/23 = 세션 11/19의 KST D+2 영업일 — 매도 정산 슬롯은 관측으로 맞음(매수는 미관측).

### 1-2. 정산 매칭 기준일 (fill_settlement 557·561·577행)
지금: `first_day = min(last_fill_day)`(체결의 KST 날짜). 그보다 늦은 정산 슬롯·행은 모두 기준 뒤 체결 몫으로 센다.
문제: 주간거래만 있는 세션 D는 last_fill_day = KST D라서, 기준 전 세션 D−1의 정산 슬롯(KST D+1)까지 집계돼 '날짜 2개·세션 1개' → SETTLEMENT_NOT_MATCHED_TO_FILLS HOLD. 연속 거래일 주간거래는 거의 매번 걸린다.
바꾼 뒤: `first_day = min(max(last_fill_day, session_date + 1일))`. 근거: 세션 S의 정산일은 늘 KST S+2 영업일 이후(1-1 관측, 기존 픽스처 test_auto_core.py 49~51행). 정규·시간외 세션은 last_fill_day가 이미 S+1인 경우가 대부분이라 결과가 같다.

## 2. 바꾸지 않는 것
주문 시각 창·FILL_TIME_INVALID·FILL_AFTER_SNAPSHOT, plan_reads·FILL_WINDOW_MAXIMUM_DAYS 14, fill_sessions(ust21610 수량 대조 — 없으면 `FILL_AMOUNT_UNAVAILABLE` HOLD, fail-closed), _assign·carried·D0 규칙, OPEN_ORDERS_PRESENT, B2-N unverified_outflow·ledger_days(743~760, 820~834행), 현금 흐름 증거, I1·I4·I5, 주문표·결정·카드, 권한 값.

## 3. 사장 지침 문구 변경 (order-receipt-process-review-2026-10-09.md 87행, 2026-10-20 19:29 KST)
- 바꾼 뒤(제안): "주문 입력 권장 시간은 그대로 저녁(프리마켓 시작 ~ 정규장 마감). 다만 사장이 주간거래로 넣은 체결도 회사 체결로 인정하고 계좌 대조가 받아들인다(2026-11-20 사장 카드, recon-dayfill-k3)."
- 적용 주체·시점: 병합 뒤 Cowork(또는 사장실 회사PC 스레드)가 문서 변경으로 87행 뒤에 한 줄 덧붙임 + active-decisions 갱신. Builder 범위 밖. 주문표 문구·알림 지시문은 바꾸지 않음.

## 4. 사전 등록 시험 (H1 — Builder 전에 고정, 기대값 바꾸면 이 판 닫힘)
새 파일 `manage-us-stock-strategy/tests/test_auto_core_reconcile_dayfill.py`.
| # | 입력 | 기대 |
|---|---|---|
| T1 | ord_dt 20261119, 주문 11:34:06, 체결 12:44:27 (11/19 실관측) | 체결 1건, filled_at_kst 2026-11-19T12:44:27+09:00, session_date 2026-11-19, segment DAY_SESSION, 오류 없음 |
| T2 | EST: ord_dt 20261102, 체결 10:00:00 | KST 11/03 10:00(시간외 끝), segment 없음 |
| T3 | EST: ord_dt 20261102, 주문 10:00:01, 체결 10:00:01 | KST 11/02 10:00:01 → DAY_SESSION |
| T3b | EST: ord_dt 20261102, 주문 14:00:00, 체결 15:00:00 | KST 11/02 15:00 = 11/02 01:00 ET → DAY_SESSION, 오류 없음(세션 날짜 검사 통과) |
| T4 | EDT: ord_dt 20261021, 주문 09:00:01, 체결 09:00:01 | KST 10/21 09:00:01 = 10/20 20:00:01 ET → DAY_SESSION |
| T5 | 주간거래 시각, 주문 > 체결 | FILL_TIME_INVALID |
| T6 | 스냅숏보다 늦은 주간거래 체결 | FILL_AFTER_SNAPSHOT |
| T7 | 11/20 06:15 재생(기준 rev 43, 103→29, ust21610 base_dt 20261119에 SOXL sell 74 / 3774.00 가짜 응답, d2 슬롯 settlement_date 2026-11-23 SELL 3771.28) | I2 PASS(−74), I3 PASS(잔차 ≤ 1.00) |
| T8 | T7과 같되 ust21610에 SOXL 행 없음 | I3 FAIL, 사유에 `FILL_AMOUNT_UNAVAILABLE:2026-11-19:SOXL` 포함 |
| T9 | 기록 as_of 2026-11-19T23:38:07Z(rev 44) 뒤 실행, 11/19 주간거래 행이 조회 창에 다시 읽힘, 11/20 세션 체결 없음 | 그 체결은 기록 이전 → 집계 0, I2 PASS, I3 PASS(정산 0, 잔차 ≤ 1.00) |
| T10 | 정규장·시간외 기존 시험 전부 | 그대로 통과 |
| T11 | 기준 뒤 주간거래만 있는 세션 D + 기준 전 세션 D−1의 정산 슬롯 KST D+1 + 세션 D 슬롯 D+2 | D+1 슬롯 무시, D+2만 매칭 → I3 PASS |
| T12 | 정규 세션 S 체결이 KST S 23:40(자정 전), S+1 슬롯은 기준 전 세션 몫, S+2 슬롯은 S 몫 | S+2만 매칭 → I3 PASS |

기존 시험 중 기대값을 바꿔도 되는 단언은 아래 **4개**뿐이다(test_auto_core_reconcile_orddt.py). 같은 파일의 독스트링·주석(1~6, 94, 107, 113행)은 새 규칙으로 고쳐도 된다(단언 아님). 그 밖의 단언 변경·삭제·skip 금지.
- 112~115행 `test_kiwoom_day_session_fill_holds`: 12:00 KST 행 → DAY_SESSION 체결 1건. 이름을 `test_kiwoom_day_session_fill_counts_on_its_order_day`로.
- 103~104행 `late`(ord_dt 20261102, 주문 10:29·체결 10:30): KST 11/02 10:30 = 11/01 20:30 ET → DAY_SESSION 체결 1건.
- 105~106행 `early`(주문 17:59:00·체결 17:59:59): KST 11/02 17:59:59 = 11/02 03:59:59 ET → DAY_SESSION 체결 1건.
- 108~109행 EDT(ord_dt 20261021, 주문 08:00·체결 09:30): 체결은 창 안(10/20 20:30 ET)이 되지만 주문 08:00 KST 10/21 = 10/20 19:00 ET가 주문 창 밖 → `FILL_TIME_INVALID:20261021:0`.

## 5. 기본 처분
Judge FAIL·시험 미달·사장 무응답 → NO_CHANGE(지금 규칙 유지, 주간거래 체결 = HOLD → 수동 대조). 노출·권한을 올리지 않는다.

## 6. 병합 전까지 임시 운영 (지금 잠김)
- 2026-11-21(토) 06:15 KST 자동 대조는 같은 11/19 행 때문에 HOLD한다(기록일 11/20 → ord_dt 20261119를 다시 읽음, plan_reads 198~208행 · explain_change 883행).
- 풀기: 11/21 06:15 실행 뒤 Cowork(회사PC 비서실 대화)에서 수동 대조 1회(broker-snapshot-reconciliation.md 2절 112~160행).
  1. `python manage-us-stock-strategy/scripts/reconcile_broker_state.py propose --cash-flow-evidence <11/21 reconcile.json의 cash_flow_evidence.evidence_path 값>` (기간 11/18부터 → S7 보류 covered_through 11-18이 이어서 풀림, 189~209행).
  2. `show` 출력을 원문 그대로 보이고, 경고(TIMING_PLAN_TICKER_CHANGED·POST_APPLY_ALERT_ENGINE_CHECK_FAILED — LITE 등록부 기록 없음, 11/05부터 이어진 표시 문제)를 먼저 알린 뒤 적용·보류를 고르게 함(118~137행).
  3. 가장 이른 읽기 기준 15분 안에(120행) 사장이 그 대화에 `확인 <코드>` 직접 입력 → `apply --confirm <code> --confirmed-via COWORK_CHAT_USER_MESSAGE --user-message "<원문>"`(146~150행) → 수동 분석으로 MATCH 확인(155행). 사장 본인 터미널 경로(170행~, CLAUDE.md 25~26행)도 가능.
  4. 기록 as_of가 KST 11/21이 되면 다음 실행(11/24 화 06:15)부터 11/19 행이 조회 창 밖 → 자동 OK 예상.
- 이 프로젝트 스레드는 apply·코드 입력을 하지 않는다.

## 7. Judge 확인 항목
J1 바뀐 파일이 9절 목록뿐 · J2 창 계산이 zoneinfo로 DST 자동이고 후보가 정확히 하나(T2~T4, T3b) · J3 DAY_SESSION 체결이 ust21610 대조를 빠져나가지 않음(T8) · J4 기존 시험 기대값 변경이 4절 **4개** 단언뿐 · J5 order_authority·quantity_authority·새 종류 키움 호출·상태 쓰기 경로 변화 없음 · J6 참조 문서 241~250행이 새 규칙과 같음 · J7 T9로 지금 잠김이 풀림 · J8 first_day 변경이 정규·시간외 기존 정산 시험 결과를 바꾸지 않음(T10·T12). 마지막 줄 `VERDICT: PASS` 또는 `VERDICT: FAIL`.

## 8. 연결표 (analysis-linkage-map 1절 8번)
| 칸 | 내용 | 상태 |
|---|---|---|
| ① 자료 | 키움 ust21150 체결(ord_dt·cntr_time)·ust21610·ust21160 | 연결 |
| ② 읽는 점검 | auto_core_reconcile.py parse_fills 270~336·fill_settlement 531~600 → I2·I3 → reconcile.json | 연결 |
| ③ 바뀌는 행동 | 대조 OK → 상태 자동 기록 → 07:45 decide G1 통과(주문표 다시 나옴) · S7 현금 흐름 이어짐 | 연결 |
| ④ 사장 행동 | 주간거래 매도 뒤 수동 대조 불필요(ust21610에 담길 때) | 연결(9절 ① 미관측이면 FILL_AMOUNT_UNAVAILABLE HOLD로 알림) |
| ⑤ 끊김 알림 | HOLD 사유는 결과 모음·통합 점검이 전달(지금과 같음) | 연결 |

## 9. 파일·미해결·별건
- Builder 바꿀 파일: manage-us-stock-strategy/scripts/auto_core_reconcile.py(96 근처 주석, 270~336 parse_fills, 531~600 fill_settlement의 first_day 한 줄과 독스트링) · manage-us-stock-strategy/tests/test_auto_core_reconcile_dayfill.py(새) · manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py(4절 4개 단언 + 주석) · manage-us-stock-strategy/references/broker-snapshot-reconciliation.md(241~250행) · docs/claude/recon-dayfill-k3-report.md(보고).
- 미해결(확인 필요): ① ust21610 base_dt D가 주간거래 체결을 담는지 — 첫 주간거래 뒤 실행이 T8형 HOLD면 관측으로 확정하고 후속 수정안 ② 키움 주간거래 정확한 시간(창이 D−1 20:00~D 04:00 ET 전체를 받으므로 결과 영향 없음, 가정과 다르면 FILL_AFTER_SNAPSHOT로 HOLD) ③ 주간거래 매수 정산 슬롯(미관측, 어긋나면 SETTLEMENT_* HOLD) ④ 11/21(토) 06:15의 d1 슬롯 주말 규칙.
- 별건(K3 범위 밖, 일반 변경 후보): auto_core_tickets.py 522행 독스트링·598~603행은 아직 ord_dt = KST 날짜를 가정 → KST 자정~발행 시각 사이 정규장 주문 행이 '발행 전 주문'으로 빠져 ticket_outcome 오분류 가능(recon-dt-report.md 66행 후속 설계안과 같은 문제, 실제 행 관측 확인 필요). 주간거래 행 귀속은 이 K3로 문제없음.

## 10. 검토 기록
- 3판(2026-11-20 11시대 KST): Builder(커밋 7eb9b2b, worktree keen-mestorf-6b7381)가 T3에서 BLOCKED — 2판 T3의 주문 시각 10:00:00 KST = D−1 20:00:00 ET는 바꾸지 않기로 한 주문 시간 창(열린 아래 끝) 밖이라 FILL_TIME_INVALID. 시험 입력 오기입이라 주문 시각만 10:00:01로 고침(기대값 불변, Builder가 기대대로 나옴을 확인). 변경은 T3 입력 한 칸뿐. 새 착수 승인 필요. 참조 문서 276~277행 정산 기준일 설명은 병합 뒤 문서 변경으로 맞춤(3절과 같은 주체).
- 1판 내장 재검토(Fable, 진단): 반영 4건. 2판 독립 재검토(Opus · high, K3): 지적 8건 중 반영 7건(세션 날짜 검사 {D−1, D}·정산 기준일 (a)안·T9 조건·단언 수 통일·T1/T7/T8 명세·6절 절차·승인 경로/범위 문구), 8번 주문표 귀속은 '별건'으로만 기록(K3와 무관, 근거 auto_core_tickets.py 521~614행 재검토 보고).
- 검토 완결: 원문 확인 14/16 · 내장 재검토 2회(반영 11건) · 미해결 4 · 자료 시점 2026-11-20 11시대 KST · 바뀔 조건: 키움 사양에 주간거래 ord_dt 정의 문구, 다음 주간거래 체결의 ust21610 관측.
