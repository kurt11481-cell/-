# dev-run first-collect — NEEDS_APPROVAL

- 시각(UTC): 2026-11-10T23:55:15Z → 2026-11-11T00:27:26Z
- 기준 커밋(base): `b2e0f08de76944b8760b7209595ab3c3e750cd24` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_first_collect.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 1
- 테스트: 기준선 Ran 3497 · 실패 168 → 변경 후 Ran 3501 · 새 실패 0 · skipped 2->2 · 스키마 감사 PASS->PASS
- diff_hash: `320a5fd42a3918a86750d53931968a02df3c640dd4dbed06cff5c0e386e226af`
- Judge 파일 sha256: `1fa9379d3c0ca2a2a7fca938dbbf30637e83e420736250a58ae791d7f031c23e`
- 사유: BASELINE_PREV_NONE
- 다음: `user decision, then .\tools\dev-merge.ps1 first-collect -ApproveAuthority`

## 바뀐 파일

- `docs/claude/first-collect-report.md`
- `manage-us-stock-strategy/scripts/auto_core.py`
- `manage-us-stock-strategy/tests/test_auto_core.py`
- `manage-us-stock-strategy/tests/test_auto_core_first_collect.py`

## Judge 보고 원문 (1회차 FAIL)

## Judge 판정: first-collect — FAIL (코드는 맞음, 보고서 한 줄만 고치면 됨)

코드와 테스트 변경은 지시문과 맞습니다. 다만 Builder 보고서 한 줄이 지시문 "지켜야 할 것 2"를 문자 그대로 어겼습니다. 같은 worktree에서 그 한 줄만 고치면 됩니다.

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core.py:35(timedelta), :58-60(주석·`FIRST_COLLECTION_LOOKBACK_DAYS = 150`), :355-356(else 쪽만 `max(FIRST_COLLECTION_DAY, today - timedelta(...))`로 바꿈). 2026-10-14 − 150일 = 2026-05-17로 다시 계산해 맞음. 하드코딩·TODO 없음. |
| G2 범위 | PASS | changed-files.txt:1-4의 경로는 모두 task-prompt.md:13의 allowed_paths 안. auto_core.py가 바뀐 곳은 diff.patch:5-33의 세 군데뿐. |
| G3 주문 경로·체결 추정 | PASS | diff.patch 전체에 주문 경로 문자열 없음. auto_core.py:357의 collector 호출과 `min(oldest, today)`는 그대로. |
| G4 정책·상태 쓰기와 실패 처리 | PASS | 정책·상태·저널에 쓰는 새 경로 없음. collect_30m.ps1은 그대로라서 빈 응답이면 여전히 실패로 멈춤(보고서:44). |
| G5 비밀 | PASS | 비밀·계좌를 읽거나 출력하는 곳 없음(diff.patch 전체). |
| G6 단언·테스트 | PASS | test_auto_core.py:1314는 기대값만 바꿨고 assertEqual 그대로. 새 테스트 test_auto_core_first_collect.py:30-49. checks.json:319 new_failures 없음, :325-333 대상 테스트 Ran 599 OK, skipped 2 = 기준선 2. |
| G7 class | PASS (class_ok=true) | 주문 단계·한도·정지 스위치 의미 변경 없음. checks.json:127의 `ADDED_LINE:kill_switch`는 보고서 글(first-collect-report.md:25)에서 나온 것이고 정지 스위치를 바꾼 것이 아님. |
| G8-1 diff 구성 | FAIL | 아래 G8-4와 같은 이유: first-collect-report.md:25가 지켜야 할 것 2를 어김. |
| G8-2 테스트가 바뀐 동작을 잡는가 | PASS | :355를 되돌리면 test_auto_core_first_collect.py:34가 2026-04-01을 받아 실패. max를 빼면 :45가 2026-05-17을 받아 실패. 선례 test_auto_core_reconcile_orddt.py:225-232와 같은 load_tests 방식. |
| G8-3 기존 경로 보존 | PASS | 이력 있는 종목은 auto_core.py:355 `date.fromisoformat(last_session)` 그대로. symbols_for_run(:350)·resolve_exchange(:354)·history_updater(:359)도 바뀌지 않음. |
| G8-4 권한 표지·주문 경로 변경 없음 | FAIL | 코드는 깨끗함. 그러나 first-collect-report.md:25가 표지 이름 4개가 들어간 새 줄을 만듦. 지시문 task-prompt.md:54("…가 들어간 줄을 만들거나…않는다", 어기면 FAIL)에 해당. 이 줄 때문에 checks.json:127에 `ADDED_LINE:kill_switch`가 생겼고, 이 사유는 병합 승인 기록에 권한 사유로 함께 나옴(devpipe.py:2130-2132). "경로 때문에 붙는 플래그"라는 지시문 전제(task-prompt.md:9)와 어긋남. |
| G8-5 대상 테스트·1313 기대값 | PASS | checks.json:325-333 OK. 2026-05-17은 2026-10-14 − 150일이 맞음. 단언을 약하게 한 것이 아님. |
| G8-6 / G9 연결표 | 해당 없음 | task-prompt.md에 `## 연결표` 절이 없음. 이 diff는 새 출력 파일·알림·화면 칸·예약을 만들지 않고, 첫 수집 시작일만 바꿈. |

```json
{"verdict": "FAIL", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:35,58-60,355-356"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/first-collect/changed-files.txt:1-4; task-prompt.md:13"}, {"id": "G3", "result": "PASS", "evidence": "diff.patch:1-169; auto_core.py:357-358"}, {"id": "G4", "result": "PASS", "evidence": "auto_core.py:355-358; docs/claude/first-collect-report.md:44"}, {"id": "G5", "result": "PASS", "evidence": "diff.patch:1-169"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core.py:1314; test_auto_core_first_collect.py:30-49; checks.json:319,325-333"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:127 ADDED_LINE:kill_switch comes from docs/claude/first-collect-report.md:25 prose, no kill switch/limit/order-stage change"}, {"id": "G8", "result": "FAIL", "evidence": "docs/claude/first-collect-report.md:25 creates a line containing order_authority/quantity_authority/execution_quantity/kill_switch, violating task-prompt.md:54; surfaces as authority reason ADDED_LINE:kill_switch (checks.json:127, tools/dev_pipeline/devpipe.py:2130-2132)"}, {"id": "G9", "result": "N/A", "evidence": "task-prompt.md has no 연결표 section; diff adds no new output (diff.patch:1-169)"}], "min_fixes": ["docs/claude/first-collect-report.md:25 — rewrite the sentence so that it contains none of the literal names order_authority, quantity_authority, execution_quantity, kill_switch (e.g. '권한 표지 4종 줄과 주문 경로 문자열은 건드리거나 넣지 않았다'); leave code and tests unchanged so the re-check's class_reasons are AUTHORITY_PATH only"]}
```

VERDICT: FAIL

## Judge 보고 원문 (2회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core.py:35 (`timedelta` import 추가), :58-60 (주석 2줄과 `FIRST_COLLECTION_LOOKBACK_DAYS = 150`), :355-356 (이력 없는 종목의 시작일 = `max(FIRST_COLLECTION_DAY, today - timedelta(days=150))`). `today`는 :348에서 정의됨. 하드코딩·TODO 없음 |
| G2 범위 | PASS | changed-files.txt:1-4의 4개 경로가 task-prompt.md:13의 allowed_paths와 정확히 같음. diff.patch에 다른 변경 없음. checks.json:147 status OK, reasons 빈 값 |
| G3 주문 경로·체결 추정 | PASS | diff.patch:1-168에 주문 도구, 주문 경로 문자열, 가격으로 체결을 추정하는 코드 없음 |
| G4 정책·상태 쓰기, fail-closed | PASS | 새 쓰기 경로 없음. `collector`·`collect_30m.ps1`은 그대로라서 빈 응답이면 여전히 `BAR_COLLECTION_FAILED`로 실패함 (auto_core.py:357-358, test_auto_core.py:1317-1319) |
| G5 비밀·계좌 식별자 | PASS | 새 코드·테스트·보고가 .env, 토큰, 계좌를 읽거나 출력하지 않음 (diff.patch 전체) |
| G6 단언·skip·새 테스트 | PASS | test_auto_core.py:1314는 기대값만 바뀌고 같은 assertEqual 전체 튜플 비교가 남음. skip 2→2 (checks.json:7,327), expected failure 표시 없음. 새 테스트 4개 (test_auto_core_first_collect.py:30-49). 전체 실행 3497→3501(+4)이라 상속 테스트가 두 번 돌지 않음. new_failures 0 (checks.json:331) |
| G7 class | PASS (class_ok=true) | class_reasons는 경로 때문에 붙은 AUTHORITY_PATH뿐 (checks.json:139-143). 주문 단계·한도·대조 불변 조건·kill switch·quantity_authority는 바뀌지 않음 (auto_core.py:305,311은 그대로) |
| G8-1 diff 구성 | PASS | diff.patch:5-33(auto_core), 34-46(test 1줄과 주석), 48-99(보고), 100-168(새 테스트) |
| G8-2 테스트가 바뀐 동작을 잡는가 | PASS | 352행을 되돌리면 NEWW 시작일이 04-01이 되어 test_auto_core_first_collect.py:34가 실패함. max를 빼면 05-17이 되어 :45가 실패함. 2026-10-14 − 150일 = 2026-05-17을 직접 다시 계산해 확인 |
| G8-3 기존 경로 보존 | PASS | 이력 있는 종목은 auto_core.py:355에서 그대로 `last_session`을 씀(:39에서 10-12 확인). collect_30m.ps1·history·symbols_for_run은 변경 목록에 없음 |
| G8-4 권한 표지·주문·키움·정책 | PASS | 권한 표지 줄 diff 없음. 보고 문구도 고쳐짐 (first-collect-report.md:25). 키움을 실제로 부르는 테스트 없음 (test 파일 :5) |
| G8-5 대상 테스트 | PASS | test_auto_core*.py: Ran 599, failures 0, status OK (checks.json:337-345). 1314행 기대값 변경은 새 규칙의 정확한 값이라 단언 약화가 아님 |
| G9 연결표 | 해당 없음 | task-prompt.md:4에 따르면 date 2026-11-11 지시문이고 `## 연결표` 절이 없음. 다만 diff에 새 출력 파일·알림·화면 칸·예약이 없고 수집 시작일만 바뀌므로 해당 없음 (task-prompt.md:72) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:35,58-60,355-356"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/first-collect/changed-files.txt:1-4; task-prompt.md:13"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/first-collect/diff.patch:1-168"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:357-358; manage-us-stock-strategy/tests/test_auto_core.py:1317-1319"}, {"id": "G5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/first-collect/diff.patch:1-168"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core.py:1314; manage-us-stock-strategy/tests/test_auto_core_first_collect.py:30-59; checks.json:326-331"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:139-143; manage-us-stock-strategy/scripts/auto_core.py:305,311"}, {"id": "G8", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_first_collect.py:34,39,45; checks.json:337-345; docs/claude/first-collect-report.md:25"}, {"id": "G9", "result": "N/A", "evidence": "workspace/outputs/dev-runs/first-collect/task-prompt.md:4,72"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-11T04:03:58Z
- 병합 커밋: `22769dc22ff7b85734894e46438c38aec015ebc7` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-11-11T04:03:55Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/first-collect/ 의 원본 기록입니다.)
