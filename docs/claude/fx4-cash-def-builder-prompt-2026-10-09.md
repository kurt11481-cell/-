---
id: fx4-cash-def-builder-prompt-2026-10-09
title: FX-1009 fx-4 Builder 지시문 — 상태 파일 현금 = 키움 주문 가능액(검사 3개) + 재고정 준비
date: 2026-10-09
class: K3 (키움 acceptance 고정 파일 변경 → 활성 acceptance 무효 → 병합 뒤 재고정)
plan: docs/claude/fx1009-fix-plan-2026-10-09.md 5-4절 · 부록 A-4 · 관제판 cash-def-k3
record: docs/claude/fx1009-fx4-record.md (위원회 판정 · 측정 V1 · 사용자 승인)
status: **대체됨 2026-10-10 — 쓰지 않는다.** 측정 V1에서 검사 ⓐ(외화예수금 비교)가 체결 직후 대조를 막는 결함으로 확인(fx1009-fx4-record.md 4-1). 현금 = 주문 가능액은 재설계 T1 Builder 지시문(docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md)에 흡수. 이전: r2 — 2026-10-09 15:17 KST 승인, 15:29 KST 수정 3건 승인(수동 분석 경로 포함, 대시보드 자금 상한 제외, worktree 맞추기). Builder 미실행
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: fx-4 Builder 세션(worktree fx-cash) · fx-4 Judge 지시문(Builder 보고 뒤 Cowork 작성) · 재고정 단계(10/7 절차) · 관제판 cash-def-k3
---

# 0. 시작 조건 (모두 충족해야 Builder를 연다)

1. 사용자 승인: 이 지시문을 검토하고 승인한다. 원문을 `fx1009-fx4-record.md` 5절에 적는다.
2. 측정 V1 PASS: 매도 체결 뒤 같은 조회 시점의 보유 수량과 현금이 서로 맞는지 확인한다(record 4절). 이 판정 없이 시작하지 않는다.
3. record 4절에 "정산 내역 금액 일치(V1-c)" 결과가 있어야 한다. 이 결과로 검사 ⓑ2를 구현할지 정한다.
4. 기준 파일이 아래 blob과 같아야 한다. 다르면 Builder 0단계에서 멈춘다.
   기준 커밋은 `c7b8f6d`이다(fx-1 `a2bc25c` 포함). 이후 커밋은 docs만 허용한다.

| 파일 | 고정(pin) | 기준 blob |
|---|---|---|
| manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py | 예 | fd305e279cfacc8a31d5f416fc315a0120276720 |
| manage-us-stock-strategy/scripts/manual_data_guards.py | 예 | 5e52d82212ddc3f237c7b7d1288468fe34b61048 |
| manage-us-stock-strategy/schemas/kiwoom-reconciliation-proposal.schema.json | 예 | daabb4fcaa168a01f639cbfdd6bca7dd20613cec |
| manage-us-stock-strategy/tests/test_manual_data_guards.py | 예 | 1c73fa7ce2234c93bf594ccb2314b4d344545aab |
| manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json | 예 | 5be053e310ecc79d16ee20798c491f36b96e383e |
| manage-us-stock-strategy/schemas/kiwoom-broker-shadow.schema.json | 아니오 | 4eac4e4e8c210b11c248d9a3fb8de5b501f668b7 |
| manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py | 아니오 | 6b022f1fb0c66fe9576d45bf490c585e77aacc3a |
| manage-us-stock-strategy/scripts/portfolio_exposure.py (바꾸지 않음, 확인만) | 아니오 | 9e8d03401d70a3de7bd376d0204b13a8654c09cd |

# 1. 사용자 조작 (Windows PowerShell, 한 줄씩 — 시작 조건 충족 뒤)

```
cd "E:\사업\##금동한\코덱스저장소"
git add docs/claude/fx4-cash-def-builder-prompt-2026-10-09.md docs/claude/fx1009-fx4-record.md
git commit -m "docs: FX-1009 fx-4 V1 result and Builder prompt r2"
```

worktree `fx-cash`는 2026-10-09에 이미 만들어졌다(52b3cda, Judge를 먼저 실행했을 때). 다음 둘 중 하나를 한다.

- `E:\사업\##금동한\코덱스저장소\.claude\worktrees\fx-cash` 폴더가 있으면, 최신 커밋으로 맞춘 뒤 그 폴더에서 연다. `git merge`가 실패하면 멈추고 Cowork에 출력을 보낸다.
  ```
  cd ".claude\worktrees\fx-cash"
  git merge --ff-only codex/master-recovery-expansion
  claude
  ```
- 폴더가 없으면 새로 만든다.
  ```
  claude --worktree fx-cash
  ```

Claude Code가 열리면 `/model`로 Opus를 고른다. 이어서 `/effort xhigh`를 입력하고, 아래 2절 상자 안의 내용만 붙여 넣는다.
권한 창에서 허용할 것: 파일 읽기, worktree 안 대상 파일 수정, 테스트 실행.
권한 창에서 거부할 것: 키움 접속, `kiwoomcli`, `.env`·토큰 읽기, 원본 폴더(worktree 밖) 수정, materialize·repin_apply·migrate 실행, 커밋·푸시.
끝나면 Cowork에 "fx-4 Builder 완료, worktree fx-cash, 새 실패 수 N" 한 줄만 보낸다. Builder 창은 닫지 않는다(Judge FAIL이면 같은 창에서 최소 수정).

# 2. Builder에게 붙여 넣을 지시문

```text
[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree(fx-cash), BOUNDARY_RESET_REQUIRED · 이유: K3 — 키움 acceptance 고정 파일의 현금 정의를 바꾸고, 병합 뒤 재고정과 독립 Judge가 필요하다.

역할: FX-1009 fx-4 Builder (K3). 사용자 승인 원문은 docs/claude/fx1009-fx4-record.md 5절에 있다. 거기 승인이 없으면 아무것도 고치지 말고 멈춘다.
먼저 읽기: CLAUDE.md(Hard safety, Change classes, Working rules), docs/claude/fx1009-fx4-record.md 전체(위원회 판정, 측정 V1), docs/claude/fx1009-fix-plan-2026-10-09.md 5-4절·7절, manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, manage-us-stock-strategy/references/development-change-review.md의 "Fail-open patterns".
목표: 대조 스크립트가 상태 파일에 쓰는 available_cash_usd = 키움 주문 가능액(fc_ord_alowa). 단, 같은 스냅샷 안의 검사 3개(ⓐⓑⓒ)를 모두 통과할 때만이다. 통과하지 못하면 제안은 적용 불가(BLOCKED, 확인 필요)가 된다. min 값으로 조용히 대신하지 않는다.
금지:
- 키움 실제 접속(테스트는 가짜 결과만), kiwoomcli 실행, 주문 도구, .env*·토큰·키링·계좌번호 읽기·출력
- 정책·상태·원장·결정 일지 파일 수정(stock-strategy-system/*.json, workspace/policies/*, workspace/state/*)
- S7 코드 변경(portfolio_exposure.py, run_portfolio_exposure_review.py — 매도 뒤 매수 멈춤 등 규칙은 그대로, FX-1009 동결)
- 대시보드 매수 자금 상한 변경: portfolio_decision_dashboard.py 1466~1474행 funding_cash = min(orderable_cash, settled_available_cash)와 1713행 비교는 그대로 둔다. 넓히지 않는다.
- 통합 점검 규칙 파일·예약 작업 변경
- 필수 조회 목록(REQUIRED_RECONCILIATION_OPERATIONS)과 브리지 조회 허용 목록 변경, 새 API 추가
- materialize·후보 생성·repin_apply·migrate 실행
- 테스트 약화·삭제, 커밋·푸시
- 줄바꿈 일괄 변환(각 파일의 원래 CRLF/LF 유지)
없는 사실은 만들지 않고 "확인 필요"로 적는다. 보고는 한국어, 식별자는 영어.

0. 기준 확인
   - git diff --stat c7b8f6d HEAD -- manage-us-stock-strategy workspace stock-strategy-system 결과가 0줄인가.
   - fx4 지시문 0절 표의 blob 8개가 git rev-parse HEAD:<path>와 같은가. 다르면 차이를 보고하고 멈춘다.
   - 테스트 기준선: docs/claude/test-baseline-*.md(fx-3이 만든 것)가 있으면 그 실패 id를 쓴다. 없으면 고치기 전에 test-runner 서브에이전트(Haiku)로 전체 스위트를 돌린다. 실패 id는 worktree 밖 임시 폴더에만 저장하고, 저장소에 기준선 파일을 만들지 않는다(fx-3 몫). 서브에이전트 출력은 위치 정보일 뿐이니 개수를 직접 세어 맞춘다.

1. 사실 확인(읽기만, 보고에 적는다)
   a. git grep으로 settled_available_cash, available_cash_usd, cash_status, order_available_cash, verified_orderable_cash_usd, orderable_cash_status, MIN_WITHDRAWABLE_AND_ORDER_AVAILABLE_USD, unsettled_funds_included의 소비처를 모두 찾고, 바꿀 곳과 그대로 둘 곳을 나눈다.
   b. account_open_items의 slby_tp 값 뜻(매수·매도 코드)을 references/kiwoom-*.md, 테스트 fixture, 저장소 안 명세 문서에서 찾는다. 확인하지 못한 코드는 매수로 본다.
   c. account_deposit_detail_read의 d1/d2 *_sell_excta·*_buy_excta·*_setl_dt 뜻을 찾고, record 4절 V1 측정값과 맞는지 본다.
   d. 원장 항목(apply_user_confirmed_broker_snapshot.py)에 proposal_id와 evidence 해시가 들어가는지 본다. 들어가면 원장 코드는 고치지 않는다(제안 파일에 현금 구성이 남으므로).
   e. validate_kiwoom_session_aware_acceptance_candidate.py 374~377행 근처에서 pin scope의 allowed_drift_predecessor_sha256·allowed_predecessor_drift가 어떻게 쓰이는지 본다. 현재 정책이 가리키는 활성 acceptance 해시(835d4f46…)도 확인한다.
   f. 이 변경으로 활성 acceptance가 무효가 되면 병합 뒤 재고정 전까지 무엇이 막히는지 코드로 확인한다(수동 분석 preflight, reconcile propose/show/apply, scheduled_input_gate, 예약 작업 경로). 보고 맨 위에 적는다.

2. 현금 정의 변경 — kiwoom_broker_shadow.py (고정)
   - 스냅샷 cash에 세 필드를 더한다.
     · verified_orderable_cash (number|null)
     · unsettled_cash_component (number|null) = fc_ord_alowa − fc_pymn_alowa
     · orderable_cash_guard {status: "PASS"|"NEEDS_CONFIRMATION", reasons: [...]}
     settled_available_cash = min(...)은 뜻을 바꾸지 않고 표시·호환용으로 둔다.
   - verified_orderable_cash = fc_ord_alowa는 ⓐⓑⓒ가 모두 PASS일 때만 채운다. 아니면 null + NEEDS_CONFIRMATION이다. PASS는 모든 조건을 충족해야 나오게 한다(허용 목록 방식). "알려진 실패가 없음"을 PASS로 보지 않는다.
     ⓐ 예수금 검사
        - fc_entra·fc_pymn_alowa·fc_ord_alowa가 모두 유한한 0 이상 숫자이고, fc_ord_alowa ≤ fc_entra + 1.00 USD여야 한다.
        - 이유 코드: CASH_FIELD_MISSING, CASH_ORDERABLE_EXCEEDS_DEPOSIT
     ⓑ 이중 계산 검사(같은 스냅샷 행만 쓴다)
        - unsettled_cash_component > 1.00이면 다음을 모두 요구한다.
          (b1) 같은 스냅샷 holdings에 qty > poss_qty인 종목이 1개 이상 있다(매도가 보유 수량에 이미 반영됐다는 뜻).
          (b2) record 4절 V1-c가 "일치"일 때만 구현한다: deposit_detail 조회가 PASS이고, 1c에서 확인한 정산 전 매도 − 매수 금액이 unsettled_cash_component와 $1 이내다.
        - unsettled_cash_component < −1.00이면(주문 가능 < 출금 가능) 모르는 상태로 보고 막는다.
        - 이유 코드: CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS, CASH_UNSETTLED_NOT_RECONCILED_WITH_SETTLEMENT_DETAIL, CASH_ORDERABLE_BELOW_WITHDRAWABLE
     ⓒ 미체결 검사
        - account_open_items 조회가 PASS이고, 미체결 매수(1b의 매수 코드, 모르는 코드 포함)가 0건이어야 한다.
        - 이유 코드: CASH_OPEN_ORDERS_UNVERIFIED, CASH_OPEN_BUY_ORDERS_PRESENT
   - cash_status는 verified_orderable_cash 기준으로 바꾼다(null이면 UNVERIFIED). 소비처 영향을 보고한다.
   - validate_reconciliation_inputs: 검사가 NEEDS_CONFIRMATION이면 이유 코드를 errors에 넣어 제안이 BLOCKED(적용 불가)가 되게 한다. 보유·평단만 따로 적용하는 경로는 만들지 않는다.
   - reconciliation_proposal
     · patch available_cash_usd = verified_orderable_cash
     · cash_semantics: available_cash_usd_basis "KIWOOM_ORDER_AVAILABLE_USD_GUARDED", unsettled_funds_included true(사실대로), settled_cash false, margin_or_credit_included false, cash_verified_scope "available_cash_only"(그대로, portfolio_policy_gates.py를 건드리지 않기 위함)
     · 새 블록 cash_components {deposit, withdrawable, order_available, unsettled_component, guard}를 제안에 넣는다. proposal_id 해시 대상이다.
   - 필수 조회 목록은 그대로 둔다. ⓒ 때문에 미체결 조회 실패가 현금 막힘이 된다는 점, ⓑ2를 구현하면 정산 내역 조회 실패가 정산 전 대금이 있을 때만 막힘이 된다는 점을 보고에 적는다.

3. 대조 비교 — manual_data_guards.py (고정)
   - compare_broker_and_system의 브로커 현금 = cash.verified_orderable_cash로 바꾼다. null이면 지금처럼 cash_unknown → UNKNOWN이고, MATCH가 되면 안 된다. 허용 오차는 그대로 둔다.
   - test_manual_data_guards.py에 추가할 경우:
     · 검사 PASS이고 같은 값 → MATCH
     · 검사 실패 → UNKNOWN
     · 상태 현금이 주문 가능액과 같고 min과는 다름 → MATCH

4. 스키마
   - kiwoom-reconciliation-proposal.schema.json(고정): basis const 교체, unsettled_funds_included const true, cash_components 정의(additionalProperties false, required).
   - kiwoom-broker-shadow.schema.json(고정 아님): cash에 새 세 필드를 required로 넣는다.
   - python manage-us-stock-strategy/scripts/validate_schema_contracts.py → PASS.

5. 고정 아닌 소비처·문구(K0/K1)
   - run_manual_portfolio_analysis.py(고정 아님) 361·1585·865행: verified_orderable_cash_usd를 broker_state.cash.verified_orderable_cash(검사 ⓐⓑⓒ 통과 값)에서 읽는다.
     · null이면 orderable_cash_status = NOT_VERIFIED, 값 None으로 둔다(주문 의도 매수는 VERIFIED_ORDERABLE_CASH_REQUIRED로 막힘).
     · 865행 무결성 비교도 같은 칸과 비교한다.
     · manual_data_guards.normalize_broker_state의 실패 대체 dict(129~138행 근처)에도 새 필드를 None·NEEDS_CONFIRMATION으로 넣는다.
     · 조이는 방향만 허용한다. 값이 원값보다 커지거나 VERIFIED가 늘어나는 경로가 있으면 고치지 말고 보고한다.
   - assets/locales/reconcile-broker-state-ko-KR.json
     · row_available_cash_usd → "가용 현금(USD, 키움 주문 가능액 — 정산 전 매도대금 포함, 같은 조회 검사 3개 통과 때만. 정산 현금 아님)"
     · 새 막힘 코드의 한국어 메시지(show가 쓰는 방식을 확인해 맞춘다)
   - references/broker-snapshot-reconciliation.md의 available_cash_usd 문단, references/kiwoom-mcp-local-integration.md 159행: 새 정의와 검사 3개로 고친다. 다른 문장은 그대로 둔다.
   - 바꾸지 않는 것: portfolio_exposure.py, run_portfolio_exposure_review.py, portfolio_policy_gates.py, portfolio_decision_dashboard.py(자금 상한 1466~1474·1713행과 표시), broker_visibility_audit.py, render_beginner_portfolio_report.py, build_holding_fact_pack.py. settled_available_cash는 뜻(min)이 그대로라 이들은 고칠 필요가 없다. 바꿔야 할 이유가 보이면 고치지 말고 보고한다.

6. pin scope 정리(O6) — kiwoom-acceptance-pin-scope.json (고정)
   - 1e 결과에 따라 고친다.
     · allowed_drift_predecessor_sha256 → 현재 활성 acceptance 해시
     · allowed_predecessor_drift → 이번에 바뀐 고정 파일 목록 + pin scope 자신
     근거와 검증기 동작을 보고한다.
   - required_implementation_paths(새 고정 파일 추가·삭제 금지)와 권한 필드는 그대로 둔다. pin_scope_id를 바꿔야 하는지는 스키마·검증기를 보고 판단해 보고한다.

7. 테스트(가짜 결과, 네트워크 없음)
   - test_kiwoom_broker_shadow.py·test_reconcile_broker_state.py에 추가:
     T1 ord = pymn(정산 전 대금 0), 미체결 0 → PASS, available_cash_usd = ord = 예전 min 값
     T2 ord − pymn > 1, 매도 종목 qty > poss_qty, 미체결 0 → PASS, patch 현금 = ord
     T3 ord − pymn > 1인데 모든 종목 qty == poss_qty(이중 계산) → BLOCKED, CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS, proposed_patch 빈 값
     T4 ord > entra + 1 → BLOCKED
     T5 경계: ord = entra + 1.00 → PASS, entra + 1.01 → BLOCKED
     T6 미체결 조회 실패 → BLOCKED · 미체결 매수 1건 → BLOCKED · 모르는 slby_tp → BLOCKED · 미체결 매도만 → PASS
     T7 fc_entra가 null·음수·숫자 아닌 값 → BLOCKED(0으로 바뀌지 않음)
     T8 ord < pymn − 1, 미체결 0 → BLOCKED
     T9 cash_components 값이 바뀌면 proposal_id·confirm_code가 바뀜
     T10 (b2 구현 때만) 정산 내역 조회 실패 또는 금액 불일치 → BLOCKED
   - test_manual_data_guards.py: 3절 경우.
   - test_manual_portfolio_analysis.py: 검사 실패 스냅샷 → verified_orderable_cash_usd None, orderable_cash_status NOT_VERIFIED. 검사 통과 → 원값과 같음.
   - test_portfolio_decision_order_intent.py: 검사 실패 보고서의 매수 의도 → VERIFIED_ORDERABLE_CASH_REQUIRED 막힘.
   - test_portfolio_decision_dashboard.py: 자금 상한이 min(주문 가능, settled_available_cash) 그대로인지(정산 전 대금이 있는 경우 포함).
   - 대상 테스트를 먼저 돌린다(-p로 파일별): test_kiwoom_broker_shadow, test_reconcile_broker_state, test_manual_data_guards, test_state_write_boundary, test_cash_flow_evidence, test_cash_flow_evidence_u3, test_broker_visibility_audit, test_portfolio_decision_dashboard, test_v2_5_beginner_renderer, test_v2_5_broker_snapshot, test_v2_6_broker_beginner, test_manual_portfolio_analysis, test_portfolio_decision_order_intent, test_build_holding_fact_pack, test_portfolio_exposure, test_portfolio_exposure_fail_closed, test_run_portfolio_exposure_review, test_scheduled_input_gate, test_materialize_kiwoom_session_aware_acceptance_candidate, test_v2_6_7_session_aware_kiwoom_priority
     명령 예: python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_broker_shadow.py"
   - 이어서 validate_schema_contracts.py를 돌린다. 마지막으로 test-runner(Haiku)로 전체 스위트를 돌리고 실패만 받는다.
   - 기준선 대비 새 실패는 0이어야 한다. 예외는 고정 파일 drift 때문에 생기는 acceptance 검사 실패다(예: test_v2_6_7 활성 manifest 검사). 이런 실패는 id와 이유를 따로 적는다. 재고정으로 풀리는 것만 예외로 인정한다.

8. 보고: docs/claude/fx4-cash-def-builder-report-2026-10-xx.md (worktree 안, 한국어)
   - 맨 위: (1) 재고정 전까지 막히는 것(1f) (2) 남는 위험 — ⓑ2를 구현하지 않았으면 "여러 매도 중 일부만 보유 수량에 반영된 경우의 이중 계산은 b1이 못 잡음"
   - 바뀐 파일과 줄 수(고정/비고정 구분, 줄바꿈 유지 확인), 1단계 사실, 선택한 이름과 이유, 테스트 전·후 실패 id, 스키마 감사, 확인 필요
   - 재고정 절차(실행하지 않음, docs/claude/kiwoom-repin-candidate-report-2026-10-07.md 순서를 이번 값으로 적용): 사전 확인 → materialize(새 날짜 폴더, --repository-base-commit = 병합 커밋) → 후보 검증 → 사본 모의(base/sim) → 재고정 Judge → 사용자 커밋 → repin_apply(활성 해시 → 새 해시, 사용자 승인) → migrate(사용자 Windows 터미널) → 확인 → 사용자 커밋
   - 실측 확인(재고정 뒤 사용자 PC): reconcile propose 1회
     · 정산 전 대금이 없으면 NO_CHANGE
     · 있으면 현금 차이 1줄
     · 검사 결과 칸이 show 표에 보이는지
   - 보고 전 자기 점검(fail-open 점검표, 항목마다 예/아니오 + 근거 줄):
     · 검사 입력이 하나라도 없을 때 PASS가 되는 경로가 없는가(누락을 허락으로 봄)?
     · 모르는 slby_tp, ord < pymn 상태가 알려진 통과로 가지 않는가?
     · None이 0이 되는 곳, 현금에 .get(key, 0)이 없는가?
     · 검사 실패 때 min 값을 검증된 현금으로 써서 적용하는 경로가 없는가?
     · 검사가 같은 스냅샷 행만 쓰는가(이전 스냅샷·상태 파일 값과 섞지 않는가)?
     · PASS가 조건 전부 충족(허용 목록)인가?
     · 새 API·필수 조회·주문 경로·권한 필드 변경이 없는가?
     · S7 코드·매도 뒤 매수 멈춤·통합 점검 규칙이 그대로인가?
     · 매수 자금 상한(대시보드 funding_cash)이나 주문 의도 금액 한도가 넓어지는 경로가 없는가?
     · 예상 매도대금 칸 verified_orderable_cash_from_expected_proceeds_usd가 여전히 상수 0이고, 새 현금 필드에서 계산되지 않는가?
```

# 3. 다음 단계

1. Builder 보고 → Cowork가 worktree를 직접 읽어 사전 확인한다(git status, diff --stat, 대상 테스트 재실행).
2. Cowork가 fx-4 Judge 지시문을 쓴다(`docs/claude/fx4-cash-def-judge-prompt-2026-10-xx.md`).
3. 별도 Claude Code 세션에서 Judge를 실행한다.
   - FAIL이면 같은 Builder 창에서 최소 수정
   - PASS(또는 조건부 PASS)면 사용자가 커밋·병합
4. 재고정을 진행한다(10/7 절차, 활성화·migrate는 사용자 승인). 병합부터 재고정 활성화까지는 한 번에 이어서 한다. 그 사이는 acceptance가 무효이기 때문이다.
5. 실측 확인 → 관제판 cash-def-k3 done.
6. 그 뒤 K1 후속(별도 승인):
   - 통합 점검 규칙 파일 56줄의 "정의 변경은 K3 대기" 문구 정리(해시 재승인)
   - 대시보드 표기
