---
id: close-confirm-e-builder-prompt
title: 확정 종가 반영 e — 주문표마다 '판정 유지 구간'을 계산해 저녁 입력 관문(priceCalc lo~hi)에 겹치기
date: 2026-10-20
class: 권한·한도 변경(K3 — 주문표 의미와 매수 입력 관문. auto_core*.py·tests/test_auto_core*.py·auto-core-*.schema.json = tools/dev_pipeline/authority-paths.txt 12·25·65행). 수동 경로: 이 Builder(worktree) → 별도 Opus Judge 세션(docs/claude/close-confirm-e-judge-prompt.md, Builder 완료 뒤 Cowork 작성) → 사용자 승인 1줄 + 병합 스크립트 1번(Judge PASS 뒤 Cowork 작성)
decision: 사용자 "1. 결정 close-confirm: a 묶음, e 켜 전"(2026-10-20 19:43 KST) — docs/claude/close-confirm-monday-gap-2026-10-20.md 2절 e(24~28행)
base: HEAD 3e753f3b6cee0e0ed1a1720809ef7c759c779f39(enter-window3 병합 2026-10-20 12:59Z) — sha256 앞 12자리(메인 작업 트리 바이트 CRLF / LF 정규화): auto_core_tickets.py f796af14d92b / c1e9d1f736d7 · auto_core_decide.py b1ea5d7be88e / ca09842e492a · auto_core_replay.py d346ba92f783 / 088a0f30ba20(바꾸지 않음) · schemas/auto-core-ticket.schema.json 24d5cd99917c / a9fbc1d8f8d8 · references/auto-core-decision.md 830dc911c738 / 9dd2af46d6d6 · tests/test_auto_core_risk1r.py 98a40b55dc7e / 444ba156db25 · tests/test_auto_core_enter_window.py 9cc3d3c026ea / b1a217e32469 · docs/claude/t2rc-oracle.py d79b12212ee2 / 6a74f813c918(= 사전 등록 고정값, 바꾸지 않음)
model: Opus · xhigh · worktree work-close-confirm-e(base 3e753f3, 사용자가 이미 연 세션)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 바뀌는 것: 주문표 priceCalc에 band·hold 추가, 매수 priceCalc lo~hi를 판정 유지 구간으로 좁힘(조이기만), 구간을 확인하지 못한 매수는 주문표 없음(HOLD_RANGE_UNVERIFIED, fail-closed) · 매도는 막지 않음(lo~hi 그대로, 구간은 경고용으로만 실음) · 가격 산식·수량·관문 G0~G5·근거·후보·결과 분류·장부·일지·정책·상태·예약 작업 불변 · 키움 호출 없음
weekly_user_touch: 0 (일회성: Builder 시작 1·Judge 시작 1·승인 1줄·병합 1번)
deadline: T2 "켜" 전(병합 + 통합점검 화면 반영까지). 구간 계산은 후보 집합·주문표 수량·가격을 바꾸지 않아 t2-rc 계산기 대조(C1·C2, 사전 등록 22~25행)에 영향이 없다. 단 HOLD_RANGE_UNVERIFIED로 매수가 빠지면 계산기는 그날을 누수(ticket_leaks → MISMATCH)로 본다 — HOLD_RANGE_UNVERIFIED는 자기 점검 불일치·계산 예외 때만 생기는 코어 결함 신호라 사전 등록 24행대로 CORE_BUG(수정 뒤 C1을 0부터)이고, 그 방향 C3 확인도 세지 않는다(48행). Judge는 더 엄격하게만 정할 수 있다(16행) — 누수 날을 MISMATCH에서 빼는 처분은 사용자 결정이다
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 현재 유지(이미 열린 worktree work-close-confirm-e — Opus·xhigh가 아니면 닫고 같은 worktree에서 Opus로 새로) · 이유: 주문표 의미·매수 입력 관문 변경(K3) + decide 경로에 새 계산

# 목표

주문표마다 **"그 종목의 평가 세션 종가가 b였어도 같은 판정이 나오는" 센트 구간 [hold.lo, hold.hi]** 를 근사 종가 ±1% 범위(band) 안에서 계산해 주문표에 싣는다.
- 매수: 대시보드 입력 관문 `priceCalc.lo~hi`를 그 구간으로 좁힌다. 지금 화면은 lo~hi 밖이면 가격을 보여 주지 않으므로, 병합만으로 매수는 fail-closed가 된다.
- 매도: `priceCalc.lo~hi`는 그대로 두고 구간만 싣는다(매수만 막는 원칙). 경고 문구는 병합 뒤 Cowork가 화면에 넣는다.

방법은 **같은 코드를 다시 부르는 것**이다. 평가 세션 봉 하나의 종가만 b로 바꾼 사본으로 그 종목의 F1(지표·트리거·근거)·R-REC1·매수 요건 행·시나리오·주문표 계산을 다시 하고 판정을 비교한다. 그래서 결정 기록의 한계("EMA·σ60 재계산으로 판정이 바뀌는 경우는 잡지 못한다", 27행)는 이 설계에서 없어진다. 남는 한계(보고서에 코드 위치로 적는다):
1. S7 검토(노출 E·멈춤·목표 비중 제안 평가·자산·비중·고점 검토)는 근사 종가로 한 번 계산한 값 그대로다.
2. 다른 종목의 주문표·교체 후보(redeploy)는 그대로다.
3. 화면 환산 배수 mult는 근사 종가의 σ60 그대로다(order-instruction-design 9-1 2-2의 "남는 위험" 그대로).

## 판정 유지 정의 (센트 b에서 — 이 절이 기준이다)
- **매수**: b에서 다시 계산한 결과에 그 종목 매수 주문표가 나오고, 그 단계 r_b ≥ 주문표의 r이며, 주문표 수량이 b의 화면 환산가에서 G4를 통과한다: `floor(cash / (p_b × (1 + CASH_BUFFER))) ≥ qty`, `p_b = (b × mult)`를 센트 내림(loc_price 매수와 같은 방향), mult = 주문표 `priceCalc.mult`, 식은 _buy_ticket 1016행과 같다. 설정에 `max_buy_ticket_pct_of_equity`가 있으면 `floor(equity × pct / p_b) ≥ qty`도 유지 조건이다(1003~1011행과 같은 식, 멈춘 이유 `G2B`). 지금은 키가 없어 꺼져 있다.
- **매도**: b에서 그 종목 매도 주문표가 나오고 r_b ≥ 주문표의 r.
- 수량 차이(기준가 반올림으로 1주 차이 등)와 decision_key 차이(근거 id가 늘거나 바뀜)는 판정 변경으로 보지 않는다. 반올림 때문에 구간이 자주 잘리는 거짓 막힘을 피하기 위해서다. 시스템이 그 종가에서 덜 사려는 경우(단계 하락)·현금 부족·금액 상한(G2b, 키가 있을 때)·주문표가 아예 안 나오는 경우만 막는다.

## 구간 계산
- band = loc_price가 낸 lo·hi 그대로(근사 종가 ±1%, 센트).
- ref = 주문표 `ref.price`(평가 세션 근사 종가 = 30분봉 이력의 raw close). 센트 단위가 아닌 날이 흔하다(2026-10-20 decision.json indicators.close: MU 905.415·DELL 455.1047·BE 226.105·LITE 834.545·SOXL 98.675). 그래서 위쪽 스캔은 ⌈ref⌉센트(ref가 센트면 ref+0.01)부터, 아래쪽은 ⌊ref⌋센트(ref가 센트면 ref−0.01)부터 시작한다.
- **자기 점검**: b = ref로 다시 계산한 주문표가 실제 주문표와 같아야 한다(`after_sale`·`ticket_id`·`gap.plan_premise`만 빼고 전체). 다르면 `unverified`(`SELF_CHECK_MISMATCH`).
- 위는 그 시작 센트부터 band.hi까지, 아래는 그 시작 센트부터 band.lo까지 한 센트씩 보고, 처음 유지가 깨지는 센트에서 멈춘다. hold.hi = 마지막 유지 센트(바로 깨지면 ref — ref가 센트 사이 값이면 그쪽 센트 입력은 화면이 모두 막는다, fail-closed). hold.lo도 같다. 센트 사이 값의 입력은 양쪽 센트가 유지면 유지로 본다(남는 한계 — 키움 기준종가의 소수 자릿수는 확인 필요).
- 멈춘 이유 `hi_limit`·`lo_limit`: `BAND`(끝까지 유지) | `NO_TICKET:<그 b의 scratch blocked에서 그 종목·방향의 첫 사유(CARD_TRIM_SIZE_MISSING은 빼고), 회로가 안 열리면 CIRCUIT_CLOSED>` | `STEP_DOWN` | `CASH`·`G2B`(매수만) | `DATA`(b의 봉·지표를 만들 수 없음).
- 스캔 중 예외는 그 센트를 `DATA`로 보고 멈춘다. ref에서 예외면 `unverified`(`EVAL_ERROR:<예외 이름>`). 예외가 decide를 멈추게 하지 않는다.

## 출력
- `priceCalc.band = {"lo", "hi"}`(= 기존 lo·hi).
- `priceCalc.hold = {"status": "ok"|"unverified", "lo", "hi", "lo_limit", "hi_limit", "checked", "reason", "basis": "SYMBOL_CLOSE_ONLY:S7_FIXED"}`. checked = 계산한 센트 수(자기 점검 포함). unverified면 lo·hi·limit은 null. 시간·실행 환경 값은 싣지 않는다(E6).
- 매수 + ok → `priceCalc.lo/hi = hold.lo/hi`.
- 매수 + unverified → 주문표를 내지 않고 blocked에 `HOLD_RANGE_UNVERIFIED`(candidates는 그대로). 화면 calcBox는 lo·hi가 숫자가 아니면 환산 칸을 그리지 않고 가격 칸은 그대로 보이므로, lo·hi를 null로 두는 방식은 fail-closed가 아니다(근거 2).
- 매도 → `priceCalc.lo/hi = band` 그대로(ok·unverified 모두), 주문표 유지.
- hold 계산을 끈 호출(`hold_range=False`, 리플레이·기존 호출)은 priceCalc를 지금과 글자까지 같게 둔다(band·hold 키 없음).

## 동치 명세 (Judge가 base 코드와 직접 대조한다)
- **E1 hold 끔**: `evaluate_session(hold_range` 기본 False`)`와 plan의 출력은 base와 글자까지 같다(plan 루프 본문을 helper로 뺀 것 포함). 그래서 auto_core_replay 결과도 그대로다.
- **E2 hold 켬(decide)**: tickets·blocked·candidates·no_action·keys·일지 payload(core_decision의 decision_sha256은 제외 — 주문표·orders를 해시하므로 바뀐다, portfolio_review_journal.py 576~581·auto_core_decide.py 756~772)·alerts·compare·dashboard runCore는 base와 같다. 다른 것은 각 주문표 priceCalc의 band·hold 추가와 매수 lo/hi 좁힘뿐이다(dashboard orders의 priceCalc는 주문표를 그대로 옮김). 예외: 매수 unverified → 그 주문표가 빠지고 blocked 1건(`HOLD_RANGE_UNVERIFIED`)이 생기며, no_action과 남은 주문표 번호는 plan 규칙 그대로 다시 정해진다. 그때 하류 값(일지 payload의 ticket_ids·no_action·blocked_reasons·order_ticket, alerts, compare, dashboard)은 그 주문표가 없는 출력을 decide 규칙 그대로 따른다(keys는 evaluate_session 전에 정해져 영향 없음).
- **E3 결과 분류 불변**: `classify_outcome(새 주문표, rows) = classify_outcome(base 주문표, rows)`. "주문표대로" 범위는 band(±1%) 그대로 쓴다(band가 없는 옛 주문표는 lo·hi).
- **E4 구간 정확성**: band 안 모든 센트 b에서, 스캔이 쓰는 판정은 전체 경로의 판정과 같다. 전체 경로 = evaluate_session에 그 종목 평가 세션 봉만 b로 바꾼 bars를 넣고, s7_runner는 ref에서 만든 검토의 제안 평가를 (symbol, target_weight)로 찾아 돌려준다(ref에 없던 제안은 통과 아님, 사유 `NOT_EVALUATED_AT_REF`). 제안 목록은 그 종목의 new_basis_met(보충 ETF는 basis_met)에 달려 있고 결과는 인덱스로 이어지므로(957~965·973~978행) 인덱스로 고정하지 않는다. hold는 그 판정이 ref부터 끊기지 않고 참인 최대 구간이다.
- **E5 조이기만**: 매수 [hold.lo, hold.hi] ⊆ band, 매도 lo/hi = band. PRICE_RANGE 등 상수는 바뀌지 않는다. 구간 계산이 주문표를 새로 만들거나 수량·가격을 바꾸지 않는다.
- **E6 결정론**: 같은 입력이면 같은 hold가 나온다(decision_identity_hash 756행이 주문표를 해시한다 — 같은 날 재실행 판정 R2-5가 그대로 동작해야 함).
- **E7 입력 불변**: 스캔 뒤 bars·ctx·S7 검토 객체가 바뀌지 않는다. raw와 adjusted가 같은 객체인 경우가 있다: 시험 helpers.bars(tests/fixtures/auto_core_t2/helpers.py 60~61행)와 status가 OK가 아닌 봉(auto_core_bars.py 180행). OK인 실제 봉은 adjust_bars가 세션별 사본을 만든다(134·188행).

# 근거 (Cowork 2026-10-20 22:3x~23:0x KST 읽기 전용 확인 — Builder는 원문을 다시 연다)

1. **결정**: close-confirm-monday-gap-2026-10-20.md 24~28행(내용·근거·한계·순서). review-stability-2026-10-13.md 47행(22번: 결정 시점은 사용자 저녁 키움 입력이므로 기존 입력 관문에 판정 유지 구간을 겹치는 안이 우선). 순서 조건 "enter-window 병합 뒤": docs/claude/dev-runs/enter-window3.md 병합 기록(3e753f3, -ApproveAuthority 12:59:22Z).
2. **지금의 입력 관문**: auto_core_tickets.py 50행 `PRICE_RANGE`, `loc_price` 376~392행(lo·hi = ref × (1 ∓ 1%) 센트, mult 소수 넷째 자리), `_common_ticket` 885행 priceCalc. decide `_dashboard` 1113~1126행(apply 모드에서만 orders, priceCalc 그대로). scheduled-prompts/auto-core-alert.txt 112·138~139행(orders를 파일 그대로 저장소에 옮김). 통합점검 HTML calcBox(live version 1792495206-e6f6): lo·hi가 숫자가 아니면 칸을 그리지 않는다. b < lo 또는 b > hi면 "범위 밖 — 입력하지 말고 Cowork에 가격 재계산"을 보인다. 안이면 b × mult를 down 내림·up 올림한다. 매수·매도 모두 막는다. 같은 카드의 가격 칸(cell "가격")은 priceCalc와 상관없이 주문표 price를 보인다 — 그래서 lo·hi를 비우면 환산 칸만 사라지고 가격은 보인다. dashboard-order-panel-2026-10-07.md 35행("선택. 없으면 price만 표시" — live 동작과 같음)·84행("값이 없으면 가격을 보여 주지 않고"는 입력값이 빈 경우로도 읽혀 모호 — 병합 뒤 35행·live에 맞게 명확히), order-instruction-design-2026-10-06.md 307행(9-1 2-2).
3. **판정 경로**: auto_core_decide.py `evaluate_session` 896~1055행 — series 924~927, closes_raw 929~930, nominal 931, 종목별 F1·근거 934~949(evaluate_symbol 939~943, official_evidence 945, evidence_summary 947~949), S7 966~979, rrec1 986~996, 요건 행 1008~1016, data_reasons 1017~1019, equity·weights(S7 검토에서) 1020~1021, model_for 1024, scenario 1025, ctx 1029~1045, plan 1046. decide `_run` 호출 655~664행. auto_core_tickets.py `plan` 718~791행(매도 루프 741~754, 매수 루프 757~771, _limit_daily 773, 번호 780~781, no_action 782~791), `_sell_ticket` 895~944, `_buy_ticket` 947~1035(G4 1012~1023), `after_sale_path` 1100~1139(model_for None이면 projection unavailable 1110~1112).
4. **봉**: auto_core_bars.py `load_symbol` 171~196행(처음 adjusted = raw 같은 객체 180행 → status OK면 188행에서 adjust_bars의 사본으로 바뀜), `adjust_bars` 129~150(134행에서 늘 세션별 사본, 분할 조정은 효력 세션 전 값에만). auto_core_rules.py `build_series` 217~252행(close·high·low·volume로 지표 계산), `evaluate_symbol` 528~541행(bars["adjusted"]로 series).
5. **결과 분류**: `classify_outcome` 629~674행(lo·hi 645~646, 주문가 범위 661~663). "changed"는 재발행 장부에서 시장 시험 1회(478~484행)이고 채점 불가(score_decision_journal.py 441~442행)라서, 분류 범위를 바꾸면 장부·채점 의미가 바뀐다 → 이 작업에서는 band 그대로(E3).
6. **리플레이**: auto_core_replay.py 250~257행이 evaluate_session을 부르고, 주문표는 symbol·side·qty·price·r만 남긴다(266~267행).
7. **계산기·일지·사전 등록**: t2rc-oracle.py `ticket_check` 2005~2022행(가격·수량을 다시 계산, priceCalc를 읽지 않음 — `grep -i pricecalc` 0건). portfolio_review_journal.py `auto_core_payloads` 573~605행(priceCalc 없음). t2-rc-preregistration-2026-10-14.md 22~25행(C1 = 회로 열림 집합 vs candidates, C2 = 수량·LOC 가격·요건·관문·현금) — 구간 계산은 후보·수량·가격을 바꾸지 않는다. 다만 계산기는 자기가 낸 주문표를 코어가 안 내면 누수로 센다(1596~1604행 ticket_leaks, 1617행 판정) → 매수 HOLD_RANGE_UNVERIFIED가 나온 날은 MISMATCH가 된다(이상 신호로서 맞는 동작. 사전 등록 24행 CORE_BUG → C1 0부터, 48행 그 방향 C3 불산입. Judge는 더 엄격하게만 바꿀 수 있다 — 16행).
8. **스키마**: auto-core-ticket.schema.json 28~39행(priceCalc additionalProperties false, lo·hi number 필수). auto-core-decision.schema.json 74행 tickets는 ticket 스키마를 참조하고, 92행 open_tickets·145행 orders는 object라 고칠 필요가 없다.
9. **테스트 골든**: test_auto_core_risk1r.py GOLDEN 36~56행·UnchangedTicketTests 198~215행(decide_compare·decide_apply 해시는 decide 수준 주문표). test_auto_core_enter_window.py BASE_GOLDEN 36~45행·GoldenCauseTests 194~224행(215행이 옛 enterWindow 뷰 해시를 BASE_GOLDEN과 비교). test_auto_core_tickets.py 65행(loc_price 매도 lo·hi 단언 — loc_price는 바꾸지 않으므로 그대로). 시나리오: test_auto_core_tickets.py `Scenario` 334~402행, risk1r `_scenarios` 73~81행·`_decide` 84~92행.
10. **설정**: workspace/policies/auto_core.json — decision_mode compare, reissue_buy_cap_not_above_first false, max_tickets_per_day·max_buy_ticket_pct_of_equity 키 없음(config.get → None). 그래서 _limit_daily(장수 상한)·G2b(금액 상한)·첫 상한 분기는 지금 꺼져 있다. _limit_daily는 helper 밖(plan 773행)에 있으므로 hold는 그 뒤에 붙인다(A-3). G2b는 판정 유지 정의에 따로 넣었다.
11. **실제 기록**: workspace/outputs/auto-core/2026-10-13~2026-10-20 decision.json(평가 세션 10-12~10-19) 주문표 0건(10-16 DELL·MU 매수는 REQ5_RREC1에서 막힘). 기존 리플레이(workspace/outputs/auto-core/replay/prereg1009/summary.md 8·12행 — 기간 07-10~10-09, 옛 코드)도 P-R1·P-R2 모두 주문표 0건이다(리플레이 기본 기간 auto_core_replay.py 54행, 공식 사실 없음 253행). 그래서 실데이터 확인에 주문표 없이도 재는 강제 측정(R2b)을 함께 둔다.
12. **시간 측정**(Cowork, 장치 VM Linux): `Scenario().run()` evaluate_session 0.114초(합성 95세션 5종목). `rules.evaluate_symbol` 1.36ms(95세션)·6.15ms(400세션). 그 종목만 다시 계산하면 센트당 수~십수 ms다. evaluate_session 전체를 센트마다 돌리면(실제 9종목 안팎·S7 모델·매도 뒤 예상 루프) 주문표당 수 분이 걸린다 → 그 종목만 다시 계산한다. 10-20 decision 근사 종가로 본 band 센트 수: MU 905.415 약 1,811 · LITE 834.545 약 1,669 · PWR 618.30 약 1,237 · DELL 455.1047 약 910 — 센트당 12ms(추정, R2b가 잰다)면 MU 주문표 1장 약 22초. decide 실행 한도: Windows 작업 InvestmentV2-AutoCoreDecide 07:45 시작·60분 제한(manage-us-stock-strategy/scripts/register_auto_core_task.ps1 11·27행), 연구 기록 대기 08:30까지(auto_core_decide.py 64행), 08:40 T2rcCheck — 한도를 넘겨 중단되면 매도 주문표까지 사라지므로 시간 예산(R3)을 둔다.
13. **줄 끝**: 대상 파일은 모두 CRLF다(base 줄의 sha 두 값). 체크아웃된 그대로 두고 일괄 변환하지 않는다.

# 바꿀 것

## A. auto_core_tickets.py
1. `plan()`의 매도 루프 본문(742~754행)과 매수 루프 본문(758~771행)을 helper 둘로 뺀다. 예: `_plan_sell(ctx, symbol, reduce_items, global_reasons, blocked, candidates)`, `_plan_buy(ctx, row, add_symbols, global_reasons, blocked, candidates)`. 둘 다 주문표 또는 None을 돌려준다. 동작은 바뀌지 않는다(E1).
2. 새 순수 함수 `hold_range(ctx, ticket) -> dict`. `ctx["hold_eval"](symbol, b)`가 주는 b용 ctx(B-1)로 1의 helper를 scratch blocked·candidates와 함께 다시 부르고(매수 row는 b용 ctx의 buy_rows에서 그 종목 행을 다시 꺼낸다 — ref 행을 넘기면 요건 ①~⑤가 ref 값으로 고정된다), "구간 계산"대로 hold를 만든다. 쓰는 값은 기존 `S["CASH_BUFFER"]`·`CENT`·loc_price의 band뿐이고 새 판정 상수는 없다(사유 코드 문자열만).
3. `plan()`: `ctx.get("hold_eval")`이 있을 때만, `_limit_daily`(773행) **뒤**·plan_premise(774~779행)·번호(780~781행) **앞**에서 남은 주문표마다 hold_range를 부르고 "출력" 규칙을 적용한다. 빠진 매수는 blocked에 더하고 tickets에서 뺀다 — 장수 상한이 켜져도 떨어진 주문표가 그 자리를 채우지 않는다(E2·E5). 없으면 지금 그대로다.
4. `classify_outcome` 645행: `band = ticket["priceCalc"].get("band") or ticket["priceCalc"]`에서 lo·hi를 읽는다. 그 밖은 그대로. 본문·주석에 `close`·`quote`·`now_pric`·`cur_prc`를 쓰지 않는다(test_auto_core_tickets.py 203~208행 가드).
5. loc_price(376~392)·후회표·수량·G0~G5·_limit_daily·plan_premise·after_sale_path·ALLOWED_NO_TICKET는 바꾸지 않는다.

## B. auto_core_decide.py
1. `evaluate_session`에 키워드 `hold_range: bool = False`를 더한다. True면 ctx를 만든 뒤(1029~1045행) `ctx["hold_eval"]`에 closure를 넣는다. closure(symbol, b)는 **호출 시점의** ctx를 얕게 복사해, 그 종목만 b로 다시 계산한 값으로 바꾼 ctx를 돌려준다(봉을 만들 수 없으면 None → DATA).
   - 봉: bars[symbol]의 사본. 평가 세션 봉의 raw·adjusted 모두 close = b, high = max(high, b), low = min(low, b)(None이면 None 그대로), 나머지 세션·필드는 그대로. 원본은 고치지 않는다(E7). 평가 세션의 raw close ≠ adjusted close면 None(분할 조정이 평가 세션에 걸린 경우).
   - **같은 함수를 같은 인자로** 부른다: rules.build_series(925~927) · rules.evaluate_symbol(939~943) · official_evidence + evidence_summary(945~949) · rule_file_nominal(931, closes_raw에서 그 종목만 b) · rules.rrec1(987~992, candidate = b의 series, rg2_series가 그 종목이면 그것도 b의 series) · buy_requirements(1010~1016, close = b, nominal·shock·evidence는 b의 것) · data_reasons(1017~1019) · scenarios(1025) · indicators(1043~1044).
   - 바꾸는 ctx 키: closes·sigmas·symbols·evidence·buy_rows(그 종목 행만)·data_reasons·scenarios·indicators에서 그 종목 값, `model_for = None`(매도 뒤 예상은 표시 전용), `hold_eval = None`(재귀 없음). review·s7·equity·weights·proposal_results·keys·cash·gate0·gate1·redeploy_candidate·redeploy_ranked·policy_instruments·config·calendar는 그대로 둔다.
   - 계산 로직은 복사하지 않는다(함수 호출 배선만). 위 호출을 evaluate_session 본문과 함께 쓰려고 작은 내부 helper로 빼는 것은 허용한다(E1 유지).
2. `_run` 655~664행 호출에 `hold_range=True`를 넣는다. decide의 다른 흐름은 바꾸지 않는다.
3. auto_core_replay.py는 바꾸지 않는다(기본 False → E1).

## C. schemas/auto-core-ticket.schema.json
priceCalc에 선택 속성 두 개를 더한다: `band`(lo·hi number ≥ 0, additionalProperties false), `hold`(status enum ok|unverified, lo·hi number|null, lo_limit·hi_limit string|null, checked integer ≥ 0, reason string|null, basis string, additionalProperties false). required는 그대로라 옛 주문표도 유효하다. description 한 줄.

## D. references/auto-core-decision.md
157~160행 Price 항목 뒤에 영문 2~3문장: hold range의 정의(the ticket symbol's own evaluation-session close replaced by each cent of the +/-1% band, everything else and S7 fixed), 매수 lo/hi narrowing, 매도 unchanged with the range for a warning, unverified buy = no ticket, outcome classification keeps the band, user decision close-confirm e (2026-10-20).

# 바꾸지 않는 것

auto_core_replay.py, auto_core_rules.py, auto_core_bars.py, auto_core_compare.py, auto_core_inputs.py, auto_core.py, portfolio_exposure.py, portfolio_review_journal.py, score_decision_journal.py, docs/claude/t2rc-oracle.py·t2rc-check-run.ps1, SIZING·CONSTANTS 값, loc_price, ALLOWED_NO_TICKET(HOLD_RANGE_UNVERIFIED는 허용 사유가 아니라 이상 신호다), 정책·상태·장부·일지·workspace/policies·stock-strategy-system, 예약 지시문(auto-core-alert는 orders를 그대로 옮기므로 바꿀 필요 없음), 통합점검·관제판 HTML, dashboard-order-panel·설계 문서, CLAUDE.md, gate-rule-epochs.json, 사전 등록 문서. 기존 ±1% 밖 매도 화면 막힘(설계 9-1 2-2)도 이 작업에서 바꾸지 않는다.

# 테스트

새 파일 `manage-us-stock-strategy/tests/test_auto_core_hold_range.py`(authority-paths 25행 패턴). test_auto_core_tickets.Scenario·risk1r._scenarios·_decide 방식을 재사용한다. 계산 시간을 줄이려고 새 시나리오는 낮은 가격대(예 $20~$40, band 40~80센트) 합성 봉을 써도 된다.

- **H1 자기 점검·기본**: Scenario()의 MU 매수와 risk1r "sell"의 SOXL 매도를 hold_range=True로 돌린다 → hold.status ok, band = hold 끈 결과의 lo·hi, band.lo ≤ hold.lo ≤ ref ≤ hold.hi ≤ band.hi, 매수 lo/hi = hold, 매도 lo/hi = band. 주문표의 나머지 필드는 hold 끈 결과와 같다(E2). ref가 센트 사이 값인 시나리오(예 x.xx5)에서도 status ok이고, 스캔이 ⌈ref⌉·⌊ref⌋센트부터 시작하며, 바로 깨지는 쪽의 hold 끝은 ref다.
- **H2 E4 전수 대조**: H1의 두 시나리오와 H3·H4 시나리오에서 band 안 모든 센트 b마다 전체 경로 판정(evaluate_session, 그 종목 평가 세션 봉만 b, s7_runner = ref 검토의 제안 평가를 (symbol, target_weight)로 찾아 주는 가짜)이 스캔 판정과 같고, hold가 그 최대 연속 구간이다. 어떤 b에서 제안 목록이 ref와 다르면, 그 차이가 그 종목 하나뿐이고 그때 두 경로 모두 그 종목 주문표가 없음을 단언한다.
- **H3 구간 안 경계(매수)**: band 안에서 판정이 바뀌는 매수 시나리오를 만든다. 예: 평가 세션의 그 종목 1일 수익률이 −2σ60보다 조금 위라 b가 조금 낮으면 그 종목 자신의 −2σ60 날(R-REC1 사건)이 된다(정의는 rules.rrec1 원문에서 확인). 또는 가격 트리거가 끝나는 경계. → hold.lo 또는 hold.hi가 band 안에서 멈추고, limit은 NO_TICKET:… 또는 STEP_DOWN이다. 화면 범위(lo~hi) 밖 b는 매수가 막힌다.
- **H4 현금**: 현금이 qty × ⌊ref × mult⌋ × 1.0025를 겨우 넘는 매수 → hold.hi가 band 안에서 CASH로 멈춘다(경계 센트를 손으로 계산해 단언).
- **H5 매도는 경고만**: hold가 band보다 좁은 매도 시나리오에서도 priceCalc.lo/hi = band이고 주문표는 그대로다.
- **H6 unverified**: hold_eval을 틀린 값을 내는 가짜로 바꾼다 → 매수: 주문표 없음, blocked HOLD_RANGE_UNVERIFIED, candidates 그대로, no_action은 plan 규칙대로. 매도: 주문표 유지, hold.status unverified, lo/hi = band. 스캔 중 예외 → DATA, ref에서 예외 → unverified이고 decide는 계속 간다.
- **H7 E1**: hold_range 기본(False)에서 risk1r GOLDEN 6키(default·g2b·cash5·research_block·sell·pwr)가 그대로다. plan helper 분리 전후 출력이 같다.
- **H8 E3**: band가 있는 새 주문표와, band 값을 lo/hi로 둔 옛 주문표에 대해 classify_outcome 결과가 같다(범위 안·밖 주문가, 부분 체결, 취소, LOC 아님).
- **H9 E6·E7**: 두 번 실행한 결과가 같다. 스캔 뒤 bars(raw·adjusted 깊은 비교)·ctx·review가 바뀌지 않는다.
- **H10 스키마**: hold가 있는 매수·매도 주문표, unverified 매도 주문표, 옛 주문표(band·hold 없음)가 auto-core-ticket.schema.json에 맞는다. decision 전체 검증도 통과한다.
- **H11 원인 확인(HoldCauseTests)**: decide 수준(risk1r._decide compare·apply)을 같은 프로세스에서 두 번 돌린다 — hold_range를 False로 강제한 실행과 그대로 켠 실행. 끄는 방법: `ORIG = decide_module.evaluate_session`을 patch 전에 잡고 `mock.patch.object(decide_module, "evaluate_session", lambda **kw: ORIG(**{**kw, "hold_range": False}))`(_run이 넘기는 hold_range=True를 덮는다 — partial·wraps로는 호출 키워드가 이겨서 끄지 못한다). 끈 실행의 주문표에 band·hold가 없음을 먼저 단언한다. 켠 실행의 각 주문표 priceCalc를 되돌린 뷰(band·hold 삭제, band가 있으면 lo/hi = band) = 끈 실행의 뷰(OS와 무관). 바뀐 것이 priceCalc뿐임을 보인다. 덧붙여 옛 GOLDEN 두 값(decide_compare `2e565c3b7f2d…`·decide_apply `d78459cbeb51…`, Windows 실측 — Linux에서는 다름)을 이 파일에 상수로 두고, 되돌린 뷰의 해시가 그 값과 같은지 Windows에서 확인해 보고서에 적는다. 되돌리기 함수는 이 파일에 두고 enter-window 테스트가 import한다.

기존 테스트 변경은 아래 셋만 허용한다(그 밖이 필요하면 멈추고 보고):
1. test_auto_core_risk1r.py GOLDEN의 decide_compare·decide_apply 두 값 + 그 위 주석 1줄("close-confirm-e: priceCalc band·hold 추가(매수 lo/hi = 판정 유지 구간) — test_auto_core_hold_range HoldCauseTests로 확인"). 다른 6키는 그대로.
2. test_auto_core_enter_window.py 215행에서 old 뷰를 해시하기 전에 H11의 되돌리기 함수를 적용하고(BASE_GOLDEN 그대로), 25~27행 옆에 그 함수 import 1줄을 더한다. 다른 줄은 그대로. 되돌리기 함수는 입력을 고치지 않고 새 뷰를 돌려준다(깊은 복사 — 223행이 원본 new·old 뷰를 비교한다).
3. decide 수준 테스트가 매수 주문표·dashboard orders의 priceCalc 값을 직접 단언해 깨지면, 그 기대값만 "옛 값 + band·hold, 매수 lo/hi = hold"로 바꾼다. 파일:행 목록과 이유를 보고서에 적는다.

실행(Claude Code는 "auto_core.py"가 든 명령을 거부한다):
- 기준선(변경 전 worktree): `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`. Cowork 참고값(장치 VM Linux, 메인 작업 트리 3e753f3, 2026-10-20 22:4x KST): Ran 460, failures 3 — test_auto_core_decide RegistryTests(PLTR: CARD_SECTION_CHANGED·CARD_NOT_ACCEPTED_IN_WATCHLIST — 등록부 파일은 git상 변경 없음, 커밋된 상태에서 나오므로 worktree에서도 실패 예상, 이 작업 범위 밖), test_auto_core_enter_window GoldenCauseTests·test_auto_core_risk1r UnchangedTicketTests(decide_* 해시가 OS마다 다름, Windows에서는 통과). Windows worktree에서 다시 잰다.
- 변경 뒤 같은 명령과 `-p "test_auto_core_hold_range.py"`. 전체 스위트는 `test-runner` 서브에이전트(Haiku)로 돌리고 실패만 보고한다 — 기준선 대비 새 실패 0(참고: enter-window3 dev-run Windows 전체 Ran 3247 · 실패 30).
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` 통과.

# 실데이터 확인 (읽기 전용 — 입력은 메인 체크아웃 E:\사업\##금동한\코덱스저장소, 출력은 저장소 밖 임시 폴더, 예 $env:TEMP\cce-check)

- **R1 센트 단위**: workspace/outputs/regular-session-closes의 종가 이력에서, 지금 universe(보유·관심·벤치마크) 종목의 최근 120세션 종가 가운데 센트 단위가 아닌 값의 수(종목별). 보고만 한다(센트 사이 ref는 스캔 시작 규칙으로 처리한다 — 10-20 decision에서도 MU·DELL·BE·LITE·SOXL ref가 센트 사이 값이었다).
- **R2 리플레이 대조**: 저장소 밖 임시 드라이버로 `auto_core_replay.main([... "--output-root", <임시>, "--run-id", "cce-off"])`를 그대로 한 번 돌린다. 이어서 `decide_module.evaluate_session`을 hold_range=True로 감싸 다시 돌린다("cce-on"). 두 replay.json의 차이는 run id·시각 값뿐이어야 한다(unverified로 빠진 매수가 없다는 뜻). 먼저 주문표 수를 보고한다(근거 11대로 0건이 예상된다). 주문표가 있으면: hold가 band보다 좁은 수(아래·위), limit 사유별 수, unverified 수(기대 0), 주문표당 확인 센트 수와 스캔 시간(`tickets_module.hold_range`를 감싸 잰다).
- **R2b 강제 측정**(R2 주문표가 0건이어도 반드시): 같은 드라이버에서 `tickets_module.plan`을 감싸 hold_range=True인 ctx를 잡는다(가능하면 최근 세션, 예 `--start 2026-10-19 --end 2026-10-19`; 안 되면 리플레이 마지막 세션). 그 ctx로(포트폴리오 P-R1의 ctx — 리플레이는 세션마다 포트폴리오별로 부르므로 하나를 고른다; P-R1 보유 MVLL·SOXL·NBIS) universe 안의 승인 매수 상품과 보유 종목마다, band 전체 센트(loc_price(ref, σ60)의 lo~hi)에 대해 `ctx["hold_eval"](symbol, b)`와 그 방향 helper 재계산을 돌린다(주문표가 없는 종목은 판정 비교 없이 계산만). 보고: 종목별 band 센트 수, 센트당 ms(최대·중앙값), DATA 수, ref가 센트 단위가 아닌 종목.
- **R3 시간 예산**: 최악값 = Σ(종목별 band 센트 수 × 센트당 ms 최대)(R2b의 매수 후보·보유 종목 모두에 주문표가 났다고 가정) ≤ 120초, 주문표 1장 ≤ 30초(사용자 PC, Windows). 넘으면 멈추고 보고한다. 센트 간격을 넓히는 등 근사로 바꾸지 않는다(그건 사용자 결정이다).

# 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 파일: auto_core_tickets.py, auto_core_decide.py, auto-core-ticket.schema.json, references/auto-core-decision.md, 새 테스트 1개, 허용된 기존 테스트 변경 1~3, 보고서. 그 밖이 필요하면 멈추고 보고한다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 든 줄을 만들거나 바꾸거나 지우지 않는다(AUTHORITY 66행 그대로). 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지.
3. 스크립트는 ASCII만 쓴다(한국어는 `\u` 이스케이프). 정책·상태·장부·일지·workspace/policies·stock-strategy-system·workspace/outputs에 쓰지 않고, docs/claude에는 보고서만 쓴다. 줄 끝은 체크아웃된 그대로.
4. E1~E7을 어기는 차이, 매수 구간이 band 밖으로 넓어지는 경우, 매도 주문표가 hold 때문에 사라지거나 lo/hi가 바뀌는 경우, 결과 분류가 바뀌는 경우는 FAIL.
5. **커밋하지 않는다.** 예약 작업·관제판·대시보드·사전 등록·규칙 파일을 고치지 않는다.

# 보고 `docs/claude/close-confirm-e-report.md` (worktree 안에 새로)

0 worktree HEAD(base 3e753f3와 다르면 그 사이 커밋이 docs/claude만인지) · 1 파일별 바뀐 곳(diff 요약, 새 함수·키) · 2 E1~E7을 어떻게 확인했는지와 결과 · 3 테스트(기준선·변경 뒤 Ran·실패, 새 테스트 이름, 허용 변경 1~3의 파일:행, GOLDEN 새 값과 H11 근거) · 4 실데이터 R1~R3 결과 · 5 남는 한계(S7 고정·다른 종목·mult — 실제 코드 위치) · 6 바뀐 파일 sha256(작업 트리 바이트)과 t2rc-oracle.py LF sha가 6a74f813…그대로인지 · 7 멈춤·범위 문제(없으면 "없음") · 8 화면이 쓸 값 요약(필드·사유 코드 표).

# 병합·화면 반영 (Judge PASS 뒤 — Builder는 하지 않는다)

1. **Cowork**(Builder 완료 확인 뒤): Judge 지시문 docs/claude/close-confirm-e-judge-prompt.md 작성 → 사용자가 별도 Opus 세션에서 Judge를 돌린다.
2. **Cowork**(Judge PASS 확인 뒤): 병합 스크립트 docs/claude/close-confirm-e-merge-<날짜>.ps1 작성(rrec-ev4-remove-merge-2026-10-19.ps1 방식 — 자동 코어·decide·T2rcCheck·DocsCommit·DevQueue가 실행 중이면 멈춤, Judge 마지막 줄 `VERDICT: PASS`, base 뒤 메인 이동은 docs/claude 커밋만, 대상 경로에 커밋 안 된 변경 없음). 사용자에게 승인 1줄 요청: `결정 close-confirm-e 병합: 승인`.
3. **사용자**: 승인 1줄 → 병합 스크립트 한 번(화~토 06:00~09:00 KST·23:20~23:45 KST 밖).
4. **Cowork**(병합 출력 확인 뒤, 같은 세션, T2 "켜" 전):
   - ① 통합점검 HTML calcBox: 디자인 규칙 문서와 live 판을 먼저 읽는다. 매수에서 b가 band 안·hold 밖이면 "판정 유지 구간 밖(<사유>) — 오늘 입력하지 않음 · 다음 아침 재판정". 매도에서 b가 band 안·hold 밖이면 가격을 보여 주고 경고 줄. 매도 hold unverified면 "판정 유지 구간 확인 필요" 경고. 규칙 줄에 band와 hold를 함께 적는다. hold가 없는 지시(옛·수동)는 지금 그대로. 표시 전용(K1).
   - ② 문서: dashboard-order-panel 3절 priceCalc 행·9절 84행(35행·live 화면에 맞게 문구 명확히), order-instruction-design 9-1 2-2 한 줄, close-confirm-monday-gap 2절 e 상태, t2-rc 사전 등록 변경 기록 1줄(코어 주문표 priceCalc만 바뀜·HOLD_RANGE_UNVERIFIED 날 = CORE_BUG(24행)·그 방향 C3 불산입(48행) 그대로, 완화는 사용자 결정), gate-rule-epochs.json `GATE:HOLD_RANGE_UNVERIFIED` 1줄(채점기는 막힘 사유의 ':' 앞을 gate 이름으로 쓴다 — score_decision_journal.py 1165~1170·1354~1361행).
   - ③ 관제판.
5. **첫 확인**: 병합 뒤 첫 decide 주문표(있으면)의 priceCalc.hold.status = ok, 매수 lo/hi ⊆ band. T2rcCheck verdict와 C1 셈에 영향이 없는지 본다.

# 작성 기록 (Cowork, 2026-10-20)

- 원문 확인: 결정 기록 1~50행 · review-stability 21~92행 · dev-runs/enter-window3.md · auto_core_tickets.py 1~460·600~1139행 · auto_core_decide.py 494~760·896~1188행 · auto_core_bars.py 1~40·91~196행 · auto_core_rules.py 1~40·217~256·528~708행 · auto_core_replay.py 1~40·195~290행 · ticket·decision 스키마 · references 150~172행 · authority-paths.txt 1~65행 · t2rc-oracle.py 2005~2060행(+priceCalc grep) · portfolio_review_journal.py 573~618행 · score_decision_journal.py 430~450행 · auto-core-alert.txt grep · t2-rc 사전 등록 20~56행 · gate-rule-epochs.json · dashboard-order-panel 1~90행 · order-receipt-process-review 14~90행 · order-instruction-design 278~312행 · 통합점검 live HTML(calcBox) · 테스트 파일(risk1r 30~236, enter_window 1~69·190~228, tickets 1~60·334~440) · 설정 auto_core.json · decision.json 10-13~10-20 · 기준선 실행·시간 측정(근거 11·12).
- 설계 선택: ① 판정 유지는 "같은 코드를 그 종목 종가만 바꿔 다시 부름"으로 정의했다(근사식 없음, Judge가 base 코드로 전수 대조 가능 — E4). ② 수량·decision_key 차이는 판정 변경에서 뺐다(반올림 거짓 막힘 방지). 단계 하락·현금·주문표 없음만 막는다. ③ 결과 분류는 band 그대로(장부·채점 의미 보존). ④ 매도 lo/hi는 그대로(지금 화면이 lo~hi 밖을 막으므로, 매도 lo/hi를 좁히면 매도가 막힌다). ⑤ 확인 못 한 매수는 주문표를 내지 않는다(화면이 null lo·hi에서는 가격을 그대로 보이므로).
- 내장 재검토(Opus, 1회차): 발견 14건 중 원문으로 다시 확인해 12건 반영 — R2 실데이터가 주문표 0건으로 끝날 수 있음 → R2b 강제 측정·R3 최악값 · 계산기 누수(HOLD_RANGE_UNVERIFIED 날 MISMATCH) 명시 · hold를 _limit_daily 뒤로 · 일지 decision_sha256 예외 · E4 가짜 S7을 (symbol, target)로 · G2b 유지 조건 · H11을 같은 프로세스 끔/켬 비교로(OS 무관) · classify_outcome 가드 단어 · epoch 이름 GATE:HOLD_RANGE_UNVERIFIED · 봉 사본 사실 정정 · PLTR 기준선 원인 정정 · 매수 row·매도 첫 사유. 결정 기록 26행 loc_price 행 번호(369~385 → 376~392)는 결정 기록 상태 줄에서 고친다. 반영하지 않은 것: 화면 null 처리(이 세션이 live HTML에서 직접 확인함 — 근거 2).
- 내장 재검토(Opus, 2회차 — 고친 부분만): 발견 10건 반영 — 근사 종가가 센트 사이 값인 날이 흔함(10-20 decision에서 직접 확인) → REF_NOT_CENT 삭제·⌈ref⌉/⌊ref⌋부터 스캔 · 누수 날 처분을 사전 등록 16·24·48행대로(Judge는 더 엄격하게만) · enter-window 테스트 import 1줄·되돌리기 깊은 복사 · H11 끄는 mock 방법 · G2b 문구 · E2 하류 값 · 리플레이 기간 문구 · 보충 ETF 제안 조건 · 패널 35행 · R2b P-R1 ctx. 최대 2회라 3회차는 돌리지 않았다.
