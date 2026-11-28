---
id: policy-a-judge-report
date: 2026-11-26
status: "Judge 완료 — PASS (병합은 사장 결정). 본 저장소 경로 쓰기가 세션 훅으로 막혀 Judge worktree keen-borg-7d091b의 같은 경로에 씀"
source: "docs/claude/policy-a-judge-prompt.md (sha256 9543701efde9f1602e6224295a2f1e8f2f54a6c5584fb522546bcd52caa6322c, 6183바이트 — 본 저장소 작업 트리 바이트로 잼, 일치)"
---

# 정책 묶음 A(policy-a-1126) 독립 Judge 보고

- 검토 대상: Builder worktree E:\사업\##금동한\코덱스저장소\.claude\worktrees\unruffled-fermat-725de3 · 브랜치 worktree-policy-a · HEAD 9e48ef285e152ef156efdf86ade82d0fbdad9c14(기준 커밋과 같음) · 커밋하지 않은 변경 13개 파일 + 새 파일 3개(test_policy_a.py · policy-a-report.md · policy-a-BLOCKED.md).
- 지시문 docs/claude/policy-a-builder-prompt.md sha256 0f9f1cd0b94a9bba7226301828ab1ad12fdf5959cee4822f9090456f5b06d664(23552바이트) = Builder 보고 둘째 줄(본문 11행)과 같음.
- 바뀐 파일 15개의 작업 트리 바이트 sha256을 다시 재어 보고 8절 표와 모두 같음(policy-a-report.md 자체는 1b7e90084e4e0905846035b63d5fb26118edd49dbdb5656bf76298f8698da192).
- 읽은 것: Judge 지시문 · Builder 지시문 · Builder 보고 · policy-a-BLOCKED.md(1·2차) · 제안 policy-a-proposal-2026-11-26.md 2·3·6·9절 · CLAUDE.md Hard safety·Change classes · `git diff --ignore-cr-at-eol`(정책·scripts·tests 전부) · portfolio_exposure.py 126~231·1155~1330·1530~1570·1660~1720행 · auto_core_decide.py 475~491·1098~1252행 · auto_core_tickets.py 161~188·700~870·1124~1203행 · schemas/portfolio-exposure-review.schema.json(recommendations·policy).
- 하지 않은 것: Builder worktree·본 저장소 파일 수정 없음 · git은 status·diff·show·rev-parse·log만 · 주문·키움·auto_core.py가 든 명령·apply·상태·일지·원장·예약·대시보드 쓰기 없음 · 비밀 읽지 않음.

## 확인 항목

### 1. diff 파일·기존 테스트 고침 — 통과
- diff 파일 = 허용 파일뿐: alert_policy.json · portfolio_exposure.py · auto_core_decide.py · 기존 test_*.py 10개 · 새 test_policy_a.py · 보고 2개. auto_core_tickets.py · schemas/ · tests/s5_exposure_fixtures.py · tests/fixtures/** diff 없음(`git diff --stat`가 빈 결과).
- ① 7곳(보고 6절 표와 diff 하나씩 일치): test_qqq_registration.py:76 · test_swing_k3_registration.py:91 · test_portfolio_exposure.py 302~309·340~356·360~361 · test_portfolio_exposure_fail_closed.py 409~413 · test_run_portfolio_exposure_review.py 195~200. 옛 add_default 동작 시험이 남음(test_soxl_paused_by_peak_review… 사본 1줄, ③ 8곳 사본, test_policy_a b·c·g).
- ③ = 지시문의 8곳(파일::함수)뿐: [1] ProposalTests.test_new_buy_within_band… · [2] NewEvidenceTests.test_scenario_buy_circuit_closes_when_the_previous_session_is_unknown · [3] ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy · [4] FullPathTests.test_supplement_proposals_change_with_the_close · [5] HoldCauseTests.test_reverted_view_hashes_as_the_old_golden · [6] HoldOffTests.test_default_off_keeps_the_six_golden_keys · [7] UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before · [8] GoldenCauseTests.test_the_old_enter_window_gives_the_base_golden.
- 8곳 모두 (가): diff는 사본을 넣는 줄(import + enterContext 2줄, [1]은 scenario.policy 1줄)만 더했고 기대값 줄은 그대로. (나)는 없음 → 짝 시험 불필요. [2]·[3]·[4] 중 (가) 한 곳 이상 충족.
- 사본 넣는 법: test_policy_a.policy_file_copy — 실제 정책 바이트에서 `"max_weight_sum": 0.10`(과 add_default)만 바꾼 임시 파일 + mock.patch(helpers.POLICY_PATH, fx.POLICY_PATH). scripts에 주입 코드 없음.
- 원인이 add_default인 곳([5]~[8], [2]·[4]의 S7_ADD 갈래)은 ①로 적혔고 (가)로 고침(보고 6절 표).
- (ㄴ) 바뀐 칸 표(보고 6절): SOXL 제안·주문표, 채우기 권고·omitted·alerts, 상한 사유·DEADBAND, review_id·s7_review_id·decision_sha256(식별자·묶음 해시)뿐. 식별자가 가리키는 S7 차이도 허용 칸뿐이라고 적힘. 1배 주문표는 식별자 말고 종목·수량·가격·금액 같음. 결정 status 차이 없음. 정책 지문 칸을 빼고 비교한 곳은 없음(지문이 골든 해시 대상에 없다고 적힘).
- (ㄷ) 새 단서 3곳 수치 있음: 3배 합 0.032414 · 여유 0.067586($2,095.50) · 가장 큰 목표 0.100 · 근거 단계 1/3 · 주문표 금액 6주×$100.50=$603.00 · 최소 $620.10 → DEADBAND. 이 금액은 auto_core_tickets.py 1142~1144행(goal·delta) → 1153~1159행(choose_step·step_quantity) → 1198행(`qty × reference < equity × 0.02`)과 직접 대조해 같은 식임을 확인. 주문표 금액 ≥ 최소 금액인데 주문표가 없는 곳 없음.
- test_policy_a.py에 D.i i-1·i-2·i-3 있음(TicketPathTests).

### 2. 정책 파일 — 통과
- 바뀐 곳 2줄뿐: 750행 add_default `card_add_stock_else_SOXL` → `card_add_stock_only` · 771행 새 키 `leveraged_3x_weight_cap`(max_weight_sum 0.10, applies_to_nominal_multiplier_gte 3, applies_to, weight_basis, source).
- 문턱·reduce_order(끝 SOXL)·single_stock_nominal_cap 0.4·single_stock_cap_exempt·nominal_multipliers·allowed_index_etfs·권한 표지 줄 무변경. JSON 파싱 정상 · CRLF 933 / LF 933(LF 단독 0) · `git diff --stat`(CR 무시 안 함)도 3줄이라 줄바꿈 바뀜 없음.
- auto_core_tickets.py(POLICY_EXPECTED 포함)·schemas/ 무변경. S7 `policy` 칸을 만드는 부분에 diff 없음(diff 덩어리는 123·137·170·1226·1237·1481행대뿐).

### 3. 3배 상한이 '늘리는 3배 매수'만 막음 — 통과
- 막음은 projected_increase_reasons 1294~1295행 한 곳: `leveraged(symbol) and 3배 합 > cap`. 이 함수를 S7 채우기(add_recommendations 1314행)·new_buy_within_band·swap_buy_leg(_evaluate_proposal 1709행)가 함께 씀.
- 반례 찾기: (a) 3배 0.12인 날 1배 매수 — leveraged(symbol)가 거짓이라 사유 안 붙음(test_policy_a e도 DELL·NBIS·MU·QQQ·MVLL로 확인). (b) 줄이기 권고·매도 주문표 새로 생김 — cap_limit·cap_breaches·reduce_recommendations(1161~1237행) 무변경, 상한은 그쪽에 들어가지 않음(test_policy_a f). (c) hold_range 우회 — hold_eval(auto_core_decide.py 1221~1248행)은 S7의 proposal_results를 그대로 두고, _hold_ticket(auto_core_tickets.py 853·859행)이 _plan_buy → _buy_ticket → best_target(1128행)으로 같은 S7 평가를 거침. 우회 없음.

### 4. 채우기·줄이기 분리 — 통과
- scripts 전체 grep(`reduce_order[-1]`·`["supplement"]`·`add_default`): 채우기 뜻은 add_supplement_instrument(portfolio_exposure.py 134~145행)를 거치는 곳뿐(180·213·1542행, auto_core_decide.py 1109~1113행). 줄이기 뜻 supplement를 읽는 세 곳(portfolio_exposure.py 1207행 · run_portfolio_exposure_review.py 527행 · 코어 본체 스크립트 163행)은 diff 없음.
- auto_core_decide.py: basis_met 갈래는 add_supplement가 None이면 없음, new_basis_met 갈래 그대로(test_policy_a g 세 개).

### 5. 옛 add_default면 뒤로 맞음 — 통과
- 옛 값 → add_supplement = SOXL(test_policy_a b·c·g). ③ 8곳이 상한 1.0 + 옛 add_default 사본에서 옛 기대값·옛 골든 해시 글자 그대로 통과(아래 8번 재실행 포함).

### 6. 새 키 없거나 틀리면 ExposureError → 코어 FAIL — 통과
- leveraged_cap_config(148~160행)·add_supplement_instrument가 ExposureError를 냄(기본값 없음). exposure_config는 auto_core_decide.py 315행에서도 불리고 add_supplement_instrument는 1109행에서 불려, 오류는 485~487행 `UNEXPECTED_ERROR` FAIL로 끝남. 보고 11·12절이 이 점을 적음.

### 7. 비중 분모 — 통과(차이가 보고에 적힘)
- S7: closing_equity(portfolio_exposure.py 412~439행) = 원장 스냅숏 수량 × 평가 종가 + 스냅숏 cash_usd. 코어 표시: rule_file_nominal(auto_core_tickets.py 161~185행) = 코어 보유 수량 × 종가 + equity_cash(키움 주문 가능 현금 또는 가장 작은 스냅숏 현금). 같은 꼴이지만 현금·수량 출처가 다름 — 보고 9절이 적음.

### 8. 테스트 — 통과 (Judge가 직접 다시 돌림, python 3.15.2, tzdata 정상, Builder worktree에서 지시문 글자 그대로)
| 패턴 | 결과 |
|---|---|
| test_policy_a.py | Ran 19 OK(skip 0) |
| test_portfolio_exposure*.py | Ran 154 OK |
| test_run_portfolio_exposure_review*.py | Ran 29 OK |
| test_auto_core* | Ran 667, 실패 1(test_auto_core_decide RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches = BLOCKED.md 35행 기준선), skip 1(기준선과 같음) |
| test_qqq_registration.py | Ran 8 OK |
| test_swing_k3_registration.py | Ran 8 OK |
| validate_schema_contracts.py | PASS |

기준선 밖 새 실패 0. 전체(-p "test_*.py")는 Judge가 다시 돌리지 않았음 — Builder 보고 5절의 3993개·실패 4(기준선 4와 같음)를 따름.

### 9. 권한 표지·주문 경로 — 통과
- 정책·scripts의 추가 73줄에 권한 표지 글자(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling)와 주문 경로 문자열 4종 없음. test_policy_a.py에는 값을 읽어 비교하는 권한 키 이름만 있고 주문 경로 문자열 없음.
- 상태·일지·원장·예약·대시보드 쓰기 코드 없음(diff 대조).

### 10. 연결표 원문 행 — 통과(행 밀림 지적)
지시문·제안 연결표 ②③⑤의 portfolio_exposure.py 행은 고친 뒤 밀렸음. 새 행:

| 연결표 행(기준 9e48ef2) | 고친 뒤 |
|---|---|
| 126~188 exposure_config | 163~231 |
| 139~141 add_default 검사 | 134~145(add_supplement_instrument) · 176~181 |
| 185~188 ExposureError | 227~230 |
| 1229~1242 projected_increase_reasons | 1282~1298 |
| 1245 add_recommendations(호출 1258) | 1301(호출 1314) |
| 1609 _evaluate_proposal(호출 1649) | 1669(호출 1709) |
| 1483~1484 채우기 후보 | 1540~1544 |
| auto_core_decide.py 1105~1107 | 1100~1113 |
| auto_core_decide.py 485~487 · auto_core_tickets.py 710~720·789·817 | 그대로 |

⑤ '알림 경로 확인 필요'는 지시문 연결표 73행에 끊김으로 적혀 있고 막는 장치(병합 스크립트가 커밋 전 새 시험 실행)도 적혀 있음.

## FAIL은 아니지만 알릴 점
1. test_portfolio_exposure.py test_projected_exposure_above_target_omits_the_add(① 목록의 342~356행)는 앞부분 기대 사유에 LEVERAGED_3X_WEIGHT_CAP가 더해졌음 — 3배 상한 때문에 바뀐 기대값이지만 지시문 ①이 이 행을 '새 정책 기대값으로 바꾸기' 대상으로 명시해 허용으로 봄. 그 대가로 'V가 N보다 먼저 채우기 목표를 줄인다' 단언이 이 함수에서 빠짐(Builder도 12절에 적음). 다른 시험에 같은 단언이 있는지는 확인하지 않음.
2. swap_buy_leg 매수 다리는 팔 다리를 빼지 않은 확정 비중으로 셈(기존 R9 규칙, 1689~1691행). 그래서 SOXL을 팔고 TQQQ를 사는 바꿔 사기는 3배 합이 늘지 않아도 막힐 수 있음 — 보수 쪽이며 기존 규칙 그대로.
3. 상한은 S7 종가 비중으로 판정하고 주문표는 LOC 가격(종가보다 높을 수 있음)으로 나옴. i-2는 주문 가격 기준으로도 ≤ 0.10임을 확인했지만, 걸음 1/1 같은 큰 주문표에서는 주문 가격 기준 비중이 0.10을 아주 조금 넘을 수 있음(체결 뒤 종가 평가는 상한 안). 판정 기준(평가 비중)은 지시문대로.
4. 이번 재개 때 기준선을 다시 재지 않고 1차 Builder 기준선을 씀(보고 5절이 밝힘). 기준 커밋이 같아 받아들임.
5. 골든 해시 4곳([5]~[8])은 이제 옛 정책 사본으로만 지켜지고, 새 정책 자체의 골든은 없음(Builder 12절).
6. 이 보고는 본 저장소 docs/claude/에 쓰려 했으나 세션 훅이 막아 Judge worktree(keen-borg-7d091b, 브랜치 claude/keen-borg-7d091b)의 같은 경로에 썼음. 병합 스크립트나 문서 커밋에 넣으려면 이 파일을 본 저장소로 옮겨야 함.

## 병합 뒤 확인(Builder 11절과 같음)
첫 07:45 코어에서 decision status가 FAIL이 아니고 reasons에 UNEXPECTED_ERROR가 없음 · S7 파일이 생김 · E ≤ 1.25인 날 S7 add에 SOXL이 없음(카드 ADD가 없으면 omitted에 NO_CARD_ADD_AND_ADD_DEFAULT_IS_CARD_ADD_STOCK_ONLY 1줄).

VERDICT: PASS
