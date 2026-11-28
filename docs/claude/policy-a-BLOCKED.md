---
id: policy-a-BLOCKED
date: 2026-11-26
status: BLOCKED (Builder stopped at the test step)
source: docs/claude/policy-a-builder-prompt.md (sha256 5b6b0ece8ea3e0136d7a8967a67d9256e5368a0d1ce5e8f827ea38e40e5e43d3), 'test' section line 52
---

# 정책 묶음 A Builder — 멈춤 (BLOCKED)

## 한 줄
정책·코드·새 시험은 지시대로 다 넣었고 새 시험 16개는 모두 통과합니다. 하지만 3배 상한 때문에 기존 테스트 8개가 새로 실패하고, 이 8개는 지시문이 고치라고 허락한 두 종류(① SOXL 채우기 기대, ② 손으로 만든 정책 fixture)에 들지 않습니다. 지시문 52행("그 밖의 기존 테스트를 고쳐야 통과하면 멈추고 BLOCKED")에 따라 멈췄습니다. 기존 테스트는 하나도 고치지 않았습니다.

## worktree
- 경로: E:\사업\##금동한\코덱스저장소\.claude\worktrees\unruffled-fermat-725de3
- 브랜치: worktree-policy-a · 기준 커밋: 9e48ef285e152ef156efdf86ade82d0fbdad9c14 (본 저장소 codex/master-recovery-expansion HEAD, 시작 때 확인)
- 커밋·push 없음. 바뀐 파일은 커밋하지 않은 채로 남겨 두었습니다.

## 지금 worktree에 있는 변경 (작업 트리 바이트 sha256)
| 파일 | sha256 | 내용 |
|---|---|---|
| stock-strategy-system/alert_policy.json | 96d076adeaa73a199b76534d47360a6cefcfd4ea3936df3aaf5c0922f88096b1 | 750행 add_default `card_add_stock_else_SOXL` → `card_add_stock_only`. 771행에 새 키 `leveraged_3x_weight_cap` {max_weight_sum 0.10, applies_to_nominal_multiplier_gte 3, applies_to exposure_increasing_buy_of_member_only, weight_basis s7_closing_value_over_closing_equity, source "strategy-1101 / policy-a-1126"}. CRLF 유지(933 CRLF, LF 0) |
| manage-us-stock-strategy/scripts/portfolio_exposure.py | e0b59e7cd238ba6e477f29c39e7113b94b172d4bafde2ffef165e745c4cb0b90 | 126~161행: 새 함수 add_supplement_instrument(옛 값이면 SOXL, 새 값이면 None, 그 밖이면 ExposureError)와 leveraged_cap_config(없거나 형식이 틀리면 ExposureError). exposure_config 177~181·213~214행: 새 칸 add_supplement·leveraged_cap·leveraged_bound를 넣고 supplement 칸은 그대로 둠. 1271~1281행: leveraged()·leveraged_weight_sum(). 1284~1295행: projected_increase_reasons는 늘리는 종목의 배수가 3 이상일 때만 LEVERAGED_3X_WEIGHT_CAP를 붙임. 1540~1544행: 채우기 후보 = 카드 ADD, 그다음 add_supplement(None이면 후보 없음 + omitted {symbol null, reasons [NO_CARD_ADD_AND_ADD_DEFAULT_IS_CARD_ADD_STOCK_ONLY]}). cap_limit·cap_breaches·reduce·S7 `policy` 칸은 그대로. ASCII, CRLF |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 89d7cd8da31b291b9c57a3b6ee55c7b9131f7d1b57f9aedf203a86c2528533db | 1101~1114행: `reduce_order[-1]` 대신 add_supplement_instrument(정책)를 씀. None이면 basis_met 갈래 없음, new_basis_met 갈래는 그대로. ASCII, CRLF |
| manage-us-stock-strategy/tests/test_policy_a.py (새 파일) | 0d8610a024822cca68b6d38c781a95cff535b3fa406088b5daf9592842f32205 | 지시문 D절 a~h. 16개 시험 모두 통과(skip 0) |

`git diff --ignore-cr-at-eol --stat`: 3 files changed, 73 insertions(+), 6 deletions(-) (새 시험 파일은 추적 안 됨).
reduce_order[-1]·supplement grep(scripts 전체): 채우기 뜻으로 쓰던 곳은 auto_core_decide.py 1107행(고침)과 portfolio_exposure.py 140·1484행(고침)뿐. supplement를 줄이기 뜻으로 읽는 곳(portfolio_exposure.py 1165행 → 지금 1208행 부근, run_portfolio_exposure_review.py 527행, 코어 본체 163행)은 그대로. auto_core_tickets.py에는 reduce_order·supplement·add_default가 없습니다.

## 테스트 (python 3.15.2, PATH의 python, tzdata 정상)
| 대상 | 바꾸기 전 | 바꾼 뒤 |
|---|---|---|
| test_policy_a.py | Ran 0 | Ran 16 OK |
| test_portfolio_exposure*.py | Ran 154 OK | Ran 154, 실패 4·오류 1 |
| test_run_portfolio_exposure_review*.py | Ran 29 OK | Ran 29, 실패 1 |
| test_auto_core* | Ran 667, 실패 1(기준선: test_auto_core_decide RegistryTests, SOXL trim_target_weight), skip 1 | Ran 667, 실패 8(기준선 1 + 새 7), skip 1 |
| test_qqq_registration.py | Ran 8 OK | 실패 1 |
| test_swing_k3_registration.py | Ran 8 OK | 실패 1 |
| validate_schema_contracts.py | PASS | (바꾼 뒤 아직 안 돌림 — 멈춤) |
| 전체 test_*.py | Ran 3974, 실패 4(registry, dev_pipeline_api_route, llm_pilot_pdfcmp, scheduler_control_plane), skip 3 | 멈춰서 안 돌림 |

### 허락된 종류 ① 안에 드는 새 실패 (지시문이 고치라고 한 곳 — 아직 고치지 않음)
- test_portfolio_exposure.py 302~312(test_default_add_is_soxl_up_to_the_target), 342~350(test_projected_exposure_above_target_omits_the_add 앞부분), 358~373(test_soxl_paused_by_peak_review_omits_the_add_without_substitute — 지시문 목록 밖이지만 실제 정책 + SOXL 채우기 기대라 ①)
- test_portfolio_exposure_fail_closed.py 409 · test_run_portfolio_exposure_review.py 195 · test_qqq_registration.py 76 · test_swing_k3_registration.py 91

### 허락된 두 종류 밖의 새 실패 (멈춘 이유)
3배 상한이 '새 단서' SOXL·TQQQ 매수와 줄이기·보유 골든 해시에 닿아 생긴 것입니다. SOXL 채우기 기대도 아니고 손으로 만든 정책 fixture도 아닙니다.
1. test_portfolio_exposure.py 479 ProposalTests.test_new_buy_within_band_is_shown_only_when_projected_exposure_and_cap_hold — SOXL 0.45를 들고 TQQQ 0.05 제안 → 사유가 [PROJECTED_EXPOSURE_ABOVE_TARGET]에서 [..., LEVERAGED_3X_WEIGHT_CAP]로 바뀜(상한이 맞게 동작함).
2. test_auto_core_t2rc_corefix.py 195 — 새 단서 SOXL 매수 주문표 1장 기대 → 상한 때문에 목표가 줄어 DEADBAND(금액 < 자산 2%, auto_core_tickets.py 1198행)로 주문표 0장. (지시문에 적힌 210~212행이 아니라 같은 시험의 앞부분 195행)
3. test_auto_core_tickets.py 645 ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy — 같은 원인(DEADBAND). (지시문에 적힌 806행이 아님)
4. test_auto_core_hold_range.py 334 FullPathTests.test_supplement_proposals_change_with_the_close — 같은 원인(DEADBAND).
5. test_auto_core_hold_range.py 753 HoldCauseTests.test_reverted_view_hashes_as_the_old_golden — 골든 해시(OLD_DECIDE_GOLDEN) 바뀜.
6. test_auto_core_hold_range.py 558 HoldOffTests.test_default_off_keeps_the_six_golden_keys — 골든 해시(risk1r.GOLDEN) 바뀜.
7. test_auto_core_risk1r.py 208 UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before — 골든 해시 GOLDEN 8개 중 여러 개 바뀜.
8. test_auto_core_enter_window.py 216 GoldenCauseTests.test_the_old_enter_window_gives_the_base_golden — 골든 해시(BASE_GOLDEN) 바뀜.
(2~8 = test_auto_core*의 새 실패 7개, 기준선 실패 test_auto_core_decide RegistryTests는 뺌. 1번까지 더하면 범위 밖 8개)

## 풀려면 (사장·코디네이터 결정 — Builder가 정하지 않음)
- 안 A(권장): 지시문 '테스트' 절에 ③을 더한다 — "3배 상한 때문에 기대값이 바뀌는 기존 테스트(위 1~8): 상한 키를 1.0으로 덮어쓴 real_policy 사본으로 옛 기대를 계속 시험하거나, 새 기대값(사유 추가·DEADBAND·골든 해시 재계산)으로 바꾸고 이유를 표에 적는다". 골든 해시 재계산은 어떤 출력 칸이 왜 바뀌었는지를 보고에 적는 조건. 고친 지시문의 새 sha256으로 같은 worktree에서 이어 하면 됩니다.
- 안 B: 범위를 줄인다(예: 3배 상한을 S7 채우기에만 걸고 새 단서 제안에는 걸지 않음) — 지시문 목표 1번과 Judge 확인 3번이 바뀌므로 제안서부터 다시.
- 안 C: 이번 변경을 버린다 — worktree의 변경을 지우면 끝(본 저장소는 안 바뀜).

## 하지 않은 것
커밋·push·병합·dev-run·dev-merge·dev-queue 없음. 기존 테스트 파일·fixtures·schemas·auto_core_tickets.py·본 저장소 작업 트리·.claude 설정은 손대지 않았습니다. 주문·키움·auto_core.py 명령·apply·상태·일지·원장·예약·대시보드 쓰기 없음. 비밀은 읽지 않았습니다.

---

# 2차 멈춤 — 보완 1로 재개한 뒤 (2026-11-26 KST, 덧붙임)

- 지시문: docs/claude/policy-a-builder-prompt.md sha256 7ddee587edc74ff3f678c38b1084a1b6082476d3b170e66740ae5ee42620e869 (21059바이트, 본 저장소 작업 트리에서 잼) · BLOCKED 1회 뒤 보완 1로 재개
- 같은 worktree·브랜치(worktree-policy-a, 기준 9e48ef2). 시작 때 바뀐 파일 4개 sha256이 위 표와 같음을 확인.

## 한 줄
① 7곳은 고쳤고 ③ 8곳 모두 (ㄱ) 원인 확인은 통과했지만, 새 단서 SOXL 3곳([2]·[3]·[4])이 (ㄷ) 멈춤 조건 "여유가 최소 금액 이상인데 주문표가 없으면 멈춘다"에 걸립니다. 여유는 $2,095.50(자산 6.76%)로 최소 금액 $620.10(2%)보다 크지만, 주문표 크기는 '여유 전체'가 아니라 '여유 × 근거 단계(r 1/3)'라서 6주 × $100.50 = $603.00 < $620.10 → DEADBAND로 주문표가 없습니다. 지시문 (ㅁ)에 따라 ③은 하나도 고치지 않고 멈췄습니다. 같은 가정이 D.i (i-2) "여유 ≥ 최소 금액 → 주문표가 나온다"에도 들어 있어 D.i도 쓰지 않았습니다.

## 이번에 한 것 (① 7곳 — 지시문이 허락한 종류)
| 파일:행(고친 뒤) | 종류 | 고친 법 | 앞 → 뒤 |
|---|---|---|---|
| test_qqq_registration.py:76 | ① | 새 정책 기대값 | add_default `card_add_stock_else_SOXL` → `card_add_stock_only` (값 고정 시험이라 새 값) |
| test_swing_k3_registration.py:91 | ① | 새 정책 기대값 | 같음 |
| test_portfolio_exposure.py:302~309 test_default_add_is_soxl_up_to_the_target | ① | 새 정책 기대값 | SOXL 0.516 채우기 → add [] · omitted [{add, null, NO_CARD_ADD_AND_ADD_DEFAULT_IS_CARD_ADD_STOCK_ONLY}] · S5_ADD_RECOMMENDATION 알림 없음. (옛 add_default만 덮어쓰면 SOXL 0.30이 이미 3배 상한 위라 0.516이 안 나옴 → 새 기대값을 고름) |
| test_portfolio_exposure.py:340~356 test_projected_exposure_above_target_omits_the_add | ① | 새 정책 기대값 | 앞부분(add_recommendations 직접 호출, SOXL 0.516): 사유 [PROJECTED_EXPOSURE_ABOVE_TARGET] → [..., LEVERAGED_3X_WEIGHT_CAP] · 뒷부분(V가 목표를 줄이는 SOXL 채우기): add[0] 검사 → add [] + NO_DEFAULT omitted. 남는 위험: 'V가 N보다 먼저 목표를 줄인다' 시험이 이 함수에서 빠짐 |
| test_portfolio_exposure.py:358~361 test_soxl_paused_by_peak_review_omits_the_add_without_substitute | ① | 사본의 add_default만 옛 값 | 줄 1개 더함(scenario.policy add_default = 옛 값). 기대값 줄 그대로 — 옛 동작 시험이 남는 곳 |
| test_portfolio_exposure_fail_closed.py:409~413 | ① | 새 정책 기대값 | `assertTrue(add)` → add [] + NO_DEFAULT omitted 1줄 |
| test_run_portfolio_exposure_review.py:195~199 | ① | 새 정책 기대값 | add 종목 ["SOXL"] → [] · "채우기 권고 1건(...)" 출력 → "채우기 권고" 없음 (러너가 실제 정책 파일을 읽어 사본을 넣을 수 없음) |
지시문 목록의 test_auto_core_t2rc_corefix.py 210~212행은 [2]와 같은 함수라 ③으로 처리할 곳, test_auto_core_tickets.py 806행은 지금 실패하지 않아 고칠 것 없음.

## ③ 8곳 (ㄱ) 원인 확인 — 모두 통과
방법: 시험 밖 실험 스크립트(scratchpad, worktree에 넣지 않음)에서 실제 정책 파일 바이트의 `"max_weight_sum": 0.10`만 `1.0`으로(①에도 걸리는 곳은 add_default도 옛 값으로) 바꾼 임시 파일을 만들고 mock.patch로 helpers.POLICY_PATH·fx.POLICY_PATH만 바꿔 8개 시험을 그대로 돌림. scripts는 손대지 않음.
| 곳 | 상한 1.0만 | 상한 1.0 + 옛 add_default |
|---|---|---|
| [1] test_portfolio_exposure ProposalTests…cap_hold | 통과 | (불필요) |
| [2] test_auto_core_t2rc_corefix NewEvidenceTests.test_scenario_buy_circuit_closes_when_the_previous_session_is_unknown | 195행 통과, 212행 실패(① S7_ADD 갈래) | 통과 |
| [3] test_auto_core_tickets ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy | 통과 | (불필요) |
| [4] test_auto_core_hold_range FullPathTests.test_supplement_proposals_change_with_the_close | 실패(hold lo 100.1 CIRCUIT_CLOSED — basis_met 갈래) | 통과 |
| [5] hold_range HoldCauseTests.test_reverted_view_hashes_as_the_old_golden | 실패 | 통과(옛 해시 글자 그대로) |
| [6] hold_range HoldOffTests.test_default_off_keeps_the_six_golden_keys | 실패 | 통과(글자 그대로) |
| [7] risk1r UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before | 실패 | 통과(글자 그대로) |
| [8] enter_window GoldenCauseTests.test_the_old_enter_window_gives_the_base_golden | 실패 | 통과(글자 그대로) |
정책 지문(alert_policy sha256)은 골든 해시 대상에 들어 있지 않아 지문 칸 제외가 필요 없었음.

## (ㄴ) 바뀐 칸 (실제 정책 산출 ↔ 사본 산출, 임시 경로 `inputs.*.path` 칸은 매 실행 다르므로 뺌)
- [1]: recommendations.proposals[2].reasons (TQQQ 0.05) [PROJECTED…, LEVERAGED_3X_WEIGHT_CAP] ↔ [PROJECTED…] · review_id(리뷰 내용 해시).
- [3] (상한 1.0만): with_record.planned.tickets — 실제 [MU 매수] ↔ 사본 [MU 매수, SOXL 매수 49주 $4,929.40] · planned.blocked [SOXL 매수 DEADBAND] ↔ [] · S7 제안 SOXL 격자(0.001~) 칸의 status·reasons·legs(0.10 초과 목표에 LEVERAGED_3X_WEIGHT_CAP) · proposal_results 같은 칸 · review_id · **MU(1배) 매수 주문표의 inputs.s7_review_id**(qty·가격·금액·게이트 등 다른 칸은 같음). no_action·결정 status 같음.
- [2] (상한 1.0 + 옛 add_default): opened = [3]과 같은 모양 + review.recommendations.add(SOXL 채우기)·omitted(NO_DEFAULT)·alerts(S5_ADD_RECOMMENDATION). shut = SOXL 'S7_ADD_RECOMMENDATION' 매수 후보·주문표 있고 없음, basis_met 갈래 SOXL 제안 격자 있고 없음(proposal_results·proposals 길이), 같은 add/omitted/alerts, review_id. 상한 1.0만 사본과의 차이는 [3]과 같은 모양.
- [4]: [2] opened와 같은 모양.
- [5]~[8] (6개 시나리오 + decide compare/apply): **상한 1.0만 사본과는 정책 지문(inputs.alert_policy.sha256)·임시 경로 말고 다른 칸이 없음 — 3배 상한은 이 4곳의 원인이 아님.** 원인은 add_default(①): 사본(옛 add_default)에서 default·g2b·pwr·research_block 시나리오의 review.recommendations.add(SOXL 채우기)·omitted·alerts·review_id가 달라지고, 그 review_id가 MU·PWR(1배) 매수 주문표의 inputs.s7_review_id와 decide의 inputs.s7_review.review_id·journal.decision_sha256로 옮겨 골든 해시가 바뀜. sell 시나리오·매도 주문표·줄이기 권고·결정 status는 같음.
- 판단을 맡길 점: 1배 주문표의 `inputs.s7_review_id`(S7 리뷰 전체의 내용 해시를 가리키는 칸)가 다릅니다. 수량·가격·금액·게이트 같은 판정 칸은 같지만, 지시문 (ㄴ) "1배 종목 칸이 다르면 멈춘다"를 글자대로 읽으면 이것도 걸립니다. 저는 '딸린 식별자'로 보았지만 결정은 맡깁니다.

## (ㄷ) 새 단서 SOXL 3곳 수치 — 멈춘 이유 ([2] opened·[3] with_record·[4]는 같은 입력이라 같은 값)
| 칸 | 실제 정책(상한 0.10) | 상한 1.0 사본 |
|---|---|---|
| 자산(S7 평가) | $31,005.00 | 같음 |
| 3배 비중 합(SOXL 0.032414 + TQQQ 0) | 0.032414 | 같음 |
| 여유 0.10 − 합 | 0.067586 = $2,095.50 | (같음) |
| 통과한 가장 큰 목표 | 0.100 (0.101 이상은 LEVERAGED_3X_WEIGHT_CAP) | 0.516 |
| 목표까지 주식 수(delta) · 금액 | 20주 · $2,095.50 | 149주 · $14,993.58 |
| 근거 단계(r_max → 고른 단계) | 1/3 → 1/3 (WITHIN_REGRET_BUDGET) | 같음 |
| 매수 금액 | floor(20 × 1/3) = 6주 × $100.50 = $603.00 | 49주 → $4,929.40 |
| 최소 금액(자산 2%) | $620.10 | $620.10 |
| 결과 | 주문표 없음 — DEADBAND (auto_core_tickets.py 1198~1200행) | SOXL 매수 주문표 1장 |
→ 여유($2,095.50) ≥ 최소 금액($620.10)인데 주문표가 없음 = 지시문 (ㄷ) 멈춤 조건. 원인은 코드 오류가 아니라 주문표 크기가 '여유 × r 단계'라는 기존 규칙(auto_core_tickets.py 1143~1159행 goal·delta·choose_step·step_quantity)입니다. 3배 상한 자체는 뜻대로 걸렸습니다(0.101 이상 목표에 사유).

## 지금 worktree 상태
- 정책·코드·test_policy_a.py: 위 1차 표와 같은 sha256(바꾸지 않음).
- ① 고친 기존 시험 5개 파일 sha256(작업 트리 바이트, 모두 CRLF 유지): test_qqq_registration.py 8393018e73b333a09e5ba4c4d971ad2c49bfa04f742f9975948dfdbd4e619b5b · test_swing_k3_registration.py af4db41063e3cdec5f48bd568a3722bab1dfe41683f6d426a8e4a4577e25458a · test_portfolio_exposure.py a4719ecdf2b5c39ab7b5327bdf999cecb5240ebbcf30ccaf8aeeec8873a741ff · test_portfolio_exposure_fail_closed.py 30a376d9a6b25a2342f01c340448d56d3291d7684ec81af1668baca2e86f045c · test_run_portfolio_exposure_review.py 3d2f40a4a8adcb8d7a75295be2f97457fc9bd4fa926de276efe31859b5582723
- ③ 8곳·D.i·policy-a-report.md: 쓰지 않음.
- 시험(python 3.15.2): test_policy_a.py Ran 16 OK · test_portfolio_exposure*.py Ran 154 실패 1([1]) · test_run_portfolio_exposure_review*.py Ran 29 OK · test_qqq_registration.py Ran 8 OK · test_swing_k3_registration.py Ran 8 OK · test_auto_core* Ran 667 실패 8(기준선 1 RegistryTests + ③ 7) skip 1 · validate_schema_contracts.py PASS · 전체 test_*.py는 멈춰서 안 돌림.
- `git diff --ignore-cr-at-eol --stat`: 8 files changed, 98 insertions(+), 24 deletions(-) (test_policy_a.py·이 파일은 추적 안 됨).

## 풀려면 (사장·코디네이터 결정)
- 안 A(권장): 지시문 (ㄷ)과 D.i의 기준을 '여유'에서 '주문표 금액 = floor(floor(여유×자산÷기준가) × r 단계) × 기준가'로 바꾼다(=기존 DEADBAND 규칙 그대로). 그러면 [2]·[3]·[4]는 "금액 $603.00 < $620.10 → DEADBAND"로 조건 안에 들고, (가) 사본 1줄로 고칠 수 있습니다. 같이 정할 것: 1배 주문표 inputs.s7_review_id 차이를 '딸린 식별자'로 허용할지. [5]~[8]은 원인이 3배 상한이 아니라 add_default(①)임을 보고에 적는 조건.
- 안 B: 3배 상한 여유가 최소 금액 이상이면 r 단계와 상관없이 주문표를 내도록 코드를 바꾼다 — auto_core_tickets.py(허용 파일 밖)와 K3-2 데드밴드 규칙에 닿으므로 제안서부터 다시.
- 안 C: 이번 변경을 버린다(worktree 변경 삭제, 본 저장소는 안 바뀜).

## 이번에도 하지 않은 것
커밋·push·병합·dev-run·dev-merge·dev-queue 없음. scripts·정책·schemas·fixtures·공용 도우미·auto_core_tickets.py·지시문·Judge 지시문·.claude 설정·본 저장소 작업 트리는 손대지 않았습니다. 실험 스크립트는 scratchpad에만 두었습니다. 주문·키움·auto_core.py 명령·apply·상태·일지·원장·예약·대시보드 쓰기 없음. 비밀은 읽지 않았습니다. 참고: 이 세션은 처음 다른 worktree(priceless-satoshi-173dca)에서 열려 쓰기가 막혀, 지시대로 이 worktree로 들어와(새 worktree·브랜치 만들지 않음) 작업했습니다.
