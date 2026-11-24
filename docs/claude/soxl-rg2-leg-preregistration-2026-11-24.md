---
id: soxl-rg2-leg-preregistration-2026-11-24
type: preregistration (고정)
status: 고정 — 이 파일의 sha256은 soxl-rg2-leg-preregistration-2026-11-24.sha256에 있고, 계산 파일이 실행 전에 대조한다
as_of: 2026-11-24 KST
decision: soxl-rg2-leg-1124 — 2026-11-24 13:50:43 KST 사장 결정 카드 '과거 자료로 1회 시험 (D3 예외)'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9DAhQaxR9BLYUv1D7xXtJMj, 질문 "SOXL 50일선 조건 시험을 어떻게 할까요?", 누른 계정 = 사장, 사장실 회사PC 스레드 'SOXL 매수 조건 시험 설계'). 카드 문구에 'D3 예외'가 있었으므로 이 문서·사이드카·계산 파일·결과 파일 = D3 동결 예외 1건(선례 strategy1101-score-preregistration-2026-11-02.md 6행)
default: NO_CHANGE(현행 R-REC1·코어 그대로). '후보'여도 규칙은 바뀌지 않고 K3 안건으로만 올라간다
consumers: 2027-03-31 '3배 상품 0으로 갈지' 결정 카드(masterplan-2026-11-18.md 219행, 관제판 strategy-1101-0331) · active-decisions.md soxl-rg2-leg-1124 행
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# SOXL 매수 관문 'SOXL 자기 50일선' 다리 — 과거 자료 1회 시험 사전 등록

## 1. 질문과 가설
- 질문: R-REC1 회복 관문 RG2의 후보 다리(SOXL 종가 ≥ SOXL EMA50, recovery-gate-R-REC1-2026-10-09.md 37행, auto_core_rules.py 947~948행)가 3배 상품 재매수를 늦춰 손해를 보는가.
- H1: SOXX 쪽 조건이 다 찬 뒤에도 SOXL은 자기 EMA50 아래에 더 오래 머물고, 그 늦춤 비용이 피한 손실보다 크다.
- H0(기본): 차이가 없거나 늦춤이 가짜 반등 손실을 막아 상쇄한다.

## 2. 이 시험의 위치 (이미 본 자료)
- 사건·RG1·RG3·RG4는 SOXX로 판정하므로 사건 목록은 이미 세 번 본 SOXX 2011~ 사건이다(r-rec1-r3-replay-results-2026-10-16.md 103행 — 그 문서의 기본 처분, 사장이 이번 카드로 연 것).
- SOXL 가격은 10/01 신호 워크포워드와 10/13 산술에서 이미 봤다.
- 그래서 결과는 '과거 자료로 본 경향'이며, '후보'가 나와도 그것만으로 규칙을 바꾸지 않는다.

## 3. 비교 규칙
| id | 정의 | 역할 |
|---|---|---|
| V0 | 운영 auto_core_rules.rrec1 그대로(가져와 실행), candidate = SOXL | 기준 |
| VA | rrec1 사본에서 RG2 한 줄만 바꿈: `rg2 = bench_ok`(948행의 cand_ok 제외). 사건(EV5 포함)·RG1·RG3·RG4·DS1·시간 소멸·창 이탈은 V0와 같다 | 유일한 채택 후보 |
| VB | 같은 줄에서 SOXL 다리를 `candidate close ≥ candidate ema20`으로 | 기록만(11/23을 본 뒤 나온 안) |

## 4. 자료
- 벤치마크: stock-strategy-system/backtests/soxl_signal_inputs_2026-10-01/SOXX_combined.csv (sha256 00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6).
- 후보: 같은 폴더 SOXL_combined.csv (sha256 56e612b764a7c5df48b1f009efb300badba34dfc1d2cc262946a0d33a7502c24).
- 두 파일 모두 r3와 같게 open·high·low·close에 adjclose/close 비율을 곱해 쓴다.
- 공통 날짜: 2010-03-11 ~ 2026-09-29. 2026-09-30 이후 자료는 쓰지 않는다.
- 운영 코드: manage-us-stock-strategy/scripts/auto_core_rules.py (sha256 ba979d234ea95644c6bb78456e8f500974060ab96c23f8dafe97281acaa4ea6a)와 portfolio_exposure.py(sha256 9a5360c58f55b18a36c906c011132588152e85cd20cce6bc768288a7a1b1fb09)의 _sample_std(r3 방식으로 그 함수만 가져옴). 해시는 원시 바이트 기준.
- 입력: thesis_damage=[](RG1 = 2세션 경과만), ev3_user_dates=[], research_sessions=None, card_accepted_on=None. 지표 계열은 전체 공통 날짜로 한 번 만들고 세션마다 최근 130세션만 넘긴다(r3 I2).
- 이 단순화 때문에 RG1·EV3는 재현하지 않는다(r3와 같은 한계).

## 5. 에피소드와 측정
- 허용 = status == "ok", 막힘 = no 또는 unk. 평가는 공통 날짜 131번째 세션(2010-09-16, 지표 130세션 확보)부터. V0가 허용이었다가 막힌 첫 세션 t0를 에피소드 시작으로 한다. 조건: t0 ≥ 2010-09-01이고 [t0−59, t0] 모든 세션에 SOXX·SOXL σ60이 있다.
- V0가 막힌 한 구간 = 에피소드 1개. 그 안에서 VA가 다시 막혀도 VA는 첫 매수를 창 끝까지 보유한 것으로 본다(매도 규칙 없음). VA의 두 번째 이후 열림은 세지 않는다. 에피소드 창은 서로 겹칠 수 있어 30·15건은 독립 표본 수가 아니다.
- VA는 V0보다 늦게 열리지 않는다(RG2가 더 넓음, 7절 3). 에피소드는 V0 기준 하나로 묶고, 세 변형의 t0 이후 첫 허용 세션 u_V를 각각 찾는다.
- 매수 = u_V 다음 세션 종가 × 1.001(r3 I7). 그 세션 인덱스를 f_V로 둔다.
- 같은 창 비교: 창 = 인덱스 f_A ~ f_A+60(매수 세션 포함 61세션, 수익 구간 60세션). f_A+60이 자료 안에 없거나 VA가 끝내 안 열리면 '오른쪽 검열'로 빼고 수만 센다. '전체 에피소드' = 오른쪽 검열을 뺀 수.
  - 창 안 매수 = f_V < 창 끝(f_A+60). f_V ≥ 창 끝이거나 끝내 안 열리면 그 변형은 창 안에서 못 산 것으로 보고 R_V = 0, MAE_V = 0(현금), d = '창 밖'.
  - R_V = 창 끝 종가 ÷ 매수가 − 1. MAE_V = (매수 다음 세션 ~ 창 끝 최저 저가) ÷ 매수가 − 1.
  - ΔR = R_A − R_0, 지연 d = f_0 − f_A(V0가 창 안에 못 사면 '창 밖'으로 따로 셈).
- 묶는 집합: B = d ≥ 1 이거나 V0가 창 안에 못 산 에피소드(다리가 실제로 걸린 경우). d = 0이면 두 변형이 같다.
- 반쪽: t0 < 2018-07-01 / ≥ 2018-07-01.
- VB 기록: 창은 VA와 같은 [f_A, f_A+60]. B_VB = R 또는 MAE가 V0와 다른 에피소드. VB가 V0보다 늦으면 d_vb < 0. VB가 끝내 안 열리거나 창 밖이면 현금(0). VB에는 판정을 붙이지 않는다.

## 6. 판정 (결과 3종 — 처분은 모두 NO_CHANGE, '후보'만 K3 안건)
- **판정 불가**: 전체 에피소드 < 30 또는 |B| < 15, 또는 7절 자체 시험 실패. 현행이 맞다는 근거가 아니다.
- **후보(VA)**: 아래 네 개 모두.
  1. B에서 ΔR 중앙값 ≥ +3.0%p.
  2. B의 MAE_A 10번째 백분위수 − B의 MAE_0 10번째 백분위수 ≥ −3.0%p(numpy percentile, linear — 에피소드별 차의 백분위수가 아님).
  3. 두 반쪽의 B 각각에서 ΔR 중앙값 > 0(반쪽 |B| < 5면 그 반쪽은 미충족으로 본다).
  4. B의 MAE_A 최솟값 − B의 MAE_0 최솟값 ≥ −5.0%p(같은 에피소드일 필요 없음).
- 읽는 법: V0가 창 안에서 늦게 사면 MAE_0 관측 구간이 짧고, 못 사면 0이다. 그래서 2·4는 VA에 불리한 쪽으로 기운 기준이고, '기준 미달'은 '현행이 낫다'는 근거가 아니다.
- **기준 미달**: 그 밖.
- 보고 전용(판정에 안 씀): 전체 에피소드 ΔR 평균·중앙값, d 분포(B의 d 최소·중앙·최대와 '창 밖' 수), 열림 종류 변형별 건수(open = 회복 확인, decay = 시간 소멸, no_event_in_window = 창 이탈), VB 값. 모두 결과 JSON의 episodes에서 그대로 센다.
- 결과를 본 뒤 기준·변형·자료를 바꾸지 않는다.

## 7. 자체 시험 (하나라도 실패하면 멈추고 결과 파일을 쓰지 않음)
1. 입력·코드 해시가 4절과 같다(--self-test·--run 모두). 사이드카 형식 = `<사전 등록 sha256> <파일명>` 다음 줄 `runner <계산 파일 sha256>`, 원시 바이트 기준. 사이드카·계산 파일 대조는 --run에서만 한다.
2. VA 사본에서 RG2 줄을 원래대로 되돌린 사본이, 실제 자료의 모든 평가 세션에서 운영 rrec1(V0)과 status·open·rg·closed_at이 같다.
3. 모든 세션에서 V0가 허용이면 VA도 허용이다. 깨지면 멈춤. VB는 이 조건이 없다(EMA20이 EMA50보다 높을 수 있어 VB가 V0보다 늦게 열릴 수 있음 — VB의 첫 허용은 t0 이후 첫 허용으로 그대로 적는다).
4. 합성 자료 1건: SOXX가 EMA50 위·SOXL이 EMA50 아래인 날 V0는 막히고 VA는 열린다.
5. 결과 파일이 이미 있으면 실행하지 않는다(1회). 자체 시험·해시 대조 실패로 성과 계산 전에 멈춘 실행은 성과 값을 만들지 않으므로 1회에 넣지 않는다(고친 뒤 문서·코드가 바뀌면 다시 고정). 결과 JSON이 한 번 쓰이면 끝이다.
6. 고정 전 점검 기록(2026-11-24, Fable 독립 점검): 합성 난수 자료(실제 자료 아님) 149건으로 episodes의 R·MAE·d를 독립 계산과 대조해 일치. 창 끝 매수 해석 1건만 달라 5절에 반영했다.

## 8. 하지 않음
- 다른 이동평균 길이·변형 추가, SOX 1994~2010·다른 후보 재생, 2026-09-30 이후 자료.
- 코어·정책·예약·카드·통합 점검 변경, 주문·수량·가격 제안, 3배 10% 상한 변경 제안.
- '후보'일 때 경로: K3 안건(권한 자리 순번, active-decisions.md 131·146행) → Builder(worktree)·독립 Judge → 사장 PowerShell `-ApproveAuthority` 병합. 함께 볼 곳: R-REC1 문서 37행, 코어 rrec1, 통합 점검 규칙·독립 계산기(확인 필요), '다음 회차 RG2 유지'(R-REC1 41행) 구현 위치(확인 필요).

## 9. 실행
- 계산 파일 docs/claude/soxl_rg2_leg_replay.py. 사장실 회사PC 스레드가 입력 사본으로 클라우드 컨테이너에서 `--self-test` 뒤 `--run` 1회. 결과 docs/claude/soxl-rg2-leg-results.json · soxl-rg2-leg-results-2026-11-24.md.
- 결과 한 줄을 active-decisions.md soxl-rg2-leg-1124 행에 적고, 관제판 strategy-1101-0331 자료 목록에 연결한다.

## 10. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)
| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| soxl-rg2-leg-results-2026-11-24.md | 사장실 회사PC 스레드, 2026-11-24 1회(9절) | 2027-03-31 결정 카드 자료(masterplan-2026-11-18.md 219행, 관제판 strategy-1101-0331 재개 2027-03-17) · active-decisions.md soxl-rg2-leg-1124 행 | 결정 카드 자료 한 줄. '후보'면 K3 안건 | 관제판 strategy-1101-0331 작업 메모에 결과 파일 경로가 있어 그 작업을 여는 스레드가 파일 없음을 본다 | 연결(관제판 메모는 이 스레드가 결과와 같은 날 단다) |
