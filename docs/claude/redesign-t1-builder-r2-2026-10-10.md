---
id: redesign-t1-builder-r2-2026-10-10
title: 재설계 T1 Builder 추가 지시 r2 — 실측으로 찾은 결함 3건 (Judge 전에 같은 worktree에서 수정)
date: 2026-10-10
from: Cowork 실측(키움 읽기 전용 조회 2026-10-10 10:5x~11:0x KST, 실전계좌·real) + Builder 보고 4절 위험 2·3·4·6 검토
class: T1과 같음(권한·한도 변경의 일부). 범위·금지는 docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md 3절 그대로
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 기존 worktree `auto-core-t1` 이어서 · 이유: Judge 전 같은 Builder 최소 수정**

## 0. 왜 (Cowork 실측 — 계좌번호·잔액 원값은 적지 않는다)

| # | 실측 | 결과 |
|---|---|---|
| M1 | ust21610 당일매매 SOXL 22주 매도(기준일 20261009): 매도 금액 3074.72, `cmsn_altx` 7.7502 → 순 3066.97. 같은 매도의 실제 정산 예정액 = 예수금 상세 `d2_usd_sell_excta` 3072.51(결제일 20261013), 주문가능 − 출금가능 = 3072.50 | **`cmsn_altx`는 실제 수수료가 아니다**(약 0.25% 기본 요율 추정). 실제 수수료 2.21 |
| M2 | ust21610 NBIS 15주 매수(기준일 20260812): 매수 금액 3225.00, `cmsn_altx` 8.0625. 같은 매수의 거래내역(ust21100, deal_dt 20260814) `fc_cmsn` 2.25, `fc_exct_amt` 3227.25 | 같은 결론(추정 8.06 vs 실제 2.25) |
| M3 | ust21610 `qry_tp=1`(당일매도전체), 기준일 20260812 | **매수만 있는 종목(NBIS)도 돌려준다** → 위험 4 해소 |
| M4 | ust21610, 거래 없는 날(기준일 20261005) | return_code 20, `[2000](571758:조회내역이 없습니다.)` |
| M5 | ust21150 일별 주문체결, 주문 없는 날(ord_dt 20260913, 20261002) | return_code 20, `[2000](571758:해당 계좌의 체결내역이 없습니다.)` (미체결 조회 문구 "해당 계좌의미체결내역이 없습니다."와 다름) |
| M6 | ust21150, ord_dt 20261005 | return_code 0, MVLL 매도 지정가 118주 행 1개, `cntr_qty` 0, `ord_stat_nm` "무효주문", `cntr_time` 빈 문자열 → 체결 0으로 처리돼야 함 |
| M7 | ust21100 배당 행(deal_dt 20260930, SOXL): `fc_deal_amt` 6.97, `frgn_pay_txam` 1.05, `fc_exct_amt` 5.92(= 입금 뒤 증가분) | **`fc_exct_amt`는 세후 순액** → 위험 6 해소(지금 flow_cash가 fc_exct_amt를 쓰는 것이 맞음) |
| M8 | 원장 마지막 줄(rev 24, proposal_id c8eb0cff…)에 연결된 스냅샷 `workspace/outputs/reconciliation/20261009T235205Z/kiwoom_broker_snapshot.shadow.json`: `order_available_cash` 12467.71, `withdrawable_cash` 9395.21, generated_at 2026-10-09T23:52:05Z. 상태 파일 현금은 옛 정의 9395.21 | 지금 코드로는 첫 실행 I3가 3072.50 차이로 HOLD(위험 3), compare만 돌면 영원히 안 풀림 |

## 1. 고칠 것 (이 3개만)

R2-1 I3 수수료·금액은 실제 정산 금액으로
 - fill_cash가 `cmsn_altx`로 $1 검사를 하면 체결 있는 날마다 HOLD된다(M1·M2). 금액은 실제 정산 금액을 쓴다:
   아직 결제 전인 체결 → 예수금 상세(ust21160, 이미 필수 조회)의 결제일별 `dN_usd_sell_excta`·`dN_usd_buy_excta`,
   결제된 체결 → 거래내역(ust21100) 매매 행의 `fc_exct_amt`(매도 +, 매수 −; `fc_cmsn` 포함 순액).
 - ust21610은 체결과 종목·수량을 묶는 용도(지금의 FILL_SOURCES_DISAGREE 검사)와 총액(`tdy_buy_amt`·`tdy_sell_amt` = 수량 × 단가)
   상한 검사에만 쓴다: |정산 금액 − 총액| ≤ 총액 × 0.5% + 0.50(수수료 범위)이 아니면 HOLD.
 - 이중 계산 금지: 기록 전 체결의 결제 행이 기록 뒤 거래내역에 나타나도 현금 변화로 세지 않는다(지금 flow_cash의 TRADE 건너뛰기 유지).
   테스트 픽스처: M1 그대로(기록 시각 이후 체결 0, 결제 행만 나타남 → 현금 변화 0) / 기록 후 매도 체결(정산 전, d2 excta로 설명) /
   기록 후 매수 체결이 결제까지 끝난 경우(ust21100 fc_exct_amt로 설명) / 추정 수수료 행 차이 5.5가 있어도 PASS.
 - 정산 금액을 결제일별로만 알 수 있어 종목별로 나눌 수 없으면, 결제일별 합계로 맞춘다(같은 결제일의 체결 묶음 = 그 날 excta).

R2-2 I3 기준 현금 = 마지막 기록과 같은 스냅샷의 주문 가능액(브로커 대 브로커)
 - 기준 현금 = 원장 마지막 줄의 proposal_id(또는 auto-core 원장 줄의 결과 경로)로 찾은 스냅샷의 `order_available_cash`,
   기준 시각 = 그 스냅샷 generated_at. 상태 파일 현금이 옛 정의(min)여도 첫날부터 설명된다(M8: 12467.71 → 오늘 12467.71).
 - 스냅샷을 못 찾거나 order_available_cash가 없으면 HOLD `BASELINE_ORDER_AVAILABLE_UNKNOWN`(상태 현금으로 대체하지 않는다).
 - apply 때 상태 현금은 새 정의(주문 가능액)로 기록되므로 다음 날부터는 둘이 같다. 원장 줄에 기준 스냅샷 경로·해시를 남긴다.

R2-3 "자료 없음" 정확 문구 추가(측정값, NO_DATA_PASS_MESSAGES·코드 표)
 - account_daily_fills_read: `[2000](571758:해당 계좌의 체결내역이 없습니다.)` (M5)
 - account_day_trades_read: `[2000](571758:조회내역이 없습니다.)` (M4)
 - M6 형태 행(cntr_qty 0, 무효주문, cntr_time 빈 값)은 체결 0. 고정 테스트(test_s1b_plan_b…test_production_tables_are_locked)는 정확한 새 집합으로 다시 잠근다.

## 2. 완료 기준
- 대상 테스트(새 픽스처 포함) 통과, 전체 스위트 실패 집합 = 기준선 29개(새 실패 0), 테스트 수 감소 0, 허용 경로 밖 변경 0, 스키마 감사 PASS.
- Builder 보고에 "r2" 절을 덧붙인다(바꾼 함수·픽스처·위 M1~M8 대응). 키움 실제 호출 금지 — 위 실측값을 픽스처로 쓴다.
