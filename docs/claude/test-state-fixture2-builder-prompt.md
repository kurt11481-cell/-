---
id: test-state-fixture2-builder-prompt
title: "타이밍 통합 시험이 실제 상태 파일 대신 저장소 안 고정 상태를 읽게 — test-state-fixture2 (재실행)"
date: 2026-11-01
class: "general(일반 변경 — 테스트 파일 2개와 새 fixture 1개만, 코어·스크립트·정책·상태 불변). 개발 큐: Builder Sonnet → 스크립트 판정 → Judge → READY_TO_MERGE면 병합"
source: "사장 결정 카드 '시험 고정 fixture 먼저'(사장실 회사PC 스레드 '전체 코드 리뷰 진행', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX94UxKvNPuoBDHobq4f2XU29, 2026-11-01 16:46 KST, 계정=사장). 근거 docs/claude/code-review-pipeline-2026-11-01.md 'P-1 원인 진단 결과'"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
weekly_user_touch: "0"
---

## 재실행 사유
같은 내용의 1차 작업 test-state-fixture는 2026-11-01 17:42 KST에 READY_TO_MERGE(Judge PASS)였다. 그러나 병합 시험 중 coreinput2 작업이 브랜치를 움직여 dev-merge가 ff_only_refused로 멈췄다. coreinput2 병합(db56303, 21:34 KST) 뒤의 기준 커밋에서 같은 변경을 다시 만든다. 1차 결과를 그대로 옮기지 말고 지금 코드에서 다시 확인한다.

## 목표
`EvaluateTimingIntegrationTests.setUp`(manage-us-stock-strategy/tests/test_evaluate_timing_integration.py 102행)은 git 밖의 실제 상태 파일 `stock-strategy-system/portfolio_state.json`을 읽는다. 이 setUp은 test_portfolio_decision_dashboard.py의 `ManualStep2TimingTests`(2336~2337행)와 그 파생 클래스들도 쓴다.
2026-10-30에 실제 보유가 바뀌면서, 신원 등록부 범위 밖 종목이 시험 입력에 들어갔다. 그 뒤로 개발 큐 기준선 실패가 22+9에서 283으로 늘었다. 시험 결과가 계좌 보유에 따라 달라지면 안 되므로, 저장소 안의 **합성 고정 상태**를 읽게 바꾼다.

## 바꿀 내용
1. 새 파일 `manage-us-stock-strategy/tests/fixtures/portfolio_state.timing.test-only.json`을 만든다.
   - 키 구조는 지금 상태 파일과 같게 둔다. 단 이 시험들이 실제로 읽는 키만 넣고, 나머지는 빼거나 빈 값으로 둔다. 어떤 키를 읽는지는 두 시험 파일과 그것이 부르는 scripts를 Read·Grep으로 확인한다.
   - **값은 모두 합성값이다.** 실제 현금·원가·평균단가·체결 기록·브로커 표시값·계좌 식별자·메모를 옮겨 적지 않는다. 금액은 100.0, 1000.0 같은 둥근 값을 쓴다.
   - 보유 종목은 시험이 전제하는 MVLL·SOXL·NBIS만 둔다. 수량은 시험이 덮어쓰는 값과 맞는 합성값으로 한다(ManualStep2TimingTests 2340~2349행은 MVLL·SOXL을 timing_plan anchor에서 계산하고, NBIS를 15로 둔다).
   - `timing_plan`은 시험이 읽는 필드(positions의 anchor_shares·completed_tranche_ids 등)를 합성값으로 채운다.
   - 맨 위에 `"test_only": true` 같은 표시 키를 둘 수 있다. 단 검증 코드가 모르는 키를 거부하면 넣지 않는다.
2. `test_evaluate_timing_integration.py`의 102행과 325행 부근에서, 실제 상태 파일 대신 위 fixture를 읽게 바꾼다. 325행은 경로를 넘기는 곳이면 fixture 경로를 넘기거나 임시 폴더 사본을 쓴다. 실제 파일에는 절대 쓰지 않는다. `alert_policy.json`은 추적 파일이므로 그대로 읽는다.
3. test_portfolio_decision_dashboard.py는 `case.setUp()`으로 바뀐 상태를 이어받으므로, 고칠 필요가 없으면 고치지 않는다. 고쳐야 하면 상태 출처를 fixture로 바꾸는 줄만 고친다.
4. 단언·기대값·skip은 바꾸지 않는다(builder-rules). 시험을 통과시키려고 검증 코드(scripts/)를 고치지 않는다.
5. 1503행 `test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan`(git 밖 workspace 파일 의존)은 이번 범위가 아니다. 손대지 않는다.

## 테스트
- 아래 두 명령을 **글자 그대로** 실행한다. 앞에 환경 변수를 붙이거나 옵션을 더하지 않는다.
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_evaluate_timing_integration.py"`
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_decision_dashboard.py"`
- 기대: 바꾸기 전에는 evaluate 실패 8·오류 1, dashboard 실패 249다(2026-11-01 15:08 KST 파이프라인 기록). 1차 작업에서는 바꾼 뒤 evaluate OK, dashboard 실패 1(1503행 역사 fixture)이었다. 바꾼 뒤에는 이 수가 크게 줄어야 한다. 남는 실패가 있으면 이름과 원인 한 줄을 보고에 적는다. 남은 실패를 없애려고 범위를 넓히지 않는다.
- 전체 스위트와 기준선 비교는 파이프라인이 한다. `.claude/` 아래를 불러오는 테스트나 명령은 실행하지 않는다. 그 밖의 셸 작업(`python -c`, 파이프, PowerShell)은 하지 않는다. git은 status·diff·log만 쓴다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. 허용 파일 4개만 바꾼다: 두 시험 파일, 새 fixture, 보고서. scripts·정책·실제 상태 파일·.worktreeinclude·tools/·.claude/는 손대지 않는다. 고치는 파일은 원래 줄바꿈을 지킨다.
2. fixture에 실제 계좌 값(현금·원가·평균단가·체결·식별자)이 없다. 모두 합성값이다.
3. 단언 약화·삭제·skip 추가가 없다.
4. 주문·키움·정책·상태·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
5. 판단이 안 되면 BLOCKED.md를 쓰고 멈춘다.

## 보고 docs/claude/test-state-fixture2-report.md
반드시 포함:
(a) 바꾼 줄(파일:행)
(b) fixture의 키 목록과 "모두 합성값" 확인 한 줄
(c) 대상 테스트 2개의 전·후 결과 마지막 3줄
(d) 남은 실패 이름과 원인 한 줄씩
(e) 실제 상태 파일을 읽는 다른 테스트 목록(grep 결과, 이번 범위 밖)
이 보고서에는 보유 수량·금액을 적지 않는다. 주문·권한 표지 문자열도 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 4개뿐이다.
2. fixture 값이 합성값이다. 실제 상태 파일과 비교해 현금·원가·체결 값이 같지 않다.
3. 단언·기대값·skip 변경이 없다. scripts 변경이 없다.
4. 시험이 실제 상태 파일을 더는 읽지 않는다(102·325행 부근).
5. 새 실패가 0이다(파이프라인 checks). 대상 테스트 실패 수가 줄었다.
6. 보고서에 (a)~(e)가 모두 있고, 수량·금액·표지가 없다.

```dev-run
{"task_id": "test-state-fixture2", "class": "general", "builder_model": "sonnet", "builder_effort": "high", "max_turns": 90, "builder_timeout_min": 50, "allowed_paths": ["manage-us-stock-strategy/tests/test_evaluate_timing_integration.py", "manage-us-stock-strategy/tests/test_portfolio_decision_dashboard.py", "manage-us-stock-strategy/tests/fixtures/portfolio_state.timing.test-only.json", "docs/claude/test-state-fixture2-report.md"], "target_tests": ["test_evaluate_timing_integration.py", "test_portfolio_decision_dashboard.py"], "commit_message": "test(timing): read a synthetic in-repo portfolio state instead of the live state file (baseline no longer moves with holdings)"}
```
