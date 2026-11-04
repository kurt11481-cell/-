---
id: t2rc-c2-sell-check-2026-11-04
type: check-record
status: current
as_of: 2026-11-04 09:05 KST
summary: "T2 C2(매도) 첫 일치 — 비교 모드 매도 주문표 AT-20261104-SOXL-1이 t2-c2-sell Judge 조건 1·2·4를 채움. '켜' 충족 표시는 C1 공식 셈 확인 전 금지(조건 5)."
sources: t2-c2-sell-judge-report.md 56~61행 · t2-rc-preregistration-2026-10-14.md 56행 · active-decisions.md C절 t2-c2-sell 행
---

# T2 C2 매도 첫 일치 확인 (2026-11-04 KST)

결론: 11/04 07:45 KST 코어가 낸 비교 모드 매도 주문표 AT-20261104-SOXL-1은 08:40 KST 독립 계산기와 전 항목 일치했고, Judge 조건 1(세는 세션)·2(매도 수량 독립 확인)·4(계산기 sha)를 채운다. 따라서 C2(주문표 1건 일치)는 매도 1건으로 충족으로 센다. 주문표는 비교 모드라 입력 대상이 아니다(대시보드 runs 11/04 core.tickets note "비교 중(입력 대상 아님)"). 이 문서에는 계좌 금액·수량을 적지 않는다(원문 파일 경로만).

## 조건 1 — 세는 세션
- 원문: workspace/outputs/auto-core/2026-11-04/t2rc-check.json (08:40 KST).
- verdict "MATCH" · counts_for_c1 true · decision.decision_mode "compare" · ticket_leaks [] · input_sha_mismatch [] · input_path_mismatch [] · ORACLE_DATA_GAP 없음.
- 주문표 AT-20261104-SOXL-1: not_recomputed [] · should_exist true · price·qty·cash·G0·G1·G2·G3 각각 match true · c2_item_match true.
- c1: oracle_open = core_candidates = [SOXL sell], missing·extra 없음.

## 조건 2 — 매도 수량 독립 확인
① 목표 비중 출처: S7 reduce 권고 order 3(보충 ETF, basis SOXL, urgent, grade D) target_weight 0.209 — workspace/outputs/auto-core/2026-11-04/s7/2026-11-03/portfolio-exposure-review.20261103T224508671906Z.json. 카드 EXIT·TRIM 목표 없음.

② 손계산(S7 밖 원자료, 이 스레드가 따로 짠 계산):
- 보유 수량: 키움 잔고 스냅샷 workspace/outputs/auto-core/2026-11-04/kiwoom_broker_snapshot.shadow.json(= result.json applied).
- 종가: workspace/outputs/regular-session-closes/history/{SOXL,BE,LITE,SOXX}.close-history.json 2026-11-03(verified true). 이 구간에 네 종목 분할 없음(corporate-actions.json은 MVLL 2026-06-26 분할 1건뿐).
- 배수(명목): SOXL 3 · BE 1 · LITE 1. 정책 정의(portfolio_exposure.py 11·242-259행): E = max(N, V), N = Σ 비중 × 배수, V = std(Σ 비중 × 일수익률) ÷ std(SOXX 일수익률), 표본 표준편차, 공통 구간 2026-04-01~2026-11-03 수익률 149세션.
- 지금 비중: SOXL 0.3826 · BE 0.3039 · LITE 0.3104 → N 1.7622 · V 2.0175 (S7 E 2.0175와 같음).
- SOXL 비중만 0.001 단위로 내려 N ≤ 1.55 그리고 V ≤ 1.55가 되는 첫 값 = 0.209 (그때 N 1.2414 · V 1.5486, S7 projected_nominal 1.2414 · projected_sox_equivalent 1.5486과 같음). 연속값으로 V = 1.55가 되는 비중은 0.2095.
- 줄일 몫 delta = 보유 − floor(0.209 × 총자산 ÷ 기준가)(t2rc-oracle.py 2058행 방식, 파일 LF 정규화 sha 41bc56df… 같음): 손계산 값이 계산기·코어 delta와 같고, r 1/2 행 수량도 같다(수량 값은 위 원문 파일).
- 판정: 목표 비중 0.209는 정책 target_exposure 1.55(alert_policy.json, S7 policy 2026-10-03-s5-r2-p-earn)에서 나온 값이 맞다.

③ 재배치 경로: SELL_TO_CASH, 후보 없음(BE·DELL·LITE·MU·PWR 모두 매수 요건 미달로 건너뜀 — t2rc-check redeploy.skipped).

④ r_max 1/2 · 근거 종류: 약한 단서 new_low·trend_break(구성 "카드 표 0 + 새 0"), 사유 S7_REDUCE_3. 매도 r_max가 카드에 정의된 종류만으로 1/3을 넘는 것은 기존 결정(t2rc-corefix 5=b)이며 Judge 6절대로 기록만 한다.

## 조건 4 — 계산기 sha
t2rc-check.json oracle_sha256 41bc56df2981606f12653d10efa0f5f6339b1b19fbde6204b05aaca105370466 = Judge 판정 때 값. 바뀌면 이 일치는 다시 본다.

## 아직 남은 것 (이 기록으로 바뀌지 않음)
- 조건 5: C1 공식 셈(10/31 MISMATCH가 셈을 다시 시작하게 하는지) 확인 필요 → '켜' 충족으로 표시하지 않는다.
- 조건 6: '켜' 판정 전 대시보드(v33)가 보류 주문표를 "주문표 확인 대기 — 입력 금지"로 보이는지 페이지 코드로 다시 확인.
- 조건 3: 켠 뒤 첫 매수 주문표가 확인되기 전까지 비서실 첫 보고 주문표 줄에 "매수 첫 주문표 미검증".
- 그 밖 관문: 대조 OK 4/5(10/30·10/31·11/03·11/04, mode apply) · 비교 연속 2/5(compare.json streak 2, required 5, 11/04 unexplained 0) · R3 사장 직접 "켜".
