---
id: f-evo-loop-s1-oi-verdicts-2026-11-07
type: learning-record
status: current
as_of: 2026-11-13 14:3x KST
label: POST_HOC_ENCODED_D
authority: "order_authority=false · quantity_authority=none · 학습 기록 전용 — 어떤 셈·발견·매매 근거에도 넣지 않음(사전 등록 11절)"
preregistration: "docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md 11절 (raw sha256 cd370982…830b183d53 = 사이드카 .sha256 일치, 2026-11-13 확인)"
consumers: "f-evo-loop 2단계 · 다음 SOXL·MVLL 카드 (사전 등록 11절 '기록 위치')"
written_by: "사장실 회사PC 스레드 '지금 진행할 작업 안내 (11/13)' — 코디네이터 지시 '시스템 몫 진행'(승인 불필요, 11/03 사장 지시 '결정 방치 없이 스스로 해결')"
---

# ③-a 옛 지시서 4건 1회 판정 (사전 등록 11절)

## 0. 결론

| 지시서 | 사전 부검 쪽 | 사전 축하 쪽 | 계산 |
|---|---|---|---|
| OI-20261008-MVLL-1 | NOT_SCORABLE | NOT_SCORABLE | 11절 표 그대로 '불가'(MRVL 키움 종가 이력 없음·옵션·R0) |
| OI-20261008-MVLL-2 | NOT_SCORABLE | NOT_SCORABLE | 같음 |
| OI-20261008-SOXL-1 | **NOT_HIT** (계산 가능 신호가 창 끝까지 안 맞음, PWR 수동 신호는 판정 안 함) | **PARTIAL — 계산 가능분 HIT** (SOXX < EMA20 연속 2세션 10/9·10/12, PWR 수동 신호는 판정 안 함) | 일부 |
| OI-20261009-SOXL-2 | **NOT_HIT** | **HIT** | 전부 |

- 한 줄: 두 SOXL 지시서 모두 '사전 축하'(약세 쪽) 신호가 창 첫머리에 맞았고, '사전 부검'(반등 쪽) 신호는 창 안에서 한 번도 맞지 않았다. 창 동안 SOXX는 10/7 대비 −33%(분할 보정, 11/05), SOXL은 10/9 대비 −67%(11/06, 45.925/139.705)였다.
- 이 표는 2026-10-16에 10/15 종가까지 일부 결과를 본 뒤 부호화했다(**POST_HOC_ENCODED_D**). 그래서 '맞았다'는 것을 규칙 성능 증거로 쓰지 않는다. 버킷 셈(30건)·발견 규칙(4절)에 넣지 않는다.
- 자료가 빈 날 없음 → 11/14로 미루지 않음(11절 '자료가 빌 때' 해당 없음). 기한 11/21 안.

## 1. 자료

- SOXX 종가: `workspace/outputs/regular-session-closes/history/SOXX.close-history.json` — 2026-04-01~2026-11-12, 157세션, continuity CONTIGUOUS(빈 세션 없음), 창 안 행 모두 verified true.
  - **3:1 분할(효력 2026-11-05, corporate-actions.json 2번째 항목 · iShares 공지 · 키움 dt 20261105)**: 11/04 이전 종가를 3으로 나눠 맞췄다(이 문서의 판단 — 11절은 '종가 이력'만 적고 분할 처리를 정하지 않았다). 분할은 창 마지막 날(11/05)에만 걸리고, 판정을 가른 세션(10/9·10/12)과 '≥ ×1.05' 비교는 모두 분할 전 자료끼리라 보정 여부와 무관하게 같은 결과다.
  - EMA20: SOXX는 decision.json `symbols`에 없어(10/13 뒤에도) 11절대로 종가 이력의 연속 구간(4/1~)에 `auto_core_rules.ema_series`(manage-us-stock-strategy/scripts/auto_core_rules.py 160행 — 첫 20개 단순평균 시드, α=2/21)와 같은 식을 손으로 적용했다(코어 코드를 실행하지 않음).
- SOXL 종가·EMA: 각 날 `workspace/outputs/auto-core/<run_day>/decision.json`의 `symbols.SOXL.indicators`(코어 값, approximate_close true = 키움 30분봉 근사 종가). 10/12~11/06 평가 세션 20개 모두 있음(빈 날 없음).
  - SOXL 10/9 종가 = 10/12 평가 decision(run_day 2026-10-13)의 `previous_close` 139.705.

## 2. SOXL-1 (OI-20261008-SOXL-1, 세션 10/8 · 창 10/9~11/5)

- 기준: SOXX 10/7 종가 582.87(분할 보정 194.29) → ×1.05 = 204.00(보정).
- 사전 부검 ① SOXX 종가 ≥ 204.00 연속 2세션: 창 안 최고 186.60(10/9) → **안 맞음**. ② PWR 상대 약세(수동): 판정 안 함. → 계산 가능한 신호가 안 맞았으므로 NOT_HIT.
- 사전 축하 ① SOXX 종가 < EMA20 연속 2세션: 10/9 186.60 < 186.96 · 10/12 181.62 < 186.45 → **맞음(10/12에 성립)**. 창 안 20세션 중 19세션이 EMA20 아래(10/28만 173.91 > 173.42). ② PWR EMA20 위 유지(수동): 판정 안 함. → PARTIAL(계산 가능분 HIT).

## 3. SOXL-2 (OI-20261009-SOXL-2, 세션 10/9 · 창 10/12~11/6)

- 사전 부검 ① SOXX 종가 ≥ 10/9 종가 559.79(보정 186.60) × 1.05 = 195.93 연속 2세션: 창 안 최고 181.62(10/12) → 안 맞음. ② SOXL 종가 > EMA20 연속 2세션: 창 안 모든 세션에서 종가 < EMA20(가장 가까운 날 10/28 107.485 < 111.761) → 안 맞음. → **NOT_HIT**.
- 사전 축하 ① SOXL 10/9 종가 139.705 < 144.2 → 맞음. ② SOXL 10/12 종가 128.36 < EMA50 139.47(코어 값) → 맞음. → **HIT**.

## 4. 남은 것·한계

- 두 쪽 모두 HIT일 수 있다는 11절 규칙상 SOXL-2는 한쪽만 HIT이다. 단 축하 쪽 신호 둘이 창 첫 이틀(10/9·10/12)짜리라, 10/16 부호화 때 이미 보였던 값이다 — 라벨이 그 이유다.
- PWR 수동 신호 2개는 이번에 판정하지 않았다(11절 'PARTIAL: 수동 신호가 섞임(계산 가능한 것만 표시)').
- Failure Museum pending 1건(RESULT:bf7bc5f3…:ANALYSIS:h20, SOXL 10/01 HOLD h20 −53.0%, journal-scores 20261108T002001Z)은 이 판정과 별개다. 사전 등록 3-5대로 다음 SOXL 카드 세션이 '직전 결정 결과'를 볼 때 채운다(빈 칸은 아무것도 막지 않음).

## 5. 결론을 바꿀 조건

- SOXX 종가 이력이 다시 받아져 10/9~10/12 값이 바뀌면 SOXL-1 축하 쪽을 다시 본다. 다른 결론은 창 안 여유가 커서(창 안 최고 SOXX가 부검 문턱까지 SOXL-1 +9.3%·SOXL-2 +7.9% 모자람) 자료 소폭 수정으로 바뀌지 않는다.
