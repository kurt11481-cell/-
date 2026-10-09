---
id: fx1009-fx4-record
title: FX-1009 fx-4 기록 — 현금 정의 통일(관제판 cash-def-k3)
date: 2026-10-09
class: K3
plan: docs/claude/fx1009-fix-plan-2026-10-09.md 5-4절 · 부록 A-4
builder_prompt: docs/claude/fx4-cash-def-builder-prompt-2026-10-09.md
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: fx-4 Builder(시작 조건 확인) · fx-4 Judge · 재고정 단계 · 관제판 cash-def-k3 · fx-6 마감 점검
---

# 0. 상태 (2026-10-09 15:2x KST)
- 완료: 1단계 범위 확인, 2단계 영향 점검, 3단계 위원회(Full), 사용자 선택 A, 4단계 Builder 지시문 초안
- 완료: 사용자 지시문 승인(5절, 15:17 KST)
- 대기: 측정 V1(4절)
- 아직 안 함: Builder 실행, 코드 변경, 정책·상태 변경

# 1. 범위 (읽기 전용 확인)
- 지금 정의: kiwoom_broker_shadow.py 75~77행 min(fc_pymn_alowa, fc_ord_alowa) → 339행 patch available_cash_usd → 397행 basis MIN_WITHDRAWABLE_AND_ORDER_AVAILABLE_USD
- 고정(pin) 파일 중 바꿀 것
  - kiwoom_broker_shadow.py
  - kiwoom-reconciliation-proposal.schema.json(basis const)
  - manual_data_guards.py(226행: 브로커 대조가 min과 상태 현금을 비교)
  - test_manual_data_guards.py
  - kiwoom-acceptance-pin-scope.json(재고정, 45cf 허용 목록 정리 O6)
- 고정 아닌 파일
  - kiwoom-broker-shadow.schema.json, 표시 문구(locales)
  - broker_visibility_audit·portfolio_decision_dashboard·render_beginner_portfolio_report(settled_available_cash 참조)
  - references 2개, 테스트들
- 바꾸지 않는 것
  - run_manual_portfolio_analysis.py: 이미 order_available_cash 사용
  - S7 코드, portfolio_policy_gates.py(현금 범위 이름 유지)
  - 정책·상태 파일
- 선행 확인: fx-1 커밋 a2bc25c, Q7 = 통합증거금 미가입(fx-0 결정 기록)

# 2. 영향 (읽기 전용 확인)
- S7 자기자본 = 확인된 보유 수량 × 종가 + 상태 파일 available_cash_usd
  - 근거: portfolio_exposure.closing_equity, run_portfolio_exposure_review.reconstruct_snapshots
  - S7 코드를 고치지 않아도 정의가 함께 바뀐다.
- 지금 어긋남: 보유 수량(poss_qty)은 매도 즉시 줄어드는데, 현금(min)은 정산 전 매도대금을 뺀다.
  - 정산 전 기간에 자기자본이 실제보다 작고 E는 크게 나온다.
  - 정산 뒤에는 두 정의가 같다.
- 증거: 최신 S7(세션 2026-10-08)은 E 2.2365 · N 1.9544 · HARD_CEILING, 멈춤 사유는 HWM 보류·입출금 미신고·HARD_CEILING
  - 같은 보유를 주문 가능액 기준으로 보면 N 1.62 · E 1.857(OI-20261009-SOXL-2 표)
  - 매도 뒤 매수 멈춤(sale hold)은 다음 대조에서 풀리고 정산을 기다리지 않는다. 10/8 결과도 이미 풀린 상태였다.
- 바뀌는 방향
  - E: 정산 전 기간에 낮아진다.
  - 매도 쪽: 가짜 HARD_CEILING과 긴급 줄이기가 사라진다.
  - 매수 요건 ②의 S7 E < 1.85: 더 빨리 통과할 수 있다 → 매수가 열리는 방향
  - 매수 가능 현금 칸: 이미 주문 가능액(v3.12.1)이라 변화 없다.
- 지금 매수 판정은 이미 큰 E 쪽이다. 통합 점검 ②는 N(예수금 기준)과 S7 E(min 기준) 중 하나라도 1.85 이상이면 막는다.

# 3. 위원회 (Full, 2026-10-09 15:0x KST — 거래 근거 아님, K3 승인 아님)
- 설계자: 조건부 진행(min은 매도 쪽 오류를 내고, 체결 뒤 주문 가능액은 '예상 매도대금'이 아님). 다른 세 목소리를 듣고 바뀜.
- 회의론자: 바꾸지 말자. 매수 판정은 min, 주문 가능액은 별도 필드에 참고로만 둔다.
- 실용주의자: 보류. E 두 개를 표시하고, 매도 직후 읽기 전용 조회로 미확인 3건을 먼저 확인한다. 재고정 수작업 부담이 크다.
- 비판자: 보류. 매수 판정에는 큰 E를 쓴다. 매도 뒤 매수 멈춤이 정산 전에 풀리면 낮게 찍힌 E로 레버리지 상품을 살 수 있다.
- 합의(셋 모두): 2단계에서 계획한 가드 "주문 가능액 > 외화 예수금 + $1"은 이중 계산을 못 잡는다(예수금도 정산 전 대금을 포함). 같은 조회 안에서 수량·현금이 맞는지 보는 검사와 미체결 매수 검사가 따로 필요하다.
- 가장 강한 반대(비판자): 체결 직후 보유 수량이 안 줄었는데 주문 가능액에 대금이 먼저 잡히면 E가 과소 → 매수 요건 ② 통과 → 실제 E 상한 초과. EXPECTED_SALE_PROCEEDS ≠ VERIFIED_ORDERABLE_CASH 위험이 이 시스템에서 생기는 실제 경로다.
- 전제 바로잡기: "FX-1009 동결 때문에 안 된다"는 틀렸다. fx-4는 계획 단계(5-4절)이고, $1 가드는 Q7 결정 기록에 있다.
- 사전 부검: 매도 체결 직후 대조에서 수량은 그대로인데 대금이 잡혀 E가 낮게 찍히고 SOXL 추가 매수가 열렸다.
- 사전 축하: 측정 2회 + 검사 3개로 Judge를 통과하고, 세 경로가 한 정의가 되어 가짜 HARD_CEILING이 사라졌다.
- 사용자 선택: 2026-10-09 15:10 KST "a로 진행" → A안
  - 지금은 정의 유지
  - Builder 시작 조건 = 측정 V1
  - 검사 ⓐ 예수금 초과, ⓑ 같은 조회 수량·현금 정합, ⓒ 미체결 매수·조회 실패 → 하나라도 못 맞추면 확인 필요(적용 불가)
  - 현금 구성은 제안에 기록
  - S7 코드·매도 뒤 매수 멈춤은 그대로
  - fx-4 목표일 10/16 유지

# 4. 측정 V1 (Builder 시작 조건 — Cowork, 읽기 전용)
- 시점: 매도 체결 뒤 첫 조회
  - OI-20261009-SOXL-2(22주 LOC)가 10/9 미국 장 마감에 체결되면 10/10 아침에 한다.
  - 미체결이면 다음 매도 체결 뒤로 미룬다. 10/16 안에 매도가 없으면 사용자에게 일정을 묻는다.
- 방법: kiwoom_query(options "profile": "실전계좌", "mode": "real"). 아래 조회를 15분 안에 함께 한다.
  - 잔고(qty, poss_qty)
  - 외화 예수금(fc_entra, fc_pymn_alowa, fc_ord_alowa)
  - 예수금 상세(d1/d2 setl_dt, *_sell_excta, *_buy_excta)
  - 미체결
  - 체결 내역
  같은 날 06:40 통합 점검 기록(현금 세 칸, "미결제 매매 있음" 줄)과도 대조한다. 8005 등 인증 오류가 나면 재발급하지 않는다. 그 조회는 실패로 적고, 점검 기록만으로 V1-a·b를 판정한다(V1-c는 미측정).
- 기록 원칙: 계좌번호·잔액 원값은 적지 않는다. 차이 값과 수량만 적는다.
- 판정 항목
  - V1-a: ord − entra ≤ $1
  - V1-b: ord − pymn > $1이면, 체결 내역의 매도 종목에서 qty − poss_qty = 매도 수량
  - V1-c: (정산 전 매도 − 매수 금액) − (ord − pymn)이 $1 이내 → 일치 / 불일치 / 미측정
  - V1-d(기록용): 미체결 매수가 있으면 주문 가능액이 그만큼 줄었는지
  - V1-e(기록용): 키움 도움말·명세에서 미결제 매도대금 재매수 제약 → 확인 필요 표시
- PASS = V1-a·V1-b 통과. 10/9 관측(MVLL qty 278 vs poss_qty 159, 정산 전 대금 있음, ord ≈ entra 1센트 차이)이 1번째 표본이고, V1이 2번째다.
- V1-c가 "일치"면 Builder가 검사 ⓑ2를 구현한다. 아니면 b1만 구현하고, 남는 위험을 Builder 보고 맨 위에 적는다.

## 4-1. V1 결과
- (대기)

# 5. 사용자 승인
- Builder 지시문(docs/claude/fx4-cash-def-builder-prompt-2026-10-09.md): 2026-10-09 15:17 KST 사용자 원문 "fx-4 Builder 지시문 승인" (초안 그대로, 수정 요청 없음). Builder 실행은 여전히 측정 V1 PASS 뒤(시작 조건 2·3).

# 6. 다음 단계
1. 사용자 지시문 검토·승인 → 5절 기록
2. 측정 V1 → 4-1 기록
3. 사용자 커밋 → claude --worktree fx-cash → Builder
4. Cowork 사전 확인 → Judge 지시문 → 별도 세션 Judge
5. 병합 → 재고정(10/7 절차) → 실측 → 관제판 done
