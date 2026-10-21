# dev-run hide-task-window — NEEDS_APPROVAL

- 시각(UTC): 2026-10-21T02:50:07Z → 2026-10-21T03:08:11Z
- 기준 커밋(base): `adfe067a9d13258cebc2e33d54f6bc0607e7739e` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/register_auto_core_task.ps1)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3247 · 실패 31 → 변경 후 Ran 3250 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `1a31c8d93b480cf43353e4eed63451c28ebe5d0e1a2132de286118dc279398f9`
- Judge 파일 sha256: `4a9fa7c35abed474a41614f520a9932951a2b7958f91cbae129c34c90de01ea3`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 hide-task-window -ApproveAuthority`

## 바뀐 파일

- `docs/claude/hide-task-window-report.md`
- `docs/claude/t2rc-register-task.ps1`
- `manage-us-stock-strategy/scripts/register_auto_core_task.ps1`
- `manage-us-stock-strategy/scripts/register_host_status_task.ps1`
- `manage-us-stock-strategy/scripts/register_journal_score_task.ps1`
- `manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1`
- `manage-us-stock-strategy/scripts/register_sec_scheduled_shadow_task.ps1`
- `manage-us-stock-strategy/tests/test_task_window_hidden.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 등록 스크립트 6개 모두 `$actionArguments`가 `-WindowStyle Hidden -NoProfile ...`으로 시작함: register_auto_core_task.ps1:84, register_host_status_task.ps1:80, register_journal_score_task.ps1:81, register_offsite_backup_task.ps1:81, register_sec_scheduled_shadow_task.ps1:139, docs/claude/t2rc-register-task.ps1:76. `New-ScheduledTaskAction`을 쓰는 다른 파일은 이미 숨김(tools/register-dev-tasks.ps1:59)이거나 테스트 전용임. 빈 껍데기·하드코딩·TODO 없음 |
| G2 범위 | PASS | changed-files.txt:1-8의 경로가 모두 allowed_paths(task-prompt.md:13) 안에 있음. checks.json:122-123에서 status OK, reasons 비어 있음. diff.patch:5-84를 보면 바뀐 것은 주석 1줄과 인자 문자열 1줄뿐임. 6개 파일 모두 CRLF가 유지됐고 비ASCII 문자 없음 |
| G3 주문 경로·체결 추정 | PASS | diff.patch:1-261에 주문 도구, 키움 호출, 가격으로 체결을 추정하는 코드가 없음 |
| G4 정책·상태 쓰기 / fail-closed | PASS | diff에 새로 생긴 쓰기 경로 없음. checks.json:99-100에 나온 state 파일 두 개는 git이 무시하는 이 worktree 안의 실행 파일(.gitignore:31-32)이고, diff에 그 파일을 쓰는 코드는 없음 |
| G5 비밀·계좌 | PASS | 새 테스트는 등록 스크립트 6개를 텍스트로만 읽음(test_task_window_hidden.py:17-24, 43-44) |
| G6 단언 약화·skip·새 테스트 | PASS | 기존 테스트 파일은 바뀌지 않음(changed-files.txt). skip이나 expectedFailure 추가 없음. 새 동작은 test_task_window_hidden.py:47-72가 검사함. checks.json:169에서 new_failures 비어 있음 |
| G7 class | PASS | 주문 단계·도구·예산·상한·불변 조건·kill switch·quantity_authority 어느 것도 바뀌지 않음. class가 authority로 매겨진 이유는 경로 하나뿐임(checks.json:116-118) |
| G8-1 diff 형태 | PASS | 파일마다 주석 1줄 추가와 인자 앞쪽 `-WindowStyle Hidden ` 추가뿐임(diff.patch:9-11, 23-25, 37-39, 51-53, 65-67, 79-81). PlanOnly의 ACTION 줄은 원래 인자를 찍지 않아 그대로 둠(register_auto_core_task.ps1:62) |
| G8-2 로그온·권한·트리거·제한·중복·이름 | PASS | `-LogonType Interactive -RunLevel Limited` 그대로(register_auto_core_task.ps1:92, register_sec_scheduled_shadow_task.ps1:149). 트리거·ExecutionTimeLimit·IgnoreNew·작업 이름 줄은 diff 밖이라 바뀌지 않음 |
| G8-3 수정 전 문자열을 잡는 자체 확인 | PASS | test_task_window_hidden.py:61-71: 수정 전 문자열, `-File` 뒤에 붙인 경우, 빈 텍스트, 대입이 2개인 경우를 모두 실패로 잡고, 수정 뒤 문자열은 통과시킴 |
| G8-4 주문·권한·정책·상태·키움·예약 작업 | PASS | diff.patch 전체에 해당 변경 없음. 보고서의 남은 위험과 병합 뒤 할 일은 hide-task-window-report.md:47-88에 있음(diff.patch:137-178) |
| G8-5 기존 테스트 무변경·target_tests | PASS | 대상 테스트 6묶음 중 5묶음 OK(checks.json:172-222). test_auto_core* 1건(PLTR 등록부 검사) 실패는 기준선에 이미 있던 실패임: 기준선 31건 = 전체 실패 31건, new_failures 비어 있음(checks.json:4, 127-128, 169). 그 테스트는 실제 등록부·관심목록 파일을 읽음(test_auto_core_decide.py:1332-1339) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/register_auto_core_task.ps1:84; register_host_status_task.ps1:80; register_journal_score_task.ps1:81; register_offsite_backup_task.ps1:81; register_sec_scheduled_shadow_task.ps1:139; docs/claude/t2rc-register-task.ps1:76"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/hide-task-window/changed-files.txt:1-8; task-prompt.md:13; checks.json:122-123"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/hide-task-window/diff.patch:1-261"}, {"id": "G4", "result": "PASS", "evidence": "diff.patch:1-261 (no write path); checks.json:99-100 with .gitignore:31-32"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_task_window_hidden.py:17-24,43-44"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_task_window_hidden.py:47-72; checks.json:169"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:116-118; diff.patch:1-84"}, {"id": "G8", "result": "PASS", "evidence": "diff.patch:9-81; register_auto_core_task.ps1:62,92; register_sec_scheduled_shadow_task.ps1:149; test_task_window_hidden.py:61-71; checks.json:4,127-128,169-222; test_auto_core_decide.py:1332-1339"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-21T05:31:01Z
- 병합 커밋: `47971612be75be4ae78cf2d408cd8f532ba69156` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-21T05:30:56Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/hide-task-window/ 의 원본 기록입니다.)
