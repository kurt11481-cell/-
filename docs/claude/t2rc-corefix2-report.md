---
id: t2rc-corefix2-report
title: t2rc-corefix2 Builder 보고 — 코어 5건 수정 (t2-rc 독립 Judge 2026-10-15 11절 "코어")
date: 2026-10-15
prompt: docs/claude/t2rc-corefix2-builder-prompt.md
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음 · 커밋 없음
---

# t2rc-corefix2 Builder 보고

## 요약

- 다섯 항목을 모두 넣었다. 바꾼 파일은 allowed_paths 안의 다섯 개다.
  - 코드: auto_core_rules.py, auto_core_decide.py, auto_core_tickets.py
  - 테스트: 새 파일 test_auto_core_t2rc_corefix.py, 기존 test_auto_core_risk1r.py(GOLDEN["sell"] 한 키)
- 골든:
  - 다섯 항목을 넣은 뒤 다시 잰 GOLDEN["sell"]은 `07c781346ca9dfa243a83e826f83759e0e57751b7f1b02eb3fb52b9e716cdfb0`다. 지시문에 정해 둔 값과 정확히 같아서 그 한 키만 바꿨다.
  - 나머지 7개 키(default, g2b, cash5, research_block, pwr, decide_compare, decide_apply)는 그대로다(아래 측정 출력).
- 테스트:
  - 대상(test_auto_core*): Ran 405, OK(skip 1). 변경 전 기준선은 Ran 383, OK(skip 1)였다. 새 테스트 22개.
  - 전체: 아래 "테스트 결과" 참고.
  - 스키마 감사: PASS.
- 규칙 파일·카드·등록부·정책·상태·스키마·CONSTANTS·관문 기준값은 바꾸지 않았다. 주문 경로·권한 표지·키움 호출도 없다.
- 1회차 worktree는 이 세션의 허용 경로 밖이라 읽기가 막혔다. 그래서 1회차 코드는 참고하지 않고 지시문만 보고 새로 구현했다.

## 바꾼 줄과 항목별 새 규칙

### 1. R-REC1 벤치마크 — SOXX 기준, GRID는 RG2 다리에만

- auto_core_rules.py
  - 751: 표지 `SAME_AS_BENCHMARK`
  - 754-757: `rrec1(..., rg2_series=SAME_AS_BENCHMARK)`
  - 760-765: docstring
  - 870-876: RG2 벤치마크 다리
  - 924: `rg2_benchmark` docstring
- auto_core_decide.py 1039-1046: 후보별 rrec1 호출

새 규칙:
- 모든 후보의 rrec1 `benchmark`는 SOXX(`rules.C["RREC_BENCHMARK"]`)다. 다음은 모두 SOXX로 계산한다.
  - 사건: EV1, EV2, EV3ⓑ
  - EV3ⓑ 기록 공백 검사
  - C0, L0, RG3, RG4, DS1
- 업종 벤치마크(`rg2_benchmark(sector)`, A1 전력이면 GRID)는 `rg2_series`로 들어간다. RG2의 벤치마크 다리(벤치마크 종가 ≥ 벤치마크 EMA50)에만 쓴다.
  - 후보 다리(후보 종가 ≥ 후보 EMA50)는 그대로다.
  - GRID 자료가 없으면(None) 그 다리는 unk다. 그래서 매수는 막힌다(fail closed).
- `rg2_series`를 주지 않으면 지금처럼 benchmark 자신을 쓴다. 포트폴리오 shock 호출과 기존 테스트가 이 경우다.
- EV4(계좌)·EV5(종목 자체)는 그대로다.
- Judge2 메모 2(2026-10-11, "공백 검사는 각 후보의 RG2 벤치마크")는 이 판정으로 바뀐다. 공백 검사는 이제 모든 후보에서 SOXX다(규칙 파일 102행, recovery-gate-R-REC1-2026-10-09.md 30행).
- 효과 방향(섞임):
  - SOXX 충격이면 A1 전력 후보(BE·PWR)도 막힌다.
  - GRID만의 충격이면 더는 막히지 않는다.
  - 매도는 이 관문으로 막지 않는다(지금과 같음).

### 2. RG3 신저가 창 — 이벤트 다음 세션부터

- auto_core_rules.py 883: `lows = [s["low"][k] for k in range(e + 1, i + 1)]`. 전에는 `range(start + 1, ...)`이었고 start = max(이벤트, 마지막 DS1)였다.

새 규칙:
- 저가 조건(모든 정규장 저가 ≥ L0)은 이벤트 다음 세션부터 판정 세션까지 본다.
- DS1은 "연속 2세션 종가 > C0" 셈만 처음으로 되돌린다(`start = max(e, last_ds1)`는 종가 셈에만 남는다). 저가 창은 되돌리지 않는다.
- 저가 보정(v3.12.1 정규장 저가 규칙)은 바꾸지 않았다. 바 적재 쪽 코드도 손대지 않았다.
- 효과: 매수를 더 막는다. 매도에는 영향이 없다.

### 3. 새 근거와 전 세션 unk

- auto_core_rules.py 698: `new = [group for group in hits if group.get("previous_state") in ("none", "pending")]`. 전에는 `!= "hit"`이었다.

새 규칙:
- 전 세션 state가 none·pending이고 오늘 hit인 그룹만 새 근거(new_groups → new_kinds)다.
- 전 세션이 unk이거나 키가 없으면 새 근거가 아니다(fail closed). 그룹의 전 세션 state는 지금처럼 그룹 안 규칙들의 최댓값 순위로 정한다.
- 영향:
  - 바뀌는 것: 매수 회로의 "새 근거만으로 충족"(`new_basis_met`), 그리고 표시 문구 "카드 표 N + 새 M"의 M.
  - 그대로인 것: `basis_met`(카드 표 N + 새 M 전체), 매도 회로(basis_met만 봄), S7 추가 경로(요건 ③ + S7 add).
- 개별 트리거의 표시용 `new` 필드는 바꾸지 않았다(지시문 범위가 매수 회로뿐이다).

### 4. 재배치 후보 거르기

- auto_core_decide.py
  - 1078-1080: 순위 호출
  - 1090: ctx `redeploy_ranked`
  - 1110-1129: `REDEPLOY_REQUIRED_CELLS`, `redeploy_ranking()`
- auto_core_tickets.py
  - 694-700: plan()의 후보 선택
  - 704-708: 매도 회로 루프
  - 756-774: `_sell_gap_sources()`

새 규칙:
- 후보(`redeploy_ranking`)는 다음을 모두 갖춘 종목이다.
  - 그날 매수 요건 행의 ①·③·④·⑤ 칸이 모두 ok
  - alert_policy `card_stock_core ∪ allowed_index_etfs`에 있음. 그래서 매도 전용 MVLL은 빠진다.
  - 등록부 자격(`eligible`)
  - 시나리오 수익률 ok
- 순위는 지금 그대로다(강 근거 수 → 약 근거 종류 수 → 종목 코드).
- plan()은 그날 매도 회로가 열린 보유 종목(갭 원천 + 매도 basis_met)을 먼저 순수 계산으로 구한다. 그날 파는 종목은 모두 여기에 든다. 남은 첫 순위를 `redeploy_candidate`로 쓴다.
  - 그래서 판 종목이 1위면 2위가 후보다.
  - 남는 종목이 없으면 후보는 None이고 현금 열만 남는다.
- 거르지 않는 것: ②(노출·현금), S7 멈춤, 판 뒤 E.
- 후회표 모양(4열 한 표, 매도 대금 전부, 센트 반올림)과 `after_sale_path`는 바꾸지 않았다.
- 갭 원천 계산은 `_sell_gap_sources`로 뽑아 냈다. 그래서 사전 계산과 매도 루프가 같은 함수를 쓴다. blocked 항목의 순서와 내용은 그대로다(GOLDEN 7개 키 불변으로 확인).

### 5. G3 ⅓ 상한의 card_defined — 매수 근거에만(사용자 결정 5 = b)

- auto_core_rules.py 691-707: `price_evidence`

새 규칙:
- 매수(+) 근거: 그룹이 card_defined인 것은 같은 그룹·같은 방향의 카드 트리거(source "card")가 오늘 hit일 때다. 정의만 있는 것으로는 안 된다.
- 매도(−) 근거: 지금 그대로다. 그 그룹에 카드 트리거 정의가 있으면 card_defined다.
- 지금 + 방향 카드 종류(new_high_hold, pullback_rebound)는 모두 공통 규칙을 대체한다. 그래서 그룹이 hit이면 카드 트리거도 hit이고, 현재 자료로는 결과가 바뀌지 않는다(GOLDEN 불변으로 확인).

## 테스트

### 새 테스트 — manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py (22개)

| 항목 | 클래스·테스트 | 내용 |
|---|---|---|
| 1 | SoxxEventTests.test_grid_only_minus_two_sigma_day_is_no_event_for_a_power_candidate | A1 전력 PWR, GRID만 −2σ 이상 하락(검증 포함) → 사건 없음, ⑤ ok |
| 1 | SoxxEventTests.test_soxx_minus_two_sigma_day_opens_the_event_with_soxx_c0_and_l0 | SOXX 470 → PWR·MU 모두 EV1, C0 470.0·L0 465.3(SOXX 값), PWR ⑤ ≠ ok |
| 1 | SoxxEventTests.test_power_candidate_record_gap_is_checked_on_soxx | SOXX 1σ 하락일의 기록 공백 → unk·EV3B_RECORD_GAP. GRID만 떨어지면 공백 아님 |
| 1 | Rg2BenchmarkLegTests (5개) | GRID < EMA50 → RG2 no. GRID·후보 ≥ EMA50 → 닫힘. 후보 < EMA50 → no. GRID 없음 → unk. 기본값 = 벤치마크 |
| 2 | Rg3LowWindowTests.test_low_below_l0_before_the_ds1_keeps_rg3_no | DS1 앞(이벤트 뒤) 저가 98 < L0 99 → DS1 뒤 회복해도 RG3 no |
| 2 | Rg3LowWindowTests.test_lows_at_or_above_l0_and_two_closes_after_the_ds1_close_the_event | 저가 모두 ≥ L0 → DS1 뒤 2세션(16·17) 종가 > C0에서 닫힘(closed_at = 17) |
| 3 | NewEvidenceTests (4개) | 전 세션 unk → new_kinds 없음·new_basis_met false·basis_met 그대로. none·pending → 새 근거. 매도 basis 불변. 시나리오에서 SOXL NEW_EVIDENCE 회로가 닫히고 S7 추가 경로만 남음 |
| 4 | RedeployRankingTests.test_filter_and_rank | MVLL(매도 전용)·⑤ no·① no·③ unk·④ no·카드/시나리오 없음은 빠짐. ② no는 거르지 않음. 순위 확인 |
| 4 | RedeployPlanTests.test_open_sell_circuit_without_a_ticket_is_left_out | 매도 회로가 열렸으나 주문표가 없는(G0) 종목도 빠짐. 남는 종목이 없으면 None |
| 4 | RedeployPlanTests.test_first_ranked_symbol_sold_today_gives_way_to_the_next | 판 SOXL이 1위여도 MU가 후보(후회표 열 `up:MU`, 교체 쌍 MU) |
| 4 | RedeployPlanTests.test_requirement_1_or_5_not_ok_leaves_only_cash | MU ① 금지 구간 또는 ⑤(R-REC1 열림) → 현금 열만, 교체 쌍 없음 |
| 5 | CardDefinedTests (4개) | 매수: 카드 정의 있음·hit 아님 + 공통 C 2종 → ⅓. 카드 hit → ½. 매도: 같은 모양 → ½. price_evidence 직접 확인 |

위 새 테스트는 대부분 변경 전 코드에서는 실패하는 조건으로 짰다.
- 항목 1·2·3·5: 판정 차이를 직접 단언한다.
- 항목 4: 함수 `redeploy_ranking` 자체가 새로 생겼다.

### 고친 기존 테스트

| 파일:행 | 전 | 후 | 이유 |
|---|---|---|---|
| test_auto_core_risk1r.py:41-43 GOLDEN["sell"] | `a3a2372037ca36cdc2ed355be7b5585e2538988e8e82f0a7c49a8c9f69509dbb` | `07c781346ca9dfa243a83e826f83759e0e57751b7f1b02eb3fb52b9e716cdfb0` (주석 2줄 추가) | 항목 4. 고정 자료는 SOXX 470(EV1)이라 R-REC1이 열려 있다. 그래서 MU ⑤ = no가 되어 재배치 후보에서 빠지고, 후회표에 현금 열만 남는다. 재측정값이 지시문에 정해 둔 값과 정확히 같다 |

- 그 밖의 기존 테스트는 검사 문장도 고정 자료도 바꾸지 않았다. 모두 그대로 통과한다.
- test_auto_core_compare_fix T5 불변 테스트도 고치지 않았고 통과한다.

### 골든 측정 출력(수정 전 실행, 다섯 항목 적용 후)

```
"default": "a62e2e538cebc610e15f771d84754ec18d9f5b3b145aa00e35900780f60b3d2c"   (불변)
"g2b": "0857c795b26629af20982b09bb815f995ccb1d7340b9ea580031b3c6ac28bca9"       (불변)
"cash5": "c3ad82a2d647e0da1a14fa5a65fe7545f52cf509d16af8e576b1826c0f4ec4c8"     (불변)
"research_block": "8254e97e2e1ea50b89e966120d83e942bc32d1bd34a0c19eaac3e83252273091" (불변)
"sell": "07c781346ca9dfa243a83e826f83759e0e57751b7f1b02eb3fb52b9e716cdfb0"      (← a3a23720…, 정해 둔 값과 일치)
"pwr": "85e3651e053e32a99d1c61ace526692810c14a2c76b7ce3a32fce0aca53d7133"       (불변)
"decide_compare": "929a8d0059f7743b733826bc6f731d47d07a9f2868349c681173b06aab323492" (불변)
"decide_apply": "431712bf43bcbb315a612c6f56492e7dc2e4fa175910f409aec84c281f383e71"   (불변)
```

### SOXL 매도 주문표 전후 (GOLDEN "sell" 고정 자료: SOXL 120주, 현금 300, SOXX 마지막 470)

측정 방법:
- 같은 프로세스에서 `git show HEAD:`로 변경 전 세 모듈을 불러 같은 고정 자료를 돌렸다.
- 이 측정은 임시 테스트 파일로 했다. 그 파일은 지금 test_auto_core_t2rc_corefix.py 본 내용으로 덮어썼다.

| | 변경 전 | 변경 후 |
|---|---|---|
| 수량 | 19주 (gap 57, r 1/3, r_max 1/3, WITHIN_REGRET_BUDGET) | 19주 (같음) |
| 후회표 열 | up:cash, down:cash, up:MU, down:MU | up:cash, down:cash |
| 행 r 0 (0주) 최대 후회 | 109.49 (up:MU 57.99, down:MU 0.0 포함) | 109.49 |
| 행 r 1/3 (19주) 최대 후회 | 72.99 (up:MU 38.66, down:MU 2.12 포함) | 72.99 |
| 행 r 1/2 (28주) 최대 후회 | 55.70 (up:MU 29.5, down:MU 3.13 포함) | 55.70 |
| 행 r 1 (57주) 최대 후회 | 109.11 (up:MU 0.0, down:MU 6.37 포함) | 109.11 |
| 예산 | 318.6 | 318.6 |
| 교체 쌍(after_sale.swap_pair) | SOXL 19주 → MU 0주 | 없음(None) |
| MU 매수 요건 칸 | ① ok ② no ③ ok ④ ok ⑤ no | 같음 |

- 수량은 바뀌지 않았다. MU 열의 후회가 모든 행에서 현금 열보다 작아서, 행별 최대 후회와 선택(r 1/3)이 같다.
- 바뀐 것은 다음 둘뿐이다. 이것이 해시가 바뀐 원인이다.
  - 후회표 열: MU 두 열이 빠졌다.
  - 교체 쌍 표시: 없어졌다.

## 테스트 결과

- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`
  - 기준선(변경 전): Ran 383, OK (skipped=1)
  - 변경 후: Ran 405, OK (skipped=1). 새 실패 0.
- 새 파일만: `-p "test_auto_core_t2rc_corefix.py"` → Ran 22, OK
- 전체: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` → Ran 3069, FAILED (failures=19, errors=9, skipped=3)
  - 실패·오류 28건은 모두 다음 13개 모듈에 있다. auto-core 테스트는 하나도 없다.
    - test_v2_6_7_session_aware_kiwoom_priority (14건, 실패 subTest 포함): "current Acceptance binding must resolve to exactly one manifest … matches=[]"
    - test_materialize_kiwoom_session_aware_acceptance_candidate (2건)
    - test_nbis_v4_kiwoom_price_authority (2건)
    - 그 밖의 모듈 1건씩: test_holding_baseline_observation_audit·test_mvll_canonical_volume_lineage·test_provider_limitation_audit(setUpClass), test_portfolio_decision_order_intent, test_nbis_v3_shadow_activation, test_validate_research_packet, test_instrument_identity_authority, test_materialize_instrument_identity_artifact, test_evaluate_timing_integration, test_portfolio_decision_dashboard
  - 바뀐 세 모듈(auto_core_rules·auto_core_decide·auto_core_tickets)을 부르는 곳은 auto_core*.py 스크립트와 test_auto_core* 테스트뿐이다(grep). 실패한 13개 모듈은 이것들도, auto_core*.py도 import하지 않는다(grep: test_materialize_kiwoom_session_aware_acceptance_candidate.py:472는 핀 목록 경로 문자열이다). 그러니 이 실패들은 이 변경과 관계가 없다.
  - 원인 메시지는 workspace의 Acceptance manifest·산출물이 없다는 뜻이다(1회차의 "worktree에는 workspace 산출물이 없다"와 같다).
  - 변경 전 코드로 전체 스위트는 돌리지 않았다. 공유 stash를 쓰지 않으려고 작업 트리를 되돌리지 않았기 때문이다. 그래서 "기준선과 같은 실패"는 측정이 아니라 import 경로로 판단한 것이다. dev-run의 기준선 비교에서 확인된다.
- 스키마 감사: `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → `{"status": "PASS", "errors": []}`

## 실자료 확인

- 이 회차에서는 하지 않는다(worktree에 workspace 산출물이 없다).
- Cowork가 병합 뒤 2026-10-15 입력으로 다음을 변경 전후로 확인한다.
  - BE·PWR의 R-REC1(사건·C0·L0·RG2 다리)
  - 매수 요건 ⑤ 칸
  - 재배치 후보

## 남은 위험

- 효과 방향:
  - 항목 1: SOXX 사건이 있는 날에는 A1 전력 후보(BE·PWR)의 매수도 막힌다. 반대로 GRID만의 −2σ 날에는 더는 막히지 않는다.
  - 2026-10-15 실자료에서 BE·PWR ⑤ 칸이 바뀔 수 있다. Cowork 확인 대상이다.
- 항목 1 RG2:
  - GRID 자료가 없거나 GRID 마지막 세션이 평가 세션과 다르면, A1 전력 후보의 RG2는 unk다. 그 후보의 매수는 막힌다(fail closed).
  - 전에는 GRID가 없으면 R-REC1 전체가 BENCHMARK_DATA_MISSING(unk)였다. 지금은 사건이 있을 때만 RG2가 unk다. 사건이 없으면 ok다.
  - 사건이 없을 때 GRID 결측이 매수를 막지 않는 것은 규칙(RG2는 열린 사건의 해제 조건)과 맞다.
- 항목 3: 전 세션 그룹 state가 그룹 안 최댓값 순위로 합쳐진다. 그래서 같은 그룹의 한 규칙이 전 세션 unk이면, 다른 규칙이 none이어도 그룹은 unk로 보고 새 근거에서 빠진다(보수적).
- 항목 4:
  - 재배치 후보는 그날 매수 요건 칸을 쓴다. 그래서 ②가 no여도 후보가 된다(지시문대로, D+1 관문이 다시 본다).
  - 교체 쌍은 표시일 뿐이며 매수 주문표가 아니다(`buy_is_ticket: false`, 불변).
- auto_core_replay.py는 evaluate_session을 같이 쓰므로 자동으로 같은 규칙을 탄다. replay 파일 자체는 고치지 않았다(범위 밖).
- 1회차 worktree 코드는 읽지 못했다(허용 경로 밖, 자동 거부). 두 회차의 구현이 같은지는 비교하지 않았다. 골든 "sell" 재측정값은 정해 둔 값과 같다.
