# r-i0b-k2 대시보드 타이밍 테스트 픽스처 — K2 Builder 지시문 (2026-10-07)

[Claude Code 실행 권장] 모델: Opus · 추론 노력: high · 세션: 새 worktree (`claude --worktree i0b-k2-tests`) · 이유: K2 — 테스트 픽스처만 수정, 정책·상태·스크립트 diff 0 (pin 목록 밖임은 Builder 0단계에서 다시 확인)

- 근거: `docs/claude/i0b-fill-confirmation-design-2026-10-06.md` §11(Judge 비차단 권고 ②③④), `docs/claude/i0b-policy-builder-report-2026-10-06.md` §6-2. 관제판 `r-i0b-k2`.
- 기준 HEAD `782ee27`. 기준 blob(`git rev-parse HEAD:<경로>`, 다르면 보고하고 멈춘다):
  - `manage-us-stock-strategy/tests/test_portfolio_decision_dashboard.py` `c0388e3a147d15bbc27f554a83d641f04c2eaf00`
  - `manage-us-stock-strategy/tests/test_evaluate_timing_integration.py` `e12f64ccf5b918bff475e2157c91475c07076fde`
  - `stock-strategy-system/alert_policy.json` `f92d4665e58fc373cc68a27bae9500e33ffd0539`
- 상태: 작성 완료, Builder 미실행. 확인 필요로 표시한 것은 Cowork가 코드 전체를 읽지 않고 쓴 부분입니다.

## 1. 사용자 조작 (Windows 터미널, 한 단계씩)

1. `cd "E:\사업\##금동한\코덱스저장소"`
2. 이 문서 커밋(worktree는 커밋된 HEAD에서 만들어진다): `git add docs/claude/r-i0b-k2-builder-prompt-2026-10-07.md` → `git commit -m "docs: r-i0b-k2 dashboard timing test fixture builder prompt"`
3. `claude --worktree i0b-k2-tests`
4. 세션 안에서 `/model` → Opus, `/effort` → high
5. 붙여 넣기: `docs/claude/r-i0b-k2-builder-prompt-2026-10-07.md 2절 상자 안의 지시를 그대로 따르는 Builder로 일해라.`
6. 권한 창: 읽기, 대상 테스트 파일 수정, 테스트 실행은 허용. 키움 접속, `apply` 실행, `.env`·토큰 읽기, 커밋·푸시는 거부.
7. 끝나면 보고 파일 경로를 Cowork에 알린다. Builder 창은 닫지 않는다.

## 2. 붙여넣기용 지시문

```text
역할: r-i0b-k2 Builder (K2). 목표: 대시보드 타이밍 테스트 묶음이 실제 정책·실제 상태 파일에 묶여 계속 실패해서 회귀를 못 잡는 문제를, 테스트 픽스처만 고쳐 해결한다.
먼저 읽기: CLAUDE.md의 Hard safety와 Change classes. docs/claude/i0b-fill-confirmation-design-2026-10-06.md §11. docs/claude/i0b-policy-builder-report-2026-10-06.md §2-2, §3-5, §6-2.
금지: stock-strategy-system/alert_policy.json·portfolio_state.json·reconciliation_ledger.jsonl·decision_journal.json·workspace/policies/* 수정, manage-us-stock-strategy/scripts/ 수정, 고정(pin) 목록 파일 수정, reconcile_broker_state.py apply·portfolio_review_journal.py apply 실행, 키움 접속·키움 도구, 주문 경로, 커밋·푸시, 줄바꿈 일괄 변환(파일은 CRLF 그대로).
없는 사실은 만들지 않는다(확인 필요). 보고는 한국어, 식별자는 영어. 한 단계씩 끝나면 짧게 보고한다.

0. 기준·범위 확인 (읽기만)
   - 위 blob 3개를 git rev-parse HEAD:<경로>로 확인한다. 다르면 보고하고 멈춘다.
   - manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json의 required_implementation_paths에 test_portfolio_decision_dashboard.py, test_evaluate_timing_integration.py 또는 수정하려는 다른 파일이 있는지 확인한다. 하나라도 있으면 K3이다. 즉시 멈추고 보고한다(사용자 승인·독립 Judge 필요).
   - Cowork 확인(2026-10-07): 위 두 테스트 파일은 pin 목록에 없다. 목록에 있는 테스트 파일은 test_manual_data_guards.py, test_scheduled_input_gate.py, test_state_write_boundary.py 세 개뿐이다.

1. 원인 확인 (읽기만, 보고 후 멈춤)
   - stock-strategy-system/portfolio_state.json은 .gitignore 대상이라 HEAD에 없다. worktree에는 이 파일이 없을 수 있다. 이것이 worktree에서 INTEGRITY_FAILURE 약 150건이 나는 원인인지 확인한다(확인 필요: 기존 보고서는 "IntegratedAuthorityLoadError: INTEGRITY_FAILURE, worktree"까지만 적었다).
   - ManualStep2TimingTests.setUp(test_portfolio_decision_dashboard.py 약 2330행)이 test_evaluate_timing_integration.EvaluateTimingIntegrationTests.setUp의 실제 정책·실제 상태를 읽는 경로를 정리한다.
   - ManualStep2TimingTests를 직접 쓰는 클래스(ManualCliInputWiringTests, TechnicalTimingConsumerAlignmentTests)와 그 하위(ManualTimingBrokerInputTests, BrokerCurrentStateAlignmentTests, ManualKiwoomOnlyTimingTests, ManualCorporateActionClearanceTests, ManualTimingEvidenceContractTests 등)를 정확히 센다. 기존 보고서의 "7개 클래스 약 150건"과 다르면 차이를 적는다.
   - 검증에 필요하면 본 폴더의 portfolio_state.json을 worktree로 "바이트 그대로" 복사하는 안을 보고한다. 복사 전에 사용자 승인을 받고, 복사 전후 sha256을 기록하고, 수정·커밋하지 않는다(gitignore 대상).
   - 여기서 사용자 확인을 받고 2단계로 간다.

2. 변경 (테스트 파일만)
   a. ManualStep2TimingTests.setUp: 실제 정책의 positions({})와 실제 상태 대신, test_evaluate_timing_integration.with_timing_positions(policy, "MVLL", "SOXL")로 만든 합성 타이밍 블록을 쓰고, 메모리 안의 holdings를 합성 정책의 anchor와 맞춘다(메모리 보유만 바꾼다. 파일은 쓰지 않는다. 기존 T1이 같은 방식: 합성 블록 + 메모리 MVLL 396). 실제 파일을 수정하지 않는다.
   b. test_stale_internal_timing_quantity_does_not_override_valid_broker_and_anchor(약 2985행)의 "Broker=396" 단언이 위 합성 구성에서도 같은 뜻으로 성립하는지 확인하고 필요한 만큼만 고친다.
   c. test_evaluate_timing_integration.py: T2(test_i0b_t2_...)에 0주 분기 단언을 추가한다. 보유 0주인 holding-risk 정책 종목이 있으면 STATE_MISMATCH/F와 경고 "holding-risk policy symbols are not positive verified holdings"가 나오는지(scripts/evaluate_alerts.py 약 514행 근처를 읽고 정확한 조건·문구를 확인. 확인 필요).
   d. 같은 파일 T1(test_i0b_t1_...)에 result["all_required_evidence_verified"] 단언을 복원한다(scripts/evaluate_alerts.py 약 623행. 어떤 입력에서 True인지 읽고 확인. 확인 필요).
   - scripts/는 읽기만 한다. 코드를 고쳐야만 통과하는 항목이 나오면 고치지 말고 보고하고 멈춘다(테스트로 코드 결함을 발견한 것이므로 사용자 결정).

3. 테스트
   - 대상 모듈을 먼저 돌린다: python -m unittest discover -s manage-us-stock-strategy/tests -p "test_evaluate_timing_integration.py" 그리고 -p "test_portfolio_decision_dashboard.py"(오래 걸리면 클래스 단위로). 변경 전 기준선(실패 수)과 변경 후를 같은 환경에서 나란히 적는다.
   - 환경 원인 실패와 이번 변경 원인 실패를 구분한다. 새 실패 0이어야 한다.
   - 전체 스위트는 서브에이전트 1회로 돌려 새 실패만 보고한다.
   - python manage-us-stock-strategy/scripts/validate_schema_contracts.py도 1회 돌린다.

4. 마무리
   - git status/diff --stat으로 바뀐 파일이 테스트 파일 2개(+보고서)뿐이고 정책·상태·scripts diff가 0임을 보인다.
   - 보고서를 docs/claude/r-i0b-k2-builder-report-2026-10-07.md에 쓴다: 변경 요약, 기준선 대비 표, 환경 원인 실패 분리, 남는 점(이름과 단언이 어긋난 테스트 3개는 S7 2차에서 정리), 확인 필요 목록.
   - 커밋·푸시는 하지 않는다. 사용자가 Windows 터미널에서 한다.
   - 끝났다는 기준: ManualStep2TimingTests와 이를 쓰는 클래스가 합성 타이밍 블록·anchor 맞춘 메모리 보유로 통과(바이트 사본 기준), T2에 0주 분기 단언, T1에 all_required_evidence_verified 단언, 정책·상태·scripts diff 0.
```

## 3. 끝난 뒤 (Cowork)

- 사용자가 "Builder 완료, worktree i0b-k2-tests, 새 실패 수 <숫자>"라고 보내면 Cowork가 worktree를 읽기 전용으로 확인한다(git diff --stat, 바뀐 파일, 대상 테스트 재실행).
- K2라 독립 Judge는 필수가 아니다. 다만 pin 목록 밖임이 확인되고 diff가 테스트 2개뿐일 때에 한한다. 하나라도 어긋나면 K3로 올린다.
- 병합·커밋은 사용자가 Windows 터미널에서 한다.
