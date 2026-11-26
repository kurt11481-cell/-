---
id: policy-a-builder-prompt
title: "정책 묶음 A — 3배 상한(3배를 늘리는 매수만) + 채우기 기본 '카드 ADD 종목만' — 수동 경로 Builder 지시문"
date: 2026-11-26
status: "승인됨 — 2026-11-26(KST) 안에 착수. 수동 경로(정책 파일은 개발 큐 보호 경로 — tools/dev_pipeline/authority-paths.txt 8~9행, 선례 qqq-reg·swing-k3)"
class: "authority(K3 — 노출 한도·채우기 상품·정책). Builder Opus(worktree, 브랜치 worktree-policy-a) → 별도 읽기 전용 Judge(Opus, docs/claude/policy-a-judge-prompt.md) → 병합은 사장 결정 + 사장 PowerShell 병합 스크립트 docs/claude/policy-a-merge-<날짜>.ps1"
allowed_files: "stock-strategy-system/alert_policy.json · manage-us-stock-strategy/scripts/portfolio_exposure.py · manage-us-stock-strategy/scripts/auto_core_decide.py · manage-us-stock-strategy/tests/test_policy_a.py(새로) · 기존 테스트 파일(test_*.py)은 아래 '테스트' 절의 세 종류 고침만 · docs/claude/policy-a-report.md · docs/claude/policy-a-BLOCKED.md(멈춘 기록 — 보완 1 뒤에도 남김, 다시 멈추면 덧붙임)"
source: "사장 결정 카드 2026-11-26 22:28:38 KST '안1 착수 (권장)'(cmsg_0137MRzn9nuDvvQmVxm6WeX974dyb4vV33MkVCvzBsrPNp, 누른 계정 = 사장) · 제안 docs/claude/policy-a-proposal-2026-11-26.md 3절 안 1·9절 · strategy-revision-2026-11-01.md 9절 3행 · active-decisions.md policy-a-1126·strategy-1101·strategy-check-1105·policy-a-first-1126 행"
authority: "주문 권한 없음 · 수량 권한 값 변경 없음 · 키움 호출 없음 · 상태·일지·원장·예약 쓰기 없음"
amendment: "보완 1(2026-11-26 KST): Builder BLOCKED(기존 테스트 8곳 — 3배 상한이 뜻대로 걸려 기대값이 바뀜) 뒤 '테스트' 절 ③·D.i·allowed_files·Judge 1번을 고침. 범위(안 1)·허용 코드 파일·정책 값 변경 없음 · 보완 2(같은 날): BLOCKED 2회 뒤 (ㄷ)·D.i 기준을 '여유'에서 기존 규칙의 '주문표 금액(여유 × 근거 단계 비율, 주 단위)'으로 바꾸고 (ㄴ)에 채우기 권고·omitted·S7 식별자 칸을 허용"
weekly_user_touch: "1 (병합: 사장 PowerShell로 병합 스크립트 1번)"
---

## 시작
- 자기 worktree에서 `git switch -C worktree-policy-a <기준>`. 기준 = 시작 때 본 저장소 브랜치 codex/master-recovery-expansion의 HEAD(2026-11-26 22시대 9e48ef2 — 그 뒤 docs/claude만 바뀐 커밋이면 그 HEAD). 보고 첫 줄에 worktree 경로·브랜치·기준 커밋을 적는다.
- 먼저 읽는다: CLAUDE.md(Hard safety·Change classes·Working rules), 제안 docs/claude/policy-a-proposal-2026-11-26.md 2·3절, 이 지시문.
- (보완으로 이어 갈 때) 새 worktree·새 브랜치를 만들지 않고 같은 worktree에서 이어 간다. 이미 넣은 정책·코드·test_policy_a.py는 그대로 두고 ③·D.i만 더 한다. 보고 첫 줄 다음 줄에 이 지시문 sha256과 'BLOCKED 2회 뒤 보완 2로 재개'를 적는다.

## 목표
사장이 고른 범위(안 1)대로, 이미 정한 '3배 상품 ≤ 계좌의 10%'(strategy-1101·strategy-check-1105)를 자동 코어가 어기지 않게 한다.
1. 3배 상품(정책 배수 3 이상)을 **늘리는** 매수는 투영 뒤 3배 상품 비중 합이 0.10을 넘으면 막는다.
2. 채우기 기본을 SOXL에서 '카드 ADD 종목만(없으면 채우기 권고 없음)'으로 바꾼다. 줄이기 순서 끝 SOXL은 그대로.

## 바꿀 내용

### A. stock-strategy-system/alert_policy.json (`portfolio_exposure_policy`)
- 새 키 1개: 3배 상품 비중 합 상한 0.10(키 이름·모양은 Builder가 정한다. 예: `"leveraged_3x_weight_cap": {"max_weight_sum": 0.10, "applies_to_nominal_multiplier_gte": 3, "applies_to": "exposure_increasing_buy_of_member_only", "source": "strategy-1101 / policy-a-1126"}`). 값은 0.10 고정. 비중 = S7이 쓰는 그날 비중(평가 비중, 명목 아님).
- `add_default`: `card_add_stock_else_SOXL` → 카드 ADD 종목만을 뜻하는 새 값(예 `card_add_stock_only`).
- 그 밖(문턱 1.55·1.85·1.25·1.9 · reduce_order · single_stock_* · allowed_index_etfs · nominal_multipliers · add_when_default_paused · 권한 표지 줄)은 그대로. 키 순서·들여쓰기·CRLF 유지.

### B. manage-us-stock-strategy/scripts/portfolio_exposure.py
- `exposure_config`(126~188행): 새 키를 읽는다(없거나 형식이 틀리면 지금처럼 ExposureError — 기본값을 만들지 않는다. 이 오류는 코어 실행 전체를 FAIL로 만든다 — auto_core_decide.py 485~487행). add_default 검사(139~141행)는 **두 값을 받는다**: 옛 값 `card_add_stock_else_<reduce_order 끝>`(지금 동작 그대로)과 새 값(채우기 상품 없음). 채우기 상품(없으면 None)은 config의 **새 칸**에 두고, `supplement` 칸은 줄이기 뜻으로 그대로 둔다 — supplement를 읽는 세 곳(portfolio_exposure.py 1165행 줄이기 3순위, run_portfolio_exposure_review.py 527행, manage-us-stock-strategy/scripts의 코어 본체 스크립트 163행 종가 수집 종목 — 읽기만, 명령에 그 파일 이름을 넣지 않음)은 바꾸지 않는다.
- `projected_increase_reasons`(1229~1242행, 호출 1258·1649행 부근): 늘리는 종목이 3배 상품(배수 ≥ 3)일 때만, 투영 비중에서 3배 상품 비중 합이 상한을 넘으면 사유(예 `LEVERAGED_3X_WEIGHT_CAP`)를 더한다. **1배 종목을 사는 매수는 이 사유로 막지 않는다**(3배가 이미 10% 위여도 — 줄이기는 사장 직접 결정, strategy-check-1105).
- 채우기 후보(1483~1484행): 채우기 상품이 None이고 카드 ADD가 없으면 채우기 권고를 만들지 않는다(omitted에 남길지·이유 문구는 Builder가 정하고 보고). 카드 ADD가 있으면 지금처럼.
- 3배 상한을 cap_limit·cap_breaches(1119~1134행)에 넣지 않는다 — 넣으면 줄이기 1순위 권고와 매도 주문표가 새로 생긴다. 3배 상한 막음이 매도·줄이기 권고·경고·fail-closed 동작을 바꾸지 않아야 한다(코드로 확인해 보고).
- S7 산출(맨 위 `policy` 칸 포함, 1539~1543행)에 새 필드를 넣지 않는다 — `policy` 칸은 스키마가 additionalProperties false이고 schemas/는 고칠 수 없다. 막음 사유 문자열·omitted 항목은 지금 형식 안에서만.
- 0.10을 auto_core_tickets.py의 `POLICY_EXPECTED`(57~59행)에 넣지 않는다(이 파일은 허용 파일 밖) — 2027-03-31에 값만 바꾸면 되게.

### C. manage-us-stock-strategy/scripts/auto_core_decide.py
- 1105~1107행: S7에 넘기는 'SOXL 채우기 제안'(`reduce_order[-1]` + basis_met)을 정책의 채우기 상품으로 바꾼다 — 채우기 상품이 없으면 이 갈래 없음. **새 단서 갈래(new_basis_met)는 그대로.** reduce_order[-1]을 채우기 뜻으로 쓰는 다른 곳이 허용 파일 안에 있으면 같이 고치고, 허용 파일 밖이면 고치지 않고 멈춘 뒤 docs/claude/policy-a-BLOCKED.md에 적는다(grep 결과를 보고에 붙임).
- ASCII만.

### D. 새 테스트 manage-us-stock-strategy/tests/test_policy_a.py
  a. 실제 alert_policy.json: 새 상한 키 0.10, add_default 새 값, 문턱 1.55·1.85·1.25·1.9 · reduce_order 끝 SOXL · single_stock_nominal_cap 0.4 · single_stock_cap_exempt SOXL·TQQQ · 권한 표지 값 그대로(이 테스트 파일 안에서 값을 읽어 비교하는 키 이름은 써도 된다 — '지켜야 할 것' 2번 참고).
  b. exposure_config: 새 키가 없거나 형식이 틀리면 ExposureError. 옛 add_default 값도 받고, 그때 채우기 상품 = SOXL(지금 동작).
  c. 실제 정책 + ADD_ZONE + 카드 ADD 없음 → 채우기 권고에 SOXL 없음. 같은 입력 + 카드 ADD 있음 → 그 카드 종목 채우기(지금처럼).
  d. 3배 0.07 보유, SOXL 새 단서 제안(new_buy_within_band) 격자 → 통과하는 가장 큰 목표가 0.10 이하. TQQQ도 같음. SOXL·TQQQ 합으로 셈(예: SOXL 0.06 + TQQQ 목표 → 합 0.10 넘으면 막음).
  e. 3배 0.12 보유일 때 1배 종목(예 DELL·QQQ) 늘리는 제안은 3배 상한 사유로 막히지 않는다.
  f. 3배 0.12 보유일 때, 같은 입력에서 상한 값을 1.0으로 둔 정책 사본과 줄이기 권고·줄이기 순서가 같다.
  g. auto_core_decide: 채우기 상품이 없으면 S7 제안 목록에 basis_met만인 SOXL이 들어가지 않고, new_basis_met인 SOXL은 들어간다.
  h. swap_buy_leg로 3배를 늘리는 매수 다리도 같은 상한으로 막힌다.
  i. (보완 1, 보완 2 고침) 주문표 경로(auto_core_tickets.py는 부르기만): (i-1) 새 단서 SOXL, 아래 ③ (ㄷ)의 주문표 금액 < 최소 금액(자산 2%) → SOXL 매수 주문표 없음(DEADBAND), 그리고 S7 제안 평가에서 0.10을 넘는 목표에 상한 사유가 붙음 (i-2) (ㄷ)의 주문표 금액 ≥ 최소 금액인 입력(여유가 넉넉한 입력) → SOXL 매수 주문표가 나오고 그 주문표 뒤 3배 합 ≤ 0.10 (i-3) (i-1)과 같은 입력 + 상한 1.0 사본 → SOXL 매수 주문표가 나온다(③ [2]·[3]·[4] 가운데 한 곳의 입력을 써도 된다).

## 테스트
- 기존 테스트는 세 종류만 고친다: ① 실제 정책을 읽으며 SOXL 채우기를 기대하던 곳 — 알려진 곳: test_qqq_registration.py 76행, test_swing_k3_registration.py 91행(add_default 기대값), test_portfolio_exposure.py 302~312행(채우기 SOXL 0.516)·342~356행, test_run_portfolio_exposure_review.py 195행, test_auto_core_t2rc_corefix.py 210~212행, test_auto_core_tickets.py 806행, test_portfolio_exposure_fail_closed.py 409행(더 있을 수 있다 — 아래 전체 실행으로 찾는다). 각 곳은 '새 정책 기대값으로 바꾸기' 또는 '그 시험 안에서 real_policy() 사본의 add_default만 옛 값으로 덮어써 옛 동작을 계속 시험하기' 가운데 하나를 고르고 이유를 적는다(옛 동작 시험이 하나도 안 남으면 안 됨) ② 손으로 만든 정책 fixture에 새 상한 키 한 줄을 넣어야 하는 곳 ③ (보완 1) 3배 상한이 뜻대로 걸려 기대값이 바뀌는 곳 — 아래 8곳뿐(policy-a-BLOCKED.md 1~8, 행은 BLOCKED 때 기준): [1] test_portfolio_exposure.py::ProposalTests.test_new_buy_within_band_is_shown_only_when_projected_exposure_and_cap_hold [2] test_auto_core_t2rc_corefix.py 195행이 든 시험 함수(이름은 보고에 적는다) [3] test_auto_core_tickets.py::ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy [4] test_auto_core_hold_range.py::FullPathTests.test_supplement_proposals_change_with_the_close [5] test_auto_core_hold_range.py::HoldCauseTests.test_reverted_view_hashes_as_the_old_golden [6] test_auto_core_hold_range.py::HoldOffTests.test_default_off_keeps_the_six_golden_keys [7] test_auto_core_risk1r.py::UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before [8] test_auto_core_enter_window.py::GoldenCauseTests.test_the_old_enter_window_gives_the_base_golden. (ㄱ) 원인 확인: 곳마다 그 시험 안에서 실제 정책의 사본을 만들어 새 상한 값만 1.0으로(그곳이 ①에도 걸리면 add_default도 옛 값으로) 바꿔 돌린다. 사본은 시험 안 deepcopy·임시 폴더 파일·mock.patch로만 넣고 scripts에 주입용 코드를 더하지 않는다. 이 사본으로 고치기 전 기대값(옛 해시는 글자 그대로)이 나와야 원인이 상한뿐이다. 해시 대상에 정책 파일 지문(sha·바이트)이 들어 있어 옛 해시가 안 나오는 곳은, 지문 칸만 빼고 비교해 같으면 확인된 것으로 보고 그 키 경로를 보고에 적는다. (보완 2) 상한만 1.0으로 바꾼 사본에서는 그대로 실패하고 add_default까지 옛 값으로 해야 옛 기대가 나오는 곳(원인이 add_default)은 보고 표에 ①로 적고 (가)만 쓴다((ㄴ) 표는 같다). (ㄴ) 바뀐 칸 표: 8곳 모두 실제 정책 산출과 1.0 사본 산출에서 다른 칸을 키 경로·앞뒤 값으로 보고 표에 적는다. 다른 칸은 SOXL·TQQQ 매수 제안·주문표의 있고 없음·목표·금액, S7 채우기 권고·omitted 항목(채우기 상품 없음 사유 포함), 그 막음 사유(상한 사유 또는 상한으로 목표가 줄어 생긴 DEADBAND), 그에 딸린 합계·건수, 그리고 (보완 2) 바뀐 S7 산출을 가리키는 식별자·해시(예 주문표의 inputs.s7_review_id — 그 주문표의 종목·수량·가격·금액은 같아야 함)뿐이어야 한다. 식별자·해시가 다르면 그것이 가리키는 S7 산출 자체를 두 정책으로 비교해 다른 칸을 같은 표에 적고, 그 칸도 위 허용 칸뿐이어야 한다. 매도·줄이기 권고·1배 종목 칸은 위 식별자·해시 칸(과 그 칸만으로 달라진 묶음 해시) 말고 다르면 멈춘다. 결정 status가 다르면 그 까닭이 '3배 매수 주문표가 없어짐'인지 적고, 다른 까닭이면 멈춘다. (ㄷ) (보완 2 고침) 새 단서 SOXL 3곳([2]·[3]·[4])은 3배 비중 합, 여유(0.10 − 합), 통과한 가장 큰 목표, 근거 단계 비율, 주문표 금액, 최소 금액(자산 2%)을 적는다. 주문표 금액 = auto_core_tickets.py가 최소 금액 판정에 실제로 쓰는 값이다(코드 행과 값을 적는다. '여유 × 근거 단계 비율, 주 단위'는 설명일 뿐이며 코드와 다르면 코드를 따르고 다른 점을 적는다 — 그것으로 멈추지 않는다). 이 값이 최소 금액 이상인데 주문표가 없고 막음 사유가 상한 사유·DEADBAND가 아니면 멈춘다. 여유는 최소 금액 이상이지만 주문표 금액이 못 미쳐 DEADBAND가 된 것은 기존 규칙대로이므로 멈추지 않는다. (ㄹ) 고치는 법은 둘 중 하나: (가) 그 사본으로 옛 기대를 계속 시험 — 사본을 넣는 줄만 더하고 기대값 줄은 그대로(권장, 골든 해시는 (가) 먼저) (나) 새 기대값으로 바꾸기 — 새 기대 쪽은 막음 사유(상한 사유 또는 상한으로 생긴 DEADBAND)를 단언하고, test_policy_a.py에 같은 입력 + 1.0 사본으로 옛 기대값(옛 해시 글자 그대로)을 단언하는 짝 시험을 둔다. [2]·[3]·[4] 가운데 적어도 한 곳은 (가). (ㅁ) 멈출 때: (ㄱ)이 안 되는 곳, (ㄴ)·(ㄷ) 조건을 넘는 곳, 이 8곳 밖에서 상한 때문에 새로 실패하는 곳은 고치지 않고 멈춘 뒤 BLOCKED.md에 덧붙인다(앞 내용은 지우지 않는다). 공용 도우미 tests/s5_exposure_fixtures.py와 tests/fixtures/**는 고치지 않는다. 고친 테스트마다 파일:행·종류(①②③)·고친 법·앞뒤를 보고 표에 적는다(③은 (ㄱ)~(ㄷ) 결과도). 그 밖의 기존 테스트를 고쳐야 통과하면 멈추고 docs/claude/policy-a-BLOCKED.md에 적는다.
- 실행은 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 형식 그대로(CLAUDE.md Working rules, builder-rules 6행) — 대상 패턴 `test_policy_a.py`·`test_portfolio_exposure*.py`·`test_run_portfolio_exposure_review*.py`·`test_auto_core*`·`test_qqq_registration.py`·`test_swing_k3_registration.py`, 그리고 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 앞에 환경 변수·옵션을 붙이지 않는다. PATH의 python이 3.15이고 tzdata가 없으면 `python` 자리만 `py -3.13`(qqq-reg-report.md 2절 선례, 보고에 적음).
- 수동 경로라 파이프라인이 없다: 바꾸기 전에 대상 패턴과 전체(`-p "test_*.py"`)를 1번씩 돌려 기준선을 재고, 바꾼 뒤 같은 두 가지를 다시 돌려 기준선 밖 새 실패가 0인지 본다. 대상 패턴 밖에서 새 실패가 나오면 위 ①, 또는 ③의 8곳일 때만 고치고, 아니면 멈추고 BLOCKED.

## 지켜야 할 것 (어기면 Judge FAIL)
1. 실행 금지: auto_core.py·"auto_core.py"가 든 명령·reconcile apply·kiwoomcli·키움 호출·run_auto_core.ps1. 상태(portfolio_state.json)·런타임·일지·원장·예약 작업·대시보드 쓰기 없음.
2. 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling) 무변경, 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`) 없음, schemas/ 무변경. 정책·scripts의 **새 줄**에는 권한 표지 글자를 쓰지 않는다(시험 표식 포함). test_policy_a.py 안에서 값을 읽어 비교하는 키 이름(hard_ceiling_when_exposure_gte·order_authority 등)은 허용한다.
3. 허용 파일만. git i/lf · 작업 트리 CRLF 파일은 줄바꿈 유지. scripts/*.py ASCII 전용.
4. 통합 점검 규칙·예약 지시문·카드·등록부·auto_core_tickets.py는 바꾸지 않는다.
5. git commit·push·병합 없음(바뀐 파일은 worktree에 커밋하지 않은 채 둔다 — 병합 스크립트가 해시 확인 뒤 커밋).

## 보고 docs/claude/policy-a-report.md (자기 worktree 안에 쓴다)
worktree 경로·브랜치·기준 커밋 · 바뀐 줄(파일:행, 앞뒤) · 새 키 이름·값 · reduce_order[-1]·supplement grep 결과와 처리 · 테스트 결과(대상·전체 각각 Ran 수·실패 수, 바꾸기 전 대비)와 `git diff --ignore-cr-at-eol --stat` · 고친 기존 테스트 표 · 바뀐 파일별 sha256(작업 트리 바이트) · 병합 뒤 첫 07:45 코어에서 확인할 것(decision status가 FAIL이 아니고 reasons에 UNEXPECTED_ERROR 없음 · S7 파일이 생김 · E ≤ 1.25인 날 S7 add에 SOXL 없음) · 남은 위험(관문 날 코어 자동 매수 길이 카드 종목·SOXL의 새 단서뿐이 됨 · 2027-03-31에 3배 0을 고르면 정책 값만 바꾸는 K3 · 3배가 이미 10% 위면 3배 매수만 막고 1배 매수는 그대로 · 정책 키가 틀리면 코어 전체 FAIL).

## 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 정책 3배 상한 값 | 이 Builder → 사장 PowerShell 병합 | portfolio_exposure.py 126~188행(exposure_config) → 1229~1242행(projected_increase_reasons) → 1245·1609행(채우기·제안) | 3배를 10% 넘게 늘리는 매수 권고·제안 빠짐 → 코어 매수 주문표 없음(auto_core_tickets.py 789·817행) | 키가 없거나 틀리면 ExposureError(portfolio_exposure.py 185~188행) → 코어 FAIL `UNEXPECTED_ERROR`(auto_core_decide.py 485~487행, 그날 매도 주문표도 없음) · FAIL 뒤 알림 경로 = 확인 필요 | 끊김(⑤ 알림 경로 확인 필요) — 막는 장치: 병합 스크립트가 커밋 전 새 시험 실행 · 승인 경로 = 이 K3(사장 카드 policy-a-1126) |
| 채우기 기본 값 | 같음 | portfolio_exposure.py 139~141·1483~1484행 · auto_core_decide.py 1105~1107행 | 카드 ADD가 없으면 채우기 매수 후보 없음 | 같음 | 같음 |
| 막음 사유 | 07:45 코어 S7 | auto_core_tickets.py 710~720행(best_target 사유) → decision.json blocked | 주문표 없음 + 사유 표시 | 코어 결과(기존 경로) | 연결(병합 뒤) |

## Judge 확인 항목
1. diff가 허용 파일뿐이고(기존 테스트는 세 종류 고침만, 보고 표와 일치. ③은 8곳뿐이고 곳마다 (ㄱ)~(ㄷ) 결과가 있다. (가)는 사본 넣는 줄만 더했고 기대값 줄은 그대로, (나)는 test_policy_a.py에 1.0 사본 짝 시험이 있다. scripts에 정책 주입용 새 코드 없음), 권한 표지 줄·주문 경로·schemas 변경이 없다.
2. 정책의 바뀐 곳이 새 상한 키와 add_default뿐이다. `POLICY_EXPECTED`·auto_core_tickets.py 무변경. 문턱·reduce_order·종목 상한·면제 목록·배수 그대로. JSON 파싱·CRLF·들여쓰기 원래대로. S7 산출 `policy` 칸 무변경.
3. 3배 상한이 늘리는 3배 매수만 막는다: S7 채우기·new_buy_within_band·swap_buy_leg 모두 걸리고, 1배 매수·매도·줄이기 권고·fail-closed는 그대로(코드 행과 테스트 d~h 대조). auto_core_tickets.py hold_range가 _plan_buy를 다시 부를 때(785~817행 부근)도 같은 S7 평가를 거친다.
4. 채우기·줄이기 상품 분리가 완전하다: 줄이기 순서 끝 SOXL 동작 그대로, 채우기 쪽에서 SOXL이 나오는 길이 없다(scripts의 reduce_order[-1]·supplement 전수 grep 대조).
5. 옛 add_default 값을 넣으면 바꾸기 전과 같은 결과(뒤로 맞음).
6. 대상·전체 테스트에서 기준선 밖 새 실패 0, 새 테스트 skip 없음.
7. 3배 상한이 쓰는 비중(S7 평가액 ÷ S7 equity, portfolio_exposure.py 1370행 부근)과 strategy-check-1105의 '그날 코어 표시 비중'(auto_core_tickets.py 185행 부근 값 ÷ total)의 분모가 같은지 대조하고 다르면 차이를 보고에 적었는지 본다.
8. 연결표 ②③⑤ 원문 행 대조(portfolio_exposure.py 126~188·139~141·185~188·1229~1242·1245·1483~1484·1609행, auto_core_decide.py 485~487·1105~1107행, auto_core_tickets.py 710~720·789·817행 — 고친 뒤 행이 밀렸으면 새 행으로).

## 검토 기록 (Builder는 읽지 않아도 됨)
- 보완 2(2026-11-26 23시대 KST): Builder BLOCKED 2회째 — (ㄷ)가 '여유 ≥ 최소 금액'으로 적혀 있었으나 주문표 금액은 여유 × 근거 단계 비율(주 단위)이라 [2]·[3]·[4]가 기존 DEADBAND로 빠짐(코드 오류 아님). (ㄱ)은 8곳 모두 옛 기대·옛 해시 그대로 확인, [5]~[8]의 원인은 add_default(①). 고친 곳: (ㄷ)·D.i 기준, (ㄴ) 허용 칸(채우기 권고·omitted·S7 식별자), (ㄱ) ① 분류 문장, 시작 절 재개 표기. 범위·코드 허용 파일 변경 없음. 조언(Fable, medium) 1회 — 지적 4건: 결론 바뀜 0 · 정정 4 반영((ㄴ) 1배 주문표 식별자 칸 모순 · 식별자가 가리키는 S7 산출도 비교 · 주문표 금액은 코드가 판정에 쓰는 값 · ①은 (가)만) · 미반영 0. 원문: worktree docs/claude/policy-a-BLOCKED.md 2차 기록.
- 보완 1(2026-11-26 22시대 KST): Builder BLOCKED — 3배 상한 때문에 지시문 두 종류 밖 기존 테스트 8곳 실패(제안 3절 안 1 '10%를 넘기는 3배 매수 주문표는 나오지 않는다'가 뜻한 동작). 범위는 그대로 두고 '테스트' 절 ③·D.i·allowed_files·Judge 1번만 고침. 사장 승인 범위(안 1) 안의 지시문 보완. 조언(Fable, medium) 1회 — 지적 7건: 결론 바뀜 0 · 정정 7 반영(상한 1.0 고정·바뀐 칸 표 · 새 단서 3곳 수치 · (나) 짝 시험 · 사본 넣는 법·정책 지문 · D.i 세 갈래 · 8곳을 함수 이름으로·BLOCKED.md 남김 · Judge 1번 문구) · 미반영 0(2건은 고쳐 반영: 정책 지문 칸만 빼고 비교 · 결정 status는 까닭을 적고 다른 까닭이면 멈춤). 원문 확인: worktree docs/claude/policy-a-BLOCKED.md.
- 조언(Fable, medium) 1회 — 지적 8건: 결론 바뀜 0 · 정정 8 반영(시험 파일 안 권한 표지 키 이름 허용 · 연결표 ⑤ = 코어 FAIL 경로 · S7 policy 칸 무변경(스키마) · 범위 열린 문장 3곳 닫음 · 전체 테스트 전후 1번씩·py -3.13 안내 · 주문 경로 문자열 나열 · 초안 표지 지움 · 판정 어려운 표현 3곳) · 미반영 0. 원문으로 다시 확인: portfolio_exposure.py 1536~1545행, schemas/portfolio-exposure-review.schema.json 18~26행, tests/s5_exposure_fixtures.py 15~20행. (작업자 약 128k 토큰 · 2.4분)
