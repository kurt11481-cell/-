---
id: policy-a-report
date: 2026-11-26
status: "Builder 완료 — Judge 대기 (커밋·병합 없음)"
source: docs/claude/policy-a-builder-prompt.md (sha256 0f9f1cd0b94a9bba7226301828ab1ad12fdf5959cee4822f9090456f5b06d664, 23552바이트)
---

# 정책 묶음 A Builder 보고

worktree E:\사업\##금동한\코덱스저장소\.claude\worktrees\unruffled-fermat-725de3 · 브랜치 worktree-policy-a · 기준 커밋 9e48ef285e152ef156efdf86ade82d0fbdad9c14
지시문 sha256 0f9f1cd0b94a9bba7226301828ab1ad12fdf5959cee4822f9090456f5b06d664 · BLOCKED 2회 뒤 보완 2로 재개

## 1. 한 줄
3배 상한 0.10(3배를 늘리는 매수만)과 채우기 기본 '카드 ADD 종목만'을 넣었습니다. 기존 테스트는 ① 7곳과 ③ 8곳을 고쳤고(③은 모두 (가) — 사본을 넣는 줄만 더함), D.i 3개를 더했습니다. 대상·전체 테스트에서 기준선 밖 새 실패는 0입니다(아래 5절). 커밋·push·병합은 하지 않았습니다. 멈춘 기록 docs/claude/policy-a-BLOCKED.md(1·2차)는 남겼습니다.

## 2. 바뀐 줄 (파일:행, 앞 → 뒤)
### stock-strategy-system/alert_policy.json (CRLF 유지, 933 CRLF·LF 0, JSON 파싱 정상)
- 750행 `"add_default": "card_add_stock_else_SOXL"` → `"card_add_stock_only"`
- 771행 새 키 `"leveraged_3x_weight_cap": {"max_weight_sum": 0.10, "applies_to_nominal_multiplier_gte": 3, "applies_to": "exposure_increasing_buy_of_member_only", "weight_basis": "s7_closing_value_over_closing_equity", "source": "strategy-1101 / policy-a-1126"}`
- 그 밖(문턱 1.55·1.85·1.25·1.9, reduce_order, single_stock_*, allowed_index_etfs, nominal_multipliers, add_when_default_paused, 권한 표지 줄) 무변경.

### manage-us-stock-strategy/scripts/portfolio_exposure.py (ASCII, CRLF)
- 126~161행(새): 상수 `ADD_DEFAULT_CARD_ONLY`·`LEVERAGED_CAP_REASON = "LEVERAGED_3X_WEIGHT_CAP"`·`NO_DEFAULT_ADD_REASON = "NO_CARD_ADD_AND_ADD_DEFAULT_IS_CARD_ADD_STOCK_ONLY"` 등, `add_supplement_instrument(section)`(옛 값 `card_add_stock_else_<reduce_order 끝>` → 그 종목, `card_add_stock_only` → None, 그 밖 → ExposureError), `leveraged_cap_config(section)`(없거나 형식이 틀리면 ExposureError, 기본값 없음).
- exposure_config 163행~: 176~181행 add_default 검사를 `add_supplement_instrument`로 옮김(옛 값·새 값 둘 다 받음), 212~214행 config 새 칸 `add_supplement`·`leveraged_cap`·`leveraged_bound`. `supplement` 칸(줄이기 3순위 뜻)은 그대로.
- 1271~1280행(새): `leveraged()`(배수 ≥ 3), `leveraged_weight_sum()`.
- 1282~1298행 projected_increase_reasons: 늘리는 종목이 3배일 때만 투영 비중의 3배 합 > 0.10이면 `LEVERAGED_3X_WEIGHT_CAP`. 1배 매수에는 붙지 않음.
- 1540~1544행 채우기 후보: 카드 ADD → 없으면 add_supplement(None이면 후보 없음 + omitted `{kind add, symbol null, reasons [NO_CARD_ADD_AND_ADD_DEFAULT_IS_CARD_ADD_STOCK_ONLY]}` 1줄).
- cap_limit(1161)·cap_breaches(1169)·reduce_recommendations(1190~)·S7 산출 `policy` 칸: 무변경.

### manage-us-stock-strategy/scripts/auto_core_decide.py (ASCII, CRLF)
- 1100~1113행: S7에 넘기는 basis_met 갈래가 `reduce_order[-1]` 대신 `add_supplement_instrument(정책)`을 씀. None이면 이 갈래 없음. new_basis_met 갈래 그대로.

## 3. 새 키·값
- `portfolio_exposure_policy.leveraged_3x_weight_cap.max_weight_sum` = 0.10 (배수 ≥ 3인 종목의 S7 평가 비중 합)
- `portfolio_exposure_policy.add_default` = `card_add_stock_only`

## 4. reduce_order[-1]·supplement grep (scripts 전체, 고친 뒤)
- 채우기 뜻: portfolio_exposure.py 142행(add_supplement_instrument 안, 옛 값 검사용) · 180·213행(add_supplement 칸) · 1542행(채우기 후보) · auto_core_decide.py 1109~1112행 — 모두 add_supplement를 거침.
- 줄이기 뜻(그대로): portfolio_exposure.py 176~177·212행(supplement 칸) · 1190~1225행(줄이기 3순위) · run_portfolio_exposure_review.py 527행(종가 수집 종목) · 코어 본체 스크립트 163행(종가 수집 종목, 읽기만).
- auto_core_tickets.py: reduce_order·supplement·add_default 없음(무변경).
→ 채우기 쪽에서 SOXL이 나오는 길은 옛 add_default 값일 때뿐.

## 5. 테스트 (python 3.15.2, PATH의 python, tzdata 정상 — py -3.13 안 씀)
기준선(바꾸기 전) = 1차 Builder가 같은 worktree에서 바꾸기 전에 잰 값(policy-a-BLOCKED.md 29~39행). 이번 재개는 새 worktree를 만들 수 없어 기준선을 다시 재지 않았습니다.
| 대상 | 바꾸기 전 | 바꾼 뒤 |
|---|---|---|
| test_policy_a.py | Ran 0 | Ran 19 OK (skip 0) |
| test_portfolio_exposure*.py | Ran 154 OK | Ran 154 OK |
| test_run_portfolio_exposure_review*.py | Ran 29 OK | Ran 29 OK |
| test_auto_core* | Ran 667, 실패 1(기준선 test_auto_core_decide RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches), skip 1 | Ran 667, 실패 1(같은 기준선), skip 1 |
| test_qqq_registration.py | Ran 8 OK | Ran 8 OK |
| test_swing_k3_registration.py | Ran 8 OK | Ran 8 OK |
| validate_schema_contracts.py | PASS | PASS |
| 전체 -p "test_*.py" | Ran 3974, 실패 4(test_auto_core_decide RegistryTests · test_dev_pipeline_api_route PickRouteTests.test_repository_switch_is_off · test_llm_pilot_pdfcmp test_script_source_contract · test_test_only_scheduler_control_plane test_os_diagnostic_d_uses_harmless_launcher), skip 3 | Ran 3993(+19 = test_policy_a), 실패 4(같은 4개), skip 3 |
→ 기준선 밖 새 실패 0.

`git diff --ignore-cr-at-eol --stat`:
13 files changed, 113 insertions(+), 24 deletions(-) — auto_core_decide.py 10 · portfolio_exposure.py 66 · alert_policy.json 3 · test_auto_core_enter_window.py 2 · test_auto_core_hold_range.py 6 · test_auto_core_risk1r.py 2 · test_auto_core_t2rc_corefix.py 2 · test_auto_core_tickets.py 2 · test_portfolio_exposure.py 29 · test_portfolio_exposure_fail_closed.py 6 · test_qqq_registration.py 2 · test_run_portfolio_exposure_review.py 5 · test_swing_k3_registration.py 2. 추적 안 되는 새 파일: test_policy_a.py, policy-a-BLOCKED.md, 이 보고서.

## 6. 고친 기존 테스트 표
| 파일:행(고친 뒤) | 종류 | 고친 법 | 앞 → 뒤 |
|---|---|---|---|
| test_qqq_registration.py:76 | ① | 새 정책 기대값 | add_default `card_add_stock_else_SOXL` → `card_add_stock_only`(정책 값 고정 시험) |
| test_swing_k3_registration.py:91 | ① | 새 정책 기대값 | 같음 |
| test_portfolio_exposure.py:302~309 test_default_add_is_soxl_up_to_the_target | ① | 새 정책 기대값 | SOXL 0.516 채우기 → add [] · omitted NO_DEFAULT 1줄 · S5_ADD_RECOMMENDATION 없음. 옛 add_default만 덮어쓰면 SOXL 0.30이 이미 상한 위라 0.516이 안 나와 이 법을 고름 |
| test_portfolio_exposure.py:340~356 test_projected_exposure_above_target_omits_the_add | ① | 새 정책 기대값 | 앞부분 사유 [PROJECTED_EXPOSURE_ABOVE_TARGET] → [..., LEVERAGED_3X_WEIGHT_CAP] · 뒷부분 SOXL 채우기 add[0] → add [] + NO_DEFAULT. 남는 위험: 'V가 목표를 먼저 줄인다' 단언이 이 함수에서 빠짐 |
| test_portfolio_exposure.py:360~361 test_soxl_paused_by_peak_review_omits_the_add_without_substitute | ① | 사본의 add_default만 옛 값 | 줄 2개(주석·덮어쓰기) 더함, 기대값 줄 그대로 — 옛 채우기 동작 시험이 남는 곳 |
| test_portfolio_exposure_fail_closed.py:409~413 | ① | 새 정책 기대값 | `assertTrue(add)` → add [] + NO_DEFAULT omitted |
| test_run_portfolio_exposure_review.py:195~200 | ① | 새 정책 기대값 | add 종목 ["SOXL"] → [] · "채우기 권고 1건(...)" → 출력에 "채우기 권고" 없음(러너가 실제 정책 파일을 읽음) |
| [1] test_portfolio_exposure.py:467 ProposalTests.test_new_buy_within_band_is_shown_only_when_projected_exposure_and_cap_hold | ③ | (가) | 줄 1개(scenario.policy 사본의 상한 1.0) 더함, 기대값 그대로 |
| [2] test_auto_core_t2rc_corefix.py:187~188 NewEvidenceTests.test_scenario_buy_circuit_closes_when_the_previous_session_is_unknown | ③ + ① | (가) | 줄 2개(사본: 상한 1.0 + 옛 add_default) 더함 |
| [3] test_auto_core_tickets.py:636~637 ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy | ③ | (가) | 줄 2개(사본: 상한 1.0) 더함 |
| [4] test_auto_core_hold_range.py:331~332 FullPathTests.test_supplement_proposals_change_with_the_close | ③ + ① | (가) | 줄 2개(사본: 상한 1.0 + 옛 add_default) 더함 |
| [5] test_auto_core_hold_range.py:755~756 HoldCauseTests.test_reverted_view_hashes_as_the_old_golden | ①(보완 2: 원인 add_default) | (가) | 줄 2개 더함, 옛 해시 글자 그대로 |
| [6] test_auto_core_hold_range.py:557~558 HoldOffTests.test_default_off_keeps_the_six_golden_keys | ①(원인 add_default) | (가) | 같음 |
| [7] test_auto_core_risk1r.py:201~202 UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before | ①(원인 add_default) | (가) | 같음 |
| [8] test_auto_core_enter_window.py:214~215 GoldenCauseTests.test_the_old_enter_window_gives_the_base_golden | ①(원인 add_default) | (가) | 같음 |
- 지시문 ① 목록의 test_auto_core_t2rc_corefix.py 210~212행은 [2]와 같은 함수(위 2줄로 처리), test_auto_core_tickets.py 806행은 실패하지 않아 고치지 않음. ② 손 fixture 고침: 없음.
- 사본을 넣는 법: test_policy_a.py `policy_file_copy(cap, old_add_default)` — 실제 정책 파일 바이트에서 `"max_weight_sum": 0.10`(와 add_default 값)만 바꾼 임시 파일을 만들고 mock.patch로 fixtures 도우미의 `POLICY_PATH`와 s5_exposure_fixtures의 `POLICY_PATH`를 그 파일로 돌림. 각 시험은 `import test_policy_a` + `self.enterContext(...)` 두 줄만 더함. scripts·공용 도우미·fixtures 파일은 무변경.
- 옛 동작 시험이 남는 곳: test_portfolio_exposure.py 고점 검토 시험, ③ 8곳 전부(사본), test_policy_a.py b·c·g.

### ③ (ㄱ) 원인 확인
실험(scratchpad 스크립트, worktree에 넣지 않음)에서 같은 사본 방법으로 8곳을 그대로 돌림.
| 곳 | 상한 1.0만 | 상한 1.0 + 옛 add_default | 분류 |
|---|---|---|---|
| [1] | 통과 | — | ③ |
| [2] | 195행 통과, 212행 실패(S7_ADD 갈래) | 통과 | ③+① |
| [3] | 통과 | — | ③ |
| [4] | 실패(hold lo 100.1 CIRCUIT_CLOSED) | 통과 | ③+① |
| [5]~[8] | 실패 | 통과(옛 해시 글자 그대로) | ① — 상한만 1.0인 사본과 실제 정책 산출이 정책 지문(inputs.alert_policy.sha256)·임시 경로 말고 같음 |
정책 지문은 골든 해시 대상에 없어 '지문 칸 제외'가 필요 없었습니다.

### ③ (ㄴ) 바뀐 칸 (실제 정책 산출 ↔ 사본 산출. 매 실행 다른 임시 경로 `inputs.*.path`는 뺌)
자동 대조 스크립트로 주문표(종목·방향별 전 칸), blocked, candidates, proposal_results, S7 review 전 칸, rows, 결정 status를 비교 — 허용 밖 칸 0건.
| 곳 | 다른 칸 (키 경로: 실제 → 사본) |
|---|---|
| [1] | recommendations.proposals[2].reasons(TQQQ 0.05): [PROJECTED_EXPOSURE_ABOVE_TARGET, LEVERAGED_3X_WEIGHT_CAP] → [PROJECTED_EXPOSURE_ABOVE_TARGET] · review_id(S7 산출 식별자) |
| [3] missing | review.recommendations.proposals·proposal_results의 SOXL 격자 416칸(0.101 이상 목표의 status OMITTED·reasons [LEVERAGED_3X_WEIGHT_CAP] → DISPLAY·[]) · review_id |
| [3] with_record | 위와 같음 + planned.tickets: SOXL 매수 없음 → 49주 $4,929.40 · planned.blocked: [SOXL 매수 DEADBAND] → [] · MU 매수 주문표 inputs.s7_review_id(종목·수량 28·가격 218.86·금액 6128.08 같음) |
| [2] opened · [4] | [3] with_record와 같은 칸 + review.recommendations.add [] → [SOXL 채우기 0.516] · omitted [NO_DEFAULT] → [] · alerts [] → [S5_ADD_RECOMMENDATION] |
| [2] shut | planned.candidates: SOXL 'S7_ADD_RECOMMENDATION' 매수 후보 없음 → 있음 · planned.tickets: SOXL 매수 없음 → 49주 $4,929.40 · basis_met 갈래 SOXL 제안 516칸(proposal_results·proposals 길이) · add·omitted·alerts(위와 같음) · review_id · MU 주문표 inputs.s7_review_id(나머지 같음) |
| [5]~[8] 시나리오 default·g2b·research_block·pwr | review.recommendations.add [] → [SOXL 채우기 0.516] · omitted [NO_DEFAULT] → [] · alerts [] → [S5_ADD_RECOMMENDATION] · review_id · default·pwr의 MU(28주 $6,128.08)·PWR(19주 $6,057.77) 매수 주문표 inputs.s7_review_id(나머지 같음) |
| [5]~[8] 시나리오 cash5·sell | 다른 칸 없음(매도 주문표·줄이기 권고 같음) |
| [5]~[8] decide compare/apply | status OK/OK 같음 · inputs.alert_policy.sha256(정책 지문) · inputs.s7_review.review_id · MU 주문표 inputs.s7_review_id(나머지 같음) · apply의 journal.decision_sha256(묶음 해시 — 위 식별자만으로 바뀜) |
- 식별자(review_id·s7_review_id)가 가리키는 S7 산출 자체의 차이는 위 표의 SOXL 제안·채우기 권고·omitted·alerts 칸뿐(보완 2 허용 칸).
- 매도·줄이기 권고·경고·fail-closed·1배 종목의 수량·가격·금액·게이트: 다른 칸 없음. 결정 status 다름 없음.

### ③ (ㄷ) 새 단서 SOXL 3곳 수치 ([2] opened·[3] with_record·[4]는 같은 입력)
| 칸 | 실제 정책(0.10) | 상한 1.0 사본 |
|---|---|---|
| 자산(S7·코어 equity) | $31,005.00 | 같음 |
| 3배 비중 합(SOXL 0.032414 + TQQQ 0) | 0.032414 | 같음 |
| 여유 0.10 − 합 | 0.067586 ($2,095.50) | — |
| 통과한 가장 큰 목표 | 0.100 (0.101부터 LEVERAGED_3X_WEIGHT_CAP) | 0.516 |
| 근거 단계 비율(r_max → 고른 단계) | 1/3 → 1/3 | 같음 |
| 주문표 금액(코드) | delta = floor((0.100 − 0.032414) × 31,005 ÷ 100.50) = 20주 → qty = floor(20 × 1/3) = 6주 → 6 × $100.50 = $603.00 | 149주 → 49주 → $4,924.50(기준가 기준. 주문표 amount는 LOC 가격 기준 $4,929.40) |
| 최소 금액(자산 2%) | $620.10 | $620.10 |
| 결과 | 주문표 없음 — DEADBAND(기존 규칙, 멈춤 아님) | 주문표 1장 |
코드 행: auto_core_tickets.py 1128행 best_target → 1142~1144행 goal·delta(`floor((goal − current) × equity ÷ reference)`) → 1153~1159행 regret_table·choose_step·step_quantity → 1198~1200행 `qty × reference < equity × 0.02` → DEADBAND. 설명('여유 × 근거 단계, 주 단위')과 다른 점: delta는 '0.10 − 3배 합'이 아니라 '통과한 가장 큰 목표 − 그 종목 현재 비중'이고, 주 단위 내림이 두 번(delta·qty) 있으며, 금액은 LOC 가격이 아니라 기준가(평가 세션 종가)로 잽니다. 이 입력은 TQQQ가 0이라 delta 금액 = 여유입니다.

## 7. D.i 새 시험 (test_policy_a.py TicketPathTests, auto_core_tickets.py는 부르기만)
- i-1 `test_i1_...`: 위 입력(실제 정책) → SOXL 매수 주문표 없음, blocked [DEADBAND], 코드 기준 금액 < 최소 금액, 여유 × 자산 ≥ 최소 금액, 0.10 초과 SOXL 목표는 모두 [LEVERAGED_3X_WEIGHT_CAP].
- i-2 `test_i2_...`: SOXL 1주 보유(여유가 넉넉한 입력) → 코드 기준 금액 ≥ 최소 금액, SOXL 매수 주문표 1장, 주문표 뒤 3배 합(현재 비중 + 수량 × 주문 가격 ÷ 자산) ≤ 0.10.
- i-3 `test_i3_...`: i-1 입력 + 상한 1.0 사본 → SOXL 매수 주문표 1장.
test_policy_a.py는 모두 19개입니다(a~h 16 + i 3). skip은 없습니다.

## 8. 바뀐 파일 sha256 (작업 트리 바이트)
| 파일 | sha256 | 줄바꿈 |
|---|---|---|
| stock-strategy-system/alert_policy.json | 96d076adeaa73a199b76534d47360a6cefcfd4ea3936df3aaf5c0922f88096b1 | CRLF |
| manage-us-stock-strategy/scripts/portfolio_exposure.py | e0b59e7cd238ba6e477f29c39e7113b94b172d4bafde2ffef165e745c4cb0b90 | CRLF |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 89d7cd8da31b291b9c57a3b6ee55c7b9131f7d1b57f9aedf203a86c2528533db | CRLF |
| manage-us-stock-strategy/tests/test_policy_a.py (새) | d377be71d6ffadece0e77046a7b3fc768cf33ede57f44f18fc06c23e32d31de6 | LF(새 파일, 1차 Builder 때부터 LF) |
| manage-us-stock-strategy/tests/test_qqq_registration.py | 8393018e73b333a09e5ba4c4d971ad2c49bfa04f742f9975948dfdbd4e619b5b | CRLF |
| manage-us-stock-strategy/tests/test_swing_k3_registration.py | af4db41063e3cdec5f48bd568a3722bab1dfe41683f6d426a8e4a4577e25458a | CRLF |
| manage-us-stock-strategy/tests/test_portfolio_exposure.py | 2878700d4b037e0bf734009c05ba0999cb406374feb9bb55e3c835e251683cc3 | CRLF |
| manage-us-stock-strategy/tests/test_portfolio_exposure_fail_closed.py | 30a376d9a6b25a2342f01c340448d56d3291d7684ec81af1668baca2e86f045c | CRLF |
| manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py | 3d2f40a4a8adcb8d7a75295be2f97457fc9bd4fa926de276efe31859b5582723 | CRLF |
| manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py | 5b488a3739a714ea6297d73a96dd0fc78beaf5987db786600823217a45e89c47 | CRLF |
| manage-us-stock-strategy/tests/test_auto_core_tickets.py | 08311c7121a864bcbff3ac1dec3f153eed4c870c0699a3422c1a03b4636e423e | CRLF |
| manage-us-stock-strategy/tests/test_auto_core_hold_range.py | 52916d61cb2016676baaf16f98300f3748a04ce84d9bf832bb1d838679f8f77b | CRLF |
| manage-us-stock-strategy/tests/test_auto_core_risk1r.py | b6301ad934e8c8f4fd2df48a7a8300eddcedfcebc927232d4c2b30c9f9b89a70 | CRLF |
| manage-us-stock-strategy/tests/test_auto_core_enter_window.py | f49917ca78cc3ca3911c7beacc0fc1ecdd5ae14881c2397dcb3fe0a16c6f3290 | CRLF |
| docs/claude/policy-a-BLOCKED.md | a9611cb67bb4add373bf3d022c21912bd2121779f12e777405d753c53cfdd38a | LF |

## 9. 확인 (Judge 항목 대조용)
- 3배 상한 막음이 매도·줄이기 권고·경고·fail-closed를 바꾸지 않음: cap_limit·cap_breaches·reduce_recommendations 무변경(코드), test_policy_a f(상한 1.0 사본과 band·single_stock_cap·fail_closed·pauses·exposure·reduce·warnings 같음), (ㄴ) 표.
- 상한이 걸리는 곳: S7 채우기(add_recommendations 1314행) · new_buy_within_band·swap_buy_leg(1709행) — 모두 projected_increase_reasons. hold_range가 _plan_buy를 다시 부를 때(auto_core_tickets.py 848·859행)도 같은 S7 proposal_results(best_target 710행)를 씀.
- 비중 분모(Judge 7): S7 비중 = 평가 세션 종가 × 확정 스냅숏 수량 ÷ (그 합 + 스냅숏 cash_usd)(portfolio_exposure.py 415~440·1411행). 코어 표시 비중 = 종가 × 보유 수량 ÷ (그 합 + equity_cash)(auto_core_tickets.py 161~185행). 둘 다 '종가 평가액 + 현금'이 분모이지만 현금·수량의 출처가 다릅니다: S7은 원장 스냅숏의 cash_usd·수량, 코어는 auto_core_decide.equity_cash(키움 주문 가능 현금 또는 가장 작은 스냅숏 현금)와 코어 보유 수량. 둘이 다른 날에는 같은 3배 합도 조금 다르게 보일 수 있습니다.
- 권한 표지 줄·주문 경로 문자열·schemas·auto_core_tickets.py(`POLICY_EXPECTED` 포함): 무변경. 새 줄에 권한 표지 글자 없음.

## 10. 연결표 원문 행 (고친 뒤)
portfolio_exposure.py exposure_config 163~231행(새 키 읽기 180~181행, 오류 148~160·229~231행) · add_default 검사 136~145·180행 · projected_increase_reasons 1282~1298행 · 채우기 후보 1540~1544행 · 제안 평가 1709행 · auto_core_decide.py 485~487행(UNEXPECTED_ERROR) · 1104~1113행 · auto_core_tickets.py 710~720행(best_target) · 754·811·859행(_plan_buy) · 1198~1200행(DEADBAND).

## 11. 병합 뒤 첫 07:45 코어에서 확인할 것
- decision status가 FAIL이 아니고 reasons에 UNEXPECTED_ERROR가 없음(정책 키가 틀리면 ExposureError → 코어 전체 FAIL).
- S7 파일이 생김.
- E ≤ 1.25인 날 S7 add에 SOXL이 없음(카드 ADD가 없으면 omitted에 NO_CARD_ADD_AND_ADD_DEFAULT_IS_CARD_ADD_STOCK_ONLY 1줄).

## 12. 남은 위험
- 관문 날 코어의 자동 매수 길은 카드 ADD 종목과 SOXL·TQQQ의 새 단서뿐입니다.
- 3배 여유가 작으면(예: 6.8%) 근거 단계 1/3 때문에 주문표 금액이 2% 아래로 내려가 DEADBAND가 됩니다(기존 규칙). 여유가 약 6%보다 작으면 r 1/3 새 단서 매수는 사실상 나오지 않습니다.
- 3배가 이미 10% 위면 3배 매수만 막히고 1배 매수는 그대로입니다. 줄이기는 사장이 직접 결정합니다.
- 2027-03-31에 3배 0을 고르면 정책 값만 바꾸는 K3입니다.
- 정책 키가 틀리면 코어 전체가 FAIL입니다(그날 매도 주문표도 없음).
- test_portfolio_exposure의 'V가 N보다 먼저 SOXL 채우기 목표를 줄인다' 단언은 새 정책에서 채우기가 없어 빠졌습니다.
- 골든 해시 4곳([5]~[8])은 이제 사본(옛 add_default)에서 옛 동작을 지킵니다. 새 정책 자체의 골든은 없습니다.

## 13. 하지 않은 것
커밋·push·병합·dev-run·dev-merge·dev-queue 없음. 주문·키움 호출·auto_core.py가 든 명령·reconcile apply·상태·일지·원장·예약·대시보드 쓰기 없음. 지시문·Judge 지시문·schemas·fixtures·공용 도우미·auto_core_tickets.py·.claude 설정·본 저장소 작업 트리는 손대지 않음. 비밀 읽지 않음. 실험 스크립트는 scratchpad에만 둠.
