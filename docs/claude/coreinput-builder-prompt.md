---
id: coreinput-builder-prompt
title: "자동 코어 입력 문서 보호 — 미커밋·없는 docs/claude 판정 입력이면 매수 주문표만 막음 (duet-q4-coreinput)"
date: 2026-11-01
class: "authority(K3 — 매수 관문을 조이기만 함, 완화 없음). 개발 큐 authority: Builder Opus → Judge(Opus) → 병합은 사장 결정 + -ApproveAuthority"
source: "사장 결정 카드 '착수 — B 방식'(사장실 회사PC 스레드 '자동 코어 입력 문서 보호', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9FN5zdRrmv1MZgP5gkYnJhR, 제안 coreinput-proposal-2026-11-01 10절 a, 2026-11-01 17:53 KST, 계정=사장). 병합은 별도 사장 결정 + 사장 PowerShell -ApproveAuthority(권한 자리 순서 dst-label 우선 — 제안 4절)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
07:45 decide가 커밋 검사 없이 읽는 docs/claude 입력을 고치기만 해도 매수 관문이 풀리는 구멍을 막는다. 대상 = decide가 실제로 읽는 경로 4종:
1. R-REC1 문서 `docs_dir / RECOVERY_GATE_DOC.name` (auto_core_decide.py:62, 644-645 — 지금은 파일이 없으면 빈 글로 읽어 사용자 지정 충격 EV3a가 사라짐)
2. M6 문서: `inputs.m6_documents(docs_dir)`가 읽는 `M6_PREFIX + "*.md"` 파일 전부 (auto_core_inputs.py:38, 195-197)
3. 관심 명단 `watchlist_path` (auto_core_inputs.py:37, 148-157 — 종목 줄·cardStatus "수락…"·sector가 매수 대상과 RG2 기준 ETF를 정함)
4. 판정 대조 설명 `explained_path` (auto_core_compare.py:34, 297-310; auto_core_decide.py:690, 831 — 연속 일수 표시에만 쓰임)

일부러 뺀 것(바꾸지 않음): 등록부 card-evidence-registry.json은 이미 커밋 검사가 있다(auto_core_inputs.py:90-107 `registry_committed`, decide의 `registry_committed_check` 주입). 카드 문서(등록부 card_doc, auto_core_inputs.py:172-178)는 커밋된 등록부의 절 해시로 고정돼 있어 고치면 그 종목 주문표가 안 나온다(완화 아님). 채점(score_decision_journal.py)의 입력은 사후 채점이라 범위 밖.

## 바꿀 내용

### A. manage-us-stock-strategy/scripts/auto_core_inputs.py
- 새 함수 `core_input_guard(*, recovery_gate_path, watchlist_path, docs_dir, repo, committed_check) -> dict`:
  - 검사 목록 = R-REC1 문서 + 관심 명단 + `m6_documents`와 같은 glob(같은 정렬)으로 찾은 파일 전부. 경로 표시는 repo 기준 상대 경로(posix), repo 밖이면 파일 이름.
  - R-REC1 문서가 없으면 사유 `CORE_INPUT_MISSING:<경로>`.
  - 있는 파일마다: `Path.is_symlink()`가 참이면 사유 `CORE_INPUT_UNCOMMITTED:<경로>`, details "SYMLINK"(`registry_committed`는 resolve로 링크 대상만 보므로 링크 바꿔치기를 놓친다). 아니면 `committed_check(path, repo)`를 부르고 `(False, reason)`이면 `CORE_INPUT_UNCOMMITTED:<경로>`, `details[<경로>] = reason`. 그 호출이 예외를 내면 같은 사유, details는 예외 이름.
  - 있는 파일마다 sha256(바이트)을 `sha256[<경로>]`에 적는다.
  - 관심 명단 파일이 없을 때는 사유를 만들지 않는다(기존 `load_watchlist`가 UNREADABLE = 관심 종목 없음으로 이미 막는다).
  - 함수 본문 전체를 try로 감싼다. 예상 못 한 예외면 `{"status": "BLOCKED", "reasons": ["CORE_INPUT_GUARD_ERROR:<예외 이름>"], ...}`를 돌려준다(decide 전체가 FAIL이 되면 매도 주문표까지 사라지므로 — auto_core_decide.py:450-454).
  - 반환 `{"status": "OK" | "BLOCKED", "reasons": [정렬], "checked": [경로 정렬], "details": {경로: 사유}, "sha256": {경로: hex}}`. 사유가 없으면 "OK".
- `registry_committed`는 바꾸지 않고 그대로 재사용한다.

### B. manage-us-stock-strategy/scripts/auto_core_decide.py
- `decide()`에 키워드 `input_committed_check: Callable[[Path, Path], tuple[bool, str | None]] | None = None`를 더한다. None이면 `registry_committed_check`를 쓴다(기존 테스트의 주입이 그대로 적용되게). `_run`으로 넘긴다.
- `_run` 읽기 순서: 지금 644-645행에 있는 R-REC1 본문 읽기(`recovery_text = ...`)를 `m6_docs = inputs.m6_documents(docs_dir)`(563행) 바로 뒤로 옮기고, 그 바로 뒤(`_wait_for_research` 호출 전)에 `guard = inputs.core_input_guard(...)`를 부른다. 문서 3종을 읽은 직후 검사하기 위해서다(지금 위치는 연구 기록 대기 — 최대 08:30 — 뒤라서, 검사를 앞에 두면 그 사이 편집을 놓친다). 그 뒤 `recovery_text`를 쓰는 곳(669행 `rules.ev3_dates(recovery_text)`)은 그대로.
  - `decision["inputs"]["core_input_guard"] = guard`.
  - guard의 reasons가 비어 있지 않고 직전 decision(`previous`)의 `inputs.core_input_guard.reasons`와 다르면 `exceptions`에 `("CORE_INPUT_UNCOMMITTED", <한 줄>)` 1건을 더한다. 한 줄: "자동 코어 입력 문서 미커밋 — 매수 주문표 막힘(매도 그대로): <경로들> — Cowork 커밋 확인" (한글은 이 파일의 기존 방식대로 \u 이스케이프).
  - `evaluate_session(..., input_block=guard["reasons"])`.
- `evaluate_session`: 키워드 `input_block: list[str] | None = None`를 더하고 `ctx["input_block"] = list(input_block or [])`. 다른 호출(auto_core_replay 등)은 기본값으로 지금과 같다.
- 판정 대조 설명(690행·831행 두 곳 모두): `explained_path` 파일이 있고 심볼릭 링크이거나 committed check가 False(또는 예외)면 `explained = []`, `explained_errors = ["EXPLAINED_FILE_UNCOMMITTED"] + <load_explained의 오류>`. 파일이 없으면 지금대로. 두 곳은 도우미 하나로 묶고, 831행 쪽 `_no_new_session`에 필요한 인자(check, repo)를 넘긴다.
- 스키마는 바꾸지 않는다(auto-core-decision.schema.json의 inputs는 `{"type": "object"}`, auto-core-compare.schema.json의 explained_errors는 문자열 배열 — 확인함).

### C. manage-us-stock-strategy/scripts/auto_core_tickets.py
- `_plan_buy`(806-821행 부근): reasons에 `list(ctx.get("input_block") or [])`를 research 사유 바로 뒤에 더한다 → 매수 주문표 없음, blocked의 매수 항목에 사유가 보인다.
- `plan()`: 기존 735-739행의 `ctx["redeploy_candidate"] = ...` 대입 **뒤에**, `ctx.get("input_block")`이 비어 있지 않으면 `ctx["redeploy_candidate"] = None`(검증 안 된 입력으로 고른 재배치 후보를 매도 regret 표에 쓰지 않음 — 후보 없는 기존 계산과 같아짐). 매도 회로·`_plan_sell`·매도 사유는 바꾸지 않는다.
- `buy_requirements` 행(①~⑥ 셀)은 바꾸지 않는다.

## 테스트
- 기존 테스트 파일은 한 줄도 바꾸지 않는다. 바뀌어야 통과하는 기존 테스트가 있으면 멈추고 BLOCKED.md에 적는다.
- 기준선에서 이미 실패하는 `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol='PLTR', 실제 등록부 카드 해시)은 이 작업과 무관하다. 고치지 않는다.
- **새 파일** `manage-us-stock-strategy/tests/test_auto_core_input_guard.py`만 만든다. test_auto_core_decide의 `Env`를 가져다 쓴다(test_auto_core_enter_window.py 25행처럼 import). 경로별로 결과를 정하는 committed check를 `input_committed_check`로 넣는다. 사례:
  a. 모두 커밋(True) → `inputs.core_input_guard.status == "OK"`, reasons [], tickets·blocked가 `input_committed_check`를 넘기지 않은 실행과 같다.
  b. R-REC1 문서만 미커밋 → 매수 주문표 0건, blocked 매수 항목에 `CORE_INPUT_UNCOMMITTED:<R-REC1 상대 경로>`. 설정은 `Env(holdings={"SOXL": 10})` + `env.write_good_news()`(test_auto_core_decide.py:390-392, 매수 1건이 나오는 설정)를 쓴다. 매도 비교는 여기서 하지 않는다(i에서 확인).
  c. R-REC1 문서 삭제 → `CORE_INPUT_MISSING:<경로>`, 매수 0건.
  d. 같은 접두어의 새 M6 파일(미커밋) → 막힘. 기존 M6 파일 미커밋 → 막힘.
  e. 관심 명단 미커밋 → 막힘.
  f. committed check가 `(False, "REGISTRY_GIT_UNAVAILABLE")`를 돌려주거나 예외를 내면 → 막힘, details에 사유. core_input_guard 안에서 예상 못 한 예외(예: mock으로 glob이 예외) → `CORE_INPUT_GUARD_ERROR:<이름>`, decide는 FAIL이 아니다.
  g. 심볼릭 링크: Windows 권한 문제로 실제 링크를 만들지 말고 `mock.patch.object(Path, "is_symlink", ...)`로 R-REC1 경로만 참 → 막힘, details "SYMLINK".
  h. 설명 파일 미커밋 → `compare.explained_errors`에 `EXPLAINED_FILE_UNCOMMITTED`, tickets·blocked는 a와 같다.
  i. 알림: 직전 기록은 `self.env.output / "2026-10-01" / "decision.json"`에 쓰는 기존 방식(test_auto_core_decide.py:293-297)을 쓴다. 직전 기록의 f6_ran·evaluation_session이 오늘과 같으면 `_no_new_session`으로 빠져 가드가 돌지 않으니(auto_core_decide.py:527-531) 새 세션이 되게 만든다. 가드가 처음 생긴 날 alerts에 code `CORE_INPUT_UNCOMMITTED` 1건(push true), 직전 기록의 inputs.core_input_guard.reasons가 같으면 없음, 다르면 다시 1건.
  j. plan() 단위: test_auto_core_t2rc_corefix.py 250-260행처럼 `redeploy_ranked`가 든 ctx를 만들어 `tk.plan(ctx)`를 부른다. input_block이 있으면 redeploy_candidate가 None이고, 매도 결과(sell tickets·blocked의 sell 항목)가 같은 ctx에서 `redeploy_ranked=[]`일 때와 같다. input_block이 없으면 지금과 같다.
  k. 대체 주입: `input_committed_check`를 주지 않고 `registry_committed_check`가 R-REC1 경로에만 `(False, "REGISTRY_UNCOMMITTED")`를 돌려주게 하면 → 매수 막힘(등록부 검사 쪽 주입이 쓰임). 단 이때 등록부 자체 경로에는 True를 돌려준다.
- 실행은 글자 그대로 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` 만(앞에 환경 변수·옵션을 붙이지 않는다). 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 전체 스위트·기준선 비교는 파이프라인이 한다. `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다. 해시 계산·`python -c`·`cd`·`&&` 등 허용 목록 밖 셸 작업은 하지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py` 실행·"auto_core.py"가 든 명령·reconcile apply·`kiwoomcli` 금지. 키움 호출·예약 작업 변경·정책/상태/일지/원장 쓰기 없음.
2. 매도: 매도 주문표 발행 여부·매도 사유·`_plan_sell`·S7·gate0/gate1은 가드 때문에 달라지지 않는다(재배치 후보 None으로 regret 열·수량·swap_pair가 달라지는 것만 예외). 가드 사유를 gate0·gate1·card_check reasons에 넣지 않는다(넣으면 매도까지 막힘).
3. 가드에 mode 조건이 없다(compare·apply 모두). 06:15 T1(auto_core.py·auto_core_reconcile.py)·GUARDED 목록·`apply_guard_reasons` 무변경.
4. 주문·권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch) 무변경, 결과 dict 기존 키의 값 형식 무변경. 새 키는 `decision["inputs"]["core_input_guard"]`와 `ctx["input_block"]`뿐. 스키마 파일 무변경.
5. 기존 테스트·M6 판정 방식(`m6_listed`)·EV3 정규식·`registry_committed` 무변경.
6. 허용 파일만. 기존 줄바꿈 유지. git commit·push·병합 없음.

## 보고 docs/claude/coreinput-report.md
바뀐 줄(파일:행), 가드 검사 목록과 사유 문자열, 읽기·검사 순서, 대상 테스트 결과, 남은 위험. 반드시 포함: (a) 이 변경은 매수 관문을 조이기만 하고(완화 없음), 재배치 후보 None은 매도 regret 열·수량·swap_pair 표시만 바꿀 수 있다(후보 없는 기존 계산과 같음) (b) 커밋된 편집, `git update-index --assume-unchanged/--skip-worktree`는 막지 못한다 (c) 병합 뒤 첫 새 세션 판정에서 `inputs.core_input_guard.status` OK 확인 필요. 보고서 문장에는 주문·권한 표지 문자열을 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목 (Opus)
1. diff가 허용 5개 파일뿐이고 스키마·정책·기존 테스트 무변경.
2. 가드 검사 목록이 decide가 실제로 읽는 docs/claude 경로와 같다(RECOVERY_GATE_DOC, m6_documents와 같은 glob, watchlist_path, explained_path). 등록부(이미 커밋 검사)와 카드 문서(커밋된 등록부의 절 해시로 고정)는 일부러 뺐다. 그 밖에 빠진 docs/claude 판정 입력이 있는지 auto_core_decide.py·auto_core_inputs.py·auto_core_compare.py·auto_core_tickets.py·auto_core_rules.py를 grep해 확인(채점 score_decision_journal.py는 범위 밖).
3. 미커밋·없음·링크·git 실패·가드 오류 모두 매수 차단(fail-closed)이고 decide를 FAIL로 만들지 않는다. 모두 커밋이면 지금과 같다.
4. 반례 탐색: 검사 시점이 세 문서를 읽은 직후인가(R-REC1 읽기가 연구 기록 대기 뒤에 남아 있지 않은가) / 가드 때문에 매도가 막히는 경로(gate·card_check·_plan_sell)가 있는가 / 가드를 우회해 매수가 나오는 경로(hold_range 재계산 `_hold_ticket`·`hold_eval`, `_limit_daily`, 재배치, `_no_new_session`)가 있는가 / 이름 바꾸기·사본·삭제·링크가 빠지는가 / `input_committed_check`가 None일 때 등록부 주입이 쓰이는가 / redeploy_candidate None이 기존 대입 뒤에 있는가.
5. 새 테스트 a~k 존재·skip 없음, 새 실패 0(파이프라인 checks), 보고 (a)~(c), 주문·권한 줄 무변경.

```dev-run
{"task_id": "coreinput", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 75, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_inputs.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_input_guard.py", "docs/claude/coreinput-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): block buy tickets when docs/claude core inputs are uncommitted or missing"}
```
